"""실제 곡 → 곡 큐 → 콘솔. t376 교훈을 지킨다: executor 예약 번호는 피한다."""

from pathlib import Path

from server.audio.analyze import AnalysisResult, analyze
from server.looks.loader import load_library_from_dir
from server.looks.songcue import (
    build_songcue_bundle,
    build_songcue_timing,
    map_sections_to_looks,
    parse_sections,
)
from server.orchestrator.tools import rig_object, rig_section
from server.safety.bootstrap import build_console_stack

SONG = Path("src/걸그룹DinoDino_C_max최고품질.wav")
#: 감독이 확인 카드에서 하는 일을 여기서 대신한다 — D등급 흐름에 K-pop 통상 구조를
#: 얹은 **제안**이지 측정이 아니다.
NAMES = [
    "Intro",
    "Verse",
    "Verse",
    "Chorus",
    "Chorus",
    "Bridge",
    "Bridge",
    "Chorus",
    "Verse",
    "Chorus",
    "Verse",
    "Chorus",
    "Breakdown",
    "Chorus",
    "Bridge",
    "Chorus",
]


class ScopedApproval:
    def __init__(self) -> None:
        self.target: int | None = None
        self.timecode: int = 1

    def request_approval(self, request) -> bool:
        want = f"Sequence {self.target} "
        tc = f"Timecode {self.timecode}"
        for item in request.items:
            c = item.command
            if c.startswith(("Store " + want, "Label " + want)):
                continue
            if c.startswith(f"Store {tc}") or c.startswith(f"Set {tc} ") or c.endswith(f"At {tc}"):
                continue
            if c.startswith("Set Cue ") and f"Sequence {self.target} " in c:
                continue
            if True:
                print(f"  🔴 범위 밖 거절: {item.command}")
                return False
        print(f"  승인 {len(request.items)}줄 — 전부 Sequence {self.target}")
        return True


def main() -> None:
    out = analyze(SONG.read_bytes())
    assert isinstance(out, AnalysisResult)
    cands = out.d_candidates
    print(f"곡 {SONG.name} · BPM {out.bpm:.1f} · 구간 {len(cands)}개")
    assert len(NAMES) == len(cands)

    raw = [
        {"name": n, "start": c.start_ms / 1000.0, "dynamics": c.d_level}
        for n, c in zip(NAMES, cands, strict=True)
    ]

    approver = ScopedApproval()
    stack = build_console_stack(receive_port=9005, approval_port=approver)
    try:
        q = stack.gate.state_port.query_state
        rs, rg = q("DataPool/Sequences"), q("DataPool/Groups")
        used = sorted(c.get("i") for c in rs.get("children", []) if c.get("i"))
        seqs = rig_section([rig_object(c) for c in rs.get("children", [])], rs)
        groups = rig_section([rig_object(c) for c in rg.get("children", [])], rg)

        # t376: 빈 시퀀스가 빈 번호는 아니다 — executor 가 가리키면 예약이다.
        reserved: set[int] = set()
        for pg in q("DataPool/Pages").get("children", []):
            pn = pg.get("i")
            for e in q(f"DataPool/Pages/{pn}").get("children", []):
                sq = q(f"DataPool/Pages/{pn}/{e.get('i')}")["node"].get("sequenceNo")
                if sq:
                    reserved.add(sq)
        print("쓰이는 시퀀스:", used, "· executor 예약:", sorted(reserved))

        lib = load_library_from_dir()
        sel = map_sections_to_looks(parse_sections(raw), lib, "edm")
        b = build_songcue_bundle("DinoFull", sel, sequences_section=seqs, groups_section=groups)

        print(
            f"\n대상 Sequence {b.sequence_number} · 큐 {len(b.stored_sections)}/{len(b.sections)}"
        )
        for k in b.skipped:
            print(f"  🔴 사라짐: cue {k.cue_number} {k.section.label} — {k.reason}")
        dark = [(s.cue_number, s.darkness.before, s.darkness.after) for s in b.darkened_sections]
        print(f"무빙 {[s.cue_number for s in b.movement_sections]} · 감광 {dark}")

        if b.sequence_number in reserved:
            raise SystemExit(f"🔴 Sequence {b.sequence_number} 는 executor 예약 — 중단")
        # 🔴 오늘의 교훈: bundle.commands 에는 타이밍이 설계상 안 들어간다.
        # 실제 서비스 경로(prepare_songcue)와 같은 조합으로 타이밍을 같이 낸다.
        free_tc = 1
        try:
            tcs = {c.get("i") for c in q("DataPool/Timecodes").get("children", [])}
            while free_tc in tcs:
                free_tc += 1
        except Exception as exc:
            print(f"  타임코드 풀 판독 실패({type(exc).__name__}) — 1번 사용")
        timing = build_songcue_timing(b, timecode_number=free_tc)
        print(f"타임코드 {free_tc} · 타이밍 명령 {len(timing.commands)}줄")
        for sk in timing.skipped_axes:
            print(f"  건너뜀: {sk.axis} — {sk.reason}")
        approver.target = b.sequence_number
        approver.timecode = free_tc
        all_cmds = list(b.commands) + list(timing.commands)
        d = stack.gate.screen(all_cmds)
        print("게이트:", d.status, "cleared=", d.cleared)
        if not d.cleared:
            raise SystemExit("게이트 거절 — 중단")
        ok = 0
        bad = []
        for c in all_cmds:
            r = stack.gate.execution_port.execute(c)
            if getattr(r, "ok", True) is False:
                bad.append((c, getattr(r, "detail", "")))
            else:
                ok += 1
        print(f"발사 {ok}/{len(all_cmds)}")
        for c, why in bad[:6]:
            print(f"  🔴 {c[:64]} -> {why}")
    finally:
        stack.stop()


main()
