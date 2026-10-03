"""카드 t501 M4 — AC-LDRENDER-004 오프라인 판독, t499 8곡 재현(M3 측정 스크립트
재사용, `measure_ac001_8songs.rehearse`/`_gate_cues_from_commands` 그대로 — DSP
재실행 없음·analysis.json 재사용, 그 스크립트 머리말·§방법론과 동일 전제).

이 스크립트가 추가로 재는 것(M3 의 AC-001 측정과 별개 축):

1. 곡당 고유 송신 RGB 수(target 2~3) — `ldrender_gate.color_count` 재사용.
2. 연속 구간 큐 사이 색 변화 횟수 — `ldrender_gate.color_change_count` 재사용.
3. 큐 1개가 동시에 내는 구별 **유채색**(웜화이트 제외) 최대 수 — 이 스크립트가
   새로 재는 값(§6.3 "최대 2개" 판정에 필요, 기존 게이트 모듈엔 없음 — M1 이
   제품화한 `layer_diversity`는 디머 포함 전체 상태를 세지 색만 세지 않는다).
4. 역할별 수신 색 확인 — back/mover=지배색(palette[0]), side/wash=보조색
   (palette[1]), key=웜화이트. 대표 구간 큐(첫 section 큐) 1개로 확인한다.

입력: `.moai/reports/t499/runs/<곡>/analysis.json` (8개, t499 커밋) — M3 와 동일.
출력: 표준출력 + `.moai/reports/t501/ac004_8songs.json`.

실행: uv run python .moai/reports/t501/measure_ac004_8songs.py
콘솔 접촉: 0건(in-process FakeConsole, t499/M3 와 동일).
"""

from __future__ import annotations

import json
from pathlib import Path

import measure_ac001_8songs as m  # noqa: E402 (같은 디렉터리, sys.path 는 m 이 이미 설정)

from server.design import color_names as _COLOR_NAMES
from server.design.ldrender_gate import color_change_count, color_count, is_exempt_cue
from server.design.rig import resolve_layer_role

HERE = Path(__file__).resolve().parent
_WARM_WHITE_RGB = _COLOR_NAMES.resolve_color_name("Warm White")
assert _WARM_WHITE_RGB is not None


def _max_chromatic_colours_per_cue(gate_cues) -> tuple[int, str]:
    """큐 1개가 동시에 내는 구별 유채색(웜화이트 제외) 최대 수 — (최대값, 그
    최대를 낸 큐 번호). 웜화이트는 §6.3 "최대 2개" 집계 밖(spec.md §3.2 [HARD]
    플래그)이라 이 함수가 직접 뺀다 — `ldrender_gate.color_count`는 송신 RGB
    전체(웜화이트 포함)를 센다."""
    worst = 0
    worst_cue = ""
    for cue in gate_cues:
        if is_exempt_cue(cue):
            continue
        chromatic = {rgb for rgb in cue.sent_rgb if rgb != _WARM_WHITE_RGB}
        if len(chromatic) > worst:
            worst = len(chromatic)
            worst_cue = cue.cue_no
    return worst, worst_cue


def _role_colour_check(bundle_cues, layer_mapping, rig_role_view_by_role) -> dict:
    """대표 section 큐(첫 번째) 1개 — back/mover=palette[0], side/wash=palette[1],
    key=웜화이트 수신 확인. `rig_role_view_by_role`는 그 큐의 역할별 rgb 집합."""
    first_section = next((c for c in bundle_cues if c.kind == "section"), None)
    if first_section is None:
        return {"checked": False}
    palette = first_section.color.palette
    dominant = _COLOR_NAMES.resolve_color_name(palette[0]) if palette else None
    accent = _COLOR_NAMES.resolve_color_name(palette[1]) if len(palette) > 1 else None
    result = {"checked": True, "cue_no": first_section.cue_number, "palette": list(palette)}
    for role in ("back", "mover", "side", "wash", "key"):
        rgbs = rig_role_view_by_role.get(role)
        result[role] = sorted(rgbs) if rgbs else []
    result["back_matches_dominant"] = dominant in (rig_role_view_by_role.get("back") or set())
    result["mover_matches_dominant"] = dominant in (rig_role_view_by_role.get("mover") or set())
    result["side_matches_accent"] = accent is not None and accent in (
        rig_role_view_by_role.get("side") or set()
    )
    result["wash_matches_accent"] = accent is not None and accent in (
        rig_role_view_by_role.get("wash") or set()
    )
    result["key_matches_warm_white"] = _WARM_WHITE_RGB in (
        rig_role_view_by_role.get("key") or set()
    )
    return result


