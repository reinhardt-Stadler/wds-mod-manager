"""M02 utils.py 测试: 纯函数 + Windows 路径处理"""

from pathlib import Path

import pytest

from wds.utils import (
    collect_all_files,
    collect_bmp_files,
    file_hash,
    game_id_from_name,
    is_excluded_dir,
    mod_id_from_filename,
    normalize_path,
)


# ===========================================================================
# file_hash
# ===========================================================================

class TestFileHash:
    def test_basic(self, tmp_path: Path):
        f = tmp_path / "test.txt"
        f.write_text("hello world", encoding="utf-8")
        h = file_hash(f)
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex length

    def test_deterministic(self, tmp_path: Path):
        f = tmp_path / "test.txt"
        f.write_text("deterministic content", encoding="utf-8")
        assert file_hash(f) == file_hash(f)

    def test_different_content_different_hash(self, tmp_path: Path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("content A", encoding="utf-8")
        f2.write_text("content B", encoding="utf-8")
        assert file_hash(f1) != file_hash(f2)

    def test_same_content_same_hash(self, tmp_path: Path):
        f1 = tmp_path / "a.bmp"
        f2 = tmp_path / "b.bmp"
        f1.write_bytes(b"\x00" * 100)
        f2.write_bytes(b"\x00" * 100)
        assert file_hash(f1) == file_hash(f2)

    def test_empty_file(self, tmp_path: Path):
        f = tmp_path / "empty.bmp"
        f.write_bytes(b"")
        h = file_hash(f)
        assert len(h) == 64

    def test_binary_file(self, tmp_path: Path):
        f = tmp_path / "binary.bmp"
        f.write_bytes(bytes(range(256)))
        h = file_hash(f)
        assert len(h) == 64

    def test_nonexistent_file_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            file_hash(tmp_path / "nonexistent.txt")


# ===========================================================================
# normalize_path
# ===========================================================================

class TestNormalizePath:
    def test_backslash_to_forward(self):
        assert normalize_path("German\\Units\\Infantry.bmp") == "German/Units/Infantry.bmp"

    def test_already_forward(self):
        assert normalize_path("German/Units/Infantry.bmp") == "German/Units/Infantry.bmp"

    def test_mixed_separators(self):
        assert normalize_path("German\\Units/Infantry.bmp") == "German/Units/Infantry.bmp"

    def test_strip_whitespace(self):
        assert normalize_path("  German/Units  ") == "German/Units"

    def test_empty_string(self):
        assert normalize_path("") == ""

    def test_single_component(self):
        assert normalize_path("German") == "German"

    def test_windows_absolute(self):
        result = normalize_path("D:\\WDS\\Moscow '41\\German")
        assert result == "D:/WDS/Moscow '41/German"

    def test_trailing_separator(self):
        result = normalize_path("German/Units/")
        assert result == "German/Units/"


# ===========================================================================
# game_id_from_name
# ===========================================================================

class TestGameIdFromName:
    def test_smolensk(self):
        assert game_id_from_name("Smolensk '43") == "S43"

    def test_moscow(self):
        assert game_id_from_name("Moscow '41") == "M41"

    def test_france(self):
        assert game_id_from_name("France 40") == "F40"

    def test_east_prussia_camelcase(self):
        assert game_id_from_name("EastPrussia' 14") == "EP14"

    def test_north_german_plain_multi_word(self):
        assert game_id_from_name("North German Plain '85") == "NGP85"

    def test_moscow_42(self):
        assert game_id_from_name("Moscow '42") == "M42"

    def test_poland(self):
        assert game_id_from_name("Poland '39") == "P39"

    def test_stalingrad(self):
        assert game_id_from_name("Stalingrad '42") == "S42"

    def test_donbas(self):
        assert game_id_from_name("Donbas '43") == "D43"

    def test_case_insensitive_input(self):
        assert game_id_from_name("smolensk '43") == "S43"

    def test_no_year_returns_name_upper(self):
        """无年份时取首字母大写"""
        result = game_id_from_name("Demo")
        assert result == "D"

    def test_campaign_vicksburg(self):
        assert game_id_from_name("Campaign Vicksburg") == "CV"


# ===========================================================================
# mod_id_from_filename
# ===========================================================================

class TestModIdFromFilename:
    def test_basic_zip(self):
        assert mod_id_from_filename("Hawkeyes_F40_Mod.zip") == "hawkeyes_f40"

    def test_without_mod_suffix(self):
        assert mod_id_from_filename("SomeCoolMod.zip") == "somecoolmod"

    def test_spaces_to_underscores(self):
        assert mod_id_from_filename("Hawkeye's B44 Mod.zip") == "hawkeye_s_b44"

    def test_directory_name(self):
        assert mod_id_from_filename("Hawkeyes_F40_Mod") == "hawkeyes_f40"

    def test_7z_extension(self):
        assert mod_id_from_filename("Jison's Style Mods New Titles Mods.7z") == "jison_s_style_mods_new_titles"

    def test_multiple_underscores_collapsed(self):
        assert mod_id_from_filename("My__Cool___Pack.zip") == "my_cool_pack"

    def test_special_characters(self):
        result = mod_id_from_filename("Mod (v2.0) [Final].zip")
        assert " " not in result
        assert result == result.lower()

    def test_empty_string(self):
        assert mod_id_from_filename("") == ""

    def test_only_extension(self):
        # ".zip" 被 Path 视为无扩展名的 dotfile，stem 为 ".zip" → 处理后为 "zip"
        assert mod_id_from_filename(".zip") == "zip"


# ===========================================================================
# is_excluded_dir
# ===========================================================================

class TestIsExcludedDir:
    @pytest.mark.parametrize("name", [
        "_backup", "Logs", "Saves", "Manuals", "Tools", "WDSEE",
    ])
    def test_excluded(self, name: str):
        assert is_excluded_dir(name) is True

    def test_sumatra_pdf(self):
        assert is_excluded_dir("SumatraPDF") is True

    @pytest.mark.parametrize("name", [
        "German", "Russian", "Info", "Map", "Media", "Data",
        "Screens", "Scenarios", "Units",
    ])
    def test_not_excluded(self, name: str):
        assert is_excluded_dir(name) is False

    def test_case_sensitive(self):
        """_backup 小写前缀是约定，大写不排除"""
        assert is_excluded_dir("_Backup") is False

    def test_backup_subfolder(self):
        """_backup 开头的都排除"""
        assert is_excluded_dir("_backup") is True


# ===========================================================================
# collect_bmp_files
# ===========================================================================

class TestCollectBmpFiles:
    def test_basic_collection(self, mock_game_root: Path):
        result = collect_bmp_files(mock_game_root)
        assert isinstance(result, dict)
        assert len(result) > 0
        # 所有 key 都是正斜杠相对路径
        for rel_path in result:
            assert "\\" not in rel_path
            assert rel_path.lower().endswith(".bmp")

    def test_includes_nation_bmps(self, mock_game_root: Path):
        result = collect_bmp_files(mock_game_root)
        assert "German/2DSymbolsLg.bmp" in result
        assert "Russian/2DSymbolsLg.bmp" in result

    def test_includes_units_bmps(self, mock_game_root: Path):
        result = collect_bmp_files(mock_game_root)
        assert "German/Units/Infantry.bmp" in result

    def test_includes_map_bmps(self, mock_game_root: Path):
        result = collect_bmp_files(mock_game_root)
        assert "Map/2DFeatures50.bmp" in result

    def test_includes_info_bmps(self, mock_game_root: Path):
        result = collect_bmp_files(mock_game_root)
        assert "Info/BlankboxH.bmp" in result

    def test_includes_screens_bmps(self, mock_game_root: Path):
        result = collect_bmp_files(mock_game_root)
        assert "Screens/AVictory.bmp" in result

    def test_excludes_backup_dir(self, mock_game_root: Path):
        # 手动创建 _backup 目录中的 BMP
        backup_bmp = mock_game_root / "_backup" / "test_mod" / "German" / "2DSymbolsLg.bmp"
        backup_bmp.parent.mkdir(parents=True)
        backup_bmp.write_text("backup", encoding="utf-8")
        result = collect_bmp_files(mock_game_root)
        for key in result:
            assert not key.startswith("_backup/")

    def test_excludes_logs_dir(self, mock_game_root: Path):
        log_bmp = mock_game_root / "Logs" / "screenshot.bmp"
        log_bmp.write_text("log", encoding="utf-8")
        result = collect_bmp_files(mock_game_root)
        assert "Logs/screenshot.bmp" not in result

    def test_values_are_absolute_paths(self, mock_game_root: Path):
        result = collect_bmp_files(mock_game_root)
        for abs_path in result.values():
            assert abs_path.is_absolute()
            assert abs_path.exists()

    def test_empty_directory(self, tmp_path: Path):
        empty = tmp_path / "empty"
        empty.mkdir()
        result = collect_bmp_files(empty)
        assert result == {}

    def test_case_insensitive_extension(self, mock_game_root: Path):
        """Flag.BMP (大写扩展名) 也应被收集"""
        result = collect_bmp_files(mock_game_root)
        bmp_keys = [k for k in result if k.lower().endswith(".bmp")]
        # mock 中有 Flag.BMP
        flag_keys = [k for k in bmp_keys if "Flag" in k]
        assert len(flag_keys) > 0


# ===========================================================================
# collect_all_files
# ===========================================================================

class TestCollectAllFiles:
    def test_all_files_no_filter(self, mock_game_root: Path):
        result = collect_all_files(mock_game_root)
        assert len(result) > 0
        # 应包含非 BMP 文件
        extensions = {Path(k).suffix.lower() for k in result}
        assert ".bmp" in extensions
        assert ".dat" in extensions or ".exe" in extensions

    def test_filter_by_extension(self, mock_game_root: Path):
        result = collect_all_files(mock_game_root, extensions={".exe"})
        assert len(result) > 0
        for key in result:
            assert key.lower().endswith(".exe")

    def test_filter_multiple_extensions(self, mock_game_root: Path):
        result = collect_all_files(mock_game_root, extensions={".oob", ".pdt"})
        for key in result:
            assert key.lower().endswith((".oob", ".pdt"))

    def test_excludes_backup_dir(self, mock_game_root: Path):
        backup_file = mock_game_root / "_backup" / "test" / "file.dat"
        backup_file.parent.mkdir(parents=True)
        backup_file.write_text("data", encoding="utf-8")
        result = collect_all_files(mock_game_root)
        for key in result:
            assert not key.startswith("_backup/")

    def test_empty_extensions_set(self, mock_game_root: Path):
        """空集合 = 不匹配任何文件"""
        result = collect_all_files(mock_game_root, extensions=set())
        assert result == {}

    def test_relative_paths_use_forward_slash(self, mock_game_root: Path):
        result = collect_all_files(mock_game_root)
        for key in result:
            assert "\\" not in key
