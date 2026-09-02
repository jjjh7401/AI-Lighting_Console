# t255 — 4단계(LXSEQ-004) 닫기 판정

> **4단계는 무엇을 냈나** — 곡 Sugar 의 큐 18개가 전부 콘솔에 올라갔고, 이름도 정본대로다. 시트에 적힌 큐를 하나도 빠뜨리지 않았다.
> **무엇이 안 됐나** — 큐 **안에** 무엇이 들었는지는 콘솔에 물어볼 방법이 없다. 데이터가 들어 있다는 것까지만 확인된다.
> **닫아도 되나** — **아직 아니다.** 인수 기준 하나가 미달이고 하나는 못 쟀다. 다만 `draft` 는 틀렸다 — 실제 상태는 「구현 중」이다.

기준: 워크트리 `.claude/worktrees/t255` · 브랜치 `WT-stage4-close` · base `origin/main ad98286`
2026-09-02 · **콘솔 쓰기 0 · 코드 변경 0 · 새 기능 0** · 콘솔 판독 7회(전부 읽기)
증거: `.moai/reports/t255/evidence/` (원문 JSON 7종)

---

## 0. 지시대로 정본을 먼저 열었다

`src/Lighting_Designer/01_스펙/LX-SEQ-SPEC-v2.1.md` (356행) 전문을 읽었다.
`progress.md` §E.1 이 자백한 「아무도 안 열었다」를 이 회차가 닫는다.

**16개 AC 가 정본과 어긋나는 자리를 더 찾았나 — 하나 찾았고, 이 SPEC 밖이다.**

| 자리 | 정본 | 실제 시트 | 판정 |
|---|---|---|---|
| `COL.xx` ↔ 팔레트 `P.xx` 1:1 (§10) | P4 = **콜드 블루** · P5 = 딥 블루 · P6 = 마젠타 · P7 = 시안 | RIG 팩 `preset-col.csv` 는 `COL.04 핫 핑크 (=P4)` · `COL.05 딥 퍼플 (=P5)` · `COL.06 터쿼이즈 (=P6)` · `COL.07 선셋 오렌지 (=P7)` | ⚠️ **결함 아님** — §2.3 이 「곡마다 팔레트를 재정의해도 되지만 ID 체계는 유지」를 허용한다. 다만 `(=P4)` 주석이 정본 팔레트를 가리키는 것으로 읽히면 오독이 난다 |

🔴 **이건 LXSEQ-004 의 AC 문제가 아니라 RIG 팩 표기 문제다.** 이 카드는 고치지 않는다 — §6 에 카드 후보로만 올린다.

---

## 1. 인수 기준 전수 판정

🔴 **먼저 개수부터 정정한다 — 16개가 아니라 14개다.**
`acceptance.md` §C.0 역추적표 실측: **001~014 번호 14개**, 그중 **004 는 t207 에서 폐기**.
즉 **살아 있는 AC 는 13개**다. 배차서의 「16개」는 어느 문서와도 안 맞는다.

