# SPEC-COPILOT-READBACK-001 — 구현 계획

> 정본은 `spec.md`. 이 문서는 **되돌리기 어려운 결정을 먼저** 놓고 기계적인 작업을 뒤로 미룬 실행 순서다.
> 기준 트리 `origin/main adae0ac` · 조사 근거 `research.md` §R1·§R2 · 개발 방식 TDD.
> REQ 번호는 spec.md 0.2.0 의 연속 번호(REQ-READBACK-001~015)를 따른다.

## A. 맥락

본 SPEC 은 분할 후 **두 축**만 갖는다. R1 은 잠긴 경계를 건드리고 **운영자 승인 재임포트 1회**를 소비한다. R2 는 코드가 아니라 **측정**이 먼저이고, 그 측정 결과가 R2 의 형상 자체를 정한다.

따라서 마일스톤 순서는 「쉬운 것부터」가 아니라 **「바뀔 가능성이 큰 결정부터」**다: 배포되면 되돌리는 데 재임포트가 또 한 번 드는 회신 형상(M0)이 먼저이고, 형상을 확정한 뒤에 읽기 전용 측정(M2), 마지막이 콘솔을 건드리는 배포(M3)다.

R3(버전 게이트)·R4(타입명 번역)는 **SPEC-COPILOT-READBACK-002** 로 떨어져 나갔다. 두 SPEC 은 파일이 겹치지 않으므로 **병렬로 진행할 수 있고**, 002 는 1.6.4 배포를 기다리지 않는다.

## B. 알려진 문제 (착수 전 재측정 대상)

| # | 항목 | 상태 |
|---|---|---|
| B1 | 프리셋 객체의 실제 프로퍼티 138개 목록은 **아무 문서에도 전수 기록돼 있지 않다.** t95 는 개수만 기록했다 | 미측정 → M2 의 산출물 |
| B2 | `SELECTIONDATA`·`DEPENDENCIES` 의 **실제 테이블 형상**은 미관측(`console-channel-facts.md:121`). R1 오프라인 테스트는 **아무도 본 적 없는 형상** 위에서 통과할 수 있다 | 미측정 → M3 에서 기록 |
| B3 | 라이브 응답기 버전은 미상. main 은 1.6.3(`copilot_responder.lua:82`, 2026-09-03 실측). live-1.6.1/main-1.6.2 전례가 있으므로 **라이브를 `ping` 으로 재라** | 미측정 → M3 |

> **조회 예산 실측표는 여기 없다.** `read_inventory` 여섯 호출 지점이 fixture-type 루트를 이미 읽는가를 잰 표(옛 §B B5)는 R4 에 속하므로 **SPEC-COPILOT-READBACK-002 `plan.md` §B** 로 옮겼다. 본 SPEC 은 `server/prechk/**` · `server/vwx/**` · `server/paperwork/**` 를 읽지도 고치지도 않는다.

## C. 결정 기록 (DECIDED)

> iteration 1 감사(D1 / MP-7)에서 미해결 결정 마커가 잡혔다. 오케스트레이터가 2026-09-03 에 확정했으므로, 이 절은 마커가 아니라 **결정**을 싣는다. 마커 문자열은 이 SPEC 어디에도 남지 않는다.

| # | 주제 | 채택 | 기각 | 기각 사유 | 파급 파일 | 결정일 |
|---|---|---|---|---|---|---|
| C-2 | 테이블 값의 회신 형상 | **`v` 안의 JSON 문자열** — `t="table"` 유지, 형제 필드 신설 없음, `PROTOCOL.md` 는 **주석 한 줄만** 추가 | 구조화된 형제 필드 신설 | 형제 필드는 소비자 파싱이 편하지만 `PROTOCOL.md` §4.6/§4.8 **개정** + 두 번째 다이제스트 재고정 + 「응답기는 해석하지 않는다」 계약의 재해석을 요구한다. `v` 안 JSON 은 회신 형상이 바뀌지 않으므로 기존 디코드 지점(`server/bridge/protocol.py:77-113`)과 모든 기존 소비자가 **무변경**이다 | `console/lua/copilot_responder.lua`(`M.safe_property` `:290-308` · `M.json_encode` `:133-166`) · `console/lua/PROTOCOL.md`(§4.6·§4.8 주석) · 기존 소비자 **무변경** | 2026-09-03 |

C-2 는 REQ-READBACK-001 로 spec.md 에 이미 반영돼 있다. 착수 전에 다시 열 사안이 아니다.

> **C-1(응답기 버전 불일치의 health state)은 이 SPEC 의 결정이 아니다.** R3 에 속하므로 **SPEC-COPILOT-READBACK-002 `plan.md` §C** 가 그 결정을 소유한다.

## D. 제약

