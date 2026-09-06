"""번들 위험 선언의 **문면**을 나갈 명령에서 읽는다 (카드 t319).

왜 따로 있는가. `_song_finalize` 의 `_song_write_risk_reason` 은 시퀀스·큐·
타임코드 셋만 읽는 곡 전용 문면이다. 봉합해야 할 나머지 자리는 프리셋 풀·
매크로 풀·패치 좌표·익스큐터 배정처럼 **다른 것**을 쓴다. 자리마다 문장을
손으로 쓰면 계획과 번들이 갈릴 때 카드가 사실과 다른 것을 말하게 되므로,
`_song_write_risk_reason` 이 세운 규율을 그대로 잇는다: **숫자와 대상은
나갈 명령 자체에서 읽는다**.

새 심사 통로가 아니다. 여기서 만드는 것은 `BatchRisk` 하나이고, 그것은
기존 `gate.screen(...)` 한 곳으로만 간다(게이트의 `@MX:ANCHOR`).

**왜 `server/safety/` 가 아니라 여기 있는가.** 이 모듈은 심사하지 않는다 —
호출자가 자기 번들을 설명하는 **문면**을 만들 뿐이고, 판단은 전부 게이트가
한다. `server/safety/` 에 두면 안전 초크포인트의 일부처럼 읽히고, 그
디렉터리는 `test_overlap_preserve.py` 의 파일 집합 핀이 지키는 자리다.
핀을 넓히는 대신 모듈을 옳은 자리로 옮겼다 — 카드 t317 이 세운 규율
(가드를 약화시키지 말고 우회하라)을 그대로 따른다.

`showfile_write_risk` 가 `None` 을 답하는 경우가 이 모듈의 요점이다.
아래 표에 없는 명령만 있는 번들 — 예컨대 프로그래머 값만 찍는
`Fixture 20 ; Attribute 'Pan' At 12` — 은 쇼파일을 안 고친다. 안 고치는
번들에 「쇼파일 쓰기」 카드를 띄우면 감독은 곧 카드를 안 읽게 되고,
그게 진짜 쓰기를 통과시킨다. 그래서 없으면 **없다고 답한다**.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from server.safety.gate import BatchRisk

#: 쇼파일 오브젝트를 만들거나 덮는 줄만 센다. `Label …` 은 바로 앞 `Store …` 에
#: 딸린 이름표라 따로 세지 않는다 — 세면 「N건」이 두 배로 부풀어 거짓이 된다.
_STORE_PRESET = re.compile(r"\bStore Preset (\d+)\.(\d+)")
_STORE_SEQUENCE_CUE = re.compile(r"\bStore Sequence (\d+) Cue (\d+(?:\.\d+)?)")
_STORE_TIMECODE = re.compile(r"\bStore Timecode (\d+)")
_STORE_MACRO = re.compile(r"\bStore Macro (\d+)")
_SET_FIXTURE_POS = re.compile(r"\bSet Fixture (\d+) Pos[xyz]\b")
_ASSIGN_EXECUTOR = re.compile(r"\bAssign Sequence (\d+) At Executor (\S+)")
_COPY_SEQUENCE = re.compile(r"\bCopy Sequence (\d+) At (\d+)")
#: 덮어쓰기 플래그. 있으면 「이미 든 것 위에 쓴다」를 문면에 싣는다.
_MERGE_OR_OVERWRITE = re.compile(r"/(?:Merge|Overwrite)\b", re.IGNORECASE)


def describe_showfile_write(
    commands: Sequence[str], *, restore_commands: Sequence[str] = ()
) -> str | None:
    """이 번들이 쇼파일에 무엇을 하는지 — 없으면 ``None``.

    반환 문면은 감독이 읽고 수락/거절을 정하는 문장이다(REQ-BULKGATE-007):
    **무엇을** 쓰는지, **몇 건**인지, 되돌릴 수 있는지.

    되돌리기 문장은 **주장이 아니라 관찰**이다. `_song_write_risk_reason` 은
    「이 앱에는 시퀀스·타임코드 복원 경로가 없습니다」를 문면에 박아 두는데,
    그 문장은 그 자리에서만 참이다 — `arrange_fixtures` 는 원좌표를 읽어
    복원 번들을 함께 만든다. 그래서 여기서는 앱 전체에 대해 단정하지 않고,
    **호출자가 실제로 들고 있는 복원 명령**을 받아 그것만 말한다. 안 주면
    「이 번들에는 되돌리기 명령이 없습니다」 — 이것은 번들에 대한 사실이다.
    """
    lines = [str(line) for line in commands]
    joined = "\n".join(lines)
    parts: list[str] = []

    presets = {f"{m.group(1)}.{m.group(2)}" for m in _STORE_PRESET.finditer(joined)}
    if presets:
        pools = sorted({slot.split(".")[0] for slot in presets})
        pool_text = ", ".join(f"{pool}번 풀" for pool in pools)
        parts.append(f"프리셋 {len(presets)}건({pool_text})을 저장")

    cues: dict[str, set[str]] = {}
    for match in _STORE_SEQUENCE_CUE.finditer(joined):
        cues.setdefault(match.group(1), set()).add(match.group(2))
    if cues:
        cue_text = ", ".join(
            f"Sequence {seq} 에 큐 {len(numbers)}건" for seq, numbers in sorted(cues.items())
        )
        parts.append(f"{cue_text}을 저장")

    slots = sorted({m.group(1) for m in _STORE_TIMECODE.finditer(joined)})
    if slots:
        parts.append("Timecode " + ", ".join(slots) + " 슬롯을 사용")

    macros = sorted({m.group(1) for m in _STORE_MACRO.finditer(joined)})
    if macros:
        parts.append("Macro " + ", ".join(macros) + " 슬롯에 매크로를 저장")

    fixtures = {m.group(1) for m in _SET_FIXTURE_POS.finditer(joined)}
    if fixtures:
        parts.append(f"패치의 3D 좌표를 장비 {len(fixtures)}대에 기록")

    executors = sorted({f"{m.group(2)}" for m in _ASSIGN_EXECUTOR.finditer(joined)})
    if executors:
        parts.append("Executor " + ", ".join(executors) + " 에 시퀀스를 배정")

    copies = sorted({f"{m.group(1)}→{m.group(2)}" for m in _COPY_SEQUENCE.finditer(joined)})
    if copies:
        parts.append("시퀀스를 " + ", ".join(copies) + " 로 복제")

    if not parts:
        return None

    overwrite = " 이미 든 내용 위에 덮어씁니다." if _MERGE_OR_OVERWRITE.search(joined) else ""
    restore = (
        f" 원상 복구 명령 {len(restore_commands)}건이 함께 준비되어 있습니다."
        if restore_commands
        else " 이 번들에는 되돌리기 명령이 없습니다."
    )
    return f"쇼파일 쓰기 — {', '.join(parts)}합니다.{overwrite}{restore}"


def showfile_write_risk(
    commands: Sequence[str], *, kind: str, restore_commands: Sequence[str] = ()
) -> BatchRisk | None:
    """쇼파일을 고치는 번들이면 선언을, 아니면 ``None``.

    ``kind`` 는 감사 로그에서 어느 통로의 판단이었는지 가르는 태그다
    (`BatchRisk` 의 어휘를 그대로 쓴다). 자리마다 서로 다른 값을 준다 —
    로그에서 자리를 되짚을 수 있어야 하기 때문이다.
    """
    reason = describe_showfile_write(commands, restore_commands=restore_commands)
    if reason is None:
        return None
    return BatchRisk(reason=reason, kind=kind)
