"""t480 M2 — 업로드 어댑터가 실제 업로드 구간으로 조립기 번들을 만드는지 본다(콘솔 없음).

실행(저장소 루트): `uv run python .moai/reports/t480/m2_smoke.py`
"""

from server.design.rig import build_rig_profile
from server.design.song_cue_composer import compose_song_cue_bundle
from server.design.song_plan import TimingPlan
from server.design.upload_song_plan import build_upload_song_plan, upload_plan_sections
from server.looks.songcue import parse_sections
from server.tests.test_songcue_t429_repeat_chorus_collision import (
    _ICE_CREAM_SECTIONS,
    _RAIN_SECTIONS,
)

for song, raw, bpm in (("Ice cream", _ICE_CREAM_SECTIONS, 100.4), ("Rain", _RAIN_SECTIONS, 76.0)):
    for tempo in (bpm, None):
        sections = parse_sections(raw)
        planned = upload_plan_sections(sections, explicit_dynamics=None, confirmed_default=False)
        plan, notes = build_upload_song_plan(
            song_title=song,
            sections=planned,
            bpm=tempo,
            genre="rock",
            records=(),
            rig=build_rig_profile(patch=[], groups={}, coords=[]),
            sequence_no=1,
            timing=TimingPlan.timecode(9),
            position_disabled_reason="업로드 길: 포지션 프리셋 시작 번호 없음",
        )
        result = compose_song_cue_bundle(plan)
        bundle = result.bundle
        roles = [d.role for d in plan.sections]
        print(
            f"## {song} bpm={tempo} sections={len(sections)} cues={len(bundle.cues) if bundle else None}"
            f" requery={len(result.requery_requirements)} notes={len(notes)}"
        )
        print("   roles:", roles)
        if bundle is not None:
            for cue in bundle.cues:
                print(
                    f"   Q{cue.cue_number:g} {cue.kind:<12} {cue.cue_name:<18} D{cue.d_level}"
                    f" dim={cue.dimmer.key_pct} color={cue.color.palette[:2]}"
                    f" pos={cue.position.stored} accent={cue.accents}"
                )
