---
id: SPEC-COPILOT-LDGUIDE-001
title: "조명감독 워크플로우 기준 사용 가이드 전면 개정 + 개선 제안 도출 (LD Guide)"
version: "0.5.0"
status: draft
created: 2026-08-17
updated: 2026-08-17
author: orchestrator (kanban plan session)
priority: P2
phase: "Phase 3 사용자 문서 — 감독 언어 축 재정렬"
module: "docs/user-guide.html (전면 개정), .moai/specs/SPEC-COPILOT-LDGUIDE-001/evidence.md (신규 증거 원장)"
lifecycle: spec-anchored
tags: "user-documentation, workflow-axis, capability-drift, evidence-ledger, dual-audience, backlog-derivation"
tier: M
related_specs: [SPEC-COPILOT-SPATIAL-001, SPEC-COPILOT-GROUPGEN-001, SPEC-COPILOT-VWX-001, SPEC-COPILOT-AUTOPATCH-001, SPEC-COPILOT-PRESETGUARD-001]
---

# SPEC-COPILOT-LDGUIDE-001 — 감독 워크플로우 축 가이드 개정

> 칸반 카드 t1(Class C)의 두 갈래 목표를 담는다: (1) 조명감독의 실제 공연 준비 흐름을
> 축으로 한 사용 가이드, (2) 단계별 미충족 지점 → 다음 SPEC 입력이 될 백로그 항목.
>
> **카드 전제 정정**: 카드는 "감독의 언어로 설명한 문서가 없습니다"라고 적었으나
> `docs/user-guide.html`(55,212바이트, 커밋 `2e20dda`, 2026-08-13)이 이미 존재하며 이미
> 워크플로우 축으로 쓰여 있다. 따라서 이 SPEC은 **신규 집필이 아니라 개정**이다.
> 사용자 확인(2026-08-17): 같은 파일 전면 개정 · 시간순 9단계 축 · 독자 = 감독 + 오퍼레이터.

## A. 결함 — 전부 실측이다

### A.1 능력 주장 드리프트 (검증됨, 산술로 확정)

기존 가이드는 도구 목록 절의 제목 자체가 **"22가지 AI 도구 전체 목록"**이다. "전체"라고
선언한 목록이 실제와 어긋난다.

| 항목 | 값 | 측정 명령 |
|---|---|---|
| 가이드가 주장하는 도구 수 | **22** | `grep -oE '22가지' docs/user-guide.html` → 1건 |
| 코드에 등록된 도구 수 | **33** | `grep -cE '^            name="[a-z_]+",$' server/orchestrator/tools.py` → `33` |
| 차이 | **11** | — |

측정 기준: 워크트리 `.claude/worktrees/ldguide`, HEAD `2092a42`(`main` 최신), 2026-08-17.

### A.2 식별자 부재 17건 (검증됨) — 다만 "능력 누락"과 동일하지 않다

> **[정정 — v0.5.0]** 초판은 "17종 등장 / 16종 부재"로 적었다. **등장과 부재가 뒤바뀐
> 오측이었다.** 실제는 **16종 등장 / 17종 부재**다. 기전은 이 SPEC이 내내 잡아온 것과
> 같은 계열이다 — §A.2의 대조 grep에 **단어 경계가 없어서**, 등록명 `preshow_check`가
> 가이드의 유령 이름 `run_preshow_check` **안에 부분 문자열로 걸려** 등장으로 계수됐다.
>
> ```
> grep -c '\bpreshow_check\b' docs/user-guide.html   → 0   (단독으로는 없다)
> grep -c 'preshow_check'     docs/user-guide.html   → 1   (유령 안에 매치)
> ```
>
> 즉 **§A.4의 유령이 §A.2의 숫자를 오염시키고 있었다.** 유령을 잡는 절과 개수를 세는 절이
> 같은 문서 안에서 서로를 가린 셈이다. plan-audit 3회가 이것을 잡지 못한 이유도 같다 —
> 감사도 같은 깨진 명령을 봤다. run 단계 M0 실측이 발견했고 lead가 독립 재측정으로 확인했다.
> (§6-C.5의 "수정이 새로운 헛도는 명령을 만든다" 패턴의 또 다른 실례.)

