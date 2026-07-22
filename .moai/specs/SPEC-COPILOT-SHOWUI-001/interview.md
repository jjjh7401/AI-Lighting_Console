# Interview: 조명 연출 컨트롤 패널 UI (SPEC-COPILOT-SHOWUI-001)

## Interview Round 1: Scope
Question: '조명 연출을 위한 UI/인터페이스'의 핵심 형태는 무엇인가요?
Answer: 연출 컨트롤 패널 — 채팅과 나란히 붙는 시각적 연출 패널. AI가 만든 룩/이펙트/시퀀스를 버튼·페이더·컬러칩으로 즉시 실행/조절. 기존 소켓·승인 흐름 재사용.

Question: UI와 콘솔(onPC) 사이의 데이터 흐름은 어떻게 할까요?
Answer: 기존 파이프라인 재사용 — 현재의 WebSocket + OSC 응답기 + get_rig_context 경로를 그대로 사용, UI는 서버 API만 호출. 새 콘솔측 Lua 추가 최소화.

## Interview Round 2: Constraints / Success Criteria
Question: 컨트롤 패널에 올라가는 항목(룩/이펙트/시퀀스 버튼)은 어떻게 만들어질까요?
Answer: AI 생성 + 수동 고정 하이브리드 — 채팅에서 AI가 연출을 만들면 '패널에 추가' 버튼으로 고정하고, 콘솔의 기존 시퀀스/프리셋도 get_rig_context로 읽어 자동 나열.

Question: 이 SPEC이 '끝났다'고 판단하는 기준은 무엇인가요?
Answer: 라이브 E2E + 테스트 그린 — 실제 onPC에서 패널 버튼 → 연출 실행/정지 라이브 검증 + pytest/vitest 전체 그린.

## Clarity Score
Initial: 4/10
Final: 8/10
Rounds completed: 2
