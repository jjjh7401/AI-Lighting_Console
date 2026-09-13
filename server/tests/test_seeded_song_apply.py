"""t294 — 시드로 실린 진짜 곡을 반영 경로에 태운다.

실측된 막힘 둘: 시드 타임라인(`Maroon 5 — Sugar`)은 `sequence_number` 가 0 이고
`layer_mapping` 이 아예 없다. 그래서 반영은 시퀀스 번호가 없다는 사유로 멈추거나,
멈추지 않더라도 모든 큐가 `role_unaddressed` 로 건너뛰어진다.

둘 다 **선언된 출처**로만 메운다. 이 파일이 지키는 선은 하나다 —
**없는 것이 틀린 것보다 낫다**: 콘솔이 그 이름의 그룹을 보고하지 않으면 번호를
지어내지 않고 그 큐를 사유와 함께 건너뛴다.
"""

from __future__ import annotations

import threading

import pytest

from server.design.cue_sheet_apply import (
    layer_mapping_from_console_groups,
    timeline_group_names,
)
from server.design.sugar_timeline import build_sugar_timeline
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.approval_bridge import ApprovalChannel
from server.web.session import ChatSession, SongTimelineStore
from server.web.timeline_library import SongTimelineLibrary

from .test_safety_gate import FakeConsole


class RefusingProvider:
    def complete(self, *args, **kwargs):  # pragma: no cover - 불려선 안 된다
        raise AssertionError("이 경로는 모델을 부르지 않는다")


def _groups_payload(*named: tuple[str, int]) -> dict:
    return {"children": [{"name": name, "i": number} for name, number in named]}


# -- 순수 함수: 주소록은 두 선언된 출처의 완전 일치뿐 --------------------------------


def test_the_seed_timeline_names_the_groups_it_needs() -> None:
    names = timeline_group_names(build_sugar_timeline())
    assert "KEY" in names and "BACK" in names and "MOVER-U" in names
    # 지시어 `ALL` 은 주소가 필요한 이름이 아니다.
    assert all(name.casefold() != "all" for name in names)
    # 중복 없이 한 번씩만.
    assert len(names) == len({name.casefold() for name in names})


def test_only_names_the_console_reported_get_an_address() -> None:
    payload = _groups_payload(("KEY", 11), ("BACK", 12), ("Unrelated", 99))
    mapping = layer_mapping_from_console_groups(payload, ["KEY", "BACK", "MOVER-U"])
    # 카드 t409 후속 — `role` 이 `_LAYER_GROUP_ALIASES` 로 같이 붙는다("KEY"·
    # "BACK" 은 정확 일치하는 별칭이 있다). 콘솔이 실제로 이 이름을 보고했는데
    # role 이 안 붙어 보조 컬러의 back 조회가 늘 실패하던 것이 이 자리의 결함이었다.
    assert mapping == [
        {"group_name": "KEY", "group_no": 11, "role": "key"},
        {"group_name": "BACK", "group_no": 12, "role": "back"},
    ]


def test_a_near_miss_name_is_left_unaddressed_rather_than_guessed() -> None:
    """`SIDE-L` 과 `Side L` 은 다른 이름이다 — 붙여 맞추지 않는다."""
    payload = _groups_payload(("Side L", 13), ("key", 11))
    mapping = layer_mapping_from_console_groups(payload, ["SIDE-L", "KEY"])
    # 대소문자만 접는다: `key` 는 `KEY` 와 같은 이름, `Side L` 은 `SIDE-L` 과 다르다.
    assert mapping == [{"group_name": "KEY", "group_no": 11, "role": "key"}]


def test_an_unreadable_payload_yields_no_address_book() -> None:
    assert layer_mapping_from_console_groups(None, ["KEY"]) == []
    assert layer_mapping_from_console_groups({"children": "nope"}, ["KEY"]) == []
    assert layer_mapping_from_console_groups(_groups_payload(("KEY", 11)), []) == []


# -- 끝단: 시드 곡을 편집하고 반영한다 ---------------------------------------------


