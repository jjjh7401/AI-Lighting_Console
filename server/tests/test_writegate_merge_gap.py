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

---

## 종결 기록 (SPEC-COPILOT-BULKGATE-001)

**전.** 위 문단들이 「이 노출은 열려 있고 고칠 자리는 `blacklist.yaml` 이다」라고
적었다. 그것이 이 파일이 처음 쓰였을 때의 판단이다.

**후.** 노출은 닫혔는데, **`blacklist.yaml` 이 아닌 디스패치 층**에서 닫혔다.
`SafetyGate.screen` 이 키워드 전용 `risk: BatchRisk | None` 을 얻어, 호출자가
자기 묶음을 「쇼파일 쓰기」로 선언하면 명령 하나하나의 분류와 무관하게 번들
전체가 보류가 되고 카드 한 장이 뜬다. 곡→콘솔 경로(`prepare_songcue`)가 그
선언을 붙였고, 초안 반영은 그 전에 t292 가 `_accept_draft_apply_batch` 로
닫았다.

**분류는 의도적으로 안 움직였다.** `Store Sequence` 를 `blacklist.yaml` 에
넣으면 이 통로뿐 아니라 **룩 생성 4 · FX 2 · 씬 컴파일 1 · 룰셋 핀 1 = 부수
피해 8건**이 붉어진다(t292 실측). 그것은 픽스처 변경이 아니라 제품 동작
변경이다 — 감독이 룩 하나 만들 때마다 승인 카드가 뜬다. 같은 축의 `Store`
동사 확대는 2026-08-05 사용자 결정과 카드 t86 에서 이미 두 번 거절됐다.

**그래서 아래 단언들은 바이트 그대로다.** 특히
`assert "Store Sequence" not in RULESET.blacklist` 는 이 SPEC 이 **지키는**
성질이지 고칠 대상이 아니다. 단언은 불변이고 문면만 갱신하는 이 조합은
**의도적**이다 — 안 적으면 다음 사람이 「구멍이 아직 열려 있다」로 읽는다.

**아직 열려 있는 것.** 선언을 붙인 자리는 곡→콘솔 하나뿐이다. 나머지 쓰기
디스패치 자리들은 `server/tests/test_write_dispatch_census.py` 의
`WRITE_WITHOUT_SEAM_DISPATCHES` 에 이름과 사유로 등재돼 있고, 각자 후속 카드를
갖는다. 그 표가 「분류했다」고 말할 뿐 「안전하다」고는 말하지 않는다.

---

## 못을 반쯤 뽑은 기록 (SPEC-COPILOT-CLASSIFYGAP-001 Phase 1, 카드 t299)

위 종결 기록이 「아래 단언들은 바이트 그대로다」라고 적었다. **그 문장은 이제
절반만 참이다** — 조용히 뒤집으면 다음 사람이 사고로 읽으므로 여기 적는다.

**무엇이 움직였나.** 블랙리스트 v4 -> v5 가 `Store Group` 과 `Store Timecode`
둘을 넣었다. 위 종결 기록이 「분류는 의도적으로 안 움직였다」고 적은 근거는
t292 의 부수피해 8건이었는데, 이 트리에서 다시 재니 그 8은 `Store Sequence`
단독 확대의 낡은 값이었고 같은 항목이 33건이 됐다(분모가 움직였다). t299 는
비용이 작고 위험 신호가 없는 두 항목만 먼저 넣었다 — 실측 14건 / 전체 12029,
전부 폐집합 핀과 「안전한 예」 리터럴이다.

**무엇이 안 움직였나.** `Store Sequence` 와 `Store Cue` 는 **여전히 폐집합에
없다.** 그래서 아래 `UNCARDED_SEQUENCE_WRITES` 세 줄과
`test_the_same_write_with_overwrite_does_raise_a_card` 의 비대칭은 **바이트
그대로 유효한 관측**이다 — 고쳐서 통과시킨 것이 아니라 아직 안 닫힌 구멍을
계속 고정하고 있는 것이다. 그 둘은 각자 후속 카드(Phase 2·3)를 갖는다.

**그래서 이 파일이 초록인 것은 「구멍이 닫혔다」가 아니다.** 네 명령 중 둘이
닫혔고 둘이 열려 있다. 아래 `store_entries` 단언이 그 상태를 그대로 센다.

