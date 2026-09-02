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
import unicodedata
from pathlib import Path

from server.lxseq.preset_mapper import (
    NAME_COLLISION_UNVERIFIED,
    NAME_TAKEN,
    POOL_TRUNCATED,
    POOL_UNREADABLE,
    SLOT_SHORTFALL,
    map_presets,
)
from server.lxseq.preset_parser import parse_preset_csv

RIG = Path("src/Lighting_Designer/02_RIG팩")
STEM = "LXSEQ_RIG_01_ShowBase_r3.preset-"


def _records(*kinds):
    """기본은 dim + bm — **저장 가능한 것은 한 종류**여야 한다.

    t134 이전에는 세 시트를 다 넣어도 저장 가능한 것이 dim 뿐이라 무해했다.
    col 이 열리면서 섞으면 한쪽이 남의 풀에 배정되므로 `map_presets` 가 거절한다.
    bm 을 남겨 두는 이유는 보류가 거절 경로에서도 살아남는지 재기 위해서다.
    """
    out = []
    for kind in kinds or ("dim", "bm"):
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
        """거절해도 보류는 버리지 않는다 — 버리면 어디로 갔는지 모른다.

        13 -> 5 는 두 이유가 겹친 것이다: t134 가 col RGB 6행을 열었고,
        픽스처가 col 을 빼서(섞으면 거절된다) 켈빈 2행도 이 호출에 없다.
        col 쪽 보류는 아래 `TestTheColSheetAllocatesToo` 가 따로 잰다.
        """
        for section in (_pool(truncated=True), _pool(capacity=3), _pool()):
            result = map_presets(_records(), pool_section=section)
            assert len(result.held) == 5
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


# --- SPEC-COPILOT-PRESETIDEM-001 (카드 t87) — 이름을 봐야 멱등이다 -------------
#
# 위 검사들은 **슬롯**만 본다. 아래는 **이름**을 본다. 매퍼가 점유 슬롯을 피하는
# 것은 슬롯 보증이지 동일성 보증이 아니어서, 이름을 안 보면 같은 시트를 두 번
# 돌릴 때 전부 복제된다. 콘솔 접촉 0 — 매퍼는 순수하고 풀 단면은 손으로 짓는다.

DIM_NAMES = ("풀", "쇼 하이", "미드", "로우", "잔광", "아웃")


def _named_pool(names=(), truncated=False, **extra):
    """이름이 실린 풀 단면. 슬롯은 1 부터 순서대로 준다.

    위 `_pool` 은 점유 항목에 이름을 안 싣는다 — 그래서 기존 검사들이 이 변경에
    영향받지 않는다. 이름을 재려면 이 헬퍼를 쓴다.
    """
    section = dict(
        objects=[dict(no=i, name=n) for i, n in enumerate(names, start=1)],
        truncated=truncated,
    )
    section.update(extra)
    return section


class TestRerunningTheSameSheetIsANoOp:
    """AC-IDEM-001 — 헤드라인. 같은 CSV 재실행은 무동작이다."""

    def test_all_six_names_present_plans_nothing(self):
        result = map_presets(_records(), pool_section=_named_pool(DIM_NAMES))
        assert result.planned == ()
        assert len(result.already_present) == 6
        assert result.refusal is None, "거절이 아니라 **수렴**이다"

    def test_the_hold_reason_is_name_taken(self):
        result = map_presets(_records(), pool_section=_named_pool(DIM_NAMES))
        assert all(h.hold_classes == (NAME_TAKEN,) for h in result.already_present)

    def test_parser_holds_are_untouched(self):
        """AC-IDEM-003 — 파서 판정은 콘솔 상태와 무관하게 그대로다.

        섞였다면 이 수가 콘솔 상태에 따라 달라지고, 회귀 기준이 날마다 흔들린다.
        재는 것은 **불변성**이지 특정 숫자가 아니다 — 13 -> 5 는 t134 가 col
        RGB 6행을 열고 픽스처가 col 을 뺀 결과이며, 세 콘솔 상태에서 같다는
        성질은 그대로다.
        """
        for section in (_named_pool(), _named_pool(DIM_NAMES), _named_pool(DIM_NAMES[:3])):
            assert len(map_presets(_records(), pool_section=section).held) == 5

    def test_an_empty_pool_is_the_control(self):
        """대조군 — 풀이 비면 6건이 계획된다.

        이게 없으면 위 0건이 「이름을 봤다」인지 「무조건 0건」인지 모른다.
        """
        result = map_presets(_records(), pool_section=_named_pool())
        assert len(result.planned) == 6
        assert result.already_present == ()


