"""SPEC-COPILOT-AUTOPATCH-001 **문서 불변식**의 기계 강제 (`R21-B`).

**왜 있는가.** 이 SPEC은 코드 축에서 *"규율을 세우면 대조군을 붙인다"*를 스물두 라운드
반복했으나 **문서 축에는 같은 원칙을 적용하지 않았다** — 검사 명령은 `plan.md` §B ①에
글로 적혀 있었고 실행은 사람에게 있었다. 그 결과 세 가지가 실제로 깨졌다:

  1. 라운드 계수 셀이 **8 → 7**로 떨어졌다(`R21-B`). M8 커밋이 `progress.md` 프론트매터
     `next:` 줄을 통째로 다시 쓰며 표지 토큰을 함께 지웠다 — round19가 프로브로 예측한
     실패 형태 그대로였고, **검사기는 작동했으나 아무도 돌리지 않았다.**
  2. 같은 `next:` 줄이 **테스트 계수**(`N passed`)도 잃고 있었다(round22 Docs 발견).
  3. 자기참조 커밋 계수가 한 세션 안에서 세 번 stale이 됐다.

**이 파일이 읽는 범위.** `.moai/specs/SPEC-COPILOT-AUTOPATCH-001/` 아래 `*.md` 여덟
아티팩트뿐이다. 다른 SPEC · 다른 디렉터리 · 소스 코드 본문은 읽지 않는다(활성 파일
목록을 파생할 때만 `server/vwx` · `server/tests` 디렉터리 **이름**을 훑는다).
그 안에서도 **이미 깨졌던 네 축**만 본다:

  (가) 라운드 계수 셀 — 개수 · 값 일치 · `plan.md` 규칙 문장 선언과의 3자 일치
  (나) 프론트매터 `next:` — 라운드 계수 토큰 · 테스트 계수 · 커밋 계수 세 항목의 **존재**
  (다) 활성 파일에 대한 `파일:행` 인용이 **신규로** 생기지 않음(동결 목록 · 축소만 허용)
  (라) 불변식 계수 — AC 27 · REQ 26 · §C.0a 합 27 · AC-026 ①~⑦

**이 파일이 보지 않는 것 — 한계를 먼저 적는다.**
round22 Docs가 프로브 ⓓ(*표에서 행을 지운다*)로 실증했다: **NOT CAUGHT**였다. 계수 셀
축은 "표지 토큰이 몇 개이고 값이 같은가"만 보기 때문이다. 구체적으로:

  · **표·문단의 내용** — §C.0a 이외의 표에서 행을 지우거나 문단이 통째로 사라져도
    토큰 개수가 그대로면 조용하다. 토큰 없는 셀은 애초에 보이지 않는다(round19 프로브).
  · **셀 값의 진위** — 여덟 셀이 **같은 값으로 함께** stale이면 통과한다. 값이 실제
    라운드 수와 맞는지는 사람이 본다.
  · **`next:` 항목의 값** — 계수가 *있는가*만 보고 *맞는가*는 보지 않는다. 값 대조는
    "무엇이 참값인가"를 문서 밖에서 알아야 해서 이 축에 넣을 수 없다.
  · **산문의 진위** — 문장이 사실인지, 인용이 옳은 자리를 가리키는지 보지 않는다.
  · **`.moai/specs` 밖** — 다른 SPEC · 리포트 · 커밋 메시지는 범위 밖이다.

**과도하게 만들지 않는다.** 문서 전반을 검사하면 위양성이 문서 작업을 막고, 흔한
위양성은 게이트의 강제력을 없앤다(round15 D · round17 #7이 같은 판단을 했다).

**비공허성.** 네 축마다 반대 대조군을 둔다 — `tempfile` 사본에서 규율을 깨뜨리고
**프로덕션 단정 함수 그 자체**가 `AssertionError`를 내는지 본다(같은 코드 경로여야
대조군이 진짜다). 워킹트리는 건드리지 않는다.
"""

from __future__ import annotations

import itertools
import re
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from server.tests.test_autopatch_contract import iter_vwx_modules, vwx_module_label

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPEC_DIRNAME = "SPEC-COPILOT-AUTOPATCH-001"
SPEC_DIR = PROJECT_ROOT / ".moai" / "specs" / SPEC_DIRNAME

