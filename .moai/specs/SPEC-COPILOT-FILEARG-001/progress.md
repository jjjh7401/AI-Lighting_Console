# SPEC-COPILOT-FILEARG-001 — 진행 기록 (progress)

문서 상태: **in-progress** (updated 2026-08-24 — M1 실행됨) · 직전 개정 v0.9.0, 2026-08-23 — B 저술이 드러낸 교정 4건(결정 M 외) · **Tier L · 통과 임계 0.85** · 칸반 카드 t10 · 분할 **A(판별기)**

---

## §0 인수인계 — 여기서 시작한다 (2026-08-22)


**분할 A(판별기)** — "이것은 무엇인가"에만 답한다. 업로드된 바이트를 받아 **술어 레지스트리**로 종류를 판정하고, 0건이면 `unknown_sheet_kind` · 2건 이상이면 `ambiguous_sheet_kind`로 거절한다. 술어는 둘이다 — `patch`는 **열 집합 서명**(정규 9열 포함 검사), `vectorworks`는 **신원 술어**(zip이면 `SCENE_ENTRY`, 아니면 `_best_header_candidate >= 0`) **AND NOT** 다른 행 서명 일치. **사용성**("패치를 뽑을 수 있는가")은 판별에 쓰지 않는다 — 대상 툴이 판단한다. 그 바이트를 실제로 **나르는 일**(세션 슬롯 · 래퍼 툴 인자 · UI 배선)은 `SPEC-COPILOT-SHEETPIPE-001`이 **A 통과 뒤** 맡는다. 후속 카드 002/003/004는 레지스트리에 행 하나씩만 더한다.

### 읽는 순서

1. `spec.md` §A.4(분할 — 무엇이 어디로 갔나) → **§A.5(A가 Tier L인 이유)** → **`design.md` §1(축이 다르다 — 감사 FAIL의 뿌리)** → `design.md` §4(위임 계약 두 갈래) → §F(세 성질)
2. `plan.md` §A.1(뒤집힐 수 있는 결정) → §A.3 **결정 K · L** → §A.4(열린 결정 **0건**)
3. `acceptance.md` §C(AC **20건**과 검증 명령 · 표 밖 4건의 이유)
4. `research.md` **§11**(F2 뿌리 · 신원 열 재계산) → §10 → §9 → §7(갭)


### 인수인계 시 반드시 알아야 할 함정 10건

1. **툴 등재는 4지점이 아니라 6지점이다.** `_TOOL_TASKS`(`server/orchestrator/runner.py:137`)와 `test_tools.py`의 닫힌 집합 상수를 빠뜨리면 `test_runner_progress.py`의 전단사 단언이 빨갛게 된다. 정본 열거는 `research.md` §6이며, `test_runner_progress`는 **지점이 아니라 누락 검출 가드**다.
2. **판별기가 첫 일치에서 멈춰도 오늘은 테스트가 통과한다** — 등록 행이 둘뿐이고 둘은 서로 겹치지 않기 때문이다. 그래서 충돌 시험은 **주입한 표**로 돌린다(`AC-FILEARG-003`). 충돌은 이론이 아니다 — 프리셋 4종에서 반드시 발화한다(`research.md` §9 (c)).
3. **서명을 사본으로 적으면 언젠가 실물을 거절한다.** `patch`는 `CANONICAL_COLUMNS`를 참조하고, `vectorworks`는 `reader.py`의 판정을 **호출**한다. 열 이름도 판정 논리도 옮겨 적지 않는다.
4. **이 저장소에는 테스트 CI가 없다.** `.github/workflows/`는 라벨 동기화 하나뿐이라 로컬 전체 스위트(pytest + vitest)가 유일한 회귀 증거다. 그리고 **착수 시점에 이미 실패 1건이 있다**(`test_pipeline_out_paths.py` / t20 귀속) — 이 SPEC 것이 아니고 여기서 고치지 않는다(§E.1 `known_baseline_failure`).
5. **열 집합으로 Vectorworks를 재려 하지 마라 — 1차 감사 FAIL의 뿌리였다.** `.mvr`·`.xlsx`는 zip이라 헤더 행이 없고(`reader.py:350-360`), 헤더는 1행이라는 보장도 없다(`reader.py:158`이 **탐색**한다). 행이 드는 것은 열 목록이 아니라 **술어**다(결정 K · `design.md` §1).
6. **그리고 술어는 "무엇인가"를 물어야 한다 — 2차(델타) 감사 FAIL의 뿌리였다.** `has_address_family`는 **"패치를 뽑을 수 있는가"**를 묻는다. 축이 다르므로 **양방향으로 틀린다**: LX-SEQ 패치 CSV가 `True`(9열 중 **7열이 VW 별칭**으로 해소 — LX-SEQ는 VW 어휘의 **부분집합**이다)이고, 주소 열 없는 진짜 VW 파일은 `False`다. 사용성 함수를 판별에 끌어들이는 순간 같은 결함이 재발한다(결정 L · REQ-FILEARG-022 · `research.md` §11.1). 그리고 **대조군을 한 축으로만 세우지 마라** — 쉼표 전용 대조군이 전부 초록인 동안 탭 축이 열려 있었고, 장바구니 목록이 실패 0건으로 Vectorworks가 됐다(`AC-FILEARG-028`).
7. **경계 게이트는 커밋 뒤에 돌린다 — 커밋 전 초록은 거짓이다.** `server/tests/test_overlap_preserve.py`는 고정 base와 **`HEAD`**를 diff하므로(실측 22개소 — `grep -c "\.\.HEAD"`; 예: `:427` · `:446` · `:456`) **작업 트리의 미커밋 변경은 그 진단의 시야 밖**이다. 커밋 전에 재서 초록이 나오는 것은 운이 아니라 **구조적으로 보장된 결과**다 — 오늘 이 보드에서 두 번 나왔고(t20 · t31), t31에서는 동결 문서의 실제 위반을 **커밋 뒤에야** 잡았다(미커밋 상태에서는 `41 passed`). 순서는 **커밋 → 게이트 → 보고**이며, "미리 돌려 두면 빠르다"로 되돌리는 것은 **검사를 없애는 것과 같다**(`AC-FILEARG-030`).
8. **수를 셀 때는 정의 앵커 grep을 쓴다.** 이 SPEC은 `006` · `009~015`를 **비운 자리로 문서화**하므로 맨 ID 패턴 grep은 참조까지 세어 과대 보고한다. `grep -c "^- \*\*REQ-FILEARG-" spec.md` → **16**, `grep -c "^### AC-FILEARG-" acceptance.md` → **20**(`acceptance.md` §D 계수 규약). 오늘 이 보드에서 같은 혼동이 네 번 나왔다.
9. **한 방향만 훑지 마라 — 부정 훑기와 긍정 훑기는 둘 다 필요하다.**
   - **부정 방향**: 부정 grep 결과를 "없앴다"의 증거로 쓰지 마라 — 인라인 강조가 문자열을 쪼갠다. `정본을 **참조**한다`는 `정본을 참조`로 검색해도 걸리지 않는다. `columns.py` 오귀속이 **세 번째로** 살아남은 경로가 정확히 이것이었다(감사 A2) — grep이 비었길래 "고쳤다"고 적었는데 강조 마크업 때문에 매치가 빗나간 것이었다. 문구 확인은 **강조를 걷어낸 짧은 토큰**(`columns.py` 같은)으로 훑고 히트를 눈으로 판독한다(`acceptance.md` §D 계수 규약).
   - **긍정 방향**: **절·파일을 옮기거나 지웠으면, 그 이름을 긍정으로 전수 훑어 남은 포인터를 찾는다. 지운 쪽만 확인하고 가리키는 쪽을 안 보면 참조가 고아가 된다.** v0.7.0이 `spec.md` §G.1~§G.4를 `design.md`로 옮기고 **가리키는 쪽 19곳을 그대로 두었다**(감사 D1) — 그중 하나는 인수인계 읽는 순서 1번이라, 다음 담당자가 없는 절을 찾아 헤매게 되어 있었다.
   - **두 방향은 같은 실수의 앞뒷면이다.** v0.7.0은 **이 함정 #9를 쓴 바로 그 라운드에** 그 거울상을 어겼다 — 부정 방향(막 적어 둔 쪽)은 지켰고 긍정 방향은 하지 않았다. 규칙을 적는 것과 그 규칙의 반대 방향을 적용하는 것은 다른 행위다.
   - **세 번째 얼굴 — 총계 방향**: **히트를 「전부」로 보고하기 전에 더 넓은 패턴으로 개수를 재라. 좁은 패턴의 히트 수는 하한이지 총계가 아니다.** 좁은 패턴은 **양방향으로 거짓말한다** — "없다"고 잘못 말하고, "그게 전부다"라고도 잘못 말한다. 실례: `test_overlap_preserve.py`의 `base..HEAD` 자리를 두고 **세 행위자(리드 · B 저자 · 감사자)가 같은 라운드에 같은 파일에서 각각 부분 개수를 총계로 보고했다** — 각자 자기 변수명(`{base}` · `{_PRECHK_BASE}` · `{_OVERLAP_BASE}`)에 맞춘 좁은 패턴을 썼기 때문이다. 넓은 패턴(`grep -c '\.\.HEAD'`)으로 재면 **22개소**이고, **지목된 줄은 누구 것도 틀리지 않았다** — 틀린 것은 "그게 전부"라는 문장뿐이다.
   - **계열 인식**: 이 카드에서 같은 계열이 **다섯 번째**다 — `columns.py` 오귀속 · `2859-2860` 좌표 · `§G.x` 포인터 · `README.md` 경로 누락(저장소 루트 README로 해소됐다). 셋 다 **"문서가 옮겨간 것을 가리킨다"**는 한 가지 형태다. 새 결함으로 보이면 먼저 이 계열인지 의심하라.
