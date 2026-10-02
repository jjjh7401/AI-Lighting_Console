"""SPEC-LDRENDER-001 M6(REQ-LDRENDER-011) — 풀에 없는 카탈로그 페이저 사전 생성.

콘솔 풀 재조회(``phaser_slot_by_label``, ``server/design/console_slots.py``)가
제안된 라벨을 찾지 못하면, 이 모듈이 그 라벨을 ``server/design/phaser_catalog.py``
(30종 카탈로그 — 라벨·스텝·Form·Phase 가 이미 고정된 정본)에서 찾아
``server/fx/instantiate.py`` 의 기존 저작 경로(``build_fx_preset_bundle``/
``select_preset_number``)로 번들을 조립한다. 이 모듈은 콘솔에 아무것도 쓰지
않는다 — 순수 함수만 있다. 호출자(``server/web/session.py``)가 반환된 명령
목록을 **기존** 승인 게이트(``run_commands`` -> ``gate.screen()``)로 보낸다
(plan.md §D "단일 관문 무변경" — 새 무승인 실행 표면을 만들지 않는다).

## [ASSUMPTION -> 측정 확정 -> M6c 해소] 문법 괴리는 스타일이 아니라 빌드 실패였다

``server/web/session.py`` 의 손수 작성한 카탈로그 저장 경로
(``_color_phaser_form_commands``/``_color_phaser_phase_command`` 등, 2026-08-16
핸드오프 §2 로 고정)는 채널 **하나**(``ColorRGB_R`` 또는 ``Dimmer``)에만
Phase·Accel·Decel 줄을 싣는다(독스트링: "레이어는 세트로 저장되므로 한
채널만으로 충분"). ``server/fx/instantiate.py`` 의 표준 경로는 **다른**
문법을 쓸 뿐 아니라, ``_guard_collision``(REQ-FXLIB-011 (a))이 **한 스텝에서
다음 스텝으로 어떤 채널이든 값이 우연히 같으면 번들 조립 자체를 거부한다**
(``server/fx/library/color.yaml`` 자신의 저작 규율 — "EVERY CHANNEL HAS TO
TRAVEL ... that is a real constraint on colour choice and it is worth knowing
it was a decision rather than an accident"). ``phaser_catalog.py`` 의 30종(콤보
10종)은 그 규율을 염두에 두고 고른 색이 **아니다**(손수 작성 경로가 Phase 를
한 채널에만 실어 이 제약을 안 받기 때문) — M6 이 직접 측정(``test_phaser_
pregen.py`` ``TestPregenerateBundle``)으로 확정한 사실: 이 SPEC 이 필요한 5개
라벨 중 ``Wave CM`` 하나만 ``build_fx_preset_bundle`` 로 끝까지 빌드되고,
나머지 넷(``Drop Slam``·``Breathe Cool``·``Finale Slam``·``Breathe Warm``)은
``FxInstantiationError(VALUE_LINE_COLLISION)`` 으로 거부됐다 — 예: "Drop
Slam"(Red@100%→Red@0%)은 두 스텝 모두 ``Attribute 'ColorRGB_R' At 100`` 줄을
내어 충돌했다.

**정정**: 위 "나머지 넷" 목록의 ``Breathe Cool``/``Breathe Warm`` 은 사실
``COMBO_PHASER_SEQUENCE`` 가 아니라 ``COLOR_PHASER_SEQUENCE`` 소속이다(단색
2개만 체이스, 디머 채널 없음) — 충돌은 콤보만의 문제가 아니라 **두 계열
모두에서 "스텝 사이 적어도 한 채널 값이 우연히 같다"는 같은 근본 원인**이
낳은 증상이었다(예: Warm White=(100,75,40) vs Amber=(100,55,5), R 만 같고
G·B 는 다름 — 그래서 R 한 줄만 충돌하고 전체 스텝은 다르다).

**M6c(카드 t501, 리드 결정 C, 2026-10-02)가 저작 쪽에서 처방했다**: ``Fx``
에 ``compound_step_values``(기본 False, 스키마 독스트링 참조) 축을 추가하고,
``_step_lines``(``server/fx/instantiate.py``, 유일한 생산 지점, 손대지 않은
것은 그 함수의 ``_guard_collision`` 호출뿐)가 그 축이 켜졌을 때 한 스텝의
채널 전부를 ``;``-체인 한 줄로 묶어 낸다 — ``Attribute 'x' At Speed 30 ;
Attribute 'y' At Speed 30`` 꼴이 "Wave CM" 으로 실기 ``executed_ok`` 를 받은
``.moai/reports/t501/m6_send_run1/result.json`` 이 그 문법의 근거다. 스텝의
**전체** 값 집합이 텍스트가 되므로, 단 하나의 채널만 달라도(콤보는 디머,
``Breathe Warm``/``Breathe Cool`` 은 나머지 두 색 채널) 두 스텝의 줄이
완전히 달라져 충돌이 사라진다. 이것은 **저작 선택**이지 dedupe 변경이
아니다 — ``_guard_collision`` 자체는 손대지 않았고(REQ-FXLIB-011 (a) 그대로),
여전히 같은 줄이 두 번 나오면 거부한다. M6b 가 시도했던 "``Step`` 경계에서
dedupe 범위를 리셋"하는 처방(브랜치 ``WT-ldrender-m6b-dedupe-abandoned``,
거절됨, SPEC-COPILOT-FXLIB-001 결정 E)과는 다른 축이다.

``pregenerate_phaser_bundle``(아래)이 이 축을 켜는 **유일한** 자리다 — 평범한
폼(오늘, 채널별 한 줄)으로 먼저 빌드를 시도하고, 그 시도가 정확히
``VALUE_LINE_COLLISION`` 으로만 거부될 때 같은 라벨을 ``compound_step_
values=True`` 로 다시 변환해 **한 번만** 재시도한다. 오늘 이미 통과하던
모든 라벨(``Wave CM`` 포함 — 색 계열 10종 중 5종, 디머 계열 10종 전부, 콤보
계열 1종)은 첫 시도에서 성공해 재시도 경로를 타지 않으므로, 그 출력은
**구조적으로** 바이트 동일하다 — 가족 전체에 이 축을 미리 켜는 방식이
아니라, "오늘 거부되는 라벨에만 켠다"는 재시도 순서 자체가 그 보장을 낸다.

처방 결과(``.moai/reports/t501/M6c.md`` 참조): 30종 카탈로그 라벨 **전부**가
이제 ``build_fx_preset_bundle`` 를 통과한다(이전에 거부되던 콤보 9종 + 색
5종, Rain 이 필요한 4개 포함 — 직접 측정, 추측 아님). 카탈로그 값을 바꿔
충돌을 피하는 것(새 RGB 발명)은
여전히 하지 않았다 — §D 제약("표준 팔레트 10색 밖의 RGB 발명 금지")을
그대로 지킨다. 진짜로 완전히 동일한 두 스텝(모든 채널 값이 같음)을 어떤
라벨이 저작하면 compound 줄도 여전히 같아 ``_guard_collision`` 이 여전히
거부한다 — 그 경계는 이 처방이 손대지 않았다.
"""

