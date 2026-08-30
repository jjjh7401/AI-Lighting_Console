# t142 — Focus·Frost 거절은 철자였다. 사유를 이름별로 가른다

- 카드: t142 · SPEC-COPILOT-LOOKLIB-001 · 기준 `c40401e`
- 트리 `.claude/worktrees/t142` · 브랜치 `WT-beam-reject-basis`
- **콘솔 접촉 0.** 문서 판독과 편집뿐이다. 코드 로직 변경 0, 단언 변경 0.

## 0. 결론 — 배차서의 「2자리」가 두 방향으로 틀렸다

| | 배차서 | 실측 |
|---|---|---|
| 같은 주장이 있는 곳 | 2자리 | **7자리** (추적 파일 전량 grep) |
| **고친** 곳 | 2자리 | **6자리 + 만료 고지 1** |
| **못 고친** 곳 | — | **1자리 (정본)** — PRESERVE 게이트 둘이 잠근다 |

더 넓게 퍼져 있었고, 정작 정본은 손댈 수 없었다.

## 1. 무엇이 만료됐나 — 값이 아니라 독법이다

`SPEC-COPILOT-LOOKLIB-001/progress.md` 측정 1(2026-07-26 · 응답기 v1.4.1 ·
선택 `Group 13`=`All`)은 넷을 거절로 기록하면서, **스스로 한정을 달아 뒀다**:

    `Illegal object` 는 (i) MA3가 모르는 attribute 이름 과
    (ii) 선택된 픽스처가 그 속성을 갖지 않음 — 양쪽과 모두 정합한다

t135 4회차 실기가 그 한정을 갈랐다. **그리고 이름마다 답이 다르다:**

| 후보 | 2026-07-26 결과 | 갈린 뒤 |
|---|---|---|
| `Focus` | ok=False, `Illegal object` | **(i) 이름 — 철자.** 채널명 `Focus1`. `Attribute 'Focus1' At 50` → `ok=True, OK` |
| `Frost` | ok=False, `Illegal object` | **(i) 이름 — 철자.** 채널명 `Frost1`. `Attribute 'Frost1' At 50` → `ok=True, OK` |
| `Prism1` | ok=False, `Failed` | **(ii) 픽스처 — 진짜 부재.** MegaPointe·MMX Spot 어느 모드에도 `Prism` 채널 없음 |
| `Shutter` | ok=False, `Illegal object` | **미확정.** 채널 `Shutter1` 은 존재하나 값을 쏜 적이 없다 |

근거: PR #191 → main `fa24d1b` 의 `.moai/reports/t135/beam-attrs.md` §21·§22·§23.
2026-08-30 · `Fixture 501`(Robin MegaPointe) 단독 · 응답기 1.6.2 ·
Store·ClearAll 없이 `Off Fixture 501` 로 해제.

**표의 값은 지금도 참이다.** 틀린 것은 그 넷을 하나의 사유로 읽던 문장이다.

### 1.1 Shutter 를 「철자」로 쓰지 않은 이유

`Shutter1` 이라는 **채널명이 존재한다**까지가 실측이고, **그 값이 받아들여진다**는
별개 명제다. t135 는 `Shutter1` 을 쏘지 않았다 — `schema.py:18` 이 danger 정책으로
배제한 대상이라 승인 범위 밖이었다(t135 §19-2·§23). 그래서 문면에도 두 명제를
갈라 적었다. 붙여 쓰면 이 저장소가 반복해 밟은 「존재는 도달의 증거가 아니다」가 된다.

## 2. 고친 6자리 — 전부 「지금 이렇다」로 읽히는 서술

| 자리 | 무엇 |
|---|---|
| `server/tests/test_looks_schema.py` 밴드3 주석 | 넷을 한 사유로 묶던 한 줄 → 사유 3분류 + 정본 포인터 |
| `server/tests/test_looks_schema.py` `Frost` 거절 검사 주석 | 「콘솔이 못 받는다」 → 「스코프 경계를 단언한다」 |
| `server/tests/test_looks_library.py` `FORBIDDEN_ATTRIBUTE_TOKENS` 주석 | 같은 3분류 + 스코프 경계는 사유와 무관히 유지됨을 명시 |
| `server/tests/test_looks_library.py` 자산 스캔 주석 | 사유가 이름마다 다름을 위 주석으로 위임 |
| `server/tests/test_lxseq_preset_parser.py` `TestStorability` 독스트링 | 「다시 열지 마라」는 유지하되 「콘솔이 못 받는다」로 읽히지 않게 |
| `docs/proposals/song-lighting-design-standard.md` 현 콘솔 능력 경계 표 | 한 괄호에 묶인 셋을 갈랐다 + 주 추가 |

