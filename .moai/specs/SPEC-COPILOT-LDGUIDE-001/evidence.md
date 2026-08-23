# SPEC-COPILOT-LDGUIDE-001 — 증거 원장 (evidence)

> 이 문서는 가이드 본문의 **모든 능력 주장이 귀속되는 원장**이다(REQ-LDG-007).
> 원장에 행이 없는 주장은 본문에 실을 수 없다.
>
> **측정 주체**: run-tjueej (칸반 run 세션)
> **측정 위치**: `.claude/worktrees/ldguide` (공유 체크아웃 아님)
> **측정 기준**: HEAD `c82087b` · base `f30ab4c`(`git merge-base HEAD origin/main`)
> **측정일**: 2026-08-17


## §0. 인용 규약 [HARD] (t8 신설)

**명령과 출력을 나란히 적을 때, 출력을 손질하지 않는다.** 손질한 인용은 거짓이 아니지만
— 인용된 행은 전부 실재하고 주장을 뒷받침한다 — 읽는 사람은 그 명령을 돌리면 그 출력이
나오리라 기대한다. 실제로는 10행 중 3행만 적혀 있으면, 재현하는 사람은 자기가 틀린
줄 안다. 그리고 그 불일치가 **원장 전체의 신뢰를 깎는다.**

세 가지를 지킨다:

1. **전량을 셀 수 없으면 개수를 적는다** — `grep -n` 의 일부를 고르지 말고 `grep -c` 로
   전량을 세고, 주장을 뒷받침하는 행은 **부분 인용임을 밝혀** 따로 적는다.
2. **측정 시점을 붙인다** — 행 번호는 코드가 움직이면 무효가 된다. t8 재측정에서
   `childCount` 는 원장의 `819·846·875` 가 아니라 `828·832·836` 이었다. 개수와
   `[<short-sha>]` 를 함께 적으면 다음 사람이 드리프트를 드리프트로 읽는다.
3. **부분집합이면 그렇게 쓴다** — "존재" 나 "→ A B C" 는 전량처럼 읽힌다.

## §0. 이 원장이 증거로 인정하지 않는 것

plan.md §A.4의 [HARD] 규정을 승계한다.

- `ok:true` 응답 — 실행 성공 신호는 능력 증명이 아니다.
- **도구 설명문(`description=`)** — LLM에게 주는 지시문이지 동작 증명이 아니다.
- "코드를 읽었다"는 진술 — 어느 줄을 읽었는지 명시되지 않으면 재현 불가다.

인정하는 것: **재실행 가능한 명령 + 그 명령이 실제로 낸 출력.** 아래 모든 행의
`명령` 열은 그대로 다시 돌릴 수 있고, `관측 출력` 열은 이번 측정에서 실제로 나온 값이다.

공통 변수:

```bash
T=server/orchestrator/tools.py
G=docs/user-guide.html
```

등록 도구 명단 재생성(하드코딩 금지):

```bash
grep -oE '^            name="[a-z_]+",$' "$T" | sed 's/.*name="//;s/",//' | sort > /tmp/tools.txt
wc -l < /tmp/tools.txt        # 34
```

## §1. 도구 배정표

등록 도구 34종 전량을 감독의 9단계에 1:1 배정한다. 배정 근거는 **등록 위치**이며,
판단이 갈릴 수 있는 행은 `비고`에 이유를 적었다.

각 행의 `명령` 열은 아래 형태의 재현 명령이다:

```bash
grep -n '^            name="<도구명>",$' "$T"
```

