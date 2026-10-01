"""카드 t501 — SPEC-LDRENDER-001 M1, REQ-LDRENDER-013/016.

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
"""

from __future__ import annotations

from server.design.ldrender_gate import (
    SectionCue,
    color_count,
    effect_line_count,
    evaluate,
    layer_diversity,
)

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
