"""좌표 판독의 왕복 수 — 리그가 커져도 한도에 걸리지 않는다.

실기 2026-08-18: 80대 리그에서 `get_spatial_context`가 픽스처당 속성 4회(실측
66.7 ms/회)와 슬롯 복구 조회까지 써 ~26초를 쓰고, 이전 한도(240=60대)에서는
«3D 좌표 응답이 … 조회 한도에 도달»로 모든 전체-리그 요청을 거절했다. 200대면
왕복 ~1,000회 ≈ 67초로 한도를 올려도 답이 아니다. 그래서 응답기 1.6.0의 `props`
페이지 판독을 쓰고, 한도는 **왕복이 실제로 드는 경로에만** 적용된다.
"""

from __future__ import annotations

from server.orchestrator.tools import (
    SPATIAL_FIXTURE_PROPERTIES,
    SPATIAL_PROPERTY_QUERY_CAP,
    read_spatial_fixtures,
)

FIXTURES_PATH = "Patch/Stages/1/Fixtures"
#: 응답기 실측 상한: 한 state 응답은 24개까지만 싣는다.
RESPONDER_PAGE = 24


class BatchRig:
    """`props`를 답하는 콘솔 — 실제 응답기 1.6.0의 모양.

    `state`는 실물처럼 첫 24개만 싣고 `truncated`를 세운다. `query_property`는
    호출되면 시험이 실패한다: 배치가 있는데 낱개 조회가 나갔다면 가속이 무효다.
    """

    def __init__(self, count: int, *, page: int = 40) -> None:
        self.count = count
        self.page = page
        self.state_calls: list[str] = []
        self.props_calls: list[tuple[int, int]] = []
        self.property_calls: list[tuple[str, str]] = []

    def query_state(self, path: str) -> dict:
        self.state_calls.append(path)
        listed = min(self.count, RESPONDER_PAGE)
        return {
            "ok": True,
            "path": path,
            "truncated": self.count > listed,
            "node": {"childCount": self.count},
            "children": [
                {"i": slot, "name": f"Fx {slot}", "class": "Fixture"}
                for slot in range(1, listed + 1)
            ],
        }

    def query_properties(self, path: str, start_slot: int, count: int, names) -> dict:
        self.props_calls.append((start_slot, count))
        rows = []
        slot = start_slot
        while slot <= self.count and len(rows) < min(count, self.page):
            values = {
                "name": f"Fx {slot}",
                "fid": str(slot),
                "posx": f"{slot}.0",
                "posy": "0.0",
                "posz": "8.0",
            }
            rows.append({"i": slot, "p": {key: values[key] for key in names if key in values}})
            slot += 1
        reply = {"ok": True, "path": path, "node": {"childCount": self.count}, "rows": rows}
        if slot <= self.count:
            reply["next"] = slot
        return reply

    def query_property(self, path: str, property_name: str) -> dict:
        self.property_calls.append((path, property_name))
        raise AssertionError(f"배치가 있는데 낱개 속성 조회가 나갔다: {path} {property_name}")


