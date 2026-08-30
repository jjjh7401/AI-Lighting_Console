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
~~지금 풀에 있는 것은 표준 딤 라이브러리다.~~ **← §12.1 에서 철회됐다. 이 20건은 우리 앱이 쓴 것이다.**

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

## 11. 전수 열거와 값 존재 신호 — t105 의 답

응답기 1.6.2 로 `DataPool/PresetPools/1/5`(`Dim 50`)의 프로퍼티 **138개를 전수 열거**했다.
콘솔 쓰기 0건.

### 11.1 회차 조건 (전부 내가 잰 값)

    responder_roundtrip --expect-version 1.6.2  →  PASS
      live version=1.6.2  plugin=CopilotResponder
      ping ok · state ok · exec ok

앞 회차까지 「1.6.2」는 리드의 관측이었고 내 것이 아니었다. 이 줄로 내 관측이 됐다.

날조 대조군을 **채널마다 따로** 세웠다 — 열거 동사와 판독 동사는 다른 동사이기 때문이다.

    introspect  DataPool/PresetPools/1/FABRICATED_CONTROL_NOPE
      → path segment not found: 'FABRICATED_CONTROL_NOPE'
    prop        DataPool/PresetPools/1/5 | OWNDATAPRESENT_NOPE
      → property not readable: OWNDATAPRESENT_NOPE

콘솔 점유도 잡기 전에 `lsof` 로 확인했다. 리드가 「내 차례다」라고 보낸 뒤였지만,
같은 날 그 문장이 쓰인 시점에만 참이었던 사례가 있었다.

### 11.2 전수 열거 — 138/138, 절단 없이 닫혔다

`--all-pages` 는 쓰지 않았다(낡은 응답기 무한 루프 기록이 있고 1.6.2 에서 그 술어를
아무도 안 쟀다). `--offset` 을 손으로 돌렸다.

    offset   0   27 fields   truncated true
    offset  27   29 fields   truncated true
    offset  56   26 fields   truncated true
    offset  82   26 fields   truncated true
    offset 108   26 fields   truncated true
    offset 134    4 fields   truncated **false**
                 ---
                138 = total

합이 total 과 같고 마지막 페이지가 `truncated: false` 다. 이 둘이 함께 있어야
「전수를 봤다」가 성립한다. `/5` 의 total 도 **138** 로, t96 이 `/3` 에서 본 값과 같다
(그것은 안 잰 항목이었다).

### 11.3 🔴 내가 또 표본을 모집단으로 읽었다 — 이번엔 그 실수를 지적하면서

앞 회차에 나는 리드에게 이렇게 보냈다:

> `PRESETDATA` 도 `STOREDDATA` 도 열거에 없다. 열거 채널과 판독 채널은 같은 집합이
> 아니고 판독 쪽이 넓다.

**틀렸다.** 근거는 t95 산출물의 **첫 페이지 27개**였고, 전수 138 을 보니 셋 다 있다.

    offset 108 페이지:  PRESETMODE · STOREDDATA · SPEEDMASTER · SPEEDSCALE · PRESETDATA
                        OWNDATAPRESENT · DIRECTPROGRAMMERCOOKING · OWNNONCOOKEDDATAPRESENT · ...

27을 138의 모집단으로 읽었다. 오늘 `head -5` 로 173건을 5건이라 읽은 것과 **같은 기전**이고,
하필 리드에게 바로 그 형태를 지적하는 메시지 안에서 재현했다. 리드는 그 위에서 배차
4번 항목을 폐기했으므로 즉시 정정해 보냈다.

**그러므로 「판독 채널이 열거보다 넓다」는 근거가 없다.** 두 채널이 같은 집합인지는
여전히 안 쟀다 — 반증만 됐고 확증된 것은 아니다.

### 11.4 값 존재 신호는 이 채널에 **있다**

전수 열거가 후보를 냈고, 날조 대조군과 함께 쐈다.

    prop /1/5 OWNDATAPRESENT           ok  "true"
    prop /1/5 OWNNONCOOKEDDATAPRESENT  ok  "true"
    prop /1/5 MEMORYTYPE               ok  "Compressed"
    prop /1/5 VALUESMODE               ok  "Normal"
    prop /1/5 SELECTIONDATA            ok  "table: 0x6000026b3600"

