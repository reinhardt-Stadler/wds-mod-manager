"""M08: WDS Mod Manager — Typer 主应用入口

提供全局选项、子命令注册、自管理命令（-un/-u/-help）和启动横幅。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import typer

from wds import __version__
from wds.cli.display import print_error, print_info
from wds.cli.install_cmd import run_install
from wds.cli.manage_cmd import run_list, run_rename, run_switch, run_uninstall
from wds.cli.scan_cmd import run_scan
from wds.cli.status_cmd import run_status

app = typer.Typer(
    name="wds",
    help="WDS 图包管理工具 — 安装、切换、回滚美化包",
    add_completion=False,
    no_args_is_help=False,
)

# 默认 WDS 根目录: 环境变量 WDS_ROOT 或 D:\WDS
DEFAULT_WDS_ROOT = Path("D:\\WDS")

# 远程仓库地址（wds -u 更新源，部署时替换为实际地址）
UPDATE_REPO_URL = "git+https://github.com/USER/wds-mod-manager.git"


def _resolve_wds_root(value: str | None) -> Path:
    """解析 WDS 根目录: CLI 参数 > 环境变量 > 默认值"""
    import os

    if value:
        return Path(value)
    env = os.environ.get("WDS_ROOT")
    if env:
        return Path(env)
    return DEFAULT_WDS_ROOT


# ===========================================================================
# 启动横幅
# ===========================================================================

BANNER = r"""
 ╔══════════════════════════════════════════════════════╗
 ║                                                     ║
 ║   _    _  ____   ____    __  __             _      ║
 ║  | |  | ||  _ \ / ___|  |  \/  | ___   __| | ___  ║
 ║  | |/\| || | | |\___ \  | |\/| |/ _ \ / _` |/ _ \ ║
 ║  \  /\  /| |_| | ___) | | |  | | (_) | (_| |  __/ ║
 ║   \/  \/ |____/ |____/  |_|  |_|\___/ \__,_|\___| ║
 ║                                                     ║
 ║   WDS 图包管理器  v{version:<33s}║
 ║                                                     ║
 ╚══════════════════════════════════════════════════════╝
""".format(version=__version__)

WELCOME_TEXT = """
  欢迎使用 WDS 图包管理器！

  快速上手:
    wds install <mod文件夹>     安装美化包（交互式路径审查）
    wds install <mod> --auto    安装美化包（全自动，跳过审查）
    wds scan <mod文件夹>        预览路径映射（不修改文件）
    wds status [游戏ID]         查看美化包安装状态
    wds switch <mod_id> --on    启用美化包
    wds switch <mod_id> --off   禁用美化包
    wds uninstall <mod_id>      卸载美化包（还原原版）
    wds ls-mods                 列出所有已注册美化包
    wds rename <mod_id> <名称>  修改美化包别名

  工具管理:
    wds -u                      更新到最新版本
    wds -un                     卸载本工具（可选还原所有美化包）
    wds -help                   查看完整使用说明
    wds --version               显示版本号

  提示: 美化包需先解压为文件夹再使用，暂不支持直接读取 zip/7z。
"""


def _show_banner():
    """显示启动横幅和快速上手指南"""
    typer.echo(BANNER)
    typer.echo(WELCOME_TEXT)


# ===========================================================================
# 自管理命令（-un / -u / -help）
# ===========================================================================


def _self_uninstall():
    """wds -un: 卸载工具自身，可选还原所有已安装美化包"""
    typer.echo(BANNER)
    typer.echo("  === 卸载 WDS 图包管理器 ===\n")

    # 检查是否有已安装的美化包
    wds_root = _resolve_wds_root(None)
    has_mods = False
    if wds_root.exists():
        from wds.scanner import discover_games
        from wds.registry import load_registry

        games = discover_games(wds_root)
        for game in games:
            reg = load_registry(game.root_path)
            if reg and reg.mods:
                has_mods = True
                break

    if has_mods:
        typer.echo("  检测到游戏中仍有已安装的美化包。")
        answer = input("  是否在卸载前还原所有美化包到原版？[Y/n] ").strip().lower()
        if answer in ("", "y", "yes"):
            typer.echo("\n  正在还原所有美化包...\n")
            from wds.installer import uninstall_mod
            from wds.scanner import discover_games as dg
            from wds.registry import load_registry as lr

            for game in dg(wds_root):
                reg = lr(game.root_path)
                if not reg or not reg.mods:
                    continue
                for mod_id in list(reg.mods.keys()):
                    try:
                        uninstall_mod(game.root_path, game, mod_id)
                        typer.echo(f"    ✓ {game.game_id}: {mod_id} 已还原")
                    except Exception as e:
                        typer.echo(f"    ✗ {game.game_id}: {mod_id} 还原失败 ({e})")
            typer.echo("\n  所有美化包已还原为原版。\n")
        else:
            typer.echo("  跳过还原，游戏文件保持当前状态。\n")

    # 执行 pip uninstall
    typer.echo("  正在卸载 wds-mod-manager ...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "uninstall", "wds-mod-manager", "-y"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        typer.echo("  ✓ 卸载完成。wds 命令已移除。")
    else:
        typer.echo(f"  ✗ 卸载失败:\n{result.stderr}")
    typer.echo()


def _self_update():
    """wds -u: 从远程仓库更新到最新版本"""
    typer.echo(f"\n  正在从远程仓库更新 wds-mod-manager ...")
    typer.echo(f"  源: {UPDATE_REPO_URL}\n")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", UPDATE_REPO_URL],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        # 获取新版本号
        from importlib.metadata import version as pkg_version
        try:
            new_ver = pkg_version("wds-mod-manager")
        except Exception:
            new_ver = "?"
        typer.echo(f"  ✓ 更新完成！当前版本: {new_ver}")
    else:
        typer.echo(f"  ✗ 更新失败:\n{result.stderr}")
        typer.echo("  请检查网络连接或仓库地址是否正确。")
    typer.echo()


def _show_help():
    """wds -help: 显示完整使用说明"""
    # 尝试打开项目目录下的使用说明文件
    doc_candidates = [
        Path(__file__).parent.parent.parent.parent / "docs" / "使用说明.md",
        Path(__file__).parent.parent.parent.parent / "README.md",
    ]
    for doc in doc_candidates:
        if doc.exists():
            typer.echo(f"\n  正在打开使用说明: {doc}\n")
            import os
            os.startfile(str(doc))  # Windows: 用默认程序打开
            return

    # 无文档文件时，输出内嵌帮助
    typer.echo(BANNER)
    typer.echo(WELCOME_TEXT)
    typer.echo("  ─────────────────────────────────────────────────────")
    typer.echo("  完整命令列表:\n")
    # 调用 Typer 内置帮助
    ctx = typer.Context(app)
    typer.echo(app.get_help(ctx))
    typer.echo()


# ===========================================================================
# 全局回调
# ===========================================================================


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", "-V", is_eager=True, help="显示版本号并退出",
    ),
    wds_root: str = typer.Option(
        None,
        "--wds-root",
        help="WDS 游戏根目录 (默认: 环境变量 WDS_ROOT 或 D:\\WDS)",
    ),
):
    """WDS Mod Manager"""
    if version:
        typer.echo(f"wds-mod-manager {__version__}")
        raise typer.Exit()
    ctx.obj = {"wds_root": _resolve_wds_root(wds_root)}

    # 无子命令时显示横幅
    if ctx.invoked_subcommand is None:
        _show_banner()


# ===========================================================================
# scan 命令
# ===========================================================================


@app.command()
def scan(
    ctx: typer.Context,
    mod_path: str = typer.Argument(
        ..., help="mod 目录或 zip 文件路径",
    ),
    game_id: str = typer.Option(
        None, "--game", "-g", help="目标游戏缩写 (如 M41)，不指定则自动推断",
    ),
):
    """扫描 mod 目录，展示路径映射表（不执行修改）"""
    wds_root = _require_wds_root(ctx)
    run_scan(
        wds_root=wds_root,
        mod_path=Path(mod_path),
        game_id_arg=game_id,
    )


# ===========================================================================
# install 命令
# ===========================================================================


@app.command()
def install(
    ctx: typer.Context,
    mod_path: str = typer.Argument(
        ..., help="mod 目录或 zip 文件路径",
    ),
    game_id: str = typer.Option(
        None, "--game", "-g", help="目标游戏缩写 (如 M41)，不指定则自动推断",
    ),
    name: str = typer.Option(
        None, "--name", "-n", help="美化包别名（默认使用目录/zip 文件名）",
    ),
    yes: bool = typer.Option(
        False, "--auto", help="跳过交互审查，直接使用自动匹配结果安装",
    ),
):
    """安装美化包到指定游戏"""
    wds_root = _require_wds_root(ctx)
    run_install(
        wds_root=wds_root,
        mod_path=Path(mod_path),
        game_id_arg=game_id,
        display_name_arg=name,
        yes=yes,
    )


# ===========================================================================
# status 命令
# ===========================================================================


@app.command()
def status(
    ctx: typer.Context,
    game_id: str = typer.Argument(
        None, help="游戏缩写 (如 M41)，不指定则显示所有游戏",
    ),
):
    """展示游戏的美化包安装状态"""
    wds_root = _require_wds_root(ctx)
    run_status(
        wds_root=wds_root,
        game_id_arg=game_id,
    )


# ===========================================================================
# uninstall 命令
# ===========================================================================


@app.command()
def uninstall(
    ctx: typer.Context,
    mod_id: str = typer.Argument(..., help="要卸载的美化包 ID"),
    game_id: str = typer.Option(
        None, "--game", "-g", help="游戏缩写 (如 M41)，不指定则自动推断",
    ),
):
    """卸载（禁用）指定美化包"""
    wds_root = _require_wds_root(ctx)
    run_uninstall(
        wds_root=wds_root,
        mod_id=mod_id,
        game_id_arg=game_id,
    )


# ===========================================================================
# switch 命令
# ===========================================================================


@app.command()
def switch(
    ctx: typer.Context,
    mod_id: str = typer.Argument(..., help="美化包 ID"),
    on: bool = typer.Option(False, "--on", help="启用美化包"),
    off: bool = typer.Option(False, "--off", help="禁用美化包"),
    game_id: str = typer.Option(
        None, "--game", "-g", help="游戏缩写 (如 M41)，不指定则自动推断",
    ),
):
    """启用或禁用指定美化包"""
    wds_root = _require_wds_root(ctx)
    run_switch(
        wds_root=wds_root,
        mod_id=mod_id,
        on=on,
        off=off,
        game_id_arg=game_id,
    )


# ===========================================================================
# rename 命令
# ===========================================================================


@app.command()
def rename(
    ctx: typer.Context,
    mod_id: str = typer.Argument(..., help="美化包 ID"),
    new_name: str = typer.Argument(..., help="新的显示名称"),
    game_id: str = typer.Option(
        None, "--game", "-g", help="游戏缩写 (如 M41)，不指定则自动推断",
    ),
):
    """修改美化包的显示别名"""
    wds_root = _require_wds_root(ctx)
    run_rename(
        wds_root=wds_root,
        mod_id=mod_id,
        new_name=new_name,
        game_id_arg=game_id,
    )


# ===========================================================================
# ls-mods 命令
# ===========================================================================


@app.command("ls-mods")
def list_mods(
    ctx: typer.Context,
    all_games: bool = typer.Option(
        False, "--all", "-a", help="列出所有游戏的 mod（不指定时仅显示有 mod 的游戏）",
    ),
):
    """列出所有已注册的美化包"""
    wds_root = _require_wds_root(ctx)
    run_list(
        wds_root=wds_root,
        all_games=all_games,
    )


# ===========================================================================
# 内部辅助
# ===========================================================================


def _require_wds_root(ctx: typer.Context) -> Path:
    """确保 wds_root 已解析，返回 Path"""
    obj = ctx.obj or {}
    wds_root = obj.get("wds_root", DEFAULT_WDS_ROOT)
    if not wds_root.exists():
        print_error(f"WDS 根目录不存在: {wds_root}")
        print_info("请通过 --wds-root 选项或 WDS_ROOT 环境变量设置正确的路径")
        raise typer.Exit(code=1)
    return wds_root


# ===========================================================================
# 入口（拦截 -un / -u / -help 自管理命令）
# ===========================================================================

_SELF_COMMANDS = {
    "-un": _self_uninstall,
    "--uninstall-tool": _self_uninstall,
    "-u": _self_update,
    "--update": _self_update,
    "-help": _show_help,
    "--doc": _show_help,
}


def run():
    """供 pyproject.toml [project.scripts] 调用的入口。

    拦截 -un / -u / -help 等自管理命令（不经过 Typer 解析），
    其余正常走 Typer app。
    """
    if len(sys.argv) >= 2 and sys.argv[1] in _SELF_COMMANDS:
        _SELF_COMMANDS[sys.argv[1]]()
        return
    app()


if __name__ == "__main__":
    run()
