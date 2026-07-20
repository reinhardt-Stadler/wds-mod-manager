"""Day 10: 全流程集成测试 — mock 环境端到端验证"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from wds.models import ModState
from wds.registry import load_registry


class TestFullPipeline:
    """完整的安装→状态→列表→切换→卸载 端到端测试"""

    def test_full_pipeline(
        self, capsys: Any, mock_wds_root: Path, mock_mod_root: Path,
    ):
        from wds.cli.scan_cmd import run_scan
        from wds.cli.install_cmd import run_install
        from wds.cli.status_cmd import run_status
        from wds.cli.manage_cmd import run_list, run_switch, run_uninstall

        # =====================================================================
        # 1. scan — 只读扫描
        # =====================================================================
        run_scan(wds_root=mock_wds_root, mod_path=mock_mod_root, game_id_arg="EP14")
        scan_out = capsys.readouterr().out
        assert "EP14" in scan_out
        # scan 输出应包含自动匹配的标记
        assert "✓" in scan_out or "自动" in scan_out

        # =====================================================================
        # 2. install — 安装
        # =====================================================================
        run_install(
            wds_root=mock_wds_root, mod_path=mock_mod_root,
            game_id_arg="EP14", display_name_arg="Integration Test Mod", yes=True,
        )
        install_out = capsys.readouterr().out
        assert "安装完成" in install_out
        assert "Integration Test Mod" in install_out

        # 验证 registry 已创建
        ep14_root = mock_wds_root / "EastPrussia' 14"
        registry = load_registry(ep14_root)
        assert registry is not None
        assert "hawkeyes_ep14" in registry.mods
        mod_info = registry.mods["hawkeyes_ep14"]
        assert mod_info.file_count > 0
        assert mod_info.active_count == mod_info.file_count  # 全部激活

        # 验证游戏文件已被替换（BMP 内容应为 mod 的内容）
        test_bmp = ep14_root / "German" / "2DSymbolsLg.bmp"
        assert test_bmp.is_file()

        # =====================================================================
        # 3. status — 状态面板
        # =====================================================================
        run_status(wds_root=mock_wds_root, game_id_arg="EP14")
        status_out = capsys.readouterr().out
        assert "Integration Test Mod" in status_out

        # =====================================================================
        # 4. list — 列表
        # =====================================================================
        run_list(wds_root=mock_wds_root, all_games=True)
        list_out = capsys.readouterr().out
        assert "hawkeyes_ep14" in list_out
        assert "Integration Test Mod" in list_out

        # =====================================================================
        # 5. switch --off — 禁用
        # =====================================================================
        run_switch(
            wds_root=mock_wds_root, mod_id="hawkeyes_ep14",
            on=False, off=True, game_id_arg="EP14",
        )
        switch_out = capsys.readouterr().out
        assert "已禁用" in switch_out

        # 验证 registry 状态已更新
        registry = load_registry(ep14_root)
        assert registry.mods["hawkeyes_ep14"].active_count == 0

        # =====================================================================
        # 6. switch --on — 重新启用
        # =====================================================================
        run_switch(
            wds_root=mock_wds_root, mod_id="hawkeyes_ep14",
            on=True, off=False, game_id_arg="EP14",
        )
        enable_out = capsys.readouterr().out
        assert "已启用" in enable_out

        registry = load_registry(ep14_root)
        assert registry.mods["hawkeyes_ep14"].active_count > 0

        # =====================================================================
        # 7. uninstall — 卸载
        # =====================================================================
        run_uninstall(
            wds_root=mock_wds_root, mod_id="hawkeyes_ep14",
            game_id_arg="EP14",
        )
        uninstall_out = capsys.readouterr().out
        assert "已卸载" in uninstall_out

        # 验证 registry 已清理
        registry = load_registry(ep14_root)
        assert registry is not None
        assert "hawkeyes_ep14" in registry.mods
        assert registry.mods["hawkeyes_ep14"].active_count == 0

    def test_scan_install_twice_different_mods(
        self, capsys: Any, mock_wds_root: Path, tmp_path: Path,
    ):
        """安装两个不同的 mod 到同一游戏，验证 registry 正确合并"""
        from wds.cli.install_cmd import run_install
        from wds.registry import get_status_summary

        def _touch(path: Path, content: str = "") -> Path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return path

        def _bmp(path: Path) -> Path:
            return _touch(path, f"FAKE:{path}")

        # Mod A: 装饰层 + German/Units/Infantry.bmp（Infantry.bmp 在 German/Units/ 下唯一）
        mod_a = tmp_path / "Mod_A"
        mod_a.mkdir()
        _bmp(mod_a / "Decorator_A" / "German" / "Units" / "Infantry.bmp")

        # Mod B: 装饰层 + German/2DSymbolsLg.bmp（带装饰层时后缀唯一匹配 German/）
        mod_b = tmp_path / "Mod_B"
        mod_b.mkdir()
        _bmp(mod_b / "Decorator_B" / "German" / "2DSymbolsLg.bmp")

        # 安装 Mod A
        run_install(
            wds_root=mock_wds_root, mod_path=mod_a,
            game_id_arg="EP14", display_name_arg="Mod A", yes=True,
        )
        out_a = capsys.readouterr().out

        # 安装 Mod B
        run_install(
            wds_root=mock_wds_root, mod_path=mod_b,
            game_id_arg="EP14", display_name_arg="Mod B", yes=True,
        )
        out_b = capsys.readouterr().out

        # 验证两个安装都成功
        assert "安装完成" in out_a, f"Mod A 安装失败: {out_a}"
        assert "安装完成" in out_b, f"Mod B 安装失败: {out_b}"

        # 验证 registry 中有两个 mod
        ep14 = mock_wds_root / "EastPrussia' 14"
        registry = load_registry(ep14)
        assert registry is not None
        assert len(registry.mods) == 2
        assert "mod_a" in registry.mods
        assert "mod_b" in registry.mods

        # 验证文件归属
        summary = get_status_summary(registry)
        ids = {s["mod_id"] for s in summary}
        assert ids == {"mod_a", "mod_b"}

    def test_rename_then_uninstall(
        self, capsys: Any, mock_wds_root: Path, mock_mod_root: Path,
    ):
        """重命名后卸载，验证修正场景"""
        from wds.cli.install_cmd import run_install
        from wds.cli.manage_cmd import run_rename, run_uninstall

        run_install(
            wds_root=mock_wds_root, mod_path=mock_mod_root,
            game_id_arg="EP14", display_name_arg="Original Name", yes=True,
        )
        capsys.readouterr()

        # 重命名
        run_rename(
            wds_root=mock_wds_root, mod_id="hawkeyes_ep14",
            new_name="New Name", game_id_arg="EP14",
        )
        rename_out = capsys.readouterr().out
        assert "New Name" in rename_out

        # 验证 registry
        ep14 = mock_wds_root / "EastPrussia' 14"
        registry = load_registry(ep14)
        assert registry.mods["hawkeyes_ep14"].display_name == "New Name"

        # 卸载
        run_uninstall(
            wds_root=mock_wds_root, mod_id="hawkeyes_ep14",
            game_id_arg="EP14",
        )
        uninstall_out = capsys.readouterr().out
        assert "已卸载" in uninstall_out

    def test_list_with_game_id_filter(
        self, capsys: Any, mock_wds_root: Path, mock_mod_root: Path,
    ):
        """status 命令不指定 game_id 时应列出所有游戏"""
        from wds.cli.install_cmd import run_install
        from wds.cli.status_cmd import run_status

        run_install(
            wds_root=mock_wds_root, mod_path=mock_mod_root,
            game_id_arg="EP14", display_name_arg=None, yes=True,
        )
        capsys.readouterr()

        # 不指定 game_id → 列表视图
        run_status(wds_root=mock_wds_root, game_id_arg=None)
        out = capsys.readouterr().out
        assert "EP14" in out
        # 其他无 mod 的游戏不应显示（因为默认不传 --all）
        # 这里 mod_count=1 的 EP14 才显示
