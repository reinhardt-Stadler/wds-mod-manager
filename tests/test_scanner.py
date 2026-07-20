"""M03 scanner.py 测试: 游戏发现 + 阵营检测 + 主 exe 识别"""

from pathlib import Path

import pytest

from wds.models import GameInfo
from wds.scanner import detect_main_exe, detect_nations, discover_games


# ===========================================================================
# discover_games
# ===========================================================================

class TestDiscoverGames:
    def test_finds_all_games(self, mock_wds_root: Path):
        """应发现 3 个游戏: EastPrussia '14, Moscow '41, Smolensk '43"""
        games = discover_games(mock_wds_root)
        game_ids = {g.game_id for g in games}
        assert len(games) == 3
        assert "EP14" in game_ids
        assert "M41" in game_ids
        assert "S43" in game_ids

    def test_returns_gameinfo_instances(self, mock_wds_root: Path):
        games = discover_games(mock_wds_root)
        for g in games:
            assert isinstance(g, GameInfo)

    def test_game_has_correct_fields(self, mock_wds_root: Path):
        games = discover_games(mock_wds_root)
        ep14 = next(g for g in games if g.game_id == "EP14")
        assert ep14.full_name == "EastPrussia' 14"
        assert ep14.exe_name == "eastprussia14.exe"
        assert ep14.root_path.is_dir()
        assert isinstance(ep14.nations, list)

    def test_nested_category_folder(self, mock_wds_root: Path):
        """分类文件夹 PanzerCampain/ 下的游戏应被发现"""
        games = discover_games(mock_wds_root)
        m41 = next(g for g in games if g.game_id == "M41")
        assert "PanzerCampain" in str(m41.root_path)

    def test_does_not_detect_menu_as_game(self, mock_wds_root: Path):
        """menu/ 目录（有 exe 无 Data/）不应被识别为游戏"""
        games = discover_games(mock_wds_root)
        names = {g.full_name for g in games}
        assert "menu" not in names

    def test_does_not_detect_scenario_documents(self, mock_wds_root: Path):
        """Scenario Documents 目录不应被识别为游戏"""
        games = discover_games(mock_wds_root)
        for g in games:
            assert "Scenario Documents" not in g.full_name

    def test_does_not_detect_mod_zip(self, mock_wds_root: Path):
        """zip 文件不应被识别为游戏"""
        games = discover_games(mock_wds_root)
        for g in games:
            assert "Hawkeyes" not in g.full_name

    def test_nations_detected(self, mock_wds_root: Path):
        """发现的游戏中应包含阵营信息"""
        games = discover_games(mock_wds_root)
        ep14 = next(g for g in games if g.game_id == "EP14")
        assert "German" in ep14.nations
        assert "Russian" in ep14.nations

    def test_m41_has_nkvd(self, mock_wds_root: Path):
        """Moscow '41 应有 NKVD 阵营"""
        games = discover_games(mock_wds_root)
        m41 = next(g for g in games if g.game_id == "M41")
        assert "NKVD" in m41.nations

    def test_has_original_backup_false(self, mock_wds_root: Path):
        """mock 环境中无 _backup，has_original_backup 应为 False"""
        games = discover_games(mock_wds_root)
        for g in games:
            assert g.has_original_backup is False

    def test_has_original_backup_true(self, mock_wds_root: Path):
        """创建 _backup/EP14_original/ 后应检测到"""
        ep14 = mock_wds_root / "EastPrussia' 14"
        (ep14 / "_backup" / "EP14_original").mkdir(parents=True)
        games = discover_games(mock_wds_root)
        ep14_info = next(g for g in games if g.game_id == "EP14")
        assert ep14_info.has_original_backup is True

    def test_empty_root(self, tmp_path: Path):
        """空目录返回空列表"""
        empty = tmp_path / "empty_wds"
        empty.mkdir()
        assert discover_games(empty) == []

    def test_nonexistent_root(self, tmp_path: Path):
        """不存在的目录返回空列表"""
        assert discover_games(tmp_path / "nonexistent") == []

    def test_max_depth_3(self, mock_wds_root: Path):
        """超过 3 层深度的游戏不应被发现"""
        deep = mock_wds_root / "a" / "b" / "c" / "DeepGame"
        deep.mkdir(parents=True)
        (deep / "Data").mkdir()
        (deep / "deepgame.exe").write_text("exe")
        games = discover_games(mock_wds_root)
        for g in games:
            assert "DeepGame" not in g.full_name

    def test_excludes_backup_dir(self, mock_wds_root: Path):
        """_backup 目录下的内容不应被扫描"""
        ep14 = mock_wds_root / "EastPrussia' 14"
        fake = ep14 / "_backup" / "FakeGame"
        fake.mkdir(parents=True)
        (fake / "Data").mkdir()
        (fake / "fake.exe").write_text("exe")
        games = discover_games(mock_wds_root)
        for g in games:
            assert "FakeGame" not in g.full_name

    def test_mod_keyword_excluded(self, mock_wds_root: Path):
        """目录名含 'Mod' 的不应被识别为游戏"""
        mod_dir = mock_wds_root / "Some Mod Pack"
        mod_dir.mkdir()
        (mod_dir / "Data").mkdir()
        (mod_dir / "some.exe").write_text("exe")
        games = discover_games(mock_wds_root)
        for g in games:
            assert "Some Mod Pack" not in g.full_name

    def test_sorted_by_game_id(self, mock_wds_root: Path):
        """结果应按 game_id 排序"""
        games = discover_games(mock_wds_root)
        ids = [g.game_id for g in games]
        assert ids == sorted(ids)


