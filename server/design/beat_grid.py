"""박자 격자 데이터 모델 — 런북 모드 콘솔 그룹 트랙 × 마디 격자 (SPEC-LDBEAT-001 M2).

이 모듈은 콘솔에 아무것도 쓰지 않는다. 입력도 출력도 순수 파이썬 사전뿐이다
(``cue_sheet_edit.py``와 같은 모양, t281). 저장은 M2가 확정한 임베드 설계를
따른다(spec.md §5 열린 결정 0'): 격자는 기존 ``timeline`` 사전의 새 키
``beat_grid`` 하나로 심는다 — ``SongTimelineStore``(``session.py:3486``)의
atomic JSON write와 ``TimelineDraftHistory``(``session.py:3831``,
``:8505``)의 전체-사전 되돌리기가 **코드 추가 없이** 격자도 덮는다. 격자
전용 독립 저장소는 M2에서 신설하지 않는다 — 이 설계를 바꾸려면 director와
재확인하고 이 주석과 progress.md를 함께 고친다.

트랙 모양(카드 t526 교정, REQ-LDBEAT-004): **줄 하나 = 콘솔 그룹 하나 =
시퀀스 하나**다. 트랙 식별자는 콘솔 그룹 번호/이름이고, "SCENE"·"BACK
PULSE" 같은 역할·효과 혼성 문자열을 식별자로 쓰지 않는다(§B 위험 9). 층
역할(``server.design.rig.RIG_LAYER_ROLES``)은 그 줄 옆의 이름표일 뿐이다.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TypedDict

from server.design.rig import resolve_layer_role

__all__ = [
    "DEFAULT_BAR_RANGE",
    "LOVE_ATTACK_TITLE",
    "BeatGridCue",
    "BeatGridTrack",
    "BeatGridView",
    "attach_beat_grid_default",
    "default_beat_grid",
    "find_overlapping_group_tracks",
    "validate_beat_grid_tracks",
]


class BeatGridCue(TypedDict):
    """격자 칸 하나. 효과 모양/속도 같은 내용은 트랙 정체성이 아니라 이
    칸의 ``label``(및 향후 M3가 채울 구조화 필드)에만 산다(REQ-LDBEAT-004)."""

    bar: int
    label: str


class BeatGridTrack(TypedDict):
    """콘솔 그룹 트랙 하나. ``group_no``가 ``None``이면 이 플랜-phase/M1
    증거에서 그룹 번호가 아직 확인되지 않았다는 뜻이다(지어내지 않는다) —
    ``group_no_confirmed``가 그 구분을 명시적으로 싣는다."""

    group_no: int | None
    group_no_confirmed: bool
    group_name: str
    layer_role: str | None
    cues: list[BeatGridCue]


class BeatGridView(TypedDict):
    song_title: str
    bar_range: dict[str, int]
    tracks: list[BeatGridTrack]
    source: str
    note: str | None


#: REQ-LDBEAT-005(a) — 초기 표시 범위. 정수, 1-base 위상 1 기준, 0 = 못갖춘마디
#: (`SPEC-LDBARMAP-001` §5 열린 결정 0과 같은 번호 공간, 카드 t529 맞춤).
DEFAULT_BAR_RANGE: tuple[int, int] = (0, 25)

#: 곡별 기본값을 가진 유일한 곡(배치 규칙서 §2~§4). 다른 곡은 빈 상태다
#: (REQ-LDBEAT-006/AC-LDBEAT-007) — 이름표 비교는 공백을 다듬고
#: 대소문자를 가리지 않는다.
LOVE_ATTACK_TITLE = "LOVE ATTACK"

#: 곡별 기본값이 없을 때 화면이 보일 안내(AC-LDBEAT-007).
_NO_DEFAULT_NOTE = "이 곡의 기본값 없음"


def _group_key(name: str) -> str:
    return name.strip().casefold()


def _group_prefix(name: str) -> str | None:
    """하이픈 앞 접두 토큰(``server.design.rig.resolve_layer_role``의 접두
    매칭과 같은 분리 — ``side``/``wash``/``mover`` 계열의 "-ALL" 그룹이 같은
    접두를 가진 다른 그룹을 전부 포함한다는 사실을 가른다). 하이픈이 없으면
    ``None``(겹침 판정 대상이 아니다)."""
    key = _group_key(name)
    prefix, separator, _rest = key.partition("-")
    return prefix if separator else None


def find_overlapping_group_tracks(group_names: Sequence[str]) -> tuple[str, str] | None:
    """제안된 트랙 목록에서 같은 장비를 겹쳐 잡는 **첫** 두 그룹 이름을 돌려준다
    (REQ-LDBEAT-004(h)). 겹침 없으면 ``None``.

    이 리그가 확인한 겹침 모양은 두 가지뿐이다(t525·rig.py):

    1. **같은 그룹을 두 번** — 대소문자 무시 정확 일치.
    2. **"<접두>-ALL"이 같은 접두의 다른 그룹을 포함한다** — 예:
       MOVER-ALL은 MOVER-U·MOVER-D를 전부 담는다(t525 §② 대응표:
       MOVER-ALL의 sf_index 30/31이 MOVER-U의 fid 501/502로 떨어진다).
       같은 모양이 SIDE-ALL/WASH-ALL 계열에도 적용된다(rig.py
       `_LAYER_GROUP_PREFIX_ROLES`와 같은 접두 분리).

    추측(RG5류 금지)이 아니라 바이트 정확 일치만 본다 — "MOVER-ALLX"처럼
    접두가 바이트 동일하지 않으면 겹침으로 안 본다.
    """
    seen: dict[str, str] = {}
    all_by_prefix: dict[str, str] = {}
    plain_by_prefix: dict[str, list[str]] = {}
    for name in group_names:
        key = _group_key(name)
        if key in seen:
            return (seen[key], name)
        seen[key] = name
        prefix = _group_prefix(name)
        if prefix is None:
            continue
        suffix = key.split("-", 1)[1]
        if suffix == "all":
            all_by_prefix[prefix] = name
        else:
            plain_by_prefix.setdefault(prefix, []).append(name)
    for prefix, all_name in all_by_prefix.items():
        for plain_name in plain_by_prefix.get(prefix, []):
            return (all_name, plain_name)
    return None


def validate_beat_grid_tracks(tracks: Sequence[Mapping[str, object]]) -> str | None:
    """단일-원인 거절 사유 하나(``cue_sheet_edit.py``와 같은 관행, REQ-LDBEAT-008) —
    겹침이 없으면 ``None``. 검증은 쓰기 전에 전부 끝낸다(부분 적용 금지) —
    이 함수는 아무것도 쓰지 않으므로 호출자가 그 원칙을 지킨다."""
    names = [str(track.get("group_name") or "") for track in tracks]
    conflict = find_overlapping_group_tracks(names)
    if conflict is None:
        return None
    first, second = conflict
    return (
        f"콘솔 그룹 '{first}'와 '{second}'는 같은 장비를 겹쳐 잡습니다 — "
        "두 그룹을 동시에 트랙으로 쓸 수 없습니다."
    )


def _track(
    *,
    group_no: int | None,
    group_no_confirmed: bool,
    group_name: str,
    cues: list[BeatGridCue],
) -> BeatGridTrack:
    return BeatGridTrack(
        group_no=group_no,
        group_no_confirmed=group_no_confirmed,
        group_name=group_name,
        layer_role=resolve_layer_role(group_name),
        cues=cues,
    )


def _cue(bar: int, label: str) -> BeatGridCue:
    return BeatGridCue(bar=bar, label=label)


def _love_attack_tracks() -> list[BeatGridTrack]:
    """LOVE ATTACK의 0~25마디 첫 기본값(배치 규칙서 §2·§4, 손으로 짠 배치를
    그대로 옮긴 것 — 지어낸 값이 아니다).

    배치 규칙서 §2의 역할별 시퀀스 6개(SCENE/BACK PULSE/SIDE CHASE/
    MOVER-U MOVE/MOVER-D MOVE/ACCENT) 중, REQ-LDBEAT-004가 확정한 "줄
    하나 = 콘솔 그룹 하나" 모양에 **깨끗이 1:1로 맞는 넷**(BACK PULSE →
    Group 4, SIDE CHASE → Group 7(SIDE-ALL), MOVER-U MOVE → Group 11,
    MOVER-D MOVE → Group 12 — 그룹 번호는 배치 규칙서 §2 "그룹(선택 하나)"
    칸에 적힌 숫자 그대로다)과, ACCENT를 그 모양에 맞춰 **그룹별로 쪼갠
    둘**(BLIND·STROBE — 역할 하나가 그룹 둘을 쓰는 것 자체가 교정 대상이던
    옛 모양이라, 쪼개는 쪽이 REQ-LDBEAT-004에 맞다)만 트랙으로 둔다.

    **SCENE은 트랙에서 뺐다(지어내지 않음)** — §2 표가 그 그룹 칸에 적은
    값은 "여럿(정적 값만)"이라 단일 콘솔 그룹이 아니다(WASH·FOH·무빙
    기본값을 걸치는 장면 레이어). 어느 그룹으로 쪼갤지는 이 plan-phase의
    증거(배치 규칙서·t525)가 답하지 않으므로, 추측 대신 director 확인이
    필요한 빈틈으로 progress.md에 남긴다.

    그룹 번호 확인 상태: BACK·SIDE-ALL·MOVER-U·MOVER-D는 배치 규칙서 §2가
    직접 적은 숫자이고 BLIND는 t525(`.moai/reports/t525/verdict.md` §②,
    `probe_groups.py`)가 그룹 14로 실측했다(둘 다 "확인됨"). STROBE는 이
    plan-phase 증거 어디에도 그룹 번호가 없다 — ``group_no=None``,
    ``group_no_confirmed=False``로 솔직하게 비워 둔다(M1/M3가 실제 쇼
    파일 조회로 채운다).
    """
    return [
        _track(
            group_no=4,
            group_no_confirmed=True,
            group_name="BACK",
            cues=[
                _cue(0, "앞박 1회"),
                _cue(3, "마디 4박마다"),
                _cue(7, "킥 1·2·4박 60%"),
                _cue(11, "—"),
                _cue(14, "—"),
                _cue(18, "킥 1·2·4박 100%"),
                _cue(22, "킥 1·2·4박 100%"),
            ],
        ),
        _track(
            group_no=7,
            group_no_confirmed=True,
            group_name="SIDE-ALL",
            cues=[
                _cue(0, "—"),
                _cue(3, "—"),
                _cue(7, "—"),
                _cue(11, "SIDE-L/R 2·4박 번갈이"),
                _cue(14, "가속(마디마다 두 배)"),
                _cue(18, "—"),
                _cue(22, "—"),
            ],
        ),
        _track(
            group_no=11,
            group_no_confirmed=True,
            group_name="MOVER-U",
            cues=[
                _cue(0, "바닥 쪽 좁은 빔, 정지"),
                _cue(3, "5마디 1박 위치 한 칸 올림"),
                _cue(7, "정지"),
                _cue(11, "기울인 자리에서 느린 팬 흔들기"),
                _cue(14, "가속 스윕 4박→2박→1박→반 박"),
                _cue(18, "18마디 위로 열고 19마디부터 팬 웨이브(한 바퀴 2박)"),
                _cue(22, "22마디 1박에 멈춰 섬"),
            ],
        ),
        _track(
            group_no=12,
            group_no_confirmed=True,
            group_name="MOVER-D",
            cues=[
                _cue(0, "바닥 쪽, 정지"),
                _cue(3, "5마디 1박 위치 한 칸 올림"),
                _cue(7, "틸트 웨이브, 한 바퀴 2마디, 위상 펼침"),
                _cue(11, "11마디 1박 새 자리, 정지"),
                _cue(14, "U 와 같은 스윕"),
                _cue(18, "위로 연 자리, 정지"),
                _cue(22, "22마디부터 틸트 웨이브(한 바퀴 2박)"),
            ],
        ),
        _track(
            group_no=14,
            group_no_confirmed=True,
            group_name="BLIND",
            cues=[
                # ACCENT 열의 0~25마디 구간 실제 발화는 이 둘뿐 — 63·67마디
                # (스트로브 포함)는 범위 밖(§4 범위, §3 전체 배치).
                _cue(17, "17마디 3·4박 전부 비움(예고)"),
                _cue(18, "18마디 1박 BLIND 100% 2박"),
            ],
        ),
        _track(
            group_no=None,
            group_no_confirmed=False,
            group_name="STROBE",
            # 0~25마디 구간에는 스트로브 발화가 없다(63·67마디부터) — 빈 트랙은
            # 거짓이 아니라 이 구간의 정확한 모습이다.
            cues=[],
        ),
    ]


def default_beat_grid(song_title: str) -> BeatGridView:
    """``song_title``의 곡별 기본값(REQ-LDBEAT-006). LOVE ATTACK 외 곡은
    빈 트랙 + "이 곡의 기본값 없음" 안내(AC-LDBEAT-007) — 강제 적용 없음."""
    bar_start, bar_end = DEFAULT_BAR_RANGE
    normalized = (song_title or "").strip().casefold()
    if normalized == LOVE_ATTACK_TITLE.casefold():
        tracks = _love_attack_tracks()
        source = "love_attack_default"
        note = None
    else:
        tracks = []
        source = "empty"
        note = _NO_DEFAULT_NOTE
    return BeatGridView(
        song_title=song_title or "",
        bar_range={"start": bar_start, "end": bar_end},
        tracks=tracks,
        source=source,
        note=note,
    )


def attach_beat_grid_default(timeline: Mapping[str, object]) -> dict[str, object]:
    """``timeline`` 사전의 사본에 격자를 싣는다 — **있으면 보존, 없으면
    기본값**(REQ-LDBEAT-006, M2 임베드 설계). 원본은 건드리지 않는다
    (``cue_sheet_edit.py``와 같은 사본-후-머지 관행).

    이 함수는 콘솔에 아무것도 쓰지 않고, 타임라인의 다른 칸도 건드리지
    않는다 — 추가되는 키는 ``beat_grid`` 하나뿐이다."""
    merged = dict(timeline)
    if merged.get("beat_grid") is not None:
        return merged
    song_title = str(merged.get("song_title") or "")
    merged["beat_grid"] = default_beat_grid(song_title)
    return merged
