"""M06 registry.py 测试: 注册表管理"""

import json
from pathlib import Path

import pytest

from wds.models import (
    FileAttribution,
    GameRegistry,
    ModInfo,
    ModState,
    SourceVersion,
)
from wds.registry import (
    REGISTRY_FILENAME,
    get_mod_state,
    get_status_summary,
    init_registry,
    load_registry,
    register_mod,
    save_registry,
    switch_active_source,
    unregister_mod,
    update_file_attribution,
)


# ===========================================================================
# 辅助
# ===========================================================================

def _make_mod_info(mod_id: str = "test_mod", game_id: str = "EP14",
                   file_count: int = 10, active_count: int = 10) -> ModInfo:
    return ModInfo(
        mod_id=mod_id, game_id=game_id, display_name=f"Test {mod_id}",
        source_path=Path(f"/mods/{mod_id}"),
        install_time="2026-07-19T10:00:00+08:00",
        file_count=file_count, active_count=active_count,
    )


def _make_source(mod_id: str = "test_mod") -> SourceVersion:
    return SourceVersion(
        file_path=f"_backup/{mod_id}/German/2DSymbolsLg.bmp",
        hash="a" * 64,
        installed_at="2026-07-19T10:00:00+08:00",
    )


# ===========================================================================
# init_registry
# ===========================================================================

class TestInitRegistry:
    def test_creates_empty(self):
        r = init_registry("EP14")
        assert isinstance(r, GameRegistry)
        assert r.game_id == "EP14"
        assert r.mods == {}
        assert r.files == {}
        assert r.original_backup == ""

    def test_different_game_ids(self):
        r1 = init_registry("M41")
        r2 = init_registry("S43")
        assert r1.game_id == "M41"
        assert r2.game_id == "S43"


# ===========================================================================
# save / load 往返
# ===========================================================================

class TestSaveLoadRegistry:
    def test_save_creates_file(self, mock_game_root: Path):
        r = init_registry("EP14")
        save_registry(mock_game_root, r)
        path = mock_game_root / "_backup" / REGISTRY_FILENAME
        assert path.is_file()

    def test_save_creates_backup_dir(self, mock_game_root: Path):
        """_backup 不存在时应自动创建"""
        r = init_registry("EP14")
        save_registry(mock_game_root, r)
        assert (mock_game_root / "_backup").is_dir()

    def test_load_nonexistent_returns_none(self, mock_game_root: Path):
        assert load_registry(mock_game_root) is None

    def test_roundtrip(self, mock_game_root: Path):
        r = init_registry("EP14")
        register_mod(r, _make_mod_info())
        update_file_attribution(r, "German/2DSymbolsLg.bmp", "test_mod", _make_source())
        save_registry(mock_game_root, r)
        loaded = load_registry(mock_game_root)
        assert loaded is not None
        assert loaded == r

    def test_valid_json(self, mock_game_root: Path):
        r = init_registry("EP14")
        register_mod(r, _make_mod_info())
        save_registry(mock_game_root, r)
        path = mock_game_root / "_backup" / REGISTRY_FILENAME
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["game_id"] == "EP14"
        assert "test_mod" in data["mods"]

    def test_atomic_write(self, mock_game_root: Path):
        """写入后不应残留临时文件"""
        r = init_registry("EP14")
        save_registry(mock_game_root, r)
        backup_dir = mock_game_root / "_backup"
        temps = list(backup_dir.glob("*.tmp"))
        assert temps == []

    def test_overwrite_existing(self, mock_game_root: Path):
        r1 = init_registry("EP14")
        register_mod(r1, _make_mod_info("mod_a"))
        save_registry(mock_game_root, r1)

        r2 = load_registry(mock_game_root)
        register_mod(r2, _make_mod_info("mod_b"))
        save_registry(mock_game_root, r2)

        r3 = load_registry(mock_game_root)
        assert "mod_a" in r3.mods
        assert "mod_b" in r3.mods


# ===========================================================================
# register_mod / unregister_mod
# ===========================================================================

