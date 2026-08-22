"""핸들-이름 번역 — SPEC-COPILOT-PARITY-001 M1 (결함 D2).

콘솔이 픽스처의 FixtureType 프로퍼티로 이름이 아니라 "FixtureType <슬롯>"
핸들을 돌려주는 갈래를 다룬다. AC-PARITY-007/008/009/010.
"""

from __future__ import annotations

from server.prechk.inventory import (
    UNTRANSLATED_NO_TABLE,
    UNTRANSLATED_SLOT_ABSENT,
    UNTRANSLATED_SLOT_UNSEEN,
    UNTRANSLATED_TREE_UNREADABLE,
    read_inventory,
    translate_fixture_type,
)
from server.prechk.mode_read import TypeNameRead, read_fixture_type_names

ROOT = "Patch/FixtureTypes"


class _Tree:
    """트리 판독 하나만 흉내낸다 — 넘긴 페이로드를 그대로 돌려준다."""

    def __init__(self, payload: object, boom: bool = False) -> None:
        self.payload = payload
        self.boom = boom
        self.calls: list[str] = []

    def query_state(self, path: str) -> object:
        self.calls.append(path)
        if self.boom:
            raise RuntimeError("응답 없음")
        return self.payload


def _tree(pairs: list[tuple[int, str]], truncated: bool = False) -> _Tree:
    return _Tree(
        {
            "ok": True,
            "truncated": truncated,
            "node": {"childCount": len(pairs) + (1 if truncated else 0)},
            "children": [{"i": slot, "name": name} for slot, name in pairs],
        }
    )


# --- 신설 판독 -------------------------------------------------------------


def test_the_tree_read_returns_every_slot_name_pair_in_one_query():
    tree = _tree([(4, "Robin Spiider"), (10, "Source 4 LED")])

    answer = read_fixture_type_names(tree, root=ROOT)

    assert answer.attempted is True
    assert answer.by_slot() == {4: "Robin Spiider", 10: "Source 4 LED"}
    # 질의 1회 — 타입마다 캐묻지 않는다.
    assert tree.calls == [ROOT]


def test_an_unanswered_tree_is_not_reported_as_an_empty_library():
    # attempted=False 와 "읽었는데 비었다" 를 뭉개면 판독 실패가
    # "슬롯 없음" 으로 둔갑한다.
    answer = read_fixture_type_names(_Tree(None, boom=True), root=ROOT)

    assert answer.attempted is False
    assert answer.by_slot() == {}
    assert answer.detail


def test_a_refusing_tree_is_attempted_false_and_names_nothing():
    """페이로드가 ok:false 로 거절한 갈래.

    예외를 던지는 갈래(위)와 값으로 거절하는 갈래는 코드가 다르다. 둘 다
    attempted=False 여야 한다 — 「트리가 답하지 않았다」는 같은 사건이다.
    """
    answer = read_fixture_type_names(_Tree({"ok": False}), root=ROOT)

    assert answer.attempted is False
    assert answer.by_slot() == {}
    assert answer.detail


def test_a_malformed_child_is_attempted_true_and_still_names_nothing():
    """트리는 답했으나 자식에 슬롯/이름이 없는 갈래.

    바로 위와 결과(이름 0건)는 같지만 attempted 가 다르다 — 이쪽은 트리가
    **답했다**. 둘을 뭉치면 「응답이 없다」와 「응답이 이상하다」가 같아 보이고,
    전자는 재시도할 자리이고 후자는 아니다.
    """
    answer = read_fixture_type_names(
        _Tree({"ok": True, "children": [{"i": 1, "name": 123}]}), root=ROOT
    )

    assert answer.attempted is True
    assert answer.by_slot() == {}
    assert "슬롯" in answer.detail


def test_a_truncated_listing_keeps_the_pairs_that_did_arrive():
    tree = _tree([(4, "Robin Spiider")], truncated=True)

    answer = read_fixture_type_names(tree, root=ROOT)

    assert answer.attempted is True
    assert answer.by_slot() == {4: "Robin Spiider"}
    assert "절단" in answer.detail


# --- 번역 계약 -------------------------------------------------------------


