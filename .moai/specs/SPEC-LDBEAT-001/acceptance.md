# SPEC-LDBEAT-001 — 인수 기준 (Acceptance Criteria)

각 AC는 `AC-LDBEAT-NNN` 형식이며, 가능한 한 기계로 검사한다. 기계로 잴 수 없는 항목은 "인간 판단"으로 명시한다.

## §A AC 매트릭스

| AC | Given | When | Then | 검증 수단 |
|---|---|---|---|---|
| AC-LDBEAT-001 | M1 프로브 중 하나 이상이 FAIL 또는 미실행으로 기록된 상태(`progress.md`) | 사용자가 그 항목에 의존하는 격자 기능의 "콘솔에 반영"을 시도한다 | 전송이 차단되고 "미확인 항목 N개(목록)" 경고가 표시된다 — 콘솔로 어떤 커맨드도 나가지 않는다 | 기계 — 감사 로그 `executed/command` 0건 + UI 경고 렌더 확인 (REQ-LDBEAT-001) |
| AC-LDBEAT-002 | 배치 규칙서 §6의 네 항목 모두 M1 프로브로 PASS 기록된 상태 | 감독이 격자 전송의 승인 파일을 승인한다 | AC-LDBEAT-001의 차단이 해제되고, 승인 파일 경로가 열린다 | 기계 — `progress.md` 항목별 PASS 4/4 읽기 + 전송 버튼 활성 상태 확인 (REQ-LDBEAT-003) |
| AC-LDBEAT-003 | 박자 격자가 렌더된 런북 모드 화면 | 사용자가 격자 블록을 연다 | SCENE / BACK PULSE / SIDE CHASE / MOVER-U MOVE / MOVER-D MOVE / ACCENT 6개 역할 트랙이 4마디 단위 행(0~2, 3~6, 7~10, 11~13, 14~17, 18~21, 22~25)으로 표시된다 | 기계 — DOM/컴포넌트 스냅샷에서 트랙 라벨 6개 + 행 7개 카운트 (REQ-LDBEAT-004·005) |
| AC-LDBEAT-004 | circle 또는 발리후(ballyhoo) 모양이 격자 칸에 선택지로 노출된 상태 | 그 칸이 렌더된다 | "⚠ 실기 미확인" 배지가 그 칸에 함께 렌더된다 | 기계 — 해당 모양 선택지에 미확인 배지 속성/클래스 존재 여부 그렙 (REQ-LDBEAT-010) |
| AC-LDBEAT-005 | 사용자가 격자 칸을 자연어 문장으로 수정 요청한 상태 | 그 문장이 제출된다 | 요청은 **새** 서버측 편집 연산(`apply_beat_grid_edit` 또는 run-phase가 확정하는 이름, `cue_sheet_edit.py`와 나란히 둔 모듈)을 통과하며, UI 소스 전체에서 서버 페이로드를 직접 구성하는 코드가 0건이다 — `parse_cue_sheet_edit_request`/`apply_cue_sheet_edit`(큐 레벨 전용, 마디·역할 어휘 없음)는 격자 요청의 경로가 **아니다** | 기계 — 호출 스택 로그가 새 연산을 거치는지 확인 + `grep -rn "changes\s*=\s*{" ui/src` 0건 + `grep -rn "parse_cue_sheet_edit_request\|apply_cue_sheet_edit" <격자 UI 소스>` 0건(큐 레벨 파서가 격자 경로에 섞여 들어가지 않았는지) (REQ-LDBEAT-007·008) |
| AC-LDBEAT-006 | 감독이 승인한 커맨드 파일과 실제 송신 감사 로그 | 앱 경로로 승격된 승인=송신 비교 로직(REQ-LDBEAT-011, `.moai/reports/t512/approval_vs_sent.py`의 로직을 포팅)을 그 둘에 실행한다 | sha256 동일 + "송신 안 됨" 0건 + "승인 안 됨" 0건 — 이 조건을 모두 만족해야 송신이 PASS로 기록된다. 그 비교 로직은 `.moai/reports/`(gitignore 대상) 밖의 앱 참조 가능 경로에 있다 | 기계 — 승격된 모듈 종료 코드 0 + 출력 파싱 + `import` 경로가 `server/` 아래(또는 run-phase가 정한 앱 경로)인지 확인, `.moai/reports/`를 직접 import하는 코드 0건 (REQ-LDBEAT-011) |
| AC-LDBEAT-007 | LOVE ATTACK이 아닌 다른 곡을 런북 모드에서 연 상태 | 사용자가 박자 격자를 연다 | LOVE ATTACK 전용 기본값(배치 규칙서 §2~§4에서 온 값)이 강제 적용되지 않고, 빈 상태 또는 "이 곡의 기본값 없음" 안내가 표시된다 | 기계 — 다른 곡 fixture로 렌더 시 LOVE ATTACK 기본값 상수가 적용되지 않음을 스냅샷 대조 (REQ-LDBEAT-006) |
| AC-LDBEAT-008 | 감독이 특정 곡에서 격자 기본 배치를 편집하고 저장한 상태 | 다른 곡의 격자를 연다 | 그 편집이 다른 곡에 영향을 주지 않는다(곡 단위로 저장됨) | 기계 — 저장 키에 곡 식별자가 포함되는지 + 교차 곡 비오염 테스트 (REQ-LDBEAT-006) |
| AC-LDBEAT-009 | 타임코드 하나에 이미 트랙 2개가 있는 콘솔 상태(t516 기준선) | M1 프로브 ①(트랙 3개 이상)이 실행된다 | 결과(성공/거절)가 `progress.md`에 기록되고, 거절이면 그 항목에 의존하는 UI 요소는 계속 "미확인" 상태를 유지하며 대안(예: 2트랙 이하 구조)이 경고로 함께 기록된다 | 기계 + 감독 관찰 — 되읽기 결과 기록 + UI 상태 플래그 대조 (REQ-LDBEAT-001·002·003) |
| AC-LDBEAT-010 | 그룹 스코프 없는 범위 불명 편집 요청(예: 값이 범위를 벗어난 조도 지정) | 그 요청이 새 서버측 편집 연산(REQ-LDBEAT-007~008)에 전달된다 | 그 연산이 선언한 새 화이트리스트·값 범위 검증(REQ-LDBEAT-008의 역할/모양/속도·축 범위, `cue_sheet_edit.py`의 부분 적용 금지·단일-원인 거절 패턴을 본뜬 것)이 적용되어 거절되며, 거절 사유 문자열이 그대로 UI에 노출된다 — 부분 적용(일부 필드만 쓰고 나머지 무시) 0건 | 기계 — 새 연산의 예외 메시지와 UI 표시 문자열 동일성 대조 + 거절 시 격자 상태 변경 0건 확인 (REQ-LDBEAT-007·008) |
| AC-LDBEAT-011 | M1~M6(§E) 전체가 완료된 상태 | 전체 REQ 체크리스트(REQ-LDBEAT-001~014)를 검토한다 | 모든 REQ가 추적 가능한 PASS/FAIL 상태를 가지며, FAIL 항목은 0건이거나 명시적으로 PASS-WITH-DEBT로 기록된다. REQ-LDBEAT-013의 새 에미터 하위 작업이 "감독 미확인"으로 생략된 경우, 그 생략과 대안 결정이 `progress.md`에 기록돼 있어야 FAIL이 아닌 것으로 집계된다 | 기계 — `progress.md` §E 평가 매트릭스 완전성 검사 (전체 REQ) |
| AC-LDBEAT-012 | 기존 `emit.py`의 `PLAYBACK_MODES`와 `CueSheetTimeline` 재생 경로(변경 없음 확인) | 그 두 파일/경로의 diff를 run-phase 종료 시점에 대조한다 | `PLAYBACK_MODES = ("manual_go", "trig_time")`와 `CueSheetTimeline`의 재생 호출 로직에 diff 0줄이다 — (조건부로 신설되는) 박자 격자 전용 새 에미터는 **별도 모듈**에만 존재하고 이 두 파일을 수정하지 않는다 | 기계 — `git diff <base>..<head> -- server/director/emit.py ui/src/components/CueSheetTimeline.tsx` 0줄 확인 (REQ-LDBEAT-013) |
| AC-LDBEAT-013 | 스피드 마스터 BPM 설정 UI | 그 UI가 렌더된다 | "자동 설정" 문구나 자동 적용 버튼이 없고, "사람이 콘솔에서 직접 설정" 안내가 표시된다 | 기계 — 해당 UI 컴포넌트 텍스트/속성 그렙 (REQ-LDBEAT-014) |

