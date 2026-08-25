# t62 — pre-push 훅 템플릿의 거짓 문서 힌트 (upstream 리포트 본문)

- 카드: t62 · 브랜치 `WT-prepush-doc-report` · base `c673ef4`
- 측정일: **2026-08-25** · 대상 `moai-adk 3.1.2`(`moai --version` 실측)
- **[HARD] 파일을 안 고쳤다. 그리고 이 리포트를 어디에도 제출하지 않았다** — 제출은 감독 결정이다.

## 0. 왜 로컬 수정이 처방이 아닌가

그 훅 파일은 **2행 마커**(`# MoAI-ADK pre-push hook …`)를 갖고 있고, t55 의 2팔 실험은
마커가 있으면 `moai update` 가 **덮어쓴다**는 것을 측정했다(A 마커있음 → 덮임 · B 마커없음 →
보존, B 가 음성 대조군). 그래서 여기서 고쳐도 **다음 `moai update` 에 지워진다.**
고칠 수 있는 자리는 upstream 템플릿뿐이고, 이 카드의 산출물은 **리포트 본문**이다.

## 1. 오늘 다시 뜬 인용 (t55 값을 옮기지 않았다)

배차서 [HARD] 대로 어제 값을 인용하지 않고 **오늘 파일에서 다시 떴다.**

```
L3   # Bypass via: SKIP_MOAI_PREPUSH=1 git push   (logged on next invocation)
L49      printf '[pre-push] Override (logged on next invocation): SKIP_MOAI_PREPUSH=1 git push\n' >&2
```

두 줄 다 **「(logged on next invocation)」** 을 약속한다. `grep -ci "logged"` → **2건**.

## 2. 실제로 일어나는 일

우회 갈래는 **로그를 쓰기 전에 나간다**:

```
L7-10   if [ "${SKIP_MOAI_PREPUSH:-0}" = "1" ]; then
            printf '[pre-push] SKIP_MOAI_PREPUSH=1 -- bypass requested\n' >&2
            exit 0          ← 여기서 끝난다
        fi
...
L44     printf '%s\t%s\t%s\t%s\t%ds\n' "$END_TS" "$USER_NAME" "$BRANCH" "$OUTCOME" "$DURATION" >> "$LOG_FILE"
```

그리고 **다음 실행도 우회를 기록하지 않는다.** L44 가 쓰는 열은
`END_TS · USER · BRANCH · OUTCOME · DURATION` 다섯이고, `OUTCOME` 의 값은 세 곳에서만 온다:

```
L26  OUTCOME="pass"
L30  OUTCOME="fail"
L34  OUTCOME="skip (no Makefile)"
```

**우회를 나타내는 값이 없다.** 즉 「다음 실행에 기록된다」는 두 방향 모두 거짓이다 —
그때도 안 남고, 나중에도 안 남는다.

> 파일 이름이 **`prepush-bypass.log`** 다. 이름과 두 주석이 함께 약속하는 감사 기록이
> 실제로는 **한 번도 만들어지지 않는다.**

## 3. 재현 절차 (음성 대조군 포함)

**이 절이 이 리포트의 본체다.** 재현 없는 리포트는 「내 환경에선 되는데요」로 닫힌다.

```sh
# 전제: moai-adk 가 훅을 배포한 git 저장소 안. 로그 경로는 REPO_ROOT 기준이다.
LOG="$(git rev-parse --show-toplevel)/.moai/logs/prepush-bypass.log"

# [1] 기준선
ls -la "$LOG" 2>/dev/null || echo "(아직 없음)"

# [2] 우회를 쏜다 — 실제 push 없이 훅만 직접 실행
SKIP_MOAI_PREPUSH=1 sh "$(git rev-parse --git-common-dir)/hooks/pre-push" \
    origin https://example.invalid/x.git < /dev/null
echo "exit=$?"

# [3] 로그가 늘었는가?   → 늘지 않는다 (기대: 「우회 기록」 1줄)
ls -la "$LOG" 2>/dev/null || echo "(여전히 없음)"

# [4] 음성 대조군 — 우회 없이 같은 훅을 실행
sh "$(git rev-parse --git-common-dir)/hooks/pre-push" \
    origin https://example.invalid/x.git < /dev/null

# [5] 이번엔 한 줄이 붙는다. 그 줄에 우회 흔적이 있는가? → 없다
cat "$LOG"
```

### 3.1 이 저장소에서 실측한 결과 (2026-08-25)

깨끗한 환경이 마침 있었다 — 워크트리 `t62` 에는 그 로그 파일이 **없었다.** 위 [2]와 [4]를
그 워크트리에서 순서대로 실행한 뒤:

```
$ cat .../worktrees/t62/.moai/logs/prepush-bypass.log
1787612589	studiox	WT-prepush-doc-report	pass	19s
```

**정확히 한 줄.** [2]의 우회는 **0줄**을 남겼고, [4]의 정상 실행이 자기 결과(`pass`)만
남겼다. 그 줄 어디에도 앞선 우회의 흔적이 없다(`grep -ci "skip_moai|bypass"` → **0**).

기존 저장소의 누적 로그도 같은 그림이다:

```
$ cut -f4 .moai/logs/prepush-bypass.log | sort | uniq -c
  87 skip (no Makefile)
```

**87건 전부 한 값**이고, 우회를 나타내는 항목은 **0건**이다.

