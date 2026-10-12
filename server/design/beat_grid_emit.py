"""박자 격자 전용 콘솔 송신 커맨드 에미터 — SPEC-LDBEAT-001 M4 (카드 t549,
REQ-LDBEAT-001/003/011~013).

이 모듈은 콘솔에 아무것도 쓰지 않는다. 입력도 출력도 순수 파이썬 값뿐이다
(``server.design.beat_grid``·``server.design.app_movement``과 같은 모양).
장비 ID·콘솔 그룹 번호·프리셋 번호·초 단위 상수는 전부 **호출자가**
넘긴다(그 곡의 데이터 파일·실제 쇼 패치에서 왔다) — 이 모듈 코드 안에는
그런 리그·곡 전용 리터럴이 전혀 없다(REQ-LDBEAT-006(vi-6)와 같은 원칙).

이 에미터가 하는 일 넷:

1. **곡 템포로 마디 시작 시각 계산** (:class:`SongTiming`) — 저장 시점에
   초를 미리 계산해 두지 않는다. 1마디 다운비트(박 1)를 기준으로 호출
   시점에만 환산한다(REQ-LDBEAT-006(i-4)와 같은 "초 저장 금지" 원칙).
2. **트랙·칸 명령 생성** — ``songcue.py``가 이미 증명한 커맨드 모양
   (``Store Sequence``/``Store Timecode``/``Set … Property 'Name'``,
   ``_ascii_label``로 영문화)과 t520이 증명한 모양(``Store Sequence``/
   ``Go Timecode``/``Off``, 트랙 주소 배정
   ``Assign Sequence … At Timecode <tc>.1.<k>`` — ``k`` 는 그 타임코드의
   1부터 센 트랙 순번이고 ``Store Timecode <tc>.1`` 이 먼저 온다. 맨 꼴
   둘째 배정은 실기에서 거절됐다, 카드 t614)을 재사용해,
   역할별 시퀀스 여러 개 × 타임코드 트랙 여러 개의 다대다 배선을 짠다
   (REQ-LDBEAT-013(c)). 칸 내용은 ``app_movement``(앱 2단계 무빙,
   ``server.design.app_movement``)·정적 프리셋 리콜(``At Preset <no>``
   — M1 ③이 확인한, ``Attribute`` 접두 없는 형태)·``brightness_value_
   commands``(밝기 값)로 구성한다.
3. **REQ-LDBEAT-001 M1 의존 게이트** — 로드맵 §4가 적은 9개 미확인
   콘솔 항목(①~⑨, ``server.design.beat_grid_probes``) 중 하나라도 그
   칸·기능이 기대는 항목이 PASS로 확인되지 않았으면, 그 칸의 쓰기 전체를
   거절한다(부분 적용 0건). feature→항목 대응은 이 모듈 상수
   ``REQUIRED_M1_ITEM_*``에 명시적으로 적어 둔다 — **⑩⑪(디머 위상 펼침·
   t520 줄 순서 재현)은 REQ-LDBEAT-001 텍스트가 열거하는 9개 안에 없고
   ``beat_grid_probes.DEFAULT_PROBE_IDS``도 1~9만 추적한다**(그 모듈
   독스트링 "⑩⑪은 … 이 SPEC의 게이트 대상이 아니다" 참조) — 이 모듈은
   현재 디머 위상 펼침을 별도 기능으로 내지 않으므로 그 항목을 게이트
   대상에서 뺀 것이 결과에 영향을 주지 않는다(판단 근거는 run-verdict에
   기록).
4. **칸별 기존 검증 재사용** — ``check_app_movement_axis_conflict``(같은
   축 배타성, REQ-006(vi-7))·``check_evidence_approval``(프리셋 번호에는
   완전한 승인 필요, REQ-015(f)(g))을 그대로 호출한다 — 새 검증 로직을
   발명하지 않는다.

카드 t553(REQ-LDBEAT-006(vi)) — M1 게이트(항목 3)가 막아 둔 ⑤⑦⑨
(``app_movement``)는, ``server.design.beat_grid_measured``가 확인한
**측정된 무빙 허용목록**과 그 칸의 (그룹, 모양, 축)이 정확히 일치할
때만 선택적으로 열린다. progress.md M1 표 자체의 판정 문자열은 고치지
않는다(원래 표는 PRESERVE) — 더 구체적인 실기 증거(카드 t538·t548)를
별도 데이터 파일 하나로만 반영한다. "부분 적용 0건" 원칙은 유지:
매칭되지 않는 칸은 여전히 막힌다.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from server.design.app_movement import app_movement_commands, brightness_value_commands
from server.design.beat_grid import check_app_movement_axis_conflict, check_evidence_approval
from server.design.beat_grid_measured import is_movement_measured_open
from server.design.cue_fade import store_with_fade
from server.design.cue_sheet_apply import _tracking_command as _tracking_line
from server.looks.songcue import _ascii_label, _format_seconds

__all__ = [
    "MEASURED_MAX_TIMECODE_TRACKS",
    "BeatGridEmitResult",
    "CueEmitResult",
    "SongTiming",
    "TrackEmitResult",
    "beat_grid_sequence_label",
    "beat_grid_timecode_label",
    "blocked_m1_items_for_cue",
    "emit_beat_grid_write_bundle",
    "required_m1_items_for_cue",
]

#: REQ-LDBEAT-001의 게이트 대상 9항목 중 이 모듈이 실제로 참조하는 것들.
#: ④ 효과 프리셋이 스피드마스터·Measure를 지니는지 — 효과 프리셋 리콜은
#: 이 항목에 기댄다(배차서 지시 그대로 — 정적 리콜 자체가 아니라 "효과
#: 프리셋을 통한 박자 동기"가 미확인이라는 뜻으로 읽는다, 판단 근거는
#: run-verdict에 기록).
_EFFECT_PRESET_RECALL_ITEM = 4
#: ⑤ 위치 프리셋 위 상대값 · ⑦ 큐 하나에 Step 2 저장 · ⑨ circle·발리후·
#: wave 모양 — ``app_movement``의 두 단계 상대 페이저(``relative_wave_
#: lines``)는 내부적으로 ``Step 2``를 쓰고(⑦), wave 모양이고(⑨), 위치
#: 프리셋 위에 얹는 상대값 움직임이다(⑤). 셋 모두가 PASS여야 한다 — 하나만
#: 확인됐다고 느슨하게 풀지 않는다(배차서 "do not loosen the mapping").
_APP_MOVEMENT_ITEMS: frozenset[int] = frozenset({5, 7, 9})

#: progress.md M1 표의 판정 문자열 중 "PASS"로 보는 접두사 — "통과"·
#: "통과(구조)" 둘 다 이 접두사로 시작한다. "부분"·"미확인"·"움직임 없음"은
#: 이 접두사로 시작하지 않는다.
_M1_PASS_PREFIX = "통과"

#: 실기에서 잰 측정값 파일 — 타임코드 하나에 붙여 본 최대 트랙 수 등
#: (카드 t553). 값과 근거는 코드가 아니라 이 데이터 파일에 산다.
_MEASURED_CONSOLE_PATH = (
    Path(__file__).resolve().parent / "beat_grid_data" / "measured_console.yaml"
)


def _load_measured_max_timecode_tracks() -> int:
    with _MEASURED_CONSOLE_PATH.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)["max_timecode_tracks"]
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"max_timecode_tracks 가 양의 정수가 아닙니다: {value!r}")
    return value


#: ①이 구조로 확인한 실제 최대 트랙 수 — ①이 PASS라도 이 수를 넘는 묶음은
#: 측정 범위 밖이라 그 타임코드의 트랙 전부를 거절한다. 처음엔 t531의 6이었고
#: (카드 t549), 카드 t553 실기 되읽기(타임코드 32, 트랙 8)로 8이 됐다 —
#: 근거는 ``beat_grid_data/measured_console.yaml``.
MEASURED_MAX_TIMECODE_TRACKS = _load_measured_max_timecode_tracks()


def beat_grid_sequence_label(group_name: str, sequence_number: int) -> str:
    """``emit_beat_grid_write_bundle``이 그 트랙의 시퀀스에 실제로 쓰는
    ASCII 이름 — 재적용 소유권 비교(카드 t572, REQ-LDBEAT-011~013)가
    이 이름을 **다시 계산**하는 대신 이 함수를 그대로 불러 쓴다. 한
    자리에만 식을 두어, 에미터가 콘솔에 실제로 적은 이름과 소유권
    레코드가 기억하는 이름이 따로 적혀 어긋나는 일이 없게 한다."""
    return _ascii_label(f"LDBEAT {group_name}", fallback=f"Sequence {sequence_number}")


def beat_grid_timecode_label(timecode_number: int) -> str:
    """``emit_beat_grid_write_bundle``이 타임코드에 실제로 쓰는 ASCII
    이름 — :func:`beat_grid_sequence_label`과 같은 이유로 소유권 비교가
    재사용한다."""
    return _ascii_label(
        f"LDBEAT Timecode {timecode_number}", fallback=f"Timecode {timecode_number}"
    )


def required_m1_items_for_cue(cue: Mapping[str, object]) -> frozenset[int]:
    """이 칸이 쓰는 기능이 REQ-LDBEAT-001의 어느 M1 항목(들)에 기대는지.

    정적 프리셋 리콜(위치·색)과 디머 프리셋/값 지정 자체는 M1 9항목
    어디에도 기대지 않는다 — ③(프리셋 **수정** 전파)은 기존 프리셋 값을
    고치는 것에 대한 항목이고, 이 에미터는 수정이 아니라 번호 리콜만
    한다(M1 ③ 자신이 "``At Preset`` 접두 없는 형태는 콘솔이 받는다"를
    이미 구조로 확인했다)."""
    items: set[int] = set()
    if cue.get("effect_preset_no") is not None:
        items.add(_EFFECT_PRESET_RECALL_ITEM)
    movement = cue.get("app_movement")
    if isinstance(movement, Mapping) and movement.get("shape") is not None:
        items.update(_APP_MOVEMENT_ITEMS)
    return frozenset(items)


def _is_m1_item_confirmed(item: int, probe_results: Mapping[int, str]) -> bool:
    status = probe_results.get(item)
    if not status:
        return False
    return status.startswith(_M1_PASS_PREFIX)


def blocked_m1_items_for_cue(
    cue: Mapping[str, object],
    probe_results: Mapping[int, str],
    *,
    group_no: int | None = None,
) -> frozenset[int]:
    """``cue``가 기대는 M1 항목 중 ``probe_results``에서 PASS로 확인되지
    않은 것들 — 빈 집합이면 M1 게이트 통과.

    카드 t553(REQ-LDBEAT-006(vi)) — ``app_movement`` 항목(⑤⑦⑨)이 아직
    막혀 있어도, ``group_no``가 주어졌고 그 칸의 (그룹, 모양, 축)이
    ``beat_grid_measured.is_movement_measured_open``이 확인한 실기
    기록과 정확히 일치하면 그 세 항목만 막힘에서 뺀다 — progress.md의
    M1 표 판정 문자열 자체는 그대로 둔다(기록을 고치지 않는다). ⑤⑦⑨가
    애초에 막혀 있지 않았다면(이미 모두 PASS) 이 경로는 아무것도
    바꾸지 않는다 — "부분 적용 0건" 원칙상 매칭 안 되는 칸은 그대로
    막힌다."""
    required = required_m1_items_for_cue(cue)
    blocked = frozenset(item for item in required if not _is_m1_item_confirmed(item, probe_results))
    if not (blocked & _APP_MOVEMENT_ITEMS):
        return blocked
    movement = cue.get("app_movement")
    if not isinstance(movement, Mapping):
        return blocked
    if is_movement_measured_open(group_no, movement.get("shape"), movement.get("axes") or ()):
        return blocked - _APP_MOVEMENT_ITEMS
    return blocked


@dataclass(frozen=True)
class SongTiming:
    """곡 템포 — 호출자가 그 곡의 실제 값을 넘긴다(리그·곡 리터럴은
    이 모듈 코드에 0건, 전부 인자로 들어온다).

    ``downbeat_bar1_seconds``는 1마디 다운비트(박 1의 시작)의 음원 초 —
    다른 모든 마디의 시작 시각은 이 기준에서 BPM으로 호출 시점에
    계산한다(저장 시점 환산 없음). ``pickup_beats``는 0마디(못갖춘마디)의
    박 수 — 없으면 0마디 트리거는 계산할 수 없다(지어내지 않는다)."""

    bpm: float
    beats_per_bar: int
    downbeat_bar1_seconds: float
    pickup_beats: float | None = None

    def bar_start_seconds(self, bar: int) -> float | None:
        bpm_valid = self.bpm is not None and self.bpm > 0
        bar_valid = self.beats_per_bar is not None and self.beats_per_bar > 0
        if not (bpm_valid and bar_valid):
            return None
        seconds_per_beat = 60.0 / self.bpm
        if bar == 0:
            if self.pickup_beats is None:
                return None
            return self.downbeat_bar1_seconds - self.pickup_beats * seconds_per_beat
        return self.downbeat_bar1_seconds + (bar - 1) * self.beats_per_bar * seconds_per_beat


@dataclass(frozen=True)
class CueEmitResult:
    bar: int
    commands: tuple[str, ...]
    blocked_reason: str | None
    #: 카드 t563(REQ-LDBEAT-001/017) — 이 칸이 실제로 저장된 `Store Sequence
    #: <sequence_number> Cue <cue_number>` 번호. 거절되거나 낼 것이
    #: 없는 칸(``commands`` 빈 튜플)은 번호를 쓰지 않았으므로 `None`이다
    #: — 미리보기(`beat_grid_preview`)가 "이 마디를 담은 큐가 몇 번인지"를
    #: 커맨드 문자열을 되읽지 않고 바로 알 수 있게 한다(값을 지어내지 않음).
    cue_number: int | None = None
    #: 카드 t576 — 이 칸의 ``entry`` 중 보내지 않은 칸과 그 이유(실기 미확인·콘솔
    #: 값이 아님). 칸 자체는 나가고, 이 필드들만 빠진다.
    skipped_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class TrackEmitResult:
    group_name: str
    group_no: int | None
    sequence_number: int | None
    timecode_number: int | None
    #: 카드 t615 — 항상 비어 있다. 첫 큐 저장이 시퀀스를 만들고(카드 t612) 이름은 그 뒤에 붙는다.
    #: 저장되는 큐가 없는 트랙은 맨 Store Sequence 줄도 내지 않는다(빈 Cue 1 을 만든다).
    #: 필드는 소비자(beat_grid_send · web/session) 호환을 위해 남긴다.
    store_sequence_commands: tuple[str, ...]
    cues: tuple[CueEmitResult, ...]
    assign_timecode_commands: tuple[str, ...]
    blocked_reason: str | None

    @property
    def commands(self) -> tuple[str, ...]:
        cue_commands = tuple(line for cue in self.cues for line in cue.commands)
        return self.store_sequence_commands + cue_commands + self.assign_timecode_commands


@dataclass(frozen=True)
class BeatGridEmitResult:
    tracks: tuple[TrackEmitResult, ...]
    blocked_reason: str | None
    timecode_setup_commands: tuple[str, ...] = field(default_factory=tuple)

    @property
    def commands(self) -> tuple[str, ...]:
        if self.blocked_reason is not None:
            return ()
        track_commands = tuple(line for track in self.tracks for line in track.commands)
        return self.timecode_setup_commands + track_commands

    @property
    def blocked_cells(self) -> tuple[tuple[str, int, str], ...]:
        """(트랙 이름, 마디, 거절 사유) — 카드 t549 run-verdict가 인용할
        "어느 LOVE ATTACK 칸/트랙이 게이트로 막혔는가" 전수 목록."""
        return tuple(
            (track.group_name, cue.bar, cue.blocked_reason)
            for track in self.tracks
            for cue in track.cues
            if cue.blocked_reason is not None
        )


def _cue_attribute_commands(
    cue: Mapping[str, object],
    *,
    group_name: str,
    group_no: int,
    timing: SongTiming,
    dimmer_attributes: Mapping[str, Sequence[str]],
    dimmer_attribute_reasons: Mapping[str, str] | None = None,
) -> tuple[tuple[str, ...], str | None]:
    """칸 내용(선택+속성 설정) 줄만 — ``Store Cue``/트리거 시각 줄은 뺀다.
    ``(명령 튜플, 사유)`` — 사유가 있으면 명령은 항상 빈 튜플이다(부분
    적용 0건)."""
    selection = f"Group {group_no}"
    commands: list[str] = []

    movement = cue.get("app_movement")
    position_preset_no = cue.get("position_preset_no")
    has_movement = isinstance(movement, Mapping) and movement.get("shape") is not None
    if has_movement:
        move_commands, reason = app_movement_commands(
            movement,  # type: ignore[arg-type]
            group_no=group_no,
            position_preset_no=position_preset_no,  # type: ignore[arg-type]
            bpm=timing.bpm,
            beats_per_bar=timing.beats_per_bar,
        )
        if reason is not None:
            return (), reason
        commands.extend(move_commands)
    elif position_preset_no is not None:
        commands.append(f"{selection} ; At Preset {position_preset_no}")

    color_preset_no = cue.get("color_preset_no")
    if color_preset_no is not None:
        commands.append(f"{selection} ; At Preset {color_preset_no}")

    effect_preset_no = cue.get("effect_preset_no")
    if effect_preset_no is not None:
        commands.append(f"{selection} ; At Preset {effect_preset_no}")

    brightness = cue.get("brightness")
    brightness = brightness if isinstance(brightness, Mapping) else {}
    mode = brightness.get("mode")
    if mode == "value":
        value_percent = brightness.get("value_percent")
        if value_percent is None:
            return (), "brightness.mode == 'value' 인데 value_percent 가 없습니다(지어내지 않음)"
        attrs = dimmer_attributes.get(group_name) or ()
        if not attrs:
            # 카드 t573 — 호출자가 왜 못 골랐는지 알면 그 사유를 그대로 쓴다.
            specific = (dimmer_attribute_reasons or {}).get(group_name)
            if specific:
                return (), specific
            return (), (
                f"'{group_name}' 트랙의 디머 속성 목록이 없어 밝기 값을 낼 수 "
                "없습니다(dimmer_attributes 누락)"
            )
        commands.extend(
            brightness_value_commands(
                group_no=group_no, value_percent=value_percent, dimmer_attributes=attrs
            )
        )
    elif mode in ("dimmer_preset", "dimmer_effect"):
        preset_no = brightness.get("preset_no")
        if preset_no is None:
            return (), f"brightness.mode == {mode!r} 인데 preset_no 가 없습니다(지어내지 않음)"
        commands.append(f"{selection} ; At Preset {preset_no}")

    return tuple(commands), None


@dataclass(frozen=True)
class _EntryPlan:
    fade_seconds: float | None = None
    trigger_offset_seconds: float = 0.0
    store_options: tuple[str, ...] = ()
    after_ops: tuple[str, ...] = ()
    skipped_fields: tuple[str, ...] = ()
    blocked_reason: str | None = None


#: 카드 t576 — 보내지 않는 ``entry`` 칸과 그 이유. 둘은 콘솔 문법이 저장소에 실기로
#: 확인된 선례가 없고(t580 실기 확인 목록), MIB 는 콘솔 값이 아니다 — 큐시트 반영
#: (``cue_sheet_apply.UNSOURCED_FIELD_REASONS["mib_mode"]``)이 같은 이유로 안 보낸다.
_UNSENT_ENTRY_REASONS: Mapping[str, str] = {
    "delay_beats": (
        "delay_beats(속성별 늦은 적용)는 콘솔 문법을 실기로 확인한 적이 없어 보내지 "
        "않습니다(t580 실기 확인 뒤)"
    ),
    "position_late_beats": (
        "position_late_beats(위치만 따로 늦게)는 콘솔 문법을 실기로 확인한 적이 없어 "
        "보내지 않습니다(t580 실기 확인 뒤)"
    ),
    "mib_mode": (
        "mib_mode 는 콘솔 큐 값이 아닙니다 — 이 저장소의 MIB 는 앱이 어둠 속 사전이동 "
        "큐를 직접 넣는 방식이라(cue_sheet_apply 와 같은 판단) 큐 속성으로 보내지 않습니다"
    ),
}


def _entry_plan(entry: object, timing: SongTiming) -> _EntryPlan:
    """카드 t576 — 칸의 전환 ``entry``(음악 단위)를 이번 송신의 콘솔 큐 속성으로.

    초는 **여기서만**, 그 곡 BPM 으로 계산한다 — ``entry``에는 초가 저장되지 않는다
    (REQ-LDBEAT-006(i-4)). 문면은 저장소 실기 선례만 쓴다:

    * 페이드 ``fade_bars``/``fade_beats`` → ``Store … CueFade <초>``
      (:func:`server.design.cue_fade.store_with_fade`). 둘이 동시에 숫자면 막는다.
    * 트리거 ``trigger_beat``(1~마디당 박) → ``TrigTime`` 을 마디 안에서 그만큼 미룬다.
    * 트래킹 ``tracking`` → Release·Block 은 저장 뒤 명령, Cue Only 는 저장 옵션
      (``cue_sheet_apply._tracking_command``·``/CueOnly``, 카드 t469). Track 은 기본값이라
      아무것도 보내지 않는다.
    * ``delay_beats``·``position_late_beats``·``mib_mode`` → 보내지 않고 이유를 단다.

    ``entry``가 없거나 전부 미정이면 :class:`_EntryPlan` 기본값 — 그때 칸의 명령은
    이 함수가 생기기 전과 바이트 동일하다."""
    if not isinstance(entry, Mapping):
        return _EntryPlan()
    seconds_per_beat = 60.0 / timing.bpm

    fade_bars = entry.get("fade_bars")
    fade_beats = entry.get("fade_beats")
    if fade_bars is not None and fade_beats is not None:
        return _EntryPlan(
            blocked_reason=(
                "fade_bars 와 fade_beats 가 둘 다 숫자입니다 — 어느 쪽인지 짐작해서 보내지 않습니다"
            )
        )
    fade_seconds: float | None = None
    if fade_bars is not None:
        fade_seconds = float(fade_bars) * timing.beats_per_bar * seconds_per_beat
    elif fade_beats is not None:
        fade_seconds = float(fade_beats) * seconds_per_beat

    trigger_beat = entry.get("trigger_beat")
    trigger_offset = 0.0
    if trigger_beat is not None:
        if (
            isinstance(trigger_beat, bool)
            or not isinstance(trigger_beat, int)
            or not 1 <= trigger_beat <= timing.beats_per_bar
        ):
            return _EntryPlan(
                blocked_reason=(
                    f"trigger_beat {trigger_beat!r} 는 1~{timing.beats_per_bar} 박이어야 "
                    "합니다(지어내지 않음)"
                )
            )
        trigger_offset = (trigger_beat - 1) * seconds_per_beat

    tracking = entry.get("tracking")
    store_options: tuple[str, ...] = ()
    after_ops: tuple[str, ...] = ()
    if tracking == "Release":
        after_ops = ("release_on",)
    elif tracking == "Block":
        after_ops = ("block",)
    elif tracking == "Cue Only":
        store_options = ("/CueOnly",)

    skipped = tuple(
        reason
        for name, reason in _UNSENT_ENTRY_REASONS.items()
        if entry.get(name) is not None and not (name == "mib_mode" and entry.get(name) == "none")
    )
    return _EntryPlan(
        fade_seconds=fade_seconds,
        trigger_offset_seconds=trigger_offset,
        store_options=store_options,
        after_ops=after_ops,
        skipped_fields=skipped,
    )


def _emit_cue(
    cue: Mapping[str, object],
    *,
    group_name: str,
    group_no: int,
    sequence_number: int,
    cue_number: int,
    timing: SongTiming,
    probe_results: Mapping[int, str],
    dimmer_attributes: Mapping[str, Sequence[str]],
    dimmer_attribute_reasons: Mapping[str, str] | None = None,
    sequence_name_command: str | None = None,
) -> CueEmitResult:
    bar = int(cue["bar"])  # type: ignore[arg-type]

    blocked = blocked_m1_items_for_cue(cue, probe_results, group_no=group_no)
    if blocked:
        listed = ", ".join(str(item) for item in sorted(blocked))
        reason = f"미확인 항목 {len(blocked)}개({listed}) — REQ-LDBEAT-001 게이트"
        return CueEmitResult(bar=bar, commands=(), blocked_reason=reason)

    axis_conflict = check_app_movement_axis_conflict(cue)
    if axis_conflict is not None:
        return CueEmitResult(bar=bar, commands=(), blocked_reason=axis_conflict)

    evidence_reason = check_evidence_approval(cue)
    if evidence_reason is not None:
        return CueEmitResult(bar=bar, commands=(), blocked_reason=evidence_reason)

    attribute_commands, reason = _cue_attribute_commands(
        cue,
        group_name=group_name,
        group_no=group_no,
        timing=timing,
        dimmer_attributes=dimmer_attributes,
        dimmer_attribute_reasons=dimmer_attribute_reasons,
    )
    if reason is not None:
        return CueEmitResult(bar=bar, commands=(), blocked_reason=reason)
    if not attribute_commands:
        return CueEmitResult(bar=bar, commands=(), blocked_reason=None)

    bar_seconds = timing.bar_start_seconds(bar)
    if bar_seconds is None:
        return CueEmitResult(
            bar=bar,
            commands=(),
            blocked_reason="이 마디의 트리거 시각을 계산할 수 없습니다(0마디 pickup_beats 없음)",
        )

    entry_plan = _entry_plan(cue.get("entry"), timing)
    if entry_plan.blocked_reason is not None:
        return CueEmitResult(bar=bar, commands=(), blocked_reason=entry_plan.blocked_reason)

    commands = list(attribute_commands)
    # 카드 t612 — 어순을 실기 선례대로 ``Store Sequence S Cue N``으로 고쳤다. 옛 어순
    #   ``Store Cue N Sequence S``는 t608 실행(run-1012 index 33)에서 콘솔이
    #   ``User Canceled Command``로 거절했다. ``CueFade``·``/CueOnly``는 cue_sheet_apply의
    #   실측 순서(``Store Sequence S Cue N CueFade x /Merge``)를 따른다.
    # @MX:WARN: [AUTO] 이 어순은 선례(t531 · cue_sheet_apply)와 같지만, 이 에미터가 낸
    #   줄을 실기에서 받았다는 확인은 아직 없다 — 첫 큐 저장이 시퀀스를 만드는 것도 이 줄이다.
    # @MX:REASON: 다음 실기 접속에서 run 의 첫 큐 줄(시퀀스 생성)을 먼저 확인한다. 거절되면
    #   이 줄의 어순만 다시 고친다(초 환산·트리거·트래킹 판정은 그대로).
    store = store_with_fade(
        f"Store Sequence {sequence_number} Cue {cue_number}", entry_plan.fade_seconds
    )
    commands.append(store + "".join(f" {option}" for option in entry_plan.store_options))
    if sequence_name_command is not None:
        # 카드 t612 — 실기 선례(t531)대로 이름은 큐 저장 바로 뒤에 건다.
        commands.append(sequence_name_command)
    commands.append("ClearAll")
    commands.append(f"Set Cue {cue_number} Sequence {sequence_number} Property 'TrigType' 'Time'")
    trigger_ms = round((bar_seconds + entry_plan.trigger_offset_seconds) * 1000)
    commands.append(
        f"Set Cue {cue_number} Sequence {sequence_number} Property 'TrigTime' "
        f"{_format_seconds(trigger_ms)}"
    )
    # 트래킹 표시는 큐가 저장된 **뒤에** 건다(cue_sheet_apply 실측 순서, 카드 t469).
    commands.extend(_tracking_line(op, sequence_number, cue_number) for op in entry_plan.after_ops)
    return CueEmitResult(
        bar=bar,
        commands=tuple(commands),
        blocked_reason=None,
        cue_number=cue_number,
        skipped_fields=entry_plan.skipped_fields,
    )


def _blocked_track(
    track: Mapping[str, object],
    *,
    sequence_numbers: Mapping[str, int],
    timecode_numbers: Mapping[str, int],
    reason: str,
) -> TrackEmitResult:
    group_name = str(track["group_name"])
    return TrackEmitResult(
        group_name=group_name,
        group_no=track.get("group_no"),  # type: ignore[arg-type]
        sequence_number=sequence_numbers.get(group_name),
        timecode_number=timecode_numbers.get(group_name),
        store_sequence_commands=(),
        cues=(),
        assign_timecode_commands=(),
        blocked_reason=reason,
    )


def emit_beat_grid_write_bundle(
    tracks: Sequence[Mapping[str, object]],
    *,
    timing: SongTiming | None,
    sequence_numbers: Mapping[str, int],
    timecode_numbers: Mapping[str, int],
    dimmer_attributes: Mapping[str, Sequence[str]],
    probe_results: Mapping[int, str],
    recorded_cue_numbers: Mapping[str, Mapping[int, int]] | None = None,
    dimmer_attribute_reasons: Mapping[str, str] | None = None,
    held_cells: Mapping[tuple[str, int], str] | None = None,
) -> BeatGridEmitResult:
    """박자 격자 트랙 목록 → 콘솔 송신 커맨드 번들. 콘솔 접촉 0건 — 전부
    순수 변환이다.

    카드 t572 — ``recorded_cue_numbers``(트랙 이름 -> {마디: 큐 번호})는
    다시 반영할 때 이 앱이 직전에 쓴 번호표다. 표에 있는 마디는 그 번호를
    그대로 쓰고, 표에 없는 새 마디는 그 트랙에 기록된 최대 번호 다음
    정수부터 받는다. 그래서 어떤 칸이 막혀도 뒤 칸들의 번호가 당겨지지
    않는다(당겨지면 막힌 칸의 옛 큐가 덮어써진다). 생략하면(첫 반영)
    지금까지처럼 1부터 차례로 매긴다.

    ``sequence_numbers``/``timecode_numbers``/``dimmer_attributes``는
    트랙 ``group_name``을 키로 하는, 호출자가 그 곡·그 쇼에서 결정한
    값이다(이 모듈은 번호를 지어내지 않는다). ``probe_results``는
    ``server.design.beat_grid_probes.read_m1_probe_results*``가 돌려주는
    것을 그대로 받는다(REQ-LDBEAT-003(b) — 이 모듈은 progress.md를 직접
    읽지 않는다, 호출자가 읽어 넘긴다).

    카드 t600 — ``held_cells``((트랙 이름, 마디) -> 사유)는 호출자가 콘솔 풀을
    읽어 송신 보류로 가른 칸이다(빈 프리셋·풀 못 읽음, REQ-LDBEAT-015(i-1)). 승인된
    칸이라도 커맨드 0줄로 막고 큐 번호를 쓰지 않는다(거절된 칸과 같다)."""
    if (
        timing is None
        or timing.bpm is None
        or timing.bpm <= 0
        or timing.beats_per_bar is None
        or timing.beats_per_bar <= 0
    ):
        return BeatGridEmitResult(
            tracks=(),
            blocked_reason="곡 타이밍(bpm/beats_per_bar/기준 초)이 없어 전체 배치를 거절합니다",
        )

    timecode_groups: dict[int, list[str]] = {}
    for track in tracks:
        group_name = str(track["group_name"])
        timecode_number = timecode_numbers.get(group_name)
        if timecode_number is not None:
            timecode_groups.setdefault(timecode_number, []).append(group_name)

    over_limit_groups: set[str] = {
        name
        for names in timecode_groups.values()
        if len(names) > MEASURED_MAX_TIMECODE_TRACKS
        for name in names
    }

    track_results: list[TrackEmitResult] = []
    used_timecode_numbers: set[int] = set()
    # 카드 t614 — 타임코드별로 지금까지 실제 배정된 트랙 수(배정 줄의 트랙 순번 k).
    assigned_track_counts: dict[int, int] = {}

    for track in tracks:
        group_name = str(track["group_name"])

        if group_name in over_limit_groups:
            timecode_number = timecode_numbers.get(group_name)
            track_count = len(timecode_groups.get(timecode_number, []))
            reason = (
                f"타임코드 {timecode_number}에 트랙 {track_count}개 — ①이 구조로 확인한 "
                f"최대 {MEASURED_MAX_TIMECODE_TRACKS}개"
                "(beat_grid_data/measured_console.yaml)를 넘습니다"
            )
            track_results.append(
                _blocked_track(
                    track,
                    sequence_numbers=sequence_numbers,
                    timecode_numbers=timecode_numbers,
                    reason=reason,
                )
            )
            continue

        if not track.get("group_no_confirmed"):
            track_results.append(
                _blocked_track(
                    track,
                    sequence_numbers=sequence_numbers,
                    timecode_numbers=timecode_numbers,
                    reason="그룹 번호가 아직 확인되지 않았습니다(group_no_confirmed=False)",
                )
            )
            continue

        sequence_number = sequence_numbers.get(group_name)
        if sequence_number is None:
            track_results.append(
                _blocked_track(
                    track,
                    sequence_numbers=sequence_numbers,
                    timecode_numbers=timecode_numbers,
                    reason=f"'{group_name}' 트랙에 시퀀스 번호가 지정되지 않았습니다",
                )
            )
            continue

        timecode_number = timecode_numbers.get(group_name)
        if timecode_number is None:
            track_results.append(
                _blocked_track(
                    track,
                    sequence_numbers=sequence_numbers,
                    timecode_numbers=timecode_numbers,
                    reason=f"'{group_name}' 트랙에 타임코드 번호가 지정되지 않았습니다",
                )
            )
            continue

        group_no = track.get("group_no")
        ascii_name = beat_grid_sequence_label(group_name, sequence_number)
        name_command = f"Set Sequence {sequence_number} Property 'Name' '{ascii_name}'"

        raw_cues = track.get("cues") or []
        cues_sorted = sorted(raw_cues, key=lambda c: int(c["bar"]))  # type: ignore[index]
        cue_results: list[CueEmitResult] = []
        recorded = (recorded_cue_numbers or {}).get(group_name) or {}
        next_cue_number = max(recorded.values(), default=0) + 1
        # 카드 t612 — 첫 큐 저장이 시퀀스를 만들고, 이름은 그 저장 바로 뒤에 붙는다.
        name_pending = True
        for cue in cues_sorted:
            # cue_number 는 "실제로 내용이 있는 칸"에만 매긴다 — 거절되거나
            # 공백인 칸은 새 번호를 쓰지 않는다(아래 조건부 증가). 기록된
            # 마디는 기록된 번호를 그대로 쓴다(카드 t572).
            bar = int(cue["bar"])  # type: ignore[index]
            hold_reason = (held_cells or {}).get((group_name, bar))
            if hold_reason is not None:
                cue_results.append(CueEmitResult(bar=bar, commands=(), blocked_reason=hold_reason))
                continue
            recorded_number = recorded.get(bar)
            result = _emit_cue(
                cue,
                group_name=group_name,
                group_no=group_no,  # type: ignore[arg-type]
                sequence_number=sequence_number,
                cue_number=recorded_number if recorded_number is not None else next_cue_number,
                timing=timing,
                probe_results=probe_results,
                dimmer_attributes=dimmer_attributes,
                dimmer_attribute_reasons=dimmer_attribute_reasons,
                sequence_name_command=name_command if name_pending else None,
            )
            if result.commands:
                name_pending = False
            if result.commands and recorded_number is None:
                next_cue_number += 1
            cue_results.append(result)

        # 카드 t615 — 저장되는 큐가 하나도 없는 트랙은 시퀀스·이름·배정·타임코드를 내지 않는다.
        # 맨 Store Sequence 줄은 빈 Cue 1 을 만들고(실기 판별: .moai/reports/t615/live/), 그 번호에
        # 나중에 큐를 저장하면 콘솔이 User Canceled Command 로 멈춘다. 칸별 사유는 그대로 남긴다.
        assign_timecode_commands: tuple[str, ...] = ()
        if not name_pending:
            used_timecode_numbers.add(timecode_number)
            # 카드 t614 — 맨 꼴 ``At Timecode N`` 은 같은 타임코드의 둘째 트랙부터 콘솔이
            #   ``Illegal object`` 로 거절했다(t608 v2 S1b). 실기 선례(t520 · t506 · t553)대로
            #   트랙 주소 ``N.1.k`` 로 배정한다 — 1 은 트랙 그룹, k 는 이 타임코드에서 실제로
            #   배정된 트랙의 1부터 센 순번이다. 막혀서 여기 닿지 못한 트랙은 순번을 쓰지 않는다.
            #   카드 t615 — 저장 큐가 없는 트랙도 여기 닿지 않으므로 순번을 쓰지 않는다.
            track_index = assigned_track_counts.get(timecode_number, 0) + 1
            assigned_track_counts[timecode_number] = track_index
            assign_timecode_commands = (
                f"Assign Sequence {sequence_number} At Timecode {timecode_number}.1.{track_index}",
            )

        track_results.append(
            TrackEmitResult(
                group_name=group_name,
                group_no=group_no,  # type: ignore[arg-type]
                sequence_number=sequence_number,
                timecode_number=timecode_number,
                # 첫 큐 저장이 시퀀스를 만들고 이름은 그 칸 줄에 붙는다(카드 t612) — 맨 줄은 없다.
                store_sequence_commands=(),
                cues=tuple(cue_results),
                assign_timecode_commands=assign_timecode_commands,
                blocked_reason=None,
            )
        )

    timecode_setup_commands: list[str] = []
    for timecode_number in sorted(used_timecode_numbers):
        name = beat_grid_timecode_label(timecode_number)
        timecode_setup_commands.append(f"Store Timecode {timecode_number}")
        timecode_setup_commands.append(f"Set Timecode {timecode_number} Property 'Name' '{name}'")
        # 카드 t614 — 트랙 주소 ``N.1.k`` 의 트랙 그룹 1 을 배정 줄보다 먼저 만든다
        #   (실기 선례 t520: ``Store Timecode 24.1`` → ``Assign … 24.1.1`` / ``24.1.2``).
        timecode_setup_commands.append(f"Store Timecode {timecode_number}.1")

    return BeatGridEmitResult(
        tracks=tuple(track_results),
        blocked_reason=None,
        timecode_setup_commands=tuple(timecode_setup_commands),
    )
