"""SPEC-COPILOT-LXSEQ-003 M2 — PRESET 매퍼.

AC-LXSEQ3-006  풀 번호는 콘솔이 답한 목록에서만 온다 (+ 비공허성)
AC-LXSEQ3-007  점유 슬롯에는 쓰지 않는다
AC-LXSEQ3-008  어긋나면 0건 + 대조표
AC-LXSEQ3-009  새 명령 문형을 만들지 않는다 (AST 검사로 읽음 — 아래 근거)
AC-LXSEQ3-014  확인 한계가 산출물에 적힌다

순수 함수 검증이다. 콘솔·네트워크 접촉 0.
"""

from __future__ import annotations

import ast
from pathlib import Path

from server.lxseq.preset_mapper import (
    POOL_TRUNCATED,
    POOL_UNREADABLE,
    SLOT_SHORTFALL,
    map_presets,
)
from server.lxseq.preset_parser import parse_preset_csv

RIG = Path("src/Lighting_Designer/02_RIG팩")
STEM = "LXSEQ_RIG_01_ShowBase_r3.preset-"


def _records():
    out = []
    for kind in ("dim", "col", "bm"):
        text = (RIG / (STEM + kind + ".csv")).read_text(encoding="utf-8-sig")
        out.extend(parse_preset_csv(text).records)
    return out


def _pool(occupied=(), truncated=False, **extra):
    section = dict(objects=[dict(no=n) for n in occupied], truncated=truncated)
    section.update(extra)
    return section


class TestSlotsComeFromTheConsole:
    def test_an_empty_pool_takes_the_lowest_slots(self):
        result = map_presets(_records(), pool_section=_pool())
        assert [p.slot for p in result.planned] == [1, 2, 3, 4, 5, 6]

    def test_the_assignment_follows_the_listing(self):
        """비공허성(필수) — 목록을 바꾸면 배정도 따라 바뀌어야 한다.

        번호가 그대로면 매퍼가 목록을 안 읽고 상수를 쓰는 것이다.
        """
        result = map_presets(_records(), pool_section=_pool(occupied=(1, 2, 3)))
        assert [p.slot for p in result.planned] == [4, 5, 6, 7, 8, 9]

    def test_a_scattered_listing_is_followed_too(self):
        """대조군 — 앞이 아니라 **중간**이 비어도 그 자리를 쓴다."""
        result = map_presets(_records(), pool_section=_pool(occupied=(1, 3, 5)))
        assert [p.slot for p in result.planned] == [2, 4, 6, 7, 8, 9]


class TestOccupiedSlotsAreNeverWritten:
    def test_the_two_sets_do_not_intersect(self):
        occupied = (2, 4, 6, 8)
        result = map_presets(_records(), pool_section=_pool(occupied=occupied))
        planned = set(p.slot for p in result.planned)
        assert planned & set(occupied) == set()
        assert len(planned) == 6, "6건은 여전히 계획되어야 한다"

    def test_an_unreadable_entry_refuses_everything(self):
        """항목 하나의 번호를 못 읽으면 **어느 슬롯도** 비었다고 말하지 않는다."""
        section = dict(objects=[dict(no=1), dict(name="번호 없음")], truncated=False)
        result = map_presets(_records(), pool_section=section)
        assert result.planned == ()
        assert result.refusal == POOL_UNREADABLE

    def test_a_truncated_listing_refuses_everything(self):
        result = map_presets(_records(), pool_section=_pool(truncated=True))
        assert result.planned == ()
        assert result.refusal == POOL_TRUNCATED


class TestMismatchYieldsZero:
    def test_not_enough_empty_slots_plans_nothing(self):
        """3건 부분 계획은 실패로 친다 — 반쯤 맞는 프리셋이 최악이다."""
        result = map_presets(_records(), pool_section=_pool(capacity=3))
        assert result.planned == ()
        assert result.refusal == SLOT_SHORTFALL

    def test_the_shortfall_table_states_all_three_numbers(self):
        result = map_presets(_records(), pool_section=_pool(capacity=3))
        assert result.shortfall is not None
        assert (result.shortfall.needed, result.shortfall.available, result.shortfall.missing) == (
            6,
            3,
            3,
        )

    def test_enough_slots_is_the_control(self):
        """대조군 — 가용이 충분하면 계획이 나온다. 이게 없으면 위 0건이
        「무조건 0건」과 구분되지 않는다."""
        result = map_presets(_records(), pool_section=_pool(capacity=6))
        assert len(result.planned) == 6
        assert result.refusal is None

    def test_held_records_survive_every_refusal(self):
        """거절해도 보류는 버리지 않는다 — 버리면 13건이 어디로 갔는지 모른다."""
        for section in (_pool(truncated=True), _pool(capacity=3), _pool()):
            result = map_presets(_records(), pool_section=section)
            assert len(result.held) == 13
            assert all(h.hold_classes for h in result.held)


