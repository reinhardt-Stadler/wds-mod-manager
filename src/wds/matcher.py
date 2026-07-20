# Copyright (c) 2026 Reinhardt Stadler. All Rights Reserved.
"""M04: 路径匹配引擎

D-014 类别优先匹配（取代 D-002 的纯文件名匹配）:

人类的查找替换思路是"先按类别匹配，再在类别内部替换文件"。据此:

1. 类别匹配: mod 文件路径中若含有与游戏顶层目录（国家 / Map / Info /
   Screens 等）名字相等的文件夹（字符规范化后比较），则该文件落入游戏
   对应类别目录下的相同相对路径。类别名匹配大小写不敏感、忽略
   空格/连字符/下划线（'East-German' == 'East German' == 'east_german'）。
2. 类内文件: 类别匹配后，文件按相对路径落到游戏类别目录；文件名大小写
   不敏感（Windows 文件系统语义），mod 的 UnitBox.bmp 对应游戏的
   Unitbox.bmp。类别匹配但游戏该类别下无此文件 → unmatched（交用户处理）。
3. 散装贴图回退: 路径中无任何类别文件夹的文件（非国家单位贴图，如根目录
   的 Menu.bmp、装饰层下的零散贴图）回退到文件名匹配（D-002 自底向上
   后缀 + Jaccard 消歧，大小写不敏感）。

类别匹配修复了 D-002 的缺陷: 两层"国家/文件"路径会剥掉国家名、按文件名
把国家文件夹散到别国（如 Czechoslovakia 误配 French、UnitBox 误配 Luftwaffe）。
"""

from __future__ import annotations

from pathlib import Path

from wds.models import GameInfo
from wds.utils import collect_bmp_files, is_excluded_dir, mod_id_from_filename, normalize_path


# ===========================================================================
# 类别名规范化
# ===========================================================================

def normalize_category_name(name: str) -> str:
    """类别名规范化: 转小写并仅保留字母数字。

    使 'East-German' / 'East German' / 'east_german' / 'EAST GERMAN' 归一为
    'eastgerman'。不上语义别名表（D-014: 仅字符规范化）。
    """
    return "".join(ch for ch in name.lower() if ch.isalnum())


# ===========================================================================
# 游戏文件索引（大小写不敏感）
# ===========================================================================

def build_game_index(game_root: Path) -> dict[str, list[str]]:
    """构建游戏文件索引: {小写文件名 → [包含此文件的相对路径列表(原始大小写)]}

    键统一小写（Windows 文件系统大小写不敏感），值为原始大小写的相对路径。
    排除 _backup/ 及 is_excluded_dir 返回 True 的目录。
    """
    all_bmps = collect_bmp_files(game_root)
    index: dict[str, list[str]] = {}
    for rel_path in all_bmps:
        filename = rel_path.rsplit("/", 1)[-1].lower()
        index.setdefault(filename, []).append(rel_path)
    return index


# ===========================================================================
# 游戏类别（顶层目录）
# ===========================================================================

def build_game_categories(game_root: Path) -> dict[str, str]:
    """构建游戏类别映射: {规范化目录名 → 原始目录名}。

    类别 = 游戏根目录下的顶层目录（国家文件夹 + Map/Info/Media/Screens 等
    功能目录），排除 _backup/ 及 is_excluded_dir 返回 True 的目录。
    """
    categories: dict[str, str] = {}
    try:
        entries = sorted(game_root.iterdir())
    except (PermissionError, FileNotFoundError):
        return categories
    for entry in entries:
        if entry.is_dir() and not is_excluded_dir(entry.name):
            categories[normalize_category_name(entry.name)] = entry.name
    return categories


# ===========================================================================
# 自底向上文件名匹配（散装贴图回退，大小写不敏感）
# ===========================================================================

