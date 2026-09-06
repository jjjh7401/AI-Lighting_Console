"""SPEC-COPILOT-WRITEGATE-001 — `session.py` 의 쇼파일 쓰기 자리를 몰아 잰다 (카드 t320).

카드 t319 가 봉합을 열 자리 남기고 멈춘 이유가 이 파일의 존재 이유다:

    봉합 자체는 `_dispatch_declared` 한 줄이지만, 이 카드가 요구하는 증거
    (거절 → 0건 / 수락 → 카드 한 장 + approved 기록)는 자리마다 다른 대화
    흐름으로 몰아야 나온다. 구동기 없이 봉합만 달면 「달았다」는 주장은 되지만
    「승인 없이는 안 나간다」는 관측이 안 된다 — 그것은 봉합이 아니라
    봉합처럼 보이는 코드다.

그래서 자리마다 **실제 메서드를 부른다**. 게이트·감사 로그·콘솔·레지스트리는
전부 진짜이고, 대역으로 바꾸는 것은 **콘솔 판독**(좌표·점유 프로브)과
**질문 채널** 둘뿐이다 — 쓰기 경로는 한 줄도 안 갈아끼운다. 판독을 대역으로
두는 이유는 그것이 이 카드가 재려는 것이 아니기 때문이다: 재려는 것은
「이 번들이 승인 없이 콘솔에 닿는가」 하나다.

자리마다 두 관측을 쌍으로 낸다.

거절
    승인기가 거절하면 **쇼파일을 고치는 줄이 콘솔에 0건** 닿는다.
    「아무것도 안 나갔다」가 아니라 「쇼파일 쓰기가 안 나갔다」로 재는 이유:
    번들에는 `ClearAll` 처럼 쇼파일을 안 건드리는 줄이 섞이는데, 게이트가
    전건을 all-or-nothing 으로 막으므로 사실은 그것들도 0건이다. 술어를
    좁게 잡아 두면 나중에 프로그래머 줄만 남기는 설계 변경이 이 검사를
    거짓으로 깨뜨리지 않는다.

수락
    카드가 **한 장**이고 그 한 장이 **번들의 모든 줄**을 싣는다(REQ-BULKGATE-002).
    그리고 감사 로그의 `approved` 기록이 그 자리의 `kind` 를 단다 — 로그에서
    어느 통로의 판단이었는지 되짚을 수 있어야 하기 때문이다.

한계. 서버 층만 잰다. DOM 도, 실기 콘솔도 안 잰다. 그리고 대역으로 둔
판독 경로(좌표 프로브·점유 프로브)의 정확성은 이 파일이 답하지 않는다.
"""

from __future__ import annotations

import json

import pytest

from server.safety.audit import AuditLog
from server.spatial.pointing import BASIC_POSITION_SEQUENCE
from server.web.approval_bridge import ApprovalChannel

from .test_runner_self_correction import ScriptedProvider
from .test_web_session import _session

# ---------------------------------------------------------------------------
# 하네스
# ---------------------------------------------------------------------------

#: 쇼파일 오브젝트를 만들거나 덮는 줄. `write_reason.py` 가 문면을 만들 때 세는
#: 것과 같은 계열이며, 여기서는 **콘솔에 무엇이 닿았는가**를 세는 데 쓴다.
_SHOWFILE_PREFIXES = ("Store ", "Assign Sequence ", "Copy Sequence ", "Set Fixture ")


def _showfile(commands) -> list[str]:
    return [c for c in commands if c.startswith(_SHOWFILE_PREFIXES)]


class _Channel(ApprovalChannel):
    """카드를 자기가 답하는 승인 채널 — 거절/수락 두 갈래를 만든다."""

    def __init__(self, verdict: bool) -> None:
        super().__init__(timeout_seconds=1.0)
        self.verdict = verdict
        self.requests: list = []

    def request_approval(self, request) -> bool:
        self.requests.append(request)
        return self.verdict


