"""시간 해석 — beat↔ms · cue 경계 · delta 사슬 (SPEC-LDCOMPILE-001 C2, REQ-LDPLUGIN-009).

계약 `LD-TIME-001`~`003` 과 `LD-MIB-001` 의 음수 ms 부분을 판정한다. 전부 순수 함수이며
콘솔·OSC·예술 producer 를 만지지 않는다.

이 모듈이 조심하는 것 셋:

1. **기본 BPM 을 넣지 않는다.** `LD-TIME-002` 가 *"tempo 불명인데 120 BPM을 가정하지
   않는다"* 고 못박았다. tempo 를 모르면 숫자를 답하지 않고 `TempoUnknownError` 를 던진다 —
   `None` 을 답하면 그 `None` 은 언젠가 `or 0` 을 만나고 그 큐는 첫 박에 발사된다
   (`server/lxseq/cue_time.py` 가 같은 이유로 다섯 갈래를 유지한다).
2. **반올림에 내장 `round()` 를 쓰지 않는다.** 파이썬은 은행가 반올림이라 `round(2.5)==2`
   인데 계약 §7 은 *"정확한 .5는 +방향"* 이다. 부동소수 두 값이 같은 ms 로 접히면
   `rounding_conflicts` 가 거부한다 — 계약 §7 *"rounding으로 충돌이 생기면 거부한다"*.
3. **음수 ms 는 Director 경로에서 거부한다.** 감독 판정(2026-09-15) 은 **경로 분리**다.
   기존 `server/lxseq/cue_time.py` 의 `CUE_TIME_PREROLL` 은 그대로 두고(참조 8건이 전부
   그 파일 안, 외부 소비자 0건 — 실측), 이 경로는 `LD-MIB-001` 대로 막으면서 사람에게
   *"원점을 확장한 새 audio/context"* 를 요청한다. 스키마의 `at_ms`/`delay_ms`/`fade_ms` 가
   이미 `integer, minimum: 0` 이므로 이 진단은 스키마가 집행하는 것을 말로 옮기는 것이다.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field
from typing import Any

from server.director.validate.diagnostics import (
    STATUS_ACCEPTED,
    STATUS_CONFLICT,
    STATUS_UNSUPPORTED,
    Diagnostic,
    present,
)

#: 이 모듈이 붙이는 stage. C1 파이프라인의 2단이다.
STAGE = "time_reference"

#: 전체 plan 을 가리키는 pointer (계약 §6.3).
ROOT_POINTER = ""

#: 계약 §6.1 playback enum. 이 둘 밖은 거부한다 — timecode·자동 GO 포함.
PLAYBACK_MODES: tuple[str, ...] = ("manual_go", "trig_time")

#: 계약 §6.1 `origin` 은 const 다. 숨은 offset 은 이 필드를 바꿔 들어온다.
REQUIRED_ORIGIN = "audio_start"

#: 계약 §6.1 beat_map status enum 중 beat 기반 FX 를 허용하는 것.
BEAT_STATUS_CONFIRMED = "confirmed"
BEAT_STATUS_SYNTHETIC = "synthetic"

#: 축 이름 — 계약 §7 `Timing` 이 붙는 자리.
TIMING_AXES: tuple[str, ...] = ("intensity", "color", "pan", "tilt", "beam", "fx")

_NEW_ORIGIN_GUIDANCE = (
    "음수 ms 는 Director 경로에서 표현하지 않습니다. LD-MIB-001 은 이 버전에 음수 clock/"
    "pre-roll 필드가 없다고 규정하므로, 준비 동작이 필요하면 원점을 확장한 새 audio/context "
    "를 제출하거나 사람이 사전 준비한 verified baseline 을 쓰십시오. authored timing 은 "
    "바꾸지 않습니다."
)


class TempoUnknownError(ValueError):
    """그 시각·그 박의 tempo 를 모른다.

    숫자를 지어내는 대신 던진다. 호출자는 이것을 진단으로 옮길 책임이 있다.
    """


def round_half_up(value: float) -> int:
    """계약 §7 — 가장 가까운 integer ms, **정확한 .5 는 +방향**.

    내장 `round()` 는 은행가 반올림(`round(2.5)==2`)이라 계약을 위반한다. `floor(v+0.5)` 는
    `.5` 를 항상 +방향으로 보낸다 — `-0.5 → 0`, `-1.5 → -1` 도 같은 규칙이다.
    """
    return math.floor(value + 0.5)


def _segments(beat_map: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(beat_map.get("segments") or [], key=lambda s: s["start_ms"])


def _segment_end_beat(segment: dict[str, Any]) -> float:
    span_ms = segment["end_ms"] - segment["start_ms"]
    return segment["start_beat"] + span_ms * segment["bpm"] / 60000


def beat_at(beat_map: dict[str, Any], t_ms: float) -> float:
    """`beat(t)=start_beat+(t-start_ms)*bpm/60000` (계약 `LD-TIME-002`).

    segment 는 `[start,end)` 다 — 경계 ms 는 **뒤** segment 가 답한다. 인접 segment 의
    `start_beat` 가 앞 segment 의 끝 박과 같으면 값이 연속한다.

    Raises:
        TempoUnknownError: 어떤 segment 도 `t_ms` 를 덮지 않을 때.
    """
    for segment in _segments(beat_map):
        if segment["start_ms"] <= t_ms < segment["end_ms"]:
            offset = t_ms - segment["start_ms"]
            return segment["start_beat"] + offset * segment["bpm"] / 60000
    raise TempoUnknownError(
        f"{t_ms}ms 를 덮는 tempo segment 가 없습니다. 기본 BPM 을 가정하지 않습니다."
    )


def ms_at_beat(beat_map: dict[str, Any], beat: float) -> int:
    """박 → ms. 최종 경계는 `round_half_up` 이다 (계약 §7 마지막 문장).

    Raises:
        TempoUnknownError: 어떤 segment 의 박 범위도 `beat` 를 덮지 않을 때.
    """
    for segment in _segments(beat_map):
        if segment["start_beat"] <= beat < _segment_end_beat(segment):
            offset_beats = beat - segment["start_beat"]
            return round_half_up(segment["start_ms"] + offset_beats * 60000 / segment["bpm"])
    raise TempoUnknownError(
        f"{beat} 박을 덮는 tempo segment 가 없습니다. 기본 BPM 을 가정하지 않습니다."
    )


@dataclass(frozen=True)
class Bundle:
    """같은 ms 의 cue 들을 묶은 **단일 semantic cue** (계약 `LD-TIME-001`).

    배열 순서는 deterministic emit order 로만 쓴다 — 뒤 action 이 앞 conflict 를 덮는다는
    뜻이 아니므로 순서를 보존해서 넘긴다.
    """

    at_ms: int
    cue_indices: list[int] = field(default_factory=list)
    action_pointers: list[str] = field(default_factory=list)


def bundle_cues(plan: dict[str, Any]) -> list[Bundle]:
    """cue 를 `at_ms` 로 묶고 시각 순으로 낸다. 입력 배열 순서에 의존하지 않는다."""
    grouped: dict[int, Bundle] = {}
    for cue_index, cue in enumerate(plan.get("cues") or []):
        if not isinstance(cue, dict):
            continue
        at_ms = cue.get("at_ms")
        if not isinstance(at_ms, int):
            continue
        bundle = grouped.setdefault(at_ms, Bundle(at_ms=at_ms))
        bundle.cue_indices.append(cue_index)
        for action_index in range(len(cue.get("actions") or [])):
            bundle.action_pointers.append(f"/cues/{cue_index}/actions/{action_index}")
    return [grouped[at_ms] for at_ms in sorted(grouped)]


@dataclass(frozen=True, slots=True)
class TrigBundle:
    """한 bundle 의 발사 방식 (계약 `LD-TIME-003`).

    `relative_ms` 는 **직전 최종 bundle 과의 차이**다. 절대 `at_ms` 를 그대로 `TrigTime` 으로
    넘기는 것을 계약이 금지했으므로 이 값이 그 금지를 구현한다.
    """

    at_ms: int
    trig: str
    relative_ms: int


def trig_time_bundles(plan: dict[str, Any]) -> list[TrigBundle]:
    """playback mode 에 따라 bundle 별 발사 방식을 계산한다.

    `manual_go` 는 모든 bundle 이 수동이며 `at_ms` 는 음악 참조일 뿐이다. `trig_time` 은
    첫 bundle 만 `manual_go/0` 이고(사람이 audio t0 에 GO), 이후는 직전 bundle 과의 delta 다.
    준비 cue 도 자기 bundle 을 가지므로 사슬에 그대로 포함된다 — 건너뛰면 뒤가 전부 밀린다.

    Raises:
        ValueError: 계약 밖 mode. 호출자(`check_timing`)가 먼저 걸러야 한다.
    """
    mode = (plan.get("playback") or {}).get("mode")
    if mode not in PLAYBACK_MODES:
        raise ValueError(f"계약 §6.1 밖의 playback mode 입니다: {mode!r}")

    bundles = bundle_cues(plan)
    if mode == "manual_go":
        return [TrigBundle(at_ms=b.at_ms, trig="manual_go", relative_ms=0) for b in bundles]

    result: list[TrigBundle] = []
    previous_at_ms: int | None = None
    for bundle in bundles:
        if previous_at_ms is None:
            result.append(TrigBundle(at_ms=bundle.at_ms, trig="manual_go", relative_ms=0))
        else:
            result.append(
                TrigBundle(
                    at_ms=bundle.at_ms,
                    trig="trig_time",
                    relative_ms=bundle.at_ms - previous_at_ms,
                )
            )
        previous_at_ms = bundle.at_ms
    return result


def rounding_conflicts(
    beat_map: dict[str, Any],
    requests: list[tuple[str, str, float]],
) -> list[Diagnostic]:
    """서로 다른 박이 같은 ms 로 접히면 거부한다 (계약 §7).

    Args:
        beat_map: tempo 지도.
        requests: `(group_id, axis, beat)` 목록. 축이 판정 단위다 — 같은 ms 라도 축이
            다르면 충돌이 아니다. 여기서 넓게 잡으면 정상 계획이 막힌다.
    """
    collapsed: dict[tuple[str, str, int], set[float]] = {}
    for group_id, axis, beat in requests:
        try:
            at_ms = ms_at_beat(beat_map, beat)
        except TempoUnknownError:
            # tempo 를 모르는 것은 반올림 충돌이 아니라 별개 결함이다. 여기서 삼키지 않고
            # 판정을 `check_timing` 의 tempo 단계에 남긴다.
            continue
        collapsed.setdefault((group_id, axis, at_ms), set()).add(beat)

    diagnostics: list[Diagnostic] = []
    for (group_id, axis, at_ms), beats in sorted(collapsed.items()):
        if len(beats) < 2:
            continue
        diagnostics.append(
            Diagnostic(
                rule_id="LD-TIME-002",
                pointer=ROOT_POINTER,
                status=STATUS_CONFLICT,
                blocking=True,
                reason=(
                    f"group {group_id} 의 {axis} 축에서 서로 다른 박 "
                    f"{sorted(beats)} 이 반올림 후 같은 {at_ms}ms 가 됩니다. 계약 §7 은 "
                    "rounding 으로 충돌이 생기면 거부하라고 규정합니다 — 자동으로 "
                    "quantize·이동하지 않습니다."
                ),
                stage=STAGE,
                after=present(at_ms),
            )
        )
    return diagnostics


def _sections_by_id(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {s["section_id"]: s for s in context.get("music_sections") or [] if "section_id" in s}


def _check_playback(plan: dict[str, Any]) -> list[Diagnostic]:
    """`LD-TIME-003` — mode 와 origin. timecode·자동 GO·숨은 offset 을 거부한다."""
    playback = plan.get("playback") or {}
    mode = playback.get("mode")
    origin = playback.get("origin")
    diagnostics: list[Diagnostic] = []

    if mode not in PLAYBACK_MODES:
        diagnostics.append(
            Diagnostic(
                rule_id="LD-TIME-003",
                pointer="/playback/mode",
                status=STATUS_UNSUPPORTED,
                blocking=True,
                reason=(
                    f"playback mode {mode!r} 를 지원하지 않습니다. 계약은 manual_go 와 "
                    "trig_time 둘만 허용하며 timecode mode·자동 GO 는 거부합니다."
                ),
                stage=STAGE,
                before=present(str(mode)),
            )
        )
    if origin is not None and origin != REQUIRED_ORIGIN:
        diagnostics.append(
            Diagnostic(
                rule_id="LD-TIME-003",
                pointer="/playback/origin",
                status=STATUS_UNSUPPORTED,
                blocking=True,
                reason=(
                    f"origin {origin!r} 를 지원하지 않습니다. 원점은 업로드 audio 의 첫 "
                    "sample=0ms 로 고정이며 숨은 offset 을 허용하지 않습니다."
                ),
                stage=STAGE,
                before=present(str(origin)),
            )
        )
    return diagnostics


def _check_section_coverage(context: dict[str, Any]) -> list[Diagnostic]:
    """`LD-TIME-001` — context sections 가 `[0,duration)` 를 겹침·공백 없이 분할한다."""
    duration_ms = (context.get("audio") or {}).get("duration_ms")
    sections = sorted(
        (s for s in context.get("music_sections") or []),
        key=lambda s: s["start_ms"],
    )
    if not sections or not isinstance(duration_ms, int):
        return [
            Diagnostic(
                rule_id="LD-TIME-001",
                pointer=ROOT_POINTER,
                status=STATUS_UNSUPPORTED,
                blocking=True,
                reason=(
                    "전곡 분할을 판정할 수 없습니다 — music_sections 또는 audio.duration_ms "
                    "가 없습니다. 판정 불능을 통과로 바꾸지 않습니다."
                ),
                stage=STAGE,
            )
        ]

    diagnostics: list[Diagnostic] = []
    if sections[0]["start_ms"] != 0:
        diagnostics.append(
            Diagnostic(
                rule_id="LD-TIME-001",
                pointer=ROOT_POINTER,
                status=STATUS_UNSUPPORTED,
                blocking=True,
                reason=(
                    f"첫 section 이 {sections[0]['start_ms']}ms 에서 시작합니다. 원점은 "
                    "업로드 audio 의 첫 sample=0ms 이며 중간 trim/offset 이 없습니다."
                ),
                stage=STAGE,
                before=present(sections[0]["start_ms"]),
            )
        )
    for previous, following in itertools.pairwise(sections):
        if previous["end_ms"] == following["start_ms"]:
            continue
        overlap = following["start_ms"] < previous["end_ms"]
        diagnostics.append(
            Diagnostic(
                rule_id="LD-TIME-001",
                pointer=ROOT_POINTER,
                status=STATUS_CONFLICT if overlap else STATUS_UNSUPPORTED,
                blocking=True,
                reason=(
                    f"section {previous['section_id']} 는 {previous['end_ms']}ms 에 끝나고 "
                    f"{following['section_id']} 는 {following['start_ms']}ms 에 시작합니다 — "
                    f"{'겹침' if overlap else '공백'}입니다. 전곡을 겹침·공백 없이 "
                    "분할해야 합니다."
                ),
                stage=STAGE,
                before=present(previous["end_ms"]),
                after=present(following["start_ms"]),
            )
        )
    if sections[-1]["end_ms"] != duration_ms:
        diagnostics.append(
            Diagnostic(
                rule_id="LD-TIME-001",
                pointer=ROOT_POINTER,
                status=STATUS_UNSUPPORTED,
                blocking=True,
                reason=(
                    f"마지막 section 이 {sections[-1]['end_ms']}ms 에 끝나지만 곡 길이는 "
                    f"{duration_ms}ms 입니다. 분할이 전곡을 덮어야 합니다."
                ),
                stage=STAGE,
                before=present(sections[-1]["end_ms"]),
                after=present(duration_ms),
            )
        )

    if not diagnostics:
        diagnostics.append(
            Diagnostic(
                rule_id="LD-TIME-001",
                pointer=ROOT_POINTER,
                status=STATUS_ACCEPTED,
                blocking=False,
                reason=(
                    f"context sections {len(sections)}개가 [0,{duration_ms}) 를 겹침·공백 "
                    "없이 분할합니다. 변경·누락 없이 수용했습니다."
                ),
                stage=STAGE,
            )
        )
    return diagnostics


def _negative_ms_diagnostics(cue_index: int, cue: dict[str, Any]) -> list[Diagnostic]:
    """`LD-MIB-001` 음수 ms — 감독 판정에 따라 Director 경로에서 거부한다."""
    diagnostics: list[Diagnostic] = []
    at_ms = cue.get("at_ms")
    if isinstance(at_ms, int) and at_ms < 0:
        diagnostics.append(
            Diagnostic(
                rule_id="LD-MIB-001",
                pointer=f"/cues/{cue_index}/at_ms",
                status=STATUS_UNSUPPORTED,
                blocking=True,
                reason=f"cue 시각이 {at_ms}ms 입니다. {_NEW_ORIGIN_GUIDANCE}",
                stage=STAGE,
                before=present(at_ms),
            )
        )
    for action_index, action in enumerate(cue.get("actions") or []):
        timing = action.get("timing") or {}
        for axis in TIMING_AXES:
            axis_timing = timing.get(axis)
            if not isinstance(axis_timing, dict):
                continue
            for key in ("delay_ms", "fade_ms"):
                value = axis_timing.get(key)
                if isinstance(value, int) and value < 0:
                    diagnostics.append(
                        Diagnostic(
                            rule_id="LD-MIB-001",
                            pointer=f"/cues/{cue_index}/actions/{action_index}/timing/{axis}/{key}",
                            status=STATUS_UNSUPPORTED,
                            blocking=True,
                            reason=f"{axis} 축 {key} 가 {value} 입니다. {_NEW_ORIGIN_GUIDANCE}",
                            stage=STAGE,
                            before=present(value),
                        )
                    )
    return diagnostics


def _cue_settle_ms(cue: dict[str, Any]) -> int:
    """이 cue 의 모든 축 fade 가 끝나는 가장 늦은 시각."""
    at_ms = cue.get("at_ms") or 0
    latest = at_ms
    for action in cue.get("actions") or []:
        for axis_timing in (action.get("timing") or {}).values():
            if not isinstance(axis_timing, dict):
                continue
            delay = axis_timing.get("delay_ms") or 0
            fade = axis_timing.get("fade_ms") or 0
            latest = max(latest, at_ms + delay + fade)
    return latest


def _check_cues(plan: dict[str, Any], context: dict[str, Any]) -> list[Diagnostic]:
    """`LD-TIME-001` — 첫 cue=0, 자기 section 의 `start<=at<end`, settle 이 duration 이내."""
    diagnostics: list[Diagnostic] = []
    sections = _sections_by_id(context)
    duration_ms = (context.get("audio") or {}).get("duration_ms")
    cues = plan.get("cues") or []

    for cue_index, cue in enumerate(cues):
        diagnostics.extend(_negative_ms_diagnostics(cue_index, cue))

        section = sections.get(cue.get("section_id"))
        at_ms = cue.get("at_ms")
        if section is None:
            diagnostics.append(
                Diagnostic(
                    rule_id="LD-TIME-001",
                    pointer=f"/cues/{cue_index}/section_id",
                    status=STATUS_UNSUPPORTED,
                    blocking=True,
                    reason=(
                        f"cue 가 참조한 section {cue.get('section_id')!r} 가 context 에 "
                        "없습니다. plan sections 는 context 의 section 을 가리켜야 합니다."
                    ),
                    stage=STAGE,
                )
            )
        elif isinstance(at_ms, int) and not (section["start_ms"] <= at_ms < section["end_ms"]):
            diagnostics.append(
                Diagnostic(
                    rule_id="LD-TIME-001",
                    pointer=f"/cues/{cue_index}/at_ms",
                    status=STATUS_UNSUPPORTED,
                    blocking=True,
                    reason=(
                        f"cue 시각 {at_ms}ms 가 자기 section {section['section_id']} 의 "
                        f"[{section['start_ms']},{section['end_ms']}) 밖입니다. 경계는 "
                        "반열림이므로 end 시각은 다음 section 의 것입니다."
                    ),
                    stage=STAGE,
                    before=present(at_ms),
                )
            )

        if isinstance(duration_ms, int):
            settle_ms = _cue_settle_ms(cue)
            if settle_ms > duration_ms:
                diagnostics.append(
                    Diagnostic(
                        rule_id="LD-TIME-001",
                        pointer=f"/cues/{cue_index}",
                        status=STATUS_UNSUPPORTED,
                        blocking=True,
                        reason=(
                            f"delay/fade 가 {settle_ms}ms 에 끝나 곡 길이 {duration_ms}ms 를 "
                            "넘습니다. 마지막 cue 뒤에 남은 fade 도 duration 내에 "
                            "완료해야 합니다."
                        ),
                        stage=STAGE,
                        before=present(settle_ms),
                        after=present(duration_ms),
                    )
                )

    bundles = bundle_cues(plan)
    if not bundles:
        diagnostics.append(
            Diagnostic(
                rule_id="LD-TIME-001",
                pointer=ROOT_POINTER,
                status=STATUS_UNSUPPORTED,
                blocking=True,
                reason=(
                    "cue 가 없습니다. 빈 cue 배열은 draft 에서만 허용하므로 시간 해석 "
                    "대상이 아닙니다."
                ),
                stage=STAGE,
            )
        )
    elif bundles[0].at_ms != 0:
        first_cue_index = bundles[0].cue_indices[0]
        diagnostics.append(
            Diagnostic(
                rule_id="LD-TIME-001",
                pointer=f"/cues/{first_cue_index}/at_ms",
                status=STATUS_UNSUPPORTED,
                blocking=True,
                reason=(
                    f"첫 cue 가 {bundles[0].at_ms}ms 입니다. 계약은 첫 cue = 0 을 요구합니다 "
                    "— 원점은 audio 첫 sample 입니다."
                ),
                stage=STAGE,
                before=present(bundles[0].at_ms),
            )
        )
    return diagnostics


def _has_beat_based_fx(plan: dict[str, Any]) -> bool:
    for cue in plan.get("cues") or []:
        for action in cue.get("actions") or []:
            if action.get("op") == "fx_start":
                return True
    return False


def _check_tempo_status(plan: dict[str, Any], context: dict[str, Any]) -> list[Diagnostic]:
    """`LD-TIME-002` + 계약 §6.1 — beat_map 근거가 이 환경에서 유효한가.

    `LD-TIME-002` 는 *"confirmed 근거 필수"* 라 쓰지만 §6.1 이 예외를 적었다 —
    *"absent/unconfirmed 에서는 beat 기반 FX 를 실행하지 않는다. `synthetic` 은 합성
    harness 에서만 허용한다."* 그래서 판정은 `confirmed`, 또는 (`synthetic` AND
    `environment == "synthetic"`) 다. 이 예외가 없으면 계약의 규범 예제가 스스로 막힌다.
    """
    beat_map = context.get("beat_map") or {}
    status = beat_map.get("status")
    environment = context.get("environment")

    if status == BEAT_STATUS_CONFIRMED:
        return [
            Diagnostic(
                rule_id="LD-TIME-002",
                pointer=ROOT_POINTER,
                status=STATUS_ACCEPTED,
                blocking=False,
                reason=(
                    f"beat_map 이 confirmed 이고 segment {len(_segments(beat_map))}개를 "
                    "제공합니다. beat 기반 계산의 근거로 수용했습니다."
                ),
                stage=STAGE,
            )
        ]

    if status == BEAT_STATUS_SYNTHETIC:
        if environment == "synthetic":
            return [
                Diagnostic(
                    rule_id="LD-TIME-002",
                    pointer=ROOT_POINTER,
                    status=STATUS_ACCEPTED,
                    blocking=False,
                    reason=(
                        "beat_map 이 synthetic 이고 environment 도 synthetic 입니다. 계약 "
                        "§6.1 이 합성 harness 에서만 이것을 허용하므로 이 조합에서 수용하며, "
                        "실제 음악 확인을 주장하지 않습니다."
                    ),
                    stage=STAGE,
                )
            ]
        return [
            Diagnostic(
                rule_id="LD-TIME-002",
                pointer=ROOT_POINTER,
                status=STATUS_UNSUPPORTED,
                blocking=True,
                reason=(
                    f"beat_map 이 synthetic 인데 environment 가 {environment!r} 입니다. "
                    "계약 §6.1 은 synthetic beat_map 을 합성 harness 에서만 허용합니다 — "
                    "production 판정의 근거로 쓸 수 없습니다."
                ),
                stage=STAGE,
                before=present(str(status)),
                after=present(str(environment)),
            )
        ]

    blocking = _has_beat_based_fx(plan)
    return [
        Diagnostic(
            rule_id="LD-TIME-002",
            pointer=ROOT_POINTER,
            status=STATUS_UNSUPPORTED if blocking else STATUS_ACCEPTED,
            blocking=blocking,
            reason=(
                f"beat_map status 가 {status!r} 입니다. 계약 §6.1 은 absent/unconfirmed "
                "에서 beat 기반 FX 를 실행하지 않도록 규정합니다"
                + (
                    " — 이 계획은 fx_start 를 요청하므로 막습니다. 기본 BPM 을 가정하지 않습니다."
                    if blocking
                    else ". 이 계획은 beat 기반 FX 를 요청하지 않아 판정에 영향이 없습니다."
                )
            ),
            stage=STAGE,
        )
    ]


def _fx_spans(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """`instance_id` 별 start/stop 시각. 1:1 짝 검사는 C3(`LD-FX-001`)의 일이다."""
    spans: dict[str, dict[str, Any]] = {}
    for cue_index, cue in enumerate(plan.get("cues") or []):
        at_ms = cue.get("at_ms")
        for action in cue.get("actions") or []:
            instance_id = action.get("instance_id")
            if not instance_id or action.get("op") not in ("fx_start", "fx_stop"):
                continue
            span = spans.setdefault(instance_id, {})
            key = "start_ms" if action["op"] == "fx_start" else "stop_ms"
            span[key] = at_ms
            span.setdefault("cue_index", cue_index)
    return spans


def _uncovered_ms(segments: list[dict[str, Any]], start_ms: int, stop_ms: int) -> int | None:
    """`[start_ms, stop_ms)` 안에서 어떤 segment 도 덮지 않는 첫 시각. 없으면 `None`.

    segment 는 인접해 있을 수도, 떨어져 있을 수도 있으므로 덮인 구간을 이어붙여서 본다.
    """
    cursor = start_ms
    for segment in segments:
        if segment["start_ms"] <= cursor < segment["end_ms"]:
            cursor = segment["end_ms"]
            if cursor >= stop_ms:
                return None
    return None if cursor >= stop_ms else cursor


def _check_fx_tempo_coverage(plan: dict[str, Any], context: dict[str, Any]) -> list[Diagnostic]:
    """`LD-TIME-002` — beat 기반 FX 구간이 tempo 지도로 완전히 덮이는가.

    이 검사가 없으면 tempo 지도가 곡 뒷부분을 안 덮어도 조용히 통과한다. `beat_at` 은
    tempo 불명에 예외를 던지지만 **아무도 큐 시각으로 그것을 부르지 않기 때문에** 부재가
    부재로 남는다. 자기 검토에서 찾은 구멍이며, 계약이 *"tempo 불명인데 120 BPM을 가정하지
    않는다"* 로 막으라고 한 바로 그 상황이다.

    범위를 FX 로 한정한다 — 일반 cue 의 `at_ms` 는 절대 시각이라 박 계산이 필요 없고, 거기까지
    막으면 tempo 지도 없이도 유효한 정적 계획이 통째로 막힌다.
    """
    segments = _segments(context.get("beat_map") or {})
    diagnostics: list[Diagnostic] = []
    for instance_id, span in sorted(_fx_spans(plan).items()):
        start_ms = span.get("start_ms")
        stop_ms = span.get("stop_ms")
        if not isinstance(start_ms, int) or not isinstance(stop_ms, int):
            continue
        gap_ms = _uncovered_ms(segments, start_ms, stop_ms)
        if gap_ms is None:
            continue
        diagnostics.append(
            Diagnostic(
                rule_id="LD-TIME-002",
                pointer=f"/cues/{span['cue_index']}",
                status=STATUS_UNSUPPORTED,
                blocking=True,
                reason=(
                    f"FX instance {instance_id} 의 구간 [{start_ms},{stop_ms}) 중 "
                    f"{gap_ms}ms 를 덮는 tempo segment 가 없습니다. cycle_beats·phase_beats "
                    "는 박 계산을 요구하므로 tempo 불명 구간에서 실행할 수 없습니다 — "
                    "기본 BPM 을 가정하지 않습니다."
                ),
                stage=STAGE,
                before=present(gap_ms),
            )
        )
    return diagnostics


def _check_fx_tempo_crossing(plan: dict[str, Any], context: dict[str, Any]) -> list[Diagnostic]:
    """`LD-TIME-002` — 한 FX instance 가 다른 bpm segment 를 가로지르면 막는다.

    구간은 `[start,stop)` 이므로 segment 경계에서 **끝나는** instance 는 가로지르지 않는다.
    """
    beat_map = context.get("beat_map") or {}
    segments = _segments(beat_map)
    internal_boundaries = [segment["start_ms"] for segment in segments[1:]]
    if not internal_boundaries:
        return []

    diagnostics: list[Diagnostic] = []
    for instance_id, span in sorted(_fx_spans(plan).items()):
        start_ms = span.get("start_ms")
        stop_ms = span.get("stop_ms")
        if not isinstance(start_ms, int) or not isinstance(stop_ms, int):
            continue
        crossed = [b for b in internal_boundaries if start_ms < b < stop_ms]
        if not crossed:
            continue
        diagnostics.append(
            Diagnostic(
                rule_id="LD-TIME-002",
                pointer=f"/cues/{span['cue_index']}",
                status=STATUS_UNSUPPORTED,
                blocking=True,
                reason=(
                    f"FX instance {instance_id} 의 active 구간 [{start_ms},{stop_ms}) 가 "
                    f"tempo 경계 {crossed} 를 가로지릅니다. 계약은 explicit stop + 새 start "
                    "로 분할하거나 unsupported 로 답하라고 규정합니다 — 한쪽 bpm 으로 "
                    "조용히 계산하지 않습니다."
                ),
                stage=STAGE,
                before=present(start_ms),
                after=present(stop_ms),
            )
        )
    return diagnostics


def _check_delta_chain(plan: dict[str, Any]) -> list[Diagnostic]:
    """`LD-TIME-003` — delta 사슬이 계산되는지. mode 가 계약 밖이면 앞 단계가 이미 막았다."""
    try:
        bundles = trig_time_bundles(plan)
    except ValueError:
        return []
    if not bundles:
        return []

    mode = plan["playback"]["mode"]
    return [
        Diagnostic(
            rule_id="LD-TIME-003",
            pointer=ROOT_POINTER,
            status=STATUS_ACCEPTED,
            blocking=False,
            reason=(
                f"playback mode {mode} 로 bundle {len(bundles)}개를 낮췄습니다. 첫 GO 는 "
                "사람이 수행하며 이후 시각은 직전 bundle 과의 상대 차이로 저장합니다 — "
                "절대 at_ms 를 TrigTime 으로 넘기지 않습니다."
            ),
            stage=STAGE,
        )
    ]


def check_timing(plan: dict[str, Any], context: dict[str, Any]) -> list[Diagnostic]:
    """C1 파이프라인 2단(`time_reference`)의 본체. 진단 목록을 낸다.

    앞 검사가 막아도 끊지 않는다 — 계약 §6.3 이 요구하는 진단 coverage 를 지키려면 사람이
    무엇을 왜 고쳐야 하는지 다 보여야 한다. 조용한 수용은 이 층의 답이 아니므로 통과도
    사유를 든 진단으로 낸다.
    """
    diagnostics: list[Diagnostic] = []
    diagnostics.extend(_check_playback(plan))
    diagnostics.extend(_check_section_coverage(context))
    diagnostics.extend(_check_cues(plan, context))
    diagnostics.extend(_check_tempo_status(plan, context))
    diagnostics.extend(_check_fx_tempo_coverage(plan, context))
    diagnostics.extend(_check_fx_tempo_crossing(plan, context))
    diagnostics.extend(_check_delta_chain(plan))
    return diagnostics
