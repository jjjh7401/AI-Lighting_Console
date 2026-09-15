## 무엇을 바꾸나

PRESERVE 기준 커밋 게이트를 **skip 에서 실패로** 바꾼다. `server/tests/test_songcue_bundle.py` 한 파일.

`_requires_run_phase_base`(skipif 마커) → `_require_run_phase_base()`(원인과 처방을 말하는 실패).
호출 모양은 같은 저장소의 `_require_codesign()`(`test_deploy_tauri_shell.py`)을 따랐다 — 새 관용구를 만들지 않는다.

## 왜

두 검사가 **CI 에서 매 실행 조용히 건너뛰어지고 있었다.**

```
SKIPPED [1] server/tests/test_songcue_bundle.py:464: run-phase base 커밋이 이 클론에 없다 …
SKIPPED [1] server/tests/test_songcue_bundle.py:478: (같음)
```

기준 커밋 `38a6e7e2` 가 스쿼시 머지로 어느 브랜치에서도 도달 불가가 됐고, `skipif` 가 그 사실을 침묵으로 바꿨다.
**침묵은 초록으로 읽힌다** — PRESERVE 불변식을 아무도 안 보는 상태가 오래 갔다(t59 에서 발견).

그 사이 두 가지가 정리됐다.

1. 커밋을 주석태그 `preserve-base-songcue-m0` 으로 origin 에 고정했다(영구 소실 위험 해소).
2. 이 저장소 CI 의 checkout 이 태그를 **실제로 받는다**는 것을 로그로 쟀다(아래).

## 🔴 리뷰어가 먼저 알아야 할 것 — **이 PR 의 CI 실행이 실험이다**

게이트가 없어졌으므로, 러너에서 기준 커밋이 안 오면 이제 skip 이 아니라 **빨간불**로 나타난다.

**그 빨간불은 결함이 아니라 측정 결과다.** 나오면 읽을 곳은 이 PR 의 코드가 아니라
`.github/workflows/test.yml` 의 `fetch-depth` 다. 실패 메시지 자체가 그렇게 안내한다.

기대값: 두 검사가 CI 에서 **실제로 돌아** pytest 통과 수가 `10013 → 10015`, skip 은 `22 → 20`.
통과 수만 보면 skip 과 구분이 안 되니 **skip 수를 같이 본다.**

## 근거 — CI 가 실제로 발행한 fetch 명령 (로그 실측, t64)

| 실행 | 트리거 | fetch-depth | `--depth=1` | `+refs/tags/*` |
|---|---|---|---|---|
| `32620440718` | pull_request | (기본) | 있음 | **없음** |
| `32719438723` | pull_request | 0 | 없음 | **있음** |
| `32719982356` | push | 0 | 없음 | **있음** |

트리거는 두 값 모두에 나타나고 결과를 가르지 않는다. **`fetch-depth` 만 결과와 함께 움직인다.**
`--no-tags` 가 붙어 있지만 명시 refspec `+refs/tags/*:refs/tags/*` 이 이긴다 — 문서가 아니라
고아 커밋을 만들어 A/B 로 재현해 확인했다(태그 refspec 있으면 옴 / 빼면 안 옴, 양성·음성 대조군 포함).

그래서 `fetch-depth: 0` 은 지금 **두 가지**를 떠받친다 — PRESERVE 의 `git diff <고정 SHA>..HEAD` 범위와
태그 도달. 얕은 클론으로 되돌리면 **둘이 동시에** 죽는다. 이 결합을 게이트 독스트링에 박아뒀다.

## 검증

- 게이트 제거 **전** 두 검사 지명 실행 → `2 passed` (숨어 있던 빨간불 없음)
- 제거 후 파일 전량 → `20 passed`, skip 0
- **날조 대조군**: 기준 SHA 를 `0000…0001` 로 치환 → 두 검사 모두 `AssertionError`.
  진짜 기준에서는 무예외 — 빨간불은 날조가 만든 것이지 하네스가 늘 실패하는 게 아니다.
  (`Skipped` 가 섞이면 잡히도록 판정 축을 "무엇을 던지는가"로 잡았다. 안 섞였다.)
- `ruff check` / `ruff format --check` 통과
- 옛 마커는 이 파일에서만 쓰였다(grep 확인) — 파일 밖 파급 없음

## 미검증

- 로컬 전량 스위트는 안 돌렸다(다른 레인이 사용 중). 전량은 이 PR 의 CI 몫이다.
- 원격 태그를 실제로 삭제해보는 시나리오는 추론으로 남긴다 — 재려고 태그를 지우지 않는다.

🗿 MoAI
