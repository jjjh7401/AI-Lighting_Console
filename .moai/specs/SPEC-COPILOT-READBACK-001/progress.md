# SPEC-COPILOT-READBACK-001 — 진행 기록

> 단계별 증거를 적는 자리. plan 단계는 §E.1 만 채우고 §E.2~§E.4 는 각 단계의 소유자가 채운다.

## §E.1 Plan-phase Audit-Ready Signal

- SPEC 작성 완료 2026-09-03 — `spec.md` · `plan.md` · `acceptance.md` (Tier M) + 동봉 `research.md`(오케스트레이터 작성, 기준 `origin/main adae0ac`).
- SPEC ID 정규식 검사: `[[ "SPEC-COPILOT-READBACK-001" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]]` → `PASS`.
- 코드 좌표 실측 확인(2026-09-03): `copilot_responder.lua:82` `VERSION = "1.6.3"` · `M.safe_property` 의 `tostring(value)` · `console.py:297-307` 이 payload 를 버림 · `render.py:87` `escape(row.fixture_type or '')` · `read_inventory` 호출 7건 중 `type_names=` 는 `tools.py:6356` 하나뿐 · 다이제스트 고정 `test_overlap_preserve.py:227-231`.
- 미검증: 프리셋 값 프로퍼티의 존재 여부(M2 산출물) · `SELECTIONDATA`/`DEPENDENCIES` 실제 형상 · 라이브 응답기 버전.

### 개정 0.1.1 — plan-audit iteration 1 (FAIL 0.795) 대응 2026-09-03

- **D1 / MP-7 해소**: 미해결 결정 마커 2건이 오케스트레이터 결정으로 확정돼 `plan.md §C` 가 「결정 기록(DECIDED)」 표로 재작성됐다 (C-1 자체 health state · C-2 `v` 안 JSON 문자열). 마커 문자열 잔존 0건 — 디렉터리 전체 grep 무매치(2026-09-03 실행, 아래 §E.1 검증 명령 참조). 상태 보고에도 마커 문자열을 다시 적지 않는다 — 그 자체가 grep 을 오염시킨다.
- **D2 / MP-1 해소**: REQ 를 `REQ-READBACK-001..032` 연속으로 재번호(공백 0). 32번째는 D5 가 신설한 조회 예산 REQ 다.
- **D3 해소**: 33개 AC 전부에 `↔ REQ-READBACK-0xx` 명기 + `acceptance.md §H` 커버리지 표(REQ 32개 → AC) 신설 + `spec.md §C` 에 AC 열 추가. §E 교차 대응 4건을 명시적으로 적었다.
- **D4 해소**: `### Out of Scope —` H3 8개 전부가 `-` 불릿을 갖는다(1개는 조회 예산 축으로 신설).
- **D5 해소**: `tools.py` 여섯 호출 지점의 fixture-type 트리 보유 여부를 실측해 `plan.md §B B5` 표에 기록(예 3 / 아니오 3, 다섯 핸들러). REQ-READBACK-027 이 지점당 추가 `query_state` 1회를 상한으로 묶고, AC-READBACK-027a(N+1) · 027b(N+0 부정 대조군)가 조회 계수 포트로 이진 판정한다.
- **D6 해소**: 어긋난 행 앵커 9건을 HEAD `adae0ac` 에 대고 재측정해 정정 — `max_payload` `:42`→`:41` · `max_prop_value` `:44`→`:43` · 배열 휴리스틱 `:146`→`:147` · `table.sort(keys)` `:157`→`:158` · `M.json_encode` `:133-165`→`:133-166` · `build_patch_sheet` `data.py:83-140`→`:82-147` · `found` 검사 `diff.py:148`→`:150` · `HANDLE_TEXT` `inventory.py:110`→`:111` · `_audit.log_blocked` `gate.py:430-431`→`:429`. 추가로 `_name_handle_types` 문서 `:471-476`→`:469-473` · `console.py:297-306`→`:297-307` · `diff.py:181-187`→`:179-185` · `:188-194`→`:188-192` · `inventory.py:497-502`→`:479-485`.
- **D7/D10 해소**: 프로세스 주어 REQ 5건을 컴포넌트 주어로 교체(`the 프로젝트`→`the 조사 스윕` · `the SPEC`→`the 조사 노트`+`the 임포트 매퍼` · `the 개정`→`the value_match 고정 테스트`/`the 번역 기계`/`the 조사 노트`). REQ-READBACK-010 의 주입 지점·반환 형상 문장(HOW)은 `plan.md §E M2 후속 표`로 이관했다.
- **D8 (optional) 해소**: AC-READBACK-001 에 회신 키 집합 동일성 단언 · AC-READBACK-012 에 「고정 갱신은 라이브 증거와 같은 커밋」+「노트가 제거보다 먼저」 단언 · AC-READBACK-030 에 `exec: ok` 미인용 항목을 추가했다.
- **D9 (optional) 해소**: `acceptance.md §A` 라이브 블록 헤더를 「라이브 검증(읽기 전용) — M3, 운영자 승인 후」로 바꾸고, 유일한 쓰기(재임포트)가 `plan.md §E M3-1` 소유임을 주석으로 명시했다.
- **미검증(0.1.1 기준)**: 조회 재사용이 `walk_mode_widths` 경로에서 실제로 배관 가능한지는 **재지 않았다**. AC 개수 33 / REQ 개수 32 의 비대칭은 의도된 것이며(AC-003a/b/c · 027a/b 하위 ID), 번호 대응은 §H 표만이 정본이다. — 이 항목은 0.2.0 분할로 **SPEC-COPILOT-READBACK-002 로 이관**됐다.

