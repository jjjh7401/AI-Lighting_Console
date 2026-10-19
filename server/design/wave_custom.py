"""카드 WT-wave-custom — 감독이 고른 웨이브 값 검사(순수 함수 · 콘솔 접촉 0건).

감독은 웨이브 모양(사인·무지개·웜쿨)과 박 수(1·2·4)와 이름을 고른다. 이 모듈은 그 값을 검사해
웨이브 프리셋 저장 묶음(``wave_presets``)이 쓰는 ``WavePreset`` 으로 바꾼다. 저장 자체는 승인 카드
경로가 하고, 칸에 적용하는 일은 이 모듈이 하지 않는다.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from server.design.wave_presets import WavePreset


@dataclass(frozen=True)
class WaveShape:
    shape_id: str  # 와이어에 실리는 모양 id
    kind: str  # "dimmer" | "color" — 저장 묶음의 종류
    fx_id: str  # 출하 fx 라이브러리의 틀
    display_head: str  # 화면에 보이는 모양 이름


#: 고를 수 있는 웨이브 모양. 틀은 출하 라이브러리에 이미 있는 것만 쓴다.
WAVE_SHAPES: tuple[WaveShape, ...] = (
    WaveShape("sine", "dimmer", "pulse-sine-breath", "디머 웨이브 · 사인"),
    WaveShape("rainbow", "color", "chase-rainbow-wave", "컬러 웨이브 · 무지개"),
    WaveShape("warmcool", "color", "chase-warm-cool", "컬러 웨이브 · 웜쿨"),
)

#: 고를 수 있는 한 주기 박 수.
WAVE_BEATS: tuple[int, ...] = (1, 2, 4)

#: 콘솔 프리셋 이름 — 영문·숫자·가운데 공백만, 첫·끝은 영문이나 숫자, 20자 이하(REQ-LDBEAT-015(d)).
WAVE_LABEL_MAX = 20
_CONSOLE_LABEL = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9 ]*[A-Za-z0-9])?")

#: 화면에 보이는 이름 — 한글·영문 모두 되고 1~40자다.
WAVE_NAME_MAX = 40


@dataclass(frozen=True)
class WaveSpec:
    shape_id: str
    beats: int
    console_label: str
    display_name: str


def wave_shape_of(shape_id: str) -> WaveShape | None:
    return next((shape for shape in WAVE_SHAPES if shape.shape_id == shape_id), None)


def wave_spec_from_fields(
    shape_id: object, beats: object, console_label: object, display_name: object
) -> tuple[WaveSpec | None, str | None]:
    """와이어 값 네 개를 검사한다. 반환: ``(규격 또는 None, 거절 사유 또는 None)``."""
    if not isinstance(shape_id, str) or wave_shape_of(shape_id) is None:
        return None, f"웨이브 모양 {shape_id!r}은 고를 수 없습니다."
    if isinstance(beats, bool) or not isinstance(beats, int) or beats not in WAVE_BEATS:
        return None, f"박 수 {beats!r}는 {WAVE_BEATS} 중 하나여야 합니다."
    if (
        not isinstance(console_label, str)
        or len(console_label) > WAVE_LABEL_MAX
        or _CONSOLE_LABEL.fullmatch(console_label) is None
    ):
        return None, (
            "콘솔 이름은 영문·숫자·가운데 공백만 쓰고 20자 이하로 적어 주세요 "
            "(첫·끝은 영문이나 숫자)."
        )
    if not isinstance(display_name, str) or not display_name.strip():
        return None, "화면 이름을 적어 주세요."
    name = display_name.strip()
    if len(name) > WAVE_NAME_MAX:
        return None, f"화면 이름은 {WAVE_NAME_MAX}자 이하로 적어 주세요."
    return WaveSpec(shape_id, beats, console_label, name), None


def wave_spec_preset(spec: WaveSpec) -> WavePreset:
    """규격 하나를 저장 묶음이 쓰는 ``WavePreset`` 으로 바꾼다. 틀과 종류는 모양이 정한다."""
    shape = wave_shape_of(spec.shape_id)
    if shape is None:  # 검사를 거친 규격만 들어온다 — 그래도 조용히 빈 묶음을 내지 않는다.
        raise KeyError(spec.shape_id)
    return WavePreset(
        display_name=spec.display_name,
        console_label=spec.console_label,
        fx_id=shape.fx_id,
        beats=spec.beats,
        kind=shape.kind,
    )


def custom_wave_problem(spec: WaveSpec, pool: Mapping[int, str | None]) -> str | None:
    """효과 풀 판독(``{번호: 이름}``)에 같은 콘솔 이름이 이미 있으면 사유를 돌려준다.

    같은 이름은 「건너뜀」이 아니라 「거절」이다 — 감독이 직접 고른 이름이 조용히 빠지면 안 된다.
    """
    taken = {name for name in pool.values() if name}
    if spec.console_label in taken:
        return (
            f"같은 이름 「{spec.console_label}」이 효과 풀에 이미 있습니다 — "
            "다른 이름으로 바꿔 저장해 주세요."
        )
    return None