등록된 도구 33종 중 **16종만** 가이드 본문에 식별자로 등장한다. 나머지 17종은 단독
식별자로 한 번도 나오지 않는다:

```
analyse_layout_image · apply_vectorworks_patch · arrange_fixtures · ask_user ·
build_magic_sheet · classify_arrangement_topology · compose_fx ·
create_arrangement_groups · find_scene · patch_fixtures · plan_executor_layout ·
precheck_patch · precheck_vectorworks_diff · preshow_check · resolve_fixture_type ·
resolve_patch_address · vectorworks_autopatch
```

측정(단어 경계 + 집합 연산 — 부분 문자열 오탐 차단):

```bash
grep -oE '^            name="[a-z_]+",$' server/orchestrator/tools.py \
  | sed 's/.*name="//;s/",//' | sort > /tmp/t.txt          # 33
grep -oE '\b[a-z]+_[a-z_]+\b' docs/user-guide.html | sort -u > /tmp/g.txt
comm -12 /tmp/g.txt /tmp/t.txt > /tmp/present.txt
wc -l < /tmp/present.txt                                    # 16 등장
comm -23 /tmp/t.txt /tmp/present.txt | wc -l                # 17 부재
```

**[미검증 — 과장 금지]** 이 17건이 곧 "가이드가 그 능력을 다루지 않는다"는 뜻은 **아니다**.
주제어 검색으로 확인한 반례가 있다: `vectorworks|도면|MVR` 8건, `배치|위상` 15건,
`매직|magic` 2건, `익스큐터` 6건이 본문에 등장하고, `<h3>6-2. 패치 점검</h3>` 절이
`precheck_patch`를 식별자 없이 산문으로 설명한다. 따라서 17건 각각이 (a) 산문으로 덮여
있는가 (b) 실제로 빠졌는가 (c) 낡은 서술로 덮여 있는가는 **M0에서 도구별 1:1 대조로
판정한다.** 개수 차이만으로 결함을 단정하지 않는다.

### A.3 구성 축이 감독의 시간축과 어긋난다 (설계 간극)

기존 목차는 앱 기능 묶음 축이다 — 쇼 준비(프로그래밍) / 연출 설계 / 현장 세팅·점검 /
쇼 진행 / 문서화·인계 5단계. 감독이 문서를 펴는 시점은 "지금 이 일을 하는 중"이지
"프로그래밍이라는 범주를 공부하는 중"이 아니다. 사용자(현직 조명감독)가 확정한 실제 흐름은
9단계다:

```
1. 도면·자료 수령 (Vectorworks / 리스트)
2. 패치 (장비 등록·주소 배정)
3. 리그 셋업 · 포커싱
4. 그룹 · 프리셋 정리
5. 룩 / 이펙트 만들기
6. 큐리스트 작성
7. 리허설 · 수정
8. 본공연 운용
9. 철수 · 인수인계
```

기존 5단계가 이 9단계를 덮지 못하는 지점이 구조적으로 존재한다 — 특히 **3(포커싱)**과
**7(리허설·수정)**은 기존 축에 대응 절이 없다.

### A.4 유령 도구 이름 5건 (검증됨) — 역방향 결함

§A.1·§A.2는 **코드 → 가이드** 한 방향만 쟀다. 반대 방향(가이드에 적힌 이름 → 실제 등록
여부)을 재보니 **저장소에 존재하지 않는 이름 5건**이 가이드에 남아 있다.

측정: 가이드의 스네이크케이스 토큰 전량(23종)에서 등록 도구 33종과 허용목록 2종을
차집합으로 제거한 잔여.

