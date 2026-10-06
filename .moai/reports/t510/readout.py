"""t510 — t499 readout.py 복사. 바뀐 점 두 가지뿐:
  1) fid_names.json 은 t499 폴더의 것을 읽는다(같은 파일, 복사 안 함).
  2) SIDE-ALL·WASH-ALL·MOVER-ALL 펼침 규칙 추가 — LDRENDER-001 송신이 이 그룹을 쓴다.
     SIDE-ALL = SIDE-L ∪ SIDE-R, WASH-ALL = WASH-U ∪ WASH-D, MOVER-ALL = MOVER-U ∪ MOVER-D
     (이름 첫 단어 기반 — INFERRED, t499 와 같은 갈래). summary.json 은 이 폴더에 쓴다.

원문(t499):
t499 — 8곡 연출 판독: 설계 층(조립기 번들) 대 송신 층(승인 = 송신 명령)을 나란히 센다.

t498 stage_content.py 의 일반화. 콘솔 접촉 없음 — rehearse_song.py 가 남긴 파일만 읽는다.

입력(곡 디렉터리마다):
  bundle_full.json              설계 층 — ComposedCue.to_dict() 전량
  console_commands_approved.txt 송신 층 — 승인 미리보기 = 가짜 콘솔 송신(곡마다 cmp 로 확인)
  replies.json                  앱 회신 — 큐별 「페이저 제안」 라벨은 여기서만 읽힌다
  ../../fid_names.json          기구 번호 → 이름 첫 단어(그룹). 이름 기반 추정 — INFERRED

송신 층 값 모델(큐 하나):
  큐 경계 = `Store Sequence N Cue X` 줄. 그 앞의 값 줄들을 순서대로 적용(콘솔 last-wins 가정).
  `Fixture <목록> ; …` 은 목록의 기구에, `Group <n> ; …` 은 그룹 풀 이름
  → 기구 이름 첫 단어로 펼친다. 그룹 n 의 이름은 rehearse_song.py 의 REAL_GROUPS
  (t498 run0 실기 판독), 구성원은 이름 첫 단어 — INFERRED.
  SIDE-ALL·WASH-ALL·MOVER-ALL·ALL·ODD·EVEN 은 이번 송신에 안 나와서 펼침 규칙을
  안 만들었다(나오면 멈춘다).
  트래킹: 큐 안에서 값을 안 받은 기구는 앞 큐 값을 이어 받는다
  (콘솔 트래킹 가정, 판독 아님 — INFERRED).

실행: uv run python .moai/reports/t499/readout.py [곡 디렉터리 …]   (기본: runs/ 아래 8곡)
출력: 표준출력 + runs/<곡>/readout.json + summary.json
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

HERE = Path(__file__).resolve().parent
FID_TABLE = {
    int(k): v
    for k, v in json.loads((HERE.parent / "t499" / "fid_names.json").read_text("utf-8")).items()
}
#: rehearse_song.py REAL_GROUPS 와 같은 표(t498 run0 실기 판독). 펼침은 이름 첫 단어로 한다.
GROUP_NAMES = {
    1: "ALL", 2: "KEY", 3: "FOH", 4: "BACK", 5: "SIDE-L", 6: "SIDE-R", 7: "SIDE-ALL",
    8: "WASH-U", 9: "WASH-D", 10: "WASH-ALL", 11: "MOVER-U", 12: "MOVER-D", 13: "MOVER-ALL",
    14: "BLIND", 15: "STROBE", 16: "HAZE", 17: "ODD", 18: "EVEN",
}  # fmt: skip
#: 카드가 부른 리그 그룹 8종 → 이름 첫 단어 묶음.
RIG = OrderedDict(
    KEY=("KEY",), FOH=("FOH",), BACK=("BACK",), SIDE=("SIDE-L", "SIDE-R"),
    WASH=("WASH-U", "WASH-D"), MOVER=("MOVER-U", "MOVER-D"), BLIND=("BLIND",), STROBE=("STROBE",),
)  # fmt: skip
FIX = re.compile(r"^Fixture ((?:\d+)(?: \+ \d+)*) ;(.*)$")
GRP = re.compile(r"^Group (\d+) ;(.*)$")
STORE = re.compile(r"^Store Sequence (\d+) Cue ([\d.]+) '([^']*)'")
ATTR = re.compile(r"Attribute '(\w+)' At ([\d.]+)")
PRESET = re.compile(r"At Preset (\d+)\.(\d+)")
PHASER_HINT = re.compile(r"^큐 ([\d.]+) (.+?) — .*?페이저 제안: (.+?)\s*$")


#: t510 추가 — 묶음 그룹 펼침(이름 첫 단어 기반, INFERRED).
_ALL_GROUPS = {
    "SIDE-ALL": ("SIDE-L", "SIDE-R"),
    "WASH-ALL": ("WASH-U", "WASH-D"),
    "MOVER-ALL": ("MOVER-U", "MOVER-D"),
}


def members(group_no: int) -> list[int]:
    name = GROUP_NAMES[group_no]
    names = _ALL_GROUPS.get(name, (name,))
    found = [f for f, row in FID_TABLE.items() if row["group"] in names]
    if not found:
        raise SystemExit(
            f"Group {group_no} {name!r}: 이름 첫 단어로 펼칠 기구가 없다 — 규칙을 만들어라"
        )
    return found


def section_role(name: str) -> str:
    low = name.lower()
    for role in (
        "return",
        "intro",
        "verse",
        "pre-chorus",
        "chorus",
        "drop",
        "bridge",
        "breakdown",
        "outro",
        "finale",
    ):
        if role in low:
            return role
    return "other"


#: 정본 §6 표의 밝기 대역(%). finale 은 §6 표에 행이 없다
#: (「마지막 drop」·「outro」 둘 다 이름으로 안 갈린다).
STD_DIMMER = {
    "intro": (20, 40), "verse": (25, 50), "pre-chorus": (40, 55), "chorus": (80, 100),
    "drop": (80, 100), "bridge": (20, 35), "breakdown": (20, 35),
}  # fmt: skip


def parse_sent(lines: list[str]):
    """송신 줄 → 큐 목록. 큐마다 값 줄과 그 줄이 만든 기구별 상태."""
    cues, pending = [], []
    for line in lines:
        m = STORE.match(line)
        if m:
            cues.append({"no": m.group(2), "name": m.group(3), "lines": pending})
            pending = []
        elif FIX.match(line) or GRP.match(line):
            pending.append(line)
    return cues


def apply(lines: list[str], state: dict[int, dict]) -> dict:
    """값 줄을 순서대로 적용. 반환: 이 큐의 선택 묶음·그룹 줄·색·프리셋·디머 기록."""
    selections, group_lines, rgbs, presets, dimmers = [], [], set(), Counter(), []
    for line in lines:
        if m := FIX.match(line):
            fids = [int(x) for x in m.group(1).split(" + ")]
            body = m.group(2)
            selections.append(tuple(fids))
        else:
            m = GRP.match(line)
            fids = members(int(m.group(1)))
            body = m.group(2)
            group_lines.append(f"Group {m.group(1)}({GROUP_NAMES[int(m.group(1))]}) {body.strip()}")
        attrs = dict(ATTR.findall(body))
        if p := PRESET.search(body):
            presets[f"{p.group(1)}.{p.group(2)}"] += 1
        rgb = None
        if "ColorRGB_R" in attrs:
            rgb = tuple(float(attrs[k]) for k in ("ColorRGB_R", "ColorRGB_G", "ColorRGB_B"))
            rgbs.add(rgb)
        for fid in fids:
            st = state.setdefault(fid, {})
            if p:
                st["pos"] = f"{p.group(1)}.{p.group(2)}"
            if "Dimmer" in attrs:
                st["dim"] = float(attrs["Dimmer"])
            if rgb is not None:
                st["rgb"] = rgb
        if "Dimmer" in attrs:
            dimmers.append(float(attrs["Dimmer"]))
    return {
        "selections": selections,
        "group_lines": group_lines,
        "rgbs": rgbs,
        "presets": presets,
        "dimmers": dimmers,
    }


def rig_view(state: dict[int, dict]) -> OrderedDict:
    """리그 그룹 8종별로 기구 상태를 묶는다 — 그룹 안 기구들이 같은 값이면 값 하나."""
    view = OrderedDict()
    for rig, prefixes in RIG.items():
        vals = {
            json.dumps(state.get(f, {}), sort_keys=True)
            for f, row in FID_TABLE.items()
            if row["group"] in prefixes
        }
        view[rig] = sorted(vals)
    return view


def read_song(song_dir: Path) -> dict:
    bundle = json.loads((song_dir / "bundle_full.json").read_text("utf-8"))
    sent = (song_dir / "console_commands_approved.txt").read_text("utf-8").splitlines()
    sent_exec = (song_dir / "console_commands_sent.txt").read_text("utf-8").splitlines()
    replies = json.loads((song_dir / "replies.json").read_text("utf-8"))
    hints = {}
    for text in replies:
        for row in (text or "").splitlines():
            if m := PHASER_HINT.match(row.strip()):
                hints[m.group(1)] = m.group(3)

    design = bundle["cues"]
    sent_cues = parse_sent(sent)
    state: dict[int, dict] = {}
    rows = []
    prev_design_color = prev_sent_rgb = None
    for cue in sent_cues:
        d = next((c for c in design if f"{c['cue_number']:g}" == cue["no"]), None)
        rec = apply(cue["lines"], state)
        view = rig_view(state)
        distinct_layers = len({tuple(v) for v in view.values() if v})
        stage_rgbs = {
            json.dumps(state[f].get("rgb")) for f in state if state[f].get("rgb") is not None
        }
        pal = (d or {}).get("color", {}).get("palette") or []
        fx = (d or {}).get("fx", {})
        row = {
            "cue": cue["no"],
            "name": cue["name"],
            "kind": (d or {}).get("kind"),
            "role": section_role(cue["name"]),
            "d": (d or {}).get("d_level"),
            # 설계 층
            "design_palette": pal,
            "design_position": (d or {}).get("position", {}).get("stored"),
            "design_key_pct": (d or {}).get("dimmer", {}).get("key_pct"),
            "design_back_pct": (d or {}).get("dimmer", {}).get("back_pct"),
            "design_fx_requested": fx.get("requested", []),
            "design_fx_permitted": fx.get("permitted", []),
            "design_phaser_hint": hints.get(cue["no"]),
            "design_accents": (d or {}).get("accents", []),
            "design_accent_fixture": (d or {}).get("accent_fixture"),
            "design_pre_drop_from": (d or {}).get("pre_drop_from"),
            # 송신 층
            "sent_lines": len(cue["lines"]),
            "sent_selection_sets": len(set(rec["selections"])),
            "sent_selection_sizes": sorted({len(s) for s in rec["selections"]}),
            "sent_group_lines": rec["group_lines"],
            "sent_rgb_in_cue": sorted(rec["rgbs"]),
            "sent_presets": dict(rec["presets"]),
            "sent_dimmers": rec["dimmers"],
            "stage_distinct_rgb": len(stage_rgbs),
            "stage_rig_layers": distinct_layers,
            "stage_rig_view": {k: [json.loads(x) for x in v] for k, v in view.items()},
            "design_color_changed": prev_design_color is not None
            and pal[:1] != prev_design_color[:1],
            "design_palette_changed": prev_design_color is not None and pal != prev_design_color,
            "sent_color_changed": prev_sent_rgb is not None
            and sorted(rec["rgbs"]) not in ([], prev_sent_rgb),
        }
        if pal:
            prev_design_color = pal
        if rec["rgbs"]:
            prev_sent_rgb = sorted(rec["rgbs"])
        rows.append(row)

    phaser_lines = [x for x in sent if "At Preset" in x and not re.search(r"At Preset 2\.", x)]
    return {
        "song": song_dir.name,
        "approved_equals_sent": sent == sent_exec,
        "n_lines": len(sent),
        "n_design_cues": len(design),
        "n_sent_cues": len(sent_cues),
        "arc_notes": bundle["arc_notes"],
        "lint_findings": bundle["lint_findings"],
        "phaser_or_other_preset_lines": phaser_lines,
        "cues": rows,
    }


def violations(song: dict) -> list[tuple[str, str]]:
    """정본 §6·§6.1·§6.2·§6.3·§7·§8 위반 — (조항, 내용). 송신 층 기준(무대에 나가는 것)."""
    out = []
    cues = [c for c in song["cues"] if c["kind"] == "section"]
    # §6 표 — 밝기 대역
    for c in cues:
        band = STD_DIMMER.get(c["role"])
        dim = c["design_key_pct"]
        if band and dim is not None and not band[0] <= dim <= band[1]:
            out.append(
                ("§6 밝기", f"큐 {c['cue']} {c['name']} 디머 {dim:g} — 대역 {band[0]}~{band[1]}")
            )
    # §6 표 — 색: 구간 성격이 달라도 송신 색이 같다
    roles_by_rgb = {}
    for c in cues:
        for rgb in c["sent_rgb_in_cue"]:
            roles_by_rgb.setdefault(tuple(rgb), set()).add(c["role"])
    for rgb, roles in roles_by_rgb.items():
        if len(roles) >= 3:
            out.append(
                (
                    "§6 색",
                    f"RGB {tuple(int(x) for x in rgb)} 한 값이 구간 성격 {len(roles)}종"
                    f"({', '.join(sorted(roles))})에 똑같이 나감",
                )
            )
    # §6 표 — 빔·움직임(효과): 설계가 요청했는데 송신 0
    req = sum(len(c["design_fx_requested"]) for c in song["cues"])
    hint = sum(1 for c in song["cues"] if c["design_phaser_hint"])
    if (req or hint) and not song["phaser_or_other_preset_lines"]:
        out.append(("§6 움직임·효과", f"효과 요청 {req}건 · 페이저 제안 {hint}큐 → 송신 0줄"))
    # §6.1 — 큐당 액센트 하나 (설계 층)
    for c in song["cues"]:
        if len(c["design_accents"]) > 1:
            out.append(("§6.1", f"큐 {c['cue']} 액센트 {len(c['design_accents'])}개"))
    # §6.2 — 층 역할: 리그 그룹 8종 중 서로 다른 값 묶음 수
    flat = [c for c in cues if c["stage_rig_layers"] <= 2]
    if flat:
        out.append(
            (
                "§6.2 층",
                f"구간 큐 {len(cues)}개 중 {len(flat)}개가 무대 값 묶음 ≤2(8그룹 대부분이 같은 값)",
            )
        )
    # §6.3 — 곡당 2~3색
    song_rgbs = {tuple(r) for c in cues for r in c["sent_rgb_in_cue"]}
    design_cols = {p for c in cues for p in c["design_palette"]}
    if not 2 <= len(song_rgbs) <= 3:
        out.append(
            (
                "§6.3 색",
                f"곡 전체 송신 색 {len(song_rgbs)}개(기준 2~3) · "
                f"설계 팔레트 이름 {len(design_cols)}종 {sorted(design_cols)}",
            )
        )
    # §7 — 후렴 회차 상승: 앞 후렴과 송신 값이 같으면 「새 요소 하나」가 없다
    choruses = [c for c in cues if c["role"] == "chorus"]
    flat_steps = []
    for a, b in zip(choruses, choruses[1:], strict=False):
        if a["stage_rig_view"] == b["stage_rig_view"]:
            flat_steps.append(f"{a['name']}→{b['name']}")
    if flat_steps:
        out.append(
            (
                "§7 상승",
                f"후렴 {len(choruses)}회 중 앞 회차와 무대 값이 완전히 같은 이음 "
                f"{len(flat_steps)}개: {', '.join(flat_steps)}",
            )
        )
    # §8 — 후렴·드롭 직전에 밝기를 빼는 큐
    missing = []
    for prev2, prev, c in zip([None] + cues, cues, cues[1:], strict=False):
        if c["role"] in ("chorus", "drop") and prev["role"] not in ("chorus", "drop"):
            before = prev2["design_key_pct"] if prev2 else None
            if c["design_pre_drop_from"] is None and not (
                before is not None
                and prev["design_key_pct"] is not None
                and prev["design_key_pct"] < before
            ):
                missing.append(c["name"])
    if missing:
        out.append(
            (
                "§8 어둠",
                f"비후렴→후렴 진입 {len(missing)}곳에 직전 밝기 내림 없음: {', '.join(missing)}",
            )
        )
    return out


def main(argv: list[str]) -> None:
    dirs = [Path(x) for x in argv] or sorted(
        p
        for p in (HERE / "runs").iterdir()
        if (p / "bundle_full.json").is_file() and p.name != "Rain_first"
    )
    summary = []
    for d in dirs:
        song = read_song(d)
        song["violations"] = violations(song)
        (d / "readout.json").write_text(json.dumps(song, ensure_ascii=False, indent=1), "utf-8")
        summary.append(song)
        print(
            f"\n=== {song['song']} · 송신 {song['n_lines']}줄 · "
            f"설계 큐 {song['n_design_cues']} · 송신 큐 {song['n_sent_cues']} · "
            f"승인=송신 {song['approved_equals_sent']}"
        )
        print(
            "큐 | 이름 | D | 설계 팔레트 | 송신 RGB | 설계 포지션 | 송신 프리셋 | "
            "설계 디머 key/back | 선택 묶음 | 그룹 줄 | 무대 층 | 효과 요청/허용/페이저"
        )
        for c in song["cues"]:
            print(
                f"{c['cue']} | {c['name']} | {c['d']} | {'/'.join(c['design_palette'])} | "
                f"{[tuple(int(v) for v in r) for r in c['sent_rgb_in_cue']]} | "
                f"{c['design_position']} | "
                f"{c['sent_presets']} | {c['design_key_pct']}/{c['design_back_pct']} | "
                f"{c['sent_selection_sets']}{c['sent_selection_sizes']} | "
                f"{c['sent_group_lines']} | "
                f"{c['stage_rig_layers']} | {len(c['design_fx_requested'])}/"
                f"{len(c['design_fx_permitted'])}/{c['design_phaser_hint']}"
            )
        for clause, text in song["violations"]:
            print(f"  위반 {clause}: {text}")
    (HERE / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), "utf-8")


if __name__ == "__main__":
    main(sys.argv[1:])
