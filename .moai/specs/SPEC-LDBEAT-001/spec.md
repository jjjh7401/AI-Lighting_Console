---
id: SPEC-LDBEAT-001
title: "런북 모드 박자 배치 — 역할별 트랙 × 마디 격자"
version: "0.1.0"
status: draft
created: 2026-10-07
updated: 2026-10-07
author: jaihyun
priority: P1
phase: "Lighting Copilot v1.2 target"
module: "ui/src/components/RunbookMode.tsx, server/design/cue_sheet_edit.py(검증 관행 재사용만), 신규 beat-grid 편집 연산 모듈(M3), 신규 beat-grid 에미터 모듈(M4, 감독 확인 조건부), .moai/reports/SPEC-LDBEAT-001-probes(M1 산출물)"
lifecycle: spec-anchored
tags: "runbook-mode, beat-grid, role-sequence, console-probe, director-review, love-attack"
tier: M
related_specs: [SPEC-LDRHYTHM-001, SPEC-LDDESIGN-001, SPEC-LDRENDER-001]
---

# SPEC-LDBEAT-001 — 런북 모드 박자 배치: 역할별 트랙 × 마디 격자

## HISTORY

| 일자 | 내용 |
|---|---|
| 2026-10-07 | 최초 작성(카드 t522). 감독 결정 2026-10-07(원문, 리드 경유): 「보고서로 만들 이걸 앱의 런모드에 만들어야 하는 거야. 런모드에서 확인하고 수정작업을 하고 콘솔로 보내도록 하는 거」. 입력: `reports/effect-arrangement-rules-20261007.md`(규칙 9개·역할별 시퀀스 6개·LOVE ATTACK 전체 배치 §3·0~25마디 격자 §4·감독 결정 §5·안 잰 것 §6 — 주 체크아웃에만 있고 아직 추적되지 않음, 카드 t523이 PR로 저장소에 싣는다), `ui/src/components/RunbookMode.tsx`(280행, 기존 런북 모드), `server/design/cue_sheet_edit.py`(809행, 기존 큐시트 편집 파서·적용기), `.moai/specs/SPEC-LDDESIGN-001/spec.md` §3.15(M7 PLAN CUE 수정요청 생성기, REQ-LDDESIGN-087~095 — 로컬 변형 금지·단일 진실 경로 선례), `.moai/reports/t516/verdict.md`·`.moai/reports/t519/verdict.md`·`origin/WT-m2-batch1:.moai/reports/t520/verdict.md`(실기 사실), `.moai/reports/t512/approval_vs_sent.py`(승인=송신 비교 도구). Tier M(§0 근거). **plan만 — 코드 diff 0줄, 콘솔 접촉 0건.** |
| 2026-10-07 | **plan-audit iteration 1 FAIL(0.71, 통과선 0.80) 대응(같은 날 후속).** `.moai/reports/plan-audit/SPEC-LDBEAT-001-review-1.md` — 7개 must-pass 전부 PASS/N/A, FAIL은 집계 점수 미달. Traceability 0.50(D2/D3: REQ-LDBEAT-009·012가 블랭킷 메타 AC-011에만 걸려 전용 AC 없음) — 전용 AC 2개(AC-LDBEAT-014 역할 스코프 재사용 검증, AC-LDBEAT-015 배치당 승인 1개 검증)를 신설해 AC 13→15개로, §A.1 REQ→AC 추적 표를 추가해 두 REQ의 메타-AC 의존을 제거했다. D1(major, 블로킹): `module:`(spec.md:11)이 신규 에미터를 "M5"로 잘못 지칭 — plan.md가 M4(§E, "콘솔 송신 경로")에 그 작업을 두는 것과 불일치 — "M4"로 교정했다. D4(minor): `EDITABLE_FIELD_LABELS` 인용 범위가 `36-53`으로 실제 범위(여는 줄 38, 닫는 중괄호 55)를 벗어남 — `38-55`로 교정하고 빠졌던 `position_preset_no`("포지션 번호")를 REQ-007/008의 열거 목록에 추가했다(spec.md/plan.md/verdict.md 전부 교정). D5(minor, Clarity 0.75 기여): REQ-LDBEAT-007/008/013이 shall 절과 긴 서술을 한 칸에 섞어 둔 것을 — 각각 한 문장짜리 shall 절만 요구사항 칸에 남기고 근거·권고·인용은 근거 칸으로 옮겼다. D6(minor): REQ-LDBEAT-010이 다른 REQ와 달리 GEARS 트리거 키워드를 굵게 표시하지 않던 것 — `**When**`을 추가했다. REQ 총량 **14개 불변** · AC 총량 **13→15개**(AC-LDBEAT-014/015 신설) — Tier M 상한(각 16개) 안에 든다. |
| 2026-10-07 | **오케스트레이터 검토 D1~D3 대응(같은 날 후속, 커밋 전 수정).** 세 가지 결함을 이 plan-phase에서 재측정해 교정했다. **D1(거짓 전제, REQ-013/§5)**: "콘솔 타임코드는 사람이 GUI에서 손으로 만든다"는 서술이 거짓이었다 — 실측 결과 t516이 `Assign Sequence … At Timecode 20.1.2`(`.moai/reports/t516/verdict.md:104`)·`Store Timecode 20.1`(`:463`)을, t520이 `Store Sequence` 22줄·`Store Timecode` 4줄·`Assign Sequence` 2줄을 리허설 게이트 집계로 보내고 `Go Timecode 22`로 재생(`origin/WT-m2-batch1:.moai/reports/t520/verdict.md:186`)한 것이 유일하게 증명된 메커니즘이다 — **커맨드로 만들어진다**, 손으로 만드는 것이 아니다. REQ-LDBEAT-013을 "해소된 전제"에서 "미해결 결정 + 권고"로 다시 썼고, §5에서 "전부 해소(0건)" 표현을 지우고 열린 결정으로 올렸다. **D2(검증 안 된 재사용 주장, REQ-007~009)**: `parse_cue_sheet_edit_request`가 격자를 "이미 커버한다"는 주장이 틀렸다 — 그 파서는 큐 앵커(`_CUE_ANCHOR:227`, "큐 N"/"이 구간·큐·부분·씬·장면")와 큐 레벨 칸(`EDITABLE_FIELD_LABELS:36-53`)만 다루고, 마디 구간 앵커나 역할·모양·속도·축 어휘가 없다(이 plan-phase 재확인). 원칙(문장만 산출, 서버 단일 진실 지점, REQ-LDDESIGN-092/094/095)은 유지하되, **새** 서버측 편집 연산이 필요하다는 것으로 교정했다. **D3(데이터 모델 부재)**: "곡별 기본값이 저장된다"고만 적혀 있던 REQ-006에 저장소 실체를 채웠다 — `SongTimelineStore`(`server/web/session.py:3486`)·`TimelineDraftHistory`(`server/web/session.py:3831`, 전체 타임라인 사전을 깊은 사본으로 쌓는 generic 되돌리기, `session.py:8505`)·`SongTimelineLibrary`(`server/web/timeline_library.py:48`, 이름=곡·항목=버전의 명명·버전 저장소)를 실측해 인용했다. 셋 중 어느 것도 지금 역할×마디 필드를 갖지 않는다는 것도 명시했다. 또한 `.moai/reports/t512/approval_vs_sent.py`는 리포트 스크립트일 뿐 앱 코드가 아니라는 점을 REQ-011에 추가했다 — run-phase가 이를(또는 동등물을) 앱 경로로 승격해야 한다. REQ/AC 총량 불변(REQ 14개·AC 13개) — 기존 문면 교정 + §5 보강뿐, ID 추가삭제 없음. |