10. **Tier 아티팩트는 세는 것이 아니라 집합을 맞추는 것이다.** Tier L 집합은 `spec + plan + acceptance + design + research`이며 **`progress.md`는 그 집합에 없다**. 파일이 다섯 개라는 것과 집합이 채워졌다는 것은 다른 문장이고, v0.6.0까지 그 둘을 혼동해 `design.md` 없이 Tier L을 주장했다(감사 A1). 이것은 `AC-FILEARG-030`의 "가드가 초록이다 ≠ 그 가드가 이 트리를 본다"와 같은 종류의 구분이다.

### 다음 담당자가 먼저 결정할 것

열린 결정은 **없다**(I·J = 리드 재정 · **K·L** = 감사 FAIL 시정 · **분할** = 2차 델타 감사 시정 — `plan.md` §A.3, 답은 아래 "M0 — Kickoff 결정 기록"). 다음 담당자가 기다리는 것은 결정이 아니라 **운영자의 Implementation Kickoff Approval**이다 — M1은 `cycle_type=tdd` 구현이므로 승인 전에는 M0도 시작하지 않는다. 승인 뒤 M1이 실측할 것: ① **`ASSUMPTION-75-b`** — LX-SEQ 패치 헤더가 `vectorworks` 신원 술어를 만족하지 **않는가**(F2가 통과한 바로 그 미측정 방향 · `AC-FILEARG-025`) ② 신원 술어가 `server/tests/fixtures/vwx/` 페이로드 10개를 흡수하는가(못 하면 안전판 REQ-FILEARG-018) ③ 확장 형식이 프리셋 4종을 가르는가(`AC-FILEARG-018`). **B(`SPEC-COPILOT-SHEETPIPE-001`)는 A가 통과할 때까지 착수하지 않는다.**

---

## Plan-phase log

### v0.1.0 — plan-phase 아티팩트 5종 작성 (2026-08-22)

- 워크트리 `.claude/worktrees/t10`, 브랜치 `WT-file-picker-args`, HEAD `eb436e8`(= `origin/main`)에서 작성.
- SPEC ID 자기 점검을 Bash로 실행해 `PASS`를 관측했다(`^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$`). `.moai/specs/`에 동명 디렉터리가 없음을 확인했다.
- 리드가 확정해 넘긴 좌표 8건은 재측정하지 않고 그대로 인용했다(`research.md`가 `[리드]` 등급으로 표시). 본 세션이 **직접 관측한 것**은 다음이며 `[코드]` 등급으로 표시했다: `TOOL_NAMES` 34종과 위치(`tools.py:232`) · `import_lxseq_patch`의 핸들러/정의/맵 위치(`:4418`·`:9226`·`:9327`) · `_TOOL_TASKS`(`runner.py:137`)와 전단사 단언(`test_runner_progress.py:303`·`:307`) · 닫힌 집합 상수 34(`test_tools.py:172`) · `CANONICAL_COLUMNS`/`_normalize_header`/`_resolve_header_map`(`parser.py:18`·`:118`·`:122-135`) · 프레임 허용 목록·검증기·분기(`messages.py:81-83`·`:194`·`:227`, `app.py:494`·`:505`) · `<input accept>`와 라우터 주석(`App.tsx:824`·`:625-635`) · Vectorworks CSV 실물 표본 언급(`server/vwx/columns.py:21`).
- 코드 변경 0건. `ui/`·`server/`·`src/` 아래 파일은 하나도 건드리지 않았다.

### M0 — Kickoff 결정 기록 (`AC-FILEARG-001` ⑥의 기록처)

