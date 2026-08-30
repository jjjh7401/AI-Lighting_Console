# t194 — 슬롯 판독 실패를 루트 실패로 접지 않는다 (2회차 · 구현 완료)

- 브랜치 `WT-slot-read-attribution` · base `766e517` · 콘솔 실기 **0회**
- 1회차는 (B) 를 구현했다가 아키텍처 게이트에 막혔다. 이 판은 리드 판정 뒤의 2회차다.

## 0. 상태 한 줄

리드가 (B'') 를 채택했고, 그 처방을 **글자대로는 구현할 수 없다**는 것을 찾아
D1(구별을 예외가 아니라 응답에 싣는다)로 갈아탔다 — 리드 승인. 전량 스위트
**10571 passed, 0 failed**, 뮤테이션 **8/8 KILL**. 수용 기준 셋 전부 단언으로 있다.

## 1. 1회차에서 살아남은 사실 (요약)

| 출처 | 주장 | 실제 |
|---|---|---|
| t194 배차서 (4) | "강제하는 검사가 없다" | **틀림** |
| t188 §7.2 | "경계 검사는 fx·looks·paperwork·scene 넷" | **틀림** |

실제 가드: `server/tests/test_autopatch_execute.py` 의 AC-018③
`test_no_vwx_module_imports_the_console_send_surface[server/vwx/patchplan.py]`.
round17 적대 감사가 13가지 우회를 실증해 막은 AST 스캐너이고, 등기부가 아니라 **금지**다.

계기 오류가 원인이었다 — 내 명령줄 `ls server/tests/ | grep -E '_boundary\\.py$'` 은
**이름 규칙을 따르는 파일**을 셌지 경계 가드를 세지 않았다.

## 2. 리드 판정과 그 함정

리드: **(B'') 채택. 다만 포트 단위가 아니라 호출 자리 단위로 감싸라** — 열거 판독과
스윕 프로브가 **같은 포트 객체**를 쓰므로 포트에 어댑터를 씌우면 자동으로 둘 다 덮이고,
그러면 전송 실패가 부재와 구별 불가가 된다.

🔴 **그 처방은 글자대로 구현할 수 없다.** `patchplan` 안에서 `query_property` 를 부르는
자리는 둘(:1525 열거 · :1580 스윕)인데 거기서 감싸려면 `StateQueryError` 를 import 해야
하고 **그것이 바로 AC-018③ 이 막은 것**이다. 두 자리 다 같은 경로 형태
(`FID_FIXTURE_ROOT/<slot>`)라 어댑터가 경로로도 못 가른다.

## 3. D1 — 구별을 예외가 아니라 **응답**에 싣는다 (리드 승인)

```
tools.py  _SlotReadPort   : except StateQueryError -> {"ok": False, "unreachable": True}
patchplan :1552 (열거)     : ok 아님        -> unreadable_fids += 1   (슬롯 사유)
patchplan :1599 (스윕)     : unreachable 임 -> probe_failures  += 1   (진단 계수)
patchplan query_state      : **번역 안 함** -> 예외 그대로 -> tools.py catch -> 루트 사유
```

그 **비대칭**이 두 사유를 가른다. `patchplan` 은 딕셔너리 키 하나를 더 읽을 뿐이라
import 가 늘지 않는다 — AC-018③(임포트 스캐너)·AC-018①(속성 이름 집합
`execution_port` · `deploy_pipeline` · `ConsoleLink` · `OscBridge`) 둘 다 안 걸린다.
전량 스위트가 그것을 확인했다(§7).

배제한 안: (D2) `type(exc).__name__` 문자열로 가르기 — `except Exception` 넓히기라 M2 가
죽인다. (D3) `server/prechk` 에 중립 예외를 두고 `StateQueryError` 가 상속 — `console.py`
계층 변경이라 폭발 반경이 크고 레인·리드 권한 밖(리드 동의).

## 4. 🔴 §5 가 "안 쟀다"고 남긴 자리 — 재고 나서 알게 된 것

`probes/_t194_sweep_exc.py` · 출력 `probes/sweep-exc-out.txt`:

