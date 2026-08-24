"""LX-SEQ RIG 팩 PRESET 시트 파서 (SPEC-COPILOT-LXSEQ-003 M1).

순수 함수다 — 콘솔·네트워크 입출력 0. `server/lxseq/group_parser.py`(002 M1)의
관용구를 따르되 **판별을 정확 열 집합으로** 한다(REQ-LXSEQ3-001).

세 종류의 열 집합이 서로 다르고, 넷째(`preset-pos`)까지 넣어도 쌍마다 구별된다.
그래서 포함 검사가 필요 없다 — 포함 검사로는 `col` 과 `bm` 이 안 갈린다.

`preset-pos` 의 서명도 분기도 두지 않는다(REQ-LXSEQ3-002). 그 시트는 값 열이
없고 현장 레코드 대상이라 이 경로의 물건이 아니다.

## 왜 레코드가 `storable` 을 들고 다니는가

시트 19행이 전부 콘솔에 넣을 수 있는 값은 **아니다.** 실측(정본 CSV, 값 열 전수):

    dim 6/6   100% · 85% · 60% · 30% · 15% · 0%       -> 넣을 수 있다
    col 6/8   R255 G180 B60 형태                       -> 보류(아래)
    col 2/8   ~3200K · ~5600K                          -> 보류(아래)
    bm  0/5   Zoom 45 도 · Gobo OPEN · Prism OFF 형태  -> 보류(아래)

파싱과 투입은 다른 일이므로 **19행은 전부 레코드로 읽는다.** 대신 넣을 수 없는
행을 **버리지 않고 사유와 함께 나른다.** 그냥 넣을 수 있는 것만 처리하면 나머지가
어디로 갔는지 아무도 모르고, 다음 사람이 무엇을 풀어야 하는지도 모른다.

이 필드가 없으면 「19 레코드가 나온다」는 검사가 파싱만 재고 통과한다 — 그리고
문면대로 구현하면 「19건 성공」이 적히는데 13건은 저장 단계에서 터지거나 빈
프로그래머에 대해 저장된다.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass

from server.looks.schema import CONFIRMED_ATTRIBUTES, PROBE_GATED_ATTRIBUTES

#: 세 종류의 **정확** 열 집합. 정본 실측이며 여기가 유일한 선언 자리다.
PRESET_SHEET_COLUMNS: dict[str, tuple[str, ...]] = dict(
    [
        ("dim", ("ID", "Name", "Level", "Purpose")),
        ("col", ("ID", "Name", "Value", "Purpose")),
        ("bm", ("ID", "Name", "TargetGroup", "Value")),
    ]
)

#: 시트 종류별 ID 접두. 어긋난 행은 거부하고 보고한다(REQ-LXSEQ3-003).
PRESET_ID_PREFIXES: dict[str, str] = dict([("dim", "DIM."), ("col", "COL."), ("bm", "BM.")])

#: 이 저장소가 **실기로 재서** 콘솔이 받는다고 확인한 속성.
#: `server/looks/schema.py` 가 정본이다 — 여기서 사본을 만들지 않는다.
_ACCEPTED_ATTRIBUTES = frozenset(CONFIRMED_ATTRIBUTES + PROBE_GATED_ATTRIBUTES)

#: 라이브 프로브가 **거절한** 속성. `server/looks/schema.py:15-18` —
#: "Focus / Frost / Prism1 / Shutter were rejected by the console".
#: 부재가 아니라 **이미 재서 안 되는 것**이다. grep 으로 다시 찾지 마라.
_PROBE_REJECTED = ("Focus", "Frost", "Prism", "Shutter")

#: 풀 계열 자체가 범위 밖인 것. `server/looks/schema.py:55-57` —
#: "Position/All/Gobo/Control/Shapers/Video are out of scope".
_OUT_OF_SCOPE = ("Gobo", "Position", "Control", "Shapers", "Video")

#: dim 의 `Level` 이 취하는 형태. 콘솔의 `Attribute 'Dimmer' At <n>` 이 퍼센트라
#: 시트와 단위가 같다 — 세 시트 중 **해석이 0인 유일한 자리**다.
_PERCENT = re.compile(r"^\s*(\d+)\s*%\s*$")

#: 값 문장에서 속성 이름 후보로 읽을 토큰. 숫자·단위·한글은 보지 않는다.
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9]*")

#: col 값에 RGB 삼원색이 적혔는지. 색온도만 있는 행과 가르는 데만 쓴다.
_HAS_RGB = re.compile(r"R\s*\d")


class UnknownPresetSheetError(ValueError):
    """헤더가 세 정확 열 집합 중 어느 것과도 같지 않다 — 파일 단위 판독 실패."""

    def __init__(self, header: tuple[str, ...]) -> None:
        self.header = header
        super().__init__("unknown_preset_sheet: " + ", ".join(header))


@dataclass(frozen=True)
class LxseqPresetRecord:
    """검증을 통과한 프리셋 1행.

    `value_raw` 는 **가공하지 않은 원문**이다. `purpose` 는 보존만 하고 값 산출에
    쓰지 않으며(REQ-LXSEQ3-004), `target_group` 은 문자열 그대로 두고 FID 로
    확장하지 않는다(REQ-LXSEQ3-005) — 그룹 멤버십은 어느 채널로도 읽히지 않아
    확장의 근거가 없다.
    """

    kind: str
    preset_id: str
    name: str
    value_raw: str
    row: int
    storable: bool
    hold_reason: str
    target_group: str | None = None
    purpose: str | None = None


@dataclass(frozen=True)
class PresetRowRejection:
    """행 거부 — 조용히 건너뛰지 않는다."""

    row: int
    preset_id_raw: str
    name_raw: str
    kind: str
    detail: str


@dataclass(frozen=True)
class PresetParseResult:
    sheet_kind: str
    records: tuple[LxseqPresetRecord, ...]
    rejected: tuple[PresetRowRejection, ...]


def _normalize(name: str) -> str:
    return name.strip().replace("\ufeff", "").replace(" ", "").lower()


def resolve_sheet_kind(header: tuple[str, ...]) -> str:
    """헤더의 **정확 열 집합**으로 종류를 정한다. 파일 이름을 보지 않는다.

    포함 검사를 쓰지 않는 이유: col(ID·Name·Value·Purpose)의 세 열을 포함
    검사로 두면 bm(ID·Name·TargetGroup·Value) 헤더가 그 서명에도 맞아 둘이
    안 갈린다. 정확 집합이면 넷이 쌍마다 구별된다.
    """
    present = frozenset(_normalize(name) for name in header)
    for kind, columns in PRESET_SHEET_COLUMNS.items():
        if present == frozenset(_normalize(name) for name in columns):
            return kind
    raise UnknownPresetSheetError(header)


def _attribute_tokens(value: str) -> list[str]:
    """값 문장에서 속성 이름으로 읽히는 토큰만 뽑는다. 값을 해석하지 않는다."""
    known_names = list(_ACCEPTED_ATTRIBUTES) + list(_PROBE_REJECTED) + list(_OUT_OF_SCOPE)
    found: list[str] = []
    for token in re.findall(_WORD, value):
        for known in known_names:
            if token.lower().startswith(known.lower()) and known not in found:
                found.append(known)
    return found


def classify_storability(kind: str, value_raw: str) -> tuple[bool, str]:
    """이 값을 지금 콘솔에 넣을 수 있는가, 없으면 왜 없는가.

    **부재가 아니라 판정이다.** 아래 사유는 전부 이 저장소가 이미 실기로 재서
    적어 둔 것이며(server/looks/schema.py), 다시 검색으로 찾아 닫힌 질문을
    열지 마라.
    """
    if kind == "dim":
        if _PERCENT.match(value_raw):
            return True, ""
        return False, "Level 이 퍼센트 형태가 아니다: " + value_raw.strip()

    if kind == "col":
        if _HAS_RGB.search(value_raw):
            return False, (
                "RGB 가 0-255 로 적혔고 콘솔은 0-100 퍼센트다. 두 축의 대응은 "
                "미측정이라 변환이 해석이 된다 — 값은 되읽을 수 없다"
            )
        return False, (
            "색온도만 있고 RGB 가 없다: "
            + value_raw.strip()
            + " — 켈빈에서 RGB 를 만드는 모델이 이 저장소에 없다"
        )

    tokens = _attribute_tokens(value_raw)
    blocked_rejected = [a for a in tokens if a in _PROBE_REJECTED]
    blocked_scope = [a for a in tokens if a in _OUT_OF_SCOPE]
    if blocked_rejected or blocked_scope:
        parts = []
        if blocked_rejected:
            parts.append("라이브 프로브가 거절한 속성: " + ", ".join(blocked_rejected))
        if blocked_scope:
            parts.append("풀 계열이 범위 밖인 속성: " + ", ".join(blocked_scope))
        return False, " / ".join(parts) + " (server/looks/schema.py 의 M0 프로브 판정)"
    return True, ""


def parse_preset_csv(text: str) -> PresetParseResult:
    """PRESET 시트 본문을 레코드와 거부로 가른다.

    행 검증 실패는 예외로 새어나가지 않는다. 파일 단위 실패인
    unknown_preset_sheet 만 UnknownPresetSheetError 로 올린다.
    한 행에 결함이 여럿이면 먼저 걸린 하나만 보고한다 — 행당 거부 하나다.
    """
    if text.startswith("\ufeff"):
        text = text[1:]
    reader = csv.DictReader(io.StringIO(text))
    header = tuple(reader.fieldnames or [])
    kind = resolve_sheet_kind(header)
    columns = PRESET_SHEET_COLUMNS[kind]
    actual = dict((_normalize(name), name) for name in header)
    prefix = PRESET_ID_PREFIXES[kind]
    value_column = "Level" if kind == "dim" else "Value"

    records: list[LxseqPresetRecord] = []
    rejected: list[PresetRowRejection] = []
    seen: set[str] = set()

    for line_no, row in enumerate(reader, start=2):
        cell = dict((name, (row.get(actual[_normalize(name)]) or "").strip()) for name in columns)
        preset_id = cell["ID"]
        name = cell["Name"]
        problem = None
        if not preset_id:
            problem = ("empty_id", "ID 가 비었다")
        elif not preset_id.startswith(prefix):
            problem = (
                "id_prefix_mismatch",
                "이 시트는 " + prefix + " 로 시작해야 한다: " + preset_id,
            )
        elif preset_id in seen:
            problem = ("duplicate_id", "같은 ID 가 두 번 나온다: " + preset_id)
        elif not name:
            problem = ("empty_name", "Name 이 비었다")
        if problem is not None:
            rejected.append(
                PresetRowRejection(
                    row=line_no,
                    preset_id_raw=preset_id,
                    name_raw=name,
                    kind=problem[0],
                    detail=problem[1],
                )
            )
            continue

        seen.add(preset_id)
        value_raw = cell[value_column]
        storable, hold_reason = classify_storability(kind, value_raw)
        records.append(
            LxseqPresetRecord(
                kind=kind,
                preset_id=preset_id,
                name=name,
                value_raw=value_raw,
                row=line_no,
                storable=storable,
                hold_reason=hold_reason,
                target_group=cell.get("TargetGroup") or None,
                purpose=cell.get("Purpose") or None,
            )
        )
    return PresetParseResult(sheet_kind=kind, records=tuple(records), rejected=tuple(rejected))