| 항목 | 답 |
|---|---|
| **결정 I** — 서명 미일치 CSV의 처분 | **(나)안 채택** (2026-08-22 리드 재정). Vectorworks export CSV를 레지스트리 행으로 등록하고, 일치 0건이면 거절한다. (가) 폴백 보존은 [HARD] 거절 규칙에 살아 있는 경로를 남기지 않고, (다) 순수 거절은 폐기 지시 없이 살아 있는 기능을 회수하므로 둘 다 기각 |
| **결정 J** — 무엇을 넓히는가 | **서명 형식의 표현력을 넓히고 레지스트리 행은 넓히지 않는다** (2026-08-22 리드 재정). 형식은 정확 열 집합과 포함·배제 쌍을 표현해야 하며(REQ-016), 프리셋·group·fx·cue-ex의 서명은 쓰지 않는다(REQ-017). 형식 충분성은 합성 서명 픽스처로 증명한다(AC-018) |
| **결정 K** — 레지스트리 행이 드는 것 | **판별 술어**다 (2026-08-23, 독립 감사 FAIL 시정). `patch`=열 집합 술어 · `vectorworks`=기존 판독기 위임(`server/vwx/reader.py`). 열 집합 서명으로는 zip(`.mvr`·`.xlsx`)도 탐색된 헤더도 표현할 수 없어, 그대로 두면 살아 있는 업로드를 회수한다. 치른 값: 표가 순수 데이터가 아니게 된다(design.md §1) |
| **결정 L** — 술어가 무엇을 묻는가 | **신원**이다 (2026-08-23, 델타 재감사 FAIL 0.62 시정). `vectorworks` = `_best_header_candidate >= 0` **AND NOT** 다른 행 서명 일치; 사용성(`has_address_family`·`not_patch_source`)은 판별에서 뺀다. 결정 K가 위임한 함수는 **다른 물음**(패치 가능성)에 답하므로 **양방향으로 틀렸다** — LX-SEQ는 VW 어휘의 **부분집합**이라 주소 계열 검사로는 영원히 갈 수 없다 |
| **결정 M** — 핸들러 열이 담는 것 | **태그 붙은 쌍 `(kind_tag, name)`**이다 (2026-08-23, B 저술 중 발견). `patch` → `(tool, import_lxseq_patch)` · `vectorworks` → `(session_method, upload_vectorworks_export)`. 열 이름은 `대상` → `핸들러`. 태그 없이는 `AC-FILEARG-023`이 `vectorworks` 행을 매번 제외해 **결정 I가 무효**가 된다. 결정 L과 **같은 계열**(판별자 없이 한 자리에 두 가지) — `design.md` §1.1 |
| 후속 SPEC 구속 (결정 M) | 002/003/004는 행 추가 시 **핸들러 태그를 반드시 선언한다**. 미선언 행은 검사 불가이므로 등록으로 치지 않는다 |
| README 인용 경로 | **정정됨** — `README.md:85-95`(저장소 루트로 해소)는 오인용. 정본은 **`server/tests/fixtures/vwx/README.md:84-95`**이며, 이 저장소에서 `README.md` 단독 표기는 금지 |
| `base..HEAD` 자리 수 | **22개소**(실측 `grep -c '\.\.HEAD'`). 앞선 "세 곳"은 좁은 패턴이 찾은 부분집합이었다 — 지목된 줄은 틀리지 않았고 "그게 전부"가 틀렸다 |
| **분할 (v0.5.0)** | 합본이 Tier M 예산(REQ 16 / AC 16)을 넘어 **둘로 나눴다** — 본 SPEC = **A(판별기)** REQ 15 · AC 19 · Tier **L** · 임계 **0.85**; **B(전달경로)** = `SPEC-COPILOT-SHEETPIPE-001` REQ 8 · AC 11 · Tier M · **A 통과 뒤 착수**. 감사 차단 결함은 전부 A에 있었고 B는 지적 0건이다 |
| **A가 Tier L인 근거** | **성격이다, 크기가 아니다.** A는 `REQ-FILEARG-017`이 LXSEQ-002/003/004에게 행 추가를 예약한 **레지스트리 계약을 정의**하므로 constitutional이다. **AC가 10건이어도 Tier L이다** — 예산에 맞춰 티어를 고른 것이 아니다(`spec.md` §A.5) |
| **`AC-FILEARG-009` 분할** | 두 요구를 동시에 섬기던 기준을 쪼갰다 — **A는 순서 단언**(판별이 파싱하지 않는다; ID 유지), **B는 표시 단언**(업로드 직후 네 필드; B 자기 번호) |
| **D1 — 위임 계약** | **두 갈래 전역 함수**로 확정. zip이면 `SCENE_ENTRY`(`tools.py:2861`), 아니면 `_best_header_candidate >= 0`. 판독기 결과 **넷**에 값 배정(미발견 F · 예외 F · `not_patch_source` T · **`unapproved_dependency` T** — 넷째는 v0.4.0에 없던 경우이며 오늘 `.mvr`이 실제로 내는 결과다) |
| **D5 — 좌표 정정** | `tools.py:2859-2860` → **`2860-2861`**, 결정 줄은 **2861**. 문서 7곳 전부 교정(spec 3 · research 2 · acceptance 1 · progress 1). `AC-FILEARG-022` ④가 이 좌표를 인수 근거로 써서, 그대로면 통과 불가였다 |
| **D3 — 세 번째 오귀속** | `plan.md` §E가 VW 서명 소유자를 `columns.py`로 되살려 두었다 — 결정 K가 오귀속으로 판정하고 L이 `reader.py`로 옮긴 그 문장이다. **같은 SPEC이 한 문서에서 고치고 다른 문서에서 되살린** 자리이며 하필 다음 카드가 먼저 읽는 절이었다. 교정 완료 |
| **D4 — AC-027 주장 축소** | "임계 2 고정"은 사실이 아니다. T=1로 낮추면 뒤집히는 것은 무관 대조군이 아니라 **진짜 VW 파일**(점수 1)이고, **T=3은 코퍼스 전체가 초록**이다(2~4점 입력 없음). **하한만** 고정된다고 다시 적었다 |
| 결정 K의 위임 대상 | **정정됨** — "판독기에 위임"이 아니라 **`_best_header_candidate`(`reader.py:158`) 호출**이다. `.mvr` 판정은 `reader.py`에 **없다**(`grep -c "mvr\|MVR"` → 0) — `tools.py:2860-2861` + `mvr.py`가 소유(F1) |
| `ASSUMPTION-75` | **재개방** — v0.2.0이 **한 방향만**(VW 헤더 → patch 서명) 재고 닫은 것이 F2를 통과시켰다. 이제 **75-a**(VW 헤더 ↛ patch 서명, 참) · **75-b**(LX-SEQ 헤더 ↛ vectorworks 술어, **M1 실측 필요**)를 각각 단언한다 — `AC-FILEARG-025` |
| 헤더 없는 `.txt`의 처분 | **`unknown_sheet_kind`가 정답이다** — 그 파일은 오늘 패치를 만들지 못한다(`server/tests/fixtures/vwx/README.md:84-95`). 잃는 것은 능력이 아니라 문구 하나이며, **조건부** 재수출 힌트로 보존한다(REQ-023 · AC-029) |
| 결정 J의 적용 범위 | **열 집합 술어에 한정** — 결정 K 이후 위임 술어는 열을 세지 않으므로 형식 확장의 대상이 아니다 |
| VW 서명 정본 좌표 | **정정됨** — `server/vwx/columns.py`(v0.2.0 오귀속) → 호출 지점 **`server/vwx/reader.py:286`**(`has_address_family(탐색된 헤더)`) |
| `ASSUMPTION-77` | **닫힘 · POSITIVE** — 실물 패치 CSV **7,258 B**(≈7 KB), 8 MiB는 약 1,150배. "수십 KB"는 한 자릿수 오차였다 |
| 리드 결정 ③ "행 하나" 문면 | **정정됨** — 행의 개수가 아니라 **파서·핸들러 없는 종류를 만들지 말라**는 뜻. 결정 D에 반영 |
| `ASSUMPTION-75` | **닫힘** — 리드 실측(`research.md` §9 (a)(b)). 표본 실재 · LX-SEQ와 VW 헤더 비충돌(9열 중 일치 3) |
| Implementation Kickoff Approval | **미통과** — M0·M1 포함 착수는 운영자 승인 뒤. 리드의 "지금 M1 착수" 지시는 철회됨 |

