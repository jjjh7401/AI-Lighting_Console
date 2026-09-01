## 무엇을 했나

t221 이 「POS 3행 불가」의 뿌리를 **콘솔 좌표 86대가 전부 원점**이라고 특정했다.
이 PR 이 그 좌표를 실제로 올리고, 그 다음에 무엇이 막는지 쟀다.

- 좌표 **86/86** 쓰기·되읽기 성공
- POS.01~06 **6/6** 산출(t221 이 죽었다고 판정한 세 행 포함) 후 `PresetPools/2` 저장
- 여덟 개 포지션 큐 중 **전 행 해결 1개(Q010)**, **실제 계획 0개**
- 회차 중 콘솔 거동 하나를 새로 실측: **MA3 는 프리셋 라벨에서 `.` 을 지운다**

전체 판정·증거: `.moai/reports/t224/verdict.md`

## 스택 순서 (둘 다 미머지)

    origin/main
      └─ origin/WT-pos-join   7f16e6b   PR #270   ← base
           └─ origin/WT-rig-coords aba50f1        ← 좌표 CSV·플롯을 머지해 들여옴
                └─ WT-coords-live  (이 PR)

`main` 을 향해 열지만 **#270 이 먼저 머지돼야 한다.** `WT-rig-coords` 는 데이터
두 파일(coords CSV 86행 · 플롯 HTML)만 들고 오므로 이 브랜치 안에 머지했다.

## 쓰기 봉투

기존 `arrange_fixtures` 의 봉투를 **한 줄도 우회하지 않았다**:
백업 읽기 → 정적 범위검사(`arrange_scope_violations`) → 쓰기 → 수치 되읽기,
그리고 복원 번들(`arrange_restore_commands`). Pan/Tilt 는 `ARRANGE_AXES` 밖 그대로다.

빈 자리는 **계획 산출 단계 하나**였다 — 기존 프리셋이 전부 기하 도형이라 장비마다
값이 다른 측량표를 표현할 수 없었다. 그래서 `explicit` 프리셋을 더했다: 계산하지
않고, 호출자가 실은 좌표를 도형 경로와 **같은 술어**(`_quantise`·`_target_fids`)로
검증·양자화만 한다.

`fids` 를 `positions` 와 따로 요구하는 것은 중복이 아니라 **선언**이다. 정적
범위검사가 명령문을 그 목록에 대고 검사하는데, 그 목록을 좌표에서 그대로 뽑아
쓰면 검사가 자기 자신을 검사하게 된다.

**쓰기 전에 복원 번들을 콘솔에서 확보했다.** `--action preview` 는 승인을 거부하는
채널로 같은 호출을 돌린다 — 백업은 실제로 읽히고 쓰기는 게이트가 막는다.

    targets 86 · backup rows 86 · restore lines 258 · unreadable None
    gate_status rejected · executed false
    독립 재판독 Posx "0.0"                       ← 쓰기 0건
    backup 좌표의 서로 다른 값: (0.0, 0.0, 0.0) 하나뿐   ← t221 재현

## 되읽기 증거

**좌표** — 3대 먼저, 그다음 86대.

    --limit 3   status arranged · verified True · mismatches None
                readback 101 (-5.0,-9.0,7.5) · 102 (-3.0,-9.0,7.5) · 103 (-1.0,-9.0,7.5)
                도구 밖 독립 재판독 slot 1: FID "101" Posx "-5.0" Posy "-9.0" Posz "7.5"

    --limit 0   status arranged · verified True · succeeded True · mismatches None
                readback rows 86 · 서로 다른 좌표 86개
                표본 201 (-6.0, 4.5, 6.1999998092651) · 430 (5.0, -1.0, 0.30000001192093)
                tolerance rel/abs 1e-06

float32 드리프트(6.2 이 6.1999998092651 로)가 그대로 보인다 — 문자열 비교였으면
정상 쓰기가 실패로 잡혔을 자리다. `ok` 를 증거로 쓰지 않았고, 판정은 전부 도구의
되읽기 + 도구 밖 독립 재판독이다.

**프리셋** — `pool_before childCount 0` → `pool_after childCount 6`.

    POS01 보컬 센터 페이스 · 합성좌표
    POS02 무대 전체 커버 · 합성좌표
    POS03 밴드 라인 백 · 합성좌표
    POS04 틸트업 스타트 (무대 안쪽) · 합성좌표
    POS05 팬아웃 종점 (객석 상단) · 합성좌표
    POS06 센터 집중 (브리지) · 합성좌표