# ===========================================================================
# detect_nations
# ===========================================================================

class TestDetectNations:
    def test_basic(self, mock_game_root: Path):
        nations = detect_nations(mock_game_root)
        assert "German" in nations
        assert "Russian" in nations
        assert "Austro-Hungarian" in nations

    def test_excludes_standard_dirs(self, mock_game_root: Path):
        """Data/Info/Map/Media 等标准目录不应被识别为阵营"""
        nations = detect_nations(mock_game_root)
        for std in ("Data", "Info", "Map", "Media", "Screens",
                     "Scenarios", "Saves", "Manuals", "Logs"):
            assert std not in nations

    def test_requires_units_or_bmp(self, mock_game_root: Path):
        """无 Units/ 且无 2DSymbolsLg.bmp 的目录不是阵营"""
        # 创建一个不含标志的目录
        (mock_game_root / "RandomFolder").mkdir()
        nations = detect_nations(mock_game_root)
        assert "RandomFolder" not in nations

    def test_units_subfolder_qualifies(self, mock_game_root: Path):
        """含 Units/ 子目录的 qualifies"""
        new_nation = mock_game_root / "Italian"
        (new_nation / "Units").mkdir(parents=True)
        nations = detect_nations(mock_game_root)
        assert "Italian" in nations

    def test_bmp_qualifies(self, mock_game_root: Path):
        """含 2DSymbolsLg.bmp 的 qualifies"""
        new_nation = mock_game_root / "Finnish"
        new_nation.mkdir()
        (new_nation / "2DSymbolsLg.bmp").write_text("bmp")
        nations = detect_nations(mock_game_root)
        assert "Finnish" in nations

    def test_sorted(self, mock_game_root: Path):
        nations = detect_nations(mock_game_root)
        assert nations == sorted(nations)

    def test_empty_dir(self, tmp_path: Path):
        empty = tmp_path / "empty_game"
        empty.mkdir()
        assert detect_nations(empty) == []


# ===========================================================================
# detect_main_exe
# ===========================================================================

class TestDetectMainExe:
    def test_basic(self, mock_game_root: Path):
        exe = detect_main_exe(mock_game_root)
        assert exe == "eastprussia14.exe"

    def test_excludes_editors(self, mock_game_root: Path):
        """编辑器 exe 不应被返回"""
        exe = detect_main_exe(mock_game_root)
        assert exe not in ("fwwcparam.exe", "fwwedit.exe", "fwwsub.exe")

    def test_pc_editors_excluded(self, tmp_path: Path):
        """PzC 系列编辑器应被排除"""
        game = tmp_path / "TestGame"
        game.mkdir()
        (game / "Data").mkdir()
        (game / "testgame.exe").write_text("main")
        (game / "pcedit.exe").write_text("editor")
        (game / "pcoob.exe").write_text("editor")
        (game / "pcparam.exe").write_text("editor")
        (game / "pcsub.exe").write_text("editor")
        assert detect_main_exe(game) == "testgame.exe"

    def test_no_exe_returns_none(self, tmp_path: Path):
        game = tmp_path / "NoExe"
        game.mkdir()
        (game / "Data").mkdir()
        assert detect_main_exe(game) is None

    def test_only_editors_returns_none(self, tmp_path: Path):
        game = tmp_path / "OnlyEditors"
        game.mkdir()
        (game / "pcedit.exe").write_text("editor")
        (game / "pcsub.exe").write_text("editor")
        assert detect_main_exe(game) is None

    def test_sumatrapdf_excluded(self, tmp_path: Path):
        game = tmp_path / "WithPDF"
        game.mkdir()
        (game / "game.exe").write_text("main")
        (game / "SumatraPDF.exe").write_text("pdf")
        assert detect_main_exe(game) == "game.exe"

    def test_cp_start_excluded(self, tmp_path: Path):
        """NW 系列 cp_start 应被排除"""
        game = tmp_path / "NWGame"
        game.mkdir()
        (game / "cpberlin.exe").write_text("main")
        (game / "cp_start.exe").write_text("launcher")
        assert detect_main_exe(game) == "cpberlin.exe"


# ===========================================================================
# 冒烟测试（手动执行: pytest -m smoke --wds-root D:\WDS）
# ===========================================================================

@pytest.mark.smoke
class TestSmokeRealWDS:
    """对真实 D:\\WDS 的只读冒烟测试"""

    @pytest.fixture
    def real_wds_root(self, pytestconfig) -> Path:
        root = pytestconfig.getoption("--wds-root", default="D:\\WDS")
        p = Path(root)
        if not p.is_dir():
            pytest.skip(f"WDS 根目录不存在: {p}")
        return p

    def test_discover_games_real(self, real_wds_root: Path):
        games = discover_games(real_wds_root)
        assert len(games) >= 1, "应至少发现 1 个游戏"
        for g in games:
            assert g.root_path.is_dir()
            assert g.exe_name.endswith(".exe")

    def test_detect_nations_real(self, real_wds_root: Path):
        games = discover_games(real_wds_root)
        if games:
            nations = detect_nations(games[0].root_path)
            assert len(nations) >= 1

    def test_detect_main_exe_real(self, real_wds_root: Path):
        games = discover_games(real_wds_root)
        if games:
            exe = detect_main_exe(games[0].root_path)
            assert exe is not None
