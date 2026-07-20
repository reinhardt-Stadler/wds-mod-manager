"""M07 installer.py 测试: 安装引擎（编排 M01~M06）"""

from pathlib import Path

import pytest

from wds.installer import install_mod, switch_mod, uninstall_mod
from wds.models import GameInfo, ModState, PathMapping
from wds.registry import get_mod_state, load_registry
from wds.utils import collect_bmp_files


# ===========================================================================
# 辅助 fixtures
# ===========================================================================

@pytest.fixture
def game_info(mock_game_root: Path) -> GameInfo:
    return GameInfo(
        game_id="EP14",
        full_name="EastPrussia' 14",
        root_path=mock_game_root,
        exe_name="eastprussia14.exe",
        nations=["German", "Russian", "Austro-Hungarian"],
        has_original_backup=False,
    )


@pytest.fixture
def basic_mappings() -> list[PathMapping]:
    """覆盖 German/ + Info/ 两个目录的基础映射"""
    return [
        PathMapping(
            mod_subfolder="Hawkeye's 2D Counters (EastPrussia 14)/German",
            game_target="German",
            confidence="auto",
            resolved_by="leaf_match",
        ),
        PathMapping(
            mod_subfolder="Generic MapMod (Blitzkrieg Phase)/Info",
            game_target="Info",
            confidence="auto",
            resolved_by="leaf_match",
        ),
    ]


# ===========================================================================
# install_mod
# ===========================================================================

class TestInstallMod:
    def test_basic_install(self, mock_game_root, mock_mod_root, game_info, basic_mappings):
        """完整安装流程无报错，返回 ModInfo"""
        result = install_mod(mock_game_root, game_info, mock_mod_root, basic_mappings)
        assert result is not None
        assert result.game_id == "EP14"
        assert result.file_count > 0

    def test_creates_original_backup(self, mock_game_root, mock_mod_root, game_info, basic_mappings):
        """首次安装应自动创建原版备份 (D-010)"""
        install_mod(mock_game_root, game_info, mock_mod_root, basic_mappings)
        assert (mock_game_root / "_backup" / "EP14_original").is_dir()

    def test_files_replaced(self, mock_game_root, mock_mod_root, game_info, basic_mappings):
        """安装后游戏文件应被 mod 文件覆盖"""
        # 记录安装前的内容
        before = (mock_game_root / "German" / "2DSymbolsLg.bmp").read_bytes()
        install_mod(mock_game_root, game_info, mock_mod_root, basic_mappings)
        after = (mock_game_root / "German" / "2DSymbolsLg.bmp").read_bytes()
        # mod 文件内容应与安装后一致
        mod_file = mock_mod_root / "Hawkeye's 2D Counters (EastPrussia 14)" / "German" / "2DSymbolsLg.bmp"
        assert after == mod_file.read_bytes()
        assert before != after  # 确实被替换了

    def test_registry_created(self, mock_game_root, mock_mod_root, game_info, basic_mappings):
        """安装后 registry 应存在且包含 mod 记录"""
        result = install_mod(mock_game_root, game_info, mock_mod_root, basic_mappings)
        registry = load_registry(mock_game_root)
        assert registry is not None
        assert result.mod_id in registry.mods

    def test_file_attribution_recorded(self, mock_game_root, mock_mod_root, game_info, basic_mappings):
        """安装后文件归属应被记录"""
        result = install_mod(mock_game_root, game_info, mock_mod_root, basic_mappings)
        registry = load_registry(mock_game_root)
        assert "German/2DSymbolsLg.bmp" in registry.files
        fa = registry.files["German/2DSymbolsLg.bmp"]
        assert fa.active_source == result.mod_id

    def test_mod_backup_created(self, mock_game_root, mock_mod_root, game_info, basic_mappings):
        """安装时应创建 mod 备份（备份被替换的当前文件）"""
        install_mod(mock_game_root, game_info, mock_mod_root, basic_mappings)
        backup_dir = mock_game_root / "_backup"
        mod_backups = [d for d in backup_dir.iterdir()
                       if d.is_dir() and not d.name.endswith("_original")
                       and d.name != "EP14_original"]
        assert len(mod_backups) >= 1

    def test_mod_state_full_after_install(self, mock_game_root, mock_mod_root, game_info, basic_mappings):
        """安装后 mod 状态应为 FULL"""
        result = install_mod(mock_game_root, game_info, mock_mod_root, basic_mappings)
        registry = load_registry(mock_game_root)
        assert get_mod_state(registry, result.mod_id) is ModState.FULL

    def test_install_idempotent_registry(self, mock_game_root, mock_mod_root, game_info, basic_mappings):
        """重复安装同一 mod 不应产生重复注册"""
        r1 = install_mod(mock_game_root, game_info, mock_mod_root, basic_mappings)
        r2 = install_mod(mock_game_root, game_info, mock_mod_root, basic_mappings)
        registry = load_registry(mock_game_root)
        assert r1.mod_id == r2.mod_id
        assert len(registry.mods) == 1

    def test_custom_display_name(self, mock_game_root, mock_mod_root, game_info, basic_mappings):
        result = install_mod(mock_game_root, game_info, mock_mod_root, basic_mappings,
                             display_name="鹰眼东线包")
        assert result.display_name == "鹰眼东线包"

    def test_multi_mod_overlay(self, mock_game_root, mock_mod_root, game_info, basic_mappings):
        """多 mod 叠加安装后 registry 正确记录所有归属"""
        r1 = install_mod(mock_game_root, game_info, mock_mod_root, basic_mappings)
        # 第二个 mod（用不同映射）
        mappings2 = [
            PathMapping("Hawkeye's PzC Map Enhancements (Non Desert)/Map",
                        "Map", "auto", "leaf_match"),
        ]
        r2 = install_mod(mock_game_root, game_info, mock_mod_root, mappings2,
                         mod_id="map_mod")
        registry = load_registry(mock_game_root)
        assert len(registry.mods) == 2
        assert r1.mod_id in registry.mods
        assert r2.mod_id in registry.mods