| 가이드에 적힌 이름 | 실제 |
|---|---|
| `run_preshow_check` | 등록명은 `preshow_check`. 내부 함수도 `run_preshow_checklist`로 이름이 다르다 |
| `check_patch` | 등록명은 `precheck_patch`. 단독 단어 `check_patch`는 0건 |
| `generate_groups` | `server`·`ui`·`console` 전체 **0건** |
| `propose_plan` | `server`·`ui`·`console` 전체 **0건** |
| `write_coordinate` | `server`·`ui`·`console` 전체 **0건** |

**허용목록(비도구이나 정당한 토큰) 2종** — 코드에 실재함을 확인했다:
`contents_unavailable`(`server/web/messages.py` 외) · `drilldown_capped`(`server/fx/matching.py` 외).

이것은 §A.1이 지목한 드리프트와 **같은 종류**이며 방향만 반대다. 1회차 감사(D2)가 3건을
지목했고, 3회차 조치로 부인목록을 **전량 차집합**으로 바꾸자 나머지 2건이 즉시 드러났다 —
알려진 것만 찾는 검사는 4번째를 영원히 놓친다는 것의 실증이다.

## B. 요구사항 (GEARS)

### B.1 구성

- **REQ-LDG-001** [Ubiquitous] — the 가이드 **shall** §A.3의 9단계를 최상위 축으로 삼고,
  각 단계를 하나의 절로 갖는다. 단계 순서는 시간순이며 재배열하지 않는다.
- **REQ-LDG-002** [Ubiquitous] — 각 단계 절 **shall** 세 부분을 이 순서로 갖는다:
  **① 감독이 하는 일** → **② 앱이 대신하는 부분** → **③ 앱이 못 하는 부분(한계)**.
  ③이 비면 "이 단계에서 확인된 간극 없음"을 명시한다 — 침묵으로 비우지 않는다.
  각 부분의 `<h3>`는 리터럴 클래스 `part-do` / `part-app` / `part-gap`을 갖고, 단계
  `<h2>`는 `id="stage-1"`~`id="stage-9"`를 갖는다. 이 마커가 없으면 구조 검사가
  문서 전체 개수 세기로 퇴화해 보존 절(REQ-LDG-010)의 `<h3>`와 뒤섞인다.
- **REQ-LDG-003** [Ubiquitous] — the 가이드 **shall** 독자 2계층을 지원한다: 본문은 감독
  기준, 오퍼레이터·크루용 보충은 시각적으로 구분된 보조 블록에 둔다. 같은 내용을 두 번
  쓰지 않는다(중복 금지 — 보조 블록은 본문이 생략한 조작 절차만 담는다).

### B.2 언어 · 표기

> 이 절이 담는 REQ: **004 · 005 · 016 · 017 · 006** (번호순이 아니라 주제순 배치 —
> 016·017은 식별자·증거 표기 규약이므로 여기 둔다. 번호 집합은 001~017 완전하다.)

- **REQ-LDG-004** [Unwanted] — the 가이드 본문 **shall not** SPEC ID·내부 모듈 경로·
  소스 파일명·함수명을 노출한다. 콘솔 용어(시퀀스·큐·익스큐터·프리셋·패치)는 감독의
  현업 어휘이므로 제한 없이 쓴다.
- **REQ-LDG-005** [Ubiquitous] — the 가이드 **shall** 도구 식별자(`get_rig_context` 등)를
  본문에서 배제하고, 문서 말미의 **참조 부록** 한 곳에만 대조표로 둔다. 그 부록은
  리터럴 마커 `<h2 id="appendix-tools">`로 시작한다 — 본문/부록 경계를 기계적으로
  특정할 수 있어야 AC가 실행 가능해지기 때문이다. 기존 가이드에 이미 존재하던 목록 절의
  유용성을 보존하되(REQ-LDG-010), 본문 서술은 감독 언어로 유지하기 위한 분리다.
- **REQ-LDG-016** [Unwanted] — the 가이드 **shall not** 등록되지 않은 도구 식별자를 쓴다.
  §A.4의 유령 5건은 제거하거나 실제 등록명으로 교정한다. 본문·부록 모두에 적용된다.
  판정은 **전량 차집합**으로 한다 — 가이드의 스네이크케이스 토큰 전량에서 등록 도구명과
  허용목록(§A.4의 2종)을 뺀 잔여가 0이어야 한다. 알려진 이름만 찾는 부인목록은 금지한다.