def resolve_target(
    mod_file_relative: str,
    game_index: dict[str, list[str]],
    game_root: Path,
    *,
    mod_root: Path | None = None,
) -> str | None:
    """自底向上文件名匹配（D-002，大小写不敏感）。

    用作非类别文件（散装贴图）的回退匹配:
    1. 取 mod 文件的小写文件名在 game_index 中查找候选（原始大小写路径）。
    2. 从 i=1 开始逐步剥离装饰层前缀，取后缀（小写）过滤候选。
    3. 唯一匹配 → 返回；多个 → disambiguate；无 → 截短前缀继续。
    4. 全部后缀都无法唯一匹配 → 返回 None。
    """
    mod_file_relative = normalize_path(mod_file_relative)
    parts = mod_file_relative.split("/")
    filename = parts[-1].lower()

    if filename not in game_index:
        return None

    all_candidates = game_index[filename]

    for i in range(1, len(parts)):
        suffix = "/".join(parts[i:]).lower()
        matched = [
            gp for gp in all_candidates
            if gp.lower() == suffix or gp.lower().endswith("/" + suffix)
        ]

        if len(matched) == 1:
            return matched[0]

        if len(matched) > 1:
            if mod_root is not None:
                result = disambiguate(
                    mod_file_relative, mod_root, matched, game_root,
                )
                if result is not None:
                    return result
            continue

    # 最终回退: 路径仅一个分量（纯文件名）时循环不执行，
    # 或所有后缀都无法唯一匹配时，尝试用裸文件名匹配。
    if len(parts) == 1:
        if len(all_candidates) == 1:
            return all_candidates[0]
        if mod_root is not None:
            result = disambiguate(
                mod_file_relative, mod_root, all_candidates, game_root,
            )
            if result is not None:
                return result

    return None


# ===========================================================================
# 文件交集消歧
# ===========================================================================

def disambiguate(
    mod_file_relative: str,
    mod_root: Path,
    candidates: list[str],
    game_root: Path,
) -> str | None:
    """文件交集消歧: 比较 mod 同目录文件集与各候选游戏路径的文件集。

    取 Jaccard 相似度（交集/并集）最大者。
    阈值: > 0.5 才接受，否则返回 None（交给用户手动选择）。

    特殊情况: 只有一个候选时直接返回。
    """
    if len(candidates) == 1:
        return candidates[0]

    mod_file_relative = normalize_path(mod_file_relative)

    mod_parent_rel = mod_file_relative.rsplit("/", 1)[0] if "/" in mod_file_relative else ""
    mod_dir = mod_root / mod_parent_rel if mod_parent_rel else mod_root
    mod_siblings = _sibling_filenames(mod_dir)

    if not mod_siblings:
        return None

    best_score = 0.0
    best_candidate: str | None = None

    for candidate in candidates:
        game_parent_rel = candidate.rsplit("/", 1)[0] if "/" in candidate else ""
        game_dir = game_root / game_parent_rel if game_parent_rel else game_root
        game_siblings = _sibling_filenames(game_dir)

        if not game_siblings:
            continue

        intersection = mod_siblings & game_siblings
        union = mod_siblings | game_siblings
        score = len(intersection) / len(union) if union else 0.0

        if score > best_score:
            best_score = score
            best_candidate = candidate

    if best_score > 0.5:
        return best_candidate
    return None


def _sibling_filenames(directory: Path) -> set[str]:
    """获取目录下所有文件的文件名集合（统一为小写）"""
    if not directory.is_dir():
        return set()
    names: set[str] = set()
    try:
        for f in directory.iterdir():
            if f.is_file():
                names.add(f.name.lower())
    except PermissionError:
        pass
    return names


# ===========================================================================
# 类别优先解析
# ===========================================================================

def _match_category(
    mod_rel_normalized: str,
    game_categories: dict[str, str],
) -> tuple[str, str] | None:
    """在 mod 相对路径中找到最浅的、名字匹配游戏类别的目录分量。

    Args:
        mod_rel_normalized: 规范化（正斜杠）的 mod 相对路径。
        game_categories: {规范化类别名 → 游戏原始目录名}。

    Returns:
        (游戏类别目录名, 类别内相对路径)；无类别匹配时返回 None。
    """
    parts = mod_rel_normalized.split("/")
    # parts[-1] 是文件名，目录分量为 parts[:-1]
    for k in range(len(parts) - 1):
        norm = normalize_category_name(parts[k])
        if norm in game_categories:
            game_cat = game_categories[norm]
            rel_within = "/".join(parts[k + 1:])
            return game_cat, rel_within
    return None


# ===========================================================================
# 扫描整个 mod
# ===========================================================================

