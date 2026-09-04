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

### M3 — 재임포트 1회 + 라이브 검증 + 사실 문서 갱신 (2026-09-04, 읽기 전용 잔여분)

기준 트리: 워크트리 `.claude/worktrees/agent-ab0e1ec2f318efaf1`, 브랜치
`WT-table-serialize`. 인터프리터: **그 트리 자신의** `.venv/bin/python` —
`server.__file__` 이 같은 트리를 가리키는 것을 실행 전에 확인했고
(`/…/agent-ab0e1ec2f318efaf1/server/__init__.py`), 도구의 `assert_same_tree` 가드도 살아 있었다.

**측정 프로브의 콘솔 쓰기 0건** — 쏜 것은 `ping`·`introspect`·`props` 뿐이다.
다만 「이 회차가 콘솔에 아무것도 안 보냈다」는 **거짓이다**: 전체 스위트를 2회 돌렸고
그때마다 `SaveShow` 가 2건씩, 합계 4건 발사됐다(전부 `ok:false`). 이것은 의도한 쓰기가
아니라 스위트의 부수 효과이고, 실측 근거와 기전은 아래 §4 에 적었다.
M3-1(계획상 유일한 쓰기인 1.6.4 재임포트)은 이 회차가 아니라 **오케스트레이터가 수행**했고,
이 절은 그 사실을 인용하되 자기 실측으로 바꿔 적지 않는다.

#### 1. 주장 (Claim)

| AC / 항목 | 판정 | 주장 |
|---|---|---|
| AC-READBACK-015 | **PASS-WITH-FINDING** | 두 팔 중 하나만 선다. **버전 팔 PASS**: 라이브가 `1.6.4` 를 답하고 배포 근거는 `ping` 뿐이다(main 문면을 증거로 쓰지 않았다). **쓰기 예산 팔은 반증됐다**: 「쓰기 명령은 재임포트 1건뿐」이 아니다 — 스위트 실행마다 `SaveShow` 2건이 추가로 발사된다(§4 실측) |
| B2 (Part 클래스 테이블 형상) | **해소** | `SELECTIONDATA` = `{}` · `DEPENDENCIES` = 레코드 배열. Part 7개 실측 |
| `console-channel-facts.md` §4 갱신 | 완료 | 「테이블 주소」 문단을 실측 형상으로 대체 |
| AC-READBACK-016 | PASS | 이 절이 그 5절 형식이고 §4 미검증 절이 비어 있지 않다 |

#### 2. 증거 (Evidence) — 명령과 그 출력

배포 확인(읽기 전용 `ping`, 이 회차가 직접 실행):

```
$ .venv/bin/python server/tools/responder_roundtrip.py \
    --listen-port 9005 --skip-exec --expect-version 1.6.4 --path DataPool --wait 5
round-trip against osc.udp://127.0.0.1:8000 (replies on 9005)
  [PASS] ping: ok
         live version=1.6.4 plugin=CopilotResponder
  [PASS] state: ok
         node={'childCount': 16, 'class': 'Pool', 'name': 'Default'} children=16
result: PASS
```

음성 대조군을 **먼저** 쐈다 — 이것이 통과한 뒤에야 아래 `ok` 가 증거로 선다:

```
$ … introspect_probe.py --listen-port 9005 --path "DataPool/Sequences/3/4/ZZZNOTREAL9"
introspect failed: path segment not found: 'ZZZNOTREAL9' (in DataPool/Sequences/3/4/ZZZNOTREAL9)
exit=1
```

열거 완전성 산술(Part 개체):

```
$ … introspect_probe.py --listen-port 9005 --path "DataPool/Sequences/3/4/1" --all-pages
class: Part | total: 195 | 도착: 195 | truncated: False | paging: complete | 이름 중복 0
```

Part 프로퍼티 판독 — 양성·음성 대조군을 같은 회신에 실었다:

```
$ … introspect_probe.py --listen-port 9005 --path "DataPool/Sequences/3/4/1" \
    --names "NAME,OWNDATAPRESENT,MEMORYFOOTPRINT,SELECTIONDATA,DEPENDENCIES,STOREDDATA,PRESETDATA,REFERENCES,__NOSUCHPROP_CONTROL__"
NAME            t=string  v="Q010 INTRO 화사"      <- 양성 대조군
OWNDATAPRESENT  t=boolean v="true"                 <- 양성 대조군
MEMORYFOOTPRINT t=number  v="4580"                 <- 양성 대조군
SELECTIONDATA   t=table   v="{}"
DEPENDENCIES    t=table   v="[{\"content_crc\":3271575126602050978,\"key\":\"Preset 4.1\",\"name_crc\":-3774025751232341734}]"
STOREDDATA      ok=false  e="property not readable: STOREDDATA"
PRESETDATA      t=string  v=""
REFERENCES      t=string  v=""
__NOSUCHPROP_CONTROL__ ok=false e="property not readable: __NOSUCHPROP_CONTROL__"  <- 음성 대조군
truncated: false
```

