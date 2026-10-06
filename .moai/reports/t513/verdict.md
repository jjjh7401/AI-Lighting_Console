# t513 판정서 — LOVE ATTACK 기존 앱 연출 실기 승인 파일 준비 (실기 쓰기 0)

- 카드: t513 · SPEC-LDRHYTHM-001 AC-010 준비 · 브랜치 `WT-baseline-live` · 워크트리 `.claude/worktrees/t513`
- base: `origin/main` `cea25c04` (`git merge-base --is-ancestor cea25c04 HEAD` 성공). t510 base `e7eaf690` 이후 `server/ src/ ui/ pyproject.toml uv.lock` 변경 0(`git diff --stat` 빈 출력) — 앱은 t510 과 같다
- 콘솔: grandMA3 onPC · 응답기 `CopilotResponder` 1.6.5 · 송신 8000 / 수신 9005
- 음원: `/Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3` — 저장소 밖, 커밋 안 함

## 판정: A안 실기 쓰기 완료 — 승인본 = 송신본 두 단계 모두 PASS, 덮어쓰기·삭제 0 (§7)

(§1~§6 은 승인 요청 시점 기록이다. 그때는 실기 쓰기 0, `ClearAll` 송신 0 이었다.)

🔴 **전제 하나가 실기와 다르다.** 카드는 「211~218·11~18 사용 중」이라 했지만, 지금 콘솔에 떠 있는 쇼에는 시퀀스 211~218·타임코드 11~18 이 **하나도 없다**(run0). t498 이 쓴 211·11, t501 의 213 이 모두 없으므로, 지금 쇼는 그 쓰기들이 저장된 쇼가 아니다(어느 쇼인지는 응답기로 못 읽는다 — t498 §6). 그래도 카드 지시대로 211~218·11~18 대역은 피해서 **시퀀스 219 · 타임코드 19** 를 제안한다.

🔴 **실기는 가짜 콘솔과 다른 경로를 탄다 — 승인 요청이 1번이 아니라 4번이다.** 실기 풀에 페이저 3종이 없어서 앱이 먼저 페이저 프리셋 3개를 새로 만들자고 한다(REQ-LDRENDER-011 사전 생성). 그래서 승인 방식이 두 갈래로 나뉜다(§4).

## 1. 빈 번호 판독 (읽기 전용)

| 풀 | 지금 있는 번호 | 제안 | 근거 |
|---|---|---|---|
| 시퀀스 | 1~15 · 210 · 1999 · 2000 (18개, 잘림 없음) | **219** | `run0_readonly_state.txt` · 직접 경로 `Sequences/219` → `path segment not found`(`run0b_number_check.txt`) |
| 타임코드 | 1 · 2 · 7 · 8 · 9 (5개) | **19** | 같은 파일 · `Timecodes/19` → `path segment not found` |
| 프리셋 4(Color) | 1~8 · 32 | 페이저 4.9 · 4.10 (A안) | `run4_preset_pools.txt` · `PresetPools/4/9` 없음 |
| 프리셋 21(All 1) | 1~6 | 페이저 21.7 (A안) | 같은 파일 · `PresetPools/21/7` 없음 |
| 프리셋 2(Position) | 1~6 · 21~30 | 새로 쓰기 0 (2.21~2.30 재사용) | `run0_readonly_state.txt` |
| 그룹 | 1~18, 이름이 t510 `REAL_GROUPS` 와 같음 | — | 같은 파일 |

- 풀 번호 `i` = 객체 `NO` 확인: 시퀀스 210·2000, 타임코드 9 의 `NO` 가 각각 210·2000·9(`run0b_number_check.txt`)

## 2. 가짜 콘솔 리허설 (t510 경로, 번호만 219/19)

| # | 주장 | 명령 | 출력(요지) |
|---|---|---|---|
| F1 | t510 과 번호만 다르다 | `diff .moai/reports/t510/rehearse_song.py .moai/reports/t513/rehearse_song.py` | 머리말 + `INSTRUCTION` 한 줄 |
| F2 | 앱 경로 끝까지 | `uv run python .moai/reports/t513/rehearse_song.py "<음원>" .moai/reports/t513/run1_fake` | exit 0 · `commands=190 approvals=1 cards=9 events=7` |
| F3 | 승인 = 송신 · 결정성 · t510 대비 | `uv run python .moai/reports/t513/compare_fake.py` | `approved==sent True` · `run1==run2 True` · 219→211·19→11 바꾸면 t510 송신과 **차이 0줄** — `compare_fake.txt` |

