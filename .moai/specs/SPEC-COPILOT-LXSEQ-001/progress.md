# SPEC-COPILOT-LXSEQ-001 — 진행 기록 (progress)

> **인용 규율.** 정본(`spec.md` · `acceptance.md`)은 줄번호로 인용하지 않고 안정 토큰만 쓴다. `파일:줄`은 코드·입력 데이터·타 SPEC 아티팩트에만 쓴다.

## §0 인수인계 — 여기서 시작한다 (2026-08-21)

### 한 문단

**무엇**: LX-SEQ v2.1 RIG 팩 **패치 CSV**(86행)를 읽어 기존 `patch_fixtures` 툴 인자 묶음(런 계획)으로 번역하고 순서대로 위임해 onPC에 패치한다. 신규 코드는 **파서 + 매퍼 + 툴 등재 1종**(`import_lxseq_patch`, `preview`/`apply`). 점유된 자리·FID는 절대 쓰지 않고 목록으로 돌려주며, 재실행은 0건 쓰기로 끝난다. 칸반 카드 t9 · 4단계 중 1단계(후속: 그룹 → 프리셋/FX → 시퀀스/큐, `plan.md` §E가 ID 예약).
**상태**: **plan-phase v0.2.2(문서 전용 — plan-audit 2회차 FAIL 0.88의 N1·R1~R3·R5 반영) · `status: draft` · 미커밋 · plan-audit 1회차 FAIL 0.86 → v0.2.0/0.2.1 → 2회차 FAIL 0.88(N1 blocking: M4 입력 전달 문구가 닫힌 인자 집합과 모순) → v0.2.2 수정, 3회차 델타 재감사 대기(`plan-audit.md`).** REQ **16** · AC **17**(라이브 1) · ASSUMPTION 3(72~74) · 마일스톤 5(M0~M4) · 라이브 세션 1회(M4, 사용자 수행) · clarification 마커 **0건**(`plan.md` §A.4 3건 → 결정 H·I·J).
**Kickoff 답(2026-08-21, 감독)**: ① 입력 채널 = `file_content_base64` 인자, 바이트는 UI 파일 선택기만(채팅 붙여넣기 불허 — REQ-LXSEQ-016) ② 이름 접두 = `group`("{Group} {FID}", 12런 수용) ③ 모드 미해결 = **대안 채택** `mode_unresolved` 건너뛰기 + `mode_overrides` 재호출(기본안 카드 위임 기각). 자세한 기록은 아래 "M0 — Kickoff 결정 기록". **남은 접점**: ④ M4 onPC 세션 일정(로컬 하네스 스크립트 `server/tools/lxseq_e2e.py`로 정본 CSV를 읽어 핸들러 직접 호출 — 서버는 파일 경로를 받지 않는다; t10 전까지 운영자는 채팅으로 이 툴을 쓸 수 없다). ⑤ UI 파일 선택기 → 툴 인자 전달 경로는 **후속 카드 t10으로 위임됨**(감독 판정 2026-08-21 — 더는 접점이 아니다).

### 읽는 순서

| 순서 | 무엇을 알려주나 | 어디 |
|---|---|---|
| 1 | 무엇을 만들기로 했나 · 감독 결정 3건 + Kickoff 답 3건 · 사전 확정 사실 6건 | `spec.md` §A · §B(REQ 16) · §D Out of Scope 5개 H3 |
| 2 | 무엇을 통과해야 하나 | `acceptance.md` AC 17 · 역추적표 · §C.0a |
| 3 | 어떤 순서로, 무엇이 닫혔나 | `plan.md` §A.1(뒤집힐 수 있는 결정 순서) · §A.3 결정 A~J(H·I·J = Kickoff 답) · §B M0~M4 |
| 4 | 기존 툴 4종의 정확한 계약(가장 김) | `research.md` §2 — 특히 §2.3 `patch_fixtures`가 `fids`를 검증하지 않는다는 사실 |

### 인수인계 시 반드시 알아야 할 함정 3건

1. **`patch_fixtures`에 `fids`를 명시하면 검증이 없다**(`tools.py:4039-4041`). LX-SEQ FID 체계(101~, 201~ …)를 보존하려면 반드시 명시해야 하므로 **FID 점유 판정은 매퍼 몫**이다 — 빠뜨리면 기존 픽스처를 조용히 덮는다(복구 불가).
2. **주소 거부는 런 단위다.** 한 행만 점유돼도 `patch_fixtures`는 런 전체를 `address_not_free`로 거부한다 → 매퍼가 행 단위로 먼저 걸러 런을 가른다.
3. **CSV `Mode`는 콘솔 모드 이름이 아니다**(`Mode 1 39ch`, `Extended 25ch`). 그대로 넘기면 `mode_not_found`. 실측 폭 `Ch`로 유일 매칭할 때만 넘긴다.

