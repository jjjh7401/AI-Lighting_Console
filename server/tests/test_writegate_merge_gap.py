"""t292 — `Store Sequence <N> Cue <M> /Merge` 는 승인 카드를 안 띄운다 (실측 고정).

t291 실측에서 초안 반영이 명령 5건을 보냈고 감사 로그는 전부 `ok`, `blocked 0`
이었다. 그 5건 안에 쇼파일 쓰기인 `Store Sequence 210 Cue 1 /Merge` 가 있었는데
승인 카드는 뜨지 않았다.

이 파일은 **고치는 파일이 아니라 못을 박는 파일**이다. 고칠 자리는
`server/safety/blacklist.yaml` 인데 그 디렉터리는 이 카드가 손대면 안 되는
곳이라, 여기서는 현재 동작을 있는 그대로 고정하고 어디가 갈라지는지를 남긴다.

가장 날카로운 사실: **같은 명령이 옵션 하나로 갈린다.**
`/Overwrite` 는 `Store /overwrite` 항목에 걸려 카드가 뜨고, `/Merge` 는 안 뜬다.
둘 다 같은 시퀀스의 같은 큐를 쓰는데도 그렇다.
"""

from __future__ import annotations

import pytest

from server.safety.classify import classify_command
from server.safety.grammar import validate
from server.safety.ruleset import load_ruleset

RULESET = load_ruleset()


def _classify(command: str):
    grammar = validate(command)
    assert grammar.ok, f"고정용 문장이 문법을 못 넘는다: {command!r} — {grammar.reason}"
    return classify_command(grammar.parsed, RULESET)


#: 오늘 `safe` 로 분류되는 쇼파일 쓰기들 — 승인 카드가 뜨지 않는다.
#: `Store Cue 12` / `Store Group 3` 은 `test_writegate.py::UNCHANGED_SAFE` 가
#: 비용 근거로 이미 비준한 항목이라 여기 다시 적지 않는다. 여기 적는 것은
#: 그 표에 없던 `Store Sequence` 계열이다.
UNCARDED_SEQUENCE_WRITES = (
    "Store Sequence 210 Cue 1 /Merge",
    "Store Sequence 210 Cue 1",
    "Store Sequence 210",
)


@pytest.mark.parametrize("command", UNCARDED_SEQUENCE_WRITES)
def test_a_sequence_cue_write_raises_no_approval_card_today(command: str) -> None:
    verdict = _classify(command)
    assert verdict.category == "safe"
    assert verdict.risky is False
    assert verdict.matched_entry is None


def test_the_same_write_with_overwrite_does_raise_a_card() -> None:
    """축은 `/Merge` 가 아니라 **블랙리스트가 든 옵션**이다.

    `Store /overwrite` 항목이 `/Overwrite` 를 잡는다. `/Merge` 를 잡을 항목은
    이 파일에 없다 — 즉 결함은 `/Merge` 전용 구멍이 아니라 `Store` 의
    오브젝트 커버리지(`Sequence` 가 항목에 없다)다.
    """
    merged = _classify("Store Sequence 210 Cue 1 /Merge")
    overwritten = _classify("Store Sequence 210 Cue 1 /Overwrite")
    assert merged.risky is False
    assert overwritten.risky is True
    assert overwritten.matched_entry == "Store /overwrite"


def test_the_gate_itself_is_healthy_on_the_same_bundle() -> None:
    """「게이트가 죽었다」가 아니라 「이 오브젝트가 목록에 없다」임을 고정한다."""
    assert _classify("Set Fixture 11 Posx '5.0'").matched_entry == "Set Fixture"
    assert _classify("Store Preset 4.1").matched_entry == "Store Preset"
    assert _classify("Delete Sequence 210").matched_entry == "Delete"


def test_the_blacklist_carries_no_entry_that_could_match_a_sequence_store() -> None:
    """최소 수정 자리를 기록한다: `Store Sequence` 라는 항목이 없다.

    이 단언이 깨지는 날은 누군가 그 항목을 넣은 날이고, 그때 이 파일 전체가
    붉어져서 「고정해 둔 구멍이 닫혔다」를 알린다.
    """
    assert "Store Sequence" not in RULESET.blacklist
    store_entries = [entry for entry in RULESET.blacklist if entry.split()[0] == "Store"]
    assert store_entries == ["Store /overwrite", "Store Preset"]
