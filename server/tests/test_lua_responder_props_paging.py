"""`props` verb — offset 기반 표 값 나눠 읽기 (카드 t531, SPEC-LDBEAT-001 M1).

`.moai/reports/t525/verdict.md` §② 실측: 그룹 소속(`SELECTIONDATA` 등 표 값
속성)이 `CONFIG.max_prop_value`(240바이트) 때문에 앞 2대만 잘려 도착했다.
`prop`(단건) 쪽은 절단이 없지만 전체 회신이 `CONFIG.max_payload`(1900바이트)
에 걸려 큰 그룹(예: 86대)에서는 응답 자체가 콘솔 명령줄 밖으로 나가지 못한다
(cmd_keyword 전송은 조용히 죽는다 — `Cmd()`는 성공을 보고한다).

이 파일은 `props <id> <PropertyName> <path> offset=<n>` 트레일링 토큰으로
표 값을 엔트리 단위로 나눠 읽는 확장을 검증한다. 토큰이 없는 기존 요청은
바이트 단위로 그대로여야 한다(회귀 금지) — 그 보증은 이 파일과
`test_lua_responder.py`의 `TestTableValueSerialization`가 함께 선다.
"""

from __future__ import annotations

import json

import pytest

from server.bridge.protocol import decode_payload

from .lua_mock_env import TABLE_PROBE_PATH, ResponderHarness, table_props_env


def _read(harness: ResponderHarness, request: str) -> dict:
    harness.main(None, request)
    return decode_payload(harness.sent()[-1].payload)


def _array_literal(values: list[str]) -> str:
    return "{ " + ", ".join(json.dumps(v) for v in values) + " }"


class TestOffsetPagingArray:
    """(i)/(ii) — 86대 그룹(배열)이 여러 페이지로 나뉘어 전부 재조립된다."""

    MEMBER_COUNT = 86

    def _members(self) -> list[str]:
        # SELECTIONDATA 와 비슷한 모양 — 그룹 소속 픽스처 이름.
        return [f"Fixture {i + 1:03d} Group Member" for i in range(self.MEMBER_COUNT)]

    def _harness(self) -> ResponderHarness:
        members = self._members()
        return ResponderHarness(
            extra_env=table_props_env(
                "{ TBL = " + _array_literal(members) + " }", order=["TBL"]
            )
        )

    def test_all_86_members_reassemble_across_pages(self):
        harness = self._harness()
        members = self._members()
        collected: list[str] = []
        offset = 0
        for _ in range(100):  # loop-prevention — pages must be far fewer than this
            payload = _read(
                harness, f"props pg{offset} TBL {TABLE_PROBE_PATH} offset={offset}"
            )
            assert payload["ok"] is True, payload
            item = payload["reads"][0]
            assert item["offset"] == offset, item
            assert item["total"] == self.MEMBER_COUNT, item
            window = json.loads(item["v"])
            assert isinstance(window, list), window
            collected.extend(window)
            if not item["truncated"]:
                break
            offset = len(collected)
        else:
            pytest.fail("offset paging never reached truncated=false within 100 pages")
        assert collected == members
        assert len(collected) == self.MEMBER_COUNT

    def test_every_page_payload_fits_the_budget(self):
        harness = self._harness()
        max_payload = int(harness.config["max_payload"])
        offset = 0
        for _ in range(100):
            harness.main(None, f"props pg{offset} TBL {TABLE_PROBE_PATH} offset={offset}")
            sent = harness.sent()[-1]
            assert len(sent.payload) <= max_payload, sent.payload
            payload = decode_payload(sent.payload)
            item = payload["reads"][0]
            window = json.loads(item["v"])
            offset += len(window)
            if not item["truncated"]:
                break
        else:
            pytest.fail("offset paging never reached truncated=false within 100 pages")


class TestOffsetPagingNoRegression:
    """(iii) — offset 토큰이 없는 요청은 바이트 단위로 그대로다."""

    def test_no_offset_reply_is_byte_identical_to_pre_change(self):
        harness = ResponderHarness(
            extra_env=table_props_env(
                "{ TBL = { zulu = 1, alpha = 2, mike = 3, bravo = 4 } }", order=["TBL"]
            )
        )
        payload = _read(harness, f"props d1 TBL {TABLE_PROBE_PATH}")
        item = payload["reads"][0]
        assert set(item) == {"n", "ok", "t", "v"}, item
        assert item["v"] == '{"alpha":2,"bravo":4,"mike":3,"zulu":1}'

    def test_no_offset_reply_has_no_offset_or_total_keys(self):
        harness = ResponderHarness(
            extra_env=table_props_env('{ TBL = { a = 1, b = "x" } }', order=["TBL"])
        )
        payload = _read(harness, f"props d2 TBL {TABLE_PROBE_PATH}")
        item = payload["reads"][0]
        assert "offset" not in item, item
        assert "total" not in item, item


class TestOffsetPagingMultiNameRejected:
    """(iv) — offset 토큰은 프로퍼티 이름 하나일 때만 허용된다."""

    def test_two_names_with_offset_is_rejected(self):
        harness = ResponderHarness(
            extra_env=table_props_env(
                '{ A = { 1, 2 }, B = { 3, 4 } }', order=["A", "B"]
            )
        )
        payload = _read(harness, f"props m1 A,B {TABLE_PROBE_PATH} offset=0")
        assert payload["ok"] is False, payload
        assert payload["reads"] == []
        assert "offset paging takes exactly one property name" in payload["error"]

    def test_single_name_with_offset_is_accepted(self):
        harness = ResponderHarness(
            extra_env=table_props_env('{ A = { 1, 2 } }', order=["A"])
        )
        payload = _read(harness, f"props m2 A {TABLE_PROBE_PATH} offset=0")
        assert payload["ok"] is True, payload


