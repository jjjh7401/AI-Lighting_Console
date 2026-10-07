# t522 판정서 — SPEC-LDBEAT-001 plan-phase (런북 모드 박자 배치)

- 카드: t522 · 워크트리 `.claude/worktrees/t522`, 브랜치 `WT-runbook-beat`(기준 `5ccd1d1c` = origin/main)
- 범위: SPEC 문서 3개(spec.md/plan.md/acceptance.md) + progress.md + 이 판정서만. 코드 diff 0줄, 콘솔 명령 0건.

## 1. 작업 전 확인(실행한 명령 + 핵심 출력)

```
$ git rev-parse --show-toplevel && git branch --show-current
/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/.claude/worktrees/t522
WT-runbook-beat
```
→ 지시된 워크트리·브랜치와 일치. 이어서 `git status --short`는 비어 있었다(clean).

```
$ ID="SPEC-LDBEAT-001"; [[ "$ID" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]] && echo PASS || echo FAIL
PASS
```

```
$ ls .moai/specs/ | grep -iE 'BEAT|RUNBOOK|GRID'
(출력 없음 — 충돌 0건)
```

## 2. 측정한 것 (명령 + 핵심 결과, 전부 이 plan-phase에서 재실행)

| 대상 | 명령 | 핵심 결과 |
|---|---|---|
| `RunbookMode.tsx` 전체 | `Read` 전체 280행 | 기존 5블록(헤더→`ConceptPanel`→`CueSheetTimeline`→`SongTimeline`→`RunbookGateBar`→실행 런북) 확인. `onApplyDraft`(승인 카드 경로), `onGeneratorSend`(t460 REQ-087~101 생성기 배선) prop 존재. |
| `cue_sheet_edit.py` 함수 목록 | `wc -l` + `grep -n "^def \|^class "` | 809행. `parse_cue_sheet_edit_request:264`, `apply_cue_sheet_edit:665`, `_find_section:359`, `_group_levels:376`, `_resolve_group_scope:493` 등 확인. |
| `SPEC-LDDESIGN-001` §3.13~3.16 | `sed -n '280,340p'` | REQ-LDDESIGN-073~101 전문 확인 — REQ-092(로컬 변형 금지, 문장만 산출), REQ-078(런북 모드가 대상 화면, 메인 화면은 건드리지 않음), REQ-086(런북이 초안을 메인에 노출하지 않음, `onApplyDraft` 경로). |
| `emit.py:51` `PLAYBACK_MODES` | `grep -n "PLAYBACK_MODES" server/director/emit.py` | `PLAYBACK_MODES = ("manual_go", "trig_time")`, import 지점·`__all__` 포함 확인. 장벽 A의 근거. |
| `SPEC-LDRHYTHM-001` spec.md/plan.md | 전체 `Read` | REQ-LDRHYTHM-001(승인 절차)·009(스피드 마스터, G9 미확인)·012(M4+ 범위 후보, (b) 타임코드). plan.md §B 위험 4(앱 계약 vs 콘솔 타임코드 구분), §E M2 구현 방식(반복 동작=페이저, 장면 경계=타임코드 이벤트). |
| t512 판정서 | `Read` 전체 | `approval_vs_sent.py` 도구 — 실데이터 4/4 PASS·양성 대조 4/4 FAIL. 비교 기준(송신 기록 = 감사 로그 `executed`·읽기 질의 제외), sha256 정규형 비교. |
| t519 판정서 | `Read` 전체 | BACK 방향 문제(높이 아님, Pan 180/Tilt 80 감독 결정) — 판정 정정 과정(사실 보존, 결론 철회) 확인. |
| t516 판정서 | `Read` 전체(§1~§4-6 상세, 이후 목차) | 페이저·SpeedMaster·Measure·트랙 2개·BACK 무점등 등 확인/미확인 표. "다음 카드" 란이 BACK 패치 판독(→ t519)을 가리킴. |
| t520 판정서(미머지) | `git show origin/WT-m2-batch1:.moai/reports/t520/verdict.md` | 751행 전부(출력 분할 2회) 읽음. §20-4 역할별 시퀀스 구조 제안 + 프로브 1~4, §14 그룹 선택 결과("둘 다 켜졌어"), Spiider `Dimmer2` 필요(§17/§18-1), 점 번호 목록 거절(`Illegal object`). |
| 배치 규칙서(주 체크아웃, 미추적) | `Read` 전체(142행) | 규칙 9개·역할별 시퀀스 6개(§2)·LOVE ATTACK 전체 배치(§3)·0~25마디 격자(§4)·감독 결정 5건(§5)·안 잰 것(§6)·확정 뒤 순서(§7, "새 SPEC(plan만)" 명시). |
| REQ-LDDESIGN-053 | `grep -n "REQ-LDDESIGN-053"` | `tracking` 필드 4모드(Block/Track/Cue Only/Release) 확인 — 이 SPEC의 범위 밖(§4 Out of Scope에 명시하지 않았으나 편집 경로 재사용 시 그대로 적용됨, REQ-LDBEAT-007이 암묵 승계). |

