"""t480 M3 — 업로드 길 실제 입구(``prepare_songcue``)가 내는 콘솔 명령 덤프.

같은 가짜 콘솔(``server/tests/upload_console_fixture.py``)·같은 입력으로 전환 전·후에
돌려 명령을 줄 단위로 비교한다. 콘솔 쓰기 0 — 실행 포트는 기록만 한다.

실행(저장소 루트): `uv run python .moai/reports/t480/m3_upload_dump.py > <출력파일>`
"""

import hashlib
import json

from server.llm.types import ToolCall
from server.orchestrator.tools import build_toolset
from server.tests.song_section_fixtures import ICE_CREAM_SECTIONS as _ICE_CREAM_SECTIONS
from server.tests.song_section_fixtures import RAIN_SECTIONS as _RAIN_SECTIONS
from server.tests.test_chorus_color_two_paths_t441 import _records, _RecordsPort
from server.tests.test_songcue_tool import _RecordingPort
from server.tests.upload_console_fixture import POSITION_START, UploadConsole

total = hashlib.sha256()
for song, raw in (("Ice cream", _ICE_CREAM_SECTIONS), ("Rain", _RAIN_SECTIONS)):
    for genre in ("rock", "edm"):
        for interview in (False, True):
            for preset_start in (None, POSITION_START):
                registry = build_toolset(
                    execution_port=_RecordingPort(),
                    state_port=UploadConsole(),
                    **({"interview_records": _RecordsPort(_records())} if interview else {}),
                )
                arguments: dict[str, object] = {
                    "song_title": song,
                    "genre": genre,
                    "timecode_number": 7,
                    "sections": [{"name": name, "start": start} for name, start in raw],
                }
                if preset_start is not None:
                    arguments["preset_start"] = preset_start
                execution = registry.dispatch(
                    ToolCall(id="t480-dump", name="prepare_songcue", arguments=arguments)
                )
                try:
                    payload = json.loads(execution.result.content)
                except json.JSONDecodeError:
                    payload = {"raw": execution.result.content}
                commands = [
                    entry["command"] if isinstance(entry, dict) else str(entry)
                    for entry in payload.get("commands", [])
                ]
                body = "\n".join(commands)
                total.update(body.encode())
                digest = hashlib.sha256(body.encode()).hexdigest()[:16]
                head = (
                    f"## {song} genre={genre} interview={interview} preset_start={preset_start}"
                    f" error={execution.result.is_error} lines={len(commands)} sha={digest}"
                )
                print(head)
                if execution.result.is_error:
                    print("   ERROR", str(payload.get("error", payload))[:300])
                summary = str(payload.get("summary_ko", "")).splitlines()
                if summary:
                    print("   summary:", summary[0][:300])
                print(body)
print(f"TOTAL sha256={total.hexdigest()}")
