# Copyright (c) 2026 Reinhardt Stadler. All Rights Reserved.
"""M10: install 命令 — 执行完整安装流程"""

from __future__ import annotations

from pathlib import Path

from wds.cli.display import (
    print_backup_hint,
    print_divider,
    print_error,
    print_info,
    print_scan_table,
    print_success,
    print_warning,
)
from wds.cli.review import build_review_groups, run_interactive_review
from wds.installer import install_mod
from wds.matcher import detect_game_from_mod, scan_mod
from wds.models import PathMapping
from wds.scanner import discover_games


def _scan_results_to_mappings(
    scan_results: list[tuple[str, str | None, str]],
) -> list[PathMapping]:
    """将 scan_mod 返回的文件级结果转换为目录级 PathMapping 列表"""
    pairs: set[tuple[str, str, str]] = set()
    for mod_file, game_target, confidence in scan_results:
        if game_target is None:
            continue
        mod_dir = mod_file.rsplit("/", 1)[0] if "/" in mod_file else ""
        game_dir = game_target.rsplit("/", 1)[0] if "/" in game_target else ""
        if mod_dir:
            pairs.add((mod_dir, game_dir, confidence))

    mappings: list[PathMapping] = []
    for mod_dir, game_dir, confidence in sorted(pairs):
        conf = "auto" if confidence == "auto" else "user_confirmed"
        mappings.append(PathMapping(
            mod_subfolder=mod_dir,
            game_target=game_dir,
            confidence=conf,
            resolved_by="leaf_match" if confidence == "auto" else "intersection",
        ))
    return mappings


def _resolve_game(
    wds_root: Path,
    mod_path: Path,
    game_id_arg: str | None,
) -> tuple | None:
    """解析目标游戏，返回 (GameInfo, source_str) 或 None"""
    games = discover_games(wds_root)
    if not games:
        print_error(f"在 {wds_root} 下未发现任何 WDS 游戏")
        return None

    if game_id_arg:
        gid = game_id_arg.lower()
        matches = [g for g in games if g.game_id.lower() == gid]
        if not matches:
            print_error(
                f"未找到游戏缩写 '{game_id_arg}'，"
                f"可用游戏: {', '.join(g.game_id for g in games)}"
            )
            return None
        return (matches[0], f"手动指定: {game_id_arg}")

    detected = detect_game_from_mod(mod_path, games)
    if not detected:
        print_error("无法自动推断 mod 所属游戏，请通过 --game/-g 参数指定")
        print_info(f"可用游戏: {', '.join(g.game_id for g in games)}")
        return None
    if len(detected) > 1:
        print_warning(
            f"发现多个候选游戏，使用最佳匹配: "
            f"{detected[0][0].game_id} ({detected[0][0].full_name})"
        )
    return detected[0]


def run_install(
    wds_root: Path,
    mod_path: Path,
    game_id_arg: str | None,
    display_name_arg: str | None,
    yes: bool,
) -> None:
    """执行 install 命令"""
    # 校验 mod 路径
    if not mod_path.exists():
        print_error(f"Mod 路径不存在: {mod_path}")
        return
    if mod_path.is_file() and mod_path.suffix.lower() in (".zip", ".7z", ".rar"):
        print_error("暂不支持从 zip/7z/rar 直接安装，请先解压为目录")
        return
    if not mod_path.is_dir():
        print_error(f"Mod 路径不是有效目录: {mod_path}")
        return

    # 解析目标游戏
    resolved = _resolve_game(wds_root, mod_path, game_id_arg)
    if resolved is None:
        return
    target_game, game_source = resolved

    # 扫描映射
    print_info(f"目标游戏: {target_game.game_id} ({target_game.full_name}) — {game_source}")
    print_info("正在扫描 mod 文件…")

    scan_results = scan_mod(mod_path, target_game)
    if not scan_results:
        print_warning("Mod 中未找到 BMP 文件")
        return

    game_info_str = f"{target_game.game_id} ({target_game.full_name})"
    print_scan_table(scan_results, mod_path_str=str(mod_path), game_info_str=game_info_str)

    matched = [(m, t, c) for m, t, c in scan_results if t is not None]
    unmatched = [(m, t, c) for m, t, c in scan_results if t is None]

    if yes:
        # 自动化场景: 直接采用自动匹配结果，不做交互识别
        if not matched:
            print_error("没有可安装的文件（所有文件均无法匹配游戏路径）")
            return
        ambig_count = sum(1 for _, _, c in matched if c == "ambiguous")
        if ambig_count > 0:
            print_warning(f"有 {ambig_count} 个文件存在路径歧义，将使用最佳匹配")
        if unmatched:
            print_warning(f"有 {len(unmatched)} 个文件无法匹配，将被跳过")
        mappings = _scan_results_to_mappings(matched)
    else:
        # 交互式路径识别: 逐组交付用户审查，无论是否匹配均需确认 (D-013)
        print_info("请逐组确认路径映射（无论是否匹配均需确认）")
        groups = build_review_groups(scan_results)
        mappings = run_interactive_review(groups)
        if mappings is None:
            print_info("已取消安装")
            return
        if not mappings:
            print_error("没有可安装的文件（所有目录组均已跳过）")
            return
        print_info(f"已确认 {len(mappings)} 个目录组，准备安装")

    # 执行安装
    print_info("正在安装，请稍候…")
    mod_info = install_mod(
        game_root=target_game.root_path,
        game_info=target_game,
        mod_path=mod_path,
        mappings=mappings,
        display_name=display_name_arg,
    )

    print_divider()
    print_success(
        f"安装完成: {mod_info.display_name} "
        f"({mod_info.active_count}/{mod_info.file_count} 文件已替换)"
    )
    print_info(f"Game: {target_game.game_id} | Mod ID: {mod_info.mod_id}")
    print_backup_hint(target_game.root_path)