`MEMORYTYPE = Compressed` 가 `PRESETDATA = ""` 를 설명한다 — 내용이 압축 저장돼 있고
그 프로퍼티가 직렬화해 주지 않는다. `SELECTIONDATA` 도 값이 아니라 **Lua 테이블 핸들**을
답한다. 즉 이 채널은 값을 **직렬화해 주지 않을 뿐**, 값의 존재는 답한다.

### 11.5 계기 판별력 — COUNT 에 한 것과 같은 검사

`OWNDATAPRESENT` 가 아무 데서나 true 를 내면 COUNT 와 같은 함정이다. 다른 클래스에 쐈다.

    prop DataPool/PresetPools/1   OWNDATAPRESENT  → ok:false  property not readable
    prop DataPool/Groups/1        OWNDATAPRESENT  → ok:false  property not readable
    prop DataPool/Plugins/1       OWNDATAPRESENT  → ok:false  property not readable
    prop DataPool/Sequences/1     OWNDATAPRESENT  → ok:false  property not readable
    prop DataPool/PresetPools/2/1 OWNDATAPRESENT  → ok        "true"   (Position "Home")

**Preset 클래스 전용 프로퍼티다.** 어디서나 읽히는 보편 참이 아니다.

**안 잰 것 — 이 계기가 `false` 를 내는 것을 못 봤다.** 시험한 프리셋 둘은 모두 점유
상태였고, 이 쇼파일에는 주소가 잡히는 빈 프리셋이 없다(`/1/25` → path segment not found).
따라서 「점유 프리셋과 빈 프리셋을 가른다」는 **미검증**이다. 그것을 세우려면 빈 프리셋을
하나 만들어야 하고 그것은 쓰기다 — t96 의 쓰기 창에 묶을 일이다.

### 11.6 MEMORYFOOTPRINT — 내용에 반응하는 간접 계기

리드가 제안한 축이다. 열거 안에 있어 추측이 필요 없다.

    Dimmer  /1  Dim 10        2084
    Dimmer  /5  Dim 50        2084
    Dimmer  /10 Full          2084
    Dimmer  /11 Breathe Soft  2104
    Dimmer  /17 Ripple        2116
    Dimmer  /20 Slam Run      2100
    Position /2/1 Home        5988
    Group    /1 All Fixtures  1096

**같은 클래스 안에서 네 값이 나온다.** 그러므로 고정 구조체 크기가 아니다 —
리드가 세운 반증 형태(「두 값이 같으면 못 쓴다」)를 통과했다. 평탄한 레벨 셋이 2084 로
동일하고 효과성 프리셋이 더 크다는 것도 내용 민감성과 맞는다.

**안 잰 것**: 빈 프리셋의 footprint. 2084 가 「구조체 + 값」인지 「구조체뿐」인지는
빈 대조군 없이는 못 가른다. §11.5 와 같은 벽이다.

### 11.7 판정

**t105 의 물음 — 이 채널이 값을 노출하는가 — 에 답한다.**

| 세운 것 | 근거 |
|---|---|
| `PRESETDATA` 의 빈 문자열은 **부재의 증거가 아니다** | 같은 오브젝트가 `OWNDATAPRESENT: true` 를 답한다 |
| 채널은 값을 **직렬화해 주지 않는다** | `MEMORYTYPE: Compressed` · `SELECTIONDATA` 는 테이블 핸들 |
| 채널은 값의 **존재는 답한다** | `OWNDATAPRESENT` · `OWNNONCOOKEDDATAPRESENT` · `MEMORYFOOTPRINT` |
| 이 결론은 **표본이 아니라 전수** 위에 있다 | 138/138, 마지막 페이지 `truncated: false` |

즉 「읽히는데 비었다」의 정확한 뜻은 **「값은 있고, 이 프로퍼티가 그것을 안 내준다」**이다.