def test_a_handle_becomes_the_name_its_slot_declares():
    # AC-PARITY-007
    value, untranslated = translate_fixture_type("FixtureType 10", {10: "Source 4 LED"})

    assert value == "Source 4 LED"
    assert untranslated is None


def test_a_name_passes_through_unchanged_even_when_absent_from_the_library():
    # AC-PARITY-008 — 번역기는 이름을 검증하는 자리가 아니다. 라이브러리에
    # 없는 이름을 거르면 조용한 두 번째 실패 경로가 생긴다.
    known, known_mark = translate_fixture_type("Robin Spiider", {4: "Robin Spiider"})
    unknown, unknown_mark = translate_fixture_type("듣도 보도 못한 기종", {4: "Robin Spiider"})

    assert (known, known_mark) == ("Robin Spiider", None)
    assert (unknown, unknown_mark) == ("듣도 보도 못한 기종", None)


def test_an_unresolvable_handle_keeps_the_raw_value_and_says_why():
    # AC-PARITY-009 — 표식만 검사하면 공허하다. 원값과 표식을 둘 다 단언한다.
    # 두 사유를 가르는 이유: 표 부재는 이 경로가 트리를 안 읽었다는 뜻(순서
    # 결함, 고칠 수 있다)이고, 슬롯 부재는 트리를 읽었는데 그 슬롯이 없다는
    # 뜻(리그 사실)이다. 뭉치면 고칠 수 있는 것과 없는 것이 같아 보인다.
    absent_value, absent_reason = translate_fixture_type("FixtureType 99", {4: "Robin Spiider"})
    no_table_value, no_table_reason = translate_fixture_type("FixtureType 4", None)

    assert (absent_value, absent_reason) == ("FixtureType 99", UNTRANSLATED_SLOT_ABSENT)
    assert (no_table_value, no_table_reason) == ("FixtureType 4", UNTRANSLATED_NO_TABLE)


def test_the_same_name_on_two_slots_is_not_ambiguous_forward():
    # AC-PARITY-010 — 라이브에서 Robin Spiider 가 슬롯 4 와 12 둘 다에 있다.
    # 오프라인 슬롯 번호는 실기와 다르므로 번호가 아니라 "같은 이름 두 슬롯"
    # 이라는 형상만 재현한다. 정방향은 둘 다 같은 답을 낸다.
    table = read_fixture_type_names(
        _tree([(4, "Robin Spiider"), (12, "Robin Spiider")]), root=ROOT
    ).by_slot()

    first, first_mark = translate_fixture_type("FixtureType 4", table)
    second, second_mark = translate_fixture_type("FixtureType 12", table)

    assert first == second == "Robin Spiider"
    assert first_mark is None and second_mark is None


def test_a_missing_reading_is_not_invented_into_a_name():
    assert translate_fixture_type(None, {4: "Robin Spiider"}) == (None, None)


# --- 순서 의존 -------------------------------------------------------------


class _Rig:
    """read_inventory 가 쓰는 두 판독만 갖춘 최소 콘솔."""

    def __init__(self, types: list[str]) -> None:
        self.types = types
        self.state_calls: list[str] = []

    def query_state(self, path: str) -> dict:
        self.state_calls.append(path)
        children = [
            {"i": slot, "name": "fx " + str(slot), "class": "Fixture"}
            for slot in range(1, len(self.types) + 1)
        ]
        return {
            "ok": True,
            "path": path,
            "truncated": False,
            "node": {"childCount": len(children)},
            "children": children,
        }

    def query_property(self, path: str, property_name: str) -> dict:
        slot = int(path.rsplit("/", 1)[-1])
        value = {
            "Patch": "1." + str(slot).zfill(3),
            "FixtureType": self.types[slot - 1],
            "Mode": "Mode 1",
            "Name": "fx " + str(slot),
        }[property_name]
        return {"ok": True, "path": path, "property": property_name, "value": value}


