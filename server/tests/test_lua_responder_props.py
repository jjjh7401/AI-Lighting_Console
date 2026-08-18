"""`props` — MANY children x MANY properties in ONE round trip (responder 1.6.0).

왜 있는가: `prop`은 속성 하나당 왕복 1회이고 실측 66.7 ms다. 80대 리그의 좌표를
읽으려면 속성 왕복 ~320회에 슬롯 복구 조회 ~80회가 더해져 약 26초가 걸렸고
(2026-08-18 실측), 200대 리그는 어떤 대화형 예산에도 들어오지 못했다. 한도를
올리는 것은 증상 처방이므로, 페이지 단위로 받아 왕복 수를 줄인다.
"""

from __future__ import annotations

import pytest

from server.bridge.protocol import decode_payload

from .lua_mock_env import ResponderHarness

STATE_ADDRESS = "/copilot/state"


def _fixtures_env(count: int, *, sparse: bool = False, long_names: bool = False) -> str:
    """`DataPool/Fixtures`에 `Get`을 답하는 픽스처 N대를 놓는다."""
    rows = []
    for index in range(1, count + 1):
        slot = index * 3 if sparse else index  # 희소 풀: 목록 위치 != 풀 슬롯
        name = ("Robin Esprite with a deliberately long name " if long_names else "Fx ") + str(
            index
        )
        rows.append(
            f'    [{slot}] = __FIXTURE("{name}", {{ fid = "{index}", '
            f'posx = "{index}.0", posy = "0.0", posz = "8.0" }})'
        )
    body = ",\n".join(rows)
    return (
        "function __FIXTURE(name, props)\n"
        '    local n = __NODE(name, "Fixture", {})\n'
        "    n._props = props\n"
        "    function n:Get(k) return self._props[k] end\n"
        "    return n\n"
        "end\n"
        'local pool = __SPARSE("Fixtures", "Pool", {\n' + body + '\n}, "Index")\n'
        '__DATAPOOL = __NODE("Default", "DataPool", { pool })\n'
        "function DataPool() return __DATAPOOL end\n"
    )


def _reply(harness: ResponderHarness, request: str) -> dict:
    harness.main(None, request)
    sent = harness.sent()
    assert sent, f"no reply for {request!r}"
    assert sent[-1].address == STATE_ADDRESS
    return decode_payload(sent[-1].payload)


class TestOneTripManyFixtures:
    def test_a_single_request_answers_every_fixture(self):
        harness = ResponderHarness(_fixtures_env(10))
        payload = _reply(harness, "props 1 DataPool/Fixtures 1 40 fid,posx,posy,posz")

        assert payload["ok"] is True
        assert payload["kind"] == "props"
        assert len(payload["rows"]) == 10
        assert payload["node"]["childCount"] == 10
        # 끝까지 읽었으면 이어받을 자리가 없다 — 그것이 `next` 부재의 뜻이다.
        assert "next" not in payload

    def test_each_row_carries_the_requested_properties(self):
        harness = ResponderHarness(_fixtures_env(3))
        payload = _reply(harness, "props 1 DataPool/Fixtures 1 40 fid,posx,posy,posz")

        first = payload["rows"][0]
        assert first["i"] == 1
        assert first["p"] == {"fid": "1", "posx": "1.0", "posy": "0.0", "posz": "8.0"}

    def test_a_name_can_be_requested_like_any_other_property(self):
        # 이름까지 한 페이지에 실리면 슬롯별 복구 조회가 아예 필요 없어진다.
        harness = ResponderHarness(_fixtures_env(2))
        payload = _reply(harness, "props 1 DataPool/Fixtures 1 40 name,fid")

        assert payload["rows"][0]["p"]["name"] == "Fx 1"

    def test_an_unknown_property_is_absent_not_fatal(self):
        harness = ResponderHarness(_fixtures_env(2))
        payload = _reply(harness, "props 1 DataPool/Fixtures 1 40 fid,nosuchprop")

        assert payload["ok"] is True
        assert "nosuchprop" not in payload["rows"][0]["p"]
        assert payload["rows"][0]["p"]["fid"] == "1"