#: 있어야 하는 아티팩트. 하나라도 없으면 **skip이 아니라 실패**다 — 문서가 조용히
#: 사라지는 것(=축소)이 이 파일이 막으려는 사고의 하나이므로, 없으면 없다고 말해야 한다.
REQUIRED_DOCS = (
    "M0-SHOWFILE-SPEC.md",
    "M8-REDEFINITION-DRAFT.md",
    "acceptance.md",
    "design.md",
    "plan.md",
    "progress.md",
    "research.md",
    "spec.md",
)

# ---- (가) 라운드 계수 셀 --------------------------------------------------------------

#: 표지 토큰의 라벨. **완성형(`[라벨=숫자]`)을 이 파일 어디에도 적지 않고 조립한다.**
#: 이유: 검사기는 토큰의 완성형을 세므로, 규칙을 *설명하는* 산문이 완성형을 쓰면 계수가
#: 부풀어 오탐이 난다 — round19가 이 함정을 명시했고 round21·round22가 실제로 밟아
#: 계수 `9`를 냈다. 스캔 뿌리는 지금 `.moai/specs` 아래뿐이라 이 파일은 세어지지 않지만,
#: 뿌리가 넓어지는 순간 이 파일이 아홉 번째 셀이 된다. 조립이 그 경로를 원천 차단한다.
_CELL_LABEL = "라운드계수셀"
_CELL_RE = re.compile(r"\[" + _CELL_LABEL + r"=(\d*)\]")

#: `plan.md` §B ①의 규칙 문장이 **스스로 선언하는** 셀 수를 읽는 자리.
#: round19 #1의 결함이 정확히 여기였다 — 규칙이 「넷」이라 적는 동안 실제는 여덟이었다.
_KOREAN_NUMERALS = {
    "셋": 3,
    "넷": 4,
    "다섯": 5,
    "여섯": 6,
    "일곱": 7,
    "여덟": 8,
    "아홉": 9,
    "열": 10,
}
_DECLARED_CELL_RE = re.compile(r"셀은\s*\*\*(" + "|".join(_KOREAN_NUMERALS) + r")\*\*")

#: 실측·규칙 선언과 3자를 이룬다. 셀을 늘리는 것은 개선이므로 막지 않는다 —
#: 다만 이 상수와 `plan.md` 규칙 문장을 **함께** 올려야 통과한다. 그 결합이 요점이다.
EXPECTED_CELL_COUNT = 8

# ---- (나) 프론트매터 `next:` ----------------------------------------------------------

_NEXT_RE = re.compile(r"^next:(.*)$", re.MULTILINE)

#: 세 번 다 잃어본 항목이므로 세 항목을 각각 단정한다. **존재만** 본다(값은 위 한계 참조).
_NEXT_REQUIREMENTS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("라운드 계수 셀 토큰", _CELL_RE),
    ("테스트 계수(`N passed`)", re.compile(r"[\d,]+\s*passed")),
    ("커밋 계수", re.compile(r"커밋.{0,30}?\d")),
)

# ---- (다) 활성 파일에 대한 `파일:행` 인용 ----------------------------------------------

_CITATION_RE = re.compile(
    r"(?P<dir>[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*/)?(?P<file>[A-Za-z0-9_]+\.py):(?P<line>\d+)"
)
_SECTION_RE = re.compile(r"^##\s+(.*)$")

#: 면제 밖에서 살아 있는 인용의 **동결 목록**. 값은 허용 상한이며 **축소만** 허용된다
#: (없어지면 통과, 늘거나 새 항목이 생기면 실패).
#:   · §0 셋은 round19 #1이 **자기 이전 판을 인용해 정정한** 기록이다 — 좌표를 지우면
#:     "이전 판은 무엇이었나"가 사라져 정정 기록이 성립하지 않는다.
#:   · `diff.py:179`은 `next:` 안의 **범위 밖 관측**(1단계 PRESERVE)이라 심볼로 바꾸지
#:     못한 자리다.
_FROZEN_LINE_CITATIONS: dict[tuple[str, str], int] = {
    ("progress.md", "patchplan.py:531"): 1,
    ("progress.md", "verdicts.py:13"): 1,
    ("progress.md", "apply.py:127"): 1,
    ("progress.md", "diff.py:179"): 1,
}

