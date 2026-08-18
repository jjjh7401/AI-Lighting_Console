# 구현 계획 — Position 프리셋 덮어쓰기 가드

base `jjjh7401/MAcopilotpos` HEAD = `f5cfe15` · Tier **M** · 개발 방식 **TDD**(`quality.yaml` `development_mode: tdd`)

> **라이브 콘솔 불필요.** 새 MA3 문법 0건(REQ-PRESETGUARD-019). 하드웨어 세션을 잡지 않는다.

## A. 리뷰 순서 (읽는 사람을 위한)

1. **`spec.md` §A.2(가드가 뒤집힌 형상) · §A.5(카드 하나, 호출자 둘)** — 이 둘이 설계 전체를 규정한다. §A.5를 건너뛰면 확인 카드를 둘로 나누는 구현이 나오고, 그러면 한쪽만 fail-closed가 되는 드리프트가 생긴다.
2. `spec.md` §B.1 REQ-001의 **"출처 무관"** 조항 — 브리핑은 *"명시 번호 경로"* 라 했으나 실측 결과 **자유 입력 경로도 동일하게 무방비**다(§C.1 아래). 가드의 **위치**가 이 조항으로 결정된다.
3. `spec.md` §B.2 REQ-009(`proposal` 분류) — 이 조항이 없으면 되읽기가 정상 워크플로에서 상시 거짓 경보를 낸다.
4. 본 문서 §C(M0 결정 3건) → §B(M1~M5) → §E(위험)
5. `acceptance.md` §B(AC 14건 — 뮤테이션 필수 **7건**)

## B. 마일스톤

각 마일스톤은 RED → GREEN → REFACTOR 1사이클이며, 커밋 1건 이상을 남긴다.

### M0 — 결정 확정 및 기준선 재실측 (코드 변경 0)

- §C의 결정 3건을 확정한다(대부분 이미 결정됨 — 문서 확인만).
- **기준선을 다시 측정한다.** plan-phase 수치 재사용 금지.
  - plan-phase 실측(2026-08-16, 오케스트레이터 직접 측정): `uv run pytest server/tests -q` → **8861 passed · 8 skipped** (141.26s)
  - `uv run ruff check server/` → **2 errors** (E501, `server/safety/console.py` — **선재 결함, 우리 것 아님. 그대로 둔다**)
- ASSUMPTION-83(트리거 오발 충돌)은 **plan-phase에서 이미 판정됐다 — 반증(충돌 실재)**. M0는 후보 문장 코퍼스를 M3용으로 확정하기만 한다.

**산출**: 커밋 없음(또는 progress.md §E.2.0 전제 검증 행만).

### M1 — 확인 카드 · 점유 판정 (REQ-001~005)

**신설 심볼** (전부 `server/web/session.py`):

- `_position_preset_span_collisions(start_no) -> tuple[list[int], str] | None`
  구간 `start_no … start_no+9` 중 점유된 슬롯 번호 목록 + 판독 상태. 풀 판독 `None`이면 `None` 반환(미상).
- `_confirm_preset_span_overwrite(start_no, *, intent) -> PresetSpanVerdict`
  **공용 카드**. `intent`는 문면만 바꾸고 판정 로직은 동일하다(§A.5).

**판정 5상태** — 이것이 설계의 중심이다:

| 상태 | 조건 | 진행? | 회신 의무 |
|---|---|---|---|
| `clear` | 풀 판독 성공 · 충돌 0 | ✅ 조용히 | 없음 |
| `unverified` | 풀 판독 `None` | ✅ 진행 | **점유 미확인 명시**(REQ-004) |
| `confirmed` | 충돌 있음 · 운영자 승낙 | ✅ 진행 | 덮어쓴 슬롯 열거 |
| `declined` | 충돌 있음 · 운영자 거절 | ❌ 중단 | 사유 |
| `unanswered` | 충돌 있음 · `_ask_one` → `None` | ❌ **중단** | **무응답 = 미승인** 명시(REQ-003) |

> **`unverified`와 `clear`는 절대 병합하지 않는다.** 둘 다 진행하지만 회신 문면이 다르다. 병합하면 판독 실패가 *"검사했고 비어 있었다"* 로 위장된다 — 이 SPEC이 닫으려는 결함과 같은 형상이다.

**가드의 배치**: `start_no <= 0` 검사(`session.py:2860` 부근) **직후**, `basic_position_presets(fixtures)` 호출 **직전**. if/else 갈래 **밖**이다(REQ-001 출처 무관 조항).

**RED**: 명시 번호 충돌 리그에서 `run_commands` 0건 · 카드 프롬프트에 충돌 슬롯 번호 · `unanswered` 리그에서 쓰기 0건.

