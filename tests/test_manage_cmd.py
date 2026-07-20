"""M12 测试: manage 命令集 (uninstall/switch/rename/list)"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from wds.installer import install_mod
from wds.models import GameInfo
from wds.scanner import discover_games


def _get_ep14_game(mock_wds_root: Path) -> tuple[Path, GameInfo]:
    """获取 mock 中的 EP14 游戏"""
    games = discover_games(mock_wds_root)
    ep14 = [g for g in games if g.game_id == "EP14"][0]
    return (mock_wds_root, ep14)


# ===========================================================================
# uninstall
# ===========================================================================


class TestRunUninstall:
    def test_mod_not_found(self, capsys: Any, mock_wds_root: Path):
        from wds.cli.manage_cmd import run_uninstall
        run_uninstall(
            wds_root=mock_wds_root, mod_id="nonexistent_mod", game_id_arg="EP14",
        )
        captured = capsys.readouterr()
        assert "未在" in captured.out or "未发现任何" in captured.out

    def test_game_not_found(self, capsys: Any, mock_wds_root: Path):
        from wds.cli.manage_cmd import run_uninstall
        run_uninstall(
            wds_root=mock_wds_root, mod_id="some_mod", game_id_arg="NONEXIST",
        )
        captured = capsys.readouterr()
        assert "未找到" in captured.out

    def test_uninstall_success(
        self, capsys: Any, mock_wds_root: Path, mock_mod_root: Path,
    ):
        from wds.cli.manage_cmd import run_uninstall

        # First install a mod
        games = discover_games(mock_wds_root)
        ep14 = [g for g in games if g.game_id == "EP14"][0]
        _preinstall_mod(ep14, mock_mod_root)

        run_uninstall(
            wds_root=mock_wds_root, mod_id="hawkeyes_ep14", game_id_arg="EP14",
        )
        captured = capsys.readouterr()
        assert "已卸载" in captured.out or "没有激活" in captured.out
        assert "备份池位于" in captured.out


# ===========================================================================
# switch
# ===========================================================================


class TestRunSwitch:
    def test_no_on_or_off(self, capsys: Any, mock_wds_root: Path):
        from wds.cli.manage_cmd import run_switch
        run_switch(
            wds_root=mock_wds_root, mod_id="foo",
            on=False, off=False, game_id_arg="EP14",
        )
        captured = capsys.readouterr()
        assert "请指定" in captured.out

    def test_switch_off(
        self, capsys: Any, mock_wds_root: Path, mock_mod_root: Path,
    ):
        from wds.cli.manage_cmd import run_switch

        games = discover_games(mock_wds_root)
        ep14 = [g for g in games if g.game_id == "EP14"][0]
        _preinstall_mod(ep14, mock_mod_root)

        run_switch(
            wds_root=mock_wds_root, mod_id="hawkeyes_ep14",
            on=False, off=True, game_id_arg="EP14",
        )
        captured = capsys.readouterr()
        assert "已禁用" in captured.out or "无可操作" in captured.out
        assert "备份池位于" in captured.out


# ===========================================================================
# rename
# ===========================================================================


class TestRunRename:
    def test_rename_success(
        self, capsys: Any, mock_wds_root: Path, mock_mod_root: Path,
    ):
        from wds.cli.manage_cmd import run_rename
        from wds.registry import load_registry

        games = discover_games(mock_wds_root)
        ep14 = [g for g in games if g.game_id == "EP14"][0]
        _preinstall_mod(ep14, mock_mod_root)

        run_rename(
            wds_root=mock_wds_root, mod_id="hawkeyes_ep14",
            new_name="Renamed Mod", game_id_arg="EP14",
        )
        captured = capsys.readouterr()
        assert "Renamed Mod" in captured.out

        # Verify registry update
        registry = load_registry(ep14.root_path)
        assert registry.mods["hawkeyes_ep14"].display_name == "Renamed Mod"

    def test_rename_nonexistent_mod(self, capsys: Any, mock_wds_root: Path):
        from wds.cli.manage_cmd import run_rename
        run_rename(
            wds_root=mock_wds_root, mod_id="no_such_mod",
            new_name="New Name", game_id_arg="EP14",
        )
        captured = capsys.readouterr()
        assert "未在" in captured.out or "未发现任何" in captured.out


# ===========================================================================
# list
# ===========================================================================


class TestRunList:
    def test_no_games(self, capsys: Any, tmp_path: Path):
        from wds.cli.manage_cmd import run_list
        empty = tmp_path / "empty"
        empty.mkdir()
        run_list(wds_root=empty, all_games=False)
        captured = capsys.readouterr()
        assert "未发现任何 WDS 游戏" in captured.out

    def test_list_all_no_mods(self, capsys: Any, mock_wds_root: Path):
        from wds.cli.manage_cmd import run_list
        run_list(wds_root=mock_wds_root, all_games=False)
        captured = capsys.readouterr()
        assert "均未安装" in captured.out or "未发现" in captured.out

    def test_list_all_with_all_flag(self, capsys: Any, mock_wds_root: Path):
        from wds.cli.manage_cmd import run_list
        run_list(wds_root=mock_wds_root, all_games=True)
        captured = capsys.readouterr()
        # With --all, should list games even without mods
        assert "EP14" in captured.out
        assert "M41" in captured.out

    def test_list_with_mod_installed(
        self, capsys: Any, mock_wds_root: Path, mock_mod_root: Path,
    ):
        from wds.cli.manage_cmd import run_list

        games = discover_games(mock_wds_root)
        ep14 = [g for g in games if g.game_id == "EP14"][0]
        _preinstall_mod(ep14, mock_mod_root)

        run_list(wds_root=mock_wds_root, all_games=False)
        captured = capsys.readouterr()
        assert "hawkeyes_ep14" in captured.out


# ===========================================================================
# 辅助: 预安装一个 mod（跳过 CLI 交互）
# ===========================================================================


def _preinstall_mod(game_info: GameInfo, mod_path: Path) -> None:
    """在指定游戏上安装 mod（直接调用 installer）"""
    from wds.matcher import scan_mod

    results = scan_mod(mod_path, game_info)
    mappings = _scan_results_to_mappings(results)

    install_mod(
        game_root=game_info.root_path,
        game_info=game_info,
        mod_path=mod_path,
        mappings=mappings,
    )


def _scan_results_to_mappings(
    scan_results: list[tuple[str, str | None, str]],
) -> list:
    """复制 install_cmd 的内部转换逻辑"""
    from wds.models import PathMapping

    pairs: set[tuple[str, str, str]] = set()
    for mod_file, game_target, confidence in scan_results:
        if game_target is None:
            continue
        mod_dir = mod_file.rsplit("/", 1)[0] if "/" in mod_file else ""
        game_dir = game_target.rsplit("/", 1)[0] if "/" in game_target else ""
        if mod_dir:
            pairs.add((mod_dir, game_dir, confidence))

    mappings: list[PathMapping] = []
    for mod_dir, game_dir, confidence in sorted(pairs):
        conf = "auto" if confidence == "auto" else "user_confirmed"
        mappings.append(PathMapping(
            mod_subfolder=mod_dir,
            game_target=game_dir,
            confidence=conf,
            resolved_by="leaf_match" if confidence == "auto" else "intersection",
        ))
    return mappings
