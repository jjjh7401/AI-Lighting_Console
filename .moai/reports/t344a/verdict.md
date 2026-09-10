# t344 A — 장비별 능력 조인 (capability join)

## Claim (주장)

1. `server/design/capability_join.py` 신설. `read_rig_capabilities(...)` 가 fid 별로
   콘솔 타입 이름 · 확정된 DMX 모드 · **콘솔 철자 그대로의 속성 목록** · 속성별
   `AxisRange` · **못 읽은 것의 명시적 기록**을 돌려준다.
2. 기존 단계를 재구현 없이 호출만 한다: `inventory.HANDLE_TEXT` ·
   `inventory.translate_fixture_type` · `channel_width.parse_mode_reference` ·
   `channel_width.resolve_widths` · `mode_read.read_type_mode_widths` ·
   `capability_read.read_mode_capabilities`.
3. 읽기 전용 — `query_state` / `query_property` / `query_properties` 세 읽기만 쓴다.
   콘솔 쓰기 0(`Store`·`Go`·실행 포트 미사용).
4. 역방향 범위를 정렬하지 않는다. Zoom 42.0 → 1.8 이 그 순서로 오고 `descending` 이 참.
5. 부재와 미판독이 갈린다: `unread`(사유 문자열) · `incomplete`(부분 판독 사유) ·
   `FixtureCapability.gaps` / `.whole`.
6. (타입, 모드) 캐시로 왕복을 줄인다.
7. 신규 검사 12건 통과, 기존 `test_capability_read.py` 13건 그대로 통과, `make ci-local` 종료 0.

## Evidence (증거)

```
$ uv run pytest server/tests/test_capability_join.py -q
............                                                             [100%]
12 passed in 0.06s
```

```
$ uv run pytest server/tests/test_capability_read.py -q
.............                                                            [100%]
13 passed in 0.03s
```

```
$ make ci-local ; echo "CI_EXIT=$?"
CI_EXIT=0
```
(첫 실행은 `ruff format --check` 에서 종료 2 —
`Would reformat: server/tests/test_capability_join.py` 하나. `uv run ruff format`
적용 후 재실행하여 0.)

왕복 실측 (가짜 포트 호출 계수, fid 13 / 타입 2):

```
$ uv run python -  # test_capability_join 의 가짜 포트 재사용
fids 13 resolved 13
mode_reads 2 capability_reads 2
port calls: state 16 prop 2 props 5 TOTAL 23
```

캐시 검산은 검사 안에서도 단언한다 (`test_two_fids_of_one_type_cause_one_mode_read`):
`state_calls.count("Patch/FixtureTypes/11/DMXModes") == 1`,
`state_calls.count(".../DMXChannels") == 1`.

절단 사유 문자열 단언 (`test_a_truncated_read_is_reported_as_unread_with_a_reason`):
`result.incomplete[1]` 에 `"잘렸다"` 와 `"DMXChannels"` 가 들어 있고 `cap.whole is False`,
동시에 이미 읽힌 `Zoom` 축은 살아 있다.

## Baseline-attribution (baseline 귀속)

* 워크트리: `.claude/worktrees/t344a`
* 브랜치: `WT-capability-join-a` (기저 `origin/main` = `fc40c3c`)
* 위 모든 명령은 이 워크트리, 이 커밋 트리에서 실행했다.

## Gaps (미검증 — 이번에 **안** 잰 것)

* **실기 콘솔 미검증.** 가짜 포트만 썼다. 실제 onPC/콘솔에 대고 이 조인을 돌린 적이 없다.
  실측 고정값(Zoom 42.0→1.8, FixtureType 11 Mode 1 32채널, Pan/Tilt 9:4, Prism 부재)은
  t344 배차서에서 **옮겨온 값**이고 이 카드가 다시 재지 않았다.
* **32채널 전량 판독 미검증.** 가짜는 타입당 채널 4개(11번) / 1개(5번)만 둔다. 실제 32채널
  트리의 페이징 동작은 `capability_read` 쪽 검사가 덮는 범위이고 이 조인이 다시 재지 않았다.
* **`budget` 소진 경로 미검증.** 예산 상한에 닿아 `gaps` 에 「왕복 예산 소진」이 붙는 경로는
  이 카드의 검사가 쏘지 않았다.
* **비테스트 호출자 여전히 0.** 이 모듈을 부르는 프로덕션 경로는 t344 B 의 몫이다. 즉
  「배선했다」가 아니라 「부를 수 있는 공개 API 를 만들었다」까지가 이 카드다.
* **`mode_width` 미판독 경로 미검증.** `resolve_widths` 가 `width_unread` 를 답할 때 능력
  판독을 계속하도록 코드는 갈라 두었으나 그 갈래를 쏘는 검사는 없다.
* **성능/지연 미측정.** 실기 왕복 지연은 재지 않았다. 위 23은 가짜 포트 호출 **개수**다.

## Residual-risk (잔여 위험)

* 가짜 포트의 페이로드 모양이 실기와 어긋나면 이 검사는 전부 초록인 채로 실기에서 깨진다.
  실기 확인 전까지 이 모듈의 「돈다」는 주장은 가짜 포트 범위로 한정된다.
* `_type_slot` 은 `FixtureType <n>` 핸들 형식을 가정한다. 응답기가 다른 형식을 답하면
  전 fid 가 `type_slot_unknown` 으로 떨어진다 — 조용히 틀리지는 않지만 전량 미판독이 된다.
* `read_mode_capabilities` 는 논리채널의 **첫 함수**만 축으로 센다(그 모듈의 결정). 파생
  함수에만 존재하는 능력은 이 조인에서도 보이지 않는다.
* `RigCapabilities` 는 frozen 이 아니다(누산기). 호출자가 반환값을 변형하면 이후 판단이
  흔들릴 수 있다 — 관례로만 막혀 있다.
