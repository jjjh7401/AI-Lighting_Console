# t186 1단계 — FID 축이 섹션 축을 이기는 자리: `map_groups` 271행

- 카드: t186 (1단계, **측정만**. 고치지 않았다)
- 워크트리: `.claude/worktrees/t186` · 브랜치 `WT-section-axis-masked`
- base: `419baf6` (착수 시점 `origin/main` 재확인)
- 대상: `server/lxseq/group_mapper.py`

## 1. 주장

S1 에서 섹션 사유가 사라지는 것은 **값이 덮여서가 아니라 술어가 호출되지 않아서**다.
`map_groups` 맨 앞 **271행**의 `if not console_fids_complete:` 가 무조건 이른 반환을
하고, 섹션 사유를 읽는 **382행** `section_refusal(groups_section)` 은 그 뒤에 있다.
FID 축이 시끄러우면 섹션 축은 **구조적으로 도달 불가**이며, 섹션 사유가 무엇이든
결과는 같다.

`GroupMapResult.refusal` 의 기본값이 `None`(147-162행)이라, 이른 반환은 그 필드를
건드리지 않고 기본값 그대로 내보낸다. 그래서 페이로드에서 「사유 없음」으로 보인다.

## 2. 증거

### 2.1 세 팔 — 자극은 한 축만

`groups_section` 은 S1·S2 에서 **바이트 동일**(`dict(reason="console_unreachable")`).
다른 것은 `console_fids_complete` 하나뿐이다. S3 는 계기가 눈멀지 않았음을 보이는 팔.

    PYTHONDONTWRITEBYTECODE=1 python3 .moai/reports/t186/probe_axis.py

| 팔 | console_fids_complete | 단면 | refusal | `section_refusal` 호출수 |
|---|---|---|---|---|
| S1 | False | 죽음 | `None` | **0** |
| S2 | True | 죽음 | `section_unread` | 1 |
| S3 | True | 정상 | `None` | 1 |

S2 원문: `refusal_detail = 단면을 못 읽었다: console_unreachable`

🔴 **S1 과 S3 의 `refusal` 은 바이트 동일한 `None` 인데 뜻이 반대다.**
S3 는 「물어봤고 단면이 멀쩡하다」, S1 은 「아무도 안 물어봤다」. 소비자는 이 둘을
가를 수단이 없다 — 호출수 0 은 페이로드에 안 실린다.

### 2.2 이기는 자리 — 줄 번호로

코드를 고치지 않고 line trace 로 실행된 줄을 그대로 받았다.

    PYTHONDONTWRITEBYTECODE=1 python3 .moai/reports/t186/probe_line.py

    S1 map_groups 실행 줄 : [271, 272, 273, 274, 275, 276, 272]
    S2 map_groups 실행 줄 : [271, 279, 280, ... , 357, 358, 382, 383, ... , 389, 383]
    S2 가 382 에 닿았나  : True
    S1 이 382 에 닿았나  : False

S1 은 271 에서 272-276(이른 반환)으로 빠지고 **그것으로 끝난다.** 271 이 이기는 자리다.

### 2.3 방향 판정 — 게이트는 안 움직인다

    PYTHONDONTWRITEBYTECODE=1 python3 .moai/reports/t186/probe_batches.py

    S1 batches = () | 배치수 = 0 | refusal = None
    S2 batches = () | 배치수 = 0 | refusal = section_unread

**두 팔 모두 배치 0.** 쓰기 계획은 이미 동일하고, 갈리는 것은 설명뿐이다.
그러므로 사유를 더 내보내는 처방은 **무르는 것도 조이는 것도 아니다** — 콘솔에
나가는 것이 바뀌지 않는다. 진단 품질 결함이지 안전장치 결함이 아니다.
판정은 리드 몫으로 남긴다(규약 §7).

## 3. 기준 귀속

- 트리: `.claude/worktrees/t186` @ base `419baf6`
- 카드가 준 t182 기준(`WT-groups-refusal-path` `87be9e6`, base `0fc0439`)은 **안 열었다.**
  이 회차의 결론은 전부 `419baf6` 의 정본 소스에 직접 건 측정이다.
- 파이썬 실행은 전부 `PYTHONDONTWRITEBYTECODE=1`(규약 §3.4 계기 오염 회피)

## 4. 범위

### 형제 매퍼는 순서가 반대다 — 같은 결함이 아니다

`server/lxseq/preset_mapper.py`: `section_refusal(pool_section)` 이 **284행**에 있고,
미완 판정(`names_incomplete`)은 **306-309행**으로 그 **뒤**다. 섹션 사유를 먼저 읽으므로
이 가림이 성립하지 않는다. `console_read_incomplete` 필드 자체가 없다(`grep -c` = 0,
파일은 400행으로 실재 — 부재의 대조군).

즉 **같은 저장소 안에 올바른 순서의 반례가 이미 있다.**

### 이 갈래를 지키는 검사는 없다

    grep -rn --include=*.py console_fids_complete=False server/tests/

매치 **1건**: `server/tests/test_lxseq_group_mapper.py:232`
`test_incomplete_console_read_yields_zero_batches` — 단언은 `batches == ()` 와
`console_read_incomplete is True` 둘뿐이고 **`refusal` 을 단언하지 않는다.**
게다가 기본(정상) 단면을 쓰므로 「FID 미완 + 단면 죽음」 조합 자체를 안 만든다.
대조군: `console_fids_complete=True` 는 2건 매치되므로 계기는 눈멀지 않았다.

카드의 「반대 방향은 아무도 안 지킨다」는 **참으로 확인**됐다.

## 5. 미검증 (gap)

- **카드 문면 한 곳을 좁혀야 한다.** 카드는 「섹션 축이 `console_unreachable` 을
  **계산했는데도**」라고 적었다. `map_groups` 안에서는 계산 자체가 없다(호출수 0).
  사유는 **상류에서 이미 계산되어 `groups_section` 안에 실려 들어온다** — map_groups 가
  그 입력을 안 읽을 뿐이다. 관측은 맞고 위치 서술만 한 칸 어긋나 있었다.
- 상류 `collect_rig_sections` 가 S1 조건에서 실제로 그 사유를 채우는지는 **안 쟀다.**
  이 회차는 `map_groups` 경계 안쪽만 봤다. 실기 콘솔 0회.
- `preset_mapper` 에 **다른 모양의** 가림 경로가 있는지는 안 쟀다. 잰 것은
  「이 결함과 같은 모양은 없다」까지다.
- 뮤테이션 0회 — 이번 회차는 검사를 추가하지 않았으므로 걸 대상이 없다.
  (규약 §3.3 은 **새로 만든 단언**에 걸라고 한다)
- `server/prechk/inventory.py` · `server/orchestrator/tools.py` 는 **안 건드렸다**
  (리드 경고: t187 과 머지 충돌 축).

## 6. 잔여 위험

- S1 은 카드 말대로 **현실적인 조합**이다. 픽스처 경로 하나가 죽으면 FID 판독과
  섹션 판독이 같은 경로를 타므로 둘 다 실패한다. 그때 사용자는 사유 없는
  「콘솔을 못 읽었다」만 받는다.
- 처방을 271 근처에 놓으면 **가장 싼 자리**라 공유 지점이다. 규약 §3.6 의
  「가장 싼 처방이 방금 살린 구별을 죽인다」가 정확히 이 모양이므로, 2단계에서는
  두 팔을 각각 죽여 **사유 문자열이 바이트 동일이 되지 않는지** 먼저 재야 한다.
