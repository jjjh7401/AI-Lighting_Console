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
module: "ui/src/components/RunbookMode.tsx, server/design/cue_sheet_edit.py(재사용만), .moai/reports/SPEC-LDBEAT-001-probes(M1 산출물)"
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

## §0. Tier 선택 근거

**Tier M.** 이 SPEC은 기존 컴포넌트(`RunbookMode.tsx`) 확장 + 기존 편집 경로(`cue_sheet_edit.py`) 재사용 + 콘솔 확인 프로브(M1, 코드 변경 없는 스크립트) + 승인=송신 비교 도구 재사용으로 구성된다 — 신규 서버 레이어나 신규 파서를 만들지 않는다. 영향 파일 추정 5~15개(UI 컴포넌트 1~2개 신설, 기존 컴포넌트 수정, 프로브 스크립트 다수), LOC 추정 300~1000줄로 Tier S 상한(5파일/300LOC)을 넘지만 Tier L 기준(15파일/1000LOC 또는 헌법적 변경)에는 못 미친다. REQ 14개·AC 13개로 Tier M 상한(각 16개) 안에 든다.

## 감독 결정 (원문, 2026-10-07, 리드 경유)

> 「보고서로 만들 이걸 앱의 런모드에 만들어야 하는 거야. 런모드에서 확인하고 수정작업을 하고 콘솔로 보내도록 하는 거」

이 결정은 `reports/effect-arrangement-rules-20261007.md` §7(확정 뒤 순서) 1항이 이미 예고한 "새 SPEC"이다 — 그 문서가 명시한 두 장벽(앱 재생 계약이 `manual_go`/`trig_time`뿐이라 타임코드를 거절한다, 스피드 마스터 BPM을 곡과 함께 싣는 방법(G9)이 미확인이다)은 이 SPEC의 §3.6/§5에서 그대로 승계한다.

## 1. 배경 — 규칙은 확정됐다, 다음은 화면이다

`reports/effect-arrangement-rules-20261007.md`(이하 "배치 규칙서")가 감독과 함께 확정한 것:

- 규칙 9개(§1) — 속성마다 음악 단위가 다르다, 위치·색은 박마다 안 바뀐다, 리듬 타는 층은 보통 둘(드롭·마지막 코러스만 셋), 주인공 4마디 교대, 두 무빙은 다르게, 정지도 도구, FOH 유지, 파스텔 넓게·원색 짧게, 강조는 예고+적중(스트로브는 선택적).
- 역할별 시퀀스 6개(§2) — SCENE / BACK PULSE / SIDE CHASE / MOVER-U MOVE / MOVER-D MOVE / ACCENT. 각 역할은 그룹 선택 하나(또는 여럿-정적뿐)와 바뀌는 음악 단위를 갖는다.
- LOVE ATTACK 전체 배치(§3) — 마디별 SCENE/주인공/보조/무빙 U·D/강조 표.
- 0~25마디 박자 격자(§4) — "앱 화면이 처음 보여줄 범위", 4마디 단위 행 × 6 역할 트랙 열.
- 감독 결정 5건(§5) — 리듬 층 수, 색 자리표시 진하기, 스트로브 선택적, 벌스 무빙 미정 항목은 앱에서 편집 가능한 기본값으로, **다음 단계는 손 시연이 아니라 앱 런북 모드 구현**.
- 안 잰 것(§6) — 타임코드 트랙 3개 이상, 그룹 한 선택 페이저 큐 저장, 같은 그룹 다른 속성 겹침, circle·발리후·위상 펼침, 줌·고보·프리즘(빔 자체는 이 규칙에서 제외).

이 SPEC은 그 규칙을 **보는 화면**(런북 모드 박자 격자), **고치는 경로**(기존 큐시트 편집 파서 재사용), **승인 거쳐 보내는 경로**(기존 승인=송신 비교 도구 재사용)로 옮긴다 — 새 규칙을 발명하지 않는다.

## 2. 기존 자산과의 관계 — 확장인가 신설인가

실측(`RunbookMode.tsx` 전체 280행, 2026-10-07 재확인):