# ===========================================================================
# uninstall_mod
# ===========================================================================

class TestUninstallMod:
    def test_basic_uninstall(self, mock_game_root, mock_mod_root, game_info, basic_mappings):
        """卸载后文件恢复到原版"""
        # 记录原版内容
        original = (mock_game_root / "German" / "2DSymbolsLg.bmp").read_bytes()
        result = install_mod(mock_game_root, game_info, mock_mod_root, basic_mappings)
        # 确认已替换
        assert (mock_game_root / "German" / "2DSymbolsLg.bmp").read_bytes() != original
        # 卸载
        count = uninstall_mod(mock_game_root, game_info, result.mod_id)
        assert count > 0
        # 验证恢复
        assert (mock_game_root / "German" / "2DSymbolsLg.bmp").read_bytes() == original

    def test_registry_updated(self, mock_game_root, mock_mod_root, game_info, basic_mappings):
        """卸载后 registry 中 mod 状态应为 INACTIVE"""
        result = install_mod(mock_game_root, game_info, mock_mod_root, basic_mappings)
        uninstall_mod(mock_game_root, game_info, result.mod_id)
        registry = load_registry(mock_game_root)
        assert get_mod_state(registry, result.mod_id) is ModState.INACTIVE

    def test_uninstall_nonexistent(self, mock_game_root, game_info):
        """卸载不存在的 mod 不应报错"""
        count = uninstall_mod(mock_game_root, game_info, "ghost_mod")
        assert count == 0

    def test_info_files_restored(self, mock_game_root, mock_mod_root, game_info, basic_mappings):
        """Info/ 下的文件也应恢复"""
        original = (mock_game_root / "Info" / "BlankboxH.bmp").read_bytes()
        result = install_mod(mock_game_root, game_info, mock_mod_root, basic_mappings)
        uninstall_mod(mock_game_root, game_info, result.mod_id)
        assert (mock_game_root / "Info" / "BlankboxH.bmp").read_bytes() == original


# ===========================================================================
# switch_mod
# ===========================================================================

class TestSwitchMod:
    def test_disable(self, mock_game_root, mock_mod_root, game_info, basic_mappings):
        """switch --off 等同于 uninstall"""
        original = (mock_game_root / "German" / "2DSymbolsLg.bmp").read_bytes()
        result = install_mod(mock_game_root, game_info, mock_mod_root, basic_mappings)
        count = switch_mod(mock_game_root, game_info, result.mod_id, enable=False)
        assert count > 0
        assert (mock_game_root / "German" / "2DSymbolsLg.bmp").read_bytes() == original

    def test_enable_after_disable(self, mock_game_root, mock_mod_root, game_info, basic_mappings):
        """禁用后重新启用，文件应再次被 mod 覆盖"""
        result = install_mod(mock_game_root, game_info, mock_mod_root, basic_mappings)
        mod_content = (mock_game_root / "German" / "2DSymbolsLg.bmp").read_bytes()
        # 禁用
        switch_mod(mock_game_root, game_info, result.mod_id, enable=False)
        # 重新启用
        count = switch_mod(mock_game_root, game_info, result.mod_id, enable=True)
        assert count > 0
        assert (mock_game_root / "German" / "2DSymbolsLg.bmp").read_bytes() == mod_content

    def test_enable_updates_registry(self, mock_game_root, mock_mod_root, game_info, basic_mappings):
        """启用后 registry 状态应为 FULL"""
        result = install_mod(mock_game_root, game_info, mock_mod_root, basic_mappings)
        switch_mod(mock_game_root, game_info, result.mod_id, enable=False)
        switch_mod(mock_game_root, game_info, result.mod_id, enable=True)
        registry = load_registry(mock_game_root)
        assert get_mod_state(registry, result.mod_id) is ModState.FULL

    def test_switch_nonexistent(self, mock_game_root, game_info):
        count = switch_mod(mock_game_root, game_info, "ghost", enable=True)
        assert count == 0