def _role_rgb_sets_for_cue(commands: list[str], bundle_cues, target_cue_no: float) -> dict:
    """특정 큐 번호의 역할별 수신 rgb 집합 — 트래킹 상태가 아니라 **그 큐 자신이
    낸 줄**만 본다(역할 배정이 실제로 그 큐에서 발화했는지 확인하려는 것이지
    트래킹 잔존값을 보려는 게 아니다)."""
    import re

    STORE = re.compile(r"^Store Sequence (\d+) Cue ([\d.]+) '([^']*)'")
    FIX = re.compile(r"^Fixture ((?:\d+)(?: \+ \d+)*) ;(.*)$")
    GRP = re.compile(r"^Group (\d+) ;(.*)$")
    ATTR = re.compile(r"Attribute '(\w+)' At ([\d.]+)")

    pending: list[str] = []
    cues: list[tuple[str, list[str]]] = []
    for line in commands:
        s = STORE.match(line)
        if s:
            cues.append((s.group(2), pending))
            pending = []
        elif FIX.match(line) or GRP.match(line):
            pending.append(line)

    role_rgbs: dict[str, set] = {}
    for cue_no, lines in cues:
        if float(cue_no) != target_cue_no:
            continue
        for line in lines:
            gm = GRP.match(line)
            if gm:
                group_no = int(gm.group(1))
                name = m.REAL_GROUPS[group_no - 1][1]
                role = resolve_layer_role(name)
                if role is None:
                    continue
                attrs = dict(ATTR.findall(gm.group(2)))
                if "ColorRGB_R" in attrs:
                    rgb = tuple(float(attrs[k]) for k in ("ColorRGB_R", "ColorRGB_G", "ColorRGB_B"))
                    role_rgbs.setdefault(role, set()).add(rgb)
                continue
            fm = FIX.match(line)
            if fm:
                attrs = dict(ATTR.findall(fm.group(2)))
                if "ColorRGB_R" in attrs:
                    rgb = tuple(float(attrs[k]) for k in ("ColorRGB_R", "ColorRGB_G", "ColorRGB_B"))
                    # 베이스라인(전체 fids) 색 — back/mover 는 이 값을 그대로
                    # 받는다(M4 가 이 둘에 델타 줄을 내지 않기로 결정했으므로,
                    # "받았다"의 증거는 베이스라인 자신이다 — Fixture 로 주소된
                    # 줄 중 ColorRGB 를 가진 줄이 이 큐의 베이스라인이다).
                    role_rgbs.setdefault("__baseline__", set()).add(rgb)
    return role_rgbs


def main() -> None:
    analysis_files = sorted((m.T499 / "runs").glob("*/analysis.json"))
    analysis_files = [p for p in analysis_files if p.parent.name != "Rain_first"]
    assert len(analysis_files) == 8, [p.parent.name for p in analysis_files]

    summary = []
    for analysis_path in analysis_files:
        song_name = analysis_path.parent.name
        result = m.rehearse(song_name, analysis_path)
        gate_cues = m._gate_cues_from_commands(result["commands"], result["bundle_cues"])
        song_colour_count = color_count(gate_cues)
        song_colour_changes = color_change_count(gate_cues)
        max_chromatic, max_chromatic_cue = _max_chromatic_colours_per_cue(gate_cues)

        first_section = next((c for c in result["bundle_cues"] if c.kind == "section"), None)
        role_rgbs = (
            _role_rgb_sets_for_cue(
                result["commands"], result["bundle_cues"], first_section.cue_number
            )
            if first_section is not None
            else {}
        )
        role_check = _role_colour_check(result["bundle_cues"], (), role_rgbs)
        # back/mover 는 델타 줄이 없다(베이스라인이 이미 지배색) — __baseline__ 집합으로 대신 확인.
        baseline = role_rgbs.get("__baseline__", set())
        role_check["back"] = sorted(baseline)
        role_check["mover"] = sorted(baseline)
        role_check["back_matches_dominant"] = (
            _COLOR_NAMES.resolve_color_name(role_check["palette"][0]) in baseline
            if role_check.get("palette")
            else False
        )
        role_check["mover_matches_dominant"] = role_check["back_matches_dominant"]

        row = {
            "song": song_name,
            "unique_sent_rgb_count": song_colour_count,
            "colour_change_count": song_colour_changes,
            "max_simultaneous_chromatic_colours": max_chromatic,
            "max_chromatic_cue": max_chromatic_cue,
            "role_colour_check": role_check,
        }
        summary.append(row)
        print(
            f"{song_name}: 고유RGB {song_colour_count}종 · 색변화 {song_colour_changes}회 · "
            f"최대동시유채색 {max_chromatic}(Q{max_chromatic_cue}) · "
            f"back==dominant {role_check['back_matches_dominant']} · "
            f"side==accent {role_check.get('side_matches_accent')} · "
            f"key==warmwhite {role_check.get('key_matches_warm_white')}"
        )

    (HERE / "ac004_8songs.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), "utf-8"
    )


if __name__ == "__main__":
    main()
