"""M10a 测试: 交互式路径识别 (review.py)

覆盖 build_review_groups 的分组/置信度聚合逻辑，
以及 run_interactive_review 的接受/修改/跳过/退出/展开交互。
"""

from __future__ import annotations

from typing import Any

import pytest


# ---------------------------------------------------------------------------
# 辅助: 脚本化输入
# ---------------------------------------------------------------------------

def scripted_input(responses: list[str]):
    """构造一个按顺序返回预设响应的 input_fn"""
    it = iter(responses)

    def _input(prompt: str = "") -> str:
        return next(it)

    return _input


# ===========================================================================
# build_review_groups
# ===========================================================================


class TestBuildReviewGroups:
    def test_groups_by_source_dir(self):
        from wds.cli.review import build_review_groups

        results = [
            ("German/Flag.bmp", "German/Flag.bmp", "auto"),
            ("German/Unitbox.bmp", "German/Unitbox.bmp", "auto"),
            ("Map/2DFeatures50.bmp", "Map/2DFeatures50.bmp", "auto"),
        ]
        groups = build_review_groups(results)
        folders = {g.mod_subfolder for g in groups}
        assert folders == {"German", "Map"}
        german = next(g for g in groups if g.mod_subfolder == "German")
        assert len(german.files) == 2

    def test_root_level_files_group_empty_string(self):
        from wds.cli.review import build_review_groups

        results = [("Splash.bmp", "Splash.bmp", "auto")]
        groups = build_review_groups(results)
        assert len(groups) == 1
        assert groups[0].mod_subfolder == ""
        assert groups[0].files[0].mod_rel == "Splash.bmp"

    def test_proposed_target_majority(self):
        from wds.cli.review import build_review_groups

        # East-German 组内: 2 个文件 → French, 1 个文件 → Luftwaffe
        results = [
            ("East-German/2DSymbolsLg.bmp", "French/2DSymbolsLg.bmp", "auto"),
            ("East-German/Flag.bmp", "French/Flag.bmp", "auto"),
            ("East-German/UnitBox.bmp", "Luftwaffe/UnitBox.bmp", "auto"),
        ]
        groups = build_review_groups(results)
        assert len(groups) == 1
        # 多数派 French 胜出
        assert groups[0].proposed_target == "French"

    def test_confidence_all_auto(self):
        from wds.cli.review import build_review_groups

        results = [
            ("German/Flag.bmp", "German/Flag.bmp", "auto"),
            ("German/Unitbox.bmp", "German/Unitbox.bmp", "auto"),
        ]
        groups = build_review_groups(results)
        assert groups[0].confidence == "auto"

    def test_confidence_all_unmatched(self):
        from wds.cli.review import build_review_groups

        results = [
            ("Czechoslovakia/Flag.bmp", None, "unmatched"),
            ("Czechoslovakia/Unitbox.bmp", None, "unmatched"),
        ]
        groups = build_review_groups(results)
        assert groups[0].confidence == "unmatched"
        assert groups[0].proposed_target is None

    def test_confidence_mixed_is_ambiguous(self):
        from wds.cli.review import build_review_groups

        results = [
            ("German/Flag.bmp", "German/Flag.bmp", "auto"),
            ("German/Weird.bmp", "German/Weird.bmp", "ambiguous"),
        ]
        groups = build_review_groups(results)
        assert groups[0].confidence == "ambiguous"

    def test_empty_input(self):
        from wds.cli.review import build_review_groups

        assert build_review_groups([]) == []


# ===========================================================================
# run_interactive_review
# ===========================================================================


