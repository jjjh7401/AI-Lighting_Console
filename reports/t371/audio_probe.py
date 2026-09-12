"""t371 — 재현/대조군 프로브: 최댓값 기준 상대 문턱이 원거리 계단에 눌린다.

카드 t371 이 참조한 `reports/onsite-round-20260912/audio_probe.py` 는 이
워크트리에 실재하지 않는다(git log 조회 결과: 커밋된 적 없음 — 원본 체크아웃의
untracked 파일이라 워크트리에 복사되지 않았다). 이 파일이 그 자리를 대신한다.
카드 본문의 정확한 수치(예: "0.0~8.0 D1 · 8.0~24.0 D4 · 24.0~30.0 D1 ·
30.0~40.0 D5")는 이 스크립트로 재현하지 않았고, 근본 원인(최댓값 기준 상대
문턱)은 아래 A/B/C 실측으로 독립적으로 확인했다 — server/audio/analyze.py:230
(수정 전 기준선, 이 파일이 기록하는 실측은 그 커밋 기준).

이 파일은 `server.tests.fixtures.audio.synthesize_track_with_steps` 로 만든
합성 트랙을 실제로 `analyze()` 에 흘려 넣어 얻은 **실측** 결과만 담는다 —
손계산이 아니다. `uv run python reports/t371/audio_probe.py` 로 재실행 가능.
"""

from __future__ import annotations

from server.audio.analyze import AnalysisResult, analyze
from server.tests.fixtures.audio import synthesize_track_with_steps

BPM = 128.0


def _run(
    label: str, gains: tuple[float, ...], boundaries: tuple[int, ...], duration_ms: int
) -> None:
    track = synthesize_track_with_steps(
        bpm=BPM, duration_ms=duration_ms, boundaries_ms=boundaries, gains=gains
    )
    outcome = analyze(track)
    if not isinstance(outcome, AnalysisResult):
        print(f"{label}: FAILURE — {outcome}")
        return
    print(f"{label}: planted={boundaries} detected={outcome.boundaries_ms}")


def main() -> None:
    print("=== 원본 재현 (t371 카드가 기술한 결함 형태) ===")
    # A — 원본: 진폭 [0.10, 0.35, 0.85, 0.06, 1.00], 5구간(8초씩), 40초.
    # 4번째 계단(0.06→1.00, 로그진폭차 최대)이 2번째 계단(0.35→0.85)을 누른다.
    _run(
        "A (원본, 큰 계단 포함)",
        (0.10, 0.35, 0.85, 0.06, 1.00),
        (0, 8000, 16000, 24000, 32000),
        40000,
    )
    # B — 대조군: 마지막 계단을 완만하게 바꿔 "유독 큰 계단"을 제거.
    _run(
        "B (대조군, 큰 계단 제거)",
        (0.10, 0.35, 0.85, 0.40, 0.90),
        (0, 8000, 16000, 24000, 32000),
        40000,
    )
    # C — 대조군: 문제의 그 계단(0.35→0.85) 하나만 단독으로 두면 잡히는가.
    _run("C (대조군, 계단만 둘)", (0.35, 0.85), (0, 20000), 40000)

    print()
    print("=== 카드가 요구한 세 가지 adversarial 케이스 ===")
    # 계단이 아예 없는 곡 — 경계를 지어내면 안 된다 (모듈 자체 docstring 경고).
    _run("NOSTEP (계단 없음)", (0.5,), (0,), 20000)
    # 조용한 곡 + 진짜 계단 — 절대 진폭이 작아도 로그 비율 판정은 스케일 불변.
    _run("QUIET (조용한 곡, 진짜 계단 3구간)", (0.02, 0.08, 0.03), (0, 15000, 30000), 45000)
    # 동일 크기 계단 여럿 — 중앙값 기준이 그중 하나를 특별 취급하지 않는지.
    _run("STAIR (동일 크기 계단 4개)", (0.10, 0.20, 0.40, 0.80), (0, 10000, 20000, 30000), 40000)


if __name__ == "__main__":
    main()
