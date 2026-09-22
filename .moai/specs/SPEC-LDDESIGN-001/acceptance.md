# SPEC-LDDESIGN-001 인수 기준

Given-When-Then 시나리오. 각 AC는 이진 판정(PASS/FAIL)이 가능해야 한다.
AC-LDDESIGN-001~013은 `final-verification-20260921.md`의 게이트
G1~G13에 1:1로 대응한다(순서도 동일). 8곡 기준선은
`.claude/worktrees/pilot-labeling/pilot_baseline.json`(또는 M6에서 옮긴
정본 위치, plan.md §D D3)이다.

**AC 개수 예외**: spec.md §2.4가 REQ 101개(2026-09-22 CUE SHEET
14열 확정·컨셉 패널 한눈에+탭 3개·시스템 폰트+tabular-nums·PLAN CUE
수정요청 생성기 항목별 제거·자유 입력 한 줄 5건 반영으로
REQ-LDDESIGN-096~101 신설 이전 95개, 그 이전 PLAN CUE 수정요청
생성기 REQ-LDDESIGN-087~095 신설 이전 86개, 그 이전 85개)를 단일
SPEC에 두는 것을 명시적 감독 지시로 예외 처리했다 — 그 REQ 101개
전량이 최소 1개의 구체적 AC로 추적돼야 하므로(auditor D3), AC
개수도 같은 예외 아래 Tier L 상한(25)을 넘는다(총 53개 — iteration 3
감사 D6 대응으로 AC-031을 AC-031·045~048 4개 개별 assert로 분리,
2026-09-22 감독 결정 5건 반영으로 AC-049~053 5개 신설, REQ 커버리지는
변동 없음). §2.4의 사유가 여기도 적용된다.

## AC-LDDESIGN-001 — G1 어휘 닫힘 (검증: REQ-LDDESIGN-005, REQ-LDDESIGN-006, REQ-LDDESIGN-007, REQ-LDDESIGN-008, REQ-LDDESIGN-016)

**Given** 8곡(pilot_baseline) 각각의 워크시트 컴파일 결과 — 구간 판정기
5종 출력(REQ-008 재매핑 입력)을 포함한다.

**When** 조립된 큐시트의 구간·트리거·원샷 이름을 어휘 상수(REQ-005~007)와
대조하고, 판정기 원출력이 9종 어휘로 재매핑됐는지 확인한다.

**Then** 8곡 전부, 큐시트에 나타나는 모든 구간·트리거·원샷 이름이 닫힌
어휘 안에 있다 — 어휘 밖 이름이 하나라도 있으면 조립 자체가
`VocabError`로 실패해야 한다(REQ-016). 판정기 5종 출력은 전부 9종 중
하나로 재매핑되어 있다(REQ-008).

## AC-LDDESIGN-002 — G2 후렴 정체성 (검증: REQ-LDDESIGN-042, REQ-LDDESIGN-030)

**Given** 후렴이 2회 이상인 7곡.

**When** 각 후렴 쌍(인접한 Chorus/Final Chorus)의 정체성 판정(주색 동일
또는 Final Chorus)을 계산한다.

**Then** 전체 후렴 쌍 전부(8곡 중 후렴≥2인 7곡 전부) 정체성 유지
비율이 **1.0**이다 — `chorus-escalation-audit-20260921.md` v3 실측치
(8곡 전부 정체성 1.0) 및 REQ-042의 엄밀한(비율이 아닌) "이전 후렴과
동일하게 유지된다" 서술과 정합한다. 구조상 후렴 쌍이 없는 곡(DinoDino,
후렴 1개)은 n/a.

## AC-LDDESIGN-003 — G3 회차마다 새 축 (검증: REQ-LDDESIGN-043)

**Given** 후렴이 2회 이상인 7곡.

**When** 5회차까지의 후렴 쌍마다 6축(그룹 수·면적·밝기·모션·방향·밀도)
중 새로 확장된 축이 있는지 확인한다.

**Then** 5회차 이내 구간에서 새 축이 0인 쌍이 없다.

## AC-LDDESIGN-004 — G4 피날레 새 축 + 여유 (검증: REQ-LDDESIGN-048, 044)

**Given** Final Chorus가 있는 7곡(DinoDino 제외 — 후렴 1개).

**When** Final Chorus 직전 쌍의 새 축 여부와, 그 직전 구간의 헤드룸
`remaining_motion`을 확인한다.

**Then** Final Chorus는 최소 1개의 새 축을 갖고, 직전 구간의 남은 모션
단계는 1 이상이다.

## AC-LDDESIGN-005 — G5 헤드룸 경고 0 (검증: REQ-LDDESIGN-050, REQ-LDDESIGN-051, REQ-LDDESIGN-052, REQ-LDDESIGN-047)

**Given** 8곡.

**When** 매 구간 큐의 헤드룸 4축(미사용 그룹·유보색·유보 효과·남은
단계, REQ-050)을 계산하고, 헤드룸 경고 4조건(인트로 전부 켬 / Chorus 1
블라인더·스트로브·순백 사용(REQ-051의 OR 조건) / 브릿지 무감소(구간
단위) / 피날레 새 축 없음)을 곡별로 검사한다.

**Then** 8곡 전부 헤드룸 4축이 채워져 있고, 경고 4조건 중 어느 것도
성립하지 않는다. 경고가 성립해도 조립은 실패하지 않고 큐시트·상태줄에
경고로만 노출된다(REQ-052).

## AC-LDDESIGN-006 — G6 컬러: 유보색 조기 0 · 브리지 위반 0 (검증: REQ-LDDESIGN-027, 029)

**Given** 8곡.

**When** 유보색(`palette.reserved`)이 해제 전 등장하는지, 인접 구간이
공통색 0개인 전환이 있는지 검사한다.

**Then** 8곡 전부 유보색 조기 등장 0건, 브리지 위반 0건이다.

## AC-LDDESIGN-007 — G7 후렴 주색 동일 (검증: REQ-LDDESIGN-030)

