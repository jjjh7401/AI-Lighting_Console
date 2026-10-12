"""카드 t491 — 한 쇼(세션) 안에서 곡 사이 룩 재사용을 피한다.

감독 결정(2026-10-12): 「같은 답을 준 연속 곡도 앱이 스스로 앞 곡과 다른 룩으로
연다」. 지금 조립기에서 룩을 정하는 것은 곡이 아니라 인터뷰 답이라(t491 1단계
실측 — 같은 답이면 이웃 쌍 7/7 이 같은 첫 큐), 앞 곡과 다르게 열 손잡이는 감독이
이미 고른 후보 **안에서** 순서를 돌리는 것뿐이다. 새 위치·새 색을 짓지 않는다.

룩(큐 하나) = ``(position.stored, color.palette)`` — 1단계 측정의 정의와 같다.
구간 큐(``kind == "section"``)만 센다. MIB 사전이동·절정 복귀는 파생 큐다.

이 모듈은 고르기만 한다(순수 함수). 후보를 만들고 기억을 쥐는 것은
``server/web/session.py`` 의 ``_song_compose`` 와 곡 저장 성공 지점이다 —
t486 이 지운 ``SongLookMemory`` 는 아무도 안 읽는 배선이었으므로, 이번에는
대화 길(``run_instruction`` → ``_song_compose`` → ``compose_song_cue_bundle``)이
직접 부른다.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar

from server.design.song_cue_composer import SongCueCompositionResult

#: 큐 하나의 룩 — (저장 위치, 팔레트 색 순서).
Look = tuple[str | None, tuple[str, ...]]
#: 곡 하나의 룩 — 구간 큐 순서대로.
SongLooks = tuple[Look, ...]

_Built = TypeVar("_Built")


def compose_avoiding_previous(
    build: Callable[[int], tuple[_Built, SongCueCompositionResult]],
    history: Sequence[SongLooks],
    *,
    enabled: bool = True,
) -> tuple[_Built, SongCueCompositionResult, int]:
    """오프셋 0, 1, 2 … 로 ``build`` 를 불러 앞 곡들과 다르게 열리는 것을 고른다.

    카드 t609 — 대화 길(``session._song_compose``)과 업로드 길(``prepare_songcue``)이
    같은 고르기를 쓰도록 t491 의 반복문을 여기로 옮겼다. ``build(k)`` 는 k칸 돌린
    조립을 돌려준다. 곡 룩이 앞서 본 후보와 같아지면(회전이 한 바퀴) 멈춘다 — 회전은
    감독 답의 목록 길이로 주기가 정해지므로 상수 없이 끝난다. 기억이 없거나
    ``enabled`` 가 거짓이면 오프셋 0(감독 답 그대로)만 조립한다.

    반환: ``(build 의 첫 값, 조립 결과, 고른 오프셋)``.
    """
    if not enabled or not history:
        built, composition = build(0)
        return built, composition, 0
    candidates: list[tuple[_Built, SongCueCompositionResult]] = []
    seen: set[SongLooks] = set()
    offset = 0
    while True:
        built, composition = build(offset)
        looks = song_looks(composition)
        if looks in seen:
            break
        seen.add(looks)
        candidates.append((built, composition))
        offset += 1
    chosen = choose_look_offset([song_looks(c) for _, c in candidates], history)
    built, composition = candidates[chosen]
    return built, composition, chosen


def song_looks(composition: SongCueCompositionResult) -> SongLooks:
    """조립 결과에서 구간 큐의 룩을 순서대로 뽑는다. 번들이 없으면 빈 튜플."""
    bundle = composition.bundle
    if bundle is None:
        return ()
    return tuple(
        (cue.position.stored, tuple(cue.color.palette))
        for cue in bundle.cues
        if cue.kind == "section"
    )


def choose_look_offset(candidates: Sequence[SongLooks], history: Sequence[SongLooks]) -> int:
    """후보(``candidates[k]`` = k칸 돌렸을 때의 곡 룩) 중 하나의 k 를 고른다.

    ``history`` 는 이 세션에서 이미 콘솔에 저장된 곡들의 룩(오래된 것부터).

    고르는 순서 — 기본값이지 강제가 아니다(멈추지 않는다):

    1. 첫 큐 룩이 이 세션에서 **한 번도** 안 쓰인 후보.
    2. 모두 쓰였으면 첫 큐 룩을 **가장 오래전에** 쓴 후보.
    3. 같으면 앞 곡에서 쓴 룩을 덜 다시 쓰는 후보.
    4. 그래도 같으면 작은 k(0 = 감독 답 그대로).

    기억이 비었거나 후보가 하나뿐이면 0.
    """
    if not candidates:
        return 0
    if not history or len(candidates) == 1:
        return 0
    last_seen: dict[Look, int] = {}
    for index, looks in enumerate(history):
        for look in looks:
            last_seen[look] = index
    previous = set(history[-1])

    def key(offset: int) -> tuple[int, int, int]:
        looks = candidates[offset]
        opening = last_seen.get(looks[0], -1) if looks else -1
        reused = sum(1 for look in looks if look in previous)
        return (opening, reused, offset)

    return min(range(len(candidates)), key=key)