## 3. 실기 전부-거절 (쓰기 0)

도구 `real_console.py`(t498 복사)에 두 겹 안전망을 넣었다.
- (a) 앱이 거절 뒤 보내는 프로그래머 정리 `ClearAll`(`server/web/session.py` `song-design-cleanup`)을 세션 레지스트리에서 가로채 기록만 한다 — 리드 지시 「ClearAll 금지」. 앱 회신은 「프로그래머는 ClearAll로 정리했습니다」라고 쓰지만 **실제로 보내지 않았다**
- (b) 콘솔 링크의 실행 경로(`_execute`)를 막아 어떤 명령도 콘솔로 못 나간다. 양성 대조: 막지 않으면 송신 1, 막으면 송신 0 — `control_exec_block.txt`

| # | 주장 | 명령 | 출력(요지) |
|---|---|---|---|
| R1 | 쓰기 0 | `uv run python .moai/reports/t513/real_console.py song .moai/reports/t513/run3_real_denyall` | `blocked_exec=0 intercepted_cleanup=[['ClearAll']] queries=1039` · `approval_requests=4 approved=0 lines=[17, 18, 21, 201]` |
| R2 | 콘솔에 간 것은 읽기뿐 | 감사 로그 `run3_real_denyall/audit/*.jsonl` 종류별 집계 | `props_query` 465 · `property_query` 119 · `state_query` 455 · `rejected` 4 · 명령 실행 0 |
| R3 | 결정성 | 같은 명령 run5 → `cmp` 요청 4개 | 4개 모두 바이트 동일 |
| R4 | 본 큐 묶음 대 가짜 콘솔 | `uv run python .moai/reports/t513/classify_real_vs_fake.py` | 실기 201 = 가짜 190 + **W 0 줄 11개**(큐마다 1줄, MOVER-D 521~528 · WASH-U/D). 설명 안 되는 줄 0 · 가짜에만 있는 줄 0 — `classify_real_vs_fake.txt` |
| R5 | 본 큐 묶음의 쓰기 대상 | 요청 4 동사 집계 | `Store Sequence 219` 큐 11개(1~10·9.5) · `Set Cue` 22 · `Store Timecode 19` · `Set Timecode 19 Property` 1 · `Assign Sequence 219 At Timecode` 1. 프리셋 저장·삭제·`SaveShow` 0 |

### 페이저 풀 응답 차이 (카드 ⑤) — 실제 줄 수

| | 가짜 콘솔 | 실기 |
|---|---|---|
| 페이저 사전 생성 요청 | 0 | **3** — Breathe Warm 17줄(`Store Preset 4.9`) · Finale Slam 18줄(`Store Preset 21.7`) · Wave CM 21줄(`Store Preset 4.9`) |
| 본 큐 묶음의 페이저 호출 줄 | 0 | 0 (사전 생성이 거절돼 미해결) |

- Breathe Warm 과 Wave CM 이 둘 다 4.9 인 것은 **거절 때문**이다. 앱은 페이저마다 풀을 다시 읽고 가장 작은 빈 번호를 고른다(`server/web/session.py` `_pregenerate_missing_phasers`, `server/fx/instantiate.py` `select_preset_number`). Breathe Warm 이 승인돼 4.9 에 저장되면 Wave CM 은 4.10 으로 간다 — **코드 판독 추정**, 실기로 안 쟀다. 덮어쓰기는 아니다(점유 슬롯이면 `PRESET_OCCUPIED` 로 거절)

## 4. 승인 요청 — 두 갈래

승인 도구는 요청 명령 목록이 승인 파일과 **글자까지 같을 때만** 승인한다(t498 방식, `--approve <폴더>`). 맞지 않는 요청은 거절되고 콘솔에 아무것도 안 간다.

### A안 — 앱 그대로(페이저 생성 포함), 3단계

