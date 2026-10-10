"""정답지 파서 — 지도 보고서 부록 A(82마디) + acceptance.md AC-007(7개 사건) +
부록 A "순간" 칸의 정밀도 증거 표시(카드 t535).

세 표 모두 정규식으로 원문 마크다운에서 직접 파싱한다(하드코딩 사본을 두지 않는다
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
    event_type: str  # "build" | "kick_entry" | "break" (REQ-LDBARMAP-008 어휘)
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


@dataclass(frozen=True)
class TruthBarFeature:
    """부록 A 한 마디의 음량·저역·보컬 대역 비율 — M3 분류기의 "실제 오디오에서 잰
    값과 동급" 입력(REQ-LDBARMAP-008/009 근거). 오디오가 아니라 지도 보고서가
    이미 측정해 커밋한 숫자다(하드코딩 사본이 아니라 이 파서가 원문에서 직접
    뽑는다 — ``parse_downbeats`` 와 같은 설계).
    """

    bar: int
    volume_norm: float  # 음량(중앙값=1)
    low_band_norm: float  # 저역(중앙값=1)
    vocal_band_ratio: float  # 보컬 대역 비율(참고, 0~1)


def parse_bar_features(report_path: Path = DEFAULT_REPORT_PATH) -> list[TruthBarFeature]:
    """부록 A(82마디 표)에서 음량·저역·보컬 대역 비율 칸을 1마디부터 순서대로 뽑는다.

    표 칸 순서(``## 부록 A.`` 머리글 직후 표): 마디 | 다운비트(초) | 구간(앱) |
    킥 후보 칸 | 스네어·클랩 후보 칸 | 음량(중앙값=1) | 저역(중앙값=1) |
    보컬 대역 비율(참고) | 순간. 킥/스네어 후보 칸은 공백으로 나뉜 복수 토큰
    (``"2.1 3.1 4.1"`` 등)이라 바깥쪽 ``|`` 분할로 셀 경계를 잡는다(정규식
    하나로 전체 행을 파싱하지 않는다 — 토큰 안의 공백이 열 경계를 흐린다).
    """
    text = report_path.read_text(encoding="utf-8")
    marker = "## 부록 A."
    idx = text.find(marker)
    if idx < 0:
        raise ValueError(f"'{marker}' 절을 찾지 못했습니다: {report_path}")
    section = text[idx:]

    rows: list[TruthBarFeature] = []
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 8 or not re.fullmatch(r"[0-9]+", cells[0]):
            continue
        bar = int(cells[0])
        volume_norm = float(cells[5])
        low_band_norm = float(cells[6])
        vocal_match = re.match(r"[0-9.]+", cells[7])
        if vocal_match is None:
            raise ValueError(f"마디 {bar}의 보컬 대역 비율 칸을 파싱하지 못했습니다: {cells[7]!r}")
        vocal_band_ratio = float(vocal_match.group(0))
        rows.append(TruthBarFeature(bar, volume_norm, low_band_norm, vocal_band_ratio))

    if not rows:
        raise ValueError(f"부록 A 표에서 특징 행을 하나도 못 찾았습니다: {report_path}")

    rows.sort(key=lambda row: row.bar)
    expected = list(range(1, len(rows) + 1))
    actual_bars = [row.bar for row in rows]
    if actual_bars != expected:
        raise ValueError(
            f"부록 A 마디 번호가 1..{len(rows)} 연속이 아닙니다 — "
            f"파싱 누락 의심: {actual_bars[:10]}..."
        )
    return rows


_EVENT_TYPE_KEYWORDS = (
    ("빌드업", "build"),
    ("큰 히트", "kick_entry"),
    # "break" — spec.md §5 열린 결정 0 events[].kind 어휘(카드 t529 인터페이스 맞춤)와
    # 맞춘 이름이다. M1 당시(카드 t527)는 그 어휘가 아직 없어 "kick_absence"를
    # 썼다 — 카드 t530(M3)에서 bar_map.py의 분류기 출력과 맞추며 통일했다.
    ("킥 멈춤", "break"),
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


#: acceptance.md AC-LDBARMAP-007 정밀도 조건의 증거 종류 2개(카드 t535,
#: 2026-10-10) — 점 사건(point event)만. ``build``·``drop``은 이 정밀도
#: 조건의 분모 밖이다(§ 정밀도 조건 "분모(모집단)" 참조).
_PRECISION_EVIDENCE_KINDS = ("break", "kick_entry")


def parse_precision_evidence(
    report_path: Path = DEFAULT_REPORT_PATH,
) -> dict[str, frozenset[int]]:
    """부록 A "순간" 칸에서 AC-LDBARMAP-007 정밀도 조건의 증거 표시를 뽑는다
    (카드 t535 — 정규식으로 원문에서 직접 파싱, acceptance.md의 표를 하드코딩
    사본으로 베끼지 않는다. acceptance.md § 정밀도 조건의 표 자체가 "이 표는
    부록 A '순간' 칸의 한 시점 스냅샷이다"라고 밝히므로, 스냅샷이 아니라
    원본을 읽는다).

    규칙(acceptance.md AC-LDBARMAP-007 § 근거 있음 판정과 동일):

    * ``break`` — "순간" 칸에 "브레이크" 또는 "킥 빠짐"이 있는 마디.
    * ``kick_entry`` — "큰 히트"가 있는 마디, **합집합** "상승 진입"이 있으면서
      "빌드업"이 **없는** 마디(17마디 제외 규칙 — acceptance.md § "17마디
      제외" 교정. 17마디는 "상승 진입(음량 119%) · 빌드업"으로 겹쳐 적혀
      있지만 빌드업 1(14~17마디)의 꼬리 마디이지 kick_entry 시작이 아니다).

    돌려주는 값은 각 종류의 증거 마디 번호 집합(1-base, frozenset — 순서
    무의미, 멤버십만 쓴다).
    """
    text = report_path.read_text(encoding="utf-8")
    marker = "## 부록 A."
    idx = text.find(marker)
    if idx < 0:
        raise ValueError(f"'{marker}' 절을 찾지 못했습니다: {report_path}")
    section = text[idx:]

    evidence: dict[str, set[int]] = {kind: set() for kind in _PRECISION_EVIDENCE_KINDS}
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 9 or not re.fullmatch(r"[0-9]+", cells[0]):
            continue
        bar = int(cells[0])
        moment = cells[8]
        if not moment:
            continue
        if "브레이크" in moment or "킥 빠짐" in moment:
            evidence["break"].add(bar)
        if "큰 히트" in moment:
            evidence["kick_entry"].add(bar)
        if "상승 진입" in moment and "빌드업" not in moment:
            evidence["kick_entry"].add(bar)

    for kind in _PRECISION_EVIDENCE_KINDS:
        if not evidence[kind]:
            raise ValueError(
                f"부록 A '순간' 칸에서 '{kind}' 증거를 하나도 못 찾았습니다 — "
                f"파싱 누락 의심: {report_path}"
            )
    return {kind: frozenset(bars) for kind, bars in evidence.items()}


def shift_downbeats(downbeats: list[float], shift_sec: float) -> list[float]:
    """정답지 전체를 shift_sec 만큼 밀어낸 격자를 만든다(음성 대조군용, REQ-LDBARMAP-005).

    프로그램적 변형 — 손으로 날조하지 않는다(재현 가능성, plan.md §D).
    """
    return [t + shift_sec for t in downbeats]