### 인수인계가 온전한지 기계로 확인하는 법 (plan-phase 시점 값)

```
git rev-parse --short HEAD                                   -> 453846a
git branch --show-current                                    -> jjjh7401/LX-SEQ
uv run pytest server/tests -q                                -> 9596 passed · 8 skipped · 1 warning in 157.34s
grep -oE 'REQ-LXSEQ-[0-9]{3}' .moai/specs/SPEC-COPILOT-LXSEQ-001/spec.md | sort -u | wc -l          -> 16
grep -oE '^### AC-LXSEQ-[0-9]{3}' .moai/specs/SPEC-COPILOT-LXSEQ-001/acceptance.md | sort -u | wc -l -> 17
grep -c 'NEEDS CLARIFICATION' .moai/specs/SPEC-COPILOT-LXSEQ-001/{spec,plan,acceptance}.md          -> 0 · 0 · 0
# 입력 정본은 주 체크아웃의 git 미추적 로컬 파일(워크트리에 없음). 저장소 계약은 v0.2.0에서 복사한 사본 — 워크트리·CI에서 실행 가능, 없으면 명시적 FAIL:
test -f server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv || { echo FAIL; exit 1; }; shasum -a 256 server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv   -> 77a34d4bfd611fc034ce621c9715c1e33129df244a67c7e8dfd75d83816d7ee3  (정본과 동일, 2026-08-21 실측)
tail -n +2 server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv | wc -l                                          -> 86
```

### 다음 담당자가 먼저 결정할 것

1. plan-auditor **3회차 델타 재감사**(2회차 FAIL 0.88 → N1·R1~R3·R5 수정 범위, Tier M 임계 0.80) → PASS면 `§E.1 plan_status`를 `audit-ready`로 갱신.
2. Implementation Kickoff Approval → M0: 사본 확인(`test -f … || exit 1` + sha256) · 계약 드리프트 대조 · baseline 실측.
3. ~~UI 파일 선택기 → `file_content_base64` 전달 경로를 별도 카드로 낼지 감독에게 확인~~ — **후속 카드 t10으로 위임됨**(감독 판정 2026-08-21, `plan.md` §A.4 ① 잔여 메모). M4는 로컬 하네스 스크립트 `server/tools/lxseq_e2e.py`(검증 도구 — 제품 코드 아님)가 정본 CSV를 읽어 base64로 `import_lxseq_patch` 핸들러를 직접 호출해 수행한다 — 서버는 파일 경로를 받지 않는다. **t10이 착지하기 전까지 운영자는 채팅으로 이 툴을 쓸 수 없다**(M4는 스크립트로 수행 가능하므로 t10은 본 SPEC `completed`의 전제가 아니다).

---

## Plan-phase log

### v0.2.0 — plan-audit 1회차 델타 수정 + 감독 Kickoff 답 반영 (2026-08-21)

plan-auditor 1회차 판정 **FAIL 0.86**(`plan-audit.md` — MP-7 마커 3건 + AC 검증 가능성 결함 D2~D7). 같은 날 감독이 마커 3건에 답했다(아래 "M0 — Kickoff 결정 기록"). 적용 내역:

| 항목 | 조치 | 위치 |
|---|---|---|
| D1 마커 3건 | 결정 H·I·J로 등록, §A.4는 기각안·잔여 메모만 | `plan.md` §A.1 행 3~5 · §A.2 · §A.3 · §A.4 |
| D2 입력 경로 | 정본 = 주 체크아웃 미추적 로컬 파일 → **v0.2.0에서 사본 `server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv`로 복사(이 카드 커밋에 포함, 7258 B, sha256 `77a34d4bfd611fc034ce621c9715c1e33129df244a67c7e8dfd75d83816d7ee3` — 정본과 동일 `shasum -a 256` 실측)** · 오프라인 AC는 사본만(절대경로 0건) · 전제 확인은 `test -f … \|\| exit 1` 명시적 FAIL · "아카이브" 문구 정정 | `spec.md` 사실 6 · §F · `plan.md` 결정 G · M0 · M4 · `acceptance.md` AC-001 ②③ · AC-016 · 본 파일 §0 |
| D3 겹침 산술 | FID 104 `Address=40` → 겹침은 **104·105**(실물 계산 `[(104,105)]`) | `acceptance.md` AC-003 ④ |
| D4 `-k` 선택자 | `test_the_registered_tools_are_exactly_the_declared_set`(collect 1/71) + 스크래치 뮤테이션 RED 기록 | `acceptance.md` AC-011 |
| D5 REQ-008 | 감독 답 ② `group`으로 REQ-008 문면이 그대로 성립 — 본문 무변경, REQ-010 기본값만 `"group"` 확정 | `spec.md` REQ-010 |
| D6 대안 런 수 | 10 → **9**(KEY+FOH · BACK+SIDE-L · WASH-U+WASH-D 병합, 86행 직접 계산) | `plan.md` §A.1 · 결정 I · §A.4 ② · `acceptance.md` AC-009 ①-b |
| D7 블라인드스팟 예시 | FID 502(2.040~078) + `2.030` 점유자 — `addressfit.evaluate` 실코드로 `ok=True`·`blind_spot` 확인 | `acceptance.md` AC-007 ④ |
| O1 · O2 | REQ-013 `[Event-driven] When` · REQ-015 `[Unwanted] shall not`(예외 2건 명시) | `spec.md` |
| O3 | `console_read_caveat` 좌표 → `server/vwx/apply.py:672`(grep 확인) | `research.md` §3 |
| O8 | AC-015 ③ 삭제 줄 상한 ≤ 3 + 줄 목록 기록 | `acceptance.md` |
| O4 · O5 · O6 · O7 | **미적용**(어휘 수·REQ 본문에 번지는 변경 — 재감사 델타 범위 밖, 오케스트레이터 재량) | — |
| 감독 답 ① | REQ-LXSEQ-016 `[Unwanted]` 신설(채팅 붙여넣기 금지 · `source.sha256`) + AC-LXSEQ-017 | `spec.md` · `acceptance.md` · `plan.md` M3 |
| 감독 답 ③ | REQ-005 개정(`mode_unresolved` 건너뛰기 · `mode_overrides` 우선 채택) · REQ-010 인자 · 데이터 모델 `ModeResolution` · AC-006 ③/③-b/④/⑥ · 시나리오 5 | `spec.md` · `acceptance.md` |

카운트: REQ 15→**16** · AC 16→**17**(M3 5→6) · 결정 7→**10** · 마커 3→**0** · spec `version` 0.1.0→**0.2.0**.

### v0.2.1 — 문서 전용 개정: UI 전달 경로 t10 위임 · M4 직접 호출 (2026-08-21)

감독 판정(칸반 리드 경유): UI 파일 선택기 → 툴 인자 전달 경로(`ui/` + `server/web/session.py`)는 **후속 카드 t10**으로 분리 — 본 SPEC은 신규 툴 밖 0-diff 유지. M4 라이브는 UI가 아니라 **툴 직접 호출(채팅/스크립트)로 파일 경로를 지정**해 수행한다. 설계 변경 0 · REQ 16 · AC 17 불변. (※ 이 절의 "직접 호출(채팅/스크립트)로 파일 경로 지정 · 서버 파일 읽기" 문구는 plan-audit 2회차 N1로 적발돼 **v0.2.2에서 정정**됐다 — 아래 v0.2.2 절이 현행.)

| 항목 | 조치 | 위치 |
|---|---|---|
| ① 잔여 메모 | "범위 밖 전제 / 별도 카드 여부 확인" → **"후속 카드 t10으로 위임됨"** | `plan.md` §A.2 4 · 결정 H · §A.4 ① · §G · `research.md` §6-6 · `acceptance.md` AC-017 ⑤ · 본 파일 §0 "남은 접점" ⑤ · "먼저 결정할 것" 3 · M0 표 ① |
| ② M4 입력 전달 | "UI 파일 선택기로 올린다" → **현재 절차(t9): 직접 호출 / 목표 상태(t10 이후): UI 파일 선택기**로 분리(한 문장에 섞지 않음), "기계 로컬(CI 대상 아님)" 유지 | `plan.md` M4 · §F 라이브 행 · `acceptance.md` AC-016 검증 방법 |
| ③ REQ-016 관계 | "바이트는 UI 파일 선택기가 고른 파일에서만" → "파일(현재: 직접 호출로 지정한 경로 / t10 이후: UI 파일 선택기)에서만 — 채팅 본문 텍스트에서는 절대 아니다" 완화; 금지 대상(붙여넣은 텍스트)과 M4 허용(직접 호출 + 서버 파일 읽기)이 충돌하지 않음을 한 문장으로 명문화; AC-017 ①의 "파일 선택기" 구절은 목표 상태 문구로 유지(보루의 본질은 붙여넣은 텍스트 거부) | `spec.md` REQ-010 · REQ-016 · HISTORY 0.2.1 · `plan.md` 결정 H · M3 · `acceptance.md` AC-017 대상/주/① |