| 단계 | 내용 | 명령 | 콘솔에 남는 것 |
|---|---|---|---|
| A1 쓰기 | 페이저 3개 생성, 본 큐 묶음은 거절 | `uv run python .moai/reports/t513/real_console.py song .moai/reports/t513/run6_A1 --approve .moai/reports/t513/approve_A_stage1_phasers` | 프리셋 4.9 Breathe Warm · 21.7 Finale Slam · 4.10 Wave CM |
| A2 읽기 | 전부-거절 다시 → 페이저가 풀에 있으니 본 큐 묶음만 1건 | `… real_console.py song .moai/reports/t513/run7_A2_denyall` | 없음 |
| A3 쓰기 | A2 의 요청 파일 그대로 승인 | `… real_console.py song .moai/reports/t513/run8_A3 --approve .moai/reports/t513/run7_A2_denyall` | 시퀀스 219 · 타임코드 19 |

- 파일: `approve_A_stage1_phasers/approval_request_{1,2,3}.txt` — 1·2 는 실기 요청 그대로, 3 은 `Preset 4.9`→`4.10` 두 줄만 바꿈(추정에 기댄다). 추정이 틀리면 요청 3 이 거절되고 Wave CM 만 빠진 채 끝난다(쓰기는 1·2 뿐)
- A3 전에 A2 의 요청과 지금 요청 4 를 비교해 차이가 **페이저 호출 줄뿐**인지 확인하고 보고한다
- 실기 송신은 t510 보고서의 기준선(페이저 0줄)과 **다르다** — 실제 앱이 이 콘솔에서 하는 일이다

### B안 — 페이저 없이(지금 잰 것 그대로), 1단계

| 단계 | 내용 | 명령 | 콘솔에 남는 것 |
|---|---|---|---|
| B1 쓰기 | 페이저 생성 3건은 거절, 본 큐 묶음만 승인 | `uv run python .moai/reports/t513/real_console.py song .moai/reports/t513/run6_B1 --approve .moai/reports/t513/approve_B_nophaser` | 시퀀스 219 · 타임코드 19 |

- 파일: `approve_B_nophaser/approval_request_4.txt` (201줄, sha256 `b60614c8…f8ac8e0`) — 전부-거절 2회와 바이트 동일한 목록이라 추정이 없다
- t510 보고서의 기준선(페이저 0줄)과 W 0 줄 11개 말고는 같다

### 두 안 공통

- 쇼 저장: 앱 자동 `SaveShow` 는 보내지 않고 기록만 한다. 쓰기 직후 감독이 콘솔에서 **복사본에 직접 저장**한다(t498 §4-7 — 저장 안 한 쓰기는 재시작에서 사라졌다)
- 덮어쓰기·삭제·`ClearAll` 송신 0: 쓰기 대상은 전부 지금 빈 번호다. 거절 뒤 정리 `ClearAll` 은 두 모드 모두 가로챈다. 승인된 묶음 **안의** `ClearAll`(큐마다 프로그래머 비우기, 본 큐 묶음 11줄 · 페이저 묶음 각 2줄)은 앱의 큐 저장 절차 그 자체라 남아 있다 — 이것도 막아야 하면 승인 전에 알려 달라
- 쓰기 직전에 run0 읽기를 다시 해 219·19(A안은 4.9·4.10·21.7 포함)가 여전히 빈지 확인한다

## 5. 안 잰 것

- 지금 떠 있는 쇼의 이름 · 211~218 이 사라진 이유(응답기로 쇼 이름을 못 읽는다)
- A안 요청 3 의 4.10 — 코드 판독 추정
- A안 A2 에서 나올 본 큐 묶음의 정확한 줄(페이저 호출 줄 형식·개수)
- 기구 목록이 지금 쇼와 t498 판독(86대)이 같은지 — 실기 요청 4 의 기구 목록을 따로 대조하지 않았다(분류는 `<SET>` 정규화). 가짜 리허설의 좌표 대역은 t498 목록이다
- 재생·육안 — 승인 뒤 감독 몫

## 6. 산출물

