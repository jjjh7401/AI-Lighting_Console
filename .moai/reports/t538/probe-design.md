# t538 무빙 원인 가르기 · 위치 프리셋 큐 — 설계·리허설·전부-거절 (실행 전)

작성 2026-10-10 · 브랜치 `WT-mover-probe`(origin/main `156a1d08` 기준) · 카드 t538 본문이 정본.
콘솔 쓰기 0. 읽기만 했다(아래 「읽은 것」). 실행은 리드 경유 감독 승인 뒤.

## 장비·조건

결론은 이 조건을 붙여 적는다(리드 원칙 2026-10-10).

- 대상: MOVER-U 501~508, MegaPointe. 디머 1개, 기본값 0(`t516/verdict.md:226`).
- Group 11 구성원 = 501~508 정확히 8대(`r3_group11.txt` sf_index 30~37 → `r3_group11_fid.txt`, t525 패치 트리 대응).
  - 그래서 A1(선택만 Group 11)은 구성원 차이가 아니라 **선택 문법** 차이만 가른다.
- 박자 112 BPM 기준: 1박 0.54초, 2박 1.07초(A0 의 `At Speed 112` 와 맞춤).
- 응답기 1.6.6(`r0_reads.txt` pong).

## 감독용 표

모두 새 시퀀스 311~321. 항목마다 「켜기 → 감독 눈 → 끄기」로 하나씩 보낸다. 감독 눈 동안 켜 둔 채 멈춘다.

| 항목 | A0 에서 바꾼 한 가지 | 새 번호 | 감독 볼 것 |
|---|---|---|---|
| **A0 양성 대조** | 없음 — t516 A2 문면 그대로(번호·이름만 다름) | 311 | 틸트가 위아래로 물결처럼 움직이나. **안 움직이면 여기서 멈춤** |
| A1 | 선택 `Fixture 501…508` → `Group 11` | 312 | A0 과 같게 움직이나 |
| A2 | 크기 Relative 30 → 12 | 313 | 움직이나, 움직임이 A0 보다 작은가 |
| A3 | 기준 `Tilt At 45` → `At Preset 2.1` | 314 | 움직이나(⑤⑨ 정지의 핵심 후보) |
| A4 | 기준 줄 없음 | 315 | 움직이나 |
| A5 | Tilt 물결 → Pan+Tilt 원(Phase 0/90, 크기 30) | 316 | 8대가 같이 원을 그리나 |
| A6a 양성 대조 2 | 쇼 효과 프리셋 21.2 PT-CIRCLE 을 Group 11 에(+Dimmer 70) | 317 | 원을 그리나 |
| A6b | 쇼 효과 프리셋 21.5 TILT-SWEEP 을 Group 11 에(+Dimmer 70) | 318 | 틸트가 쓸고 가나 |
| B1 | 위치 큐 4개: 2.1 POS01 → 2.4 POS04(1박) → 2.5 POS05(2박) → 2.3 POS03(1박), Goto 로 하나씩 | 319 | 큐마다 자리를 옮기며 **쓸고 가나**. 큐 1 에서 2.1 이 이 8대를 움직이기는 하나 |
| B2 | B1 과 같은 큐 + 큐마다 `TrigType Follow`(큐 1 도 2박), Goto Cue 1 만 | 320 | 혼자 네 자리를 돌고 **처음으로 되감기며** 반복하나 |
| B3 | MIB: 큐 1 POS02 켜짐 → 큐 2 암전 → (2.5 어둠 속 미리 이동, Follow) → 큐 3 POS05 켜짐 | 321 | 큐 3 에서 **이미 POS05 를 보고 켜지나**(켜지며 휘두르면 실패) |

판정 읽기:

- A0 움직임 + A3 만 정지 → 원인은 「위치 프리셋을 기준으로 부름」. ⑤⑨ 와 t516 v3 L4(`At Preset 2.24` 위 Tilt 상대값, 틸트 정지)가 같은 쪽이다.
- A0 움직임 + A1/A2 정지 → 그 변수가 원인.
- A4 정지 → 「기준 절대값이 있어야 상대값이 돈다」. A4 움직임 → 기준값은 원인 아님(t516 A2 에서도 기준 Tilt 45 는 큐에 안 남았다, `t516/verdict.md:390`).
- 둘 이상 정지 → 변수가 하나가 아니다. 본 그대로 적는다.
- A6 정지는 둘 중 무엇인지 가르지 못한다: 프리셋에 501~508 값이 없음 / 불러도 안 돎(아래 「안 잰 것」).

## 문면

- 생성기: `.moai/reports/t538/mover_probe.py` (t531 `m1_common.main_cli` 재사용 — 리허설·전부-거절·승인 고정 세 모드).
- A0 대조: `store_A0` 10줄 중 8줄이 `t516/approval_rhythm_probe_v4.txt:18-27` 과 같고, 다른 2줄은 시퀀스 번호·이름뿐(리허설 `planned` 비교).
- B1·B2 저장 줄은 앱 함수 `server/spatial/pointing.position_cue_store_commands` 가 낸다(`Store Sequence n Cue k '이름' CueFade s`).
- B3 은 앱 함수 `apply_mib → position_cue_bundle → premove_follow_command` 가 낸 줄 그대로다(Fixture 목록 선택, 2.5 미리 이동 큐 CueFade 1 + Follow).
- 승인 목록: `approval_t538.txt` 156줄, sha256 `5220d0901b5eebc4d6c4fc8911f8a2aba9a414557daaf51899232e799ac4b84e`. SaveShow·Delete·Remove·Master 0줄.

