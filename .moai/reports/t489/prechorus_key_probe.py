"""t489 부수 관찰 — Pre-Chorus(D4) 시트 KEY 가 Verse(D3) 보다 낮은 원인을 잰다.

t486 실경로 곡을 그대로 조립하고, 큐마다 KEY 와 `pre_drop_from`(드롭 앞 어둠이
내리기 전 값, 카드 t462)을 출력한다. 그리고 드롭 앞 어둠만 끈 대조군을 같이 낸다.
실행: `uv run python .moai/reports/t489/prechorus_key_probe.py`
"""

import dataclasses
import sys

sys.path.insert(0, ".")
import server.design.song_cue_composer as composer
from server.design.song_plan import DLevelDecision, PaletteDecision
from server.tests.test_song_timeline_concept_report_wiring import _plan, _section
from server.web.session import _infer_confirmed_role

SONG = [
    ("Intro", 2, "blue"),
    ("Verse 1", 3, "blue"),
    ("Pre-Chorus 1", 4, "amber"),
    ("Chorus 1", 5, "red"),
    ("Verse 2", 3, "blue"),
    ("Pre-Chorus 2", 4, "amber"),
    ("Chorus 2", 5, "red"),
    ("Bridge", 2, "cyan"),
    ("Chorus 3", 5, "red"),
    ("Outro", 3, "blue"),
]


def plan():
    d_levels = [d for _, d, _ in SONG]
    sections = tuple(
        dataclasses.replace(
            _section(i + 1, label, i * 12_000),
            d=DLevelDecision(level=d, source="section_mood"),
            palette=PaletteDecision(colors=(color,), source="director"),
            role=_infer_confirmed_role(i, d_levels),
        )
        for i, (label, d, color) in enumerate(SONG)
    )
    return _plan(bpm=120.0, sections=sections)


def keys(result):
    return [(c.dimmer.key_pct, c.pre_drop_from) for c in result.bundle.cues]


real = keys(composer.compose_song_cue_bundle(plan()))
original = composer._apply_pre_drop_darkness
composer._apply_pre_drop_darkness = lambda cues, labels: cues
control = keys(composer.compose_song_cue_bundle(plan()))
composer._apply_pre_drop_darkness = original

print("label | D | KEY | pre_drop_from | KEY without pre-drop darkness")
for (label, d, _), (key, frm), (ctl, _f) in zip(SONG, real, control, strict=True):
    print(f"{label} | {d} | {key} | {frm} | {ctl}")