## §B 엣지 케이스

- **M1 프로브 부분 PASS**: 4항목 중 2개만 PASS일 때, M4(송신 와이어링)는 그 2개에만 의존하는 기능만 활성화하고 나머지 2개에 의존하는 기능은 비활성 상태를 유지해야 한다(AC-LDBEAT-009와 같은 패턴을 네 항목 전부에 적용).
- **곡 전환 중 미저장 편집**: 감독이 LOVE ATTACK에서 격자를 편집하다가 다른 곡으로 전환하면, 미저장 편집은 LOVE ATTACK 쪽에 남아 다른 곡으로 새지 않아야 한다(AC-LDBEAT-008의 변형).
- **그룹 스코프 편집 + 미확인 모양 조합**: "MOVER-U만 circle로"처럼 그룹 스코프(REQ-LDBEAT-009)와 미확인 모양(REQ-LDBEAT-010)이 같은 요청에 섞이면, 미확인 배지가 먼저 뜨고 M1 프로브 ④가 PASS이기 전에는 전송이 차단된다(AC-LDBEAT-001과 AC-LDBEAT-004의 교차).

## §C 인간 판단 항목 (기계로 검사하지 않음)

- **격자의 "읽기 쉬움"**: 6개 역할 트랙 × 7개 행이 한눈에 들어오는지는 감독 육안 검토로 판정한다. 열 너비·색 대비·스크롤 UX는 AC의 PASS/FAIL 대상이 아니다.
- **M1 프로브 ②·③·④의 "깜박임/혼선 없음" 감독 관찰**: 큐 Part 크기 증가나 되읽기만으로는 실제 눈에 보이는 결과를 대신할 수 없다 — t520 §20-4가 이미 "+ 감독 눈"을 병기한 이유와 같다. 기계 측정은 사전 체(pre-filter)일 뿐, 최종 PASS는 감독 관찰이 결정한다.
- **곡별 기본값의 "음악적으로 적절함"**: 배치 규칙서 §2~§4의 LOVE ATTACK 기본값이 실제로 그 곡에 어울리는지는 이미 감독이 §5에서 확정했다 — 이 SPEC의 범위는 그 값을 정확히 옮기는 것이지, 재평가하는 것이 아니다.

