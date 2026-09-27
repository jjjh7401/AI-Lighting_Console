"""t462 완료 조건 ③ — probe_a 와 같은 곡을 대화 길로 만들어 **콘솔 명령**까지 뽑는다.

probe_a.py 와 같은 11구간·BPM 120 곡을 실제 대화 길 빌더로 짓고, 블라인더 그룹
(콘솔 그룹 이름 ``BLIND``, 번호 14 — 가짜 주소록 한 줄)을 준 채 실제 명령 생성기
(``ChatSession._reviewed_song_commands``)로 콘솔 명령을 만든다. 콘솔 쓰기는 없다.

실행: uv run python .moai/reports/t462/probe_a_console.py
"""

from server.design.profile import MusicProfile
from server.design.rig import build_rig_profile
from server.design.song_cue_composer import compose_song_cue_bundle
from server.design.song_plan import TimingPlan
from server.spatial.pointing import BASIC_POSITION_SEQUENCE
from server.spatial.position_cuesheet import PositionSheetSection
from server.web.session import (
    ChatSession,
    _blinder_group_no,
    _build_unified_song_plan,
    _confirmed_section_names,
    _infer_confirmed_role,
)

LAYER_MAPPING = [{"role": "effect", "group_no": 14, "group_name": "BLIND"}]

d_levels = [2, 3, 4, 5, 3, 4, 5, 2, 4, 5, 5]
roles = [_infer_confirmed_role(i, d_levels) for i in range(len(d_levels))]
names = _confirmed_section_names(roles)
sections, t = [], 0
for n, r, d in zip(names, roles, d_levels, strict=True):
    sections.append(PositionSheetSection(name=n, start_ms=t, mood="", d_level=d, role=r))
    t += 16000
timing = TimingPlan.trig_time()
plan = _build_unified_song_plan(
    sections=sections,
    profile=MusicProfile(bpm=120.0),
    rig=build_rig_profile(patch=[], groups={}, coords=[]),
    records=(),
    timing=timing,
    sequence_no=120,
    blinder_group_no=_blinder_group_no(LAYER_MAPPING),
)
res = compose_song_cue_bundle(plan)
print("== cues")
for c in res.bundle.cues:
    fixture = c.accent_fixture.to_dict() if c.accent_fixture else None
    print(
        f"{c.cue_number:>5g} {c.kind:13} {c.cue_name:16} D{c.d_level} key={c.dimmer.key_pct} "
        f"pre_drop_from={c.pre_drop_from} blinder={fixture} start={c.timing.start_ms}"
    )
print("== arc_notes")
for note in res.bundle.arc_notes:
    print(note)


class _Stub:
    def __init__(self):
        self._last_phaser_failures = {}
        self._last_color_failures = {}

    def _phaser_slots_for_bundle(self, bundle):
        return {}, {}

    def _resolve_position_preset_labels(self, labels, *, start, span, pool_no=None):
        return {label: start + BASIC_POSITION_SEQUENCE.index(label) for label in labels}

    _reviewed_song_timing_commands = ChatSession._reviewed_song_timing_commands


commands = ChatSession._reviewed_song_commands(
    _Stub(),
    res,
    sequence_no=120,
    preset_start=1,
    fids=[1, 2, 3, 4],
    timing=timing,
    layer_mapping=LAYER_MAPPING,
)
print("== console commands")
for line in commands:
    print(line)
