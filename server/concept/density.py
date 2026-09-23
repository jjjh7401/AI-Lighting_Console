"""3층 큐 밀도 컴파일러 — SPEC-LDDESIGN-001 M4 (REQ-LDDESIGN-036~041, 045~046).

순수 데이터 모듈이다 — OSC 송신·콘솔 접근·네트워크를 하지 않는다(plan.md
M3 "server/concept/ 패키지 신설" 원칙, M1~M3 와 같은 방향).

입력 계약: ``sections`` 는 이미 9종 어휘(REQ-005)로 재매핑되고, 같은
섹션 이름끼리 1부터 매기는 회차(``occurrence``)가 붙은 시간순 목록이다
(재매핑 자체는 :mod:`server.concept.vocab` 의
``remap_classifier_roles`` 가 하는 일이고, 이 모듈은 그 출력을
그대로 받는다).

출력은 세 층으로 나뉜다(REQ-036):

- 구간 층(section) — 9종 어휘 각 발생마다 1큐. 마디 수로 기계 분할하지
  않는다 — 각 큐의 근거는 "그 구간이 시작했다"는 사건 하나뿐이다.
- 프레이즈 층(phrase) — 워크시트 트리거 한 줄(빌드업·눈 리셋·후렴
  뒷마디 상승)당 1큐. 시퀀스 큐 집계(G13)에 포함된다.
- 원샷 레인 — 시퀀스 큐 목록과 분리된 별도 레인(REQ-040). ``evidence``·
  ``headroom`` 계산 대상이 아니고, G13 큐 수 집계에서도 제외된다.

색은 이 모듈이 결정하지 않는다(M3 스코프) — 색이 필요한 자리마다
호출자가 넘긴 ``color_for(section, occurrence) -> str | None`` 콜백을
쓴다. 기본값(``None``)은 색 동작(op)을 아예 내지 않는다는 뜻이다.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from server.concept.cue_model import layer_limit_warning
from server.concept.vocab import validate_one_shot, validate_section

__all__ = [
    "GROUP_ROSTER",
    "MOVER_GROUPS",
    "CHORUS_FAMILY",
    "ColorForCallback",
    "SectionOccurrence",
    "DensityResult",
    "bar_seconds",
    "g13_density_warning",
    "compile_density",
]


# --- 그룹 로스터 -------------------------------------------------------------
#
# ``.moai/state/verify/f12e5c95-t429/final_integrated.py`` 9행의 그룹
# 로스터를 그대로 옮긴 것이다 — **프로토타입 로스터이지 실제 리그가
# 아니다**. 실 리그 바인딩은 이 SPEC 밖이다(REQ-017 "3밴드 속성 값
# 자체... 리그 바인딩 시점은 이 SPEC이 건드리지 않는다").

GROUP_ROSTER: tuple[str, ...] = (
    "KEY",
    "FOH",
    "BACK",
    "SIDE-L",
    "SIDE-R",
    "WASH-U",
    "WASH-D",
    "MOVER-U",
    "MOVER-D",
    "BLIND",
    "STROBE",
)
MOVER_GROUPS: tuple[str, ...] = ("MOVER-U", "MOVER-D")

# 후렴 계열 — Chorus 와 Final Chorus 를 하나의 "회차 축"으로 합쳐 센다
# (REQ-042~049 는 이 둘을 구분하지 않고 "후렴이 반복되면"으로 서술한다).
CHORUS_FAMILY: frozenset[str] = frozenset({"Chorus", "Final Chorus"})

ColorForCallback = Callable[[str, int], "str | None"]


def bar_seconds(bpm: float) -> float:
    """마디 길이(초) — 4/4 박자를 가정한다(REQ-037/038 마디 계산 단위).

    이 SPEC 은 박자 표기를 별도로 읽지 않으므로 4/4 이외 박자의 곡은
    이 함수가 낸 마디 길이가 실제와 어긋날 수 있다 — progress.md 편차
    기록.
    """
    return 4 * 60 / bpm


def g13_density_warning(sequence_count: int, *, low: int = 10, high: int = 45) -> str | None:
    """REQ-041/G13 — 시퀀스 큐(구간+프레이즈, 원샷 제외) 수가 10~45 밖이면
    경고 문장을 낸다. 조립을 막지 않는다(경고만) — ``None`` 이면 범위 안.
    """
    if low <= sequence_count <= high:
        return None
    return f"G13: 시퀀스 큐 수 {sequence_count} 가 {low}~{high} 범위 밖(경고 — 조립은 막지 않는다)"


@dataclass(frozen=True)
class SectionOccurrence:
    """컴파일러 입력 — 이미 9종 어휘로 재매핑된 구간 발생 하나.

    Attributes:
        section: 9종 어휘(REQ-005) 중 하나.
        occurrence: 이 ``section`` 이름의 몇 번째 발생인지(1-base) — 같은
            이름끼리 독립적으로 센다(Chorus 와 Final Chorus 는 이름이
            달라 각자 1부터 시작한다).
        start: 시작 시각(초).
        end: 종료 시각(초).
    """

    section: str
    occurrence: int
    start: float
    end: float

    def __post_init__(self) -> None:
        validate_section(self.section)
        if self.occurrence < 1:
            raise ValueError("occurrence: 1 이상이어야 한다")
        if self.end <= self.start:
            raise ValueError("end: start 보다 커야 한다")


@dataclass(frozen=True)
class DensityResult:
    """컴파일 결과 — 세 층(구간/프레이즈/원샷) + 린트 경고.

    ``sequence`` 의 각 행은 :func:`server.concept.resolver.resolve_sequence`
    가 바로 소비할 수 있는 매핑이다(``section``/``occurrence``/``ops``/
    ``tracking``/``base_name`` 키) — 추가로 ``ts``/``kind``
    (``"section"`` 또는 ``"phrase"``)/``trigger``/``layers`` 를 갖는다.
    """

    sequence: tuple[Mapping[str, object], ...]
    one_shots: tuple[Mapping[str, object], ...]
    warnings: tuple[str, ...]


def _color_ops(color_for: ColorForCallback | None, section: str, occurrence: int) -> list[dict]:
    """REQ-017/030 — 색 결정은 M3 스코프다. 콜백이 없거나 ``None`` 을
    내면 색 동작을 아예 내지 않는다.
    """
    if color_for is None:
        return []
    color = color_for(section, occurrence)
    if color is None:
        return []
    return [{"op": "replace", "color": color}]


def distribute_motion_steps(chorus_total: int, *, max_motion: int = 3) -> tuple[int, ...]:
    """REQ-044 — 모션 단계(0~max_motion)를 후렴 총수에 비례해 분배한다.

    마지막 회차 이전에 최대치에 도달하지 않도록, 마지막 회차만 항상
    ``max_motion`` 이고 그 앞은 선형 분배로 ``max_motion - 1`` 을 넘지
    않는다(4곡에서 피날레 전 남은 모션 단계 0 을 실측한 v2 결함을
    다시 만들지 않는다 — `chorus-escalation-audit-20260921.md` 개선사항
    3).
    """
    if chorus_total <= 0:
        return ()
    if chorus_total == 1:
        return (max_motion,)
    mid_span = max(1, chorus_total - 2)
    steps: list[int] = []
    for k in range(1, chorus_total + 1):
        if k == chorus_total:
            steps.append(max_motion)
        elif k == 1:
            steps.append(1)
        else:
            steps.append(min(max_motion - 1, 1 + (k - 2) * (max_motion - 1) // mid_span))
    return tuple(steps)


def _phrase_slot_count(k: int, bars: float) -> int:
    """후렴 뒷마디 상승 프레이즈 큐 개수 — REQ-045 "4회차 이후 후렴당
    최대 1개"를 넘지 않는다. 구간 길이(``bars``)가 짧으면 그보다도
    적다(2마디당 1개 자리로 본다).
    """
    cap = 1 if k >= 4 else min(3, k)
    by_bars = int(bars // 2)
    return max(0, min(cap, by_bars))


def _chorus_position(k: int, prev_is_chorus_family: bool) -> str | None:
    """REQ-043 방향 축 — 회차마다 포지션을 바꾼다. 단 무버가 이미 켜진
    채 연속 후렴으로 들어오면(어두운 창이 없으면) 포지션을 바꾸지 않는다
    (``None`` — 이전 값 유지, 프로토타입의 "연속 후렴이면 어두운 창
    없음" 규칙 그대로)."""
    if k >= 4 and prev_is_chorus_family:
        return None
    if k == 2:
        return "side"
    return "front"


def _next_chorus_position(
    sections: Sequence[SectionOccurrence], from_index: int, k_by_index: Mapping[int, int]
) -> str | None:
    """카드 t439 §④b M5 판단 2 — ``from_index`` 뒤로 처음 나오는 후렴이
    실제로 쓸 포지션을 미리 본다(REQ-064 "다음 후렴을 위해"). ``None``
    이면 그 후렴이 새 포지션을 요구하지 않거나(``_chorus_position`` 이
    이미 ``None`` — k>=4·직전이 후렴, REQ-043 방향 축 예외), 뒤에 후렴
    자체가 없다는 뜻이다 — 두 경우 모두 "포지션을 옮길 이유가 없다"로
    같은 값(``None``)으로 합쳐진다(:func:`_movers_need_repositioning`
    가 소비한다)."""
    for idx in range(from_index + 1, len(sections)):
        if sections[idx].section in CHORUS_FAMILY:
            k = k_by_index[idx]
            prev_is_chorus = idx > 0 and sections[idx - 1].section in CHORUS_FAMILY
            return _chorus_position(k, prev_is_chorus)
    return None


def _movers_need_repositioning(
    sections: Sequence[SectionOccurrence],
    from_index: int,
    k_by_index: Mapping[int, int],
    current_pos: str,
) -> bool:
    """REQ-064 — "무버가... **다음 후렴을 위해 포지션을 바꿔야 하면**"
    만 무버를 소등한다(원래 배차서 5·카드 t439 §④b M5 판단 2). 뒤에
    후렴이 없거나, 그 후렴이 새 포지션을 요구하지 않거나, 요구하는
    포지션이 지금 위치와 같으면 전부 False — "옮길 이유가 없다"는 같은
    결론이다. 카드 t438 이 만든 :func:`server.concept.mib.
    movers_off_ops` (``section in MOVER_HOLD_SECTIONS`` 조건만 봄)는
    이 조건을 아직 갖지 않아, 이 함수가 그 조건을 조립기(assembler,
    이 모듈)에 직접 넣는다 — 두 번째 판정 함수를 만드는 것이 아니라
    ``mib.movers_off_ops`` 가 아직 못 갖춘 조건을 그 함수를 부르지
    않는 이 자리에서 대신 계산하는 것이다."""
    next_pos = _next_chorus_position(sections, from_index, k_by_index)
    return next_pos is not None and next_pos != current_pos


def compile_density(
    sections: Sequence[SectionOccurrence],
    bpm: float,
    *,
    color_for: ColorForCallback | None = None,
) -> DensityResult:
    """3층 큐 밀도를 컴파일한다(REQ-036~041, 045~046).

    Args:
        sections: 시간순 구간 발생 목록(입력 계약은 모듈 docstring 참고).
        bpm: 곡 BPM — 마디 길이 계산에 쓴다(:func:`bar_seconds`).
        color_for: ``(section, occurrence) -> color | None`` — 색이 필요한
            자리(구간 큐 색 지정, Final Chorus 클라이맥스 색 전환,
            빌드업 언더페인팅)마다 호출한다. 기본 ``None`` 은 색 동작을
            내지 않는다.

    Returns:
        :class:`DensityResult` — ``sequence`` 는 ``ts`` 오름차순.
    """
    bar = bar_seconds(bpm)
    warnings: list[str] = []
    rows: list[dict] = []
    # 카드 t439 §④b M5 판단 2 — 지금까지 조립된 행이 마지막으로 정한
    # 포지션. 안전 시작 큐(``safety.first_safety_cue``)의 ``pos:
    # "home"`` 과 같은 초기값이다(이 모듈은 안전 큐를 직접 만들지 않지만,
    # ``gates.build_song`` 이 이 시퀀스 앞에 항상 그 안전 큐를 붙인다).
    current_pos = "home"

    def _append(row: dict) -> None:
        nonlocal current_pos
        rows.append(row)
        warning = layer_limit_warning(row["kind"], row["layers"])
        if warning is not None:
            warnings.append(f"{row['section']} {row['occurrence']}: {warning}")
        for op in row["ops"]:
            if "pos" in op:
                current_pos = op["pos"]

    chorus_indices = [i for i, s in enumerate(sections) if s.section in CHORUS_FAMILY]
    chorus_total = len(chorus_indices)
    motion_steps = distribute_motion_steps(chorus_total)
    k_by_index = {idx: k for k, idx in enumerate(chorus_indices, start=1)}

    for i, occ in enumerate(sections):
        ts = occ.start
        bars = (occ.end - occ.start) / bar
        prev = sections[i - 1] if i > 0 else None
        prev_is_chorus_family = prev is not None and prev.section in CHORUS_FAMILY

        if occ.section == "Intro":
            # 프로토타입(``final_integrated.py`` 61~62행)을 그대로 포팅한다
            # (카드 t439 G5 수정 — 카드 t437 의 축소 포팅이 KEY 10% 하나만
            # 남기고 아래 BACK 25% 확장과 "보컬 시작" 예고 프레이즈를
            # 빠뜨렸다):
            #
            #   if d=='Intro':
            #       add(ts,d,occ,None,[{'op':'replace','color':COOL},
            #           {'op':'expand','roles':['BACK'],'dimmer':25,
            #           'pos':'back','motion':0}],'구간',R,'Track',
            #           ('long',2.0),None,src,'보조색 고립',
            #           base_name='Intro')
            #       if bars>=4: add(round(en[i]-4*BAR,1),d,occ,'보컬 시작',
            #           [{'op':'add','roles':['BACK','SIDE-L','SIDE-R'],
            #           'dimmer':35}],'프레이즈',R,'Track',('short',1.0),
            #           None,'rule','보컬 4마디 전 예고')
            #
            # ``tracking`` 은 프로토타입의 ``'Track'`` 을 그대로 옮기지
            # 않는다 — REQ-056(``tracking.py``)이 phrase 층 기본값을
            # ``cue_only`` 로 못박은 이유가 이 파일의 다른 phrase 큐
            # (빌드업·눈 리셋)에 이미 적용돼 있고, 이 새 phrase 만 다른
            # 규칙을 쓸 이유가 없다.
            ops = _color_ops(color_for, occ.section, occ.occurrence) + [
                {"op": "expand", "roles": ["KEY"], "dimmer": 10, "pos": "home", "motion": 0},
                {"op": "expand", "roles": ["BACK"], "dimmer": 25, "pos": "back", "motion": 0},
            ]
            _append(
                dict(
                    ts=ts,
                    section=occ.section,
                    occurrence=occ.occurrence,
                    kind="section",
                    trigger=None,
                    layers=frozenset({"visibility", "environment"}),
                    ops=ops,
                    tracking="track",
                    base_name=None,
                )
            )
            if bars >= 4:
                _append(
                    dict(
                        ts=round(occ.end - 4 * bar, 1),
                        section=occ.section,
                        occurrence=occ.occurrence,
                        kind="phrase",
                        trigger="보컬 시작",
                        layers=frozenset({"visibility", "environment"}),
                        ops=[
                            {
                                "op": "add",
                                "roles": ["BACK", "SIDE-L", "SIDE-R"],
                                "dimmer": 35,
                            }
                        ],
                        tracking="cue_only",
                        base_name=None,
                    )
                )

        elif occ.section == "Verse":
            if occ.occurrence == 1:
                # 앞 구간(대개 후렴)이 켜 둔 무버·WASH·FOH 를 끈다 — 지우지
                # 않으면 carry 로 그대로 새어 들어와 절 밝기가 후렴 값을
                # 물려받는다(어두운 창을 만드는 목적도 겸한다, MIB 판정과
                # 같은 방향).
                #
                # 카드 t439 §④b M5 판단 2 — REQ-064 문면대로 "다음 후렴을
                # 위해 포지션을 바꿔야 할 때만" 무버를 소등하도록
                # 조건화해 봤으나(`_movers_need_repositioning`, 이 파일
                # 아래에 남겨 둔 구현), TOO_COOL_RAW 픽스처에서 무조건
                # 회귀했다 — AC-LDDESIGN-010 이 고정한
                # `test_verse_first_occurrence_clears_prior_mover_and_wash_
                # state`(밝기 45 기대)가 100 으로 깨진다. 다음 후렴이 지금과
                # 같은 포지션이면(이 픽스처가 정확히 그 경우) 무버가 이전
                # 후렴의 100% 밝기를 그대로 들고 절로 들어온다 — REQ-064는
                # "포지션을 바꿀 필요가 없다"만 말하지 "밝기도 그대로
                # 둔다"를 말하지 않는데, 이 둘을 하나의 소등/비소등
                # 이분법으로 묶으면 후자가 딸려 온다. 밝기를 절 수준(45%)
                # 으로는 낮추되 위치는 안 바꾸는 제3의 동작이 필요할 수
                # 있는데, 그 값은 이 SPEC 문면에 없어 지어내지 않는다 —
                # 감독 확인 필요(리드에게 보고, 카드 지시 "matrix 변하면
                # 재고정하지 말고 보고"와 같은 원칙을 이 회귀에도 적용).
                # 그래서 무조건 소등 동작은 그대로 두고, 조건 계산 자체만
                # `_movers_need_repositioning`(아래)로 분리해 시험으로
                # 고정해 둔다 — 배선 여부는 이 판단이 난 뒤에 결정한다.
                ops = _color_ops(color_for, occ.section, occ.occurrence) + [
                    {"op": "remove", "roles": [*MOVER_GROUPS, "WASH-U", "WASH-D", "FOH"]},
                    {
                        "op": "expand",
                        "roles": ["BACK", "SIDE-L", "SIDE-R", "KEY"],
                        "dimmer": 45,
                        "motion": 0,
                    },
                ]
            else:
                ops = [
                    {"op": "restore", "ref": "Verse 1"},
                    {"op": "reduce", "factor": 0.85, "ref": "Verse 1"},
                    *_color_ops(color_for, occ.section, occ.occurrence),
                ]
            _append(
                dict(
                    ts=ts,
                    section=occ.section,
                    occurrence=occ.occurrence,
                    kind="section",
                    trigger=None,
                    layers=frozenset({"visibility", "architecture"}),
                    ops=ops,
                    tracking="track",
                    base_name=None,
                )
            )

        elif occ.section in CHORUS_FAMILY:
            k = k_by_index[i]
            motion = motion_steps[k - 1]
            if k == 1:
                ops = _color_ops(color_for, occ.section, occ.occurrence) + [
                    {
                        "op": "expand",
                        "roles": ["KEY", "FOH", "BACK", "SIDE-L", "SIDE-R"],
                        "dimmer": 75,
                        "pos": "back",
                        "motion": motion,
                    }
                ]
                dimmer = 75
            elif occ.section == "Final Chorus":
                fin_pos = None if (prev_is_chorus_family and chorus_total >= 4) else "audience"
                expand_op: dict = {
                    "op": "expand",
                    "roles": ["WASH-U", "WASH-D", "MOVER-U", "MOVER-D"],
                    "dimmer": 100,
                    "motion": motion,
                }
                if fin_pos is not None:
                    expand_op["pos"] = fin_pos
                ops = [
                    {"op": "restore", "ref": "Chorus 1"},
                    *_color_ops(color_for, occ.section, occ.occurrence),
                    expand_op,
                    {"op": "release", "role": "BLIND", "dimmer": 90},
                ]
                dimmer = 100
            else:
                pos = _chorus_position(k, prev_is_chorus_family)
                fam = ["WASH-U", "WASH-D"] if k == 2 else ["WASH-U", "WASH-D", "MOVER-U", "MOVER-D"]
                dimmer = min(100, 60 + 8 * k)
                expand_op = {"op": "expand", "roles": fam, "dimmer": dimmer, "motion": motion}
                if pos is not None:
                    expand_op["pos"] = pos
                ops = [{"op": "restore", "ref": "Chorus 1"}, expand_op]

            _append(
                dict(
                    ts=ts,
                    section=occ.section,
                    occurrence=occ.occurrence,
                    kind="section",
                    trigger=None,
                    layers=frozenset({"visibility", "environment", "motion"}),
                    ops=ops,
                    tracking="track",
                    base_name=None,
                )
            )

            n_phr = _phrase_slot_count(k, bars)
            for p in range(n_phr):
                p_ts = round(ts + 2 * bar * (p + 1), 1)
                if p_ts >= occ.end:
                    break
                _append(
                    dict(
                        ts=p_ts,
                        section=occ.section,
                        occurrence=occ.occurrence,
                        kind="phrase",
                        trigger="악기 추가",
                        layers=frozenset({"environment"}),
                        ops=[
                            {
                                "op": "add",
                                "roles": ["WASH-U", "WASH-D"],
                                "dimmer": min(100, dimmer + 5 * (p + 1)),
                            }
                        ],
                        tracking="cue_only",
                        base_name=None,
                    )
                )

        elif occ.section == "Bridge":
            # REQ-047 — KEY·BACK 을 제외한 그룹은 무조건 끈다.
            #
            # 카드 t439 §④b M5 판단 2 — Verse 1회차와 같은 이유로 무버만
            # REQ-064 조건(`_movers_need_repositioning`)으로 바꿔 봤으나
            # TOO_COOL_RAW 의 두 Bridge 발생 중 최소 하나가 같은 회귀를
            # 낸다(`test_bridge_removes_everything_but_key_and_back`/
            # `test_bridge_cue_ops_shape`, 위 Verse 주석과 같은 원인·같은
            # 미결정 — 감독 확인 필요). 배선하지 않는다.
            ops = _color_ops(color_for, occ.section, occ.occurrence) + [
                {
                    "op": "remove",
                    "roles": [g for g in GROUP_ROSTER if g not in ("KEY", "BACK")],
                },
                {"op": "expand", "roles": ["KEY", "BACK"], "dimmer": 30, "motion": 0},
            ]
            _append(
                dict(
                    ts=ts,
                    section=occ.section,
                    occurrence=occ.occurrence,
                    kind="section",
                    trigger=None,
                    layers=frozenset({"visibility"}),
                    ops=ops,
                    tracking="track",
                    base_name=None,
                )
            )

        elif occ.section == "Outro":
            ops = _color_ops(color_for, occ.section, occ.occurrence) + [
                {
                    "op": "remove",
                    "roles": [g for g in GROUP_ROSTER if g not in ("KEY", "BACK")],
                },
                {"op": "expand", "roles": ["KEY", "BACK"], "dimmer": 20, "motion": 0},
            ]
            _append(
                dict(
                    ts=ts,
                    section=occ.section,
                    occurrence=occ.occurrence,
                    kind="section",
                    trigger=None,
                    layers=frozenset({"visibility"}),
                    ops=ops,
                    tracking="track",
                    base_name=None,
                )
            )

        else:
            # Pre-Chorus(판정기가 직접 낸 경우)·Post-Chorus·Rap/Solo/Dance
            # Break — 감독 지정이 필요한 자리라 상태를 유지만 한다
            # (프로토타입 else 분기와 같은 방향, "감독 지정 필요").
            _append(
                dict(
                    ts=ts,
                    section=occ.section,
                    occurrence=occ.occurrence,
                    kind="section",
                    trigger=None,
                    layers=frozenset({"visibility"}),
                    ops=[{"op": "retain"}],
                    tracking="track",
                    base_name=None,
                )
            )

    # --- REQ-037 빌드업 프레이즈 큐 ------------------------------------------
    buildup_counter = 0
    for i in chorus_indices:
        if i == 0:
            continue
        prev = sections[i - 1]
        if prev.section in CHORUS_FAMILY:
            continue
        is_final = sections[i].section == "Final Chorus"
        threshold_bars = 3 if is_final else 5
        prev_bars = (prev.end - prev.start) / bar
        if prev_bars < threshold_bars:
            continue
        nb = 2 if is_final else 4
        buildup_counter += 1
        b_ts = round(sections[i].start - nb * bar, 1)
        _append(
            dict(
                ts=b_ts,
                section="Pre-Chorus",
                occurrence=buildup_counter,
                kind="phrase",
                trigger="빌드업 시작",
                layers=frozenset({"environment", "visibility"}),
                ops=[
                    {
                        "op": "add",
                        "roles": ["BACK", "SIDE-L", "SIDE-R", "KEY", "FOH"],
                        "dimmer": 60,
                    },
                    *_color_ops(color_for, "Pre-Chorus", buildup_counter),
                ],
                tracking="cue_only",
                base_name=None,
            )
        )

    # --- REQ-038 눈 리셋 프레이즈 큐 -----------------------------------------
    outro_index = next((i for i, s in enumerate(sections) if s.section == "Outro"), None)
    if outro_index is not None and outro_index > 0:
        final = sections[outro_index - 1]
        if final.section == "Final Chorus":
            gap_bars = (sections[outro_index].start - final.start) / bar
            if gap_bars >= 3:
                _append(
                    dict(
                        ts=round(sections[outro_index].start - bar, 1),
                        section="Final Chorus",
                        occurrence=final.occurrence,
                        kind="phrase",
                        trigger="드롭 직전의 정적",
                        layers=frozenset({"visibility"}),
                        ops=[{"op": "reduce", "factor": 0.3}],
                        tracking="cue_only",
                        base_name=None,
                    )
                )

    rows.sort(key=lambda r: r["ts"])

    # --- 원샷 레인(REQ-040) — 시퀀스·evidence·headroom·G13 대상 밖 ----------
    one_shots: list[dict] = []
    for i in chorus_indices:
        occ = sections[i]
        shot = "Blinder hit" if occ.section == "Final Chorus" else "White hit"
        target = "BLIND" if shot == "Blinder hit" else "KEY+FOH"
        validate_one_shot(shot)
        one_shots.append(
            dict(ts=occ.start, shot=shot, target=target, at=f"{occ.section} {occ.occurrence} 첫 박")
        )
    one_shots.sort(key=lambda r: r["ts"])

    g13 = g13_density_warning(len(rows))
    if g13 is not None:
        warnings.append(g13)

    return DensityResult(sequence=tuple(rows), one_shots=tuple(one_shots), warnings=tuple(warnings))
