# SPEC-LDBEAT-001 — 구현 계획

## §A 맥락

- **입력(2026-10-07, 카드 t522)**: `reports/effect-arrangement-rules-20261007.md`(규칙 9개·역할별 시퀀스 6개·LOVE ATTACK 전체 배치 §3·0~25마디 격자 §4·감독 결정 §5·안 잰 것 §6) · `ui/src/components/RunbookMode.tsx`(280행, 기존 5블록) · `server/design/cue_sheet_edit.py`(809행, 큐 레벨 파서 `parse_cue_sheet_edit_request:264`(큐 앵커 `_CUE_ANCHOR:227`, 칸 화이트리스트 `EDITABLE_FIELD_LABELS:38-55`)/적용기 `apply_cue_sheet_edit:665`/그룹 스코프 `_GROUP_SCOPE:187`·`_resolve_group_scope:493` — 마디 구간·역할 어휘는 **없음**, D2 재확인) · `server/web/session.py:8467`(`_cue_sheet_draft_edit`, 큐 레벨 편집 요청의 서버 진입점)·`:8498`(거절 사유 예외 패턴)·`:3486`(`SongTimelineStore`)·`:3831,8505`(`TimelineDraftHistory`, 전체-사전 되돌리기 스냅샷) · `server/web/timeline_library.py:48`(`SongTimelineLibrary`, 이름=곡·항목=버전 저장소) · `.moai/specs/SPEC-LDDESIGN-001/spec.md` §3.15(M7, REQ-LDDESIGN-087~095 — 로컬 변형 금지·단일 진실 경로 선례) · `.moai/reports/t512/approval_vs_sent.py`(승인=송신 비교 **로직**, AC-LDRHYTHM-012가 쓰는 것 — 리포트 스크립트, 앱 코드 아님) · `.moai/reports/t516/verdict.md:104,463`·`.moai/reports/t519/verdict.md`·`origin/WT-m2-batch1:.moai/reports/t520/verdict.md:92-94,183-186`(실기 사실 — 타임코드 트랙·이벤트가 **커맨드로** 만들어진다는 증거, §20-4 프로브 1~4 제안).
- **입력 추가(2026-10-10, 카드 t526)**: `reports/ldbeat-feasibility-roadmap-20261010.md`+`.html`(되는 것·일부만 되는 것·없는 것 7개·안 잰 것 9개·SPEC 진행안·결정 필요 1~5) · `reports/ldbeat-runbook-ui-proposal-20261008.html`(+ `.md`, UI 결정 + 트랙 모양 "정정" 절) · `reports/ldbeat-runbook-mockup-20261008.html`(+ `.md`, 프리셋 아키텍처 + 편집 세 길) · `reports/ldbeat-plan-summary-20261008.md` · `.moai/reports/t525/verdict.md`(읽기 전용 프로브, 콘솔 쓰기 0 — 무대 2D 좌표 실측) · `server/looks/songcue.py:634`(`_timecode_commands` — 타임코드 커맨드 이미 존재, 재확인: `grep -n "^def _timecode_commands" server/looks/songcue.py` → `634`)·`:683`(`_ascii_label` — 영문화 이미 존재, 재확인: `grep -n "^def _ascii_label" server/looks/songcue.py` → `683`) · `server/director/emit.py:51`(`PLAYBACK_MODES`, 재확인: `grep -n "PLAYBACK_MODES" server/director/emit.py` → `51`) · `console/lua/copilot_responder.lua:43`(`max_prop_value = 240`)·`:282`(`json_encode_bounded`)·`:999-1005`(절단 분기) — 모두 이 plan-phase가 Bash로 재확인한 줄 번호.
- **전제 SPEC**: `SPEC-LDRHYTHM-001`(status: in-progress — M1 감독 통과, M2 손 시연 두 번째 판은 감독 결정으로 접힘, 이 SPEC이 그 M2/M3의 "다음 단계"를 승계), `SPEC-LDDESIGN-001`(completed — M7 PLAN CUE 수정요청 생성기의 REQ-092 패턴을 재사용), `SPEC-LDRENDER-001`(implemented). **새 SPEC(아직 미존재, 카드 t526)**: `SPEC-LDBARMAP-001`(마디 분석)·`SPEC-LDARRANGE-001`(자동 배치) — 둘 다 이 SPEC(LDBEAT) 범위 밖(spec.md §4)이며 `.moai/specs/` 아래 디렉터리가 없다.
- **범위**: 런북 모드 안에 콘솔 그룹 트랙 × 마디 격자를 **독립 전체화면 뷰**로 추가(카드 t537, 감독 결정 2026-10-10 「전체 화면 + 속성별 값」 — M2/M2후속이 만든 "기존 5블록 사이의 새 블록" 모양 대신, `App.tsx`의 `runbookMode`가 참인 분기 안에서 전환되는 독립 화면; UI 결정: 한 화면 고정+스크롤, 큐 편집 칸 내부의 "전환" 토글(큐 편집 ↔ 들어오는-전환 편집, 전역 모드 전환이 아님 — plan-audit D7 재검증), 하단 명령창, 우측 편집 칸, 2D 무대 — 콘솔 패치에서 그림, t525) + 격자 칸 데이터의 속성별 구조화(밝기/위치 프리셋/색 프리셋/효과 프리셋/들어올 때, REQ-LDBEAT-006(i-1)~(i-7)·(ii-1)~(ii-5)·(iii), 레거시 `label` 마이그레이션 규칙 포함) + 새 서버측 편집 연산(기존 큐시트 편집기의 검증 관행 재사용, 로직은 새로 작성, 편집 세 길: 직접 고르기/문장/AI 제안→적용) + 프리셋 아키텍처(종류별 풀, 밝기 단일모드, 앱 번호대 덮어쓰기 경계, 영문 전용 이름, LOVE ATTACK 기본값의 "미정" 강제 규칙 REQ-LDBEAT-015(f)) + 승인=송신 비교 로직 재사용(앱 경로로 승격, 쓰기 매번/미리보기 1회) + 콘솔 확인 프로브(M1, 9항목) + M1 판정의 실시간 읽기 배선(REQ-LDBEAT-003(b), 손으로 옮긴 상수 대체) + 응답기 긴 값 나눠 읽기 확장 + 박자 전용 새 앱측 에미터(확정, `songcue.py` 커맨드 모양 재사용) + 장벽 B(스피드 마스터 BPM 자동 설정)의 범위 경계 결정. 코파일럿 **메인** 화면(`runbookMode` 거짓 분기)·다른 곡의 배치 규칙서 작성·circle/발리후 실기 구현·BPM 자동 설정·오디오 분석 기반 실시간 타임코드 생성·마디 분석(LDBARMAP)·자동 배치 생성(LDARRANGE)은 범위 밖(spec.md §4) — `CueSheetTimeline*`·`emit*`·`songcue*`·`cue_sheet_edit*`·`console/lua/**`도 그대로 범위 밖이다(카드 t537이 요구하지 않는 한 손대지 않는다).
- **진입 조건**: 이 plan-phase 종료 후 Implementation Kickoff Approval(감독 착수 승인) — run-phase는 그 승인 뒤에만 시작한다. **확정된 감독 결정 1~5(spec.md § 확정된 감독 결정)는 이미 2026-10-10에 리드를 통해 받았으므로, 이 승인 라운드는 Tier M 통상 착수 승인이다** — 장벽 A(새 에미터)는 더 이상 별도 확인 라운드가 필요 없다(결정②로 해소). run-phase 진입 후에도 REQ-LDBEAT-001의 내부 게이트(M1 프로브 9항목 각각의 PASS/FAIL)는 M4(콘솔 송신 경로) 착수 여부를 독립적으로 가른다.