`childCount 0` 을 부재로 읽지 않았다 — 같은 호출 형태로 형제 풀
`DataPool/PresetPools/4` 를 쳐서 `childCount 7` 을 받았다.

## 🔴 새 실측 — 콘솔이 라벨의 점을 지운다

    보냄   Label Preset 2.1 'POS.01 보컬 센터 페이스 · 합성좌표'   status executed_ok
    되읽음 state DataPool/PresetPools/2 → "POS01 보컬 센터 페이스 · 합성좌표"

    대조군 state DataPool/PresetPools/4 → "골드 앰버 (=P1)" · "핫 핑크 (=P4)" …

같은 판독 채널이 괄호도 `=` 도 그대로 답한다. 즉 판독기가 문장부호를 지우는 것이
아니라 **콘솔이 `.` 만** 지운다(추정 원인 `pool.slot` 구분자 — 그 추정은 안 쟀다).

조인 술어(`import_lxseq_cues`)가 `POS.` 를 요구하고 있어 여섯 프리셋이 전부 안
걸렸다. **비교 시점에 정규화하지 않았다** — 그러면 「보낸 라벨 == 되읽은 라벨」이
상시 거짓이 되고, 되읽기가 이 저장소의 유일한 판정 수단이라 그 수단에 노이즈를
심는다. 대신 **콘솔이 안 삼키는 형태로 보낸다.** 시트 정본 키(`POS.01`)와 콘솔
라벨 첫 어절(`POS01`) 사이의 변환은 `position_derive.py` **한 자리**에서만
일어나고(`console_label_head` · `preset_id_from_console_head`), 조인은 자기 술어를
안 갖고 그 함수를 부른다.

왕복 대조: **보낸 라벨 6개 == 되읽은 이름 6개 (True)**. 괄호가 든 POS04 도 동일.

느슨해진 것은 점 하나뿐이다 — `POS001` · `POSA1` · `POS.1` · `POS 03` · `POS01foo`
는 전부 안 걸린다(전수 검사 + 뮤테이션 M7).

## `POS.xx` 낱개 결과

| ID | 그룹 | 규칙 | 조준 | 판정 |
|---|---|---|---|---|
| POS.01 | KEY | `focus_vocal` | 6 | 산출 |
| POS.02 | MOVER-D | `spread_floor` | 8 | 산출 |
| POS.03 | BACK | `silhouette_line` | 12 | 산출 |
| POS.04 | MOVER-U | `floor_inside` | 8 | 산출 |
| POS.05 | MOVER-ALL | `fan_out` | 16 | 산출 |
| POS.06 | KEY+BACK | `focus_vocal` | 18 | 산출 |

`skipped` **0건**. t221 의 세 「불가」가 전부 풀렸고, 퇴화(전원 한 값)도 사라졌다 —
POS.01/02/05/06 은 장비마다 pan/tilt 가 다르다.

다만 **POS.03 은 12대 전부 `(180.0, 44.2)`, POS.04 는 8대 전부 `(180.0, 19.9)`** 다.
t221 의 퇴화와 원인이 다르다: 두 규칙이 장비를 「자기 x · cy · z」로 겨누므로 x 가
상쇄되고, 같은 트러스 위 장비는 y·z 가 같아 각도가 같아진다. **좌표가 아니라 규칙의
성질**이고 시트 문장과 어긋나지 않는다. 무대에서 맞는지는 안 쟀다.

## 여덟 큐 — 몇 개가 열리나

`--action preview --limit 0`, **콘솔 apply 없음**.

| | 조인 수리 전 | 조인 수리 후 |
|---|---|---|
| `preset_slots_resolved` | 14 | **20** (+6) |
| 미해결 프리셋 | POS 6 + BM 4 + FX 6 + COL 1 | **BM 4 + FX 6 + COL 1** |
| 보류 행 | 30 | 28 |
| 여덟 중 전 행 해결 | 0 | **1 (Q010)** |
| `planned_cues` | 0개 | **0개** |