# ---- (라) 불변식 계수 ------------------------------------------------------------------

_AC_ID_RE = re.compile(r"AC-AUTOPATCH-(\d{3})")
_REQ_ID_RE = re.compile(r"REQ-AUTOPATCH-(\d{3})")
_AC026_BULLET_RE = re.compile(r"^ {2}- (?P<mark>[\u2460-\u2473])", re.MULTILINE)
_NEXT_HEADING_RE = re.compile(r"\n#{2,3} ")

EXPECTED_AC_COUNT = 27
EXPECTED_REQ_COUNT = 26
EXPECTED_AC026_ITEMS = ("①", "②", "③", "④", "⑤", "⑥", "⑦")


# ======================================================================================
# 판독기 — 뿌리(`root`)를 인자로 받는다. 대조군이 임시 사본에 **같은 함수**를 걸기 위해서다.
# ======================================================================================


def _read(root: Path, name: str) -> str:
    path = root / name
    assert path.is_file(), (
        f"{SPEC_DIRNAME}/{name} 이 없다. 이 게이트는 문서가 없으면 skip하지 않는다 — "
        "아티팩트가 조용히 사라지는 것 자체가 막으려는 사고다."
    )
    return path.read_text(encoding="utf-8")


def _spec_markdown(root: Path) -> tuple[tuple[str, str], ...]:
    """SPEC 디렉터리 아래 `*.md` 를 (상대경로, 본문)으로. 재귀 — `grep -r` 재도출이다."""
    assert root.is_dir(), f"{root} 가 없다 — SPEC 디렉터리 자체가 사라졌다."
    docs = tuple(
        (path.relative_to(root).as_posix(), path.read_text(encoding="utf-8"))
        for path in sorted(root.rglob("*.md"))
    )
    assert docs, f"{root} 에 마크다운이 0건이다 — 아래 단정이 공허해진다."
    return docs


def _round_count_cells(root: Path) -> tuple[tuple[str, str], ...]:
    r"""표지 토큰 실측 — (파일, 값).

    `plan.md` §B ①의 두 줄 명령을 **베끼지 않고 재도출한다.** 명령은
    `grep -rno '\[<라벨>=[0-9]*\]' $S | wc -l`(개수)와 `grep -rho ... | sort | uniq -c`
    (값 분포)이며, 여기서는 같은 정규식을 같은 뿌리에 걸어 일치를 모은 뒤 개수와 값
    집합을 따로 단정한다. 명령 쪽 정규식·뿌리가 바뀌면 두 결과가 갈라지고, 그 갈라짐이
    곧 이 게이트의 실패로 나타난다.

    읽는 범위: `.moai/specs/SPEC-COPILOT-AUTOPATCH-001/**/*.md` 전부.
    """
    return tuple(
        (name, match.group(1))
        for name, text in _spec_markdown(root)
        for match in _CELL_RE.finditer(text)
    )


def _declared_cell_count(root: Path) -> int:
    """`plan.md` 규칙 문장이 선언하는 셀 수."""
    match = _DECLARED_CELL_RE.search(_read(root, "plan.md"))
    assert match, (
        "plan.md 에서 셀 수를 선언하는 문장(「… 셀은 **N**이며 …」)을 찾지 못했다. "
        "문장을 바꿨다면 이 정규식도 함께 고쳐라 — round19 #1의 결함이 바로 "
        "'규칙의 열거와 실제가 갈라진 것'이었다."
    )
    return _KOREAN_NUMERALS[match.group(1)]


def _next_entry(root: Path) -> str:
    """`progress.md` 프론트매터 `next:` 값. 두 건이거나 0건이면 그 자체가 실패다."""
    matches = _NEXT_RE.findall(_read(root, "progress.md"))
    assert len(matches) == 1, f"progress.md 의 `next:` 항목이 {len(matches)}건이다(1건이어야 한다)."
    return matches[0]


