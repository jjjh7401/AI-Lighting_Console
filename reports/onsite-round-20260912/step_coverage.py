"""문서 20 §2 의 12단계를 **모델이 부를 수 있는 도구**에 대고 잰다.

계기 주의: 파일에 단어가 있는 것은 존재의 증거일 뿐 도달의 증거가 아니다.
한 단계가 「닿는다」는 것은 그 일을 하는 도구가 툴셋에 등록돼 있다는 뜻이다.
"""

import re
from pathlib import Path

src = Path("server/orchestrator/tools.py").read_text(encoding="utf-8")
tools = sorted(set(re.findall(r'name="([a-z_]+)"', src)))

STEPS = {
    "1 무대 분석": [
        "get_rig_context",
        "import_lxseq_patch",
        "import_uploaded_sheet",
        "analyse_layout_image",
        "precheck_vectorworks_diff",
    ],
    "2 Patch": [
        "patch_fixtures",
        "precheck_patch",
        "resolve_patch_address",
        "resolve_fixture_type",
        "vectorworks_autopatch",
        "apply_vectorworks_patch",
    ],
    "3 하이브리드 그룹": [
        "arrange_fixtures",
        "classify_arrangement_topology",
        "create_arrangement_groups",
        "import_lxseq_groups",
    ],
    "4 픽셀 튜브 그룹": [],
    "5 틸트 픽셀 바(픽셀 마스터 그룹)": [],
    "6 포지션 프리셋": ["get_spatial_context", "build_preset_list", "import_lxseq_presets"],
    "7 고보/포커스": [],
    "8 빔 프리셋": ["find_fx", "instantiate_fx", "compose_fx"],
    "9 컬러 프리셋": ["find_looks", "instantiate_look", "find_scene", "compile_scene"],
    "10 regen all": [],
    "11 레이아웃 정리": ["plan_executor_layout", "build_magic_sheet"],
    "12 오버라이드": [],
}

print(f"등록된 도구 {len(tools)}개\n")
print(f"{'단계':34} {'닿는 도구':>6}  도구 이름")
hit = 0
for step, names in STEPS.items():
    present = [n for n in names if n in tools]
    if present:
        hit += 1
    mark = "🟢" if present else "—"
    print(f"{step:34} {mark:>6}  {', '.join(present) if present else '(없음)'}")
print(f"\n도구가 닿는 단계: {hit}/12")

missing = [n for names in STEPS.values() for n in names if n not in tools]
print("표에 적었으나 툴셋에 없는 이름:", missing or "없음")