def _audit_events(audit: AuditLog) -> list[dict]:
    root = audit.directory if hasattr(audit, "directory") else audit._directory
    entries: list[dict] = []
    for path in sorted(root.rglob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entries.append(json.loads(line))
    return entries


def _build(tmp_path, verdict: bool):
    channel = _Channel(verdict)
    session, console, audit, sent, _channel = _session(
        tmp_path, ScriptedProvider([]), channel=channel
    )
    return session, console, audit, channel


#: 좌표가 확인된 장비 둘 — 판독 대역이 돌려주는 값.
_FIXTURES = [(20, (0.0, 0.0, 5.0)), (21, (2.0, 0.0, 5.0))]


def _stub_reads(session, *, executors: set[int] | None = None) -> None:
    """콘솔 **판독**만 대역으로 바꾼다 — 쓰기 경로는 그대로 둔다."""
    session._read_pointing_coordinates = lambda _tag: list(_FIXTURES)
    session._read_pointing_frames = lambda _tag: (list(_FIXTURES), {}, [], [])
    session._song_sequence_occupied = lambda _no: False
    session._console_slot_occupied = lambda _path, **_kw: False
    if executors is not None:
        session._page_one_executors = lambda **_kw: set(executors)


def _answers(session, answers: list[str]) -> list[str]:
    """질문 카드를 미리 준비한 답으로 답한다. 물어본 문면을 돌려준다."""
    asked: list[str] = []

    def _ask(prompt, **_kwargs):
        asked.append(prompt)
        return answers.pop(0) if answers else None

    session._ask_one = _ask
    return asked


# ---------------------------------------------------------------------------
# 자리별 구동기 — 각 함수는 (session, 결과) 를 만드는 한 회차다
# ---------------------------------------------------------------------------


def _drive_look_bundle(session):
    from .test_looks_instantiate import _groups, _look, _plan, _pools

    plan = _plan(_look(attributes=(("Dimmer", 50),)), _groups((11, "Back")), _pools())
    session.run_look_bundle(plan)


def _drive_look_pan_tilt(session):
    _stub_reads(session)
    _answers(session, [])
    session._look_pan_tilt("장비들 부채살로 펼치고 포지션 프리셋 7번에 저장해줘")


def _drive_position_fx_sequence(session):
    _stub_reads(session)
    _answers(session, [])
    session._position_fx_sequence("포지션 이펙트 서클 시퀀스 201 만들어줘, FX 프리셋 41번부터")


def _drive_fx_executor_assignment(session):
    _stub_reads(session, executors=set())
    _answers(session, ["걸기"])
    session._offer_fx_executor_assignment(201)


def _drive_phaser_recall_sequence(session):
    _stub_reads(session, executors={101, 102, 103, 104, 105, 106, 107, 108, 109, 110})
    _answers(session, [])
    session._phaser_slot_by_label = lambda _label: (1, 3)
    session._phaser_recall_fids = lambda _label, **_kw: ([20, 21], "")
    session._phaser_recall_sequence("Breathe Warm 시퀀스 201로 쳐줘")


def _drive_store_position_preset_looks(session):
    session._store_position_preset_looks(
        [("정면", [(20, 0.0, 10.0), (21, 5.0, 10.0)], [])],
        31,
        before=None,
    )


def _drive_position_cue_store(session):
    _stub_reads(session)
    _answers(session, [])
    session._position_cue_store("프리셋 2.28을 시퀀스 101 큐 1로 저장, 페이드 5초")


def _drive_position_cue_sheet(session):
    _stub_reads(session)
    _answers(session, [])
    session._song_pick_sequence = lambda requested, **_kw: requested or 110
    session._position_cue_sheet(
        "포지션 큐 시트, 시퀀스 110, 프리셋 21번부터: 인트로 0:00 잔잔하게, 후렴 0:40 클럽 드롭"
    )


def _drive_timeline_cue_merge(session):
    _stub_reads(session)
    _answers(session, [])
    timeline = {"sequence_number": 210, "preset_start": 21}
    sections = [{"name": "인트로", "position": "정면"}]
    session._merge_timeline_cue_position(timeline, sections, 0, 1, _MERGE_TARGET)


def _drive_setlist(session):
    _stub_reads(session)
    _answers(session, ["승인"])
    session._timeline_library = _Library()
    session._setlist_mode("셋리스트 만들어줘")


class _Library:
    def items(self):
        return [
            {
                "name": "첫곡 v1",
                "timeline": {"sequence_number": 300, "console_stored": True},
            }
        ]


_MERGE_TARGET = BASIC_POSITION_SEQUENCE[0]


#: (자리 이름, 구동기, 감사 로그에 실려야 할 `kind`)
SITES = (
    ("run_look_bundle", _drive_look_bundle, "look_bundle"),
    ("_look_pan_tilt", _drive_look_pan_tilt, "look_pan_tilt"),
    ("_position_fx_sequence", _drive_position_fx_sequence, "position_fx_sequence"),
    ("_offer_fx_executor_assignment", _drive_fx_executor_assignment, "fx_executor_assign"),
    ("_phaser_recall_sequence", _drive_phaser_recall_sequence, "phaser_recall_sequence"),
    ("_store_position_preset_looks", _drive_store_position_preset_looks, "position_preset_look"),
    ("_position_cue_store", _drive_position_cue_store, "position_cue_store"),
    ("_position_cue_sheet", _drive_position_cue_sheet, "position_cue_sheet"),
    ("_merge_timeline_cue_position", _drive_timeline_cue_merge, "timeline_cue_merge"),
    ("_setlist_mode", _drive_setlist, "setlist_assign"),
)


@pytest.mark.parametrize(("name", "drive", "kind"), SITES, ids=[s[0] for s in SITES])
class TestEverySealedSiteIsDriven:
    def test_a_rejected_bundle_reaches_the_console_zero_times(self, tmp_path, name, drive, kind):
        session, console, _audit, channel = _build(tmp_path, verdict=False)
        drive(session)
        assert channel.requests, f"{name}: 카드가 아예 안 떴다 — 봉합이 안 걸린 것이다"
        assert _showfile(console.executed) == [], (
            f"{name}: 감독이 거절했는데 쇼파일 쓰기가 콘솔에 닿았다: {console.executed}"
        )

    def test_an_approved_bundle_rides_one_card_carrying_every_command(
        self, tmp_path, name, drive, kind
    ):
        session, console, _audit, channel = _build(tmp_path, verdict=True)
        drive(session)
        assert channel.requests, f"{name}: 카드가 아예 안 떴다"
        for request in channel.requests:
            held = [item.command for item in request.items]
            assert _showfile(held), f"{name}: 카드에 쇼파일 쓰기 줄이 없다: {held}"
        assert _showfile(console.executed), f"{name}: 수락했는데 콘솔에 아무것도 안 갔다"

    def test_the_audit_names_this_site(self, tmp_path, name, drive, kind):
        session, _console, audit, _channel = _build(tmp_path, verdict=True)
        drive(session)
        approved = [e for e in _audit_events(audit) if e.get("event") == "approved"]
        assert approved, f"{name}: approved 기록이 없다"
        assert any(e.get("kind") == kind for e in approved), (
            f"{name}: approved 기록이 kind={kind!r} 를 안 단다: {[e.get('kind') for e in approved]}"
        )


class TestTheDriversAreNotVacuous:
    """구동기가 실제로 명령을 만들었는지 — 0건이면 위 검사가 공허하다."""

    @pytest.mark.parametrize(("name", "drive", "kind"), SITES, ids=[s[0] for s in SITES])
    def test_each_driver_produces_at_least_one_showfile_command(self, tmp_path, name, drive, kind):
        session, console, _audit, channel = _build(tmp_path, verdict=True)
        drive(session)
        carried = [item.command for request in channel.requests for item in request.items]
        assert _showfile(carried), f"{name}: 이 구동기는 쇼파일 쓰기를 한 줄도 안 만들었다"


class TestABundleWithNoShowfileWriteRaisesNoCard:
    """해롭지 않은 번들에 카드를 띄우면 감독이 카드를 안 읽게 된다.

    `_look_pan_tilt` 는 프리셋 저장을 지시받지 않으면 프로그래머 값만 찍는다 —
    `showfile_write_risk` 가 `None` 을 답하고, 선언 통로는 그 회차에 카드를
    만들지 않는다. (분류 층이 다른 이유로 카드를 띄울 수는 있으므로, 재는 것은
    「선언이 만든 카드가 없다」 — 즉 카드에 실린 사유에 선언 문면이 없다.)
    """

    def test_a_programmer_only_look_carries_no_declaration_reason(self, tmp_path):
        session, _console, _audit, channel = _build(tmp_path, verdict=True)
        _stub_reads(session)
        _answers(session, [])
        session._look_pan_tilt("장비들 부채살로 펼쳐줘")
        reasons = [
            reason
            for request in channel.requests
            for item in request.items
            for reason in item.risk_reasons
        ]
        assert not any(r.startswith("쇼파일 쓰기 —") for r in reasons), reasons
