"""WDS Mod Manager 测试 fixtures

提供三个核心 mock fixture，用 tmp_path 构建虚拟目录树，
模拟真实 WDS 游戏、mod、WDS 根目录的结构。
所有自动化测试在这些 mock 环境中运行，不直接操作 D:\\WDS。
"""

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# pytest CLI 选项
# ---------------------------------------------------------------------------

def pytest_addoption(parser):
    parser.addoption(
        "--wds-root",
        action="store",
        default="D:\\WDS",
        help="WDS 游戏根目录路径（用于 smoke 测试）",
    )


# ---------------------------------------------------------------------------
# 辅助: 快速创建文件（含父目录）
# ---------------------------------------------------------------------------

def _touch(path: Path, content: str = "") -> Path:
    """创建文件（自动建父目录），写入 content"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _make_bmp(path: Path) -> Path:
    """创建一个假的 .bmp 文件（仅用于路径/结构测试，非真实位图）
    用完整路径做内容，确保不同位置的同名文件内容不同。"""
    return _touch(path, f"FAKE_BMP:{path}")


# ---------------------------------------------------------------------------
# Fixture: mock_game_root — 单个 WDS 游戏目录
# ---------------------------------------------------------------------------
# 模拟 EastPrussia '14 的结构（原版参考文件）:
#   - 3 个国家文件夹 (German, Russian, Austro-Hungarian)，各含 Units/ + BMP
#   - Data/, Info/, Map/（含子结构）, Media/, Screens/, Scenarios/, Saves/
#   - 主 exe + 编辑器 exe
#   - _backup/ 目录（可选，测试备份逻辑时启用）

@pytest.fixture
def mock_game_root(tmp_path: Path) -> Path:
    """构建一个模拟 WDS 游戏目录 (EastPrussia '14 风格)"""
    root = tmp_path / "EastPrussia' 14"
    root.mkdir()

    # --- 国家文件夹 ---
    for nation in ("German", "Russian", "Austro-Hungarian"):
        nation_dir = root / nation
        nation_dir.mkdir()
        # 国家级 BMP
        for bmp in ("2DSymbolsLg.bmp", "2DSymbolsMag.bmp", "2DSymbolsSm.bmp",
                     "3DCounters100.bmp", "3DCounters50.bmp",
                     "Flag.BMP", "Unitbox.bmp", "UnitboxBack.bmp"):
            _make_bmp(nation_dir / bmp)
        _touch(nation_dir / "Units.dat", "units_data")
        # Units/ 子目录
        units_dir = nation_dir / "Units"
        units_dir.mkdir()
        for unit_bmp in ("Infantry.bmp", "Armor.bmp", "Artillery.bmp"):
            _make_bmp(units_dir / unit_bmp)

    # --- Data/ ---
    data_dir = root / "Data"
    data_dir.mkdir()
    _touch(data_dir / "game.oob", "oob_data")
    _touch(data_dir / "game.pdt", "pdt_data")
    _touch(data_dir / "game.ai", "ai_data")
    _touch(data_dir / "game.dat", "dat_data")

    # --- Info/ ---
    info_dir = root / "Info"
    info_dir.mkdir()
    for bmp in ("BlankboxH.bmp", "BlankboxV.bmp", "TerrainH.bmp",
                "TerrainV.bmp", "Unitname.bmp", "Unknown.bmp"):
        _make_bmp(info_dir / bmp)

    # --- Map/（含多层子结构）---
    map_dir = root / "Map"
    map_dir.mkdir()
    # Map 根目录的 2D/3D 贴图
    for bmp in ("2DDamage50.bmp", "2DDamage100.bmp",
                "2DFeatures50.bmp", "2DFeatures100.bmp",
                "2DSymbolsLg.bmp", "2DSymbolsMag.bmp", "2DSymbolsSm.bmp"):
        _make_bmp(map_dir / bmp)
    # 子结构
    for sub in ("Hex Outline", "No Hex Outline",
                "Hi-res Graphics/Hex Outline", "Hi-res Graphics/No Hex Outline"):
        sub_dir = map_dir / sub
        sub_dir.mkdir(parents=True)
        for bmp in ("2DFeatures50.bmp", "2DFeatures100.bmp",
                    "2DSymbolsLg.bmp"):
            _make_bmp(sub_dir / bmp)

    # --- Media/ ---
    media_dir = root / "Media"
    media_dir.mkdir()
    _touch(media_dir / "fire.wav", "wav_data")
    _touch(media_dir / "move.wav", "wav_data")

    # --- Screens/ ---
    screens_dir = root / "Screens"
    screens_dir.mkdir()
    for bmp in ("AVictory.bmp", "NVictory.bmp", "Cover.bmp", "PhaseBox.BMP"):
        _make_bmp(screens_dir / bmp)

    # --- Scenarios/ ---
    scenarios_dir = root / "Scenarios"
    scenarios_dir.mkdir()
    _touch(scenarios_dir / "scenario1.scn", "scn_data")
    _touch(scenarios_dir / "map1.map", "map_data")

    # --- Saves/ ---
    saves_dir = root / "Saves"
    saves_dir.mkdir()
    _touch(saves_dir / "save1.btl", "btl_data")

    # --- Manuals/ ---
    manuals_dir = root / "Manuals"
    manuals_dir.mkdir()
    _touch(manuals_dir / "manual.pdf", "pdf_data")

    # --- Logs/ ---
    logs_dir = root / "Logs"
    logs_dir.mkdir()
    _touch(logs_dir / "game.log", "log_data")

    # --- 可执行文件 ---
    _touch(root / "eastprussia14.exe", "exe_main")
    _touch(root / "fwwcparam.exe", "exe_editor")
    _touch(root / "fwwedit.exe", "exe_editor")
    _touch(root / "fwwsub.exe", "exe_editor")

    return root


# ---------------------------------------------------------------------------
# Fixture: mock_mod_root — 单个 mod 目录
# ---------------------------------------------------------------------------
# 模拟 Hawkeyes_F40_Mod 的结构:
#   - 装饰性顶层文件夹名
#   - 国家透传层（与游戏国家文件夹同名）
#   - Map/ 和 Info/ 替换层

@pytest.fixture
def mock_mod_root(tmp_path: Path) -> Path:
    """构建一个模拟 mod 目录 (Hawkeyes 风格)"""
    mod = tmp_path / "Hawkeyes_EP14_Mod"
    mod.mkdir()

    # --- 装饰层 1: 2D Counters ---
    counters = mod / "Hawkeye's 2D Counters (EastPrussia 14)"
    counters.mkdir()
    for nation in ("German", "Russian", "Austro-Hungarian"):
        nation_dir = counters / nation
        nation_dir.mkdir()
        for bmp in ("2DSymbolsLg.bmp", "2DSymbolsMag.bmp", "2DSymbolsSm.bmp",
                     "Flag.bmp", "UnitBox.bmp", "UnitboxBack.bmp"):
            _make_bmp(nation_dir / bmp)
        # Units/ 子目录
        units_dir = nation_dir / "Units"
        units_dir.mkdir()
        for unit_bmp in ("Infantry.bmp", "Armor.bmp"):
            _make_bmp(units_dir / unit_bmp)

    # --- 装饰层 2: Map Enhancements ---
    map_enh = mod / "Hawkeye's PzC Map Enhancements (Non Desert)"
    map_enh.mkdir()
    map_dir = map_enh / "Map"
    map_dir.mkdir()
    for bmp in ("2DDamage50.bmp", "2DDamage100.bmp",
                "2DFeatures50.bmp", "2DFeatures100.bmp",
                "2DSymbolsLg.bmp", "2DSymbolsMag.bmp", "2DSymbolsSm.bmp"):
        _make_bmp(map_dir / bmp)

    # --- 装饰层 3: Generic (Info + Screens) ---
    generic = mod / "Generic MapMod (Blitzkrieg Phase)"
    generic.mkdir()
    info_dir = generic / "Info"
    info_dir.mkdir()
    for bmp in ("BlankboxH.bmp", "BlankboxV.bmp", "TerrainH.bmp",
                "TerrainV.bmp", "Unitname.bmp", "Unknown.bmp"):
        _make_bmp(info_dir / bmp)
    screens_dir = generic / "Screens"
    screens_dir.mkdir()
    _make_bmp(screens_dir / "PhaseBox.BMP")

    return mod


# ---------------------------------------------------------------------------
# Fixture: mock_wds_root — WDS 根目录（含分类文件夹 + 多个游戏）
# ---------------------------------------------------------------------------
# 模拟 D:\WDS 的结构:
#   - 分类文件夹 (PanzerCampain/) 下含多个游戏
#   - 顶层也有游戏
#   - 非游戏目录 (menu/, mod zip, Scenario Documents)

@pytest.fixture
def mock_wds_root(tmp_path: Path) -> Path:
    """构建一个模拟 WDS 根目录，含分类文件夹和多个游戏"""
    wds = tmp_path / "WDS"
    wds.mkdir()

    # --- 顶层游戏: EastPrussia '14 ---
    ep14 = wds / "EastPrussia' 14"
    ep14.mkdir()
    (ep14 / "Data").mkdir()
    _touch(ep14 / "Data" / "game.oob", "oob")
    _touch(ep14 / "eastprussia14.exe", "exe")
    for nation in ("German", "Russian"):
        n = ep14 / nation
        n.mkdir()
        _make_bmp(n / "2DSymbolsLg.bmp")
        (n / "Units").mkdir()
        _make_bmp(n / "Units" / "Infantry.bmp")

    # --- 分类文件夹: PanzerCampain/ ---
    pzc = wds / "PanzerCampain"
    pzc.mkdir()

    # 游戏 1: Moscow '41
    m41 = pzc / "Moscow '41"
    m41.mkdir()
    (m41 / "Data").mkdir()
    _touch(m41 / "Data" / "game.oob", "oob")
    _touch(m41 / "moscow41.exe", "exe")
    _touch(m41 / "pcedit.exe", "editor")
    for nation in ("German", "Russian", "NKVD"):
        n = m41 / nation
        n.mkdir()
        _make_bmp(n / "2DSymbolsLg.bmp")
        (n / "Units").mkdir()
        _make_bmp(n / "Units" / "Infantry.bmp")

    # 游戏 2: Smolensk '43
    s43 = pzc / "Smolensk '43"
    s43.mkdir()
    (s43 / "Data").mkdir()
    _touch(s43 / "Data" / "game.oob", "oob")
    _touch(s43 / "smolensk43.exe", "exe")
    for nation in ("German", "Russian"):
        n = s43 / nation
        n.mkdir()
        _make_bmp(n / "2DSymbolsLg.bmp")
        (n / "Units").mkdir()
        _make_bmp(n / "Units" / "Infantry.bmp")

    # --- 非游戏目录（不应被识别为游戏）---
    # menu 工具
    menu = wds / "menu"
    menu.mkdir()
    _touch(menu / "menu.exe", "menu_exe")

    # Scenario Documents（无 Data/ 目录）
    docs = wds / "Moscow '41 Scenario Documents"
    docs.mkdir()
    _touch(docs / "Map colour small.jpg", "jpg")

    # 一个 mod zip（不应被识别为游戏）
    _touch(wds / "Hawkeyes_F40_Mod.zip", "zip_data")

    return wds
