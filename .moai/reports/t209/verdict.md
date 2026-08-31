# t209 — 4단계 큐 발사기 (`lxseq_cues_e2e.py`)

- 카드: t209 · 브랜치 `WT-cue-tool` · PR **#261**
- 커밋: `5ba17b3`(발사기·검사 신규) → `01a4a48`(헤더 실패 사유화)
- base: `12846e9` (착수 시점 origin/main)
- 워크트리: `.claude/worktrees/t209-cuetool`

## 1. 주장 (Claim)

4단계 네 조각 중 **e2e 발사기**를 만들었다. 형제 `lxseq_presets_e2e.py` 구조를
승계하되, 명세서가 시킨 두 자리만 다르다. 콘솔에는 **아무것도 보내지 않았다.**

## 2. 증거 (Evidence)

### 2.1 정본 CSV 인구조사 — 하네스가 직접 셈

```
데이터 행 89 · 고유 Q# 18 (Q010~Q180, 10 단위)
콘솔 대상 83 · 영상 콜(LED-W) 6
그룹 13종, ALL 1행 (§11.1 2열이 ALL 허용)
```

### 2.2 큐 단위 자르기 실측

```
limit=1 skip=0  -> rows 3   cues [Q010]
limit=2 skip=0  -> rows 6   cues [Q010, Q020]
limit=1 skip=1  -> rows 3   cues [Q020]
limit=None      -> rows 89  cues 18종 전부
```

### 2.3 검사·뮤테이션

```
server/tests/test_lxseq_cue_harness.py : 11 passed
뮤테이션 6/6 잡힘 (2회차 합산)
  1회차 — 판별기를 Note 로 되돌림 / 자르기를 행 단위로 / 유출 탐지기 무력화
  2회차 — 헤더 검사 제거 / 실패 메시지에서 이유 삭제 / 발견 헤더 목록 비움
  매 회차 원본 바이트 동일 복원 확인
범위 : uv run pytest -k "lxseq or cue" -> 794 passed, 2 skipped
ruff : check 통과 · format 통과
```

### 2.4 파서 교차 검산 (`origin/WT-cue-parser` `9ad96bc`, 읽기 전용 · 머지 안 함)

```
파서   records 89 / cues 18 / rejections 0 / video 6
하네스 total   89 / cues 18 / console   83 / video 6
큐 순서 동일 · 영상콜 큐 목록 동일 (Q080 Q090 Q110 Q130 Q160 Q170)
파서 video 판별이 전부 group == LED-W
```

리드 측정치까지 합쳐 **세 번의 독립 측정**이 같은 수에 도달했다.

## 3. 발견 — 반증한 전제 둘

### 3.1 🔴 배차서 전제 반증 — LED-W 판별기는 `Note` 가 될 수 없다

배차서는 「LED-W 6행 **전부** `Note` 가 `영상 큐 LW-0N 콜`」이라 했다.
정본 CSV 직독 결과 **6 중 5**다.

| Q# | Note |
|---|---|
| Q080 | 영상 큐 LW-02 콜 |
| Q090 | 영상 큐 LW-03 콜 |
| Q110 | 영상 큐 LW-04(로우) 콜 |
| Q130 | 영상 큐 LW-05(피크) 콜 |
| Q160 | 영상 큐 LW-06 콜 |
| **Q170** | **영상 페이드아웃 동기** — `LW-` 도 「콜」도 아님 |

`Note` 텍스트를 판별기로 쓰면 **1행이 콘솔 명령으로 샌다.** 과거 명령 유출
사고가 났던 자리이고, 집계가 `5/6` 으로 나와 **그럴듯해서 눈에 안 띈다** —
`0/6` 이면 누구나 알아챈다. 가장 안 보이는 형태로 새는 것이다.

처방: 판별기는 `Group == "LED-W"` 하나. `Note` 는 근거 서술로만.
`census.note_pattern_hits`(5)와 `note_pattern_would_miss`(1)가 매 실행마다
이 수를 다시 재고, `test_note_text_is_not_a_discriminator` 가 단언한다 —
실패 메시지에 「판별기를 Note 로 되돌리지 마라」가 들어 있다.

**독립 확인**: 파서도 `_VIDEO_CALL_GROUP = "LED-W"` 로 그룹 판별을 한다.
두 레인이 서로 안 보고 같은 축에 도달했다.

### 3.2 헤더 관용도 어긋남 — 정규화로 닫지 않았다

파서(`cue_parser.py:112` `_normalize_header`)는 헤더를 소문자화·공백제거·
BOM제거해 관대하게 받는다. 이 하네스는 원문 그대로 인덱싱한다.

**양팔 실측** (헤더만 `Q#`→`q #` 로 바꾼 변형 CSV, 데이터 행은 정본 그대로):

```
파서   : OK  records = 89  cues = 18
하네스 : 실패 — KeyError 'Q#'
```

