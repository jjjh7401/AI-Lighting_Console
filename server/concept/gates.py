"""곡 단위 조립 + 13개 검증 게이트 — SPEC-LDDESIGN-001 M6 (REQ-LDDESIGN-075~076,
카드 t439).

순수 데이터 모듈이다 — OSC 송신·콘솔 접근·네트워크를 하지 않는다(다른
``server/concept/*`` 모듈과 같은 원칙).

이 모듈은 ``.moai/state/verify/f12e5c95-t429/final_integrated.py``(이하
"프로토타입")가 단일 파일로 하던 일 — baseline_name 재매핑 → 팔레트 색
결정 → 안전 큐 포함 전체 시퀀스 해석 → 13개 검증 게이트 판정 — 을
``server/concept/`` 의 기존 모듈(density·resolver·escalation·headroom·
color_lint·color_strip·timing·tracking·mib·safety·vocab)로 재조립한다.
컬러 검사·에너지·페이드 로직 자체는 재구현하지 않는다 — 그 모듈들을
그대로 호출한다.

프로토타입과 알려진 편차(의도적):

- G4 는 escalation.py 의 새 정의(카드 t439 REQ-044/048 재정의 — 직전
  한 줄이 아니라 피날레 이전 최대 모션)를 쓴다.
- G6 은 프로토타입의 인라인 ``bridge_viol`` 공식(사실상 REQ-029 의
  "암전 전환은 예외" 예외 케이스를 거꾸로 위반으로 셈)이 아니라
  :func:`server.concept.color_lint.check_adjacent_bridge`(REQ-029 그대로
  구현)와 :func:`server.concept.color_lint.check_reserved_color_release`
  (REQ-027)를 합성해서 낸다.
- G9 의 "누출 0" 절은 프로토타입에서 항상 참인 자리표시자
  (``all(True for _ in [0])``)였다 — 이 모듈은
  :func:`server.concept.tracking.verify_no_cue_only_leak` 로 실제 검사한다.
- Outro 구간 동작은 density.py 가 프로토타입과 다르게 짠다(M4 스코프
  독자 결정) — 이 모듈은 그 차이를 그대로 받아들인다.

**색 입력(카드 t444).** 아래 ``PRIMARY_COLOR`` 등 상수 4개는 프로토타입
팔레트를 옮긴 자리표시자다 — 입력이 아니다. 색에 기대는 게이트(G2·G6·
G7 전체, G5 의 "Chorus 1 흰색" 조건 하나)는 원시 구간이 ``palette``(그
구간이 실제로 내는 색 이름 목록, 주색 먼저)를 실어 올 때만 그 색으로
판정한다. 실어 오지 않으면 n/a(:data:`NO_INPUT_COLOR_REASON`)다 — 상수로
판정한 값은 무대에 나갈 색에 대한 증거가 아니다. 상수 팔레트는 색 입력이
없을 때 큐 상태를 채우는 데만 계속 쓰인다(컴파일·에너지 경로가 오늘과
바이트 동일하게 남도록).

이 편차들이 판정 결과(PASS/FAIL/n/a)를 바꾸는지는 오늘 실측한
프로토타입 기준선(``.moai/reports/t439/baseline/matrix.json``)과 셀 단위로
대조한다(REQ-076) — 이 파일 자체는 그 대조 결과를 담지 않는다(시험의 몫).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from server.concept.color_lint import (
    ColorLintResult,
    check_adjacent_bridge,
    check_chorus_identity,
    check_reserved_color_release,
)
from server.concept.color_strip import ConceptCue
from server.concept.cue_model import CueState, Timing
from server.concept.density import (
    CHORUS_FAMILY,
    GROUP_ROSTER,
    MOVER_GROUPS,
    ColorForCallback,
    SectionOccurrence,
    bar_seconds,
    compile_density,
)
from server.concept.escalation import (
    ChorusPair,
    GateResult,
    build_chorus_snapshots,
    check_pairs,
    g2_identity,
    remaining_motion_before_final,
)
from server.concept.escalation import g3_new_axis_within_five as _g3_new_axis_within_five
from server.concept.escalation import (
    g4_final_new_axis_and_headroom as _g4_final_new_axis_and_headroom,
)
from server.concept.headroom import SectionCueSnapshot, g5_warnings
from server.concept.mib import MibVerdict, compute_mib_sequence
from server.concept.resolver import resolve_sequence
from server.concept.safety import first_safety_cue, last_safety_cue
from server.concept.timing import chorus_entry_timing, default_timing
from server.concept.tracking import verify_no_cue_only_leak
from server.concept.vocab import VocabError, validate_one_shot, validate_section, validate_trigger

__all__ = [
    "PRIMARY_COLOR",
    "SECONDARY_COLOR",
    "CLIMAX_COLOR",
    "UNDER_COLOR",
    "RESERVED_COLORS",
    "NO_INPUT_COLOR_REASON",
    "TableRow",
    "SongBuild",
    "remap_baseline_sections",
    "build_song",
    "evaluate_song",
    "GATE_NAMES",
]

# --- 팔레트 — 프로토타입 9~10행(PAL) 그대로 옮긴다 --------------------------

PRIMARY_COLOR = "노랑"
SECONDARY_COLOR = "파랑"
CLIMAX_COLOR = "흰색"
UNDER_COLOR = "주황"
RESERVED_COLORS: tuple[str, ...] = (CLIMAX_COLOR,)

#: 카드 t444 — 입력에 색이 없을 때 색 의존 게이트가 내는 n/a 사유.
NO_INPUT_COLOR_REASON = "입력에 색 없음 — 상수 팔레트 판정 안 함"

#: G5 "Chorus 1 흰색" 조건이 흰색으로 보는 이름 — 상수 팔레트(한국어)와
#: 운영 경로 표준 10색(영어, ``server/design/color_names.py``) 둘 다.
#: 대소문자·공백만 접어 비교한다(``color_lint._normalize_color_name`` 과
#: 같은 규칙 — warm white 같은 수식어 붙은 이름은 흰색으로 치지 않는다).
_WHITE_NAMES: frozenset[str] = frozenset({"흰색", "white"})

_EFFECT_GROUPS: frozenset[str] = frozenset({"BLIND", "STROBE"})
_BUILDUP_TRIGGER = "빌드업 시작"

# 곡 마지막 안전 큐(``reduce factor=0.0``)가 참조할 기준 상태 이름 — 그
# 이름의 실제 값(어떤 그룹이 몇 %였는지)은 어느 게이트 판정에도 쓰이지
# 않으므로, density.py 의 마지막 시퀀스 큐에 이 이름으로 명시적
# ``base_name`` 을 하나 더 등록해 참조 대상을 항상 존재하게 만든다
# (REQ-069 "그룹 전부를 담은 기준 상태를 미리 등록해 둬야 한다" 의 가장
# 단순한 충족 방법 — 어느 곡이든 시퀀스 마지막 행은 항상 있다).
_RELEASE_REF_BASE_NAME = "song_release_reference"


def _mmss(text: str) -> float:
    """ "M:SS" 형식 문자열을 초로 바꾼다(프로토타입 50행 ``t`` 람다와 동일)."""
    minutes, seconds = str(text).split(":")
    return float(int(minutes) * 60 + int(seconds))


def remap_baseline_sections(
    raw_sections: Sequence[Mapping[str, object]],
) -> tuple[SectionOccurrence, ...]:
    """실기 판정기 원시 구간(``baseline_name``)을 9종 어휘로 재매핑한다.

    프로토타입 ``doc_sections()``(42~48행)와 동일 로직이다 — 마지막
    Chorus 는 전체 Chorus 발생이 3회 이상일 때만 Final Chorus 로
    승급하고, ``Finale`` 은 Outro 로, 그 밖의 이름은 Rap/Solo/Dance
    Break 로 묶는다.
    """
    chorus_positions = [
        i for i, x in enumerate(raw_sections) if str(x["baseline_name"]).startswith("Chorus")
    ]
    last_chorus = chorus_positions[-1] if chorus_positions else None
    occurrence_by_name: dict[str, int] = {}
    result: list[SectionOccurrence] = []
    for i, x in enumerate(raw_sections):
        name = str(x["baseline_name"]).split(" ")[0]
        if name == "Chorus" and i == last_chorus and len(chorus_positions) >= 3:
            section = "Final Chorus"
        elif name == "Finale":
            section = "Outro"
        elif name in ("Intro", "Verse", "Chorus", "Bridge"):
            section = name
        else:
            section = "Rap/Solo/Dance Break"
        occurrence_by_name[section] = occurrence_by_name.get(section, 0) + 1
        result.append(
            SectionOccurrence(
                section=section,
                occurrence=occurrence_by_name[section],
                start=_mmss(x["start"]),
                end=_mmss(x["end"]),
            )
        )
    return tuple(result)


def _buildup_under_flags(
    doc: Sequence[tuple[str, int]],
    starts: Sequence[float],
    *,
    bar: float,
    total_chorus: int,
) -> dict[int, bool]:
    """프리코러스 빌드업 큐마다 "언더페인팅"(클라이맥스 색 예고 심기)
    여부를 정한다 — 프로토타입 89~96행의 ``pre``/``under`` 계산과 동일
    로직이며, density.py 의 ``buildup_counter`` 증가 조건(REQ-037)과
    같은 문턱을 쓴다(달라지면 이 모듈이 낸 occurrence 번호와
    density.py 가 실제로 매긴 번호가 어긋난다).

    반환값의 키는 1-base 빌드업 발생 번호(``buildup_counter`` 값과
    같은 축)다.
    """
    chorus_indices = [i for i, (name, _) in enumerate(doc) if name in CHORUS_FAMILY]
    flags: dict[int, bool] = {}
    pre = 0
    for j, i in enumerate(chorus_indices):
        if i == 0 or doc[i - 1][0] in CHORUS_FAMILY:
            continue
        is_final = doc[i][0] == "Final Chorus"
        threshold_bars = 3 if is_final else 5
        prev_bars = (starts[i] - starts[i - 1]) / bar
        if prev_bars < threshold_bars:
            continue
        pre += 1
        flags[pre] = total_chorus >= 3 and (is_final or (j % 2 == 0 and j > 0))
    return flags


def _make_color_for(under_flags: Mapping[int, bool]) -> ColorForCallback:
    """§ 팔레트 색 배정 콜백 — 프로토타입 ``build()`` 안의 색 결정
    지점(61·64·69·78·84행)을 하나로 모은다.

    - Intro·Verse·Bridge → 보조색(COOL)
    - Chorus 1회차(기준 후렴) → 주색(WARM). 2회차 이후는 "Chorus 1"
      상태를 복원(``restore``)하므로 색 동작 자체가 필요 없다 —
      density.py 도 그 회차엔 이 콜백을 부르지 않는다.
    - Final Chorus → 클라이맥스색(WHITE)
    - Pre-Chorus 빌드업 중 "언더페인팅" 대상만 → under 색(AMBER)
    - Outro → 색 동작 없음(``None``) — 프로토타입도 Outro 구간 자체엔
      색을 다시 지정하지 않는다(안전 마지막 큐 전까지 이전 색 유지).
    """

    def color_for(section: str, occurrence: int) -> str | None:
        if section in ("Intro", "Verse", "Bridge"):
            return SECONDARY_COLOR
        if section == "Chorus" and occurrence == 1:
            return PRIMARY_COLOR
        if section == "Final Chorus":
            return CLIMAX_COLOR
        if section == "Pre-Chorus":
            return UNDER_COLOR if under_flags.get(occurrence, False) else None
        return None

    return color_for


def _input_palettes(
    raw_sections: Sequence[Mapping[str, object]],
) -> tuple[tuple[str, ...], ...] | None:
    """카드 t444 — 원시 구간마다 실어 온 ``palette``(실제로 내는 색 이름,
    주색 먼저)를 읽는다. 어느 구간도 색을 싣지 않았으면 ``None`` —
    "입력에 색 없음"이다. 목록/튜플이 아닌 값·빈 문자열은 버린다(색을
    추측해 채우지 않는다)."""
    palettes: list[tuple[str, ...]] = []
    for raw in raw_sections:
        value = raw.get("palette")
        colors: tuple[str, ...] = ()
        if isinstance(value, (list, tuple)):
            colors = tuple(
                dict.fromkeys(str(color).strip() for color in value if str(color).strip())
            )
        palettes.append(colors)
    return tuple(palettes) if any(palettes) else None


def _replace_op(palette: Sequence[str]) -> dict[str, object]:
    """입력 팔레트 하나를 resolver 의 ``replace`` 동작으로 — 둘째 색이
    있으면 ``secondary`` 로 함께 싣는다."""
    op: dict[str, object] = {"op": "replace", "color": palette[0]}
    if len(palette) > 1:
        op["secondary"] = palette[1]
    return op


def _inject_input_colors(
    rows: Sequence[dict[str, object]],
    sections: Sequence[SectionOccurrence],
    palettes: Sequence[tuple[str, ...]],
) -> list[dict[str, object]]:
    """카드 t444 — 구간 큐(``kind == "section"``)마다 그 구간이 입력으로
    실어 온 색을 ``replace`` 동작으로 얹는다.

    density.py 는 색 콜백 없이(``color_for=None``) 부른 상태다 — 프로토타입
    팔레트 결정(언더페인팅 포함)은 입력 색이 있을 때 쓰지 않는다. 동작
    위치는 ``restore`` 뒤다: ``restore`` 가 기준 상태의 색을 되살리므로
    그 앞에 두면 입력 색이 덮여 사라진다(후렴 2회차 이후가 "Chorus 1"
    을 복원하는 행이 그렇다). 색을 싣지 않은 구간은 건드리지 않는다 —
    앞 큐 색이 이어진다(콘솔에서 색 명령이 없는 큐와 같다)."""
    by_key = {
        (occ.section, occ.occurrence): palette
        for occ, palette in zip(sections, palettes, strict=True)
    }
    result: list[dict[str, object]] = []
    for row in rows:
        palette = by_key.get((str(row["section"]), int(row.get("occurrence", 1))))  # type: ignore[call-overload]
        if row.get("kind") != "section" or not palette:
            result.append(row)
            continue
        ops = [op for op in row["ops"] if op.get("op") != "replace"]  # type: ignore[attr-defined, union-attr]
        insert_at = max((i + 1 for i, op in enumerate(ops) if op.get("op") == "restore"), default=0)
        ops.insert(insert_at, _replace_op(palette))
        result.append(dict(row, ops=ops))
    return result


def _state_colors(state: CueState) -> tuple[str, ...]:
    """큐 상태가 띠는 색 — 주색, 그리고 있으면 보조색(중복 제거)."""
    return tuple(
        dict.fromkeys(color for color in (state.color, state.secondary) if color is not None)
    )


# --- 곡 단위 큐 테이블 --------------------------------------------------------


@dataclass(frozen=True)
class TableRow:
    """큐 하나를 게이트 판정용으로 요약한 것 — 프로토타입 ``table`` 한
    행(119~135행)의 부분집합(게이트 판정에 실제로 쓰는 필드만)."""

    q: int
    ts: float
    section: str
    occurrence: int
    kind: str  # "section" | "phrase" | "safety"
    trigger: str | None
    tracking: str
    on: tuple[str, ...]
    n_on: int
    area: float
    top: int
    color: str | None
    pos: str
    motion: int
    timing: Timing
    #: 카드 t444 — 이 큐가 띠는 색 전부(주색, 보조색 순). ``color`` 는
    #: 주색만이다(후렴 정체성 판정 등 기존 소비자용).
    colors: tuple[str, ...] = ()


@dataclass(frozen=True)
class SongBuild:
    """곡 하나를 끝까지 해석한 결과 — 13개 게이트가 공통으로 읽는다."""

    song: str
    bpm: float
    rows: tuple[Mapping[str, object], ...]
    states: tuple[CueState, ...]
    table: tuple[TableRow, ...]
    one_shots: tuple[Mapping[str, object], ...]
    pairs: tuple[ChorusPair, ...]
    mib: tuple[MibVerdict | None, ...]
    final_index: int | None
    buildup_needed: int
    #: 카드 t444 — 큐 색의 출처. ``"input"`` 이면 원시 구간이 실어 온 색,
    #: ``"constant"`` 면 프로토타입 상수 팔레트(증거 아님 — 색 게이트 n/a).
    color_source: str = "constant"
    #: 입력이 선언한 유보색(``raw_song["reserved"]``). 없으면 빈 튜플 —
    #: 유보색 검사(REQ-027)는 그때 판정하지 않는다.
    reserved: tuple[str, ...] = ()


def build_song(raw_song: Mapping[str, object]) -> SongBuild:
    """``pilot_baseline.json`` 곡 하나(``'error'`` 키 없는 것)를 안전
    큐까지 포함한 전체 시퀀스로 조립한다(REQ-075).

    파이프라인: 구간 재매핑 → :func:`server.concept.density.compile_density`
    → 안전 처음/끝 큐(:mod:`server.concept.safety`)로 감싸기 →
    :func:`server.concept.resolver.resolve_sequence` 로 해석 → 후렴 스냅샷
    (:mod:`server.concept.escalation`) + MIB(:mod:`server.concept.mib`) 계산.
    """
    bpm = float(raw_song["bpm"])
    bar = bar_seconds(bpm)
    sections = remap_baseline_sections(raw_song["sections"])  # type: ignore[arg-type]
    doc = [(s.section, s.occurrence) for s in sections]
    starts = [s.start for s in sections]
    total_chorus = sum(1 for s in sections if s.section in CHORUS_FAMILY)
    under_flags = _buildup_under_flags(doc, starts, bar=bar, total_chorus=total_chorus)
    input_palettes = _input_palettes(raw_song["sections"])  # type: ignore[arg-type]
    color_for = _make_color_for(under_flags) if input_palettes is None else None

    density_result = compile_density(sections, bpm, color_for=color_for)
    sequence_rows = [dict(row) for row in density_result.sequence]
    if input_palettes is not None:
        sequence_rows = _inject_input_colors(sequence_rows, sections, input_palettes)

    safety_start: dict[str, object] = dict(first_safety_cue(default_color=SECONDARY_COLOR))
    safety_start.update(section="Intro", occurrence=0, ts=-1.0, kind="safety", trigger=None)
    if input_palettes is not None:
        # 곡 앞 안전 큐는 컨셉 파이프라인이 만든 큐다(운영 경로에는 없다).
        # 상수 색을 두면 첫 구간과의 브리지가 상수 색으로 판정되므로, 입력
        # 중 가장 먼저 나오는 색(곡이 처음 내는 색)을 그대로 쓴다.
        first_palette = next(palette for palette in input_palettes if palette)
        safety_start["ops"] = [
            _replace_op(first_palette) if op.get("op") == "replace" else op
            for op in safety_start["ops"]  # type: ignore[union-attr]
        ]

    if sequence_rows:
        # 마지막 시퀀스 큐에 참조 이름을 하나 더 등록한다(REQ-069) — 그
        # 큐 자신의 기존 base_name(항상 None, density.py 는 이 필드를
        # 안 채운다)을 대체하는 것이지 값 자체를 바꾸지 않는다.
        sequence_rows[-1] = dict(sequence_rows[-1], base_name=_RELEASE_REF_BASE_NAME)
        last_end = sections[-1].end
    else:
        last_end = 0.0

    safety_end: dict[str, object] = dict(last_safety_cue(ref=_RELEASE_REF_BASE_NAME))
    safety_end.update(
        section="Outro", occurrence=0, ts=round(last_end + 1.0, 1), kind="safety", trigger=None
    )

    full_rows: list[dict[str, object]] = [safety_start, *sequence_rows, safety_end]
    states = resolve_sequence(full_rows)  # type: ignore[arg-type]

    table: list[TableRow] = []
    final_index: int | None = None
    for q, (row, state) in enumerate(zip(full_rows, states, strict=True)):
        on = tuple(sorted(role for role, value in state.dim.items() if value > 0))
        top = max(state.dim.values(), default=0)
        section = str(row["section"])
        kind = str(row["kind"])
        trigger = row.get("trigger")
        if kind == "section" and section in CHORUS_FAMILY:
            timing = chorus_entry_timing()
        else:
            timing = default_timing(trigger=trigger, section=section)  # type: ignore[arg-type]
        table.append(
            TableRow(
                q=q + 1,
                ts=float(row["ts"]),
                section=section,
                occurrence=int(row.get("occurrence", 1)),
                kind=kind,
                trigger=trigger,  # type: ignore[arg-type]
                tracking=str(row.get("tracking", "track")),
                on=on,
                n_on=len(on),
                area=round(len(on) / len(GROUP_ROSTER), 4) if GROUP_ROSTER else 0.0,
                top=top,
                color=state.color,
                pos=state.pos,
                motion=state.motion,
                timing=timing,
                colors=_state_colors(state),
            )
        )
        if final_index is None and kind == "section" and section == "Final Chorus":
            final_index = q

    snapshots = build_chorus_snapshots(full_rows, states, total_groups=len(GROUP_ROSTER))  # type: ignore[arg-type]
    pairs = check_pairs(snapshots)
    timestamps = [float(row["ts"]) for row in full_rows]
    mib_list = compute_mib_sequence(states, timestamps, movers=MOVER_GROUPS)

    return SongBuild(
        song=str(raw_song["song"]),
        bpm=bpm,
        rows=tuple(full_rows),
        states=tuple(states),
        table=tuple(table),
        one_shots=density_result.one_shots,
        pairs=tuple(pairs),
        mib=tuple(mib_list),
        final_index=final_index,
        buildup_needed=len(under_flags),
        color_source="input" if input_palettes is not None else "constant",
        reserved=tuple(
            str(color).strip()
            for color in raw_song.get("reserved", ()) or ()  # type: ignore[union-attr]
            if str(color).strip()
        ),
    )


# --- ConceptCue 변환(G6·G7 컬러 검사기 입력) ---------------------------------


def _concept_cues(table: Sequence[TableRow]) -> list[ConceptCue]:
    """게이트 테이블을 color_lint.py 가 기대하는 :class:`ConceptCue` 목록
    으로 바꾼다. 안전 큐(``kind=="safety"``)는 "section" 층으로
    취급한다 — 곡 시작·끝을 표시하는 앵커 큐라는 점에서 구간 큐와 같은
    성격이다(REQ-027 은 층을 가리지 않으므로 이 선택이 그 판정을
    바꾸지 않는다).

    ``colors`` 는 그 큐가 띠는 색 전부다(:attr:`TableRow.colors` — 주색,
    그리고 입력이 둘째 색을 줬으면 보조색).

    카드 t439 는 이 자리에서 "큐 하나가 두 색을 담는 자리가 모델 어디에도
    없다"는 것을 확인하고 한 색만 실었다. 카드 t444 가 그 자리를 만들었다:
    :class:`server.concept.cue_model.CueState` 의 ``secondary``, resolver 의
    ``replace`` 동작이 나르는 ``secondary``, 원시 구간의 ``palette`` 입력
    (:func:`_input_palettes`). 둘째 색은 **입력이 실어 온 것만** 들어간다 —
    곡 전역 상수(``SECONDARY_COLOR``)를 큐마다 끼워 넣지 않는다(그건 내지
    않는 색을 지어내 G6 을 통과시키는 것이다). 입력에 색이 없으면 이 목록의
    색은 상수 팔레트 값이고, 색 게이트는 그때 판정하지 않는다
    (:data:`NO_INPUT_COLOR_REASON`).
    """
    cues: list[ConceptCue] = []
    for row in table:
        layer = "section" if row.kind in ("section", "safety") else "phrase"
        cues.append(
            ConceptCue(
                section=row.section,
                occurrence=row.occurrence,
                layer=layer,  # type: ignore[arg-type]
                colors=row.colors,
                max_brightness=float(row.top),
                lit_groups=row.n_on,
                total_groups=len(GROUP_ROSTER),
                lit_group_ids=frozenset(row.on),
            )
        )
    return cues


def _lint_to_gate(result: ColorLintResult) -> GateResult:
    if result.status == "not_evaluated":
        return GateResult(None, f"{result.rule}: 평가 대상 없음(n/a)")
    return GateResult(
        result.status == "pass", f"{result.rule}: {result.status} (위반 {len(result.violations)}건)"
    )


# --- 13개 게이트 --------------------------------------------------------------


def g1_vocab_closed(build: SongBuild) -> GateResult:
    """G1 — 구간·트리거·원샷이 전부 닫힌 어휘 안인지(REQ-005~007)를
    ``vocab.validate_*`` 로 실제 검증한다(프로토타입은 상수 True 였다 —
    이 모듈은 실제 검증으로 바꾼다, 편차 기록)."""
    try:
        for row in build.rows:
            validate_section(str(row["section"]))
            trigger = row.get("trigger")
            if trigger is not None:
                validate_trigger(str(trigger))
        for shot in build.one_shots:
            validate_one_shot(str(shot["shot"]))
    except VocabError as error:
        return GateResult(False, f"어휘 위반: {error}")
    return GateResult(True, "구간·트리거·원샷 전부 문서 어휘(vocab.validate_* 실제 검증)")


def g2_chorus_identity(build: SongBuild) -> GateResult:
    """G2 — 후렴 쌍 정체성(REQ-042: 주색 동일 또는 Final Chorus). 판정이
    색 비교뿐이라 입력에 색이 없으면 n/a 다(카드 t444)."""
    if build.pairs and build.color_source != "input":
        return GateResult(None, NO_INPUT_COLOR_REASON)
    return g2_identity(build.pairs)


def g3_chorus_new_axis_within_five(build: SongBuild) -> GateResult:
    return _g3_new_axis_within_five(build.pairs)


def g4_final_new_axis_and_headroom_gate(build: SongBuild) -> GateResult:
    remaining = remaining_motion_before_final(build.states, build.final_index)
    return _g4_final_new_axis_and_headroom(build.pairs, before_final_remaining_motion=remaining)


def g5_headroom_warnings(build: SongBuild) -> GateResult:
    section_rows = [row for row in build.table if row.kind == "section"]
    intro_row = next((row for row in section_rows if row.section == "Intro"), None)
    chorus1_row = next(
        (row for row in section_rows if row.section == "Chorus" and row.occurrence == 1), None
    )
    bridge_snapshots = tuple(
        SectionCueSnapshot(
            section=row.section,
            occurrence=row.occurrence,
            is_bridge=row.section == "Bridge",
            groups_on=row.n_on,
            top_dimmer=row.top,
            effects_on=frozenset(row.on) & _EFFECT_GROUPS,
            color=row.color,
        )
        # 카드 t439 — 프로토타입(``final_integrated.py`` 162~166행 ``_prev_nb``)
        # 처럼 구간 큐만이 아니라 표의 **모든 행**(안전·구간·프레이즈)을
        # 넣는다. Bridge 직전에 무대에 켜져 있던 상태는 앞 구간의 마지막
        # 행(예: Intro 의 "보컬 시작" 프레이즈 4그룹 35%)이지 그 구간의
        # 첫 큐가 아니다 — 구간 큐만 넣으면 이 프레이즈가 빠져 Bridge 가
        # "감소 아님"으로 오판된다(scott-buckley-neon, REQ-047).
        for row in build.table
    )
    final_pair = next((pair for pair in build.pairs if pair.curr.section == "Final Chorus"), None)
    final_chorus_has_new_axis = bool(final_pair.axes) if final_pair is not None else None

    chorus1_effects_on = (
        frozenset(chorus1_row.on) & _EFFECT_GROUPS if chorus1_row is not None else frozenset()
    )
    # 카드 t444 — 네 조건 중 "Chorus 1 색이 흰색" 하나만 색에 기댄다. 입력에
    # 색이 없으면 그 조건만 빼고(``chorus1_color=None``) 나머지 세 조건은
    # 그대로 판정한다 — 색과 무관한 조건까지 n/a 로 만들 이유가 없다.
    chorus1_is_white: bool | None = None
    if build.color_source == "input" and chorus1_row is not None and chorus1_row.color:
        chorus1_is_white = " ".join(chorus1_row.color.casefold().split()) in _WHITE_NAMES
    warnings = g5_warnings(
        intro_groups_on=intro_row.n_on if intro_row is not None else None,
        total_groups=len(GROUP_ROSTER),
        chorus1_effects_on=chorus1_effects_on,
        chorus1_color=CLIMAX_COLOR if chorus1_is_white else None,
        bridge_snapshots=bridge_snapshots,
        final_chorus_has_new_axis=final_chorus_has_new_axis,
        white_color=CLIMAX_COLOR,
    )
    detail = "; ".join(warnings) if warnings else "경고 0건"
    if build.color_source != "input":
        detail += f" (Chorus 1 흰색 조건: {NO_INPUT_COLOR_REASON})"
    return GateResult(len(warnings) == 0, detail)


def g6_color_release_and_bridge(build: SongBuild) -> GateResult:
    """G6 — 유보색 조기 등장 0(REQ-027) · 인접 구간 브리지 위반 0(REQ-029).

    카드 t444 — 입력에 색이 없으면 n/a. 입력 색이 있으면 브리지는 그 색
    (주색+보조색)으로 판정한다. 유보색 검사는 입력이 유보색을 선언했을
    때만(``raw_song["reserved"]``) 판정하고, 아니면 그 절만 n/a 로 적는다
    — 상수 ``RESERVED_COLORS`` 를 입력 색에 대 보지 않는다."""
    if build.color_source != "input":
        return GateResult(None, NO_INPUT_COLOR_REASON)
    cues = _concept_cues(build.table)
    bridge = check_adjacent_bridge(cues)
    bridge_detail = f"브리지 {bridge.status}(위반 {len(bridge.violations)})"
    if not build.reserved:
        return GateResult(bridge.ok, f"유보색 n/a(입력에 유보색 없음) · {bridge_detail}")
    release = check_reserved_color_release(
        cues, reserved=build.reserved, release_section="Final Chorus", release_occurrence=1
    )
    detail = f"유보색 {release.status}(위반 {len(release.violations)}) · {bridge_detail}"
    return GateResult(release.ok and bridge.ok, detail)


def g7_chorus_primary_color(build: SongBuild) -> GateResult:
    """G7 — 후렴 주색 동일(REQ-030). 입력에 색이 없으면 n/a(카드 t444)."""
    if build.color_source != "input":
        return GateResult(None, NO_INPUT_COLOR_REASON)
    return _lint_to_gate(check_chorus_identity(_concept_cues(build.table)))


def g8_buildup_before_chorus(build: SongBuild) -> GateResult:
    have = sum(1 for row in build.table if row.trigger == _BUILDUP_TRIGGER)
    need = build.buildup_needed
    return GateResult(have >= need, f"빌드업 {have} / 필요 {need}")


def g9_tracking_block_release_leak(build: SongBuild) -> GateResult:
    block_first = bool(build.table) and build.table[0].tracking == "block"
    release_last = bool(build.table) and build.table[-1].tracking == "release"
    leak_free = verify_no_cue_only_leak(build.rows)  # type: ignore[arg-type]
    n_cue_only = sum(1 for row in build.rows if row.get("tracking") == "cue_only")
    passed = block_first and release_last and leak_free
    detail = (
        f"Block 처음 {block_first} · Release 마지막 {release_last} · "
        f"cue_only {n_cue_only} · 누출 없음 {leak_free}"
    )
    return GateResult(passed, detail)


def g10_verse_relative_reduction(build: SongBuild) -> GateResult:
    verse_tops = [
        row.top for row in build.table if row.kind == "section" and row.section == "Verse"
    ]
    if len(verse_tops) <= 2:
        return GateResult(None, f"절 밝기 {verse_tops}(2개 이하 — n/a)")
    later_tops = set(verse_tops[1:])
    return GateResult(len(later_tops) <= 1, f"절 밝기 {verse_tops}")


def g11_timing_assigned(build: SongBuild) -> GateResult:
    all_have_timing = all(row.timing is not None for row in build.table)
    chorus_entries = [
        row for row in build.table if row.kind == "section" and row.section in CHORUS_FAMILY
    ]
    all_staggered = all(row.timing.stagger for row in chorus_entries)
    snap = sum(1 for row in build.table if row.timing.kind == "snap")
    short = sum(1 for row in build.table if row.timing.kind == "short")
    long_ = sum(1 for row in build.table if row.timing.kind == "long")
    staggered = sum(1 for row in chorus_entries if row.timing.stagger)
    detail = f"snap {snap} · short {short} · long {long_} · 후렴 순차 {staggered}"
    return GateResult(all_have_timing and all_staggered, detail)


def g12_mib_no_live_moves(build: SongBuild) -> GateResult:
    dark = sum(1 for verdict in build.mib if verdict is not None and verdict.status == "dark")
    mark = sum(1 for verdict in build.mib if verdict is not None and verdict.status == "mark")
    live = [verdict for verdict in build.mib if verdict is not None and verdict.status == "live"]
    return GateResult(len(live) == 0, f"어둠 {dark} · Mark {mark} · 켜진 채 {len(live)}")


def g13_cue_density(build: SongBuild) -> GateResult:
    count = len(build.table)
    return GateResult(10 <= count <= 45, f"시퀀스 큐 {count} + 원샷 {len(build.one_shots)}")


GATE_NAMES: tuple[str, ...] = (
    "G1 어휘 닫힘",
    "G2 후렴 정체성",
    "G3 회차마다 새 축(5회차까지)",
    "G4 피날레 새 축 + 여유",
    "G5 헤드룸 경고 0",
    "G6 컬러: 유보색 조기 0 · 브리지 위반 0",
    "G7 후렴 주색 동일",
    "G8 후렴 앞 빌드업",
    "G9 트래킹: Block·Release·누출 0",
    "G10 상대 감소 겹침 없음",
    "G11 타이밍 전 큐 배정",
    "G12 MIB: 켜진 채 이동 0",
    "G13 큐 밀도 10~45",
)

_GATE_FUNCS = (
    g1_vocab_closed,
    g2_chorus_identity,
    g3_chorus_new_axis_within_five,
    g4_final_new_axis_and_headroom_gate,
    g5_headroom_warnings,
    g6_color_release_and_bridge,
    g7_chorus_primary_color,
    g8_buildup_before_chorus,
    g9_tracking_block_release_leak,
    g10_verse_relative_reduction,
    g11_timing_assigned,
    g12_mib_no_live_moves,
    g13_cue_density,
)


#: 카드 t439·t445 — 감독이 곡마다 후렴 색을 바꾸기로 고른 색 운용(Q2B).
#: 이 곡들은 G7(후렴 주색 동일)을 판정하지 않는다.
_G7_NA_COLOR_USAGES = frozenset({"per_chorus", "split_swap"})


def evaluate_song(
    raw_song: Mapping[str, object], *, color_usage: str = "modulate"
) -> dict[str, GateResult]:
    """곡 하나(``'error'`` 키 없는 것)를 조립하고 13개 게이트를 전부
    판정한다(REQ-075/076).

    ``color_usage`` — 감독이 곡마다 고르는 색 운용(Q2B). ``"per_chorus"``
    곡은 후렴 회차마다 색을 바꾸는 것이 감독의 선택이므로 G7(후렴 주색
    동일)을 판정하지 않고 n/a 로 둔다(카드 t439, 감독 결정 2026-09-23 —
    REQ-LDDESIGN-004/030 은 기본값이고 곡별 선택은 예외). 한 후렴의 분할 큐
    안에서 주·보조색을 맞바꾸는 ``"split_swap"`` 도 같은 이유로 n/a 다
    (카드 t445)."""
    build = build_song(raw_song)
    results = dict(zip(GATE_NAMES, (gate(build) for gate in _GATE_FUNCS), strict=True))
    if color_usage in _G7_NA_COLOR_USAGES:
        g7 = next(name for name in GATE_NAMES if name.startswith("G7"))
        results[g7] = GateResult(None, f"곡별 {color_usage} 선택 — 후렴 색 고정 판정 제외")
    return results
