# MA3 코파일럿 — 감독 타임라인 워크플로우 완성 (2026-08-15)

브랜치 `research/ma3-effects-phaser`. 핸드오프(2026-08-15) 합의 우선순위 1~6 전부 구현·검증·커밋.

## 완료 항목

| # | 기능 | 커밋 | 요지 |
|---|---|---|---|
| 1 | PLAN 편집 + 큐 추가/삭제 | `1feefd3` | 승인 거절 시 `_pending_song_plan` 보존, "큐 N 삭제/추가/포지션·컬러" 콘솔 무접촉 편집 → 재합성 → 재승인. 오버라이드 인덱스 재매핑 |
| 2 | 편집 어휘 확장 | `a98b969` | 디머(D1~5·어둡게/밝게), 페이드(초), FX on/off, 시간 이동(m:ss, 이웃 교차 시 재정렬). `SectionDecision.fade_override`, payload `fade_seconds` |
| 3 | 자동 버전 스냅샷 | `ec1897e` | 승인 실행 후(verified·readback_failed 모두) 라이브러리에 `이름 (자동 vN)` 자동 저장. N=기존 스탬프 max+1 |
| 4 | 셋리스트 모드 | `29d78c9` | 라이브러리 최신 버전/곡 → `Copy Sequence src At 210+10i` + `Assign … At Executor 101+i`. 슬롯 빈자리 사전점검, 승인 1회, Executor readback(node.sequenceNo) |
| 5 | 리허설 편집 | `4989b07` | "지금/현재 큐를 <포지션>으로" — 시퀀스 핸들 CurrentCue(T-H3 실측)로 재생 큐 판별, 매회 승인 필수, /Merge 공용 헬퍼 `_merge_timeline_cue_position` |
| 6 | 레이어 매핑 실사용 | `77024fd` | 확인된 back 그룹 → 점등 섹션 큐마다 `Group N ; Dimmer At key×0.8` (전체 키 디머 뒤, Store 앞). RG5 준수(그룹 번호 주소만) |
| - | 정리 | `5b66751`, `b0b5c88` | 기존 포맷 드리프트 정리, 동시 세션 `bcc174a`의 CSS 누락분 완성 |

## 검증
- 전체 서버 테스트 8,753 passed / 0 failed (신규 31건)
- UI 449 passed, `ui/dist` 재빌드·서빙 반영
- 백엔드 `grandma3-web-stable` 재기동·ready (`http://127.0.0.1:8765/`)
- 안전 불변식: 미승인 콘솔 쓰기 0건 — 기능별 "거절 시 무기록" 테스트로 고정

## 실기 확인 필요 (다음 리허설)
1. `Copy Sequence A At B` — 저장소 첫 사용 (빈 슬롯 대상, readback이 실패 감지)
2. Back 그룹 디머 last-wins 순서 실기 재현 확인

## 동시 작업
다른 세션 커밋 `51df4d4`(UI), `c3be934`(perf: audit tail-read, snapshot cache), `bcc174a`(진행 순서 보드)와 병행 — 내 `app.py` 주입 라인은 `c3be934`에 실림. 충돌 없음.
