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

### M2 — 매퍼 (2026-08-21, run 세션 · cycle_type=tdd · 직접 구현)

M1에서 확립한 순서를 그대로 적용했다: **테스트 먼저 → GREEN 커밋 → 그 다음 뮤테이션**(커밋을 선행해야 `git diff`가 복구 증거로 선다).

- **커밋**: `7acc1b1`(매퍼 + 테스트 32건) · 본 커밋(AC-010 결함 보강 + 기록)
- **RED**: `ModuleNotFoundError: No module named 'server.lxseq.mapper'` — M1과 같은 수집 단계 중단이라 개별 판별력은 아래 뮤테이션으로 별도 증명했다.
- **AC-LXSEQ-005** PASS — `-k "type_resolution"` 5 passed. `present`만 런에 들어가고 콘솔 이름을 쓴다(CSV 표기 `Robe Spiider`가 런에 0회), `ambiguous`/`absent`/`library_unreadable`은 그 타입 전 행 `type_unresolved`, 타입 해석 요청은 **서로 다른 타입 8종에 8회**(행 86회가 아니다).
- **AC-LXSEQ-006** PASS — `-k "mode_resolution"` 9 passed. 폭 유일 → `width_unique`, 폭 동률 + 라벨 토큰 유일 → `label_token`, 둘 다 실패 → 그 타입 전 행 `mode_unresolved`(질문 카드 없음 — 결정 J), `mode_overrides`는 실측 목록에 있을 때만 채택(대소문자 무시), 목록에 없으면 여전히 `mode_unresolved`, 트리 미판독 → `caller_unverified`. CSV `Mode` 문자열이 런에 새는 경우 0.
- **AC-LXSEQ-007** PASS — `-k "occupied"` 5 passed. 자리 점유 → `address_occupied`(점유자 동봉), 같은 타입·같은 시작 주소 → `already_patched`(별 부류), FID 점유 → `fid_occupied`. **구간 안에서 시작**하는 장비만 확정 충돌이고, 구간 앞에서 시작해 뻗는 장비는 잡지 않되 `blind_spot` 문구를 계획에 싣는다. 건너뛴 FID는 어느 런에도 없다.
- **AC-LXSEQ-008** PASS — `-k "read_incomplete"` 5 passed. 인벤토리 절단·FID 미해결·FID 미조회 세 분기 각각에서 런 0 · 전 행 `console_read_incomplete`, 읽기가 전수로 바뀌면 런이 생긴다(비공허성).
- **AC-LXSEQ-009** PASS — `-k "runs"` 6 passed. 기본 `group` 모드 **런 12개 · 86대**, `type` 모드 **9개 · 86대**, KEY 런 `1.1`/6대/FID 101~106/12ch, MOVER-D 런 `3.1`/8대/FID 521~528, `fid_map` 키 86개, 중간 행을 건너뛰면 MOVER-U가 런 2개로 갈린다.
- **AC-LXSEQ-010** PASS — `-k "no_write_surface"` 1 passed(**보강 후**) + `test_architecture.py` 통과. 금지 import·식별자·문자열 0건, 스캔 파일 3개(비공허성).
- **전체 파일**: 32 passed. **회귀 없음**: `uv run pytest server/tests/ -q` → **9649 passed, 8 skipped, 1 warning**(M1 종료 9614 대비 +35, 실패 0). lint·format 모두 통과.

#### 뮤테이션 6회 — 그리고 드러난 결함 1건

| # | 겨냥 | 변형 | 결과 |
|---|---|---|---|
| 1 | AC-005 | `present` 아닌 타입도 런에 넣게 | 겨냥 묶음 3건 RED (3 failed, 29 passed) |
| 2 | AC-006 | 폭 동률이어도 첫 번째를 집게(`len(same_width) >= 1`) | 겨냥 묶음 3건 RED |
| 3 | AC-007 | 점유 판정 결과를 무시하게 | 겨냥 묶음 5건 + 런 분할 1건 RED (6 failed) |
| 4 | AC-008 | 전수 판독 게이트를 항상 통과시키게 | 겨냥 묶음 4건 RED |
| 5 | AC-009 | 런 경계의 연속성 조건을 무시하게(`contiguous = True`) | 1건만 RED — 아래 관찰 참조 |
| 6 | AC-010 | `from server.vwx import luagen` 주입 | **32 passed — 잡지 못했다 → 결함** |

**결함(뮤테이션 6): 쓰기표면 스캔이 `from X import Y` 형태를 통과시켰다.** `from server.vwx import luagen`은 AST에서 `module="server.vwx"` · `alias="luagen"`으로 갈라지는데, 검사가 `module`만 금지 접두와 대조하고 있었다. 즉 `import server.vwx.luagen`과 `from server.vwx.luagen import X`는 잡지만 **실제로 쓰기 모듈을 끌어오는 가장 자연스러운 형태는 통과**했다 — REQ-LXSEQ-009 보루에 구멍이 있었다는 뜻이다. `module`과 `alias`를 합친 정규화 이름(`f"{module}.{alias.name}"`)까지 대조하도록 보강했고, 3가지 형태(`from server.vwx import luagen` · `import server.bridge` · `from server.vwx import stagedpatch`)를 각각 주입해 **전부 RED**가 되는 것을 확인했다.

**관찰(뮤테이션 5): 런 개수 단언은 연속성을 검사하지 않는다.** 연속성 조건을 무력화해도 `런 12개`·`런 9개` 단언은 통과했다. 실물 CSV에서는 런 경계가 (타입·모드·유니버스·Group) 키만으로 이미 갈려, 연속성 조건이 실제로 작동할 자리가 없기 때문이다. 연속성을 검사하는 것은 `test_runs_split_when_a_row_in_the_middle_is_skipped` 하나뿐이다 — 커버는 되지만 **단 1건에 의존**한다. 결함은 아니나 이월 채무로 적는다.

**복구 증명**: 6회 모두 복구 후 `git diff -- server/lxseq/mapper.py` 빈 출력 확인. 최종 클린 런 32 passed.

### M3 — 툴 등재 · 위임 · 보고 (2026-08-21, run 세션 · cycle_type=tdd · 직접 구현)

- **위치 확인(착수 전)**: `pwd` / `git rev-parse --show-toplevel` = `/Users/studiox/orca/workspaces/AI-Lighting_Console/LX-SEQ` · `git branch --show-current` = `jjjh7401/LX-SEQ` · `git rev-parse --short HEAD` = `3340a62`. 리드 대조 일치.
- **커밋 3개**(전부 명시 pathspec · 메시지에 `t9`): `4955e97`(M2 점유 판정 순서 교정) · `2b4e341`(M3 툴) · `35ab98f`(저장소 가드 3종 갱신).
- **4지점 등재**: `TOOL_NAMES`(`patch_fixtures` 다음) · 핸들러 클로저(`patch_fixtures` 뒤) · `ToolDefinition`(정의 튜플 끝) · `handlers` 맵. **기존 핸들러 본문 변경 0건.**
- **테스트 27건 신규** `server/tests/test_lxseq_tool.py`. 가짜 콘솔은 `deploy`가 받은 Lua를 되읽어 픽스처를 **실제로** 만든다 — 계획을 믿지 않고 실행 경로째 본다.