## §0. Tier 선택 근거

**Tier M.** 이 SPEC은 기존 컴포넌트(`RunbookMode.tsx`) 확장 + 새 서버측 편집 연산(`cue_sheet_edit.py`의 검증 관행·원칙 재사용, 로직은 새로 작성) + 콘솔 확인 프로브(M1, 코드 변경 없는 스크립트) + 승인=송신 비교 로직 재사용 + 박자 격자 전용 새 앱측 에미터(§3.6 REQ-013, 감독 확인 조건부)로 구성된다. 영향 파일 추정 5~15개(UI 컴포넌트 1~2개 신설, 신규 편집 연산 모듈 1개, 신규 에미터 모듈 1개, 기존 컴포넌트 수정, 프로브 스크립트 다수), LOC 추정 300~1000줄로 Tier S 상한(5파일/300LOC)을 넘지만 Tier L 기준(15파일/1000LOC 또는 헌법적 변경)에는 못 미친다. REQ 14개·AC 13개로 Tier M 상한(각 16개) 안에 든다.

## 감독 결정 (원문, 2026-10-07, 리드 경유)

> 「보고서로 만들 이걸 앱의 런모드에 만들어야 하는 거야. 런모드에서 확인하고 수정작업을 하고 콘솔로 보내도록 하는 거」

이 결정은 `reports/effect-arrangement-rules-20261007.md` §7(확정 뒤 순서) 1항이 이미 예고한 "새 SPEC"이다 — 그 문서가 명시한 두 장벽(앱 재생 계약이 `manual_go`/`trig_time`뿐이라 타임코드를 거절한다, 스피드 마스터 BPM을 곡과 함께 싣는 방법(G9)이 미확인이다)을 이 SPEC의 §3.6/§5가 승계한다. **다만 장벽 A는 이 plan-phase의 재측정으로 "앱 계약이 거절한다"에서 "콘솔 쪽은 커맨드로 증명됐으나 앱이 그 메커니즘을 아직 쓰지 않는다"로 더 정확하게 교정됐다** — §3.6 REQ-LDBEAT-013·§5 참조.

