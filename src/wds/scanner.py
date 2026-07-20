# Copyright (c) 2026 Reinhardt Stadler. All Rights Reserved.
"""M03: 游戏发现

自动扫描 WDS 根目录，递归发现所有游戏，构建 GameInfo 列表。
识别规则: Data/ 子目录 + 至少一个 .exe 文件 = 有效游戏。
"""

from __future__ import annotations

from pathlib import Path

from wds.models import GameInfo
from wds.utils import game_id_from_name, is_excluded_dir

# ===========================================================================
# 常量
# ===========================================================================

# 最大扫描深度: WDS根 / 分类文件夹 / 游戏 /（不再 deeper）
_MAX_DEPTH = 3

# 标准游戏子目录（非阵营）
_STANDARD_DIRS: frozenset[str] = frozenset({
    "Data", "Info", "Map", "Media", "Logs", "Manuals",
    "Screens", "Scenarios", "Saves",
})

# 已知编辑器/工具 exe 前缀（小写匹配）
_EDITOR_EXE_PREFIXES: tuple[str, ...] = (
    "pcedit", "pcoob", "pcparam", "pcsub",     # Panzer Campaigns
    "mcedit", "mcoob", "mcparam", "mcsub",     # Modern Campaigns
    "nwedit", "nwcamp",                         # Napoleonic Wars
    "sscamp", "ssedit", "sssub",                # Squad Battles
    "cwedit", "cwcamp",                         # Civil War
    "cp_start",                                 # NW launcher
    "sumatrapdf",                               # PDF reader
    "fwwcparam", "fwwedit", "fwwsub",           # WW1 (EastPrussia etc.)
)

# 目录名中包含这些关键词的跳过（不区分大小写）
_SKIP_DIR_KEYWORDS: tuple[str, ...] = (
    "scenario documents",
    "mod",
    "美化",
    "menu",
    "推演记录",
)


# ===========================================================================
# 内部辅助
# ===========================================================================

def _should_skip_dir(name: str) -> bool:
    """判断目录是否应跳过（排除目录 + 关键词匹配）"""
    if is_excluded_dir(name):
        return True
    lower = name.lower()
    return any(kw in lower for kw in _SKIP_DIR_KEYWORDS)


def _is_game_dir(path: Path) -> bool:
    """判断目录是否为有效游戏: Data/ + 至少一个 .exe"""
    if not (path / "Data").is_dir():
        return False
    return any(f.suffix.lower() == ".exe" for f in path.iterdir() if f.is_file())


# ===========================================================================
# 公开 API
# ===========================================================================

def discover_games(wds_root: Path) -> list[GameInfo]:
    """递归扫描 wds_root 下所有子目录，返回已发现的游戏列表。

    识别规则:
    1. 目录内存在 Data/ 子目录
    2. 目录内存在至少一个 .exe 文件
    3. 两条同时满足 → 这是一个游戏

    扫描策略:
    - 最大递归深度: 3 层（WDS/分类文件夹/游戏/）
    - 排除: is_excluded_dir 返回 True 的目录
    - 排除: 目录名含 'Scenario Documents', 'Mod', '美化', 'menu', '推演记录'

    返回按 game_id 排序的列表。不存在的目录返回空列表。
    """
    if not wds_root.is_dir():
        return []

    games: list[GameInfo] = []

    def _scan(dir_path: Path, depth: int) -> None:
        if depth > _MAX_DEPTH:
            return
        try:
            entries = sorted(dir_path.iterdir())
        except PermissionError:
            return

        for entry in entries:
            if not entry.is_dir():
                continue
            if _should_skip_dir(entry.name):
                continue

            if _is_game_dir(entry):
                # 发现游戏，不再深入其子目录
                nations = detect_nations(entry)
                exe_name = detect_main_exe(entry) or ""
                game_id = game_id_from_name(entry.name)
                has_backup = (entry / "_backup" / f"{game_id}_original").is_dir()

                games.append(GameInfo(
                    game_id=game_id,
                    full_name=entry.name,
                    root_path=entry.resolve(),
                    exe_name=exe_name,
                    nations=nations,
                    has_original_backup=has_backup,
                ))
            else:
                # 非游戏目录，可能是分类文件夹，继续递归
                _scan(entry, depth + 1)

    _scan(wds_root, 1)
    games.sort(key=lambda g: g.game_id)
    return games


def detect_nations(game_root: Path) -> list[str]:
    """扫描游戏目录，返回所有阵营文件夹名（排序）。

    阵营文件夹的识别规则:
    - 顶层目录（不在 Data/Info/Map/Media/Logs/Manuals/Screens/Scenarios/Saves 之列）
    - 不是排除目录（_backup 等）
    - 内含 Units/ 子目录 或 含 2DSymbolsLg.bmp
    """
    if not game_root.is_dir():
        return []

    nations: list[str] = []
    try:
        entries = sorted(game_root.iterdir())
    except PermissionError:
        return []

    for entry in entries:
        if not entry.is_dir():
            continue
        if entry.name in _STANDARD_DIRS:
            continue
        if is_excluded_dir(entry.name):
            continue
        # 阵营标志: Units/ 子目录 或 2DSymbolsLg.bmp
        if (entry / "Units").is_dir() or (entry / "2DSymbolsLg.bmp").is_file():
            nations.append(entry.name)

    return sorted(nations)


def detect_main_exe(game_root: Path) -> str | None:
    """找到游戏主 exe 文件名。

    策略: 在游戏根目录找 .exe 文件，排除已知编辑器/工具。
    返回剩下的第一个（按文件名排序）。无匹配返回 None。
    """
    if not game_root.is_dir():
        return None

    candidates: list[str] = []
    try:
        for f in sorted(game_root.iterdir()):
            if not f.is_file() or f.suffix.lower() != ".exe":
                continue
            stem_lower = f.stem.lower()
            if any(stem_lower.startswith(prefix) for prefix in _EDITOR_EXE_PREFIXES):
                continue
            candidates.append(f.name)
    except PermissionError:
        return None

    return candidates[0] if candidates else None
