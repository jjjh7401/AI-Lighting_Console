# SPEC-COPILOT-AUTOPATCH-001 — 진행 기록 (progress)

> **인용 규율**: 본 SPEC의 `spec.md`·`acceptance.md`는 행 번호로 인용하지 않는다 — 안정 토큰만 쓴다.
> `file:line`은 코드·룰북·`console/lua/PROTOCOL.md`·**다른** SPEC의 아티팩트에만.
> **증거 등급**: `[코드]` · `[문서]` · `[실측]` · `[미확정]`.

## §0 인수인계 — 여기서 시작한다 (**2026-08-06 갱신** · 이전 판은 §0a)

**상태**: **plan-audit `audit-ready` — round10 독립 감사 PASS(0.865 ≥ Tier L 0.85, round9 0.8025
대비 +0.0625)로 v0.1.4가 승인 가능 상태다.** (v0.1.4 = v0.1.3 반자동 모델 amendment +
round7 18건 + round8 13건 + round9 8건 + round10 7건 반영. round6 PASS(1.000)는 v0.1.2에 대한
판정이므로 승계하지 않고, **round10이 v0.1.4를 직접 감사해 PASS했다**.) ·
run-phase 진행 중 ·
M0 종결(5차까지) · **M1·M2·M3·M4·M5 완료** · M6·M7 착수 가능 · M8 재정의 필요.**
테스트 **5,044 passed / 7 skipped**(착수 4,898 → +146, 회귀 0) ·
커밋 **run-phase 15건**(`9f7516c..HEAD` · `ca00bc5..HEAD` 총 19건 — **본 갱신을 담은 커밋을
포함한 계수**다. 이전 판은 자기 커밋을 빼고 세어 갱신 직후부터 1 어긋나 있었다,
round10 감사 N55. §0을 갱신할 때마다 재계산하라) ·
PRESERVE 5경로 0-diff · 콘솔 세션 전 상태로 완전 원복.
**2026-08-06 5차**: §0 미시험 6건 중 **L1·L3·L4·L5 전부 NEGATIVE** ·
**L6은 "명령줄 목적지는 옮겨지고 듣는다"의 양성 대조군을 확보**했다 →
**목적지 조작 처방이 반증**됐다(§E.2 M0 5차). 남은 미시험은 **L2 1건**(사용자 자원 필요).
**2026-08-06 amendment v0.1.4**: 반자동 실행 모델로 전환(§E.2aa, 사용자 승인) +
독립 감사 round7·8·9 지적 39건 + round10 7건 반영(§E.1a 7·8·9·10회차).
**2026-08-06 M4 완료**: Lua 생성기 + 주소 계획, 테스트 +38, AC-013·014·016(§E.2 M4 절).
**2026-08-06 M5 완료**: 실행 전달(사람) · 검증 인계, 테스트 +63, AC-015·017·018·019.
`RecordingExecutionPort` 도달 발화 **0건**을 **사본 대조군 9종**으로 비공허하게 닫았다(§E.2 M5 절).

### 지금 이 SPEC이 막혔던 것 — 무엇에 막혔고 어떻게 우회했나

