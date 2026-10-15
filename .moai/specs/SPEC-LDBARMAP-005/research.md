# SPEC-LDBARMAP-005 — research.md

plan-phase의 코드·문서 조사다. **읽고 센 것이지 돌려 본 것이 아니다** — 시험을 하나도 돌리지 않았고 코드를 바꾸지 않았다. 명령과 출력 원문은 부록 A에 있다(요약 문장이 아니라 명령이 낸 글자 그대로). 본문의 줄 번호는 트리 `bef3e16d`(이 워크트리의 HEAD, 브랜치 `WT-barmap-meter`) 기준이다.

**출처 표기.** `[measured: <명령> @ <트리>]` 이 plan-phase가 실행한 명령의 출력 · `[carried: <파일:줄>]` 다른 문서·코드에서 옮긴 값 · `[predicted]` 측정 전에 정한 값(사전 등록 문턱, 합성 매개변수, 산술, 규모 추정; 관측이 아니다).

## §1. 리드 진술과 전제의 대조

리드 문면에 있던 인용을 열어 읽어 맞춰 보았다. 틀린 곳은 표에 그대로 적는다.

| 리드 진술 | 실제 | 판정 |
|---|---|---|
| SPEC-002 `spec.md` row 29 = 2026-10-14 결정 기록 | 줄 29가 결정 기록 행이다 [measured: `Read SPEC-LDBARMAP-002/spec.md` 줄 29 @ bef3e16d]. 이 표의 SPEC 본문 줄 대조는 모두 파일을 열어 읽은 것이다 | 맞음 |
| `:71` = P5 「분석기는 4/4 전용이다」 | 맞음 | 맞음 |
| `:126` = REQ-LDBARENTRY-015 | 맞음 | 맞음 |
| `:143–150` D2 표, `:147` (가), `:148` (나) | 맞음 | 맞음 |
| `:235` = 「분석기 `server/audio/bar_map.py`는 이 SPEC이 수정하지 않는다」 | 줄 235가 그 불릿이고 제목은 줄 233(`### Out of Scope — 일반 박자표`)이다 | 맞음. **추가 발견**: 줄 244에도 같은 취지의 제외(`derive_bars`·`detect_beat_grid` 수정 금지)가 있다 → spec.md §3.1 R-4 |
| SPEC-001 `:71` = REQ-LDBARMAP-004, `:107` = REQ-LDBARMAP-016 | 맞음 | 맞음 |
| 「SPEC-001 §5 item 1 (약 `:147-160`)」이 일반 규칙을 이미 말한다 | 일반 규칙은 있으나(`:147`, `:160`) 파일의 번호는 **열린 결정 0**이다. 「항목 1」(`:163`)은 LDARRANGE와의 경계 서술이다 | 번호만 어긋남. 내용은 맞음 → spec.md §3.1 R-8 |
| 4/4 가정 줄: `bar_map.py` `:55`, `:134`, `:445`, `:452–457`, `:462`, `:468`; `bar_map_entry.py` `:50–55`, `:88–89`, `:171`; `session.py` `:9546`, `:9547–9553` | 모두 맞음 [measured: 부록 A-1, A-2, A-5] | 맞음. 이 목록이 전부가 아님도 맞음 → §2 |
| 곡은 10곡: SPEC-001 `progress.md:682`, `research.md:120–135` | 두 위치는 「10곡」이라는 개수를 말하는 문장이다(`progress.md:682`는 상수 서술 안의 한 구절, `research.md:120`·`:124`는 본문). **곡 이름은 두 파일에 없고** `.moai/reports/t547/after_songs.txt` 10행에 있다 [measured: 부록 A-12] | 개수는 맞음. 곡 목록의 출처만 다름 → §3 |
| 「11곡」 | 저장소에서 찾지 못했다 | **미검증** → §3 |
| tier 상한 M 16/16, L 25/25 | `spec-workflow.md` § SPEC Complexity Tier 표 [carried] | 맞음 |
| SPEC-002 REQ 16개·AC 16개 | [measured: 부록 A-14] 16, 16 | 맞음 |

**ID·접두사 점검.** `SPEC-LDBARMAP-005` 정규식 `^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$` → `PASS` [measured: 부록 A-13]. `LDBARMETER`는 현재 트리, `origin/main`, 전체 git 이력에서 0건 [measured: 부록 A-13]. 형제 워크트리에는 SPEC-LDBARMAP-003(`../t648`)과 004(`../WT-barmap-song-match`)가 있고 005는 어디에도 없다 [measured: 부록 A-13].

**선행 SPEC.** SPEC-LDBARMAP-001 `status: completed`, SPEC-LDBARMAP-002 `status: completed` — `depends_on`이 충족된다. SPEC-LDARRANGE-001(`draft`)과 SPEC-LDBEAT-001(`completed`)은 존재한다 [measured: 부록 A-14]. 네 SPEC 모두 `phase: "Lighting Copilot v1.2 target"` — 이 SPEC도 같은 값을 쓴다(릴리스 목표 라벨이고 생애주기 단계 이름이 아니다).

## §2. 4/4 가정 전수 점검

리드의 목록(grep 한 번의 결과)은 시작점이었다. 아래는 이 plan-phase가 마디 지도 경로의 모든 파일을 읽어 완성한 표다. 「범위」 열: **안** = 이 SPEC이 바꾼다, **밖** = 바꾸지 않는다(이유 병기), **불변** = 이미 박자표에 일반적이라 바꿀 것이 없다.

