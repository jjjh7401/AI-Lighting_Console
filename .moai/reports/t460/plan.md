# t460 계획 — PLAN CUE 수정요청 생성기 (SPEC-LDDESIGN-001 M7 4차)

작성 2026-09-27 · lane-3 · 트리 `.claude/worktrees/t460-ui` @ `5beb2a73`

## 실측으로 드러난 전제 (읽은 코드 기준)

| # | 사실 | 근거 |
|---|------|------|
| F1 | REQ-083(PLAN CUE 카드 하단 3줄 + `Q###` 배지)은 **아직 없다** | `ui/src/components/SongTimeline.tsx:119-168` `TimelineSectionCard` 에 `Fade/Track`·`MIB/남김`·헤드룸 줄 없음(grep 0) |
| F2 | 생성기 UI 는 전혀 없다 | `ui/src` 에서 생성기·변경 스택·선택 취소 grep 0 |
| F3 | 파서가 읽는 어휘: 조도(절대·상대), 페이드(절대·상대), 전환(SNAP/XFADE/FADE), 무드, 무브먼트, 이펙트, 컬러(주), 노트, 그룹 스코프. **트래킹·MIB·페이저·프리셋 번호는 없다** | `server/design/cue_sheet_edit.py:205-283` |
| F4 | 한 문장 = 한 큐. 그룹 스코프는 문장 전체에 걸리고, 큐 전체 값(페이드·무브먼트)과 섞이면 거절 | 같은 파일 `_resolve_group_scope` 420-, t461 시험 |
| F5 | 서버 응답은 `chat_response` 평문 하나. 수락은 `song_timeline_event` 의 `draft.depth` 증가로만 보인다 | `server/web/session.py:9369-9412`, `ui/src/protocol.ts:1109` |
| F6 | `PresetPoolPopup` 은 읽기 전용이다. 선택 콜백 없음 | `ui/src/components/PresetPoolPopup.tsx:143-147` |
| F7 | `concept_report.reserve`·`rows[].unused_groups` 는 서버에 있으나 UI 타입에 없다 | `server/concept/session_bridge.py:182,258` vs `ui/src/protocol.ts:446-476` |
| F8 | 팬 폭·페이저 속도는 UI 로 오는 데이터 어디에도 없다 | `protocol.ts` grep 0 |
| F9 | 대상 화면은 런북 모드. `RunbookMode.tsx:228-246` 이 ConceptPanel·CueSheetTimeline·SongTimeline·GateBar 를 이미 그린다(M7 1~6 착지) | 코드 |

## 설계 결정 — 감독 승인 2026-09-27 (범위: 파서가 아는 것만 · 전송: 줄마다 한 문장)

- **D1 전송 단위 — diff 줄 하나 = 문장 하나, 순차 전송.** F4 때문에 한 문장에 섞으면 서버가 통째로 거절한다. 줄마다 보내면 거절 사유가 그 줄에 그대로 붙는다(REQ-091·092). 한 번에 한 요청만 날고, 응답(`chat_response`) 도착 뒤 다음 줄을 보낸다. 자유 입력 한 줄은 **마지막 문장 끝**에 덧붙인다(REQ-101).
- **D2 어휘 범위 — 파서가 읽는 것만 조작으로 낸다.** 조도(그룹별), 컬러(그룹 하나), 페이드, 전환, 무브먼트·이펙트(프리셋 이름을 값으로). 트래킹·MIB·페이저는 조작 위젯을 **만들지 않고** 서버 어휘 확장 카드를 따로 만든다(F3). 이유: 파서가 모르는 문장은 `None` → 편집 라우트를 안 타고 일반 대화로 흘러, 「반영 요청」이 아무 일도 안 한 채 끝난다.
- **D3 파생 경고 — 데이터가 있는 넷만.** (1) 후렴 밝기 역전, (3) 리저브 위반(`reserve` 소비), (4) 잔여 그룹 < 4(`unused_groups` 소비), (5) MIB live. (2) 팬 폭·(6) 페이저=BPM 은 F8 로 계산 불가 → 서버 필드 노출 카드로 넘긴다. 재사용 셋은 서버 값을 그대로 읽고 재계산하지 않는다(AC-040).
- **D4 프리셋 팝업 — `onSelect?` 선택 prop 하나 추가.** 없으면 지금과 바이트 동일(읽기 전용). 재구현 금지(REQ-089) 준수.
- **D5 3상태 — 선택(로컬) / 요청(전송·응답 대기) / 초안 반영(`draft.depth` 증가 확인).** 「선택 취소」·항목 `✕` 는 로컬 상태만 지우고 서버에 아무것도 안 보낸다(AC-042·052). 되돌리기 깊이는 서버 값만 쓴다.

## 구현 순서 (파일 단위)

1. `ui/src/protocol.ts` — `reserve`·`unused_groups` 타입 추가(추가만).
2. `ui/src/components/SongTimeline.tsx` — REQ-083 하단 3줄 + `Q###` 배지.
3. `ui/src/components/cueRequestSentence.ts`(신규) — 선택 → 문장 조립 순수 함수. 파서 어휘만 쓴다.
4. `ui/src/components/cueRequestWarnings.ts`(신규) — 경고 4종 순수 함수.
5. `ui/src/components/PresetPoolPopup.tsx` — `onSelect?`.
6. `ui/src/components/PlanCueRequestGenerator.tsx`(신규) — 그룹 칩 다중 선택·혼합 표시·BLIND 잠금·값 패널·변경 스택·선택 취소·`✕`·자유 입력·반영 요청.
7. `SongTimeline.tsx`/`RunbookMode.tsx`/`App.tsx` — 카드 하단 마운트, 전송은 기존 `sendChat` 한 길(REQ-094, 대화 기록 동일 경로).
8. 시험 — vitest 컴포넌트·순수 함수 + **pytest 어휘 일치 시험**(AC-039: `cueRequestSentence` 가 만드는 대표 문장 5종을 픽스처로 떠서 `parse_cue_sheet_edit_request` 로 통과시켜 기대 `changes` 대조).

## AC 대응

034(마운트) · 035(혼합) · 036(프리셋 이름) · 037(BLIND 잠금) · 038(상태 라벨·줄별 경고) · 039(어휘 일치 pytest) · 040(경고 4종, 2종 n/a+카드) · 041(sendChat 한 길) · 042(선택 취소 무전송) · 043(「되돌리기」 라벨 1개) · 044(수락 뒤 스택 비움·depth+1) · 052(`✕`) · 053(자유 입력 끝 덧붙임)

## 범위 밖 → 카드로

- **t466** 서버 어휘 확장: 트래킹·MIB·페이저·프리셋 번호 문장 (REQ-089 포지션/페이저 행, AC-039 트래킹 1건)
- **t467** 서버 필드 노출: 팬 폭·페이저 속도 (REQ-093 (2)(6))
