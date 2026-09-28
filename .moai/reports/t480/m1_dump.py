"""t480 M1 — 대화 길 명령 생성기의 출력을 시험 실행 중에 전부 받아 적는다.

`ChatSession._reviewed_song_commands` 를 감싸, 시험이 부를 때마다 결과 명령을
한 줄씩 파일에 쓴다. 옮기기 전·후에 같은 시험 목록으로 돌려 `cmp` 한다.

실행(저장소 루트): `uv run python .moai/reports/t480/m1_dump.py <출력파일>`
"""

import sys
from pathlib import Path

import pytest

from server.web import session as session_module

TESTS = [
    "server/tests/test_song_cue_color_emission.py",
    "server/tests/test_web_session.py",
    "server/tests/test_song_cue_w_channel_t430.py",
    "server/tests/test_song_cue_white_preset_t453.py",
    "server/tests/test_song_cue_arc_t462.py",
    "server/tests/test_writegate_song_finalize.py",
    "server/tests/test_write_dispatch_census.py",
    "server/tests/test_preset_label_lookup_t232.py",
]

out_path = Path(sys.argv[1])
records: list[str] = []
original = session_module.ChatSession._reviewed_song_commands


def _recording(self, *args, **kwargs):
    result = original(self, *args, **kwargs)
    records.append(f"# call {len(records)} ncmd={len(result)}")
    records.extend(result)
    return result


session_module.ChatSession._reviewed_song_commands = _recording
code = pytest.main(["-q", "-p", "no:cacheprovider", "-p", "no:randomly", *TESTS])
out_path.write_text("\n".join(records) + "\n")
print(f"pytest exit={code} calls_recorded={sum(1 for r in records if r.startswith('# call'))}")
sys.exit(int(code))
