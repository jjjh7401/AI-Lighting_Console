# t65 판정 — CI 가 구조적으로 못 도는 10건을 어떻게 다룰 것인가

조사 트리: `.claude/worktrees/t65` · 브랜치 `WT-ci-blind-spots` · HEAD `143c783`
읽기 전용. 콘솔 접촉 0 · 전량 스위트 미실행.

대상은 t59 가 특정한 CI 전용 skip 12건 중 **10건**이다(나머지 2건은 t64 가 닫았다).
이 문서를 여기 둔 이유: 두 표면 다 `SPEC-COPILOT-DEPLOY-001` 이 소유한다
(`spec.md`·`plan.md`·`progress.md` 가 `PortInUseError` 를, `spec.md` 가 `codesign`/`seal` 을 언급).

---

## 0. 이 카드가 답한 질문

배차서가 못박은 것: **「5건이 안 돈다」와 「서명이 깨져도 아무도 모른다」는 다른 진술**이고,
후자가 참인지는 **다른 데서 덮이는지**에 달렸다. 그래서 「안 도는 목록」이 아니라
**「안 돌아서 실제로 무엇이 무방비인가」**를 쟀다.

방법은 하나다 — 두 게이트 그룹 각각에 대해 **같은 클래스·같은 파일의 게이트 없는 형제 테스트**를
전수로 읽고, 잃는 단언과 남는 단언을 갈랐다.

**결론부터**: 10건이 통째로 무방비인 것이 아니다. **6건은 다른 검사가 이미 덮거나 덮게 만들 수 있고,
4건이 진짜 macOS 전용이다.** 그리고 그 4건 중 서명 쪽에는 **CI 가 「덮은 척」하는 자리가 하나 있다.**

---

## 1. 판정 요약

| 그룹 | 건수 | 판정 | 처방 |
|---|---|---|---|
| codesign 부재 | 5 | **4건 진짜 macOS 전용 · 1건은 ⓒ로 닫힌다** | ⓑ+ⓒ 혼합. ⓐ(러너)는 감독 결정으로 남긴다 |
| `sys.platform != darwin` | 5 | **4건은 배선이라 ⓒ로 닫힌다 · 1건만 플랫폼 실측** | **ⓒ 우선.** 러너 없이 4건을 되살릴 수 있다 |

🔴 **가장 중요한 발견은 개수가 아니다.**
봉인 클래스에서 CI 가 돌리는 **유일한** 테스트는 `test_the_seal_check_skips_where_codesign_does_not_exist`
(`test_deploy_tauri_shell.py:674`)이고, 그것이 단언하는 것은
**「codesign 이 없으면 `verify_bundle` 이 0(통과)을 낸다」**이다.

즉 **CI 에서 그 파일이 초록인 것은 서명에 대해 아무것도 말하지 않는다** —
검증이 no-op 인 경로를 검증이 통과했다고 세고 있다. 이것이 배차서가 말한
「보드가 방어선을 셀 때 이걸 덮는 것으로 세면 안 된다」의 정확한 실체다.

---

## 2. codesign 그룹 5건 — 잃는 것과 남는 것

`TestTheBundleIsSealedAfterThePayloadLands` 는 테스트 **6건**이고 그중 5건이 게이트다.

| 테스트 | 위치 | CI | 단언하는 것 |
|---|---|---|---|
| `test_a_bundle_with_its_payload_but_no_seal_is_rejected` | `:640` | ❌ | 봉인 안 된 번들 → `verify_bundle == 1` |
| `test_the_rejection_names_the_signature_not_the_payload` | `:648` | ❌ | 거절 사유가 payload 가 아니라 **서명**이라고 말한다 |
| `test_sealing_makes_the_bundle_verify` | `:654` | ❌ | 봉인하면 `verify_bundle == 0` |
| `test_a_data_directory_in_frameworks_cannot_be_sealed` | `:661` | ❌ | **근본 원인** — `Contents/Frameworks` 에 데이터 디렉터리가 있으면 codesign 이 통째로 거부 |
| `test_the_seal_check_skips_where_codesign_does_not_exist` | `:674` | ✅ | codesign 부재 → **0(통과)**. 크래시하지 않는다 |
| `test_the_bundle_step_seals_before_it_verifies` | `:681` | ❌ | `--bundle` 한 번이 payload→봉인→검증 **순서**로 돌고 `_CodeSignature` 가 생긴다 |

### 2.1 CI 에 남는 것 (전수)

- **payload 절반은 덮인다.** `test_verify_fails_on_a_bundle_missing_the_runtime_payload`(`:477`) ·
  `test_verify_fails_on_a_bundle_missing_the_executable`(`:483`) — 둘 다 게이트 없이 `verify_bundle == 1` 을 낸다.
  서명 검사에 닿기 전에 실패하므로 리눅스에서도 성립한다.
