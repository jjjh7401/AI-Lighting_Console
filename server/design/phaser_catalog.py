"""페이저 프리셋 카탈로그 30종과 라벨 → 풀 이름 표.

카드 t480(SPEC-LDDESIGN-001 REQ-003) — 원래 ``server/web/session.py`` 에 있었다.
업로드 길(``server/orchestrator/tools.py``)도 조립기 큐의 페이저 라벨을 콘솔 슬롯으로
찾아야 하는데, 그 길은 층 경계 때문에 ``server.web`` 을 import 할 수 없다. 값은 한 글자도
바꾸지 않고 자리만 옮겼다.
"""

from __future__ import annotations

#: 멀티컬러 페이저 프리셋 10종 카탈로그 — `docs/handoff/2026-08-16-session-
#: handoff.md` §2 표 그대로 고정(라벨·스텝·Form·Phase 순서가 계약). 슬롯 1은
#: 항상 'Breathe Warm'이고 재생성 가족 필터의 first_label이 된다(팔레트·
#: 포지션·FX와 같은 규율). 각 원소: (라벨, 스텝 순서의 팔레트 라벨들,
#: Form("sine"|"rectangle"), Phase 커맨드 토큰).
COLOR_PHASER_SEQUENCE: tuple[tuple[str, tuple[str, ...], str, str], ...] = (
    ("Breathe Warm", ("Warm White", "Amber"), "sine", "0"),
    ("Breathe Cool", ("Cool White", "Blue"), "sine", "0"),
    ("Chase RB", ("Red", "Blue"), "rectangle", "0"),
    ("Chase CM", ("Cyan", "Magenta"), "rectangle", "0"),
    ("Wave CM", ("Cyan", "Magenta"), "sine", "0 Thru 360"),
    ("Wave WA", ("Warm White", "Amber"), "sine", "0 Thru 360"),
    ("Rainbow", ("Red", "Green", "Blue"), "sine", "0 Thru 360"),
    ("Pulse RY", ("Red", "Yellow"), "sine", "0"),
    ("Duo GL", ("Green", "Lavender"), "sine", "180"),
    ("Slam RW", ("Red", "Warm White"), "rectangle", "0 Thru 360"),
)


#: 디머 페이저 프리셋 10종 — T5 카탈로그(코디네이터 지시 고정, T4 프로브
#: `09-dimmer-phaser-m0-probe.md`가 확인한 문법만 사용). 각 원소: (라벨,
#: 스텝 순서의 디머 값(%)들, Form("sine"|"rectangle"), Phase 커맨드 토큰).
#: 슬롯 1은 항상 'Breathe Soft'이고 재생성 가족 필터의 first_label이 된다.
DIMMER_PHASER_SEQUENCE: tuple[tuple[str, tuple[int, ...], str, str], ...] = (
    ("Breathe Soft", (30, 70), "sine", "0"),
    ("Breathe Deep", (10, 90), "sine", "0"),
    ("Pulse Hard", (0, 100), "rectangle", "0"),
    ("Pulse Half", (30, 100), "rectangle", "0"),
    ("Wave Soft", (30, 70), "sine", "0 Thru 360"),
    ("Wave Full", (0, 100), "sine", "0 Thru 360"),
    ("Ripple", (30, 60, 100), "sine", "0 Thru 360"),
    ("Flash Accent", (100, 20), "rectangle", "0"),
    ("Alt Half", (50, 100), "sine", "180"),
    ("Slam Run", (0, 100), "rectangle", "0 Thru 360"),
)


#: 콤보(컬러+디머 혼합) 페이저 프리셋 10종 — T8 카탈로그(코디네이터 지시
#: 고정, T7 프로브 ``10-combo-phaser-m0-probe.md``가 확인한 저장 풀만
#: 사용). 각 원소: (라벨, 스텝 순서의 (팔레트 라벨, 디머%) 쌍들,
#: Form("sine"|"rectangle"), Phase 커맨드 토큰). 슬롯 1은 항상 'Drop Slam'
#: 이고 재생성 가족 필터의 first_label이 된다(팔레트·포지션·컬러·디머와
#: 같은 규율). Rectangle 근사는 ``_color_phaser_form_commands``/
#: ``_dimmer_phaser_form_commands``와 동일한 ASSUMPTION(공식 수치 없음)을
#: 상속한다.
COMBO_PHASER_SEQUENCE: tuple[tuple[str, tuple[tuple[str, int], ...], str, str], ...] = (
    ("Drop Slam", (("Red", 100), ("Red", 0)), "rectangle", "0"),
    ("Breathe Amber", (("Warm White", 70), ("Amber", 30)), "sine", "0"),
    ("Breathe Blue", (("Cool White", 60), ("Blue", 25)), "sine", "0"),
    ("Police", (("Red", 100), ("Blue", 100)), "rectangle", "0"),
    ("Heartbeat", (("Red", 90), ("Red", 15)), "sine", "0"),
    ("Golden Wave", (("Amber", 100), ("Warm White", 40)), "sine", "0 Thru 360"),
    ("Ocean Wave", (("Cyan", 90), ("Blue", 30)), "sine", "0 Thru 360"),
    (
        "Rainbow Run",
        (("Red", 100), ("Green", 50), ("Blue", 100)),
        "sine",
        "0 Thru 360",
    ),
    ("Club Duo", (("Magenta", 100), ("Cyan", 40)), "rectangle", "180"),
    ("Finale Slam", (("Warm White", 100), ("Red", 0)), "rectangle", "0 Thru 360"),
)


# 페이저 recall(T11) — 저장된 카탈로그 30종(컬러/디머/콤보 페이저)을
# 소비(즉시 발사·해제·시퀀스화)하는 어휘. 저장·재생성 가족은 포괄 어휘축
# (멀티컬러/디머 이펙트/콤보 등)으로 문장을 매치하고, 여기는 반대로 라벨
# 자체(예: 'Breathe Warm')가 문장에 있어야만 발동한다 — 두 축이 사용하는
# 토큰 집합이 겹치지 않으므로(저장 문장에는 카탈로그 라벨이 없다) 디스패치
# 등록 순서를 저장·재생성 가족들보다 뒤에 둬도 그 문장들을 삼키지 않는다.
_PHASER_LABEL_POOL_NAME: dict[str, str] = {
    **{label: "Color" for label, *_ in COLOR_PHASER_SEQUENCE},
    **{label: "Dimmer" for label, *_ in DIMMER_PHASER_SEQUENCE},
    **{label: "All 1" for label, *_ in COMBO_PHASER_SEQUENCE},
}
