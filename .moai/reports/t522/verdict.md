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

- `spec.md`: REQ-LDBEAT-001~014, **14개**. 6개 그룹(R1 프로브 게이트 3개·R2 UX/데이터 모델 3개·R3 편집 경로 3개·R4 미확인 표시 1개·R5 승인=송신 2개·R6 장벽 경계 2개).
- `acceptance.md`: AC-LDBEAT-001~013, **13개**. Given-When-Then 13건 + 엣지 케이스 3건 + 인간 판단 3건 + DoD 체크 6항목 + 품질 게이트 기준 3항목.
- Tier M 상한(각 16개) 이내 — REQ 14/16, AC 13/16.
- Out of Scope H3 하위헤딩 5개(`### Out of Scope — ...`) 전부 `-` 불릿 포함 — `OutOfScopeRule` 린트 충족.

## 4. 장벽 결정 (A·B)

### 장벽 A — 앱 재생 계약(`PLAYBACK_MODES`)과 콘솔 타임코드는 다른 층

- **증거**: `server/director/emit.py:51` `PLAYBACK_MODES = ("manual_go", "trig_time")` — timecode 모드는 앱의 큐 재생 경계에서 거부된다(이 plan-phase 재확인).
- **반대 증거(콘솔 쪽은 다름)**: `.moai/reports/t516/verdict.md` §4-1 — t506가 이미 콘솔 GUI/명령줄에서 타임코드 이벤트가 실제로 진행되는 것을 실기로 확인했다(Go+ 이벤트 3개가 Seq 9를 1→2→3으로 진행). `SPEC-LDRHYTHM-001` plan.md §B 위험 4가 이 구분("M2 손 시연은 사람이 콘솔 GUI에서 직접 조작, 앱이 timecode 모드로 재생하는 것이 아니다")을 이미 명시했다.
- **결정**: REQ-LDBEAT-013으로, 이 SPEC은 `PLAYBACK_MODES`를 바꾸지 않는다. 박자 격자의 콘솔 송신 경로는 기존 `Store`/`Go`/`Goto` 커맨드만 쓴다. 완전 자동(앱이 마디 경계를 감지해 타임코드 이벤트를 자동 생성·재생)은 `SPEC-LDRHYTHM-001` REQ-LDRHYTHM-012(b)의 M4+ 범위 후보로 남기고, 이 SPEC의 §4 Out of Scope에 명시했다.

### 장벽 B — 스피드 마스터 BPM 자동 설정(G9) 미확인

- **증거**: `SPEC-LDRHYTHM-001` REQ-LDRHYTHM-009 — "`Master 3.n At BPM <값>`을 곡 재생 중 싣는 구체 방법"은 미확인(G9)으로 명시. `.moai/reports/t516/verdict.md` §4-1 — 감독이 손으로 실행기에 걸어 확인했을 뿐(표시 "Speed15 / 112"), 자동 설정 경로는 측정된 적이 없다.
- **결정**: REQ-LDBEAT-014로, 이 SPEC은 G9을 풀지 않는다. UI는 그 값을 "사람이 콘솔에서 직접 설정"으로 안내하고, 자동 설정 기능으로 표시하지 않는다.

## 5. 감독에게 열린 질문 (결정 불필요, 참고만)

1. 배치 규칙서(`reports/effect-arrangement-rules-20261007.md`)는 카드 t523이 별도 PR로 저장소에 싣는다고 적혀 있다 — 이 SPEC의 run-phase 착수 시점에 t523이 아직 머지되지 않았다면, 절대경로로 직접 읽거나 머지를 기다릴지는 리드/manager-develop의 판단이다(plan.md §B 위험 7에 양쪽 경로를 적어 두었다).
2. 격자 블록을 `RunbookMode.tsx`의 다섯 블록 중 정확히 어디에 끼울지(`CueSheetTimeline`과 `SongTimeline` 사이 vs 별도 하위 패널)는 M2(UX/데이터 모델) 설계 단계에서 감독과 구체 와이어프레임으로 확인하는 것이 낫다 — 이 plan-phase는 "다섯 블록 순서는 보존"만 REQ로 못박았다(REQ-LDBEAT-004).

## 6. 안 잰 것(이 plan-phase가 측정하지 않은 것)

- 배치 규칙서의 §3 LOVE ATTACK 전체 배치(26마디~82마디)를 격자 데이터 모델이 어떻게 담을지 — 이 plan-phase는 §4(0~25마디, 앱이 처음 보여줄 범위)만 REQ-LDBEAT-005로 못박았고, 26마디 이후 확장은 M2 설계 범위로 열어 두었다(별도 REQ 없음).
- M1 프로브 4항목의 실제 실기 결과 — 이 plan-phase는 프로브의 **설계**(무엇을 가르는가, 어떤 절차를 따르는가)만 REQ-LDBEAT-001~003으로 정했고, 실제 프로브 실행은 run-phase M1의 일이다.
- `ui/src/protocol.ts`의 `SongTimelineView`/`CueExecutorEntry` 타입이 박자 격자 데이터를 어떤 필드로 받을지 — SPEC 범위 규칙(§ SPEC Scope Boundaries, "함수명·클래스 구조·API 스키마는 WHAT/WHY가 아니라 HOW")에 따라 이 plan-phase는 구체 타입 설계를 적지 않았다. run-phase(M2)의 몫이다.
- 배치 규칙서 §5 "벌스 무빙 미정" 항목의 실제 UI 편집 흐름(어떤 화면에서 어떻게 바꾸는지) — REQ-LDBEAT-006이 모델(곡별 기본값+편집 가능)만 못박았고, 구체 UX는 M2 설계 범위다.