class TestRegisterMod:
    def test_register(self):
        r = init_registry("EP14")
        register_mod(r, _make_mod_info())
        assert "test_mod" in r.mods
        assert r.mods["test_mod"].display_name == "Test test_mod"

    def test_register_multiple(self):
        r = init_registry("EP14")
        register_mod(r, _make_mod_info("mod_a"))
        register_mod(r, _make_mod_info("mod_b"))
        assert len(r.mods) == 2

    def test_register_overwrites(self):
        r = init_registry("EP14")
        register_mod(r, _make_mod_info("test_mod", file_count=10))
        register_mod(r, _make_mod_info("test_mod", file_count=20))
        assert r.mods["test_mod"].file_count == 20


class TestUnregisterMod:
    def test_unregister(self):
        r = init_registry("EP14")
        register_mod(r, _make_mod_info())
        update_file_attribution(r, "German/2DSymbolsLg.bmp", "test_mod", _make_source())
        unregister_mod(r, "test_mod")
        assert "test_mod" not in r.mods

    def test_unregister_cleans_file_sources(self):
        """注销 mod 后，文件归属中该 mod 的 source 也应移除"""
        r = init_registry("EP14")
        register_mod(r, _make_mod_info())
        update_file_attribution(r, "German/2DSymbolsLg.bmp", "test_mod", _make_source())
        unregister_mod(r, "test_mod")
        fa = r.files.get("German/2DSymbolsLg.bmp")
        if fa is not None:
            assert "test_mod" not in fa.sources

    def test_unregister_nonexistent(self):
        """注销不存在的 mod 不应报错"""
        r = init_registry("EP14")
        unregister_mod(r, "ghost_mod")  # 不应抛异常

    def test_unregister_resets_active_source(self):
        """注销后，若该 mod 是某文件的 active_source，应重置为 None"""
        r = init_registry("EP14")
        register_mod(r, _make_mod_info())
        update_file_attribution(r, "German/2DSymbolsLg.bmp", "test_mod", _make_source())
        unregister_mod(r, "test_mod")
        fa = r.files.get("German/2DSymbolsLg.bmp")
        if fa is not None:
            assert fa.active_source is None


# ===========================================================================
# update_file_attribution
# ===========================================================================

class TestUpdateFileAttribution:
    def test_new_file(self):
        r = init_registry("EP14")
        register_mod(r, _make_mod_info())
        update_file_attribution(r, "German/2DSymbolsLg.bmp", "test_mod", _make_source())
        assert "German/2DSymbolsLg.bmp" in r.files
        fa = r.files["German/2DSymbolsLg.bmp"]
        assert fa.active_source == "test_mod"
        assert "test_mod" in fa.sources

    def test_second_mod_same_file(self):
        """第二个 mod 替换同一文件，active_source 应更新"""
        r = init_registry("EP14")
        register_mod(r, _make_mod_info("mod_a"))
        register_mod(r, _make_mod_info("mod_b"))
        update_file_attribution(r, "German/2DSymbolsLg.bmp", "mod_a", _make_source("mod_a"))
        update_file_attribution(r, "German/2DSymbolsLg.bmp", "mod_b", _make_source("mod_b"))
        fa = r.files["German/2DSymbolsLg.bmp"]
        assert fa.active_source == "mod_b"
        assert len(fa.sources) == 2

    def test_original_backup_set(self):
        r = init_registry("EP14")
        r.original_backup = "_backup/EP14_original"
        register_mod(r, _make_mod_info())
        update_file_attribution(r, "German/2DSymbolsLg.bmp", "test_mod", _make_source())
        fa = r.files["German/2DSymbolsLg.bmp"]
        assert fa.original_backup == "_backup/EP14_original/German/2DSymbolsLg.bmp"


# ===========================================================================
# switch_active_source
# ===========================================================================

class TestSwitchActiveSource:
    def test_switch_to_mod(self):
        r = init_registry("EP14")
        register_mod(r, _make_mod_info("mod_a"))
        register_mod(r, _make_mod_info("mod_b"))
        update_file_attribution(r, "German/2DSymbolsLg.bmp", "mod_a", _make_source("mod_a"))
        update_file_attribution(r, "German/2DSymbolsLg.bmp", "mod_b", _make_source("mod_b"))
        switch_active_source(r, "German/2DSymbolsLg.bmp", "mod_a")
        assert r.files["German/2DSymbolsLg.bmp"].active_source == "mod_a"

    def test_switch_to_none_rollback(self):
        r = init_registry("EP14")
        register_mod(r, _make_mod_info())
        update_file_attribution(r, "German/2DSymbolsLg.bmp", "test_mod", _make_source())
        switch_active_source(r, "German/2DSymbolsLg.bmp", None)
        assert r.files["German/2DSymbolsLg.bmp"].active_source is None

    def test_switch_nonexistent_file(self):
        """切换不存在的文件不应报错"""
        r = init_registry("EP14")
        switch_active_source(r, "NonExistent.bmp", "mod_a")  # 不应抛异常


