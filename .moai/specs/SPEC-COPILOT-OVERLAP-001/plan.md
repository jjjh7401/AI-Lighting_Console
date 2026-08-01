# SPEC-COPILOT-OVERLAP-001 — 구현 계획 (plan)

status: draft (v0.1.0, 2026-07-30) · Tier M

> **v0.1.0 — 최초 작성.** 마일스톤 **M0~M8 9개**, 열린 결정 **0건**, clarification 마커 **0건**. 본 계획은 닫힌 정본 3종(`research.md` · `spec.md` · `acceptance.md`)과 오케스트레이터가 확정한 `CONTRACT.md`의 계수를 따른다: REQ **18** · AC **21** · ASSUMPTION **31~35 5건** · 라이브 세션 **0회**. 마일스톤별 `배정 AC`는 `CONTRACT.md` §5 표와 1:1이며 합 **21 · 중복 0 · 누락 0**이다(§B.10에서 별도 표로 재확인한다).
>
> **본 계획은 무엇을 만드는가를 정하지 않는다.** 무엇을 만드는가는 `spec.md`가, 왜 그 형상인가는 `design.md`가 소유한다. 본 문서는 **어떤 순서로 만드는가와 각 단계를 무엇으로 닫는가**만 답한다. `CONTRACT.md` §2의 결정 8건(D-1~D-8)과 §5의 마일스톤 경계는 재논의 대상이 아니며 본 계획은 그것을 상세화한다.
>
> **참조 규약.** 본 SPEC의 정본은 줄번호로 인용하지 않고 `REQ-OVERLAP-003` · `AC-OVERLAP-014` · `ASSUMPTION-34` 같은 안정 토큰과 절 제목으로만 참조한다. `파일:줄` 좌표는 **코드 · 룰북 · 응답기 프로토콜 · 타 SPEC 아티팩트**에만 쓴다. 요구·인수 토큰은 슬러그 포함 완전형만 쓴다(축약형 **0건**).
>
> **등급 규약.** `[코드]`(저장소 정적 조사) · `[문서]` · `[실측]`(**라이브 콘솔 직접 관측만**) · `[미확정]` · `[추론]`(저장소 근거에서 유도했으나 관측으로 확인되지 않음). **본 SPEC은 라이브 세션 0회이므로 본 계획이 자기 관측으로 주장하는 `[실측]`은 0건이다** — 실측 수치는 전부 `.moai/specs/SPEC-COPILOT-PRECHK-001/`을 출처로 하는 인용이며 그 사실을 인용마다 밝힌다.

---

## §A. 착수 전 상황

### §A.1 BASE — 세 개가 있고 섞으면 게이트가 죽는다

`CONTRACT.md` §4는 BASE 두 개를 못박았다. 계획 층에서는 **세 번째가 하나 더 있다** — 선례 트립와이어가 쓰는 SONGCUE BASE다. 셋의 용도가 다르므로 여기서 한 표에 모은다 `[코드]`.

| # | 용도 | SHA | 누가 쓰나 |
|---|---|---|---|
| 1 | **본 SPEC의 BASE** — 스위트·회귀·`server/safety/**` diff 기준 | `85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a` | `AC-OVERLAP-002` ③ · 각 마일스톤 무회귀 대조 · M8 역방향 검증 |
| 2 | **PRECHK PRESERVE 기준점 — 영구 불변** | `95687a0e0eba90b325daf76efbd0ac197e69e2fc` | `AC-OVERLAP-019` ①②④⑤ (M7 신규 게이트 파일) |
| 3 | SONGCUE run-phase BASE — **선례 파일 전용, 본 SPEC이 새로 쓰지 않는다** | `38a6e7e2157a4862721fcd868056e0dbbb09c4c0` | `server/tests/test_songcue_bundle.py:45`의 `_RUN_PHASE_BASE`. 보호구역 상수 `(234, 238)` · `(524, 569)`가 이 BASE 상대다(`server/tests/test_songcue_bundle.py:65`) |

**#2와 #3은 같은 파일에 살 수 없다.** `AC-OVERLAP-019` ⑥이 신규 게이트를 신규 파일에 두라고 요구하는 이유가 이것이며 수치 근거는 `research.md` §9.3이다 — 선례 값 `(234, 238)`을 PRECHK BASE에서 쓰면 주석 한복판을 지키고, `(524, 569)`는 dedupe 실행 루프보다 13행 앞에서 시작해 끝점 `failed = True`를 보호하지 못한다.

**본 계획이 직접 확인한 것** `[코드]`: `git show 95687a0e0eba90b325daf76efbd0ac197e69e2fc:server/orchestrator/tools.py`의 247행이 `_PROGRAMMER_STATE_COMMANDS = (`, 251행이 `)`, 537행이 `failed = False`, 582행이 `failed = True`다 — `CONTRACT.md` §4의 BASE 상대 좌표 `(247, 251)`·`(537, 582)`가 끝점 원문까지 재현된다. **같은 두 범위를 HEAD 기준으로 읽으면 247–251은 주석 본문이다**(HEAD의 `server/orchestrator/tools.py`는 1919행). 이 좌표는 **BASE 상대이며 HEAD 좌표로 옮겨 적으면 안 된다.**

### §A.2 착수 baseline — 이월 인용을 금지한다

| 항목 | 값 | 출처 |
|---|---|---|
| BASE SHA | `85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a` | `CONTRACT.md` §1 |
| 착수 baseline | **2758 passed · 5 skipped · 0 failed** | `CONTRACT.md` §1 · `spec.md` §C. **오케스트레이터의 실측 기록이며 본 계획의 관측이 아니다** |

**원칙: 각 마일스톤은 착수 직전에 baseline을 직접 실측한다.** 위 값은 BASE 시점의 기록일 뿐이고 run-phase 마일스톤 baseline으로 **이월하지 않는다.** 마일스톤 M`n`의 DoD가 *"계수가 baseline 이상"*이라고 말할 때 그 baseline은 **M`n` 자신이 착수 직전에 실행한 `uv run pytest server/tests/ -q`의 출력**이며, M`n-1`의 기록도 위 표의 2758도 아니다.

근거는 절차적이다. 선행 SPEC의 계획이 같은 원칙을 세웠고(`.moai/specs/SPEC-COPILOT-PRECHK-001/plan.md:101`) 그 SPEC의 스위트가 실제로 2490 → 2721 → 2758로 움직였다 `[문서]`. 이월 인용은 마일스톤 하나가 계수를 줄여도 다음 마일스톤이 그것을 정상으로 읽게 만든다.

### §A.3 사용자 승인 — 1건 확보, 추가 0건

| # | 접점 | 상태 | 내용 |
|---|---|---|---|
| 1 | **닫힌 판정 어휘 확장** | **승인 (2026-07-30)** | 신규 축 `overlap_basis` 4값 + `SKIPPED_CHECK_KIND` 1값. `spec.md` 머리말과 §A가 정본이다 |

**추가로 받을 사용자 승인은 0건이다.** 선행 SPEC의 최대 위험이 `server/safety/**` 조건부 예외 **승인 대기**였고 그것이 M1을 막고 M2 이후를 전부 정지시켰다(`.moai/specs/SPEC-COPILOT-PRECHK-001/plan.md:33`) `[문서]`. **본 SPEC에는 그 게이트가 없다** — 순회가 프로퍼티를 0건 읽고 `state`만 쓰므로 신규 예외 지점이 0건이다(`REQ-OVERLAP-002`). 따라서 코드 착수를 막는 승인은 존재하지 않는다.

**단 그 판정 자체가 `ASSUMPTION-34`이며 M0가 닫는다.** 부정이면 사용자 접점이 하나 열린다 — §E.2의 조건부 접점 1번이다.

### §A.4 라이브 세션 0회 — 이것이 PRECHK와 갈리는 지점이다

선행 SPEC은 라이브 2회(M0 전제 측정 · M8 종단)를 계획했다(`.moai/specs/SPEC-COPILOT-PRECHK-001/plan.md:179`) `[문서]`. **본 SPEC은 0회다.** 근거 넷.

1. **필요한 실측 값이 전부 선행 SPEC에 전재되어 있다.** 모드별 폭 29·29·29·31은 `.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:403`, 19슬롯 주소표는 `:308-326`, `DMXChannels` 열거가 `truncated=true`인데 `childCount`가 참값을 준다는 비대칭은 `:408`이다 — 전부 `[문서]` 인용이다. 본 SPEC이 요구하는 것은 **그 값을 런타임에 읽는 형상**이고 값 자체가 아니다(`REQ-OVERLAP-001`).
2. **M0의 판정 대상이 라이브를 요구하지 않는다.** `ASSUMPTION-34`는 *"`state` 표면만으로 3단 순회가 도달하는가"*이며 **인메모리 프로토타입 1개로 갈린다**(`research.md` §11 U-7). 콘솔에 붙어야 답이 나오는 질문이 아니다.
3. **M8의 판정 대상도 라이브를 요구하지 않는다.** `AC-OVERLAP-021`이 *"라이브 세션을 요구하지 않는다 — 인메모리 리그와 툴 디스패치로 닫힌다"*를 명문화했다.
4. **미확정 분기는 라이브로 관측할 수 없다.** 현재 쇼파일의 최소 간격이 42이고 상계가 31이므로 17개 인접쌍 **전부**가 `간격 ≥ 상계`다 — `bound_inconclusive`를 발동시키는 입력이 **0건**이다(`research.md` §3.2, `.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:1097` `[문서]`). 라이브에 붙어도 그 분기는 보이지 않는다. §C.4가 이것을 게이트 규율로 못박는다.

**귀결: 콘솔 접근 가능성은 본 SPEC의 착수 조건도 종료 조건도 아니다.** 라이브가 필요한 항목은 `ASSUMPTION-31` · `ASSUMPTION-32` · `ASSUMPTION-33`이며 셋 다 **다른 쇼파일**을 요구하므로 본 SPEC에서 닫히지 않고 `SKIP:` 접두로 기록된다(`AC-OVERLAP-020` ③).

### §A.5 PRESERVE 재확인 — 계획 층의 방침

| 항목 | 계획 방침 | 게이트 |
|---|---|---|
| `server/looks/{schema,loader,roles,resolver,instantiate,matching}.py` · `server/looks/library/` | 본 SPEC은 룩 계층 소비자가 아니다. 변경 0건 | `AC-OVERLAP-019` ① (PRECHK BASE) |
| `server/web/preview.py` | 웹 산출물 0건 | 같음 |
| `console/lua/**` | 상계가 요구하는 읽기 전량이 현재 `state` 표면으로 달성된다. 응답기 변경 0건. **잠금 근거를 여기 남기는 것이 절차 요건이다** — 선행 SPEC에서 오케스트레이터가 `plan.md`의 좁은 목록만 보고 정본 절을 읽지 않아 응답기 변경을 지시한 실수가 있었다(`spec.md` §C) | 같음 |
| `server/rulebook/assets/v2.4.2/**` | 룰북을 편집하지 않는다. `addr + 42` 레시피는 인용 대상이며 수정 대상이 아니다(`server/rulebook/assets/v2.4.2/30_plugin_patterns.md:37-56`) | 같음 |
| `server/orchestrator/tools.py`의 `_PROGRAMMER_STATE_COMMANDS`와 dedupe 실행 루프 | M6가 tools.py를 고치지만 두 보호구역에 hunk를 만들지 않는다 | `AC-OVERLAP-019` ④ (hunk 위치 봉쇄, PRECHK BASE 상대) |
| **`server/safety/**`** | 무변경. 단 이 판정이 `ASSUMPTION-34`이며 M0가 닫는다 | `AC-OVERLAP-002` ③④ (본 SPEC BASE) · `AC-OVERLAP-019` ⑤ (PRECHK BASE 파일집합 봉쇄) |
| `.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md` | **무변경.** `server/tests/test_prechk_patch.py:310-317` · `server/tests/test_prechk_macro.py:49` · `server/tests/test_prechk_inventory.py:196`이 그 문서를 읽고, `DESCOPE: ASSUMPTION-27` 접두 행이 정확히 1건이어야 한다. 본 SPEC의 게이트 행은 자기 `progress.md`에 쓴다 | `AC-OVERLAP-019` ⑧ |

**갱신이 강제되는 트립와이어 2건은 PRESERVE 위반이 아니다** — `server/tests/test_songcue_bundle.py:64`의 hunk 목록(M6 소유, §B.6), `server/tests/test_prechk_verdicts.py`의 재타이핑 정본 3단정(M1 소유, §B.1). **형태를 약화시키지 않는 것이 조건이다.**

**본 계획이 직접 확인한 게이트 현재 상태** `[코드]`:

```
git diff --stat 95687a0e0eba90b325daf76efbd0ac197e69e2fc..HEAD -- \
  server/looks/schema.py server/looks/loader.py server/looks/roles.py \
  server/looks/resolver.py server/looks/instantiate.py server/looks/matching.py \
  server/looks/library/ server/web/preview.py console/lua/ \
  server/rulebook/assets/v2.4.2/
→ 빈 출력

git diff --stat 95687a0e0eba90b325daf76efbd0ac197e69e2fc..HEAD -- server/safety/
→ server/safety/console.py | 30 ++++...   (추가 30 · 삭제 0)
  server/safety/gate.py    | 17 ++++...-  (추가 16 · 삭제 1)
  2 files changed, 46 insertions(+), 1 deletion(-)
```

**착수 시점에 ①이 초록이고 ⑤의 파일집합이 정확히 2개다.** `research.md` §9.4의 표와 전건 일치하며, 이것이 M7이 상수를 추측하지 않아도 되는 이유다.

---

## §B. 마일스톤 M0~M8

각 마일스톤은 **착수 직전 baseline을 직접 실측한다**(§A.2). 아래 `배정 AC`는 `CONTRACT.md` §5 표를 그대로 옮긴 것이며 재해석하지 않는다.

**착수 순서는 M0 → M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8 선형이다.** 두 순서 제약이 계약이다:

- **M0 이전에 M1에 착수하지 않는다** — `ASSUMPTION-34`가 부정이면 PRESERVE 서술이 바뀌고 그것이 M6·M7의 형상을 바꾼다(`CONTRACT.md` §5).
- **M1은 교차 슬라이스 선행물이다** — 어휘가 없으면 M3·M4·M5가 값을 낼 수 없다(§B.1의 마지막 항).

### §B.0 M0 — 전제 판정: `state`만으로 도달하는가

**목표.** `ASSUMPTION-34`를 닫는다. 3단 순회(`Patch/FixtureTypes` 열거 → 각 타입의 `DMXModes` 열거 → 각 모드의 `DMXChannels` `childCount`)가 `StateQueryPort.query_state` **하나로만** 도달하는지, 아니면 프로퍼티 조회가 한 번이라도 필요한지를 인메모리 프로토타입으로 갈라 낸다. `GO`면 `server/safety/**` 무변경이 확정되어 `AC-OVERLAP-002` ③과 `AC-OVERLAP-019` ⑤가 착수 시점 값으로 성립하고, 부정이면 범위를 재개정한다. **라이브는 필요하지 않다**(§A.4의 2번).

