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

    def _append(row: dict) -> None:
        rows.append(row)
        warning = layer_limit_warning(row["kind"], row["layers"])
        if warning is not None:
            warnings.append(f"{row['section']} {row['occurrence']}: {warning}")

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
            ops = _color_ops(color_for, occ.section, occ.occurrence) + [
                {"op": "expand", "roles": ["KEY"], "dimmer": 10, "pos": "home", "motion": 0}
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

        elif occ.section == "Verse":
            if occ.occurrence == 1:
                # 앞 구간(대개 후렴)이 켜 둔 무버·WASH·FOH 를 끈다 — 지우지
                # 않으면 carry 로 그대로 새어 들어와 절 밝기가 후렴 값을
                # 물려받는다(어두운 창을 만드는 목적도 겸한다, MIB 판정과
                # 같은 방향).
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
