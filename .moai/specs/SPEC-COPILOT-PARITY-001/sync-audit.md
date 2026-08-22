---
id: SPEC-COPILOT-PARITY-001
type: sync-audit
version: "1.0.0"
created: 2026-08-22
author: sync-auditor (칸반 카드 t11 · 감사 레인)
verdict: PASS-WITH-DEBT
score: 0.86
threshold: 0.80
tier: M
audited: fc37abc
---

# SPEC-COPILOT-PARITY-001 — 독립 sync 감사

대상: `origin/WT-handle-to-name` 커밋 `fc37abc`. 트리 `.claude/worktrees/t11-sync-audit` · 브랜치 `WT-parity-sync-audit`.
범위: 콘솔 무접촉 · 제품 코드 수정 0건 · 판정만.
같은 감사자가 이 SPEC 의 plan-audit 1차(FAIL 0.72) · 2차(PASS 0.88)를 냈다. **이번은 다른 질문이다 — 구현이 그 SPEC 을 충족하는가.**

---

## §1 Claim — 판정

**PASS-WITH-DEBT — 0.86 / Tier M 기준 0.80.**

**AC 12건 전부 통과**를 재현했고 `completed` 전이는 **정당하다.** 다만 어디에도 공개되지 않은 **주요 결함 1건(D-1)** 과 경미 2건(D-2 · D-3)이 있다. D-1 은 AC 를 깨지 않으나 **이 카드가 스스로 세운 코드 계약을 이 카드의 배선이 어긴다.** 이 카드가 처음부터 끝까지 지켜 온 것이 「공개」이므로, 닫기 전에 **고치거나 공개하거나** 둘 중 하나를 권한다 — 어느 쪽이든 닫힌다.

이 구현의 증거 규율은 이 저장소에서 본 것 중 상위다. 스스로 불리한 항목 둘을 올렸고(D4 초과 · 미검사 갈래), 「8곳 중 1곳만 배선」이라는 자기 설계의 한계를 **구문적 사실로** 못 박았으며, 어긋남 3건을 **열린 채로 사용자 문서에까지** 실었다.

---

## §2 Evidence

### 재현한 것 — 리드 값과 대조

| # | 검증 | 결과 |
|---|---|---|
| R1 | 커밋 사슬 6단 | 배차와 일치 (`5c988bd` → `aabcdde` → `581a1fb` → `d6b1c49` → `4152bd4` → `fc37abc`), `fc37abc` 는 `5c988bd` 의 자손 |
| R2 | 봉쇄 구역 `5c988bd..fc37abc`(`vwx` · `paperwork`) | **빈 출력** — 일치 |
| R3 | `4152bd4..fc37abc` 변경 파일 | `test_prechk_handle_types.py` · `progress.md` 둘뿐 — 일치 |
| R4 | `status:` | `implemented` — 전이 안 됨, 일치 |
| R5 | **전체 스위트 직접 실행** | `9705 passed, 8 skipped, 1 warning in 155.33s` · **exit 0** — 리드 기준선 `9705` 와 일치 |
| R6 | 신규 테스트 14건 | `test_prechk_handle_types.py` **12 passed** · `test_lxseq_tool.py -k handle` **2 passed** |
| R7 | 복구 체크섬 | `shasum -a 256 server/prechk/mode_read.py` → `8fac1096147abe2fab267e93eb7994ee84cc52fac49a0286fcf49957c2787871` — progress.md 가 인용한 `8fac1096…7871` 과 일치 |
| R8 | 신설 코드가 `aabcdde` 이후 무변경 | `aabcdde..fc37abc` 의 `mode_read.py` · `inventory.py` · `tools.py` → **빈 출력** |

**R5 가 이 감사의 중심 증거다.** 1·2차 plan-audit 에서 내가 여덟 항목의 Gaps 중 첫 번째로 적었던 「테스트를 한 건도 돌리지 않았다」가 이번에 닫혔다. 기준선을 남에게 듣지 않고 직접 쟀다.