### 개정 0.2.0 — plan-audit iteration 2 (PASS 0.925) D11 대응 · SPEC 분할 2026-09-03

- **D11(Tier 예산 2배 초과) 해소 — 분할**. 감사는 REQ 32 / AC 33 이 Tier M 상한(각 16)의 정확히 2배를 넘는다고 판정했고, 감독이 2026-09-03 에 **두 Tier M SPEC 으로 분할**을 결정했다. 분할선은 옛 `plan.md:83` 이 이미 「순수 서버 · 병렬 가능」으로 떼어 둔 자리를 그대로 썼다.
  - 본 SPEC(001) = **R1 응답기 테이블 직렬화 + R2 프리셋 값 측정** → REQ **15** / AC **16**.
  - 신설 SPEC-COPILOT-READBACK-002 = **R3 런타임 버전 게이트 + R4 FixtureType 번역** → REQ **14** / AC **16**.
- **횡단 규율 5건(옛 REQ-028~032)의 배분**: 옛 028(쓰기 예산 1회) + 029(ping 근거)를 하나로 접어 REQ-READBACK-008 로, 옛 032(잠금 규약)를 REQ-READBACK-007 로 — 셋 다 R1 의 1.6.4 배포 행위에 구속되기 때문이다. 옛 030(5절 형식) + 031(`exec: ok` 금지)은 한 건의 횡단 REQ-READBACK-015 로 합쳤고, 002 는 같은 규율을 자기 REQ-014 로 따로 갖는다.
- **REQ 병합(부정 대조군 무손실)**: 옛 001+002(회신 형상) → REQ-001, 옛 004+005 는 **병합하지 않고** 각각 REQ-003·REQ-004 로 유지(깊이/순환과 배열 판정은 부정 대조군이 다르다), 옛 008+009(조사 스윕 + 노트 기록 규율) → REQ-009. AC 는 옛 003b+003c 를 두 Given 팔을 가진 AC-003 하나로, 옛 001+002 를 AC-001 하나로, 옛 028+029 를 AC-015 하나로 합쳤다. **부정 대조군은 5종 전부 살아 있다**(해시-with-`[1]` · 순환 · 깊이 · 절단 · 메타메소드).
- **D12(잔존 산출물 주어) 해소**: 옛 `the 근거`/`the 되읽기 주장`/`the 실행 결과` 셋을 행위자로 교체 — `the 재임포트 실행자`(REQ-008) · `the 완료 보고 작성자`(REQ-015) · `the 1.6.4 개정 커밋 작성자`(REQ-007). 네 번째(옛 `the 저장소`, REQ-016)는 002 로 이관되며 그쪽에서 `the 안전 모듈` 로 교체됐다.
- **D13(하위 ID 설명) 해소**: `acceptance.md §F` 도입문이 REQ 15 / AC 16 의 개수와 **이 SPEC 에 하위 ID 가 없다는 사실**, 그리고 개수 차 1의 실제 사유(REQ-004 가 AC 두 건으로 갈림)를 적는다.
- **D14(조사 노트 판정의 주관성) 해소**: REQ-READBACK-012 가 `시도한 이름` · `사유` · `대조군` · `실행일` 네 표제를 **리터럴로** 요구하고, AC-READBACK-013 이 `grep -c -E '^#{1,6}\s*(시도한 이름|사유|대조군|실행일)\b'` 가 **4** 를 답할 것을 이진 판정 조건으로 못박는다. R2 종료가 사람의 독해에서 명령으로 옮겨졌다.
- **B5 조회 예산 실측표 이관**: 옛 `plan.md §B B5`(여섯 호출 지점의 fixture-type 루트 보유 여부)는 R4 소속이므로 002 `plan.md §B` 로 옮겼고, 본 SPEC `plan.md §B` 에는 포인터만 남겼다. 결정 C-1(자체 health state)도 002 `plan.md §C` 로 이관, C-2(`v` 안 JSON)는 본 SPEC 에 남았다.
- **행 앵커 재검증(2026-09-03, HEAD `adae0ac`)**: 분할로 두 SPEC 에 나눠 실린 앵커를 트리에 대고 다시 읽었다. 정정 2건 — `build_patch_sheet` 범위 `data.py:82-147`→**`:82-143`**(147행은 함수 밖 빈 줄·구획 주석), `presets_api.py` 반환 형상 `:265-285`→**`:279-284`**(실제 반환 딕셔너리). 나머지는 일치. 새로 기록: `read_fixture_type_names` 호출 자리 `tools.py:6352`, `fuzzy_type_equal` 정의 자리 `server/vwx/rig.py:58`(사용은 `diff.py:180`).
- **미검증(이번 개정 기준)**: 분할 자체는 문서 작업이므로 코드·콘솔 접촉 0. R1·R2 의 미측정 항목(프리셋 값 프로퍼티 존재 여부 · `SELECTIONDATA`/`DEPENDENCIES` 실제 형상 · 라이브 응답기 버전)은 그대로 남아 있고 `plan.md §B` 가 소유한다.