class TestRunInteractiveReview:
    def _make_groups(self):
        from wds.cli.review import build_review_groups

        results = [
            ("German/Flag.bmp", "German/Flag.bmp", "auto"),
            ("German/Unitbox.bmp", "German/Unitbox.bmp", "auto"),
            ("Map/2DFeatures50.bmp", "Map/2DFeatures50.bmp", "auto"),
        ]
        return build_review_groups(results)

    def test_accept_all(self, capsys: Any):
        from wds.cli.review import run_interactive_review

        groups = self._make_groups()
        # 两个组各按一次 Enter 接受
        mappings = run_interactive_review(groups, input_fn=scripted_input(["", ""]))
        assert mappings is not None
        assert len(mappings) == 2
        targets = {m.mod_subfolder: m.game_target for m in mappings}
        assert targets == {"German": "German", "Map": "Map"}
        for m in mappings:
            assert m.confidence == "user_confirmed"
            assert m.resolved_by == "manual"

    def test_edit_target(self, capsys: Any):
        from wds.cli.review import build_review_groups, run_interactive_review

        groups = build_review_groups([
            ("Czechoslovakia/Flag.bmp", "French/Flag.bmp", "auto"),
        ])
        # e → 输入新目标
        mappings = run_interactive_review(
            groups, input_fn=scripted_input(["e", "Czechoslovakia"]),
        )
        assert mappings is not None
        assert len(mappings) == 1
        assert mappings[0].game_target == "Czechoslovakia"

    def test_edit_normalizes_backslash_and_slash(self, capsys: Any):
        from wds.cli.review import build_review_groups, run_interactive_review

        groups = build_review_groups([("German/Flag.bmp", "German/Flag.bmp", "auto")])
        mappings = run_interactive_review(
            groups, input_fn=scripted_input(["e", "\\German\\Sub\\"]),
        )
        assert mappings is not None
        assert mappings[0].game_target == "German/Sub"

    def test_skip_group(self, capsys: Any):
        from wds.cli.review import run_interactive_review

        groups = self._make_groups()
        # 第一组跳过, 第二组接受
        mappings = run_interactive_review(groups, input_fn=scripted_input(["s", ""]))
        assert mappings is not None
        assert len(mappings) == 1
        assert mappings[0].mod_subfolder == "Map"

    def test_abort_returns_none(self, capsys: Any):
        from wds.cli.review import run_interactive_review

        groups = self._make_groups()
        mappings = run_interactive_review(groups, input_fn=scripted_input(["q"]))
        assert mappings is None

    def test_unmatched_requires_edit_or_skip(self, capsys: Any):
        from wds.cli.review import build_review_groups, run_interactive_review

        groups = build_review_groups([
            ("Czechoslovakia/Flag.bmp", None, "unmatched"),
        ])
        # 先按 Enter (无效, 无建议目标) → 再 e → 输入目标
        mappings = run_interactive_review(
            groups, input_fn=scripted_input(["", "e", "Czechoslovakia"]),
        )
        assert mappings is not None
        assert len(mappings) == 1
        assert mappings[0].game_target == "Czechoslovakia"
        out = capsys.readouterr().out
        assert "无建议目标" in out or "指定目标" in out

    def test_unmatched_skip(self, capsys: Any):
        from wds.cli.review import build_review_groups, run_interactive_review

        groups = build_review_groups([
            ("Czechoslovakia/Flag.bmp", None, "unmatched"),
        ])
        mappings = run_interactive_review(groups, input_fn=scripted_input(["s"]))
        assert mappings == []

    def test_view_files_then_accept(self, capsys: Any):
        from wds.cli.review import run_interactive_review

        groups = self._make_groups()
        # v 查看第一组文件 → Enter 接受 → Enter 接受第二组
        mappings = run_interactive_review(
            groups, input_fn=scripted_input(["v", "", ""]),
        )
        assert mappings is not None
        assert len(mappings) == 2
        out = capsys.readouterr().out
        # 展开视图应显示组内文件
        assert "German/Flag.bmp" in out

    def test_empty_edit_rejected(self, capsys: Any):
        from wds.cli.review import build_review_groups, run_interactive_review

        groups = build_review_groups([("German/Flag.bmp", "German/Flag.bmp", "auto")])
        # e → 空路径 (无效) → e → 有效路径
        mappings = run_interactive_review(
            groups, input_fn=scripted_input(["e", "", "e", "German"]),
        )
        assert mappings is not None
        assert mappings[0].game_target == "German"

    def test_empty_groups_returns_empty_list(self, capsys: Any):
        from wds.cli.review import run_interactive_review

        assert run_interactive_review([], input_fn=scripted_input([])) == []
