# t74 — CI 사각 10건 중 4건을 러너 없이 되살렸다 (+ t65 정정)

구현 트리: `.claude/worktrees/t74` · 브랜치 `WT-ci-revive` · base `389b642`
콘솔 접촉 0 · 전량 스위트 미실행(지명 실행만) · 프로덕션 코드 변경 0(테스트만).

t65 판정(`t65-verdict.md`, `389b642` 로 머지됨)의 구현이다. **그 문서의 처방 하나가 틀렸고,
아래 §1 이 정정한다.** 머지된 문서는 고치지 않았다 — 어디가 갱신됐는지 추적 가능해야 해서다.

---

## 1. 🔴 t65 정정 — seam 은 하나가 아니었고, 내가 지목한 seam 도 틀렸다

`t65-verdict.md` §3.3 은 이렇게 적었다:

> `launcher.probe_port_available` 를 가짜로 만들어 False 를 내게 하면 …
> `require_ports_available` → `build_runtime` → `main` → 호스트 채널까지
> **배선 전체가 리눅스에서 돈다.**

**틀렸다.** 돌려보니 넷 중 **하나만** 그 seam 이었다.

### 1.1 무엇이 틀렸나

`serve.py:478` 이 `real_serve = run is None` 이다. 테스트는 `main(..., run=lambda …)` 로
uvicorn 을 주입하므로 **`real_serve` 가 False 이고, 프리플라이트 블록(`:505-509`)이 아예 안 돈다.**

측정(`.moai/reports/t74/probe_pragma.py`):

    run= 을 주입한 main() 에서
      exit code          = 0
      프로브가 불린 횟수  = 0

그러면 `serve:188`·`serve:209` 의 exit 2 는 어디서 오는가 — **실제 bind** 다.
`server/safety/bootstrap.py:145` 가 `bridge.start()` 의 bridge-local
`ReceivePortInUseError` 를 launcher 의 `PortInUseError` 로 **번역**하고, 그것이 위로 흐른다.

| 검사 | t65 가 지목한 seam | **실제 seam** |
|---|---|---|
| `launcher:306` | probe | **probe** ✅ 맞았다 |
| `serve:170` (`build_runtime`) | probe | **bridge.start** ❌ |
| `serve:188` (`main` exit 2) | probe | **bridge.start** ❌ |
| `serve:209` (호스트 채널) | probe | **bridge.start** ❌ |

### 1.2 왜 이 정정이 중요한가

t65 처방대로 바로 구현했으면 세 검사에 **가짜 프로브를 태우고 아무것도 안 잡는 검사**를
만들었을 것이다. 그리고 그건 **초록**이라 아무도 안 봤을 것이다 —
t65 가 진단한 `test_the_seal_check_skips_where_codesign_does_not_exist` 와 **같은 형태**다.

배차서가 「첫 작업은 구현이 아니라 확인」을 [HARD] 로 박은 이유가 이걸로 증명됐다.

### 1.3 t65 의 나머지는 그대로 선다

- 「4건은 되살릴 수 있다」 — **맞다.** seam 이 둘이었을 뿐 건수는 같다.
- 「`launcher:282` 는 플랫폼 주장이라 못 옮긴다」 — **맞다.** 그대로 뒀다.
- 「봉인 1건은 소스 순서 단언으로 닫힌다」 — **맞다.** §3 에서 닫았고 뮤테이션으로 확인했다.
- ⓐ(macOS 러너) 판정 — 이 카드가 건드리지 않았다.

---

## 2. 되살린 4건 — 무엇을 어떻게 바꿨나

원칙 하나: **가짜는 입력 조건만 만들고, 단언 대상은 프로덕션 코드다.**
`launcher:282` 를 남긴 이유가 정확히 이 선이다 — 거기서는 가짜가 **주장 자체**를 만들어 버린다.