## §D Definition of Done

- [ ] REQ-LDBEAT-001~014 전부 `progress.md`에 PASS/FAIL로 기록됨(AC-LDBEAT-011).
- [ ] M1 프로브 4항목(타임코드≥3트랙/단일 그룹 선택 페이저 저장/속성 겹침/circle·발리후) 각각의 결과가 기록됨 — 전부 PASS가 아니어도 되지만, FAIL/미실행 항목에 의존하는 기능은 비활성 상태로 커밋됨.
- [ ] 격자 편집이 새 서버측 편집 연산을 거치고, 로컬 서버-페이로드 구성 0건으로 확인됨(AC-LDBEAT-005) — 큐 레벨 파서(`parse_cue_sheet_edit_request`)가 격자 경로에 쓰이지 않음.
- [ ] 승인=송신 비교 로직이 앱 참조 가능 경로로 승격돼 PASS(AC-LDBEAT-006), 신규 비교 **로직** 0개(승격은 로직 재작성이 아니다).
- [ ] 코파일럿 메인 화면(`App.tsx` 메인 분기) + `server/director/emit.py` + `CueSheetTimeline.tsx` 재생 로직 diff 0줄(AC-LDBEAT-012).
- [ ] Implementation Kickoff Approval 라운드에서 REQ-LDBEAT-013의 새 에미터 권고가 감독에게 명시적으로 제시·확인됐음이 `progress.md`에 기록됨(채택이든 보류든).
- [ ] M2에서 격자 저장소 결정(REQ-LDBEAT-006의 임베드 권고 채택 여부)이 `progress.md`에 명시적으로 기록됨.
- [ ] 감독 Implementation Kickoff Approval 기록 이후에만 run-phase 커밋이 존재함.

## §E 품질 게이트 기준

- TRUST 5 중 Tested — 격자 렌더/편집 경로/승인=송신 재사용 각각에 최소 1개 이상의 테스트.
- TRUST 5 중 Secured — 서버 `changes` 경로 우회 0건(AC-LDBEAT-005/010)을 보안·데이터 무결성 관점으로도 겸해 본다(임의 UI 입력이 서버 검증을 건너뛰지 않는지).
- 콘솔 쓰기를 수반하는 모든 테스트/프로브는 승인=송신 비교(REQ-LDBEAT-011)를 통과해야 "완료"로 집계된다 — 가짜 콘솔 리허설 PASS만으로는 완료로 집계하지 않는다(t516/t519/t520의 선례와 동일한 기준).
