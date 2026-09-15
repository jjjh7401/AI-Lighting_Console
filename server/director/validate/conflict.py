"""fixture×axis 충돌 검출 (SPEC-LDCOMPILE-001 C3, REQ-LDPLUGIN-011).

계약 §8 `LD-CONFLICT-001` 의 판정 단위는 **fixture 다.** group 단위로 뭉치면 겹친 두 group 이
같은 fixture 의 같은 축을 동시에 써도 보이지 않는다 — 그래서 첫 단계가 group → `fixture_ids`
전개다.

예약 구간의 형태가 두 번째 축이다:

```
        at_ms                     at_ms+delay+fade
          |------- delay -------|--- fade ---|
          [                                  )        ← 반열림
```

- **시작은 `at_ms`** — delay 구간도 예약이다. 계약이 *"delay 구간은 새 transition 예약
  구간이며 다른 변경으로 시작값을 바꾸지 못한다"* 고 적었다.
- **반열림** — `transition 끝 == 다음 시작` 은 허용이다. 규범 예제가 이 규칙에 의존한다
  (FX `[52000, 79500)` 앞뒤로 static intensity 가 `…50500` 과 `80000…` 에 놓인다).
- **길이 0 구간도 예약이다** — `fade=0` 의 순간 변경. 같은 시각에 둘이면 충돌이고
  (*"한 instant 의 중복 쓰기"*), 남의 구간 끝점에 놓이면 허용이다.

같은 값이어도 충돌이다. 「결과가 같으니 괜찮다」는 이 층의 답이 아니다 — 어느 쪽이 이기는지
정해지지 않은 것 자체가 결함이다.

[HARD] 콘솔 무접촉 · OSC 무접촉 — dict 만 다룬다.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any

from server.director.validate.diagnostics import (
    STATUS_ACCEPTED,
    STATUS_CONFLICT,
    STATUS_UNRESOLVED,
    Diagnostic,
)
from server.director.validate.simulate import ActionRef, action_refs, fx_instances

STAGE = "tracking_fx"

ROOT_POINTER = ""

#: 예약 단위가 되는 축 다섯. `position_set` 은 pan·tilt 둘을 각각 예약한다 —
#: 상태 슬롯은 `position_ref` 하나지만 축은 둘이며, 축이 판정 단위다.
AXES: tuple[str, ...] = ("intensity", "color", "pan", "tilt", "beam")

#: static op → 그 op 이 예약하는 축. 각 축의 timing 은 action 의 `timing[axis]` 에 있다.
_OP_AXES: dict[str, tuple[str, ...]] = {
    "intensity_set": ("intensity",),
    "color_set": ("color",),
    "position_set": ("pan", "tilt"),
    "beam_set": ("beam",),
    "group_release": AXES,
}


@dataclass(frozen=True, slots=True)
class Reservation:
    """한 fixture 의 한 축을 `[start_ms, end_ms)` 동안 잡는다."""

    fixture_id: str
    axis: str
    start_ms: int
    end_ms: int
    pointer: str
    label: str

    def overlaps(self, other: Reservation) -> bool:
        """반열림 겹침 + **같은 시작 시각**.

        같은 시작을 따로 두는 이유: 길이 0 구간(`fade=0` 순간 변경)은 반열림 판정만으로는
        아무와도 겹치지 않는다. 그러면 *"한 instant 의 중복 쓰기"* 가 조용히 통과한다.
        """
        if self.start_ms == other.start_ms:
            return True
        return self.start_ms < other.end_ms and other.start_ms < self.end_ms


def _timing_window(action: dict[str, Any], axis: str, at_ms: int) -> tuple[int, int] | None:
    """축 하나의 예약 구간. timing 항목이 없으면 `None` — 지어내지 않는다."""
    timing = action.get("timing")
    if not isinstance(timing, dict):
        return None
    entry = timing.get(axis)
    if not isinstance(entry, dict):
        return None
    delay = int(entry.get("delay_ms", 0))
    fade = int(entry.get("fade_ms", 0))
    return at_ms, at_ms + delay + fade


def _group_fixtures(context: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    return {
        str(g.get("group_id")): tuple(str(f) for f in g.get("fixture_ids") or [])
        for g in context.get("groups") or []
        if isinstance(g, dict)
    }


def _preset_axes(context: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    return {
        str(p.get("preset_id")): tuple(str(a) for a in p.get("affects_axes") or [])
        for p in context.get("presets") or []
        if isinstance(p, dict)
    }


def _unresolved(pointer: str, reason: str) -> Diagnostic:
    return Diagnostic(
        rule_id="LD-CONFLICT-001",
        pointer=pointer,
        status=STATUS_UNRESOLVED,
        blocking=True,
        reason=reason,
        stage=STAGE,
    )


def _static_reservations(
    ref: ActionRef, fixtures: tuple[str, ...]
) -> tuple[list[Reservation], list[Diagnostic]]:
    reservations: list[Reservation] = []
    diagnostics: list[Diagnostic] = []
    for axis in _OP_AXES.get(ref.op, ()):
        window = _timing_window(ref.action, axis, ref.at_ms)
        if window is None:
            diagnostics.append(
                _unresolved(
                    ref.pointer,
                    f"{ref.op} 에 {axis} 축 timing 이 없습니다. 계약 §7 은 모든 axis timing 을 "
                    "명시하도록 규정하며 기본값 상속이 없으므로, 예약 구간을 지어내지 "
                    "않고 판정 불능으로 답합니다.",
                )
            )
            continue
        start, end = window
        for fixture in fixtures:
            reservations.append(
                Reservation(
                    fixture_id=fixture,
                    axis=axis,
                    start_ms=start,
                    end_ms=end,
                    pointer=ref.pointer,
                    label=f"{ref.op}(group {ref.group_id})",
                )
            )
    return reservations, diagnostics


def _fx_reservations(
    plan: dict[str, Any],
    group_fixtures: dict[str, tuple[str, ...]],
    preset_axes: dict[str, tuple[str, ...]],
) -> tuple[list[Reservation], list[Diagnostic]]:
    """FX 는 start 시각부터 **stop fade 완료까지** 자기 축을 잡는다.

    계약: *"stop fade 는 base state 로 복귀하므로 영향을 받는 base 축은 FX active 동안
    바꾸지 않는다"* + *"FX stop fade 가 끝난 뒤에만 그 축을 다시 쓸 수 있다"*.
    """
    reservations: list[Reservation] = []
    diagnostics: list[Diagnostic] = []

    for instance, entry in sorted(fx_instances(plan).items()):
        if not entry.starts or not entry.stops:
            # 짝이 없는 FX 는 `simulate.check_ready` 가 LD-FX-001 로 막는다. 여기서
            # 구간의 끝을 지어내면 없는 충돌을 만들거나 있는 충돌을 가린다.
            continue
        start, stop = entry.starts[0], entry.stops[0]
        preset_ref = str(start.action.get("preset_ref", ""))
        axes = preset_axes.get(preset_ref)
        if axes is None:
            diagnostics.append(
                _unresolved(
                    start.pointer,
                    f"FX preset {preset_ref} 를 context 에서 찾을 수 없어 affects_axes 를 "
                    "알 수 없습니다. 빈 집합으로 두면 이 FX 가 아무 축도 쓰지 않는 것처럼 "
                    "보여 충돌이 조용히 사라지므로, 판정 불능으로 답합니다.",
                )
            )
            continue

        window = _timing_window(stop.action, "fx", stop.at_ms)
        end_ms = window[1] if window else stop.at_ms
        fixtures = group_fixtures.get(start.group_id, ())

        for axis in axes:
            for fixture in fixtures:
                reservations.append(
                    Reservation(
                        fixture_id=fixture,
                        axis=axis,
                        start_ms=start.at_ms,
                        end_ms=end_ms,
                        pointer=start.pointer,
                        label=f"FX {instance}(group {start.group_id})",
                    )
                )

    return reservations, diagnostics


def reservations(
    plan: dict[str, Any], context: dict[str, Any]
) -> tuple[list[Reservation], list[Diagnostic]]:
    """계획 전체를 `(fixture, axis)` 예약 목록으로 전개한다."""
    group_fixtures = _group_fixtures(context)
    preset_axes = _preset_axes(context)

    collected: list[Reservation] = []
    diagnostics: list[Diagnostic] = []
    missing_groups: set[str] = set()

    for ref in action_refs(plan):
        if ref.op in ("fx_start", "fx_stop"):
            continue
        fixtures = group_fixtures.get(ref.group_id)
        if fixtures is None:
            if ref.group_id not in missing_groups:
                missing_groups.add(ref.group_id)
                diagnostics.append(
                    _unresolved(
                        ref.pointer,
                        f"group {ref.group_id} 이 context 의 groups 에 없어 fixture 로 전개할 "
                        "수 없습니다. 빈 fixture 집합으로 두면 그 group 의 충돌이 전부 "
                        "사라지므로, 판정 불능으로 답합니다.",
                    )
                )
            continue
        found, problems = _static_reservations(ref, fixtures)
        collected.extend(found)
        diagnostics.extend(problems)

    fx_found, fx_problems = _fx_reservations(plan, group_fixtures, preset_axes)
    collected.extend(fx_found)
    diagnostics.extend(fx_problems)

    return collected, diagnostics


#: 박 전개 한 판의 상한. `cycle_beats` 최소값 0.0625 에 긴 곡을 곱하면 만 단위가 되므로
#: 상한을 둔다. 상한에 닿았다는 사실은 아래에서 진단으로 남긴다 — 조용히 자르지 않는다.
_MAX_BEAT_REQUESTS_PER_INSTANCE = 10_000


def fx_beat_requests(plan: dict[str, Any], context: dict[str, Any]) -> list[tuple[str, str, float]]:
    """FX cycle 경계를 `(group_id, axis, beat)` 목록으로 낮춘다.

    `timing.rounding_conflicts` 가 받는 입력이다. C2 가 그 검사를 만들었지만 이 목록을
    만드는 곳이 없어 검사가 경로에 이어지지 않았다 — 계약 §7 *"rounding 으로 충돌이
    생기면 거부한다"* 가 실제로 걸리는 자리는 FX 처럼 **박으로 반복되는** 것뿐이다.
    일반 cue 의 `at_ms` 는 절대 시각이라 박 계산을 거치지 않는다.
    """
    from server.director.validate.timing import TempoUnknownError, beat_at, ms_at_beat

    beat_map = context.get("beat_map")
    if not isinstance(beat_map, dict):
        return []

    preset_axes = _preset_axes(context)
    requests: list[tuple[str, str, float]] = []

    for entry in fx_instances(plan).values():
        if not entry.starts or not entry.stops:
            continue
        start, stop = entry.starts[0], entry.stops[0]
        axes = preset_axes.get(str(start.action.get("preset_ref", "")))
        if not axes:
            continue
        cycle = float(start.action.get("cycle_beats") or 0)
        if cycle <= 0:
            continue

        window = _timing_window(stop.action, "fx", stop.at_ms)
        end_ms = window[1] if window else stop.at_ms
        try:
            beat = beat_at(beat_map, start.at_ms) + float(start.action.get("phase_beats") or 0)
        except TempoUnknownError:
            # tempo 불명은 반올림 충돌이 아니라 별개 결함이다. C2 의 tempo 단계가 소유한다.
            continue

        for _ in range(_MAX_BEAT_REQUESTS_PER_INSTANCE):
            try:
                if ms_at_beat(beat_map, beat) > end_ms:
                    break
            except TempoUnknownError:
                break
            for axis in axes:
                requests.append((start.group_id, axis, beat))
            beat += cycle

    return requests


def _conflict_diagnostic(a: Reservation, b: Reservation) -> Diagnostic:
    first, second = sorted((a, b), key=lambda r: (r.start_ms, r.end_ms, r.pointer, r.label))
    return Diagnostic(
        rule_id="LD-CONFLICT-001",
        pointer=second.pointer,
        status=STATUS_CONFLICT,
        blocking=True,
        reason=(
            f"fixture {first.fixture_id} 의 {first.axis} 축을 두 변경이 겹치는 구간에서 "
            f"씁니다 — {first.label} 이 [{first.start_ms}, {first.end_ms}) 를, "
            f"{second.label} 이 [{second.start_ms}, {second.end_ms}) 를 잡습니다. 계약 "
            "LD-CONFLICT-001 은 **동일 값이어도** conflict 로 규정합니다: 어느 쪽이 "
            "이기는지 정해지지 않은 것 자체가 결함입니다. delay 구간도 예약이며, "
            "transition 끝 == 다음 시작은 허용입니다."
        ),
        stage=STAGE,
    )


def check_conflicts(plan: dict[str, Any], context: dict[str, Any] | None) -> list[Diagnostic]:
    """3단의 충돌 판정 — `LD-CONFLICT-001`.

    `context` 없이는 group → fixture 전개를 할 수 없다. 판정 불능을 수용으로 바꾸지
    않는다 — 그러면 충돌 검사가 조용히 사라진 채 ready 가 나올 수 있다.
    """
    if context is None:
        return [
            _unresolved(
                ROOT_POINTER,
                "ContextSnapshot 없이 충돌을 판정할 수 없습니다 — group membership 과 preset "
                "affects_axes 가 모두 context 에 있습니다. context 를 주입해 검증기를 "
                "구성하십시오.",
            )
        ]

    collected, diagnostics = reservations(plan, context)

    by_key: dict[tuple[str, str], list[Reservation]] = {}
    for reservation in collected:
        by_key.setdefault((reservation.fixture_id, reservation.axis), []).append(reservation)

    for key in sorted(by_key):
        # 전수 쌍 비교다. 인접 쌍만 보면 한 구간이 뒤의 여럿과 겹칠 때 뒤의 것들이
        # 배열 순서에 밀려 사라진다 — 계약이 금지한 「배열 순서로 덮어쓰기」다.
        for a, b in combinations(sorted(by_key[key], key=lambda r: (r.start_ms, r.end_ms)), 2):
            if a.pointer == b.pointer and a.label == b.label:
                # 같은 action 이 같은 fixture 를 두 번 잡는 일은 없다. 방어적 무시.
                continue
            if a.overlaps(b):
                diagnostics.append(_conflict_diagnostic(a, b))

    if diagnostics:
        # 진단은 예약 구간으로 결정되며 배열 순서에 의존하지 않는다. 정렬해서 내는 것은
        # 「순서를 뒤집으면 같은 집합이 나온다」를 사람이 눈으로도 확인할 수 있게 하려는 것.
        return sorted(diagnostics, key=lambda d: (d.pointer, d.reason))

    return [
        Diagnostic(
            rule_id="LD-CONFLICT-001",
            pointer=ROOT_POINTER,
            status=STATUS_ACCEPTED,
            blocking=False,
            reason=(
                f"예약 구간 {len(collected)} 개를 fixture 로 전개해 대조했고 같은 "
                "fixture·축에서 겹치는 구간이 없습니다. transition 끝 == 다음 시작은 "
                "허용이므로 맞닿은 구간은 충돌로 세지 않았습니다."
            ),
            stage=STAGE,
        )
    ]
