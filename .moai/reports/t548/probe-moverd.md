# t548 ③ MOVER-D 2단계 무빙 프로브 — 설계·리허설·전부-거절 (실행 전)

콘솔 쓰기 0. 실행은 리드 「실행」 뒤에만. 쇼 저장 0.

## 감독 결정 (2026-10-11, 리드 경유)

1. 팬 흔들기 = `position_fx` 의 `wave` 에 축 매개변수(새 모양 아님) → D2
2. 무빙 기준 위치 = 그 칸의 `position_preset_no` → 모든 묶음의 기준 줄 `At Preset 2.1`
3. run 전 MOVER-D(Group 12) 2단계 무빙 실기 프로브 — 이 문서

## 무엇을 재나

t538 은 Robin MegaPointe(MOVER-U, Group 11)에서만 쟀다. 이 프로브는 같은 형태(A3 기준 프리셋 + 2단계 상대값, A5b 곡선)가 Spiider(MOVER-D)에서도 도는지 처음 잰다.

| 묶음 | 내용 | 감독이 볼 것 |
|---|---|---|
| v0a | Dimmer 70 + 기준 위치(프로그래머만, Store 0) | 켜지나 |
| v0b | v0a + `Dimmer2` 70 | v0a 와 다른가(Spiider 는 디머가 둘 — t516 가설, 미측정) |
| D1 (seq 331) | Tilt 2단계 ±30 + 곡선 + 위상 펼침, 한 바퀴 2마디(Speed 14) | 물결로 움직이나 / 2.1 자리 중심인가 |
| D2 (seq 332) | **Pan** 2단계 — 결정 ①, 한 바퀴 2박(Speed 56) | 좌우로 흔들리나 |
| D3 (seq 333) | Tilt 2단계, 한 바퀴 2박(Speed 56) | D1 보다 빠른 물결인가 |
| D4 (seq 334) | Pan+Tilt 2단계, 위상 0/90 + 곡선(A5b), 한 바퀴 2박 | 동그란 원인가(t538 은 MegaPointe 에서 원) |

## 값의 출처 (상수 금지)

| 값 | 읽은 곳 | 값 |
|---|---|---|
| 선택 | `default_beat_grid("LOVE ATTACK")` MOVER-D 트랙 `group_no`(t543 실측) | `Group 12` |
| 기준 위치 | 같은 트랙의 `position_preset_no`(감독 승인 2026-10-10) | `2.1` |
| BPM | `server/tests/fixtures/love_attack_beat_grid.json` 박 시각 회귀 기울기 | 112.002 |
| 속도 | BPM ÷ 한 바퀴 박 수(MA Speed = 분당 바퀴) | 2마디=14, 2박=56 |

픽스처의 `bpm` 필드(112.347)는 hop 512 격자에 묶인 값이라 쓰지 않았다(t536 실측).

## 실측 (2026-10-11)

| 단계 | 결과 | 증거 |
|---|---|---|
| 응답기 버전 | 처음 1.6.5 → 게이트 `responder_version_mismatch` 로 멈춤(요청 0) → 감독이 1.6.6 붙여넣기(t531 ASCII, sha256 앞 `0382db9457149555`) → `ping true, version 1.6.6` | `ping_after_paste.txt` |
| 가짜 콘솔 리허설 | 16묶음 전부 통과 | `rehearse/result.json` (`rehearsal ok`) |
| 실기 전부-거절 | preflight `responder_ok` · 빈 번호 331~334 모두 비어 있음 · 요청 16, 승인 0 · 쓰기 감사 `rejected` 16 / `executed` 0 · 읽기 감사 핑 1 + 상태 읽기 12 | `denyall/result.json` · `denyall/audit/audit-20261010.jsonl` · `denyall/audit/probe-20261010.jsonl` |
| 문면 대조 | 실기 요청 16 = 리허설 계획 16, 바이트 동일 | 아래 명령 |
| 금지 줄 | SaveShow·Delete·Remove·Master·Overwrite·Store Preset·Store Group 0줄, Store 대상은 시퀀스 331~334 뿐 | 아래 명령 |

## 승인 목록

- 파일: `.moai/reports/t548/approval_t548_moverd.txt`
- 91줄, sha256 `c25b136f45db6110b684b3c53fc3c51f4cd06b6ddde807f25ebcccff6c1ea336`
- 생성: `python .moai/reports/t538/write_approval.py .moai/reports/t548/denyall .moai/reports/t548/approval_t548_moverd.txt`

