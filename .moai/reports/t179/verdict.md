# t179 — 미판독을 「안 잘렸다」로 답하던 자리

카드: t179 · 브랜치 `WT-unread-not-false` · base `413b7a5` (origin/main, 착수 시점 재확인)
선행: t166(PR #218, 호출 지점 방어) · t163(전수 기록) · t109(술어 SSOT)

---

## 1. 주장 (Claim)

1. `build_group_write_plan` 이 **미판독 픽스처 단면**에 `fixture_list_truncated=False`
   를 답하던 것을 고쳤다. 이제 미판독은 `True` 이고, 사유가 절단과 **다른 문면**이다.
2. 잠들어 있던 `guard_fixture_list_truncation` 이 미판독을 **별도 사유 코드**
   `FIXTURE_LIST_UNREAD` 로 거절한다. 종전에는 그냥 통과시켰다.
3. **유일한 프로덕션 호출자의 payload 는 바뀌지 않았다** — 조이는 방향이 아니다.
4. 검사 가짜 **넷**이 「읽었다」를 태우려다 실은 「미판독」을 태우고 있었다. 넷 다 고쳤다.

---

## 2. 증거 (Evidence)

### 2.1 결함의 자리

    server/groupgen/write.py:419 (수정 전)
      fixture_list_truncated = bool(fixtures_section.get("truncated"))

실패 단면에는 `truncated` 키가 **아예 없다**. 그래서 `bool(...)` 이 `False` 가 되고,
한 글자도 못 읽은 상태가 「깨끗하게 다 읽었다」와 **바이트 동일**로 나갔다.

이 필드는 그냥 값이 아니라 **문서화된 계약**이다 — 같은 파일 `:127-131` 이
「a caller that only reads the `plan` field still receives the truncation fact」라고
적어 뒀다. 미판독에서 그 caller 가 받던 것은 사실의 부재가 아니라 **거짓 사실**이었다.

### 2.2 왜 공용 술어인가

`server/rig/section.py` 독스트링이 자기 계약을 이렇게 적는다:

> 이 저장소는 「재지 못함」을 「비었음」으로 읽는 결함을 **네 번** 겪었다 ...
> 자리별로 고치면 다섯 번째 자리가 생길 때 또 난다. 그래서 술어를 여기 하나만
> 두고, 슬롯을 재는 자리는 **전부 이것을 부른다.**

`write.py:419` 는 단면을 근거로 사실을 만들어 내면서 그 술어를 안 부르는 자리였다.
사본을 짓지 않고 `section_refusal` 을 부르게 했다.

### 2.3 잠든 가드 (범위 확대 — 리드 승인 A)

    server/groupgen/write.py:262 (수정 전)
      if fixtures_section.get("truncated"):   ← 미판독은 그냥 통과

    프로덕션 호출자: 0
      grep -rn "guard_fixture_list_truncation" . --include='*.py'
        __init__.py:12,26                       재수출
        write.py:39,246                         정의
        test_groupgen_write.py:26,112,115,117,121,122   검사 둘
      (리드가 `git grep` 으로 독립 확인 — 같은 결과)

이 함수는 **거절이 유일한 일**인데 가장 나쁜 입력을 안 막았다. 독스트링이 예고한
미래 호출자(auto-selection, "group the whole rig for me")는 **바로 그 못 읽은
목록에서** `fids` 를 뽑는다. 잠들어 있다는 것은 완화 요인이 아니라 **결함이 발견되지
않는 이유**다.

리드 조건 셋 이행:
1. 사유 코드를 갈랐다 — `FIXTURE_LIST_UNREAD` 신설. `FIXTURE_LIST_TRUNCATED` 재사용 안 함
2. 검사가 「거절됐다」가 아니라 `excinfo.value.code == FIXTURE_LIST_UNREAD` 를 단언
3. 독스트링에 잠들어 있다는 것 + 무엇이 깨우는지 + 깨어나면 두 상태를 가른다는 것을 적음

### 2.4 검사 가짜 넷 — 이름과 실물이 갈려 있었다

`objects` 키가 없으면 `section_refusal` 이 그 단면을 **미판독**으로 읽는다.
넷 다 그 상태였다:

    test_groupgen_write.py:40   UNTRUNCATED_FIXTURES_SECTION
    test_groupgen_write.py:41   TRUNCATED_FIXTURES_SECTION
    test_groupgen_write.py:209  live_shape_truncated_fixtures
    test_groupgen_choreography_seam.py:28  UNTRUNCATED_FIXTURES_SECTION

:209 가 특히 나빴다 — 그 검사의 독스트링이 자기 모양을 「exactly `ok/truncated/
objects: 18 entries`」라고 **적어 놓고** 리터럴엔 `objects` 가 없었다.
「LIVE-shape regression」이라 이름 붙은 검사가 라이브 모양을 안 태우고 있었다.

### 2.5 뮤테이션 — 예고가 아니라 실제로 돌린 것과 그 결과

회차마다 `PYTHONDONTWRITEBYTECODE=1` + `assert mutated != original` +
복원 후 `assert restored == original`(t176 계기 오염 대비).

| # | 축 (하나만 건드린다) | 결과 |
|---|---|---|
| M1 | 생산 지점이 미판독을 `False` 로 되돌린다 | **KILLED** — 새 검사 3개만 빨강. 전 스위트 `3 failed, 10542 passed` |
| M2 | 미판독 사유 문면을 절단 문면으로 바꾼다 | **KILLED** — 새 검사 3개. 절단 대조군은 초록 |
| M3 | 잠든 가드의 미판독 거절을 끈다 (`if False and ...`) | **KILLED** — 새 검사 3개 + `test_ruff_check_passes_on_them` 1개. ⚠️ 넷째는 **뮤턴트 자신의 린트 위반**이라 축 오염 → M3b 로 재측정 |
| M3b | 같은 축, 분기를 통째로 삭제 (린트 비오염) | **KILLED** — 새 검사 3개만. 전 스위트 `3 failed, 10542 passed` |
| M4 | 가드가 미판독을 절단 코드로 답한다 | **KILLED** — 사유 코드 단언 3개. 「거절됐다」만 봤으면 살았다 |
| M5 | 필드를 `True` 로 굳힌다 (과잉 조임) | **KILLED** — 대조군 ② 3개. 정당한 빈 관측이 절단으로 나가는 것을 잡는다 |
| M6 | 호출 지점의 사유 덮어쓰기를 끈다 | **KILLED** — 중립성 검사 + 기존 3절 |

### 2.6 대조군 두 팔

- **팔 ①(새 검사가 잡는가)**: 위 M1~M6 전부 KILLED.
- **팔 ②(기존 상태에서는 못 잡는가)**: M1·M3b 를 **전 스위트 10,557개**에 대고 돌려
  빨개진 것은 **내가 새로 넣은 3개뿐**이었다. 즉 이 두 축은 이 저장소에서 **아무도
  안 재고 있었다.**

### 2.7 중립성 — 「조이는 방향이 아니다」를 검사로 못박았다

`test_the_producer_reason_does_not_leak_into_the_payload` (도구 층).
생산 지점 문면을 **리터럴로 복사하지 않는다** — 실제 생산자를 불러 얻고, 사유 보간
앞부분만 잘라 비교한다(규약 §3 「대조군이 술어를 복사하면 대조군이 아니다」).

🔴 첫 판에서 이 검사의 한 팔이 **우연히 통과**했다: 전체 문자열 비교였는데 보간된
사유 코드가 달라(`console did not answer` vs `path_not_resolved`) 늘 달랐다.
M6 이 그 팔을 안 죽이고 다음 팔에서 죽는 것으로 드러났다 — 팔을 접두 비교로 고쳐
다시 재니 그 팔에서 죽는다.

### 2.8 회귀 — exit code 가 아니라 통과 수의 차이

    직전 상태(origin/main 413b7a5, 별도 워크트리):  93 passed
    현재:                                          103 passed
    차이 +10 = 추가한 검사 10개 (지운 검사 0)

대상 4파일 기준. 교체는 없었으므로 순증과 추가 수가 일치한다.

---

## 3. Baseline 귀속

    base            origin/main 413b7a5 (착수 시점 `git fetch` 후 재확인)
    전 스위트       uv run pytest -q server -> 10,545 passed, 12 skipped (아래 §5)
    린트            uv run ruff check server tools packaging console -> All checks passed!
    포맷            uv run ruff format --check <4파일> -> 4 files already formatted
    직전 상태 대조  git worktree add --detach <tmp> origin/main 에서 같은 4파일 실행

---

## 4. 안 잰 것 (Gaps)

- **둘째 프로덕션 호출자가 생길 계획이 있는지 안 쟀다.** 카드가 남긴 미측정 그대로다.
  이 수정은 관측된 사고를 고친 것이 아니라 **판독에서 나온 위험**을 닫은 것이다.
  등급을 올려 쓰지 않는다.
- **실기 0건.** 콘솔에 아무것도 안 보냈다. 이 카드는 순수 조립 층이고 콘솔 쓰기가 없다.
- `guard_fixture_list_truncation` 을 **깨우는** auto-selection 호출자는 여전히 없다.
  이 수정으로 그 호출자가 생기지도, 가까워지지도 않았다.
- `write.py` 의 새 사유 문자열은 **영문**이다(파일 나머지와 일치). 사용자에게 닿는
  자리는 호출 지점의 한국어 문면이라 지금은 문제가 없지만, 둘째 호출자가 이 문자열을
  그대로 사용자에게 보이면 언어가 섞인다. **안 쟀다** — 그런 호출자가 없어서다.
- `GroupSlotError` 독스트링의 「four module constants」를 「the module constants」로
  고쳤다(상수가 이미 여섯이었고 내가 일곱째를 더했다). **이 한 낱말은 내 변경이
  더 틀리게 만든 자리라 고쳤고**, 그 외 문면은 안 건드렸다.

---

## 5. 잔여 위험 (Residual-risk)

- `section_refusal` 이 「미판독」으로 읽는 세 신호 중 **`objects` 키 부재** 갈래는
  생산 지점(`rig_section`)이 성공 단면에 늘 그 키를 넣는다는 전제에 기댄다.
  생산 지점이 바뀌면 이 술어의 의미가 조용히 넓어진다 — t166 잔여 위험 2번 그대로이고,
  이 카드가 그것을 좁히지 못했다.
- 검사 가짜를 넷 다 「읽은 단면」으로 바꿨으므로, 앞으로 **미판독 모양을 태우려는**
  검사는 `UNREAD_FIXTURES_SECTIONS` 를 명시적으로 써야 한다. 우연한 미판독 태움이
  사라진 대신, 안 쓰면 그 갈래가 안 태워진다.
- M3 이 린트 축을 함께 건드린 것은 **뮤턴트 설계의 문제**였다. 같은 형태(`if False and`)를
  쓰는 다음 사람도 같은 오염을 만든다.
