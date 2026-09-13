"""t383 — the operator's real song, end-to-end, checking d_level this time.

t381 already proved sections/times/BPM cross the bridge. This probe checks
the fourth measured value — d_level — the same way: real DSP analysis, no
monkeypatch, on the operator's actual WAV, through the confirmation card,
into the design-interview path with NO explicit sections/BPM/mood in the
instruction, so the confirmed analysis is the only source.
"""

import base64
import hashlib
import json
import pathlib
import sys
import tempfile
import time
from collections import Counter

sys.path.insert(0, ".")

from server.tests.test_runner_self_correction import ScriptedProvider
from server.tests.test_web_session import TestSongDesignInterviewSession as _Harness
from server.tests.test_web_session import _session

WAV_PATH = "src/걸그룹DinoDino_C_max최고품질.wav"

with open(WAV_PATH, "rb") as f:
    audio_bytes = f.read()
audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
print("sha256:", hashlib.sha256(audio_bytes).hexdigest())
print("byte_length:", len(audio_bytes))

tmp_path = pathlib.Path(tempfile.mkdtemp())

harness = _Harness()
session, _console, _audit, sent, _ = _session(tmp_path, ScriptedProvider([]))
session._registry = harness._registry([])


class _Channel:
    def __init__(self, answers):
        self.answers = list(answers)
        self.asked = []

    def ask(self, request, **_kwargs):
        self.asked.append(request)
        return self.answers.pop(0) if self.answers else "UNANSWERED"


# 1st pop = confirmation-card acknowledgement (accepts all sections + measured BPM)
# next 5 pops = the 5-card director interview
channel = _Channel(
    ["확인", "우주", "우주 색 조합", "Ring In", "우주 컨셉 우선 배치", "템포 맞춤 (BPM 기준)"]
)
session._question_channel = channel

t0 = time.monotonic()
session.upload_song_audio("걸그룹DinoDino_C_max최고품질.wav", "audio/wav", audio_b64)
notify_event = session.analyse_song_audio()
t1 = time.monotonic()
print(f"analyse_song_audio wall time: {t1 - t0:.2f}s")
print("analyse_song_audio notify:", notify_event.get("message", notify_event))

record = session.song_analysis
print("\n--- confirmed analysis (measured by DSP) ---")
measured_d_levels = []
if record is None:
    print("NO CONFIRMED RECORD — analysis produced no confirmable proposals")
else:
    print("bpm:", record.bpm)
    print("num sections:", len(record.sections))
    for s in record.sections:
        print(
            f"  [{s.index}] {s.label} {s.start_ms}-{s.end_ms}ms D{s.d_level} selected={s.selected}"
        )
        if s.selected:
            measured_d_levels.append(s.d_level)

print("\nmeasured d_level histogram:", dict(sorted(Counter(measured_d_levels).items())))

# 2) drive the design interview path with NO explicit sections/bpm/mood in
# the instruction, so the confirmed analysis is the only source.
instruction = "디자인 큐 시트, 시퀀스 110, 프리셋 21번부터, 타임코드 7"
event = session.run_instruction(instruction)
print("\n--- run_instruction result text ---")
print(event.get("message", event) if isinstance(event, dict) else event)

timeline_events = [e for e in sent if e.get("type") == "song_timeline"]
print("\ntimeline events emitted:", len(timeline_events))
if timeline_events:
    payload = timeline_events[0]
    with open("reports/t383/timeline-payload.json", "w", encoding="utf-8") as out:
        json.dump(payload, out, ensure_ascii=False, indent=2)
    print("saved to reports/t383/timeline-payload.json")
    timeline_d_levels = [sec["d_level"] for sec in payload["timeline"]["sections"]]
    print("\ntimeline d_level list:", timeline_d_levels)
    print("timeline d_level histogram:", dict(sorted(Counter(timeline_d_levels).items())))
    print(
        "\ncomparison — measured (confirmed, in section order) vs timeline "
        "(may carry extra bar-split cues per section, and the last section's "
        "d_level is Q3's climax answer, not the measured value):"
    )
    print("measured:", measured_d_levels)
    print("timeline:", timeline_d_levels)
else:
    print("NO TIMELINE EVENT EMITTED")