**Given** 후렴(Chorus, Final Chorus 제외)이 있는 7곡.

**When** Chorus 구간 큐의 색 집합 크기를 센다.

**Then** 7곡 전부 색 집합 크기가 1 이하다(주색이 단일하다).

## AC-LDDESIGN-008 — G8 후렴 앞 빌드업 (검증: REQ-LDDESIGN-037)

**Given** 8곡.

**When** 빌드업 삽입 조건(앞 구간이 후렴이 아니고 일반 후렴은 5마디
이상, Final Chorus 앞은 3마디 이상)을 만족하는 자리 수와, 실제로 삽입된
빌드업 큐 수를 비교한다.

**Then** 삽입된 빌드업 큐 수가 조건을 만족하는 자리 수 이상이다(자리마다
최소 1개).

## AC-LDDESIGN-009 — G9 트래킹: Block·Release·누출 0 (검증: REQ-LDDESIGN-053, REQ-LDDESIGN-054, REQ-LDDESIGN-055, REQ-LDDESIGN-056, REQ-LDDESIGN-057)

**Given** 8곡.

**When** 모든 큐의 `tracking` 필드가 4모드(REQ-053: Block/Track/Cue
Only/Release) 중 하나인지 확인하고, 각 곡의 첫 큐·마지막 큐의
`tracking` 값과, 구간 큐(REQ-055 기본 Track)·프레이즈 큐(REQ-056 기본
Cue Only) 다음 큐의 트래킹 상태를 확인한다.

**Then** 모든 큐가 4모드 중 하나를 갖고, 첫 큐는 `Block`, 마지막 큐는
`Release`, 구간 큐는 `Track`, 프레이즈 큐는 `Cue Only`이며, `Cue Only`
큐가 적용한 값이 다음 큐로 새어 나간 사례가 0건이다.

## AC-LDDESIGN-010 — G10 상대 감소 겹침 없음 (검증: REQ-LDDESIGN-021)

**Given** 절(Verse)이 3개 이상인 곡(구조적으로 해당 없는 곡은 n/a).

**When** 2번째 이후 절의 최대 밝기 값들을 비교한다.

**Then** 서로 다른 절의 밝기 값 집합 크기가 1 이하다(구간 기준 참조로
계산돼, 앞 절 값에 겹쳐 곱해지지 않는다).

## AC-LDDESIGN-011 — G11 타이밍 전 큐 배정 (검증: REQ-LDDESIGN-058, REQ-LDDESIGN-059, REQ-LDDESIGN-060, REQ-LDDESIGN-061)

**Given** 8곡.

**When** 모든 시퀀스 큐의 `timing.kind`와 `seconds`가 채워져 있는지,
후렴 진입 큐마다 `stagger`(순차 딜레이 서술)가 있는지, 방출되는 페이드
초가 `server/design/cue_fade.py`의 `store_with_fade`(`CueFade` 키워드,
REQ-061)를 재사용하는지 확인한다.

**Then** 8곡 전부, 모든 큐가 `timing.kind`/`seconds`를 갖고 후렴 진입
큐 전부가 `stagger` 값을 가지며, 방출된 페이드 명령이 `CueFade` 문법
그대로다(`Property 'Fade'` 형태가 나타나지 않는다).

## AC-LDDESIGN-012 — G12 MIB: 켜진 채 이동 0 (검증: REQ-LDDESIGN-062, REQ-LDDESIGN-063, REQ-LDDESIGN-064, REQ-LDDESIGN-065, REQ-LDDESIGN-066, REQ-LDDESIGN-067)

**Given** 8곡.

**When** MIB 판정(`dark`/`mark`/`live`, REQ-062)을 포지션 변화 큐마다
계산하고, `mark` 판정에 Mark 큐가 자동 삽입됐는지(REQ-063), 이 판정
로직이 songcue/컨셉 계층 경로에 연결돼 있는지(`director/validate/mib.py`
를 직접 import하지 않고 같은 원칙을 재구현했는지, REQ-067) 확인한다.

**Then** `live`(켜진 채 이동) 판정이 0건이다 — 어두운 창이 없는
구간(연속 후렴 등)에서는 REQ-065에 따라 포지션을 유지해 애초에 변화
자체가 없어야 한다. `mark` 판정마다 Mark 큐가 정확히 1건 삽입돼 있다
(REQ-063). MIB 판정 로직은 songcue 경로 안에서 계산되며 `director/
validate/mib.py`를 직접 import하지 않는다(REQ-067).

## AC-LDDESIGN-013 — G13 큐 밀도 10~45 (검증: REQ-LDDESIGN-041)

**Given** 8곡.

**When** 곡별 시퀀스 큐(구간+프레이즈, 원샷 제외) 총 개수를 센다.

**Then** 8곡 전부 시퀀스 큐 수가 10~45 범위 안에 있다.

## AC-LDDESIGN-014 — 어휘 밖 값은 항상 거부된다(경계 케이스) (검증: REQ-LDDESIGN-016)

**Given** 워크시트의 `sections[].section`에 9종 어휘에 없는 문자열
(예: "Hook")을 넣은 픽스처.

**When** 워크시트 로더가 이 워크시트를 파싱·컴파일한다.

**Then** 조립은 예외로 실패하고, 오류 메시지가 어느 필드에 어떤 값이
왔는지 명시한다 — 부분 성공(어휘 밖 값을 조용히 무시하고 나머지만
조립)은 일어나지 않는다.

## AC-LDDESIGN-015 — `Cue Only` 큐는 다음 큐로 복원된다(회귀 방지) (검증: REQ-LDDESIGN-057)

**Given** 프레이즈 큐(`Cue Only`)가 구간 큐 사이에 삽입된 픽스처 —
프레이즈 큐가 밝기를 일시적으로 100까지 올린다.

**When** 그다음 구간 큐를 계산한다.

**Then** 그다음 구간 큐의 시작 상태는 프레이즈 큐 이전(직전 `Track`
큐)의 값을 기준으로 계산되며, 프레이즈 큐가 올린 100이 이어지지 않는다.