## 4. `pre-commit` 은 같은 결함이 없다 (t55 가 미검증으로 남긴 자리)

같은 마커 모양을 갖는다:

```
pre-commit L2   # MoAI-ADK pre-commit hook — fast subset (gofmt + go vet) + heavy gate (moai gate)
```

그러나 **거짓 주장이 없다** — 애초에 로그를 약속하지 않고, 로그를 쓰지도 않는다:

```
pre-commit:  grep -ci "logged"                        → 0
pre-commit:  grep -ciE "LOG_FILE|LOG_DIR|>> "         → 0
pre-push  :  grep -ci "logged"                        → 2
```

`pre-commit` 의 우회 안내는 `Override: SKIP_MOAI_PRECOMMIT=1 git commit` 뿐이고
**기록을 약속하지 않는다.** 내부적으로 일관된다 — **리포트에 넣을 필요가 없다.**

## 5. 제안하는 수정 (upstream 이 고를 것)

둘 중 하나면 문면과 동작이 다시 일치한다.

| | 무엇 | 대가 |
|---|---|---|
| **A — 문서를 동작에 맞춘다** | L3·L49 에서 `(logged on next invocation)` 를 지운다 | 감사 기록은 여전히 없다. 파일 이름 `prepush-bypass.log` 도 같이 봐야 한다 |
| **B — 동작을 문서에 맞춘다** | 우회 갈래(L7-10)가 `exit 0` 전에 `OUTCOME="bypass"` 로 로그 한 줄을 쓴다 | 훅이 하는 일이 늘고, `LOG_DIR` 생성이 우회 경로로 앞당겨진다 |

**A 가 싸고 B 가 이름값을 한다.** 어느 쪽이든 **지금은 이름·주석·동작 셋이 서로 다르다.**

## 6. Gaps — 재지 않은 것

- 🔴 **처음에 엉뚱한 로그 파일을 봤다.** 우회 실행 뒤 **primary 체크아웃**의 로그를 재고
  「안 늘었다」로 읽을 뻔했는데, 그 실행의 `REPO_ROOT` 는 워크트리라 애초에 그 파일을
  건드리지 않는다. **맞는 결론을 틀린 근거로 적을 뻔했다.** §3.1 은 실제 대상 파일에서
  다시 잰 값이다.
- **`moai update` 가 `pre-commit` 도 덮어쓰는지는 안 쟀다.** 같은 2행 마커 **모양**을
  갖는다는 것만 확인했다. t55 의 2팔 실험은 `pre-push` 에 대해서만 돌았고, 나는
  `pre-commit` 으로 그 실험을 반복하지 않았다 — **「같은 마커니 같이 덮인다」는 추론이지
  측정이 아니다.**
- **바이너리 내장 템플릿 원본과 배포본을 바이트 비교하지 않았다.** 배포본
  (`.git/hooks/pre-push`)에서 인용했다. t55 가 「마커 있으면 덮인다」를 측정했으므로
  배포본은 템플릿에서 온 것으로 본다 — 다만 **그것도 t55 의 측정이지 오늘 내 측정이 아니다.**
- **upstream 저장소를 열어 보지 않았다.** 이 결함이 이미 보고돼 있는지, 최신 판에서
  고쳐졌는지 모른다. **제출 전에 그것부터 확인해야 한다.**
- **실제 `git push` 로는 재현하지 않았다.** 훅을 직접 실행했다 — 훅에 들어오는 stdin 형식은
  같지만(빈 입력), 실제 push 경로에서 git 이 다르게 부를 가능성은 배제하지 못했다.

---

## 부록 — 제출용 영문 본문 (아직 제출하지 않음)

> 제출 여부는 감독 결정이다. 아래는 그때 쓸 수 있도록 만들어 둔 본문이며,
> upstream 이 읽을 수 있도록 영문으로 적었다.

**Title**: `pre-push` hook comments promise bypass logging that never happens

**Version**: moai-adk 3.1.2 · measured 2026-08-25

**What the template says** — `templates/.git_hooks/pre-push`:

```
L3   # Bypass via: SKIP_MOAI_PREPUSH=1 git push   (logged on next invocation)
L49      printf '[pre-push] Override (logged on next invocation): SKIP_MOAI_PREPUSH=1 git push\n' >&2
```

**What happens** — the bypass branch returns before the log is written, and no later
invocation records that a bypass occurred:

- The bypass branch prints to stderr and `exit 0` at L9.
- The only write to the log is at L44, after that exit.
- The `OUTCOME` field written there is assigned in exactly three places (L26 `pass`,
  L30 `fail`, L34 `skip (no Makefile)`). **No value denotes a bypass.**

So the phrase *(logged on next invocation)* is false in both directions: not then, not later.
The log file is named `prepush-bypass.log` and never records a bypass.

**Reproduction** (negative control included) — see the shell block in §3 above.

**Observed** in a clean tree where the log did not yet exist: the bypass run produced **zero**
lines; the following normal run produced exactly one line, `… pass 19s`, with no bypass trace.
In an existing repository, all 87 accumulated entries carry the single value
`skip (no Makefile)` and none denotes a bypass.

**`pre-commit` is not affected** — it makes no logging claim and performs no logging
(`grep -ci "logged"` → 0).

**Suggested fix** — either drop `(logged on next invocation)` from L3/L49, or write a
`bypass` outcome line before the early `exit 0`. The file name suggests the latter was intended.