- **빌드 스크립트가 번들 단계를 포함한다는 트립와이어.** `test_the_build_script_runs_the_payload_step`(`:608`)이
  `package.json` 의 `shell:build` 에 `--bundle` 이 있는지 본다. 게이트 없다.
- **소스 수준 단언 패턴이 이미 있다.** `test_the_payload_destination_matches_the_bootloader_expectation`(`:596`)이
  `stage_sidecar` 소스를 읽어 문자열을 단언한다 — 코드를 실행하지 않고 구조를 고정하는 방식이다.

### 2.2 그래서 실제로 무방비인 것

**누가 `--bundle` 경로에서 봉인 단계를 지워도 CI 는 못 잡는다.**

실물(`packaging/stage_sidecar.py:346-348`):

    if seal_bundle(app_bundle) is not None:
        …
    return verify_bundle(app_bundle)

`:608` 은 `--bundle` **플래그가 스크립트에 있는지**만 본다. 그 안에서 `seal_bundle` 호출이 사라져도
플래그는 그대로다. 그리고 봉인 여부를 보는 유일한 테스트(`:681`)는 게이트다.
→ **CI 초록 + 봉인 없는 배포**가 성립한다.

### 2.3 처방

**ⓒ로 닫히는 것 1건**: `--bundle` 경로가 **`seal_bundle` 을 `verify_bundle` 보다 먼저 부른다**는
**소스 수준 단언**을 추가한다. `:596` 이 이미 쓰는 기법이고 codesign 이 필요 없으므로 **리눅스에서 돈다.**
이것이 §2.2 의 무방비를 정확히 닫는다 — 순서까지 고정하므로 `:681` 이 지키던 것의 **구조 절반**을 되찾는다.

**나머지 4건은 진짜 macOS 전용이다.** 전부 실제 `codesign` 의 수용/거부 행동을 단언한다.
`subprocess` 를 가짜로 만들면 **우리 인자 조립을 시험할 뿐 codesign 을 시험하지 않는다** —
그건 검사를 되살리는 게 아니라 이름만 되살리는 것이다.
→ **ⓑ**: 명시 목록으로 고정하고 「CI 는 서명을 보지 않는다」를 문서화한다(§4).

**ⓐ(macOS 러너)는 감독 결정으로 남긴다.** 다만 재고 나서 붙일 소견 하나 —
러너를 추가해도 검사 대상은 **합성 번들**이지 실제 배포 산출물이 아니다
(`:590` 의 실물 번들 검사는 빌드가 있는 트리에서만 도는 별개 게이트다).
서명이 실제로 문제되는 순간은 **로컬 macOS 에서 배포본을 만들 때**이고, 그 순간은 CI 밖이다.
비용을 쓰기 전에 그 비대칭을 먼저 볼 것.

---

## 3. darwin 그룹 5건 — 여기는 ⓒ가 크게 먹는다

게이트 사유(테스트가 스스로 적은 것): UDP 이중 bind 충돌은 darwin 실측 동작이고,
리눅스는 `SO_REUSEADDR` 로 두 번째 bind 가 성공해 **점유를 못 본다**.

| 테스트 | 위치 | 단언하는 것 | 성격 |
|---|---|---|---|
| `test_a_udp_probe_sees_a_duplicate_instance_holding_the_receive_port` | `launcher:282` | 점유된 UDP 포트 → 프로브가 **False** | 🔴 **플랫폼 실측** |
| `test_require_ports_available_rejects_an_occupied_receive_port` | `launcher:306` | 프리플라이트가 거절한다 | 배선 |
| `test_build_runtime_raises_the_error_the_launcher_handles` | `serve:170` | `PortInUseError` 를 낸다 — bridge-local 예외가 **잡히지 않고 새던** 결함을 고정 | 배선 |
| `test_main_exits_two_with_operator_guidance_instead_of_a_traceback` | `serve:188` | exit 2 + 이중언어 안내 (traceback 아님) | 배선 |
| `test_the_shell_is_told_the_cause_on_the_host_channel` | `serve:209` | **stdout** 호스트 채널로 알린다 — 패키지 앱엔 터미널이 없어서 stderr 가 안 닿는다 | 배선 |

### 3.1 CI 에 남는 것

- **오류 문구는 게이트 없이 덮인다.** `test_the_bilingual_guidance_is_what_str_of_the_error_shows`(`serve:231`)이
  `str(err) == err.guidance` 와 이중언어를 단언한다. 「안내문이 도달 불가였다」는 과거 결함은 CI 가 계속 잡는다.
