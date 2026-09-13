"""t377·t378 확증 — 실기 콘솔이 없는 자리에서 감독이 본 리그와 같은 모양으로 대체 확인.

카드 배차서: "the diagnosis needs the live console for the rig read, so
substitute a static groups section of the same shape if none is available."

`reports/onsite-round-20260912/diag.py` 는 grandMA3 실기(포트 9005)와 실제 곡
오디오 파일(`src/걸그룹DinoDino_C_max최고품질.wav`)이 필요하다 — 이 워크트리에는
둘 다 없다(라이브 콘솔 접속 불가, 오디오 파일 미동기화). 그래서 감독이 그날 관측한
**같은 리그 모양**(18그룹, `reports/onsite-round-20260912/realsong-cue-diagnosis.txt`
"리그 그룹 18개")과 **같은 구간 순서**(NAMES 목록)를 그대로 재현하고, 다이내믹스만
그 결과가 실제로 낸 룩 종류(edm-haze-shafts=1 · edm-intro-bed=2 · edm-drop-crimson=5)
에 맞춰 명시로 지정한다. 오디오 분석을 대체하는 것이지 리그나 구조를 지어내는 것이
아니다.
"""

from server.looks.loader import load_library_from_dir
from server.looks.songcue import build_songcue_bundle, map_sections_to_looks, parse_sections
from server.tests.test_looks_instantiate import _groups

NAMES = [
    "Intro",
    "Verse",
    "Verse",
    "Chorus",
    "Chorus",
    "Bridge",
    "Bridge",
    "Chorus",
    "Verse",
    "Chorus",
    "Verse",
    "Chorus",
    "Breakdown",
    "Chorus",
    "Bridge",
    "Chorus",
]
#: 실측 다이어그노시스가 낸 룩 종류 그대로 — Intro/Bridge/Breakdown=1,
#: Verse=2, Chorus=5(realsong-cue-diagnosis.txt "룩 종류" 절).
_DYNAMICS = {"Intro": 1, "Verse": 2, "Chorus": 5, "Bridge": 1, "Breakdown": 1}

#: realsong-cue-diagnosis.txt "리그 그룹 18개" 그대로 — 번호는 감독 실기 순서를
#: 몰라 선언 순서(1부터)로 매긴다. 이 스크립트가 재는 것은 **어느 그룹이 값을
#: 받는가**(이름 기준)이지 그룹 번호 자체가 아니므로, 번호 배정 순서는 결론에
#: 영향을 주지 않는다.
GROUP_NAMES = [
    "KEY",
    "FOH",
    "BACK",
    "SIDE-L",
    "SIDE-R",
    "SIDE-ALL",
    "MOVER-U",
    "MOVER-D",
    "MOVER-ALL",
    "WASH-U",
    "WASH-D",
    "WASH-ALL",
    "BLIND",
    "STROBE",
    "HAZE",
    "ALL",
    "ODD",
    "EVEN",
]


def _groups_section() -> dict:
    return _groups(*((index + 1, name) for index, name in enumerate(GROUP_NAMES)))


def _sequences_section() -> dict:
    return {"objects": [{"no": 1, "name": "Sequence 1"}], "truncated": False, "total": 1}


raw = [{"name": name, "start": index * 8.0} for index, name in enumerate(NAMES)]
sections = parse_sections(raw)
explicit_dynamics = {section.index: _DYNAMICS[section.label] for section in sections}

lib = load_library_from_dir()
selections = map_sections_to_looks(sections, lib, "edm", explicit_dynamics)
bundle = build_songcue_bundle(
    "Diag-static",
    selections,
    sequences_section=_sequences_section(),
    groups_section=_groups_section(),
)

gnames = {index + 1: name for index, name in enumerate(GROUP_NAMES)}

print("== 큐마다: 어느 그룹에 무슨 값이 갔나 (프론트 필·찍는 액센트 포함) ==")
used_groups: set[int] = set()
for s in bundle.stored_sections:
    parts: list[str] = []
    commands = s.commands
    i = 0
    while i < len(commands):
        if commands[i].startswith("Group "):
            gline = commands[i]
            gs = [int(x) for x in gline.replace("Group ", "").split(" + ") if x.strip().isdigit()]
            used_groups |= set(gs)
            names = [gnames.get(g, f"?{g}") for g in gs]
            attrs = [a.split("'")[1] for a in commands[i + 1].split(";") if "'" in a]
            parts.append(f"{'+'.join(names)}:{','.join(attrs)}")
            i += 2
        else:
            i += 1
    front = "front_fill" if s.front_fill is not None else "-"
    accent = s.accent_fixture.rung if s.accent_fixture is not None else "-"
    print(
        f"  cue {s.cue_number:>2} {s.section.label:10} {s.selection.look.look_id:22} "
        f"{' / '.join(parts)}  [front={front} accent={accent}]"
    )

print(f"\n== 리그 그룹 {len(gnames)}개 중 큐가 건드린 그룹 ==")
touched = sorted(used_groups)
print("  건드림:", [gnames.get(g) for g in touched])
print("  한 번도 안 건드림:", [n for g, n in sorted(gnames.items()) if g not in touched])

print("\n== 프론트 필 ==")
print(f"  채운 큐 수: {len(bundle.front_filled_sections)} / {len(bundle.stored_sections)}")

print("\n== 찍는 액센트(블라인더·스트로브) ==")
print(f"  켠 큐 수: {len(bundle.accent_fixture_sections)}")
for s in bundle.accent_fixture_sections:
    print(
        f"  cue {s.cue_number} {s.section.label} instance={s.section.instance} → {s.accent_fixture}"
    )

print("\n== 건너뜀 ==")
print(" ", bundle.skipped or "0건")
