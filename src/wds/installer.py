"""M07: 安装引擎

编排完整的 install/uninstall/switch 流程，串联 M01~M06。
原子性保障: install 中途失败时回滚已复制的文件。
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from wds.backup import (
    create_mod_backup,
    create_original_backup,
    has_original_backup,
    restore_from_backup,
)
from wds.models import GameInfo, ModInfo, PathMapping, SourceVersion
from wds.registry import (
    init_registry,
    load_registry,
    register_mod,
    save_registry,
    switch_active_source,
    unregister_mod,
    update_file_attribution,
)
from wds.utils import collect_all_files, file_hash, mod_id_from_filename, normalize_path


# ===========================================================================
# install_mod
# ===========================================================================

def install_mod(
    game_root: Path,
    game_info: GameInfo,
    mod_path: Path,
    mappings: list[PathMapping],
    *,
    mod_id: str | None = None,
    display_name: str | None = None,
    confirm_callback: Callable | None = None,
) -> ModInfo:
    """完整的安装流程:

    1. 检查原版备份是否存在，不存在则创建 (D-010)
    2. 根据 mappings 确定需要替换的文件列表
    3. 创建 mod 备份（备份即将被覆盖的当前文件）
    4. 将 mod 文件复制到游戏目录（覆盖）
    5. 更新 game_registry: 注册 mod + 记录文件归属
    6. 返回 ModInfo

    原子性: 步骤 4 若中途失败，回滚已复制的文件。
    """
    # --- 1. 原版备份 ---
    if not has_original_backup(game_root, game_info.game_id):
        create_original_backup(game_root, game_info.game_id)

    # --- 2. 确定 mod_id 和需要替换的文件 ---
    if mod_id is None:
        mod_id = mod_id_from_filename(mod_path.name)
    if display_name is None:
        display_name = mod_id

    # 收集每个 mapping 下的文件: {游戏内相对路径 → mod 文件绝对路径}
    files_to_install: dict[str, Path] = {}
    for mapping in mappings:
        mod_subdir = mod_path / mapping.mod_subfolder
        if not mod_subdir.is_dir():
            continue
        sub_files = collect_all_files(mod_subdir)
        for rel_in_sub, abs_path in sub_files.items():
            game_rel = f"{mapping.game_target}/{rel_in_sub}"
            files_to_install[normalize_path(game_rel)] = abs_path

    if not files_to_install:
        # 无文件可安装，仍注册 mod（空 mod）
        pass

    # --- 3. 备份即将被覆盖的当前游戏文件 ---
    current_files: dict[str, Path] = {}
    for game_rel in files_to_install:
        game_file = game_root / game_rel
        if game_file.is_file():
            current_files[game_rel] = game_file

    if current_files:
        create_mod_backup(game_root, mod_id, current_files)

    # --- 4. 复制 mod 文件到游戏目录（带原子回滚）---
    copied: list[str] = []
    try:
        for game_rel, mod_file in files_to_install.items():
            dest = game_root / game_rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(mod_file, dest)
            copied.append(game_rel)
    except Exception:
        # 回滚: 从 mod 备份还原已复制的文件
        if current_files:
            # 找到刚创建的 mod 备份目录（最新的）
            backup_dir = game_root / "_backup"
            mod_backups = sorted(
                [d for d in backup_dir.iterdir()
                 if d.is_dir() and d.name.startswith(f"{mod_id}_")],
                key=lambda d: d.name,
            )
            if mod_backups:
                restore_from_backup(game_root, mod_backups[-1].name, copied)
        raise

    # --- 4b. 保存 mod 文件副本到 _backup/{mod_id}_modfiles/（供 switch 重新启用）---
    modfiles_dir = game_root / "_backup" / f"{mod_id}_modfiles"
    for game_rel, mod_file in files_to_install.items():
        dest = modfiles_dir / game_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(mod_file, dest)

    # --- 5. 更新 registry ---
    registry = load_registry(game_root)
    if registry is None:
        registry = init_registry(game_info.game_id)
        registry.original_backup = f"_backup/{game_info.game_id}_original"

    now = datetime.now(timezone.utc).isoformat()
    mod_info = ModInfo(
        mod_id=mod_id,
        game_id=game_info.game_id,
        display_name=display_name,
        source_path=mod_path.resolve(),
        install_time=now,
        file_count=len(files_to_install),
        active_count=len(files_to_install),
    )
    register_mod(registry, mod_info)

    for game_rel, mod_file in files_to_install.items():
        sv = SourceVersion(
            file_path=f"_backup/{mod_id}_modfiles/{game_rel}",
            hash=file_hash(mod_file),
            installed_at=now,
        )
        update_file_attribution(registry, game_rel, mod_id, sv)

    save_registry(game_root, registry)

    return mod_info


# ===========================================================================
# uninstall_mod
# ===========================================================================

def uninstall_mod(
    game_root: Path,
    game_info: GameInfo,
    mod_id: str,
) -> int:
    """禁用一个 mod: 将该 mod 所有 active 的文件还原到原版。

    1. 加载 registry
    2. 找到该 mod 所有 active 的文件
    3. 从原版备份还原
    4. 更新 registry: active_source → None
    5. 返回还原的文件数
    """
    registry = load_registry(game_root)
    if registry is None or mod_id not in registry.mods:
        return 0

    # 找到该 mod 当前激活的文件
    active_files: list[str] = []
    for game_file, fa in registry.files.items():
        if fa.active_source == mod_id:
            active_files.append(game_file)

    if not active_files:
        return 0

    # 从原版备份还原
    original_subdir = f"{game_info.game_id}_original"
    count = restore_from_backup(game_root, original_subdir, files=active_files)

    # 更新 registry
    for game_file in active_files:
        switch_active_source(registry, game_file, None)

    # 更新 mod 的 active_count
    registry.mods[mod_id].active_count = 0

    save_registry(game_root, registry)
    return count


# ===========================================================================
# switch_mod
# ===========================================================================

def switch_mod(
    game_root: Path,
    game_info: GameInfo,
    mod_id: str,
    enable: bool,
) -> int:
    """启用/禁用一个 mod。

    enable=True:  将该 mod 的所有文件设为 active（从备份复制 mod 版本到游戏目录）
    enable=False: 同 uninstall_mod（还原原版）
    返回: 操作的文件数
    """
    if not enable:
        return uninstall_mod(game_root, game_info, mod_id)

    registry = load_registry(game_root)
    if registry is None or mod_id not in registry.mods:
        return 0

    # 找到该 mod 提供的所有文件（无论当前是否激活）
    mod_files: list[str] = []
    for game_file, fa in registry.files.items():
        if mod_id in fa.sources:
            mod_files.append(game_file)

    if not mod_files:
        return 0

    # 从 _backup/{mod_id}_modfiles/ 复制 mod 文件到游戏目录
    modfiles_dir = game_root / "_backup" / f"{mod_id}_modfiles"

    count = 0
    if modfiles_dir.is_dir():
        for game_file in mod_files:
            src = modfiles_dir / game_file
            if src.is_file():
                dest = game_root / game_file
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                count += 1

    # 更新 registry: 将所有该 mod 的文件设为 active
    for game_file in mod_files:
        switch_active_source(registry, game_file, mod_id)

    registry.mods[mod_id].active_count = count

    save_registry(game_root, registry)
    return count