#### 구현 중 드러난 M2 결함 1건 (M3의 AC가 잡았다)

`AC-LXSEQ-013 ①`은 2회차 preview의 `skipped` 86건이 전부 `already_patched`이길 요구하는데 실측은 전부 `fid_occupied`였다:

```
skipped kinds: Counter({'fid_occupied': 43})
planned: 43
sample: {'fid': 101, 'address': '1.1', 'kind': 'fid_occupied',
         'detail': 'FID 101는 콘솔에 이미 있다', 'occupant': None, 'occupied_fid': 101}
```

원인은 `mapper.py::_occupancy_skip`(M2, `7acc1b1`)의 **판정 순서** — FID 점유를 자리 충돌보다 먼저 본다. 이미 패치된 행은 두 조건이 동시에 참이라 덜 정확한 쪽이 이겼다. **거르는 동작 자체는 옳았다**(43/43 분할 정확). 틀린 것은 라벨이고, 라벨이 지시하는 다음 행동이 정반대다 — `fid_occupied`는 «다른 FID로 다시 패치하라»로 읽혀 같은 리그를 한 벌 더 만든다. 실행 취소는 없다. 자리 판정을 먼저 하도록 순서를 바꿨다(`4955e97`, 되돌리기 쉽게 별도 커밋). 리드 보고 후 진행.

#### 뮤테이션 8회 — 전부 겨냥 테스트를 죽였다

| # | 겨냥(사전 지목) | 변형 | 결과 |
|---|---|---|---|
| ① | `test_the_registered_tools_are_exactly_the_declared_set` | `TOOL_NAMES`에서 등재 1줄 제거 | 1 failed, 97 deselected — RED |
| ② | `test_preview_is_the_default_action_and_writes_nothing` | preview 경로에서 `deploy_pipeline.deploy` 1회 호출 주입 | 1 failed — RED |
| ③ | `test_apply_stops_...` · `test_apply_propagates_awaited_human_...` | `status != "created"`에서 멈추지 않게 | 2 failed — RED |
| ④ | 재실행 멱등 3건 | `_occupancy_skip` 결과를 무시하게 | 3 failed — RED |
| ④b | `AC-013 ①` 라벨 | 판정 순서를 **교정 이전으로 되돌림** | 2 failed — 원래 실패 2건 정확히 재현 (교정이 하중을 받는다는 증거) |
| ⑤ | `test_a_partial_apply_summary_never_claims_success` | 부분 생성 요약이 «성공»을 말하게 | 1 failed — RED |
| ⑦a | `test_the_definition_forbids_pasting_...` | 인자 설명에서 붙여넣기 금지 문구 제거 | 1 failed — RED |
| ⑦b | `test_guidance_repeats_the_paste_ban_to_the_model` | `guidance`에서 같은 문구 제거 | 1 failed — RED |
| ⑦c | sha256 2건 | `source.sha256`을 빈 바이트 상수로 고정 | 2 failed — RED |

**복구 증명**: 8회 모두 복구 후 `git diff --quiet -- server/` 빈 출력 확인. (이 트리에는 이 카드와 무관한 미커밋 83건이 있어 인자 없는 `git diff`는 **구조적으로 비지 않는다** — 반드시 `-- server/`로 좁혀야 한다.)

#### AC-LXSEQ-015 회귀·PRESERVE 게이트 (BASE=`453846a`)

- ② `git diff --stat 453846a..HEAD -- console/lua server/safety server/prechk server/vwx server/paperwork server/rulebook/assets` → **빈 출력**.
- ⑤ 게이트 비공허성: `server/prechk/mode_read.py`에 임시 2줄 주입 후 같은 대조 → `server/prechk/mode_read.py | 2 ++` **비지 않음** 확인, 되돌린 뒤 diff 빈 출력 재확인.
- ③ `git diff 453846a..HEAD -- server/orchestrator/tools.py | grep -c '^-[^-]'` → **0** (상한 3). 삭제된 줄 원문 출력도 **빈 출력** — 순수 추가다.
- ④ `uv run ruff check server/lxseq server/orchestrator/tools.py server/orchestrator/runner.py server/tests/test_lxseq_*.py` → `All checks passed!`

#### ① 전체 스위트 — **이 저장소에는 테스트 CI가 없다**

`.github/workflows/`에 `label-sync.yml` 하나뿐이라 브랜치에도 PR에도 테스트를 도는 워크플로가 없다. 전체 로컬 실행이 이 카드의 유일한 회귀 증거다.

1회차(가드 갱신 전): `uv run pytest server/tests -q` → **3 failed, 9673 passed, 8 skipped, 1 warning in 141.66s**. 실패 3건은 전부 **신규 툴 등재가 원인**이며 무관한 실패가 아니었다 — `_TOOL_TASKS` 한국어 작업 이름 누락 · tools.py 헝크 트립와이어 · `ruff format`.

최종: `uv run pytest server/tests -q` → **9676 passed, 8 skipped, 1 warning in 140.64s**. 기준선 9649 passed · 8 skipped 대비 **+27 = 신규 테스트 수와 정확히 일치**, 실패 0.

#### AC 판정

| AC | 판정 | 근거 |
|---|---|---|
| AC-LXSEQ-011 | PASS | 파리티 테스트 + preview 쓰기 0(뮤테이션 ①②로 판별력 증명), 런 12 · `write_count_planned` 86 · `apply.entered == False` |
| AC-LXSEQ-012 | PASS(주 1건) | 12런 전량 `created` · 플러그인 12회 · 부분 생성에서 `stopped_at == 2` + 이후 `not_attempted` 9건 · `only_fids` 1런 2대 · Lua 출처 `luagen` |
| AC-LXSEQ-013 | PASS | 2회차 preview 런 0 · `already_patched` 86 · 2회차 apply 쓰기 0 · `is_error False` · 절반 상태 43/43 분할 |
| AC-LXSEQ-014 | PASS | 최상위 키 7개 일치 · 닫힌 어휘 · 부분 생성 요약에 «성공/완료» 0건 · "쓰기 0건"은 `entered == False`에서만 · `guidance` 3구절 |
| AC-LXSEQ-015 | PASS | 위 게이트 4종 |
| AC-LXSEQ-017 | PASS | 설명문·인자 설명·`guidance` 3중 보루 · 인자 키 5개/`required`/`additionalProperties: False` · sha256 비공허성 · 업로드 포트 읽기 0회 |

**AC-LXSEQ-012 주**: ③의 "질문 카드로 **모드**를 묻는 시나리오"는 이 설계에서 **도달 불가**다 — 매퍼가 위임 전에 모드를 확정하므로 `patch_fixtures`의 모드 질문 가지에 닿지 않는다(오히려 정상 성질이다). 도달 가능한 질문 카드는 «Patch 편집기를 열어 달라» 하나뿐이라, 관측 계약 3가지(해당 런 `not_run` · `awaited_human` 전달 · 이후 런 미실행)를 그 경로로 검증했다. AC 문구와 실제 경로가 다르다는 사실을 여기 남긴다.

#### M3에서 새로 생긴 이월 채무

