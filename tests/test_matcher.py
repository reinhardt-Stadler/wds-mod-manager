"""M04 matcher.py 测试: 路径匹配引擎"""

from pathlib import Path

import pytest

from wds.matcher import (
    build_game_categories,
    build_game_index,
    detect_game_from_mod,
    disambiguate,
    normalize_category_name,
    resolve_target,
    scan_mod,
)
from wds.models import GameInfo


# ===========================================================================
# build_game_index
# ===========================================================================

class TestBuildGameIndex:
    def test_basic(self, mock_game_root: Path):
        index = build_game_index(mock_game_root)
        assert isinstance(index, dict)
        assert len(index) > 0

    def test_filename_keys(self, mock_game_root: Path):
        """key 是小写纯文件名（不含路径，大小写不敏感）"""
        index = build_game_index(mock_game_root)
        assert "2dsymbolslg.bmp" in index
        assert "infantry.bmp" in index
        assert "blankboxh.bmp" in index

    def test_values_are_relative_paths(self, mock_game_root: Path):
        """value 是包含此文件的相对路径列表（原始大小写）"""
        index = build_game_index(mock_game_root)
        paths = index["2dsymbolslg.bmp"]
        assert isinstance(paths, list)
        assert len(paths) >= 3  # German/, Russian/, Map/ 等
        for p in paths:
            assert "\\" not in p  # 正斜杠

    def test_same_file_multiple_locations(self, mock_game_root: Path):
        """2DSymbolsLg.bmp 应出现在多个路径（值为原始大小写）"""
        index = build_game_index(mock_game_root)
        paths = index["2dsymbolslg.bmp"]
        assert "German/2DSymbolsLg.bmp" in paths
        assert "Russian/2DSymbolsLg.bmp" in paths
        assert "Map/2DSymbolsLg.bmp" in paths

    def test_unique_file_single_path(self, mock_game_root: Path):
        """唯一文件只有一个路径（值为原始大小写）"""
        index = build_game_index(mock_game_root)
        assert len(index["blankboxh.bmp"]) == 1
        assert index["blankboxh.bmp"][0] == "Info/BlankboxH.bmp"

    def test_excludes_backup(self, mock_game_root: Path):
        """_backup 下的文件不应出现在索引中"""
        backup_bmp = mock_game_root / "_backup" / "mod" / "German" / "FakeFile.bmp"
        backup_bmp.parent.mkdir(parents=True)
        backup_bmp.write_text("fake")
        index = build_game_index(mock_game_root)
        assert "fakefile.bmp" not in index

    def test_excludes_logs(self, mock_game_root: Path):
        log_bmp = mock_game_root / "Logs" / "screenshot.bmp"
        log_bmp.write_text("log")
        index = build_game_index(mock_game_root)
        assert "screenshot.bmp" not in index

    def test_case_insensitive_bmp(self, mock_game_root: Path):
        """Flag.BMP (大写扩展名) 也应被索引为小写键"""
        index = build_game_index(mock_game_root)
        assert "flag.bmp" in index
        # 值保留原始大小写
        assert any("Flag.BMP" in p for p in index["flag.bmp"])


# ===========================================================================
# normalize_category_name (D-014)
# ===========================================================================

class TestNormalizeCategoryName:
    def test_lowercase(self):
        assert normalize_category_name("German") == "german"

    def test_strips_hyphen(self):
        """连字符被去除: 'East-German' → 'eastgerman'"""
        assert normalize_category_name("East-German") == "eastgerman"

    def test_strips_space(self):
        """空格被去除: 'East German' → 'eastgerman'"""
        assert normalize_category_name("East German") == "eastgerman"

    def test_strips_underscore(self):
        assert normalize_category_name("east_german") == "eastgerman"

    def test_all_equivalent(self):
        """不同写法归一为同一结果"""
        variants = ["East-German", "East German", "east_german", "EAST GERMAN"]
        results = {normalize_category_name(v) for v in variants}
        assert len(results) == 1

    def test_keeps_digits(self):
        assert normalize_category_name("Map50") == "map50"

    def test_austro_hungarian(self):
        assert normalize_category_name("Austro-Hungarian") == "austrohungarian"


# ===========================================================================
# build_game_categories (D-014)
# ===========================================================================