---

## 못을 뽑은 기록 (SPEC-COPILOT-CLASSIFYGAP-001 Phase 2, 카드 t299)

**이 파일의 제목이 이제 틀렸다.** `Store Sequence <N> Cue <M> /Merge` 는 승인
카드를 **띄운다**. 블랙리스트 v5 -> v6 이 `Store Sequence` 를 넣었다. 파일 이름과
위 세 절은 이 파일이 처음 박은 못의 역사로 남기고, 아래 단언들은 뒤집었다 —
조용히 뒤집으면 다음 사람이 사고로 읽는다.

**무엇이 뒤집혔나.** 셋이다.

1. `UNCARDED_SEQUENCE_WRITES` -> `CARDED_SEQUENCE_WRITES`. 세 줄 전부
   `matched_entry='Store Sequence'` / `risky=True` 다.
2. **`/Merge` 대 `/Overwrite` 비대칭이 사라졌다.** 위 11~13행이 「가장 날카로운
   사실」이라 부른 것이 이 SPEC 이 고친 것이다. 둘 다 이제 카드가 뜨고, 잡는
   항목만 다르다(`Store Sequence` 대 `Store /overwrite`). 그 진단 — 결함은
   `/Merge` 전용 구멍이 아니라 `Store` 의 오브젝트 커버리지 — 이 옳았고,
   오브젝트를 넣어서 닫혔다.
3. `test_the_blacklist_carries_no_entry_that_could_match_a_sequence_store` 의
   `assert "Store Sequence" not in RULESET.blacklist` 가 뒤집혔다. 위 35~38행이
   「이 SPEC 이 **지키는** 성질」이라 적은 그 단언이고, 지키던 이유(부수피해 8건)는
   낡은 값이었다. 이 트리 실측은 32건 / 전체 12034 이고 전부 갱신 대상이었다 —
   쇼파일을 안 고치는 흐름이 승인을 요구하게 된 자리는 0건이다.

**비용을 낸 자리 하나.** 확대 직후 큐시트 반영 한 동작에 카드가 **두 장** 떴다 —
그 자리(`session.py::_cue_sheet_draft_apply`)가 t292 당시 자기 채널로 수락을
따로 받고 있었기 때문이다. 그 임시 채널을 걷어내고 `BatchRisk` 선언으로 바꿔
게이트가 유일한 질문자가 되게 했다(카드 1장, 사유 둘 병기). 위 26행이 말한
`_accept_draft_apply_batch` 는 그래서 이제 없다.

**아직 열려 있는 것.** `Store Cue` 하나다(Phase 3). 아래 `store_entries` 단언이
그 상태를 그대로 센다 — 네 명령 중 셋이 닫혔다.

---

## 마지막 못을 뽑은 기록 (SPEC-COPILOT-CLASSIFYGAP-001 Phase 3, 카드 t299)

블랙리스트 v6 -> v7 이 `Store Cue` 를 넣었다. 위 절이 「아직 열려 있는 것」이라
적은 그 하나이고, 이제 **이 SPEC 이 범위로 든 네 오브젝트가 다 닫혔다**.

**무엇이 뒤집혔나.** 하나다 — `store_entries` 목록과 그 짝인
`assert "Store Cue" not in RULESET.blacklist`. 위 절이 「그것까지 닫히면 이 단언이
다시 붉어진다」고 예고해 뒀고, 예고대로 붉어졌다.

**무엇이 안 뒤집혔나.** `CARDED_SEQUENCE_WRITES` 세 줄의 귀속은 v6 그대로
`'Store Sequence'` 다. `Store Cue` 의 키워드 둘이 그 세 줄에도 다 있으므로 항목
수준에서는 닿지만, `_match_blacklist` 가 **첫** 일치에서 돌아오고 v7 은 항목을
목록 끝에 넣었기 때문이다. 그 성질을 아래
`test_the_entry_order_preserves_the_sequence_attribution` 이 검사로 지킨다 —
주석으로만 두면 누가 항목을 위로 옮겨도 아무것도 붉어지지 않는다.
합성 룰셋으로 두 방향을 잰 증거는 `reports/classifygap-t299-p3/08_entry_order.txt`.

