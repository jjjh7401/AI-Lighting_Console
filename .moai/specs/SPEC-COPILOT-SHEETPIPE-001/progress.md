# SPEC-COPILOT-SHEETPIPE-001 — 진행 기록 (progress)

문서 상태: draft (v0.1.0, 2026-08-23) · **Tier M · 통과 임계 0.80** · 칸반 카드 t10 · **분할 B(전달경로)**

> **읽는 순서.** ① `spec.md` §A(개요 · 사전 확정 사실) → ② `spec.md` §F(세 성질 — **함정이 여기 있다**) → ③ `plan.md` §A.1(뒤집힐 수 있는 결정 넷) · §A.4(열린 결정 1건) → ④ `spec.md` §G(등재 7지점) → ⑤ `acceptance.md` §C.
>
> **A를 먼저 읽어야 한다.** B는 판별하지 않는다. 레지스트리 · 술어 · 신원/사용성 축 · `.mvr` 위임 계약은 전부 `SPEC-COPILOT-FILEARG-001`이 소유하며, 그 `design.md` §1~§4가 설계 논증을 든다.

---

## §E.1 Plan-phase Audit-Ready Signal

```yaml
spec_id: SPEC-COPILOT-SHEETPIPE-001
tier: M
pass_threshold: 0.80
phase: plan
artifact_set:
  required: [spec.md, plan.md, acceptance.md]   # Tier M = 3종
  emitted:  [spec.md, plan.md, acceptance.md]
  progress_md: emitted (Tier 집합에 포함되지 않음 — A의 감사 A1이 잡은 오산)
counts:
  req: 9      # grep -c "^- \*\*REQ-SHEETPIPE-" spec.md
  ac: 11      # grep -c "^### AC-SHEETPIPE-" acceptance.md
  milestones: 3
  decisions_resolved: 8      # plan.md §A.3 (A~H)
  clarification_markers: 1   # plan.md §A.4 ①
lead_allocation:
  req: 8      # 실측 9 — +1의 사유는 spec.md §B 머리의 [HARD] 주가 소유한다
  ac: 11      # 일치
baseline_measured: null      # 의도적으로 비어 있음 — M0가 이 워크트리에서 직접 잰다
assumptions_open: [ASSUMPTION-78, ASSUMPTION-79]
mutation_ledger_planned: 6   # AC-003 · 004 · 006 · 009 · 010 · 011
```

### 좌표 실측 기록 (본 세션 · `grep`)

`spec.md` §H가 좌표표를 소유한다. 본 세션에서 **11건을 전수 재측정**했고, 정정 4건이 나왔다:

| 대상 | 앞선 기록 | 실측 | 왜 어긋났나 |
|---|---|---|---|
| `_UploadedVectorworksExport` | `2492` | **`2493`** | `@dataclass` 데코레이터를 클래스 시작으로 셈 |
| `LayoutImageUpload` | `2511` | **`2512`** | 같음 |
| `protocol.ts` 빌더 둘 | `502` · `517` (본 세션 초안) | **`503`** · **`519`** | `sed` 출력에서 눈으로 셈 — `grep`으로 재서 잡음 |
| `test_overlap_preserve.py`의 `base..HEAD` | `427` · `446` · `456` (A 인용) | **`427`** · **`456`** · **`464`** | `:446`에는 그 패턴이 없다 |

**정정 하나 더 — 인용 경로.** A는 헤더 없는 내보내기 근거를 `README.md:85-95`로 적었다. 디렉터리가 없어 저장소 루트의 다른 문서(안전 게이트 절)로 풀린다. 실제 원본은 **`server/tests/fixtures/vwx/README.md:84-95`**다.

**교훈 두 줄** — ① **좌표는 눈이 아니라 `grep`이 낸다.** ② **결정적인 줄을 인용하고, 범위는 양끝을 잰다.**

### 등재 지점 실측 (본 세션)

`vectorworks_autopatch`를 추적해 **7지점**으로 확정했다(`spec.md` §G가 표와 배제 기준을 소유). 앞선 SPEC의 "4지점"(`REQ-LXSEQ-010`)은 낡았고, 빠진 셋 중 둘(`test_tools.py`의 리터럴 · 트립와이어)은 **툴 이름을 문자열로 담지 않아 첫 grep에 영원히 걸리지 않는다**.

독립 확인: `TOOL_NAMES` 파싱 결과 **34개**이며 `upload_vectorworks_export`는 **그 안에 없다**. 이 한 번의 측정이 두 가지를 동시에 준다 — `test_tools.py:172`의 리터럴 `34`가 옳다는 것과, A 레지스트리 `target` 열이 **두 종을 담는다**는 것(`plan.md` §A.4 ①의 근거).

### 미해소 항목

| 항목 | 상태 | 해소 시점 |
|---|---|---|
| `plan.md` §A.4 ① — A 레지스트리 `target` 열의 두 종 | **열림** | Implementation Kickoff Approval 전 |
| `ASSUMPTION-78` — A가 이 워크트리에 있는가 | 미검증 | M0 ① |
| `ASSUMPTION-79` — 오늘 되던 업로드가 거절되는가 | 미검증 | 운영자 이력이 있어야 닫힌다 — **B에서 닫지 않는다** |
| `baseline_measured` | 미측정 | M0 ③ |

---

## §E.2 Run-phase Evidence

_<pending run-phase>_

---

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

---

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