| # | 위치 | 4/4 가정 | 범위 | 처리 |
|---|---|---|---|---|
| 1 | `bar_map.py:54-55` | 상수 `_BEATS_PER_BAR = 4` | 안 | 제거. 분자를 인자로 받는다 (REQ-009) |
| 2 | `bar_map.py:134-136` | `BarMap` docstring이 「4/4박자 LOVE ATTACK」을 가정 | 안 | docstring 갱신 |
| 3 | `bar_map.py:445` | `derive_bars` docstring의 `% 4` | 안 | docstring 갱신 (AC-010의 정적 점검 대상) |
| 4 | `bar_map.py:452-457` | 오프셋 범위 `0 ≤ o < 4`와 거절 | 안 | 분자를 따른다 (REQ-012). 오프셋 ≥ N의 처리는 OD-4 |
| 5 | `bar_map.py:461-463` | 다운비트 `(i − o) % _BEATS_PER_BAR == 0` | 안 | 분자 N으로 (REQ-009) |
| 6 | `bar_map.py:464` | 못갖춘마디 `min(o, len)` | 불변 | 분자에 무관하다 |
| 7 | `bar_map.py:468` | 주석 「4/4박자 — 다운비트와 동일」 | 안 | 주석 갱신. 다운비트 = 마디 경계는 모든 박자에서 참이다 |
| 8 | `bar_map.py:221-270` `detect_beat_grid` | 칸 세기를 돌려주지 않는다 | 안 | `BeatGridResult`에 필드 하나 (판별 입력). 기존 판정은 불변 |
| 9 | `bar_map.py:311-438` 두 배/절반 검사 | 인접 칸 쌍과 홀짝 쌍을 본다. 4를 쓰지 않는다 [measured: 부록 A-3 — 단독 숫자 4가 있는 비주석 줄은 `:17`(마일스톤 `M4` 언급), `:55`, `:134`, `:445`, `:468`이고 박자와 관계된 것은 위 1·2·3·7번뿐이다] | 불변 | 박자 판별이 읽기만 한다 (REQ-004) |
| 10 | `bar_map.py:601-708` `extract_bar_features` | 창이 마디 경계 목록으로 정해진다 — 박 수를 쓰지 않는다 | 불변 | 3/4·6/8 마디도 같은 코드로 잰다 |
| 11 | `bar_map.py:494-553, 711-755` `classify_bar_events` | 문턱이 곡 중앙값 대비 **비율**이고 `_BUILD_MIN_BARS = 3`은 마디 수다. 박 수를 쓰지 않으나 비율은 LOVE ATTACK(4/4)으로 맞췄다 | 밖 | 코드는 박자에 무관하다. 3/4·6/8 마디에서의 품질은 미상 → Gaps, OQ-12 |
| 12 | `bar_map_entry.py:50-55` | `_TIME_SIGNATURE = (4, 4)`, `_BEATS_PER_BAR` | 안 | 표기 분모 이름표로 바꾸고 분자는 판별 결과에서 받는다 (REQ-010) |
| 13 | `bar_map_entry.py:79-90` | `first_beat_offset_problem`이 `0 ≤ o < 4`를 디코드 전에 점검 | 안 | 2단: 디코드 전(형식 + 상한 5), 분자 확정 뒤(정확한 범위) (REQ-012) |
| 14 | `bar_map_entry.py:142-152` | 두 배 BPM 채택은 거절 | 밖 | 그대로. BPM 배수 거절이고 박자 거절이 아니다 (OQ-5) |
| 15 | `bar_map_entry.py:154-173` | `derive_bars(…, o)` 호출과 `time_signature=_TIME_SIGNATURE` | 안 | 판별 결과를 넘긴다 |
| 16 | `bar_map_store.py:105` | `build_bar_map_payload`의 기본 인자 `time_signature=(4, 4)` | 불변 | 기본값일 뿐이다. 시험 밖의 호출처는 `bar_map_entry.py:167` 하나이고 박자표를 명시해 넘긴다 [measured: 부록 A-2b]. 후속 정리 후보 |
| 17 | `bar_map_store.py:203-215, 258-267` | 분자 1~16, 분모 {1, 2, 4, 8, 16}, 오프셋 0 ~ 분자−1, 마지막 마디 부분 채움 | 불변 | 이미 일반적이다. 3, 4, 6과 분모 4, 8이 모두 허용 범위다 |
| 18 | `session.py:9546-9553` | 합성 호출과 실패 종류별 처리 | 안 | 판별 결과를 받아 응답에 반영 (REQ-017) |
| 19 | `session.py:9457-9466` | 성공 응답을 저장 관문이 만든다 | 안 | 선택 인자로 문구 한 줄을 받는다 (OD-3 기본안) |
| 20 | `messages.py:766-779`, `app.py:841-` | 파서는 범위를 재지 않는다. 디스패치는 오프셋만 넘긴다 | 불변 | 프레임 모양 불변 (REQ-016). 주석 `:771`의 「0~3」만 낡는다 |
| 21 | `server/web/PROTOCOL.md:26` | 응답 설명이 이미 「0..beats-per-bar−1」로 일반적이다 | 안(한 줄) | 응답 본문의 「박자 추정」을 한 줄 더한다 |
| 22 | `server/design/beat_grid_emit.py:216`, `beat_grid_send.py:248-283`, `beat_grid_edit.py:326-350`, `cue_density.py:139-160` | 소비자: `beats_per_bar`를 분자에서 읽고 분모는 읽지 않는다. 3/4 시험이 있다 [measured: 부록 A-6, A-16] | 불변 | 소비자는 이미 일반적이다 (§4) |
| 23 | `server/audio/analyze.py:52-64, 526-528` | `bar_ms = 4.0 × 60000 / bpm`, `_MIN_SEGMENT_BARS = 4.0` — **구간 경계 하한**의 4칸 가정 | 밖 | 마디 지도 경로가 아니라 `analyze()`의 구간(섹션) 경계 경로다 [measured: 부록 A-4]. BPM 확정 계약과 같은 곳이라 건드리지 않는다. OQ-11 |
| 24 | 시험 4개 | 오프셋 4·5·99 거절, `0~3` 사유, `time_signature == [4, 4]` [measured: 부록 A-8] | 안 | 새 계약에 맞춰 고친다 (plan.md §C) |
| 25 | 시험 다수 | `SongTiming(…beats_per_bar=4…)`와 `_bar_map(beats_per_bar=4)` 등 소비자 쪽 고정물 [measured: 부록 A-7] | 불변 | 소비자 시험의 입력값이지 분석기 가정이 아니다 |
| 26 | `server/design/profile.py:299`, `server/design/sugar_timeline.py:473` | `MusicProfile.meter` 기본값 `"4/4"`, 견본 타임라인이 `"time_signature": "4/4"` 문자열을 고정 기록 [measured: 부록 A-12f] | 밖 | 분석기 경로가 아니다. 단, 소비자가 이 문자열을 `bar_map`보다 **먼저** 읽는다(§4, OQ-6) |

**전수 점검의 한계.** 점검은 `server/`와 `tools/`의 `.py`, `ui/src`, `server/web/PROTOCOL.md`의 이름 검색과 마디 지도 파일 네 개의 정독이다. 이름이 다른 4 가정(예: 곡 계획의 박자표 문자열을 다루는 코드)은 찾은 만큼만 적었다. `ui/src`에는 `bar_map_analyse`가 0건이다 [measured: 부록 A-9].

## §3. 곡 목록, 박자표 라벨, 「11곡」

**기록된 곡은 10곡이다.** `.moai/reports/t547/after_songs.txt`의 곡 행 10개 [measured: 부록 A-12]:

| # | 곡 | 칸 BPM(회귀) | 두 배 판정 |
|---|---|---|---|
| 1 | LOVE ATTACK.mp3 | 112.002 | keep |
| 2 | Club Diver.mp3 | 140.026 | keep |
| 3 | Cut and Run.mp3 | 107.666 | keep |
| 4 | Ice cream.mp3 | 100.446 | keep |
| 5 | Let's Dance.mp3 | 120.030 | keep |
| 6 | LoveMe.mp3 | 99.994 | keep |
| 7 | Morning.mp3 | 117.454 | keep |
| 8 | Rain.mp3 | 76.013 | keep |
| 9 | Too Cool.mp3 | 160.003 | keep |
| 10 | scott-buckley-neon.mp3 | 120.185 | keep |

(값은 [carried: `.moai/reports/t547/after_songs.txt`]. 카드 t547 시점의 기록이며 현재 코드에서 다시 재지 않았다.) LOVE ATTACK은 샘플 폴더 밖 경로에 있다 [carried: `.moai/reports/t547/probe_songs.py:33`]. 이 plan-phase는 그 파일이 지금 있는지 확인하지 않았다.

**「11곡」은 저장소에서 찾지 못했다.** `.moai/specs`, `.moai/reports`, `tools`, `server`에서 곡 11개를 가리키는 기록이 없다. 다만 하나의 관찰이 있다 — 로컬 샘플 폴더(`src/sample music`, 저장소에 추적되지 않는다)에 파일이 **10개** 있다: 기록된 mp3 9개와 기록에 없는 wav 1개(`걸그룹DinoDino_C_max최고품질.wav`) [measured: 부록 A-12b, A-12c — 추적 파일 0개]. LOVE ATTACK(폴더 밖)을 더하면 로컬 오디오가 11개일 수 있다. 이것이 리드가 말한 「11」의 출처라는 것은 **추정**이다. 확인하지 못했다. D-4에 따라 기준선은 기록된 10곡이다.

**사람이 확인한 박자표 라벨은 없다.** 곡 이름과 박자표 단어를 함께 가진 `.moai/reports`의 줄을 세면 파일 몇 개가 나온다 [measured: 부록 A-12d]. 내용을 열어 보니 그것들은 두 종류다 — (1) 카드 t539·t541의 SPEC 감사 문서(LOVE ATTACK을 4/4 예시로 든 서술), (2) 카드 t476·t498·t499·t501 실행 산출물 `events.json`의 `"time_signature": "4/4"` 줄. (2)가 곡 이름 폴더를 가진 것은 Rain, Morning, Club Diver, Too Cool, Cut and Run, Ice cream, scott-buckley-neon — 기록된 10곡 가운데 7곡이다. **이 줄이 사람이 박자를 확인했다는 증거는 아니다.** 같은 문자열이 코드에 기본값 또는 고정 리터럴로 있기 때문이다(`MusicProfile.meter = "4/4"` — `profile.py:299`, 견본 타임라인 — `sugar_timeline.py:473`) [measured: 부록 A-12]. 어느 쪽이 `events.json`을 만들었는지는 추적하지 않았다. 그래서 「이 10곡은 4/4다」라고 말할 근거가 저장소에 없다.

