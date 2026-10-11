# t551 run 판정서 — SPEC-LDBEAT-001 M3 박자 격자 칸 편집

- 카드: t551 · 레인: lane-3 · 브랜치: `WT-ldbeat-grid-edit` · 기준: `af00ffb2`(origin/main) · HEAD: `21db2ea3`
- 범위: REQ-LDBEAT-007~009·015 (M3). 콘솔 쓰기 0건 — 콘솔 접촉은 시험용 가짜 콘솔뿐이다.
- 작성: lane-3 가 아래 명령을 이 트리에서 직접 다시 돌려 확인했다. 구현 에이전트의 보고 숫자를 옮겨 적지 않았다.

## 무엇이 생겼나

1. **서버 편집 연산 `apply_beat_grid_edit`** (`server/design/beat_grid_edit.py`) — 편집 세 길이 모두 이 한 함수로 들어온다. 부분 적용 0건이고, 거절할 때는 원인 하나만 지목한다. 그룹 스코프는 기존 `layer_role` 관행을 그대로 따른다.
2. **전용 WS 채널** (`server/web/session.py`·`messages.py`) — 채팅 명령 디스패치 체인에는 섞지 않았다.
   - `beat_grid_edit`: 직접 고르기
   - 문장 길: `server/design/beat_grid_sentence.py`
   - `beat_grid_suggest`·`beat_grid_suggestion_apply`·`beat_grid_suggestion_reject`: AI 제안. 「적용」 전에는 초안이 바뀌지 않는다. 운영 기본 제안 소스는 `NullSuggestionSource`다.
3. **프리셋 카탈로그** (`server/design/beat_grid_presets.py`) — 기존 판독 경로를 재사용한다. 새 판독 규율은 만들지 않았다.
   - `console_slots.paged_pool_children`/`resolve_named_pool_no`
   - `preset_names.match_preset_name_across_pools`
4. **UI** (`ui/src/components/BeatGrid.tsx` 외)
   - 명령창 「문장 적용」·「AI 제안」
   - 오른쪽 편집 칸 드롭다운: 밝기 단일모드(값/디머 프리셋/디머 효과), 위치·색·효과(움직임) 프리셋. 묶음은 목업 그대로 「이 곡 프리셋」/「쇼에 이미 있는 프리셋」/「+ 새 프리셋 만들기…」.
   - 프리셋 서랍: 풀별 목록, `쓰는 곳: 큐 N개` 툴팁, 클릭하면 쓰는 막대를 강조.
   - AI 제안 점선 막대.
   - `preset_pools.yaml` 의 `confirmed: false` → 「⚠ 번호대 미확인」 배지(서랍과 드롭다운 옆).
5. **번호대 데이터** `server/design/beat_grid_data/preset_pools.yaml`
   - `confirmed: false` 이고 값은 잠정이다. 출처는 목업 md 14-17·26-29 의 「예시 번호」다.
   - 리드 결정(옵션 A): 번호대 밖 선택은 confirmed:false 동안 **경고**, confirmed:true 이면 **거절**.

## 증거 (이 트리, HEAD 21db2ea3, 2026-10-11)

| 확인 | 명령 | 결과 |
|---|---|---|
| 서버 t551 + 큐시트 편집·위치 효과 회귀 | `uv run --quiet pytest server/tests/test_beat_grid_edit_t551.py server/tests/test_session_beat_grid_edit_t551.py server/tests/test_beat_grid_presets_t551.py server/tests/test_cue_sheet_edit.py server/tests/test_position_fx.py -q` | `217 passed in 1.16s` |
| 린트 | `uv run --quiet ruff check server/` | `All checks passed!` |
| 포맷 | `uv run --quiet ruff format --check server/design server/web server/tests` | `527 files already formatted` |
| UI 타입 | `cd ui && npx tsc --noEmit` | 출력 없음(깨끗) |
| UI 시험 | `cd ui && npx vitest run` | `Test Files 35 passed (35)` · `Tests 882 passed (882)` |
| AC-005 UI 페이로드 직접 구성 | `grep -rnE "changes\s*=\s*\{" ui/src \| wc -l` | `0` |
| 번호대 리터럴(코드) | `grep -nE '"[0-9]+\.[0-9]+"' server/design/beat_grid_presets.py server/design/beat_grid_edit.py` | 0건 |
| M4(t549) 겹침 | `git diff --stat af00ffb2..HEAD -- server/design/beat_grid.py` | 0줄 |

RED→GREEN 순서는 구현 에이전트가 기록했다(`progress.md` M3 절). lane-3 는 GREEN 쪽만 다시 돌렸다.

