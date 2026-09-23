"""컴파일 경로 시험 — SPEC-LDDESIGN-001 M6 (REQ-LDDESIGN-073·074, 카드 t439).

AC-LDDESIGN-027 이 요구하는 두 가지를 각각 다른 시험 클래스로 나눈다.

1. **추적해 실제로 호출하는지** — ``TestReuseIsTraced`` 는
   :func:`server.design.lint.lint_sheet` · :func:`server.design.energy.
   axis_budget` · :func:`server.design.cue_fade.store_with_fade` 셋을
   monkeypatch 스파이로 감싸 컴파일 한 번에 실제로 불리는지 확인한다.
   래핑 전에는 원본 함수를 그대로 호출하므로(스파이가 아니라 감싸기),
   반환값 검증도 원본 그대로 유지된다.
2. **8곡 전체가 예외 없이 컴파일된다** — ``TestCompileAllEightSongs`` 는
   린트를 완화하지 않고 실측 위반 건수를 그대로 고정한다(REQ-076 과
   같은 원칙 — 종이로 덮지 않는다).

``TestFitsExistingReadbackParsing`` 은 REQ-LDDESIGN-074 — 컴파일된 큐가
기존 Sequence 저장·리드백 파싱(``server.web.session._SONG_STORE_CUE``)을
새 파서 없이 그대로 통과하는지 확인한다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from server.concept import compile as compile_module
from server.concept import timing as timing_module
from server.concept.compile import compile_song
from server.concept.gates import build_song
from server.design import energy as energy_module
from server.design import lint as lint_module

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "pilot_baseline.json"


def _load_usable_songs() -> list[dict[str, Any]]:
    data = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    return [song for song in data if "error" not in song]


_SONGS = _load_usable_songs()
_SONGS_BY_NAME = {song["song"]: song for song in _SONGS}


class TestReuseIsTraced:
    """AC-LDDESIGN-027 — "추적해 실제로 호출하는지" 를 spy 로 증명한다."""

    def test_lint_sheet_is_actually_called(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[object] = []
        original = lint_module.lint_sheet

        def _spy(sheet, profile, rig):
            calls.append(sheet)
            return original(sheet, profile, rig)

        monkeypatch.setattr(compile_module, "lint_sheet", _spy)
        build = build_song(_SONGS_BY_NAME["Rain.mp3"])
        result = compile_song(build)

        assert len(calls) == 1
        # 스파이가 원본을 그대로 감쌌으므로 반환값도 실제 lint_sheet 호출
        # 결과다 — 우회 경로로 판정을 지어내지 않았다는 증거.
        assert result.lint_report is not None

    def test_axis_budget_is_actually_called(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[int] = []
        original = energy_module.axis_budget

        def _spy(d_level, profile, rig):
            calls.append(d_level)
            return original(d_level, profile, rig)

        monkeypatch.setattr(compile_module, "axis_budget", _spy)
        build = build_song(_SONGS_BY_NAME["Rain.mp3"])
        result = compile_song(build)

        # 큐마다 정확히 1번 — 재구현(직접 계산)이 아니라 하류 함수를
        # 그대로 호출했다는 증거다.
        assert len(calls) == len(build.table)
        assert len(result.energy_reports) == len(build.table)
        assert all(level in (1, 2, 3, 4, 5) for level in calls)

    def test_store_with_fade_is_actually_called(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[str] = []
        original = timing_module.store_with_fade

        def _spy(store, fade_seconds):
            calls.append(store)
            return original(store, fade_seconds)

        # emit_fade()(timing.py, REQ-061)가 store_with_fade 를 감싼
        # 그 자리를 스파이로 감싼다 — 새 페이드 문법을 만들지 않았다는
        # 증거다.
        monkeypatch.setattr(timing_module, "store_with_fade", _spy)
        build = build_song(_SONGS_BY_NAME["Rain.mp3"])
        result = compile_song(build)

        assert len(calls) == len(build.table)
        assert len(calls) == len(result.commands)
        # store_with_fade 가 받은 줄은 CueFade 접미사가 아직 안 붙은 원본
        # Store 줄이다 — 접미사는 store_with_fade 자신이 붙인다.
        assert all(call.startswith("Store Sequence") for call in calls)
        assert all("CueFade" not in call for call in calls)


class TestCompileAllEightSongs:
    """AC-LDDESIGN-027 — 8곡 전체가 예외 없이 컴파일된다.

    린트는 완화하지 않는다 — 카드 t439 가 실제로 낸 값(``uv run pytest
    server/tests/test_concept_compile.py -k compile -q`` 로 재현 가능)을
    그대로 고정한다. 값이 달라지면(새 findings 발생·소멸) 이 시험이
    FAIL 로 그 변화를 드러낸다 — 종이로 덮지 않는다(REQ-076 과 같은
    원칙).
    """

    EXPECTED: dict[str, dict[str, int]] = {
        "Club Diver.mp3": {"commands": 31, "findings": 23, "disabled": 2, "energy": 31},
        "Cut and Run.mp3": {"commands": 38, "findings": 19, "disabled": 2, "energy": 38},
        "Ice cream.mp3": {"commands": 13, "findings": 7, "disabled": 2, "energy": 13},
        "Morning.mp3": {"commands": 29, "findings": 25, "disabled": 2, "energy": 29},
        "Rain.mp3": {"commands": 27, "findings": 20, "disabled": 2, "energy": 27},
        "Too Cool.mp3": {"commands": 44, "findings": 30, "disabled": 2, "energy": 44},
        "scott-buckley-neon.mp3": {"commands": 32, "findings": 22, "disabled": 2, "energy": 32},
        "걸그룹DinoDino_C_max최고품질.wav": {
            "commands": 14,
            "findings": 9,
            "disabled": 2,
            "energy": 14,
        },
    }

    def test_fixture_has_eight_usable_songs(self) -> None:
        assert len(_SONGS) == 8
        assert set(self.EXPECTED) == {song["song"] for song in _SONGS}

    @pytest.mark.parametrize("song_name", list(EXPECTED))
    def test_song_compiles_and_matches_pinned_counts(self, song_name: str) -> None:
        build = build_song(_SONGS_BY_NAME[song_name])
        result = compile_song(build)
        expected = self.EXPECTED[song_name]

        assert len(result.commands) == expected["commands"]
        assert len(result.lint_report.findings) == expected["findings"]
        assert len(result.lint_report.disabled_rules) == expected["disabled"]
        assert len(result.energy_reports) == expected["energy"]
        # 표(안전+구간+프레이즈)와 명령·에너지 결과가 1:1이다 — 큐 하나가
        # 조용히 빠지거나 더해지지 않았다.
        assert len(result.commands) == len(build.table)
        assert len(result.energy_reports) == len(build.table)

    def test_disabled_lint_rules_are_l6_l7_single_layer(self) -> None:
        # 이 컴파일 경로는 라이브 리그를 읽지 않는다(모듈 독스트링) —
        # L6/L7 은 항상 단일 레이어로 꺼진다. 거짓 PASS 가 아니라 명시적
        # DisabledRuleNote 다(RG1, lint.py 독스트링).
        build = build_song(_SONGS_BY_NAME["Rain.mp3"])
        result = compile_song(build)
        rule_ids = {note.rule_id for note in result.lint_report.disabled_rules}
        assert rule_ids == {"L6", "L7"}


class TestFitsExistingReadbackParsing:
    """REQ-LDDESIGN-074 — 컴파일된 큐가 기존 Sequence + Cue 저장·리드백
    흐름을 그대로 통과한다(새 승인 경로를 만들지 않는다). 실기 콘솔
    없이, 기존 리드백 정규식(``server.web.session._SONG_STORE_CUE``)이
    새 파서 없이 파싱해내는지만 확인한다.
    """

    def test_every_store_line_matches_existing_readback_regex(self) -> None:
        from server.web.session import _SONG_STORE_CUE

        build = build_song(_SONGS_BY_NAME["Rain.mp3"])
        result = compile_song(build)

        assert result.commands
        for command in result.commands:
            match = _SONG_STORE_CUE.match(command)
            assert match is not None, command

    def test_readback_cue_numbers_round_trip_to_table_q(self) -> None:
        from server.web.session import _SONG_STORE_CUE

        build = build_song(_SONGS_BY_NAME["Rain.mp3"])
        result = compile_song(build)

        parsed = [float(_SONG_STORE_CUE.match(command).group(1)) for command in result.commands]
        assert parsed == [float(row.q) for row in build.table]


class TestDLevelFromBrightness:
    """§ compile.py 독스트링 — 밝기(%) → D 레벨 역매핑이 energy.py §3
    표의 ``dimmer_pct`` 밴드와 일치한다(경계 포함 규칙 — 상한을 그
    밴드에 귀속한다)."""

    @pytest.mark.parametrize(
        "top_pct,expected_level",
        [
            (0.0, 1),
            (20.0, 1),
            (40.0, 1),
            (40.1, 2),
            (60.0, 2),
            (60.1, 3),
            (80.0, 3),
            (80.1, 4),
            (100.0, 4),  # 알려진 한계 — D5(100~100) 는 이 역매핑으로 나오지 않는다.
        ],
    )
    def test_band_boundaries(self, top_pct: float, expected_level: int) -> None:
        assert compile_module._d_level_from_brightness(top_pct) == expected_level