## §B 알려진 위험 (manager-develop 착수 전 필독)

1. **"run-phase 진입 승인"과 "M1 프로브 게이트 통과"는 서로 다른 승인이다.** REQ-LDBEAT-001은 M1 프로브로 확인되지 않은 항목에 의존하는 콘솔 송신을 금지한다 — run-phase가 착수되더라도 M4(송신 와이어링)는 그 항목들이 PASS로 기록될 때까지 미착수 상태로 둔다. 둘을 혼동해 run-phase 착수 승인만으로 미확인 항목에 의존한 송신 코드를 쓰기 시작하면 REQ-LDBEAT-001 위반이다.
2. **격자는 `CueSheetTimeline`을 대체하지 않는다.** `CueSheetTimeline`은 큐 번호 단위(한 큐 = 한 행), 박자 격자는 마디 단위(한 역할 트랙이 여러 큐·여러 타임코드 이벤트에 걸친다)다. 두 뷰를 하나로 합치려 하면 REQ-LDBEAT-004가 보존하려는 기존 5블록 순서가 깨진다.
3. **[카드 t526 재교정] "앱이 타임코드 커맨드를 전혀 만들지 않는다"는 과장이었다 — 진짜 틈은 둘로 더 좁다.** `server/looks/songcue.py:634` `_timecode_commands`는 이미 `Store Timecode`/`Set Timecode … Property 'Name'`/`Assign Sequence … At Timecode`를 낸다(재확인: `grep -n "^def _timecode_commands" server/looks/songcue.py` → `634`). 진짜 틈은 (가) `server/director/emit.py:51`의 `PLAYBACK_MODES`가 타임코드 재생 트리거를 거부하는 것, (나) songcue가 시퀀스 1개 : 타임코드 1개만 지원해 역할별 시퀀스 여러 개 × 타임코드 트랙 여러 개 구조가 없는 것이다. **장벽 A는 확정된 감독 결정②로 신설이 확정됐다** — spec.md §5 항목 0은 더 이상 열려 있지 않다. M4는 이제 "만들 것인가"가 아니라 "songcue의 커맨드 모양을 재사용해 그 다대다 구조를 어떻게 설계하는가"만 다룬다.
4. **G9(스피드 마스터 BPM 자동 설정) 미확인은 이 SPEC의 몫이 아니다.** `SPEC-LDRHYTHM-001` REQ-LDRHYTHM-009가 이미 미확인으로 플래그했고, M4+ 선행 조건이다. 이 SPEC은 그 미확인 상태를 UI에 정직하게 반영하는 것(REQ-LDBEAT-014)만 한다 — G9을 이 SPEC에서 풀려고 하지 않는다.
5. **새 서버측 편집 연산을 "어차피 기존 파서가 다 한다"고 생각하고 설계를 생략하지 마라(D2).** `parse_cue_sheet_edit_request`는 큐 레벨 어휘(`_CUE_ANCHOR:227`, `EDITABLE_FIELD_LABELS:38-55`)만 갖고 마디 구간·역할·모양 어휘가 없다 — 이 SPEC은 그 파서의 **검증 관행**(부분 적용 금지, 단일-원인 거절 사유, 화이트리스트 패턴)만 재사용하고 **연산 자체는 새로 설계**해야 한다(REQ-LDBEAT-007/008/009, M3). "원칙 재사용 = 코드 재사용"으로 오독하면 M3가 존재 자체가 빠진 채 M2에서 M4로 건너뛰는 사고가 난다.
6. **승인=송신 비교 로직은 이미 있다 — 새로 만들지 않는다. 그러나 그 파일 자체는 앱 코드가 아니다.** `.moai/reports/t512/approval_vs_sent.py`는 t516/t519/t520이 반복 검증한 **로직**이지만 `.moai/reports/`(gitignore 대상 로컬 아티팩트)에 있는 리포트 스크립트다 — M4가 그 로직을(또는 바이트 동일 포팅을) 앱이 import 가능한 경로로 승격해야 한다(REQ-LDBEAT-011). 로직을 재사용하면서 파일 위치의 "앱 코드 자격"까지 저절로 생긴다고 가정하면 run-phase가 리포트 디렉터리를 import하는 사고가 난다.
7. **배치 규칙서(`reports/effect-arrangement-rules-20261007.md`)는 이 워크트리에 없다.** 주 체크아웃(`AI-Lighting_Console/reports/`)에만 있는 추적되지 않은 파일이고, 카드 t523이 별도 PR로 싣는다. run-phase 착수 시점에 그 경로가 아직 main에 없다면, 절대경로로 직접 읽거나(이 plan-phase가 한 방식) t523의 머지를 기다린다 — 복사해서 이 SPEC의 디렉터리에 두지 않는다(중복 소스가 생기면 어느 쪽이 정본인지 헷갈린다).
8. **"곡별 기본값이 저장된다"고만 적고 저장소를 정하지 않으면 M2가 허공에 뜬다(D3).** 오늘 이 저장소는 `SongTimelineStore`(`session.py:3486`, 프로세스-전역 "현재" 하나)·`TimelineDraftHistory`(`session.py:3831`, `:8505`에서 **전체 타임라인 사전**을 깊은 사본으로 쌓는 generic 되돌리기)·`SongTimelineLibrary`(`timeline_library.py:48`, 이름=곡·항목=버전)의 세 메커니즘을 갖지만, 역할×마디 격자 필드는 셋 중 아무 데도 없다. M2는 "기존 `timeline` 사전에 `beat_grid` 키를 심어 세 메커니즘을 코드 추가 없이 재사용"을 권고 기본값으로 삼지만, 이것이 **결정이 아니라 권고**라는 것을 감독과 재확인해야 한다(spec.md §5 항목 0').
9. **[카드 t526] 트랙은 "역할"이 아니라 "콘솔 그룹"이다 — SCENE/BACK PULSE/… 이름을 코드에 박지 마라.** `reports/ldbeat-runbook-ui-proposal-20261008.html`의 "정정" 절이 이전 시안의 여섯 트랙 이름을 "장비와 하는 일을 섞은 임시 이름"으로 자기 철회했다. 트랙 = 콘솔 그룹(줄 하나 = 그룹 하나 = 시퀀스 하나), 층 역할(key/back/side/wash/mover/effect/audience)은 이름표, 펄스·체이스 같은 효과는 큐 안의 내용일 뿐이다. 데이터 모델(M2)에 "SCENE"·"BACK PULSE" 같은 문자열을 트랙 식별자로 하드코딩하면 다른 곡·다른 리그(그룹 구성이 다른)에서 깨진다 — 트랙 식별자는 **콘솔 그룹 번호/이름**이어야 한다(REQ-LDBEAT-004).
10. **[카드 t526] M1은 코드 diff 0줄 원칙에 응답기 lua 확장이라는 예외를 하나 갖는다.** `console/lua/copilot_responder.lua:43`(`max_prop_value = 240`)이 표 값 속성(`SELECTIONDATA` 등)을 그룹당 앞 2대로 자른다(`.moai/reports/t525/verdict.md` §② 실측) — M1은 이 응답기에 offset 나눠 읽기를 추가해야 그룹 소속 전체가 보인다. 이것은 **앱 코드가 아니라 콘솔 쪽 lua 스크립트**이므로, 수정 전후 기존 응답기 verb(`ping`/`state`/`prop`/`props`/`introspect`)의 동작을 깨지 않는지 회귀 확인이 필요하다 — 긴 값 한도를 "올리는" 것이 아니라 "나눠 읽는" 것으로 고쳐야 한다(응답 전체 한도 `max_payload = 1900`에 걸리므로, `.moai/reports/t525/verdict.md` 잔여 위험).
11. **[카드 t526] 프리셋 번호대는 "앱 번호대만 덮어쓴다"는 원칙이고, 정확한 범위는 M2/M3의 실측 대상이다.** 로드맵의 예시 번호(위치 `2.61~2.68`, 색 `4.41~`, 디머 `1.21~1.26`/`1.31~1.33`, All `22.x`)를 결정으로 착각해 그대로 하드코딩하면, 실제 쇼 파일에 이미 그 번호가 쓰이고 있을 경우 "쇼에 원래 있던 프리셋은 절대 덮어쓰지 않는다"는 더 상위 규칙(REQ-LDBEAT-015)을 어기게 된다 — M2/M3 착수 시 반드시 실제 쇼 파일의 기존 프리셋 번호 전부를 조회해 충돌 없는 번호대를 재확정한다.
12. **[신설 — 카드 t537] M2/M2후속(t532/t534)이 만든 "기존 5블록 사이의 블록" 배치는 phase ②의 출발점이 아니라 고칠 대상이다.** `RunbookMode.tsx`에 `<BeatGrid>`를 `CueSheetTimeline`과 `SongTimeline` 사이에 끼워 넣은 현재 구현(`git diff --stat` 확인 가능)은 감독의 새 지시("전체 화면")와 맞지 않는다 — phase ②를 "기존 블록에 살을 붙이는" 작업으로 착각하면 전체화면 독립 뷰 요구(REQ-LDBEAT-004(a)(g))를 못 채운다. `App.tsx`의 `runbookMode` 참 분기 안에 전환 가능한 별도 화면을 만드는 것이 phase ②의 출발점이다.
13. **[신설 — 카드 t537] `BeatGridCue.label`을 지우는 것과 "구조화 필드로 대체하는 것"은 같지 않다.** 레거시 `{bar, label}` 칸을 읽을 때 구조화 필드를 전부 미정으로 두고 `label`을 그대로 보여주는 것(REQ-LDBEAT-006(ii-1))과, `label` 자유 텍스트를 파싱해 구조화 필드를 **추측**하는 것은 다르다(REQ-LDBEAT-006(ii-2)) — 후자는 금지된 "지어낸 값"이다. M3가 label 파싱기를 만들려는 유혹을 받으면 이 항목을 재확인한다.
14. **[신설 — 카드 t537 plan-audit D2] §4의 밝기 퍼센트·마디 페이드 힌트를 "SCENE 열이니까 전사 대상 없음"으로 뭉뚱그려 생략하지 마라.** §4에 숫자가 명시된 밝기 퍼센트·페이드 힌트는 SCENE 열에만 있는 것이 아니다 — BACK PULSE 열의 `킥 1·2·4박 60%/100%`(`:106,109,110`)와 ACCENT 열의 `18마디 1박 BLIND 100% 2박`(`:109`)은 전사 대상 큐(BACK·BLIND 트랙)에 **실제로 존재**한다. M7 (1)이 이 넷을 빠뜨리고 "전부 null"로 단순화하면 REQ-LDBEAT-006(i-5)를 위반한다 — M7 데이터 모양 블록(§E M7 (1))의 전사 기대표를 그대로 옮긴다.

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
# 앱 재생 계약 재확인(장벽 A — PLAYBACK_MODES 자체는 바뀌지 않아야 함, 새 에미터는 별도 모듈)
grep -n "PLAYBACK_MODES" server/director/emit.py
# songcue 가 이미 내는 타임코드 커맨드 모양 재확인(카드 t526 재교정 — M4가 재사용할 대상)
grep -n "^def _timecode_commands\|^def _ascii_label" server/looks/songcue.py
# 콘솔 쪽 타임코드가 커맨드로 만들어진다는 증거 재확인(D1)
grep -n "Assign Sequence\|Store Timecode" .moai/reports/t516/verdict.md
# 응답기 긴 값 절단 지점 재확인(카드 t526 — M1 확장 대상)
grep -n "max_prop_value\|json_encode_bounded" console/lua/copilot_responder.lua
# 승인=송신 비교 로직 존재 확인(앱 경로 승격 전 — 리포트 스크립트 위치임을 재확인)
ls -l .moai/reports/t512/approval_vs_sent.py
# 무대 2D 좌표 프로브 산출물 존재 확인(t525 — M2가 재사용할 대상)
ls -l .moai/reports/t525/verdict.md .moai/reports/t525/probe_spatial.py 2>/dev/null
# RunbookMode 기존 5블록 순서 재확인
grep -n "ConceptPanel\|CueSheetTimeline\|SongTimeline\|RunbookGateBar" ui/src/components/RunbookMode.tsx
```

## §D 제약 (위반 금지)

- **PRESERVE**: `ui/src/components/CueSheetTimeline.tsx`·`ui/src/components/SongTimeline.tsx`·`ui/src/components/ConceptPanel.tsx`(이 SPEC이 수정하지 않는 기존 블록) · `App.tsx`의 **메인** 화면 분기(`runbookMode`가 거짓일 때 렌더되는 부분 — **카드 t537 교정**: `runbookMode`가 참인 분기 안쪽은 더 이상 전면 PRESERVE가 아니다, REQ-LDBEAT-004(a)(g)가 그 안에 전체화면 전환을 추가하는 것을 허용한다; 참 분기 안에서도 기존 5블록 호출부(헤더·`ConceptPanel`·`CueSheetTimeline`·`SongTimeline`·`RunbookGateBar`)의 호출 순서 자체는 그대로 PRESERVE한다) · `server/design/cue_sheet_edit.py`의 파서·검증 규칙 본문(값 범위·거절 사유 — 격자 전용 완화나 마디 어휘를 그 파일에 끼워 넣지 않는다, D2) · `server/director/emit.py`의 `PLAYBACK_MODES`(기존 큐시트 재생 경로는 바뀌지 않는다, REQ-LDBEAT-013 — 바뀌는 것은 "새 에미터 모듈이 추가되는가"이지 `PLAYBACK_MODES` 자체가 아니다) · `server/looks/songcue.py`의 기존 함수 본문(새 에미터는 그 커맨드 **모양**을 재사용하되 별도 모듈에 새로 짠다 — songcue 자체를 1:N으로 고치지 않는다).
- 박자 격자의 어떤 편집도 서버 페이로드를 UI가 직접 구성해 새 편집 연산을 거치지 않고 보내는 것을 금지한다(REQ-LDBEAT-008) — AI 제안 경로의 「적용」 클릭도 예외가 아니다. 매 편집 PR에서 `grep -rn "changes\s*=\s*{" ui/src` 류의 자체 점검으로 로컬 구성이 없음을 확인한다.
- M1 프로브의 콘솔 쓰기는 t516/t519/t520과 같은 절차(가짜 콘솔 리허설 → 실기 읽기 → 실기 전부-거절 → 감독 승인 → 실기 실행)를 따른다 — 생략하거나 축약하지 않는다(REQ-LDBEAT-002). **쓰기는 감독의 명시적 「실행」 신호 뒤에만** 한다 — 미리보기(Goto Cue/Off Sequence) 1회 승인이 쓰기 승인을 대신하지 않는다.
- M1의 각 프로브는 로드맵 §4의 9항목 중 **정확히 하나**를 가르도록 설계한다 — 여러 항목을 한 번에 섞어 쓰면 결과가 어느 항목에 대한 답인지 불분명해진다(t520 §20-3이 겪은 "선택 다섯을 섞어 원인이 불분명해진" 실수의 반복 금지).
- 응답기(`console/lua/copilot_responder.lua`) 확장은 **나눠 읽기**로 구현한다 — `max_prop_value` 상한을 단순히 올리는 것은 `max_payload = 1900`(응답 전체 한도)에 걸려 큰 그룹(예: 86대)을 한 번에 담지 못한다(§D 제약 위반, `.moai/reports/t525/verdict.md` 잔여 위험 참조).
- M4(콘솔 송신 경로)는 REQ-LDBEAT-003의 기록(`progress.md`의 9항목 PASS/FAIL)이 없는 상태에서 착수하지 않는다. 새 에미터(REQ-LDBEAT-013)는 확정된 감독 결정②로 신설이 이미 확정됐으므로 별도 확인 라운드는 필요 없다 — 다만 M1 PASS 게이트(REQ-LDBEAT-001)는 여전히 M4의 실제 착수 여부를 항목별로 가른다.
- 곡별 기본값(REQ-LDBEAT-006)을 전역 상수로 하드코딩하지 않는다 — LOVE ATTACK 외 곡에서 그 값이 암묵적으로 적용되는 경로를 만들지 않는다(AC-LDBEAT-007이 이를 검사한다).
- 격자 데이터를 `SongTimelineStore`/`TimelineDraftHistory`가 다루는 `timeline` 사전 밖의 별도 전역 변수나 파일로 두지 않는다(REQ-LDBEAT-006의 임베드 권고를 M2가 실제로 채택하는 한) — 채택하지 않기로 결정한 경우는 그 결정과 대안 저장소를 `progress.md`에 기록한다.
- 콘솔 그룹 트랙 식별자를 "SCENE"·"BACK PULSE" 같은 역할·효과 혼성 문자열로 하드코딩하지 않는다(§B 위험 9) — 트랙 식별자는 콘솔 그룹 번호/이름이다.
- 프리셋 번호대(REQ-LDBEAT-015)를 로드맵의 예시 번호 그대로 하드코딩하지 않는다(§B 위험 11) — M2/M3가 실제 쇼 파일과 대조해 재확정한다.
- **(카드 t537) LOVE ATTACK 기본값의 큐 레벨 프리셋 번호(밝기/위치/색/효과)를 배치 규칙서·t525류 실측 출처 없이 지어내 채우지 않는다(REQ-LDBEAT-015(f))** — 출처 없는 자리는 `null`(미정)로 남긴다. `reports/ldbeat-runbook-ui-proposal-20261008.html`의 `P` 객체에 적힌 번호(`4.21`·`2.41`·`1.31` 등)는 그 시안 자신이 지어낸 예시일 뿐 배치 규칙서의 출처가 아니므로 그대로 베끼면 이 제약을 어긴다.
- **(카드 t537) M1 9항목 판정 화면을 손으로 옮긴 TS 상수로 영구히 유지하지 않는다(REQ-LDBEAT-003(b))** — `beatGridM1Probes.ts` 같은 고정 상수는 progress.md가 갱신될 때마다 바로 낡는다; phase ②는 그 표를 읽어 오는 살아있는 경로로 교체한다.

## §E 마일스톤 (결정 번복 비용 순 — 단, M1은 "작은 프로브로 콘솔 송신을 게이트한다"는 감독 지시에 따라 예외적으로 먼저 둔다)

> **순서 예외 근거**: 통상 원칙(가장 되돌리기 비싼 UX·데이터 모델 결정을 먼저)과 달리, M1은 측정 작업(코드 0, 콘솔 읽기·리허설·감독 승인 뒤 소량 쓰기)이라 "결정 번복"의 대상이 아니다 — 무엇을 확인하느냐가 아니라 확인됐는지 여부만 가른다. M1의 결과는 M2(UX·데이터 모델)의 설계를 좌우하지 않는다(격자의 모양과 편집 UX는 콘솔 확인 여부와 독립적으로 설계 가능하다) — 다만 M4(콘솔 송신 와이어링)는 M1의 PASS 항목에만 의존한다. 그래서 M1을 먼저 두어도 "결정이 가장 쉽게 바뀌는 작업을 나중으로 미루는" 효과는 생기지 않는다.

### M1 — 콘솔 확인 프로브 + 응답기 긴 값 나눠 읽기 확장 (REQ-LDBEAT-001~003, 카드 t526 확장)

로드맵 §4의 9개 미확인 항목을 가르는 최소 프로브 + 응답기 확장. 코드 diff는 응답기 lua 확장 1건을 제외하면 0줄 — 콘솔 접촉은 쓰기 신호("실행") 뒤에만.

- 프로브 설계(t520 §20-4 제안 채택 + 로드맵 §4 확장, 9항목을 각각 가르는 최소 단위로):
  1. 타임코드 하나에 트랙 3개 이상(최대 6개) — `Assign Sequence … At Timecode N.1.3`이 NO 3 트랙을 만드는지 되읽기(t516은 2개까지만 측정).
  2. Goto 2번 이후 큐·여러 시퀀스 동시 — Goto 마디 미리보기가 두 번째 이후에도 작동하는지.
  3. 프리셋을 고치면 참조하는 큐가 따라 바뀌는지(프리셋 참조 전파).
  4. 효과 프리셋이 스피드마스터 15·Measure를 지니는지(지금까지 고정 속도만 확인됨).
  5. 위치 프리셋 위에 상대값 움직임 효과를 얹을 수 있는지.
  6. 타임코드를 곡 중간부터 재생할 수 있는지.
  7. 큐 하나에 그룹 하나 + Step 2 저장(역할 분리) — t520에서 한 효과만 남은 원인.
  8. 같은 그룹을 두 시퀀스가 나눠 쓰기(밝기/위치 분담) — 섞이는지 감독 눈으로 확인.
  9. circle·발리후·위상 펼침 모양 — `position_fx.py:16-24`의 base effect(circle/ballyhoo)를 실제로 저장·재생해 감독이 눈으로 확인.
- **응답기 확장(코드 diff 1건, 카드 t526)**: `console/lua/copilot_responder.lua`에 표 값 속성(`SELECTIONDATA` 등)의 offset 기반 나눠 읽기를 추가한다(`:43` `max_prop_value`, `:282` `json_encode_bounded`, `:999-1005` 절단 분기 — `.moai/reports/t525/verdict.md` §② 실측). 기존 응답기 verb(`ping`/`state`/`prop`/`props`/`introspect`)의 동작을 회귀시키지 않는지 확인한다. 이 확장이 끝나면 그룹 소속 전체(18개 그룹 전부, t525가 확인한 4개를 넘어)를 읽을 수 있는지 재확인한다.
- 각 프로브는 가짜 콘솔 리허설 → 승인=송신 비교(PASS 확인) → 실기 전부-거절 → 감독 승인 → 실기 실행의 순서를 따른다(REQ-LDBEAT-002). 미리보기(Goto Cue/Off Sequence)는 세션 시작 1회 승인으로 반복하되, 쓰기는 매번 승인받는다(결정⑤).
- 결과를 `progress.md`에 9항목 각각 PASS/FAIL/미실행으로 기록한다(REQ-LDBEAT-003).
- 산출물: 프로브 스크립트·응답기 확장 diff·승인 파일·판정 기록(`.moai/reports/SPEC-LDBEAT-001-m1-probes/` 또는 run-phase가 정하는 경로) — 응답기 lua 외의 서버/앱 코드는 수정하지 않는다.

### M2 — 박자 격자 UX·데이터 모델 + 저장소 결정 + 2D 무대(콘솔 패치 기반) (REQ-LDBEAT-004~006·015)

가장 되돌리기 비싼 축 — 감독이 격자의 모양·범위·기본값 구조를 통째로 고칠 수 있다.

- **콘솔 그룹 트랙** × 4마디 행(0~25마디, REQ-LDBEAT-005)의 읽기 전용 렌더부터 설계한다 — 트랙 식별자는 콘솔 그룹 번호/이름이고, 층 역할(key/back/side/wash/mover/effect/audience)은 이름표로만 붙인다(§B 위험 9, 트랙 모양 교정). 편집 UX(M3)는 이 데이터 모델이 안정된 뒤에 얹는다.
- UI 결정을 반영한다(plan-audit D7 재검증 — 입력 보고서의 실제 줄 번호로 교정): 한 화면 고정 높이 + 좌우 스크롤(`:155`), 전역 "모두 접기/펴기" + 층 역할 폴더 개별 접기/펴기(`:376`), 막대 클릭 시 우측 밝기·위치·색·움직임 편집 칸(`:495-502`), 그 칸 헤더 우측(✕ 옆)의 "전환" 토글 버튼이 큐 편집 뷰 ↔ 들어오는-전환 편집 뷰(페이드·트리거·딜레이·트래킹)를 전환하며 첫 큐에서 비활성(`:495,504,519`) — **"타임라인 ↔ 상세" 전역 모드 전환은 입력 보고서에 존재하지 않는다(D7, 삭제)**, 하단 명령창(`:196-200`).
- **2D 무대는 콘솔 패치에서 그린다**(REQ-LDBEAT-004, t525): `read_spatial_fixtures`/`_spatial_read_budget`(앱이 이미 쓰는 함수)로 장비 좌표·회전을 일괄 `props`로 읽는다. 그룹 소속 칠하기는 M1의 응답기 확장이 끝난 뒤 전체 그룹으로 넓힌다. 무대 앞뒤(Y 방향)는 이름 추정을 유지한다(미확인, §5 항목 5).
- **저장소 결정(열린 결정 0', spec.md §5)**: 권고 기본값은 "기존 `timeline` 사전에 `beat_grid` 키로 임베드"다(REQ-LDBEAT-006) — 이러면 `TimelineDraftHistory`의 전체-사전 되돌리기(`session.py:8505`)가 코드 추가 없이 격자 되돌리기도 덮고, `SongTimelineStore`의 atomic JSON write(`session.py:3486`)가 영속성을, `SongTimelineLibrary`(`timeline_library.py:48`)가 곡별 명명 버전 저장을 그대로 제공한다. 이 권고를 채택할지, 또는 격자 전용 독립 저장소를 신설할지 이 마일스톤에서 확정하고 `progress.md`에 결정과 근거를 기록한다.
- 곡별 기본값(REQ-LDBEAT-006)을 설계한다 — LOVE ATTACK의 기본값은 배치 규칙서 §2~§4에서 가져오고, 다른 곡은 빈 상태(또는 "이 곡의 기본값 없음" 안내)로 둔다.
- **프리셋 아키텍처 번호대 초안(REQ-LDBEAT-015)**: 실제 쇼 파일의 기존 프리셋 번호를 조회해, 로드맵 예시(위치 `2.61~2.68`·색 `4.41~`·디머 `1.21~1.26`/`1.31~1.33`·All `22.x`)와 충돌하지 않는 번호대를 확정하고 `progress.md`에 기록한다(§B 위험 11).
- `RunbookMode.tsx`의 기존 5블록 순서 안에서 격자 블록의 삽입 위치를 정한다(예: `CueSheetTimeline`과 `SongTimeline` 사이, 또는 둘 중 하나의 하위 패널) — 코파일럿 메인 화면은 손대지 않는다(REQ-LDBEAT-004).

### M3 — 새 서버측 그리드 편집 연산 + 편집 세 길 + 프리셋 화이트리스트 (REQ-LDBEAT-007~009·015)

되돌리기 비용은 M2보다 낮다(데이터 모델은 고정, 입력 경로만 배선) — 그러나 **이 마일스톤 자신을 "M2 다음은 바로 송신 와이어링"으로 건너뛰지 않는 것**이 핵심이다(D2가 바로 이 건너뛰기에서 나왔다).

- **편집 세 길**(확정된 감독 결정④, `reports/ldbeat-runbook-mockup-20261008.html` §2)을 구현한다 — ① 직접 고르기(목록 선택, 즉시 반영) ② 문장(정해진 꼴, 규칙으로 즉시 해석) ③ AI 제안(제안 카드 → 감독의 명시적 「적용」 클릭 전에는 초안도 콘솔도 바뀌지 않음). 세 길 모두 **새** 서버측 편집 연산(가칭 `apply_beat_grid_edit`, `cue_sheet_edit.py`와 나란히)으로 수렴한다 — UI는 서버 페이로드를 직접 만들지 않는다(REQ-LDBEAT-007/008).
- 새 연산 안에 닫힌 화이트리스트를 선언한다 — 콘솔 그룹 트랙, 모양 어휘(§6 미확인 모양 포함 + "⚠ 미확인" 플래그), 속도·축 값 범위, **프리셋 풀 번호대(REQ-LDBEAT-015, M2가 확정한 값)**, 밝기 단일모드(값/디머 프리셋/디머 효과 중 하나). 거절 사유는 `cue_sheet_edit.py:665`/`session.py:8498`과 같은 "한 가지 원인만 지목" 패턴을 따른다(REQ-LDBEAT-008).
- 특정 그룹에만 적용되는 편집은 기존 그룹 스코프 검증 관행(`_GROUP_SCOPE`/`_resolve_group_scope`)과 같은 모양으로 새 연산 안에 구현한다(REQ-LDBEAT-009) — 트랙→그룹 매핑은 새로 선언하되, 매핑 뒤 로직은 본뜬다.
- 콘솔에 들어가는 신규 프리셋 이름은 영문·숫자만 생성한다(REQ-LDBEAT-015, `_ascii_label` 패턴 재확인).
- M1에서 미확인으로 남은 항목(예: 같은 그룹 두 시퀀스 분담이 FAIL)에 의존하는 편집 기능은 비활성 상태로 둔다.

### M4 — 콘솔 송신 경로: 새 에미터(확정) + 승인=송신 승격 + 쓰기/미리보기 승인 분리 (REQ-LDBEAT-011~013)

되돌리기 비용은 낮다(이미 증명된 메커니즘을 연결하는 일). 선행 조건은 REQ-LDBEAT-001의 M1 PASS 게이트 **하나뿐**이다 — 새 에미터 신설은 확정된 감독 결정②로 이미 확정됐으므로 더 이상 별도 감독 확인 라운드가 필요 없다(장벽 A 해소, §B 위험 3 재교정).

- `progress.md`의 M1 기록을 읽어, PASS로 확정된 항목에만 의존하는 송신 경로를 연다(REQ-LDBEAT-003).
- 승인=송신 비교: `.moai/reports/t512/approval_vs_sent.py`의 로직을 그대로 가져와 앱이 참조 가능한 경로(예: `server/design/` 또는 공유 유틸 모듈)로 **승격**한다 — 리포트 디렉터리를 그대로 import하지 않는다(REQ-LDBEAT-011). 이 대조는 **쓰기**에만 적용한다 — 미리보기는 콘솔 상태를 바꾸지 않으므로 대조 대상이 없다(결정⑤).
- 구간/묶음 단위 커맨드 파일 1개를 통째로 1회 감독 승인받는 절차(REQ-LDBEAT-012, `SPEC-LDRHYTHM-001` REQ-LDRHYTHM-001과 동일)를 격자 **쓰기** 전송에 적용한다. 미리보기(Goto Cue/Off Sequence)는 세션 시작 1회 승인으로 별도 배선한다.
- **박자 격자 전용 새 앱측 에미터**(가칭)를 신설해 `songcue.py:634` `_timecode_commands`가 이미 증명한 커맨드 모양(`Store Timecode`/`Set Timecode … Property 'Name'`/`Assign Sequence … At Timecode`)을 재사용하고, t520이 증명한 추가 모양(`Store Sequence`/`Go Timecode`/`Off`)을 더해 역할별 시퀀스 여러 개 × 타임코드 트랙 여러 개의 다대다 배선을 새로 설계한다(REQ-LDBEAT-013) — 기존 `emit.py`의 `PLAYBACK_MODES`와 `CueSheetTimeline` 경로는 그대로 둔다. 콘솔 이름은 `_ascii_label` 패턴대로 영문화한다.

### M5 — 미확인 어휘 UI 표시 (REQ-LDBEAT-010)

M2~M4와 독립적으로 추가 가능한 표시 레이어 — 되돌리기 비용이 낮다.

- circle·발리후·위상 펼침 모양이 격자 칸에 제안·선택 가능하게 노출될 때 "⚠ 실기 미확인" 배지를 단다.
- M1에서 그 항목이 PASS로 확정되기 전에는 곡별 기본값으로 제공하지 않는다(REQ-LDBEAT-010) — 명시적 선택만 허용.

### M6 — 장벽 B(G9) 범위 경계 문서화 (REQ-LDBEAT-014)

코드가 아니라 문구·주석·UI 안내 수준의 작업 — 되돌리기 비용이 가장 낮다. (장벽 A의 구현은 M4가 맡는다 — 장벽 A는 확정된 감독 결정②로 신설이 확정됐으므로 더 이상 "문서화만 하면 끝"이 아니라 실제 구현이 필요하기 때문이다, D1/카드 t526 정정.)

- 스피드 마스터 BPM 설정 UI에 "사람이 콘솔에서 직접 설정" 안내를 단다(REQ-LDBEAT-014) — 자동 설정 기능으로 표시하지 않는다.

### M7 — 전체화면 전환 + 칸 데이터 구조화 + M1 실시간 읽기 (REQ-LDBEAT-004(a)(g)·006(i)~(iii)·003(b)·015(f), 카드 t537, phase ② — **아직 미구현, 명세만**)

M2/M2후속(t532/t534)이 이미 머지한 "기존 5블록 사이의 블록" 구현을 감독의 새 지시("전체 화면 + 속성별 값")에 맞춰 다시 짠다. 결정 번복 비용이 큰 것부터 — 데이터 모양(1)을 먼저 고정해야 그 위에 얹는 화면(2)·렌더 규칙(3)·배선(4)이 흔들리지 않고, 기계적 마무리(5)는 맨 뒤에 둔다.

1. **(가장 비쌈) 칸 데이터를 구조화한다(REQ-LDBEAT-006(i-1)~(i-7)·(ii-1)~(ii-5)·(iii), plan-audit D2/D9 교정)**: `server/design/beat_grid.py`의 `BeatGridCue`를 `{bar, label}`에서 아래 모양으로 확장한다 — D2 교정으로 `entry`는 `fade_seconds`가 아니라 `fade_bars`(마디 수)를 쓰고, D9 교정으로 `effect_preset_no`는 위치 효과 풀 고정이 아니라 `effect_kind`로 풀 종류를 구분한다:

   ```
   {bar, brightness: {mode: "value"|"dimmer_preset"|"dimmer_effect"|None, value_percent, preset_no}, position_preset_no, color_preset_no, effect_preset_no, effect_kind: "position"|"color"|"dimmer"|"mixed"|None, entry: {fade_bars, mib_mode}, source_ref, label}
   ```

   `brightness`는 값/디머 프리셋/디머 효과 중 정확히 하나만 쓰는 단일-모드 구분(REQ-LDBEAT-015(c)). `entry.fade_bars`는 마디 수 정수(초 아님) — 기존 `SongTimelineSection.fade_seconds`(`ui/src/protocol.ts:368`)와 다른 단위를 **의도적으로** 쓴다(REQ-LDBEAT-006(i-4); 마디→초 환산은 그 곡 BPM으로 화면 표시 시점에 계산하며 저장하지 않는다). `source_ref`는 그 칸의 값이 비롯된 §4 파일 경로+행 번호(칸당 1개, 문자열 또는 `None`)다. `label`은 레거시 호환 전용 선택 필드로 남긴다. 레거시 칸(구조화 필드 전부 없음) 읽기는 이 필드 전부를 `None`으로 채우고 `label`만 그대로 보여준다 — 파싱·추측 0건(REQ-LDBEAT-006(ii-1)(ii-2)).

   `_love_attack_tracks()`의 기존 30개 큐를 이 모양으로 옮길 때: **(a)** 네 프리셋 **번호** 필드(`brightness`의 디머 프리셋·디머 효과 프리셋 번호, `position_preset_no`, `color_preset_no`, `effect_preset_no`)는 30개 전부 `None`(배치 규칙서 §4에 번호가 없다 — §5 항목 4/§B 위험 11과 같은 "아직 실측 안 됨" 분류, REQ-LDBEAT-015(f)). **(b)** `brightness.value_percent`·`entry.fade_bars`는 §4(`reports/effect-arrangement-rules-20261007.md:98-115`)에 숫자로 적힌 **네 자리만** 전사한다(REQ-LDBEAT-006(i-5)) — BACK(그룹4)@7마디=60%(`:106`)·@18마디=100%(`:109`)·@22마디=100%(`:110`), BLIND(그룹14)@18마디=100%(`:109`), 각각 `source_ref`에 그 행 번호를 남긴다. SCENE 열의 30%·40%·70%·"2마디 번짐"·"끊어 바꿈"·"1마디 번짐"(`:104,106,109,110`)은 SCENE이 트랙에 없어(`_love_attack_tracks()`가 SCENE을 뺀 이유, 이 파일 자체 docstring) 대응 큐가 없으므로 전사하지 않는다 — 나머지 26개 큐의 `value_percent`와 30개 큐 전부의 `fade_bars`는 `None`이다(REQ-LDBEAT-006(i-6)(i-7)). `find_overlapping_group_tracks`/`validate_beat_grid_tracks`는 트랙 레벨만 보므로 수정 불필요(REQ-LDBEAT-004(h)/REQ-LDBEAT-006(iii) 불변, 직접 재확인).
2. **런북 모드 안의 전체화면 전환을 만든다(REQ-LDBEAT-004(a)(g))**: `App.tsx`의 `runbookMode` 참 분기 안에 전환 가능한 전체화면 모드를 추가한다(트리거의 정확한 UI는 §5 열린 결정 6, M2에서 director와 확정). 기존 5블록(`RunbookMode.tsx`의 헤더·`ConceptPanel`·`CueSheetTimeline`·`SongTimeline`·`RunbookGateBar`) 안에 `<BeatGrid>`를 끼워 넣는 현재 배선은 제거하고, `BeatGrid`를 그 전체화면 모드의 루트 컴포넌트로 승격한다. 코파일럿 **메인** 화면(`runbookMode` 거짓)은 건드리지 않는다.
3. **칸 편집 UI를 다섯 필드로 분리하고, 막대 채우기 색 규칙을 정한다**: 큐 편집 칸(REQ-LDBEAT-004(c))이 밝기·위치·색·효과·들어올 때를 각각 독립된 자리에 보여준다(같은 문장 네 번 반복하던 M2후속 임시 동작 제거). 막대 채우기 색은 `color_preset_no`가 있으면 그 프리셋의 스웨치 색, **미정(`None`)이면 명시적 중립색(예: 회색 해칭)으로 "안 정해짐"을 그대로 보여준다 — 임의 색을 지어내 칠하지 않는다**(REQ-LDBEAT-015(f)와 같은 원칙을 렌더링에도 적용).
4. **M1 상태표를 실시간 소스로 바꾼다(REQ-LDBEAT-003(b))**: `ui/src/components/beatGridM1Probes.ts`의 손으로 옮긴 상수 의존을 걷어내고, 서버가 `progress.md`의 M1 표를 파싱해 서빙하거나(권고) 빌드 타임에 그 표를 읽어 생성하는 경로 중 하나로 교체한다. 표가 비어 있거나 파싱 실패 시 "미확인"으로 표시(지어낸 PASS 금지).
5. **(가장 저렴, 마무리) 시안 대조 캡처 + 차이 목록을 기록한다**: 시안(`reports/ldbeat-runbook-ui-proposal-20261008.html`)과 같은 뷰포트의 헤드리스 캡처를 나란히 찍고, `progress.md`에 차이 목록(남은 격차)을 정직하게 적는다 — t532/t534 선례(`side_by_side.png`)와 같은 방식.
6. **(사후 SPEC 편입, 구현은 이미 커밋 `edc537db`/`7ff80bed`로 머지됨)** (1)의 구현이 REQ-LDBEAT-006 밖에서 만든 `scene_memos`(SCENE 메모, REQ-LDBEAT-006(iv-1)~(iv-4))와 로더의 리그·곡 무관 일반화(REQ-LDBEAT-006(v-1)(v-2))는 `progress.md` "t537 ② 구현" 절 (5)(6)이 "감사 필요"로 남겨 둔 것을 이 카드의 SPEC 개정이 정식 REQ/AC로 편입했다 — 코드 변경 0줄(spec.md/acceptance.md만 교정).

## §F 안티패턴

- **격자를 편한 대로 로컬 데이터 구조로 직접 콘솔 커맨드에 매핑하지 마라** — REQ-LDBEAT-007/008. 문장 → 새 서버측 편집 연산 → 서버 경로를 거쳐야 한다. AI 제안의 「적용」도 예외가 아니다.
- **"기존 파서가 이미 격자를 커버한다"고 가정하고 M3을 생략하지 마라(D2)** — REQ-LDBEAT-007. `parse_cue_sheet_edit_request`에는 마디·역할 어휘가 없다. 재사용되는 것은 원칙과 검증 관행이고, 연산 자체는 새로 만든다.
- **M1 프로브를 "어차피 다 될 것"이라 가정하고 M4의 송신 와이어링 부분을 먼저 쓰지 마라** — REQ-LDBEAT-001. FAIL이 나오면 그 기능은 비활성으로 남아야 한다.
- **"songcue가 타임코드 커맨드를 이미 낸다"를 "에미터 신설이 필요 없다"로 읽지 마라(카드 t526 재교정)** — REQ-LDBEAT-013. songcue는 시퀀스 1 : 타임코드 1만 지원한다 — 박자 격자의 다대다 배선은 여전히 새로 설계해야 한다. 반대로 "앱이 타임코드를 전혀 못 만든다"는 이전 과장도 더 이상 쓰지 마라.
- **콘솔 그룹 트랙을 "SCENE"·"BACK PULSE" 같은 역할·효과 혼성 이름으로 코드에 박지 마라(§B 위험 9)** — REQ-LDBEAT-004. 트랙 식별자는 콘솔 그룹 번호/이름이다.
- **응답기 `max_prop_value` 상한을 그냥 올리지 마라** — REQ-LDBEAT-002/§D. `max_payload = 1900`에 걸려 큰 그룹을 한 번에 못 담는다. 나눠 읽기로 고친다.
- **새 승인=송신 비교 로직을 작성하지 마라, 그러나 리포트 스크립트를 그대로 앱에서 import하지도 마라** — REQ-LDBEAT-011. `.moai/reports/t512/approval_vs_sent.py`의 로직을 앱 경로로 승격한다 — 로직 재작성도, 위치 방치도 둘 다 금지.
- **G9(스피드 마스터 BPM 자동 설정)을 이 SPEC에서 풀려고 하지 마라** — REQ-LDBEAT-014. 미확인 상태를 정직하게 보여주는 것까지만 이 SPEC의 일이다.
- **LOVE ATTACK의 배치 규칙서 값을 전역 상수로 박아 다른 곡에도 적용되게 하지 마라** — REQ-LDBEAT-006. 곡별 기본값이지 전곡 강제가 아니다.
- **배치 규칙서 파일을 이 워크트리로 복사해 두 소스를 만들지 마라** — §B 위험 7. 절대경로 참조 또는 t523 머지 대기.
- **격자 데이터를 `timeline` 사전 밖의 별도 변수로 "임시로" 두고 넘어가지 마라** — REQ-LDBEAT-006/§D. M2에서 저장소 결정을 명시적으로 내리고 기록한다.
- **프리셋 번호대를 로드맵 예시 그대로 쓰지 마라** — REQ-LDBEAT-015/§B 위험 11. 실제 쇼 파일과 대조해 재확정한다.
- **마디 분석(SPEC-LDBARMAP-001)이나 자동 배치(SPEC-LDARRANGE-001)를 이 SPEC에서 선구현하지 마라** — spec.md §4. 둘 다 아직 존재하지 않는 별도 SPEC이다.
- **(카드 t537) 전체화면 전환 요구를 "기존 블록 레이아웃을 조금 키우는 것"으로 축소하지 마라** — REQ-LDBEAT-004(a)(g). 감독 지시는 독립 전체화면 뷰이고, `App.tsx`의 런북 모드 분기 안에 전환이 필요하다. 다만 코파일럿 **메인** 화면(`runbookMode` 거짓)은 여전히 건드리지 않는다.
- **(카드 t537) `BeatGridCue.label`의 자유 텍스트를 파싱해 구조화 필드(밝기/위치/색/효과)를 역산하지 마라** — REQ-LDBEAT-006(ii-2). 레거시 칸은 구조화 필드를 미정으로 두고 `label`만 그대로 보여준다(REQ-LDBEAT-006(ii-1)).
- **(카드 t537 plan-audit D2) `entry`에 초 단위 페이드 값을 저장하지 마라** — REQ-LDBEAT-006(i-4). `fade_bars`(마디 수)로만 저장하고, 초 환산은 화면 표시 시점에 BPM으로 계산한다.
- **(카드 t537 plan-audit D9) `effect_preset_no`를 "위치 효과 풀 전용"으로 못박지 마라** — REQ-LDBEAT-006(i-3). 색·혼합 효과도 같은 필드에 담되 `effect_kind`로 구분한다.
- **(카드 t537) LOVE ATTACK 기본값의 프리셋 번호를 시안(`ldbeat-runbook-ui-proposal-20261008.html`)의 `P` 객체에서 베껴 쓰지 마라** — REQ-LDBEAT-015(f). 그 객체는 시안 자신이 지어낸 예시이고 배치 규칙서의 출처가 아니다. 출처 없는 자리는 미정(`null`)이다.
- **(카드 t537) M1 상태표를 또 다른 손-복사 상수로 "다시" 박아 두지 마라** — REQ-LDBEAT-003(b). `beatGridM1Probes.ts`가 겪은 낡음 문제(progress.md 재확인)를 반복하지 않는다 — 살아있는 읽기 경로로 교체한다.

## §G 교차 참조

- `reports/effect-arrangement-rules-20261007.md`(주 체크아웃, 2026-10-07 작성 — 규칙 9개·역할별 시퀀스 6개·§3 전체 배치·§4 0~25마디 격자·§5 감독 결정·§6 안 잰 것·§7 확정 뒤 순서). 카드 t523이 이 저장소에 추적본을 싣는다.
- `reports/effect-arrangement-research-pro-20261007.md`·`reports/effect-arrangement-research-kpop-20261007.md`(배치 규칙서의 원 조사 자료, 같은 주 체크아웃 경로, 같은 추적 상태).
- `reports/ldbeat-feasibility-roadmap-20261010.md`+`.html`(카드 t526 입력 — 되는 것·일부만 되는 것·없는 것 7개·안 잰 것 9개·SPEC 진행안·결정 필요 1~5).
- `reports/ldbeat-runbook-ui-proposal-20261008.html`(+ `.md`, UI 결정 + 트랙 모양 "정정" 절 — REQ-LDBEAT-004 교정의 1차 출처).
- `reports/ldbeat-runbook-mockup-20261008.html`(+ `.md`, 프리셋 아키텍처 §3~§4 + 편집 세 길 §2 — REQ-LDBEAT-015/007~009 확장의 1차 출처).
- `.moai/reports/t525/verdict.md`(읽기 전용 프로브, 콘솔 쓰기 0 — 2D 무대 좌표 실측·그룹 소속 절단 실측).
- `.moai/specs/SPEC-LDRHYTHM-001/spec.md`·`plan.md`(REQ-LDRHYTHM-001·009·012, M1~M3·M4+ 범위 후보 — 이 SPEC이 그 M4+ 중 "런북 모드 구현" 조각을 담당).
- `.moai/specs/SPEC-LDDESIGN-001/spec.md` §3.15(M7, REQ-LDDESIGN-087~095 — 로컬 변형 금지·단일 진실 경로 패턴의 출처).
- `server/design/cue_sheet_edit.py:227,264,665,38-55,187,493` — 큐 레벨 파서·앵커·칸 화이트리스트·적용기·그룹 스코프(원칙·검증 관행 재사용 대상, 연산 자체는 재사용 대상 아님, D2).
- `server/web/session.py:3486,3831,8467,8498,8505` — `SongTimelineStore`·`TimelineDraftHistory`·편집 요청 서버 진입점·거절 사유 패턴·전체-사전 되돌리기 스냅샷(D3 저장소 실체).
- `server/web/timeline_library.py:48` — `SongTimelineLibrary`(D3 저장소 실체).
- `server/director/emit.py:51` — 장벽 A(`PLAYBACK_MODES`, 바뀌지 않는 기존 경로).
- `server/looks/songcue.py:634,683` — `_timecode_commands`(타임코드 커맨드 모양, M4 재사용 대상)·`_ascii_label`(영문화, 카드 t526 재교정 핵심 사실).
- `console/lua/copilot_responder.lua:43,282,999-1005` — 응답기 긴 값 절단 지점(M1 확장 대상, 카드 t526).
- `.moai/reports/t512/approval_vs_sent.py` — 재사용 대상 승인=송신 비교 로직(앱 경로로 승격 필요, 리포트 스크립트 자체는 재사용 대상 아님).
- `.moai/reports/t516/verdict.md:104,463`·`.moai/reports/t519/verdict.md`·`origin/WT-m2-batch1:.moai/reports/t520/verdict.md:92-94,183-186` — 실기 사실 출처(타임코드가 커맨드로 만들어진다는 D1 증거 + §20-4 프로브 1~4 제안).
- `ui/src/components/RunbookMode.tsx`(280행) — 확장 대상 컴포넌트.
- `SPEC-LDBARMAP-001`·`SPEC-LDARRANGE-001`(가칭, 아직 미존재) — spec.md §4 Out of Scope 교차 참조.
- `server/design/beat_grid.py`(M2 신설, 커밋 `05ad9ec4`) — `BeatGridCue{bar,label}` 현재 모양(M7이 구조화할 대상), `_love_attack_tracks()`의 30개 큐(배치 규칙서 §2·§4 전사, 프리셋 번호 0개), `find_overlapping_group_tracks`/`validate_beat_grid_tracks`(트랙 레벨만 — M7 영향 없음 확인 대상).
- `ui/src/protocol.ts:362-399,404-432` — `SongTimelineSection`의 큐 레벨 명명 관례(`movement`/`effect`/`mib_mode`/`fade_seconds`/`position_preset_no`, M7 구조화 필드 명명의 선례)와 현재 `BeatGridCue`/`BeatGridTrack`/`BeatGridView` 모양. **plan-audit D2 이탈 고지**: M7의 `entry`는 이 선례의 `fade_seconds`를 따르지 않고 `fade_bars`(마디 수)를 쓴다 — REQ-LDBEAT-006(i-4) 참조, 의도적 단위 변경이다.
- `ui/src/components/BeatGrid.tsx`·`RunbookMode.tsx`(M2/M2후속, 커밋 `05ad9ec4`·`7be4785e`) — M7이 다시 짤 "기존 5블록 사이 블록" 현재 배선.
- `ui/src/components/beatGridM1Probes.ts`(카드 t534 신설) — M7 (4)가 교체할 손-복사 상수(`M1_PROBE_RESULTS_T531`).
- `.moai/specs/SPEC-LDBEAT-001/progress.md` M2 후속 절 "안 잰 것" — M1 상수 낡음 위험을 그 자신이 이미 적어 둔 기록(REQ-LDBEAT-003(b)의 근거).
