# t158 — 인용 전수. 무게 있는 자리는 하나뿐이었고, 검산 경로는 이미 있다

- 카드: t158 · 감사 카드 · 기준 `aa2c63b` · 브랜치 `WT-citation-record-audit`
- **콘솔 접촉 0 · 코드 변경 0 · SPEC 파일 생성/수정 0.** 판정과 전수표까지다.

## 0. 결론 셋

1. **(3) 죽은 인용 0** — 살아 있는 코드가 인용하는 고유 REQ **381**개가 전부 SPEC 문서에 실재한다. **날조 대조군으로 검출력을 먼저 확인**했다.
2. **(1) 인용된 SPEC 37개 중 진행 기록 없는 것 5** — 그런데 **무게가 있는 자리는 FXGEN 하나뿐**이다(§2).
3. 🔴 **(2) 기록 복원은 필요 없다** — 그 승인의 **집행은 기계적 핀**이 하고 REQ 인용은 근거일 뿐이다. **t144 에 내가 쓴 문장이 너무 셌고, 그 보고서에 정정 고지를 붙였다**(§4).

## 1. (1) 전수 — 인용된 SPEC 37 중 기록 없는 것 5

방법: REQ 접두에서 SPEC 이름을 **추측하지 않았다**(`LXSEQ3` → `LXSEQ-003` 같은 자리에서
틀린다). 대신 모든 SPEC 문서에서 그 REQ 를 찾아 소유자를 정했다 — 못 찾으면 그것이
죽은 인용이다. 한 술어가 두 물음(소유자 · 실재)에 같이 답한다.

    살아 있는 코드(server·console·ui·tools·src)가 인용하는 고유 REQ   381
    인용된 SPEC                                                        37
    그중 progress.md 없는 것                                            5

| SPEC | 인용 REQ 수 | progress | plan | acceptance |
|---|---|---|---|---|
| FXGEN-001 | 10 | **-** | **-** | **-** |
| TRUNCATE-001 | 10 | **-** | O | O |
| SPATIALMEM-001 | 9 | **-** | **-** | **-** |
| IMGLAYOUT-001 | 4 | **-** | **-** | **-** |
| RESTORE-001 | 1 | **-** | **-** | **-** |

🔴 **`TRUNCATE-001` 은 t144 의 tier 축이 「OK」로 낸 자리다**(M, md 4개, 계약 충족).
tier 는 채웠는데 진행 기록이 없고, 살아 있는 코드가 10개 REQ 를 인용한다.
**두 축이 또 서로 다른 것을 잡는다** — t144(tier) ∩ t158(인용) 은 4건이고, 각 축이
상대가 못 보는 것을 하나씩 갖는다(t158→TRUNCATE, t144→PRESETGUARD-002 등 인용 없는 위반).

## 2. 🔴 무게 구분 — 예외를 정당화하는 인용은 4자리, 전부 FXGEN

인용이라고 다 같지 않다. 문제가 되는 형태는 **안전장치의 예외를 정당화하는** 인용이다
(t144 이 FXGEN 축에서 본 것). 전수하니:

    server/tests/test_fx_boundary.py:612    REQ-FXGEN-016 grants ONE asset the fx tool
    server/tests/test_overlap_preserve.py:96   granted exception — REQ-FXGEN-017 (b)
    server/tests/test_overlap_preserve.py:579  narrower APPEND-ONLY grant (REQ-FXGEN-017 (b))
    server/tests/test_overlap_preserve.py:608  The 2026-08-15 grant (REQ-FXGEN-017 (b))

**넷 전부 FXGEN-001 이다.** 나머지 넷(TRUNCATE·SPATIALMEM·IMGLAYOUT·RESTORE)의 인용은
**출처 주석**이다 — 「이 코드가 왜 있는가」이지 「이 방어를 왜 풀어도 되는가」가 아니다.

> **[정정 고지 — 2026-08-30, t160 이 덧붙였다. 위 문단은 한 글자도 고치지 않았다.]**
>
> **「넷 전부 FXGEN」이 틀렸다. `TRUNCATE-001` 도 승인을 지고 있다.**
>
>     server/tests/test_songcue_bundle.py:153
>     # SPEC-COPILOT-TRUNCATE-001 (2026-08-05, user-approved) — granted exception,
>
> 못 본 이유는 **한국어가 아니라 인용 형태**였다. 위 조사의 우주가 `REQ-<도메인>-<번호>`
> 였는데 이 승인은 **SPEC-ID 를 인용한다.** 술어가 REQ 를 요구하니 애초에 후보에 안 들었다.
> 같은 파일에 승인이 셋 더 있고(`:141` GROUPGEN-001 · `:175` 타임코드), **파일 자체가
> 위 조사에 안 들어왔다** — `test_overlap_preserve.py` 축만 봤다.
>
> 정정된 수: 승인을 지는 **기록 없는 SPEC 은 2개**(FXGEN-001 · TRUNCATE-001).
> 전수와 대조군: `.moai/reports/t160/korean-grant-vocab.md`.

