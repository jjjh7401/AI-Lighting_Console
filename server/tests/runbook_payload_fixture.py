"""카드 t496 — 런북 UI 시험·미리보기용 서버 출력 사본의 생성기.

사본: `ui/src/components/runbookServerPayload.json`. t458 이 처음 만들고 t493 이 다시 뜬
스크립트(`.moai/reports/t493/measure_payload.py`)와 같은 곡·같은 서버 실경로
(`_song_timeline_payload`)다. 콘솔 접촉 0.

사본이 서버 실출력과 구조(키 집합·목록 길이)가 다르면
`test_runbook_payload_fixture_t496.py` 가 실패하고, 이 명령으로 다시 뜨라고 알려 준다:

    uv run python -m server.tests.runbook_payload_fixture
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from server.design.song_cue_composer import compose_song_cue_bundle
from server.design.song_plan import PaletteDecision
from server.tests.test_song_timeline_concept_report_wiring import _plan, _section
from server.web.session import _song_timeline_payload

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "ui/src/components/runbookServerPayload.json"
REGEN_COMMAND = "uv run python -m server.tests.runbook_payload_fixture"

#: t454 와 같은 8구간·120 BPM 곡. 구간마다 다른 색을 줘서 HEX 해석(t456)·미해석
#: (흰색·gold·핑크)이 함께 보이게 한다(t458). 시험 자료다 — 앱 상수가 아니다.
_SECTIONS: tuple[tuple[str, int, tuple[str, ...]], ...] = (
    ("Intro", 0, ("Blue",)),
    ("Verse 1", 15000, ("블루", "Amber")),
    ("Chorus 1", 40000, ("Warm White",)),
    ("Verse 2", 60000, ("흰색",)),
    ("Chorus 2", 85000, ("gold", "Red")),
    ("Bridge", 105000, ("Lavender",)),
    ("Chorus 3", 125000, ("Cyan", "Magenta")),
    ("Outro", 150000, ("핑크",)),
)


def build_payload() -> dict[str, object]:
    """사본과 같은 입력으로 지금 서버가 내는 타임라인 페이로드."""
    sections = tuple(
        replace(
            _section(i + 1, label, start_ms),
            palette=PaletteDecision(colors=colors, source="director"),
        )
        for i, (label, start_ms, colors) in enumerate(_SECTIONS)
    )
    plan = _plan(bpm=120.0, sections=sections)
    return _song_timeline_payload(
        plan, compose_song_cue_bundle(plan), lifecycle="pending_approval", sequence_no=1
    )


def write_fixture(path: Path = FIXTURE_PATH) -> None:
    """t493 과 같은 직렬화(`ensure_ascii=False, indent=1`, 끝 줄바꿈 없음)로 쓴다."""
    with path.open("w", encoding="utf-8") as fh:
        json.dump(build_payload(), fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    write_fixture()
    print(f"wrote {FIXTURE_PATH}")