### 자진 신고 2건 — 둘 다 결함이 아니다

**① D4 문면 초과 → 문서 지체.** `plan.md` D4 는 「A-1 이면 `inventory.py` + 테스트」라 적었고 실제는 `mode_read.py` · `tools.py` 2파일 초과다. 그러나 두 파일 모두 **계획이 지시한 것**이다 — `plan.md` M1-3 이 「(슬롯→이름) 전체 표를 돌려주는 판독을 **신설**」하라 했고(그 문장은 이 감사자의 1차 지적으로 들어갔다), 판독 공유 결정이 호출자의 표 전달을 요구한다. `acceptance.md` 를 임의로 고치지 않은 것은 소유 경계 준수다(manager-spec 소유). **결함 아님 — 문서 지체.**

**② 미검사 갈래 2건 → 닫혔고, 예외도 정당했다.** `mode_read.py:127` · `:130`. 리드 예외(테스트 파일만)가 기계적으로 지켜졌음을 R8 · R7 이 확인한다. 두 테스트는 결과가 같은 두 갈래를 `attempted` 로 가르고, 뮤테이션이 **각각 자기 테스트 한 건만** 죽였다 — 판별력의 증거다(이 저장소가 「뮤테이션 6회 중 2회 통과」로 물린 자리라 이 형태가 중요하다). **예외 승인 정당.**

---

### D-1 (주요) — 트리 판독 실패가 「슬롯 부재」로 보고된다. 이 코드의 자기 주석이 금지한 바로 그 혼동이다

> **`completed` 로 가기 전에 고치거나 공개해야 하는 이유**: 이 카드가 세운 계약을 이 카드의 배선이 어기고 있고, 그 사실이 progress.md · CHANGELOG · README 어디에도 없다. 이 카드가 지켜 온 유일한 방어선이 「공개」다.

**측정했다 — 코드를 읽은 추론이 아니다.** 트리 판독을 `ok:false` 로 거절하는 리더를 만들어 실행했다.

```
attempted: False | pairs: () | by_slot(): {} | is None: False
translate(failed-tree table): ('FixtureType 4', 'slot_absent')
translate(no table at all)  : ('FixtureType 4', 'no_type_table')
```

`by_slot()` 은 판독이 실패해도 `None` 이 아니라 **빈 dict** 를 돌려준다. 유일한 배선(`tools.py:4518`)은 `attempted` 를 보지 않고 `.by_slot()` 을 그대로 넘긴다. 그래서 **트리가 답하지 않았을 때 모든 핸들이 `slot_absent` 로 표시된다.**

이 코드 자신이 그러면 안 된다고 적어 두었다.

- `TypeNameRead` 주석: *"``attempted`` separates 'the tree did not answer' from 'the tree answered and declared nothing'. Both leave ``pairs`` empty, and **a caller that conflates them would report a read failure as 'slot absent'**."*
- `FixtureRecord.fixture_type_untranslated` 주석: 두 사유를 가르는 이유는 **「순서 결함(고칠 수 있다)」과 「리그 사실(고칠 수 없다)」을 혼동하지 않기 위해서**다.

즉 주석이 예고한 실패가 그대로 일어난다. 그리고 이것은 **D2 자신과 같은 결함 부류**다 — 라벨이 틀려 사람이 엉뚱한 손을 움직인다. `slot_absent` 를 읽은 감독은 「내 콘솔에 그 타입이 없다」로 이해해 리그를 손보러 가고, 실제로 필요한 것은 **재시도**다.

**등급을 주요로 두고 차단으로 올리지 않은 이유** — 셋을 함께 적는다.

1. **AC 를 깨지 않는다.** AC-PARITY-009 가 요구하는 것은 「원값 보존 + 미번역 표식」까지이고 둘 다 성립한다. 사유의 정확성을 요구하는 AC 는 없다.
2. **쓰기는 0이다.** D2 와 같이 라벨 결함이지 안전 결함이 아니다.
3. **노출이 부분적으로 가려질 수 있다 — 다만 이것은 내가 재지 않았다.** 배선된 경로에서 `read_type_mode_widths`(`:4510`)가 **같은 트리를 먼저** 읽으므로, 트리가 죽으면 모드 미해석으로 먼저 걸러질 가능성이 있다. **코드 순서를 읽은 추론이며 실행해 확인하지 않았다** — 그래서 이 완화를 근거로 등급을 더 내리지도 않았다.

