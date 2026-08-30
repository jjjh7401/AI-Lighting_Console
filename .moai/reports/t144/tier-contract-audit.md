# t144 — tier 계약 전수. 카드가 안 것은 2, 실제는 10, 그리고 SPEC 이 아닌 자리가 하나

- 카드: t144 · 대상 `.moai/specs/` 전량 · 기준 `a80a3dc` · 브랜치 `WT-tier-contract-audit`
- **콘솔 접촉 0 · 코드 변경 0 · SPEC 파일 생성/수정 0.** 판정과 전수표까지다.
- 소유권: status 전이는 manager-docs · SPEC 본문은 manager-spec. 이 카드는 **아무것도 안 썼다.**

## 0. 결론

| | 수 |
|---|---|
| `.moai/specs/` 아래 SPEC 디렉터리 | **45** |
| tier 계약 미충족 | **10** |
| 그중 `status: completed` | **3** |
| `spec.md` 자체가 없는 디렉터리 | **1** (카드에 없던 것) |
| 카드가 알고 있던 것 | 2 |

카드가 지목한 둘은 t136 이 우연히 본 것이었고, 전수하니 **다섯 배**다.

🔴 그리고 **가장 급한 자리의 성격이 카드 예상과 다르다** — FXGEN-001 의 `completed` 는
**정확하다.** 부재한 것은 작업이 아니라 **기록**이다(§2).

## 1. 전수표 (45)

계약(`.claude/rules/moai/workflow/spec-workflow.md` § SPEC Complexity Tier):
`S` = spec+plan(2) · `M` = +acceptance(3) · `L` = +design+research(5) · tier 부재 → L 취급.
⚠️ **`progress.md` 는 tier 산출물 집합에 없다** — 별개 축이라 따로 셌다.

### 1.1 미충족 10건

| SPEC | status | tier | 계약 | 실제 md | progress | 빠진 것 |
|---|---|---|---|---|---|---|
| **FXGEN-001** | **completed** | L | 5 | 2 | **없음** | plan · acceptance · design |
| **IMGLAYOUT-001** | **completed** | 부재→L | 5 | 2 | **없음** | plan · acceptance · design · research |
| **SPATIALMEM-001** | **completed** | M | 3 | 1 | **없음** | plan · acceptance |
| COLORPRESET-001 | draft | M | 3 | 3 | 있음 | acceptance |
| CUETIME-001 | (없음) | 부재→L | 5 | 5 | 있음 | design |
| DEPLOY-001 | in-progress | L | 5 | 15 | 있음 | design |
| PRESETGUARD-002 | draft | S | 2 | 1 | **없음** | plan |
| PRESETIDEM-001 | draft | S | 2 | 3 | 있음 | plan |
| SONGSTD-001 | (없음) | 부재→L | 5 | 5 | **없음** | design |
| **RESTORE-001** | — | — | — | 6 | — | **`spec.md` 자체가 없다** |

「실제 md」가 계약보다 커도 미충족일 수 있다 — **개수가 아니라 이름**이 계약이다
(DEPLOY-001 은 md 15개인데 `design.md` 가 없다).

### 1.2 `progress.md` 부재 8건

FXGEN-001 · IMGLAYOUT-001 · PRESETGUARD-002 · SONGSTD-001 · SPATIALMEM-001 ·
TREEID-001 · TRUNCATE-001 · UNREQ-001.

뒤 셋은 **tier 계약은 충족**한다 — 즉 두 축은 겹치되 같지 않다.

## 2. (a) FXGEN-001 의 `completed` 는 실제 완료를 반영하는가 — **한다**

요약이 아니라 **커밋 이력과 산출물 실재**로 답한다.

**커밋:**

    e11ff17  feat(fx): open measured phaser axes, compose_fx tool, preset-All destination,
             editor-routing asset                          <- 구현 커밋, SPEC 디렉터리를 건드렸다
    c760b00  docs(SPEC-COPILOT-FXGEN-001): sync-phase artifacts — 3-phase close
    5a6c844  docs(changelog): SPEC-COPILOT-FXGEN-001 entry
    b2b07c1  docs: FXGEN completed 전환 …

**REQ 가 만들라고 한 것이 실제로 있는가:**

| REQ | 산출물 | 실측 |
|---|---|---|
| REQ-FXGEN-016 | `server/rulebook/assets/v2.4.2/33_effect_editors.md` **신설** | **존재**, 4,595 B |
| REQ-FXGEN-017 (b) | `31_choreography_patterns.md` 에 `OBSERVED EFFECT` 항 **추가** | **존재**, 1건 |
| (구현) | `compose_fx` 툴 | `tools.py` 에 **8회** |

**살아 있는 안전장치가 그 REQ 를 인용한다** — `server/tests/test_overlap_preserve.py`
의 PRESERVE 예외 주석 **4자리**(`:93` `:96` `:579` `:608`)가 `REQ-FXGEN-016`·
`REQ-FXGEN-017(b)` 를 근거로 든다. 그리고 그 REQ 는 `spec.md:91-92` 에 **본문으로 실재**한다.

**판정: 장부가 앞서 나간 것이 아니다.** 일은 됐고 닫혔다. 없는 것은 **계획·수용·설계
문서와 진행 기록**이다. 즉 **부재한 것은 작업이 아니라 기록이다.**

⚠️ 다만 그 결과가 무해하지 않다: **PRESERVE 예외가 왜 정당한지 검산하려면 진행
기록을 봐야 하는데 그게 없다.** 지금은 `spec.md` 의 REQ 문면과 자산 실재로만 검산된다.

