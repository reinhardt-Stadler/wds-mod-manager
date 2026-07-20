# Copyright (c) 2026 Reinhardt Stadler. All Rights Reserved.
"""M10a: 交互式路径识别

将 scan_mod 的文件级匹配结果按 mod 源目录分组，逐组交付用户审查：
无论是否匹配得上都停下来，用户可接受建议、修改目标目录、展开查看组内
单文件、或跳过该组。最终产出 install_mod 可消费的目录级 PathMapping 列表。

设计要点 (D-013):
- 粒度: 按目录组审查，组内可展开查看单文件明细。
- --yes 场景不走本模块（由 install_cmd 直接用自动匹配结果）。
- 无匹配组必须显式指定目标或跳过，不允许直接接受。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

from wds.cli.display import (
    print_review_files,
    print_review_group,
    print_warning,
)
from wds.models import PathMapping


# ===========================================================================
# 数据结构
# ===========================================================================


@dataclass
class FilePreview:
    """组内单个文件的映射预览"""

    mod_rel: str                    # mod 内相对路径, e.g. "German/Flag.bmp"
    proposed_target: str | None     # 建议的游戏相对路径, None = 无匹配
    confidence: str                 # auto / ambiguous / unmatched


@dataclass
class ReviewGroup:
    """一个 mod 源目录 → 游戏目标目录 的审查组"""

    mod_subfolder: str              # mod 源目录, "" = mod 根目录
    proposed_target: str | None     # 建议的游戏目标目录, None = 整组无匹配
    confidence: str                 # 组级置信度
    files: list[FilePreview] = field(default_factory=list)
    # 用户决策结果:
    final_target: str | None = None
    skipped: bool = False


# ===========================================================================
# 分组
# ===========================================================================


def _dir_of(rel_path: str) -> str:
    """取相对路径的目录部分（正斜杠），根级文件返回 ''"""
    return rel_path.rsplit("/", 1)[0] if "/" in rel_path else ""


def _aggregate_confidence(confs: set[str]) -> str:
    """聚合组级置信度: 全 auto→auto, 全 unmatched→unmatched, 其余→ambiguous"""
    if confs == {"auto"}:
        return "auto"
    if confs == {"unmatched"}:
        return "unmatched"
    return "ambiguous"


def build_review_groups(
    scan_results: list[tuple[str, str | None, str]],
) -> list[ReviewGroup]:
    """将 scan_mod 的文件级结果按 mod 源目录分组。

    Args:
        scan_results: [(mod_file, game_target, confidence), ...]

    Returns:
        按 mod 源目录排序的 ReviewGroup 列表。
    """
    bucket: dict[str, list[FilePreview]] = {}
    for mod_file, game_target, confidence in scan_results:
        sub = _dir_of(mod_file)
        bucket.setdefault(sub, []).append(
            FilePreview(mod_rel=mod_file, proposed_target=game_target, confidence=confidence)
        )

    groups: list[ReviewGroup] = []
    for sub in sorted(bucket.keys()):
        files = bucket[sub]

        # 建议目标: 取组内文件目标目录的多数派
        target_dirs = [
            _dir_of(f.proposed_target) for f in files if f.proposed_target is not None
        ]
        if target_dirs:
            proposed_target = Counter(target_dirs).most_common(1)[0][0]
        else:
            proposed_target = None

        confidence = _aggregate_confidence({f.confidence for f in files})
        groups.append(
            ReviewGroup(
                mod_subfolder=sub,
                proposed_target=proposed_target,
                confidence=confidence,
                files=files,
            )
        )

    return groups


# ===========================================================================
# 交互式审查
# ===========================================================================


def _normalize_target(raw: str) -> str:
    """规范化用户输入的目标目录: 反斜杠转正斜杠，去首尾斜杠"""
    return raw.replace("\\", "/").strip("/")


def _default_input(prompt: str) -> str:
    """默认输入函数: 走内置 input()"""
    return input(prompt)


def run_interactive_review(
    groups: list[ReviewGroup],
    *,
    input_fn: Callable[[str], str] | None = None,
) -> list[PathMapping] | None:
    """逐组交互式审查，返回最终 PathMapping 列表。

    Args:
        groups: build_review_groups 的产出。
        input_fn: 输入函数 (prompt) -> str，测试时注入脚本化输入；
                  默认使用内置 input()。

    Returns:
        用户确认后的 PathMapping 列表；若用户中途退出 (q) 则返回 None。
    """
    if input_fn is None:
        input_fn = _default_input

    mappings: list[PathMapping] = []
    total = len(groups)

    for index, group in enumerate(groups, start=1):
        print_review_group(
            index=index,
            total=total,
            mod_subfolder=group.mod_subfolder,
            proposed_target=group.proposed_target,
            confidence=group.confidence,
            file_count=len(group.files),
        )

        while True:
            choice = input_fn("    操作 > ").strip().lower()

            if choice in ("", "y", "a"):
                if group.proposed_target is None:
                    print_warning("此组无建议目标，请输入 e 指定目标路径，或 s 跳过")
                    continue
                group.final_target = group.proposed_target
                break

            if choice == "e":
                raw = input_fn("    新目标路径 > ").strip()
                if not raw:
                    print_warning("目标路径不能为空，请重新输入")
                    continue
                group.final_target = _normalize_target(raw)
                break

            if choice == "v":
                print_review_files(
                    [(f.mod_rel, f.proposed_target, f.confidence) for f in group.files]
                )
                continue

            if choice == "s":
                group.skipped = True
                break

            if choice == "q":
                return None

            print_warning(f"无效选择: '{choice}'（可用: Enter / e / v / s / q）")

        if not group.skipped and group.final_target is not None:
            mappings.append(
                PathMapping(
                    mod_subfolder=group.mod_subfolder,
                    game_target=group.final_target,
                    confidence="user_confirmed",
                    resolved_by="manual",
                )
            )

    return mappings
