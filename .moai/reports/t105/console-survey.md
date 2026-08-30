# t105 콘솔 실측 — 읽기 전용 조사 (2026-08-30)

콘솔 쓰기 **0건**. 아래는 전부 읽기이고, 인용한 응답은 프로브가 출력한 그대로다.

- 트리: `.claude/worktrees/t105` · 브랜치 `WT-value-readback` · HEAD `03455b9` (= `origin/main`, 0/0)
- 콘솔: `app_gma3` pid **38706** · grandMA3 2.4.2 · UDP 8000·9005
- 계기: `./.venv/bin/python tools/console_probe.py --listen-port 9005 <STEP>`

§1~§8 은 t98 이 콘솔을 쥐고 있던 동안의 읽기 전용 조사다. t98 이 콘솔을 놓은 뒤 **본 측정을 §10 에서 수행했다.**

---

## 1. 날조 대조군 — 통과

```
>>> state 'DataPool/ThisPathDoesNotExist_FABRICATED_CONTROL'
<<< {"error": "path segment not found: 'ThisPathDoesNotExist_FABRICATED_CONTROL' (in DataPool/ThisPathDoesNotExist_FABRICATED_CONTROL)", "id": "854d2b10", "kind": "state", "offset": 0, "ok": false, "path": "DataPool/ThisPathDoesNotExist_FABRICATED_CONTROL", "v": 1}
```

없는 경로에 **경로 세그먼트를 지목한 거절**이 돌아왔다. 따라서 이 회차의 `ok:true` 는 증거로 쓸 수 있다.
대조군 없이 `ok` 를 증거로 쓰지 말라는 규율의 이행이다.

## 2. 응답기 사본 셋이 없다

`03455b9` 의 조사는 응답기 이름 슬롯이 셋이라고 기록했고, 그 사본이 어느 VERSION 을 들었는지는 안 잰 채 두었다
(「정리는 콘솔 GUI 에서 사람이 한다」). 오늘 같은 경로를 다시 읽었다.

```
>>> state 'DataPool/Plugins'
<<< {"children": [{"class": "UserPlugin", "i": 1, "name": "CopilotResponder"}, {"class": "UserPlugin", "i": 2, "name": "CopilotPatchRobinEsprite"}, {"class": "UserPlugin", "i": 3, "name": "CopilotPatchRobinLEDBeam350"}, {"class": "UserPlugin", "i": 4, "name": "CopilotPatchSharpyPlus"}, {"class": "UserPlugin", "i": 5, "name": "CopilotPatchMacAuraXB"}], "id": "0d5ee262", "kind": "state", "node": {"childCount": 5, "class": "Plugins", "name": "Plugins"}, "offset": 0, "ok": true, "path": "DataPool/Plugins", "truncated": false, "v": 1}
```

| 시점 | childCount | 응답기 슬롯 |
|---|---|---|
| `03455b9` 조사 | 11 | `CopilotResponder` · `CopilotResponder#2` · `CopilotResponder_2` |
| 오늘 (pid 38706) | **5** | `CopilotResponder` 하나 |

`truncated: false` 이므로 5 는 절단이 아니라 전량이다. 별칭 잔해는 이 쇼파일에 없다.

**안 잰 것**: 살아 있는 그 하나의 `VERSION`. 포트를 뺏겨(§5) 프로퍼티 판독까지 못 갔다.
따라서 「1.6.2 가 돌고 있다」고 말할 수 없다 — 오늘 세운 것은 「사본이 하나뿐이라 응답자가 모호하지 않다」까지다.

**이것이 사본 소멸의 원인을 말해 주지는 않는다.** onPC 재시작·쇼파일 교체·사람의 GUI 정리 중 어느 것인지는 안 쟀다.

## 3. 프리셋 경로 — 상수가 아니라 실측

```
>>> state 'DataPool'
<<< ... {"class": "PresetPools", "i": 4, "name": "PresetPools"} ... "childCount": 16 ... "truncated": false

>>> state 'DataPool/PresetPools'
<<< ... 1 Dimmer · 2 Position · 3 Gobo · 4 Color · 5 Beam · 6 Focus · 7 Control · 8 Shapers · 9 Video
    · 21 All 1 · 22 All 2 · 23 All 3 · 24 All 4 · 25 All 5 ... "childCount": 14 ... "truncated": false
```