여섯 자리 모두 **정본이 아직 옛 사유를 말한다는 포인터**를 함께 박았다(§3).

## 3. 못 고친 자리 — 정본은 PRESERVE 잠금이다

`server/looks/schema.py:16-18` 이 이 계열의 정본인데, **두 검사가 그 파일에
`git diff` 빈 출력을 단언한다**:

| 검사 | 목록 | 기준 |
|---|---|---|
| `test_overlap_preserve.py::TestPreserveDiffIsEmpty::test_the_preserved_paths_are_unchanged` | `_PRESERVE_PATHS` (10경로) | `95687a0e` |
| `test_songcue_bundle.py::test_preserve_look_files_are_unchanged_from_run_phase_base` | `_PRESERVE_LOOK_FILES` (6파일) | `38a6e7e2` |

**둘 다 건너뛰지 않고 실제로 돈다** — 각각 `1 passed`.

### 3.1 게이트를 쏴서 확인하지 않았다 — 재현 가능한 대체 방법

확인과 사고가 같은 행위인 자리라, 커밋해서 빨갛게 만들지 않았다.
**두 명령의 차이**가 증명이다:

    git diff --stat 95687a0e..HEAD -- server/looks/schema.py   # 게이트가 보는 것
    git diff --stat 95687a0e     -- server/looks/schema.py   # 내 작업트리

편집분이 있을 때 앞은 빈 출력, 뒤는 `1 file changed, 17 insertions(+), 3 deletions(-)`.
커밋하면 앞이 뒤가 된다. 잠금은 **커밋 경계에서만** 발동하므로, 작업트리 편집만으로는
스위트가 초록이다 — 이 카드가 「커밋 → 스위트 → 보고」 순서를 지킨 이유다.

처분: 예외 심사는 **t149**. 안전장치를 무르는 결정이 문면 정정 카드에 딸려 들어가면
안 된다고 판단했고 리드가 받았다.

## 4. 안 고친 기록 — 만료 고지만

`.moai/specs/SPEC-COPILOT-LOOKLIB-001/progress.md` 측정 1: **24줄 삽입 · 0줄 삭제**.
표의 숫자·결과·`Prism1` 의 `Failed` 보존 문장 전부 불변. 고지는 그 아래 인용 블록으로
붙였고 「위 기록은 한 글자도 고치지 않았다」를 머리에 적었다.

## 5. 검증

### 5.1 리드가 건 불변식 — 스위트가 안 움직여야 한다

산문만 고쳤으니 통과·스킵·실패가 편집 전후로 정확히 같아야 한다.

    편집 전 (기준 c40401e, 깨끗한 트리)  10471 passed, 12 skipped, 1 warning   exit 0
    편집 후 (커밋된 HEAD)                10471 passed, 12 skipped, 1 warning   exit 0

`.moai/reports/t142/suite-before.txt` · `suite-after.txt` (트리 로컬).

PRESERVE 게이트 둘도 커밋 후 초록:

    pytest -k preserved_paths_are_unchanged        -> 1 passed
    pytest -k preserve_look_files_are_unchanged    -> 1 passed
    git diff --stat 95687a0e..HEAD -- server/looks/schema.py  -> 빈 출력

### 5.2 그 불변식이 공허하지 않다는 대조군

「수치가 같다」는 스위트가 그 파일을 **실제로 훑을 때만** 증거다. 그래서 쏴 봤다:

    assert PROBE_GATED_ATTRIBUTES == ("Zoom", "Iris")   ->   == ("Zoom",)

결과 **KILLED** — `1 failed, 62 passed`,
`test_band_three_is_the_m0_resolved_beam_vocabulary` 에서 잡혔다.
복원 후 체크섬 일치(`4ff65b3e…fe05e`), `git status --short` 빈 출력.

