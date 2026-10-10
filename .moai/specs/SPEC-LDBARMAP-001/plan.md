# SPEC-LDBARMAP-001 — 구현 계획

## §A. 개요 (Context)

LOVE ATTACK 한 곡을 대상으로, 오프라인 분석으로 비트·다운비트·마디 경계·마디별 변화 이벤트(킥 진입·빌드업·드롭·브레이크)를 검출하는 기능을 설계한다. 이 plan-phase는 문서 5개(spec.md·plan.md·acceptance.md·research.md·progress.md)만 산출하며, `server/` 아래 코드는 한 줄도 바꾸지 않는다. 착수(M1) 승인은 이 plan-phase가 끝난 뒤 별도로 받는다.

- 작업 위치: 메인 체크아웃(워크트리 `.claude/worktrees/t527`, 브랜치 `WT-barmap-plan`, 베이스 `origin/main` `88ecfb9d`).
- 선행 SPEC: `SPEC-LDBEAT-001`(런북 모드 박자 배치, draft) — 이 SPEC의 산출물(마디 지도)은 그 SPEC의 박자 격자가 소비할 수 있는 입력 후보다. 두 SPEC은 서로 독립적으로 진행 가능하다(LDBEAT M1~M2는 LOVE ATTACK 손 배치를 입력으로 쓰고, 이 SPEC의 산출물을 기다리지 않는다).
- 후속 SPEC: `SPEC-LDARRANGE-001`(역할×마디 자동 배치, 아직 존재하지 않음) — 이 SPEC의 마디 지도를 소비할 장래 SPEC.

## §B. 열린 결정 — 저장 인터페이스 (먼저 제시)

`spec.md` §5 열린 결정 0을 그대로 가져온다 — 이것이 이 plan의 가장 바뀔 가능성이 높은 결정이므로 마일스톤 목록보다 먼저 적는다.

| 옵션 | 내용 | 장점 | 단점 |
|---|---|---|---|
| A — 임베드 | `timeline` 사전의 새 키(예: `beat_grid` 또는 `bar_map`)로 기존 `SongTimelineStore`/`TimelineDraftHistory`/`SongTimelineLibrary`에 얹는다 | 되돌리기·버전 관리를 코드 추가 없이 재사용(`SPEC-LDBEAT-001` REQ-LDBEAT-006 선례) | 82마디 × 여러 필드가 박자 격자보다 무거워 `TimelineDraftHistory`의 "전체 사전 깊은 사본" 비용이 커질 수 있음 |
| B — 독립 저장소 | 마디 지도 전용 신규 저장 모듈 | 생명주기(곡당 1개, 재분석 시 덮어쓰기)가 편집 이력과 분리되어 더 정직 | 신규 코드, LDBEAT·LDARRANGE와 별도 배선 필요 |

**결정 시점**: M2+ 착수 시 감독과 함께. 이 plan-phase는 선택하지 않는다(REQ-LDBARMAP-010).

## §C. 마일스톤 (우선순위 기반, 시간 추정 없음)

마일스톤은 바뀔 가능성이 가장 큰 결정(어떤 검출기를 채택할지, 어떤 지표로 성공을 가를지)을 먼저 배치하고, 기계적 단계(테스트 추가, 문서 교차참조)는 뒤로 미룬다.

### M1 — 계기 보정 (우선순위 High)

후보 검출기(예: `librosa.beat.beat_track`의 변형, 온셋 기반 다운비트 추정, 자기상관 기반 마디 길이 추정 등 2개 이상)를 LOVE ATTACK에 실행하고, 지도 보고서(`reports/loveattack-music-map-20261006.md`) 대비 REQ-LDBARMAP-004의 네 지표로 채점한다. 음성 대조군(REQ-LDBARMAP-005 — 날조/이동 격자)을 반드시 포함한다. 코드 diff 0줄 — 측정·채점 스크립트만 작성하고 `.moai/reports/SPEC-LDBARMAP-001-probes/`에 둔다.

