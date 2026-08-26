# t110 — 앱 경로의 프리셋·그룹 쓰기가 항상 거절되던 자리

- 카드: t110 (감사 C2)
- 브랜치: `WT-app-approval-port` · 기준 `origin/main` **ca0ac49**
- 범위: **배선 하나.** fail-closed 기본값은 안 건드린다. 승인 UI 는 안 만든다(이미 있다).
- 실기: **0건** (콘솔은 sync 레인이 쓰는 중)

## 1. 주장

`import_lxseq_presets` · `create_arrangement_groups` 는 자기 승인 통로
(`group_approval_port`)를 따로 묻는다 — 게이트가 `Store Preset` · `Store Group` 을
위험으로 분류하지 않기 때문이다. 통로가 없으면 `DenyAllApprovalPort` 로 떨어져
거절한다(fail-closed, 2026-08-25 사고 뒤 설계).

**앱이 그 통로를 한 번도 안 실었다.** `ChatSession` 은 게이트와 **같은**
`ApprovalChannel` 을 이미 들고 있고 자기 UI 에 bind 까지 해 두고서,
`build_toolset(...)` 호출에는 안 넘겼다. 그래서 앱에서는 프리셋 적용이 **항상
declined** 였다 — 이 파이프라인은 하네스에서만 돌았다.

## 2. 증거

### 2.1 착수 1번 측정 — 「앱 쪽 구현체가 있는가」

**있다.** 그래서 갈래는 배선이고, 감독 판단(스키마에서 `apply` 를 내려 광고를 멈춤)은
필요 없다.

| # | 자리 | 관측 |
|---|---|---|
| 1 | `server/safety/approval.py:37` | `class ApprovalPort(Protocol)` · `:45` `DenyAllApprovalPort` |
| 2 | `server/web/approval_bridge.py:81` | `class ApprovalChannel` — "Blocking ApprovalPort/ReviewPort implementation bridged to the UI" |
| 3 | `server/web/serve.py:304` · `:309` | 채널을 **하나** 만들어 게이트에 `approval_port=channel` 로 넘긴다 |
| 4 | `server/web/session.py:3615` · `:3678` · `:3703` | 같은 채널이 `ChatSession` 에 들어와 세션 UI 에 `bind` 된다 |
| 5 | `server/web/session.py:3712` | 그 `build_toolset(...)` 인자 목록에 `group_approval_port` **없음** |
| 6 | `server/orchestrator/tools.py:1889` | `group_approval = group_approval_port or DenyAllApprovalPort()` |

즉 「구현체 부재」가 아니라 **이미 살아 있는 채널을 그 호출에 안 실은 것**이다.

### 2.2 결함 재현 (수정 전)

    .venv/bin/python -m pytest server/tests/test_app_group_approval_wiring.py -q
    -> 3 failed, 2 passed in 4.25s

빨간 셋은 전부 배선 축이다. **fail-closed 축 둘은 처음부터 초록**이었다 — 결함이
「거절 로직이 깨졌다」가 아니라 **「통로를 안 실었다」** 라는 것의 증거다.

### 2.3 수정 (1자리)

`server/web/session.py` 의 `build_toolset(...)` 호출에 `group_approval_port=approval_channel`
한 줄. 새 통로를 만들지 않는다 — 게이트와 같은, UI 에 bind 된 그 채널이어야 사람이
답할 수 있다. `tools.py` 의 fail-closed 기본값은 **무변**이다.

### 2.4 검사 (수정 후)

    .venv/bin/python -m pytest server/tests/test_app_group_approval_wiring.py -q
    -> 5 passed in 0.75s

    .venv/bin/python -m pytest -q
    -> 10435 passed, 12 skipped, 1 warning in 156.30s   (기준선 10430 + 신규 5)

    make lint
    -> 종료코드 0 (출력 없음)

    ruff format --check (수정 2파일)
    -> 2 files already formatted

## 3. 뮤테이션 — 5/5 KILLED, 두 축이 따로 죽는다

복원은 백업 + sha256 대조. 매 회 치환 적용을 먼저 단언했다.

| # | 뮤테이션 | 축 | 판정 |
|---|---|---|---|
| 1 | 배선을 통째로 되돌린다(수정 전 상태) | 배선 | KILLED (3 failed) |
| 2 | `group_approval_port=None` 으로 싣는다 | 배선 | KILLED (3 failed) |
| 3 | 세션 것이 아니라 **새** 채널을 싣는다 | 배선 | KILLED (1 failed) |
| 4 | deny-all 을 명시적으로 싣는다 | 배선 | KILLED (1 failed) |
| 5 | `or DenyAllApprovalPort()` 를 허용으로 뒤집는다 | **fail-closed** | KILLED (1 failed) |

**5번을 내 파일만으로 따로 다시 쐈다** — `test_app_group_approval_wiring.py` 단독에서
`TestFailClosedSurvives::test_no_port_still_declines_and_fires_nothing` 이 죽였다.
기존 `test_lxseq_preset_safety.py` 는 **항상 통로를 주고** 부르므로 `or` 갈래를 못 지난다 —
즉 이 축은 오늘까지 아무도 안 지키고 있었다.

3번이 중요하다: 「무언가 실렸다」로 끝내면 세션 UI 에 bind 안 된 새 채널을 실어도
통과한다. 그러면 사람에게 물어볼 수 없는 통로가 되고, 화면엔 아무것도 안 뜬 채
타임아웃으로 거절된다 — **증상이 지금과 똑같아 구분이 안 된다.**