- **REQ-LDG-017** [Ubiquitous] — the 가이드 **shall** 모든 능력 주장에 증거 원장의 행 id를
  `data-ev` 속성으로 부착한다. **부착 대상은 구조로 정의한다**: `part-app` 구간의 모든
  `<p>`와 모든 `class="warn"` 블록. "능력 주장 문장"을 의미로 정의하면 셀 수 없으므로,
  세는 단위를 마크업 구조에 고정한다. 원장 행 id는 `E-<숫자>` 형식이며 원장에서
  `| E-17 | …` 앵커 행으로 존재한다 — 부분문자열 대조를 막기 위한 형식 고정이다.
  이것이 REQ-LDG-007의 "주장 ↔ 원장 행 대응"을 기계적으로 확인 가능하게 만드는 장치다.
- **REQ-LDG-006** [Unwanted] — the 가이드 **shall not** 시간 예측("2일", "일주일")을 쓴다.
  순서("A를 마친 뒤 B")로 표현한다.

### B.3 증거 규율

- **REQ-LDG-007** [Ubiquitous] — 가이드의 모든 능력 주장("앱이 ~를 해준다") **shall**
  증거 원장 `evidence.md`의 한 행에 대응한다. 각 행은 **명령**과 **관측된 출력**을 갖는다
  (`verification-claim-integrity.md` §2 귀속 규율 승계).
- **REQ-LDG-008** [Unwanted] — the 개정 **shall not** 실행으로 확인하지 못한 능력을 단정
  서술한다. 확인하지 못한 항목은 가이드 본문에 **"미확인"**으로 표기하거나 아예 싣지 않는다.
  둘 중 무엇을 택했는지는 증거 원장에 남긴다.
- **REQ-LDG-009** [Ubiquitous] — **모든 형태의 수치 주장** **shall** 개정 시점의 실측값과
  일치한다. 대상은 개수형(`N가지`·`N종`·`N개`·`N 이펙트`)에 한정되지 않고 **백분율
  (`N%`)·배수·비율 주장**을 포함한다. §A.1의 "22 vs 33" 재발을 막기 위해, 각 수치는
  증거 원장에 측정 명령과 함께 기록한다. 실측할 수 없는 수치는 싣지 않는다.

### B.4 보존 · 범위

- **REQ-LDG-010** [State] — WHILE 개정하는 동안, the 작업 **shall** 기존 문서에서 여전히
  사실인 서술을 보존한다. 백지 재작성은 금지 — 사용자 선택은 "같은 파일 전면 개정"이지
  "폐기 후 신규"가 아니다(2026-08-17 확인).
- **REQ-LDG-011** [Ubiquitous] — the 가이드 **shall** 외부 의존 0을 유지한다(자체완결 단일
  HTML). 기존 파일은 이미 외부 URL 0건·`<script>`/`<link>` 0건으로 측정됐다 — 이 성질을
  회귀시키지 않는다.
- **REQ-LDG-012** [Unwanted] — the 개정 **shall not** `docs/user-guide.html`과
  `.moai/specs/SPEC-COPILOT-LDGUIDE-001/**` 외의 파일을 변경한다. 서버 코드·룰북·
  다른 SPEC은 무접촉이다.

### B.5 안전 경고 배치

