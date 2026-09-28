"""t480 M2 — 업로드 어댑터가 실제 업로드 구간으로 조립기 번들을 만드는지 본다(콘솔 없음).

M3 에서 D4(인터뷰 없으면 Q2 추천 1순위 팔레트)가 들어와 팔레트 출처와 주색의 RGB
해석 여부도 찍는다. `jazz` 는 §7 장르 표에 없는 단어의 대조군이다.

실행(저장소 루트): `uv run python .moai/reports/t480/m2_smoke.py`
"""

from server.design.color_names import resolve_color_name
from server.design.rig import build_rig_profile
from server.design.song_cue_composer import compose_song_cue_bundle
from server.design.song_plan import TimingPlan
from server.design.upload_song_plan import build_upload_song_plan, upload_plan_sections
from server.looks.songcue import parse_sections
from server.tests.song_section_fixtures import ICE_CREAM_SECTIONS as _ICE_CREAM_SECTIONS
from server.tests.song_section_fixtures import RAIN_SECTIONS as _RAIN_SECTIONS

for song, raw, bpm in (("Ice cream", _ICE_CREAM_SECTIONS, 100.4), ("Rain", _RAIN_SECTIONS, 76.0)):
    for tempo, genre in ((bpm, "rock"), (None, "edm"), (bpm, "jazz")):
        sections = parse_sections(raw)
        planned = upload_plan_sections(sections, explicit_dynamics=None, confirmed_default=False)
        plan, notes, palette = build_upload_song_plan(
            song_title=song,
            sections=planned,
            bpm=tempo,
            genre=genre,
            records=(),
            rig=build_rig_profile(patch=[], groups={}, coords=[]),
            sequence_no=1,
            timing=TimingPlan.timecode(9),
            position_disabled_reason="업로드 길: 포지션 프리셋 시작 번호 없음",
        )
        result = compose_song_cue_bundle(plan)
        bundle = result.bundle
        roles = [d.role for d in plan.sections]
        cue_count = len(bundle.cues) if bundle else None
        print(
            f"## {song} genre={genre} bpm={tempo} sections={len(sections)} cues={cue_count}"
            f" requery={len(result.requery_requirements)} notes={len(notes)}"
        )
        print("   roles:", roles)
        print("  ", palette.notice(), "| profile.palette =", plan.music_profile.palette)
        if bundle is not None:
            unresolved = 0
            for cue in bundle.cues:
                primary = cue.color.palette[0] if cue.color.palette else None
                rgb = resolve_color_name(primary) if primary else None
                unresolved += rgb is None
                print(
                    f"   Q{cue.cue_number:g} {cue.kind:<12} {cue.cue_name:<18} D{cue.d_level}"
                    f" dim={cue.dimmer.key_pct} color={cue.color.palette[:2]} rgb={rgb}"
                    f" accent={cue.accents}"
                )
            print(f"   primary colours without RGB: {unresolved}/{len(bundle.cues)}")
