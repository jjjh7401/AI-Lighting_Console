"""카드 t452 — 곡 끝 안전 큐의 ``reduce ref`` 기준 행이 cue_only 이면 G9 가 깨진다.

4초 간격 5구간 곡(t441 ``_RAW_SECTIONS_B``)은 마지막 시퀀스 행이 프레이즈
큐(``tracking="cue_only"``)다. 기준 이름 ``song_release_reference`` 를 그
행에 붙이면, G9 의 누출 검사(:func:`verify_no_cue_only_leak`)가 cue_only 행을
빼고 다시 해석할 때 기준 이름도 함께 사라져 안전 큐의 ``reduce`` 가
``VocabError`` 로 거절된다(REQ-021 — ref 가 주어졌는데 bases 에 없으면 거절).
운영 경로(``_run_concept_pipeline``)는 이 예외를 ``available: False`` 로
삼키므로 콘솔 명령은 영향이 없지만, 컨셉 리포트는 통째로 사라진다.
"""

from __future__ import annotations

from server.concept.gates import _RELEASE_REF_BASE_NAME, build_song, evaluate_song
from server.concept.session_bridge import (
    _raw_sections_from_pairs,
    build_concept_report_from_songcue_sections,
)
from server.concept.tracking import verify_no_cue_only_leak

#: t441 ``_RAW_SECTIONS_B`` 와 같은 곡 — 4초 간격, 마지막 Chorus 가 꼬리 15초.
_PAIRS = [("Intro", 0), ("Chorus", 4000), ("Verse", 8000), ("Drop", 12000), ("Chorus", 16000)]


def _raw_song() -> dict[str, object]:
    return {"song": "t452", "bpm": 120.0, "sections": _raw_sections_from_pairs(_PAIRS)}


def test_last_sequence_row_is_cue_only_in_this_song() -> None:
    """전제 확인 — 이 곡이 정말 "마지막 시퀀스 행이 cue_only" 인 곡인가.
    이 전제가 무너지면 아래 시험은 결함을 재지 않는다."""
    rows = build_song(_raw_song()).rows
    sequence = [row for row in rows if row.get("kind") != "safety"]
    assert sequence[-1].get("tracking") == "cue_only"


def test_release_reference_is_registered_on_a_tracked_row() -> None:
    rows = build_song(_raw_song()).rows
    owners = [row for row in rows if row.get("base_name") == _RELEASE_REF_BASE_NAME]
    assert len(owners) == 1
    assert owners[0].get("tracking") != "cue_only"


def test_leak_check_resolves_without_cue_only_rows() -> None:
    assert verify_no_cue_only_leak(build_song(_raw_song()).rows) is True


def test_g9_is_judged_not_raised() -> None:
    gates = evaluate_song(_raw_song())
    g9 = next(result for name, result in gates.items() if name.startswith("G9"))
    assert g9.passed is True, g9.detail


def test_production_report_is_available() -> None:
    """운영 경로 — 예외가 ``available: False`` 로 삼켜지지 않고 리포트가 선다."""
    report = build_concept_report_from_songcue_sections(
        "t452", 120.0, [(name, start_ms) for name, start_ms in _PAIRS]
    )
    assert report["available"] is True, report
