"""t467 실측 — 포지션 프리셋별 「기구 간 팬 각도 퍼짐」이 팬 폭 경고의 재료가 되는가.

앱이 포지션 프리셋을 저장할 때 쓰는 계산(``basic_position_presets``·``fx_position_presets``)을
4 m 바 위 무빙 4대(높이 6 m)에 돌려, 프리셋마다 기구 팬 각도의 (최대 − 최소) ÷ 2 를 잰다.
팬은 원을 돌므로 첫 기구 기준으로 (−180, 180] 에 접어 잰다.

실행: uv run python .moai/reports/t467/probe_pan_spread.py
"""

from server.spatial.pointing import (
    _normalize_degrees,
    basic_position_presets,
    fx_position_presets,
)

BAR = tuple((fid, (x, 0.0, 6.0)) for fid, x in ((1, -3.0), (2, -1.0), (3, 1.0), (4, 3.0)))


def half_width(pans):
    reference = pans[0]
    offsets = [_normalize_degrees(pan - reference) for pan in pans]
    return round((max(offsets) - min(offsets)) / 2.0, 1)


for label, aims, skipped in (*basic_position_presets(BAR), *fx_position_presets(BAR)):
    pans = [round(pan, 1) for _fid, pan, _tilt in aims]
    tilts = [round(tilt, 1) for _fid, _pan, tilt in aims]
    width = half_width(pans) if pans else None
    print(f"{label:13} ±{width}°  pans={pans}  tilts={tilts}  skipped={list(skipped)}")
