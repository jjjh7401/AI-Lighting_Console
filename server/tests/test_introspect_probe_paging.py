"""t104 — `--all-pages` 페이징 루프가 **멈추는가**.

이 루프의 실패는 예외가 아니라 **무한 루프**다. 창 1을 영원히 다시 읽으면
실기 창에서 붙잡고 있을 시간이 없다. 그래서 멈춤 조건을 전부 검사로 못박는다:

1. 정상 — truncated 가 false 가 되면 멈춘다
2. 빈 창 — 이름이 0개면 멈춘다
3. offset 에코 없음 — 1.6.2 이전 응답기다, 페이징 불가로 보고하고 멈춘다
4. 에코 불일치 — offset 을 무시하는 응답기다, 같은 창을 반복하지 않고 멈춘다

3·4 는 「조용한 반복」을 막는 자리이므로 대조군(정상 경로)과 함께 잰다.

순수 검증이다. 콘솔·네트워크 접촉 0.
"""

from __future__ import annotations

from server.tools.introspect_probe import _page_to_exhaustion


class _Port:
    def __init__(self, windows):
        self.windows = list(windows)
        self.asked = []

    def enumerate_fields(self, path, *, offset=0):
        self.asked.append(offset)
        if not self.windows:
            raise AssertionError("루프가 준비된 창보다 더 물었다 — 멈추지 않았다")
        return self.windows.pop(0)


def _window(names, *, offset, truncated, echo=True):
    payload = {
        "ok": True,
        "kind": "introspect",
        "fields": [{"n": n, "t": "string"} for n in names],
        "total": 40,
        "truncated": truncated,
    }
    if echo:
        payload["offset"] = offset
    return payload


class TestTheLoopTerminates:
    def test_a_normal_two_window_walk_merges_and_stops(self):
        port = _Port(
            [
                _window([f"P{i}" for i in range(27)], offset=0, truncated=True),
                _window([f"P{i}" for i in range(27, 40)], offset=27, truncated=False),
            ]
        )
        result = _page_to_exhaustion(port, "p", 0)
        assert port.asked == [0, 27], "받은 개수만큼 전진하지 않았다"
        assert result["paging"] == "complete"
        assert [f["n"] for f in result["fields"]] == [f"P{i}" for i in range(40)]

    def test_an_empty_window_stops(self):
        port = _Port([_window([], offset=99, truncated=False)])
        result = _page_to_exhaustion(port, "p", 99)
        assert result["paging"] == "complete"
        assert result["fields"] == []

    def test_a_missing_offset_echo_stops_and_says_paging_is_unsupported(self):
        """🔴 1.6.1 응답기가 아직 배치돼 있으면 여기로 온다."""
        port = _Port([_window(["A"], offset=0, truncated=True, echo=False)])
        result = _page_to_exhaustion(port, "p", 0)
        assert result["paging"] == "unsupported"
        assert port.asked == [0], "페이징 불가인데 또 물었다"

    def test_an_echo_mismatch_stops_instead_of_repeating_the_window(self):
        """offset 을 무시하는 응답기 — 에코가 0으로 고정된다."""
        port = _Port(
            [
                _window(["A", "B"], offset=0, truncated=True),
                _window(["A", "B"], offset=0, truncated=True),
            ]
        )
        result = _page_to_exhaustion(port, "p", 0)
        assert result["paging"] == "stalled"
        assert port.asked == [0, 2], port.asked

    def test_every_window_is_recorded_for_the_reader(self):
        """무엇을 물었고 무엇이 왔는지가 남아야 사후에 재현된다."""
        port = _Port(
            [
                _window([f"P{i}" for i in range(27)], offset=0, truncated=True),
                _window([f"P{i}" for i in range(27, 40)], offset=27, truncated=False),
            ]
        )
        result = _page_to_exhaustion(port, "p", 0)
        assert [w["requested_offset"] for w in result["windows"]] == [0, 27]
        assert [w["received"] for w in result["windows"]] == [27, 13]