## 3. REQ/AC 집계

- `spec.md`: REQ-LDBEAT-001~014, **14개**(오케스트레이터 검토 D1~D3 교정 후에도 불변). 6개 그룹(R1 프로브 게이트 3개·R2 UX/데이터 모델/저장소 3개·R3 새 서버측 편집 연산 3개·R4 미확인 표시 1개·R5 승인=송신 2개·R6 장벽 경계 2개).
- `acceptance.md`: AC-LDBEAT-001~013, **13개**(불변). Given-When-Then 13건 + 엣지 케이스 3건 + 인간 판단 3건 + DoD 체크 7항목 + 품질 게이트 기준 3항목.
- Tier M 상한(각 16개) 이내 — REQ 14/16, AC 13/16.
- Out of Scope H3 하위헤딩 6개(`### Out of Scope — ...`) 전부 `-` 불릿 포함 — `OutOfScopeRule` 린트 충족(D1 교정으로 첫 섹션명이 "SPEC-LDRHYTHM-001 M4+ 자동 타임코드 재생"에서 "오디오 분석 기반 실시간 타임코드 자동 생성"으로 바뀌었다 — 개수는 그대로 6개).

## 4. 오케스트레이터 검토 D1~D3 재측정 (2026-10-07, 같은 날 후속, 커밋 전 수정)

### D1 — 거짓 전제: "콘솔 타임코드는 사람이 GUI에서 손으로 만든다"

**재측정 명령 + 핵심 출력(전부 이 수정에서 재실행):**

```
$ sed -n '100,108p' .moai/reports/t516/verdict.md
```
→ 104행: `④ 트랙 둘 | TC20/1 아래 Track 두 개: NO 1 → Sequence 220, NO 2 → Sequence 221. 두 번째 Assign … At Timecode 20.1.2가 새 트랙을 만들었다.` — **커맨드**(`Assign … At Timecode 20.1.2`)가 트랙을 만들었다는 명시적 서술.

```
$ sed -n '460,464p' .moai/reports/t516/verdict.md
```
→ 463행: `Store Timecode 20.1(트랙 그룹 만들기)은 t506 1회차 PREP 모양이다.` — `Store Timecode`도 커맨드.

```
$ git show origin/WT-m2-batch1:.moai/reports/t520/verdict.md | sed -n '92,97p'
```
→ 94행: `트랙을 셋 이상으로 늘리는 것은 안 잰 일이라 피했다.` (트랙 둘은 커맨드로 만듦, t516 v1에서 기계로 PASS).

```
$ git show origin/WT-m2-batch1:.moai/reports/t520/verdict.md | grep -n "Store Sequence.*22\|Store Timecode.*4\|Assign Sequence.*2\|Go Timecode 22"
```
→ 186행: `게이트 사유(리허설 steps.jsonl 집계): Store Sequence 22 · Store Timecode 4 · Assign Sequence 2가 금지 목록에 걸린다.` — 리허설 게이트가 커맨드 동사를 **집계**했다는 것 자체가 커맨드로 만들어졌다는 증거. 183행: `Go Timecode 22` / `Off Timecode 22`로 재생.

**결론**: 이전 버전의 "사람이 콘솔 GUI에서 손으로 만든다"는 서술은 **거짓**이었다. 콘솔 쪽 타임코드 트랙·이벤트는 커맨드(`Store Sequence`/`Store Timecode`/`Assign … At Timecode`/`Go Timecode`/`Off`)로 만들어진다 — 이 사실은 이미 t516/t520 당시에도 측정돼 있었으나, 이전 plan.md §B 위험 3·spec.md REQ-013이 그 사실을 "사람이 손으로"로 잘못 서술해 장벽 A를 거짓으로 "해소"해 버렸다.

**교정**: `spec.md` REQ-LDBEAT-013을 전면 재작성(§3.6) — 앱의 `PLAYBACK_MODES`/`CueSheetTimeline`은 불변이되, 박자 격자가 마디에 맞춰 보내지려면 타임코드가 필요하고 그 메커니즘은 증명됐으니 **새 앱측 에미터 권고**를 명시, 감독 확인이 필요한 **열린 결정**으로 §5에 0번 항목 추가. `plan.md` §B 위험 3·M4를 재작성(M4가 장벽 A의 결정+조건부 구현을 담당). `acceptance.md` AC-LDBEAT-012를 "타임코드 코드 0건 확인"에서 "기존 `emit.py`/`CueSheetTimeline` diff 0줄 확인"으로 교정(새 에미터가 생겨도 기존 경로는 안 바뀜을 검사하는 것으로 의미를 바꿨다 — 전자는 이제 성립하지 않는 전제였다).