| 큐 | 판정 | 남은 미해결 |
|---|---|---|
| Q010 | **전 행 해결** | — |
| Q020 | 보류 | `COL.02` |
| Q040 | 보류 | `BM.02` · `FX.03` |
| Q050 | 보류 | `BM.01` · `BM.03` · `FX.01` |
| Q080 | 보류 | `BM.02` |
| Q090 | 보류 | `BM.01` · `BM.03` · `FX.01` |
| Q110 | 보류 | `BM.04` |
| Q130 | 보류 | `BM.01` · `BM.03` · `FX.01` |

**POS 를 무는 행은 여덟 개 전부에서 해결됐다.** `planned_cues` 가 0인 것은 실패가
아니라 규격이다 — `LX-SEQ-SPEC-v2.1.md` §11.1 「부분집합 금지」라 한 행이라도
보류면 배치 전체가 거절된다. 정직한 답은 **「여덟 중 0개가 콘솔에 갈 수 있다」**이고,
그 0 의 원인이 좌표에서 **BM·FX·COL 조인**으로 옮겨간 것이 이 카드의 결과다.

## 회귀

| | 통과 | 건너뜀 |
|---|---|---|
| base (`WT-pos-join` + rig-coords, 자체 venv) | 10745 | 12 |
| 이 브랜치 | **10779** | 12 |

**+34**, 전량 설명:

- `test_spatial_explicit_arrange.py` 신규 **30**
- `TestConsoleDropsTheDotInLabels` 신규 **4**
- 수정한 검사 2건은 **제자리 수정**이라 수를 안 바꾼다
  (`test_its_schema_closes_the_preset_vocabulary` 어휘가 `explicit` 하나 늘었고 목록은
  여전히 박혀 있다 · `test_the_label_leads_with_the_id_so_the_join_can_key_on_it`
  조인 키가 `POS01` 로 바뀌었고 왕복 단언을 더했다)

기준선은 리드 값을 옮기지 않고 **이 트리에서 자체 venv 로 다시 쟀다.** 전수 판정은
이 PR 의 CI 런으로 대신한다.

**뮤테이션 9/9 사망, arm2 전부 0** — 아홉 갈래 모두 이 카드 전에는 아무도 안
지키고 있었다. 1회차에 M3 이 거짓 생존했는데, 치환 술어가 파일에 세 번 나와
`replace(…, 1)` 이 엉뚱한 함수에 붙은 것이었다. `assert mutated != original` 은
통과한다 — 치환은 됐고 자리만 틀렸다. 러너에 `count(old) == 1` 을 더해 기계화했다.

## Gaps (안 잰 것)

- **좌표가 합성이다.** 감독 승인 아래 만든 값이고 현장 보정이 전제다. 라벨의
  `· 합성좌표` 가 그 사실을 나른다. 무대에서 빔이 어디 떨어지는지는 이 카드가 못 잰다.
- `.` 삭제의 **원인**은 추정이다. 다른 문자(`/` `:` `,`)와 다른 풀은 안 쐈다.
- **POS.02 의 「면이 아니라 선」**(t221 §5) — 이제 잴 수 있는데 안 쟀다.
- **POS.03·04 의 「전원 한 값」이 무대에서 맞는지** — 판독은 규칙 탓이라고 읽었다.
- **기종별 Pan/Tilt 물리 가동범위** — t221 §4 의 gap 그대로. `135.0°` 는 여전히
  다른 리그의 상수이고, 이번엔 아무 행도 안 걸려서 노출되지 않았을 뿐이다.
- **BM·FX·COL 미해결 11종** — 세기만 했고 원인은 안 갈랐다(리드 판단: 별 카드).
- **큐 apply 안 함.** `Sequences/3` 무접촉.
- **복원 번들을 쏴 보지 않았다** — 안전장치를 발사해서 확인하지 않는다.
- **t222(PR #271)의 `degenerate_rig` 가드**와 합쳐서 안 돌려 봤다. 좌표가 폭을
  가지므로 안 걸릴 것으로 읽지만 미측정이다.

## 콘솔에 남긴 것

- `Patch/Stages/1/Fixtures/*` 의 `Posx/Posy/Posz` 86대 (이전 전부 `0.0`,
  복원 번들 258줄 `.moai/reports/t224/evidence/restore_bundle.txt`)
- `DataPool/PresetPools/2` 프리셋 6개 (이전 `childCount 0`)

무접촉: `Sequences/2`·`/3`, `PresetPools/1`·`/4`·`/21`, 오늘의 프로브 잔여물.

🗿 MoAI