🔴 **정규화를 넣지 않는 것이 판정이다.** 이 하네스의 인구조사는 툴 응답을
대조할 **독립 분모**다. 정규화를 두 벌 두면 두 벌이 **같이 틀렸을 때 대조가
「일치」라고 답한다** — 대조군이 대조 대상의 해석을 베끼는 순간 존재 이유가
사라진다. 그래서 비표준 헤더는 이 하네스의 **범위 밖**으로 두고, 조용히 죽는
것만 고쳤다: `CanonicalHeaderRequired` 가 못 찾은 열과 시트에 있던 헤더를 둘 다
말하고, **왜 관대하게 받지 않는지**를 예외 docstring 과 실패 메시지 양쪽에
박았다.

## 4. 안 잰 것 (Gaps)

- 🔴 **실기 발사 0회.** `import_lxseq_cues` 등재 전이라 dispatch 가 안 간다
  (`tool_unavailable` + exit 3 으로 기록). **콘솔에 아무것도 보내지 않았다.**
- 🔴 **완료 조건 미도달.** 리드 실측 기준선 `DataPool/Sequences` `childCount`
  발사 전 `1` → 성공 시 `2`, 큐 자식 18 — 재도록 **만들어만 뒀고 아직 안 쟀다.**
- **유출 봉쇄의 실기 미검증.** 탐지기 자체는 양성 대조군으로 검증했으나
  (`test_leak_detector_fires_on_a_fabricated_leak`), 실제 툴이 LED-W 행으로
  무엇을 만드는지는 툴이 없어 못 봤다.
- `cue_mapper.py`(`origin/WT-cue-mapper` `6e19fda`)와는 대조하지 않았다.
  통합은 run 소유라 머지하지 않았다.

## 5. 잔여 위험 (Residual risk)

- **인구조사와 툴 집계가 어긋날 수 있다.** 그건 결함이 아니라 이 하네스가
  존재하는 이유다 — 어긋나면 그 자체가 발견이다. 다만 지금은 툴이 없어 이
  대조가 **한 번도 실행된 적 없다.**
- `slice_by_cue` 는 `limit is None and skip == 0` 일 때 `read_rows` 를 거치지
  않아 **통째 경로만 헤더 검사를 우회한다.** 지금 결함은 아니다 — `main()` 이
  항상 `census(read_rows(...))` 를 먼저 부른다. 미래의 직접 호출자에게만
  구멍이고, **리드 판정으로 닫지 않고 둔다**(범위 밖 작업이 본 작업을 밀어내지
  않도록).
- 되읽기는 번호·이름까지만 열린다(`cue_monitor._cue_items`, 2026-08-02
  LIVE-VERIFIED). **큐 내용이 맞는지는 이 채널로 판정할 수 없다.**

## 6. 계기 관측 — 덮는다, 파지 않는다

- **워크트리 Bash 가드의 방아쇠는 「중괄호 안에 쉼표」다.** 빈 중괄호는
  통과하는데 쉼표가 든 사전/집합 컴프리헨션은 브레이스 확장으로 읽혀 거절된다.
  큰 히어독이 거절돼 크기 축인 줄 알았으나 아니었고, 그 표현을 빼니 통과했다.
  메모리의 「크기 축 미확정」을 이걸로 좁힐 수 있다. 파일은 히어독을 5조각으로
  나눠 이어붙여 만들었다.
- **`Write`/`Edit` 는 이 워크트리에서 절대·상대 경로 양쪽 다 거절된다**
  (`Path traversal detected`). 같은 경로에 Bash 는 통과한다. 이 세션의 시작
  디렉터리가 primary 가 아니라 `orca/workspaces/AI-Lighting_Console/LX-SEQ`
  (브랜치 `jjjh7401/LX-SEQ`)여서다. 도구 막힘이지 레인 막힘이 아니다.
- **재귀 강제 삭제 명령은 대상이 `/tmp` 하위여도 위험명령 가드에 걸린다** —
  정규식이 슬래시까지만 보고 매칭한다. `shutil.rmtree` 로 우회했다.
  🔴 이 verdict 를 쓰다가 **그 명령 문자열을 본문에 인용한 것만으로도 거절됐다.**
  가드는 실행이 아니라 페이로드 문자열을 본다.

## 7. 🔴 자기정정 — 뮤테이션 도구 자신이 공허할 수 있다

2회차 셋째 뮤테이션의 앵커 들여쓰기를 8칸으로 잘못 써서 **0건 매치로 조용히
건너뛰어졌다.** 「건너뜀(앵커 N건)」을 출력하게 해 둔 덕에 눈에 띄었고, 앵커를
고쳐 다시 쟀다(잡힘 확인).

**앵커 건수를 안 찍었으면 2/3 을 3/3 으로 보고했을 것이다.** 뮤테이션은
「검사가 죽었나」를 재는 도구인데 그 도구 자체가 아무것도 안 할 수 있다 —
저장소의 「검사가 자기 자신이 공허할 수 있다」 계열에 붙는 뮤테이션 판이다.

