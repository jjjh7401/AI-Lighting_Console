"""t501 M6 — fx.permitted=0 처방 확인 (REQ-LDRENDER-009 M1 결과 소비,
REQ-LDRENDER-010). 읽기 전용(콘솔 쓰기 0건, 실기 접촉 없음).

M1(`measure_fx_permitted_zero.py`)은 Pan/Tilt/Strobe/Shutter 를 전부 선언한
합성 기구로도 "effect" 가 capability_fids 에 나타나지 않음을 확인해 원인을
`capability_verdict.CAPABILITY_VOCABULARY` 가 "effect" 키 자체를 안 가진
구조적 공백으로 확정했다(M1.md). 이 스크립트는 M6 의 처방(``Dimmer`` ->
``EFFECT_CAPABILITY``, `capability_verdict.py` 참조)을 적용한 뒤 같은 측정을
**실기 실측 채널 표**(t241/verdict.md §2, Rain 8기종 전수 — Strobe/Shutter
가정을 더 이상 쓰지 않는다)로 재현한다.
"""

from __future__ import annotations

import json
from pathlib import Path

from server.design.capability_join import FixtureCapability, RigCapabilities
from server.design.capability_verdict import patch_records
from server.design.energy import EFFECT_AXIS_CAPABILITY, _fx_axes
from server.design.rig import build_rig_profile
from server.prechk.capability_read import AxisRange

HERE = Path(__file__).resolve().parent
T499_DIR = HERE.parent / "t499"
FID_NAMES = json.loads((T499_DIR / "fid_names.json").read_text("utf-8"))

EFFECT_GROUP_PREFIXES = ("BLIND", "STROBE", "HAZE")
effect_fids = {
    int(fid): row["group"]
    for fid, row in FID_NAMES.items()
    if row["group"] in EFFECT_GROUP_PREFIXES
}
print(f"Rain 실측 BLIND/STROBE/HAZE fid {len(effect_fids)}대: {sorted(effect_fids)}")


# t241/verdict.md §2 실측 채널 표(전수 8기종) 중 효과 역할 셋만 — Strobe/Shutter
# 가정 없이, "Dimmer" 보유 여부만으로 fixture 축을 합성한다(M1 의 "전수 판독"
# gaps=() 규율은 유지하되, 선언하는 애트리뷰트만 실측값으로 좁힌다).
#   BLIND  (Elation CUEPIX Blinder WW2): Dimmer ✓ · ColorRGB ✗ · Zoom ✗
#   STROBE (Martin Atomic 3000 LED):     Dimmer ✓ · ColorRGB ✓ · Zoom ✗
#   HAZE   (Look Unique 2.1):            Dimmer ✗ · ColorRGB ✗ · Zoom ✗
def _axis(attribute: str, channel_name: str) -> AxisRange:
    return AxisRange(
        attribute=attribute, channel_name=channel_name, physical_from=0.0, physical_to=100.0
    )


_MEASURED_AXES = {
    "BLIND": (_axis("Dimmer", "Main Module_Dimmer"),),
    "STROBE": (
        _axis("Dimmer", "Aura_Dimmer"),
        _axis("ColorRGB_R", "Aura_ColorRGB_R"),
        _axis("ColorRGB_G", "Aura_ColorRGB_G"),
        _axis("ColorRGB_B", "Aura_ColorRGB_B"),
    ),
    "HAZE": (),  # t241: Dimmer ✗ · ColorRGB ✗ — 효과 그룹 중 유일하게 무능력.
}

fixtures = {
    fid: FixtureCapability(
        fid=fid,
        type_slot={"BLIND": 13, "STROBE": 14, "HAZE": 15}[group],
        type_name={
            "BLIND": "CuePix Blinder WW2",
            "STROBE": "Atomic 3000 LED",
            "HAZE": "Unique 2 1",
        }[group],
        mode_slot=1,
        mode_name="Mode 1",
        mode_width=len(_MEASURED_AXES[group]) or 1,
        channel_count=len(_MEASURED_AXES[group]) or 1,
        axes=_MEASURED_AXES[group],
        gaps=(),  # 전수 판독 — 미판독이 아니다(t241 채널 표가 완전하다)
    )
    for fid, group in effect_fids.items()
}
caps = RigCapabilities(fixtures=fixtures, unread={}, incomplete={})
records = patch_records(caps)
print(f"\npatch_records() 결과 {len(records)}건 중 처음 3건:")
for record in records[:3]:
    print(" ", record)

all_capabilities = {cap for record in records for cap in record["capabilities"]}
print(f"\n이 레코드들에 실제로 실린 capabilities 전체 집합: {sorted(all_capabilities)}")
print(f'"effect" 가 포함되는가: {"effect" in all_capabilities}')

rig = build_rig_profile(patch=records, groups={}, coords=[])
has_effect = rig.inventory.has_capability(EFFECT_AXIS_CAPABILITY)
print(f'\nrig.inventory.has_capability("{EFFECT_AXIS_CAPABILITY}") = {has_effect}')
print(f"rig.inventory.capability_fids = {dict(rig.inventory.capability_fids)}")

fx_axes_budget_if_nonzero = 10
fx_axes = _fx_axes(fx_axes_budget_if_nonzero, rig)
print(
    f"\n_fx_axes(budget={fx_axes_budget_if_nonzero}, rig) = {fx_axes} "
    "(M1 에서는 0 이었다 — 이 리그가 effect 능력을 선언하는 기구(BLIND·STROBE 의 "
    "Dimmer)를 가진 상태로 재측정)"
)

print("\n=== 결론 ===")
if has_effect and fx_axes > 0:
    print(
        'M6 처방 확인됨 — "effect" 가 capability_fids 에 나타나고(BLIND·STROBE 의 '
        'Dimmer 선언으로), has_capability("effect")=True, _fx_axes 가 더 이상 '
        "무조건 0을 돌려주지 않는다(예산이 있으면 양수). HAZE(Dimmer 없음)는 "
        "effect 를 단독 선언하지 못하지만 같은 그룹에 BLIND/STROBE 가 있어 리그 "
        "전체 has_capability 는 True 다."
    )
else:
    print("처방 미확인 — has_effect 또는 fx_axes 가 기대와 다르다. 재검토 필요.")
