# t480 계획서 — 업로드 길 입구를 대화 길 조립기로 합친다 (REQ-003 완결, AC-017)

- 카드: t480 · SPEC-LDDESIGN-001 REQ-003 / AC-017 · 감독 결정 2026-09-28(t448 ① 재확인)
- 기준 트리: `d6ded877`(`origin/main`), 워크트리 `.claude/worktrees/t480`, 브랜치 `WT-upload-into-composer`
- 콘솔 쓰기: 0 (계획 단계, 코드 수정 0줄)

## 0. 요약

업로드 길을 조립기로 옮기는 일은 "호출 하나 바꾸기"가 아니다. 대화 길의 **콘솔 명령 생성기**가 세션 객체 안에 묶여 있고, 조립기의 입력(`UnifiedSongLightingPlan`)은 인터뷰 답을 전제로 만들어진다. 업로드 길에는 둘 다 없다. 그래서 3단계로 나눈다.

- **M1 (행동 변화 0)** — 대화 길 명령 생성기를 세션 밖 공용 모듈로 꺼낸다. 대화 길 명령 바이트 동일.
- **M2 (행동 변화 0, 병행 산출)** — 업로드 입력 → `UnifiedSongLightingPlan` 어댑터를 만들고, 업로드 길은 그대로 둔 채 "조립기로 만들었다면 나갈 명령"을 옆에서 뽑아 before/after diff 를 증거로 남긴다.
- **M3 (전환)** — `prepare_songcue` 가 조립기 길로 명령을 낸다. B 직접 호출 시험 정리, 8곡 게이트 재측정.

M1 은 어느 결정이 나와도 필요한 일이라 바로 착수한다. M3 은 아래 §4 의 결정 셋이 나와야 확정된다.

## 1. 실측 (d6ded877)

| 항목 | 값 | 명령 |
|---|---|---|
| tools.py 조립기 참조 / B 참조 | 0 / 6 | `grep -c` (ac_server_closeout.md 와 같은 기준) |
| B `build_songcue_bundle(` 시험 호출 | 17파일 · 55곳 | `grep -rl` / `grep -ro … \| wc -l` |
| A `compose_song_cue_bundle(` 시험 호출 | 10파일 · 40곳 | 같은 기준 (t448 때 8파일·25곳에서 늘었다) |
| `prepare_songcue` 를 부르는 시험 파일 | 20 | `grep -rl prepare_songcue server/tests` |
| 대화 길 명령 생성기 | `session.py:8287` `_reviewed_song_commands` — **세션 메서드** | 판독 |
| 그 생성기가 콘솔에서 읽는 것 | 포지션 프리셋 라벨(`:10557`), 페이저 슬롯(`:8371`), 흰색 프리셋(`:6272`), 기구 번호(fids), 레이어 매핑 | 판독 |
| 조립기 입력 조립 | `session.py:1906` `_build_unified_song_plan` — `MusicProfile`·인터뷰 기록(records)·리그 프로파일·`TimingPlan` 필요 | 판독 |
| 8곡 게이트 계산 | `server.concept.gates.evaluate_song` 만 쓴다 — 두 조립기 어느 쪽도 거치지 않는다 | `.moai/reports/t444/gen_gates_8songs.py` import |

## 2. 옮길 목록 — 업로드 길 입구가 지금 하는 일

`tools.py:3188-3700` `prepare_songcue` 기준.

| # | 지금 하는 일 | 조립기 길에서 | 처리 |
|---|---|---|---|
| 1 | 인자 검사(곡명·장르·타임코드 번호·구간·구간 이름·explicit_dynamics) | 그대로 | 유지 |
| 2 | 확정 분석 기록 기본값·불일치 보고(SONGCONFIRM) | 그대로 | 유지 |
| 3 | `parse_sections` | 그대로 | 유지 |
| 4 | **장르 → 룩 라이브러리 선택**(`select_genre`·`map_sections_to_looks`) | 조립기에 룩 라이브러리 개념 없음 | **결정 D1** |
| 5 | 곡 사이 룩 기억(t358 `song_look_memory`, `cross_song_looks`) | 룩이 없으면 의미 없음 | **결정 D1** |
| 6 | 마디 분할(`split_selections_for_density`, `plan_cue_density` 공유) | 대화 길도 `plan_cue_density` 사용 | 어댑터가 구간 목록으로 넘김 |
| 7 | 감독 주색 덮기(t441 `_override_songcue_main_color`) | 조립기는 `_section_palette_choice` 를 직접 씀(같은 함수) | 어댑터에서 records 로 넘김 |
| 8 | 컨셉 리포트(`build_concept_report_from_songcue_sections`) | 대화 길은 `build_concept_report` | 대화 길 것으로 교체 |
| 9 | 리그: 콘솔 `sequences`·`groups` 섹션 수집 | 조립기 명령은 포지션 프리셋·기구 번호·페이저 풀을 읽는다 | **결정 D2** |
| 10 | `build_songcue_bundle` (절정 상한·강조 사다리·드롭 앞 어둠·front fill·yield) | 조립기: 어둠·절정 블라인더·2박 복귀는 t462 로 이미 있음. 강조 사다리는 대화 길 자기 것 | **결정 D3** |
| 11 | 타임코드 슬롯 점검·`build_songcue_timing` | 대화 길 타이밍 경로 | 대화 길 것으로 교체 |
| 12 | 쓰기 게이트(`BatchRisk kind="songcue"`), 되읽기, `build_songcue_report` | 게이트는 유지. 보고서는 조립기 결과 기준으로 새로 | 유지 + 보고서 교체 |
| 13 | 운영자 인계(`operator_handoff_commands`) | 무관 | 유지 |

