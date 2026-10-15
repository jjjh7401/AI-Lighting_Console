"""카드 t497 — 거절된 곡 번들 뒤 `ClearAll` 이 콘솔로 나가면 안 된다.

실측 근거 (t474 run5, 전부 거절 모드): 감사 로그
`.moai/reports/t474/run5_song_dry/audit/audit-20260927.jsonl` 의 466행이
`rejected`(번들 전체), 467행이 그 뒤 43ms 에 나간 `executed` `ClearAll` 이다.

리드 결정 B: 콘솔에 한 줄도 안 나간 거절·차단에는 정리 줄을 보내지 않는다.
줄이 나간 뒤 실패한 경우(실패한 줄 포함)에만 정리를 유지한다. 두 경계를 함께 고정한다.
"""

from __future__ import annotations

from server.tests.test_writegate_song_finalize import _Console, _drive


def test_a_rejected_bundle_sends_no_line_to_the_console(tmp_path):
    console, approval, sites, _questions, _audit = _drive(tmp_path, approve=False)
    assert len(approval.requests) == 1, "번들 하나에 카드 한 장"
    assert sites == ["song-design-reviewed-bundle"], "정리 디스패치가 없어야 한다"
    assert console.executed == [], f"거절된 번들 뒤 콘솔로 나간 줄 (실제: {console.executed})"


class _SecondSendFails(_Console):
    """두 번째로 나간 줄만 콘솔이 거부한다 — 첫 줄은 실제로 반영된다."""

    failed_on: str | None = None

    def execute(self, command: str):
        if len(self.executed) == 1:
            self.fail_on[command] = "실기 거부 (시험)"
            self.failed_on = command
        return super().execute(command)


def test_a_partly_applied_bundle_still_gets_the_cleanup(tmp_path):
    console, approval, sites, _questions, _audit = _drive(
        tmp_path, approve=True, console=_SecondSendFails()
    )
    assert approval.requests, "승인 카드가 떠야 번들이 나간다"
    assert console.failed_on is not None, "두 번째 줄이 실제로 나가야 경계가 선다"
    failed_at = console.executed.index(console.failed_on)
    assert failed_at + 1 < len(console.executed), "실패한 줄 뒤에 정리 줄이 나가지 않았다"
    assert console.executed[failed_at + 1] == "ClearAll", "실패한 줄 바로 뒤에 정리 줄이 나간다"
    assert "song-design-cleanup" in sites
