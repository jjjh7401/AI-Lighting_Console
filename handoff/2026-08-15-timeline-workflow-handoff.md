# MA3 코파일럿 — 감독 타임라인 워크플로우 핸드오프 (2026-08-15)

## 실행 환경
- 테스트 주소: `http://127.0.0.1:8765/` (5173 Vite는 사용 안 함 — 백엔드가 `ui/dist` 정적 서빙)
- 백엔드: 감독 프로세스 `grandma3-web-stable` (`.venv/bin/python -m server.web`,
  `restart=on-failure` + persist + ready체크 `@copilot:ready`/포트 8765). `hub restart grandma3-web-stable`로 재시작.
- **코드 변경 후에는 `cd ui && npx vite build` → 백엔드 재시작** (UI는 dist 서빙).
- 파이썬 3.11.15 고정(`.python-version`) — uv의 제자리 업그레이드가 codesign SIGKILL을 일으켰던 사고 방지.
- 브랜치 `research/ma3-effects-phaser`. **모든 작업 커밋됨** (`230a121`~`bc1f335`, 5커밋).
  커밋 후 전체 스위트 8706 passed / 0 failed. UI 426 passed.

## 완성된 워크플로우 (전부 라이브 검증됨)
1. **자연어 곡 브리프** → 감독 인터뷰 라우팅 (`_song_design_interview`, 기술 키워드 불필요)
2. **인터뷰**: 시퀀스/프리셋/타이밍 카드 → Q1~Q5 → 레이어 매핑 카드(콘솔 그룹 이름에서 role 추정, 세션 1회)
   → 색감 충돌 카드(Q1 vs Q2 서로소일 때) → **모든** 미해결 구간 재질의(역할별 맞춤 선택지)
3. **PLAN 타임라인**: 구간별 Look Arc(D/Texture/FX/Palette 차등, 불변식: 피날레≥후렴, 브리지 FX≤후렴, 도입 FX 없음),
   직접 자연어 포지션 의도가 Q4보다 우선. 미응답 재질의는 `_pending_song_requery`로 보존 → 다음 턴
   "벌스는 Center → Fan Out" / "취소"로 재개. 미확정 Q_n은 부분 재인터뷰(restart_from) — 무응답 시 스냅샷 복원.
4. **승인 → 원자 실행 → readback 검증** (`Store Sequence S Cue N 'Name' CueFade f`만 사용; `Property 'Fade'` 금지)
5. **상태 분리**: 섹션별 `plan_status: draft|requires_requery|approved|stored|verified` + `console_stored` +
   `warnings` + `layer_mapping` + `preset_start` (전부 타임라인 payload에). UI: PLAN CUE(점선·콘솔 미저장) vs CUE(저장 확인),
   LIVE 배지는 stored/verified + 시퀀스 번호 일치 Executor만 ("1 — Section 1" 형식 파싱 포함).
6. **영속성**: `SongTimelineStore` — 새 WS 접속마다 replay + 디스크 영속
   (`~/Library/Application Support/GrandMA3 Copilot/song_timeline.json`) → 새로고침·서버 재시작 모두 생존.
7. **타임라인 라이브러리**: `/api/timelines` (GET 목록 / POST 저장 / POST {id}/load / DELETE).
   같은 이름 = 여러 버전. load 시 라이브러리 이름이 song_title로 표시. UI 패널은 런북 페인 상단.
   영속: `song_timeline_library.json`.
8. **타임라인 큐 편집** (`_timeline_cue_edit`): "타임라인 큐3를 무대 중앙으로" → **화면 타임라인의 시퀀스 번호**로
   `Fixture … ; At Preset 2.xx` + `Store Sequence S Cue N /Merge` → projection 즉시 갱신.
   마지막 포지션 단어가 목적지("객석이 아니라 중앙으로"→Center). preset_start 없는 구저장본은 1회 질문.
9. **런북 분할 뷰**: 좌 런북(타임라인+실행 런북) / 우 대화창(카드 포함) — 런북 모드에서 대화 상시 가능.