## AC-LDDESIGN-016 — `_arc_palette`/`per_chorus` 회전이 정체성 판정에서 제거됐다 (검증: REQ-LDDESIGN-031, REQ-LDDESIGN-004)

**Given** 같은 후렴 역할(`role="chorus"`)이 6회 반복되는 픽스처(오늘
`_arc_palette(("blue","white"), "chorus", k)` k=1..6 실측 — (blue,warm
white)(blue,magenta) 교대 반복을 재현하는 입력).

**When** M3 완료 후 이 픽스처로 컨셉 계층의 정체성 판정 경로(§3.5)를
실행한다.

**Then** 6회 전부 주색이 동일하다(더 이상 warm white/magenta 교대가
나타나지 않는다) — `_arc_palette`/`_per_chorus_palette`가 이 경로에서
호출되지 않는다는 증거로, 정체성 판정 결과가 항등이다.

## AC-LDDESIGN-017 — 큐 생성 경로가 하나다 (검증: REQ-LDDESIGN-003, 077)

**Given** 같은 곡·같은 워크시트 입력.

**When** 채팅/웹 세션 경로(`server/web/session.py`)와 LLM 툴 경로
(`server/orchestrator/tools.py:3230`) 양쪽으로 큐를 생성한다.

**Then** M6 완료 후, 두 경로가 생성한 큐시트(구간·순서·값)가 동일하다
— 두 개의 독립된 컴파일 로직이 아니라 하나의 컴포저를 공유한다는
증거다.

## AC-LDDESIGN-018 — 런북 모드 레이아웃 유지 + 컨셉 패널이 존재하고 기본 접힘이며 설명 4칸과 인과 불릿을 편다 (검증: REQ-LDDESIGN-078, REQ-LDDESIGN-079, REQ-LDDESIGN-080, REQ-LDDESIGN-086, B군)

**Given** 런북 모드(`RunbookMode.tsx`)로 전환되어 큐시트가 생성된
화면 상태. 메인 화면(리그 대시보드·큐 모니터·채팅·설정·페이퍼워크)은
대상이 아니다.

**When** 런북 모드 화면을 처음 연다.

**Then** 런북 모드의 기존 5블록 레이아웃(오늘의 곡·큐 순서 →
타임라인 → CUE SHEET → PLAN CUE 카드 → 상태줄, REQ-078)이 그대로
보이고, 컨셉 패널이 접힌 상태로 보이며, 항목을 클릭하면 설명
4칸(무슨 뜻 / 무대에서 / 왜 이렇게 제안했나 / 바꾸려면)이 펼쳐진다.
컨셉 패널의 연출 설명은 워크시트 `concept` 필드의 인과 불릿 원문 +
여섯 칸 문법 요약 표(구간→색→기구·밝기→움직임→효과→그래서 보이는
것, 실제 값으로 채워짐, REQ-080)로 구성된다. 메인 화면 컴포넌트는
수정되지 않은 채 그대로이고, 런북 모드가 표시하는 프리셋 풀 이름·
번호·콘솔 연결 상태는 메인 화면에서 읽어온 값과 일치하며, 메인
화면 쪽에는 런북 모드의 제안(초안) 상태가 반영되지 않는다(REQ-086).

## AC-LDDESIGN-019 — `Q###` 배지가 세 곳에서 동일하고 CUE SHEET가 정확히 14열로 재구성됐다 (검증: REQ-LDDESIGN-083, REQ-LDDESIGN-082, REQ-LDDESIGN-096)

**Given** 런북 모드에서 조립된 큐시트 하나.

**When** 같은 큐의 실행기 번호(`Q###`)를 타임라인, CUE SHEET, PLAN CUE
카드 세 곳에서 각각 읽고, CUE SHEET의 열 구성을 신규 5열·기존 9열·
제거된 5열 목록과 대조하며, 임의의 한 행에서 좌측 색 레일을 확인한다.

**Then** 세 곳의 `Q###` 값이 모두 동일하다. CUE SHEET는 **정확히
14열**이다 — 기존 9열(Q#·구간·시각·색·밝기·기구 그룹·움직임·효과·
Fade) 유지 + 신규 5열(회차·Trigger·MIB·Track 예외·근거 등급) 추가
(REQ-082). `Track 예외`는 기본값 `Track`일 때만 빈 칸이다. 기존에만
있던 5열(`TC Out`·`Dur`·`Mood`·`Trans`·`Note`)은 화면에 나타나지
않는다(REQ-082). `Trans` 값(SNAP/XFADE/FADE)은 열이 사라졌어도
`server/design/cue_sheet_edit.py`의 `TRANS_VALUES`·
`EDITABLE_FIELD_LABELS["trans"]`에서 계속 유효한 값으로 남아
있다(REQ-096). 각 행의 좌측 7px에는 그 큐 구간의 Color Strip 색이
색 레일로 표시된다.

## AC-LDDESIGN-020 — 타임라인과 CUE SHEET 스크롤이 연동되고 타임라인 색이 Color Strip과 일치하며 상태줄에 GATE가 보인다 (검증: REQ-LDDESIGN-085, REQ-LDDESIGN-081, REQ-LDDESIGN-084)

**Given** 런북 모드에서, 큐 개수가 화면 높이를 넘는 곡(예: Too Cool,
시퀀스 큐 35+개).

**When** CUE SHEET를 세로로 스크롤해 특정 큐를 화면 중앙에 두고,
타임라인 블록 색을 그 큐의 Color Strip 값과 대조하며, 상태줄을 읽는다.

**Then** 타임라인이 가로로 자동 이동해 같은 큐의 시각 지점을 화면
안에 보여준다(REQ-085). 타임라인 블록 색은 Color Strip 산출값과
동일하다(REQ-081). 상태줄은 §3.6~3.11 게이트 통과/경고 요약(GATE
표시)을 갖는다(REQ-084).

