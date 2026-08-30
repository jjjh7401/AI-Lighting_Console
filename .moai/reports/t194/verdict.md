# t194 — 슬롯 판독 실패를 루트 실패로 접지 않는다 (진행 중 · 리드 판정 대기)

- 브랜치 `WT-slot-read-attribution` · base `822e9bd` · 커밋 `5c3f8ed`
- **미푸시.** 게이트 위반이라 푸시하지 않았다.
- 콘솔 실기 **0회**.

## 0. 상태 한 줄

(B) 를 구현했고 검사·뮤테이션까지 끝냈는데, **전량 스위트가 아키텍처 게이트
위반을 잡았다.** 그 게이트의 존재가 배차서 전제와 내 t188 §7.2 를 둘 다 반증한다.
구현 형태를 (B'') 로 갈아탈 것을 제안하고 판정을 리드에게 올렸다.

## 1. 🔴 반증된 전제 — 경계를 강제하는 검사가 **있다**

| 출처 | 주장 | 실제 |
|---|---|---|
| t194 배차서 (4) | "강제하는 검사가 없다(fx·looks 에는 있고 vwx 에는 없다)" | **틀림** |
| 내 t188 §7.2 | "경계 검사는 fx·looks·paperwork·scene 넷" | **틀림** |

실제 가드: `server/tests/test_autopatch_execute.py`

    test_no_vwx_module_imports_the_console_send_surface[server/vwx/patchplan.py]
      독스트링: "AC-018③ — 콘솔 발화로 이어지는 모듈 import 0건"
      실패:     assert ['server.safety.console',
                        'server.safety.console.StateQueryError'] == []

**계기 오류가 원인이다.** 내 명령줄은 `ls server/tests/ | grep -E '_boundary\.py$'`
였다 — 그것은 **그 이름 규칙을 따르는 파일**을 세지 경계 가드를 세지 않는다.
vwx 가드는 `test_autopatch_execute.py` 안에 산다. 그리고 나는 리드의 문면
("fx·looks 에는 있고")을 그대로 계기 설계에 옮겼다. 규약 3.6 이 말하는
「산출물을 근거로 실을 때는 그것을 만든 명령줄을 같이 실어라」의 반대 사례다 —
내가 명령줄을 실었더라면 리드가 그 자리에서 반증할 수 있었다.

관행이 아니라 **명문화된 수용 기준**이다. round17 적대 감사가 13가지 우회 형태를
실증해 막은 AST 스캐너이고, 상대 import · alias · 동적 import · f-string ·
스타드 인자까지 본다. 등기부(`_REGISTERED_VWX_IMPORTS`)는 손으로 한 줄 더하면
풀리는 **의도된 마찰**이지만 콘솔 워드는 등기부가 아니라 **금지**다.

## 2. 전량 스위트

    uv run pytest server/tests -q      →  6 failed, 10561 passed, 12 skipped

실패 6건 전부 vwx 임포트 게이트다. 내가 추가한 검사 6개는 통과한다.

⚠️ **처음엔 7 failed 였다.** `test_tree_identity.py::test_own_tree_runs_normally` 가
같이 죽었는데, 그건 내가 **남의 트리 venv 를 빌려 쓴** 탓이다
(`ModuleNotFoundError: server.tools.probe_preflight` — 그 파일은 이 트리에 있고
git 에도 있다). `uv run pytest` 로는 4 passed. **계기 문제이지 코드 결함이 아니다.**
대조군으로 갈랐다.

## 3. 구현 형태와 무관하게 살아 있는 것 — 검사 6개

수용 기준을 단언으로 옮긴 것이라 구현이 바뀌어도 그대로 쓴다.
`server/tests/test_lxseq_group_section_request.py` 6절, **13 -> 19 (교체 0)**.

두 팔 대조 (규약 3.6): 수리 전 상태에서 **2개가 죽는다** —
`test_the_slot_reason_actually_reaches_the_payload` ·
`test_the_slot_reason_is_not_byte_identical_to_the_root_reason`.
실패 문면이 t188 이 잰 그 문자열이다:

    AssertionError: assert '콘솔의 픽스처 루트 상태를 읽지 못했다'
                        != '콘솔의 픽스처 루트 상태를 읽지 못했다'

나머지 넷(생존 · 불변식 · 넓히기방지 · 대조군)은 양쪽에서 초록이다. 맞다 —
값어치는 뮤테이션이 말한다(3.5).

## 4. 뮤테이션 6/6 KILL (`probes/_t194_mutate.py`)

| 뮤턴트 | 판정 | 죽은 검사 |
|---|---|---|
| M1 수리 제거 | KILL | 2 (구별 검사 둘) |
| M2 `except Exception` 으로 넓히기 | KILL | 1 (무관 예외 안 삼킴) |
| M3 조용히 삼키기 | KILL | 2 |
| M4 값 지어내기 | KILL | 2 |
| M5 사유 문구 변경 | KILL | 1 |
| M6 루트도 슬롯 사유로 (구별 접기) | KILL | **4** |