- 산출물: 후보별 채점표(BPM 오차율·다운비트 적중률·마디 경계 적중률·마디별 이벤트 재현율), 음성 대조군 결과, 감독 검토용 판정서.
- 통과 조건: acceptance.md AC-LDBARMAP-001~006 전부 PASS인 후보가 최소 1개 존재(plan-audit iteration 2 D-NEW-1 교정 — AC-003 신설로 밀린 번호 재반영. 이 범위는 M1 완전성(001)·음성 대조군 1·2(002/003)·BPM 배수 함정(004)·다운비트 적중률(005)·마디 경계 적중률(006)을 모두 포함한다 — M1 자신이 "REQ-LDBARMAP-004의 네 지표로 채점한다"고 적은 대로, 마디 경계 적중률도 빠짐없이 들어간다).
- `lesson-calibrate-the-instrument-against-ground-truth-first.md`(이 저장소 메모리) — "판별기 넷 다 실패, 1번은 정답의 반대. 원인 하나" — 이 교훈을 그대로 적용: 채점 전 채택하지 않는다.
- **M1 결과(카드 t530, 2026-10-10) — 통과 조건 미충족, 그대로 기록한다.** 후보 검출기 3개(A/B/C) 모두 AC-LDBARMAP-005/006(자체 위상 선택 기준 다운비트·마디 경계 적중률)에서 FAIL했다(0/82, 0.0% — 위상 1을 강제하면 A 100%·B 97.6%로 박 격자·BPM 자체는 맞다, `.moai/reports/SPEC-LDBARMAP-001-probes/m1-calibration.md`). **M2는 이 통과 조건이 충족되어서가 아니라, 리드 경유 감독 결정("귀 확인 + 수동 지정 병행", `progress.md` §E.2 "M1 판정 후 감독 결정")에 따라 범위를 줄여 진행한다** — 아래 M2 기술 참조. AC-LDBARMAP-005/006 자체는 보류 상태(자동 위상 선택 능력의 회귀 추적용)로 acceptance.md에 그대로 남아 있다.

### M2 — 다운비트·마디 경계 검출기 확정 (우선순위 High, 범위 축소 — 카드 t530)

**범위 축소(2026-10-10 감독 결정, 「귀 확인 + 수동 지정 병행」)**: M1이 자동 위상 선택에서 세 후보 모두 FAIL했으므로, M2는 자동 위상 선택기를 채택하지 않는다. 대신: (a) 비트 격자(`beat_times`)는 그대로 자동 검출기가 만들고, (b) 마디의 첫 박(다운비트 위상)은 감독이 귀로 들어 1회 지정하는 **첫 박 오프셋**(REQ-LDBARMAP-016 — 정수, `beat_times` 인덱스 mod 4, 범위 0~3) 값 하나로 받는다. M2 신규 모듈(`server/audio/bar_map.py` 가칭)은 "자동 비트 격자 + 사람이 지정한 오프셋"으로 다운비트·마디 경계를 파생한다 — 자동 위상 선택 로직 자체는 M2 범위에서 보류한다.

- 산출물: 신규 모듈(자동 비트 격자 검출 + 오프셋 입력을 받아 다운비트/마디 경계를 파생하는 함수) + 테스트(82마디 LOVE ATTACK 기준 회귀 테스트, **AC-LDBARMAP-016**의 오프셋 기반 수치를 assertion으로 고정 — AC-LDBARMAP-005/006은 보류 상태로 테스트에 남기되 PASS를 요구하지 않는다, plan-audit iteration 2 D-NEW-1 교정 이력은 그대로 유지).
- 통과 조건: 신규 모듈이 사람이 지정한 오프셋을 받아 LOVE ATTACK에서 AC-LDBARMAP-016 수치(다운비트·마디 경계 적중률 각 90% 이상)를 재현.
- 저장: M2 산출물은 여전히 메모리/테스트 픽스처 범위에만 둔다 — 저장 인터페이스 배선은 M4(§B 열린 결정 확정 뒤)의 몫이며 이 범위 축소로 바뀌지 않는다(REQ-LDBARMAP-010).

### M3 — 마디별 변화 이벤트 분류기 (우선순위 Medium)

REQ-LDBARMAP-008의 네 종류(킥 진입·빌드업·드롭·브레이크)를 분류하는 로직을 M2 모듈 위에 얹는다. (범위 축소 반영, 카드 t530: M3의 마디 인덱싱은 M2가 "자동 비트 격자 + 사람이 지정한 첫 박 오프셋"으로 파생한 다운비트·마디 경계를 그대로 쓴다 — M3 자신이 별도의 위상 판단을 하지 않는다.)

- 산출물: 이벤트 분류 함수 + 테스트(지도 보고서 §2.1/§2.3의 라벨 대비 재현율 AC-LDBARMAP-007 — plan-audit iteration 2 D-NEW-1 교정: AC-003 삽입으로 밀린 번호를 반영, AC-006은 마디 경계 적중률이지 이벤트 재현율이 아니다).
- 통과 조건: AC-LDBARMAP-007 PASS.

### M4 — 저장 인터페이스 배선 (우선순위 Medium, §B 결정 선행 필요)

§B의 열린 결정이 M2+ 착수 시 확정되면, 그 결정대로 마디 지도를 저장 경로에 배선한다.

- 선행 조건: §B 결정 확정(감독).
- 산출물: 저장 배선 코드 + 왕복(쓰기→읽기) 테스트.

### M5 — LDRHYTHM 교차참조 (우선순위 Low, sync-phase)