def _active_paths() -> frozenset[str]:
    """`파일:행` 인용이 금지되는 **활성 파일** 경로.

    활성의 정의는 round19 #1 심볼 규율 그대로다 — `server/vwx/**` ·
    `server/orchestrator/tools.py` · `server/tests/test_autopatch_*.py`.
    손으로 쓴 목록을 두지 않고 저장소에서 파생한다: 목록을 두면 모듈이 늘 때 조용히
    규율 밖으로 빠지고, 그 형태가 round17 #8~#10이었다.
    [round24] `server/vwx/**`라 적어 놓고 순회는 평면 `glob("*.py")`이었다 — 하위
    패키지가 생기는 날 그 모듈들이 활성 목록에서 조용히 빠지므로 공용 순회로 바꿨다.
    """
    vwx_root = PROJECT_ROOT / "server" / "vwx"
    paths = {f"server/vwx/{vwx_module_label(p)}" for p in iter_vwx_modules(vwx_root)}
    paths.add("server/orchestrator/tools.py")
    paths |= {
        f"server/tests/{p.name}"
        for p in (PROJECT_ROOT / "server" / "tests").glob("test_autopatch_*.py")
    }
    assert "server/vwx/patchplan.py" in paths, sorted(paths)
    assert "server/tests/test_autopatch_contract.py" in paths, sorted(paths)
    return frozenset(paths)


def _is_exempt(doc: str, heading: str | None) -> bool:
    """면제 구역 판정 — 스냅샷이라 지금 규율을 소급 적용하면 기록이 거짓이 되는 자리.

    ① `progress.md` 첫 `##` 이전 = 인용 규율 **본문**이고 거기 적힌 좌표는 규칙의 예시다.
    ② `§E.2*` = append-only 라운드 기록이며, 그때의 좌표로 남긴 인용을 지금 좌표로 고치면
       "그 라운드가 무엇을 봤는가"가 바뀐다.
    """
    if heading is None:
        return doc == "progress.md"
    return heading.startswith("§E.2")


def _line_citations(root: Path) -> tuple[dict[tuple[str, str], int], int]:
    """활성 파일에 대한 `파일:행` 인용 — (면제 밖 집계, 면제 안 건수).

    경로 접두가 붙은 인용은 접두까지 대조하고, 파일명만 적힌 인용은 파일명으로 판정한다
    (`report.py`·`verdicts.py`는 다른 패키지에도 있으나, 수식 없는 인용은 이 SPEC 문맥에서
    vwx를 가리키므로 잡는 쪽이 안전하다 — 오탐이면 접두를 붙여 명확히 하면 된다).
    """
    active_paths = _active_paths()
    active_names = {Path(p).name for p in active_paths}
    outside: dict[tuple[str, str], int] = {}
    exempt = 0
    for doc, text in _spec_markdown(root):
        heading: str | None = None
        for line in text.splitlines():
            section = _SECTION_RE.match(line)
            if section:
                heading = section.group(1).strip()
                continue
            for match in _CITATION_RE.finditer(line):
                directory = match.group("dir") or ""
                filename = match.group("file")
                if directory:
                    if f"{directory}{filename}".lstrip("./") not in active_paths:
                        continue
                elif filename not in active_names:
                    continue
                if _is_exempt(doc, heading):
                    exempt += 1
                else:
                    key = (doc, f"{filename}:{match.group('line')}")
                    outside[key] = outside.get(key, 0) + 1
    return outside, exempt


def _c0a_rows(root: Path) -> tuple[tuple[str, tuple[str, ...], int], ...]:
    """`acceptance.md` §C.0a 마일스톤별 AC 배정표 — (마일스톤, AC 번호들, 선언한 수)."""
    text = _read(root, "acceptance.md")
    start = text.find("### §C.0a")
    assert start != -1, "acceptance.md 에서 §C.0a 마일스톤 배정표를 찾지 못했다."
    body = text[start:]
    end = _NEXT_HEADING_RE.search(body, 1)
    section = body[: end.start()] if end else body
    rows: list[tuple[str, tuple[str, ...], int]] = []
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 3 or not cells[2].isdigit():
            continue
        rows.append((cells[0], tuple(re.findall(r"\b\d{3}\b", cells[1])), int(cells[2])))
    return tuple(rows)


