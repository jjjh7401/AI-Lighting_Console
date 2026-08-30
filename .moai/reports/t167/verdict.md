# t167 판정 — 그룹 매퍼가 단면 거절 사유를 버린다 (수리 완료)

- 카드: t167 (t152 가 처음 문 자리, t163 이 전수로 지목)
- 브랜치: `WT-group-refusal-reason` · base `origin/main` **17af4aa** (착수 시점 0/0)
- 커밋: **4837ef2**
- 이 레인 세션 카드 수: **2장째** (§9 다섯 장 트리거 밖)
- 등급: 관측된 사고가 **아니다.** 판독에서 나온 개선이고, 두 사유가 구별 안 되는 것이
  사용자를 막고 있다는 관측은 없다. 카드가 정한 등급을 유지한다.

---

## 1. 주장 (Claim)

**C0 — 카드 문면을 반증했다.** 카드는 「`map_groups` 가 튜플을 버려 두 사유가 사용자에게
바이트 동일로 나간다」고 적었다. 재보니 그게 아니었다:

- `console_read_incomplete` 는 **두 축**에서 선다 — FID 판독(`group_mapper:265`)과
  그룹 풀 단면(`:367`).
- 페이로드의 사유 채널 `console_read_reason`(`tools.py:4769`)은 **FID 축에만** 걸려 있다.
- 호출부가 `console_fids_complete=fid_read.complete`(`tools.py:4744`)로 **같은 값**을
  넘기므로, 단면 축에 닿았다는 것은 FID 게이트를 통과했다는 뜻이다.
- 따라서 단면 축으로 True 가 서면 `console_read_reason` 은 **항상 `null`** 이었다.

즉 「사유가 접힌다」가 아니라 **「참 플래그 + 빈 사유」**이고, 그 채널은 애초에 다른 축
것이었다. 리드가 독립으로 같은 좌표를 재서 확인했다.

**C1** 단면 축 거절이 이제 `refusal`·`refusal_detail` 로 실린다 — 형제와 **같은 이름**.
**C2** 두 분류(`path_not_resolved` / `console_unreachable`)가 이제 **갈린다**.
**C3** FID 축 채널은 안 바뀌었다.

## 2. 증거 (Evidence)

    uv run pytest -q <영향 검사 3파일>
      착수 기준선  -> 94 passed
      수리 후      -> 97 passed        (검사 함수 +3, 일치)

    uv run pytest -q      (전 스위트, 커밋 4837ef2 이후)
      -> 10534 passed, 12 skipped in 158.63s

    uv run ruff check <바뀐 4파일>          -> All checks passed!
    uv run ruff format                       -> 재포맷 1건, 전부 내가 넣은 줄

### 대조군 두 팔 (§3)

**팔 1) 새 검사가 잡는가** — 수리 후 97 passed, 그중 셋이 t167 이 더한 팔.

**팔 2) 기존 상태에서는 못 잡는가** — 프로덕션 두 파일만 `origin/main` 판으로 되돌려:

    -> 3 failed, 28 passed
       FAILED ... test_a_refused_groups_section_now_carries_the_classified_reason
       FAILED ... test_the_two_classifications_no_longer_read_the_same
       FAILED ... test_a_readable_section_carries_no_refusal

🔴 **정직한 단서**: 넷째 팔 `test_the_fid_axis_channel_is_untouched` 는 **양쪽에서 초록**이다.
그것은 「잡는 팔」이 아니라 **불변식 팔**이라 정상이며, 팔 2 만 보면 값을 안 하는 것처럼
보인다. 그 팔이 실제로 무엇을 가르는지는 아래 M-C 가 보인다.

### 뮤테이션 — 축 하나씩 (§3)

| 뮤턴트 | 축 | 결과 | 빨개진 것 |
|---|---|---|---|
| M-A `refusal=section_reason[0]` -> `None` (detail 은 남김) | 코드 필드 | **KILL** | 코드 단언 둘 |
| M-B 페이로드의 두 줄 삭제 | 운반 | **KILL** | 도구 층 하나 (매퍼 층 초록) |
| M-C 새 필드 대신 `console_read_reason` 재활용 | 채널 설계 | **KILL** | **축 분리 팔 하나뿐** |