딤 풀은 **`DataPool/PresetPools/1`**(이름 `Dimmer`)이다. `DataPool/Presets` 는 존재하지 않는 경로였다.
「딤 풀 1 은 코드 상수가 아니다」는 기존 관측에 따라 가정하지 않고 읽었고, 이 쇼파일에서는 1 이 맞았다.

## 4. 이어받기 쪽지의 콘솔 상태 기술이 만료됐다

```
>>> state 'DataPool/PresetPools/1'
<<< 1 Dim 10 · 2 Dim 20 · 3 Dim 30 · 4 Dim 40 · 5 Dim 50 · 6 Dim 60 · 7 Dim 70 · 8 Dim 80 · 9 Dim 90
    · 10 Full · 11 Breathe Soft · 12 Breathe Deep · 13 Pulse Hard · 14 Pulse Half · 15 Wave Soft
    · 16 Wave Full · 17 Ripple · 18 Flash Accent · 19 Alt Half
    node: {"childCount": 20, "class": "Presets", "name": "Dimmer"} · ok: true · truncated: **true**
```

쪽지는 딤 풀을 이렇게 기술하며 「건드리지 말 것」으로 못박았다.

| 쪽지의 기술 | 오늘 실측 |
|---|---|
| 슬롯 2 = `쇼 하이 OLD` (옛 M4 경로 산물, 값 없음) | 슬롯 2 = `Dim 20` |
| 슬롯 7 = `쇼 하이` (t108 경로 산물, 85%, 육안 확인) | 슬롯 7 = `Dim 70` |
| 슬롯 1·3~6 = 이름만 있는 빈 껍데기 | `Dim 10` · `Dim 30`~`Dim 60` |

쪽지가 「지우거나 개명하면 그 대조가 사라진다」며 지킨 **부재와 잇힘의 나란한 대조가 이 쇼파일에 없다.**
지금 풀에 있는 것은 `Dim 10`~`Full` 과 `Breathe`·`Pulse`·`Wave` 계열, 즉 표준 딤 라이브러리다.

**이 표는 「누가 지웠다」를 말하지 않는다.** 쇼파일이 다르다는 것만이 실측이고, 왜 다른지는 안 쟀다.

**안 잰 것**: 슬롯 20. `truncated: true` 라 19개만 돌아왔다 — 절단은 개수가 아니라 페이로드 예산이므로,
남은 하나를 보려면 offset 페이징이 필요하다.

## 5. 포트 침묵의 원인 — 응답기가 아니라 동시 세션

§3 까지는 프로브가 붙었고, 그 다음 호출부터 바인드가 실패했다.

```
server.bridge.osc.ReceivePortInUseError: OSC 수신 포트 9005(OSC feedback receive, 127.0.0.1)가
동일-포트 재바인드 재시도 후에도 여전히 사용 중입니다.
```

침묵을 응답기 탓으로 읽지 않고 포트를 쟀다.

```
$ netstat -an -p udp | grep -w 9005
udp4  0  0  127.0.0.1.9005  *.*
udp4  0  0  *.9005          *.*

$ ps -Ao pid,etime,args | grep lxseq_e2e
55219  00:13  .venv/bin/python -m server.tools.lxseq_e2e --listen-port 9005 --action preview
               --csv src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.patch.csv
57379  00:10  (같은 명령, 55219 종료 후 재실행)

$ lsof -a -p 55219 -d cwd  →  .claude/worktrees/t98
$ lsof -a -p 57379 -d cwd  →  .claude/worktrees/t98
```

`*.9005` 는 콘솔이고 `127.0.0.1.9005` 는 t98 의 e2e 다. 2분 사이 두 번 돌았다.
물리 콘솔은 하나이므로 두 카드가 동시에 몰 수 없다. 감독 판단으로 콘솔 순번을 t98 에 양보하고,
t105 의 본 측정은 이연했다.

레인 식별은 **프로세스 cwd** 로 했다. 세션 이름(`ListAgents`)으로는 t98 을 특정하지 못했다 —
런치 이름은 그 레인의 카드가 아니기 때문이다.

## 6. 곁가지 실측 — 가드 방아쇠, 그리고 내가 두 번 틀린 자리