- **REQ-LDG-013** [Event] — WHEN 어떤 위험의 근거가 증거 원장에 귀속될 때, the 가이드
  **shall** 그 경고를 해당 단계 절 안에 배치한다(문서 끝 안전 절로 몰지 않는다).
  근거 재확인에 실패한 위험은 **싣지 않으며**, 제외 사실과 사유를 원장에 남긴다
  (REQ-LDG-008 승계). 각 경고 블록은 리터럴 `class="warn"`을 갖고 `data-ev`로 근거 행을
  가리킨다 — 이 리터럴이 없으면 "지정 단계 구간 안에 있는가"를 셀 수 없다.
  아래 4건은 **하한이 아니라 조사 후보**다 — 4건 전부를 싣는 것이
  요구사항이 아니라, 근거가 확인된 것을 빠짐없이 싣는 것이 요구사항이다:

  | 위험 | 단계 | 근거 |
  |---|---|---|
  | 그룹 멤버십은 판독 불가 → 점유 슬롯 덮어쓰기는 복구 불가 | 4 | 기존 기록 |
  | 프리셋 덮어쓰기 확인 카드 — 승낙 어휘가 좁아 저장이 조용히 멈출 수 있음 | 4 | PRESETGUARD 계열 |
  | 씬을 룩+이펙트 따로 호출해 만들면 **조용히** 실패 | 5 | `compile_scene` 설명 원문 |
  | 서버는 Vectorworks 패치를 직접 실행하지 않음 — 사람이 Lua를 실행해야 함 | 1·2 | `apply_vectorworks_patch` 설명 원문 |

  각 경고의 근거는 M0에서 재확인한 뒤 증거 원장에 귀속한다(기억이나 전언 금지).

### B.6 개선 제안 도출

- **REQ-LDG-014** [Event] — WHEN 한 단계의 ③(한계)에 항목이 기재되면, the 작업 **shall**
  그것을 개선 제안 목록 `backlog-candidates.md`의 실행 가능한 항목으로 옮긴다.
  각 항목은 **① 어느 단계의 무엇이 막히는가 ② 관측된 근거 ③ 다음 SPEC이 무엇을 정해야
  하는가**를 갖는다. "좋아지면 좋겠다" 수준의 문장은 항목이 아니다.
- **REQ-LDG-015** [Unwanted] — the plan 세션 **shall not** 백로그 큐에 직접 등록한다.
  목록 파일만 만들어 lead에게 넘기고, 등록(`moai todo add`)은 lead의 몫이다(카드 지시).
  the `$B` 파일 **shall** 첫 절에 리터럴 문장 `등록은 lead가 수행한다`를 담아 이 인계
  계약을 명시한다.

  > **[검증 한계 — 명시]** 이 REQ의 **부정 주장**("등록하지 않았다")은 기계적으로 검증할
  > 수 없다. 큐 파일 `.moai/state/kanban/backlog.json`은 `.gitignore`(L209 `.moai/state/`)에
  > 걸려 있어 어떤 `git diff`에도 나타나지 않고, 감사 시점에는 lead가 이미 등록했을 수 있으며
  > 누가 넣었는지 구분할 수단이 없다. 따라서 AC-016은 **긍정 산출물 계약**(목록 파일의 존재와
  > 인계 문구)만 검증하고, 부정 주장은 `progress.md`에 프로세스 진술로 남긴다.
  > 통과할 수밖에 없는 AC를 두는 것보다 검증 한계를 적는 편이 정직하다(2회차 감사 N1).

## C. Out of Scope

### C.1 Out of Scope — 제외 항목

- 가이드의 **다국어화** — 한국어 단일본만 다룬다.
- 앱 기능의 **구현·수정** — 이 SPEC은 문서 산출물이다. ③에서 나온 간극은 백로그로만 나간다.
- `INSTALL.ko.md`·`README.md`·`docs/curriculum/` 개정 — 별도 축이다.
- 아티팩트 발행(claude.ai 공유 링크) 자체 — 파일이 완성되면 발행은 운영 행위이며,
  카드의 "공유 가능한 HTML"은 자체완결성(REQ-LDG-011)으로 충족한다.
- 오퍼레이터 전용 별도 문서 분리 — 사용자 선택은 한 문서 2계층이다.

## D. 열린 질문