### M2 — 저장 되읽기 (REQ-006~010)

**신설 심볼**:

- `_verify_preset_span_stored(expected: dict[int, str], outcomes) -> str`
  루프 종료 후 **1회** 풀 재판독 → 대조 → 회신에 붙일 산술 문장 반환.

**분류 3구간**:

| 구간 | 판정 | 문면 예 |
|---|---|---|
| 게이트 통과(`ok`) + 풀에 존재 | **확인** | `2.21–2.30 중 10개 확인` |
| 게이트 보류(`proposal`/`locked`/`blocked`/`rejected`) | **미착지 — 결함 아님**(REQ-009) | `2.24 승인 대기 — 승인 후 반영` |
| 게이트 통과 + 풀에 부재 | **미확인** | `2.27 미확인` |
| 재판독 `None` | **전건 미검증**(REQ-008) | `저장 결과를 확인하지 못했습니다 — 풀 판독 실패` |

**RED**: 산술 문장 존재 · 재판독 실패 리그에서 *"확인"* 문면 부재 · `proposal` 리그에서 미확인 경보 부재.

### M3 — 재생성 경로 (REQ-011~014)

**신설**: `_REGENERATE_POSITIONS_REQUEST` 정규식 + `_regenerate_position_presets(text)` 핸들러.

- 디스패치 등록은 **`_basic_position_presets`보다 앞**에 둔다(재생성 문장이 신규 저장 트리거에 **실제로 걸리므로** — ASSUMPTION-83 반증, REQ-015). 기존 트리거는 **무변경**이다.
- 좌표 판독 → `_position_preset_ready_starts()` → 후보 0/다수면 질문(REQ-013) → **M1의 같은 카드** → `basic_position_presets(fixtures)` 재계산 → M1/M2와 동일한 저장 루프 + 되읽기.
- 저장 루프는 `_basic_position_presets`와 **공유 헬퍼로 추출**한다(중복 구현 금지 — 두 경로가 갈라지면 안전 동작 한쪽만 퇴행한다).

**RED**: 기존 구간 표적 · 같은 카드 통과 · `unanswered`에서 쓰기 0건 · 큐/시퀀스 명령 부재 · **겹치는 문장이 재생성으로 라우팅**(+ 신규 저장 문장은 여전히 신규 저장으로 — 양방향).

### M4 — 회귀 · 경계 봉쇄

- 기존 3건(`TestBasicPositionPresets`) 무회귀 확인. **특히** `test_an_explicit_start_number_skips_the_question` — 스텁 레지스트리가 `query_state`에 `"{}"`를 돌려주므로 풀 판독이 `None`(미상)이 되어 `unverified` 갈래를 타고 **카드 없이 진행**한다. `channel.asked == []` 단정은 그대로 성립하나 **회신 문면이 바뀐다**. 이 테스트가 문면을 단정하지 않는지 확인하고, 필요하면 `unverified` 리그임을 명시하도록 **보강**한다(약화 아님).
- byte-diff: `server/spatial/**` · `server/orchestrator/tools.py` · `server/safety/**` 변경 0.
- 전체 스위트 + `ruff check` + `ruff format --check`.

### M5 — 커밋 · 푸시

Tier M → Hybrid Trunk 규율에 따라 `manager-develop`이 직접 커밋·푸시한다. Conventional Commits · `--no-verify` 금지.

## C. M0 결정

### M0.1 — 가드의 배치: if 갈래 안인가 밖인가 → **밖(확정)**

브리핑은 결함을 *"명시 번호 경로에 가드가 없다"* 로 기술했다. **실측 결과 그보다 넓다**: else 갈래의 질문 카드도 `_ask_one`을 통하고, `_ask_one`은 **자유 입력을 항상 제공한다**(`session.py:6060` 독스트링). 운영자가 제안 버튼 대신 번호를 타이핑하면 `int(re.search(r"\d+", answer).group(0))`(`:2856`)이 그 값을 그대로 받는다 — **명시 번호 경로와 동일하게 무방비**다.

→ 가드는 `start_no`가 **확정된 지점**에 놓인다. 검증된 제안 버튼을 고른 경우는 충돌 0이므로 `clear`로 통과하며 **추가 카드가 뜨지 않는다**(REQ-005). 즉 이 배치는 마찰을 늘리지 않고 구멍만 닫는다.

### M0.2 — 카드는 하나인가 둘인가 → **하나(확정)**

`spec.md` §A.5. 두 호출자(REQ-1 사고 방지 / REQ-3 의도된 덮어쓰기)가 같은 판정 로직을 공유하고 `intent` 인자로 문면만 분기한다. 근거: 카드를 나누면 fail-closed 규칙이 두 곳에 복제되고, 한쪽만 갱신되는 드리프트가 이 저장소에서 이미 관측된 실패 형상이다(TRUNCATE `spec.md` §A.4 — 플래그를 실어 보냈으나 소비자가 읽지 않은 사례).

