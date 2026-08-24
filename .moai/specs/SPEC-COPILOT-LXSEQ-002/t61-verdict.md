# t61 판정 — 응답 포트는 값이 틀린 게 아니라 **관측되지 않고 있었다**

카드 t61. 워크트리 `.claude/worktrees/t61`, 브랜치 `WT-probe-port`, 기준 `797aa70`.

카드는 「프로브 도구들의 응답 포트가 서로 안 맞는다」로 왔다. 안 맞는 것은 사실이다.
그러나 뿌리는 숫자가 아니었다.

---

## 1. 주장 (Claim)

1. **아무도 안 보고 있었다.** `introspect_probe` 의 검사 셋이 `--listen-port` 를
   아예 안 넘기고 침묵의 기본값 9000 으로 통과하고 있었다 — 즉 **이 도구가 어느
   포트로 쏘는지 재는 검사가 하나도 없었다.** 값이 틀린 것보다 강한 진술이다.
2. **필수 인자(ⓑ)는 절반짜리 처방이다.** 조용히 기본값으로 틀리는 것은 막지만,
   사람이 틀린 값을 명시하면 침묵은 똑같이 모호하다.
3. **나머지 절반은 이미 저장소 안에 있었다.** `server/web/reply_discovery.py` 가
   같은 사고를 위해 지어져 있었고, 도구들이 그것을 안 쓰고 있었다.
4. 처방은 실기로 **비공허함이 확인됐다** — 틀린 포트와 맞는 포트가 서로 다른
   이름의 진단을 낸다.

## 2. 증거 (Evidence)

### 2.1 전수 (17개, `server/tools/*.py`) — 카드 목록보다 넓었다

```
[9005 기본값]  busking_e2e · groupgen_e2e · lxseq_e2e
[9000 기본값]  introspect_probe · responder_roundtrip · osc_smoke   ← osc_smoke 은 카드에 없었다
[필수 인자]    lxseq_groups_e2e(t18) · t60_exec_budget_bisect · t60_exec_budget_narrow
               · t66_destination_probe · t66_length_bisect
[손수 파싱 · 침묵 기본값 9005]  t60_sweep · t60_bare_form_sweep · t60_nonspace_pad
               · t60_operand_vs_bytes · t60_pad_position
[해당 없음]    provider_smoke
```

손수 파싱 다섯은 **이 카드 전날 밤에 만들어졌다**(t60 측정 하네스, 이 레인이 만든
것이다). 그때는 원인 축을 가르는 것이 급했고 그것이 옳은 지름길이었다. 지금
정리하는 것도 옳다. 둘 다 사실이다.

### 2.2 검사가 기본값에 기대고 있었다 — 이 카드의 핵심

기본값을 지우자 `test_introspect_probe.py` 의 검사 **셋이 즉시 빨개졌다**:

```
SystemExit: 2  "the following arguments are required: --listen-port"
```

셋 다 포트를 안 넘기고 있었다. 그러므로 그 검사들은 **이 도구가 9000 으로 쏜다는
사실을 재고 있지 않았다** — 현장이 9005 라는 것과 어긋난다는 것도 몰랐다. 카드
원문의 「서로 안 맞는다」 아래에 있던 진짜 상태는 **「아무도 안 보고 있었다」**다.

지금은 세 호출이 포트를 명시하고, 새 검사 둘이 **넘긴 값이 실제로 스택에 도달하는지**
단언한다. 뮤테이션(`receive_port=args.listen_port` → 하드코딩 9000): **KILL 2/2**.

### 2.3 실기 비공허 확인 — 두 발이 다른 이름을 낸다

```
--listen-port 9005 (맞는 포트)  ->  verdict "responder_ok"
--listen-port 9000 (틀린 포트)  ->  verdict "port_mismatch"
    observed_port 9005 · listened [9001,8999,9002,8998,9003,8997,9004,8996,9005,8995]
    detail "설정한 포트 9000 으로는 회신이 없고 9005 으로 왔다. 응답기는 살아 있다"
```

같은 두 발을 실제 도구(`lxseq_groups_e2e --probe-only`)로도 냈다. 예전에는 틀린
포트에서 `"no state reply ... within 5.0s"` 세 줄만 보였고 — **죽은 응답기와
구분되지 않았다.** 지금은 그 위에 진단이 먼저 온다.

`ping` 한 발 외에 아무것도 안 쐈다. 콘솔 상태 미변경.

### 2.4 갈래는 셋이 아니라 넷이다

`reply_discovery` 가 `unbindable` 을 접지 않고 따로 보고하는 이유를 그대로 계승한다.