D-4가 「기록된 곡 가운데 4/4가 아닌 곡을 발견하면 멈추고 보고하라」고 했는데, 이 plan-phase는 **그런 곡을 발견하지 못했다** — 이는 「4/4임을 확인했다」가 아니라 「아닌 증거를 찾지 못했다」일 뿐이다. 이 점이 spec.md Gaps 4다. 회귀 기준을 「참 박자」가 아니라 「현행 분석 결과와 같은 마디 경계」로 둔 이유가 이것이다(REQ-LDBARMETER-019).

**3/4·6/8 실제 곡 오디오.** 저장소 안에서 박자표가 라벨된 곡을 찾지 못했다 [measured: 부록 A-12d, A-12e — 왈츠·복합박 단어를 가진 파일 0개]. 리드의 「그런 곡이 있다」는 진술은 이 트리에서 확인되지 않는다 → 실제 곡 정확도 주장 금지(P5, REQ-LDBARMETER-015).

## §4. 소비자와 우선순위

- 소비자는 마디 시작을 `1마디 + (N−1) × 분자 × 60 / bpm`으로 계산한다 [carried: `beat_grid_emit.py:216`]. 분자는 `time_signature[0]`이고 분모는 읽지 않는다 [carried: `beat_grid_send.py:248-255`]. 3/4 시험이 있다 [measured: 부록 A-16]. → 저장 값의 뜻을 「`bpm` = 칸 빈도, 분자 = 마디당 칸」으로 둔다(REQ-002).
- 마디당 박 수를 읽는 다른 길: `beats_per_bar_from_timeline`은 **곡 계획의 `timeline["time_signature"]` 문자열을 먼저** 보고, 없으면 `bar_map.time_signature[0]`을 본다 [carried: `server/design/beat_grid_edit.py:326-350`]. 곡 계획이 「4/4」라고 선언한 타임라인에 판별이 3/4를 저장하면 두 길이 서로 다른 값을 쓴다 — 에미터(`build_song_timing_from_bar_map`)는 `bar_map`의 분자를 쓰고, 편집 검증(`beats_per_bar_from_timeline`)은 문자열을 먼저 본다. 견본 타임라인은 이 문자열을 `"4/4"`로 고정 기록한다(`sugar_timeline.py:473` [measured: 부록 A-12f]). 어느 쪽이 이겨야 하는지는 이 SPEC이 정하지 않는다 → OQ-6.

## §5. 형제 SPEC과의 겹침

두 SPEC은 이 트리와 `origin/main`에 없고 다른 워크트리에서만 읽었다. 둘 다 `status: draft`다.

| SPEC | 위치 | 이 SPEC과 닿는 곳 |
|---|---|---|
| SPEC-LDBARMAP-003 (진입 화면 UI) | `../t648` | 화면이 `bar_map_analyse`를 부른다. 이 SPEC은 프레임을 바꾸지 않는다. AC-014 (3)의 화면 점검은 이 SPEC이 병합된 트리에서 의미가 생긴다 |
| SPEC-LDBARMAP-004 (저장: 곡 길이 확인과 원본 기록, 서버) | `../WT-barmap-song-match` | 모듈 목록에 `server/audio/bar_map.py`, `bar_map_entry.py`, `bar_map_store.py`, `server/web/session.py`가 있어 이 SPEC의 변경 파일과 겹친다. 그 SPEC의 REQ-LDBARLEN-002는 「원본 기록이 마디 지도 사전 안에 들어가지 않고, 최상위 키 집합(여섯 개)과 `validate_bar_map`이 바뀌지 않는다」이다. 저장 성공 때 타임라인의 다른 키가 바뀌면 REQ-LDBARENTRY-010 개정이 필요하다고 적었고, 자기 기록의 자리를 기존 키 `total_duration_ms`로 확정했다 [carried: 부록 A-15의 출력 줄 94, 188-198, 123, 223] |

**이 형제 파일은 움직인다.** 이 plan-phase가 같은 파일을 두 번 읽었는데 첫 번째에는 자리(OD-1)가 열려 있었고(줄 63, 91, 116 부근) 두 번째에는 확정되어 있었다(줄 123). 위 인용은 부록 A-15를 실행한 시점의 것이며 지금 파일과 다를 수 있다.

결론: 「박자 추정」 표지의 저장 자리(OD-3)는 004의 기록 자리 결정과 같은 종류의 질문이다 — 둘 다 `bar_map` 밖의 어딘가에 값을 얹으려 하고 REQ-LDBARENTRY-010의 「그 밖의 키는 바이트까지 같다」와 부딪힌다. 병합 순서와 충돌은 이 plan-phase가 점검하지 못했다(spec.md Gaps 11, OQ-10).

## §6. 가정 — 이 SPEC이 깔고 있는 것

침묵한 채 고르지 않으려고 적는다. 각 항목은 감독 또는 plan-auditor가 뒤집을 수 있다.

| # | 가정 | 어디서 | 뒤집히면 |
|---|---|---|---|
| A-1 | 후보는 {3, 4, 6}이고 2/4는 후보가 아니다 | design.md §3.2 | PR-01, 픽스처, AC-001~003 |
| A-2 | 이 SPEC의 6/8 주장은 추적기가 8분음표 펄스를 잡은 경우에 한정한다 | design.md §3.3 | OQ-3의 하위 박 판정이 범위에 들어온다 |
| A-3 | 칸 세기는 기존 온셋 강도 환경이고 합성 강세는 진폭으로 넣는다 | design.md §4.1, §7.2 | 신호를 바꾸면 PR-02와 M1 전체 |
| A-4 | 사전 등록 문턱(시드 30, 27/30, 29/30, 1/30, MIN_PAIRS 12, α/2)은 설계자의 제안이다 | design.md §6.1 | OQ-9 |
| A-5 | 두 배 BPM 검사의 `ambiguous`는 박자 판별을 추정으로 만든다 | design.md §5 U-1 | OQ-2 |
| A-6 | 부분 정보가 있어도 불확실하면 4/4다(P3 문면) | design.md §5 U-6 | OQ-1 |
| A-7 | 「박자 추정」은 응답 본문에 싣고 요약 라벨은 늘리지 않는다 | design.md §9.1 | 요약 라벨을 쓰면 화면 SPEC의 라벨 목록이 흔들린다 [carried: 부록 A-15의 004 `spec.md:96` 언급] |
| A-8 | OD-3 기본안은 저장하지 않는다 | design.md §9.2 | 선택지 2로 바꾸면 spec.md §3.3 |
| A-9 | 회귀 기준선은 M1의 첫 단계, 변경 전 코드로 찍는다 | design.md §11.2 | M2 뒤에 찍으면 순환 비교 |
| A-10 | 칸 시각 목록 하나가 오프셋 0~3의 마디 경계를 모두 정한다 | design.md §11.4 | `derive_bars`가 칸 목록과 오프셋만 쓴다는 읽기에 의존한다 [carried: `bar_map.py:461-464`] |
| A-11 | Tier L은 REQ 개수(상한 초과) 때문이고 파일·줄 수 때문이 아니다 | spec.md §0 | — |
| A-12 | 사전 등록 문턱과 규모 추정을 `[predicted]`로 표기한다 — 리드의 세 표기 안에서 | 모든 문서 | 네 번째 표기를 쓰자는 요구가 있으면 일괄 변경 |
| A-13 | 동결 점검의 기준 커밋은 `bef3e16d`다(plan 커밋이 병합되면 plan 커밋의 부모로 바꾼다) | acceptance.md AC-021 | — |
| A-14 | 줄 번호는 `bef3e16d` 기준이고 다른 세션이 같은 파일을 고치면 움직인다 | 모든 문서 | 병합 전 줄 번호 재확인 |

## §7. 확인하지 못한 것

spec.md §7이 Gaps의 정본이다. 이 조사에서만 해당하는 것을 덧붙인다.

