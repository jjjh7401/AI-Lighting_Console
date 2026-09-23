"""t445 probe — 두 입구(경로 A 인터뷰 · 경로 B 곡 업로드)의 후렴 분할 큐 주색.

같은 곡 모양: 후렴 32초(16마디 @120bpm) 3회 + 사이 절. 같은 답(Q2 블루 + Q2B).
실행: uv run python .moai/reports/t445/probe_two_paths.py
"""

from server.design.interview import Q2_PALETTE, Q2B_COLOR_USAGE, AnswerRecord
from server.design.profile import MusicProfile
from server.design.rig import build_rig_profile
from server.design.section_palette import role_for_songcue_label
from server.design.song_plan import TimingPlan
from server.looks.loader import load_library_from_dir
from server.looks.songcue import (
    _look_color,
    map_sections_to_looks,
    parse_sections,
    split_selections_for_density,
)
from server.orchestrator.tools import _override_songcue_main_color
from server.spatial.position_cuesheet import PositionSheetSection
from server.web.session import _build_unified_song_plan, _split_sections_for_density


def _records(color_usage):
    def rec(step, value):
        return AnswerRecord(
            step=step,
            proposals=(),
            choice=None,
            free_text=str(value),
            value=value,
            confirmed=True,
            source="standard",
        )

    return (rec(Q2_PALETTE, "블루"), rec(Q2B_COLOR_USAGE, color_usage))


def path_a(color_usage):
    secs = [PositionSheetSection(name="Intro", start_ms=0, mood="", d_level=2, role="intro")]
    t = 8000
    for _ in range(3):
        secs.append(
            PositionSheetSection(name="Verse", start_ms=t, mood="", d_level=3, role="verse")
        )
        t += 16000
        secs.append(
            PositionSheetSection(name="Chorus", start_ms=t, mood="", d_level=5, role="chorus")
        )
        t += 32000
    secs.append(PositionSheetSection(name="Outro", start_ms=t, mood="", d_level=2, role="outro"))
    profile = MusicProfile(bpm=120.0, palette=("블루",))
    expanded, origin, _ = _split_sections_for_density(
        secs, profile=profile, color_usage=color_usage
    )
    plan = _build_unified_song_plan(
        sections=expanded,
        profile=profile,
        rig=build_rig_profile(patch=[], groups={}, coords=[]),
        records=_records(color_usage),
        timing=TimingPlan.manual_go(),
        sequence_no=445,
        section_origin=origin,
    )
    return [(d.section.label, d.palette.colors[0]) for d in plan.sections if d.role == "chorus"]


def path_b(color_usage):
    raw = (
        ("Intro", "0:00"),
        ("Verse", "0:08"),
        ("Chorus", "0:24"),
        ("Verse", "0:56"),
        ("Chorus", "1:12"),
        ("Verse", "1:44"),
        ("Chorus", "2:00"),
        ("Outro", "2:32"),
    )
    library = load_library_from_dir()
    selections = map_sections_to_looks(parse_sections(raw), library, "edm")
    selections, _ = split_selections_for_density(selections, bpm=120.0, song_end_ms=160_000)
    overridden, notes = _override_songcue_main_color(selections, records=_records(color_usage))
    rows = []
    for sel in overridden:
        if role_for_songcue_label(sel.section.label) != "chorus" or sel.look is None:
            continue
        rgb = {c.name: c.value for c in _look_color(sel.look)}
        rows.append(
            (
                f"{sel.section.label} {sel.section.instance}",
                (rgb.get("ColorRGB_R"), rgb.get("ColorRGB_G"), rgb.get("ColorRGB_B")),
            )
        )
    return rows, notes


for usage in ("modulate", "split_swap"):
    a = path_a(usage)
    b, notes = path_b(usage)
    print(f"== {usage}")
    print("A cues", len(a), "primaries", sorted({p for _, p in a}), a)
    print("B cues", len(b), "primary RGB", sorted({p for _, p in b}), b, "notes", notes)
