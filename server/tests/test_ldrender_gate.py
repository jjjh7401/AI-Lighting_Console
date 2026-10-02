"""카드 t501 — SPEC-LDRENDER-001 M1/M7, REQ-LDRENDER-013/014/016.

`server.design.ldrender_gate`의 LIT-only·큐-단위 집계를 두 대조군으로 검증한다
(AC-LDRENDER-013): Rain 고치기 전 송신 목록(음성 대조 — 반드시 경고)과 통과
기준을 만족하는 합성 송신 목록(양성 대조 — 반드시 경고 없음). 어느 한쪽만
PASS 하면 공허한 검사다(moai-memory 교훈 — 안 쏘면 검사가 아니다).

``_RAIN_CUES``는 실측 기록의 **부분집합**이다 — 2026-10-01
`.moai/reports/t499/runs/Rain/readout.json`(gitignored, t499 가 가짜 콘솔 송신을
재현해 만든 판독 결과)에서 ``kind == "section"``인 12개 큐 중 4개(1·2·3·4번,
BACK 디머가 20/40/56/80 사이를 오가는 대표 구간)를 ``sent_rgb_in_cue``·
``stage_rig_view`` 그대로 옮겼다(``python3 -c "import json; json.load(open(...))"``
로 읽어 수기 전사 — 그 디렉터리가 gitignore 되어 테스트가 파일을 직접 열 수
없으므로 리터럴로 박아 둔다). 실측 당시 12개 큐 **전부**가 LIT 버킷 2개(전체 값
+ BACK)였음을 스크립트로 확인했다(M1 progress.md 의 명령 기록 참조) — 이 4개는
그 전수 결과를 대표하도록 고른 것이지 "전부를 옮겼다"는 주장이 아니다. 효과
요청 수(``fx_hinted=11``)와 송신 효과 줄 0(``phaser_or_other_preset_lines``가
빈 목록)은 readout.json 전체(12개 큐 + climax_return 1개) 기준의 실측값이다.

M7(이 파일 하단) — ``gate_cues_from_commands``/``role_group_map``/
``kind_for_composed_cue``(송신 직전 명령 목록 → 게이트 입력 배선)와
``evaluate()``의 신규 ``warm_white_rgb``/``effect_role_mapped`` 축을 겨눈다.
"""

from __future__ import annotations

from dataclasses import replace

from server.design import color_names as _COLOR_NAMES
from server.design.ldrender_gate import (
    SectionCue,
    color_count,
    effect_line_count,
    evaluate,
    gate_cues_from_commands,
    kind_for_composed_cue,
    layer_diversity,
    role_group_map,
)
from server.design.song_cue_composer import (
    ComposedCue,
    CueAccentFixtureData,
    CueColorData,
    CueDimmerData,
    CueFxData,
    CueMibData,
    CuePositionData,
    CueTimingData,
)
from server.design.song_cue_render import reviewed_song_commands
from server.design.song_plan import MANUAL_GO, TimingPlan

# -- 실측 부분집합: Rain 고치기 전 (2026-10-01, .moai/reports/t499/runs/Rain/readout.json) --

#: 12개 구간 큐 전부가 송신한 유일한 RGB — readout.json 의 `sent_rgb_in_cue`.
_RAIN_RGB = (5.0, 20.0, 100.0)