def _ac026_items(root: Path) -> tuple[str, ...]:
    """`AC-AUTOPATCH-026` 절의 최상위 기대결과 항목 표지(①②…) 를 나온 순서대로."""
    text = _read(root, "acceptance.md")
    start = text.find("### AC-AUTOPATCH-026")
    assert start != -1, "acceptance.md 에서 AC-AUTOPATCH-026 절을 찾지 못했다."
    body = text[start:]
    end = _NEXT_HEADING_RE.search(body, 1)
    section = body[: end.start()] if end else body
    return tuple(match.group("mark") for match in _AC026_BULLET_RE.finditer(section))


# ======================================================================================
# 단정기 — 대조군이 그대로 재사용한다. 여기 없는 assert 는 대조군이 지키지 못한다.
# ======================================================================================


def _assert_documents_present(root: Path) -> None:
    for name in REQUIRED_DOCS:
        _read(root, name)


def _assert_cell_count(root: Path) -> None:
    cells = _round_count_cells(root)
    assert len(cells) == EXPECTED_CELL_COUNT, [name for name, _ in cells]


def _assert_cell_rule_agrees(root: Path) -> None:
    declared = _declared_cell_count(root)
    assert declared == EXPECTED_CELL_COUNT, (
        f"plan.md 규칙 문장은 셀이 {declared}개라 선언하는데 이 파일의 상수는 "
        f"{EXPECTED_CELL_COUNT}다. 셀을 늘렸다면 둘을 함께 올려라(round19 #1)."
    )


def _assert_cell_values_agree(root: Path) -> None:
    values = sorted({value for _, value in _round_count_cells(root)})
    assert len(values) == 1, f"라운드 계수 셀의 값이 갈라졌다: {values}"


def _assert_next_entry_carries_its_counters(root: Path) -> None:
    value = _next_entry(root)
    missing = [label for label, pattern in _NEXT_REQUIREMENTS if not pattern.search(value)]
    assert not missing, f"`next:` 가 필수 항목을 잃었다: {missing}"


def _assert_no_new_line_citations(root: Path) -> None:
    outside, _ = _line_citations(root)
    excess = {
        key: count for key, count in outside.items() if count > _FROZEN_LINE_CITATIONS.get(key, 0)
    }
    assert not excess, (
        f"활성 파일을 `파일:행`으로 새로 인용했다: {sorted(excess)}. "
        "round19 #1 심볼 규율 — 움직이는 대상은 좌표가 아니라 심볼명으로 가리킨다."
    )


def _assert_invariant_counts(root: Path) -> None:
    ac_ids = frozenset(_AC_ID_RE.findall(_read(root, "acceptance.md")))
    req_ids = frozenset(_REQ_ID_RE.findall(_read(root, "spec.md")))
    assert len(ac_ids) == EXPECTED_AC_COUNT, sorted(ac_ids)
    assert len(req_ids) == EXPECTED_REQ_COUNT, sorted(req_ids)

    rows = _c0a_rows(root)
    assert rows, "§C.0a 표에 데이터 행이 0건이다 — 아래 단정이 공허해진다."
    for milestone, ids, declared in rows:
        assert len(ids) == declared, (milestone, ids, declared)
    assigned = [item for _, ids, _ in rows for item in ids]
    assert len(assigned) == len(set(assigned)), f"§C.0a 배정에 중복이 있다: {sorted(assigned)}"
    assert sum(declared for _, _, declared in rows) == EXPECTED_AC_COUNT
    assert set(assigned) == set(ac_ids), sorted(set(assigned) ^ set(ac_ids))

    assert _ac026_items(root) == EXPECTED_AC026_ITEMS, _ac026_items(root)


# ======================================================================================
# 사본 하네스 — 대조군은 워킹트리를 건드리지 않는다.
# ======================================================================================


@pytest.fixture
def spec_copy(tmp_path: Path) -> Callable[[dict[str, Callable[[str], str]]], Path]:
    """SPEC 문서 사본을 만들고 지정한 파일만 변형해 뿌리를 돌려준다."""
    counter = itertools.count()

    def make(edits: dict[str, Callable[[str], str]]) -> Path:
        root = tmp_path / f"copy{next(counter)}"
        shutil.copytree(SPEC_DIR, root)
        for name, edit in edits.items():
            path = root / name
            path.write_text(edit(path.read_text(encoding="utf-8")), encoding="utf-8")
        return root

    return make