카운트: REQ **16**(불변) · AC **17**(불변) · 마커 **0** · spec `version` 0.2.0→**0.2.1**.

### v0.2.2 — 문서 전용 개정: plan-audit 2회차(FAIL 0.88) N1·R1~R3·R5 반영 (2026-08-21)

plan-auditor 2회차 판정 **FAIL 0.88**(`plan-audit.md` "Iteration 2 (delta)" — 1회차 D1~D7 전부 해소, must-pass 7/7, 유일한 blocking은 N1). 리드가 (가)안을 승인했다. 설계 변경 0 · REQ 16 · AC 17 불변 · 마커 0.

| 항목 | 조치 | 위치 |
|---|---|---|
| **N1** M4 입력 전달 모순(blocking) | v0.2.1의 "툴을 직접 호출하며 파일 경로를 지정하고 서버가 파일을 읽어 `file_content_base64`를 구성"은 REQ-LXSEQ-010/AC-LXSEQ-017 ①의 닫힌 인자 집합(경로 인자 없음)·`tools.py`의 파일 읽기 0건과 모순 → **(가) 채택**: "현재 절차(t9): 로컬 하네스 스크립트 `server/tools/lxseq_e2e.py`(검증 도구 — 제품 코드 아님)가 정본 CSV 파일을 읽어 base64로 인코딩해 `import_lxseq_patch` 핸들러를 직접 호출한다 — 서버는 파일 경로를 받지 않는다(인자 집합 불변). 채팅 경유 호출은 t10 이후." 스크립트의 이름·소유(M4)·소재(`server/tools/`, `busking_e2e`·`groupgen_e2e`와 같은 DEV TOOL 계열)를 plan M4 파일 줄에 기재 | `spec.md` REQ-010 · REQ-016 · HISTORY 0.2.2 · `plan.md` 머리 · §A.1 4 · 결정 H · §A.4 ① · M4(지시·파일) · §F · §G · `acceptance.md` AC-016 검증 방법 · AC-017 대상/주 · `research.md` §4 · §6-6 · 본 파일 §0 ④ · "먼저 결정할 것" 1·3 · M0 표 ① |
| **R1** REQ-008 `type` 경로 조건절 | `name_prefix_mode="type"`이면 `Group`을 런 경계에서 제외 — 실물 CSV 9런, 1문장 추가 | `spec.md` REQ-LXSEQ-008 |
| **R2** BACK+SIDE-L 병합 구간 | `4.001–325` → **`4.001–450`**(fixture CSV 직접 재계산: BACK 12행 4.001–300 + SIDE-L 6행 4.301–450, 전부 `Martin MAC Aura XB`·`Extended 25ch`·Ch 25·U4) | `acceptance.md` AC-009 ①-b · `plan.md` §A.4 ② · `research.md` §1.1 |
| **R3** Spiider 모드 폭 | 시나리오 5 · AC-006 ③을 실물 `Robe Spiider`(MOVER-D 8행 · `Mode 1 49ch` · `Ch=49`)로 — `[("A",49),("B",49)]` + `Mode="Mode 1 49ch"`(토큰으로도 못 가름). `Extended 25ch`/Ch 25는 `Martin MAC Aura XB` 24행(BACK·SIDE-L·SIDE-R)이지 Spiider가 아니다(fixture CSV 직접 확인). AC-006 ②의 합성 `[("Basic",25),("Extended",25)]` 예는 그대로(토큰 분기) | `acceptance.md` 시나리오 5 · AC-006 ③ |
| **R5** stray 상태 파일 | SPEC 디렉터리 안 `.moai/state/{config-cache,context-usage,github/counts}.json` 3건 + 빈 `.moai/` 디렉터리 삭제(SPEC 디렉터리 cwd에서 `moai`가 돈 흔적, `.gitignore:248`에 가려짐; `find <SPEC dir> -type f -not -name '*.md'` → 빈 출력 확인). `.claude/agent-memory/`는 하네스가 할당한 에이전트 메모리 마운트(파일 0)라 남겨 둠. 이후 모든 명령은 워크트리 루트에서 실행 | SPEC 디렉터리 |
| R4 O4~O7 · R6 fixture 명시적 add | 미적용(재량) · plan 커밋 시 `git add` 명시적 pathspec으로 fixture 포함(스윕 금지) — 절차 메모 | — |