### D2 — 검증 안 된 재사용 주장: "기존 큐시트 파서가 격자를 이미 커버한다"

**재측정 명령 + 핵심 출력:**

```
$ sed -n '105,115p' server/design/cue_sheet_edit.py
```
→ 111행: `_CUE_NUMBER = re.compile(r"큐\s*(?P<cue>\d+)")` — 큐 번호만 매칭, 마디 구간 패턴 없음.

```
$ sed -n '220,232p' server/design/cue_sheet_edit.py
```
→ 227행: `_CUE_ANCHOR = re.compile(r"큐\s*\d+|이\s*(구간|큐|부분|씬|장면)|선택(한|된)\s*(구간|큐|부분)")` — "큐 N"·"이 구간/큐/부분/씬/장면"·"선택된 구간/큐/부분" 세 패턴뿐. "11~13마디" 같은 마디 구간 앵커 없음.

```
$ sed -n '35,58p' server/design/cue_sheet_edit.py
```
→ 36-53행 `EDITABLE_FIELD_LABELS`: 무드·컬러(주/보조)·조도·무브먼트·이펙트·전환·페이드·노트·트래킹·MIB·페이저·포지션 — 12칸, 전부 **큐 레벨**. 역할(SCENE/BACK PULSE/…)·움직임 모양 어휘·속도·축·위상 필드 없음.

**결론**: "그 경로가 격자를 이미 커버한다"는 이전 서술은 틀렸다. 그 파서는 큐 레벨 편집 전용이며 마디 구간·역할 어휘가 전혀 없다.

**교정**: `spec.md` §3.3(R3)을 "편집 경로 재사용"에서 "새 서버측 그리드 편집 연산"으로 재작성 — REQ-LDBEAT-007~009 전부 재작성, 재사용 대상을 **원칙·검증 관행**(부분 적용 금지, 단일-원인 거절 사유, 화이트리스트 패턴)으로 좁히고 **연산 자체는 새로** 만들도록 명시. `plan.md` M3·§B 위험 5·§F 안티패턴을 동일하게 교정. `acceptance.md` AC-LDBEAT-005/010을 "새 연산을 거치는지" 검사로 재작성.

### D3 — 데이터 모델 부재: "곡별 기본값이 저장된다"고만 적혀 있었음

**재측정 명령 + 핵심 출력:**

```
$ sed -n '1,30p' server/web/timeline_draft.py
```
→ `TimelineDraftHistory` — "되돌릴 수 있는 걸음 수" 스택, `record(previous: dict)`가 깊은 사본을 쌓는 generic 메커니즘(필드 종류 무관).

```
$ grep -n "_draft_history\." server/web/session.py
```
→ 8505행: `self._draft_history.record(timeline)` — **전체 `timeline` 사전**을 스냅샷. `timeline = store.latest`(8482행 부근, `_cue_sheet_draft_edit` 본문) — `store`는 `self._timeline_store`(`SongTimelineStore` 인스턴스).

```
$ sed -n '3486,3502p' server/web/session.py
```
→ `class SongTimelineStore` — "Process-wide LAST director-timeline payload", `latest` setter가 매 갱신마다 atomic JSON write(`self._save()`), 경로는 `serve.py`가 사용자 데이터 디렉터리에 배선.

```
$ sed -n '1,48p' server/web/timeline_library.py
```
→ `class SongTimelineLibrary` — "Director-timeline library — named, versioned saves", "같은 이름이 여러 번 나타날 수 있다 — 이름은 곡이고, 항목은 버전이다", `PinStore`/`SongTimelineStore`와 같은 atomic temp+replace 영속화 패턴.

**결론**: 세 메커니즘(`SongTimelineStore`/`TimelineDraftHistory`/`SongTimelineLibrary`) 모두 실재하고, 셋 다 "곡 타임라인"을 다루지만 **역할×마디 격자 필드는 셋 중 아무 데도 없다.** `TimelineDraftHistory.record`가 **전체 사전**을 깊은 사본으로 쌓는다는 사실이, 격자를 `timeline` 사전의 새 키로 심으면 되돌리기를 코드 추가 없이 재사용할 수 있다는 구체적 권고의 근거다.

**교정**: `spec.md` REQ-LDBEAT-006을 저장소 실체 인용으로 재작성, §5에 0' 항목(M2에서 확정할 열린 결정)으로 추가. `plan.md` §A 입력·§B 위험 8(신설)·M2·§D 제약을 동일하게 교정.