from __future__ import annotations

from collections.abc import Mapping

from server.design import color_names as _COLOR_NAMES
from server.design.phaser_catalog import (
    _PHASER_LABEL_POOL_NAME,
    COLOR_PHASER_SEQUENCE,
    COMBO_PHASER_SEQUENCE,
    DIMMER_PHASER_SEQUENCE,
)
from server.fx.instantiate import (
    VALUE_LINE_COLLISION,
    FxInstantiation,
    FxInstantiationError,
    build_fx_preset_bundle,
    select_preset_number,
)
from server.fx.schema import Fx, FxStep, StepValue

__all__ = [
    "CATALOG_AUTHORING_GROUP_NO",
    "PhaserPregenError",
    "fx_for_catalog_label",
    "pool_name_for_label",
    "presets_section_from_pool_children",
    "pregenerate_phaser_bundle",
]


class PhaserPregenError(ValueError):
    """라벨이 사전 생성 카탈로그에 없거나, 카탈로그 색 이름을 표준 팔레트에서
    못 찾거나, phase/form 토큰을 해석할 수 없을 때."""


#: `server/orchestrator/tools.py:2037` `LXSEQ_PRESET_APPLY_GROUP_NO = 1` 과
#: 같은 전제(그룹 1 = "All", 리그 전체 대상 그룹) — **저작 시점 스크래치
#: 선택**일 뿐이다. `build_fx_preset_bundle` 이 짓는 프리셋은 `/Universal` 로
#: 저장돼 recall 대상 기구를 제한하지 않으므로(독스트링 참조), 이 상수를
#: 실제 recall 이 겨눌 `fids` 와 혼동하지 마라 — 완전히 무관한 축이다.
CATALOG_AUTHORING_GROUP_NO = 1