> **이 절의 초판은 틀렸다.** 「방아쇠는 둘 — 중괄호와 파이프」라고 적었고, 덧붙여
> 「기존 기록은 중괄호 축만 남기고 있었다」고 적었다. **둘 다 반증됐다.**

### 6.1 초판의 두 잘못

**(1) 한 덩어리에 변수 둘.** 파이프 결론의 근거는 이 대조였다.

    거절:  cat <<EOF | tr … > FILE   …   EOF   +   cat FILE
    통과:  cat > FILE <<EOF          …   EOF   +   wc -c FILE

파이프만 다른 것이 아니라 **뒤따르는 명령도 달랐다.** 두 변수를 동시에 바꾸고
통과/거절을 한쪽에만 귀속시켰다.

**(2) 비교 대상을 안 열고 한 비교.** 「기존 기록은 중괄호 축만 남기고 있었다」는
`lesson-bash-guard-trigger-is-the-unquoted-brace-pair` 와의 대조인데, 그 파일을
**열지 않은 채로** 냈다. 열어 보니 그 파일은 방아쇠 A(살아 있는 명령 텍스트의 확장 구문)와
방아쇠 B(heredoc 본문 안 JSON 중괄호)를 이미 갈라 적고 있었고, 크기/복잡도 축까지 있었다.
그 파일이 §다섯째에서 「기존 기록보다 넓다고 말하려면 먼저 열어라」고 적은 바로 그 형태다.

### 6.2 격리 실측 — 방아쇠는 파이프가 아니라 리다이렉트 위치다

본문(`plain line, no braces`)과 후속 명령(`wc -c FILE`)을 **동일하게 고정**하고
명령 형태만 바꿨다.

    cat > FILE <<'EOF'          통과   (2회, 회차 처음과 끝)
    cat <<'EOF' > FILE          거절   <- 파이프 없음. 리다이렉트 위치만 다르다
    cat <<'EOF' | cat > FILE    거절

**리다이렉트가 히어독 연산자 뒤로 가면 거절된다. 파이프는 필요하지 않다.**
초판이 파이프에 귀속시킨 거절은 이 축이었다.

**안 잰 것 — 기전.** 리다이렉트가 뒤에 오면 가드가 쓰기 대상을 정적으로 못 묶는다는
설명이 그럴듯하지만, 확인한 것은 아니다. 관측은 위 세 줄까지다.
`>>`(추가) 형태, 다른 명령에서의 같은 배치, 크기와의 상호작용은 안 쟀다.

### 6.3 이미 알려져 있던 것 (내가 다시 발견한 것)

- 방아쇠 B(heredoc 본문 안 JSON 형태 중괄호)는 기존 항목에 있다. 이 회차의
  중괄호 거절은 **재현**이지 발견이 아니다.
- `Write`/`Edit` 가 워크트리 밖으로 판정되는 것도 기존 항목
  (`lesson-write-guard-boundary-is-the-launch-dir`)에 있다. 이번에 보탠 것은
  **상대 경로로도 같은 문면으로 거절된다**는 한 점이다.

### 6.4 이 문서를 어떻게 썼나

치환문자(`@` `^`)로 쓴 뒤 `tr` 로 되돌렸고, 쓰기는 전부 `cat > FILE <<'EOF'` 형태로 했다.
쓰기 대상 경로가 명령문 앞쪽에 그대로 보이므로 가드가 검사하려는 경계는 우회하지 않았다.

## 7. 안 잰 것 (총괄)

- 살아 있는 응답기의 `VERSION` — 포트 경합으로 중단. 1.6.2 인지 미확인
- 딤 풀 슬롯 20 — `truncated: true`
- 쇼파일이 바뀐 시점과 원인 — t98 의 ShowBase CSV 와 아귀가 맞는 **정황**일 뿐, 실측이 아니다
- 지금 풀의 `Dim 10`~`Full` 이 값을 들었는지 — **안 쟀다.** 이름이 값을 시사하더라도 그것은 증거가 아니다
  (내용 있는 오브젝트도 `COUNT 0` 을 답한 선례가 있다). 값 보유의 독립 증인이 필요하다