class TestBuildGameCategories:
    def test_returns_dict(self, mock_game_root: Path):
        cats = build_game_categories(mock_game_root)
        assert isinstance(cats, dict)
        assert len(cats) > 0

    def test_nation_categories(self, mock_game_root: Path):
        """国家文件夹应出现在类别中"""
        cats = build_game_categories(mock_game_root)
        assert cats["german"] == "German"
        assert cats["russian"] == "Russian"
        assert cats["austrohungarian"] == "Austro-Hungarian"

    def test_functional_categories(self, mock_game_root: Path):
        """功能目录 (Map/Info/Screens 等) 也是类别"""
        cats = build_game_categories(mock_game_root)
        assert cats["map"] == "Map"
        assert cats["info"] == "Info"
        assert cats["screens"] == "Screens"

    def test_excludes_backup(self, mock_game_root: Path):
        """_backup 不应出现在类别中"""
        cats = build_game_categories(mock_game_root)
        assert "backup" not in cats

    def test_excludes_logs_saves_manuals(self, mock_game_root: Path):
        """is_excluded_dir 排除的目录不应出现"""
        cats = build_game_categories(mock_game_root)
        assert "logs" not in cats
        assert "saves" not in cats
        assert "manuals" not in cats

    def test_nonexistent_dir(self, tmp_path: Path):
        """不存在的目录返回空 dict"""
        cats = build_game_categories(tmp_path / "nonexistent")
        assert cats == {}


# ===========================================================================
# 类别优先匹配 (D-014) — 通过 scan_mod 验证
# ===========================================================================

class TestCategoryFirstMatching:
    @pytest.fixture
    def game_info(self, mock_game_root: Path) -> GameInfo:
        return GameInfo(
            game_id="EP14",
            full_name="EastPrussia' 14",
            root_path=mock_game_root,
            exe_name="eastprussia14.exe",
            nations=["German", "Russian", "Austro-Hungarian"],
            has_original_backup=False,
        )

    def test_nation_folder_maps_to_same_nation(self, mock_mod_root, game_info):
        """mod 国家文件夹中的文件应映射到游戏同名国家文件夹"""
        result = scan_mod(mock_mod_root, game_info)
        # German/2DSymbolsLg.bmp → German/2DSymbolsLg.bmp
        german = [(m, g, c) for m, g, c in result
                  if "German/2DSymbolsLg" in m]
        assert len(german) >= 1
        for _, target, conf in german:
            assert target == "German/2DSymbolsLg.bmp"
            assert conf == "auto"

    def test_case_insensitive_filename_within_category(self, mock_mod_root, game_info):
        """类别内文件名大小写不敏感: mod UnitBox.bmp → 游戏 Unitbox.bmp"""
        result = scan_mod(mock_mod_root, game_info)
        # mod 有 UnitBox.bmp (大写B)，游戏有 Unitbox.bmp (小写b)
        unitbox = [(m, g, c) for m, g, c in result
                   if "UnitBox.bmp" in m or "Unitbox.bmp" in m]
        assert len(unitbox) >= 1
        for _, target, conf in unitbox:
            assert target is not None
            assert target.lower().endswith("unitbox.bmp")
            assert conf == "auto"

    def test_flag_bmp_case_insensitive(self, mock_mod_root, game_info):
        """mod Flag.bmp → 游戏 Flag.BMP（扩展名大小写不同）"""
        result = scan_mod(mock_mod_root, game_info)
        flag = [(m, g, c) for m, g, c in result if "Flag" in m]
        assert len(flag) >= 1
        for _, target, conf in flag:
            assert target is not None
            assert target.lower().endswith("flag.bmp")
            assert conf == "auto"

    def test_category_match_but_file_absent_is_unmatched(self, mock_mod_root, game_info):
        """类别匹配但游戏该类别下无此文件 → unmatched"""
        extra = mock_mod_root / "Extra" / "German" / "TotallyNew.bmp"
        extra.parent.mkdir(parents=True)
        extra.write_text("new")
        result = scan_mod(mock_mod_root, game_info)
        unmatched = [(m, g, c) for m, g, c in result if "TotallyNew" in m]
        assert len(unmatched) == 1
        assert unmatched[0][1] is None
        assert unmatched[0][2] == "unmatched"

    def test_decorative_wrapper_stripped(self, mock_mod_root, game_info):
        """装饰层前缀被剥离，类别匹配仍生效"""
        result = scan_mod(mock_mod_root, game_info)
        # "Hawkeye's 2D Counters (EastPrussia 14)/Russian/..." → Russian/...
        russian = [(m, g, c) for m, g, c in result
                   if "Russian/2DSymbolsLg" in m]
        assert len(russian) >= 1
        for _, target, conf in russian:
            assert target == "Russian/2DSymbolsLg.bmp"
            assert conf == "auto"

    def test_normalized_category_name_match(self, tmp_path, game_info):
        """规范化类别名匹配: mod 'East-German' 风格不直接测试，
        但验证带连字符的 Austro-Hungarian 能匹配游戏的 Austro-Hungarian"""
        mod = tmp_path / "TestMod"
        mod.mkdir()
        nation = mod / "Austro-Hungarian"
        nation.mkdir()
        (nation / "2DSymbolsLg.bmp").write_text("x")
        result = scan_mod(mod, game_info)
        assert len(result) == 1
        assert result[0][1] == "Austro-Hungarian/2DSymbolsLg.bmp"
        assert result[0][2] == "auto"

    def test_loose_root_file_uses_filename_fallback(self, tmp_path, game_info):
        """无类别文件夹的散装文件回退到文件名匹配"""
        mod = tmp_path / "LooseMod"
        mod.mkdir()
        # 直接放在 mod 根目录，无任何类别文件夹
        (mod / "BlankboxH.bmp").write_text("x")
        result = scan_mod(mod, game_info)
        assert len(result) == 1
        # 文件名回退: BlankboxH.bmp 唯一 → Info/BlankboxH.bmp
        assert result[0][1] == "Info/BlankboxH.bmp"
        assert result[0][2] == "auto"


