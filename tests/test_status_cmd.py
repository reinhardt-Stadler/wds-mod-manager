"""M11 测试: status 命令"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from wds.models import GameRegistry, ModInfo
from wds.registry import save_registry


class TestRunStatus:
    """验证 status 命令逻辑"""

    def test_no_games_discovered(self, capsys: Any, tmp_path: Path):
        from wds.cli.status_cmd import run_status
        empty_root = tmp_path / "empty_wds"
        empty_root.mkdir()
        run_status(wds_root=empty_root, game_id_arg=None)
        captured = capsys.readouterr()
        assert "未发现任何 WDS 游戏" in captured.out

    def test_invalid_game_id(self, capsys: Any, mock_wds_root: Path):
        from wds.cli.status_cmd import run_status
        run_status(wds_root=mock_wds_root, game_id_arg="NONEXIST")
        captured = capsys.readouterr()
        assert "未找到" in captured.out

    def test_game_no_registry(self, capsys: Any, mock_wds_root: Path):
        from wds.cli.status_cmd import run_status
        # EP14 exists in mock_wds_root but has no registry
        run_status(wds_root=mock_wds_root, game_id_arg="EP14")
        captured = capsys.readouterr()
        assert "EP14" in captured.out
        assert "未安装任何美化包" in captured.out

    def test_game_with_empty_registry(
        self, capsys: Any, mock_wds_root: Path,
    ):
        from wds.cli.status_cmd import run_status
        # EP14 exists, create empty registry
        ep14 = mock_wds_root / "EastPrussia' 14"
        registry = GameRegistry(
            game_id="EP14",
            mods={},
            files={},
            original_backup="",
        )
        save_registry(ep14, registry)

        run_status(wds_root=mock_wds_root, game_id_arg="EP14")
        captured = capsys.readouterr()
        assert "EP14" in captured.out
        assert "未安装任何美化包" in captured.out

    def test_game_with_mod(
        self, capsys: Any, mock_wds_root: Path,
    ):
        from wds.cli.status_cmd import run_status
        from wds.models import FileAttribution, SourceVersion
        ep14 = mock_wds_root / "EastPrussia' 14"
        registry = GameRegistry(
            game_id="EP14",
            mods={
                "test_mod": ModInfo(
                    mod_id="test_mod",
                    game_id="EP14",
                    display_name="Test EP14 Mod",
                    source_path=ep14 / "test_mod",
                    install_time="2026-07-19T00:00:00",
                    file_count=5,
                    active_count=5,
                ),
            },
            files={
                "German/2DSymbolsLg.bmp": FileAttribution(
                    original_backup="",
                    active_source="test_mod",
                    sources={
                        "test_mod": SourceVersion(
                            file_path="", hash="abc", installed_at="2026-07-19T00:00:00",
                        ),
                    },
                ),
            },
            original_backup="",
        )
        save_registry(ep14, registry)

        run_status(wds_root=mock_wds_root, game_id_arg="EP14")
        captured = capsys.readouterr()
        assert "EP14" in captured.out
        assert "Test EP14 Mod" in captured.out

    def test_list_all_games_no_game_id(
        self, capsys: Any, mock_wds_root: Path,
    ):
        from wds.cli.status_cmd import run_status
        run_status(wds_root=mock_wds_root, game_id_arg=None)
        captured = capsys.readouterr()
        # Should list all discovered games
        assert "EP14" in captured.out or "EastPrussia" in captured.out
        assert "M41" in captured.out or "Moscow" in captured.out
        assert "S43" in captured.out or "Smolensk" in captured.out

    def test_list_all_with_one_modded_game(
        self, capsys: Any, mock_wds_root: Path,
    ):
        from wds.cli.status_cmd import run_status
        # Add a mod to EP14
        ep14 = mock_wds_root / "EastPrussia' 14"
        registry = GameRegistry(
            game_id="EP14",
            mods={
                "test_mod": ModInfo(
                    mod_id="test_mod",
                    game_id="EP14",
                    display_name="Test Mod",
                    source_path=ep14 / "test_mod",
                    install_time="2026-07-19T00:00:00",
                    file_count=3,
                    active_count=3,
                ),
            },
            files={},
            original_backup="",
        )
        save_registry(ep14, registry)

        run_status(wds_root=mock_wds_root, game_id_arg=None)
        captured = capsys.readouterr()
        # EP14 should show 1 mod, others show 0
        assert "1 个 mod" in captured.out or "Test Mod" in captured.out
