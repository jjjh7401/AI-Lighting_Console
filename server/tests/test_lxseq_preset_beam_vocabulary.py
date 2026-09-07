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
from server.lxseq.preset_parser import (
    HOLD_ATTRIBUTE_UNKNOWN,
    HOLD_PROBE_REJECTED,
    parse_preset_csv,
)

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
        # t141 이 선언을 `= tuple(...)` 파생으로 바꿨다. 앵커를 안 따라가면 split 이
        # 아무것도 못 잘라 **파일 전체**를 훑고, 그러면 이 검사가 「주석 블록에 있다」가
        # 아니라 「파일 어딘가에 있다」를 재게 된다 — 조용히 약해지는 자리다.
        anchor = "_PROBE_REJECTED = tuple("
        assert anchor in source, "선언 형태가 또 바뀌었다 — 앵커를 같이 옮겨라"
        block = source.split(anchor)[0]
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


def _stale_holds(accepted, mapping, rejected) -> tuple[str, ...]:
    """보류 사유가 **거짓이 된** 항목.

    콘솔 이름이 수용 어휘에 들어갔는데 그 시트 토큰이 아직 보류 목록에 있으면,
    그 행의 사유 문면("라이브 프로브가 거절한 속성")은 더 이상 참이 아니다.
    """
    return tuple(
        token
        for token, console_name in mapping.items()
        if console_name in accepted and token in rejected
    )


def _widened_with(name: str) -> frozenset:
    """콘솔 어휘가 그 이름만큼 넓어진 세계. t149 가 오는 날의 모양이다."""
    return frozenset(parser_module._ACCEPTED_ATTRIBUTES).union([name])


class TestTheMappingIsTheOnlyJoinBetweenTheTwoVocabularies:
    """t141 — 두 어휘의 연결을 산문이 아니라 **데이터**로 둔 자리."""

    def test_the_derived_tuple_is_byte_identical_to_the_hand_written_one(self):
        """파생으로 바꾸면서 동작이 안 바뀌었다는 것을 다음 사람이 검산하는 자리."""
        assert parser_module._PROBE_REJECTED == ("Focus", "Frost", "Prism", "Shutter")
        assert tuple(parser_module._SHEET_TO_CONSOLE_ATTRIBUTE) == parser_module._PROBE_REJECTED

    def test_every_console_name_is_strictly_longer_than_its_sheet_token(self):
        """방향 불변식 — 콘솔 이름이 시트 토큰보다 길다.

        이 부등호가 뒤집히면 「짧은 쪽을 목록에 둔다」는 규칙의 전제가 사라진다.
        """
        for token, console_name in parser_module._SHEET_TO_CONSOLE_ATTRIBUTE.items():
            assert console_name.startswith(token), (token, console_name)
            assert len(console_name) > len(token), (token, console_name)

    def test_a_console_name_in_the_list_would_stop_matching_its_own_sheet_token(self):
        """「그냥 맞추면 되잖아」가 닫히는 자리 — 술어를 실제로 돌려서 잰다."""
        for token, console_name in parser_module._SHEET_TO_CONSOLE_ATTRIBUTE.items():
            assert token.lower().startswith(token.lower())
            assert not token.lower().startswith(console_name.lower()), (token, console_name)


class TestTheStaleHoldTripwire:
    """콘솔 어휘가 넓어지는 날(t149) 보류 사유가 조용히 거짓이 되는 것을 잡는다.

    🔴 보류를 자동으로 **풀지는** 않는다. `server/orchestrator/tools.py` 의 소비
    루프는 값을 명령으로 못 옮기는 배정이 하나라도 있으면 만들어 둔 번들을 통째로
    버린다. bm 에는 적용 줄이 없으므로(`LXSEQ_PRESET_APPLY_ATTRIBUTE` 는
    `preset-dim` 한 칸) bm 한 행이 저절로 열리면 **그 bm 임포트가 통째로 0건**이
    된다 — 자동 해제는 그 지뢰를 심는 것이다. 그래서 푸는 대신 **빨개진다.**

    ⚠️ 여기 「프리셋 임포트 **전체**가 0건」이라 적혀 있었으나 t154 가 반증했다 —
    한 번의 임포트 = 한 시트 = 한 종류라 다른 종류로 번지지 않는다
    (`parse_preset_csv` 가 종류를 하나로 정하고 프로덕션 호출지가 하나다).
    막을 이유는 그대로다: 그 시트가 0건이 되는 것만으로 충분하다.
    """

    def test_no_hold_reason_is_stale_today(self):
        stale = _stale_holds(
            parser_module._ACCEPTED_ATTRIBUTES,
            parser_module._SHEET_TO_CONSOLE_ATTRIBUTE,
            parser_module._PROBE_REJECTED,
        )
        assert stale == (), (
            "콘솔 어휘가 넓어져 이 토큰들의 보류 사유가 거짓이 됐다: "
            + ", ".join(stale)
            + " — 목록에서 빼기 전에 **적용 경로부터 열어라**. "
            "bm 에 적용 줄이 없는 채로 열면 그 bm 임포트가 통째로 0건이 된다 "
            "(server/orchestrator/tools.py 의 apply_untranslatable fail-closed)."
        )

    def test_the_tripwire_actually_fires_when_a_console_name_becomes_accepted(self):
        """비공허성 — 「오늘 조용하다」와 「검사가 공허하다」를 가른다.

        위 검사는 빈 튜플을 단언한다. 술어가 무엇을 넣어도 빈 튜플을 낸다면 그
        단언은 아무것도 안 지킨다. 그래서 넓어진 세계를 만들어 실제로 울리는지 본다.
        """
        stale = _stale_holds(
            _widened_with("Frost1"),
            parser_module._SHEET_TO_CONSOLE_ATTRIBUTE,
            parser_module._PROBE_REJECTED,
        )
        assert stale == ("Frost",)

    def test_the_tripwire_stays_quiet_when_the_token_left_the_hold_list(self):
        """반대 방향 — 사유가 사라진 뒤에는 울리면 안 된다(과잉 경보 방지)."""
        without_frost = tuple(t for t in parser_module._PROBE_REJECTED if t != "Frost")
        stale = _stale_holds(
            _widened_with("Frost1"),
            parser_module._SHEET_TO_CONSOLE_ATTRIBUTE,
            without_frost,
        )
        assert stale == ()