- **plan.md M3 파일 목록 밖 3파일을 만졌다.** `server/lxseq/mapper.py`(위 결함), `server/orchestrator/runner.py`(`_TOOL_TASKS`), `server/tests/test_songcue_bundle.py`(헝크 트립와이어). 뒤 둘은 "툴을 등재하면 반드시 따라오는" 가드이며 트립와이어는 자기 주석이 갱신 절차를 정해 둔 자리다 — 계획의 파일 목록이 이 두 자리를 빠뜨렸다. 다음 툴 등재 카드는 처음부터 5파일로 잡아라.
- **`already_patched` 판정 순서를 지키는 것은 툴 테스트 2건뿐이다.** `test_lxseq_mapper.py`에는 순서를 단언하는 테스트가 없다(뮤테이션 ④b가 매퍼 테스트 32건을 전혀 죽이지 않았다). 매퍼 단위에서 이 순서가 조용히 뒤집혀도 M2 스위트는 초록이다.
- **가짜 콘솔은 모드를 타입마다 1개만 준다.** 폭이 같은 모드가 여럿인 경우(라벨 토큰 갈래)와 `mode_overrides` 재호출 경로는 툴 계층에서 미검증이다 — 매퍼 단위 테스트에는 있다.

### M4 — onPC 실기 확인 (2026-08-21, run 세션 · cycle_type=none · **preview까지. apply 미실행**)

- **하네스**: `server/tools/lxseq_e2e.py`(커밋 `16b2d67`). DEV TOOL — `busking_e2e`·`groupgen_e2e` 계열. 콘솔 스택 `build_console_stack` · 툴 `build_toolset` · 배포 `DeployPipeline`(serve.py와 동일 조립). 우회 배선 0.
- **이월 채무 기계 확인**: `grep -c 'server\.bridge' server/tools/lxseq_e2e.py` → **0**. `uv run pytest server/tests/test_architecture.py -q` → 4 passed.

#### 착수 차단 1건 — 수신 포트 9005 이중 점유 (해소됨)

```
server.web.launcher.PortInUseError: port 9005 for 'OSC feedback receive' on 127.0.0.1 is already in use

$ lsof -nP -iUDP:9005
python3.1 67461 studiox  4u IPv4 UDP 127.0.0.1:9005
app_gma3  99116 studiox 20u IPv4 UDP *:9005
$ ps -o pid,ppid,lstart,command -p 67461
67461 67459 Fri Aug 21 16:25:15 2026  .../LX-SEQ/.venv/bin/python3 -m server.web
```

막고 있던 것은 onPC가 아니라 **이 워크트리에서 뜬 코파일럿 백엔드**였다(TCP 8765 LISTEN + **ESTABLISHED 7건** — 브라우저 UI가 붙어 있었다). 부모가 `launchd`라 Ctrl-C할 터미널이 없었다. **에이전트가 죽이지 않고 감독께 올려 감독 손으로 종료**했다 — 살아 있는 세션을 말없이 끊지 않기 위해서다. 종료 후 `app_gma3(*:9005)`만 남았고 왕복은 결정적으로 돈다.

#### 채널 검증 — 정상 왕복 + **날조 대조군** (매 실행 선행, 인자로 끌 수 없음)

명령: `uv run python -m server.tools.lxseq_e2e --csv <정본 절대경로> --probe-only --listen-port 9005 --out .moai/reports/SPEC-COPILOT-LXSEQ-001/m4-probe.json`

```json
"live": { "path": "Patch/FixtureTypes", "ok": true, "child_count": 15,
          "children_returned": 15, "truncated": false }
"fabricated_control": { "path": "Patch/FixtureTypesZZZNotAThing/9999",
          "raised": "StateQueryError: path segment not found: 'FixtureTypesZZZNotAThing'
                     (in Patch/FixtureTypesZZZNotAThing/9999)" }
"trustworthy": true
```

(a) 실재 경로 응답·절단 없음. (b) **날조 경로는 `ok`가 아니라 예외로 거부**됐다 — 이 채널의 `ok`는 증거로 쓸 수 있다. 이 저장소에는 오타 플래그가 붙은 명령이 `ok`로 저장까지 된 기록이 있어(`lesson-fabricated-control-probe.md`) 대조군 없이는 이후 모든 `ok`가 증거가 못 된다.

**미검증으로 남는 것**: 위는 **판독 채널**이다. `preview`는 명령을 한 발도 쏘지 않으므로 **실행 채널**의 "오타가 `ok`로 오는가"는 아직 검증되지 않았다. apply 승인 전에 처분이 필요하다.

#### preview 실측 — 계획 12런 86대가 아니라 **9런 62대**

명령: `uv run python -m server.tools.lxseq_e2e --csv <정본 절대경로> --action preview --listen-port 9005 --out .moai/reports/SPEC-COPILOT-LXSEQ-001/m4-preview.json` → exit 0

```
is_error: False · awaited_human: False
sha256 대조: True  — source.sha256 == 로컬 파일 sha256
              77a34d4bfd611fc034ce621c9715c1e33129df244a67c7e8dfd75d83816d7ee3 / 7258 bytes
console_read: {complete_enough_to_judge_absence: True, caveat: None,
               fid_read: {attempted: True, known: 0, child_count: 0, unresolved: 0}}
런 9 · write_count_planned 62 · skipped 24 · skipped_by_kind {"mode_unresolved": 24}
types.unresolved []  ·  승인 요청 0 · 배포 검토 0 · 질문 0 · 콘솔 송신 0건
summary_ko: "미리보기 — 쓰기 0건. 런 9개 · 계획 62대 · 건너뛴 행 24건."
```

`fid_read.child_count == 0` — **감독이 말씀하신 "패치 U1~U5 비어 있음"이 기계로 확인**됐다. 점유 건너뜀 0건이 그 결과다.

**타입 해석 8종 전부 성공**(`types.unresolved == []`):

| CSV | 콘솔 |
|---|---|
| ETC S4 LED S3 Lustr X8 | Source 4 LED Series 3 Lustr X8 |
| Robe Spiider | Robin Spiider |
| Robe MegaPointe | Robin MegaPointe |
| Martin MAC Aura XB | Mac Aura XB |
| Martin RUSH PAR 2 RGBW Z | Rush Par 2 RGBW Zoom |
| Martin Atomic 3000 LED | Atomic 3000 LED |
| Elation CUEPIX Blinder WW2 | CuePix Blinder WW2 |
| Look Unique 2.1 | Unique 2 1 |

**주의(추적 대상)**: 콘솔 라이브러리 15종 목록에 `Robin Spiider`가 **두 번** 나온다(중복 등록). 이번 호출은 `present`로 확정됐으나 어느 슬롯을 잡았는지는 이 페이로드로 알 수 없다.

#### 건너뛴 24대 — `mode_unresolved` 단일 원인 (설계대로 동작)

전부 `Martin MAC Aura XB` · CSV `Mode="Extended 25ch"` · `Ch=25`.

```
BACK     12대  FID 201~212  4.001 ~ 4.300
SIDE-L    6대  FID 301~306  4.301 ~ 4.450
SIDE-R    6대  FID 311~316  5.001 ~ 5.150
```

