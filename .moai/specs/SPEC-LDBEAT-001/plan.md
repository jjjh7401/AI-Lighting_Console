# SPEC-LDBEAT-001 — 구현 계획

## §A 맥락

- **입력**: `reports/effect-arrangement-rules-20261007.md`(규칙 9개·역할별 시퀀스 6개·LOVE ATTACK 전체 배치 §3·0~25마디 격자 §4·감독 결정 §5·안 잰 것 §6 — 주 체크아웃에만 있고 아직 추적되지 않음, 카드 t523이 PR로 싣는다. 이 plan-phase는 그 경로를 그대로 참조만 하고 이 워크트리로 복사하지 않는다) · `ui/src/components/RunbookMode.tsx`(280행, 기존 5블록) · `server/design/cue_sheet_edit.py`(809행, 큐 레벨 파서 `parse_cue_sheet_edit_request:264`(큐 앵커 `_CUE_ANCHOR:227`, 칸 화이트리스트 `EDITABLE_FIELD_LABELS:38-55`)/적용기 `apply_cue_sheet_edit:665`/그룹 스코프 `_GROUP_SCOPE:187`·`_resolve_group_scope:493` — 마디 구간·역할 어휘는 **없음**, D2 재확인) · `server/web/session.py:8467`(`_cue_sheet_draft_edit`, 큐 레벨 편집 요청의 서버 진입점)·`:8498`(거절 사유 예외 패턴)·`:3486`(`SongTimelineStore`)·`:3831,8505`(`TimelineDraftHistory`, 전체-사전 되돌리기 스냅샷) · `server/web/timeline_library.py:48`(`SongTimelineLibrary`, 이름=곡·항목=버전 저장소) · `.moai/specs/SPEC-LDDESIGN-001/spec.md` §3.15(M7, REQ-LDDESIGN-087~095 — 로컬 변형 금지·단일 진실 경로 선례) · `server/director/emit.py:51`(`PLAYBACK_MODES`, 장벽 A) · `.moai/reports/t512/approval_vs_sent.py`(승인=송신 비교 **로직**, AC-LDRHYTHM-012가 쓰는 것 — 리포트 스크립트, 앱 코드 아님) · `.moai/reports/t516/verdict.md:104,463`·`.moai/reports/t519/verdict.md`·`origin/WT-m2-batch1:.moai/reports/t520/verdict.md:92-94,183-186`(실기 사실 — 타임코드 트랙·이벤트가 **커맨드로** 만들어진다는 증거, §20-4 프로브 1~4 제안).
- **전제 SPEC**: `SPEC-LDRHYTHM-001`(status: in-progress — M1 감독 통과, M2 손 시연 두 번째 판은 감독 결정으로 접힘, 이 SPEC이 그 M2/M3의 "다음 단계"를 승계), `SPEC-LDDESIGN-001`(completed — M7 PLAN CUE 수정요청 생성기의 REQ-092 패턴을 재사용), `SPEC-LDRENDER-001`(implemented).
- **범위**: 런북 모드(`RunbookMode.tsx`)에 박자 격자 블록 추가 + 새 서버측 편집 연산(기존 큐시트 편집기의 검증 관행 재사용, 로직은 새로 작성) + 승인=송신 비교 로직 재사용(앱 경로로 승격) + 콘솔 확인 프로브(M1) + 장벽 A(타임코드 신규 에미터 — 감독 확인 조건부)·장벽 B(스피드 마스터 BPM 자동 설정)의 범위 경계 결정. 코파일럿 메인 화면·다른 곡의 배치 규칙서 작성·circle/발리후 실기 구현·BPM 자동 설정·오디오 분석 기반 실시간 타임코드 생성은 범위 밖(spec.md §4).
- **진입 조건**: 이 plan-phase 종료 후 Implementation Kickoff Approval(감독 착수 승인) — run-phase는 그 승인 뒤에만 시작한다. 그 승인 라운드에서 **spec.md §5 항목 0(장벽 A 권고 — 새 앱측 에미터)을 감독에게 명시적으로 제시하고 확인받는다** — 이것은 일반 착수 승인과 별도의 결정이다. run-phase 진입 후에도 REQ-LDBEAT-001의 내부 게이트(M1 프로브 각 항목의 PASS/FAIL)는 M4(콘솔 송신 경로) 착수 여부를 독립적으로 가른다.