## AC 대조

### M3 본 AC (acceptance.md, 기준 af00ffb2)

| AC | 판정 | 근거 |
|---|---|---|
| AC-LDBEAT-005 세 길 → 새 연산 | PASS | 세 길이 모두 전용 채널을 거쳐 `apply_beat_grid_edit` 로 간다. UI `changes={` 0건. 격자 UI 소스에 `parse_cue_sheet_edit_request\|apply_cue_sheet_edit` 0건(에이전트 grep, 파일 목록 progress.md). AI 제안은 「적용」 전 상태 diff 0 을 시험이 확인한다. |
| AC-LDBEAT-010 범위 밖 요청 거절 | PASS | 단일 원인 거절 문자열이 UI 에 그대로 보이고, 거절 시 격자 변경 0. 시험 `test_session_beat_grid_edit_t551.py` |
| AC-LDBEAT-016(a) 번호대 밖 거절 | **문면 불일치 — 판단 필요** | AC 문면은 무조건 「거절된다」다. 리드 결정 A 이후 구현은 confirmed:false 동안 경고만 한다. spec REQ-015 증거 칸은 번호대를 「재확인 대상」이라 적고 있다. acceptance.md 개정이 필요하다(manager-spec 소관, 이 카드에서 고치지 않았다). |

### t554 신규 AC (origin/WT-ldbeat-ui-design @ 9cfc1783) — 이 카드가 손댄 자리만

| AC | 판정 | 근거 |
|---|---|---|
| AC-021(b) 편집 칸 필드 순서 | 부분 | 밝기→위치→색→움직임 순서다(`BeatGrid.tsx:1346-1358`). 「들어올 때」는 필드 목록에 없다. 옆빛 L·R·콘솔명령 행은 이 카드 범위 밖(M9)이다. |
| AC-021(a)·AC-023 「이 마디 한눈에」 표 | 해당 없음 | 이 카드는 표를 건드리지 않았다(표 클릭 핸들러 0 — 023(a) 「제자리 변경 0」은 유지). 023(b)(c)(d)는 M9 몫이다. |
| AC-025(a) 문장 즉시 해석 | PASS | `beat_grid_sentence.py` → 같은 연산. 정해진 꼴 밖이면 단일 원인으로 거절한다. |
| AC-025(b)(c) AI 제안 점선·수락 전 변경 0 | PASS(메커니즘) | 점선 막대와 적용/거절 버튼이 있다. 실제 AI 소스는 없다(`NullSuggestionSource`). 렌더는 시험용 가짜 소스로만 확인했다. |
| AC-025(d) 서랍 — 쓰는 큐 수·강조·번호대 리터럴 0 | 부분 | 쓰는 수 툴팁(`BeatGrid.tsx:1926`)·클릭 강조(`:1190`)가 있고 코드 리터럴은 0건이다. 다만 번호대는 쇼 파일이 아니라 `preset_pools.yaml`(잠정)에서 읽는다 — AC 문구 「쇼 파일에서 읽음」과 다르다. |
| AC-019(a) 상태 4종 중 AI제안=점선 | 부분 | 점선만 이 카드가 만들었다. 고침/같은프리셋 상태는 M9 몫이다. |

## 안 잰 것

- 실제 콘솔: 프리셋 풀 판독·번호대 대조 모두 가짜 콘솔로만 시험했다. 번호대는 `confirmed: false` 그대로다.
- 실제 AI 제안 소스는 없다. 운영 기본값은 제안이 나오지 않는다.
- 브라우저 화면 육안 확인 0회. 목업과의 대조는 문구 인용과 DOM 시험뿐이다.
- 전체 시험 묶음은 돌리지 않았다(레인 로컬 원칙). 전체는 CI 몫이다.
- t554 브랜치를 합친 트리에서 시험을 돌리지 않았다. AC 문면만 대조했다.

## 남는 위험

- `ui/src/protocol.ts`: 기존 한 줄 `| SongTimelineEvent;` 의 세미콜론을 떼고 유니온 항목을 이었다. t549(M4)도 같은 유니온 끝에 붙이면 머지 충돌 자리다.
- AC-016(a) 문면과 구현(경고)이 어긋난다. acceptance.md 개정 전까지 감사에서 FAIL 로 읽힐 수 있다.
- `BeatGrid.tsx:1376` 주석이 「효과·디머 효과는 아직 읽기 전용」이라고 적혀 있다. 옵션 A 이후 낡은 주석이다.
- `isBrightnessValueEditable` 은 컴포넌트에서 더는 호출되지 않는다(export·시험은 남아 있다).