Part 7개 표본(한 개체로 클래스를 일반화하지 않기 위해 넓혔다):

| 경로 | NAME | SELECTIONDATA | DEPENDENCIES | truncated |
|---|---|---|---|---|
| `DataPool/Sequences/3/1/1` | `Part 0` | `{}` | `{}` | false |
| `DataPool/Sequences/3/2/1` | `Part 0` | `{}` | `{}` | false |
| `DataPool/Sequences/3/4/1` | `Q010 INTRO 화사` | `{}` | 1건 `Preset 4.1` | false |
| `DataPool/Sequences/3/6/1` | `Q030 VERSE1 확장` | `{}` | 2건 `Preset 4.4`·`Preset 21.1` | false |
| `DataPool/Sequences/3/7/1` | `Q040 PRE1 축적` | 미조회 | 1건 `Preset 4.4` | false |
| `DataPool/Sequences/3/10/1` | `Q070 VERSE2 하강` | 미조회 | 1건 `Preset 4.3` | false |
| `DataPool/Sequences/3/14/1` | `Q110 BRIDGE 절제` | 미조회 | `{}` | false |

값 크기와 상한의 거리(측정):

```
3/4/1 entries=1 bytes=88  cap=240 headroom=152
3/6/1 entries=2 bytes=175 cap=240 headroom=65   (엔트리당 약 87바이트)
```

**콘솔 쓰기 0건의 기계적 근거** — 주장이 아니라 두 갈래로 쟀다:

```
1) 정적: server/tools/introspect_probe.py:139  attempt_session_backup=False
   (build_console_stack 의 기본값은 True 이므로 이 인자가 그 발사를 막는다)
2) 실측: 런타임 감사 로그 server/audit_logs/audit-20260904.jsonl 에서
   이 회차 구간(10:35~10:37) 19행 전부 kind=introspect_query / props_query.
   kind=backup 행 0건.
```

전체 스위트(같은 트리·같은 인터프리터):

```
$ .venv/bin/python -m pytest server/tests -q
10992 passed, 12 skipped, 1 warning in 148.77s (0:02:28)
exit=0
```

#### 3. 기준 귀속 (Baseline-attribution)

- 라이브 계기: 응답기 `1.6.4`, OSC `127.0.0.1:8000` 송신, 회신 포트 `9005`.
  버전은 **이 회차가 직접 쏜 `ping`** 으로 잰 값이다(위 §2). 오케스트레이터도
  같은 결과를 보고했으나, 여기 적은 출력은 이 회차·이 트리에서 다시 잰 것이다.
- 재임포트 행위 자체는 **오케스트레이터 귀속**이다. 이 회차는 그 실행을 관측하지
  않았고, 관측한 것은 그 뒤 상태(`ping` 이 1.6.4 를 답함)뿐이다.
- 스위트 숫자 `10992 passed`는 이 회차에서 다시 잰 값이며 옮겨 온 것이 아니다.

#### 4. 미검증 (Gaps)

- **`SELECTIONDATA` 가 채워지는 조건은 여전히 미관측**(옛 B2 의 남은 절반).
  Part 7개·Preset 2개 전부 `{}` 였다. 「비어 있다」를 쟀을 뿐 **무엇이 이 축을
  채우는지는 못 쟀다** — 채워진 표본을 한 번도 못 봤으므로, 이 채널이 선택
  정보를 실을 수 있는지 자체가 아직 열린 질문이다.
- **Part·Preset 이외 클래스의 테이블 형상은 미관측.** Cue·Sequence·Group 등은
  이 회차가 건드리지 않았다.
- **의존 3건 이상인 Part 를 못 찾아 절단을 재지 못했다.** 3건부터 240바이트를
  넘는다는 것은 87바이트/엔트리에서 나온 **산술이고 측정이 아니다.**
- **`REFERENCES` 의 페이로드는 해독하지 않았다.** Part 에서는 빈 문자열이었고,
  M2 가 Preset 에서 본 `<정수>:<64비트 정수>` 형태와 다르다 — 왜 다른지 안 쟀다.