## 1. 배경 — 규칙은 확정됐다, 다음은 화면이다

`reports/effect-arrangement-rules-20261007.md`(이하 "배치 규칙서")가 감독과 함께 확정한 것:

- 규칙 9개(§1) — 속성마다 음악 단위가 다르다, 위치·색은 박마다 안 바뀐다, 리듬 타는 층은 보통 둘(드롭·마지막 코러스만 셋), 주인공 4마디 교대, 두 무빙은 다르게, 정지도 도구, FOH 유지, 파스텔 넓게·원색 짧게, 강조는 예고+적중(스트로브는 선택적).
- 역할별 시퀀스 6개(§2) — SCENE / BACK PULSE / SIDE CHASE / MOVER-U MOVE / MOVER-D MOVE / ACCENT. 각 역할은 그룹 선택 하나(또는 여럿-정적뿐)와 바뀌는 음악 단위를 갖는다.
- LOVE ATTACK 전체 배치(§3) — 마디별 SCENE/주인공/보조/무빙 U·D/강조 표.
- 0~25마디 박자 격자(§4) — "앱 화면이 처음 보여줄 범위", 4마디 단위 행 × 6 역할 트랙 열.
- 감독 결정 5건(§5) — 리듬 층 수, 색 자리표시 진하기, 스트로브 선택적, 벌스 무빙 미정 항목은 앱에서 편집 가능한 기본값으로, **다음 단계는 손 시연이 아니라 앱 런북 모드 구현**.
- 안 잰 것(§6) — 타임코드 트랙 3개 이상, 그룹 한 선택 페이저 큐 저장, 같은 그룹 다른 속성 겹침, circle·발리후·위상 펼침, 줌·고보·프리즘(빔 자체는 이 규칙에서 제외).

이 SPEC은 그 규칙을 **보는 화면**(런북 모드 박자 격자), **고치는 경로**(새 서버측 편집 연산 — 기존 큐시트 편집기의 검증 관행·"문장만 산출" 원칙을 재사용, §3.3), **승인 거쳐 보내는 경로**(기존 승인=송신 비교 로직 재사용, §3.5)로 옮긴다 — 새 규칙을 발명하지 않는다.

## 2. 기존 자산과의 관계 — 확장인가 신설인가

실측(`RunbookMode.tsx` 전체 280행, 2026-10-07 재확인):

- 런북 모드는 이미 5블록 순서를 갖는다 — 헤더(오늘의 곡·큐 순서) → 컨셉 패널(`ConceptPanel`) → `CueSheetTimeline`(가로 타임라인+세로 큐시트, 큐 단위 편집) → `SongTimeline`(에너지선+생성기 대화) → `RunbookGateBar`(상태줄) → 실행 런북(실행기 목록).
- 박자 격자(SCENE/BACK PULSE/… 6트랙 × 4마디 행)는 이 다섯 블록 중 어느 것과도 같은 모양이 아니다 — `CueSheetTimeline`은 **큐 번호 단위**(콘솔 큐 하나 = 한 행)이고, 배치 규칙서의 격자는 **마디 단위**(한 역할 트랙이 여러 큐·여러 타임코드 이벤트에 걸쳐 리듬을 탄다, §1 규칙 3). 격자는 `CueSheetTimeline`을 대체하지 않고 **그 위에 추가되는 새 블록**이다(REQ-LDBEAT-004).
- 편집 경로는 **원칙**을 재사용하고 **연산**은 새로 만든다 — 기존 `parse_cue_sheet_edit_request`(`server/design/cue_sheet_edit.py:264`)는 큐 앵커(`_CUE_ANCHOR:227`)와 큐 레벨 칸(`EDITABLE_FIELD_LABELS:38-55`)만 다루며 마디 구간·역할 어휘가 없다(이 plan-phase 재확인, D2 정정) — 그 경로가 격자를 "이미 커버한다"는 이전 서술은 틀렸다. `SPEC-LDDESIGN-001` REQ-LDDESIGN-092(M7)가 확정한 "로컬 변형 금지, 문장만 산출, 서버가 단일 진실 지점" **원칙**은 그대로 적용하되, 그 원칙을 구현하는 **새** 서버측 편집 연산(`cue_sheet_edit.py`와 나란히, 그 검증 관행을 재사용)을 M3가 설계한다(REQ-LDBEAT-007~009).
- 승인=송신 **비교 로직**은 신설하지 않는다 — `.moai/reports/t512/approval_vs_sent.py`(AC-LDRHYTHM-012가 쓰는 도구, t516·t519·t520이 실기로 검증한 패턴)의 로직을 그대로 쓴다. 다만 그 파일 자체는 리포트 스크립트(`.moai/reports/`, gitignore 대상)이고 앱 코드가 아니므로, run-phase가 앱이 참조 가능한 경로로 승격해야 한다(REQ-LDBEAT-011).