콘솔 실측 모드 6종: `Extended - Extended(25)` · `Extended - RAW(25)` · `Extended - RGB(25)` · `Standard - Extended(14)` · `Standard - RAW(14)` · `Standard - RGB(14)`.

**25ch가 3개**라 폭-유일로 못 가르고, CSV 라벨 토큰 `Extended`가 그 셋 **모두**에 걸려 라벨 토큰으로도 못 가른다 → `mode_unresolved`. **결정 J가 의도한 그대로다** — 셋 중 하나를 집었으면 24대가 잘못된 색 모드로 패치됐고, MA3는 패치된 장비를 코파일럿으로 지울 수단이 없다. 세 모드는 **폭이 같아 주소 계획은 동일**하고 속성 배치만 다르다: 오선택의 결과는 주소 충돌이 아니라 «장비가 엉뚱하게 반응»이다.

해소 경로: 감독이 모드를 고른 뒤 `--mode-overrides '{"Martin MAC Aura XB": "<콘솔 모드 이름>"}'`로 재호출.

#### 계획된 9런 · 예상 주소 대역 (폭 전량 `console_measured`)

| # | Group | 콘솔 타입 | 모드 | 주소 | 대 | 폭 | FID | 대역 |
|---|---|---|---|---|---|---|---|---|
| 0 | KEY | Source 4 LED Series 3 Lustr X8 | Direct | 1.1 | 6 | 12 | 101~106 | 1.001–072 |
| 1 | FOH | Source 4 LED Series 3 Lustr X8 | Direct | 1.73 | 8 | 12 | 111~118 | 1.073–168 |
| 2 | BLIND | CuePix Blinder WW2 | 4 channel | 1.169 | 6 | 4 | 601~606 | 1.169–192 |
| 3 | STROBE | Atomic 3000 LED | Extended | 1.193 | 4 | 14 | 611~614 | 1.193–248 |
| 4 | HAZE | Unique 2 1 | Mode 0 | 1.249 | 2 | 2 | 621~622 | 1.249–252 |
| 5 | MOVER-U | Robin MegaPointe | Mode 1 | 2.1 | 8 | 39 | 501~508 | 2.001–312 |
| 6 | MOVER-D | Robin Spiider | Mode 1 | 3.1 | 8 | 49 | 521~528 | 3.001–392 |
| 7 | WASH-U | Rush Par 2 RGBW Zoom | 9 channel | 5.151 | 10 | 9 | 401~410 | 5.151–240 |
| 8 | WASH-D | Rush Par 2 RGBW Zoom | 9 channel | 5.241 | 10 | 9 | 421~430 | 5.241–330 |

합계 **62대**. 런 7·8은 주소가 이어지지만 `Group` 경계(결정 I, `name_prefix_mode="group"`)로 갈렸다 — 의도대로다.

#### 판정 — **AC-LXSEQ-016 미완결**

`preview` 구간만 관측했다. `apply`(86대 생성 재조회 확인) 및 재실행 0건 쓰기는 **미실행**이며, 리드 승인 전까지 실행하지 않는다. 감독 결정 ②에 따라 AC-LXSEQ-016 미수행 상태에서 `implemented`는 가능하나 `completed`는 불가하다.

증거 파일: `.moai/reports/SPEC-COPILOT-LXSEQ-001/m4-probe.json` · `m4-preview.json` — **이 경로는 `.gitignore`(`.moai/reports`)에 걸려 커밋되지 않는다.** 실행한 세션의 디스크에만 있으므로 clean checkout에서는 해석되지 않는다. 그래서 위 관측값은 전부 이 문서 본문에 원문으로 옮겨 적었다 — 판정 근거는 이 절이지 그 파일이 아니다.

#### 감독 결정 — Aura XB 모드 확정 (2026-08-21)

25ch 3종 중 **`Extended - Extended`**. 리그팩 폴더(`02_RIG팩`)에는 CSV와 xlsx뿐이고 서브모드를 적은 문서가 없어 추측 근거가 없었으므로 감독께 직접 여쭈어 받은 답이다(에이전트 추천은 통상값 기반임을 밝히고 물었다). apply 범위도 함께 확정: **모드 확정 후 86대 한 번에**(62대 선행안은 콘솔이 절반 찬 상태에서 2회차를 돌리게 되어 멱등 경로가 실기 첫 시험대가 되므로 기각).

#### preview 재실행 (`--mode-overrides`) — **12런 86대 · 건너뜀 0**

명령: `uv run python -m server.tools.lxseq_e2e --csv <정본 절대경로> --action preview --listen-port 9005 --mode-overrides '{"Martin MAC Aura XB": "Extended - Extended"}' --out .moai/reports/SPEC-COPILOT-LXSEQ-001/m4-preview-override.json` → exit 0

```
채널 trustworthy: True · sha256 대조: True · is_error: False
승인 요청 0 · 배포 검토 0 · 콘솔 송신 0건
런 12 · write_count_planned 86 · skipped 0 · skipped_by_kind {}
summary_ko: "미리보기 — 쓰기 0건. 런 12개 · 계획 86대 · 건너뛴 행 0건."
```

**SPEC 기대치(런 12 · 픽스처 86 · FID 합집합 = CSV)와 일치**한다(REQ-LXSEQ-008). `mode_overrides` 재호출 경로가 실기에서 처음 밟혔고 의도대로 동작했다 — 이 경로는 오프라인 툴 테스트에서 미검증 채무였다.

| # | Group | 콘솔 타입 | 모드 | 주소 | 대 | 폭 | FID | 대역 |
|---|---|---|---|---|---|---|---|---|
| 0 | KEY | Source 4 LED Series 3 Lustr X8 | Direct | 1.1 | 6 | 12 | 101~106 | 1.001–072 |
| 1 | FOH | Source 4 LED Series 3 Lustr X8 | Direct | 1.73 | 8 | 12 | 111~118 | 1.073–168 |
| 2 | BLIND | CuePix Blinder WW2 | 4 channel | 1.169 | 6 | 4 | 601~606 | 1.169–192 |
| 3 | STROBE | Atomic 3000 LED | Extended | 1.193 | 4 | 14 | 611~614 | 1.193–248 |
| 4 | HAZE | Unique 2 1 | Mode 0 | 1.249 | 2 | 2 | 621~622 | 1.249–252 |
| 5 | MOVER-U | Robin MegaPointe | Mode 1 | 2.1 | 8 | 39 | 501~508 | 2.001–312 |
| 6 | MOVER-D | Robin Spiider | Mode 1 | 3.1 | 8 | 49 | 521~528 | 3.001–392 |
| 7 | BACK | Mac Aura XB | Extended - Extended | 4.1 | 12 | 25 | 201~212 | 4.001–300 |
| 8 | SIDE-L | Mac Aura XB | Extended - Extended | 4.301 | 6 | 25 | 301~306 | 4.301–450 |
| 9 | SIDE-R | Mac Aura XB | Extended - Extended | 5.1 | 6 | 25 | 311~316 | 5.001–150 |
| 10 | WASH-U | Rush Par 2 RGBW Zoom | 9 channel | 5.151 | 10 | 9 | 401~410 | 5.151–240 |
| 11 | WASH-D | Rush Par 2 RGBW Zoom | 9 channel | 5.241 | 10 | 9 | 421~430 | 5.241–330 |