### 5.3 lint

    ruff check server/        -> All checks passed!   exit 0
    ruff format --check (편집 3파일)  -> 3 files already formatted   exit 0

## 6. 뮤테이션 — 왜 이 카드엔 대상이 없나 (지어내지 않았다)

이 카드의 변경은 **전량 주석·독스트링·마크다운**이다. 술어가 없으니 뒤집을 것이 없고,
주석을 바꿔 통과가 유지되는 것은 결함이 아니라 **정의상 당연**하다. 없는 뮤테이션을
만들어 「N/N KILLED」로 적으면 그 수치가 아무것도 안 지킨다.

대신 이 카드에서 falsifiable 한 것은 **「단언을 안 건드렸다」** 쪽이고, 그것은 §5.1의
수치 동일성으로 재고 §5.2의 대조군으로 공허성을 막았다. 대조군이 KILLED 를 냈으므로
수치 동일성은 실제 판별력을 가진 진술이다.

## 7. 안 잰 것 (gap)

1. **`Shutter1` 의 값 수용** — 안 쐈다. danger 정책 배제라 승인 범위 밖이고, 이 카드는
   콘솔에 아무것도 안 보냈다. 「채널명 존재」와 「값 수용」은 계속 별개로 둔다.
2. **BM.04 가 열리는가** — 안 열었다(리드 §4 지시). t135 가 이미 쟀듯
   `LXSEQ_PRESET_APPLY_ATTRIBUTE` 는 `preset-dim` 하나뿐이고 bm 은 표에도 분기에도
   없다(`server/orchestrator/tools.py:1691` 주석: 「dim 만 남은 것은 누락이 아니라
   판정」). **정본을 고쳐도 갈 곳이 없다.** 실기 검증은 별도 카드.
3. **`EFFECTWHEEL` 이 프리즘 등가인지** — t135 §26-1 이 남긴 미지. 로베 명명 관례는
   저장소 밖 지식이라 추측으로 메우지 않았다. `Prism` 을 「진짜 부재」로 쓴 근거는
   「`Prism` 이라는 이름의 채널이 없다」까지이지 「프리즘 기능이 없다」가 아니다.
4. **정본 `schema.py:16-18`** — §3. t149.
5. **다른 카드 소유 자리** — 안 건드렸고 사유는 각각 다르다:
   - LXSEQ-003 문면 4파일 → **t146**
   - `server/lxseq/preset_parser.py` 튜플(`:87`)과 그 위 주석 블록(`:70`·`:78-86`),
     `test_lxseq_preset_beam_vocabulary.py` → **t141**. 주석이 튜플의 존재 이유를
     설명하는 한 몸이라 갈라 고치면 t141 과 충돌한다(파일이 아니라 의미로 그은 경계)
   - `SPEC-COPILOT-SONGSTD-001/research.md:92` → **t148**. 남의 SPEC 본문이라
     소유권이 manager-spec 이다
   - `.moai/reports/cue-ex-columns/parity-and-live.md:227` → **t148**. 그 시점 기록이라
     정정 대상이 아니라 만료 고지 대상이다
6. **`_PROBE_REJECTED` 를 정본 철자에 맞추면 회귀한다** — t135 가 이미 쟀다. 이 카드는
   그 튜플을 안 봤고 안 건드렸다. 「정합성 개선」으로 손대면 BM.03 이 열린다.

## 8. 잔여 위험

- 고친 6자리가 정본과 **의도적으로 어긋난 상태**로 남는다. 포인터를 박아 문서화했지만,
  t149 → 정본 정정이 안 오면 그 어긋남이 그대로 굳는다. 침묵하는 모순보다는 낫되
  영구 해법은 아니다.
- `Focus1`·`Frost1` 이 통과한 것은 **Fixture 501 한 대 · 한 모드**다. 다른 기종에서도
  같은 철자인지는 안 쟀다. 문면은 「이 리그에서」로 한정해 적었다.
- 이 보고서의 스위트 수치는 이 트리·이 커밋 기준이고 CI 초록이 아니다. PR CI 는
  머지 결과를 잰다.
