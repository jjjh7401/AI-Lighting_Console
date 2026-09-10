# t344 B — 능력 판독을 계획 단계 판정으로 배선한다

## Baseline-attribution

- 워크트리: `.claude/worktrees/t344b` (L1, `git worktree add -b WT-capability-verdicts … origin/main`)
- 기준 커밋: `d676a8e` (`origin/main`, t344 A 편 머지 직후)
- 브랜치: `WT-capability-verdicts`
- 측정 일자: 2026-09-11. 콘솔 쓰기 0 — 가짜 포트만 사용(실기 접속 없음).

## Claim

1. **조인 키는 이 저장소에 존재한다.** 배차 전제 「fid↔기종 조인 키가 이 경로에 없다」는 틀렸다.
2. 팬/틸트 없는 기종은 계획 단계에서 **이름 대어** 거절된다.
3. 측정 범위 밖 값은 **보류**되고 사유에 측정 범위가 실린다(clamp 없음, 역방향 안전).
4. `session.py` 의 `patch=[]` 리터럴이 사라지고 콘솔 판독이 그 자리에 들어갔다.

## Evidence

### (1) 조인 키 — 코드 실측

```
$ grep -n "^FIXTURE_ROOT" server/prechk/inventory.py
52:FIXTURE_ROOT = "Patch/Stages/1/Fixtures"
$ grep -n "FID_FIXTURE_ROOT" server/vwx/patchplan.py | head -1
44:FID_FIXTURE_ROOT = "Patch/Stages/1/Fixtures"
```

두 판독이 **같은 슬롯 도메인**을 쓴다. `vwx.patchplan.read_existing_fids` 는 슬롯마다
`FID` 프로퍼티를 실제로 읽고 `ExistingFidRead.fid_slots: tuple[(slot, fid), …]` 로
슬롯과 값을 **함께** 나른다(`patchplan.py:1527` 주석 round23 R21-A, `:1620` 반환).
따라서 `read_inventory().fixtures[*].slot -> (fixture_type, mode)` 와 슬롯으로 맞물려
`fid -> (타입, 모드)` 가 **추측 없이** 나온다.

`prechk.inventory` 가 FID 를 화이트리스트 밖에 둔 것은 그 모듈의 **정책**이고
(`inventory.py:216 fid_note` 독스트링) 콘솔 한계가 아니다 — 배차서가 「미측정」이라 한
축이 이것이며, 코드 실측으로 **정책 쪽**임이 확정됐다.

동작 증거(가짜 포트, 슬롯 2·5 ↔ FID 41·42):

```
$ uv run pytest server/tests/test_capability_verdict.py::TestJoinKey -q
..                                                                       [100%]
2 passed
```

### (2) 판정 + 대조군 + 뮤테이션

```
$ uv run pytest server/tests/test_capability_verdict.py -q
............................                                             [100%]
28 passed in 0.72s
```

뮤테이션 4건, 전부 관측:

| 뮤테이션 | 결과 |
|---|---|
| `patch=list(rig_read.patch)` → `patch=[]` (session.py 회귀) | `1 failed` — `TestWiredCallSite::test_the_call_site_hands_the_console_read_to_build_rig_profile` |
| `low=min/high=max` → `low=first/high=second` (역방향 무시) | `4 failed` — `TestReversedZoomRange::test_in_range_values_pass_on_a_descending_axis[5.0/20.0/42.0]` + 1 |
| 어휘 `any(` → `all(` (1차, 대조군 없음) | `27 passed` — **살아남았다.** Pan 전용 대조군을 추가해 재실행 |
| 어휘 `any(` → `all(` (2차, 대조군 추가 후) | `1 failed` — `TestVocabulary::test_position_is_any_of_not_all_of` |

### (3) 회귀 + 전량

```
$ uv run pytest server/tests/test_capability_read.py server/tests/test_capability_join.py -q
25 passed in 0.06s

$ uv run pytest server/tests/test_design_without_coordinates.py server/tests/test_design_needs_coordinates.py -q
21 passed in 4.16s

$ make ci-local ; echo "EXIT=$?"
EXIT=0        (성공 시 무출력 — Makefile:80 의 설계)

$ uv run pytest -q -x -p no:cacheprovider
12146 passed, 35 skipped, 1 warning in 195.89s (0:03:15)
```