**이 회차의 비용.** 33건 / 전체 12047. 전부 폐집합·버전 핀과 「안전한 예」
리터럴이고, 쇼파일을 안 고치는 흐름이 승인을 요구하게 된 자리는 0건이다.
Phase 2 가 낸 비용(큐시트 이중 카드)에 해당하는 것은 이 회차에 없었다 — 카드 수는
확대 전후 모두 1장이다.

**그래도 「구멍이 다 닫혔다」는 아니다.** `Store Page`·`Store Macro`·`Assign`·
`Copy` 는 §F 가 범위 밖에 뒀고 여전히 "safe" 다. 그래서 `SEAL_DEFENCE` 의
seal-only 는 이 회차 뒤에도 **2 로 그대로**다(실측:
`reports/classifygap-t299-p3/07_seal_defence_p3.txt`) — 남은 두 자리가 실어 나르는
것이 `Assign Sequence`·`Copy Sequence` 뿐이기 때문이다.
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


#: 이제 승인 카드가 뜨는 시퀀스 쓰기들 — v6 이 `Store Sequence` 를 넣었다.
#: 세 줄 모두 옵션이 다르다(`/Merge` · 옵션 없음 · 큐 없음). 잡는 것은 옵션이
#: 아니라 **오브젝트**이므로 셋 다 같은 항목에 걸려야 한다 — 그게 이 목록이
#: 세 줄인 이유다.
#:
#: `Store Cue 12` 는 여기 없다. Phase 2 판은 「`UNCHANGED_SAFE` 가 여전히 비준하는
#: 열린 구멍이라」라고 적었지만, v7(Phase 3)이 그것도 닫았다. 지금 빠져 있는 이유는
#: 다르다 — 이 목록은 **시퀀스** 쓰기의 오브젝트 축을 재고, `Store Cue <n>` 은
#: 시퀀스를 지목하지 않는 짧은 형태라 다른 항목(`Store Cue`)에 걸린다. 그 줄의
#: 귀속은 `test_the_entry_order_preserves_the_sequence_attribution` 이 잰다.
CARDED_SEQUENCE_WRITES = (
    "Store Sequence 210 Cue 1 /Merge",
    "Store Sequence 210 Cue 1",
    "Store Sequence 210",
)


@pytest.mark.parametrize("command", CARDED_SEQUENCE_WRITES)
def test_a_sequence_cue_write_now_raises_an_approval_card(command: str) -> None:
    """갱신 근거 (t299 Phase 2): 이 파일이 박은 못을 이 SPEC 이 뽑았다.

    옛 이름은 `test_a_sequence_cue_write_raises_no_approval_card_today` 였고
    `category == "safe"` 를 고정했다. v6 이 오브젝트를 폐집합에 넣었으므로 그
    고정은 이제 거짓이다 — 이름과 단언을 같이 뒤집는다.
    """
    verdict = _classify(command)
    assert verdict.category == "blacklisted"
    assert verdict.risky is True
    assert verdict.matched_entry == "Store Sequence"


def test_merge_and_overwrite_now_both_raise_a_card_by_different_entries() -> None:
    """비대칭이 사라졌다 — 이 SPEC 이 고친 것이 바로 그것이다.

    옛 이름은 `test_the_same_write_with_overwrite_does_raise_a_card` 이고,
    `/Overwrite` 만 카드가 뜨고 `/Merge` 는 안 뜨는 것을 고정했다. 그 검사의
    진단은 옳았다 — 「결함은 `/Merge` 전용 구멍이 아니라 `Store` 의 오브젝트
    커버리지다」. v6 이 그 오브젝트를 넣어서 닫혔다.

    그래서 지금 재는 것은 **둘 다 카드가 뜬다**는 것과, 잡는 항목이 서로 다르다는
    것이다. 항목까지 재는 이유: 둘이 같은 항목에 걸리기 시작하면 옵션 축과
    오브젝트 축이 뒤섞였다는 뜻이고, 그건 과다매칭 신호다.
    """
    merged = _classify("Store Sequence 210 Cue 1 /Merge")
    overwritten = _classify("Store Sequence 210 Cue 1 /Overwrite")
    assert merged.risky is True
    assert overwritten.risky is True
    assert merged.matched_entry == "Store Sequence"
    assert overwritten.matched_entry == "Store /overwrite"


