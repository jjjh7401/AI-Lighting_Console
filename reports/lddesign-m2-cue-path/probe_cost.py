"""방향별 비용 실측 — 길 A 에 색을 붙이는 데 필요한 부품이 이미 있는가."""

import sys

sys.path.insert(0, ".")

from server.design.color_names import COLOR_PALETTE_SEQUENCE, resolve_color_name
from server.web.session import _color_apply_command

print("=== 1) 설계층이 내는 팔레트 이름을 resolve_color_name 이 아는가")
# probe_path_a.py 가 실제로 넣은 색 + 컴포저 기본 팔레트.
names = ["blue", "cyan", "amber", "white", "magenta", "red"]
resolved = {}
for n in names:
    rgb = resolve_color_name(n)
    resolved[n] = rgb
    print(f"  {n:9} -> {rgb}")
unknown = [n for n, v in resolved.items() if v is None]
print(f"  모르는 이름: {len(unknown)}/{len(names)} {unknown}")

print()
print("=== 2) 그 RGB 를 콘솔 값 라인으로 바꾸는 함수가 이미 있는가")
for n in names:
    if resolved[n] is not None:
        print(f"  {n:9} -> {_color_apply_command([1, 2, 3, 4], resolved[n])}")

print()
print("=== 3) 앱이 아는 팔레트 이름 전체")
print(f"  COLOR_PALETTE_SEQUENCE {len(COLOR_PALETTE_SEQUENCE)}개")
print(f"  {[n for n, _ in COLOR_PALETTE_SEQUENCE]}")