- 런북 모드는 이미 5블록 순서를 갖는다 — 헤더(오늘의 곡·큐 순서) → 컨셉 패널(`ConceptPanel`) → `CueSheetTimeline`(가로 타임라인+세로 큐시트, 큐 단위 편집) → `SongTimeline`(에너지선+생성기 대화) → `RunbookGateBar`(상태줄) → 실행 런북(실행기 목록).
- 박자 격자(SCENE/BACK PULSE/… 6트랙 × 4마디 행)는 이 다섯 블록 중 어느 것과도 같은 모양이 아니다 — `CueSheetTimeline`은 **큐 번호 단위**(콘솔 큐 하나 = 한 행)이고, 배치 규칙서의 격자는 **마디 단위**(한 역할 트랙이 여러 큐·여러 타임코드 이벤트에 걸쳐 리듬을 탄다, §1 규칙 3). 격자는 `CueSheetTimeline`을 대체하지 않고 **그 위에 추가되는 새 블록**이다(REQ-LDBEAT-004).
- 편집 경로는 신설하지 않는다 — `parse_cue_sheet_edit_request`(`server/design/cue_sheet_edit.py:264`) → `apply_cue_sheet_edit`(`:665`) → `server/web/session.py:8467` `_cue_sheet_draft_edit` 경로, 그룹 스코프 파서(`_GROUP_SCOPE:187`, `_resolve_group_scope:493`)를 그대로 쓴다. `SPEC-LDDESIGN-001` REQ-LDDESIGN-092(M7)가 이미 확정한 "로컬 변형 금지, 문장만 산출, 서버가 단일 진실 지점" 원칙을 격자 편집에도 적용한다(REQ-LDBEAT-007~009).
- 승인=송신 비교도 신설하지 않는다 — `.moai/reports/t512/approval_vs_sent.py`(AC-LDRHYTHM-012가 쓰는 도구, t516·t519·t520이 실기로 검증한 패턴)를 그대로 쓴다(REQ-LDBEAT-011).

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
| REQ-LDBEAT-006 | **The** 박자 격자의 역할·배치 값 **shall** 곡별 기본값으로 저장되며, 배치 규칙서 §2~§4(LOVE ATTACK)는 그 첫 기본값의 소스일 뿐 전곡에 강제되는 고정 규칙이 아니다 — 감독이 곡마다 다른 배치를 선택·편집할 수 있다. | 감독 결정(2026-09-23, 리드 경유) "스타일마다 다른데 하나로 고정은 무리" — 기본값 + 곡별 선택 모델, `feedback-lighting-rules-are-defaults-not-universal.md` |

### 3.3 R3 — 편집 경로 재사용 (REQ-LDBEAT-007~009)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBEAT-007 | [HARD] 박자 격자 칸의 수정 요청 **shall** 기존 경로(`parse_cue_sheet_edit_request` `server/design/cue_sheet_edit.py:264` → `apply_cue_sheet_edit` `:665` → `server/web/session.py:8467` `_cue_sheet_draft_edit`)로만 콘솔 커맨드 변경에 닿는다 — 생성기의 산출물은 **문장뿐**이다(REQ-LDDESIGN-092와 같은 원칙). | `SPEC-LDDESIGN-001` REQ-LDDESIGN-092, 실측 `cue_sheet_edit.py:264,665`, `session.py:8467` |
| REQ-LDBEAT-008 | [HARD] 박자 격자 편집 UI는 **shall not** 격자 객체(역할·배치 상태)를 로컬에서 변형하거나 서버 `changes` 매핑을 UI가 직접 만들어 기존 파서를 우회한다 — 값 범위(조도 0-100, 페이드 ≤60초, `TRANS_VALUES` 3종)·부분 적용 금지·거절 사유 문자열의 단일 진실 지점은 서버(`apply_cue_sheet_edit`)다. | `SPEC-LDDESIGN-001` REQ-LDDESIGN-092, `cue_sheet_edit.py:665` 부분 적용 금지 독스트링 |
| REQ-LDBEAT-009 | **Where** 특정 역할 그룹에만 적용되는 편집(예: "MOVER-U만 틸트 웨이브로")이 필요하면, **shall** 기존 그룹 스코프 파서(`_GROUP_SCOPE:187`, `_resolve_group_scope:493`)를 사용한다 — 새 그룹 스코프 파서를 만들지 않는다. | 실측 `cue_sheet_edit.py:187,493` |

### 3.4 R4 — 미확인 어휘 표시 (REQ-LDBEAT-010)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBEAT-010 | [HARD] 박자 격자 칸에 circle·발리후(ballyhoo)·위상 펼침 등 §6의 미확인 모양이 제안되거나 선택 가능하게 노출될 때, UI는 **shall** 그 칸에 "⚠ 실기 미확인" 표시를 달고, M1 프로브가 그 항목을 PASS로 확정하기 전에는 그 모양을 **곡의 기본값**으로 제공하지 **shall not**(REQ-LDBEAT-006의 기본값과 구분 — 미확인 모양은 사용자가 명시적으로 선택해야만 격자에 들어가며, 선택해도 전송은 REQ-LDBEAT-001의 게이트를 통과해야 한다). | `reports/effect-arrangement-rules-20261007.md` §3 "⚠ = 실기 미확인 모양" 표기, §6 |

