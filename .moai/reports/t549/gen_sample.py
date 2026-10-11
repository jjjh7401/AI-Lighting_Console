"""t549 — LOVE ATTACK 샘플 승인 배치 생성(시험 입력, 콘솔 번호 아님)."""

from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid
from server.design.beat_grid_emit import SongTiming, emit_beat_grid_write_bundle
from server.design.beat_grid_probes import (
    default_progress_md_path,
    read_m1_probe_results_from_path,
)
from server.design.send_approval import build_write_approval_batch

grid = default_beat_grid(LOVE_ATTACK_TITLE)
tracks = grid["tracks"]
probe_results = read_m1_probe_results_from_path(default_progress_md_path())
print("probe_results (live, from progress.md):", probe_results)

timing = SongTiming(bpm=120.0, beats_per_bar=4, downbeat_bar1_seconds=1.5)
# 시험 입력 - 실제 콘솔 번호가 아니다. 8개 트랙을 타임코드 둘로 나눈다
# (MEASURED_MAX_TIMECODE_TRACKS=6을 넘지 않도록).
sequence_numbers = {t["group_name"]: 300 + i for i, t in enumerate(tracks)}
timecode_numbers = {t["group_name"]: (30 if i < 4 else 31) for i, t in enumerate(tracks)}
dimmer_attributes = {t["group_name"]: ("Dimmer",) for t in tracks}

result = emit_beat_grid_write_bundle(
    tracks,
    timing=timing,
    sequence_numbers=sequence_numbers,
    timecode_numbers=timecode_numbers,
    dimmer_attributes=dimmer_attributes,
    probe_results=probe_results,
)

print()
print("=== blocked cells ===")
for group_name, bar, reason in result.blocked_cells:
    print(f"{group_name} bar={bar}: {reason}")

print()
print("=== allowed cells with content ===")
for track in result.tracks:
    for cue in track.cues:
        if cue.blocked_reason is None and cue.commands:
            print(f"{track.group_name} bar={cue.bar}: {len(cue.commands)} lines")

print()
print("=== track-level blocked ===")
for track in result.tracks:
    if track.blocked_reason is not None:
        print(f"{track.group_name}: {track.blocked_reason}")

cells = []
for track in result.tracks:
    if track.store_sequence_commands:
        cells.append(track.store_sequence_commands)
    for cue in track.cues:
        if cue.commands:
            cells.append(cue.commands)
    if track.assign_timecode_commands:
        cells.append(track.assign_timecode_commands)
if result.timecode_setup_commands:
    cells.append(result.timecode_setup_commands)

batch = build_write_approval_batch(cells)
print()
print("=== approval batch ===")
print("cell_count:", batch.cell_count)
print("command_count:", len(batch.commands))
print("sha256:", batch.sha256)

with open(".moai/reports/t549/sample-approval-batch.txt", "w") as f:
    for line in batch.commands:
        f.write(line + "\n")
print("written: .moai/reports/t549/sample-approval-batch.txt")
