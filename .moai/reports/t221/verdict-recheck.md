# t221 재측정 — 처방 둘이 이행됐고, POS 는 더 이상 막지 않는다

**판정: 이 카드는 이미 답이 나와 있었다.** 같은 폴더의 `verdict.md`(콘솔 좌표가 전부
`(0,0,0)` 이던 시점의 회차)가 (A)물리 도달 불가도 (B)규칙 오류도 (C)모델 불일치도
아니라 **퇴화한 입력**이라고 이미 판정했고, 처방 둘을 남겼다. 이 회차가 새로 잰 것은
**그 처방이 이행됐는지**와 **그래서 큐가 몇 개 열리는지**다.

| 그때의 처방 | 이행 | main 반영 |
|---|---|---|
| 처방 1 — 콘솔에 실제 리그 좌표를 넣는다 | t224 | `45a8307` — `git merge-base --is-ancestor` YES |
| 처방 2 — 퇴화 리그를 `degenerate_rig` 로 거절한다 | t222 | `d4d6651` — 같은 방법으로 YES |

배차서와 카드 본문은 처방 이행 **이전**의 「산출 3 / 불가 3」을 실었다. 틀린 값이 아니라
낡은 값이다 — 아래가 그것을 잰 기록이다.

측정 트리 `.claude/worktrees/t221` · base `origin/main 24f11e5` · 브랜치 `WT-pos-aim-cause`
콘솔 접촉 전부 **읽기 전용**(`--action preview`, `--approve` 없음). 콘솔 쓰기 0건.

---

## 1. 배차 전제가 만료됐다 — 재서 반증

배차서(와 카드 본문)는 「산출 3 / 불가 3, 사유 '대상 전부 조준 한계 밖 또는 계산 불가'」를 실었다.
같은 명령을 이 트리에서 다시 돌렸다.

| 시점 | 좌표(콘솔이 답한 값) | 산출 | 거절 |
|---|---|---|---|
| `2026-09-01T13:10:25+0900` (구 t221 회차) | 86/86 이 `(0.0, 0.0, 0.0)` — all-zero 86 | **3** | `unaimable` 3 (POS.02·03·04) |
| `2026-09-01T22:17:57+0900` (이 회차) | 86/86 실좌표, all-zero **0**, `low_confidence=false` | **6** | **없음** (`skipped: []`) |

같은 콘솔 · 같은 포트 9005 · 같은 86 FID 집합이다. **바뀐 것은 좌표뿐**이고, 그 좌표를 넣은 것이 t224(`45a8307`, main 에 있음)다.

증거:

- 구: `evidence/preview.json` (산출 3 / 거절 3) · `evidence/spatial_raw.json` (`fixtures[*] x=y=z=0.0`, `freshness.read_at 13:10:25`)
- 신: `evidence/live_preview_t221.json` (산출 6 / `skipped: []`) · `evidence/spatial_raw_after_t224.json` (`101 → (-5.0, -9.0, 7.5)`, `analysis.low_confidence false`, `vertical_span 7.3`)

명령줄(신, 라이브):

    uv run python server/tools/lxseq_pos_e2e.py \
      --pos-csv src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.preset-pos.csv \
      --patch-csv ...patch.csv --group-csv ...group.csv \
      --action preview --limit 0 --listen-port 9005 \
      --out .moai/reports/t221/evidence/live_preview_t221.json

산출물의 `approval_requests` 가 `[]` 다 — 승인 통로에 아무것도 안 갔다.

### 두 산출물이 어느 코드에서 나왔나 — 추론이 아니라 잰 것

두 산출물의 **필드 구성 자체가 다르다**: 구 `preview.json` 은 `label_suffix: null`, 신 산출물은 `label_suffix: "산출값"`.
`label_suffix` 는 t224 가 더한 인자다(`position_derive.py` 의 `derive_position_presets(label_suffix=...)`).
즉 구 측정은 **t224 이전 코드 + 퇴화 좌표**에서 나온 값이다. 틀린 값이 아니라 낡은 값이다.

⚠️ 다만 「구 회차가 정확히 어느 커밋에서 돌았는가」는 이 필드로 **하한만** 정해진다 — 커밋 SHA 는 산출물에 없다. 그건 미측정으로 남긴다.

## 2. (A)/(B)/(C) 는 이미 답이 나왔고, 지금은 답할 대상이 없다

행별 판정과 **초과 각도**는 `verdict.md` §8 이 퇴화 상태에서 이미 쟀다 — POS.03 은
`tilt 180.0° vs 상한 135.0° → +45.0°`, POS.02·POS.04 는 `목표점 = 장비 자신, 거리 0.0 m`
로 tilt 미정의. 셋 다 같은 뿌리(좌표 0)이고, 그래서 그 문서는 「좌표가 채워지기 전에는
(A)/(B)/(C) 어느 것도 원리적으로 판정할 수 없다」로 닫았다.

좌표가 채워진 지금은 **세 행의 거절이 0건**이라 붙일 초과 각도가 없다. 배차서가 요구한
행별 (A)/(B)/(C) 분류는 **사라진 문제**다 — 새 값을 만들어 채우지 않는다.

카드가 든 단서(「POS.03 은 불가인데 같은 BACK 12대를 포함한 POS.06 은 된다」)도 같은 자리에서
설명된다: 전 장비가 한 점에 접히면 목표점을 자기 규칙으로 만드는 행은 목표가 자기 자신이거나
한계 밖이 되고, POS.01 의 점을 재사용하는 POS.06 은 그 한 점을 물려받아 통과한다.
⚠️ 이 문단은 **설명**이다 — 퇴화 상태의 행별 수치는 위 `verdict.md` §8 이 근거이고, 이 회차가 다시 재지 않았다.