합계 **86대**. 런 7·8이 `4.001–300`/`4.301–450`으로 갈린 것은 `Group` 경계(결정 I)이며, 두 구간을 합치면 SPEC v0.2.2 R2가 실물 재계산으로 정정한 **`4.001–450`**과 일치한다.

#### 쓰기 채널 날조 대조군 (apply 직전, 리드 승인 조건)

판독 채널 검증은 **쓰기 채널을 덮지 않는다**. `preview`는 명령을 한 발도 쏘지 않으므로 「틀린 명령이 `ok`로 오는가」는 별도로 봐야 한다. 그래서 apply 전에 1발을 쐈다.

명령: `uv run python -m server.tools.lxseq_e2e --csv <정본 절대경로> --write-probe --approve --listen-port 9005 --out .moai/reports/SPEC-COPILOT-LXSEQ-001/m4-writeprobe.json`

```
보낸 명령: 'ZZZNOTACOMMAND'
is_error : True
승인 요청: 0 건
outcome  : {"command": "ZZZNOTACOMMAND", "status": "failed", "detail": "Illegal object"}
payload  : {"all_ok": false, "commands": [{"command": "ZZZNOTACOMMAND",
            "status": "failed", "detail": "Illegal object"}]}
trustworthy: True
```

**콘솔이 «Illegal object»로 거부했다 — `executed_ok`가 아니다.** 이 채널의 성공 응답은 증거로 쓸 수 있다.

대조군 문자열 선택 근거: 동사도 객체도 플래그도 아닌 **단일 미지 토큰**이라 파싱이 성립하지 않고 어떤 객체도 겨냥하지 않는다. 유효 명령에 오타 플래그를 붙이는 형태(`Store … /CueOnlyy`)는 **쓰지 않았다** — 이 저장소 실측 기록에서 그 형태는 유효한 앞부분이 실행되어 `ok`+저장까지 됐다(`lesson-fabricated-control-probe.md`). 대조군은 부분적으로도 유효해서는 안 된다.

**부수 관측 1건(추적 대상)**: `승인 요청 0건` — 안전 게이트가 이 명령에 승인 번들을 요구하지 않았다. 즉 게이트는 이 문자열을 위험 동사로 분류하지 않았다. 대조군 자체는 무해했으나, **게이트가 모든 송신에 승인을 요구하지는 않는다**는 사실이 여기서 실측됐다. apply의 `Plugin '…'` 실행 역시 같을 수 있다(플러그인 **배포**는 `DeployPipeline` 검토를 별도로 거친다).

#### apply 1차 — **0대 생성, fail-closed** (하네스 결함)

감독이 onPC에서 Patch 편집기를 열어 두신 것을 확인받고 실행. 5.5초 만에 끝났다.

```
요약: 부분 생성 — 계획 86대 중 0대만 콘솔 재조회로 확인됐다. 0번 런에서 멈췄다.
런 0: not_deployed  created 0/6
      "배포가 deploy_failed로 끝났다(cannot confirm plugin source write
       (readback did not match any setter form)). 패치는 일어나지 않았다."
런 1~11: not_attempted  (0번 런이 created가 아니라 시도하지 않았다)
독립 재조회: child_count 0  ← 콘솔은 그대로였다
```

**설계대로 멈췄다.** 첫 런이 `created`가 아니므로 나머지 11런은 시도조차 하지 않았고, 독립 재조회가 `child_count 0`으로 **아무것도 쓰이지 않았음을 확인**했다. 부분 생성 위에 재시도하는 경로는 존재하지 않는다.

**원인은 제품이 아니라 하네스였다.** `--plugin-import-dir`를 넘기지 않아 OSC `deploy` 동사 대체 경로로 떨어졌다. 현장 설정(`~/Library/Application Support/…/settings.toml`)에는 값이 있었다:

```
plugin_import_dir = "/Users/studiox/MALightingTechnology/gma3_library/datapools/plugins"
receive_port = 9005
osc_slot = 2
```

`serve.py`는 이 값을 `resolve_effective_settings`로 읽는데, 하네스는 플래그로만 받고 있었다. **하네스가 앱과 다른 값을 쓰면 검증 대상이 제품 경로가 아니다.** 그래서 플래그 기본값을 하드코딩하는 대신 **같은 이음매(`resolve_effective_settings`)를 쓰도록** 고쳤다 — 현장 설정이 바뀌면 하네스가 따라간다. 페이로드에 `plugin_import_dir`와 `plugin_import_dir_source`를 실어 어느 값을 썼는지 매 실행 기록한다.

재시도 전 전제 재확인: `child_count 0` · 계획 12런 86대 불변 · `plugin_import_dir_source: site_settings`.

#### apply 2차 — **86대 생성 확인** (5분 3초)

명령: `uv run python -m server.tools.lxseq_e2e --csv <정본 절대경로> --action apply --approve --listen-port 9005 --mode-overrides '{"Martin MAC Aura XB": "Extended - Extended"}' --out .moai/reports/SPEC-COPILOT-LXSEQ-001/m4-apply2.json`

```
is_error: False · awaited_human: False · stopped_at: None · 질문 카드 0건
요약: "86대를 만들었고 콘솔 재조회로 확인했다. 건너뛴 행 0건."

런  0 created  6/6     런  6 created  8/8
런  1 created  8/8     런  7 created 12/12
런  2 created  6/6     런  8 created  6/6
런  3 created  4/4     런  9 created  6/6
런  4 created  2/2     런 10 created 10/10
런  5 created  8/8     런 11 created 10/10
생성 합계 86

배포 검토 12건 — 타입마다 자기 플러그인(CopilotPatchSource4LEDSeries3LustrX8 ×2 ·
CuePixBlinderWW2 · Atomic3000LED · Unique21 · RobinMegaPointe · RobinSpiider ·
MacAuraXB ×3 · RushPar2RGBWZoom ×2)
```

**독립 재조회**(툴 응답과 별개로 픽스처 루트를 직접 되읽음):

```
{"path": "Patch/Stages/1/Fixtures", "ok": true, "child_count": 86,
 "children_listed": 19, "truncated": true, "enumeration_complete": false}
```

`childCount == 86`. 열거는 19대에서 **절단**됐다(이 저장소의 알려진 함정 — `childCount`가 진짜 총계다). 절단 범위 안 19행을 프로퍼티까지 되읽어 계획과 대조한 결과 FID·주소가 정확히 일치했다:

```
slot  1 FID 101 1.001 · … · slot  6 FID 106 1.061   (KEY,   12ch 간격)
slot  7 FID 111 1.073 · … · slot 14 FID 118 1.157   (FOH,   12ch 간격)
slot 15 FID 601 1.169 · … · slot 19 FID 605 1.185   (BLIND,  4ch 간격)
```

절단 밖 슬롯도 직접 지목해 표본 확인(읽기 전용 일회성 진단):

```
slot 35~42  FID 521~528  3.001/3.050/3.099/…/3.344  FixtureType 4  "1 Mode 1"       Name "MOVER-D 521…528"   (49ch 간격)
slot 43~44  FID 201~202  4.001/4.026                FixtureType 8  "1 Extended - Extended"  Name "BACK 201/202"  (25ch 간격)
```