class TestPagingIsBySlotNeverByPosition:
    def test_a_count_limit_names_the_slot_to_resume_from(self):
        harness = ResponderHarness(_fixtures_env(10))
        first = _reply(harness, "props 1 DataPool/Fixtures 1 4 fid")

        assert [row["i"] for row in first["rows"]] == [1, 2, 3, 4]
        assert first["next"] == 5

    def test_resuming_at_next_continues_without_a_gap_or_a_repeat(self):
        harness = ResponderHarness(_fixtures_env(10))
        first = _reply(harness, "props 1 DataPool/Fixtures 1 4 fid")
        second = _reply(harness, f"props 2 DataPool/Fixtures {first['next']} 4 fid")

        assert [row["i"] for row in second["rows"]] == [5, 6, 7, 8]

    def test_rows_use_the_real_pool_slot_on_a_sparse_pool(self):
        # [HARD] 목록 위치를 슬롯으로 쓰면 이웃의 좌표를 읽는다 — 이 프로토콜이
        # 다른 자리에서 이미 거부한 그 버그다.
        harness = ResponderHarness(_fixtures_env(4, sparse=True))
        payload = _reply(harness, "props 1 DataPool/Fixtures 1 40 fid")

        assert [row["i"] for row in payload["rows"]] == [3, 6, 9, 12]
        assert payload["rows"][0]["p"]["fid"] == "1"

    def test_a_start_slot_past_the_pool_returns_an_empty_page(self):
        harness = ResponderHarness(_fixtures_env(3))
        payload = _reply(harness, "props 1 DataPool/Fixtures 99 40 fid")

        assert payload["ok"] is True
        assert payload["rows"] == []
        assert "next" not in payload


class TestItNeverOverflowsTheTransport:
    def test_an_oversized_page_is_trimmed_and_resumable(self):
        # MA3 명령줄은 ~2048바이트에서 조용히 죽는다 — 페이지가 그 한도를 넘으면
        # 마지막 행을 덜어내고 이어받을 자리를 남겨야 한다.
        harness = ResponderHarness(_fixtures_env(60, long_names=True))
        payload = _reply(harness, "props 1 DataPool/Fixtures 1 60 name,fid,posx,posy,posz")

        assert len(payload["rows"]) < 60
        assert payload["next"] > 1
        assert len(harness.raw_packed()[-1]) <= 2048


class TestMalformedRequests:
    @pytest.mark.parametrize(
        "request_text",
        [
            "props 1",
            "props 1 DataPool/Fixtures",
            "props 1 DataPool/Fixtures 1",
            "props 1 DataPool/Fixtures 1 40",
            "props 1 DataPool/Fixtures x 40 fid",
        ],
    )
    def test_a_malformed_request_is_refused_with_a_usable_message(self, request_text):
        harness = ResponderHarness(_fixtures_env(2))
        payload = _reply(harness, request_text)

        assert payload["ok"] is False
        assert "props" in payload["error"]

    def test_an_unresolvable_path_is_refused_not_answered_empty(self):
        harness = ResponderHarness(_fixtures_env(2))
        payload = _reply(harness, "props 1 DataPool/NoSuchPool 1 40 fid")

        assert payload["ok"] is False
        assert payload["error"]


class TestTheOlderVerbsAreUntouched:
    def test_state_and_prop_still_answer(self):
        harness = ResponderHarness(_fixtures_env(2))

        state = _reply(harness, "props 1 DataPool/Fixtures 1 40 fid")
        assert state["ok"] is True

        single = _reply(harness, "prop 2 DataPool/Fixtures/1 fid")
        assert single["kind"] == "prop"
        assert single["value"] == "1"

    def test_the_version_advertises_the_new_verb(self):
        harness = ResponderHarness(_fixtures_env(1))
        assert harness.module["VERSION"] == "1.6.0"