| AC | 판정 | 근거 (명령·파일:줄·출력) |
|---|:---:|---|
| 001 되읽기 수단 확정 | **PASS** | `progress.md` §E.0 이 경로·함수로 지목. 이 트리에서 재확인 — `server/web/cue_monitor.py:49` `SEQUENCE_PATH_TEMPLATE`, `:145` `_cue_items`, `:222` 소비 지점 |
| 002 정확 열 집합 | **PASS** | `cue_parser.py:96` `unexpected_columns: ` + `missing_columns` 양쪽 실재, 검사에서 각각 2·4건 단언 |
| 003 `Dim` 은 숫자다 | 🔴 **FAIL** | 앞절(숫자 해석)은 선다 — `test_lxseq_cue_mapper.py:162` 가 `dim_raw="55"` 경로를 단언. **뒷절이 안 선다**: AC 는 「`DIM.01` 이 오면 거부하고 **「이 열은 참조가 아니라 숫자다」를 사유로**」를 요구하는데, 실제 사유는 `cue_mapper.py:206` `BAD_NUMBER` = 「시트 셀이 수로 안 읽힌다」다. 그리고 큐 시트 `Dim` 에 참조를 넣는 검사가 **0건**(`grep 'dim_raw="DIM'` → 0). `progress.md` §E.3 Gap 3 이 이미 정직하게 적어 뒀다 |
| ~~004~~ | — | t207 폐기. 정본 `:272`·`:275`·`:276` 과 충돌 |
| 005 그룹은 콘솔 목록에서만 | **PASS** | `cue_mapper.py:127` `UNKNOWN_GROUP`, 검사 8건 단언 |
| 006 페이드는 초 단위 숫자 | **PASS** | `test_lxseq_cue_mapper.py:160` `test_blank_fades_are_tracking_not_zero` · `:179` `test_blackout_needs_both_zero_and_fade` — `0.0` 과 빈칸을 갈라 단언 |
| 007 [HARD] 큐 단위 0건 | **PASS** | `cue_mapper.py:452` `cues_held` · `tools.py:5844` `partial_ship` · `:5878` `notice_partial_ship`. `test_lxseq_cue_partial_ship.py` 실재. 독립 재현: 이 회차가 정본 CSV 를 매퍼에 먹여 프리셋 배정을 바꿔가며 잰 결과 큐 단위로 갈렸다(t251 evidence) |
| 008 [HARD] 두 층 수렴 | **PASS** | AC 가 이름으로 지목한 검사 둘이 실재 — `test_lxseq_cue_mapper.py:540` · `:555` |
| 009 새 명령 문형 금지 | **PASS**(약함) | `test_lxseq_cue_tool.py:142` 가 `Store Sequence <n> '…'` · `Group '…'` · `Store Cue <n> '…'` 세 문형을 단언. ⚠️ **소스 텍스트 grep 단언**이지 런타임 산출 명령 단언이 아니다 |
| 010 툴 등재·인자 닫힘 | **PASS** | `tools.py:280`·`:11170`·`:11476` 등재. `test_lxseq_cue_tool.py:45` 가 인자 집합을 **완전 등식**으로 단언(9종) — `song_title`·`genre`·`sections` 는 그 집합에 없다 |
| 011 lxseq 에 쓰기 수단 없음 | **PASS** | `grep -rn 'import.*osc\|OscBridge\|execution_port\|socket' server/lxseq/` → **0건** |
| 012 [HARD] 실패를 놓치지 않는다 | **PASS** | 사유 5종 전부 검사에서 문자열로 단언 — `missing_columns` 4 · `unexpected_columns` 2 · `unknown_group` 8 · `unresolved_preset` 10 · `slot_shortfall` 2 |
| 013 [HARD] 되읽기 한계를 적는다 | **PASS** | `cue_mapper.py:454` `unverified = ("value_match","tracked_value")` + `:455` `unverified_reason`, `tools.py:5864` 가 산출물에 싣는다 |
| 014 [HARD] 「안 된다」 3분류 | **PASS** | `cue_mapper.py:178` `BLOCK_CONSOLE_STATE` · `:179` `BLOCK_DOC_INTENT` · `def block_report` 실재, 기본값 (C) |

**합계: PASS 12 · FAIL 1 · 미측정 0 · 폐기 1.**
검사 실행: `pytest server/tests/test_lxseq_cue_*.py -q` → **128 passed, 0 failed**.

🔴 **「실기 발사 성공률」은 AC 가 아니다** — `acceptance.md` §D 가 의도적으로 뺐다. 그래서 위 표에 없다.

---

## 2. 약속 대 산출 — 「18큐」는 **전부**다

감독 질문의 중심이 여기다. 숫자로 확정한다.

### 2.1 단위가 둘이었다

```
CUE 시트     행 18 · 고유 Q# 18      <- 곡의 큐 수
CUE-EX 시트  행 89 · 고유 Q# 18      <- long format (한 큐 × 한 그룹 = 한 행)
양방향 차집합 0                       <- 정본 §11.1 「부분집합 금지」 충족
```

**89 는 목표가 아니라 입력 행 수다.** 89행이 18큐로 접힌다. 「89행이 목표였는데 18큐만 올라갔다」는 **단위 오독**이다 — 접기 전 숫자와 접은 뒤 숫자를 나란히 놓은 것이다.

### 2.2 콘솔에는 18개가 전부 있다 (오늘 완전 열거)

```
DataPool/Sequences        childCount 6, truncated false
   1 Default · 2 Sugar · 3 'Sugar r3' · 4 eset1Fade · 9 T215 SCRATCH · 2000
DataPool/Sequences/3      childCount 21
   offset 0  -> 13 수신, truncated TRUE      <- 🔴 한 번만 읽었으면 13 으로 셌다
   offset 13 -> 8 수신,  truncated false
   13 + 8 = 21 = childCount                   <- 산술 일치
   내역: OffCue · CueZero · 'Cue 1' + Q010~Q180 18개
```

**Q010 · Q020 · Q030 · Q040 · Q050 · Q060 · Q070 · Q080 · Q090 · Q100 · Q110 · Q120 · Q130 · Q140 · Q150 · Q160 · Q170 · Q180** — CUE 시트의 18개와 **완전 일치**. `cueNo` 도 10~180 으로 콘솔이 되돌려 준다.

> 🔴 **t230 §4.2 의 경고가 오늘 그대로 재현됐다** — `query_state` 자식 목록은 `truncated: true` 를 달고 조용히 잘린다. 페이징 없이 세면 **18 을 13 으로 센다.**