## AC-LDDESIGN-021 — 실기 콘솔 1곡 검증(Rain) (검증: M8, 필수)

**Given** M0~M7이 완료된 파이프라인, 실기 grandMA3 onPC, Rain 워크시트.

**When** Rain 워크시트를 이 파이프라인으로 컴파일해 콘솔에 반영한다
(승인 절차 포함).

**Then**
- Sequence + Cue + Timecode가 콘솔에 실제로 저장된다(리드백으로 확인).
- 육안으로 후렴 6회 전체가 동일한 색(노랑 계열)으로 보인다 — 흰색↔빨강
  교대(오늘 회귀 실측)가 재현되지 않는다.
- 이 AC 없이는 이 SPEC의 M8은 완료로 간주되지 않는다(사용자 명시 요구).

## AC-LDDESIGN-022 — B군: Block/Release 콘솔 문법 프로브 (검증: 후속 SPEC 전제)

**Given** 실기 grandMA3 onPC, 트래킹 정책 필드가 채워진 테스트 큐 2개
(하나는 `Block`, 하나는 `Release`).

**When** 두 큐를 콘솔에 순서대로 보내고 그 뒤 트래킹 상태를 관측한다.

**Then** 관측된 실제 명령 문법(성공/거부/대체 문법)을 프로브 결과로
기록한다 — 이 AC는 PASS/FAIL이 아니라 **관측치를 남기는 것 자체가
완료 기준**이다(B군, §4 콘솔 프로브 필요).

## AC-LDDESIGN-023 — B군: 축별 딜레이(순차) 콘솔 문법 프로브 (검증: 후속 SPEC 전제)

**Given** 실기 grandMA3 onPC, `stagger`(중앙→외곽 0→0.4초) 필드가 채워진
테스트 큐.

**When** 이 큐를 콘솔에 보내고 실제로 축별(Pan/Tilt)로 지연이 걸리는지
관측한다.

**Then** 관측된 실제 명령 문법(또는 미지원 판정)을 프로브 결과로
기록한다(B군).

## AC-LDDESIGN-024 — B군: Mark 콘솔 문법 프로브 (검증: 후속 SPEC 전제)

**Given** 실기 grandMA3 onPC, MIB 판정이 `mark`로 나온 테스트 큐 시퀀스.

**When** Mark 큐를 콘솔에 보내고 그 뒤 목표 큐에서 실제로 포지션이
사전 이동 완료된 상태로 나타나는지 관측한다.

**Then** 관측된 실제 명령 문법과 창 조건(이동+정착 초 실측치)을 프로브
결과로 기록한다(B군) — 이 실측값이 plan.md §F의 잠정값(MIB 이동/정착
초)을 콘솔 실측치로 교체한다.

## AC-LDDESIGN-025 — t429 회귀 재현 시험 + bpm 실배선이 선행 전제로 고정된다 (검증: REQ-LDDESIGN-001, REQ-LDDESIGN-002, M0 게이트)

**Given** `origin/main`(t429 미수정 상태를 재현하는 픽스처 — 후렴 2회
이상, 실제 룩 라이브러리 사용, 프로덕션 순서 그대로), `density_bpm`이
계산되는 픽스처(`tools.py:3177`).

**When** M0 착수 전 이 픽스처로 프로덕션 경로(`build_songcue_bundle`
공개 진입점)를 실행하고, M0 완료 후 `tools.py:3230`의 호출 인자에
`bpm=density_bpm`이 실제로 전달되는지 확인한다.

**Then**
- M0 이전: `SongCueBundleError: movement_line_collision`이 재현된다
  (t429 미수정 상태 확인 — 이 SPEC이 실제로 그 위에서 시작하는지 검증).
- M0 완료 후: 같은 픽스처가 예외 없이 성공한다 — 8곡×2장르×분할 유무
  32/32 OK(오늘 수정 브랜치 실측치)를 최소선으로 재현.
- M0 완료 후: `build_songcue_bundle` 호출부에 `bpm=density_bpm`이 실제
  인자로 전달돼 있다(REQ-002) — SPEC-LDRETURN-001이 `status: completed`
  이거나, 명시적 override 로그(`.moai/logs/depends-on-override.log`)가
  존재해야 이 단계가 착수 가능하다.
- M0이 닫히지 않은 채 M1 이후 작업을 시작하면 이 AC는 FAIL이고, 그
  마일스톤은 착수 자체가 무효다(REQ-LDDESIGN-001).

## AC-LDDESIGN-026 — 안전 큐 위치·근거 등급 노출·자동 설명 (검증: REQ-LDDESIGN-068, REQ-LDDESIGN-069, REQ-LDDESIGN-070, REQ-LDDESIGN-071, REQ-LDDESIGN-072)

**Given** 조립된 큐시트 하나(8곡 중 아무 곡).

**When** 첫 큐와 마지막 큐를 확인하고, 임의 큐의 `evidence` 등급·
`description` 자동 생성 여부·"[공개 근거 없음]" 표시 대상을 확인한다.

**Then** 첫 큐는 안전(프리셋) 큐 Q0.5로 `Block` 트래킹·최소 조명·기본
색·포지션 홈을 명시하고(REQ-068), 마지막 큐는 모든 그룹을 끄고
`Release`로 제어를 반환한다(REQ-069). 모든 큐가 `description`을 갖고
복원/추가/제거·색 변화·최대 밝기·남겨둔 자원을 서술한다(REQ-070).
`evidence` 등급은 화면 열로 노출되고 `verified`는 "이 곡에서 검증한
것이 아니다"라는 설명이 함께 붙는다(REQ-071). 자동 채움 항목 중 공개
근거가 없는 것은 "[공개 근거 없음]" 표시를 갖는다(REQ-072).

## AC-LDDESIGN-027 — 기존 하류 브리지 재사용 확인 (검증: REQ-LDDESIGN-073, REQ-LDDESIGN-074, REQ-LDDESIGN-075, REQ-LDDESIGN-076, REQ-LDDESIGN-077)