## §B 알려진 위험 (manager-develop 착수 전 필독)

1. **"run-phase 진입 승인"과 "M1 프로브 게이트 통과"는 서로 다른 승인이다.** REQ-LDBEAT-001은 M1 프로브로 확인되지 않은 항목에 의존하는 콘솔 송신을 금지한다 — run-phase가 착수되더라도 M4(송신 와이어링)는 그 항목들이 PASS로 기록될 때까지 미착수 상태로 둔다. 둘을 혼동해 run-phase 착수 승인만으로 미확인 항목에 의존한 송신 코드를 쓰기 시작하면 REQ-LDBEAT-001 위반이다.
2. **격자는 `CueSheetTimeline`을 대체하지 않는다.** `CueSheetTimeline`은 큐 번호 단위(한 큐 = 한 행), 박자 격자는 마디 단위(한 역할 트랙이 여러 큐·여러 타임코드 이벤트에 걸친다)다. 두 뷰를 하나로 합치려 하면 REQ-LDBEAT-004가 보존하려는 기존 5블록 순서가 깨진다.
3. **"앱 재생 계약이 타임코드를 거절한다" ≠ "타임코드는 손으로만 만든다" — 이 둘을 혼동한 것이 D1 결함이었다.** `server/director/emit.py:51`은 앱의 `PLAYBACK_MODES`(큐 재생 트리거)를 제한하는 것뿐이다. 콘솔 쪽 타임코드 트랙·이벤트는 **커맨드로** 만들어진다는 것이 t516(`Assign Sequence … At Timecode 20.1.2`, `.moai/reports/t516/verdict.md:104`)과 t520(`Store Sequence`/`Store Timecode`/`Assign Sequence`를 리허설 게이트 집계로 승인=송신 뒤 보냄, `origin/WT-m2-batch1:.moai/reports/t520/verdict.md:186`)으로 실기 증명됐다 — 사람이 GUI를 손으로 조작하는 것이 아니다. 그래서 **장벽 A는 "앱 계약이 거절하니 끝"이 아니라 "앱이 그 증명된 메커니즘을 아직 안 쓴다"는 미해결 결정**이다(spec.md §5 항목 0). M4가 그 결정(감독 확인 + 조건부 새 에미터)을 다룬다.
4. **G9(스피드 마스터 BPM 자동 설정) 미확인은 이 SPEC의 몫이 아니다.** `SPEC-LDRHYTHM-001` REQ-LDRHYTHM-009가 이미 미확인으로 플래그했고, M4+ 선행 조건이다. 이 SPEC은 그 미확인 상태를 UI에 정직하게 반영하는 것(REQ-LDBEAT-014)만 한다 — G9을 이 SPEC에서 풀려고 하지 않는다.
5. **새 서버측 편집 연산을 "어차피 기존 파서가 다 한다"고 생각하고 설계를 생략하지 마라(D2).** `parse_cue_sheet_edit_request`는 큐 레벨 어휘(`_CUE_ANCHOR:227`, `EDITABLE_FIELD_LABELS:38-55`)만 갖고 마디 구간·역할·모양 어휘가 없다 — 이 SPEC은 그 파서의 **검증 관행**(부분 적용 금지, 단일-원인 거절 사유, 화이트리스트 패턴)만 재사용하고 **연산 자체는 새로 설계**해야 한다(REQ-LDBEAT-007/008/009, M3). "원칙 재사용 = 코드 재사용"으로 오독하면 M3가 존재 자체가 빠진 채 M2에서 M4로 건너뛰는 사고가 난다.
6. **승인=송신 비교 로직은 이미 있다 — 새로 만들지 않는다. 그러나 그 파일 자체는 앱 코드가 아니다.** `.moai/reports/t512/approval_vs_sent.py`는 t516/t519/t520이 반복 검증한 **로직**이지만 `.moai/reports/`(gitignore 대상 로컬 아티팩트)에 있는 리포트 스크립트다 — M4가 그 로직을(또는 바이트 동일 포팅을) 앱이 import 가능한 경로로 승격해야 한다(REQ-LDBEAT-011). 로직을 재사용하면서 파일 위치의 "앱 코드 자격"까지 저절로 생긴다고 가정하면 run-phase가 리포트 디렉터리를 import하는 사고가 난다.
7. **배치 규칙서(`reports/effect-arrangement-rules-20261007.md`)는 이 워크트리에 없다.** 주 체크아웃(`AI-Lighting_Console/reports/`)에만 있는 추적되지 않은 파일이고, 카드 t523이 별도 PR로 싣는다. run-phase 착수 시점에 그 경로가 아직 main에 없다면, 절대경로로 직접 읽거나(이 plan-phase가 한 방식) t523의 머지를 기다린다 — 복사해서 이 SPEC의 디렉터리에 두지 않는다(중복 소스가 생기면 어느 쪽이 정본인지 헷갈린다).
8. **"곡별 기본값이 저장된다"고만 적고 저장소를 정하지 않으면 M2가 허공에 뜬다(D3).** 오늘 이 저장소는 `SongTimelineStore`(`session.py:3486`, 프로세스-전역 "현재" 하나)·`TimelineDraftHistory`(`session.py:3831`, `:8505`에서 **전체 타임라인 사전**을 깊은 사본으로 쌓는 generic 되돌리기)·`SongTimelineLibrary`(`timeline_library.py:48`, 이름=곡·항목=버전)의 세 메커니즘을 갖지만, 역할×마디 격자 필드는 셋 중 아무 데도 없다. M2는 "기존 `timeline` 사전에 `beat_grid` 키를 심어 세 메커니즘을 코드 추가 없이 재사용"을 권고 기본값으로 삼지만, 이것이 **결정이 아니라 권고**라는 것을 감독과 재확인해야 한다(spec.md §5 항목 0').

## §C 사전 점검 (M1 착수 직전)

```bash
git branch --show-current
git rev-parse HEAD
# 배치 규칙서 원문 확인(주 체크아웃, 이 워크트리 밖)
ls -l "/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/reports/effect-arrangement-rules-20261007.md" 2>/dev/null \
  || echo "주 체크아웃에 없음 — t523 머지 확인 필요"
# 기존 큐 레벨 편집 경로 재확인(마디·역할 어휘가 여전히 없는지 — D2 전제 재확인)
grep -n "^def parse_cue_sheet_edit_request\|^def apply_cue_sheet_edit\|^_GROUP_SCOPE\|^def _resolve_group_scope\|^_CUE_ANCHOR" server/design/cue_sheet_edit.py
grep -n "_cue_sheet_draft_edit" server/web/session.py
# 곡 타임라인 저장소 3종 재확인(D3 — 역할×마디 필드가 여전히 없는지)
grep -n "class SongTimelineStore" server/web/session.py
grep -n "class TimelineDraftHistory" server/web/timeline_draft.py
grep -n "class SongTimelineLibrary" server/web/timeline_library.py
grep -n "_draft_history.record" server/web/session.py
# 앱 재생 계약 재확인(장벽 A — 바뀌지 않아야 함)
grep -n "PLAYBACK_MODES" server/director/emit.py
# 콘솔 쪽 타임코드가 커맨드로 만들어진다는 증거 재확인(D1)
grep -n "Assign Sequence\|Store Timecode" .moai/reports/t516/verdict.md
# 승인=송신 비교 로직 존재 확인(앱 경로 승격 전 — 리포트 스크립트 위치임을 재확인)
ls -l .moai/reports/t512/approval_vs_sent.py
# RunbookMode 기존 5블록 순서 재확인
grep -n "ConceptPanel\|CueSheetTimeline\|SongTimeline\|RunbookGateBar" ui/src/components/RunbookMode.tsx
```

## §D 제약 (위반 금지)

- **PRESERVE**: `ui/src/components/CueSheetTimeline.tsx`·`ui/src/components/SongTimeline.tsx`·`ui/src/components/ConceptPanel.tsx`(이 SPEC이 수정하지 않는 기존 블록) · `App.tsx`의 메인 화면 분기(런북 모드가 거짓일 때 렌더되는 부분) · `server/design/cue_sheet_edit.py`의 파서·검증 규칙 본문(값 범위·거절 사유 — 격자 전용 완화나 마디 어휘를 그 파일에 끼워 넣지 않는다, D2) · `server/director/emit.py`의 `PLAYBACK_MODES`(기존 큐시트 재생 경로는 바뀌지 않는다, REQ-LDBEAT-013 — 바뀌는 것은 "새 에미터가 추가되는가"이지 `PLAYBACK_MODES` 자체가 아니다).
- 박자 격자의 어떤 편집도 서버 페이로드를 UI가 직접 구성해 새 편집 연산을 거치지 않고 보내는 것을 금지한다(REQ-LDBEAT-008) — 매 편집 PR에서 `grep -rn "changes\s*=\s*{" ui/src` 류의 자체 점검으로 로컬 구성이 없음을 확인한다.
- M1 프로브의 콘솔 쓰기는 t516/t519/t520과 같은 절차(가짜 콘솔 리허설 → 실기 읽기 → 실기 전부-거절 → 감독 승인 → 실기 실행)를 따른다 — 생략하거나 축약하지 않는다(REQ-LDBEAT-002).
- M1의 각 프로브는 §6의 네 항목(타임코드≥3 트랙 / 단일 그룹 선택 페이저 저장 / 같은 그룹 다른 속성 겹침 / circle·발리후) 중 **정확히 하나**를 가르도록 설계한다 — 여러 항목을 한 번에 섞어 쓰면 결과가 어느 항목에 대한 답인지 불분명해진다(t520 §20-3이 겪은 "선택 다섯을 섞어 원인이 불분명해진" 실수의 반복 금지).
- M4(콘솔 송신 경로)는 REQ-LDBEAT-003의 기록(`progress.md`의 항목별 PASS/FAIL)이 없는 상태에서 착수하지 않는다. **또한 REQ-LDBEAT-013의 새 에미터 부분은 Implementation Kickoff Approval 라운드에서 감독이 명시적으로 확인하기 전에는 착수하지 않는다**(spec.md §5 항목 0) — M1 PASS와 감독 확인은 서로 다른 두 선행 조건이다.
- 곡별 기본값(REQ-LDBEAT-006)을 전역 상수로 하드코딩하지 않는다 — LOVE ATTACK 외 곡에서 그 값이 암묵적으로 적용되는 경로를 만들지 않는다(AC-LDBEAT-007이 이를 검사한다).
- 격자 데이터를 `SongTimelineStore`/`TimelineDraftHistory`가 다루는 `timeline` 사전 밖의 별도 전역 변수나 파일로 두지 않는다(REQ-LDBEAT-006의 임베드 권고를 M2가 실제로 채택하는 한) — 채택하지 않기로 결정한 경우는 그 결정과 대안 저장소를 `progress.md`에 기록한다.

## §E 마일스톤 (결정 번복 비용 순 — 단, M1은 "작은 프로브로 콘솔 송신을 게이트한다"는 감독 지시에 따라 예외적으로 먼저 둔다)

> **순서 예외 근거**: 통상 원칙(가장 되돌리기 비싼 UX·데이터 모델 결정을 먼저)과 달리, M1은 측정 작업(코드 0, 콘솔 읽기·리허설·감독 승인 뒤 소량 쓰기)이라 "결정 번복"의 대상이 아니다 — 무엇을 확인하느냐가 아니라 확인됐는지 여부만 가른다. M1의 결과는 M2(UX·데이터 모델)의 설계를 좌우하지 않는다(격자의 모양과 편집 UX는 콘솔 확인 여부와 독립적으로 설계 가능하다) — 다만 M4(콘솔 송신 와이어링)는 M1의 PASS 항목에만 의존한다. 그래서 M1을 먼저 두어도 "결정이 가장 쉽게 바뀌는 작업을 나중으로 미루는" 효과는 생기지 않는다.

### M1 — 콘솔 확인 프로브 (REQ-LDBEAT-001~003)

배치 규칙서 §6의 네 미확인 항목을 가르는 최소 프로브. 코드 diff 0줄 — 콘솔 접촉만.

- 프로브 설계(t520 §20-4 제안 채택, 네 항목을 각각 가르는 최소 단위로):
  1. 타임코드 하나에 트랙 3개 이상 — `Assign Sequence … At Timecode N.1.3`이 NO 3 트랙을 만드는지 되읽기(t516은 2개까지만 측정).
  2. 단일 그룹 선택 페이저 큐 저장 — `Group N ; Dimmer 30` → `Step 2` → `Dimmer 60` + Phase/Measure/SpeedMaster를 한 그룹 선택으로 저장했을 때 큐 Part 크기가 정적 큐보다 커지는지(기계) + 감독 눈(깜박임).
  3. 같은 그룹의 다른 속성을 두 시퀀스가 잡을 때 섞이는지 — 예: SCENE이 MOVER 디머, MOVER MOVE가 MOVER Pan/Tilt를 같은 그룹에 따로 저장했을 때 감독 눈으로 혼선 여부 확인.
  4. circle·발리후·위상 펼침 모양 — `position_fx.py:16-24`의 base effect(circle/ballyhoo)를 실제로 저장·재생해 감독이 눈으로 확인.
- 각 프로브는 가짜 콘솔 리허설 → 승인=송신 비교(PASS 확인) → 실기 전부-거절 → 감독 승인 → 실기 실행의 순서를 따른다(REQ-LDBEAT-002).
- 결과를 `progress.md`에 항목별 PASS/FAIL/미실행으로 기록한다(REQ-LDBEAT-003).
- 산출물: 프로브 스크립트·승인 파일·판정 기록(`.moai/reports/SPEC-LDBEAT-001-m1-probes/` 또는 run-phase가 정하는 경로) — 서버/앱 코드는 수정하지 않는다.

### M2 — 박자 격자 UX·데이터 모델 + 저장소 결정 (REQ-LDBEAT-004~006)

가장 되돌리기 비싼 축 — 감독이 격자의 모양·범위·기본값 구조를 통째로 고칠 수 있다.

- 역할별 트랙(SCENE/BACK PULSE/SIDE CHASE/MOVER-U MOVE/MOVER-D MOVE/ACCENT) × 4마디 행(0~25마디, REQ-LDBEAT-005)의 읽기 전용 렌더부터 설계한다 — 편집 UX(M3)는 이 데이터 모델이 안정된 뒤에 얹는다.
- **저장소 결정(열린 결정 0', spec.md §5)**: 권고 기본값은 "기존 `timeline` 사전에 `beat_grid` 키로 임베드"다(REQ-LDBEAT-006) — 이러면 `TimelineDraftHistory`의 전체-사전 되돌리기(`session.py:8505`)가 코드 추가 없이 격자 되돌리기도 덮고, `SongTimelineStore`의 atomic JSON write(`session.py:3486`)가 영속성을, `SongTimelineLibrary`(`timeline_library.py:48`)가 곡별 명명 버전 저장을 그대로 제공한다. 이 권고를 채택할지, 또는 격자 전용 독립 저장소를 신설할지 이 마일스톤에서 확정하고 `progress.md`에 결정과 근거를 기록한다.
- 곡별 기본값(REQ-LDBEAT-006)을 설계한다 — LOVE ATTACK의 기본값은 배치 규칙서 §2~§4에서 가져오고, 다른 곡은 빈 상태(또는 "이 곡의 기본값 없음" 안내)로 둔다.
- `RunbookMode.tsx`의 기존 5블록 순서 안에서 격자 블록의 삽입 위치를 정한다(예: `CueSheetTimeline`과 `SongTimeline` 사이, 또는 둘 중 하나의 하위 패널) — 코파일럿 메인 화면은 손대지 않는다(REQ-LDBEAT-004).

### M3 — 새 서버측 그리드 편집 연산 (REQ-LDBEAT-007~009)

되돌리기 비용은 M2보다 낮다(데이터 모델은 고정, 입력 경로만 배선) — 그러나 **이 마일스톤 자신을 "M2 다음은 바로 송신 와이어링"으로 건너뛰지 않는 것**이 핵심이다(D2가 바로 이 건너뛰기에서 나왔다).

- 격자 칸의 수정 요청을 문장으로 변환하는 UI를 만들고, 그 문장을 **새** 서버측 편집 연산(가칭 `apply_beat_grid_edit`, `cue_sheet_edit.py`와 나란히)으로 보낸다 — UI는 서버 페이로드를 직접 만들지 않는다(REQ-LDBEAT-007/008).
- 새 연산 안에 닫힌 화이트리스트를 선언한다 — 역할 6종, 모양 어휘(§6 미확인 모양 포함 + "⚠ 미확인" 플래그), 속도·축 값 범위. 거절 사유는 `cue_sheet_edit.py:665`/`session.py:8498`과 같은 "한 가지 원인만 지목" 패턴을 따른다(REQ-LDBEAT-008).
- 특정 역할 그룹에만 적용되는 편집은 기존 그룹 스코프 검증 관행(`_GROUP_SCOPE`/`_resolve_group_scope`)과 같은 모양으로 새 연산 안에 구현한다(REQ-LDBEAT-009) — 역할→그룹 매핑은 새로 선언하되, 매핑 뒤 로직은 본뜬다.
- M1에서 미확인으로 남은 항목(예: 단일 그룹 선택 페이저 저장이 FAIL)에 의존하는 편집 기능은 비활성 상태로 둔다.

### M4 — 콘솔 송신 경로: 장벽 A 확인 + 승인=송신 승격 + (조건부) 새 에미터 (REQ-LDBEAT-011~013)

되돌리기 비용은 낮다(이미 증명된 메커니즘을 연결하는 일) — 그러나 **두 개의 독립 선행 조건**이 걸려 있어 어느 하나라도 없으면 착수하지 않는다: (가) REQ-LDBEAT-001의 M1 PASS 게이트, (나) REQ-LDBEAT-013의 감독 확인(spec.md §5 항목 0, Implementation Kickoff Approval 라운드에서 받는다).

- `progress.md`의 M1 기록을 읽어, PASS로 확정된 항목에만 의존하는 송신 경로를 연다(REQ-LDBEAT-003).
- 승인=송신 비교: `.moai/reports/t512/approval_vs_sent.py`의 로직을 그대로 가져와 앱이 참조 가능한 경로(예: `server/design/` 또는 공유 유틸 모듈)로 **승격**한다 — 리포트 디렉터리를 그대로 import하지 않는다(REQ-LDBEAT-011).
- 구간/묶음 단위 커맨드 파일 1개를 통째로 1회 감독 승인받는 절차(REQ-LDBEAT-012, `SPEC-LDRHYTHM-001` REQ-LDRHYTHM-001과 동일)를 격자 전송에도 그대로 적용한다.
- **감독이 새 에미터를 확인한 경우에만**: 박자 격자 전용 새 앱측 에미터(가칭)를 신설해 t520이 증명한 커맨드 모양(`Store Sequence`/`Store Timecode`/`Assign … At Timecode`/`Go Timecode`/`Off`)을 포팅한다(REQ-LDBEAT-013) — 기존 `emit.py`의 `PLAYBACK_MODES`와 `CueSheetTimeline` 경로는 그대로 둔다. 감독이 다른 방향(타임코드 없이 근사, 또는 M4 전체 보류)을 선택한 경우, 이 하위 작업은 생략하고 `progress.md`에 그 결정을 기록한다.

### M5 — 미확인 어휘 UI 표시 (REQ-LDBEAT-010)

M2~M4와 독립적으로 추가 가능한 표시 레이어 — 되돌리기 비용이 낮다.

- circle·발리후·위상 펼침 모양이 격자 칸에 제안·선택 가능하게 노출될 때 "⚠ 실기 미확인" 배지를 단다.
- M1에서 그 항목이 PASS로 확정되기 전에는 곡별 기본값으로 제공하지 않는다(REQ-LDBEAT-010) — 명시적 선택만 허용.

### M6 — 장벽 B(G9) 범위 경계 문서화 (REQ-LDBEAT-014)

코드가 아니라 문구·주석·UI 안내 수준의 작업 — 되돌리기 비용이 가장 낮다. (장벽 A의 문서화·결정은 M4로 이동했다 — 장벽 A는 더 이상 "문서화만 하면 끝"이 아니라 결정+조건부 구현이 필요하기 때문이다, D1 정정.)

- 스피드 마스터 BPM 설정 UI에 "사람이 콘솔에서 직접 설정" 안내를 단다(REQ-LDBEAT-014) — 자동 설정 기능으로 표시하지 않는다.

## §F 안티패턴

- **격자를 편한 대로 로컬 데이터 구조로 직접 콘솔 커맨드에 매핑하지 마라** — REQ-LDBEAT-007/008. 문장 → 새 서버측 편집 연산 → 서버 경로를 거쳐야 한다.
- **"기존 파서가 이미 격자를 커버한다"고 가정하고 M3을 생략하지 마라(D2)** — REQ-LDBEAT-007. `parse_cue_sheet_edit_request`에는 마디·역할 어휘가 없다. 재사용되는 것은 원칙과 검증 관행이고, 연산 자체는 새로 만든다.
- **M1 프로브를 "어차피 다 될 것"이라 가정하고 M4의 송신 와이어링 부분을 먼저 쓰지 마라** — REQ-LDBEAT-001. FAIL이 나오면 그 기능은 비활성으로 남아야 한다.
- **"콘솔이 커맨드로 타임코드를 만들 수 있다"를 "앱의 재생 계약이 해소됐다"로 읽지 마라(D1)** — REQ-LDBEAT-013. 둘은 다른 층이다 — 앱이 그 메커니즘을 쓰려면 새 에미터가 필요하고, 그 신설은 감독 확인 없이 착수하지 않는다.
- **새 승인=송신 비교 로직을 작성하지 마라, 그러나 리포트 스크립트를 그대로 앱에서 import하지도 마라** — REQ-LDBEAT-011. `.moai/reports/t512/approval_vs_sent.py`의 로직을 앱 경로로 승격한다 — 로직 재작성도, 위치 방치도 둘 다 금지.
- **G9(스피드 마스터 BPM 자동 설정)을 이 SPEC에서 풀려고 하지 마라** — REQ-LDBEAT-014. 미확인 상태를 정직하게 보여주는 것까지만 이 SPEC의 일이다.
- **LOVE ATTACK의 배치 규칙서 값을 전역 상수로 박아 다른 곡에도 적용되게 하지 마라** — REQ-LDBEAT-006. 곡별 기본값이지 전곡 강제가 아니다.
- **배치 규칙서 파일을 이 워크트리로 복사해 두 소스를 만들지 마라** — §B 위험 7. 절대경로 참조 또는 t523 머지 대기.
- **격자 데이터를 `timeline` 사전 밖의 별도 변수로 "임시로" 두고 넘어가지 마라** — REQ-LDBEAT-006/§D. M2에서 저장소 결정을 명시적으로 내리고 기록한다.

## §G 교차 참조

- `reports/effect-arrangement-rules-20261007.md`(주 체크아웃, 2026-10-07 작성 — 규칙 9개·역할별 시퀀스 6개·§3 전체 배치·§4 0~25마디 격자·§5 감독 결정·§6 안 잰 것·§7 확정 뒤 순서). 카드 t523이 이 저장소에 추적본을 싣는다.
- `reports/effect-arrangement-research-pro-20261007.md`·`reports/effect-arrangement-research-kpop-20261007.md`(배치 규칙서의 원 조사 자료, 같은 주 체크아웃 경로, 같은 추적 상태).
- `.moai/specs/SPEC-LDRHYTHM-001/spec.md`·`plan.md`(REQ-LDRHYTHM-001·009·012, M1~M3·M4+ 범위 후보 — 이 SPEC이 그 M4+ 중 "런북 모드 구현" 조각을 담당).
- `.moai/specs/SPEC-LDDESIGN-001/spec.md` §3.15(M7, REQ-LDDESIGN-087~095 — 로컬 변형 금지·단일 진실 경로 패턴의 출처).
- `server/design/cue_sheet_edit.py:227,264,665,38-55,187,493` — 큐 레벨 파서·앵커·칸 화이트리스트·적용기·그룹 스코프(원칙·검증 관행 재사용 대상, 연산 자체는 재사용 대상 아님, D2).
- `server/web/session.py:3486,3831,8467,8498,8505` — `SongTimelineStore`·`TimelineDraftHistory`·편집 요청 서버 진입점·거절 사유 패턴·전체-사전 되돌리기 스냅샷(D3 저장소 실체).
- `server/web/timeline_library.py:48` — `SongTimelineLibrary`(D3 저장소 실체).
- `server/director/emit.py:51` — 장벽 A(`PLAYBACK_MODES`, 바뀌지 않는 기존 경로).
- `.moai/reports/t512/approval_vs_sent.py` — 재사용 대상 승인=송신 비교 로직(앱 경로로 승격 필요, 리포트 스크립트 자체는 재사용 대상 아님).
- `.moai/reports/t516/verdict.md:104,463`·`.moai/reports/t519/verdict.md`·`origin/WT-m2-batch1:.moai/reports/t520/verdict.md:92-94,183-186` — 실기 사실 출처(타임코드가 커맨드로 만들어진다는 D1 증거 + §20-4 프로브 1~4 제안).
- `ui/src/components/RunbookMode.tsx`(280행) — 확장 대상 컴포넌트.
