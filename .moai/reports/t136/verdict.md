# t136 판정 — SPEC-COPILOT-COLORPRESET-001 장부 대조

카드: t136 · 판정 카드(코드 변경 없음) · 트리 `.claude/worktrees/t136` · 브랜치 `WT-colorpreset-ledger`
base `82395fa` (리드가 지정한 값, 되읽어 확인) · 콘솔 미사용

🔴 **status 는 건드리지 않았다.** 전이는 manager-docs 소유이고 이 카드는 판정까지다.

---

## 물음 ① — progress.md 의 M0~M4 완료 표시가 실제 코드/테스트와 맞나

### 판정

**갈린다. M1~M3 는 실증됐고, M0·M4 는 코드로 검증 불가이며 전제가 노화했다.
그리고 완료 표시가 앉은 자리 자체가 스키마 밖이다.**

progress 를 증거로 쓰지 않고 커밋을 열었다.

### 1-A. M1~M3 — 실증됨 (주장 4개 전부 확인)

    git log -1 --format='%H %s' ef0103a
    -> ef0103ab1c5315cc9e17a60ac1be9fcd43b1d357
       feat(SPEC-COPILOT-COLORPRESET-001): 표준 팔레트 컬러 프리셋 10종 — M0~M3

| 커밋이 주장한 것 | 잰 명령 | 출력 | 판정 |
|---|---|---|---|
| 파일 3개만 접촉 (`tools.py·spatial·lua 무접촉`) | `git show --stat ef0103a` | `progress.md` / `test_web_session.py` / `session.py` — 3 files, 1178+ 82- | ✅ |
| 테스트 +21건 | `git show ef0103a -- server/tests/test_web_session.py \| grep -c '^+    def test_'` | `21` | ✅ |
| 분해 「판별 7 + 저장/재생성 14」 | 위 목록 육안 대조 (앞 7건이 판별 계열) | 7 + 14 = 21 | ✅ |
| 「기존 포지션/FX 테스트 **무수정**」 = REQ-006 증거 | `git show --numstat ef0103a -- server/tests/test_web_session.py` | `548  0` — **삭제 0줄** · 삭제된 test 함수 `0` | ✅ |

오늘도 살아 있고 통과하는가:

    grep -o 'def test_[a-z_]*' server/tests/test_web_session.py | sed 's/^def //' | sort -u   -> 327개
    comm -23 <커밋이 추가한 21개> <오늘 327개>                                                 -> 0 (누락 없음)

    .venv/bin/python -m pytest server/tests/test_web_session.py -q
    -> 406 passed in 5.36s

    .venv/bin/python -m pytest -q
    -> 10435 passed, 12 skipped, 1 warning in 156.67s

21개가 전부 이 파일 안에 있고 파일이 전건 그린이므로 21개는 통과한다.

⚠️ progress 의 「전체 스위트 **9080** 그린」은 2026-08-16 값이다. 오늘 값은 10435 로
**다른 트리·다른 시점**이다. 9080 을 재현하려면 그 커밋을 체크아웃해 돌려야 하고
안 했다 — gap 이지 불일치가 아니다(2주간 증가와 모순되지 않는다).

### 1-B. M0·M4 — 코드로 검증 불가 + 전제 노화

둘 다 라이브 콘솔 관측이다. 커밋에 대응 산출물이 없고, 있을 수도 없다.

M0 이 실측이라 적은 값: 「이 리그 **41대**」 · 「fid 40·41 제외 = 2대」 · 「풀 4 = `Color`」
M4 가 실측이라 적은 값: 「41대 중 39대 적용」 · 「기대 10개 중 10개」 · 4.11~ 라벨 실재

🔴 **그 전제가 노화했다.** 오늘 t96 에서 내가 직접 잰 바로는 콘솔에 로드된 쇼파일이
2026-08-26 회차의 쇼와도 다르다 — `DataPool/Groups` 18→5, `DataPool/PresetPools/1` 6→20,
`DataPool/Plugins` 11→5 (증거: `.moai/reports/t96/reimport-recheck-20260830.md`).
플러그인·프리셋·그룹이 `.show` 안에 사는 이상, M0/M4 가 잰 리그는 지금 로드된 리그가
아닐 가능성이 높다.

⚠️ 관련해 리드가 t105 실측이라며 `Patch/Stages/1/Fixtures childCount 80` 을 전했다.
M0 의 41 과 다르다. **다만 이건 내가 안 쟀다 — 리드 보고를 옮긴 값이다.** 이 카드는
콘솔 불필요로 배차됐고 콘솔은 run 레인이 쓰는 중이라 확인하지 않았다.