```
=== axis 2: 표식 없는 포트 단위 번역 ===
TimeoutError    + 번역                   probe_failures=2  unseen=2
StateQueryError + 번역                   probe_failures=0  unseen=2

=== 판정 ===
기존 검사 종류(TimeoutError) 가 변하나?  False
  probe_failures 2 -> 2
프로덕션 종류(StateQueryError) 가 변하나? True
  probe_failures 2 -> 0
안전 결과(complete) 가 변하나?           False
unseen 이 변하나?                        False
```

세 가지가 나왔다.

1. **회귀는 실재한다.** 표식 없이 번역하면 스윕 전송 실패가 부재와 한 바구니에 들어간다.
2. **안전 결함이 아니라 구별 결함이다.** `complete` 도 `unseen` 도 안 변한다 —
   슬롯이 관측으로 안 올라가므로 fail-closed 는 유지된다. 그래서 **더 조용하다.**
3. 🔴 **기존 검사가 이 회귀를 못 잡는다.** 스윕 예외를 쏘는 검사는 있다
   (`test_autopatch_fid.py:3063` R19, `probe_failure_count == 2`). 그런데 그것이 쏘는
   종류는 `_R19SweepPort.hidden_mode="raise"` -> **`TimeoutError`**(:2925)이고
   프로덕션이 던지는 것은 `StateQueryError`(`console.py:713` · `:718`)다. 위 표의 첫
   줄이 그 결과다 — 2 -> 2, **안 변한다**. 회귀가 나도 스위트는 초록으로 남는다.

   한 입력 계열에만 맞춰진 방어가 그 계열의 형제를 놓치는 형태다. 리드 판정:
   **그 검사는 자매지 대체가 아니므로 그대로 두고 더한다.**

## 5. 구현

| 파일 | 변경 |
|---|---|
| `server/orchestrator/tools.py` | `_SlotReadPort` 신설(모듈 수준) · 호출 3자리에 끼움 · `FidPropertyPort` 임포트 |
| `server/vwx/patchplan.py` | `FidPropertyPort` 응답 계약 문서화 · 스윕이 `unreachable` 을 셈 · `unreadable_root` 독스트링 정정 |

- 어댑터를 **모듈 수준**에 둔 이유: `build_toolset` 안에 중첩하면 검사가 직접 못 부른다.
  수용 기준 3은 이 도구의 페이로드로 관측되지 않으므로(아래 §6) 어댑터를 직접 불러야 한다.
- `FidPropertyPort` 독스트링(리드 요청): 이전 판은 시그니처만 있고 무엇이 돌아오는지·
  무엇이 던져지는지 아무 데도 없었다 — **이 카드가 고친 거짓 귀속의 뿌리가 거기다.**
- `unreadable_root` 독스트링의 "예외 이름을 부르는 것은 거기 안 걸린다"는 **반증됐다**
  (게이트가 실제로 걸었다). 그 자리에 실측을 적었다.

## 6. 검사 6 -> 10 (교체 0)

`server/tests/test_lxseq_group_section_request.py` — §6 여섯 유지, **§7 넷 추가**.
파일 전체 19 -> 23.

| 수용 기준 | 지키는 단언 |
|---|---|
| 1. 두 사유가 바이트 동일이 아니다 | `test_the_slot_reason_is_not_byte_identical_to_the_root_reason` |
| 2. 그 사유가 실제로 나간다 | `test_the_slot_reason_actually_reaches_the_payload` (dispatch 페이로드) |
| 3. 스윕 전송 실패에서 `probe_failures` 가 는다 | `test_a_sweep_transport_failure_still_counts_as_a_probe_failure` |

§7 의 나머지 셋: 어댑터 계약(`unreachable` 표식) · **넓히기 방지**(부재는 안 센다) ·
**자매 팔**(`TimeoutError` 는 여전히 스윕의 `except` 가 센다).

넓히기 방지 팔이 없으면 수용 기준 3의 가장 싼 통과법이 "`ok is True` 조건을 지운다"이고,
그러면 희소 풀의 **부재**까지 전송 실패로 세어 round19 주석이 지키는 fail-closed 구별이
죽는다. M6 가 그것을 실증한다.