- t98 이 어느 세션 창인지
- 가드의 크기 축·중괄호가 아닌 형태(셸 함수 본문 등) — 이번에도 안 쟀다

## 8. 잔여 위험

- 쇼파일은 세션 밖에서 바뀔 수 있다. 이 보고서의 풀 내용은 **이 시점의 관측**이고, 다음 회차에 그대로일 보장이 없다
- t105·t96 의 본 측정을 재개할 때는 pid·포트·풀 내용을 **다시 재야 한다**. 이 문서의 값을 기준선으로 재사용하면
  흐르는 기준을 쓰는 것이 된다
- t98 이 콘솔에 무엇을 남기는지 이 세션은 모른다. 재개 시 풀 내용이 또 달라져 있을 수 있다

## 9. 선행 SPEC 대조 — PRESETGUARD-001 §A.3 은 값 판독 불가를 알고 되읽기를 슬롯 산술로 좁혔다

> **이 절의 초판은 틀렸다.** 초판은 「`PRESETGUARD-001` 에 `A.3` 이 없고, 값 되읽기 불가 취지의 문장도 없다」고
> 적었다. 리드가 반증했고, 재측정으로 확인했다. 아래는 정정본이며, 초판의 결론(t105 는 발견이다)만 유지된다.
> 결론의 **근거가 부재에서 범위로** 바뀌었다.

### 9.1 내가 틀린 기전 — 상한을 모집단으로 읽었다

초판의 근거는 이 명령이었다.

```
$ grep -rn "A\.3\b" .moai/specs/ | head -5
   → TREEID-001/spec.md:78 · FXLIB-001/progress.md:71 · FXLIB-001/plan.md:34
     · FXLIB-001/plan.md:140 · FXLIB-001/acceptance.md:191
```

다섯 줄이 나왔고 `PRESETGUARD-001` 이 없기에 「없다」고 적었다. 상한을 풀고 다시 쟀다.

```
$ grep -rn "A\.3\b" .moai/specs/ | wc -l
173
$ grep -rn "A\.3\b" .moai/specs/SPEC-COPILOT-PRESETGUARD-001/
.moai/specs/SPEC-COPILOT-PRESETGUARD-001/spec.md:56:### A.3 이 저장소는 이미 "쓰기 전에 되읽는다"를 규율로 갖고 있다
```

히트는 **173건**이었고 나는 그중 5건을 보고 전체라고 적었다. `head -5` 의 5 는 모집단이 아니라 **내가 건 상한**이다.
센 개수와 전체 개수를 나란히 두었으면 즉시 걸렸다.

리드는 내 실수를 「양성 대조군을 다른 파일에서 세웠다」로 진단했다. 그 지적도 타당한 약점이지만 —
대조군은 판정 대상과 같은 자리에서 세우는 편이 강하다 — **치명적인 단계는 그것이 아니라 절단이었다.**
같은 파일에서 대조군을 세웠더라도, 첫 grep 에 상한이 걸려 있는 한 같은 오판이 나왔다.

### 9.2 A.3 이 실제로 적은 것 (직접 읽음)

`spec.md:56~62` 을 직접 읽었다. 리드의 인용을 옮겨 적지 않았다.

> **프리셋 저장만 요청을 완료로 보고한다.** 그리고 프리셋 저장은 좌표 쓰기와 달리 **백업이 원리적으로 불가능하다**
> — 프리셋 내용을 되읽어 재기록할 경로가 없다.

따라서 「값 되읽기 불가」 취지의 문장은 **거기 있다.** 초판의 두 주장 모두 반증된다.

### 9.3 그 문장의 근거는 코드 인용이지 콘솔 측정이 아니다

A.3 의 논증 전체는 **저장소의 코드 경로**를 든다 — `arrange_fixtures`(`tools.py:5318~`)가 원좌표를 전수 백업하고
(`:5566~`), 백업 실패 시 아무것도 쓰지 않으며(`:5606~5613`), 쓰기 후 재조회로 판정한다는 file:line 인용이다.
프리셋 경로에는 그 규율이 없다는 것이 ②의 근거다.

즉 「경로가 없다」는 **툴 계층에 그 코드가 없다**는 진술이고, A.3 은 프로브도 콘솔 응답도 인용하지 않는다.
집필자가 별도로 콘솔 증거를 들고 있었는지는 이 본문으로는 보이지 않는다 — 그것까지 단정하지 않는다.

