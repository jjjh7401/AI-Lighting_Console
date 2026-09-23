# SPEC-LDDESIGN-001 구현 계획

## §A. 컨텍스트

- **대상**: 신설 `server/concept/` 패키지(컨셉 계층 — 워크시트 로더, Color
  Strip 산출, 회차 에스컬레이션 규칙, 헤드룸 계산, MIB 판정) + 기존
  `server/looks/songcue.py`·`server/design/song_cue_composer.py`(경로
  단일화 대상) + 기존 하류 재사용 대상(`server/design/{lint,energy,
  cue_fade}.py`, `server/director/validate/mib.py`) + UI
  (`ui/src/components/`).
- **⚠️ 착수 전 필수 동기화**: 이 SPEC을 작성한 시점의 primary checkout은
  `origin/main`(`9dd21171`)보다 **19커밋 뒤져 있다**
  (`git rev-list --count --left-right origin/main...HEAD` → `19 0` 실측,
  2026-09-21). 이 SPEC의 모든 코드 인용(행 번호 포함)은 별도 워크트리
  `scratchpad/wt-main`(`origin/main@9dd21171`)에서 직접 읽은 것이다.
  run-phase 착수 전에 primary checkout을 `origin/main`과 동기화해야 한다
  (`agent-common-protocol.md` § Pre-Spawn Sync Check 절차 그대로).
- **⚠️ M0 선행 조건이 아직 머지되지 않았다**: 이 SPEC이 인용하는 t429
  수정(브랜치 `WT-chorus-collision`, 커밋 `4d4cc94f`)은 `origin/main`에
  아직 없다. M1 이후 마일스톤을 착수하기 전에 M0(§F)을 먼저 닫아야 한다
  — REQ-LDDESIGN-001.
- **선행 완료 작업**: SPEC-LDRETURN-001(절정 복귀 큐 값 충돌 회피)이
  `build_songcue_bundle(bpm=...)` 공개 진입점을 통한 성공 삽입 경로를
  확보했다 — 이 SPEC의 M0(REQ-LDDESIGN-002, `bpm=density_bpm` 실제 배선)는
  그 위에서만 안전하다. SPEC-LDCLIMAX-001/LDACCENT-001이 정의한 절정
  지속시간 상한·액센트 사다리(REQ-LDCLIMAX-006~011)는 이 SPEC이 건드리지
  않는 별도 메커니즘이다(REQ-LDDESIGN-077).
- **이 SPEC의 성격**: 11편의 오늘 자 조사·검증 보고서와 그 근거
  프로토타입(`final_integrated.py`, 8곡 게이트 98 PASS/6 n/a/0 FAIL)을
  실제 저장소 구현으로 옮긴다. 프로토타입은 스크립트일 뿐 아직 코드가
  아니다 — M1~M6는 이 스크립트의 해석기(`apply`/`build` 함수)를 저장소의
  타입·모듈 구조로 재작성하는 작업이다.

## §B. 마일스톤 순서와 리뷰 우선순위

마일스톤 순서(M0~M8)는 **의존성** 순서다(선행 없이는 다음 단계가
성립하지 않는다). 단, 인간 리뷰가 가장 먼저 눈여겨봐야 할 결정 —
바뀔 가능성이 가장 큰 결정 — 은 의존성 순서와 다르다:

**리뷰 우선순위(변경 가능성 큰 순)**: M2(큐 모델 v2 — 새 타입 인터페이스,
`operation`/`layer`/`tracking`/`timing`/`mib` 7개 필드는 이후 모든
마일스톤이 이 스키마 위에서 동작하므로 여기서 잘못 정하면 M3~M6 전체가
재작업된다) → M3(컨셉·컬러 규칙 — 사용자 대면 워크시트 스키마와 팔레트
규칙, 감독이 직접 채우는 필드라 UX 영향이 크다) → M7(UI — 화면에 보이는
결과) → 나머지(M0·M1·M4·M5·M6·M8은 기계적 배선·회귀 고정·프로브에
가깝다).

빌드 순서는 아래 M0~M8 그대로 유지한다(§A의 의존 사슬을 깨지 않기
위해서다) — 단 리뷰는 M2·M3·M7의 산출물(타입 정의, 워크시트 스키마
문서, UI 목업)을 M0·M1·M4~M6·M8의 산출물보다 먼저, 더 꼼꼼히 본다.

