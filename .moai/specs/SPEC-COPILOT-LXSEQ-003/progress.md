# SPEC-COPILOT-LXSEQ-003 — 진행 기록 (progress)

카드 t69. 아티팩트 3종(spec · plan · acceptance)은 plan-phase 에서 작성됐다.
이 문서는 그 이후의 진행을 기록한다.

---

## A. 플랜 단계 요약

| 항목 | 값 |
|---|---|
| Tier | M (3 아티팩트) |
| REQ | 16건 (상한 16) |
| AC | 14건 (상한 16, 실기 1건 포함) |
| 마일스톤 | M0~M4 |
| 근거 조사 | `.moai/specs/SPEC-COPILOT-LXSEQ-002/t68-path-survey.md` (카드 t68) |
| 범위 | 프리셋 **Dim 6 · Col 8 · Beam 5 = 19건**. Pos 8 제외(spec.md §C.3) |

### A.1 이 SPEC 이 답한 위임 판정 1건

리드가 t69 배차서에서 위임한 「레지스트리 행 정합」 — **spec.md §A.3 에서 판정했다.**
결론: 행 3개는 `REQ-FILEARG-017` 위반이 아니다(근거 셋). 그리고 `FILEARG-001/spec.md:82` 의
「각각 한 행씩」은 부정확한 산문이므로 정정을 **별건 처방**으로 분리했다 — 본 SPEC 은 고치지 않는다.

### A.2 이 SPEC 이 열어 둔 것 (정한 척하지 않는다)

- 배치 크기 기본값 — M2 가 정하고 M4 가 바꾼다
- RIG ID ↔ 슬롯 대응의 저장 형태 — 산출물로 시작, LXSEQ-004 가 상태로 올릴지 정한다
- `/Universal` 문형 — 미검증 문법(ASSUMPTION-02), M4 가 답한다
- M4 세션 횟수 — 분할 투입 결과에 달렸다

---

## §E.1 Plan-phase Audit-Ready Signal

    plan_status: audit-ready
    plan_complete_at: 2026-08-25

산출: `spec.md`(248행) · `plan.md`(156행) · `acceptance.md`(168행).
콘솔 접촉 0 · 코드 변경 0 — 이 카드는 문서 작성이다.

### 검증 (이 트리에서 잰 것)

- 프론트매터 필수 12필드 충족 12/12 · `phase` 는 금지 토큰 아님
- `Out of Scope` 는 h3(`### C.2` · `### C.3`) — h2 단독이 아니다
- 재료 실측: `preset-dim` 6행 · `preset-col` 8행 · `preset-bm` 5행 = **19** (헤더 제외 행수)
- 열 집합 실측: dim `ID,Name,Level,Purpose` · col `ID,Name,Value,Purpose` ·
  bm `ID,Name,TargetGroup,Value` · pos `ID,StageMeaning,TargetGroup,RecordGuide`

### 미검증 (Gap)

1. **테스트를 돌리지 않았다** — 이 카드는 문서다. 코드가 없으므로 돌릴 것이 없다.
2. **t72 · t66 의 바이트 실측은 인용이다** — 리드 보고이며 이 SPEC 의 관측이 아니다.
   spec.md §G.1 에 그렇게 표기했다.
3. **era 분류는 재측정으로 해소했다.** 이 파일이 없을 때 `moai spec audit` 은 `V2.x` 를 냈고,
   이 파일을 만든 뒤 다시 돌리니 **`V3R2-R4`** 로 바뀌었다(기준선 LXSEQ-002 와 동일).
   즉 분류를 가른 것은 `progress.md` 의 `§E.1` 마커다 — 「Gap 으로 남긴다」가 아니라 **닫았다**.
   남는 것은 하나: 이 SPEC 이 목표하는 V3R6 는 run·sync 단계의 `§E.2`~`§E.4` 가 생겨야 도달한다.