## §E.2 Run-phase Evidence

### M0 — R1 오프라인 직렬화 (2026-09-04, cycle_type=tdd)

기준 트리: 워크트리 `.claude/worktrees/agent-ab0e1ec2f318efaf1`, 브랜치
`worktree-agent-ab0e1ec2f318efaf1`, 베이스 `origin/main 7cdb765`(READBACK-002
머지 후). 인터프리터: 이 워크트리 자신의 `.venv/bin/python`(`uv run`).
**콘솔 접촉 0** — 라이브 명령을 한 건도 쏘지 않았다.

#### 1. 주장 (Claim)

| AC | 판정 | 주장 |
|---|---|---|
| AC-READBACK-001 | PASS | 테이블 값이 `v` 안 JSON 으로 도착하고, 회신 키 집합이 그대로이며, 두 번 읽으면 바이트 동일하다 |
| AC-READBACK-002 | PASS | `[1]` 키를 가진 해시가 `name`·`flag` 를 잃지 않는다 |
| AC-READBACK-003 | PASS | 자기참조 테이블이 회신을 내고 재방문 지점이 `"<cycle>"` 를 담는다 · 깊이 8 초과 노드가 `"<max depth 8 exceeded>"` 로 대체된다 |
| AC-READBACK-004 | PASS | 절단된 테이블 값이 `json.loads` 를 통과하고 항목이 `truncated:true` 를 단다 |
| AC-READBACK-005 | PASS | `__index`·`__tostring`·`__pairs`·`__len` 어느 것도 발동하지 않는다 |
| AC-READBACK-006 | **PASS-WITH-DEBT** | 예산 테스트가 통과하고 `max_payload` 는 `1900` 그대로다. 다만 **값 상한을 올리지 않았다** — AC 의 Given(「상한이 상향된 상태」)이 성립하지 않는다. 사유는 아래 §4 |
| AC-READBACK-007 | **PASS-WITH-BLOCKER** | 다이제스트 2건 재고정 · 날짜 붙은 승인 블록 · `VERSION`/테스트 리터럴 전부 `1.6.4`. 다만 `EXPECTED_RESPONDER_VERSION` 이 범위 밖이라 전체 스위트가 3건 빨갛다 — 아래 §4 |
| AC-READBACK-008~014 | 미착수 | M2 소유(읽기 전용 측정 스윕) |
| AC-READBACK-015 | 미착수 | M3 소유(재임포트 1회) |
| AC-READBACK-016 | 진행 중 | 이 절이 그 5절 형식이다 |

#### 2. 증거 (Evidence) — 명령과 그 출력

RED 증거(GREEN 이전에 잡은 실패 출력, `.moai/state/verify/readback001/red.txt`):