#: 아래 4개 대표 큐(1~4번)의 `stage_rig_view` — 8개 리그 그룹 중 BACK 만 디머가
#: 다르고(20/40/56/80), 나머지 7개 그룹은 전체 디머와 같은 값을 받는다 —
#: LIT-only 로 세도 버킷은 2개뿐이다(전체 값 1 + BACK 1). 실측 스크립트로 12개
#: 큐 전부가 이 2버킷 패턴을 공유함을 확인했다(M1 progress.md).
_RAIN_CUES = (
    SectionCue(
        cue_no="1",
        name="Intro",
        kind="section",
        sent_rgb=(_RAIN_RGB,),
        role_view={
            "KEY": ({"dim": 50.0, "pos": "2.30", "rgb": list(_RAIN_RGB)},),
            "FOH": ({"dim": 50.0, "pos": "2.30", "rgb": list(_RAIN_RGB)},),
            "BACK": ({"dim": 40.0, "pos": "2.30", "rgb": list(_RAIN_RGB)},),
            "SIDE": ({"dim": 50.0, "pos": "2.30", "rgb": list(_RAIN_RGB)},),
            "WASH": ({"dim": 50.0, "pos": "2.30", "rgb": list(_RAIN_RGB)},),
            "MOVER": ({"dim": 50.0, "pos": "2.30", "rgb": list(_RAIN_RGB)},),
            "BLIND": ({"dim": 50.0, "pos": "2.30", "rgb": list(_RAIN_RGB)},),
            "STROBE": ({"dim": 50.0, "pos": "2.30", "rgb": list(_RAIN_RGB)},),
        },
    ),
    SectionCue(
        cue_no="2",
        name="Verse 1",
        kind="section",
        sent_rgb=(_RAIN_RGB,),
        role_view={
            "KEY": ({"dim": 50.0, "rgb": list(_RAIN_RGB)},),
            "FOH": ({"dim": 50.0, "rgb": list(_RAIN_RGB)},),
            "BACK": ({"dim": 56.0, "rgb": list(_RAIN_RGB)},),
            "SIDE": ({"dim": 50.0, "rgb": list(_RAIN_RGB)},),
            "WASH": ({"dim": 50.0, "rgb": list(_RAIN_RGB)},),
            "MOVER": ({"dim": 50.0, "rgb": list(_RAIN_RGB)},),
            "BLIND": ({"dim": 50.0, "rgb": list(_RAIN_RGB)},),
            "STROBE": ({"dim": 50.0, "rgb": list(_RAIN_RGB)},),
        },
    ),
    SectionCue(
        cue_no="3",
        name="Verse 2",
        kind="section",
        sent_rgb=(_RAIN_RGB,),
        role_view={
            "KEY": ({"dim": 50.0, "rgb": list(_RAIN_RGB)},),
            "FOH": ({"dim": 50.0, "rgb": list(_RAIN_RGB)},),
            "BACK": ({"dim": 20.0, "rgb": list(_RAIN_RGB)},),
            "SIDE": ({"dim": 50.0, "rgb": list(_RAIN_RGB)},),
            "WASH": ({"dim": 50.0, "rgb": list(_RAIN_RGB)},),
            "MOVER": ({"dim": 50.0, "rgb": list(_RAIN_RGB)},),
            "BLIND": ({"dim": 50.0, "rgb": list(_RAIN_RGB)},),
            "STROBE": ({"dim": 50.0, "rgb": list(_RAIN_RGB)},),
        },
    ),
    SectionCue(
        cue_no="4",
        name="Chorus 1",
        kind="section",
        sent_rgb=(_RAIN_RGB,),
        role_view={
            "KEY": ({"dim": 50.0, "rgb": list(_RAIN_RGB)},),
            "FOH": ({"dim": 50.0, "rgb": list(_RAIN_RGB)},),
            "BACK": ({"dim": 80.0, "rgb": list(_RAIN_RGB)},),
            "SIDE": ({"dim": 50.0, "rgb": list(_RAIN_RGB)},),
            "WASH": ({"dim": 50.0, "rgb": list(_RAIN_RGB)},),
            "MOVER": ({"dim": 50.0, "rgb": list(_RAIN_RGB)},),
            "BLIND": ({"dim": 50.0, "rgb": list(_RAIN_RGB)},),
            "STROBE": ({"dim": 50.0, "rgb": list(_RAIN_RGB)},),
        },
    ),
)

#: readout.json `phaser_or_other_preset_lines` — 11개 큐가 페이저 제안
#: (`design_phaser_hint`)을 받았지만 송신 줄은 0 (t499 §3 P5b).
_RAIN_SENT_LINES_NO_EFFECT: tuple[str, ...] = ()