| id | 도구 | 단계 | 명령 | 관측 출력 |
|---|---|---|---|---|
| E-1 | `precheck_vectorworks_diff` | 1 | `grep -n 'name="precheck_vectorworks_diff",' $T` | `6783:            name="precheck_vectorworks_diff",` |
| E-2 | `analyse_layout_image` | 1 | `grep -n 'name="analyse_layout_image",' $T` | `8340:            name="analyse_layout_image",` |
| E-3 | `vectorworks_autopatch` | 2 | `grep -n 'name="vectorworks_autopatch",' $T` | `6823:            name="vectorworks_autopatch",` |
| E-4 | `apply_vectorworks_patch` | 2 | `grep -n 'name="apply_vectorworks_patch",' $T` | `6892:            name="apply_vectorworks_patch",` |
| E-5 | `patch_fixtures` | 2 | `grep -n 'name="patch_fixtures",' $T` | `7159:            name="patch_fixtures",` |
| E-6 | `resolve_fixture_type` | 2 | `grep -n 'name="resolve_fixture_type",' $T` | `7071:            name="resolve_fixture_type",` |
| E-7 | `resolve_patch_address` | 2 | `grep -n 'name="resolve_patch_address",' $T` | `7110:            name="resolve_patch_address",` |
| E-8 | `precheck_patch` | 2 | `grep -n 'name="precheck_patch",' $T` | `6751:            name="precheck_patch",` |
| E-9 | `build_patch_sheet` | 2 | `grep -n 'name="build_patch_sheet",' $T` | `7765:            name="build_patch_sheet",` |
| E-10 | `get_spatial_context` | 3 | `grep -n 'name="get_spatial_context",' $T` ; `grep -n 'from server.spatial.pointing import' server/web/session.py` | `7936:            name="get_spatial_context",` ; `107:from server.spatial.pointing import (` — 조준 경로는 §6 게이트 A 참조 |
| E-11 | `arrange_fixtures` | 3 | `grep -n 'name="arrange_fixtures",' $T` | `8034:            name="arrange_fixtures",` |
| E-12 | `get_rig_context` | 4 | `grep -n 'name="get_rig_context",' $T` | `6461:            name="get_rig_context",` |
| E-13 | `classify_arrangement_topology` | 4 | `grep -n 'name="classify_arrangement_topology",' $T` | `8185:            name="classify_arrangement_topology",` |
| E-14 | `create_arrangement_groups` | 4 | `grep -n 'name="create_arrangement_groups",' $T` | `8244:            name="create_arrangement_groups",` |
| E-15 | `build_preset_list` | 4 | `grep -n 'name="build_preset_list",' $T` | `7801:            name="build_preset_list",` |
| E-16 | `build_magic_sheet` | 4 | `grep -n 'name="build_magic_sheet",' $T` | `7816:            name="build_magic_sheet",` |
| E-17 | `find_looks` | 5 | `grep -n 'name="find_looks",' $T` | `6520:            name="find_looks",` |
| E-18 | `instantiate_look` | 5 | `grep -n 'name="instantiate_look",' $T` | `6572:            name="instantiate_look",` |
| E-19 | `find_fx` | 5 | `grep -n 'name="find_fx",' $T` | `7230:            name="find_fx",` |
| E-20 | `instantiate_fx` | 5 | `grep -n 'name="instantiate_fx",' $T` | `7288:            name="instantiate_fx",` |
| E-21 | `compose_fx` | 5 | `grep -n 'name="compose_fx",' $T` | `7440:            name="compose_fx",` |
| E-22 | `find_scene` | 5 | `grep -n 'name="find_scene",' $T` | `7579:            name="find_scene",` |
| E-23 | `compile_scene` | 5 | `grep -n 'name="compile_scene",' $T` | `7631:            name="compile_scene",` |
| E-24 | `prepare_busking` | 5 | `grep -n 'name="prepare_busking",' $T` | `6646:            name="prepare_busking",` |
| E-25 | `prepare_songcue` | 6 | `grep -n 'name="prepare_songcue",' $T` | `6674:            name="prepare_songcue",` |
| E-26 | `build_cue_sheet` | 6 | `grep -n 'name="build_cue_sheet",' $T` | `7787:            name="build_cue_sheet",` |
| E-27 | `plan_executor_layout` | 6 | `grep -n 'name="plan_executor_layout",' $T` | `7866:            name="plan_executor_layout",` |
| E-28 | `query_state` | 7 | `grep -n 'name="query_state",' $T` ; `ls ui/src/components \| grep CueMonitor` | `6415:            name="query_state",` ; `CueMonitor.tsx` `CueMonitor.test.tsx` — 큐 진행 모니터 화면이 이 조회 경로 위에 있다 |
| E-29 | `run_commands` | 7 | `grep -n 'name="run_commands",' $T` ; `ls ui/src/components \| grep -E 'LockToggle\|RunbookMode\|PoolTile'` | `6394:            name="run_commands",` ; `LockToggle.tsx` `RunbookMode.tsx` `PoolTile.tsx` — 쇼 컨트롤 타일·런북·라이브 잠금이 이 실행 경로 위에 있다 |
| E-30 | `preshow_check` | 8 | `grep -n 'name="preshow_check",' $T` | `6991:            name="preshow_check",` |
| E-31 | `deploy_plugin` | 8 | `grep -n 'name="deploy_plugin",' $T` | `6443:            name="deploy_plugin",` |
| E-32 | `build_handover_pack` | 9 | `grep -n 'name="build_handover_pack",' $T` ; `grep -n 'truncated' server/web/messages.py` | `7840:            name="build_handover_pack",` ; `602:    truncated: bool = False,` `613:    - ``truncated`` — the responder itself said the listing was cut short.` — 불완전성 배지 3종의 정의부(나머지 2종은 §5) |
| E-33 | `ask_user` | 공통 | `grep -n 'name="ask_user",' $T` | `7013:            name="ask_user",` |
| E-34 | `import_lxseq_patch` | 2 | `grep -n 'name="import_lxseq_patch",' $T` | `9264:            name="import_lxseq_patch",` |

