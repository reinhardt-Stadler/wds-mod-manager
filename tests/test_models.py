"""M01 models.py 测试: 构造 + JSON 序列化往返"""

import json
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from wds.models import (
    FileAttribution,
    FileStatus,
    GameInfo,
    GameRegistry,
    ModFileEntry,
    ModInfo,
    ModState,
    PathMapping,
    SourceVersion,
)


# ===========================================================================
# Enum 测试
# ===========================================================================

class TestFileStatus:
    def test_values(self):
        assert FileStatus.ORIGINAL.value == "original"
        assert FileStatus.REPLACED.value == "replaced"
        assert FileStatus.ROLLED_BACK.value == "rolled_back"
        assert FileStatus.MODIFIED.value == "modified"

    def test_from_value(self):
        assert FileStatus("replaced") is FileStatus.REPLACED

    def test_all_members(self):
        assert len(FileStatus) == 4


class TestModState:
    def test_values(self):
        assert ModState.FULL.value == "full"
        assert ModState.PARTIAL.value == "partial"
        assert ModState.INACTIVE.value == "inactive"

    def test_all_members(self):
        assert len(ModState) == 3


# ===========================================================================
# GameInfo
# ===========================================================================

class TestGameInfo:
    def _make(self) -> GameInfo:
        return GameInfo(
            game_id="EP14",
            full_name="EastPrussia' 14",
            root_path=Path("D:/WDS/EastPrussia' 14"),
            exe_name="eastprussia14.exe",
            nations=["German", "Russian", "Austro-Hungarian"],
            has_original_backup=False,
        )

    def test_construction(self):
        g = self._make()
        assert g.game_id == "EP14"
        assert g.nations == ["German", "Russian", "Austro-Hungarian"]
        assert isinstance(g.root_path, Path)
        assert g.has_original_backup is False

    def test_to_dict(self):
        d = self._make().to_dict()
        assert d["game_id"] == "EP14"
        assert d["root_path"] == "D:/WDS/EastPrussia' 14"
        assert isinstance(d["root_path"], str)
        assert d["nations"] == ["German", "Russian", "Austro-Hungarian"]

    def test_roundtrip(self):
        original = self._make()
        restored = GameInfo.from_dict(json.loads(json.dumps(original.to_dict())))
        assert restored == original

    def test_roundtrip_windows_path(self):
        g = GameInfo(
            game_id="M41",
            full_name="Moscow '41",
            root_path=PureWindowsPath("D:\\WDS\\PanzerCampain\\Moscow '41"),
            exe_name="moscow41.exe",
            nations=["German", "Russian"],
            has_original_backup=True,
        )
        d = g.to_dict()
        assert "\\" not in d["root_path"] or "/" in d["root_path"]
        restored = GameInfo.from_dict(d)
        assert restored.game_id == "M41"
        assert restored.has_original_backup is True


# ===========================================================================
# ModFileEntry
# ===========================================================================

class TestModFileEntry:
    def _make(self) -> ModFileEntry:
        return ModFileEntry(
            game_file="German/2DSymbolsLg.bmp",
            mod_file="Hawkeye's 2D Counters/German/2DSymbolsLg.bmp",
            backup_path="_backup/hawkeyes_f40/German/2DSymbolsLg.bmp",
            original_hash="a" * 64,
            mod_hash="b" * 64,
            status=FileStatus.REPLACED,
        )

    def test_construction(self):
        e = self._make()
        assert e.status is FileStatus.REPLACED
        assert e.game_file == "German/2DSymbolsLg.bmp"

    def test_to_dict_enum_serialized(self):
        d = self._make().to_dict()
        assert d["status"] == "replaced"

    def test_roundtrip(self):
        original = self._make()
        restored = ModFileEntry.from_dict(json.loads(json.dumps(original.to_dict())))
        assert restored == original

    def test_roundtrip_original_status(self):
        e = ModFileEntry(
            game_file="Info/BlankboxH.bmp",
            mod_file="Generic/Info/BlankboxH.bmp",
            backup_path="_backup/mod/Info/BlankboxH.bmp",
            original_hash="c" * 64,
            mod_hash="d" * 64,
            status=FileStatus.ORIGINAL,
        )
        restored = ModFileEntry.from_dict(e.to_dict())
        assert restored.status is FileStatus.ORIGINAL


# ===========================================================================
# ModInfo
# ===========================================================================