def test_rain_before_fix_warns_on_all_three_axes() -> None:
    """음성 대조 — 고치기 전 Rain 은 색/LIT 층/효과 세 축 모두에서 걸려야 한다."""
    result = evaluate(
        _RAIN_CUES,
        sent_lines=_RAIN_SENT_LINES_NO_EFFECT,
        fx_requested=0,
        fx_hinted=11,  # readout.json: 11개 구간 큐가 design_phaser_hint 를 받음
        palette_mode="modulate",
    )
    assert result.warns, "Rain 고치기 전 송신 목록은 반드시 경고가 발동해야 한다"
    assert result.color_count == 1, f"색 수는 1 이어야 한다(실측): {result.color_count}"
    assert result.min_cue_lit_layers == 2, (
        f"모든 큐의 LIT 층은 2(전체 값 + BACK)여야 한다: {result.min_cue_lit_layers}"
    )
    assert result.effect_lines_sent == 0, f"효과 송신 줄은 0이어야 한다: {result.effect_lines_sent}"
    # 세 사유 전부가 문자열로 실려야 한다(§3.2 — 사유는 문자열로 단언).
    joined = " / ".join(result.violations)
    assert "색 수 1개" in joined
    assert "LIT 층 3 미만" in joined
    assert "효과 요청" in joined


# -- 합성(날조): 통과 기준을 만족하는 송신 목록 --

#: 3색, 모든 구간 큐가 LIT 층 3개 이상(key/back/side 가 서로 다른 값), 효과 요청
#: 곡에 효과 줄 1개 이상 — AC-013 양성 대조 조건 그대로.
_PASSING_RGB_A = (10.0, 200.0, 30.0)
_PASSING_RGB_B = (200.0, 10.0, 30.0)

_PASSING_SYNTHETIC_CUES = (
    SectionCue(
        cue_no="1",
        name="Intro",
        kind="section",
        sent_rgb=(_PASSING_RGB_A,),
        role_view={
            "key": ({"dim": 60.0, "rgb": list(_PASSING_RGB_A)},),
            "back": ({"dim": 40.0, "rgb": list(_PASSING_RGB_A)},),
            "side": ({"dim": 30.0, "rgb": list(_PASSING_RGB_B)},),
            "effect": ({"dim": 0.0},),  # 비액센트 큐 — effect 는 꺼져 있다(R3)
        },
    ),
    SectionCue(
        cue_no="2",
        name="Chorus 1",
        kind="section",
        sent_rgb=(_PASSING_RGB_B,),
        role_view={
            "key": ({"dim": 90.0, "rgb": list(_PASSING_RGB_B)},),
            "back": ({"dim": 100.0, "rgb": list(_PASSING_RGB_B)},),
            "side": ({"dim": 70.0, "rgb": list(_PASSING_RGB_A)},),
            "wash": ({"dim": 55.0, "rgb": list(_PASSING_RGB_A)},),
            "effect": ({"dim": 0.0},),
        },
    ),
    SectionCue(
        cue_no="3",
        name="Outro",
        kind="section",
        sent_rgb=(_PASSING_RGB_A,),
        role_view={
            "key": ({"dim": 30.0, "rgb": list(_PASSING_RGB_A)},),
            "back": ({"dim": 20.0, "rgb": list(_PASSING_RGB_A)},),
            "mover": ({"dim": 15.0, "rgb": list(_PASSING_RGB_B)},),
            "effect": ({"dim": 0.0},),
        },
    ),
)

_PASSING_SENT_LINES_WITH_EFFECT = (
    "Group 11 ; Attribute 'Dimmer' At 60",
    "Fixture 70 + 71 ; At Preset 5.3",  # 페이저 recall — 풀 5, 포지션 풀(2) 아님
)


def test_passing_synthetic_does_not_warn() -> None:
    """양성 대조 — 세 기준을 만족하는 합성 송신 목록은 경고가 없어야 한다."""
    result = evaluate(
        _PASSING_SYNTHETIC_CUES,
        sent_lines=_PASSING_SENT_LINES_WITH_EFFECT,
        fx_requested=1,
        fx_hinted=1,
        palette_mode="modulate",
    )
    assert not result.warns, f"통과 기준을 만족하는데 경고가 발동했다: {result.violations}"
    assert result.color_count == 2
    assert result.min_cue_lit_layers is not None and result.min_cue_lit_layers >= 3
    assert result.effect_lines_sent == 1


def test_palette_mode_na_skips_color_count_check() -> None:
    """REQ-015/AC-014 — 비기본 palette_mode 는 색 수 경고에서 n/a."""
    # Rain 큐 그대로 쓰되(색 1개 — modulate 라면 FAIL 대상) palette_mode 만 바꾼다.
    result = evaluate(
        _RAIN_CUES,
        sent_lines=_RAIN_SENT_LINES_NO_EFFECT,
        fx_requested=0,
        fx_hinted=0,
        palette_mode="single",
    )
    assert not any("색 수" in v for v in result.violations), (
        f"single 모드에서는 색 수 축이 n/a 여야 한다: {result.violations}"
    )
    # LIT 층 축은 palette_mode 와 무관하게 여전히 걸린다(별개의 축).
    assert any("LIT 층" in v for v in result.violations)