| 되살린 검사 | 주입 | 단언 대상(프로덕션) |
|---|---|---|
| `test_the_udp_row_carries_its_protocol_all_the_way_to_the_probe` | `launcher.probe_port_available` | `require_ports_available` 가 `sock_type` 을 프로브까지 **전달**하는가 |
| `test_build_runtime_raises_the_error_the_launcher_handles` | `OscBridge.start` | `bootstrap.py:145` 의 **번역** |
| `test_main_exits_two_with_operator_guidance_instead_of_a_traceback` | `OscBridge.start` | exit 2 + 이중언어 안내 |
| `test_the_shell_is_told_the_cause_on_the_host_channel` | `OscBridge.start` | stdout 호스트 채널 한 줄 |

### 2.1 🔴 `launcher:306` 은 축을 좁혀서 되살렸다

그대로 되살리면 **이미 있는 검사의 사본**이 된다. 게이트 없는 형제
`test_a_three_tuple_spec_still_means_tcp` 가 이미 「프리플라이트가 `PortInUseError` 를 낸다」를 덮는다.
사본을 만들면 「검사가 하나 늘었다」로 세어지는데 **실제로는 안 는다** — 이 카드가 고치려는 병과 같은 계열이다.

그래서 고유 축으로 바꿨다: **UDP 행이 `sock_type` 을 달고 프로브까지 가는가.**
표가 `SOCK_DGRAM` 을 *선언*한다는 것은 `test_web_serve.py:141` 이 덮지만,
프리플라이트가 그것을 프로브에 *전달*하는지는 **여기서만** 잰다. 안 전달하면 UDP 포트를
TCP 포트 공간에서 재고 점유를 통째로 못 본다.

---

## 3. 봉인 1건 — 소스 순서 단언으로 닫았다

`test_the_bundle_branch_seals_between_payload_and_verify` (신규, **게이트 없음**).
`--bundle` 가지를 AST 로 읽어 `bundle_payload` → `seal_bundle` → `verify_bundle` **순서**를 고정한다.

실행이 아니라 구조를 재는 이유: 실제 봉인은 `codesign` 을 부르고, 그것을 가짜로 만들면
**codesign 이 아니라 우리 인자 조립을 시험**하게 된다. 그건 검사를 되살리는 게 아니라 이름만 되살리는 것이다.

⚠️ **구현하다 하나 배웠다 — `ast.walk` 는 소스 순서가 아니다.** 너비 우선이라 중첩 깊이가 순서를
뒤집는다. 첫 판이 `['Path','bundle_payload','print','verify_bundle','seal_bundle','print']` 를 내서
정상 코드에서 빨간불이 났다. `(lineno, col_offset)` 로 정렬해 고쳤고, 그 이유를 코드 주석에 남겼다.

---

## 4. 되살린 것이 실제로 무언가를 잡는가 — 뮤테이션 3회

「되살렸다」가 「늘 통과하는 검사를 만들었다」가 아님을 증명한다. 복원은 백업+체크섬으로 했다
(`git checkout` 은 미커밋분을 날린다).

| # | 뮤테이션 | 결과 |
|---|---|---|
| 1 | `bootstrap.py` 의 번역 제거(`bridge.start()` 만 남김) | **KILL** — 되살린 serve 3건 전부 FAILED |
| 2 | `launcher.py` 의 `sock_type=sock_type` 전달 제거 | **KILL** — `udp_row_carries…` FAILED |
| 3 | `stage_sidecar.py` 의 `--bundle` 가지에서 `seal_bundle` 호출 제거 | **KILL** — 신규 순서 검사 FAILED |

🔴 **3번에서 결정적 대조가 나왔다.** 같은 뮤테이션에서 기존 게이트 없는 검사
`test_the_build_script_runs_the_payload_step` 은 **통과했다.**
즉 t65 가 「봉인 호출이 사라져도 CI 는 못 잡는다」고 주장한 사각이 **실증됐고**, 신규 검사가 그것을 닫는다.

체크섬 복원 확인: `bootstrap.py` `5a90d7b3…` · `launcher.py` `10f6c72b…` · `stage_sidecar.py` `3273a953…`
— 셋 다 뮤테이션 전 값과 일치. `git status` 는 테스트 3파일만 modified.

