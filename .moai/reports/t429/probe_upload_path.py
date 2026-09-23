"""t429 — 샘플 곡 전부를 업로드 경로(analyze → 확정 기록 → prepare_songcue)로 발사한다.

사용: python3 probe_upload_path.py <트리 루트> <출력 json>
  - 트리 루트: 검사할 코드 트리(HEAD 워크트리, 또는 대조군용 옛 트리 추출본)
  - 분석(analyze)은 그 트리의 것을 쓴다. 콘솔 접촉 0건 — 가짜 실행/상태 포트.

두 이름 갈래:
  A default  — section_names 없음 → 확정 기본 이름 S<n> (운영자가 이름 안 줌)
  B chorus   — section_names = pilot_baseline 의 'Chorus 1'/'Chorus 2'… 회차별 라벨
               (#475 가 고친 결함 형상). 구간 수가 안 맞으면 규칙 이름으로 대체하고 표시.
"""
from __future__ import annotations

import base64
import json
import sys
import traceback
from pathlib import Path

ROOT = sys.argv[1]
OUT = sys.argv[2]
sys.path.insert(0, ROOT)

from server.audio.analyze import AnalysisResult, analyze  # noqa: E402
from server.design.profile import BpmResolution  # noqa: E402
from server.llm.types import ToolCall  # noqa: E402
from server.looks.loader import load_library_from_dir  # noqa: E402
from server.orchestrator.tools import build_toolset  # noqa: E402
from server.tests.test_looks_resolver import LXSEQ_RIG  # noqa: E402
from server.tests.test_looks_tool import _RecordingPort  # noqa: E402
from server.tests.test_songcue_confirmed_default import _AnalysisPort  # noqa: E402
from server.tests.test_songcue_tool import _SongCueStatePort, _tree  # noqa: E402
from server.web.question import (  # noqa: E402
    ConfirmedSongAnalysis,
    ConfirmedSongSection,
    SongSectionProposal,
    section_label,
)

MUSIC = Path("/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/src/sample music")
BASELINE = Path(
    "/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/.claude/worktrees/"
    "pilot-labeling/pilot_baseline.json"
)
GROUPS = tuple((i + 1, name) for i, (name, _n) in enumerate(LXSEQ_RIG))
GENRES = ("rock", "edm")

baseline = {s["song"]: s for s in json.loads(BASELINE.read_text())}
library = load_library_from_dir()


def rule_names(proposals):
    counters: dict[str, int] = {}
    names = []
    for p in proposals:
        base = "Chorus" if p.d_level >= 4 else "Verse"
        counters[base] = counters.get(base, 0) + 1
        names.append(f"{base} {counters[base]}")
    return names


def fire(song, record, genre, names):
    port = _RecordingPort()
    registry = build_toolset(
        execution_port=port,
        state_port=_SongCueStatePort(_tree(groups=GROUPS)),
        look_library=library,
        song_analysis=_AnalysisPort(record),
    )
    args = {"song_title": song, "genre": genre, "timecode_number": 7}  # _tree 기본 점유 (1, 3) 회피
    if names is not None:
        args["section_names"] = names
    try:
        execution = registry.dispatch(ToolCall(id="t429", name="prepare_songcue", arguments=args))
    except Exception as error:  # 예외는 데이터로 남긴다
        return {"result": "EXC", "detail": f"{type(error).__name__}: {error}"[:300],
                "trace": traceback.format_exc()[-800:]}
    content = execution.result.content
    try:
        payload = json.loads(content)
    except ValueError:
        payload = None
    stores = [c for c in port.executed if c.startswith("Store Sequence ")]
    if execution.result.is_error:
        return {"result": "ERR", "detail": content[:400], "stores": len(stores)}
    cues = payload.get("report", {}).get("generated_cues", []) if isinstance(payload, dict) else []
    return {"result": "OK", "cues": len(cues), "stores": len(stores)}


rows = []
for path in sorted(MUSIC.iterdir()):
    if path.name.startswith("."):
        continue
    song = path.name
    outcome = analyze(path.read_bytes())
    if not isinstance(outcome, AnalysisResult):
        rows.append({"song": song, "analysis": "REJECT", "reason": getattr(outcome, "reason", repr(outcome))})
        continue
    proposals = tuple(
        SongSectionProposal(start_ms=c.start_ms, end_ms=c.end_ms, d_level=c.d_level)
        for c in outcome.d_candidates
    )
    labels = [section_label(p) for p in proposals]
    record = ConfirmedSongAnalysis(
        source_sha256="0" * 64,
        source_file_name=song,
        confirmed_at="2026-09-23T00:00:00+00:00",
        bpm=BpmResolution(bpm=outcome.bpm, source="measured", reason="t429 probe"),
        sections=tuple(
            ConfirmedSongSection(
                index=i, label=lab, start_ms=p.start_ms, end_ms=p.end_ms,
                d_level=p.d_level, selected=True, label_shared=labels.count(lab) > 1,
            )
            for i, (p, lab) in enumerate(zip(proposals, labels))
        ),
    )
    base = baseline.get(song)
    base_names = [x["baseline_name"] for x in base["sections"]] if base and "sections" in base else []
    if len(base_names) == len(proposals):
        chorus_names, chorus_src = base_names, "pilot_baseline"
    else:
        chorus_names, chorus_src = rule_names(proposals), f"rule(baseline {len(base_names)}≠{len(proposals)})"
    n_chorus = sum(1 for n in chorus_names if n.startswith("Chorus"))
    for genre in GENRES:
        for arm, names in (("A_default", None), ("B_chorus", chorus_names)):
            r = fire(song, record, genre, names)
            rows.append({
                "song": song, "bpm": outcome.bpm, "sections": len(proposals),
                "chorus_labels": n_chorus, "names_src": None if names is None else chorus_src,
                "genre": genre, "arm": arm, **r,
            })

for r in rows:
    print(" | ".join(str(r.get(k, "")) for k in
                     ("song", "analysis", "bpm", "sections", "chorus_labels", "genre", "arm",
                      "result", "cues", "stores", "names_src", "reason", "detail")))
Path(OUT).write_text(json.dumps(rows, ensure_ascii=False, indent=1))
