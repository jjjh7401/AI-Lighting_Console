"""t538 — 무빙 움직임 원인 가르기 + 위치 프리셋 큐 무빙 (SPEC-LDBEAT-001 M1 후속).

카드 t538 본문이 정본이다. 알려진 성공 t516 A2(`.moai/reports/t516/approval_rhythm_probe_v4.txt:18-27`,
감독 「움직임」)를 A0 로 그대로 다시 만들고, A1~A5 는 A0 에서 **한 가지씩만** 바꾼다.
A6 은 쇼에 이미 있는 효과 프리셋(21.2·21.5)을 불러 보는 두 번째 양성 대조다.
B 는 위치 프리셋으로 큐를 엮어 무빙을 내는 길이다.

번호: 시퀀스 311~321(전부 새 번호). 2026-10-10 읽기(r0_reads.txt)에서 300~310 위로는
1999·2000 뿐이다. 실행 직전 main_cli 가 빈 번호를 다시 읽는다.

장비·조건(리드 원칙 2026-10-10 — 결론에는 이 조건을 붙여 적는다):
- 대상: MOVER-U 501~508(MegaPointe, 디머 1개, 기본값 0 — t516 verdict.md:226).
- Group 11 구성원 = 501~508 정확히(r3_group11.txt + t525 패치 트리 대응, r3_group11_fid.txt).
- 박자 112 BPM 기준(1박 0.54초, 2박 1.07초) — A0 의 `At Speed 112` 와 맞춘다.

쇼 저장 0줄. 기존 객체는 읽기만 한다(Store 는 311~321 에만).
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t531")
from m1_common import main_cli, seq_path  # noqa: E402

from server.spatial.mib import (  # noqa: E402
    PositionCuePlan,
    apply_mib,
    position_cue_bundle,
    premove_follow_command,
)
from server.spatial.pointing import position_cue_store_commands  # noqa: E402

FIDS = (501, 502, 503, 504, 505, 506, 507, 508)
FIX = "Fixture " + " + ".join(str(f) for f in FIDS)
GROUP = "Group 11"
BEAT = 0.54  # 112 BPM 1박(초)
TWO_BEATS = 1.07

SEQ = dict(
    A0=311, A1=312, A2=313, A3=314, A4=315, A5=316,
    A6a=317, A6b=318, B1=319, B2=320, B3=321,
)


def _name(item: str, text: str) -> str:
    # 점(.)은 MA3 가 이름에서 지운다(SKILL §3b) — 이름엔 점을 넣지 않는다.
    return f"'T538 - {item} {text}'"


def _store(item: str, text: str) -> list[str]:
    no = SEQ[item]
    return [
        f"Store Sequence {no} Cue 1 {_name(item, text)}",
        "ClearAll",
        f"Set Sequence {no} Property 'Name' {_name(item, text)}",
    ]


def _a0_body(
    *,
    sel: str = FIX,
    base: str | None = "Attribute 'Tilt' At 45",
    size: int = 30,
) -> list[str]:
    """t516 A2 의 몸통(v4:20-24). 인자 하나만 바꿔 A1~A4 를 만든다."""
    lines = ["ChangeDestination Root", "ClearAll", f"{sel} ; Attribute 'Dimmer' At 70"]
    if base is not None:
        lines.append(f"{sel} ; {base}")
    lines += [
        f"{sel} ; Attribute 'Tilt' At Relative {size}",
        "Attribute 'Tilt' At Phase 0 Thru 360",
        "Attribute 'Tilt' At Speed 112",
    ]
    return lines


def _play(item: str) -> list[tuple[str, list[str]]]:
    no = SEQ[item]
    return [(f"play_{item}", [f"Goto Cue 1 Sequence {no}"]), (f"off_{item}", [f"Off Sequence {no}"])]


# ---------------------------------------------------------------- A 페이저


def plan_a() -> list[tuple[str, list[str]]]:
    plan: list[tuple[str, list[str]]] = []
    items = [
        ("A0", "A2 replay", _a0_body()),
        ("A1", "group 11", _a0_body(sel=GROUP)),
        ("A2", "relative 12", _a0_body(size=12)),
        ("A3", "base preset 2-1", _a0_body(base="At Preset 2.1")),
        ("A4", "no base", _a0_body(base=None)),
        (
            "A5",
            "pan tilt circle",
            [
                "ChangeDestination Root",
                "ClearAll",
                f"{FIX} ; Attribute 'Dimmer' At 70",
                f"{FIX} ; Attribute 'Tilt' At 45",
                f"{FIX} ; Attribute 'Pan' At Relative 30",
                f"{FIX} ; Attribute 'Tilt' At Relative 30",
                "Attribute 'Pan' At Phase 0",
                "Attribute 'Tilt' At Phase 90",
                "Attribute 'Pan' At Speed 112",
                "Attribute 'Tilt' At Speed 112",
            ],
        ),
        (
            "A6a",
            "fx preset 21-2 PT-CIRCLE",
            ["ChangeDestination Root", "ClearAll", f"{GROUP} ; Attribute 'Dimmer' At 70", "At Preset 21.2"],
        ),
        (
            "A6b",
            "fx preset 21-5 TILT-SWEEP",
            ["ChangeDestination Root", "ClearAll", f"{GROUP} ; Attribute 'Dimmer' At 70", "At Preset 21.5"],
        ),
    ]
    for item, text, body in items:
        plan.append((f"store_{item}", [*body, *_store(item, text)]))
        plan += _play(item)
    return plan


# ---------------------------------------------------------------- B 위치 프리셋 큐

#: 큐 차례(위치 프리셋 번호, CueFade 초). 2.1 은 ⑤⑨ 의 기준 프리셋 — 이것이 501~508 을
#: 움직이기는 하는지도 B1 큐 1 에서 함께 보인다(2.1 크기 1568B 가 풀에서 가장 작다, r6).
B_CUES = ((1, None), (4, BEAT), (5, TWO_BEATS), (3, BEAT))
B_NAMES = ("POS01", "POS04", "POS05", "POS03")


def _b_cue_lines(no: int) -> list[str]:
    lines = ["ChangeDestination Root", "ClearAll"]
    for k, ((preset, fade), label) in enumerate(zip(B_CUES, B_NAMES, strict=True), start=1):
        if k == 1:
            lines.append(f"{GROUP} ; Attribute 'Dimmer' At 70")  # 트래킹으로 2~4 큐에도 남는다
        lines.append(f"{GROUP} ; At Preset 2.{preset}")
        lines += list(position_cue_store_commands(no, k, fade_seconds=fade, name=f"T538 {label}"))
        lines.append("ClearAll")
    return lines


def plan_b() -> list[tuple[str, list[str]]]:
    plan: list[tuple[str, list[str]]] = []

    # B1 — 큐 4개, Goto 로 하나씩. 감독: 다음 자리로 「쓸고 가는지」(페이드 1박·2박).
    no = SEQ["B1"]
    plan.append(
        (
            "store_B1",
            [*_b_cue_lines(no), f"Set Sequence {no} Property 'Name' {_name('B1', 'position cues')}"],
        )
    )
    for k in range(1, 5):
        plan.append((f"play_B1_c{k}", [f"Goto Cue {k} Sequence {no}"]))
    plan.append(("off_B1", [f"Off Sequence {no}"]))

    # B2 — B1 과 같은 큐 + 큐마다 TrigType Follow(검증된 꼴, 31_choreography_patterns.md:111).
    # 되감기는 새 시퀀스 기본값 WRAPAROUND true(r5_seq_props.txt, 310·308)에 기댄다 — 이것으로
    # 큐 4 다음 큐 1 의 Follow 가 다시 도는지는 안 잰 것이다(이 항목이 그것을 잰다).
    # 큐 1 페이드 0 은 되감길 때 순간 이동이 되므로 B2 는 큐 1 도 2박으로 둔다.
    no = SEQ["B2"]
    body = ["ChangeDestination Root", "ClearAll"]
    for k, ((preset, fade), label) in enumerate(zip(B_CUES, B_NAMES, strict=True), start=1):
        if k == 1:
            body.append(f"{GROUP} ; Attribute 'Dimmer' At 70")
            fade = TWO_BEATS
        body.append(f"{GROUP} ; At Preset 2.{preset}")
        body += list(position_cue_store_commands(no, k, fade_seconds=fade, name=f"T538 {label}"))
        body.append("ClearAll")
    body += [f"Set Cue {k} Sequence {no} Property 'TrigType' 'Follow'" for k in range(1, 5)]
    body.append(f"Set Sequence {no} Property 'Name' {_name('B2', 'follow loop')}")
    plan.append(("store_B2", body))
    plan += _play("B2")

    # B3 — MIB, 앱 함수(apply_mib → position_cue_bundle → premove_follow_command)가 낸 줄 그대로.
    # 큐 1 POS02 켜짐 → 큐 2 암전 → 큐 3 POS05 켜짐. 2.5 미리 이동이 끼워진다.
    no = SEQ["B3"]
    cues = apply_mib(
        (
            PositionCuePlan(cue_no=1, name="T538 POS02 lit", preset_no=2, dimmer=70.0),
            PositionCuePlan(cue_no=2, name="T538 dark", dimmer=0.0, fade_seconds=BEAT),
            PositionCuePlan(cue_no=3, name="T538 POS05 reveal", preset_no=5, dimmer=70.0, fade_seconds=BEAT),
        )
    )
    body = ["ChangeDestination Root", "ClearAll"]
    for cue in cues:
        body += list(position_cue_bundle(no, cue, FIDS))
        if cue.premove:
            body.append(premove_follow_command(no, cue))
    body.append(f"Set Sequence {no} Property 'Name' {_name('B3', 'MIB')}")
    plan.append(("store_B3", body))
    # 🔴 `Go+ Sequence <n>` 은 이 저장소 송신 기록에 없는 꼴이다(룰북은 `Go+ Executor`).
    # 실행기 배정(쓰기)을 피하려고 쓴다 — 거절되면 그 자체가 결과다.
    plan.append(("play_B3_c1", [f"Goto Cue 1 Sequence {no}"]))
    plan.append(("play_B3_go_dark", [f"Go+ Sequence {no}"]))
    plan.append(("play_B3_go_reveal", [f"Go+ Sequence {no}"]))
    plan.append(("off_B3", [f"Off Sequence {no}"]))
    return plan


def build_plan() -> list[tuple[str, list[str]]]:
    return [*plan_a(), *plan_b()]


if __name__ == "__main__":
    sys.exit(
        main_cli(
            item="T538",
            risk_reason="t538 — 시퀀스 311~321(새), 무빙 원인 가르기 A0~A6 + 위치 큐 B1~B3",
            build_plan=build_plan,
            free_slots=[seq_path(n) for n in SEQ.values()],
            extra_notes=[
                "A0 = t516 A2(v4:18-27) 문면, 시퀀스 번호·이름만 다름. A0 이 안 움직이면 나머지 중단.",
                "Group 11 = 501~508(r3_group11_fid.txt).",
                "21.2/21.5 안의 값·대상 장비는 응답기로 못 읽음(childCount 0, r1). A6 이 안 움직이면 "
                "「프리셋에 501~508 값이 없음」과 「불러도 안 돎」을 가르지 못한다.",
                "B2 되감기·B3 Go+ Sequence 는 미측정 꼴.",
            ],
        )
    )