카운트: REQ **16**(불변) · AC **17**(불변) · 마커 **0** · spec `version` 0.2.1→**0.2.2**.

### M0 — Kickoff 결정 기록 (감독 답변 2026-08-21 · AC-LXSEQ-001 ⑤의 기록처)

| # | 질문(plan.md v0.1.0 §A.4) | 답 | 기본안 여부 | 반영 |
|---|---|---|---|---|
| ① | 입력 채널 | 툴 인자 `file_content_base64`. 세션 업로드 포트 재사용 **기각** · 신규 엔드포인트 **기각**. 바이트는 **파일에서만**(현재 절차 t9: 로컬 하네스 스크립트 `server/tools/lxseq_e2e.py`가 읽어 base64로 전달 — 서버는 파일 경로를 받지 않는다 / t10 이후: UI 파일 선택기) — 채팅 붙여넣기 **불허**(개행·공백이 조용히 깨져 잘못 패치된다). UI 전달 경로는 후속 카드 **t10**으로 위임(v0.2.1, 입력 메커니즘 문구는 v0.2.2 N1 정정) | 기본안 채택(+ 붙여넣기 금지 추가) | 결정 H · REQ-LXSEQ-016 · AC-LXSEQ-017 |
| ② | 픽스처 이름 접두 | `name_prefix_mode="group"`, 이름 `"{Group} {FID}"`. 런 10→12는 수용한 비용(콘솔이 이름에서 그룹을 읽는다 · 2단계 그룹 SPEC과 어휘 공유). 타입 접두 대안은 **9런** | 기본안 채택 | 결정 I · REQ-LXSEQ-010 기본값 · AC-LXSEQ-009 |
| ③ | 모드 미해결 시 처리 | **대안 채택, 기본안 기각** — `mode_unresolved`로 건너뛰고 보고 목록 하나에 모은다; `mode_overrides: {"<FixtureType>": "<콘솔 모드>"}`로 재호출. `patch_fixtures` 선택 카드 위임은 하지 않는다(감독 결정 ③과 같은 자세 — 최대 12회 대신 1회 중단). ASSUMPTION-73 유지 | **비기본 선택** | 결정 J · REQ-LXSEQ-005/010/011 · AC-LXSEQ-006 |

사본 기록(plan-phase, 2026-08-21): `server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv` · 7258 B · sha256 `77a34d4bfd611fc034ce621c9715c1e33129df244a67c7e8dfd75d83816d7ee3` · 정본과 동일(`shasum -a 256` 두 파일 실측) · 86행 · 헤더 9열. (M0 나머지 — 계약 드리프트 대조표 · baseline — 은 run-phase M0가 이 절에 이어 적는다.)

### v0.1.0 — plan-phase 아티팩트 5종 작성 (2026-08-21)

착수 SHA **`453846a`**(브랜치 `jjjh7401/LX-SEQ`), 착수 baseline **9596 passed · 8 skipped · 1 warning · 157.34s(0:02:37)** — `uv run pytest server/tests -q -x` 직접 실측(`/private/tmp/…/scratchpad/baseline.txt`), 이월 인용 아님.

| 아티팩트 | 내용 |
|---|---|
| `spec.md` | REQ 15 · Out of Scope 5 H3(전부 `-` 불릿) · ASSUMPTION 72~74 · 데이터 모델 §E · 참조 구현 §F |
| `plan.md` | M0~M4 · 결정 A~G · 열린 결정 3건 · 후속 SPEC ID 예약 · Mode Selection 권고(serial) |
| `acceptance.md` | AC 16(오프라인 15 + onPC 실기 1) · 역추적표 REQ 15/15 · §C.0a 합 16 |
| `research.md` | 입력 데이터 실물 조사 · 툴 4종 계약 · 재사용 헬퍼 시그니처 · 경계·입력 채널 · 메모리 교차 확인 · 갭 |
| `progress.md` | 본 파일 — 인수인계 + §E 골격 + §F 자리 |

### 조사 방법

Vectorworks(VWX-001)와 달리 **입력 실물이 저장소 옆에 있다**(`src/Lighting_Designer/`). 파일을 전문 판독하고 생성기·검증기를 읽어 컬럼 계약을 실물로 동결했다. 기존 툴은 `tools.py` 본문을 직접 읽었고(요약 아님), 메모리 인덱스의 주장(`fid-vs-slot`, `patch_cracked`, `group-membership-not-readable`)은 코드 주석·룰북으로 재확인한 것만 인용했다(`research.md` §5).

### Phase 1 Plan Audit Gate — 스킵 사유