- 콘솔 쓰기 총 예산 **1회**(재임포트). M0·M2 는 쓰기 0. SPEC-COPILOT-READBACK-002 도 쓰기 0 이므로 이 1회가 두 SPEC 을 합친 전체다.
- `console/lua/` 는 다이제스트 잠금. 편집은 날짜 붙은 승인 블록 + 재고정과 **같은 커밋**.
- TDD. R1 은 `server/tests/lua_mock_env.py` 가 실제 `.lua` 를 lupa 로 돌리므로 라이브 없이 RED 가능.
- `server/prechk/**` · `server/vwx/**` · `server/paperwork/**` 는 **범위 밖**(002 소유). 본 SPEC 의 diff 에 이 세 디렉터리가 나타나면 범위 침범이다.

---

## E. 마일스톤

### M0 — R1 오프라인 직렬화 (되돌리기 가장 어려운 결정이 여기 있다)

`v` 의 형상은 §C C-2 로 확정됐고, 그 형상은 **콘솔에 배포되는 순간 되돌리는 데 또 한 번의 재임포트**가 든다. 그래서 첫 번째다.

| 파일 | 델타 | 내용 |
|---|---|---|
| `console/lua/copilot_responder.lua` | [MODIFY] | `M.safe_property` `:290-308` 에 테이블 분기 · `M.json_encode` `:133-166` 에 깊이 상한·순환 탐지·명시적 배열 판정 · 구조적 절단 · `VERSION` `:82` → `1.6.4` · 변경 이력 블록 추가 |
| `console/lua/PROTOCOL.md` | [MODIFY] | §4.6·§4.8 에 테이블 값 계약 명문화(주석 한 줄, §C C-2) |
| `server/tests/test_lua_responder.py` | [MODIFY] | 직렬화 · 순환 · 깊이 · 해시-with-`[1]` · 구조적 절단 · **회신 키 집합 동일성** 케이스 추가, 버전 리터럴 `:81` |
| `server/tests/lua_mock_env.py` | [MODIFY] | `__NODE._props` 에 테이블 값을 심을 수 있게 확장 |
| `server/tests/test_overlap_preserve.py` | [MODIFY] | 날짜 붙은 승인 블록 + 다이제스트 2건 재고정 `:227-231` |
| `server/tests/test_responder_deploy.py` `test_responder_roundtrip.py` | [MODIFY] | 버전 리터럴 `:177` / `:125,128,136` |
| `server/tests/test_lua_responder_payload_budget.py` | [EXISTING] | 2048 산술 — 값 상한 상향의 천장 |

산출: 오프라인 전부 초록. **콘솔 접촉 0.** (AC-READBACK-001~007)

### M2 — R2 측정 스윕 (읽기 전용 · 1.6.3 에서 실행 가능)

> 마일스톤 번호 M1 은 비어 있다. 옛 M1(R3+R4)이 SPEC-COPILOT-READBACK-002 로 이관됐고, 남은 번호를 당기면 이미 배차된 문서·보고서의 참조가 어긋난다. 번호 공백은 이관의 흔적이지 누락이 아니다.

**1.6.4 배포를 기다리지 않는다.** 이름 열거와 판독 시도는 **1.6.3 페이징으로 충분**하다 — 테이블 값이 실제로 나올 경우에만 1.6.4 가 필요하고, 그 경우 판독 시도는 `table: 0x…` 주소를 답하는데 **그것 자체가 「테이블 값 프로퍼티가 존재한다」는 양성 신호**다. 즉 1.6.3 로도 R2 의 질문에는 답할 수 있다.

절차:

1. 프리셋 객체 1개에 `introspect` 전수 열거(페이징, `childCount` 대조 + `truncated` 판독).
2. 나온 이름 전부에 `props` 판독. 결과를 이름별로 기록 — 값 · 사유 문자열 · 타입.
3. **양성 대조군**: 판독된다고 이미 알려진 프로퍼티(예: `name`)를 같은 스윕에 포함해 계기가 살아 있음을 보인다.
4. **음성 대조군**: 존재하지 않는 이름을 쏴서 「없는 것은 없다고 답한다」를 보인다. 이것 없이는 모든 `not readable` 이 계기 고장과 구별되지 않는다.
5. 산출물: `docs/research/ma3-effects/` 옆의 조사 노트. **표제 네 개(`시도한 이름` · `사유` · `대조군` · `실행일`)를 마크다운 표제로 그대로 쓴다** — AC-READBACK-013 의 grep 이 그 문자열을 센다. **양쪽 결과 모두 유효한 종점**(REQ-READBACK-012).

M2 후속 — 발견 경로 (설계 상세는 여기가 소유한다. spec.md 는 「값과 출처가 회신에 실린다」까지만 요구한다):