class TestOnlyTheMatchingRecordIsHeld:
    """AC-IDEM-002 — 비공허성. 이름 하나만 달라도 그 하나만 계획된다."""

    def test_one_changed_name_plans_exactly_that_record(self):
        altered = ("풀", "쇼 하이", "미드", "로우", "잔광", "아웃X")
        result = map_presets(_records(), pool_section=_named_pool(altered))
        assert [p.preset_id for p in result.planned] == ["DIM.OUT"]
        assert len(result.already_present) == 5

    def test_the_planned_slot_is_the_first_free_one(self):
        """6개가 점유돼 있으니 남은 1건은 7번으로 간다 — 배정은 여전히 콘솔 유래."""
        altered = ("풀", "쇼 하이", "미드", "로우", "잔광", "아웃X")
        result = map_presets(_records(), pool_section=_named_pool(altered))
        assert [p.slot for p in result.planned] == [7]


class TestTheComparisonIsExact:
    """AC-IDEM-003 — 관대한 비교를 쓰지 않는다.

    근거는 착수 게이트의 바이트 일치 실측이다(SPEC §A.4: 6/6 `byte_equal`,
    공백을 품은 `쇼 하이` 가 `0x20` 유지, 단음절 `풀` 이 NFC 조합형 유지).
    양쪽이 이미 트림된다는 것도 쟀다(§A.5) — 파서 `preset_parser.py:274` 와
    명령 빌더 `store.py:31`.

    그러므로 가장 엄격한 규칙이 성립하고, 관대한 비교는 **미측정 변환**이라
    사용자가 넣으려던 레코드를 조용히 떨어뜨린다. 아래 셋은 전부 **불일치**여야
    한다 — 즉 그 레코드는 계획되어야 한다.
    """

    @staticmethod
    def _first_planned_ids(first_name):
        section = _named_pool((first_name,) + DIM_NAMES[1:])
        return [p.preset_id for p in map_presets(_records(), pool_section=section).planned]

    def test_a_decomposed_name_is_not_a_match(self):
        """NFD 분해형 — 눈에 같아 보여도 바이트가 다르다."""
        assert self._first_planned_ids(unicodedata.normalize("NFD", "풀")) == ["DIM.FULL"]

    def test_an_inner_space_removed_name_is_not_a_match(self):
        section = _named_pool(("풀", "쇼하이") + DIM_NAMES[2:])
        planned = [p.preset_id for p in map_presets(_records(), pool_section=section).planned]
        assert planned == ["DIM.SHOW"]

    def test_a_padded_name_is_not_a_match_either(self):
        """콘솔이 패딩된 이름을 답하면 대조가 성립하지 않는다.

        우리 쪽은 파서가 트림하지만 **콘솔 답을 트림하지는 않는다** — 재지 않은
        변환을 넣지 않는다는 뜻이다. 이 검사가 그 선택을 못박는다.
        """
        assert self._first_planned_ids(" 풀 ") == ["DIM.FULL"]

    def test_the_exact_name_is_the_control(self):
        """양성 대조군 — 정확히 같으면 계획에서 빠진다.

        이게 없으면 위 셋이 「엄격해서 안 맞다」인지 「무조건 계획된다」인지 모른다.
        """
        assert self._first_planned_ids("풀") == []


class TestFilteringHappensBeforeAllocation:
    """AC-IDEM-004 — 배정 후에 걸렀다면 없는 부족분이 생긴다."""

    def test_no_false_shortfall_when_five_are_already_present(self):
        section = _named_pool(DIM_NAMES[:5], capacity=6)
        result = map_presets(_records(), pool_section=section)
        assert result.refusal is None, "1건만 필요한데 부족분이 나오면 배정 후에 거른 것이다"
        assert [p.preset_id for p in result.planned] == ["DIM.OUT"]
        assert [p.slot for p in result.planned] == [6]

    def test_a_real_shortfall_still_refuses(self):
        """대조군 — 진짜로 모자라면 여전히 0건이다. 이름 검사가 그 갈래를 못 지운다."""
        result = map_presets(_records(), pool_section=_named_pool(capacity=3))
        assert result.planned == ()
        assert result.refusal == SLOT_SHORTFALL
        assert result.shortfall.needed == 6