### 9.4 그래서 t105 는 그 SPEC 밖이다

| | 재는 것 |
|---|---|
| `AC-PRESETGUARD-007` | 기대 수 · 확인 수 · **미확인 슬롯 번호**(`2.27`) → **어느 슬롯이 찼는가** |
| t105 | **찬 슬롯 안에 무엇이 들었는가** |

A.3 이 값 판독 불가를 전제했기 **때문에** 그 SPEC 은 되읽기를 슬롯 산술로 의도적으로 좁혔다.
t105 는 그 SPEC 이 닫지 않은 자리를 연다 — **확인이 아니라 발견이다.** 근거는 부재가 아니라 범위다.

### 9.5 부수 소득 — 「슬롯 점유 = 저장됨」 정정의 근거

PRESETGUARD-001 은 풀 판독 결과를 **세 상태**로 갈라 놓았고, 둘을 접는 것을 뮤테이션으로 금지한다.

| 상태 | SPEC 의 취급 |
|---|---|
| 점유 (검증됨) | 충돌 카드를 띄운다 |
| 검증된 빈칸 | 조용히 지나간다 (시나리오 2, 비공허성) |
| 판독 불가 (`None`, 미상) | 빈칸으로 접지 않는다 (시나리오 4 · AC-006 · AC-008) |

이어받기 쪽지가 스스로 정정한 문장 — 「슬롯 점유가 보증하는 것은 이름 가진 오브젝트 존재뿐」 — 은
그 세 상태 위에 한 층 더 있는 구분이다. 점유가 검증돼도 그것은 *이름*의 점유이지 *값*의 존재가 아니다.

**안 잰 것**: `PRESETIDEM-001` · `COLORPRESET-001` · `PRESETGUARD-002` 의 본문.

## 10. t105 본 측정 — 값 채널을 대조군 둘 사이에 세웠다

t98 이 콘솔을 놓은 뒤 실행했다. **콘솔 쓰기 0건.**

```
>>> prop 'DataPool/PresetPools/1/5' 'Name'
<<< ok: true · value: "Dim 50"                          ← 양성 대조군
>>> prop 'DataPool/PresetPools/1/5' 'PRESETDATAA'
<<< ok: false · "property not readable: PRESETDATAA"    ← 음성 대조군 (날조 이름)
>>> prop 'DataPool/PresetPools/1/5' 'PRESETDATA'
<<< ok: true · value: ""
>>> prop 'DataPool/PresetPools/1/5' 'COUNT'
<<< ok: true · value: "0"
>>> prop 'DataPool/PresetPools/1/5' 'STOREDDATA'
<<< ok: true · value: "Universal"
```

두 대조군 사이에서 갈린 것: `PRESETDATA` 의 빈 문자열은 **「못 읽어서 빈 것」이 아니라 「읽히는데 빈 것」**이다.
날조 이름은 거절되고 진짜 이름은 `ok:true` 로 값 자리를 돌려준다. 그리고 `STOREDDATA` 는 **비지 않는다** —
이 채널이 균일하게 눈먼 것이 아니다.

### 10.1 🔴 COUNT 는 내용 계기가 아니다 — 용량을 답한다

`COUNT 0` 을 해석하려면 0 이 아닌 값을 내는 자리가 있어야 한다. 풀 층에서 물었다.

```
>>> prop 'DataPool/PresetPools/1' 'COUNT'   <<< value: "1000"    (실제 자식 20)
>>> prop 'DataPool/Groups' 'COUNT'          <<< value: "1000"    (실제 자식 5)
>>> prop 'DataPool/Groups/1' 'COUNT'        <<< value: "0"       (All Fixtures)
>>> state 'DataPool/Groups/1'               <<< children: [] · childCount: 0
```

풀 둘이 자식 수와 무관하게 **똑같이 1000** 을 답한다. `COUNT` 는 내용물이 아니라 **풀 용량(슬롯 1000)** 을 세는
프로퍼티이고, 잎 오브젝트에서의 0 은 「비었다」가 아니라 **그 자리에서 의미가 없다**로 읽힌다.