# ===========================================================================
# get_mod_state
# ===========================================================================

class TestGetModState:
    def test_full(self):
        """所有文件都激活 → FULL"""
        r = init_registry("EP14")
        register_mod(r, _make_mod_info(file_count=2, active_count=2))
        update_file_attribution(r, "German/2DSymbolsLg.bmp", "test_mod", _make_source())
        update_file_attribution(r, "Info/BlankboxH.bmp", "test_mod", _make_source())
        assert get_mod_state(r, "test_mod") is ModState.FULL

    def test_partial(self):
        """部分文件被其他 mod 覆盖 → PARTIAL"""
        r = init_registry("EP14")
        register_mod(r, _make_mod_info("mod_a", file_count=2))
        register_mod(r, _make_mod_info("mod_b", file_count=1))
        update_file_attribution(r, "German/2DSymbolsLg.bmp", "mod_a", _make_source("mod_a"))
        update_file_attribution(r, "Info/BlankboxH.bmp", "mod_a", _make_source("mod_a"))
        # mod_b 覆盖了 mod_a 的一个文件
        update_file_attribution(r, "German/2DSymbolsLg.bmp", "mod_b", _make_source("mod_b"))
        assert get_mod_state(r, "mod_a") is ModState.PARTIAL

    def test_inactive(self):
        """所有文件都不激活 → INACTIVE"""
        r = init_registry("EP14")
        register_mod(r, _make_mod_info())
        update_file_attribution(r, "German/2DSymbolsLg.bmp", "test_mod", _make_source())
        switch_active_source(r, "German/2DSymbolsLg.bmp", None)
        assert get_mod_state(r, "test_mod") is ModState.INACTIVE

    def test_nonexistent_mod(self):
        r = init_registry("EP14")
        assert get_mod_state(r, "ghost") is ModState.INACTIVE

    def test_no_files_registered(self):
        """mod 已注册但无文件记录 → INACTIVE"""
        r = init_registry("EP14")
        register_mod(r, _make_mod_info(file_count=0, active_count=0))
        assert get_mod_state(r, "test_mod") is ModState.INACTIVE


# ===========================================================================
# get_status_summary
# ===========================================================================

class TestGetStatusSummary:
    def test_empty_registry(self):
        r = init_registry("EP14")
        assert get_status_summary(r) == []

    def test_single_mod(self):
        r = init_registry("EP14")
        register_mod(r, _make_mod_info(file_count=2, active_count=2))
        update_file_attribution(r, "German/2DSymbolsLg.bmp", "test_mod", _make_source())
        update_file_attribution(r, "Info/BlankboxH.bmp", "test_mod", _make_source())
        summary = get_status_summary(r)
        assert len(summary) == 1
        entry = summary[0]
        assert entry["mod_id"] == "test_mod"
        assert entry["state"] is ModState.FULL
        assert entry["active_count"] == 2
        assert entry["total_count"] == 2

    def test_multiple_mods(self):
        r = init_registry("EP14")
        register_mod(r, _make_mod_info("mod_a", file_count=2))
        register_mod(r, _make_mod_info("mod_b", file_count=1))
        update_file_attribution(r, "German/2DSymbolsLg.bmp", "mod_a", _make_source("mod_a"))
        update_file_attribution(r, "Info/BlankboxH.bmp", "mod_a", _make_source("mod_a"))
        update_file_attribution(r, "German/2DSymbolsLg.bmp", "mod_b", _make_source("mod_b"))
        summary = get_status_summary(r)
        assert len(summary) == 2
        by_id = {s["mod_id"]: s for s in summary}
        assert by_id["mod_a"]["state"] is ModState.PARTIAL
        assert by_id["mod_b"]["state"] is ModState.FULL

    def test_display_name_included(self):
        r = init_registry("EP14")
        register_mod(r, _make_mod_info())
        summary = get_status_summary(r)
        assert summary[0]["display_name"] == "Test test_mod"