> **run 세션에게**: 위 표에 결정 I·J의 답이 있으므로 `AC-FILEARG-001` ⑥의 답 요건은 충족됐다. 남은 것은 **Implementation Kickoff Approval**이며, 그 전에는 M0도 시작하지 않는다.

---

## §E.1 Plan-phase Audit-Ready Signal

```yaml
plan_status: audit-pending   # plan-audit 미실시 · Implementation Kickoff Approval 미통과(M0 착수 전제)
plan_complete_at: 2026-08-22
plan_audit: "미실시"
spec_version: "0.9.0"
tier: L                     # 분할 A는 constitutional (레지스트리 계약 정의) — 크기가 아니라 성격. 통과 임계 0.85
base_sha: 1c104f0              # 실제 착수 기준선. 6296af3은 plan 작성 시점 값이며 base가 그 뒤 진행했다(G-7)
baseline_measured: "9885 passed, 12 skipped, 0 failed @ 1c104f0 — 측정 명령 `.venv/bin/python -m pytest -q`. 콘솔 정지 상태에서 쟀다(`pgrep app_gma3` 빈 출력 → 9005 포트 거짓 빨강 없음). 이월값이 아니라 이 워크트리에서 직접 잰 값이다."
artifacts: [spec.md, plan.md, acceptance.md, design.md, research.md]   # Tier L 집합 5종. progress.md는 Tier 집합에 없는 별도 파일이다 — v0.6.0까지 이 칸이 progress.md를 세고 design.md를 빠뜨렸다(감사 A1)
requirements: 16            # 정의 앵커: grep -c "^- \*\*REQ-FILEARG-" spec.md → 16 (001~005 · 007 · 008 · 016~024; 006 · 009~015는 SHEETPIPE로 이동 — 번호 재사용 금지)
acceptance_criteria: 20     # 정의 앵커: grep -c "^### AC-FILEARG-" acceptance.md → 20 (001~006 · 009(순서 구간) · 018~030; 조건부 1: AC-021 · 앱 실기 0 — B가 소유)
milestones: 2               # M0(게이트, cycle_type=none) · M1(판별기·레지스트리, tdd). M2~M5는 SHEETPIPE로 이동
assumptions_open: 2         # ASSUMPTION-75(재개방 — 75-b 미검증) · 76. 77은 7,258 B 실측으로 POSITIVE 닫힘
decisions_closed: 13        # plan.md §A.3 A~M (I·J = 리드 재정 · K = 감사 FAIL 시정 · L = 델타 감사 FAIL 시정 · M = 핸들러 태그 쌍)
clarifications_open: 0      # 결정 I로 닫힘 — 답은 "M0 — Kickoff 결정 기록"
live_sessions_planned: 0    # A는 콘솔도 앱도 건드리지 않는다 — 실기 확인은 B(SHEETPIPE)가 소유
new_runtime_dependencies: 0
new_data_files: 0
known_baseline_failure: "server/tests/test_overlap_preserve.py::TestTouchedFilesPassLint::test_ruff_format_reports_no_change — 착수 시점 기존 실패 1건. 원인은 t20(6296af3)이 server/tests/test_pipeline_out_paths.py를 ruff format 없이 들여온 것. 이 SPEC 범위 밖이며 여기서 고치지 않는다(다른 레인이 별도 카드로 처리 중). M0가 실행 시점에 이미 고쳐져 있으면 그 상태를 관측한 대로 적는다."
base_advance: "eb436e8 → 6296af3 (3커밋: e7a8e90 t17 · 6296af3 t20). 문서의 코드 줄번호는 한 세대 낡았다 — M0가 토큰 앵커로 재확인한다."
tool_count_delta: "0 (A는 툴을 등재하지 않는다 — 34 → 35 래퍼 툴 등재는 SHEETPIPE 몫)"
```

## §E.2 Run-phase Evidence

M1 구현 커밋 **`bd21a4c`** · 게이트 실행 HEAD **`e65e1c2`** · 기준선 `1c104f0`.

### M1 — 실측 교차 분류표 (AC-FILEARG-019 ⑤)

`research.md` §11.4에서 "기대"로 표시했던 칸을 M1이 실측했다. **8칸이 예측대로
관측됐고 뒤집힌 칸은 0개다.** 아래 값은 `_best_header_candidate` 호출 결과이며
배제 절 적용 **전**의 원시 신원 술어 값이다.

| 파일 | 크기/형태 | idx | score | 신원 술어 | 최종 분류 |
|---|---|---|---|---|---|
| `demoshow_grandma3.mvr` | zip 315,155 B | — | — | **True** (SCENE_ENTRY) | `vectorworks` |
| `vectorworks_export_sample_with_data.csv` | csv `,` | 0 | 17 | True | `vectorworks` |
| `vectorworks_worksheet_absolute_address_only.csv` | csv `,` | 0 | 18 | True | `vectorworks` |
| `vectorworks_worksheet_multisystem_full.csv` | csv `,` | 0 | 20 | True | `vectorworks` |
| `vectorworks_worksheet_grid_ma3_patch.csv` | csv `,` | 1 | 11 | True | `vectorworks` |
| `vwx_worksheet_grid_from_screenshot.csv` | csv `,` | 1 | 7 | True | `vectorworks` |
| `vwx_worksheet_grid_patch_ready.csv` | csv `,` | 1 | 9 | True | `vectorworks` |
| `synthetic_path_b_worksheet_grid.csv` | csv `,` | 1 | 5 | True | `vectorworks` |
| `drop_dk_rigging_not_a_vectorworks_export.csv` | csv `,` | **-1** | 0 | False | `unknown_sheet_kind` |
| `vectorworks_export_instrument_data_no_header.txt` | tsv 균일폭 | **-1** | **1** | False | `unknown_sheet_kind` + 힌트 |
| `LXSEQ_RIG_01_ShowBase_r3.patch.csv` (참고) | csv `,` | 0 | 7 | **True** | `patch` (배제 절이 갈랐다) |

**안전판(REQ-FILEARG-018)은 발동하지 않는다.** 위임 술어가 vwx 페이로드 10개
전량을 흡수했다 — 흡수하지 못한 변형이 0건이므로 `AC-FILEARG-021`은 **N/A**다
(사유와 관측은 아래 AC 표에 있다).