# ===========================================================================
# resolve_target
# ===========================================================================

class TestResolveTarget:
    @pytest.fixture
    def game_index(self, mock_game_root: Path) -> dict:
        return build_game_index(mock_game_root)

    def test_direct_nation_match(self, game_index, mock_game_root):
        """mod 中 German/2DSymbolsLg.bmp → 游戏 German/2DSymbolsLg.bmp"""
        result = resolve_target(
            "Hawkeye's 2D Counters/German/2DSymbolsLg.bmp",
            game_index, mock_game_root,
        )
        assert result == "German/2DSymbolsLg.bmp"

    def test_units_subfolder_match(self, game_index, mock_game_root):
        """mod 中 German/Units/Infantry.bmp → 游戏 German/Units/Infantry.bmp"""
        result = resolve_target(
            "Hawkeye's 2D Counters/German/Units/Infantry.bmp",
            game_index, mock_game_root,
        )
        assert result == "German/Units/Infantry.bmp"

    def test_info_match(self, game_index, mock_game_root):
        """mod 中 Info/BlankboxH.bmp → 游戏 Info/BlankboxH.bmp"""
        result = resolve_target(
            "Generic MapMod/Info/BlankboxH.bmp",
            game_index, mock_game_root,
        )
        assert result == "Info/BlankboxH.bmp"

    def test_screens_match(self, game_index, mock_game_root):
        """mod 中 Screens/PhaseBox.BMP → 游戏 Screens/PhaseBox.BMP"""
        result = resolve_target(
            "Generic MapMod/Screens/PhaseBox.BMP",
            game_index, mock_game_root,
        )
        assert result == "Screens/PhaseBox.BMP"

    def test_map_disambiguation(self, game_index, mock_game_root, mock_mod_root):
        """Map/2DFeatures50.bmp 有多个候选，应通过交集消歧选择 Map/ 根"""
        result = resolve_target(
            "Hawkeye's PzC Map Enhancements (Non Desert)/Map/2DFeatures50.bmp",
            game_index, mock_game_root,
            mod_root=mock_mod_root,
        )
        assert result == "Map/2DFeatures50.bmp"

    def test_no_match_returns_none(self, game_index, mock_game_root):
        """游戏中不存在的文件应返回 None"""
        result = resolve_target(
            "Some Mod/German/NonExistentFile.bmp",
            game_index, mock_game_root,
        )
        assert result is None

    def test_deep_decorative_layers(self, game_index, mock_game_root):
        """多层装饰前缀应被正确剥离"""
        result = resolve_target(
            "Layer1/Layer2/Layer3/German/2DSymbolsLg.bmp",
            game_index, mock_game_root,
        )
        assert result == "German/2DSymbolsLg.bmp"

    def test_already_relative_path(self, game_index, mock_game_root):
        """已经是游戏相对路径的情况"""
        result = resolve_target(
            "Info/BlankboxH.bmp",
            game_index, mock_game_root,
        )
        assert result == "Info/BlankboxH.bmp"


