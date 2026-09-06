"""카드 t274 — 확정 구간에 운영자의 이름을 붙인다 (``prepare_songcue.section_names``).

오늘 확정 기본값 경로는 중립 ASCII ``S<n>`` 을 쓴다(SPEC-COPILOT-SONGCONFIRM-001
REQ-009). 이름이 룩 라이브러리의 dynamics 어휘(``인트로``·``chorus``·``drop`` …)에
닿으면 ``_section_dynamics`` 가 그 이름으로 dynamics 를 다시 매겨 ``d_level`` 과 두
정본이 되기 때문이다.

이 파일이 지키는 계약: **이름은 라벨에만 닿고 dynamics 에는 닿지 않는다.** 운영자가
``section_names`` 로 준 이름이 큐 라벨이 되고, 룩 선택은 여전히 확정 기록의
``d_level`` 이 정한다 — 이름이 어휘와 겹쳐도 그렇다(``TestNamesNeverDecideDynamics``).

콘솔 접촉 0건. 가짜 실행 포트(``_RecordingPort``)·가짜 상태 포트만 쓴다.
"""

from __future__ import annotations

import pytest

from server.orchestrator.tools import build_toolset

from .test_songcue_confirmed_default import (
    _TOOL,
    _AnalysisPort,
    _call,
    _dimmer_values,
    _record,
    _registry,
)

# 어휘와 정면으로 겹치는 이름들 — DYNAMICS_TERMS 에 실제로 있는 낱말이다.
_VOCAB_NAMES = ["Intro", "Chorus", "Drop"]


def _cue_labels(payload) -> list[str]:
    return [section["name"] for section in payload["report"]["sections"]]


def _stored_cue_names(port) -> list[str]:
    import re

    names = []
    for command in port.executed:
        match = re.fullmatch(r"Store Sequence \d+ Cue \d+ '(.*)'", command)
        if match:
            names.append(match.group(1))
    return names


class TestOperatorNamesReachTheCueLabel:
    """운영자가 준 이름이 리포트와 콘솔 명령의 큐 라벨에 그대로 선다."""

    def test_supplied_names_replace_the_neutral_defaults(self):
        registry, port = _registry(song_analysis=_AnalysisPort(_record()))
        _execution, payload = _call(registry, section_names=["Intro", "Verse", "Chorus"])
        assert payload["sections_source"] == "confirmed_analysis"
        assert payload["section_names_source"] == "operator"
        assert _cue_labels(payload) == ["Intro", "Verse", "Chorus"]
        assert _stored_cue_names(port) == ["Intro", "Verse", "Chorus"]

    def test_omitting_the_argument_keeps_todays_neutral_names(self):
        # 대조군 — 인자가 없으면 오늘과 바이트 동일하다(S<n>).
        registry, port = _registry(song_analysis=_AnalysisPort(_record()))
        _execution, payload = _call(registry)
        assert payload["section_names_source"] == "default"
        assert _cue_labels(payload) == ["S1", "S2", "S3"]
        assert _stored_cue_names(port) == ["S1", "S2", "S3"]


class TestNamesNeverDecideDynamics:
    """이 카드의 핵심 — 이름은 dynamics 의 출처가 아니다.

    ``_record()`` 의 채택 구간은 D1 / D3 / D5 이고 라이브러리는 dynamics 마다 Dimmer
    값이 다른 룩 하나씩(``d1``=10 … ``d5``=50)이다. 이름을 어휘 낱말로 줘도 골라진
    룩의 Dimmer 는 여전히 10 / 30 / 50 이어야 한다 — 이름이 dynamics 를 다시 매겼다면
    ``Intro``(1,2) · ``Chorus``(4,5) · ``Drop``(4,5) 를 따라 값이 달라진다.
    """

    def test_vocabulary_names_do_not_move_the_look_selection(self):
        registry, _port = _registry(song_analysis=_AnalysisPort(_record()))
        _execution, payload = _call(registry, section_names=_VOCAB_NAMES)
        assert _cue_labels(payload) == _VOCAB_NAMES
        assert _dimmer_values(payload) == [10, 30, 50]

    def test_the_inverted_case_is_the_same_answer(self):
        # 어휘 밴드와 정반대로 이름을 붙인다 — D5 구간에 ``Intro``(1,2), D1 구간에
        # ``Drop``(4,5). 이름이 이겼다면 값이 뒤집힌다.
        registry, _port = _registry(song_analysis=_AnalysisPort(_record()))
        _execution, payload = _call(registry, section_names=["Drop", "Verse", "Intro"])
        assert _dimmer_values(payload) == [10, 30, 50]


