# SPEC-COPILOT-SHEETPIPE-001 — 진행 기록 (progress)

문서 상태: draft (v0.3.0, 2026-08-24) · **Tier M · 통과 임계 0.80** · 칸반 카드 t10 · **분할 B(전달경로)**

> **읽는 순서.** ① `spec.md` §A(개요 · 사전 확정 사실) → ② `spec.md` §F(세 성질 — **함정이 여기 있다**) → ③ `plan.md` §A.1(뒤집힐 수 있는 결정 넷) · §A.4(**닫힌** 결정 ① — A의 `target` 태그 재정) → ④ `spec.md` §G(등재 7지점) → ⑤ `acceptance.md` §C.
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
  decisions_resolved: 8      # plan.md §A.3 (A~H) — B 자신의 결정
  clarification_markers: 0   # plan.md §A.4 ① 2026-08-23 A 재정으로 닫힘
lead_allocation:
  req: 8      # 실측 9 — +1의 사유는 spec.md §B 머리의 [HARD] 주가 소유한다
  ac: 11      # 일치
baseline_measured: null      # 의도적으로 비어 있음 — M0가 이 워크트리에서 직접 잰다
assumptions_open: [ASSUMPTION-78, ASSUMPTION-79]
mutation_ledger_planned: 8   # AC-003 · 004 · 005(문구 :555) · 005(앵커 주석) · 006 · 009 · 010 · 011
plan_audit:
  verdict: PASS-WITH-DEBT
  score: 0.91                # Tier M 임계 0.80
  must_pass: 7/7
  debts_closed: 6            # D1~D6 (v0.3.0) — 전부 문서 편집, 코드 변경 0
