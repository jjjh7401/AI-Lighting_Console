"""카드 t477 — 반영 전에 콘솔 풀을 읽어 포지션·페이저 **이름**을 풀 번호로 채운다.

t469 는 번호(``2.<n>``)가 있는 포지션만 콘솔로 보냈고, 이름만 있는 포지션과
페이저는 사유를 달고 건너뛰었다(`.moai/reports/t469/verdict.md` §0). 이 카드는
그 두 경우를 푼다 — 세션이 반영 직전에 콘솔 풀을 **읽기만** 해서 이름을 번호로
바꾸고, 못 찾으면 지어내지 않고 사유를 단다.

가짜 콘솔의 풀 회신은 t469 실기 캡처를 **그대로** 옮긴 것이다
(`server/tests/fixtures/console/t469_preset_pools.json`, 생성
`.moai/reports/t477/extract_pools.py`). 실기 포지션 이름은
``POS05 팬아웃 종점 (객석 상단) · 합성좌표`` 처럼 길다 — 감독이 ``POS05`` 라고
적어도 찾을 수 있어야 하고, 그래서 「이름 첫 낱말이 하나뿐일 때」 규칙이 있다.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from server.design.cue_sheet_apply import (
    UNSOURCED_FIELD_REASONS,
    plan_console_apply,
    plan_cue_console_apply,
)
from server.design.preset_names import (
    NAME_ABSENT,
    NAME_AMBIGUOUS,
    POOL_UNREAD,
    match_preset_name,
    match_preset_name_across_pools,
)
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.approval_bridge import ApprovalChannel
from server.web.session import ChatSession, SongTimelineStore
from server.web.timeline_library import SongTimelineLibrary

from .test_safety_gate import FakeConsole
from .test_web_cue_sheet_apply import RefusingProvider, _run_with_auto_approval, _timeline

_FIXTURE = Path(__file__).parent / "fixtures" / "console" / "t469_preset_pools.json"
_CAPTURE_ROOT = "ShowData/DataPools/Default/PresetPools"
_SESSION_ROOT = "DataPool/PresetPools"  # 세션 기본 경로(`_rig_paths` 미설정)


def _captured_pools() -> dict[str, dict]:
    replies = json.loads(_FIXTURE.read_text(encoding="utf-8"))["replies"]
    return {path.replace(_CAPTURE_ROOT, _SESSION_ROOT): body for path, body in replies.items()}


def _children(path: str) -> dict[int, str | None]:
    body = _captured_pools()[path]
    return {child["i"]: child.get("name") for child in body["children"]}


# --- 1. 공용 판독 함수 (순수) ------------------------------------------------------


class TestMatchPresetName:
    def test_the_full_console_name_matches_exactly(self):
        pool = _children(f"{_SESSION_ROOT}/21")
        match = match_preset_name(pool, "DIM-BREATHE")
        assert (match.slot, match.rule) == (4, "exact")

    def test_a_hash_suffix_is_ignored(self):
        match = match_preset_name({7: "Home#2"}, "Home")
        assert match.slot == 7

    def test_leading_token_finds_the_real_long_position_name(self):
        pool = _children(f"{_SESSION_ROOT}/2")
        match = match_preset_name(pool, "POS05", leading_token=True)
        assert (match.slot, match.rule) == (5, "leading_token")
        assert match.name == "POS05 팬아웃 종점 (객석 상단) · 합성좌표"

    def test_leading_token_is_off_unless_asked(self):
        pool = _children(f"{_SESSION_ROOT}/2")
        match = match_preset_name(pool, "POS05")
        assert (match.slot, match.kind) == (None, NAME_ABSENT)

    def test_leading_token_ignores_case(self):
        match = match_preset_name({3: "POS03 밴드 라인 백"}, "pos03", leading_token=True)
        assert match.slot == 3

    def test_an_exact_match_beats_a_leading_token_match(self):
        match = match_preset_name({1: "Sweep L extra", 9: "Sweep"}, "Sweep", leading_token=True)
        assert (match.slot, match.rule) == (9, "exact")

    def test_two_leading_token_candidates_are_ambiguous(self):
        match = match_preset_name({1: "POS05 a", 2: "POS05 b"}, "POS05", leading_token=True)
        assert match.slot is None
        assert match.kind == NAME_AMBIGUOUS
        assert match.candidates == (1, 2)

    def test_a_span_picks_the_one_inside(self):
        match = match_preset_name({21: "Home", 99: "Home"}, "Home", span=(21, 30))
        assert match.slot == 21

    def test_a_description_word_does_not_match(self):
        # 이름 중간 낱말로는 찾지 않는다 — 부분 일치는 짐작이다.
        pool = _children(f"{_SESSION_ROOT}/2")
        match = match_preset_name(pool, "팬아웃", leading_token=True)
        assert match.slot is None


class TestAcrossPools:
    def test_a_unique_match_names_its_pool(self):
        pools = {21: _children(f"{_SESSION_ROOT}/21"), 1: _children(f"{_SESSION_ROOT}/1")}
        found = match_preset_name_across_pools(pools, "DIM-BREATHE")
        assert (found.pool_no, found.slot) == (21, 4)

    def test_the_same_name_in_two_pools_is_ambiguous(self):
        found = match_preset_name_across_pools({1: {3: "Glow"}, 21: {5: "Glow"}}, "Glow")
        assert found.slot is None
        assert found.kind == NAME_AMBIGUOUS

    def test_an_unread_pool_blocks_a_match_elsewhere(self):
        # 읽지 못한 풀에 같은 이름이 있을 수 있다 — 유일하다고 말할 수 없다.
        found = match_preset_name_across_pools({1: None, 21: {4: "DIM-BREATHE"}}, "DIM-BREATHE")
        assert found.slot is None
        assert found.kind == POOL_UNREAD

    def test_absent_everywhere_is_absent(self):
        pools = {21: _children(f"{_SESSION_ROOT}/21"), 4: _children(f"{_SESSION_ROOT}/4")}
        found = match_preset_name_across_pools(pools, "Breathe Soft")
        assert (found.slot, found.kind) == (None, NAME_ABSENT)


# --- 2. 계획기: 페이저 번호가 있으면 싣는다 -----------------------------------------


def _plan_timeline() -> dict:
    return {
        "song_title": "Sugar",
        "sequence_number": 210,
        "layer_mapping": [{"role": "key", "group_no": 11, "group_name": "KEY"}],
        "sections": [
            {
                "index": 1,
                "label": "VERSE1",
                "cue_number": 20,
                "start_ms": 0,
                "d_level": 4,
                "intensity": [{"group": "KEY", "level": 70}],
                "fixture_groups": ["KEY"],
            }
        ],
    }


def _plan_with(new_fields: dict):
    baseline = _plan_timeline()
    current = copy.deepcopy(baseline)
    current["sections"][0].update(new_fields)
    return plan_console_apply(baseline, current)


def test_a_phaser_with_a_pool_number_is_recalled_like_t469_measured():
    plan = _plan_with({"phaser": "DIM-BREATHE", "phaser_preset_no": "21.4"})
    value = next(line for line in plan.commands if line.startswith("Group 11"))
    assert value.endswith(" ; Group 11 ; At Preset 21.4")
    assert "페이저 21.4" in plan.summaries[20]
    assert not plan.skipped


def test_position_and_phaser_ride_the_same_value_line():
    plan = _plan_with(
        {
            "position": "POS05",
            "position_preset_no": "2.5",
            "phaser": "DIM-BREATHE",
            "phaser_preset_no": "21.4",
        }
    )
    value = next(line for line in plan.commands if line.startswith("Group 11"))
    assert value.endswith(" ; Group 11 ; At Preset 2.5 ; Group 11 ; At Preset 21.4")


def test_a_phaser_name_without_a_number_keeps_its_reason():
    plan = _plan_with({"phaser": "Breathe Soft"})
    assert plan.commands == ()
    (skip,) = plan.skipped
    assert UNSOURCED_FIELD_REASONS["phaser"] in skip.detail


@pytest.mark.parametrize("number", ["21", "21.", "x.4", "21.4.1"])
def test_a_malformed_phaser_number_is_not_sent(number):
    plan = _plan_with({"phaser": "DIM-BREATHE", "phaser_preset_no": number})
    assert not any("At Preset" in line for line in plan.commands)
    assert any("페이저" in skip.detail for skip in plan.skipped)


def test_full_apply_leaves_composer_phaser_names_alone():
    section = {**_plan_timeline()["sections"][0], "phaser": "Breathe Soft"}
    decision = plan_cue_console_apply(section, None, _plan_timeline()["layer_mapping"], {})
    assert "At Preset" not in decision.value_line
    assert not any("페이저" in skip.detail for skip in decision.skips)


# --- 3. 세션: 반영 직전 풀 판독 → 번호 채우기 (가짜 콘솔 = t469 캡처) -----------------


class _RecordingConsole(FakeConsole):
    def __init__(self, state_tree: dict | None = None) -> None:
        super().__init__(state_tree=state_tree)
        self.queried: list[str] = []

    def query_state(self, path: str) -> dict:
        self.queried.append(path)
        return super().query_state(path)


def _harness(tmp_path, state_tree: dict):
    console = _RecordingConsole(state_tree=state_tree)
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=2.0)
    gate = SafetyGate(console=console, audit=audit, approval_port=channel)
    store = SongTimelineStore()
    store.latest = _timeline()
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


def _edit_cue_20(session, store, **fields) -> None:
    """초안 편집 결과를 직접 놓는다 — 문장 파싱은 t466 시험이 잰다."""
    session._draft_baseline = copy.deepcopy(store.latest)
    edited = copy.deepcopy(store.latest)
    edited["sections"][1].update(fields)
    store.latest = edited


def _apply(tmp_path, state_tree, **fields):
    session, console, store, sent, channel = _harness(tmp_path, state_tree)
    _edit_cue_20(session, store, **fields)
    event = _run_with_auto_approval(session, sent, channel, "초안을 콘솔에 반영해줘")
    return event, console


def test_a_position_name_is_filled_from_the_captured_pool(tmp_path):
    event, console = _apply(tmp_path, _captured_pools(), position="POS05")
    assert "Group 11 ; Attribute 'Dimmer' At 60 ; Group 11 ; At Preset 2.5" in console.executed
    assert "Store Sequence 210 Cue 20 /Merge" in console.executed
    assert "2.5" in event["text"]
    assert "POS05 팬아웃 종점" in event["text"]  # 어느 프리셋으로 찾았는지 이름을 보인다


def test_a_phaser_name_is_filled_from_the_captured_pool(tmp_path):
    event, console = _apply(tmp_path, _captured_pools(), phaser="DIM-BREATHE")
    assert any(line.endswith("; At Preset 21.4") for line in console.executed)
    assert "21.4" in event["text"]


def test_a_catalog_name_absent_from_the_pool_is_not_invented(tmp_path):
    # t469 실측: 카탈로그 이름(Breathe Soft)은 이 콘솔 풀에 없다.
    event, console = _apply(tmp_path, _captured_pools(), phaser="Breathe Soft")
    assert not any("At Preset" in line for line in console.executed)
    assert not any(line.startswith("Store") for line in console.executed)
    assert "Breathe Soft" in event["text"]
    assert "찾지 못했습니다" in event["text"]


def test_an_unreadable_position_pool_is_a_distinct_reason(tmp_path):
    tree = {k: v for k, v in _captured_pools().items() if not k.endswith("/2")}
    event, console = _apply(tmp_path, tree, position="POS05")
    assert not any("At Preset" in line for line in console.executed)
    assert "읽지 못" in event["text"]


def test_two_presets_sharing_the_leading_word_are_refused(tmp_path):
    tree = _captured_pools()
    pool = copy.deepcopy(tree[f"{_SESSION_ROOT}/2"])
    pool["children"].append({"class": "Preset", "i": 7, "name": "POS05 사본"})
    pool["node"]["childCount"] = 7
    tree[f"{_SESSION_ROOT}/2"] = pool
    event, console = _apply(tmp_path, tree, position="POS05")
    assert not any("At Preset" in line for line in console.executed)
    assert "특정할 수 없" in event["text"]


def test_no_pool_read_when_nothing_needs_a_name(tmp_path):
    session, console, store, sent, channel = _harness(tmp_path, _captured_pools())
    _edit_cue_20(session, store, intensity=[{"group": "KEY", "level": 80}])
    _run_with_auto_approval(session, sent, channel, "초안을 콘솔에 반영해줘")
    assert not any("PresetPools" in path for path in console.queried)
    assert "Store Sequence 210 Cue 20 /Merge" in console.executed


def test_a_position_that_already_has_a_number_is_not_looked_up(tmp_path):
    session, console, store, sent, channel = _harness(tmp_path, _captured_pools())
    _edit_cue_20(session, store, position="POS02", position_preset_no="2.2")
    _run_with_auto_approval(session, sent, channel, "초안을 콘솔에 반영해줘")
    assert not any("PresetPools" in path for path in console.queried)
    assert any(line.endswith("; At Preset 2.2") for line in console.executed)


def test_the_lookup_reads_but_never_writes_the_pool(tmp_path):
    # 판독은 읽기 전용이다 — 프리셋 저장·라벨 명령이 한 줄도 나가지 않는다.
    _event, console = _apply(tmp_path, _captured_pools(), position="POS05", phaser="DIM-PULSE")
    assert not any(
        line.startswith(("Store Preset", "Label Preset", "Delete Preset"))
        for line in console.executed
    )
