"""t243 — 대상 열을 싣는 시트가 상수 그룹 발사 경로로 들어오면 **소리가 나게** 한다.

이 파일은 **오늘 무엇을 막지 않는다.** 오늘은 막을 것이 없다 — bm 은 표에도 분기에도
없어서 `_lxseq_preset_apply_command` 가 `None` 을 내고 호출지가 저장 줄도 안 낸다.
**fail-closed 는 이미 그 자리에 있고, 이 카드는 그것을 복제하지 않는다.**

막는 것은 **미래의 한 순간**이다: 누군가 bm 을 열려고 `LXSEQ_PRESET_APPLY_ATTRIBUTE`
에 항목을 더하거나 `_lxseq_preset_apply_command` 에 분기를 더하는 그 순간, 기존
fail-closed 가 **사라지고** 명령이 상수 그룹으로 나간다. 시트는 `MOVER-ALL`(16대)을
적었는데 명령은 `ALL`(86대 중 그 속성을 가진 전부)로 간다 — t241 이 실측으로 확정한
자리이고, 값은 되읽을 수 없어 조용히 틀린다(t108 C1 계열).

🔴 **비대칭은 원리적이다.**

    대상 열이 **없는** 시트(dim·col)  ->  상수 그룹이 **옳다** (시트가 대상을 말한 적 없다)
    대상 열을 **싣는** 시트(bm)       ->  상수 그룹이 **틀리다** (시트가 다른 대상을 말했다)

「dim 은 왜 안 막나」의 답은 「dim 시트는 대상을 말한 적이 없다」이지 예외 처리가 아니다.

순수 검증이다. 콘솔·네트워크 접촉 0.
"""

from __future__ import annotations

from pathlib import Path

from server.lxseq.preset_parser import PRESET_SHEET_COLUMNS
from server.orchestrator.tools import (
    LXSEQ_PRESET_APPLY_ATTRIBUTE,
    LXSEQ_PRESET_APPLY_GROUP_NO,
)

TOOLS = Path("server/orchestrator/tools.py")
RIG = Path("src/Lighting_Designer/02_RIG팩")
STEM = "LXSEQ_RIG_01_ShowBase_r3.preset-"

#: 대상 열의 열 이름. 시트가 이 이름을 바꾸면 이 파일의 전제가 사라진다.
TARGET_COLUMN = "TargetGroup"


def _target_bearing_kinds() -> tuple[str, ...]:
    """시트가 **대상을 말하는** 종류. 파서의 헤더 표 하나에서만 읽는다."""
    return tuple(kind for kind, columns in PRESET_SHEET_COLUMNS.items() if TARGET_COLUMN in columns)


def _apply_command_source() -> str:
    """`_lxseq_preset_apply_command` 의 본문만. 파일 전체를 훑으면 검사가 약해진다."""
    source = TOOLS.read_text(encoding="utf-8")
    anchor = "def _lxseq_preset_apply_command("
    assert anchor in source, "함수 이름이 바뀌었다 — 앵커를 같이 옮겨라"
    body = source.split(anchor, 1)[1]
    return body.split("\ndef ", 1)[0]


class TestTheInstrumentIsNotBlind:
    """계기 점검이 먼저다 — 아래 「없다」들이 무엇에 대한 없음인지 고정한다."""

    def test_exactly_one_parsed_kind_carries_a_target_column(self):
        assert _target_bearing_kinds() == ("preset-bm",)

    def test_the_other_kinds_really_do_not_carry_it(self):
        """대조군 — 전부 싣거나 전부 안 실으면 이 파일의 비대칭이 사라진다."""
        without = tuple(k for k in PRESET_SHEET_COLUMNS if k not in _target_bearing_kinds())
        assert sorted(without) == ["preset-col", "preset-dim"]

    def test_the_sheets_on_disk_agree_with_the_header_table(self):
        """표가 아니라 **정본 시트**를 열어 대조한다 — 표만 보면 표가 낡아도 모른다."""
        for kind, columns in PRESET_SHEET_COLUMNS.items():
            header = (
                (RIG / (STEM + kind.removeprefix("preset-") + ".csv"))
                .read_text(encoding="utf-8-sig")
                .splitlines()[0]
            )
            assert (TARGET_COLUMN in header.split(",")) == (TARGET_COLUMN in columns), kind

    def test_the_body_scanner_finds_a_branch_that_is_really_there(self):
        """소스 스캔이 눈멀지 않았다는 것 — col 분기는 실재한다."""
        assert 'placement.kind == "preset-col"' in _apply_command_source()


class TestNoTargetBearingKindMayUseTheConstantGroup:
    """🔴 이 파일의 이유. 둘 다 빨개져야 그 순간에 소리가 난다."""

    def test_the_apply_attribute_table_holds_no_target_bearing_kind(self):
        for kind in _target_bearing_kinds():
            assert kind not in LXSEQ_PRESET_APPLY_ATTRIBUTE, (
                kind
                + " 은 시트에 "
                + TARGET_COLUMN
                + " 을 싣는다. 이 표에 넣으면 명령이 행의 대상이 아니라 상수 그룹 "
                + str(LXSEQ_PRESET_APPLY_GROUP_NO)
                + " 로 나가고, 값은 되읽을 수 없어 조용히 틀린다(t241). "
                + "행의 대상을 쓰는 경로를 먼저 만들어라 — t244 소유다."
            )

    def test_the_apply_command_has_no_branch_for_a_target_bearing_kind(self):
        body = _apply_command_source()
        for kind in _target_bearing_kinds():
            assert 'placement.kind == "' + kind + '"' not in body, (
                kind + " 분기가 생겼다 — 위 검사와 같은 이유로 막는다"
            )

    def test_the_control_is_that_a_kind_without_a_target_column_is_allowed_in(self):
        """대조군 — 「표가 비었다」로 통과하는 것이 아니다. dim 은 실제로 들어 있다."""
        assert "preset-dim" in LXSEQ_PRESET_APPLY_ATTRIBUTE
        assert "preset-dim" not in _target_bearing_kinds()


class TestTodaysFailClosedIsNotDuplicated:
    """이미 있는 방어를 복제하지 않았다는 것 — 그리고 그것이 **오늘만** 참이라는 것."""

    def test_beam_has_no_apply_command_today(self):
        from types import SimpleNamespace

        from server.orchestrator.tools import _lxseq_preset_apply_command

        placement = SimpleNamespace(kind="preset-bm", value_raw="Zoom 45°")
        assert _lxseq_preset_apply_command(placement) is None

    def test_and_dim_does_have_one(self):
        from types import SimpleNamespace

        from server.orchestrator.tools import _lxseq_preset_apply_command

        placement = SimpleNamespace(kind="preset-dim", value_raw="85%")
        assert _lxseq_preset_apply_command(placement) is not None

    def test_the_constant_carries_the_rule_in_prose(self):
        """상수 옆 문장이 사라지면 다음 사람이 이 검사를 「왜 있는지」 모른다."""
        source = TOOLS.read_text(encoding="utf-8")
        anchor = "LXSEQ_PRESET_APPLY_GROUP_NO = 1"
        assert anchor in source
        block = source.split(anchor)[0]
        assert "대상 열을 싣는 시트 종류는 이 상수를 쓰면 안 된다" in block
        assert "fail-closed 는 이미 그 자리에 있다" in block