@pytest.fixture
def harness(tmp_path):
    console = FakeConsole(
        state_tree={"DataPool/Groups": _groups_payload(("KEY", 11), ("BACK", 12))}
    )
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=2.0)
    gate = SafetyGate(console=console, audit=audit, approval_port=channel)
    store = SongTimelineStore()
    store.latest = build_sugar_timeline()
    sent: list[dict] = []
    session = ChatSession(
        gate=gate,
        provider=RefusingProvider(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=sent.append,
        approval_channel=channel,
        timeline_store=store,
        timeline_library=SongTimelineLibrary(tmp_path / "library.json"),
    )
    return session, console, store, sent, channel


def _run_with_auto_approval(session, sent, channel, text):
    stop = threading.Event()

    def poller():
        while not stop.is_set():
            for event in sent:
                if event.get("type") == "approval_request":
                    channel.resolve(event["request_id"], approved=True)
                    return
            stop.wait(0.01)

    thread = threading.Thread(target=poller)
    thread.start()
    try:
        return session.run_instruction(text)
    finally:
        stop.set()
        thread.join(timeout=2.0)


def _first_key_cue(store) -> int:
    for section in store.latest["sections"]:
        if "KEY" in section.get("fixture_groups", []):
            return int(section["cue_number"])
    raise AssertionError("시드에 KEY 를 쓰는 구간이 없다")


def test_the_seeded_song_applies_end_to_end_when_the_director_names_the_sequence(harness):
    session, console, store, sent, channel = harness
    cue = _first_key_cue(store)
    session.run_instruction(f"큐 {cue} 더 밝게 해줘", cue)
    assert console.executed == []  # 편집만으로는 콘솔 0건

    event = _run_with_auto_approval(session, sent, channel, "시퀀스 210에 초안을 콘솔에 반영해줘")

    assert [e for e in sent if e.get("type") == "execution_preview"]
    assert f"Store Sequence 210 Cue {cue} /Merge" in console.executed
    assert any(command.startswith("Group ") for command in console.executed)
    assert "Sequence 210" in event["text"]
    # 두 칸이 실제로 이번 경로에서 채워졌음을 답장이 말한다(조용히 채우지 않는다).
    assert "타임라인에는 번호가 없었습니다" in event["text"]
    assert "KEY=Group 11" in event["text"]
    # 시드에는 두 칸이 실제로 비어 있다 — 이 검사가 공허하지 않다는 증거.
    seed = build_sugar_timeline()
    assert seed["sequence_number"] == 0
    assert "layer_mapping" not in seed


def test_without_a_declared_sequence_number_nothing_is_written(harness):
    """시퀀스 번호를 지어내지 않는다 — 엉뚱한 곡을 덮는 것이 최악의 사고다."""
    session, console, store, sent, channel = harness
    cue = _first_key_cue(store)
    session.run_instruction(f"큐 {cue} 더 밝게 해줘", cue)
    event = _run_with_auto_approval(session, sent, channel, "초안을 콘솔에 반영해줘")
    assert "시퀀스 번호가 없습니다" in event["text"]
    assert console.executed == []


# -- t296: 컬러·페이드가 실제로 데스크에 닿는가 ---------------------------------
#
# t293 이 컬러·페이드 명령 형태를 더했지만, 브라우저 실측은 조도만 통과시켰다.
# 아래 두 검사는 2026-09-06 브라우저 실측(가짜 콘솔 9100/9101, 시퀀스 3)에서
# **받은 줄 그대로**를 고정한다 — 그 실측이 사라져도 형태가 남게.

#: 브라우저 실측에 쓴 리그와 같은 그룹 번호 배정(콘솔이 스스로 보고한 순서).
_SUGAR_RIG = (
    ("KEY", 1),
    ("BACK", 2),
    ("SIDE-L", 3),
    ("SIDE-R", 4),
    ("MOVER-U", 5),
    ("MOVER-D", 6),
    ("WASH-U", 7),
    ("WASH-D", 8),
    ("HAZE", 9),
    ("LED-W", 10),
    ("BLIND", 11),
    ("STROBE", 12),
)


@pytest.fixture
def full_rig(tmp_path):
    """Sugar 가 쓰는 이름을 전부 아는 콘솔. 주소가 잡혀야 명령이 생긴다."""
    console = FakeConsole(state_tree={"DataPool/Groups": _groups_payload(*_SUGAR_RIG)})
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=2.0)
    store = SongTimelineStore()
    store.latest = build_sugar_timeline()
    sent: list[dict] = []
    session = ChatSession(
        gate=SafetyGate(console=console, audit=audit, approval_port=channel),
        provider=RefusingProvider(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=sent.append,
        approval_channel=channel,
        timeline_store=store,
        timeline_library=SongTimelineLibrary(tmp_path / "library.json"),
    )
    return session, console, store, sent, channel


def test_a_colour_change_reaches_the_desk_as_a_colour_command(full_rig):
    """컬러 변경이 컬러 명령으로 나간다 — 실측 줄 그대로.

    큐 10 은 BACK·WASH-U·HAZE 를 쓰고 팔레트가 P1 골드앰버다. P4 핫핑크
    (#FF3C9E)로 바꾸면 백분율 축으로 (100, 24, 62) 가 된다.

    카드 t409 후속 — 콘솔이 실제로 보고한 "BACK" 그룹이 이제
    `layer_mapping_from_console_groups` 로 role 이 잡히므로, 큐 10 의
    보조 컬러("P2 웜화이트")가 그 back 그룹(Group 2)에도 실려 나간다 —
    메인 값 줄 뒤에 이어붙는 두 번째 `Group … ; Attribute 'ColorRGB…'` 절.
    """
    session, console, _store, sent, channel = full_rig
    session.run_instruction("큐 10 컬러를 P4 핫핑크로 바꿔줘", 10)
    assert console.executed == []  # 편집만으로는 콘솔 0건

    event = _run_with_auto_approval(session, sent, channel, "시퀀스 3에 초안을 콘솔에 반영해줘")

    assert (
        "Group 2 + 7 + 9 ; Attribute 'Dimmer' At 55 ; "
        "Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 24 ; "
        "Attribute 'ColorRGB_B' At 62 ; "
        "Group 2 ; Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 88 ; "
        "Attribute 'ColorRGB_B' At 69"
    ) in console.executed
    assert "Store Sequence 3 Cue 10 /Merge" in console.executed
    assert "컬러 P4 핫핑크" in event["text"]
    assert "보조컬러 P2 웜화이트" in event["text"]
    assert "미반영" not in event["text"]  # 건너뛴 큐 없음


def test_a_fade_change_reaches_the_desk_as_a_fade_command(full_rig):
    """페이드 변경이 CueFade 로 나간다 — `Property 'Fade'` 는 여전히 안 쓴다."""
    session, console, _store, sent, channel = full_rig
    session.run_instruction("큐 20 페이드 3초로 바꿔줘", 20)
    assert console.executed == []

    event = _run_with_auto_approval(session, sent, channel, "시퀀스 3에 초안을 콘솔에 반영해줘")

    assert "Store Sequence 3 Cue 20 CueFade 3 /Merge" in console.executed
    assert "Group 1 + 2 ; Attribute 'Dimmer' At 70" in console.executed
    assert not any("Property 'Fade'" in command for command in console.executed)
    assert "페이드 3초" in event["text"]
    assert "미반영" not in event["text"]


def test_groups_the_console_never_reported_are_skipped_with_a_reason(harness):
    """콘솔이 모르는 이름은 사유와 함께 건너뛴다 — 번호를 만들지 않는다."""
    session, console, store, sent, channel = harness
    target = None
    for section in store.latest["sections"]:
        if "MOVER-U" in section.get("fixture_groups", []) and "KEY" not in section.get(
            "fixture_groups", []
        ):
            target = int(section["cue_number"])
            break
    assert target is not None
    session.run_instruction(f"큐 {target} 더 밝게 해줘", target)
    event = _run_with_auto_approval(session, sent, channel, "시퀀스 210에 초안을 콘솔에 반영해줘")
    assert "MOVER-U" in event["text"]
    assert "role_unaddressed" in event["text"]
    assert all("Store Sequence" not in command for command in console.executed)