class TestOffsetPagingBeyondTotal:
    """(v) — offset >= total 은 빈 컨테이너 + truncated=false."""

    def test_offset_at_total_yields_empty_untruncated_container(self):
        harness = ResponderHarness(
            extra_env=table_props_env("{ TBL = { 1, 2, 3 } }", order=["TBL"])
        )
        payload = _read(harness, f"props o1 TBL {TABLE_PROBE_PATH} offset=3")
        item = payload["reads"][0]
        assert item["total"] == 3, item
        assert item["offset"] == 3, item
        assert item["truncated"] is False, item
        assert json.loads(item["v"]) == []

    def test_offset_past_total_yields_empty_untruncated_container(self):
        harness = ResponderHarness(
            extra_env=table_props_env("{ TBL = { 1, 2, 3 } }", order=["TBL"])
        )
        payload = _read(harness, f"props o2 TBL {TABLE_PROBE_PATH} offset=999")
        item = payload["reads"][0]
        assert item["total"] == 3, item
        assert item["offset"] == 999, item
        assert item["truncated"] is False, item
        assert json.loads(item["v"]) == []


class TestOffsetPagingObjectShaped:
    """(vi) — 해시(객체) 모양 표도 엔트리 단위로 나뉜다."""

    def test_hash_table_paginates_by_whole_entries(self):
        entries = {f"k{i:02d}": f"value-{i:02d}" for i in range(10)}
        props_lua = (
            "{ TBL = { "
            + ", ".join(f'{k} = "{v}"' for k, v in entries.items())
            + " } }"
        )
        harness = ResponderHarness(extra_env=table_props_env(props_lua, order=["TBL"]))
        # 엔트리 1~2개만 들어가는 예산으로 강제로 여러 페이지를 만든다
        # (전체 10개 기본 예산(1900)에선 한 페이지에 다 들어가 버린다 —
        # 실측: 450 바이트에서 페이지당 2개씩, 총 5페이지).
        harness.config["max_payload"] = 450
        collected: dict[str, str] = {}
        offset = 0
        for _ in range(50):
            payload = _read(
                harness, f"props h{offset} TBL {TABLE_PROBE_PATH} offset={offset}"
            )
            assert payload["ok"] is True, payload
            item = payload["reads"][0]
            window = json.loads(item["v"])
            assert isinstance(window, dict), window
            collected.update(window)
            if not item["truncated"]:
                break
            offset += len(window)
        else:
            pytest.fail("hash offset paging never reached truncated=false within 50 pages")
        assert collected == entries

    def test_zero_fitting_entries_returns_empty_container_not_a_stall(self):
        """엔트리 하나도 못 들어가면 빈 컨테이너 + truncated=true — 무한루프 없음."""
        entries = {f"k{i:02d}": "V" * 100 for i in range(5)}
        props_lua = (
            "{ TBL = { "
            + ", ".join(f'{k} = "{v}"' for k, v in entries.items())
            + " } }"
        )
        harness = ResponderHarness(extra_env=table_props_env(props_lua, order=["TBL"]))
        harness.config["max_payload"] = 60  # wrapper 조차 못 드는 예산
        payload = _read(harness, f"props h2 TBL {TABLE_PROBE_PATH} offset=0")
        item = payload["reads"][0]
        assert json.loads(item["v"]) == {}
        assert item["truncated"] is True, item
        assert item["total"] == 5, item


class TestOffsetPagingNonTable:
    """(vii) — 비-테이블 값에 offset 토큰은 기존 경로와 동일하게 처리된다."""

    def test_non_table_value_with_offset_behaves_like_no_offset(self):
        harness = ResponderHarness(
            extra_env=table_props_env('{ STR = "plain-value" }', order=["STR"])
        )
        with_offset = _read(harness, f"props n1 STR {TABLE_PROBE_PATH} offset=0")
        without_offset = _read(harness, f"props n2 STR {TABLE_PROBE_PATH}")
        item_with = with_offset["reads"][0]
        item_without = without_offset["reads"][0]
        assert item_with["v"] == item_without["v"] == "plain-value"
        assert "offset" not in item_with, item_with
        assert "total" not in item_with, item_with

    def test_non_table_value_with_offset_still_respects_max_prop_value(self):
        long_value = "V" * 500
        harness = ResponderHarness(
            extra_env=table_props_env(f'{{ STR = "{long_value}" }}', order=["STR"])
        )
        harness.config["max_prop_value"] = 50
        payload = _read(harness, f"props n3 STR {TABLE_PROBE_PATH} offset=0")
        item = payload["reads"][0]
        assert item["truncated"] is True, item
        assert len(item["v"]) <= 50, item


class TestOffsetPagingInvalidToken:
    """부정 대조군 — 잘못된 offset 토큰은 에러가 아니라 0으로 降格된다."""

    @pytest.mark.parametrize("token", ["offset=-3", "offset=abc", "offset=1.5", "offset="])
    def test_invalid_offset_degrades_to_zero(self, token):
        harness = ResponderHarness(
            extra_env=table_props_env("{ TBL = { 1, 2, 3 } }", order=["TBL"])
        )
        payload = _read(harness, f"props iv1 TBL {TABLE_PROBE_PATH} {token}")
        assert payload["ok"] is True, payload
        item = payload["reads"][0]
        assert item["offset"] == 0, item
        assert item["total"] == 3, item
