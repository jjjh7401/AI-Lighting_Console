"""t501 M6c — 스텝 값 동치 증명: BEFORE(카탈로그 의도) vs AFTER(생성된 명령에서
역파싱) 비교. 콘솔 접촉 0건 — 순수 함수 + 텍스트 파싱만.

이 스크립트가 증명하는 것: M6c 저작 처방(``Fx.compound_step_values``)이 바꾼
것은 스텝의 "텍스트 형태"뿐이고, 스텝이 실제로 담는 값(채널별 숫자)은
카탈로그가 의도한 것과 정확히 같다 — 저작 처방이 무대 결과를 바꾸지 않았다는
증거.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from server.design import color_names
from server.design.phaser_catalog import COLOR_PHASER_SEQUENCE, COMBO_PHASER_SEQUENCE
from server.design.phaser_pregen import (
    pregenerate_phaser_bundle,
    presets_section_from_pool_children,
)

HERE = Path(__file__).resolve().parent
LABELS = ["Drop Slam", "Breathe Warm", "Breathe Cool", "Finale Slam"]

_ATTR_LINE = re.compile(r"Attribute '([A-Za-z_]+)' At (-?\d+(?:\.\d+)?)")
_MODIFIER_MARKERS = (" Phase ", " Speed ", " Accel", " Decel")


def _catalog_before() -> dict[str, list[dict[str, float]]]:
    """카탈로그가 의도한 스텝별 채널 값 — ``phaser_catalog.py`` 정본 그대로."""
    before: dict[str, list[dict[str, float]]] = {}
    for label, colors, _form, _phase in COLOR_PHASER_SEQUENCE:
        if label in LABELS:
            before[label] = [
                dict(
                    zip(
                        ("ColorRGB_R", "ColorRGB_G", "ColorRGB_B"),
                        color_names.resolve_color_name(c),
                        strict=True,
                    )
                )
                for c in colors
            ]
    for label, pairs, _form, _phase in COMBO_PHASER_SEQUENCE:
        if label in LABELS:
            rows = []
            for color, dimmer_pct in pairs:
                r, g, b = color_names.resolve_color_name(color)
                rows.append(
                    {"ColorRGB_R": r, "ColorRGB_G": g, "ColorRGB_B": b, "Dimmer": dimmer_pct}
                )
            before[label] = rows
    return before


def _parse_steps_from_commands(commands: tuple[str, ...]) -> list[dict[str, float]]:
    """생성된 명령 목록에서 스텝 값 줄만 역파싱 — Phase/Speed/Accel/Decel 수정자
    줄은 건너뛴다(이 함수가 겨누는 것은 스텝의 값 집합이지 수정자 축이 아니다).
    압축(``;``-체인) 줄과 평범한(채널별 한 줄) 줄 둘 다 처리한다."""
    steps: list[dict[str, float]] = []
    current: dict[str, float] | None = None
    in_value_region = False
    for command in commands:
        if command in ("ChangeDestination Root", "ClearAll") or command.startswith("Group "):
            continue
        if command == "Step 2":
            if current is not None:
                steps.append(current)
            current = {}
            in_value_region = True
            continue
        if command.startswith(("Store ", "Label ")):
            if current is not None:
                steps.append(current)
            current = None
            break
        if any(marker in command for marker in _MODIFIER_MARKERS):
            continue
        if current is None:
            current = {}
            in_value_region = True
        for part in command.split(" ; "):
            match = _ATTR_LINE.match(part.strip())
            if match:
                attribute, raw_value = match.group(1), float(match.group(2))
                current[attribute] = int(raw_value) if raw_value.is_integer() else raw_value
    if current is not None and in_value_region and current not in steps:
        steps.append(current)
    return steps


def main() -> None:
    section = presets_section_from_pool_children({})
    before = _catalog_before()
    report: list[dict] = []
    all_match = True
    for label in LABELS:
        plan = pregenerate_phaser_bundle(label, presets_section=section, preset_pool=9)
        after_steps = _parse_steps_from_commands(plan.commands)
        rows = []
        paired = enumerate(zip(before[label], after_steps, strict=True), start=1)
        for index, (before_step, after_step) in paired:
            matches = before_step == after_step
            all_match = all_match and matches
            rows.append(
                {"step": index, "before": before_step, "after": after_step, "match": matches}
            )
        report.append({"label": label, "steps": rows})

    output_path = HERE / "m6c_step_value_equivalence.json"
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nALL_STEPS_MATCH={all_match}")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
