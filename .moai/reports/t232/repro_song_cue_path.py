"""t232 재현 — REAL 생산 빌더 3경로를 가짜 콘솔 풀 상태 두 가지에 올린다.

콘솔 접촉 0(FakeConsole). 스크립트는 이 카드의 수정 전/후 **동일하게** 실행
된다 — 세션 메서드(`ChatSession._reviewed_song_commands`/
`_position_fx_sequence`/`_merge_timeline_cue_position`)의 호출 형태는
안 바뀌었고, 그 안의 번호 산출 방식만 바뀌었기 때문이다.

사용: .venv/bin/python .moai/reports/t232/repro_song_cue_path.py

상태:
  C — 슬롯 1~10에 Home..Ring In(BASIC_POSITION_SEQUENCE 순서)이 저장돼
      있고, 감독이 고른 시작 번호도 1이다(그 10칸 = 그 10종). FX 쪽은
      21~30에 FX_POSITION_SEQUENCE 순서로 저장, 시작 번호 21.
  D — 슬롯 1~10에는 "POS01 시트".."POS10 시트"가 앉아 있고(시작 번호는
      여전히 1), 진짜 'Center'는 다른 자리(41)에 있다. FX 쪽 D는 21~30이
      다른 이름으로 차 있고 'Circle Base'는 61에 있다.
  D2 — 'Center'가 어디에도 없다(전부 다른 프리셋).
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# 트리 동일성 — 이 스크립트를 경로로 직접 실행하면(sys.path[0] = 이 파일의
# 디렉터리) venv 의 editable .pth 가 이겨서 "server" 가 이 워크트리가 아니라
# 메인 체크아웃에서 임포트될 수 있다(server/tools 쪽 가드가 잡는 것과 같은
# 함정, test_tree_identity.py). 이 리포트 스크립트 자신의 트리를 sys.path
# 맨 앞에 강제로 얹어 그 함정을 피한다.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from server.design.energy import EFFECT_AXIS_CAPABILITY
from server.design.profile import MusicProfile
from server.design.rig import build_rig_profile
from server.design.song_cue_composer import compose_song_cue_bundle
from server.design.song_plan import (
    AccentDecision,
    ApprovalState,
    DLevelDecision,
    FxDecision,
    PaletteDecision,
    PositionDecision,
    SectionDecision,
    TextureDecision,
    TimestampedSection,
    TimingPlan,
    UnifiedSongLightingPlan,
)
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.spatial.pointing import (
    BASIC_POSITION_SEQUENCE,
    FX_POSITION_SEQUENCE,
    SpatialPointingError,
)
from server.tests.conftest import AutoApproveChannel
from server.tests.test_runner_self_correction import ScriptedProvider
from server.tests.test_safety_gate import FakeConsole
from server.web.session import ChatSession

_EMPTY = {"ok": True, "node": {"childCount": 0}, "children": []}


def _build_session(tmp_path: Path, console: FakeConsole):
    """`server/tests/test_web_session.py::_session`의 최소 재현.

    그 헬퍼를 직접 임포트하지 않는 이유: 이 스크립트는 수정 전/후 트리 양쪽
    에서 **바이트 동일**하게 돌아야 하는데, `test_web_session.py` 자체가 이
    카드에서 수정된 파일이라 옛 트리에서는 새 API(`required_position_labels`)
    임포트에 걸려 죽는다. 세션 조립 논리만 이 스크립트 안에 그대로 둔다.
    """
    provider = ScriptedProvider([])
    audit = AuditLog(tmp_path / "audit")
    channel = AutoApproveChannel(timeout_seconds=1.0)
    gate = SafetyGate(console=console, audit=audit, approval_port=channel)
    sent: list[dict] = []
    session = ChatSession(
        gate=gate,
        provider=provider,
        system_prefix="PREFIX",
        audit=audit,
        send_event=sent.append,
        approval_channel=channel,
    )
    return session


class _PoolConsole(FakeConsole):
    """ "DataPool/PresetPools/2"만 상태(C/D)로 답하고, 나머지는 미점유로 답한다."""

    def __init__(self, position_pool: dict) -> None:
        super().__init__()
        self._position_pool = position_pool

    def query_state(self, path: str) -> dict:
        if path == "DataPool/PresetPools/2":
            return self._position_pool
        if path.startswith(("DataPool/Sequences/", "DataPool/Timecodes/", "DataPool/Groups")):
            return _EMPTY
        raise RuntimeError(f"repro: 예상 밖 경로 조회 {path!r}")


def _pool_payload(entries: dict[int, str]) -> dict:
    return {"ok": True, "children": [{"i": slot, "name": name} for slot, name in entries.items()]}


# ---------------------------------------------------------------------------
# (1) 감독 확정 곡 큐 — `_reviewed_song_commands`
# ---------------------------------------------------------------------------


def _rig():
    patch = [
        {"fid": fid, "type_name": "Fixture", "capabilities": [EFFECT_AXIS_CAPABILITY]}
        for fid in range(1, 3)
    ]
    return build_rig_profile(
        patch=patch, groups={}, coords=[], declared_layers={"key": [1], "back": [2]}
    )


def _section(index: int, position: str):
    return SectionDecision(
        section=TimestampedSection(index=index, label=f"S{index}", start_ms=(index - 1) * 20_000),
        d=DLevelDecision(level=3, source="section_mood"),
        palette=PaletteDecision(colors=("blue", "cyan"), source="director"),
        position=PositionDecision(preset=position, source="director"),
        texture=TextureDecision(label="long fade", source="genre"),
        fx=FxDecision(allowed=(), disabled=(), density=0),
        accent=AccentDecision(accents=()),
        cue_number=100 + index,
    )


def _song_composition(*positions: str):
    sections = tuple(_section(i, position) for i, position in enumerate(positions, start=1))
    plan = UnifiedSongLightingPlan(
        song_title="t232 repro",
        sequence_name="repro seq",
        sections=sections,
        timing=TimingPlan.timecode(9),
        music_profile=MusicProfile(bpm=120.0, palette=("blue", "warm white")),
        rig_profile=_rig(),
        approval=ApprovalState.approved(reviewer="director"),
    )
    return compose_song_cue_bundle(plan)


class _SongStub:
    """`_reviewed_song_commands`가 실제로 쓰는 자리만 채운 대역(콘솔 무접촉)."""

    def __init__(self, position_pool: dict) -> None:
        self._last_phaser_failures: dict[str, str] = {}
        self._last_color_failures: dict[str, str] = {}
        self._rig_paths: dict[str, str] = {}
        console = _PoolConsole(position_pool)

        class _Registry:
            def dispatch(self, call, context=None):
                from server.llm.types import ToolResult
                from server.orchestrator.tools import ToolExecution

                payload = console.query_state(call.arguments["path"])
                import json as _json

                return ToolExecution(
                    ToolResult(tool_call_id=call.id, name=call.name, content=_json.dumps(payload))
                )

        self._registry = _Registry()

    def _phaser_slots_for_bundle(self, bundle):
        return {}, {}

    _reviewed_song_timing_commands = ChatSession._reviewed_song_timing_commands
    _position_preset_pool_children = ChatSession._position_preset_pool_children
    _paged_pool_children = ChatSession._paged_pool_children
    # t232 이전 트리에는 이 메서드가 없다 — 두 트리에서 스크립트가 바이트
    # 동일하게 돌게, 있을 때만 묶는다(옛 코드는 애초에 이 자리를 안 부른다).
    if hasattr(ChatSession, "_resolve_position_preset_labels"):
        _resolve_position_preset_labels = ChatSession._resolve_position_preset_labels


def _song_cue_recalls(position_pool: dict, *, preset_start: int, positions: tuple[str, ...]):
    stub = _SongStub(position_pool)
    try:
        commands = ChatSession._reviewed_song_commands(
            stub,
            _song_composition(*positions),
            sequence_no=210,
            preset_start=preset_start,
            fids=[1, 2],
            timing=TimingPlan.timecode(9),
            layer_mapping=(),
        )
    except SpatialPointingError as error:
        return None, f"거부: {error}"
    return commands, None


# ---------------------------------------------------------------------------
# (2) 대화 포지션 수정 — `_merge_timeline_cue_position`
# ---------------------------------------------------------------------------


def _chat_edit_recall(position_pool: dict, *, preset_start: int, target: str):
    tmp = Path(tempfile.mkdtemp(prefix="t232-repro-chat-"))
    console = _PoolConsole(position_pool)
    session = _build_session(tmp, console)
    session._read_pointing_coordinates = lambda _tag: [(1, (0.0, 0.0, 5.0)), (2, (2.0, 0.0, 5.0))]
    timeline = {"sequence_number": 210, "preset_start": preset_start}
    sections = [{"name": "S1", "position": BASIC_POSITION_SEQUENCE[0]}]
    result = session._merge_timeline_cue_position(timeline, sections, 0, 1, target)
    recalls = [c for c in console.executed if "At Preset" in c]
    return recalls, result.text


# ---------------------------------------------------------------------------
# (3) 포지션 FX — `_position_fx_sequence`
# ---------------------------------------------------------------------------


def _fx_recall(position_pool: dict, *, text: str):
    tmp = Path(tempfile.mkdtemp(prefix="t232-repro-fx-"))
    console = _PoolConsole(position_pool)
    session = _build_session(tmp, console)
    session._read_pointing_coordinates = lambda _tag: [(1, (0.0, 0.0, 5.0)), (2, (2.0, 0.0, 5.0))]
    session._song_sequence_occupied = lambda _no: False
    result = session._position_fx_sequence(text)
    recalls = [c for c in console.executed if "At Preset" in c]
    return recalls, (result.text if result is not None else "(라우팅 안 됨)")


def main() -> None:
    print("(1) 감독 확정 곡 큐 — 상태 C (기본 10종이 1~10, 시작 1)")
    pool_c = _pool_payload({1 + i: name for i, name in enumerate(BASIC_POSITION_SEQUENCE)})
    commands, refusal = _song_cue_recalls(pool_c, preset_start=1, positions=("Center", "Ring In"))
    if refusal:
        print(f"  {refusal}")
    else:
        for line in commands:
            if "At Preset" in line:
                print(f"  {line}")
        print("  전체 명령열:")
        for line in commands:
            print(f"    {line}")

    print()
    print("(1) 감독 확정 곡 큐 — 상태 D (시트 프리셋 10개가 1~10, 진짜 Center는 41)")
    pool_d = _pool_payload({1 + i: f"POS{i + 1:02d} 시트" for i in range(10)})
    pool_d["children"].append({"i": 41, "name": "Center"})
    commands, refusal = _song_cue_recalls(pool_d, preset_start=1, positions=("Center",))
    if refusal:
        print(f"  {refusal}")
    else:
        for line in commands:
            if "At Preset" in line:
                print(f"  'Center' 큐 recall -> {line}")

    print()
    print("(1) 감독 확정 곡 큐 — 상태 D2 ('Center'가 어디에도 없음)")
    pool_d2 = _pool_payload({1 + i: f"POS{i + 1:02d} 시트" for i in range(10)})
    _commands, refusal = _song_cue_recalls(pool_d2, preset_start=1, positions=("Center",))
    print(f"  {refusal}")

    print()
    print("(2) 대화 포지션 수정 — 상태 C (기본 10종이 21~30, 시작 21)")
    pool_c21 = _pool_payload({21 + i: name for i, name in enumerate(BASIC_POSITION_SEQUENCE)})
    recalls, text = _chat_edit_recall(pool_c21, preset_start=21, target="Center")
    print(f"  recall -> {recalls}")
    print(f"  회신: {text}")

    print()
    print("(2) 대화 포지션 수정 — 상태 D (시트 프리셋 10개가 21~30, 진짜 Center는 41)")
    pool_d21 = _pool_payload({21 + i: f"POS{i + 1:02d} 시트" for i in range(10)})
    pool_d21["children"].append({"i": 41, "name": "Center"})
    recalls, text = _chat_edit_recall(pool_d21, preset_start=21, target="Center")
    print(f"  recall -> {recalls}")
    print(f"  회신: {text}")

    print()
    print("(2) 대화 포지션 수정 — 상태 D2 ('Center'가 어디에도 없음)")
    pool_d2_21 = _pool_payload({21 + i: f"POS{i + 1:02d} 시트" for i in range(10)})
    recalls, text = _chat_edit_recall(pool_d2_21, preset_start=21, target="Center")
    print(f"  recall -> {recalls}")
    print(f"  회신: {text}")

    print()
    print("(3) 포지션 FX — 상태 C (FX 10종이 21~30, 시작 21)")
    fx_pool_c = _pool_payload({21 + i: name for i, name in enumerate(FX_POSITION_SEQUENCE)})
    recalls, text = _fx_recall(
        fx_pool_c, text="원을 그리는 포지션 이펙트 시퀀스 201 걸어줘, 21번부터"
    )
    print(f"  recall -> {recalls}")
    print(f"  회신: {text[:60]}...")

    print()
    print("(3) 포지션 FX — 상태 D (21~30은 다른 이름, 진짜 'Circle Base'는 61)")
    fx_pool_d = _pool_payload({21 + i: f"OTHER{i}" for i in range(10)})
    fx_pool_d["children"].append({"i": 61, "name": "Circle Base"})
    recalls, text = _fx_recall(
        fx_pool_d, text="원을 그리는 포지션 이펙트 시퀀스 201 걸어줘, 21번부터"
    )
    print(f"  recall -> {recalls}")
    print(f"  회신: {text[:80]}...")

    print()
    print("(3) 포지션 FX — 상태 D2 ('Circle Base'가 어디에도 없음)")
    fx_pool_d2 = _pool_payload({21 + i: f"OTHER{i}" for i in range(10)})
    recalls, text = _fx_recall(
        fx_pool_d2, text="원을 그리는 포지션 이펙트 시퀀스 201 걸어줘, 21번부터"
    )
    print(f"  recall -> {recalls}")
    print(f"  회신: {text[:80]}...")


if __name__ == "__main__":
    main()
