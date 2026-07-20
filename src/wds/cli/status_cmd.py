# Copyright (c) 2026 Reinhardt Stadler. All Rights Reserved.
"""M11: status 命令 — 展示游戏的美化包安装状态"""

from __future__ import annotations

from pathlib import Path

from wds.cli.display import print_error, print_info, print_mod_list, print_status_panel
from wds.registry import get_status_summary, load_registry
from wds.scanner import discover_games


def run_status(
    wds_root: Path,
    game_id_arg: str | None,
) -> None:
    """执行 status 命令

    Args:
        wds_root: WDS 游戏根目录
        game_id_arg: 用户指定的游戏缩写，None 则显示所有游戏
    """
    games = discover_games(wds_root)
    if not games:
        print_error(f"在 {wds_root} 下未发现任何 WDS 游戏")
        return

    if game_id_arg:
        # 显示指定游戏的状态
        gid = game_id_arg.lower()
        matches = [g for g in games if g.game_id.lower() == gid]
        if not matches:
            print_error(f"未找到游戏缩写 '{game_id_arg}'，可用游戏: {', '.join(g.game_id for g in games)}")
            return
        game = matches[0]

        registry = load_registry(game.root_path)
        if registry is None:
            print_status_panel(
                game_name=f"{game.game_id} ({game.full_name})",
                summary=[],
                registry_exists=False,
            )
        else:
            summary = get_status_summary(registry)
            print_status_panel(
                game_name=f"{game.game_id} ({game.full_name})",
                summary=summary,
                registry_exists=True,
            )
    else:
        # 显示所有游戏的汇总
        games_data = []
        for game in games:
            registry = load_registry(game.root_path)
            mods = []
            if registry is not None:
                summary = get_status_summary(registry)
                # 需要根据 registry.files 里的 active_source 重新计算
                for entry in summary:
                    mods.append({
                        "mod_id": entry["mod_id"],
                        "display_name": entry["display_name"],
                        "state": entry["state"],
                        "active_count": entry["active_count"],
                        "total_count": entry["total_count"],
                    })

            games_data.append({
                "game_id": game.game_id,
                "full_name": game.full_name,
                "mods": mods,
                "mod_count": len(mods),
            })

        print_mod_list(games_data)