**고치는 법(제안)**: 호출 지점에서 `attempted` 를 보고 실패 시 `None` 을 넘기거나, `by_slot()` 이 `attempted=False` 일 때 `None` 을 돌려주게 한다. 어느 쪽이든 몇 줄이고, 그 갈래를 고정하는 테스트가 함께 필요하다. **고치지 않기로 한다면 progress.md · CHANGELOG 에 「트리 판독 실패는 현재 `slot_absent` 로 보고된다」를 적으면 이 항목은 닫힌다.**

### D-2 (경미) — CHANGELOG 의 검증 수치가 출하 HEAD 보다 낡았다

CHANGELOG 는 「`9703 passed` · 손대기 전 기준선 `9691` 대비 **+12 = 신규 테스트 수와 정확히 일치**(단위 10 + 통합 2)」로 적었다. 그러나 출하 HEAD `fc37abc` 는 **`9705`** 이고 신규 테스트는 **14건**(단위 12 + 통합 2)이다. `grep -c "9705" CHANGELOG.md` → **0**.

`fc37abc` 후속 커밋이 `progress.md` 는 갱신하면서(§E.4 정정에 `9705` · +2 가 있다) **사용자 문서는 갱신하지 않았다.** 숫자 자체가 틀린 것은 아니고 `d6b1c49` 시점에는 맞았으나, 출하되는 트리와 어긋난다. 이 저장소가 반복해 물린 **「측정한 것과 옮긴 것이 다르다」** 의 시간축 변형이다.

**고치는 법**: CHANGELOG 검증 줄을 `9705` · +14(단위 12 + 통합 2)로 갱신하고 후속 커밋에서 미검사 갈래 2건을 닫았다는 한 줄을 붙인다.

### D-3 (경미) — M2 집계 줄의 산술이 어긋난다

progress.md 분류표 아래 집계: 「어긋남 3(C3 · C4 · C5) · 닫힘 2(C1 · C9) · **무관 5**(C2 · C8 · C10판정 · C11 · C12 · C13 중 판정축)」 — 괄호에 이름이 **여섯** 있는데 수는 **5** 로 적혔다. 검산하면 3 + 2 + 6 = 11 = 「측정됨 11」과 맞으므로 **6이 옳다.** 바로 다음 절의 A-1 표도 「닫을 필요가 없다 | C2 · C8 · C10 · C11 · C12 · C13」로 여섯을 든다.

---

## §3 관찰