class TestARigBiggerThanTheCap:
    def test_two_hundred_fixtures_read_completely(self):
        # [HARD] 이 한 줄이 사용자의 질문이다 — 200대에서도 거절되지 않는가.
        rig = BatchRig(200)
        reply = read_spatial_fixtures(rig, rig, FIXTURES_PATH, SPATIAL_PROPERTY_QUERY_CAP)

        assert "fixtures" in reply, reply.get("guidance")
        assert reply["coverage"] == {"judged": 200, "of": 200, "complete": True}
        assert reply["roundtrip_capped"] is False
        assert reply["truncated"] is False

    def test_it_costs_a_handful_of_round_trips_not_hundreds(self):
        rig = BatchRig(200)
        read_spatial_fixtures(rig, rig, FIXTURES_PATH, SPATIAL_PROPERTY_QUERY_CAP)

        # 200대 x 4속성 = 800회였던 자리다. 페이지 판독이면 한 자릿수여야 한다.
        assert len(rig.props_calls) <= 6, rig.props_calls
        assert rig.property_calls == []
        # 슬롯 복구 조회도 사라진다: 컨테이너 조회는 한 번뿐이다.
        assert rig.state_calls == [FIXTURES_PATH]

    def test_the_coordinates_are_the_ones_the_console_gave(self):
        rig = BatchRig(30)
        reply = read_spatial_fixtures(rig, rig, FIXTURES_PATH, SPATIAL_PROPERTY_QUERY_CAP)

        by_fid = {record["fid"]: record for record in reply["fixtures"]}
        assert by_fid[29]["x"] == 29.0
        assert by_fid[29]["z"] == 8.0
        # 목록에 실리지 않았던 슬롯(25~30)도 이름이 온다 — 페이지가 실어 왔다.
        assert by_fid[29]["name"] == "Fx 29"


class TestTheFallbackStaysExactlyAsItWas:
    def test_a_console_without_the_batch_verb_still_walks(self):
        class OldRig(BatchRig):
            """1.5.0 응답기 — `props`를 모른다."""

            def query_properties(self, *args, **kwargs):
                raise RuntimeError("unknown verb: props")

            def query_property(self, path: str, property_name: str) -> dict:
                self.property_calls.append((path, property_name))
                slot = int(path.rsplit("/", 1)[-1])
                value = {
                    "fid": str(slot),
                    "posx": f"{slot}.0",
                    "posy": "0.0",
                    "posz": "8.0",
                }[property_name]
                return {"ok": True, "value": value}

        rig = OldRig(10)
        reply = read_spatial_fixtures(rig, rig, FIXTURES_PATH, SPATIAL_PROPERTY_QUERY_CAP)

        assert "fixtures" in reply
        assert len(rig.property_calls) == 10 * len(SPATIAL_FIXTURE_PROPERTIES)

    def test_the_cap_still_bites_on_the_walking_path(self):
        # 배치가 없으면 한도는 그대로 살아 있어야 한다 — 그것이 부분 판독 신호다.
        class OldRig(BatchRig):
            def query_properties(self, *args, **kwargs):
                raise RuntimeError("unknown verb: props")

            def query_property(self, path: str, property_name: str) -> dict:
                self.property_calls.append((path, property_name))
                return {"ok": True, "value": "1.0"}

        over = SPATIAL_PROPERTY_QUERY_CAP // len(SPATIAL_FIXTURE_PROPERTIES) + 5
        rig = OldRig(over)
        reply = read_spatial_fixtures(rig, rig, FIXTURES_PATH, SPATIAL_PROPERTY_QUERY_CAP)

        assert "fixtures" not in reply
        assert reply["roundtrip_capped"] is True
        assert len(rig.property_calls) == SPATIAL_PROPERTY_QUERY_CAP


class TestAPartialBatchDegradesInsteadOfLying:
    def test_a_page_that_fails_midway_falls_back_for_the_rest(self):
        class HalfRig(BatchRig):
            def query_properties(self, path, start_slot, count, names):
                if start_slot > 1:
                    raise RuntimeError("link dropped")
                return super().query_properties(path, start_slot, 20, names)

            def query_property(self, path: str, property_name: str) -> dict:
                self.property_calls.append((path, property_name))
                slot = int(path.rsplit("/", 1)[-1])
                return {"ok": True, "value": str(slot) if property_name == "fid" else "1.0"}

        rig = HalfRig(30, page=20)
        reply = read_spatial_fixtures(rig, rig, FIXTURES_PATH, SPATIAL_PROPERTY_QUERY_CAP)

        # 배치가 답한 20대는 왕복 0회, 나머지는 낱개 조회로 메운다.
        assert "fixtures" in reply
        assert reply["coverage"]["judged"] == 30
        assert len(rig.property_calls) == 10 * len(SPATIAL_FIXTURE_PROPERTIES)
