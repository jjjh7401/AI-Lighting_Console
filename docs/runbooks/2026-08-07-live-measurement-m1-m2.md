# 라이브 측정 절차 — M1(`CueFade`) · M2(I-14 반환 타입)

> **이 문서는 콘솔이 붙는 세션이 그대로 집행하도록 썼다.** 읽는 순서: §0 → §1 → 해당 측정.
>
> 작성 2026-08-07 · 집행 전 · **측정 결과는 이 문서에 적지 말고 §4의 기록처로 보낼 것**

---

## §0. 착수 전 3줄 — 어긋나면 멈춰라

```bash
cd <repo>
uv run python -m server.tools.responder_roundtrip --expect-version 1.5.0 --skip-exec
```

- `[PASS] ping … live version=1.5.0` 이 나와야 한다.
- **버전이 다르면 측정하지 마라.** 재임포트가 실행 중 플러그인의 Lua 소스를 갱신하지
  않는 사례가 관측돼 있다(`console/lua/README.md` § Deployment Reliability). 다른
  버전에서 잰 값은 어느 응답기의 답인지 말할 수 없다.
- `[FAIL] state`가 나오면 OSC 출력 행(콘솔 → 이 호스트 `--listen-port`)이 없는 것이다.

---

## §1. 규율 — 이 측정에 한정해 다시 적는다

1. **관측하지 않은 것을 보고하지 않는다.** 못 읽으면 못 읽었다고 적는다.
   "아마 되겠지" · "비슷한 프로퍼티가 되니까" 는 관측이 아니다.
2. **거절도 결과다.** `ok=false`와 콘솔의 error 문자열을 **원문 그대로** 옮긴다.
   툴이 그것을 가공하지 않도록 만들어 뒀다(`responder_roundtrip.py`가 `value`/`error`를
   `!r`로 인쇄한다).
3. **날조 대조군을 반드시 함께 발화한다.** 존재하지 않는 이름이 **다른 답**을 내야
   그 답이 실제 판독이라는 것이 증명된다. GROUPGEN-001이 그룹 멤버십 `0`을 실제
   판독으로 확정한 것이 정확히 이 방법이다 — 대조군이 `ok:false`를 냈기 때문에
   실사용 그룹의 `0`이 "못 읽어서 0"이 아님이 성립했다.
   **대조군 없이 얻은 값은 이 프로젝트에서 증거가 아니다.**
4. 판정 어휘는 **GO / NO-GO** 둘뿐이다. "부분적으로 됨"은 GO가 아니라 **무엇이
   됐고 무엇이 안 됐는지** 두 줄로 나눠 적는다.

---

## §2. M1 — `CueFade`가 읽히는가 (비파괴, 약 10분)

### 무엇이 걸려 있나

`TrigType`·`TrigTime`은 응답기 v1.5.0의 `prop`으로 **이미 읽힌다**
(`SPEC-COPILOT-SCENE-001/spec.md:230`). 남은 것은 `CueFade`와 큐의 **내용** 둘이며,
내용은 반환 경로가 없다(`:232`). 그래서 이 측정의 대상은 `CueFade` **하나**다.

- **GO면**: 큐시트가 진짜 큐시트가 된다(이름 + `cueNo` + 트리거 + 페이드).
- **NO-GO면**: 명시적 DESCOPE 확정. **추정 열은 만들지 않는다** — 못 읽는 값을
  그럴듯한 기본값으로 채운 열은 오독을 생산한다.

### 구조는 이미 확인됐다 — 남은 것은 성립 여부뿐

`prop`은 임의 오브젝트 경로 + 단일 토큰 프로퍼티를 받고, 응답기의 매치가
`^(.-)%s+(%S+)%s*$` (경로에 비탐욕)이라 **경로에 공백이 있어도 마지막 토큰만
프로퍼티명으로 잘린다**. 이건 추정이 아니라 실제 Lua 응답기를 상대로 통과하는
회귀 테스트다 — `server/tests/test_responder_roundtrip.py::TestPropStep::
test_a_path_containing_a_space_reaches_the_responder_intact`.