⚠️ 수용 기준 3은 이 도구의 페이로드에 **안 나온다.** `probe_failures` 는 `reason()` 에
들어가지 않고 `to_dict()` 의 `probe_failure_count` 로만 나가는 **진단 계수**다
(patchplan `reason()` 여섯 축에 없다 — 실측). 그래서 §7 은 dispatch 가 아니라
`_existing_fids_from_console(_SlotReadPort(port))` 를 직접 부른다.

## 7. 뮤테이션 8/8 KILL (`probes/_t194_mutate.py` · 출력 `mutate-out.txt`)

| 뮤턴트 | 파일 | 판정 | 죽은 검사 |
|---|---|---|---|
| M1 어댑터 무력화 | tools | KILL | 3 |
| M2 `except Exception` 넓히기 | tools | KILL | 1 |
| M3 `unreachable` 표식 제거 | tools | KILL | 2 |
| M4 값 지어내기 | tools | KILL | 4 |
| M5 스윕 계수 되돌리기 (**수용 기준 3 파괴**) | patchplan | KILL | 1 |
| M6 스윕 과다계수 (부재까지 셈) | patchplan | KILL | 1 |
| M7 사유 문구 변경 | patchplan | KILL | 1 |
| M8 구별 접기 | patchplan | KILL | 6 |

M5·M6 이 이 회차의 값이다 — **오직 §7 의 새 검사만** 그 둘을 가른다. 1회차 검사 여섯은
둘 다에서 초록이다.

🔴 **계기 수정.** 1회차 하네스는 `PY` 에 **다른 트리의 venv** 경로를 박아 뒀었다
(`/Users/studiox/orca/workspaces/.../LX-SEQ/.venv`). 그것이 1회차의 "7 failed" 중
`test_tree_identity` 를 가짜로 죽였다. 이제 `sys.executable` 을 쓰고 그 환경이 이 트리
안인지 **단언**한다. (그 가드의 1차 판도 틀렸다 — `.venv/bin/python` 은 심볼릭 링크라
`resolve()` 하면 트리 밖으로 나간다. 인터프리터 **바이너리**가 아니라 **환경**
(`sys.prefix`)을 재야 한다. 계기를 고치다 계기를 또 틀린 사례로 남긴다.)

## 8. 전량 스위트

```
uv run pytest server/tests -q   ->  10571 passed, 12 skipped, 0 failed  (147s)
```

1회차의 `6 failed`(vwx 임포트 게이트)가 **0** 이다. 게이트를 우회한 게 아니라
경계를 안 넘는 형태로 갈아탄 결과다.

## 9. 안 잰 것

- **실기 콘솔 0회.** 이 회차도 그대로다.
- `patch_fixtures`(:4411) · `import_lxseq_patch`(:5503)의 **사용자 문면** — 어댑터는
  세 자리 다 끼웠지만 사유 문자열을 실제로 재 본 것은 `import_lxseq_groups` 하나다.
  t188 이 남긴 gap 이 그대로 남는다.
- 🔴 **어댑터가 `query_state` 까지 감싸는 오설계를 아무 검사도 안 잡는다.** 감싸면 루트
  실패가 `ok=False` 로 와서 `patchplan :1493` 이 같은 `unreadable_root()` 를 부르므로
  **사용자 문면이 동일**하고, `tools.py` 의 `except StateQueryError` 만 조용히 죽은
  코드가 된다. 동작 결함은 아니지만 t182 가 세운 자리가 소리 없이 비는 형태다.
  뮤턴트를 안 만들었다 — 만들었어도 초록일 것이라 예측하지만 **안 쟀다.**
- C2(Patch 프로퍼티 사망)가 왜 거절이 아니라 `status=unverified` 로 통과했는지 —
  t188 이 남긴 그대로, 이 회차도 안 쫓았다.

## 10. main 에 실린 틀린 문장 (만료 고지)

`.moai/reports/t188/verdict.md` §7.2 가 "그 경계를 **강제하는 검사가 없다**"라고 적었고
main 에 머지됐다(`dee1da9`). **틀렸다** — §1 이 반증한다. t188 리포트는 그 시점 기록이라
고치지 않고 여기 고지를 남긴다(규약 §5).
