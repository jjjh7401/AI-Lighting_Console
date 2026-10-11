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
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from server.design.app_movement import dimmer_attribute_names
from server.design.beat_grid_emit import SongTiming
from server.design.rig_capability_read import DesignRigRead
from server.looks.songcue import SequenceNumberError, select_sequence_number

__all__ = [
    "BeatGridCellKey",
    "beat_grid_cell_snapshot",
    "build_song_timing_from_bar_map",
    "pick_sequence_numbers",
    "resolve_dimmer_attributes",
    "unsent_beat_grid_cells",
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
                snapshot[(group_name, bar)] = cue
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
        if current.get((group_name, bar)) != snapshot.get((group_name, bar))
    ]
    return unsent