**`ASSUMPTION-75-b` 확정 · NEGATIVE 아님.** LX-SEQ 패치 헤더는 원시 신원 술어를
**만족한다**(idx=0 · score=7). 즉 75-b는 신원 술어 **단독으로는 성립하지 않고**,
배제 절이 있어야 성립한다. 뮤테이션이 이를 기계로 고정한다 — 배제 절을 빼면
`count == 2`가 되어 `ambiguous_sheet_kind`로 떨어진다.

### AC-FILEARG-024 — 판별 함수에 남은 `else`의 근거

`discriminate` 본문에 `else` 가지가 **하나** 있다. 그것은 암묵적 폴백이 아니라
**계수 결과 `count >= 2`** 이며 `REQ-FILEARG-004`가 선언한 결과다.

```
if count == 0:      outcome = OUTCOME_UNKNOWN     # REQ-FILEARG-003
elif count == 1:    outcome = OUTCOME_RESOLVED
else:               outcome = OUTCOME_AMBIGUOUS   # count >= 2 — REQ-FILEARG-004
```

세 가지가 계수의 전 영역을 덮으므로 표 밖으로 흘러가는 경로가 없다. 술어가 전부
거짓인 경우는 첫 가지이며, 그것 역시 선언된 결과다.

### AC PASS/FAIL 행렬 (M1 배정 19건)

| AC | 검증 명령 | 실제 출력 | 상태 |
|---|---|---|---|
| 001 | `grep -n "_best_header_candidate\|_MIN_HEADER_ALIAS_MATCHES" server/vwx/reader.py` · `grep -c "mvr\|MVR" server/vwx/reader.py` | `43:_MIN_HEADER_ALIAS_MATCHES = 2` · `158:def _best_header_candidate(...)` · `0` | **PASS** (좌표 무드리프트) |
| 002 | `pytest ... -k "signature"` | `10 passed, 73 deselected` | **PASS** |
| 003 | `pytest ... -k "superset or count"` | `4 passed, 79 deselected` | **PASS** |
| 004 | `pytest ... -k "unknown"` · `grep -rn "difflib\|SequenceMatcher\|closest\|best_match" server/sheets/` | `8 passed, 75 deselected` · 빈 출력 (양성 대조군 4행 발화 확인) | **PASS** |
| 005 | `pytest ... -k "ambiguous"` | `6 passed, 77 deselected` | **PASS** |
| 006 | `pytest ... -k "registry"` | `83 passed` (선택자 희석 — 아래 관찰 O-1) | **PASS** |
| 009 | `pytest ... -k "no_trial_parse or parse_once"` | `3 passed, 80 deselected` | **PASS** |
| 018 | `pytest ... -k "format_sufficiency"` | `9 passed, 74 deselected` | **PASS** |
| 019 | `pytest ... -k "cross_classify"` | `13 passed, 70 deselected` | **PASS** (표는 위 §E.2) |
| 020 | `grep -rn "preset-dim\|preset-col\|preset-bm\|preset-pos\|cue-ex" server/sheets/` + 행 수 단언 | 빈 출력 (양성 대조군 3행 발화 확인) · `len(REGISTRY) == 2` 초록 | **PASS** |
| 021 | `pytest ... -k "declared_fallback"` · `grep -n "발동함" plan.md` | `83 deselected` (수집 0) · **비어 있지 않음 — plan.md:182** | **N/A** (아래 결함 D-1) |
| 022 | `pytest ... -k "mvr or headerless"` | `10 passed, 73 deselected` | **PASS** |
| 023 | `pytest ... -k "handler_resolution"` | `5 passed, 78 deselected` | **PASS** |
| 024 | `pytest ... -k "no_implicit_else"` | `7 passed, 76 deselected` | **PASS** (`else` 근거 위에 기록) |
| 025 | `pytest ... -k "patch_identity"` | `3 passed, 80 deselected` | **PASS** |
| 026 | `pytest ... -k "negative_control"` | `2 passed, 81 deselected` | **PASS** |
| 027 | `pytest ... -k "alias_threshold"` | `2 passed, 81 deselected` | **PASS** (하한만 주장) |
| 028 | `pytest ... -k "fabricated_control"` | `4 passed, 79 deselected` | **PASS** (탭·쉼표 두 축) |
| 029 | `pytest ... -k "reexport_hint"` | `5 passed, 78 deselected` | **PASS** |
| 030 | 커밋 → 게이트 → 대조 (아래 경계 게이트 절) | 대조 빈 출력 · 게이트 `41 passed` | **PASS** |

합 **19 PASS · 0 FAIL · 1 N/A**(021은 조건 미발동).

### 뮤테이션 원장

계획 §B M1이 지정한 넷 + AC가 필수로 건 넷. **여덟 중 여덟이 대상 테스트를
죽였다.** 복원은 전부 sha256 대조로 확인했다(초록이 아니라 체크섬으로).

| # | 출처 | 뮤테이션 | 죽은 테스트 | 복원 |
|---|---|---|---|---|
| ① | plan | 판별기를 첫 일치에서 중단 | `superset_header_matches_both` · `superset_header_yields_count_two` (`assert 1 == 2`) | sha256 일치 |
| ② | plan | 서명에서 `AddrRange` 제거 | `signature_rejects_when_one_canonical_column_is_missing` (+ 참조 동일성) | sha256 일치 |
| ③ | plan | `CANONICAL_COLUMNS` → 내용 동일 하드코딩 사본 | `registry_patch_row_references_canonical_columns_by_identity` **단 1건** — 나머지 82건은 초록 | sha256 일치 |
| ④ | plan | 확장 형식의 배제 조건 무시 | `format_sufficiency[bm]` 2건 (`ambiguous_sheet_kind != resolved`) | sha256 일치 |
| ⑤ | AC-022 | `vectorworks` 술어를 열 집합 술어로 되돌림 | `.mvr` 4건 + `cross_classify[demoshow_grandma3.mvr]` | sha256 일치 |
| ⑥ | AC-023 | 태그 무시하고 `TOOL_NAMES` 하나로만 확인 | `handler_resolution_never_excludes_todays_two_rows` + `.mvr` 5건 | sha256 일치 |
| ⑦ | AC-025 | 배제 절 제거 | `patch_identity_is_a_single_match` · `patch_identity_excludes_vectorworks` | sha256 일치 |
| ⑧ | AC-029 | 재수출 힌트 제거 | `reexport_hint` 2건 | sha256 일치 |

**AC-027 임계 뮤테이션(하한 방향)**: `_MIN_HEADER_ALIAS_MATCHES`를 **1**로 낮추면
실물 `vectorworks_export_instrument_data_no_header.txt`가 `outcome = resolved` ·
`matched = ('vectorworks',)` · `hint is None = True`로 뒤집힌다 — `AC-FILEARG-019` ④와
`AC-FILEARG-029`가 함께 죽는다. 인메모리 패치라 복원 대상 파일이 없다.

