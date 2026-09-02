# t237 — 🔴 벽이 아니었다. 막힌 것은 `Off Fixture` 하나이고, 되돌리는 길은 그때도 열려 있었다

기준: 워크트리 `.claude/worktrees/t237` · 브랜치 `WT-revert-path-rescope` · base `origin/main 7a2977f`
2026-09-02 · **콘솔 접촉 0 · 콘솔 쓰기 0 · 코드 변경 0**
원문 출력: `.moai/reports/t237/evidence/0{1..5}-output.txt` (재현 스크립트 같은 디렉터리)
재현: `PYTHONPATH=. .venv/bin/python .moai/reports/t237/evidence/0N-*.py` — 저장소 루트에서

## 0. 🔴 첫 줄 — 카드 제목이 남은 사실보다 넓다

카드 제목은 「**하네스에서 프로그래머를 되돌릴 방법이 없다**」였다. **그 문장은 이제 거짓이다.**

- `Clear` 는 게이트에서 `safe` 다 — 승인 통로 없이도 통과한다(§2).
- `ClearAll` 도 `safe` 이고, 이 저장소의 출하 경로가 **이미 수십 건 실행해 왔다**(§2.3).
- `t248` 이 `Clear` 로 `COUNTTOTALSELECTED` **1 → 0** 복귀를 되읽기로 실측했다.

살아남은 사실은 **하나**뿐이다: `Off Fixture <fid>` 는 승인 통로가 없는 배선에서 거부된다.
그건 「되돌릴 수 없다」가 아니라 **「가장 정밀한 해제 문형 하나가 승인을 요구한다」**다.

> **이 카드를 착수 조건으로 인용한 카드가 있다면 그 조건은 풀렸다** — 인용처는 §6.

**🔴 그러나 이 절을 「이제 안전하다」로 읽지 마라.** 되돌리는 길은 열려 있지만
**되돌아갔는지 확인하는 계기는 절반만 있다.** 그 절반이 §5 의 함정이고, 이 회차에서
가장 값나가는 발견이다.

## 1. 만료 판정 — 2026-09-01 에는 셋 다 참이었다

카드가 틀렸던 것이 아니다. **기록은 안 흐르는데 세상이 흘렀다.**
그날엔 `Clear` 를 아무도 안 쐈고, 프로그래머 되읽기 채널도 없었다.

| 카드가 적은 것 | 2026-09-01 | 2026-09-02 (오늘) | 무엇이 바꿨나 |
|---|---|---|---|
| 「되돌릴 방법이 없다」 | 참 (아무도 안 쟀다) | **거짓** | `t246` 오프라인 분류 + `t248` 실측 되읽기 |
| 「남았는지조차 관측 불가」 | 참 | **거짓 — 절반만** | `t248` 이 `prop COUNTTOTALSELECTED` 로 **선택**을 읽었다. **값**은 여전히 못 읽는다(§5) |
| `Off Fixture 501` → 거부라 hold | 참 | **참 · 오늘 재현됨** | 안 바뀌었다. 다만 **원인이 게이트가 아니었다**(§4) |

세 줄 중 셋째만 살고, 둘째는 **절반만** 죽었다. 「관측 불가」를 통째로 지우면
§5 의 위험이 사라진 것처럼 읽힌다 — 그건 반대 방향의 오류다.

## 2. 물음 ① — `Clear` 가 `Off Fixture` 를 어디까지 대신하는가

### 2.1 게이트에서는 완전히 대신한다

```
'Clear'                     category=safe        (승인 불필요)
'ClearAll'                  category=safe        (승인 불필요)
'Off Fixture 501'           category=invoking -> hold -> 승인 필요
```
(`evidence/01-output.txt` · 정본 룰셋 `server/safety/blacklist.yaml` 을 그대로 로드)

### 2.2 🔴 의미에서는 **대신하지 못한다 — `Clear` 는 단계 명령이다**

정본 룰북(`server/rulebook/assets/v2.4.2/00_grammar.md:57-58`):

```
| `Clear`    | Step programmer clear (selection -> values) | `Clear`    |
| `ClearAll` | Clear the whole programmer                  | `ClearAll` |
```

`server/orchestrator/tools.py:831` 의 주석도 같은 값을 든다 — `# step clear (selection -> values)`.

**즉 `Clear` 한 번은 선택만 지운다. 값은 다음 `Clear` 가 지운다.**