`spec.md` §A **사전 확정 사실 1**("패치는 Lua `AddFixtures` 전용이며 정확히 2단계 —
`deploy_plugin` → `run_commands([\"Plugin '<이름>'\"])`")이 **실기에서 성립하지 않았다.**
실행 경로 **10가지**(4차까지 9 + 5차 매크로 발화 1)와 그 안에서 시험한 `AddFixtures` **인자 변형 8종**,
별도 생성 기법 **1종**(객체 모델 `Append`)에서 픽스처가 **한 대도 생성되지 않았다**(§E.2 M0 1~5차).

**v0.1.3이 그 벽을 우회했다** — 서버가 실행하지 않고 **사람이 실행하고 서버가 검증**한다.
`REQ-AUTOPATCH-018`을 조정했고, **M4(Lua 생성)·M6(검증 읽기)·M7(툴 배선)은 살아남았으며
M5만 "실행"에서 "실행 안내 + 검증 인계"로 축소**됐다. M8은 사람 실행 단계를 포함하도록
**재정의가 필요**하다(미착수). 상세는 §E.2aa.

**M1·M2·M3·M4는 영향받지 않는다** — 콘솔 쓰기와 무관한 순수 로직·생성 계층이고
테스트 **83건**과 함께 유효하다. M4가 만드는 Lua는 **사람이 실행할 검토용 소스**다.

### [HARD] 다음 담당자가 반드시 알아야 할 인식론적 한계 (**5차로 일부 해소 · 핵심은 여전히 미확정**)

**이 절의 이전 판은 "양성 대조군이 없다"였다. 5차에서 대조군을 얻었으나, 그것은
"명령줄 목적지"에 대한 대조군이고 "플러그인의 목적지"에 대한 대조군이 아니다.**

매크로 명령줄에서 `ChangeDestination`은 **실제로 적용되며**, 뒤따르는 줄은 옮겨진 목적지
— patch fixtures 컨테이너 그 자체 — 를 기준으로 동작한다(짝지은 음성 대조군과 함께
독립 증명: 목적지 미이동 시 같은 명령이 `Illegal object`이거나 무효과).
**그 컨텍스트에서 플러그인을 실행해도 플러그인은 `TempCmdlines Cmdline 1`을 본다.**

```
REFUTED  : "명령줄 목적지를 patch fixtures 레이어로 옮기면 AddFixtures가 성공한다"
           — 처방(remedy)의 반증. 옮겼고, 옮겨진 것을 독립 증명했고, 그래도 0건이다.
CONFIRMED: 플러그인 Lua 실행 컨텍스트는 명령줄 목적지를 물려받지 않으며,
           이 저장소가 접근 가능한 어떤 수단으로도 플러그인의 목적지를 바꿀 수 없다.
UNDETERMINED: "실패 원인이 플러그인의 목적지다"라는 가설 자체.
           플러그인의 목적지가 TempCmdlines가 **아닌** 컨텍스트는 10개 실행 경로 전부에서
           한 번도 만들어지지 않았다 — 즉 가설의 전건이 실현된 적이 없고,
           그 가설은 관측된 0건과 **여전히 양립한다.** 반증된 것이 아니다.
```

**따라서 원인은 미확정이다.** 확정된 것은 **원인이 무엇이든 명령줄 목적지 조작으로는
거기에 도달할 수 없다**는 것이다. 목적지를 조작하는 후속 설계는 **근거가 없다 —
그 방향에 투자하지 마라.** 이것이 실무적으로 필요한 결론의 전부이며,
여기서 "원인은 목적지가 아니다"로 넘어가면 §E.2z가 자기정정한 **같은 과잉주장을 반복**하게 된다.

### 미시험 항목 — 6건 중 5건 종결, **L2만 남았다**

| # | 항목 | 판정 (2026-08-06 5차) |
|---|---|---|
| **L1** | 매크로 2줄(같은 명령줄에서 CD → 플러그인) | **NEGATIVE** — 매크로에서 실행 확인됨(회수 매크로 삭제 후 재생성). 플러그인 목적지 불변 · `nil` · 0건 |
| **L2** | **패치 편집 세션 활성 상태에서 실행** | **미시험 — 유일하게 남음.** OSC 도달 불가(`ASSUMPTION-75` NEGATIVE, 합성 키 입력은 4차에서 위험 판정). **사용자가 편집 세션에 진입해야 한다.** 단 L6이 기대값을 크게 낮춘다 |
| **L3** | `idtype`를 객체 핸들로 | **NEGATIVE** — 이름·인덱스 양쪽. 핸들은 `userdata`로 정상 해석됨(인자 nil이 원인 아님) |
| **L4** | `CreateUndo` 안에서 CD 없이 | **NEGATIVE** |
| **L5** | 룰북 예제 글자그대로 | **NEGATIVE** — `Robin MMX Spot`·`Mode 1` 실재 확인 후 원문 그대로 실행. **G1 REFUTED** |
| **L6** | 양성 대조군 확보 | **부분 ACHIEVED** — "명령줄 목적지는 옮겨지고 듣는다"는 짝지은 대조군으로 확보(→ **목적지 조작 처방 반증**). 단 **"플러그인의 목적지"에 대한 양성 대조군은 여전히 0** — 원인 가설 자체는 미확정(위 [HARD] 절) |
| G6 | (신규) 객체 모델 생성 경로 | **NEGATIVE** — `Fixtures:Append`는 실재 `function`(허구 키 대조군 통과)이나 `nil` 반환 · 0건 |

측정 누계 **실행 경로 10가지 · 인자 변형 8종 · 별도 생성 기법 1종**, 생성 **0건**.
상세·원문 라벨·계수 근거는 §E.2 M0 5차.

### 6건이 전부 실패하면 — 설계 대안 → **v0.1.3으로 채택됨 (2026-08-06 사용자 승인)**

**반자동 모델로의 전환**을 제안한다. 현 SPEC은 "서버가 콘솔에 쓴다"를 전제하나,
제품의 명시적 비목표가 *"라이브 실시간 자율 운영 배제 — 실행 버튼은 항상 사람이 누른다"*
(`.moai/project/product.md` §6)이다.

```
서버:  후보 정리 → FID 배정 → 타입 매칭 → Lua 소스 생성 → 드라이런 표 제시
사람:  검토 → 콘솔에서 실행
서버:  precheck_patch 재조회 → 건별 검증 → 리포트
```

- 앞쪽 절반은 **M1·M2·M3로 이미 완성**되어 있다.
- 뒤쪽 검증은 `precheck_patch` 재사용이라 성립한다(결정 F).
- 막힌 것은 **"서버가 직접 실행" 한 칸뿐**이다.
- 조정 대상은 `REQ-AUTOPATCH-018` 하나이며, **M4(Lua 생성)·M6(검증 읽기)·M7(툴 배선)은 그대로 살아난다.**
  M5만 "실행"에서 "실행 안내 + 검증"으로 축소된다.
- 비가역 쓰기를 사람이 통제한다는 **SPEC 원래 정신에 오히려 더 부합**한다.

이 전환은 plan-phase amendment이며 **재감사 대상**이다. 오케스트레이터가 임의로 승격하지 않는다.
→ 2026-08-06 사용자가 승인해 `v0.1.3`으로 반영되고, 독립 감사 round7(FAIL 0.7375)·round8(FAIL
0.805) 지적 31건을 반영해 **`v0.1.4`**가 되었다(§E.2aa · §E.1a 7·8회차).
round9도 FAIL(0.8025)로 8건을 지적해 반영했고, **round10이 v0.1.4를 PASS(0.865)** 했다
(§E.1a 9·10회차). **현재 `audit-ready` — Implementation Kickoff Approval → M4 착수 단계다.**

### 이 SPEC이 1단계와 근본적으로 다른 점

**콘솔에 쓴다.** 1단계는 읽고 비교만 했다.
패치는 픽스처를 **생성**하고, 이 앱에는 실행 취소·백업 복원 경로가 **없다**.
그래서 요구사항의 절반 이상이 기능이 아니라 **되돌릴 수 없는 쓰기를 사람이 통제하게 만드는 장치**다.
— 그리고 그 장치 중 하나(REQ-AUTOPATCH-023 검증 읽기)가 이번 M0에서 **실제로 값을 했다.**
플러그인이 `OK`를 반환하고도 0건을 만든 상황을 그 요구가 거짓 성공으로부터 막았다.

### 읽는 순서

| # | 무엇을 | 어디서 |
|---|---|---|
| 1 | 무엇을 만들기로 했나 | `spec.md` — REQ 26건 · §C `의존 범위 한정` · §C ASSUMPTION **71~76** · §C PRESERVE · §D Out of Scope 6건 |
| 2 | M0가 무엇을 확정했나 | **`progress.md` §E.2 M0 1~5차** — 전제 **6건** 판정과 **실행 경로 10가지 · 인자 변형 8종** 측정 전문. **`plan.md` §A.2의 "M0가 먼저"는 이미 이행됐다** |
| 2a | **왜 설계가 바뀌었나** | **`progress.md` §E.2aa** — v0.1.3 반자동 실행 모델 amendment |
| 3 | 부정이면 어떻게 되나 | `plan.md` §A.3 — 가정 **6건**의 부정 처리표. 부정은 실패가 아니라 **기능 축소**다 |
| 4 | 무엇을 통과해야 하나 | `acceptance.md` — AC 27건 · §C.0 역추적표(REQ 26/26) · §C.0a 마일스톤 배정 · §F DoD |
| 5 | 어떻게 만들 것인가 | `design.md` — §3 흐름도 · §5 설계 슬롯 5건 · §6.3 비공허성 대조군 **10건** · §7 안티패턴 10건 |
| 6 | 근거는 무엇인가 | `research.md` — 패치 기법(**룰북 주장 4건은 반증됨**) · FID 난제 · 타입 핸들 · 비가역성 · 1단계 상속 |

### 함정 11건 — 먼저 읽어라 (2026-08-06: 1번 재정정 · 7·8번 신설 · **9·10·11번 신설(5차)**)

1. **~~`ChangeDestination`을 어디에서도 보내지 마라~~ → [재정정 · 5차]** 룰북은 "CD를 보내면 패치가
   `nil`을 반환한다"고 적었으나(`30_plugin_patterns.md:20-29`), **CD를 보내든 안 보내든 결과가 같다**.
   5차에서 **양성 대조군까지 확보**했다 — 매크로 명령줄의 CD는 **실제로 적용되고 듣지만**
   (목적지 미이동 시 같은 명령은 `Illegal object`/무효과) 플러그인 Lua는 그 목적지를
   **물려받지 않는다**. 생성 산출물의 CD 금지(REQ-AUTOPATCH-017)는 **그대로 유효**하나,
   "CD가 실패 원인"이라는 인과 설명은 **반증됐다**. 단 **"원인이 목적지가 아니다"까지 가지는 마라** —
   플러그인의 목적지를 바꾼 컨텍스트는 한 번도 만들지 못했다(위 [HARD] 절). 실무 결론은
   **목적지 조작 방향에 투자하지 마라**는 것이다(§E.2 M0 5차).
2. **슬롯은 FID가 아니다.** 슬롯을 FID로 쓰면 **MA3가 조용히 받아들이고 엉뚱한 픽스처를 덮는다**
   (`31_choreography_patterns.md:203-209`). **단 FID 자체는 읽힌다** — `Patch/Stages/1/Fixtures/<slot>`의
   `FID` 프로퍼티(2026-08-06 실측, `ASSUMPTION-71` GO). `server/prechk/inventory.py:57`의
   화이트리스트가 좁은 것과는 별개다(그쪽은 PRESERVE라 확장하지 않는다).
3. **`FixtureType`·`Mode`는 표시 문자열이다.** 거기서 채널 수를 파싱하지 마라 —
   `ASSUMPTION-27`이 이미 반증했다(`server/prechk/patch.py:14-22`). 실측 확인: 픽스처의 `Mode`가
   `"2 Mode 2"` 형태로 온다 — 파싱 유혹이 실재한다.
4. **플러그인이 오류 없이 끝난 것은 성공이 아니다.** `AddFixtures`는 실패 시 `nil`을 반환할 뿐이다.
   **검증 읽기가 성공의 유일한 근거다**(REQ-AUTOPATCH-023). **2026-08-06 실물 재현**: `exec`가 `OK`를
   반환하고 픽스처는 0건 생성됐다.
5. **~~`run_commands` 배열 길이는 1이다~~ → [폐기 · v0.1.3]** 그 요구는 REQ-AUTOPATCH-018 조정으로
   **폐기됐다**(AC-AUTOPATCH-015④ · `design.md` §7 안티패턴 2) — 서버는 플러그인 실행을 발화하지
   않는다. 남는 규율은 **콘솔로 나가는 문장은 `run_commands` → `bundle_gate.screen()` 단일 통로**
   (REQ-AUTOPATCH-021)이며, 이름을 인용할 때는 **작은따옴표**를 쓴다(큰따옴표는
   `server/bridge/protocol.py:109`가 거부).
6. **역산된 주소로 패치할 수 있다.** 1단계가 `absolute_back_calculated` 등급을 붙여 넘긴다.
   금지하지 않되 **승인 화면에 등급과 전제를 노출**해야 한다(design.md §5 슬롯 D).
7. **[신설] `DMXChannels` 개수는 DMX 점유폭이 아니다.** 실측 반증: `Robin LEDBeam 350` Mode 2의
   `DMXChannels` childCount는 **14**인데 실제 주소 stride는 **16**이다. 14를 폭으로 쓰면 픽스처마다
   2채널씩 겹친다. `DMXFootprint` 프로퍼티는 존재하나 responder 1.6.1이 `table: 0x…`로만 반환한다
   (§E.2 M0 1차, `ASSUMPTION-72` GO(한정) → 폭 검증 descope).
8. **[신설] `Patch()`는 `ShowData.Patch`가 아니라 `ShowData.LivePatch`다.**
   `ShowData/Patch`는 childCount **0**, `ShowData/LivePatch`가 **14**로 픽스처를 담고 있다
   (2026-08-06 실측). MA3에 편집 버퍼와 라이브 패치가 분리되어 있을 가능성이 있으며 이는
   §0 미시험 항목 **L2**의 근거다.
9. **[신설 · 5차] `deploy` 동사로는 이 빌드에 플러그인 소스가 써지지 않는다.**
   `cannot confirm plugin source write`로 실패하면서 **플러그인 객체는 생성되고 소스는 빈 상태**가
   된다 — 그것을 실행하면 `exec`가 **`OK`를 반환하고 아무 일도 일어나지 않는다**(함정 4번의 변종).
   **라이브러리 파일 + `Import Plugin '<파일명>'`이 유일한 배포 경로**다. XML `<Block>`은 base64
   **1368자(원본 1026바이트)** 상한이고 `FileContent Size`가 블록 수다 — 초과분을 단일 블록에 넣으면
   **오류 없이 실행되지 않는다**. OSC `deploy` 페이로드 자체도 인코딩 후 약 **1950자**에서 잘린다.
10. **[신설 · 5차] 플러그인 안의 `Cmd()`는 큐에 쌓이며 플러그인이 중단되면 폐기된다.**
   그래서 여러 시도를 한 플러그인에 넣으면 **아무 출력도 남지 않는다** — "실행 안 됨"으로 오독하기
   쉽다. **시도 1건 = 플러그인 1개**로 쪼개라. 즉시 반영이 필요한 관측 기록은 **객체 모델 대입**
   (`....name = "..."`)을 써라 — 큐를 타지 않아 중단에도 살아남는다.
11. **[신설 · 5차] 매크로 줄은 `Store Macro <id>.<line>`으로 먼저 만들어야 한다.**
   안 만들고 `Set Macro <id>.<line> Property 'Command'`를 보내면 **`Illegal object`**. 룰북
   `00_grammar.md:80-84`가 빠뜨린 단계다. 또 매크로 줄 안에서는 **중첩 인용이 불가**하므로
   CD 인자는 인용부호 없는 `ShowData.LivePatch.Stages.1.Fixtures` 형식을, 플러그인 호출은
   **숫자 슬롯**(`Plugin 29`)을 써야 한다.

### 기계 확인 커맨드

```bash
W=/Users/studiox/orca/workspaces/AI-Lighting_Console/spec-vwx-001
git -C "$W" rev-parse --abbrev-ref HEAD   # feature/SPEC-COPILOT-VWX-001 (1단계 위에 스택)
uv run pytest server/tests -q             # 현재 기준선: 5044 passed / 7 skipped (착수 4898)
uv run ruff check        server/vwx server/tests/test_autopatch_*.py
uv run ruff format --check server/vwx server/tests/test_autopatch_*.py   # [필수] check만으로는 부족
git -C "$W" diff --stat ca00bc5..HEAD -- console/lua server/safety server/prechk server/paperwork server/looks
```

**라이브 콘솔 프로브**(onPC 기동 상태에서):

```bash
uv run python -m server.tools.responder_roundtrip \
  --host 127.0.0.1 --port 8000 --listen-port 9005 --skip-exec --wait 4
.venv/bin/python tools/console_probe.py --listen-port 9005 "state:Patch/Stages/1/Fixtures"
```

세션 값: `console_host=127.0.0.1` · `console_port=8000` · `receive_port=9005` · `osc_slot=2` ·
live responder **1.6.1**(저장소 `console/lua`는 1.5.0 — **콘솔 쪽이 최신이니 덮어쓰지 마라**).

### 다음 담당자가 먼저 할 것 (**2026-08-06 v0.1.4 기준으로 갱신**)

1. **L1·L3·L4·L5·L6은 이미 측정됐다 — 다시 돌리지 마라.** §E.2 M0 5차에 원문 라벨까지 있다.
2. **반자동 모델 전환도, 그 재감사도, M4·M5도 이미 끝났다 — 되돌리거나 다시 제안하지 마라.**
   2026-08-06 사용자 승인으로 `v0.1.3` → round7·8·9 지적 39건 + round10 7건 반영 → **`v0.1.4`**,
   **round10 독립 감사 PASS(0.865)** 로 `plan_status: audit-ready`(§E.2aa · §E.1a 7·8·9·10회차).
   **M4(Lua 생성기 + 주소 계획, +38)·M5(실행 전달 · 검증 인계, +63)도 완료**됐다
   (§E.2 M4·M5 절). **다음 코드 마일스톤은 `M6`**(멱등 · 검증 읽기, AC-020·021·022),
   이어 M7. **M8은 사람 실행 단계를 포함하도록 재정의가 필요**하다.
2a. **M4가 남긴 계약 3건은 M5에서 지켜졌다 — 되돌리지 마라**:
   ① `luagen.render_addfixtures_plugin(entries)`가 전달물의 본체다 —
      `LuaPatchEntry(console_type, console_mode, fid, name, universe, address)` 6필드뿐이고
      **자유 Lua 삽입 지점이 없다**(그런 파라미터를 추가하면 AC-014③(b) 테스트가 깨진다).
   ② 목적지 토큰을 담은 이름은 `LuaGenerationError`로 **거부**된다 —
      `apply.build_patch_handoff`이 그것을 잡아 `lua_generation_refused`로 제외한다.
   ③ `patchplan.plan_addresses(targets, footprints=..., occupied=...)`의 `footprints`는
      **1단계 도면이 준 폭**이다. 콘솔의 `DMXChannels` 개수를 넣지 마라 — 그것은 폭이 아니다
      (실측 14 vs stride 16). 폭을 모르면 `footprint_unknown`으로 제외된다.
2b. **M6·M7을 쓸 때 M5가 남긴 계약 4건을 지켜라**:
   ① `apply.build_patch_handoff(targets, address_plan=, resolutions=, names=, dry_run=True)`가
      전달 진입점이다 — 파라미터 **5개가 전부**이고, 여기에 인자를 더하면
      AC-017②(리뷰 우회 인자 0건) 테스트가 깨진다. **실행 포트·배포 파이프라인을 넘기지 마라.**
   ② **드라이런과 전달의 `lua_source`는 동일해야 한다**(테스트가 직접 대조한다).
      두 모드를 가르는 것은 `procedure`·`next_step`뿐이며, 그 경계선은 `delivered = not dry_run`
      **한 줄**이다 — AC-019④의 승격 대조군이 그 줄을 문자열로 집는다.
   ③ **`server/vwx/` 어느 모듈도 `server.bridge`·`pythonosc`를 import하지 마라.**
      M6의 검증 읽기도 예외가 아니다 — 콘솔 읽기는 포트 프로토콜을 인자로 받아서 하고
      (`patchplan.FidPropertyPort`·`typemap.LibraryPort` 선례), 그 표면을 import하지 않는다.
      `test_autopatch_execute.py`의 스캐너가 `server/vwx/*.py` **전수**를 돈다.
   ④ 제외 사유는 `verdicts.TARGET_EXCLUSION_REASON`에 **등재된 코드로만** 보고한다.
      **거부된 입력을 사유 문구에 되싣지 마라** — 이름이 목적지 토큰을 담고 있으면
      AC-014① 산출물 스캐너가 거짓 양성을 내 게이트가 강제력을 잃는다(M5에서 실제로 걸렸다).
3. **L2를 돌리려면 사용자가 패치 편집 세션에 진입해야 한다.** 자동화로 대체 불가.
4. **배포는 `deploy` 동사로 하지 마라 — 이 빌드에서 소스가 써지지 않는다**
   (`cannot confirm plugin source write`, 객체만 생기고 소스는 빈 상태로 조용히 실행됨).
   **라이브러리 파일 + `Import Plugin '<파일명>'`이 유일한 경로**이며, XML `<Block>`은
   base64 **1368자(원본 1026바이트)** 단위로 쪼개고 `FileContent Size`에 블록 수를 적어야 한다.
   초과분을 단일 블록에 넣으면 **오류 없이 실행되지 않는다**(§E.2 M0 5차 방법론 정정 2).
5. **플러그인 안의 `Cmd()`는 큐에 쌓이고 플러그인이 중단되면 폐기된다.** 그래서 시도를
   여러 개 넣은 플러그인은 **아무 출력도 남기지 않는다**. **시도 1건 = 플러그인 1개**로 쪼개라
   (5차에서 7건 배터리는 무출력, 1건씩 분리하니 7건 전부 완주).
6. 회수 채널은 **매크로 라벨**을 쓴다 — `Cmd("Store Macro <id>")` + `Cmd("Label Macro <id> <text>")`,
   **비영문숫자를 전부 `X`로 치환**하면 인용 문제가 사라진다. 즉시 반영이 필요하면
   **객체 모델 대입**(`....name = "..."`)을 쓴다 — 큐를 타지 않아 중단에도 살아남는다.
   `SendOSCMessage`(G4)는 5차에서 **아무 것도 수신되지 않았다**.
7. 매크로 줄은 **`Store Macro <id>.<line>`으로 먼저 만들어야** `Set Macro <id>.<line> Property
   'Command'`가 듣는다(안 만들면 `Illegal object`). 룰북 `00_grammar.md:80-84`가 빠뜨린 단계다.
   매크로 줄 안에서는 **중첩 인용이 불가**하므로 CD 인자는 인용부호 없는 형식
   `ShowData.LivePatch.Stages.1.Fixtures`를 쓰고, 플러그인은 **숫자 슬롯**(`Plugin 29`)으로 부른다.
8. **테스트 쇼파일은 확보되어 있다** — `NewShow_2026.07.15_05.44.02UTC`,
   사용자가 2026-08-06에 테스트용으로 확인함(§E.2 M0 2차). 픽스처 39대 · FID 1~39 · 유니버스 1~3.
   **슬롯≠FID 조건을 이미 만족**하므로 `ASSUMPTION-71` 재측정은 불필요하다.
9. 프로브 작성 시 **플러그인 재임포트 캐싱 함정**에 주의 — 같은 이름으로 재임포트하면 소스가
   갱신되지 않는다(`console/lua/README.md` §2.1). 매번 새 이름을 쓰거나 슬롯을 지우고 임포트하라.

---

## Plan-phase log

### v0.1.0 — plan-phase 아티팩트 6종 작성 (2026-08-05)

착수 SHA **`ca00bc5c853bfe5d9391290f1b9db263610b4bfa`**(1단계 v0.1.7 완료 시점),
착수 baseline **4,898 passed · 7 skipped · 1 warning · 92.28s** — **직접 실측, 이월 인용 아님.**

작성 방식: **오케스트레이터 직접 작성.** 1단계 run-phase에서 dispatch 왕복이
코디네이터 재검증 → 지시문 번역 → 워커 해석 → 재검증의 **번역 왕복 2회**를 만들어 3라운드를
되돌려보낸 이력이 있다. 작성은 직접 하고 **감사만 분리**해 독립성을 올린다(작성자 ≠ 감사자).

| 아티팩트 | 내용 | 라인 수 |
|---|---|---|
| `spec.md` | REQ 26건 · ASSUMPTION 71~75 · Out of Scope 6개 H3 · PRESERVE 5경로 · `depends_on` | v0.1.1 |
| `plan.md` | 마일스톤 M0~M8 · 결정 A~G(미결 0) · 라이브 2회 · 테스트 골격 · §G Mode 권고 | 192 |
| `acceptance.md` | AC 27건 · §C.0 역추적표(REQ 26/26) · §C.0a 배정 합 27 · §F DoD | v0.1.1 |
| `design.md` | 변경 표면 · 흐름 · 위험 7건 · 설계 슬롯 5건(전부 종결) · 비공허성 8건 · 안티패턴 10건 | 216 |
| `research.md` | 증거 등급별 조사 8절 · 미확정 5건을 ASSUMPTION으로 승격 | 202 |
| `progress.md` | 본 문서 | 158 |

**합 1,476줄** — 커밋 시점 실측(`wc -l`).

---

## §E.1 Plan-phase Audit-Ready Signal

> **[v0.1.4 amendment · 2026-08-06]** 아래 round6 PASS(1.000)는 **v0.1.2에 대한 판정**이다.
> 반자동 실행 모델 amendment(§E.2aa)가 REQ-AUTOPATCH-018·020·024와 AC-015·017·019·020·022·001,
> M4/M5 경계를 건드렸으므로 **그 판정을 승계하지 않는다.** 현재 상태는
> round7(FAIL 0.7375)·round8(FAIL 0.805)·round9(FAIL 0.8025) 지적 39건 + round10 지적 7건을
> 전량 반영한 v0.1.4에 대해 **독립 round10이 PASS(0.865)했다**(§E.1a 7·8·9·10회차).
> 따라서 현재 상태는 **`audit-ready`** 이며, 이 신호는 **round6이 아니라 round10에 근거한다**.

**상태: plan-audit 6회차(재시도 상한 3회차 이후 독립 위임 재확인) PASS(1.000 ≥ Tier L 0.85, round5
0.923보다 +0.077 — 개선, 역행 아님).**
**현재 상태는 `audit-ready` — v0.1.4에 대한 독립 round10 감사가 PASS(0.865 ≥ 0.85)했다.**
이 신호는 **round10에 근거하며 round6 PASS를 승계한 것이 아니다**
(round10 감사 N52 교정: 이전 판은 이 자리에 round6의 "audit-ready 유지"를 적어 당시 yaml의
`plan_status`와 정면으로 어긋났다). 아래는 round6 당시의 서술이며 **v0.1.2 시점 기록**이다.
감사 통과 전에는 신호를 쓰지 않았다. 이는 **의도된 규율**이다 — 감사가 FAIL이면 신호가 거짓이 되기
때문이며, 실제로 1회차는 FAIL(0.80)이었다. (이 브랜치의 `.moai/specs/` 에는 같은 규율을 쓴 선행
SPEC이 없다. 유사 선례가 미머지 형제 브랜치에 존재하나 여기서 인용 가능한 자산이 아니다.)
2회차 이후 N1~N4 반영으로 **v0.1.2**가 되었으며, 그 반영은 신규 요구·AC를 만들지 않고
기존 요구를 인터페이스 계약과 일치시킨 것이라 감사 판정을 무효화하지 않는다(§E.1a 2회차 반영 절).
**3회차가 v0.1.2를 독립 재검증해 PASS(0.857, round2와 동일 점수 — 역행 아님)를 재확인했다.**
3회차는 N1~N4 CLOSED를 재확인하는 한편 신규 지적 2건(N5 major · N6 minor)을 발견했다 — 둘 다
PASS를 막지 않는 경량 후속 항목이다(§E.1a 3회차 절 참조). N5(design.md §6.2 표 행 손실)는
Implementation Kickoff Approval 전 경량 패치를 권고하나, audit-ready 신호를 철회할 사유는 아니다
(요구·AC 수 불변, must-pass 전부 PASS/N/A 유지).
**4회차(재시도 상한 이후 오케스트레이터 재량 위임)가 작성자의 N5·N6 자기수정을 독립 재검증해
PASS(0.923, round3보다 +0.066 — 개선, 역행 아님)를 확인했다.** N5·N6은 원문 대조로 **genuinely
CLOSED** 확인됨(§E.1a 4회차 절 참조). 4회차는 이번 회차의 전수 스윕 지시(`design.md` §6.2 27개
AC 전부를 acceptance.md 자체 인용과 대조)로 **신규 지적 3건**(N7 major · N8·N9 minor)을 발견했다 —
전부 `design.md` §6.2(테스트 파일 포인터 표, 추적성 SSOT인 §C.0/§C.0a와는 별개)에 국한되며,
PASS를 막지 않는다. N7(AC-AUTOPATCH-015가 잘못된 테스트 파일 행에 배정됨)은 §6.2 표가 4회차 연속
동일 위치에서 결함을 낸다는 **공정 관찰**(§E.1a 4회차 절 "공정 관찰" 참조)의 근거이며, Implementation
Kickoff Approval 전 경량 패치를 권고하나 audit-ready 신호를 철회할 사유는 아니다.
**5회차가 N7 자기수정을 독립 재검증해 PASS(0.923, round4와 동일 — 횡보)를 확인했다.** N7은 여섯
AC(013~019) 전부 대조로 **genuinely CLOSED** 확인됨(§E.1a 5회차 절 참조). N8·N9는 작성자의 신고대로
미반영 상태로 정확히 남아 있음을 원문 대조로 확인했다. 5회차는 전수 스윕(27개 AC 전부를
acceptance.md 자체 인용과 대조)에서 **신규 지적 1건**(N10 minor — AC-004 이중 인용의 두 번째 파일
누락, round4가 "무결"로 인증했던 배치 안에서 발견)을 찾았다 — PASS를 막지 않으며, §6.2 표가
5회차 연속 동일 결함 클래스를 낸다는 공정 관찰을 심화한다(§E.1a 5회차 절 "공정 관찰" 참조,
구조적 대안 — §6.2 삭제 — 을 자문으로 제시).
**6회차(재시도 상한 이후 오케스트레이터 재량 위임)가 작성자의 §6.2 폐지 자기수정(N8·N9·N10 구조적
해소 주장)을 독립 재검증해 PASS(1.000, round5보다 +0.077 — 개선, 역행 아님)를 확인했다.** N8·N9·N10
전부 원문 대조로 **genuinely CLOSED** 확인됨(§E.1a 6회차 절 참조) — §6.2 표가 진짜로 삭제되었고,
6개 아티팩트 전체에 §6.2를 권위 출처로 참조하는 곳이 0건이며, N8·N10의 실제 대상이었던 AC-004·
AC-025 자신의 검증방법 필드가 이미 두 파일 모두 완전히 명시하고 있었음을 확인했다(삭제가 정보를
옮긴 게 아니라 부정확한 사본만 제거). round1 이후 처음으로 **4개 축 전부 잔여 결함 0건**이다.

기록된 값 (**v0.1.4 기준으로 갱신** — round7·round8·round9 반영 후. round6 PASS 값은 v0.1.2 시점 기록):

```yaml
plan_status: audit-ready   # round10 독립 감사 PASS(0.865 ≥ Tier L 0.85)로 v0.1.4가 audit-ready. round7 FAIL(0.7375)·round8 FAIL(0.805)·round9 FAIL(0.8025) 지적 39건 + round10 지적 7건 전량 반영(§E.1a 7·8·9·10회차). round6 PASS(1.000)는 v0.1.2에 대한 판정이므로 승계하지 않는다 — 이 신호는 round10에 근거한다
plan_complete_at: "2026-08-06 — v0.1.4에 대한 round10 독립 감사 PASS (0.865 ≥ Tier L 0.85, round9 0.8025 대비 +0.0625 개선). round6 PASS(1.000)는 v0.1.2 기준의 이전 판정"
spec_version: "0.1.4"     # v0.1.3 반자동 실행 모델 amendment + round7 18건 + round8 13건 + round9 8건 + round10 7건 반영. REQ 26 · AC 27 수 불변, REQ-018/020/024 · AC-014/015/017/019/020/022/001 내용 조정, M4↔M5 경계 이동
base_sha: ca00bc5c853bfe5d9391290f1b9db263610b4bfa
baseline_measured: "uv run pytest server/tests -q → 4898 passed, 7 skipped, 1 warning in 92.28s"
artifacts: [spec.md, plan.md, acceptance.md, design.md, research.md, progress.md]
requirements: 26          # REQ-AUTOPATCH-001~026 (v0.1.1에서 026 신설)
acceptance_criteria: 27   # AC-AUTOPATCH-001~027 (v0.1.1에서 027 신설)
milestones: 9             # M0~M8. M0·M8만 cycle_type=none (라이브 측정)
assumptions_open: 0       # ASSUMPTION-71~76 전부 판정 완료. 71 GO · 72 GO(한정) · 73·74 INCONCLUSIVE · 75 NEGATIVE · 76 NEGATIVE(v0.1.3 신설·즉시 판정)
live_sessions_planned: 2  # M0 전제 측정 · M8 종단 검증
decisions_closed: 7       # plan.md §A.4 결정 A~G
decisions_open: 0
design_slots_closed: 5    # design.md §5 슬롯 A~E
design_slots_open: 0
clarification_markers: 0
machine_gates:
  req_to_ac_coverage: "26/26 — acceptance.md 역추적표 REQ 행 26, 커버 누락 0"
  ac_milestone_assignment: "27 — M0 1 · M1 3 · M2 5 · M3 4 · M4 3 · M5 4 · M6 3 · M7 3 · M8 1. 중복 0 · 누락 0 (v0.1.3: AC-015가 M4→M5)"
  ac_absent_from_traceability_table: "5 — AC-AUTOPATCH-001(전제 게이트) · AC-AUTOPATCH-023(툴 등록) · AC-AUTOPATCH-024(PRESERVE) · AC-AUTOPATCH-025(1단계 회귀) · AC-AUTOPATCH-026(라이브 통합). acceptance.md가 의도로 명시"
  out_of_scope_h3_headings: "6"
  nonvacuity_controls_required: 10  # design.md §6.3 (v0.1.4 round7 반영에서 8 → 10: 패치 실행 발화 0건 · 별도 배포 호출 0건 신설)
known_gaps:
  - "[CLOSED · M0 1~5차] ASSUMPTION-71~76 전부 판정 완료 — 71 GO · 72 GO(한정) · 73·74 INCONCLUSIVE(선행조건 미성립) · 75 NEGATIVE · 76 NEGATIVE. M2·M3 설계 확정, M6는 검증 읽기 유지."
  - "[CLOSED · M0 2차] 테스트 쇼파일 확보·사용자 확인 완료 — NewShow_2026.07.15_05.44.02UTC(픽스처 39 · FID 1~39 · U1~3, 슬롯≠FID 만족)."
  - "[핵심 잔여] AddFixtures가 이 빌드에서 픽스처를 만들지 못한다(실행 경로 10가지 · 인자 변형 8종 · 별도 생성 기법 1종, 전부 0건). **원인은 미확정**이며, 확정된 것은 '명령줄 목적지 조작으로는 거기에 도달할 수 없다'는 처방 차원의 반증이다(양성 대조군의 대상은 명령줄 목적지이고, 플러그인 목적지에 대한 대조군은 0 — round7 N11 교정). 이 때문에 v0.1.3이 반자동 실행 모델로 전환했다."
  - "CID/다른 idtype 축(research.md §3.3 경로 c)은 조사 부족으로 이번 범위 밖이다."
  - "[v0.1.3] L2(패치 편집 세션 활성 상태에서 AddFixtures 실행)만 미시험으로 남는다 — 사용자 자원 필요. 긍정으로 나오면 REQ-AUTOPATCH-018을 되돌릴 수 있다(§E.2aa 가역성 기록)."
  - "[v0.1.3] M8(라이브 종단)이 사람 실행 단계를 포함하는 형태로 재정의되어야 한다 — 미착수."
  - "[v0.1.3] responder deploy 동사가 이 빌드에서 소스를 쓰지 못한다(spec.md §A 사실 8). 서버 자동 배포 경로는 G3(별건 SPEC)에 의존한다."
  # round2 N1~N4는 v0.1.2에서 전량 CLOSED — §E.1a "2회차 지적 반영" 절 참조. 잔여 gap 아님.
  # round3 N5·N6은 round4가 원문 대조로 독립 재검증해 CLOSED 확정(§E.1a 4회차 절). 잔여 gap 아님.
  - "[CLOSED · round4 독립 검증] round3 N5(major) — design.md §6.2 표에 `002 · 003 · 004 |
    test_autopatch_candidates.py` 행 복원 확인(누락 지점에 정확히 삽입, 27/27 행 커버로 복귀 —
    전수 재열거로 재확인, 복원 편집 자체의 부수 손상 없음)."
  - "[CLOSED · round4 독립 검증] round3 N6(minor) — acceptance.md:3·plan.md:3 상태줄이
    `v0.1.2, 2026-08-06`로 갱신되고 acceptance.md:3의 'AC 27건 계획'이 §C.0a '합 27'과 일치함을
    직접 대조로 확인. 6개 아티팩트 전체 26/27건 언급 광역 재스캔에서 잔여 staleness 0건."
  - "[CLOSED · round5 독립 검증] round4 N7(major) — design.md §6.2에서 AC-AUTOPATCH-015를
    `013·014·016 | test_autopatch_lua.py` 행에서 분리해 `015·017·018·019 |
    test_autopatch_execute.py` 행으로 재배정. AC-013·014·015·016·017·018·019 여섯 건 전부를
    acceptance.md 자체 검증방법과 개별 대조해 확인, git diff로 단일 훅·부수 손상 없음 확인.
    잔여 gap 아님."
  - "[CLOSED · round6 독립 검증] round4 N8(minor) — design.md §6.2 폐지로 `024·025` 행 자체가
    소멸. AC-025 자신의 검증방법(acceptance.md:427-429)이 test_vwx_*.py 전수 + 골든스냅샷
    test_autopatch_contract.py를 이미 완전히 명시하고 있었음을 원문 대조로 확인 — 삭제가
    정보를 옮긴 게 아니라 부정확한 사본만 제거했다. 잔여 gap 아님."
  - "[CLOSED · round6 독립 검증] round4 N9(minor) — design.md:3 상태줄 접미사가
    '1~5회차 지적 반영 · §6.2 폐지'로 갱신됨을 원문 대조로 확인. 잔여 gap 아님."
  - "[CLOSED · round6 독립 검증] round5 N10(minor) — design.md §6.2 폐지로 `002·003·004` 행 자체가
    소멸. AC-004 자신의 검증방법(acceptance.md:159)이 test_autopatch_candidates.py ·
    test_autopatch_execute.py 두 파일을 이미 완전히 명시하고 있었음을 원문 대조로 확인. 잔여
    gap 아님."
  - "[CLOSED · round6 독립 검증] §6.2 폐지가 다른 참조를 깨뜨리지 않음 — 6개 아티팩트 전체를
    '§6.2'·'design.md §6' 패턴으로 광역 재스캔해 §6.2를 권위 출처로 참조하는 곳 0건을 확인
    (매치는 전부 다른 절 참조이거나 progress.md 자체 감사기록). plan.md §E 테스트 골격이
    §6.2와 독립적으로 이미 파일→주제 매핑을 제공하고 있어 온보딩 가독성도 유지됨. 잔여
    gap 아님 — round1 이후 최초로 4개 축 전부 잔여 결함 0건."
next: "**M6 착수**(멱등 · 검증 읽기, AC-020·021·022). **M5 완료**(실행 전달·검증 인계, +63 테스트, §E.2 M5 절) — `RecordingExecutionPort` 도달 발화 0건을 사본 대조군 9종으로 비공허하게 닫았고, 드라이런·전달 두 모드 모두 쓰기 0건이다. **M4 완료**(Lua 생성기 + 주소 계획, +38 테스트, §E.2 M4 절). round10 독립 감사가 v0.1.4를 **PASS(0.865)** 했다 — plan-phase 관점의 착수 전제는 해소됐다. 지적 누계 N1~N55 **전량 반영**(round1~6 N1~N10 CLOSED 확정 · round7 N11~N28 · round8 N29~N41 · round9 N42~N49 · round10 N50~N55). M1~M5가 완료 상태이므로 다음 코드 마일스톤은 **M6(멱등 · 검증 읽기)**이고, 이어 **M7(툴 배선 · 회귀 · PRESERVE)**이다. M7은 `PatchPlan.to_dict()`의 `deferred_to_m2·m3·m4` 마커 3종을 함께 해소해야 한다(§E.2 M5 절 미검증 잔여). **M8은 사람 실행 단계를 포함하도록 재정의가 필요**하다(미착수). 남은 사용자 접점 2건: ① **L2 측정**(패치 편집 세션 진입 — 선택. 긍정이면 REQ-AUTOPATCH-018을 v0.1.2 형태로 복원 가능) · ② M8 라이브 종단 세션 일정. 착수 전 `spec.md` §A 사실 7·8과 §0 함정 9·10·11을 읽어라 — 배포·회수 경로가 그 위에 서 있다. M5가 남긴 계약 4건은 §0 항목 2b."
```

---

## §E.1a Plan-audit 결과

### 1회차 (round1) — 2026-08-06 — plan-auditor 독립 감사

**판정: FAIL** — Overall Score **0.80**(조화평균) < Tier L 임계 **0.85**.
전문: `.moai/reports/plan-audit/SPEC-COPILOT-AUTOPATCH-001-round1.md`

**Must-Pass**: MP-1~MP-7 **전부 기계적 PASS/N/A**(MP-4 N/A: 단일 언어 프로젝트).
다만 MP-5(D7)는 좁은 검증구문(retired/superseded/archived만 검사) 상 기계적 PASS이나,
그 인접 위험을 **D1(critical)**로 별도 승격했다 — `SPEC-COPILOT-VWX-001`(직접 선행 SPEC, spec.md에
명시)이 `status: draft` · `run_status: partial-blocked`(M8 여전히 BLOCKED)인데도 본 SPEC이
`related_specs:`(게이트 미작동 필드)만 쓰고 `depends_on:`(게이트 작동 필드)을 선언하지 않아
Phase 1 Depends_on Pre-flight Check가 이 불일치를 전혀 잡지 못한다.

**축별 점수** (조화평균 산정):

| 축 | 점수 | 근거 |
|---|---|---|
| Clarity | 0.75 | D1(1단계 완료 여부 모순) · D7(REQ-AUTOPATCH-022 멱등 매칭 기준 미정) · D8(AC-AUTOPATCH-001 Where/When 오용) |
| Completeness | 0.75 | D1(`depends_on:` 부재) · D3(design.md §5 슬롯 D "근거 등급 노출" 미보증) · D5(AC-AUTOPATCH-025 "계약 스냅샷" 메커니즘 미정의 — `test_vwx_report.py` grep 확인, 현재 그런 스냅샷 테스트 없음) |
| Testability | 0.75 | D4(AC-AUTOPATCH-014③ "구조적으로 보인다"가 ①②와 같은 검증법 재서술 — AC-AUTOPATCH-007①의 진짜 AST 구조 검사와 대비됨) · D5(AC-AUTOPATCH-025① "의미가 그대로다" 준-위즐워드) |
| Traceability | 1.0 | §C.0 25행 전량 재대조 PASS. 공유-AC REQ쌍 **4건**(디스패치 힌트의 "3건"보다 1건 더 발견) 전부 독립 검증 가능 확인 — 은폐 없음 |

**지적표 요약**(전문 참조): D1 critical(1) · D2·D3·D4·D5 major(4) · D6·D7·D8·D9·D10 minor(5).
P0/P1 상당 지적 5건(D1~D5)이 이번 회차의 핵심 — 전부 "design.md가 약속한 안전장치가 REQ/AC로
집행되지 않음" 또는 "1단계 상태 주장이 1단계 자신의 progress.md와 불일치" 패턴이다.

**권고 수정 순서**: D1(`depends_on:` 추가 + 1단계 상태 조정) → D3(근거 등급 컬럼 추가) →
D5(계약 스냅샷 구체화) → D4(AC-AUTOPATCH-014③ AST 구조 검사로 교체) → D2(FID 부정 분기 완화책 강화) →
D6~D10 일괄. 구조적 결함이 아니라 열거 가능한 구체적 gap이므로, 2회차에서 PASS 도달이 현실적이다
(scope-reduction 불필요 — LEAN Workflow STOP 에스컬레이션 조건 미해당, 1회차뿐이라 회귀 비교 대상 없음).

### 1회차 지적 반영 — v0.1.1 (2026-08-06, 작성자=오케스트레이터)

**10건 전량 반영. 미반영 0건.**

| # | 반영 내용 | 반영 위치 |
|---|---|---|
| D1 critical | frontmatter `depends_on: [SPEC-COPILOT-VWX-001]` 추가로 run-phase 진입에 Phase 1 의존성 게이트를 물린다. **동시에** "1단계 완료" 주장을 좁혀 §C `의존 범위 한정` 신설 — 무엇에 의존하고(리포트 스키마·멀티셀/액세서리 분류·`address_basis`·`diffs.performed` 불변식, 전부 M1~M7 구현·검증 완료) 무엇에 의존하지 않는지(`ASSUMPTION-70`·1단계 M8·`status: draft`) 표로 분리 | `spec.md` frontmatter · 도입 blockquote · §C |
| D2 major | **REQ-AUTOPATCH-026 신설** — `ASSUMPTION-71` 부정/INCONCLUSIVE 시 "FID 범위가 콘솔에서 비어 있음을 눈으로 확인했다"를 일반 승인과 구분되는 **별도 페이로드 필드**로 요구하고 없으면 실행 거부. 산문 경고에서 **건별 감사 가능한 구조 데이터**로 승격. AC-AUTOPATCH-027이 GO/부정 대조로 비공허하게 검증 | `spec.md` §B.2 · `acceptance.md` · `plan.md` §A.3 |
| D3 major | REQ-AUTOPATCH-003의 드라이런 표 필수 열에 **`address_basis` 추가**. AC-AUTOPATCH-004③이 역산 전제 문구 노출을 검증하고, 전 항목 직접값인 입력에서는 그 문구가 **안 나오는지**까지 대조 | `spec.md` REQ-AUTOPATCH-003 · `acceptance.md` AC-AUTOPATCH-004 · `design.md` §4 R5 |
| D4 major | AC-AUTOPATCH-014를 **두 기법 분리**로 재작성 — ①② 산출물 문자열 스캔, ③ `server/vwx/luagen.py` **소스 AST 스캔**(금지 리터럴 0건 + 자유 문자열이 명령 배열/Lua 본문에 도달하는 경로 0건). AC-AUTOPATCH-007① AST 패턴 계승 | `acceptance.md` AC-AUTOPATCH-014 |
| D5 major | AC-AUTOPATCH-025에 **골든 스냅샷 기법 정의** — 최상위 키 집합 + 키별 타입 시그니처를 JSON 픽스처로 고정(값은 고정하지 않음), 키 내부 의미는 1단계 기존 구조 assert에 위임. 파일명·픽스처 경로 명시, `plan.md` §E 테스트 표에 등재 | `acceptance.md` AC-AUTOPATCH-025 · `plan.md` §E |
| D6 minor | M0에 **진입 전제** 신설 — 테스트 쇼파일 확보는 권고가 아니라 차단 전제. 끝내 미확보 시 `ASSUMPTION-73`·`-74`는 INCONCLUSIVE로 판정하고 M8은 BLOCKED로 남는다(운영 쇼파일 대체 금지) | `plan.md` §B M0 |
| D7 minor | REQ-AUTOPATCH-022에 멱등 일치 튜플 **(유니버스, 주소, FixtureType, DMXMode 이름)** 명시. **주소 일치 + 타입/모드 불일치는 멱등이 아니라 충돌**로 보고 | `spec.md` REQ-AUTOPATCH-022 · `acceptance.md` AC-AUTOPATCH-020 |
| D8 minor | AC-AUTOPATCH-001 `**Where**` → `**When**`(이벤트 트리거이지 capability gate가 아니다) | `acceptance.md` AC-AUTOPATCH-001 |
| D9 minor | 존재하지 않는 선례 인용 삭제. 감사 전 신호 보류가 **의도된 규율**임을 직접 서술하고, 유사 선례가 미머지 형제 브랜치에 있어 인용 불가함을 명시 | `progress.md` §E.1 |
| D10 minor | `design.md` §4에 **R8 신설** — 미리보기와 실행이 툴 호출 수준에서 결속되지 않는 잔여 위험을 **수용된 위험으로 명시**. 승인은 오케스트레이터/사람 대화 계층에서 강제되며 이는 저장소의 다른 쓰기 툴과 동일 패턴. plan-hash/preview-token 결속은 도입하지 않는다(이 SPEC만 다른 규약을 쓰면 일관성이 깨진다) | `design.md` §4 |

**반영 후 기계 재검증**(작성자 실측): REQ 26 · AC 27 · 역추적 26/26 누락 0 · 표 밖 AC 5(의도) ·
§C.0a 합 27 · `plan.md` 마일스톤 AC 줄과 **1:1 전수 일치** · 약어 토큰 0 · 명료화 마커 0 ·
레거시 EARS 조건절 키워드 0 · 레거시 패턴 라벨 0 · `depends_on` 1건.

**2회차 감사 필요.** 이 절의 반영 주장은 작성자 자신의 것이므로 독립 확인 대상이다.

### 2회차 (round2) — 2026-08-06 — plan-auditor 독립 감사

**판정: PASS** — Overall Score **0.857**(조화평균) ≥ Tier L 임계 **0.85**(여유 +0.007, 근소).
1회차 0.80 → 2회차 0.857로 **상승**(LEAN 점수 역행 STOP 미해당). 전문:
`.moai/reports/plan-audit/SPEC-COPILOT-AUTOPATCH-001-round2.md`

**회귀 확인**: D1~D10 **10건 전량 각 지적의 원문 required-fix 문구 기준으로 CLOSED 재확인**됨
(작성자의 claimed-fix 표를 그대로 신뢰하지 않고 인용 위치를 직접 재열람·재검증). 어느 지적도
미반영 상태로 재발하지 않았다. D1만 예외적으로 "핵심은 CLOSED, 잔향(research.md의 미조정 문구)은
새 지적 N3로 별도 기록" — round1의 D1 required-fix가 명시적으로 지목한 위치(spec.md §A/§C)는
둘 다 충족되었으므로 D1 자체는 재개방하지 않는다.

**신규 지적 4건**(모두 PASS를 막지 않음, N1만 major): 이 라운드는 회귀 확인에 그치지 않고
"수정 자체가 새 결함을 낳았는가"를 별도로 스캔했다 — REQ-AUTOPATCH-026/AC-AUTOPATCH-027이 닿은
모든 아티팩트의 전체 동기화 여부를 확인.

- **N1 (major)** — design.md §2.3 파라미터 스키마 초안이 REQ-AUTOPATCH-026/AC-AUTOPATCH-027의
  구조화된 확인 필드를 위한 필드명을 여전히 갖지 않는다 — D3가 잡았던 결함 **패턴**(안전 요구가
  REQ/AC 산문에는 있으나 구체 스키마엔 없음)이 새 요구사항에서 재발했다.
- **N2 (minor)** — design.md §6.2 "AC → 테스트 파일" 표에 AC-AUTOPATCH-027 행 누락.
- **N3 (minor, D1 잔향)** — research.md:23이 여전히 "본 SPEC의 입력은 확정되어 있다"는 무조건
  문구를 쓴다 — spec.md §C `의존 범위 한정`과 미조정. research.md는 v0.1.1에서 손대지 않았다.
- **N4 (minor)** — AC-AUTOPATCH-027(M2)이 문서 순서상 AC-AUTOPATCH-026(M8) **뒤**에 위치 —
  자매 SPEC `SPEC-COPILOT-VWX-001`의 v0.1.4 증분 삽입 관례(신규 AC는 M7/M8 말미 쌍보다 **앞**에
  삽입)와 어긋난다. §C.0a 배정표는 정확해 추적성·검증가능성 피해는 없다.

**축별 점수**: Clarity 0.75(변화 없음 — D7·D8 CLOSED로 상쇄, N3·N4가 잔여) · Completeness 0.75
(변화 없음 — D1·D3·D5 CLOSED이나 N1·N2가 같은 결함급을 재도입) · Testability 1.0(D4·D5 완전
CLOSED, weasel word 재스캔 0건) · Traceability 1.0(REQ-AUTOPATCH-026→AC-AUTOPATCH-027 신규 1:1, 26/26 유지).

**권고**: PASS이므로 3회차 의무 아님. N1(major)은 M2 착수 전 경량 v0.1.2 패치로 필드명을
확정하는 것을 권한다 — required fix는 round2 리포트 Defects Found N1 참조. N2~N4는 선택.

### 2회차 지적 반영 — v0.1.2 (2026-08-06, 작성자=오케스트레이터)

**N1~N4 4건 전량 반영. 미반영 0건.** 2회차가 PASS(0.857)였으므로 의무는 아니나,
N1은 D3와 **같은 결함 패턴**(설계가 약속한 것이 인터페이스 계약에 없음)의 재발이라 방치하지 않는다.

| # | 반영 내용 | 위치 |
|---|---|---|
| N1 major | `design.md` §2.3 툴 스키마에 **`fid_range_visually_confirmed_empty: boolean`** 필드 신설 — `ASSUMPTION-71` 부정·INCONCLUSIVE 분기 필수, 생략 시 실행 거부, `selected`·`dry_run`과 독립임을 주석에 명시. AC-AUTOPATCH-027 기대결과가 **그 정확한 필드명을 인용**하도록 재작성해 요구와 인터페이스 계약이 같은 자산을 지목하게 했다 | `design.md` §2.3 · `acceptance.md` AC-AUTOPATCH-027 |
| N2 minor | `design.md` §6.2 AC→테스트 파일 표의 `test_autopatch_fid.py` 행에 `027` 추가 | `design.md` §6.2 |
| N3 minor | `research.md` §1의 무조건적 "입력은 확정되어 있다" 문단 아래에 v0.1.1 갱신 주석 추가 — 확정 범위가 `spec.md` §C `의존 범위 한정`으로 좁혀졌고 1단계 전체 완료를 뜻하지 않음을 명시. `status:` 줄도 v0.1.2로 갱신 | `research.md` §1 · status |
| N4 minor | AC-AUTOPATCH-027 절을 AC-AUTOPATCH-008 **직후**로 이동 — 개정 AC를 종단 마일스톤(M7/M8) 뒤가 아니라 소속 마일스톤(M2) 그룹에 두는 `SPEC-COPILOT-VWX-001` v0.1.4 관례를 따른다. 문서 순서: … 007 · 008 · **027** · 009 … | `acceptance.md` |

**반영 후 기계 재검증**(작성자 실측): REQ 26 · AC 27 · 역추적 26/26 누락 0 · 표 밖 AC 5 ·
§C.0a 합 27 · `plan.md` 1:1 일치 · 약어 토큰 0 · 명료화 마커 0 · 필드명이 `design.md`와
`acceptance.md` 양쪽에 동일 문자열로 존재.

### 3회차 (round3) — 2026-08-06 — plan-auditor 독립 감사

**판정: PASS** — Overall Score **0.857**(조화평균, round2와 **동일** — 역행 아님, LEAN 점수 역행
STOP 미해당). 전문: `.moai/reports/plan-audit/SPEC-COPILOT-AUTOPATCH-001-round3.md`

**공정 이상 사항 발견**: 감사 지시는 v0.1.2가 "미커밋 작업트리 변경"이라 전제했으나, 실제로는 이미
`fa70cf3`(0869fdd의 자식 1커밋)로 커밋되어 있었다(`git status --short`가 SPEC 디렉터리에 대해
비어 있음을 반환). 3회차 감사는 이 사실을 그대로 보고하고, `0869fdd..HEAD` diff를 감사 대상으로
삼아 진행했다 — 감사 자체의 유효성에는 영향이 없다(대상 텍스트는 동일).

**N1~N4 전량 CLOSED 재확인**(작성자의 claimed-fix 표를 신뢰하지 않고 원문 재대조): N1(필드명
`fid_range_visually_confirmed_empty`가 `design.md` §2.3와 `acceptance.md` AC-027 양쪽에 정확히
일치) · N2(`design.md` §6.2에 027 추가, 문구 그대로 충족) · N3(`research.md` 갱신 문구가
`spec.md` §C와 무모순, `status:` v0.1.2로 갱신 확인) · N4(VWX-001의 실제 `acceptance.md`를
**직접 재조회**해 관례를 독립 재검증 — AC-VWX-027/028/029가 M7/M8 종단쌍보다 앞에 위치함을 확인).

**신규 지적 2건 발견**(모두 PASS를 막지 않음, N5는 major):
- **N5 (major)** — `design.md` §6.2에 027을 추가한 바로 그 편집이 기존 `002 · 003 · 004 →
  test_autopatch_candidates.py` 행을 **삭제**했다. 실제 테스트 파일 매핑은 `acceptance.md`의
  각 AC 본문과 `plan.md` §E에 여전히 정확하게 남아 있어 실질 피해는 design.md 로컬이지만,
  round2 이후에도 자기검증 범위가 "전체 표 재대조"가 아니라 "대상 행만"이었다는 동일 실패
  패턴이 재발했다. `progress.md`의 N2 claimed-fix 행은 이 삭제를 언급하지 않아 과소 신고다.
- **N6 (minor)** — `acceptance.md:3` · `plan.md:3` 상태줄이 여전히 `v0.1.0`이며,
  `acceptance.md:3`의 "AC 26건 계획"은 같은 문서 §C.0a의 "합 27"과 **자기모순**이다.

**축별 점수**: Clarity 0.75(N3·N4 CLOSED로 상쇄되나 N6이 같은 밴드를 유지) · Completeness 0.75
(N1 CLOSED가 개선이나 N5가 같은 결함 패턴을 더 나쁜 형태로 재도입 — round2의 26/27 커버가
24/27로 후퇴) · Testability 1.0(AC-027이 구체 필드명을 얻어 오히려 개선, weasel word 0건) ·
Traceability 1.0(§C.0/§C.0a는 design.md §6.2와 별개 SSOT, N5 영향 없음, 26/26·27/27 유지).

**권고**: 3회차(재시도 상한)이므로 4회차 의무 아님. N5(major)를 경량 패치로 되돌리기를 권한다 —
`design.md` §6.2에 `002 · 003 · 004 | test_autopatch_candidates.py` 행 복원. N6은 선택.

### 4회차 (round4) — 2026-08-06 — plan-auditor 독립 감사 (재시도 상한 이후, 오케스트레이터 재량 위임)

**판정: PASS** — Overall Score **0.923**(조화평균, round3의 0.857보다 **+0.066 개선** — 역행 아님,
LEAN 점수 역행 STOP 미해당). 전문: `.moai/reports/plan-audit/SPEC-COPILOT-AUTOPATCH-001-round4.md`

**감사 대상**: round3 이후 오케스트레이터(작성자, 감사 에이전트 아님)가 직접 손댄 `acceptance.md`·
`design.md`·`plan.md` 3개 파일의 미커밋 작업트리 변경(round3 N5·N6 자기수정) — `progress.md` §E.1
`known_gaps`에 `[반영됨·미검증]` 접두로 기록된 바로 그 변경. 이 접두 자체가 "자기검증만 거쳤다"는
신호이므로, 이전 라운드와 동일한 규율로 신뢰하지 않고 원문 대조로 독립 재검증했다.

**N5·N6 전량 CLOSED 확인**(claimed-fix 표를 신뢰하지 않고 `git diff fa70cf3`로 실제 diff를 직접
대조): N5(`design.md` §6.2에 `002 · 003 · 004 | test_autopatch_candidates.py` 행이 정확한 위치에
복원되었고, 표 전체를 처음부터 다시 세어 27/27 AC 커버·중복 0·누락 0을 확인. 복원 편집 자체는
`git diff` 상 1줄 추가뿐으로 부수 손상 없음) · N6(양쪽 상태줄이 `v0.1.2, 2026-08-06`으로 갱신되고
acceptance.md:3의 "AC 27건"이 §C.0a "합 27"과 일치함을 직접 대조로 확인, 6개 아티팩트 전체에 대한
광역 "26건/27건" 재스캔에서 잔여 staleness 0건).

**신규 지적 3건 발견**(모두 PASS를 막지 않음, N7만 major) — 이번 회차의 과제 지시가 요구한 "터치된
행뿐 아니라 27개 AC 전부를 acceptance.md 자체 검증방법과 대조"하는 전수 스윕에서 처음 발견됨:

- **N7 (major)** — `design.md` §6.2의 `013·014·015·016 | test_autopatch_lua.py` 행에
  AC-AUTOPATCH-015가 잘못 배정되어 있다. AC-015 자신의 `acceptance.md:313` 검증방법
  (`test_autopatch_execute.py`)과 `plan.md:180`의 파일별 주제 설명이 모두 execute.py를 가리킨다.
  v0.1.0부터 존재해온 결함으로 이번 라운드의 N5 복원 편집이 만든 것이 아니다(`git diff`로 확인 —
  그 행은 이번 회차에 손대지 않았다). §C.0/§C.0a 추적성 SSOT는 무영향.
- **N8 (minor)** — `design.md` §6.2의 `024·025` 행이 AC-025의 신설 골든스냅샷 파일
  `test_autopatch_contract.py`를 명시하지 않는다(`plan.md:183`·`acceptance.md:427-428`은 명시).
- **N9 (minor)** — `design.md:3` 상태줄 접미사 "plan-audit 1·2회차 지적 반영"이 이번 회차 N5 반영
  사실을 반영하지 못해 이 파일 자체의 변경사항과 어긋난다.

**축별 점수**: Clarity 1.0(N6 CLOSED로 상승 — 잔여 Clarity급 결함 없음, weasel word 재스캔 0건) ·
Completeness 0.75(N5는 깨끗이 닫혔으나 N7이 같은 결함급을 다른 구체적 사유로 재도입 — round3와
동일 밴드 유지) · Testability 1.0(무변화) · Traceability 1.0(무변화 — N7~N9는 §6.2 국소, SSOT
무영향).

**공정 관찰(과제 명시 요청)**: round2→round3는 "수정이 직접 새 결함(N5)을 낳음"(N2의 편집이 N5를
유발)이었으나, round3→round4는 그 특정 하위 패턴이 재발하지 **않았다**(N5 복원 편집 자체는
`git diff`로 확인된 대로 깨끗함). 그러나 더 넓은 패턴 — "`design.md` §6.2가 4회차 동안 한 번도
전수·정확성 기준으로 완전히 검증된 적이 없다" — 는 여전히 살아 있다: 1회차는 §6.2를 아예 감사하지
않았고, 2회차(N2)는 027 등재 여부만, 3회차(N5)는 행의 존재 여부만 확인했을 뿐 행 **내용의 정확성**은
아무도 확인하지 않았다. 이번 회차가 처음으로 27개 AC 전부에 대해 acceptance.md 자체 인용과 대조하는
전수 스윕을 수행했고, 그 즉시 v0.1.0부터 있던 N7을 찾아냈다. **Kickoff 전에 N7 수정 후 다시 한 번
전수 대조를 권고한다** — round2→round3의 "좁은 범위 자기검증이 새 결함을 놓친다" 실패 패턴이 N7 수정
자체에서도 재발하지 않는지 확인하기 위함이다.

**권고**: 재시도 상한(3회차) 이후 재량 위임 검증이므로 5회차 의무 아님. N7(major)을 경량 패치로
수정하기를 권한다 — `013·014·016 | test_autopatch_lua.py`와 `015·017·018·019 |
test_autopatch_execute.py`로 행 분리. N8·N9는 선택(같은 패치에 묶어도 무방).

### 5회차 (round5) — 2026-08-06 — plan-auditor 독립 감사 (재시도 상한 이후, 오케스트레이터 재량 위임)

**판정: PASS** — Overall Score **0.923**(조화평균, round4와 **동일** — 역행도 개선도 아닌 **횡보**,
LEAN 점수 역행 STOP 미해당). 전문: `.moai/reports/plan-audit/SPEC-COPILOT-AUTOPATCH-001-round5.md`

**감사 대상**: round4 이후 오케스트레이터(작성자, 감사 에이전트 아님)가 직접 손댄 `design.md` §6.2
표의 미커밋 작업트리 변경(round4 N7 자기수정 — `013·014·015·016` 행을 `013·014·016`과
`015·017·018·019`로 분리) — `progress.md` §E.1 `known_gaps`에 `[반영됨·미검증]` 접두로 기록된 바로
그 변경. N8·N9는 이번 회차에 손대지 않았다고 기록되어 있어(각각 `[신규 · round4 발견]` 접두, 
`[반영됨]` 아님), 이 주장 자체를 원문 대조로 독립 검증했다.

**N7 전량 CLOSED 확인**(claimed-fix 표를 신뢰하지 않고 AC-013·014·015·016·017·018·019 여섯 건
전부를 acceptance.md 자체 검증방법과 개별 대조): `design.md` §6.2가 `013·014·016 |
test_autopatch_lua.py`와 `015·017·018·019 | test_autopatch_execute.py`로 정확히 분리되었고,
여섯 AC 전부 자체 인용과 정확히 일치함을 확인. `git diff fa70cf3`로 이 편집이 단일 훅(hunk)이며
그 두 행 외 다른 어떤 행도 건드리지 않았음을 확인 — 부수 손상 없음.

**N8·N9 원문 대조로 미반영 확정**(작성자 기록이 정확함을 독립 검증): `024·025` 행은 여전히
`test_autopatch_contract.py`를 명시하지 않고, `design.md:3` 상태줄 접미사는 여전히 "1·2회차
지적 반영"에 머문다. `git diff fa70cf3 -- design.md`가 두 지점 모두 이번 회차에 손대지 않았음을
확인 — 작성자가 은폐 없이 정확히 신고한 대로다.

**신규 지적 1건 발견**(PASS를 막지 않음, minor) — 이번 회차의 과제 지시가 요구한 "27개 AC 전부를
acceptance.md 자체 인용과 대조"하는 전수 스윕에서 발견됨. round4의 "25건 무결" 주장의 범위(001-014
포함) 안에 있었으나 round4가 놓쳤다:

- **N10 (minor)** — `design.md` §6.2의 `002 · 003 · 004 | test_autopatch_candidates.py` 행이
  AC-AUTOPATCH-004 자신의 검증방법(`acceptance.md:159` — `test_autopatch_candidates.py` ·
  `test_autopatch_execute.py` 이중 인용)의 두 번째 파일을 표에 담지 않는다. v0.1.0(`db95781`)부터
  존재해온 결함(`git show`로 확인) — 이번 회차 편집이 만든 것이 아니다. N8과 같은 결함급(행이
  일부 파일만 담고 나머지를 누락)이며, round4가 "무결"이라 인증한 바로 그 배치(001-014) 안에서
  나왔다는 점이 이번 회차 공정 관찰의 근거다.

**축별 점수**: Clarity 1.0(무변화) · Completeness 0.75(N7은 깨끗이 닫혔으나 N10이 같은 결함급을
같은 표에서 재도입 — round4와 동일 밴드, 이산 루브릭상 항목 수와 무관하게 0이 아니면 0.75) ·
Testability 1.0(무변화) · Traceability 1.0(무변화 — N8~N10은 §6.2 국소, SSOT 무영향).

**공정 관찰(과제 명시 요청)**: round2→round3의 "수정이 직접 새 결함을 낳는" 하위 패턴은 두 회차
연속(round3→round4, round4→round5) 재발하지 않았다 — N7 분리 편집 자체는 `git diff`로 확인된 대로
깨끗하다. 그러나 더 넓은 패턴은 이번 회차가 한층 더 구체적으로 보여준다: round4가 "전수"라 부른
스윕조차 "행 배정이 맞는가"만 확인했을 뿐 "행이 그 AC가 인용하는 모든 파일을 담는가"는 확인하지
않았다 — AC-004(이중 인용)가 그 사각지대에 있었다. §6.2는 acceptance.md 각 AC의 검증방법 필드를
손으로 베낀 중복 표이며, 5회차 연속 발견된 모든 결함(N2·N5·N7·N8·N9·N10)이 "두 문서가 불일치"
패턴이다. **권고(자문, 차단 아님)**: §6.2를 유지·재검증하는 대신 **삭제하고 "각 AC의 검증방법
필드를 보라"는 한 문장으로 대체**하는 편이 이 결함 클래스 자체를 없앤다 — 손으로 유지되는 요약은
아무리 신중히 재검증해도 다음 편집에서 또 어긋날 수 있다.

**회귀 워치(미발동)**: N8·N9가 이제 2회 연속(round4, round5) 미반영으로 남았다 — 정체 감지
조항은 3회 연속을 요구하므로 아직 미해당이나, round6이 있다면 주시 대상이다.

**권고**: 재시도 상한(3회차) 이후 재량 위임 검증이므로 6회차 의무 아님. N8·N9·N10을 한 번에 묶어
경량 패치하거나, 공정 관찰의 구조적 대안(§6.2 삭제)을 고려하기를 권한다.

### 6회차 (round6) — 2026-08-06 — plan-auditor 독립 감사 (재시도 상한 이후, 오케스트레이터 재량 위임)

**판정: PASS** — Overall Score **1.000**(조화평균, round5(0.923)보다 **+0.077 개선** — 역행 아님,
LEAN 점수 역행 STOP 미해당). 전문: `.moai/reports/plan-audit/SPEC-COPILOT-AUTOPATCH-001-round6.md`

**감사 대상**: round5 이후 오케스트레이터(작성자, 감사 에이전트 아님)가 직접 손댄 `design.md`
§6.2 — 8행 표 전체를 삭제하고 "유일한 출처는 acceptance.md 각 AC의 검증 방법 줄" 이라는 안내
문단으로 대체(v0.1.3), 상태줄도 "1·2회차 지적 반영" → "1~5회차 지적 반영 · §6.2 폐지"로 갱신.
`progress.md` §E.1 `known_gaps`에 `[구조적으로 해소 · 재검증 대상 아님]` 접두로 기록되었으나, 그
항목 자신이 "폐지가 다른 참조를 깨지 않았는지는 6회차 독립 재확인 전까지 미검증으로 취급"이라고
명시한 바로 그 주장을 원문 대조로 독립 검증했다.

**N8·N9·N10 전량 genuinely CLOSED 확인**(작성자의 "구조적으로 해소" 주장을 신뢰하지 않고 6가지
과제로 독립 재검증): (1) §6.2 표가 진짜로 삭제되었고 잔여 표·주석 표 없음을 직접 읽어 확인. (2)
6개 아티팩트 전체를 "§6.2"·"design.md §6" 패턴으로 광역 재스캔 — §6.2를 권위 출처로 참조하는
곳 0건(발견된 매치는 전부 다른 절(§2.3·§5) 참조이거나 progress.md 자체 감사기록). (3) N8·N10의
실제 대상이었던 AC-004·AC-025 자신의 검증방법 필드를 직접 읽어 두 파일 모두 필드 안에 이미
완전히 명시되어 있었음을 확인 — 삭제가 정보를 옮긴 게 아니라 부정확한 사본만 제거했음을 실증.
(4) 새 안내 문단 자체에 과장·잘못된 리포트 경로·구조 넘버링 붕괴 없음을 확인(§6 넘버링 §1~§8
전부 재추출, 간극·중복 없음, §6.2 제목 자체는 보존되어 있어 참조 넘버링 붕괴 없음). N9는 상태줄
자체가 "1~5회차 지적 반영"으로 갱신되어 직접 재확인으로 해소 확인.

**신규 지적 0건.** 과제가 명시 요청한 "새 지적을 감추지 말 것"에 따라 인용 정밀도 관점(§6.2 폐지
사유 인용이 "round5 N7/N8/N10"만 들고 N9를 뺀 점)을 별도로 조사했으나, N9는 §6.2 표-드리프트와
다른 결함급(같은 파일의 별개 상태줄 문제)이며 같은 편집의 다른 훅으로 이미 해소되어 있어 결함으로
접수하지 않았다(전문 참조).

**축별 점수**: Clarity 1.0(무변화) · **Completeness 0.75→1.0**(N7은 round5가, N8·N9·N10은 이번
회차가 각각 원문 대조로 genuinely CLOSED 확인 — round1 이후 최초로 4개 축 전부 잔여 결함 0건) ·
Testability 1.0(무변화) · Traceability 1.0(§C.0a 9행을 plan.md M0~M8 `AC` 줄과 행 단위로 재대조,
합 27 확인).

**공정 관찰 마무리**: round2~round5에 걸쳐 4연속으로 새 결함을 낸 §6.2가 이번 회차로 완전히
사라졌다 — round5 리포트가 제안한 구조적 대안이 실행되었고, 독립 검증으로 그 대안이 실제로
결함 클래스 자체를 제거했음이 확인됐다(표가 없으므로 더 이상 드리프트할 대상이 없다). `plan.md
§E 테스트 골격`이 이미 파일→주제 매핑을 독립적으로 제공하고 있어 온보딩 가독성 손실도 크지
않다는 점도 확인했다(전문 과제 6 참조).

**회귀 워치**: N8·N9가 2회 연속(round4·round5) 미반영이었으나 3회 연속에 도달하기 전(이번
회차)에 해소되어 정체(stagnation) 플래그는 발동하지 않았다.

**권고**: 4연속 라운드 재발 패턴이 근본 원인(수기 사본 구조) 제거로 종결됨. 잔여 결함 0건 —
추가 delta-check 불필요. Implementation Kickoff Approval로 진행 가능(plan-phase 관점에서;
M0 라이브 세션 일정·테스트 쇼파일 확보는 run-phase 착수 전제이며 plan-audit 지적 사항 아님).

### 7회차 (round7) — 2026-08-06 — 독립 감사 (v0.1.3 amendment 대상, 작성자 ≠ 감사자)

**판정: FAIL** — Overall Score **0.7375**(4개 축 산술평균, Tier L 임계 0.85 미달).
감사 대상은 **v0.1.3 반자동 실행 모델 amendment**(§E.2aa)이며 round6 PASS(1.000)는 v0.1.2에
대한 판정이라 승계하지 않았다. 감사자 산출물: `agent://PlanAuditRound7`.

**축별 점수**: 완전성 0.72 · **일관성 0.60** · 검증가능성 0.70 · 추적성 **0.93**.

**감사자가 확인해 준 것(작성자 주장과 일치)**: REQ **26** · AC **27** · §C.0 커버 **26/26** ·
§C.0a 합 **27**(중복 0 · 누락 0) · M4 **3** · M5 **4** — 감사자가 독립 재계수해 전부 일치.
반자동 모델 자체는 기록된 증거 위에서 **옳은 결정**이라고 판정했다.

**FAIL 사유는 두 갈래다.**

**(1) N11(major) — 인과 과잉주장의 재발.** 초판 v0.1.3이 `spec.md` §A 사실 7과
`progress.md` §0·§E.2·§E.1 네 곳에 **"원인이 command destination이 아님은 확정됐다"**고 적었다.
**그것은 과잉주장이다** — L6의 양성 대조군이 증명한 것은 **명령줄 목적지가 옮겨지고 듣는다**는
명제이고, **플러그인의 목적지**는 10개 실행 경로 전부에서 `TempCmdlines Cmdline 1`이었다. 즉 가설의
**전건이 실현된 적이 없으므로** 그 가설은 관측된 0건과 여전히 양립하며 반증되지 않았다.
**§E.2z가 자기정정한 바로 그 오류를 v0.1.3 초판이 되풀이했다.** 감사자가 그것을 잡았다.
→ 네 곳 전부를 **"처방(remedy)의 반증 / 원인은 미확정"** 으로 교정하고, 판정 블록에
`UNDETERMINED` 줄을 신설했으며, `spec.md` 사실 7에 **재질의 금지의 범위**를 명시해
원인 규명을 금지 register에서 빼냈다.

**(2) N12~N28(major 6 · minor 11) — amendment 전파 누락.** 요구·AC 본문은 고쳤으나
**같은 내용을 다른 곳에서 반복하는 지점들**을 함께 고치지 않았다:
§0 상태줄이 round6 PASS와 "M4~M8 착수 불가"를 그대로 광고(N12) · `acceptance.md` §B 시나리오
1·7이 서버 실행과 철회된 편집기 안내를 계속 요구(N13·N25) · §F DoD 3번이 전제 5건에 머무름(N14) ·
`design.md` §7 안티패턴 1·2가 폐기된 요구와 반증된 근거에 의존(N15·N19) ·
`plan.md` §A.2·M0가 전제 5건(N17) · `research.md` §8 레지스트리에 76 부재(N18) ·
§2 제목이 "정본이고 라이브 검증을 마쳤다"로 남음(N20) · §0 서술·읽는 순서가 9경로/5건/8건(N21·N22·N26) ·
L2 가역성이 `progress.md`에만 있고 `spec.md`·`plan.md`에 없음(N23) · AC-015③ 무대조군(N24) ·
제목이 "자동 패치"(N27) · REQ-018 극성 혼재(N28).

**가장 실질적인 지적은 N16(major)이다.** `AC-AUTOPATCH-019`의 **비공허성 대조군이 성립 불가**가
됐다 — 그 대조군은 "실행 호출에서는 같은 기록기가 쓰기를 잡는다"였는데 반자동 모델에서는
실행 경로가 **쓰기를 하지 않으므로** 대조군을 만들 수 없고, 따라서 ①이 **공허**해진다.
이 SPEC이 §6.3으로 막으려 한 바로 그 실패다. `AC-AUTOPATCH-020`의 ①②도 같은 구조적 문제를
갖고 있었다(서버가 생성하지 않으므로 "생성 명령 0건"의 대조군이 없다).
→ 두 AC를 **산출물 수준**(사본에 쓰기를 되살려 심는 기법 · 생성된 Lua의 내용)으로 재작성하고,
`design.md` §6.3 대조군 목록을 **8건 → 10건**으로 확장했다.

**반영 결과**: N11~N28 **18건 전량 반영**. REQ 26 · AC 27 · §C.0a 합 27 **불변**(N28은 신규 REQ ID를
만드는 대신 REQ-018을 **복합 태그**로 명시해 26을 유지 — 감사자가 제시한 두 대안 중 계수 불변인 쪽).
코드 변경 0. **round8 독립 재검증 대상이다.**

**이 회차의 교훈(공정 관찰)**: 이 SPEC은 **인과 과잉주장을 두 번 했다**(4차 → §E.2z 자기정정,
v0.1.3 초판 → round7 N11). 두 번 모두 "상관을 확정으로 승격"하는 같은 형태였다.
`spec.md` 사실 7의 **재질의 금지 범위 명시**가 세 번째를 막는 구조적 장치다 —
관측은 동결하고 **원인 규명은 동결하지 않는다.**

### 8회차 (round8) — 2026-08-06 — 독립 재검증 (round7 반영 대상, 작성자 ≠ 감사자)

**판정: FAIL** — Overall Score **0.805**(Tier L 임계 0.85 미달, round7(0.7375)보다 **+0.0675 개선**
— 역행 아님). 감사자 산출물: `agent://PlanAuditRound8`.

**축별 점수**: 완전성 0.82 · **일관성 0.68** · 검증가능성 0.80 · 추적성 **0.92**.

**round7 18건 closure 판정**: **15건 CLOSED · 2건 PARTIALLY CLOSED(N11·N27) · 재staleness 1건(N12)**.
**N16은 genuinely CLOSED로 확인**됐다 — AC-019②·020①②의 대조군이 실제로 구축 가능해졌고
`design.md` §6.3이 정말 10행임을 감사자가 직접 계수했다. **N28(복합 REQ)도 정합하게 실행됐다고
확인**됐다 — AC-015①이 Ubiquitous 반쪽을, ②③이 Unwanted 반쪽을 실제로 검증한다.