행 수 검증:

```bash
grep -c '^| E-' .moai/specs/SPEC-COPILOT-LDGUIDE-001/evidence.md   # 34 == wc -l < /tmp/tools.txt
```

### §1.1 배정 판단이 갈릴 수 있는 행 — 이유 명시

> 아래는 산문으로 적는다. 표로 두면 첫 열이 `| E-` 로 시작해 §1 배정표의 앵커 행으로
> 오계수된다(AC-008이 `^| E-` 를 센다).

- **E-11 `arrange_fixtures`** — 단계 2(패치)로도 읽힌다. 그러나 이 도구는 DMX 주소가 아니라
  **3D 좌표**를 쓴다. 주소 배정은 단계 2, 물리 배치는 단계 3이다.
- **E-28 `query_state` · E-29 `run_commands`** — 전 단계에서 쓰인다. 그러나 **감독이 의식적으로
  꺼내는 시점**은 리허설 중 수정이며, 다른 단계에서는 다른 도구가 이들을 내부적으로 호출한다.
- **E-30 `preshow_check`** — 단계 7(리허설)로도 읽힌다. 이름 그대로 **본공연 직전** 점검이므로
  단계 8에 둔다. 리허설 중 점검은 E-28로 한다.
- **E-33 `ask_user`** — 단계 배정 없음. 내부 도구이며 감독이 직접 부르는 것이 아니라 앱이
  되묻는 경로다. 부록에만 기재한다.

## §2. 수치 주장 재측정 — 불일치 5건

REQ-LDG-009는 개수형뿐 아니라 **백분율·배수·비율**을 포함한다.

측정 명령:

```bash
for f in server/looks/library/*.yaml; do echo -n "$f "; grep -cE '^\s+- look_id:' "$f"; done
for f in server/fx/library/*.yaml;    do echo -n "$f "; grep -cE '^\s+- fx_id:'   "$f"; done
grep -cE '^\s+- scene_id:' server/scene/library/core.yaml
sed -n '43,51p' server/spatial/topology.py
grep -cE '^            name="build_[a-z_]+",$' "$T"
```

