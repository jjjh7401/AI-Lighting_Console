"""핸들-이름 번역 — SPEC-COPILOT-PARITY-001 M1 (결함 D2).

콘솔이 픽스처의 FixtureType 프로퍼티로 이름이 아니라 "FixtureType <슬롯>"
핸들을 돌려주는 갈래를 다룬다. AC-PARITY-007/008/009/010.
"""

from __future__ import annotations

from server.prechk.inventory import (
    UNTRANSLATED_LISTING_SHAPE_INVALID,
    UNTRANSLATED_NO_TABLE,
    UNTRANSLATED_SLOT_ABSENT,
    UNTRANSLATED_SLOT_UNSEEN,
    UNTRANSLATED_TREE_UNREADABLE,
    read_inventory,
    translate_fixture_type,
)
from server.prechk.mode_read import (
    TypeNameRead,
    read_fixture_type_names,
    read_type_mode_widths,
)

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
    assert "전수 확인 불가" in answer.detail and "선언 총계보다 짧다" in answer.detail


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

    assert whole.whole_unconfirmed is False and cut.whole_unconfirmed is True

    absent = read_inventory(rig, type_names=whole).fixtures[0]
    unseen = read_inventory(rig, type_names=cut).fixtures[0]

    assert absent.fixture_type_untranslated == UNTRANSLATED_SLOT_ABSENT
    assert unseen.fixture_type_untranslated == UNTRANSLATED_SLOT_UNSEEN
    # 원값은 양쪽 다 보존된다 — 표식만 검사하면 공허하다.
    assert absent.fixture_type == unseen.fixture_type == "FixtureType 4"


def test_a_malformed_listing_is_not_reported_as_a_rig_fact():
    """감사 N-1 — 형태 불량이 slot_absent 로 나가던 자리.

    slot_absent 의 계약은 「트리가 **전수** 답했고 그 슬롯을 선언하지 않는다 —
    리그 사실이며 재조회해도 같다」다. 자식에 슬롯/이름이 없는 응답은 그 계약의
    「전수 답했다」를 만족하지 않는다. 지시되는 행동이 다르다 — 고칠 곳은
    리그가 아니라 **판독 쪽**이다.

    판독기의 분류(attempted=True)는 건드리지 않는다. 「응답이 없다」와
    「응답이 이상하다」를 가른 것은 이 카드가 세운 doctrine 이고
    fc37abc 의 테스트가 그것을 고정하고 있다 — 하류 사유만 늘린다.
    """
    malformed = _Tree({"ok": True, "children": [{"i": 1, "name": 123}]})
    read = read_fixture_type_names(malformed, root=ROOT)

    # 판독기 분류는 그대로 — 트리는 답했다.
    assert read.attempted is True
    assert read.whole_unconfirmed is True
    assert read.pairs == ()

    rec = read_inventory(_Rig(["FixtureType 4"]), type_names=read).fixtures[0]

    assert rec.fixture_type == "FixtureType 4"
    assert rec.fixture_type_untranslated == UNTRANSLATED_LISTING_SHAPE_INVALID


def test_an_empty_listing_is_not_a_rig_fact():
    """코드리뷰 #1 — 「자식 0개」를 「전수 답했고 비었다」로 읽던 자리.

    **이 테스트는 앞선 판본을 뒤집는다.** 이전에는 빈 목록을 slot_absent 로
    비준했고 그 판정이 감사 3회를 통과했다. 뒤집는 근거는 형제 모듈의 원문이다 —
    footprint.py 의 walk_mode_widths 는 같은 페이로드에 whole=False 를 강제하며
    13줄 주석으로 이유를 적어 뒀다: 응답기의 safe_children 은 Children() 과
    Count() 가 둘 다 실패하면 빈 표를 돌려주고 childCount 가 그 같은 빈 판독에서
    파생되므로, childCount == len(children) == 0 이고 truncated 도 안 붙는다.
    **「비었다」와 「못 읽었다」가 구별되지 않는다.**

    두 모듈이 같은 페이로드에 다른 답을 내면 그것이 다음 결함이므로 맞춘다.
    """
    read = read_fixture_type_names(_tree([]), root=ROOT)

    assert read.attempted is True and read.pairs == ()
    assert read.whole_unconfirmed is True

    rec = read_inventory(_Rig(["FixtureType 4"]), type_names=read).fixtures[0]

    assert rec.fixture_type_untranslated == UNTRANSLATED_SLOT_UNSEEN


def test_a_whole_listing_without_the_slot_is_the_only_rig_fact():
    """대조군 — slot_absent 가 남아 있는 유일한 자리.

    선언 총계와 실제 자식 수가 맞고, 버린 자식이 없고, 그런데도 그 슬롯이
    없다. 이때만 「리그 사실」이다. 이 대조군이 없으면 위 수정이 slot_absent 를
    통째로 없애 버려도 초록이다.
    """
    read = read_fixture_type_names(_tree([(10, "Source 4 LED")]), root=ROOT)

    assert read.whole_unconfirmed is False and read.pairs == ((10, "Source 4 LED"),)

    rec = read_inventory(_Rig(["FixtureType 4"]), type_names=read).fixtures[0]

    assert rec.fixture_type_untranslated == UNTRANSLATED_SLOT_ABSENT


