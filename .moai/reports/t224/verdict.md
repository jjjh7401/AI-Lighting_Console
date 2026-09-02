# t224 — 좌표 86대를 콘솔에 올리고, 그 다음 벽이 어디인지 쟀다

기준: 브랜치 `WT-coords-live` · base `origin/WT-pos-join` `7f16e6b`(PR #270, 미머지)
+ `origin/WT-rig-coords` `aba50f1` 머지 · 2026-09-01 ·
콘솔 LIVE(onPC 2.4.2 · 응답기 1.6.2 · `--listen-port 9005`)

## 0. 한 줄

좌표 **86/86** 을 쓰고 되읽었고, POS.01~06 **6/6** 이 산출되어 `PresetPools/2` 에
올라갔다. 그런데 여덟 큐 중 **전 행이 해결된 것은 Q010 하나**이고 **실제로 계획된
큐는 0개**다. 좌표는 더 이상 벽이 아니다 — 다음 벽은 **BM·FX·COL 프리셋 조인**이다.

그리고 회차 중에 콘솔 거동 하나를 새로 쟀다: **MA3 는 프리셋 라벨에서 `.` 을 지운다.**

## 1. 좌표 쓰기

### 1.1 없던 경로를 만들었다 — 봉투는 그대로

`arrange_fixtures` 의 프리셋은 전부 **기하 도형**이라 장비마다 값이 다른 측량표를
올릴 길이 없었다. t221 의 「막힌 것은 능력이 아니라 데이터」는 절반만 맞았다 —
계획 산출 단계 하나가 비어 있었다.

`explicit` 프리셋을 더했다. **계산하지 않는다** — 호출자가 실은 좌표를 검증·양자화만
하고, 도형 경로와 **같은 술어**(`_quantise`·`_target_fids`)를 지난다. 봉투
(백업 → 정적 범위검사 → 쓰기 → 되읽기)는 한 줄도 우회하지 않았다.
Pan/Tilt 는 `ARRANGE_AXES` 밖 그대로다.

`fids` 를 `positions` 와 따로 요구한다. 중복이 아니라 **선언**이다: 정적 범위검사가
명령문을 그 목록에 대고 검사하는데, 그 목록을 좌표에서 그대로 뽑아 쓰면 검사가
자기 자신을 검사하게 된다.

### 1.2 쓰기 전 — 복원 번들을 콘솔에서 확보했다

`--action preview` 는 **승인을 거부하는 채널**로 같은 호출을 돌린다. 백업은 콘솔에서
실제로 읽히고 쓰기는 게이트에서 막힌다.

    server/tools/lxseq_coords_write.py --action preview --limit 0 --listen-port 9005

    targets 86 · backup rows 86 · restore lines 258
    walk: slot_queries 86 · roundtrip_capped false · truncated true
    unreadable: None
    gate_status: rejected · executed: false
    독립 재판독 sample_after Posx: "0.0"      ← 쓰기 0건 확인
    backup 좌표의 서로 다른 값: 하나뿐, (0.0, 0.0, 0.0)   ← 86대 전부 원점, t221 재현

거절 사유는 `blacklisted command (matches closed-set entry 'Set Fixture')` —
승인 채널이 거부했고 아무것도 안 나갔다.

복원 번들 258줄: `evidence/restore_bundle.txt` (원문 `evidence/coords_restore_bundle.json`).

### 1.3 쓰기 — 3대 먼저, 그다음 86대

**3대(소수 먼저):**

    --action apply --approve --limit 3
    status arranged · verified True · mismatches None
    readback: 101 (-5.0,-9.0,7.5) · 102 (-3.0,-9.0,7.5) · 103 (-1.0,-9.0,7.5)
    독립 재판독 slot 1: FID "101" Posx "-5.0" Posy "-9.0" Posz "7.5"

부호가 살았다 — `Set Fixture <fid> <axis> '<value>'` 의 홑따옴표 형태가 실기에서
음수를 지킨다(§E.2.6a 재확인).

**86대 전량:**

    --action apply --approve --limit 0
    status arranged · verified True · succeeded True · mismatches None
    readback rows 86 · 서로 다른 좌표 86개
    표본: 101 (-5.0,-9.0,7.5) · 201 (-6.0,4.5,6.1999998092651) · 430 (5.0,-1.0,0.30000001192093)
    tolerance: rel 1e-06 · abs 1e-06

float32 드리프트가 그대로 보인다(6.2 이 6.1999998092651 로). 문자열 비교였으면
정상 쓰기가 실패로 잡혔을 자리이고, 수치 비교라 통과했다.

`ok` 를 증거로 쓰지 않았다 — 판정은 전부 도구의 되읽기 + **도구 밖 독립 재판독**이다.

## 2. 🔴 새 실측 — MA3 는 프리셋 라벨에서 `.` 을 지운다

이 회차의 부산물이지만 프로젝트가 계속 쓸 사실이라 verbatim 으로 박는다.

**보낸 명령**(`evidence/pos_apply_6.json`, `sent[0].payload.commands`):

    {"command": "Label Preset 2.1 'POS.01 보컬 센터 페이스 · 합성좌표'",
     "status": "executed_ok", "detail": "OK"}

**되읽은 값**(`state DataPool/PresetPools/2`):

    "POS01 보컬 센터 페이스 · 합성좌표"

**대조군** — 같은 판독 채널, 같은 호출 형태, 형제 풀:

    state DataPool/PresetPools/4
    "골드 앰버 (=P1)" · "핫 핑크 (=P4)" · "딥 퍼플 (=P5)" · "터쿼이즈 (=P6)"

괄호도 `=` 도 그대로 온다. 즉 **판독기가 문장부호를 지우는 것이 아니라 콘솔이 `.` 만**
지운다. 추정 원인은 `.` 이 `pool.slot` 구분자라는 것 — 그 추정은 안 쟀다.

**왜 이게 조용한 결함인가.** 명령은 `executed_ok` 를 답하고, 풀에는 프리셋이 여섯 개
멀쩡히 보인다. 「6/6 저장 성공」에서 멈추면 여기서 끝난다. 어긋난 것은 이름 안의
한 글자뿐이고, 그 한 글자에 조인이 걸려 있었다.

### 2.1 고친 방식 — 비교가 아니라 왕복을 고쳤다

첫 제안은 비교 시점에 점을 지우는 것이었다. 리드가 물렀다: 그러면 **송신값과 수신값이
다른 상태**가 남고, 되읽기가 이 저장소의 유일한 판정 수단인데 그 수단에 상시 노이즈를
심는다.

그래서 **콘솔이 안 삼키는 형태로 보낸다.** 시트 정본 키(`POS.01`)와 콘솔 라벨 첫
어절(`POS01`) 사이의 변환은 `server/lxseq/position_derive.py` **한 자리**에서만
일어난다(`console_label_head` · `preset_id_from_console_head`).
`import_lxseq_cues` 의 조인은 자기 술어를 안 갖고 그 함수를 부른다.

**왕복 대조**(`evidence/pos_apply_6_dotless.json`):

    보낸 라벨 6개 == 되읽은 이름 6개 : True

    Label Preset 2.1 'POS01 보컬 센터 페이스 · 합성좌표'
      → "POS01 보컬 센터 페이스 · 합성좌표"
    Label Preset 2.4 'POS04 틸트업 스타트 (무대 안쪽) · 합성좌표'
      → "POS04 틸트업 스타트 (무대 안쪽) · 합성좌표"

괄호는 살아남는다 — `.` 만 문제였다는 것을 이 왕복이 다시 확인한다.

독립 재판독(`tools/console_probe.py`): `childCount 6`, 이름 6개 동일.

### 2.2 술어가 느슨해지지 않았다

느슨해진 것은 점 하나뿐이다. 접두·자릿수·숫자 검사는 그대로라
`POS001` · `POSA1` · `POS.1` · `POS 03` · `POS01foo` 는 전부 안 걸린다
(`test_normalising_the_dot_does_not_widen_the_predicate`, 네 형태 전수).
뮤테이션 M7 이 그 경계를 쏜다.

## 3. POS 산출 — 6/6, 실패 0

    server/tools/lxseq_pos_e2e.py --action preview --limit 0 --synthetic-coords

    coordinates_read: 86 · reason None
    POS.01 slot 1 KEY       focus_vocal      aims  6  skipped 없음
    POS.02 slot 2 MOVER-D   spread_floor     aims  8  skipped 없음
    POS.03 slot 3 BACK      silhouette_line  aims 12  skipped 없음
    POS.04 slot 4 MOVER-U   floor_inside     aims  8  skipped 없음
    POS.05 slot 5 MOVER-ALL fan_out          aims 16  skipped 없음
    POS.06 slot 6 KEY+BACK  focus_vocal      aims 18  skipped 없음
    skipped 행: 0

**t221 이 죽었다고 판정한 세 행(POS.02·03·04)이 전부 산다.** 조준 한계 초과도,
거리 0 도 없다. 카드가 「하나라도 실패하면 그것이 진짜 발견이다」라고 했는데
실패가 없으므로 그 발견은 없다.

퇴화도 사라졌다: t221 이 잰 「전원이 한 값」(POS.01·06 이 101~106 전부
`Pan 180 / Tilt 128.7`)이 이제 장비마다 다르다.

    POS.01  101 (-111.8, 42.4) · 102 (-123.7, 31.4) · 103 (-153.4, 20.8) …  서로 다른 값 6
    POS.02  서로 다른 값 8 · POS.05 16 · POS.06 18

### 3.1 다만 POS.03 · POS.04 는 전원이 한 값이다 — 이번엔 규칙 탓

    POS.03  12대 전부 (180.0, 44.2)
    POS.04   8대 전부 (180.0, 19.9)

t221 의 퇴화와 **다른 원인**이다. 두 규칙은 장비를 「자기 x · cy · z」로 겨눈다 —
x 가 상쇄되므로 조준 벡터가 y·z 평면 안에 갇히고, 같은 트러스 위 장비는 y·z 가
같으니 pan/tilt 가 같아진다. 즉 **좌표가 아니라 규칙의 성질**이고, 「각 장비가
자기 앞을 곧게 본다」는 시트 문장과 어긋나지 않는다. 무대에서 맞는지는 안 쟀다.

## 4. 프리셋 저장 — 6/6, 콘솔이 답한 이름 그대로

    pool_before: DataPool/PresetPools/2 · childCount 0
    sent: POS.01~06 전부 is_error False
    pool_after : childCount 6

    POS01 보컬 센터 페이스 · 합성좌표
    POS02 무대 전체 커버 · 합성좌표
    POS03 밴드 라인 백 · 합성좌표
    POS04 틸트업 스타트 (무대 안쪽) · 합성좌표
    POS05 팬아웃 종점 (객석 상단) · 합성좌표
    POS06 센터 집중 (브리지) · 합성좌표

**`childCount 0` 을 부재로 읽지 않았다.** 같은 호출 형태로 형제 경로
`DataPool/PresetPools/4` 를 쳐서 `childCount 7` 을 받았다 — 계기가 0 이 아닌 값을
답할 수 있다는 확인(§2 의 대조군과 같은 호출).

라벨 꼬리는 **`· 합성좌표`** 다. `· 산출값` 은 조준값이 계산됐다는 뜻이라
「좌표는 실측인데 조준만 계산했다」로 읽힌다 — 이 리그의 좌표는 합성이고 그쪽이
더 강한 주장이다. 기본값은 `산출값` 그대로이고, 어느 꼬리를 다는지는 **좌표의
출처를 아는 쪽**(호출자)이 정한다.

## 5. 큐 preview — 여덟 개 중 전 행 해결은 1개, 실제 계획은 0개

정본 `LXSEQ_SAMPLE_01_Sugar_r3.cue-ex.csv` 18큐, `--action preview --limit 0`.
**콘솔에 apply 하지 않았다.**

| | 조인 수리 전 | 조인 수리 후 |
|---|---|---|
| `preset_slots_resolved` | 14 | **20** (+6 = POS 여섯) |
| 미해결 프리셋 | POS 6 + BM 4 + FX 6 + COL 1 = 17종 | **BM 4 + FX 6 + COL 1 = 11종** |
| 보류 행 | 30 | 28 |
| 여덟 중 전 행 해결 | 0 | **1 (Q010)** |
| `planned_cues` | 비어 있음 | 비어 있음 |

여덟 개 낱개:

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

**POS 를 무는 행은 여덟 개 전부에서 해결됐다.** 남은 것은 전부 다른 축이다.

그리고 `planned_cues` 가 빈 것은 실패가 아니라 **규격**이다 —
`LX-SEQ-SPEC-v2.1.md` §11.1 1행 「부분집합 금지」라 한 행이라도 보류면 배치 전체가
거절된다. 그래서 정직한 답은 **「여덟 중 0개가 콘솔에 갈 수 있다」**이고,
그 0 의 원인은 이제 좌표가 아니라 BM·FX·COL 이다.

## 6. 검증

### 6.1 회귀

| | 통과 | 건너뜀 |
|---|---|---|
| base(`origin/WT-pos-join` + rig-coords 머지, 자체 venv) | 10745 | 12 |
| 이 브랜치 | **10779** | 12 |

차이 **+34**, 전부 설명된다:

- `server/tests/test_spatial_explicit_arrange.py` 신규 **30**
- `test_lxseq_position_derive.py::TestConsoleDropsTheDotInLabels` 신규 **4**
- 수정한 검사 **2건은 제자리 수정**이라 수를 안 바꾼다
  (`test_its_schema_closes_the_preset_vocabulary` — 어휘가 `explicit` 하나 늘었고
  목록은 여전히 박혀 있다 · `test_the_label_leads_with_the_id_so_the_join_can_key_on_it`
  — 조인 키가 `POS.01` 에서 `POS01` 로 바뀌었고 왕복 단언을 더했다)

기준선은 리드 값을 옮기지 않고 **이 트리 이 커밋에서 자체 venv 로 다시 쟀다**
(`evidence/regress_base.txt`). 리드 값과 일치했다. 전수 판정은 PR 의 CI 런을 인용한다.

### 6.2 뮤테이션 — 9/9 사망, 사전 보호 0

`evidence/t224_mutation.py` 가 `evidence/mutation.txt` 를 만든다. 두 팔:
arm1 = 이 카드가 더한 검사, arm2 = **이 카드가 안 건드린** 기존 검사
(`test_spatial_arrange` · `test_spatial_context` · `test_lxseq_cue_mapper`).
`test_lxseq_position_derive` 는 이 카드가 수정했으므로 arm2 에서 뺐다 — 넣으면
「기존 상태에서는 못 잡는가」가 성립 자체를 안 한다.

| 뮤턴트 | arm1 | arm2 |
|---|---|---|
| M1 선언 대조 제거 | 2 | 0 |
| M2 미지 키 검사 제거 | 1 | 0 |
| M3 bool 좌표 검사 제거 | 1 | 0 |
| M4 양자화 우회 | 3 | 0 |
| M5 빈 꼬리 거절 제거 | 1 | 0 |
| M6 꼬리 인자 무시 | 1 | 0 |
| M7 조인 술어를 접두 일치로 무름 | 1 | 0 |
| M8 콘솔 형태 인식 제거 | 8 | 0 |
| M9 쓰기 라벨의 점 제거 되돌림 | 3 | 0 |

arm2 가 전부 0 이라 아홉 갈래 모두 **이 카드 전에는 아무도 안 지키고 있었다.**

🔴 **1회차에 M3 이 거짓 생존했다.** 치환 술어
`if isinstance(value, bool) or not isinstance(value, (int, float)):` 가 파일에
**세 번** 나오는데 `replace(old, new, 1)` 이 첫 출현(`_positive_number`)에 붙었다.
`assert mutated != original` 은 통과한다 — 치환은 실제로 됐고 **자리만** 틀렸다.
규약 §3.4 의 「적용 안 됨」 갈래가 **적용은 됐지만 다른 축**이라는 형태로 나온
것이고, 러너에 `assert original.count(old) == 1` 을 더해 기계화했다.

### 6.3 린트

변경 파일 전부 `ruff check` · `ruff format --check` 통과.

## 7. 안 잰 것 (Gaps)

- **이 좌표가 맞는 자리인지.** 합성이다. 리드가 감독 승인 아래 만든 값이고 현장
  보정이 전제다. 「무대에서 빔이 어디 떨어지는가」는 이 카드가 원리적으로 못 잰다.
- **`.` 삭제의 원인.** `pool.slot` 구분자라는 것은 **추정**이다. 다른 문자
  (`/` · `:` · `,`)가 어떻게 되는지 안 쐈다 — 콘솔 쓰기를 늘리지 않으려고 안 쟀다.
- **다른 풀에서도 점이 지워지는지.** Position 풀에서만 쟀다. Color·Dimmer·Beam
  풀에 점 든 라벨을 안 써 봤다.
- **기존에 점을 들고 저장된 라벨이 어딘가 있는지.** 이 회차가 만든 여섯 개는
  덮어썼다. 다른 풀·다른 쇼파일은 안 봤다.
- **POS.02 의 (C) 여부.** t221 §5 가 「면이 아니라 선」을 의심했다. 좌표가 찼으니
  이제 잴 수 있는데 **안 쟀다** — 이 카드 범위 밖이고, `spread_floor` 의 착지점이
  무대 의미와 맞는지는 사람이 봐야 한다.
- **POS.03·04 의 「전원 한 값」이 무대에서 맞는지.** §3.1 대로 원인은 규칙이라고
  읽었고, 그 판독이 옳은지는 실기 관찰이 필요하다.
- **기종별 Pan/Tilt 물리 가동범위.** t221 §4 의 gap 그대로다. `135.0°` 상수는
  여전히 다른 리그의 값이고, 좌표가 찼으니 이제 이 상수가 「도달 불가」 판정의
  **유일한** 근거다. 이번엔 아무 행도 그 한계에 안 걸려서 노출되지 않았을 뿐이다.
- **BM·FX·COL 조인.** 미해결 11종을 **세기만** 했다. 왜 안 풀리는지(프리셋이 콘솔에
  없는지, 시트가 안 실렸는지, 조인 술어 문제인지)는 안 갈랐다. 별 카드감이고
  리드가 그렇게 정했다.
- **큐 apply.** preview 만 돌렸다. `Sequences/3` 에 아무것도 안 넣었다.
- **복원 번들의 실제 동작.** 258줄을 확보했지만 **쏴 보지 않았다** — 안전장치를
  발사해서 확인하지 않는다.
- **t222 의 `degenerate_rig` 가드와의 상호작용.** PR #271 이 미머지라 이 베이스에
  없다. 좌표가 폭을 가지므로 안 걸릴 것으로 읽지만 **합쳐서 안 돌려 봤다.**

## 8. 콘솔에 남긴 것

- `Patch/Stages/1/Fixtures/*` 의 `Posx/Posy/Posz` — 86대. 이전 값은 전부 `0.0`,
  복원 번들 `evidence/restore_bundle.txt` 258줄.
- `DataPool/PresetPools/2` — 프리셋 6개(슬롯 1~6). 이전 `childCount 0`.

건드리지 않은 것: `Sequences/2`·`/3`, `PresetPools/1`·`/4`·`/21`,
오늘의 프로브 잔여물(`4 'eset1Fade'` · `9 'T215 SCRATCH DELETABLE'` · `2000`).

## 9. 증거 파일

    evidence/regress_base.txt              base 회귀 10745/12
    evidence/regress_after.txt             이 브랜치 회귀 10779/12
    evidence/mutation.txt                  뮤테이션 9/9 (두 팔)
    evidence/t224_mutation.py              위를 만든 러너
    evidence/coords_preview_3.json         쓰기 전 3대 — 게이트 거절 확인
    evidence/coords_restore_bundle.json    쓰기 전 86대 백업 원문
    evidence/restore_bundle.txt            복원 명령 258줄
    evidence/coords_apply_3.json           3대 쓰기·되읽기
    evidence/coords_apply_86.json          86대 쓰기·되읽기
    evidence/pos_preview_after_coords.json 좌표 후 POS 산출 6/6
    evidence/pos_preview_synthetic_label.json  합성좌표 꼬리 preview
    evidence/pos_apply_6.json              1차 저장 — 점 삭제가 잡힌 자리
    evidence/pos_apply_6_dotless.json      2차 저장 — 왕복 바이트 동일
    evidence/cues_preview_after_pos.json   조인 수리 전 큐 preview
    evidence/cues_preview_after_join_fix.json  조인 수리 후 큐 preview
    evidence/_cue_count.py                 위 둘을 세는 스크립트
    evidence/_cue_eight.py                 여덟 큐 낱개 판정 스크립트
    evidence/debrace.sh                    하네스 Bash 가드 우회 보조(규약 §2)
