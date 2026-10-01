"""t501 M6 — 5절 정지점 산출물: Rain 파일럿 사전 생성 명령(WITHOUT SENDING).

🔴 콘솔 접촉 0건. 실제 콘솔 쓰기는 하지 않는다 — 이 스크립트는
``server.design.phaser_pregen`` 의 순수 함수만 불러 "지금 이 저장 풀 상태로
사전 생성을 실행하면 나갈 명령"을 산출할 뿐이다.

풀 점유 상태의 출처: ``.moai/reports/t469/run3_phaser_pools.txt`` — 실기
`Preset 4`(Color)·`Preset 21`(All 1)·`Preset 1`(Dimmer) 세 풀의 완전 판독
(``state`` 조회, ``truncated: false``, 2026-09(t469) 캡처). **이 트리에
t498 이 남긴 더 구체적인 풀 스냅샷(run0c_meta_pool2page.txt 등)은 Position
풀(2번)만 담고 있어 Color/All 1 풀 점유를 모른다 — t469 의 저장된 읽기가
Color/All 1 둘 다 커버하는 유일한 레코드라 이것을 쓴다.** 보내기 직전에는
반드시 새로 읽어야 한다(아래 `m6_pregen_targets_rain.md` 참조 — 이 상태는
스냅샷일 뿐 지금 이 순간의 점유가 아니다).

M1 측정값(§배차서)대로 각 라벨의 송신 풀은 카탈로그 고정(``_PHASER_LABEL_
POOL_NAME``): Drop Slam/Finale Slam -> All 1(21번), Wave CM/Breathe Cool/
Breathe Warm -> Color(4번).
"""

from __future__ import annotations

import json
from pathlib import Path

from server.design.phaser_pregen import (
    PhaserPregenError,
    pool_name_for_label,
    pregenerate_phaser_bundle,
    presets_section_from_pool_children,
)
from server.fx.instantiate import FxInstantiationError

HERE = Path(__file__).resolve().parent

# t469/run3_phaser_pools.txt verbatim 발췌(§Claim 참조) — 번호(i)만 쓰므로
# 이름은 생략. 캡처 날짜: 그 보고서 자체의 날짜(해당 SPEC t469).
_SAVED_POOL_READS = {
    "Color": {"pool_no": 4, "occupied_slots": [1, 2, 3, 4, 5, 6, 7, 8, 32]},
    "All 1": {"pool_no": 21, "occupied_slots": [1, 2, 3, 4, 5, 6]},
}

# Rain 의 설계 층이 실제로 제안하는 5개 라벨(coordinator 매핑 표 — 절정/
# 클라이맥스/피크=Drop Slam, 후렴=Wave CM, 벌스=Breathe Warm, 브리지/
# 간주=Breathe Cool, 피날레/아웃트로/엔딩=Finale Slam). t498/t499 Rain
# 구조가 다섯 섹션 역할(intro/verse/chorus/bridge/finale)을 전부 쓴다
# (`.moai/reports/t499/verdict.md` 8곡 구조표 참조).
_RAIN_NEEDED_LABELS = ("Drop Slam", "Wave CM", "Breathe Warm", "Breathe Cool", "Finale Slam")

targets: list[dict] = []
command_file_lines: list[str] = []

for label in _RAIN_NEEDED_LABELS:
    pool_name = pool_name_for_label(label)
    saved = _SAVED_POOL_READS[pool_name]
    presets_section = presets_section_from_pool_children(dict.fromkeys(saved["occupied_slots"], ""))
    entry = {
        "label": label,
        "pool_name": pool_name,
        "pool_no": saved["pool_no"],
        "evidence_file": ".moai/reports/t469/run3_phaser_pools.txt",
        "evidence_captured": "t469 (pre-t501)",
        "occupied_slots_at_capture": saved["occupied_slots"],
    }
    try:
        plan = pregenerate_phaser_bundle(
            label, presets_section=presets_section, preset_pool=saved["pool_no"]
        )
    except (PhaserPregenError, FxInstantiationError) as error:
        reason = getattr(error, "reason", "phaser_pregen_error")
        entry["result"] = "REFUSED"
        entry["refusal_reason_code"] = reason
        entry["refusal_detail"] = str(error)
        command_file_lines.append(f"# {label} -> REFUSED ({reason}): {error}")
    else:
        entry["result"] = "WOULD_SEND"
        entry["target_slot"] = plan.preset
        entry["commands"] = list(plan.commands)
        command_file_lines.append(f"# {label} -> Preset {saved['pool_no']}.{plan.preset}")
        command_file_lines.extend(plan.commands)
    command_file_lines.append("")
    targets.append(entry)

commands_path = HERE / "m6_pregen_commands_rain.txt"
commands_path.write_text("\n".join(command_file_lines), encoding="utf-8")

print(json.dumps(targets, ensure_ascii=False, indent=2))
print(f"\nwrote {commands_path}")