_SINE_CURVE = -100.0
_RECTANGLE_CURVE = 0.0


def _color_step_values(color_label: str) -> tuple[StepValue, StepValue, StepValue]:
    rgb = _COLOR_NAMES.resolve_color_name(color_label)
    if rgb is None:
        raise PhaserPregenError(f"색 이름 {color_label!r}을 표준 팔레트에서 찾지 못했습니다")
    r, g, b = rgb
    return (
        StepValue("ColorRGB_R", float(r)),
        StepValue("ColorRGB_G", float(g)),
        StepValue("ColorRGB_B", float(b)),
    )


def _phase_bounds(token: str) -> tuple[float, float | None]:
    """카탈로그 phase 토큰(``"0"``/``"180"``/``"0 Thru 360"``) -> (phase_from,
    phase_to). 세 토큰은 카탈로그가 실제로 쓰는 전부다(``phaser_catalog.py``
    전수 확인) — 그 밖의 토큰은 카탈로그에 없으므로 추측 없이 거부한다."""
    token = token.strip()
    if token == "0":
        return 0.0, None
    if token == "180":
        return 180.0, None
    if token == "0 Thru 360":
        return 0.0, 360.0
    raise PhaserPregenError(f"알 수 없는 페이저 카탈로그 phase 토큰 {token!r}")


def _curve(form: str) -> float:
    if form == "sine":
        return _SINE_CURVE
    if form == "rectangle":
        return _RECTANGLE_CURVE
    raise PhaserPregenError(f"알 수 없는 페이저 카탈로그 form {form!r}")


def _slugify(label: str) -> str:
    return label.lower().replace(" ", "-")


def fx_for_catalog_label(label: str, *, compound_step_values: bool = False) -> Fx:
    """카탈로그 라벨(``phaser_catalog.py`` 30종 중 하나) -> ``Fx``.

    세 계열(컬러/콤보/디머)을 순서대로 찾는다 — 라벨은 세 계열에서 서로소다
    (``_PHASER_LABEL_POOL_NAME`` 생성 규율과 같은 전제). 못 찾으면
    ``PhaserPregenError``(추측 금지 — 새 페이저를 지어내지 않는다).
    모듈 독스트링의 [ASSUMPTION] 문법 괴리가 이 함수의 phase/curve 선택에
    적용된다.

    ``compound_step_values``(M6c, 기본 False) — 그대로 ``Fx.compound_step_
    values``로 전달한다. 기본값에서는 오늘(M6)과 바이트 동일한 Fx 를 낸다 —
    이 축을 켜는 유일한 호출자는 ``pregenerate_phaser_bundle`` 의 충돌-후-재시도
    경로(아래)뿐이다.
    """
    for catalog_label, colors, form, phase_token in COLOR_PHASER_SEQUENCE:
        if catalog_label != label:
            continue
        start, end = _phase_bounds(phase_token)
        curve = _curve(form)
        steps = tuple(FxStep(values=_color_step_values(color)) for color in colors)
        return Fx(
            fx_id=f"pregen-color-{_slugify(label)}",
            display_name=label,
            pattern="chase",
            steps=steps,
            phase_from=start,
            phase_to=end,
            accel=curve,
            decel=curve,
            speed=30.0,
            compound_step_values=compound_step_values,
        )
    for catalog_label, step_pairs, form, phase_token in COMBO_PHASER_SEQUENCE:
        if catalog_label != label:
            continue
        start, end = _phase_bounds(phase_token)
        curve = _curve(form)
        steps = tuple(
            FxStep(values=(*_color_step_values(color), StepValue("Dimmer", float(dimmer_pct))))
            for color, dimmer_pct in step_pairs
        )
        return Fx(
            fx_id=f"pregen-combo-{_slugify(label)}",
            display_name=label,
            pattern="chase",
            steps=steps,
            phase_from=start,
            phase_to=end,
            accel=curve,
            decel=curve,
            speed=30.0,
            compound_step_values=compound_step_values,
        )
    for catalog_label, values, form, phase_token in DIMMER_PHASER_SEQUENCE:
        if catalog_label != label:
            continue
        start, end = _phase_bounds(phase_token)
        curve = _curve(form)
        steps = tuple(FxStep(values=(StepValue("Dimmer", float(value)),)) for value in values)
        return Fx(
            fx_id=f"pregen-dimmer-{_slugify(label)}",
            display_name=label,
            pattern="pulse",
            steps=steps,
            phase_from=start,
            phase_to=end,
            accel=curve,
            decel=curve,
            speed=30.0,
            # a lone-attribute (Dimmer-only) step has nothing to chain — a no-op either way
            compound_step_values=compound_step_values,
        )
    raise PhaserPregenError(f"'{label}'은 사전 생성 카탈로그(30종)에 없는 라벨입니다")