| # | 질문 | 상태 |
|---|---|---|
| Q1 | 17건 식별자 부재 중 실제 능력 누락은 몇 건인가 | **M0에서 판정** — 개수 추론 금지(§A.2) |
| Q2 | 단계 3(포커싱)에 대응하는 도구가 실제로 있는가 | **M0에서 판정.** `server/spatial/pointing.py`는 존재하나 33종 등록 목록에 조준 도구 이름이 없다 — 노출 여부 미확인 |
| Q3 | 단계 7(리허설·수정)에 전용 지원이 있는가 | **M0에서 판정.** 현재 후보는 `query_state`/`run_commands` 저수준뿐으로 보이나 UI 기능(큐 진행 모니터 등)이 덮을 수 있음 |
| Q4 | 참조 부록의 도구 대조표를 남길 것인가 | REQ-LDG-005로 **남김** 결정. 카드의 "내부 모듈명 금지"는 모듈 경로를 뜻하며 앱 기능 표면과 구분된다는 판단 — 사용자가 뒤집으면 부록만 삭제하면 되는 국소 결정 |
| Q5 | 가이드의 나머지 수치 주장(`12 이펙트`·`4종`·백분율 9건)이 실제와 맞는가 | **M0에서 판정.** 1회차 감사도 "존재만 확인했고 진위는 재지 않았다"고 공백으로 남겼다 |
| Q6 | 유령 식별자가 §A.4의 3건뿐인가 | **M0에서 전수 판정.** 1회차 감사는 표 19행의 이름 실재만 쟀고 설명문의 정확성은 대조하지 않았다 — "낡은 서술" 유형이 더 있을 수 있다 |

## 이력

| 버전 | 일자 | 작성 | 변경 |
|---|---|---|---|
| 0.1.0 | 2026-08-17 | kanban plan session | 최초 작성(draft, Tier M). 칸반 카드 t1. 사용자 확인 3건(9단계 축·전면 개정·독자 2계층) 반영. 카드 전제("문서 없음") 정정 — 기존 문서 존재 실측. |
| 0.5.0 | 2026-08-17 | kanban plan session | **§A.2 오측 정정** — 등장/부재가 뒤바뀌어 있었다(17 등장/16 부재 → **16 등장/17 부재**). 기전은 단어 경계 없는 alternation이 유령 이름 `run_preshow_check` 안에서 등록명 `preshow_check`에 부분 매치한 것. run 단계 M0 실측 발견, lead 독립 재측정 확인. 부재 목록에 `preshow_check` 추가, Q1·plan 게이트 C·AC-009 기준값 동반 정정. `acceptance.md` §0에 규약 6(부분 문자열 매칭 금지) 신설. |
| 0.4.0 | 2026-08-17 | kanban plan session | plan-audit 3회차(FAIL 0.79 · 상한 도달 · 권고 PASS-WITH-DEBT) 잔여 R1~R7 반영. §A.4가 3건 → **5건**(전량 차집합 전환으로 `propose_plan`·`write_coordinate` 추가 발견) + 허용목록 2종 실측 확정. REQ-016을 부인목록 금지·전량 차집합으로 명문화. |
| 0.3.0 | 2026-08-17 | kanban plan session | plan-audit 2회차(FAIL 0.70) 결함 반영. 신규 P0 3건(gitignore 경유 상시통과·제목줄 오계수·부록 마커 부재 fail-open) 교정. §A.4 신설(유령 3건), REQ-013에 `class="warn"` 리터럴, REQ-015에 검증 한계 명시, REQ-017 부착 대상 구조 정의. |
| 0.2.0 | 2026-08-17 | kanban plan session | plan-audit 1회차(FAIL 0.56) 결함 반영. §A.4 신설(유령 식별자 3건 — 역방향 미측정, D2). REQ-005에 조동사+부록 리터럴 마커(D4·D8), REQ-009 백분율 포섭(D13), REQ-013을 "근거 귀속된 것을 배치"로 재정의해 AC-014 모순 해소(D3), REQ-016(유령 식별자 금지)·REQ-017(`data-ev` 원장 대응 장치, D5) 신설. Out of Scope h3화(D14). 열린 질문 Q5·Q6 추가. |