| 문형 | 범위 | 게이트 | 우리 용도(쏜 것을 되돌린다) |
|---|---|---|---|
| `Off Fixture <fid>` | **한 대**, 정밀 | 승인 필요 | 가장 좁다. 감독 작업물 무손상 |
| `Clear` | 프로그래머 **한 단계** (선택 → 값) | 통과 | **두 번 쳐야 값까지 간다** |
| `ClearAll` | 프로그래머 **전체** | 통과 | 감독이 손으로 쌓아 둔 것까지 날린다 — `t233` 이 금지한 그 이유 |

**답: 우리 용도에는 `Clear` 로 충분하다. 단 한 번이 아니라 두 번이고, 그 사실이
지금까지 어디에도 안 적혀 있었다.** 이 카드는 「벽」이 아니라
**「더 정밀한 해제가 승인 뒤에 있다」**로 격하된다.

### 2.3 이 능력은 새로 생긴 게 아니다 — 출하 경로가 이미 쓰고 있었다

`ClearAll` 은 이 저장소의 실기 기록에 반복 등장하고 전부 `executed_ok` 다:

```
SPEC-COPILOT-FXLIB-001/progress.md:383   Store Sequence 3 Cue 1 '박자 펄스' / ClearAll   <- 10줄 전량 executed_ok
CHANGELOG.md:221 (M7 종단 라이브)         ChangeDestination Root 1건 · ClearAll 12건 전량 생존
tools/placement_verify.py:113,165        probe.exec("ClearAll")
```

🔴 **그래서 「되돌릴 방법이 없다」는 처음부터 저장소 안에서 반증 가능했다.**
`t233` 이 `ClearAll` 을 **금지**한 것은 옳았지만(범위가 너무 넓다), 그 금지가
**「해제 자체가 막혔다」로 굳는 데 한 걸음이 됐다.** 금지의 사유(범위)와
가능 여부(게이트)는 다른 축인데 한 문장에 섞였다.

### 2.4 두 번 치는 것이 dedupe 에 안 먹히는가 — 먹히지 않는다

```
'Clear'        programmer_state=True     <- dedupe 면제
'ClearAll'     programmer_state=True     <- dedupe 면제
'Clear Clear'  programmer_state=False    <- ⚠️ 한 문자열로 붙이면 면제가 안 걸린다
```
(`evidence/05-output.txt` · `server/orchestrator/tools.py:830-834`)

한 번들에 `Clear` 를 **두 줄로** 넣어야 한다. `"Clear Clear"` 한 줄은 룰북 문형도 아니고
면제도 못 받는다. 게이트 clearance 는 `Counter(commands)` 라(`gate.py:392`) 같은 명령
두 줄이면 발사 권한도 2회다 — **묶어 보내는 것이 맞는 형태다.**

## 3. 물음 ② — `Off Fixture` 가 막히는 것은 결함인가 설계인가

### 3.1 기전 (콘솔 접촉 0 으로 재확정)

```
blacklist.yaml:174-185   invoking_verbs.verbs 에 Off 가 있다
classify.py:44           RECOGNIZED_REFERENCE_TYPES = ('Macro','Plugin','Sequence','Executor')
classify.py:128 _extract_reference   -> 'Fixture' 는 그 넷이 아니다 -> None
expand.py:83             _hold('unverifiable reference: no recognizable target object')
```

### 3.2 판정: **과잉 거절이다. 다만 무해한 과잉이 아니다**

`invoking` 규칙의 목적은 **참조의 본문이 임의 명령을 담을 수 있다**는 위험이다
(`expand.py` 가 본문을 가져와 blacklist 를 다시 돌리는 이유). 픽스처 참조에는
**본문이 없다** — 그 위험이 구조적으로 부재한다. 그래서 형식적으로는 과잉이다.

그런데 `Off` 는 픽스처만 받지 않는다:

```
'Off'              -> invoking (참조 없음)     <- 맨 Off
'Off Group 1'      -> invoking (참조 없음)
'Off Sequence 1'   -> invoking (참조 Sequence 1)  <- 본문이 있는 진짜 위험
```

**`Off` 를 동사 축에서 푸는 것은 `Off Sequence` 까지 같이 여는 일이다.** 이 저장소는
그 방향의 비용을 이미 기록해 뒀다 — 동사로 키를 잡지 말고 **오브젝트로 잡으라**는 것이
`blacklist.yaml` 의 `Store Preset` · `Set Fixture` 항목이 든 이유다.

### 3.3 🔴 순진한 수리(참조 타입에 `Fixture` 추가)는 **무력하다 — 재서 확인했다**