M4 는 스스로 부작용도 적어 두었다 — 「E2E 2회 실행으로 4.11~4.30 에 두 벌 저장됨,
한 벌은 수동 삭제 가능」. 이 잔여 콘솔 상태가 정리됐는지는 **미검증**이다.

### 1-C. 🔴 완료 표시가 앉은 자리가 스키마 밖이다 (구조 소견)

`progress.md` 전문을 열어 보니 섹션이 `## §E. 라이브 판정` · `### §E.1 M0` ·
`## §F. 마일스톤 상태` 셋뿐이다.

정본 섹션 지도(`spec-frontmatter-schema.md` § progress.md Section Map)에 대면:

| 스키마가 요구 | 이 SPEC | 결과 |
|---|---|---|
| `§E.2 Run-phase Evidence` | **없음** | M1~M3 의 실행 증거가 지정된 자리에 없다 |
| `§E.3 Run-phase Audit-Ready Signal` | **없음** | run 단계 완료 신호 없음 |
| `§E.4 Sync-phase Audit-Ready Signal` | **없음** | sync 미도달과 정합 |
| `§F` = Phase 4 Mode Selection | `§F. 마일스톤 상태` 로 사용 | 글자 충돌 |

즉 M1~M4 의 `✅` 는 **스키마가 지정한 run-evidence 섹션이 아니라 산문**에 있다.
내용은 위 1-A 로 실증됐지만, 자리는 정본과 다르다.

이것이 `moai spec audit` 이 이 SPEC 을 **V3R2-R4** 로 분류한 이유이기도 하다 —
휴리스틱 `H-2 (progress.md without §E.* markers)` 가 §E.2~§E.5 부재로 발동한다.

### 1-D. status 불일치 (보고만, 손대지 않음)

    frontmatter status: draft      (spec.md)
    progress:           M0~M4 ✅ · plan_status: audit-ready
    ef0103a:            feat(SPEC-...): ... M0~M3   ← run 단계 커밋

스키마상 `draft → in-progress` 는 첫 run 단계 커밋에서 manager-develop 이 수행한다.
`ef0103a` 가 그 커밋인데 status 는 `draft` 로 남았다.

⚠️ **다만 도구는 이것을 결함으로 걸지 않는다.** 아래 ② 의 감사 결과대로 이 SPEC 은
grandfathered(V3R2-R4) 라 drift 검출 대상이 아니고, 실제로 MUST-FIX 가 0건이다.
고칠지 말지는 정책 판단이고, 전이 자체는 이 카드 소유가 아니다.

---

## 물음 ② — acceptance.md 부재가 결함인가, 그 시기 규약인가

### 판정

**결함이다. 규약이 아니다.** 도구 자신의 시대 묶음으로 재도 그렇다.

### 2-A. 먼저 내 첫 대조군이 무효였다 (자기 정정)

날짜 근접으로 대조군을 잡았다 — 같은 날(08-16) PRESETGUARD-001 이 `tier: M` 이고
acceptance.md 를 갖고 있으니 규약이 아니다, 로 갈 뻔했다.

    moai spec audit --json  (시대 라벨)
    SPEC-COPILOT-COLORPRESET-001   V3R2-R4
    SPEC-COPILOT-PRESETGUARD-001   V3R6      <- 같은 날인데 다른 시대
    SPEC-COPILOT-PRESETGUARD-002   V2.x      <- 같은 날인데 또 다른 시대
    SPEC-COPILOT-LDGUIDE-001       V3R6
    SPEC-COPILOT-FXGEN-001         V2.x

**같은 날이 같은 시대가 아니다.** 시대 휴리스틱은 생성일이 아니라 progress.md 의
§E 구조를 본다. 그래서 날짜 기반 대조군은 도구 자신의 잣대로 무효다 — 폐기했다.

### 2-B. 같은 시대(V3R2-R4) 전수 — 5건 중 4건이 갖고 있다

    (moai spec audit --json 으로 V3R2-R4 를 뽑고, 각 디렉터리의 tier 와 acceptance.md 존재를 대조)

| SPEC | tier | 요구되나 | acceptance.md |
|---|---|---|---|
| AXISCORE-001 | S | 아니오 | **YES** |
| **COLORPRESET-001** | **M** | **예** | **no** |
| CUETIME-001 | (없음 → L 간주) | 예 | **YES** |
| LXSEQ-002 | M | 예 | **YES** |
| PRESETIDEM-001 | S | 아니오 | **YES** |

