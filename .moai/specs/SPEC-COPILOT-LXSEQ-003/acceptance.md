# SPEC-COPILOT-LXSEQ-003 — 인수 기준 (acceptance)

Tier M · AC **14건**(실기 1건 포함, 상한 16).
SSOT 는 이 문서다 — REQ 는 `spec.md` §D, 마일스톤은 `plan.md` §B 를 본다.

---

## A. 검증의 축

| 축 | 내용 | 왜 축인가 |
|---|---|---|
| ① 열 집합 무추측 | 세 종류는 **정확 열 집합**으로만 갈린다. 파일 이름·확장자로 가르지 않는다 | 포함 검사로는 `col` 과 `bm` 이 안 갈린다 — `AC-FILEARG-018` 이 그 대조군을 이미 명시했다 |
| ② 어긋나면 0건 | 풀·슬롯이 어긋나면 계획을 내지 않는다 | 부분 계획이 최악이다. 반쯤 맞는 프리셋이 쇼파일에 남고, 다음 단계(큐)가 그것을 참조한다 |
| ③ 단일 쓰기 경로 | 쓰기는 `run_commands` 위임뿐. `server/lxseq/` 에 쓰기 수단 0 | 001·002 의 축 승계. t68 이 「툴 경유는 그 한 문뿐」을 확인했다 |
| ④ 등급 정직성 | **값 일치는 미측정**이라 적는다. 단정하지 않는다 | 슬롯 점유는 읽히고 값은 안 읽힌다(t68 §2.7). 그룹 멤버십에서 이미 값을 치른 실패 형태다 |
| ⑤ 상한을 안전 근거로 쓰지 않음 | 바이트 상한을 판정에 쓰지 않고, 대신 실패를 fail-fast 로 잡는다 | 거절 축이 길이가 아니다(t72: 2044B 거절·2080B 통과). 「짧으니 안전」은 근거 없는 안심이다 |

---

## B. 대표 시나리오 (Given-When-Then)

**Given** 정본 `preset-col.csv`(8행)와 빈 슬롯이 8개 이상인 콘솔,
**When** 운영자가 그 시트를 툴에 넣고 승인하면,
**Then** 8건이 콘솔이 답한 빈 슬롯에 저장되고, 산출물이 **RIG ID ↔ 슬롯 대응표**와
**「값 일치는 되읽지 못했다」는 한 줄**을 함께 싣는다.

**Given** 같은 시트와 빈 슬롯이 3개뿐인 콘솔,
**When** 같은 절차를 밟으면,
**Then** **0건이 저장되고** 대조표(필요 8 · 가용 3)가 보고된다. 3건만 넣지 않는다.

---

## C. 인수 기준

### C.0 역추적표

| REQ | 커버 AC | M |
|---|---|---|
| (M0 계약 확인) | AC-LXSEQ3-001 | M0 |
| REQ-LXSEQ3-001 | AC-LXSEQ3-002 | M1 |
| REQ-LXSEQ3-002 | AC-LXSEQ3-003 | M1 |
| REQ-LXSEQ3-003 | AC-LXSEQ3-004 | M1 |
| REQ-LXSEQ3-004, REQ-LXSEQ3-005 | AC-LXSEQ3-005 | M1 |
| REQ-LXSEQ3-006 | AC-LXSEQ3-006 | M2 |
| REQ-LXSEQ3-007 | AC-LXSEQ3-007 | M2 |
| REQ-LXSEQ3-008 | AC-LXSEQ3-008 | M2 |
| REQ-LXSEQ3-009 | AC-LXSEQ3-009 | M2 |
| REQ-LXSEQ3-010 | AC-LXSEQ3-013 | M2 |
| REQ-LXSEQ3-011 | AC-LXSEQ3-010 | M3 |
| REQ-LXSEQ3-012 | AC-LXSEQ3-011 | M3 |
| REQ-LXSEQ3-013 | AC-LXSEQ3-012 | M3 |
| REQ-LXSEQ3-014 | AC-LXSEQ3-014 | M2·M3 |
| REQ-LXSEQ3-015 | AC-LXSEQ3-013 | M4 |
| REQ-LXSEQ3-016 | AC-LXSEQ3-001 | M0 |

### AC-LXSEQ3-001 — 계약 정합 판정이 문서에 있다 (M0)