| 가이드 주장 | 개정 전 위치 | 재측정값 | 판정 | 근거 |
|---|---|---|---|---|
| `22가지 AI 도구` | L345 절 제목 | **33** | 불일치 | `wc -l < /tmp/tools.txt` → `33` |
| `22 도구` (구성 도식) | L236 | **33** | 불일치 | 동일 |
| `12 이펙트` | L435 절 제목 | **19** | 불일치 | color `3` + dimmer `5` + movement `11` |
| `fx12` (구성 도식) | L236 | **19** | 불일치 | 동일 |
| `자동 생성 문서 4종` | L580 절 제목 | **5** | 불일치 | `build_` 접두 등록 도구 5종(E-9·15·16·26·32) |
| `앞/뒤/좌/우/상/하 6개 위상` | L463 | 수 6은 일치, **이름이 전부 다름** | 서술 불일치 | `TopologyKind` = `depth_rows` `lateral_split` `concentric` `vertical_levels` `grid` `bilateral_pairs` |
| `위상 분류 6종` | L363 | **6** | 일치 | 동일 |
| `32개 룩` | L392 | **32** | 일치 | ballad 7 + rock 8 + edm 9 + worship 8 |
| 발라드 7 / 록 8 / EDM 9 / 워십 8 | L397~419 | 동일 | 일치 | 위와 같은 명령 |
| `씬5` (구성 도식) | L237 | **5** | 일치 | `scene/library/core.yaml` |
| `장르4` (구성 도식) | L237 | **4** | 일치 | `ls server/looks/library/*.yaml \| wc -l` → `4` |
| `커버리지 약 70%` | L389 | **재측정 불가** | 싣지 않음 | 산출 정의도 산출물도 저장소에 없다 |
| `커버리지 약 78%` | L486 | **재측정 불가** | 싣지 않음 | 동일 |
| `문법 오류율 0.40% (248회 중 1회)` | L629 | **재측정 불가** | 싣지 않음 | 248회 측정의 원자료가 저장소에 없다 |
| `100%` · `50%` · `40%` (예시 값) | 본문 다수 | 조명 값 예시 | 대상 아님 | 능력 주장이 아니라 MA3 디머 값 |

**"재측정 불가" 3건은 REQ-LDG-008에 따라 개정본에 싣지 않는다.** "미확인"으로 표기해
남기는 선택지도 있었으나, 커버리지 백분율은 그 자체가 **정의 없이는 의미가 없는 수**이므로
표기가 아니라 삭제를 택했다. 이 선택을 여기 남긴다.

## §3. 식별자 부재 17종 — 3값 판정

**[정정 반영]** spec.md §A.2 v0.5.0이 `16 등장 / 17 부재`로 정정됐다. 이 원장은 정정판 기준이다.

판정 명령:

```bash
grep -oE '\b[a-z]+_[a-z_]+\b' "$G" | sort -u > /tmp/used.txt
comm -13 /tmp/used.txt /tmp/tools.txt   # 부재 17종
comm -12 /tmp/used.txt /tmp/tools.txt   # 등장 16종
```

| 도구 | 판정 | 근거 (개정 전 가이드 기준) |
|---|---|---|
| `precheck_patch` | stale | L361이 등록명 아닌 `check_patch`로 적음. 능력 서술 자체는 §6-2에 존재 |
| `preshow_check` | stale | L360이 등록명 아닌 `run_preshow_check`로 적음. 능력 서술은 §6-1에 존재 |
| `create_arrangement_groups` | stale | L363이 저장소에 없는 `generate_groups`로 적음 |
| `build_magic_sheet` | stale | §12 A1이 "현재 누락"이라 적었으나 **등록돼 있다**(E-16) |
| `plan_executor_layout` | stale | §12 A4가 미구현 제안으로 적었으나 **등록돼 있다**(E-27) |
| `analyse_layout_image` | stale | §12 C2가 미구현 제안으로 적었으나 **등록돼 있다**(E-2) |
| `precheck_vectorworks_diff` | covered-in-prose | §12 C3이 Vectorworks 연계를 다루나 미래형 서술 — 능력은 다뤄지되 시제가 낡음 |
| `vectorworks_autopatch` | covered-in-prose | 동일 |
| `apply_vectorworks_patch` | covered-in-prose | 동일 |
| `arrange_fixtures` | covered-in-prose | §5-7 "빠른 조명 어휘" 표(L465~480)가 격자·일렬·원형·높이 배치를 식별자 없이 서술 |
| `classify_arrangement_topology` | covered-in-prose | §5-6(L462)이 위상 분류를 식별자 없이 서술 |
| `find_scene` | covered-in-prose | §5-3(L439) 씬 컴파일러 절이 검색 단계를 뭉뚱그려 포함 |
| `get_spatial_context` | covered-in-prose | 등장 16종에 포함되나 §5-6·5-7 산문이 능력을 함께 덮음 — 참고 표기 |
| `patch_fixtures` | absent | 패치 생성 능력에 대응하는 서술이 본문에 없다 |
| `resolve_fixture_type` | absent | 없음 |
| `resolve_patch_address` | absent | 없음 |
| `compose_fx` | absent | 이펙트 **합성** 능력에 대응하는 서술이 없다(§5-2는 검색·적용만) |
| `ask_user` | absent | 내부 도구. 부재가 정상이며 개정본에서도 부록에만 둔다 |

