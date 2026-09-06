"""t303 — 쇼 전에 돌리는 읽기 전용 리그 점검.

이 파일이 고정하는 것은 셋이다:

1. **네 리그 상태**가 각각 다른 답을 낸다 — 전부 맞음 / 일부 맞음 / 전부
   불일치 / **콘솔 불통**. 앞의 셋은 리그를 고치라는 답이고, 넷째는 데스크를
   켜라는 답이다. 넷째를 「일치 0」으로 보고하면 감독이 엉뚱한 것을 고친다.
2. 점검은 **콘솔 쓰기 0건**이다 — 네 경로 전부에서.
3. 점검의 대조 규칙은 반영의 대조 규칙과 **같은 함수**다 — 점검이 통과했는데
   반영이 건너뛰는 어긋남이 생기지 않는다.
"""

from __future__ import annotations

import pytest

from server.design.cue_sheet_apply import timeline_group_names
from server.design.rig_preflight import (
    ROLE_UNADDRESSED,
    UNMEASURED_NOTES,
    plan_rig_preflight,
    render_rig_preflight,
)
from server.design.sugar_timeline import build_sugar_timeline
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.approval_bridge import ApprovalChannel
from server.web.session import ChatSession, SongTimelineStore, _is_rig_preflight_request
from server.web.timeline_library import SongTimelineLibrary

from .test_safety_gate import FakeConsole


class RefusingProvider:
    def complete(self, *args, **kwargs):  # pragma: no cover - 불려선 안 된다
        raise AssertionError("이 경로는 모델을 부르지 않는다")


def _groups_payload(*named: tuple[str, int]) -> dict:
    return {"children": [{"name": name, "i": number} for name, number in named]}


def _seed_names() -> tuple[str, ...]:
    return timeline_group_names(build_sugar_timeline())


# -- 순수 함수: 네 리그 상태 --------------------------------------------------------


def test_a_fully_resolving_rig_reports_every_name_addressed() -> None:
    names = _seed_names()
    payload = _groups_payload(*[(name, 10 + i) for i, name in enumerate(names)])
    report = plan_rig_preflight(build_sugar_timeline(), console_payload=payload)

    assert report.console_reachable is True
    assert report.unresolved == ()
    assert len(report.resolved) == len(names)
    assert report.skipped_cues == ()
    assert report.appliable_cues == report.cues
    assert len(report.cues) > 0


def test_a_partially_resolving_rig_names_what_resolved_and_what_did_not() -> None:
    """일부만 맞는 리그 — 감독이 **무엇을 고칠지** 이름으로 읽을 수 있어야 한다."""
    names = _seed_names()
    assert len(names) >= 2
    kept, dropped = names[0], names[1]
    payload = _groups_payload((kept, 11), ("Unrelated", 99))

    report = plan_rig_preflight(build_sugar_timeline(), console_payload=payload)

    assert report.console_reachable is True
    assert [entry["group_name"] for entry in report.resolved] == [kept]
    assert dropped in report.unresolved
    # 부분 성공이다: 나가는 큐도 있고 건너뛰는 큐도 있다.
    assert report.appliable_cues != ()
    assert report.skipped_cues != ()
    for cue in report.skipped_cues:
        assert cue.reason == ROLE_UNADDRESSED

    text = render_rig_preflight(report)
    assert f"{kept}=Group 11" in text
    assert dropped in text
    assert "주소를 못 잡은 대상" in text
    assert "콘솔에는 아무것도 쓰지 않았습니다" in text


def test_a_fully_mismatched_rig_says_zero_matched_and_still_says_it_reached_the_console() -> None:
    """t302 의 실측 상태 — 닿았는데 이름이 하나도 안 맞는다."""
    payload = _groups_payload(("완전히", 1), ("다른", 2), ("이름들", 3))
    report = plan_rig_preflight(build_sugar_timeline(), console_payload=payload)

    assert report.console_reachable is True
    assert report.resolved == ()
    assert set(report.unresolved) == set(_seed_names())
    assert report.appliable_cues == ()
    assert len(report.skipped_cues) == len(report.cues)

    text = render_rig_preflight(report)
    # 「읽었다」가 본문에 있다 — 이것이 불통과 갈리는 자리다.
    assert "콘솔 그룹 이름 3개를 읽었습니다" in text
    assert "닿지 못했습니다" not in text


def test_an_unreachable_console_is_never_reported_as_nothing_matched() -> None:
    """이 카드의 요점 — 불통과 불일치는 **다른 문장**이어야 한다."""
    report = plan_rig_preflight(
        build_sugar_timeline(),
        console_payload=None,
        console_error="no such path: DataPool/Groups",
    )

    assert report.console_reachable is False
    # 재지 못한 것을 0 이라고 주장하지 않는다.
    assert report.console_names == ()
    assert report.cues == ()
    assert report.unresolved == ()

    text = render_rig_preflight(report)
    assert "콘솔에 닿지 못했습니다" in text
    assert "일치 수는 재지 않았습니다" in text
    assert "no such path: DataPool/Groups" in text
    # 불일치 보고의 문구가 섞이면 안 된다.
    assert "주소를 못 잡은 대상" not in text
    assert "반영 가능" not in text