- **프로토콜 축의 존재 이유도 덮인다.** `test_the_tcp_probe_is_blind_to_a_held_udp_receive_port`(`launcher:268`) ·
  `test_a_free_udp_port_is_still_reported_available`(`launcher:294`) — 둘 다 게이트 없다.
- 프리플라이트 표가 프로토콜을 선언한다는 것(`serve:141`·`:153`)도 게이트 없다.

### 3.2 그래서 실제로 무방비인 것 — **배선이다**

문구는 있고 탐지의 반대 사례도 있는데, **탐지가 참일 때 그것이 각 표면까지 가는 경로**가 CI 에 없다.
그 경로가 고정하는 건 **과거에 실제로 터진 결함 셋**이다 —
bridge-local 예외가 새던 것 · traceback 이 나가던 것 · 셸이 「런타임 파일 없음」으로 오추측하던 것.

### 3.3 처방 — 4건은 러너 없이 되살릴 수 있다 (실측 근거 있음)

호출 사슬을 확인했다:

- `server/web/launcher.py:267 require_ports_available` 가 **모듈 수준 `probe_port_available`** 를 부른다(`:292`)
- `server/web/serve.py:507` 이 `require_ports_available(startup_port_specs(args))` 를 부른다
  (`:43-55` 에서 launcher 로부터 임포트)

즉 **`launcher.probe_port_available` 를 가짜로 만들어 False 를 내게 하면**,
점유 상태를 실제로 만들지 않고도 `require_ports_available` → `build_runtime` → `main` → 호스트 채널까지
**배선 전체가 리눅스에서 돈다.**

그러면 갈래가 이렇게 선다:

| 되살릴 수 있는가 | 대상 | 방식 |
|---|---|---|
| ✅ 4건 | `launcher:306` · `serve:170` · `serve:188` · `serve:209` | 가짜 프로브로 조건을 만든다. 게이트 제거 |
| ❌ 1건 | `launcher:282` | **플랫폼 주장 자체**다. 「darwin 에서 이중 bind 가 실제로 충돌한다」는 가짜로 만들 수 없다 — 만드는 순간 자기 가짜를 시험한다 |

⚠️ **이 분리를 지키는 것이 요점이다.** 4건을 가짜 프로브로 옮기면서 `launcher:282` 까지 같이 옮기면,
**「리눅스는 점유를 못 본다」는 사실이 검사에서 사라진다.** 그러면 언젠가 프로브를 리눅스에서도
동작한다고 착각하고 게이트를 지우게 된다. 플랫폼 주장은 플랫폼에 남긴다.

⚠️ 그리고 이건 **처방이지 실측이 아니다.** 가짜 프로브가 실제로 그 네 경로를 통과시키는지는
**구현해서 돌려봐야** 안다 — 이 카드는 조사라 안 돌렸다. 착수하면 첫 작업이 그 확인이다.

---

## 4. 무엇을 고르든 참이 되어야 하는 진술

배차서의 뿌리: **「보드가 방어선을 셀 때 이걸 덮는 것으로 세면 안 된다.」**

지금은 그 진술이 **거짓**이다 — §1 의 발견 때문이다. 봉인 클래스가 CI 에서 초록인데
그 초록은 「검증이 no-op 이다」를 뜻한다. 세는 사람은 그걸 「서명 검증 통과」로 읽는다.

**그래서 어느 갈래를 고르든 다음 둘은 해야 한다:**

1. **CI 가 덮지 않는 자리를 명시 목록으로 고정한다.** 개수가 아니라 **이름**으로.
   이 문서 §2·§3 의 표가 그 목록의 초안이다.
2. **`:674` 의 성격을 문서에 박는다** — 그 테스트는 「codesign 없는 환경에서 크래시하지 않는다」를 지키는
   정당한 검사이지만, **그것이 CI 의 유일한 봉인 검사라는 사실**과 함께 읽혀야 한다.
   지금은 그 맥락이 어디에도 없다.

권고하는 조합: **darwin 4건은 ⓒ(가짜 프로브)로 되살리고, codesign 1건은 ⓒ(소스 순서 단언)로 닫고,
남는 5건(codesign 4 + launcher 1)은 ⓑ로 명시 고정한다. ⓐ는 그다음에 판단해도 늦지 않다.**
이 조합이면 **10건 중 5건이 CI 로 돌아오고**, 나머지 5건은 「안 덮는다」가 문서에 남는다.

---

## 5. 증거

### 5.1 주장
10건이 통째로 무방비인 것이 아니다. **6건은 다른 검사가 이미 덮거나 덮게 만들 수 있고 4건이 진짜 macOS 전용**이며,
그와 별개로 **CI 의 유일한 봉인 검사가 「검증이 no-op」을 단언한다**.