## 4. 이미 있던 것과의 대조 (짓기 전에 SPEC 을 읽었다)

| SPEC | status | 이 카드와의 관계 |
|---|---|---|
| `SPEC-COPILOT-GROUPGEN-001` | completed | `group_approval_port` 를 **하네스**(`groupgen_e2e.py`)에 배선했다. AC-GROUPGEN-036·040 의 범위는 툴 계층 강제이고 **앱(ChatSession) 배선은 그 AC 에 없다** — 재발견이 아니라 진짜 빈자리다 |
| `SPEC-COPILOT-WRITEGATE-001` | **in-progress** | `spec.md:51` 이 이 통로를 **부채**로 명명한다 — 「게이트가 쓰기를 분류하지 못해 툴 계층에 제2 승인 창구가 생겼다」. `:134` 는 게이트 분류로 **대체·제거**하는 것을 `Store` 축이 열린 뒤로 미룬다 |

## 5. 미검증 (gap)

- **실기 0건.** 앱을 띄워 승인 카드가 화면에 뜨고 사람이 눌러 프리셋이 저장되는 것은
  안 봤다. 잰 것은 **세션이 무엇을 넘기는가**와 **통로 유무에 따른 거절/발화**까지다.
- **UI 쪽 표시는 안 봤다.** 채널은 같은 것이니 승인 카드가 뜰 것으로 보지만, 프리셋
  번들의 `risk_reasons` 가 화면에 어떻게 렌더되는지는 이 카드가 안 물었다.
- **`create_arrangement_groups`(그룹 축)는 같은 인자를 쓰므로 함께 열렸다.** 이 카드의
  검사는 프리셋 툴로 쐈다 — 그룹 툴의 앱 경로는 같은 인자라는 **구조 논증**이지
  따로 쏜 관측이 아니다.

## 6. 잔여 위험

- **부채를 늘리진 않았지만 굳혔다.** WRITEGATE-001 이 제거를 예정한 제2 승인 창구를
  이제 앱도 쓴다. 그 SPEC 이 게이트 분류로 대체할 때 앱 배선도 같이 걷어야 한다 —
  이 파일이 그 자리를 지목한다.
- **채널은 하나이고 세션마다 `session_key` 로 갈린다.** 프리셋 승인이 게이트 승인과
  같은 채널을 공유하므로, 한 세션이 대기 중인 승인을 끊으면(`unbind` → `deny_pending_for`)
  프리셋 승인도 함께 거절된다. fail-closed 방향이라 안전한 쪽이지만, 사용자에게는
  「왜 거절됐는지」가 안 보일 수 있다. 안 쟀다.

## 7. SPEC 소급 대조 (리드 지시 2026-08-26 — 배차서 `spec:` 필드 신설)

리드가 지목한 셋을 읽었다. **결론: 이 배선을 요구하는 REQ 는 없다.** 「REQ 미이행」이
아니라 진짜 빈자리다. 다만 fail-closed 는 새로 논증하지 않고 **인용**한다.

| SPEC | status | 읽은 것 | 이 카드와의 관계 |
|---|---|---|---|
| `WRITEGATE-001` | in-progress | `spec.md:51` · `:134` | 이 통로를 **부채**로 명명하고 게이트 분류로 대체·제거를 `Store` 축 개방 뒤로 미룬다. 배선을 요구하지 **않는다** |
| `UNREQ-001` | implemented | `B.1` · `B.2` · `REQ-UNREQ-007~009` | 대상은 **세션 계층** `_preset_store_commands`(`session.py:2951`) 경로이고, 막는 축은 「지시에 명명되지 않은 대상」이다. `REQ-UNREQ-009` 는 「게이트는 변경하지 않는다 — 응용 층에서만 산다」. **툴 계층 승인 통로는 그 범위 밖** |
| `PRESETGUARD-001` | completed | `REQ-003` · `REQ-016` | `REQ-016` 이 범위를 「세션 계층 동작 · 기존 툴 위에서만」으로 봉쇄한다. **툴 계층 배선은 그 범위 밖** |
| `GROUPGEN-001` | completed | `AC-036` · `AC-040` | 이 통로를 **하네스**에 배선했다(`groupgen_e2e.py`). 앱 배선은 그 AC 에 없다 |

**인용 (새로 논증하지 않는다).** 이 카드가 지킨 fail-closed 는
**`REQ-PRESETGUARD-003`** 이 이미 적은 원리다 — 「**침묵은 동의가 아니며 손실은 복구
불가다**」. 뮤테이션 5번(`or DenyAllApprovalPort()` 뒤집기)이 지키는 것이 정확히 그 문장이다.

**UNREQ-001 B.2 가 그린 지도에 이 카드를 얹으면** 층이 셋이 된다:

| 층 | 덮어쓰기 | 빈 슬롯 신규 생성 |
|---|---|---|
| 게이트 (`Store /overwrite`) | 막음 | 안 막음 |
| 응용 — 세션 계층 (PRESETGUARD-001) | 막음 | 설계상 통과 |
| 툴 계층 (`group_approval_port`) | 물음 | **물음** — 다만 **오늘까지 앱에서는 통로가 없어 항상 거절**이었다 |

세 번째 줄이 이 카드다. UNREQ-001 이 「어느 쪽도 안 덮는다」고 적은 그 자리를 툴
계층은 이미 덮고 있었는데, **앱에서 그 층에 닿을 수가 없었다.**
