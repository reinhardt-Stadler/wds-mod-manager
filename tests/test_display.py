"""M13 测试: display.py 输出格式化"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from wds.models import ModState


class TestPrintHelpers:
    """验证彩色消息辅助函数可调用"""

    def test_print_success(self, capsys: Any):
        from wds.cli.display import print_success
        print_success("hello")
        captured = capsys.readouterr()
        assert "hello" in captured.out

    def test_print_warning(self, capsys: Any):
        from wds.cli.display import print_warning
        print_warning("warn msg")
        captured = capsys.readouterr()
        assert "warn msg" in captured.out

    def test_print_error(self, capsys: Any):
        from wds.cli.display import print_error
        print_error("err msg")
        captured = capsys.readouterr()
        assert "err msg" in captured.out

    def test_print_info(self, capsys: Any):
        from wds.cli.display import print_info
        print_info("info msg")
        captured = capsys.readouterr()
        assert "info msg" in captured.out

    def test_print_header(self, capsys: Any):
        from wds.cli.display import print_header
        print_header("Test Title")
        captured = capsys.readouterr()
        assert "Test Title" in captured.out

    def test_print_divider(self, capsys: Any):
        from wds.cli.display import print_divider
        print_divider()
        captured = capsys.readouterr()
        assert len(captured.out) > 0


class TestCreateProgress:
    """验证进度条创建"""

    def test_create_progress(self):
        from wds.cli.display import create_progress
        progress = create_progress()
        assert progress is not None


class TestPrintScanTable:
    """验证 scan 映射表输出"""

    def test_empty_mappings(self, capsys: Any):
        from wds.cli.display import print_scan_table
        print_scan_table([], mod_path_str="test_mod", game_info_str="test_game")
        captured = capsys.readouterr()
        assert "test_mod" in captured.out
        assert "test_game" in captured.out

    def test_with_mappings(self, capsys: Any):
        from wds.cli.display import print_scan_table
        mappings = [
            ("mod/Info/BlankboxH.bmp", "Info/BlankboxH.bmp", "auto"),
            ("mod/Map/2DFeatures50.bmp", None, "ambiguous"),
            ("mod/Unknown/extra.txt", None, "unmatched"),
        ]
        print_scan_table(mappings)
        captured = capsys.readouterr()
        assert "BlankboxH.bmp" in captured.out
        assert "自动" in captured.out
        assert "歧义" in captured.out
        assert "无匹配" in captured.out

    def test_all_auto(self, capsys: Any):
        from wds.cli.display import print_scan_table
        mappings = [(f"mod/Info/file{i}.bmp", f"Info/file{i}.bmp", "auto") for i in range(3)]
        print_scan_table(mappings)
        captured = capsys.readouterr()
        assert "3 个文件" in captured.out
        assert "3 自动" in captured.out


class TestPrintStatusPanel:
    """验证 status 面板输出"""

    def test_no_registry(self, capsys: Any):
        from wds.cli.display import print_status_panel
        print_status_panel("Moscow '41", [], registry_exists=False)
        captured = capsys.readouterr()
        assert "Moscow '41" in captured.out
        assert "未安装任何美化包" in captured.out

    def test_empty_summary(self, capsys: Any):
        from wds.cli.display import print_status_panel
        print_status_panel("Test Game", [])
        captured = capsys.readouterr()
        assert "未安装任何美化包" in captured.out

    def test_with_full_mod(self, capsys: Any):
        from wds.cli.display import print_status_panel
        summary: list[dict[str, Any]] = [
            {
                "mod_id": "hawkeyes_f40",
                "display_name": "Hawkeye's F40 Mod",
                "state": ModState.FULL,
                "active_count": 45,
                "total_count": 45,
            },
        ]
        print_status_panel("France '40", summary)
        captured = capsys.readouterr()
        assert "France '40" in captured.out
        assert "Hawkeye's F40 Mod" in captured.out
        assert "已安装" in captured.out

    def test_with_partial_mod(self, capsys: Any):
        from wds.cli.display import print_status_panel
        summary: list[dict[str, Any]] = [
            {
                "mod_id": "mod_a",
                "display_name": "Mod A",
                "state": ModState.PARTIAL,
                "active_count": 20,
                "total_count": 45,
            },
        ]
        print_status_panel("Test", summary)
        captured = capsys.readouterr()
        assert "Mod A" in captured.out
        assert "部分" in captured.out

    def test_with_inactive_mod(self, capsys: Any):
        from wds.cli.display import print_status_panel
        summary: list[dict[str, Any]] = [
            {
                "mod_id": "mod_b",
                "display_name": "Mod B",
                "state": ModState.INACTIVE,
                "active_count": 0,
                "total_count": 30,
            },
        ]
        print_status_panel("Test", summary)
        captured = capsys.readouterr()
        assert "Mod B" in captured.out
        assert "未安装" in captured.out


class TestPrintModList:
    """验证 list 汇总输出"""

    def test_no_games(self, capsys: Any):
        from wds.cli.display import print_mod_list
        print_mod_list([])
        captured = capsys.readouterr()
        assert "未发现任何 WDS 游戏" in captured.out

    def test_game_without_mods(self, capsys: Any):
        from wds.cli.display import print_mod_list
        data: list[dict[str, Any]] = [
            {
                "game_id": "S43",
                "full_name": "Smolensk '43",
                "mods": [],
                "mod_count": 0,
            },
        ]
        print_mod_list(data)
        captured = capsys.readouterr()
        assert "S43" in captured.out
        assert "Smolensk '43" in captured.out
        assert "无 mod" in captured.out

    def test_game_with_mods(self, capsys: Any):
        from wds.cli.display import print_mod_list
        data: list[dict[str, Any]] = [
            {
                "game_id": "M41",
                "full_name": "Moscow '41",
                "mods": [
                    {
                        "mod_id": "hawkeyes_m41",
                        "display_name": "Hawkeye's M41",
                        "state": ModState.FULL,
                        "active_count": 30,
                        "total_count": 30,
                    },
                    {
                        "mod_id": "test_mod",
                        "display_name": "Test Mod",
                        "state": ModState.INACTIVE,
                        "active_count": 0,
                        "total_count": 10,
                    },
                ],
                "mod_count": 2,
            },
        ]
        print_mod_list(data)
        captured = capsys.readouterr()
        assert "M41" in captured.out
        assert "2 个 mod" in captured.out
        assert "hawkeyes_m41" in captured.out
        assert "test_mod" in captured.out
