"""t501 M6c — 5절 정지점 산출물 재생성: 저작 처방 후 Rain 4개 라벨(WITHOUT SENDING).

🔴 콘솔 접촉 0건. 실제 콘솔 쓰기는 하지 않는다 — 이 스크립트는
``server.design.phaser_pregen`` 의 순수 함수만 불러 "지금 이 저장 풀 상태로
사전 생성을 실행하면 나갈 명령"을 산출할 뿐이다. 번호는 모두 실제로 계산한다
(하드코드 금지) — ``select_preset_number`` 가 공석 번호를 직접 측정한다.

``Wave CM`` 은 이미 실기 콘솔에 Preset 4.9 로 저장돼 있다(배차서: "Wave CM is
on the console as 4.9 and must NOT be sent") — 이 스크립트는 그 라벨을
**다시 계산하지 않는다**. M6 이 거부했던 나머지 4개(``Drop Slam``/``Breathe
Warm``/``Breathe Cool``/``Finale Slam``)만 겨눈다 — M6c 의 저작 처방
(``Fx.compound_step_values`` + ``pregenerate_phaser_bundle`` 의 충돌-후-재시도,
``server/design/phaser_pregen.py`` 모듈 독스트링 참조) 뒤 전부 WOULD_SEND 로
바뀌었는지 확인하는 것이 이 카드의 목적이다.

풀 점유 상태의 출처(배차서가 지정한 두 증거 파일, 둘 다 M6 Wave CM 송신 이후
읽기 전용 재조회):
  - Color(4번): ``.moai/reports/t501/m6_postsend_reread_20261002.txt``
    (``Preset 4.9 'Wave CM'`` 송신 **직후** 읽기 전용 재조회 — 1-9, 32 점유).
  - All 1(21번): ``.moai/reports/t501/m6_pool_reread_readonly.txt``
    (M6 송신 **직전** 읽기 전용 재조회 — All 1 풀은 아무것도 저장하지 않았으므로
    그 이후로도 값이 바뀔 사유가 없다 — 1-6 점유).

앱의 ``_pregenerate_missing_phasers``(``server/web/session.py``)는 대기 중인
라벨을 ``sorted()`` 순서로 처리하고, 라벨마다 풀을 다시 읽는다 — 그래서 같은
풀을 쓰는 라벨들 사이에서 번호가 누적된다(한 라벨이 쓴 슬롯이 다음 라벨
차례에는 이미 점유된 것으로 보인다). 콘솔에 실제로 쓰지 않으므로, 이
스크립트는 그 누적을 **로컬 변수**로 흉내 낸다: 한 라벨이 계산한 target slot
을 그 풀의 점유 집합에 더해 다음 라벨 계산에 반영한다(§배차서 "app's
_pregenerate_missing_phasers processes pending labels in sorted() order and
re-reads the pool per label, so slots accumulate").
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

# 두 증거 파일 verbatim 발췌(모듈 독스트링 참조) — 번호(i)만 쓰므로 이름은
# 생략. 둘 다 M6 Wave CM 송신 이후(또는 송신에 영향받지 않는) 읽기 전용
# 재조회다.
_SAVED_POOL_READS = {
    "Color": {
        "pool_no": 4,
        "occupied_slots": [1, 2, 3, 4, 5, 6, 7, 8, 9, 32],
        "evidence_file": ".moai/reports/t501/m6_postsend_reread_20261002.txt",
        "evidence_captured": "M6 Wave CM 송신 직후 읽기 전용 재조회(2026-10-02)",
    },
    "All 1": {
        "pool_no": 21,
        "occupied_slots": [1, 2, 3, 4, 5, 6],
        "evidence_file": ".moai/reports/t501/m6_pool_reread_readonly.txt",
        "evidence_captured": "M6 Wave CM 송신 직전 재조회 — All 1 은 안 썼으므로 불변",
    },
}

# M6 이 거부했던 4개 라벨(Rain 이 필요한 5개 중 Wave CM 제외) — sorted() 순서가
# 앱의 처리 순서(server/web/session.py `_pregenerate_missing_phasers`).
_PENDING_LABELS = sorted(["Drop Slam", "Breathe Warm", "Breathe Cool", "Finale Slam"])

# 라벨마다 다시 읽을 "현재 점유 집합" — 누적 시뮬레이션(모듈 독스트링 참조).
_accumulated_occupied: dict[str, list[int]] = {
    pool_name: list(data["occupied_slots"]) for pool_name, data in _SAVED_POOL_READS.items()
}

targets: list[dict] = []
command_file_lines: list[str] = []

for label in _PENDING_LABELS:
    pool_name = pool_name_for_label(label)
    pool_no = _SAVED_POOL_READS[pool_name]["pool_no"]
    occupied_now = _accumulated_occupied[pool_name]
    presets_section = presets_section_from_pool_children(dict.fromkeys(occupied_now, ""))
    entry = {
        "label": label,
        "pool_name": pool_name,
        "pool_no": pool_no,
        "evidence_file": _SAVED_POOL_READS[pool_name]["evidence_file"],
        "evidence_captured": _SAVED_POOL_READS[pool_name]["evidence_captured"],
        "occupied_slots_at_this_step": list(occupied_now),
    }
    try:
        plan = pregenerate_phaser_bundle(
            label, presets_section=presets_section, preset_pool=pool_no
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
        command_file_lines.append(f"# {label} -> Preset {pool_no}.{plan.preset}")
        command_file_lines.extend(plan.commands)
        # 누적: 이 라벨이 잡은 슬롯을 그 풀의 점유 집합에 더해 다음 라벨의
        # 계산에 반영한다(앱의 라벨마다-재조회 동작 시뮬레이션).
        _accumulated_occupied[pool_name].append(plan.preset)
    command_file_lines.append("")
    targets.append(entry)

commands_path = HERE / "m6c_pregen_commands_rain.txt"
commands_path.write_text("\n".join(command_file_lines), encoding="utf-8")

output_path = HERE / "m6c_pregen_stop_point_output.json"
output_path.write_text(json.dumps(targets, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(json.dumps(targets, ensure_ascii=False, indent=2))
print(f"\nwrote {commands_path}")
print(f"wrote {output_path}")
