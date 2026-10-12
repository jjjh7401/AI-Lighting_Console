"""카드 t491 1단계 — 곡 사이 룩 재사용 실측(구현 없음, 콘솔 접촉 0).

질문: 지금 조립기(``song_cue_composer``) 경로로 저장소의 곡 여러 개를 연달아
돌리면, 이웃한 두 곡이 같은 룩을 고르는가? 시험 쇼 값의 의미는 해석하지 않는다
— 같은지 다른지만 센다.

하네스: t501 ``measure_ac001_8songs``(대화 길 끝까지, in-process FakeConsole,
t499 analysis.json 재생 — DSP 재실행 없음) + ``measure_m7_8songs`` 의 읽기 전용
실기 증거 패치(능력 판독·페이저 풀). 두 파일 모두 수정 없이 재사용한다.

룩 정의(큐 하나): ``(position.stored, color.palette)`` — 위치 프리셋 + 색 조합.
보조 정의로 효과(``fx.permitted``)를 더한 ``look+fx`` 도 센다. 구간 큐
(``kind == "section"``)만 센다 — MIB 사전이동·절정 복귀는 파생 큐다.

실행 모드
- ``same_session``: 한 ``ChatSession`` 에서 8곡을 차례로(실제 쇼 운용 형태).
- ``fresh``: 곡마다 새 ``ChatSession``(대조군). 두 모드의 룩이 곡마다 같으면
  앞 곡이 뒤 곡의 선택에 영향을 주지 않는다(곡 사이 기억 없음)는 실측이다.
- 답 세트 ``fixed``: 8곡 모두 같은 인터뷰 답(t501 ANSWERS 그대로).
- 답 세트 ``rotated``: 컨셉 답만 곡마다 카드가 내민 선택지 중 k%3 번째로 돌린다
  (재사용이 답에서 오는지 조립기에서 오는지 가르는 대조).

실행: uv run python .moai/reports/t491/measure_look_reuse.py
출력: 표준출력 + .moai/reports/t491/look_reuse.json
"""

from __future__ import annotations

import base64
import hashlib
import itertools
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
T501 = HERE.parent / "t501"
T499 = HERE.parent / "t499"
sys.path.insert(0, str(T501))

import measure_ac001_8songs as m  # noqa: E402
import measure_m7_8songs as m7  # noqa: E402

from server.safety.audit import AuditLog  # noqa: E402
from server.safety.gate import SafetyGate  # noqa: E402
from server.web.approval_bridge import ApprovalChannel  # noqa: E402
from server.web.question import UNANSWERED  # noqa: E402
from server.web.session import ChatSession, SongAudioUpload  # noqa: E402


class _RotatingQuestions:
    """곡마다 답 목록을 새로 받는다. ``concept_index`` 가 주어지면 첫 카드(컨셉)의
    답만 그 카드가 실제로 내민 선택지의 그 번째로 바꾸고, 둘째 카드(팔레트)는
    「<컨셉> 색 조합」 선택지가 있으면 그것으로 맞춘다."""

    def __init__(self):
        self.answers: list[str] = []
        self.concept_index: int | None = None
        self.log: list[dict] = []
        self._concept: str | None = None

    def load(self, answers, concept_index):
        self.answers = list(answers)
        self.concept_index = concept_index
        self._concept = None

    def ask(self, request, **_kw):
        options = [getattr(o, "label", str(o)) for o in (getattr(request, "options", ()) or ())]
        if self.answers:
            answer = self.answers.pop(0)
            if self.concept_index is not None and answer == m.ANSWERS[0] and options:
                answer = options[self.concept_index % len(options)]
                self._concept = answer
            elif self._concept and m.ANSWERS[0] in answer:
                # 「우주 색 조합」·「우주 컨셉 우선 배치」처럼 컨셉 이름이 박힌 답은
                # 고른 컨셉으로 바꿔 끼운다(카드가 그 이름으로 선택지를 다시 낸다).
                wanted = answer.replace(m.ANSWERS[0], self._concept)
                answer = wanted if wanted in options else answer
        elif "이 매핑 사용" in options:
            answer = "이 매핑 사용"
        elif any(str(label).startswith("승인") for label in options):
            answer = "승인"
        else:
            answer = UNANSWERED
        self.log.append({"options": options[:20], "answer": answer})
        return answer

    def bind(self, *_a, **_kw):
        return None


