# t166 판정 — 미판독 픽스처 단면이 크기 검사를 끈다 (수리 완료)

- 카드: t166 (수리 카드, t163 이 세움)
- 브랜치: `WT-truncation-fail-closed`
- base: `origin/main` **5ae562d** (착수 시점에 다시 읽음 — 배차서 시점 d32c15f 에서 움직였다)
- 커밋: **a689882**
- 이 레인 세션 카드 수: **1장째** (§9 다섯 장 트리거 밖)
- 컨텍스트(§9): `raw_pct 35` · `stage none` · `session_id 224300e0-...`
  — SessionStart 귀속과 일치하므로 **내 값**이다(공유 트리 오염 아님)
- 등급: 관측된 현장 사고가 **아니다**. 가짜 콘솔 실행 관측이고 도달성은 판독으로 선다.
  카드가 정한 등급을 그대로 유지한다.

---

## 1. 주장 (Claim)

`create_arrangement_groups` 가 픽스처 단면을 못 읽었을 때 나던 두 결함을 고쳤다.

- **C1** 미판독 단면이 `fixture_list_truncated: false` + 빈 사유로 나가던 것이,
  이제 `true` + 미판독 사유로 나간다. 이 값은 승인 카드의 위험 사유에도 실린다.
- **C2** 미판독 단면에서 부분판독 쓰기 거절의 크기 대조가 건너뛰어지던 것이,
  이제 **거절**된다(fail-closed). 발화 0줄.
- **C3** 인접 축(응답기가 childCount 를 안 준 경우)은 **바뀌지 않았다** —
  크기 대조는 거기서 여전히 적용되지 않고 나머지 셋은 산다.

## 2. 증거 (Evidence)

명령과 관측된 출력.

    uv run pytest -q server/tests/test_section_refusal_reason_survives.py
      착수 시점(수리 전)      -> 9 passed
      수리 후                 -> 12 passed        (검사 함수 +3, 일치)

    uv run pytest -q      (전 스위트, 커밋 a689882 이후)
      -> 10525 passed, 12 skipped, 1 warning in 163.69s

    uv run ruff check <바뀐 두 파일>            -> All checks passed!
    uv run ruff format --check <바뀐 두 파일>   -> 두 파일 모두 포맷됨
      (포맷 대상 헝크 둘은 전부 내가 넣은 줄이었다. base 파일을 따로 떼어
       `ruff format --check` 한 결과가 "1 file already formatted" 였다 —
       즉 기존 코드를 재포맷한 것이 아니다.)

    uv run pytest -q server/tests/test_section_refusal_reason_survives.py \
                     server/tests/test_groupgen_write.py \
                     server/tests/test_truncate_disclosure.py \
                     server/tests/test_groupgen_tools.py
      -> 125 passed

거절문의 실제 문면(관측):

    픽스처 컨테이너를 못 읽었다(단면을 못 읽었다: path_not_resolved). 부분판독 그룹
    'GEO Stage Left' 을(를) 쓰려면 'acknowledged_unread_fids' 의 길이를 부족분과
    대조해야 하는데, 단면을 한 줄도 못 읽어 부족분 자체를 잴 수 없다 — ...

### 대조군 두 팔 (§3)

**팔 1) 새 검사가 잡는가** — 수리 후 12 passed. 그중 셋이 t166 이 더한 팔이다.

**팔 2) 기존 상태에서는 못 잡는가** — 프로덕션 파일만 `origin/main` 판으로 되돌리고
새 검사 파일 그대로 실행:

    -> 3 failed, 9 passed
       FAILED ... test_an_unread_fixture_container_says_so_and_names_the_reason
       FAILED ... test_an_unread_container_refuses_the_same_undersized_enumeration
       FAILED ... test_an_unread_container_refuses_even_a_correctly_sized_enumeration

예측한 정확히 그 셋만 빨강이고, 대조군·이웃축 아홉은 초록이다. 즉 새 검사는
필요했고(팔 2), 동시에 넓게 잡지 않는다.

### 뮤테이션 — 축 하나씩 (§3 신규 항목의 첫 적용)

| 뮤턴트 | 건드린 축 | 결과 | 빨개진 것 |
|---|---|---|---|
| M-A `if fixtures_unread:` 를 `if False:` 로 | 축 B(거절)만 | **KILL** | 팔③·팔④ 둘. 3절(축 A)은 초록 |
| M-B `or fixtures_unread` 를 뗀다 | 축 A(고지)만 | **KILL** | 3절 하나. 4절(축 B)은 초록 |
| M-C 술어를 `is not None` 으로 넓힌다 | 술어의 키잉 | **KILL** | 대조군①·팔①·팔② **셋 다 대조군** |

