"""CUE-EX 매퍼 검사 (4단계 큐).

이 검사가 지키는 것은 **빈칸의 뜻**이다. 이 도메인에서 가장 비싼 결함은 예외가
아니라 조용한 오독이다: 트래킹이 0으로 접히면 무대에서 조명이 꺼지고, 그것은
쇼가 도는 도중에 드러난다.

## 파서 레코드 대역(stand-in)을 쓰는 이유

`server/lxseq/cue_parser.py` 는 같은 회차에 **다른 레인**이 짓는다. 그것이 없는
동안 이 검사가 못 돌면, 매퍼의 결함이 남의 진행에 가려진다. 그래서 리드가 못
박은 계약대로 대역을 여기 두고 매퍼를 잰다.

🔴 **대역은 계약이 맞다는 증거가 아니다.** 그래서 `test_record_contract_matches_parser`
가 파서가 생기는 순간 필드를 대조한다 — 없는 동안에는 사유를 적고 건너뛴다.
「없어서 안 쟀다」가 「통과했다」로 읽히면 안 된다.
"""

from __future__ import annotations

import csv
import importlib.util
from dataclasses import dataclass, fields
from pathlib import Path

import pytest

from server.lxseq.cue_mapper import (
    BAD_NUMBER,
    BAD_SNAP,
    CUE_COVERAGE_GAP,
    CUE_EMPTIED_BY_HOLD,
    DIM_OUT_OF_RANGE,
    SLOT_SHORTFALL,
    UNKNOWN_GROUP,
    UNRESOLVED_PRESET,
    map_cues,
)
from server.rig.section import SECTION_TRUNCATED, SECTION_UNREAD

CANONICAL_CSV = Path("src/Lighting_Designer/03_곡파일_Sugar/LXSEQ_SAMPLE_01_Sugar_r3.cue-ex.csv")


@dataclass(frozen=True)
class StandInCueRecord:
    """리드가 못 박은 `LxseqCueRecord` 계약의 대역. 원문만 보존한다."""

    cue_no: str
    group: str
    dim_raw: str = ""
    col_raw: str = ""
    pos_raw: str = ""
    bm_raw: str = ""
    fx_raw: str = ""
    fx_rate_raw: str = ""
    fx_phase_raw: str = ""
    fx_width_raw: str = ""
    i_fade_raw: str = ""
    i_delay_raw: str = ""
    p_fade_raw: str = ""
    c_fade_raw: str = ""
    b_fade_raw: str = ""
    snap_raw: str = ""
    note: str = ""
    is_video_call: bool = False


def _readable_section(objects=()) -> dict:
    """콘솔이 답한 정상 단면. 빈 목록은 **정당한 빈 풀**이다."""
    return dict(objects=list(objects), truncated=False)


def _slots(*names: str) -> dict[str, int]:
    return dict((name, index) for index, name in enumerate(names, start=1))


_GROUPS = _slots(
    "BACK",
    "WASH-U",
    "WASH-D",
    "KEY",
    "SIDE-L",
    "SIDE-R",
    "MOVER-U",
    "MOVER-D",
    "HAZE",
    "STROBE",
    "BLIND",
    "ALL",
    "LED-W",
)
_PRESETS = _slots(
    "COL.01",
    "COL.02",
    "COL.03",
    "COL.04",
    "COL.05",
    "COL.06",
    "COL.07",
    "COL.08",
    "POS.01",
    "POS.02",
    "POS.03",
    "POS.04",
    "POS.05",
    "POS.06",
    "BM.01",
    "BM.02",
    "BM.03",
    "BM.04",
    "BM.05",
    "FX.01",
    "FX.02",
    "FX.03",
    "FX.04",
    "FX.05",
    "FX.06",
    "FX.07",
    "FX.08",
)