# -- 집계 동치성 (AC-LDRENDER-012) --


def test_layer_diversity_matches_manual_lit_only_count() -> None:
    """게이트의 LIT-only 층 수가 손으로 센 것과 일치해야 한다(집계 동치성)."""
    cue = _RAIN_CUES[0]
    manual_lit_states = {
        (
            state["dim"],
            tuple(state.get("rgb", ())),
            state.get("pos"),
        )
        for states in cue.role_view.values()
        for state in states
        if state.get("dim", 0) > 0
    }
    assert layer_diversity(cue.role_view) == len(manual_lit_states)
    assert layer_diversity(cue.role_view) == 2  # 전체 값(1) + BACK(1)


def test_layer_diversity_excludes_zero_dimmer_roles() -> None:
    """뮤테이션 대조 — effect 를 켜면(dim>0) 버킷이 늘어야 한다(LIT-only 가 실제로
    0 을 걸러낸다는 증거, §3.3 요구 — 뮤테이션은 새 단언에 걸어라)."""
    cue = _PASSING_SYNTHETIC_CUES[0]
    before = layer_diversity(cue.role_view)
    mutated_view = dict(cue.role_view)
    mutated_view["effect"] = ({"dim": 80.0, "rgb": [1.0, 2.0, 3.0]},)
    after = layer_diversity(mutated_view)
    assert after == before + 1, (
        f"effect 를 디머>0 으로 켰는데 버킷 수가 그대로다(before={before}, after={after}) — "
        "LIT-only 필터가 꺼진 상태를 실제로 거르고 있는지 의심해야 한다"
    )


def test_color_count_excludes_exempt_cues() -> None:
    """블랙아웃/MIB 사전이동 큐는 색 집계에서 빠진다(AC-001 경계 사례)."""
    exempt_cue = SectionCue(
        cue_no="11.5",
        name="Chorus 6 Return",
        kind="mib_premove",
        sent_rgb=((9.0, 9.0, 9.0),),  # 이 값이 집계에 들어가면 테스트가 실패한다
        role_view={},
    )
    cues = (*_RAIN_CUES, exempt_cue)
    assert color_count(cues) == 1, "예외 큐의 색이 전체 색 집계에 섞여 들어갔다"


def test_effect_line_count_excludes_position_preset_pool() -> None:
    """readout.py 의 규칙 재사용 — `At Preset 2.<slot>`(포지션 풀)은 효과 줄이 아니다."""
    lines = (
        "Fixture 1 ; At Preset 2.30",  # 포지션 프리셋 — 효과 아님
        "Group 11 ; At Preset 5.3",  # 페이저 recall — 효과
        "Group 11 ; Attribute 'Dimmer' At 80",  # 프리셋 아님
    )
    assert effect_line_count(lines) == 1


# -- M7(REQ-LDRENDER-014) — role_group_map / kind_for_composed_cue --


_SIDE_MULTI_MAPPING = (
    {"role": "key", "group_no": 2},
    {"role": "back", "group_no": 4},
    {"role": "side", "group_no": 5},
    {"role": "side", "group_no": 6},
    {"role": "side", "group_no": 7},
    {"role": "effect", "group_no": 14},
    {"role": "effect", "group_no": 15},
    {"role": "effect", "group_no": 16},
)


def test_role_group_map_last_wins_for_single_valued_roles() -> None:
    """side 가 그룹 5/6/7 전부에 매칭되어도, 주소는 마지막 항목(7)만 역할로
    산다 — `song_cue_render._role_group_numbers`와 같은 동점 규율(M2 선례)."""
    mapping = role_group_map(_SIDE_MULTI_MAPPING)
    assert mapping[7] == "side"
    assert mapping[5] == "side"  # 역방향 조회 자체는 모든 그룹 번호를 담는다
    assert mapping[2] == "key"
    assert mapping[4] == "back"


