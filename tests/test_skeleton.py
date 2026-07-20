"""Phase 0 冒烟测试: 验证项目骨架和 mock fixture 可用"""

from pathlib import Path


class TestProjectSkeleton:
    """验证项目基础设施"""

    def test_version_importable(self):
        """wds 包可导入且版本号正确"""
        from wds import __version__
        assert __version__ == "1.0.0"

    def test_cli_app_exists(self):
        """Typer app 对象存在"""
        from wds.cli.app import app
        assert app is not None


class TestMockFixtures:
    """验证三个核心 mock fixture 构建正确"""

    def test_mock_game_root_structure(self, mock_game_root: Path):
        """mock 游戏目录包含 Data/ + exe + 国家文件夹"""
        assert mock_game_root.is_dir()
        assert (mock_game_root / "Data").is_dir()
        assert (mock_game_root / "eastprussia14.exe").is_file()
        # 国家文件夹
        for nation in ("German", "Russian", "Austro-Hungarian"):
            nation_dir = mock_game_root / nation
            assert nation_dir.is_dir(), f"缺少国家文件夹: {nation}"
            assert (nation_dir / "Units").is_dir()
            assert (nation_dir / "2DSymbolsLg.bmp").is_file()
        # 标准子目录
        for subdir in ("Info", "Map", "Media", "Screens"):
            assert (mock_game_root / subdir).is_dir()

    def test_mock_mod_root_structure(self, mock_mod_root: Path):
        """mock mod 目录包含装饰层 + 国家透传 + Map/Info"""
        assert mock_mod_root.is_dir()
        # 至少有一个装饰层子目录
        subdirs = [d for d in mock_mod_root.iterdir() if d.is_dir()]
        assert len(subdirs) >= 2, "mod 应包含多个装饰层"
        # 检查 2D Counters 层含国家文件夹
        counters = mock_mod_root / "Hawkeye's 2D Counters (EastPrussia 14)"
        assert counters.is_dir()
        assert (counters / "German" / "2DSymbolsLg.bmp").is_file()
        # 检查 Map 层
        map_enh = mock_mod_root / "Hawkeye's PzC Map Enhancements (Non Desert)"
        assert (map_enh / "Map" / "2DFeatures50.bmp").is_file()

    def test_mock_wds_root_structure(self, mock_wds_root: Path):
        """mock WDS 根目录包含分类文件夹 + 多个游戏 + 非游戏目录"""
        assert mock_wds_root.is_dir()
        # 顶层游戏
        ep14 = mock_wds_root / "EastPrussia' 14"
        assert (ep14 / "Data").is_dir()
        assert (ep14 / "eastprussia14.exe").is_file()
        # 分类文件夹下的游戏
        pzc = mock_wds_root / "PanzerCampain"
        assert pzc.is_dir()
        assert (pzc / "Moscow '41" / "Data").is_dir()
        assert (pzc / "Smolensk '43" / "Data").is_dir()
        # 非游戏目录存在
        assert (mock_wds_root / "menu").is_dir()
        assert (mock_wds_root / "Moscow '41 Scenario Documents").is_dir()

    def test_mock_game_has_bmp_files(self, mock_game_root: Path):
        """mock 游戏目录中 BMP 文件数量合理"""
        bmp_files = list(mock_game_root.rglob("*.bmp")) + list(mock_game_root.rglob("*.BMP"))
        assert len(bmp_files) > 20, f"BMP 文件过少: {len(bmp_files)}"


class TestAppSubcommands:
    """验证 M08 子命令注册"""

    def test_app_has_commands(self):
        from wds.cli.app import app
        commands = list(app.registered_commands)
        command_names = {getattr(c.callback, "__name__", None) for c in commands}
        expected = {"scan", "install", "status", "uninstall", "switch", "rename", "list_mods", "undo"}
        for name in expected:
            assert name in command_names, f"缺少子命令: {name}"

    def test_app_callback(self):
        from wds.cli.app import app
        assert app.registered_callback is not None


class TestDisplayModule:
    """验证 M13 display 模块导出"""

    def test_display_functions_exist(self):
        from wds.cli.display import (
            create_progress,
            print_divider,
            print_error,
            print_header,
            print_info,
            print_mod_list,
            print_scan_table,
            print_status_panel,
            print_success,
            print_warning,
        )
        assert callable(create_progress)
        assert callable(print_divider)
        assert callable(print_error)
        assert callable(print_header)
        assert callable(print_info)
        assert callable(print_mod_list)
        assert callable(print_scan_table)
        assert callable(print_status_panel)
        assert callable(print_success)
        assert callable(print_warning)
