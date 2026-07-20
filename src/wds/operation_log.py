"""操作日志: 记录每次 install/uninstall/switch 操作，支持 undo 回退。

日志存储于 {game_root}/_backup/operation_log.json，追加式写入。
每条记录包含足够信息以反向执行上一次操作。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG_FILENAME = "operation_log.json"


def _log_path(game_root: Path) -> Path:
    """操作日志文件路径"""
    return game_root / "_backup" / LOG_FILENAME


def log_operation(
    game_root: Path,
    action: str,
    mod_id: str,
    game_id: str,
    details: dict[str, Any] | None = None,
) -> None:
    """追加一条操作记录。

    Args:
        game_root: 游戏根目录。
        action: 操作类型 ("install" / "uninstall" / "switch_on" / "switch_off")。
        mod_id: 美化包 ID。
        game_id: 游戏缩写。
        details: 附加信息（如文件数、别名等）。
    """
    path = _log_path(game_root)
    path.parent.mkdir(parents=True, exist_ok=True)

    entries: list[dict] = []
    if path.exists():
        try:
            entries = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            entries = []

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "mod_id": mod_id,
        "game_id": game_id,
        "details": details or {},
    }
    entries.append(entry)

    path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_last_operation(game_root: Path) -> dict[str, Any] | None:
    """读取最后一条操作记录（不删除）。"""
    path = _log_path(game_root)
    if not path.exists():
        return None
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not entries:
        return None
    return entries[-1]


def pop_last_operation(game_root: Path) -> dict[str, Any] | None:
    """弹出（读取并删除）最后一条操作记录。

    用于 undo: 读取后移除，防止重复回退。
    """
    path = _log_path(game_root)
    if not path.exists():
        return None
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not entries:
        return None

    last = entries.pop()
    path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return last


def list_operations(game_root: Path, limit: int = 10) -> list[dict[str, Any]]:
    """列出最近 N 条操作记录（最新在前）。"""
    path = _log_path(game_root)
    if not path.exists():
        return []
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return list(reversed(entries[-limit:]))