## 3. 요구사항 (GEARS)

### 3.1 R1 — 콘솔 확인 프로브 게이트 (REQ-LDBEAT-001~003)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBEAT-001 | [HARD] **While** 배치 규칙서 §6이 적은 미확인 콘솔 항목(타임코드 트랙 3개 이상, 단일 그룹 선택 페이저 큐 저장, 같은 그룹의 다른 속성을 두 시퀀스가 잡을 때 섞이는지, circle·발리후·위상 펼침 모양) 중 하나라도 작은 프로브로 아직 확인되지 않은 동안, 런북 모드의 박자 격자는 그 항목에 의존하는 콘솔 송신을 **shall not** 수행한다. | 감독 결정("확인하고 … 콘솔로 보내도록"), `reports/effect-arrangement-rules-20261007.md` §2 "🔴 실기에서 아직 확인 안 된 것" + §6, `origin/WT-m2-batch1:.moai/reports/t520/verdict.md` §20-4 프로브 1~4 |
| REQ-LDBEAT-002 | **When** M1 프로브가 실행되면, 그 절차는 **shall** t516/t519/t520이 쓴 기존 패턴(가짜 콘솔 리허설 → 실기 읽기 → 실기 전부-거절 → 감독 승인 → 실기 실행)을 따르고, 코드 diff 0줄·기존 번호 덮어쓰기 0건이다. 각 프로브는 §2의 네 항목 중 하나를 가르는 최소 단위로 설계한다(`.moai/reports/t520/verdict.md` §20-4의 "작은 프로브 하나로 묶을 수 있다" 제안 채택). | `.moai/reports/t516/verdict.md`·`.moai/reports/t519/verdict.md`·`origin/WT-m2-batch1:.moai/reports/t520/verdict.md` 선례 |
| REQ-LDBEAT-003 | **The** 프로브 결과 **shall** 이 SPEC의 `progress.md`에 항목별(타임코드≥3 트랙 / 단일 그룹 선택 저장 / 속성 겹침 / circle·발리후) PASS·FAIL·미실행으로 기록되며, M4(콘솔 송신 와이어링, §3.5)는 PASS로 기록된 항목에만 의존하는 송신 경로를 연다 — FAIL이거나 미실행인 항목에 의존하는 기능은 그 항목이 해소될 때까지 비활성(그레이아웃 또는 숨김) 상태를 유지한다. | REQ-LDBEAT-001의 게이트를 UI 상태로 구현하는 요구사항 |

### 3.2 R2 — 박자 격자 UX·데이터 모델 (REQ-LDBEAT-004~006)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBEAT-004 | **The** 런북 모드 **shall** 역할별 트랙(SCENE / BACK PULSE / SIDE CHASE / MOVER-U MOVE / MOVER-D MOVE / ACCENT) × 마디 격자 뷰를 새 블록으로 추가한다 — 기존 5블록(헤더·컨셉 패널·`CueSheetTimeline`·`SongTimeline`·`RunbookGateBar`) 순서와 코파일럿 메인 화면(`App.tsx`의 `runbookMode`가 거짓일 때 렌더되는 화면)은 이 SPEC이 수정하지 않는다(`REQ-LDDESIGN-078` 선례와 같은 경계). | 감독 결정, `reports/effect-arrangement-rules-20261007.md` §2·§4, 실측 `RunbookMode.tsx`(280행, 5블록) |
| REQ-LDBEAT-005 | **The** 박자 격자의 초기 표시 범위 **shall** 0~25마디(4마디 단위 행 7개)다 — 배치 규칙서 §4가 "앱 화면이 처음 보여줄 범위"로 확정한 구간이며, 그 구간 밖(26마디~)으로 스크롤·확장하는 것은 이 SPEC의 범위이되 초기 렌더는 §4 구간을 우선한다. | `reports/effect-arrangement-rules-20261007.md` §4 표 제목 |
| REQ-LDBEAT-006 | [HARD] **The** 박자 격자의 역할·배치 값 **shall** 서버측 단일 진실 지점에 곡별 기본값으로 저장되며, 배치 규칙서 §2~§4(LOVE ATTACK)는 그 첫 기본값의 소스일 뿐 전곡에 강제되는 고정 규칙이 아니다(감독이 곡마다 다른 배치를 선택·편집할 수 있다). **저장소 실체(이 plan-phase 재확인)**: 오늘 이 저장소의 "곡 타임라인" 저장은 세 메커니즘으로 나뉜다 — (a) `SongTimelineStore`(`server/web/session.py:3486`, 프로세스-전역 "현재" 타임라인 하나, `latest` 갱신마다 atomic JSON write, 경로는 `serve.py`가 사용자 데이터 디렉터리에 배선, 파일 손상 시 fail-open으로 "타임라인 없음"에 내려앉음), (b) `TimelineDraftHistory`(`server/web/timeline_draft.py`, `session.py:3831` `self._draft_history`, 되돌리기/다시하기 — `session.py:8505` `self._draft_history.record(timeline)`가 **편집 직전의 전체 타임라인 사전을** 깊은 사본으로 쌓는 generic 메커니즘이다, 필드 종류를 가리지 않는다), (c) `SongTimelineLibrary`(`server/web/timeline_library.py:48`, 이름=곡·항목=버전의 명명·버전 저장소, 같은 atomic temp+replace 패턴). **셋 중 어느 것도 지금 역할×마디 격자 필드를 갖지 않는다** — 이것은 M2의 명시적 설계 결정이다(§5): 격자 데이터를 기존 `timeline` 사전의 새 키(예: `beat_grid`)로 심으면 (b)의 되돌리기가 **코드 추가 없이** 격자 편집도 덮는다(전체-사전 스냅샷 방식 때문) — 이 임베드 방식을 M2의 **권고 기본 설계**로 삼되, 독립 저장소가 필요한지는 M2에서 director와 함께 확정한다. | 감독 결정(2026-09-23, 리드 경유) "스타일마다 다른데 하나로 고정은 무리" — `feedback-lighting-rules-are-defaults-not-universal.md`; 저장소 실측 `session.py:3486,3831,8505`, `timeline_library.py:48` |