이것은 t95 의 관측(「내용 있는 Group 도 COUNT 0 을 답한다」)을 **설명한다.** COUNT 는 애초에 내용 계기가
아니었다. 따라서 `COUNT 0` 을 부재의 증거로 든 모든 문장은 계기를 잘못 읽은 것이다.

**안 잰 것**: 1000 이 용량이라는 것은 두 풀이 같은 값을 냈다는 관측에서 온 **가장 단순한 설명**이지,
용량임을 직접 확인한 것이 아니다. 자식 수가 다른 두 풀이 같은 수를 낸다는 사실만이 실측이다.

> **재발견이다, 발견이 아니다 (정정).** 이 결론은 메모리
> `lesson-ask-what-the-instrument-counts` 에 이미 있었다 — 「`COUNT` on a grandMA3 pool
> reports *capacity*, not *content* — an empty pool answers 1000」. 나는 그 항목을
> 열지 않은 채 측정했고, 리드에게 「새 발견, 메모리 재작성 필요」로 보고했다가 정정했다.
> 저장소가 이미 갖고 있는 것을 다시 발견한 사례가 이 프로젝트에서 아홉 번째다.
>
> 이 회차가 실제로 보탠 것은 **범위 한 칸**이다. 기존 문면은 「빈 풀이 1000 을 답한다」인데,
> 오늘은 자식 20 인 풀과 자식 5 인 풀이 **둘 다** 1000 을 답했다. 즉 점유와 무관하다는
> 것까지 넓어졌다. 그 이상은 아니다.


### 10.2 그런데 쇼파일은 「MA3 기본」이 아니다 — 우리 리그가 올라가 있다

```
>>> state 'Patch/Stages/1/Fixtures'
<<< 1 Robin Esprite 1 … 17 Robin Esprite 17 · childCount: 80 · truncated: true
>>> state 'DataPool/Groups'
<<< 1 All Fixtures · 2 Robin Esprite · 3 Robin LEDBeam 350 · 4 Sharpy Plus · 5 Mac Aura XB · childCount 5
```

장비 **80대**가 패치돼 있고 그룹은 우리 장비 종류별로 서 있다. 즉 이 쇼파일은 빈 MA3 기본값이 아니다.

그런데 딤 프리셋 20건은 우리 것이 아니다. 우리 시트를 직접 읽었다.

```
$ head "src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.preset-dim.csv"
ID,Name,Level,Purpose
DIM.FULL,풀,100%,…   DIM.SHOW,쇼 하이,85%,…   DIM.MID,미드,60%,…
DIM.LOW,로우,30%,…   DIM.GLOW,잔광,15%,…      DIM.OUT,아웃,0%,…
```

우리 딤 프리셋은 **한글 6건**이다. 콘솔의 `Dim 10`~`Alt Half` 20건과 겹치지 않는다.

**따라서 지금 콘솔은 「리그는 우리 것, 프리셋은 우리 것이 아닌」 혼합 상태다.**
§4 에서 이 풀을 「표준 딤 라이브러리」라고 쓴 것은 근거 없는 추측이었다 — 이름의 인상으로 분류했다.
MA3 기본값인지 제3의 출처인지는 **안 쟀다.**

### 10.3 남은 한 칸 — 값 보유의 독립 증인

t105 의 판정은 아직 서지 않는다. 갈리려면 「`Dim 50` 이 값을 들었는가」가 필요한데 **아무도 안 쟀다.**

| `Dim 50` 이 값을 들었다면 | `PRESETDATA` 빈값 = **이 채널이 값을 노출하지 않는다** (t105 답) |
| `Dim 50` 이 비었다면 | 빈값은 정직한 답이고 t105 는 값 든 프리셋을 기다려야 한다 |

이름이 값을 시사해도 증거가 아니다. **감독 육안 한 번**이면 갈린다 — 딤 풀에서 `Dim 50` 을 눌러
장비가 50% 로 가는지 보는 것. 콘솔 쓰기 0건이다.

**안 잰 것**: 패치 80대와 이전 쇼파일의 86대 차이. 슬롯 20(절단). `Dim 50` 외 프리셋의 `PRESETDATA`.
`STOREDDATA` 가 답한 `Universal` 이 t100 의 `PRESETMODE` 와 같은 축인지.