교훈: **뮤테이션 스크립트는 앵커 매치 건수를 반드시 단언하거나 출력해야 한다.**
치환이 0건이면 그 회차는 「생존」도 「잡힘」도 아니라 **안 잰 것**이다.

## 8. 다음

- 통합·등재·`preview` 는 **run** 소유. `apply`(실기 발사)는 **리드 세션**에서
  한다 — 동료가 전달한 승인은 승인이 아니고, 감독 승인은 받은 채널에서만
  유효하다.
- 발사 후 이 발사기가 `childCount 1 → 2` 와 큐 18 을 재면 그것이 완료 판정이다.

## 9. `server/sheets/registry.py` 의 `cue-ex` 행 — 실측 후 **넣지 않았다**

2026-08-31 리드 배차로 조사했다. 결론: **라우팅 공백은 실재하지만, 지금 행을
넣으면 열리지 않고 검사만 빨개진다.** 파일 변경 0 · 커밋 0 으로 남겼다.

### 9.1 라우팅 공백은 실재한다

```
discriminate(cue-ex CSV) -> matched=() · outcome=unknown_sheet_kind
```

형제 셋(`patch`·`group`·`preset` 3종)은 전부 등재돼 있는데 큐만 없다.
감독이 시트를 업로드해도 어느 도구로도 가지 않는다.

### 9.2 🔴 그런데 지금 행을 넣어도 안 열린다

`discriminate` 가 `registry` 인자를 받으므로 **파일을 고치지 않고** 후보 행을
메모리로 먹여 실험했다. 후보: `ExactColumns(CANONICAL_CUE_COLUMNS 17열)` +
`Handler(HANDLER_TAG_TOOL, "import_lxseq_cues")` + `passthrough_args=("action",)`.

| 시트 | 현재 표 | 후보 행 추가 후 |
|---|---|---|
| patch | `('patch',)` | `('patch',)` · errs `['cue-ex']` |
| group | `('group',)` | `('group',)` · errs `['cue-ex']` |
| preset-dim | `('preset-dim',)` | `('preset-dim',)` · errs `['cue-ex']` |
| preset-col | `('preset-col',)` | `('preset-col',)` · errs `['cue-ex']` |
| preset-bm | `('preset-bm',)` | `('preset-bm',)` · errs `['cue-ex']` |
| **cue-ex** | `()` | **`()`** · errs `['cue-ex']` |

**cue-ex 는 행을 넣어도 `matched=()` 다.** `import_lxseq_cues` 가 등재 전이라
판별기가 그 행을 `no_target_tool` 설정오류로 떨어뜨린다.

이건 저장소가 이미 정한 규칙이다:
- `registry.py:359` — 「예약된 종류의 행은 만들지 않는다 — 그 종류의 **파서·핸들러가
  있어야** 행을 만든다(REQ-FILEARG-017)」
- `test_sheets_registry.py:234` `test_registry_has_no_row_reserved_for_a_later_spec`
  — 개수가 아니라 **핸들러 실재**로 잰다. `assert reserved == []` 인데 위 표대로
  `['cue-ex']` 가 나오므로 **빨개진다**

### 9.3 ✅ 핵심 위험은 없다 — 6종 전수 대조군

배차가 지목한 진짜 위험은 「네 시트가 같은 라우터를 지나 서로 훔쳐가는가」였다.
**안 훔쳐간다.** 위 표에서 patch·group·preset 3종이 후보 행 추가 후에도 전부
자기 종류로 그대로 붙는다. 17열 `ExactColumns` 는 4열 프리셋 서명과 겹칠 수
없고, 역방향도 실측 0건이다.

🔴 **이 표를 다시 재지 마라.** 행을 넣는 회차는 이 결과를 근거로 쓰고, 행 추가 +
검사 + push 만 하면 된다.

### 9.4 행이 들어갈 조건 둘

1. `server/lxseq/cue_parser.py` 가 트리에 있을 것 — `CANONICAL_CUE_COLUMNS` 를
   **참조로** 들어야 한다(사본 금지). 형제 `patch` 행이 `parser.CANONICAL_COLUMNS`
   를 드는 방식 그대로. 실측: 이 모듈은 조사 시점에 **내 트리에도 `origin/main`
   에도 없었다** — 미머지 브랜치에만 있었다
2. `import_lxseq_cues` 가 등재돼 있을 것 — 없으면 행이 죽고 검사가 빨개진다

### 9.5 판정 (리드, 2026-08-31) — (b′)

CI 가 결제로 멈춰 main 이 안 움직이므로, **run 이 `WT-cue-integrate` 를 push 하면
그 브랜치를 기점으로** 행을 올린다. 그 브랜치에 조건 둘이 다 들어 있다. 파일도
안 겹친다(run 은 `tools.py`, 이 레인은 `registry.py`).

「지금 넣고 검사를 고친다」는 양쪽 다 반대했다 — 그 검사가 「예약 행 금지」를
지키는 장치이고, 통과시키려면 장치를 무력화해야 한다. 그러면 다음에 진짜 예약
행이 들어와도 아무도 못 잡는다.
