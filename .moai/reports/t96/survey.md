# t96 · t105 — 읽기 전용 실기 측정

날짜: 2026-08-26 · 트리: `.claude/worktrees/t96` (base `94d4f76`) · 브랜치 `WT-name-roundtrip-live`
콘솔: grandMA3 onPC (`app_gma3` pid 78611, UDP 8000·9005 점유) · `127.0.0.1:8000` 송신 / `9005` 수신
**콘솔 쓰기 0줄** — 모든 호출이 `--approve` 없는 `--action preview` 또는 introspect/props 판독이다.

## 1. 주장 (Claim)

1. t96 ① — 같은 CSV 를 다시 쏘면 매퍼가 수렴한다. **다만 6건이 카드가 지목한 바구니에 없다.**
2. t96 ③ — col·bm 계열의 이름 왕복은 **지금 측정 불가**다. 저장 가능 0건이라 콘솔에 이름이 없다.
3. t105 — 값 판독의 유일한 확장 경로(introspect 페이징)가 **실기에서 살아 있지 않다.**
   main 의 코드는 1.6.2 인데 콘솔에 로드된 응답기는 **1.6.1** 이다.

## 2. 증거 (Evidence)

### 2.0 계기 신뢰성 — 날조 대조군을 먼저 쐈다

    python -m server.tools.introspect_probe --path 'DataPool/ZZZNoSuchPoolXYZ' --listen-port 9005
    → introspect failed: path segment not found: 'ZZZNoSuchPoolXYZ'

→ `control-fabricated-path.txt`

`lxseq_presets_e2e` 는 회차마다 자체 대조군을 싣는다 — 네 회차 전부
`baseline.fabricated_control.ok = false`, `baseline.channel_trustworthy = true`.
계기가 아무 경로에나 `ok` 를 주지 않으므로 아래 판독은 증거다.

### 2.1 t96 ① — 네 시트 전수 (읽기 전용)

    python -m server.tools.lxseq_presets_e2e --preset-csv <시트> \
      --action preview --limit 0 --listen-port 9005

| 시트 | pool | read | planned | held | already_present | pool_after |
|---|---|---|---|---|---|---|
| dim | 1 | 6 | **0** | **0** | **6** | 6 |
| col | 4 | 8 | 0 | 8 | 0 | 0 |
| bm  | 5 | 5 | 0 | 5 | 0 | 0 |
| pos | — | — | — | — | — | — |

원자료: `preview-dim.json` · `preview-col.json` · `preview-bm.json` · `preview-pos.json`

🔴 **카드 문면 정정.** 카드는 「planned=0 · held=6」을 예측했다. `planned=0` 은 맞고
6건은 **`already_present`** 에 있다. 툴 자신의 정의로 두 바구니는 다른 뜻이다 —
`held` 는 「시트 자체가 넣을 수 없어 보류」, `already_present` 는 「같은 이름이
콘솔에 이미 있어 계획에 안 들어감」이다. 수렴은 확인됐으나 지목한 자리가 틀렸다.

`pos` 시트는 프리셋 시트가 아니다: `unknown_preset_sheet: ID, StageMeaning,
TargetGroup, RecordGuide`. 범위 밖이지 실패가 아니다.

### 2.2 t96 ③ — col·bm 은 여전히 저장 가능 0건

보류 사유(원자료의 `held_by_class`):

| 시트 | 클래스별 집계 | 행 수 |
|---|---|---|
| col | `scale_unconverted` 6 · `no_rgb_value` 2 | 8 |
| bm  | `attribute_probe_rejected` 3 · `family_out_of_scope` 3 | **5** |

⚠️ **계기 주의**: `held_by_class` 는 **행이 아니라 클래스 출현 횟수**를 센다. bm 은 3+3=6
이지만 행은 5다 — `BM.01` 이 `attribute_probe_rejected` 와 `family_out_of_scope` 를
함께 진다. 이 집계를 합산해 행 수로 읽으면 틀린다.

따라서 col·bm 의 이름 왕복은 **NEGATIVE 가 아니라 측정 불가**다. 대조할 대상 자체가
콘솔에 없다. 「이름이 안 맞는다」로 닫으면 안 잰 것을 닫는 것이다.