### 2.3 답

| 물음 | 답 | 근거 |
|---|---|---|
| 18큐는 부분인가 전부인가 | 🟢 **전부다** | 곡의 큐 = 18, 콘솔의 큐 = 18, 차집합 0 |
| 그럼 4단계가 약속한 것을 다 냈나 | ⚠️ **큐 **개수**는 다 냈다. 큐 **안의 행**은 못 확인한다** | §3 |

---

## 3. 올라간 18큐의 내용 — 다시 쟀고, **지금도 못 읽는다**

카드 지시: 「오늘 판독 채널이 열렸지만 그건 프로그래머 축이지 큐 내용 축이 아니다 — 지금도 못 읽는지 다시 재라.」 **쟀다.**

### 3.1 응답기 1.6.3 이 연 것은 큐 축이 아니다 (소스 대조)

```
copilot_responder.lua:76   -- 1.6.3: additive ROOT_ALIASES entries programmer/programmerpart/
copilot_responder.lua:82   VERSION = "1.6.3"
```

1.6.3 의 추가분은 **`ROOT_ALIASES` 뿐**이다. 큐 내용 축에 손대지 않았다.

### 3.2 클래스가 그 필드를 안 갖고 있다 — 완전 열거

```
introspect DataPool/Sequences/3/4      class=Cue   total=23   truncated=false  paging=complete
introspect DataPool/Sequences/3/4/1    class=Part  total=195  truncated=false  paging=complete
```

`Cue` 23필드 어디에도 내용이 없다. 「못 찾았다」가 아니라 **완전 열거해서 없다**.

### 3.3 `Part` 의 내용 후보 필드 — 오늘 1.6.3 에서 재판독 (양성 대조군 포함)

```
NAME             = 'Q010 INTRO 화사'      <- 양성 대조군, 정본 라벨 실재
OWNDATAPRESENT   = true                   <- 비어 있지 않다
MEMORYFOOTPRINT  = 4580                   <- 데이터가 있다
STOREDDATA       = property not readable  <- 못 읽는다
PRESETDATA       = ""                     <- 읽히는데 비었다
REFERENCES       = ""                     <- 읽히는데 비었다
SELECTIONDATA    = table: 0x600000910780  <- 🔴 테이블 **주소**
DEPENDENCIES     = table: 0x600000910900  <- 🔴 테이블 **주소**
VALUESMODE       = 'Normal' · PRESETMODE = 'Selective' · COUNT = 0
```

**t230(1.6.2) 판정이 그대로 유지된다.** 데이터가 있는 것이 확실한 자리에서 내용 필드가 비므로, 이 빈값은 **부재의 증거가 아니다.**

### 3.4 🔴 새로 나온 것 — 두 필드는 「비었다」가 아니라 「직렬화가 안 됐다」

t230 은 `PRESETDATA`·`REFERENCES`·`STOREDDATA` 셋만 읽었다(그 문서 §2.3). 이 회차가 **`SELECTIONDATA`·`DEPENDENCIES` 를 처음 읽었고**, 둘은 빈 문자열이 아니라 **`table: 0x…` Lua 테이블 주소**를 답한다.

**차이가 크다**: 빈 문자열은 「이 채널이 그 축을 안 잰다」이고, 테이블 주소는 **「값은 거기 있는데 응답기가 문자열로 풀지 않았다」**다. 후자는 **제거 가능한 미구현**이다 — t235 가 `Programmer` 별칭에 대해 밝힌 것과 같은 형태.

⚠️ **이것은 「열면 읽힌다」가 아니다.** 그 테이블 안에 참조가 들었는지는 **안 쟀고 이 채널로는 못 잰다.** 확인하려면 응답기가 테이블을 직렬화해야 하고, 그건 콘솔에 배포되는 코드 변경이다 — 이 카드 범위 밖(§6 카드 후보 2).

### 3.5 확정 — 이 SPEC 의 잔여 한계

> **큐 **내용** 되읽기는 이 채널로 불가능하다.** `Cue` 클래스에 내용 필드가 없고(23/23 열거), `Part` 의 후보 필드는 못 읽거나 비거나 주소만 답한다. `AC-LXSEQ4-013` 이 이 한계를 산출물에 싣게 한 것은 **옳았고 지금도 유효하다.**

따라서 `progress.md` §E.3 Gap 1(「18큐 중 8개가 POS 행 없이 나갔는지 확인 안 했다」)은 **닫히지 않는다** — 확인 수단이 원리적으로 없기 때문이 아니라, **응답기가 그 테이블을 안 풀기 때문**이다. 사유가 바뀌었으니 그렇게 적는다.

---