def _cell_token(value: object) -> str:
    """대조군이 심을 표지 토큰 — 완성형을 소스에 적지 않으려고 조립한다."""
    return f"[{_CELL_LABEL}={value}]"


def _edit_next_line(edit: Callable[[str], str]) -> Callable[[str], str]:
    def apply(text: str) -> str:
        return _NEXT_RE.sub(lambda match: "next:" + edit(match.group(1)), text, count=1)

    return apply


def _insert_after_heading(heading_prefix: str, payload: str) -> Callable[[str], str]:
    def apply(text: str) -> str:
        lines = text.splitlines(keepends=True)
        for index, line in enumerate(lines):
            if line.startswith("## " + heading_prefix):
                lines.insert(index + 1, payload + "\n")
                return "".join(lines)
        raise AssertionError(f"제목 `## {heading_prefix}` 를 찾지 못했다 — 대조군 불성립.")

    return apply


# ======================================================================================
# (0) 아티팩트 존재 — 없으면 skip이 아니라 실패
# ======================================================================================


def test_the_spec_documents_are_present_and_readable():
    """문서가 없는 환경에서 이 파일은 **조용히 넘어가지 않는다.**

    skip으로 두면 문서 삭제가 초록 결과를 내고, 그것이 바로 이 게이트가 막는 축소다.
    """
    _assert_documents_present(SPEC_DIR)


def test_a_missing_document_is_caught(spec_copy):
    """비공허성 — 아티팩트 하나를 지우면 위 단정이 실제로 실패한다."""
    root = spec_copy({})
    (root / "design.md").unlink()
    with pytest.raises(AssertionError):
        _assert_documents_present(root)


# ======================================================================================
# (가) 라운드 계수 셀
# ======================================================================================


def test_the_round_count_cells_are_neither_lost_nor_added_silently():
    """(가-1) 표지 토큰 개수가 규칙과 일치한다 — `R21-B`가 만든 8→7이 여기서 잡힌다."""
    _assert_cell_count(SPEC_DIR)


def test_the_rule_and_the_constant_declare_the_same_number_of_cells():
    """(가-2) [round19 #1] `plan.md` 규칙 문장의 선언과 이 파일의 상수가 일치한다.

    셀을 하나 늘리는 것은 개선이지 결함이 아니다 — 다만 규칙 문장과 상수를 **함께**
    올려야 통과한다. round19는 규칙이 「넷」이라 적는 동안 실제가 여덟이던 것을 잡았다.
    """
    _assert_cell_rule_agrees(SPEC_DIR)


def test_the_round_count_cells_all_carry_the_same_value():
    """(가-3) 값 불일치 탐지 — 둘째 grep이 두 줄을 내는 상태를 막는다.

    읽는 범위: `.moai/specs/SPEC-COPILOT-AUTOPATCH-001/**/*.md` 전부.
    """
    _assert_cell_values_agree(SPEC_DIR)


def test_deleting_one_round_count_cell_is_caught(spec_copy):
    """(가) 비공허성 — `R21-B`가 실제로 낸 조작(셀 하나 소실)을 재현하면 실패한다."""
    root = spec_copy({"progress.md": lambda text: _CELL_RE.sub("", text, count=1)})
    with pytest.raises(AssertionError):
        _assert_cell_count(root)


def test_a_stale_round_count_cell_is_caught(spec_copy):
    """(가) 비공허성 — 셀 하나만 stale로 남기면(값 불일치) 실패한다.

    `R21-B` 당시 실제 상태가 이것이었다: 남은 일곱이 전부 stale 값이었다.
    """
    root = spec_copy({"design.md": lambda text: _CELL_RE.sub(_cell_token(3), text, count=1)})
    _assert_cell_count(root)  # 개수 축은 이 조작을 못 잡는다 — 그래서 값 축이 따로 있다
    with pytest.raises(AssertionError):
        _assert_cell_values_agree(root)