### 부가 — `approval_vs_sent.py`는 리포트 스크립트, 앱 코드 아님

재확인: `.moai/reports/t512/approval_vs_sent.py`는 `.moai/reports/`(gitignore 대상 로컬 아티팩트) 아래에 있다. `spec.md` REQ-LDBEAT-011·`plan.md` M4·`acceptance.md` AC-LDBEAT-006/DoD에 "run-phase가 그 로직을(또는 바이트 동일 포팅을) 앱 참조 가능 경로로 승격해야 한다"는 요구를 추가했다 — 로직 재작성은 금지하되, 파일 위치의 "앱 코드 자격"은 자동으로 생기지 않는다는 것을 명시.

## 5. 감독에게 열린 질문 (D1 교정 이후 — 결정이 필요한 항목 2개 + 참고용 2개)

1. **[결정 필요] 박자 격자의 콘솔 송신에 새 앱측 에미터를 신설할 것인가** (spec.md §5 항목 0, REQ-LDBEAT-013). 이 plan-phase의 권고는 "예, t520이 증명한 커맨드 모양을 포팅"이지만 권고일 뿐이다 — Implementation Kickoff Approval 라운드에서 감독에게 명시적으로 제시하고 확인받아야 한다.
2. **[M2에서 확정] 박자 격자 데이터를 어디에 저장할 것인가** (spec.md §5 항목 0', REQ-LDBEAT-006). 권고는 "기존 `timeline` 사전에 새 키로 임베드"이지만, 격자가 커지면(26~82마디 전체 + 여러 곡·버전) 독립 저장소가 필요할 수 있다.
3. 배치 규칙서(`reports/effect-arrangement-rules-20261007.md`)는 카드 t523이 별도 PR로 저장소에 싣는다고 적혀 있다 — 이 SPEC의 run-phase 착수 시점에 t523이 아직 머지되지 않았다면, 절대경로로 직접 읽거나 머지를 기다릴지는 리드/manager-develop의 판단이다(plan.md §B 위험 7에 양쪽 경로를 적어 두었다).
4. 격자 블록을 `RunbookMode.tsx`의 다섯 블록 중 정확히 어디에 끼울지(`CueSheetTimeline`과 `SongTimeline` 사이 vs 별도 하위 패널)는 M2 설계 단계에서 감독과 구체 와이어프레임으로 확인하는 것이 낫다 — 이 plan-phase는 "다섯 블록 순서는 보존"만 REQ로 못박았다(REQ-LDBEAT-004).

## 6. 안 잰 것(이 plan-phase가 측정하지 않은 것)

- 배치 규칙서의 §3 LOVE ATTACK 전체 배치(26마디~82마디)를 격자 데이터 모델이 어떻게 담을지 — 이 plan-phase는 §4(0~25마디, 앱이 처음 보여줄 범위)만 REQ-LDBEAT-005로 못박았고, 26마디 이후 확장은 M2 설계 범위로 열어 두었다(별도 REQ 없음).
- M1 프로브 4항목의 실제 실기 결과 — 이 plan-phase는 프로브의 **설계**(무엇을 가르는가, 어떤 절차를 따르는가)만 REQ-LDBEAT-001~003으로 정했고, 실제 프로브 실행은 run-phase M1의 일이다.
- `ui/src/protocol.ts`의 `SongTimelineView`/`CueExecutorEntry` 타입이 박자 격자 데이터를 어떤 필드로 받을지 — SPEC 범위 규칙(§ SPEC Scope Boundaries, "함수명·클래스 구조·API 스키마는 WHAT/WHY가 아니라 HOW")에 따라 이 plan-phase는 구체 타입 설계를 적지 않았다. run-phase(M2)의 몫이다.
- 배치 규칙서 §5 "벌스 무빙 미정" 항목의 실제 UI 편집 흐름(어떤 화면에서 어떻게 바꾸는지) — REQ-LDBEAT-006이 모델(곡별 기본값+편집 가능)만 못박았고, 구체 UX는 M2 설계 범위다.
- **새 서버측 편집 연산(`apply_beat_grid_edit`)·새 앱측 에미터·승인=송신 로직의 승격 위치의 구체 모듈 경로** — SPEC 범위 규칙상 이 plan-phase는 "어디에 둘지"를 못박지 않았다(HOW는 run-phase). `cue_sheet_edit.py`와 "나란히" 둔다는 것만 REQ-007/008에 명시했다.
- `TimelineDraftHistory`가 다루는 `timeline` 사전에 `beat_grid` 키를 심었을 때 `DRAFT_HISTORY_LIMIT`(20걸음) 상한이 격자 편집 빈도에 충분한지 — 이 plan-phase는 그 상수를 읽었을 뿐 격자 편집 빈도를 추정하지 않았다.