**해당 없음.** 이 SPEC에는 선행 plan-auditor 판정이 없으므로 스킵 조건(PASS · 임계 이상 · 아티팩트 해시 불변) 세 가지를 전부 만족할 수 없다 → `/moai run` 진입 시 Phase 1이 **재실행**된다.

### 감독 결정 반영 확인

| 결정 | 반영 위치 |
|---|---|
| ① 신규 코드 = 파서 + 매퍼만, 쓰기 경로 신설 금지 | REQ-LXSEQ-009/010/015 · Out of Scope "신규 콘솔 쓰기 경로" |
| ② 4단계 분할, 단계마다 onPC 실기 | Out of Scope "2~4단계" · `plan.md` §E · AC-LXSEQ-016 |
| ③ 점유 슬롯 불가침 + 목록 보고 | REQ-LXSEQ-006/007/012 · Out of Scope "점유 슬롯 쓰기" |

---

## §E.1 Plan-phase Audit-Ready Signal

```yaml
plan_status: audit-ready   # plan-audit iter1 FAIL 0.86 → iter2 FAIL 0.88 → iter3 PASS-WITH-DEBT 0.94 (2026-08-21, plan-audit.md §Iteration 3)
plan_complete_at: 2026-08-21T14:20:00+09:00
plan_audit: "iter1 FAIL 0.86 (plan-audit.md) · delta v0.2.0 pending re-audit"
spec_version: "0.2.2"
tier: M
base_sha: 453846a
base_branch: jjjh7401/LX-SEQ
baseline_measured: "uv run pytest server/tests -q -x → 9596 passed, 8 skipped, 1 warning in 157.34s (0:02:37)"
artifacts: [spec.md, plan.md, acceptance.md, research.md, progress.md]
requirements: 16            # REQ-LXSEQ-001~016
acceptance_criteria: 17     # AC-LXSEQ-001~017 (라이브 1: AC-LXSEQ-016)
milestones: 5               # M0~M4 (M0·M4 cycle_type=none)
assumptions_open: 3         # ASSUMPTION-72~74
decisions_closed: 10        # plan.md §A.3 A~J (H·I·J = 2026-08-21 감독 Kickoff 답, J는 비기본 선택)
clarifications_open: 0      # v0.1.0의 3건은 결정 H·I·J로 닫힘 — 답은 "M0 — Kickoff 결정 기록"
live_sessions_planned: 1    # M4, 사용자 수행
new_runtime_dependencies: 0
fixture_csv: "server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv sha256=77a34d4bfd611fc034ce621c9715c1e33129df244a67c7e8dfd75d83816d7ee3 (plan-phase 복사, 정본과 동일)"
```

## §E.2 Run-phase Evidence

### M0 — 기존 툴 계약 확인 · 입력 정본 고정 (2026-08-21, run 세션)

- **위치 확인**: `pwd` / `git rev-parse --show-toplevel` = `/Users/studiox/orca/workspaces/AI-Lighting_Console/LX-SEQ` · `git branch --show-current` = `jjjh7401/LX-SEQ` · `git rev-parse --short HEAD` = `875b2ea` (lead 대조 일치, 착수 승인 받음).
- **게이트 복구**: `npm --prefix ui install` 실행(99 packages added). `ui/node_modules/.bin/vitest` 존재 확인. pre-commit 훅(`/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/.git/worktrees/LX-SEQ` → 공유 `.git/hooks/pre-commit`) 실재 확인(gofmt+go vet 고속 서브셋 + `moai gate` 중게이트).
- **입력 사본 확인**: `test -f server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv` → 존재. `shasum -a 256` = `77a34d4bfd611fc034ce621c9715c1e33129df244a67c7e8dfd75d83816d7ee3` (정본과 일치). `wc -l` = 87행(헤더 1 + 데이터 86). 헤더 열 수 = 9(`FID,Group,FixtureType,Mode,Ch,Universe,Address,AddrRange,Position`).
- **기존 툴 계약 드리프트 대조**: `resolve_fixture_type`(server/orchestrator/tools.py:3408) · `patch_fixtures`(server/orchestrator/tools.py:3820) · `read_existing_fids`(server/vwx/patchplan.py:1395) · `read_inventory`(server/prechk/inventory.py:344) · `read_type_mode_widths`(server/prechk/mode_read.py:76) 전부 실재 확인 — 드리프트 0건.
- **baseline 전체 스위트**: `uv run pytest server/tests/ -q` → **9596 passed, 8 skipped, 1 warning in 144.35s** — plan-phase 기준선(progress.md §E.1: 9596 passed · 8 skipped · 1 warning · 157.34s)과 일치(수치, 시간은 참고치).
- **AC-LXSEQ-001**: PASS (뮤테이션 ①②는 착수 전 대조·사본 확인을 실제로 수행했으므로 해당 없음).