- **O-1. 리드가 준 측정 하나가 재현되지 않는다.** 배차문은 `581a1fb..fc37abc -- server/ ui/` → **빈 출력(제품 코드 0)** 이라 적었으나, 그대로 돌리면 `server/tests/test_prechk_handle_types.py | 29 +++++` 가 나온다. **주장은 참이다** — 테스트를 제외한 형태(`':!server/tests/'`)로 다시 재면 빈 출력이고, 제품 코드는 실제로 0건이다. 어긋난 것은 **인용한 명령과 그 출력의 짝**이다. 이 저장소가 이 카드에서만 세 번 물린 모양(8→13 · 20→22 · 9703↔9705)의 같은 계열이며, 이번엔 리드 쪽이다. 명령을 고치거나 「테스트 제외」를 명시하면 닫힌다.
- **O-2. AC-011 은 통과하나, 미측정 2건은 acceptance 가 허용한 종류가 아니다.** `acceptance.md` 는 「**오프라인으로 결론이 안 나는 자리**는 미측정으로 남기는 것이 옳은 결과」라고 **조건을 달았다.** C6(`tools.py:3734`) · C7(`prechk/patch.py:236`)은 오프라인으로 측정 가능한 자리이고, progress.md 자신이 그렇게 적었다 — 「핸들러를 실행해 페이로드를 관측하지 않았다」 · 「`to_dict()` 를 실행하지 않았다」. 즉 **「옳은 미측정」이 아니라 「안 잰 것」이다.** 그럼에도 **AC-011 문면은 통과한다**: 요구는 각 행에 (a) 판정 (b) 측정됨/미측정 (c) 근거가 있을 것이고, 두 행 모두 셋을 갖췄다. 표가 스스로 정직하므로 결함이 아니라 관찰로 둔다 — 다만 「옳은 결과」라는 수식을 이 두 행에 붙이면 그건 과장이다.
- **O-3. A-1 의 표제 이득은 배송되지 않았다 — 그러나 은폐도 없다.** `spec.md §A.4` 는 A-1 을 고른 이유를 「C1~C13 **동시 해결**」로 적었다. 실제로 닫힌 것은 **C1 · C9 둘**이고, 이는 같은 표가 A-2 에 배정한 범위(「C1만 해결」)와 사실상 같다. A-1 의 구조적 이점(자리를 판독 경계에 잡아 두어 다음 호출자가 표만 넘기면 번역이 따라온다)은 남지만, **오늘의 커버리지는 A-1 을 고른 근거와 다르다.** progress.md 가 이를 「8곳 중 1곳」으로 못 박고 CHANGELOG · README 가 열린 3건을 사용자에게까지 알리므로 **은폐는 없다.** `spec.md` 문면이 갱신되지 않은 것은 소유 경계(manager-spec) 때문이며 문서 지체다. 다음 카드가 그 줄을 고칠 자리다.
- **O-4. C3 거짓 경보가 실제로 사용자 문서까지 갔다.** 리드가 [HARD] 로 지킨 세 문장을 열어 확인했다 — CHANGELOG 에 「**모든 타입이 `console_count=0` 으로 보고된다. 실기에 86대가 있어도 「콘솔에 아무것도 없다」로 읽힌다**」 · 「AC 전건 통과가 실기 D2 해소의 증거는 아니다」 · 「이 저장소에는 테스트 CI 가 없다」 셋 다 있다. README 도 「closed **offline**」 · 「**This has not been re-verified on a console**」 · 미번역 소비자 2건을 담는다. **오프라인 보증이 실기 보증으로 승격되지 않았다.**
- **O-5. 내 2차 지적 O-8 이 반영됐다.** 「라이브 관측 단 1건」이 CHANGELOG 에서 「한 번의 판독에서 86행 · 8개 슬롯이 모두 같은 형식」으로 바뀌었다. 근거를 부풀리지 않고 사실에 맞춘 정정이다.

---

## §4 AC 12건 판정

| AC | 판정 | 재현한 증거 |
|---|---|---|
| 001 | PASS | `FakeConsole(handle_types=...)` 생성자 인자 1개. 기본 False → 이름 |
| 002 | PASS | 기본 경로 불변. 스위트 `9691`(M1-0) → `9705`(HEAD), 증가 14 = 신규 테스트 14건. 내가 잰 것은 HEAD 쪽 `9705` 이며 `9691` 은 §E.2 인용이다 |
| 003 | PASS | `test_the_handle_branch_is_off_by_default_and_leaves_the_tree_naming` — 한 테스트 안에서 트리는 이름 · 프로퍼티는 핸들을 함께 단언 |
| 004 | PASS(기록) | 수정 전 RED 는 §E.2 M1-2 의 기록이며 **재현 대상이 아니다**(번역 코드가 이미 있다). 그 목적은 D3 뮤테이션이 보증한다 |
| 005 | PASS | `test_a_handle_answering_console_still_reports_already_patched` — 통과 확인. 호출이 아니라 **결과**(`already_patched`)를 단언한다 |
| 006 | PASS(인용) | 뮤테이션 4종 KILLED 는 §E.2 기록. **내가 재현하지 않았다**(제품 코드 수정 0건 범위) — §5 Gaps 1번 |
| 007 | PASS | `test_a_handle_becomes_the_name_its_slot_declares` — `("FixtureType 10", {10:...})` → 이름, 표식 None |
| 008 | PASS | `test_a_name_passes_through_unchanged_even_when_absent_from_the_library` — **라이브러리에 있는 이름과 없는 이름 양쪽**을 단언(acceptance 요구 그대로) |
| 009 | PASS | `test_an_unresolvable_handle_keeps_the_raw_value_and_says_why` — **원값과 표식을 둘 다** 단언. 「표식만 검사하면 공허하다」는 acceptance 경고가 테스트 주석에 그대로 있다. **단 (a) 갈래의 사유가 틀린다 — D-1** |
| 010 | PASS | `test_the_same_name_on_two_slots_is_not_ambiguous_forward` — 번호가 아니라 「같은 이름 두 슬롯」 형상만 재현 |
| 011 | PASS | C1~C13 열세 행 · 각 행에 판정 · 측정여부 · 근거. 측정 11 · 미측정 2. 집계 산술은 D-3, 미측정의 성격은 O-2 |
| 012 | PASS | **직접 실행**: `9705 passed, 8 skipped, 1 warning in 155.33s` · exit 0 |

