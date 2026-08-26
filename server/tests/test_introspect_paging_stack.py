"""t104 — introspect 페이징이 계층을 **관통하는가**.

응답기와 요청 빌더가 offset 을 알아도, 중간 계층 하나가 조용히 떨어뜨리면
페이징 루프는 창 1을 영원히 다시 읽는다 — 실패가 아니라 **무한 루프**로 나타나고,
실기 창에서 그게 터지면 되돌릴 시간이 없다.

그래서 통과 계층마다 「값이 실제로 아래로 갔는가」를 잰다. 각 계층의 반환값이
아니라 **아래로 넘어간 인자**를 본다 — 반환값은 가짜 아래층이 무엇을 주든 같다.

순수 검증이다. 콘솔·네트워크 접촉 0.
"""

from __future__ import annotations

from server.bridge.protocol import build_introspect_query
from server.safety.console import ConsoleLink


class _RecordingLink(ConsoleLink):
    """보낸 줄만 받아 적는다 — 회신은 성공 하나로 고정한다."""

    def __init__(self) -> None:
        self.lines: list[str] = []
        super().__init__(send=self.lines.append)

    def _round_trip(self, line, request_id, timeout):  # noqa: D102
        self._send(line)
        return {"ok": True, "kind": "introspect", "fields": [], "total": 0, "offset": 0}


class TestTheOffsetSurvivesTheConsoleLink:
    def test_an_offset_reaches_the_wire(self):
        link = _RecordingLink()
        link.enumerate_fields("DataPool/PresetPools/1/3", offset=27)
        assert link.lines, "아무것도 안 보냈다"
        assert "offset=27" in link.lines[-1], link.lines[-1]

    def test_no_offset_keeps_the_historical_bytes(self):
        """1.6.1 응답기가 아직 배치돼 있을 수 있다 — 기본 호출은 그대로여야 한다."""
        link = _RecordingLink()
        link.enumerate_fields("DataPool/PresetPools/1/3")
        assert "offset=" not in link.lines[-1], link.lines[-1]


class TestTheOffsetSurvivesTheGate:
    def test_the_gate_state_port_forwards_the_offset(self):
        """게이트 포트가 offset 을 떨어뜨리면 페이징 루프가 창 1에서 멈추지 않는다."""
        seen: list[tuple[str, int]] = []

        class _FakeGate:
            def _enumerate_fields(self, path, *, offset=0):
                seen.append((path, offset))
                return {"ok": True, "fields": [], "total": 0, "offset": offset}

        from server.safety.gate import _GateStatePort

        port = _GateStatePort(_FakeGate())
        port.enumerate_fields("DataPool/PresetPools/1/3", offset=54)
        assert seen == [("DataPool/PresetPools/1/3", 54)]

    def test_the_gate_audits_the_path_only_even_when_paged(self):
        """감사 주체는 경로뿐이다(REQ-INTROSPECT-018) — offset 이 값을 새게 하지 않는다."""
        logged: list[tuple[str, str, bool]] = []

        class _Audit:
            def log_executed(self, subject, *, kind, ok):
                logged.append((subject, kind, ok))

        class _Console:
            def enumerate_fields(self, path, *, offset=0):
                return {"ok": True, "offset": offset}

        from server.safety.gate import SafetyGate

        gate = SafetyGate.__new__(SafetyGate)
        gate._console = _Console()
        gate._audit = _Audit()
        gate._enumerate_fields("DataPool/PresetPools/1/3", offset=27)
        assert logged == [("DataPool/PresetPools/1/3", "introspect_query", True)]


class TestPagingToExhaustionAcrossTheStack:
    """루프를 도는 쪽의 계약 — 받은 개수만큼 전진한다. 고정 페이지 크기로 전진하면
    창 폭을 예산이 정하므로 이름을 건너뛴다."""

    def test_the_loop_advances_by_what_it_received(self):
        windows = [
            {
                "ok": True,
                "fields": [{"n": f"P{i}"} for i in range(0, 27)],
                "total": 40,
                "offset": 0,
                "truncated": True,
            },
            {
                "ok": True,
                "fields": [{"n": f"P{i}"} for i in range(27, 40)],
                "total": 40,
                "offset": 27,
                "truncated": False,
            },
        ]
        asked: list[int] = []

        def enumerate_fields(path, *, offset=0):
            asked.append(offset)
            return windows[len(asked) - 1]

        seen: list[str] = []
        offset = 0
        for _ in range(10):
            payload = enumerate_fields("p", offset=offset)
            names = [f["n"] for f in payload["fields"]]
            if not names:
                break
            seen.extend(names)
            offset += len(names)
            if not payload["truncated"]:
                break
        assert asked == [0, 27]
        assert len(seen) == 40
        assert len(set(seen)) == 40, "이름이 겹쳤다 — 전진 폭이 틀렸다"


class TestTheBuilderAndTheLinkAgreeOnTheToken:
    """빌더와 링크가 각자 토큰을 만들면 갈라진다 — 하나가 다른 하나를 쓰는지 본다."""

    def test_the_link_uses_the_shared_builder(self):
        link = _RecordingLink()
        link.enumerate_fields("DataPool/Sequences/My Seq", offset=8)
        request_id = link.lines[-1].split("introspect ")[1].split(" ")[0]
        assert link.lines[-1] == build_introspect_query(
            request_id, "DataPool/Sequences/My Seq", offset=8
        )