즉 `DataPool/Sequences/1/Cue 1` + `CueFade`는 **발화 가능**하다. 콘솔이 답하는지가
미측정이다.

### 발화

먼저 대상 큐가 실재하는지 확인한다(경로가 틀리면 "없는 프로퍼티"와 "없는 오브젝트"가
같은 실패로 보인다):

```bash
uv run python -m server.tools.responder_roundtrip --skip-exec \
    --path "DataPool/Sequences/1"
```

`children`에 `Cue 1`류가 보이면 그 **실제 이름**을 아래에 그대로 쓴다.

```bash
# ① 본 측정
uv run python -m server.tools.responder_roundtrip --skip-exec \
    --prop-path "DataPool/Sequences/1/Cue 1" --prop-name CueFade

# ② 이미 읽히는 것으로 확정된 프로퍼티 — 양성 대조군
#    (이게 실패하면 경로가 틀린 것이지 CueFade가 없는 것이 아니다)
uv run python -m server.tools.responder_roundtrip --skip-exec \
    --prop-path "DataPool/Sequences/1/Cue 1" --prop-name TrigType

# ③ 날조 대조군 — 반드시 ①과 다른 답이 나와야 한다
uv run python -m server.tools.responder_roundtrip --skip-exec \
    --prop-path "DataPool/Sequences/1/Cue 1" --prop-name CueFadeXyzzy
```

### 판정표

| ① | ② | ③ | 판정 |
|---|---|---|---|
| `ok=true` + 값 | `ok=true` | `ok=false` | **GO.** 큐시트에 페이드 열을 넣는다 |
| `ok=false` | `ok=true` | `ok=false` | **NO-GO.** `CueFade`가 없는 것이다. DESCOPE 확정 |
| `ok=true` + 값 | `ok=true` | **`ok=true`** | **측정 무효.** 날조 이름이 답했다면 ①의 값도 실제 판독이 아니다. 이 경우를 무시하고 GO로 적지 마라 |
| — | `ok=false` | — | **경로 오류.** 큐 이름을 다시 확인하고 재실행. `CueFade`에 대한 판정을 내리지 마라 |

값이 나오면 **단위를 추정하지 말 것.** `"3"`이 초인지 프레임인지 이 측정은 말하지
않는다. 나온 문자열을 그대로 적고, 단위는 별도 측정이다.

---

## §3. M2 — I-14 (⚠️ **비파괴가 아니다**)

### 인계문서 정정 2건 — 착수 전에 읽어라

이전 인계문서(`docs/handoff/2026-08-07-session-handoff.md` §2 4️⃣)는 M2를
*"`ASSUMPTION-27` 미측정 후보 **2건**"* · *"비파괴 읽기"* 로 적었다. 실측 결과 둘 다
틀렸다.