같은 시대 5건 중 **4건이 갖고 있다.** 그중 둘(AXISCORE-001·PRESETIDEM-001)은 **Tier S 라
요구되지도 않는데** 썼다 — 그 시기 규약은 「덜 쓰는」 쪽이 아니라 **더 쓰는** 쪽이었다.
COLORPRESET-001 은 요구되는 Tier M 이면서 **유일하게 없는** 항목이다.

### 2-C. 규칙이 요구하는가 — 요구한다

    sed -n '1,25p' .moai/specs/SPEC-COPILOT-COLORPRESET-001/spec.md
    -> tier: M

`spec-workflow.md` § SPEC Complexity Tier: Tier M = **3 파일** (spec.md + plan.md +
**acceptance.md**). SPEC 이 스스로 `tier: M` 을 선언했으므로 3파일 계약을 택한 것이다.
실제 디렉터리는 `plan.md` · `progress.md` · `spec.md` — acceptance.md 가 없다.

부수 소견(범위 밖, 보고만): 같은 대조에서 FXGEN-001 은 `tier: L`(5파일 요구)인데
`research.md` · `spec.md` 둘뿐이고, PRESETGUARD-002 는 `tier: S`(2파일 요구)인데
`spec.md` 하나뿐이다. 이 카드의 판정 대상은 아니다.

### 2-D. 도구는 이 축을 안 본다 (계기 경계 명시)

`moai spec audit` 은 **progress.md 의 §E 구조로 시대를 나누고 lifecycle drift 를
잡는다.** tier 산출물 세트는 보지 않는다. 그래서 이 도구를 「acceptance.md 가
있어야 하나」의 답으로 인용하면 안 된다 — 옆엣것을 재는 것이다.

이 보고서는 도구를 **「같은 시대인가」를 기계적으로 확정하는 용도로만** 썼고,
「요구되는가」는 규칙(tier 표)과 파일 실재로 답했다. 두 축을 갈라 둔다.

---

## 3. 기준선 귀속

- 트리 `.claude/worktrees/t136` · `git branch --show-current` → `WT-colorpreset-ledger`
- `git log --oneline -1` → `82395fa measure(t98): address_occupied 12행 실측 …` (리드 지정 base 와 일치)
- 자체 venv (`uv sync --group dev`). 주 체크아웃 venv 를 빌리지 않았다
- 전체 스위트: 이 트리, 이 커밋에서 오늘 실행 → 10435 passed / 12 skipped / 0 failed
- `moai spec audit --json` → `audited_at: 2026-08-30T02:31:52Z`

## 4. 미검증 (Gaps)

| 안 잰 축 | 왜 |
|---|---|
| progress 의 「9080 그린」 | 2026-08-16 트리를 체크아웃해 돌려야 재현된다. 안 했다 |
| M0 의 리그 41대 · 풀 4=Color | 라이브 콘솔이 필요. 이 카드는 콘솔 불필요로 배차됐고 run 레인이 쓰는 중 |
| M4 의 E2E 관측 전부 | 위와 같음. 게다가 쇼가 바뀌어 재현도 보장 안 된다 |
| `Patch/Stages/1/Fixtures = 80` | **리드 보고를 옮긴 값이다. 내가 안 쟀다** |
| M4 잔여 콘솔 상태(4.11~4.30 두 벌) | 정리됐는지 미확인 |
| tier 규칙의 **당시** 문면 | 오늘의 `spec-workflow.md` 를 읽었다. 2026-08-16 시점 규칙 문면은 git 이력으로 안 팠다 |
| 감사 도구 계수 이상의 **원인** | 아래 5 참조. 원인 미확인 |

## 5. 잔여 위험

- ⚠️ **감사 도구 요약의 계수가 셋으로 갈린다.** 디렉터리 45 = findings 의 distinct id
  45(comm 양방향 0)인데 `total_specs` 는 **44**, `grandfathered(32) + modern_era_clean(11)`
  은 **43** 이다. 원인은 안 쟀다. 내 ② 결론은 per-SPEC 시대 라벨에만 의존하므로
  이 이상이 결론을 흔들지는 않지만, **이 도구의 총계를 인용할 때는 주의해야 한다.**
- 이 SPEC 은 grandfathered 라 MUST-FIX 가 0건이다. 「결함이다」는 **tier 계약과 동시대
  관행에 대한 판정**이지, 도구가 걸었다는 뜻이 아니다. 둘을 섞으면 안 된다.
- M0/M4 를 되재려면 쇼파일 결정이 선행돼야 한다(t96 참조). 지금 재면 다른 쇼를 재게 된다.
- 코드 변경 0줄. 되돌릴 것이 없다.