M-C 가 이 판정의 핵심이다. 「한 채널에 두 축」은 가장 솔깃한 오설계인데, 그것을 가르는
유일한 팔이 팔 2 에서 값을 안 해 보이던 넷째 팔이었다. **불변식 팔의 값어치는 팔 2 가
아니라 뮤테이션에서 드러난다.**

등가 뮤턴트 아님: 셋 다 동작을 바꿨고 빨강이 났다. 생존이 0이라 §3 의 「생존을 읽는
여섯 갈래」는 적용 대상이 없다.

**「적용 안 됨」은 단언으로 쟀다(§3).** 회차마다 치환 전에 `assert s.count(anchor) == 1`
을 걸었고, **실제로 한 번 걸렸다**: M-B 의 첫 시도가 `AssertionError` 로 멈췄다 — 앵커
두 줄이 형제(프리셋) 페이로드 `tools.py:4978` 에도 **바이트 동일**로 있어 유일하지
않았기 때문이다. 눈으로 봤으면 「적용됐다」고 믿고 지나갔을 자리다. (그 중복 자체가
이 카드의 목표가 달성됐다는 부수 증거이기도 하다 — 이름이 형제와 같아졌다.)

**계기 오염(§3 여섯째 갈래) 검산.** 이 배치는 `PYTHONDONTWRITEBYTECODE=1` 없이 돌았다.
그래서 끝난 뒤 `find server -name __pycache__ -type d` 25개를 지우고, 바이트코드 기록을
끈 상태로 다시 돌려 **97 passed** 를 재확인했다. 초록이 낡은 바이트코드의 산물이 아니다.

## 3. 기준 귀속 (Baseline-attribution)

트리 `.claude/worktrees/t167`, 브랜치 `WT-group-refusal-reason`, base `origin/main` 17af4aa
(착수 시 `git rev-list --count --left-right origin/main...HEAD` = `0 0`).
기준선 94 는 이 트리·이 base 에서 잰 값이고, 전 스위트 10534 는 커밋 4837ef2 이후 값이다.

## 4. 안 잰 것 (Gaps)

- **계약이 「추가만」인지는 잰 것이다, 가정이 아니다.** 리드가 구멍을 지목했다 —
  「incomplete=True + reason=null」 조합 자체를 축 역산 신호로 쓰는 자리가 있으면
  추가가 아니라 계약 변경이다. 전수했다: `console_read_reason` 의 비주석 독자는
  생산자(`tools.py:4769`)와 특성화 검사 **둘뿐**이고, `console_read_incomplete` 의
  다른 소비자 셋(`test_lxseq_group_mapper:234`, `test_unmeasured_is_not_empty:277·283`)은
  **불리언만** 단언한다. `null` 을 조건으로 쓰는 자리는 **없다.**
- 🔴 **도구 층에서 `console_unreachable` 은 여전히 도달 불가다.** 4절이 기록한
  기존 결함이다 — 픽스처 경로가 죽으면 `read_existing_fids` 가 예외를 안 잡아 도구가
  거절이 아니라 죽는다. **t167 은 그것을 고치지 않았다**(축이 다르다). 그래서 이 도구의
  사용자가 실제로 볼 수 있는 분류는 여전히 `path_not_resolved` 하나다. 두 분류가 갈리는
  것은 매퍼 층에서만 관측된다. **후속 카드 후보로 리드에게 보고한다.**
- **실기 미검증** — 가짜 콘솔만 탔다. 콘솔 불필요 카드라 원래 범위 밖이다.
- **사유를 살리면 진단이 실제로 달라지는지** 안 쟀다. 카드가 그렇게 적었고 유지한다.

## 5. 잔여 위험 (Residual-risk)

- `refusal` 코드는 두 분류에서 **같다**(`section_unread`). 갈리는 것은 detail 문자열이라,
  하류가 코드로 분기하면 여전히 못 가른다. 그것을 코드로 옮기려면 이 도메인에 어휘를
  새로 만들어야 하고 소비자가 0이므로 t109 의 갈라짐을 다시 만든다 — 의도된 선택이다.
- detail 문면이 바뀌면 문구 단언이 깨진다. 의도된 취약성이다 — 사유가 바뀌면 사람이 본다.
- 형제와 이름이 같아졌으므로(`tools.py:4770` 과 `:4978`), 앞으로 한쪽만 고치면 다시
  갈린다. 그 위험은 이름을 맞춘 대가다.
