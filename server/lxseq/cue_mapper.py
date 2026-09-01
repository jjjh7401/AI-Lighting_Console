"""LX-SEQ v2.1 CUE-EX 매퍼 (4단계 큐).

순수 함수다 — 콘솔·네트워크 입출력 0, 명령 문자열 조립 0. 형제
`preset_mapper` · `group_mapper` 와 같은 층이고 같은 규율을 따른다: 번역은 툴
층이 하고, 여기서는 **무엇을 놓을지**만 정한다.

## 대상이 형제와 다르다 — 배정할 것은 시퀀스 슬롯 **하나**뿐이다

- 프리셋: 풀 슬롯 하나 = 프리셋 하나. N 건이면 N 슬롯을 배정한다.
- 큐: **시퀀스 하나 + 그 아래 큐 여러 개.** Q# 는 시트가 이미 정했다
  (Q010·Q020…). 그러므로 **큐 번호를 새로 배정하지 않는다** — 배정하는 것은
  이 시퀀스가 앉을 슬롯 하나다.

큐 번호를 여기서 다시 매기면 CUE 시트·연출 레이어·현장 큐시트가 부르는 번호와
갈린다. 그 갈라짐은 쇼가 도는 도중에 드러난다.

## 해석의 무게중심은 빈칸이다

명세서 §11.2 #1 이 「변경 파라미터만 기입한다, 빈칸 = 트래킹」이라고 못 박았다.
파서(`cue_parser`, 같은 회차의 다른 레인)가 원문을 보존한 채 넘기고, 이 층이
해석한다.

## 이 층이 지키는 다섯

1. **빈칸은 트래킹이지 0이 아니다.** 빈 Dim 은 None 으로 간다. 0 으로 접으면
   앞 큐에서 살아 있어야 할 레벨이 꺼진다. 소등은 Dim 0 과 I-Fade 가 **함께
   적혔을 때만**이다(§11.2 #2).
2. **영상 콜 행은 콘솔 명령을 만들지 않는다.** 버리지도 않는다 — 별도 바구니로
   나른다.
3. **OFF 는 페이저 정지 명령**이다(§11.1 7행). 「이펙트 안 씀」(빈칸)과 다르다.
4. **부분 계획을 내지 않는다** (AC-LXSEQ4-007 [HARD]). 단면을 못 읽었거나
   슬롯이 모자라거나 **한 행이라도 보류되면** 0건이다. 성한 행만 골라 보내면
   그룹 하나 빠진 큐가 콘솔에 올라가는데, MA3 는 트래킹하므로 그 큐는 큐
   리스트에서 정상으로 보이고 **발사할 때에야** 어긋난다.
5. **이미 있으면 수렴한다** (AC-LXSEQ4-008 [HARD]). 시퀀스 층과 큐 층을 갈라,
   같은 시트를 두 번 돌려도 시퀀스가 복제되지 않고 이미 있는 큐는 다시
   계획하지 않는다.

## 왜 파서 타입을 실행 시각에 임포트하지 않는가

`cue_parser` 는 같은 회차에 **다른 레인**이 짓는다. 실행 시각 임포트를 두면 이
모듈이 그 파일 없이는 임포트조차 안 되고, 그러면 이 층의 검사가 남의 진행에
묶인다. 타입만 필요하므로 TYPE_CHECKING 뒤에 둔다 — 이 층은 레코드의 속성만
읽지 생성하지 않는다.

**그 대신 계약을 검사로 고정한다**: `server/tests/test_lxseq_cue_mapper.py` 의
계약 검사가, `cue_parser` 가 생기는 순간 이 모듈이 읽는 필드 이름과 실제
레코드의 필드를 대조한다. 없는 동안에는 사유를 적고 건너뛴다 — 「없어서 안
쟀다」가 「통과했다」로 읽히지 않게.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from server.rig.section import section_refusal

if TYPE_CHECKING:  # pragma: no cover - 타입 전용 (위 독스트링 참조)
    from server.lxseq.cue_parser import LxseqCueRecord

__all__ = [
    "BAD_NUMBER",
    "BAD_SNAP",
    "CUE_COVERAGE_GAP",
    "DIM_OUT_OF_RANGE",
    "FX_STOP",
    "NAME_TAKEN",
    "PRESET_REF_PATTERN",
    "BLOCK_CONSOLE_STATE",
    "BLOCK_DOC_INTENT",
    "BLOCK_OUR_DEFECT",
    "ROWS_HELD",
    "SLOT_SHORTFALL",
    "UNKNOWN_GROUP",
    "UNRESOLVED_PRESET",
    "UNRESOLVED_CONSOLE_LACKS_NAME",
    "UNRESOLVED_POOL_UNREADABLE",
    "UNRESOLVED_SHEET_LACKS_ID",
    "UNRESOLVED_SHEET_NOT_SUPPLIED",
    "CueBucket",
    "CueCoverageGap",
    "CueHold",
    "CueMapResult",
    "CueRowPlan",
    "PhaseSpread",
    "PresetRef",
    "SequencePlacement",
    "VideoCall",
    "block_report",
    "map_cues",
    "resolve_preset_ref",
]

#: 시트가 선언한 큐 중 한 행도 없는 것이 있다 — 부분집합 금지(§11.1 1행).
CUE_COVERAGE_GAP = "cue_coverage_gap"

#: 빈 시퀀스 슬롯이 없다 — 부분 계획을 내지 않는다.
SLOT_SHORTFALL = "slot_shortfall"

#: 한 행이라도 계획에 못 들어갔다 — 배치 전체가 0건이다(AC-LXSEQ4-007 [HARD]).
#:
#: 선행 상수 ``cue_emptied_by_hold`` 를 **대체한다.** 그쪽은 「보류 때문에 어떤
#: 큐의 콘솔 행이 0이 된 경우」만 거절했고, 큐에 성한 행이 하나라도 남으면
#: 그 큐를 **불완전한 채로** 내보냈다. MA3 는 트래킹하므로 그렇게 나간 큐는
#: 큐 리스트에서 정상으로 보이고 **발사할 때에야** 어긋난다 — 관객 앞에서다.
#: 되읽기 채널은 큐 내용을 안 주므로(AC-LXSEQ4-013) 사후 탐지 수단도 없다.
#: 반면 큐가 통째로 빠지면 적재 시점에 보이고, 이 파이프라인은 preview 단계와
#: 멱등성을 갖췄으므로 시트를 고쳐 다시 부르면 된다. **조용한 오답이 시끄러운
#: 부재보다 나쁘다** — 정본 §11.1 1행 「부분집합 금지」가 이미 그렇게 적었다.
ROWS_HELD = "rows_held"


#: 그룹 이름이 그룹 배정표에 없다 — 추측하지 않는다.
UNKNOWN_GROUP = "unknown_group"

#: 프리셋 참조가 배정표에 없다 — 정의되지 않은 프리셋은 못 쓴다(§11.2 #5).
UNRESOLVED_PRESET = "unresolved_preset"

#: `unresolved_preset` 을 **원인별로** 가르는 닫힌 클래스.
#:
#: 이 분류를 붙이는 것은 이 층이 아니라 **툴 층**이다 -- 아래
#: `_HOLD_BLOCK_CLASS` 가 적어 둔 「이 층에서는 안 갈린다」가 그 이유이고,
#: 시트(정의)와 콘솔 되읽기(조인)를 **둘 다** 쥔 자리는
#: `import_lxseq_cues` 뿐이다. 그런데 어휘는 여기 둔다: `UNRESOLVED_PRESET`
#: 을 **세는** 코드와 그것을 **가르는** 어휘가 다른 파일에서 자라면, 한쪽만
#: 늘어난 날 두 산출물이 같은 것을 다른 이름으로 부른다.
#:
#: 셋을 가르는 이유는 처방이 다르기 때문이다 -- 시트를 안 실은 것은 호출
#: 인자를 고치면 되고, 시트에 ID 가 없는 것은 시트를 고쳐야 하고, 콘솔에
#: 그 이름이 없는 것은 **프리셋을 먼저 만들어야** 한다. 한 덩어리로 세면
#: 「어느 하나를 풀면 몇 건이 열리는지」를 아무도 모른다
#: (`preset_parser` 의 HOLD_* 닫힌 클래스가 같은 이유로 있다).
UNRESOLVED_SHEET_NOT_SUPPLIED = "sheet_not_supplied"
UNRESOLVED_SHEET_LACKS_ID = "sheet_lacks_id"
UNRESOLVED_CONSOLE_LACKS_NAME = "console_lacks_name"
UNRESOLVED_POOL_UNREADABLE = "pool_unreadable"

#: 수치 열이 수로 안 읽힌다.
BAD_NUMBER = "bad_number"

#: Snap 열이 닫힌 어휘 밖이다.
BAD_SNAP = "bad_snap"

#: Dim 이 0–100 밖이다(§11.1 3행).
DIM_OUT_OF_RANGE = "dim_out_of_range"

#: 같은 이름의 시퀀스가 이미 있다 — **목표 상태가 이미 달성돼 있다.**
#: 거절이 아니라 수렴이다(형제 preset_mapper.NAME_TAKEN 과 같은 규약).
NAME_TAKEN = "name_taken"

#: 페이저 정지. 빈칸(=이펙트 언급 없음)과 **다른 상태**다(§11.1 7행).
FX_STOP = "OFF"

#: 프리셋 ID 한 체계 — TYPE 과 2자리 숫자(§10 머리말). TYPE 넷이 닫힌 어휘다.
#: 종류마다 해석기를 따로 두지 않는 이유는, 갈라지면 한쪽만 고쳐지기 때문이다.
PRESET_REF_PATTERN = re.compile(r"^(POS|COL|BM|FX)\.([0-9]{2})$")

#: 「안 된다」 3분류 (AC-LXSEQ4-014). **기본값은 (C)** 다.
#:
#: (A) 로 분류하려면 왜 우리 코드 문제인지 근거를 **같은 줄에** 대야 하므로,
#: 거절 코드만 보고는 (A) 를 붙일 수 없다 -- 아래 표에 (A) 항목이 하나도 없는
#: 것은 누락이 아니라 **설계**다. 근거 없는 (A) 는 감독께 여쭤보면 끝날 일을
#: 조사 카드로 만드는 형태이고, 그것을 막는 것이 이 AC 의 목적이다.
BLOCK_OUR_DEFECT = "A_our_code_defect"
BLOCK_CONSOLE_STATE = "B_console_state"
BLOCK_DOC_INTENT = "C_doc_intent_unverified"

#: 거절 코드 -> (분류, 왜 그 분류인가).
_REFUSAL_BLOCK_CLASS: dict[str, tuple[str, str]] = {
    CUE_COVERAGE_GAP: (
        BLOCK_DOC_INTENT,
        "시트가 선언한 큐 중 행이 없는 것이 있다 -- 작성자가 트래킹으로 두려던 "
        "것인지 빠뜨린 것인지 시트만으로는 안 갈린다",
    ),
    SLOT_SHORTFALL: (
        BLOCK_CONSOLE_STATE,
        "콘솔의 시퀀스 풀에 빈 슬롯이 없거나 번호를 못 읽었다 -- 쇼 파일 상태다",
    ),
}

#: 보류 사유 -> (분류, 왜 그 분류인가). ROWS_HELD 는 행마다 사유가 달라
#: 한 덩어리로 못 묶는다.
_HOLD_BLOCK_CLASS: dict[str, tuple[str, str]] = {
    UNKNOWN_GROUP: (
        BLOCK_CONSOLE_STATE,
        "그 이름의 그룹이 콘솔 그룹 배정표에 없다 -- 2단계가 만들지 않았거나 쇼 파일이 다르다",
    ),
    UNRESOLVED_PRESET: (
        BLOCK_DOC_INTENT,
        "프리셋 참조가 배정표에 없다 -- PRESET 시트에 정의가 없는 것인지, "
        "정의는 있는데 콘솔 슬롯 조인이 안 선 것인지 이 층에서는 안 갈린다",
    ),
    BAD_NUMBER: (BLOCK_DOC_INTENT, "시트 셀이 수로 안 읽힌다 -- 작성 문면 문제다"),
    BAD_SNAP: (BLOCK_DOC_INTENT, "Snap 셀이 닫힌 어휘(Y·빈칸) 밖이다"),
    DIM_OUT_OF_RANGE: (BLOCK_DOC_INTENT, "Dim 이 0-100 밖이다(§11.1 3행)"),
}


def block_report(result: CueMapResult) -> tuple[dict[str, object], ...]:
    """막힌 자리를 (A)/(B)/(C) 로 분류해 편다 (AC-LXSEQ4-014).

    거절이 없어도 보류가 있으면 싣는다 -- 다만 이 층에서는 보류가 곧 거절이라
    (ROWS_HELD) 실제로는 함께 온다. 분류를 못 찾으면 **기본값 (C)** 다:
    모르는 것을 우리 결함으로 올려 부르지 않는다.
    """
    rows: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()

    refusal = result.refusal
    if refusal is not None and refusal != ROWS_HELD:
        klass, why = _REFUSAL_BLOCK_CLASS.get(
            refusal,
            (BLOCK_DOC_INTENT, "분류표에 없는 거절 코드다 -- 기본값 (C)"),
        )
        rows.append(dict(code=refusal, block_class=klass, why=why, where=[]))

    where_by_cause: dict[str, list[str]] = {}
    for item in result.held:
        for cause in item.hold_classes:
            where_by_cause.setdefault(cause, []).append(item.cue_no + " / " + item.group)
    for cause, where in where_by_cause.items():
        klass, why = _HOLD_BLOCK_CLASS.get(
            cause,
            (BLOCK_DOC_INTENT, "분류표에 없는 보류 사유다 -- 기본값 (C)"),
        )
        key = (cause, klass)
        if key in seen:
            continue
        seen.add(key)
        rows.append(dict(code=cause, block_class=klass, why=why, where=list(where)))
    return tuple(rows)


_VALUE_MATCH_REASON = (
    "이 층은 **놓을 자리와 값을 정할 뿐** 콘솔이 그것을 받았는지 되읽지 않는다. "
    "되읽기 채널(cue_monitor._cue_items)은 번호와 이름까지만 답하고 **큐 내용은 "
    "안 준다** — 「시퀀스가 있다」는 「큐가 맞게 들어갔다」가 아니다"
)

_TRACKING_REASON = (
    "빈칸은 **트래킹**이라 이 계획에 아무 값도 싣지 않는다. 앞 큐의 값이 그대로 "
    "산다는 뜻이고, 그 값이 무엇인지는 이 층이 모른다 — 큐 스택을 따라가야 안다"
)

_NAME_UNREADABLE_REASON = (
    "점유 슬롯 중 **이름을 못 읽은 것**이 있어 그 슬롯과는 이름을 대조하지 "
    "못했다. 같은 이름의 시퀀스가 이미 있는데도 계획에 들어갔을 수 있다"
)


@dataclass(frozen=True)
class PresetRef:
    """해석된 프리셋 참조 — 시트의 ID 와 콘솔 슬롯의 대응.

    원문(`raw`)을 같이 나른다. 슬롯만 남기면 계획을 읽는 사람이 어느 시트 행에서
    왔는지 못 되짚는다.
    """

    raw: str
    kind: str
    slot: int


@dataclass(frozen=True)
class PhaseSpread:
    """FX-Phase 값 — 한 수이거나 **그룹 내 확산 구간**이다(§11.1 9행).

    명세서가 이 열에 `0` 과 `0..360` 두 모양을 함께 적었다. 확산은 그룹 멤버마다
    위상을 벌리라는 뜻이라 단일 수로 접히지 않는다 — 접으면 그룹 전체가 같은
    위상으로 돌고, 그것은 시트가 의도한 파도가 아니라 **일제히 깜빡임**이 된다.

    `end` 가 None 이면 한 수다. 두 모양을 한 타입으로 두는 이유는, 소비자가
    `isinstance` 로 갈래를 타면 한쪽만 고친 변경이 조용히 남기 때문이다.

    ⚠️ 정본 CSV 는 `0..360` 말고 **`180..540` 도 쓴다**(10행). 명세서 문면은
    `0..360` 만 예로 들지만 확산은 시작점이 0이 아닐 수 있으므로 일반형
    `A..B` 를 받는다 — 문면을 좁게 읽으면 정본의 10행이 거절된다.
    """

    start: float
    end: float | None = None

    @property
    def is_spread(self) -> bool:
        return self.end is not None


@dataclass(frozen=True)
class SequencePlacement:
    """이 시트가 앉을 시퀀스 슬롯 하나. 큐 번호는 여기 없다 — 시트가 정한다."""

    name: str
    slot: int


@dataclass(frozen=True)
class CueRowPlan:
    """한 큐 × 한 그룹의 계획 한 행.

    🔴 **None 은 「0」이 아니라 「건드리지 않는다」다.** 이 구분이 이 층의 존재
    이유다(§11.2 #1). 소비자가 `dim or 0` 으로 읽으면 트래킹이 소등이 되고,
    그것은 무대에서 조명이 꺼지는 결함이다.
    """

    cue_no: str
    group: str
    group_no: int
    dim: float | None
    col: PresetRef | None
    pos: PresetRef | None
    bm: PresetRef | None
    fx: PresetRef | None
    #: FX 열이 OFF 였다 — 페이저 **정지 명령**이다. `fx is None` 과 다르다.
    fx_stop: bool
    fx_rate: float | None
    fx_phase: PhaseSpread | None
    fx_width: float | None
    i_fade: float | None
    i_delay: float | None
    p_fade: float | None
    c_fade: float | None
    b_fade: float | None
    snap: bool
    note: str

    @property
    def is_blackout(self) -> bool:
        """소등 행인가 — Dim 0 과 I-Fade 가 **함께** 있을 때만(§11.2 #2).

        `dim == 0` 만으로 참이 되지 않는다. 명세서가 「침묵으로 끄지 않는다」고
        적은 것은 페이드를 안 적은 0 을 소등으로 읽지 말라는 뜻이다.
        """
        return self.dim == 0.0 and self.i_fade is not None


@dataclass(frozen=True)
class CueBucket:
    """한 큐의 콘솔 행 묶음. 큐 번호는 시트가 준 것을 그대로 쓴다."""

    cue_no: str
    rows: tuple[CueRowPlan, ...]


@dataclass(frozen=True)
class CueHold:
    """계획에 못 들어간 한 행 — 사유 클래스와 산문을 함께 나른다."""

    cue_no: str
    group: str
    hold_classes: tuple[str, ...]
    details: tuple[str, ...]


@dataclass(frozen=True)
class VideoCall:
    """영상 콜 행 — 콘솔에 안 보내고, 버리지도 않는다.

    🔴 과거에 이 행들이 콘솔 명령이 되어 나간 사고가 있었다. 그래서 배치에서
    빼되 **결과에 남긴다**: 「이 큐에 영상 콜이 있다」는 운영 정보이고, 조용히
    사라지면 큐시트를 읽는 사람이 그 큐를 비어 있는 것으로 본다.

    `held` 에 섞지 않는 이유는 형제 preset_mapper 가 already_present 를 가른
    이유와 같다 — 보류는 「고치면 들어갈 것」이고 이것은 **설계상 안 들어갈
    것**이다. 섞으면 「보류 N건」이 고칠 거리로 읽힌다.
    """

    cue_no: str
    group: str
    note: str


@dataclass(frozen=True)
class CueCoverageGap:
    """선언된 큐와 행이 있는 큐의 대조표. 부분 계획 대신 이것을 낸다."""

    declared: tuple[str, ...]
    covered: tuple[str, ...]
    missing: tuple[str, ...]


@dataclass(frozen=True)
class CueMapResult:
    """매퍼 산출물.

    `refusal` 이 있으면 `planned` 는 반드시 비어 있다 — 어긋나면 0건이다.
    `held` 와 `video_calls` 는 `refusal` 과 무관하게 항상 실린다: 사용자가 시트를
    고칠 근거는 콘솔 상태와 무관하다(형제 preset_mapper 가 held 를 거절 경로에도
    싣는 것과 같은 이유).

    `refusal` 이 없고 `already_present` 도 없을 때 **세 바구니의 합이 읽은 행
    수와 같다**: `planned` 의 행 + `held` + `video_calls`.
    """

    planned: tuple[CueBucket, ...]
    held: tuple[CueHold, ...]
    video_calls: tuple[VideoCall, ...]
    coverage_gap: CueCoverageGap | None
    refusal: str | None
    refusal_detail: str
    #: 배정된 시퀀스 슬롯. 거절 경로와 already_present 경로에서는 None.
    placement: SequencePlacement | None = None
    #: 같은 이름의 시퀀스가 이미 있다 -- **거절이 아니다**, 컨테이너가 이미
    #: 있다는 뜻일 뿐이다. 계획을 막지 않는다(이전엔 막았다 -- 시퀀스 층과
    #: 큐 층을 안 갈라 18큐가 통째로 안 나갔다, 리드 재현 2026-08-31). 그
    #: 시퀀스 안에 없는 큐는 그대로 planned 에 들어간다.
    already_present: SequencePlacement | None = None
    #: 이미 그 시퀀스 안에 있는 큐 번호라서 계획에서 뺀 것들 -- 시퀀스
    #: 층의 already_present 와는 다른 축이다(형제 preset_mapper 의 레코드
    #: 단위 NAME_TAKEN 과 같은 무게).
    cues_already_present: tuple[str, ...] = ()
    #: 콘솔 행이 0인데 **영상 콜만 있어서** 그런 큐. 결함이 아니라 상태다 —
    #: 그 큐는 조명이 할 일이 없다. 보류로 비어 버린 큐와 **다르다**(그쪽은 거절).
    video_only_cues: tuple[str, ...] = ()
    #: 확인 한계 — 산출물이 스스로 말한다(형제 preset_mapper 와 같은 규약).
    unverified: tuple[str, ...] = ("value_match", "tracked_value")
    unverified_reason: str = _VALUE_MATCH_REASON + " / " + _TRACKING_REASON


def resolve_preset_ref(
    raw: str,
    *,
    preset_slots: Mapping[str, int],
) -> tuple[PresetRef | None, str | None]:
    """COL.01 같은 참조 하나를 해석한다.

    반환은 (참조, 사유) 쌍이다. 빈칸이면 (None, None) — **트래킹이지 결함이
    아니다.** 문법이 맞는데 배정표에 없으면 (None, 사유) 로 사유를 낸다.

    TYPE 마다 해석기를 두지 않는 이유는 §10 이 프리셋 ID 를 **한 체계**로
    적었기 때문이다. 넷으로 갈라 놓으면 한 종류만 고친 변경이 조용히 남는다.
    """
    text = raw.strip()
    if not text:
        return None, None
    found = PRESET_REF_PATTERN.match(text)
    if found is None:
        return None, "프리셋 참조 문법이 아니다: " + text + " — TYPE 과 2자리 한 체계다(§10)"
    if text not in preset_slots:
        return None, (
            "프리셋 " + text + " 가 배정표에 없다 — PRESET 시트에 정의된 것만 쓴다(§11.2 #5). "
            "정의되지 않은 참조를 빈칸처럼 넘기면 그 행이 **트래킹으로 조용히 "
            "바뀐다**"
        )
    return PresetRef(raw=text, kind=found.group(1), slot=preset_slots[text]), None


def _held_digest(held: Sequence[CueHold]) -> str:
    """보류된 행들을 「어느 큐 · 어느 행 · 왜」로 편다.

    맨 「0건」은 **다른 침묵**일 뿐이라 사람이 89행을 눈으로 훑게 만든다. 사유
    클래스는 이 모듈이 이미 쓰는 어휘를 그대로 쓴다 — 거절 전용 어휘를 따로
    만들면 같은 실패가 자리마다 다른 이름으로 불린다.
    """
    lines = [
        item.cue_no
        + " / "
        + item.group
        + ": "
        + ", ".join(item.hold_classes)
        + " — "
        + " · ".join(item.details)
        for item in held
    ]
    return "; ".join(lines)


def _number(raw: str, *, column: str) -> tuple[float | None, str | None]:
    """수치 열 하나. 빈칸은 (None, None) — 트래킹이지 0이 아니다."""
    text = raw.strip()
    if not text:
        return None, None
    try:
        return float(text), None
    except ValueError:
        return None, column + " 열이 수로 안 읽힌다: " + text


def _phase(raw: str) -> tuple[PhaseSpread | None, str | None]:
    """FX-Phase 열. 한 수이거나 `A..B` 확산이다(§11.1 9행).

    빈칸은 (None, None) — 트래킹이다. 확산을 단일 수로 접지 않는 이유는
    `PhaseSpread` 독스트링에 적었다.
    """
    text = raw.strip()
    if not text:
        return None, None
    if ".." in text:
        head, _, tail = text.partition("..")
        try:
            start, end = float(head), float(tail)
        except ValueError:
            return None, "FX-Phase 확산이 수로 안 읽힌다: " + text
        if end <= start:
            return None, "FX-Phase 확산의 끝이 시작보다 크지 않다: " + text
        return PhaseSpread(start=start, end=end), None
    try:
        return PhaseSpread(start=float(text)), None
    except ValueError:
        return None, "FX-Phase 열이 수로 안 읽힌다: " + text


def _snap(raw: str) -> tuple[bool, str | None]:
    """Snap 열. 닫힌 어휘는 Y 와 빈칸 둘뿐이다(§11.1 16행)."""
    text = raw.strip().upper()
    if not text:
        return False, None
    if text == "Y":
        return True, None
    return False, "Snap 열이 닫힌 어휘 밖이다: " + raw.strip() + " — Y 또는 빈칸"


def _occupied_slots(section: Mapping[str, object]) -> set[int] | None:
    """콘솔이 답한 점유 슬롯 집합. 못 읽으면 None — **추측하지 않는다.**

    한 항목의 번호를 못 읽으면 **어느 슬롯도** 비었다고 말할 수 없다. 형제
    preset_mapper._occupied_slots 와 같은 판단이다.
    """
    listed = section.get("objects")
    if not isinstance(listed, list):
        return None
    occupied: set[int] = set()
    for entry in listed:
        number = entry.get("no") if isinstance(entry, Mapping) else None
        if not isinstance(number, int):
            return None
        occupied.add(number)
    return occupied


def _occupied_names(section: Mapping[str, object]) -> tuple[dict[str, int], bool]:
    """점유 **이름 -> 슬롯** 표와 「못 읽은 이름이 있었나」.

    **번호와 달리 이름은 못 읽어도 거절하지 않는다.** 번호를 틀리면 점유 슬롯을
    덮어써 복구가 불가능하지만, 이름을 모르면 생기는 것은 **중복**이다. 무게가
    달라 처방도 다르다 — 거절 대신 unverified 에 한계를 싣는다.
    """
    listed = section.get("objects")
    names: dict[str, int] = dict()
    if not isinstance(listed, list):
        return names, True
    incomplete = False
    for entry in listed:
        if not isinstance(entry, Mapping):
            incomplete = True
            continue
        raw = entry.get("name")
        number = entry.get("no")
        if not isinstance(raw, str) or not raw or not isinstance(number, int):
            incomplete = True
            continue
        names.setdefault(raw, number)
    return names, incomplete


def _cue_number(cue_no: str) -> int | None:
    """ "Q010" -> 10. 콘솔이 답하는 cueNo(정수)와 대조하려면 시트 쪽 번호도
    정수여야 한다. 자릿수가 아니면 None -- 정본 형식(Q + 숫자)이 아닌 값은
    대조하지 않는다(추측하지 않는다, 형제 술어들과 같은 규율)."""
    digits = cue_no.removeprefix("Q")
    return int(digits) if digits.isdigit() else None


def _lowest_free_slot(occupied: set[int], *, capacity: int | None) -> int | None:
    """가장 낮은 빈 슬롯. 상한이 있고 그 안에 빈자리가 없으면 None."""
    candidate = 1
    while capacity is None or candidate <= capacity:
        if candidate not in occupied:
            return candidate
        candidate += 1
    return None


def map_cues(
    records: Sequence[LxseqCueRecord],
    *,
    declared_cues: Sequence[str],
    sequence_name: str,
    sequence_section: Mapping[str, object],
    group_slots: Mapping[str, int],
    preset_slots: Mapping[str, int],
    slot_capacity: int | None = None,
    existing_cue_numbers: Sequence[int] = (),
) -> CueMapResult:
    """CUE-EX 레코드를 **시퀀스 하나 + 그 아래 큐들**의 계획으로 바꾼다.

    `declared_cues` 는 파서가 정본 CSV 에서 읽은 큐 번호다(정본에서 18개).
    `sequence_section` 은 콘솔이 답한 시퀀스 풀 단면 — 형제의 pool_section ·
    groups_section 과 같은 자리다. `group_slots` 는 2단계가 배정한 「그룹 이름
    -> 콘솔 그룹 번호」, `preset_slots` 는 3단계가 배정한 「프리셋 ID -> 콘솔
    슬롯」이다. 뒤 둘은 이 층에서 만들지 않는다 — 만들면 앞 단계와 배정이 갈린다.
    existing_cue_numbers 는 시퀀스가 이미 있을 때 그 안에 실제로 있는
    큐 번호(콘솔 cueNo, 응답기 1.5.0+) -- 새 시퀀스에는 못 있을 수밖에 없는
    값이라 이 층은 already_present 가 아닐 때 이 인자를 쓰지 않는다.

    어긋나면 아무것도 만들지 않는다. 반쯤 맞는 큐 스택은 이 도메인에서 최악의
    결과다: 쇼가 도는 도중에 드러나고, 그때는 고칠 시간이 없다.
    """
    held: list[CueHold] = []
    video_calls: list[VideoCall] = []
    rows_by_cue: dict[str, list[CueRowPlan]] = dict()
    seen_cues: list[str] = []

    for record in records:
        cue_no = record.cue_no
        if cue_no not in seen_cues:
            seen_cues.append(cue_no)

        # 🔴 영상 콜은 **가장 먼저** 걷어낸다 — 해석하기 전에.
        # 해석 후에 거르면 그 행의 Dim 이 계획 값으로 한 번 만들어지고, 그 값이
        # 로그·미리보기에 남는다. 「만들었다가 안 보낸다」와 「만들지 않는다」는
        # 사고가 났을 때 다른 이야기가 된다.
        if record.is_video_call:
            video_calls.append(VideoCall(cue_no=cue_no, group=record.group, note=record.note))
            continue

        classes: list[str] = []
        details: list[str] = []

        group_no = group_slots.get(record.group)
        if group_no is None:
            classes.append(UNKNOWN_GROUP)
            details.append(
                "그룹 " + record.group + " 가 그룹 배정표에 없다 — 2단계가 만들지 않은 그룹이다. "
                "추측해서 번호를 붙이지 않는다"
            )

        refs: dict[str, PresetRef | None] = dict()
        for column, raw in (
            ("COL", record.col_raw),
            ("POS", record.pos_raw),
            ("BM", record.bm_raw),
        ):
            ref, reason = resolve_preset_ref(raw, preset_slots=preset_slots)
            refs[column] = ref
            if reason is not None:
                classes.append(UNRESOLVED_PRESET)
                details.append(column + ": " + reason)

        # FX 열만 어휘가 하나 더 있다 — OFF 는 참조가 아니라 **정지 명령**이다.
        fx_stop = record.fx_raw.strip().upper() == FX_STOP
        fx_ref: PresetRef | None = None
        if not fx_stop:
            fx_ref, fx_reason = resolve_preset_ref(record.fx_raw, preset_slots=preset_slots)
            if fx_reason is not None:
                classes.append(UNRESOLVED_PRESET)
                details.append("FX: " + fx_reason)

        numbers: dict[str, float | None] = dict()
        for column, raw in (
            ("Dim", record.dim_raw),
            ("FX-Rate", record.fx_rate_raw),
            ("FX-Width", record.fx_width_raw),
            ("I-Fade", record.i_fade_raw),
            ("I-Delay", record.i_delay_raw),
            ("P-Fade", record.p_fade_raw),
            ("C-Fade", record.c_fade_raw),
            ("B-Fade", record.b_fade_raw),
        ):
            value, number_reason = _number(raw, column=column)
            numbers[column] = value
            if number_reason is not None:
                classes.append(BAD_NUMBER)
                details.append(number_reason)

        dim = numbers["Dim"]
        if dim is not None and not (0.0 <= dim <= 100.0):
            classes.append(DIM_OUT_OF_RANGE)
            details.append("Dim 이 0–100 밖이다: " + record.dim_raw.strip())

        phase, phase_reason = _phase(record.fx_phase_raw)
        if phase_reason is not None:
            classes.append(BAD_NUMBER)
            details.append(phase_reason)

        snap, snap_reason = _snap(record.snap_raw)
        if snap_reason is not None:
            classes.append(BAD_SNAP)
            details.append(snap_reason)

        if classes:
            # 🔴 **행 단위로 보류한다.** 성한 열만 골라 보내지 않는다.
            # 색을 못 찾은 행에서 Dim 만 보내면 앞 큐의 색이 그대로 남은 채
            # 밝기만 바뀐다 — 시트가 의도한 룩이 아니고, 무대에서는 그것이
            # 「고장」이 아니라 「다른 룩」으로 보여 아무도 못 알아챈다.
            held.append(
                CueHold(
                    cue_no=cue_no,
                    group=record.group,
                    hold_classes=tuple(dict.fromkeys(classes)),
                    details=tuple(details),
                )
            )
            continue

        assert group_no is not None  # 위에서 None 이면 classes 가 비지 않는다
        rows_by_cue.setdefault(cue_no, []).append(
            CueRowPlan(
                cue_no=cue_no,
                group=record.group,
                group_no=group_no,
                dim=dim,
                col=refs["COL"],
                pos=refs["POS"],
                bm=refs["BM"],
                fx=fx_ref,
                fx_stop=fx_stop,
                fx_rate=numbers["FX-Rate"],
                fx_phase=phase,
                fx_width=numbers["FX-Width"],
                i_fade=numbers["I-Fade"],
                i_delay=numbers["I-Delay"],
                p_fade=numbers["P-Fade"],
                c_fade=numbers["C-Fade"],
                b_fade=numbers["B-Fade"],
                snap=snap,
                note=record.note,
            )
        )

    declared = tuple(declared_cues)
    covered = tuple(cue for cue in declared if cue in seen_cues)
    missing = tuple(cue for cue in declared if cue not in seen_cues)
    if missing:
        # 부분집합 금지(§11.1 1행). 시트 자체가 큐를 빠뜨렸다 — 계획을 내지 않는다.
        return CueMapResult(
            planned=(),
            held=tuple(held),
            video_calls=tuple(video_calls),
            coverage_gap=CueCoverageGap(declared=declared, covered=covered, missing=missing),
            refusal=CUE_COVERAGE_GAP,
            refusal_detail=(
                "선언된 큐 "
                + str(len(declared))
                + " 개 중 "
                + str(len(missing))
                + " 개에 행이 없다: "
                + ", ".join(missing)
                + " — 부분집합은 금지다(§11.1). 빠진 큐는 트래킹으로 지나가는데, "
                "그 큐에서 무엇이 살아 있어야 하는지 시트가 말한 적이 없다"
            ),
        )

    # 🔴 [HARD] AC-LXSEQ4-007 — 한 행이라도 못 옮기면 배치 전체가 0건이다.
    #
    # 이 게이트가 `held` 를 **소비하지 않는다** — 아래 `held=tuple(held)` 로 그대로
    # 실어 preview 가 고칠 자리를 전부 보여준다. 바뀐 것은 **콘솔에 무엇이 닿는가**
    # 하나뿐이다: 전에는 성한 행만 골라 그 큐를 불완전한 채로 내보냈다.
    #
    # 시트 층의 결함이라 콘솔 단면을 읽기 전에 답한다 — 콘솔이 어떤 상태든 처방이
    # 같기 때문이다(시트를 고쳐 다시 부른다).
    if held:
        return CueMapResult(
            planned=(),
            held=tuple(held),
            video_calls=tuple(video_calls),
            coverage_gap=None,
            refusal=ROWS_HELD,
            refusal_detail=(
                "행 "
                + str(len(held))
                + " 개를 계획에 못 넣어 **아무것도 보내지 않았다** — 부분 투입이 없다"
                "(§11.1 1행 부분집합 금지). 한 그룹이 빠진 큐는 MA3 트래킹 때문에 큐 "
                "리스트에서 정상으로 보이고 발사할 때에야 어긋난다. 고칠 자리: "
                + _held_digest(held)
            ),
        )

    names, names_incomplete = _occupied_names(sequence_section)
    unverified = ["value_match", "tracked_value"]
    unverified_reason = _VALUE_MATCH_REASON + " / " + _TRACKING_REASON
    if names_incomplete:
        unverified.append("name_collision")
        unverified_reason = unverified_reason + " / " + _NAME_UNREADABLE_REASON

    # [HARD] 슬롯을 재기 전에 단면이 관측인지 묻는다. 술어는 이 저장소에
    # 하나뿐이고(server/rig/section.py), 슬롯을 재는 자리는 전부 그것을 부른다.
    if (reason := section_refusal(sequence_section)) is not None:
        return CueMapResult(
            planned=(),
            held=tuple(held),
            video_calls=tuple(video_calls),
            coverage_gap=None,
            refusal=reason[0],
            refusal_detail=reason[1],
        )

    # 시퀀스 층: 이미 있으면 그 슬롯을 그대로 쓴다(already_present) -- 새로
    # 배정하지 않는다. 없으면 빈 슬롯을 골라 새로 만든다(placement). 두
    # 갈래가 서로 다른 필드에 실리는 이유는 tools.py 가 이 값으로
    # Store Sequence 명령을 낼지 말지 가르기 때문이다(already_present 면
    # 안 낸다, placement 면 낸다).
    existing_slot = names.get(sequence_name)
    is_new_sequence = existing_slot is None

    if is_new_sequence:
        occupied = _occupied_slots(sequence_section)
        slot = None if occupied is None else _lowest_free_slot(occupied, capacity=slot_capacity)
        if slot is None:
            return CueMapResult(
                planned=(),
                held=tuple(held),
                video_calls=tuple(video_calls),
                coverage_gap=None,
                refusal=SLOT_SHORTFALL,
                refusal_detail=(
                    "빈 시퀀스 슬롯을 못 골랐다 -- 번호를 못 읽었거나 상한 "
                    + str(slot_capacity)
                    + " 안에 빈자리가 없다. 점유 슬롯에는 쓰지 않는다: 시퀀스는 경고 "
                    "없이 덮이고 내용은 되읽을 수 없어 복구 수단이 없다"
                ),
            )
    else:
        slot = existing_slot

    # 큐 층: 시퀀스가 이미 있을 때만 의미가 있다 -- 새 시퀀스엔 큐가 있을
    # 수 없다(existing_cue_numbers 를 실수로 넘겨도 새 시퀀스에서는 안 쓴다).
    cues_already_present: tuple[str, ...] = ()
    if not is_new_sequence and existing_cue_numbers:
        present = frozenset(existing_cue_numbers)
        cues_already_present = tuple(cue for cue in declared if _cue_number(cue) in present)

    # 콘솔 행이 0인데 영상 콜만 있어서 그런 큐는 **정상 상태**다 -- 그 큐는
    # 조명이 할 일이 없다. 「보류로 비어 버린 큐」 갈래는 여기 없다: 위의
    # ROWS_HELD 게이트가 held 가 하나라도 있으면 이미 거절했으므로 이 지점의
    # held 는 반드시 비어 있다(선행 상수 cue_emptied_by_hold 는 그 게이트에
    # 완전히 포함돼 폐기됐다).
    assert not held  # 위 게이트가 보장한다 -- 아래 갈래의 전제다
    video_only_cues = tuple(
        cue
        for cue in declared
        if not rows_by_cue.get(cue)
        and cue not in cues_already_present
        and any(call.cue_no == cue for call in video_calls)
    )

    placement_obj = SequencePlacement(name=sequence_name, slot=slot)
    planned = tuple(
        CueBucket(cue_no=cue, rows=tuple(rows_by_cue[cue]))
        for cue in declared
        if rows_by_cue.get(cue) and cue not in cues_already_present
    )
    return CueMapResult(
        planned=planned,
        held=tuple(held),
        video_calls=tuple(video_calls),
        coverage_gap=None,
        refusal=None,
        refusal_detail="",
        placement=placement_obj if is_new_sequence else None,
        already_present=None if is_new_sequence else placement_obj,
        cues_already_present=cues_already_present,
        video_only_cues=video_only_cues,
        unverified=tuple(unverified),
        unverified_reason=unverified_reason,
    )