- **🔴 전체 스위트 실행이 라이브 콘솔에 `SaveShow` 를 2건 쏜다 — 실측, 원인 호출자는 미특정.**
  이 회차가 스위트를 **두 번** 돌렸고, 두 번 다 그 실행 구간 끝에 `kind=backup`
  `command=SaveShow` 행이 **정확히 2행씩** 새로 생겼다 — 1회차 `10:43:17`·`10:43:26`,
  2회차 `10:51:13`·`10:51:22`. 그 두 구간에 다른 종류의 행은 0건이다. 즉
  **스위트 1회 = SaveShow 2건**이 재현됐다(2/2). 같은 짝이 이 회차 이전에도
  하루 종일 남아 있다(08:37·08:43·08:47·10:23) — M0·M2 의 스위트 실행 흔적으로 보인다.
  두 건 모두 `ok:false`(「5초 안에 결과 확인 없음」)이므로 **효과는 확인되지 않았고**,
  발사 자체는 일어났다. 기전은 `build_console_stack` 의 `attempt_session_backup`
  기본값이 **True** 라는 것 — 이 인자를 넘기지 않는 호출자는 스택 조립만으로
  `SaveShow` 를 쏜다(`server/safety/console.py:291` 이 그 대기 문자열의 출처).
  **어느 테스트인지는 특정하지 못했다**: 읽어 본 두 곳(`test_web_e2e.py`
  `test_safety_bootstrap.py`)은 가짜 콘솔·tmp 감사 디렉터리로 격리돼 있어 해당 없다.
  **AC-READBACK-015 의 「콘솔 쓰기 총계 1」 셈은 이 사실 위에서 다시 봐야 한다** —
  이 회차의 프로브는 0건이지만, 스위트를 돌리는 행위가 매번 2건을 더한다.
- **git 검증 일체 미실행** — 이 회차를 실행한 에이전트 세션이 다른 워크트리
  (`agent-ad6f71aaf77af45e9`)에 격리돼 격리 가드가 대상 트리로의 모든 git 명령을
  거부했다. 그래서 `git diff --stat`(범위 침범 검사) · `git status` ·
  PRESERVE 목록 대조 · 커밋을 **하나도 수행하지 못했다.** 아래 §E.3 의 git 계열
  항목이 `unmeasured` 인 이유가 이것이다.

#### 5. 잔여 위험 (Residual-risk)

- **표본이 한 시퀀스(`Sequences/3`)에 몰려 있다.** Part 7개는 전부 같은 시퀀스의
  파트다. 「Part 클래스는 이렇다」가 아니라 「이 시퀀스의 Part 는 이렇다」까지가
  잰 넓이다.
- **쇼 지문은 노화한다.** 이 저장소에는 쇼가 하루 사이에 바뀐 전례가 있다.
  위 경로·이름·CRC 는 2026-09-04 10:35~10:37 시점의 값이고, 재현할 때는
  경로 존재부터 다시 재야 한다.
- `content_crc` · `name_crc` 는 **부호 있는 64비트로 도착한다**(음수 관측:
  `-3774025751232341734`). 소비자가 부호 없는 정수로 읽으면 값이 어긋난다.
- 빈 테이블이 `[]` 가 아니라 `{}` 로 오므로, 소비자가 `DEPENDENCIES` 를 항상
  배열로 가정하면 빈 경우에 타입이 갈린다.

## §E.3 Run-phase Audit-Ready Signal