1. 시험을 돌리지 않았다. 부록의 줄 번호는 읽은 것이다.
2. 다른 워크트리 49개 중 `.moai/specs/SPEC-LDBARMAP-*`를 가진 곳만 훑었다. 그 안의 미커밋 변경은 보지 않았다.
3. `src/sample music`의 오디오 파일은 열지 않았다. 목록만 보았다.
4. `LOVE ATTACK.mp3`가 로컬에 있는지 확인하지 않았다(폴더 밖 절대 경로라 이 plan-phase가 읽지 않았다).
5. `moai spec lint`의 결과는 progress.md §E.1에 적는다.

## 부록 A. 명령과 출력 원문

트리 `bef3e16d`(브랜치 `WT-barmap-meter`)에서 워크트리 루트 기준으로 실행했다. 각 블록은 `$ <명령>`, 그 출력 원문, 마지막 줄의 종료 코드다. 이 부록은 명령을 실행해 파일에 기록했다 — 출력을 손으로 옮기지 않았다. 파이프라인의 종료 코드는 마지막 명령의 것이다. 긴 SPEC 본문 줄은 `grep -o`의 앞뒤 16자 창으로 잘랐다(창 안의 글자는 원문 그대로이고, 창은 글자 단위라 단어 중간에서 끊긴다). 괄호로 시작하는 한 줄 설명(예: 「위 명령은 일치가 없어 출력 없음」)은 작성자 주석이지 명령의 출력이 아니다. 버전 관리 명령이 든 블록(A-12c, A-13의 `git` 줄, A-17b)은 한 줄씩 따로 실행해 덧붙였으므로 종료 코드를 캡처하지 않았다. 실행 환경이 `grep`을 `ugrep`으로 대신하고 있어 앞뒤 30자 창은 복잡도 한계로 실패했다 — 처음 시도한 그 실패는 지우고 16자 창으로 다시 실행했다(A-10, A-11).

### A-1 — bar_map.py의 4/4 가정 줄

```text
$ grep -n -E "_BEATS_PER_BAR|% 4|4/4|4박|four beats|beats_per_bar|time_signature|\[4, 4\]|\(4, 4\)" server/audio/bar_map.py
54:#: 한 마디(4/4박자)의 박 수. REQ-LDBARMAP-016 — 오프셋은 이 값의 나머지다.
55:_BEATS_PER_BAR = 4
134:    ``downbeats_ms`` 와 ``bar_boundaries_ms`` 는 이 SPEC(4/4박자 LOVE ATTACK)에서는
445:    인덱스 ``i`` 가 ``(i - first_beat_offset) % 4 == 0`` 인 자리다. 첫 다운비트
454:    if not (0 <= first_beat_offset < _BEATS_PER_BAR):
456:            f"첫 박 오프셋은 0~{_BEATS_PER_BAR - 1} 범위여야 합니다: {first_beat_offset}"
462:        t for i, t in enumerate(beat_times_ms) if (i - first_beat_offset) % _BEATS_PER_BAR == 0
468:        bar_boundaries_ms=downbeats,  # 4/4박자 — 다운비트와 동일(spec.md §5 열린 결정 3)
[exit 0]
```

### A-2 — bar_map_entry.py·bar_map_store.py의 4/4 가정 줄

```text
$ grep -n -E "_BEATS_PER_BAR|% 4|4/4|4박|beats_per_bar|time_signature|_TIME_SIGNATURE|\[4, 4\]|\(4, 4\)" server/audio/bar_map_entry.py server/audio/bar_map_store.py
server/audio/bar_map_entry.py:50:#: 합성이 다루는 박자표 — 분석기(``derive_bars``)가 4/4 전용이다(REQ-LDBARENTRY-015,
server/audio/bar_map_entry.py:52:_TIME_SIGNATURE = (4, 4)
server/audio/bar_map_entry.py:55:_BEATS_PER_BAR = _TIME_SIGNATURE[0]
server/audio/bar_map_entry.py:88:    if not (0 <= first_beat_offset < _BEATS_PER_BAR):
server/audio/bar_map_entry.py:89:        return f"첫 박 오프셋은 0~{_BEATS_PER_BAR - 1} 범위여야 합니다: {first_beat_offset}"
server/audio/bar_map_entry.py:171:            time_signature=_TIME_SIGNATURE,
server/audio/bar_map_store.py:15:LOVE ATTACK 고유값(82마디·112.35 BPM·4/4 전용)을 가정하지 않는다. 임의의
server/audio/bar_map_store.py:55:    {"schema_version", "bpm", "time_signature", "first_beat_offset", "bars", "events"}
server/audio/bar_map_store.py:105:    time_signature: tuple[int, int] = (4, 4),
server/audio/bar_map_store.py:111:    ATTACK 4/4 전용이 아니다, spec.md §5 열린 결정 0 일반화 규칙) —
server/audio/bar_map_store.py:118:    numerator, denominator = time_signature
server/audio/bar_map_store.py:148:        "time_signature": [int(numerator), int(denominator)],
server/audio/bar_map_store.py:195:    time_signature = payload["time_signature"]
server/audio/bar_map_store.py:197:        not isinstance(time_signature, Sequence)
server/audio/bar_map_store.py:198:        or isinstance(time_signature, str | bytes)
server/audio/bar_map_store.py:199:        or len(time_signature) != 2
server/audio/bar_map_store.py:201:        return f"time_signature 는 [분자, 분모] 2개짜리여야 합니다: {time_signature!r}"
server/audio/bar_map_store.py:202:    numerator, denominator = time_signature
server/audio/bar_map_store.py:204:        return f"time_signature 분자는 1~16 사이 정수여야 합니다: {numerator!r}"
server/audio/bar_map_store.py:207:            "time_signature 분모는 "
[exit 0]
```

### A-2b — build_bar_map_payload 호출처(시험 제외)

```text
$ grep -rn "build_bar_map_payload(" server tools --include="*.py" | grep -v "^server/tests"
server/audio/bar_map_entry.py:167:        return build_bar_map_payload(
server/audio/bar_map_store.py:100:def build_bar_map_payload(
[exit 0]
```

### A-3 — bar_map.py에서 단독 숫자 4가 있는 비주석 줄

```text
$ grep -n -E "(^|[^0-9.])4([^0-9.]|$)" server/audio/bar_map.py | grep -v -E "^[0-9]+:[[:space:]]*#"
17:(REQ-LDBARMAP-010, 저장 인터페이스 배선은 M4의 몫).
55:_BEATS_PER_BAR = 4
134:    ``downbeats_ms`` 와 ``bar_boundaries_ms`` 는 이 SPEC(4/4박자 LOVE ATTACK)에서는
445:    인덱스 ``i`` 가 ``(i - first_beat_offset) % 4 == 0`` 인 자리다. 첫 다운비트
468:        bar_boundaries_ms=downbeats,  # 4/4박자 — 다운비트와 동일(spec.md §5 열린 결정 3)
[exit 0]
```

### A-4 — analyze.py의 4칸 마디 가정(구간 경계 하한)

```text
$ grep -n -E "bar_ms|_MIN_SEGMENT_BARS|4\.0 \*" server/audio/analyze.py
48:#: 4마디 미만 38/38.** BPM 을 알면 :data:`_MIN_SEGMENT_BARS` 가 하한을 정한다.
64:_MIN_SEGMENT_BARS = 4.0
505:    BPM 을 알면 :data:`_MIN_SEGMENT_BARS` 마디, 모르면 :data:`_MIN_SEGMENT_SECONDS` 초다.
526:    bar_ms = 4.0 * 60_000.0 / bpm
527:    bars_floor = _MIN_SEGMENT_BARS * bar_ms
[exit 0]
```

### A-5 — session.py의 마디 지도 진입·저장 자리

