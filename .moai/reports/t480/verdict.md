# t480 판정서 — 업로드 길을 대화 길 조립기로 합쳤다 (SPEC-LDDESIGN-001 REQ-003 · AC-017)

- 카드: t480 · 감독 결정 2026-09-28(t448 ① 재확인) · 리드 결정 D1~D4(아래 §1)
- 브랜치: `WT-upload-into-composer` · 기준 `d6ded877`(`origin/main`)
- 전환 커밋: `00c2c2ee`(M3) · 재고 갱신 `bf78b04f` · 정리(D3)는 같은 PR 의 뒤 커밋
- 콘솔 쓰기: 0 — 모든 측정은 가짜 실행 포트·가짜 상태 포트 위에서 했다

## 0. 요약

곡 업로드 길(`prepare_songcue`)이 이제 대화 길과 **같은 계획 조립·같은 조립기·같은 명령 생성기**로 큐를 만든다.

| 항목 | 전 (`d6ded877`) | 후 |
|---|---|---|
| 업로드 길이 부르는 조립기 | `build_songcue_bundle`(룩 라이브러리) | `build_upload_song_plan` → `compose_song_cue_bundle` → `reviewed_song_commands` |
| `tools.py` 조립기 참조 / 옛 조립기 호출 | 0 / 6 | `prepare_songcue` 안에서 `compose_song_cue_bundle` 호출 1 · `build_songcue_bundle` 호출 0 (`test_upload_composer_t480.py::TestOneComposer` 가 AST 로 잰다) |
| 대화 길 콘솔 명령 | — | 바이트 동일(46회 호출 · 938줄 덤프 `cmp`) |
| 절정·사다리·어둠 기준값 | `server/looks/songcue.py` | 같은 파일, **변경 0줄**(`git diff d6ded877 -- server/looks/songcue.py server/design/song_cue_composer.py` → 0줄) |
| 8곡 게이트 | PASS 75 · n/a 29 · FAIL 0 (`t444/gates_8songs.txt`) | 같은 값, 출력 파일 **바이트 동일**(`gates_8songs_after.txt`) |

AC-017 은 이제 구조로 충족된다 — 업로드 입력은 모양만 바뀌어 대화 길이 부르는 그 계획 조립 함수로 들어간다(`TestOneComposer::test_the_upload_plan_is_the_chat_paths_plan_for_the_same_input`: 같은 입력이면 두 길의 계획 구간·음악 프로필이 같다).

## 1. 결정과 근거