def test_a_rule_that_undercounts_its_own_cells_is_caught(spec_copy):
    """(가) 비공허성 — round19 #1 재현. 규칙 문장만 「넷」으로 되돌리면 실패한다."""
    root = spec_copy({"plan.md": lambda text: _DECLARED_CELL_RE.sub("셀은 **넷**", text, count=1)})
    with pytest.raises(AssertionError):
        _assert_cell_rule_agrees(root)


# ======================================================================================
# (나) 프론트매터 `next:`
# ======================================================================================


def test_the_next_entry_carries_the_three_counters_it_has_lost_before():
    """(나) `next:` 가 라운드 계수 토큰 · 테스트 계수 · 커밋 계수를 지닌다.

    셋 다 실제로 잃어봤다 — 토큰은 `R21-B`, 테스트 계수는 round22 Docs, 커밋 계수는
    한 세션에 세 번. 그래서 셋을 각각 단정한다.
    """
    _assert_next_entry_carries_its_counters(SPEC_DIR)


@pytest.mark.parametrize(
    "label,mutate",
    [
        ("라운드 계수 셀 토큰", lambda value: _CELL_RE.sub("", value)),
        ("테스트 계수", lambda value: value.replace("passed", "")),
        ("커밋 계수", lambda value: re.sub(r"커밋.{0,30}?\d+", "", value)),
    ],
    ids=["cell-token", "test-count", "commit-count"],
)
def test_dropping_any_next_counter_is_caught(spec_copy, label, mutate):
    """(나) 비공허성 — 세 항목을 하나씩 지우면 **각각** 실패한다.

    셋을 한 단정에 접속사로 묶어 두면 하나가 죽어도 다른 둘이 살려 낸다. 항목별로
    대조군을 돌리는 것이 그 붕괴를 막는 유일한 방법이다.
    """
    root = spec_copy({"progress.md": _edit_next_line(mutate)})
    with pytest.raises(AssertionError, match=label.split("(")[0].strip()):
        _assert_next_entry_carries_its_counters(root)


# ======================================================================================
# (다) 활성 파일에 대한 `파일:행` 인용
# ======================================================================================


def test_no_new_line_citation_points_at_an_actively_edited_file():
    """(다) [round19 #1] 활성 파일은 `파일:행`이 아니라 심볼명으로 인용한다.

    동결 목록에 있는 기존 인용은 허용하되 **늘지 않는다**(줄어드는 것은 통과다).
    """
    _assert_no_new_line_citations(SPEC_DIR)


# **동결 목록에 「죽은 행」 게이트를 두지 않는 이유.** 인용 하나를 심볼로 고치면 그 행은
# 실재하지 않게 되는데, 그때 "목록도 함께 줄여라"를 강제하면 **개선이 실패로 나타난다** —
# 규율은 「축소만 허용」이지 「축소를 벌한다」가 아니다. 목록은 **상한**이며 상한이 실제보다
# 넓은 것은 무해하다(같은 좌표가 되살아나는 것뿐이고, 그것은 새 표류가 아니다).
# 판정기가 조용히 아무것도 못 찾게 되는 공허화는 아래 두 단정이 대신 막는다:
# 면제 건수 > 0, 그리고 심어 넣은 신규 인용이 실제로 잡히는 대조군.


def test_the_round_record_exemption_is_doing_real_work():
    """(다) §E.2* 라운드 기록 안에 실제로 면제되는 인용이 있다 — 면제가 공허하지 않다.

    면제 구역 판정이 깨지면(절 제목이 바뀌어 구역을 못 찾는 등) 면제 건수가 0이 되고,
    그러면 위 게이트는 "면제가 없어서 통과"하는 것과 구별되지 않는다.
    """
    _, exempt = _line_citations(SPEC_DIR)
    assert exempt > 0


def test_a_new_line_citation_outside_the_exempt_zones_is_caught(spec_copy):
    """(다) 비공허성 — §0에 활성 파일 좌표를 심으면 실패한다."""
    root = spec_copy(
        {"progress.md": _insert_after_heading("§0", "보라 `server/vwx/typemap.py:42` 를.")}
    )
    with pytest.raises(AssertionError):
        _assert_no_new_line_citations(root)


