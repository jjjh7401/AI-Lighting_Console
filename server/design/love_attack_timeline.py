"""LOVE ATTACK 의 라이브러리 시드 — 곡 제목·측정된 박·기본 격자를 싣는 읽기 전용 투영.

Sugar 시드와 달리 **구간(섹션) 계획은 옮기지 않는다**. 저장소의 구간 초안
(``.moai/reports/t537/love_attack_sections.json``)은 네 구간뿐이고 한 마디를 2.0초로
잡고 있어, 측정된 마디 지도(한 마디 약 2.14초 · 벌스 1 이 14.4초의 7마디에서 시작)와
맞지 않는다. 어긋난 마디 번호를 시드에 굳히지 않으려고 구간은 비워 두고, 마디 지도는
「마디 지도 분석」이 곡 오디오에서 새로 만들어 초안의 ``bar_map`` 에 붙인다.

싣는 값과 출처 — 전부 저장소에 이미 있는 값이고, 없는 값은 키를 내지 않는다:

* ``bpm`` 112.0 — 박 회귀값 112.002 를 반올림(``server/tests/fixtures/love_attack_beat_grid.json``,
  카드 t550 이 중앙값 112.347 대신 회귀값으로 바꿨다).
* ``time_signature`` 4/4 — 배치 규칙서 §4 의 격자가 4/4 를 전제한다.
* ``beat_grid`` — ``server/design/beat_grid_data/love_attack.yaml`` 의 0~25마디 기본 격자.
  ``attach_beat_grid_default`` 가 붙인다(카드 t537, 감독 결정 2026-10-10).

``sequence_number`` · ``timecode_number`` 는 저장소 어디에도 없어 비워 둔다.
"""

from __future__ import annotations

from server.design.beat_grid import LOVE_ATTACK_TITLE, attach_beat_grid_default

__all__ = [
    "LOVE_ATTACK_ENTRY_ID",
    "LOVE_ATTACK_TIMELINE_NAME",
    "build_love_attack_timeline",
    "love_attack_library_entry",
]

LOVE_ATTACK_ENTRY_ID = "seed-love-attack-r1"
LOVE_ATTACK_TIMELINE_NAME = LOVE_ATTACK_TITLE
#: 시드의 생성일. 시드는 실행 때마다 새로 저장되는 값이 아니라 고정된 한 판이다.
_LOVE_ATTACK_SAVED_AT = "2026-10-15T00:00:00+00:00"


def build_love_attack_timeline() -> dict[str, object]:
    """구간 없는 LOVE ATTACK 타임라인 페이로드(읽기 전용 리뷰 투영)."""
    timeline: dict[str, object] = {
        "song_title": LOVE_ATTACK_TIMELINE_NAME,
        "sequence_name": None,
        "sequence_number": None,
        "timing_mode": "timecode",
        "timecode_number": None,
        "lifecycle": "pending_approval",
        "approval": "pending_review",
        "director_decisions": [],
        "sections": [],
        "lint": [],
        "unresolved": [],
        "disabled": [],
        "readback": {"verified": None, "message": None},
        "bpm": 112.0,
        "time_signature": "4/4",
    }
    return attach_beat_grid_default(timeline)


def love_attack_library_entry() -> dict[str, object]:
    """``SongTimelineLibrary`` 항목 한 칸 — {id, name, saved_at, timeline}."""
    return {
        "id": LOVE_ATTACK_ENTRY_ID,
        "name": LOVE_ATTACK_TIMELINE_NAME,
        "saved_at": _LOVE_ATTACK_SAVED_AT,
        "timeline": build_love_attack_timeline(),
    }