**③이 이 원장에서 가장 중요한 칸이다.** 내용이 같은 사본은 **행동으로는 보이지
않는다**(82건 초록). 참조 동일성 단언 하나만이 그 드리프트를 잡는다.

### 경계 게이트 (AC-FILEARG-030)

실행 순서 그대로: 커밋 → 게이트 → 대조.

```
0) git diff --stat 95687a0e..HEAD -- server/web/preview.py   → 빈 출력 (뮤테이션 전제 충족)
1) git commit                                                 → bd21a4c
2) uv run pytest server/tests/test_overlap_preserve.py -q     → 41 passed
3) git diff --stat 1c104f0..HEAD -- server/lxseq server/vwx server/orchestrator
   server/web ui console/lua server/safety server/prechk server/paperwork
   server/rulebook/assets                                     → 빈 출력
```

3)의 **양성 대조군**: 같은 명령을 `-- server/sheets server/tests`로 겨누면
`3 files changed, 902 insertions(+)`가 나온다. 빈 출력이 명령이 죽어서 난 것이
아님을 확인했다.

**뮤테이션 — `server/web/preview.py` 한 줄, 두 상태를 모두 기록한다.**

| 상태 | 검사 2) 게이트 | 검사 3) 대조 |
|---|---|---|
| **미커밋** | `41 passed` — **초록** | 빈 출력 — **초록** |
| **커밋 뒤** (`1b6b60a`) | `1 failed, 40 passed` — `TestPreserveDiffIsEmpty::test_the_preserved_paths_are_unchanged` | `server/web/preview.py \| 1 +` |

미커밋 초록이 이 AC가 막는 거짓 신호이며, 실물로 재현됐다. 뮤테이션 커밋은
`e65e1c2`로 되돌렸고 되돌린 뒤 `git diff --stat bd21a4c..HEAD`가 빈 출력이다
(내용이 M1 커밋과 동일).

### 전체 스위트 대조

| 시점 | 명령 | 결과 |
|---|---|---|
| 기준선 `1c104f0` | `uv run pytest server/tests -q` | `9885 passed, 12 skipped, 0 failed` (M0 실측, 이 워크트리) |
| M1 최종 `e65e1c2` | `uv run pytest server/tests -q` | `9968 passed, 12 skipped, 0 failed` (140.88s) |

**증가 +83 · 감소 0.** 신규 테스트가 정확히 83건이므로 델타가 전부 설명된다.

**중간에 잡힌 회귀 1건(기록).** 첫 전체 실행에서 `test_autopatch_contract.py`의
R24 가드 2건이 빨갛게 나왔다 — `_payloads()`가 `VWX_DIR.iterdir()`로 훑었는데,
그 가드는 **경로 꼬리가 `vwx`인 모든 순회**를 vwx 모듈 순회로 읽어 공용 순회
사용이나 등기를 요구한다. 여기서 세는 것은 vwx **모듈**이 아니라 테스트
**픽스처**이고, 등기처(`_R24_INDEPENDENT_SWEEPS`)는 A의 경계 밖이다. 그래서
`FIXTURES.rglob("*")`로 훑고 `vwx/` 하위만 고르도록 고쳤다 — 가드가 지키려는
성질(모듈 순회의 정의는 하나)은 건드리지 않는다. 상세는 아래 관찰 O-2.

### 결함 · 관찰 (run 세션 소인)

**D-1 (주요) — `AC-FILEARG-021`의 N/A 검증 토큰에 판별력이 없다.**
그 AC는 "N/A일 때 `grep -n "발동함" plan.md`가 **빈 출력이어야 하며**, 빈 출력이
곧 N/A의 증거"라고 적는다. 그런데 실제 출력은 비어 있지 않다:

```
$ grep -n "발동함" .moai/specs/SPEC-COPILOT-FILEARG-001/plan.md
182:… 폴백을 타는 순간 이 문단을 "발동함"으로 갱신하고 …
```

§D.1의 **지시문 자체가 그 토큰을 인용**하고 있어, 폴백이 발동하든 하지 않든 grep은
언제나 한 행을 낸다. 이것은 그 AC가 v0.2.0에서 고쳤다고 적은 결함(**이미 있는
문장을 grep해 오늘도 통과하는 검사**)과 **같은 형태가 한 겹 아래에서 되풀이된
것**이다 — 토큰만 바꿨고 인용을 지우지 않았다. 코드 결함이 아니라 **검사 결함**이다.
그러므로 N/A 판정은 이 grep이 아니라 실질 근거로 적는다: 위임 술어가 페이로드
10/10을 흡수했고(교차 분류표), 레지스트리에 폴백 행이 없으며,
`pytest -k "declared_fallback"`이 **0건 수집**이다.
제안 교정: 판별력 있는 토큰은 인용되지 않는 형태여야 한다(예: 문단 머리의
`상태: 발동함` 같은 **행 앞머리 앵커**를 `^`로 고정해 grep).

**O-1 (관찰) — `-k` 선택자가 모듈 이름에 희석된다.**
`pytest -k "registry"`는 `83 passed`(deselected 0)를 낸다. pytest의 키워드 매칭이
**모듈 이름**(`test_sheets_registry`)까지 훑기 때문이며, `AC-FILEARG-006`의 검증
명령은 실질적으로 파일 전체 실행이다. 같은 이유로 `-k "sheets"`도 전량을 고른다.
AC의 ①~⑤는 전용 클래스(`TestRegistryTable`)가 따로 덮으므로 덮개에는 구멍이
없지만, **그 명령이 좁혀 준다고 읽으면 틀린다.**

**O-2 (관찰) — R24 가드가 픽스처 디렉터리를 모듈 순회로 읽는다.**
`test_autopatch_contract.py`의 R24 가드는 **경로 꼬리가 `vwx`인 모든 순회**를
vwx 모듈 순회로 판정해 공용 순회(`iter_vwx_modules`) 사용이나
`_R24_INDEPENDENT_SWEEPS` 등기를 요구한다. 그런데 `server/tests/fixtures/vwx/`는
모듈이 아니라 **픽스처**이고, 이름이 우연히 같을 뿐이다. 교리대로면 등기가 옳으나
등기처가 A의 경계(`REQ-FILEARG-024`) 밖이라 이 카드에서는 손댈 수 없다. 그래서
순회를 `FIXTURES.rglob("*")` + `parent.name == "vwx"` 필터로 바꿨다 — 디스크를
실제로 읽는 성질은 그대로이고(테스트가 공허해지지 않는다), 가드가 지키는 성질도
건드리지 않는다. **다음 카드(SHEETPIPE)가 같은 자리에 다시 부딪힌다** — 그때는
경계가 다르므로 등기가 가능할 수 있다.

### SPEC 공백 (문서가 답하지 않아 판단해야 했던 자리)

이 목록은 실패가 아니라 **인수인계 문서로서의 SPEC이 어디서 침묵했는가**의 기록이다.
각 항은 (무엇이 필요했나 · 어느 아티팩트가 답했어야 하나 · 무엇을 했나) 셋을 적는다.

