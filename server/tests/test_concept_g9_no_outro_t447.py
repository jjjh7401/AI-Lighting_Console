"""카드 t447 — Outro 없이 cue_only 프레이즈로 끝나는 곡의 G9 누출 검사.

재현(``origin/main@187f6061``): 샘플 곡에서 마지막 구간을 빼 후렴으로 끝나게
하면 6곡이 ``evaluate_song`` 에서 ``VocabError: reduce: ref
'song_release_reference' 가 bases 에 없음`` 으로 멈췄다. ``build_song`` 은
끝까지 갔고, 멈춘 곳은 G9 의 ``verify_no_cue_only_leak`` 이 cue_only 행을 빼고
다시 해석하는 두 번째 ``resolve_sequence`` 였다 — 곡의 Release 기준 이름이
마지막 시퀀스 행(후렴 「악기 추가」 cue_only 프레이즈)에 붙어 있어서 그 행과
함께 사라졌다(``.moai/reports/t447/baseline_before.txt``).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from server.concept.gates import GATE_NAMES, build_song, evaluate_song

_FIXTURE = Path(__file__).parent / "fixtures" / "pilot_baseline.json"
_SONGS = {
    s["song"]: s for s in json.loads(_FIXTURE.read_text(encoding="utf-8")) if "error" not in s
}
_G9 = next(name for name in GATE_NAMES if name.startswith("G9"))

#: 마지막 구간을 빼면 후렴으로 끝나는 곡(재현에서 6곡 전부 VocabError).
_ENDS_ON_CHORUS = (
    "Club Diver.mp3",
    "Cut and Run.mp3",
    "Ice cream.mp3",
    "Morning.mp3",
    "Rain.mp3",
    "scott-buckley-neon.mp3",
)


def _without_last_section(song_name: str) -> dict[str, object]:
    song = copy.deepcopy(_SONGS[song_name])
    song["sections"] = song["sections"][:-1]
    return song


@pytest.mark.parametrize("song_name", _ENDS_ON_CHORUS)
def test_premise_the_song_ends_on_a_cue_only_phrase(song_name):
    """전제 실측 — 이 입력의 마지막 시퀀스 행이 정말 cue_only 다(아니면 이
    시험은 결함을 재현하지 않는다)."""
    rows = build_song(_without_last_section(song_name)).rows
    last_sequence_row = rows[-2]  # rows[-1] 은 곡 끝 안전 큐
    assert last_sequence_row["tracking"] == "cue_only"


@pytest.mark.parametrize("song_name", _ENDS_ON_CHORUS)
def test_g9_judges_a_song_that_ends_without_outro(song_name):
    results = evaluate_song(_without_last_section(song_name))
    assert results[_G9].passed is True, results[_G9].detail
