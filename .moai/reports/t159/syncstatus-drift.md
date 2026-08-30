# t159 — 도구가 걸었지만 결함이 아니다. 그리고 그 처방을 따르면 거짓이 생긴다

- 카드: t159 · 도구 축 판정 · 기준 `3adb20a` · 브랜치 `WT-syncstatus-drift`
- **콘솔 접촉 0 · 코드 변경 0 · SPEC 파일 생성/수정 0.** 판정까지다.
- 상태 변경 **0** — 측정은 전부 읽기와 `--dry-run` 으로 했다.

## 0. 결론 셋

1. **도구의 관측은 참이다.** §E.2·§E.4·`sync_commit_sha` 가 실재하고 `status != completed` 다.
2. **도구의 추론은 틀렸다.** 마커 실재는 **감사 통과**가 아니다. 같은 §E.4 블록에
   `sync_audit: FAIL 0.86` · `ac_fail: 1` · `open_defects: 1` 이 적혀 있다.
3. 🔴 **도구의 처방은 거짓을 만든다.** `--dry-run` 으로 재 보니 `status → completed` 를
   적용하려 하고, **선행조건이 안 막았다**(exit 0).

## 1. 이름이 아니라 출력 전문을 읽었다

    [MUST-FIX] SPEC-COPILOT-LXSEQ-001 (V3R6) — SyncStatusDrift
               Remediation: moai spec close SPEC-COPILOT-LXSEQ-001 --backfill-only
               Reason: §E.2 + §E.4 + sync_commit_sha present (sync complete) but status != completed

주장이 네 조각이라 하나씩 따로 쟀다:

| # | 도구의 주장 | 실측 | 판정 |
|---|---|---|---|
| ① | `status != completed` | `spec.md:5  status: implemented` | **참** |
| ② | §E.2 실재 | `progress.md:164  ## §E.2 Run-phase Evidence` | **참** |
| ③ | §E.4 실재 | `progress.md:930  ## §E.4 Sync-phase Audit-Ready Signal` | **참** |
| ④ | `sync_commit_sha` 실재 | `progress.md:949  sync_commit_sha: 2b328c6` 형태의 **진짜 SHA**(placeholder 아님) | **참** |

**네 조각 다 참이다.** 그런데 결론이 틀렸다.

## 2. 🔴 도구가 못 읽는 것이 바로 옆 줄에 있다

같은 §E.4 블록, 몇 줄 아래:

    sync_audit: FAIL 0.86          # 재판정 (HEAD 07bc93b, 수정 후)
                                   # FAIL 동인은 오직 AC-LXSEQ-016
    ac_fail: 1                     # AC-LXSEQ-016
    open_defects: 1                # D2(F1) → 카드 t11

그리고 `acceptance.md` 가 **왜** `implemented` 인지 명시한다:

    acceptance.md:3    17건 중 16 PASS · AC-LXSEQ-016 FAIL
                       → §D DoD 대로 `implemented`에서 멈추고 `completed`가 아니다
    acceptance.md:298  AC-LXSEQ-016이 미수행이면 `implemented`는 가능하나
                       `completed`는 불가(**감독 결정 ②**)

**`implemented` 는 표류가 아니라 의도다.** 감독 결정으로 고정된 상태이고, 그 사유가
문서에 적혀 있다. `AC-LXSEQ-016` 은 **사용자가 onPC 실기로 수행**하는 유일한 라이브 AC다.

⚠️ 사유였던 결함 D2 는 나중에 닫혔다(`09afff7 fix(SPEC-COPILOT-PARITY-001): … D2 핸들↔이름
정합`, PARITY-001 status `completed`). **그래도 `completed` 가 정당해지지 않는다** —
AC-016 은 라이브 재수행과 그 기록을 요구하는데 **재수행 기록이 0건**이다
(`git grep "AC-LXSEQ-016" -- .moai/reports` → 빈 출력).

## 3. 🔴 처방을 dry-run 으로 쟀다 — 선행조건이 안 막는다