```

### 좌표 실측 기록 (본 세션 · `grep`)

`spec.md` §H가 좌표표를 소유한다. 본 세션에서 **11건을 전수 재측정**했고, 정정 4건이 나왔다:

| 대상 | 앞선 기록 | 실측 | 왜 어긋났나 |
|---|---|---|---|
| `_UploadedVectorworksExport` | `2492` | **`2493`** | `@dataclass` 데코레이터를 클래스 시작으로 셈 |
| `LayoutImageUpload` | `2511` | **`2512`** | 같음 |
| `protocol.ts` 빌더 둘 | `502` · `517` (본 세션 초안) | **`503`** · **`519`** | `sed` 출력에서 눈으로 셈 — `grep`으로 재서 잡음 |
| ~~`test_overlap_preserve.py`의 `base..HEAD`~~ | ~~`427` · `446` · `456`~~ | **철회 — 아래 참조** | 내 정정이 틀렸다 |

**철회 (v0.2.0) — 내가 A를 고친 것이 틀렸다.** v0.1.0은 A의 `:446`을 두고 "그 파일에 `base..HEAD`가 없다"고 적었다. **거짓이다.** `:446`은 `_PRECHK_BASE`를 쓰는 진짜 `..HEAD` 지점이며, 내 grep이 `{base}..HEAD`라는 **내 변수명**만 훑어 보이지 않았을 뿐이다. 리드가 변수명을 벗기고 재서 확정한 총계는 **22곳**이다:

```
grep -cE '\.\.HEAD' server/tests/test_overlap_preserve.py   → 22
```

내 셋(`427 · 456 · 464`)도 A의 셋(`427 · 446 · 456`)도 **둘 다 부분집합**이었고, 각자 자기 변수명만 매칭했기 때문이다. **좁은 패턴의 히트 수는 총계가 아니라 하한이다** — 이것은 §C.0 계수 규약 2(부정 grep은 부재의 증거가 아니다)의 세 번째 얼굴이며, A가 자기 함정 목록에 그 형태로 싣는다. 본 SPEC의 두 인용(`plan.md` §A.5 · `AC-SHEETPIPE-011`)은 낱개 좌표를 버리고 **총계와 그것을 낸 명령**으로 바꿨다.

**정정 하나 더 — 인용 경로.** A는 헤더 없는 내보내기 근거를 `README.md:85-95`로 적었다. 디렉터리가 없어 저장소 루트의 다른 문서(안전 게이트 절)로 풀린다. 실제 원본은 **`server/tests/fixtures/vwx/README.md:84-95`**다.

**교훈 세 줄** — ① **좌표는 눈이 아니라 `grep`이 낸다.** ② **결정적인 줄을 인용하고, 범위는 양끝을 잰다.** ③ **좁은 패턴의 히트 수는 총계가 아니라 하한이다** — 남의 좌표를 정정하기 전에 내 패턴이 그 사람의 표기까지 덮는지 먼저 본다(위 철회가 그 값을 치렀다).

### 등재 지점 실측 (본 세션)

`vectorworks_autopatch`를 추적해 **7지점**으로 확정했다(`spec.md` §G가 표와 배제 기준을 소유). 앞선 SPEC의 "4지점"(`REQ-LXSEQ-010`)은 낡았고, 빠진 셋 중 둘(`test_tools.py`의 리터럴 · 트립와이어)은 **툴 이름을 문자열로 담지 않아 첫 grep에 영원히 걸리지 않는다**.

독립 확인: `TOOL_NAMES` 파싱 결과 **34개**이며 `upload_vectorworks_export`는 **그 안에 없다**. 이 한 번의 측정이 두 가지를 동시에 준다 — `test_tools.py:172`의 리터럴 `34`가 옳다는 것과, A 레지스트리 `target` 열이 **두 종을 담는다**는 것(`plan.md` §A.4 ①의 근거이자, 그 재정의 리드측 독립 확인과 일치한다).

### 채무 정리 실측 (v0.3.0 · plan-audit 0.91)

| 채무 | 명령 | 결과 |
|---|---|---|
| **D1** 예견인가 사고인가 | `git log -1 --format='%s' 43b1b04` | `feat(SPEC-COPILOT-IMGLAYOUT-001): M4+M5 …` — **`fix`가 아니다** |
| **D1** docstring 서법 | `sed -n '3360,3361p' server/web/session.py` | `would therefore freeze` — **가정법** |
| **D1** 아티팩트 언급 | `grep -rc 'LayoutImageUploadView\|freeze\|얼어' .moai/specs/SPEC-COPILOT-IMGLAYOUT-001/` | `contract.md:0` · `spec.md:0` — **0건** |
| **D2** 형제 문구 | `grep -n 'Vectorworks' ui/src/App.tsx` | `:551` · `:555` · `:559` — **셋** |
| **D2** vitest 델타 | `grep -rln 'Vectorworks export는' ui/src/` | `App.tsx` 하나 — 테스트 단언 **0건** |
| **D3** 앵커 판별력 | `grep -c 'SPEC-COPILOT-SHEETPIPE-001' ui/src/App.tsx` | **0** — 검사가 오늘 빨갛다(판별력 있음) |
| **D5** 이름 변경 비용 | `git grep -l 'vectorworks_export_upload'` | **16파일**(코드·계약 8 + 문서 8) |
| **D5** 빌더 수 | `grep -c 'export function buildVectorworksExportUpload' ui/src/protocol.ts` | **1** — "빌더 둘"은 하나 많았다 |

**D1이 남긴 일반형은 §C.0 규약 6이 든다.** 이 카드에서 **세 번째 형태**다 — `columns.py` 오귀속(옮겨간 문서를 가리킴) · `:446` 철회(좁은 패턴을 총계로 읽음) · 그리고 이번(방어 코드의 설명문을 역사로 읽음). 셋 다 **읽은 것의 종류를 잘못 판정한** 결과다.

### 미해소 항목

| 항목 | 상태 | 해소 시점 |
|---|---|---|
| A의 태그 재정이 **A 쪽 코드에** 반영됐는가 | 미확인 | M0 5 — 재정은 문서에 적힌 것이지 A의 코드에 있는 것이 아니다 |
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