def test_role_group_map_preserves_every_distinct_effect_group() -> None:
    """effect 는 BLIND/STROBE/HAZE 가 각자 독립 주소라 셋 다 보존된다 —
    `_effect_group_numbers`와 동형(단일값으로 접지 않는다)."""
    mapping = role_group_map(_SIDE_MULTI_MAPPING)
    assert {no for no, role in mapping.items() if role == "effect"} == {14, 15, 16}


def test_role_group_map_ignores_malformed_entries() -> None:
    malformed = (
        {"role": "key"},  # group_no 없음
        {"group_no": 4},  # role 없음
        {"role": "back", "group_no": True},  # bool 은 int 가 아니다(가드)
        {"role": "side", "group_no": 7},
    )
    assert role_group_map(malformed) == {7: "side"}


class _KindCue:
    """``kind_for_composed_cue``가 실제로 읽는 두 필드(``kind``·
    ``dimmer.blackout``)만 채운 대역."""

    def __init__(self, kind: str, blackout: bool = False) -> None:
        self.kind = kind
        self.dimmer = CueDimmerData(
            key_pct=0.0 if blackout else 50.0,
            back_pct=None,
            budget_range_pct=(0.0, 100.0),
            blackout=blackout,
        )


def test_kind_for_composed_cue_passes_mib_premove_through() -> None:
    assert kind_for_composed_cue(_KindCue("mib_premove")) == "mib_premove"


def test_kind_for_composed_cue_detects_blackout_flag() -> None:
    assert kind_for_composed_cue(_KindCue("section", blackout=True)) == "blackout"


def test_kind_for_composed_cue_folds_climax_return_into_section() -> None:
    """climax_return 은 AC-001 "구간 큐 전부" 예외가 아니다(M3 후속 해소) —
    블랙아웃이 아니면 평범한 section 으로 접는다."""
    assert kind_for_composed_cue(_KindCue("climax_return")) == "section"
    assert kind_for_composed_cue(_KindCue("section")) == "section"


def test_kind_for_composed_cue_missing_bundle_cue_defaults_to_section() -> None:
    """``bundle_cues=()``(조립기 번들 교차조회 불가)이면 보수적으로
    ``"section"``으로 본다 — 예외 큐를 놓치면 과도하게 엄격해질 뿐, 조용히
    느슨해지지 않는다(``gate_cues_from_commands`` 독스트링 참조)."""
    gate_cues = gate_cues_from_commands(
        (
            "Fixture 1 + 2 ; Attribute 'Dimmer' At 50",
            "Store Sequence 1 Cue 1 'Intro'",
        ),
        bundle_cues=(),
        layer_mapping=({"role": "key", "group_no": 2},),
    )
    assert gate_cues[0].kind == "section"


# -- M7 — gate_cues_from_commands (명령 문자열 → SectionCue) --


_PARSER_MAPPING = (
    {"role": "key", "group_no": 2},
    {"role": "back", "group_no": 4},
    {"role": "effect", "group_no": 14},
)


def test_gate_cues_from_commands_baseline_applies_to_every_known_role() -> None:
    """`Fixture` 베이스라인 줄(공유 선택)은 모든 알려진 역할에 같은 값을
    적용한다 — fid 멤버십을 몰라도 된다(RG5)."""
    commands = (
        "Fixture 1 + 2 + 3 ; Attribute 'Dimmer' At 60",
        "Store Sequence 1 Cue 1 'Intro'",
    )
    gate_cues = gate_cues_from_commands(commands, layer_mapping=_PARSER_MAPPING)
    assert len(gate_cues) == 1
    cue = gate_cues[0]
    assert cue.cue_no == "1"
    assert cue.name == "Intro"
    assert cue.kind == "section"
    assert cue.role_view["key"] == ({"dim": 60.0},)
    assert cue.role_view["back"] == ({"dim": 60.0},)
    assert cue.role_view["effect"] == ({"dim": 60.0},)


def test_gate_cues_from_commands_group_line_overrides_only_its_role() -> None:
    commands = (
        "Fixture 1 + 2 + 3 ; Attribute 'Dimmer' At 60",
        "Group 4 ; Attribute 'Dimmer' At 80",
        "Store Sequence 1 Cue 1 'Verse'",
    )
    gate_cues = gate_cues_from_commands(commands, layer_mapping=_PARSER_MAPPING)
    cue = gate_cues[0]
    assert cue.role_view["back"] == ({"dim": 80.0},)
    assert cue.role_view["key"] == ({"dim": 60.0},)  # 베이스라인 그대로