class TestTheThreeBasketsAccountForEveryRow:
    """AC-IDEM-005 — `refusal` 이 없으면 셋의 합이 읽은 수와 같다.

    거절 경로는 대상이 아니다: 그때는 저장 가능분이 어느 바구니에도 안 들어간다
    (변경 전에도 그랬다). 세 번째 바구니를 안 읽는 소비자가 생기면 이 합이 깨진다.
    """

    def test_every_readable_pool_state_conserves_the_row_count(self):
        records = _records()
        for section in (
            _named_pool(),
            _named_pool(DIM_NAMES),
            _named_pool(DIM_NAMES[:3]),
            _named_pool(("풀", "없는이름", "미드")),
            _named_pool(DIM_NAMES[:5], capacity=6),
        ):
            result = map_presets(records, pool_section=section)
            assert result.refusal is None
            total = len(result.planned) + len(result.held) + len(result.already_present)
            assert total == len(records), section


class TestAnUnreadableNameIsALimitNotARefusal:
    """AC-IDEM-006 — 이름을 못 읽어도 거절하지 않는다. 대신 한계를 말한다.

    번호와 무게가 다르다: 번호를 틀리면 점유 슬롯을 **덮어써** 복구가 불가능하고
    (`_occupied_slots` 가 그래서 fail-closed 다), 이름을 모르면 생기는 것은
    **중복**이다. 저장소가 이미 그 차이를 `refusal` 과 `unverified` 로 갈라 뒀다.
    """

    @staticmethod
    def _pool_with_a_nameless_slot():
        return dict(
            objects=[dict(no=1, name=""), dict(no=2, name="풀")],
            truncated=False,
        )

    def test_it_does_not_refuse(self):
        result = map_presets(_records(), pool_section=self._pool_with_a_nameless_slot())
        assert result.refusal is None

    def test_the_limit_is_stated_in_the_result(self):
        result = map_presets(_records(), pool_section=self._pool_with_a_nameless_slot())
        assert NAME_COLLISION_UNVERIFIED in result.unverified
        assert "이름을 못 읽은 것" in result.unverified_reason

    def test_the_readable_names_are_still_compared(self):
        """한 칸을 못 읽었다고 나머지 대조를 포기하지 않는다."""
        result = map_presets(_records(), pool_section=self._pool_with_a_nameless_slot())
        assert [h.preset_id for h in result.already_present] == ["DIM.FULL"]

    def test_a_fully_named_pool_carries_no_such_marker(self):
        """대조군 — 이름이 전부 있으면 마커가 없다.

        이게 없으면 위 마커가 「못 읽어서」인지 「항상 붙어서」인지 모른다.
        """
        result = map_presets(_records(), pool_section=_named_pool(DIM_NAMES))
        assert result.unverified == ("value_match",)

    def test_value_match_survives_alongside_it(self):
        """기존 한계를 밀어내지 않는다 — 더한다."""
        result = map_presets(_records(), pool_section=self._pool_with_a_nameless_slot())
        assert "value_match" in result.unverified
        assert "값이 맞는지는" in result.unverified_reason


