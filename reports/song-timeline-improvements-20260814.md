# MA3 코파일럿 — 곡 조명 연출 / 감독 타임라인 개선 리포트 (2026-08-14)

## 완료된 개선 (핸드오프 결함 1~5 대응)

### 1단계 — 미해결 구간 재질의 및 재합성 (결함 2)
- `server/web/session.py`: 첫 질문 하나만 묻고 종료하던 흐름을 제거. 모든 `requery_requirements`에 대해 카드 표시(포지션 선택지 4종 + 자유 입력).
- 포지션 이름이 포함된 답변 → 해당 구간의 완전한 `DirectorOverride`(D/색은 구간 아크에서 보충)로 병합. 포지션이 없으면 답변을 그 구간의 새 무드로 병합.
- 병합 후 **동일한 계획**을 `_build_unified_song_plan` → `compose_song_cue_bundle`로 전 구간 재합성, 타임라인 이벤트 재전송 (최대 3라운드).
- 미해결이 남아있는 동안 `run_commands` 도달 불가. 종료 메시지에 남은 재질의 **전체 목록** 표기.

### 2단계 — 계획 Cue / 저장 Cue / 검증 Cue 상태 분리 (결함 1)
- 서버 payload: 각 섹션에 `plan_status: draft | requires_requery | approved | stored | verified`, 타임라인에 `console_stored: bool`, `warnings: string[]` 추가.
- UI(`SongTimeline.tsx`): PLAN CUE(점선 카드, "설계 초안/재질의 필요 · 콘솔 미저장") vs CUE("콘솔 저장 확인") 구분. LIVE 배지는 stored/verified + 시퀀스 번호 일치 Executor일 때만. `console_stored=false`면 헤더에 "계획 단계 — 콘솔에 저장된 큐가 없습니다."

### 3단계 — Section별 Look Arc (결함 3)
- `_section_texture_decision` / `_section_fx_decision` 구간별 결정으로 전환. 역할 분류(도입/벌스/후렴/브리지/피날레)로 Texture·FX·Palette·D-Level 차등.
- Q5 질감의 FX 밀도는 상한(ceiling)으로 유지 — 감독이 정적을 원하면 아크가 FX를 되살리지 않음.
- 불변식 강제: 피날레 D ≥ 후렴 D(사후 보정), 브리지 FX ≤ 후렴, 도입 FX 없음, 전 구간 동일 Palette/Texture/FX 시 경고.

### 결함 4 — 구간 자연어 의도 우선
- `_direct_position_intent`: 보컬→Vocal DSC, 관객/객석→Audience, 넓혀/퍼지→Fan Out, 비워/고립→Wall. Q4 전곡 공간 스토리보다 우선. 재질의 답변은 그보다 더 우선.

### 4단계 / 결함 5 — 색감 충돌 카드
- Q1 컨셉 색 단어 vs Q2 팔레트가 서로소면 충돌 카드([팔레트 중심] [컨셉 색 중심] [구간 분배]).
- 미응답 시 팔레트 유지 + 경고 명시(조용한 덮어쓰기 금지). `구간 분배` 선택 시 후렴/피날레만 컨셉 색.

## 검증 결과
- `pytest server/tests/test_web_session.py` — 96 passed (신규 3: 재질의 병합→5 PLAN CUE pending_approval·쓰기 0회 / 아크 다양성+불변식+포지션 의도 / 팔레트 충돌 카드)
- `pytest server/tests/test_position_cuesheet.py` — 14 passed
- `vitest` SongTimeline+RunbookMode — 22 passed (신규 7), `vite build` 성공
- 백엔드(`grandma3-web-stable`) 재시작 후 127.0.0.1:8765 브라우저 스모크: PLAN CUE 카드·콘솔 미저장·계획 단계 헤더 확인
- CueFade 계약 유지: `Store … CueFade` 사용, `Property 'Fade'` 금지 어서션 통과
- 사전 존재 실패(이번 작업과 무관): 서버 스냅샷/린트류 6건, `PaperworkPanel.test.tsx` 11건(커밋된 테스트↔컴포넌트 drift)

## 다음 단계
1. 결함 6 — Rig Layer 매핑: 콘솔 Group 이름 readback 또는 1회 확인 카드로 Front/Back/Beam/Wash/Audience 매핑 수립. 미확인 시 "단일 레이어 계획" 문구는 유지.
2. 실기 E2E: 새 시퀀스 번호로 승인→저장→readback→Executor LIVE 연동 실측. Sequence 150은 성공 결과로 간주 금지(선 확인·정리).
3. 재질의 UX 고도화: 구간 무드에서 파생한 맞춤 선택지(현재 고정 4종), 미응답 요구 pending 상태 세션 보존.
4. 미확정 인터뷰 답변(Q_n 자동 초안) 재질의를 부분 재인터뷰(`Q_n 다시`)로 라우팅.

## 추가 제안
- 아크 테이블(색/FX/D)을 장르 프로파일별로 분리(발라드/EDM/메탈).
- 재합성 시 타임라인 replace 이벤트에 diff 표시(무엇이 바뀌었는지 감독에게 명시).
- warnings를 lint 규칙으로 승격해 `composition.lint_findings`에 통합.
- 계획 저장 전 `query_state`로 대상 Sequence 선점 여부 확인(기존 큐 덮어쓰기 방지 카드).
