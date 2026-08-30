# t96 재측정 — 응답기는 1.6.1 이고, 잰 범위에서 재배포는 일어난 적이 없다

날짜: 2026-08-30 · 트리 `.claude/worktrees/t96` · 브랜치 `WT-responder-pool-aliases` · HEAD `2631313`
콘솔: grandMA3 onPC `app_gma3` **pid 38706** (UDP 8000·9005) · 송신 `127.0.0.1:8000` / 수신 `9005`
**콘솔 쓰기 0줄** — 전부 state / introspect / ping 판독이다. PR 없음.

## 1. 주장 (Claim)

1. 실기 응답기는 **여전히 1.6.1** 이다. 버전 문자열과 동작, **두 채널이 독립으로** 그렇게 답한다.
2. 🔴 **카드 전제가 만료됐다.** 카드는 "재임포트 후"를 전제했지만, 배포 파일 mtime 이
   2026-08-26 16:33 에서 움직이지 않았다 — 잰 범위에서 **재배포가 일어난 적이 없다.**
3. 🔴 **로드된 쇼파일이 이전 회차의 그것이 아니다.** 기준선이 있는 풀 셋이 전부 어긋난다.
   플러그인은 .show 안에 저장되므로, 이 쇼의 응답기가 1.6.1 인 것이다.
4. 이전 회차의 진단(사본 셋 → 별칭 정리)은 **지금 로드된 쇼에는 적용되지 않는다.**
   사본은 없다. 응답기 슬롯은 하나뿐이다.

## 2. 증거 (Evidence)

### 2.0 계기 신뢰성 — 도구마다 날조 대조군을 따로 쐈다

두 도구를 썼으므로 대조군도 둘이다. 한쪽 대조군으로 다른 도구의 ok 를 보증할 수 없다.

    python -m server.tools.introspect_probe --path 'DataPool/ZZZNoSuchPoolXYZ' --listen-port 9005
    -> introspect failed: path segment not found: 'ZZZNoSuchPoolXYZ' (in DataPool/ZZZNoSuchPoolXYZ)   [exit 1]

    python -m server.tools.t95_state_dump   --path 'DataPool/ZZZNoSuchPoolXYZ' --listen-port 9005
    -> state failed: path segment not found: 'ZZZNoSuchPoolXYZ' (in DataPool/ZZZNoSuchPoolXYZ)        [exit 1]

둘 다 아무 경로에나 ok 를 주지 않는다. 따라서 아래 판독은 증거다.

### 2.1 버전 — 축 두 개가 따로 1.6.1 이라고 답한다

    python -m server.tools.responder_roundtrip --listen-port 9005 --skip-exec --expect-version 1.6.2
    -> [FAIL] ping: live responder version '1.6.1' != expected '1.6.2'
             live version=1.6.1 plugin=CopilotResponder
    -> [PASS] state: ok   (Sequences · childCount 1 · children 1)
    -> result: FAIL                                                                        [exit 1]

이 출력은 이전 회차의 live-version-after-restart.txt 와 **글자 단위로 동일**하다.

동작 축(문자열이 아니라 파서를 잰다):

    python -m server.tools.introspect_probe --path 'DataPool/PresetPools/1/3' --offset 27 --listen-port 9005
    -> introspect failed: path segment not found: '3 offset=27' (in DataPool/PresetPools/1/3 offset=27)  [exit 1]

오프셋 토큰이 경로에 삼켜진다 = 1.6.2 파서 부재. 버전 문자열이 거짓말을 해도 이 축은 안 속는다.

### 2.2 배포 소스는 1.6.2 이고, 나흘째 그대로다

    ls -la ~/MALightingTechnology/gma3_library/datapools/plugins/
    -> -rw-r--r--  49078  Aug 26 16:33  copilot_responder.lua
    -> -rw-r--r--  47240  Aug 26 16:33  copilot_responder.lua.bak-20260826-163328
    -> -rw-r--r--    607  Aug 26 16:33  copilot_responder.xml
    (디렉터리 자체 mtime: Aug 26 16:38)

    grep -n 'VERSION = ' ~/MALightingTechnology/.../copilot_responder.lua
    -> 76:    VERSION = "1.6.2",

    shasum -a 256 <배포본> <이 트리 console/lua/copilot_responder.lua>
    -> 8c5b5defb2065cdc447ea9a711657308dd0dc01a6b2ef3a2a46b0c1491100b29  (배포본)
    -> 8c5b5defb2065cdc447ea9a711657308dd0dc01a6b2ef3a2a46b0c1491100b29  (이 트리)

바이트가 같다. 배포 소스는 옳고, **2026-08-26 16:33 이후 아무도 다시 쓰지 않았다.** 오늘은 08-30 이다.

### 2.3 로드된 쇼파일이 다르다 — 기준선 있는 풀 셋이 전부 어긋난다

    python -m server.tools.t95_state_dump --path '<경로>' --listen-port 9005