### 3.3 R3 — 새 서버측 그리드 편집 연산 (REQ-LDBEAT-007~009)

> **D2 정정(2026-10-07)**: 기존 `parse_cue_sheet_edit_request`가 격자 편집을 "이미 커버한다"는 이전 문면은 검증 안 된 주장이었다 — 이 plan-phase가 재확인한 결과 그 파서는 큐 레벨 편집만 다루며, 마디 구간·역할 어휘가 없다(아래 REQ-007 근거). 아래 REQ들은 그 사실을 반영해 **새 서버측 편집 연산**을 요구하되, 그 연산이 지킬 **원칙**(문장만 산출, 서버 단일 진실 지점, 부분 적용 금지)은 기존 경로가 이미 증명한 것과 같다.

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBEAT-007 | [HARD] **The** 박자 격자의 수정 요청은 **shall** `cue_sheet_edit.py`와 나란히 두는 **새** 서버측 편집 연산(가칭 `apply_beat_grid_edit`)만을 거쳐 콘솔 커맨드 변경에 닿는다. | 기존 `parse_cue_sheet_edit_request`(`cue_sheet_edit.py:264`)는 큐 앵커 하나만 받는다 — `_CUE_ANCHOR`(`:227`, "큐 N"/"이 구간·큐·부분·씬·장면"/"선택된 구간·큐·부분")와 큐 레벨 칸(`EDITABLE_FIELD_LABELS:38-55`, 무드·컬러·조도·무브먼트·이펙트·전환·페이드·노트·트래킹·MIB·페이저·포지션·포지션 번호)뿐이며, 마디 구간 앵커("11~13마디")·역할(SCENE/BACK PULSE/SIDE CHASE/MOVER-U·D MOVE/ACCENT)·움직임 모양·속도·축·위상 어휘가 없다(이 plan-phase 재확인) — 그 경로가 박자 격자를 "이미 커버한다"는 이전 주장은 틀렸다(D2). UI는 문장만 산출한다는 원칙(REQ-LDDESIGN-092와 같은 모양)은 유지한다. 실측 `cue_sheet_edit.py:227,38-55,264`; `SPEC-LDDESIGN-001` REQ-LDDESIGN-092(원칙의 출처) |
| REQ-LDBEAT-008 | [HARD] **The** 새 편집 연산은 **shall** `cue_sheet_edit.py`의 검증 관행(부분 적용 금지·단일-원인 거절 사유·화이트리스트 패턴)을 재사용하고, 박자 격자 편집 UI가 서버 페이로드를 직접 구성해 그 연산을 우회하는 것을 **shall not** 허용한다. | 재사용 대상 관행 (a) 부분 적용 금지("사유를 던지기 전에 아무것도 쓰지 않는다", `apply_cue_sheet_edit:665` 독스트링), (b) 거절 사유를 한 가지 원인만 지목하는 예외 패턴(`CueSheetEditError`, `session.py:8498` 호출부의 "거짓 사유가 참 사유를 가리지 않게" 원칙), (c) 모르는 칸을 "없는 칸"으로 거절하는 화이트리스트 패턴(`EDITABLE_FIELD_LABELS:38-55`). 그 관행 위에 **새** 닫힌 화이트리스트(역할 6종, §6 미확인 모양을 포함한 모양 어휘 + "⚠ 미확인" 플래그, 속도·축 값 범위)를 그 연산 안에 선언한다 — 값 범위·부분 적용 금지·거절 사유의 단일 진실 지점은 서버다. `cue_sheet_edit.py:665,38-55`, `session.py:8498` 거절 사유 패턴 |
| REQ-LDBEAT-009 | **Where** 특정 역할 그룹에만 적용되는 편집(예: "MOVER-U만 틸트 웨이브로")이 필요하면, 새 편집 연산은 **shall** 기존 그룹 스코프 어휘·검증 관행(`_GROUP_SCOPE:187`, `_resolve_group_scope:493`)과 같은 모양을 재사용한다 — 역할명이 큐시트의 "그룹"과 다른 명명 체계일 수 있으므로, 역할→그룹 매핑은 새 연산이 선언하되, 매핑 뒤의 그룹 스코프 적용 로직은 기존 패턴을 그대로 본뜬다. | 실측 `cue_sheet_edit.py:187,493` |

