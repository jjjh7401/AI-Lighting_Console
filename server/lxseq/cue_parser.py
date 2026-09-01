"""LX-SEQ CUE-EX 시트 파서 (SPEC-COPILOT-LXSEQ-004 M1, t209).

순수 함수다 -- 콘솔·네트워크 입출력 0. `server/lxseq/group_parser.py`(002 M1)
의 관용구를 그대로 따른다: 이름 기반 컬럼 매칭(위치 해석 금지), 행 검증
실패는 예외가 아니라 닫힌 거부 목록으로, 파일 단위 실패만 예외로 올린다.

CUE-EX 는 long format 이다(명세서 §11 제목) -- 한 큐 × 한 그룹 = 한 행.
정본 CSV(`LXSEQ_SAMPLE_01_Sugar_r3.cue-ex.csv`)는 89행 / 고유 Q# 18개다.

## 왜 모든 값 열이 `_raw` 로 원문 보존인가 (REQ-LXSEQ4-001)

명세서 §11.2 (1): "빈칸 = 트래킹." `Dim` 이 빈 칸이면 그 그룹은 이번 큐에서
값을 바꾸지 않는다는 뜻이지 0%(소등)라는 뜻이 아니다. 소등은 `Dim 0` +
`I-Fade` 를 명시해야 한다(§11.2 (2)). 파서가 빈 칸을 `0` 이나 `None` 으로
접으면 트래킹과 소등이 같은 값이 되어 mapper 층에서 더는 구별할 수 없다 --
그 구별을 파서가 없애면 명세서가 금지한 사고(침묵으로 끄기)가 파서
안에서 조용히 일어난다. 해석은 mapper 몫이다.

## 왜 is_video_call 인가 (유출 사고 재발 방지)

LED-W 그룹은 영상팀이 소유한 큐 콜이다 -- 조명 콘솔에 명령을 내면 안
된다(과거 유출 사고). 그렇다고 그 행을 버리면 그 큐 번호가 조용히
증발하고, 다음 사람은 "그 행이 원래 없었다"와 "걸러졌다"를 구별할 수
없다. 그래서 버리지 않고 레코드로 남기되 is_video_call=True 로 표시한다
-- mapper/tool 층이 이 플래그를 보고 콘솔 명령 생성에서 제외할 책임을
진다(이번 회차 범위 밖).

## 계약 (t209 배차, sync 레인의 cue_mapper.py 와 동시 진행)

리드가 이 파일과 LxseqCueRecord/CueParseResult 의 필드 이름·타입을
못 박았다 -- 협의 없이 이 문면이 정본이다. mapper 는 이 산출물을
소비하는 별도 회차다.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass

CANONICAL_CUE_COLUMNS: tuple[str, ...] = (
    "Q#",
    "Group",
    "Dim",
    "COL",
    "POS",
    "BM",
    "FX",
    "FX-Rate",
    "FX-Phase",
    "FX-Width",
    "I-Fade",
    "I-Delay",
    "P-Fade",
    "C-Fade",
    "B-Fade",
    "Snap",
    "Note",
)

_VIDEO_CALL_GROUP = "LED-W"


class MissingCueColumnsError(ValueError):
    """정규 17개 중 하나라도 헤더에 없을 때 -- 파일 단위 판독 실패."""

    def __init__(self, missing: tuple[str, ...]) -> None:
        self.missing = missing
        super().__init__("missing_columns: " + ", ".join(missing))


@dataclass(frozen=True)
class LxseqCueRecord:
    """한 큐 x 한 그룹 = 한 행(명세서 11절 제목). 모든 값 열은 원문 그대로다."""

    cue_no: str
    group: str
    dim_raw: str
    col_raw: str
    pos_raw: str
    bm_raw: str
    fx_raw: str
    fx_rate_raw: str
    fx_phase_raw: str
    fx_width_raw: str
    i_fade_raw: str
    i_delay_raw: str
    p_fade_raw: str
    c_fade_raw: str
    b_fade_raw: str
    snap_raw: str
    note: str
    is_video_call: bool


@dataclass(frozen=True)
class CueRowRejection:
    """행 거부 -- 조용히 건너뛰지 않는다."""

    row_no: int
    reason: str
    detail: str


@dataclass(frozen=True)
class CueParseResult:
    records: tuple[LxseqCueRecord, ...]
    rejections: tuple[CueRowRejection, ...]
    cue_numbers: tuple[str, ...]


def _normalize_header(name: str) -> str:
    return name.strip().replace(" ", "").replace(chr(0xFEFF), "").lower()


def _resolve_header_map(fieldnames: list[str]) -> dict[str, str]:
    normalized = dict()
    for name in fieldnames:
        normalized[_normalize_header(name)] = name
    resolved: dict[str, str] = dict()
    missing: list[str] = []
    for canonical in CANONICAL_CUE_COLUMNS:
        actual = normalized.get(_normalize_header(canonical))
        if actual is None:
            missing.append(canonical)
        else:
            resolved[canonical] = actual
    if missing:
        raise MissingCueColumnsError(tuple(missing))
    return resolved


def parse_cue_csv(text: str) -> CueParseResult:
    """CUE-EX 시트 본문을 레코드와 거부로 가른다.

    행 검증 실패는 예외로 새어나가지 않는다. 파일 단위 실패인
    missing_columns 만 MissingCueColumnsError 로 올린다. 값 열은 전혀
    해석하지 않는다 -- 파싱과 해석은 다른 일이다.
    """
    if text.startswith(chr(0xFEFF)):
        text = text[1:]

    reader = csv.DictReader(io.StringIO(text))
    fieldnames = list(reader.fieldnames or [])
    header_map = _resolve_header_map(fieldnames)

    records: list[LxseqCueRecord] = []
    rejections: list[CueRowRejection] = []
    cue_numbers: list[str] = []
    seen_cue_numbers: set[str] = set()

    def cell(row: dict[str, str], canonical: str) -> str:
        return row.get(header_map[canonical]) or ""

    for offset, row in enumerate(reader):
        line_no = offset + 2
        cue_no = cell(row, "Q#").strip()
        group = cell(row, "Group").strip()

        if not cue_no:
            rejections.append(
                CueRowRejection(row_no=line_no, reason="cue_no_empty", detail="Q# 가 비어 있다")
            )
            continue
        if not group:
            rejections.append(
                CueRowRejection(row_no=line_no, reason="group_empty", detail="Group 이 비어 있다")
            )
            continue

        if cue_no not in seen_cue_numbers:
            seen_cue_numbers.add(cue_no)
            cue_numbers.append(cue_no)

        records.append(
            LxseqCueRecord(
                cue_no=cue_no,
                group=group,
                dim_raw=cell(row, "Dim"),
                col_raw=cell(row, "COL"),
                pos_raw=cell(row, "POS"),
                bm_raw=cell(row, "BM"),
                fx_raw=cell(row, "FX"),
                fx_rate_raw=cell(row, "FX-Rate"),
                fx_phase_raw=cell(row, "FX-Phase"),
                fx_width_raw=cell(row, "FX-Width"),
                i_fade_raw=cell(row, "I-Fade"),
                i_delay_raw=cell(row, "I-Delay"),
                p_fade_raw=cell(row, "P-Fade"),
                c_fade_raw=cell(row, "C-Fade"),
                b_fade_raw=cell(row, "B-Fade"),
                snap_raw=cell(row, "Snap"),
                note=cell(row, "Note"),
                is_video_call=(group == _VIDEO_CALL_GROUP),
            )
        )

    return CueParseResult(
        records=tuple(records),
        rejections=tuple(rejections),
        cue_numbers=tuple(cue_numbers),
    )