def test_gate_cues_from_commands_tracks_color_and_sent_rgb() -> None:
    commands = (
        "Fixture 1 + 2 + 3 ; Attribute 'ColorRGB_R' At 5 ; Attribute 'ColorRGB_G' At 20 ; "
        "Attribute 'ColorRGB_B' At 100",
        "Group 14 ; Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 0 ; "
        "Attribute 'ColorRGB_B' At 0",
        "Store Sequence 1 Cue 1 'Chorus'",
    )
    gate_cues = gate_cues_from_commands(commands, layer_mapping=_PARSER_MAPPING)
    cue = gate_cues[0]
    assert cue.role_view["back"][0]["rgb"] == (5.0, 20.0, 100.0)
    assert cue.role_view["effect"][0]["rgb"] == (100.0, 0.0, 0.0)
    assert set(cue.sent_rgb) == {(5.0, 20.0, 100.0), (100.0, 0.0, 0.0)}


def test_gate_cues_from_commands_group_with_no_mapped_role_is_ignored() -> None:
    """층 매핑에 없는 그룹 번호(예: 포지션 풀 참조)는 역할로 못 옮기므로
    건너뛴다 — 추측하지 않는다."""
    commands = (
        "Fixture 1 ; Attribute 'Dimmer' At 50",
        "Group 99 ; Attribute 'Dimmer' At 10",
        "Store Sequence 1 Cue 1 'Intro'",
    )
    gate_cues = gate_cues_from_commands(commands, layer_mapping=_PARSER_MAPPING)
    assert len(gate_cues) == 1
    assert all(group_no not in (99,) for group_no in role_group_map(_PARSER_MAPPING))


def test_gate_cues_from_commands_tracks_state_across_multiple_cues() -> None:
    """콘솔 트래킹 가정 — 큐 안에서 값을 안 받은 역할은 앞 큐 값을 잇는다."""
    commands = (
        "Fixture 1 + 2 ; Attribute 'Dimmer' At 50",
        "Store Sequence 1 Cue 1 'Intro'",
        "Group 4 ; Attribute 'Dimmer' At 90",
        "Store Sequence 1 Cue 2 'Chorus'",
    )
    gate_cues = gate_cues_from_commands(commands, layer_mapping=_PARSER_MAPPING)
    assert gate_cues[0].role_view["key"] == ({"dim": 50.0},)
    # 큐 2 에서도 key 는 큐 1 의 값을 그대로 잇는다(건드리지 않았으므로).
    assert gate_cues[1].role_view["key"] == ({"dim": 50.0},)
    assert gate_cues[1].role_view["back"] == ({"dim": 90.0},)


# -- M7(REQ-LDRENDER-004 §6.3 집계 플래그) — warm_white_rgb 색 수 제외 축 --


_WARM_WHITE = _COLOR_NAMES.resolve_color_name("Warm White")


def test_color_count_excludes_the_given_rgb_when_asked() -> None:
    cues = (
        SectionCue(cue_no="1", kind="section", sent_rgb=((5.0, 20.0, 100.0), _WARM_WHITE)),
        SectionCue(cue_no="2", kind="section", sent_rgb=((100.0, 55.0, 5.0), _WARM_WHITE)),
    )
    assert color_count(cues) == 3  # 제외 없이는 웜화이트도 고유 색 1종
    assert color_count(cues, exclude_rgb=_WARM_WHITE) == 2


