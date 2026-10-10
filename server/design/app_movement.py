"""앱 2단계 무빙 칸(``app_movement``) 명령 에미터 — SPEC-LDBEAT-001 M8
(카드 t548, REQ-LDBEAT-006(vi)(vii), REQ-LDBEAT-015(g)).

이 모듈은 콘솔에 아무것도 쓰지 않는다. 입력도 출력도 순수 파이썬 값뿐이다
(``server.design.beat_grid``·``server.spatial.position_fx``와 같은 모양).
장비 ID·콘솔 그룹 번호·프리셋 번호는 전부 **호출자가** 넘긴다(그 곡의 데이터
파일에서 왔다) — 이 모듈 코드 안에는 그런 리그·곡 전용 리터럴이 전혀 없다
(REQ-LDBEAT-006(vi-6), AC-LDBEAT-016(s)).

두 가지를 낸다:

1. :func:`app_movement_commands` — 한 칸의 ``app_movement``를 명령 줄
   리스트로. 실기 검증된 순서(선택+기준 위치 리콜 → 상대 두 단계 → 커브 →
   위상 → 속도, `.moai/reports/t548/probe-moverd.md`)를 따른다. 기준 위치는
   **그 칸 자신의** ``position_preset_no``에서만 온다(REQ-LDBEAT-006(vi-8))
   — ``position_fx``의 레이블 해석 뱅크 프리셋(``'Floor Base'``류)은 절대
   호출하지 않는다.
2. :func:`dimmer_attribute_names` / :func:`brightness_value_commands` —
   ``brightness.mode == "value"``인 칸의 값을 그 기구의 **모든** 디머
   속성에 낸다(MOVER-D/Spiider는 Dimmer+Dimmer2 둘 다 켜야 빛난다 —
   `.moai/reports/t548/probe-moverd.md` v0a/v0b 실측). 어느 기구가 무슨
   디머 속성을 갖는지는 ``FixtureCapability``가 이미 읽은 값에서만 온다 —
   이 모듈은 어떤 기구 타입 이름도 속성 번호도 몰라도 된다.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence

from server.spatial.position_fx import POSITION_FX_EFFECTS, relative_wave_lines

__all__ = [
    "app_movement_commands",
    "brightness_value_commands",
    "dimmer_attribute_names",
]

#: MA3 Dimmer 속성 패밀리 — "Dimmer"·"Dimmer2"처럼 접두 "Dimmer" 뒤에 숫자만
#: (또는 아무것도) 오는 이름 **정확** 일치. "DimmerCurve"처럼 뒤에 다른
#: 단어가 붙은 속성은 밝기 조정이 아니라 제외한다(접두 일치가 아니다).
_DIMMER_ATTRIBUTE = re.compile(r"^dimmer\d*$")


def dimmer_attribute_names(attributes: Sequence[str]) -> tuple[str, ...]:
    """``attributes``(콘솔 철자 그대로, ``FixtureCapability.attributes``와
    같은 원천) 중 MA3 디머 패밀리만 걸러 원래 순서로 돌려준다. 순수 필터 —
    기구 타입 이름·속성 번호·장비 ID를 전혀 모른다."""
    return tuple(
        name for name in attributes if _DIMMER_ATTRIBUTE.fullmatch(name.strip().casefold())
    )


def brightness_value_commands(
    *,
    group_no: int,
    value_percent: int,
    dimmer_attributes: Sequence[str],
) -> tuple[str, ...]:
    """``brightness.mode == "value"``인 칸의 퍼센트를 ``dimmer_attributes``의
    **모든** 속성 각각에 한 줄씩 낸다 — Dimmer만 있는 기구는 한 줄(Dimmer2
    줄 0건), Dimmer+Dimmer2를 가진 기구(MOVER-D/Spiider)는 두 줄이다
    (`.moai/reports/t548/probe-moverd.md` v0a/v0b 실측 — Dimmer2까지 내야
    빛난다). ``dimmer_attributes``가 비어 있으면 아무것도 내지 않는다(이
    함수는 "속성이 없다"를 단정하지 않는다 — 그 판정은 호출자의 몫,
    :func:`dimmer_attribute_names`의 whole/gaps 주의 참조)."""
    selection = f"Group {group_no}"
    return tuple(
        f"{selection} ; Attribute '{attr}' At {value_percent}" for attr in dimmer_attributes
    )


def app_movement_commands(
    movement: Mapping[str, object] | None,
    *,
    group_no: int,
    position_preset_no: str | None,
    bpm: float | None,
    beats_per_bar: int | None,
) -> tuple[tuple[str, ...], str | None]:
    """한 칸의 ``app_movement``를 명령 줄 리스트로 — 실기 검증 순서(선택+
    기준 위치 리콜 → 상대 두 단계 → 커브 → 위상 → 속도).

    ``movement``가 `None`(이 칸에 app_movement가 없음)이면 ``((), None)``
    — 거절이 아니라 "낼 것이 없다". 그 외에는 셋 중 하나:

    - BPM·(마디 주기일 때) 마디당 박·주기값 중 하나라도 없으면 **거절**
      (사유 문자열, 커맨드 0개) — 속도를 지어내지 않는다.
    - ``shape``가 이 에미터가 아직 못 내는 모양(이 M8은 ``"wave"``만
      구현한다)이면 **거절** — 추측 구현하지 않는다(plan.md §F 안티패턴).
    - 그 외에는 명령 줄 튜플 + `None`(사유 없음).

    기준 위치는 **그 칸 자신의** ``position_preset_no``에서만 온다
    (REQ-LDBEAT-006(vi-8)) — `None`이면 기준 리콜 줄 자체가 0건이고(생략,
    기본 위치(수직) 중심으로 상대 단계가 그대로 나간다), ``position_fx``의
    레이블 해석 뱅크 프리셋은 이 함수 어디에서도 호출하지 않는다."""
    if not movement:
        return (), None

    shape = movement.get("shape")
    if shape not in POSITION_FX_EFFECTS:
        return (), f"app_movement.shape {shape!r} 는 닫힌 모양 어휘가 아닙니다"
    if shape != "wave":
        return (), f"app_movement.shape {shape!r} 는 이 에미터가 아직 못 냅니다(M8은 wave만 구현)"

    axes_raw = movement.get("axes") or ()
    axes = frozenset(axes_raw)
    if not axes or not axes <= {"Pan", "Tilt"}:
        return (), f"app_movement.axes {axes_raw!r} 가 Pan/Tilt의 비어있지 않은 부분집합이 아닙니다"

    period_unit = movement.get("period_unit")
    if period_unit not in ("beat", "bar"):
        return (), f"app_movement.period_unit {period_unit!r} 는 'beat' 또는 'bar' 가 아닙니다"

    period_value = movement.get("period_value")
    if not isinstance(period_value, int) or isinstance(period_value, bool) or period_value <= 0:
        return (), f"app_movement.period_value {period_value!r} 는 양의 정수가 아닙니다"

    if bpm is None or not math.isfinite(bpm) or bpm <= 0:
        return (), "BPM이 없어 Speed를 계산할 수 없습니다(지어내지 않음)"

    if period_unit == "bar":
        if beats_per_bar is None or beats_per_bar <= 0:
            return (), "beats_per_bar가 없어 마디 단위 주기를 박으로 환산할 수 없습니다"
        beats_per_cycle = period_value * beats_per_bar
    else:
        beats_per_cycle = period_value
    speed_bpm = bpm / beats_per_cycle

    selection = f"Group {group_no}"
    commands: list[str] = []
    if position_preset_no is not None:
        commands.append(f"{selection} ; At Preset {position_preset_no}")
    else:
        commands.append(selection)

    phase_spread = bool(movement.get("phase_spread"))
    commands.extend(relative_wave_lines(axes, speed_bpm, phase_spread=phase_spread))
    return tuple(commands), None