# ===========================================================================
# disambiguate
# ===========================================================================

class TestDisambiguate:
    def test_picks_best_intersection(self, mock_game_root, mock_mod_root):
        """mod Map/ 目录文件集与游戏 Map/ 根交集最大"""
        candidates = [
            "Map/2DFeatures50.bmp",
            "Map/Hex Outline/2DFeatures50.bmp",
            "Map/No Hex Outline/2DFeatures50.bmp",
        ]
        result = disambiguate(
            "Hawkeye's PzC Map Enhancements (Non Desert)/Map/2DFeatures50.bmp",
            mock_mod_root,
            candidates,
            mock_game_root,
        )
        assert result == "Map/2DFeatures50.bmp"

    def test_returns_none_when_no_clear_winner(self, mock_game_root, tmp_path):
        """交集都不超过阈值时返回 None"""
        # 创建一个 mod 目录，文件集与任何候选都不匹配
        mod = tmp_path / "weird_mod"
        weird = mod / "WeirdFolder"
        weird.mkdir(parents=True)
        (weird / "totally_unique_1.bmp").write_text("x")
        (weird / "totally_unique_2.bmp").write_text("x")

        candidates = [
            "Map/2DFeatures50.bmp",
            "Map/Hex Outline/2DFeatures50.bmp",
        ]
        result = disambiguate(
            "WeirdFolder/totally_unique_1.bmp",
            mod,
            candidates,
            mock_game_root,
        )
        assert result is None

    def test_single_candidate_returned(self, mock_game_root, mock_mod_root):
        """只有一个候选时直接返回"""
        result = disambiguate(
            "Generic/Info/BlankboxH.bmp",
            mock_mod_root,
            ["Info/BlankboxH.bmp"],
            mock_game_root,
        )
        assert result == "Info/BlankboxH.bmp"


# ===========================================================================
# scan_mod
# ===========================================================================

class TestScanMod:
    @pytest.fixture
    def game_info(self, mock_game_root: Path) -> GameInfo:
        return GameInfo(
            game_id="EP14",
            full_name="EastPrussia' 14",
            root_path=mock_game_root,
            exe_name="eastprussia14.exe",
            nations=["German", "Russian", "Austro-Hungarian"],
            has_original_backup=False,
        )

    def test_returns_list_of_tuples(self, mock_mod_root, game_info):
        result = scan_mod(mock_mod_root, game_info)
        assert isinstance(result, list)
        assert len(result) > 0
        for item in result:
            assert len(item) == 3  # (mod_file, game_target, confidence)

    def test_auto_confidence(self, mock_mod_root, game_info):
        """明确匹配的文件应标记为 auto"""
        result = scan_mod(mock_mod_root, game_info)
        auto_entries = [(m, g, c) for m, g, c in result if c == "auto"]
        assert len(auto_entries) > 0
        # Info/BlankboxH.bmp 应该是 auto
        info_entries = [e for e in auto_entries if "BlankboxH" in e[0]]
        assert len(info_entries) == 1
        assert info_entries[0][1] == "Info/BlankboxH.bmp"

    def test_nation_files_matched(self, mock_mod_root, game_info):
        """国家文件夹中的文件应被正确匹配"""
        result = scan_mod(mock_mod_root, game_info)
        german_entries = [(m, g, c) for m, g, c in result
                          if "German/2DSymbolsLg" in m]
        assert len(german_entries) >= 1
        matched = [e for e in german_entries if e[1] == "German/2DSymbolsLg.bmp"]
        assert len(matched) >= 1

    def test_unmatched_files(self, mock_mod_root, game_info):
        """游戏中不存在的文件应标记为 unmatched"""
        # 在 mod 中创建一个游戏没有的文件
        extra = mock_mod_root / "Extra" / "German" / "TotallyNew.bmp"
        extra.parent.mkdir(parents=True)
        extra.write_text("new")
        result = scan_mod(mock_mod_root, game_info)
        unmatched = [(m, g, c) for m, g, c in result if c == "unmatched"]
        assert any("TotallyNew" in m for m, _, _ in unmatched)

    def test_all_mod_bmps_accounted(self, mock_mod_root, game_info):
        """mod 中所有 BMP 都应出现在结果中"""
        from wds.utils import collect_bmp_files
        mod_bmps = collect_bmp_files(mock_mod_root)
        result = scan_mod(mock_mod_root, game_info)
        assert len(result) == len(mod_bmps)

    def test_map_files_disambiguated(self, mock_mod_root, game_info):
        """Map/ 下的文件应通过消歧匹配到 Map/ 根"""
        result = scan_mod(mock_mod_root, game_info)
        map_entries = [(m, g, c) for m, g, c in result
                       if "Map Enhancements" in m and g is not None]
        for _, game_target, _ in map_entries:
            assert game_target.startswith("Map/"), f"Expected Map/ prefix, got {game_target}"


