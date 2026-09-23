"""t452 재현 — 4초 간격 5구간 곡(t441 _RAW_SECTIONS_B)을 운영 툴셋으로 돌려
concept_report 를 출력한다. 콘솔 쓰기 0 (가짜 포트)."""

import json
import sys

sys.path.insert(0, ".")

from server.looks.loader import load_library_from_dir  # noqa: E402
from server.orchestrator.tools import build_toolset  # noqa: E402
from server.tests.test_chorus_color_two_paths_t441 import (  # noqa: E402
    TestToolsetWiring,
    _records,
    _RecordsPort,
)
from server.tests.test_songcue_bpm_production_wiring import _record  # noqa: E402
from server.tests.test_songcue_confirmed_default import _AnalysisPort  # noqa: E402
from server.tests.test_songcue_tool import (  # noqa: E402
    _RecordingPort,
    _SongCueStatePort,
    _tree,
)

for label, port in (
    ("records_absent", None),
    ("records_present", _RecordsPort(_records("modulate"))),
):
    registry = build_toolset(
        execution_port=_RecordingPort(),
        state_port=_SongCueStatePort(_tree()),
        look_library=load_library_from_dir(),
        song_analysis=_AnalysisPort(_record(bpm=120.0)),
        **({} if port is None else {"interview_records": port}),
    )
    execution, payload = TestToolsetWiring()._dispatch(registry)
    rep = payload.get("concept_report")
    print(label, "is_error=", execution.result.is_error)
    print("  concept_report=", json.dumps(rep, ensure_ascii=False)[:500])
