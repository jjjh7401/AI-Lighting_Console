## Spatial design — firing the rig in the ORDER it is hung

The choreography section sets VALUES on a selection. Spatial design decides what
that selection's ORDER is, so that "a wave from stage left" comes out different
on one long bar than on a three-row grid instead of identical on both. Every
command in this section was validated live on onPC 2.4.2.

### The principle — direction is selection order, not coordinates (measured)

A phaser fans its phase across the SELECTION, in selection order. MA3 has no
built-in "build a selection grid out of the rig's real positions", so the order
is what you have to build: read the patch coordinates, sort the fixture ids by a
stage axis, and utter the selection in that sorted order.

This was measured, not assumed. With the coordinates and every phaser line held
IDENTICAL, and only the selection chain reversed, the observed wave reversed
with it. So:

- A coordinate is an INPUT to the sort. It never appears in a programming
  command — there is no MA3 grammar that would accept one, and a wave aimed the
  wrong way looks like a working wave in every log.
- Reversing the chain is the whole reversal mechanism. Do not reach for a
  negative phase span to flip a spatial wave when the order can flip instead.

### Step 1 — read the positions: `get_spatial_context`

Fixture positions live in the patch, not in the rig snapshot, so
`get_rig_context` cannot answer this question. `get_spatial_context` returns one
entry per fixture — its real fixture id, its name and its three stage
coordinates — alongside the reads that failed and whether the answer was cut
short.

Three things in that reply change what you do next:

- A fixture that could not be read comes back in the UNREADABLE list, with a
  reason, instead of in the coordinate list. It is not a fixture sitting at the
  origin: do not put it in the chain, and do not fill a coordinate in for it.
- A truncated or round-trip-capped reply is a PARTIAL rig. A chain built from it
  has holes, so say the read was cut short rather than presenting the short
  chain as the whole rig.
- Every fixture reading the SAME point means the show is patched but was never
  positioned. That is a successful read, not a missing one, and there is no
  spatial order to be had from it — fall back to the non-spatial choreography
  patterns and say why, rather than sorting fixture ids and calling the result
  a wave from stage left.

### The sort vocabulary — four names, closed

| sort | order | Korean qualifiers |
|---|---|---|
| `left_to_right` | x ascending, within each detected row | 왼쪽에서 오른쪽(으로), 좌에서 우로 |
| `right_to_left` | x descending, within each detected row | 오른쪽에서 왼쪽(으로), 우측에서 좌측으로 |
| `center_out` | outward from each row's midpoint | 가운데부터 바깥으로, 센터에서 양옆으로 |
| `diagonal` | row order and within-row order combined into one sweeping wavefront | 대각선(으로), 사선 |

The list is closed. An instruction that names none of them is not a spatial
instruction — program it with the ordinary choreography patterns. An instruction
that names TWO ("대각선으로 왼쪽에서 오른쪽") has named none of them: ask which
one is meant instead of picking whichever was recognised first.

### Step 2 — the recipe: sort, select, phaser (validated)

```
ChangeDestination Root
ClearAll
Fixture <first fid> + Fixture <next fid> + ... + Fixture <last fid>
Attribute 'Dimmer' At 0
Step 2
Attribute 'Dimmer' At 100
Attribute 'Dimmer' At Phase 0 Thru 360
Attribute 'Dimmer' At Speed 30
ClearAll
```

- The chain is ADDITIVE and one `Fixture` keyword per element — `Fixture <a> +
  Fixture <b>`, never a `Thru` range. A range is a numeric span, and the order
  the sort computed is exactly what a span throws away.
- Every element of the chain is a real fixture id that came back from the read,
  and the elements stay in the order the sort returned them. Do not re-sort,
  de-duplicate or tidy the chain on the way out: the order IS the direction.
- The chain and the phaser are one bundle. Selection is programmer state, so it
  does not survive the closing `ClearAll` — a later bundle rebuilds the order
  rather than referring back to it.
- To reverse the wave, reverse the sort (`left_to_right` <-> `right_to_left`)
  and re-utter the chain. Nothing else in the bundle changes.

### A phaser needs TWO steps (measured)

The two dimmer lines either side of `Step 2` are not decoration. A phaser fans
phase ACROSS steps, so a single static value has nothing to fan.

Measured: a bundle that set one value and then applied `At Phase 0 Thru 360` to
it returned ok on every single line and left the stage lit and MOTIONLESS. Ok on
a phaser line means the line parsed, never that anything is moving. Always build
the low value, `Step 2`, then the high value, and only then spread the phase and
set the speed.