def scan_mod(
    mod_path: Path,
    game_info: GameInfo,
) -> list[tuple[str, str | None, str]]:
    """扫描整个 mod，类别优先匹配，返回映射表。

    返回: [(mod_file_relative, game_target, confidence), ...]
    confidence:
        "auto"      — 类别匹配成功（文件存在于游戏类别）或文件名唯一匹配
        "ambiguous" — 文件名有多个候选但消歧失败，需用户确认
        "unmatched" — 无法匹配（含"类别匹配但游戏无此文件"）
    """
    game_root = game_info.root_path
    game_index = build_game_index(game_root)
    game_categories = build_game_categories(game_root)
    game_paths_lower = {p.lower() for p in collect_bmp_files(game_root)}
    mod_bmps = collect_bmp_files(mod_path)

    results: list[tuple[str, str | None, str]] = []

    for mod_rel in sorted(mod_bmps.keys()):
        norm = normalize_path(mod_rel)

        # --- 1. 类别优先匹配 ---
        cat = _match_category(norm, game_categories)
        if cat is not None:
            game_cat, rel_within = cat
            target = f"{game_cat}/{rel_within}" if rel_within else game_cat
            if target.lower() in game_paths_lower:
                results.append((mod_rel, target, "auto"))
            else:
                # 类别匹配但游戏该类别下无此文件 → 无对应，交用户处理
                results.append((mod_rel, None, "unmatched"))
            continue

        # --- 2. 散装贴图: 文件名回退 ---
        target = resolve_target(norm, game_index, game_root, mod_root=mod_path)
        if target is not None:
            results.append((mod_rel, target, "auto"))
        else:
            filename = norm.rsplit("/", 1)[-1].lower()
            if filename in game_index:
                results.append((mod_rel, None, "ambiguous"))
            else:
                results.append((mod_rel, None, "unmatched"))

    return results


# ===========================================================================
# Mod 所属游戏检测
# ===========================================================================

def detect_game_from_mod(
    mod_path: Path,
    known_games: list[GameInfo],
) -> list[tuple[GameInfo, str]]:
    """推断 mod 属于哪个游戏（D-009 渐进式匹配）。

    策略:
    1. 文件名匹配: 从目录/zip 名提取游戏缩写，在 known_games 中查找
    2. 内部阵营名推断: mod 内顶层目录名与各游戏 nations 求交集
    3. 返回所有候选（按匹配度降序），由用户最终确认

    返回: [(GameInfo, reason), ...]，空列表 = 无法推断。
    """
    if not mod_path.exists():
        return []

    candidates: list[tuple[GameInfo, str, int]] = []  # (game, reason, score)

    # --- 策略 1: 文件名匹配 ---
    mod_id = mod_id_from_filename(mod_path.name)
    for game in known_games:
        gid_lower = game.game_id.lower()
        if gid_lower in mod_id:
            candidates.append((
                game,
                f"文件名匹配: '{mod_path.name}' 含游戏缩写 '{game.game_id}'",
                100,  # 最高优先级
            ))

    # --- 策略 2: 阵营名推断 ---
    mod_dirs = _top_level_dir_names(mod_path)
    if mod_dirs:
        for game in known_games:
            # 跳过已通过文件名匹配的
            if any(c[0].game_id == game.game_id for c in candidates):
                continue

            game_nations = {n.lower() for n in game.nations}
            overlap = mod_dirs & game_nations
            if overlap:
                score = len(overlap) * 10
                # 独有阵营加分（该阵营只在此游戏中出现）
                for nation in overlap:
                    appears_in = sum(
                        1 for g in known_games
                        if nation in {n.lower() for n in g.nations}
                    )
                    if appears_in == 1:
                        score += 50  # 独有阵营是强信号

                overlap_names = ", ".join(sorted(overlap))
                candidates.append((
                    game,
                    f"阵营名推断: mod 含 {overlap_names}（匹配 {len(overlap)} 个阵营）",
                    score,
                ))

    # 按分数降序排序
    candidates.sort(key=lambda c: c[2], reverse=True)
    return [(game, reason) for game, reason, _ in candidates]


def _top_level_dir_names(path: Path) -> set[str]:
    """获取路径下所有顶层目录名（小写），排除装饰层关键词"""
    if not path.is_dir():
        return set()
    names: set[str] = set()
    try:
        for entry in path.iterdir():
            if entry.is_dir() and not is_excluded_dir(entry.name):
                names.add(entry.name.lower())
    except PermissionError:
        pass
    return names
