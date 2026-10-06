# ruff: noqa: E501 — 페이지에 끼워 넣는 JS 시험 문자열이라 줄 길이 규칙을 끈다
"""t514 — 필터 버튼이 실제로 행·막대를 숨기는지 헤드리스 Chrome 으로 잰다.

보고서 사본 끝에 시험 스크립트를 붙여(원본은 그대로) 버튼을 눌러 보고, 보이는 행 수·흐려진 막대 수를
<pre id='probe'> 에 적은 뒤 --dump-dom 으로 읽는다.
실행: uv run python .moai/reports/t514/filter_probe.py <html>
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
src = Path(sys.argv[1]).read_text(encoding="utf-8")
probe = """<pre id='probe'></pre><script>
setTimeout(() => {
  const rows = () => [...document.querySelectorAll('table.script tbody tr')].filter(t => !t.classList.contains('hide')).length;
  const off = () => document.querySelectorAll('.tl rect.off').length;
  const log = [];
  log.push(`start rows=${rows()} off=${off()}`);
  const click = k => document.querySelector(`.fb[data-k='${k}']`).click();
  click('pulse'); log.push(`pulse off: rows=${rows()} off=${off()}`);
  ['color','pos','move','chase','blind','strobe','etc'].forEach(click);
  log.push(`only pulse off->all off: rows=${rows()} off=${off()}`);
  click('strobe'); log.push(`strobe only on: rows=${rows()}`);
  document.querySelector('.fb.all').click(); log.push(`all on: rows=${rows()} off=${off()}`);
  document.getElementById('probe').textContent = log.join('\\n');
}, 100);
</script></body>"""
with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as fh:
    fh.write(src.replace("</body>", probe, 1))
dom = subprocess.run(
    [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--virtual-time-budget=3000",
        "--dump-dom",
        Path(fh.name).as_uri(),
    ],
    capture_output=True,
    text=True,
    timeout=60,
    check=True,
).stdout
print(re.search(r"<pre id=\"probe\">(.*?)</pre>", dom, re.S).group(1))