def _new_session():
    tmp = Path(tempfile.mkdtemp(prefix="t491-"))
    console = m._Console()
    audit = AuditLog(tmp / "audit")
    gate = SafetyGate(console=console, audit=audit, approval_port=m._Approval())
    session = ChatSession(
        gate=gate,
        provider=m._Provider(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=lambda _e: None,
        approval_channel=ApprovalChannel(timeout_seconds=1.0),
    )
    session._registry = m._Spatial(session._registry)
    questions = _RotatingQuestions()
    session._question_channel = questions
    return session, questions


def _run_song(session, questions, song, path, slot, concept_index):
    record, resolution = m._confirmed_analysis_from_t499(path, song)
    fake = song.encode("utf-8")
    session._song_audio = SongAudioUpload(
        file_name=song,
        mime_type="audio/mpeg",
        content_base64=base64.b64encode(fake).decode(),
        sha256=hashlib.sha256(fake).hexdigest(),
        byte_length=len(fake),
    )
    session._song_analysis = record
    session._song_bpm = resolution
    questions.load(m.ANSWERS, concept_index)
    start = len(questions.log)
    # 같은 세션의 다음 곡이 앞 곡의 시퀀스·타임코드 번호와 부딪치지 않게 곡마다
    # 번호를 비운다(번호 충돌은 이 측정의 질문이 아니다).
    instruction = f"디자인 큐 시트, 시퀀스 {211 + slot}, 프리셋 21번부터, 타임코드 {11 + slot}"
    captured_before = len(_CAPTURED)
    reply = session.run_instruction(instruction)
    new = _CAPTURED[captured_before:]
    bundle = new[-1].bundle if new and new[-1].bundle else None
    cues = [c for c in (bundle.cues if bundle else ()) if c.kind == "section"]
    concept = next(
        (
            c["answer"]
            for c in questions.log[start:]
            if c["options"][:1] and "색 조합" not in c["answer"]
        ),
        None,
    )
    return {
        "song": song,
        "concept_answer": concept,
        "status": reply.get("status"),
        "cues": [
            {
                "no": c.cue_number,
                "name": c.cue_name,
                "position": c.position.stored,
                "palette": list(c.color.palette),
                "fx": list(c.fx.permitted),
            }
            for c in cues
        ],
    }


_CAPTURED: list = []


def _install_capture():
    original = ChatSession._reviewed_song_commands

    def recording(self, composition, **kwargs):
        _CAPTURED.append(composition)
        return original(self, composition, **kwargs)

    ChatSession._reviewed_song_commands = recording
    ChatSession._try_rig_capabilities = m7._patched_try_rig_capabilities
    m7._patch_console_query_state()


def _look(cue, with_fx=False):
    key = (cue["position"], tuple(cue["palette"]))
    return key + (tuple(cue["fx"]),) if with_fx else key


def _pair_stats(a, b, with_fx=False):
    la = [_look(c, with_fx) for c in a["cues"]]
    lb = [_look(c, with_fx) for c in b["cues"]]
    sa, sb = set(la), set(lb)
    reused = sum(1 for x in lb if x in sa)
    return {
        "a": a["song"],
        "b": b["song"],
        "opening_same": bool(la and lb and la[0] == lb[0]),
        "b_cues": len(lb),
        "b_cues_reusing_a_look": reused,
        "b_reuse_ratio": round(reused / len(lb), 3) if lb else None,
        "distinct_a": len(sa),
        "distinct_b": len(sb),
        "shared_distinct": len(sa & sb),
        "jaccard": round(len(sa & sb) / len(sa | sb), 3) if sa | sb else None,
        "identical_look_set": sa == sb,
    }


def _summary(rows, pairs):
    adj = pairs
    return {
        "pairs": len(adj),
        "opening_same": sum(p["opening_same"] for p in adj),
        "identical_look_set": sum(p["identical_look_set"] for p in adj),
        "b_cues_total": sum(p["b_cues"] for p in adj),
        "b_cues_reusing_a_look": sum(p["b_cues_reusing_a_look"] for p in adj),
        "pairs_with_any_shared_look": sum(1 for p in adj if p["shared_distinct"] > 0),
    }


def main():
    _install_capture()
    paths = sorted(
        p for p in (T499 / "runs").glob("*/analysis.json") if p.parent.name != "Rain_first"
    )
    assert len(paths) == 8, [p.parent.name for p in paths]
    songs = [(p.parent.name, p) for p in paths]
    out: dict = {"songs": [s for s, _ in songs], "runs": {}}
    for answers in ("fixed", "rotated"):
        for mode in ("same_session", "fresh"):
            rows = []
            session, questions = _new_session()
            for slot, (song, path) in enumerate(songs):
                if mode == "fresh" and slot:
                    session, questions = _new_session()
                concept_index = slot if answers == "rotated" else None
                rows.append(_run_song(session, questions, song, path, slot, concept_index))
            empty = [r["song"] for r in rows if not r["cues"]]
            if empty:
                # 큐 0개는 「룩이 다르다」가 아니라 하네스가 곡을 못 돌린 것이다.
                raise SystemExit(f"{answers}/{mode}: 구간 큐 0개 — {empty}")
            out["runs"][f"{answers}/{mode}"] = rows
    report: dict = {"songs": out["songs"], "runs": out["runs"], "analysis": {}}
    for key, rows in out["runs"].items():
        adjacent = [_pair_stats(a, b) for a, b in itertools.pairwise(rows)]
        adjacent_fx = [_pair_stats(a, b, True) for a, b in itertools.pairwise(rows)]
        all_pairs = [_pair_stats(a, b) for a, b in itertools.combinations(rows, 2)]
        report["analysis"][key] = {
            "adjacent": {"summary": _summary(rows, adjacent), "pairs": adjacent},
            "adjacent_with_fx": {"summary": _summary(rows, adjacent_fx)},
            "all_pairs": {"summary": _summary(rows, all_pairs)},
        }
    # 대조: 같은 세션과 새 세션의 큐별 룩이 곡마다 바이트 동일한가
    for answers in ("fixed", "rotated"):
        same = report["runs"][f"{answers}/same_session"]
        fresh = report["runs"][f"{answers}/fresh"]
        report["analysis"][f"{answers}/same_vs_fresh_identical"] = [
            {"song": a["song"], "identical": a["cues"] == b["cues"], "n": len(a["cues"])}
            for a, b in zip(same, fresh, strict=True)
        ]
    (HERE / "look_reuse.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), "utf-8")
    for key, value in report["analysis"].items():
        if key.endswith("identical"):
            print(key, [(r["song"], r["identical"], r["n"]) for r in value])
            continue
        print("==", key)
        print("  adjacent     ", value["adjacent"]["summary"])
        print("  adjacent+fx  ", value["adjacent_with_fx"]["summary"])
        print("  all pairs    ", value["all_pairs"]["summary"])
    for key, rows in report["runs"].items():
        print(
            "--", key, [(r["song"], r["concept_answer"], r["status"], len(r["cues"])) for r in rows]
        )


if __name__ == "__main__":
    main()