`.moai/reports/t513/` — `run0*` 읽기 · `run1_fake`·`run2_fake` 리허설 · `run3_real_denyall`·`run5_real_denyall_again` 실기 전부-거절 · `run4_preset_pools.txt` · `approve_A_stage1_phasers/` · `approve_B_nophaser/` · 스크립트 `probe_steps.py` `rehearse_song.py` `compare_fake.py` `real_console.py` `control_exec_block.py` `classify_real_vs_fake.py` `reply_notices.py`. 제품 코드 변경 0.

## 7. 실행 (2026-10-06, 감독 A안 승인 · 리드 경유)

| 단계 | 명령 | 결과 | 근거 |
|---|---|---|---|
| A1 직전 확인 | `probe_steps.py steps_prewrite.txt` | 219·19·4.9·4.10·21.7 전부 `path segment not found` · 풀은 run0 과 같음 | `run6a_prewrite_check.txt` |
| A1 쓰기 | `real_console.py song run6_A1 --approve approve_A_stage1_phasers` | 승인 3/3(요청 1~3 = 승인 파일 `cmp` 동일 — 4.10 추정 맞음) · 본 묶음 210줄은 승인 파일에 없어 거절 · 정리 `ClearAll` 가로챔 · `SaveShow` 기록만 3 | `run6_A1.stdout.txt` |
| A1 대조 | `approval_vs_sent.py run6_A1/approved_combined.txt run6_A1/audit` | 승인 56 = 송신 56 · sha256 동일 · 송신 안 됨 0 · 승인 안 됨 0 · **PASS** | `run6_A1_approval_vs_sent.txt` |
| A1 되읽기 | `pool_snapshot.py` run6a/run0 대 run6b | 추가: 4.9 Breathe Warm · 4.10 Wave CM · 21.7 Finale Slam 뿐. 제거·이름 변경 0 | `run6c_diff_run0_vs_after_A1.txt` |
| A2 읽기 | `real_console.py song run7_A2_denyall` | 요청 1건 210줄 = A1 의 거절된 요청 4 와 바이트 동일. 이전 요청 4(201) 대비 제거 0 · 추가 9 전부 페이저 호출(4.9×5 · 4.10×3 · 21.7×1) | `diff_A2_vs_req4.txt` |
| A3 직전 확인 | `probe_steps.py steps_after_A1.txt` | A1 뒤와 전 풀 동일, 219·19 빔 | `run8a_prewrite_A3.txt` |
| A3 쓰기 | `real_console.py song run8_A3 --approve run7_A2_denyall/approval_request_1.txt` | 승인 1/1(요청 = 승인 파일 `cmp` 동일) · 정리 `ClearAll` 0 · `SaveShow` 기록만 1 · 앱 되읽기 「검증 완료: DataPool/Sequences/219, DataPool/Timecodes/19」 | `run8_A3.stdout.txt`, `run8_A3/replies.json` |
| A3 대조 | `approval_vs_sent.py run7_A2_denyall/approval_request_1.txt run8_A3/audit` | 승인 210 = 송신 210 · sha256 `639a8f2e…` 동일 · **PASS** | `run8_A3_approval_vs_sent.txt` |
| A3 되읽기 | `pool_snapshot.py` run8a 대 run8b(시퀀스 2쪽까지) | 추가: 시퀀스 219(Intro~Finale 11큐 + OffCue·CueZero) · 타임코드 19 「Sequence 219 Timecode」. 그 밖 제거·변경 0 | `run8b_after_A3.txt` |

- 앱 회신의 확인 포인트: 「절정 연출 미반영: blinder_six_row_absent」(t498 발견 4 와 같은 갈래) · 린트 5건(G1 1 · V1 4) — 연출 판정은 감독 몫
- 🔴 **쇼 저장 안 함.** 앱은 `SaveShow` 를 한 줄도 보내지 않았다. 감독이 콘솔에서 복사본에 직접 저장해야 쓰기가 남는다(t498 소실 전례)

### 콘솔에 남은 것

- 시퀀스 219 「Sequence 219」 큐 11개 · 타임코드 19 「Sequence 219 Timecode」 · 프리셋 4.9 Breathe Warm · 4.10 Wave CM · 21.7 Finale Slam
- 안 잰 것: 큐 안의 값(밝기·색·포지션·페이저 참조 보존) — 응답기로 못 읽는다. 재생·육안은 감독 몫