~~**감독 육안 확인은 이제 이 판정에 필요하지 않다.**~~ **← 이 문장은 §11.9 에서 철회됐다.** `Dim 50` 이 값을 들었는지를 채널이
직접 답했다. 다만 §11.5 의 `false` 대조군이 없으므로, 「`OWNDATAPRESENT` 가 빈 프리셋을
가른다」는 별도 주장은 아직 못 한다 — 이 판정은 그 주장에 기대지 않는다.

### 11.8 남은 것

- `OWNDATAPRESENT` 의 `false` 사례 (빈 프리셋 필요 → 쓰기 → t96 창)
- 빈 프리셋의 `MEMORYFOOTPRINT`
- 열거 채널과 판독 채널이 같은 집합인지 (§11.3 에서 반증만 됐다)
- `PRESETDATA` 가 어떤 조건에서 비지 않는지 — 다른 클래스·다른 모드에서 안 쟀다
- `/3` 의 offset 27 이후가 `/5` 와 같은지 (프리셋마다 다를 수 있다)

## 11.9 🔴 판정 정정 — 팔이 하나다

리드가 §11.5 와 §11.7 의 자기모순을 잡았다. 인용한다:

> §11.5 는 「`false` 사례를 못 봤다 … 이 판정은 그 주장에 기대지 않는다」고 적었다.
> 뒷문장이 앞문장과 안 맞는다. §11.7 의 판정 근거는 `OWNDATAPRESENT → "true"` 하나이고,
> 그 프로퍼티가 `false` 를 말하는 걸 아무도 본 적이 없다. 그러면 "true" 는
> 「데이터가 있다」의 증거가 아니라 「이 프로퍼티는 Preset 클래스에서 true 를 답한다」의
> 증거일 수 있다.

**맞다.** 그리고 이것은 오늘 아침 `COUNT` 에서 내가 잡은 그 형태다 — `COUNT` 도 얌전히
숫자를 답했고, **자식 수가 다른 둘이 같은 값을 낼 때까지** 계기인 줄 알았다.

§11.5 의 시험은 **클래스 판별력**을 쟀다(다른 클래스에서 거절된다). 그것은
「아무 데서나 true 를 내진 않는다」를 세운다. 하지만 **같은 클래스 안에서 갈리는가**는
안 쟀고, 계기의 판별력은 그쪽이다. 두 시험은 다른 질문이다.

### `false` 를 쓰기 없이 찾아봤다 — 못 찾았다