```yaml
run_complete_at: 2026-09-04T10:46:35Z
run_commit_sha: pending-backfill-m3   # 이 회차는 커밋을 수행하지 못했다 — 아래 blocker 참조
run_status: evidence-complete-commit-blocked

# AC 회계 (정본은 acceptance.md, AC 총 16건)
ac_total: 16
ac_pass_count: 10            # 001·002·003·004·005(M0) · 009·010·013·014(M2) · 016(M3)
ac_pass_with_qualifier: 3    # 006 PASS-WITH-DEBT · 007 PASS-WITH-BLOCKER(M0 기록 그대로) · 015 PASS-WITH-FINDING(M3)
ac_no_recorded_verdict: 3    # 008 · 011 · 012 — 미발견 경로라 공허 충족이나 명시 판정이 기록에 없다
ac_fail_count: 0

# M0 이 남긴 blocker 의 현재 상태 (관측만, M0 판정은 고쳐 적지 않는다)
m0_blocker_expected_responder_version: resolved-observed
  # M0 시점 3건 빨갛던 원인(server/safety/responder_version.py 의 1.6.3 고정)이
  # 지금은 안 보인다 — 전체 스위트 10992 passed / 0 failed. READBACK-002 가
  # 그 한 줄을 옮긴 것으로 보이나, 그 인과는 이 회차가 재지 않았다.

# 이 회차가 만진 파일
m3_files_touched: 2
  # docs/runbooks/console-channel-facts.md
  # .moai/specs/SPEC-COPILOT-READBACK-001/progress.md
total_run_phase_files: unmeasured   # 누적 집계는 git diff 가 필요하고 아래 사유로 못 했다

# 콘솔 예산
console_writes_by_probes: 0
  # 정적 근거: introspect_probe.py:139 attempt_session_backup=False
  # 실측 근거: audit-20260904.jsonl 10:35~10:37 19행 전부 introspect/props, backup 0행
console_writes_by_test_suite: 4
  # 스위트 2회 실행 x SaveShow 2건. 의도한 발사가 아니라 스위트가 부수적으로 쏜 것이고,
  # 4건 모두 ok:false(결과 미확인)다. 상세와 기전은 §E.2 M3 §4 미검증 참조.
  # 「프로브는 0건」과 「이 회차가 콘솔에 아무것도 안 보냈다」는 다른 주장이다 — 후자는 거짓이다.
console_write_budget_total: 1        # M3-1 재임포트 — 오케스트레이터 수행, 이 회차 아님
console_write_budget_caveat: 스위트 1회 실행마다 SaveShow 2건이 발사된다(실측 2/2, §4 참조). 이 회차 스위트 2회 = 4건

# 품질
full_suite: "10992 passed, 12 skipped, 1 warning in 148.11s"   # 문서 편집 후 재측정
full_suite_runs_this_milestone: 2   # 편집 전 148.77s / 편집 후 148.11s, 둘 다 0 failed
new_warnings_or_lints_introduced: 0
  # 이 회차 변경은 마크다운 2개뿐이라 파이썬 린트 표면이 없다. ruff 는 돌리지 않았다.
  # 스위트의 warning 1건은 fastapi/starlette 사전 존재 경고이며 이 회차 유래가 아니다.
cross_platform_build: not_applicable
  # 파이썬 프로젝트이고 교차 컴파일 단계가 없다. 대체 증거는 위 전체 스위트다.

# git 계열 — 전부 미수행 (사유 동일)
l44_pre_commit_fetch: not_performed
l44_post_push_fetch: not_performed
preserve_list_post_run_count: unmeasured
scope_intrusion_check: unmeasured    # server/prechk · vwx · paperwork 대조 못 함
git_blocked_reason: >
  이 회차를 실행한 에이전트 세션이 워크트리 agent-ad6f71aaf77af45e9 에 격리됐고,
  격리 가드가 대상 워크트리(agent-ab0e1ec2f318efaf1)로 향하는 git 명령을 cd 형태와
  -C 형태 양쪽 모두 거부했다. 파일 쓰기는 되었으나 git 은 한 건도 실행하지 못했다.

m1_to_mN_commit_strategy: 마일스톤별 개별 커밋 · 브랜치 WT-table-serialize · 푸시 없음

# 작업 트리 상태 (git 대신 mtime 으로 잰 것 — git 이 막혀 있어 status 를 못 봤다)
working_tree_note: >
  이 회차가 쓴 파일은 정확히 2개다 —
  docs/runbooks/console-channel-facts.md (10:39:58Z) ·
  .moai/specs/SPEC-COPILOT-READBACK-001/progress.md (10:53:25Z).
  그러나 트리에는 이 회차 이전의 미커밋 변경이 이미 있었다:
  server/lxseq/preset_mapper.py 와 docs/research/ma3-effects/10-preset-property-readback-sweep.md
  가 둘 다 10:20:36Z — M2 의 산출물이고 이 회차가 건드리지 않았다.
  또한 스위트 실행이 server/paperwork_output/**.html 과 .pytest_cache · .ruff_cache 를
  트리에 새로 썼다(예: cue_sheet.html 10:50:40Z, 두 번째 스위트 구간).
commit_staging_warning: >
  그러므로 커밋할 때 git add -A 를 쓰면 안 된다. 스위트가 만든 paperwork_output HTML 과
  캐시가 함께 실린다. 경로를 명시해서 담아라 — 최소한
  docs/runbooks/console-channel-facts.md 와 progress.md 두 개이며,
  M2 의 preset_mapper.py 를 이 커밋에 포함할지는 M2 소유자의 판단이다.
m3_commit: PENDING — 작업 트리에 미커밋 상태로 남겨 인계한다
```

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_

## Plan Audit-Ready Signal

- plan_complete_at: 2026-09-03T23:12:38Z
- plan_status: audit-ready
- plan_audit: PASS 0.935 (iteration 3, .moai/reports/plan-audit/SPEC-COPILOT-READBACK-001-review-3.md)
