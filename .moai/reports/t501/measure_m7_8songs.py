"""카드 t501 M7 — 마일스톤 측정(재구성, analysis.json 재생). 리드 결정
(2026-10-02) — "M7 마일스톤 측정은 analysis.json 재생을 써도 되지만, **최종
오프라인 판정(카드의 5개 조건)은 실제 음원 DSP 재생 경로**로 해야 한다"는
요구를 분리한다 — 이 스크립트는 전자("M7 마일스톤 측정(재구성)")만 수행한다.
`measure_m7_dsp_8songs.py`(실제 음원 DSP 경로)가 "최종 오프라인 판정"을
별도로 낸다.

`measure_ac001_8songs.rehearse()`(M3/M4/M5/M6 재사용, DSP 재실행 없음)를
그대로 쓰되, 이 트리의 가짜 콘솔이 두 가지를 공급하지 않아 M6 가 이미
명시한 하네스 한계(§Gaps, M6.md)를 이 카드가 메운다:

1. **능력 판독** — `ChatSession._try_rig_capabilities()`가 `Patch/Stages/1/
   Fixtures`를 못 읽어(`RuntimeError: path segment not found`) 항상 빈
   `DesignRigRead`를 돌려줬다(모든 곡 `fx.permitted=0`, M6.md "하네스 한계"
   절). 이 카드는 `ChatSession._try_rig_capabilities`를 **읽기 전용 저장된
   실기 패치 증거**로 몽키패치한다 — fid 목록은
   `.moai/reports/t498/run3_rain_real_denyall/approval_request_1.txt`(86개,
   `measure_ac001_8songs.REAL_FIDS`와 바이트 동일, 교차검증 완료), 기종/능력은
   `.moai/reports/t498/run4_fixture_names.txt`(FID→FixtureType 조인) +
   `.moai/reports/t241/verdict.md` §2(기종별 Dimmer 채널 표, "Dimmer 84/86 —
   HAZE 2대만 없음")다. `capability_verdict.CAPABILITY_VOCABULARY`(M6)의
   `EFFECT_CAPABILITY: (DIMMER_ATTRIBUTE,)` 그대로 — Dimmer 채널이 있으면
   "effect" 능력을 선언한다(추측 아님, 실측 채널표 재사용).
2. **페이저 풀 상태** — 가짜 콘솔이 `DataPool/PresetPools`(루트)·`/4`(Color)·
   `/21`(All 1)을 전혀 모른다(`RuntimeError`). 이 카드는 그 세 경로를
   **저장된 읽기 전용 실기 증거**로 공급한다 — 루트 풀 목록은
   `.moai/reports/t216/console-presetpools-state.json`(14개 풀, 이름→번호
   안정적 — 운영자가 잘 안 바꾸는 값), 풀 4/21 의 **현재** 내용은
   `.moai/reports/t501/m6c_postsend_reread.txt`(이 SPEC 의 M6c 가 2026-10-02
   에 실기로 4종 페이저를 실제로 저장한 **직후** 재조회 — Wave CM=4.9,
   Breathe Cool=4.10, Breathe Warm=4.11, Drop Slam=21.7, Finale Slam=21.8).
   이 카드 자신은 콘솔에 **쓰지 않는다** — 이미 쓰여 있는 결과를 읽기만
   한다(배차서 "NO CONSOLE CONTACT" 그대로 준수).

콘솔 접촉: 0건(in-process FakeConsole, t499/M1~M6 와 동일한 하네스 계열).

실행: uv run python .moai/reports/t501/measure_m7_8songs.py
출력: 표준출력 + .moai/reports/t501/measure_m7_8songs.json
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import measure_ac001_8songs as m  # noqa: E402
import measure_m5_8songs as m5  # noqa: E402

from server.design.rig_capability_read import DesignRigRead
from server.web.session import ChatSession

HERE = Path(__file__).resolve().parent
T498 = HERE.parent / "t498"
T241 = HERE.parent / "t241"
T216 = HERE.parent / "t216"

# -- 1. 능력 판독 몽키패치 재료 (읽기 전용 실기 증거) ------------------------

_NAME_PROP_FILE = T498 / "run4_fixture_names.txt"
_PROP_BLOCK = re.compile(r'<<< (\{.*?"v": 1\})\s*$', re.M)


def _real_patch_records() -> tuple[dict[str, object], ...]:
    """`.moai/reports/t498/run4_fixture_names.txt`(86개 FID/Name/FixtureType/
    Mode 실측) → `build_rig_profile(patch=...)` 레코드. HAZE 2대(621/622,
    `.moai/reports/t241/verdict.md` §2 "Dimmer ✗" 실측)만 "effect" 능력을
    못 받는다 — 나머지 84대는 전부 Dimmer 채널이 있다(§2 "Dimmer 84/86")."""
    text = _NAME_PROP_FILE.read_text("utf-8")
    records: list[dict[str, object]] = []
    haze_fids = set()
    for block in _PROP_BLOCK.finditer(text):
        data = json.loads(block.group(1))
        reads = {r["n"]: r["v"] for r in data["reads"]}
        fid = int(reads["FID"])
        name = str(reads["Name"])
        type_name = str(reads["FixtureType"])
        if name.startswith("HAZE"):
            haze_fids.add(fid)
        records.append({"fid": fid, "type_name": type_name, "capabilities": ["effect"]})
    assert len(records) == 86, len(records)
    assert haze_fids == {621, 622}, haze_fids
    haze_records = tuple(
        {"fid": fid, "type_name": "Look Unique 2.1", "capabilities": []}
        for fid in sorted(haze_fids)
    )
    return tuple(r for r in records if r["fid"] not in haze_fids) + haze_records


_REAL_PATCH_RECORDS = _real_patch_records()


def _patched_try_rig_capabilities(self: ChatSession) -> DesignRigRead:  # noqa: ARG001
    return DesignRigRead(
        attempted=True, patch=_REAL_PATCH_RECORDS, capabilities=None, gap="", detail=""
    )


# -- 2. 페이저 풀 상태 몽키패치 재료 (읽기 전용 실기 증거) -------------------

_PRESET_POOLS_ROOT = json.loads(T216.joinpath("console-presetpools-state.json").read_text("utf-8"))


def _pool_payload_from_m6c(pool_no: int) -> dict:
    """`.moai/reports/t501/m6c_postsend_reread.txt`의 해당 풀 블록을 그대로
    판독(저장된 읽기, 새 조회 0건) — M6c 가 2026-10-02 에 4종 페이저를 실기에
    저장한 직후 재조회한 "지금 이 순간"에 가장 가까운 증거."""
    text = (HERE / "m6c_postsend_reread.txt").read_text("utf-8")
    for block in re.finditer(r"<<< (\{.*?\"v\": 1\})", text):
        data = json.loads(block.group(1))
        if data.get("path") == f"ShowData/DataPools/Default/PresetPools/{pool_no}":
            return data
    raise AssertionError(f"pool {pool_no} not found in m6c_postsend_reread.txt")


_POOL_4_COLOR = _pool_payload_from_m6c(4)
_POOL_21_ALL1 = _pool_payload_from_m6c(21)
assert {c["name"] for c in _POOL_4_COLOR["children"]} >= {"Wave CM", "Breathe Cool", "Breathe Warm"}
assert {c["name"] for c in _POOL_21_ALL1["children"]} >= {"Drop Slam", "Finale Slam"}

_PATCHED_POOL_PATHS = {
    "DataPool/PresetPools": _PRESET_POOLS_ROOT,
    "DataPool/PresetPools/4": _POOL_4_COLOR,
    "DataPool/PresetPools/21": _POOL_21_ALL1,
}


def _patch_console_query_state() -> None:
    """`measure_ac001_8songs._Console.query_state`에 풀 경로 셋을 추가한다
    (클래스 메서드 재정의 — 모듈 수준 1회, M3~M6 산출물은 건드리지 않는다).
    기존 분기(Position 풀·Groups·Sequences·Timecodes)는 한 글자도 안 바꾼다."""
    original = m._Console.query_state

    def patched(self, path: str) -> dict:
        self.queried.append(path)
        if path in _PATCHED_POOL_PATHS:
            return _PATCHED_POOL_PATHS[path]
        return original(self, path)

    m._Console.query_state = patched


# -- 3. rehearse() 변형 — gate 결과도 함께 돌려준다 --------------------------


def rehearse_with_gate(song_name: str, analysis_path: Path) -> dict:
    """`measure_ac001_8songs.rehearse()`와 바이트 동일한 몸통 +
    `session._last_gate_result`(M7 프로덕션 배선이 실제로 계산한 값, 이
    스크립트가 다시 계산하지 않는다) 캡처만 추가한다."""
    original_try_rig = ChatSession._try_rig_capabilities
    captured_gate: list[object] = []
    original_finalize = ChatSession._song_finalize

    def _recording_finalize(self, *args, **kwargs):
        result = original_finalize(self, *args, **kwargs)
        captured_gate.append(self._last_gate_result)
        return result

    ChatSession._try_rig_capabilities = _patched_try_rig_capabilities
    ChatSession._song_finalize = _recording_finalize
    try:
        result = m.rehearse(song_name, analysis_path)
    finally:
        ChatSession._try_rig_capabilities = original_try_rig
        ChatSession._song_finalize = original_finalize
    result["gate_result"] = captured_gate[-1] if captured_gate else None
    return result


def main() -> None:
    _patch_console_query_state()
    analysis_files = sorted((m.T499 / "runs").glob("*/analysis.json"))
    analysis_files = [p for p in analysis_files if p.parent.name != "Rain_first"]
    assert len(analysis_files) == 8, [p.parent.name for p in analysis_files]

    summary = []
    for analysis_path in analysis_files:
        song_name = analysis_path.parent.name
        result = rehearse_with_gate(song_name, analysis_path)
        commands = result["commands"]
        bundle_cues = {c.cue_number: c for c in result["bundle_cues"]}
        gate_result = result["gate_result"]

        # 카드의 5개 오프라인 조건, 전부 M7 프로덕션 배선이 낸 gate_result +
        # M5 가 쓰던 effect-상태 판독(readout.py state-tracker, fid_names.json
        # group 배선 재사용 — 능력 축과 무관한 별개 판독)에서 뽑는다.
        effect_rows = m5._effect_states_per_cue(commands)
        non_accent_violations = {name: 0 for name in m5._EFFECT_GROUPS.values()}
        non_accent_cue_count = 0
        accent_rows = []
        prev_dims = {name: None for name in m5._EFFECT_GROUPS.values()}
        for row in effect_rows:
            try:
                cue_no_float = float(row["cue_no"])
            except ValueError:
                prev_dims = {name: row[name] for name in m5._EFFECT_GROUPS.values()}
                continue
            composed = bundle_cues.get(cue_no_float)
            is_accent_cue = composed is not None and composed.accent_fixture is not None
            if is_accent_cue:
                accent_group_name = m5._EFFECT_GROUPS.get(composed.accent_fixture.group_no)
                if accent_group_name is not None:
                    before = prev_dims[accent_group_name]
                    after = row[accent_group_name]
                    accent_rows.append(
                        {
                            "cue_no": row["cue_no"],
                            "group": accent_group_name,
                            "before": before,
                            "after": after,
                            "rises": (before or 0.0) < (after or 0.0),
                        }
                    )
            else:
                non_accent_cue_count += 1
                for name in m5._EFFECT_GROUPS.values():
                    val = row[name]
                    if val is not None and val > 0:
                        non_accent_violations[name] += 1
            prev_dims = {name: row[name] for name in m5._EFFECT_GROUPS.values()}

        under3 = [(no, n) for no, n in gate_result.cue_lit_layers if n < 3] if gate_result else []
        row = {
            "song": song_name,
            # 카드 조건 1 — 색 2~3
            "color_count": gate_result.color_count if gate_result else None,
            # 카드 조건 2 — 큐 사이 색 변화 >= 1
            "color_change_count": gate_result.color_change_count if gate_result else None,
            # 카드 조건 3 — 구간 큐 LIT 층 >= 3 (전부)
            "n_section_cues": len(gate_result.cue_lit_layers) if gate_result else 0,
            "n_cues_lit_lt_3": len(under3),
            "failing_cues": under3,
            # 카드 조건 4 — fx 요청 곡은 송신 효과 >= 1
            "fx_requested": gate_result.fx_requested if gate_result else None,
            "fx_hinted": gate_result.fx_hinted if gate_result else None,
            "effect_lines_sent": gate_result.effect_lines_sent if gate_result else None,
            # 카드 조건 5 — 비액센트 큐의 effect 그룹 점등 0
            "n_non_accent_cues": non_accent_cue_count,
            "non_accent_effect_violations": non_accent_violations,
            "n_accent_cues": len(accent_rows),
            "n_accent_rises": sum(1 for r in accent_rows if r["rises"]),
            # 게이트 자체 판정(비차단 경고 — REQ-014)
            "gate_warns": gate_result.warns if gate_result else None,
            "gate_violations": list(gate_result.violations) if gate_result else [],
        }
        summary.append(row)
        total_violations = sum(non_accent_violations.values())
        print(
            f"{song_name}: 색 {row['color_count']}종 · 색변화 {row['color_change_count']} · "
            f"LIT<3 {row['n_cues_lit_lt_3']}/{row['n_section_cues']} · "
            f"fx 요청/힌트/송신 "
            f"{row['fx_requested']}/{row['fx_hinted']}/{row['effect_lines_sent']} · "
            f"비액센트 effect>0 위반 {total_violations}/{non_accent_cue_count} · "
            f"액센트 상승 {row['n_accent_rises']}/{row['n_accent_cues']} · "
            f"게이트 경고 {'YES' if row['gate_warns'] else 'no'}"
        )
        for clause in row["gate_violations"]:
            print(f"  게이트 위반: {clause}")

    (HERE / "measure_m7_8songs.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), "utf-8"
    )


if __name__ == "__main__":
    main()