| 파일 | 델타 | 내용 |
|---|---|---|
| `server/web/presets_api.py` | [MODIFY] | `PresetsDeps` `:57-67` 에 프로퍼티 조회 포트를 더하는 것이 주입 지점 |
| `server/web/presets_api.py` | [MODIFY] | 반환 형상은 `:279-284` 의 반환 딕셔너리에서 확장 — 콘솔 유래 값 필드와 앱 팔레트 필드를 **구별 가능하게** (REQ-READBACK-013) |
| `server/lxseq/preset_mapper.py` | [MODIFY] | `:307-311` 의 `value_match` 제거 경로 |
| `server/tests/test_lxseq_preset_mapper.py` | [MODIFY] | 고정 3건(`:239-241, :443, :445-448`) 갱신 — **라이브 증거와 같은 커밋에서만**(REQ-READBACK-014) |

M2 후속 — 미발견 경로: `_VALUE_MATCH_REASON` `preset_mapper.py:64-68` 문면 강화 + 조사 노트 링크. 고정 3건은 **초록 그대로 남는다.**

### M3 — 재임포트 1회 + 라이브 검증 + 사실 문서 갱신

여기서만 콘솔을 쓴다. 운영자 승인 후, 머지와 **분리된 행위**로.

1. **M3-1 (유일한 콘솔 쓰기 · 운영자 승인 게이트)**: `Import Plugin` 경로(`server/safety/console.py:323` → `:463`)로 1.6.4 재임포트. `acceptance.md` §A 의 라이브 명령은 `--skip-exec` 라 이 쓰기를 포함하지 않는다 — 이 단계가 그 예산 1회를 소비하는 유일한 자리다.
2. `ping` 이 **`1.6.4`** 를 답하는 것으로 배포 확인. main 내용은 증거가 아니다(live-1.6.1/main-1.6.2 전례). 명령: `responder_roundtrip.py --listen-port 9005 --skip-exec --expect-version 1.6.4 --path DataPool`.
3. 실제 Part 객체에 읽기 전용 프로브를 걸어 `SELECTIONDATA`/`DEPENDENCIES` 의 **실제 형상**을 기록(B2 해소).
4. `docs/runbooks/console-channel-facts.md` §4 갱신 — 「테이블 주소」 항목을 실측 형상으로 대체.
5. R2 가 발견 경로였다면 라이브 되읽기 값 vs 변환값 대조까지.

---

## F. 위험과 완화

| 위험 | 완화 |
|---|---|
| 실제 답이 전부 절단되는 직렬화를 배포한다 | M0 에서 구조적 절단을 강제(REQ-READBACK-005). 그래도 86대 선택 테이블은 넘칠 수 있으므로 **절단이 기본 경로**임을 계약에 적는다 |
| 아무도 본 적 없는 형상 위에서 오프라인 테스트가 통과한다 | M3 3번이 실제 형상을 기록하고, 어긋나면 후속 카드 |
| `value_match` 를 증거 없이 뗀다 | 고정 테스트 3건이 트립와이어(REQ-READBACK-014). 라이브 증거와 같은 커밋에서만 갱신 |
| 재임포트가 조용히 실패한다 | `ping` 버전 확인이 유일한 성공 판정(REQ-READBACK-008). `ReloadAllPlugins` 의 `ok:true` 는 증거가 아니다 |
| 미발견 경로를 「읽어 보니 괜찮더라」로 닫는다 | AC-READBACK-013 의 표제 grep 이 4 를 답해야 닫힌다 — 사람의 독해가 아니라 명령이 판정한다 |
| 002 와 같은 파일을 건드려 충돌한다 | 파일 집합이 겹치지 않는다(§D). 002 는 `server/safety/**`·`server/prechk/**`·`server/vwx/**`·`server/paperwork/**`·`ui/**`, 본 SPEC 은 `console/lua/**`·`server/web/presets_api.py`·`server/lxseq/**`. 겹치는 유일한 디렉터리는 `server/tests/` 이며 파일 단위로 갈린다 |

## G. 안티패턴

- `exec: ok` 를 효과의 증거로 인용하는 것.
- 페이징 판독에서 `childCount` 대조 없이 「전부 읽었다」고 쓰는 것.
- 값 프로퍼티를 못 찾은 것을 **실패**로 처리해 R2 를 재시도 루프에 넣는 것 — 측정된 부재는 결과다.
- 조사 노트의 네 표제를 다른 말로 바꿔 쓰는 것 — grep 이 문자열을 센다.
- 팔레트 스와치를 콘솔 판독값 자리에 놓는 것.
- 재임포트를 머지에 묶어 「배포됐다」를 커밋으로 주장하는 것.
- 002 의 범위(`prechk`/`vwx`/`paperwork`/`safety`/`ui`)를 「가는 김에」 손대는 것.

## H. 교차 참조

`spec.md` · `acceptance.md` · `research.md` §R1·§R2 · `.moai/specs/SPEC-COPILOT-READBACK-002/` · `.moai/reports/plan-audit/SPEC-COPILOT-READBACK-001-review-1.md` · `-review-2.md` · `reports/app-fresh-eyes-review-20260903.md` · `docs/runbooks/console-channel-facts.md` · `console/lua/PROTOCOL.md` · `.claude/rules/moai/core/verification-claim-integrity.md`