## 3. 큐는 몇 개 열리는가

명령줄:

    uv run python server/tools/lxseq_cues_e2e.py \
      --cue-csv src/Lighting_Designer/03_곡파일_Sugar/LXSEQ_SAMPLE_01_Sugar_r3.cue-ex.csv \
      --sequence-name Sugar --action preview --limit 0 --listen-port 9005 \
      --preset-dim-csv ... --preset-col-csv ... --preset-bm-csv ... --fx-csv ... --cue-sheet-xlsx ... \
      --out .moai/reports/t221/evidence/cues_preview_t221.json

**POS 축은 완전히 열렸다. 지금 막는 것은 BM·COL·FX 다.**

POS 를 참조하는 큐 8개의 현재 보류 사유:

| 큐 | 참조 POS | 지금 보류? | 보류 사유 |
|---|---|---|---|
| Q010 | POS.03 | **아니오 — 열렸다** | — |
| Q020 | POS.01 | 예 | `COL.02` |
| Q040 | POS.04 | 예 | `BM.02` |
| Q050 | POS.05 · POS.02 | 예 | `BM.01` · `BM.03` |
| Q080 | POS.04 | 예 | `BM.02` |
| Q090 | POS.05 · POS.02 | 예 | `BM.01` · `BM.03` |
| Q110 | POS.06 | 예 | `BM.04` |
| Q130 | POS.05 · POS.02 | 예 | `BM.01` · `BM.03` |

**보류 사유에 POS 가 한 건도 없다.** 미해결 참조는 7종이고 전부 `console_lacks_name` 이다:
`BM.01` `BM.02` `BM.03` `BM.04` · `COL.02` · `FX.04` `FX.06`.

양성 대조군 — POS 가 정말 조인되는지: `Q010` 1행의 참조는 `COL.01` 과 `POS.03` 둘뿐이고(정본 CSV 직독),
`COL.01` 은 미해결 목록에 없고 `POS.03` 도 없으며 **Q010 은 held 가 아니다**. `POS.03` 이 안 풀렸다면 Q010 이 보류됐어야 한다.
POS 는 다른 종과 같은 `resolve_preset_ref` 를 탄다(`cue_mapper.py:669`) — 조용히 건너뛰는 경로가 아니다.

전체 18큐 기준으로 **보류 행이 0인 큐는 7개**: `Q010 Q030 Q060 Q100 Q120 Q170 Q180`. 보류된 큐는 11개.

### 🔴 `planned_cues: 0` 을 「0개 열림」으로 읽지 마라

산출물의 `planned_cues` 는 `[]` 이고 `cue_bundles_planned` 는 0 이다. 그런데 **원인이 보류가 아니다** —
`cues_already_present` 가 18큐 **전부**다. 코드가 두 조건을 함께 뺀다(`cue_mapper.py:928`):

    if rows_by_cue.get(cue) and cue not in cues_already_present and cue not in held_cue_names

즉 이 0 은 「막혔다」가 아니라 **「새로 쏠 게 없다」**다. 두 상태가 같은 숫자로 나오므로 `planned_cues` 만 보면 갈리지 않는다.

## 4. 안 잰 것

- **빔이 실제로 어디 떨어지는지** — 프리셋 값 판독 채널이 없다(t105). 산출물도 `unverified: ["field_record"]` 를 스스로 단다.
- **조준 상한 135°** 가 다른 기종에서 온 가정이라는 사실은 그대로다. 이번 회차는 거절이 0이라 이 상한에 걸린 행이 없어 **재지 않았다**.
- **구 회차의 정확한 커밋 SHA** — 위 §1 참조. `label_suffix` 부재로 t224 이전이라는 하한만 잡았다.
- **퇴화 좌표에서의 행별 수치** — 이 회차가 재지 않았다. `verdict.md` §8 의 값을 인용만 했다.
- **좌표 자체가 합성이다**(t224, 감독 승인·현장 수정 전제). 실측 좌표가 아니다.
- 콘솔 쓰기 **0건**. 프리셋 풀 2 는 t224 가 남긴 6건 그대로이고 이 회차는 건드리지 않았다.

## 5. 남은 병목 — 이 카드 밖

`BM.01~04` · `COL.02` · `FX.04` · `FX.06` 이 콘솔 풀에 없다. 이것이 지금 11큐를 잡고 있고, t224 가 「원인이 좌표에서 BM·FX·COL 조인으로 옮겨갔다」고 적어 t225 로 낸 그 자리다. 고치는 것은 이 카드 범위 밖이다 — 리드 판단.

## 6. 이 회차가 만든 파일

    .moai/reports/t221/verdict-recheck.md                       이 문서
    .moai/reports/t221/evidence/live_preview_t221.json          POS 산출 6/6 · skipped [] (라이브 preview)
    .moai/reports/t221/evidence/spatial_raw_after_t224.json     get_spatial_context 원문 (86대 실좌표)
    .moai/reports/t221/evidence/cues_preview_t221.json          큐 계획 preview (held 11 · 미해결 참조 7종)
    .moai/reports/t221/evidence/t221_raw_spatial_recheck.py     좌표 원문 덤프 프로브 (읽기 전용)

`verdict.md` 는 **숫자를 고치지 않고 맨 위에 만료 고지만 붙였다** — 그 시점의 기록이기 때문이다.