## 실행 명령 (리드 「실행」 뒤에만)

감독이 하나씩 볼 수 있게 `--only` 로 나눠 보낸다. 승인은 묶음 문면이 승인 목록에 있는지로 맞춘다.

```
R=.moai/reports/t548
uv run python $R/probe_moverd.py $R/live/v0a --approve $R/denyall --only v0a_dimmer_only
uv run python $R/probe_moverd.py $R/live/v0a_clear --approve $R/denyall --only v0a_clear
uv run python $R/probe_moverd.py $R/live/v0b --approve $R/denyall --only v0b_dimmer_and_dimmer2
uv run python $R/probe_moverd.py $R/live/v0b_clear --approve $R/denyall --only v0b_clear
uv run python $R/probe_moverd.py $R/live/D1 --approve $R/denyall --only store_D1,play_D1
uv run python $R/probe_moverd.py $R/live/D1_off --approve $R/denyall --only off_D1
(D2·D3·D4 같은 꼴)
```

🔴 빈 번호 재확인은 `--only` 가 첫 묶음을 포함할 때만 돈다(`m1_common.py`). 저장 묶음 직전에 시퀀스 목록을 한 번 더 읽는다.

## 안 잰 것

- `Dimmer2` 가 이 쇼의 Spiider 속성 이름으로 받아들여지는지 — t516 채널 표의 이름일 뿐, 명령으로 보낸 적 없다. 거절되면 v0b·D1~D4 저장 묶음이 그 줄에서 실패한다.
- Group 12 의 그룹 안 순서 — 위상 펼침의 물결 방향이 Fixture 목록 순서와 같은지는 t538 이 Group 11 에서만 쟀다.
- 앱 회신 포트 9005 를 onPC 자신도 열고 있다(`lsof`). 지금은 핑이 돌아오지만 회신이 끊기면 첫 용의자.

## 실기 결과 (리드 「실행」 2026-10-11, 승인 목록 sha256 c25b136f…ea336 보내기 전 재확인 일치)

| 묶음 | 보낸 줄 | 콘솔 응답 | 쓰기 감사 | 감독 육안 |
|---|---|---|---|---|
| v0a | `ChangeDestination Root` · `ClearAll` · `Group 12 ; Attribute 'Dimmer' At 70` · `Group 12 ; At Preset 2.1` | 4줄 모두 `OK` | approved 1 → executed 4 · SaveShow skipped | **안 켜짐** — 2.1 자리는 빔이 꺼져 판정 불가 |
| v0a_clear | `ClearAll` | `OK` | approved 1 → executed 1 | — |
| v0b | v0a 4줄 + `Group 12 ; Attribute 'Dimmer2' At 70`(Dimmer 뒤) | 5줄 모두 `OK` — `Dimmer2` 거절 없음 | approved 1 → executed 5 · SaveShow skipped | **켜짐** — 리드 onPC 3D 캡처 00:44:08·00:44:13(전송 00:43:54 뒤), 「8 Fixtures Selected」, 8대 모두 빔이 아래로 · v0a(안 켜짐)와 차이는 `Dimmer2` 한 줄 → **Spiider MOVER-D 는 Dimmer2 가 있어야 켜진다(실측)** |
| D1 (seq 331) | store_D1 17줄(v0b 머리 + Tilt ±30 2단계 + 곡선 4 + `Phase 0 Thru 360` + `Speed 14` + Store/ClearAll/Name) · play_D1 `Goto Cue 1 Sequence 331` — 전송 00:45:20 | 18줄 모두 `OK` · 331 전송 전 비어 있음 | approved 2 → executed 18 | **움직임** — 리드 3D 캡처 4장 00:45:35~39, 프레임 사이 변화 1.3~1.4% 픽셀, 차이는 빔 가장자리·바닥 스폿에만 |
| off_D1 | `Off Sequence 331` — 00:46:32 | `OK` | approved 1 → executed 1 | — |
| v0b 재전송(정지 켜짐 대조) | v0b 5줄 — 00:46:37 | 5줄 `OK` | approved 1 → executed 5 | **켜짐·정지** — 밝기 D1 과 같음, 프레임 사이 변화 0.00% (리드 캡처) |
| D2 (seq 332) | store_D2 17줄(**Pan** ±30 2단계 + 곡선 + `Phase 0 Thru 360` + `Speed 56`) · play_D2 — 전송 00:47:12 | 18줄 `OK` · 332 전송 전 비어 있음 | approved 2 → executed 18 | **판정 불가**(정지 아님) — 변화 0.02~0.03%(대조 0.00%, D1 1.3%). 2.1 에서 빔이 거의 수직 아래라 Pan 은 빔 축 회전뿐 → 기울인 기준으로 재시험 필요 |
| off_D2 | `Off Sequence 332` — 00:47:58 | `OK` | approved 1 → executed 1 | — |
| D3 (seq 333) | store_D3 17줄(Tilt ±30 2단계 + 곡선 + `Phase 0 Thru 360` + `Speed 56`) · play_D3 — 전송 00:48:03 | 18줄 `OK` · 333 전송 전 비어 있음 | approved 2 → executed 18 | **움직임·D1 보다 빠름** — 0.27초 간격 프레임 변화 1.0~1.3%(D1 은 1초 간격에 비슷한 변화) → 2박 vs 2마디와 맞음 |
| off_D3 | `Off Sequence 333` — 00:48:27 | `OK` | approved 1 → executed 1 | — |
| D4 (seq 334) | store_D4 21줄(Pan+Tilt ±30 2단계 + 곡선 + 위상 0/90 + `Speed 56`) · play_D4 — 전송 00:48:32 | 22줄 `OK` · 334 전송 전 비어 있음 | approved 2 → executed 22 | **움직임** — 프레임 변화 1.1~2.1%, 넷 중 최대 |
| off_D4 | `Off Sequence 334` — 00:49:22 | `OK` | approved 1 → executed 1 | — |
| 마무리 | `ClearAll`(승인 목록의 v0b_clear 묶음) — 00:49:23 | `OK` | approved 1 → executed 1 | — |

