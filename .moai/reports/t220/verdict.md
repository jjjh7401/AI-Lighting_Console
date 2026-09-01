# t220 — POS.xx 를 좌표에서 산출하고 큐 조인을 세운다

기준: `origin/main` `112c1c4` · 브랜치 `WT-pos-join` · 2026-09-01

## 1. 막힌 자리 — 구멍이 **둘**이었다

배차서는 조인 하나를 지목했는데 실제로는 둘이었다. 하나만 고쳤으면 슬롯은 풀리고
큐는 여전히 포지션을 안 불렀을 것이다 — 그리고 그 실패는 **조용하다**(명령은
성공하고 무빙만 이전 자리에 남는다).

| # | 구멍 | 자리 |
|---|---|---|
| 1 | POS 시트에 Name 열이 없어 ID -> Name -> 슬롯 조인이 안 선다 | `tools.py` `preset_slots` 루프 |
| 2 | **명령 조립 루프에 `row.pos` 가 아예 없다** — `for ref in (row.col, row.bm)` | `tools.py` 큐 번들 조립 |

2번은 배차서에 없던 것이다. 매퍼(`cue_mapper.py:607-617`)는 COL·POS·BM 셋을 모두
해석하는데 소비 루프가 둘만 읽고 있었다.

## 2. 접근 — 별칭표를 안 만든다

감독 결정대로 앱의 BASIC 10종에 매핑하지 않았다. 대신 시트가 이미 적어 둔 두 열을
기하로 푼다:

    StageMeaning(무대 의미) + TargetGroup(대상) + 리그 좌표  ->  Pan/Tilt

조인은 별칭표가 아니라 **라벨 첫 어절의 ID**로 선다. 콘솔에
`POS.01 보컬 센터 페이스 · 산출값` 으로 저장하면 `tools.py` 가 첫 어절 `POS.01` 을
읽어 슬롯을 잡는다 — COL 이 쓰는 이름 조인과 같은 층, 다른 키다.

🔴 **두 좌표계를 갈랐다.** 조준 대상은 그 행의 `TargetGroup`(전 픽스처가 아니다),
무대 기준틀은 **리그 전체**다. 대상 그룹만으로 기준틀을 잡으면 KEY 6대의 y 가
최전열이 되어 보컬 포인트가 FOH 브리지 2m 앞 — **객석 안**에 생긴다.
`TestDerivation::test_the_stage_frame_is_the_whole_rig_not_the_target_group` 이
이 축을 잡고, 뮤테이션 M7 이 그것을 확인했다.

## 3. POS 행별 결과 (산출 규칙)

| ID | 대상 | 규칙 | 상태 |
|---|---|---|---|
| POS.01 보컬 센터 페이스 | KEY | 리그 중심 x · 최전열 2m 앞 · 높이 1.6m 를 전원 조준 (`basic_position_presets` 의 Vocal DSC 와 **같은 점**) | 산출 |
| POS.02 무대 전체 커버 | MOVER-D | 리그 x 폭을 대수로 등분한 착지점을 무대 중앙 깊이 바닥에 한 줄로 | 산출 |
| POS.03 밴드 라인 백 | BACK | 각 장비 x 유지 · 무대 중앙 깊이 · 머리 높이 1.6m — 실루엣 각, 착지점이 무대 위라 객석 직사 없음 | 산출 |
| POS.04 틸트업 스타트 | MOVER-U | 각 장비 x 유지 · 무대 중앙 깊이 바닥 — 상승 시작점 | 산출 |
| POS.05 팬아웃 종점 | MOVER-ALL | `fan_pan_tilt(mode="out")` — 다운스테이지 기준 tilt 45도, 좌우 30도 부채꼴 | 산출 |
| POS.06 센터 집중 | KEY+BACK | POS.01 과 같은 보컬 포인트를 KEY+BACK 이 함께 조준 | 산출 |
| POS.07 크로스 빔 | MOVER-U | 규칙 없음 | **범위 밖** |
| POS.08 플로어 스캔 | MOVER-D | 규칙 없음 | **범위 밖** |

07·08 은 시트가 스스로 「예비 (타 곡 대비)」라 적었고 정본 큐시트가 한 번도
참조하지 않는다(전수: POS.01~06 만 12칸). 안 쓰는 프리셋을 올리는 것은 이득 없는
쓰기다. 검사가 「큐시트의 모든 POS 참조에 규칙이 있다」를 고정한다.

못 푸는 행은 **날조하지 않고** 사유와 함께 나온다: `unknown_group` ·
`no_coordinates` · `unaimable`. 한 행이 못 풀려도 나머지는 산다.

## 4. 산출은 레코드가 아니다

`rig_data.py:162` 의 「POS.01~08 포지션 프리셋 전부 현장 레코드 필요」는 이 카드
뒤에도 그대로 유효하다. 라벨 꼬리 `· 산출값` 이 콘솔 화면에서 산출과 레코드를
가르는 유일한 자리이고, 산출물도 스스로 말한다:

    unverified = ("field_record",)
    "좌표 기하에서 산출한 값이다 — 현장에서 실제 빔 착지를 보고 잡은 값이 아니다"