class TestDuplicateNamesInsideOneSheet:
    """AC-IDEM-007 — 파서는 `duplicate_id` 만 막고 이름은 안 본다.

    안 막으면 이 가드가 **첫 실행에서** 중복을 만든다 — 빈 풀에 같은 이름 두 행을
    쏘면 서로 다른 슬롯에 같은 이름이 둘 생긴다.
    """

    @staticmethod
    def _two_rows_one_name():
        text = "ID,Name,Level,Purpose\nDIM.FULL,같은이름,100%,t\nDIM.MID,같은이름,60%,t\n"
        return parse_preset_csv(text).records

    def test_the_second_row_is_held_not_planned(self):
        records = self._two_rows_one_name()
        result = map_presets(records, pool_section=_named_pool())
        assert [p.preset_id for p in result.planned] == ["DIM.FULL"]
        assert [h.preset_id for h in result.already_present] == ["DIM.MID"]

    def test_distinct_names_are_the_control(self):
        text = "ID,Name,Level,Purpose\nDIM.FULL,이름하나,100%,t\nDIM.MID,이름둘,60%,t\n"
        result = map_presets(parse_preset_csv(text).records, pool_section=_named_pool())
        assert len(result.planned) == 2
        assert result.already_present == ()

    def test_the_parser_does_not_catch_this_itself(self):
        """이 검사가 왜 매퍼에 있는지를 못박는다 — 파서는 ID 만 본다.

        파서가 나중에 이름 중복을 잡게 되면 이 검사가 빨개지고, 그때 매퍼 쪽
        중복 방지가 남아도는지 다시 판단하면 된다.
        """
        records = self._two_rows_one_name()
        assert len(records) == 2, "파서는 같은 Name 두 행을 그대로 통과시킨다"
        assert all(r.storable for r in records)


class TestTheColSheetAllocatesToo:
    """t134 가 col RGB 6행을, t229 가 켈빈 2행을 열어 **8행 전부**가 배정된다.

    위 클래스들이 dim 으로 재는 것을 col 로 재는 미러다. 픽스처에서 col 을
    뺐으므로(섞으면 거절된다) col 쪽 자리는 여기가 잰다.
    """

    def test_every_row_takes_the_lowest_slots(self):
        result = map_presets(_records("col"), pool_section=_pool())
        assert [p.slot for p in result.planned] == [1, 2, 3, 4, 5, 6, 7, 8]
        assert [p.preset_id for p in result.planned] == [
            "COL.01",
            "COL.02",
            "COL.03",
            "COL.04",
            "COL.05",
            "COL.06",
            "COL.07",
            "COL.08",
        ]

    def test_the_assignment_follows_the_listing(self):
        """비공허성 — 목록을 바꾸면 배정도 따라 바뀌어야 한다."""
        result = map_presets(_records("col"), pool_section=_pool(occupied=(1, 2, 3)))
        assert [p.slot for p in result.planned] == [4, 5, 6, 7, 8, 9, 10, 11]

    def test_a_held_row_still_takes_no_slot(self):
        """정본 col 은 이제 보류가 0이다 — 그래서 **합성 행**으로 이 자리를 지킨다.

        보류가 없다고 이 검사를 지우면 「보류에도 슬롯을 준다」는 회귀를 아무도
        못 잡는다. 정의역 밖 색온도가 여전히 보류되는 자리다(t229).
        """
        records = _records("col")
        held_kind = [r for r in records if not r.storable]
        assert held_kind == [], "정본에 보류가 생겼다 — 이 검사의 전제를 다시 봐라"

        outside = parse_preset_csv("ID,Name,Value,Purpose\nCOL.99,정의역 밖,~40000K,합성\n").records
        result = map_presets(records + list(outside), pool_section=_pool())
        assert [h.preset_id for h in result.held] == ["COL.99"]
        assert [p.preset_id for p in result.planned][-1] == "COL.08"


class TestOneCallMapsOneSheet:
    """저장 가능한 레코드가 두 종류 섞이면 한쪽이 **남의 풀에** 배정된다.

    t134 이전에는 col·bm 이 전부 보류라 이 실수가 무해했다 — col 이 열리면서
    유해해졌다. 생산 경로는 시트 하나씩 넘기므로 지금 결함은 아니고, 이 검사는
    그 계약을 문서가 아니라 **동작으로** 고정한다.
    """

    def test_mixing_two_storable_kinds_raises(self):
        import pytest

        with pytest.raises(ValueError, match="more than one sheet kind"):
            map_presets(_records("dim", "col"), pool_section=_pool())

    def test_one_storable_kind_plus_held_others_is_fine(self):
        """대조군 — 보류만 섞이는 것은 막지 않는다. 안 막으면 위 예외가
        「무조건 예외」와 구분되지 않는다."""
        result = map_presets(_records("dim", "bm"), pool_section=_pool())
        assert len(result.planned) == 6
        assert result.refusal is None