**Given** 착수 전 트리, **When** `spec.md` §A.3 을 읽으면, **Then** ① REQ-FILEARG-017 과 3행의 정합 판정이
근거 셋과 함께 있고 ② FILEARG-001 문면 정정이 **별건 처방**으로 분리돼 있다.

**검증**: `grep -c "REQ-FILEARG-017" .moai/specs/SPEC-COPILOT-LXSEQ-003/spec.md` ≥ 1 이고,
§A.3 이 「판정」과 「처방」을 각각 명시할 것.

### AC-LXSEQ3-002 — 세 시트가 정확 열 집합으로 읽힌다 (M1)

**Given** 정본 3종, **When** 파서에 넣으면, **Then** dim 6행 · col 8행 · bm 5행 = **19 레코드**가 나온다.

**비공허성(필수)**: 열 하나를 바꾼 헤더(예: `Level` → `Lvl`)를 넣으면 **반드시 거부**되어야 한다.
통과하면 파서가 열 집합을 재고 있지 않다는 뜻이므로 AC 미충족.

### AC-LXSEQ3-003 — `preset-pos` 는 어느 서명에도 맞지 않는다 (M1)

**Given** 정본 `preset-pos.csv`, **When** 판별기에 넣으면, **Then** `unknown_sheet_kind` 이며
matched 가 빈 튜플이다. **그리고** `grep -rn "preset-pos" server/lxseq/ server/sheets/` 가 **빈 출력**이다.

### AC-LXSEQ3-004 — ID 접두 불일치 행은 거부되고 보고된다 (M1)

**Given** `preset-col.csv` 의 한 행 ID 를 `BM.99` 로 바꾼 사본, **When** 파서에 넣으면,
**Then** 그 행이 거부되고 **거부 사유와 행 번호가 보고**된다. 조용히 건너뛰지 않는다.

### AC-LXSEQ3-005 — 산문 열도 그룹 이름도 해석되지 않는다 (M1)

**Given** `Purpose` 가 「풀 100%」처럼 값처럼 읽히는 행과 `TargetGroup` 이 `MOVER-ALL` 인 bm 행,
**When** 파서에 넣으면, **Then** ① `Purpose` 는 레코드에 **보존만** 되고 값 산출에 안 쓰이며
② `TargetGroup` 은 **문자열 그대로** 남고 FID 목록으로 확장되지 않는다.

### AC-LXSEQ3-006 — 풀 번호는 콘솔이 답한 목록에서만 온다 (M2)

**Given** 풀 목록을 답하는 가짜 상태 포트, **When** 매퍼를 돌리면,
**Then** 배정된 풀 번호가 **그 목록에 있는 값**이다.

**비공허성(필수)**: 목록을 다른 번호대로 바꾸면 배정도 따라 바뀌어야 한다.
번호가 그대로면 매퍼가 목록을 안 읽고 상수를 쓰는 것이므로 AC 미충족.

### AC-LXSEQ3-007 — 점유 슬롯에는 쓰지 않는다 (M2)

**Given** 일부 슬롯이 점유된 풀, **When** 매퍼를 돌리면, **Then** 생성된 명령의 슬롯 집합과
점유 슬롯 집합의 **교집합이 공집합**이다.

### AC-LXSEQ3-008 — 어긋나면 0건 (M2)

**Given** 필요 8건 · 빈 슬롯 3개, **When** 매퍼를 돌리면, **Then** 명령이 **0건**이고
대조표(필요 수 · 가용 수 · 부족 수)가 보고된다. **3건 부분 계획은 실패로 친다.**

### AC-LXSEQ3-009 — 새 명령 문형을 만들지 않는다 (M2)

**Given** 매퍼 소스, **When** 명령 문자열이 조립되는 자리를 훑으면, **Then** 문형은 기존 빌더에서 오고
`server/lxseq/` 안에 `Store Preset` 리터럴을 **새로 쓰는 자리가 없다**.

**검증**: `grep -rn "Store Preset" server/lxseq/` → 빈 출력.

### AC-LXSEQ3-010 — 툴이 등재되고 인자 집합이 닫혀 있다 (M3)

**Given** 착수 후 트리, **When** 레지스트리를 훑으면, **Then** `import_lxseq_presets` 가 등재돼 있고
그 인자 집합에 **경로 인자가 없다**(파일 내용은 `file_content_base64` 로만 들어온다).