집계: **stale 6 · covered-in-prose 7 · absent 5** = 18행(`get_spatial_context`는 등장 16종
쪽에 속하는 참고 행이므로 부재 17종 집계에서 제외). 부재 17종 = stale 6 + covered-in-prose 6
+ absent 5.

**판정이 뒤집은 것**: 개수만 보면 "17종 능력 누락"으로 읽히지만, 실제 누락(absent)은
`ask_user`를 빼면 **4종**뿐이다. 나머지 13종은 이름이 틀렸거나(stale 6) 산문으로 덮여
있다(covered-in-prose 6~7). spec.md §A.2가 "개수 차이만으로 결함을 단정하지 않는다"고
유보한 것이 옳았다.

## §4. 유령 식별자 5건 — 재확인

```bash
printf 'contents_unavailable\ndrilldown_capped\n' | sort > /tmp/allow.txt
comm -23 /tmp/used.txt /tmp/tools.txt | comm -23 - /tmp/allow.txt
```

관측 출력:

```
check_patch
generate_groups
propose_plan
run_preshow_check
write_coordinate
```

차집합 반환값 **5** — 개정 전 비공허성 확인. 개정본에서 이 값은 **0**이어야 한다(AC-019).

| 유령 이름 | 처리 |
|---|---|
| `check_patch` | 등록명 `precheck_patch`로 교정 → 부록에만 |
| `run_preshow_check` | 등록명 `preshow_check`로 교정 → 부록에만 |
| `generate_groups` | 등록명 `create_arrangement_groups`로 교정 → 부록에만 |
| `propose_plan` | 저장소 0건. **삭제** |
| `write_coordinate` | 저장소 0건. **삭제** |

## §5. 허용목록 2종 — 코드 실재 재확인

plan.md M0 2-b의 [HARD] 지시(`base`가 `f30ab4c`로 바뀌었으므로 재확인)를 수행했다.

```bash
grep -rn "contents_unavailable" server | grep -v "/tests/"
grep -rn "drilldown_capped"     server | grep -v "/tests/"
```

| 토큰 | 관측 출력(비테스트 경로) | 판정 |
|---|---|---|
| `contents_unavailable` | `server/web/messages.py:604,616,631,733` · `server/web/PROTOCOL.md:148,178` | 실재 — 허용목록 유지 |
| `drilldown_capped` | `server/fx/matching.py:81` · `server/web/messages.py:603,614,630,732,765` | 실재 — 허용목록 유지 |

**새 항목 추가 없음.** 추측으로 허용목록을 늘리면 유령을 정당화하게 되므로, 코드 실재
근거 없이는 넣지 않는다.

## §6. 게이트 A~D 판정

### 게이트 A — 단계 3(셋업·포커싱)에 대응 기능이 있는가 → **GO**

```bash
grep -rn "pointing" server | grep -v "/tests/" | grep -E "^[^:]*:[0-9]+:(from|import)"
sed -n '107,124p' server/web/session.py
sed -n '214,228p' server/web/session.py
grep -n "pointing" "$T"
```

관측:

```
server/web/session.py:107:from server.spatial.pointing import (
    BASIC_POSITION_SEQUENCE, FX_POSITION_SEQUENCE, POSITION_PRESET_POOL,
    PointingTarget, SpatialPointingError, aim_pan_tilt, aimed_commands,
    basic_position_presets, fan_chain, fan_pan_tilt, fx_position_presets,
    pointing_commands, position_cue_store_commands,
    position_preset_store_commands, preset_recall_command, radial_pan_tilt,
)
server/web/session.py:216-218: # Aim every moving head's beam at one stage point
                               # (measured pan/tilt model — server/spatial/pointing.py)
server/web/session.py:219: _POINT_AT_TARGET = re.compile(
    r"(?:바라보|바라볼|비추|비춰|비출|향하|향해|향할|조준|겨냥|point|aim)", re.IGNORECASE)
server/web/session.py:238-246: _LOOK_FAN / _LOOK_FAN_IN / _LOOK_FAN_CROSS / _LOOK_RING / _LOOK_SPREAD

server/orchestrator/tools.py:7976:  "direction or 'which way is it pointing' needs these axes "
    (← 문자열 한 건. import 아님)
```

**판정 GO.** 조준은 구현돼 있고 자연어로 도달한다. 다만 33종 등록 도구가 아니라
`server/web/session.py`의 결정적 의도 인식 층이 `server/spatial/pointing.py`를 직접
호출하는 경로다. `tools.py`에서 `pointing`은 설명 문자열 1건으로만 등장한다.

→ 단계 3 ②에 기재한다. 동시에 **단계 3 ③에 간극 1건**: 도구 목록에도 부록에도 나타나지
않으므로 감독이 이 기능의 존재를 알 방법이 없다.

**"조준 기능이 없다"고 쓰지 않는다** — 그것이 미관측 주장이었을 것이다.

### 게이트 B — 단계 7(리허설·수정)에 전용 지원이 있는가 → **부분 GO**

```bash
ls ui/src/components/ | grep -E "CueMonitor|LockToggle|RunbookMode"
```

관측:

```
CueMonitor.tsx
CueMonitor.test.tsx
LockToggle.tsx
RunbookMode.tsx
RunbookMode.test.tsx
```

**판정 부분 GO.** "리허설"이라는 이름의 전용 기능은 없다. 그러나 리허설 중 실제로 쓰이는
표면이 존재한다: 큐 진행 모니터(`CueMonitor`) · 라이브 잠금(`LockToggle`) · 런북
모드(`RunbookMode`) + 저수준 수정 경로 E-28·E-29.

→ 단계 7 ②에 UI 3종 + 저수준 2종을 기재.
→ 단계 7 ③에 2건: (a) 큐 내용 판독 경로가 없어 "다음 Go가 무엇을 바꾸는가"를 미리 볼 수
없다 (b) 되돌리기 경로가 없다.

### 게이트 C — 식별자 부재 판정 → §3에서 완료 (17종 전량, 공란 0)

### 게이트 D — 안전 경고 4건의 근거 재확인 → **4건 전부 배치**

§0에 따라 **도구 설명문은 근거로 쓰지 않는다.** 아래 `근거` 열은 코드 경로와 테스트 파일이며,
설명문은 보조 인용으로만 표기했다.

| 위험 | 단계 | 근거 (명령 → 관측) | 부착 앵커 | 판정 |
|---|---|---|---|---|
| 그룹 멤버십을 판독할 수 없어, 점유된 슬롯을 덮어쓰면 복구할 수 없다 | 4 | `grep -c "childCount" $T` → **20행** [cf86dad] · 그중 총계 승격을 막는 처리는 828·832·836 (부분 인용임을 밝힌다) ; `grep -n "Delete\|Remove" server/safety/blacklist.yaml` → `63:  - "Delete"` `64:  - "Remove"` (승인 필수) ; 복원 경로 부재는 §12 B3이 "되돌릴 수 없다"로 기록 | E-14 | 배치 |
| 프리셋 덮어쓰기 확인 카드는 승낙 어휘가 좁아, 다르게 답하면 저장이 조용히 멈춘다 | 4 | `grep -c "승낙" server/web/session.py` → **26행** [cf86dad] · 그중 어절 집합 정의와 "부분 문자열 매칭은 쓰지 않는다"는 2676·2680·2681·2686 (부분 인용임을 밝힌다) | E-18 | 배치 |
| 씬을 룩과 이펙트로 나눠 만들면 조용히 실패한다 | 5 | `ls server/tests | grep scene | wc -l` → **7개** [cf86dad] · 이 주장을 직접 뒷받침하는 것은 `test_scene_compile.py` `test_scene_boundary.py` (부분 인용임을 밝힌다) ; (보조) `tools.py:7637-7645` 설명 원문 | E-23 | 배치 |
| 서버는 Vectorworks 패치를 실행하지 않는다 — 사람이 콘솔에서 Lua를 실행해야 한다 | 1·2 | `ls server/tests | grep autopatch | wc -l` → **9개** [cf86dad] · 이 주장을 직접 뒷받침하는 것은 `test_autopatch_execute.py` `test_autopatch_verify.py` `test_autopatch_contract.py` (부분 인용임을 밝힌다) ; (보조) `tools.py:6893-6900` 설명 원문 | E-4 | 배치 |

