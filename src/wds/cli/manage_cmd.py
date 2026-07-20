# Copyright (c) 2026 Reinhardt Stadler. All Rights Reserved.
"""M12: 管理命令集 — uninstall / switch / rename / list"""

from __future__ import annotations

from pathlib import Path

from wds.cli.display import (
    print_backup_hint,
    print_divider,
    print_error,
    print_info,
    print_mod_list,
    print_success,
    print_warning,
)
from wds.installer import switch_mod, uninstall_mod
from wds.registry import get_status_summary, load_registry, save_registry
from wds.scanner import discover_games


# ===========================================================================
# 内部辅助
# ===========================================================================


def _find_game(wds_root: Path, game_id_arg: str | None) -> tuple | None:
    """根据 game_id 查找游戏，返回 (GameInfo,) 或 None"""
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
        return (matches[0],)

    # 有多个游戏时要求指定
    if len(games) == 1:
        return (games[0],)

    print_error("请通过 --game/-g 参数指定目标游戏")
    print_info(f"可用游戏: {', '.join(g.game_id for g in games)}")
    return None


def _find_game_by_mod(wds_root: Path, mod_id: str) -> tuple | None:
    """在所有游戏中查找包含指定 mod_id 的游戏"""
    games = discover_games(wds_root)
    for game in games:
        registry = load_registry(game.root_path)
        if registry and mod_id in registry.mods:
            return (game,)
    return None


def _require_mod_in_registry(game, mod_id: str) -> bool:
    """确保 mod 已注册，打印错误并返回 False 否则"""
    registry = load_registry(game.root_path)
    if registry is None or mod_id not in registry.mods:
        print_error(f"Mod '{mod_id}' 未在 {game.game_id} ({game.full_name}) 中注册")
        return False
    return True


# ===========================================================================
# uninstall
# ===========================================================================


def run_uninstall(
    wds_root: Path,
    mod_id: str,
    game_id_arg: str | None,
) -> None:
    """禁用指定美化包"""
    # 先尝试按 game_id 找，再按 mod_id 全局搜索
    resolved = _find_game(wds_root, game_id_arg)
    if resolved is None:
        # 尝试在所有游戏中查找
        fallback = _find_game_by_mod(wds_root, mod_id)
        if fallback is None:
            return
        game = fallback[0]
        print_info(f"在 {game.game_id} ({game.full_name}) 中找到 mod '{mod_id}'")
    else:
        game = resolved[0]

    if not _require_mod_in_registry(game, mod_id):
        return

    count = uninstall_mod(game.root_path, game, mod_id)

    if count > 0:
        print_success(f"已卸载 '{mod_id}'，还原了 {count} 个文件到原版")
    else:
        print_warning(f"'{mod_id}' 没有激活的文件需要还原")

    print_backup_hint(game.root_path)
    print_info(f"可用 `wds status {game.game_id}` 查看当前状态")


# ===========================================================================
# switch
# ===========================================================================


def run_switch(
    wds_root: Path,
    mod_id: str,
    on: bool,
    off: bool,
    game_id_arg: str | None,
) -> None:
    """启用或禁用指定美化包"""
    if on == off:
        print_error("请指定 --on 或 --off（二选一）")
        return

    resolved = _find_game(wds_root, game_id_arg)
    if resolved is None:
        fallback = _find_game_by_mod(wds_root, mod_id)
        if fallback is None:
            return
        game = fallback[0]
        print_info(f"在 {game.game_id} ({game.full_name}) 中找到 mod '{mod_id}'")
    else:
        game = resolved[0]

    if not _require_mod_in_registry(game, mod_id):
        return

    action = "启用" if on else "禁用"
    count = switch_mod(game.root_path, game, mod_id, enable=on)

    if count > 0:
        print_success(f"已{action} '{mod_id}'（{count} 个文件）")
    else:
        print_warning(f"'{mod_id}' 无可操作的文件（可能尚未安装或无文件记录）")

    print_backup_hint(game.root_path)
    print_info(f"可用 `wds status {game.game_id}` 查看当前状态")


# ===========================================================================
# rename
# ===========================================================================


def run_rename(
    wds_root: Path,
    mod_id: str,
    new_name: str,
    game_id_arg: str | None,
) -> None:
    """修改美化包的显示别名"""
    resolved = _find_game(wds_root, game_id_arg)
    if resolved is None:
        fallback = _find_game_by_mod(wds_root, mod_id)
        if fallback is None:
            return
        game = fallback[0]
        print_info(f"在 {game.game_id} ({game.full_name}) 中找到 mod '{mod_id}'")
    else:
        game = resolved[0]

    registry = load_registry(game.root_path)
    if registry is None or mod_id not in registry.mods:
        print_error(f"Mod '{mod_id}' 未在 {game.game_id} ({game.full_name}) 中注册")
        return

    old_name = registry.mods[mod_id].display_name
    registry.mods[mod_id].display_name = new_name
    save_registry(game.root_path, registry)

    print_success(f"已将 '{mod_id}' 的别名从 '{old_name}' 修改为 '{new_name}'")
    print_info(f"可用 `wds status {game.game_id}` 查看")


# ===========================================================================
# list
# ===========================================================================


def run_list(
    wds_root: Path,
    all_games: bool,
) -> None:
    """列出所有已注册的美化包"""
    games = discover_games(wds_root)
    if not games:
        print_error(f"在 {wds_root} 下未发现任何 WDS 游戏")
        return

    games_data = []
    for game in games:
        registry = load_registry(game.root_path)
        mods = []
        if registry is not None:
            summary = get_status_summary(registry)
            for entry in summary:
                mods.append({
                    "mod_id": entry["mod_id"],
                    "display_name": entry["display_name"],
                    "state": entry["state"],
                    "active_count": entry["active_count"],
                    "total_count": entry["total_count"],
                })

        if all_games or mods:
            games_data.append({
                "game_id": game.game_id,
                "full_name": game.full_name,
                "mods": mods,
                "mod_count": len(mods),
            })

    if not games_data:
        print_info("所有游戏均未安装任何美化包")
        print_info("可用 `wds status <game_id>` 查看各游戏状态")
        return

    print_mod_list(games_data)