### 3.4 R4 — 미확인 어휘 표시 (REQ-LDBEAT-010)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBEAT-010 | [HARD] **When** 박자 격자 칸에 circle·발리후(ballyhoo)·위상 펼침 등 §6의 미확인 모양이 제안되거나 선택 가능하게 노출되면, UI는 **shall** 그 칸에 "⚠ 실기 미확인" 표시를 달고, M1 프로브가 그 항목을 PASS로 확정하기 전에는 그 모양을 **곡의 기본값**으로 제공하지 **shall not**(REQ-LDBEAT-006의 기본값과 구분 — 미확인 모양은 사용자가 명시적으로 선택해야만 격자에 들어가며, 선택해도 전송은 REQ-LDBEAT-001의 게이트를 통과해야 한다). | `reports/effect-arrangement-rules-20261007.md` §3 "⚠ = 실기 미확인 모양" 표기, §6 |

### 3.5 R5 — 승인=송신 송신 경로 (REQ-LDBEAT-011~012)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBEAT-011 | [HARD] **When** 박자 격자의 변경이 콘솔로 송신되면, 승인된 커맨드 파일의 바이트와 실제 송신 기록을 재구성한 바이트는 **shall** 동일해야 한다(sha256 동일 + 설명 안 되는 줄 0건) — 비교 로직은 `.moai/reports/t512/approval_vs_sent.py`(AC-LDRHYTHM-012가 쓰는 도구, t516/t519/t520이 반복 검증한 패턴)의 로직을 그대로 재사용한다. 새 비교 로직을 발명하지 **shall not**. **그 파일 자체는 리포트 스크립트이고 앱 코드가 아니다**(`.moai/reports/`는 gitignore 대상 로컬 아티팩트) — run-phase는 M4(§3.5) 착수 시 그 로직(또는 바이트 동일 포팅)을 앱이 참조 가능한 경로(예: `server/` 아래 모듈, 또는 공유 스크립트 디렉터리)로 승격해야 한다, 리포트 디렉터리에서 그대로 import하지 않는다. | `AC-LDRHYTHM-012`, `.moai/reports/t512/approval_vs_sent.py`, t516/t519/t520 실기 검증 |
| REQ-LDBEAT-012 | **The** 콘솔 송신 경로 **shall** 구간(또는 묶음) 단위 커맨드 파일 1개를 통째로 1회 감독 승인받는 기존 절차(`SPEC-LDRHYTHM-001` REQ-LDRHYTHM-001)를 따른다 — 격자 칸 하나하나에 대한 줄 단위 개별 승인이 아니다. | `SPEC-LDRHYTHM-001` REQ-LDRHYTHM-001 |

### 3.6 R6 — 장벽 A(재생 계약 vs 증명된 콘솔 메커니즘)와 장벽 B(G9) (REQ-LDBEAT-013~014)

