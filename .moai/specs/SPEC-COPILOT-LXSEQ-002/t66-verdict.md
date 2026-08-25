# t66 판정 — M4 그룹 쓰기 실패의 원인과 처방

카드 t66. 워크트리 `.claude/worktrees/t66`, 브랜치 `WT-selection-budget`,
기준 `8189971` + t18 `d7ef181` 머지(`69e3408`).

배차서가 준 진단은 「1201바이트가 전송 경계 `[1200, 1208)` 를 1바이트 넘겼다」였다.
**그 진단은 틀렸다.** 아래는 무엇을 쟀고 무엇을 못 쟀는지다.

---

## 1. 주장 (Claim)

1. **M4 그룹 쓰기는 닫혔다.** 콘솔에 그룹 18개가 만들어졌고 18개 전부 슬롯 존재와
   이름이 재조회로 확인됐다.
2. **실패 원인은 미확정이다.** 길이·문법·경로 세 축은 실측으로 소거됐다. 남은
   후보는 콘솔 상태이고, 그중 문서화된 유일 후보는 Patch 목적지다 — **정황이지
   측정이 아니다.**
3. **선택 줄이 dedupe 면제를 못 받고 있었다.** 이것은 실패 원인과 **무관하게**
   존재하던 결함이고, t66 이 닫았다.
4. **요청 방향 바이트 상한은 이 저장소가 처음 쟀고, 1201B 아래에서는 안 걸린다.**

## 2. 증거 (Evidence)

### 2.1 M4 재발사 — 압축 전 원형 그대로

발사 전(읽기 전용 프로브, `lxseq_groups_e2e --probe-only`):

```
날조 대조군 Patch/FixtureTypesZZZNotAThing/9999 → ok=false "path segment not found"
Patch/Stages/1/Fixtures  childCount 86  (children_in_reply 19, truncated true)
DataPool/Groups          childCount 0
channel_trustworthy true · all_pass true
```

발사(`lxseq_groups_e2e --action apply --approve`, 69e3408 의 세 파일을 그대로 둔 상태):

```
배치 0  status created · succeeded true · 슬롯 1~16
배치 1  status created · succeeded true · 슬롯 17~18
verified_steps 18개 전부 slot_exists true · name_verified true
skipped []  ·  slot_divergence None  ·  console_read_incomplete false
```

발사 후(독립 재조회): `DataPool/Groups` childCount **0 → 18**
(children_in_reply 18, truncated false).

그 배치 안에 배차서가 실패로 지목한 줄이 그대로 들어 있다 —
`Fixture 101 + Fixture 102 + … + Fixture 622` (86개, **1201B**) →
`Store Group 1` → `Label Group 1 'ALL'`. **통과했다.**

원본: `.moai/reports/t66-apply-precompression.json` (gitignore 대상 — 이 저장소
밖으로 나가지 않는다).

### 2.2 목적지 판별자 — `server/tools/t66_destination_probe.py`

```
C0  Zzzblah Foo 1          13B  ok=false "Illegal object"   ← 날조 대조군 정상
A   Fixture 101 Thru 106   20B  ok=true  "OK"   ← ChangeDestination 없이 성공
B   ChangeDestination Root 22B  ok=true  "OK"
    Fixture 101 Thru 106   20B  ok=true  "OK"
```

셋 다 게이트 심사 `cleared`. 저장 없음, 픽스처 미접촉.

**1차 발사는 공허했다.** 하네스가 게이트 승인을 안 거치고 `execution_port.execute`
를 직접 불러 6줄 전부 `blocked: command was not cleared by the safety gate` 로
떨어졌는데, 그것을 「A 실패·B 실패 → 목적지 아님」으로 **판정했다.** 콘솔엔
아무것도 안 닿았으니 관측이 아니라 공허였다. 그 판정은 폐기했고, 지금 하네스는
게이트 심사 결과를 판정에 넣어 cleared 아닌 줄이 있으면 「하네스 공허」를 낸다.
위 표는 재작성 후 값이다.

### 2.3 길이 이분 탐색 — `server/tools/t66_length_bisect.py`