def test_the_report_says_what_it_did_not_measure() -> None:
    payload = _groups_payload(*[(name, 10 + i) for i, name in enumerate(_seed_names())])
    text = render_rig_preflight(plan_rig_preflight(build_sugar_timeline(), console_payload=payload))
    for note in UNMEASURED_NOTES:
        assert note in text


def test_a_sequence_number_of_zero_is_not_reported_as_slot_zero() -> None:
    """시드 타임라인은 ``sequence_number`` 가 0 이다 — 「번호 없음」이지 0번 슬롯이 아니다.

    브라우저 1회차 실측(2026-09-06)에서 보고가 「(Sequence 0)」을 달고 나왔다.
    """
    seed = build_sugar_timeline()
    assert seed["sequence_number"] == 0
    report = plan_rig_preflight(seed, console_payload=_groups_payload(("KEY", 11)))
    assert report.sequence_number is None
    assert "Sequence 0" not in render_rig_preflight(report)


def test_no_timeline_is_not_an_unreachable_console() -> None:
    report = plan_rig_preflight(None, console_payload=_groups_payload(("KEY", 11)))
    assert report.console_reachable is True
    assert report.cues == ()


# -- 판별기: 새 문이 기존 문의 판정을 바꾸지 않는다 ----------------------------------


PREFLIGHT_REQUESTS = (
    "리그 점검해줘",
    "쇼 전에 그룹 이름 점검해줘",
    "그룹 이름 맞는지 확인해줘",
    "프리플라이트",
    "반영 전 점검해줘",
    "주소 점검해줘",
)

NOT_PREFLIGHT_REQUESTS = (
    "콘솔에 보내줘",
    "시퀀스 3에 반영해줘",
    "초안 적용해줘",
    "데스크로 전송해줘",
    "큐 3 조도 올려줘",
    "더 밝게",
    # 「반영하고 확인」은 보내는 요청이다 — 점검이 가로채면 안 된다.
    "초안을 콘솔에 반영해줘",
)


@pytest.mark.parametrize("text", PREFLIGHT_REQUESTS)
def test_a_preflight_shaped_request_reaches_the_preflight_predicate(text) -> None:
    assert _is_rig_preflight_request(text) is True


@pytest.mark.parametrize("text", NOT_PREFLIGHT_REQUESTS)
def test_a_send_or_edit_shaped_request_does_not_reach_the_preflight_predicate(text) -> None:
    assert _is_rig_preflight_request(text) is False


def test_the_preflight_predicate_never_swallows_the_existing_corpora() -> None:
    """t290·t295·t300·t301 이 고정한 코퍼스 전량에 대고 잰다."""
    from server.tests.test_cue_sheet_edit import (
        ANCHORLESS_CUE_COMMANDS,
        FADE_COMMANDS_WITHOUT_AN_EDIT_VERB,
        STILL_REFUSED_WITH_A_SELECTION,
    )
    from server.tests.test_draft_apply_routing import APPLY_REQUESTS, NOT_APPLY_REQUESTS

    corpora = {
        "t295 apply": APPLY_REQUESTS,
        "t295 not-apply": NOT_APPLY_REQUESTS,
        "t290 short-command": ANCHORLESS_CUE_COMMANDS,
        "t290 song-brief": STILL_REFUSED_WITH_A_SELECTION,
        "t300 fade": FADE_COMMANDS_WITHOUT_AN_EDIT_VERB,
    }
    leaked = {
        name: [t for t in texts if _is_rig_preflight_request(t)] for name, texts in corpora.items()
    }
    assert leaked == {name: [] for name in corpora}


# -- 끝단: 세션에서 돌리고 **콘솔 쓰기 0건**을 센다 ----------------------------------


def _session(tmp_path, console):
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
    return session, sent


@pytest.mark.parametrize(
    "state_tree",
    [
        pytest.param(
            {"DataPool/Groups": _groups_payload(("KEY", 11), ("BACK", 12), ("MOVER-U", 15))},
            id="partially-resolving",
        ),
        pytest.param(
            {"DataPool/Groups": _groups_payload(("무관", 1))},
            id="fully-mismatched",
        ),
        pytest.param({}, id="unreachable"),
    ],
)
def test_the_preflight_sends_zero_console_writes_on_every_path(tmp_path, state_tree) -> None:
    """읽기 전용의 증거 — 어떤 리그 상태에서도 실행된 명령이 0건이다."""
    console = FakeConsole(state_tree=state_tree)
    session, _sent = _session(tmp_path, console)

    event = session.run_instruction("리그 점검해줘")

    assert console.executed == []
    assert event["status"] == "ok"
    assert event.get("commands") in (None, [], ())


