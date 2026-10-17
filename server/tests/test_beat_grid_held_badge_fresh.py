"""SPEC-LDRHYTHM-001 전체 실행 C-10·J-05 — 보류 배지가 반영과 같은 M1 판정을 읽는다.

배지(``m1_held_cell_count``)는 격자에 저장된 낡은 ``probe_results`` 로 「칸 17개 보류」를 띄웠는데,
반영은 progress.md 를 그 자리에서 다시 읽어 아무 칸도 막지 않았다. 배지도 progress.md 를 읽는다.

콘솔 접촉 0건.
"""

from __future__ import annotations

from server.web.session import derive_beat_grid_fields


def _progress_table(results: dict[int, str]) -> str:
    return "\n".join(
        f"| {chr(0x2460 + item - 1)} 항목 | {status} | 본 것 | 근거 |"
        for item, status in results.items()
    )


def _timeline(stored_probes: dict[int, str]) -> dict:
    return {
        "song_title": "Test Song",
        "beat_grid": {
            "tracks": [
                {
                    "group_name": "BACK",
                    "group_no": 7,
                    "group_no_confirmed": True,
                    # 효과 프리셋 칸 — M1 ④ 에 기댄다.
                    "cues": [{"bar": 1, "effect_preset_no": "3.1"}],
                }
            ],
            "probe_results": stored_probes,
        },
    }


def _held_count(tmp_path, monkeypatch, *, stored: dict[int, str], progress: dict[int, str]) -> int:
    path = tmp_path / "progress.md"
    path.write_text(_progress_table(progress), encoding="utf-8")
    monkeypatch.setattr("server.web.session.default_progress_md_path", lambda: path)
    derived = derive_beat_grid_fields(
        _timeline(stored), snapshots={}, pool_slots={}, empty_marks={}
    )
    return derived["beat_grid"]["m1_held_cell_count"]


_ALL = range(1, 10)


def test_stale_unconfirmed_grid_does_not_hold_cells_progress_md_passes(tmp_path, monkeypatch):
    count = _held_count(
        tmp_path,
        monkeypatch,
        stored={item: "미확인" for item in _ALL},
        progress={item: "통과" for item in _ALL},
    )
    assert count == 0


def test_stale_passing_grid_still_holds_when_progress_md_does_not_pass(tmp_path, monkeypatch):
    count = _held_count(
        tmp_path,
        monkeypatch,
        stored={item: "통과" for item in _ALL},
        progress={**{item: "통과" for item in _ALL}, 4: "미확인"},
    )
    assert count == 1