## §C. 마일스톤

### M0 — 선행 조건 닫기 (REQ-LDDESIGN-001~004) — **닫힘 (2026-09-22)**

선행 조건 3건 모두 `origin/main` 에서 실측 확인했다(기준선 `b661da2d`,
`git rev-list --count --left-right origin/main...HEAD` → `0 0`).

| 항목 | 상태 | 증거 |
|---|---|---|
| `WT-chorus-collision`(`4d4cc94f`) 머지 | 닫힘 | `7447ca55` — `fix(t429): 회차마다 다른 라벨을 쓰는 업로드 경로에서 반복 코러스 충돌 해소 (#475)` |
| `build_songcue_bundle(...)` 에 `bpm=density_bpm` 배선 | 닫힘 | `server/orchestrator/tools.py:3240` (`density_bpm` 계산은 `:3177`), 머지 커밋 `b661da2d` (#476) |
| SPEC-LDRETURN-001 `status: completed` 선행조건 | 닫힘 | `.moai/specs/SPEC-LDRETURN-001/spec.md:5` → `status: completed`. `depends-on` override 불필요 — 대기·override 경로 모두 발동하지 않았다 |

**두 경로(`server/web/session.py` 확정 경로 · `tools.py:3230` LLM 툴
경로)의 큐 경로 단일화는 M0 에서 M2 첫 단계로 옮겼다** — 아래 M2 를
보라. 옮긴 이유: M0 에 남겨 두면 "회귀 시험만 고정"에 머물러 실제
통합은 M6 까지 미뤄지는데, 감독이 확정한 방향(인터뷰의 입구 + 대화의
엔진)은 큐 모델 v2 를 **단일 경로 위에** 올려야 성립한다. v2 타입을
두 경로에 각각 태우면 M2 산출물이 두 벌이 된다.

### M1 — 어휘 + 워크시트 + 재매핑 (REQ-LDDESIGN-005~016)

- 구간 9종·트리거 10토큰·원샷 7종 어휘 상수와 `VocabError` 예외 정의.
- 판정기 5종 → 9종 재매핑 표(신규 모듈, 예: `server/concept/vocab.py`).
- 워크시트 YAML 로더(`palette`/`concept`/`sections`/`notes` 4구획,
  `pydantic` 모델 또는 `dataclass` — 기존 저장소 관행 확인 후 결정).
- 파일: `server/concept/vocab.py`(신규), `server/concept/worksheet.py`
  (신규), `server/tests/test_concept_vocab.py`(신규),
  `server/tests/test_concept_worksheet.py`(신규).

### M2 — 큐 모델 v2 + 해석기 (REQ-LDDESIGN-017~025)

- **[M0 에서 이관] 큐 경로 단일화 — M2 의 첫 단계.** `server/web/session.py`
  확정 경로와 `server/orchestrator/tools.py:3230` LLM 툴 경로가 같은
  컴포저를 거치도록 배선을 실제로 합친다(회귀 시험 고정에 그치지 않는다).
  방향: **인터뷰가 입구, 대화가 엔진** — 감독이 워크시트/인터뷰로 넣은
  입력이 단일 컴포저에 들어가고, LLM 대화는 그 컴포저를 호출하는
  엔진으로만 동작한다. 아래 큐 모델 v2 타입은 이 단일 경로 위에 올린다.
  - 착수 전 실측할 것: 두 경로가 **같은 입력에 같은 결과**를 내는지
    (회귀 시험 먼저 → RED 확인 → 통합).
  - 관련 이름 충돌 정리도 여기서 한다 — `server/design/song_cue_composer.py`
    와 `server/looks/songcue.py` 가 각각 `SongCueBundle` 이라는 이름을
    쓴다. 2026-09-22 실측: 두 모듈을 동시에 import 하는 파일은
    `server/web/session.py` 하나뿐이고 이미
    `SongCueBundle as TimingSongCueBundle` 별칭으로 갈라져 있다
    (`session.py:123`), `design` 쪽 클래스 이름은 import 되지도 않는다
    — **현재 실제 충돌 0건**이므로 단독 선행 과제가 아니라 v2 타입
    정의와 함께 정리한다.

- 큐 모델 v2 타입 정의(`layer`/`operation`/`tracking`/`timing`/
  `evidence`/`headroom`/`mib` 7필드).
- `final_integrated.py`의 `apply()` 해석기(9종 동작: retain/add/remove/
  reduce/replace/isolate/expand/restore/release)를 저장소 타입으로
  재작성 — `restore`는 색 포함(REQ-020), `reduce`는 구간 기준 참조
  (REQ-021).
- 큐 설명 자동 생성기(REQ-023).
- 파일: `server/concept/cue_model.py`(신규), `server/concept/resolver.py`
  (신규), `server/concept/description.py`(신규),
  `server/tests/test_concept_resolver.py`(신규).

### M3 — 컨셉 계층 + 컬러 규칙 + 검사 (REQ-LDDESIGN-026~035)

- `server/concept/` 패키지 신설(순수 데이터, OSC/콘솔 접근 금지).
- Color Strip 산출(REQ-026), 유보색(REQ-027)·언더페인팅(REQ-028)·브리지
  (REQ-029)·후렴 주색 동일(REQ-030) 검사기.
- `_arc_palette`/`_per_chorus_palette` 회전 로직을 정체성 판정 경로에서
  제거(REQ-031) — 함수 자체는 삭제하지 않고 다른 목적(초안 생성 등)으로
  재활용 가능한지는 M3 내부 판단.
- 파일: `server/concept/color_strip.py`(신규),
  `server/concept/color_lint.py`(신규), `server/web/session.py`(수정 —
  `_arc_palette` 호출부 제거), `server/tests/test_concept_color_lint.py`
  (신규).

### M4 — 3층 밀도 + §4 회차 규칙 + 헤드룸 (REQ-LDDESIGN-036~052)

- 구간/프레이즈/원샷 3층 밀도 컴파일러(REQ-036), 빌드업(REQ-037)·눈
  리셋(REQ-038) 삽입 규칙.
- §4 회차 에스컬레이션 6축(REQ-043), 모션 분배(REQ-044), 4회 이후 밀도
  상한(REQ-045), Bridge remove(REQ-046)·구간 단위 감소 비교(REQ-047).
- 헤드룸 4축 계산 + 경고 4조건(REQ-050~052).
- 파일: `server/concept/density.py`(신규), `server/concept/escalation.py`
  (신규), `server/concept/headroom.py`(신규), `server/tests/
  test_concept_density.py`(신규), `server/tests/test_concept_escalation.py`
  (신규).

### M5 — 트래킹·타이밍·MIB·안전 큐 (REQ-LDDESIGN-053~072)

- 트래킹 4모드 해석(REQ-053~057).
- 타이밍 필드 배정(REQ-058~061) — 축별 딜레이 실제 명령 방출은 M8 이후
  별도 SPEC(§4 B군).
- MIB 판정기(REQ-062~067) — 어두운 창 판정은 §F 잠정값(이동 1.5초 +
  정착 0.5초)으로 구현하고, M8 프로브 실측 후 상수만 교체 가능하도록
  단일 지점에 둔다.
- 안전 큐 Q0.5/끝 Release(REQ-068~069), 근거 등급(REQ-071~072).
- 파일: `server/concept/tracking.py`(신규), `server/concept/timing.py`
  (신규), `server/concept/mib.py`(신규, `server/director/validate/mib.py`
  의 어두운 창 증명 원칙을 재구현·재사용 — import는 하지 않음, REQ-067
  근거), `server/tests/test_concept_tracking.py`(신규), `server/tests/
  test_concept_mib.py`(신규).

### M6 — 기존 하류 브리지 + 8곡 게이트 고정 (REQ-LDDESIGN-073~077)

- 큐 모델 v2 → 콘솔 명령 컴파일 경로가 `server/design/lint.py`(L1~L14),
  `server/design/energy.py`(D1~D5), `server/design/cue_fade.py`를
  재사용하도록 배선.
- `final_integrated.py`의 13게이트(G1~G13)를 `server/tests/
  test_concept_gates.py`(신규)로 고정, `pilot_baseline.json`(8곡) 기준
  회귀 기준선 — 오늘 실측치(PASS 98/n·a 6/FAIL 0)를 최소선으로 삼는다.
  이 시험 데이터는 `.claude/worktrees/pilot-labeling/pilot_baseline.json`
  을 그대로 참조하거나 `server/tests/fixtures/`로 복사한다(경로는 M6
  착수 시 확정).
- `server/orchestrator/tools.py`·`server/web/session.py`가 신규 컨셉
  계층을 통해 단일 컴포저를 호출하도록 최종 배선(M0에서 미룬 실제 통합).
- 파일: `server/design/song_cue_composer.py`(수정 — 컨셉 계층 결과
  소비), `server/orchestrator/tools.py`(수정), `server/web/session.py`
  (수정), `server/tests/test_concept_gates.py`(신규).

### M7 — UI (REQ-LDDESIGN-078~095, 096~101)

**감독 확인(2026-09-22) — 대상 화면은 런북 모드.** M7의 작업 대상은
코파일럿 메인 화면(grandMA3 콘솔 상태 거울)이 아니라, 이미 존재하는
런북 모드(`ui/src/components/RunbookMode.tsx`, 263행) 안의 컴포넌트
전면 재구성이다. 메인 화면 컴포넌트(`DashBoard`·`CueMonitor`·
`ChatView`·`SettingsPanel` 등)는 이 SPEC이 건드리지 않는다. `src/
DESIGN.md`(수령 디자인) §0이 이 전제를 확정했다 — 아래 D-step 시퀀스와
컴포넌트 목록은 변경 없음(런북 모드 안의 컴포넌트라는 사실이 파일
경로를 바꾸지 않는다). REQ-082의 "12열+2열" 전제가 실측(`CueSheetTimeline.
tsx:225`)으로 틀렸음이 드러나 spec.md §3.14 REQ-082를 정정했다 — CUE
SHEET는 이미 14열이었고, **정확히 14열(기존 9열 유지 + 신규 5열
추가: 회차·Trigger·MIB·Track 예외·근거 등급, 기존에만 있던 5열
`TC Out`·`Dur`·`Mood`·`Trans`·`Note`는 전부 제거)로 확정됐다(감독
결정, 2026-09-22, §3.14 참조).** `src/DESIGN.md`가 REQ-079/080보다
넓은 디자인(한눈에 5단계+탭 3개)을 돌려줬다 — 감독이 2026-09-22
그 디자인 전체를 채택해 spec.md §3.16 REQ-LDDESIGN-097(5단계 카드)·
098(탭 3개 구조)로 요구사항화했다.

**감독 결정(2026-09-22, 둘째) — PLAN CUE 카드 하단의 "PLAN CUE 수정요청
생성기"는 M7 범위로 확정됐다(spec.md §3.15, REQ-LDDESIGN-087~095).**
이 항목은 더 이상 "감독 결정 대기"가 아니다. 생성기는 REQ-083(PLAN
CUE 카드 하단 3줄 + `Q###` 배지)의 문언을 바꾸지 않고 그 카드 하단에
얹히는 별도 조작면이며, **M2(큐 모델 v2)의 그룹 스코프 `layer`/
`operation`이 있어야만 성립한다** — M7 내부에서도 생성기 관련 작업은
읽기 전용 표면(컨셉 패널·타임라인·CUE SHEET·상태줄)을 구현한 **다음에**
착수한다(아래 M7 구현 순서 참조). 자유 입력 한 줄과 변경 스택
항목별 제거(`✕`)도 감독이 같은 날 채택해 spec.md §3.16
REQ-LDDESIGN-101·100으로 각각 요구사항화됐다 — 둘 다 더 이상
"감독 결정 대기"가 아니다.

**감독 결정(2026-09-22, 셋째) — IBM Plex 웹폰트는 채택하지 않는다.**
`src/DESIGN.md` §2가 확정한 `IBM Plex Sans KR`+`IBM Plex Mono`는
시스템 폰트로 대체한다(REQ-LDDESIGN-099, §3.16) — 공연장 오프라인
환경에서 폰트 로딩 실패 위험과 번들 증가를 피하기 위함이다. 수치
열의 세로 정렬은 `font-variant-numeric: tabular-nums`로 유지한다.
새 파일은 필요 없다 — 전역 CSS(폰트 스택 선언)와 수치 표시 컴포넌트의
클래스에 `tabular-nums`를 추가하는 것으로 끝난다.

**Conditional Design Route 적용 여부: 적용됨(2026-09-22 감독 결정 —
`plan → design → run`, `manager-design` 투입).** 기존 판단("미적용 —
`plan → run` 직행")은 뒤집혔다. `spec-workflow.md` § Conditional
Design Route의 UI-surface 휴리스틱(명시적 프론트엔드 산출물 OR
`tier: L` + 프론트엔드 모듈)은 이 SPEC의 `tier: L` + `module:`의
`ui/src/components/`로 성립하며, REQ-078의 "기존 레이아웃 유지"
제약과 `reports/final-verification-20260921.html`의 기존 데모는
design-phase를 생략하는 근거가 아니라 **design-phase 브리프의 입력**
으로 재해석한다 — 국소적 변경이라도 감독이 보게 될 실제 화면(컨셉
패널 인터랙션, 6칸 문법표, GATE 배지 등)은 Claude Design 시안으로
먼저 확정한 뒤 구현에 들어간다.

**D-step 시퀀스** (design.md §2.1 파이프라인과 동일):

1. D1 디자인 시스템 확인 — `manager-design`이 DesignSync 프로젝트 확인.
2. D2 브리프 전달 — `.moai/specs/SPEC-LDDESIGN-001/design/handoff-
   brief.md`를 Claude Design에 전달(§screens.md·§tokens.md·
   §constraints.md 동봉).
3. D3 Claude Design 작업 — 7개 표면(컨셉 패널·타임라인·CUE SHEET·
   PLAN CUE 카드·PLAN CUE 수정요청 생성기·상태줄·스크롤 연동) 시안 생성.
4. D4 수령 — `design/review-checklist.md`로 REQ-078~095·096~101·
   AC-018~020·AC-034~044·049~053 대조, 예약 경로 페이스트.
5. D5 구현 반영 — 통과분을 `manager-develop`에 Section A-E 배차,
   PRESERVE 목록에 `design/` 산출물 포함. 아래 구현 순서는 D5 이후
   적용 대상이다.

**M7 구현 순서 — 읽기 전용 표면 먼저, 생성기는 마지막(M2 의존).**
M7은 별도 마일스톤으로 쪼개지 않지만, 내부 착수 순서는 다음을 따른다
— 생성기(6번)는 읽기 전용 표면이 큐 데이터(구간·색·헤드룸·MIB)를
이미 화면에 정확히 보여주고 있어야 조작 대상(그룹·값·프리셋)이
성립하고, 그 데이터 계약은 M2의 그룹 스코프 큐 모델 v2가 없으면 아예
정의되지 않기 때문이다:

1. 시스템 폰트 스택 + `tabular-nums` 전역 적용 — REQ-099(§3.16, 다른
   컴포넌트 작업의 전제가 되는 스타일 기반이므로 먼저 처리).
2. 컨셉 패널 "한눈에" 5단계 카드(REQ-097) + 탭 3개 구조(REQ-098) +
   기본 접힘·클릭 시 설명 4칸 — REQ-079/080, 신규 컴포넌트.
3. 탭 1 인과 불릿 + 6칸 문법 요약 표 — REQ-080.
4. 타임라인 블록 색 = Color Strip, 원샷·Mark 점 줄 — REQ-081.
5. CUE SHEET 재구성(정확히 14열 — 기존 9열 유지 + 신규 5열 추가:
   회차·`Trigger`·MIB·`Track 예외`·근거 등급, 기존에만 있던 5열
   `TC Out`·`Dur`·`Mood`·`Trans`·`Note`는 전부 제거, 감독 결정
   확정 — §3.14 참조) — REQ-082. `Trans` 값은 데이터 모델·수정
   경로에서 존속한다. 감독 결정(2026-09-23): 화면 열에서 제거하고,
   변경 경로는 대화창(`cue_sheet_edit.py:230`) 하나만 둔다. 생성기에
   조작을 추가하지 않고, 데이터 모델과 `SNAP`→fade 0 접기는 그대로
   둔다 — REQ-096.
6. 상태줄 GATE 표시 + 타임라인↔CUE SHEET 스크롤 연동 — REQ-084/085.
7. **(마지막, M2 완료 전제)** PLAN CUE 카드 하단 3줄 + `Q###` 배지
   (REQ-083, 변경 없음) 위에 PLAN CUE 수정요청 생성기를 얹는다 —
   그룹 다중 선택 + 혼합 표시(REQ-088) → 우측 콘솔 반영 값 패널·
   프리셋 이름 저장(REQ-089) → BLIND 잠금(REQ-090) → 변경 스택 +
   상태 라벨 + 항목별 경고 병기(REQ-091, REQ-093) + 항목별 제거
   `✕`(REQ-100) → **"선택 취소" 버튼을 기존 `↶ 되돌리기`
   (`CueSheetTimeline.tsx:612`, `TimelineDraftHistory`)와 분리
   배선(REQ-095 — 서버 미전송 확인)** → 자유 입력 한 줄, REQ-092
   경로 재사용(REQ-101) → 서버 단일 진실·파서 우회 금지 배선
   (REQ-092, `server/design/cue_sheet_edit.py` 재사용 확인) →
   대화 기록 연속성(REQ-094).
- 파일: `ui/src/components/ConceptPanel.tsx`(신규),
  `ui/src/components/SongTimeline.tsx`(수정 — PLAN CUE 카드 +
  수정요청 생성기가 위치하는 파일, REQ-083·087~094 전부 여기),
  `ui/src/components/CueSheetTimeline.tsx`(수정),
  `ui/src/components/StatusBanner.tsx`(수정), 대응 `*.test.tsx` 각각.
  생성기가 호출하는 서버 경로 `server/design/cue_sheet_edit.py`·
  `server/web/session.py:9351`·`server/web/timeline_draft.py`
  (`TimelineDraftHistory`)은 REQ-092·REQ-095에 따라 **재사용만** 하고
  이 SPEC이 재구현하지 않는다(PRESERVE).

### M8 — 실기 콘솔 검증 1곡 + 프로브 3종

- 곡 1개(Rain 권장 — 오늘 보고서 전부가 이 곡을 기준으로 실행값을
  냈다)를 M0~M7 완료된 파이프라인으로 실제 콘솔(grandMA3 onPC)에 반영,
  Sequence + Cue + Timecode 저장, 리드백 확인, 후렴 색 동일 육안 확인.
- 프로브 3종(§4 B군): Block/Release 문법, 축별 딜레이(순차) 문법, Mark
  문법. 결과에 따라 §3.9~§3.11의 데이터 필드는 그대로 두고 콘솔 명령
  방출 계층만 별도 후속 SPEC으로 연결한다.
- 산출물: `progress.md`(run-phase에서 신설)에 콘솔 반영 로그, 프로브
  결과 3종 기록.

## §D. 알려진 이슈

- **D1 — 컨셉 계층과 기존 3밴드 스키마의 경계.** `server/looks/
  schema.py`의 밴드 1~3(Dimmer/ColorRGB, Pan/Tilt, Zoom/Iris)은 이
  SPEC이 건드리지 않는다. 큐 모델 v2의 새 필드(`layer`/`operation` 등)는
  이 3밴드 값을 **참조**하고 **조작**하되, 밴드 자체를 확장하지 않는다
  — Gobo/Prism/객석광 확장은 §4 비목표(C군)다.
- **D2 — `_arc_palette`를 삭제할지 재활용할지는 M3에서 결정.** REQ-031은
  "정체성 판정 경로에서 더 이상 호출되지 않는다"만 요구한다 — 함수
  자체를 삭제하는 것은 이 SPEC이 강제하지 않는다(다른 소비자가 있는지
  M3 착수 시 grep으로 확인 필요).
- **D3 — 게이트 회귀 기준선의 데이터 파일 위치.** `pilot_baseline.json`은
  현재 `.claude/worktrees/pilot-labeling/`(임시 워크트리)에 있다 — M6
  착수 시 이 파일이 여전히 존재하는지, 저장소 정본 위치(`server/tests/
  fixtures/` 등)로 옮겨야 하는지 확인이 필요하다.
- **D4 — `server/director/validate/mib.py`와 M5 신규 MIB 판정기의 중복
  가능성.** REQ-067은 명시적으로 "import하지 않는다"고 정했다(계약
  경계가 다르다 — `mib.py`는 director 교환 경로 전용). 이 결정이
  중복 유지보수 비용을 만든다는 점을 M5 착수 시 재확인하고, 만약 공통
  로직을 뽑아낼 가치가 있다면 별도 리팩터 카드로 제안한다(이 SPEC의
  범위를 넓히지 않는다).
- **D5 — 색 표현 방식 확장은 t430~t433로 미룬다(2026-09-23 감독 발의).**
  10색 고정 표(`server/design/color_names.py`)를 RGB 좌표나 젤 번호로
  넓히자는 감독 질의는 이 SPEC의 범위가 아니다 — M2가 배선한 경로는
  10색 표 위에서만 돈다. 조사와 4단계 후속 과제(W 채널 구동 → 젤 번호
  → CIE 좌표 → 쇼별 색 사전)는
  `docs/proposals/2026-09-23-color-representation-expansion.md`에
  기록했고, 백로그 카드 t430~t433이 이를 잇는다.

## §E. 자기검증

- [ ] REQ-LDDESIGN-001~101 전량이 acceptance.md의 AC 또는 §E의 게이트
  매핑(G1~G13)으로 추적 가능한가 — spec.md 각 REQ 표의 `[G#]` 표시와
  acceptance.md AC 목록을 교차 확인.
- [ ] M0~M8 각 마일스톤의 "파일" 목록이 실제 존재하거나(수정 대상) 신설
  계획에 있는가.
- [ ] §F 잠정값 3건이 Implementation Kickoff Approval 시점에 감독
  재확인을 거쳤는가(잠정값 그대로 착수 승인 받았는지, 또는 값이
  바뀌었는지).
- [ ] 8곡 게이트 회귀 기준선(§C M6)이 오늘 실측치보다 나빠지지 않는가.

## §F. 잠정값 — M8 콘솔 프로브로 확정

이 세 항목은 값이 정해지지 않은 빈칸이 아니라 **이미 채택된 잠정값**이다
— 착수를 막지 않는다. Implementation Kickoff Approval 시점에 감독이
세 값을 재확인하고, 실제 콘솔 값은 M8 프로브(acceptance.md
AC-LDDESIGN-022~024)로 실측치로 교체한다.

- **MIB 이동/정착 초 = 이동 1.5초 + 정착 0.5초**(프로토타입 가정값,
  REQ-LDDESIGN-062가 그대로 채택). 근거: `tracking-timing-mib-
  20260921.md` 한계 절 — "이동 1.5s + 정착 0.5s는 가정. 기종별 실측
  없음". M5는 이 값을 상수로 구현하되 단일 지점에 두어 M8 실측 후
  교체가 한 곳만 바뀌도록 한다. 잠정값임을 큐 설명(REQ-023)과 근거
  등급(`evidence: designed_rule`)에 명시한다.
- **콘솔 문법 3종(Block/Release, 축별 딜레이/순차, Mark)은 M8 프로브
  결과로 확정한다.** 이 저장소에서 실기 관측 0건이다(`server/
  director/emit.py:60` `AXIS_TIMING_OBSERVED` 주석, `tracking-timing-
  mib-20260921.md` "셋 다 미실측"). 그때까지 컴파일러는 이 세 필드를
  실제 콘솔 명령으로 방출하지 않고, 주석/메타데이터(예: 큐
  `description`의 부기 문구, 또는 별도 `pending_console_syntax` 메타
  필드)로만 출력한다 — §4 B군, spec.md §4 "콘솔 프로브가 필요한 문법".
- **`allow_strobe` 기본값 = `false`.** 이것이 잠정값이자 채택값이다
  — 감독이 워크시트에서 곡마다 명시적으로 켜야만 스트로브 큐가
  생성된다. 근거: `server/web/preview.py:131-139`가 스트로브·셔터를
  이미 `danger` 분류로 표시하고 있다(`lighting-director-upgrade-
  20260921.md` 문서 자체에 대한 비판 절). §3.7(Final Chorus 스트로브
  해제, REQ-048류)의 스트로브 해제 동작은 이 기본값이 `true`로 바뀐
  곡에서만 실제 콘솔 명령을 방출한다.

세 잠정값 모두 Implementation Kickoff Approval 시점에 감독 재확인
대상이며, M8에서 실측치로 교체된다(§C M8, acceptance.md AC-022~024).