### 위치와 조준은 다른 축이다 — 먼저 가른다 (measured)

무대의 장비에는 **서 있는 자리**와 **바라보는 방향**이라는 두 축이 있다. 둘은
다른 데이터고, 다른 명령이고, 되돌리는 방법도 다르다.

| | 패치 좌표 (위치) | Pan/Tilt (조준) |
|---|---|---|
| 뜻 | 장비가 무대 **어디에** 있나 | 머리가 **어디를** 보나 |
| 단위 | 미터 (무대 원점 기준) | 도(°) |
| 사는 곳 | 패치 — 쇼파일 구조 | 프로그래머·큐 값 |
| 바꾸면 | 무대 도면이 바뀐다 | 빔 방향만 바뀐다 |
| 명령 형태 | `Set Fixture <fid> Posz ...` (도구가 만든다) | `Attribute Pan At <n>` |
| 도구 | `arrange_fixtures` | 조준 계산 후 `run_commands` |

높이·배치·이동·트러스 위치는 **위치 축**이다. “6미터로 올려”, “원래 높이로
되돌려”, “한 줄로 배치해”는 전부 `arrange_fixtures`다. Pan/Tilt로는 장비를
옮길 수 없다 — 고개만 돌아가고 자리는 그대로다. 조준은 “어디를 비춰라”,
“무대 중앙을 봐라”처럼 **바라보는 대상**이 있을 때만이다.

되돌리기 요청(“원래대로”, “되돌려줘”)은 **직전에 바꾼 그 축**으로 되돌린다.
높이를 바꿨으면 높이로 되돌리고, 조준을 바꿨으면 조준으로 되돌린다. 축을
갈아타면 요청은 이행되지 않은 채 엉뚱한 값이 콘솔에 남는다.

#### 좌표 쓰기 문법은 도구가 소유한다

좌표 쓰기는 `Set Fixture` 로 시작해 축 이름 `Posx`·`Posy`·`Posz` 가 오고, 값이
**작은따옴표에 싸인** 한 가지 형태뿐이다.

```
Set Fixture <fid> Posz '<metres>'
```

**작은따옴표는 장식이 아니다.** onPC 2.4.2 실측에서 다섯 형태 중 셋이
`ok:true` 를 답하면서 틀린 값을 저장했다 — 따옴표 없는 음수는 부호를 잃었고,
부호와 숫자 사이에 빈칸이 있으면 아무것도 저장되지 않았으며, 앞에 영을 붙인
형태는 영으로 저장됐다. 무대 원점 왼쪽은 전부 음수라 이 함정은 예외가 아니라
주 경로에 있다.

그래서 이 형태를 **손으로 쓰지 않는다.** `arrange_fixtures` 가 이 문법을 만들고,
쓰기 전 원좌표를 백업하고, 쓴 뒤 되읽어 수치로 비교한다. `run_commands` 로
직접 좌표를 쓰면 그 세 가지가 전부 사라진다. 이 형태를 여기 적어 두는 이유는
**무엇이 위치 명령인지 알아보기 위해서**이지, 직접 조립하기 위해서가 아니다.

### 3D 레이아웃·시뮬레이션·배치·이동 요청

사용자가 **3D**, **레이아웃**, **시뮬레이션**, **배치**, **이동**, 높이, 트러스,
행·격자·원형을 말하면 이는 장비의 실제 무대 좌표 작업일 수 있다. 익스큐터
레이아웃과 혼동하지 말고, 먼저 `get_spatial_context`로 패치 3D 좌표와 실제 FID를
읽는다. 목록이 잘렸거나 좌표를 읽지 못한 장비가 있으면 전체 장비 배치라고
말하지 않는다.

요청을 다음의 짧은 작업어로 정리해 도구를 고른다.

| 사용자 요청 요약 | 수행 |
|---|---|
| 3D 레이아웃 보기·시뮬레이션 확인 | `get_spatial_context` |
| 일렬·격자·원형으로 배치 | `arrange_fixtures`에 `row`·`grid`·`circle`과 읽은 FID 전달 |
| 현재 위치를 유지하고 바닥에서 N m 높이로 이동 | `arrange_fixtures`에 `elevation`, 읽은 FID, `height: N` 전달 |