### 요약 (MOVER-D, Spiider, Group 12, 기준 2.1)

- 켜짐: `Dimmer` 만으로는 안 켜지고 `Dimmer2` 를 더하면 켜진다(v0a vs v0b, 한 줄 차이).
- 2단계 상대 페이저는 Spiider 에서도 돈다: Tilt 물결 2마디(D1)·2박(D3)·원(D4) 모두 움직임. 정지 대조 0.00%.
- Pan 물결(D2)은 판정 불가 — 2.1 에서 빔이 거의 수직 아래라 Pan 이 빔 축 회전으로만 나타남. D2' 로 재시험.
- 콘솔에 남은 것: 시퀀스 331~334(모두 Off), 쇼 저장 0. 판정은 리드 onPC 3D 캡처(Display 3) 프레임 차이와 감독 육안(v0a).

## D2' — Pan 물결 재시험, 기울인 기준 (설계·전부-거절, 실행 전)

- 스크립트 `probe_moverd_d2p.py`. 기준 줄은 2.1 대신 `Attribute 'Tilt' At 45` — t538 A0′ 의 실측 기준 줄(MegaPointe 에서 2단계 물결이 그 자리 중심으로 돈다고 감독 확인). 45 는 각도 값, 장비·그룹·프리셋 번호 아님. 선택·디머·BPM 은 데이터에서(Group 12 · Dimmer+Dimmer2 · Speed 56).
- **기울었는지 아는 법**: 첫 묶음 `t0_tilted_lit`(프로그래머만, Store 0)이 같은 기준으로 켜기만 한다 → 리드 3D 캡처로 바닥 스폿이 v0b(2.1, 장비 바로 아래)에서 옆으로 옮겨졌는지 본다. 옮겨지지 않았으면 D2' 를 보내지 않는다.
- 묶음 6: t0_tilted_lit → t0_clear → store_D2p(seq 335) → play_D2p → off_D2p → final_clear.
- 리허설 6/6 통과 · 실기 전부-거절: preflight `responder_ok`, 335 비어 있음, 쓰기 감사 rejected 6 / executed 0, 읽기 감사 executed 4, 문면 리허설과 동일, 금지 줄 0, Store 는 `Sequence 335 Cue 1` 한 줄.
- 승인 목록 `approval_t548_d2p.txt` — 26줄, sha256 `51fa4d5ad9cb1d88b86adc57a489c9a37491e36d6c374137999417f16ec4e0f6`.
