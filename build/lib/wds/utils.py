"""M02: 工具函数

全项目复用的纯函数：哈希计算、路径操作、命名转换、文件收集。
无副作用（collect_* 系列仅读取文件系统，不修改）。
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


# ===========================================================================
# 哈希
# ===========================================================================

def file_hash(path: Path) -> str:
    """计算文件的 SHA-256 哈希，返回 64 位 hex 字符串。

    分块读取以支持大文件（BMP 通常不大，但保持健壮性）。
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


# ===========================================================================
# 路径操作
# ===========================================================================

def normalize_path(p: str) -> str:
    """统一路径分隔符为正斜杠，去除首尾空白。

    >>> normalize_path("German\\\\Units\\\\Infantry.bmp")
    'German/Units/Infantry.bmp'
    """
    return p.strip().replace("\\", "/")


# ===========================================================================
# 命名转换
# ===========================================================================

def _split_camel_case(name: str) -> list[str]:
    """将 CamelCase 拆分为单词列表。

    "EastPrussia" → ["East", "Prussia"]
    "Smolensk"    → ["Smolensk"]
    """
    # 在大写字母前插入空格（但不在字符串开头）
    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
    return spaced.split()


def game_id_from_name(full_name: str) -> str:
    """从游戏全名生成缩写: 地名首字母(大写) + 两位年份。

    规则:
    - 提取末尾的年份数字（'43, 40, '14 等）
    - 地名部分按空格和 CamelCase 拆分为单词
    - 取每个单词首字母大写拼接
    - 无年份时仅返回首字母

    示例:
        "Smolensk '43"           → "S43"
        "Moscow '41"             → "M41"
        "France 40"              → "F40"
        "EastPrussia' 14"        → "EP14"
        "North German Plain '85" → "NGP85"
    """
    name = full_name.strip()

    # 提取年份: 匹配末尾的 'XX 或 XX（两位数字）
    year_match = re.search(r"['\u2019]?\s*(\d{2})\s*$", name)
    year = ""
    if year_match:
        year = year_match.group(1)
        name = name[: year_match.start()].strip()

    # 按空格拆分，再对每个部分做 CamelCase 拆分
    words: list[str] = []
    for part in name.split():
        words.extend(_split_camel_case(part))

    # 取首字母
    initials = "".join(w[0].upper() for w in words if w)

    return initials + year


def mod_id_from_filename(filename: str) -> str:
    """从 zip/目录文件名生成 mod_id。

    规则:
    1. 去扩展名
    2. 转小写
    3. 非字母数字字符替换为下划线
    4. 去除尾部 "_mod" / "_mods" 后缀
    5. 合并连续下划线，去首尾下划线

    示例:
        "Hawkeyes_F40_Mod.zip"                → "hawkeyes_f40"
        "Hawkeye's B44 Mod.zip"               → "hawkeye_s_b44"
        "Jison's Style Mods New Titles Mods.7z" → "jison_s_style_mods_new_titles"
    """
    # 去扩展名（用 suffix 判断，避免 ".zip" 这种 dotfile 被误处理）
    p = Path(filename)
    name = p.stem if p.suffix else filename

    # 转小写
    name = name.lower()

    # 非字母数字 → 下划线
    name = re.sub(r"[^a-z0-9]", "_", name)

    # 合并连续下划线
    name = re.sub(r"_+", "_", name)

    # 去首尾下划线
    name = name.strip("_")

    # 去尾部 _mod / _mods
    name = re.sub(r"_mods?$", "", name)

    return name


# ===========================================================================
# 目录排除
# ===========================================================================

# 扫描时应排除的目录名（精确匹配）
_EXCLUDED_DIRS: frozenset[str] = frozenset({
    "_backup",
    "Logs",
    "Saves",
    "Manuals",
    "Tools",
    "WDSEE",
    "SumatraPDF",
    "__pycache__",
})


def is_excluded_dir(name: str) -> bool:
    """判断目录名是否应在扫描中排除。

    排除: _backup, Logs, Saves, Manuals, Tools, WDSEE, SumatraPDF, __pycache__
    """
    return name in _EXCLUDED_DIRS


# ===========================================================================
# 文件收集
# ===========================================================================

def collect_bmp_files(directory: Path) -> dict[str, Path]:
    """递归收集目录下所有 .bmp 文件（不区分大小写）。

    返回: {相对路径(正斜杠) → 绝对路径}
    排除 is_excluded_dir 返回 True 的子目录。
    """
    return collect_all_files(directory, extensions={".bmp"})


def collect_all_files(
    directory: Path,
    extensions: set[str] | None = None,
) -> dict[str, Path]:
    """递归收集目录下指定扩展名的文件。

    Args:
        directory: 要扫描的根目录
        extensions: 扩展名集合（小写，含点号，如 {".bmp", ".dat"}）。
                    None = 收集全部文件。
                    空集合 = 不匹配任何文件，返回 {}。

    返回: {相对路径(正斜杠) → 绝对路径}
    排除 is_excluded_dir 返回 True 的子目录。
    """
    if extensions is not None and len(extensions) == 0:
        return {}

    # 统一扩展名为小写
    if extensions is not None:
        extensions = {ext.lower() for ext in extensions}

    result: dict[str, Path] = {}

    def _walk(dir_path: Path, rel_prefix: str) -> None:
        try:
            entries = sorted(dir_path.iterdir())
        except PermissionError:
            return

        for entry in entries:
            if entry.is_dir():
                if is_excluded_dir(entry.name):
                    continue
                child_prefix = f"{rel_prefix}{entry.name}/" if rel_prefix else f"{entry.name}/"
                _walk(entry, child_prefix)
            elif entry.is_file():
                if extensions is None or entry.suffix.lower() in extensions:
                    rel_path = f"{rel_prefix}{entry.name}" if rel_prefix else entry.name
                    result[rel_path] = entry.resolve()

    _walk(directory, "")
    return result