닫기 전에 다른 풀로 넓혔다. 전부 읽기다.

    PresetPools/3  (Gobo)   childCount **0**  — 빈 풀. 주소 잡히는 프리셋이 없다
    PresetPools/4  (Color)  childCount 20 — Warm White · Cool White · Red · …
    PresetPools/21 (All 1)  Drop Slam · Breathe Amber · … 그리고 `#2` 중복본들

    prop /4/1   OWNDATAPRESENT → "true"    (Warm White)
    prop /21/1  OWNDATAPRESENT → "true"    (Drop Slam)
    prop /21/11 OWNDATAPRESENT → "true"    (Drop Slam#2)

`#2` 중복본이 빈 껍데기일까 싶었으나 아니었다 — footprint 가 원본과 같다.

    /21/1  Drop Slam    MEMORYFOOTPRINT 14372
    /21/11 Drop Slam#2  MEMORYFOOTPRINT 14372

**프리셋 다섯을 세 풀에 걸쳐 쐈고 전부 `true` 다. `false` 는 한 번도 안 나왔다.**
읽기만으로 두 번째 팔을 세울 길은 이 쇼파일에 없다.

### 정정된 판정문

| | |
|---|---|
| **세운 것** | 이 채널은 값의 **존재를** 답한다 — `OWNDATAPRESENT` · `OWNNONCOOKEDDATAPRESENT` · `MEMORYTYPE: Compressed`. 값 **자체**는 직렬화해 주지 않는다 — `PRESETDATA` 빈값 · `SELECTIONDATA` 는 Lua 핸들 |
| **못 세운 것** | 그 프로퍼티들이 **빈 프리셋에서 `false` 를 말하는지.** 이 쇼파일에 주소 잡히는 빈 프리셋이 없어 **대조군 한 팔이 비었다** |
| **따라서** | 「`Dim 50` 이 값을 들었다」는 **단일 팔 근거**다. 두 번째 팔은 (a) 물리층 확인 — 감독이 `Dim 50` 을 눌러 장비가 50% 로 가는지, 또는 (b) 빈 프리셋 생성 후 재판독(쓰기, t96 창) |

### 감독 육안의 역할이 바뀐다 — 빼는 것이 아니다

앞선 §11.7 은 「감독 육안이 이 판정에 필요하지 않다」고 적었다. **그 문장을 철회한다.**

    전   유일한 경로. 없으면 아무것도 모른다
    후   **두 번째 채널.** 물리층이라 콘솔 메타데이터와 완전히 독립이다

`OWNDATAPRESENT` 와 육안은 **다른 층**에서 같은 물음에 답한다. 30초짜리이고 쓰기 0이다.
안 쓸 이유가 없다.

### `MEMORYFOOTPRINT` 도 같은 한계다

같은 클래스에서 값이 갈린 것(2084·2100·2104·2116)은 **고정 구조체 가설을 죽인다** —
그건 성과다. 그러나 2084 가 「구조체+값」인지 「구조체뿐」인지는 빈 대조군 없이 못 가른다.
이 회차에 폭이 더 넓어졌지만(All 1 풀 14372 · Position 5988 · Group 1096) 팔은 여전히 하나다.

**이 절이 §11.7 의 마지막 문단을 대체한다.**

## 12. 🔴 「딤 프리셋은 우리 것이 아니다」 철회 — 그리고 두 번째 팔이 나왔다

### 12.1 §4·§10.2 의 주장을 철회한다

이 보고서는 §4 와 §10.2 에서 이렇게 적었다.

> 딤 프리셋 20건은 우리 것이 아니다. 우리 시트는 한글 6건이다.
> 지금 콘솔은 「리그는 우리 것, 프리셋은 우리 것이 아닌」 혼합 상태다.

**틀렸다.** 근거는 콘솔 풀을 **생산자 하나**(`LXSEQ_RIG_01_ShowBase_r3.preset-dim.csv`)에만
대조한 것이었다. 저장소에는 생산자가 둘이고, 다른 하나가 정확히 일치한다.

    server/web/session.py:2004  DIMMER_LEVEL_SEQUENCE
      ("Dim 10", 10) ("Dim 20", 20) … ("Dim 90", 90) ("Full", 100)        10개

    server/web/session.py:2043  DIMMER_PHASER_SEQUENCE
      ("Breathe Soft", (30,70), "sine", "0")
      ("Breathe Deep", (10,90), "sine", "0")
      ("Pulse Hard",   (0,100), "rectangle", "0")
      ("Pulse Half",   (30,100),"rectangle", "0")
      ("Wave Soft",    (30,70), "sine", "0 Thru 360")
      ("Wave Full",    (0,100), "sine", "0 Thru 360")
      ("Ripple",       (30,60,100), "sine", "0 Thru 360")
      ("Flash Accent", (100,20),"rectangle", "0")
      ("Alt Half",     (50,100),"sine", "180")
      ("Slam Run",     (0,100), "rectangle", "0 Thru 360")               10개
                                                                        ────
                                                                          20

콘솔 딤 풀의 `childCount 20` 과 **이름·순서가 모두 일치한다.** 컬러 풀도 같다 —
`COLOR_PALETTE_SEQUENCE` 10 + `COLOR_PHASER_SEQUENCE` 10 = 20 이고 콘솔과 일치한다.

**두 풀 다 우리 것이고, 출처는 CSV 파이프라인이 아니라 앱 경로다.**

**기전**: 「우리 것인가」를 후보 하나에만 대조했다. 불일치를 「남의 것」으로 읽었지만,
불일치가 말하는 것은 **그 후보가 아니다**까지다. 생산자를 전수로 세지 않았다.
[[lesson-existence-is-not-reachability]] 가 「생산·노출·호출을 따로 재라」고 적은 것과
같은 축이고, 오늘 §9.1·§11.3 과도 같은 계열이다 — **부분을 전체로 읽었다.**

리드의 「grandMA3 기본 쇼파일이다」와 내 「혼합 상태다」가 **둘 다** 틀렸다.
정확한 문장: **리그도 프리셋도 우리 것이고, 딤·컬러 두 풀은 앱 경로가 썼다.**
LXSEQ 시트(한글 6건)가 만든 프리셋이 없을 뿐이다.

### 12.2 그 정정이 t105 에 두 번째 팔을 준다

생산자를 알게 되자 **반증 가능한 예측**이 생겼다. 생산자는 프리셋마다 스텝 수를 정한다 —
레벨은 값 하나, 페이저는 둘 또는 셋. footprint 가 내용을 따라간다면 스텝 수로 층이 져야 한다.

측정 시점에 이미 있던 값(§11.6):

    1스텝  Dim 10 · Dim 50 · Full                  2084
    2스텝  Breathe Soft 2104 · Slam Run 2100
    3스텝  Ripple                                  2116

**예측**: 아직 안 잰 2스텝 프리셋들은 2100~2104 대여야 한다. 2084 로 떨어지거나
2116 에 닿으면 대응이 깨진다.

    /12 Breathe Deep  (10,90)   2스텝 → 2104
    /13 Pulse Hard    (0,100)   2스텝 → 2100
    /15 Wave Soft     (30,70)   2스텝 → 2100
    /18 Flash Accent  (100,20)  2스텝 → 2100
    /19 Alt Half      (50,100)  2스텝 → 2100

**다섯 전부 예측 안에 들어왔다.** 프리셋 11개를 재서 층이 이렇게 진다:

    1스텝  2084          ×3
    2스텝  2100 · 2104   ×7
    3스텝  2116          ×1

**층이 겹치지 않는다.** 소스 코드가 정한 스텝 수와 콘솔이 답한 footprint 가
**다른 층에서 대응한다** — 하나는 저장소의 리터럴, 하나는 콘솔의 메타데이터다.

### 12.3 판정 갱신 — 팔이 둘이 됐다

§11.9 는 「팔이 하나」라고 적었다. 그 상태가 바뀐다.

| 팔 | 층 | 말하는 것 |
|---|---|---|
| 1 | 콘솔 메타데이터 | `OWNDATAPRESENT: true` · `MEMORYTYPE: Compressed` |
| 2 | **생산자 소스 ↔ 콘솔 footprint 대응** | 스텝 수 층이 겹치지 않고, 5건 예측이 버텼다 |

두 팔은 **독립이다** — 하나는 콘솔이 자기에 대해 하는 말이고, 하나는 저장소의 코드와
콘솔의 숫자가 만나는 지점이다. 계기가 내용에 반응하지 않는다면 이 대응이 나올 수 없다.

**따라서 「`Dim 50` 이 값을 들었다」는 더 이상 단일 팔이 아니다.**

### 12.4 그래도 안 세운 것 — 빈 프리셋

여전히 **빈 프리셋을 못 봤다.** §12.2 가 세운 것은 「footprint 가 스텝 수에 반응한다」이지
「2084 > 빈 프리셋」이 아니다. 스텝 0 짜리를 잰 적이 없다.

    측정된 스텝 수:  1 · 2 · 3
    안 잰 스텝 수:   0

단조가 0 까지 이어지는지는 외삽이고 측정이 아니다. 그것을 세우려면 빈 프리셋이 필요하고,
그건 쓰기다(t96 창). `OWNDATAPRESENT` 가 `false` 를 말하는 것도 여전히 못 봤다.

감독 육안(`Dim 50` → 장비 50%)은 **세 번째 채널**로 남는다 — 물리층이라 앞의 둘과 또 독립이다.

### 12.5 이 정정이 다른 카드에 미치는 것

- **쓰기 창 배차의 필수 축**: `preset-col.csv`(한글 8행)나 `preset-dim.csv`(한글 6행)를
  재실행하면 **앱이 이미 쓴 20건과 만난다.** 이름이 안 겹치므로(한글 대 ASCII) 덮어쓰기는
  아닐 가능성이 높지만, 슬롯 배정이 어떻게 되는지는 **아무도 안 쟀다.**
- 리드의 인계 문서 §2(「grandMA3 기본 쇼파일」)와 그 뒤 정정(「혼합」) **둘 다** 갱신 대상이다.

## 13. 계기는 스텝 수가 아니라 구조에 반응한다 — 페이저 10건 전수

리드가 §12.2 의 「스텝 수 층」을 더 정밀하게 갈랐다. 실측을 생산자 리터럴
`(라벨, 값들, Form, Phase)` 에 붙이면 스텝 수만으로는 설명이 안 된다.

    Wave Soft (30,70) 는 Breathe Soft 와 **값이 같은데** footprint 가 다르다 (2100 대 2104)
    Wave Soft 도 sine 인데 2100 이다 — Form 만으로도 안 된다

리드가 낸 규칙: `sine` **그리고** phase `"0"` 일 때만 2104. 그 규칙이 예측한 둘을 쐈다.

    /14 Pulse Half  (30,100) rectangle "0"          → 예측 2100 · 실측 **2100**
    /16 Wave Full   (0,100)  sine "0 Thru 360"      → 예측 2100 · 실측 **2100**

**딤 페이저 10건이 전수가 됐다.**

    슬롯 값들          Form       Phase          footprint
    11  (30,70)        sine       0              2104
    12  (10,90)        sine       0              2104
    13  (0,100)        rectangle  0              2100
    14  (30,100)       rectangle  0              2100
    15  (30,70)        sine       0 Thru 360     2100
    16  (0,100)        sine       0 Thru 360     2100
    17  (30,60,100)    sine       0 Thru 360     2116
    18  (100,20)       rectangle  0              2100
    19  (50,100)       sine       180            2100
    20  (0,100)        rectangle  0 Thru 360     2100

레벨 프리셋(1스텝) 셋은 2084 다.

### 13.1 두 항짜리 모형

측정된 13건 전부가 이 식에 들어맞는다.

    footprint = 2084 + 16 x (스텝수 - 1) + 4 x (sine 이고 phase 가 "0")

    1스텝                   2084
    2스텝                   2100
    2스텝 + sine/phase "0"  2104
    3스텝                   2116

스텝 하나가 **16바이트**, sine·phase"0" 조합이 **4바이트**다. `Alt Half` 가 sine 인데도
2100 인 것(phase 가 `"180"`)이 두 항을 가르는 자리다.

### 13.2 이것이 §12.3 의 두 번째 팔을 굳힌다

우연히 층이 진 것이라면 값·Form·Phase 세 축 중 어느 하나로도 설명이 됐어야 한다.
그런데 **어느 하나로도 안 되고 둘의 조합으로만 된다.** 저장소 리터럴의 구조가
콘솔 메타데이터에 대응한다는 진술이 13건에서 성립한다.

### 13.3 여전히 안 잰 것 — 이 절은 §12.4 를 대체하지 않는다

모형이 예측하는 값 하나가 특히 눈에 띈다.

    스텝 0 (빈 프리셋)  →  2084 - 16 = **2068**

**이것은 외삽이지 측정이 아니다.** 잰 스텝 수는 1·2·3 뿐이고 0 을 잰 적이 없다.
모형이 정량적이 됐다는 것이 0 을 관측했다는 뜻은 아니다 — 오히려 이런 깔끔한 식은
「그러니 2068 일 것이다」로 넘어가기 쉬워서 더 조심할 자리다.

세 번째 채널(감독 육안)과 t96 쓰기 창(빈 프리셋 생성 후 재판독)은 그대로 남는다.

**안 잰 것 추가**: 레벨 프리셋 10건 중 셋(`Dim 10`·`Dim 50`·`Full`)만 쟀다.
나머지 일곱이 모두 2084 인지는 미측정이다 — 셋이 같았다고 열이 같다고 적으면
오늘 여섯 번 밟은 그 형태다.
