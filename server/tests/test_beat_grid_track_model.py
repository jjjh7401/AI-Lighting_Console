"""줄 수가 무대에 따라 달라도 반영이 끝까지 간다(카드 WT-track-model, 2026-10-18).

새 곡 전체 점검(FRESH TEST 1018): #817 로 콘솔 그룹에서 KEY 줄이 붙어 9줄이 되자, 타임코드
트랙 상한 8 을 넘어 그 타임코드의 트랙 **전부**가 막혔다 — 「콘솔에 반영할 내용이 없습니다」.

- 상한 8 은 콘솔 제약이 아니라 「8개까지 재 봤다」였다. 2026-10-18 실기에서 16개를 붙여
  되읽었다(childCount 17, TARGET 16개 순서 일치) — ``measured_console.yaml`` 값이 16 이 됐다.
- 잰 수를 넘는 줄이 생겨도 **넘친 줄만** 이유와 함께 막고 나머지는 보낸다.
"""

from __future__ import annotations

from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid
from server.design.beat_grid_emit import MEASURED_MAX_TIMECODE_TRACKS, emit_beat_grid_write_bundle
from server.design.beat_grid_probes import read_m1_probe_results_from_path
from server.tests.test_beat_grid_emit_t549 import _TIMING, default_progress_md_path


def _emit(tracks):
    return emit_beat_grid_write_bundle(
        tracks,
        timing=_TIMING,
        sequence_numbers={t["group_name"]: 300 + i for i, t in enumerate(tracks)},
        timecode_numbers={t["group_name"]: 30 for t in tracks},
        dimmer_attributes={t["group_name"]: ("Dimmer",) for t in tracks},
        probe_results=read_m1_probe_results_from_path(default_progress_md_path()),
    )


def _rows(count: int) -> list[dict]:
    """LOVE ATTACK 기본 격자 줄을 이름만 바꿔 ``count`` 줄로 늘린다(칸 내용은 실제 기본값)."""
    base = list(default_beat_grid(LOVE_ATTACK_TITLE)["tracks"])
    return [dict(base[i % len(base)], group_name=f"ROW-{i + 1}") for i in range(count)]


def _cap_blocked(result) -> list[str]:
    return [
        t.group_name
        for t in result.tracks
        if t.blocked_reason is not None and str(MEASURED_MAX_TIMECODE_TRACKS) in t.blocked_reason
    ]


def _sent(result) -> list[str]:
    return [t.group_name for t in result.tracks if t.assign_timecode_commands]


#: 기본 격자를 복사한 줄 중 STROBE 줄(8번째)은 칸 내용상 원래 보낼 것이 없다(상한과 무관, 예전부터).
_NOTHING_TO_SEND = {"ROW-8"}


def test_nine_rows_reach_the_console() -> None:
    result = _emit(_rows(9))
    assert result.commands, "줄 9개인 격자의 반영 명령이 0개다"
    assert _cap_blocked(result) == []
    assert set(_sent(result)) == {f"ROW-{i}" for i in range(1, 10)} - _NOTHING_TO_SEND


def test_eleven_rows_reach_the_console() -> None:
    # 이 무대에서 처음 쓰는 곡이 콘솔 그룹으로 만드는 줄 수(2026-10-18 실측 계산값).
    result = _emit(_rows(11))
    assert result.commands
    assert _cap_blocked(result) == []
    assert set(_sent(result)) == {f"ROW-{i}" for i in range(1, 12)} - _NOTHING_TO_SEND


def test_rows_beyond_the_measured_cap_are_blocked_alone_and_the_rest_are_sent() -> None:
    rows = _rows(MEASURED_MAX_TIMECODE_TRACKS + 2)
    result = _emit(rows)
    overflow = [r["group_name"] for r in rows[MEASURED_MAX_TIMECODE_TRACKS:]]
    assert _cap_blocked(result) == overflow
    assert not set(_sent(result)) & set(overflow)
    assert len(_sent(result)) >= MEASURED_MAX_TIMECODE_TRACKS - len(_NOTHING_TO_SEND) - 1
    assert result.commands
