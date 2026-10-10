"""정답지 파서 — 지도 보고서 부록 A(82마디) + acceptance.md AC-007(7개 사건).

두 표 모두 정규식으로 원문 마크다운에서 직접 파싱한다(하드코딩 사본을 두지 않는다
— 정답지가 바뀌면 이 파서가 다시 읽어 저절로 반영된다).

REQ-LDBARMAP-004/005/007/008/009 근거.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_PATH = REPO_ROOT / "reports" / "loveattack-music-map-20261006.md"
DEFAULT_ACCEPTANCE_PATH = REPO_ROOT / ".moai/specs/SPEC-LDBARMAP-001/acceptance.md"

# 지도 보고서 §A 상수(acceptance.md §A와 동일, 재사용)
TARGET_BPM = 112.35
BEAT_INTERVAL_SEC = 60.0 / TARGET_BPM  # 0.534...
BAR_INTERVAL_SEC = 4.0 * BEAT_INTERVAL_SEC  # 2.136...
DOWNBEAT_TOLERANCE_SEC = 0.060  # ±60ms
EVENT_TOLERANCE_BARS = 1  # ±1마디


@dataclass(frozen=True)
class TruthEvent:
    """acceptance.md AC-007 7개 사건 중 하나."""

    event_id: int
    name: str
    event_type: str  # "build" | "kick_entry" | "kick_absence"
    start_bar: int
    end_bar: int

    @property
    def window(self) -> tuple[int, int]:
        """±1마디 허용오차 창 — (start_bar - 1, start_bar + 1)."""
        return (self.start_bar - EVENT_TOLERANCE_BARS, self.start_bar + EVENT_TOLERANCE_BARS)


def parse_downbeats(report_path: Path = DEFAULT_REPORT_PATH) -> list[float]:
    """부록 A(82마디 표)에서 마디 1박(다운비트) 시각(초)을 1마디부터 순서대로 뽑는다.

    표 형식: `| <마디> | <다운비트초> | <구간> | ... |`
    """
    text = report_path.read_text(encoding="utf-8")
    # 부록 A 절만 범위를 좁힌다 — §3/§4의 다른 표에 섞인 숫자 행을 피한다.
    marker = "## 부록 A."
    idx = text.find(marker)
    if idx < 0:
        raise ValueError(f"'{marker}' 절을 찾지 못했습니다: {report_path}")
    section = text[idx:]

    rows: list[tuple[int, float]] = []
    row_re = re.compile(r"^\|\s*(\d+)\s*\|\s*([\d.]+)\s*\|", re.MULTILINE)
    for match in row_re.finditer(section):
        bar = int(match.group(1))
        downbeat_s = float(match.group(2))
        rows.append((bar, downbeat_s))

    if not rows:
        raise ValueError(f"부록 A 표에서 행을 하나도 못 찾았습니다: {report_path}")

    rows.sort(key=lambda pair: pair[0])
    # 마디 번호가 1..N 연속인지 확인 — 정답지가 빠진 줄 없이 파싱됐는지 검산.
    expected = list(range(1, len(rows) + 1))
    actual_bars = [bar for bar, _ in rows]
    if actual_bars != expected:
        raise ValueError(
            f"부록 A 마디 번호가 1..{len(rows)} 연속이 아닙니다 — "
            f"파싱 누락 의심: {actual_bars[:10]}..."
        )
    return [downbeat_s for _, downbeat_s in rows]


_EVENT_TYPE_KEYWORDS = (
    ("빌드업", "build"),
    ("큰 히트", "kick_entry"),
    ("킥 멈춤", "kick_absence"),
)


def _classify_event_type(name: str) -> str:
    for keyword, event_type in _EVENT_TYPE_KEYWORDS:
        if keyword in name:
            return event_type
    raise ValueError(f"사건 이름을 분류하지 못했습니다(알려진 키워드 없음): {name!r}")


def parse_events(acceptance_path: Path = DEFAULT_ACCEPTANCE_PATH) -> list[TruthEvent]:
    """acceptance.md AC-LDBARMAP-007의 7개 사건 표를 파싱한다.

    표 형식: `| # | 사건 | 구간(마디) | 판정 기준(온셋 ±1마디) |`
    """
    text = acceptance_path.read_text(encoding="utf-8")
    marker = "### AC-LDBARMAP-007"
    idx = text.find(marker)
    if idx < 0:
        raise ValueError(f"'{marker}' 절을 찾지 못했습니다: {acceptance_path}")
    # 다음 AC 제목(### AC-LDBARMAP-008) 전까지로 범위를 좁힌다.
    next_idx = text.find("### AC-LDBARMAP-008", idx)
    section = text[idx:next_idx] if next_idx > 0 else text[idx:]

    row_re = re.compile(
        r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*(\d+)(?:~(\d+))?\s*\|",
        re.MULTILINE,
    )
    events: list[TruthEvent] = []
    for match in row_re.finditer(section):
        event_id = int(match.group(1))
        name = match.group(2).strip()
        start_bar = int(match.group(3))
        end_bar = int(match.group(4)) if match.group(4) else start_bar
        event_type = _classify_event_type(name)
        events.append(TruthEvent(event_id, name, event_type, start_bar, end_bar))

    if len(events) != 7:
        raise ValueError(
            f"AC-007 사건 표에서 7개가 아니라 {len(events)}개를 파싱했습니다 — "
            f"정답지 표 형식이 바뀌었는지 확인하세요: {events}"
        )
    return events


def shift_downbeats(downbeats: list[float], shift_sec: float) -> list[float]:
    """정답지 전체를 shift_sec 만큼 밀어낸 격자를 만든다(음성 대조군용, REQ-LDBARMAP-005).

    프로그램적 변형 — 손으로 날조하지 않는다(재현 가능성, plan.md §D).
    """
    return [t + shift_sec for t in downbeats]
