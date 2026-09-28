"""t485 — 런북 브라우저 확인용 페이로드(콘솔은 가짜, 실기 접촉 0).

실제 세션을 인터뷰부터 끝까지 돌려(``test_song_analysis_to_timeline`` 하니스) 나간
``song_timeline`` 이벤트의 타임라인을 그대로 저장한다. 두 벌을 만든다.

- ``payload_causal.json`` — Q1 에 인과 문장 두 줄을 직접 입력한 곡
- ``payload_blank.json`` — Q1 을 빈 답으로 넘긴 곡(자동 초안)

실행: 워크트리 루트에서 ``uv run python .moai/reports/t485/make_payload.py``
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, ".")
from server.tests import test_song_analysis_to_timeline as seam  # noqa: E402

HERE = Path(__file__).parent
CAUSAL = "이 곡은 이별 노래다 → 그래서 주조색은 차가운 파랑\n→ 후렴에서만 흰색을 터뜨린다"
#: Q2 는 하니스 답("우주 색 조합")이 Q1 = "우주" 일 때만 나오는 제안 이름이라 색 이름으로
#: 바꾼다. 나머지(Q2B·Q3·Q4·Q5)는 하니스 답 그대로다.
REST = ["블루와 화이트", *seam._INTERVIEW_ANSWERS[2:]]


def timeline(q1: str) -> dict:
    seam._INTERVIEW_ANSWERS = [q1, *REST]
    analysis = seam._confirmed((0, 24_000, 2), (24_000, 48_000, 5), (48_000, 72_000, 3))
    with tempfile.TemporaryDirectory() as tmp:
        sent = seam._drive(Path(tmp), seam._NO_SECTIONS, analysis)
    events = seam._timeline_events(sent)
    if not events:
        for event in sent[-6:]:
            print(json.dumps(event, ensure_ascii=False)[:300])
    assert events, "타임라인 이벤트가 안 나갔다"
    return events[0]["timeline"]


def main() -> None:
    for name, q1 in (("payload_causal.json", CAUSAL), ("payload_blank.json", "")):
        data = timeline(q1)
        (HERE / name).write_text(json.dumps(data, ensure_ascii=False, indent=1))
        print(name, json.dumps(data["concept_bullet"], ensure_ascii=False))


if __name__ == "__main__":
    main()