**정정 ① — 후보는 2건이 아니라 1건이다.** 등재된 두 후보는 I-14와 I-15인데
(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md` §「`ASSUMPTION-27` 주장 범위
정정」의 표), **I-15는 이미 출하됐다** — 보수적 점유폭 상계가 곧
`SPEC-COPILOT-OVERLAP-001`이고 `status: completed`다. I-15는 애초에 라이브 측정이
필요한 후보도 아니었다(폭 ∈ {29,31}, 최소 간격 42라는 **기존 실측만으로** 성립하는
산술이다). 따라서 측정 대상은 **I-14 하나**다.

**정정 ② — I-14는 읽기가 아니다.** I-14의 내용은
*"`deploy` + `exec`로 콘솔측 프로브 플러그인을 올려 `handle:Get("FixtureType")`의
실제 반환 타입을 판독"* 이다. `deploy`는 쇼파일의 플러그인 풀에 **쓴다**. 저장소
파일을 건드리지 않으므로 `console/lua/**` PRESERVE는 침범하지 않지만, **쇼파일은
변한다.** 그러므로:

- **M1과 같은 세션에 묶어 "30분 비파괴 읽기"로 돌리지 마라.**
- 쓰기 게이트를 거쳐야 한다(`WRITEGATE-001`). 사용자 승인이 **제출 직전에** 필요하다.
- 착수 전 쇼파일 백업 상태를 확인하라. 스냅샷 보관·조회는 이미 있다
  (`server/safety/backup.py`) — **되돌려 올리는 발신부는 아직 없다**(§5 참조).
  즉 지금은 "망가지면 손으로 되돌린다"가 유일한 복구 경로다.

### 무엇이 걸려 있나

`ASSUMPTION-27`(픽스처↔채널폭 조인) 부정을 뒤집을 수 있는가. 뒤집히면 상계가
**정확폭으로 승격**한다. 안 뒤집히면 상계 유지 — 그건 이미 출하돼 돌아가고 있으므로
**NO-GO여도 잃는 것이 없다.**

### 왜 지금 급하지 않은가 (권고)

`ASSUMPTION-27` 부정의 정확한 주장 범위는 이미 좁혀져 기록돼 있다 —
*"변경하지 않은 응답기 읽기 표면(`state`·`prop`) 위에서, 실제 발화한 프로퍼티명
집합에 한정해 0건."* 그리고 같은 문단이 못박는다: **응답기는 프로퍼티명을 열거할 수
없으므로 어떤 프로퍼티 프로브 집합도 부재 증명이 될 수 없다**
(`copilot_responder.lua:204-217`).

I-14는 그 한계를 우회하는 유일한 후보지만 쓰기를 요구한다. **M1(순수 읽기, 이득
명확)을 먼저 집행하고, I-14는 쓰기 승인과 복구 경로가 갖춰진 세션으로 미루는 것을
권고한다.** 이 문서는 그 판단을 강제하지 않고 근거만 남긴다.

---

## §4. 결과 기록처 — 이 문서가 아니다

측정값은 해당 SPEC의 `progress.md`에 **원문 보존 + 소급 정정 각주** 형식으로 넣는다.
완결 SPEC의 과거 판정을 덮어쓰지 않는다.

| 측정 | 기록처 | 형식 |
|---|---|---|
| M1 `CueFade` | `.moai/specs/SPEC-COPILOT-SCENE-001/progress.md` | `:230`/`:232`의 YES/NO 판정 옆에 각주. GO면 `spec.md`의 NO 행에 소급 정정 각주 |
| M2 I-14 | `.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md` | §「`ASSUMPTION-27` 주장 범위 정정」의 후보표 I-14 행 |

기록에 **반드시** 포함할 것: 발화한 정확한 문자열 3건(①②③) · 각 응답의 `ok`/`value`/
`error` **원문** · 응답기 버전 · 측정 일시 · 쇼파일 식별. 그중 하나라도 없으면
다음 사람이 재현할 수 없고, 재현할 수 없는 수치는 이 프로젝트에서 근거가 아니다.

---

## §5. 이 문서가 다루지 않는 것

- **`TrigType`·`TrigTime`** — 측정 대상이 **아니다.** 이미 읽힌다(SCENE-001 `spec.md:230`).
  ⚠️ 단 그 행의 판정은 `YES — 단 **게이트 우회 직결 경로**`다(`server/safety/console.py:391`
  `query_property`). `CueFade`가 GO여도 **같은 우회 경로를 물려받는다** — 큐시트가 그
  값을 쓰려면, 판독 가능 여부와 별개로 그 경로를 그대로 둘 것인지가 결정 사항이다.
  이 측정은 그 결정을 내리지 않는다.
- **그룹 멤버십** — 측정 대상이 **아니다.** 사다리 전량과 대조군까지 이미 탔고
  플랫폼 한계로 확정됐다(GROUPGEN-001 `spec.md:361-364`).
- **큐의 내용(저장된 값)** — 반환 경로가 존재하지 않는다(SCENE-001 `spec.md:232`).
  `CueFade`가 GO여도 이건 열리지 않는다. 둘을 한 덩어리로 다루지 마라.
- **쇼파일 복원 발신부** — 스냅샷 보관·조회·감사연결은 완료, 되돌려 올리는 발신부만
  비어 있다. 자리는 `server/safety/gate.py`의 `@MX:NOTE`에 예약돼 있고 사유는
  `server/safety/backup.py:24-28`에 있다. **자체 SPEC이 필요하다.**