### 4.1 붙인 날조 대조군 (검사로 상주한다)

| 대조군 | 무엇을 막나 |
|---|---|
| `test_the_bridge_local_type_is_not_a_launcher_type` | 두 타입이 상속으로 이어지면 번역 검사가 공허해진다 — `issubclass` 가 False 임을 고정 |
| `test_a_bridge_that_starts_does_not_take_the_refusal_path` | 거절이 주입과 무관하게 항상 일어나면 통과한다 — 주입을 걷으면 exit 0 |
| `test_a_probe_that_reports_free_does_not_reject` | 같은 것을 프로브 축에서 |
| 순서 검사의 `assert called` | 가지를 못 찾으면 순서 단언이 공허하다 |

---

## 5. 🔴 `# pragma: no cover` — **지우지 않았다.** 재봤더니 주장이 여전히 참이다

배차서: 「그 프라그마는 주장이다. 네 변경이 거짓으로 만든다. 같이 지워라 — 다만 덮인다는 증거를 붙여라.」

**재봤고, 안 덮인다.** `serve.py:509` 의 갈래는 `real_serve` 뒤에 있고, 테스트는 `run=` 을 주입하므로
그 블록에 **도달하지 않는다.** 측정: `run=` 주입 상태에서 프로브 호출 **0회**(§1.1).

덮으려면 `run=None` 으로 실제 서빙을 해야 하는데 테스트에서 할 수 없다.
그러므로 「점유된 포트가 없으면 못 덮는다」는 주장은 **참으로 남는다** — 지우면 내가 거짓을 심는 것이다.

⚠️ 다만 문면이 살짝 부정확하다. 정확히는 「점유된 포트」만이 아니라 **「`real_serve` + 점유」**가 필요하다.
프로브를 가짜로 만들 수 있으므로 남은 조건은 사실상 `real_serve` 하나다.
**이 정정은 이 카드가 하지 않는다** — 프로덕션 파일을 건드리지 않는다는 이 카드의 경계 안이 아니고,
문면 정정만으로 얻는 것도 없다. 여기 적어 다음 사람이 알게 한다.

---

## 6. ⓑ — CI 가 **안 덮는** 자리 (보드가 세지 말 것)

되살리기 뒤에도 CI(리눅스)가 못 도는 것은 **6건**이다. 이름으로 고정한다 — 개수로 세면 또 흐려진다.

| # | 검사 | 위치 | 왜 여기 남나 |
|---|---|---|---|
| 1 | `test_a_bundle_with_its_payload_but_no_seal_is_rejected` | `test_deploy_tauri_shell.py:640`* | 실제 `codesign` 의 거부 행동 |
| 2 | `test_the_rejection_names_the_signature_not_the_payload` | `:648`* | 같음 |
| 3 | `test_sealing_makes_the_bundle_verify` | `:654`* | 실제 `codesign` 의 수용 행동 |
| 4 | `test_a_data_directory_in_frameworks_cannot_be_sealed` | `:661`* | **근본 원인** — Frameworks 안의 데이터 디렉터리를 codesign 이 거부 |
| 5 | `test_the_bundle_step_seals_before_it_verifies` | `:681`* | 실제 봉인이 `_CodeSignature` 를 만드는가 (구조 절반은 §3 이 되찾았다) |
| 6 | `test_a_udp_probe_sees_a_duplicate_instance_holding_the_receive_port` | `test_web_launcher.py:282` | **플랫폼 주장** — darwin 에서 이중 bind 가 실제로 충돌한다 |

\* 줄 번호는 이 변경 이후 기준이며 §3 이 앞에 검사를 하나 더해 밀렸다. 이름으로 찾는 편이 안전하다.

**세는 사람에게**: 이 6건은 CI 초록에 포함되지 않는다. 특히 1~5 는
`test_the_seal_check_skips_where_codesign_does_not_exist` 가 CI 에서 초록이라
「서명 검사가 돈다」로 오독되기 쉽다 — 그 검사가 단언하는 것은 **「검증이 no-op 이다」**이다.

