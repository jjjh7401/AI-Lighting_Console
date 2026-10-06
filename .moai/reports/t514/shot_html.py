"""t514 — 감독용 HTML 을 헤드리스 Chrome 으로 찍어 눈으로 확인한다(화면 너비·높이 인자).

실행: uv run python .moai/reports/t514/shot_html.py <html> <png> [폭] [높이]
"""

import subprocess
import sys
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
src, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
w, h = (sys.argv[3], sys.argv[4]) if len(sys.argv) > 4 else ("1200", "2400")
subprocess.run(
    [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        f"--window-size={w},{h}",
        f"--screenshot={out}",
        src.as_uri(),
    ],
    check=True,
    capture_output=True,
    timeout=60,
)
print(out, out.stat().st_size)