`SPEC-LDRHYTHM-001` REQ-LDRHYTHM-012(a)에 "이 SPEC이 그 후보를 실제로 다뤘다"는 교차참조 한 줄을 추가한다 — LDRHYTHM 쪽 파일 수정이므로 별도 SPEC 소유권 경계를 존중해 sync-phase에 manager-spec 재위임으로 처리한다(REQ-LDBARMAP-012 — 승계 의무, REQ-LDBARMAP-013 — 이 plan-phase가 LDRHYTHM 파일을 직접 고치지 않는다는 경계. plan-audit iteration 1 D2가 이 둘을 하나의 이중 모달 REQ에서 분리했다).

- 산출물: `SPEC-LDRHYTHM-001/spec.md` HISTORY에 한 줄 추가(이 SPEC이 직접 쓰지 않음 — 재위임 기록만 이 plan에 남긴다).

## §D. 기술적 접근

- M1은 순수 측정/채점 — `server/audio/analyze.py`의 기존 함수(`analyze()`, `_tempo_from_beats`)를 **읽기만** 하고 호출해 `beat_times`를 꺼낸다(현재 `analyze()`는 `beat_times`를 반환하지 않으므로, M1 스크립트는 `analyze.py`를 import해 내부 함수를 직접 호출하거나, `librosa.beat.beat_track`을 독립적으로 재호출한다 — 어느 쪽이든 `server/` 파일은 수정하지 않는다).
- 채점 스크립트는 지도 보고서의 부록 A(82마디 표, 다운비트 시각·마디별 이벤트 라벨)를 정답 테이블로 파싱한다.
- 음성 대조군은 정답 테이블을 프로그램적으로 변형(전체를 N ms 또는 1박 밀기)해 만든다 — 손으로 날조하지 않는다(재현 가능성).
- M2의 신규 모듈은 `AnalysisResult`를 확장하지 않는다 — REQ-LDBARMAP-010이 저장 형태를 정하지 않으므로, M2 자체는 별도 함수(`detect_bar_map(audio_bytes) -> BarMapResult | BarMapFailure` 가칭)로 분리해 기존 `analyze()` 계약을 건드리지 않는다. 기존 `AnalysisResult`/`AnalysisFailure`의 "예외를 밖으로 내보내지 않는다"(`analyze.py:297` 원칙)를 신규 모듈도 따른다.

## §E. 위험

| 위험 | 완화 |
|---|---|
| BPM 배수 오류(절반/두 배)가 다운비트·마디 경계 지표까지 오염 | REQ-LDBARMAP-006 — 격자 정합도 비교를 BPM 채택 전 필수 단계로 둔다 |
| 채점기 자체가 공허(무엇을 넣어도 통과) | REQ-LDBARMAP-005 — 음성 대조군을 M1 통과 조건에 포함 |
| 지도 보고서의 "추정" 라벨(구간 이름·드롭 위치)을 정답으로 과신 | REQ-LDBARMAP-009 — 신뢰도 갈래를 이어받아 "추정" 항목은 미달 판정의 유일한 근거로 쓰지 않음 |
| 저장 인터페이스를 이 plan-phase가 섣불리 확정 | REQ-LDBARMAP-010 — 열린 결정으로 명시 보존, M2+에서 확정 |
| 다른 박자(3/4 등)·다른 곡으로 일반화할 때 LOVE ATTACK 전용 상수(60ms 허용오차 등)가 깨짐 | REQ-LDBARMAP-004 각주 — 이 SPEC은 LOVE ATTACK 한 곡만 보정하고, 일반화는 범위 밖(§5 열린 결정 3) |

## §F. 제약 (PRESERVE 목록)

- `server/audio/analyze.py` — M1~M3는 **읽기만** 한다. 수정은 착수 승인 뒤 M2부터.
- `SPEC-LDRHYTHM-001/spec.md`·`plan.md`·`acceptance.md`·`progress.md` — 이 plan-phase가 수정하지 않는다(교차참조는 M5, 별도 재위임).
- `SPEC-LDBEAT-001/spec.md`·`plan.md`·`acceptance.md`·`progress.md` — 이 plan-phase가 수정하지 않는다(인용만).
- LOVE ATTACK 원곡 오디오(`/Users/studiox/Music/AI-Lighting_Console-listen/`) — 저장소에 커밋하지 않는다.

## §G. 교차참조

- `reports/ldbeat-feasibility-roadmap-20261010.md` §3 항목 1, §5 ②
- `.moai/specs/SPEC-LDRHYTHM-001/spec.md` REQ-LDRHYTHM-012(a)
- `.moai/specs/SPEC-LDBEAT-001/spec.md` REQ-LDBEAT-006
- `reports/loveattack-music-map-20261006.md`(정답지)