class TestModInfo:
    def _make(self) -> ModInfo:
        return ModInfo(
            mod_id="hawkeyes_f40",
            game_id="F40",
            display_name="Hawkeye's F40 Mod",
            source_path=Path("D:/Mods/Hawkeyes_F40_Mod"),
            install_time="2026-07-18T14:30:00+08:00",
            file_count=156,
            active_count=156,
        )

    def test_construction(self):
        m = self._make()
        assert m.mod_id == "hawkeyes_f40"
        assert m.file_count == 156
        assert isinstance(m.source_path, Path)

    def test_to_dict(self):
        d = self._make().to_dict()
        assert isinstance(d["source_path"], str)
        assert d["file_count"] == 156

    def test_roundtrip(self):
        original = self._make()
        restored = ModInfo.from_dict(json.loads(json.dumps(original.to_dict())))
        assert restored == original

    def test_partial_active(self):
        m = ModInfo(
            mod_id="test_mod",
            game_id="S43",
            display_name="Test",
            source_path=Path("/tmp/mod"),
            install_time="2026-07-19T10:00:00+08:00",
            file_count=100,
            active_count=45,
        )
        restored = ModInfo.from_dict(m.to_dict())
        assert restored.active_count == 45


# ===========================================================================
# PathMapping
# ===========================================================================

class TestPathMapping:
    def _make(self) -> PathMapping:
        return PathMapping(
            mod_subfolder="Hawkeye's PzC Map Enhancements (Non Desert)/Map",
            game_target="Map",
            confidence="auto",
            resolved_by="leaf_match",
        )

    def test_construction(self):
        p = self._make()
        assert p.confidence == "auto"
        assert p.resolved_by == "leaf_match"

    def test_roundtrip(self):
        original = self._make()
        restored = PathMapping.from_dict(json.loads(json.dumps(original.to_dict())))
        assert restored == original

    def test_user_confirmed(self):
        p = PathMapping(
            mod_subfolder="Some Mod/Map",
            game_target="Map/Hi-res Graphics/Hex Outline",
            confidence="user_confirmed",
            resolved_by="manual",
        )
        restored = PathMapping.from_dict(p.to_dict())
        assert restored.confidence == "user_confirmed"
        assert restored.resolved_by == "manual"


# ===========================================================================
# SourceVersion
# ===========================================================================

class TestSourceVersion:
    def _make(self) -> SourceVersion:
        return SourceVersion(
            file_path="_backup/hawkeyes_f40/German/2DSymbolsLg.bmp",
            hash="e" * 64,
            installed_at="2026-07-18T14:30:00+08:00",
        )

    def test_construction(self):
        s = self._make()
        assert s.hash == "e" * 64

    def test_roundtrip(self):
        original = self._make()
        restored = SourceVersion.from_dict(json.loads(json.dumps(original.to_dict())))
        assert restored == original


# ===========================================================================
# FileAttribution
# ===========================================================================

class TestFileAttribution:
    def _make(self) -> FileAttribution:
        return FileAttribution(
            original_backup="_backup/m41_original/German/2DSymbolsLg.bmp",
            active_source="hawkeyes_f40",
            sources={
                "hawkeyes_f40": SourceVersion(
                    file_path="_backup/hawkeyes_f40/German/2DSymbolsLg.bmp",
                    hash="a" * 64,
                    installed_at="2026-07-18T14:30:00+08:00",
                ),
                "another_mod": SourceVersion(
                    file_path="_backup/another_mod/German/2DSymbolsLg.bmp",
                    hash="b" * 64,
                    installed_at="2026-07-20T09:00:00+08:00",
                ),
            },
        )

    def test_construction(self):
        fa = self._make()
        assert fa.active_source == "hawkeyes_f40"
        assert len(fa.sources) == 2
        assert isinstance(fa.sources["hawkeyes_f40"], SourceVersion)

    def test_active_source_none(self):
        fa = FileAttribution(
            original_backup="_backup/orig/Info/BlankboxH.bmp",
            active_source=None,
            sources={},
        )
        assert fa.active_source is None
        d = fa.to_dict()
        assert d["active_source"] is None
        restored = FileAttribution.from_dict(d)
        assert restored.active_source is None

    def test_roundtrip(self):
        original = self._make()
        restored = FileAttribution.from_dict(
            json.loads(json.dumps(original.to_dict()))
        )
        assert restored == original
        assert isinstance(restored.sources["another_mod"], SourceVersion)