def test_evaluate_excludes_warm_white_from_the_colour_axis() -> None:
    """M4 §Gaps 2(AC-004(a) 웜화이트 집계 플래그) 해소 — `key` 웜화이트를
    빼면 색 수가 §6.3 기준(2~3) 안으로 들어온다."""
    cues = (
        SectionCue(
            cue_no="1",
            kind="section",
            sent_rgb=((5.0, 20.0, 100.0), (100.0, 55.0, 5.0), _WARM_WHITE),
            role_view={
                "back": ({"dim": 60.0},),
                "side": ({"dim": 60.0},),
                "key": ({"dim": 60.0},),
            },
        ),
    )
    without_exclusion = evaluate(cues, palette_mode="modulate")
    assert without_exclusion.color_count == 3
    assert not any("색 수" in v for v in without_exclusion.violations)  # 우연히 범위 안

    many_colours = (
        SectionCue(
            cue_no="1",
            kind="section",
            sent_rgb=(
                (5.0, 20.0, 100.0),
                (100.0, 55.0, 5.0),
                (100.0, 0.0, 0.0),
                _WARM_WHITE,
            ),
            role_view={
                "back": ({"dim": 60.0},),
                "side": ({"dim": 60.0},),
                "mover": ({"dim": 60.0},),
                "key": ({"dim": 60.0},),
            },
        ),
    )
    result = evaluate(many_colours, palette_mode="modulate", warm_white_rgb=_WARM_WHITE)
    assert result.color_count == 3  # 웜화이트 제외 후 3종 — §6.3 기준 안
    assert not any("색 수" in v for v in result.violations)

    result_no_exclusion = evaluate(many_colours, palette_mode="modulate")
    assert result_no_exclusion.color_count == 4  # 제외 없으면 4종 — 기준 밖
    assert any("색 수" in v for v in result_no_exclusion.violations)


# -- M7(M5 블로커 조건 ①) — effect_role_mapped 축 --


def test_evaluate_warns_when_effect_role_is_unmapped_even_without_fx_request() -> None:
    """효과를 요청하지 않은 곡이라도, 층 매핑에 effect 역할 자체가 없으면
    (``_effect_dimmer_zero_lines``가 구조적으로 무력화됨) 별도로 경고한다 —
    기존 fx 축(요청 대비 송신 0)과 **독립**이다."""
    cues = (SectionCue(cue_no="1", kind="section", role_view={"key": ({"dim": 60.0},)}),)
    mapped = evaluate(cues, fx_requested=0, fx_hinted=0, effect_role_mapped=True)
    unmapped = evaluate(cues, fx_requested=0, fx_hinted=0, effect_role_mapped=False)
    assert not any("효과 역할 그룹" in v for v in mapped.violations)
    assert any("효과 역할 그룹" in v for v in unmapped.violations)
    assert unmapped.warns


# -- M7(REQ-LDRENDER-013, 교차검증) — 게이트 층 수 vs 독립 AC-001 재계산 --


def _full_cue(
    *,
    cue_number: float,
    name: str,
    key_pct: float,
    role_pct: dict[str, float],
    palette: tuple[str, ...],
    accent_fixture: CueAccentFixtureData | None = None,
) -> ComposedCue:
    return ComposedCue(
        kind="section",
        section_index=1,
        cue_number=cue_number,
        cue_name=name,
        d_level=3,
        fade_seconds=0.0,
        position=CuePositionData(requested=None, stored=None, width_tier=None, source="design"),
        dimmer=CueDimmerData(
            key_pct=key_pct,
            back_pct=role_pct.get("back"),
            budget_range_pct=(0.0, 100.0),
            role_pct=role_pct,
        ),
        color=CueColorData(palette=palette, saturation="full"),
        fx=CueFxData(requested=(), permitted=(), disabled=(), density=0, axis_budget=0),
        accents=(),
        mib=CueMibData(),
        timing=CueTimingData(mode=MANUAL_GO, trigger="manual_go", start_ms=0),
        accent_fixture=accent_fixture,
    )


class _GateCrossValidationBundle:
    """``reviewed_song_commands``가 읽는 한 필드(``cues``)만 채운 대역."""

    def __init__(self, cues: tuple[ComposedCue, ...]) -> None:
        self.cues = cues


#: key=2, back=4, side=7, wash=10, mover=13, effect=14(BLIND 하나만 — 멀티그룹은
#: 위 `test_role_group_map_*`가 별도로 겨눈다) — M4/M5 가 실제로 쓰는 층→색
#: 배정 축(back+mover=지배색, side+wash=보조색, key=웜화이트)을 그대로 재현.
_CROSS_VALIDATION_MAPPING = (
    {"role": "key", "group_no": 2},
    {"role": "back", "group_no": 4},
    {"role": "side", "group_no": 7},
    {"role": "wash", "group_no": 10},
    {"role": "mover", "group_no": 13},
    {"role": "effect", "group_no": 14},
)


