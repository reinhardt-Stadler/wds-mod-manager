"""Day 10: CLI 冒烟测试 — 对真实 D:\\WDS 的只读验证

执行方式: pytest -m smoke --wds-root D:\\WDS tests/test_smoke_cli.py
"""

from __future__ import annotations

from pathlib import Path

import pytest

from wds.scanner import discover_games


@pytest.fixture
def real_wds_root(pytestconfig) -> Path:
    """获取真实的 WDS 根目录，不存在则跳过"""
    root = Path(pytestconfig.getoption("--wds-root", default="D:\\WDS"))
    if not root.is_dir():
        pytest.skip(f"WDS 根目录不存在: {root}")
    return root


@pytest.mark.smoke
class TestSmokeScan:
    """scan 命令冒烟测试（只读）"""

    def test_scan_mod_in_wds_tree(self, real_wds_root: Path):
        """在 WDS 目录树中找到第一个 mod 目录并扫描"""
        from wds.cli.scan_cmd import run_scan

        # 遍历 WDS 目录找第一个 mod-like 目录含 BMP 的
        mod_candidates = [
            d for d in real_wds_root.iterdir()
            if d.is_dir() and list(d.rglob("*.bmp"))[:1]
        ]
        if not mod_candidates:
            pytest.skip("未找到含 BMP 的子目录")

        mod_path = mod_candidates[0]
        # 捕获输出而不是检查具体内容（只验证不抛异常即可）
        try:
            run_scan(wds_root=real_wds_root, mod_path=mod_path, game_id_arg=None)
        except Exception as e:
            pytest.fail(f"scan 命令异常: {e}")

    def test_scan_specific_game(self, real_wds_root: Path):
        """指定 game_id 扫描"""
        from wds.cli.scan_cmd import run_scan
        games = discover_games(real_wds_root)
        if not games:
            pytest.skip("未发现任何 WDS 游戏")

        # 尝试用第一个游戏的根目录作为 mod 路径（可能不是真 mod 但应优雅处理）
        game = games[0]
        try:
            run_scan(wds_root=real_wds_root, mod_path=game.root_path, game_id_arg=game.game_id)
        except Exception as e:
            pytest.fail(f"scan 命令异常: {e}")


@pytest.mark.smoke
class TestSmokeStatus:
    """status 命令冒烟测试（只读）"""

    def test_status_all_games(self, real_wds_root: Path):
        from wds.cli.status_cmd import run_status
        try:
            run_status(wds_root=real_wds_root, game_id_arg=None)
        except Exception as e:
            pytest.fail(f"status 命令异常: {e}")

    def test_status_first_game(self, real_wds_root: Path):
        from wds.cli.status_cmd import run_status
        games = discover_games(real_wds_root)
        if not games:
            pytest.skip("未发现任何 WDS 游戏")
        try:
            run_status(wds_root=real_wds_root, game_id_arg=games[0].game_id)
        except Exception as e:
            pytest.fail(f"status 命令异常: {e}")


@pytest.mark.smoke
class TestSmokeList:
    """list-mods 命令冒烟测试（只读）"""

    def test_list_all(self, real_wds_root: Path):
        from wds.cli.manage_cmd import run_list
        try:
            run_list(wds_root=real_wds_root, all_games=True)
        except Exception as e:
            pytest.fail(f"list 命令异常: {e}")
