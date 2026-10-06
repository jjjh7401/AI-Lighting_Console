"""t509 — 앱 분석 경로가 LOVE ATTACK 에 내는 BPM·구간 경계·D 등급·구간 이름 (읽기 전용 호출).

실행(저장소 루트):
    .venv/bin/python .moai/reports/t509/app_sections.py "<LOVE ATTACK.mp3>" <out.json>

앱과 같은 함수를 그대로 부른다. 제품 코드는 바꾸지 않는다.
- server/audio/analyze.py ``analyze`` — 업로드 확인 카드가 부르는 그 함수(session.py:11384)
- d_candidates → 확인 카드 제안 구간(session.py:11386-11393)
- 확정 기본값 경로의 역할·이름: server/design/upload_song_plan.py:66-69 와 같은 두 함수
  (``_infer_confirmed_role`` → ``_confirmed_section_names``)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")

from server.audio.analyze import AnalysisResult, analyze  # noqa: E402
from server.design.song_cue_render import (  # noqa: E402
    _confirmed_section_names,
    _infer_confirmed_role,
)

audio, out = Path(sys.argv[1]), Path(sys.argv[2])
result = analyze(audio.read_bytes())
if not isinstance(result, AnalysisResult):
    print("FAILURE", result.reason)
    sys.exit(1)

levels = [c.d_level for c in result.d_candidates]
roles = [_infer_confirmed_role(i, levels) for i in range(len(levels))]
names = _confirmed_section_names(roles)
sections = [
    {
        "i": i,
        "name": name,
        "role": role,
        "d": c.d_level,
        "start_ms": c.start_ms,
        "end_ms": c.end_ms,
    }
    for i, (c, role, name) in enumerate(zip(result.d_candidates, roles, names, strict=True))
]
payload = {
    "audio": str(audio),
    "bpm": result.bpm,
    "bpm_confidence": result.bpm_confidence,
    "boundaries_ms": list(result.boundaries_ms),
    "n_onsets": len(result.onsets_ms),
    "sections": sections,
}
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
print(f"bpm {result.bpm} confidence {result.bpm_confidence:.3f} sections {len(sections)}")
for s in sections:
    print(
        f"{s['i']:2d} {s['start_ms'] / 1000:7.2f}-{s['end_ms'] / 1000:7.2f} D{s['d']} {s['name']}"
    )
