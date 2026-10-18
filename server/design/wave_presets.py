"""카드 WT-wave-presets — 디머·컬러 웨이브 효과 프리셋 다섯 개(리드 초안 목록).

출하 fx 라이브러리의 틀(``dimmer.yaml`` · ``color.yaml``)에 한 주기 박 수를 얹어, 「All 1」
효과 풀(풀 21)의 빈 번호에 ``Store Preset 21.<n> '<이름>' /Universal`` 로 저장할 묶음을 낸다.

- 속도: 곡 BPM 을 ``Master 3.<speed_master> At BPM`` 으로 깔고, 한 주기 박 수를 ``At Measure`` 로
  ``At SpeedMaster <speed_master>`` 에 묶는다. 고정 ``At Speed`` 는 쓰지 않는다
  (움직임 효과와 같은 규칙).
- 위상: 틀의 ``Phase 0 Thru 360`` 은 저장할 때 고른 줄(선택)의 장비 순서로 나뉜다. 줄 번호는
  호출자가 준다 — 대본 리그 그룹 번호는 여기 없다.
- 콘솔 이름은 영문·숫자만(REQ-LDBEAT-015(d)). 화면에 보이는 이름만 한글이다.
- 한 번에 보낸다: 저장할 프리셋 전부가 **한 송신 묶음**(한 승인 카드)으로 나간다. 승인한 줄과
  나가는 줄이 같아야 하므로, 송신 직전 재확인도 묶음 전체에 한 번 건다.
- 이 모듈은 콘솔에 아무것도 보내지 않는다. 쓰기는 승인 카드 경로가 한다.
"""

from __future__ import annotations

import dataclasses
import functools
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from server.fx.instantiate import build_fx_preset_bundle
from server.fx.loader import load_library_from_dir
from server.fx.schema import Fx


@dataclass(frozen=True)
class WavePreset:
    display_name: str  # 화면에 보이는 이름(한글)
    console_label: str  # 콘솔 프리셋 이름(영문·숫자)
    fx_id: str  # 출하 fx 라이브러리의 틀
    beats: int  # 한 주기 박 수 — ``At Measure`` 로 간다
    kind: str  # "dimmer" | "color"


#: 리드 초안 목록 다섯 개. 틀은 출하 라이브러리에 이미 있는 것만 쓴다.
WAVE_PRESETS: tuple[WavePreset, ...] = (
    WavePreset("디머 웨이브 · 사인 1박", "WAVE DIM SINE 1B", "pulse-sine-breath", 1, "dimmer"),
    WavePreset("디머 웨이브 · 사인 2박", "WAVE DIM SINE 2B", "pulse-sine-breath", 2, "dimmer"),
    WavePreset("디머 웨이브 · 사인 4박", "WAVE DIM SINE 4B", "pulse-sine-breath", 4, "dimmer"),
    WavePreset("컬러 웨이브 · 무지개 2박", "WAVE COL RAINBOW 2B", "chase-rainbow-wave", 2, "color"),
    WavePreset("컬러 웨이브 · 웜쿨 2박", "WAVE COL WARMCOOL 2B", "chase-warm-cool", 2, "color"),
)


@dataclass(frozen=True)
class WaveWrite:
    """저장할 웨이브 프리셋 하나와 그 효과 풀 번호."""

    preset: WavePreset
    slot: int


def plan_wave_slots(occupied: Iterable[int], count: int) -> list[int]:
    """효과 풀에서 빈 번호 ``count`` 개를 작은 번호부터 고른다. 판독에 있는 번호는 찬 것이다."""
    taken = set(occupied)
    slots: list[int] = []
    number = 1
    while len(slots) < count:
        if number not in taken:
            slots.append(number)
        number += 1
    return slots


