# SPEC-LDDESIGN-001 — AC 마무리(서버 쪽): AC-017 · AC-040

- 기준 트리: `30f02eb5`(`origin/main`, sync PR #529 머지 뒤), 워크트리 `.claude/worktrees/ac-server`
- 콘솔 접속: 0회
- 원시 출력: `.moai/state/verify/ac-server/` (gitignore 대상이라 이 PR 에는 없다 — 아래에 줄 단위로 옮겼다)
- 분류표 원본: `ac_evidence_map.md`(이 파일은 그 표를 고치지 않고 두 AC 의 판정만 덧붙인다)

## 요약

| AC | 이전 분류 | 이번 판정 | 한 줄 근거 |
|---|---|---|---|
| AC-017 | UNVERIFIED | **미충족(구조 미통합)** | 업로드 길 `tools.py` 는 조립기를 한 번도 부르지 않는다(참조 0건) — 두 길은 여전히 다른 조립기다. 공유된 것은 색 결정(t441)과 어둠·절정 기준값(t462)뿐 |
| AC-040 | UNVERIFIED(부분) | **PASS(n/a 2종 제외)** | 구현된 4종 중 재사용 3종(리저브·헤드룸·MIB)은 서버 필드를 읽기만 한다 — UI 비시험 코드에 계산 로직 0. 시험 65+46 passed |

## AC-017 — 큐 생성 경로가 하나다

### 주장

AC 문면("두 경로가 생성한 큐시트(구간·순서·값)가 동일 — 하나의 컴포저를 공유한다는 증거")은 **t462 머지 뒤에도 충족되지 않는다.**

### 증거

1. 호출 그래프(정적 판독, `30f02eb5`):

   ```
   server/orchestrator/tools.py composer=0 bundle=6
   server/web/session.py composer=5 bundle=0
   ```

   (`grep -c -E 'compose_song_cue_bundle|song_cue_composer'` / `grep -c build_songcue_bundle`)

   - 대화 길: `server/web/session.py:9038`, `:11236` → `compose_song_cue_bundle(...)`
   - 업로드 길: `server/orchestrator/tools.py:3498` → `build_songcue_bundle(...)`

2. 두 길이 실제로 공유하는 부분:
   - 구간별 주색 결정 — t441(`191f6529`)이 공용 함수로 합쳤다. `uv run pytest -q server/tests/test_chorus_color_two_paths_t441.py` → `26 passed in 1.41s`
   - 드롭 앞 어둠·절정 길이 상한·블라인더 기준값 — t462(`4a2f38c9`)가 조립기에서 `server/looks/songcue.py` 의 순수 함수를 **불러다 쓰게** 했다(`song_cue_composer.py:34` `from server.looks.songcue import LADDER_BLINDER_OR_FLASH, climax_cap_beats, darkness_target`). 업로드 길 명령은 바이트 동일(t462 판정서 §3 ②).

3. 업로드 길 입구(`prepare_songcue`)를 조립기로 옮기는 일을 맡은 열린 카드: **없음** (`moai todo` 에서 dropped 이외 행 중 `REQ-003|build_songcue_bundle|조립기|AC-017|REQ-077` 일치 0행). t448 판정서 §1.4 도 "갈아타는 것은 B 의 입구 하나"라고 적었고, t462 는 범위를 좁혀 이 입구 전환은 하지 않았다.

### 기준 귀속

`30f02eb5` 트리에서 이번 세션이 직접 실행한 grep·pytest. t441·t462 판정서 인용은 옮긴 값이다.

### 안 잰 것

- 같은 곡을 두 길에 넣어 **큐시트 전체(구간·순서·값)를 diff** 하는 실측은 하지 않았다. 두 길의 입력 형태가 다르다(업로드 길은 raw 구간 dict, 대화 길은 `UnifiedSongLightingPlan`). 호출 그래프에서 이미 "하나의 컴포저" 전제가 깨졌으므로 diff 가 0 이 나올 수 없다고 보고, 그 대조 도구를 새로 만들지 않았다.
- t441 의 `probe_command_diff.py` 는 **업로드 길 하나 안에서** 인터뷰 기록 유무를 비교한 것이라 이 AC 의 두 길 비교 증거가 아니다.

### 남은 위험 · 닫는 방법(리드 판단)

- (가) 업로드 길 입구를 조립기로 옮기는 카드를 새로 만든다 — t448 감독 결정 ①("A 로 합친다")의 남은 절반.
- (나) 또는 마지막 닫기에서 AC-017 문면을 t448·t462 결정에 맞춰 "기준값·색 결정을 공유한다"로 좁힌다(SPEC 본문 수정 → manager-spec).

## AC-040 — 파생 경고 6종, 재사용 대상은 재계산하지 않는다

### 주장

n/a 2종을 뺀 나머지는 AC 를 충족한다. 재사용 3종은 서버가 이미 계산한 필드를 그대로 읽고, UI 쪽에 별도 계산 로직이 없다.

### n/a 2종 (감독 결정, 옮긴 값)

- (2) 팬 폭 ±25° · (6) 페이저 = BPM — `ui/src/components/cueRequestWarnings.ts:1-5` 머리 주석(D3 감독 결정 2026-09-27). t467(PR #515, `ea91c389`) 감독 결정: 서버에 페이저 속도 값이 없고, 좌표로 계산한 팬 퍼짐은 모이는 룩에서 경고 뜻과 반대. t473(PR #520): 응답기 1.6.5 로 두 값 모두 콘솔에서 읽히지 않음.

### 증거 — 구현 4종과 원천

| 경고 | UI 판정 함수 | 읽는 필드 | 서버 원천 |
|---|---|---|---|
| (1) 후렴 밝기 역전 [신규] | `cueRequestWarnings.ts:18` `chorusReversalWarning` | 구간 밝기(UI 가 계산 — REQ-093 이 "신규"라 허용) | — |
| (3) 리저브 위반 [재사용] | `cueRequestWarnings.ts:40` `reserveViolationWarning` | `concept_report.reserve[].released_q` | `server/concept/session_bridge.py:197` `_concept_reserve`(REQ-027 유보색·REQ-090 BLIND 잠금) |
| (4) 헤드룸 < 4 [재사용, 임계값만 신규] | `cueRequestWarnings.ts:56` `headroomWarning` | `rows[].unused_groups` | `session_bridge.py:182` `compute_cue_headroom(state).unused_groups`(REQ-050) |
| (5) MIB live [재사용] | `cueRequestWarnings.ts:64` `mibLiveWarning` | `rows[].mib` | `session_bridge.py:176` `build.mib` 판정(REQ-066) |

코드 검사 — UI 비시험 파일에서 세 필드가 나오는 곳 전부(`grep -rn -E "unused_groups|released_q|\.mib\b" ui/src --exclude='*.test.*'`, 21행):

- `protocol.ts:482-513` — 타입 선언
- `cueRequestWarnings.ts:47,48,57,58,65` — 비교·표시만
- `SongTimeline.tsx:157,158,165,228`, `CueSheetTimeline.tsx:777`, `runbookM7.ts:90,174,201,202,249`, `PlanCueRequestGenerator.tsx:98,108` — 표시·잠금 판정용 읽기

세 값을 **만들어 내는** 줄(대입·계산)은 0행이다. 재계산 로직 없음.

시험(이번 세션 실행):

```
$ npx vitest run src/components/cueRequestWarnings.test.ts src/components/PlanCueRequestGenerator.test.tsx src/components/SongTimeline.test.tsx
 Test Files  3 passed (3)
      Tests  65 passed (65)
exit=0

$ uv run pytest -q server/tests/test_concept_reserve_t461.py server/tests/test_concept_color_lint.py server/tests/test_concept_headroom.py
46 passed in 0.33s
exit=0
```

`cueRequestWarnings.test.ts:81` `describe("headroomWarning / mibLiveWarning — consume, never recompute (AC-040)")` 가 서버 필드 부재 시 n/a(지어낸 결함 없음)까지 단언한다.

### 기준 귀속

`30f02eb5` 트리, 이번 세션 실행. vitest 는 이 워크트리에 설치본이 없어 주 체크아웃의 `ui/node_modules` 를 심볼릭 링크로 빌려 돌렸다(커밋하지 않음, 실행 뒤 제거).

### 안 잰 것

- 8곡 실곡에서 경고가 실제로 몇 건 뜨는지(AC 의 Given "각 경고 조건을 유발하는 큐가 있는 곡들")는 재지 않았다 — 판정은 단위 시험과 코드 검사 근거다.
- 브라우저 화면에서의 표시는 보지 않았다.

### 남은 위험 · 닫는 방법

- AC 문면은 여전히 "6개 조건"을 적고 있다. 마지막 닫기에서 AC-021 처럼 "(2)(6) 은 감독 결정으로 n/a(t467·t473)"를 문면에 반영해야 문면과 구현이 맞는다(SPEC 본문 수정 → manager-spec).
