"""t135 — bm 시트 어휘와 콘솔 프로브 어휘는 **다른 것**이다 (SPEC-COPILOT-LXSEQ-003).

이 파일은 **뒤집힌 전제 뒤에** 쓰였다. 카드는 「파서의 속성 철자가 콘솔 실제
채널명과 달라 고쳐야 한다」였는데, 재보니 고치면 **회귀**였다.

    schema.py:16 문면   콘솔에 **쏜** 문자열          Focus / Frost / Prism1 / Shutter
    _PROBE_REJECTED     감독 **시트에 적힌** 토큰      Focus / Frost / Prism  / Shutter

정본 문면에 맞춰 `Prism1` 로 바꾸면 술어가 시트 토큰 `Prism` 에 안 걸려
**BM.03 이 열린다** — 그리고 그 속성은 프로브가 `Failed` 를 낸 바로 그것이다
(`SPEC-COPILOT-LOOKLIB-001/progress.md:157-164`).

BM.03 은 이 카드 전에는 **어느 검사도 안 잡고 있었다.** 핀은 BM.01 하나뿐이었고,
BM.01 은 Gobo(범위 밖)에도 막혀 있어 프리즘 사유가 사라져도 여전히 보류로 보인다.
**사유가 둘인 행은 사유 하나가 사라지는 것을 못 보여준다** — 그래서 사유가 하나뿐인
BM.03 이 이 술어의 유일한 관측 창이다.

순수 함수 검증이다. 콘솔·네트워크 접촉 0.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.lxseq import preset_parser as parser_module
from server.lxseq.preset_parser import HOLD_PROBE_REJECTED, parse_preset_csv

RIG = Path("src/Lighting_Designer/02_RIG팩")
BM = RIG / "LXSEQ_RIG_01_ShowBase_r3.preset-bm.csv"

#: 정본 문면(`schema.py:16`)이 적는 **콘솔에 쏜** 문자열. 시트 토큰이 아니다.
PROBED_STRINGS = ("Focus", "Frost", "Prism1", "Shutter")


def _records():
    return parse_preset_csv(BM.read_text(encoding="utf-8-sig")).records


def _by_id():
    return dict((r.preset_id, r) for r in _records())


class TestTheSheetVocabularyIsWhatMatches:
    def test_the_two_vocabularies_differ_in_exactly_one_name(self):
        """비공허성 — 차이가 하나뿐이라는 것이 이 카드의 관측이다.

        차이가 사라지면(누군가 「정합성」을 이유로 맞춰 버리면) 아래 검사들이
        무엇을 지키는지 읽히지 않는다.
        """
        sheet = parser_module._PROBE_REJECTED
        assert len(sheet) == len(PROBED_STRINGS)
        differing = [(a, b) for a, b in zip(sheet, PROBED_STRINGS, strict=True) if a != b]
        assert differing == [("Prism", "Prism1")]

    def test_the_sheet_actually_writes_the_shorter_token(self):
        """술어가 시트 어휘여야 하는 근거 — 시트 원문에 `Prism1` 은 없다."""
        text = BM.read_text(encoding="utf-8-sig")
        assert "Prism " in text or "Prism3" in text or "Prism·" in text
        assert "Prism1" not in text


class TestTheProbeRejectedRowsStayHeld:
    def test_bm03_is_held_by_the_probe_reason_alone(self):
        """🔴 이 행이 이 술어의 유일한 관측 창이다 — 사유가 하나뿐이다."""
        record = _by_id()["BM.03"]
        assert record.storable is False
        assert record.hold_classes == (HOLD_PROBE_REJECTED,)

    def test_bm04_is_held_by_the_probe_reason_alone_too(self):
        """대조군 — `Frost` 쪽은 두 어휘가 같다. 같은 자리에서 같이 막혀야 한다."""
        record = _by_id()["BM.04"]
        assert record.storable is False
        assert record.hold_classes == (HOLD_PROBE_REJECTED,)

    def test_no_beam_row_is_storable(self):
        assert not [r for r in _records() if r.storable]


class TestMatchingTheCanonicalProseWouldOpenARejectedRow:
    """치환을 **실제로 해서** 잰다. 「그럴 것이다」로 적으면 다음 사람이 확인 못 한다."""

    def test_substituting_prism1_opens_bm03(self, monkeypatch):
        monkeypatch.setattr(parser_module, "_PROBE_REJECTED", PROBED_STRINGS)
        opened = [r for r in _records() if r.storable]
        assert [r.preset_id for r in opened] == ["BM.03"]

    def test_substituting_prism1_also_strips_one_reason_from_bm01(self, monkeypatch):
        """BM.01 은 Gobo 에도 막혀 **보류로 남는다** — 그래서 BM.01 만 보면
        이 회귀가 안 보인다. 그 눈먼 자리를 검사로 적어 둔다."""
        monkeypatch.setattr(parser_module, "_PROBE_REJECTED", PROBED_STRINGS)
        record = _by_id()["BM.01"]
        assert record.storable is False
        assert HOLD_PROBE_REJECTED not in record.hold_classes

    def test_the_control_is_that_nothing_opens_without_the_substitution(self):
        """대조군 — 치환 없이도 열리면 위 두 검사는 치환을 재는 게 아니다."""
        assert not [r for r in _records() if r.storable]


class TestTheProbeEvidenceIsBoundedNotExhaustive:
    """정본 실측표가 스스로 단 한정 — 주석이 그보다 세게 말하지 않도록 고정한다."""

    def test_the_parser_comment_does_not_claim_the_syntax_is_invalid(self):
        source = Path("server/lxseq/preset_parser.py").read_text(encoding="utf-8")
        block = source.split("_PROBE_REJECTED = (")[0]
        assert "전수 확정으로도" in block, "한정 문장이 사라졌다"
        assert "관측되지 않았다" in block, "Failed 차이의 미관측이 사라졌다"

    def test_the_canonical_measurement_still_records_the_two_readings(self):
        """정본이 그 한정을 지우면 위 주석의 근거가 사라진다 — 같이 잰다."""
        canonical = Path(".moai/specs/SPEC-COPILOT-LOOKLIB-001/progress.md")
        if not canonical.exists():  # pragma: no cover - 정본이 옮겨간 경우
            pytest.skip("정본 progress.md 가 이 경로에 없다")
        text = canonical.read_text(encoding="utf-8")
        assert "Illegal object" in text
        assert "속성을 실제로 보유하는지는 확립되지 않았다" in text
        assert "Failed" in text


class TestThePrefixMatchIsDirectional:
    """이 카드 전체의 기전 — `_attribute_tokens` 는 **접두 일치**다.

    판독기는 원문 토큰을 돌려주지 않고, 아는 이름 중 **토큰이 그것으로 시작하는
    것**을 돌려준다(`token.lower().startswith(known.lower())`). 방향이 있다:

        토큰 `Prism1`  vs  아는 이름 `Prism`   -> 걸린다   (Prism1 이 Prism 으로 시작)
        토큰 `Prism`   vs  아는 이름 `Prism1`  -> 안 걸린다 (Prism 은 Prism1 로 시작 안 함)

    그래서 목록에 **짧은 쪽**(`Prism`)을 두면 시트가 어느 철자를 쓰든 걸리고,
    **긴 쪽**(`Prism1`)을 두면 시트의 `Prism` 이 빠져나간다. 카드가 하려던 치환이
    회귀인 이유가 이 비대칭이다 — 철자 취향 문제가 아니다.
    """

    def test_the_longer_sheet_spelling_still_matches_the_shorter_entry(self):
        assert parser_module._attribute_tokens("Prism1 ON") == ["Prism"]
        storable, _reasons = parser_module.classify_storability("preset-bm", "Prism1 ON")
        assert storable is False

    def test_but_the_shorter_spelling_would_not_match_a_longer_entry(self, monkeypatch):
        """반대 방향을 실제로 쏜다 — 이것이 BM.03 이 열리는 기전 그 자체다."""
        monkeypatch.setattr(parser_module, "_PROBE_REJECTED", PROBED_STRINGS)
        assert parser_module._attribute_tokens("Prism 3-facet ON") == []
        storable, reasons = parser_module.classify_storability("preset-bm", "Prism 3-facet ON")
        assert storable is True
        assert reasons == ()

    def test_the_control_is_the_current_list(self):
        """대조군 — 치환 없이는 같은 값이 막힌다."""
        storable, reasons = parser_module.classify_storability("preset-bm", "Prism 3-facet ON")
        assert storable is False
        assert HOLD_PROBE_REJECTED in [r.hold_class for r in reasons]