```text
$ grep -n -E "bar_map|synthesize_bar_map|first_beat_offset" server/web/session.py
41:from server.audio.bar_map_entry import (
44:    first_beat_offset_problem,
45:    synthesize_bar_map,
47:from server.audio.bar_map_store import attach_bar_map, read_bar_map, validate_bar_map
126:    build_song_timing_from_bar_map,
9419:    # -- t539 M4 — 마디 지도 저장 (timeline["bar_map"], 콘솔 무접촉) -------------
9421:    def store_timeline_bar_map(self, payload: dict) -> dict:
9422:        """마디 지도를 초안 타임라인의 ``bar_map`` 키에 쓴다(REQ-LDBARMAP-010,
9426:        잘못된 페이로드는 검증 단계에서 거절되고(``validate_bar_map``), 타임라인과
9440:        reason = validate_bar_map(payload)
9451:        updated = attach_bar_map(timeline, payload)
9469:    def timeline_bar_map(self) -> dict | None:
9476:        return read_bar_map(timeline)
9478:    def analyse_bar_map(self, first_beat_offset: int) -> None:
9479:        """첨부된 곡 오디오로 마디 지도를 만들어 초안 타임라인의 ``bar_map`` 키에 저장한다
9484:        곡 열쇠 기억 → base64 풀기 → 합성(``synthesize_bar_map`` — 같은 점검을 거기서도 한다) →
9485:        곡 열쇠 재확인 → 저장 관문(``store_timeline_bar_map``).
9531:        problem = first_beat_offset_problem(first_beat_offset)
9546:        result = synthesize_bar_map(audio_bytes, first_beat_offset)
9569:        event = self.store_timeline_bar_map(result)
9570:        if self.timeline_bar_map() == result:
10645:            timing = build_song_timing_from_bar_map(timeline.get("bar_map"))
11626:            timing = build_song_timing_from_bar_map(timeline.get("bar_map"))
[exit 0]
```

### A-6 — beats_per_bar를 쓰는 비시험 코드(소비자)

```text
$ grep -rn -E "beats_per_bar|BEATS_PER_BAR" server tools --include="*.py" | grep -v "^server/tests/"
server/design/beat_grid_emit.py:202:    beats_per_bar: int
server/design/beat_grid_emit.py:208:        bar_valid = self.beats_per_bar is not None and self.beats_per_bar > 0
server/design/beat_grid_emit.py:216:        return self.downbeat_bar1_seconds + (bar - 1) * self.beats_per_bar * seconds_per_beat
server/design/beat_grid_emit.py:300:            beats_per_bar=timing.beats_per_bar,
server/design/beat_grid_emit.py:406:        fade_seconds = float(fade_bars) * timing.beats_per_bar * seconds_per_beat
server/design/beat_grid_emit.py:416:            or not 1 <= trigger_beat <= timing.beats_per_bar
server/design/beat_grid_emit.py:420:                    f"trigger_beat {trigger_beat!r} 는 1~{timing.beats_per_bar} 박이어야 "
server/design/beat_grid_emit.py:593:        or timing.beats_per_bar is None
server/design/beat_grid_emit.py:594:        or timing.beats_per_bar <= 0
server/design/beat_grid_emit.py:598:            blocked_reason="곡 타이밍(bpm/beats_per_bar/기준 초)이 없어 전체 배치를 거절합니다",
server/design/app_movement.py:80:    beats_per_bar: int | None,
server/design/app_movement.py:124:        if beats_per_bar is None or beats_per_bar <= 0:
server/design/app_movement.py:125:            return (), "beats_per_bar가 없어 마디 단위 주기를 박으로 환산할 수 없습니다"
server/design/app_movement.py:126:        beats_per_cycle = period_value * beats_per_bar
server/design/beat_grid_effect_presets.py:300:    beats_per_bar: int | None,
server/design/beat_grid_effect_presets.py:310:        if beats_per_bar is None or beats_per_bar <= 0:
server/design/beat_grid_effect_presets.py:312:        beats_per_cycle *= beats_per_bar
server/design/beat_grid_effect_presets.py:331:    beats_per_bar: int | None,
server/design/beat_grid_effect_presets.py:345:            grid, number, library=library, policy=policy, bpm=bpm, beats_per_bar=beats_per_bar
server/design/beat_grid_send.py:255:    beats_per_bar = time_signature[0]
server/design/beat_grid_send.py:256:    if not isinstance(beats_per_bar, int) or isinstance(beats_per_bar, bool) or beats_per_bar <= 0:
server/design/beat_grid_send.py:283:        beats_per_bar=int(beats_per_bar),
server/design/cue_density.py:139:def beats_per_bar(meter: object) -> int | None:
server/design/cue_density.py:157:    beats = beats_per_bar(meter)
server/design/beat_grid_edit.py:326:def beats_per_bar_from_timeline(timeline: object) -> int | None:
server/design/beat_grid_edit.py:359:def _validate_entry(value: object, beats_per_bar: int | None = None) -> None:
server/design/beat_grid_edit.py:390:        if beats_per_bar is None:
server/design/beat_grid_edit.py:395:        if not 1 <= trigger_beat <= beats_per_bar:
server/design/beat_grid_edit.py:397:                f"트리거 박은 1~{beats_per_bar} 사이여야 합니다(이 곡 박자표 기준, "
server/design/beat_grid_edit.py:462:    beats_per_bar: int | None = None,
server/design/beat_grid_edit.py:512:        _validate_entry(changes["entry"], beats_per_bar)
server/design/beat_grid_edit.py:689:    beats_per_bar: int | None = None,
server/design/beat_grid_edit.py:727:            current, bar=bar, target=target, changes=changes, beats_per_bar=beats_per_bar
server/web/session.py:79:    beats_per_bar_from_timeline,
server/web/session.py:1468:def _song_beats_per_bar(meter: object) -> int | None:
server/web/session.py:1485:    beats = _song_beats_per_bar(profile.meter)
server/web/session.py:9808:        beats_per_bar = beats_per_bar_from_timeline(timeline)
server/web/session.py:9817:                    beats_per_bar=beats_per_bar,
server/web/session.py:9821:                    grid, bar=bar, target=target, changes=changes, beats_per_bar=beats_per_bar
server/web/session.py:10136:        beats_per_bar = beats_per_bar_from_timeline(timeline)
server/web/session.py:10139:                grid, bar=bar, target=target, changes=changes, beats_per_bar=beats_per_bar
server/web/session.py:10231:        beats_per_bar = beats_per_bar_from_timeline(timeline)
server/web/session.py:10234:                grid, bar=bar, target=target, changes=changes, beats_per_bar=beats_per_bar
server/web/session.py:10313:        beats_per_bar = beats_per_bar_from_timeline(timeline)
server/web/session.py:10316:                grid, bar=bar, target=target, changes=changes, beats_per_bar=beats_per_bar
server/web/session.py:11633:                beats_per_bar=timing.beats_per_bar if timing is not None else None,
server/audio/bar_map.py:55:_BEATS_PER_BAR = 4
server/audio/bar_map.py:454:    if not (0 <= first_beat_offset < _BEATS_PER_BAR):
server/audio/bar_map.py:456:            f"첫 박 오프셋은 0~{_BEATS_PER_BAR - 1} 범위여야 합니다: {first_beat_offset}"
server/audio/bar_map.py:462:        t for i, t in enumerate(beat_times_ms) if (i - first_beat_offset) % _BEATS_PER_BAR == 0
server/audio/bar_map_entry.py:55:_BEATS_PER_BAR = _TIME_SIGNATURE[0]
server/audio/bar_map_entry.py:88:    if not (0 <= first_beat_offset < _BEATS_PER_BAR):
server/audio/bar_map_entry.py:89:        return f"첫 박 오프셋은 0~{_BEATS_PER_BAR - 1} 범위여야 합니다: {first_beat_offset}"
[exit 0]
```

### A-7 — beats_per_bar를 세는 시험 파일별 줄 수

