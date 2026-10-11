# 카드 t553 — SPEC-LDBEAT-001 M4 후속 run-verdict

cycle_type=tdd. Part ①(측정된 무빙 허용목록) 콘솔 접촉 0건. Part ②(실기 프로브)는 리허설 + 전부-거절까지만 — 실행 0건, 쇼 저장 0건. 기준 `ae3afea6`(origin/main, PR #600 포함).

**작업 위치 고지**: 배차서는 `.claude/worktrees/t553`(`WT-ldbeat-gate-update`)를 지정했으나, 이 구현 서브에이전트는 런타임이 자동 격리한 `.claude/worktrees/agent-a6fd8f53bcc5b099d`(브랜치 `worktree-agent-a6fd8f53bcc5b099d`)에서 작업했다. `git merge-base --is-ancestor ae3afea6 HEAD` 확인 완료 — 레인/리드가 이 브랜치를 `WT-ldbeat-gate-update`로 fast-forward 해야 한다.

---

## Part ① — 측정된 무빙 허용목록

### RED (실패 확인, 구현 전)

```
$ uv run --quiet pytest server/tests/test_beat_grid_measured_t553.py -q
==================================== ERRORS ====================================
________ ERROR collecting server/tests/test_beat_grid_measured_t553.py _________
ImportError while importing test module '.../server/tests/test_beat_grid_measured_t553.py'.
...
E   ModuleNotFoundError: No module named 'server.design.beat_grid_measured'
=========================== short test summary info ============================
ERROR server/tests/test_beat_grid_measured_t553.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.07s
```

기존 통합 시험(`test_beat_grid_emit_t549.py::TestLoveAttackIntegrationAgainstLiveM1Status::test_blocked_and_allowed_cells_match_the_m1_gate_mapping`)도 구현 전에는 신규 기대(`("MOVER-D",7)`·`("MOVER-D",22)`가 더 이상 막히지 않음)와 어긋나 실패했다:

```
>       assert expected_app_movement_blocked <= blocked
E       AssertionError: assert {('MOVER-D', ...MOVER-U', 18)} <= {('BACK', 3),...-U', 11), ...}
E
E         Extra items in the left set:
E         ('MOVER-D', 22)
E         ('MOVER-D', 7)
FAILED server/tests/test_beat_grid_emit_t549.py::TestLoveAttackIntegrationAgainstLiveM1Status::test_blocked_and_allowed_cells_match_the_m1_gate_mapping
1 failed, 26 passed in 0.22s
```

### GREEN (구현 후)

```
$ uv run --quiet pytest server/tests/test_beat_grid_emit_t549.py server/tests/test_beat_grid_measured_t553.py -q
........................................                                 [100%]
40 passed in 0.16s
```

### 구현 요약

- **신설** `server/design/beat_grid_data/measured_movements.yaml` — 리그 전용 숫자(group_no)는 전부 여기에만. 엔트리 2개:
  - `group_no=12(MOVER-D), shape=wave, axes=[Tilt], base_condition=any` — 출처 `.moai/reports/t548/probe-moverd.md` D1(seq 331, 2마디 주기+위상 펼침, 프레임 변화 1.3~1.4%)·D3(seq 333, 2박 주기, 1.0~1.3%), 정지 대조 0.00%.
  - `group_no=12(MOVER-D), shape=wave, axes=[Pan], base_condition=requires_tilted_base_unverifiable` — 출처 D2(기준 2.1, 판정 불가 0.02~0.03%)·D2'(기준 Tilt 45, 움직임 3.7~5.1%). **이 엔트리는 매칭되어도 게이트를 절대 열지 않는다** — 앱이 position_preset_no의 실제 기울기를 못 읽기 때문(M1 ⑥과 같은 한계).
- **신설** `server/design/beat_grid_measured.py` — `is_movement_measured_open(group_no, shape, axes)`: group_no+shape+axes **정확 일치**만, `base_condition == "any"`일 때만 True. 9개 단위 시험.
- **수정** `server/design/beat_grid_emit.py` — `blocked_m1_items_for_cue`에 키워드 전용 `group_no: int | None = None` 추가(기본값 유지로 기존 2-위치-인자 호출부는 바이트 동일). ⑤⑦⑨가 막혀 있고 group_no가 있고 허용목록과 일치하면 그 세 항목만 막힘에서 뺀다. `_emit_cue`가 이미 쥐고 있던 `group_no`를 넘겨준다. progress.md M1 표의 원래 판정 문자열은 고치지 않는다(PRESERVE).
- **갱신(삭제 아님)** `server/tests/test_beat_grid_emit_t549.py` — LOVE ATTACK 전수 통합 시험에서 `("MOVER-D",7)`·`("MOVER-D",22)`를 거절→허용으로 옮김(날짜 붙은 주석으로 사유 기록). `TestBlockedM1ItemsForCue`에 `group_no` 오버라이드 전용 단위 시험 4개 추가.

### 최종 blocked/open 전수 (LOVE ATTACK, 실제 progress.md M1 상태 기준)

| 칸 | 이전(t549) | 이후(t553) |
|---|---|---|
| MOVER-D bar 7 (Tilt wave, 2마디+위상 펼침) | 거절(미확인 5,7,9) | **허용** |
| MOVER-D bar 22 (Tilt wave, 2박) | 거절(미확인 5,7,9) | **허용** |
| MOVER-D bar 18 (정적 위치 프리셋 2.1, app_movement 없음) | 허용 | 허용(변화 없음) |
| MOVER-U bar 11 (Pan wave, 주기 없음) | 거절(미확인 5,7,9) | 거절 — **게이트 매칭 자체가 없음**, 그리고 `app_movement_commands`가 그 전에 이미 "period_unit이 'beat'/'bar'가 아님"으로 거절(레이블이 주기를 말하지 않아 지어내지 않음, M1 게이트와 무관한 별개 사유) |
| MOVER-U bar 18 (Pan wave, 2박, 기준 2.1) | 거절(미확인 5,7,9) | 거절 — Pan 단독은 MOVER-U에서 한 번도 라이브로 재지 않았다 |
| (전체 효과 프리셋 8칸·FOH/WASH-ALL/BLIND 6칸) | 변화 없음 | 변화 없음 |

### Dimmer2 확인 (코드 추적만, 콘솔 접촉 0)

`server/design/app_movement.py`의 `brightness_value_commands`는 호출자가 넘긴 `dimmer_attributes`의 **모든** 디머 계열 속성(정규식 `^dimmer\d*$`)에 한 줄씩 명령을 낸다 — Spiider처럼 Dimmer+Dimmer2 둘 다 필요한 기구도 호출자가 두 이름을 넘기기만 하면 **이미 일반적으로 처리되어 있다**(코드 수정 불필요, 배차서 질문에 대한 답).

다만:

```
$ awk '/group_name: MOVER-D/,/group_name: BLIND/' server/design/beat_grid_data/love_attack.yaml | grep -c "brightness"
0
```

`love_attack.yaml`의 MOVER-D 트랙은 **전체 큐(bar 0·3·7·11·14·18·22)에 `brightness` 필드가 하나도 없다**. 즉 이제 열린 bar 7·22의 `app_movement` 큐는 Dimmer/Dimmer2 명령을 전혀 내지 않는다 — 이 트랙은 이 데이터 그대로는 격자 전체에서 한 번도 "켜지는" 큐가 없다(이전 큐에서 이미 켜져 있지 않은 한 빔이 안 보일 수 있다). **보고만 한다 — 데이터 보강은 이 카드 범위를 벗어나 고치지 않았다.**

### 검증

```
$ uv run --quiet pytest server/tests/ -k "beat_grid or app_movement" -q
........................................................................ [ 42%]
........................................................................ [ 84%]
...........................                                              [100%]
171 passed, 14791 deselected, 1 warning in 5.86s
```

```
$ uv run ruff check server/design/beat_grid_measured.py server/design/beat_grid_emit.py \
    server/tests/test_beat_grid_measured_t553.py server/tests/test_beat_grid_emit_t549.py \
    .moai/reports/t553/*.py
All checks passed!
$ uv run ruff format --check <같은 파일들>
8 files already formatted
```

```
$ git diff --stat ae3afea6 -- server/director/emit.py server/looks/songcue.py \
    ui/src/components/CueSheetTimeline.tsx server/safety/ console/lua/ \
    .moai/specs/SPEC-LDBEAT-001/spec.md .moai/specs/SPEC-LDBEAT-001/plan.md \
    .moai/specs/SPEC-LDBEAT-001/acceptance.md
(출력 없음 — 0줄, PRESERVE 확인)
```

progress.md에 "2026-10-11 대체 고지 (카드 t553)" 절 + "M4 후속" §E.2 항목 추가(원래 M1 표 행은 보존).

---

## Part ② — 실기 프로브 (설계·리허설·전부-거절만, 실행 금지)

### ①-1 8트랙 타임코드 재측정 (P1b)

카드 t549 발견: LOVE ATTACK은 콘솔 그룹 트랙 8개인데 `MEASURED_MAX_TIMECODE_TRACKS=6`(①이 구조로 확인한 실제 최대)을 넘어 한 타임코드에 전부 몰면 트랙 레벨 전부 거절된다. 이 프로브는 t531 P1(6트랙, TC 30)과 같은 형태로 트랙 수만 8로 재측정한다.

- 스크립트: `.moai/reports/t553/p1_tc_tracks_8.py`
- 새 번호: 타임코드 **32**(실기 읽기로 비어 있음 확인). 트랙: 기존 시퀀스 **226~233**(RHYTHM PROBE v2/v3, 실기 읽기로 존재 확인) — 참조만, 수정 없음.
- 리허설(가짜 콘솔): 4묶음 전부 `cleared+executed` — `rehearse_8track/result.json`.
- 전부-거절(실기): preflight `responder_ok`, 빈 슬롯(TC 32) 실기 읽기로 재확인(`occupied_before: []`), 4묶음 전부 `approved: false`, `"verdict": "deny-all: nothing written"` — `denyall_8track/result.json`, `denyall_8track.stdout.txt`.
- 쓰기 감사 로그(`denyall_8track/audit/audit-20261011.jsonl`): `event: rejected` 4건(쓰기 묶음 전부), `event: executed`는 `heartbeat`(ping) 1건뿐 — 실행된 쓰기 0건.
- 읽기 감사: `state_query` 9건(자유-슬롯 확인).

### ①-2 MOVER-U(Group 11) 기운 기준 Pan 물결 재시험 (리드 추가 배차)

t548 D2'는 **MOVER-D**(Spiider, Group 12)에서 기운 기준 Pan 물결을 확인했다. MOVER-U(MegaPointe, Group 11)는 이 형태를 한 번도 라이브로 재지 않았다 — 이 프로브가 처음 잰다. **PASS여도 이 카드는 게이트를 열지 않는다** — 리드가 직접 실행·판정한 뒤 별도 카드로 `measured_movements.yaml`에 반영한다(리드 지시 그대로).

- 스크립트: `.moai/reports/t553/probe_moveru_pan_tilted.py`
- 선택: `default_beat_grid("LOVE ATTACK")` MOVER-U 트랙의 `group_no` → `Group 11`(데이터에서 읽음, 코드 리터럴 아님).
- 디머: `Dimmer` 하나만(t538 실측 — Robin MegaPointe Mode 1, 디머 1개. Spiider의 Dimmer+Dimmer2와 다른 조건 — 리그 리터럴이라 프로브 스크립트에만 있다, 앱 코드 아님).
- 기운 기준: `Attribute 'Tilt' At 45` — t538 `mover_probe_v2.py` A0′가 실측한 바로 그 기준 줄.
- BPM: `love_attack_beat_grid.json` 박 시각 회귀 기울기 = 112.002 → Speed(2박) = 56(t548 `probe_moverd.py`/`probe_moverd_d2p.py`와 같은 계산 방식).
- 새 번호: 시퀀스 **336**(t548이 쓴 331~335 바로 다음, 실기 읽기로 비어 있음 확인).
- 묶음: `t0_tilted_lit`(프로그래머만, Store 0 — 기울었는지 리드가 3D 캡처로 먼저 확인) → `t0_clear` → `store_U_pan`(저장+이름) → `play_U_pan` → `off_U_pan` → `final_clear`.
- 리허설(가짜 콘솔): 6묶음 전부 `cleared+executed` — `rehearse_u_pan/result.json`.
- 전부-거절(실기): preflight `responder_ok`, 시퀀스 336 실기 읽기로 비어 있음 확인(`occupied_before: []`), 6묶음 전부 `approved: false`, `"verdict": "deny-all: nothing written"` — `denyall_u_pan/result.json`, `denyall_u_pan.stdout.txt`.
- 쓰기 감사 로그: `event: rejected` 6건, `event: executed`는 heartbeat 1건 + 읽기(`state_query`, `ok: false` — 336 비어 있음 재확인) 2건뿐 — 실행된 쓰기 0건.

### 금지 줄 전수 확인 (두 묶음 합친 승인 목록 기준)

```
$ grep -iE "SaveShow|Delete|Remove|Master|Overwrite|Store Preset|Store Group" .moai/reports/t553/approval_t553.txt
(출력 없음 — 0건)
$ grep -n "^Store " .moai/reports/t553/approval_t553.txt
1:Store Timecode 32
4:Store Timecode 32.1
41:Store Sequence 336 Cue 1 'T553 - MOVERU pan wave 2 beats tilted base'
```

`Store` 대상은 새로 확인한 빈 번호(타임코드 32, 시퀀스 336) 둘뿐 — 기존 객체(226~233 등)에는 `Assign`/`Off`만 쓴다.

### 승인 목록 (합쳐서 하나)

- 파일: `.moai/reports/t553/approval_t553.txt`
- **46줄**, **sha256 `cc7f58817254a0d1d9bcfb71357f7826af8ea71571169ea19b8b98e8c556902e`**
- 목록 요약(사람이 읽는 묶음별 분해): `.moai/reports/t553/approval-list.md` — 묶음 10개(P1b 4 + 추가 6), 줄 46.
- 생성: `uv run python .moai/reports/t553/make_combined_approval.py`(`denyall_8track/approvals.json` + `denyall_u_pan/approvals.json`를 합쳐 `--approve <각 denyall 폴더>`로 각각 글자까지 같은 묶음만 승인).

### 선택한 빈 번호와 비어 있음을 증명한 읽기

| 번호 | 쓰임 | 비어 있음 확인 |
|---|---|---|
| 타임코드 32 | P1b 신규 타임코드 | ① 사전 ad-hoc 라이브 읽기(`StateQueryError`) · ② `rehearse_8track`(가짜 콘솔, 참고용) · ③ `denyall_8track` 전부-거절 실행 시 `occupied_before: []`(실기 재확인) |
| 시퀀스 336 | MOVER-U Pan 프로브 신규 시퀀스 | 동일 3단계(①②③), `denyall_u_pan` `occupied_before: []` |
| 시퀀스 226~233 | P1b 참조 트랙(기존, 수정 없음) | ad-hoc 라이브 읽기로 전부 존재 확인("RHYTHM PROBE v2/v3 …") — Store/수정 줄 0건 |

### 실행 뒤 되읽기 (준비만, 미실행)

- 스크립트: `.moai/reports/t553/readback_t553.py` — 쓰기 0건, `Timecodes/32/1` 자식 수(기대 9 = Marker 1 + Track 8)·Track 8개의 `TARGET` 속성이 226..233 순서인지, `Sequences/336`의 존재·크기를 읽는다.
- 실행 전 상태에서 미리 돌려 기능을 확인했다(`.moai/reports/t553/readback_pre_execution_check.txt`) — 두 슬롯 모두 `path segment not found`(아직 안 썼다는 증거, 전부-거절 결과와 일치).
- Off/정리 줄은 이미 승인 목록 안에 있다(`Off Timecode 32`+`Off Sequence 226..233`, `Off Sequence 336`, 양쪽 끝 `ClearAll`).

### 리드가 볼 것 (실행·판정 안내)

| 묶음 | 리드가 볼 것 |
|---|---|
| P1b (8트랙) | 기계 판독만 필요. 실행 뒤 `readback_t553.py`로 `Timecodes/32/1` 자식 9개 + Track TARGET 순서 226..233 일치를 확인하면 PASS. |
| MOVER-U 기운 기준 Pan | `t0_tilted_lit` 뒤 onPC 3D 캡처로 바닥 스폿이 수직(2.1) 기준에서 무대 쪽으로 옮겨졌는지 먼저 확인(기울었다는 증거). 본 묶음(`store_U_pan`+`play_U_pan`) 재생 중 **빔이 좌우로 쓸리는지**(t548 D2'와 같은 판정 기준) 육안 확인. 움직이면 PASS — 단 이 카드는 그 결과를 게이트에 반영하지 않는다(별도 카드). |

### 안 잰 것 (Gaps)

- Part ①: D4(Pan+Tilt circle, t548 seq 334)는 `app_movement_commands`가 아직 `shape="wave"`만 구현해(circle 미구현) 허용목록에 옮기지 않았다. MOVER-D bar 7·22가 실제로 켜진 채 움직이는지는 Dimmer 공백 때문에 데이터 보강 없이는 확인 불가(위 Dimmer2 절 참조).
- Part ②: 시퀀스 226~233(RHYTHM PROBE v2/v3)의 **내용**이 P1b 재생 중 실제로 어떻게 움직이는지는 이 프로브의 관심사가 아니다(① 구조 확인용, t531과 동일 설계) — 재생 자체의 시각 판정은 안 쟀다(감독 관찰 불필요로 설계). MOVER-U 기운 기준 Pan의 "좌우로 쓸림" 정도(퍼센트)는 리드 캡처 전까지 미측정. Group 11 그룹 내부 순서가 위상 펼침 방향과 일치하는지는 이 프로브 범위 밖(단일 축 Pan, 위상 펼침 없음).

---

## 커밋 전 요약

- 파일 변경: `server/design/beat_grid_emit.py`(수정), `server/design/beat_grid_measured.py`(신설), `server/design/beat_grid_data/measured_movements.yaml`(신설), `server/tests/test_beat_grid_measured_t553.py`(신설), `server/tests/test_beat_grid_emit_t549.py`(수정), `.moai/specs/SPEC-LDBEAT-001/progress.md`(수정, 대체 고지 + §E.2 항목), `.moai/reports/t553/**`(신설, 보고서+스크립트).
- PRESERVE diff: 0줄(`emit.py`/`songcue.py`/`CueSheetTimeline.tsx`/`safety/**`/`console/lua/**`/spec·plan·acceptance body).
- 콘솔 쓰기: Part ① 0건, Part ② 0건(전부-거절까지만) — 승인 목록은 리드 「실행」 대기.

## 실기 실행 결과 (레인, 2026-10-11 — 리드 「실행」 뒤)

이 위의 「실행 금지」·「PASS여도 게이트를 열지 않는다」는 실행 전 시점 문면이다. 아래가 실행 뒤 사실이다.
보낼 때마다 승인 목록 sha256 을 다시 재 일치 확인했고, 묶음마다 멈춰 리드 판정을 받았다. 쇼 저장 0.

| 묶음 | 승인 목록 줄 | 콘솔 | 판정(리드) | 근거 |
|---|---|---|---|---|
| ① 8트랙 TC 32 | `approval_t553.txt` 1~22 | 22줄 OK | PASS — childCount 9, TARGET 226..233 | `live/p1b/`, `live/p1b_readback.txt` |
| 336 기울인 기준 켜기 | 23~26 | 4줄 OK | 8대 켜짐·기울어짐 | `live/u_t0/` |
| 336 저장·재생 | 27~44 | 18줄 OK | 움직임 4.5~5.3% | `live/u_store_play/` |
| 336 끄기 | 45~46 | OK | — | `live/u_off/` |
| 338 저장·재생(앱 출력) | `approval_t553_cell.txt` 20~35 | 16줄 OK | 판정 불가 0.00~0.01% | `live/cell_338_on/` |
| 338 끄기 | 36~37 | OK | — | `live/cell_338_off/` |
| 337 저장·재생(336 + 기준 2.1) | 1~17 | 17줄 OK(첫 시도는 빈 번호 확인에 걸려 0줄) | 판정 불가 0.01~0.02% | `live/cell_337_on/`, `live/cell_337_on_stopped_slotcheck/` |
| 337 끄기 | 18~19 | OK | — | `live/cell_337_off/` |

- 단계 (2)에서 리드 범위(23~27줄) 중 27줄 `ClearAll` 은 캡처 전에 빛을 끄므로 (3) 직전으로 미뤘다 — 문면·순서 무변경.
- 결론: 타임코드 8트랙 확인 → `measured_console.yaml` 상한 8. MOVER-U Pan 단독은 기울인 기준에서만 보이고 2.1(수직) 기준에선 판정 불가 → bar 18 닫힘, `measured_movements.yaml` 에 기록만. 열려면 기울인 위치 프리셋을 칸에 지정(감독 결정 대상).
- 안 잰 것: 8 초과 트랙, 타임코드 재생 중 큐 TrigTime 진행, 337·338·336 시퀀스와 TC 32 는 콘솔에 남아 있다(쇼 저장 0 이라 쇼를 다시 열면 사라짐, 삭제는 승인 범위 밖).

### 옆 화면 확인 — 「2.1 = 빔 수직」을 잰 사실로 (2026-10-11)

감독이 onPC 3D 를 FRONT + SIDE 로 나눈 뒤 리드 지시로 다시 쟀다. 승인 파일 `approval_t553_cell.txt`(sha256 `ca09ae4b…a39c`) 20~23줄(ChangeDestination Root · ClearAll · Group 11 Dimmer 70 · Group 11 At Preset 2.1, 프로그래머만·Store 0)을 그대로 읽는 `probe_side_check.py` 로 리허설 → 실기 전부-거절 → 승인 줄 바이트 대조 일치 → 전송(4줄 OK). 리드 SIDE 캡처 판정: **8대 빔이 트러스에서 거의 수직으로 떨어지고 바닥 스폿은 장비 줄 바로 아래, 앞쪽으로 아주 조금**. 그 뒤 37줄 ClearAll OK. 캡처 파일은 리드 작업 폴더에 있어 저장소에는 글로만 남긴다. 근거 `live/side_lit/`, `live/side_clear/`, `denyall_side/`.