**검증**: `grep -c '"import_lxseq_presets"' server/orchestrator/tools.py` ≥ 2(정의 + 핸들러 표).

### AC-LXSEQ3-011 — [HARD] 세 헤더가 각각 하나로 갈린다 (M3)

**Given** 정본 세 헤더, **When** 판별기에 넣으면, **Then** 셋이 각각 `count == 1` 이고
어느 것도 `ambiguous_sheet_kind` 로 떨어지지 않는다.

**비공허성(필수)** — `AC-FILEARG-018` 이 명시한 대조군을 그대로 승계한다:
`preset-col` 서명을 **포함 검사** 세 열(`ID`·`Name`·`Value`)로 바꾸면 `preset-bm` 헤더가 두 서명에 맞아
**`count == 2` 가 되어야 한다.** 이 대조군이 통과해 버리면 시험이 술어의 힘을 재고 있지 않으므로 AC 미충족.

**아울러** 예약 행 금지 검사가 계속 통과할 것:
`uv run pytest server/tests/test_sheets_registry.py -q -k "reserved"`.
그 검사는 **개수가 아니라 핸들러 실재**를 재므로 행이 셋 늘어도 숫자를 올릴 필요가 없다(spec.md §A.2-5).

### AC-LXSEQ3-012 — `server/lxseq/` 에 콘솔 쓰기 수단이 없다 (M3)

**Given** 착수 후 트리, **When** 훑으면, **Then** `server/lxseq/` 안에
`execution_port` · `run_commands` 호출도, OSC/소켓 임포트도 **0건**이다.

**검증**: `grep -rn "execution_port\|OscBridge\|socket" server/lxseq/` → 빈 출력.
**양성 대조군**: 같은 grep 을 `server/orchestrator/tools.py` 에 쏘면 비지 않아야 한다 — grep 이 도는지 먼저 확인한다.

### AC-LXSEQ3-013 — [HARD] 실패를 놓치지 않는다 (M2·M4)

**Given** 명령 일부가 거절되도록 만든 가짜 실행 포트, **When** 번들을 보내면,
**Then** ① 산출물이 **어느 명령까지 성공했는지**를 명시하고 ② 실패를 성공으로 접지 않으며
③ 발화 전 잰 번들 바이트가 **기록**된다.

🔴 **이 AC 는 바이트 상한을 판정에 쓰지 않는다.** 거절 축이 길이가 아니기 때문이다
(t72 실측: 2044B 거절 · 2080B 통과 — **리드 보고이며 이 SPEC 의 관측이 아니다**).
바이트는 **기록 대상**이지 통과 조건이 아니다. 「짧으니 안전」이라고 적는 순간 이 AC 는 공허해진다.

**하네스 조건**: `--approve` 없이 하네스를 돌리면 콘솔에 **아무 명령도 가지 않아야** 한다.

### AC-LXSEQ3-014 — [HARD] 확인 한계가 산출물에 적힌다 (M2·M3)

**Given** 성공한 투입 1회, **When** 산출물을 읽으면, **Then** 다음 셋이 모두 있다:
① RIG ID ↔ 콘솔 슬롯 대응표 ② 「슬롯 점유는 되읽어 확인했다」 ③ **「값 일치는 되읽지 못했다」**.

**왜 ③ 이 필수인가**: 슬롯이 찼다는 것은 「무언가 저장됐다」까지만 말한다. 값이 맞는지는 이 채널로 안 보인다.
그 구분을 안 적으면 다음 사람이 「검증된 19건」으로 읽고, 틀린 값이 조용히 영속한다 —
그룹 멤버십에서 이미 일어난 실패 형태다(t68 §2.7 · 002 축 ⑤).

---

## D. AC 로 만들지 않은 것 (의도적)

- **값 일치 검증** — 채널이 없다. 만들 수 없는 AC 를 쓰면 그 자리가 공허해진다. §G.2 위험으로 남긴다.
- **바이트 상한 통과 조건** — 축이 미지다(t72). AC-LXSEQ3-013 이 기록만 요구한다.
- **`/Universal` 문형 검증** — 미검증 문법(ASSUMPTION-02). M4 가 답하며 그전까지 기본형만 쓴다.
- **Pos 8종** — 범위 밖(spec.md §C.3).
