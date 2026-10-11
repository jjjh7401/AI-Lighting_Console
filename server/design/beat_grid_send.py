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

from collections.abc import Mapping, Sequence
from dataclasses import replace

from server.design.app_movement import dimmer_attribute_names
from server.design.beat_grid_emit import BeatGridEmitResult, CueEmitResult, SongTiming
from server.design.rig_capability_read import DesignRigRead
from server.looks.songcue import SequenceNumberError, select_sequence_number

__all__ = [
    "BeatGridCellKey",
    "apply_beat_grid_ownership_reuse",
    "beat_grid_cell_snapshot",
    "beat_grid_reapply_summary",
    "build_song_timing_from_bar_map",
    "pick_sequence_numbers",
    "resolve_dimmer_attributes",
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
        if console_name != recorded_name:
            return {}, (
                f"'{group_name}' 트랙이 쓰던 시퀀스 {recorded_no}번의 콘솔 이름"
                f"('{console_name}')이 기록된 이름('{recorded_name}')과 달라 재적용을 "
                "거절합니다."
            )
        owned_sequences[group_name] = recorded_no
    return owned_sequences, None


def _overwrite_store_cue(cue: CueEmitResult, *, sequence_number: int) -> CueEmitResult:
    """이 칸이 실제로 저장한 ``Store Cue <n> Sequence <s>`` 줄 하나(있다면
    정확히 그 줄, ``_emit_cue``가 쓰는 모양 그대로)에만 ``/Overwrite``를
    덧붙인다 — 문자열을 더 넓게 훑지 않는다(``cue_number``로 그 줄이
    정확히 무엇일지 미리 알고, 그 값과만 비교한다).

    # @MX:WARN: [AUTO] ``Store Cue ... /Overwrite``는 이 저장소에서 실기로
    #   확인된 적이 없다 — 기존 쓰기 경로들(``position_fx.py``·
    #   ``pointing.py``·``scene/compile.py``)은 전부 ``/Merge``를 고르고
    #   ``/Overwrite``를 일부러 피한다(각자의 독스트링: "destructive flag
    #   the safety gate routes to human approval"). 재적용이 바로 그 승인을
    #   받으려는 쪽이므로 선택은 맞지만, 콘솔이 이 정확한 문법(``Sequence``
    #   뒤 ``/Overwrite``)을 받는지는 아직 측정되지 않았다.
    # @MX:REASON: 측정 전까지는 가설 문법이다 — ``31_choreography_
    #   patterns.md``에 ``Store ... /Overwrite``의 측정 기록이 없다. 다음
    #   실기 접속에서 먼저 이 한 줄만 쏘아 확인하고, 거절되면 이 함수가
    #   돌려주는 모양부터 고친다.
    """
    if not cue.commands or cue.cue_number is None:
        return cue
    target = f"Store Cue {cue.cue_number} Sequence {sequence_number}"
    overwritten = tuple(f"{line} /Overwrite" if line == target else line for line in cue.commands)
    return replace(cue, commands=overwritten)


def apply_beat_grid_ownership_reuse(
    result: BeatGridEmitResult,
    *,
    owned_sequences: Mapping[str, int],
    owned_timecode: int | None,
    recorded_cue_numbers: Mapping[str, Mapping[int, int]],
) -> BeatGridEmitResult:
    """재적용 — 소유권 확인을 이미 통과한 (그룹 -> 시퀀스 번호) 묶음과
    (있다면) 소유한 타임코드 번호를 받아, 방금 에미터가 낸 **전체** 번들
    에서 "이미 콘솔에 있는 것"을 다시 만드는 줄만 걷어낸다.

    아무 쓰기도 지어내지 않는다 — 이 함수는 ``result``가 이미 낸 명령을
    가지치기/치환만 한다:

    * 소유한 트랙의 ``Store Sequence <s>`` 줄은 뺀다(``Set ... 'Name'``
      줄은 남긴다 — 코디네이터 결정, 이름 갱신 자체는 해롭지 않다).
    * ``owned_timecode``가 있으면(그 타임코드를 재사용한다) 전체 ``Store
      Timecode``/``Set ... 'Name'`` 설정 줄을 뺀다(한 곡에 타임코드는
      하나뿐이라 전역이다) — 그리고 소유한 트랙의 ``Assign Sequence ...
      At Timecode ...`` 줄도 뺀다(이미 배정돼 있다, 다시 배정하면 콘솔이
      둘째 트랙을 만든다). 새 트랙(``owned_sequences``에 없는 그룹)은
      ``Assign`` 줄을 그대로 낸다(그 시퀀스는 아직 그 타임코드에
      배정된 적이 없다).
    * 소유한 트랙에서 **기록된 마디**의 ``Store Cue`` 줄에만 ``/Overwrite``를
      붙인다(그 큐는 콘솔에 이미 있다). 새 마디는 새 번호라 그대로 둔다.
    * 소유한 트랙에서, 기록된 마디 중 **이번 초안에서 정말 비워진** 칸
      (격자에서 빠졌거나 낼 내용이 없음)의 번호마다 ``Delete Cue <n>
      Sequence <s>``를 추가한다. **막힌 칸**(``blocked_reason`` 있음)은
      지우지 않는다 — 막혔다는 건 이번에 그 칸을 확인하지 못했다는 뜻이지
      비웠다는 뜻이 아니다(카드 t572 리드 결정, 콘솔 내용은 되돌릴 수
      없다). 레코드에 없던 트랙(새 트랙)에는 삭제를 내지 않는다."""
    new_timecode_setup = () if owned_timecode is not None else result.timecode_setup_commands

    new_tracks = []
    for track in result.tracks:
        owned_number = owned_sequences.get(track.group_name)
        is_owned = owned_number is not None and owned_number == track.sequence_number
        # 트랙 전체가 막힌 경우(그룹 번호 미확인 등)에는 에미터가 칸 목록을
        # 비워 돌려준다 — 그걸 「칸이 다 비워졌다」로 읽으면 그 트랙의 큐를
        # 전부 지우게 된다. 막힌 트랙은 손대지 않는다(명령 0줄 그대로).
        if not is_owned or track.blocked_reason is not None:
            new_tracks.append(track)
            continue

        store_sequence_commands = tuple(
            line for line in track.store_sequence_commands if not line.startswith("Store Sequence ")
        )
        assign_timecode_commands = (
            () if owned_timecode is not None else track.assign_timecode_commands
        )
        recorded = recorded_cue_numbers.get(track.group_name) or {}
        cues = tuple(
            _overwrite_store_cue(cue, sequence_number=track.sequence_number)
            if cue.bar in recorded
            else cue
            for cue in track.cues
        )
        emitted_bars = {cue.bar for cue in cues if cue.cue_number is not None}
        blocked_bars = {cue.bar for cue in cues if cue.blocked_reason is not None}
        emptied = sorted(
            (bar, number)
            for bar, number in recorded.items()
            if bar not in emitted_bars and bar not in blocked_bars
        )
        # @MX:WARN: [AUTO] ``Delete Cue <n> Sequence <s>``도 ``/Overwrite``와
        #   같은 처지다 — 이 저장소 어디에도 실기로 확인된 선례가 없다
        #   (grep 결과 0건, 2026-10-11). 게이트가 위험으로 분류해도 괜찮다
        #   (배차서 지시) — 한 번들 안의 다른 쓰기와 똑같이 승인을 탄다.
        # @MX:REASON: 가설 문법. 다음 실기 접속에서 먼저 확인하고, 거절되면
        #   (예: 번호 띄어쓰기·대상 지정 방식) 이 자리만 고친다 — 소유권
        #   판정·레코드 쪽은 건드릴 필요가 없다(순수하게 명령 문자열 문제).
        delete_cues = tuple(
            CueEmitResult(
                bar=bar,
                commands=(f"Delete Cue {number} Sequence {track.sequence_number}",),
                blocked_reason=None,
                cue_number=None,
            )
            for bar, number in emptied
        )
        new_tracks.append(
            replace(
                track,
                store_sequence_commands=store_sequence_commands,
                assign_timecode_commands=assign_timecode_commands,
                cues=cues + delete_cues,
            )
        )

    return replace(result, tracks=tuple(new_tracks), timecode_setup_commands=new_timecode_setup)


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
