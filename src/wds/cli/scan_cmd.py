# Copyright (c) 2026 Reinhardt Stadler. All Rights Reserved.
"""M09: scan 命令 — 扫描 mod 目录，展示路径映射表"""

from __future__ import annotations

from pathlib import Path

from wds.cli.display import print_error, print_info, print_scan_table, print_warning
from wds.matcher import detect_game_from_mod, scan_mod
from wds.scanner import discover_games


def run_scan(
    wds_root: Path,
    mod_path: Path,
    game_id_arg: str | None,
) -> None:
    """执行 scan 命令

    Args:
        wds_root: WDS 游戏根目录
        mod_path: mod 目录或 zip 文件路径
        game_id_arg: 用户指定的游戏缩写，None 则自动推断
    """
    # 校验 mod 路径
    if not mod_path.exists():
        print_error(f"Mod 路径不存在: {mod_path}")
        return

    if mod_path.is_file() and mod_path.suffix.lower() in (".zip", ".7z", ".rar"):
        print_error("暂不支持从 zip/7z/rar 直接扫描，请先解压为目录")
        return

    if not mod_path.is_dir():
        print_error(f"Mod 路径不是有效目录: {mod_path}")
        return

    # 发现游戏
    games = discover_games(wds_root)
    if not games:
        print_error(f"在 {wds_root} 下未发现任何 WDS 游戏")
        return

    # 确定目标游戏
    target_game = None

    if game_id_arg:
        gid = game_id_arg.lower()
        matches = [g for g in games if g.game_id.lower() == gid]
        if not matches:
            print_error(f"未找到游戏缩写 '{game_id_arg}'，可用游戏: {', '.join(g.game_id for g in games)}")
            return
        target_game = matches[0]
        game_source = f"手动指定: {game_id_arg}"
    else:
        # 自动推断
        detected = detect_game_from_mod(mod_path, games)
        if not detected:
            print_error("无法自动推断 mod 所属游戏，请通过 --game/-g 参数指定")
            print_info(f"可用游戏: {', '.join(g.game_id for g in games)}")
            return
        if len(detected) == 1:
            target_game, reason = detected[0]
            game_source = reason
        else:
            # 多个候选，取第一个（最佳匹配）
            target_game, reason = detected[0]
            game_source = reason
            print_warning(f"发现多个候选游戏，使用最佳匹配: {target_game.game_id} ({target_game.full_name})")
            print_info(f"可通过 --game 参数指定目标游戏")

    print_info(f"目标游戏: {target_game.game_id} ({target_game.full_name}) — {game_source}")
    print_info(f"Mod 路径: {mod_path}")

    # 扫描映射
    mappings = scan_mod(mod_path, target_game)

    if not mappings:
        print_warning("Mod 中未找到 BMP 文件")
        return

    # 展示结果
    game_info_str = f"{target_game.game_id} ({target_game.full_name})"
    print_scan_table(mappings, mod_path_str=str(mod_path), game_info_str=game_info_str)
