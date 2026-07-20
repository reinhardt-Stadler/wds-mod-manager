"""M13: 输出格式化 — Rich 表格、面板、进度条、彩色消息"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn
from rich.style import Style
from rich.table import Table
from rich.text import Text

from wds.models import ModState

# 全局 Console 实例（单例）
_console = Console()

# ===========================================================================
# 状态符号映射
# ===========================================================================

_MOD_STATE_SYMBOLS = {
    ModState.FULL: ("■", "已安装", "green"),
    ModState.PARTIAL: ("◐", "部分", "yellow"),
    ModState.INACTIVE: ("□", "未安装", "dim"),
}

_CONFIDENCE_SYMBOLS = {
    "auto": ("✓", "自动", "green"),
    "ambiguous": ("⚠", "歧义", "yellow"),
    "unmatched": ("✗", "无匹配", "red"),
}


def _state_cell(state: ModState) -> Text:
    """生成 ModState 的格式化单元格"""
    symbol, label, color = _MOD_STATE_SYMBOLS.get(state, ("?", "未知", "red"))
    return Text(f"[{symbol} {label}]", style=color)


def _confidence_cell(confidence: str) -> Text:
    """生成置信度的格式化单元格"""
    symbol, label, color = _CONFIDENCE_SYMBOLS.get(confidence, ("?", "未知", "red"))
    return Text(f"{symbol} {label}", style=color)


# ===========================================================================
# 彩色消息
# ===========================================================================


def print_success(msg: str) -> None:
    """绿色成功消息"""
    _console.print(f"[bold green]✓[/] {msg}")


def print_warning(msg: str) -> None:
    """黄色警告消息"""
    _console.print(f"[bold yellow]⚠[/] {msg}")


def print_error(msg: str) -> None:
    """红色错误消息"""
    _console.print(f"[bold red]✗[/] {msg}")


def print_info(msg: str) -> None:
    """蓝色信息消息"""
    _console.print(f"[bold blue]i[/] {msg}")


def print_header(title: str) -> None:
    """打印带装饰线的标题"""
    _console.print()
    _console.print(f"[bold]{title}[/]")
    _console.print("─" * min(len(title), 72))


def print_divider() -> None:
    """打印分隔线"""
    _console.print("─" * 72, style="dim")


# ===========================================================================
# 进度条
# ===========================================================================


def create_progress() -> Progress:
    """创建统一的 Rich 进度条"""
    return Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=_console,
    )


# ===========================================================================
# scan 映射表
# ===========================================================================


def print_scan_table(
    mappings: list[tuple[str, str | None, str]],
    mod_path_str: str = "",
    game_info_str: str = "",
) -> None:
    """打印 scan 结果的路径映射表

    Args:
        mappings: scan_mod 的返回结果 [(mod_file, game_target, confidence), ...]
        mod_path_str: mod 来源路径（显示在表头）
        game_info_str: 目标游戏信息（显示在表头）
    """
    # 表头
    if game_info_str:
        print_header(f"目标游戏: {game_info_str}")
    if mod_path_str:
        _console.print(f"Mod 来源: [cyan]{mod_path_str}[/]")

    # 统计
    total = len(mappings)
    auto_count = sum(1 for _, _, c in mappings if c == "auto")
    ambig_count = sum(1 for _, _, c in mappings if c == "ambiguous")
    unmatch_count = sum(1 for _, _, c in mappings if c == "unmatched")

    table = Table(show_edge=False, pad_edge=False, box=None)
    table.add_column("Mod 路径", style="cyan", no_wrap=True, ratio=2)
    table.add_column("", width=3)  # 箭头
    table.add_column("游戏目标路径", style="white", no_wrap=True, ratio=2)
    table.add_column("置信度", style="white", no_wrap=True)

    for mod_file, game_target, confidence in mappings:
        target_str = game_target if game_target else "???"
        arrow = "→" if game_target else " "
        conf_cell = _confidence_cell(confidence)

        table.add_row(mod_file, arrow, target_str, conf_cell)

    _console.print(table)
    _console.print(
        f"[dim]总计 {total} 个文件 | "
        f"[green]✓ {auto_count} 自动[/] | "
        f"[yellow]⚠ {ambig_count} 歧义[/] | "
        f"[red]✗ {unmatch_count} 无匹配[/]"
    )


# ===========================================================================
# status 面板
# ===========================================================================


def print_status_panel(
    game_name: str,
    summary: list[dict[str, Any]],
    registry_exists: bool = True,
) -> None:
    """打印 status 开关面板

    Args:
        game_name: 游戏全名（如 "Moscow '41"）
        summary: get_status_summary 的返回结果
        registry_exists: 该游戏是否已有注册表
    """
    title = f"{game_name} — 美化包状态"
    print_header(title)

    if not registry_exists or not summary:
        _console.print("[dim]未安装任何美化包[/]")
        _console.print()
        return

    table = Table(show_edge=False, pad_edge=False, box=None)
    table.add_column("美化包", style="white", no_wrap=True, ratio=3)
    table.add_column("状态", style="white", no_wrap=True)
    table.add_column("覆盖文件", style="white", justify="right")
    table.add_column("别名", style="dim", no_wrap=True, ratio=1)

    # 收集 PARTIAL mod 的详情（用于子行显示哪些文件被其他 mod 覆盖）
    partial_details: dict[str, list[str]] = {}
    for entry in summary:
        if entry["state"] == ModState.PARTIAL:
            mod_id = entry["mod_id"]
            details = _compute_partial_detail(summary, entry)
            if details:
                partial_details[mod_id] = details

    for entry in summary:
        display_name = entry["display_name"]
        state = entry["state"]
        active = entry["active_count"]
        total = entry["total_count"]

        state_cell = _state_cell(state)

        if state == ModState.FULL:
            file_cell = f"{total} 个文件"
        else:
            file_cell = f"{active}/{total} 个"

        table.add_row(display_name, state_cell, file_cell, "")

        # PARTIAL 详情子行
        if state == ModState.PARTIAL and entry["mod_id"] in partial_details:
            for detail in partial_details[entry["mod_id"]]:
                table.add_row(
                    f"  └─ {detail}",
                    "", "", "",
                    style="dim",
                )

    _console.print(table)
    _console.print("[dim]无归属 (原版)[/]  —  [dim]其余文件均为原版[/]")
    _console.print()


def _compute_partial_detail(
    summary: list[dict[str, Any]],
    partial_entry: dict[str, Any],
) -> list[str]:
    """为 PARTIAL 状态的 mod 计算被谁覆盖了哪些文件"""
    # 这个是展示辅助，从 summary 数据无法精确知道谁覆盖了什么，
    # 完整的实现需要 registry.files 数据。这里返回通用提示。
    mod_id = partial_entry["mod_id"]
    active = partial_entry["active_count"]
    total = partial_entry["total_count"]
    diff = total - active
    return [f"{diff} 个文件被其他 mod 覆盖"]


# ===========================================================================
# list 汇总
# ===========================================================================


def print_mod_list(
    games_data: list[dict[str, Any]],
) -> None:
    """打印所有游戏的 mod 汇总

    Args:
        games_data: [
            {
                "game_id": str,
                "full_name": str,
                "mods": [{"mod_id", "display_name", "state", "active_count", "total_count"}, ...],
                "mod_count": int,
            },
            ...
        ]
    """
    total_games = len(games_data)
    total_mods = sum(g.get("mod_count", 0) for g in games_data)

    print_header(f"已发现游戏 ({total_games}) — 共 {total_mods} 个美化包")

    if not games_data:
        _console.print("[dim]未发现任何 WDS 游戏[/]")
        _console.print()
        return

    for game in games_data:
        game_id = game["game_id"]
        full_name = game["full_name"]
        mods = game.get("mods", [])
        mod_count = game.get("mod_count", 0)

        header = f"[bold]{game_id}[/] ([cyan]{full_name}[/]) — {mod_count} 个 mod"
        _console.print(header)

        if not mods:
            _console.print("  [dim]无 mod[/]")
        else:
            for m in mods:
                state_cell = _state_cell(m["state"])
                display_name = m["display_name"]
                active = m["active_count"]
                total = m["total_count"]

                if m["state"] == ModState.FULL:
                    file_info = f"{total}/{total} 文件"
                elif m["state"] == ModState.INACTIVE:
                    file_info = f"0/{total} 文件"
                else:
                    file_info = f"{active}/{total} 文件"

                _console.print(
                    f"  {state_cell} [white]{m['mod_id']:<20}[/] "
                    f"{display_name:<30} {file_info}"
                )

        print_divider()


# ===========================================================================
# 交互式路径识别 (review)
# ===========================================================================


def print_review_group(
    index: int,
    total: int,
    mod_subfolder: str,
    proposed_target: str | None,
    confidence: str,
    file_count: int,
) -> None:
    """打印交互识别中单个目录组的标题行与操作提示

    Args:
        index: 当前组序号（从 1 开始）
        total: 总组数
        mod_subfolder: mod 源目录（"" 表示 mod 根目录）
        proposed_target: 建议的游戏目标目录，None = 整组无匹配
        confidence: 组级置信度 auto/ambiguous/unmatched
        file_count: 组内文件数
    """
    symbol, label, color = _CONFIDENCE_SYMBOLS.get(confidence, ("?", "未知", "red"))
    src = f"{mod_subfolder}/" if mod_subfolder else "(根目录)"

    if proposed_target is not None:
        tgt = f"{proposed_target}/"
        arrow = "→"
    else:
        tgt = "(无匹配)"
        arrow = " "

    _console.print()
    _console.print(
        f"[bold][{index}/{total}][/] [cyan]{src}[/] {arrow} "
        f"[white]{tgt}[/]  [{color}]{symbol} {label}[/] · {file_count} 个文件"
    )
    if proposed_target is None:
        _console.print("    [red]此组无建议目标，需指定目标目录或跳过[/]")
        _console.print("    [dim]e=输入目标路径  v=查看文件  s=跳过  q=退出[/]")
    else:
        _console.print("    [dim]Enter=接受  e=改目标  v=查看文件  s=跳过  q=退出[/]")


def print_review_files(files: list[tuple[str, str | None, str]]) -> None:
    """展开打印组内每个文件的映射明细

    Args:
        files: [(mod_rel, proposed_target, confidence), ...]
    """
    for mod_rel, target, confidence in files:
        symbol, _, color = _CONFIDENCE_SYMBOLS.get(confidence, ("?", "red"))
        tgt = target if target else "???"
        _console.print(
            f"      [cyan]{mod_rel}[/] → [white]{tgt}[/]  [{color}]{symbol}[/]"
        )


# ===========================================================================
# 备份提示
# ===========================================================================


def print_backup_hint(game_root: Path) -> None:
    """在替换/管理工作完成后提醒用户备份池位置"""
    _console.print(
        f"[dim]备份池位于: {game_root / '_backup'}"
        f"（含原版基准与 mod 副本，请勿手动删除）[/]"
    )