**감사자가 독립 재계수한 값 — 작성자 주장과 전부 일치**: REQ **26** · AC **27**(001~027 간극 0) ·
§C.0 26행 / 커버 **26/26** / 중복 0 / 의도적 표외 **5건**(001·023·024·025·026) ·
§C.0a 1+3+5+4+3+4+3+3+1 = **27**(중복 0 · 누락 0) · `plan.md` M0~M8 `AC` 줄과 **1:1** ·
§6.3 10행 · §7 안티패턴 10건 · §0 함정 11건 · Out of Scope H3 6건 · ASSUMPTION 71~76 6건.
구조 스윕에서 **표 행 중복 0 · 고아 `---` 0 · 빈 본문 heading 0**.

**N11 판정 — 규범 지점은 옳고, 서술 지점 2곳이 남았다.** 감사자는 `spec.md` §A 사실 7의
`[재질의 금지의 범위]`, `ASSUMPTION-76` 종결문, `plan.md` §A.3의 76행, §0 [HARD]의 `UNDETERMINED`
블록, §E.1 `known_gaps`를 **전부 옳다**고 판정했고, **과소주장(under-claim)도 없다**고 확인했다
("L6 양성 대조군 확보"와 "플러그인 목적지 대조군 0"이 각각 **다른 대상**으로 명시 범위화되어
모순이 아니다). 남은 것은 서술 2곳 —
§E.2 M0 5차의 "이것이 §0의 결론에 갖는 함의" 첫 문장이 여전히 **가설** 반증으로 읽혔고(N29,
같은 절 두 단락 아래와 자기모순), §E.2aa 승인 기록이 "L6 양성 대조군 → destination 가설 반증"으로
남아 **사용자에게 제시한 근거를 잘못 기술**하고 있었다(N30). **둘 다 "처방 반증 · 원인 미확정"으로
교정했다.**

**나머지 신규·잔여 지적 11건도 전량 반영**:
N31 `nonvacuity_controls_required: 8` → **10**(머신 게이트가 자기 주석이 가리키는 §6.3과 불일치) ·
N32 §0 상태줄 "독립 round7 대기" → **round8 재검증 대기**(round7 N12와 **같은 결함 클래스의 재발**) ·
N33 §E.1 `plan_status`·`next:` 동일 교정 · N34 `spec.md` **H1**이 여전히 "자동 패치"(프론트매터만
고쳤던 N27의 잔여) → **반자동** · N35 `design.md` 상태줄 "1~5회차" → **1~7회차**(round6 N9와 같은
클래스) · N36 §0 **함정 5**가 폐기된 "배열 길이 1"을 그대로 지시 → **[폐기 · v0.1.3]** 표기 ·
**N37 "0건" 주장 5건(AC-007③·013③·016③·017②·021②)에 대조군 부재** — §F 항목 7이 "전부 붙어
있다"고 주장하는데 실제로는 아니었다(**v0.1.3 이전부터의 결함**) → 5건 전부에 사본 기법 대조군
부착 + `design.md` §6.3에 **표의 범위**를 명시(구조 수준 10건 vs AC별 전수 강제) ·
**N38 AC-019가 REQ-004의 "명시 승인 없이"라는 조건을 더 이상 가르지 못함**(두 분기 모두 쓰기 0건이
되어 조건이 관측 불가) → **④를 신설**해 **산출물 수준**에서 가른다(승인 없는 호출은 실행 가능한
Lua 전달물을 산출하지 않는다, 대조군 포함) · N39 "방법론 정정 3건" heading이 4행 표 위에 있음
(§0 항목 4가 "정정 2"로 상호참조하므로 번호가 하중을 받는다) → **4건** ·
N40 `0.1.3+r7` HISTORY 행이 프론트매터 `version`과 불일치 → **`v0.1.4`로 승격**하고 6개 아티팩트
상태줄 전부 일치 · N41 §F Justification이 `ASSUMPTION-71~75`로 M2를 게이트(§F는 `plan.md` §G보다
**우선하는 정본**이라 이 stale 범위가 형식상 이긴다) → **71~76**.

**반영 결과**: round8 지적 **13건 전량 반영**, 버전 **v0.1.4** 승격.
REQ 26 · AC 27 · §C.0a 합 27 **불변**. 코드 변경 0. **round9 독립 재검증 대상.**

**공정 관찰 — 1패스 대량 반영의 구조적 위험**: round7·round8 두 회차 모두 FAIL 사유의 다수가
"본문은 고쳤으나 **같은 사실을 반복하는 파생 지점**(상태줄 · 머신 게이트 · 온보딩 색인 · DoD ·
§F)을 함께 고치지 않음"이었다. round6이 `design.md` §6.2를 **폐지**해 없앤 결함 클래스가,
amendment가 만든 **새로운 파생 지점들**에서 되살아난 것이다. 다음 반영에서는 요구·AC 본문을
고치기 전에 **"이 사실을 반복하는 곳"의 목록을 먼저 만들고** 그 목록을 체크리스트로 쓰는 편이
싸다(파생 지점: §0 상태줄·§0 서술·§0 함정·§0 읽는 순서·§E.1 yaml 머신 게이트·§E.1 next·
§F Justification·각 아티팩트 상태줄·`spec.md` H1·프론트매터·§F DoD·§B 시나리오·§6.3 목록).

### 9회차 (round9) — 2026-08-06 — 독립 재검증 (v0.1.4 대상, 작성자 ≠ 감사자)

**판정: FAIL** — Overall Score **0.8025**(Tier L 임계 0.85 미달. round8(0.805) 대비 **−0.005 —
횡보, 실질 무변화**). **같은 근본 원인으로 3회 연속 FAIL**이다. 감사자 산출물: `agent://PlanAuditRound9`.

**축별 점수**: 완전성 0.82 · **일관성 0.72** · 검증가능성 0.75 · 추적성 **0.92**.
일관성이 3회 연속 최저 축이다.

**closure 판정**: round7·round8 지적 31건 중 **27 CLOSED · 3 PARTIALLY CLOSED · 0 NOT CLOSED**.
감사자가 **모든 계수를 독립 재확인**했다 — REQ 26 · AC 27 · §C.0 26/26(중복 0 · 의도적 표외 5건) ·
§C.0a 합 27(중복·누락 0) · `plan.md` M0~M8 `AC` 줄 **1:1** · §6.3 10행 · §7 10건 · 함정 11건 ·
Out of Scope 6건 · ASSUMPTION 6건 · 방법론 정정 4건. **구조 손상 0**(표 행 중복 0 · 고아 `---` 0 ·
깨진 표 0 · 상호참조 전부 해결). "기계적으로 확인 가능한 작성자 주장은 전부 옳다"고 판정했다.

**N11 판정 — 규범 표면은 처음으로 전부 옳다.** 감사자가 12개 지점을 전수 확인해
**처방 반증 / 원인 미확정 구분이 정확하고, 과소주장도 없다**(실무 결론이 4곳에서 확고히 유지됨)고
판정했다. 단 **세 번째 서술 지점**이 남아 있었다 — **N43**: §E.2z **자기정정 절 자신의 후속
블록**이 "L6 양성 대조군은 확보됐고 그 결과는 반증이다 — `MOST-LIKELY-HYPOTHESIS` 블록은 폐기한다"로
남아, 대조군의 대상을 범위화하지 않고 **가설 자체를 폐기**한다고 읽혔다. 과잉주장을 경계하는 절에서
과잉주장이 남아 있던 셈이다. → **`MOST-LIKELY` 등급만 폐기 · 가설은 `UNDETERMINED` · 플러그인
목적지 대조군은 여전히 0**으로 교정했다.

**가장 중요한 지적 — N42(P1): round8 N38에 대응해 넣은 내 수정이 틀렸다.**
`AC-AUTOPATCH-019④`("승인 없는 호출은 실행 가능한 Lua 전달물을 산출하지 않는다")는 **두 가지로
깨져 있었다**:

1. **정면 충돌** — 드라이런은 `REQ-AUTOPATCH-003`·`AC-AUTOPATCH-004②`가 **Lua 소스 전문을 내라고
   요구**하고 `design.md` §3 흐름도도 그렇게 그려져 있다. 드라이런은 승인 **이전**의 기본 동작이므로
   "승인 없으면 Lua를 내지 않는다"는 그 요구와 양립할 수 없다.
2. **스키마 부재 필드 인용** — 근거로 든 `승인 플래그`는 SPEC 전체에 **단 한 번** 등장하고
   `design.md` §2.3 툴 스키마에 **없다.** 이것은 **D3 · round2 N1과 똑같은 결함 패턴**이다 —
   AC-AUTOPATCH-027이 `fid_range_visually_confirmed_empty`를 직접 인용하도록 고쳐서 없앤 그 패턴을,
   내가 되살렸다. 감사자는 세 가지 해석 모두에서 ④가 무너진다는 것을 보였고,
   해석 (c)에서는 ④가 AC-003②로 붕괴해 **N38이 애초에 미수정**이라고 지적했다.

→ **④를 철회하고, `REQ-AUTOPATCH-004`가 스스로 열거한 세 금지**
(**드라이런의 실행 승격 경로 · 실행이 기본값인 인자 · 승인을 함축하는 재시도**)를 ③④⑤로 그대로
검증하게 재작성했다. 조건절의 관측 가능한 실패 모드는 애초에 그 세 개였으므로 **새 필드도 새 어휘도
필요하지 않다.** 각 항에 사본 기법 대조군을 붙였다. 감사자가 제안한 `approved: boolean` 신설안보다
이쪽이 낫다 — 스키마를 늘리지 않고 요구 원문에 밀착하며, 드라이런 요구와 충돌하지 않는다.

**나머지 6건도 전량 반영**:
**N47**(P2) `AC-AUTOPATCH-014③(a)`의 문자열 리터럴 0건에 **대조군 부재** — ③의 비공허성 절이 (b)만
지목하고 ②는 다른 기법(산출물 문자열)이라 (a)를 덮지 못한다. §F 항목 7의 "전수 성립" 주장에 대한
**유일한 반례**였다 → (a) 전용 대조군 신설(`luagen.py` 사본에 CD 리터럴 심기) ·
**N44**(P2) §F Justification이 M0 BLOCKED · M2 미착수로 서술 — **§F는 `plan.md` §G보다 우선하는
정본**이라 형식상 이 stale 서술이 이긴다(round8 N41이 같은 문장의 가정 범위만 고치고 나머지를 남겼다)
→ M0 5차 종결 · M1·M2·M3 완료 · 게이트 해제로 갱신 ·
**N45**(P2) §0 amendment 문단이 "독립 round7 감사 대기 중" · **N46**(P2) §0 "다음 담당자가 먼저 할 것"
2번이 **이미 승인·반영된 전환을 다시 제안하라고 지시**(최다 통행 온보딩 지점) → 둘 다 현재 상태로 ·
**N48**(P3) §6.3의 8→10 확장 귀속이 v0.1.3(실제로는 v0.1.4/round7 반영) · **N49**(P3) §E.1 yaml
캡션이 "6회차 감사 PASS로 갱신".

**반영 결과**: round9 지적 **8건(N42~N49) 전량 반영**. 버전 `v0.1.4` 유지(내용 교정이며 요구·AC
계수 무변). REQ 26 · AC 27 · §C.0a 합 27 **불변**. 코드 변경 0. **round10 독립 재검증 대상.**

