"""LOVE ATTACK 의 라이브러리 시드 — 곡 제목·측정된 박·기본 격자·구간을 싣는 읽기 전용 투영.

구간은 규칙 보고서 §3 의 배치(인트로·벌스·프리·후렴·브리지·드롭·아웃트로)를 **측정된 마디
지도 위에** 옮긴 것이다. 옛 구간 초안(``.moai/reports/t537/love_attack_sections.json``)은 한
마디를 2.0초로 잡아 측정 지도와 어긋나므로 쓰지 않는다. 구간의 시작 시각은 고정 박 시각 픽스처
(``server/tests/fixtures/love_attack_beat_grid.json``)를 ``derive_bars`` 로 계산한 값이고, 시험
(``test_love_attack_sections.py``)이 그 계산과 같은지 지킨다. 마디 지도 전체는 「마디 지도 분석」이
곡 오디오에서 새로 만들어 초안의 ``bar_map`` 에 붙이므로 시드는 싣지 않는다.

싣는 값과 출처 — 저장소에 이미 있는 값이거나 실곡 분석에서 잰 값만 싣는다:

* ``bpm`` 112.0 — 박 회귀값 112.002 를 반올림(``server/tests/fixtures/love_attack_beat_grid.json``,
  카드 t550 이 중앙값 112.347 대신 회귀값으로 바꿨다).
* ``time_signature`` 4/4 — 배치 규칙서 §4 의 격자가 4/4 를 전제한다.
* ``beat_grid`` — ``server/design/beat_grid_data/love_attack.yaml`` 의 0~25마디 기본 격자.
  ``attach_beat_grid_default`` 가 붙인다(카드 t537, 감독 결정 2026-10-10).
* ``sections`` — 위 §3 배치를 측정 마디 지도에 옮긴 값. 킥 멈춤(33·61마디)은 뒤 구간에 붙이고,
  드럼머신(3~6마디)은 인트로로 묶었다. 마지막 구간은 곡의 끝을 저장소가 모르므로 끝을 적지 않는다.
* ``bar_count`` 83 — 실곡 마디 지도 분석 응답(``b-love-attack-seed-analyse.json`` 의
  ``bar_map.bar_count``, 2026-10-15 측정). 근거 파일은 ``.moai/reports`` 아래 git 무시 경로라
  저장소에는 없다.
* ``seconds_per_bar`` — ``60 / 112.002 × 4``.
  ``total_duration_ms`` 는 곡 끝을 저장소가 모르므로 ``None``.

화면이 읽는 키는 값이 없어도 키를 둔다. 값을 지어내지 않고 모양만 맞춘다: 목록은 빈 배열,
글자는 빈 문자열, 참·거짓(``mib``)은 ``False``, 숫자(``cue_number``·``d_level``)는 ``None``.
``trig_time_seconds`` 는 구간 시작 시각 ``start_ms / 1000`` 으로 계산한다(Sugar 시드와 같은 규칙).

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
#: 구간 배치 — (이름, 시작 마디, 시작 시각 ms). 마디 0은 못갖춘 박, 1부터는 다운비트다.
#: 같은 종류가 다시 나오면 번호를 붙인다. 시작 시각은 픽스처 박 시각을 ``derive_bars`` 로
#: 계산한 값이며, ``test_love_attack_sections.py`` 가 같은 계산과 맞는지 지킨다.
_SECTION_PLAN: tuple[tuple[str, int, int], ...] = (
    ("인트로", 0, 964),
    ("벌스 1", 7, 14362),
    ("프리 1", 14, 29350),
    ("후렴 1", 18, 37895),
    ("벌스 2", 33, 70055),
    ("프리 2", 42, 89374),
    ("후렴 2", 46, 97930),
    ("브리지", 61, 130055),
    ("드롭", 63, 134362),
    ("후렴 3", 67, 142907),
    ("아웃트로", 82, 175055),
)


def _love_attack_sections() -> list[dict[str, object]]:
    """구간 배치를 구간 항목으로 — 끝은 다음 구간의 시작이고, 마지막 구간은 끝을 적지 않는다."""
    sections: list[dict[str, object]] = []
    for position, (label, bar_start, start_ms) in enumerate(_SECTION_PLAN):
        section: dict[str, object] = {
            "index": position + 1,
            "label": label,
            "bar_start": bar_start,
            "start_ms": start_ms,
            # 화면이 읽는 키 — 값이 없으면 키는 두고 빈 값을 넣는다(값을 지어내지 않는다).
            "trig_time_seconds": start_ms / 1000,
            "cue_number": None,
            "d_level": None,
            "palette": [],
            "fx": [],
            "accents": [],
            "intensity": [],
            "fixture_groups": [],
            "position": "",
            "movement": "",
            "mood": "",
            "texture": "",
            "mib": False,
        }
        if position + 1 < len(_SECTION_PLAN):
            next_bar_start, next_start_ms = _SECTION_PLAN[position + 1][1:]
            section["bar_count"] = next_bar_start - bar_start
            section["end_ms"] = next_start_ms
        sections.append(section)
    return sections


def build_love_attack_timeline() -> dict[str, object]:
    """구간이 붙은 LOVE ATTACK 타임라인 페이로드(읽기 전용 리뷰 투영)."""
    timeline: dict[str, object] = {
        "song_title": LOVE_ATTACK_TIMELINE_NAME,
        "sequence_name": None,
        "sequence_number": None,
        "timing_mode": "timecode",
        "timecode_number": None,
        "lifecycle": "pending_approval",
        "approval": "pending_review",
        "director_decisions": [],
        "sections": _love_attack_sections(),
        "lint": [],
        "unresolved": [],
        "disabled": [],
        "readback": {"verified": None, "message": None},
        "bpm": 112.0,
        "time_signature": "4/4",
        # 실곡 마디 지도 분석 응답 b-love-attack-seed-analyse 의 bar_map.bar_count
        # (측정, 2026-10-15)
        "bar_count": 83,
        # 4/4, 회귀 BPM 112.002 기준. 곡 끝은 저장소가 모르므로 total_duration_ms 는 None 이다.
        "seconds_per_bar": 60 / 112.002 * 4,
        "total_duration_ms": None,
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