### 5.2 증거 (파일:줄 — 전부 이 트리에서 읽었다)

봉인 그룹:
- 클래스 전수 6건 · 게이트 5건 · 비게이트 1건 — `test_deploy_tauri_shell.py:617-692`
- 비게이트가 단언하는 것 — `:674-679`(codesign 부재 → `verify_bundle == 0`)
- CI 에 남는 payload 검사 2건 — `:477-481` · `:483-486`
- 빌드 스크립트 트립와이어 — `:608-614`(`--bundle` 존재만 본다)
- 소스 수준 단언 선례 — `:596-606`
- 실물 순서 — `packaging/stage_sidecar.py:346-348`(`seal_bundle` → `verify_bundle`)
- 실물 스크립트 — `package.json` `shell:build` = `stage_sidecar.py && tauri build && stage_sidecar.py --bundle …`

darwin 그룹:
- 게이트 5건 — `test_web_launcher.py:275-306` · `test_web_serve.py:163-229`
- 비게이트로 남는 것 — `test_web_serve.py:231-242`(문구) · `test_web_launcher.py:268` · `:294` ·
  `test_web_serve.py:141` · `:153`
- 호출 사슬 — `server/web/launcher.py:267 require_ports_available` → `:292 probe_port_available` /
  `server/web/serve.py:43-55` 임포트 → `:507` 호출

### 5.3 기준 귀속
전부 워크트리 `t65` · HEAD `143c783` 에서 이번 세션에 읽은 값이다. 콘솔 접촉 0.
t59 의 10건 목록은 **내가 같은 보드에서 특정한 것**이고(`LXSEQ-002/t68-path-survey.md` 이전 카드),
이번에는 그 목록을 **재확인하지 않고 입력으로 썼다** — §5.4-1 참조.

### 5.4 미검증 (Gap)

1. ~~10건 목록 미재측정~~ — **닫았다.** t69 PR 의 CI 로그(head `b703920`, main `143c783` 직전)를
   되읽어 확인했다:

       SKIPPED [5] server/tests/test_deploy_tauri_shell.py:638: codesign unavailable on this host
       SKIPPED [1] server/tests/test_web_launcher.py:275  (darwin)
       SKIPPED [1] server/tests/test_web_launcher.py:299  (darwin)
       SKIPPED [1] server/tests/test_web_serve.py:163     (darwin)
       SKIPPED [1] server/tests/test_web_serve.py:181     (darwin)
       SKIPPED [1] server/tests/test_web_serve.py:202     (darwin)

   합계 **5 + 5 = 10**이고 줄 번호가 t59 실측과 같다. main 이 `1f1ed25` → `143c783` 로 움직이는 동안
   이 목록은 안 변했다.
2. **가짜 프로브 처방(§3.3)을 실제로 돌려보지 않았다.** 호출 사슬은 코드로 확인했지만
   그 네 경로가 실제로 통과하는지는 **구현해야** 안다. **처방이지 실측이 아니다.**
3. **소스 순서 단언 처방(§2.3)도 안 돌려봤다.** 같은 성격이다.
4. **테스트를 하나도 실행하지 않았다.** 전량은 run 레인과 겹치고, 이 카드는 조사라 필요가 없었다.
5. **`launcher.py` 와 `serve.py` 전수를 읽지 않았다.** 두 파일에서 이 표면과 관련된 자리만 따라갔다.
   다른 곳에 같은 경로를 덮는 검사가 더 있을 가능성은 배제하지 못했다.
6. **ⓐ(macOS 러너)의 비용을 재지 않았다.** §2.3 의 소견은 「합성 번들 대 실제 배포본」이라는
   구조 관찰이지 비용 계산이 아니다. 그 판단은 감독 몫이다.

### 5.5 잔여 위험

- **§3.3 을 구현하면서 `launcher:282` 까지 가짜로 옮기면 플랫폼 주장이 사라진다.**
  그 순간 「리눅스는 점유를 못 본다」가 검사에서 없어지고, 나중에 누가 게이트를 지우게 된다.
  이 분리가 처방의 핵심이며, 구현 카드가 이걸 놓치면 처방이 결함으로 바뀐다.
- **ⓑ(명시 목록)는 관리되지 않으면 낡는다.** 목록을 문서에 적어 두고 검사로 고정하지 않으면
  테스트가 늘거나 줄 때 목록만 남는다. 목록을 **검사가 읽는 형태**로 둘지는 구현 카드가 정한다.
- **`:674` 를 「봉인 검사」로 세는 습관은 사람 쪽 문제다.** 코드를 고쳐도 그 습관은 안 고쳐진다.
  문서에 맥락을 박는 것(§4-2)이 그래서 필요하다.
