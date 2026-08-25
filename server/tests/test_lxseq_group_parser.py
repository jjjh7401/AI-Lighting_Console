"""SPEC-COPILOT-LXSEQ-002 M1 — GROUP 시트 파서 (RED 먼저).

AC-LXSEQ2-002  헤더는 이름으로 매칭한다. BOM 흡수. 4열 누락은 파일 단위 실패.
AC-LXSEQ2-003  행 검증 실패는 예외가 아니라 닫힌 5부류 거부다.
AC-LXSEQ2-004  Members 열은 멤버십 판정에 쓰지 않는다 — 원문 보존만.

순수 함수 검증이다. 콘솔·네트워크 접촉 0.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.lxseq.group_parser import (
    CANONICAL_GROUP_COLUMNS,
    GROUP_SLOT_CEILING,
    MissingGroupColumnsError,
    parse_group_csv,
)

FIXTURE = Path("server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.group.csv")

# 정본 사본이 계약이다 (plan.md 결정 S). 여기서 읽고, 변형은 메모리에서 한다.
_CANONICAL_SHA256 = "bc7aced27b0bc06938f2aed2b52c2cff8e2e6ec362ceac154694d5ef64af0172"


def _canonical_text() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def _rows(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]


def _rebuild(header: str, body: list[str]) -> str:
    return "\n".join([header, *body]) + "\n"


def test_fixture_contract_holds():
    """사본이 계약대로인지 먼저 잰다 — 이 테스트가 죽으면 아래 전부가 무의미하다."""
    import hashlib

    raw = FIXTURE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == _CANONICAL_SHA256
    lines = _rows(raw.decode("utf-8"))
    assert len(lines) == 19, "헤더 1 + 데이터 18"


class TestHeaderAndShape:
    """AC-LXSEQ2-002."""

    def test_bom_is_absorbed_and_first_column_resolves(self):
        text = _canonical_text()
        assert text.startswith("\ufeff"), "정본에 BOM 이 있어야 이 검사가 공허하지 않다"
        result = parse_group_csv(text)
        assert len(result.records) == 18
        assert result.records[0].group_no == 1
        assert result.records[0].name == "ALL"

    def test_columns_are_matched_by_name_not_position(self):
        """열 순서를 섞어도 같은 18개 레코드가 나와야 한다."""
        lines = _rows(_canonical_text().lstrip("\ufeff"))
        header, body = lines[0], lines[1:]

        def shuffle(line: str) -> str:
            a, b, c, d = line.split(",", 3)
            return ",".join([d, b, a, c])

        shuffled = _rebuild(shuffle(header), [shuffle(row) for row in body])
        result = parse_group_csv(shuffled)
        straight = parse_group_csv(_canonical_text())
        assert [r.group_no for r in result.records] == [r.group_no for r in straight.records]
        assert [r.name for r in result.records] == [r.name for r in straight.records]

    @pytest.mark.parametrize("dropped", CANONICAL_GROUP_COLUMNS)
    def test_any_missing_column_fails_the_whole_file(self, dropped: str):
        lines = _rows(_canonical_text().lstrip("\ufeff"))
        header_cells = lines[0].split(",")
        keep = [i for i, cell in enumerate(header_cells) if cell != dropped]
        assert len(keep) == 3, "정확히 한 열만 빠져야 한다"

        def prune(line: str) -> str:
            cells = line.split(",", 3)
            return ",".join(cells[i] for i in keep)

        pruned = _rebuild(prune(lines[0]), [prune(row) for row in lines[1:]])
        with pytest.raises(MissingGroupColumnsError) as caught:
            parse_group_csv(pruned)
        assert dropped in caught.value.missing


class TestRowRejection:
    """AC-LXSEQ2-003 — 닫힌 5부류. 예외는 새어나가지 않는다."""

    def _with_row(self, replacement: str, target_no: str = "5") -> str:
        lines = _rows(_canonical_text().lstrip("\ufeff"))
        header, body = lines[0], lines[1:]
        out = []
        for row in body:
            out.append(replacement if row.split(",", 1)[0] == target_no else row)
        return _rebuild(header, out)

    def test_groupno_not_int(self):
        result = parse_group_csv(self._with_row("five,SIDE-L,SIDE-L 6대,하수 사이드"))
        kinds = [r.kind for r in result.rejected]
        assert kinds == ["groupno_not_int"]
        assert len(result.records) == 17, "나머지 17행은 살아야 한다 (비공허성)"

    def test_groupno_out_of_range_low(self):
        result = parse_group_csv(self._with_row("0,SIDE-L,SIDE-L 6대,하수 사이드"))
        assert [r.kind for r in result.rejected] == ["groupno_out_of_range"]

    def test_groupno_out_of_range_high(self):
        over = str(GROUP_SLOT_CEILING + 1)
        result = parse_group_csv(self._with_row(f"{over},SIDE-L,SIDE-L 6대,하수 사이드"))
        assert [r.kind for r in result.rejected] == ["groupno_out_of_range"]

    def test_group_slot_ceiling_itself_is_accepted(self):
        """경계는 통과해야 한다 — 상한 자체를 거부하면 경계가 하나 밀린다."""
        result = parse_group_csv(
            self._with_row(f"{GROUP_SLOT_CEILING},SIDE-L,SIDE-L 6대,하수 사이드")
        )
        assert result.rejected == ()
        assert any(r.group_no == GROUP_SLOT_CEILING for r in result.records)

    def test_groupno_duplicate(self):
        """5번을 4번으로 바꾸면 둘째 4번이 거부된다."""
        result = parse_group_csv(self._with_row("4,SIDE-L,SIDE-L 6대,하수 사이드"))
        assert [r.kind for r in result.rejected] == ["groupno_duplicate"]
        assert len(result.records) == 17

    def test_name_empty(self):
        result = parse_group_csv(self._with_row("5,,SIDE-L 6대,하수 사이드"))
        assert [r.kind for r in result.rejected] == ["name_empty"]

    @pytest.mark.parametrize("quoted", ["SIDE'L", 'SIDE"L'])
    def test_name_has_quote(self, quoted: str):
        """따옴표는 _label_command 가 터뜨리기 전에 행 단위로 걸러야 한다.

        server/groupgen/write.py 의 `_label_command` 는 작은따옴표·큰따옴표를
        각각 ValueError 로 거부한다. 그게 툴 계층에서 터지면 배치 전체가
        죽으므로, 파서가 그 행 하나만 떨어뜨린다.
        """
        result = parse_group_csv(self._with_row(f"5,{quoted},SIDE-L 6대,하수 사이드"))
        assert [r.kind for r in result.rejected] == ["name_has_quote"]
        assert len(result.records) == 17

    def test_no_exception_escapes_on_any_rejection(self):
        """다섯 부류를 한꺼번에 심어도 예외가 안 난다."""
        lines = _rows(_canonical_text().lstrip("\ufeff"))
        header = lines[0]
        body = [
            "five,ALL,전 픽스처,글로벌",
            "0,KEY,KEY 6대,인물광",
            "3,FOH,FOH 8대,전면 워시",
            "3,BACK,BACK 12대,실루엣",
            "5,,SIDE-L 6대,하수 사이드",
            "6,SIDE'R,SIDE-R 6대,상수 사이드",
        ]
        result = parse_group_csv(_rebuild(header, body))
        assert [r.kind for r in result.rejected] == [
            "groupno_not_int",
            "groupno_out_of_range",
            "groupno_duplicate",
            "name_empty",
            "name_has_quote",
        ]
        assert len(result.records) == 1, "FOH 한 행만 살아남는다 (비공허성)"


class TestMembersIsNotInterpreted:
    """AC-LXSEQ2-004 — Members 는 판정에 안 쓴다. 원문 보존만."""

    def test_records_survive_when_members_is_blanked(self):
        """Members 를 전부 비워도 18개 레코드가 그대로 나온다."""
        lines = _rows(_canonical_text().lstrip("\ufeff"))
        header = lines[0]
        body = []
        for row in lines[1:]:
            no, name, _members, purpose = row.split(",", 3)
            body.append(",".join([no, name, "", purpose]))
        result = parse_group_csv(_rebuild(header, body))
        assert len(result.records) == 18
        assert result.rejected == ()
        assert all(r.members_raw == "" for r in result.records)

    def test_members_is_preserved_verbatim(self):
        """네 문법이 전부 원문 그대로 남는다 — 정규화도 파싱도 하지 않는다."""
        result = parse_group_csv(_canonical_text())
        by_name = {r.name: r.members_raw for r in result.records}
        assert by_name["KEY"] == "KEY 6대"
        assert by_name["SIDE-ALL"] == "SIDE-L + SIDE-R"
        assert by_name["ALL"] == "전 픽스처 (FOLLOW 제외)"
        assert by_name["ODD"] == "MOVER-ALL 홀수 FID"

    def test_nonsense_members_does_not_reject_the_row(self):
        """해석 불가한 Members 도 행을 떨어뜨리지 않는다.

        해석하지 않으니 해석 실패라는 것이 존재할 수 없다. 이 검사가
        빨개지면 파서가 Members 를 읽고 있다는 뜻이다.
        """
        lines = _rows(_canonical_text().lstrip("\ufeff"))
        header = lines[0]
        body = []
        for row in lines[1:]:
            no, name, _members, purpose = row.split(",", 3)
            body.append(",".join([no, name, "!!! 해석 불가 !!!", purpose]))
        result = parse_group_csv(_rebuild(header, body))
        assert len(result.records) == 18
        assert result.rejected == ()


class TestPurityBoundary:
    """server/lxseq/ 는 콘솔을 모른다 — 파서 모듈에 쓰기 수단이 0건이다."""

    FORBIDDEN = ("run_commands", "deploy_pipeline", "execution_port", "state_port", "socket")

    @staticmethod
    def _identifiers(source: str) -> set[str]:
        import ast

        found: set[str] = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Name):
                found.add(node.id)
            elif isinstance(node, ast.Attribute):
                found.add(node.attr)
            elif isinstance(node, ast.alias):
                found.add(node.name.split(".")[0])
                if node.asname:
                    found.add(node.asname)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                found.add(node.name)
        return found

    def test_scanner_finds_a_planted_write_surface(self):
        """날조 대조군 — 스캐너가 실제로 찾는지 먼저 증명한다.

        이걸 안 쏘면 아래 0건이 「없다」인지 「스캐너가 못 본다」인지 못 가른다.
        이 저장소가 이미 여러 번 밟은 형태다. 다섯 금지어를 **각각** 심어
        각 형태(호출·속성·임포트)가 잡히는지 본다.
        """
        planted = "\n".join(
            [
                "from server.bridge import run_commands",
                "def go(port):",
                "    run_commands(['ClearAll'])",
                "    port.deploy_pipeline.deploy()",
                "    port.execution_port.fire()",
                "    port.state_port.read()",
                "    import socket",
            ]
        )
        names = self._identifiers(planted)
        missed = [f for f in self.FORBIDDEN if f not in names]
        assert missed == [], f"스캐너가 못 보는 금지어: {missed}"

    def test_parser_module_names_no_write_surface(self):
        source = Path("server/lxseq/group_parser.py").read_text(encoding="utf-8")
        names = self._identifiers(source)
        assert [f for f in self.FORBIDDEN if f in names] == []
        # 같은 스캐너가 이 파일 안의 실재 식별자는 본다 — 빈 집합을 0건으로 읽지 않기 위해.
        assert "parse_group_csv" in names
        assert "MissingGroupColumnsError" in names


class TestLabelCommandEquivalence:
    """파서의 금지 문자 집합이 `_label_command` 의 거부 집합과 같은가.

    `server/groupgen/write.py` 의 `_label_command` 는 이름에 따옴표가 있으면
    ValueError 를 던지고, 그 예외는 **배치 전체**를 죽인다. 파서가 먼저
    걸러야 그 행 하나만 떨어진다. 두 집합이 어긋나면 파서를 통과한 이름이
    툴 계층에서 터진다.

    집합을 여기 다시 적지 않고 **실제로 탐침해서** 잰다 — 적어 두면 그건
    같은 주장을 두 번 쓰는 것이지 두 집합을 대조한 것이 아니다.
    `server/lxseq/` 는 `server/groupgen/` 을 임포트하지 않는다(층 경계).
    테스트만 양쪽을 임포트한다 — write.py 의 @MX:ANCHOR 가 정한 방식이다.
    """

    # 탐침 우주. 여기 없는 문자에 대해서는 이 검사가 아무 말도 하지 않는다.
    PROBE = "".join(chr(c) for c in range(33, 127)) + "한글 ·—"

    def test_the_two_forbidden_sets_are_equal(self):
        from server.groupgen.write import _label_command
        from server.lxseq.group_parser import _FORBIDDEN_NAME_CHARS

        rejected_by_label = set()
        for ch in self.PROBE:
            try:
                _label_command(7, "G" + ch + "X")
            except ValueError:
                rejected_by_label.add(ch)

        assert rejected_by_label == set(_FORBIDDEN_NAME_CHARS), (
            "파서가 거르는 문자와 Label 조립이 거부하는 문자가 다르다 — "
            f"label={sorted(rejected_by_label)} parser={sorted(_FORBIDDEN_NAME_CHARS)}"
        )
        # 비공허성 — 탐침이 실제로 무언가를 걸렀는가.
        assert rejected_by_label, "탐침이 아무것도 못 걸렀다면 이 대조는 공허하다"

    def test_a_clean_name_assembles(self):
        """양성 대조군 — 거부만 보고 통과를 안 보면 절반만 잰 것이다."""
        from server.groupgen.write import _label_command

        assert _label_command(7, "MOVER-ALL") == "Label Group 7 'MOVER-ALL'"

    def test_every_canonical_group_name_survives_label_assembly(self):
        """정본 18개 이름이 전부 Label 로 조립된다."""
        from server.groupgen.write import _label_command

        result = parse_group_csv(_canonical_text())
        assert len(result.records) == 18
        for record in result.records:
            assert _label_command(record.group_no, record.name).startswith("Label Group ")