# ===========================================================================
# GameRegistry (顶层持久化对象)
# ===========================================================================

class TestGameRegistry:
    def _make(self) -> GameRegistry:
        return GameRegistry(
            game_id="M41",
            mods={
                "hawkeyes_f40": ModInfo(
                    mod_id="hawkeyes_f40",
                    game_id="M41",
                    display_name="Hawkeye's F40 Mod",
                    source_path=Path("D:/Mods/Hawkeyes_F40_Mod"),
                    install_time="2026-07-18T14:30:00+08:00",
                    file_count=156,
                    active_count=156,
                ),
            },
            files={
                "German/2DSymbolsLg.bmp": FileAttribution(
                    original_backup="_backup/m41_original/German/2DSymbolsLg.bmp",
                    active_source="hawkeyes_f40",
                    sources={
                        "hawkeyes_f40": SourceVersion(
                            file_path="_backup/hawkeyes_f40/German/2DSymbolsLg.bmp",
                            hash="a" * 64,
                            installed_at="2026-07-18T14:30:00+08:00",
                        ),
                    },
                ),
            },
            original_backup="_backup/m41_original",
        )

    def test_construction(self):
        r = self._make()
        assert r.game_id == "M41"
        assert "hawkeyes_f40" in r.mods
        assert "German/2DSymbolsLg.bmp" in r.files
        assert isinstance(r.mods["hawkeyes_f40"], ModInfo)
        assert isinstance(r.files["German/2DSymbolsLg.bmp"], FileAttribution)

    def test_empty_registry(self):
        r = GameRegistry(
            game_id="S43",
            mods={},
            files={},
            original_backup="",
        )
        d = r.to_dict()
        assert d["mods"] == {}
        assert d["files"] == {}
        restored = GameRegistry.from_dict(d)
        assert restored.mods == {}

    def test_roundtrip(self):
        original = self._make()
        json_str = json.dumps(original.to_dict(), ensure_ascii=False, indent=2)
        restored = GameRegistry.from_dict(json.loads(json_str))
        assert restored == original

    def test_roundtrip_preserves_nested_types(self):
        original = self._make()
        restored = GameRegistry.from_dict(
            json.loads(json.dumps(original.to_dict()))
        )
        mod = restored.mods["hawkeyes_f40"]
        assert isinstance(mod, ModInfo)
        assert isinstance(mod.source_path, Path)
        fa = restored.files["German/2DSymbolsLg.bmp"]
        assert isinstance(fa, FileAttribution)
        assert isinstance(fa.sources["hawkeyes_f40"], SourceVersion)

    def test_json_serializable(self):
        """整个 registry 可以直接 json.dumps 不报错"""
        r = self._make()
        json_str = json.dumps(r.to_dict(), ensure_ascii=False)
        assert "hawkeyes_f40" in json_str
        assert "M41" in json_str

    def test_multiple_mods_same_file(self):
        """同一文件被多个 mod 覆盖的场景"""
        r = GameRegistry(
            game_id="M41",
            mods={
                "mod_a": ModInfo("mod_a", "M41", "Mod A", Path("/a"),
                                 "2026-07-18T10:00:00+08:00", 50, 50),
                "mod_b": ModInfo("mod_b", "M41", "Mod B", Path("/b"),
                                 "2026-07-19T10:00:00+08:00", 30, 20),
            },
            files={
                "German/2DSymbolsLg.bmp": FileAttribution(
                    original_backup="_backup/orig/German/2DSymbolsLg.bmp",
                    active_source="mod_a",
                    sources={
                        "mod_a": SourceVersion("_backup/mod_a/German/2DSymbolsLg.bmp",
                                               "a" * 64, "2026-07-18T10:00:00+08:00"),
                        "mod_b": SourceVersion("_backup/mod_b/German/2DSymbolsLg.bmp",
                                               "b" * 64, "2026-07-19T10:00:00+08:00"),
                    },
                ),
            },
            original_backup="_backup/m41_original",
        )
        restored = GameRegistry.from_dict(json.loads(json.dumps(r.to_dict())))
        fa = restored.files["German/2DSymbolsLg.bmp"]
        assert fa.active_source == "mod_a"
        assert len(fa.sources) == 2
        assert restored.mods["mod_b"].active_count == 20
