"""t299 Phase 3 — 항목 순서가 귀속을 바꾸는가. 추론이 아니라 실측.

배차서는 「이 확대가 같은 번들에 **두 번째** 일치 항목을 더한다」고 적었다.
항목 수준에서는 맞다 — `Store Cue` 의 키워드 둘(`Store`·`Cue`)이
`Store Sequence 210 Cue 10 /Merge` 의 토큰에 전부 있으므로 이 항목만 든 룰셋에서도
그 줄은 걸린다. 그러나 `classify.py::_match_blacklist` 는 목록을 순회하며 **첫**
일치에서 즉시 돌아오므로, 배치된 순서(`Store Sequence` 가 앞)에서는 두 번째 사유가
카드에 실리지 않는다.

그 둘은 다른 주장이고, 둘 다 재야 확정된다. 이 프로브는 세 가지 룰셋으로 같은 줄을
분류한다:

  ① 배치된 순서 (`Store Sequence` … `Store Cue`)  -> 기대: 'Store Sequence'
  ② `Store Cue` 만 든 룰셋                        -> 기대: 'Store Cue' (항목이 닿는다)
  ③ `Store Cue` 를 앞으로 뒤집은 순서             -> 기대: 'Store Cue' (귀속이 바뀐다)

②·③ 은 임시 파일에 쓴 **합성 룰셋**으로만 잰다. 배치된 `server/safety/blacklist.yaml`
은 건드리지 않는다.

실행:  uv run python reports/classifygap-t299-p3/probe_entry_order.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import server
from server.safety.classify import classify_command
from server.safety.grammar import validate
from server.safety.ruleset import DEFAULT_RULESET_PATH, load_ruleset

#: 큐시트 반영 번들이 실제로 내보내는 줄. 이 줄의 귀속이 이 프로브의 관측 대상이다.
LINE = "Store Sequence 210 Cue 10 /Merge"

#: 모델 통로의 짧은 형태. 대조용 — 어느 룰셋에서도 `Store Cue` 로 걸려야 한다.
SHORT = "Store Cue 1"


def _synthetic(entries: list[str], version: int) -> Path:
    """항목 순서만 바꾼 합성 룰셋을 임시 파일로 쓴다."""
    tmp = Path(tempfile.mkdtemp(prefix="t299p3-order-")) / "blacklist.yaml"
    lines = [
        "# 합성 룰셋 — probe_entry_order.py 전용. 배치본이 아니다.",
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
    print(f"interpreter : {sys.version.split()[0]}")
    print(f"server pkg  : {server.__file__}")
    print(f"ruleset path: {DEFAULT_RULESET_PATH}")
    print(f"ruleset ver : {shipped.version}")
    print(f"blacklist   : {list(shipped.blacklist)}\n")

    print("① 배치된 순서 — `Store Sequence` 가 `Store Cue` 앞에 있다")
    order = list(shipped.blacklist)
    print(f"   Store Sequence index = {order.index('Store Sequence')}")
    print(f"   Store Cue      index = {order.index('Store Cue')}")
    print(f"   {LINE!r:36} -> matched_entry={_matched(LINE, shipped)!r}")
    print(f"   {SHORT!r:36} -> matched_entry={_matched(SHORT, shipped)!r}")

    print("\n② `Store Cue` **만** 든 합성 룰셋 — 이 항목이 그 줄에 닿는가")
    only_cue = load_ruleset(_synthetic(["Store Cue"], 2))
    print(f"   blacklist = {list(only_cue.blacklist)}")
    print(f"   {LINE!r:36} -> matched_entry={_matched(LINE, only_cue)!r}")

    print("\n③ 순서를 뒤집은 합성 룰셋 — `Store Cue` 를 `Store Sequence` 앞으로")
    flipped = load_ruleset(_synthetic(["Store Cue", "Store Sequence"], 2))
    print(f"   blacklist = {list(flipped.blacklist)}")
    print(f"   {LINE!r:36} -> matched_entry={_matched(LINE, flipped)!r}")

    print("\n[검산] 세 관측이 말하는 것")
    a = _matched(LINE, shipped)
    b = _matched(LINE, only_cue)
    c = _matched(LINE, flipped)
    print(f"   항목이 그 줄에 닿는다            : {b == 'Store Cue'}  (② = {b!r})")
    print(f"   배치 순서에서 귀속은 안 바뀐다   : {a == 'Store Sequence'}  (① = {a!r})")
    print(f"   앞으로 옮기면 귀속이 바뀐다      : {c == 'Store Cue'}  (③ = {c!r})")
    print(
        "   => 「두 번째 사유가 카드에 실린다」는 이 배치에서 **성립하지 않는다**. "
        "첫 일치에서 돌아오기 때문이고, 그것이 순서를 못 박는 이유다."
    )


if __name__ == "__main__":
    main()