- **`cycle_type`**: **`none`** — 측정 마일스톤이며 **코드 변경 0건**이다.
- **산출 파일**
  - 구현: **0건.**
  - 테스트: **0건.**
  - 기록: `.moai/specs/SPEC-COPILOT-OVERLAP-001/progress.md`의 M0 절. **이것이 M0의 유일한 산출물이다.**
  - **인메모리 프로토타입은 추적되지 않는 생산물이며 판정 직후 삭제한다.** 커밋하지 않고 `server/`나 `server/tests/`에 남기지 않는다. 프로토타입이 남으면 그것은 `cycle_type=none`의 위반이고, `git status --porcelain`이 그것을 기계로 적발한다(DoD 4·5).
- **배정 AC**: `AC-OVERLAP-020`.
- **진입 조건 (기계 판정)**
  1. `git rev-parse HEAD`가 `85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a`의 자손임을 `git merge-base --is-ancestor 85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a HEAD`가 종료 코드 0으로 확인한다.
  2. `uv run pytest server/tests/ -q`를 직접 실행해 baseline을 기록한다. 실패 0건이어야 한다.
- **종료 조건 (DoD · 전건 기계 판정)**
  1. `progress.md`에 `ASSUMPTION-31`~`ASSUMPTION-35` **5건 전부**의 접두 행이 있고, 네 접두어(`GO:` · `DESCOPE:` · `SKIP:` · `REOPEN:`)로 시작하는 행의 합이 **정확히 5행**이다. 한 전제가 두 행을 갖지 않는다(`AC-OVERLAP-020` ①).
  2. `ASSUMPTION-34` 행에 프로토타입이 호출한 **포트 메서드 이름 목록**이 병기되어 있고 그 목록이 **비어 있지 않다**. 비공허성 조건이다 — 빈 목록으로 `GO`를 적으면 아무것도 실행하지 않고 판정한 것이다.
  3. `ASSUMPTION-31` · `ASSUMPTION-32` · `ASSUMPTION-33` 3건의 접두어가 **`SKIP:`**이고 각 행이 **무엇을 측정·조회하면 갈리는지**를 담는다. 이 셋 중 하나라도 `GO:`면 **실패로 판정한다** — 관측 없이 닫을 수 없다(`AC-OVERLAP-020` ③).
  4. `git status --porcelain -- server/ console/`이 **빈 출력**이다 — 코드 변경 0건의 기계 확인.
  5. `git status --porcelain`이 **빈 출력**이다 — 프로토타입이 워킹트리에 남지 않았음의 기계 확인(4의 상위 조건이며 `.moai/` 기록 커밋 이후에 판정한다).
  6. `uv run pytest server/tests/ -q`의 계수가 DoD 진입 시 기록한 baseline과 **동일**하다. 코드 변경 0건이므로 증가도 감소도 결함이다.