폭·이름 접두(`{Group} {FID}`)·모드 전부 계획대로다.

#### 재실행 — 쓰기 0건 (AC 핵심 충족) · **다만 사유가 기대와 다르다**

```
요약: "미리보기 — 쓰기 0건. 런 0개 · 계획 0대 · 건너뛴 행 86건."
런 0 · write_count_planned 0 · skipped_by_kind {"console_read_incomplete": 86}
승인 요청 0 · 배포 검토 0
```

**「재실행은 0건 쓰기」는 충족됐다.** 그러나 plan.md M4 ③이 기대한 `already_patched` 86건이 아니라 `console_read_incomplete` 86건이다. 콘솔 판독은 이랬다:

```
complete_enough_to_judge_absence: false
caveat.kind : "console_read_index_domain_unknown"
caveat      : child_count 86 · observed_count 86 · missing_count 0 ·
              unreadable_address_count 0 · unread_count 0
              "열거가 절단됐으나 선언된 자식을 전부 관측했다 — 수량 비교는 정확하고,
               인덱스 도메인만 미상이다."
fid_read    : known 86 · unresolved 0
```

#### 결함 D1 — 매퍼의 판독 게이트가 저장소 정본 규약보다 엄격하다 (M2, 미수정)

**추론이 아니라 대조로 확인했다.** `server/vwx/apply.py::console_read_caveat` 독스트링이 두 상태를 명시적으로 가른다:

> `missing_count == 0` 인데 `index_domain_unknown` — 열거는 짧았지만 선언된 것을 전부 관측했다. `childCount`가 진짜 총계이므로 **수량 비교는 정확하다**. **주의는 남기되 막지 않는다.**

형제 호출부 둘이 그 규약을 지킨다 — `server/orchestrator/tools.py:4203`(`patch_fixtures`)과 `server/vwx/apply.py:804`가 똑같이 `caveat["kind"] != CONSOLE_READ_INCOMPLETE`로 판정한다. 실제로 이번 apply에서 `patch_fixtures`는 같은 절단 상태에서 12런 전부를 정확히 `created`로 판정했다.

그런데 `server/lxseq/mapper.py:115`의 `_judge_console_read`는 `inventory.completeness != COMPLETE`를 쓴다 — **caveat 종류를 보지 않고 완전성 라벨만 본다.** `index_domain_unknown`은 `completeness == "incomplete"`이므로 여기서 막힌다.

**영향**: 이 콘솔의 열거는 19대에서 절단된다. 즉 리그가 그 선을 넘는 순간 `import_lxseq_patch`는 **어떤 계획도 세우지 못한다** — 이번 멱등 확인만이 아니라 향후 모든 패치 임포트가 `console_read_incomplete`로 막힌다. 방향은 안전한 쪽(fail-closed, 쓰기 0)이지만, 실기에서 이 툴은 첫 임포트 이후 사실상 무력해진다. AC-LXSEQ-013 ①의 `already_patched` 경로도 실기에서는 도달 불가다 — 오프라인 테스트가 통과한 이유는 가짜 콘솔이 절단되지 않기 때문이다.

#### D1 수정 — 형제 규약에 맞춤 (감독 결정으로 t9 안에서 처리, 커밋 `d48d4b7`)

새 정책을 만든 것이 아니라 **이미 문서화된 규약에 맞춘 것**이다. `_judge_console_read`가 `completeness` 라벨 대신 `console_read_caveat(inventory)["kind"] == CONSOLE_READ_INCOMPLETE`로 판정한다 — 형제 호출부 둘과 같은 잣대다. **규약을 넓히지 않았다**: `missing_count > 0`인 진짜 짧은 판독은 그대로 막힌다.

**테스트를 먼저 세웠다.** 이 결함이 오프라인에서 안 잡힌 이유는 「가짜 콘솔은 절단되지 않는다」였으므로, `FakeConsole`에 **절단 변형**(`truncate_at`)을 추가했다 — `childCount`는 진짜 총계로 두고 `children`만 짧아진다. 신규 5건:

| 테스트 | 겨냥 |
|---|---|
| `test_a_truncated_but_fully_observed_read_still_plans` (매퍼) | 절단·전수관측 → 12런 86대 |
| `test_a_genuinely_short_read_still_blocks` (매퍼) | `missing_count > 0` → 여전히 차단 |
| `test_the_gate_uses_the_repository_criterion_not_the_completeness_label` (매퍼) | 두 인벤토리의 `completeness`가 **똑같이** INCOMPLETE임을 먼저 단언 — 라벨로는 가를 수 없음을 고정 |
| `test_a_truncating_console_still_reports_already_patched` (툴) | 실기 형상 종단 재현 |
| `test_a_truncating_console_is_not_vacuously_truncated` (툴) | 절단 변형이 실제로 짧은 목록을 내는가 |

**뮤테이션 3회 — 전부 겨냥 테스트를 죽였다** (양방향으로 확인):

| # | 변형 | 결과 |
|---|---|---|
| ① | 잣대를 예전(`completeness` 라벨)으로 되돌림 | 신규 3건 RED — 교정이 하중을 받는다 |
| ② | caveat 검사를 통째로 제거(규약을 지나치게 넓힘) | 5건 RED — 가드가 느슨해지지 않았다 |
| ③ | 가짜 콘솔의 절단을 무력화 | 비공허성 1건 RED — 절단 변형이 실재한다 |

복구 후 `git diff --quiet -- server/` 빈 출력 3회 확인.

#### D1 라이브 재검증 — **판독 게이트 열림 확인** (preview, 쓰기 0건)

콘솔의 86대는 그대로 둔 채 `--action preview`만 재실행했다.

```
판독: complete_enough_to_judge_absence: True · caveat.kind: "console_read_index_domain_unknown"
런 0 · write_count_planned 0 · 건너뜀 86 · 승인 요청 0 · 배포 검토 0
콘솔 상태 불변: child_count 86 · children_listed 19 · truncated true
```

수정 전 `complete_enough_to_judge_absence: False`로 막히던 자리가 **`True`로 열렸다.** 리그가 절단선을 넘으면 툴이 무력해지던 문제는 실기로 닫혔다.

#### 결함 D2 — 실기 `occupant.fixture_type`은 이름이 아니라 **핸들 문자열**이다 (신규, 미수정)

그런데 건너뛴 사유는 `already_patched`가 아니라 `fid_occupied` 86건이다. **원인이 D1과 다르다.**

```
occupant 표본: {"address": "1.1", "name": "KEY 101", "fixture_type": "FixtureType 10"}
전 86행 분포 : FixtureType 4:8 · 8:24 · 9:20 · 10:14 · 11:8 · 13:6 · 14:4 · 15:2
매퍼가 비교하는 값: "Source 4 LED Series 3 Lustr X8" 등 **이름**
```

실물 콘솔의 `FixtureType` 프로퍼티는 `FixtureType <슬롯>` 형태의 **객체 핸들**을 돌려준다. `_occupancy_skip`의 `already_patched` 갈래는 `(first.fixture_type or "") == console_type`, 즉 **이름 대조**를 요구하므로 실기에서는 절대 참이 되지 않는다. 가짜 콘솔은 이름을 그대로 돌려주므로 오프라인에서는 이 갈래가 성립한다 — **D1과 정확히 같은 계열의 가짜↔실물 괴리다.**