def test_without_a_table_a_handle_is_marked_not_quietly_accepted():
    """대응표를 안 넘긴 경로에서 번역이 조용히 사라지지 않는다.

    판독을 공유하면서 생긴 순서 의존을 여기에 고정한다. 트리를 읽지 않은
    호출자는 표가 없고, 그때 핸들은 "번역됨"으로 지나가는 것이 아니라
    no_type_table 로 표시된다. 이 테스트가 없으면 나중에 호출 순서가 바뀌었을
    때 번역이 조용히 사라진다.
    """
    rig = _Rig(["FixtureType 4", "FixtureType 4"])

    inventory = read_inventory(rig)

    assert [record.fixture_type for record in inventory.fixtures] == [
        "FixtureType 4",
        "FixtureType 4",
    ]
    assert [record.fixture_type_untranslated for record in inventory.fixtures] == [
        UNTRANSLATED_NO_TABLE,
        UNTRANSLATED_NO_TABLE,
    ]
    # 그리고 스스로 트리를 읽지 않았다 — 예산 가드가 지키는 성질이다.
    assert not [call for call in rig.state_calls if "FixtureTypes" in call]


def test_with_a_table_the_same_rig_translates_and_reads_no_extra_tree():
    # 비공허성 — 위 테스트가 "표가 없어서" 실패한 것이지 번역이 아예
    # 동작하지 않아서가 아님을 같은 리그로 보인다.
    rig = _Rig(["FixtureType 4", "FixtureType 4"])

    inventory = read_inventory(
        rig, type_names=TypeNameRead(attempted=True, pairs=((4, "Robin Spiider"),))
    )

    assert [record.fixture_type for record in inventory.fixtures] == [
        "Robin Spiider",
        "Robin Spiider",
    ]
    assert [record.fixture_type_untranslated for record in inventory.fixtures] == [
        None,
        None,
    ]
    assert not [call for call in rig.state_calls if "FixtureTypes" in call]


def test_an_unreadable_tree_is_not_reported_as_a_rig_fact():
    """감사 D-1 — 판독 실패가 slot_absent 로 보고되던 자리.

    두 사건은 결과가 같다(이름 0건). 그러나 slot_absent 를 읽은 사람은 리그를
    손보러 가고, 실제로 필요한 것은 재조회다. by_slot() 만 넘기면 두 사건이
    똑같은 빈 표로 도착해 이 구분이 사라지므로, 판독 결과를 통째로 넘긴다.
    """
    rig = _Rig(["FixtureType 4"])

    unreadable = read_inventory(rig, type_names=TypeNameRead(attempted=False))
    declares_nothing = read_inventory(rig, type_names=TypeNameRead(attempted=True))

    assert unreadable.fixtures[0].fixture_type == "FixtureType 4"
    assert unreadable.fixtures[0].fixture_type_untranslated == UNTRANSLATED_TREE_UNREADABLE
    # 대조군 — 같은 「이름 0건」이지만 사유가 다르다.
    assert declares_nothing.fixtures[0].fixture_type_untranslated == UNTRANSLATED_SLOT_ABSENT
    assert UNTRANSLATED_TREE_UNREADABLE != UNTRANSLATED_SLOT_ABSENT != UNTRANSLATED_NO_TABLE


def test_a_slot_missing_from_a_truncated_listing_is_unseen_not_absent():
    """절단된 목록에서 안 보인 슬롯을 「없다」로 단정하지 않는다.

    이 저장소는 이미 「절단이 무효화하는 것은 부정 결론뿐이다」를 규약으로 갖고
    있고(결함 D1 계열), slot_absent 는 바로 그 부정 결론이다. 전수 목록에서
    안 보이는 것과 잘린 목록에서 안 보이는 것은 다른 사건이다.
    """
    rig = _Rig(["FixtureType 4"])
    whole = read_fixture_type_names(_tree([(10, "Source 4 LED")]), root=ROOT)
    cut = read_fixture_type_names(_tree([(10, "Source 4 LED")], truncated=True), root=ROOT)

    assert whole.truncated is False and cut.truncated is True

    absent = read_inventory(rig, type_names=whole).fixtures[0]
    unseen = read_inventory(rig, type_names=cut).fixtures[0]

    assert absent.fixture_type_untranslated == UNTRANSLATED_SLOT_ABSENT
    assert unseen.fixture_type_untranslated == UNTRANSLATED_SLOT_UNSEEN
    # 원값은 양쪽 다 보존된다 — 표식만 검사하면 공허하다.
    assert absent.fixture_type == unseen.fixture_type == "FixtureType 4"