## 4. status 전이 — `draft` 는 틀렸다, 그러나 `completed` 도 아니다

### 4.1 현재 상태 (실측)

```
LXSEQ-004  spec.md frontmatter : status: draft · updated: 2026-08-31
LXSEQ-003  spec.md frontmatter : status: draft · updated: 2026-08-25
```

코드는 main 에 있다 — `78e846f`(t207) 이후 `f8ed451`(t225) · `a478953`(t228) · `09bd3a7`(t229) · `2fa654e`(t230) 이 전부 머지됐고, 콘솔에 18큐가 실재한다(§2.2).

### 4.2 판정

| 후보 | 성립하나 | 근거 |
|---|:---:|---|
| `draft` | ❌ | 코드가 main 에 있고 실기까지 갔다. 「아직 계획 단계」로 오독된다 |
| `in-progress` | 🟢 **이것이다** | 구현은 있고 수용 기준이 **미충족**(AC-003 FAIL) |
| `implemented` / `completed` | ❌ | AC-003 이 FAIL 이고 `progress.md` 가 base `78e846f` 에 멈춰 t225·t228·t229·t230 을 **한 줄도 안 담는다** |

🔴 **전이는 이 카드가 하지 않는다.** `spec-frontmatter-schema.md` 의 소유권 표가 `draft → in-progress` 를 **manager-develop** 에 배정한다. 남의 소유 전이를 대행하면 그 자체가 새 드리프트다 — t113 이 같은 자리에서 같은 판단을 했고 그것이 옳았다.

**LXSEQ-003 도 같은 상태다.** 카드 지시대로 **이름만 세운다** — 이미 `t117` 이 큐에 있고 그 카드가 002·003 을 덮는다. **004 를 t117 에 얹는 것을 권한다**(같은 소유자·같은 전이·같은 근거 형태).

### 4.3 🔴 전이보다 먼저 고칠 것 — `progress.md` 가 낡았다

`progress.md` 는 base `78e846f`(t207) 기준이다. 그 뒤 **t225 · t228 · t229 · t230** 이 머지됐고, 그중 **t228 은 AC-007 의 입도를 배치에서 큐로 바꿨다**. `acceptance.md` 는 그 개정을 담았는데 `progress.md` 는 안 담는다. 이 상태에서 `completed` 로 올리면 **낡은 기록이 확정된다.**

---

## 5. 안 잰 것

- **AC-003 을 고치지 않았다.** 코드 변경 0 이 카드 경계다. 사유 문자열 한 줄 + 검사 한 건이면 닫힌다(§6 카드 후보 1)
- **큐 내용 값 대조.** §3.5 — 이 채널로 불가
- **`SELECTIONDATA` 테이블 안에 무엇이 있는지.** 주소만 봤다
- **t209 실기의 실제 `preset_slots`.** `progress.md` §E.3 Gap 1 그대로 — 사후 확인 수단이 없다
- **`Sequences/2` 'Sugar'(구판) 의 내용.** 읽지 않았다 — 이 카드 대상은 `/3` 이다
- **1~3 단계 AC-014.** `progress.md` §E.3 Gap 4 그대로

---

## 6. 카드로 세울 것 (제안만 — 여기서 만들지 않았다)

| # | 무엇 | 왜 지금 아닌가 | 크기 |
|---|---|---|---|
| 1 | **AC-003 사유 문자열 정합** — `BAD_NUMBER` 갈래에서 `Dim` 열만 「이 열은 참조가 아니라 숫자다」로 답하게 하고 검사 한 건 추가 | 코드 변경이라 이 카드 경계 밖 | 한 줄 + 검사 1 |
| 2 | **응답기가 `SELECTIONDATA` 를 직렬화한다** | 콘솔 배포 코드 변경 · 감독 승인 사안 | 응답기 1.6.4 |
| 3 | **`progress.md` 를 t225·t228·t229·t230 까지 끌어올린다** | status 전이의 선행 | 문서 |
| 4 | **RIG 팩 `preset-col` 의 `(=Pn)` 주석 정합** — 정본 §2.3 재정의 허용을 명시하거나 이름을 맞춘다 | LXSEQ-004 밖 | 문서 |

---

## 7. 이 회차가 안 한 것

- **콘솔 쓰기 0.** 판독 7회 전부 `query_state`·`props`·`introspect`. 음성 대조군(`DataPool/Sequences/ZZZNOTREAL9` → `path segment not found`)을 먼저 쏴서 `ok` 가 증거로 서게 했다
- **코드 변경 0** — `git status --porcelain server/ src/` 로 확인
- **status 전이 0** — 소유자가 따로 있다(§4.2)
- **카드 생성 0** — §6 은 제안이다
- **머지 안 했다** — 리드가 확인하고 한다