class TestAnUnknownAttributeIsHeldNotPassed:
    """t137 — 어휘 축이 fail-open 이었다. 모르는 속성이 사유 0건으로 통과했다.

    막는 목록(`_PROBE_REJECTED` · `_OUT_OF_SCOPE`)만 있고 **아는 이름 전체**를 묻는
    자리가 없어서, 목록 어디에도 없는 토큰은 토큰이 0개로 잡혀 아무 검사도 안 받았다.
    이 저장소의 다른 판정기들(`preset_mapper` 의 POOL_UNREADABLE, `rig/section.py` 의
    SECTION_TRUNCATED)은 전부 fail-closed 다 — 이 자리만 방향이 반대였다.
    """

    def test_an_attribute_in_no_list_at_all_is_held(self):
        """재현 — 시트 오타나 새 속성이 조용히 콘솔로 향하면 안 된다."""
        storable, reasons = parser_module.classify_storability("preset-bm", "Blorptron 99°")
        assert storable is False
        assert HOLD_ATTRIBUTE_UNKNOWN in [r.hold_class for r in reasons]

    def test_the_hold_names_the_attribute_it_did_not_recognize(self):
        """사유 문면이 어느 이름인지 말해야 다음 사람이 시트를 고칠 수 있다."""
        _storable, reasons = parser_module.classify_storability("preset-bm", "Blorptron 99°")
        detail = " ".join(r.detail for r in reasons if r.hold_class == HOLD_ATTRIBUTE_UNKNOWN)
        assert "Blorptron" in detail

    def test_the_control_is_that_a_known_attribute_raises_no_such_hold(self):
        """대조군 — 아는 이름에도 울리면 위 검사는 어휘를 재는 게 아니다."""
        _storable, reasons = parser_module.classify_storability("preset-bm", "Zoom 45°")
        assert HOLD_ATTRIBUTE_UNKNOWN not in [r.hold_class for r in reasons]

    def test_the_canonical_sheet_gains_no_unknown_hold(self):
        """정본 다섯 행의 속성은 전부 아는 이름이다 — 이 변경이 고정값을 안 흔든다."""
        classes = [c for r in _records() for c in r.hold_classes]
        assert HOLD_ATTRIBUTE_UNKNOWN not in classes

    def test_a_prefix_of_a_known_name_is_not_treated_as_known(self):
        """`Zo` 는 `Zoom` 의 접두지만 아는 이름이 아니다 — 역방향은 숫자 접미만 허용한다."""
        _storable, reasons = parser_module.classify_storability("preset-bm", "Zo 5")
        assert HOLD_ATTRIBUTE_UNKNOWN in [r.hold_class for r in reasons]

    def test_the_tripwire_still_opens_bm03_under_the_prism1_substitution(self, monkeypatch):
        """🔴 이 검사가 하중을 진다 — 새 fail-closed 축이 t135 의 증명을 죽이면 안 된다.

        치환하면 시트 토큰 `Prism` 이 막는 목록에서 빠진다. 어휘 검사가 **한 방향**
        접두 매칭이면 `Prism` 이 그 순간 「모르는 이름」이 되어 BM.03 이 새 사유로
        막히고, 「치환은 회귀다」라는 증명이 조용히 사라진다. 두 어휘의 길이가 서로
        반대 방향이라(`시트 Prism` ↔ `콘솔 Prism1`) 어휘 검사는 대칭이어야 한다.
        """
        monkeypatch.setattr(parser_module, "_PROBE_REJECTED", PROBED_STRINGS)
        opened = [r for r in _records() if r.storable]
        assert [r.preset_id for r in opened] == ["BM.03"]
