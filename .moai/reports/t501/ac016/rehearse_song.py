"""t501 AC-016 준비 — M7 가짜 콘솔 + 실제 DSP 리허설(일반화).

`measure_m7_dsp_8songs.py` 의 `_rehearse_one`(= t499 `rehearse_song.py`
213~297행과 바이트 동일 로직 + M7 능력/풀 몽키패치)이 이미 하는 일을
**다시 쓰지 않는다** — 콘솔(`_Console`)·질문(`_Questions`)·승인(`_Approval`)·
공간 대역(`_Spatial`)·제공자(`_Provider`) 클래스와 능력 패치
(`_patched_try_rig_capabilities`)는 `measure_m7_dsp_8songs` 모듈에서 그대로
가져와 쓴다. 이 스크립트가 더하는 것은 세 가지뿐이다:
  1) 지시문의 시퀀스·타임코드 번호를 인자로 받는다(측정 스크립트는 211/11 고정).
  2) `real_song.py` 와 같은 출력 파일 형식(approval_request_N.txt 등)으로 떠서
     `classify_diff.py` 로 줄 단위 비교할 수 있게 한다.
  3) `measure_m7_dsp_8songs.main()` 의 "8개 오프라인 판정" 행 계산(M5 효과
     위반·M7 게이트 결과 집계)을 **같은 모듈을 불러 재사용**해 이번 두 곡에도
     적용하고 `offline_checks.json` 으로 남긴다.

콘솔 접촉: 0건(in-process FakeConsole, measure_m7_dsp_8songs.py 와 동일).
오디오: 주 체크아웃의 비추적 파일(`src/sample music/`), 읽기 전용.

실행: uv run python .moai/reports/t501/ac016/rehearse_song.py \
      <song-file-name> <sequence> <timecode> <out-dir>
"""

from __future__ import annotations

import base64
import json
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
T501 = HERE.parent
sys.path.insert(0, str(T501))

import measure_m5_8songs as m5  # noqa: E402
import measure_m7_8songs as m7  # noqa: E402
import measure_m7_dsp_8songs as m7dsp  # noqa: E402

from server.safety.audit import AuditLog  # noqa: E402
from server.safety.gate import SafetyGate  # noqa: E402
from server.web.approval_bridge import ApprovalChannel  # noqa: E402
from server.web.session import ChatSession  # noqa: E402

AUDIO_ROOT = Path("/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/src/sample music")

SONG_FILE, SEQUENCE, TIMECODE = sys.argv[1], sys.argv[2], sys.argv[3]
OUT = Path(sys.argv[4])
OUT.mkdir(parents=True, exist_ok=True)
AUDIO = AUDIO_ROOT / SONG_FILE
assert AUDIO.is_file(), f"{AUDIO} 없음(읽기 전용 확인 실패)"

#: t498 real_console.py / measure_m7_dsp_8songs.py 와 바이트 동일한 지시문
#: 형태 — 번호만 이 카드가 지정한 시퀀스/타임코드로 바꾼다.
INSTRUCTION = f"디자인 큐 시트, 시퀀스 {SEQUENCE}, 프리셋 21번부터, 타임코드 {TIMECODE}"
#: t498/t499/M7 과 바이트 동일한 고정 인터뷰 답변 목록(재사용, 다시 안 적음).
ANSWERS = list(m7dsp.ANSWERS)

_captured: list[object] = []
captured_gate: list[object] = []
original_reviewed = ChatSession._reviewed_song_commands
original_try_rig = ChatSession._try_rig_capabilities
original_finalize = ChatSession._song_finalize


def _recording_reviewed(self, composition, **kwargs):
    _captured.append(composition)
    return original_reviewed(self, composition, **kwargs)


def _recording_finalize(self, *args, **kwargs):
    result = original_finalize(self, *args, **kwargs)
    captured_gate.append(self._last_gate_result)
    return result


ChatSession._reviewed_song_commands = _recording_reviewed
ChatSession._try_rig_capabilities = m7._patched_try_rig_capabilities
ChatSession._song_finalize = _recording_finalize