## 3. 콘솔 명령 변화 예상 (업로드 길)

- **지금**: 그룹 선택 + 룩 라이브러리 속성 값 줄 + `store_with_fade`, 강조 사다리 단계(zoom/iris·블라인더·스트로브·색 스냅).
- **바뀐 뒤**: 대화 길과 같은 모양 — 기구 번호 목록 + 라벨로 찾은 포지션 프리셋 + 밝기 % + RGB 색 값 줄 + 페이저 줄, 대화 길 강조 사다리(moving position hit / climax accent / white flash), 드롭 앞 어둠·절정 블라인더·2박 복귀(t462 위임, 기준값은 `songcue.py` 그대로).
- 즉 **명령은 거의 전부 바뀐다**. 증거는 M2 의 before/after diff(같은 입력, 명령 줄 단위)로 남긴다.
- 절정·사다리·어둠 **기준값**(`darkness_target`·`climax_cap_beats`·`LADDER_BLINDER_OR_FLASH`)은 `songcue.py` 한 곳에 남고 바이트 불변 — 조립기는 이미 그것을 불러다 쓴다(`song_cue_composer.py:34`).
- 8곡 게이트(75/29/0)는 두 조립기 모두와 무관한 계산이라 바뀌지 않을 것으로 본다 — M3 뒤 재측정으로 확인한다.

## 4. 리드(감독)가 정할 것

- **D1 장르 룩 라이브러리·곡 사이 룩 기억** — 조립기 길에는 룩이 없다. 옮기면 업로드 길에서 "장르 단어로 룩을 고른다"와 t358 곡 사이 중복 회피가 사라진다. (가) 받아들인다 — `genre` 인자는 `MusicProfile.genre` 로만 남긴다. (나) 조립기에 룩 선택을 새로 넣는다(별도 카드 규모).
  - 레인 기본값: **(가)**.
- **D2 포지션 프리셋이 없는 리그** — 대화 길 명령 생성기는 포지션 라벨을 콘솔 풀에서 찾고, 못 찾으면 **쓰기를 한 줄도 내지 않고 거부**한다. 업로드 길은 지금 그룹·시퀀스만 있으면 돈다. (가) 대화 길과 같은 규칙(없으면 거부). (나) 업로드 길은 못 찾으면 포지션 축을 끄고(`position_disabled_reason`, 이미 있는 장치) 나머지만 낸다.
  - 레인 기본값: **(나)** — 업로드 길이 오늘 되는 리그에서 갑자기 멈추지 않게.
- **D3 B 전용 기능(LDACCENT zoom/iris/스트로브/색 스냅 사다리·front fill·yield)** — t462 가 "대화 길에 자기 사다리가 있어 겹치면 한 큐에 액센트 둘" 이라며 n/a 로 둔 것들이다. 전환하면 생산 호출처가 0 이 되어 죽은 코드가 된다. (가) `build_songcue_bundle` 과 그것만 부르는 시험을 은퇴시킨다(기준값 함수·상수는 남김). (나) 코드는 남기고 시험만 "생산 호출처 없음"을 명시.
  - 레인 기본값: **(가)** — t448 이 경고한 "시험은 초록인데 기능은 죽은" 상태를 남기지 않는다. 다만 LDACCENT/LDRETURN SPEC(completed) 시험이 줄어드는 것이라 리드 확인이 필요하다.

## 5. 단계별 완료 조건

| 단계 | 완료 조건 | 증거 |
|---|---|---|
| M1 | 대화 길 명령 바이트 동일(세션 시험 전부 통과 + 대표 곡 명령 덤프 before/after `cmp`) | `m1_session_dump.{before,after}.txt` |
| M2 | 어댑터가 업로드 입력 8곡(pilot_baseline) × 장르 2 로 조립기 번들을 만든다, 업로드 길 명령은 바이트 동일 | `m2_upload_commands.{b,a}.txt` + diff 요약 |
| M3 | `prepare_songcue` 가 조립기 길 사용, tools.py 조립기 참조 ≥1·B 참조 0, 8곡 게이트 75/29/0(바뀌면 곡별 사유), 기준값 바이트 불변(`git diff` 에 `darkness_target`·`climax_cap_beats`·`LADDER_*` 변화 0), 콘솔 쓰기 0 | `verdict.md` |

## 6. 안 잰 것 (계획 시점)

- 명령 생성기를 세션 밖으로 꺼낼 때 끌려 나오는 의존 개수(세션 상태 필드 수)는 아직 세지 않았다 — M1 착수 첫 일로 잰다.
- 조립기 길이 업로드 입력(`dynamics` 1..5 숫자, mood 없음)으로 D 레벨을 어떻게 정할지는 판독만 했다(`section.d_level` 경로가 있음, `session.py:2017`). M2 에서 실행으로 확인한다.