def test_fixing_a_citation_into_a_symbol_reference_still_passes(spec_copy):
    """(다) 규율의 **정방향**을 고정한다 — 좌표를 심볼로 고치면 통과해야 한다.

    동결 목록은 상한이지 등가물이 아니다. 이 단정이 없으면 나중에 누군가 위 비교를
    `outside == _FROZEN_LINE_CITATIONS` 같은 등가 비교로 바꿔도 아무도 모르고, 그러면
    **규율을 지키는 수정이 실패로 나타나는** 게이트가 된다(round22가 이름 붙인
    「역방향 대조군」이 정확히 그 형태다).
    """
    fixed = ("progress.md", "apply.py:127")
    root = spec_copy(
        {"progress.md": lambda text: text.replace("`apply.py:127`", "`apply.HandoffEntry`")}
    )
    before, _ = _line_citations(SPEC_DIR)
    after, _ = _line_citations(root)
    assert fixed in before and fixed not in after, "조작이 헛돌았다 — 이 대조군이 공허하다"
    _assert_no_new_line_citations(root)


def test_a_new_line_citation_inside_a_round_record_is_deliberately_not_caught(spec_copy):
    """(다) 면제의 **반대쪽**을 실측한다 — §E.2 안에 같은 좌표를 심으면 잡히지 않는다.

    이것은 결함이 아니라 설계다(위 `_is_exempt` 참조). 다만 그 대가를 여기 적어 둔다:
    **라운드 기록 안에서는 이 규율이 강제되지 않는다.** 같은 조작이 §0에서는 잡히고
    §E.2에서는 잡히지 않는다는 사실 자체를 고정해, 면제 구역이 조용히 넓어지면
    (예: `§E.2` 접두를 다른 절에 붙이면) 위 대조군이 대신 깨지게 한다.
    """
    root = spec_copy(
        {"progress.md": _insert_after_heading("§E.2 ", "보라 `server/vwx/typemap.py:42` 를.")}
    )
    _, before = _line_citations(SPEC_DIR)
    _, after = _line_citations(root)
    assert after == before + 1, "심은 좌표가 인용으로 판독되지 않았다 — 이 대조군이 공허하다"
    _assert_no_new_line_citations(root)


# ======================================================================================
# (라) 불변식 계수
# ======================================================================================


def test_the_invariant_counts_hold():
    """(라) AC 27 · REQ 26 · §C.0a 합 27(행별 배정과 1:1) · AC-026 ①~⑦.

    읽는 범위: `acceptance.md` 와 `spec.md` 두 아티팩트뿐이다.
    """
    _assert_invariant_counts(SPEC_DIR)


@pytest.mark.parametrize(
    "name,mutate",
    [
        ("acceptance.md", lambda t: t.replace("AC-AUTOPATCH-027", "AC-AUTOPATCH-026")),
        ("spec.md", lambda t: t.replace("REQ-AUTOPATCH-026", "REQ-AUTOPATCH-025")),
        ("acceptance.md", lambda t: t.replace("· 008 · 027 | 5 |", "· 008 · 027 | 4 |")),
        ("acceptance.md", lambda t: t.replace("· 008 · 027 | 5 |", "· 008 | 5 |")),
        ("acceptance.md", lambda t: re.sub(r"\n {2}- ⑦[^\n]*", "", t)),
    ],
    ids=["ac-27", "req-26", "c0a-declared", "c0a-row-ids", "ac026-items"],
)
def test_breaking_any_invariant_count_is_caught(spec_copy, name, mutate):
    """(라) 비공허성 — 네 축을 하나씩 깨뜨리면 실패한다.

    `c0a-declared`(선언 수만 바꿈)와 `c0a-row-ids`(행에서 AC 하나 삭제)를 나눈 것은
    round22 Docs 프로브 ⓓ 때문이다 — 표에서 **행 내용**을 지우는 조작을 계수 축이
    못 잡는다는 실증이었다. §C.0a 만큼은 행별 1:1까지 본다.
    """
    root = spec_copy({name: mutate})
    with pytest.raises(AssertionError):
        _assert_invariant_counts(root)