def test_the_session_report_distinguishes_a_dead_desk_from_a_renamed_rig(tmp_path) -> None:
    dead = FakeConsole(state_tree={})
    session_dead, _ = _session(tmp_path / "a", dead)
    dead_text = session_dead.run_instruction("리그 점검해줘")["text"]

    renamed = FakeConsole(state_tree={"DataPool/Groups": _groups_payload(("무관", 1))})
    session_renamed, _ = _session(tmp_path / "b", renamed)
    renamed_text = session_renamed.run_instruction("리그 점검해줘")["text"]

    assert "콘솔에 닿지 못했습니다" in dead_text
    assert "콘솔에 닿지 못했습니다" not in renamed_text
    assert "콘솔 그룹 이름 1개를 읽었습니다" in renamed_text
    assert dead_text != renamed_text


def test_the_unreachable_reason_names_the_path_without_the_json_wrapper(tmp_path) -> None:
    """실측(브라우저 2회차): 사유가 `{"error": "…"}` 로 싸여 나왔다."""
    console = FakeConsole(state_tree={})
    session, _ = _session(tmp_path, console)

    text = session.run_instruction("리그 점검해줘")["text"]

    assert "DataPool/Groups" in text  # 어느 읽기가 실패했는지는 남는다
    assert '{"error"' not in text  # 감싼 JSON 은 안 보인다
    assert console.executed == []


def test_the_preflight_verdict_agrees_with_what_apply_would_actually_skip(tmp_path) -> None:
    """점검이 「나간다」고 한 큐는 반영도 나간다 — 두 판정이 같은 술어를 쓴다."""
    from server.design.cue_sheet_apply import layer_mapping_from_console_groups

    payload = _groups_payload(("KEY", 11))
    report = plan_rig_preflight(build_sugar_timeline(), console_payload=payload)
    mapping = layer_mapping_from_console_groups(payload, _seed_names())

    assert [entry["group_name"] for entry in report.resolved] == [
        entry["group_name"] for entry in mapping
    ]


# -- t304: 판정을 재구현하지 않고 반영에게 물어본다 -----------------------------------


def _unbound_palette_timeline() -> dict:
    """주소는 잡히는데 **룩이 안 붙는** 타임라인.

    큐 20 의 ``palette_primary`` 를 팔레트 범례에 없는 이름으로 바꾼다. t303 의
    판정은 「이 큐의 그룹 이름이 전부 풀리는가」뿐이라 이 큐를 **반영 가능**으로
    셌지만, 반영은 이 큐에 대해 `UNMAPPED_LOOK` 건너뜀 기록을 남긴다 — 점검이
    낙관 방향으로 틀리던 자리다.
    """
    timeline = build_sugar_timeline()
    sections = [dict(section) for section in timeline["sections"]]
    for section in sections:
        if section["cue_number"] == 20:
            section["palette_primary"] = "P99 범례에 없는 색"
    timeline["sections"] = sections
    return timeline


def _payload_for(timeline: dict) -> dict:
    names = timeline_group_names(timeline)
    return _groups_payload(*[(name, 10 + i) for i, name in enumerate(names)])


def test_a_cue_with_an_address_but_no_binding_look_carries_applys_own_reason() -> None:
    """이 카드의 요점 — 두 판정이 어긋나던 큐가 이제 반영의 사유와 함께 나온다."""
    from server.design.cue_sheet_apply import (
        UNMAPPED_LOOK,
        layer_mapping_from_console_groups,
        palette_index,
        plan_cue_console_apply,
    )

    timeline = _unbound_palette_timeline()
    payload = _payload_for(timeline)
    report = plan_rig_preflight(timeline, console_payload=payload)

    cue20 = next(cue for cue in report.cues if cue.cue_number == 20)
    # 주소는 잡혔다 — t303 이 「반영 가능」이라고만 적던 상태다.
    assert cue20.would_apply is True
    # 이제는 못 나가는 칸이 사유와 함께 붙는다.
    assert cue20.skips != ()
    assert cue20.reason == UNMAPPED_LOOK
    assert cue20 in report.partial_cues

    # 사유는 **반영이 쓴 기록 그대로**다 — 번역본이 아니다.
    section = next(s for s in timeline["sections"] if s["cue_number"] == 20)
    mapping = layer_mapping_from_console_groups(payload, timeline_group_names(timeline))
    decision = plan_cue_console_apply(section, None, mapping, palette_index(timeline))
    assert cue20.skips == decision.skips

    text = render_rig_preflight(report)
    assert "P99 범례에 없는 색" in text
    assert "색을 지어내지 않습니다" in text
    assert "일부만 나가는 큐 1건" in text