def test_the_gate_itself_is_healthy_on_the_same_bundle() -> None:
    """「게이트가 죽었다」가 아니라 「이 오브젝트가 목록에 없다」임을 고정한다."""
    assert _classify("Set Fixture 11 Posx '5.0'").matched_entry == "Set Fixture"
    assert _classify("Store Preset 4.1").matched_entry == "Store Preset"
    assert _classify("Delete Sequence 210").matched_entry == "Delete"


def test_the_blacklist_now_carries_every_store_object_this_spec_scoped() -> None:
    """갱신 근거 (t299 Phase 3): **이 검사가 자기 갱신을 예고해 뒀다.**

    Phase 2 판의 docstring 이 「남은 구멍은 `Store Cue` 하나다. 그것까지 닫히면
    이 단언이 다시 붉어지고, 그때 이 파일은 『네 명령 전부 닫혔다』로 갱신된다
    (Phase 3)」라고 적었다. v7 이 그 항목을 넣었고 예고대로 붉어졌다 — 갱신
    근거를 새로 만들 필요가 없었다. 검사가 자기 수명을 적어 두면 다음 사람이
    「고쳐서 통과시킨 것인지」를 되짚지 않아도 된다.

    이름도 같이 바꾼다. `..._the_sequence_store_entry` 는 이제 셋 중 하나만
    가리키므로 좁다.

    **주의 — 이 목록은 「폐집합이 완결됐다」가 아니다.** 이 SPEC(§F)이 범위로 든
    네 오브젝트가 다 들어왔다는 뜻이고, `Store Page`·`Store Macro` 는 여전히
    밖이다. 그 둘은 `test_writegate.py::UNCHANGED_SAFE` 가 계속 비준하며 각자
    후속 카드를 갖는다. 아래 마지막 단언이 그 경계를 문면으로 센다.
    """
    assert "Store Sequence" in RULESET.blacklist
    # Phase 2 판이 「Phase 3 의 착수 신호」라 적은 줄을 뒤집는다.
    assert "Store Cue" in RULESET.blacklist
    store_entries = [entry for entry in RULESET.blacklist if entry.split()[0] == "Store"]
    assert store_entries == [
        "Store /overwrite",
        "Store Preset",
        "Store Group",
        "Store Timecode",
        "Store Sequence",
        "Store Cue",
    ]
    # 아직 열려 있는 오브젝트 — 이 SPEC §F 가 범위 밖에 뒀고 후속 카드가 받는다.
    # 이 두 줄이 없으면 위 목록이 「전부 닫혔다」로 잘못 읽힌다.
    assert "Store Page" not in RULESET.blacklist
    assert "Store Macro" not in RULESET.blacklist


def test_the_entry_order_preserves_the_sequence_attribution() -> None:
    """갱신 근거 (t299 Phase 3): 순서가 카드 문면을 정한다 — 실측으로 확인함.

    `classify.py::_match_blacklist` 는 목록을 순회하며 **첫** 일치에서 돌아온다.
    그래서 `Store Cue` 를 `Store Sequence` 앞에 두면
    `Store Sequence 210 Cue 10 /Merge` 의 귀속이 `'Store Cue'` 로 바뀐다 — 안전
    판정은 같지만 감독이 카드에서 읽는 사유가 달라진다.

    v7 은 항목을 목록 **끝**에 넣어 v6 의 귀속을 보존했다. 그 성질은 주석이 아니라
    검사로 지켜야 한다: 누가 항목을 위로 옮기면 이 줄이 붉어진다.

    합성 룰셋으로 두 방향을 함께 잰 증거:
    `reports/classifygap-t299-p3/08_entry_order.txt`.
    """
    order = list(RULESET.blacklist)
    assert order.index("Store Sequence") < order.index("Store Cue")
    assert _classify("Store Sequence 210 Cue 10 /Merge").matched_entry == "Store Sequence"
    # 짧은 형태는 새 항목에 걸린다 — 위 순서가 그 줄을 가리지 않는다는 비공허성 짝.
    assert _classify("Store Cue 10").matched_entry == "Store Cue"