**12/12 PASS.** 004 · 006 은 성질상 기록 인용이며 그 사실을 위에 명시했다.

---

## §5 `completed` 전이 판정 — 이 감사가 그 게이트다

**전이해도 된다.** 근거 넷:

1. **AC 12/12 통과**, 그중 핵심 넷(002 · 005 · 009 · 012)은 내가 직접 실행해 재현했다.
2. **범위가 지켜졌다** — 봉쇄 구역 0-diff, 제품 코드는 `581a1fb` 이후 0건, `fc37abc` 예외는 조건대로 테스트 파일만.
3. **열린 것이 열린 채로 공개됐다** — 어긋남 3건이 progress.md · CHANGELOG · README 세 층 모두에 있고, 「오프라인 보증 ≠ 실기 보증」이 사용자 문서에 그대로 있다.
4. **자진 신고 2건은 결함이 아니다**(문서 지체 · 닫힘).

**다만 D-1 은 닫고 가라.** 차단으로 올리지 않는 이유는 §2 에 셋으로 적었으나, 이 카드가 처음부터 지켜 온 방어선이 「공개」이고 **D-1 만이 실재하면서 공개되지 않은 유일한 항목**이다. 고치는 것(몇 줄 + 테스트)과 적는 것(한 줄) 둘 다 싸다. 어느 쪽이든 닫힌다.

D-2 · D-3 은 문서 한 줄씩이며 `completed` 를 막지 않는다.

---

## §6 Baseline-attribution

| 항목 | 값 |
|---|---|
| 대상 | `fc37abc` (`origin/WT-handle-to-name`) |
| 트리 | `.claude/worktrees/t11-sync-audit` · 브랜치 `WT-parity-sync-audit` |
| 스위트 | `uv run pytest server/tests -q` → `9705 passed, 8 skipped, 1 warning in 155.33s` · exit 0 **(이 트리, 이 실행)** |
| 표적 실행 | `test_prechk_handle_types.py` 12 passed · `test_lxseq_tool.py -k handle` 2 passed |
| 프로브 | 거절 리더로 `read_fixture_type_names` → `by_slot()` → `translate_fixture_type` 실행 (D-1 의 근거) |
| 체크섬 | `mode_read.py` = `8fac1096…7871` |
| 읽은 원문 | `mode_read.py`(신설 `TypeNameRead` · `read_fixture_type_names`) · `inventory.py`(`HANDLE_TEXT` · `translate_fixture_type` · `_name_handle_types` · `read_inventory` 시그니처) · `tools.py`(배선 9행) · `progress.md` 384행 · `CHANGELOG.md` PARITY 항목 · `README.md:286-301` · 신규 테스트 14건 |
| 콘솔 | 접속 0건 |