**Given** 큐 모델 v2로 조립된 8곡 전체.

**When** 콘솔 명령 컴파일 경로가 부르는 함수를 추적해 `server/design/
lint.py`(L1~L14)·`server/design/energy.py`(D1~D5)·`server/design/
cue_fade.py`를 실제로 호출하는지 확인하고, 13게이트가 `server/tests/`
아래 자동 테스트로 존재하는지, 오늘 측정치(PASS 98·n/a 6·FAIL 0)
대비 악화가 없는지 확인한다.

**Then** 콘솔 명령 컴파일 경로는 기존 lint/energy/cue_fade 함수를
직접 호출한다(재구현하지 않는다, REQ-073). 생성된 큐는 기존
`Sequence + Cue + Timecode` 저장·리드백·승인 흐름을 그대로 통과한다
(REQ-074). 13게이트가 `server/tests/`에 회귀 시험으로 고정돼 있고
(REQ-075), 8곡 중 어느 곡도 오늘 측정치보다 나쁜 결과(새 FAIL)가
없다 — 있다면 그 마일스톤은 병합 보류 상태로 `progress.md`에 원인이
기록돼 있다(REQ-076). `server/looks/songcue.py`의 사다리 로직은 더는
독립 코드 경로가 아니고 §3.7 회차 규칙의 데이터 표로 흡수돼 있다
(REQ-077).

## AC-LDDESIGN-028 — 재매핑 감독 확인 표시 + 자유 입력 전용 트리거 (검증: REQ-LDDESIGN-009, REQ-LDDESIGN-010)

**Given** 판정기가 재매핑한 구간(REQ-008)이 포함된 큐시트, 그리고
오디오로 검출 불가능한 트리거 4종(코드·조성 변화, 핵심 가사, 안무
대형 변화, 중심 멤버·솔로 변경)이 필요한 픽스처.

**When** 재매핑되거나 규칙이 새로 삽입한 구간(빌드업 Pre-Chorus 등)의
표시를 확인하고, 위 4종 트리거가 워크시트 자유 입력 없이 자동
생성되는지 확인한다.

**Then** 재매핑·삽입된 구간 전부에 "감독 확인" 표시가 명시적으로
붙어 있다(REQ-009). 4종 트리거는 감독이 워크시트에 직접 적지 않는 한
자동 생성되지 않는다(REQ-010) — 빈 트리거 필드가 정상 상태다.

## AC-LDDESIGN-029 — 워크시트 4구획 스키마 필드 존재 (검증: REQ-LDDESIGN-011, REQ-LDDESIGN-012, REQ-LDDESIGN-013, REQ-LDDESIGN-014, REQ-LDDESIGN-015)

**Given** 최소 구성 워크시트 YAML 하나(팔레트 4칸 · 컨셉 인과 문장 ·
구간 줄 1개 · 원샷 줄 1개 · 메모).

**When** 워크시트 로더가 이 파일을 파싱한다.

**Then** `palette`(4칸: primary/secondary/climax/reserved, REQ-012),
`concept`(인과 문장 필드, REQ-013), `sections`(각 줄이 section/
occurrence/trigger/operation/memo를 가짐, REQ-014), `sections.
one_shots`(shot/anchor_section/anchor_occurrence/at, REQ-015),
`notes` 4개 최상위 구획이 전부 파싱 결과에 존재한다(REQ-011).

## AC-LDDESIGN-030 — 큐 모델 v2 필드 7종 전부 채워짐 (검증: REQ-LDDESIGN-017, REQ-LDDESIGN-018, REQ-LDDESIGN-019, REQ-LDDESIGN-020, REQ-LDDESIGN-022, REQ-LDDESIGN-023, REQ-LDDESIGN-024, REQ-LDDESIGN-025)

**Given** 조립된 임의 구간 큐 하나(`restore` 동작을 포함하는 후렴 큐).

**When** 그 큐의 7개 필드(`layer`/`operation`/`tracking`/`timing`/
`evidence`/`headroom`/`mib`)와, `restore` 동작이 색을 포함해 복원하는지
확인한다.

**Then** 7개 필드가 전부 값을 갖는다(REQ-017). `layer`는 5종 중
1개 이상(REQ-018), `operation`은 9종 중 하나(REQ-019)다. `restore`
동작은 디머·색·모션을 함께 복원하고 포지션은 제외한다(REQ-020).
`evidence`는 4등급 중 하나(REQ-022), `description`은 자동 생성돼
있다(REQ-023). `timing`은 `kind`/`seconds`/`attr_split`/`stagger`를
갖는다(REQ-024). `headroom`은 §3.8의 4축 계산 결과를 담는다(REQ-025).

## AC-LDDESIGN-031 — Color Strip은 프레이즈·원샷 큐를 포함하지 않는다 (검증: REQ-LDDESIGN-026, REQ-LDDESIGN-033)

**Given** 팔레트 4칸이 채워진 워크시트.

**When** Color Strip 산출 대상이 구간 큐로만 한정되는지 확인한다
(REQ-026, REQ-033).

**Then** Color Strip은 프레이즈·원샷 큐를 포함하지 않는다(REQ-026,
033).

## AC-LDDESIGN-032 — 3층 밀도 나머지(레이어 제한·원샷 분리·밀도 근거) (검증: REQ-LDDESIGN-036, REQ-LDDESIGN-038, REQ-LDDESIGN-039, REQ-LDDESIGN-040)

**Given** 원샷 4개 이상, 프레이즈 큐 2개 이상을 포함하는 곡(Rain 또는
동급 픽스처).

**When** 큐 밀도가 분할 단위가 아니라 트리거로 정해지는지(REQ-036),
Outro 직전 눈 리셋 큐가 삽입됐는지(간격 3마디 이상일 때, REQ-038),
프레이즈 큐가 레이어 1~2개만 바꾸는지(REQ-039), 원샷이 시퀀스 큐
목록과 분리된 별도 레인에 있고 `evidence`/`headroom` 계산에서
제외되는지(REQ-040) 확인한다.