class TestNamesAreRefusedRatherThanSilentlyMangled:
    """콘솔 라벨은 ASCII 로 접힌다 — 조용히 떨어지느니 이름을 대고 거절한다.

    ``server/looks/songcue.py`` 의 ``_ascii_label`` 은 NFKD 뒤 ascii-ignore 를 하므로
    한글 이름은 통째로 사라지고 ``Section <n>`` 폴백이 선다(실측 2026-09-06). 그
    폴백은 운영자가 요청한 이름이 아니므로, 라벨에 남지 않을 이름은 도구 경계에서
    거절한다.
    """

    @pytest.mark.parametrize(
        "names",
        [
            ["인트로", "후렴", "브릿지"],  # 한글 — 라벨에서 통째로 사라진다
            ["Intro", "후렴", "Chorus"],  # 한 칸만 비-ASCII 여도 거절
            ["Café", "Verse", "Chorus"],  # 악센트는 조용히 Cafe 로 바뀐다
        ],
    )
    def test_non_ascii_names_are_refused(self, names):
        registry, _port = _registry(song_analysis=_AnalysisPort(_record()))
        execution, payload = _call(registry, section_names=names)
        assert execution.result.is_error is True
        assert "ASCII" in payload["error"]

    @pytest.mark.parametrize("bad", ["", "   ", "---", "!!!"])
    def test_names_without_a_letter_or_digit_are_refused(self, bad):
        registry, _port = _registry(song_analysis=_AnalysisPort(_record()))
        execution, payload = _call(registry, section_names=[bad, "Verse", "Chorus"])
        assert execution.result.is_error is True
        assert "'section_names'" in payload["error"]

    def test_a_single_quote_is_refused_like_every_other_label(self):
        # map_cues 의 ``sequence_name`` · 정본 CUE 시트 검사와 **같은 규칙**이다 —
        # MA3 홑따옴표 문자열은 홑따옴표로 닫히므로 이름 안의 홑따옴표가 명령을
        # 그 자리에서 자른다. 이스케이프 없이 fail-closed.
        registry, _port = _registry(song_analysis=_AnalysisPort(_record()))
        execution, payload = _call(registry, section_names=["Rock'n", "Verse", "Chorus"])
        assert execution.result.is_error is True
        assert "홑따옴표" in payload["error"]


class TestTheCountMustLineUp:
    """index 정렬이 계약이다 — 개수가 다르면 어느 이름이 어느 구간인지 알 수 없다."""

    @pytest.mark.parametrize("names", [["Intro"], ["Intro", "Verse"], ["a", "b", "c", "d"]])
    def test_a_length_mismatch_names_both_counts(self, names):
        registry, _port = _registry(song_analysis=_AnalysisPort(_record()))
        execution, payload = _call(registry, section_names=names)
        assert execution.result.is_error is True
        assert str(len(names)) in payload["error"]
        assert "3" in payload["error"]


class TestExplicitSectionsAlreadyCarryTheirNames:
    """``sections`` 를 명시했으면 이름은 거기 있다 — 조용히 버리지 않고 거절한다."""

    def test_section_names_with_explicit_sections_is_an_error(self):
        registry, _port = _registry(song_analysis=_AnalysisPort(_record()))
        execution, payload = _call(
            registry,
            sections=[{"name": "Intro", "start": "0:00"}],
            section_names=["Chorus"],
        )
        assert execution.result.is_error is True
        assert "'sections'" in payload["error"]
        assert "'section_names'" in payload["error"]

    def test_without_a_record_section_names_is_also_an_error(self):
        # 기록이 없으면 붙일 확정 구간 자체가 없다.
        registry, _port = _registry()
        execution, payload = _call(registry, section_names=["Intro"])
        assert execution.result.is_error is True
        assert "'section_names'" in payload["error"]


class TestTheArgumentShapeIsChecked:
    @pytest.mark.parametrize("value", ["Intro", 3, {"0": "Intro"}, [1, 2, 3], ["Intro", None, "x"]])
    def test_non_string_arrays_are_refused(self, value):
        registry, _port = _registry(song_analysis=_AnalysisPort(_record()))
        execution, payload = _call(registry, section_names=value)
        assert execution.result.is_error is True
        assert "'section_names'" in payload["error"]


class TestTheSchemaAdvertisesTheArgument:
    def test_section_names_is_optional_and_documented(self):
        registry, _port = _registry()
        definition = next(d for d in registry.definitions() if d.name == _TOOL)
        # 필수 셋은 그대로다 — 이 카드는 계약을 넓히기만 한다.
        assert set(definition.parameters["required"]) == {"song_title", "genre", "timecode_number"}
        schema = definition.parameters["properties"]["section_names"]
        assert schema["type"] == "array"
        assert schema["items"]["type"] == "string"
        assert "ASCII" in schema["description"]
        assert "dynamics" in schema["description"]


class TestTheToolLayerAddsNoServerWebImport:
    """층 경계 — 이 카드는 ``server.orchestrator.tools`` 의 import 를 넓히지 않는다."""

    def test_build_toolset_signature_is_unchanged(self):
        import inspect

        parameters = inspect.signature(build_toolset).parameters
        assert "song_analysis" in parameters