`make ci-local` 은 **전량이 아니다**(Makefile:22-24 — 20초 목표의 빠른 미러). 그래서
전량을 따로 돌렸고 위 숫자가 그 결과다.

## 무엇을 배선했는가

- 새 파일 `server/design/capability_verdict.py` — 어휘 표(의도적 부분집합) + `position_verdict` + `range_verdict` + `patch_records`
- 새 파일 `server/design/rig_capability_read.py` — 콘솔→능력 조인 진입점 + 결손 코드 3종 + 고지
- `server/web/session.py:~7999` — `patch=[]` → `patch=list(rig_read.patch)`; 팬/틸트 전무 리그는 t311 의 `skipped_steps=(Q4_SPATIAL_STORY,)` **같은 기제**로 Q4 를 건너뛴다(두 번째 기제를 만들지 않았다)

`"effect"`(`energy.EFFECT_AXIS_CAPABILITY`)는 **일부러 매핑하지 않았다** — 어떤 속성이
이펙트 축을 여는지 측정된 바가 없고, 지어 넣으면 `energy.axis_budget` 이 추측 위에서
이펙트 어휘를 연다. 시험이 그 부재를 못박는다(`test_the_effect_capability_is_deliberately_unmapped`).

## Gaps — 재지 않은 것

- **실기 콘솔에서 이 배선을 돌리지 않았다.** 전부 가짜 포트다. 실기에서
  `read_existing_fids` + `read_inventory` + 능력 판독을 연달아 돌린 왕복 비용·절단
  거동은 미측정이다(리그 15기종·수십 fid 기준의 실제 왕복 수를 모른다).
- **`range_verdict` 에 프로덕션 호출자가 없다.** 이 카드는 판정 함수와 시험까지만
  냈다 — 큐시트가 요구하는 Zoom 값을 어디서 읽어 대조할지는 시트 파서 쪽 결정이고,
  그 배선은 후속이다. 즉 (2b)는 **부품이 초록이고 경로는 안 이어졌다** 상태이며
  이 문장이 그 고지다.
- **`groups` 는 여전히 `{}`** — 그룹 판독은 이 경로에 없고 리그는 단일 레이어로
  내려간다(원래 RG5 고지 그대로). 이 카드는 그것을 건드리지 않았다.
- **전체 어휘 표 미작성** — Pan/Tilt/Zoom 셋만 매핑했다. 나머지 속성(Frost·Gobo·
  Prism·Color 계열)은 소비자가 없어 안 넣었다.
- **`whole_unconfirmed`/`completeness` 갈래의 실기 빈도 미측정** — 가짜 포트에서만
  두 값을 만들어 봤다.
- **`_design_coord_notice` 의 결합 문면**(` / ` 이어붙이기)이 UI 에서 어떻게 줄바꿈
  되는지 브라우저 실측 없음.

## Residual-risk

- `read_design_rig` 의 `except Exception` 은 넓다. 층 경계상(`server/design` 은
  `server.safety` 를 임포트할 수 없다) 예외 형태를 모르기 때문이지만, 이 안에서
  발생한 **프로그래밍 오류도** `rig_unreadable` 로 번역된다 — `detail` 에
  `type(error).__name__` 을 실어 구별 가능하게 뒀으나 정적으로 막지는 못한다.
- 슬롯→FID 판독이 부분이면 그 슬롯이 patch 에서 빠진다. 고지는 나가지만
  `build_rig_profile` 은 **줄어든 리그**를 보므로 `budget_scale_factor` 가 실제보다
  낮게 나올 수 있다(보수적 방향이라 큐가 과해지지는 않는다).
- 한 기종의 두 모드가 서로 다른 축을 가지면 `position_verdict` 는 **가능**을
  택한다(`allowed` 가 `refused` 를 이긴다). 그 기종의 어떤 모드는 실제로 못 움직일
  수 있고, 그때 거절이 한 단계 늦게(프리셋 발사 시점) 걸린다.
- 전량 195.89s 는 이 기계 한 대·한 회차다. flake 여부는 1회 실행으로 판정 못 한다.