**Then** 시퀀스 큐 생성 근거가 전부 "워크시트 트리거 한 줄"이지
마디 수 기계 분할이 아니다(REQ-036). Outro 진입 조건을 만족하는 곡은
눈 리셋 큐가 정확히 1개 있다(REQ-038, 조건 미충족 곡은 n/a). 프레이즈
큐는 레이어 1~2개만 바꾼 흔적이 있다(REQ-039). 원샷은 시퀀스 큐
목록에 나타나지 않고 G13 큐 수 집계에서도 제외된다(REQ-040).

## AC-LDDESIGN-033 — §4 회차 규칙 나머지(모션 분배·밀도 상한·6회 이상 정상) (검증: REQ-LDDESIGN-045, REQ-LDDESIGN-046, REQ-LDDESIGN-049)

**Given** 후렴 4회 이상인 곡(Too Cool·Cut and Run 등)과 Bridge 구간이
있는 곡.

**When** 4회차 이후 후렴당 프레이즈 큐 수(REQ-045), Bridge 큐가
`remove`로 KEY·BACK 외 그룹을 끄고 남은 그룹을 30%로 축소했는지
(REQ-046), 후렴 6회 이상 곡에서 상승 축이 소진된 뒤 상태 유지가
경고로 잡히지 않는지(REQ-049) 확인한다.

**Then** 4회차 이후 후렴당 프레이즈 큐는 최대 1개다(REQ-045). Bridge
큐는 KEY·BACK만 남기고 30% 수준으로 축소돼 있다(REQ-046, Bridge 없는
곡은 n/a). 후렴 6회 이상 곡에서 상태 유지가 결함으로 잡히지 않는다
(REQ-049, 후렴 6회 미만 곡은 n/a).

## AC-LDDESIGN-034 — 생성기는 M2 완료 전에는 마운트되지 않는다 (검증: REQ-LDDESIGN-087)

**Given** M2(큐 모델 v2 그룹 스코프)가 미완료인 빌드.

**When** 런북 모드에서 PLAN CUE 카드를 연다.

**Then** PLAN CUE 수정요청 생성기 UI는 마운트되지 않고, 카드는
REQ-083 문언 그대로(하단 3줄 + `Q###` 배지) 읽기 전용에 머문다. M2
완료 이후 빌드에서는 같은 조작으로 생성기가 마운트된다(UI 리뷰
항목 — 컴포넌트 존재 여부 스냅샷).

## AC-LDDESIGN-035 — 다중 선택 + 혼합 표시 (검증: REQ-LDDESIGN-088)

**Given** 값(밝기 또는 색)이 서로 다른 기구 그룹 2개 이상.

**When** 두 그룹을 동시에 선택한다.

**Then** 밝기·색 필드는 "혼합"(단일 축 차이) 또는 "혼합 2색"(색상
차이) 라벨로 표시된다 — 특정 값 하나로 뭉뚱그려 표시되지 않는다.

## AC-LDDESIGN-036 — 콘솔 반영 값 패널의 프리셋 이름 저장·표시 (검증: REQ-LDDESIGN-089)

**Given** 동일한 딤머 값(예: 90%)을 갖지만 이름이 다른 두 프리셋
(`1.18 Dim 90`과 다른 다이내믹 프리셋).

**When** 프리셋 풀 팝업에서 하나를 선택해 딤머 행에 반영한다.

**Then** 딤머 행에는 값이 아니라 **선택한 프리셋 이름**이 표시되고,
값만으로는 구분되지 않던 두 프리셋이 이름으로 구분된다. 컬러·딤머
선택은 선택된 그룹에만 적용되고, 포지션·이펙트·페이저 선택은 큐
전체에 적용된다.

## AC-LDDESIGN-037 — BLIND 잠금 (검증: REQ-LDDESIGN-090)

**Given** 해제 큐(BLIND 리저브 해제) 이전 시점의 큐.

**When** 기구 그룹 줄에서 BLIND 칩을 클릭한다.

**Then** BLIND는 선택되지 않고 잠금 표시(비활성 스타일)를 유지한다.
해제 큐 이후에는 같은 클릭으로 정상 선택된다.

## AC-LDDESIGN-038 — 변경 스택 상태 라벨 + 항목별 경고 병기 (검증: REQ-LDDESIGN-091)

**Given** 감독이 생성기에서 밝기 1항목과 색 1항목을 바꾸고, 그중 색
변경이 규칙 위반(예: 리저브 위반)을 유발한다.

**When** 변경 스택을 렌더한다.

**Then** 스택 헤더(또는 상단)에 "바꾼 것 2 — 코파일럿 확인 대기" 류
상태 라벨이 보이고, 두 diff 줄이 개별 표시되며(`~ 필드 이전값 →
이후값` 형식), 경고 문장은 색 변경 diff 줄에만 병기된다 — 스택
하단에 별도로 모아 쓰지 않는다. `코파일럿에게 반영 요청`을 누른
직후에도 라벨은 "반영됨"으로 바뀌지 않고 "확인 대기"를 유지한다
(요청·수락·반영 3상태가 구분된다).

## AC-LDDESIGN-039 — 생성기와 파서가 같은 어휘를 공유한다 (검증: REQ-LDDESIGN-092)

**Given** 대표 조작 5가지 — 그룹 다중 선택 + 밝기, 색, 프리셋, 페이드,
트래킹(Fade/Track) 각 1건씩.

**When** 생성기가 각 조작에서 만든 요청을 기존 파서
(`parse_cue_sheet_edit_request`, `server/design/cue_sheet_edit.py`)에
통과시킨다.

**Then** 5건 전부 기대한 `changes` 키·값이 나온다 — 생성기가 `changes`
매핑을 직접 만들어 파서를 우회하는 코드 경로는 존재하지 않는다(정적
검사: 생성기 모듈이 `apply_cue_sheet_edit`을 파서 결과 없이 직접
호출하지 않는다).