**제외분 없음.** 4건 모두 근거가 코드·테스트에 귀속됐다.

> **잔여 위험(닫지 않음)**: 위 테스트 파일들의 **존재**는 확인했으나 **실행**은 하지 않았다.
> 실행은 M5 회귀 배치에서 수행하며, 그때까지 이 4건의 근거는 "대응 테스트가 존재한다"
> 수준이다. 이 한계를 여기 남긴다.

## §7. 보존 판정 — 개정 전 `<h3>` 25개 전량

```bash
BASE=$(git merge-base HEAD origin/main)      # f30ab4c
git show "$BASE:$G" | grep -c '<h3'          # 25
```

| # | 개정 전 행 | 절 제목 | 판정 | 사유 / 이동처 |
|---|---|---|---|---|
| 1 | 187 | 한 줄 정의 | keep | 도입부 보존(REQ-LDG-010) |
| 2 | 304 | 화면 영역별 기능 | keep | 도입부 보존 |
| 3 | 323 | 자연어로 MA3 조작하기 | merge | 도입부 "이 앱을 쓰는 법"으로 통합 |
| 4 | 345 | 22가지 AI 도구 전체 목록 | merge | 참조 부록으로 이관 + 수치 22→33 교정 |
| 5 | 372 | Lua 플러그인 제작 | merge | 단계 8 |
| 6 | 391 | 5-1 룩 라이브러리 | merge | 단계 5 |
| 7 | 435 | 5-2 이펙트 라이브러리 (12 이펙트) | merge | 단계 5 + 수치 12→19 교정 |
| 8 | 439 | 5-3 씬 컴파일러 | merge | 단계 5 |
| 9 | 448 | 5-4 큐리스트 초안 | merge | 단계 6 |
| 10 | 459 | 5-5 버스킹 준비 마법사 | merge | 단계 5 |
| 11 | 462 | 5-6 공간 인식과 배치 그룹 | merge | 단계 4 + 위상 이름 교정 |
| 12 | 465 | 5-7 빠른 조명 어휘 | merge | 단계 3(배치·조준) + 단계 5(연출 어휘)로 분할 |
| 13 | 488 | 6-1 프리쇼 체크 | merge | 단계 8 |
| 14 | 501 | 6-2 패치 점검 | merge | 단계 2 |
| 15 | 528 | 7-1 쇼 컨트롤 패널 | merge | 단계 8 |
| 16 | 538 | 7-2 큐 진행 모니터 | merge | 단계 7·8 |
| 17 | 546 | 7-3 볼런티어 런북 모드 | merge | 단계 8 |
| 18 | 562 | 7-4 라이브 잠금 모드 | merge | 단계 8 |
| 19 | 580 | 자동 생성 문서 4종 | merge | 단계 9 + 수치 4→5 교정 |
| 20 | 607 | 사용 방법 | merge | 단계 9 |
| 21 | 655 | 추가 안전 장치 | merge | 해당 단계의 경고 블록으로 분산(REQ-LDG-013 — 문서 끝으로 몰지 않는다) |
| 22 | 673 | 초기 설정 (처음 한 번) | keep | 말미 보존 |
| 23 | 696 | AI 모델 전환 | keep | 말미 보존 |
| 24 | 700 | 연결 상태 표시 | keep | 말미 보존 |
| 25 | 891 | 로드맵 한눈에 보기 | drop | 아래 사유 |

