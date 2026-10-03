"""t501 M1 — fx.permitted=0 원인 실측 (REQ-LDRENDER-009/AC-LDRENDER-008).

읽기 전용(§C "M1 읽기 전용 경계" — 콘솔 쓰기 0건). 실기 콘솔 접촉 없이, 프로덕션
경로(`server.design.rig_capability_read.read_design_rig` -> `capability_verdict.
patch_records` -> `rig.build_rig_profile`)가 **구조적으로** "effect" 능력을 선언할
수 있는지를 코드 수준에서 대조한다.

측정 방법: Rain 실기 파일럿(t498/t499)이 실측한 BLIND/STROBE/HAZE 그룹(fid 는
readout.py `GROUP_NAMES`/`fid_names.json` 과 동일한 명명)에 대해, 실제 그 기구가
Pan/Tilt/Zoom 뿐 아니라 "Strobe"/"Shutter" 류의 효과성 속성까지 **전부 선언한다고
가정한** `FixtureCapability`(전수 판독, gaps=())를 합성해 `patch_records()`에
통과시킨다. "effect" 가 이 출력에 나타나지 않으면, 그 원인은 "이 리그에 특정
속성이 없어서"가 아니라 "capability_verdict.CAPABILITY_VOCABULARY 자체가 그
능력 이름을 선언하지 않아서"임이 확정된다 — 어떤 실기 패치 데이터를 넣어도
결과가 같다는 뜻이다(코드 판독 결론의 실측 확인).
"""

from __future__ import annotations

import json
from pathlib import Path

from server.design.capability_join import FixtureCapability, RigCapabilities
from server.design.capability_verdict import patch_records
from server.design.energy import EFFECT_AXIS_CAPABILITY
from server.design.rig import build_rig_profile
from server.prechk.capability_read import AxisRange

HERE = Path(__file__).resolve().parent
T499_DIR = HERE.parent / "t499"
FID_NAMES = json.loads((T499_DIR / "fid_names.json").read_text("utf-8"))

#: readout.py GROUP_NAMES 와 같은 명명 — BLIND/STROBE/HAZE 그룹에 속한 fid 전부.
EFFECT_GROUP_PREFIXES = ("BLIND", "STROBE", "HAZE")
effect_fids = [int(fid) for fid, row in FID_NAMES.items() if row["group"] in EFFECT_GROUP_PREFIXES]
print(f"Rain 실측 BLIND/STROBE/HAZE fid {len(effect_fids)}대: {sorted(effect_fids)}")

# 전수 판독(gaps=())으로 합성 — Pan/Tilt(포지션) + Strobe/Shutter(효과성 속성
# 가정)를 **전부** 선언한 기구라고 치자. 그래도 "effect" 가 나오는지 본다.
synthetic_axes = (
    AxisRange(attribute="Pan", channel_name="Pan", physical_from=0.0, physical_to=540.0),
    AxisRange(attribute="Tilt", channel_name="Tilt", physical_from=0.0, physical_to=270.0),
    AxisRange(attribute="Strobe", channel_name="Strobe", physical_from=0.0, physical_to=100.0),
    AxisRange(attribute="Shutter", channel_name="Shutter", physical_from=0.0, physical_to=100.0),
)
fixtures = {
    fid: FixtureCapability(
        fid=fid,
        type_slot=1,
        type_name="SyntheticEffectFixture",
        mode_slot=1,
        mode_name="Mode 1",
        mode_width=16,
        channel_count=16,
        axes=synthetic_axes,
        gaps=(),  # 전수 판독 — 미판독이 아니다
    )
    for fid in effect_fids
}
caps = RigCapabilities(fixtures=fixtures, unread={}, incomplete={})
records = patch_records(caps)
print(f"\npatch_records() 결과 {len(records)}건 중 처음 3건:")
for record in records[:3]:
    print(" ", record)

all_capabilities = {cap for record in records for cap in record["capabilities"]}
print(f"\n이 레코드들에 실제로 실린 capabilities 전체 집합: {sorted(all_capabilities)}")
print(f'"effect" 가 포함되는가: {"effect" in all_capabilities}')

# build_rig_profile() 까지 통과시켜 RigInventory.has_capability("effect") 확인.
rig = build_rig_profile(patch=records, groups={}, coords=[])
has_effect = rig.inventory.has_capability(EFFECT_AXIS_CAPABILITY)
print(f'\nrig.inventory.has_capability("{EFFECT_AXIS_CAPABILITY}") = {has_effect}')
print(f"rig.inventory.capability_fids = {dict(rig.inventory.capability_fids)}")

# energy._fx_axes 가 쓰는 조건 그대로 재현 — fx 예산이 0 이 되는지 직접 확인.
from server.design.energy import _fx_axes  # noqa: E402 — 위 임포트 뒤 조건부 접근

fx_axes_budget_if_nonzero = 10  # §3 D 레벨 표의 임의의 양수 예산
fx_axes = _fx_axes(fx_axes_budget_if_nonzero, rig)
print(
    f"\n_fx_axes(budget={fx_axes_budget_if_nonzero}, rig) = {fx_axes} "
    "(이 리그에 Strobe/Shutter 를 선언하는 기구가 있어도 0)"
)

print("\n=== 결론 ===")
print(
    "Pan/Tilt/Strobe/Shutter 를 전부 선언하는 전수 판독 기구를 합성했는데도 "
    '"effect" 는 capability_fids 에 나타나지 않는다. 원인은 capability_verdict.'
    "CAPABILITY_VOCABULARY 테이블이 'effect' 능력 이름 자체를 선언하지 않기 "
    "때문이다(position/zoom 만 선언) — 어떤 실기 패치를 넣어도 이 결과는 "
    "바뀌지 않는다(구조적 원인, 리그별 개별 결함이 아니다)."
)