## AC-LDDESIGN-040 — 파생 경고 6종, 재사용 대상은 재계산하지 않는다 (검증: REQ-LDDESIGN-093)

**Given** 8곡(pilot_baseline) 중 각 경고 조건을 유발하는 큐가 있는
곡들.

**When** PLAN CUE 카드를 생성기로 열어 파생 경고 6종을 계산한다.

**Then** 6개 조건(밝기 역전·팬 폭·리저브 위반·헤드룸<4·MIB live·
페이저=BPM) 중 성립하는 것만 표시되고, 그중 리저브 위반·헤드룸·MIB
live 3종은 REQ-LDDESIGN-027(유보색)·REQ-LDDESIGN-090(BLIND 잠금)·
REQ-LDDESIGN-050·REQ-LDDESIGN-066이 이미 계산한 필드 값을 그대로
소비한다(별도 재계산 로직을 갖지 않는다 — 코드 검사).

## AC-LDDESIGN-041 — 생성기 요청이 대화 기록에 사람이 읽는 문장으로 남는다 (검증: REQ-LDDESIGN-094)

**Given** 감독이 생성기로 요청 하나를 만들어 `코파일럿에게 반영
요청`을 누른다.

**When** 대화 기록(채팅 뷰)을 확인한다.

**Then** 그 요청은 사람이 읽을 수 있는 문장 형태로 나타나며, 감독이
손으로 입력한 요청과 같은 렌더링 경로(같은 채팅 컴포넌트)를 쓴다 —
입력 방식을 구분하는 별도 표시나 별도 승인 경로가 없다(승인 카드는
`onApplyDraft` 한 길로 동일).

## AC-LDDESIGN-042 — "선택 취소"는 서버에 아무것도 보내지 않는다 (검증: REQ-LDDESIGN-095)

**Given** 변경 스택에 아직 전송되지 않은 선택(diff) 항목이 쌓여 있다.

**When** 그 항목의 「선택 취소」 버튼을 누른다.

**Then** `timeline_draft_undo` 프로토콜 메시지가 서버로 전송되지
않는다(네트워크/프로토콜 로그에 해당 메시지 부재로 기계 확인) —
선택 취소와 기존 초안 되돌리기가 같은 핸들러로 묶여 있지 않다.

## AC-LDDESIGN-043 — 한 화면에 "되돌리기" 라벨이 둘 이상 존재하지 않는다 (검증: REQ-LDDESIGN-095)

**Given** 런북 모드 화면(CUE SHEET + PLAN CUE 수정요청 생성기)이
동시에 떠 있다.

**When** 화면의 모든 버튼 라벨을 나열한다.

**Then** 정확한 문자열 "되돌리기"를 쓰는 버튼은 CUE SHEET의
`↶ 되돌리기`(`CueSheetTimeline.tsx:612`) 하나뿐이고, 변경 스택의
취소 버튼은 "선택 취소"로 구분된다(UI 리뷰 항목).

## AC-LDDESIGN-044 — 수락 후 변경 스택이 비고 되돌리기 단계 수가 오른다 (검증: REQ-LDDESIGN-095)

**Given** 변경 스택에 항목 N개가 쌓인 상태에서 「코파일럿에게 반영
요청」을 누르고, 코파일럿이 수락한다.

**When** 수락 응답을 초안에 반영한다.

**Then** 변경 스택은 비워지고, CUE SHEET 배지의 되돌리기 단계 수
(`되돌리기 N단계`, `TimelineDraftHistory.depth` 기반)가 수락 전보다
1 증가한다.

## AC-LDDESIGN-045 — 후렴 3회 이상 곡의 언더페인팅 최소 1회 (검증: REQ-LDDESIGN-028)

**Given** 후렴이 3회 이상인 곡.

**When** 언더페인팅이 최소 1회 나타나는지 확인한다(REQ-028).

**Then** 후렴 3회 이상 곡은 언더페인팅 1회 이상이다(REQ-028, 후렴
3회 미만 곡은 n/a).

## AC-LDDESIGN-046 — 인과 불릿은 요약·재작성 없이 원문 그대로다 (검증: REQ-LDDESIGN-032)

**Given** 컨셉 패널이 노출하는 인과 불릿과 워크시트 `concept` 원문.

**When** 두 값을 바이트 단위로 비교한다(REQ-032).

**Then** 인과 불릿은 요약·재작성 없이 원문과 바이트 동일하다
(REQ-032).

## AC-LDDESIGN-047 — 팔레트 미입력 워크시트는 인터뷰 답변으로 자동 채워진다 (검증: REQ-LDDESIGN-035)

**Given** 팔레트가 비어 있는 워크시트(인터뷰 답변만 있는 경우).

**When** 팔레트가 빈 워크시트에서 인터뷰 답변이 자동 초안으로
채워지는지 확인한다(REQ-035).

**Then** 팔레트 미입력 워크시트는 인터뷰 답변으로 자동 채워진다
(REQ-035).

## AC-LDDESIGN-048 — 빈 제약은 관련 린트를 평가하지 않는다 (검증: REQ-LDDESIGN-034)

**Given** 의상·세트·LED·피부톤 중 하나 이상이 비어 있는 워크시트.

**When** 해당 항목이 비어 있을 때 관련 린트가 평가되는지 확인한다
(REQ-034).

**Then** 제약이 빈 값이면 관련 린트는 평가되지 않는다(안 재고는 안
쓴다, REQ-034).

## AC-LDDESIGN-049 — 컨셉 패널 "한눈에" 5단계 카드가 큐 데이터에서 파생되고 하드코딩 문장이 없다 (검증: REQ-LDDESIGN-097)

**Given** 런북 모드에서 컨셉 패널을 펼친 상태.

**When** "한눈에" 구획의 5단계 카드(시작→쌓기→강조→예고→정점→마무리)
각각의 Q 범위·구간·시간·색 HEX·밝기 범위를 그 곡의 큐 데이터(CUE
SHEET·타임라인과 같은 소스)와 대조하고, 카드 렌더 소스 코드에서
문자열 리터럴로 값이 박혀 있는지 검사한다.