### 3.5 R5 — 승인=송신 송신 경로 (REQ-LDBEAT-011~012)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBEAT-011 | [HARD] **When** 박자 격자의 변경이 콘솔로 송신되면, 승인된 커맨드 파일의 바이트와 실제 송신 기록을 재구성한 바이트는 **shall** 동일해야 한다(sha256 동일 + 설명 안 되는 줄 0건) — `.moai/reports/t512/approval_vs_sent.py`(AC-LDRHYTHM-012가 쓰는 도구)를 그대로 재사용한다. 새 비교 도구를 발명하지 **shall not**. | `AC-LDRHYTHM-012`, `.moai/reports/t512/approval_vs_sent.py`, t516/t519/t520 실기 검증 |
| REQ-LDBEAT-012 | **The** 콘솔 송신 경로 **shall** 구간(또는 묶음) 단위 커맨드 파일 1개를 통째로 1회 감독 승인받는 기존 절차(`SPEC-LDRHYTHM-001` REQ-LDRHYTHM-001)를 따른다 — 격자 칸 하나하나에 대한 줄 단위 개별 승인이 아니다. | `SPEC-LDRHYTHM-001` REQ-LDRHYTHM-001 |

### 3.6 R6 — 두 장벽의 범위 경계 (REQ-LDBEAT-013~014)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBEAT-013 | [HARD] **The** 앱의 재생 계약(`server/director/emit.py:51` `PLAYBACK_MODES = ("manual_go", "trig_time")`) **shall** 이 SPEC에서 바뀌지 않는다 — 박자 격자의 콘솔 송신 경로는 기존 `Store`/`Go`/`Goto` 커맨드만 사용하며, 앱이 타임코드 재생 모드로 자동 진입한다고 가정하는 코드·UI 문구를 두지 **shall not**. 콘솔 쪽 타임코드 이벤트(사람이 콘솔 GUI에서 손으로 만드는 트랙·이벤트, t506/t516/t519/t520이 실기로 확인한 메커니즘)는 이 게이트 밖이며 M1 프로브의 대상이다 — 앱의 **재생 계약**과 콘솔의 **타임코드 객체**는 서로 다른 층이다. | `server/director/emit.py:51`(이 plan-phase 재확인), `reports/effect-arrangement-rules-20261007.md` §7 "장벽 둘" 첫째, `SPEC-LDRHYTHM-001` REQ-LDRHYTHM-012(b) |
| REQ-LDBEAT-014 | [HARD] **While** 스피드 마스터 BPM을 곡 재생 중 자동으로 싣는 방법(G9, `Master 3.n At BPM <값>`을 큐 커맨드나 매크로로 싣는 구체 방법)이 미확인인 동안, UI는 **shall** 그 값을 자동 설정 기능으로 표시하지 않고 "사람이 콘솔에서 직접 설정"이라는 안내를 표시한다. | `reports/effect-arrangement-rules-20261007.md` §7 "장벽 둘" 둘째, `SPEC-LDRHYTHM-001` REQ-LDRHYTHM-009 미확인 플래그 |

## 4. 제외 범위 (Out of Scope)

### Out of Scope — SPEC-LDRHYTHM-001 M4+ 자동 타임코드 재생

앱이 박자 격자에서 마디 경계를 자동으로 타임코드 이벤트로 송신·재생하는 기능(완전 자동화)은 `SPEC-LDRHYTHM-001` REQ-LDRHYTHM-012(b)의 M4+ 범위 후보로 남아 있고, 이 SPEC은 그 자동화를 구현하지 않는다(REQ-LDBEAT-013).

- 마디 경계를 감지해 자동으로 `Store Timecode`/이벤트를 생성·재생하는 서버 로직.

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

## 5. 열린 결정 — 전부 해소(0건), 잔여 플래그만 기록

1. **벌스 무빙 배치는 감독의 직접 답이 없다** — 배치 규칙서 §5가 "초안(한쪽만 느리게, 다른 쪽 정지, 4마디 교대)을 기본값으로 두고, 앱에서 고칠 수 있게 한다"고 명시했다. REQ-LDBEAT-006의 "곡별 기본값 + 감독 편집" 모델이 이 결정을 그대로 구현한다 — 별도 재결정 사항이 아니다.
2. **BACK 방향(Pan 180/Tilt 80)은 계산상 바닥 밖(공중)을 비춘다** — `.moai/reports/t519/verdict.md` §7-4. 펄스를 넣어도 화면에서 덜 보일 수 있다는 잔여 위험이 있으나, 이 SPEC의 범위(UI·편집·승인 경로)와는 독립적이다 — 역할 배치값 자체의 현장감은 M1 프로브와 별개로 감독이 격자에서 직접 조정할 수 있다(REQ-LDBEAT-006).
3. **타임코드 트랙 6개(배치 규칙서 §2 "타임코드 하나에 트랙 여섯")는 t516이 2개까지만 측정했다** — REQ-LDBEAT-001의 게이트가 이 항목을 M1 프로브 대상으로 묶는다.
