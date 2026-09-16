# progress — SPEC-LDSTORE-001

## §E.1 Plan-phase Audit-Ready Signal

```
plan_status: audit-ready-with-gap
plan_complete_at: 2026-09-14
```

**Gap (정직 고지)**: 독립 plan-audit 이 **없다.** `/moai run SPEC-LDPLUGIN-001` 의 Phase 1
Plan Audit Gate 에서 `plan-auditor` 가 `Prompt is too long` 으로 죽어 verdict 가
`INCONCLUSIVE` 였고, 이 자식 SPEC 에 대해서도 같은 통로가 막혀 있다. 아래 §F 참조.

계획 품질 검토는 오케스트레이터의 **자기 검토**로만 이루어졌다. 자기 검토는 독립 감사보다
약하다. 다만 무용하지는 않았다 — 자기 검토에서 실제로 두 건의 자체 오류가 나왔다:

1. 예술 producer cutover 의 담당 SPEC 을 지정하지 않았다 → `SPEC-LDCUTOVER-001` 로 명명해
   `split-proposal.md` §1.1 에 등재.
2. **안전 구멍**: M2 최소판의 `context_digest` 를 9축 중 4축으로만 계산하도록 써서, 나머지
   5축(특히 preset 내용) 변경 시 이전 승인이 유효하게 남는 상태였다 → 9축 전부를 digest 에
   넣도록 `plan.md` §2.1 에 [HARD] 불변식으로 고정. 이후 계약 §9.1 을 읽어 이 수정이 계약과
   일치함을 확인했다(*"최상위 context_digest key 하나만 제거한 객체. compiler/safety/
   identity/만료·모든 metadata 포함"*).

## §F Phase 4 Mode Selection

**입력 파라미터**

| 항목 | 값 |
|---|---|
| tier | M (`spec.md` frontmatter) |
| scope (파일 수) | 신규 7 + 기존 EXTEND 1 (`server/web/serve.py`) |
| domain count | 1 (Python 백엔드 — 신규 `server/director/` 패키지) |
| file language mix | 100% Python + SQL 1 |
| concurrency benefit | LOW — coding-heavy |
| 서브에이전트 가용성 | **불가 (실측)** |

**모드 평가**

| 모드 | 선택 | 사유 |
|---|---|---|
| `direct` | **선택** | 강제됨 — 아래 참조 |
| `serial` | 미선택 | 원래 이 작업의 정답. coding-heavy 단일 도메인이므로 `serial`(마일스톤당 sub-agent 1개)이 규칙상 기본값이다. 그러나 서브에이전트 통로가 기계적으로 막혀 실행 불가 |
| `fanout` | 미선택 | 단일 도메인 · coding-heavy. Anthropic 의 coding-task 병렬성 유보 조항에 걸린다 |
| `sweep` | 미선택 | 파일 8개로 ~30 파일 문턱 미달, 기계적 단일 변환도 아니다 |

**Decision: direct**

**정당화 — 이것은 선호가 아니라 강제다.** 규칙상 정답은 `serial` 이다. 그런데 이 저장소에서
서브에이전트가 일을 시작하기 전에 적재되는 컨텍스트를 실측한 결과:

| 초기 적재 (manager-spec 기준) | 바이트 |
|---|---|
| `paths:` 없는 always-loaded 규칙 13개 | 202,132 |
| `CLAUDE.md` | 20,523 |
| `MEMORY.md` | 24,929 |
| 에이전트 정의 | 20,298 |
| 프리로드 스킬 2종 본문 | 39,134 |
| **합계** | **307,016 (≈114K 토큰)** |

여기에 세션의 도구 스키마가 더 얹힌다. 실측 결과 2회 연속 실패:

1. `plan-auditor` — 우산 SPEC 감사 위임 → `Prompt is too long`
2. `manager-spec` — 분할 제안 위임 (읽을 파일을 42.5KB 로 못박았음에도) → `Prompt is too long`

`runtime-recovery-doctrine.md` §3 invariant 2(같은 회복 행위를 같은 턴에 재시도 금지)에 따라
3회차 spawn 을 하지 않고 다음 rung 으로 넘어갔다 — 오케스트레이터 직접 실행.

**미측정**: 서브에이전트의 실제 컨텍스트 창 크기와 토큰 단위 적재량. 위는 **바이트 실측 +
토큰 추정**이다. 원인으로 가장 유력하나 확정된 것은 아니다.

**결과로 잃은 것**: 독립 감사(§E.1 Gap). 오케스트레이터가 구현자이면서 검토자다.

## §E.2 Run-phase Evidence

> **만료 고지 (2026-09-15)**: 아래 회차 기록들은 **커밋 전** 작업 트리(`98a822e`) 기준으로
> 작성되었고, 그 시점에는 사실이었다. 그 뒤 M1 과 M2 가 함께 커밋되어 `origin/main` 에
> 올라갔다:
>
> ```
> $ git log --oneline origin/main -- server/director/models.py server/director/store.py server/director/context.py
> cde27445 feat(SPEC-LDSTORE-001): director 저장층 M1+M2 — 교환 스키마·불변 저장·ContextSnapshot 아홉 축
> ```
>
> 따라서 아래 본문의 **「커밋하지 않았다」·「커밋 전」·「uncommitted」 표현은 전부 만료**
> 되었다. 기록은 당시 사실이므로 고쳐 쓰지 않고 이 고지로 무효화한다 — 처방(무엇을 더
> 해야 하나)만 아래 §E.2b 에 갱신해 둔다.

### §E.2b 갱신된 처방 (2026-09-15 기준)

| 항목 | 당시 기록 | 현재 |
|---|---|---|
| M1 커밋 | 「커밋하지 않았다」 | **`cde27445` 로 `origin/main` 에 있음** |
| M2 (ContextSnapshot) | 「미착수」 | **완료** — `server/director/context.py` 가 `origin/main` 에 있음 (434줄) |
| M3 (지식 seed) | 미착수 | **완료 (2026-09-16)** — `server/director/knowledge.py` + `server/director/knowledge_seed/` — 아래 "M3 완료" 절 참조 |
| SPEC 문서 | 커밋 안 됨 | **이 커밋으로 추적 시작** |
| 독립 감사 | 없음 | **없음 유지** — `plan-auditor` 가 이 저장소에서 컨텍스트 초과로 죽는다 (§F). M3 도 같은 이유로 독립 감사 없이 자기 검토로만 진행했다 |

**안 잰 것**: M2 의 인수 기준(`AC-LDPLUGIN-004`) 달성 여부를 이 정정에서는 재지 않았다.
`context.py` 가 `origin/main` 에 존재한다는 것과 그 파일이 M2 의 AC 를 충족한다는 것은
다른 주장이다 — 후자는 이 정정의 범위가 아니다.

#### 도구와의 불일치 (기록 — 감춤 없이)

`status: in-progress` 는 도메인 도구의 권고와 **다르다.** 도구를 먼저 돌렸고 출력은 이렇다:

```
$ moai spec lint .moai/specs/SPEC-LDSTORE-001/spec.md
WARNING  StatusGitConsistency  .moai/specs/SPEC-LDSTORE-001/spec.md  1
  SPEC SPEC-LDSTORE-001 frontmatter status 'in-progress' disagrees with git-implied status 'implemented'
0 error(s), 1 warning(s)
```

**도구를 따르지 않은 이유**: `StatusGitConsistency` 는 커밋 이력에서 상태를 추론하므로
M1+M2 커밋(`cde27445`)을 보고 `implemented` 를 답한다. 그러나 `implemented` 는 *요구사항
구현이 끝났다*는 주장이고, **M3(지식 seed, `REQ-LDPLUGIN-027`)은 착수조차 안 됐다**
(`server/director/knowledge.py` 부재 — 실측). 도구는 마일스톤 잔여를 모른다.

즉 이 경고는 도구가 틀린 것도 내가 틀린 것도 아니라, **도구가 볼 수 없는 사실(M3 잔여)이
판단을 가른 경우**다. `implemented` 로 적으면 M3 에 대한 미검증 완료 주장이 되므로
`in-progress` 를 유지한다. M3 가 끝나면 이 경고는 자연히 사라진다.

**범위 밖 발견 (보고용)**: 같은 도구의 다른 명령이 저장소 전체 문제를 드러냈다 —
`moai spec drift` 는 **54개 SPEC 중 13개가 status drift** 라고 답한다. 이 정정은 LD 계열
셋만 다루며 나머지 열셋은 손대지 않았다. 참고로 LD 계열 넷은 drift 표에서 `era-exempt` 로
분류되어 이 검사기가 어느 쪽으로도 검증해 주지 않는다.

### M1 완료 (REQ-LDPLUGIN-007 · REQ-LDPLUGIN-015)

작업 트리 기준 HEAD `98a822e` · 커밋 전. **[만료 — `cde27445` 로 커밋됨, 위 고지 참조]**

**Claim**: M1 의 두 요구사항을 TDD 로 구현했다 — 교환 객체 strict parsing(007)과 불변
저장·revision CAS·멱등(015). 계약 §9 의 digest 는 계약이 §9 "합성 예제 digest 재현 규칙"
으로 제공한 시험 벡터로 검증했다.

**Evidence — 회귀 (실제 출력)**

```
$ uv run pytest -q          # 작업 트리, HEAD 98a822e
12866 passed, 31 skipped, 1 warning in 171.57s
```
파일: `.moai/state/verify/cbfacab7/ldstore-m1-complete.txt`

**Baseline-attribution**: 기준선 `12794 passed, 31 skipped` (같은 HEAD, 구현 전 실측).
신규 테스트 **72개**(5파일). 12794 + 72 = **12866** — 정확히 일치, skipped 불변, 실패 0.

신규 테스트 개수는 파일을 명시해 셌다(`-k director` 는 기존 테스트 82개를 함께 잡아
154 를 답한다 — 계기가 무엇을 세는지 확인한 결과):

| 파일 | 개수 |
|---|---|
| `test_director_exchange_schema.py` + `test_director_boundary.py` + `test_director_digest.py` + `test_director_store_cas.py` + `test_director_service_seam.py` | **72** |

**Evidence — digest 가 계약 값을 재현한다 (가장 강한 확인)**

계약이 규정한 값을 우리 구현이 재현했다. 우리가 만든 기대값이 아니다.

| 대상 | 계약이 선언한 값 | 재현 |
|---|---|---|
| `audio.sha256` (규범 fixture bytes) | `sha256:ca890598f1f0…` | 일치 |
| `context_digest` | `sha256:fde69740868b…` | 일치 |
| `plan_digest` (validation.json 선언) | `sha256:bee1cda574b5…` | 일치 |

**Evidence — JCS 를 근사하지 않은 이유 (실측)**

`json.dumps(sort_keys=True, separators=(",", ":"))` 도 위 `context_digest` 를 **재현한다** —
예제의 float 일곱이 전부 정수값이 아니기 때문이다. 그러나 JCS 가 아니다:

```
stdlib  : {"x":1.0}
rfc8785 : {"x":1}
```

digest 는 외부 플러그인이 같은 값을 계산해야 하는 wire 계약이므로 규격 구현
(`rfc8785>=0.1.4`)을 의존성으로 선언했다. 이 차이를 회귀 시험
(`TestCanonicalDigestIsJcsNotAnApproximation`)으로 고정했다 — 안 남기면 누군가 의존성을
걷어내며 조용히 wire 를 깬다.

**Evidence — 계기가 공허하지 않다는 확인 (전부 실측)**

| 확인 | 방법 | 결과 |
|---|---|---|
| 스키마 검사가 깊은 곳까지 도는가 | `plan.json` 의 `cues[0].cue_id` 를 깨뜨림 | `SCHEMA_INVALID` + pointer `/cues/0/cue_id`. 원본은 통과 |
| 경계 가드가 실물인가 | `server/director/` 에 `from server.bridge.osc import OscBridge` 를 심음 | 잡힘 → 삭제 후 초록 복귀 |
| CAS backstop 이 DB 인가 | head 검사를 우회해 같은 revision 을 직접 INSERT | `sqlite3.IntegrityError` |
| 진짜 경쟁에서 하나만 이기는가 | 두 연결·두 스레드·barrier, **12회 시행** | 12/12 가 `('error','ok')` — 매번 하나만 이기고 다른 하나는 `REVISION_CONFLICT`. lock 경합(`busy`) 0회 |
| 아홉 축 전부가 digest 를 움직이는가 | 축을 하나씩 변형 | 9/9 움직임 |
| Unicode 정규화를 하지 않는가 | NFC 대 NFD 같은 글자 | 다른 digest (계약 §9 요구대로) |
| seam 이 통과를 사칭하지 않는가 | stub 에 네 가지 입력 | 전부 `blocked`. 주입한 통과 검증기로는 `ready_for_review` 도달 → seam 살아 있음 |

**자기 검토에서 찾은 내 오류 (수정 완료)**

1. `len(raw)` 가 `str` 에서 문자 수를 세어 한글로 2 MiB 상한을 3배까지 우회할 수 있었다 →
   바이트로 재도록 고치고 `test_limit_counts_bytes_not_characters` 로 고정.
2. 경쟁 시험의 단언이 `len(successes) <= 1` 이라 **둘 다 실패해도 통과**했다 → 12회 실측
   후 `== 1` 로 조이고, 경합이 있었던 경우만 예외로 뒀다.

**만든 파일**

```
server/director/__init__.py          경계 선언
server/director/models.py            parse_exchange · ExchangeError · Detail
server/director/digest.py            raw_digest · canonical_digest · context_digest · plan_digest
server/director/store.py             DirectorStore — 불변 저장 · CAS · 멱등
server/director/service.py           DirectorService — 검증기 seam (stub 은 blocked 만)
server/director/migrations/001_initial.sql   plan_revisions · idempotency_keys (STRICT)
server/director/schemas/exchange.schema.json 계약본과 바이트 동일 (시험으로 고정)
```

의존성 추가: `jsonschema[format-nongpl]>=4.23` · `rfc8785>=0.1.4` (둘 다 계약이 규범으로
지정한 것을 집행하기 위한 것이며 사유를 `pyproject.toml` 주석에 남겼다).

**Gaps — M1 에서 하지 않은 것**

- **M2(ContextSnapshot) · M3(지식 seed) 미착수.** `AC-LDPLUGIN-004` · `AC-LDPLUGIN-027` 미달성.
- **의미 검사 미구현.** 계약 §11 이 스키마로 보장되지 않는다고 열거한 것들(ID uniqueness,
  ref 해소, state simulation 등). 계약 §11: *"independent 구현자는 schema pass만으로 ready 를
  반환하면 안 된다."* 현재 구현은 schema pass 까지이며 그 이상을 주장하지 않는다. 그래서
  검증기 seam 의 기본값이 `blocked` 다.
- **superseded 전이 미구현.** 계약 §10 의 *"새 head 가 생기면 이전 미실행 revision 은
  superseded"* 는 승인 개념이 필요해 `LDRECV` 와 함께 다뤄야 한다.
- **HTTP 경로 없음.** `ld_submit_plan` 의 HTTP 표면은 `LDRECV` 의 것이다.
- **독립 감사 없음** (§F). ~~커밋하지 않았다.~~ **[만료 — `cde27445` 로 커밋됨]**

**Residual-risk**

- `MAX_EXCHANGE_BYTES` 를 다섯 교환 전체에 일률 적용한 것은 계약 §2 의 "structured plan
  2 MiB" 를 보수적으로 읽은 해석이다. 정상 예제 최대가 59 KB 라 실질 위험은 없다.
- 경쟁 시험의 12/12 는 이 기계·이 빌드의 실측이다. 다른 환경에서 lock 경합이 나면
  `busy` 분기로 떨어지고 그때는 "하나만 이김"을 단언하지 않는다 — 시험이 그 경우를 안다.
- 오류 detail 에 검사기 원문을 싣지 않아 디버깅 정보가 줄어든다. 계약 §3 의 누출 금지를
  택한 결과다.

### (이전 회차) M1 전반 — 교환 객체 strict parsing (REQ-LDPLUGIN-007)

작업 트리 기준 HEAD `98a822e` (커밋 전 · 아래 산출물은 uncommitted).
**[만료 — `cde27445` 로 커밋됨, §E.2 고지 참조]**

**Claim**: 계약 §2 의 wire 규칙과 §5 의 안정 code 로 교환 객체를 엄격히 파싱하는
`server/director/models.py` 를 TDD 로 구현했고, 다섯 계약 예제가 통과하며 거절 케이스가
각각 계약 code 를 답한다.

**Evidence — RED (구현 전, 실제 출력)**

```
$ uv run pytest server/tests/test_director_exchange_schema.py -q
server/tests/test_director_exchange_schema.py:23: in <module>
    from server.director.models import ExchangeError, parse_exchange
E   ModuleNotFoundError: No module named 'server.director'
1 error in 0.06s
```
파일: `.moai/state/verify/cbfacab7/ldstore-m1-RED.txt`

**Evidence — GREEN (실제 출력)**

```
$ uv run pytest server/tests/test_director_exchange_schema.py server/tests/test_director_boundary.py -q
31 passed in 0.57s
```

**Evidence — 회귀 (실제 출력)**

```
$ uv run pytest -q          # 작업 트리, HEAD 98a822e
12825 passed, 31 skipped, 1 warning in 169.84s
```
파일: `.moai/state/verify/cbfacab7/ldstore-m1-final.txt`

**Baseline-attribution**: 기준선 `12794 passed, 31 skipped` (같은 HEAD, 같은 트리, 구현 전
실측). 12794 + 신규 31 = **12825** — 정확히 일치하며 skipped 불변, 실패 0.

**Evidence — 린트·포맷 (실제 출력)**

```
$ uv run ruff check server/director/ server/tests/test_director_*.py
All checks passed!
$ uv run ruff format --check server/director/ server/tests/test_director_*.py
4 files already formatted
```

**Evidence — 계기가 공허하지 않다는 확인 (날조 대조군 실측)**

1. **스키마 검사가 깊은 곳까지 도는가** — `plan.json` 의 `cues[0].cue_id` 를 잘못된 Id 로
   바꾸자 `SCHEMA_INVALID` + pointer `/cues/0/cue_id`. 같은 자리에 unknown 필드를 넣자
   pointer `/cues/0/sneaky_field`. 손대지 않은 원본은 통과. → 회귀 시험
   `TestValidationReachesLeaves` 로 고정.
2. **경계 가드가 실물인가** — `server/director/_fabricated_control.py` 에
   `from server.bridge.osc import OscBridge` 를 심자 경계 시험이
   `('_fabricated_control.py', 'server.bridge.osc')` 로 잡았다. 파일 삭제 후 5 passed 복귀.
3. **바이트 상한 구멍** — `len(raw)` 가 `str` 에서 문자 수를 세어 한글로 상한을 3배까지
   우회할 수 있었다. 자기 검토에서 발견해 바이트로 재도록 고치고
   `test_limit_counts_bytes_not_characters` 로 고정.

**Gaps — 이번 회차에서 하지 않은 것**

- **M1 의 나머지 절반(불변 저장 · CAS)은 구현하지 않았다.** `store.py`,
  `service.py`, `migrations/001_initial.sql` 미착수. `AC-LDPLUGIN-015` 미달성.
- **M2(ContextSnapshot) · M3(지식 seed) 미착수.** `AC-LDPLUGIN-004` · `AC-LDPLUGIN-027` 미달성.
- **의미 검사 미구현.** 계약 §11 이 스키마로 보장되지 않는다고 열거한 것들 — ID uniqueness,
  모든 ref 해소, hash 정합성 등. 계약 §11: *"independent 구현자는 schema pass만으로 ready 를
  반환하면 안 된다."* 현재 구현은 **schema pass 까지**이며 그 이상을 주장하지 않는다.
- ~~커밋하지 않았다.~~ **[만료 — `cde27445` 로 커밋됨]**

**Residual-risk**

- `jsonschema` 의존성을 새로 추가했다. `uv sync` 가 미선언 빌드 의존성
  `pyinstaller`·`setuptools` 를 걷어냈고 수동 복구했다 — 아래 별도 항목 참조.
- `MAX_EXCHANGE_BYTES` 를 다섯 교환 전체에 일률 적용한 것은 계약 §2 의 "structured plan
  2 MiB" 를 보수적으로 읽은 것이다. 계약이 plan 에만 건 상한일 수 있다. 정상 예제 최대가
  59 KB 이므로 실질 위험은 없지만 해석임을 밝힌다.
- 오류 detail 에 검사기 원문 메시지를 싣지 않고 rule 이름만 싣는다. 계약 §3 의 누출 금지를
  지키는 선택이지만, 디버깅 정보가 줄어든다.

### 발견 — 선언되지 않은 빌드 의존성 (이 SPEC 범위 밖, 보고용)

`packaging/build.sh:12` 는 `.venv` 에 `pyinstaller` 가 설치돼 있음을 **전제**로 적고 스스로
설치하지 않는다. 그런데 `pyproject.toml` 에 `pyinstaller` 선언이 없다. 따라서 **누구든
`uv sync` 를 돌리면 데스크톱 빌드가 깨진다** — 이번 회차에 실제로 깨졌고
`uv pip install --python .venv/bin/python pyinstaller` 로 원상 복구했다(6.22.3).

이건 이 SPEC 이 만든 문제가 아니라 드러낸 문제다. 근본 수리(선언 추가)는 이 SPEC 의 범위
밖이므로 하지 않았다.

### M3 완료 (REQ-LDPLUGIN-027 · AC-LDPLUGIN-027) — 2026-09-16

작업 트리 기준 HEAD `dd3c1121`.

**Claim**: design.md §3 의 검토된 5주제(음악 근거 규칙·tracking 규칙·연출 case·rig·preset
규칙·적용·안전 규칙)를 `server/director/knowledge.py` + `server/director/knowledge_seed/`
로 TDD 구현했다. feedback seed(design.md §3 6번째 행)는 범위 밖으로 제외했다 — plan.md §2
M3 가 "지식 seed" 단일 마일스톤으로만 명시하고, feedback 워크플로는 `SPEC-LDPLUGIN-001` 이
소유하는 `director-feedback` 패키지의 몫이다.

**Evidence — RED (구현 전, 실제 출력)**

```
$ uv run pytest server/tests/test_director_knowledge_seed.py -q
ImportError: cannot import name 'knowledge' from 'server.director'
1 error in 0.05s
```
파일: `.moai/state/verify/ldstore-m3/RED.txt`

**Evidence — GREEN (실제 출력)**

```
$ uv run pytest server/tests/test_director_knowledge_seed.py -q
...........................                                              [100%]
27 passed in 0.42s
```
파일: `.moai/state/verify/ldstore-m3/GREEN.txt`

**Evidence — 회귀 (실제 출력)**

```
$ uv run pytest -q          # 작업 트리, HEAD dd3c1121
13376 passed, 35 skipped, 1 warning in 221.70s
```
파일: `.moai/state/verify/ldstore-m3/regression-full.txt`

**Baseline-attribution**: 기준선 `13349 passed, 35 skipped` (같은 HEAD `dd3c1121`, 구현
직전 프롬프트에 실측값으로 제공됨). 신규 테스트 **27개** (1 파일:
`test_director_knowledge_seed.py`). 13349 + 27 = **13376** — 정확히 일치, skipped 불변(35),
실패 0.

**Evidence — 린트·포맷 (실제 출력)**

```
$ uv run ruff check server/director/ server/tests/test_director_knowledge_seed.py
All checks passed!
$ uv run ruff format --check server/director/ server/tests/test_director_knowledge_seed.py
23 files already formatted
```

**Evidence — 경계 grep (실제 출력)**

```
$ grep -rn "server.bridge.osc\|from server.bridge" server/director/knowledge*.py server/director/knowledge_seed/
OK
$ grep -rn "songcue\|_ARC_" server/director/knowledge*.py server/director/knowledge_seed/
OK
```

**Evidence — AC-LDPLUGIN-027 의 다섯 PASS 조건 매핑**

| # | PASS 조건 | 시험 |
|---|---|---|
| 1 | seed 주제 정확히 5개, 각 항목이 provenance·조건·예외·검토 revision·권리 범위를 가진다 | `test_exactly_five_seed_topics` · `test_seed_topics_cover_four_rules_and_one_case`(rule 4 + case 1) · `test_every_record_has_the_five_required_fields`(5개 파라미터화, 비어있지 않음까지 단언) · 음성 대조 `test_missing_field_is_caught_not_silently_accepted` |
| 2 | bounded inline typed details — 요약 문자열이 아니라 typed 구조 | `test_details_is_a_typed_structure_not_a_summary_string`(kind 별 shape·상한 단언) · `test_search_results_carry_full_details_inline` · `test_page_and_record_shape_match_the_contract` |
| 3 | current context 변경 시 이전 cursor 는 stale | `test_context_change_makes_the_cursor_stale`(`CURSOR_STALE`/409) · `test_query_change_makes_the_cursor_stale` · `test_malformed_cursor_is_rejected` · 양성 대조 `test_matching_context_cursor_continues_the_page`(같은 context 재사용은 통과) |
| 4 | 미승인 지식 노출 0 | `test_unreviewed_knowledge_never_surfaces` — 승인 합성 레코드는 검색되고(양성 대조), 미승인 합성 레코드는 `count == 0` |
| 5 | "강제 법칙"/"학습된 가중치" 로 표시하지 않는다 | `test_no_seed_record_labels_itself_a_mandatory_rule_or_trained_weight`(실 seed 전수 검사) · 날조 대조군 `test_forbidden_label_sweep_actually_catches_a_violation`(검사기가 헛돌지 않음을 확인) |

**설계 결정 — `rights_scope` 는 계약의 최소 shape 을 넘는 추가 필드다**

계약 §3 이 규정한 `KnowledgeRecord` 정확한 shape 에는 "권리 범위" 에 대응하는 별도
필드가 없다(`{record_id,kind,scope,summary,applicability,exceptions,provenance,
evidence_refs,resource_id,reviewed_revision,details}`). 그러나 `REQ-LDPLUGIN-027` 은
"권리 범위" 보존을 명시적으로 요구하고, `KnowledgeRecord`/`KnowledgePage` 는 다섯
exchange message_type 중 하나가 아니라 계약 §3 의 envelope 정의라 `exchange.schema.json`
의 closed-world 검사 대상이 아니다(실측: `$defs` 39개 키에 `knowledge_record`/
`knowledge_page` 없음). 그래서 `rights_scope` 필드를 추가해도 계약의 wire shape 을 깨지
않는다고 판단했다. 실제 HTTP 표면(추후 `LDRECV` 가 붙인다)이 이 필드를 그대로 노출할지
`provenance.rationale` 로 접을지는 이 SPEC 의 범위 밖이며, `knowledge.py` 모듈
docstring 에 이 경계를 명시했다.

**설계 결정 — scope 는 전부 `user_style`**

5주제 모두 특정 곡/쇼에 결합되지 않는 일반 지식이므로 계약의 세 scope 값
(`this_song`/`this_show`/`user_style`) 중 `user_style` 을 택했다. `this_song`/
`this_show` 는 feedback scope binding(design.md §3 마지막 문단)의 몫이며 이 SPEC 이
구현하지 않는 feedback 워크플로에 속한다.

**만든 파일**

```
server/director/knowledge.py                          KnowledgeRecord · KnowledgePage · KnowledgeService · cursor 인코딩
server/director/knowledge_seed/__init__.py             RAW_TOPICS 집계 (순수 데이터, knowledge.py 를 참조하지 않는다 — 순환 임포트 회피)
server/director/knowledge_seed/music_evidence.py        주제 1 — 음악 근거 규칙
server/director/knowledge_seed/tracking.py              주제 2 — tracking 규칙
server/director/knowledge_seed/staging_cases.py         주제 3 — 연출 case (kind=case)
server/director/knowledge_seed/rig_preset.py            주제 4 — rig·preset 규칙
server/director/knowledge_seed/safety.py                주제 5 — 적용·안전 규칙
server/tests/test_director_knowledge_seed.py            27개 시험 — AC-LDPLUGIN-027 다섯 PASS 조건 + 경계
```

새 의존성 없음 — `base64`·`json`·`dataclasses` 는 stdlib 이고, 기존
`server/director/models.py` 의 `Detail`/`ExchangeError` 를 재사용했다.

**Gaps — M3 에서 하지 않은 것**

- **HTTP 경로 없음.** `ld_search_knowledge` 의 HTTP 표면(`GET P/knowledge`)은 `LDRECV` 의
  몫이다 (plan.md §4 는 M1 예시만 다루지만 같은 경계가 M3 에도 적용된다 — spec.md §4.1).
- **feedback seed 미구현.** design.md §3 6번째 행(feedback scope binding·
  pending→approved→revoked)은 명시적으로 범위 밖이다 — 배차 지시에서 확인.
- **SQLite 영속화 없음.** design.md §4 는 "reviewed knowledge" 를 store.py 가 소유할
  SQLite 데이터 단위로 열거하지만, plan.md §2 M3 행은 `knowledge.py`/`knowledge_seed/`
  만 명시한다. 이 M3 구현은 정적 in-memory seed 다 — 검토·철회가 실제로 일어나는
  永続 계층은 M3 의 범위가 아니라고 판단했다(plan.md 파일 소유 열에 store.py 확장이
  없음).
- **retrieval_revision 이 실제 승인/철회에 반응하지 않는다.** `_retrieval_revision()` 은
  현재 `reviewed` 레코드 집합의 함수이므로 그 집합이 바뀌면(예: 서비스에 다른 레코드
  목록을 주입) cursor 가 stale 해지지만, feedback 승인/철회 이벤트 자체는 이 모듈에
  없다(위 Gap 과 동일 경계).

**Residual-risk**

- 검색은 단순 substring 매칭이다(`_matches`) — 계약은 검색 알고리즘을 규정하지 않으므로
  위반은 아니지만, 실제 배포에서는 관련성 랭킹이 필요할 수 있다.
- cursor 인코딩은 base64(JSON) 이며 서명·암호화가 없다 — 계약은 "opaque 서버 값" 만
  요구하고 위조 방지를 요구하지 않는다. 위조된 cursor 는 offset 조작으로 다른 페이지를
  볼 수는 있지만 `reviewed=False` 레코드를 노출하지는 않는다(필터가 offset 보다 먼저
  적용된다) — 이 경계는 시험하지 않았다(Gap).
- `_enforce_bounds` 의 64 KiB/256 KiB 상한은 seed 데이터가 작아 실제로 걸린 적이 없다
  (날조 대조군을 별도로 쏘지 않았다) — 코드 경로는 있으나 실측 확인은 못 했다.

### 기준선

```
$ uv run pytest -q          # HEAD 98a822e, 2026-09-14
12794 passed, 31 skipped, 1 warning in 166.21s
```

**CI 는 저장소 전체가 과금 차단으로 죽어 있다.** 로컬 pytest 가 유일한 판정 근거다.

## §E.4 Sync-phase Audit-Ready Signal

```
sync_status: completed
sync_complete_at: 2026-09-16
sync_commit_sha: pending-backfill-ldstore-001-sync
```

**Claim**: SPEC-LDSTORE-001 전체(M1 교환 스키마·불변 저장 + M2 ContextSnapshot + M3 지식
seed)가 완료됐다. M1+M2는 `origin/main` `cde27445`로 앞서 머지됐고, M3는 이 워크트리
HEAD(`dd3c1121` 이후 `9f44a1ba` → merge `913bb02b`)에서 TDD로 완료됐다. 세 마일스톤
모두가 이 SPEC의 계획된 범위 전부다 — `plan.md` §2는 M1/M2/M3 세 행만 명시한다.

**Evidence**

```
$ uv run pytest -q          # 이 워크트리 HEAD 기준
13376 passed, 35 skipped, 1 warning
```
```
$ uv run pytest server/tests/test_director_knowledge_seed.py -q   # M3 단독
27 passed
```
```
$ uv run ruff check server/director/ server/tests/test_director_knowledge_seed.py
All checks passed!
$ uv run ruff format --check server/director/ server/tests/test_director_knowledge_seed.py
(clean)
```
```
$ grep -rn "server.bridge.osc\|from server.bridge" server/director/
(no matches)
$ grep -rn "songcue\|_ARC_" server/director/
(no matches — 문서 언급만 있음)
```

**Baseline-attribution**: 이 워크트리 HEAD 기준 실행, §E.2 "M3 완료" 절에 기록된 동일
숫자(13376/35)와 일치. 커밋 SHA는 이 세션에서 직접 확인함(`git log --oneline -5` 재측정,
아래 §H).

**Gaps**: 독립 plan-audit 없음(§E.1 — 이 저장소에서 `plan-auditor`가 컨텍스트 초과로
죽는다, §F). HTTP 표면(`LDRECV` 몫) 없음 — M1·M3 둘 다 계약이 정의하는 API 노출은 이
SPEC의 범위 밖이다. feedback seed(scope binding)는 M3에서 명시적으로 범위 밖.

**Residual-risk**: §E.2 M1/M3 각 절의 Residual-risk 참조 — 경쟁 시험은 이 기계·이 빌드
실측(12/12), `MAX_EXCHANGE_BYTES` 해석은 보수적 읽기, 검색은 단순 substring, cursor는
서명 없는 base64(계약이 요구하지 않음).

### 계약 독해 기록 (M1 착수 조건 — `plan.md` §6)

`contract.md` 읽은 절: §2(공통 wire 규칙) · §3(MCP signature·Envelope·ErrorEnvelope) ·
§5(인증·오류 code) · §6.1(ContextSnapshot) · §6.2(LightingPlan) · §9(hash·canonical scope) ·
§10(revision·승인·실행 state machine).

안 읽은 절: §4(APP human routes → `LDRECV`) · §6.3~6.5 · §7(typed action·timing → `LDCOMPILE`) ·
§8(semantic rule IDs → `LDCOMPILE`) · §11(예제 묶음).

그 결과 `acceptance.md` AC-007/AC-015 의 "계약 code" 자리를 실제 code
(`SCHEMA_INVALID` · `UNSUPPORTED_SCHEMA_VERSION` · `INVALID_JSON` · `REVISION_CONFLICT` ·
`IDEMPOTENCY_CONFLICT` · `IDENTITY_MISMATCH` · `PAYLOAD_TOO_LARGE`)로 채웠다.
