# ruff: noqa: E501 — 근거(판독값·인용)를 그대로 싣는 한국어 머리말이라 줄 길이 규칙을 끈다
"""t520 SPEC-LDRHYTHM-001 M2 묶음 1 — LOVE ATTACK 0~25마디 손 시연 명령(쓰기 판).

대본: .moai/specs/SPEC-LDRHYTHM-001/m1-love-attack-script.md §3 의 0:00.0~0:55.1 행.
수단: t516 판정서 맨 위 요약표에서 실기로 확인된 것만 쓴다.
  - 반복 동작 = 2단계 페이저 + `At Measure <박>` + `At SpeedMaster 15`(t516 v3 L2·v4 B3/B4, 마스터 15 = 112.35, 표시 112)
  - 움직임 = 절대값 2단계 페이저, 단계마다 Pan·Tilt 를 같이 넣는다(t516 v5 E1 246 — 기울인 기준 위 Pan 흔들림 확인)
  - 장면 경계·강조 = 타임코드 이벤트 Go+(t506 v3 · t516 v1 트랙 둘). 트랙 1 = 장면 250, 트랙 2 = 리듬 251
  - 다중 디머 기구는 서브픽스처까지 적는다(Aura XB `201 + 201.1`, Spiider `521 + 521.1 + 521.2 + 521.3` — run0_readonly.txt)
  - 선택+값은 한 줄 모양 `Fixture 목록 ; Attribute …`(t516 §4-4 line_shapes)
층 소유(같은 속성을 두 시퀀스가 함께 잡지 않게 — 겹침 우선순위는 안 잰 것):
  - 장면 250: WASH 디머·색 · FOH 디머 · BACK/SIDE/무빙 색 · BACK 위치(Pan 180 · Tilt 80, 모든 큐) · 무빙 디머 · BLIND 디머
  - 리듬 251: BACK 디머 · SIDE 디머 · 무빙 Pan/Tilt — 매 큐가 이 속성 전부를 두 단계로 다시 적는다(트래킹으로 앞 큐 페이저가 남지 않게)
번호: 시퀀스 250·251, 타임코드 22(run0_readonly.txt — 모두 `path segment not found`). 이름 'LOVE ATTACK - RHYTHM M2a <역할>'.
타임코드 시각 = 음악 시각 + LEAD(3초). 음원 재생은 m2a_play.py 가 맡는다.

실행: uv run python .moai/reports/t520/m2a_batch1.py <출력폴더> [--rehearse | --approve <전부-거절 폴더>]
🔴 --approve 는 리드의 「실행」 메시지 뒤에만.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t506")
import tc_probe  # noqa: E402
from tc_probe import LISTEN_PORT, Probe, RecordingApproval  # noqa: E402

from server.safety.audit import AuditLog  # noqa: E402
from server.safety.console import ExecOutcome, LinkTimeouts, StateQueryError  # noqa: E402
from server.safety.gate import BatchRisk, SafetyGate  # noqa: E402
from server.safety.ruleset import load_ruleset  # noqa: E402

tc_probe.RISK = BatchRisk(
    reason="t520 M2 묶음 1 — 빈 번호 250·251·TC22 생성(LOVE ATTACK 0~25마디)", kind="t520_m2a"
)

LEAD = 3.0  # 타임코드 0초 → 음악 0초 사이 여유
DURATION = 62  # 3 + 55.08(26마디 1박) + 여유
SM = "SpeedMaster 15"
EXPECT_MASTER_NORMED = "69"  # t516 v1 이 112.35 로 바꾼 뒤 값 — 다르면 누가 BPM 을 바꾼 것
POOL = "ShowData/DataPools/Default"

#: 번호·이름·줄 꼴 — configure() 로 바꾼다. 기본값은 v2(250·251·TC22, 점 번호를 목록에 섞음).
#: 쓰기 1회(live_write)에서 점 번호가 든 24·40개 목록 줄이 `Illegal object` 로 거절됐다 — 프로브 A 결과로 B 의 꼴을 고른다.
#:   SUB_MODE "mixed"      : 본체와 점 번호를 한 목록에(v2 — 실기에서 거절됨)
#:            "main_only"  : 점 번호를 뺀다(본체 선택만으로 서브픽스처 디머까지 열릴 때)
#:            "split_list" : 본체 목록 한 줄 + 점 번호 목록 한 줄(점 번호 목록이 받아들여질 때)
#:            "split_each" : 본체 목록 한 줄 + 점 번호 하나씩 한 줄(`Fixture 201.1 ;` — t516 에서 확인된 꼴)
#:   MAX_LIST : 목록 하나의 최대 개수(None = 제한 없음). 목록 길이가 원인이면 20(실기 성공 최대)으로 둔다.
S_SCENE, S_RHY, TC_NO = 250, 251, 22
TAG = "M2a"
SUB_MODE = "mixed"
BARE_AT_GROUPS: set[str] = set()  # 맨 `At` 으로 디머를 줄 그룹(--target b2)
DIM2_OPEN: list = []  # 장면 큐1 에 더할 Spiider Dimmer2 open 줄(--target b2)
MAX_LIST: int | None = None
TC = f"{POOL}/Timecodes/{TC_NO}"
SEQ = {n: f"{POOL}/Sequences/{n}" for n in (S_SCENE, S_RHY)}


def configure(
    scene: int, rhythm: int, tc: int, tag: str, sub_mode: str, max_list: int | None
) -> None:
    global S_SCENE, S_RHY, TC_NO, TAG, SUB_MODE, MAX_LIST, TC, SEQ
    if sub_mode not in ("mixed", "main_only", "split_list", "split_each", "group"):
        raise ValueError(sub_mode)
    S_SCENE, S_RHY, TC_NO, TAG, SUB_MODE, MAX_LIST = scene, rhythm, tc, tag, sub_mode, max_list
    TC = f"{POOL}/Timecodes/{TC_NO}"
    SEQ = {n: f"{POOL}/Sequences/{n}" for n in (S_SCENE, S_RHY)}
    tc_probe.RISK = BatchRisk(
        reason=f"t520 M2 묶음 1 — 빈 번호 {S_SCENE}·{S_RHY}·TC{TC_NO} 생성(LOVE ATTACK 0~25마디)",
        kind="t520_m2a",
    )


def add_target_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--target",
        choices=("v2", "b", "b2"),
        default="v2",
        help="v2 = 250·251·TC22, b = 253·254·TC23",
    )
    parser.add_argument(
        "--sub-mode",
        choices=("mixed", "main_only", "split_list", "split_each", "group"),
        default=None,
    )
    parser.add_argument("--max-list", type=int, default=None)


def apply_target(args: argparse.Namespace) -> None:
    if args.target == "b":
        if args.sub_mode in (None, "mixed"):
            raise SystemExit(
                "--target b 는 --sub-mode group|main_only|split_list|split_each 를 정해야 한다"
            )
        configure(253, 254, 23, "M2a B", args.sub_mode, args.max_list)
    elif args.target == "b2":
        # B v2(리드 지시): 그룹 선택 + Spiider 든 그룹(12·13)의 디머만 맨 `At`, 새 번호 269·270·TC24
        global BARE_AT_GROUPS
        configure(269, 270, 24, "M2a B2", "group", None)
        BARE_AT_GROUPS = {"Group 12", "Group 13"}
        # Spiider 두 번째 디머 — 감독 손 시험(원문) 「딤머2를 켜야되네」. 유형 판독(dim2_readonly.txt): 논리 채널
        # `Dimmer2`(PRETTY 「Dim2」, FeatureGroup 1.1), 채널 세트 closed = DMX 0 · No Feature 1~254 · open = 255.
        # 맨 `At 60` 은 Dimmer2 도 60%(No Feature 구간)로 둘 수 있어, 큐1 에 open(100%)을 Spiider(그룹 12)에만 따로 준다.
        DIM2_OPEN.append(val(MOV_D, "Attribute 'Dimmer2' At 100"))
    elif args.sub_mode not in (None, "mixed") or args.max_list:
        raise SystemExit("--target v2 는 기록용 — 줄 꼴을 바꾸지 않는다")


def name(role: str) -> str:
    return f"'LOVE ATTACK - RHYTHM {TAG} {role}'"


# ---------------------------------------------------------------- 리그(diag7_patch_table.txt · run0_readonly.txt)


def with_subs(ids: range, subs: int) -> list[str]:
    return [x for i in ids for x in [str(i), *(f"{i}.{k}" for k in range(1, subs + 1))]]


BACK = with_subs(range(201, 213), 1)  # Aura XB — 서브픽스처 1(디머 둘)
BACK_MAIN = [str(i) for i in range(201, 213)]
SIDE_L = with_subs(range(301, 307), 1)
SIDE_R = with_subs(range(311, 317), 1)
WASH = [str(i) for i in [*range(401, 411), *range(421, 431)]]  # Rush Par 2 — 서브픽스처 없음
FOH = [str(i) for i in range(111, 119)]  # 디머 하나
BLIND = [str(i) for i in range(601, 607)]  # 디머 하나
MOV_U = [str(i) for i in range(501, 509)]  # MegaPointe — 서브픽스처 없음
MOV_D = with_subs(range(521, 529), 3)  # Spiider — 서브픽스처 3(디머 셋)
MOV_ALL = MOV_U + MOV_D


def selections(ids: list[str]) -> list[list[str]]:
    """SUB_MODE·MAX_LIST 대로 선택 목록을 나눈다."""
    mains = [i for i in ids if "." not in i]
    subs = [i for i in ids if "." in i]
    if SUB_MODE == "mixed" or not subs:
        groups = [ids]
    elif SUB_MODE == "main_only":
        groups = [mains]
    elif SUB_MODE == "split_list":
        groups = [mains, subs]
    else:
        groups = [mains, *([s] for s in subs)]
    if MAX_LIST:
        groups = [g[k : k + MAX_LIST] for g in groups for k in range(0, len(g), MAX_LIST)]
    return groups


#: 색 — 이름만 대본에서, 값은 자리표시(감독 지시 2026-09-28: 색 미세 조정은 전체를 마친 뒤)
COLORS = {
    "cold": (85, 92, 100),
    "lavender": (72, 60, 100),
    "pink": (100, 62, 80),
    "peach": (100, 75, 55),
}


def rgb(color: str) -> str:
    r, g, b = COLORS[color]
    return f"Attribute 'ColorRGB_R' At {r} ; Attribute 'ColorRGB_G' At {g} ; Attribute 'ColorRGB_B' At {b}"


class V(NamedTuple):
    """선택 + 값. 줄로 바꾸는 것은 render() 때 — configure() 뒤의 SUB_MODE·MAX_LIST 를 따른다."""

    ids: list[str]
    parts: tuple[str, ...]


def val(ids: list[str], *parts: str) -> V:
    return V(ids, parts)


#: SUB_MODE "group" — 기존 그룹 번호(t498 run0 그룹 이름 · 감독이 그룹 4 = 뒤쪽 12대 확인, t516 §4-5).
#: 프로브 G2: `Group 5 ; Dimmer 100` 과 `Fixture 301 Thru 302. ; Dimmer 100` 둘 다 서브픽스처 디머까지 열었다(감독 「둘 다 켜졌어」).
#: 열쇠는 본체 번호 집합이다. 그룹 구성원은 응답기로 못 읽으므로 그룹 이름과 패치 표가 근거다.
GROUP_OF = {
    frozenset(str(i) for i in range(111, 119)): 3,  # FOH
    frozenset(str(i) for i in range(201, 213)): 4,  # BACK
    frozenset(str(i) for i in range(301, 307)): 5,  # SIDE-L
    frozenset(str(i) for i in range(311, 317)): 6,  # SIDE-R
    frozenset(str(i) for i in [*range(301, 307), *range(311, 317)]): 7,  # SIDE-ALL
    frozenset(str(i) for i in [*range(401, 411), *range(421, 431)]): 10,  # WASH-ALL
    frozenset(str(i) for i in range(501, 509)): 11,  # MOVER-U
    frozenset(str(i) for i in range(521, 529)): 12,  # MOVER-D
    frozenset(str(i) for i in [*range(501, 509), *range(521, 529)]): 13,  # MOVER-ALL
    frozenset(str(i) for i in range(601, 607)): 14,  # BLIND
}


def group_selection(ids: list[str]) -> str:
    """기존 그룹이 맞으면 `Group N`, 아니면 이어진 범위 `Fixture a Thru b.`(뒤 점 — 본체 + 서브픽스처 전부)."""
    mains = [int(i) for i in ids if "." not in i]
    key = frozenset(str(i) for i in mains)
    if key in GROUP_OF:
        return f"Group {GROUP_OF[key]}"
    if mains == list(range(mains[0], mains[-1] + 1)):
        return f"Fixture {mains[0]} Thru {mains[-1]}."
    raise ValueError(
        f"그룹도 이어진 범위도 아닌 선택: {ids}"
    )  # 목록 안 뒤 점은 안 잰 꼴이라 만들지 않는다


def render(v: V, after: tuple[str, ...] = ()) -> list[str]:
    """나뉜 선택마다 `Fixture 목록 ; Attribute …` 한 줄, 그 뒤에 after(페이저 타이밍 — 지금 선택에 붙는다)."""
    out: list[str] = []
    if SUB_MODE == "group":
        sel = group_selection(v.ids)
        parts = v.parts
        if sel in BARE_AT_GROUPS:
            # Spiider 가 든 그룹은 맨 `At` — t459 verdict.md:62-63(감독 확인): `Attribute 'Dimmer' At 100` 은 안 켜지고 `At 100` 은 켠다
            parts = tuple(
                p.replace("Attribute 'Dimmer' At ", "At ", 1)
                if p.startswith("Attribute 'Dimmer' At ")
                else p
                for p in parts
            )
        return [" ; ".join([sel, *parts]), *after]
    ids = v.ids
    position_only = all(p.startswith(("Attribute 'Pan'", "Attribute 'Tilt'")) for p in v.parts)
    if SUB_MODE != "mixed" and position_only:
        # 위치는 본체에만 — t519 `Fixture 201 ; Pan/Tilt` 로 BACK 이 실제로 돌았다(Spiider 는 안 잰 것)
        ids = [i for i in ids if "." not in i]
    for g in selections(ids):
        out += [" ; ".join(["Fixture " + " + ".join(g), *v.parts]), *after]
    return out


#: 역광 방향 — 감독 결정 2026-10-07 「80도 정도는 되어야겠어」(t519 시험 Seq 260~262, 객석 = −Y).
#: 줄 꼴은 t519 approval_back_aim.txt 와 같다: 위치는 본체(201)에만, 서브픽스처 없이.
BACK_AIM = val(BACK_MAIN, "Attribute 'Pan' At 180", "Attribute 'Tilt' At 80")


def dim(v: float) -> str:
    return f"Attribute 'Dimmer' At {v:g}"


# ---------------------------------------------------------------- 장면 시퀀스 250 (대본 색/위치 한 단계·강조)

#: (큐, 이름, CueFade 초, 음악 시각 초, 대본 행, 값 줄)
SCENE: list[tuple[int, str, float, float, str, list[str]]] = [
    (
        1,
        "Intro A",
        0,
        0.00,
        "0:00.0 시작 장면",
        [
            val(WASH, dim(0), rgb("lavender")),
            val(FOH, dim(0)),
            val(BACK, rgb("cold")),
            val(SIDE_L + SIDE_R, rgb("lavender")),
            val(MOV_ALL, dim(60), rgb("cold")),
            val(BLIND, dim(0)),
        ],
    ),
    (
        2,
        "Verse One",
        4.27,
        14.36,
        "0:14.4 벌스 1 장면(2마디 번짐)",
        [
            val(WASH, dim(40)),
            val(FOH, dim(60)),
            val(BACK, rgb("lavender")),
        ],
    ),
    (3, "Pre One", 0.53, 29.35, "0:29.4 프리코러스 덜어냄", [val(WASH, dim(25))]),
    (4, "Pre Gap", 0, 36.86, "0:36.9 17마디 3박 비움", [val(WASH, dim(10))]),
    (
        5,
        "Chorus One Hit",
        0,
        37.90,
        "0:37.9 강조 BLIND 60 + WASH 핑크 70",
        [
            val(BLIND, dim(60)),
            val(WASH, dim(70), rgb("pink")),
        ],
    ),
    (6, "Blind Off", 0.27, 38.43, "0:37.9 강조 — 1박 뒤 반 박 안에 끔", [val(BLIND, dim(0))]),
    (7, "Peach Bleed", 2.14, 46.51, "0:46.5 핑크 → 피치(1마디 번짐)", [val(WASH, rgb("peach"))]),
]

# ---------------------------------------------------------------- 리듬 시퀀스 251 (펄스·체이스·움직임)

FULL = {
    "back": (30, 30, "1"),  # (단계1, 단계2, Measure)
    "side_l": (0, 0, "4"),
    "side_r": (0, 0, "4"),
    "mov_u": (0, 0, 15, 15, "0", "2"),  # (Pan1, Pan2, Tilt1, Tilt2, Phase, Measure)
    "mov_d": (0, 0, 15, 15, "0", "2"),
}

TILT_WAVE = (0, 0, 33, 57, "0 Thru 360", "8")  # 45 ± 12, 한 바퀴 8박


def sweep(measure: str) -> tuple:
    return (-12, 12, 45, 45, "0", measure)  # 모두 같이 좌우 왕복


#: (큐, 이름, 음악 시각 초, 대본 행, 바뀌는 상태)
RHYTHM: list[tuple[int, str, float, str, dict]] = [
    (1, "Intro Back", 0.00, "0:00.0 BACK 30 실루엣 · 무빙 바닥 쪽 고정", {}),
    (2, "Start Hit", 0.96, "0:00.0 시작 히트 BACK 한 번(앞박 0.96초)", {"back": (100, 100, "1")}),
    (3, "Intro Hold", 1.50, "시작 히트 끝 — BACK 30 으로", {"back": (30, 30, "1")}),
    (4, "Kick Four", 5.78, "0:05.8 3~6마디 4박 펄스(BACK)", {"back": (30, 60, "4")}),
    (
        5,
        "Movers Mid",
        10.07,
        "0:10.1 5마디 무빙 중간 높이로",
        {"mov_u": (0, 0, 45, 45, "0", "2"), "mov_d": (0, 0, 45, 45, "0", "2")},
    ),
    (6, "Verse Pulse", 14.36, "0:14.4 7~10마디 1·2·4박 펄스 60", {"back": (30, 60, "1")}),
    (
        7,
        "Tilt Wave",
        16.50,
        "0:16.5 8~13마디 틸트 웨이브 8박",
        {"mov_u": TILT_WAVE, "mov_d": TILT_WAVE},
    ),
    (
        8,
        "Side Chase",
        22.93,
        "0:22.9 11~13마디 SIDE 2·4박 번갈아 · 펄스 멈춤",
        {"back": (30, 30, "1"), "side_l": (0, 100, "4"), "side_r": (100, 0, "4")},
    ),
    (
        9,
        "Sweep Four",
        29.35,
        "0:29.4 14마디 가속 스윕 4박 · 체이스·웨이브 멈춤",
        {"side_l": (0, 0, "4"), "side_r": (0, 0, "4"), "mov_u": sweep("4"), "mov_d": sweep("4")},
    ),
    (10, "Sweep Two", 31.51, "15마디 스윕 2박", {"mov_u": sweep("2"), "mov_d": sweep("2")}),
    (11, "Sweep One", 33.65, "16마디 스윕 1박", {"mov_u": sweep("1"), "mov_d": sweep("1")}),
    (
        12,
        "Sweep Half",
        35.79,
        "17마디 1·2박 스윕 반 박",
        {"mov_u": sweep("0.5"), "mov_d": sweep("0.5")},
    ),
    (
        13,
        "Pre Gap",
        36.86,
        "0:36.9 17마디 3박 — 모두 멈춤, 무빙 위쪽 한 점",
        {"mov_u": (0, 0, 60, 60, "0", "2"), "mov_d": (0, 0, 60, 60, "0", "2")},
    ),
    (
        14,
        "Chorus Pulse",
        37.90,
        "0:37.9 18~25마디 BACK 펄스 100 · MOVER-U 위로 연다",
        {"back": (30, 100, "1"), "mov_u": (0, 0, 75, 75, "0", "2")},
    ),
    (
        15,
        "Pan Wave",
        40.08,
        "0:40.1 19~25마디 MOVER-U 팬 웨이브 2박",
        {"mov_u": (-12, 12, 75, 75, "0 Thru 360", "2")},
    ),
]


def rhythm_states() -> list[tuple[int, str, float, str, dict]]:
    """큐마다 앞 상태에 바뀐 것을 얹어 전체 상태를 만든다."""
    state = dict(FULL)
    out = []
    for cue, label, t, row, change in RHYTHM:
        state = {**state, **change}
        out.append((cue, label, t, row, dict(state)))
    return out


def timing(attr: str, phase: str, measure: str) -> list[str]:
    return [
        f"Attribute '{attr}' At Phase {phase}",
        f"Attribute '{attr}' At Measure {measure}",
        f"Attribute '{attr}' At {SM}",
    ]


def rhythm_cue_lines(state: dict) -> list[str]:
    """한 큐 = 소유 속성 전부를 두 단계로(단계 1 → `Step 2` → 단계 2 + 타이밍)."""
    dims = [("back", BACK), ("side_l", SIDE_L), ("side_r", SIDE_R)]
    movs = [("mov_u", MOV_U), ("mov_d", MOV_D)]
    lines: list[str] = []
    for k, ids in dims:
        lines += render(val(ids, dim(state[k][0])))
    for k, ids in movs:
        p1, _, t1, _, _, _ = state[k]
        lines += render(val(ids, f"Attribute 'Pan' At {p1}", f"Attribute 'Tilt' At {t1}"))
    lines.append("Step 2")
    for k, ids in dims:
        _, hi, measure = state[k]
        lines += render(val(ids, dim(hi)), tuple(timing("Dimmer", "0", measure)))
    for k, ids in movs:
        _, p2, _, t2, phase, measure = state[k]
        after = tuple(timing("Pan", phase, measure) + timing("Tilt", phase, measure))
        lines += render(val(ids, f"Attribute 'Pan' At {p2}", f"Attribute 'Tilt' At {t2}"), after)
    return lines


# ---------------------------------------------------------------- 묶음


def tc_time(t: float) -> str:
    return f"{LEAD + t:.2f}".rstrip("0").rstrip(".")


def build(tracks: tuple[int, int] = (1, 2)) -> list[tuple[str, list[str]]]:
    n_scene, n_rhy = tracks
    scene = ["ChangeDestination Root", "ClearAll"]
    for cue, label, fade, _, _, lines in SCENE:
        scene += [
            *(
                line
                for v in [*lines, *(DIM2_OPEN if cue == 1 else []), BACK_AIM]
                for line in render(v)
            ),
            f"Store Sequence {S_SCENE} Cue {cue} '{label}' CueFade {fade:g}",
            "ClearAll",
        ]
    scene.append(f"Set Sequence {S_SCENE} Property 'Name' {name('SCENE')}")
    rhy = ["ChangeDestination Root", "ClearAll"]
    for cue, label, _, _, state in rhythm_states():
        rhy += [
            *rhythm_cue_lines(state),
            f"Store Sequence {S_RHY} Cue {cue} '{label}' CueFade 0",
            "ClearAll",
        ]
    rhy.append(f"Set Sequence {S_RHY} Property 'Name' {name('RHYTHM')}")
    events = []
    for no, times in ((n_scene, [s[3] for s in SCENE]), (n_rhy, [r[2] for r in RHYTHM])):
        events.append(f"cd Timecode {TC_NO}.1.{no}.1.1")
        events += [
            f"Store Property 'Time' {tc_time(t)} 'AbsTime' {tc_time(t)} 'Token' 'Go+'"
            for t in times
        ]
        events.append("cd root")
    return [
        ("seq_scene", scene),
        ("seq_rhythm", rhy),
        (
            "tc_a",
            [
                f"Store Timecode {TC_NO}",
                f"Set Timecode {TC_NO} Property 'Name' {name('TC')}",
                f"Set Timecode {TC_NO} Property 'Duration' {DURATION} 'AutoStop' 0",
                f"Store Timecode {TC_NO}.1",
                f"Assign Sequence {S_SCENE} At Timecode {TC_NO}.1.1",
                f"Assign Sequence {S_RHY} At Timecode {TC_NO}.1.2",
            ],
        ),
        ("tc_b", [f"Store Type 'CmdSubTrack' Timecode {TC_NO}.1.{n}.1" for n in (n_scene, n_rhy)]),
        ("tc_c", events),
    ]


# ---------------------------------------------------------------- 가짜 콘솔(리허설 전용 — t516 v1 모형을 번호만 바꿈)


class FakeConsole:
    """번호 존재·타임코드 트랙 NO·이벤트 수만 흉내 낸다. 페이저·재생 의미론의 증거가 아니다."""

    responder_version = "fake"

    def __init__(self) -> None:
        self.sent: list[str] = []
        self.exists: set[str] = set()
        self.tracks: list[int] = []
        self.subs: set[int] = set()
        self.events: dict[int, int] = {}
        self.cwd = "root"

    def ping(self) -> bool:
        return True

    def execute(self, command: str) -> ExecOutcome:
        self.sent.append(command)
        if '"' in command:
            return ExecOutcome(status="failed", detail="fake: double quote rejected")
        words = command.split()
        if command.startswith("Store Sequence"):
            self.exists.add(SEQ[int(words[2])])
        elif command == f"Store Timecode {TC_NO}":
            self.exists.add(TC)
        elif command.startswith("Assign Sequence"):
            self.tracks.append(int(words[2]))
        elif command.startswith("Store Type 'CmdSubTrack'"):
            self.subs.add(int(words[-1].split(".")[2]))
        elif command.startswith("cd "):
            self.cwd = words[1] if words[1] == "root" else words[2]
        elif command.startswith("Store Property 'Time'"):
            no = int(self.cwd.split(".")[2])
            self.events[no] = self.events.get(no, 0) + 1
        return ExecOutcome(status="ok", detail="OK")

    def query_state(self, path: str, offset: int = 0) -> dict:
        if (path in SEQ.values() or path.startswith(TC)) and not any(
            path.startswith(p) for p in self.exists
        ):
            raise StateQueryError(f"path segment not found (in {path})")
        kids: list[tuple[str, int]] = []
        if path == f"{TC}/1":
            kids = [("MarkerTrack", 1)] + [("Track", i + 2) for i in range(len(self.tracks))]
        elif path.startswith(f"{TC}/1/") and path.count("/") == 6:
            kids = [("TimeRange", 1)]
        elif path.startswith(f"{TC}/1/") and path.count("/") == 7:
            no = int(path.split("/")[6]) - 1
            kids = [("CmdSubTrack", 1)] if no in self.subs else []
        elif path.startswith(f"{TC}/1/") and path.count("/") == 8:
            no = int(path.split("/")[6]) - 1
            kids = [("CmdEvent", i + 1) for i in range(self.events.get(no, 0))]
        children = [{"class": c, "i": i, "name": c} for c, i in kids]
        return dict(
            ok=True, path=path, node=dict(childCount=len(children)), children=children, fake=True
        )

    def query_properties(self, path: str, names) -> dict:
        reads = []
        for n in names:
            if path.startswith(f"{TC}/1/") and path.count("/") == 6:
                idx = int(path.split("/")[6]) - 2
                v = {"NO": str(idx + 1), "TARGET": f"Sequence {self.tracks[idx]}"}.get(n, "fake")
            elif n == "NORMEDVALUE":
                v = EXPECT_MASTER_NORMED
            else:
                v = "fake"
            reads.append(dict(n=n, ok=True, v=v))
        return dict(ok=True, path=path, reads=reads, fake=True)

    def query_property(self, path: str, name: str) -> dict:
        return self.query_properties(path, [name])

    def enumerate_fields(self, path: str, offset: int = 0) -> dict:
        return dict(ok=True, path=path, fields=[], fake=True)


# ---------------------------------------------------------------- 진행


def _value(payload: dict | None, key: str):
    for read in (payload or {}).get("reads") or ():
        if read.get("n") == key and read.get("ok"):
            return read.get("v")
    return None


def _children(payload: dict | None) -> list[dict]:
    return [c for c in (payload or {}).get("children") or () if isinstance(c, dict)]


def run(gate: SafetyGate, out: Path, *, deny_all: bool) -> dict:
    probe = Probe(gate, out)
    result: dict = dict(slots=[S_SCENE, S_RHY, TC_NO], bundles={})

    def stop(reason: str) -> dict:
        result["verdict"] = reason
        with (out / "steps.jsonl").open("w", encoding="utf-8") as handle:
            for row in probe.log:
                handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        return result

    # 사전 판독 — 쓰는 번호가 모두 비었는지, 스피드 마스터 15 가 t516 이 둔 값 그대로인지
    taken = [p for p in [*SEQ.values(), TC] if probe.read_state("pre_slot", p) is not None]
    master = _value(
        probe.read_props("pre_master", "ShowData/Masters/3/15", ["NAME", "NORMEDVALUE"]),
        "NORMEDVALUE",
    )
    result["pre_master_normed"] = master
    if taken:
        return stop(f"stopped: slots not empty {taken}")
    if master != EXPECT_MASTER_NORMED:
        return stop(f"stopped: Masters/3/15 NORMEDVALUE {master} != {EXPECT_MASTER_NORMED}")
    plan = build()
    if deny_all:
        for label, cmds in plan:
            result["bundles"][label] = probe.fire(label, cmds)
        return stop("deny-all: approval texts recorded, nothing written")

    def fire(label: str, cmds: list[str]) -> bool:
        result["bundles"][label] = ok = probe.fire(label, cmds)
        return ok

    by = dict(plan)
    for label in ("seq_scene", "seq_rhythm"):
        if not fire(label, by[label]):
            return stop(f"{label} not executed")
    for n, p in SEQ.items():
        props = probe.read_props(f"post_seq_{n}", p, ["NAME"])
        kids = _children(probe.read_state(f"post_seq_{n}_cues", p))
        result.setdefault("post_seq", {})[n] = dict(
            name=_value(props, "NAME"), cues=sum(1 for k in kids if k.get("class") == "Cue")
        )
    if not fire("tc_a", by["tc_a"]):
        return stop("tc_a not executed")
    tracks = []
    for child in _children(probe.read_state("post_a_group", f"{TC}/1")):
        if child.get("class") == "Track":
            props = probe.read_props("post_a_track", f"{TC}/1/{child['i']}", ["NO", "TARGET"])
            tracks.append(
                dict(i=child["i"], no=_value(props, "NO"), target=_value(props, "TARGET"))
            )
    result["tracks"] = tracks
    want = {f"Sequence {S_SCENE}", f"Sequence {S_RHY}"}
    if {t["target"] for t in tracks} != want or len(tracks) != 2:
        return stop(f"stopped after tc_a: tracks {tracks}")
    by_target = {t["target"]: t for t in tracks}
    nos = tuple(int(float(by_target[f"Sequence {s}"]["no"])) for s in (S_SCENE, S_RHY))
    live = dict(build(nos))  # 트랙 NO 가 1·2 가 아니면 문면이 승인과 달라져 게이트가 거절한다
    if not fire("tc_b", live["tc_b"]):
        return stop("tc_b not executed")
    subs = {}
    for s in (S_SCENE, S_RHY):
        kids = _children(
            probe.read_state(f"post_b_{s}", f"{TC}/1/{by_target[f'Sequence {s}']['i']}/1")
        )
        subs[s] = [k.get("class") for k in kids]
    result["post_b"] = subs
    if any(v != ["CmdSubTrack"] for v in subs.values()):
        return stop(f"stopped before cd: {subs}")
    fire("tc_c", live["tc_c"])
    want_events = {S_SCENE: len(SCENE), S_RHY: len(RHYTHM)}
    for s in (S_SCENE, S_RHY):
        path = f"{TC}/1/{by_target[f'Sequence {s}']['i']}/1/1"
        result.setdefault("events", {})[s] = len(_children(probe.read_state(f"post_c_{s}", path)))
    probe.read_props("post_tc", TC, ["NAME", "DURATION"])
    ok = result["events"] == want_events
    return stop(
        "written — events match" if ok else f"written — events {result['events']} != {want_events}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--rehearse", action="store_true")
    parser.add_argument("--approve", default=None)
    parser.add_argument("--print-plan", action="store_true", help="콘솔 없이 묶음 문면만 출력")
    add_target_args(parser)
    args = parser.parse_args()
    apply_target(args)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.print_plan:
        (out / "plan.json").write_text(json.dumps(build(), ensure_ascii=False, indent=1), "utf-8")
        return 0
    skipped: list[str] = []
    if args.rehearse:
        from server.safety.backup import BackupManager

        console = FakeConsole()
        approval = RecordingApproval([cmds for _, cmds in build()])
        gate = SafetyGate(
            console=console,
            audit=AuditLog(out / "audit"),
            ruleset=load_ruleset(),
            approval_port=approval,
            backup=BackupManager(
                backup_action=lambda: skipped.append("SaveShow skipped (rehearsal)")
            ),
        )
        result = run(gate, out, deny_all=False)
        result["fake_sent"] = len(console.sent)
    else:
        from server.safety.bootstrap import build_console_stack
        from server.tools.probe_preflight import preflight

        pinned = None
        if args.approve:
            requests = json.loads((Path(args.approve) / "approvals.json").read_text("utf-8"))
            pinned = [r["commands"] for r in requests]
        approval = RecordingApproval(pinned)
        stack = build_console_stack(
            send_host="127.0.0.1",
            send_port=8000,
            receive_host="127.0.0.1",
            receive_port=LISTEN_PORT,
            approval_port=approval,
            audit_dir=out / "audit",
            timeouts=LinkTimeouts(state_query_seconds=6.0),
            attempt_session_backup=False,
        )
        stack.backup._backup_action = lambda: skipped.append("SaveShow skipped (supervisor)")
        try:
            health = preflight(
                stack.gate, receive_host="127.0.0.1", receive_port=LISTEN_PORT, console_port=8000
            )
            if health.get("verdict") != "responder_ok":
                print(json.dumps(dict(preflight=health), ensure_ascii=False, indent=2))
                return 1
            result = run(stack.gate, out, deny_all=pinned is None)
            result["preflight"] = health.get("verdict")
        finally:
            stack.stop()
    result["approval_requests"] = len(approval.requests)
    result["approved"] = sum(1 for r in approval.requests if r["approved"])
    result["skipped_saveshow"] = skipped
    (out / "approvals.json").write_text(
        json.dumps(approval.requests, ensure_ascii=False, indent=2), "utf-8"
    )
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
    print(
        json.dumps(
            {
                k: result.get(k)
                for k in ("verdict", "bundles", "tracks", "events", "post_seq", "approved")
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