```
날조 대조군  Zzzblah Foo 1                    13B  ok=false "Illegal object"
n=1          Fixture 101                      11B  ok=true  "OK"
n=86         Fixture 101 + Fixture 102 + …  1201B  ok=true  "OK"
판정: 상한 없음 — 전체 86개가 통과했다
```

### 2.4 dedupe 면제 (`is_programmer_state`)

```
Fixture 101 + Fixture 102 + Fixture 103          → False   ← t66 까지 내던 줄
Fixture 101 + 102 + 103                          → True    ← 규칙서 :28 검증 문법
Fixture 101 Thru 106 + 111 Thru 118 + 621 + 622  → True    ← 지금 내는 줄
```

### 2.5 압축 실측 (86 FID)

```
반복 키워드형        1201B
키워드 1회(규칙서형)  521B
그 위에 Thru 압축     182B
```

### 2.6 회귀 테스트 뮤테이션 — d7ef181 결함 3건

`server/tests/test_lxseq_group_apply_path.py` (신규, 진짜 `_run_batch` 를 태운다):

| 뮤테이션 | 새 파일 | 기존 `test_lxseq_group_tool.py` |
|---|---|---|
| `fid_read.complete` → `.complete()` | **KILL 4/4** | 16개 전부 통과 (공허) |
| `ToolCall` 의 `id` 인자 제거 | **KILL 3/4** | 16개 전부 통과 (공허) |
| `.content`/`.is_error` → `.status`/`.payload` | **KILL 3/4** | 16개 전부 통과 (공허) |

preview 검사가 안 갈리는 것은 정상이다 — 그 갈래는 `_run_batch` 앞에서 반환한다.
`server/orchestrator/tools.py` 는 뮤테이션 전후 체크섬이 같다
(`8d486f59ab7dc1f54a7981340dd7fa541ec45a348dd53b0efec2b22047b4c9e2`).

### 2.7 날조 대조군 — 압축 후에도 예산을 넘는 입력

`TestFabricatedOversizeControl`. 예산을 **낮추지 않고**(기본 2000) 입력을 키운다:
`KEY` 라벨에 홀수 FID 600개를 더해 압축이 한 자리도 못 접게 만들었다. 결과는
`ALL` 이 `line_over_budget` 으로 **발화 전에** 걸린다. 예산 가드를 `if False:` 로
무력화하면 이 검사를 포함해 3건이 빨개진다(**KILL**).

부산물: 부풀린 `KEY` 자체는 예산 검사에 **도달하지 않는다** — 시트가 적은 개수와
실제 수가 달라 앞단 교차검증이 먼저 문다. 그 순서도 검사에 못박았다.

## 3. 기준 귀속 (Baseline attribution)

- 트리: `.claude/worktrees/t66` @ `WT-selection-budget`
- 기준 커밋: `8189971`(main) + `d7ef181`(t18, 미푸시) → 머지 `69e3408`
- 콘솔: onPC, OSC 송신 8000 / 수신 9005, 응답기 v1.6.1
- 전량 스위트: `make test` → **10138 passed, 12 skipped, exit 0**
- 게이트: `make ci-local` (fmt + lint + test-fast) → **exit 0**

## 4. 미검증 (Gaps)

1. **실패 원인은 확정되지 않았다.** 같은 명령이 그때 실패하고 지금 성공하므로
   차이는 콘솔 상태다. 그 상태가 무엇이었는지는 **안 쟀다.** Patch 목적지는
   문서화된 유일 후보이고 오류 문자열이 글자 그대로 일치하지만
   (`server/rulebook/assets/v2.4.2/31_choreography_patterns.md:9-23`), 재현하려면
   감독이 Patch 에디터를 다시 열어야 한다. 콘솔에 미저장 유일본 86대가 있고
   규칙서가 `ChangeDestination` 은 "either fails outright or moves the destination
   somewhere `AddFixtures` cannot use" 라고 적어 놨으므로 **프로그램으로 재현하지
   않았다.** 리드 합의로 재현 요청도 하지 않았다.