### M0.3 — `unanswered`의 처리 → **fail-closed(확정)**

`_ask_one` → `None`은 저장하지 않는다. 근거: `None`은 UI 미연결 **또는** 무응답이며, 둘 다 *"운영자가 승낙했다"* 의 증거가 아니다. 기존 시작 번호 카드가 `None`에서 거부하는 선례가 이미 있다(`session.py:2862~2866` — `"시작 프리셋 번호를 받지 못해 저장을 시작하지 않았습니다"`). **본 SPEC은 그 선례를 확장할 뿐 새 규율을 만들지 않는다.**

## D. 파일별 변경 계획

| 파일 | 변경 | 근거 |
|---|---|---|
| `server/web/session.py` | 신설 헬퍼 3~4 · `_basic_position_presets` 개정 · 재생성 핸들러 + 정규식 신설 · 디스패치 등록 | REQ-001~014 |
| `server/tests/test_web_session.py` | `TestBasicPositionPresets` 확장 · `TestPositionPresetRegeneration`(신설) | AC 전건 |
| `server/tests/test_spatial_pointing.py` | **무변경 예상** — 기하 계층 불변(REQ-016) | PRESERVE |
| `server/spatial/**` | **무변경** | REQ-016 |
| `server/orchestrator/tools.py` | **무변경** | REQ-017 (hunk 핀 트립와이어) |

예상 규모: **2파일 · 400~700 LOC** → Tier M 범위(300~1000 LOC · 5~15 파일) 하단.

## E. 위험

1. **트리거 오발 충돌 — 가설이 아니라 측정** (ASSUMPTION-83 **반증됨**) — *"기본 포지션 다시 잡아줘"* 가 `_BASIC_POSITIONS_REQUEST`(`기본.{0,16}?포지션.*?(저장|만들|잡아|생성)`)에 **실제로 걸린다.** `잡아`가 이미 그 대안에 있다. 2026-08-16 직접 실행: 후보 4문장 전건 `True`. **완화**: 교집합 공집합화는 **불가능**(기존 트리거를 좁혀야 하고 그것은 파괴적 변경 — spec.md D-3). 대신 재생성 핸들러를 디스패치 순서에서 **먼저** 두고, 겹치는 문장의 **행선지**를 AC-011이 양방향으로 고정한다. 이것이 M3의 최대 리스크다.
2. **저장 루프 중복 구현** — `_basic_position_presets`와 재생성이 각자 루프를 가지면 안전 동작(룩별 번들 · ClearAll · 라벨)이 한쪽만 퇴행한다. **완화**: M3에서 공유 헬퍼로 추출하고, 두 경로 모두에 같은 회귀 단정을 건다.
3. **`proposal` 상시 경보** — REQ-009를 빠뜨리면 승인 게이트가 켜진 정상 환경에서 되읽기가 언제나 *"미확인"* 을 낸다. 그 경보는 무시되고, 무시되는 경보는 진짜 미착지를 가린다. **완화**: AC-009가 이를 직접 단정한다.
4. **기존 테스트의 조용한 통과** — M4가 지적한 대로 스텁이 `"{}"`를 돌려주므로 새 가드가 `unverified` 갈래로 빠져 **가드가 없어도 기존 테스트가 통과한다**. **완화**: 새 AC는 전부 **판독 성공 리그**를 명시 구성한다. 스텁 기본값에 의존하는 AC는 무효다.
5. **풀 판독 왕복 증가** — 가드 1 + 되읽기 1 = 최대 2왕복 추가. 저장 10회 대비 무시 가능(§C.1). 재생성은 `ready_starts` 판독을 가드와 **공유**해 1왕복으로 접는다(`_position_preset_ready_starts(slots=...)`가 이미 그 인자를 받는다).

## F. 검증 절차 (run-phase 완료 시)

```bash
uv run pytest server/tests -q                      # 8861 + 신규, 회귀 0
uv run pytest server/tests/test_web_session.py -q  # 표적 스위트
uv run ruff check server/                          # 선재 2건 외 신규 0
uv run ruff format --check server/
git diff --stat -- server/spatial/ server/orchestrator/tools.py server/safety/   # 비어 있어야 함
```

## G. 인계 계약

run-phase 진입 전 필요한 것: **없음**(라이브 콘솔 불필요 · 사용자 결정 대기 없음). §F의 열린 결정 2건은 **에이전트 판단 가능**으로 분류되며 킥오프에서 사용자가 뒤집을 수 있다.