**Then** 5단계 카드 각각의 수치·구간·색 항목(Q 범위·구간·시간·색
HEX·밝기 범위)은 전부 큐 데이터와 일치한다 — 큐 데이터를 바꾸면 카드
값도 같이 바뀐다. 렌더 소스에 하드코딩된 수치·구간명·색 HEX 리터럴이
없다(REQ-097).

## AC-LDDESIGN-050 — 컨셉 패널 탭 라벨 문자열이 고정값과 일치한다 (검증: REQ-LDDESIGN-098)

**Given** 컨셉 패널을 펼친 상태.

**When** "한눈에" 구획 아래 탭 3개의 라벨 텍스트를 읽는다.

**Then** 탭 라벨은 정확히 `이 곡의 연출` / `이 곡의 재료` / `지키는
것·하지 않는 것·아껴 두는 것` 세 문자열이며, 영어 병기(Master
Concept / Micro Concept / Visual Grammar)는 각 라벨보다 작은 보조
표기로만 존재한다(REQ-098).

## AC-LDDESIGN-051 — 빌드 산출물에 웹폰트가 없고 수치 열에 tabular-nums가 적용된다 (검증: REQ-LDDESIGN-099)

**Given** UI 빌드 산출물(`ui/dist` 또는 번들 결과) 및 CUE SHEET·PLAN
CUE 카드·타임라인 소스.

**When** 빌드 산출물에서 웹폰트 파일(`.woff`/`.woff2`/`.ttf`)과 폰트
CDN 링크(`fonts.googleapis.com` 등)를 검색하고, CUE SHEET 수치 열·
PLAN CUE 카드 수치·타임라인 시간 눈금의 CSS를 확인한다.

**Then** 웹폰트 파일도 폰트 CDN 링크도 존재하지 않는다(REQ-099). 위
세 영역의 수치 표시 CSS는 `font-variant-numeric: tabular-nums`를
적용하고 있다.

## AC-LDDESIGN-052 — 변경 스택 항목별 제거 `✕`가 개별 diff 줄만 지운다 (검증: REQ-LDDESIGN-100)

**Given** 변경 스택에 diff 줄 4개가 쌓인 상태.

**When** 그중 한 줄의 `✕`를 누른다.

**Then** 그 줄만 스택에서 사라지고 나머지 3줄은 남는다. 전체 「선택
취소」 버튼은 여전히 스택 전체를 한 번에 비울 수 있다(REQ-095 불변)
— 두 조작(항목별 `✕`, 전체 「선택 취소」)은 서로 다른 핸들러다
(REQ-100).

## AC-LDDESIGN-053 — 자유 입력 한 줄이 REQ-092 경로를 그대로 따른다 (검증: REQ-LDDESIGN-101)

**Given** 변경 스택 하단의 자유 입력 한 줄에 "그리고 이 구간 전체를
반 박자 당겨줘"를 입력한 상태, 선택된 diff 항목 1개 이상.

**When** `코파일럿에게 반영 요청`을 누른다.

**Then** 전송된 요청 문장 끝에 자유 입력 문구가 그대로(해석·변형
없이) 덧붙어 있다. 그 요청은 REQ-092가 정의한 경로(기존 파서
`parse_cue_sheet_edit_request` → `apply_cue_sheet_edit`)를 그대로
거치며, 생성기가 별도 `changes` 매핑을 만들지 않는다(REQ-101).

## Definition of Done

- REQ-LDDESIGN-001~101 전량 PASS 또는 명시적 n/a(구조상 해당 없는 곡,
  §E 자기검증 표) — 개별 추적성은 위 AC-LDDESIGN-001~053의 각 "검증:"
  목록이 담당하며, 이 포괄 문구는 그것을 대체하지 않는다(AC-026~033·
  045~048이 이전에 미인용이던 REQ 53개를, AC-034~044가
  REQ-087~095(9개)를, AC-049~053이 REQ-096~101(6개)을 닫는다 —
  AC-045~048은 AC-031 분리분으로 REQ 커버리지 자체는 이전과 동일하다).
- AC-LDDESIGN-001~020, 025~053 전량 PASS(순수 로컬 계산 —
  `uv run pytest` / Vitest). 특히 AC-025(t429 선행 조건 + bpm 실배선)는
  M1 착수 전 게이트이고, AC-002~013(G2~G13, DinoDino·Ice cream처럼
  구조상 n/a인 게이트는 n/a로 기록, FAIL이 아니다)는 8곡 회귀 기준선을
  오늘 실측치 이하로 떨어뜨리지 않아야 한다. AC-034~044(생성기, M7
  마지막 하위 단계)은 M2 완료 전에는 AC-034(마운트 안 됨)만 PASS
  가능하고 나머지는 M2 완료 이후에만 실행 가능하다. AC-049~053(M7
  확정 사항, §3.16)은 순수 로컬 계산이며 M2 완료 여부와 무관하게
  PASS 가능하다.
- AC-LDDESIGN-021(실기 콘솔 Rain 검증)은 사용자가 명시적으로 요구한
  필수 항목 — 이 AC 없이는 이 SPEC은 완료로 간주되지 않는다.
- AC-LDDESIGN-022~024(B군 프로브 3종)는 PASS/FAIL이 아니라 관측치
  기록이 완료 기준 — 기록이 plan.md §F의 잠정값을 콘솔 실측치로
  교체한다.
- `uv run pytest -q` 전체 스위트 통과, 착수 전 기준선 대비 델타가 이
  SPEC이 더한 신규 시험 수와 정확히 일치.
- `ruff check` / `ruff format --check` clean(Python 계층). UI 계층은
  기존 lint/format 파이프라인(`ui/` 자체 스크립트) clean.
- plan.md §F의 잠정값 3건은 Implementation Kickoff Approval 시점에
  감독 재확인을 거치고, AC-022~024의 프로브 결과로 콘솔 실측치로
  교체된다.
