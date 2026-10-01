"""SPEC-LDRENDER-001 M6(REQ-LDRENDER-011) — 풀에 없는 카탈로그 페이저 사전 생성.

콘솔 풀 재조회(``phaser_slot_by_label``, ``server/design/console_slots.py``)가
제안된 라벨을 찾지 못하면, 이 모듈이 그 라벨을 ``server/design/phaser_catalog.py``
(30종 카탈로그 — 라벨·스텝·Form·Phase 가 이미 고정된 정본)에서 찾아
``server/fx/instantiate.py`` 의 기존 저작 경로(``build_fx_preset_bundle``/
``select_preset_number``)로 번들을 조립한다. 이 모듈은 콘솔에 아무것도 쓰지
않는다 — 순수 함수만 있다. 호출자(``server/web/session.py``)가 반환된 명령
목록을 **기존** 승인 게이트(``run_commands`` -> ``gate.screen()``)로 보낸다
(plan.md §D "단일 관문 무변경" — 새 무승인 실행 표면을 만들지 않는다).

## [ASSUMPTION -> 측정 확정] 문법 괴리는 스타일이 아니라 빌드 실패다 (M6)

``server/web/session.py`` 의 손수 작성한 카탈로그 저장 경로
(``_color_phaser_form_commands``/``_color_phaser_phase_command`` 등, 2026-08-16
핸드오프 §2 로 고정)는 채널 **하나**(``ColorRGB_R`` 또는 ``Dimmer``)에만
Phase·Accel·Decel 줄을 싣는다(독스트링: "레이어는 세트로 저장되므로 한
채널만으로 충분"). ``server/fx/instantiate.py`` 의 표준 경로는 **다른**
문법을 쓸 뿐 아니라, ``_guard_collision``(REQ-FXLIB-011 (a))이 **한 스텝에서
다음 스텝으로 어떤 채널이든 값이 우연히 같으면 번들 조립 자체를 거부한다**
(``server/fx/library/color.yaml`` 자신의 저작 규율 — "EVERY CHANNEL HAS TO
TRAVEL ... that is a real constraint on colour choice and it is worth knowing
it was a decision rather than an accident"). ``phaser_catalog.py`` 의 30종은
그 규율을 염두에 두고 고른 색이 **아니다**(손수 작성 경로가 Phase 를 한
채널에만 실어 이 제약을 안 받기 때문) — 그래서 직접 측정(``test_phaser_
pregen.py`` ``TestPregenerateBundle``)이 확정한다: 이 SPEC 이 필요한 5개
라벨 중 **``Wave CM`` 하나만** ``build_fx_preset_bundle`` 로 끝까지 빌드되고,
나머지 넷(``Drop Slam``·``Breathe Cool``·``Finale Slam``·``Breathe Warm``)은
``FxInstantiationError(VALUE_LINE_COLLISION)`` 으로 거부된다 — 예: "Drop
Slam"(Red@100%→Red@0%)은 두 스텝 모두 ``Attribute 'ColorRGB_R' At 100`` 줄을
내어 충돌한다. 이것은 **측정된 사실**이지 추측이 아니다.

이 거부는 FXLIB 기존 사유 코드(``VALUE_LINE_COLLISION``)를 그대로 전파하며
(이 모듈이 새 충돌 검사를 만들지 않는다), 호출자(``server/web/session.py``
``_pregenerate_missing_phasers``)가 **거부·보고**(덮어쓰지 않음, 지어내지
않음)로 처리해 ``_phaser_failure_note`` 에 노출한다. 카탈로그 값을 바꿔
충돌을 피하는 것(새 RGB 발명)은 하지 않는다 — §D 제약("표준 팔레트 10색
밖의 RGB 발명 금지")과 "색 값을 조용히 깎지 않는다"는 이 저장소의 반복
원칙을 그대로 지킨다. 처방(카탈로그 색 재선정, 또는 FXLIB 쪽에 "레이어
전체를 한 줄로 묶는" 새 빌더 추가)은 이 SPEC 의 범위를 넘는 결정이라
후속 카드 후보로 남긴다(``.moai/reports/t501/M6.md`` 참조).
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
from server.fx.instantiate import FxInstantiation, build_fx_preset_bundle, select_preset_number
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


def fx_for_catalog_label(label: str) -> Fx:
    """카탈로그 라벨(``phaser_catalog.py`` 30종 중 하나) -> ``Fx``.

    세 계열(컬러/콤보/디머)을 순서대로 찾는다 — 라벨은 세 계열에서 서로소다
    (``_PHASER_LABEL_POOL_NAME`` 생성 규율과 같은 전제). 못 찾으면
    ``PhaserPregenError``(추측 금지 — 새 페이저를 지어내지 않는다).
    모듈 독스트링의 [ASSUMPTION] 문법 괴리가 이 함수의 phase/curve 선택에
    적용된다.
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
    """
    fx = fx_for_catalog_label(label)
    slot = select_preset_number(presets_section, requested=requested_slot)
    return build_fx_preset_bundle(
        fx, group=group, preset_pool=preset_pool, preset=slot, label=label
    )