class TestNoCommandSyntaxIsBuiltHere:
    """AC-LXSEQ3-009 를 **AST 검사로 읽는다.** 문면과 다르므로 근거를 적는다.

    AC 문면은 `grep -rn "Store Preset" server/lxseq/` 가 빈 출력일 것을 요구한다.
    그 명령은 AC-LXSEQ3-003 과 **같은 결함**을 갖는다 — 코드와 설명을 못 가른다.
    매퍼 독스트링이 「`Store Preset` 문형을 여기서 만들지 않는다」고 적으면 그
    문장 때문에 grep 이 비지 않고, 만족시키려면 그 설명을 지워야 한다.

    그래서 **소스를 파싱해 문자열 리터럴만 본다.** 독스트링은 제외하고, 코드가
    실제로 들고 있는 문자열에 명령 문형이 없는지 잰다. 설명은 살고 검사는 정확해진다.
    부재를 재는 grep 보다 강하다 — 문자열을 바꿔 우회할 수 없다.

    **airtight 은 아니다. 무엇이 남는지 알고 받아들인다.** 접두어를 통짜
    (`"Store Preset"`)가 아니라 **`"Store "` 로** 재기 때문에 조립해도 리터럴이
    남는다 — 실측:

        "Store " + kind        -> 리터럴 'Store ' 가 남는다        잡힘
        f"Store {pool}.{n}"    -> JoinedStr 조각 'Store ' 가 보인다  잡힘
        "Sto" + "re Preset 1"  -> 'Sto' · 're Preset 1'             **샌다**

    남는 우회는 **접두어 자체를 쪼개는 것** 하나이고, 그것은 사고가 아니라
    의도적 은폐다. 검사는 실수를 잡지 은폐를 잡지 않는다 — 통짜 문자열로
    쟀다면 위 셋 중 둘이 샜을 것이므로, 접두어로 재는 선택이 그 차이를 만든다.
    """

    MODULES = ("server/lxseq/preset_mapper.py", "server/lxseq/preset_parser.py")

    @staticmethod
    def _code_strings(path: str) -> list[str]:
        tree = ast.parse(Path(path).read_text(encoding="utf-8"))
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef):
                doc = ast.get_docstring(node, clean=False)
                if doc is not None:
                    docstrings.add(doc)
        return [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value not in docstrings
        ]

    def test_no_module_holds_a_store_command_literal(self):
        for path in self.MODULES:
            offending = [s for s in self._code_strings(path) if "Store " in s]
            assert offending == [], path + " 가 명령 문형을 들고 있다: " + repr(offending)

    def test_the_scanner_sees_code_strings_at_all(self):
        """양성 대조군 — 스캐너가 실제로 문자열을 걷는지 먼저 확인한다.

        이게 없으면 위 빈 목록이 「없다」인지 「아무것도 안 봤다」인지 모른다.
        """
        found = self._code_strings("server/lxseq/preset_mapper.py")
        assert len(found) > 10
        assert POOL_TRUNCATED in found, "닫힌 사유 상수는 코드 문자열이라 보여야 한다"

    def test_the_scanner_would_catch_a_planted_literal(self):
        """날조 대조군 — 심으면 잡히는지."""
        source = "x = 'Store Preset 1.1'\n"
        tree = ast.parse(source)
        planted = [
            n.value
            for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
        ]
        assert any("Store " in s for s in planted)

    def test_an_assembled_command_is_still_caught(self):
        """조립 우회 — 접두어를 통짜가 아니라 `"Store "` 로 재는 이유.

        이 검사가 없으면 다음 사람이 「전체 문자열로 재는 게 정확하지」 하고
        바꾸고, 그 순간 연결·f-string 조립이 전부 샌다.
        """
        for source in ('x = "Store " + kind', 'x = f"Store {pool}.{n}"'):
            strings = [
                n.value
                for n in ast.walk(ast.parse(source))
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
            ]
            assert any("Store " in s for s in strings), source

    def test_the_known_escape_is_recorded_not_claimed_closed(self):
        """남는 우회를 **검사로 못박는다** — 「막았다」고 적지 않기 위해서다.

        접두어 자체를 쪼개면 샌다. 그것은 실수가 아니라 은폐이고, 이 검사는
        실수를 잡는 도구다. 이 사실이 검사에 없으면 다음 사람이 airtight 로
        읽는다.
        """
        source = 'x = "Sto" + "re Preset 1"'
        strings = [
            n.value
            for n in ast.walk(ast.parse(source))
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
        ]
        assert not any("Store " in s for s in strings), "이 우회는 실제로 샌다"

    def test_docstrings_are_excluded_on_purpose(self):
        """이 검사가 왜 grep 보다 나은지를 검사로 못박는다.

        매퍼 독스트링에는 `Store Preset` 이 실제로 들어 있다 — 왜 여기서 만들지
        않는지를 설명하기 때문이다. grep 은 그것을 위반으로 읽고, AST 검사는
        읽지 않는다.
        """
        raw = Path("server/lxseq/preset_mapper.py").read_text(encoding="utf-8")
        assert "Store Preset" in raw, "설명이 살아 있어야 한다"
        assert all("Store " not in s for s in self._code_strings("server/lxseq/preset_mapper.py"))


class TestConfirmationLimitIsStated:
    def test_the_result_says_value_match_is_unverified(self):
        result = map_presets(_records(), pool_section=_pool())
        assert "value_match" in result.unverified
        assert "값이 맞는지는" in result.unverified_reason

    def test_the_placement_table_maps_rig_id_to_slot(self):
        """다음 단계(큐)가 `DIM.FULL` 같은 RIG ID 로 슬롯을 찾는다."""
        result = map_presets(_records(), pool_section=_pool())
        table = dict((p.preset_id, p.slot) for p in result.planned)
        assert table["DIM.FULL"] == 1
        assert len(table) == 6