슬롯 번호는 라이브러리 목록과 일치한다(4=Robin Spiider · 8=Mac Aura XB · 9=Rush Par 2 RGBW Zoom · 10=Source 4 LED Series 3 Lustr X8 · 11=Robin MegaPointe · 13=CuePix Blinder WW2 · 14=Atomic 3000 LED · 15=Unique 2 1, 대수 합 86). 즉 **슬롯→이름은 모호하지 않다.**

**영향은 D1보다 작다**: `fid_occupied`도 건너뛰므로 쓰기는 0건이고 중복은 생기지 않는다. 다만 라벨이 지시하는 다음 행동이 여전히 「다른 FID로 다시 패치하라」라, M3에서 라벨 순서를 고친 이유가 실기에서는 아직 살아 있지 않다.

**수정하지 않았다.** 핸들→이름 해석은 라이브러리 판독을 매퍼에 새로 주입해야 하는 **설계 변경**이고, 역방향(이름→슬롯)은 `Robin Spiider` 중복 때문에 모호하다. 리드·감독 판단 대상이다.

#### 관측 — `Robin Spiider` 중복 등록 (추정 없음)

```
Patch/FixtureTypes  childCount 15 · listed 15 · truncated false
  슬롯  4  Robin Spiider   <-- 중복
  슬롯 12  Robin Spiider   <-- 중복
```

MOVER-D 8대(FID 521~528)는 **슬롯 4**를 잡았다(`FixtureType 4`, 실측). 슬롯 12가 무엇이 다른지(모드 집합·GDTF 판본)는 이 판독으로 알 수 없다 — **못 읽음**으로 적는다. 감독 확인 대상이다.

#### AC-LXSEQ-016 판정 — **PASS-WITH-DEBT**

| 요구 | 판정 | 근거 |
|---|---|---|
| `preview` 계획 확인 | PASS | 12런 · 86대 · 건너뜀 0 · 콘솔 송신 0건 |
| `apply` 런마다 `created` 관측 | PASS | 12런 전부 `created`, 합 86 |
| 86대 생성이 재조회로 확인 | PASS | 툴과 **독립된** 재조회에서 `child_count 86`, 표본 프로퍼티 대조 일치 |
| 재실행은 0건 쓰기 | PASS | 런 0 · `write_count_planned` 0 · 배포 0 · 승인 요청 0 |
| 재실행 사유 `already_patched` 86건 | **FAIL** | D1 수정 전 `console_read_incomplete` 86건 → **수정 후 `fid_occupied` 86건**. 판독 게이트는 열렸으나(D1 닫힘) 라벨은 여전히 기대와 다르다 — 원인은 신규 결함 **D2**(실기 `occupant.fixture_type`이 이름이 아닌 핸들 문자열) |

D1은 이 카드 안에서 **수정·라이브 재검증 완료**. D2는 신규 발견이며 설계 변경이 필요해 **미수정**이다. `ASSUMPTION-72/73/74` 판정과 D2 처분은 sync 단계 또는 후속 카드로 넘긴다.

**전체 스위트**(D1 수정 후): `uv run pytest server/tests -q` → **9681 passed, 8 skipped, 1 warning in 141.73s**. 기준선 9676 대비 **+5 = 신규 테스트 수와 정확히 일치**, 실패 0.

증거 파일(전부 `.gitignore` 대상 — 본문 원문이 정본): `m4-apply.json` · `m4-apply2.json` · `m4-rerun.json` · `m4-writeprobe.json` · `m4-precheck.json`

_<M4 종료. 콘솔에 86대가 실재한다 — 이 상태는 되돌릴 수 없다.>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase — manager-develop 소유>_

## §E.4 Sync-phase Audit-Ready Signal

```yaml
sync_status: audit-ready
sync_at: 2026-08-21
card: t9
base_sha: 453846a
base_branch: jjjh7401/LX-SEQ
head_at_sync_entry: 70418dc
docs_updated: [CHANGELOG.md, README.md, "progress.md §E.4", "spec.md/plan.md/acceptance.md frontmatter status"]
code_changed_in_sync: 0        # sync 단계는 문서 전용 — 콘솔 무접촉, server/ 무변경
ac_total: 17
ac_pass: 16
ac_pass_with_debt: 1           # AC-LXSEQ-016 (5행 중 4 PASS · 1 FAIL, 사유는 결함 D2)
ac_fail: 0
open_defects: 1                # D2 → 후속 카드 t11 (감독 결정으로 t9 안에서 고치지 않음)
tools_registered: 34           # TOOL_NAMES 항목 수 실측 (33 → 34)
```

### sync 세션이 **직접 재측정**한 것 (귀속: 이 세션, 2026-08-21, HEAD `70418dc`)

아래 5건은 전부 이 세션이 명령을 실행하고 출력을 관측한 것이다. 리드가 전달한 수치를 옮겨 적은 것이 아니다.

| # | 명령 | 관측한 출력 | 판정 |
|---|---|---|---|
| ① | `uv run pytest server/tests -q` | `9681 passed, 8 skipped, 1 warning in 141.64s (0:02:21)` · exit 0 | PASS |
| ② | `uv run ruff check server/lxseq server/orchestrator/tools.py server/orchestrator/runner.py server/tests/test_lxseq_*.py server/tools/lxseq_e2e.py` | `All checks passed!` · exit 0 | PASS |
| ③ | `uv run ruff format --check <같은 범위>` | `9 files already formatted` | PASS |
| ④ | `git diff --stat 453846a..HEAD -- console/lua server/safety server/prechk server/vwx server/paperwork server/rulebook/assets` | **빈 출력** | PASS (봉쇄 구역 0-diff) |
| ⑤ | `git diff 453846a..HEAD -- server/orchestrator/tools.py \| grep -c '^-[^-]'` | `0` | PASS (순수 추가 — 기존 툴 계약 0-diff) |

증거 원문: `.moai/state/verify/t9-sync/pytest-full.txt` (전체 스위트 출력 전문).

**기준선 귀속**: ①의 9681은 plan-phase 기준선 9596(§E.1 `baseline_measured`)에서 M1 +18 → 9614, M2 +35 → 9649, M3 +27 → 9676, D1 수정 +5 → 9681로 이어진 값이며, 각 증가분은 §E.2에 기록된 신규 테스트 수와 일치한다. 이 세션은 최종값만 재현했고 중간 4개 값은 §E.2의 run 세션 기록을 읽은 것이다 — **재현하지 않았다.**

### 미검증 (Gaps — 이 세션이 관측하지 **않은** 것)