```text
$ grep -rc -E "beats_per_bar|BEATS_PER_BAR" server/tests --include="*.py" | grep -v ":0$"
server/tests/test_app_movement_t548.py:18
server/tests/test_beat_grid_reapply_cue2_t616.py:1
server/tests/test_beat_grid_entry_t574.py:12
server/tests/test_beat_grid_empty_track_t615.py:1
server/tests/test_session_bar_map_entry.py:1
server/tests/test_beat_grid_send_t563.py:3
server/tests/test_new_preset_dialog_t589.py:2
server/tests/test_beat_grid_store_order_t612.py:1
server/tests/test_beat_grid_emit_t549.py:2
server/tests/test_effect_preset_create_t593.py:5
server/tests/test_beat_grid_dimmer_per_group_t573.py:2
server/tests/test_cue_density.py:2
server/tests/test_apply_time_approval_t577.py:2
server/tests/test_approved_empty_hold_t600.py:1
server/tests/test_beat_grid_reapply_t572.py:2
server/tests/test_beat_grid_emit_entry_t576.py:1
[exit 0]
```

### A-8 — 4/4 계약을 단언하는 기존 시험 줄

```text
$ grep -n -E "0~3|\[4, 4\]|\(4, 4\)|offset_out_of_range|offset = 4|\[-1, 4|\[-1, 0, 1, 2, 3, 4\]|\[0, 1, 2, 3, -1, 4\]|beats_per_bar == 4" server/tests/test_audio_bar_map.py server/tests/test_audio_bar_map_entry.py server/tests/test_session_bar_map_entry.py server/tests/test_web_bar_map_entry.py server/tests/test_messages_bar_map_entry.py
server/tests/test_web_bar_map_entry.py:340:@pytest.mark.parametrize("offset", [-1, 0, 1, 2, 3, 4])
server/tests/test_audio_bar_map_entry.py:240:@pytest.mark.parametrize("bad_offset", [-1, 4, 99])
server/tests/test_audio_bar_map_entry.py:245:    assert "0~3" in result.reason
server/tests/test_audio_bar_map_entry.py:266:@pytest.mark.parametrize("bad_offset", [-1, 4, 99])
server/tests/test_audio_bar_map_entry.py:270:    assert "0~3" in problem
server/tests/test_audio_bar_map_entry.py:338:    assert result["time_signature"] == [4, 4]
server/tests/test_audio_bar_map_entry.py:527:            grid.beat_times_ms, 0, bpm=grid.bpm, time_signature=(4, 4), events=bad_events
server/tests/test_audio_bar_map.py:125:@pytest.mark.parametrize("bad_offset", [-1, 4, 5, 100, -100])
server/tests/test_audio_bar_map.py:129:    assert "0~3" in result.reason
server/tests/test_session_bar_map_entry.py:335:    return build_bar_map_payload(beats, 0, bpm=120.0, time_signature=(4, 4))
server/tests/test_session_bar_map_entry.py:343:@pytest.mark.parametrize("bad_offset", [-1, 4, 99])
server/tests/test_session_bar_map_entry.py:354:    _assert_rejected_and_untouched(h, before, reason="0~3")
server/tests/test_session_bar_map_entry.py:385:    response = _assert_rejected_and_untouched(h, before, reason="0~3")
server/tests/test_session_bar_map_entry.py:403:    assert "0~3" not in response["text"], response["text"]
server/tests/test_session_bar_map_entry.py:698:    assert timing.beats_per_bar == 4  # (3)
server/tests/test_session_bar_map_entry.py:792:    elif name == "offset_out_of_range":
server/tests/test_session_bar_map_entry.py:793:        offset = 4
server/tests/test_session_bar_map_entry.py:824:        "offset_out_of_range",
server/tests/test_session_bar_map_entry.py:852:    for name in ("timeline_missing", "offset_out_of_range", "double_bpm", "song_changed"):
server/tests/test_messages_bar_map_entry.py:8:범위(0~3) 판정은 세션이 맡는다(AC-LDBARENTRY-003). 그래서 -1 과 4 도 파서는 통과시킨다.
server/tests/test_messages_bar_map_entry.py:38:@pytest.mark.parametrize("offset", [0, 1, 2, 3, -1, 4])
[exit 0]
```

### A-9 — 요청 경로: 허용 목록·파서·디스패치·PROTOCOL.md·화면

```text
$ grep -n -E "bar_map_analyse|BAR_MAP_ANALYSE" server/web/app.py server/web/messages.py
server/web/app.py:841:                elif message_type == "bar_map_analyse":
server/web/messages.py:140:    "bar_map_analyse",
server/web/messages.py:766:    if message_type == "bar_map_analyse":
server/web/messages.py:774:            raise ProtocolError("bar_map_analyse.first_beat_offset must be an integer")
server/web/messages.py:777:            "type": "bar_map_analyse",
[exit 0]
```

### A-9b — PROTOCOL.md의 bar_map_analyse 행(앞뒤 창)

```text
$ grep -n -o -E ".{0,20}bar_map_analyse.{0,60}" server/web/PROTOCOL.md
26:| `bar_map_analyse` | `first_beat_offset` (required int, no default) | (LDBARM
[exit 0]
```

### A-9c — ui/src의 bar_map_analyse 줄 수, messages.py의 낡을 주석

```text
$ grep -rn "bar_map_analyse" ui/src | wc -l
       0
$ grep -n "범위(0~3)" server/web/messages.py
771:        # 범위(0~3)는 여기서 재지 않는다 — 박 수는 세션이 한 곳에서 판정한다.
[exit 0]
```

### A-10 — SPEC-LDBARMAP-001의 4/4 표현(spec.md 36줄 이후, acceptance.md 18줄 이후)