| 번호 | 결정(리드·감독 2026-09-28) | 근거(실측) | 구현 |
|---|---|---|---|
| D1 | 업로드 길의 장르 룩 라이브러리·곡 사이 룩 기억은 사라져도 된다 | 조립기에는 룩 라이브러리 개념이 없다(`plan.md` §2 #4·#5) | `genre` 는 음악 프로필 장르로만 남아 D4 팔레트를 정한다. 곡 사이 기억(t358)은 이 길에서 쓰이지 않는다 |
| D2 | 선택 인자 `preset_start` — 주면 라벨로 슬롯, 없으면 포지션 축을 끄고 사유 명시. 번호 지어내기 금지 | 대화 길은 프리셋 시작 번호를 감독 카드로 받는데, 업로드 길(LLM 도구)은 그 입력도 카드도 없다 | 스키마에 `preset_start` 추가(선택). 없으면 `position_disabled_reason` 으로 축을 끄고 회신 `report.notes` 에 적는다. 있으면 `console_slots.resolve_position_preset_labels` 로 풀 2 에서 라벨을 찾고, 못 찾으면 쓰기 0 으로 거절 |
| D3 | `build_songcue_bundle`·전용 시험 은퇴 — 전환이 초록인 뒤 같은 PR 의 별도 커밋. 기준값 함수는 남긴다 | 전환 뒤 생산 호출처 0(`d3_reach.txt`: 운영 코드가 닿지 않는 이름 127개 · `songcue.py` 2,322줄 · `songcue_report.py` 257줄) | §7 |
| D4 | 인터뷰가 없으면 Q2 추천 1순위를 팔레트로, 회신에 「팔레트: 인터뷰 없음 → Q2 추천 '<라벨>'」. 영어 장르 5단어 → §7 한국어 키 | 인터뷰 없으면 주색 기본값 '중립' 이 RGB 로 안 풀려 색 줄 0(`m2_smoke.txt` 실측) | `upload_song_plan.upload_profile` 이 `_q2_color_candidates(profile)[0]` 을 쓴다. `UPLOAD_GENRE_KEYS` = rock→록 · edm→edm · ballad→발라드 · pop→팝 · metal→메탈. 표에 없는 단어는 무드 표로 떨어지고 그 사유를 회신에 적는다 |

## 2. 어떻게 옮겼나 (커밋 순서)

모든 이동 단계는 **대화 길 명령 바이트 동일**을 매번 쟀다(`m1_dump.py` — 대화 길 명령 생성기를 감싸 시험 8개 파일 실행 중 나온 명령 전부를 적는다. 대조 2회 `cmp` 동일로 결정성 확인).

| 커밋 | 내용 | 증거 |
|---|---|---|
| `6d1d7992` M1 | 세션 안의 계획 조립·명령 값 줄 헬퍼 48개 이름(775줄, 전이 폐포)을 `server/design/song_cue_render.py` 로 이동. 명령 반복문을 콘솔을 읽지 않는 순수 함수 `reviewed_song_commands` 로 분리 | `m1_closure.txt` · `m1_session_dump.{before,after}.txt` cmp 동일 · 영향 시험 2290/25 |
| `75060ce3` M1b | 페이저 카탈로그(`phaser_catalog.py`)·콘솔 풀 판독기(`console_slots.py`) 이동. 세션 메서드는 이름·프로브 id 그대로 위임 | `m1b_session_dump.after.txt` cmp 동일 · 2290/25 · 1409/2 |
| `036b3454` M2a | 마디 분할·확정 역할·블라인더 판정 10개 이름(174줄) 이동 | `m2a_session_dump.after.txt` cmp 동일 |
| `4b303989` M2b | 업로드 입력 → 계획 어댑터(`upload_song_plan.py`) | `m2_smoke.txt` |
| `a75ccc09` | 가짜 콘솔(패치·기종·프리셋 풀) + 전환 전 업로드 덤프 | `m3_upload_dump.before.txt` |
| `00c2c2ee` M3 | `prepare_songcue` 전환 + 보고서(`upload_song_report.py`) + 시험 정리 | 아래 §3~§5 |
| `bf78b04f` | `tools.py` 헝크 재고 82 → 83 | `measure_hunks.out.txt` |

층 경계: `server/orchestrator/tools.py` 는 `server.web` 을 import 할 수 없다. 그래서 대화 길 코드를 세션 밖(`server/design/`)으로 먼저 꺼낸 뒤 두 길이 같이 쓰게 했다. 꺼낸 코드는 `server.design` · `server.spatial` · `server.looks` 만 import 한다(`m1_closure.txt` import 목록).

## 3. 업로드 길 콘솔 명령 — 전후 비교

같은 가짜 콘솔(`server/tests/upload_console_fixture.py`)·같은 입력 16조합(곡 2 × 장르 2 × 인터뷰 유무 × `preset_start` 유무)으로 실제 입구를 쐈다(`m3_upload_dump.py`).

| 셈 | 전 | 후 | 이유 |
|---|---|---|---|
| 오류 | 0/16 | 0/16 | — |
| `Store Sequence` | 148 | 152 | Rain·edm 4조합에서 전에는 큐 1개가 건너뛰어졌다(보고 「섹션 12개 · 큐 11개 · 건너뜀 1개」 — 사유는 덤프에 남기지 않아 안 쟀다). 조립기 길은 12구간 전부 저장 |
| 선택 방식 | `Group <n>`(룩의 역할 그룹) 238줄 | `Fixture <패치 번호들>` 478줄 | D1 — 룩 역할 그룹이 아니라 패치된 기구 번호에 저장한다(대화 길과 같다) |
| `Group` 줄 | 238 | 32 | 남은 것은 절정 블라인더 — `Group 17`(이름 BLINDER) 켜기 16 · 다음 큐에서 끄기 16 |
| `At Preset` | 0 | 212 | 포지션 프리셋(`preset_start` 준 8조합, 큐마다 1) + 컬러 페이저 프리셋 |
| `ColorRGB` 줄 | 228 | 114 | 전: 역할 그룹마다 1. 후: 큐마다 1(전 기구). **edm·인터뷰 없음 4조합은 0** — §6 t483 |
| `Label Sequence` / `Store Timecode` | 16 / 16 | 16 / 16 | 시퀀스 이름표·타임코드 이름은 옛 규칙(`_ascii_label`, 첫 저장 뒤 한 번) 그대로 유지 |
| `TrigTime` | 148 | 152 | 저장 큐 수를 따른다 |

같은 구간의 대표 예(Ice cream · rock · 인터뷰 없음 · `preset_start=21`):

```
전: Group 15 / Attribute 'Dimmer' At 25 ; ColorRGB 60/8/30 / Group 12 / ... Store Sequence 3 Cue 1 'Intro' CueFade 2
후: Fixture 101 + 102 + 103 + 104 ; At Preset 2.21 / ... 'Dimmer' At 50 / ... ColorRGB 100/0/0 / Store Sequence 3 Cue 1 'Intro' CueFade 2
```

명령은 거의 전부 바뀌었다 — 계획서 §3 에서 예상한 그대로다. 인터뷰가 있으면 장르가 명령을 바꾸지 않는다(같은 sha — 팔레트가 인터뷰 답에서 오므로).

## 4. 시험

| 묶음 | 결과 |
|---|---|
| 영향 시험 90파일(session·songcue 관련) | 2235 passed · 25 skipped (전환 전 2290 — 차이 55 는 §5 에서 뺀 시험 수와 같다) |
| `server.web` 추가 50파일 | 1409 passed · 2 skipped (기준선과 같다) |
| `tools`·`server.design` 을 쓰는 나머지 103파일 | 4063 passed · 3 skipped |
| 신규 `test_upload_composer_t480.py` | 22 passed |
| 헝크 재고·형제 게이트(`test_songcue_bundle.py` · `test_overlap_preserve.py`) | 99 passed(재고 갱신 뒤, 커밋 **뒤에** 잼) |

## 5. 뺀 시험과 바꾼 시험 (55건 제거)

- **뺀 것 — 옛 동작을 재던 시험.** 결정으로 사라진 동작이라 성립하지 않거나(음성 대조가 깨짐), 무엇을 넣어도 통과하는 공허한 시험이 됐다.
  - `test_songcue_rig_aware_look.py` 48건 — 실제 입구로 「역할 그룹이 묶여야 저장」을 재던 시험과 O/X 행렬. 이제 기구 번호에 저장하므로 양성은 공허, 음성은 불성립.
  - `test_songcue_cross_song.py` 4건 — 실제 입구의 곡 사이 룩 기억(D1).
  - `test_songcue_cue_density.py` 3건 순감 — 룩 후보 수 기준 분할·못 묶이는 룩 접힘.
  - `test_songcue_tool.py` 「역할 미결속으로 0건 저장」 1건 → 「패치를 못 읽으면 쓰기 전 거절」 1건으로 교체.
- **바꾼 것 — 같은 계약을 새 모양으로 다시 잰다.**
  - 이름은 D 레벨을 정하지 않는다(t274): 룩 Dimmer 10/30/50 대신 보고서 `d_level` [1, 3, 5] 로 잰다.
  - 확정 기본값의 큐 라벨: `S1/S2/S3` → 대화 길과 같은 역할+회차(`Intro · Verse 1 · Finale`, t391).
  - 마디 분할: 측정 BPM 이면 쪼갠다(3구간 → 4큐), BPM 없으면 안 쪼갠다, 곡 끝을 알면 마지막 구간도 쪼갠다(`split_swap` 에서 5큐 · 오프셋 [0, 14.861, 32, 47, 61.861]).
  - 인터뷰 없음의 색: 룩 색(crimson) 대신 Q2 추천 팔레트 출처를 잰다(t441·t444).
  - 건너뜀 고지: 보고서가 문장의 주인이라는 계약을 `UploadSongReport.to_operator_notice` 단위로 잰다.

## 6. 발견한 것 (이 카드에서 고치지 않음)

1. **edm Q2 추천 팔레트의 주색이 RGB 로 안 풀린다** — §7 표 문구 「단색 볼드, 퍼플/레드/화이트」의 첫 토큰이 '단색'. 대화 길에서 감독이 그 옵션을 골라도 같다. 업로드 길 edm·인터뷰 없음 곡은 색 줄 0(회신에 색 실패 사유는 나간다). **카드 t483**(리드 생성, 다른 레인).
2. **쪼갠 큐 이름이 `Intro 12` 처럼 저장된다** — `_disambiguate_split_names` 가 붙인 `(1/2)` 를 콘솔 라벨 정리(`_safe_song_cue_name`)가 괄호·빗금을 지워 「12」로 만든다. 대화 길 기존 동작이며 업로드 길도 이제 같다. 카드 후보.
3. **헝크 재고 시험은 커밋 전에 공허하게 통과한다** — 전환 뒤 영향 시험을 돌렸을 때 `test_tools_hunks_are_only_songcue_registration_and_not_dedupe_or_state` 는 초록이었지만, 그것은 커밋 전이라 내 변경을 안 본 결과였다(그 시험 주석이 경고한 t350 함정). 푸시 전 검사가 커밋 뒤 실패로 잡았고, 커밋 뒤에 재어 갱신했다.

## 7. D3 (조립기 은퇴) — 진행 상태

`d3_reach.txt` 가 범위를 잰다: 운영 코드가 import 하는 이름(23개)에서 닿지 않는 이름 127개. 그것을 import 하는 시험 파일 22개. 그중 일부(`test_songcue_timing.py` 등)는 **남는 함수**(타이밍·시퀀스 번호)를 시험하면서 옛 조립기를 재료로만 쓰므로, 파일째 지우지 않고 재료를 바꿔야 한다. 이 절은 D3 커밋 뒤에 채운다.

## 8. 안 잰 것

- **실기 콘솔.** 조립기 길 명령은 대화 길에서 실기로 검증된 모양(`Fixture … ; At Preset` · RGB 값 줄 · 페이저 프리셋)이지만, 업로드 입구로 실기에 쏜 적은 없다.
- **`preset_start` 를 준 업로드 곡의 포지션 선택.** 인터뷰가 없으면 모든 구간이 기본 포지션(`Home`, 슬롯 21)이다 — 대화 길에서 Q4(공간 서사)를 안 답한 것과 같다. 구간마다 다른 포지션은 인터뷰가 있어야 나온다.
- **W 채널·흰색 프리셋.** 업로드 길은 W 기구 판별(`_w_capable_fids`, 세션 메서드)을 하지 않고 `w_fids` 를 빈 집합으로 둔다 — 흰색 큐도 RGB 줄만 낸다(대화 길에서 W 판별이 실패한 경우와 같다).
- **레이어 매핑(Back 레이어 값 줄).** 업로드 길은 감독 확인 카드를 띄울 수 없어 레이어 매핑 없이 간다(대화 길 단일 레이어 경고와 같은 상태).
- **8곡 게이트는 두 조립기와 무관한 계산이다**(`server.concept.gates.evaluate_song` 만 쓴다). 바이트 동일은 「전환이 게이트를 흔들지 않았다」의 증거이지 「업로드 길 큐 품질이 게이트를 통과한다」의 증거가 아니다.
- CI 결과는 PR 에서 확인한다(이 문서 작성 시점 미확인).

## 9. 남은 위험

- 업로드 길은 이제 **패치를 읽어야** 돈다. 패치를 못 읽는 콘솔에서는 예전(그룹·시퀀스만 있으면 동작)과 달리 쓰기 전에 거절한다.
- 곡 사이 룩 기억(`SongLookMemory`)은 세션이 여전히 만들어 넘기지만 업로드 길에서 쓰이지 않는다 — D3 에서 배선 정리 여부를 판단한다.
