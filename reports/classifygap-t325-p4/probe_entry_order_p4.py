"""t325 Phase 4 — 항목 순서가 귀속을 바꾸는가. 추론이 아니라 실측.

Phase 3 은 순서가 **의미를 가졌다**. `Store Cue` 와 `Store Sequence` 는 동사가
같고 키워드 집합이 겹쳐서, `_match_blacklist` 가 첫 일치에서 돌아오는 성질 때문에
목록 앞뒤가 카드 사유를 바꿨다. 그래서 항목을 목록 끝에 두는 것이 조건이 됐다.

이 회차는 **그 선례를 가정하지 않는다**. `Assign Sequence` · `Copy Sequence` 의
동사는 `Assign` · `Copy` 이고, 기존 항목 열넷의 동사 키워드는 그 둘과 겹치지
않는다 — 그렇다면 순서는 귀속에 무관해야 한다. 「무관해야 한다」는 예상이므로
세 갈래로 잰다:

  ① 배치된 순서 (새 항목이 목록 **끝**)     -> 기존 여섯 줄의 귀속
  ② 새 항목을 목록 **앞**으로 뒤집은 순서   -> 귀속이 바뀌는가
  ③ 동사 키워드 교차 검사                   -> 왜 안 바뀌는가 (기전)

②·③ 은 임시 파일에 쓴 **합성 룰셋**으로만 잰다. 배치된
`server/safety/blacklist.yaml` 은 건드리지 않는다.

실행:  uv run python reports/classifygap-t325-p4/probe_entry_order_p4.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import server
from server.safety.classify import _keyword_match, classify_command
from server.safety.grammar import validate
from server.safety.ruleset import DEFAULT_RULESET_PATH, load_ruleset

#: Phase 4 가 넣는 둘.
NEW_ENTRIES = ("Assign Sequence", "Copy Sequence")

#: 귀속이 움직이면 안 되는 줄들. Phase 1~3 이 닫은 넷 + 이 회차의 둘.
WATCHED = (
    "Store Group 3",
    "Store Timecode 9",
    "Store Sequence 210 Cue 10 /Merge",
    "Store Cue 1",
    "Assign Sequence 201 At Executor 101",
    "Copy Sequence 300 At 210",
)


def _synthetic(entries: list[str], version: int) -> Path:
    """항목 순서만 바꾼 합성 룰셋을 임시 파일로 쓴다."""
    tmp = Path(tempfile.mkdtemp(prefix="t325p4-order-")) / "blacklist.yaml"
    lines = [
        "# 합성 룰셋 — probe_entry_order_p4.py 전용. 배치본이 아니다.",
        "# REVISION HISTORY",
        "#   v1 -> v2  SPEC-COPILOT-CLASSIFYGAP-001 합성 픽스처",
        f"version: {version}",
        "blacklist:",
    ]
    lines += [f'  - "{entry}"' for entry in entries]
    lines += [
        "invoking_verbs:",
        "  verbs:",
        '    - "Go"',
        "  bare_object_forms:",
        '    - "Macro <n>"',
    ]
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tmp


def _matched(line: str, ruleset) -> str | None:
    result = validate(line)
    assert result.ok, f"프로브 줄이 파싱돼야 한다: {line!r} ({result.reason})"
    return classify_command(result.parsed, ruleset).matched_entry


def main() -> None:
    shipped = load_ruleset()
    order = list(shipped.blacklist)
    print(f"interpreter : {sys.version.split()[0]}")
    print(f"server pkg  : {server.__file__}")
    print(f"ruleset path: {DEFAULT_RULESET_PATH}")
    print(f"ruleset ver : {shipped.version}")
    print(f"blacklist   : {order}\n")

    print("① 배치된 순서 — 새 항목이 목록 끝에 있다")
    for entry in NEW_ENTRIES:
        where = order.index(entry) if entry in order else "(없음)"
        print(f"   {entry!r:18} index = {where}")
    shipped_attr = {}
    for line in WATCHED:
        shipped_attr[line] = _matched(line, shipped)
        print(f"   {line!r:40} -> matched_entry={shipped_attr[line]!r}")

    print("\n② 새 항목을 목록 **앞**으로 뒤집은 합성 룰셋")
    flipped_entries = [*NEW_ENTRIES, *[e for e in order if e not in NEW_ENTRIES]]
    flipped = load_ruleset(_synthetic(flipped_entries, 2))
    print(f"   blacklist = {list(flipped.blacklist)}")
    moved = []
    for line in WATCHED:
        after = _matched(line, flipped)
        same = after == shipped_attr[line]
        if not same:
            moved.append((line, shipped_attr[line], after))
        print(f"   {line!r:40} -> {after!r}   {'같음' if same else '<<< 바뀌었다'}")
    print(f"   => 귀속이 움직인 줄: {len(moved)} {moved}")

    print("\n③ 동사 키워드 교차 검사 — 왜 순서가 무관한가 (기전)")
    others = [e for e in order if e not in NEW_ENTRIES]
    clashes = []
    for new in NEW_ENTRIES:
        new_verb = new.split()[0]
        for other in others:
            other_verb = other.split()[0]
            # `_match_blacklist` 는 parsed.verb 를 parts[0] 에 대고 잰다.
            # 두 방향 다 본다: 남의 동사로 온 명령이 새 항목에 닿는가, 그 반대도.
            if _keyword_match(new_verb, other_verb) or _keyword_match(other_verb, new_verb):
                clashes.append((new, other))
    for new in NEW_ENTRIES:
        print(f"   {new.split()[0]!r:10} vs 기존 동사 {sorted({e.split()[0] for e in others})}")
    print(f"   => 동사가 겹치는 조합: {len(clashes)} {clashes}")

    print("\n[검산] 세 관측이 말하는 것")
    print(
        f"   새 두 항목이 대상 줄을 잡는다     : "
        f"{all(shipped_attr[c] in NEW_ENTRIES for c in WATCHED[4:])}"
    )
    print(f"   순서를 뒤집어도 귀속은 안 바뀐다  : {len(moved) == 0}")
    print(f"   기전 — 동사 교차 0                : {len(clashes) == 0}")
    print(
        "   => Phase 3 과 **조건이 다르다**. 거기서는 순서가 귀속의 조건이었지만, "
        "이 회차는 동사가 겹치지 않아 순서가 무관하다. 그 무관함이 조건이므로 "
        "`test_the_new_verb_entries_are_order_independent` 가 검사로 지킨다."
    )


if __name__ == "__main__":
    main()