```text
$ grep -n -o -E ".{0,16}(0~3|mod 4|4/4|4박|% 4|0~\(분자).{0,16}" .moai/specs/SPEC-LDBARMAP-001/spec.md | grep -v -E "^([1-9]|[12][0-9]|3[0-5]):"
71:차 ±60ms, 단위 % — 4/4 박자인 이 곡에서는 다운비트
72:전체를 1마디(2.136초, 4박) 밀어낸 격자 — 를 입력받
107: 박 오프셋」(정수 박 번호 0~3, 단위: 박)에서 받는다 —
107:— 정수 beat-index(0~3)는 "비트 배열의 몇 번째가
107:Q 자신의 `shall` 절(mod 4, 범위 0~3)은 LOVE 
107:ATTACK M2 범위(4/4 박자)에 한정된 값이며 바뀌
107: 분자로 나눈 나머지, 범위 0~(분자−1)"로 일반화한 것이고, 
107:이 REQ의 mod 4·0~3은 그 일반화 규칙의 **4/
147: 분자로 나눈 나머지, 범위 0~(분자−1), 단위 박; LOVE 
147:ATTACK M2는 4/4이므로 mod 4·범위 0~3
156:통일; LOVE ATTACK 4/4에서는 1~4), 기본 1 —
156: 지도 보고서의 "67마디 4박에 당겨 들어오는 히트" 같은
160: 분자로 나눈 나머지, 범위 0~(분자−1), 단위 박. LOVE 
160:ATTACK M2 범위(4/4)에서는 분자=4이므로 mod
160: 4·범위 0~3이 그 **인스턴스**다 — 
160:DBARMAP-016 자신은 4/4 전용 M2 범위를 서술하고,
160: 이 일반화 규칙은 비-4/4 곡으로 확장할 때의 재해석이
162:BPM·고정 마디 번호 범위·4/4 전용)을 가정하지 않는다 —
165:운비트와 마디 경계는 이 곡(4/4박자)에서 같은 사건이다.**
$ grep -n -o -E ".{0,16}(0~3|mod 4|4/4|4박|% 4|0~\(분자).{0,16}" .moai/specs/SPEC-LDBARMAP-001/acceptance.md | grep -v -E "^([1-9]|1[0-7]):"
26: 2.136 | 초/마디 | 4박 × 0.534초 |
33:2) | 2.136 | 초(=4박) | REQ-LDBARMAP
35: t530 신설) | 정수, 0~3 | beat-index(be
35:at_times 인덱스 mod 4) | REQ-LDBARMAP
53:— 음성 대조군 2: 1마디(4박) 밀림
55: 전체 1마디(2.136초, 4박) 밀어낸 "날조 격자 2"가
95: **검출기 자신이 위상(1~4박 중 어느 것이 "하나"인가)
99:로 주어진 상태에서(이 곡은 4/4박자라 마디 경계 = 다운비트
100:기의 마디 분할 결과(연속된 4박 그룹의 시작점)를 엄격한 순
103:md §5 열린 결정 3 — 4/4박자 곡이라 다운비트=마디 경
177: ATTACK 모양(82마디·4/4·못갖춘마디 없음)이 아닌 픽
177:스처 — 예: 3/4박자, 못갖춘마디 없음, 마지막
177:다 — LOVE ATTACK(4/4)의 0~3 범위를 그대로 적
218:지정한 첫 박 오프셋(정수, 0~3)이 입력으로 주어진 상태에서
219:중 `(i − offset) % 4 == 0`인 `i`를 다운비
224:beat_times` 인덱스 mod 4). 근거: 감독이 위상 클릭
[exit 0]
```

### A-11 — SPEC-LDBARMAP-002의 4/4 표현(spec.md 33줄 이후, acceptance.md 7줄 이후, plan.md 전체)

```text
$ grep -n -o -E ".{0,16}(0~3|\[4, 4\]|4/4|4박|% 4).{0,16}" .moai/specs/SPEC-LDBARMAP-002/spec.md | grep -v -E "^([1-9]|[12][0-9]|3[0-2]):"
71:| P5 | 분석기는 4/4 전용이다 — 한 마디 박 수
71:ive_bars`는 오프셋이 0~3 밖이면 거절한다 | `ser
73:는 `(i - offset) % 4 == 0`), `bar_ma
93:42`의 주석과 같다. 범위(0~3) 판정은 분석 첫 점검이 맡
126:진입 경로 **shall** 4/4 박자만 다루고 저장되는 `t
126:me_signature`를 `[4, 4]`로 명시해 싣는다. 다른 박
126: | P5, P6. 분석기가 4/4 전용이다. 저장 쪽이 일반적
147:| (가) 4/4 전용 **(2026-10-1
147:me_signature`는 `[4, 4]`로 명시한다(REQ-LDBA
150:는데 곡이 3/4면, 마디가 4박 단위로 묶여 모든 마디 경계
150:time_signature: [4, 4]`가 저장 값에 명시돼 화면이
200:. 보고서가 적은 "67마디 4박에 당겨 들어오는 히트"는 이
235:- 4/4 밖의 박자표 분석(D2). 
$ grep -n -o -E ".{0,16}(0~3|\[4, 4\]|4/4|4박|% 4).{0,16}" .moai/specs/SPEC-LDBARMAP-002/acceptance.md | grep -v -E "^[1-6]:"
11: 오프셋 유효 범위 | 정수 0~3 | 박(beat-index)
11:ap.py:452-457`. 4/4 전용(D2) |
12:| 박자표 | `[4, 4]` | 분자/분모 | REQ-
45:되고 그 본문에 허용 범위 `0~3`이 들어 있다. (2) 검출
63:me_signature == [4, 4]`이고 `first_beat_
163:| 마지막 마디가 4박 미만 | 저장 스키마가 마지
$ grep -n -o -E ".{0,16}(0~3|\[4, 4\]|4/4|4박|% 4).{0,16}" .moai/specs/SPEC-LDBARMAP-002/plan.md
17:2026-10-14): D2 4/4 전용이다. 분석기를 일반화하
[exit 0]
```

### A-12 — 곡 목록(기록)

```text
$ cat .moai/reports/t547/after_songs.txt
song                        med      reg |  outcome@med adopt@med amb@med |  outcome@reg adopt@reg amb@reg
LOVE ATTACK.mp3         112.347  112.002 |         keep   112.347   False |         keep   112.002   False
Club Diver.mp3          139.675  140.026 |         keep   139.675   False |         keep   140.026   False
Cut and Run.mp3         107.666  107.666 |         keep   107.666   False |         keep   107.666   False
Ice cream.mp3           100.446  100.446 |         keep   100.446   False |         keep   100.446   False
Let's Dance.mp3         119.681  120.030 |         keep   119.681   False |         keep   120.030   False
LoveMe.mp3               99.384   99.994 |         keep    99.384   False |         keep    99.994   False
Morning.mp3             117.454  117.454 |         keep   117.454   False |         keep   117.454   False
Rain.mp3                 76.014   76.013 |         keep    76.014   False |         keep    76.013   False
Too Cool.mp3            161.499  160.003 |         keep   161.499   False |         keep   160.003   False
scott-buckley-neon.mp3  120.185  120.185 |         keep   120.185   False |         keep   120.185   False
[exit 0]
```

### A-12b — 로컬 샘플 폴더 목록(추적되지 않는 폴더, 파일은 열지 않았다)

```text
$ ls "../../../src/sample music"
Club Diver.mp3
Cut and Run.mp3
걸그룹DinoDino_C_max최고품질.wav
Ice cream.mp3
Let's Dance.mp3
LoveMe.mp3
Morning.mp3
Rain.mp3
scott-buckley-neon.mp3
Too Cool.mp3
[exit 0]
```

### A-12c — 샘플 폴더의 추적 파일 수

```text
$ git ls-files "src/sample music" | wc -l
       0
[exit 상태: 이 블록은 명령을 한 줄씩 따로 실행해 덧붙였으므로 종료 코드를 캡처하지 않았다 — 출력만 기록]
```

### A-12d — 곡 이름과 박자표 단어를 함께 가진 .moai/reports 줄의 파일별 개수

```text
$ grep -rIn -i -E "(박자표|\bmeter\b|time.signature)" .moai/reports --include="*.md" --include="*.txt" --include="*.json" | grep -i -E "club diver|cut and run|ice cream|let.s dance|loveme|morning|rain|too cool|neon|love attack" | cut -d: -f1 | sort | uniq -c
   3 .moai/reports/t476/rain_after/events.json
   3 .moai/reports/t498/run1_fake_rain_1/events.json
   3 .moai/reports/t498/run1_fake_rain_2/events.json
   3 .moai/reports/t498/run11_rain_real_denyall_again/events.json
   3 .moai/reports/t498/run12_rain_real_write_again/events.json
   3 .moai/reports/t498/run3_rain_real_denyall/events.json
   3 .moai/reports/t498/run6_rain_real_write/events.json
   3 .moai/reports/t499/runs/Club Diver/events.json
   3 .moai/reports/t499/runs/Cut and Run/events.json
   3 .moai/reports/t499/runs/Ice cream/events.json
   3 .moai/reports/t499/runs/Morning/events.json
   3 .moai/reports/t499/runs/Rain_first/events.json
   3 .moai/reports/t499/runs/Rain/events.json
   3 .moai/reports/t499/runs/scott-buckley-neon/events.json
   3 .moai/reports/t499/runs/Too Cool/events.json
   3 .moai/reports/t501/ac016/real_rain_212_denyall/events.json
   3 .moai/reports/t501/ac016/real_rain_212_write/events.json
   3 .moai/reports/t501/ac016/rehearse_rain_212_run2/events.json
   3 .moai/reports/t501/ac016/rehearse_rain_212/events.json
   2 .moai/reports/t539/plan-audit-m4.md
   1 .moai/reports/t541/plan-audit.md
   1 .moai/reports/t574/run-verdict.md
[exit 0]
```

### A-12e — 왈츠·복합박 단어를 가진 파일(이 SPEC 디렉터리 제외)

```text
$ grep -rIl -i -E "waltz|왈츠|compound meter|복합박" .moai/specs .moai/reports server tools docs 2>/dev/null | grep -v "SPEC-LDBARMAP-005"
[exit 1]
```

### A-12f — 코드의 4/4 리터럴(시험 제외)

```text
$ grep -rn -E "meter: str = \"4/4\"|\"time_signature\": \"4/4\"" server --include="*.py" | grep -v "^server/tests"
server/design/profile.py:299:    meter: str = "4/4"
server/design/sugar_timeline.py:473:        "time_signature": "4/4",
[exit 0]
```

### A-14 — 선행 SPEC의 상태·phase·tier

```text
$ grep -n -E "^(id|status|phase|tier):" .moai/specs/SPEC-LDARRANGE-001/spec.md .moai/specs/SPEC-LDBEAT-001/spec.md .moai/specs/SPEC-LDBARMAP-001/spec.md .moai/specs/SPEC-LDBARMAP-002/spec.md
.moai/specs/SPEC-LDBARMAP-001/spec.md:2:id: SPEC-LDBARMAP-001
.moai/specs/SPEC-LDBARMAP-001/spec.md:5:status: completed
.moai/specs/SPEC-LDBARMAP-001/spec.md:10:phase: "Lighting Copilot v1.2 target"
.moai/specs/SPEC-LDBARMAP-001/spec.md:14:tier: M
.moai/specs/SPEC-LDARRANGE-001/spec.md:2:id: SPEC-LDARRANGE-001
.moai/specs/SPEC-LDARRANGE-001/spec.md:5:status: draft
.moai/specs/SPEC-LDARRANGE-001/spec.md:10:phase: "Lighting Copilot v1.2 target"
.moai/specs/SPEC-LDARRANGE-001/spec.md:14:tier: M
.moai/specs/SPEC-LDBARMAP-002/spec.md:2:id: SPEC-LDBARMAP-002
.moai/specs/SPEC-LDBARMAP-002/spec.md:5:status: completed
.moai/specs/SPEC-LDBARMAP-002/spec.md:10:phase: "Lighting Copilot v1.2 target"
.moai/specs/SPEC-LDBARMAP-002/spec.md:14:tier: M
.moai/specs/SPEC-LDBEAT-001/spec.md:2:id: SPEC-LDBEAT-001
.moai/specs/SPEC-LDBEAT-001/spec.md:5:status: completed
.moai/specs/SPEC-LDBEAT-001/spec.md:10:phase: "Lighting Copilot v1.2 target"
.moai/specs/SPEC-LDBEAT-001/spec.md:14:tier: L
$ grep -c "^| REQ-LDBARENTRY-" .moai/specs/SPEC-LDBARMAP-002/spec.md
16
$ grep -c "^### AC-LDBARENTRY-" .moai/specs/SPEC-LDBARMAP-002/acceptance.md
16
[exit 0]
```

### A-15 — 형제 SPEC-LDBARMAP-004(다른 워크트리)의 저장 모양 관련 줄

```text
$ grep -n -o -E ".{0,16}(REQ-LDBARLEN-002|REQ-LDBARENTRY-010|OD-1\. 원본).{0,60}" ../WT-barmap-song-match/.moai/specs/SPEC-LDBARMAP-004/spec.md | head -8
66:02/spec.md:111`(REQ-LDBARENTRY-010). **이 약속은 OD-4의 길이 기록과 부딪힐 수 있다(§5 「SPEC-LDBARMAP-002 개정 문안
94:| REQ-LDBARLEN-002 | [HARD] **The** 원본 기록 **shall** 마디 지도 사전 안에 들어가지 **shall n
123:**OD-1. 원본 기록의 자리 — 확정(결정 6).** 원본 기록은 타임라인의 기존 키 `total_duration_ms` 
188:- REQ-LDBARENTRY-010(`.moai/specs/SPEC-LDBARMAP-002/spec.md:111`): 「서버 shall 타임라
191:충돌이 생기는 자리: REQ-LDBARENTRY-010은 **저장이 성공하는 순간**의 변화를 말한다. OD-4가 길이를 쓰는 때는 **곡 입력·분석 때**이고,
194: `draft` 표식뿐이다. REQ-LDBARENTRY-010의 저장 조항은 충돌하지 않는다. AC-LDBARENTRY-004 (5)도 호출 전 상태를 기준으로 비교하므
198:- REQ-LDBARENTRY-010: 「서버 shall 타임라인에서 `bar_map` 키, 저장 관문이 얹는 `draft` 표식, SPEC-L
223: 안이거나 저장 관문 안이면 REQ-LDBARENTRY-010을 개정해야 한다(§5 「SPEC-LDBARMAP-002 개정 문안」). 개정 없이 구현하면 완료 보고가 거
$ grep -n -o -E ".{0,16}라벨 목록 고정.{0,16}" ../WT-barmap-song-match/.moai/specs/SPEC-LDBARMAP-004/spec.md
99:REQ-LDBARUI-007(라벨 목록 고정) |
$ grep -n -E "^(id|status|module):" ../WT-barmap-song-match/.moai/specs/SPEC-LDBARMAP-004/spec.md | cut -c1-200
2:id: SPEC-LDBARMAP-004
5:status: draft
11:module: "server/web/session.py, server/audio/bar_map.py, server/audio/bar_map_entry.py, server/audio/bar_map_store.py, server/web/PROTOCOL.md, server/tests/test_session_bar_map_entry.py, server/tes
[exit 0]
```

### A-16 — 소비자 쪽 3/4 시험

```text
$ sed -n 116,123p server/tests/test_beat_grid_entry_t574.py


@pytest.mark.parametrize(("beats_per_bar", "ok", "bad"), [(4, 4, 5), (3, 3, 4)])
def test_trigger_beat_range_follows_the_song_meter(beats_per_bar, ok, bad) -> None:
    assert _edit(_entry(trigger_beat=ok), beats_per_bar)["trigger_beat"] == ok
    with pytest.raises(BeatGridEditError, match="트리거"):
        _edit(_entry(trigger_beat=bad), beats_per_bar)

[exit 0]
```

### A-17 — 수락 기준 명령의 변경 전 기준값(버전 관리 명령은 A-17b)

```text
$ grep -c -E "_BEATS_PER_BAR|% 4|_TIME_SIGNATURE|0~3" server/audio/bar_map.py server/audio/bar_map_entry.py
server/audio/bar_map_entry.py:5
server/audio/bar_map.py:8
$ sed -n "/message_type == \"bar_map_analyse\"/,/^    if message_type == \"question_answer\"/p" server/web/messages.py | wc -l
      16
$ sed -n "/message_type == \"bar_map_analyse\"/,/^    if message_type == \"question_answer\"/p" server/web/messages.py | grep -c -i -E "meter|time_signature|numerator|beats_per_bar|박자"
0
$ sed -n "/message_type == \"bar_map_analyse\"/,/elif message_type == \"history_restore\"/p" server/web/app.py | grep -c -i -E "meter|time_signature|numerator|박자"
0
[exit 1]
```

### A-13 — SPEC ID 정규식, 접두사 충돌, 형제 워크트리

```text
$ ID="SPEC-LDBARMAP-005"; [[ "$ID" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]] && echo PASS || echo FAIL
PASS
$ git grep -c "LDBARMETER" HEAD
(위 명령은 일치가 없어 출력 없음)
$ git grep -c "LDBARMETER" origin/main
(위 명령은 일치가 없어 출력 없음)
$ git log --all --oneline -S"LDBARMETER" | wc -l
       0
$ git log --all --oneline -S"SPEC-LDBARMAP-005" | wc -l
       0
(위 명령은 출력이 개수 한 줄이다)
$ ls -d ../*/.moai/specs/SPEC-LDBARMAP-* 2>/dev/null | grep -v "^\.\./t656/" | cut -d/ -f5 | sort | uniq -c
  41 SPEC-LDBARMAP-001
  14 SPEC-LDBARMAP-002
   1 SPEC-LDBARMAP-003
   1 SPEC-LDBARMAP-004
$ ls -d ../*/.moai/specs/SPEC-LDBARMAP-00[3-9] 2>/dev/null | grep -v "^\.\./t656/"
../t648/.moai/specs/SPEC-LDBARMAP-003
../WT-barmap-song-match/.moai/specs/SPEC-LDBARMAP-004
```

### A-17b — 동결 파일 점검의 변경 전 기준값(버전 관리 명령)

```text
$ git diff --name-only bef3e16d9da14a398f7c07a8f48bdff94097a636 HEAD -- .moai/specs/SPEC-LDBARMAP-001 .moai/specs/SPEC-LDBARMAP-002 | wc -l
       0
$ git status --short -- .moai/specs/SPEC-LDBARMAP-001 .moai/specs/SPEC-LDBARMAP-002 | wc -l
       0
```
