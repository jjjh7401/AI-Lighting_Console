# SPEC-COPILOT-CUETIME-001 — 수용 기준

## T1 (M1)

- [ ] `position_cue_store_commands` 유닛: 문법 정합(`Store Sequence S Cue C
  'name' CueFade F`), fade 생략, 소수점 큐 번호, 경계 거절(음수/무한/따옴표
  라벨) — pytest green.
- [ ] 세션: "프리셋 N을 시퀀스 S 큐 C로 저장 페이드 F초" → 번들
  [`Fixture <sel> ; At Preset 2.N`, Store, `ClearAll`] 단일 dispatch;
  시퀀스 미지정 → 카드 1장; 무응답 → no-op 거절 — pytest green.
- [ ] ruff clean (변경 파일).
- [ ] 라이브: 큐 저장 ok → `Go+` 재생 중 프레임 diff ≠ 0 (이동 관측),
  responder prop `CueFade` == 지정값.

## T2 (M2)

- [ ] 디머 0 큐 뒤 포지션 변경 큐에 선행 큐(k.5, 디머 0+포지션) 자동 삽입.
- [ ] 라이브: 선행 큐에서 빔 비가시, 본 큐에서 무이동 페이드 인.

## T3 (M3)

- [ ] 구간 무드 입력 → 프리셋 참조 큐 시트 초안 (모든 Store가 `At Preset
  2.<n>` 리콜 상태), MIB 규칙 반영.
- [ ] 라이브 시퀀스 재생 검증.

## 공통

- [ ] 새 함정 발견 시 `.claude/skills/ma3-spatial-pointing/SKILL.md` 기록.
- [ ] 커밋·푸시 (feature/position-cue-timeline).