- **뮤테이션 20회**(M1 3 · M2 6 · M3 8 · D1 3)는 run 세션이 실행한 것이며, 이 세션은 §E.2의 기록을 읽었을 뿐 **재현하지 않았다.**
- **M4 실기 증거 전부**(preview 12런 86대 · apply 86대 생성 · 독립 재조회 `child_count 86` · 날조 대조군 2종 · D1 라이브 재검증)는 run 세션이 감독 onPC에서 실행한 것이다. **이 세션은 콘솔에 접속하지 않았다** — 리드 조건 4(콘솔 무접촉)를 지켰고, 86대가 실재하는 상태는 되돌릴 수 없으므로 재현 자체가 부적절하다. `.moai/reports/SPEC-COPILOT-LXSEQ-001/m4-*.json`은 `.gitignore` 대상이라 저장소에 없으며 **§E.2 본문이 정본이다.**
- **`§E.3 Run-phase Audit-Ready Signal`이 `pending` 상태로 남아 있다.** 소유자는 `manager-develop`이며 sync 단계에서 대신 채우지 않았다(소유 경계). run 증거 자체는 §E.2에 전량 기록돼 있으므로 **증거의 부재가 아니라 서명 블록의 부재**다.
- **CI 부재**: `.github/workflows/`에 `label-sync.yml` 하나뿐이라 이 PR에도 테스트가 돌지 않는다. ①의 로컬 실행이 유일한 회귀 증거다.

### 잔여 위험 (Residual risk — 관측했음에도 남는 것)

- **D2는 열린 채로 출하된다.** 쓰기는 0건이고 중복도 생기지 않지만, 재실행 시 라벨이 `fid_occupied`로 나가 「다른 FID로 다시 패치하라」로 읽힌다. 사용자가 그 지시를 따르면 중복 리그가 생긴다 — **문서(CHANGELOG · README)에 이 간극을 명시했으나 툴 응답 문구는 고치지 않았다.** 카드 `t11`.
- **가짜↔실물 괴리가 계열로 두 번 나왔다**(D1 절단, D2 핸들). 가짜 콘솔이 실물과 다른 자리는 이 둘 말고도 더 있을 수 있으며, 오프라인 스위트 9681건은 그 자리를 원리적으로 볼 수 없다.
- **`Robin Spiider` 슬롯 4/12 중복** — 슬롯 12가 무엇이 다른지(모드 집합 · GDTF 판본) **못 읽었다.** 추정하지 않았고, 이름→슬롯 역방향 해석을 시도하는 후속 작업은 이 모호성을 먼저 풀어야 한다.
- **개별 테스트 판별력 일부 미증명** — 뮤테이션이 AC 묶음당 1~2회라 `AC-LXSEQ-002` 5건 중 4건, 거부 부류 4종은 "그 검사를 무력화하면 그 테스트가 빨개지는가"가 확인되지 않았다. 조용히 깨지면 §E.1a가 먼저 볼 자리다.
- **UI 배선 미완**(`t10`) — 지금 이 툴을 부를 수 있는 것은 로컬 하네스뿐이며, 최종 사용자 경로는 아직 존재하지 않는다.

## §E.1a 이월 채무 (plan → run, 2026-08-21 리드 확정 — run에서 기록만 이어받고 plan에서는 수정하지 않음)

- REQ-005 토큰 분할 규칙 미정의 (plan-audit §Iteration 1 O-기존 · §Iteration 3 채무 6)
- O9: plan.md §G "검증 도구 1 + fixture 1 — plan-phase 커밋에 선반영" 괄호 경계 흐림 (M4 줄이 정본: 하네스는 M4 소유·run 단계 산출물)
- R4: plan-audit §Iteration 1 optional O4~O7 미적용 (재량)
- R6: 커밋은 명시 pathspec만 — fixture `server/tests/fixtures/lxseq/` 포함, 스윕(`add -A`/`add .`/`commit -a`) 금지
- M4 하네스 `server.bridge` import 0 전제 → 구현 시 `grep -c server.bridge server/tools/lxseq_e2e.py` 로 기계 확인

### M1에서 새로 생긴 이월 채무 (2026-08-21, 리드 확정 — 확대하지 말고 기록만)

뮤테이션은 AC 묶음당 1~2회로 그쳤다. 이미 실결함 1건(AC-004 짝수 오프셋)을 건졌고 개별 테스트 전수 뮤테이션은 이 단계에서 값보다 비용이 크다는 판단이다. 나중에 이 부분이 조용히 깨지면 **아래가 먼저 볼 자리**다:

- **AC-LXSEQ-002 5건 중 판별력이 증명된 것은 1건**(`test_header_column_order_scrambled_still_name_matched`)뿐이다. 나머지 4건(실물 86행 · BOM 흡수 · 누락 컬럼 파일 단위 실패 · `extra` 보존)은 존재는 확인됐고 판별력은 미증명이다.
- **거부 부류 4종에 전용 뮤테이션 미실시**: `zero_channels` · `non_integer_field` · `duplicate_fid` · `address_overlap_in_file`. 테스트는 있으나 "그 검사를 무력화하면 그 테스트가 빨개지는가"는 확인하지 않았다.
- 반대로 판별력이 기계로 증명된 것: `addr_range_mismatch`(뮤테이션 2) · `address_out_of_range` 3건(뮤테이션 4) · AC-004 자리 불변 2종 + AST 스캔(뮤테이션 3·3b).

### M2에서 새로 생긴 이월 채무 (2026-08-21)

- **런 경계의 연속성 조건은 테스트 1건에만 의존한다.** 연속성을 무력화해도 `런 12개`·`런 9개` 단언은 통과한다(실물 CSV에서는 타입·모드·유니버스·Group 키만으로 이미 런이 갈려, 연속성이 작동할 자리가 없다). 유일한 검사자는 `test_runs_split_when_a_row_in_the_middle_is_skipped`다 — 이 테스트가 지워지거나 약해지면 연속성 회귀가 조용히 통과한다.
- **`address_out_of_range`·`zero_channels` 행이 매퍼 단계에 도달하는 경로는 미검증이다.** 파서가 걸러내므로 매퍼 테스트는 항상 정상 레코드만 받는다.

### M2·M3 절차 규칙 (M1 1회차 실패에서 도출 — 리드 확정)

**GREEN을 먼저 커밋하고 그 다음에 뮤테이션한다.** M1 1회차 뮤테이션은 `parser.py`가 미추적이라 `git diff`가 구조적으로 항상 빈 출력이었고, 복구 증명이 성립하지 못했다(코드 원문 대조로 대신했다). 커밋을 선행하면 diff가 항상 증거로 선다.

## §F Phase 4 Mode Selection

- **tier**: M · **scope**: 약 10파일(신규 3 + 테스트 3 + 검증 도구 1 + fixture 1(선반영) + 수정 2) · **domain**: 1(Python 백엔드) · **parallel benefit**: LOW(M1→M2→M3 강한 데이터 사슬, 코딩 중심).
- 평가: `direct` 미선택(신규 모듈+툴 배선, 사소하지 않음) · `fanout` 미선택(도메인 1, 조사형 아님) · `sweep` 미선택(기계적 일률 변환 아님, Kickoff Approval은 이미 통과했으나 사슬 의존성이 sweep을 배제) · **`serial` 선택**.
- **Decision: serial**
- **Justification**: M1(파서)→M2(매퍼, M1 산출물 소비)→M3(툴 등재, M2 산출물 소비)의 강한 순차 데이터 사슬이며 코딩 중심 작업이다(Anthropic coding-task parallelism caveat). `plan.md` §G의 사전 권고와 일치.

_M1 이하 — manager-develop 소유, 착수 예정_
