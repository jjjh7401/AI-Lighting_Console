"""LX-SEQ v2.1 RIG 팩 GROUP 시트 파서 (SPEC-COPILOT-LXSEQ-002 M1).

순수 함수다 — 콘솔·네트워크 입출력 0. 바이트를 레코드로 바꾸는 일만 한다.
`server/lxseq/parser.py`(001 M1)의 관용구를 그대로 따른다.

REQ-LXSEQ2-001: 이름 기반 컬럼 매칭(위치 해석 금지), 4개 정규 컬럼, `extra` 보존.
REQ-LXSEQ2-002: 행 검증 실패는 예외가 아니라 닫힌 5부류 거부로 분류한다.
REQ-LXSEQ2-003: `Members` 열은 멤버십 판정에 **쓰지 않는다**. 원문 보존만 한다.

`Members` 를 왜 안 읽는가 — 한 열에 문법이 넷이다(라벨에 개수 / 라벨 합집합 /
전체에서 제외 / 다른 그룹에 대한 술어). 한 파서로 받으면 규칙이 늘 때마다 파서가
늘고, 오해석이 **조용히** 잘못된 그룹을 만든다. 멤버십은 이 프로젝트가 시도한
어느 채널로도 되읽히지 않았고 grandMA3 가 노출하는지 여부는 미측정이라
(SPEC-COPILOT-RESTORE-001 readability-survey.md A.2·A.5), 사후 적발 수단이 없다.
멤버십은 001 의 FID 매핑표와 `group_mapper.py` 의 닫힌 규칙에서만 온다.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

# 정규 컬럼 4개. 헤더는 이 이름들로만 맞춘다 — 위치는 보지 않는다.
CANONICAL_GROUP_COLUMNS: tuple[str, ...] = ("GroupNo", "Name", "Members", "Purpose")

# 그룹 슬롯 번호의 상한.
#
# @MX:NOTE: [AUTO] 1000 은 **실측된 풀 용량**이지 MA3 의 하드 리밋이 아니다.
# @MX:REASON: `prop DataPool/Groups COUNT` 가 그룹이 0개인 풀에서도 1000 을
#   답했다(SPEC-COPILOT-RESTORE-001 readability-survey.md D.8) — 즉 COUNT 는
#   저장된 개수가 아니라 용량이다. 그 값을 상한으로 쓰되, 「MA3 가 1000 을
#   넘는 슬롯을 거부한다」고 주장하지 않는다. 그건 안 쟀다. 여기서 거르는
#   이유는 시트의 오타(자릿수 실수)를 툴 계층에 도달하기 전에 잡는 것이다.
GROUP_SLOT_CEILING = 1000

# 이름에 들어오면 안 되는 따옴표.
#
# @MX:ANCHOR: [AUTO] 이 집합은 `server/groupgen/write.py` `_label_command` 가
#   거부하는 문자와 같아야 한다.
# @MX:REASON: 거기서는 ValueError 로 터지고 그 예외는 **배치 전체**를 죽인다.
#   파서가 먼저 걸러 그 행 하나만 떨어뜨리면 나머지 17개는 살아서 계획에
#   들어간다. 이 등가성이 깨지면 파서를 통과한 이름이 툴 계층에서 터진다.
_FORBIDDEN_NAME_CHARS: tuple[str, ...] = ("'", '"')


class MissingGroupColumnsError(ValueError):
    """정규 4개 중 하나라도 헤더에 없을 때 — 파일 단위 판독 실패."""

    def __init__(self, missing: tuple[str, ...]) -> None:
        self.missing = missing
        super().__init__("missing_columns: " + ", ".join(missing))


@dataclass(frozen=True)
class LxseqGroupRecord:
    """검증을 통과한 그룹 1행."""

    group_no: int
    name: str
    members_raw: str
    purpose: str
    extra: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class GroupRowRejection:
    """행 거부 — 닫힌 `kind` 집합 5부류."""

    row: int
    group_no_raw: str
    name_raw: str
    kind: str
    detail: str


@dataclass(frozen=True)
class GroupParseResult:
    records: tuple[LxseqGroupRecord, ...]
    rejected: tuple[GroupRowRejection, ...]


def _normalize_header(name: str) -> str:
    return name.strip().replace(" ", "").replace("\ufeff", "").lower()


def _resolve_header_map(fieldnames: list[str]) -> dict[str, str]:
    """정규 이름에서 실제 헤더 문자열로. 대소문자·공백 무시, 위치 무관."""
    normalized = dict()
    for name in fieldnames:
        normalized[_normalize_header(name)] = name
    resolved: dict[str, str] = dict()
    missing: list[str] = []
    for canonical in CANONICAL_GROUP_COLUMNS:
        actual = normalized.get(_normalize_header(canonical))
        if actual is None:
            missing.append(canonical)
        else:
            resolved[canonical] = actual
    if missing:
        raise MissingGroupColumnsError(tuple(missing))
    return resolved


def _parse_int(raw: str) -> int | None:
    text = raw.strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _rejection(
    line_no: int, number_raw: str, name_raw: str, kind: str, detail: str
) -> GroupRowRejection:
    return GroupRowRejection(
        row=line_no, group_no_raw=number_raw, name_raw=name_raw, kind=kind, detail=detail
    )


def parse_group_csv(text: str) -> GroupParseResult:
    """GROUP 시트 본문을 레코드와 거부로 가른다.

    행 검증 실패는 예외로 새어나가지 않는다(REQ-LXSEQ2-002). 파일 단위
    실패인 `missing_columns` 만 `MissingGroupColumnsError` 로 올린다.

    한 행에 결함이 여럿이면 **먼저 걸린 하나만** 보고한다 — 행당 거부 하나다.
    검사 순서는 번호(정수 → 범위 → 중복) 다음 이름(빈값 → 따옴표)이다.
    """
    if text.startswith("\ufeff"):
        text = text[1:]

    reader = csv.DictReader(io.StringIO(text))
    fieldnames = list(reader.fieldnames or [])
    header_map = _resolve_header_map(fieldnames)
    canonical_actuals = set(header_map.values())
    extra_columns = [name for name in fieldnames if name not in canonical_actuals]

    records: list[LxseqGroupRecord] = []
    rejected: list[GroupRowRejection] = []
    seen_numbers: dict[int, int] = dict()

    for offset, row in enumerate(reader):
        line_no = offset + 2  # 헤더가 1행
        number_raw = (row.get(header_map["GroupNo"]) or "").strip()
        name_raw = (row.get(header_map["Name"]) or "").strip()

        number = _parse_int(number_raw)
        if number is None:
            rejected.append(
                _rejection(
                    line_no,
                    number_raw,
                    name_raw,
                    "groupno_not_int",
                    "GroupNo 가 정수가 아니다: " + repr(number_raw),
                )
            )
            continue
        if number < 1 or number > GROUP_SLOT_CEILING:
            rejected.append(
                _rejection(
                    line_no,
                    number_raw,
                    name_raw,
                    "groupno_out_of_range",
                    "GroupNo 가 1 이상 "
                    + str(GROUP_SLOT_CEILING)
                    + " 이하가 아니다: "
                    + str(number),
                )
            )
            continue
        if number in seen_numbers:
            rejected.append(
                _rejection(
                    line_no,
                    number_raw,
                    name_raw,
                    "groupno_duplicate",
                    "GroupNo "
                    + str(number)
                    + " 는 "
                    + str(seen_numbers[number])
                    + "행에서 이미 쓰였다",
                )
            )
            continue
        if not name_raw:
            rejected.append(
                _rejection(line_no, number_raw, name_raw, "name_empty", "Name 이 비어 있다")
            )
            continue
        offending = [ch for ch in _FORBIDDEN_NAME_CHARS if ch in name_raw]
        if offending:
            rejected.append(
                _rejection(
                    line_no,
                    number_raw,
                    name_raw,
                    "name_has_quote",
                    "Name 에 따옴표가 있다 ("
                    + "".join(offending)
                    + ") — Label 명령이 조립되지 않는다",
                )
            )
            continue

        seen_numbers[number] = line_no
        extra = dict()
        for column in extra_columns:
            extra[column] = row.get(column) or ""
        records.append(
            LxseqGroupRecord(
                group_no=number,
                name=name_raw,
                # Members 는 strip 도 하지 않는다 — 원문 그대로가 계약이다.
                members_raw=row.get(header_map["Members"]) or "",
                purpose=(row.get(header_map["Purpose"]) or "").strip(),
                extra=extra,
            )
        )

    return GroupParseResult(records=tuple(records), rejected=tuple(rejected))