```
$ uv run pytest server/tests/test_lua_responder.py::TestTableValueSerialization \
    server/tests/test_lua_responder.py::TestLoading server/tests/test_responder_deploy.py -q
FAILED …::test_a_table_value_arrives_as_parseable_json_in_v
FAILED …::test_two_reads_of_the_same_table_are_byte_identical
FAILED …::test_a_hash_carrying_key_1_keeps_every_other_key
FAILED …::test_a_dense_integer_table_is_still_an_array
FAILED …::test_a_self_referential_table_replies_instead_of_hanging
FAILED …::test_nesting_past_the_depth_cap_is_cut_and_marked
FAILED …::test_a_truncated_table_value_still_parses
FAILED …::test_serialization_never_fires_a_metamethod
FAILED …::test_a_wide_table_read_still_fits_the_payload_budget
FAILED …::test_the_prop_verb_carries_the_same_json
FAILED …::TestLoading::test_module_export_and_defaults
FAILED server/tests/test_responder_deploy.py::TestVersionBump::…
12 failed, 12 passed in 0.34s
```

`acceptance.md §A` 오프라인 3줄(구현 후):

```
$ uv run pytest server/tests/test_lua_responder.py \
    server/tests/test_lua_responder_payload_budget.py \
    server/tests/test_responder_protocol.py -q
186 passed in 0.71s

$ uv run pytest server/tests/test_overlap_preserve.py -q
54 passed in 0.62s

$ uv run pytest server/tests/test_lxseq_preset_mapper.py \
    server/tests/test_web_presets_api.py -q
73 passed, 1 warning in 0.34s
```

AC 별 개별 판정(`-v`, 13/13 PASSED):

```
$ uv run pytest "server/tests/test_lua_responder.py::TestTableValueSerialization" -v
… test_a_table_value_arrives_as_parseable_json_in_v PASSED
… test_the_reply_item_key_set_is_unchanged_from_1_6_3 PASSED
… test_two_reads_of_the_same_table_are_byte_identical PASSED
… test_a_hash_carrying_key_1_keeps_every_other_key PASSED
… test_a_dense_integer_table_is_still_an_array PASSED
… test_a_self_referential_table_replies_instead_of_hanging PASSED
… test_nesting_past_the_depth_cap_is_cut_and_marked PASSED
… test_a_truncated_table_value_still_parses PASSED
… test_a_short_table_value_is_not_marked_truncated PASSED
… test_serialization_never_fires_a_metamethod PASSED
… test_the_payload_budget_constant_is_untouched PASSED
… test_a_wide_table_read_still_fits_the_payload_budget PASSED
… test_the_prop_verb_carries_the_same_json PASSED
13 passed in 0.17s
```

잠금 규약(AC-READBACK-007):

```
$ git hash-object console/lua/copilot_responder.lua console/lua/PROTOCOL.md
6c6fa0f25728378a684fddb507781d9b77e01878
ec08949e5a56511861648fa9311ef28ca20924df

$ uv run pytest "server/tests/test_overlap_preserve.py::TestConsoleLuaReadmeGrantedException" -v
… test_the_locked_console_lua_assets_are_byte_identical PASSED
… test_the_revised_assets_match_the_granted_digests_exactly PASSED
… test_the_only_console_lua_changes_are_the_granted_ones PASSED
… test_the_grant_is_not_an_empty_exemption PASSED
4 passed in 0.09s
```

재고정 전/후 다이제스트: `copilot_responder.lua`
`75ab824876e93c6eef81827a6b85b6ce7af3535b` → `6c6fa0f25728378a684fddb507781d9b77e01878`,
`PROTOCOL.md` `984210533aab40501e32309c4db8cde5bb4f34ba` →
`ec08949e5a56511861648fa9311ef28ca20924df`.

범위 침범 검사(002 소유 디렉터리 5종):

```
$ git diff --name-only origin/main | grep -E '^(server/prechk/|server/vwx/|server/paperwork/|server/safety/|ui/)'
(출력 없음, exit 1)
```

#### 3. 기준 귀속 (Baseline-attribution)

착수 전 대조군: 같은 트리·같은 명령으로 잰 초록 baseline —
`uv run pytest server/tests/test_lua_responder.py server/tests/test_lua_responder_payload_budget.py server/tests/test_responder_protocol.py server/tests/test_overlap_preserve.py -q`
→ `227 passed in 2.89s` (베이스 `7cdb765`, 편집 전). 위 숫자는 전부 **이 회차·이
트리**에서 다시 잰 값이며, 다른 세션의 숫자를 옮겨 온 것이 없다.