def _map(records, *, declared=None, section=None, name="Sugar", **kwargs):
    """기본 인자를 채워 `map_cues` 를 부른다 — 검사마다 다른 축만 적게."""
    return map_cues(
        records,
        declared_cues=declared if declared is not None else sorted({r.cue_no for r in records}),
        sequence_name=name,
        sequence_section=section if section is not None else _readable_section(),
        group_slots=_GROUPS,
        preset_slots=_PRESETS,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# 빈칸의 뜻 — 이 층의 존재 이유
# ---------------------------------------------------------------------------


def test_blank_dim_is_tracking_not_zero():
    """🔴 빈 Dim 은 None 이다. 0 이 되면 앞 큐의 레벨이 꺼진다(§11.2 #1)."""
    result = _map([StandInCueRecord(cue_no="Q010", group="BACK", dim_raw="")])
    row = result.planned[0].rows[0]
    assert row.dim is None
    assert row.dim != 0.0  # 비공허성 — None 과 0.0 이 같은 값이면 위 단언이 공허하다


def test_blank_fades_are_tracking_not_zero():
    """페이드 열도 같다 — 빈칸을 0초로 접으면 스냅이 된다."""
    row = _map([StandInCueRecord(cue_no="Q010", group="BACK", dim_raw="55")]).planned[0].rows[0]
    assert row.i_fade is None
    assert row.c_fade is None
    assert row.p_fade is None


def test_zero_dim_is_kept_as_zero():
    """대조군 — 0 이라고 **적힌** 것은 0으로 간다. 위 검사가 전부 None 을 내는
    구현으로도 통과하면 안 된다."""
    row = (
        _map([StandInCueRecord(cue_no="Q010", group="BACK", dim_raw="0", i_fade_raw="3.5")])
        .planned[0]
        .rows[0]
    )
    assert row.dim == 0.0


def test_blackout_needs_both_zero_and_fade():
    """소등은 Dim 0 **과** I-Fade 가 함께 있을 때만이다(§11.2 #2)."""
    with_fade = (
        _map([StandInCueRecord(cue_no="Q010", group="BACK", dim_raw="0", i_fade_raw="3.5")])
        .planned[0]
        .rows[0]
    )
    silent = _map([StandInCueRecord(cue_no="Q010", group="BACK", dim_raw="0")]).planned[0].rows[0]
    assert with_fade.is_blackout is True
    assert silent.is_blackout is False


# ---------------------------------------------------------------------------
# 영상 콜 — 콘솔에 안 보내고, 버리지도 않는다
# ---------------------------------------------------------------------------


def test_video_call_row_never_becomes_a_console_row():
    """🔴 과거 유출 사고가 있던 자리. 계획에 그 그룹이 한 번도 안 나와야 한다."""
    records = [
        StandInCueRecord(cue_no="Q080", group="BACK", dim_raw="55"),
        StandInCueRecord(
            cue_no="Q080",
            group="LED-W",
            dim_raw="60",
            i_fade_raw="8.0",
            note="영상 큐 LW-02 콜",
            is_video_call=True,
        ),
    ]
    result = _map(records)
    planned_groups = [row.group for bucket in result.planned for row in bucket.rows]
    assert "LED-W" not in planned_groups
    assert len(result.video_calls) == 1
    assert result.video_calls[0].note == "영상 큐 LW-02 콜"


def test_video_call_is_not_reported_as_a_hold():
    """보류는 「고치면 들어갈 것」이다. 영상 콜은 **설계상 안 들어갈 것**이라
    섞으면 「보류 N건」이 고칠 거리로 읽힌다."""
    result = _map(
        [
            StandInCueRecord(cue_no="Q080", group="BACK", dim_raw="55"),
            StandInCueRecord(cue_no="Q080", group="LED-W", is_video_call=True),
        ]
    )
    assert result.held == ()


def test_cue_with_only_video_calls_is_a_state_not_a_refusal():
    """영상 콜만 있는 큐는 「조명이 할 일이 없다」이지 부분 계획이 아니다."""
    result = _map(
        [
            StandInCueRecord(cue_no="Q010", group="BACK", dim_raw="55"),
            StandInCueRecord(cue_no="Q020", group="LED-W", is_video_call=True),
        ],
        declared=["Q010", "Q020"],
    )
    assert result.refusal is None
    assert result.video_only_cues == ("Q020",)
    assert [bucket.cue_no for bucket in result.planned] == ["Q010"]


# ---------------------------------------------------------------------------
# FX — OFF 는 정지 명령이고 빈칸은 언급 없음이다 (§11.1 7행)
# ---------------------------------------------------------------------------


def test_off_is_a_stop_command_not_absence():
    off = _map([StandInCueRecord(cue_no="Q010", group="BACK", fx_raw="OFF")]).planned[0].rows[0]
    blank = _map([StandInCueRecord(cue_no="Q010", group="BACK", fx_raw="")]).planned[0].rows[0]
    assert off.fx_stop is True
    assert off.fx is None
    assert blank.fx_stop is False
    assert blank.fx is None
    # 두 상태가 실제로 갈리는지 — 한 필드만 보면 둘이 같아 보인다
    assert (off.fx_stop, off.fx) != (blank.fx_stop, blank.fx)


def test_off_is_case_insensitive_and_stripped():
    row = _map([StandInCueRecord(cue_no="Q010", group="BACK", fx_raw=" off ")]).planned[0].rows[0]
    assert row.fx_stop is True


def test_fx_reference_resolves_to_a_slot():
    row = _map([StandInCueRecord(cue_no="Q010", group="BACK", fx_raw="FX.01")]).planned[0].rows[0]
    assert row.fx_stop is False
    assert row.fx is not None
    assert row.fx.kind == "FX"
    assert row.fx.slot == _PRESETS["FX.01"]


# ---------------------------------------------------------------------------
# 프리셋 참조 — 한 체계, 그리고 못 찾으면 행 전체를 보류한다
# ---------------------------------------------------------------------------


def test_all_four_preset_types_use_one_resolver():
    row = (
        _map(
            [
                StandInCueRecord(
                    cue_no="Q010",
                    group="BACK",
                    col_raw="COL.01",
                    pos_raw="POS.03",
                    bm_raw="BM.02",
                    fx_raw="FX.05",
                )
            ]
        )
        .planned[0]
        .rows[0]
    )
    assert (row.col.kind, row.pos.kind, row.bm.kind, row.fx.kind) == ("COL", "POS", "BM", "FX")
    assert row.col.slot == _PRESETS["COL.01"]
    assert row.pos.slot == _PRESETS["POS.03"]


def test_undefined_preset_holds_the_whole_row():
    """🔴 성한 열만 골라 보내지 않는다. Dim 만 나가면 앞 큐의 색이 남은 채
    밝기만 바뀌고, 무대에서는 그것이 「고장」이 아니라 「다른 룩」으로 보인다."""
    result = _map(
        [
            StandInCueRecord(cue_no="Q010", group="BACK", dim_raw="55", col_raw="COL.99"),
            StandInCueRecord(cue_no="Q010", group="KEY", dim_raw="40"),
        ]
    )
    assert len(result.held) == 1
    assert UNRESOLVED_PRESET in result.held[0].hold_classes
    planned_groups = [row.group for bucket in result.planned for row in bucket.rows]
    assert planned_groups == ["KEY"]  # 보류된 행의 Dim 은 어디에도 안 실린다


def test_malformed_preset_reference_is_held():
    result = _map([StandInCueRecord(cue_no="Q010", group="BACK", col_raw="COL.1")])
    assert UNRESOLVED_PRESET in result.held[0].hold_classes


# ---------------------------------------------------------------------------
# 행 단위 판정 — 그룹·수치·Snap
# ---------------------------------------------------------------------------


def test_unknown_group_is_held_not_guessed():
    result = _map([StandInCueRecord(cue_no="Q010", group="NOPE", dim_raw="55")])
    assert UNKNOWN_GROUP in result.held[0].hold_classes
    assert result.planned == ()


def test_non_numeric_column_is_held():
    result = _map([StandInCueRecord(cue_no="Q010", group="BACK", dim_raw="밝게")])
    assert BAD_NUMBER in result.held[0].hold_classes


def test_dim_out_of_range_is_held():
    result = _map([StandInCueRecord(cue_no="Q010", group="BACK", dim_raw="120")])
    assert DIM_OUT_OF_RANGE in result.held[0].hold_classes


def test_snap_vocabulary_is_closed():
    yes = _map([StandInCueRecord(cue_no="Q010", group="BACK", snap_raw="Y")]).planned[0].rows[0]
    blank = _map([StandInCueRecord(cue_no="Q010", group="BACK", snap_raw="")]).planned[0].rows[0]
    bad = _map([StandInCueRecord(cue_no="Q010", group="BACK", snap_raw="N")])
    assert yes.snap is True
    assert blank.snap is False
    assert BAD_SNAP in bad.held[0].hold_classes


# ---------------------------------------------------------------------------
# 부분 계획 금지 — 어긋나면 0건
# ---------------------------------------------------------------------------


def test_missing_cue_refuses_everything():
    """부분집합 금지(§11.1 1행). 빠진 큐는 트래킹으로 지나가는데, 거기서 무엇이
    살아 있어야 하는지 시트가 말한 적이 없다."""
    result = _map(
        [StandInCueRecord(cue_no="Q010", group="BACK", dim_raw="55")],
        declared=["Q010", "Q020"],
    )
    assert result.refusal == CUE_COVERAGE_GAP
    assert result.planned == ()
    assert result.coverage_gap.missing == ("Q020",)
    assert result.coverage_gap.covered == ("Q010",)


def test_cue_emptied_by_hold_refuses_everything():
    """보류로 비어 버린 큐는 부분 계획이다 — 영상 콜만 있는 큐와 갈린다."""
    result = _map(
        [
            StandInCueRecord(cue_no="Q010", group="BACK", dim_raw="55"),
            StandInCueRecord(cue_no="Q020", group="NOPE", dim_raw="55"),
        ],
        declared=["Q010", "Q020"],
    )
    assert result.refusal == CUE_EMPTIED_BY_HOLD
    assert result.planned == ()
    assert "Q020" in result.refusal_detail


def test_holds_survive_a_refusal():
    """사용자가 시트를 고칠 근거는 거절 여부와 무관하다(형제와 같은 규약)."""
    result = _map(
        [StandInCueRecord(cue_no="Q010", group="NOPE", dim_raw="55")],
        declared=["Q010", "Q020"],
    )
    assert result.refusal == CUE_COVERAGE_GAP
    assert len(result.held) == 1  # 거절 경로에서도 실린다


# ---------------------------------------------------------------------------
# 시퀀스 슬롯 — 배정은 하나뿐이고, 큐 번호는 시트가 정한다
# ---------------------------------------------------------------------------


def test_cue_numbers_come_from_the_sheet_not_from_assignment():
    """🔴 큐 번호를 새로 매기지 않는다 — CUE 시트·현장 큐시트가 부르는 번호다."""
    result = _map(
        [
            StandInCueRecord(cue_no="Q010", group="BACK", dim_raw="55"),
            StandInCueRecord(cue_no="Q180", group="BACK", dim_raw="0", i_fade_raw="5"),
        ],
        declared=["Q010", "Q180"],
    )
    assert [bucket.cue_no for bucket in result.planned] == ["Q010", "Q180"]


def test_sequence_slot_is_the_lowest_free_one():
    section = _readable_section([dict(no=1, name="다른 곡"), dict(no=2, name="또 다른 곡")])
    result = _map([StandInCueRecord(cue_no="Q010", group="BACK", dim_raw="55")], section=section)
    assert result.placement.slot == 3
    assert result.placement.name == "Sugar"


def test_unreadable_section_refuses_and_carries_the_shared_code():
    """술어는 저장소에 하나뿐이고 코드를 자기 어휘로 번역하지 않는다."""
    result = _map(
        [StandInCueRecord(cue_no="Q010", group="BACK", dim_raw="55")],
        section=dict(ok=False, reason="연결 없음"),
    )
    assert result.refusal == SECTION_UNREAD
    assert result.planned == ()
    assert result.placement is None


def test_truncated_section_refuses():
    result = _map(
        [StandInCueRecord(cue_no="Q010", group="BACK", dim_raw="55")],
        section=dict(objects=[dict(no=1, name="x")], truncated=True),
    )
    assert result.refusal == SECTION_TRUNCATED
    assert result.planned == ()


def test_empty_observed_pool_is_a_legitimate_first_import():
    """「빈 관측」과 「관측 없음」은 다르다 — 통과시키지 않으면 첫 임포트가 막힌다."""
    result = _map([StandInCueRecord(cue_no="Q010", group="BACK", dim_raw="55")])
    assert result.refusal is None
    assert result.placement.slot == 1


def test_slot_shortfall_refuses_instead_of_overwriting():
    section = _readable_section([dict(no=1, name="다른 곡")])
    result = _map(
        [StandInCueRecord(cue_no="Q010", group="BACK", dim_raw="55")],
        section=section,
        slot_capacity=1,
    )
    assert result.refusal == SLOT_SHORTFALL
    assert result.planned == ()


# ---------------------------------------------------------------------------
# 멱등성 — 같은 시트를 두 번 돌려도 복제되지 않는다
# ---------------------------------------------------------------------------


def test_existing_name_is_convergence_not_refusal():
    """시퀀스 층 수렴이지 계획 자체를 막지 않는다(t209 리드 재현, 2026-08-31:
    시퀀스가 이미 있다고 18큐 전체가 안 나갔다) -- existing_cue_numbers 를
    안 주면(이 시퀀스 안에 뭐가 있는지 안 잰 것과 같다) 큐 층 판단을 못
    하니 planned 를 낸다. 큐 층 자체 판정은 아래 별도 검사가 확인한다."""
    section = _readable_section([dict(no=4, name="Sugar")])
    result = _map([StandInCueRecord(cue_no="Q010", group="BACK", dim_raw="55")], section=section)
    assert result.refusal is None  # 거절이 아니다 -- 목표 상태가 이미 달성돼 있다
    assert len(result.planned) == 1
    assert result.planned[0].cue_no == "Q010"
    assert result.placement is None
    assert result.already_present.slot == 4
    assert result.cues_already_present == ()


def test_a_cue_number_already_in_the_sequence_is_skipped_not_replanned():
    """큐 층 -- 시퀀스가 이미 있고 그 안에 Q010(cueNo=10)이 이미 있으면 그
    큐만 뺀다. 나머지 선언 큐는 그대로 계획한다(형제 preset_mapper 의 레코드
    단위 NAME_TAKEN 과 같은 무게, 컨테이너가 아니라 항목 단위)."""
    section = _readable_section([dict(no=4, name="Sugar")])
    result = _map(
        [
            StandInCueRecord(cue_no="Q010", group="BACK", dim_raw="55"),
            StandInCueRecord(cue_no="Q020", group="BACK", dim_raw="60"),
        ],
        declared=("Q010", "Q020"),
        section=section,
        existing_cue_numbers=(10,),
    )
    assert result.refusal is None
    assert result.cues_already_present == ("Q010",)
    assert [b.cue_no for b in result.planned] == ["Q020"]
    assert result.already_present.slot == 4
    assert result.placement is None


def test_a_new_sequence_ignores_existing_cue_numbers():
    """새 시퀀스에는 큐가 있을 수 없다 -- existing_cue_numbers 를 실수로
    넘겨도(예: 다른 호출의 값을 재사용) 무시한다."""
    section = _readable_section([])
    result = _map(
        [StandInCueRecord(cue_no="Q010", group="BACK", dim_raw="55")],
        section=section,
        existing_cue_numbers=(10,),
    )
    assert result.refusal is None
    assert result.cues_already_present == ()
    assert len(result.planned) == 1
    assert result.placement is not None
    assert result.already_present is None


def test_unreadable_name_is_declared_not_refused():
    """이름을 못 읽으면 생기는 것은 중복이지 덮어쓰기가 아니다 — 무게가 달라
    거절 대신 한계를 싣는다."""
    section = _readable_section([dict(no=1, name=""), dict(no=2, name="다른 곡")])
    result = _map([StandInCueRecord(cue_no="Q010", group="BACK", dim_raw="55")], section=section)
    assert result.refusal is None
    assert "name_collision" in result.unverified


# ---------------------------------------------------------------------------
# 회계 — 세 바구니의 합
# ---------------------------------------------------------------------------


def test_three_baskets_sum_to_the_rows_read():
    """거절이 없을 때 planned 행 + held + video_calls 가 읽은 행 수와 같다.
    합이 깨지면 어딘가에서 행이 조용히 사라진 것이다."""
    records = [
        StandInCueRecord(cue_no="Q010", group="BACK", dim_raw="55"),
        StandInCueRecord(cue_no="Q010", group="NOPE", dim_raw="55"),
        StandInCueRecord(cue_no="Q010", group="LED-W", is_video_call=True),
    ]
    result = _map(records)
    planned_rows = sum(len(bucket.rows) for bucket in result.planned)
    assert planned_rows + len(result.held) + len(result.video_calls) == len(records)


# ---------------------------------------------------------------------------
# 정본 CSV — 손으로 지은 입력이 아니라 실제 곡 파일로 잰다
# ---------------------------------------------------------------------------


def _records_from_canonical() -> tuple[list[StandInCueRecord], list[str]]:
    """정본 CSV 를 대역 레코드로 읽는다.

    ⚠️ 이것은 **파서가 아니다.** 영상 콜 판정을 여기서 `LED-W` 로 두는데, 실제
    판정은 파서 몫이다(리드 계약: `is_video_call` 은 레코드에 실려 온다).
    여기서 하는 것은 매퍼에 먹일 입력을 만드는 것뿐이다.
    """
    rows: list[StandInCueRecord] = []
    order: list[str] = []
    with CANONICAL_CSV.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            cue = row["Q#"]
            if cue not in order:
                order.append(cue)
            rows.append(
                StandInCueRecord(
                    cue_no=cue,
                    group=row["Group"],
                    dim_raw=row["Dim"],
                    col_raw=row["COL"],
                    pos_raw=row["POS"],
                    bm_raw=row["BM"],
                    fx_raw=row["FX"],
                    fx_rate_raw=row["FX-Rate"],
                    fx_phase_raw=row["FX-Phase"],
                    fx_width_raw=row["FX-Width"],
                    i_fade_raw=row["I-Fade"],
                    i_delay_raw=row["I-Delay"],
                    p_fade_raw=row["P-Fade"],
                    c_fade_raw=row["C-Fade"],
                    b_fade_raw=row["B-Fade"],
                    snap_raw=row["Snap"],
                    note=row["Note"],
                    is_video_call=row["Group"] == "LED-W",
                )
            )
    return rows, order


def test_canonical_csv_shape_is_what_this_suite_assumes():
    """입력이 변하면 아래 검사들의 뜻이 조용히 바뀐다 — 먼저 못 박는다."""
    records, order = _records_from_canonical()
    assert len(order) == 18
    assert len(records) == 89
    assert sum(1 for r in records if r.is_video_call) == 6


def test_canonical_csv_plans_every_cue():
    records, order = _records_from_canonical()
    result = _map(records, declared=order)
    assert result.refusal is None
    assert result.held == ()
    assert len(result.planned) == 18
    assert len(result.video_calls) == 6
    # 영상 콜을 빼도 어느 큐도 비지 않는다 — 그래서 video_only_cues 가 비어 있다
    assert result.video_only_cues == ()
    planned_rows = sum(len(bucket.rows) for bucket in result.planned)
    assert planned_rows + len(result.video_calls) == len(records)


def test_canonical_csv_keeps_blanks_as_tracking():
    """정본에서 빈 Dim 이 실제로 있고, 그것이 0 이 되지 않는지 잰다."""
    records, order = _records_from_canonical()
    result = _map(records, declared=order)
    rows = [row for bucket in result.planned for row in bucket.rows]
    tracking = [row for row in rows if row.dim is None]
    assert tracking, "정본에 빈 Dim 행이 없다면 이 검사는 공허하다"
    assert 0.0 not in [row.dim for row in tracking]


def test_canonical_csv_carries_both_fx_states():
    records, order = _records_from_canonical()
    rows = [row for bucket in _map(records, declared=order).planned for row in bucket.rows]
    assert sum(1 for row in rows if row.fx_stop) == 17
    assert sum(1 for row in rows if row.fx is not None) > 0


# ---------------------------------------------------------------------------
# 계약 — 파서가 생기는 순간 대역과 대조한다
# ---------------------------------------------------------------------------


def test_record_contract_matches_parser():
    """🔴 대역은 계약이 맞다는 증거가 아니다. 파서가 생기면 여기서 갈린다.

    없는 동안 건너뛰되 **사유를 적는다** — 「없어서 안 쟀다」가 「통과했다」로
    읽히면 안 된다.
    """
    if importlib.util.find_spec("server.lxseq.cue_parser") is None:
        pytest.skip(
            "server/lxseq/cue_parser.py 가 아직 없다 (같은 회차의 run 레인이 짓는다). "
            "이 검사는 파일이 생기는 순간 대역과 실제 레코드의 필드를 대조한다 — "
            "그때까지 매퍼의 필드 계약은 **미검증**이다"
        )
    from server.lxseq.cue_parser import LxseqCueRecord  # noqa: PLC0415

    stand_in = {field.name for field in fields(StandInCueRecord)}
    real = {field.name for field in fields(LxseqCueRecord)}
    missing = sorted(stand_in - real)
    assert stand_in <= real, "매퍼가 읽는 필드가 파서 레코드에 없다: " + str(missing)


# ---------------------------------------------------------------------------
# FX-Phase — 한 수와 확산 구간 (§11.1 9행)
#
# 이 갈래는 손으로 지은 입력이 아니라 **정본에서 나왔다**: 처음 구현은 이 열을
# 단순 수로 읽었고, 정본 89행 중 29행이 확산 구간이라 전부 보류돼 큐 전체가
# 거절됐다. 문면을 좁게 읽은 쪽이 틀렸다.
# ---------------------------------------------------------------------------


def test_single_phase_value_is_not_a_spread():
    row = _map([StandInCueRecord(cue_no="Q010", group="BACK", fx_phase_raw="0")]).planned[0].rows[0]
    assert row.fx_phase.start == 0.0
    assert row.fx_phase.end is None
    assert row.fx_phase.is_spread is False


def test_spread_keeps_both_ends():
    """🔴 확산을 단일 수로 접으면 그룹이 일제히 깜빡인다 — 파도가 아니라."""
    row = (
        _map([StandInCueRecord(cue_no="Q010", group="BACK", fx_phase_raw="0..360")])
        .planned[0]
        .rows[0]
    )
    assert (row.fx_phase.start, row.fx_phase.end) == (0.0, 360.0)
    assert row.fx_phase.is_spread is True


def test_spread_may_start_off_zero():
    """정본은 `180..540` 도 쓴다(10행). 명세서 예시만 받으면 그 10행이 거절된다."""
    row = (
        _map([StandInCueRecord(cue_no="Q010", group="BACK", fx_phase_raw="180..540")])
        .planned[0]
        .rows[0]
    )
    assert (row.fx_phase.start, row.fx_phase.end) == (180.0, 540.0)


def test_blank_phase_is_tracking():
    row = _map([StandInCueRecord(cue_no="Q010", group="BACK")]).planned[0].rows[0]
    assert row.fx_phase is None


def test_backwards_spread_is_held():
    result = _map([StandInCueRecord(cue_no="Q010", group="BACK", fx_phase_raw="360..0")])
    assert BAD_NUMBER in result.held[0].hold_classes


def test_canonical_csv_carries_both_phase_shapes():
    records, order = _records_from_canonical()
    rows = [row for bucket in _map(records, declared=order).planned for row in bucket.rows]
    spreads = [row.fx_phase for row in rows if row.fx_phase is not None and row.fx_phase.is_spread]
    singles = [
        row.fx_phase for row in rows if row.fx_phase is not None and not row.fx_phase.is_spread
    ]
    assert len(spreads) == 29
    assert len(singles) == 1
