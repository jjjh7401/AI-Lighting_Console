# 2026-08-19 세션 핸드오프 — 페이저 체계 완성 + 저장소 단일화, 다음: 관측 2건·research 판정

applied lessons: reland-over-merge · nc-flag-confirm-bypass · preserve-gate-format-trap ·
composite-sentence-dispatch-order · label-slot-runtime-lookup · truncated-listing-never-decides

## 1. 이 세션이 끝낸 것 (전부 main 머지·라이브 검증)

| 축 | 내용 | PR |
|---|---|---|
| 페이저 프리셋 3가족 | 멀티컬러(Color 4.31~40)·디머 레벨+페이저(Dimmer 1.11~30)·콤보(All 1 21.21~30) — M0 프로브(08/09/10번 노트) 실측 문법만 사용, 실기 저장·되읽기 검증. **총 7가족 70종** 완성 | #43, #45 상당 |
| UI 정합 | 풀 팝업 24캡 → offset 페이징 완전 판독, 대시보드 배지 childCount 정합, 분할 원 스와치(풀 이름 스코핑 — 발명 금지) | #43 |
| 다관점 리뷰 1회전 | 합성 문장 오라우팅 2건("컬러 디머 페이저"→디머에 삼켜짐 등, 디스패치 구체축 우선으로 수정)·스와치 풀 스코핑·bool-as-int·pool_no 가드 + rig_object int 강제·리졸버/판별 몸통 통합 | #45~#46 상당 |
| recall 3단계 | ①즉시 발사("Drop Slam 쳐줘"/"빼줘") ②시퀀스+Exec("Wave CM 시퀀스 N으로") ③곡 큐 통합(섹션 어휘→페이저 자동 제안, 리뷰 시트 표시, `extra_value_lines`로 recall 삽입). 라벨→슬롯은 **런타임 되읽기**(코드 상수 금지). 11번 프로브 | #48 이전, 커밋 0feec90 |
| introspect 재이식 | spec/introspect-001(behind 308, PR #23)을 머지 대신 **재이식** — 응답기 **1.6.1**(props 일괄판독+introspect 자기진단+AC-004), 실기 배포·재검증(12번 노트). PR #23 close(후계 #48 명기), 원본은 원격 아카이브 | #48 |
| ASSUMPTION 공략 | introspect로 기계 재공략(13번 노트) 후 **사용자 육안 확인**: A1(멀티스텝 실증)·A2 적재(recall이 페이저를 싣는다) **종결**. 회신 문구 축소 반영 | #49, #51 |
| 저장소 단일화 | 워크트리 6→4, main 단일 기준(orca/…/MAcopilotpos). 원본 체크아웃의 미커밋 1,460줄 보존(819aa6f)+main 정렬(behind 44→6). 포트 전쟁 근원(Documents 구코드 데몬) 제거. 지도+유지규칙 R1~R6: `docs/worktree-map.html` | #50 |

**main @ 4a18c0b · 전체 스위트 9251 passed · vitest 458 · 미푸시 0.**

## 2. 다음 세션 과제 (우선순위순)

1. **관측 2건 회수** (사용자가 onPC에서 실행, 결과만 받아 반영):
   - "Chase RB 쳐줘" → 하드컷이면 A3(Rectangle 근사) 종결 / 섞이면 Transition 수치 재탐색 필요
   - 곡 설계 시퀀스를 Exec 재생 → 페이저 섹션에서 색이 움직이면 마지막 ASSUMPTION(큐 참조 보존) 종결
   - 반영 방법은 PR #51 커밋(4a18c0b 직전) 패턴 그대로: 문구 축소 + 13번 노트 확인 기록.
2. **research/ma3-effects-phaser 판정**: main 미합류 +2,153줄(응답기 WIP·QuestionCard·vwx·prechk). 완성/폐기 판정 → Lua를 main 정본 1.6.1 기준으로 정리 → PR. 주의: research의 props 짜깁기는 1.6.0 기반이라 **재이식된 1.6.1이 정본**.
3. **재료 확장**: 스트로브(드롭 연출 최대 공백, Shutter 속성 M0 프로브 필요)·Beam 줌(판별 프로브 필요). 기존 파이프라인(M0→구현→라이브) 그대로.
4. **F1 후속**: 페이저 라벨 오타 시 라우터 거부→LLM 폴스루로 의도치 않은 프리셋 저장(T13 실측, 22.1 사건). 좁은 가드 설계 필요 — 정당한 LLM 요청을 삼키지 않는 조건이 관건.
5. **deploy_plugin 표준화 SPEC**: 응답기 자기삭제 함정(12번 노트 §1) — `/nc`+임시 중복본 4단계를 배포 도구의 표준 경로로. 현재는 수동 우회.
6. blocked16 미커밋 2건 — R4(WIP 보존 커밋) 적용 대상. 콘솔 잔재(시퀀스 209 'Wave CM'·250 등, 구 플러그인, Macro 99)는 onPC 수동 삭제 권장.

## 3. 전제 검증 (다음 세션 첫 커맨드)

1. `git log --oneline -1` → 4a18c0b 이후, 브랜치 main (orca/…/MAcopilotpos 워크트리)
2. `uv run pytest server/tests -q` → 9251 passed 기준
3. 응답기 **1.6.1** (`responder_roundtrip --expect-version 1.6.1`)
4. 콘솔 프리셋 70종: Color 37·Dimmer 27·Position 31·All 1 26 (`/api/presets/{4,1,2,21}` total)
5. 앱: hub 감독 `copilot-web`(restart=on-failure, persist)이 8765/9005 보유 — `curl /healthz`

## 4. 환경·규율 (이 세션에서 확립)

- **유지 규칙 R1~R6**: `docs/worktree-map.html` §3. 요지: main은 PR로만 / 머지된 브랜치 즉시 삭제 / behind 30 상한 / 미커밋으로 밤 넘기지 않기 / 오래 멈춘 브랜치는 재이식 / 앱·포트는 main 워크트리 하나만.
- **포트 전쟁 종결**: Documents 데몬(broker) 제거됨. 프로브로 9005가 필요하면 `/tmp/probe_window.sh <명령>`(자동 kill→실행→재선점). 베이비시터 불필요.
- **콘솔 확인창 우회**: 삭제·Import가 'User Canceled Command'로 거부되면 `/nc` 플래그 (실측: Delete Sequence·Delete Preset·Import Plugin 전부 유효).
- **절단 함정**: 시퀀스/풀 목록의 첫 창은 바이트 캡으로 24개보다 일찍 잘릴 수 있다 — **절단된 목록으로 빈 번호를 판단하지 말 것**(이 세션 실수 1회). 슬롯별 점유 검사(`_console_slot_occupied`)가 정답.
- **보존 게이트 함정**: 광역 `ruff format`이 보존 경로(preview.py 등)를 건드리면 게이트가 잡는다 — 포맷은 변경 파일만 지정.
- 트립와이어 재실측 이력: songcue 헝크핀 68개(재이식 후), lua/PROTOCOL.md 다이제스트는 1.6.1 기준 재핀.