#### 4. 미검증 (Gaps)

- **B2 — `SELECTIONDATA`/`DEPENDENCIES` 의 실제 테이블 형상은 여전히 미관측**
  (`console-channel-facts.md:121`). 오프라인 테스트가 고정한 것은 **아무도 이
  콘솔에서 본 적 없는 형상** 위에서의 인코더 거동이다. 실제 형상이 어긋나면
  이 초록은 그 사실을 말해 주지 않는다. M3 3번이 이 구멍을 닫는다.
- **B3 — 라이브 응답기 버전 미측정.** 이 회차는 `ping` 을 쏘지 않았다. main 이
  1.6.4 를 담는 것은 배포의 증거가 아니다(live-1.6.1 / main-1.6.2 전례).
- **프리셋 객체가 테이블 값 프로퍼티를 갖는지 재지 않았다** — R1 은 능력이고
  그 질문은 R2(M2)다. 능력이 열렸다는 것이 값이 있다는 뜻이 아니다.
- **값 상한(`max_prop_value = 240`)을 올리지 않았다 — 이것은 산술이 강제한
  결과가 아니라 결정이다.** REQ-READBACK-006 은 [Where] 조건절이고 그 전건이
  성립하지 않는다. 처음에 적었던 사유(「percent-encoding 이 3배로 부풀어
  240 이 이미 예산의 1/3」)는 **재지 않은 어림이었고, 재 보니 틀렸다**:

  ```
  $ uv run python -c '… h.module["percent_encode"](h.module["json_encode"](t)) …'
  raw_json_bytes 117
  percent_encoded_bytes 167
  expansion_ratio 1.427
  ```

  (문자열 4개짜리 테이블 값 기준. 영숫자는 그대로 통과하고 `{`·`"`·`:`·`,`
  만 3바이트가 되므로 팽창률은 내용에 따라 움직인다 — 이 값도 한 형태에서
  잰 한 점이다.) 즉 `max_payload = 1900` 에는 여유가 있고, 테이블 값에
  한정한 상향은 **산술적으로 가능하다.** 올리지 않은 이유는 두 가지다:
  (1) M0 계획표가 요구하지 않았고 REQ 는 조건절이며, (2) `max_prop_value`
  는 스칼라 값과 공유되므로 전역 상향은 16개 이름 요청에서 예산 가드가
  **더 많은 읽기를 버리게** 만든다 — SPEC 이 요구하지 않은 스칼라 쪽 거동
  변경이다. 테이블 전용 상한을 새로 두는 형태(REQ 문면이 가리키는 형태)는
  가능하지만 새 설정 키가 늘어난다. **감독/오케스트레이터 결정 사안으로
  남긴다.** 지금 상태에서 240바이트는 20바이트 값 기준 약 7 엔트리다.
- **@MX ANCHOR 파일 상한 초과가 1건 늘었다**: `copilot_responder.lua` 는 이
  변경 **전에 이미 5개**(상한 3)였고 이번에 6개가 됐다. 남의 앵커를 강등하는
  것은 범위 밖이라 손대지 않았다.
- **전체 스위트가 3건 빨갛다** — 전부 한 줄이 원인이다:
  `server/safety/responder_version.py:35` 의 `EXPECTED_RESPONDER_VERSION`
  이 `"1.6.3"` 에 고정돼 있다. 그 파일은 SPEC-COPILOT-READBACK-002 소유이고
  본 회차의 PRESERVE 목록에 있어 **손대지 않았다**. 그 파일의 주석이 이
  인계를 미리 적어 뒀다 — 「001 이 응답기를 1.6.4 로 올리면 바뀌는 것은 이 한
  줄뿐이다」. 판정은 오케스트레이터 몫이다.

#### 5. 잔여 위험 (Residual-risk)

- 깊이 상한 8 과 순환 표식 문자열(`<cycle>` · `<max depth 8 exceeded>`)은
  **콘솔 값이 아니라 응답기가 만든 문자열**이다. 소비자가 이 문자열을 값으로
  오독할 수 있다. 계약은 `PROTOCOL.md` §4.8 에 적었지만 스키마 검증은 없다
  (`server/bridge/protocol.py:77-113` 에는 원래 없다).