**공정 관찰 — 세 번째 FAIL의 성격이 달라졌다.** round7·round8은 "본문은 맞고 파생 지점이 stale"이
주였다. round9는 **파생 지점 stale이 20개 스윕 대상 중 5개로 줄었지만**(감사자 표현: "materially
reduced but not eliminated"), 대신 **내가 직전 라운드에 넣은 수정 자체가 틀렸다**(N42)는 새로운
실패 양식이 나왔다. 교훈: **감사 지적을 급히 봉합하면 새 결함을 만든다.** N38은 "조건이 관측
불가"라는 지적이었는데, 나는 **새 조건을 발명해서** 답했고 그 조건이 기존 요구와 충돌했다.
**옳은 답은 요구 원문이 이미 열거한 실패 모드를 읽는 것**이었다 — 새 어휘를 만들기 전에
**요구가 스스로 무엇을 금지했는지 다시 읽어야 한다.**

### 10회차 (round10) — 2026-08-06 — 독립 재검증 (v0.1.4 대상, 작성자 ≠ 감사자)

**판정: PASS** — Overall Score **0.865 ≥ Tier L 0.85**. round9(0.8025) 대비 **+0.0625 개선** —
**이 amendment 사이클의 첫 비-FAIL**이다. 감사자 산출물: `agent://PlanAuditRound10`.

**축별 점수**: 완전성 0.87 · **일관성 0.82** · 검증가능성 0.85 · 추적성 **0.92**.
일관성은 **4회 연속 상승**했다(0.60 → 0.68 → 0.72 → 0.82).

**closure**: 39건 중 **37 CLOSED · 2 PARTIALLY CLOSED(N47 요약 꼬리 · N49) · 0 NOT CLOSED.**

**핵심 판정 두 건 — 둘 다 CLOSED로 확인됐다.**

1. **N42/N38 — 건전하게 닫혔다.** 감사자가 네 항목으로 검증했다: (a) 철회된 ④가 사라졌고 새 ④는
   `dry_run=true`가 전달 경로로 흐르는 것만 금지하므로 `REQ-AUTOPATCH-003`·`AC-AUTOPATCH-004②`
   (드라이런은 Lua 소스 전문을 낸다)와 **직교**한다 · (b) `dry_run`만 인용하며 그것은 `design.md`
   §2.3에 **실재**한다(스키마 부재 필드 인용 없음) · (c) ③④⑤가 **각각 독립적으로 반증 가능**하다
   (기본값 뒤집기 · 승격 경로 심기 · 자동 재시도 심기) · (d) REQ-004가 열거한 세 금지에 **1:1 대응하고
   누락이 없다**. 감사자는 **내 선택(요구 원문이 이미 금지한 것을 읽는 것)이 round9 감사자가 제안한
   `approved: boolean` 신설안보다 낫다**고 판정했다 — §2.3 스키마를 늘리지 않기 때문이다.
2. **N11 — 규범·서술 표면 전부 옳고 완전하다.** 13개 지점 전수 확인. 어느 지점도 *가설*이
   반증됐다고 적지 않으며, 실무 결론도 약화되지 않았다. §E.2z 후속 블록(N43)이 `MOST-LIKELY`
   등급만 폐기하고 가설을 `UNDETERMINED`로 남기며 "플러그인 목적지 대조군은 여전히 0"을 적은 것이
   확인됐다.

**비공허성 전수 검증**: 감사자가 `acceptance.md`의 **모든** 0건 주장 **31건**을 표로 열거해
**31/31 대조군 보유**를 확인했다 — round9의 유일한 반례(AC-014③(a))가 진짜로 닫혔고 새 반례는 없다.

**계수 독립 재확인**: REQ 26 · AC 27 · §C.0 26/26(중복 0 · 의도적 표외 5건) · §C.0a 합 27 ·
`plan.md` 1:1 · §6.3 10행 · §7 10건 · 함정 11건 · Out of Scope 6건 · ASSUMPTION 6건 ·
방법론 정정 4건 · 룰북 반증 4건 — **전부 일치**. 구조 손상 **0**.

**신규 지적 6건(N50~N55) 전량 반영 — 전부 P2/P3, 규범 아님, 킥오프 비차단:**

- **N50(P2) — 가장 실질적. "경로 13가지"가 자기 열거와 맞지 않았다.** 감사자가 어떤 해석으로도
  13이 나오지 않음을 보였다(4차 9 + 5차 열거 8 = 17, 또는 16). 원인은 **계수 단위 혼용**이다 —
  나는 **실행 컨텍스트**와 **인자 변형**을 한 숫자에 섞었다. 13은 이 SPEC에서 가장 널리 전파된
  증거 숫자이고(10개 지점) **amendment 전체의 실증 근거**이므로 재구성 불가는 심각하다.
  → **계수 단위를 분리**했다: **실행 경로 10가지**(4차까지 9 + 5차 매크로 발화 1) ·
  **`AddFixtures` 인자 변형 8종**(a·b·c·d·e·f·g·h) · **별도 생성 기법 1종**(객체 모델 `Append`).
  5차의 인자 변형은 전부 **기존 OSC 발화 컨텍스트** 안에서 돌았으므로 새 경로가 아니다.
  §E.2 M0 5차에 **계수 표**를 넣고 의존 지점 12곳 전부에 전파했다.
- **N53(P2)** `design.md` §6.3 범위 주석과 `acceptance.md` 상태줄이 대조군 추가를 **5건·N37**로만
  적어, round9 N47이 반박한 바로 그 근거로 "전수 성립"을 주장하고 있었다(`spec.md` HISTORY만 6건으로
  옳았다 — 같은 변경의 세 요약이 불일치) → **6건 · N37+N47**로 통일.
- **N52(P2)** §E.1 굵은 헤드라인이 "audit-ready 유지"로 남아 **바로 아래 yaml `plan_status`와 정면
  모순** → 현재 상태를 적고 round6 서술을 역사 기록으로 강등.
- **N51(P2)** §E.1 전문 블록과 yaml 캡션이 **round9를 누락**(N49의 잔여) → round7·8·9 39건으로.
- **N55(P3)** `커밋 10건`이 실측과 불일치(`ca00bc5..HEAD` = **15건**, run-phase **11건**) →
  **계수 기준을 명시**해 갱신.
- **N54(P3)** §0 amendment 꼬리의 짝 없는 `**` → 제거.
- **N55b(P3)** §F 항목 7의 보증이 **`"0건"` 토큰에만 걸려** 있어, 같은 성질의 문장형 부재 주장
  5건(AC-007②·010③·018③·021③·023③)이 대조군 없이 통과했다 → 항목 7을 **"금지·부재를 주장하는
  항목 전부"** 로 넓히고 그 5건에 대조군을 부착. 넓힌 기준을 스스로 적용해 **AC-009②도** 추가
  발견·부착했고, 라이브 세션으로만 검증되는 **AC-001·AC-026 2건을 명시적 범위 예외**로 적었다.

**반영 결과**: round10 지적 6건 + 자체 발견 1건(AC-009②) 반영. 버전 `v0.1.4` 유지.
REQ 26 · AC 27 · §C.0a 합 27 **불변**. 코드 변경 0.

```
plan-audit: PASS (round10, 0.865 ≥ 0.85)
권고: Implementation Kickoff Approval → M4 착수
```

**공정 관찰 — 무엇이 이 사이클을 빠져나오게 했나.** round7~9가 세 번 연속 FAIL한 이유는 두 가지
였고 성격이 달랐다: (1) **파생 지점 전파 누락**(요구 본문은 맞는데 같은 사실을 반복하는 상태줄·
머신 게이트·온보딩 색인이 stale) — round10에서 20개 스윕 대상 중 stale 3~4개로 줄어 통과했다.
(2) **급한 봉합이 만든 새 결함**(N42) — 지적을 새 어휘로 답하려 한 것이 원인이었고,
**요구 원문이 이미 열거한 실패 모드를 읽는 것**이 정답이었다.
세 번째로, round10이 **내 핵심 증거 숫자 자체(13경로)를 반박**했다 — 감사가 문서 정합성뿐 아니라
**측정 기록의 재구성 가능성**까지 검증한 것이며, 계수 단위를 섞어 쓴 것이 실제 결함이었다.
**남은 위험은 파생 지점 클래스가 구조적으로 제거되지 않았다는 것**이다(§6.2처럼 없앨 수 있는
표가 아니라 서술 지점이라 폐지가 불가능하다). 다음 담당자는 요구·AC를 고칠 때
§E.1a 8회차의 **파생 지점 체크리스트**를 반드시 쓰라.

---

## §E.2 Run-phase Evidence

(마일스톤별 증거를 기록한다. M0는 `GO:` / `NEGATIVE:` / `INCONCLUSIVE:` 접두 행으로
`ASSUMPTION-71`~`-76` 판정을 남긴다. 76은 M0 3~5차에서 사후 식별돼 편입됐다.)

### M0 checkpoint — live access blocked (2026-08-06 10:42 KST)

**상태: BLOCKED — M0 전제 측정 미착수.** Implementation Kickoff Approval은 통과했으나,
현재 디스패치에서 실기 onPC/responder 왕복이 성립하지 않아 `ASSUMPTION-71`~`75`에
`GO:` / `NEGATIVE:` / `INCONCLUSIVE:` 판정 행을 쓰지 않는다. 이 판정 행들은 실제 라이브
증거가 있을 때만 추가한다.

**실측한 환경 값**: `resolve_effective_settings()` 기준 site config는
`console_host=127.0.0.1`, `console_port=8000`, `receive_port=9005`, `osc_slot=2`,
`plugin_import_dir=~/MALightingTechnology/gma3_library/datapools/plugins`.

**읽기 전용 프로브 결과**:

| probe | command | result |
|---|---|---|
| FixtureType root | `uv run python -m server.tools.responder_roundtrip --host 127.0.0.1 --port 8000 --listen-port 9005 --path "Patch/FixtureTypes" --skip-exec --wait 3` | `ping` timeout · `state` timeout · `result: FAIL` |
| reply-port control | `uv run python -m server.tools.responder_roundtrip --host 127.0.0.1 --port 8000 --listen-port 9000 --path "Patch/FixtureTypes" --skip-exec --wait 3` | `ping` timeout · `state` timeout · `result: FAIL` |
| existing DataPool root | `uv run python -m server.tools.responder_roundtrip --host 127.0.0.1 --port 8000 --listen-port 9005 --path "DataPool/Sequences" --skip-exec --wait 3` | `ping` timeout · `state` timeout · `result: FAIL` |
| passive receive check | `uv run python -m server.tools.responder_roundtrip --host 127.0.0.1 --port 8000 --listen-port 9005 --diagnose --wait 3` | listened for 3s; no OSC messages observed |

**Orca coordinator decision**: `record_blocked`. Coordinator instructed this worker to record M0 as blocked
using the observed timeout evidence and missing immediate destructive-write/showfile details, and to not proceed
to AddFixtures or M0-dependent implementation milestones.

**후속 차단 사유**:

- 테스트 쇼파일의 실제 이름/상태를 이 디스패치에서 관측하지 못했다.
- `ASSUMPTION-73`·`74`의 AddFixtures 측정은 파괴적 쓰기라 즉시 승인 없이는 수행하지 않았다.
- `plan.md` §A.2·§B M0가 **M2·M3·M6** 설계를 M0 판정에 의존시켜 두었으므로 **M2 이후**를 착수하지
  않는다. **[정정 · 후속 디스패치]** 이 절의 최초 기록은 "M1 이후 코드 마일스톤도 착수하지 않는다"고
  적었으나 그것은 과했다 — `plan.md` §A.2가 막는 것은 "M2 이후"이고 M1은 콘솔 무접촉이라
  차단 대상이 아니다. M1은 아래 절에서 완료되었다.

### M1 — 패치 후보 입력 모델 (완료)

**상태: COMPLETE — M1은 콘솔 무접촉 인메모리 리포트 payload 범위에서 완료.** 직전 M0 checkpoint의
"M1 이후 코드 마일스톤도 착수하지 않는다" 판단은 이번 디스패치 handoff가 정정했다. 근거:
`plan.md` §A.2 문구는 "M0 없이 M2 이후를 착수하지 않는다"이며, M1의 AC-002·003·004는
1단계 리포트 payload 기반이라 라이브 콘솔 없이 검증 가능하다.

**TDD RED 증거**: `uv run pytest server/tests/test_autopatch_candidates.py -q` →
`ModuleNotFoundError: No module named 'server.vwx.patchplan'`, `1 error in 0.06s`.

**구현 산출**:

- `server/vwx/verdicts.py` — `candidate_rejection_reason` · `selection_error_reason` 닫힌 어휘와
  라벨표-어휘 키집합 일치 검증. 후보 거부 사유는 `comparison_not_performed` ·
  `invalid_report_payload` · `multi_system_mapping_absent`, 선택 오류 사유는 `unknown_candidate_id`.
- `server/vwx/patchplan.py` — `build_patch_plan(report, selected=None, dry_run=True)` 리포트 전용
  후보 정규화, 결정적 후보 ID, 항목 단위 선택, 구조화 거부/선택 오류, 드라이런 대상 표 산출.
  M2·M3·M4 산출물인 FID·모드·점유폭·Lua 소스는 추측하지 않고 `None` + `deferred_to_*` 표식으로 둔다.
- `server/tests/test_autopatch_candidates.py` — AC-AUTOPATCH-002·003 전체, AC-AUTOPATCH-004 부분
  비공허 테스트 13건.

**AC 판정**:

- AC-AUTOPATCH-002: PASS. `test_candidates_are_derived_only_from_missing_in_console_without_new_reads`,
  `test_reader_and_console_recorders_are_nonvacuous_on_a_phase_one_control_path`,
  `test_diffs_not_performed_is_rejected_with_the_report_reason_quoted`,
  `test_multi_system_mapping_absent_skip_rejects_as_structured_payload`로 검증.
- AC-AUTOPATCH-003: PASS. `test_candidate_ids_are_stable_for_the_same_report_payload`,
  `test_default_selection_has_zero_targets_and_explicit_selection_targets_only_that_item`,
  `test_unknown_candidate_id_is_reported_as_an_error_not_silently_ignored`로 검증.
- AC-AUTOPATCH-004: PARTIAL. `dry_run` 생략 기본값, 대상 표 필수 열, `address_basis` 전제 문구,
  비가역 경고는 `test_dry_run_is_the_default_and_target_table_carries_required_unresolved_columns`,
  `test_absolute_back_calculated_basis_reuses_phase_one_premise_note`,
  `test_direct_address_basis_does_not_emit_the_back_calculation_note`,
  `test_irreversible_warning_is_present_and_the_absence_checker_is_nonvacuous`로 검증. Lua 소스 전문은
  `server/vwx/luagen.py`가 M4 산출물이고 주소 계획이 `ASSUMPTION-72` 판정에 의존하므로 M1에서
  완결 주장하지 않는다.

**비공허성 대조군**:

- 도면 재판독 0건: planner 호출에서 `RecordingDrawingReader.calls == []`를 assert했고,
  대조군 `exercise_phase_one_recorders()`에서 같은 기록기가 1건을 잡음을 assert.
- 실측 호출 0건: planner 호출에서 `RecordingConsolePort.state_calls/property_calls == []`를 assert했고,
  대조군에서 `read_inventory()` 경유 호출 기록이 실제로 생김을 assert.
- 기본 비선택 0건: `selected` 생략 시 `targets == []`를 assert했고, 특정 ID 1건 선택 시 정확히
  그 1건만 대상이 됨을 같은 테스트에서 assert.
- 비가역 경고 부재 검출: 결과 payload에서 warning을 제거한 사본을 검사해 `AssertionError`가
  실제로 발생함을 `with pytest.raises(AssertionError)`로 assert.

**실측 결과**:

| command | result |
|---|---|
| `uv run pytest server/tests/test_autopatch_candidates.py -q` | `13 passed in 0.06s` |
| `uv run pytest server/tests -q` | `4911 passed, 7 skipped, 1 warning in 91.81s` |
| `uv run ruff check server/vwx server/tests/test_autopatch_candidates.py` | `All checks passed!` |
| `git diff --stat -- console/lua server/safety server/prechk server/paperwork server/looks` | 빈 출력(PRESERVE 0-diff) |
| `uv run python -c '...build_patch_plan(report, selected=[candidate_id])...'` | `{'ok': True, 'dry_run': True, 'target_count': 1, 'lua_source': None, 'warnings': 1}` |

### M0 라이브 세션 1차 — 읽기 프로브 3건 판정 (2026-08-06, 오케스트레이터 직접 실측)

**세션 성립.** onPC를 기동하자 이전 세션의 OSC 설정이 유지되어 responder 왕복이 즉시 성립했다 —
직전 checkpoint의 BLOCKED 사유(프로브 timeout)는 **콘솔 미기동**이 원인이었고 설정 문제가 아니었다.

```
uv run python -m server.tools.responder_roundtrip --host 127.0.0.1 --port 8000 \
  --listen-port 9005 --skip-exec --wait 4
  [PASS] ping: ok   live version=1.6.1 plugin=CopilotResponder
  [PASS] state: ok  node={'childCount': 21, 'class': 'Sequences'} children=18
```

**측정 도구**: `tools/console_probe.py`(게이트 하위 M0 전용 프로브, FXLIB·SPATIAL·GROUPGEN M0에서
이미 쓰인 도구). 아래 3건은 **전부 읽기 전용**이며 콘솔에 아무것도 쓰지 않았다.

**responder 버전 드리프트 고지**: 라이브 responder는 **1.6.1**인데 저장소 `console/lua/`는
**1.5.0**이다(299줄 차이). 아래 판정은 **1.6.1 동작에 대한 실측**이다. 저장소 사본이 더 낡았으므로
덮어쓰지 않았고, `console/lua/**`는 본 SPEC의 PRESERVE라 여기서 조정하지 않는다 — 별도 건이다.

#### `GO: ASSUMPTION-71` — FID는 콘솔에서 읽히는 프로퍼티다

**판정 근거가 성립하는 쇼파일이다.** AC-AUTOPATCH-001 ②가 요구한 **슬롯≠FID** 조건을 현재 로드된
쇼파일이 이미 만족한다 — 슬롯 `n` → FID `n+19`가 표본 7개 전부에서 일관된다.

| slot | FID | Patch | FixtureType(표시문자열) | Mode(표시문자열) |
|---|---|---|---|---|
| 1 | 20 | 3.001 | `FixtureType 3` | `2 Mode 2` |
| 2 | 21 | 3.017 | `FixtureType 3` | `2 Mode 2` |
| 3 | 22 | 3.033 | `FixtureType 3` | `2 Mode 2` |
| 4 | 23 | 3.049 | `FixtureType 3` | `2 Mode 2` |
| 5 | 24 | 3.065 | `FixtureType 3` | `2 Mode 2` |
| 9 | 28 | 3.129 | `FixtureType 3` | `2 Mode 2` |
| 14 | 33 | 3.209 | `FixtureType 3` | `2 Mode 2` |

읽기 가능한 프로퍼티 이름: `FID` · `Fid` · `fid` · `No` · `no` — 다섯 이름이 **모두 같은 값 20**을
반환한다(slot 1). `FixtureId`/`FixtureID`는 not readable. `CID`는 readable이나 값이 nil.
`IDType` = `Fixture`.

**부수 성과 — `PROTOCOL.md:319-321`의 미해소 모호성이 해소됐다.** 그 문서는 ASSUMPTION-7 프로브가
읽는 `child.no`가 슬롯인지 FID인지 "responder가 둘을 구별할 수 없다"고 적었다. 슬롯≠FID 쇼파일에서
`no`가 **FID(20)를 반환**하므로 `no`는 슬롯이 아니라 FID다. (본 SPEC은 이 사실을 소비만 하고
`server/prechk/**`·`console/lua/**`를 고치지 않는다 — 둘 다 PRESERVE다.)

**요구에 미치는 영향**: REQ-AUTOPATCH-009의 **충돌 사전검사를 켠다**(GO 분기). 따라서
REQ-AUTOPATCH-026의 `fid_range_visually_confirmed_empty` 강제는 **발동하지 않는다**
(`spec.md` REQ-AUTOPATCH-026 마지막 문장 — GO 분기에서는 요구하지 않는다).

#### `GO(한정): ASSUMPTION-72` — 드릴다운은 되지만 점유폭은 얻지 못한다

**되는 것**: `Patch/FixtureTypes` 열거(3종: `Robin MMX Spot` · `FixtureType 2` ·
`Robin LEDBeam 350`) → 타입 드릴다운(`DMXModes` 자식 존재) → 모드 열거 → 모드 이름 읽기
(`prop:…/DMXModes/1|Name` → `Mode 1`) → `DMXChannels` 자식 수 읽기.

| 타입 | 모드 | `DMXChannels` childCount |
|---|---|---|
| Robin MMX Spot | Mode 1 · 2 · 3 | 29 · 29 · 29 |
| Robin MMX Spot | Mode 4 | 31 |
| Robin LEDBeam 350 | Mode 1 · 2 | 14 · 14 |
| Robin LEDBeam 350 | Mode 3 | 16 |

**안 되는 것 — 그리고 이것이 핵심이다**: `DMXChannels` childCount는 **DMX 점유폭이 아니다.**
실측 반증: 위 표의 패치된 픽스처는 전부 `Robin LEDBeam 350` **Mode 2**(childCount **14**)인데
실제 주소 간격은 **16**이다(`3.001 → 3.017 → 3.033 …`, slot 14가 `3.209 = 1 + 13x16`으로 일관).
**14를 점유폭으로 쓰면 픽스처마다 2채널씩 겹친다** — `design.md` §4 R4가 경고한 주소 계획 붕괴다.

정확한 점유폭 획득 시도, 전부 실패:

| 시도 | 결과 |
|---|---|
| `prop:…/DMXModes/1\|DMXFootprint` | **존재하나 `table: 0x600001b703c0`** — responder 1.6.1이 테이블을 직렬화하지 못한다(`inventory.py:64-72` POINTER_TEXT 사례) |
| `prop:…/DMXModes/1\|Footprint` · `ChannelCount` · `Channels` · `ChannelWidth` · `Width` · `Size` | 전부 `property not readable` |
| `prop:…/DMXChannels/1\|Offset` · `Resolution` | 전부 `property not readable` |
| `state:…/DMXModes/1/DMXFootprint` | `path segment not found` — 프로퍼티이지 자식 객체가 아니다 |
| `prop:…/DMXChannels/1\|DMXBreak` | readable(`1`) — 점유폭과 무관 |

**요구에 미치는 영향**: REQ-AUTOPATCH-014(점유폭 일치 확인)를 **읽기 표면만으로는 충족할 수 없다.**
`plan.md` §A.3의 `ASSUMPTION-72` 부정 처리를 적용한다 — 점유폭 일치 확인 **descope**, 모드 선택은
사용자 확인 단독, 드라이런 표에 "점유폭 미검증" 열 추가. 근본 해결(responder가 `DMXFootprint`
테이블을 직렬화)은 `console/lua/**` 변경이 필요하고 그것은 본 SPEC의 PRESERVE이므로 **범위 밖**이다.

#### `NEGATIVE: ASSUMPTION-75` — Patch 편집기 상태는 감지되지 않는다

객체 트리를 전수 열거해 편집기/윈도우/커맨드 목적지를 노출하는 객체를 찾았으나 **0건**이다.

| 열거한 경로 | 자식 |
|---|---|
| `Root` | MessageCenter · StationSettings · Interfaces · KeyRegistry · MAnetSocket · Cloud · NDI · UsbNotifier · WebServer · VirtualKeys · HardwareConfigurations · KeyboardLayouts · ShowData · TimecodeSlots |
| `ShowData` | ShowSettings · MediaPools · Scribbles · Appearances · Tags · GelPools · Meshes · RDMData · LivePatch · Patch · PsrPatch · Output · Masters · DataPools |
| `Patch` | DmxCurves · AttributeDefinitions · Layers · Classes · PsrExtraData · FixtureTypes · Stages · UIChannels · RTChannels · IDTypes · DmxUniverses · DmxAddresses · FixtureTypesOverview · PatchFilter |
| `ShowData/ShowSettings` | DefaultPlaybackSettings · GlobalSettings · MidiSettings · SoundSettings · TimecodeStatuses · GlobalVariables · AddonVariables · ShowMetaData · ShowDeletedData · ScreenEncoder |
| `ShowData/DataPools` | Default · Preview |

보조 확인: `orca computer list-windows --app grandMA3` → `windows: []`,
`get-app-state` → `window_not_found`. grandMA3는 접근성 API에 창을 노출하지 않아 **GUI 관측 경로도
없다.** `ChangeDestination`/`CD` 전송은 룰북이 무조건 금지하므로 시도하지 않았다.

**요구에 미치는 영향**: `plan.md` §A.3대로 **사전 안내를 포기하고 사후 안내만** 한다 —
REQ-AUTOPATCH-024가 이미 그 경로("생성 0건이면 Patch > Fixtures 편집기를 먼저 열라")를 규정한다.

#### 미판정 2건 — 파괴적 측정, 쇼파일 확인 대기

`ASSUMPTION-73`(다중 유니버스 `patch` 배열) · `ASSUMPTION-74`(패치 직후 관측)는 **AddFixtures 실제
쓰기**를 요구한다. 현재 로드된 쇼파일은 **픽스처 39대가 패치된 리그**이며(`Patch/Stages/1/Fixtures`
childCount = 39), 이름을 읽을 수 있는 경로가 없다(`ShowData|ShowName`·`ShowFileName` 둘 다
not readable, `ShowMetaData` childCount 0). **테스트 쇼파일임이 확인되지 않았다.**

`plan.md` §C는 "세션 시작 전 사용자에게 쇼파일이 테스트용임을 확인받고 그 확인을 `progress.md`에
기록한다"를 요구한다. 그 확인은 오케스트레이터가 자체 발급할 수 없다 — **73·74는 확인 전까지
미판정으로 남긴다.** 운영 쇼파일로 대체하지 않는다(`plan.md` §B M0 진입 전제 D6).

#### 후속 마일스톤 확정 사항

| 마일스톤 | M0가 확정한 것 |
|---|---|
| M2 | **충돌 사전검사 ON**(ASSUMPTION-71 GO). REQ-AUTOPATCH-026 확인 필드 강제 **미발동**. `FID` 프로퍼티명으로 읽는다 |
| M3 | **점유폭 일치 확인 descope**(ASSUMPTION-72 한정). 드라이런 표에 "점유폭 미검증" 열 추가. 모드 이름은 `DMXModes/<i>` 열거 + `Name` 프로퍼티로 확정 |
| M6 | 사전 안내 없음, **사후 안내만**(ASSUMPTION-75 NEGATIVE) |
| M4·M5 | ASSUMPTION-73·74 미판정이라 **주소 배열 형태와 검증 읽기 재시도 정책이 아직 확정되지 않았다** |

### M2 — FID 배정 (완료)

**상태: COMPLETE — FID 배정은 사용자 `fid_range` 안에서만 수행하며, `ASSUMPTION-71` 런타임 입력에
따라 GO 분기는 `FID` 프로퍼티 충돌 사전검사를 수행하고 부정/INCONCLUSIVE 분기는 구조화된 축소와
`fid_range_visually_confirmed_empty` 별도 확인을 요구한다.** M1 호환을 위해 `fid_range`나
`assumption_71` 등 M2 표면이 주입되지 않은 기존 `build_patch_plan()` 호출은 M1의 `deferred_to_m2`
산출을 유지한다.

**TDD RED 증거**: `uv run pytest server/tests/test_autopatch_fid.py -q` →
`ImportError: cannot import name 'ASSUMPTION_71_GO' from 'server.vwx.patchplan'`, `1 error in 0.06s`.

**구현 산출**:

- `server/vwx/patchplan.py` — `fid_range` 파라미터, `ASSUMPTION_71_*` 런타임 분기, 순차 FID 배정,
  범위 초과/기존 FID 충돌 건별 제외, `FID` 프로퍼티 기반 기존 FID 읽기, 안전망/축소/확인 감사 payload.
- `server/vwx/verdicts.py` — FID 범위 거부, 대상 제외, skipped-check 닫힌 어휘와 라벨 추가.
- `server/tests/test_autopatch_fid.py` — AC-AUTOPATCH-005·006·007·008·027 인메모리 더블 기반 9건.

**AC 판정**:

| AC | 판정 근거 | 실측 명령 · 결과 |
|---|---|---|
| AC-AUTOPATCH-005 | `test_fids_stay_inside_user_range_and_excess_targets_are_reported` — FID 100·101만 배정, 3번째 항목은 `fid_range_exhausted` 제외, 같은 입력/범위 재호출도 같은 배정 | `uv run pytest server/tests/test_autopatch_fid.py -q` → `9 passed in 0.07s` |
| AC-AUTOPATCH-006 | `test_missing_fid_range_rejects_m2_and_does_not_guess_from_slots` — M2 표면에서 `fid_range` 부재 시 `fid_range_required` 거부, `start`·`end` 입력 안내, 배정 0건 | 동 |
| AC-AUTOPATCH-007 | `test_fid_assignment_source_does_not_read_fixture_record_slot`, `test_unresolved_fid_note_is_not_assignment_basis_and_no_fixture_selection_is_generated` — `patchplan.py` AST에서 `.slot`/`'slot'` 참조 0건, `fid_note`의 `999 (미확정)` 대신 범위 FID 100 배정, payload 내 `Fixture <n>` 선택 명령 0건 | 동 |
| AC-AUTOPATCH-008 | `test_go_branch_reads_fid_property_and_excludes_existing_fid_collisions`, `test_negative_branch_skips_precheck_structurally_and_lists_all_assignments` — GO는 `Patch/Stages/1/Fixtures/<i>`에서 `FID`만 읽고 기존 100 충돌 항목 제외, 부정은 포트를 호출하지 않고 `fid_conflict_precheck_descope`를 `skipped_checks`에 기록, 양쪽 모두 대상별 FID 표를 산출 | 동 |
| AC-AUTOPATCH-027 | `test_negative_or_inconclusive_execution_requires_separate_visual_empty_confirmation`, `test_visual_confirmation_is_independent_and_audited_when_present` — 부정/INCONCLUSIVE에서 확인 필드 누락·거짓 거부, GO는 필드 없이 통과, 부정+확인 참은 통과하고 건별 row에 확인 사실 기록 | 동 |

**비공허성 대조군**:

- 추정 배정 로직: `FixtureRecord(slot=41)`에서 `slot+1` 추정 FID 42를 심은 payload를
  `assert_no_fid_assignments()`에 통과시켜 `AssertionError`가 실제 발생함을 확인.
- 슬롯 참조 AST: 가짜 소스 `record.slot`과 `row['slot']`를 `ast` 스캐너에 넣어 검출되는 대조군 확인.
- GO vs 부정 확인필드: 같은 입력에서 GO는 `fid_range_visually_confirmed_empty` 없이 통과하고,
  부정은 같은 필드 누락 시 거부되며 참일 때만 통과함을 확인.

**M0 GO 판정 소비**: `ASSUMPTION-71`은 GO로 소비해 충돌 사전검사 ON이 기본 분기이며, 기존 FID는
정규 프로퍼티명 `FID`로만 읽는다. 부정/INCONCLUSIVE 분기도 런타임 입력으로 구현·테스트했다.

**실측 결과**:

| command | result |
|---|---|
| `uv run pytest server/tests/test_autopatch_fid.py -q` | `9 passed in 0.07s` |
| `uv run pytest server/tests/test_autopatch_candidates.py -q` | `13 passed in 0.06s` |
| `uv run pytest server/tests -q` | `4920 passed, 7 skipped, 1 warning in 91.78s` |
| `uv run ruff check server/vwx server/tests/test_autopatch_*.py` | `All checks passed!` |
| `git diff --stat -- console/lua server/safety server/prechk server/paperwork server/looks` | 빈 출력(PRESERVE 0-diff) |
| 인메모리 planner driver | GO: 기존 FID 100 충돌 제외 후 101 배정. 부정: `fid_conflict_precheck_descope` 기록 후 200·201 배정 |

### M3 — FixtureType · DMXMode 해석 (완료)

**상태: COMPLETE — 타입·모드는 `Patch/FixtureTypes` 열거에서만 얻고, 퍼지 매칭 후보는 사람이
확인해야 확정되며, 부재는 항목 단위 하드 스톱이다. 점유폭 일치 확인은 `ASSUMPTION-72` 런타임
입력으로 갈라져 GO 분기는 불일치를 승인 전에 제시하고, 부정/INCONCLUSIVE 분기(= M0 실측이 만든
현실 기본값)는 확인을 descope하고 축소를 건별로 명시한다.**

**TDD RED 증거**: `uv run pytest server/tests/test_autopatch_types.py -q` →
`ModuleNotFoundError: No module named 'server.vwx.typemap'`, `1 error in 0.08s`.

**구현 산출**:

- `server/vwx/typemap.py` — 신규. `Patch/FixtureTypes` → `<t>/DMXModes` → `<m>|Name` →
  `<m>/DMXChannels` 열거·드릴다운, `rig.fuzzy_type_equal` 재사용 퍼지 매칭(새 헬퍼 신설 0건),
  별칭 재사용, 항목 단위 하드 스톱, `ASSUMPTION_72_*` 런타임 분기, `점유폭 미검증` 열을 가진
  `type_table`.
- `server/vwx/verdicts.py` — 어휘 추가: 제외 사유 `fixture_type_not_in_library` ·
  `dmx_mode_not_in_library`, skipped-check `footprint_match_descope` ·
  `fixture_type_library_truncated` · `fixture_type_library_unreadable`, 신규 닫힌 어휘
  `type_resolution_status`(4종) + 라벨.
- `server/tests/test_autopatch_types.py` — 신규 23건. 전부 `RigPort` 관례 더블 기반 인메모리,
  콘솔 접촉 0.

**AC 판정**:

| AC | 판정 근거 | 실측 명령 · 결과 |
|---|---|---|
| AC-AUTOPATCH-009 | ① `test_candidates_come_from_patch_fixture_types_enumeration_not_source_constants` — 첫 state 호출이 `Patch/FixtureTypes`이고 타입·모드 이름이 전부 열거 응답에서 나온다. ② `test_truncated_enumeration_is_reported_and_absence_is_not_asserted` — `truncated: true`면 `library_incomplete` + `fixture_type_library_truncated`이고 하드 스톱 0건, 같은 입력에서 `truncated: false`면 `library_absent` + `fixture_type_not_in_library`로 갈라진다. 열거 실패·모드 열거 실패·모드 열거 절단도 각각 부재 단정이 아님을 별도 3건이 확인 | `uv run pytest server/tests/test_autopatch_types.py -q` → `23 passed in 0.06s` |
| AC-AUTOPATCH-010 | ① `test_string_equality_alone_never_confirms_a_mapping` — 이름이 완전히 같아도 `needs_confirmation`이고 `console_type`은 `None`. ② `test_observed_vw_and_gdtf_names_both_produce_candidates` — `Robe MegaPointe`(VW)와 `Robe Lighting@MegaPointe`(GDTF) 둘 다 콘솔 `MegaPointe` 후보를 만든다. ③ `test_stored_alias_is_reused_and_the_reuse_is_visible_in_the_payload` — 별칭이 있으면 `resolved` + `confirmation_source: type_alias` + `alias_reuse` 행이 남고, 없으면 같은 입력이 `needs_confirmation`. 별칭이 라이브러리에 없는 이름을 가리키면 신뢰하지 않고 하드 스톱(`test_alias_naming_a_type_outside_the_library_is_not_trusted`) | 동 |
| AC-AUTOPATCH-011 | ① `test_only_the_unmatched_item_is_excluded_and_the_rest_proceed` — 2건 중 미대응 1건만 `hard_stops`에 실리고 나머지는 후보 제시로 진행, `ok`는 참(전체 실패 아님). ② `test_hard_stop_reason_names_the_gdtf_import_prerequisite` — 사유에 `GDTF`·`임포트` 포함. ③ `test_no_similar_name_substitute_assignment` — 미대응 항목의 `console_type`이 `None`. 모드 부재는 `dmx_mode_not_in_library`로 별도 하드 스톱 | 동 |
| AC-AUTOPATCH-012 | ① `test_go_branch_presents_the_footprint_mismatch_before_approval` — GO 분기에서 도면 16 vs 콘솔 24 불일치가 `presented_before_approval: true` + `footprint_mismatches` 행으로 나오고 상태가 `resolved`에서 `needs_confirmation`으로 강등된다(승인 전 제시). ② `test_descoped_branch_states_the_reduction_and_adds_the_unverified_column`(negative·inconclusive·기본값 3분기) — `footprint_match_descope`가 `skipped_checks`에 실리고 사유에 `DMXFootprint`·`직렬화`·`DMXChannels`·`14`·`16`이 담기며 `type_table`에 `점유폭 미검증` 열이 생긴다. 채널 수를 못 읽으면 일치로 간주하지 않고 `match: null`로 보고. ③ `test_channel_count_is_never_parsed_out_of_a_display_string` — 표시문자열 `2 Mode 2`의 열거 인덱스는 **3**(선행 숫자 2와 일부러 어긋냄)이고 채널 수는 `DMXChannels` 자식 수 16이다. ④ `test_multicell_eight_cell_mode_is_the_one_selected` — 8셀 장비에서 `Standard`가 아니라 `8 Cell Mode`(인덱스 2, 96ch)가 선택되고 GO 분기 점유폭이 일치한다 | 동 |

**비공허성 대조군 4건 — 전부 실제로 잡혔다**:

| 심은 것 | 스캐너 | 결과 |
|---|---|---|
| 라이브러리 이름 상수 `LIBRARY = "Robin MMX Spot"` · `GDTF = "Robe Lighting@MegaPointe"` | `library_name_constants` (AST 문자열 상수) | 가짜 소스에서 검출됨 · `typemap.py` 실소스는 0건 |
| 동등 확정 `designed.instrument_type == entry.name` · `type_name == "X"` · `any(key == entry.name ...)` | `equality_confirmation_locations` (AST Compare) | 3종 전부 검출됨 · 실소스 0건 |
| 대체 배정 (하드 스톱 행에 `console_type` 주입) | `assert_no_substitute_assignment` | `AssertionError` 발생 확인 |
| 표시문자열 파싱 `int(mode.name.split(' ')[0])` · `re.search(r"(\d+)", name)` | `display_string_parse_locations` | 2종 전부 검출됨 · 실소스 0건 |

**추가 뮤테이션 검증 5건**(테스트가 구현을 실제로 붙잡는지 — 각각 `typemap.py`를 일시 변조 후 복원):

| 뮤테이션 | 결과 |
|---|---|
| 별칭 없이 자동 확정 | 2건 RED |
| 퍼지 매칭을 `==`로 교체 | 4건 RED (AST 스캐너 포함) |
| 절단된 열거에서 부재 단정 | 1건 RED |
| 점유폭 불일치를 조용히 통과 | 1건 RED |
| descope 분기에서도 `DMXChannels` 읽기 | 3건 RED (`ExplodingChannelPort`가 잡음) |

**M0 GO(한정) 판정을 어떻게 소비했는가**: `ASSUMPTION-72`의 드릴다운은 되지만 점유폭은 못 얻는다는
실측을 그대로 반영해, `plan.md` §A.3의 **부정 처리를 현실 기본 분기로 삼았다** — `assumption_72`의
기본값이 `negative`이고 GO는 명시 입력이어야 한다. descope 사유에 근거를 그대로 적는다:
`DMXFootprint`는 responder 표면에서 table 포인터로만 돌아와 직렬화되지 않고, `DMXChannels` 자식
수는 점유폭이 아니다(**실측 14 vs 실제 주소 stride 16**). 근본 해결은 `console/lua/**` 변경이라
본 SPEC의 PRESERVE이며 범위 밖임을 축소 사유 문자열에 명시했다. GO 분기도 함께 구현·테스트했으므로
판정은 컴파일 타임 상수가 아니라 런타임 입력이다(M2의 `ASSUMPTION_71_*`과 같은 패턴).

**범위 경계**: `점유폭 미검증` 열은 M3 산출물인 `typemap`의 `type_table`에 있다. `patchplan`의
`target_table`과의 병합은 주소 계획을 소유하는 **M4**의 일이다 — 본 마일스톤은 `patchplan.py` ·
`server/orchestrator/tools.py`를 건드리지 않았고 `luagen.py`도 만들지 않았다.

**실측 결과**:

| command | result |
|---|---|
| `uv run pytest server/tests/test_autopatch_types.py -q` | `23 passed in 0.06s` |
| `uv run pytest server/tests/test_autopatch_candidates.py server/tests/test_autopatch_fid.py -q` | `22 passed in 0.10s` (M1·M2 회귀 0) |
| `uv run pytest server/tests -q` | `4943 passed, 7 skipped, 1 warning in 91.23s` (직전 baseline 4920 + 신규 23, 회귀 0) |
| `uv run ruff check server/vwx server/tests/test_autopatch_*.py` | `All checks passed!` |
| `git diff --stat -- console/lua server/safety server/prechk server/paperwork server/looks` | 빈 출력(PRESERVE 0-diff) |
| `uv run pytest server/tests/test_architecture.py -q` | `4 passed` (`server.bridge`·`pythonosc` 미import 경계 유지) |

**미검증 잔여**: 콘솔 접촉 0건이므로 본 마일스톤의 모든 판정은 **더블 기반**이다. 실기에서
`Patch/FixtureTypes` 열거가 대형 쇼파일에서 절단되는 실제 임계, 별칭 표의 영속화 위치,
GO 분기를 켤 수 있는 점유폭 출처(=responder 확장)는 전부 미해결이며 M8/별건 대상이다.

### M4 — Lua 생성기 + 주소 계획 (완료)

**상태: COMPLETE — `AddFixtures` 호출은 룰북 필드 집합만으로 생성되고, 목적지 변경 명령은
생성 어휘에 존재하지 않으며, 주소는 도면 값을 그대로 쓰되 겹치는 항목은 재배치 없이 제외된다.**
`plan_status: audit-ready`(round10 PASS) 위에서 착수했다.

**AC**: AC-AUTOPATCH-013 · AC-AUTOPATCH-014 · AC-AUTOPATCH-016 (`acceptance.md` §C.0a M4 = 3건)

**테스트**: **4,943 → 4,981 passed / 7 skipped (+38, 회귀 0)** ·
`ruff check` OK · `ruff format --check` 15 files already formatted.

#### 산출물

| 파일 | 신규/변경 | 역할 |
|---|---|---|
| `server/vwx/luagen.py` | **신규** | `AddFixtures` Lua 생성. 공개 API는 `LuaPatchEntry` + 렌더 2종뿐 |
| `server/vwx/patchplan.py` | 변경 | `AddressPlanEntry` · `AddressPlan` · `plan_addresses` 추가 |
| `server/vwx/verdicts.py` | 변경 | 제외 사유 3종 등재(`address_already_occupied` · `address_overlap_in_plan` · `footprint_unknown`) |
| `server/tests/test_autopatch_lua.py` | **신규** | 38건 |

#### 설계 결정 — 금지를 검사가 아니라 어휘로 둔다 (REQ-AUTOPATCH-017 · design.md §5 슬롯 C)

`luagen.py`가 만들 수 있는 Lua는 `AddFixtures` 호출 **하나뿐**이다. 목적지를 옮기는 문장을
조립하는 함수도, 자유 문자열을 본문에 실어 보낼 파라미터도 **없다.** 이것을 두 기법으로 못박았다:

- **AST**(AC-014③(a)) — 모듈 전체에 그 토큰을 담은 **문자열 리터럴 0건**.
- **시그니처**(AC-014③(b)) — 공개 함수는 `entry` / `entries` 하나씩만 받고 `*args`·`**kwargs`·
  키워드 전용 인자가 **없다**. `LuaPatchEntry`의 필드 집합은 `AddFixtures` 인자에 1:1 대응하는
  6개로 고정이며 `extra_lua`·`prelude`·`raw` 류의 통로가 하나라도 생기면 테스트가 깨진다.

**고지 — 토큰 탐지기를 리터럴 없이 만든 방법**: 생성기 자신이 그 토큰을 **검출**해야 하므로
`"Change" + "Destination"` · `"C" + "D"`로 조각을 런타임에 합쳐 정규식을 만든다. 소스에 완성된
토큰 리터럴이 없으므로 (a) 스캔을 통과하며, **탐지 능력은 산출물 스캐너 테스트가 따로 증명한다**
(가짜 산출물을 넣어 실제로 잡히는지 확인 — AC-014②). 리터럴을 피하기 위한 편법이 아니라
"모듈에 그 문장이 없다"와 "그 문장을 잡아낸다"를 **동시에** 만족시키는 유일한 방법이다.

#### 적대적 이름을 어떻게 처리했는가 — **거부**한다

`name`은 설계상 Lua 본문에 들어가야 하는 필드이므로 "자유 문자열 도달 0건"을 부재로 닫을 수 없다.
**인코더 통과 강제**로 닫았다(`_lua_string`이 유일한 통로: 따옴표·역슬래시·제어문자 이스케이프,
한 줄 유지). 적대적 입력 8종으로 **키 주입이 불가능**함을 확인했다.

그런데 이름이 그 토큰을 담으면 문제가 다르다 — 통과시키면 **AC-014①의 산출물 토큰 스캐너가
거짓 양성을 내 게이트가 강제력을 잃고**, 조용히 고치면 **자동 보정 금지**를 어긴다.
그래서 **`LuaGenerationError`로 거부**하고 항목 제외 결정을 호출자(M5)에게 넘긴다.
거부가 공허하지 않음을 정상 이름 통과로 함께 확인했다.

#### 주소 계획 — M0 함정 7이 설계를 결정했다

**점유폭을 콘솔에서 읽지 않는다.** `DMXChannels` childCount는 점유폭이 아니고(**실측 14 vs
실제 stride 16**) `DMXFootprint`는 직렬화되지 않는다. 그래서 `plan_addresses`는 폭을
**1단계 도면이 준 값**으로만 받고, **모르면 추측하지 않고 `footprint_unknown`으로 제외**한다.
"폭도 간격도 상수로 두지 않는다"(`SPEC-COPILOT-OVERLAP-001`의 42 교훈)를 그대로 지킨다.

**재배치 경로가 함수에 없다**(AC-016③). 살아남은 항목의 주소는 **언제나 도면 주소**이고,
겹치는 항목은 **제외**된다 — 빈 주소를 찾아 옮겨 붙이는 것은 사람이 결정할 일이다
(design.md §7 안티패턴 7). 점유 판정은 **시작 주소가 아니라 점유폭 구간 전체**로 한다.

#### 스모크 — 테스트가 아니라 실물 산출물로 확인했다

도면 5대(콘솔 U1 95~120 점유, 1건 폭 미확정, 1건 계획 내 겹침) 입력:

```
계획: a: U1 1..16(폭 16) · b: U1 17..32(폭 16)
제외: c 도면 주소가 콘솔에서 이미 점유됨 (100~115 vs 95~120)
      d 같은 유니버스 안에서 다른 계획 항목과 점유 구간이 겹침 (24~39 vs b의 17..32)
      e 점유폭 미확정 — 추측하지 않고 제외
```

```lua
local function main()
  AddFixtures({ mode = Patch().FixtureTypes["Robin LEDBeam 350"].DMXModes["Mode 1"], amount = 1, fid = "101", idtype = "Fixture", name = "LEDBeam 101", patch = { "1.1" } })
  AddFixtures({ mode = Patch().FixtureTypes["Robin LEDBeam 350"].DMXModes["Mode 1"], amount = 1, fid = "102", idtype = "Fixture", name = "LEDBeam 102", patch = { "1.17" } })
end

return main
```

목적지 명령 토큰 **0건** · 적대적 이름 **거부 확인**. 도면 주소(1·17)가 그대로 유지됐고
제외된 3건은 다른 주소로 옮겨 붙지 않았다.

**중요 — 이 Lua는 이 빌드에서 픽스처를 만들지 못한다.** M0가 확정한 대로 `AddFixtures`가
서버 자동 실행으로 성립하지 않기 때문이다. M4의 산출물은 **사람이 콘솔에서 실행할 검토용
소스**이며(v0.1.3 반자동 모델, REQ-AUTOPATCH-018) 그 전달과 검증이 M5·M6의 일이다.

#### 범위 경계

`server/orchestrator/tools.py` 무접촉(툴 배선은 M7) · 실행·배포 코드 0건(M5) ·
검증 읽기 0건(M6) · PRESERVE 5경로 무접촉.

**실측 결과**:

| command | result |
|---|---|
| `uv run pytest server/tests/test_autopatch_lua.py -q` | `38 passed in 0.05s` |
| `uv run pytest server/tests -q` | `4981 passed, 7 skipped, 1 warning in 90.30s` (직전 baseline 4943 + 신규 38, **회귀 0**) |
| `uv run ruff check server/vwx server/tests/test_autopatch_*.py` | `OK` |
| `uv run ruff format --check server/vwx server/tests/test_autopatch_*.py` | `15 files already formatted` |
| `git diff --stat ca00bc5..HEAD -- console/lua server/safety server/prechk server/paperwork server/looks` | 빈 출력(PRESERVE 0-diff) |
| 스모크(실물 렌더) | 계획 2건 · 제외 3건(사유 3종) · 목적지 토큰 0건 · 적대적 이름 거부 |

**착수 시 실패 확인(TDD RED)**: `uv run pytest server/tests/test_autopatch_lua.py -q` →
`ModuleNotFoundError: No module named 'server.vwx.luagen'` · `1 error in 0.06s`.

**미검증 잔여**: 콘솔 접촉 0건이므로 본 마일스톤의 판정은 전부 **더블·문자열 검사 기반**이다.
생성된 Lua가 **실기에서 픽스처를 만드는지는 이 빌드에서 확인할 수 없다**(M0 NEGATIVE) —
사람이 실행하는 경로의 종단 확인은 **M8**이며, 그 M8은 사람 실행 단계를 포함하도록 재정의가 필요하다.
점유폭 출처(도면 값)의 정확성은 1단계 산출물 품질에 의존하며 본 SPEC이 재판독하지 않는다.

### M5 — 실행 전달(사람) · 검증 인계 (완료)

**상태: COMPLETE — 서버는 검토용 Lua 소스와 실행 절차를 사람에게 넘기는 데서 멈춘다.
`RecordingExecutionPort`에 도달한 발화는 승인 여부와 무관하게 0건이며, 그 0건은
발화·쓰기·우회 배포를 되살려 심은 사본이 같은 기록기에 실제로 잡히는 것으로 닫혔다.**
M4 완료(`plan_status: audit-ready`, round10 PASS) 위에서 착수했다.

**AC**: AC-AUTOPATCH-015 · 017 · 018 · 019 (`acceptance.md` §C.0a M5 = 4건)

**테스트**: **4,981 → 5,044 passed / 7 skipped (+63, 회귀 0)** ·
`ruff check` OK · `ruff format --check` 17 files already formatted.

#### 산출물

| 파일 | 신규/변경 | 역할 |
|---|---|---|
| `server/vwx/apply.py` | **신규** | 전달물 조립(`build_patch_handoff`). 공개 API는 `HandoffEntry`·`PatchHandoff`·진입점 1개 |
| `server/vwx/verdicts.py` | 변경 | 제외 사유 4종 등재(`fid_not_assigned`·`fixture_name_missing`·`type_confirmation_pending`·`lua_generation_refused`) |
| `server/tests/test_autopatch_execute.py` | **신규** | 63건 |

#### [핵심] "발화 0건"을 어떻게 비공허하게 만들었나

`apply.py`는 실행 포트를 **인자로 받지도 import하지도 않는다.** 그래서 "기록기에 0건"을 그냥
주장하면 **기록기를 아무것도 볼 수 없는 자리에 놓았을 뿐**일 수 있다 — 그 공허함이 이 마일스톤의
진짜 난점이었다. 다음 하네스로 닫았다:

```
① server.bridge 를 기록기(RecordingExecutionPort · RecordingDeployPipeline)를 담은
   가짜 모듈로 sys.modules 에 꽂는다.
   — 그 표면이 "콘솔로 나가는 유일한 문"임은 test_architecture.py 의
     _FORBIDDEN_MODULE_PREFIXES = ("server.bridge", "pythonosc") 가 이미 강제한다.
② 같은 하네스 · 같은 기록기 · 같은 진입점으로 두 소스를 돌린다 —
   원본 소스, 그리고 발화/쓰기/우회 배포를 되살려 심은 사본.
③ 사본에서 기록기가 실제로 잡는 것을 보인 뒤에만 원본의 0건을 인수한다.
```

대조군 실측(사본에서 **잡혔다**):

| 심은 것 | 기록기가 잡은 것 | AC |
|---|---|---|
| 전달 후 플러그인 실행 발화 | `port.executed == ["Plugin 'VWX AddFixtures'"]` | 015② |
| 전달 전 콘솔 쓰기 | `port.executed == ["Store Fixture 101"]` | 019② |
| 우회 배포 호출 | `pipeline.deployed == [("VWX AddFixtures", …)]` | 017① |
| `execution_port.execute` 직접 호출 | AST 스캐너가 속성 대상 `execution_port` 검출 | 018② |
| `from server.bridge import …` | import 스캐너가 `server.bridge` 검출 | 018③ |
| `dry_run` 기본값을 `False`로 | 기본값 단정이 실제로 뒤집힘 | 019③ |
| `delivered = True`로 승격 | 드라이런 호출이 `delivered=True`가 됨 | 019④ |
| 전달 후 자동 재시도 | 렌더 호출 계수 1 → **2** | 019⑤ |
| 리뷰 우회 인자 `skip_review` | 시그니처 스캔이 검출 | 017② |

원본에서는 **드라이런·전달 요청 두 모드 모두** `port.executed == []` · `pipeline.deployed == []`다.

#### 설계 결정 — 승인이 있어도 실행 분기가 조립되지 않는다

`luagen`이 목적지 명령을 **어휘에서 없앤** 것과 같은 기법이다(design.md §5 슬롯 C).
`apply.py`에는 발화할 대상 자체가 없으므로 "승인이 있으면 서버가 실행한다"는 분기를
**쓸 수가 없다** — 사후 검사로 막는 것이 아니다. AC-015③("승인 여부와 무관")이
`dry_run` 두 값 모두에 대한 파라미터화 테스트로 닫힌 이유가 이것이다.

**드라이런과 전달의 차이는 한 줄(`delivered = not dry_run`)이다.** 드라이런도 **Lua 소스 전문을
낸다**(REQ-AUTOPATCH-003 · AC-004②, round9 N42가 철회시킨 그 요구를 지킨다) — 두 모드의
`lua_source`가 **동일함을 테스트가 직접 대조**한다. 달라지는 것은 **실행 절차와 검증 인계**뿐이다.

#### 실행 절차에 무엇을 적었고 무엇을 적지 않았나

적은 것은 **실측으로 확정된 것뿐**이다(§0 항목 4·9, 함정 9·11):
라이브러리 파일 저장 → `Import Plugin '<파일명>'`(**`deploy` 동사 금지** — 이 빌드에서 소스가
써지지 않고 객체만 생긴다) → **재임포트 캐싱 주의**(새 이름 또는 슬롯 비우기) → 사람이 실행 →
서버에 검증 읽기 요청.

**적지 않은 것**: 룰북의 *"Patch > Fixtures 편집기를 먼저 열라"* 는 `ASSUMPTION-75` NEGATIVE로
근거를 잃었고, 목적지 이동 처방은 5차에서 반증됐다. **틀린 원인을 사용자에게 안내하지 않는다**
(REQ-AUTOPATCH-024 [v0.1.3]). 그 부재를 테스트가 직접 단정한다.

경고 3종을 전달물에 싣는다: 비가역성(`IRREVERSIBLE_WARNING`) · **플러그인 무오류 종료는 성공이
아니다**(함정 4) · **이 절차의 종단 성공은 이 빌드에서 미확인**(정직 고지 — M8).

#### M4 계약 3건을 어떻게 지켰나 (§0 항목 2a)

| 계약 | M5의 준수 |
|---|---|
| ① 자유 Lua 파라미터 추가 금지 | 진입점 파라미터는 `targets`·`address_plan`·`resolutions`·`names`·`dry_run` **5개뿐**이고 Lua 본문에 닿는 통로는 `LuaPatchEntry` 6필드가 전부다. 시그니처 전수 단정 테스트로 못박았다 |
| ② `LuaGenerationError`는 항목 제외 + 사유 보고 | `render_addfixtures_call`로 **항목별 사전 검증**하고 예외를 잡아 `lua_generation_refused`로 제외한다. 조용히 고치지 않는다 |
| ③ `footprints`는 도면 값만 | M5는 폭을 **계산하지도 읽지도 않는다** — `AddressPlanEntry.footprint`를 그대로 표에 옮길 뿐이다 |

**②에서 실제로 걸린 것 하나**: 처음에 제외 사유에 `LuaGenerationError` 메시지를 그대로 실었더니
**거부된 이름이 페이로드에 되실려** 산출물 스캐너가 목적지 토큰을 검출했다 — AC-014①이 거짓
양성으로 강제력을 잃는 바로 그 경로다. 사유에서 **입력을 되싣지 않도록** 고쳤고, 그 부재를
`test_the_refused_name_is_not_silently_repaired`가 지킨다.

#### 제외 사유 4종 신설 — 왜 필요했나

"항목 제외 + 사유 보고"는 닫힌 어휘로만 보고된다(design.md §5 슬롯 B). M5가 처음 만드는
제외 사유 4종을 `server/vwx/verdicts.py`에 등재했다 — `fid_not_assigned` ·
`fixture_name_missing`(**이름을 지어내지 않는다**) · `type_confirmation_pending`(R2 — 확인이
남은 타입 매칭으로 되돌릴 수 없는 쓰기를 만들지 않는다) · `lua_generation_refused`.
`server/prechk/verdicts.py`는 PRESERVE이므로 건드리지 않았다.

#### 스모크 — 테스트가 아니라 실물 산출물로 확인했다

도면 6대(U1 95~120 콘솔 점유 · 1건 폭 미확정 · 1건 계획 내 겹침 · 1건 이름에 목적지 토큰) 입력:

```
dry_run=True   delivered=False  next_step=review_dry_run                    procedure 0줄
dry_run=False  delivered=True   next_step=human_execution_then_verification_read  procedure 5줄
두 모드의 lua_source 동일

전달: a(FID 101, U1.1) · b(FID 102, U1.17)
제외: c 도면 주소가 콘솔에서 이미 점유됨
      d 같은 유니버스 안에서 다른 계획 항목과 점유 구간이 겹침
      e 점유폭 미확정 — 추측하지 않고 제외
      f Lua 생성기가 이름을 거부 — 조용히 고치지 않고 제외
페이로드 전문 목적지 토큰 0건
```

#### 범위 경계

`server/orchestrator/tools.py` 무접촉(툴 배선은 M7) · 멱등 재조회·검증 읽기 0건(M6) ·
콘솔 접촉 0건 · PRESERVE 5경로 무접촉.

**실측 결과**:

| command | result |
|---|---|
| `uv run pytest server/tests/test_autopatch_execute.py -q` | `63 passed in 0.08s` |
| `uv run pytest server/tests -q` | `5044 passed, 7 skipped, 1 warning in 91.37s` (직전 baseline 4981 + 신규 63, **회귀 0**) |
| `uv run ruff check server/vwx server/tests/test_autopatch_*.py` | `OK` |
| `uv run ruff format --check server/vwx server/tests/test_autopatch_*.py` | `17 files already formatted` |
| `git diff --stat ca00bc5..HEAD -- console/lua server/safety server/prechk server/paperwork server/looks` | 빈 출력(PRESERVE 0-diff) |
| 스모크(실물 전달물) | 전달 2건 · 제외 4건(사유 4종) · 두 모드 소스 동일 · 목적지 토큰 0건 |

**착수 시 실패 확인(TDD RED)**: `uv run pytest server/tests/test_autopatch_execute.py -q` →
`ModuleNotFoundError: No module named 'server.vwx.apply'` · `1 error in 0.06s`.

**미검증 잔여**:
- 콘솔 접촉 0건이므로 본 마일스톤의 판정은 전부 **더블·AST·소스 사본 기반**이다.
  **사람이 실행하는 경로가 실제로 픽스처를 만드는지는 여전히 미확인**이다 — 서버 자동 실행은
  10경로 전부 0건이었고(M0), 사람 실행 종단 확인은 **M8**이다. 전달물의 경고 3번이 이 사실을
  사용자에게 그대로 고지한다.
- `RecordingExecutionPort` 하네스는 **`server.bridge`를 콘솔 도달의 유일한 문**으로 전제한다.
  그 전제 자체는 `test_architecture.py`의 단일 초크포인트 경계가 강제하며, 본 마일스톤이
  새로 증명한 것이 아니라 **승계한 것**이다.
- **M7이 갚아야 할 빚**: `PatchPlan.to_dict()`가 아직 `lua_source: None` ·
  `lua_source_unresolved_reason: deferred_to_m4`를 낸다(`patchplan.py:326-327`). M4·M5가 끝난
  지금 그 마커는 "이 계층이 아직 배선되지 않았다"는 뜻으로만 참이다 —
  `deferred_to_m2`·`deferred_to_m3`와 같은 처지이며, **셋을 함께 해소하는 것은 M7 배선의 일**이다.
  M5가 단독으로 이름만 바꾸면 어휘가 세 벌로 어긋난다.


### M0 라이브 세션 2차 — 테스트 쇼파일 확인 · 파괴적 측정 착수 전 기록 (2026-08-06)

#### 사용자 확인 (`plan.md` §C 요구사항)

`plan.md` §C는 "세션 시작 전 사용자에게 쇼파일이 테스트용임을 확인받고, 그 확인을 `progress.md`에
기록한다"를 요구한다. **본 절이 그 기록이며, 파괴적 측정보다 앞서 쓰였다.**

| 항목 | 값 |
|---|---|
| 쇼파일 | `NewShow_2026.07.15_05.44.02UTC` (onPC 2.4.2.2 타이틀바, 사용자 스크린샷) |
| 사용자 확인 | **"그냥 이 쇼파일을 사용해도 될거 같아"** — 테스트용 사용 승인 (2026-08-06) |
| 오케스트레이터가 만든 것인가 | **아니다.** 본 세션은 콘솔 쓰기 0이었고 쇼파일 생성·로드도 하지 않았다. onPC 기동 시 이미 열려 있었다 |

**확인을 뒷받침하는 콘솔 실측 근거**(추론이 아니라 관측):

| 근거 | 관측값 |
|---|---|
| Plugins 풀 | `CopilotResponder` · `CopilotBusk`(BUSKWIZ 산출물) · `kpop_summer_twinkle` · `GenSequence100Look` — **4개 전부 본 프로젝트 생성물** |
| Macros 풀 | `Copilot Go` 1건 — 본 프로젝트 매크로 |
| 이름 형식 | `NewShow_<UTC타임스탬프>` = MA3가 새 쇼에 붙이는 기본명 |
| 저장소 교차 | `SPEC-COPILOT-DASHUI-001/progress.md:192`가 당시 **픽스처 19대**로 기록 → 현재 39대. 선행 라이브 세션(MVP·PRECHK·LOOKLIB·EXECBODY·BUSKWIZ·DASHUI) 누적으로 정합 |

운영 쇼파일이라면 `CopilotBusk`·`kpop_summer_twinkle`이 존재할 수 없다.

#### 파괴적 측정 전 사전 상태 (원복 기준선)

| 항목 | 값 |
|---|---|
| `Patch/Stages/1/Fixtures` childCount | **39** |
| 사용 중 FID | **1 … 39** (빈틈 0) |
| 사용 중 유니버스 | **1 · 2 · 3** |
| U1 주소 범위 | 1 … 437 (n=10) |
| U2 주소 범위 | 1 … 401 (n=9) |
| U3 주소 범위 | 1 … 305 (n=20) |

**테스트 자원은 기존과 완전히 분리한다** — FID `501`~`503`(기존 최대 39보다 훨씬 위),
유니버스 `10`·`11`(둘 다 미사용). 충돌 가능성 0.

#### `ASSUMPTION-71` 근거 보강 — 슬롯↔FID에 고정점이 없다

1차 세션은 표본 7개(slot 1~5·9·14)에서 `slot n → FID n+19`를 관측하고 그렇게 기록했다.
전수 조사 결과 실제 매핑은 **단순 오프셋이 아니라 회전(rotation)** 이다:

| slot | 1 | 20 | 21 | 39 |
|---|---|---|---|---|
| FID | 20 | 39 | 1 | 19 |

슬롯 1~20 → FID 20~39, 슬롯 21~39 → FID 1~19. **고정점(slot == FID)이 하나도 없다.**
1차 기록의 "표본 7개에서 `n+19`"는 그 표본 범위 안에서 정확하며, 전수 확인은 판정을 **강화**한다 —
이 쇼파일의 어떤 픽스처에서 측정해도 FID 프로브와 슬롯 프로브가 구별된다.

#### 파괴적 측정 시도 — `AddFixtures`가 조용히 `nil`을 반환한다 (미판정 유지)

**결과: `ASSUMPTION-73`·`74` 여전히 미판정.** 생성된 픽스처 **0건**(39 → 39 불변).
측정을 3회 시도했고, 실패 지점을 **단계별로 특정**했다. 실패를 성공으로 적지 않으며 판정도 내리지 않는다.

측정 도구: `tools/console_probe.py`(게이트 하위, M0 전용). 플러그인은 `deploy_plugin` 게이트 경로가
아니라 라이브러리 폴더 배치 + `Import Plugin` 경로로 넣었다 — M0 측정은 승인 채널 밖이라는
그 도구의 규약을 따른다.

**시도 1 — 편집기 닫힘 상태**

| 단계 | 결과 |
|---|---|
| `Import Plugin 'autopatch_m0_probe'` | `OK` — 풀 슬롯 5에 `AutopatchM0Probe` 생성 확인 |
| `Plugin 'AutopatchM0Probe'` | `OK` |
| `Patch/Stages/1/Fixtures` 재조회 | **39 → 39. 생성 0건** |

`exec` 결과가 `OK`인데 아무것도 만들어지지 않았다 — **`progress.md` §0 함정 4의 실물 재현이자
REQ-AUTOPATCH-023(검증 읽기가 성공의 유일한 근거)의 라이브 정당화**다. 플러그인 무오류 종료를
성공으로 삼았다면 이 SPEC은 여기서 거짓 성공을 보고했을 것이다.

**시도 2 — 사용자가 Patch > Fixtures 편집기를 연 상태**

룰북 처방(`30_plugin_patterns.md:28-29`)대로 사용자에게 편집기 개방을 요청하고 재실행했다.
결과 **동일 — 39 → 39, 생성 0건.**

**시도 3 — 실패 지점 특정 프로브(v2)**

`AddFixtures`가 왜 실패하는지 단계별로 갈라 각 분기가 플러그인 슬롯 5의 **라벨**에 판정을 쓰게 했다
(응답기가 읽을 수 있는 유일한 출력 채널 — `Printf`는 서버로 돌아오지 않는다).

| 단계 | 결과 |
|---|---|
| `Patch()` | **non-nil** |
| `Patch().FixtureTypes["Robin LEDBeam 350"]` | **해석됨** |
| `.DMXModes["Mode 1"]` | **해석됨** |
| `AddFixtures{...}` | **`nil` 반환** — 예외 아님(`pcall` 통과), 조용한 실패 |

읽어낸 라벨: **`AM0_ADD_NIL`**.

**부수 성과 — `ASSUMPTION-72`의 쓰기측 핸들 경로가 라이브로 확인됐다.**
`Patch().FixtureTypes["<이름>"].DMXModes["<이름>"]`이 실기에서 실제로 핸들을 반환한다
(REQ-AUTOPATCH-016이 요구하는 정확한 형태). 1차 세션의 `GO(한정)` 판정에서 "읽기 표면으로 점유폭을
못 얻는다"는 제약은 그대로이나, **핸들 해석 자체는 이제 미확정이 아니다.**

**배제된 원인**

| 가설 | 반증 |
|---|---|
| 타입 이름 오타 / 핸들 미해석 | 위 표 — 3단계 전부 해석됨 |
| 유니버스 10·11 미구성 | `Patch/DmxUniverses` childCount = **1024**. 10·11 전부 존재 |
| 기존 픽스처와 FID·주소 충돌 | 기존 FID 1~39 · 유니버스 1~3. 프로브는 FID 501~503 · 유니버스 10~11 |
| 예외 발생 | `pcall`이 참을 반환 — 던지지 않고 `nil`을 반환했다 |
| `ChangeDestination` 오염 | 플러그인 소스·명령 어디에도 `CD`/`ChangeDestination` 없음 |

**남은 원인 가설 — command destination의 컨텍스트 분리 (미확정)**

룰북이 지목한 원인은 하나뿐이다: `AddFixtures`는 **현재 command destination**을 읽으며 그것이
patch fixtures 레이어여야 한다. 사용자가 GUI에서 편집기를 열었는데도 OSC 경로가 실패했다는 사실은
**목적지가 세션/컨텍스트별로 분리되어 GUI 조작이 OSC 명령줄의 목적지를 바꾸지 않는다**는 가설을
가리킨다. `ChangeDestination` 전송은 룰북이 무조건 금지하므로 서버측 우회 수단이 없다.

판별 프로브를 콘솔에 배치해 두었다 — 슬롯 6 `AutopatchM0Probe3`을 **GUI에서 직접 탭**하면
GUI 사용자 컨텍스트에서 실행되며, 결과가 슬롯 5 라벨(`AM0 T1 <OK|NIL> T2 <OK|NIL>`)에 기록된다.
**OSC 대조군은 이미 확보했다: `AM0 T1 NIL T2 NIL`.**

#### 이 발견이 위협하는 것 — REQ-AUTOPATCH-018 / M5 실행 경로 (미결, 사용자 결정 대기)

GUI 탭이 성공하고 OSC가 실패한다면, `spec.md` §A 사전 확정 사실 1이 규정한 2단계 실행 경로
(`deploy_plugin` → `run_commands(["Plugin '<이름>'"])`)가 **실기에서 픽스처를 만들지 못한다.**
REQ-AUTOPATCH-018은 그 경로를 요구사항으로 못박고 있고 M5 전체가 그 위에 서 있다.

이 위험은 `spec.md` §C의 ASSUMPTION 71~75 어디에도 없다 — **plan-phase가 놓친 전제**다.
`AddFixtures`가 command destination을 읽는다는 사실은 룰북에 있었으나, "서버가 OSC로 발화한
플러그인 실행이 그 목적지를 갖는가"는 아무도 묻지 않았다.

**오케스트레이터가 임의로 승격하지 않는다.** 이것을 `ASSUMPTION-76`으로 신설하고
REQ-AUTOPATCH-018을 조정하는 것은 plan-phase 아티팩트 개정(amendment)이며 재감사 대상이다.
사용자 결정 항목으로 남긴다.

#### 근본 원인 확정 — command destination이 `TempCmdlines Cmdline 1`이고 옮길 수단이 없다

측정을 계속해 **원인을 특정했다.** 아래는 전부 라이브 실측이다.

**증거 1 — GUI 탭도 동일하게 실패한다(destination 컨텍스트 분리 가설 기각).**
슬롯 5 라벨을 `AM0 WAITING GUI TAP` 센티넬로 두고 사용자가 GUI에서 플러그인을 탭했다.
라벨이 `AM0 T1 NIL T2 NIL`로 **바뀌었다** — 실행은 됐고 결과는 OSC 경로와 **동일**하다.
GUI/OSC 컨텍스트 차이는 원인이 아니다. (부수 효과: 이후 반복 측정을 서버측에서 자유롭게 수행했다.)

**증거 2 — `patch` 배열도 유니버스도 원인이 아니다.**

| 변형 | 결과 |
|---|---|
| `patch` 배열 **생략**(룰북상 optional) | `NIL` |
| 유니버스 **1**(기존 픽스처가 사는 살아있는 유니버스), 빈 주소 `1.461` | `NIL` |

**증거 3 — `AddFixtures`는 컨테이너 메서드가 아니다.**
`Patch().Stages[1].Fixtures`는 `userdata`로 해석되고 `:Count()` = **39**로 정상 동작하나,
`.AddFixtures` 필드는 **nil**이다. 즉 대상을 명시적으로 지정해 호출할 방법이 없고,
**앰비언트 목적지에만 의존하는 전역 함수**다.

**증거 4 — 현재 목적지를 직접 읽었다.**

```
CmdObj() → class = Cmdline · name = 'Cmdline 1' · AddrNative = 'TempCmdlines Cmdline 1'
```

patch fixtures 레이어가 아니라 **임시 명령줄 객체**다. 룰북이 전제한
"`…/Patch/Stages/Stage 1/Fixtures>` 상태"가 플러그인 실행 시점에 성립하지 않는다.

**증거 5 — 목적지를 옮길 Lua API가 존재하지 않는다.** (존재 여부만 조회, 호출 없음)

| 심볼 | 존재 |
|---|---|
| `SetCmdObj` · `SetDestination` · `ChangeDestination`(Lua 전역) | **전부 없음** |
| `CurrentCommandLine()` | **없음**(이 빌드에서 미제공 — 선행 세션의 `CheckDest.xml`이 쓰던 API다) |
| `Patch` · `AddFixtures` · `CmdIndirect` · `CurrentExecPage` | function |
| `Obj` | table |

`CurrentCommandLine().destination`에 컨테이너를 대입하는 비-CD 경로도 시도했으나
`CurrentCommandLine()` 자체가 없어 성립하지 않았다.

**증거 6 — 선행 세션이 같은 벽에 부딪혔다(콘솔 라이브러리 고고학).**
콘솔 플러그인 라이브러리 폴더에 본 세션과 무관한 선행 산물이 남아 있다:
`CheckDest.xml` · `CheckDest2.xml`(목적지 판독 시도) · `patch_here.xml`(CD 없이 현재 목적지로
패치 시도) · `patch_proper.xml` · `PatchMMX.xml` · `patch_order.xml` · `patch_rest.xml`.
`patch_proper.xml`을 디코딩하면 **`Cmd("ChangeDestination " .. Patch():Addr(), undo)`로 목적지를
옮긴 뒤 `AddFixtures`를 부르고 다시 `ChangeDestination Root`로 되돌리는** 구조다
(`CreateUndo`/`CloseUndo` 세션 안에서). 즉 선행 세션도 CD 없이는 성립하지 않는다고 판단해
CD 경로를 만들었다. 그 결과는 이 파일들만으로 알 수 없다.

#### 판정

```
INCONCLUSIVE: ASSUMPTION-73 — 다중 유니버스 patch 배열. AddFixtures가 어떤 인자로도
              실행되지 않아 배열 의미론을 관측할 기회 자체가 없었다.
INCONCLUSIVE: ASSUMPTION-74 — 패치 직후 관측. 생성이 0건이라 관측 대상이 없었다.
```

`plan.md` §A.3의 부정 처리를 적용한다(INCONCLUSIVE는 부정과 동일 취급):
`ASSUMPTION-73` → 유니버스별 분할 실행으로 대체하되 **그 대체안도 미검증**이다.
`ASSUMPTION-74` → 검증 읽기에 재시도 대기를 넣되 미관측 시 "확인 불가" 보고.

**M0 최종: 5건 중 3건 판정(71 GO · 72 GO(한정) · 75 NEGATIVE), 2건 INCONCLUSIVE.**
`plan.md` §B M0 D6에 따라 **M8은 BLOCKED로 남고 SPEC은 완결되지 않는다.**

#### 이것이 무효화하는 plan-phase 전제 — 사용자 결정 필요

`spec.md` §A **"사전 확정 사실 (조사 확정 — 재질의 금지)"** 의 두 항목이 이 빌드에서
**동시에 성립할 수 없다**:

| # | 내용 | 실측 결과 |
|---|---|---|
| 1 | 패치는 정확히 2단계 — `deploy_plugin` → `run_commands(["Plugin '<이름>'"])` | 그 경로로는 목적지가 `TempCmdlines Cmdline 1`이라 **항상 0건 생성** |
| 2 | `ChangeDestination`/`CD`를 **어디에서도** 보내면 안 된다 | 목적지를 옮길 다른 수단이 **존재하지 않음**(증거 5) |

1을 지키면서 2를 지키면 **픽스처가 만들어지지 않는다.** 이는 조사 부족이 아니라
**plan-phase가 놓친 전제**다 — 룰북은 "`AddFixtures`가 현재 목적지를 읽는다"까지 적었으나
"서버가 발화한 플러그인 실행이 그 목적지를 갖는가"는 아무도 묻지 않았다.
ASSUMPTION-71~75 어디에도 이 항목이 없다.

**오케스트레이터는 다음 중 어느 것도 임의로 하지 않는다** — 전부 사용자 결정이다:

| 선택지 | 내용 | 대가 |
|---|---|---|
| A | **CD 경로를 M0 측정으로 1회 승인** — `patch_proper.xml` 방식(`Patch():Addr()`로 CD → `AddFixtures` → `CD Root`, undo 세션)을 테스트 쇼파일에서 측정. 룰북의 CD 금지가 과일반화인지 실측으로 판정한다 | `spec.md` §A 사전 확정 사실 2 · `design.md` §7 안티패턴 1을 **의도적으로 1회 위반**. 승인 없이는 불가 |
| B | **`ASSUMPTION-76` 신설 + REQ-AUTOPATCH-018 조정** — plan-phase amendment. spec/plan/acceptance/design 개정 후 **plan-auditor 재감사** | 아티팩트 개정 + 재감사 비용. round6 PASS 1.000이 재평가된다 |
| C | **여기서 마감** — 73·74 INCONCLUSIVE 확정, M8 BLOCKED, SPEC 미완결로 기록 | M4~M8 미착수. M1·M2·M3 성과는 보존 |

#### 콘솔 잔여물 — **전량 정리 완료**

세션 종료 시점 실측(`plan.md` §C "세션 후 생성물 제거" 이행):

| 항목 | 세션 전 | 세션 후 | 상태 |
|---|---|---|---|
| `Patch/Stages/1/Fixtures` | 39 | **39** | 무손상 — 생성 0건이었으므로 삭제할 픽스처도 없었다 |
| Plugins 풀 | 4 (`CopilotResponder`·`CopilotBusk`·`kpop_summer_twinkle`·`GenSequence100Look`) | **4 (동일)** | 프로브 8종 전량 `Delete Plugin` 완료 |
| Macros 풀 | 1 (`Copilot Go`) | **1 (동일)** | 프로브가 매크로를 만들지 않았다 |
| 라이브러리 폴더 | — | — | `autopatch_m0_probe{,2..7}` · `am0p8` 파일 전량 삭제 |
| FID · 유니버스 | 1~39 · U1~3 | **동일** | 프로브는 FID 501~503 · U10~11만 겨냥했고 하나도 생성되지 않았다 |

저장소 무변경: 프로브 파일은 전부 콘솔 라이브러리 폴더였고 `console/lua/**`(PRESERVE)는 무접촉이다
(`git diff --stat -- console/lua` 빈 출력).

### M0 라이브 세션 3차 — `ChangeDestination` 승인 측정 (2026-08-06)

#### 승인 기록

사용자가 **"쓰고 측정해라"** 로 `ChangeDestination` 1회 사용을 명시 승인했다(2026-08-06).
이는 `spec.md` §A 사전 확정 사실 2 · `design.md` §7 안티패턴 1을 **의도적으로 위반하는
측정**이며, 위반 사실과 승인 근거를 여기 남긴다. 생성 코드에 CD를 넣는 것이 아니라
**M0 측정 프로브에 한정**된다 — REQ-AUTOPATCH-017(생성기 산출물의 CD 금지)은 불변이다.

#### 측정 결과 — CD로도 목적지를 옮기지 못한다

| # | 경로 | CD 명령 결과 | 이후 `CmdObj()` | `AddFixtures` |
|---|---|---|---|---|
| 1 | 플러그인 내부 `Cmd("ChangeDestination " .. Patch():Addr(), undo)`<br/>(`patch_proper.xml` 방식, `CreateUndo`/`CloseUndo`로 감쌈) | — | `TempCmdlines Cmdline 1` **불변** | `T1 NIL · T2 NIL` |
| 2 | 플러그인 내부 CD, 대상을 `Fixtures:AddrNative()`로 교체 | — | **불변** | — |
| 3 | OSC 명령줄 `ChangeDestination 149712`(숫자 주소) | **`Failed`** | 불변 | `T1 NIL · T2 NIL` |
| 4 | OSC 명령줄 `ChangeDestination ShowData.LivePatch.Stages.'Stage 1'.Fixtures` | **`OK`** | **불변** | `T1 NIL · T2 NIL` |
| 5 | 플러그인 내부 `CmdIndirect("ChangeDestination " .. 위 경로)` | 호출 성공 | **불변** | `T1 NIL` |

**기계적 원인**: `Cmd()`·OSC exec는 호출마다 **일회용 임시 명령줄**에서 실행된다.
CD는 그 임시 명령줄의 목적지를 바꾸고 함께 소멸한다 — 플러그인이 `AddFixtures`를 부를 때
보는 앰비언트 목적지에는 도달하지 못한다. 4번이 `OK`를 반환하고도 다음 호출에 남지 않는 것이
그 직접 증거다.

#### 확보한 부수 사실 (후속 SPEC 자산)

| 사실 | 값 |
|---|---|
| `Patch()`가 가리키는 실제 객체 | **`ShowData.LivePatch`** (`ShowData.Patch`가 아니다) |
| Fixtures 컨테이너 네이티브 경로 | `ShowData.LivePatch.Stages.'Stage 1'.Fixtures` |
| 동 숫자 주소 | `149712` |
| 유효한 CD 인자 형식 | 위 **경로 형식은 `OK`**, **숫자 주소는 `Failed`**, `LivePatch` 단독은 `Failed`, `Patch`·`Root`는 `OK` |
| 라벨 문자열 특성 | MA3 라벨이 `.`·`/` 구분자를 제거한다(경로를 라벨로 실어 나를 때 주의) |

#### 남은 단 하나의 시나리오 — 룰북이 실제로 기술한 상태

지금까지의 GUI 탭 측정은 **콘솔 메인 명령줄의 목적지를 명시적으로 옮기지 않은 채** 수행됐다.
사용자는 Patch 편집기 **창**을 열었을 뿐이고, 그것이 메인 명령줄 목적지를 옮긴다는 보장이 없다.
룰북이 기술한 상태는 정확히 이것이다:

> `AddFixtures`는 콘솔의 **현재 command destination**을 읽으며, 그것은 이미 patch fixtures
> 레이어다 — **프롬프트가 `…/Patch/Stages/Stage 1/Fixtures>` 로 읽히기 때문**이다.

즉 **프롬프트 자체가 그 경로여야** 한다. 미측정 상태로 남은 시나리오:
콘솔 메인 명령줄에 직접 `ChangeDestination ShowData.LivePatch.Stages.'Stage 1'.Fixtures`를
입력해 프롬프트를 옮긴 뒤, GUI에서 플러그인을 탭한다. 이 경로만 남았고 프로브를 배치해 두었다
(슬롯 6 `AM0FINAL`, 결과는 슬롯 5 `AM0 RESULT HERE` 라벨로 회수).

이 시나리오가 성공하면 **서버 자동화로는 패치할 수 없고 사람이 목적지를 잡아 줘야 한다**는
결론이 되며, 그것은 REQ-AUTOPATCH-018과 M5 설계를 근본에서 바꾼다.
실패하면 이 빌드에서 `AddFixtures` 경로 자체가 성립하지 않는다는 결론이다.

#### 그 시나리오도 실패했다 — 최종 판정

사용자가 콘솔 메인 명령줄에 CD를 입력해 프롬프트를 옮겼다. 스크린샷으로 확인된 상태:

```
Admin@ShowData/LivePatch/Stages/Stage 1/Fixtures>
```

**룰북이 기술한 바로 그 상태다.** 그 상태에서 두 경로를 모두 측정했다.
측정 재현성을 위해 프로브에 **난수 태그**를 넣어 "실행되었는가"와 "결과가 무엇인가"를 분리했다
(직전 회차에 센티넬을 리셋하지 않아 OSC 결과와 GUI 결과를 구별하지 못한 오류를 교정한 것이다).

| 실행 경로 | 실행 확인 | 플러그인이 본 목적지 | 결과 |
|---|---|---|---|
| OSC `Plugin 'AM0FINAL'` (프롬프트 이동 상태) | — | `TempCmdlines Cmdline 1` | `T1 NIL · T2 NIL` |
| **GUI 탭** (프롬프트 이동 상태) | **`R302`** 난수 확인 | **`TempCmdlines Cmdline 1`** | `T1 NIL · T2 NIL` |
| **GUI/OSC, 정식 플러그인 구조** (`return Main, Cleanup, Execute`, `patch_proper.xml` 형태) | **`R463`**, `display_handle` 수신됨(`dhtrue`) | **`TempCmdlines Cmdline 1`** | `T1 NIL` |

**메인 명령줄 프롬프트가 Fixtures 레이어에 있어도 플러그인의 Lua 실행 컨텍스트는
`TempCmdlines Cmdline 1`이다.** 프롬프트와 플러그인 실행 컨텍스트는 별개의 명령줄이다.

#### `NEGATIVE: AddFixtures 경로` — M0 최종 판정

```
GO:            ASSUMPTION-71  FID 가독 (슬롯≠FID 전수 확인, 고정점 0)
GO(한정):      ASSUMPTION-72  드릴다운·모드명·핸들 해석 O / 점유폭 획득 X
NEGATIVE:      ASSUMPTION-75  Patch 편집기 상태 감지 불가
INCONCLUSIVE:  ASSUMPTION-73  배열 의미론을 관측할 기회가 없었음
INCONCLUSIVE:  ASSUMPTION-74  생성 0건이라 관측 대상이 없었음
```

73·74가 INCONCLUSIVE인 이유는 측정 부족이 아니라 **선행 조건이 성립하지 않기 때문**이다.
아래 8개 경로를 전부 측정했고 단 하나도 픽스처를 만들지 못했다:

| # | 경로 | 결과 |
|---|---|---|
| 1 | OSC 발화 플러그인, 편집기 닫힘 | 목적지 `TempCmdlines` · 0건 |
| 2 | OSC 발화 플러그인, 편집기 열림 | 0건 |
| 3 | GUI 탭, 프롬프트 미이동 | `TempCmdlines` · 0건 |
| 4 | **GUI 탭, 프롬프트 = `…/Stage 1/Fixtures>`** | **`TempCmdlines` · 0건** |
| 5 | 정식 플러그인 구조(`Main, Cleanup, Execute`) | `TempCmdlines` · 0건 |
| 6 | 플러그인 내부 `Cmd("ChangeDestination …", undo)` | 목적지 불변 · 0건 |
| 7 | 플러그인 내부 `CmdIndirect("ChangeDestination …")` | 목적지 불변 · 0건 |
| 8 | OSC 명령줄 CD 후 별도 호출로 플러그인 실행 | CD는 `OK`, 목적지 미지속 · 0건 |

구조적 배제(전부 실측):
`AddFixtures`는 컨테이너 메서드가 아니다(`Fixtures.AddFixtures` = nil, 단 `Fixtures:Count()` = 39) ·
목적지 설정 Lua API 부재(`SetCmdObj`·`SetDestination`·`ChangeDestination` 전역 없음,
`CurrentCommandLine()` 이 빌드 미제공) · `patch` 배열/유니버스/FID 충돌/예외/CD 오염 전부 배제.

**결론**: onPC **2.4.2.2** + responder **1.6.1** 환경에서, 이 저장소가 접근 가능한 **어떤 경로로도**
`AddFixtures`가 픽스처를 생성하지 못한다. 플러그인 Lua 실행 컨텍스트의 목적지가 항상
`TempCmdlines Cmdline 1`이고 이를 바꿀 수단이 없기 때문이다.

#### 이것이 무효화하는 것 — 본 SPEC의 근간

`spec.md` §A **사전 확정 사실 1**("패치는 Lua `AddFixtures` 전용이며 정확히 2단계")은
**이 환경에서 성립하지 않는다.** 사실 2(CD 금지)와의 충돌 문제가 아니라, **CD를 써도 안 된다.**
본 SPEC의 REQ-AUTOPATCH-016·018·020, 마일스톤 M4·M5·M6·M8이 전부 이 전제 위에 있다.

M1·M2·M3(후보 모델 · FID 배정 · 타입/모드 해석)은 **콘솔 쓰기와 무관한 계층**이므로
이 판정에 영향받지 않는다 — 45건의 테스트와 함께 그대로 유효하다.

#### 미해소로 남기는 것 (다음 담당자용)

| # | 항목 | 왜 열려 있나 |
|---|---|---|
| G1 | 룰북 `30_plugin_patterns.md:11-53`이 이 경로를 "라이브 검증됨"으로 기술한 근거 | 어느 세션이 어떤 조건에서 성공했는지 저장소에 기록이 없다. 그 조건이 재현되면 판정이 뒤집힌다 |
| G2 | Executor에 할당한 플러그인 · 매크로에서 호출 등 **다른 실행 트리거** | 측정하지 않았다. 트리거마다 실행 컨텍스트가 다를 가능성이 남아 있다 |
| G3 | responder 확장으로 목적지를 세팅하는 경로 | `console/lua/**`는 본 SPEC의 PRESERVE라 범위 밖. 별건 SPEC 대상 |
| G4 | `SendOSCMessage(slot, ...)`로 플러그인이 서버에 직접 보고하는 채널 | `patch_proper.xml`이 쓰던 기법. 본 세션은 플러그인 라벨로 대체했다 |

#### 콘솔 최종 상태 — 세션 전과 동일

| 항목 | 세션 전 | 세션 후 |
|---|---|---|
| `Patch/Stages/1/Fixtures` | 39 | **39** |
| FID · 유니버스 | 1~39 · U1~3 | **동일** |
| Plugins 풀 | 4 | **4** (프로브 14종 전량 삭제) |
| Macros 풀 | 1 | **1** |
| 라이브러리 폴더 | — | 프로브 파일 전량 삭제(`ls \| grep am0` → none) |
| 명령줄 목적지 | — | `ChangeDestination Root`로 원복 |

`console/lua/**`(PRESERVE) 무접촉. 저장소 코드 변경 0.

### M0 라이브 세션 4차 — G2 추적(다른 실행 트리거) · 종결 (2026-08-06)

#### 새 발견 1 — `Lua` 커맨드가 존재하고 동작한다

명령줄 커맨드 **`Lua '<code>'`** 가 이 빌드에 존재하며 Lua를 실행하고 `Cmd()`도 호출할 수 있다
(플러그인 슬롯 라벨이 `LUAWORKS`로 바뀌는 것으로 실증). 작은따옴표 인자 안에서 Lua 문자열은
`[[ ]]` 롱브래킷으로 쓴다 — 응답기 프로토콜이 큰따옴표를 거부하기 때문이다
(`server/bridge/protocol.py:109`). **플러그인을 거치지 않고 콘솔에서 Lua를 실행하는 경로**이며
후속 SPEC의 자산이다.

#### 새 발견 2 — 플러그인 Lua 상태와 명령줄 Lua 상태는 별개 환경이다

플러그인이 `_G.AF = function() … end`로 전역을 정의한 뒤, 같은 세션에서
명령줄에 `Lua 'AF()'`를 입력하면 **`attempt to call a nil value (global 'AF')`** 가 난다
(사용자 스크린샷으로 확인). 반면 OSC로 `Lua 'AF()'`를 보내면 정상 실행된다(`R204` 반환).
즉 **명령줄의 Lua 환경은 플러그인/OSC 경로의 Lua 환경과 전역 테이블을 공유하지 않는다.**

#### 측정 — 9번째 경로도 0건

사용자가 프롬프트 `Admin@ShowData/LivePatch/Stages/Stage 1/Fixtures>` 상태에서 직접 입력:

```
Lua 'AddFixtures{mode=Patch().FixtureTypes[3].DMXModes[1],amount=1,fid=[[501]],
     idtype=[[Fixture]],name=[[T1]],patch={[[10.1]]}}'
```

명령은 **`OK`** 로 접수되었고(청크가 오류 없이 실행됨), `Patch/Stages/1/Fixtures` childCount는
**39 그대로**다. `AddFixtures`가 또 조용히 `nil`을 반환했다.

**측정 한계 고지**: 같은 화면의 직전 행에
`User Canceled Command(User Input aborted: ""):Lua " ="Patch"` 가 보인다 — MA3 명령줄의
자동완성이 입력에 개입한 흔적이다. 따라서 **실행된 인자 목록이 타이핑한 것과 정확히 같았는지는
확정할 수 없다.** 다만 픽스처 개수 39 불변은 명확하므로 **생성 0건**은 확정이다.

#### 시도했으나 안전하지 않아 중단한 것 — 합성 키 입력

오케스트레이터가 사용자 대신 명령줄에 입력하기 위해 Orca computer-use로 창을 찾아
(`app_gma3` pid 86771 / window 127941) 키를 주입했다. **MA3는 키 입력을 텍스트가 아니라 콘솔
하드키 단축키로 해석한다** — 타이핑한 글자들이 각각 명령으로 실행되어 명령줄 히스토리에
`OK:Normal` 약 20행과 `OK:At` 1행을 남겼다. 텍스트 입력 모드 전환 절차 없이 이 경로를 쓰면
`Delete`·`Store` 등으로 매핑되는 글자가 섞일 수 있어 **위험하다고 판단하고 중단했다.**

영향 확인: 쇼파일 무변경(픽스처 39 · Sequences 21 · Macros 1 — 전부 세션 시작 시와 동일).
`Normal`·`At`은 프로그래머 상태 명령이라 쇼파일을 바꾸지 않는다. 프로그래머 잔여 상태 정리
(`Clear`)는 사용자의 미저장 작업을 날릴 수 있어 **오케스트레이터가 임의로 보내지 않았다.**

부수 관측: Display 3 창에 **릴리스 노트 소프트웨어 동의 다이얼로그**가 떠 있었다. 동의는
오케스트레이터가 대신 누를 사안이 아니라 건드리지 않았다.

#### G2 판정 — 닫힘

```
NEGATIVE: G2 — 다른 실행 트리거로도 AddFixtures가 픽스처를 만들지 못한다.
```

측정한 실행 트리거 누계 **9경로**, 생성 **0건**:
OSC 발화 플러그인(편집기 닫힘/열림) · GUI 탭(프롬프트 미이동/이동) · 정식 플러그인 구조 ·
플러그인 내 `Cmd(CD)` · 플러그인 내 `CmdIndirect(CD)` · OSC 명령줄 CD 후 별도 호출 ·
**명령줄 직접 입력 `Lua 'AddFixtures{…}'`**.

#### 갱신된 미해소 목록

| # | 항목 | 상태 |
|---|---|---|
| G1 | 룰북 `30_plugin_patterns.md:11-53`의 "라이브 검증" 근거 | **열림** — 어느 세션이 어떤 조건에서 성공했는지 저장소에 기록 없음. 재현되면 판정이 뒤집힌다 |
| G2 | 다른 실행 트리거 | **닫힘 — NEGATIVE**(위 9경로). 단 Executor 할당 트리거는 미측정으로 남는다 |
| G3 | responder 확장으로 목적지 세팅 | **열림** — `console/lua/**`가 본 SPEC PRESERVE라 범위 밖. 별건 SPEC |
| G4 | `SendOSCMessage`로 플러그인→서버 직접 보고 | **열림** — `patch_proper.xml`의 기법. 본 세션은 플러그인 라벨로 대체 |
| G5 | 명령줄 자동완성이 긴 `Lua` 인자에 개입하는 문제 | **신규·열림** — 9번째 경로 측정의 신뢰도를 낮춘 요인 |

#### 최종 콘솔 상태

| 항목 | 값 | 세션 시작 대비 |
|---|---|---|
| `Patch/Stages/1/Fixtures` | 39 | **동일** |
| `DataPools/Default/Sequences` | 21 | **동일** |
| `DataPools/Default/Macros` | 1 | **동일** |
| `DataPools/Default/Plugins` | 4 | **동일** (프로브 전량 삭제) |
| 라이브러리 폴더 프로브 파일 | 0 | **동일** |

`console/lua/**`(PRESERVE) 무접촉. 저장소 코드 변경 0. **M0 종결.**

### §E.2z 자기정정 — "근본 원인 확정"은 과했다 (2026-08-06, 세션 종료 직전)

본 §E.2의 M0 3·4차 절이 destination을 **"근본 원인 확정"** 이라고 적었다. **그 표현은 과하다.**

**확인된 것**: 9개 실행 경로 전부에서 (a) 플러그인이 보는 목적지가 `TempCmdlines Cmdline 1`이었고
(b) `AddFixtures`가 `nil`을 반환했다.

**확인되지 않은 것**: 목적지가 `TempCmdlines`가 **아닌** 컨텍스트를 **한 번도 만들지 못했다.**
따라서 "목적지를 옮기면 성공한다"는 **양성 대조군이 없다.** 상관은 있고 인과는 미확정이다.
이 SPEC이 다른 곳에서는 "0건 주장에 반드시 비공허성 대조군을 붙인다"는 규율(§6.3)을 지켰으면서,
정작 자신의 인과 주장에는 대조군 없이 "확정"을 붙였다 — 같은 잣대를 자기 판정에도 적용해야 한다.

**세션 종료 직전 추가 실측 — 미시험 영역이 드러났다**:

| 경로 | childCount |
|---|---|
| `ShowData/Patch` | **0** (비어 있음) |
| `ShowData/LivePatch` | **14** (`FixtureTypes`·`Stages`·`Layers` 등, 픽스처 39대가 여기) |
| `ShowData/Patch/Stages` | 조회 실패(경로 없음) |

MA3에 **패치 편집 버퍼와 라이브 패치가 분리**되어 있고 `Patch()`는 **LivePatch**를 가리킨다.
모든 측정이 LivePatch만 겨냥했다. 편집 버퍼가 편집 세션 중에만 채워진다면 `AddFixtures`의
대상이 애초에 달랐을 수 있다. **이 축은 전혀 측정되지 않았다.**

**정정된 판정 문구**:

```
MOST-LIKELY-HYPOTHESIS (미증명): AddFixtures 실패의 원인은 플러그인 실행 컨텍스트의
  command destination이 patch fixtures 레이어가 아니기 때문이다.
  근거 — 9경로 상관. 반증 미확보 — 양성 대조군 0.
CONFIRMED: 측정한 9개 실행 경로 어디에서도 픽스처가 생성되지 않았다.
CONFIRMED: 목적지를 옮길 Lua API가 이 빌드에 존재하지 않는다.
REFUTED  : "CD를 보내면 실패한다"는 룰북의 인과 설명 — CD 유무와 무관하게 결과가 같다.
```

**다음 담당자는 §0의 미시험 항목 L1~L6부터 시작하라.** 특히 L1(매크로 2줄)과 L2(편집 세션)는
구조적으로 다른 실행 컨텍스트이며 아직 측정되지 않았다. "이미 다 해봤다"는 결론은 **이르다.**

> **[후속 · 2026-08-06 5차 · round9 감사 N43 교정]** 이 절의 요구는 이행됐다.
> L1·L3·L4·L5는 **NEGATIVE**이고, L6에서 **"명령줄 목적지"에 대한 양성 대조군을 확보**했다.
> 그 결과는 **처방의 반증**이다 — 위 `MOST-LIKELY-HYPOTHESIS` 블록의 **`MOST-LIKELY` 등급만
> 폐기**한다. **가설 자체는 폐기되지 않는다**: 플러그인의 목적지가 `TempCmdlines`가 아닌
> 컨텍스트를 한 번도 만들지 못했으므로 전건이 실현된 적이 없고, 가설은 **`UNDETERMINED`로
> 남는다**(§E.2 M0 5차 판정 블록). **"플러그인의 목적지"에 대한 양성 대조군은 여전히 0이다** —
> 이 절이 경계한 그 공백은 아직 메워지지 않았다.
> 남은 미시험은 **L2 1건**뿐이다. `L5`에 관해서는 선행 세션의
> 라이브러리 산물 `patch_here.xml`·`patch_rest.xml`이 이미 같은 레시피(MMX Spot·Mode 1·U1·101)를
> 시도했던 것으로 디코딩되었으나 **결과 기록이 없었고**, 5차가 그것을 직접 측정해 0건으로 확정했다.

### M0 라이브 세션 5차 — §0 미시험 항목 L1·L3·L4·L5·L6 측정 · **목적지 조작 처방 반증** (2026-08-06)

§E.2z가 요구한 **양성 대조군을 이 회차에서 확보했다** — 단 그 대조군의 대상은 **명령줄 목적지**다.
그 결과 destination 가설의 **처방**("목적지를 옮기면 된다")은 **반증됐다** — 목적지는 옮길 수 있고
옮기면 실제로 듣지만, 플러그인 Lua 컨텍스트는 그것을 물려받지 않으며 `AddFixtures`는 0건이다.
**가설 자체(원인이 플러그인의 목적지인가)는 전건이 실현된 적이 없어 미확정으로 남는다**
(round7 감사 N11 교정 — 아래 판정 블록 참조).

#### 전제 재확인 (측정 전, 직접 실측)

| 항목 | 값 |
|---|---|
| 브랜치 · HEAD | `feature/SPEC-COPILOT-VWX-001` · `6039b0a` |
| 테스트 | **4,943 passed / 7 skipped** (93.30s) |
| `ruff check` · `ruff format --check` | `OK` · `13 files already formatted` (둘 다 통과) |
| PRESERVE 5경로 `diff --stat ca00bc5..HEAD` | **빈 출력** |
| responder 왕복 | `PASS` · live **1.6.1** · `127.0.0.1:8000` / recv 9005 / osc_slot 2 |
| 쇼파일 착수 상태 | Fixtures **39** · Plugins **4** · Macros **1** · Sequences **21** |

#### 방법론 정정 4건 — 4차까지의 측정을 제약하고 있었다

측정에 착수하자마자 **장치 자체의 결함 4건**이 드러났다. 이것을 먼저 고치지 않으면
어떤 음성 결과도 "정말 실패한 것"인지 "측정이 도달하지 못한 것"인지 구별할 수 없다.

| # | 사실 | 근거 | 함의 |
|---|---|---|---|
| 1 | **`deploy` 동사로는 이 빌드에 플러그인 소스를 쓸 수 없다.** 모든 배포가 `cannot confirm plugin source write (readback did not match any setter form)`로 실패하고, 플러그인 **객체는 생성되되 소스는 비어 있다** | 빈 소스 플러그인 실행 → `exec` `OK`, 라벨 무변화 | `console/lua/**`가 PRESERVE(G3)라 수정 불가. **유일한 배포 경로는 라이브러리 파일 + `Import Plugin`** (2차 세션이 쓴 경로와 동일) |
| 2 | **플러그인 XML `<Block>`은 base64 **1368자**(원본 1026바이트)가 상한**이고 `FileContent Size`는 블록 개수다 | `copilot_responder.xml` = 45블록 × 1368, `patch_proper.xml` = 2블록 | 단일 블록에 2372자를 넣은 배포는 **조용히 실행되지 않는다**(오류 없음). 콘솔 자신의 파일이 정답을 갖고 있었다 |
| 3 | **플러그인 안의 `Cmd()`는 지연 실행(큐)이며, 플러그인이 중단되면 큐가 폐기된다** | 시도 7건을 한 플러그인에 넣으면 **첫 `rep()`조차 남지 않음**. 시도를 1건씩 분리하면 7건 전부 정상 완주 | 다중 시도 배터리는 **아무 출력도 남기지 않는다**. 이것이 "실행 안 됨"으로 오독될 수 있는 함정이며, 4차까지의 `Cmd` 기반 관측 신뢰도에 영향을 준다 |
| 4 | OSC `deploy` 요청 페이로드 상한은 인코딩 후 **약 1950자** | 원본 1183바이트(인코딩 1951자) 지점에서 소스가 잘려 `'}' expected ... near <eof>` | 큰 소스는 OSC로 보낼 수 없다 — 파일 경로가 필수 |

측정 장치는 `tools/console_probe.py`에 `deploy:` · `listen:` · `sleep:` 스텝을 더한 사본을
**저장소 밖**(`/tmp/am0b/probe.py`)에 두고 썼다 — 2~4차의 "저장소 코드 변경 0" 성질을 유지한다.
회수 채널은 **매크로 라벨**(`Store Macro <id>` + `Label Macro <id> <alnum>`)이며,
비영문숫자를 전부 `X`로 치환해 인용 문제를 원천 제거했다. `SendOSCMessage`(G4)는
**아무 것도 수신되지 않았다 — G4 여전히 열림.**

#### 장치 검증 (음성 결과를 신뢰하기 위한 선행 조건)

| 검증 | 결과 |
|---|---|
| `Import Plugin 'am5smoke'` → 풀 슬롯 생성 | `OK` |
| 시도 0건 하니스 실행 → 매크로 라벨 회수 | **`R510SXXDTempXCmdlinesXCmdlineX1`** — 장치 동작 확인 |
| 2블록 플러그인 실행 | **정상 완주**(`R512S2…END`) — 분할이 원인이 아님을 확인 |
| 시도 8건 개별 컴파일(`load`) | **8/8 통과** — 음성 결과가 문법 오류 때문이 아님 |

#### L1·L3·L4·L5 — 전부 NEGATIVE (시도 1건 = 플러그인 1개, 매크로 라벨 원문)

판정 코드: `<키>1` = `AddFixtures`가 non-nil 반환(생성) · `<키>0` = `nil` 반환(조용한 실패) ·
`<키>E` = 예외.

| 항목 | 시도 | 매크로 라벨 (원문) | `AddFixtures` | Fixtures |
|---|---|---|---|---|
| (대조) | `a` 문자열 `idtype`, LEDBeam Mode 1, FID 701, U10 | `R513AXa0XENDXDTempXCmdlinesXCmdlineX1` | **`nil`** | 39 |
| **L3** | `b` `idtype = Patch().IDTypes["Fixture"]`(이름 핸들) | `R513BXb0XENDXDTempXCmdlinesXCmdlineX1` | **`nil`** | 39 |
| **L3** | `c` `idtype = Patch().IDTypes[1]`(인덱스 핸들) | `R513CXc0XENDXDTempXCmdlinesXCmdlineX1` | **`nil`** | 39 |
| **L4** | `d` `CreateUndo` 세션 안 · **CD 0건** · `undo` 필드 전달 | `R513DXd0XENDXDTempXCmdlinesXCmdlineX1` | **`nil`** | 39 |
| **L5** | `f` 룰북 레시피(MMX Spot · Mode 1)를 **빈 FID·빈 유니버스**로 | `R513FXf0XENDXDTempXCmdlinesXCmdlineX1` | **`nil`** | 39 |
| (추가) | `g` `idtype` **완전 생략** | `R513GXg0XENDXDTempXCmdlinesXCmdlineX1` | **`nil`** | 39 |
| (추가) | `h` `patch` **완전 생략**(주소를 MA3가 고르게) | `R513HXh0XENDXDTempXCmdlinesXCmdlineX1` | **`nil`** | 39 |
| **L5 글자그대로** | `e` `Robin MMX Spot`·`Mode 1`·`fid=tostring(2)`·`name="MMX "..2`·`patch={"1."..101}` — `30_plugin_patterns.md:40-53` 원문 | `R513EXe0XENDXDTempXCmdlinesXCmdlineX1` | **`nil`** | 39 |

`idtype`·`mode` 핸들은 **실제로 해석된다**(`TIuserdata` · `TMuserdata`) — 인자가 nil이어서
실패하는 것이 아니다. `Robin MMX Spot`은 이 쇼파일에 **실재한다**(`Patch/FixtureTypes` 슬롯 1,
`DMXModes` 4개 중 `Mode 1`). **L5는 자원 부재가 아니라 진짜 실패다.**

**L1 — 매크로 2줄(같은 명령줄 순차 실행)**: 매크로 97을 만들어 줄 단위로 원문 검증했다.

```
97.1  ChangeDestination ShowData.LivePatch.Stages.1.Fixtures
97.2  Plugin 29                    (= AM5L1, 목적지 판독 + AddFixtures 1회)
97.3  ChangeDestination Root
```

| 실행 | 플러그인 실행 확인 | 플러그인이 본 목적지 | `AddFixtures` | Fixtures |
|---|---|---|---|---|
| 대조: OSC `Plugin 29`(CD 없음) | 매크로 110 생성 | `TempCmdlines Cmdline 1` | `nil` | 39 |
| **L1: `Macro 97`** | 매크로 110 **삭제 후 재생성** = 확실히 실행됨 | **`TempCmdlines Cmdline 1`** | **`nil`** | **39** |

`Set Macro 97.1 Property 'Command'`가 처음 **`Illegal object`** 로 실패했다 —
**매크로 줄은 `Store Macro <id>.<line>`으로 먼저 만들어야 한다.** 룰북
`00_grammar.md:80-84`는 이 단계를 적지 않았다(**룰북 결함, 신규**).

#### L6 — 양성 대조군 확보 (§E.2z가 요구한 바로 그것)

"목적지를 옮기면 된다"를 검증하려면 **목적지가 실제로 옮겨졌고 그 상태가 듣는다**는 것을
독립적으로 보여야 한다. 목적지에 **상대적인** 명령(`Label <index> <text>`)을 쓰면
Lua를 거치지 않고 그것을 보일 수 있다.

| # | 실행 | 기대 | 실측 |
|---|---|---|---|
| 음성 대조 | OSC `Label 90 ZZCONTROL`(목적지 미이동) | 실패 | **`Illegal object`** · 매크로 90 이름 불변 |
| 양성 | 매크로: `CD ShowData.DataPools.1.Macros` → `Label 90 ZZMOVED` | 이름 변경 | **매크로 90 → `ZZMOVED`** |
| 음성 대조(픽스처) | OSC `Label 1 ZZFX`(목적지 미이동) | 실패 | `OK` 반환하고 **이름 불변**(`RLB350M1 1`) |
| **양성(픽스처)** | 매크로: `CD ShowData.LivePatch.Stages.1.Fixtures` → `Label 1 ZZFX` | 이름 변경 | **픽스처 슬롯 1 → `ZZFX`** |

**즉 매크로 명령줄에서 CD는 실제로 적용되고, 뒤따르는 줄은 옮겨진 목적지 —
patch fixtures 컨테이너 그 자체 — 를 기준으로 동작한다.** L1은 **바로 그 컨텍스트**에서
플러그인을 실행했고, 플러그인은 여전히 `TempCmdlines Cmdline 1`을 보았으며 0건을 만들었다.

(픽스처 슬롯 1의 이름은 **원복했다** — `Label 1 RLB350M1 1`은 후행 ` 1`이 파서에 먹혀
`RLB350M1`이 되었고, 객체 모델 대입 `Patch().Stages[1].Fixtures[1].name = "RLB350M1 1"`로
정확히 복원한 뒤 재조회로 확인했다.)

#### 판정

```
NEGATIVE: L1 — 매크로 2줄(같은 명령줄 CD → 플러그인). 플러그인 목적지 불변 · 0건.
NEGATIVE: L3 — idtype 객체 핸들(이름·인덱스 양쪽). 핸들은 userdata로 해석됨 · 0건.
NEGATIVE: L4 — CreateUndo 세션 안 · CD 0건. 0건.
NEGATIVE: L5 — 룰북 예제 글자그대로(MMX Spot·Mode 1·U1·101). 자원 실재 · 0건.
ACHIEVED(부분): L6 — 양성 대조군 확보. 단 그 대조군의 대상은 **명령줄 목적지**다 —
          목적지는 옮겨지며 옮기면 듣는다(픽스처 레이어 포함, 짝지은 음성 대조군과 함께).
          **"플러그인의 목적지"에 대한 양성 대조군은 확보하지 못했다.**
REFUTED : destination 가설의 **처방(remedy)** — "명령줄 목적지를 patch fixtures 레이어로
          옮기면 AddFixtures가 성공한다". 옮겼고, 옮겨진 것을 독립 증명했고,
          그 컨텍스트에서 실행했고, 그래도 0건이다.
CONFIRMED: 플러그인 Lua 실행 컨텍스트는 명령줄 목적지를 물려받지 않는다 —
          매크로 명령줄이 Fixtures 레이어에 있어도 플러그인은 TempCmdlines Cmdline 1을 본다.
          이 저장소가 접근 가능한 수단으로 플러그인의 목적지를 바꿀 방법이 없다.
UNDETERMINED: "실패 원인이 플러그인의 목적지다"라는 **가설 자체**. 10개 실행 경로 전부에서
          플러그인의 목적지는 TempCmdlines Cmdline 1이었다 — 전건이 실현된 적이 없으므로
          이 가설은 관측된 0건과 **여전히 양립하며 반증되지 않았다.**
          (§E.2z가 자기정정한 과잉주장을 반복하지 않기 위해 이 줄을 명시한다.)
NEGATIVE: G6(신규) — 객체 모델 생성 경로. Fixtures 컨테이너의 Append는 실재하는
          function이나(비공허성 대조군 통과) 호출하면 nil을 반환하고 0건을 만든다.
REFUTED : G1 — 룰북 `30_plugin_patterns.md:11-53`의 "라이브 검증됨" 주장. 그 예제를
          글자그대로 돌려 0건이다. 이 빌드에서 룰북 절차는 성립하지 않는다.
```

측정 누계 — **계수 단위를 분리해 적는다**(round10 감사 N50 교정. 이전 판은 "경로 13가지"라고
적었으나 실행 컨텍스트와 인자 변형을 섞어 세어 재구성이 불가능했다):

| 계수 단위 | 수 | 내역 |
|---|---|---|
| **실행 경로(실행 컨텍스트)** | **10** | 4차까지 **9** + 5차의 **매크로 발화 플러그인 1**(L1). 5차의 인자 변형들은 전부 **기존 OSC 발화 컨텍스트** 안에서 돌았으므로 새 경로가 아니다 |
| **`AddFixtures` 인자 변형** | **8종** | `a` 문자열 idtype(대조) · `b` 핸들(이름) · `c` 핸들(인덱스) · `d` CreateUndo · `e` 룰북 글자그대로 · `f` MMX 자유 FID/유니버스 · `g` idtype 생략 · `h` patch 생략. (L1은 `a` 형태를 매크로 컨텍스트에서 재실행한 것) |
| **별도 생성 기법(비-`AddFixtures`)** | **1종** | 객체 모델 `Fixtures:Append` |

**생성 0건** — 위 전부에서.

#### 부수 신규 사실 (후속 SPEC 자산)

| 사실 | 값 |
|---|---|
| **인용부호 없는 유효 CD 인자** | `ShowData.LivePatch.Stages.1.Fixtures` → `OK` · `ShowData.DataPools.1.Macros` → `OK`. `Patch.Stages.1.Fixtures` → `Failed` · `ShowData.LivePatch.Stages.Stage 1.Fixtures` → `Failed`. **매크로 줄 안에서는 중첩 인용이 불가하므로 이 형식이 유일한 통로다** |
| `Lua` 커맨드의 롱브래킷 형태 | `Lua [==[...]==]` → **`Not allowed`**. 작은따옴표 `Lua '...'`만 유효 |
| **객체 모델 프로퍼티 쓰기는 즉시 적용되고 실제로 듣는다** | `Patch().Stages[1].Fixtures[1].name = "..."`가 **목적지와 무관하게** 성공. patch 레이어는 Lua로 **쓸 수 있다** — 못 하는 것은 `AddFixtures`의 **생성**뿐이다 |
| `Fixtures` 컨테이너 메서드 실재 여부 | `Append` = `function`, 허구 키 `ZZBogusNotAMethod`·`Frobnicate9` = `nil` (**비공허성 대조군 통과**). 단 `Append()` 반환 `nil` · Count 39→39 |
| `Label`의 "OK ≠ 효과" 재확인 | 목적지 미이동 `Label 1 ZZFX`가 **`OK`를 반환하고 아무것도 바꾸지 않았다** — 함정 4번의 또 다른 실례 |
| `ShowData/Patch` vs `ShowData/LivePatch` (L2 전제 재실측) | **0** vs **14**. 함정 8번·L2 전제 그대로 유효 |

#### 남은 것 — L2 (사용자 필요)

**L2(패치 편집 세션 활성 상태에서 실행)만 미측정으로 남는다.** OSC로 도달할 수 없다 —
`ASSUMPTION-75`가 이미 NEGATIVE(편집기 상태 감지 불가)이고, 4차에서 합성 키 입력이
위험하다고 판단해 중단한 경로다. 사용자가 편집 세션에 진입해야 한다.

**단 L6의 결과가 L2의 기대값을 크게 낮춘다.** L2의 근거는 "편집 버퍼가 편집 세션 중에만
채워지고 `AddFixtures`의 대상이 거기일 수 있다"였다. 그러나 L6이 보인 것은
**목적지를 patch fixtures 컨테이너로 옮겨도 플러그인이 그것을 보지 못한다**는 것이며,
이는 편집 세션이 목적지를 어디로 옮기든 플러그인 컨텍스트에는 도달하지 못한다는 쪽을 가리킨다.
**L2를 배제하지는 않는다**(측정하지 않은 것을 측정했다고 적지 않는다). 기대값만 낮춘다.

#### 콘솔 최종 상태 — 세션 전과 동일

| 항목 | 세션 전 | 세션 후 | 비고 |
|---|---|---|---|
| `Patch/Stages/1/Fixtures` | 39 | **39** | 생성 0건 |
| 픽스처 슬롯 1 이름 | `RLB350M1 1` | **`RLB350M1 1`** | L6에서 `ZZFX`로 바꾼 뒤 원복·재조회 확인 |
| `DataPools/Default/Plugins` | 4 | **4** | 프로브 30개 전량 삭제(슬롯 34→5 역순) |
| `DataPools/Default/Macros` | 1 (`Copilot Go`) | **1 (`Copilot Go`)** | 회수·제어용 매크로 전량 삭제 |
| `DataPools/Default/Sequences` | 21 | **21** | 무접촉 |
| 라이브러리 폴더 | 20개 파일 | **20개 파일** | 내가 만든 `am5*.xml` **22개 전량 삭제**, 선행 산물(`patch_*.xml`·`CheckDest*.xml` 등) 무접촉 |
| 명령줄 목적지 | — | `ChangeDestination Root`로 원복 |

`console/lua/**`(PRESERVE) 무접촉. **저장소 코드 변경 0**(`git status --porcelain`에
본 세션 산물 0건 · HEAD `6039b0a` 불변). 측정 도구는 `/tmp/am0b/`에만 존재한다.

#### 이것이 §0의 결론에 대해 갖는 함의

§0은 "6건이 전부 실패하면 반자동 모델 전환을 제안한다"고 적었다.
**L1·L3·L4·L5가 실패하고 L6이 destination 가설의 처방을 반증했으므로 그 조건은 실질적으로
충족됐다** — 남은 L2는 사용자 자원이 필요하고 L6에 의해 기대값이 낮아진 단일 항목이다.
(가설 자체는 미확정이다 — 아래 두 단락과 판정 블록의 `UNDETERMINED` 줄 참조.)

`AddFixtures`가 이 빌드에서 실패하는 **원인은 여전히 미확정**이다. 확정된 것은
**원인이 무엇이든 명령줄 목적지 조작으로는 거기에 도달할 수 없다**는 것이다.
이것은 4차의 "MOST-LIKELY-HYPOTHESIS"를 **처방 차원에서** 폐기하며,
**목적지를 조작하는 어떤 후속 설계도 근거가 없다**는 뜻이다 —
그 방향의 추가 투자를 막는 것이 이 회차의 실질적 산출이다.

**다만 "원인이 command destination이 아니다"라고까지 적지 않는다.** 플러그인의 목적지가
`TempCmdlines`가 아닌 컨텍스트를 한 번도 만들지 못했으므로 그 가설의 전건은 실현되지 않았고,
가설은 데이터와 양립한 채 남는다. 이 구별을 흐리면 §E.2z가 교정한 오류를 되풀이하는 것이다
(round7 감사 지적 N11 — 초판이 실제로 그 오류를 되풀이했고 여기서 교정했다).

---

## §E.2aa Amendment v0.1.3 — 반자동 실행 모델 (2026-08-06, 사용자 승인)

**승인 기록**: M0 5차 결과(L1·L3·L4·L5 NEGATIVE · L6 양성 대조군 → destination 가설의
**처방** 반증, **원인은 미확정**)를
제시하고 진로를 물었고, 사용자가 **"반자동 모델 amendment 착수"** 를 선택했다.
§0의 "6건이 전부 실패하면 반자동 모델 전환을 제안한다"가 그 근거이며,
**오케스트레이터가 임의 승격하지 않았다** — 승인 전에는 아티팩트를 고치지 않았다.

### 무엇을 바꿨나 (REQ 26 · AC 27 — **수 불변**, 내용만 조정)

| 아티팩트 | 변경 |
|---|---|
| `spec.md` | `version` 0.1.2 → **0.1.3** · HISTORY 행 추가 · §A 개요 한 줄을 반자동으로 · **사전 확정 사실 1·2를 반증 확정으로 정정** · **사실 7·8 신설**(플러그인 컨텍스트 목적지 미상속 · `deploy` 동사 소스 쓰기 불가) · **REQ-AUTOPATCH-018 조정**(서버 실행 → 사람 실행 전달 + 서버 검증) · REQ-AUTOPATCH-020에 배포 경로 비가용 고지 · **REQ-AUTOPATCH-024의 "편집기를 먼저 열라" 안내 철회**(원인 설명이 반증됨) · **`ASSUMPTION-76` 신설 + 즉시 NEGATIVE 판정** |
| `acceptance.md` | **AC-AUTOPATCH-015 재작성**(단일 명령 실행 → 사람 실행 전달 · 패치 실행 발화 0건, **비공허성 대조군 부착**) · **AC-AUTOPATCH-017 재작성**(별도 배포 경로 신설 0건, 비공허성 부착) · AC-AUTOPATCH-022③ 안내 문구 요구 철회 · **AC-AUTOPATCH-001 5건 → 6건**(`ASSUMPTION-76` 편입) · §C.0 REQ-018 행 **M4 → M5** · §C.0a **M4 4→3 · M5 3→4**(합 27 불변) |
| `plan.md` | §A.3에 **`ASSUMPTION-76` 부정 처리 행** 추가 · **M5를 "배포 · 실행"에서 "실행 전달(사람) · 검증 인계"로 축소** · M4의 AC 줄에서 015 제거 · §E 테스트 골격 `execute.py` 행 갱신 |
| `design.md` | §2.1 `apply.py` 역할에서 **실행 제거** · §3 흐름에서 `deploy_plugin` → `run_commands(["Plugin 'X'"])` 구간을 **"실행 전달 + 사람 실행"** 으로 교체 · 0건 분기 안내 문구 정정 |
| `research.md` | §2 룰북 주장 표에 **반증 주석**(2단계 절차 · CD 인과 · 편집기 안내 · 워크된 예제 = **G1 REFUTED**). 여전히 유효한 항목(필드 집합 · `mode` 핸들 형식 · `nil = 실패` · 점유폭 원칙)을 분리 명시 |

### 살아남은 것 / 축소된 것

| 마일스톤 | 영향 |
|---|---|
| M1 · M2 · M3 | **무영향** — 완료 상태 유지(테스트 45건) |
| M4 (Lua 생성 · 주소 계획) | **살아남음** — 생성물은 그대로 필요하다(사람이 실행할 소스가 곧 산출물) |
| M5 (배포 · 실행) | **축소** — "실행"에서 "실행 안내 + 검증 인계"로. AC 3건 → 4건(015 편입) |
| M6 (멱등 · 검증 읽기) | **살아남음** — `precheck_patch` 재조회는 실행 주체와 무관하다(결정 F) |
| M7 (툴 배선 · 회귀 · PRESERVE) | **살아남음** |
| M8 (라이브 종단) | 사람 실행 단계를 포함하는 형태로 재정의 필요(**미착수**) |

### 이 amendment가 하지 않은 것

- **L2를 측정하지 않았다.** 사용자 자원이 필요하며 미시험으로 남는다(§0).
  L2가 나중에 긍정으로 나오면 REQ-AUTOPATCH-018을 되돌릴 수 있다 — 그 가역성을 여기 남긴다.
- **`console/lua/**` 무접촉**(PRESERVE). responder 확장으로 배포·목적지를 해결하는 경로는
  여전히 **G3(별건 SPEC)** 이다.
- **코드 변경 0.** 본 amendment는 plan-phase 아티팩트만 고쳤다.
  테스트 **4,943 passed / 7 skipped** 불변 · `ruff check`·`format --check` 통과 ·
  PRESERVE 5경로 0-diff · HEAD `6039b0a`.

### 재감사 필요 — round6 PASS(1.000)는 v0.1.2에 대한 것이다

본 amendment는 요구·AC·마일스톤 경계를 건드렸으므로 **round6 PASS를 그대로 승계하지 않는다.**
독립 plan-audit(round7)을 받아야 하며, 감사 지적은 §E.1a에 이어 기록한다.
**작성자 ≠ 감사자** 원칙에 따라 감사는 별도 위임으로 수행한다.

---

## §E.3 Run-phase Audit-Ready Signal

(run-phase 완료 시 기록한다.)

---

## §E.4 Sync-phase Audit-Ready Signal

(sync-phase 완료 시 기록한다.)

---

## §F. Phase 4 Mode Selection — 확정 기록 (오케스트레이터 소유)

Decision: `sub-agent`

본 절은 **오케스트레이터가 첫 run-phase `Agent()` 스폰 전에 작성**하는 구속력 있는 기록이다.
`plan.md` §G의 대응 절은 **권고**이며 오케스트레이터가 확정하거나 기각한다.
어긋나면 **본 절이 이긴다.** 본문이 채워지기 전까지 이 절은 **비어 있음이 정상**이다.

### Input Parameters

```yaml
tier: L
scope: "server/vwx 확장 + 신규 orchestrator tool + tests, but M0 blocked before code"
domain_count: 2
file_language_mix: "Python + Markdown"
concurrency_benefit: LOW
agent_teams_prereq_status: "retired / not selectable"
implementation_kickoff_approval: "passed by coordinator handoff"
```

### Mode Evaluation

| mode | result | rationale |
|---|---|---|
| trivial | not selected | Tier L SPEC이며 M0 이후 여러 코드 마일스톤이 예정되어 있다. |
| background | not selected | run-phase 증거와 차단 판단은 동기 체크포인트가 필요하다. |
| agent-team | not selected | Mode 3 is retired. |
| parallel | not selected | M0가 M2·M3·M6 설계를 직렬로 결정하므로 병렬 이득이 낮다. |
| sub-agent | selected | coding-heavy work의 기본 안전 모드이며 `plan.md` §G 권고와 일치한다. |
| workflow | not selected | 고볼륨 기계적 변환이 아니며 M0 전제 측정이 먼저 필요하다. |

### Justification

`sub-agent`를 확정한다. 이 SPEC은 콘솔 쓰기를 포함하고 M0 판정이 후속 설계를 결정하므로,
한 번에 한 마일스톤씩 진행하는 직렬 모드가 맞다.
**실제 진행 (v0.1.4 기준 갱신 — round9 감사 N44)**: M0는 최초 시도에서 라이브 접근 부재로
BLOCKED였으나(§E.2 M0 checkpoint) **라이브 세션 1~5차로 종결**됐고(§E.2 M0 1~5차),
M1·M2·M3는 같은 sub-agent 모드로 **완료**됐다(§E.2 M1·M2·M3 절, 테스트 45건).
`ASSUMPTION-71`~`76`은 **6건 전부 판정 완료**이므로(71 GO · 72 GO(한정) · 73·74 INCONCLUSIVE ·
75·76 NEGATIVE) **M2 착수 게이트는 이미 해제**됐다. 남은 것은 M4·M6·M7이며 **M5는 축소**,
**M8은 사람 실행 단계를 포함하도록 재정의 필요**다 — 착수 전제는 plan-audit PASS(round10)뿐이다.
