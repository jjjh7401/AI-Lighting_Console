"""실제 운영 팔레트 이름 중 무엇이 RGB 로 해소되지 않는가 — 전수."""

import sys

sys.path.insert(0, ".")

from server.design.color_names import _KO_EN_COLOR_EQUIV, resolve_color_name
from server.web.session import _ARC_PALETTE

print("=== _ARC_PALETTE (session.py:817) — 아크가 실제로 내는 이름 전수")
arc_names = sorted({n for names in _ARC_PALETTE.values() for n in names})
arc_fail = []
for n in arc_names:
    rgb = resolve_color_name(n)
    if rgb is None:
        arc_fail.append(n)
    print(f"  {n:16} -> {rgb}")
print(f"  해소 실패 {len(arc_fail)}/{len(arc_names)}: {arc_fail}")

print()
print("=== 감독 한국어 표기 (_KO_EN_COLOR_EQUIV) 전수")
ko_fail = []
for ko in sorted(_KO_EN_COLOR_EQUIV):
    rgb = resolve_color_name(ko)
    if rgb is None:
        ko_fail.append(ko)
print(f"  해소 실패 {len(ko_fail)}/{len(_KO_EN_COLOR_EQUIV)}: {ko_fail}")

print()
print("=== 시험 픽스처가 쓰는 맨 'white'")
print(f"  white -> {resolve_color_name('white')}")
print("  (운영 아크는 'warm white' 를 쓴다 — 맨 white 는 시험 픽스처 값)")