## 콘솔 현재 상태 (실기 onPC 2.4.2.2, NewShow_2026.08.08)
- Sequence 210 = 검증된 5큐(도입 Vocal DSC D2 / 벌스 Fan Out D3 / 후렴 **Center**(편집됨) D5 / 브리지 Wall D2 / 피날레 Audience D5)
- Executor 101 ← Sequence 210 배정 (원래 Sequence 50이 있었음 — 복원: `Assign Sequence 50 At Executor 101`)
- Sequence 150에 과거 모델 폴백의 오수정 잔재(Group 13 → Center 병합) — 미원복
- 페이지1 다른 실행기들은 데모 중 Off됨 (데이터 무손실, 재Go로 복귀)
- 프리셋 기본 포지션 10종 = 2.21~2.30 (preset_start 21)

## 알려진 이슈
- **responder flapping**: onPC responder가 간헐적으로 degraded↔online 반복 → 가끔 "콘솔 연결이 필요합니다" 차단.
  재시도로 해결되나 근본 원인(콘솔측) 미조사.
- 실기 `get_spatial_context`(41픽스처)가 ~2분 소요 → 인터뷰 첫 카드가 늦게 뜸.
- OSC 피드백 포트 9005 점유 좀비(`python -m server.web` 잔재)가 crash-loop을 만들 수 있음 → `lsof -i:9005`로 확인 후 kill.
- 커밋 제외된 로컬 상태: `.moai/`, `.claude/`, `.playwright-cli/` 등 (의도적).

## 다음 작업 (합의된 우선순위 — 사용자 승인됨)
1. **PLAN 단계 편집 + 큐 추가/삭제** ← 최우선 (워크플로우 ③의 공백).
   승인 전 타임라인을 콘솔 무접촉으로 수정: "큐 3 컬러를 골드로", "큐 2와 3 사이에 브레이크 추가", "큐 4 삭제".
   설계: `_pending_song_requery`의 `_SongDesignState`를 pending_approval 단계에도 보존해 편집 → `_song_compose` 재합성.
   STORED 편집은 diff만 /Merge(현행 큐편집 확장), 라이브 출력 중 큐 경고.
2. 편집 어휘 확장: 디머/D레벨·컬러·페이드·FX on/off·시간 이동.
3. 자동 버전 스냅샷: 승인·저장 성공 시 라이브러리에 `이름 (자동 vN)` 자동 저장.
4. 셋리스트 모드: 라이브러리 곡들에 시퀀스(210,220…)·Executor(101~) 자동 배분.
5. 리허설 편집: 큐 번호 없이 "지금 이 큐"(현재 큐 지칭) 편집, 라이브 중 승인 필수.
6. (미착수) 결함6 후속: 레이어 매핑을 명령 생성에 실제 사용(Front/Back 분리 연출) — 현재는 기록·표시만.

## 안전 규칙 (불변)
- unresolved/번들 없음/승인 전/색충돌 미해결 상태에서 `run_commands` 금지 (전부 테스트로 고정).
- 콘솔 쓰기는 승인 게이트 경유. 타임라인/라이브러리는 읽기 projection — 복원해도 권한 없음.
- 실기 테스트 시 새 시퀀스 번호 사용 또는 기존 상태 확인 후 진행. Cue 3/5는 객석 방향 풀 인텐시티 주의.

## 테스트 명령
```bash
uv run pytest server/tests -q                       # 전체 (2m20s, 8706)
uv run pytest server/tests/test_web_session.py -q    # 세션 플로우 (핵심)
cd ui && npx vitest run && npx vite build             # UI (426)
```
주의: 커밋 후에는 baseline-diff 가드(test_songcue_bundle hunk-pin, test_overlap_preserve,
test_prechk_tool 웹표면 스냅샷)가 재평가됨 — 새 라우트/보존 파일 변경 시 스냅샷 갱신 필요.
`server/web/preview.py`는 보존 대상(byte-exact) — ruff format 금지.