- **건드리는 기존 테스트**: **0건.** M0는 코드도 테스트도 만들지 않으므로 갱신 정당화가 필요한 대상이 없다.
- **`ASSUMPTION-34` 부정 시의 분기 — 미리 정의한다**

  부정은 *"3단 순회가 `query_property`를 한 번이라도 요구한다"*를 뜻한다. 그때 정의된 결과는 셋이며, **워커 재량이 아니라 오케스트레이터 접점이다**(§E.2 조건부 1).

  | # | 무엇이 바뀌나 | 근거 |
  |---|---|---|
  | 1 | **`spec.md` §C의 PRESERVE 서술을 개정한다** — *"본 SPEC은 `server/safety/**`를 무변경으로 둔다"*를 *"PRECHK가 연 조건부 예외 4지점을 재사용한다"*로 바꾸고 **사유를 기록한다** | `AC-OVERLAP-020` ② |
  | 2 | **M6의 형상이 바뀐다** — 순회가 프로퍼티 포트를 요구하므로 `build_toolset`의 `property_port` 경로를 순회에 스레딩해야 하고, `AC-OVERLAP-002` ①(`query_property` 호출 0건 · AST 식별자 스캔)이 **개정 대상**이 된다 | `server/orchestrator/tools.py:537-538`이 `property_port`를 `state_port`에서 승격시키는 기존 이음새다 `[코드]` |
  | 3 | **M7의 형상이 바뀐다** — `AC-OVERLAP-002` ③의 *"safety diff가 빈 출력"*이 성립하지 않고, `AC-OVERLAP-019` ⑤의 파일집합 봉쇄(정확히 2파일 · 삭제 0/≤1)를 **재계수해야 한다** | §A.5의 실측 표가 그 2파일의 착수 시점 값이다 `[코드]` |

  **정본 개정은 M0가 직접 하지 않는다.** M0는 판정과 사유를 `progress.md`에 쓰고 오케스트레이터에게 정본 개정 필요를 올린다 — 선행 SPEC이 *"plan-phase 산출물은 그 시점의 판단 기록이고 사후 재작성은 흐린다"*를 못박았고(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:679-681`) `[문서]` 그 규율이 정본에도 적용된다.

### §B.1 M1 — 어휘 확장

**목표.** 승인된 어휘 확장을 **13편집점 + 배선 3** 전부 집행한다 — 신규 축 생성 **10** + 기존 축 값 추가 **3**(`research.md` §7.1). 신규 축 `overlap_basis` 4값과 `SKIPPED_CHECK_KIND`의 1값을 넣고, 라벨표 `OVERLAP_BASIS_LABELS`를 만들고, **import 시점 가드 루프를 레지스트리 순회로 구조 변경하고**(D-6), 재타이핑 정본 3단정을 갱신한다. 이 마일스톤의 산출물은 다음 축을 추가하는 사람이 같은 함정을 만나지 않는 **구조**다.

- **`cycle_type`**: **`tdd`**.
- **산출 파일**
  - 구현(갱신): `server/prechk/verdicts.py` — 신규 축 상수 · `CLOSED_VOCABULARIES` **맨 끝 append** · `SKIPPED_CHECK_KIND`에 값 1개(D-5).
  - 구현(갱신): `server/prechk/report.py` — `OVERLAP_BASIS_LABELS` 신설 · `VOCABULARY_LABELS`에 항목 1개 · **가드 루프(`server/prechk/report.py:111-119`)를 `CLOSED_VOCABULARIES` 순회로 교체**.
  - 테스트(갱신): `server/tests/test_prechk_verdicts.py` — 재타이핑 정본 3단정(집합 동일성 `:26-45` · 레지스트리 키 동일성 `:47-54` · 레지스트리 **순서** 동일성 `:55-61`).
  - 테스트(갱신): `server/tests/test_prechk_report.py` — 라벨표 순회 단정(`:273-278`)은 형태 무변경이고 신규 축을 자동 포함한다. 가드 형태 변경에 대한 단정을 추가한다.
  - 신규 파일: **0건.**
- **배정 AC**: `AC-OVERLAP-014`.
- **절차 순서 — 이 순서를 지킨다. D-6이 무증상 단계를 구조적으로 없애는 결정이므로 구조 변경이 먼저다**

  `research.md` §7.2가 확정한 것: **`server/prechk/report.py`의 가드 루프는 하드코딩 5-튜플이며 신규 축을 빠뜨려도 어떤 테스트도 실패하지 않는다.** import은 성공하고, 라벨 드리프트는 `server/tests/test_prechk_report.py:273-278`이 `CLOSED_VOCABULARIES`를 순회하므로 여전히 잡히며, 따라서 **실패 0건**이다. 잃는 것은 신규 축의 import 시점 결속뿐이다. 스위트가 못 잡는 단계가 정확히 여기 하나다.

  | 단 | 작업 | 이 단계가 끝난 뒤 성립해야 하는 것 |
  |---|---|---|
  | 1 | **가드 루프를 `CLOSED_VOCABULARIES` 순회로 먼저 바꾼다 — 신규 축 도입 *이전*에.** 이 시점의 어휘는 5종이므로 하드코딩 5-튜플과 순회가 **같은 결과**를 낸다 | `uv run pytest server/tests/ -q`가 baseline과 동일. 즉 구조 변경 단독으로는 무회귀다 |
  | 2 | 1의 성질을 테스트로 고정한다 — 라벨표에서 **기존 축**의 항목 1개를 제거하면 `import server.prechk.report`가 예외를 낸다 | `AC-OVERLAP-014` ⑦의 판정이 **신규 축 없이** 이미 성립한다 |
  | 3 | `server/prechk/verdicts.py`에 신규 축 상수 + 레지스트리 **맨 끝 append** | 이 상태에서 `import server.prechk.report`가 **실패한다** — 순회 가드가 라벨표에 없는 축을 즉시 적발한다 |
  | 4 | `server/prechk/report.py`에 `OVERLAP_BASIS_LABELS` + `VOCABULARY_LABELS` 항목 | import 복구. **3과 4 사이에 무증상 창이 없다** — 그것이 1을 먼저 한 값이다 |
  | 5 | `SKIPPED_CHECK_KIND` += `range_overlap_bound_inconclusive` + 대응 라벨 | 기존 축 값 추가 3편집점 완료 |
  | 6 | `server/tests/test_prechk_verdicts.py` 정본 3단정 갱신 | 집합 · 키 · **순서** 셋 다 유지. 어느 하나도 삭제하거나 부분집합으로 약화시키지 않는다 |

  **1을 마지막에 하면 3과 4 사이에 무증상 창이 열린다.** 그 창에서 4를 빼먹으면 스위트가 초록인 채로 신규 축이 import 결속을 잃는다 — 이 프로젝트가 P1 4건을 2721개 전부 통과하는 상태에서 살려 둔 것과 같은 계열이다(규율 16, `.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:1247` `[문서]`). **순서가 곧 결함 예방이다.**

- **진입 조건 (기계 판정)**
  1. M0의 DoD 6항 전건 충족.
  2. `progress.md`에 `ASSUMPTION-34` 접두 행이 존재한다 — M0가 판정을 남겼음의 확인.
  3. `ASSUMPTION-34`가 부정이면 **M1에 착수하지 않고** §B.0의 부정 분기를 먼저 집행한다.
  4. baseline 직접 실측.
- **종료 조건 (DoD · 전건 기계 판정)**
  1. `python -c "import server.prechk.report"`가 종료 코드 0.
  2. `uv run pytest server/tests/test_prechk_verdicts.py server/tests/test_prechk_report.py -q` 전건 통과.
  3. **뮤테이션 A**: `OVERLAP_BASIS_LABELS`에서 항목 1개를 제거하면 `import server.prechk.report`가 예외를 낸다(`AC-OVERLAP-014` ⑥⑦). killed로 기록한다.
  4. **뮤테이션 B**: 레지스트리에서 신규 축 항목을 제거하면 `server/tests/test_prechk_verdicts.py`의 집합·키·순서 3단정 중 **최소 1건**이 실패한다. killed로 기록한다.
  5. `git diff 85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a..HEAD -- server/prechk/verdicts.py`의 `CLOSED_VOCABULARIES` 기존 5줄이 **바이트 동일**하다 — append-last의 기계 확인(D-5).
  6. `COLLISION_KIND`와 `FIXTURE_VERDICT`가 착수 시점과 **바이트 동일**하다(`AC-OVERLAP-014` ③). 어휘 파생 단정 3건이 무변경으로 통과하는 것이 그 확인이다.
  7. 신규 축의 값 집합이 정확히 `{exact_widths, bound_proves_clear, bound_inconclusive, not_performed}`이고, `SKIPPED_CHECK_KIND`의 그 밖 값이 착수 시점과 동일하다(`AC-OVERLAP-014` ①②).
  8. 라벨표 이름이 `OVERLAP_BASIS_LABELS`이며 `_LABELS`로 끝난다(`AC-OVERLAP-014` ⑤ · `CONTRACT.md` §2 D-5).
  9. 어휘 코드 문자열이 표현 계층에서 **라벨표 대입 안에서만** 철자된다. 그 밖의 리터럴 사용 0건이며, **스캔이 수집한 코드 수 ≥ 신규 값 수**를 함께 단정한다(`AC-OVERLAP-014` ⑧, 비공허성).
  10. 금지 토큰 스캐너 3종이 신규 어휘 전량을 통과한다 — `proven` · `verified` · `all_clear` · `_lit` 계열 0건(`AC-OVERLAP-014` ⑨ · `research.md` §7.6).
  11. `uv run pytest server/tests/ -q`의 계수가 진입 시 실측한 baseline **이상**이다.
- **건드리는 기존 테스트와 갱신 정당화**

  | 대상 | 갱신 성격 | 왜 정당한가 |
  |---|---|---|
  | `server/tests/test_prechk_verdicts.py:26-61` | **트립와이어 갱신 = 집행** | 어휘 확장이 사용자 승인 사항이므로 재타이핑 정본을 갱신하는 것이 **승인의 집행**이다(`spec.md` §C). **형태를 약화시키지 않는 것이 조건**이며 DoD 4·6이 그것을 기계로 판정한다 |
  | `server/tests/test_prechk_report.py:273-278` | **무변경 통과** | 이 단정은 이미 `CLOSED_VOCABULARIES`를 순회하므로 신규 축을 자동 포함한다. 코드를 고칠 필요가 없고, 고치면 그 자체가 약화 신호다 |
  | `server/prechk/report.py:111-119` | **구조 교체** | 하드코딩 5-튜플 → 레지스트리 순회. `AC-OVERLAP-014` ⑦이 이 형태를 명시적으로 인정한다. 튜플에 항목을 추가하는 것으로 끝내지 않는다(D-6) |

- **M1이 교차 슬라이스 선행물인 이유 — 기계적이다**

  `server/prechk/verdicts.py:50`의 `validate(vocabulary, value)`는 **알려지지 않은 어휘 이름에 대해 예외를 던진다**(`server/prechk/verdicts.py:57-60`) `[코드]`. 그리고 `server/prechk/patch.py:52-53`이 보여 주듯 판정 계층의 코드값 상수는 **모듈 로드 시점에 `validate(...)`를 통과해야 한다.** 따라서 M1이 레지스트리에 `overlap_basis`를 넣기 전에는 M3·M4·M5가 그 축의 값을 **상수로 선언할 수조차 없다** — 모듈 import이 실패한다. **어휘 없이는 세 마일스톤이 값을 낼 수 없다**는 것은 정책이 아니라 물리다.

### §B.2 M2 — 순회 모듈

**목표.** `server/prechk/footprint.py`를 신설한다(D-1). 3단 순회 · 완전성 술어 **2종** · 조회 예산 · 실패 분류를 담는다. 이 모듈은 `server.orchestrator.tools`를 import하지 않으며 **경로와 예산 상한을 인자로 받는 순수 함수**다.

- **`cycle_type`**: **`tdd`**.
- **산출 파일**
  - 구현(신규): `server/prechk/footprint.py`.
  - 테스트(신규): `server/tests/test_prechk_footprint.py`.
  - 갱신: **0건.**
- **배정 AC**: `AC-OVERLAP-001` · `AC-OVERLAP-002` · `AC-OVERLAP-003` · `AC-OVERLAP-004` · `AC-OVERLAP-005` · `AC-OVERLAP-006` (**6건**).
- **진입 조건 (기계 판정)**
  1. M1의 DoD 11항 전건 충족. 특히 1항(`import server.prechk.report` 성공)이 없으면 순회 모듈이 판정 어휘를 쓸 수 없다.
  2. baseline 직접 실측.
- **종료 조건 (DoD · 전건 기계 판정)**
  1. `python -c "import server.prechk.footprint"`가 종료 코드 0 — 단독 import 가능(`AC-OVERLAP-005` ③). 이것이 D-1의 A-4(핸들러 클로저) 배치를 배제하는 기계 판정이다.
  2. **AST import 스캔**: `server.orchestrator.tools` import **0건** + 방문한 import 노드 수 ≥ 1(`AC-OVERLAP-005` ②, 비공허성).
  3. **AST 호출 스캔**: 포트 사용이 `query_state` **하나**이고 `query_property` 호출 **0건** + 방문한 호출 노드 수 ≥ 1(`AC-OVERLAP-002` ①).
  4. **AST 상수 스캔**: `server/prechk/**`의 상수 집합에 `29` · `31` · `42` · `50`이 폭·간격·상계 의미로 **0건** + 방문한 파일 수 ≥ 1 + 수집한 상수 노드 수 ≥ 1(`AC-OVERLAP-001` ①). 스캔 범위는 `server/prechk/`이며 `server/tests/`가 아니다.
  5. 인메모리 리그에 모드 폭 `{17, 23}`을 주입하면 상계가 **23**으로 산출된다(`AC-OVERLAP-001` ②) — 산출값이 주입값에서 나오고 인용된 실측 31에 고정되어 있지 않음의 확인.
  6. 조회 경로가 `Patch/FixtureTypes` → `…/<t>/DMXModes` → `…/<t>/DMXModes/<m>/DMXChannels` 순서로 기록되고 **기록된 경로 수 ≥ 3**(`AC-OVERLAP-001` ③).
  7. **AST 스캔**: 3단에서 `children`을 참조하는 지점 **0건** + 방문한 함수 수 ≥ 1(`AC-OVERLAP-001` ④). 폭을 읽는 유일한 값이 `node.childCount`다.
  8. `AC-OVERLAP-003` ①②③④: 1단이 짧을 때 · 2단이 짧을 때 · 예산이 소진될 때(예산을 2로 낮춘 리그) · 조회가 예외를 낼 때 **네 경우 모두** 상계가 산출되지 않고 판정이 `not_performed`다.
  9. **AST 제어 흐름 판정**: `max`(또는 그 역할을 하는 축약)를 포함하는 노드가 **완전성 판정 분기의 내부**에 있다 + 방문한 함수 수 ≥ 1(`AC-OVERLAP-003` ⑤). 부분 결과를 `max`에 넣고 사후에 플래그로 무효화하는 제어 흐름은 그 자체가 결함이다(`REQ-OVERLAP-003`).
  10. **`AC-OVERLAP-003` ⑥ 거짓 양성 재현 테스트가 존재하고, 수정 전 코드에서 실패함이 역방향으로 확인된다.** 모드 폭 `{29, 29, 29, 31}` · 2단 예산 3 · 최소 간격 30인 리그에서 판정이 `bound_proves_clear`가 **아니다**. §C.3의 절차로 확인하고 killed로 기록한다.
  11. `AC-OVERLAP-004` ①②를 **한 테스트에서 함께** 돌려 결과가 다름을 단정한다(④). 3단은 `truncated=true`·`children=[]`이어도 폭 판독이 **성공**하고, 1단이 `truncated=true`면 상계를 **계산하지 않는다**. 그리고 3단 술어가 `childCount > len(children)` 비교를 **쓰지 않는다**(③).
  12. `AC-OVERLAP-006` ①②③④: 두 실패가 서로 다른 사유 코드이고 그 코드가 기존 `REASON_UNRESOLVED` / `REASON_UNREACHABLE`(`server/orchestrator/tools.py:196-197`)이며 새 사유 어휘 신설 0건이고, 프로덕션 게이트 포트가 두 경우를 **같은 예외 타입**으로 던지는 것을 테스트가 재현하고도(`server/safety/console.py:387-388`) 구분이 성립하며, 사용자가 읽는 문자열이 두 경우에 다르고 어느 쪽도 *"겹침이 없다"*나 *"모드가 없다"*를 말하지 않는다.
  13. `git diff --stat 85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a..HEAD -- server/safety/`가 **빈 출력**이고, 같은 명령을 `server/prechk/`에 대해 돌리면 **비어 있지 않다**(`AC-OVERLAP-002` ③④ — 비공허성).
  14. `PROPERTY_WHITELIST`가 착수 시점과 **바이트 동일**하다(`AC-OVERLAP-002` ②).
  15. `uv run pytest server/tests/ -q`의 계수가 baseline **이상**.
- **건드리는 기존 테스트와 갱신 정당화**

  **갱신 0건이다.** 소비만 하는 기존 테스트가 둘 있고 **무변경으로 통과해야 한다**:

  | 대상 | 무엇을 확인하나 |
  |---|---|
  | `server/tests/test_prechk_inventory.py:693-699` | `Inventory.queried_paths`의 전 항목이 픽스처 루트 하위여야 한다. 순회가 자기 조회 기록을 **별도 자료구조**에 담으므로 무변경 통과한다 — 이것이 D-1이 A-1(`inventory.py` 확장)을 배제한 기계 판정의 뒷면이다 |
  | `server/tests/test_prechk_inventory.py:378-399` · `:715-716` | 금지 프로퍼티명 스캔. `"Footprint"` · `"Channels"` · `"ChannelCount"` · `"Universe"` · `"Address"` · `"No"` · `"Break"`가 정확 문자열로 금지되므로 **신규 모듈 안에서 이 일곱을 문자열 리터럴로 쓰지 않는다**(`CONTRACT.md` §2 D-1). 소문자 모듈명 `footprint.py`는 그 스캔의 대상이 아니다 |

### §B.3 M3 — 상계 판정

**목표.** 간격 산수와 판정 술어를 넣는다. 술어는 **`간격 < 상계`**이며 `간격 == 상계`는 **증명 가능하게 깨끗하다**. 간격은 **각 유니버스 내부에서만** 계산하고, 주소는 계산에 쓰기 전에 **유효 범위를 검증**하고, 증명되지 않은 쌍은 **충돌이 아니라 미확정**으로 남긴다.

- **`cycle_type`**: **`tdd`**.
- **산출 파일**
  - 구현(갱신): `server/prechk/footprint.py` — 인접 간격 · 최소값 · 판정 술어. 저장소 전체에 `a[i+1]-a[i]`를 구하는 지점이 0건이므로 신규다(`research.md` §6.5).
  - 구현(갱신): `server/prechk/patch.py` — `_address_duplicates`(`server/prechk/patch.py:266`)의 `(유니버스, 주소)` 그룹핑을 **키 집합**으로 추출해 상계 경로가 쓴다(D-7). 주소 유효 범위 검증. 미확정을 `range_overlaps`에 넣지 않는 분기.
  - 테스트(갱신): `server/tests/test_prechk_footprint.py`, `server/tests/test_prechk_patch.py`.
  - 신규 파일: **0건.**
- **배정 AC**: `AC-OVERLAP-008` · `AC-OVERLAP-009` · `AC-OVERLAP-010` · `AC-OVERLAP-011` · `AC-OVERLAP-012` (**5건**).
- **진입 조건 (기계 판정)**
  1. M2의 DoD 15항 전건 충족.
  2. baseline 직접 실측.
- **종료 조건 (DoD · 전건 기계 판정)**
  1. `AC-OVERLAP-008` ①②③④: 상계 `W`에 대해 간격 `W-1` → `bound_inconclusive` · 간격 **정확히 `W`** → `bound_proves_clear` · 간격 `W+1` → `bound_proves_clear`. 셋이 **같은 리그 형상에서 간격만 바꿔** 돌아가고 ①이 ②③과 다름을 단정한다. **②가 off-by-one을 잡는 경계 테스트다** — `.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md` §E.6 ④의 *"상계 이하라 미확정"* 표현으로 구현하면 실패한다(`research.md` §3.1이 코드로 정정했다).
  2. `AC-OVERLAP-009` ①: 유니버스 1의 마지막 주소와 유니버스 2의 첫 주소 사이 차분이 간격 집합에 **없다** — `1.500`과 `2.001`처럼 인접해도 없다.
  3. `AC-OVERLAP-009` ②: 간격 총수가 `Σ (n_u - 1)`이다. 실측 리그 형상(10 + 9)에서 **17**이며, **그 17을 상수로 박지 않고 리그 형상에서 계산한다**(`AC-OVERLAP-001` ①의 하드코딩 금지와 같은 규율).
  4. **뮤테이션**: 구간 겹침 축에서 유니버스 키잉을 제거하면(단일 공간으로 붕괴) 테스트가 실패한다(`AC-OVERLAP-009` ③). 대응 테스트가 **정확폭 축과 상계 축 양쪽에** 존재한다(④). **착수 시점에 이 뮤테이션이 살아 있었음**을 확인·기록한다 — `_range_overlaps`를 두 유니버스로 밟는 테스트가 0건이었고 서로소성을 고정하는 테스트는 주소 중복 축의 `server/tests/test_prechk_patch.py:184-189` 1건뿐이었다(`research.md` §5.5).
  5. `AC-OVERLAP-010` ①②: 같은 `(유니버스, 주소)`를 둘 이상이 점유하면 그 주소가 간격 집합에 **한 번만** 들어가고 간격 0이 산출되지 않으며, 같은 리그에서 주소 중복 축이 그것을 검출한다 — 이중 계상이 아니라 **분업**이다.
  6. `AC-OVERLAP-010` ③④: 픽스처타입·모드가 판독 실패인 픽스처가 **간격 계산에 포함**되고, 같은 픽스처가 **정확폭 축에서는 제외**된다. 두 축의 술어가 다름을 한 테스트에서 단정한다. 근거는 D-7 — `_range_overlaps`(`server/prechk/patch.py:324`)는 `type_mode_ok`를 요구하지만 `_address_duplicates`는 요구하지 않고, **상계 논증의 요점이 "어느 모드를 쓰는지 몰라도 성립"이므로 후자의 술어가 맞다.**
  7. `AC-OVERLAP-011` ⑤ **먼저**: `bound_inconclusive`가 실제로 산출됨을 단정한다. 그 다음 ①②③: `collisions.range_overlaps`가 **빈 목록** · 충돌 계수 **0** · 관여 픽스처 verdict가 `collision`이 **아니다**. ⑤ 없이 ①②③만 쓰면 공허하다.
  8. `AC-OVERLAP-011` ④: 사용자가 읽는 요약이 그 상태를 **말하고**, 그 라벨이 *"이상 없음"*을 뜻하지 않는다. (요약 도달의 전량 판정은 M5 소유이며 여기서는 미확정 상태가 침묵으로 처리되지 않음만 고정한다.)
  9. `AC-OVERLAP-012` ①②③④: `0.0` · `1.0` · `0.1`이 간격 계산에 **들어가지 않고**, 범위를 벗어난 주소가 **판독 실패로 분류되어 보고**되며 *"그런 픽스처가 없다"*로 바뀌지 않고, 유효한 `1.001` · `2.401`은 그대로 통과하며(과잉 거부 방지), **범위 상한이 코드에 상수로 박혀 있지 않다**. 착수 시점에 `0.0` · `1.0` · `1.99999`가 `ok=True`로 통과함이 조사에서 실행 확인됐다(`research.md` §4.4).
  10. `uv run pytest server/tests/ -q`의 계수가 baseline **이상**.
- **건드리는 기존 테스트와 갱신 정당화**

  **갱신 0건 — 추가만 한다.** 아래 셋이 **무변경으로 통과해야 하며** 그것이 M3의 무회귀 판정이다:

  | 대상 | 무엇을 확인하나 |
  |---|---|
  | `server/tests/test_prechk_patch.py:217-226` | 기존 정확폭 GO 분기. `overlap.universe == 1` · `overlap.span == (1, 43)` 등이 그대로 성립해야 한다 — 상계 축 추가가 정확폭 경로를 바꾸지 않았음의 확인 |
  | `server/tests/test_prechk_patch.py:184-189` | 주소 중복 축의 유니버스 서로소성. M3가 상계 축에 같은 성질을 **추가**하되 기존 단정을 대체하지 않는다 |
  | `server/tests/test_prechk_patch.py:310-317` | `DESCOPE: ASSUMPTION-27` 접두 행이 PRECHK `progress.md`에 정확히 1건. 본 SPEC이 `ASSUMPTION-27`을 뒤집지 않고 그 문서를 건드리지 않음의 기계 확인 |

### §B.4 M4 — 정확폭 우선 · 근거 배선

**목표.** 정확폭이 상계보다 **우선**하게 하고, `overlap_basis`를 **신규 최상위 키**에 실어 리그 전역 스칼라로 내보내고, 상계의 **근거**(값 + 출처)를 페이로드에 도달시키고, 순회 실패가 리포트의 나머지를 잃지 않게 한다.

- **`cycle_type`**: **`tdd`**.
- **산출 파일**
  - 구현(갱신): `server/prechk/patch.py` — 정확폭 우선순위 · 신규 최상위 키(키 이름은 `design.md` 소유) · 근거 자료구조 · 순회 실패 격리.
  - 테스트(갱신): `server/tests/test_prechk_patch.py`, `server/tests/test_prechk_footprint.py`.
  - 신규 파일: **0건.**
- **배정 AC**: `AC-OVERLAP-007` · `AC-OVERLAP-013` · `AC-OVERLAP-016` (**3건**).
- **진입 조건 (기계 판정)**
  1. M3의 DoD 10항 전건 충족.
  2. baseline 직접 실측.
- **종료 조건 (DoD · 전건 기계 판정)**
  1. `AC-OVERLAP-016` ④: 신규 최상위 키에 대해 **정확 키집합 단정을 새로 만든다** — `set(payload[<신규 키>]) == {...}` 형태. 기존 `server/tests/test_prechk_patch.py:442-450`의 부분집합 단정과 `server/tests/test_prechk_report.py:103-114`의 포함 단정은 **그대로 두고 추가한다.** 착수 시점에 최상위는 부분집합·포함 단정만 있어 키를 얹어도 아무것도 깨지지 않으므로(`research.md` §8.1·§8.2) 새 단정 없이 얹으면 커버 침식이다.
  2. `AC-OVERLAP-016` ①②③: 페이로드에 상계 값과 **출처 문자열**이 실리고, 출처가 **어느 경로의 어느 계수**에서 왔는지 식별하며(자유 산문이 아니라 경로를 담는다), 근거 필드를 담는 자료구조와 페이로드 키가 **함께** 존재한다. 선례는 `server/prechk/patch.py:159-170`의 `FootprintPolicy.source`가 필드로 있으면서 페이로드에 나가지 않아 소비자 0건으로 죽어 있는 것이다 `[코드]`.
  3. `AC-OVERLAP-013` ①②③: 정확폭이 주어진 슬롯은 `exact_widths`, 없는 슬롯에만 상계, 혼재 리그에서 둘 다 수행되고 결과가 각각의 근거로 보고된다.
  4. `AC-OVERLAP-013` ④: 착수 시점의 정확폭 테스트가 **전건 통과** — 기존 `FootprintPolicy` 경로 무회귀.
  5. `AC-OVERLAP-013` ⑤: 착수 시점에 존재하던 부분 커버리지 고지가 **여전히 발화**한다 — 정확폭도 상계도 없는 슬롯이 있으면 미수행이 고지된다(`server/prechk/patch.py:305`의 `_judgeable_without_width` 형상).
  6. **D-4 정직성 판정 1**: 리그 전역 스칼라가 **수행된 비교 전체의 최약 등급**이다. 3슬롯이 비교되지 않은 상태에서 `bound_proves_clear`를 리그 전역으로 찍으면 **실패하는 테스트**가 존재한다.
  7. **D-4 정직성 판정 2**: `range_overlap_bound_inconclusive`가 **kind당 1행**만 리포트에 도달하고, 한 행의 `reason`에 유니버스·슬롯을 열거한다. `server/tests/test_prechk_patch.py:245`의 `skipped_checks[]` 행 **정확 3키** 단정이 무변경 통과한다.
  8. `AC-OVERLAP-007` ①: 순회가 전면 실패한 리그에서 `inventory` 블록의 `observed_count`가 순회 성공 시와 **동일**하다.
  9. `AC-OVERLAP-007` ②: 같은 리그에서 주소 중복 판정이 여전히 수행되고 **심은 중복이 검출된다**(중복 0건이면 이 단정이 공허하므로 비공허성이 조건이다).
  10. `AC-OVERLAP-007` ③④: `overlap_basis`가 `not_performed`이고 `skipped_checks`에 대응 행이 있으며, 요약이 *"충돌 0건"*을 **한정 없이** 말하지 않는다.
  11. `server/tests/test_prechk_report.py:116-119`의 `collisions` 딕셔너리 **전체 동등** 단정이 무변경 통과한다 — 미확정을 `range_overlaps`에 넣지 않았음의 기계 확인.
  12. `uv run pytest server/tests/ -q`의 계수가 baseline **이상**.
- **건드리는 기존 테스트와 갱신 정당화**

  **갱신 0건 — 추가만 한다.** `server/tests/test_prechk_patch.py:442-450`(최상위 부분집합) · `:451`(collisions 정확 2키) · `:453-464`(fixtures 행 정확 10키) · `server/tests/test_prechk_report.py:103-119`가 **전부 무변경 통과해야 한다.** D-4가 신규 최상위 키를 고른 이유가 이것이며, **DoD 1이 그 자리를 새로 잠그는 대가를 함께 지불한다.**

### §B.5 M5 — 리포트

**목표.** `overlap_basis` 라벨을 **사용자가 실제로 읽는 문자열**에 도달시킨다. 그리고 `bound_proves_clear`가 *"관측된 모드 집합에 한정해"*를 함께 말하게 한다.

- **`cycle_type`**: **`tdd`**.
- **산출 파일**
  - 구현(갱신): `server/prechk/report.py` — 요약 배선(`server/prechk/report.py:169`의 `summary_ko` 계열).
  - 테스트(갱신): `server/tests/test_prechk_report.py`.
  - 신규 파일: **0건.**
- **배정 AC**: `AC-OVERLAP-015` · `AC-OVERLAP-017` (**2건**).
- **진입 조건 (기계 판정)**
  1. M4의 DoD 12항 전건 충족.
  2. baseline 직접 실측.
- **종료 조건 (DoD · 전건 기계 판정)**
  1. `AC-OVERLAP-017` ①④: `overlap_basis` **4값 각각**에 대해 그 값이 산출된 리그의 요약 문자열에 대응 라벨이 포함되고, **4값 전부가 테스트에서 실제로 산출된다**(비공허성). 산출되지 않는 값이 있으면 그 값은 죽은 어휘다.
  2. `AC-OVERLAP-017` ②: **AST로 확인한다** — 라벨이 표현 계층의 표에서 오고 판정 계층이 한국어를 만들지 않는다.
  3. `AC-OVERLAP-017` ③: 라벨 집합과 어휘 집합이 **정확히 일치**한다(양방향). `server/tests/test_prechk_report.py:273-278`의 순회가 신규 축을 자동 포함하므로 이 단정은 M1의 구조 변경 위에서 자동 성립하며, M5는 **그것이 성립함을 확인**한다.
  4. `AC-OVERLAP-015` ①②④: `bound_proves_clear`가 실린 리포트의 사용자 문자열에 **관측 범위 한정 표현**이 있고, 그것이 **상계가 어느 모드 집합에서 왔는지**를 가리키며, 문자열이 비어 있지 않고 한국어를 포함한다.
  5. `AC-OVERLAP-015` ③ **대조**: 정확폭으로 판정된 슬롯에는 그 한정이 붙지 **않는다** — 정확폭은 그 슬롯에 대해 무한정이다.
  6. `uv run pytest server/tests/ -q`의 계수가 baseline **이상**.
- **건드리는 기존 테스트와 갱신 정당화**

  **갱신 0건 — 추가만 한다.** `server/tests/test_prechk_report.py:103-114`(설계된 섹션 존재)와 `:273-278`(라벨표 순회)이 무변경 통과한다.

  이 마일스톤이 막는 결함 계열은 명확하다 — **`REQ-OVERLAP-017`이 *"요약이 사용자가 실제로 읽는 유일한 문자열"*이라고 적은 이유는 페이로드에만 넣고 요약에 넣지 않으면 사용자에게 보이지 않기 때문이다.** 그리고 `AC-OVERLAP-015`가 요구하는 한정은 선행 SPEC이 *"후보 12건 전건 부정"*을 무한정으로 적어 감사 지적을 받은 것과 같은 계열의 예방이다(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:646` `[문서]`).

### §B.6 M6 — 툴 배선

**목표.** 순회를 툴 표면에 잇는다. 경로는 `rig_paths` 경유로 수령하고(D-2), 섹션 가드는 **별도 상수를 신설해 `create_macro` 분기 밖에서** 검사하고(D-3), 예산 상한을 스레딩한다. 그리고 tools.py를 고치므로 **선례 트립와이어를 같은 커밋에서 갱신한다.**

- **`cycle_type`**: **`tdd`**.
- **산출 파일**
  - 구현(갱신): `server/orchestrator/tools.py`.
  - 테스트(갱신): `server/tests/test_prechk_tool.py`.
  - 테스트(**트립와이어 값 갱신**): `server/tests/test_songcue_bundle.py:64`의 `_TOOLS_EXPECTED_HUNK_OLD_STARTS`.
  - 신규 파일: **0건.**
- **배정 AC**: `AC-OVERLAP-018`.
- **진입 조건 (기계 판정)**
  1. M5의 DoD 6항 전건 충족.
  2. baseline 직접 실측.
  3. `git diff --unified=0 38a6e7e2157a4862721fcd868056e0dbbb09c4c0..HEAD -- server/orchestrator/tools.py | grep '^@@'`의 hunk old-start 목록이 `server/tests/test_songcue_bundle.py:64`의 현재 값과 일치함을 확인한다 — 갱신 전 기준선을 잡는다.
- **종료 조건 (DoD · 전건 기계 판정)**
  1. `AC-OVERLAP-018` ①②③④⑤ 전건: 신규 REST 라우트·웹소켓 메시지 타입 0건(+ 방문 파일 ≥ 1) · `execution_port` 직접 접근 0건 · `server.bridge` 직접 import 0건이며 아키텍처 테스트 전건 통과(`server/tests/test_architecture.py:26-31` · `:33-39` · `:48-61`) · `server/tools/` 운영 유틸 예외 목록이 **바이트 동일**(`server/tests/test_architecture.py:33-39`) · 콘솔에 발화하는 커맨드 **0건**.
  2. **D-2 기계 확인**: `server/prechk/footprint.py`에 `"Patch/FixtureTypes"` 리터럴이 **0건**이고, 핸들러가 `rig_paths["fixture_types"]`를 넘긴다. `Patch/FixtureTypes`는 이미 `server/orchestrator/tools.py:117`에 기본값으로 있으므로 **신규 경로 상수 0건**이며, 오버라이드 이음새(`server/orchestrator/tools.py:508` · `:534`)가 이 축에도 적용된다.
  3. **D-3 기계 확인**: `server/orchestrator/tools.py:157`의 `PRECHK_RIG_SECTIONS = ("groups", "macros")`가 **바이트 동일**하다. 신설 튜플(이름은 `design.md` 소유)이 `create_macro` 값과 **무관하게 항상** 검사되고, 누락 시 메시지가 **어느 섹션이 빠졌는지 이름으로 말하며** 풀 판독 실패를 암시하지 않는다.
  4. `server/tests/test_prechk_tool.py:895-905` · `:907`이 **무변경 통과**한다 — 누락 섹션 **집합**을 메시지로 단정하는 두 테스트가 2섹션을 유지한다. `PRECHK_RIG_SECTIONS`에 `"fixture_types"`를 추가하면 이 둘이 깨지므로 D-3이 신설을 택했다.
  5. `server/tests/test_tools.py:511-522`의 **정확 10키** 단정이 무변경 통과한다 — 신규 경로 키 0건의 기계 확인. (11번째 키를 요구하는 것은 꼬리 초과 축뿐이며 `spec.md` §D가 그것을 범위 밖으로 두었다.)
  6. **순회 예외 포착의 기계 판정**: `server/tests/test_prechk_tool.py`의 `_dispatch` 호출 **41지점**이 전건 통과한다. 그 파일의 `RigPort`(`server/tests/test_prechk_tool.py:43-60`)는 픽스처 루트·`DataPool/Groups`·`DataPool/Macros` 3경로 외 전부 `RuntimeError`를 던지고 `_registry()`가 `rig_paths`를 넘기지 않아 기본값을 쓰므로 `Patch/FixtureTypes`가 대상이 된다 — **순회가 예외를 포착하지 않으면 41개가 전량 깨진다**(`research.md` §6.1) `[코드]`.
  7. **트립와이어 갱신**: `git diff --unified=0 38a6e7e2157a4862721fcd868056e0dbbb09c4c0..HEAD -- server/orchestrator/tools.py`의 hunk old-start 목록이 `_TOOLS_EXPECTED_HUNK_OLD_STARTS`와 일치하고, `server/tests/test_songcue_bundle.py:65`의 `_TOOLS_PROTECTED_OLD_RANGES = ((234, 238), (524, 569))`가 **바이트 동일**하며 **보호구역 교차 단정이 계속 성립**한다(`server/tests/test_songcue_bundle.py:233` · `:237`).
  8. `uv run pytest server/tests/ -q`의 계수가 baseline **이상**.
- **건드리는 기존 테스트와 갱신 정당화**

  | 대상 | 갱신 성격 | 왜 정당한가 |
  |---|---|---|
  | `server/tests/test_songcue_bundle.py:64` | **트립와이어 값 갱신 = 집행** | 주석이 스스로 *"tools.py를 정당하게 고치는 후속 SPEC은 이것을 의도적으로 갱신해야 하며 그것이 요점이다"*라고 선언한다(`server/tests/test_songcue_bundle.py:56-63`). PRECHK가 이미 한 번 갱신했다. **값만 늘어나고 보호구역 상수 `:65`는 바이트 동일해야 한다** |
  | `server/tests/test_prechk_tool.py` | **추가만** | `:895-905`·`:907`은 무변경 통과가 조건이다(DoD 4) |

- **갱신이 M6 커밋에 들어가야 하는 이유 — 기계적이다**

  `server/tests/test_songcue_bundle.py:447`이 `git diff --unified=0 <_RUN_PHASE_BASE>..HEAD -- server/orchestrator/tools.py`를 실행한다 `[코드]`. **`BASE..HEAD`는 커밋 대 커밋이며 워킹트리를 보지 않는다.** 따라서 tools.py 변경이 커밋되는 순간 hunk 목록이 바뀌고, 트립와이어가 같은 커밋에 갱신되지 않으면 **M6 커밋 직후부터 M7 커밋 전까지 스위트가 빨간 구간**이 된다. `CONTRACT.md` §5가 M7에 배정한 것은 **`AC-OVERLAP-019` ⑦의 판정**(갱신됐고 교차 단정이 계속 성립함)이며, 값 편집은 그것을 성립시키기 위해 M6가 수행한다. M7이 그 결과를 판정한다.

### §B.7 M7 — PRESERVE 상시 테스트 · 게이트

**목표.** 선행 SPEC의 **이월 항목을 집행한다.** `AC-PRECHK-015`의 PRESERVE 게이트가 1회성 수동 절차였고, **CI가 0건인 저장소에서 PRESERVE를 지키는 유일한 수단이 상시 테스트**다(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:999` `[문서]`). 남아 있던 것은 BASE 상대 좌표였고 조사가 전부 실측 대조했다(`research.md` §9).

- **`cycle_type`**: **`tdd`**.
- **산출 파일**
  - 테스트(신규): **`server/tests/test_overlap_preserve.py`** — PRESERVE 상시 게이트 전량. **선례 파일을 확장하지 않는다**(`AC-OVERLAP-019` ⑥).
  - 구현: **0건.**
  - 갱신: **0건** — 트립와이어 값은 M6가 이미 갱신했고 M7은 그것을 **판정**한다.
- **배정 AC**: `AC-OVERLAP-019`.
- **진입 조건 (기계 판정)**
  1. M6의 DoD 8항 전건 충족. 특히 7항 — tools.py 커밋이 이미 있어야 hunk 봉쇄가 최종값을 갖는다.
  2. baseline 직접 실측.
- **종료 조건 (DoD · 전건 기계 판정)**
  1. **`git diff --stat 95687a0e0eba90b325daf76efbd0ac197e69e2fc..HEAD -- <PRESERVE 10경로>`가 빈 출력**이다(`AC-OVERLAP-019` ①). **`<PRECHK_BASE>`는 `95687a0e0eba90b325daf76efbd0ac197e69e2fc`이며 본 SPEC의 BASE가 아니다** — 근거는 §C.2다.
  2. **범위 고정 단정**: ①이 만드는 argv의 범위 인자가 정확히 `95687a0e0eba90b325daf76efbd0ac197e69e2fc..HEAD` 형태다(`AC-OVERLAP-019` ②). 인자 없는 `git diff`로 "단순화"하는 것을 금지하는 기계 판정이며 선례가 `server/tests/test_songcue_bundle.py:211`에 있다.
  3. **비공허성 — 선례보다 강하게**(`AC-OVERLAP-019` ③): 경로 목록이 비어 있지 않고 **원소 수가 10**이며 **각 경로가 실재한다.** 디렉터리 원소는 `is_dir()`로, 파일 원소는 `is_file()`로 판정하고 **그 분류를 목록 자체에서 기계로 도출한다** — 하드코딩된 분류 표에 의존하지 않으므로 목록이 개정돼도 견딘다. 존재하지 않는 경로는 `--stat`에 조용히 0행을 기여하므로 오타 한 글자로 게이트가 영구 통과한다.
  4. **tools.py hunk 위치 봉쇄**(`AC-OVERLAP-019` ④): BASE 상대 범위 `(247, 251)`과 `(537, 582)`에 hunk가 교차하지 않는다. **범위는 `95687a0e…` 상대이며 HEAD 좌표로 옮겨 적지 않는다**(§A.1).
  5. **`server/safety/**` 파일집합 봉쇄와 삭제 행 봉쇄**(`AC-OVERLAP-019` ⑤): 변경 파일이 **정확히 2개**이고, 한쪽은 삭제 **0행**, 다른 쪽은 삭제 **≤ 1행**이며 **그 1행이 독스트링임**을 함께 단정한다. 두 번째 조건이 없으면 의미 있는 삭제가 허용치 아래로 숨는다. 착수 시점 값은 §A.5의 표다 `[코드]`.
  6. **신규 파일 확인**(`AC-OVERLAP-019` ⑥): `git diff --numstat 85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a..HEAD -- server/tests/test_songcue_bundle.py`의 변경이 **트립와이어 값 1행에 한정**된다. 선례 파일에 신규 게이트 상수가 들어가지 않았음의 기계 확인.
  7. **트립와이어 판정**(`AC-OVERLAP-019` ⑦): M6의 갱신이 성립하고 보호구역 교차 단정이 계속 성립한다.
  8. **PRECHK progress.md 무변경**(`AC-OVERLAP-019` ⑧): `git diff --stat 85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a..HEAD -- .moai/specs/SPEC-COPILOT-PRECHK-001/`가 **빈 출력**이고, `DESCOPE: ASSUMPTION-27` 접두 행이 여전히 **정확히 1건**이다(`server/tests/test_prechk_patch.py:310-317`이 상시 판정한다). **이 한 항목만 본 SPEC의 BASE를 쓴다** — PRECHK BASE로 돌리면 PRECHK SPEC 6문서의 최초 작성 전량(6파일 · 추가 2887행)이 diff에 실려 판정이 성립하지 않는다 `[코드]`. 반면 `85a4b23…`은 PRECHK의 §E.9를 기록한 커밋이므로 그 시점 이후의 변경이 정확히 *"본 SPEC이 손댄 것"*이다.
  9. **`ruff check`와 `ruff format --check`가 본 SPEC이 손댄 전 파일에서 통과**한다(`AC-OVERLAP-019` ⑨).
  10. `uv run pytest server/tests/ -q`의 계수가 baseline **이상**.
- **엄중한 경고 2건 — 위반하면 게이트가 즉시 실패하거나 엉뚱한 곳을 지킨다**

  > **경고 1 — `tools.py`에 "삭제 0행" 규칙을 쓰지 마라.**
  >
  > `git diff --numstat 95687a0e0eba90b325daf76efbd0ac197e69e2fc..HEAD -- server/orchestrator/tools.py`의 착수 시점 값은 **추가 357 · 삭제 1 · hunk 9개**다 `[코드]`(본 계획이 직접 실행해 확인했고 `research.md` §9.4의 표와 일치한다). 삭제 1행의 원문은 `-from server.orchestrator.ports import BundleGate, CommandExecutionPort, StateQueryPort`이며 import 1행이 12행 블록으로 대체된 것이다. **선행 SPEC의 §E.7 ⑤가 적은 *"순수 추가 = 삭제 0"* 기계 규칙을 tools.py에 적용하면 게이트가 착수 직후 즉시 실패한다.** 반드시 **hunk 위치 봉쇄**를 쓴다. 같은 파일의 `server/safety/console.py`(삭제 0)와 `server/safety/gate.py`(삭제 1, 독스트링)에는 삭제 행 봉쇄가 적용되며 그 둘은 DoD 5가 다룬다.

  > **경고 2 — 선례 파일(`server/tests/test_songcue_bundle.py`)을 확장하지 마라.**
  >
  > 그 파일의 상수는 **SONGCUE BASE `38a6e7e…` 상대**이고 신규 게이트의 상수는 **PRECHK BASE `95687a0e…` 상대**다. 한 모듈에 두 BASE를 섞으면 게이트가 엉뚱한 곳을 지킨다. 수치 증명은 `research.md` §9.3이다 — 두 BASE의 `tools.py` 총 행수가 1234 대 1564이고 보호구역이 각각 **+13** 어긋난다. 선례 값 `(234, 238)`을 PRECHK BASE에서 쓰면 **dedupe 예외 근거를 설명하는 주석 한복판**을 지키고, `(524, 569)`는 실행 루프보다 **13행 앞**에서 시작해 루프 끝 13행 전에 닫혀 **`failed = True`(582)를 보호하지 못한다.** 신규 파일 `server/tests/test_overlap_preserve.py`가 PRECHK BASE 상수를 단독으로 소유한다.

### §B.8 M8 — 종단 통합

**목표.** 툴 표면에서 `overlap_basis` **4값 전량**이 산출되는 것을 확인하고, **신규 테스트가 수정 전 코드에서 실패함을 역방향으로 확인**하고, 스위트를 닫는다.

- **`cycle_type`**: **`tdd`**.
- **산출 파일**
  - 테스트(갱신): `server/tests/test_prechk_tool.py` — 4값 종단 산출 · 조회 계수 상한 · 감사 로그 대조.
  - 테스트(갱신): `server/tests/test_prechk_footprint.py` — 역방향 검증 대상 목록의 소유 파일.
  - 구현: **0건.**
  - 기록: `progress.md`의 M8 절 — 역방향 검증 결과(`AC-OVERLAP-021` ⑥).
- **배정 AC**: `AC-OVERLAP-021`.
- **라이브가 필요 없는 이유 — 이 마일스톤에서 특히 명시한다**
  1. `AC-OVERLAP-021`이 *"라이브 세션을 요구하지 않는다 — 인메모리 리그와 툴 디스패치로 닫힌다"*를 명문화했다.
  2. `bound_inconclusive`는 **합성 인메모리 리그만이** 도달할 수 있다 — 현재 쇼파일에서 그 분기를 발동시키는 입력이 0건이다(`research.md` §3.3). 라이브에 붙어도 관측되지 않는다.
  3. `bound_proves_clear`는 현재 쇼파일에서 **이미 참**이다 — 간격 42·50 대 상계 31이므로 17쌍 전부가 통과한다(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:987` · `:1097` `[문서]` 인용). 라이브가 새 정보를 주지 않는다.
  4. 합성 리그를 라이브 미러로 묶지 않는 것은 이미 확립된 선례다 — `range_overlap_go()`의 폭이 *"INJECTED, never derived"*이고(`server/tests/test_prechk_inventory.py:369-372`) 그 결정이 `.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:419`에 있다 `[코드]`·`[문서]`.
- **진입 조건 (기계 판정)**
  1. M7의 DoD 10항 전건 충족.
  2. baseline 직접 실측.
  3. `git status --porcelain`이 **빈 출력** — 역방향 절차가 워킹트리를 건드리므로 시작 상태가 깨끗해야 한다.
- **종료 조건 (DoD · 전건 기계 판정)**
  1. `AC-OVERLAP-021` ①: 툴을 통해 4개 `overlap_basis` 값 **각각**이 산출되는 리그가 존재하고, 각 경우의 페이로드가 스키마 정본과 일치한다.
  2. `AC-OVERLAP-021` ②: 착수 시점의 `precheck_patch` 테스트가 **전건 통과** — `server/tests/test_prechk_tool.py`의 `_dispatch` **41 호출 지점**을 순회 추가가 깨지 않는다. 순회가 예외를 포착하지 않으면 전량이 깨지므로 이것이 포착의 기계 판정이다(§B.6 DoD 6과 같은 판정을 종단에서 재확인한다).
  3. `AC-OVERLAP-021` ③: 조회 계수가 예산 상한을 **넘지 않는다.** 착수 시점에 조회 계수를 고정하는 단정이 **0건**이었으므로(`research.md` §6.1 — `state_calls`에 대한 등호 단정이 저장소 전체에 0건) 본 항이 그것을 신설한다.
  4. `AC-OVERLAP-021` ④: 감사 로그에 순회 조회가 전건 기록된다 — **조회 1건 = 감사 1건**.
  5. `AC-OVERLAP-021` ⑤: 스위트 전체가 통과하고 계수가 착수 baseline 이상이다.
  6. `AC-OVERLAP-021` ⑥: **아래 역방향 절차를 실행하고 결과를 `progress.md`에 기록한다.** 통과하는 테스트는 **회귀 테스트가 아니라고 코드에 명시**한다 — 비공허성 보증 또는 불변식 가드로 라벨한다. 규율 16의 집행이다(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:1247` `[문서]`).
- **역방향 검증 — 명령 순서를 그대로 지킨다**

  ```sh
  # 0) 시작 상태가 깨끗함을 확인한다
  git status --porcelain            # → 빈 출력이어야 한다

  # 1) 본 SPEC이 만든 신규·변경 테스트 목록을 고정한다
  git diff --name-only 85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a..HEAD -- server/tests/

  # 2) 신규 모듈을 워킹트리 밖으로 옮긴다 (BASE에 없으므로 checkout이 지우지 않는다)
  mkdir -p /tmp/overlap-reverse
  mv server/prechk/footprint.py /tmp/overlap-reverse/

  # 3) 구현만 BASE로 되돌린다 — 테스트는 HEAD를 유지한다
  git checkout 85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a -- \
      server/prechk/ server/orchestrator/tools.py

  # 4) 역방향 실행 — 본 SPEC의 신규 테스트가 FAIL해야 한다
  uv run pytest server/tests/test_prechk_footprint.py server/tests/test_prechk_patch.py \
                server/tests/test_prechk_report.py server/tests/test_prechk_tool.py \
                server/tests/test_prechk_verdicts.py -q

  # 5) 복원 — 두 명령을 모두 실행한다
  git checkout HEAD -- server/prechk/ server/orchestrator/tools.py
  mv /tmp/overlap-reverse/footprint.py server/prechk/footprint.py
  git status --porcelain            # → 빈 출력이어야 한다

  # 6) 정방향 전체 스위트
  uv run pytest server/tests/ -q
  ```

  **4단계 출력의 판정 규율 — 두 등급을 섞지 않는다.**

  | 등급 | 무엇을 증명하나 | 어떻게 기록하나 |
  |---|---|---|
  | **A — 모듈 부재** | `server/tests/test_prechk_footprint.py`가 **collection error**를 낸다. 신규 모듈에 의존하는 테스트가 수정 전 코드에서 성립하지 않음을 보인다. **약한 증거이며 그 사실을 명시한다** — 무엇을 막는지는 말해 주지 않는다 | `progress.md` M8 절에 collection error 원문 |
  | **B — 뮤테이션 killed** | 각 신규 테스트가 **무엇을** 막는지 증명한다. 목록은 고정이다: `AC-OVERLAP-003` ⑥(부분집합 상계 거짓 양성) · `AC-OVERLAP-008` ②(간격 == 상계 off-by-one) · `AC-OVERLAP-009` ③(유니버스 키잉 붕괴) · `AC-OVERLAP-014` ⑥⑦(라벨표 항목 제거 시 import 실패) | 각 마일스톤 절에 killed/survived. **survived는 그 마일스톤 미완료로 본다** |
  | **C — 수정 전에도 통과** | 회귀 테스트가 **아니다.** 비공허성 보증 또는 불변식 가드로 코드에 명시 라벨한다 | `AC-OVERLAP-021` ⑥의 요구 |

  **A 등급만으로 규율 16을 충족했다고 적지 않는다.** 선행 SPEC의 P1 4건은 2721개 스위트가 전부 통과하는 상태에서 살아 있었고, 그것을 잡은 것은 존재 확인이 아니라 **뮤테이션**이었다.
- **건드리는 기존 테스트와 갱신 정당화**

  **갱신 0건 — 추가만 한다.** M8은 새 단정을 얹고 기존 단정을 고치지 않는다. 3항(조회 계수 상한)은 착수 시점에 대응 단정이 0건이었으므로 **신설**이며, 그것이 유일한 신규 계약이 아니라 `AC-OVERLAP-021` ③이 이미 요구한 것이다.

### §B.9 AC 배정 표 — `CONTRACT.md` §5와 전건 일치

| # | 이름 | `cycle_type` | 배정 AC | 건수 |
|---|---|---|---|---|
| **M0** | 전제 판정 — `state`만으로 도달하는가 | **none** | `AC-OVERLAP-020` | 1 |
| **M1** | 어휘 확장 | tdd | `AC-OVERLAP-014` | 1 |
| **M2** | 순회 모듈 | tdd | `AC-OVERLAP-001` · `AC-OVERLAP-002` · `AC-OVERLAP-003` · `AC-OVERLAP-004` · `AC-OVERLAP-005` · `AC-OVERLAP-006` | 6 |
| **M3** | 상계 판정 | tdd | `AC-OVERLAP-008` · `AC-OVERLAP-009` · `AC-OVERLAP-010` · `AC-OVERLAP-011` · `AC-OVERLAP-012` | 5 |
| **M4** | 정확폭 우선 · 근거 배선 | tdd | `AC-OVERLAP-007` · `AC-OVERLAP-013` · `AC-OVERLAP-016` | 3 |
| **M5** | 리포트 | tdd | `AC-OVERLAP-015` · `AC-OVERLAP-017` | 2 |
| **M6** | 툴 배선 | tdd | `AC-OVERLAP-018` | 1 |
| **M7** | PRESERVE 상시 테스트 · 게이트 | tdd | `AC-OVERLAP-019` | 1 |
| **M8** | 종단 통합 | tdd | `AC-OVERLAP-021` | 1 |
| | | | **합** | **21** |

### §B.10 배정 합 21 · 중복 0 · 누락 0 — 별도 표로 재확인

역방향으로 센다. AC 21건 각각에 배정 마일스톤이 **정확히 하나** 있어야 한다.

| 인수 조건 | 배정 마일스톤 | 배정 수 |
|---|---|---|
| `AC-OVERLAP-001` | M2 | 1 |
| `AC-OVERLAP-002` | M2 | 1 |
| `AC-OVERLAP-003` | M2 | 1 |
| `AC-OVERLAP-004` | M2 | 1 |
| `AC-OVERLAP-005` | M2 | 1 |
| `AC-OVERLAP-006` | M2 | 1 |
| `AC-OVERLAP-007` | M4 | 1 |
| `AC-OVERLAP-008` | M3 | 1 |
| `AC-OVERLAP-009` | M3 | 1 |
| `AC-OVERLAP-010` | M3 | 1 |
| `AC-OVERLAP-011` | M3 | 1 |
| `AC-OVERLAP-012` | M3 | 1 |
| `AC-OVERLAP-013` | M4 | 1 |
| `AC-OVERLAP-014` | M1 | 1 |
| `AC-OVERLAP-015` | M5 | 1 |
| `AC-OVERLAP-016` | M4 | 1 |
| `AC-OVERLAP-017` | M5 | 1 |
| `AC-OVERLAP-018` | M6 | 1 |
| `AC-OVERLAP-019` | M7 | 1 |
| `AC-OVERLAP-020` | M0 | 1 |
| `AC-OVERLAP-021` | M8 | 1 |

**행 수 21 = AC 총수 21 → 누락 0.** **배정 수 열의 값이 전부 1 → 중복 0.** **배정 수 합 = 21 = §B.9의 건수 합.** 세 계수가 서로를 검산한다.

---

## §C. 게이트와 검증 전략

### §C.1 마일스톤별 기계 게이트 — 실행 가능한 명령

모든 게이트는 종료 코드 또는 출력 동일성으로 판정한다. 주관적 판단이 들어가는 항목은 없다.

| 마일스톤 | 게이트 명령 | 통과 조건 |
|---|---|---|
| **전 마일스톤 (진입)** | `uv run pytest server/tests/ -q` | 실패 0건. 출력 계수를 그 마일스톤의 baseline으로 기록한다(§A.2) |
| **전 마일스톤 (종료)** | `uv run pytest server/tests/ -q` | 실패 0건 · 계수가 자기 baseline 이상 |
| **M0** | `git status --porcelain -- server/ console/` · `git status --porcelain` | 둘 다 빈 출력 |
| **M0** | `git merge-base --is-ancestor 85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a HEAD` | 종료 코드 0 |
| **M1** | `python -c "import server.prechk.report"` | 종료 코드 0 |
| **M1** | `uv run pytest server/tests/test_prechk_verdicts.py server/tests/test_prechk_report.py -q` | 실패 0건 |
| **M1** | `git diff 85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a..HEAD -- server/prechk/verdicts.py` | `CLOSED_VOCABULARIES` 기존 5줄이 diff에 나타나지 않는다(append-last) |
| **M2** | `python -c "import server.prechk.footprint"` | 종료 코드 0 |
| **M2** | `git diff --stat 85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a..HEAD -- server/safety/` | **빈 출력** |
| **M2** | `git diff --stat 85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a..HEAD -- server/prechk/` | **비어 있지 않다**(②의 비공허성 대조) |
| **M2·M3·M4·M5** | AST 스캔 테스트(import 경계 · 호출 식별자 · 상수 집합 · 제어 흐름 · 라벨 출처) | 각 스캔의 **방문 노드 수 ≥ 1**을 함께 단정 |
| **M6** | `uv run pytest server/tests/test_prechk_tool.py server/tests/test_tools.py server/tests/test_architecture.py -q` | 실패 0건 |
| **M6** | `git diff --unified=0 38a6e7e2157a4862721fcd868056e0dbbb09c4c0..HEAD -- server/orchestrator/tools.py \| grep '^@@'` | hunk old-start 목록이 `server/tests/test_songcue_bundle.py:64`와 일치 |
| **M7** | `git diff --stat 95687a0e0eba90b325daf76efbd0ac197e69e2fc..HEAD -- <PRESERVE 10경로>` | **빈 출력** |
| **M7** | `git diff --numstat 95687a0e0eba90b325daf76efbd0ac197e69e2fc..HEAD -- server/safety/` | 파일 **정확 2개** · console.py 삭제 0 · gate.py 삭제 ≤ 1(독스트링) |
| **M7** | `git diff --unified=0 95687a0e0eba90b325daf76efbd0ac197e69e2fc..HEAD -- server/orchestrator/tools.py` | hunk가 `(247, 251)` · `(537, 582)`와 교차 0건 |
| **M7** | `git diff --numstat 85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a..HEAD -- server/tests/test_songcue_bundle.py` | 변경이 트립와이어 값 1행에 한정 |
| **M7** | `git diff --stat 85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a..HEAD -- .moai/specs/SPEC-COPILOT-PRECHK-001/` | **빈 출력** — 유일하게 본 SPEC BASE를 쓰는 M7 게이트(§B.7 DoD 8) |
| **M7** | `grep -c '^DESCOPE: ASSUMPTION-27 ' .moai/specs/SPEC-COPILOT-PRECHK-001/progress.md` | 출력이 정확히 `1` |
| **M7** | `ruff check <손댄 파일>` · `ruff format --check <손댄 파일>` | 둘 다 종료 코드 0 |
| **M8** | §B.8의 역방향 6단 절차 | 4단에서 신규 테스트가 FAIL · 5단 후 `git status --porcelain` 빈 출력 · 6단 전건 통과 |

**게이트가 결함을 비껴가는 형태를 의심한다**(`CONTRACT.md` §6의 4번). 위 목록에서 특히 셋을 금지한다: 대조 전에 페이로드를 지우는 정규화 · 한 페이즈만 보는 필터 · 명시적 `continue`. 그리고 **0건 판정에는 비공허성 단정을 반드시 동반한다** — 스캔이 아무것도 방문하지 않아 0건이 나오는 경우를 배제해야 한다.

### §C.2 PRESERVE 게이트는 PRECHK BASE로 돌린다 — 본 SPEC의 BASE가 아니다

**`AC-OVERLAP-019` ①이 쓰는 `<PRECHK_BASE>`는 `95687a0e0eba90b325daf76efbd0ac197e69e2fc`다.** 본 SPEC의 BASE `85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a`가 아니다.

**이유는 하나이고 실측으로 증명되어 있다.** 새 BASE로 돌리면 **착수 직후 항상 0행**이다 — 커밋 시점 이후의 변경만 보이므로 그 이전에 커밋된 위반은 전부 비가시가 된다. 게이트가 통째로 무력해진다. 선행 SPEC이 같은 무력화를 뮤테이션으로 나란히 측정했다: `console/lua/copilot_responder.lua`에 위반을 **커밋해 둔 상태에서** 인자 없는 `git diff --stat -- <목록>`은 **0행**을 냈고 `<BASE>..HEAD`는 그 위반을 적발했다(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:558` `[문서]`).

**두 BASE를 섞지 않게 하는 세 장치를 함께 둔다.**

1. **범위 고정 단정**(`AC-OVERLAP-019` ②) — argv의 범위 인자가 정확히 `95687a0e0eba90b325daf76efbd0ac197e69e2fc..HEAD` 형태여야 한다. 인자 없는 diff로의 "단순화"를 기계로 금지한다.
2. **파일 분리**(`AC-OVERLAP-019` ⑥) — PRECHK BASE 상수는 신규 파일 `server/tests/test_overlap_preserve.py`가 단독 소유한다. SONGCUE BASE 상수는 `server/tests/test_songcue_bundle.py:45`에 남는다. 한 모듈에 두 BASE가 없다.
3. **본 SPEC BASE의 용도 한정** — `85a4b23…`은 네 곳에만 쓴다: `AC-OVERLAP-002` ③(safety diff) · M1의 append-last 확인 · M8의 역방향 checkout · `AC-OVERLAP-019` ⑧(PRECHK SPEC 디렉터리 무변경, §B.7 DoD 8). **PRESERVE 10경로 게이트와 hunk 봉쇄와 safety 파일집합 봉쇄에는 쓰지 않는다.** ⑧이 예외인 이유는 §B.7 DoD 8에 적었다 — 그 항목이 묻는 것은 *"선행 SPEC이 잠근 것"*이 아니라 *"본 SPEC이 남의 기록을 건드렸는가"*이므로 착수 시점이 기준이다.

**그리고 두 BASE의 역할이 왜 다른지가 구조적이다.** PRESERVE는 *"선행 SPEC이 잠근 것을 지금도 안 건드렸는가"*를 묻고, 본 SPEC BASE의 safety diff는 *"이번 SPEC이 새로 건드렸는가"*를 묻는다. 첫 질문은 잠금 시점을 기준으로만 답이 나오고 둘째 질문은 착수 시점을 기준으로만 답이 나온다. **같은 SHA로 둘 다 물을 수 없다.**

### §C.3 규율 16 집행 절차 — 새 테스트의 역방향 검증과 기록 위치

`CONTRACT.md` §6의 3번이 규율 16이다: **"스위트가 통과한다"는 "결함이 없다"가 아니다.** 선행 SPEC에서 P1 4건이 2721개 전부 통과하는 상태에서 살아 있었다(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:1247` `[문서]`). 집행 절차는 셋이다.

**① 마일스톤 내부 — 뮤테이션.** 각 마일스톤이 자기 뮤테이션 목록을 소진한다. 본 계획이 고정한 목록:

| 마일스톤 | 뮤테이션 | 죽어야 하는 것 |
|---|---|---|
| M1 | `OVERLAP_BASIS_LABELS`에서 항목 1개 제거 | `import server.prechk.report`가 예외(`AC-OVERLAP-014` ⑥⑦) |
| M1 | 레지스트리에서 신규 축 제거 | `server/tests/test_prechk_verdicts.py`의 집합·키·순서 3단정 중 ≥ 1건 |
| M2 | 완전성 판정을 `max` **뒤로** 옮긴다 | `AC-OVERLAP-003` ⑤(AST 제어 흐름) |
| M2 | 2단 예산 3 · 폭 `{29,29,29,31}` · 간격 30 리그에서 부분집합 상계를 채택 | `AC-OVERLAP-003` ⑥(거짓 양성 재현) |
| M2 | 1·2단과 3단의 절단 술어를 하나로 뭉갠다 | `AC-OVERLAP-004` ④ |
| M3 | 판정 술어를 `간격 ≤ 상계 → 미확정`으로 바꾼다 | `AC-OVERLAP-008` ②(간격 == 상계 경계) |
| M3 | 유니버스 키잉을 제거해 단일 공간으로 붕괴 | `AC-OVERLAP-009` ③④ — **정확폭 축과 상계 축 양쪽** |
| M3 | 미확정 쌍을 `range_overlaps`에 넣는다 | `AC-OVERLAP-011` ①②③ |
| M4 | 근거 필드를 만들고 페이로드 키를 만들지 않는다 | `AC-OVERLAP-016` ③ |
| M4 | 3슬롯 미비교 상태에서 리그 전역에 `bound_proves_clear` | D-4 정직성 판정 1(§B.4 DoD 6) |
| M5 | 라벨을 판정 계층에서 만든다 | `AC-OVERLAP-017` ② |
| M6 | `PRECHK_RIG_SECTIONS`에 `"fixture_types"`를 추가한다 | `server/tests/test_prechk_tool.py:895-905`·`:907` |
| M7 | PRESERVE 10경로 중 하나에 공백 1줄을 넣은 임시 커밋 | `AC-OVERLAP-019` ① — 즉시 되돌린 뒤 다시 빈 출력이어야 한다(게이트 비공허성 증명) |
| M7 | 범위 인자를 인자 없는 `git diff`로 바꾼다 | `AC-OVERLAP-019` ② |

**② 종단 — 구현 되돌리기.** §B.8의 6단 절차. **A 등급(모듈 부재)은 약한 증거이며 그 사실을 함께 적는다.**

**③ 기록 위치 — `progress.md`, 두 곳.**

| 무엇 | 어디에 |
|---|---|
| 마일스톤별 뮤테이션 결과 | `progress.md`의 해당 마일스톤 절에 **killed / survived**로. **survived는 그 마일스톤 미완료로 본다** |
| 종단 역방향 결과 | `progress.md`의 M8 절에 4단 출력 원문 + A/B/C 등급 분류(`AC-OVERLAP-021` ⑥) |
| 수정 전에도 통과하는 테스트 | **코드에 명시 라벨** — 회귀 테스트가 아니라 비공허성 보증 또는 불변식 가드임을 도크스트링·주석에 적는다 |

### §C.4 미확정 분기에 라이브 증거를 요구하지 않는다 — 감사 지적에 대한 선제 반박

**규율: `bound_inconclusive` 분기의 인수 조건은 합성 인메모리 리그로 충족하며, 라이브 증거를 요구하지 않는다.**

**원리적으로 불가능하기 때문이다.** 근거를 산술로 닫는다.

| 항목 | 값 | 출처 |
|---|---|---|
| 상계 `W` | `max{29, 29, 29, 31}` = **31** | `.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:403` `[문서]` 인용 |
| 유니버스 1 인접 간격 | `[100, 42, 42, 42, 42, 42, 42, 42, 42]` (9쌍) → 최소 **42** | `research.md` §3.2가 `:308-326`의 주소표로 재계산 |
| 유니버스 2 인접 간격 | `[50] × 8` (8쌍) → 최소 **50** | 같음 |
| `간격 ≥ 31` (겹침 없음 증명) | **17쌍** | `research.md` §3.2 |
| `간격 < 31` (미확정) | **0쌍** | 같음 |

**현재 쇼파일에는 `bound_inconclusive`를 발동시키는 입력이 0건이다.** 콘솔에 붙어도 그 분기가 실행되지 않으므로 라이브 관측이 존재할 수 없다. 라이브 증거를 요구하는 인수 조건은 **충족 불가능**하며 `acceptance.md`가 머리말에서 그것을 쓰지 않는다고 명문화했다.

**감사가 이것을 지적으로 올릴 수 있다** — *"`GO` 분기만 실측됐고 미확정 분기는 관측 근거가 없다"*는 형태다. **그 지적은 부당하며 근거는 넷이다.**

1. **산술이 그 분기의 부재를 설명한다.** 위 표가 관측 부재의 원인을 준다 — 우연이 아니고 측정 누락도 아니다. 최소 간격 42가 상계 31보다 크다는 것이 곧 미확정 0쌍이다.
2. **42는 이 쇼파일의 산물이다.** 룰북의 `AddFixtures` 예제가 `addr = 101`에서 `addr = addr + 42`를 9회 돌린 결과가 실측 유니버스 1의 슬롯 2~10 주소와 **정확히 일치한다**(`server/rulebook/assets/v2.4.2/30_plugin_patterns.md:37-56` · `research.md` §5.6). 다른 쇼파일에서는 다른 값이 나오며, 그것이 `REQ-OVERLAP-001`이 폭도 간격도 상수로 두지 않게 한 이유다.
3. **합성 리그를 라이브 미러로 묶지 않는 것이 확립된 선례다.** `range_overlap_go()`의 폭이 주석으로 *"INJECTED, never derived"*라고 선언되어 있고(`server/tests/test_prechk_inventory.py:369-372` `[코드]`), 인메모리 픽스처를 현장 쇼파일에 묶으면 리그가 바뀔 때마다 테스트가 깨지고 결정성이 사라진다는 결정이 `.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:419`에 있다 `[문서]`.
4. **단위 접근 경로가 인수 조건으로 이미 요구되어 있다.** `AC-OVERLAP-005` ④가 *"순회 함수를 툴을 거치지 않고 직접 호출해 인메모리 리그로 상계를 얻는 테스트"*를 요구하며, 그 이유를 *"`bound_inconclusive` 분기가 합성 리그로만 도달 가능하므로 이 단위 접근이 필수"*라고 적었다.

**대신 무엇으로 그 분기를 지키는가.** 라이브 대체물이 아니라 **뮤테이션**이다 — §C.3 ①의 M2 두 항(완전성 판정 위치 · 부분집합 상계 거짓 양성)과 M3 두 항(경계 술어 · 미확정을 충돌로 안 냄)이 그 분기의 실질 커버다. `AC-OVERLAP-003` ⑥이 `research.md` §4.1의 시나리오를 코드로 옮긴 것이며 **수정 전 코드에서 반드시 실패해야 한다**고 못박은 것이 그 집행이다.

---

## §D. 위험과 완화

`CONTRACT.md` §6의 결함 계열 6건을 마일스톤에 매핑한다. **위험 1~3이 필수 포함 항목이며 심각도 순이다.**

### §D.1 위험 1 — 부분집합 상계가 거짓 양성을 낸다 (가장 심각)

| 축 | 내용 |
|---|---|
| **결함 계열** | `node.childCount`와 `len(children)`을 함께 보지 않으면 **열거가 짧고 상계도 상계가 아니다**(`CONTRACT.md` §6의 2번) |
| **구체 형태** | 2단(`DMXModes` 열거)에서 예산이 모드 3개 만에 소진되면 관측 부분집합이 `{29, 29, 29}`이고 계산된 "상계"가 **29**다(참값 31보다 **작다**). 간격 30인 쇼파일에서 `30 ≥ 29` → **`bound_proves_clear` 발화(거짓)**. 참 상계 31이면 `30 < 31` → `bound_inconclusive`가 옳다(`research.md` §4.1) |
| **왜 안 보이나** | **현재 쇼파일(간격 42)에서는 결론이 우연히 같아 이 결함이 보이지 않는다.** 스위트가 초록인 채로 살아 있을 수 있는 형태다 |
| **왜 선례 복사가 이 결함을 만드나** | `drill_into`의 예산 소진 처리는 `drilldown_capped` 플래그를 붙이고 **순회를 계속한다**(`server/orchestrator/tools.py:378-419`) `[코드]`. 거기서 소진은 *그 자식에 국소적인 정보 부재*이고 다른 자식의 판정을 바꾸지 않는다. **여기서는 표기와 판정이 서로 다른 대상에 붙어 표기가 남아도 판정이 이미 오염된다** |
| **소유 마일스톤** | **M2**(완전성 판정을 `max` 앞에 두는 제어 흐름) · **M3**(경계 술어) |
| **완화 — 기계 판정** | ① `AC-OVERLAP-003` ⑤ AST 제어 흐름 판정: `max` 노드가 완전성 판정 분기 **내부**에 있다. ② `AC-OVERLAP-003` ⑥ 거짓 양성 재현 테스트가 **수정 전 코드에서 실패**함을 §C.3의 절차로 확인한다. ③ `AC-OVERLAP-004` ③ 3단 술어가 `childCount > len(children)`를 **쓰지 않는다** — 두 술어를 뭉개면 1·2단이 잘못 통과한다 |
| **위험의 방향이 한 쪽뿐이다** | 구간 겹침이 `intervals`를 유니버스로 키잉하고 `_flush_cluster`가 `universe`를 스칼라로 받으므로(`server/prechk/patch.py:330` · `:355`) 유니버스를 넘는 점유는 **구조적으로 비가시**하다. 따라서 가능한 오류는 거짓 충돌이 아니라 **거짓 "겹침 없음 증명"** 뿐이다(`research.md` §5.3). **인수 조건은 이 방향만 막으면 되고, 그 사실이 완화를 좁고 확실하게 만든다** |

### §D.2 위험 2 — 새 순회가 예외를 포착하지 않으면 기존 툴 테스트 41개가 전량 깨진다

| 축 | 내용 |
|---|---|
| **결함 계열** | *"판독 실패"와 "그런 것이 없음"을 섞으면 결함이다*(`CONTRACT.md` §6의 1번, 선행 SPEC이 이 계열로 **7건**을 냈다) |
| **구체 형태** | `server/tests/test_prechk_tool.py:43-60`의 `RigPort`가 픽스처 루트·`DataPool/Groups`·`DataPool/Macros` **3경로 외 전부 `RuntimeError`**를 던지고, `_registry()`가 `rig_paths`를 넘기지 않아 기본값을 쓴다 — 즉 `Patch/FixtureTypes`가 대상이 된다. 그 파일의 `_dispatch` 호출은 **41지점**이다 `[코드]`(본 계획이 직접 센 값이며 `research.md` §6.1과 일치한다) |
| **소유 마일스톤** | **M2**(실패 분류) · **M6**(툴 배선) · **M8**(종단 재확인) |
| **완화 — 기계 판정** | ① §B.6 DoD 6과 §B.8 DoD 2: 41 호출 지점 전건 통과. ② `AC-OVERLAP-006` ①②: 두 실패가 서로 다른 사유 코드이고 **기존** `REASON_UNRESOLVED`/`REASON_UNREACHABLE`(`server/orchestrator/tools.py:196-197`)이며 새 어휘 신설 0건. ③ `AC-OVERLAP-006` ③: 프로덕션 게이트 포트가 두 경우를 **같은 예외 타입**으로 던지는 것을 재현하고도(`server/safety/console.py:387-388`) 구분이 성립한다 — 구분의 근거가 예외 타입이 **아니다**. ④ `AC-OVERLAP-007`: 순회 실패가 리포트의 나머지를 잃지 않는다 |
| **함정 하나 더** | **포착하면 0건 깨진다** — `state_calls`에 대한 등호 단정이 저장소 전체에 **0건**이므로 조회 1건 추가가 계수로는 아무 테스트도 깨뜨리지 않는다(`research.md` §6.1). **따라서 조회 비용을 지키는 단정은 새로 써야 한다** — `AC-OVERLAP-021` ③이 그것이고 M8이 신설한다 |

### §D.3 위험 3 — 어휘 라벨 누락은 스위트 실패가 아니라 import 실패로 툴셋 전제를 죽인다

| 축 | 내용 |
|---|---|
| **결함 계열** | *테스트 존재는 커버를 뜻하지 않는다* + 규율 16(`CONTRACT.md` §6의 3번) |
| **구체 형태** | `server/prechk/report.py`의 라벨표 누락은 **import 실패**다 — 가드가 발생하고, `server/orchestrator/tools.py`가 report를 경유하므로 **테스트 20+ 파일이 수집 실패**한다(`research.md` §7.3). 스위트가 "1건 실패"가 아니라 **수집 단계에서 죽는다** |
| **더 나쁜 쌍둥이** | **가드 튜플 누락은 무증상이다** — import 성공, 라벨 드리프트는 `server/tests/test_prechk_report.py:273-278`이 잡으므로 **실패 0건**이다(`research.md` §7.2). 잃는 것은 신규 축의 import 시점 결속뿐이고, 그것을 잃었다는 신호가 어디에도 없다 |
| **소유 마일스톤** | **M1** |
| **완화 — 순서로 없앤다** | **D-6이 가드 루프를 `CLOSED_VOCABULARIES` 순회로 바꿔 무증상 단계를 구조적으로 제거한다.** 그리고 §B.1의 절차 순서가 구조 변경을 **1단**에 둬서 3단과 4단 사이에 무증상 창이 열리지 않게 한다. `AC-OVERLAP-014` ⑦이 그 형태를 인정하고 판정한다 |
| **완화 — 기계 판정** | ① `AC-OVERLAP-014` ⑥⑦ 뮤테이션(라벨표 항목 제거 → import 예외). ② §B.1 DoD 1(`import server.prechk.report` 종료 코드 0). ③ `AC-OVERLAP-014` ⑤ 라벨표 이름이 `_LABELS`로 끝난다 — 미종료면 AST 하한 단정과 stray 단정 2건이 실패한다(`research.md` §7.3) |

### §D.4 나머지 결함 계열의 매핑

| 계열 (`CONTRACT.md` §6) | 본 SPEC에서의 형태 | 소유 마일스톤 | 완화 게이트 |
|---|---|---|---|
| 4. **게이트가 결함을 비껴가는 형태** | PRESERVE 게이트가 새 BASE로 돌면 항상 0행 · 선례 상수 복사로 엉뚱한 범위를 지킴 | **M7** | `AC-OVERLAP-019` ②(범위 고정) · ③(경로 실재 + 비공허성) · ⑥(신규 파일). §C.2 · §B.7의 경고 2건 |
| 5. **불완전한 집합에 판정을 단정하지 않는다**(선행 SPEC이 같은 항목에서 **두 번** 미끄러졌다) | `bound_proves_clear`에 *"관측된 모드 집합에 한정해"*가 빠지면 세 번째 미끄러짐이다 | **M5** | `AC-OVERLAP-015` ①②④(한정 표현 존재·상계 출처 지시·비공허성) · ③(정확폭 대조) |
| 6. **추측한 코드값·경로를 쓰지 않는다** | 폭 29·31, 간격 42·50, 유니버스 용량 `B`를 상수로 박는 것 | **M2**(상수 스캔) · **M3**(주소 범위 상한) | `AC-OVERLAP-001` ①(AST 상수 스캔 + 비공허성) · `AC-OVERLAP-012` ④(상한이 상수로 박혀 있지 않다). `ASSUMPTION-33`이 용량을 `[미확정]`으로 남기고 `B ≥ 467`이라는 약한 명제만 쓴다 |
| — **쓰기 0건이라 적용되지 않는 계열** | *효과는 재조회로만 확인한다* · *`Cmd` 접수 `OK`는 효과 증거가 아니다* | 해당 없음 | `AC-OVERLAP-018` ⑤가 *"콘솔에 발화하는 커맨드 0건"*을 기계로 고정해 **그 사실 자체를 범위 경계로 만든다** |

### §D.5 절차적 위험 1건 — 수렴 유혹

`CONTRACT.md` §2 D-8이 닫은 것을 위험으로 다시 적는다. 절단 계수 비교의 구현이 **3건** 있고(`server/prechk/inventory.py:389` · `server/prechk/macro.py:249-251` · `server/orchestrator/tools.py:1296-1302`) **`childCount` 부재·0 정책이 서로 다르다** — 예외 / 관용 / 예외+0거부다 `[코드]`. 본 SPEC은 **4번째 사본을 만들고 수렴을 시도하지 않는다.**

**수렴 시도가 위험인 이유**: 단순 통합은 `.moai/specs/SPEC-COPILOT-PRECHK-001/acceptance.md:313`(§D 퇴화·경계 케이스)의 *"픽스처 0개는 거부가 아니라 정상이다"*와 매크로 풀의 인용 근거를 충돌시킨다. 순회는 **자기 정책**을 갖는다 — 1·2단은 목록 완전성(짧으면 상계 미계산), 3단은 계수 존재성(`childCount`가 **1 이상의 정수**면 성공). **수렴은 별도 리팩터 SPEC의 일이며 본 계획이 그 사실을 기록한다.**

---

## §E. 사용자 접점

### §E.1 추가로 받을 승인 0건

**현재 받아야 할 사용자 승인은 0건이다.** 확보된 1건(어휘 확장, 2026-07-30)이 착수 전에 완료됐고 §A.3이 정본이다.

| 시점 | 접점 | 상태 |
|---|---|---|
| Kickoff | 어휘 확장 승인 | **확보 (2026-07-30)** — 재질의 0건 |
| Kickoff | 라이브 세션 접근 가능성 | **해당 없음** — 라이브 0회(§A.4) |
| Kickoff | `server/safety/**` 조건부 예외 승인 | **해당 없음** — 신규 예외 0지점(`REQ-OVERLAP-002`). **단 §E.2의 조건부 1이 이것을 되살릴 수 있다** |

**선행 SPEC과의 대비가 이 SPEC의 성격을 말한다.** 그 SPEC의 최대 위험은 승인 대기였고 그것이 M1을 막고 M2 이후를 정지시켰다(`.moai/specs/SPEC-COPILOT-PRECHK-001/plan.md:33`). **본 SPEC에는 코드 착수를 막는 접점이 없다** — 그러나 접점이 없다는 것은 위험이 없다는 뜻이 아니고, 위험이 **승인 대기가 아니라 판정 정직성**에 있다는 뜻이다(§D).

### §E.2 조건부 접점 3건

세 조건은 전부 정의된 결과를 가지며 **새 질문을 만들지 않는다.** 사용자에게 무엇을 물을지가 아니라 무엇을 고지할지가 정해져 있다.

| # | 조건 | 접점 | 왜 사용자 접점인가 |
|---|---|---|---|
| 1 | **`ASSUMPTION-34` 부정** — 3단 순회가 `query_property`를 요구한다 | **사용자에게 PRESERVE 서술 개정을 고지한다.** `spec.md` §C가 *"`server/safety/**`를 무변경으로 둔다"*고 적었고 그것이 바뀐다. 대체 설계를 묻지 않고, PRECHK가 연 조건부 예외 4지점을 재사용하는 형태와 그 사유를 공유한다 | PRESERVE는 사용자가 잠근 경계다. 조사 판정(`research.md` §9.6)이 `[추론]`이었으므로 부정은 예상된 결과 중 하나이며, **경계가 움직이면 고지 없이 진행하지 않는다.** 그리고 §B.0의 표대로 M6·M7의 형상이 함께 바뀐다 |
| 2 | **새 상계 산출이 기존 정확폭 경로를 바꿔야 하는 경우** | **오케스트레이터가 사용자에게 회귀 범위를 고지하고 후속 판단을 요청한다.** `AC-OVERLAP-013` ④가 *"착수 시점의 정확폭 테스트가 전건 통과"*를 요구하므로, 그것을 만족시킬 수 없다는 판정이 나오면 그 자체가 정본 위반이며 워커가 우회하지 않는다 | 정확폭 경로는 이미 출하된 거동이다. `REQ-OVERLAP-013`이 *"기존 `FootprintPolicy` 경로를 깨지 않는 것이 요건"*이라고 적었으므로, 깨야 한다는 판정은 요구 개정이고 워커 재량이 아니다 |
| 3 | **M8이 산수 부정합을 내는 경우** — 툴 종단 산출이 §C.4의 산술과 어긋난다 | **불일치 자체를 `progress.md`에 기록하고 오케스트레이터에게 후속 판단을 요청한다.** M8이 인용된 실측 값을 덮어쓰지 않는다 | 선행 SPEC이 같은 형태의 접점을 두었다 — *"M8에서 M0 판정과 종단 관측이 어긋나는 경우 불일치 자체를 기록하고 M8이 M0 판정을 덮어쓰지 않는다"*(`.moai/specs/SPEC-COPILOT-PRECHK-001/plan.md:289`) `[문서]`. 본 SPEC에서 어긋남의 후보는 상계 31·간격 42·17쌍 셋이며, 셋 다 **인용 값**이므로 본 SPEC이 정정할 권한이 없다 |

**Implementation Kickoff Approval은 위 접점의 승인을 받는 절차이지 `CONTRACT.md` §2의 결정 8건을 다시 여는 절차가 아니다.**

---

## §F. 부록 — 직접 생산하는 산출물 목록

### §F.1 신규

| 파일 | 소유 마일스톤 | 내용 |
|---|---|---|
| `server/prechk/footprint.py` | M2 (신설) · M3 (확장) | 3단 순회 · 완전성 술어 2종 · 조회 예산 · 실패 분류 · 인접 간격 · 판정 술어. **경로와 예산을 인자로 받는 순수 함수**이며 `server.orchestrator.tools`를 import하지 않는다 |
| `server/tests/test_prechk_footprint.py` | M2 · M3 · M4 · M8 | 위 모듈의 단위 테스트. `bound_inconclusive` 분기의 합성 리그가 여기 산다 |
| `server/tests/test_overlap_preserve.py` | M7 | PRESERVE 상시 게이트. **PRECHK BASE `95687a0e…` 상수를 단독 소유한다** |
| `.moai/specs/SPEC-COPILOT-OVERLAP-001/progress.md` | M0~M8 (오케스트레이터 소유) | 전제 접두 행 5건 · 마일스톤별 뮤테이션 killed/survived · M8 역방향 결과 · §F 모드 확정 기록 |

### §F.2 갱신

| 파일 | 소유 마일스톤 | 갱신 성격 |
|---|---|---|
| `server/prechk/verdicts.py` | M1 | 신규 축 상수 + 레지스트리 **맨 끝 append** + `SKIPPED_CHECK_KIND` 값 1개. 기존 5줄 바이트 동일 |
| `server/prechk/report.py` | M1 · M5 | `OVERLAP_BASIS_LABELS` 신설 · `VOCABULARY_LABELS` 항목 · **가드 루프 구조 교체** · 요약 배선 |
| `server/prechk/patch.py` | M3 · M4 | 그룹핑 추출 · 주소 범위 검증 · 미확정 격리 · 정확폭 우선 · 신규 최상위 키 · 근거 자료구조 |
| `server/orchestrator/tools.py` | M6 | `rig_paths` 수령 · 신설 섹션 가드 · 예산 스레딩 |
| `server/tests/test_prechk_verdicts.py` | M1 | **트립와이어 갱신 = 집행.** 정본 3단정. 형태 약화 0건 |
| `server/tests/test_prechk_report.py` | M1 · M5 | 추가만 |
| `server/tests/test_prechk_patch.py` | M3 · M4 | 추가만 |
| `server/tests/test_prechk_tool.py` | M6 · M8 | 추가만 |
| `server/tests/test_songcue_bundle.py` | M6 (편집) · M7 (판정) | **트립와이어 값 1행 갱신.** 보호구역 상수 `:65`는 바이트 동일 |
| `.moai/specs/SPEC-COPILOT-OVERLAP-001/spec.md` §C | **조건부만** — `ASSUMPTION-34` 부정 시 | PRESERVE 서술 개정 + 사유(`AC-OVERLAP-020` ②). 오케스트레이터가 수행하며 워커가 하지 않는다 |

### §F.3 버려지는 것

| 산출물 | 언제 | 왜 |
|---|---|---|
| M0의 인메모리 프로토타입 | `ASSUMPTION-34` 판정 직후 | **추적되지 않는 생산물이다.** `cycle_type=none`이므로 코드 변경 0건이며, 커밋하지 않고 워킹트리에 남기지 않는다. §B.0 DoD 4·5가 `git status --porcelain`으로 기계 판정한다 |

### §F.4 무변경 — 명시한다

`server/safety/**`(단 `ASSUMPTION-34` 조건부) · `console/lua/**` · `server/looks/{schema,loader,roles,resolver,instantiate,matching}.py` · `server/looks/library/` · `server/web/preview.py` · `server/rulebook/assets/v2.4.2/**` · `server/orchestrator/tools.py`의 보호구역 2개 · `.moai/specs/SPEC-COPILOT-PRECHK-001/**` 전체 · `server/tests/test_songcue_bundle.py:65`의 보호구역 상수 · `server/orchestrator/tools.py:157`의 `PRECHK_RIG_SECTIONS` · `PROPERTY_WHITELIST` · `server/tools/` 운영 유틸 예외 목록.

### §F.5 계수 요약

| 항목 | 값 |
|---|---|
| 신규 파일 | **4** (구현 1 · 테스트 2 · 기록 1) |
| 갱신 파일 | **9** + 조건부 1 (`spec.md` §C) |
| 버려지는 산출물 | **1** (M0 프로토타입) |
| 마일스톤 | **9** (M0~M8) |
| 배정 AC 합 | **21** — 중복 0 · 누락 0 (§B.10) |
| 새로 만든 요구·AC·전제 | **0** |
| 열린 결정 | **0** |
| clarification 마커 | **0** |
| 라이브 세션 | **0회** |
| 추가로 받을 사용자 승인 | **0건** (확보된 승인은 착수 전 1건 — §A.3) |

---

## §G. Phase 4 모드 선택 — 사전 평가 (오케스트레이터 확정용 권고)

> **구속력 있는 기록은 `progress.md` §F이며 오케스트레이터 소유다**(첫 run-phase `Agent()` 스폰 전 작성). **본 절은 권고이며 오케스트레이터가 확정하거나 기각한다. 어긋나면 `progress.md`가 이긴다.** 선행 SPEC이 같은 관계를 명문화했다(`.moai/specs/SPEC-COPILOT-PRECHK-001/plan.md:246` · `.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:1251`) `[문서]`.

### §G.1 입력 파라미터

- **tier**: M.
- **scope (file count)**: **13~14 파일.** 신규 구현 1 · 신규 테스트 2 · 갱신 구현 4 · 갱신 테스트 5 · 기록 1 · 조건부 정본 1(§F).
- **domain count**: **1.** Python 백엔드 + markdown 기록. Lua 응답기 · 프런트엔드 · 룰북 자산은 전부 PRESERVE이므로 **제2 도메인이 0개**다. 신규 런타임 의존성 0.
- **file language mix**: Python + markdown.
- **parallel benefit**: **LOW.** 근거는 §G.2의 사슬 셋과 §G.3의 파일 교집합이다.
- **Agent Teams prereqs**: 해당 없음.

### §G.2 사슬이 셋 겹친다

| 사슬 | 내용 | 왜 끊을 수 없나 |
|---|---|---|
| **어휘 사슬** | **M1 → M3 · M4 · M5** | `server/prechk/verdicts.py:50`의 `validate()`가 알려지지 않은 어휘 이름에 예외를 던지고(`:57-60`), 판정 계층의 코드값 상수는 **모듈 로드 시점**에 그것을 통과해야 한다(`server/prechk/patch.py:52-53`이 그 형태다) `[코드]`. **M1 전에는 세 마일스톤이 `overlap_basis` 값을 상수로 선언조차 못 한다 — import이 실패한다.** 정책이 아니라 물리다 |
| **데이터 사슬** | **M2 → M3 → M4 → M5 → M6 → M8** | M2의 상계가 M3의 입력, M3의 판정이 M4의 근거 배선 대상, M4의 페이로드 형상이 M5의 요약 입력, M5의 결과가 M6 툴 반환 형상, 전부가 M8의 종단 대상이다 |
| **모듈 사슬** | `footprint.py`(M2·M3) → `patch.py`(M3·M4) → `report.py`(M1·M5) → `tools.py`(M6) | 층으로 쌓인다. 선행 SPEC의 `inventory.py` → `patch.py` → `report.py`와 같은 형상이다(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:1275` `[문서]`) |

### §G.3 파일 교집합 — 병렬 슬라이스가 성립하지 않는다

선행 SPEC이 폭 2를 정당화할 때 쓴 판정 기준은 **파일 교집합 0건 · 데이터 의존 0건**이었다(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:1323-1332` `[문서]`). 같은 기준으로 본 SPEC을 재면 이렇다.

| 마일스톤 쌍 | 공유 파일 | 판정 |
|---|---|---|
| M2 ∩ M3 | `server/prechk/footprint.py` · `server/tests/test_prechk_footprint.py` | **교집합 2** |
| M3 ∩ M4 | `server/prechk/patch.py` · `server/tests/test_prechk_patch.py` | **교집합 2** |
| M1 ∩ M5 | `server/prechk/report.py` · `server/tests/test_prechk_report.py` | **교집합 2** |
| M6 ∩ M8 | `server/tests/test_prechk_tool.py` | **교집합 1** |
| M2 ∩ M4 | `server/tests/test_prechk_footprint.py` | **교집합 1** |
| **M7 ∩ 나머지 전부** | **없음** — `server/tests/test_overlap_preserve.py` 단독 | **교집합 0. 유일한 병렬 후보다** |

**M7만이 자립 슬라이스 후보이고 그것도 성립하지 않는다.** 두 이유다.

1. **입력이 M6 커밋에 걸려 있다.** `AC-OVERLAP-019` ④의 hunk 위치 봉쇄는 `git diff --unified=0 95687a0e…..HEAD -- server/orchestrator/tools.py`를 대상으로 하고, 그 diff는 **M6가 tools.py를 커밋한 뒤에야 최종값을 갖는다.** M7을 먼저 열면 봉쇄 판정을 두 번 써야 하고 두 번째가 첫 번째를 덮는다.
2. **이득이 비용보다 작다.** M7의 산출은 단일 테스트 파일이고 상수는 이미 실측 고정되어 있다(§A.5 · `research.md` §9). 워커 하나를 병행해 절약되는 것은 한 파일의 작성 시간이고, 지불하는 것은 hunk 재갱신과 두 워커가 같은 BASE 상수를 각자 해석할 위험이다 — **`CONTRACT.md` §4가 *"BASE 두 개를 절대 섞지 않는다"*고 못박은 지점에 조율 부담을 새로 만드는 것**이다.

### §G.4 모드 평가

| # | 모드 | 선택 | 근거 |
|---|---|---|---|
| 1 | trivial | 미선택 | 신규 모듈 · 어휘 확장 · 툴 배선 · PRESERVE 게이트 신설이 있다 |
| 2 | background | 미선택 | 코드 쓰기와 정본 판정이 포함된다 |
| 3 | agent-team | 미선택 | retired/tombstone 모드 |
| 4 | parallel | 미선택 | domain count 1 · 단일 언어 · 사슬 셋이 겹치고(§G.2) 병렬 후보가 M7 하나뿐이며 그것도 M6 커밋에 걸려 있다(§G.3) |
| 5 | **sub-agent** | **선택** | 순차 의존이 강하고, 각 마일스톤을 단일 워커가 계약대로 밀고 가는 편이 충돌이 적다 |
| 6 | workflow | 미선택 | 균일 기계 변환이 아니라 판정 정직성과 뮤테이션 결과를 계속 확인해야 한다 |

### §G.5 권고: **sub-agent 순차 — 폭 1**

**초기 폭은 1을 권고한다.** 근거 셋:

1. **어휘 사슬이 M1을 단독 선행물로 만든다** — `validate()`가 모듈 로드 시점에 어휘를 강제하므로 M1 없이는 M3·M4·M5가 import조차 되지 않는다(§G.2). 이것은 조율 문제가 아니라 실행 불가다.
2. **파일 교집합이 0인 마일스톤 쌍이 M7 하나뿐이고 그것도 M6 커밋에 걸려 있다**(§G.3) — 병렬화할 독립 슬라이스가 실질적으로 없다.
3. **M0가 새 도메인을 만들지 않는다** — `ASSUMPTION-34`가 `GO`면 형상 무변경이고 부정이면 **범위 재개정**이다(§B.0). 어느 쪽도 병렬 슬라이스를 만들지 않는다. 선행 SPEC에서 폭이 2로 올라간 계기는 M0가 미지를 닫아 **입력이 전부 확정된 자립 슬라이스**를 만든 것이었고, 본 SPEC의 M0는 그런 것을 만들지 않는다.

**선행 SPEC의 개정 선례를 인용한다.** 그 SPEC도 처음엔 폭 1이었다 — `plan.md` §G가 `sub-agent`를 권고하고 오케스트레이터가 `progress.md` §F에서 *"Decision: sub-agent (순차) — `plan.md` §G의 권고를 확정한다"*로 그대로 확정했다(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:1253` `[문서]`). 그리고 **M0 실측 후 M4를 병렬 슬라이스로 분리해 폭 2로 개정했다**(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:1313-1336` `[문서]`). 개정이 정당했던 조건이 명시되어 있다 — `ASSUMPTION-26`이 `GO`가 되어 저작 리터럴과 대상 그룹이 실측되면서 **M4의 입력이 전부 확정됐고**, 구현 파일·테스트 파일·입력·상호 의존 네 축에서 **파일 교집합 0건 · 데이터 의존 0건**이었다. M5 이후는 다시 폭 1로 돌아갔다.

**따라서 본 계획은 그 SPEC의 조항 하나를 계승한다 — *"폭을 미리 약속하지 않는다."*** M0나 이후 마일스톤이 새 도메인 또는 교집합 0의 자립 슬라이스를 만들면 오케스트레이터가 그때 `progress.md` §F를 개정하고 사유를 적는다. 본 절은 **초기 폭 1을 권고하고 개정 가능성을 닫지 않는다.**

**그리고 plan-phase에서 검증된 병렬 형태 하나는 run-phase에서도 유효하다 — 읽기 전용 scout다.** 본 SPEC의 plan-phase가 scout 4개를 동시에 돌려 충돌 0건으로 선행 기록의 오류·누락 5건을 잡았다(`research.md` §2 · §12). run-phase에서 조사가 필요해지면 같은 형태를 쓰며, 이것은 폭 권고와 무관하게 성립한다.

### §G.6 오케스트레이터가 확정할 때 함께 기록해야 하는 것

권고가 아니라 **참조 무결성 요건**이다. 선행 SPEC에서 `plan.md`가 존재하지 않는 `progress.md` §F를 구속력 있는 기록으로 지목해 **끊어진 참조**를 만든 사례가 있었고(`.moai/specs/SPEC-COPILOT-LOOKLIB-001/plan.md:289`) 후속 SPEC이 §F 헤딩을 **선제 생성**해 그것을 고쳤다(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:1251` `[문서]`). 본 SPEC의 `progress.md`도 §F 헤딩을 착수 시점에 선제 생성하며, 본문이 채워지기 전까지 비어 있음이 정상이고 **비어 있다는 사실 자체가 "아직 스폰하지 않았다"의 기록**이다.

§F가 확정 시점에 함께 담아야 하는 값 셋:

| 값 | 어디에 쓰이나 |
|---|---|
| 착수 SHA `85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a` | `AC-OVERLAP-002` ③ · M1 append-last 확인 · M8 역방향 checkout |
| PRESERVE 기준점 `95687a0e0eba90b325daf76efbd0ac197e69e2fc` | `AC-OVERLAP-019` ①②④⑤ — **본 SPEC BASE로 대체하는 것은 협상 불가**(§C.2) |
| 확정 폭과 그 사유 | 개정 시 §F 하위절로 추가하고 사유를 적는다 |