| 경로 | 이전 회차 (2026-08-26, survey.md) | 지금 (2026-08-30) |
|---|---|---|
| `DataPool/Plugins` | childCount **11** · 응답기 사본 셋 (슬롯 1·10·11) | childCount **5** · 응답기 **하나** (슬롯 1) |
| `DataPool/Groups` | childCount **18** (t66 이 올림) | childCount **5** — All Fixtures / Robin Esprite / Robin LEDBeam 350 / Sharpy Plus / Mac Aura XB |
| `DataPool/PresetPools/1` (Dimmer) | pool_after **6** | childCount **20** (truncated true) — Dim 10…Dim 90, Full, Breathe Soft … Alt Half |

`Plugins` 는 이전에도 지금도 truncated false 다 — 절단이 아니라 실제 개수다.

🔴 **산수가 사본 정리 가설을 반증한다.** 사본 둘만 지웠다면 11-2=**9** 여야 한다. 5다.
6개가 더 사라졌고, Groups 와 프리셋 풀의 내용까지 통째로 다르다. 슬롯 2~5 는
CopilotPatch* 플러그인이라 순정 기본 쇼도 아니다 — **또 다른 쇼**다.

지금 풀에 `CopilotResponder#2` / `CopilotResponder_2` 는 없다. 따라서 이전 회차가
추론으로 남겼던 "사본이 ping 을 침묵시킨다"는 **이 회차의 1.6.1 응답을 설명하지 않는다.**
교란 요인이 없는 상태에서 유일한 슬롯이 1.6.1 을 답한다.

## 3. 기준선 귀속 (Baseline-attribution)

- 트리 `.claude/worktrees/t96` · `git branch --show-current` -> `WT-responder-pool-aliases`
- `git rev-parse --short HEAD` -> `2631313` · `git status --short` -> 비어 있음
- `git fetch origin main` 후 `git rev-list --count --left-right origin/main...HEAD` -> `7` `2`
  (main 이 7 앞섬. 읽기 전용 회차라 막지 않았으나 후속 쓰기 전엔 정합 필요)
- 자체 venv (`.venv/bin/python`). 주 체크아웃 venv 를 빌리지 않았다
- 대조 기준선: `.moai/reports/t96/survey.md` (2026-08-26) · `.moai/reports/t96/pool-aliases.md`
- 콘솔 프로세스: `lsof -nP -iUDP:8000 -iUDP:9005` -> `app_gma3` pid **38706**
  (이전 회차는 pid 78611 — 그 사이 재기동이 있었다)

## 4. 미검증 (Gaps) — 안 잰 것

| 안 잰 축 | 왜 / 무엇이 필요한가 |
|---|---|
| **임포트가 시도됐는지** | mtime 은 파일이 쓰인 시각이지 콘솔이 임포트한 시각이 아니다. 파일을 안 건드리고 GUI 에서 Import Plugin 만 눌렀다면 mtime 은 그대로다. "재배포가 없었다"까지가 정확하고 "임포트 시도가 없었다"는 **미검증**이다 |
| **로드된 쇼파일의 이름·경로** | 이 응답기 채널에 쇼 이름을 묻는 동사가 없다. "이전 회차의 쇼가 아니다"까지만 실측이고, 어느 쇼인지는 모른다 |
| **왜 쇼가 바뀌었나** | 누가/언제 바꿨는지 모른다. 관측은 풀 내용 차이뿐이다 |
| **이전 쇼의 사본 셋이 어떻게 됐나** | 지금 쇼에 없다는 것만 안다. 지워졌는지, 다른 쇼에 그대로 있는지 모른다 |
| t96 (2) 이름 길이 상한 | 긴 이름 저장 = 콘솔 쓰기. 범위 밖 |
| t105 PRESETDATA 재판독 | 1.6.1 이라 페이징이 없다 |
| dim 프리셋의 **값** | 이 쇼의 20건은 이름만 봤다. 값은 이 채널로 안 읽힌다 |

## 5. 잔여 위험 (Residual-risk)

- 🔴 **이전 회차의 처방(별칭 정리)을 그대로 실행하면 안 된다.** 그 처방은 사본 셋이 있는
  쇼를 대상으로 쓰였고, 지금 로드된 쇼에는 사본이 없다. 없는 것을 지우려 들면 유일한
  응답기 슬롯을 건드리게 된다 — 되돌릴 수 없다.
- **쇼가 또 바뀔 수 있다.** 이 회차의 모든 풀 판독은 "지금 로드된 쇼"에 귀속된다.
  쇼가 바뀌면 이 숫자들은 전부 노화한다. 후속 회차는 풀 개수를 먼저 재서 동일 쇼인지
  확인한 뒤 진행해야 한다.
- **1.6.2 를 물려도 111개 열거가 열릴 뿐, 값 판독이 열린다는 보장은 없다**
  (t95 2.4: 열거 목록은 판독 가능성의 목록이 아니다). 이 회차가 그걸 바꾸지 않았다.
