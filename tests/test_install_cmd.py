"""M10 测试: install 命令"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


class TestRunInstall:
    """验证 install 命令逻辑"""

    def test_mod_path_not_exists(self, capsys: Any, mock_wds_root: Path):
        from wds.cli.install_cmd import run_install
        mod_path = mock_wds_root / "nonexistent_mod"
        run_install(
            wds_root=mock_wds_root, mod_path=mod_path,
            game_id_arg=None, display_name_arg=None, yes=True,
        )
        captured = capsys.readouterr()
        assert "不存在" in captured.out

    def test_zip_not_supported(self, capsys: Any, mock_wds_root: Path):
        from wds.cli.install_cmd import run_install
        zip_path = mock_wds_root / "Hawkeyes_F40_Mod.zip"
        run_install(
            wds_root=mock_wds_root, mod_path=zip_path,
            game_id_arg=None, display_name_arg=None, yes=True,
        )
        captured = capsys.readouterr()
        assert "暂不支持" in captured.out

    def test_no_games(self, capsys: Any, tmp_path: Path):
        from wds.cli.install_cmd import run_install
        empty_root = tmp_path / "empty"
        empty_root.mkdir()
        mod_dir = tmp_path / "mod"
        mod_dir.mkdir()
        run_install(
            wds_root=empty_root, mod_path=mod_dir,
            game_id_arg=None, display_name_arg=None, yes=True,
        )
        captured = capsys.readouterr()
        assert "未发现任何 WDS 游戏" in captured.out

    def test_invalid_game_id(self, capsys: Any, mock_wds_root: Path, mock_mod_root: Path):
        from wds.cli.install_cmd import run_install
        run_install(
            wds_root=mock_wds_root, mod_path=mock_mod_root,
            game_id_arg="NONEXIST", display_name_arg=None, yes=True,
        )
        captured = capsys.readouterr()
        assert "未找到" in captured.out

    def test_install_with_auto_detect(
        self, capsys: Any, mock_wds_root: Path, mock_mod_root: Path,
    ):
        from wds.cli.install_cmd import run_install
        run_install(
            wds_root=mock_wds_root, mod_path=mock_mod_root,
            game_id_arg="EP14", display_name_arg="Test Install", yes=True,
        )
        captured = capsys.readouterr()
        assert "安装完成" in captured.out
        assert "Test Install" in captured.out

    def test_install_then_check_registry(
        self, capsys: Any, mock_wds_root: Path, mock_mod_root: Path,
    ):
        from wds.cli.install_cmd import run_install
        from wds.registry import load_registry

        run_install(
            wds_root=mock_wds_root, mod_path=mock_mod_root,
            game_id_arg="EP14", display_name_arg=None, yes=True,
        )
        capsys.readouterr()  # discard output

        # Verify registry was created
        ep14 = mock_wds_root / "EastPrussia' 14"
        registry = load_registry(ep14)
        assert registry is not None
        assert registry.game_id == "EP14"
        assert len(registry.mods) > 0
        # At least one mod registered
        mod_id = list(registry.mods.keys())[0]
        assert registry.mods[mod_id].file_count > 0

    def test_install_with_display_name(
        self, capsys: Any, mock_wds_root: Path, mock_mod_root: Path,
    ):
        from wds.cli.install_cmd import run_install
        from wds.registry import load_registry

        run_install(
            wds_root=mock_wds_root, mod_path=mock_mod_root,
            game_id_arg="EP14", display_name_arg="My Custom Name", yes=True,
        )
        capsys.readouterr()

        ep14 = mock_wds_root / "EastPrussia' 14"
        registry = load_registry(ep14)
        mod = list(registry.mods.values())[0]
        assert mod.display_name == "My Custom Name"


class TestRunInstallInteractive:
    """验证非 --yes 的交互式路径识别 (D-013)"""

    def test_interactive_accept_all_installs(
        self, capsys: Any, mock_wds_root: Path, mock_mod_root: Path, monkeypatch: Any,
    ):
        from wds.cli.install_cmd import run_install
        from wds.cli.review import build_review_groups
        from wds.matcher import scan_mod
        from wds.registry import load_registry
        from wds.scanner import discover_games

        # 预计算每组应答: 有建议目标的组回车接受, 无匹配组跳过
        games = discover_games(mock_wds_root)
        ep14 = [g for g in games if g.game_id == "EP14"][0]
        groups = build_review_groups(scan_mod(mock_mod_root, ep14))
        responses = ["s" if g.proposed_target is None else "" for g in groups]
        it = iter(responses)
        monkeypatch.setattr("builtins.input", lambda *a, **k: next(it))

        run_install(
            wds_root=mock_wds_root, mod_path=mock_mod_root,
            game_id_arg="EP14", display_name_arg="Interactive", yes=False,
        )
        out = capsys.readouterr().out
        assert "安装完成" in out
        assert "备份池位于" in out  # 完成后提醒备份位置

        ep14_root = mock_wds_root / "EastPrussia' 14"
        registry = load_registry(ep14_root)
        assert registry is not None
        assert len(registry.mods) > 0

    def test_interactive_abort(
        self, capsys: Any, mock_wds_root: Path, mock_mod_root: Path, monkeypatch: Any,
    ):
        from wds.cli.install_cmd import run_install
        from wds.registry import load_registry

        # 首组即输入 q 退出
        monkeypatch.setattr("builtins.input", lambda *a, **k: "q")
        run_install(
            wds_root=mock_wds_root, mod_path=mock_mod_root,
            game_id_arg="EP14", display_name_arg=None, yes=False,
        )
        out = capsys.readouterr().out
        assert "已取消安装" in out

        ep14 = mock_wds_root / "EastPrussia' 14"
        assert load_registry(ep14) is None  # 未安装

    def test_interactive_skip_all_no_install(
        self, capsys: Any, mock_wds_root: Path, mock_mod_root: Path, monkeypatch: Any,
    ):
        from wds.cli.install_cmd import run_install
        from wds.registry import load_registry

        # 所有组都跳过
        monkeypatch.setattr("builtins.input", lambda *a, **k: "s")
        run_install(
            wds_root=mock_wds_root, mod_path=mock_mod_root,
            game_id_arg="EP14", display_name_arg=None, yes=False,
        )
        out = capsys.readouterr().out
        assert "没有可安装的文件" in out

        ep14 = mock_wds_root / "EastPrussia' 14"
        assert load_registry(ep14) is None


class TestBackupHint:
    """验证替换工作完成后的备份位置提醒"""

    def test_install_yes_shows_backup_hint(
        self, capsys: Any, mock_wds_root: Path, mock_mod_root: Path,
    ):
        from wds.cli.install_cmd import run_install

        run_install(
            wds_root=mock_wds_root, mod_path=mock_mod_root,
            game_id_arg="EP14", display_name_arg=None, yes=True,
        )
        out = capsys.readouterr().out
        assert "备份池位于" in out
        assert "_backup" in out