M-C 가 이 판정에서 제일 값나간다. 술어를 넓히면 **절단된 정상 컨테이너까지 거절**하고,
거절문이 「목록이 절단됐다 … 한 줄도 못 읽어」라는 **자기모순**을 말한다. 잡은 것이
전부 대조군이라는 사실이 "SECTION_UNREAD 로 키잉한 것"이 값을 한다는 증거다.

등가 뮤턴트 아님: 셋 다 실제로 동작을 바꿨고 빨강이 났다.

## 3. 기준 귀속 (Baseline-attribution)

- 트리: `.claude/worktrees/t166`, 브랜치 `WT-truncation-fail-closed`
- base: `origin/main` 5ae562d. 착수 시점 `git rev-list --count --left-right origin/main...HEAD` = `0 0`
- 착수 전 기준선 9 passed 는 **이 트리, 이 base** 에서 잰 값이다
- 전 스위트 10525 는 **커밋 a689882 이후** 값이다(§3 커밋→스위트 순서)

## 4. 안 잰 것 (Gaps)

- 🔴 **`server/groupgen/write.py:419` 는 그대로다.** `build_group_write_plan` 은
  여전히 단면의 `truncated` 키만 읽어 미판독을 False 로 답한다. 지금은 유일한
  프로덕션 호출자가 호출 지점에서 덮어쓰므로 사용자에게 닿는 값은 정직하다.
  **잰 것**: `build_group_write_plan` 의 호출자 전수 20자리 중 프로덕션은
  `tools.py` 한 자리, 나머지 19는 검사다. 그래서 지금 구멍은 없다.
  **안 잰 것**: 두 번째 프로덕션 호출자가 생기면 그 자리가 구멍을 물려받는다.
  거기서 고치려면 검사 가짜 둘(`UNTRUNCATED_FIXTURES_SECTION`,
  `TRUNCATED_FIXTURES_SECTION`)이 `objects` 키를 안 갖고 있어 같이 고쳐야 한다 —
  범위가 커져서 **안 했다. 후속 카드로 세우기를 리드에게 제안한다.**
- **실기 미검증.** 가짜 콘솔만 탔다. 프로덕션 포트는 실패·타임아웃에 예외를 던지고
  가짜도 그 갈래를 타지만, 실제 onPC 에서 픽스처 경로만 죽은 상태는 안 만들어 봤다.
- **한 경로만 죽는 형태.** 그룹 풀은 살고 픽스처만 죽는 조합만 쟀다. 반대(그룹만
  죽음)나 둘 다 죽음은 이 카드의 축이 아니라 안 쟀다.

### gap 이 아니라 이번에 잰 것

카드의 셋째 물음(「거짓 긍정을 하류가 어떻게 쓰는가」)은 t163 이 미추적으로 남겼는데,
한 명령이면 답이 나서 지금 쟀다(§7):

    grep -rn "fixture_list_truncated" (py/ts/tsx/js/jsx/lua/md, server/ 제외)

`server/` 밖에는 **코드 소비자가 없다** — SPEC 문서 5건뿐. `server/` 안의 코드
소비자는 `server/tools/groupgen_e2e.py:240` 하나. 따라서 이 필드의 실제 독자는
**모델(툴 페이로드)** 과 **사람(승인 카드 위험 사유)** 둘이고, 별도 UI 렌더 경로는
없다. 거짓 긍정의 피해자가 그 둘이었다는 뜻이다.

## 5. 잔여 위험 (Residual-risk)

- 이 수리는 **조이는 방향**이다. 이전에 통과하던 호출(미판독 + 부분판독 그룹)이
  이제 거절된다. 그 조합에서 쓰기가 나가고 있었다면 그 흐름이 끊긴다 —
  다만 그 흐름이 바로 이 카드가 없애려던 것이다. §7 대로 **판정은 리드에게 넘긴다.**
- `section_refusal` 이 `objects` 키 부재를 미판독으로 읽는다. 프로덕션 생산 지점
  (`rig_section`)은 항상 그 키를 넣으므로 지금은 안전하지만, 생산 지점이 바뀌면
  이 술어의 의미가 조용히 넓어진다.
- 문구 단언과 성질 단언을 갈라 놨지만(§3), 사유 문면이 바뀌면 문구 단언이
  깨진다. 그건 의도된 취약성이다 — 사유가 바뀌면 사람이 봐야 한다.