- 이 회차는 **콘솔 쓰기 0줄**이라 되돌릴 것이 없다.

## 6. 함정 기록 (다음 회차용)

- **9005 를 묶는 프로브를 병렬로 돌리지 마라.** 두 개를 한 턴에 띄웠더니 Errno 48
  Address already in use 가 났고, 끝난 프로세스의 소켓이 잠깐 남아 다음 호출까지 막았다.
  하나씩 직렬로.
- **워크트리 가드가 PIPESTATUS 확장에 걸린다.** 확장 구문 없는 단순 명령으로.
- **Write 도구가 이 트리 전체를 거부한다** (워크트리가 .claude/ 아래). Bash 로 쓴다.
- 🔴 **`git check-ignore` 를 추적 중인 파일에 쏘면 무시 규칙이 아니라 추적 여부를 잰다.**
  이 회차에서 실제로 틀렸다. `.moai/reports/t96/survey.md`(추적됨)에 쏘니 exit 1 이 나와
  "무시 규칙 없음"으로 읽었지만, 새로 만든 파일에 쏘니 `.gitignore:247:.moai/reports/` 가
  나왔다. **디렉터리는 무시된다.** 인계문의 "gitignore 라 이 트리에만 있다"가 맞고 내가 틀렸다.
  무시 여부는 **추적된 적 없는 경로**로 재라. 이전 회차들이 증거를 커밋할 수 있었던 건
  `git add -f` 로 강제 추가했기 때문이다 — 이 회차도 같은 방식으로 넣는다.

---

## 7. 붙여넣기 이후 (같은 날, 감독 Option B 완료 후)

감독이 처음엔 Option A(Import)로 갔고 인수가 FAIL 했다 — 파일은 1.6.2 인데 실기는
1.6.1. README §2.1 이 적어 둔 그 함정이다. Option B(Lua 편집기 전체 붙여넣기) 후 PASS.

**두 채널이 실패와 성공 양쪽에서 다 작동했다.** 아침엔 둘 다 1.6.1 을, 지금은 둘 다
1.6.2 를 답한다. 문자열 하나였으면 「그 필드만 안 갱신됐나」로 흔들렸을 자리다.

### 7.1 인수 — 두 채널 + 대조군 (리드와 독립으로 각자 측정, 일치)

    responder_roundtrip --skip-exec --expect-version 1.6.2
    -> [PASS] ping: ok · live version=1.6.2 plugin=CopilotResponder
    -> [PASS] state: ok
    -> result: PASS

    introspect_probe --path 'DataPool/ZZZNoSuchPoolXYZ' --listen-port 9005     (대조군)
    -> introspect failed: path segment not found: 'ZZZNoSuchPoolXYZ'   [exit 1]

    introspect_probe --path 'DataPool/PresetPools/1/3' --offset 27             (아침과 동일 명령)
    -> ok:true · "offset": 27 · "path": "DataPool/PresetPools/1/3" · total 138 · truncated true

경로를 안 바꾸고 **아침에 실패했던 그 명령 그대로** 쐈다 — 전후 비교가 같은 입력 위에 선다.

| 항목 | 아침 (1.6.1) | 붙여넣기 후 (1.6.2) |
|---|---|---|
| `offset` | 경로에 삼켜짐 (`'3 offset=27'`) | `"offset": 27` 로 파싱 |
| `path` | 오염 | 깨끗 |
| 도달 가능 프로퍼티 | 27 | **total 138** |

아침 §4 에 「안 잰 것」으로 적었던 **프로퍼티 111개**(138−27)의 도달 경로가 열렸다.

### 7.2 관측 — 프리셋 풀 절단은 **안 풀렸다** (예측 적중)

인수가 아니라 관측으로 쐈다. 예측은 「호출부에 페이징 루프가 없으니 그대로」였다.

    t95_state_dump --path 'DataPool/PresetPools/1' --listen-port 9005
    -> childCount 20 · children 19 · offset 0 · truncated true

→ `pool-after-162-20260830.json`. **1.6.2 전과 동일하다.**

이로써 t131 의 진단이 확증됐다 — 절단은 응답기 버전이 아니라 **호출부** 결함이다:
`console/lua/copilot_responder.lua:230`(state 페이징은 1.6.0부터) ·
`server/orchestrator/tools.py:4870`(오프셋 없이 1회 호출) ·
`server/rig/section.py:91`(`truncated` → fail-closed).

**여전히 안 잰 것:** 실기 1.6.2 가 `state ... offset=N` 을 실제로 존중하는지. 방금 쏜
`offset` 은 **introspect** 다. lua 는 두 verb 가 파서 하나(`parse_paged_args`)를 공유한다고
적어 두었지만 그건 소스 근거다 — `t95_state_dump` 에 `--offset` 이 없어 실측을 못 했다.
t131 이 그 플래그를 붙이면서 실측으로 승격한다.