2. **압축형은 실기 미검증이다.** 압축형이 콘솔에서 통과한다는 증거는 없다.
   재발사를 압축 전 형태로 먼저 한 결과 그룹 풀이 18개로 찼고,
   `select_group_slot` 은 점유 슬롯을 무조건 차단하며 `Delete Group` 은
   블랙리스트다 — 이 쇼파일에서는 앞으로도 못 만든다. 압축형은
   **규칙서 `31_choreography_patterns.md:27-28` 이 실기 검증한 문법
   (`Fixture 11 Thru 19`, `Fixture 11 + 12 + 13`)을 조립한 형태이고, 실기
   미검증이다.** 「콘솔에서 통과함」이라고 읽으면 안 된다. 빈 그룹풀 쇼파일이
   생기면 한 번 태워 닫는다 — 카드 t67.

3. **요청 방향 상한은 못 찾았다.** 1201B 까지 통과했을 뿐이고, 상한이 없다는
   증명이 아니다. 이분 탐색이 경계를 못 낸 것도 결과이므로 없는 값을 만들지
   않았다.

4. **멤버십은 되읽히지 않았다.** 18개 그룹의 슬롯 존재와 이름은 재조회로
   확인했지만 **어떤 픽스처가 실제로 들어갔는지는 확인할 수 없다** — 이
   플랫폼이 그 채널을 노출하는지 자체가 미측정이다. 사람이 콘솔에서
   `Group 1` ~ `Group 18` 을 직접 눌러 봐야 한다(`human_check_commands`).

5. **t60(exec 경로에 `_validate_plugin_call_budget` 없음)은 이 카드가 안 닫는다.**
   그 검사기의 기준은 `MAX_PLUGIN_CALL_BYTES = 2048` 이라, 걸려 있었어도 1201B 는
   안 걸렸다. 흡수해도 이 실패를 못 막으므로 **갈랐다.**

## 5. 잔여 위험 (Residual risk)

- 원인을 모르는 채로 닫았다. 같은 실패가 다시 나면 이 문서가 소거한 세 축을
  다시 재는 낭비를 막아 주지만, **어떤 상태가 그것을 일으켰는지는 다음 사람이
  잡아야 한다.** 재현되면 그 순간의 콘솔 목적지를 먼저 적어라.
- 압축형이 실기에서 거절될 가능성은 남는다. 그 경우 그룹은 만들어지지 않고
  fail-fast 로 멈추며(`apply_group_batches` 는 재시도하지 않는다), 점유 슬롯
  차단이 기존 18개를 지킨다 — 파급은 제한적이다.
- `DEFAULT_LINE_BYTE_BUDGET = 2000` 은 **여전히 실측이 아니다.** 프레이밍
  상한에서 역산한 값이고, 상수 옆에 그 사실과 방향·대상·단위를 적어 두었다.
  요청 방향 실측 상한이 생기면 고칠 자리는 그 상수와 그 주석 둘뿐이다.

---

## 배차서 진단에 대한 정정 (기록)

| 배차서가 말한 것 | 실측 |
|---|---|
| 전송 경계 `[1200, 1208)` 를 1B 넘겼다 | 그 경계는 **회신 방향** payload 절단 값이다. `docs/runbooks/fake-real-parity-method.md` §3 의 표는 전부 `payload bytes` 이고, 같은 문서 §4 가 스스로 "이 방법은 쓰기 경로를 못 닫는다"고 적었다. 요청 방향 상한은 안 잰 값이었다 |
| 예산 검사기가 exec 경로에 없어서 잘린 명령이 콘솔까지 갔다 | 가드는 `server/lxseq/group_mapper.py:287` 에 **이미 있었다.** 값이 2000 이라 1201 이 정당히 통과했을 뿐이다. 그리고 같은 파일 주석이 t60 을 이미 알고 5475B 실측까지 적어 두고 있었다 |
| 처방은 범위 압축이다 | 압축은 옳지만 **실패를 고치지 않는다.** 압축이 닫는 것은 dedupe 면제 결함이고, 실패는 압축 없이도 재현되지 않았다 |

숫자에는 **방향·대상·단위**를 함께 적는다. 이번 오진은 잰 숫자를 반대 방향에
갖다 붙여서 생겼고, 그 세 가지가 적혀 있었으면 성립하지 않았다.