def test_gate_layer_count_matches_an_independent_ac001_recount() -> None:
    """AC-LDRENDER-012 집계 동치성의 **종단** 교차검증(M1 은 1개 큐만 손으로
    셌다, §Gaps) — 실제 `reviewed_song_commands()` 출력을 `gate_cues_from_
    commands()`로 판독한 결과가, 입력 데이터(role_pct·palette·accent_fixture)
    에서 **독립적으로** 손으로 유도한 LIT-only 버킷 수와 일치해야 한다.

    큐 1(비액센트) — 손 유도: 베이스라인(dim=60, Blue)이 모든 역할에 먼저
    실리고, side/wash 역할 색 델타(Amber)·key 역할 색 델타(Warm White)·
    back/mover 역할 디머 델타(60, 베이스라인과 같은 값)가 덧씌워진다.
    effect 는 비액센트라 `_effect_dimmer_zero_lines`가 dim=0 으로 내려
    LIT 집계에서 빠진다. 남는 LIT 버킷: key(60,WarmWhite) · back+mover(60,
    Blue) · side+wash(60,Amber) = **3**.

    큐 2(액센트, 같은 effect 그룹을 블라인더로 씀) — 손 유도: 베이스라인
    (dim=80, Red)이 먼저 실리고 side/wash=Cyan·key=WarmWhite 델타가 덧씌워진
    뒤, 액센트 큐라 `_effect_dimmer_zero_lines`가 이 큐의 유일한 effect
    그룹(그 자신이 액센트 대상)을 건너뛰어 effect 의 dim 은 베이스라인(80)
    에 머물다가 `_accent_fixture_value_lines`가 그 위에 dim=90 을 덮어쓴다 —
    effect 의 최종 상태는 (90, Red) 로, back+mover(80, Red) 와 dim 이 달라
    **새 버킷**이 된다. 남는 LIT 버킷: key(80,WarmWhite) · back+mover(80,Red)
    · side+wash(80,Cyan) · effect(90,Red) = **4**.
    """
    blue = _COLOR_NAMES.resolve_color_name("Blue")
    red = _COLOR_NAMES.resolve_color_name("Red")
    assert blue is not None and red is not None

    cue1 = _full_cue(
        cue_number=1.0,
        name="Intro",
        key_pct=60.0,
        role_pct={"back": 60.0, "mover": 60.0},
        palette=("Blue", "Amber"),
    )
    cue2 = _full_cue(
        cue_number=2.0,
        name="Chorus",
        key_pct=80.0,
        role_pct={"back": 80.0, "mover": 80.0},
        palette=("Red", "Cyan"),
        accent_fixture=CueAccentFixtureData(rung="climax accent", group_no=14, dimmer_pct=90.0),
    )
    bundle = _GateCrossValidationBundle((cue1, cue2))

    commands, color_failures = reviewed_song_commands(
        bundle,
        sequence_no=211,
        fids=(1, 2, 3, 4, 5, 6),
        timing=TimingPlan.manual_go(),
        position_slots={},
        phaser_slots={},
        white_presets=None,
        layer_mapping=_CROSS_VALIDATION_MAPPING,
    )
    assert not color_failures, color_failures

    gate_cues = gate_cues_from_commands(
        commands, bundle.cues, layer_mapping=_CROSS_VALIDATION_MAPPING
    )
    result = evaluate(gate_cues, sent_lines=commands)

    # 독립 재계산(§docstring) — 코드 경로를 다시 부르지 않고 입력 데이터에서
    # 직접 유도한 손 집계다.
    independent_recount = {"1": 3, "2": 4}
    for cue_no, lit_count in result.cue_lit_layers:
        assert lit_count == independent_recount[cue_no], (
            f"큐 {cue_no}: 게이트 {lit_count} vs 독립 재계산 {independent_recount[cue_no]}"
        )
    assert result.min_cue_lit_layers == 3


def test_cross_validation_cue_survives_unrelated_field_replace() -> None:
    """교차검증 큐가 `dataclasses.replace`로도 여전히 유효함을 확인 —
    `ComposedCue`가 frozen dataclass 임을 그대로 보인다(픽스처 자체의
    자기-점검, 새 단언 대상 아님)."""
    cue1 = _full_cue(cue_number=1.0, name="Intro", key_pct=60.0, role_pct={}, palette=("Blue",))
    renamed = replace(cue1, cue_name="Intro Renamed")
    assert renamed.cue_name == "Intro Renamed"
    assert renamed.dimmer is cue1.dimmer