**G-1 — 헤더 정규화 함수를 어떻게 가져오는가. 결정 F와 `REQ-FILEARG-024`가 충돌한다.**
결정 F: private `_normalize_header`를 다른 모듈이 직접 import하지 말고 **공개 별칭 한
줄**을 `server/lxseq/parser.py`에 더하라(그것이 lxseq에 허용되는 유일한 변경).
`REQ-FILEARG-024`(v0.6.0 신설): `server/lxseq/**`를 **한 줄도** 고치지 않는다 —
`AC-FILEARG-030`이 기계로 확인한다. 둘은 같은 줄을 두고 반대를 말한다. 답했어야 할
곳: `plan.md` §A.3 결정 F(또는 v0.6.0이 REQ-024를 넣으면서 결정 F를 정정했어야 한다).
**한 것**: 결정 F가 스스로 남긴 탈출구("그마저 없이 될 방법이 있으면 그쪽을 택한다")를
따라 `_normalize_header`를 직접 import했다. lxseq 파일은 0줄 변경이고 사본도 만들지
않았으므로 두 요구 중 기계 검사가 있는 쪽을 지켰다.

**G-2 — `.mvr`이 아닌 zip(진짜 `.xlsx`)은 무엇이 되는가.**
`REQ-FILEARG-019`는 "`.mvr` · `.xlsx` … 는 계속 동작한다 — 이 SPEC은 그 능력을
회수하지 않는다"고 적는다. 그런데 `REQ-FILEARG-021`의 두 갈래 전역 함수는
**zip이면 `SCENE_ENTRY` 검사**뿐이므로, `SCENE_ENTRY`가 없는 zip은 False가 되어
`unknown_sheet_kind`로 떨어진다. `design.md` §4는 결과 ④(`unapproved_dependency`)에
**True**를 배정하지만 그 결과는 `reader.read()`의 PK 갈래에서만 나오고, 같은 문단이
"zip 갈래가 먼저 갈라 xlsx 경로에 **들어가지 않게** 막는다"고 적으므로 **④는 명세대로
구현하면 도달 불가능한 칸**이다. 답했어야 할 곳: `spec.md` REQ-021 / `design.md` §4.
**한 것**: REQ-021을 문면 그대로 구현했다(zip → `SCENE_ENTRY`만). 코퍼스에 `.xlsx`
표본이 **0개**라 실측이 바뀌는 칸은 없다 — 그러나 이 자리는 **비어 있는 채로 남았다**.
**후속 종결(2026-08-24).** 리드가 재정했다 — zip 두 형상 모두 신원 참이다. 구현·시험·
미검증 칸은 아래 「M1 후속 — zip 갈래 분기」에 적었다.

**G-3 — 해석 불가 술어 형식의 설정 오류 이름.**
`REQ-FILEARG-016`은 "해석하지 못하는 형태를 표에서 만나면 조용히 건너뛰지 않고 설정
오류로 보고한다"고 요구하지만, `spec.md` §E의 "판별 시점 설정 오류" 행은
`no_target_tool` **하나만** 정의한다. 답했어야 할 곳: `spec.md` §E 표.
**한 것**: `unsupported_predicate_form`을 신설했다(`no_target_tool`과 같은 처분 —
후보 제외 + 오류 보고).

**G-4 — 배제 절이 무엇에 걸리는가.**
"레지스트리의 **다른 행의 서명** 일치"에서, 다른 행이 **열 집합 술어**일 때만 세는지
아니면 어떤 술어든 원시 일치면 세는지가 명시돼 있지 않다. 오늘 행이 둘뿐이라 두 읽기가
같은 답을 낸다 — 그러나 002가 위임 술어 행을 더하면 갈린다. 답했어야 할 곳:
`spec.md` REQ-007 / `design.md` §1.
**한 것**: "사용 가능한 다른 행의 **원시 일치** 아무것이나"로 구현했다.

**G-5 — `SCENE_ENTRY`를 어디서 import하는가.**
정본으로 지목된 `server/orchestrator/tools.py:2861`은 **툴 핸들러 본문 안의 판정
줄**이라 import할 수 있는 것이 아니다. 상수 자체는 `server/vwx/mvr.py:30`에 있다.
답했어야 할 곳: `spec.md` §G / `design.md` §4(둘 다 "결정 줄"과 "소유자"를 구분해
적지만 **호출자가 무엇을 import해야 하는지**는 적지 않는다). **한 것**:
`server.vwx.mvr`에서 상수를 가져와 `tools.py:2861`과 **같은 관용구**를 적용했다.
`server.orchestrator`를 import하면 `sheets → orchestrator` 의존이 생기는데, 그것은
판별 계층을 무겁게 만들고 순수 함수 요구와 어긋난다.

**G-6 — `AC-FILEARG-009` ②③은 A가 소유한 코드로는 만족시킬 수 없다.**
"종류가 정해진 **뒤에야** 실제 파싱이 정확히 한 번 돈다(파서 진입점 호출 계수 1) ·
행 수는 그 파싱에서 파생된다"는 **바이트를 나르는 층**의 성질이고, A의 판별기는
파서를 **아예 부르지 않는다**(그것이 ①의 요구다). 분할 기록은 "A는 순서 단언을
가진다"고 적지만 ②③의 문면은 남아 있다. 답했어야 할 곳: `acceptance.md` AC-009.
**한 것**: A의 범위 안에서 검사 가능한 형태로 읽었다 — 판별 중 파서 호출 **0회**를
단언하고(①④), 종류가 정해진 **뒤** 파서를 한 번 불러 레코드가 나오는 것을 보였다(②③).

**G-7 — M0 실측값이 `progress.md` §E.1에 반영돼 있지 않다.**
`baseline_measured`는 여전히 `미측정`이고 `base_sha`는 `6296af3`인데 실제 착수
기준선은 `1c104f0`이다. M0 기록처가 그 칸을 채우도록 돼 있으나(§E.1 문면이 스스로
"M0가 이 워크트리에서 직접 재서 채운다"고 적는다) 채워지지 않았다. §E.1은 plan-phase
소유라 run 세션이 고치지 않았다 — **실측값은 §E.2·§E.3에 적었다.**
**후속 종결(2026-08-24).** 리드 재정으로 두 칸을 채웠다(`base_sha: 1c104f0` ·
`baseline_measured`). 이월이 아니라 이 워크트리에서 **다시 쟀다**. 함께 관측된 것:
`known_baseline_failure`에 적힌 실패는 `1c104f0`에서 **관측되지 않는다**(전체 0 failed ·
`TestTouchedFilesPassLint` 3 passed). 그 칸은 리드가 지정한 두 칸이 아니므로 고치지
않고 관측만 남긴다.

### M1 후속 — zip 갈래 분기 (리드 재정 · G-2 종결)

**재정.** `PK` 매직이면 **두 형상 모두 신원 참**이다 — `SCENE_ENTRY`가 있으면 `.mvr`,
없으면 `.xlsx`. 둘 다 Vectorworks가 내보내는 형식이므로 신원은 참이고, *어느* zip인가는
신원이 아니라 뒷단이 가른다. 판독 **불가능한** 아카이브는 거짓 그대로다(경계 미확장).

