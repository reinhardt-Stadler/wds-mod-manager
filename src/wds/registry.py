# Copyright (c) 2026 Reinhardt Stadler. All Rights Reserved.
"""M06: 注册表管理

读写 _backup/game_registry.json，维护每个游戏的 mod 注册表和文件归属表。
原子写入避免中断损坏。
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from wds.models import (
    FileAttribution,
    GameRegistry,
    ModInfo,
    ModState,
    SourceVersion,
)

REGISTRY_FILENAME = "game_registry.json"
BACKUP_DIR_NAME = "_backup"


# ===========================================================================
# 读写
# ===========================================================================

def load_registry(game_root: Path) -> GameRegistry | None:
    """加载 game_registry.json，不存在则返回 None。"""
    path = game_root / BACKUP_DIR_NAME / REGISTRY_FILENAME
    if not path.is_file():
        return None
    return GameRegistry.load(path)


def save_registry(game_root: Path, registry: GameRegistry) -> None:
    """保存 GameRegistry 到 _backup/game_registry.json。

    原子写入: 先写临时文件再 rename，避免写入中断导致损坏。
    """
    backup_dir = game_root / BACKUP_DIR_NAME
    backup_dir.mkdir(exist_ok=True)
    target = backup_dir / REGISTRY_FILENAME

    # 写入临时文件（同目录，确保同一文件系统以支持原子 rename）
    fd, tmp_path = tempfile.mkstemp(
        suffix=".tmp", dir=str(backup_dir),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(registry.to_dict(), f, ensure_ascii=False, indent=2)
        # 原子替换
        os.replace(tmp_path, target)
    except BaseException:
        # 写入失败时清理临时文件
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def init_registry(game_id: str) -> GameRegistry:
    """创建空的 GameRegistry。"""
    return GameRegistry(
        game_id=game_id,
        mods={},
        files={},
        original_backup="",
    )


# ===========================================================================
# Mod 注册/注销
# ===========================================================================

def register_mod(registry: GameRegistry, mod_info: ModInfo) -> None:
    """向注册表添加一个新 mod（已存在则覆盖）。"""
    registry.mods[mod_info.mod_id] = mod_info


def unregister_mod(registry: GameRegistry, mod_id: str) -> None:
    """从注册表移除一个 mod（不删除备份文件）。

    同时清理文件归属表中该 mod 的 source 记录，
    并将 active_source 指向该 mod 的文件重置为 None。
    """
    registry.mods.pop(mod_id, None)

    for fa in registry.files.values():
        fa.sources.pop(mod_id, None)
        if fa.active_source == mod_id:
            fa.active_source = None


# ===========================================================================
# 文件归属
# ===========================================================================

def update_file_attribution(
    registry: GameRegistry,
    game_file: str,
    mod_id: str,
    source_version: SourceVersion,
) -> None:
    """记录某个文件被某个 mod 替换。

    如果该文件首次被记录，自动创建 FileAttribution 并设置 original_backup。
    active_source 更新为当前 mod_id。
    """
    if game_file not in registry.files:
        # 首次记录: 构建原版备份路径
        original_backup = ""
        if registry.original_backup:
            original_backup = f"{registry.original_backup}/{game_file}"
        registry.files[game_file] = FileAttribution(
            original_backup=original_backup,
            active_source=None,
            sources={},
        )

    fa = registry.files[game_file]
    fa.sources[mod_id] = source_version
    fa.active_source = mod_id


def switch_active_source(
    registry: GameRegistry,
    game_file: str,
    new_source: str | None,
) -> None:
    """切换文件的激活来源。None = 回滚到原版。

    文件不存在于归属表中时静默忽略。
    """
    fa = registry.files.get(game_file)
    if fa is None:
        return
    fa.active_source = new_source


# ===========================================================================
# 状态查询
# ===========================================================================

def get_mod_state(registry: GameRegistry, mod_id: str) -> ModState:
    """计算某个 mod 的当前状态。

    FULL:     该 mod 提供的所有文件都处于激活状态
    PARTIAL:  部分文件被其他 mod 覆盖
    INACTIVE: 无文件激活（或 mod 不存在/无文件记录）
    """
    if mod_id not in registry.mods:
        return ModState.INACTIVE

    # 收集该 mod 提供的所有文件
    mod_files: list[str] = []
    active_files: list[str] = []

    for game_file, fa in registry.files.items():
        if mod_id in fa.sources:
            mod_files.append(game_file)
            if fa.active_source == mod_id:
                active_files.append(game_file)

    if not mod_files:
        return ModState.INACTIVE

    if len(active_files) == len(mod_files):
        return ModState.FULL

    if len(active_files) == 0:
        return ModState.INACTIVE

    return ModState.PARTIAL


def get_status_summary(registry: GameRegistry) -> list[dict]:
    """生成 status 面板所需的数据。

    返回: [{mod_id, display_name, state, active_count, total_count}, ...]
    """
    results: list[dict] = []

    for mod_id, mod_info in registry.mods.items():
        state = get_mod_state(registry, mod_id)

        # 统计该 mod 的文件数
        total = 0
        active = 0
        for game_file, fa in registry.files.items():
            if mod_id in fa.sources:
                total += 1
                if fa.active_source == mod_id:
                    active += 1

        results.append({
            "mod_id": mod_id,
            "display_name": mod_info.display_name,
            "state": state,
            "active_count": active,
            "total_count": total,
        })

    return results