def plan_wave_writes(
    pool: Mapping[int, str | None],
) -> tuple[tuple[WaveWrite, ...], tuple[WavePreset, ...]]:
    """효과 풀 판독(``{번호: 이름}``)에서 저장할 것과 건너뛸 것을 가른다.

    같은 이름이 이미 있으면 건너뛴다. 이름이 같으면 「있다」로 보고, 내용은 확인하지 않는다
    (그래서 보고에 그 사실을 적는다). 저장할 것은 목록 순서대로 빈 번호의 작은 쪽부터 받는다.
    """
    existing = {name for name in pool.values() if name}
    pending = tuple(preset for preset in WAVE_PRESETS if preset.console_label not in existing)
    skipped = tuple(preset for preset in WAVE_PRESETS if preset.console_label in existing)
    slots = plan_wave_slots(pool.keys(), len(pending))
    writes = tuple(WaveWrite(preset, slot) for preset, slot in zip(pending, slots, strict=True))
    return writes, skipped


@functools.cache
def wave_templates() -> Mapping[str, Fx]:
    """출하 fx 라이브러리의 틀을 id 로 찾는다. 틀이 없으면 ``KeyError`` 를 낸다."""
    return {fx.fx_id: fx for fx in load_library_from_dir().fx}


def wave_master_line(bpm: float, speed_master: int) -> str:
    """곡 BPM 을 스피드 마스터에 깐다. 다섯 프리셋이 같이 쓰므로 묶음 맨 앞에 한 번만 낸다."""
    return f"Master 3.{speed_master} At BPM {bpm:g}"


def wave_preset_bundle(
    preset: WavePreset,
    fx: Fx,
    *,
    group_no: int,
    preset_pool: int,
    preset_slot: int,
    speed_master: int,
    selection: str | None = None,
) -> tuple[str, ...]:
    """웨이브 프리셋 하나의 저장 줄. 마스터 BPM 줄은 ``wave_save_commands`` 가 맨 앞에 낸다.

    고정 속도 대신 ``Measure`` · ``SpeedMaster`` 로 묶는다(틀의 ``speed`` 는 버린다).
    줄은 ``ChangeDestination Root`` · ``ClearAll`` 로 시작하고 ``ClearAll`` 로 끝나,
    앞뒤 프리셋의 programmer 상태가 섞이지 않는다. ``selection`` 이 있으면 ``Group`` 줄 대신 쓴다.
    """
    timed = dataclasses.replace(
        fx, speed=None, measure=float(preset.beats), speed_master=speed_master
    )
    bundle = build_fx_preset_bundle(
        timed,
        group=group_no,
        preset_pool=preset_pool,
        preset=preset_slot,
        label=preset.console_label,
        selection=selection,
    )
    return tuple(bundle.commands)


# @MX:NOTE: [AUTO] 저장 묶음은 한 번의 송신으로 보낸다(한 승인 카드).
#   같은 지시의 채팅 도구 호출을 여러 번 나누면 runner 가 넘기는 executed_ok 가 공통 줄
#   (ChangeDestination Root 등)을 skipped_already_executed 로 건너뛰고, Store 는 그대로 나가
#   프리셋이 조용히 빈다. 승인 카드 경로(_dispatch_declared)는 호출마다 빈 문맥이라 그 위험은 없다.
def wave_save_commands(
    writes: Iterable[WaveWrite],
    *,
    group_no: int,
    preset_pool: int,
    bpm: float,
    speed_master: int,
    selection: str | None = None,
) -> tuple[str, ...]:
    """저장할 웨이브 프리셋 전부를 한 송신 묶음으로. 마스터 BPM 줄은 맨 앞에 한 번만 있다.
    ``selection`` 은 줄의 선택 꼴(서브 광원 범위 ``Fixture a Thru b.``), 없으면 ``Group``."""
    templates = wave_templates()
    lines: list[str] = [wave_master_line(bpm, speed_master)]
    for write in writes:
        lines.extend(
            wave_preset_bundle(
                write.preset,
                templates[write.preset.fx_id],
                group_no=group_no,
                preset_pool=preset_pool,
                preset_slot=write.slot,
                speed_master=speed_master,
                selection=selection,
            )
        )
    return tuple(lines)