```
reference_types = (…, 'Fixture', 'Group')
  'Off Fixture 501'  ref='Fixture 501'  hold=True
      reasons=("unverifiable reference 'Fixture 501': no body path mapping for 'Fixture 501'")
```
(`evidence/04-output.txt`)

`DEFAULT_BODY_PATHS` 에 `Fixture` 항목이 없으므로(`console.py:790`, 키는 Macro·Plugin·Sequence 셋)
**hold 사유 문자열만 바뀌고 결정은 그대로다.** 그리고 이것은 새 발견이 아니다 —
`classify.py:33-43` 의 `@MX:NOTE` 가 `Executor` 추가 때 **정확히 같은 일이 일어났다**고
적어 뒀다(「Recognition alone … is a no-op wrt the gate's observable decision」).

**설계 제안을 낸다면 그 선례를 먼저 읽어야 한다. 안 읽으면 두 번째로 같은 무효 패치를 만든다.**

### 3.4 설계만 낸다 — 발사도 배선 변경도 안 했다 (카드 경계)

| 갈래 | 형태 | 대가 |
|---|---|---|
| A **아무것도 안 바꾼다** (권장) | 해제는 `Clear`×2 로 한다. `Off Fixture` 는 승인이 필요한 정밀 도구로 남긴다 | 안전 배선 무변경. 대가는 「한 대만 끄기」가 승인 뒤에 있다는 것뿐 |
| B 본문 없는 오브젝트를 **별도 분류** | `Off <Fixture\|Group>` 만 오브젝트 축으로 좁혀 `safe` 로 | fail-closed 를 무는 변경. `Off Sequence` 는 안 건드리지만 **리드+감독 승인 사안** |
| C 참조 타입 확장 | — | **§3.3 에서 무력함이 확인됨. 후보가 아니다** |

🔴 **A 를 권한다.** B 가 여는 것은 「한 대만 끄기」 하나이고, 치르는 것은 안전 게이트의
거절 경계다. `Clear`×2 로 용도가 채워지는 이상 **지금 무를 이유가 없다.**

## 4. 🔴 `t233` §9.2 가 「추론」이라 표시한 자리를 쟀다 — 그리고 **틀렸다**

`t233` 은 t135(통과)와 t233(거부)이 갈린 이유를 **`question_port=_RefusingQuestions()`**
로 추정하고, ⚠️ 로 「이것은 추론이고 안 쟀다」를 명시했다. **정직한 표시였고, 그 덕에 잴 수 있었다.**

### 4.1 소스가 답한다 — 갈린 축은 `approval_port` 다

```
gate.py:338-352   held 가 있으면 -> self._approval_port.request_approval(...)
                    False -> status="rejected", reason 에 hold 사유 그대로
                    True  -> 계속 -> status="cleared", 같은 사유가 reasons 에 남는다
gate.py:159       self._approval_port = approval_port or DenyAllApprovalPort()
approval.py:45-49 DenyAllApprovalPort.request_approval -> return False
```

`_RefusingQuestions` 는 `build_toolset(question_port=...)` 로 들어가는 **질문 카드 통로**이지
게이트의 승인 통로가 아니다. `t233` 의 프로브(`evidence/attr_probe.py`)는
`build_console_stack(...)` 를 **`approval_port` 인자 없이** 불렀다 — 그래서 기본값
`DenyAllApprovalPort` 가 거부한 것이다.

### 4.2 오프라인 재현 — 두 배선을 나란히 (`evidence/03-output.txt`)

```
--- approval_port=None (기본값 = DenyAllApprovalPort — t233 배선) ---
  'Off Fixture 501'  cleared=False status=rejected
        reasons=('reference-invoking command', 'unverifiable reference: no recognizable target object')

--- approval_port=Approve() (승인 통로 있음 — t135 배선) ---
  'Off Fixture 501'  cleared=True  status=cleared
        reasons=('reference-invoking command', 'unverifiable reference: no recognizable target object')
```

**두 회차가 관측한 문자열이 둘 다 재현됐다** — t233 의 거부 사유는 글자까지 같고,
t135 가 적은 「`unverifiable reference` 경고가 붙었지만 **cleared**」도 그대로 나온다.
같은 hold, 같은 사유, 다른 결론. **갈린 것은 게이트가 아니라 승인자다.**

### 4.3 그래서 `t233` §9.3 의 규약 문장이 **더 강해진다**

> 기록에 `cleared` 가 있으면 그것이 무조건 통과였는지 **승인을 거친 통과였는지**를 갈라야 한다.

이 문장은 옳았고, 이제 **기전까지 확인됐다** — `gate.py:398-403` 은 승인을 거친 통과에도
같은 `status="cleared"` 를 붙이고, 구분은 `approval_request` 필드에만 남는다.
**판별자는 통과 옆의 메타데이터라던 t233 의 지목이 정확했다.**

⚠️ 다만 `t233` 이 지목한 **범인의 이름은 틀렸다.** 축(승인 통로)은 맞고 객체(`_RefusingQuestions`)가
아니었다. `t233` 은 그것을 추론으로 표시했으므로 **이것은 그 문서의 결함이 아니라
그 표시가 작동한 사례다.**

## 5. 🔴 물음 ③ — 남은 진짜 위험: **계기가 위험한 상태에서 0 을 답한다**

`Clear` 가 게이트에서 실패하는 경로는 **없다**(`safe`, 승인 불필요, dedupe 면제).
위험은 실패가 아니라 **관측**에 있다.

```
값을 실은 뒤 Clear 를 한 번 친 상태:
    선택  = 비었다          -> COUNTTOTALSELECTED = 0   ← 우리 유일한 계기가 0 을 답한다
    값    = 남아 있다        -> 읽을 필드가 없다          ← 계기 자체가 없다
```

**즉 「값이 남은 위험한 상태」와 「완전히 비운 안전한 상태」가 우리 계기로 같은 0 을 낸다.**
이것은 `t248` §5 가 기록한 「망가진 계기가 정답과 같은 글자를 냈다」와 **같은 계열의
둘째 사례**다 — 이번엔 계기가 망가진 게 아니라, **멀쩡한 계기가 다른 축을 보고 있다.**

그 상태에서 `Store` 가 돌면 남은 값이 실린다 — `t108 C1` 이 그 형태다.

| 등급 | 근거 |
|---|---|
| `Clear` 가 단계 명령이라는 것 | **문면 근거** — 정본 룰북 `00_grammar.md:57`, 코드 주석 `tools.py:831` 이 독립으로 같은 말 |
| 한 번 친 뒤 값이 실제로 남는가 | **미측정** — 이 콘솔에서 아무도 안 쟀다. 값을 실어야 잴 수 있고 그건 새 승인이다 |
| `COUNTTOTALSELECTED` 가 값 축을 안 본다는 것 | **미측정** — `t248` 이 값을 한 번도 안 실었다(§7) |

🔴 **그래서 처방은 「`Clear` 쓰면 된다」가 아니라 「`Clear` 를 **두 줄** 보내고,
되읽기로는 절반만 확인된다는 것을 알고 쓴다」다.**

## 6. 인용처 — 센 개수와 전체 개수를 나란히

| 대상 | 검색한 전체 | `t237` 을 담은 것 |
|---|---|---|
| 저장소 파일 (`.git`·`node_modules`·`__pycache__` 제외) | **1,893** | **0** |
| 큐 카드 (`moai todo`) | **193** | **3** — `t237` 자신 + **2건** |

인용 2건의 내용:

| 카드 | 인용한 문장 | 이 판정 뒤 |
|---|---|---|
| `t245` (queued) | 「해제가 `Off Fixture` 로 막히면(t237) **그 자리에서 멈추고 보고해라**」 | 🔴 **정지 조건이 풀렸다.** 해제 경로는 `Clear`×2 다. 다만 §5 때문에 **되읽기 확인은 절반**이라는 단서가 붙는다 |
| `t246` (dropped·닫힘) | 「막힌 것은 `Off Fixture` 이지 프로그래머 해제 자체가 아니었다」 | 이 판정과 **일치**. t246 이 이미 옳게 적었고, 이 회차가 독립 경로로 재현했다 |

🔴 **`t246` 이 어제 이미 정확히 적어 뒀다는 것이 이 회차의 뼈아픈 값이다.**
「막힌 것은 `Off Fixture` 이지 해제 자체가 아니다」가 닫힌 카드 본문에 있었는데,
`t237` 은 그 사실을 못 받고 「벽」으로 하루를 더 살았다.
**닫힌 카드의 본문은 아무도 안 읽는다** — 그것이 이 회차가 남기는 규약 후보다.

## 7. 안 잰 것

| 미측정 | 왜 |
|---|---|
| `Clear` 한 번 뒤 값이 실제로 남는가 | 값을 실어야 재고, **그건 새 승인이다**(카드 경계에서 명시적으로 배제됨) |
| `Clear` 두 번이 실제로 값을 지우는가 | 위와 같음. 룰북 문면만 있고 이 콘솔 실측 0 |
| `ClearAll` 과 `Clear`×2 의 차이 | 안 쟀다. 룰북은 전자를 「전체」로 적지만 무엇이 더 남는지 모른다 |
| 프로그래머 **값** 축의 판독 필드 | 존재 여부 자체가 미확인. `t248` 이 `ProgrammerPart COUNT` 를 봤지만 **무엇을 세는지 안 쟀다** |
| `Off Group <n>` · 맨 `Off` 의 실기 거동 | 오프라인 분류만 했다. 콘솔 접촉 0 |
| B 갈래(오브젝트 축 분류)를 실제로 구현했을 때의 회귀 | 코드 변경 0 — 설계만 냈다 |

## 8. 잔여 위험

- **§0 을 「이제 안전하다」로 요약하면 §5 가 사라진다.** 되돌리는 길과 되돌아갔음을
  확인하는 길은 **다른 축**이고, 후자는 아직 절반이다. **이 문서에서 §0 과 §5 를
  떼어 인용하지 마라.**
- **`t235`(응답기 Programmer 판독 별칭)와의 짝은 여전히 유효하다.** 카드가 물은
  「둘 다 필요한가 하나로 되나」의 답: **둘 다 필요하다.** 해제는 열렸고(`Clear`),
  값 축의 되읽기는 여전히 없다. `t235` 는 이 카드가 닫혀도 안 닫힌다.
- **`Clear` 를 한 줄만 보내는 하네스 코드가 어딘가에 생기면 §5 의 함정에 그대로 들어간다.**
  이 회차는 코드를 안 고쳤으므로 그 방어는 **아직 없다.**
- **§3.2 의 「과잉 거절」 판정은 형식 논증이다.** 픽스처에 본문이 없다는 것은
  `DEFAULT_BODY_PATHS` 로 확인했지만, MA3 가 픽스처 참조에 본문 비슷한 것을
  붙이지 않는다는 것은 **콘솔에 안 물어봤다.**

## 9. 이 회차가 안 한 것

- **콘솔 접촉 0.** 소켓을 한 번도 안 열었다 — 모든 프로브는 가짜 `ConsolePort` 이고,
  §3.3 의 fetcher 는 질의가 닿으면 `AssertionError` 를 내도록 짜 뒀다(닿지 않았다).
- **코드 변경 0.** `server/safety/**` byte-diff 0. §3.4 의 갈래 B 는 **설계만** 이고
  구현·발사 둘 다 안 했다.
- **큐 카드를 안 고쳤다.** 만료 고지는 `t240` 선례대로 **문서**에 붙였다
  (`.moai/reports/t233/verdict.md`) — 카드 본문 재작성은 리드/감독의 행위다.
  카드용 문안은 §10 에 붙여넣기 형태로 뒀다.
- **머지 안 했다** — 리드가 확인하고 한다.

## 10. 리드에게 — 카드 `t237` 본문에 붙일 만료 고지 (붙여넣기용)

```
⚠️ 만료 고지 (t237 자기 판정, 2026-09-02) — 제목의 「되돌릴 방법이 없다」는 거짓이 됐다.
Clear 는 게이트에서 safe 이고(승인 불필요) t248 이 COUNTTOTALSELECTED 1→0 복귀를 실측했다.
ClearAll 은 이 저장소 출하 경로가 이미 수십 건 실행해 왔다. 살아남은 사실은 셋째 하나 —
Off Fixture <fid> 가 승인 통로 없는 배선에서 거부된다는 것뿐이고, 그 원인도 게이트가 아니라
approval_port 기본값(DenyAllApprovalPort)이었다(t233 §9.2 의 _RefusingQuestions 추정은 반증).
처방 갱신: 해제는 Clear 를 **두 줄** 보낸다(단계 명령 — 1회는 선택만, 값은 2회째).
🔴 다만 우리 계기(COUNTTOTALSELECTED)는 1회째 Clear 뒤 이미 0 을 답하므로 「값이 남은 위험한
상태」와 「완전히 빈 상태」를 구분하지 못한다 — 값 축 되읽기는 여전히 t235 뒤에 있다.
판정서: .moai/reports/t237/verdict.md · 2026-09-01 시점에는 원문 셋 다 참이었다.
```
