"""박자 격자 M4 — 콘솔 송신 입력 소스 결정 헬퍼 (카드 t563, SPEC-LDBEAT-001
REQ-LDBEAT-011~013/017).

``beat_grid_emit.emit_beat_grid_write_bundle``가 요구하는 네 입력
(``sequence_numbers``·``timecode_numbers``·``dimmer_attributes``·
``timing``) 중 세 개를 **콘솔에서 읽거나 이미 읽은 값에서 순수 변환**해
만든다(타임코드 번호 하나는 director 입력이라 이 모듈이 아니라
``server/web/session.py``가 직접 다룬다 — 그 판정만
``server.orchestrator.tools.timecode_slot_verdict``를 그대로 재사용한다,
이 모듈에서 재사용하면 ``tools.py`` -> ``server.design`` -> 이 모듈 ->
``tools.py``의 순환 임포트가 생긴다).

콘솔 쓰기 0건 — 이 모듈 자체는 읽기 질의조차 하지 않는다(``sequences_
section``·``design_rig``·``bar_map``을 호출자가 이미 읽어 넘긴다). 리그·
곡 전용 숫자(그룹 번호·프리셋 번호·초 단위 상수)는 이 모듈 코드에 전혀
없다 — 전부 인자로 들어온다(``beat_grid_emit`` 모듈 독스트링과 같은 원칙).

카드 t572(REQ-LDBEAT-011~013) — 재적용(두 번째 이후 「콘솔에 반영」)의
소유권 확인(:func:`verify_owned_sequences`)과 이미 쓴 번들의 가지치기
(:func:`apply_beat_grid_ownership_reuse`)도 이 모듈에 둔다 — 둘 다 이미
읽은 섹션·이미 낸 ``BeatGridEmitResult``의 순수 변환이다(콘솔 접촉 0건).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import replace

from server.design.app_movement import dimmer_attribute_names
from server.design.beat_grid_emit import BeatGridEmitResult, SongTiming
from server.design.rig_capability_read import DesignRigRead
from server.looks.songcue import SequenceNumberError, select_sequence_number

__all__ = [
    "BeatGridCellKey",
    "apply_beat_grid_ownership_reuse",
    "clear_app_timecode_before_rebuild",
    "song_end_seconds_from_bar_map",
    "beat_grid_cell_snapshot",
    "beat_grid_reapply_summary",
    "build_song_timing_from_bar_map",
    "dimmer_unread_notices",
    "pick_sequence_numbers",
    "resolve_dimmer_attributes",
    "timecode_overwrite_note",
    "resolve_group_dimmer_attributes",
    "unsent_beat_grid_cells",
    "verify_owned_sequences",
]

#: (group_name, bar) — ``apply_beat_grid_edit``의 ``target``/``bar``와 같은
#: 이름(``server/design/beat_grid_edit.py``) 그대로다. 새 식별 체계를 짓지
#: 않는다(코디네이터 계약, t568과 합의).
BeatGridCellKey = tuple[str, int]

#: ``select_sequence_number``/``_sequence_numbers``가 던지는 코드 문자열을
#: 감독이 읽을 한국어 사유로 바꾼다 — 코드 자체는 두 모듈(이 파일과
#: ``server/fx/instantiate.py``)이 이미 상수로 고정했으므로 여기서는 매핑만
#: 한다(새 분류 로직을 발명하지 않는다).
_SEQUENCE_REASON_MESSAGES: Mapping[str, str] = {
    "sequence_unavailable": "시퀀스 풀을 콘솔에서 읽지 못해 번호를 고를 수 없습니다",
    "sequence_truncated": "시퀀스 풀 읽기가 잘려 빈 번호를 확신할 수 없습니다",
    "sequence_number_unavailable": "시퀀스 풀의 한 항목에 번호가 없어 점유 여부를 알 수 없습니다",
}


def _sequence_reason(error: SequenceNumberError) -> str:
    code = str(error)
    return _SEQUENCE_REASON_MESSAGES.get(code, code)


def _listed_key(section: Mapping[str, object]) -> str | None:
    """``select_sequence_number``/``_sequence_numbers``가 읽는 두 가능한
    키(``objects`` 우선, 없으면 ``children``) 중 이 섹션이 실제로 쓴 쪽."""
    if isinstance(section.get("objects"), list):
        return "objects"
    if isinstance(section.get("children"), list):
        return "children"
    return None


def pick_sequence_numbers(
    sequences_section: Mapping[str, object], group_names: Sequence[str]
) -> tuple[dict[str, int], str | None]:
    """트랙(``group_names``)마다 **서로 다른** 시퀀스 번호를 순차로 고른다.

    ``select_sequence_number``의 점유 판정 자체는 건드리지 않는다 —
    매 트랙을 고를 때마다 그 섹션의 복사본에 **지금까지 고른 번호들**을
    점유 중인 자식으로 덧붙여 넘길 뿐이다(배차서 지시: "이미 선택된 번호를
    점유 집합에 더해 다음 트랙을 고른다"). 풀 자체를 못 읽거나(truncated
    포함) 한 항목에 번호가 없으면 **배치 전체**를 그 사유로 거절한다 —
    일부 트랙만 번호를 받는 부분 적용은 없다.

    ``group_names``가 비어 있으면 (``{}``, ``None``) — 고를 트랙이 없다는
    것은 거절이 아니다."""
    if not group_names:
        return {}, None
    key = _listed_key(sequences_section)
    if key is None:
        # select_sequence_number 자신이 "objects"/"children" 둘 다 없으면
        # SEQUENCE_UNAVAILABLE 을 던진다 — 같은 사유 문자열을 재사용한다.
        try:
            select_sequence_number(sequences_section)
        except SequenceNumberError as error:
            return {}, _sequence_reason(error)
        # select_sequence_number 가 예외 없이 끝났는데 key 가 없다는 것은
        # 이 함수의 전제가 깨졌다는 뜻 — 발생하지 않지만 지어내지 않는다.
        return {}, _SEQUENCE_REASON_MESSAGES["sequence_unavailable"]

    base_listed = list(sequences_section[key])  # type: ignore[index]
    chosen: dict[str, int] = {}
    for name in group_names:
        working = dict(sequences_section)
        working[key] = base_listed + [{"no": number} for number in chosen.values()]
        try:
            chosen[name] = select_sequence_number(working)
        except SequenceNumberError as error:
            return {}, _sequence_reason(error)
    return chosen, None


def resolve_dimmer_attributes(
    design_rig: DesignRigRead, group_names: Sequence[str]
) -> dict[str, tuple[str, ...]]:
    """리그 판독이 **전수**이고, 패치된 **모든** 기구 타입이 동일한 디머
    속성 튜플을 낼 때만 그 튜플을 모든 트랙에 쓴다.

    콘솔에 그룹 소속(어느 기구가 어느 콘솔 그룹인가)을 읽는 함수가 없다
    (t525 실측 — ``SELECTIONDATA``뿐이고 서버엔 그 판독기가 없다). 그룹은
    패치의 부분집합이므로, 패치 전체가 같은 디머 속성을 갖는다면 그
    교집합은 어느 그룹에 대해서도 맞다 — 그 반대(기구 타입마다 디머
    속성이 다름)는 어느 그룹이 어느 타입인지 모르는 채로는 안전하게 못
    쓰므로 **아무 것도 내주지 않는다**(부분 적용 없음 — 이 칸만 디머 속성
    부재로 막히게 두고, 틀린 속성을 지어내지 않는다)."""
    if not design_rig.whole or design_rig.capabilities is None:
        return {}
    capabilities = design_rig.capabilities
    if capabilities.unread or capabilities.incomplete:
        return {}
    tuples_by_type: dict[str, tuple[str, ...]] = {}
    for capability in capabilities.fixtures.values():
        if not capability.whole:
            return {}
        dimmer = dimmer_attribute_names(capability.attributes)
        existing = tuples_by_type.get(capability.type_name)
        if existing is not None and existing != dimmer:
            return {}
        tuples_by_type[capability.type_name] = dimmer
    distinct = set(tuples_by_type.values())
    if len(distinct) != 1:
        return {}
    (uniform,) = distinct
    if not uniform:
        return {}
    return {name: uniform for name in group_names}


#: 디머 속성을 「아직 읽지 않았다」로 막힌 사유의 표식. :func:`resolve_group_dimmer_attributes`
#: 가 쓰는 사유 가운데 판독이 빠진 쪽에만 든다("읽지 못해"·"다 읽지 못했고"). 기종이
#: 섞인 그룹("섞여 있어")은 읽기는 끝났으므로 여기 들지 않는다.
_DIMMER_UNREAD_MARKS: tuple[str, ...] = ("읽지 못해", "다 읽지 못했고")


def dimmer_unread_notices(blocked_cells: Sequence[tuple[str, int, str]]) -> list[str]:
    """미리보기 안내 — 디머 속성 판독이 없어 막힌 칸을 한 줄로 센다.

    ``blocked_cells``는 ``(트랙 이름, 마디, 사유)`` 전수 목록이다. 사유에 판독 부재 표식이
    있는 칸만 세어 「이 장비는 밝기 정보를 아직 읽지 않았어요 — N칸 제외」 한 줄을 낸다.
    목록 자체는 건드리지 않는다 — 칸별 사유는 그대로 남고, 나머지 칸은 그대로 나간다."""
    unread = [
        cell for cell in blocked_cells if any(mark in cell[2] for mark in _DIMMER_UNREAD_MARKS)
    ]
    if not unread:
        return []
    return [f"이 장비는 밝기 정보를 아직 읽지 않았어요 — {len(unread)}칸 제외"]


def resolve_group_dimmer_attributes(
    design_rig: DesignRigRead,
    group_names: Sequence[str],
    group_members: Mapping[str, Sequence[int]],
) -> tuple[dict[str, tuple[str, ...]], dict[str, str]]:
    """트랙(콘솔 그룹)마다 디머 속성을 고른다 — ``(속성 표, 못 고른 사유 표)``.

    카드 t573(REQ-LDBEAT-011~013). ``group_members``는 그룹 이름 -> 소속
    fid 목록으로, :func:`server.design.beat_grid_stage.read_beat_grid_stage`가
    읽은 ``member_fids`` 중 **전수(complete)** 로 읽힌 그룹만 담아 넘긴다
    (호출자 몫 — 부분 소속은 넣지 않는다). 기종 이름·속성 이름은 이
    함수에 하나도 없다 — 전부 리그 판독(``FixtureCapability.attributes``)에서
    :func:`dimmer_attribute_names`로 걸러 온다.

    한 그룹의 규칙:

    - 소속을 안다 → 소속 장비 **전부**의 능력이 전수로 읽혀 있고, 모두 같은
      (비지 않은) 디머 속성 튜플을 내면 그 튜플. 소속 장비 하나라도 능력을
      못 읽었거나, 장비끼리 디머 속성이 다르면(섞인 그룹) 고르지 않는다 —
      섞인 그룹에 합집합을 내는 것은 실기로 잰 적이 없어 지어내지 않는다.
    - 소속을 모른다 → :func:`resolve_dimmer_attributes`(리그 전 기종이 같을
      때만)로 되돌아간다. 그 규칙은 소속과 무관하게 맞다.

    못 고른 트랙은 속성 표에서 빠지고 사유 표에 한 줄이 남는다 — 에미터가
    그 트랙의 밝기 값 칸만 그 사유로 막는다(다른 트랙은 그대로 나간다)."""
    uniform = resolve_dimmer_attributes(design_rig, group_names)
    capabilities = design_rig.capabilities
    resolved: dict[str, tuple[str, ...]] = {}
    reasons: dict[str, str] = {}
    for name in group_names:
        members = group_members.get(name)
        if not members:
            if name in uniform:
                resolved[name] = uniform[name]
            else:
                reasons[name] = (
                    f"'{name}' 그룹의 소속 장비를 다 읽지 못했고 리그 기종마다 디머 "
                    "속성이 같지 않아 디머 속성을 고를 수 없습니다"
                )
            continue
        if capabilities is None:
            reasons[name] = (
                f"장비 능력을 콘솔에서 읽지 못해 '{name}' 그룹의 디머 속성을 고를 수 없습니다"
            )
            continue
        tuples: dict[tuple[str, ...], list[int]] = {}
        missing: list[int] = []
        for fid in members:
            capability = capabilities.fixtures.get(fid)
            if capability is None or not capability.whole:
                missing.append(fid)
                continue
            tuples.setdefault(dimmer_attribute_names(capability.attributes), []).append(fid)
        if missing:
            listed = ", ".join(str(fid) for fid in missing)
            reasons[name] = (
                f"'{name}' 그룹 장비(fid {listed})의 능력을 다 읽지 못해 디머 속성을 "
                "고를 수 없습니다"
            )
            continue
        if len(tuples) != 1:
            listed = " / ".join(
                f"{', '.join(attrs) or '없음'}(fid {', '.join(map(str, fids))})"
                for attrs, fids in tuples.items()
            )
            reasons[name] = (
                f"'{name}' 그룹 안에 디머 속성이 다른 장비가 섞여 있어 하나로 고를 수 "
                f"없습니다 — {listed}"
            )
            continue
        (attrs,) = tuples
        if not attrs:
            reasons[name] = f"'{name}' 그룹 장비에 디머 속성이 없습니다"
            continue
        resolved[name] = attrs
    return resolved, reasons


def build_song_timing_from_bar_map(bar_map: Mapping[str, object] | None) -> SongTiming | None:
    """``timeline["bar_map"]``(``server.audio.bar_map_store.read_bar_map``의
    결과)를 에미터의 :class:`SongTiming`으로 옮긴다. ``bar_map``이 없거나
    1마디(다운비트)가 없으면 ``None`` — 그 경우 에미터 자신이 "곡 타이밍이
    없어 전체 배치를 거절합니다"로 응답한다(이 함수는 지어내지 않는다).

    ``downbeat_bar1_seconds``는 1마디 ``start_ms`` / 1000 — 초로 저장하지
    않는다는 원칙(``bar_map_store`` 모듈 독스트링)대로 여기서만 환산한다.
    ``pickup_beats``는 0마디(못갖춘마디)가 있으면 그 박 수, 없으면
    ``None``이다(지어내지 않음 — 0마디 트리거는 그때 계산 불가로 남는다,
    ``SongTiming.bar_start_seconds`` 참조)."""
    if not isinstance(bar_map, Mapping):
        return None
    bpm = bar_map.get("bpm")
    if isinstance(bpm, bool) or not isinstance(bpm, (int, float)) or bpm <= 0:
        return None
    time_signature = bar_map.get("time_signature")
    if (
        not isinstance(time_signature, Sequence)
        or isinstance(time_signature, (str, bytes))
        or len(time_signature) != 2
    ):
        return None
    beats_per_bar = time_signature[0]
    if not isinstance(beats_per_bar, int) or isinstance(beats_per_bar, bool) or beats_per_bar <= 0:
        return None
    bars = bar_map.get("bars")
    if not isinstance(bars, list):
        return None
    bar1 = next(
        (b for b in bars if isinstance(b, Mapping) and b.get("bar") == 1),
        None,
    )
    if bar1 is None:
        return None
    start_ms = bar1.get("start_ms")
    if isinstance(start_ms, bool) or not isinstance(start_ms, (int, float)):
        return None

    pickup_beats: float | None = None
    bar0 = next(
        (b for b in bars if isinstance(b, Mapping) and b.get("bar") == 0),
        None,
    )
    if bar0 is not None:
        beats_ms = bar0.get("beats_ms")
        if isinstance(beats_ms, list) and beats_ms:
            pickup_beats = float(len(beats_ms))

    return SongTiming(
        bpm=float(bpm),
        beats_per_bar=int(beats_per_bar),
        downbeat_bar1_seconds=float(start_ms) / 1000.0,
        pickup_beats=pickup_beats,
    )


#: 화면 표시용으로만 붙는 칸 키(콘솔 이름·계획 이름).
#: 콘솔 풀을 읽는 시점에 따라 나타나거나 사라지고, 콘솔에 아직 없는 계획 값이라
#: 「반영 이후 바뀐 칸」 비교에 넣지 않는다. 넣으면 풀을 읽거나 계획을 세우는 것만으로
#: 미반영 칸이 생긴다. 계획 색(`color_planned`)의 `color_rgb` 도 같은 이유로 뺀다.
#: `planned_color`·`planned_position` 은 콘솔 값이 아닌 계획 값이라
#: 「반영 이후 바뀐 칸」 비교에서 뺀다.
_DISPLAY_ONLY_CUE_KEYS = frozenset(
    {
        "position_preset_name",
        "color_preset_name",
        "effect_preset_name",
        "color_planned",
        "planned_color",
        "planned_position",
        "planned_dimmer_name",
        "planned_position_name",
    }
)


def _comparable_cue(cue: Mapping[str, object]) -> dict[str, object]:
    """비교용 칸 사본 — 서빙 때만 붙는 표시값을 뺀다. 칸 하나의 왼쪽·오른쪽 색(``split``)은 쪽마다
    ``color_rgb`` 가 저장 값 ``color`` 에서 서빙 경계가 푼 파생값이라, 스냅샷(저장 모양)과 지금(서빙
    모양)이 달라 보이지 않게 뺀다. ``split`` 이 없는 칸은 표시용 이름 키만 빠지는 예전 그대로다."""
    comparable = {key: value for key, value in cue.items() if key not in _DISPLAY_ONLY_CUE_KEYS}
    split = comparable.get("split")
    if isinstance(split, Mapping):
        comparable["split"] = {
            side: (
                {key: value for key, value in body.items() if key != "color_rgb"}
                if isinstance(body, Mapping)
                else body
            )
            for side, body in split.items()
        }
    return comparable


def beat_grid_cell_snapshot(grid: Mapping[str, object]) -> dict[BeatGridCellKey, object]:
    """``grid``(``BeatGridView``)의 칸을 ``(group_name, bar) -> 칸 사전``으로
    평평하게 편다 — 트랙 순서·칸 순서와 무관하게 **내용**만으로 두 시점을
    비교하기 위한 자리(카드 t563/t568 합의, "콘솔에 반영"이 성공할 때마다
    한 번씩 이 모양으로 찍어 둔다). 콘솔 접촉 0건, 이미 받은 사전의 순수
    변환."""
    snapshot: dict[BeatGridCellKey, object] = {}
    for track in grid.get("tracks") or []:
        if not isinstance(track, Mapping):
            continue
        group_name = str(track.get("group_name"))
        for cue in track.get("cues") or []:
            if not isinstance(cue, Mapping):
                continue
            bar = cue.get("bar")
            if isinstance(bar, int) and not isinstance(bar, bool):
                body = _comparable_cue(cue)
                if cue.get("color_planned"):
                    body.pop("color_rgb", None)  # 계획 색은 콘솔 색이 아니라서 비교에서 뺀다
                snapshot[(group_name, bar)] = body
    return snapshot


def unsent_beat_grid_cells(
    grid: Mapping[str, object], snapshot: Mapping[BeatGridCellKey, object] | None
) -> list[dict[str, object]] | None:
    """지금 격자와 가장 최근 「콘솔에 반영」 스냅샷을 비교해, 내용이 달라진
    (추가·변경·삭제 전부 포함) 칸 전수를 ``{"group_name","bar"}``로 돌려준다.

    ``snapshot``이 ``None``이면(이 곡으로 반영을 한 번도 하지 않았다)
    ``None``을 돌려준다 — **빈 리스트와 다른 사실**이다("반영 기록이
    없다" vs "반영 기록과 지금이 일치한다", 코디네이터 계약 2항)."""
    if snapshot is None:
        return None
    current = beat_grid_cell_snapshot(grid)
    keys = set(current) | set(snapshot)
    unsent = [
        {"group_name": group_name, "bar": bar}
        for group_name, bar in sorted(keys)
        if _cell_differs(current.get((group_name, bar)), snapshot.get((group_name, bar)))
    ]
    return unsent


def _cell_differs(now: object, then: object) -> bool:
    """두 시점의 칸 내용이 다른가.

    방향 값(``direction``)은 칸의 진짜 값이라 둘 다 가졌을 때 달라지면 바뀐 칸이다. 하지만
    한쪽에만 있으면(반영 뒤에 이 키가 생긴 스냅샷과 비교하는 업그레이드) 그 키만 뺀 나머지로
    비교한다 — 칸의 콘솔 값은 그대로인데 키 하나가 새로 생겼다고 칸마다 미반영으로 세면 미반영
    칸 수가 한꺼번에 터진다.
    """
    if (
        isinstance(now, dict)
        and isinstance(then, dict)
        and ("direction" in now) != ("direction" in then)
    ):
        now = {key: value for key, value in now.items() if key != "direction"}
        then = {key: value for key, value in then.items() if key != "direction"}
    return now != then


# =============================================================================
# 재적용 소유권 (카드 t572, REQ-LDBEAT-011~013) — 두 번째 이후 「콘솔에
# 반영」은 이 앱이 저번에 **자기 손으로 쓴** 번호만 덮어쓴다. 아래 두
# 함수는 콘솔에 아무것도 쓰지 않는다(읽기 질의 0건, 순수 변환).
# =============================================================================


def _owned_sequence_names(sequences_section: Mapping[str, object]) -> dict[int, str | None]:
    """``_sequence_numbers``(``server.looks.songcue``)와 같은 열쇠 해석
    (``objects`` 우선, 없으면 ``children``)이지만, 점유 번호의 **집합**이
    아니라 번호 -> 콘솔 이름 사전을 돌려준다 — 소유권 확인은 번호가
    있다는 사실만으로는 부족하고, 그 번호에 달린 이름이 기록과 같은지도
    봐야 한다."""
    listed = sequences_section.get("objects")
    if not isinstance(listed, list):
        listed = sequences_section.get("children")
    if not isinstance(listed, list):
        raise SequenceNumberError("sequence_unavailable")
    names: dict[int, str | None] = {}
    for entry in listed:
        if not isinstance(entry, Mapping):
            raise SequenceNumberError("sequence_number_unavailable")
        number = entry.get("no", entry.get("i"))
        if not isinstance(number, int) or isinstance(number, bool):
            raise SequenceNumberError("sequence_number_unavailable")
        name = entry.get("name")
        names[number] = name if isinstance(name, str) else None
    return names


#: 앱이 만든 타임코드·시퀀스 이름 접두사 — ``beat_grid_timecode_label`` /
#: ``beat_grid_sequence_label`` 이 콘솔에 적는 이름의 앞부분이다.
APP_TIMECODE_PREFIX = "LDBEAT Timecode"
APP_SEQUENCE_PREFIX = "LDBEAT "

_TRAILING_NUMBER = re.compile(r"(\d+)\s*$")


_SEQUENCE_WORD = re.compile(r"Sequences?[\s/.:_-]*(\d+)", re.IGNORECASE)
_DOTTED_HANDLE = re.compile(r"^\d+(?:\.\d+)+$")


def parse_track_target(
    value: object, sequence_names: Mapping[int, str | None]
) -> tuple[int | None, str | None]:
    """트랙 TARGET 한 값 -> ``(시퀀스 번호, 이름)``. 알 수 없으면 둘 다 ``None``.

    받는 꼴: 정수 · ``Sequence N`` · ``N`` · 시퀀스 이름 문자열 ·
    ``DataPool/Sequences/N`` 같은 객체 경로 · ``13.1.6.16`` 핸들(마지막 마디가 N) ·
    ``{"no"/"i": N, "name": ...}`` 매핑."""
    if isinstance(value, bool):
        return None, None
    if isinstance(value, int):
        return value, sequence_names.get(value)
    if isinstance(value, Mapping):
        for key in ("no", "i", "index", "number"):
            inner = value.get(key)
            if isinstance(inner, int) and not isinstance(inner, bool):
                return inner, sequence_names.get(inner) or (
                    value["name"] if isinstance(value.get("name"), str) else None
                )
        name = value.get("name")
        return (None, name) if isinstance(name, str) else (None, None)
    if not isinstance(value, str):
        return None, None
    text = value.strip()
    if not text:
        return None, None
    if text.isdigit():
        return int(text), sequence_names.get(int(text))
    for number, name in sequence_names.items():
        if name is not None and name == text:
            return number, name
    if _DOTTED_HANDLE.match(text):
        number = int(text.rsplit(".", 1)[1])
        return number, sequence_names.get(number)
    word = _SEQUENCE_WORD.search(text)
    if word is not None:
        number = int(word.group(1))
        return number, sequence_names.get(number)
    match = _TRAILING_NUMBER.search(text)
    if match is not None and int(match.group(1)) in sequence_names:
        number = int(match.group(1))
        return number, sequence_names[number]
    return None, text


def timecode_overwrite_note(
    wanted: int,
    occupant: str,
    track_targets: Sequence[object],
    sequence_names: Mapping[int, str | None],
) -> tuple[str | None, str | None]:
    """앱이 만든 타임코드를 같은 번호로 다시 반영해도 되는지(덮어쓰기 허용 규칙).

    ``(승인 카드 위험 줄, None)`` 이면 허용, ``(None, 사유)`` 이면 이전처럼 거절.
    허용 조건은 둘이 함께여야 한다 — 타임코드 이름이 ``LDBEAT Timecode`` 로
    시작하고, 그 트랙이 가리키는 시퀀스가 **전부** 앱 소유(``LDBEAT`` 접두)이며
    하나 이상 있다. 항목은 TARGET 값 자체이거나 ``{"target": 값, "track_name": 이름}``
    — TARGET 을 읽지 못한 트랙(``target`` 이 ``None``)은 트랙 이름이 앱 시퀀스
    이름(``LDBEAT ``)일 때만 앱 소유로 본다(트랙 이름도 아니면 거절)."""
    if not occupant.startswith(APP_TIMECODE_PREFIX):
        return None, None
    if not track_targets:
        return None, (
            f"Timecode {wanted}의 트랙이 가리키는 시퀀스를 확인하지 못해 덮어쓰기를 거절합니다."
        )
    for item in track_targets:
        track_name: str | None = None
        target = item
        if isinstance(item, Mapping) and "target" in item:
            target = item.get("target")
            raw_name = item.get("track_name")
            track_name = raw_name.strip() if isinstance(raw_name, str) else None
        _, name = parse_track_target(target, sequence_names) if target is not None else (None, None)
        if name is None and track_name is not None:
            name = track_name
        if not isinstance(name, str) or not name.startswith(APP_SEQUENCE_PREFIX):
            return None, (
                f"Timecode {wanted}이 앱 소유가 아닌 시퀀스({target!r})를 가리키고 있어 "
                "반영을 거절합니다."
            )
    return f"기존 {occupant} 을 덮어씁니다", None


_CONSOLE_DUPLICATE_SUFFIX = re.compile(r"#\d+")


def _same_owned_sequence_name(console_name: str | None, recorded_name: object) -> bool:
    """콘솔 이름이 기록된 이름과 같거나, 기록된 이름 뒤에 콘솔이 붙인 「#숫자」만 더 붙었는지.

    같은 이름의 시퀀스가 이미 있으면 콘솔은 이름 끝에 ``#6`` 같은 접미사를 붙인다(실서버
    rerun3: 'LDBEAT FOH#6' 대 기록 'LDBEAT FOH'). 그 밖의 차이는 여전히 다른 이름이다."""
    if not isinstance(console_name, str) or not isinstance(recorded_name, str):
        return console_name == recorded_name
    if console_name == recorded_name:
        return True
    suffix = console_name[len(recorded_name) :]
    return console_name.startswith(recorded_name) and bool(
        _CONSOLE_DUPLICATE_SUFFIX.fullmatch(suffix)
    )


def verify_owned_sequences(
    sequences_section: Mapping[str, object],
    owned: Mapping[str, Mapping[str, object]],
) -> tuple[dict[str, int], str | None]:
    """``owned``(소유권 레코드의 ``tracks`` — 그룹 이름 -> {``sequence_
    number``, ``sequence_name``, ...})가 **지금** 콘솔 시퀀스 풀에
    그 번호·그 이름 그대로 있는지 확인한다.

    하나라도 못 찾거나 이름이 다르면 **그 묶음 전체**를 그 사유로
    거절한다(부분 적용 0건 — ``pick_sequence_numbers``와 같은 원칙).
    풀 자체를 못 읽거나 잘렸으면(truncated) "있다"도 "없다"도 단정하지
    않고 그 사유로 거절한다.

    ``owned``가 비어 있으면(이 곡으로 반영을 한 번도 하지 않았다) 확인할
    것이 없으므로 ``({}, None)``이다."""
    if not owned:
        return {}, None
    unavailable = sequences_section.get("reason")
    if isinstance(unavailable, str) or sequences_section.get("ok") is False:
        return {}, _SEQUENCE_REASON_MESSAGES["sequence_unavailable"]
    if sequences_section.get("truncated"):
        return {}, _SEQUENCE_REASON_MESSAGES["sequence_truncated"]
    try:
        console_names = _owned_sequence_names(sequences_section)
    except SequenceNumberError as error:
        return {}, _sequence_reason(error)

    owned_sequences: dict[str, int] = {}
    for group_name, allocation in owned.items():
        recorded_no = allocation.get("sequence_number")
        recorded_name = allocation.get("sequence_name")
        if not isinstance(recorded_no, int) or isinstance(recorded_no, bool):
            return {}, (
                f"'{group_name}' 트랙의 소유권 기록에 시퀀스 번호가 없어 재적용을 "
                "거절합니다(기록 손상)."
            )
        if recorded_no not in console_names:
            return {}, (
                f"'{group_name}' 트랙이 쓰던 시퀀스 {recorded_no}번을 콘솔에서 찾지 "
                "못해 재적용을 거절합니다."
            )
        console_name = console_names[recorded_no]
        if not _same_owned_sequence_name(console_name, recorded_name):
            return {}, (
                f"'{group_name}' 트랙이 쓰던 시퀀스 {recorded_no}번의 콘솔 이름"
                f"('{console_name}')이 기록된 이름('{recorded_name}')과 달라 재적용을 "
                "거절합니다."
            )
        owned_sequences[group_name] = recorded_no
    return owned_sequences, None


def apply_beat_grid_ownership_reuse(
    result: BeatGridEmitResult,
    *,
    owned_sequences: Mapping[str, int],
    owned_timecode: int | None,
    recorded_cue_numbers: Mapping[str, Mapping[int, int]],
    overwrite_all_groups: frozenset[str] = frozenset(),
) -> BeatGridEmitResult:
    """재적용 — 소유권 확인을 이미 통과한 (그룹 -> 시퀀스 번호) 묶음과
    (있다면) 소유한 타임코드 번호를 받아, 방금 에미터가 낸 **전체** 번들
    에서 "이미 콘솔에 있는 것"을 다시 만드는 줄만 걷어낸다.

    아무 쓰기도 지어내지 않는다 — 이 함수는 ``result``가 이미 낸 명령을
    가지치기/치환만 한다:

    * 소유한 트랙(트랙 전체가 막히지 않았고 낼 큐가 있는 트랙)은 **시퀀스를 통째로 지우고 같은
      번호로 다시 만든다** — 첫 큐 줄 앞에 ``Delete Sequence <s> /NoConfirm`` 을 넣는다. 그
      뒤 큐 줄은 첫 반영과 같은 꼴(``/Overwrite`` 없음, 이름 줄 포함)이다. 재실행 4: 큐 하나
      지우기(``Delete Cue N Sequence S``)는 실콘솔이 「Not allowed」로 거절했고(t608 v4·
      rerun4, t618), ``Delete Sequence N /NoConfirm`` 은 rerun2 에서 8건 모두 ``OK`` 였다.
      옛 큐를 남기면 ``Go+`` 재생이 낡은 큐를 지나간다. 다시 만든 번호는
      ``rebuilt_sequences`` 에 적는다.
    * 막힌 트랙과 낼 큐가 없는 트랙은 손대지 않는다(명령 0줄 그대로).
    * ``owned_timecode``가 있으면(그 타임코드를 재사용한다) 전체 ``Store
      Timecode``/``Set ... 'Name'`` 설정 줄을 뺀다(한 곡에 타임코드는
      하나뿐이라 전역이다) — 그리고 소유한 트랙의 ``Assign Sequence ...
      At Timecode ...`` 줄도 뺀다(이미 배정돼 있다, 다시 배정하면 콘솔이
      둘째 트랙을 만든다).

    ``recorded_cue_numbers``·``overwrite_all_groups`` 는 시퀀스를 다시 만들면서 더 쓰지 않는다
    (호출 꼴만 유지한다). 큐 번호는 호출자가 기록 없이 방출해 1번부터 시간 순서로 매긴다."""
    del recorded_cue_numbers, overwrite_all_groups
    new_timecode_setup = () if owned_timecode is not None else result.timecode_setup_commands

    new_tracks = []
    rebuilt: list[int] = []
    for track in result.tracks:
        owned_number = owned_sequences.get(track.group_name)
        is_owned = owned_number is not None and owned_number == track.sequence_number
        # 트랙 전체가 막힌 경우(그룹 번호 미확인 등)에는 에미터가 칸 목록을
        # 비워 돌려준다 — 그걸 「칸이 다 비워졌다」로 읽으면 그 트랙의 큐를
        # 전부 지우게 된다. 막힌 트랙은 손대지 않는다(명령 0줄 그대로).
        first = next((i for i, cue in enumerate(track.cues) if cue.commands), None)
        if not is_owned or track.blocked_reason is not None or first is None:
            new_tracks.append(track)
            continue

        assign_timecode_commands = (
            () if owned_timecode is not None else track.assign_timecode_commands
        )
        cues = list(track.cues)
        delete_line = f"Delete Sequence {track.sequence_number} /NoConfirm"
        cues[first] = replace(cues[first], commands=(delete_line, *cues[first].commands))
        rebuilt.append(track.sequence_number)
        new_tracks.append(
            replace(
                track,
                assign_timecode_commands=assign_timecode_commands,
                cues=tuple(cues),
            )
        )

    new_events = () if owned_timecode is not None else result.timecode_event_commands
    return replace(
        result,
        tracks=tuple(new_tracks),
        timecode_setup_commands=new_timecode_setup,
        timecode_event_commands=new_events,
        rebuilt_sequences=tuple(rebuilt),
    )


def clear_app_timecode_before_rebuild(
    result: BeatGridEmitResult,
    timecode_number: int,
    delete_sequences: Sequence[int] = (),
) -> BeatGridEmitResult:
    """카드 tc-events — 앱이 만든 ``LDBEAT Timecode N`` 을 같은 번호로 다시 반영할 때, 옛 트랙
    (콘솔이 덧붙인 빈 ``Track 9`` 따위)이 쌓이지 않도록 그 타임코드를 **먼저 지우고** 새로
    만든다. 지우는 줄은 번들 맨 앞(타임코드 설정 첫 줄)에 들어가 승인 카드에 그대로 보이고,
    대상은 호출자가 앱 소유로 확인한 이 번호 하나뿐이다. 실기 선례: t608 v2 정리
    (``Delete Timecode 70 /NoConfirm`` → ``OK`` + 사후 empty).

    이 번호를 다시 만드는 줄(``Store Timecode N``)이 번들에 없으면 지우기만 하게 되므로
    아무것도 하지 않는다.

    ``delete_sequences``(카드 apply-safety, D14) — 덮어쓰는 옛 타임코드가 가리키던 앱 시퀀스
    가운데 이번 격자 그룹과 짝이 안 맞아 재사용하지 못한 것. 타임코드를 지운 **뒤** 같은 번들에서
    지운다(타임코드가 참조하는 동안 지우지 않는다). 호출자가 ``LDBEAT `` 접두를 확인한
    번호만 넘긴다.

    # @MX:WARN: [AUTO] ``Delete Sequence <n> /NoConfirm`` 는 ``Delete Timecode N /NoConfirm``
    #   (t608 v2 실기 선례)과 같은 꼴의 가설 문법이다 — 이 저장소에 실기 선례가 없다.
    # @MX:REASON: 거절되면 승인 카드가 그 줄을 보이므로 감독이 보고, 이 함수의 줄 모양만 고친다.
    """
    store_line = f"Store Timecode {timecode_number}"
    if store_line not in result.timecode_setup_commands:
        return result
    return replace(
        result,
        timecode_setup_commands=(
            f"Delete Timecode {timecode_number} /NoConfirm",
            *(f"Delete Sequence {number} /NoConfirm" for number in delete_sequences),
            *result.timecode_setup_commands,
        ),
    )


def song_end_seconds_from_bar_map(bar_map: Mapping[str, object] | None) -> float | None:
    """``bar_map`` 의 마지막 마디 끝(곡 기준 초) — 타임코드 ``Duration`` 이다. 마디 길이는
    박자표·BPM 으로 환산한다(저장 값 아님). 읽지 못하면 ``None`` — 길이를 지어내지 않는다."""
    timing = build_song_timing_from_bar_map(bar_map)
    if timing is None or not isinstance(bar_map, Mapping):
        return None
    ends: list[float] = []
    for bar in bar_map.get("bars") or []:
        if not isinstance(bar, Mapping) or not isinstance(bar.get("bar"), int) or bar["bar"] < 1:
            continue
        start_ms = bar.get("start_ms")
        if isinstance(start_ms, bool) or not isinstance(start_ms, (int, float)):
            continue
        ends.append(float(start_ms) / 1000.0 + timing.beats_per_bar * 60.0 / timing.bpm)
    return max(ends) if ends else None


def beat_grid_reapply_summary(
    result: BeatGridEmitResult,
    *,
    recorded_cue_numbers: Mapping[str, Mapping[int, int]],
) -> tuple[dict[str, dict[int, int]], list[tuple[str, int, str]], int]:
    """카드 t572 — 이번 반영이 콘솔에 남길 큐 번호표와, 승인 카드에 적을 두 숫자.

    돌려주는 셋:

    * 다음 소유 기록의 번호표(트랙 이름 -> {마디: 큐 번호}) — 이번에 쓴 칸에
      **막혀서 그대로 둔 칸**의 기록 번호를 더한 것. 막힌 칸은 콘솔에 옛 큐가
      남아 있으므로 기록에서도 빼지 않는다(빼면 다음 반영이 그 번호를 모른다).
      트랙 전체가 막혔으면 그 트랙의 기록을 통째로 그대로 둔다.
    * 막혀서 그대로 둔 칸 목록 (트랙, 마디, 사유) — 기록에 있던 칸만.
    * 번호 순서와 시간(마디) 순서가 어긋난 큐의 수 — 콘솔에 남을 큐를 번호
      순으로 늘어놓았을 때, 앞 번호의 마디보다 이른 마디를 가진 큐의 수. 새
      마디가 기존 마디 사이에 끼면 최대 번호 다음 정수를 받으므로 생긴다.
      타임코드 재생은 TrigTime 으로 맞더라도 사람이 Go 로 넘기면 순서가
      어긋나므로 승인 카드에 알린다(리드 결정)."""
    next_record: dict[str, dict[int, int]] = {}
    preserved: list[tuple[str, int, str]] = []
    out_of_order = 0
    for track in result.tracks:
        recorded = dict(recorded_cue_numbers.get(track.group_name) or {})
        if track.blocked_reason is not None:
            if recorded:
                next_record[track.group_name] = recorded
                preserved.extend(
                    (track.group_name, bar, track.blocked_reason) for bar in sorted(recorded)
                )
            continue
        numbers = {cue.bar: cue.cue_number for cue in track.cues if cue.cue_number is not None}
        for cue in track.cues:
            if cue.blocked_reason is not None and cue.bar in recorded:
                numbers[cue.bar] = recorded[cue.bar]
                preserved.append((track.group_name, cue.bar, cue.blocked_reason))
        next_record[track.group_name] = numbers
        latest_bar = -1
        for _number, bar in sorted((number, bar) for bar, number in numbers.items()):
            if bar < latest_bar:
                out_of_order += 1
            latest_bar = max(latest_bar, bar)
    return next_record, preserved, out_of_order
