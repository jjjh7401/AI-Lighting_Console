"""t255 — LXSEQ-004 인수 기준을 기계적으로 판정한다. 콘솔 쓰기 0."""

import subprocess
from pathlib import Path

TESTS = Path("server/tests")


def grep(pattern: str, *paths: str) -> list[str]:
    out = subprocess.run(["grep", "-rn", pattern, *paths], capture_output=True, text=True)
    return [line for line in out.stdout.splitlines() if line.strip()]


def show(label: str, hits: list[str], limit: int = 3) -> None:
    print(f"\n### {label}  → {len(hits)} 건")
    for line in hits[:limit]:
        print("   ", line[:160])


def main() -> None:
    # AC-002 정확 열 집합 — 빠진 열 / 남는 열 각각 거부하는 검사
    show("AC-002 missing_columns", grep("missing_columns", "server/lxseq/", str(TESTS)))
    show("AC-002 unexpected_columns", grep("unexpected_columns", "server/lxseq/", str(TESTS)))

    # AC-003 Dim 은 숫자 — 사유 문면
    show("AC-003 bad_number", grep("bad_number", "server/lxseq/cue_parser.py"))
    show(
        "AC-003 「참조가 아니라 숫자」 문면",
        grep("참조가 아니라\\|not a reference", "server/lxseq/"),
    )

    # AC-005 unknown_group
    show("AC-005 unknown_group", grep("unknown_group", "server/lxseq/cue_mapper.py"))

    # AC-006 페이드 — 0.0 과 빈칸 구분
    show("AC-006 fade 검사", grep("def test.*fade", str(TESTS / "test_lxseq_cue_mapper.py")))

    # AC-007 큐 단위 원자성 (t228)
    show(
        "AC-007 partial_ship", grep("partial_ship", "server/lxseq/", "server/orchestrator/tools.py")
    )
    show("AC-007 cues_held", grep("cues_held", "server/lxseq/cue_mapper.py"))

    # AC-008 두 층 수렴 — 이름 지정된 검사 둘
    show(
        "AC-008 지정 검사",
        grep(
            "test_existing_name_is_convergence_not_refusal\\|"
            "test_a_cue_number_already_in_the_sequence_is_skipped_not_replanned",
            str(TESTS),
        ),
    )

    # AC-010 툴 등재 + 인자 닫힘
    show("AC-010 등재", grep('"import_lxseq_cues"', "server/orchestrator/tools.py"))
    show(
        "AC-010 prepare_songcue 인자 미수용 검사",
        grep("song_title", str(TESTS / "test_lxseq_cue_tool.py")),
    )

    # AC-011 lxseq 에 쓰기 수단 없음
    show(
        "AC-011 OSC/전송 임포트",
        grep("import.*osc\\|OscBridge\\|execution_port\\|socket", "server/lxseq/"),
    )

    # AC-012 사유 문자열 5종
    for code in (
        "missing_columns",
        "unexpected_columns",
        "unknown_group",
        "unresolved_preset",
        "slot_shortfall",
    ):
        hits = grep(code, str(TESTS))
        print(f"  AC-012 사유 {code:22} 검사에서 {len(hits)} 건 단언")

    # AC-013 되읽기 한계
    show("AC-013 unverified", grep("unverified", "server/lxseq/cue_mapper.py"))

    # AC-014 3분류
    show(
        "AC-014 block_report",
        grep(
            "def block_report\\|BLOCK_DOC_INTENT\\|BLOCK_CONSOLE_STATE",
            "server/lxseq/cue_mapper.py",
        ),
    )


if __name__ == "__main__":
    main()
