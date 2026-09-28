"""t480 — 파일의 표지 줄부터 (끝 표지 앞까지 또는 끝까지)를 다른 파일 내용으로 바꾼다.

시험 파일 다시 쓰기용.

실행(저장소 루트):
  uv run python .moai/reports/t480/splice_tail.py <대상> <시작 표지> <새 내용 파일> [끝 표지]
"""

import sys
from pathlib import Path

target, marker, tail = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]).read_text()
end_marker = sys.argv[4] if len(sys.argv) > 4 else None
src = target.read_text()
at = src.index(marker)
end = src.index(end_marker, at) if end_marker else len(src)
target.write_text(src[:at] + tail + src[end:])
print("ok", target)