def test_every_cue_verdict_matches_what_apply_would_do_with_the_same_rig() -> None:
    """전수 대조 — 점검의 큐별 판정과 반영의 계획이 큐 단위로 같다.

    반영은 명령 문자열을 지어야 해서 시퀀스 번호를 요구하므로 여기서만 번호를
    선언한 사본으로 돌린다. 번호가 **판정에 쓰이지 않는다**는 것이 이 대조가
    보이는 것이다.
    """
    from server.design.cue_sheet_apply import (
        layer_mapping_from_console_groups,
        plan_console_apply,
    )

    timeline = _unbound_palette_timeline()
    payload = _payload_for(timeline)
    report = plan_rig_preflight(timeline, console_payload=payload)

    target = dict(timeline)
    target["sequence_number"] = 210
    target["layer_mapping"] = layer_mapping_from_console_groups(
        payload, timeline_group_names(timeline)
    )
    plan = plan_console_apply({}, target)

    assert [cue.cue_number for cue in report.appliable_cues] == list(plan.applied)
    assert [skip for cue in report.cues for skip in cue.skips] == list(plan.skipped)
    assert {cue.cue_number: cue.summary for cue in report.appliable_cues} == dict(plan.summaries)


def test_a_fully_mismatched_rig_agrees_with_apply_that_nothing_goes_out() -> None:
    from server.design.cue_sheet_apply import plan_console_apply

    timeline = build_sugar_timeline()
    report = plan_rig_preflight(timeline, console_payload=_groups_payload(("무관", 1)))

    target = dict(timeline)
    target["sequence_number"] = 210
    target["layer_mapping"] = []
    plan = plan_console_apply({}, target)

    assert report.appliable_cues == ()
    assert plan.applied == ()
    assert plan.is_empty is True


# -- t304: 슬롯 점유 ------------------------------------------------------------------


def test_slot_occupancy_is_not_claimed_when_no_number_is_declared() -> None:
    """시드 타임라인은 번호가 없다 — 「비었다」고 적으면 안 된다."""
    report = plan_rig_preflight(
        build_sugar_timeline(), console_payload=_groups_payload(("KEY", 11))
    )
    assert report.sequence_slot == ""
    assert report.timecode_number is None
    text = render_rig_preflight(report)
    assert "시퀀스 번호가 없어 재지 않았습니다" in text
    assert "타임코드 번호가 없어 재지 않았습니다" in text


@pytest.mark.parametrize(
    ("state", "phrase"),
    [
        ("empty", "비어 있습니다"),
        ("occupied", "이미 내용이 있습니다"),
        ("unreadable", "읽지 못했습니다"),
    ],
)
def test_a_declared_slot_reports_all_three_verdicts(state, phrase) -> None:
    timeline = dict(build_sugar_timeline())
    timeline["sequence_number"] = 210
    timeline["timecode_number"] = 7
    report = plan_rig_preflight(
        timeline,
        console_payload=_groups_payload(("KEY", 11)),
        sequence_slot=state,
        timecode_slot=state,
    )
    text = render_rig_preflight(report)
    assert f"시퀀스 210번 슬롯: {phrase}" in text
    assert f"타임코드 7번 슬롯: {phrase}" in text


def test_the_session_probes_the_declared_slots_and_still_writes_nothing(tmp_path) -> None:
    """실제 세션에서 슬롯을 읽는다 — 그리고 **콘솔 쓰기는 여전히 0건**이다."""
    console = FakeConsole(
        state_tree={
            "DataPool/Groups": _groups_payload(("KEY", 11), ("BACK", 12)),
            "DataPool/Sequences/210": {"ok": True, "node": {"name": "SUGAR"}},
        }
    )
    session, _ = _session(tmp_path, console)
    timeline = dict(build_sugar_timeline())
    timeline["sequence_number"] = 210
    timeline["timecode_number"] = 7
    session._timeline_store.latest = timeline

    text = session.run_instruction("리그 점검해줘")["text"]

    assert console.executed == []
    assert "시퀀스 210번 슬롯: 이미 내용이 있습니다" in text
    assert "타임코드 7번 슬롯" in text


def test_no_slot_is_probed_when_the_console_is_unreachable(tmp_path) -> None:
    """불통이면 슬롯도 안 읽는다 — 못 읽은 것을 「비었다」로 적지 않는다."""
    console = FakeConsole(state_tree={})
    session, _ = _session(tmp_path, console)
    timeline = dict(build_sugar_timeline())
    timeline["sequence_number"] = 210
    session._timeline_store.latest = timeline

    text = session.run_instruction("리그 점검해줘")["text"]

    assert console.executed == []
    assert "콘솔에 닿지 못했습니다" in text
    assert "슬롯" not in text