**TDD 순서 — RED가 먼저 있었다.**

| 단계 | 명령 | 결과 |
|---|---|---|
| RED(수정 전) | `.venv/bin/python -m pytest server/tests/test_sheets_registry.py::TestZipShapes -q` | `3 failed, 3 passed` — 요지 `assert ('unknown_sheet_kind', ()) == ('resolved', ('vectorworks',))` |
| GREEN(수정 후) | 같은 명령 | `6 passed` |
| 모듈 전체 | `.venv/bin/python -m pytest server/tests/test_sheets_registry.py -q` | `89 passed` (83 → **+6**) |

RED이 **빨강 3 / 초록 3**으로 갈린 것이 핵심이다. 새로 참이 되는 `.xlsx` 형상 3건만
빨갛고, 유지돼야 할 `.mvr` 형상 · 판독 불가 아카이브 · 비공허성 대조군 3건은 처음부터
초록이다 — 한 갈래만 열고 나머지 경계는 건드리지 않았다는 뜻이다.

**뮤테이션 1발 — 이 수정이 무엇을 지키는가.** zip 갈래에서 판독 가능성 검사를 지우고
`return True`만 남기면 `test_zip_magic_that_is_not_a_readable_archive_is_identity_false`가
`assert True is False`로 죽는다(`1 failed, 5 passed`). 즉 "두 형상 모두 참"은 "`PK`이면
무조건 참"과 **기계로 구분된다**. 복원은 sha256 대조로 확인했다(`56c0b74f…451ecf` 일치).
`git checkout --`가 되돌린 것은 **커밋된 수정 전 파일**이었으므로 수정을 다시 얹은 뒤
대조했다 — 초록이 아니라 **체크섬**이 복원의 증거다.

**전체 스위트.** 9968 → **9974 passed, 12 skipped, 0 failed**(증가 **+6** · 감소 **0**).
콘솔 정지 상태에서 쟀다(`pgrep app_gma3` 빈 출력). `ruff check` · `ruff format --check` 모두 clean.

**미검증으로 남긴 것 — 명세에는 있고 코퍼스에는 없다.**
코퍼스에 `.xlsx` 표본이 **0개**다. 표본을 날조하지 않았고, `SCENE_ENTRY` 유무만 다른
**인메모리 zip 형상 대조군**으로 술어 갈래만 고정했다. 따라서 셋이 열린 채로 남는다:

1. **실물 `.xlsx` 바이트가 신원 참을 받는가** — 형상은 맞췄으나 실물로 재지 않았다.
2. **`design.md` §4 결과 ④(`unapproved_dependency`)가 실제로 나오는가** — 이 재정으로
   `.xlsx`가 뒷단 판독기에 **닿게 되어** 도달 가능해졌으나, 이 저장소는 `openpyxl`을
   필수 의존으로 두므로 이 환경에서는 발화하지 않는다.
3. **뒷단이 `.mvr`과 `.xlsx`를 어떻게 가르는가** — 신원이 아니라 `SPEC-COPILOT-SHEETPIPE-001` 몫이다.

`.xlsx` 표본이 하나 생기면 **위 1·2를 그 자리에서 재라.**

## §E.3 Run-phase Audit-Ready Signal

```yaml
run_complete_at: 2026-08-24
run_commit_sha: bd21a4c          # M1 구현 커밋. 게이트 실행 HEAD는 e65e1c2(뮤테이션 커밋 1b6b60a의 revert)
run_status: complete-with-findings
ac_pass_count: 19
ac_fail_count: 0
ac_na_count: 1                   # AC-021 안전판 — 위임 술어가 페이로드 10/10을 흡수해 조건 미발동
milestones_complete: "M0(리드 실측) · M1"
baseline_measured: "9885 passed, 12 skipped, 0 failed @ 1c104f0 (M0가 이 워크트리에서 직접 잼)"
suite_after_run: "9968 passed, 12 skipped, 0 failed @ e65e1c2 — 증가 +83 · 감소 0"
new_tests: 83
new_warnings_or_lints_introduced: 0    # ruff format/check 모두 clean
preserve_list_post_run_count: 10       # _PRESERVE_PATHS 불변
boundary_gate: "PASS — 대조 빈 출력(양성 대조군 확인) · test_overlap_preserve 41 passed · 커밋 뒤 실행"
boundary_mutation: "PASS — server/web/preview.py 전제 빈 출력 확인 후 실행. 미커밋 초록 / 커밋 뒤 빨강 두 상태 모두 기록"
mutations_fired: 9                     # plan 4 + AC 4 + AC-027 임계(인메모리)
mutations_killed_target: 9
mutation_restore_proof: "sha256 대조 — registry.py 5fd78fe9…65b43f 8회 전부 일치"
assumption_75b: "확정 — LX-SEQ 헤더는 원시 신원 술어를 만족한다(idx=0, score=7). 배제 절이 있어야 75-b가 성립하며, 뮤테이션 ⑦이 그것을 고정한다"
fallback_req_018: "미발동 — plan.md §D.1은 갱신 대상 아님"
total_run_phase_files: 3               # server/sheets/__init__.py · registry.py · server/tests/test_sheets_registry.py
files_outside_boundary_touched: 0
live_session: 0                        # A는 콘솔도 앱도 건드리지 않는다
new_runtime_dependencies: 0
new_data_files: 0
tool_count_delta: 0                    # A는 툴을 등재하지 않는다
findings_for_sync: "결함 1(D-1: AC-021의 N/A 검증 토큰이 판별력 없음) · 관찰 2(O-1 -k 선택자 희석 · O-2 R24 가드 이름 충돌) · SPEC 공백 5건(G-1~G-5) — run 세션 보고서 소유"
```

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_

## §F.1 Phase 4 Mode Selection

- **tier**: **L**(constitutional — 레지스트리 계약 정의; 크기가 아니라 성격, `spec.md` §A.5) · **통과 임계 0.85** · **scope**: 3파일(신규 `server/sheets/__init__.py` · `server/sheets/registry.py` · `server/tests/test_sheets_registry.py`) · **domain**: 1(Python 백엔드 — UI 0) · **parallel benefit**: LOW.
- 평가: `direct` 미선택(신규 모듈 + 술어 설계, 사소하지 않다) · `fanout` 미선택(도메인 1, 조사형 아님) · `sweep` 미선택(기계적 일률 변환 아님) · **`serial` 선택**.
- **Decision: serial**
- **Justification**: 분할 후 A는 M0(게이트) → M1(판별기·레지스트리) 둘뿐이고 한 도메인·한 모듈이다. 마일스톤이 둘이므로 병렬화할 사슬 자체가 없다. 분할 전 근거(M1→M2→M3→M4 데이터 사슬)는 **B로 이관**됐다 — 세션 슬롯·래퍼 툴·UI 배선은 `SPEC-COPILOT-SHEETPIPE-001`이 자기 모드 선택을 기록한다.

_M1 — manager-develop 소유, Implementation Kickoff Approval 통과 후 착수 예정_