**M6 이 이 회차의 값이다.** `test_the_root_failure_still_names_the_root` 는 수리
전후 양쪽에서 초록이라 「이 검사가 필요했나」로 물으면 지워질 팔인데, 구별을 접는
오설계를 가르는 유일한 팔이다. 3.5 의 「불변식 팔」 사례가 하나 더 늘었다.

⚠️ M2 가 t182 의 4절 `LookupError` 팔은 **안 죽였다.** 예측이 어긋난 게 아니라
축이 다르다 — 내 `except` 는 슬롯 경로에 있고 그 검사는 루트를 죽이는 자극이다.
그대로 적어 둔다.

## 5. 제안 — (B''): 경계를 안 넘고 같은 결과를 낸다

`patchplan` **무수정**(독스트링 제외). `tools.py` 안에 `read_existing_fids` 전용
얇은 래퍼를 두고 **`query_property` 의 `StateQueryError` 만** `ok=False` 로 옮긴다.
그러면 `patchplan` 의 **이미 있는** 갈래가 그대로 받는다:

    루트 실패 → :1484 `state.get("ok") is not True` → unreadable_root() → 루트 사유
    슬롯 실패 → :1523 `response.get("ok") is True` 거짓 → unreadable_fids → 슬롯 사유

두 사유가 갈린다 — 수용 기준 만족.

**잰 전제:**
- `tools.py` 는 이미 `:130` 에서 `StateQueryError` 를 임포트한다(경계 안).
- `_InventoryPort` 는 **11자리**에서 만들어지고 그중 **7이 `read_inventory`** 다.
  그래서 공용 어댑터에서 옮기면 t181 이 죽는다(t182 가 든 그 이유, 유효하다).
  → 공용이 아니라 `read_existing_fids` **3자리 전용 래퍼**여야 한다.
- `query_state` 는 **안 건드린다.** 건드리면 루트 실패가 `ok=False` 로 바뀌어
  t182 의 `tools.py:4751` catch 가 죽은 코드가 된다 — 3.6 의 그 형태다.

🔴 **(B'') 의 숨은 비용 — 미측정.** 스윕(`:1551`)의 `except Exception:
probe_failures += 1` 이 포트 예외를 못 받게 된다(번역돼서 `ok=False` 로 온다).
그러면 전송 오류가 「부재」와 한 바구니로 들어가 `probe_failures` 가 그것을 안 센다.
**착수하면 이것부터 재라**: 스윕 프로브를 **예외로 만드는** 검사가 있는지.
확인한 것은 `test_r19_a_pointer_string_from_a_probe_is_never_adopted_as_a_fid`
(`test_autopatch_fid.py:3089`)가 `hidden_mode="pointer"` 즉 `ok=true` + 포인터
문자열을 쓴다는 것뿐이다 — 그 검사는 영향 없다. **예외 팔은 안 찾아봤다.**

## 6. 배제된 안

- **(A) 호출부 세 곳에 각각 `except`** — 리드가 배제. 거짓 사유를 셋으로 복제한다.
- **(B) `patchplan` 안에서 `StateQueryError` 를 잡기** — 구현했고 게이트가 막았다.
  AC-018③ 위반.
- **(B-등기부) AC-018③ 을 고쳐 예외 이름 임포트를 허용** — SPEC 수용 기준 변경이라
  레인 권한 밖이다. 리드 권한도 넘을 수 있다.
- **(C) `except Exception`** — 넓히기. M2 가 그것을 잡는다.

## 7. 안 잰 것

- 실기 콘솔 **0회**.
- (B'') 를 **구현도 측정도 안 했다.** §5 는 설계와 그 전제까지다.
- 스윕 프로브를 예외로 만드는 검사의 존재 여부(§5 의 🔴).
- `patch_fixtures`(`:4369`) · `import_lxseq_patch`(`:5457`)의 사용자 문면 —
  이 회차에서도 안 쟀다. t188 이 남긴 gap 그대로다.
- t182 의 `unreadable_root` 독스트링이 "예외 이름을 부르는 것은 거기 안 걸린다"고
  적고 있는데 **게이트가 실제로 걸었다.** 그 문장은 이제 반증됐다 —
  (B'') 로 가더라도 그 한 줄은 고쳐야 한다(규약 §5, 처방 서술).

## 8. main 에 실린 틀린 문장 (만료 고지)

`.moai/reports/t188/verdict.md` §7.2 가 "그 경계를 **강제하는 검사가 없다** —
경계 검사는 fx·looks·paperwork·scene 넷이고 vwx 것이 아니다"라고 적었고
main 에 머지됐다(`dee1da9`). **그 문장은 틀렸다** — 위 §1 이 반증한다.
t188 리포트는 그 시점 기록이라 고치지 않고 여기 고지를 남긴다(규약 §5).