> **D1 정정(2026-10-07)**: "콘솔 타임코드는 사람이 GUI에서 손으로 만드는 것"이라는 이전 문면은 거짓이었다 — 아래 REQ-013이 재측정한 사실로 교정한다. 장벽 A는 **해소된 전제가 아니라 미해결 결정**이다(§5에 열린 결정으로 기록).

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBEAT-013 | [HARD] **The** 앱의 기존 재생 계약(`server/director/emit.py:51` `PLAYBACK_MODES = ("manual_go", "trig_time")`)과 기존 큐시트 재생 경로(`CueSheetTimeline`)는 **shall** 이 SPEC에서 바뀌지 않는다 — 박자 격자 전용 새 앱측 에미터의 신설 여부는 **열린 결정**이다(§5 항목 0, 감독 착수 승인 시점에 확인). | 박자 격자가 REQ-LDBEAT-001~005가 전제하는 대로 "마디 경계에 맞춰 보내진다"에는 타임코드 기반 송신이 필요하고, 그 메커니즘은 **사람이 콘솔 GUI에서 손으로 만드는 것이 아니라 커맨드로 만들어진다**: t516이 `Assign Sequence … At Timecode 20.1.2`(`.moai/reports/t516/verdict.md:104`)와 `Store Timecode 20.1`(`:463`)으로, t520이 `Store Sequence`(22줄)·`Store Timecode`(4줄)·`Assign Sequence`(2줄)를 리허설 게이트 집계로 보내고 `Go Timecode 22`로 재생(`origin/WT-m2-batch1:.moai/reports/t520/verdict.md:186`)한 것이 실기로 유일하게 증명된 메커니즘이다. 앱의 `emit.py` 에미터는 이 타임코드 기반 커맨드를 지금 만들지 않는다 — 타임코드 없이는 박자 격자가 마디에 맞춰 자동 재생될 길이 없다. **권고**: 기존 `emit.py`/`CueSheetTimeline`은 그대로 두고, 박자 격자 전용 새 앱측 에미터를 신설해 t520이 증명한 커맨드 모양(`Store Sequence`/`Store Timecode`/`Assign … At Timecode`/`Go Timecode`/`Off`)을 포팅하며 REQ-LDBEAT-011의 같은 승인=송신 검사를 거친다. 오디오 분석 기반 실시간 타임코드 생성(`SPEC-LDRHYTHM-001` REQ-LDRHYTHM-012(a))과는 다르다 — 새 에미터는 감독이 확정한 값을 배치로 커맨드화할 뿐이다(§4 Out of Scope). `server/director/emit.py:51`(이 plan-phase 재확인), `.moai/reports/t516/verdict.md:104,463`, `origin/WT-m2-batch1:.moai/reports/t520/verdict.md:92-94,183-186`, `SPEC-LDRHYTHM-001` REQ-LDRHYTHM-012(a)(b) |
| REQ-LDBEAT-014 | [HARD] **While** 스피드 마스터 BPM을 곡 재생 중 자동으로 싣는 방법(G9, `Master 3.n At BPM <값>`을 큐 커맨드나 매크로로 싣는 구체 방법)이 미확인인 동안, UI는 **shall** 그 값을 자동 설정 기능으로 표시하지 않고 "사람이 콘솔에서 직접 설정"이라는 안내를 표시한다. | `reports/effect-arrangement-rules-20261007.md` §7 "장벽 둘" 둘째, `SPEC-LDRHYTHM-001` REQ-LDRHYTHM-009 미확인 플래그 |

## 4. 제외 범위 (Out of Scope)

### Out of Scope — 오디오 분석 기반 실시간 타임코드 자동 생성

REQ-LDBEAT-013의 권고(새 앱측 에미터)는 감독이 격자에서 **확정한 값**을 배치로 커맨드화하는 것이지, 곡 재생 중 비트·다운비트를 실시간으로 검출해 타임코드 이벤트 시각을 그 자리에서 생성하는 것이 아니다. 후자는 `SPEC-LDRHYTHM-001` REQ-LDRHYTHM-012(a)의 M4+ 범위 후보로 남아 있고, 이 SPEC은 구현하지 않는다.

- 곡 재생 중 비트/다운비트/킥을 실시간 검출해 그 자리에서 타임코드 이벤트를 생성하는 서버 로직(`server/audio/analyze.py` 확장).

### Out of Scope — 코파일럿 메인 화면 변경

`App.tsx`의 `runbookMode`가 거짓일 때 렌더되는 메인 화면(리그 대시보드·프리셋 풀 브라우저·큐 모니터·채팅·설정·페이퍼워크)과 그 컴포넌트는 이 SPEC이 수정하지 않는다(REQ-LDBEAT-004).

- `App.tsx`의 메인 화면 분기 로직, `PresetPoolPopup.tsx` 등 메인 화면 전용 컴포넌트의 재구현.

### Out of Scope — LOVE ATTACK 이외 곡의 곡별 기본값 자동 생성

이 SPEC은 LOVE ATTACK의 배치 규칙서(§2~§4)를 첫 곡별 기본값의 소스로 쓴다. 다른 곡의 배치 규칙서를 작성하거나, 임의의 곡에서 배치 규칙서를 자동 생성하는 알고리즘(예: 자동 비트/드롭 검출로 역할 배치를 추론)은 범위 밖이다(REQ-LDBEAT-006).

