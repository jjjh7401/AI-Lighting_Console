"""t61 — 프리플라이트가 **네 갈래를 실제로 가르는지** 잰다.

실기로는 둘만 만들 수 있었다(맞는 포트 -> `responder_ok`, 틀린 포트 ->
`port_mismatch`). 나머지 둘은 응답기를 죽여야 나오는데, 콘솔에 미저장 유일본이
있어 그럴 수 없다. 그래서 여기서 가짜 발견기로 덮는다.

**넷째(`discovery_incomplete`)가 이 파일의 이유다.** 「어디에도 회신이 없다」와
「못 들은 포트가 있어서 못 찾았다」는 결과가 같아 보이지만 다른 사건이다. 접으면
t61 이 없애려던 모호성이 자리만 옮긴다.
"""

from __future__ import annotations

import server.tools.probe_preflight as preflight_module
from server.safety.monitor import HealthMonitor
from server.tools.probe_preflight import preflight
from server.web.reply_discovery import ReplyProbeResult


class _Gate:
    def __init__(self, state: str) -> None:
        self._state = state
        self.pings = 0

    def heartbeat(self) -> str:
        self.pings += 1
        return self._state


def _run(monkeypatch, state, result):
    gate = _Gate(state)
    if result is not None:
        monkeypatch.setattr(preflight_module, "discover_reply_port", lambda **_kw: result)
    return preflight(gate, receive_host="127.0.0.1", receive_port=9000, console_port=8000)


def _probe(**overrides) -> ReplyProbeResult:
    fields = dict(
        configured_port=9000,
        candidates=(9001, 8999, 9005),
        listened=(9001, 8999, 9005),
        unbindable=(),
        observed_port=None,
        send_error=None,
    )
    fields.update(overrides)
    return ReplyProbeResult(**fields)


class TestFourVerdicts:
    def test_a_healthy_responder_costs_no_discovery(self, monkeypatch):
        called = []
        monkeypatch.setattr(preflight_module, "discover_reply_port", lambda **_kw: called.append(1))
        report = _run(monkeypatch, HealthMonitor.ONLINE, None)
        assert report["verdict"] == "responder_ok"
        assert called == [], "응답기가 살아 있는데 발견을 돌렸다 — 공짜여야 한다"

    def test_a_reply_on_another_port_is_named_a_mismatch(self, monkeypatch):
        report = _run(monkeypatch, HealthMonitor.CONSOLE_OFFLINE, _probe(observed_port=9005))
        assert report["verdict"] == "port_mismatch"
        assert "9005" in report["detail"]
        assert report["observed_port"] == 9005

    def test_silence_everywhere_is_named_a_silent_responder(self, monkeypatch):
        report = _run(monkeypatch, HealthMonitor.CONSOLE_OFFLINE, _probe())
        assert report["verdict"] == "responder_silent"
        assert "포트 불일치가 아니라" in report["detail"]

    def test_an_unlistened_candidate_is_not_folded_into_silence(self, monkeypatch):
        """넷째. 이 검사가 없으면 셋째가 「다 못 봐서 못 찾았다」까지 삼킨다."""
        report = _run(
            monkeypatch,
            HealthMonitor.CONSOLE_OFFLINE,
            _probe(listened=(9001,), unbindable=(8999, 9005)),
        )
        assert report["verdict"] == "discovery_incomplete"
        assert report["verdict"] != "responder_silent"
        assert report["unbindable"] == [8999, 9005]
        assert "8999" in report["detail"]
        assert "9005" in report["detail"]

    def test_the_four_verdicts_are_distinct(self, monkeypatch):
        """비공허 — 넷이 서로 다른 이름이어야 가르는 것이다."""
        seen = []
        seen.append(_run(monkeypatch, HealthMonitor.ONLINE, None)["verdict"])
        seen.append(
            _run(monkeypatch, HealthMonitor.CONSOLE_OFFLINE, _probe(observed_port=9005))["verdict"]
        )
        seen.append(_run(monkeypatch, HealthMonitor.CONSOLE_OFFLINE, _probe())["verdict"])
        seen.append(
            _run(
                monkeypatch,
                HealthMonitor.CONSOLE_OFFLINE,
                _probe(listened=(9001,), unbindable=(8999,)),
            )["verdict"]
        )
        assert len(set(seen)) == 4, "갈래가 겹친다: " + repr(seen)


class TestItNeverAdopts:
    def test_the_report_carries_no_way_to_apply_itself(self, monkeypatch):
        """REQ-DEPLOY-026 — 조용히 포트를 바꾸는 것은 같은 병의 부호 반대다.

        보고는 진단이지 조치가 아니다. 「적용」 통로가 생기면 설정 화면과
        런타임이 갈리는 그 사고가 그대로 돌아온다.
        """
        report = _run(monkeypatch, HealthMonitor.CONSOLE_OFFLINE, _probe(observed_port=9005))
        assert report["configured_port"] == 9000, "설정값이 조용히 바뀌었다"
        assert all(not callable(value) for value in report.values())
