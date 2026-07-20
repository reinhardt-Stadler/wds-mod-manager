"""M01: 核心数据结构

定义全项目共享的数据类，所有模块的输入输出类型。
每个 dataclass 提供 to_dict() / from_dict() 用于 JSON 序列化往返。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


# ===========================================================================
# 枚举
# ===========================================================================

class FileStatus(Enum):
    """单个游戏文件的生命周期状态"""
    ORIGINAL = "original"
    REPLACED = "replaced"
    ROLLED_BACK = "rolled_back"
    MODIFIED = "modified"


class ModState(Enum):
    """mod 在 status 面板中的三态"""
    FULL = "full"         # ■ 已安装（全部激活）
    PARTIAL = "partial"   # ◐ 部分（部分被其他 mod 覆盖）
    INACTIVE = "inactive" # □ 未安装（已注册但未激活）


# ===========================================================================
# 序列化辅助
# ===========================================================================

def _path_to_str(p: Path | PurePosixPath | PureWindowsPath | str) -> str:
    """Path → 正斜杠字符串（统一序列化格式）"""
    return str(p).replace("\\", "/")


def _str_to_path(s: str) -> Path:
    """字符串 → Path"""
    return Path(s)


# ===========================================================================
# 数据类
# ===========================================================================

@dataclass
class GameInfo:
    """一个已发现的 WDS 游戏"""
    game_id: str              # 缩写: "S43", "M41", "EP14"
    full_name: str            # "Smolensk '43"
    root_path: Path           # 游戏根目录绝对路径
    exe_name: str             # "eastprussia14.exe"
    nations: list[str]        # ["German", "German-SS", "Russian", ...]
    has_original_backup: bool # _backup/{game_id}_original/ 是否存在

    def to_dict(self) -> dict[str, Any]:
        return {
            "game_id": self.game_id,
            "full_name": self.full_name,
            "root_path": _path_to_str(self.root_path),
            "exe_name": self.exe_name,
            "nations": list(self.nations),
            "has_original_backup": self.has_original_backup,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GameInfo:
        return cls(
            game_id=d["game_id"],
            full_name=d["full_name"],
            root_path=_str_to_path(d["root_path"]),
            exe_name=d["exe_name"],
            nations=list(d["nations"]),
            has_original_backup=d["has_original_backup"],
        )


@dataclass
class ModFileEntry:
    """单个文件的替换记录"""
    game_file: str            # 游戏内相对路径: "German/2DSymbolsLg.bmp"
    mod_file: str             # mod 内相对路径
    backup_path: str          # 备份相对路径: "_backup/hawkeyes_f40/German/..."
    original_hash: str        # SHA-256 of 原版文件
    mod_hash: str             # SHA-256 of mod 文件
    status: FileStatus        # 文件当前状态

    def to_dict(self) -> dict[str, Any]:
        return {
            "game_file": self.game_file,
            "mod_file": self.mod_file,
            "backup_path": self.backup_path,
            "original_hash": self.original_hash,
            "mod_hash": self.mod_hash,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ModFileEntry:
        return cls(
            game_file=d["game_file"],
            mod_file=d["mod_file"],
            backup_path=d["backup_path"],
            original_hash=d["original_hash"],
            mod_hash=d["mod_hash"],
            status=FileStatus(d["status"]),
        )


@dataclass
class ModInfo:
    """一个美化包的完整信息"""
    mod_id: str               # "hawkeyes_f40" (来自 zip 文件名)
    game_id: str              # "F40"
    display_name: str         # 用户自定义别名, 默认 = mod_id
    source_path: Path         # mod 源文件/目录路径
    install_time: str         # ISO-8601
    file_count: int           # 覆盖的文件总数
    active_count: int         # 当前激活的文件数

    def to_dict(self) -> dict[str, Any]:
        return {
            "mod_id": self.mod_id,
            "game_id": self.game_id,
            "display_name": self.display_name,
            "source_path": _path_to_str(self.source_path),
            "install_time": self.install_time,
            "file_count": self.file_count,
            "active_count": self.active_count,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ModInfo:
        return cls(
            mod_id=d["mod_id"],
            game_id=d["game_id"],
            display_name=d["display_name"],
            source_path=_str_to_path(d["source_path"]),
            install_time=d["install_time"],
            file_count=d["file_count"],
            active_count=d["active_count"],
        )


@dataclass
class PathMapping:
    """一条路径映射记录（mod 子目录 → 游戏目标目录）"""
    mod_subfolder: str        # mod 内的子目录
    game_target: str          # 游戏内目标目录
    confidence: str           # "auto" | "user_confirmed"
    resolved_by: str          # "leaf_match" | "intersection" | "manual"

    def to_dict(self) -> dict[str, Any]:
        return {
            "mod_subfolder": self.mod_subfolder,
            "game_target": self.game_target,
            "confidence": self.confidence,
            "resolved_by": self.resolved_by,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PathMapping:
        return cls(
            mod_subfolder=d["mod_subfolder"],
            game_target=d["game_target"],
            confidence=d["confidence"],
            resolved_by=d["resolved_by"],
        )


@dataclass
class SourceVersion:
    """某个 mod 为某个文件提供的版本"""
    file_path: str     # 在 _backup/ 中的存储路径
    hash: str          # SHA-256
    installed_at: str  # ISO-8601

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "hash": self.hash,
            "installed_at": self.installed_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SourceVersion:
        return cls(
            file_path=d["file_path"],
            hash=d["hash"],
            installed_at=d["installed_at"],
        )


@dataclass
class FileAttribution:
    """单个游戏文件的归属信息"""
    original_backup: str               # 原版备份路径
    active_source: str | None          # 当前激活的 mod_id, None=原版
    sources: dict[str, SourceVersion]  # mod_id → 该 mod 提供的版本

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_backup": self.original_backup,
            "active_source": self.active_source,
            "sources": {
                mod_id: sv.to_dict() for mod_id, sv in self.sources.items()
            },
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> FileAttribution:
        return cls(
            original_backup=d["original_backup"],
            active_source=d["active_source"],
            sources={
                mod_id: SourceVersion.from_dict(sv)
                for mod_id, sv in d["sources"].items()
            },
        )


@dataclass
class GameRegistry:
    """单个游戏的完整注册表 (对应 _backup/game_registry.json)

    这是顶层持久化对象，包含该游戏所有已安装 mod 的信息
    和每个被替换文件的归属记录。
    """
    game_id: str
    mods: dict[str, ModInfo]           # mod_id → ModInfo
    files: dict[str, FileAttribution]  # game_file_path → 归属信息
    original_backup: str               # "_backup/EP14_original"

    def to_dict(self) -> dict[str, Any]:
        return {
            "game_id": self.game_id,
            "mods": {
                mod_id: mi.to_dict() for mod_id, mi in self.mods.items()
            },
            "files": {
                path: fa.to_dict() for path, fa in self.files.items()
            },
            "original_backup": self.original_backup,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GameRegistry:
        return cls(
            game_id=d["game_id"],
            mods={
                mod_id: ModInfo.from_dict(mi)
                for mod_id, mi in d["mods"].items()
            },
            files={
                path: FileAttribution.from_dict(fa)
                for path, fa in d["files"].items()
            },
            original_backup=d["original_backup"],
        )

    def save(self, path: Path) -> None:
        """将注册表写入 JSON 文件"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> GameRegistry:
        """从 JSON 文件读取注册表"""
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)
