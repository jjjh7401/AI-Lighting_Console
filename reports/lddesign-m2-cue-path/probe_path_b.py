"""길 B(코파일럿 LLM 툴) 대조군 — 같은 탐침이 색을 잡아내는가. (임시, 커밋 안 함)"""

import sys

sys.path.insert(0, ".")

from server.looks.loader import load_library_from_dir
from server.looks.songcue import (
    build_songcue_bundle,
    map_sections_to_looks,
    parse_sections,
)
from server.tests.busking_fixtures import FULL_RIG
from server.tests.test_looks_instantiate import _groups
from server.tests.test_songcue_ladder import _sequences

sections = parse_sections((("Intro", "0:00"), ("Verse", "0:20"), ("Chorus", "0:40")))
library = load_library_from_dir()
selections = map_sections_to_looks(sections, library, "edm")

bundle = build_songcue_bundle(
    "Probe Song",
    selections,
    sequences_section=_sequences(),
    groups_section=_groups(*FULL_RIG),
)

cmds = list(bundle.commands)
print("=== 길 B 가 내는 콘솔 명령")
for c in cmds:
    print("   ", c)
print()
print(f"  명령 총 {len(cmds)}줄")

# 길 A 탐침과 **같은** 판별 토큰을 쓴다 — 계기를 바꾸지 않는다.
tokens = ("color", "colour", "cyan", "amber", "magenta", "blue", "red", "white")
hits = [c for c in cmds if any(t in c.lower() for t in tokens)]
print(f"  색 관련 줄: {len(hits)}")
for h in hits[:12]:
    print("    ->", h)
