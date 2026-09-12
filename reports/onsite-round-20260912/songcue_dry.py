"""실기 dry-run: 살아 있는 콘솔에서 rig 를 읽고, 곡 큐 번들을 **세우기만** 한다.
쓰기 0 — build_songcue_bundle 은 순수 함수이고, 여기서는 명령을 보내지 않는다."""

import json

from server.looks.loader import load_library_from_dir
from server.looks.songcue import (
    build_songcue_bundle,
    map_sections_to_looks,
    parse_sections,
    render_songcue_report,
)
from server.orchestrator.tools import rig_object, rig_section
from server.safety.bootstrap import build_console_stack

SONG_A = dict(
    title="DryA",
    genre="edm",
    sections=[
        {"name": "Intro", "start": "0:00", "dynamics": 2},
        {"name": "Verse", "start": "0:16", "dynamics": 2},
        {"name": "Chorus", "start": "0:48", "dynamics": 4},
        {"name": "Verse", "start": "1:20", "dynamics": 3},
        {"name": "Chorus", "start": "1:52", "dynamics": 4},
        {"name": "Breakdown", "start": "2:24", "dynamics": 2},
        {"name": "Drop", "start": "2:40", "dynamics": 5},
        {"name": "Outro", "start": "3:12", "dynamics": 1},
    ],
)


def main():
    stack = build_console_stack(receive_port=9005)
    try:
        q = stack.gate.state_port.query_state
        raw_seqs = q("DataPool/Sequences")
        raw_groups = q("DataPool/Groups")
        seqs = rig_section([rig_object(c) for c in raw_seqs.get("children", [])], raw_seqs)
        groups = rig_section([rig_object(c) for c in raw_groups.get("children", [])], raw_groups)
        print("== 라이브 rig ==")
        print("  sequences:", json.dumps(seqs, ensure_ascii=False)[:200])
        print("  groups   :", json.dumps(groups, ensure_ascii=False)[:200])
        lib = load_library_from_dir()
        sections = parse_sections(SONG_A["sections"])
        sel = map_sections_to_looks(sections, lib, SONG_A["genre"])
        bundle = build_songcue_bundle(
            SONG_A["title"], sel, sequences_section=seqs, groups_section=groups
        )
        print("\n== 리포트 ==")
        print(render_songcue_report(bundle))
        print("\n== A 반복 후렴 ==")
        for s in bundle.sections:
            lk = s.selection.look
            print(
                f"  cue {s.cue_number:>4} {s.section.label!r}"
                f"#{s.section.instance} look={getattr(lk, 'look_id', None)}"
            )
        print("\n== 저장/건너뜀 ==")
        print("  stored:", [x.cue_number for x in bundle.stored_sections])
        for k in bundle.skipped:
            print("  skipped:", k)
        print("\n== C 드롭 앞 어둠 ==")
        for s in bundle.darkened_sections:
            print("  darkened:", s.cue_number, s.section.label, s.darkness)
        for w in bundle.withheld_darkness:
            print("  withheld:", w.cue_number, w.reason)
        print("\n== D 무빙 ==")
        for s in bundle.movement_sections:
            print("  MOVES:", s.cue_number, s.section.label, s.movement)
        for w in bundle.withheld_movement:
            print("  withheld:", w.cue_number, w.section.label, w.reason)
    finally:
        stack.stop()


main()
