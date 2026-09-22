"""방향 2 실측 — 길 B 에 설계·검사를 붙이려면 무엇이 없는가.

검사(`_lint_report`)와 MIB(`_apply_mib`)는 `UnifiedSongLightingPlan` /
`ComposedCue` 위에서만 돈다. 그래서 길 B 를 검사에 태우려면 길 B 의 자료를
`UnifiedSongLightingPlan` 으로 바꾸는 변환기가 있어야 한다. 그 변환기가
**무엇을 지어내야 하는지**를 필드 단위로 센다.
"""

import dataclasses
import sys

sys.path.insert(0, ".")

from server.design.song_plan import SectionDecision, UnifiedSongLightingPlan
from server.looks.loader import load_library_from_dir
from server.looks.songcue import SongCueLookSelection, map_sections_to_looks, parse_sections

sections = parse_sections((("Intro", "0:00"), ("Verse", "0:20"), ("Chorus", "0:40")))
selections = map_sections_to_looks(sections, load_library_from_dir(), "edm")

print("=== 길 B 가 실제로 들고 있는 것 (SongCueLookSelection)")
have = {f.name for f in dataclasses.fields(SongCueLookSelection)}
for f in dataclasses.fields(SongCueLookSelection):
    print(f"  {f.name}")

print()
print("=== 길 A 검사가 요구하는 것 (SectionDecision)")
# 길 B 자료로 직접 채울 수 있는 필드 ↔ 지어내야 하는 필드
suppliable = {
    "section": "SongCueSection 에서 라벨·시각을 옮길 수 있다",
    "d": "requested_dynamics 로 근사 가능(세기 목록 -> 단일 D레벨은 손실)",
}
need = [f.name for f in dataclasses.fields(SectionDecision) if f.default is dataclasses.MISSING]
invent = [n for n in need if n not in suppliable]
for n in need:
    mark = "채울 수 있음" if n in suppliable else "지어내야 함"
    note = suppliable.get(n, "길 B 자료에 대응 항목 없음 — Look 안에 녹아 있어 역산 불가")
    print(f"  {n:10} {mark:8} — {note}")

print()
print(f"  필수 {len(need)}개 중 지어내야 하는 것: {len(invent)}개 {invent}")

print()
print("=== 계획 수준에서 더 필요한 것 (UnifiedSongLightingPlan)")
plan_need = [
    f.name for f in dataclasses.fields(UnifiedSongLightingPlan) if f.default is dataclasses.MISSING
]
plan_have = {"song_title"}
for n in plan_need:
    mark = "채울 수 있음" if n in plan_have else "지어내야 함"
    print(f"  {n:14} {mark}")
print(
    f"  필수 {len(plan_need)}개 중 지어내야 하는 것: "
    f"{len([n for n in plan_need if n not in plan_have])}개"
)

print()
print("=== 기존 SectionDecision 생산자는 몇 개인가")
print("  session.py:2061 하나뿐 — 감독 인터뷰/확정 분석에서 만든다")
print("  (source='song_design_interview', palette/position/texture 는 감독 답변에서 파생)")