# ===========================================================================
# detect_game_from_mod
# ===========================================================================

class TestDetectGameFromMod:
    @pytest.fixture
    def known_games(self) -> list[GameInfo]:
        return [
            GameInfo("EP14", "EastPrussia' 14", Path("/games/EP14"),
                     "eastprussia14.exe",
                     ["German", "Russian", "Austro-Hungarian"], False),
            GameInfo("M41", "Moscow '41", Path("/games/M41"),
                     "moscow41.exe",
                     ["German", "Russian", "NKVD", "Belgian"], False),
            GameInfo("F40", "France 40", Path("/games/F40"),
                     "france40.exe",
                     ["German", "French", "British", "Belgian"], False),
            GameInfo("S43", "Smolensk '43", Path("/games/S43"),
                     "smolensk43.exe",
                     ["German", "Russian"], False),
        ]

    def test_filename_match(self, tmp_path, known_games):
        """zip 文件名含游戏缩写 → 直接匹配"""
        mod = tmp_path / "Hawkeyes_F40_Mod"
        mod.mkdir()
        (mod / "German").mkdir()
        results = detect_game_from_mod(mod, known_games)
        assert len(results) >= 1
        assert results[0][0].game_id == "F40"
        assert "文件名" in results[0][1] or "filename" in results[0][1].lower()

    def test_nation_inference(self, tmp_path, known_games):
        """无文件名线索时，用阵营名推断"""
        mod = tmp_path / "Unknown Mod Pack"
        mod.mkdir()
        # NKVD 只在 M41 中有
        (mod / "NKVD").mkdir()
        (mod / "German").mkdir()
        results = detect_game_from_mod(mod, known_games)
        assert len(results) >= 1
        # M41 应排在前面（NKVD 是独有阵营）
        assert results[0][0].game_id == "M41"

    def test_no_match_returns_empty(self, tmp_path, known_games):
        """完全无法匹配时返回空列表"""
        mod = tmp_path / "Random Stuff"
        mod.mkdir()
        (mod / "Aliens").mkdir()
        (mod / "Predators").mkdir()
        results = detect_game_from_mod(mod, known_games)
        assert results == []

    def test_multiple_candidates_sorted(self, tmp_path, known_games):
        """多个候选按匹配度排序"""
        mod = tmp_path / "Generic Mod"
        mod.mkdir()
        # German + Russian 在多个游戏中都有
        (mod / "German").mkdir()
        (mod / "Russian").mkdir()
        results = detect_game_from_mod(mod, known_games)
        assert len(results) >= 2

    def test_austro_hungarian_unique(self, tmp_path, known_games):
        """Austro-Hungarian 只在 EP14 中有"""
        mod = tmp_path / "WW1 Mod"
        mod.mkdir()
        (mod / "Austro-Hungarian").mkdir()
        results = detect_game_from_mod(mod, known_games)
        assert len(results) >= 1
        assert results[0][0].game_id == "EP14"

    def test_mod_root_not_dir(self, tmp_path, known_games):
        """mod 路径不存在时返回空列表"""
        results = detect_game_from_mod(tmp_path / "nonexistent", known_games)
        assert results == []


# ===========================================================================
# 冒烟测试
# ===========================================================================

@pytest.mark.smoke
class TestSmokeMatcher:
    @pytest.fixture
    def real_wds_root(self, pytestconfig) -> Path:
        root = Path(pytestconfig.getoption("--wds-root", default="D:\\WDS"))
        if not root.is_dir():
            pytest.skip(f"WDS 根目录不存在: {root}")
        return root

    def test_build_index_real(self, real_wds_root):
        from wds.scanner import discover_games
        games = discover_games(real_wds_root)
        if games:
            index = build_game_index(games[0].root_path)
            assert len(index) > 0