try:
    tmp = Path(tempfile.mkdtemp(prefix="t501-ac016-"))
    console = m7dsp._Console()
    audit = AuditLog(tmp / "audit")
    approval = m7dsp._Approval()
    gate = SafetyGate(console=console, audit=audit, approval_port=approval)
    sent: list[dict] = []
    session = ChatSession(
        gate=gate,
        provider=m7dsp._Provider(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=sent.append,
        approval_channel=ApprovalChannel(timeout_seconds=1.0),
    )
    session._registry = m7dsp._Spatial(session._registry)
    questions = m7dsp._Questions(ANSWERS)
    session._question_channel = questions

    data = AUDIO.read_bytes()
    mime = "audio/wav" if AUDIO.suffix.lower() == ".wav" else "audio/mpeg"
    t0 = time.monotonic()
    replies = [
        session.upload_song_audio(AUDIO.name, mime, base64.b64encode(data).decode()),
        session.analyse_song_audio(),
    ]
    analysis = session.song_analysis
    dsp_seconds = time.monotonic() - t0
    replies.append(session.run_instruction(INSTRUCTION))
finally:
    ChatSession._reviewed_song_commands = original_reviewed
    ChatSession._try_rig_capabilities = original_try_rig
    ChatSession._song_finalize = original_finalize

commands = list(console.executed)
gate_result = captured_gate[-1] if captured_gate else None

# ---- real_song.py 와 같은 출력 형식(승인 요청 1건 = 명령 전체) ----
(OUT / "approval_requests.json").write_text(
    json.dumps([{"commands": commands, "approved": True}], ensure_ascii=False, indent=1), "utf-8"
)
(OUT / "approval_request_1.txt").write_text("\n".join(commands) + "\n", "utf-8")
(OUT / "cards.json").write_text(json.dumps(questions.log, ensure_ascii=False, indent=1), "utf-8")
(OUT / "replies.json").write_text(
    json.dumps([r.get("text") for r in replies], ensure_ascii=False, indent=1), "utf-8"
)
(OUT / "events.json").write_text(
    json.dumps(sent, ensure_ascii=False, indent=1, default=str), "utf-8"
)
(OUT / "queries.txt").write_text("\n".join(console.queried) + "\n", "utf-8")
(OUT / "analysis.json").write_text(
    json.dumps(
        None
        if analysis is None
        else {
            "sha256": analysis.source_sha256,
            "bpm": analysis.bpm.bpm,
            "bpm_source": analysis.bpm.source,
            "sections": [
                {
                    "i": s.index,
                    "label": s.label,
                    "start_ms": s.start_ms,
                    "end_ms": s.end_ms,
                    "d": s.d_level,
                    "selected": s.selected,
                }
                for s in analysis.sections
            ],
        },
        ensure_ascii=False,
        indent=1,
    ),
    "utf-8",
)

bundle_cues_obj = list(_captured[-1].bundle.cues) if _captured and _captured[-1].bundle else []
bundle_rows = []
for cue in bundle_cues_obj:
    bundle_rows.append(
        {
            "cue": cue.cue_number,
            "kind": cue.kind,
            "name": cue.cue_name,
            "d": cue.d_level,
            "dimmer": cue.dimmer.to_dict() if hasattr(cue.dimmer, "to_dict") else str(cue.dimmer),
            "position": cue.position.to_dict()
            if hasattr(cue.position, "to_dict")
            else str(cue.position),
            "color": cue.color.to_dict()
            if getattr(cue, "color", None) is not None and hasattr(cue.color, "to_dict")
            else str(getattr(cue, "color", None)),
            "mib": cue.mib.to_dict() if getattr(cue, "mib", None) is not None else None,
            "pre_drop_from": getattr(cue, "pre_drop_from", None),
            "accent": cue.accent_fixture.to_dict() if cue.accent_fixture else None,
            "start_ms": cue.timing.start_ms,
            "fade": cue.fade_seconds,
        }
    )
if bundle_rows:
    (OUT / "bundle_cues.json").write_text(
        json.dumps(
            {"cues": bundle_rows, "arc_notes": list(_captured[-1].bundle.arc_notes)},
            ensure_ascii=False,
            indent=1,
            default=str,
        ),
        "utf-8",
    )

# ---- M7 "8개 오프라인 판정" 행(measure_m7_dsp_8songs.main() 의 같은 계산을
# 재사용 — 로직을 다시 안 적는다) ----
effect_rows = m5._effect_states_per_cue(commands)
bundle_by_no = {c.cue_number: c for c in bundle_cues_obj}
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
    composed = bundle_by_no.get(cue_no_float)
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
offline_row = {
    "song": SONG_FILE,
    "sequence": SEQUENCE,
    "timecode": TIMECODE,
    "dsp_seconds": round(dsp_seconds, 2),
    "analysis_bpm": None if analysis is None else analysis.bpm.bpm,
    "analysis_n_sections": None if analysis is None else len(analysis.sections),
    "color_count": gate_result.color_count if gate_result else None,
    "color_change_count": gate_result.color_change_count if gate_result else None,
    "n_section_cues": len(gate_result.cue_lit_layers) if gate_result else 0,
    "n_cues_lit_lt_3": len(under3),
    "failing_cues": under3,
    "fx_requested": gate_result.fx_requested if gate_result else None,
    "fx_hinted": gate_result.fx_hinted if gate_result else None,
    "effect_lines_sent": gate_result.effect_lines_sent if gate_result else None,
    "n_non_accent_cues": non_accent_cue_count,
    "non_accent_effect_violations": non_accent_violations,
    "n_accent_cues": len(accent_rows),
    "n_accent_rises": sum(1 for r in accent_rows if r["rises"]),
    "gate_warns": gate_result.warns if gate_result else None,
    "gate_violations": list(gate_result.violations) if gate_result else [],
}
(OUT / "offline_checks.json").write_text(
    json.dumps(offline_row, ensure_ascii=False, indent=1), "utf-8"
)

total_violations = sum(non_accent_violations.values())
print(
    f"song={SONG_FILE} seq={SEQUENCE} tc={TIMECODE} DSP {offline_row['dsp_seconds']}s · "
    f"BPM {offline_row['analysis_bpm']} · 구간 {offline_row['analysis_n_sections']} · "
    f"색 {offline_row['color_count']}종 · 색변화 {offline_row['color_change_count']} · "
    f"LIT<3 {offline_row['n_cues_lit_lt_3']}/{offline_row['n_section_cues']} · "
    f"fx 요청/힌트/송신 {offline_row['fx_requested']}/{offline_row['fx_hinted']}/"
    f"{offline_row['effect_lines_sent']} · "
    f"비액센트 effect>0 위반 {total_violations}/{non_accent_cue_count} · "
    f"액센트 상승 {offline_row['n_accent_rises']}/{offline_row['n_accent_cues']} · "
    f"게이트 경고 {'YES' if offline_row['gate_warns'] else 'no'}"
)
for clause in offline_row["gate_violations"]:
    print(f"  게이트 위반: {clause}")
print(f"commands={len(commands)} approvals={len(approval.requests)} cards={len(questions.log)}")
for reply in replies:
    print("REPLY:", (reply.get("text") or "")[:500])
