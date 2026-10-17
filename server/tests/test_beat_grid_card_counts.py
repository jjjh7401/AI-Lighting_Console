"""SPEC-LDRHYTHM-001 전체 실행 C-11 — 승인 카드의 큐 수·칸 수가 무엇으로 이루어졌는지 적는다.

실콘솔 카드에 「큐 90개」, 승인 목록 100칸, 격자 86칸이 설명 없이 나왔다. 차이는 어둠 속 미리
이동(MIB) 큐, 보낼 내용 없는 칸, 타임코드 준비·트랙 연결·재생 이벤트 칸이다. 숫자는 전부 실제로
보내는 결과에서 센다. 콘솔 접촉 0건.
"""

from __future__ import annotations

from server.design.beat_grid_emit import BeatGridEmitResult, CueEmitResult, TrackEmitResult
from server.web.session import _beat_grid_cell_breakdown, _beat_grid_target_summary


def _cue(bar: int, number: int | None, *, premove: bool = False, held: bool = False):
    return CueEmitResult(
        bar=bar,
        commands=() if number is None else (f"Store Sequence 62 Cue {number}",),
        blocked_reason="M1 보류" if held else None,
        cue_number=number,
        premove=premove,
    )


def _result() -> BeatGridEmitResult:
    track = TrackEmitResult(
        group_name="FOH",
        group_no=3,
        sequence_number=62,
        timecode_number=5,
        cues=(
            _cue(1, 1),
            _cue(2, 2, premove=True),  # 어둠 속 미리 이동 큐
            _cue(3, 3),
            _cue(4, None, held=True),  # 보류 칸
            _cue(5, None),  # 보낼 내용 없는 칸
        ),
        assign_timecode_commands=("Assign Sequence 62 At Timecode 5.1.1",),
        blocked_reason=None,
    )
    return BeatGridEmitResult(
        tracks=(track,),
        blocked_reason=None,
        timecode_setup_commands=("Store Timecode 5",),
        timecode_event_commands=("Store Type 'CmdSubTrack' Timecode 5.1.1.1",),
    )


def test_summary_explains_grid_cells_versus_cues() -> None:
    text = _beat_grid_target_summary(_result(), 5, {"FOH": 62}, grid_cell_count=4)
    assert text.endswith(
        "큐 3개(격자 칸 4개 중 보내는 칸 2개 + 어둠 속 미리 이동 큐 1개 · 보류 칸 1개 · "
        "보낼 내용 없는 칸 1개)"
    )


def test_breakdown_adds_up_to_the_approval_cell_count() -> None:
    result = _result()
    cells = [
        ("Store Preset 2.10",),
        *(cue.commands for cue in result.tracks[0].cues if cue.commands),
        result.timecode_setup_commands,
        result.tracks[0].assign_timecode_commands,
        result.timecode_event_commands,
    ]
    text = _beat_grid_cell_breakdown(cells, creation_count=1, cue_count=3, result=result)
    assert text == (
        "승인 묶음 7칸 = 큐 3 + 새 프리셋 만들기 1 + 타임코드 준비 1 + 트랙 연결 1 + 재생 이벤트 1"
    )