## 5. 🔴 콘솔 실기 — 못 했다. onPC 가 회차 중에 사라졌다

**콘솔 쓰기 0건. 되읽기 없음.** 산출값이 실제로 어디에 떨어지는지 안 쟀다.

시간순 실측:

| 순서 | 명령 | 결과 |
|---|---|---|
| 1 | `console_probe.py --listen-port 9005 state:DataPool/PresetPools` | ok · 풀 14개 · **Position = 2** |
| 2 | `state:DataPool/PresetPools/2` | ok · **childCount 0** |
| 3 | `state:DataPool/PresetPools/4` (대조군) | ok · childCount **7** · 이름 실목록 |
| 4 | `state:DataPool/Groups` (대조군) | ok · childCount **18** |
| 5 | `prop:Patch/Fixtures/101\|Posx` | `ok=false` · `path segment not found: Fixtures` |
| 6 | `state:Patch/Stages/1/Fixtures` (좌표 경로) | **TIMEOUT** (6s · 재시도 30s) |
| 7 | `state:Patch` · `state:Patch/Stages` · `state:Patch/Stages/1` | 전부 TIMEOUT |
| 8 | `state:DataPool/PresetPools/2` (1·2번과 **같은 명령**) | **TIMEOUT** |
| 9 | `ps aux \| grep -i ma3` · `lsof -nP -iUDP:8000` | **둘 다 0건 — onPC 프로세스가 없다** |

즉 2번의 `childCount 0` 은 살아 있는 계기가 답한 진짜 0 이다(3·4번이 양성 대조군).
그리고 8번이 1·2번과 **바이트 동일한 명령**인데 타임아웃이므로, 그 사이에 계기가
죽은 것이지 경로가 사라진 것이 아니다.

⚠️ **인과는 안 쟀다.** `state:Patch*` 조회 뒤에 응답기가 멎었고 이후 onPC 프로세스가
없다 — 상관은 관측했지만 그 조회가 onPC 를 죽였다고는 **관측하지 않았다**(죽는
순간을 못 봤고, 재현하려면 같은 사고를 한 번 더 내야 한다). 다만 좌표 경로를
프로브하려는 다음 사람은 이 순서를 알고 들어가는 편이 낫다.

**onPC 를 다시 띄우지 않았다.** 재기동은 쇼 파일을 다시 읽고, 이 콘솔에는
미저장 유일본이 있다(저장소가 여러 카드에서 그렇게 적어 뒀다). 감독·리드 판단이다.

### 실기가 열리면 할 일

    .venv/bin/python server/tools/lxseq_pos_e2e.py \
      --pos-csv src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.preset-pos.csv \
      --patch-csv src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.patch.csv \
      --group-csv src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.group.csv \
      --listen-port 9005 --action preview

`--action apply --approve --limit 1` 이 「소수 먼저 넣고 되읽는다」다.
`--approve` 없이는 콘솔에 아무것도 닿지 않고, 그 거부는 콘솔 스택을 세우기
**전에** 난다(실측: `--action apply` 단독 -> `error: --action apply 는 --approve 를 요구한다`).

## 6. 회귀 회계

전부 **이 워크트리의 자체 venv**(`uv sync --group dev`)로 쟀다.

| 상태 | 결과 |
|---|---|
| `origin/main` 상태(내 트리에서 tools.py·트립와이어 되돌리고 새 파일 뺌) | `10725 passed, 12 skipped` + 인위적 실패 2 = **10727** |
| HEAD | **`10745 passed, 12 skipped`** |

차이 **+18** = 새로 넣은 검사 18개. 지운 검사 0, 교체 0.
인위적 실패 둘(`test_tools_hunks_...` · `test_the_touched_set_covers_non_ascii_paths`)은
스왑 자체가 만든 것이다 — HEAD 커밋과 디스크가 어긋난 상태를 그 둘이 본다.
리드 기준값 `10727 passed, 12 skipped` 와 일치한다.

헝크 트립와이어(`test_songcue_bundle.py`): 47 -> 48, 새 시작점 **477**(순수 삽입,
count 0), 사라진 시작점 없음. 보호 구간 둘(234..238 / 524..569) 무접촉 —
524..569 이웃은 479·591 로 그대로다.

## 7. 재현 우선 · 뮤테이션

`TestCueJoin` 이 빨강/초록이다. 같은 파일을 `origin/main` 의 `tools.py` 로 돌리면
**3 failed, 15 passed**, 이 브랜치에서 **18 passed**:

| 검사 | origin/main | HEAD |
|---|---|---|
| `test_a_derived_label_lets_the_same_sheet_plan` | FAIL (`rows_held`) | PASS |
| `test_the_cue_command_recalls_the_position_preset` | FAIL (`KeyError: approval`) | PASS |
| `test_the_pool_number_comes_from_the_console_reply_not_a_constant` | FAIL (`rows_held`) | PASS |
| `test_an_empty_position_pool_holds_the_row_and_refuses_the_batch` | PASS | PASS |
| `test_a_label_without_the_id_does_not_resolve` | PASS | PASS |

뒤 둘은 **팔 2** 다 — 오늘의 상태(빈 풀)와 ID 없는 라벨은 여전히 안 풀린다는 것을
고정한다. 조인이 넓어지지 않았다는 증거이지 새 능력의 증거가 아니다.

뮤테이션 9종 · `PYTHONDONTWRITEBYTECODE=1` · 회차마다 `assert mutated != original`:

| # | 치환 | 판정 |
|---|---|---|
| M1 | 라벨 ID 판별을 `if False` 로 | 죽음 |
| M2 | 명령 조립에서 `row.pos` 를 뺀다 | 죽음 |
| M3 | 풀 번호를 상수 2 로 굳힌다 | 죽음 |
| M4 | 슬롯을 ID 와 무관하게 1 로 | 죽음 |
| M5 | 라벨에서 ID 를 뺀다 | 죽음 |
| M6 | 라벨에서 `산출값` 고지를 뺀다 | 죽음 |
| M7 | 무대 기준틀을 대상 그룹 좌표로 좁힌다 | 죽음 |
| M8 | 모르는 그룹을 빈 집합으로 삼킨다 | 죽음 |
| M9 | 좌표 없는 그룹을 조용히 계획에 올린다 | 죽음 |

**9/9 죽음.** M3 은 1회차에 **생존**했다 — 가짜 콘솔이 Position 풀 번호를 2 로
굳혀 두어서 「상수 2」 뮤턴트가 등가였다. 가짜의 풀 번호를 12 로 바꿀 수 있게
열고 다시 재니 죽었다. 계기가 실제 값과 같으면 그 축은 안 재진다.

## 8. 배차서에서 바꾼 것 (규약 §6)

배차서는 「`_PRESET_POOL_FAMILY` 에 Position 을 넣으라」고 했다. 넣었더니
`test_the_pool_family_table_covers_every_kind` 가 빨개졌다 — 그 표의 정의역은
`preset_parser` 가 파싱하는 **시트 종류**이고 등호로 고정돼 있다.
`preset-pos` 는 값 열이 없어 그 경로에서 명시적으로 빠져 있다(REQ-LXSEQ3-002).
그래서 그 표를 넓히는 대신 옆에 `POSITION_POOL_FAMILY = "Position"` 을 두고
이유를 주석으로 남겼다. 기존 가드를 무르지 않는 쪽이다.

## 9. PRESETGUARD-002 REQ-PG2-003 — 미구현 확인

배차서의 의심이 맞다. `_read_pointing_coordinates`(`session.py:4195`)는
`get_spatial_context` 응답을 그대로 쓰고 **Pan/Tilt 어트리뷰트 유무로 거르지
않는다.** 이 카드에서 고치지 않았다 — 산출 경로는 조준이 안 되는 장비를
`aim_pan_tilt` 거절로 잡아 `skipped_fids` 에 이름을 남기므로(클램프 없음) 같은
위험이 이 경로에는 없고, `session.py` 를 건드리는 것은 이 카드의 범위 밖이다.
REQ-PG2-003 자체는 **여전히 열려 있다.**

## 10. 안 잰 것 (Gaps)

- 🔴 **산출값이 실제로 어디에 떨어지는지.** 콘솔이 죽어 쓰기·되읽기 0건이다.
  Pan/Tilt 수치도 실좌표가 아니라 합성 좌표로만 계산해 봤다.
- 🔴 **8개 큐가 실기에서 계획으로 넘어가는지.** 가짜 상태 포트로는 넘어간다
  (POS 한 칸 기준). 정본 18큐 전체 preview 는 콘솔이 있어야 한다 —
  COL·BM·FX 슬롯 조인이 그 쇼 파일 상태에 달려 있다.
- **`state:Patch*` 조회가 응답기를 멎게 하는지.** 상관만 봤고 인과는 안 쟀다.
- **라벨 길이 상한.** `POS.04 틸트업 스타트 (무대 안쪽) · 산출값` 이 MA3 라벨에
  온전히 들어가는지 안 쟀다(따옴표·제어문자는 `preset_label_refusal` 이 본다).
- **POS.02 의 「겹침 30%」.** 등분 착지로 근사했을 뿐 실제 빔 각도로 겹침률을
  계산하지 않았다 — Zoom 을 모르면 못 푼다.
- **`fan_pan_tilt` 기본 spread 30도**가 시트의 「좌우 부채꼴」과 맞는지.
  시트에 각도가 없어 라이브러리 기본값을 썼다.
- **CI.** 저장소 전체가 결제정지로 죽어 있다(리드 고지). 로컬 자체 venv 로만 쟀다.

