# 세션 핸드오프 — 2026-08-14 (spatial-pointing 마감 → position-cue-timeline 착수)

이전 세션(공간 포인팅·포지션 프리셋·무드 제안)은 **main에 머지 완료**. 이 문서는
다음 세션이 새 브랜치에서 바로 착수하도록 남기는 인수인계다. 상세 기술 기록은
`handoff/2026-08-13-spatial-pointing-handoff.md`(머지됨)를 먼저 읽어라.

## 1. 리포지토리 상태

- `main` = `614eab9` (Merge feature/spatial-pointing, 푸시됨). 구 브랜치는
  로컬·원격 모두 삭제.
- **작업 브랜치: `feature/position-cue-timeline`** (main에서 분기, 원격 추적
  설정, 현재 체크아웃 상태, 아직 커밋 없음).
- 워킹트리의 `.moai/*.jsonl` 등 잔여 변경은 이전부터 있던 로컬 런타임 항목 —
  커밋하지 않는 관례 유지 (2026-08-13 핸드오프 §5).
- 서버 테스트 기존 실패 3건(prechk 웹표면 / songcue diff 가드 / tools 레지스트리
  중복)은 이 작업과 무관하게 HEAD에 존재.

## 2. 콘솔·서버 상태 (라이브)

- onPC 2.4.2 `NewShow_2026.08.08` 가동 중. 리그: 무빙 40대 링 배치(원본 좌표
  복원됨) + 원점 마커 Sphere(FID 41).
- 쇼파일 산출물: Position 프리셋 **2.21~2.30**(Home~Ring In), **Sequence 100
  Cue 1 'Rock Fast RGB Chase'**(Preset 2.28 참조 + RGB 페이저) → Executor 103.
  현재 Off + ClearAll 상태.
- 서버: hub 프로세스 `grandma3-web-stable`(포트 8765) online. 포트 9005 경합이
  onPC 때문에 1회 발생할 수 있음 — 재시도로 해소. probe류는 서버 중지 후 사용.

## 3. 다음 세션의 과제 — 시간축 (조명연출 발전 제안 §1·§2)

정지 룩 → 시간 위의 연출. 사용자 승인된 우선순위:

### T1. 포지션 큐 트랜지션 (Fade/Delay)
- 포지션 룩(프리셋 참조)을 큐로 저장할 때 `Store Cue <n> Fade <s>` 지원 —
  검증된 문법(00_grammar.md:69). "빔이 천천히 넘어가는" 전환이 목적.
- 구현 씨앗: `server/spatial/pointing.py`의 `position_preset_store_commands`
  옆에 큐 저장 빌더 추가, 세션 어휘 "…포지션을 큐로 (페이드 N초)".

### T2. MIB(Move In Black) 규칙
- 이전 큐 디머가 0이면 포지션을 다크에서 선이동 — 큐 시퀀스 생성 시
  "포지션 선행 큐(디머 0 + 포지션) → 본 큐(디머 페이드 인)" 패턴 자동 삽입.
- 라이브에서 헤드가 보이며 허우적대는 것을 없애는 업계 표준 규칙.

### T3. 곡 구조 × 포지션 큐 시트
- `server/looks/songcue.py`(`prepare_songcue`: 구간+시각→큐리스트) ×
  `server/spatial/position_moods.py`(무드→포지션) 결합: 구간 무드를 받아
  곡 전체 포지션 큐 초안 생성. 에너지 곡선 원칙(좁→넓, 사람→공간) 반영.
- 큐는 반드시 **프리셋 참조**(`At Preset 2.<n>` 상당)로 빌드 — 공연장 이동 시
  프리셋 재생성만으로 전 큐 추종.

후순위(같은 제안서의 §3~5): 관객 직사 가드(빔 벡터 기하 검증), 포커스 유지
스웨이(±3~5° 상대 페이저), 버스킹 페이지 자동 구성.

## 4. 반드시 기억할 실측 함정 (전부 스킬에 근거 기록됨)

`.claude/skills/ma3-spatial-pointing/SKILL.md` 참조. 요약:
1. Pan/Tilt `At` = 도(°). 픽스처당 `Fixture <fid> ; …` **한 줄 체이닝** 필수
   (동일 텍스트 dedupe가 84/160을 삼킨 실측).
2. 페이저 큐에 `/merge` 재저장 금지 — 페이저 평탄화. 한 프로그래머 상태로
   `/Overwrite`. 구동 검증은 3D 두 프레임 픽셀 diff.
3. 익스큐터 배정: `Assign Sequence n At Executor m` (Page 1.x 형태는 실패 가능).
   페이지 컨테이너 슬롯 ≠ 익스큐터 번호.
4. 프리셋 이름 중복 시 `#2` 자동 접미사(대소문자 무시).
5. 룰북 31의 "percent" 표기는 오류지만 바이트 핀 — 정정은 32_spatial_design.md.
6. Store 뒤 ClearAll, 프리셋 번호는 사용자 명시 없이 추측 금지, 부분 좌표
   읽기로는 조준 시작 금지 — 기존 패턴 유지.

## 5. 검증 루틴 (이 프로젝트의 표준 사이클)

구현 → `uv run pytest`(스코프 스위트) + ruff → 서버 재시작 → WS 라이브
(질문 카드·승인 자동 응답 스크립트 패턴은 이전 세션 트랜스크립트/핸드오프 참조)
→ 3D 스크린샷(`screencapture -l <windowid>`, 창 id는 재조회) → 픽셀 diff나
좌표 readback으로 정량 확인 → 오류 시 수정·재검증 반복 → 스킬에 함정 기록 →
커밋·푸시.
