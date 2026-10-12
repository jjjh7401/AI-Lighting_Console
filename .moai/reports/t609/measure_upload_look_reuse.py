"""카드 t609 — 업로드 길(``prepare_songcue``)의 곡 사이 룩 재사용 실측(콘솔 접촉 0).

t491 측정(`.moai/reports/t491/measure_look_reuse.py`)의 업로드 길 짝이다. 같은 t499
8곡, 같은 룩 정의(``(position.stored, color.palette)``, 구간 큐만), 같은 「이웃 쌍」
셈법을 쓴다. 다른 점은 입구 하나 — 대화 길 ``run_instruction`` 이 아니라 모델이
부르는 도구 ``prepare_songcue`` 를 ``build_toolset`` 레지스트리로 직접 부른다.

인터뷰 답은 t491 과 같아야 비교가 된다. 업로드 길은 세션의 **가장 최근에 끝난**
연출 인터뷰 기록(``interview_records``)을 읽으므로, t491 하네스로 대화 길 한 곡을
돌려 그 세션의 기록을 그대로 꺼내 8곡 모두에 넘긴다(같은 답).

콘솔은 t480 업로드 시험의 가짜(``_SongCueStatePort(_tree())`` + ``_RecordingPort``)다.
포지션 축을 켜려고 ``preset_start=POSITION_START``(가짜 콘솔의 기본 10라벨 시작)를 준다.

실행 세 가지
- ``none``   : 기억 창을 안 넘김 — 오늘 main 과 같은 업로드 길(구현 전).
- ``shared`` : 8곡이 한 기억을 함께 씀 — 한 쇼(구현 후).
- ``fresh``  : 곡마다 새 기억(대조) — 효과가 기억에서 오는지 가른다.

실행: uv run python .moai/reports/t609/measure_upload_look_reuse.py
출력: 표준출력 + .moai/reports/t609/upload_look_reuse.json
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
T491 = HERE.parent / "t491"
T499 = HERE.parent / "t499"
sys.path.insert(0, str(T491))
sys.path.insert(0, str(HERE.parent / "t501"))

import measure_ac001_8songs as m  # noqa: E402
import measure_look_reuse as t491  # noqa: E402

import server.orchestrator.tools as tools  # noqa: E402
from server.llm.types import ToolCall  # noqa: E402
from server.tests.test_chorus_color_two_paths_t441 import _RecordsPort  # noqa: E402
from server.tests.test_looks_tool import _RecordingPort  # noqa: E402
from server.tests.test_songcue_tool import _SongCueStatePort, _tree  # noqa: E402
from server.tests.upload_console_fixture import POSITION_START  # noqa: E402


class _AnalysisPort:
    def __init__(self):
        self.current = None


class _Memory:
    def __init__(self):
        self.history: list = []


_FINAL: list = []
_original_compose = tools.compose_song_cue_bundle


def _recording_compose(plan):
    result = _original_compose(plan)
    _FINAL.append(result)
    return result


def _interview_records():
    """t491 하네스로 대화 길 한 곡을 돌려 그 세션의 인터뷰 기록을 꺼낸다."""
    t491._install_capture()
    session, questions = t491._new_session()
    song, path = _songs()[0]
    t491._run_song(session, questions, song, path, 0, None)
    records = session._song_interview_records
    assert records, "대화 길 인터뷰 기록이 비었다 — 같은 답을 넘길 수 없다"
    return tuple(records)


def _songs():
    paths = sorted(
        p for p in (T499 / "runs").glob("*/analysis.json") if p.parent.name != "Rain_first"
    )
    assert len(paths) == 8, [p.parent.name for p in paths]
    return [(p.parent.name, p) for p in paths]


def _run(mode: str, records) -> list[dict]:
    analysis = _AnalysisPort()
    shared = _Memory()
    rows = []
    registry = None
    for slot, (song, path) in enumerate(_songs()):
        memory = {"none": None, "shared": shared, "fresh": _Memory()}[mode]
        if registry is None or mode != "shared":
            registry = tools.build_toolset(
                execution_port=_RecordingPort(),
                state_port=_SongCueStatePort(_tree()),
                song_analysis=analysis,
                interview_records=_RecordsPort(records),
                song_look_memory=memory,
            )
        record, _resolution = m._confirmed_analysis_from_t499(path, song)
        analysis.current = record
        before = len(_FINAL)
        execution = registry.dispatch(
            ToolCall(
                id=f"t609-{slot}",
                name="prepare_songcue",
                arguments={
                    "song_title": song,
                    "genre": "pop",
                    "timecode_number": 7,
                    "preset_start": POSITION_START,
                },
            )
        )
        payload = json.loads(execution.result.content)
        final = _FINAL[-1] if len(_FINAL) > before else None
        cues = [
            c for c in (final.bundle.cues if final and final.bundle else ()) if c.kind == "section"
        ]
        rows.append(
            {
                "song": song,
                "executed": payload.get("executed"),
                "is_error": execution.result.is_error,
                "look_offset": payload.get("look_offset"),
                "memory_len": None if memory is None else len(memory.history),
                "cues": [
                    {
                        "no": c.cue_number,
                        "name": c.cue_name,
                        "position": c.position.stored,
                        "palette": list(c.color.palette),
                        "fx": list(c.fx.permitted),
                    }
                    for c in cues
                ],
            }
        )
    empty = [r["song"] for r in rows if not r["cues"]]
    if empty:
        raise SystemExit(f"{mode}: 구간 큐 0개 — {empty} · {[r['is_error'] for r in rows]}")
    return rows


def main():
    records = _interview_records()
    tools.compose_song_cue_bundle = _recording_compose
    report: dict = {"songs": [s for s, _ in _songs()], "runs": {}, "analysis": {}}
    for mode in ("none", "shared", "fresh"):
        report["runs"][mode] = _run(mode, records)
    for mode, rows in report["runs"].items():
        adjacent = [t491._pair_stats(a, b) for a, b in itertools.pairwise(rows)]
        all_pairs = [t491._pair_stats(a, b) for a, b in itertools.combinations(rows, 2)]
        distinct = {t491._look(c) for r in rows for c in r["cues"]}
        report["analysis"][mode] = {
            "adjacent": {"summary": t491._summary(rows, adjacent), "pairs": adjacent},
            "all_pairs": {"summary": t491._summary(rows, all_pairs)},
            "distinct_looks": len(distinct),
        }
    (HERE / "upload_look_reuse.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), "utf-8"
    )
    for mode, value in report["analysis"].items():
        print("==", mode, "distinct", value["distinct_looks"])
        print("  adjacent ", value["adjacent"]["summary"])
        print("  all pairs", value["all_pairs"]["summary"])
    for mode, rows in report["runs"].items():
        print(
            "--",
            mode,
            [
                (
                    r["song"],
                    r["executed"],
                    r["look_offset"],
                    r["memory_len"],
                    len(r["cues"]),
                    t491._look(r["cues"][0]),
                )
                for r in rows
            ],
        )


if __name__ == "__main__":
    main()
