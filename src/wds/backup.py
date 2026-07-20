"""M05: 备份管理

管理游戏目录内的 _backup/ 备份池（D-001）。
原版基准备份、mod 安装备份、从备份还原。
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from wds.utils import collect_bmp_files, is_excluded_dir

BACKUP_DIR_NAME = "_backup"


# ===========================================================================
# 基础设施
# ===========================================================================

def ensure_backup_dir(game_root: Path) -> Path:
    """确保 _backup/ 目录存在，返回其路径。"""
    backup_dir = game_root / BACKUP_DIR_NAME
    backup_dir.mkdir(exist_ok=True)
    return backup_dir


# ===========================================================================
# 原版基准备份
# ===========================================================================

def create_original_backup(game_root: Path, game_id: str) -> Path:
    """创建原版基准备份: 将游戏当前所有 BMP 文件备份到 _backup/{game_id}_original/。

    幂等: 若目录已存在则跳过，返回已有路径。
    返回: 备份目录路径。
    """
    backup_dir = ensure_backup_dir(game_root)
    target = backup_dir / f"{game_id}_original"

    if target.is_dir():
        return target

    # 收集游戏中所有 BMP（collect_bmp_files 已排除 _backup 等目录）
    game_bmps = collect_bmp_files(game_root)

    for rel_path, abs_path in game_bmps.items():
        dest = target / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(abs_path, dest)

    return target


def has_original_backup(game_root: Path, game_id: str) -> bool:
    """检查原版基准备份是否存在。"""
    return (game_root / BACKUP_DIR_NAME / f"{game_id}_original").is_dir()


# ===========================================================================
# Mod 安装备份
# ===========================================================================

def create_mod_backup(
    game_root: Path,
    mod_id: str,
    files_to_backup: dict[str, Path],
) -> Path:
    """为 mod 安装创建备份: 仅备份即将被替换的文件。

    Args:
        game_root: 游戏根目录
        mod_id: mod 标识符
        files_to_backup: {游戏内相对路径 → 当前游戏文件的绝对路径}

    存储位置: _backup/{mod_id}_{YYYYMMDD_HHMMSS}/
    返回: 备份目录路径。
    """
    backup_dir = ensure_backup_dir(game_root)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = backup_dir / f"{mod_id}_{timestamp}"
    target.mkdir(parents=True, exist_ok=True)

    for rel_path, abs_path in files_to_backup.items():
        dest = target / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if abs_path.is_file():
            shutil.copy2(abs_path, dest)

    return target


# ===========================================================================
# 还原
# ===========================================================================

def restore_from_backup(
    game_root: Path,
    backup_subdir: str,
    files: list[str] | None = None,
) -> int:
    """从备份还原文件到游戏目录。

    Args:
        game_root: 游戏根目录
        backup_subdir: _backup/ 下的子目录名（如 "EP14_original"）
        files: 要还原的文件相对路径列表，None = 全部

    返回: 还原的文件数。
     raises FileNotFoundError: 备份子目录不存在。
    """
    backup_path = game_root / BACKUP_DIR_NAME / backup_subdir
    if not backup_path.is_dir():
        raise FileNotFoundError(f"备份目录不存在: {backup_path}")

    if files is not None:
        # 还原指定文件
        count = 0
        for rel_path in files:
            src = backup_path / rel_path
            if src.is_file():
                dest = game_root / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                count += 1
        return count

    # 还原全部: 遍历备份目录中的所有文件
    count = 0
    for src in backup_path.rglob("*"):
        if src.is_file():
            rel = src.relative_to(backup_path)
            dest = game_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            count += 1
    return count


# ===========================================================================
# 列出备份
# ===========================================================================

def list_backups(game_root: Path) -> list[dict]:
    """列出 _backup/ 下所有备份。

    返回: [{name, type, file_count, size}, ...]
    type: "original"（含 _original 后缀）或 "mod"（其他）
    """
    backup_dir = game_root / BACKUP_DIR_NAME
    if not backup_dir.is_dir():
        return []

    results: list[dict] = []
    for entry in sorted(backup_dir.iterdir()):
        if not entry.is_dir():
            continue

        file_count = 0
        total_size = 0
        for f in entry.rglob("*"):
            if f.is_file():
                file_count += 1
                total_size += f.stat().st_size

        backup_type = "original" if entry.name.endswith("_original") else "mod"
        results.append({
            "name": entry.name,
            "type": backup_type,
            "file_count": file_count,
            "size": total_size,
        })

    return results