집계: **keep 5 · merge 19 · drop 1 = 25.** 공란 0.

```bash
for v in keep merge drop; do echo -n "$v: "; grep -cE "\| $v \|" "$E"; done   # 5 / 19 / 1
grep -cE '\| *(keep|merge|drop) *\|' "$E"                                     # 25
```

> **자기 정정 기록**: 이 집계를 처음 `keep 6 · merge 18`로 적었다. 표의 행을 세지 않고
> 눈대중으로 쓴 값이었고, 위 명령으로 재보니 `5 · 19`였다. 합계 25는 우연히 맞았기 때문에
> 합계만 보는 검사(§D.11)로는 잡히지 않았다 — **이 SPEC이 §A.1에서 지목한 것과 같은 종류의
> 결함**(선언한 수와 실제가 어긋남)을 원장 자신이 한 번 재생산한 것이다. 지우지 않고 남긴다.

### §7.1 유일한 drop 판정의 사유

`로드맵 한눈에 보기`(개정 전 L891)를 싣지 않는 이유는 두 가지이며, 둘 다 실측이다.

1. **내용이 사실과 어긋난다.** 이 표가 "아직 없는 기능"으로 분류한 항목 중 최소 4건이
   이미 등록된 도구다 — A1 매직시트(E-16) · A4 익스큐터 레이아웃(E-27) · C2 이미지
   분석(E-2) · C3 Vectorworks 연계(E-1·E-3·E-4). §A.1이 지목한 능력 드리프트가 로드맵
   절에서 한 번 더 반복된 것이다.
2. **시간 예측을 담고 있다.** `즉시 (1~2주)` · `측정 후 (2~4주)` · `중기 (1~2개월)` ·
   `장기 (3~6개월+)` — REQ-LDG-006 위반.

이 절의 기능(다음에 무엇을 할 것인가)은 `backlog-candidates.md`가 대신한다. 그쪽은 각
항목이 관측 근거를 갖는다.

> **E4 처리**: 개정본과 **모순**되는 서술이므로 병기하지 않고 drop한다(acceptance §E E4).

## §8. 검증 명령 뮤테이션 — 위임 기록

`acceptance.md` §D의 미검증 10개(D.1 · D.2 · D.4 · D.7 · D.9 · D.10 · D.12 · D.13 · D.16 ·
D.17)를 이 세션이 전량 뮤테이션 검증했고, 결함 4건을 찾아 교정형을 plan 세션에 인계했다.
결과는 `acceptance.md` §G.1-b에 원자료로 기록돼 있다(관측자 `run-tjueej`).

발견 요약:

| 명령 | 결함 | 방향 |
|---|---|---|
| D.1 | 번호 집합을 보지 않아 단계 9 누락 문서가 통과 | fail-open |
| D.2 | 순서 검사가 판정이 아니라 육안 출력 | 판정 부재 |
| D.7 | 후행 어미를 요구해 실제 시간 예측 8건을 0으로 반환 | fail-open |
| D.13 | rebase 후 기준점이 무관한 이력 296파일을 삼켜 **상시 실패** | fail-**closed** |

D.13은 이 SPEC에서 처음 나온 반대 방향 결함이다. 앞의 것들은 감사가 **같은 깨진 명령을
봤기 때문에** 못 잡았고, D.13은 **rebase가 감사보다 나중이었기 때문에** 못 잡았다 —
감사 회차를 늘려도 잡히지 않는 종류다.

이 세션이 처음 제안한 D.7 교정형은 **위양성 3건**(`10분 간격 백업` · `90일 보관`)을
냈고, 실물에 돌려 보고 스스로 철회했다. 기각된 형태도 §G에 남겼다 — 다음 세션이 같은
광역형을 다시 제안하는 것을 막기 위함이다.

## 이력

| 일자 | 내용 |
|---|---|
| 2026-08-17 | M0 최초 작성. 도구 33종 배정 · 수치 재측정(불일치 5건) · 부재 17종 3값 판정 · 유령 5건 · 허용목록 재확인 · 게이트 A~D 판정 · 보존 25건 판정. 측정 주체 run-tjueej, base `f30ab4c`. |