| verdict | 뜻 |
|---|---|
| `responder_ok` | 하트비트가 돌아왔다. 발견 비용 0 |
| `port_mismatch` | 다른 후보로 회신이 왔다. 그 포트를 이름으로 댄다. **채택하지 않는다** |
| `responder_silent` | **들을 수 있었던 후보 전부**에 안 왔다. 포트 문제가 아니다 |
| `discovery_incomplete` | 못 바인드한 후보가 있다. **위 둘 중 어느 판정도 못 한다** |

넷째를 셋째로 접으면 이 카드가 없애려던 모호성이 자리만 옮긴다. 실기로는 앞의 둘만
만들 수 있어(응답기를 죽여야 나온다 — 콘솔에 미저장 유일본이 있다) 나머지 둘은
`test_probe_preflight.py` 가 가짜 발견기로 덮는다. 넷이 서로 다른 이름인지도 잰다.

### 2.5 검사 자신의 비공허성

`test_probe_port_discipline.py` — 도구 목록을 **하드코딩하지 않고** 디렉터리를
전수 스캔한다(t51 형태). 날조 대조군 넷을 먼저 쏜다:

| 심은 형태 | 결과 |
|---|---|
| argparse 한 줄 `default=9005` | 잡음 |
| argparse 여러 줄 `default=9000` | 잡음 |
| **손수 파싱 `listen = 9005`** | 잡음 |
| 올바른 형태(공용 선언) | 통과 — 「무엇이든 잡는」 스캐너가 아님 |

실제 도구에 심은 뮤테이션 둘도 **KILL**: argparse 기본값 복원 · 손수 파싱 복원.

**이 검사 자신이 한 번 공허했다.** 처음에는 `add_listen_port_argument` 라는 **글자**가
파일 어디든 있으면 통과했고, 선언만 손수 파싱으로 되돌린 뮤테이션이 **안 걸렸다** —
임포트 줄이 검사를 만족시켰다. 찾는 도구와 판정하는 도구가 달랐다. 지금은 **호출**
(`add_listen_port_argument(parser)`)을 잰다.

## 3. 기준 귀속 (Baseline attribution)

- 트리 `.claude/worktrees/t61` @ `WT-probe-port`, 기준 `797aa70`
- 콘솔: onPC, 송신 8000 / 현장 수신 **9005**, 응답기 v1.6.1
- `make ci-local` exit 0 · `make test` **10151 passed, 12 skipped, exit 0**
- 콘솔 상태 미변경 (ping 외 발사 없음)

## 4. 미검증 (Gaps)

1. **프리플라이트를 붙인 도구는 `lxseq_groups_e2e` 하나다.** 나머지는 공용 진입점
   (`python -m server.tools.probe_preflight --listen-port N`)으로 따로 돌려야 한다.
   포트 선언은 16개 전부 통일됐지만 프리플라이트 채택은 부분이다.
2. **`responder_silent` / `discovery_incomplete` 는 실기 미검증이다.** 단위 검사로만
   덮었다 — 응답기를 죽이거나 포트를 점유해야 나오는데 콘솔에 미저장 유일본이 있다.
3. **현장값 9005 는 이 한 대에서만 확인됐다.** `SITE_LISTEN_PORT` 는 도움말 문구로만
   쓰고 기본값으로 쓰지 않는다 — 다른 현장에서 다르면 조용히 틀릴 자리이기 때문이다.
4. **`--listen-port` 를 명시하되 틀리게 적는 경우**는 여전히 침묵이다. 프리플라이트가
   그 침묵에 이름을 붙이지만, 도구가 프리플라이트를 안 부르면 그대로다(1번과 같은 구멍).

## 5. 잔여 위험 (Residual risk)

- 필수 인자는 호출을 번거롭게 만든다. 스크립트에 포트를 박아 두는 습관이 생기면
  **박아 둔 값이 낡는 순간** 같은 병으로 돌아온다 — 그때 구하는 것은 프리플라이트다.
- `reply_discovery` 의 후보 집합은 설정 포트 ±5 다. 현장이 그 밖으로 옮겨가면
  `port_mismatch` 대신 `responder_silent` 가 나온다. 근거는 그 모듈이 적어 뒀다
  (관측된 드리프트가 9000→9005 였다).

---

## 부수 관측 — `ci-local` 초록이 안전이 아니다

이 카드의 빨간불 셋은 **`make ci-local` 을 통과하고 `make test` 에서만** 났다.
빠른 부분집합에 `test_introspect_probe.py` 가 없기 때문이다. 결함이 아니라 설계대로다
(t55 가 Makefile 주석에 예고한 경계이고, 전량과 CI 가 잡았다). 다만 그 경계가
**실물로 관측된 첫 사례**이므로 남긴다 — 「ci-local 초록」은 푸시해도 된다는 뜻이지
전량이 초록이라는 뜻이 아니다.