기준선은 **`9705`**(`fc37abc`)를 썼다. `9703`(M1-6) · `9691`(M1-0)은 §E 인용으로만 쓰고, 다른 카드의 `9681` · `9682` 는 인용하지 않았다.

---

## §7 Gaps — 내가 재현하지 않은 것

1. **뮤테이션 4종(D3)을 재현하지 않았다.** 배차 범위가 「제품 코드 수정 0건」이라 번역 지점을 항등으로 바꿔 보지 않았다. AC-006 은 §E.2 의 기록을 **인용**한 것이며 내 관측이 아니다. 대신 복구 체크섬(R7)을 대조해 「본문이 되돌아왔다」까지는 독립 확인했다.
2. **D-1 의 완화가 실제로 성립하는지 재지 않았다.** 「모드 판독이 같은 트리를 먼저 읽어 가려질 것」은 **코드 순서를 읽은 추론**이다. 배선 경로 전체를 태워 확인하지 않았다.
3. **C6 · C7 을 내가 대신 재지 않았다.** M2 의 몫이고 감사가 대신하면 카드를 먹는다.
4. **어긋남 3건(C3 · C4 · C5)의 원인 동일성을 재지 않았다.** progress.md 도 「원인이 하나로 보이나 측정 안 했다」로 남겼고 나도 재지 않았다.
5. **콘솔 무접촉.** 실기 핸들 형식, 슬롯 12, 86대 재조회 — 전부 하지 않았다. 이 카드의 최대 잔여 가정이 그대로다.
6. **UI 스위트를 돌리지 않았다.** CHANGELOG 의 「496 passed 불변」은 인용이다.
7. **`read_inventory` 나머지 7곳의 질의 순증을 재지 않았다.** M1·sync 가 남긴 항목 그대로.
8. **`/code-review` 는 이번에도 내가 돌리지 않았다.** 감독이 병행 중이라고 들었으나 **내 판정은 그것을 기다리지도 참고하지도 않았다** — 두 검사가 독립이어야 대조에 의미가 있다는 배차 지시대로다.

---

## §8 Residual-risk

- **D-1 을 고치면 새 갈래가 생긴다.** `attempted=False` 에 `None` 을 넘기면 그 경로의 표식이 `no_type_table` 로 바뀐다 — 「이 경로가 트리를 안 읽었다」는 뜻인데 실제로는 「읽었으나 답이 없었다」이다. 두 사유로 부족할 수 있으며 세 번째 사유(`table_read_failed`)가 필요할 수 있다. **설계 판단이므로 여기서 정하지 않는다.**
- **A-1 의 구조적 이점은 아직 가설이다.** 「다음 호출자가 표만 넘기면 번역이 따라온다」는 실제로 두 번째 호출자가 배선될 때 증명된다. 오늘은 한 곳뿐이라 A-2 와 커버리지가 같다(O-3).
- **이 감사도 한 형태다.** 원문 대조 + 표적 실행 + 전체 스위트 + 프로브 하나. `/code-review` 가 무엇을 낼지는 모르며, 이 저장소는 감사 2회가 놓친 것을 코드 리뷰가 잡은 전례를 갖는다(t9). **내 목록에 없는 축**: 성능 · 동시성 · 신설 판독의 예외 안전성 · UI · 실기.
- **가짜↔가짜 괴리 발견(t12 재료)이 시사하는 것.** 이번 카드가 찾은 첫 실례는 「가짜 ↔ 실물」이 아니라 **「가짜 ↔ 가짜」** 였다. 오프라인만으로 가능한 축이 남아 있다는 뜻이며, t12 를 「실기 필요」로만 틀 지으면 그 축을 놓친다. 이 지적은 progress.md 가 이미 적었고 내가 동의한다.

---

**결론: PASS-WITH-DEBT 0.86 · `completed` 전이 정당.** D-1 은 고치거나 적어라. D-2 · D-3 은 문서 한 줄씩.

감사자: sync-auditor (t11 감사 레인) · 대상 `fc37abc` · 트리 `.claude/worktrees/t11-sync-audit`