## 리허설 · 전부-거절

| 단계 | 결과 | 증거 |
|---|---|---|
| 가짜 콘솔 리허설 | 38묶음 전부 게이트 통과·실행, 156줄 | `rehearse/result.json` verdict `rehearsal ok` |
| 실기 전부-거절 | preflight `responder_ok` · 빈 번호 311~321 모두 비어 있음 · 요청 38, 승인 0 · 쓰기 감사 `rejected` 38 / `executed` 0 · 요청 문면 = 리허설 True | `denyall/result.json`, `denyall/audit/audit-20261010.jsonl`, `check_denyall.py` 출력 |

## 실행 명령 (리드 「실행」 뒤에만)

승인은 「묶음 문면이 승인 목록에 있는가」로 맞춘다(`t506/tc_probe.py:83-87`) — 일부만 보내도 된다.
항목마다 켜기와 끄기를 따로 돌린다:

```bash
uv run python .moai/reports/t538/mover_probe.py .moai/reports/t538/live/A0_on --approve .moai/reports/t538/denyall --only store_A0,play_A0
# 감독 눈 → 리드 경유 답
uv run python .moai/reports/t538/mover_probe.py .moai/reports/t538/live/A0_off --approve .moai/reports/t538/denyall --only off_A0
```

A1~A6b·B2 는 같은 꼴(`store_<X>,play_<X>` → `off_<X>`). B1 은 `store_B1,play_B1_c1` → `play_B1_c2` → `play_B1_c3` → `play_B1_c4` → `off_B1`. B3 은 `store_B3,play_B3_c1` → `play_B3_go_dark` → `play_B3_go_reveal` → `off_B3`.
🔴 빈 번호 재확인은 `--only` 가 첫 묶음(`store_A0`)을 포함할 때만 돈다(`m1_common.py:320-322`). 다른 항목의 저장 전에는 `r0_reads.txt` 와 같은 시퀀스 목록 읽기를 한 번 더 한다.

## 읽은 것 (쓰기 0)

| 파일 | 내용 |
|---|---|
| `r0_reads.txt` | pong 1.6.6 · 시퀀스 300~310 + 1999·2000(🔴 **t516 의 234~249 는 없다** — A2 시퀀스 236 은 지워졌다) · **B0 위치 풀 2 = 16개**: 1~6 POS01~06, 21 Home, 22 Wall, 23 Audience, 24 Center, 25 Vocal DSC, 26 Fan Out, 27 Fan In, 28 Cross, 29 Ring Out, 30 Ring In · 풀 21 = 1~7 + 301 |
| `r1_preset_inside.txt`, `r2_preset_props.txt` | 21.2·21.5·2.1 모두 `childCount 0` — 안의 값은 응답기로 못 읽는다. MEMORYFOOTPRINT 21.2=2260, 21.5=1992, 2.1=1568, 2.24=4476. NOTE 빈칸, MAtricks 없음 |
| `r3_group11.txt`, `r3_group11_fid.txt` | Group 11 = 8대, 501~508 |
| `r4_seq_fields.txt`, `r5_seq_props.txt` | 시퀀스 속성 65개 중 `WRAPAROUND` true · `SEQUMIB` Enabled · `RESTARTMODE` First Cue (310·308, 이 세션이 만든 시퀀스의 기본값) |
| `r6_goto_and_footprints.txt` | `TIMINGGOTO` Default · 위치 프리셋 크기: 1~6 은 1568~2640, 21~30 은 4060~4476 |

## 안 잰 것 · 위험

- **21.2·21.5 의 대상 장비·내용**: 못 읽는다. A6 이 안 움직이면 원인을 가르지 못한다.
- **2.1 이 501~508 값을 담고 있는지**: 못 읽는다(풀에서 가장 작음 1568B). B1 큐 1 이 눈으로 답한다. ⑤⑨ 의 감독 「프리셋 자리에 서 있다」는 담고 있다는 쪽이지만 사람 눈 기록이다.
- **Goto 가 큐 페이드를 쓰는지**: `TIMINGGOTO` 가 `Default` 라는 것만 읽었다. B1 에서 쓸고 가지 않고 툭 옮겨지면 Goto 시간 탓일 수 있다 — 그때 B2(Follow 자동 진행)가 대조가 된다.
- **B2 되감기**: `WRAPAROUND` true 에 기대지만, 큐 4 다음 큐 1 의 Follow 가 다시 도는지는 이 항목이 처음 잰다.
- **`Go+ Sequence <n>`**(B3): 이 저장소 송신 기록에 없는 꼴. 룰북은 `Go+ Executor` 만 검증. 실행기 배정(쓰기)을 피하려고 썼다. 거절되면 그 자체가 결과다.
- 콘솔 자체 MIB 기능(`SEQUMIB` Enabled)이 앱 MIB 와 겹쳐 어떻게 도는지는 안 쟀다.
- `Tilt 45` 의 단위(퍼센트·각도)는 여전히 안 잰 것이다(t516 과 같음).
- 장비 특성은 MegaPointe 한 종류에서만 본다. 다른 무빙(Spiider 처럼 디머가 여럿인 기종)은 Dimmer 한 줄로 안 켜질 수 있다(`t516/verdict.md:230`, 가설·미측정) — 앱이 패치에서 기종별 디머 채널 수를 읽어 처리해야 할 항목이다.

## 남는 객체

실행하면 시퀀스 311~321 이 남는다. 지울지는 리드·감독 결정. 쇼 저장 0.