- 다른 곡(LOVE ATTACK 이외)의 역할별 배치 규칙서 작성, 자동 배치-생성 알고리즘.

### Out of Scope — circle·발리후 등 미확인 모양의 실기 구현

M1 프로브가 확인하기 전에는 circle·발리후·위상 펼침 모양을 콘솔에 실제로 저장·재생하는 기능을 구현하지 않는다(REQ-LDBEAT-001, REQ-LDBEAT-010). 확인 자체(프로브)는 범위 안이다.

- circle·발리후 모양을 콘솔에 저장하는 서버 함수(확인 전), 빔(줌·고보·프리즘) 관련 역할 트랙 추가(배치 규칙서 §6이 명시적으로 뺀 항목).

### Out of Scope — 스피드 마스터 BPM 자동 설정(G9)

G9(곡 재생 중 BPM을 자동으로 싣는 방법)가 미확인인 동안, 그 자동화는 구현하지 않는다(REQ-LDBEAT-014).

- `Master 3.n At BPM <값>`을 큐 재생 중 자동으로 싣는 매크로/커맨드 로직.

### Out of Scope — 이 plan-phase 자신의 콘솔 접촉

이 문서를 작성하는 plan-phase 자신은 콘솔에 어떤 커맨드도 보내지 않는다. M1 프로브의 콘솔 쓰기는 이 SPEC의 run-phase 이후, 감독 착수 승인 뒤의 별도 활동이다.

- 이 plan-phase 세션의 콘솔 접촉(조회·쓰기 모두 포함).

## 5. 열린 결정

이전 버전("전부 해소(0건)")은 틀렸다 — 오케스트레이터 검토(D1)가 장벽 A를 해소된 전제가 아니라 미해결 결정으로 되돌렸다. 아래 두 항목(0·0')은 **감독 착수 승인 시점에 확인이 필요한 결정**이고, 나머지는 구현 전 재확인이 필요한 잔여 플래그다(발명하지 않고 명시만 함).

0. **[열린 결정 — 감독 확인 필요] 박자 격자의 콘솔 송신에 타임코드가 필요한가, 그렇다면 새 앱측 에미터를 만들 것인가** (REQ-LDBEAT-013). 박자 격자가 마디 경계에 맞춰 자동 재생되려면 타임코드 기반 송신이 필요하고, 그 메커니즘은 콘솔 쪽에서 커맨드로 증명됐다(t516/t520). 이 plan-phase의 권고는 "기존 `emit.py`/`CueSheetTimeline`은 그대로 두고, 박자 격자 전용 새 에미터를 추가"이지만, 이것은 **권고일 뿐 결정이 아니다** — 감독이 다른 방향(예: 타임코드 없이 큐 전환만으로 근사, 또는 M4를 전체 보류)을 선택할 수 있다. Implementation Kickoff Approval 시점에 이 권고를 제시하고 명시적으로 확인받아야 한다.
0'. **[열린 결정 — M2에서 확정] 박자 격자 데이터가 어디에 저장되는가** (REQ-LDBEAT-006). 이 plan-phase의 권고는 "기존 `timeline` 사전의 새 키로 임베드해 `TimelineDraftHistory`/`SongTimelineStore`/`SongTimelineLibrary`를 코드 추가 없이 재사용"이지만, 격자가 독립 저장소를 필요로 할 만큼 커지거나(예: 26~82마디 전체 + 여러 곡의 여러 버전) 생명주기가 다를 경우 M2에서 별도 모듈을 신설하는 쪽으로 바뀔 수 있다.
1. **벌스 무빙 배치는 감독의 직접 답이 없다** — 배치 규칙서 §5가 "초안(한쪽만 느리게, 다른 쪽 정지, 4마디 교대)을 기본값으로 두고, 앱에서 고칠 수 있게 한다"고 명시했다. REQ-LDBEAT-006의 "곡별 기본값 + 감독 편집" 모델이 이 결정을 그대로 구현한다 — 별도 재결정 사항이 아니다.
2. **BACK 방향(Pan 180/Tilt 80)은 계산상 바닥 밖(공중)을 비춘다** — `.moai/reports/t519/verdict.md` §7-4. 펄스를 넣어도 화면에서 덜 보일 수 있다는 잔여 위험이 있으나, 이 SPEC의 범위(UI·편집·승인 경로)와는 독립적이다 — 역할 배치값 자체의 현장감은 M1 프로브와 별개로 감독이 격자에서 직접 조정할 수 있다(REQ-LDBEAT-006).
3. **타임코드 트랙 6개(배치 규칙서 §2 "타임코드 하나에 트랙 여섯")는 t516이 2개까지만 측정했다** — REQ-LDBEAT-001의 게이트가 이 항목을 M1 프로브 대상으로 묶는다.
