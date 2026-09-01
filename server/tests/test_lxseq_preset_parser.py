"""SPEC-COPILOT-LXSEQ-003 M1 — PRESET 파서.

AC-LXSEQ3-002  세 시트가 정확 열 집합으로 읽힌다 (+ 비공허성)
AC-LXSEQ3-003  preset-pos 는 어느 서명에도 맞지 않는다 (동작 검사로 읽음 — 아래 근거)
AC-LXSEQ3-004  ID 접두 불일치 행은 거부되고 보고된다
AC-LXSEQ3-005  산문 열도 그룹 이름도 해석되지 않는다

그리고 이 SPEC 의 AC 가 재지 않는 것을 하나 더 잰다 — **저장 가능성**.
AC-002 는 「19 레코드가 나온다」를 요구하는데 그것은 파싱이라 통과한다. 값이
콘솔에 넣을 수 있는 것인지는 어느 AC 도 묻지 않아서, 문면대로 구현하면
「19건 성공」이 적히고 13건은 저장 단계에서 터진다. 아래 TestStorability 가
그 자리를 관측 가능하게 만든다.

순수 함수 검증이다. 콘솔·네트워크 접촉 0.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from server.lxseq.preset_parser import (
    HOLD_FAMILY_OUT_OF_SCOPE,
    HOLD_NO_RGB_VALUE,
    HOLD_PROBE_REJECTED,
    HOLD_VALUE_NOT_MACHINE_READABLE,
    PRESET_SHEET_COLUMNS,
    UnknownPresetSheetError,
    classify_storability,
    parse_preset_csv,
    resolve_sheet_kind,
)

RIG = Path("src/Lighting_Designer/02_RIG팩")
STEM = "LXSEQ_RIG_01_ShowBase_r3.preset-"

EXPECTED_ROWS = dict([("preset-dim", 6), ("preset-col", 8), ("preset-bm", 5)])


def _text(kind: str) -> str:
    return (RIG / (STEM + kind.removeprefix("preset-") + ".csv")).read_text(encoding="utf-8-sig")


def _parsed(kind: str):
    return parse_preset_csv(_text(kind))


def _held():
    return [r for k in EXPECTED_ROWS for r in _parsed(k).records if not r.storable]


class TestExactColumnSets:
    def test_three_sheets_parse_to_nineteen_records(self):
        counts = dict((k, len(_parsed(k).records)) for k in EXPECTED_ROWS)
        assert counts == EXPECTED_ROWS
        assert sum(counts.values()) == 19

    def test_each_sheet_resolves_to_its_own_kind(self):
        for kind in EXPECTED_ROWS:
            assert _parsed(kind).sheet_kind == kind

    @pytest.mark.parametrize("kind", sorted(EXPECTED_ROWS))
    def test_a_single_renamed_column_is_refused(self, kind: str):
        """비공허성(필수) — 열 하나만 바꿔도 거부되어야 한다.

        통과하면 파서가 열 집합을 재고 있지 않다는 뜻이고, 그러면 위 검사는
        「무엇이든 읽는 파서가 무엇이든 읽었다」와 구분되지 않는다.
        """
        header = list(PRESET_SHEET_COLUMNS[kind])
        header[2] = header[2][:-1] + "X"
        with pytest.raises(UnknownPresetSheetError):
            resolve_sheet_kind(tuple(header))

    def test_the_three_signatures_do_not_collide(self):
        """대조군 — 정확 집합이라 쌍마다 갈린다. 포함 검사였다면 col 과 bm 이 겹친다."""
        resolved = [resolve_sheet_kind(PRESET_SHEET_COLUMNS[k]) for k in sorted(EXPECTED_ROWS)]
        assert resolved == sorted(EXPECTED_ROWS)
        assert len(set(resolved)) == 3


class TestPosIsRefused:
    """AC-LXSEQ3-003 을 **동작 검사로 읽는다.** 문면과 다르므로 근거를 적는다.

    AC 문면은 `grep -rn "preset-pos" server/lxseq/ server/sheets/` 가 빈 출력일
    것을 요구한다. 그 명령은 두 가지를 못 한다.

    1. **분기와 설명을 못 가른다.** 파서 독스트링이 「왜 pos 를 안 읽는지」를
       적으면 그 문장 때문에 grep 이 비지 않는다. 문면대로 만족시키려면 그
       설명을 지워야 하는데, 그러면 다음 사람이 왜 없는지 모르고 채워 넣는다.
       주석·독스트링을 걸러내는 정제 grep 도 안 통한다 — `grep -v` 는 패턴이
       **있는 줄**만 빼므로 독스트링 본문 줄은 그대로 걸린다.
    2. **빌드 산물을 센다.** `__pycache__/*.pyc` 가 매치되어, 테스트를 한 번
       돌린 뒤에는 소스 내용과 무관하게 실패한다.

    그래서 **부재 대신 거절을 잰다.** grep 은 부재를 재고 동작 검사는 거절을
    재는데, 부재는 문자열을 바꾸면 우회되지만 거절은 안 된다. 문면 정정은 카드
    t77 이며 이 SPEC 본문은 이 레인이 고치지 않는다.
    """

    def test_the_pos_header_is_refused(self):
        with pytest.raises(UnknownPresetSheetError):
            parse_preset_csv(_text("preset-pos"))

    def test_the_refusal_names_the_header_it_saw(self):
        """거절만으로는 부족하다 — 무엇을 보고 거절했는지 말해야 고칠 수 있다."""
        with pytest.raises(UnknownPresetSheetError) as caught:
            parse_preset_csv(_text("preset-pos"))
        assert "StageMeaning" in str(caught.value)

    def test_it_does_not_refuse_everything(self):
        """비공허성 — 위 거절이 「무엇이든 거절한다」와 구분되어야 한다.

        같은 판별기가 정본 세 종류는 받는다. 이 대조군이 없으면 거절 검사는
        파서가 죽어 있어도 통과한다.
        """
        for kind in EXPECTED_ROWS:
            assert resolve_sheet_kind(PRESET_SHEET_COLUMNS[kind]) == kind


class TestRowRejection:
    def test_a_mismatched_id_prefix_is_rejected_and_reported(self):
        """조용히 건너뛰지 않는다 — 행 번호와 사유가 함께 나온다."""
        text = _text("preset-col").replace("COL.04", "BM.99", 1)
        result = parse_preset_csv(text)
        assert len(result.records) == 7, "한 행만 떨어져야 한다"
        assert len(result.rejected) == 1
        bad = result.rejected[0]
        assert bad.kind == "id_prefix_mismatch"
        assert bad.preset_id_raw == "BM.99"
        assert bad.row > 1, "행 번호가 보고되어야 한다"
        assert "COL." in bad.detail

    def test_the_untouched_sheet_has_no_rejections(self):
        """대조군 — 정본은 거부가 0이다. 이게 없으면 위 1건이 「원래 나던 것」과
        구분되지 않는다."""
        for kind in EXPECTED_ROWS:
            assert _parsed(kind).rejected == ()


class TestProseIsNotInterpreted:
    def test_purpose_is_preserved_but_never_becomes_the_value(self):
        """`Purpose` 에 값처럼 읽히는 문구가 있어도 값 산출에 안 쓴다."""
        dim = _parsed("preset-dim")
        full = next(r for r in dim.records if r.preset_id == "DIM.FULL")
        assert full.purpose is not None and full.purpose != ""
        assert full.value_raw == "100%"
        assert full.purpose not in full.value_raw

    def test_target_group_stays_a_string(self):
        """FID 목록으로 확장하지 않는다 — 그룹 멤버십은 읽히지 않아 근거가 없다."""
        bm = _parsed("preset-bm")
        first = bm.records[0]
        assert first.target_group == "MOVER-ALL"
        assert isinstance(first.target_group, str)

    def test_sheets_without_that_column_carry_none(self):
        """대조군 — bm 에만 TargetGroup 이 있고 dim/col 에는 없다."""
        assert all(r.target_group is None for r in _parsed("preset-dim").records)
        assert all(r.purpose is None for r in _parsed("preset-bm").records)


class TestStorability:
    """이 SPEC 의 AC 가 재지 않는 자리 — **넣을 수 있는가**.

    사유는 전부 이 저장소가 **이미 실기로 재서** 적어 둔 것이다
    (`server/looks/schema.py`: M0 프로브가 Zoom·Iris 만 받았고 Gobo 계열은 범위
    밖). 다만 M0 가 거절한 넷은 **사유가 하나가 아니다** — `Focus`·`Frost` 는 철자가
    틀렸던 것이고(콘솔 채널명은 `Focus1`·`Frost1`, t135 가 실기로 둘 다 통과시켰다),
    `Prism` 은 이 리그에 채널 자체가 없으며, `Shutter` 는 danger 정책 배제라 프로브
    결과와 무관하다. **부재가 아니라 판정**이므로 다시 검색해서 닫힌 질문을 열지
    마라 — 다만 「콘솔이 못 받는다」로도 읽지 마라.

    정본 `server/looks/schema.py:16-18` 은 아직 옛 사유를 하나로 말한다. PRESERVE
    게이트 둘이 그 파일을 바이트 단위로 잠그고 있어 t142 가 못 고쳤고, 정정은
    t149(예외 심사) 뒤로 간다.
    """

    def test_dim_and_the_rgb_half_of_col_are_storable(self):
        """col 6행이 열렸다 — t134 가 0-255 대 0-100 대응을 실기로 쟀다.

        **8행이 아니라 6행이다.** 켈빈 2행은 사유가 다르고(`no_rgb_value`)
        소유자가 다르다(t133). bm 5행은 그대로 전부 보류다.
        """
        by_kind = dict((k, _parsed(k).records) for k in EXPECTED_ROWS)
        storable = dict((k, sum(1 for r in v if r.storable)) for k, v in by_kind.items())
        assert storable == dict([("preset-dim", 6), ("preset-col", 8), ("preset-bm", 0)])
        assert sum(storable.values()) == 14

    def test_every_held_record_carries_at_least_one_reason(self):
        """보류를 버리지 않는다 — 사유 없이 보류하면 다음 사람이 못 푼다.

        13 -> 7 은 t134 가 col RGB 6행을 열었기 때문이고, 7 -> 5 는 t229 가 켈빈
        2행(COL.02·COL.03)을 열었기 때문이다. **막던 사유가 사라진 것이지 보류가
        조용히 버려진 것이 아니다** — 아래 클래스별 개수가 그것을 말한다.
        """
        held = _held()
        assert len(held) == 5
        assert all(record.hold_reasons for record in held)
        assert all(reason.detail.strip() for record in held for reason in record.hold_reasons)

    def test_reasons_carry_a_machine_countable_class(self):
        """산문만 두면 13건이 한 덩어리로 보인다.

        클래스가 있어야 **어느 하나를 풀면 몇 건이 열리는지** 읽힌다.
        """
        counts = Counter(c for record in _held() for c in record.hold_classes)
        assert counts == Counter(
            dict(
                [
                    ("attribute_probe_rejected", 3),
                    ("family_out_of_scope", 3),
                ]
            )
        )

    def test_the_class_sum_exceeds_the_row_count_by_the_multi_blocked_rows(self):
        """t153 표기 규약의 근거 — 클래스 합과 행 수는 **다른 것을 센다.**

        문서가 「3 · 3」과 「5행」을 나란히 적으면 안 맞는 것처럼 보이지만 산수
        오류가 아니다. 한 행이 사유 둘을 지면 클래스 합이 행 수보다 크고, **그
        차이가 곧 다중 차단 행의 수**다. 위 두 검사는 각각 행 수(7)와 클래스
        합(3+3+2=8)을 따로 단언할 뿐 **그 둘의 관계**는 아무 데서도 안 잰다 —
        그래서 「개수를 맞추는」 정리가 참인 값을 거짓으로 바꿔도 안 걸린다.
        """
        held = _held()
        total_classes = sum(len(record.hold_classes) for record in held)
        multi = [record.preset_id for record in held if len(record.hold_classes) > 1]
        assert total_classes > len(held), (
            "클래스 합이 행 수를 넘지 않는다 — 그러면 문서가 두 값을 구분해 적을 "
            "이유가 사라지고, 이 표기 규약 자체가 근거를 잃는다: "
            + str(total_classes)
            + " vs "
            + str(len(held))
        )
        # 판별력을 지는 것은 아래 단언이다. 위 부등호는 방향만 고정한다 —
        # 「합 − 행 == 다중 행 수」 형태로 적었다가 뺐다: bm 에서 도달 가능한
        # 클래스가 둘뿐이라 어느 행도 셋을 못 져서 이 코퍼스에서는 **항등식**이고,
        # 항등식은 아무것도 안 지킨다.
        assert multi == ["BM.01"], (
            "다중 차단 행이 바뀌었다 — 문서의 「합 N > 행 M」 표기도 같이 고쳐야 한다 "
            "(.moai/specs/SPEC-COPILOT-LXSEQ-003/preset-unify-design.md §5 표기 규약, "
            "spec.md §A.4-2 합계 행): " + str(multi)
        )

    def test_every_class_is_from_the_closed_set(self):
        """비공허성 — 클래스가 열려 있으면 위 개수는 오타를 세고 있을 수 있다."""
        known = frozenset(
            [
                HOLD_NO_RGB_VALUE,
                HOLD_PROBE_REJECTED,
                HOLD_FAMILY_OUT_OF_SCOPE,
                HOLD_VALUE_NOT_MACHINE_READABLE,
            ]
        )
        seen = set(c for record in _held() for c in record.hold_classes)
        assert seen <= known
        assert len(seen) == 2, "정본에서 실제로 나오는 클래스는 둘이다 (t229 전에는 셋)"

        # 🔴 `no_rgb_value` 가 정본에서 사라진 것은 **켈빈 2행이 열렸기 때문**이지
        # 그 클래스가 죽은 것이 아니다. 숫자만 3 -> 2 로 낮추면 그 클래스가 조용히
        # 고아가 되고, 다음 사람이 「안 쓰는 클래스」로 읽고 지운다. 도달 가능한지
        # 여기서 직접 쏴서 고정한다 — 정의역 밖 색온도가 그 자리다.
        outside_domain, holds = classify_storability("preset-col", "~40000K")
        assert not outside_domain
        assert [h.hold_class for h in holds] == [HOLD_NO_RGB_VALUE]

    def test_a_row_blocked_twice_carries_both_reasons(self):
        """한 사유만 실으면 하나를 풀었을 때 그 행이 열릴 것처럼 보인다.

        `BM.01`(Zoom · Gobo OPEN · Prism OFF)은 Gobo(범위 밖)와 Prism(거절)
        **둘 다**에 막힌다. Gobo 만 풀어도 안 열린다 — 목록이 그것을 말해야 한다.
        """
        first = next(r for r in _parsed("preset-bm").records if r.preset_id == "BM.01")
        assert set(first.hold_classes) == set([HOLD_PROBE_REJECTED, HOLD_FAMILY_OUT_OF_SCOPE])

    def test_solving_one_class_would_not_open_every_beam_row(self):
        """위 검사의 실질 — 「Gobo 만 풀면 몇 건」이 정직하게 나오는지."""
        beam = _parsed("preset-bm").records
        only_gobo = [r for r in beam if set(r.hold_classes) == set([HOLD_FAMILY_OUT_OF_SCOPE])]
        assert len(only_gobo) == 2, "Gobo 만 풀면 5건 중 2건만 열린다"

    def test_a_fabricated_prose_level_is_not_storable(self):
        """날조 대조군 — dim 이 무조건 통과하는 게 아니라 형태를 재는 것이다."""
        text = _text("preset-dim").replace("100%", "아주 밝게", 1)
        record = parse_preset_csv(text).records[0]
        assert record.storable is False
        assert record.hold_classes == (HOLD_VALUE_NOT_MACHINE_READABLE,)

    def test_a_fabricated_percent_beam_would_be_storable(self):
        """반대편 — bm 이 무조건 보류인 게 아니라 요구 속성으로 판정하는 것이다.

        Zoom 은 M0 프로브가 **받은** 속성이므로 Zoom 만 요구하는 행은 통과해야
        한다. 이 대조군이 없으면 위 5/5 보류가 「bm 은 전부 막는다」와 구분되지
        않는다.
        """
        text = _text("preset-bm").replace("Zoom 45° · Gobo OPEN · Prism OFF", "Zoom 45", 1)
        record = parse_preset_csv(text).records[0]
        assert record.storable is True, record.hold_reasons