def test_one_slotless_child_does_not_switch_off_the_whole_rig():
    """코드리뷰 #2 — 자식 하나가 나쁘면 표 전체를 버리던 자리.

    PROTOCOL.md(응답기 1.2.0)는 i 가 슬롯을 확정 못 하면 **생략된다**고 적고,
    「서버는 이미 i 없는 자식을 이름-only 항목으로 격하한다」고 한다. 자식별
    격하가 established 관례다. 표 전체를 버리면 슬롯 미확정 타입이 하나만 있어도
    리그 전체 번역이 꺼지고 D2 가 조용히 재발한다.

    쓸 수 있는 쌍은 살리되, 버린 자식이 있으므로 목록은 **부분집합**이다 —
    없는 슬롯에 대한 부정 결론은 보류한다.
    """
    payload = {
        "ok": True,
        "truncated": False,
        "node": {"childCount": 2},
        "children": [{"i": 4, "name": "Robin Spiider"}, {"name": "슬롯 미확정 타입"}],
    }
    read = read_fixture_type_names(_Tree(payload), root=ROOT)

    # 좋은 쌍은 살아남는다 — 하나가 나쁘다고 전체가 꺼지지 않는다.
    assert read.by_slot() == {4: "Robin Spiider"}
    assert read.shape_invalid is False
    # 그러나 목록은 부분집합이다.
    assert read.whole_unconfirmed is True

    named = read_inventory(_Rig(["FixtureType 4"]), type_names=read).fixtures[0]
    missing = read_inventory(_Rig(["FixtureType 9"]), type_names=read).fixtures[0]

    assert named.fixture_type == "Robin Spiider"
    assert named.fixture_type_untranslated is None
    assert missing.fixture_type_untranslated == UNTRANSLATED_SLOT_UNSEEN


# --- P5 · 모드 판독도 자식별로 격하한다 -------------------------------------


class _ModeTree:
    """타입 목록과 모드 목록을 함께 답하는 최소 콘솔."""

    def __init__(self, type_children: list[dict]) -> None:
        self.type_children = type_children

    def query_state(self, path: str) -> dict:
        if path.endswith("/DMXModes"):
            return {
                "ok": True,
                "truncated": False,
                "node": {"childCount": 1},
                "children": [{"i": 1, "name": "Mode 1"}],
            }
        return {
            "ok": True,
            "truncated": False,
            "node": {"childCount": len(self.type_children)},
            "children": self.type_children,
        }

    def query_property(self, path: str, property_name: str) -> dict:
        return {"ok": True, "path": path, "property": property_name, "value": 49}


def test_a_slotless_type_does_not_kill_another_types_mode_read():
    """P5 — 자식 하나가 슬롯이 없으면 그 타입 모드 판독 전체를 죽이던 자리.

    파장이 라벨보다 크다: 모드를 못 읽은 타입은 mode_unresolved 로 계획돼
    **픽스처가 아예 안 패치된다.** 슬롯 미확정 타입이 라이브러리에 하나만
    있어도 멀쩡한 타입까지 함께 죽었다.

    P4(read_fixture_type_names)를 같은 규약으로 이미 고쳤는데 여기는 안
    고쳐서 **같은 저장소 안에 형제 불일치**가 있었다 — M3 전수표가 잡았다.
    """
    console = _ModeTree([{"name": "슬롯 미확정 타입"}, {"i": 4, "name": "Robin Spiider"}])

    answer = read_type_mode_widths(console, console, root=ROOT, type_name="Robin Spiider")

    assert answer.attempted is True
    assert answer.type_found is True
    assert [choice.name for choice in answer.modes] == ["Mode 1"]


def test_a_type_missing_from_a_subset_listing_is_not_declared_absent():
    """대조군 — 버린 자식이 있으면 「목록에 없다」로 단정하지 않는다.

    전수 목록에서 없는 것과 부분집합에서 안 보이는 것은 다른 사건이다.
    """
    whole = _ModeTree([{"i": 4, "name": "Robin Spiider"}])
    subset = _ModeTree([{"name": "슬롯 미확정"}, {"i": 4, "name": "Robin Spiider"}])

    gone = read_type_mode_widths(whole, whole, root=ROOT, type_name="Martin MAC")
    unsure = read_type_mode_widths(subset, subset, root=ROOT, type_name="Martin MAC")

    assert gone.type_found is False and "목록에 없다" in gone.detail
    assert unsure.type_found is False
    assert "부분집합" in unsure.detail and "단정할 수 없다" in unsure.detail


# --- SPEC-COPILOT-READBACK-002 M1 — 번역 기계 무변경 확인 -----------------------
#
# REQ-READBACK2-010: 결함은 번역기가 아니라 **호출자가 인자를 안 넘기는 것**이다.
# 아래 둘은 그 사실을 특성화한다 — 같은 번역기가, 표를 받으면 옳게 답하고
# 안 받으면 표식을 켠다. `server/prechk/**` 를 고칠 필요가 없다는 실측 근거다.


def test_the_translator_needs_only_the_table_no_change_to_its_own_code():
    """표를 넘기는 것만으로 핸들이 이름이 된다 — 기계는 그대로다."""
    tree = _tree([(12, "Robe MegaPointe")])
    table = read_fixture_type_names(tree, root=ROOT)

    assert translate_fixture_type("FixtureType 12", table.by_slot()) == (
        "Robe MegaPointe",
        None,
    )
    # 조회는 루트 1회로 끝난다 — 「Query count is 1」(mode_read.py:141).
    assert tree.calls == [ROOT]


def test_the_same_translator_marks_the_handle_when_no_table_arrives():
    """부정 대조군 — 표가 없으면 번역이 **조용히 사라지지 않고** 사유가 남는다."""
    assert translate_fixture_type("FixtureType 12", None) == (
        "FixtureType 12",
        UNTRANSLATED_NO_TABLE,
    )