`elevation`은 각 장비의 현재 x/y를 보존하고 z만 바닥 기준 절대 높이로 바꾼다.
예를 들어 “모든 장비를 바닥에서 5m 높이로 올려”는 완전한 공간 좌표 응답의
모든 FID와 `height: 5`를 쓴다. “5m 올려”처럼 절대 높이인지 상대 이동인지
불명확하면 쓰기 전에 의미를 확인한다. 좌표 쓰기는 쇼파일을 바꾸므로 명시 요청에만
수행하고, 승인·백업·읽기 검증이 끝난 뒤에만 성공으로 보고한다.

### 헤드를 무대 좌표로 향하게 하기 — Pan/Tilt 조준 (measured)

`Attribute 'Pan' At <n>` / `Attribute 'Tilt' At <n>` 의 값은 **물리 각도(도)**다 —
퍼센트가 아니다. 라이브 계측으로 확정한 규약 (패치 회전 전부 0 기준):

- Pan 0 / Tilt 0 = 빔이 수직 아래(무대 −Z).
- Tilt 양수 = 빔이 무대 +Y(업스테이지) 쪽으로 기움 (Pan 0 기준).
- Pan 양수 = 그 기울임 방향을 위에서 봐서 반시계로 회전 (+Y → −X at +90).
- 패치 바디 회전 `Rotz r` 은 Pan 기준틀을 같은 방향으로 돌린다 — 필요한
  Pan에서 r을 뺀다. `Rotx`/`Roty` 는 미계측: 0이 아니면 조준을 계산하지 말고
  말하라.
- 음수 값은 따옴표 없이 그대로 동작한다 (`At -150`). 패치 좌표 쓰기의
  작은따옴표 규칙과 다른 채널이다.

픽스처 위치 F에서 목표 T를 향하는 값은, v = T − F 로 두고 tilt는
`acos(-v_z / |v|)`, pan은 `atan2(-v_x, v_y) − Rotz` (−180..180 정규화)다.
픽스처마다 값이 다르므로 반드시 **한 대씩 선택 → 속성** 순서로 묶는다:

```
Fixture <fid>
Attribute 'Dimmer' At 100
Attribute 'Pan' At <pan degrees>
Attribute 'Tilt' At <tilt degrees>
```

- 목표와 같은 좌표에 있는 오브젝트(원점 마커 등)는 방향이 정의되지 않는다 —
  제외하고 그렇게 말하라.
- 계산된 tilt가 헤드 가동범위(약 135도)를 넘으면 clamp하지 말고 제외·보고한다.
- 서버 구현: `server/spatial/pointing.py` (`aim_pan_tilt`, `pointing_commands`).

### 연출 의도 → 포지션 어휘 (추천 기본값)

사용자가 기법 이름 없이 무드·장면만 말할 때, 아래 관례 매핑을 추천의
출발점으로 쓴다. 단정해 바로 실행하지 말고 ask_user로 한 번 확인하라 —
매핑은 관례이지 취향의 대체가 아니다.

| 연출 의도 | 추천 포지션 | 이유 |
|---|---|---|
| 발라드·잔잔·보컬·솔로 | 다운스테이지 보컬 지점 포커스 | 시선을 사람에게 모은다 |
| 오프닝·등장·드라마틱 | 센터 한 점 수렴 | 한 점 수렴 = 시선 고정 |
| 웅장·장엄·피날레 | 중심축 위 수렴 콘 | 규모감의 관례적 표현 |
| 신나는·후렴·클럽·드롭 | 교차빔 | 에너지 큰 구간의 표준 룩 |
| 화려·개방·펼침 | 부채살(팬, 필요시 틸트 V 추가) | 개방감과 스케일 |
| 관객 호응·싱어롱 | 객석 방향 | 호응 유도 관례 |
| 합창·배경·장벽 | 전 대 동일 각도의 평행 빔 커튼 | 장면 뒤를 세우는 룩 |
| 전환·대기·리셋 | 수직 아래 홈 | 안전한 파킹 |

저장된 Position 프리셋(이름: Home, Wall, Audience, Center, Vocal DSC,
Fan Out, Fan In, Cross, Ring Out, Ring In)이 이미 있으면 값을 다시 계산하지
말고 그 프리셋을 리콜해 큐를 빌드하라 — 프리셋 참조로 저장된 큐는 프리셋
재생성만으로 전체가 따라온다.

### What never reaches the command line

- Coordinates, in any form. They are the sort's input.
- A fixture id the read did not return.
- A double-quote character — this transport rejects it outright. MA3 attribute
  names go in SINGLE quotes, exactly as they do everywhere else in the rulebook.