- 넓은 테이블에서 **절단이 기본 경로**다. 240바이트는 실제 프리셋 테이블에
  비해 좁으므로, 값이 나오더라도 첫 몇 엔트리만 보일 공산이 크다. 「보였다」와
  「전부 보였다」를 소비자가 구별하려면 항목의 `truncated` 를 반드시 읽어야
  한다.
- 순환 탐지는 **조상 기준**이다(빠져나올 때 표식을 지운다). 같은 테이블을
  형제 자리에서 여러 번 참조하는 DAG 는 순환이 아니므로 여러 번 인코딩되고,
  깊이 상한만이 그 폭을 막는다. 병적인 DAG 에서의 인코딩 비용은 안 쟀다.
- 배열 판정을 `[1]` 휴리스틱에서 「1..n 연속 정수 전체」로 바꿨다. 기존 회신
  배열은 전부 `M.array()`(ARRAY_MT) 로 표시돼 있어 영향이 없음을 스위트로
  확인했지만, 표시 없이 배열로 인코딩되기를 기대하던 **외부** 소비자가 있다면
  그쪽은 안 쟀다.

### M2 — R2 측정 스윕 (읽기 전용 · 콘솔 쓰기 0건)

**판정: 미발견(measured-absent)** — 판독 가능한 값 프로퍼티 0건. 고정 테스트 3건은 초록 그대로.

| AC | 판정 | 증거(명령 + 관측 출력) |
|---|---|---|
| AC-READBACK-009 (음성 대조군) | PASS | `introspect_probe --names "…,__NOSUCHPROP_CONTROL__"` → `{"e":"property not readable: __NOSUCHPROP_CONTROL__","ok":false}`. 노트가 21건을 「0 건」이 아니라 「재지 못함」으로 분류 |
| AC-READBACK-010 (열거 완전성 산술) | PASS | `introspect_probe --all-pages` → `total:138` · 도착 138(27+28+26+26+26+5) · 마지막 창 `truncated:false` · `paging:"complete"`. 세 값 정합 |
| AC-READBACK-013 (미발견 경로 표제 grep) | PASS | `grep -c -E '^#{1,6}\s*(시도한 이름\|사유\|대조군\|실행일)\b' docs/research/ma3-effects/10-preset-property-readback-sweep.md` → **4** |
| AC-READBACK-014 (팔레트 위장 금지) | PASS | `presets_api.py` 무변경 — 콘솔 유래 값 필드를 신설하지 않았다. 근거가 없으므로 만들지 않는다 |

**라이브 계기**: 응답기 `1.6.4`, OSC `127.0.0.1:8000`, 회신 포트 `9005`.
`responder_roundtrip --expect-version 1.6.4` → `[PASS] ping: ok / live version=1.6.4`.

**마일스톤 도중 응답기 버전이 바뀌었다 (1.6.3 → 1.6.4)**. M2 스윕을 1.6.3 에 대고 한 번
끝낸 뒤 운영자가 1.6.4 를 재임포트했고(`2026-09-04T10:09:46Z` 에 `ping` 으로 확인),
**전 구간을 1.6.4 에 대고 다시 쟀다.** 이 재임포트는 M2 가 수행한 행위가 아니다 —
M2 의 콘솔 쓰기는 여전히 **0건**이다.

**B2 해소**: 1.6.3 에서 주소만 답하던 세 이름이 1.6.4 에서 JSON 을 답했고, 바뀐 값은
정확히 그 셋뿐이다 — `SELECTIONDATA` `table: 0x…`→`{}`, `DEPENDENCIES` `table: 0x…`→`{}`,
`DOSHUFFLE` `PropertyInvokeMeta: 0x…`→`{"Property":"DOSHUFFLE","Target":"Preset 4.1"}`.
Preset 개체에서 두 테이블은 **비어 있다**(Part 등 다른 클래스는 여전히 미관측).

**미검증**: `REFERENCES` 의 `<정수>:<64비트 정수>` 페이로드는 해독하지 않았고 회신에서
절단된다(`truncated:true`, 240자 관측 — 1.6.3 에서도 동일) · Preset 이외 클래스의 테이블
형상 · Dimmer·Color 2개체 외 다른 featureGroup 의 열거 목록 동일성.

산출물: `docs/research/ma3-effects/10-preset-property-readback-sweep.md`

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_

## Plan Audit-Ready Signal

- plan_complete_at: 2026-09-03T23:12:38Z
- plan_status: audit-ready
- plan_audit: PASS 0.935 (iteration 3, .moai/reports/plan-audit/SPEC-COPILOT-READBACK-001-review-3.md)
