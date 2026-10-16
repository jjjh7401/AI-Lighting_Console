"""칸 하나의 왼쪽·오른쪽 따로 색 — UI 시험용 서버 출력 사본의 생성기.

사본: `ui/src/components/beatgrid/cellSplitServerPayload.json`. 곡·리그 고유값이 없는 일반
격자 한 장을, 서버가 격자를 화면에 내보낼 때 거치는 순수 함수 두 자리
(`attach_beat_grid_runtime_extras` 의 칸 읽기 · `attach_beat_grid_ui_values` 의 화면용 값)에
통과시킨 결과다. 세션 상태도 콘솔도 쓰지 않는다 — `derive_beat_grid_fields`(반영 기록·풀 기억이
필요한 파생 필드)는 `split` 과 무관해서 거치지 않는다.

사본이 서버 실출력과 다르면 `test_cell_split_payload_fixture.py` 가 실패하고, 이 명령으로
다시 뜨라고 알려 준다:

    uv run python -m server.tests.cell_split_payload_fixture
"""

from __future__ import annotations

import json
from pathlib import Path

from server.design.beat_grid import attach_beat_grid_runtime_extras
from server.design.beat_grid_ui_values import attach_beat_grid_ui_values
from server.design.rig import resolve_layer_role

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2] / "ui/src/components/beatgrid/cellSplitServerPayload.json"
)
REGEN_COMMAND = "uv run python -m server.tests.cell_split_payload_fixture"

#: M1 판정 표(progress.md)를 읽지 않는다 — 없는 경로를 주면 서버가 9항목을 전부 「미확인」으로 낸다.
#: 저장소의 그 파일이 바뀌어도 사본이 흔들리지 않게 한다.
_NO_PROGRESS_TABLE = Path("/nonexistent/cell-split-fixture-progress.md")

SPLIT_BAR = 7
NEXT_BAR = 14

#: 시험 자료다 — 앱 상수가 아니다. 줄 둘: 나뉜 칸 하나가 낀 줄과 보통 줄.
#: 색 이름은 표준 팔레트 이름이다.
_TRACKS: tuple[tuple[int, str, tuple[dict[str, object], ...]], ...] = (
    (
        21,
        "SIDE-ALL",
        (
            {"bar": 0, "label": "앞박 1회"},
            {
                "bar": SPLIT_BAR,
                "label": "왼쪽 오른쪽 따로",
                "brightness": {"mode": "value", "value_percent": 70, "preset_no": None},
                "split": {"left": {"color": "Red"}, "right": {"color": "Blue"}},
            },
            {"bar": NEXT_BAR, "label": "다시 합침"},
        ),
    ),
    (22, "FRONT-ALL", ({"bar": 0, "label": "앞빛 켬"},)),
)


def _raw_grid() -> dict[str, object]:
    """저장소에 있을 법한 격자 — 칸은 일부 필드만 적은 선언이다(서버가 읽을 때 채운다)."""
    return {
        "song_title": "Cell Split Fixture",
        "bar_range": {"start": 0, "end": 25},
        "tracks": [
            {
                "group_no": group_no,
                "group_no_confirmed": True,
                "group_name": name,
                "layer_role": resolve_layer_role(name),
                "cues": [dict(cue) for cue in cues],
            }
            for group_no, name, cues in _TRACKS
        ],
        "scene_memos": [],
        "probe_results": {},
        "source": "custom",
        "note": None,
    }


def build_payload() -> dict[str, object]:
    """사본과 같은 입력으로 지금 서버가 내는 타임라인 페이로드(JSON 으로 직렬화했다 읽은 값).

    브라우저가 받는 모양으로 맞추려고 JSON 을 한 번 왕복한다(정수 키 → 문자열 키 등)."""
    timeline: dict[str, object] = {"song_title": "Cell Split Fixture", "beat_grid": _raw_grid()}
    timeline = attach_beat_grid_runtime_extras(timeline, progress_md_path=_NO_PROGRESS_TABLE)
    timeline = attach_beat_grid_ui_values(timeline)
    return json.loads(json.dumps(timeline, ensure_ascii=False))


def write_fixture(path: Path = FIXTURE_PATH) -> None:
    """사본을 쓴다(`ensure_ascii=False, indent=1`, 끝 줄바꿈 없음 — 런북 사본과 같은 직렬화)."""
    with path.open("w", encoding="utf-8") as fh:
        json.dump(build_payload(), fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    write_fixture()
    print(f"wrote {FIXTURE_PATH}")
