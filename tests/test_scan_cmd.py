"""M09 测试: scan 命令"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


class TestRunScan:
    """验证 scan 命令逻辑"""

    def test_mod_path_not_exists(self, capsys: Any, mock_wds_root: Path):
        from wds.cli.scan_cmd import run_scan
        mod_path = mock_wds_root / "nonexistent_mod"
        run_scan(wds_root=mock_wds_root, mod_path=mod_path, game_id_arg=None)
        captured = capsys.readouterr()
        assert "不存在" in captured.out

    def test_zip_file_not_supported(self, capsys: Any, mock_wds_root: Path):
        from wds.cli.scan_cmd import run_scan
        zip_path = mock_wds_root / "Hawkeyes_F40_Mod.zip"
        run_scan(wds_root=mock_wds_root, mod_path=zip_path, game_id_arg=None)
        captured = capsys.readouterr()
        assert "暂不支持" in captured.out

    def test_no_games_discovered(self, capsys: Any, tmp_path: Path):
        from wds.cli.scan_cmd import run_scan
        empty_root = tmp_path / "empty_wds"
        empty_root.mkdir()
        mod_dir = tmp_path / "some_mod"
        mod_dir.mkdir()
        run_scan(wds_root=empty_root, mod_path=mod_dir, game_id_arg=None)
        captured = capsys.readouterr()
        assert "未发现任何 WDS 游戏" in captured.out

    def test_auto_detect_game_by_mod(
        self, capsys: Any, mock_wds_root: Path, mock_mod_root: Path,
    ):
        from wds.cli.scan_cmd import run_scan
        # mock_mod_root 是 "Hawkeyes_EP14_Mod" 风格，含 EP14 的阵营名
        # mock_wds_root 中包含 EastPrussia' 14 (EP14)
        run_scan(wds_root=mock_wds_root, mod_path=mock_mod_root, game_id_arg=None)
        captured = capsys.readouterr()
        # 应自动检测到 EP14 并扫描输出映射表
        assert "EP14" in captured.out
        assert "✓" in captured.out or "自动" in captured.out

    def test_specify_game_id(
        self, capsys: Any, mock_wds_root: Path, mock_mod_root: Path,
    ):
        from wds.cli.scan_cmd import run_scan
        run_scan(wds_root=mock_wds_root, mod_path=mock_mod_root, game_id_arg="EP14")
        captured = capsys.readouterr()
        assert "EP14" in captured.out
        assert "手动指定" in captured.out

    def test_invalid_game_id(
        self, capsys: Any, mock_wds_root: Path, mock_mod_root: Path,
    ):
        from wds.cli.scan_cmd import run_scan
        run_scan(wds_root=mock_wds_root, mod_path=mock_mod_root, game_id_arg="NONEXIST")
        captured = capsys.readouterr()
        assert "未找到" in captured.out

    def test_unmatched_mod_no_detection(
        self, capsys: Any, mock_wds_root: Path, tmp_path: Path,
    ):
        from wds.cli.scan_cmd import run_scan
        # 创建一个与任何游戏都不匹配的 mod 目录
        unknown_mod = tmp_path / "Unknown_Mod"
        unknown_mod.mkdir()
        (unknown_mod / "SomeRandomDir").mkdir()
        run_scan(wds_root=mock_wds_root, mod_path=unknown_mod, game_id_arg=None)
        captured = capsys.readouterr()
        assert "无法自动推断" in captured.out