> **[정정 고지 — 2026-08-30, t158 이 덧붙였다. 위 문단은 한 글자도 고치지 않았다.]**
>
> **위 ⚠️ 문단은 너무 셌다.** 「검산하려면 진행 기록을 봐야 한다」가 참이 아니다 —
> t158 이 전수하며 그 승인의 **집행 경로**를 읽었다:
>
>     _RULEBOOK_GRANTED_ADDITIONS  -> 33_effect_editors.md 를 **경로 이름으로** 고정
>     _RULEBOOK_GRANTED_APPEND     -> 31_choreography_patterns.md
>     _RULEBOOK_APPEND_HEADING     -> 추가 블록의 **헤딩 문자열**까지 고정
>     삭제 0 요구 + test_the_only_rulebook_changes_are_the_granted_ones 가 단언
>
> 즉 **집행은 기계적 핀이 하고, REQ 인용은 근거(rationale)일 뿐이다.** 진행 기록이
> 없어도 그 승인이 무엇을 허용하는지는 바이트 단위로 좁혀져 있다. 게다가 같은 파일의
> `granted` 28회 중 REQ 를 근거로 드는 것은 3회뿐이다 — **대부분의 승인은 애초에 REQ
> 없이 정당화된다.**
>
> 기록이 있으면 더해지는 것은 **집행이 아니라 서사**(감독이 왜 승인했는지)다.
> 전수와 근거: `.moai/reports/t158/citation-record-audit.md`.

## 3. (b) tier 를 낮추나 산출물을 채우나 — **둘 다 단순 적용이 안 된다**

### 3.1 FXGEN-001 은 **어느 tier 에도 안 맞는다**

가진 것: `spec.md` + `research.md`.

| tier | 요구 | FXGEN 이 못 채우는 것 |
|---|---|---|
| S | spec + plan | **plan.md** |
| M | + acceptance | plan · acceptance |
| L | + design + research | plan · acceptance · design |

`research.md` 는 **L 전용 산출물**인데 `plan.md` 가 없다. 즉 **낮춰도 안 맞고 올려도
안 맞는** 조합이라 「tier 하향」이 답이 아니다.

### 3.2 그리고 소급 저작은 위조에 가깝다

끝나서 닫힌 SPEC 에 `plan.md`·`acceptance.md` 를 지금 쓰면 **없던 계획을 사후에
지어내는 것**이다. 이 저장소가 반복해 지킨 선(기록은 고치지 않고 고지한다)의 정반대다.

**남는 선택지는 셋이고, 셋 다 소유자가 따로다:**

| | 무엇 | 소유 |
|---|---|---|
| ① | tier 선언을 **실제 산출물에 맞게** 재정의(또는 「grandfathered」 표기 신설) | manager-spec |
| ② | 계약 미충족을 **고지로 남기고** 그대로 둔다 — 소급 저작 대신 | manager-spec |
| ③ | 계약 자체를 **완료 SPEC 에는 소급 적용하지 않는다**고 규칙에 명시 | 규칙 소유자 |

**이 카드는 셋 중 하나를 고르지 않는다.** 판정과 표까지가 범위다.

### 3.3 RESTORE-001 은 다른 종류다

`spec.md` 가 **한 번도 없었다**. 커밋 5건이 전부 `docs(restore):` 조사 문서다
(`restore-design.md` · `readability-survey.md` 등 6개). **SPEC 이 아니라 조사 모음이
`.moai/specs/` 아래 있는 것**이고, tier 위반이 아니라 **분류 문제**다.

## 4. (c) 도구 축과 이 판정은 **서로소다**

    moai spec audit  ->  MUST-FIX **1건** (저장소 전체)
                         SPEC-COPILOT-LXSEQ-001 — SyncStatusDrift
                         Reason: §E.2 + §E.4 + sync_commit_sha present (sync complete)
                                 but status != completed

**내 10건과 하나도 안 겹친다.** LXSEQ-001 은 tier 계약을 충족한다(M, md 7개).
반대로 FXGEN-001·IMGLAYOUT-001·SPATIALMEM-001 은 도구가 `[INFO] (V2.x) —
EraAutoDetected` 로만 낸다 — **grandfathered 라 MUST-FIX 가 아니다.**
RESTORE-001 은 `[INFO] — AuditError`(분류 불가).

🔴 **그러므로 「도구가 0건이니 문제없다」도, 「내가 10건이니 도구가 틀렸다」도 아니다.**
두 축이 다른 것을 잰다:

    도구  = 그 시대 규약에 맞는가 (era 기준, 완료 SPEC 은 관대)
    이 판정 = 선언한 tier 의 파일 계약을 채웠는가

t136 이 그은 구분(「결함이다」는 계약 판정이지 도구가 걸었다는 뜻이 아니다)이 여기서
**수치로** 확인됐다 — 교집합 0.

## 5. 안 잰 것

1. **10건 각각의 커밋 이력** — FXGEN-001 만 이력까지 팠다(카드가 그것을 가장 급한
   자리로 지목했다). 나머지 9건은 파일 집합과 frontmatter 까지만 봤다.
2. **`progress.md` 부재가 언제부터인지** — 8건이 원래 없었는지 지워졌는지 안 봤다.
3. **다른 인용 관계** — 안전장치가 SPEC REQ 를 인용하는 자리를 FXGEN 축만 확인했다.
   같은 형태(살아 있는 검사가 기록 없는 SPEC 을 인용)가 더 있는지는 미측정이다.
4. **`contract.md` 같은 비표준 이름** — IMGLAYOUT-001 의 `contract.md` 가 acceptance
   역할을 하는지 열어보지 않았다. 그렇다면 이름만 다른 것이고 판정이 달라진다.
5. **tier 부재 3건**(CUETIME-001 · SONGSTD-001 · IMGLAYOUT-001)이 의도적 미선언인지
   누락인지 — 하위호환 규칙이 L 로 읽으라고만 한다.