### 2.3 t105 — introspect 페이징이 실기에서 안 산다

    python -m server.tools.introspect_probe --path 'DataPool/PresetPools/1/3' \
      --offset 27 --listen-port 9005
    → introspect failed: path segment not found: '3 offset=27'
                         (in DataPool/PresetPools/1/3 offset=27)

→ `introspect-offset-27-swallowed.txt`

오프셋 토큰이 **경로에 삼켜졌다.** 이 트리의 `console/lua/copilot_responder.lua:239`
가 그 실패를 이름까지 붙여 예고해 뒀다 — "which is exactly the pre-1.6.2 failure —
an offset token swallowed into the path". 같은 파일 242행이 1.6.2 의 파서다.

추론으로 두지 않고 버전을 직접 쟀다:

    python -m server.tools.responder_roundtrip --listen-port 9005 --skip-exec \
      --expect-version 1.6.2
    → [FAIL] ping: live responder version '1.6.1' != expected '1.6.2'
             live version=1.6.1 plugin=CopilotResponder
    → [PASS] state: ok

→ `live-responder-version.txt`

**코드는 맞고 배포가 안 갈렸다.** t104 는 PR #164 로 main(`0c0adfa`)에 들어갔지만
콘솔에 로드된 플러그인은 1.6.1 이다. 툴 자신의 진단 문구가 원인을 지목한다 —
재임포트가 **구동 중인 플러그인을 갱신하지 않는다**(`console/lua/README.md`
§ Deployment Reliability).

`state` 는 PASS 다 — 채널이 죽은 것이 아니라 **이 버전에 그 기능이 없다.**

## 3. 기준선 귀속 (Baseline-attribution)

- 트리 `.claude/worktrees/t96`, `git rev-parse --short HEAD` → `94d4f76`,
  `git rev-list --count --left-right origin/main...HEAD` → `0` `0`
- 자체 venv (`uv sync --group dev`). 주 체크아웃 venv 를 빌리지 않았다
- t87 기준선 `.moai/reports/t87/name-roundtrip.json` (compared 6 · byte_equal 6)
- t95 대조군 `.moai/reports/t95/state-group-1.json` (`ALL` 그룹이 childCount 0 을 답한다)

곁가지 실측 1건 — `baseline.groups.child_count` 가 **18** 이다. t4 카드가 적어 둔
측정 조건 「DataPool/Groups 0」은 만료됐다(t66 이 18개를 올렸다).

## 4. 미검증 (Gaps) — 안 잰 것

| 안 잰 축 | 왜 |
|---|---|
| t96 ② **이름 길이 상한** | 긴 이름을 저장해 봐야 안다 = 콘솔 쓰기. 이 회차 범위 밖 |
| t96 ③ col·bm **이름 왕복** | 저장 가능 0건이라 대상 부재. 시트 쪽이 먼저다 |
| t105 **PRESETDATA 재판독** | 값이 든 프리셋이 필요하고, 만들려면 빈 슬롯에 저장 = 콘솔 쓰기 |
| 프로퍼티 **111개 이름** | 실기 1.6.1 이라 페이징이 없다. 1.6.2 를 콘솔에 다시 물려야 열린다 |
| **값 일치**(`value_match`) | 매퍼가 `unverified` 로 계속 실어 나른다. 이 회차가 바꾸지 않았다 |
| dim 6건의 **값이 맞는지** | `already_present` 는 이름만 대조한다. 「이미 있음」은 「맞게 있음」이 아니다 |

## 5. 잔여 위험 (Residual-risk)

- **`already_present=6` 을 「검증된 6건」으로 읽으면 틀린 값이 조용히 영속한다.**
  이름만 같고 값이 다를 수 있고, 그 값은 이 채널로 안 읽힌다.
- 1.6.1 을 1.6.2 로 갈아도 **111개 안에 값 이름이 있다는 보장은 없다.** 페이징은
  열거를 열 뿐이고, t95 §2.4 가 보였듯 **열거 목록은 판독 가능성의 목록이 아니다**
  (`GUID` 가 열거되지만 property not readable).
- `Patch/Stages/1/Fixtures` 는 이번에도 `truncated: true` (86 중 19). 절단은 개수가
  아니라 페이로드 예산이므로, 「N개가 온다」로 못박는 검사를 만들면 안 된다.
- 이 회차는 콘솔 쓰기 0줄이라 **되돌릴 것이 없다.**
