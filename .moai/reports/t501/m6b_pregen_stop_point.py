"""t501 M6b — 5절 정지점 산출물 재생성: Step 경계 dedupe 완화 이후 (WITHOUT SENDING).

🔴 콘솔 접촉 0건. ``m6_pregen_stop_point.py``와 같은 기계로, 풀 점유 증거만
갱신한 버전이다 — M6b 가 ``run_commands`` 중복 제거 범위를 ``Step <n>``
경계에서 리셋하도록 좁히고(카드 t501, 2026-10-02 리드 결정) FXLIB
``_guard_collision``을 그에 맞춰 완화한 뒤로는, 5개 필요 라벨 전부가 이
경로로 빌드된다(Wave CM 은 M6 당시에도 빌드됐다 — 변한 것은 나머지 4개).

풀 점유 상태의 출처(갱신, M6b):
  - Color(4번): ``.moai/reports/t501/m6_postsend_reread_20261002.txt`` —
    Wave CM 이 이미 실기에 전송돼 **slot 9 를 점유**한 상태의 실측 재조회
    (``state`` 조회, ``truncated: false``, 2026-10-02 캡처). 점유:
    1,2,3,4,5,6,7,8,9,32.
  - All 1(21번): ``.moai/reports/t501/m6_pool_reread_readonly.txt`` — 읽기
    전용 재조회(2026-10-02). 점유: 1,2,3,4,5,6.

레인 정정(2026-10-02): 처음 판은 5개 라벨을 서로 독립으로 계산해 Wave CM
재송신과 번호 중복 제안(4.10 ×3, 21.7 ×2)을 냈다. 지금 판은 앱과 같은 순서
(``sorted``)·누적 점유로 계산하고, 실기에 이미 있는 Wave CM(4.9)은 보내지
않는다. 전송 직전 재조회는 여전히 필수다.
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

# 갱신된 풀 점유(§모듈 독스트링) — Color(4)는 Wave CM 전송 이후 재조회,
# All 1(21)은 읽기 전용 재조회.
_SAVED_POOL_READS = {
    "Color": {
        "pool_no": 4,
        "occupied_slots": [1, 2, 3, 4, 5, 6, 7, 8, 9, 32],
        "evidence_file": ".moai/reports/t501/m6_postsend_reread_20261002.txt",
        "evidence_captured": "2026-10-02 (M6, Wave CM 전송 직후 재조회)",
    },
    "All 1": {
        "pool_no": 21,
        "occupied_slots": [1, 2, 3, 4, 5, 6],
        "evidence_file": ".moai/reports/t501/m6_pool_reread_readonly.txt",
        "evidence_captured": "2026-10-02 (읽기 전용 재조회)",
    },
}

_RAIN_NEEDED_LABELS = ("Drop Slam", "Wave CM", "Breathe Warm", "Breathe Cool", "Finale Slam")

# 레인 정정(t501, 2026-10-02): 앱(`session.py::_pregenerate_missing_phasers`)은
# 풀에 이미 있는 라벨은 건너뛰고(`pending` 은 `failed` 에 남은 라벨만), 남은
# 라벨을 `sorted()` 순서로 하나씩 처리하며 라벨마다 풀을 **다시 읽는다** — 앞
# 라벨이 Store 한 번호는 다음 라벨에서 점유로 보인다. 독립 계산은 Wave CM 재송신
# (4.10)과 같은 번호 중복 제안(4.10 ×3, 21.7 ×2)을 냈으므로, 같은 순서·같은
# 누적 점유로 흉내 낸다. Wave CM 은 실기 Preset 4.9 로 이미 존재한다
# (m6_postsend_reread_20261002.txt).
_ALREADY_ON_CONSOLE = {"Wave CM": (4, 9)}

targets: list[dict] = []
command_file_lines: list[str] = []
occupied = {name: list(saved["occupied_slots"]) for name, saved in _SAVED_POOL_READS.items()}

for label in sorted(_RAIN_NEEDED_LABELS):
    if label in _ALREADY_ON_CONSOLE:
        pool_no, slot = _ALREADY_ON_CONSOLE[label]
        targets.append(
            {"label": label, "result": "ALREADY_ON_CONSOLE", "preset": f"{pool_no}.{slot}"}
        )
        command_file_lines.append(f"# {label} -> 이미 실기 Preset {pool_no}.{slot} (보내지 않음)")
        command_file_lines.append("")
        continue
    pool_name = pool_name_for_label(label)
    saved = _SAVED_POOL_READS[pool_name]
    presets_section = presets_section_from_pool_children(dict.fromkeys(occupied[pool_name], ""))
    entry = {
        "label": label,
        "pool_name": pool_name,
        "pool_no": saved["pool_no"],
        "evidence_file": saved["evidence_file"],
        "evidence_captured": saved["evidence_captured"],
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
        entry["line_count"] = len(plan.commands)
        entry["commands"] = list(plan.commands)
        entry["has_step_2_marker"] = "Step 2" in plan.commands
        step1_count = (
            plan.commands.index("Step 2") if "Step 2" in plan.commands else len(plan.commands)
        )
        entry["step1_value_line_count"] = sum(
            1
            for c in plan.commands[3:step1_count]
            if c.startswith("Attribute '") and " At " in c and "Phase" not in c and "Speed" not in c
        )
        command_file_lines.append(f"# {label} -> Preset {saved['pool_no']}.{plan.preset}")
        command_file_lines.extend(plan.commands)
        occupied[pool_name].append(plan.preset)
    command_file_lines.append("")
    targets.append(entry)

commands_path = HERE / "m6b_pregen_commands_rain.txt"
commands_path.write_text("\n".join(command_file_lines), encoding="utf-8")

output_path = HERE / "m6b_pregen_stop_point_output.json"
output_path.write_text(json.dumps(targets, ensure_ascii=False, indent=2), encoding="utf-8")

print(json.dumps(targets, ensure_ascii=False, indent=2))
print(f"\nwrote {commands_path}")
print(f"wrote {output_path}")