---

## 7. 증거

### 7.1 주장
CI 사각 10건 중 **4건을 러너 없이 되살렸고**, 봉인 사각 하나를 소스 순서 단언으로 닫았다.
되살린 것이 실제로 결함을 잡는다는 것은 뮤테이션 3회로 확인했다.

### 7.2 증거 (명령과 관측)

    $ uv run pytest -q -rs server/tests/test_web_serve.py \
        server/tests/test_web_launcher.py server/tests/test_deploy_tauri_shell.py
      144 passed, 2 skipped, 1 warning in 27.07s
      (skip 2건은 빌드 산출물이 없는 트리 조건 — 이 카드 범위 밖, 공통 10건에 속한다)

    $ uv run ruff check <세 파일>   → All checks passed!

뮤테이션 3회는 §4 표. 체크섬 복원 확인도 거기.
seam 판별 프로브 3종: `.moai/reports/t74/probe_fake.py` · `probe_bridge.py` · `probe_main_seam.py` ·
프라그마 프로브 `probe_pragma.py`.
⚠️ 그 디렉터리는 `.gitignore` 라 **브랜치를 타지 않는다.** 판정에 필요한 값은 전부 이 문서에 옮겨 적었다.

### 7.3 기준 귀속
워크트리 `t74` · base `389b642` · macOS. 프로덕션 파일 3종은 뮤테이션 전후 체크섬 일치.

### 7.4 미검증 (Gap)

1. **리눅스에서 안 돌려봤다.** 되살린 4건이 리눅스에서 도는지는 **이 PR 의 CI 가 답한다.**
   주입은 플랫폼 독립이라 돌아야 하지만, 그건 예측이고 관측이 아니다.
   ⚠️ 검산 방법도 적어 둔다 — CI 의 `skipped` 가 **20 → 16** 이면 4건이 실제로 돌아온 것이다.
2. **전량 스위트를 안 돌렸다.** run 레인이 LXSEQ-003 을 쓰는 중이라 지명 실행만 했다.
   내 변경은 테스트 3파일뿐이고 프로덕션 코드 0이라 파급은 그 파일들 안이지만, **전량은 CI 몫**이다.
3. **`launcher:282` 는 여전히 macOS 에서만 돈다.** 의도이며 §2 의 선이다.
4. **`serve.py:509` 프라그마 문면의 부정확은 안 고쳤다**(§5). 다음 사람 몫으로 남긴다.
5. **ⓑ 목록을 검사로 고정하지 않았다.** 문서 §6 이 전부다.
   기계로 고정하려면 「게이트된 검사 이름 목록」 트립와이어가 필요한데, 이 저장소는 그 형태를
   이미 한 번 조건 검사로 바꿨다(`test_registry_has_no_row_reserved_for_a_later_spec`).
   같은 함정을 새로 만들지 않으려고 안 했다 — 판단이므로 뒤집을 수 있다.

### 7.5 잔여 위험

- **되살린 검사는 「번역이 있다」를 지키지 실제 bind 충돌을 지키지 않는다.** 그 주장은 여전히
  `launcher:282` 하나뿐이고 macOS 에서만 돈다. 되살림을 「이제 CI 가 중복 실행을 막는다」로 읽으면 안 된다.
- **주입 seam 이 바뀌면 검사가 조용히 공허해진다.** 예컨대 `bootstrap.py` 가 `bridge.start()` 대신
  다른 자리에서 시작하게 바뀌면, 가짜가 아무 데도 안 걸리고 검사는 초록으로 남는다.
  §4.1 의 대조군 중 `test_a_bridge_that_starts_does_not_take_the_refusal_path` 가 그 절반을 막는다
  (주입 없이 exit 0) — 나머지 절반(주입이 실제로 걸리는가)은 §4 뮤테이션이 답했고, 그건 상주 검사가 아니다.
- **`ast.walk` 순서 함정**(§3)은 이 저장소의 다른 AST 스캐너에도 있을 수 있다. 확인 안 했다.