⚠️ **계기 주의**: 처음에 「예외」로 grep 했더니 13자리가 나왔는데, 그중 9자리는
**언어의 예외**(「행 검증 실패는 예외로 새어나가지 않는다」)였다. 한국어 「예외」가 두
뜻으로 잡힌다 — 술어를 영어 `grant` 로 좁혀야 승인만 남는다.

### 2.1 분모 — 대부분의 승인은 REQ 없이 정당화된다

    test_overlap_preserve.py 안의 "granted"        28회
    그중 REQ 를 근거로 드는 것                       3회

**나머지 25회는 SPEC REQ 를 안 든다.** 감독 승인 날짜 + 기계적 핀(이름 고정·digest·
정확 행 쌍)으로 정당화된다. 즉 **REQ 인용은 이 저장소의 표준 정당화 수단이 아니다.**

## 3. (2) 검산 경로 — 이미 대체돼 있다

FXGEN 승인 둘의 **집행**을 읽었다:

    _RULEBOOK_GRANTED_ADDITIONS  -> "…/33_effect_editors.md" 를 **경로 이름으로** 고정
    _RULEBOOK_GRANTED_APPEND     -> "…/31_choreography_patterns.md"
    _RULEBOOK_APPEND_HEADING     -> "### OBSERVED EFFECT — live validation V1~V7 …"
                                    추가 블록의 **헤딩 문자열**까지 고정
    + 삭제 0 요구 (기존 행 번호 인용 :29 :75 :80 :85-89 :100 :111 :115 :236-241 보존)
    + test_the_only_rulebook_changes_are_the_granted_ones 가 단언

**집행은 전부 기계적이다.** 파일 이름·헤딩 문자열·삭제 0 이 바이트 단위로 좁힌다.
REQ 인용은 그 옆의 **근거 서술**이고, 없어도 게이트가 무엇을 허용하는지는 확정된다.

**판정: 기록 복원 불필요.** 기록이 있으면 더해지는 것은 **집행이 아니라 서사**다 —
감독이 왜 그 예외를 승인했는지, 어떤 대안을 봤는지. 그것은 값이 있지만 **안전 축이
아니다.**

## 4. 🔴 t144 의 내 문장을 정정했다

t144 보고서 §2 가 이렇게 닫았다:

    ⚠️ PRESERVE 예외가 왜 정당한지 검산하려면 진행 기록을 봐야 하는데 그게 없다.

**너무 셌다.** 검산은 진행 기록이 아니라 §3 의 핀으로 된다. 원문은 고치지 않고
**정정 고지**를 붙였다(`.moai/reports/t144/tier-contract-audit.md`) — 내가 그렇게
주장했다는 사실 자체가 기록이고, t142·t154 에서 세운 처분 그대로다.

카드가 「안전장치가 무효다로 올려 쓰지 마라」고 경고했는데, **정작 올려 쓴 것은 내
앞 카드였고 이번 카드가 그것을 내렸다.**

## 5. (3) 죽은 인용 0 — 대조군으로 검출력 확인

    죽은 인용(어느 SPEC 문서에도 없는 REQ)   0
    spec.md 엔 없고 다른 SPEC 문서에만 있는 것 0

🔴 **0을 그냥 안 믿었다.** `server/lxseq/preset_parser.py` 맨 위에 `REQ-ZZTOP-999` 를
심고 다시 돌리니:

    === 죽은 인용: 1 ===
       REQ-ZZTOP-999   인용 1 곳  예: server/lxseq/preset_parser.py

**계측기가 실제로 잡는다.** 그러니 위 0은 「없다」이지 「안 보인다」가 아니다.
복원 확인: `git status --porcelain` 0줄.

## 6. 안 잰 것

1. **인용의 무게를 `grant` 문자열로만 갈랐다** — 승인을 다른 말로 적은 자리(예:
   「완화한다」·「허용한다」)가 있으면 §2 의 「4자리」가 늘어난다. 한국어 「예외」는
   두 뜻이라 빼야 했고, 그 대가로 한국어로 적힌 승인은 못 봤다.
2. **`.claude/` 아래 규칙 파일의 인용** — 살아 있는 **코드**(server·console·ui·tools·src)만
   훑었다. 규칙·스킬 문서가 REQ 를 인용하는 자리는 안 봤다.
3. **인용된 REQ 가 그 SPEC 안에서 실제로 그 내용인지** — 문자열 실재까지만 봤다.
   REQ 번호는 맞는데 내용이 딴 것을 가리키는 경우는 안 쟀다(FXGEN 둘만 본문을 읽었다).
4. **TRUNCATE-001·SPATIALMEM-001 의 인용 10·9개가 무엇을 근거로 드는지** — 승인이
   아니라는 것까지만 봤고 각 인용의 성격은 안 팠다.
5. **`progress.md` 가 있는 32개 SPEC 의 기록이 실제로 검산에 쓸 만한지** — 존재만 봤다.