def pool_name_for_label(label: str) -> str:
    """라벨 -> 저장 풀 이름("Color"/"Dimmer"/"All 1") — ``_PHASER_LABEL_POOL_NAME``
    재사용(새 매핑 발명 금지)."""
    pool_name = _PHASER_LABEL_POOL_NAME.get(label)
    if pool_name is None:
        raise PhaserPregenError(f"'{label}' 라벨의 저장 풀 이름을 알 수 없습니다")
    return pool_name


def presets_section_from_pool_children(children: Mapping[int, str | None]) -> dict[str, object]:
    """``paged_pool_children``(완전 판독만 통과 — 절단·실패는 호출자가 먼저
    ``None`` 으로 거른다)의 결과를 ``select_preset_number`` 가 기대하는
    ``presets_section`` 모양(``{"objects": [{"no": int}, ...]}``)으로 옮긴다.
    번호만 필요하므로 이름은 버린다 — 점유 여부는 번호만으로 판정된다."""
    return {"objects": [{"no": slot} for slot in children], "truncated": False}


def pregenerate_phaser_bundle(
    label: str,
    *,
    presets_section: Mapping[str, object],
    preset_pool: int,
    group: int = CATALOG_AUTHORING_GROUP_NO,
    requested_slot: int | None = None,
) -> FxInstantiation:
    """REQ-LDRENDER-011 — 라벨 -> Fx 변환 + 빈 슬롯 측정 + 번들 조립.

    콘솔에 아무것도 보내지 않는 순수 함수다 — 호출자가 반환된
    ``FxInstantiation.commands`` 를 **기존** 승인 게이트(``run_commands`` ->
    ``gate.screen()``)로 보낸다. 번호 충돌은 ``select_preset_number`` 가
    ``FxInstantiationError``(``PRESET_OCCUPIED``/``PRESET_POOL_UNAVAILABLE``/
    ``PRESET_POOL_TRUNCATED``/``PRESET_NUMBER_UNAVAILABLE``, FXLIB 기존
    사유 코드 — REQ-FXLIB-012 (c))로 그대로 전파한다. 새 충돌 검사를 만들지
    않는다(plan.md §D 제약 — ``select_preset_number`` 재사용만).

    M6c(카드 t501, 리드 결정 C) — 오늘(M6)과 같은 평범한 폼(채널별 한 줄씩)으로
    먼저 시도한다. 그 시도가 정확히 ``VALUE_LINE_COLLISION``(``_guard_
    collision``, 손대지 않음)으로 거부될 때만, 같은 ``fx``를 ``compound_step_
    values=True``로 다시 변환해 **한 번만** 재시도한다 — 스텝의 채널 전부를
    한 줄로 묶어 텍스트를 유일하게 만드는 저작 처방(모듈 독스트링 참조).
    오늘 이미 통과하던 라벨(``Wave CM`` 포함)은 첫 시도에서 성공하므로 재시도
    경로를 전혀 타지 않는다 — 바이트 동일이 구조적으로 보장된다. 다른 사유
    (``PRESET_OCCUPIED`` 등)는 그대로 전파한다 — 재시도로 가릴 결함이 아니다.
    """
    # fx_for_catalog_label 먼저 — 모르는 라벨은 풀을 건드리기 전에 거절한다
    # (test_an_unknown_label_refuses_before_touching_the_pool, 순서 보존).
    fx = fx_for_catalog_label(label)
    slot = select_preset_number(presets_section, requested=requested_slot)
    try:
        return build_fx_preset_bundle(
            fx, group=group, preset_pool=preset_pool, preset=slot, label=label
        )
    except FxInstantiationError as error:
        if error.reason != VALUE_LINE_COLLISION:
            raise
        compounded = fx_for_catalog_label(label, compound_step_values=True)
        return build_fx_preset_bundle(
            compounded, group=group, preset_pool=preset_pool, preset=slot, label=label
        )