### M1 — 파서 (2026-08-21, run 세션 · cycle_type=tdd)

**위임 2회 실패 후 직접 구현.** `Agent()` 스폰이 두 번 모두(격리를 지정하지 않았음에도) `main` 기준 격리 워크트리(`.claude/worktrees/agent-*`, HEAD `453846a`)로 배치돼 본 SPEC이 존재하지 않는 트리에서 깨어났다. 두 에이전트 모두 위치 불일치를 감지하고 **파일 0개 생성·커밋 0건**으로 블로커 반환. 리드 판정(2026-08-21)에 따라 M1은 이 세션이 직접 구현했다.

**RED → GREEN 순서 준수**: 테스트를 먼저 작성해 수집 실패(`ModuleNotFoundError: No module named 'server.lxseq.parser'`)를 확인한 뒤 `parser.py`를 썼다. 단, 이 RED는 **수집 단계 중단**이라 개별 테스트는 하나도 실행되지 않았다 — 각 테스트의 판별력은 아래 뮤테이션으로 별도 증명한다.

- **커밋**: `fc30986` (파서 + 테스트 15건) · 본 커밋(테스트 보강 3건 + ruff format + 기록)
- **AC-LXSEQ-002** PASS — `uv run pytest server/tests/test_lxseq_parser.py -q -k "real_csv or header"` → 5 passed. 실물 CSV 86 레코드 · 거부 0 · 제외 0, 첫 `fid=101 universe=1 address=1 channels=12 group="KEY"`, 마지막 `fid=430 universe=5 address=322`.
- **AC-LXSEQ-003** PASS — `-k "reject or overflow or duplicate or overlap"` → 7 passed. 500 통과/502 `universe_overflow`, `1.013–023` → `addr_range_mismatch`, hyphen·em-dash 관용, 중복 FID·구간 겹침은 관여 행 전부 거부.
- **AC-LXSEQ-004** PASS — `-k "fid_is_not_an_address"` → 4 passed(보강 후). FID 오프셋 3종 + Group/Position 변경에도 자리 집합 불변, AST 스캔 위반 0(스캔 함수 ≥ 3 비공허성 동반).
- **전체 파일**: `uv run pytest server/tests/test_lxseq_parser.py -q` → **18 passed**(초기 15 + 결함 보강 3).
- **회귀 없음**: `uv run pytest server/tests/ -q` → **9614 passed, 8 skipped, 1 warning (145.87s)**. M0 baseline 9596 + 신규 18 = 9614, 실패 0.
- **lint**: `uv run ruff check server/lxseq/ server/tests/test_lxseq_parser.py` → All checks passed. `ruff format` 1건 적용(`test_overlap_preserve.py::test_ruff_format_reports_no_change` PRESERVE 게이트가 적발 → 수정 후 41 passed).

#### 뮤테이션 3회 — 각 AC 묶음의 판별력 검증

각 회차는 `parser.py`만 변형하고 테스트는 불변으로 두었다. 복구는 "14 passed 재현"이 아니라 **`git diff -- server/lxseq/parser.py` 빈 출력**으로 증명했다(부분 복구가 통과로 위장될 수 있어 통과는 복구의 증거가 못 된다).

| # | 겨냥 | 변형 | 결과 |
|---|---|---|---|
| 1 | AC-002 | `_resolve_header_map`이 이름 대신 **위치**로 컬럼을 읽게 | `test_header_column_order_scrambled_still_name_matched` **단독** RED (1 failed, 14 passed) — 겨냥한 그 테스트가 맞았다 |
| 2 | AC-003 | `_addr_range_matches`가 항상 `True` 반환 | `test_reject_addr_range_mismatch_wrong_digits` **단독** RED (1 failed, 14 passed) |
| 3 | AC-004 | `address = Address + FID % 2` (fid를 자리 계산에 섞음) | AST 스캔은 RED로 잡았으나 **`..._addresses_stable_under_fid_offset`은 GREEN을 유지** → **결함 발견** |

**3회차에서 드러난 테스트 결함과 조치.** AC-LXSEQ-004 ①이 명시한 오프셋 `+1000`은 짝수라 `fid % 2`가 보존돼, fid가 주소에 실제로 섞였는데도 자리 집합이 같게 나왔다. 즉 그 테스트는 "짝수 오프셋에 대해서만" 불변을 검사하고 있었다. 리드 기준(뮤테이션에도 GREEN이면 통과가 아니라 결함)에 따라 조용히 넘기지 않고 보강했다:

- `offset_kind` 3종으로 매개변수화 — `even_1000`(AC 원문 유지) · `odd_1001` · `per_row_varying`(행마다 다른 오프셋)
- 자리 집합 비교 전 `assert baseline_addrs` 비공허성 단언 추가(빈 집합끼리 같다고 통과하는 길 차단)
- `test_fid_is_not_an_address_group_and_position_do_not_move_addresses` 신설 — REQ-LXSEQ-003의 "Group·Position을 바꿔도 자리는 변하지 않는다" 절을 직접 검사(기존엔 미검증이었다)

보강 후 같은 뮤테이션을 재투입해 판별력을 확인했다: `odd_1001`·`per_row_varying` 2건이 RED로 잡았다(`even_1000`은 여전히 통과 — 원래 결함이 재현되며, 이것이 보강이 필요했던 이유의 증거다). 복구 후 `git diff` 빈 출력 · 18 passed.

**뮤테이션 4 (추가) — 미검증 부류 닫기.** 3회차 종료 시점에 거부 7부류 중 `address_out_of_range`만 전용 테스트가 없어(도달 경로만 존재) 미검증으로 남아 있었다. 테스트 3건(`Address=0` · `Address=-3` · `Universe=0`)을 추가한 뒤 `if address < 1 or universe < 1:`을 `if False:`로 무력화하니 **추가한 3건이 정확히 RED**가 됐다(3 failed, 18 passed). 복구 후 21 passed, 뮤테이션 마커 0건, 뮤테이션 관련 diff 줄 0.

**최종 수치**: `uv run pytest server/tests/test_lxseq_parser.py -q` → **21 passed**(15 초기 + 3 AC-004 보강 + 3 `address_out_of_range`). lint·format 모두 통과.

**Gaps(잔여 미검증)**: ① 뮤테이션은 AC 묶음당 1~2회라, 한 묶음 안 개별 테스트 **전부**의 판별력이 증명된 것은 아니다(예: AC-002 5건 중 뮤테이션이 겨냥한 것은 열 순서 1건). ② `zero_channels`·`non_integer_field`·`duplicate_fid`·`address_overlap_in_file` 부류는 테스트는 있으나 전용 뮤테이션은 돌리지 않았다 — 존재는 확인됐고 판별력은 미증명이다.

_<M2 이하 — 착수 예정>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase — manager-develop 소유>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase — manager-docs 소유>_

## §E.1a 이월 채무 (plan → run, 2026-08-21 리드 확정 — run에서 기록만 이어받고 plan에서는 수정하지 않음)

- REQ-005 토큰 분할 규칙 미정의 (plan-audit §Iteration 1 O-기존 · §Iteration 3 채무 6)
- O9: plan.md §G "검증 도구 1 + fixture 1 — plan-phase 커밋에 선반영" 괄호 경계 흐림 (M4 줄이 정본: 하네스는 M4 소유·run 단계 산출물)
- R4: plan-audit §Iteration 1 optional O4~O7 미적용 (재량)
- R6: 커밋은 명시 pathspec만 — fixture `server/tests/fixtures/lxseq/` 포함, 스윕(`add -A`/`add .`/`commit -a`) 금지
- M4 하네스 `server.bridge` import 0 전제 → 구현 시 `grep -c server.bridge server/tools/lxseq_e2e.py` 로 기계 확인

## §F Phase 4 Mode Selection

- **tier**: M · **scope**: 약 10파일(신규 3 + 테스트 3 + 검증 도구 1 + fixture 1(선반영) + 수정 2) · **domain**: 1(Python 백엔드) · **parallel benefit**: LOW(M1→M2→M3 강한 데이터 사슬, 코딩 중심).
- 평가: `direct` 미선택(신규 모듈+툴 배선, 사소하지 않음) · `fanout` 미선택(도메인 1, 조사형 아님) · `sweep` 미선택(기계적 일률 변환 아님, Kickoff Approval은 이미 통과했으나 사슬 의존성이 sweep을 배제) · **`serial` 선택**.
- **Decision: serial**
- **Justification**: M1(파서)→M2(매퍼, M1 산출물 소비)→M3(툴 등재, M2 산출물 소비)의 강한 순차 데이터 사슬이며 코딩 중심 작업이다(Anthropic coding-task parallelism caveat). `plan.md` §G의 사전 권고와 일치.

_M1 이하 — manager-develop 소유, 착수 예정_
