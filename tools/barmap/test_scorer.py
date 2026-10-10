"""채점기 자체를 검증하는 음성/양성 대조군 — REQ-LDBARMAP-005, AC-LDBARMAP-002/003.

`lesson-the-guard-itself-can-be-vacuous.md`(이 저장소 메모리)의 교훈을 그대로
적용한다 — 채점기가 무엇을 넣어도 통과하지 않는지 먼저 확인한 뒤에야 후보를
채점한다. 실행: `.venv/bin/python -m pytest tools/barmap -q`
"""

from __future__ import annotations

from tools.barmap.ground_truth import (
    BAR_INTERVAL_SEC,
    BEAT_INTERVAL_SEC,
    parse_downbeats,
    parse_events,
    shift_downbeats,
)
from tools.barmap.scorer import strict_index_hit_rate


def test_positive_control_truth_vs_itself_is_100_percent() -> None:
    """양성 대조군 — 정답지를 정답지 자신과 비교하면 100%여야 한다."""
    truth = parse_downbeats()
    result = strict_index_hit_rate(truth, truth)
    assert result.matched == result.total == len(truth)
    assert result.rate_pct == 100.0


def test_negative_control_1beat_shift_fails_below_10_percent() -> None:
    """음성 대조군 1(REQ-LDBARMAP-005(i), AC-LDBARMAP-002) — 전체 1박(0.534s) 밀어낸
    날조 격자는 엄격한 순서 대응 하에서 적중률 10% 미만이어야 한다."""
    truth = parse_downbeats()
    shifted = shift_downbeats(truth, BEAT_INTERVAL_SEC)
    result = strict_index_hit_rate(shifted, truth)
    assert result.rate_pct < 10.0, (
        f"1박 밀림 날조 격자가 {result.rate_pct:.1f}% 적중 — 채점기가 공허할 위험(D3)"
    )


def test_negative_control_1bar_shift_fails_below_10_percent() -> None:
    """음성 대조군 2(REQ-LDBARMAP-005(ii), AC-LDBARMAP-003) — 전체 1마디(2.136s=4박)
    밀어낸 날조 격자는 엄격한 순서 대응 하에서 적중률 10% 미만이어야 한다.

    이것이 바로 plan-audit iteration 1 D3가 지적한 핵심 — 최근접 매칭을 썼다면
    이 날조 격자는 "다음 정답 다운비트에 우연히 맞아" 약 97%로 잘못 통과했을
    것이다. 엄격한 순서 대응(n번째 검출 vs n번째 정답만 비교)이 이를 막는다.
    """
    truth = parse_downbeats()
    shifted = shift_downbeats(truth, BAR_INTERVAL_SEC)
    result = strict_index_hit_rate(shifted, truth)
    assert result.rate_pct < 10.0, (
        f"1마디 밀림 날조 격자가 {result.rate_pct:.1f}% 적중 — 최근접 매칭이었다면 "
        "약 97%로 통과했을 함정에 걸렸을 수 있다(D3)"
    )


def test_1bar_shift_would_have_passed_under_nearest_matching() -> None:
    """D3 수치 재현 — 최근접 매칭이었다면 이 날조 격자가 얼마나 높게(잘못) 통과했을지
    보여 준다(엄격한 순서 대응의 필요성을 수치로 증명, 참고용 — PASS/FAIL 판정에
    쓰지 않는다).
    """
    truth = parse_downbeats()
    shifted = shift_downbeats(truth, BAR_INTERVAL_SEC)
    tol = 0.060
    nearest_hits = 0
    for t in shifted:
        if any(abs(t - truth_t) <= tol for truth_t in truth):
            nearest_hits += 1
    nearest_rate_pct = nearest_hits / len(truth) * 100.0
    # D3가 말한 "약 97%"에 가까운 높은 값이어야 한다 — 최근접 매칭의 위험을 실증.
    assert nearest_rate_pct > 80.0, (
        f"최근접 매칭 적중률이 예상보다 낮다({nearest_rate_pct:.1f}%) — "
        "D3가 묘사한 함정 조건을 재현하지 못했을 수 있다"
    )


def test_ground_truth_parses_82_downbeats_and_7_events() -> None:
    """정답지 파서 자체의 건전성 — 82마디·7사건이 아니면 이후 모든 채점이 무의미하다."""
    truth = parse_downbeats()
    events = parse_events()
    assert len(truth) == 82
    assert len(events) == 7
    assert sorted(t for t in truth) == truth  # 시각 순서로 정렬돼 있어야 한다(마디 1부터)