`moai spec close --help` 는 선행조건에 **「all AC PASS」**가 있다고 적는다. LXSEQ-001 은
`ac_fail: 1` 이므로 거절돼야 한다. **추측하지 않고 물었다** — `--dry-run` 은 스테이징·커밋
없이 미리보기만 하므로 안전장치를 쏘는 것이 아니다:

    $ moai spec close SPEC-COPILOT-LXSEQ-001 --backfill-only --dry-run
    [dry-run] SPEC SPEC-COPILOT-LXSEQ-001 — preview only, no staging performed
    Would apply the following transitions:
      progress.md:§E.5.mx_commit_sha → <derived-from-recent-mx-commit>
      spec.md:frontmatter.status → completed
      progress.md:§E.3.status → completed
    exit=0
    작업트리 변경: 0줄

**exit 0.** 선행조건이 안 막았고, `status → completed` 를 적용하려 한다.
`--force`(선행조건 우회)는 **안 썼다** — 권고된 그대로 `--backfill-only` 만 썼다.

**즉 MUST-FIX 의 처방을 그대로 따르면, 감독 결정이 금지한 `completed` 가 찍히고
라이브 검증을 안 한 SPEC 이 완료로 표시된다.** 이것이 이 카드의 무게다.

## 4. 덤 — 처방이 은퇴한 절을 쓰려 한다

dry-run 첫 줄이 `progress.md:§E.5.mx_commit_sha` 를 쓰겠다고 한다. 그런데:

- LXSEQ-001 의 `progress.md` 에 **§E.5 가 없다**(헤딩은 §E.1 · §E.2 · §E.3 · §E.4 · §E.1a)
- 정본 규칙(`spec-frontmatter-schema.md` § progress.md Section Map)은 **§E.5 를 RETIRED**
  로 표시하고 「do NOT author new §E.5 sections」라 적는다. 현행은 **3-phase close** 다
- `moai spec close --help` 도 「**4-phase** close preconditions (§E.2 … + **§E.5** Mx section
  present)」라고 적는다

**도구가 4-phase 모델에 남아 있고, 정본 규칙은 3-phase 로 옮겼다.** 그러면 이 처방은
은퇴한 절에 필드를 쓰는 셈이다. (도구 소스가 이 트리에 없어 구현은 못 읽었다 — 판정은
`--help` 문면과 dry-run 출력이라는 **관측**에 근거한다.)

## 5. 판정

| 물음 | 답 |
|---|---|
| 결함이 실재하나 | **아니다.** `implemented` 는 감독 결정으로 고정된 정당한 상태다 |
| 도구가 틀렸나 | **관측은 맞고 추론이 틀렸다.** 마커 실재 ≠ 감사 통과 |
| 왜 틀리나 | 판별식이 **존재**를 읽고 **결과**를 안 읽는다. 감사 판정·실패 AC 수·미해결 결함이 전부 같은 블록에 있는데 안 본다 |
| 처방을 따라도 되나 | **안 된다.** dry-run 실측상 `completed` 를 찍고 선행조건이 안 막는다 |

t136 이 「도구가 안 걸었다 ≠ 결함이 아니다」를 세웠다면, 이 건은 그 **역**이다 —
**「도구가 걸었다 ≠ 실재한다」.** 그리고 이번 쪽이 더 위험하다: 앞의 실패는 **놓치는**
것이고, 이쪽은 처방을 따르면 **거짓을 새로 만든다.**

## 6. 안 잰 것

1. **도구 구현** — `moai` 바이너리의 Go 소스가 이 트리에 없다(`grep SyncStatusDrift`
   → 0건). 「판별식이 감사 결과를 안 읽는다」는 **출력과 `--help` 문면에서 추론**한 것이지
   소스를 읽은 것이 아니다. 소스를 보면 더 정확한 진단이 나온다.
2. **다른 SPEC 에서도 같은 오탐이 나는지** — MUST-FIX 가 저장소 전체에 이 1건뿐이라
   표본이 하나다. 다른 저장소·다른 상태에서 이 판별식이 어떻게 도는지는 모른다.
3. **`--force` 경로** — 안 눌렀다. 선행조건을 우회하는 플래그라 dry-run 으로도 안 건드렸다.
4. **AC-LXSEQ-016 을 지금 통과시킬 수 있는지** — D2 는 닫혔으니 라이브 재수행이 가능할
   수 있다. 그것은 콘솔 작업이고 이 카드 범위 밖이다. **재수행하면 `completed` 가
   정당해진다** — 그때는 처방이 아니라 절차가 답이다.
5. **`spec.md` §A Lifecycle Sync row** — dry-run 이 안 건드린다고 했으나 확인 안 했다.
