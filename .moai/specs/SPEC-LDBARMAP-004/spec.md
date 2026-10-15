---
id: SPEC-LDBARMAP-004
title: "마디 지도 저장 — 곡 길이 확인과 원본 기록 (서버)"
version: "0.1.1"
status: draft
created: 2026-10-14
updated: 2026-10-15
author: jaihyun
priority: P1
phase: "Lighting Copilot v1.2 target"
module: "server/web/session.py, server/audio/bar_map.py, server/audio/bar_map_entry.py, server/audio/bar_map_store.py, server/web/PROTOCOL.md, server/tests/test_session_bar_map_entry.py, server/tests/test_audio_bar_map_store.py"
lifecycle: spec-anchored
tags: "bar-map, save-gate, song-length, audio-provenance, server-only, draft"
tier: M
related_specs: [SPEC-LDBARMAP-001, SPEC-LDBARMAP-003]
depends_on: [SPEC-LDBARMAP-002]
---

# SPEC-LDBARMAP-004 — 마디 지도 저장: 곡 길이 확인과 원본 기록 (서버)

## HISTORY

| 일자 | 버전 | 내용 |
|---|---|---|
| 2026-10-14 | 0.1.0 | 최초 작성(카드 t649, plan 단계). 입력: 길이 측정 기록 `.moai/reports/t649/measure.md`(측정 기준 커밋 `af2dd7e1`), 감독 결정 2026-10-14 「C + B 길이만」, 선행 SPEC-LDBARMAP-002(`status: completed`), 화면 쪽 SPEC-LDBARMAP-003(브랜치 `WT-barmap-entry-ui`, 아직 머지 전)과의 문구 정렬. 코드 변경 0줄. 요구사항 접두사는 `REQ-LDBARLEN-`, 수락 기준 접두사는 `AC-LDBARLEN-`이다(현재 HEAD와 `WT-barmap-entry-ui`에서 미사용을 확인했다). 허용 오차 수치와 타임라인 길이 출처는 감독이 정할 때까지 비워 두었다(§5 열린 결정). |
| 2026-10-15 | 0.1.1 | plan 단계 개정(카드 t649). REQ-LDBARLEN-003에서 원본 기록의 자리를 중립으로 바꿨다(자리는 OD-1이 정한다). 전제 P10을 정정하고(시드 항목이라는 예외가 있다) P18을 더했다(정적 추적이며 실행 확인은 아니다). OD-8(저장 성공 문구의 화면 표시)을 더했고, OD-4와 §7에 P18 참조를 달았다. 열린 결정의 선택지는 고르지 않았고 허용 오차 수치는 여전히 없다. 요구사항·수락 기준 번호는 그대로다. |

## §0. Tier 선택 근거

- 판정: **Tier M**. 산출물은 `spec.md`·`plan.md`·`acceptance.md` 세 개다. `progress.md`는 모든 Tier 공통이라 셈에 들지 않는다. `research.md`는 Tier L에서만 요구되므로 만들지 않는다.
- 근거(파일 수): 예상 변경 파일은 8개다(`plan.md` §파일 요약). Tier S의 상한(5개 미만)을 넘고, Tier L의 기준(15개 초과 또는 헌법적 변경)에는 닿지 않는다.
- 주의: LOC는 아직 재지 않았다(코드를 쓰기 전이다). 구현 뒤 LOC가 1000을 넘으면 Tier L로 재판정한다(`.claude/rules/moai/workflow/spec-workflow.md` § SPEC Complexity Tier).
- 예산: 요구사항 11개, 수락 기준 12개. Tier M 상한(각 16개) 안이다.

## §1. 배경 — 왜 지금인가

- SPEC-LDBARMAP-002가 분석에서 저장까지의 서버 입구를 열었다. 저장 관문은 마디 지도 자체의 모양만 검사하고, **그 지도가 어느 곡 음원에서 나왔는지**와 **그 음원의 길이가 초안 타임라인과 맞는지**는 검사하지 않는다.
- 측정 기록(`.moai/reports/t649/measure.md`)은 다음을 보였다. (a) 디코드한 길이는 FFmpeg 전체 디코드와 밀리초 단위에서 전부 같았다(실제 곡 10개). (b) 헤더가 선언한 길이는 디코드 길이와 최대 0.243초 차이가 났고, Let's Dance는 헤더 판독기 셋 모두 48초 이상 부풀었다. (c) Xing 헤더가 없는 VBR 보정 파일에서 디코더가 10초 파일을 3.284초로 읽고도 오류를 내지 않았다(조용한 잘림).
- 감독 결정(2026-10-14): 화면에 곡 파일명을 보이는 일은 SPEC-LDBARMAP-003이 맡는다. 이 SPEC은 **서버만** 바꾼다. 세 가지를 한다. (1) 저장 시 곡 파일명과 sha256을 마디 지도 **밖**에 기록한다. (2) 저장 성공 응답 문구에 파일명과 타임라인 제목을 싣는다. (3) 곡 **길이만** 대조한다. BPM 대조는 하지 않는다.

## §2. 범위

### 포함

- 저장 성공 때 분석에 쓴 곡 오디오의 파일명과 sha256을 마디 지도 밖에 기록한다(REQ-LDBARLEN-001, 002, 003).
- 저장 성공 응답의 첫 문장을 SPEC-LDBARMAP-003과 같은 글자로 쓰고, 타임라인 제목을 함께 싣는다(REQ-LDBARLEN-004).
- 분석 디코드 길이와 타임라인의 곡 길이 정보를 대조한다. 정보가 없으면 「확인할 수 없음」으로 통과시킨다(REQ-LDBARLEN-005~007, 009).

### 제외

§8 「제외 범위」를 본다.

## §3. 전제와 증거

아래 줄 번호는 기준 커밋 `fe6adf28`의 워킹 트리를 열어 읽은 것이다. 옮긴 값은 쓰지 않았다.

| ID | 사실 | 근거 |
|---|---|---|
| P1 | 저장 성공 응답 문구는 지금 파일명을 싣지 않는다 | `server/web/session.py:9461` (「마디 지도를 초안에 저장했습니다 (콘솔 무접촉). …」) |
| P2 | 분석은 시작할 때 곡 오디오 객체를 한 번 잡는다. 분석 중의 업로드는 `self._song_audio`만 바꾼다 | `session.py:9498` (`audio = self._song_audio`), `session.py:13770` (새 `SongAudioUpload` 대입) |
| P3 | 곡 오디오 객체는 파일명과 sha256을 이미 가진다 | `session.py:13770-13776` (sha256은 `:13774`) |
| P4 | 마디 지도 사전의 최상위 키는 여섯 개로 고정되고, 그 밖의 키는 거절된다 | `server/audio/bar_map_store.py:54-56`(`_TOP_LEVEL_KEYS`), `:175-177`(알 수 없는 필드 거절) |
| P5 | SPEC-LDBARMAP-002는 저장 성공 때 `bar_map` 키와 `draft` 표식만 바뀌고 「그 밖의 키는 바이트까지 같다」고 약속한다 | `.moai/specs/SPEC-LDBARMAP-002/spec.md:111`(REQ-LDBARENTRY-010). **이 약속은 OD-1과 충돌한다** |
| P6 | 디코드 길이는 샘플 수 ÷ 샘플레이트, 밀리초 반올림이다 | `server/audio/bar_map.py:213-214` |
| P7 | 디코드 길이는 탐지 결과로 나가지 않는다. `BeatGridResult`에 길이 필드가 없고, `detect_beat_grid`는 `mono`와 `sample_rate`만 꺼낸다 | `bar_map.py:105-116`, `:229-232` |
| P8 | 같은 바이트가 특징 추출에서 한 번 더 디코드된다 | `bar_map.py:625-628` |
| P9 | 조용한 잘림 검사는 선언 길이가 어림값(`length_is_a_guess`)이면 꺼진다 | `bar_map.py:199-202`; 어림 판정 `server/audio/analyze.py:317-341` |
| P10 | 설계 흐름이 만드는 초안 타임라인에는 곡 길이(`total_duration_ms`)를 채우는 생산자가 없다. 주석이 이를 명시한다. 이름으로 이 키를 쓰는 비테스트 코드는 여섯 줄뿐이고, 값을 넣는 줄은 샘플 빌더의 고정 값 하나다. **다만 그 값이 초안에 들어오는 길은 있다(P18)** | `server/web/session.py:1505-1509`(「곡 전체 길이를 아는 생산자가 없다」). 설계 흐름의 헤더는 `apply_cue_sheet_view`(`server/design/song_plan.py:1109-1115`)가 `CueSheetViewFields.to_dict()`를 합쳐 만들고, 값이 `None`이면 키를 싣지 않는다(`song_plan.py:1064-1067`). `git grep -n total_duration_ms -- 'server/*.py' ':!server/tests'`는 `song_plan.py:919`·`:1024`·`:1040-1041`(필드 선언과 값 검사), `session.py:1505`(주석), `server/design/sugar_timeline.py:475`(`build_sugar_timeline` 안의 고정 값 `236_000`)만 돌려준다. 이름 검색에는 기록 경로가 없어 보이지만, 항목을 통째로 복사하는 길은 이름에 걸리지 않는다(P18) |
| P11 | 확정 BPM 상태 `_song_bpm`은 타임라인 `bpm`과 같은 객체다 | `session.py:4297-4301` |
| P12 | REQ-LDBARENTRY-011 원문: 진입 경로는 콘솔에 쓰거나 읽지 않고, `SongTimelineLibrary`에 저장하지 않고, BPM 확정 상태를 바꾸지 않고, `analyse_song_audio`의 메시지 계약을 바꾸지 않는다 | `.moai/specs/SPEC-LDBARMAP-002/spec.md:112` (HEAD와 `WT-barmap-entry-ui`에서 같은 문장) |
| P13 | 화면 쪽 정렬 대상: 저장 성공 문구(REQ-LDBARUI-006), 거절 라벨 세 개(REQ-LDBARUI-007), 파일명 시점 한계(E3) | `WT-barmap-entry-ui:.moai/specs/SPEC-LDBARMAP-003/spec.md:79`, `:80`, `:176` |
| P14 | 분석 중 초안이 다른 곡으로 바뀌었는지 두 시점을 비교해 확인한다 | `session.py:9557-9558` |
| P15 | 저장 성공 시 타임라인 전체가 `song_timeline` 프레임으로 나간다 | `session.py:9456`; `server/web/PROTOCOL.md:83` |
| P16 | 곡 오디오 링크 기록은 `OSError`를 조용히 삼킨다 | `session.py:13787-13789` (`contextlib.suppress(OSError)`) |
| P17 | 저장 관문의 거절 응답은 이벤트를 반환만 하고 보내지 않는다. 성공은 직접 보낸다 | `session.py:9569-9572` |
| P18 | **시드 항목의 `total_duration_ms`(236000)는 초안 타임라인으로 흐른다.** 정적 추적이며 실행 확인은 아니다(읽은 트리: HEAD `0c167944`). 조건은 운영자가 라이브러리의 시드 항목을 불러오는 것이다(`POST /api/timelines/{id}/load`). 이 값은 첨부 곡의 길이가 아니라 샘플 문서 한 판의 고정 값이다. 이 키를 읽어 디코드 길이와 비교하는 비테스트 코드는 0줄이다(P10의 검색 결과) | 홉: ① `server/web/serve.py:29`(import), `:450-452`(`SongTimelineLibrary(..., seed=(sugar_library_entry(),))`) → ② `server/design/sugar_timeline.py:486`(`sugar_library_entry`)이 `build_sugar_timeline()`(`:455`)의 결과를 `timeline`에 싣는다. 값 리터럴은 `:475`이고 `build_sugar_timeline` 안에 있다 → ③ `server/web/timeline_library.py:67`(`_load`)과 `:126`(`_seeded`)로 항목 목록에 들어가고, `:76`(`get`)이 사본을 돌려준다 → ④ `server/web/timeline_api.py:58`(`deps.library.get`), `:69`(`dict(entry["timeline"])` 통째 복사이므로 이름 검색에 안 걸린다), `:71`(`deps.store.latest = timeline`) → ⑤ `deps.store`는 `server/web/app.py:1144`에서 `deps.song_timeline_store`이고, 세션도 `app.py:428`로 같은 객체를 받는다(`session.py:4168` `self._timeline_store`) → ⑥ `session.py:3769-3773`(`SongTimelineStore.latest` 세터)는 키를 거르지 않는다 → ⑦ `analyse_bar_map`이 `store.latest`를 읽고(`session.py:9526`, `:9557`), 저장 관문은 `attach_bar_map`(`server/audio/bar_map_store.py:338`의 `dict(timeline)` 사본)으로 다른 키를 그대로 둔다(`session.py:9451`). 라이브러리 읽기 API는 `items()`(`timeline_library.py:71`)와 `get()`(`:76`) 둘이다. 비테스트 호출처: `session.py:11236`(`items()`, 셋리스트 — 읽는 필드는 `sequence_number`·`console_stored`뿐이다, `:11282-11284`), `timeline_api.py:33`(`items()`를 `timeline_entry_summary`로 투영한다 — 그 투영 `timeline_library.py:33-45`에 길이 필드는 없다), `timeline_api.py:58`(`get()`, 위 ④). **미확인(Gap)**: 앱을 띄워 불러오기를 실행하지 않았다. `ui/src`가 이 엔드포인트를 어떻게 부르는지 열지 않았다. 불러온 뒤 `store.latest`를 다시 쓰는 다른 경로(`session.py:8869` 등 10곳)가 이 키를 지우는지 하나씩 읽지 않았다 |

측정 근거(`.moai/reports/t649/measure.md`):

- M1: 실제 곡 10개에서 앱 디코드 길이와 FFmpeg 전체 디코드 길이가 밀리초 단위로 같다(§2). 샘플 단위 비교는 하지 않았다.
- M2: 헤더 선언 길이는 디코드와 0~0.243초 다르다(Let's Dance 제외). Let's Dance는 헤더 판독기 셋 모두 +48초 이상이다(§2).
- M3: Xing 없는 VBR 보정 파일(10.000초)을 앱 디코더가 3.284초로 읽었다. 오류는 없었다. `bitrate_guess=True`라 잘림 검사가 꺼졌다(§1). 원인은 libsndfile이 헤더 추정 프레임에서 멈춘 것이라는 **가설**이며 확인되지 않았다.
- M4: Let's Dance도 `bitrate_guess=True`인데, 디코드는 90.984초로 FFmpeg과 일치한다(§2, §6). 즉 어림 플래그가 켜졌다고 곧 잘린 것은 아니다.
- M5: 편집판 쌍은 0개이고, LOVE ATTACK 음원은 저장소 안에 없다(§4, §5). 타임라인 길이 측정은 0건이다(§3).

## §4. 요구사항 (GEARS)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBARLEN-001 | [HARD] **When** 분석이 성공해 저장 관문에 이르면, 서버 **shall** 분석 시작 때 잡은 곡 오디오 객체의 파일명과 sha256을 저장 결과에 기록한다. 분석 도중 새로 올라온 곡의 값을 **shall not** 쓴다. | P2, P3. 분석 중 교체되면 디코드한 바이트와 기록이 어긋난다 |
| REQ-LDBARLEN-002 | [HARD] **The** 원본 기록 **shall** 마디 지도 사전 안에 들어가지 **shall not** 한다. `bar_map` 사전의 최상위 키 집합(여섯 개)과 `validate_bar_map`의 검사는 바뀌지 **shall not** 한다. 기록의 정확한 위치는 OD-1로 정한다. | P4, P5. 감독 결정: 마디 지도 밖 |
| REQ-LDBARLEN-003 | **When** 저장이 거절되면(길이 불일치 포함, REQ-LDBARLEN-007), 서버 **shall** 기존 타임라인을 한 바이트도 바꾸지 **shall not** 하고, 원본 기록의 상태(없었으면 없는 채로, 있었으면 있던 그대로)도 바꾸지 **shall not** 하며, 되돌리기 깊이도 그대로 둔다. 원본 기록을 어디에 두는지는 OD-1이 정한다. | REQ-LDBARENTRY-007(SPEC-LDBARMAP-002 §4.2) 계승; OD-1 |
| REQ-LDBARLEN-004 | **When** 저장이 성공하면, 서버 **shall** 응답 `text`의 첫 문장을 「곡 «{파일명}» 마디 지도를 초안에 저장했습니다.」와 **같은 글자**로 쓰고, 이어서 타임라인 제목을 싣는다. 파일명이 비어 있으면 첫 문장은 「마디 지도를 초안에 저장했습니다.」다. 「콘솔 무접촉」과 「라이브러리에 남기려면 별도로 저장」 문장은 남긴다. | P1; SPEC-LDBARMAP-003 REQ-LDBARUI-006(정렬); SPEC-LDBARMAP-002 REQ-LDBARENTRY-011이 약속한 문구 |
| REQ-LDBARLEN-005 | **When** 분석이 성공해 저장 직전에 이르면, 서버 **shall** 디코드 길이(밀리초)를 타임라인의 곡 길이 정보와 대조한다. 대조 시점은 곡 열쇠 재확인(REQ-LDBARENTRY-009) 뒤다. | P14, P6 |
| REQ-LDBARLEN-006 | **When** 타임라인에 곡 길이 정보가 없으면, 서버 **shall** 길이 확인을 통과로 처리하고 응답 `text`에 「곡 길이: 확인할 수 없음」이라는 사실을 적는다. 이때 저장은 성공한다. | 감독 결정 3(B 결정) |
| REQ-LDBARLEN-007 | **When** 타임라인에 곡 길이 정보가 있고 디코드 길이와의 차이가 허용 오차를 넘으면, 서버 **shall** 저장하지 **shall not** 하고, 두 길이를 응답 `text`에 싣는다. 요약 라벨은 기존 라벨 가운데 하나를 쓰고 새 라벨을 만들지 **shall not** 한다. 허용 오차의 값과 라벨 선택은 OD-2, OD-3이 정한다. | 감독 결정 4(허용 오차 미정); SPEC-LDBARMAP-003 REQ-LDBARUI-007(라벨 목록 고정) |
| REQ-LDBARLEN-008 | [HARD] **The** 길이 확인 **shall not** 확정 BPM 상태(`_song_bpm`, `_song_analysis`)를 읽거나 기록된 BPM과 비교하지 **shall not** 한다. | 감독 결정 3; P11, P12(REQ-LDBARENTRY-011 유지) |
| REQ-LDBARLEN-009 | [HARD] **The** 디코드 길이 **shall** 분석에 쓴 바이트를 디코드한 결과에서 얻는다. 헤더가 선언한 길이(libsndfile 선언값, ffprobe, afinfo)를 길이 값으로 **shall not** 쓴다. | P6, P7, P8, M1, M2 |
| REQ-LDBARLEN-010 | [HARD] **The** 구현과 시험 **shall not** 특정 곡의 길이·제목·파일 해시를 상수로 박거나, 음원 파일을 저장소에 커밋하지 **shall not** 한다(REQ-LDBARENTRY-016 계승). | 감독 원칙(2026-10-10, 전 레인 공통) |
| REQ-LDBARLEN-011 | [HARD] **The** 저장 관문의 요약 라벨 집합(`마디 지도 저장`, `마디 지도 분석 거절`, `마디 지도 저장 거절`, `마디 지도 저장 불가`)과 `chat_response` 프레임의 `status`(`ok`)는 바뀌지 **shall not** 한다. 새 클라이언트 메시지 타입을 **shall not** 추가한다. 바뀌는 것은 REQ-LDBARLEN-004의 성공 문구와 REQ-LDBARLEN-006·007이 정하는 문장뿐이다. | REQ-LDBARENTRY-012, REQ-LDBARENTRY-013(SPEC-LDBARMAP-002 §4.3~4.4), SPEC-LDBARMAP-003 REQ-LDBARUI-007 |

## §5. 감독 결정과 열린 결정

### 확정된 결정 (재논의하지 않는다)

1. 결정은 「C + B 길이만」이다.
2. C(화면에 파일명 보이기)는 SPEC-LDBARMAP-003의 몫이다. 이 SPEC은 서버만 다룬다. (a) 원본 기록은 마디 지도 **밖**에 둔다(마디 지도 안이나 마디 지도의 새 최상위 키는 쓰지 않는다). (b) 저장 성공 응답 문구에 파일명과 타임라인 제목을 싣는다.
3. B는 길이만 본다. BPM 대조는 하지 않는다. REQ-LDBARENTRY-011은 그대로 둔다. 타임라인에 길이 정보가 없으면 「확인할 수 없음」으로 통과시키고, 응답 문구에 그 사실을 적는다.
4. 허용 오차는 **결정되지 않았다**. 이 문서에는 숫자가 없다(OD-2).
5. 등급은 파일 수로 정했다(§0).

### 열린 결정 (감독이 정한다. 이 SPEC은 어느 선택지도 고르지 않았다)

**OD-1. 원본 기록의 자리.** 「마디 지도 밖」은 확정이다. 자리는 아직 정하지 않았다.

- 선택지 (a): 타임라인의 최상위 키, `bar_map`과 같은 단계에 둔다(제안 이름 예: `bar_map_source`). 장점: 저장 경로 한 곳에서 같이 쓰이고 재시작에도 남는다(타임라인 저장소가 그 키를 보존한다는 전제는 확인하지 않았다, §6). **단점: SPEC-LDBARMAP-002 REQ-LDBARENTRY-010이 「그 밖의 키는 바이트까지 같다」고 약속하므로 충돌한다.** 이 선택지를 고르면 SPEC-LDBARMAP-002 REQ-LDBARENTRY-010을 정식 개정(`completed → in-progress (amendment)`)해야 한다.
- 선택지 (b): 곡 열쇠로 찾는 별도 기록 저장소를 둔다(곡 오디오 링크 저장소 옆). 장점: 타임라인 바이트가 그대로다. 단점: 새 저장소와 쓰기 실패 처리가 필요하다. 링크 쓰기는 `OSError`를 조용히 삼키므로(P16) 이 경로를 그대로 빌려 쓰면 원본 기록이 조용히 빌 수 있다.
- 선택지 (c): 세션 메모리에만 둔다. 장점: 타임라인과 저장소를 건드리지 않는다. 단점: 서버 재시작 뒤 원본이 사라진다.

**OD-2. 허용 오차.** 숫자를 쓰지 않는다. 근거가 없다. 편집판 쌍이 0개이고(M5), 타임라인 길이 측정도 0건이다. 측정으로 말할 수 있는 것은 산포뿐이며(M1, M2), 그것은 숫자를 고르는 근거가 아니다. 감독 결정: 근거가 생기기 전까지 숫자를 정하지 않는다.

**OD-3. 길이 불일치 때 쓸 요약 라벨.** 새 라벨은 금지다(REQ-LDBARLEN-011, SPEC-003 REQ-LDBARUI-007 목록). 기존 라벨 두 개가 후보다.

- 후보 (a): `마디 지도 저장 거절`. 저장 검사 거절과 같은 종류라 자연스럽다.
- 후보 (b): `마디 지도 분석 거절`. 분석 결과의 불일치로 읽힌다.

**OD-4. 타임라인 곡 길이의 출처. 가장 중요한 열린 결정이다.** 확인된 사실: 설계 흐름이 만드는 초안 타임라인에는 곡 길이를 채우는 생산자가 없다(P10). 예외는 시드 항목 하나다. 이 항목을 불러오면 고정 값 236000이 초안에 들어온다(P18). 그러므로 이 경로에서는 REQ-LDBARLEN-006(「확인할 수 없음」 통과)이 **상시 결과**가 될 가능성이 크다. 이 상태에서 REQ-LDBARLEN-007은 실제로 실행되지 않는다. 즉 B 대조는 지금 상태로는 사실상 빈 검사다. 감독이 이를 알고 정해야 한다.

- 선택지 (a): 곡 길이를 채우는 생산 경로를 따로 만든다(이 SPEC 범위 밖. 별도 SPEC 또는 카드).
- 선택지 (b): 마지막 구간의 끝으로 길이를 유도한다. 현재 불가능하다(P10 주석: 「마지막 구간의 끝을 아무도 안 준다」).
- 선택지 (c): 「확인할 수 없음」을 이 경로의 상시 결과로 받아들이고, B 검사가 실효 없음을 문서에 명시한다.
- 선택지 (d): 다른 출처. 감독이 제시한다.

**OD-5. 조용한 잘림 가드 정책.** 이 SPEC은 잘림 가드의 동작을 바꾸지 않는다(§8). 정책은 감독이 정한다.

- 사실: 어림 플래그가 켜지면 가드가 꺼진다(P9). 잘림이 실제로 일어났을 때의 메커니즘은 가설이다(M3). 그리고 플래그가 켜진 **정상** 곡 Let's Dance가 있다(M4).
- 선택지 (a): 두 번째 디코더로 교차 검증한다. 런타임에 두 번째 디코더를 쓸 수 있는지는 확인하지 않았다(§6).
- 선택지 (b): 어림 플래그가 켜지면 거절한다. **Let's Dance를 거절한다(M4). 측정된 오거절이다.**
- 선택지 (c): 통과시키되 응답에 「길이 추정」 사실을 적는다.

**OD-6. 입력 자료.** 감독 또는 리드가 공급한다.

- LOVE ATTACK 음원 파일: 저장소 밖 경로가 필요하다. 저장소 안에는 없다(M5). 로컬 전용 게이트에 쓴다(REQ-LDBARLEN-010).
- 편집판 쌍: 0개다(M5). OD-2와 OD-5의 근거가 된다.

**OD-7. 문구 세트.** 다음 문장을 확정해야 구현할 수 있다. 아래 값은 **제안**이며 확정이 아니다.

- 길이 확인 결과 세 가지: 「곡 길이: 확인할 수 없음」(확정 요구, REQ-LDBARLEN-006), 통과 문구(제안: 「곡 길이: 대조 통과」), 불일치 문구(제안: 디코드 길이와 타임라인 길이를 함께 적는 한 문장).
- 타임라인 제목이 없을 때의 문구(제안: 「타임라인 제목: 확인할 수 없음」).

**OD-8. 저장 성공 문구의 화면 표시.** 감독이 정한다. 이 SPEC은 어느 선택지도 고르지 않았다.

- 사실: SPEC-LDBARMAP-003 REQ-LDBARUI-006(브랜치 `WT-barmap-entry-ui`의 `.moai/specs/SPEC-LDBARMAP-003/spec.md:79`, 결과 라벨 표 `:151-158`)은 `마디 지도 저장`일 때 고정된 성공 문장만 보인다(파일명 유무에 따른 두 가지). 서버 `text`를 그대로 보이는 라벨은 거절·불가 세 개뿐이다(REQ-LDBARUI-007, `:80`). 그래서 이 SPEC의 타임라인 제목(REQ-LDBARLEN-004)과 「곡 길이: 확인할 수 없음」(REQ-LDBARLEN-006)은 성공 때 `chat_response.text`로 와이어에는 실리지만 진입 컨트롤의 결과 줄에는 보이지 않는다. REQ-LDBARUI-015는 결과 `chat_response`를 기존 리듀서 처리 그대로 채팅 기록에 남긴다고 하는데, 그 처리가 `text`를 화면에 그리는지는 `ui/src`를 열어 확인하지 않았다. 길이 불일치 거절(REQ-LDBARLEN-007)은 거절 라벨이라 문장이 화면에 보인다.
- 선택지 (a): SPEC-LDBARMAP-003을 그대로 둔다. 비용: 제목과 길이 확인 결과가 성공 때 컨트롤 줄에 보이지 않는다. 이 SPEC의 수락 기준은 서버 응답 `text` 검사까지만 닿는다. 다른 브랜치의 SPEC·구현·시험은 바뀌지 않는다.
- 선택지 (b): SPEC-LDBARMAP-003 REQ-LDBARUI-006을 개정해 성공 때도 서버 `text`를 보이게 한다. 비용: 아직 머지 전인 `WT-barmap-entry-ui`의 SPEC, 화면 구현(`ui/src`), 시험을 함께 고쳐야 한다. 문구 고정표(그 SPEC의 §4)와 REQ-LDBARUI-007과의 일관성을 다시 봐야 한다. 이 SPEC은 `ui/src`를 건드리지 않으므로(§8) 개정은 SPEC-LDBARMAP-003 쪽 작업이다. 두 SPEC이 성공 문장의 첫 문장을 같은 글자로 맞추는 현재 방식(REQ-LDBARLEN-004)도 다시 정해야 할 수 있다.

## §6. Gaps — 확인하지 않은 것

1. 타임라인 저장소(`SongTimelineStore`)가 최상위 키를 재시작 뒤에도 보존하는지 읽지 않았다. OD-1 (a)의 전제다.
2. 타임라인 키 집합을 검사하는 테스트나 UI 코드가 있는지 전수로 세지 않았다(`server/web`, `server/audio`, `server/design`에서 키 허용 목록은 찾지 못했다). `ui/src`는 열지 않았다.
3. 런타임에 두 번째 디코더(예: FFmpeg)를 쓸 수 있는지 확인하지 않았다. OD-5 (a)의 전제다.
4. libsndfile이 헤더 추정 프레임에서 멈춘다는 메커니즘은 재현하지 않았다(M3는 한 파일에서 관찰했을 뿐이다).
5. 타임라인 길이 정보가 실제 세션에서 어떤 경로로 들어오는지 앱 세션을 띄워 확인하지 않았다(측정 기록 §3과 같다).
6. 샘플 단위 비교는 하지 않았다(M1은 밀리초 단위다).
7. LOVE ATTACK 음원과 편집판 쌍은 없다(OD-6).
8. SPEC-LDBARMAP-003의 E3(파일명 시점 한계)는 이 SPEC으로 풀리지 않는다. 원본 기록은 분석 시점의 값이므로, 타임라인 곡과 같은 곡인지는 여전히 열려 있다(곡 열쇠 재확인은 두 시점의 열쇠만 비교한다, P14).
9. `.moai/reports/t649/scope.md`와 `resume.md`의 내용은 이 SPEC의 근거로 쓰지 않았다. `scope.md`는 열어 읽지 않았다.

## §7. 잔여 위험

- **B 검사의 공허함.** 설계 흐름 초안에서는 P10 때문에 REQ-LDBARLEN-007이 실행되지 않는다. 시드 항목을 불러온 초안에서는 고정 값(236000)이 있어 실행될 수 있고, 그 값은 첨부 곡의 길이가 아니다(P18). 이 위험은 OD-4를 정하기 전까지 해소되지 않는다. 검사가 실패할 수 없는 상태를 「검사가 있다」로 보고하면 안 된다(완료 보고에 「길이 대조 통과」라고 쓰려면 실제 대조가 실행된 증거가 있어야 한다).
- **조용한 잘림.** OD-5가 정해지기 전까지, 어림 플래그가 켜진 파일이 부분 길이로 저장될 수 있다(M3). 이 SPEC은 이 위험을 줄이지 않는다.
- **타임라인 키 추가의 파급.** OD-1 (a)를 고르면 `song_timeline` 프레임에 새 키가 실린다(P15). 클라이언트나 시험이 키 집합을 고정하고 있으면 깨진다(§6 Gap 2).
- **SPEC-LDBARMAP-002 약속과의 충돌.** OD-1 (a)는 REQ-LDBARENTRY-010을 개정해야 한다. 개정 없이 구현하면 완료 보고가 거짓이 된다.
- **디코드 두 번.** 분석은 같은 바이트를 두 번 디코드한다(P8). 두 결과가 같다는 것은 현재 확인된 사실이지만, 구현이 길이를 두 번째 디코드에서 얻으면 이 가정이 깨진다(REQ-LDBARLEN-009가 막는다).

## §8. 제외 범위 (Out of Scope)

### Out of Scope — 화면 표시

- 곡 파일명을 화면에 보이는 일(C)은 SPEC-LDBARMAP-003이 맡는다. 이 SPEC은 UI 파일(`ui/src/**`)을 건드리지 않는다.
- 진입 컨트롤, 오프셋 드롭다운, 대기 상태 표시는 이 SPEC의 범위가 아니다.

### Out of Scope — BPM 대조

- 기록된 BPM과 검출 BPM의 비교는 하지 않는다(감독 결정 3, REQ-LDBARLEN-008).
- 두 배 BPM 채택 거절(SPEC-LDBARMAP-002 REQ-LDBARENTRY-008)의 동작은 바꾸지 않는다.

### Out of Scope — 편집판 길이 대조

- 편집판과 원본의 길이 차이를 재는 검사는 이 SPEC에 없다. 입력 쌍이 없고(OD-6), 요구사항도 없다.

### Out of Scope — 허용 오차 수치

- 허용 오차의 숫자는 OD-2가 정하기 전까지 이 문서에 쓰지 않는다. 구현자가 임의로 고르지 않는다.

### Out of Scope — 조용한 잘림 가드 변경

- `server/audio/bar_map.py`와 `server/audio/analyze.py`의 잘림 검사 동작(어림 플래그에 따른 분기)은 바꾸지 않는다. 정책은 OD-5가 정한다.
- 길이 값을 `detect_beat_grid` 결과로 **전달하는** 변경은 이 SPEC의 범위다(REQ-LDBARLEN-009). 검사 로직 변경과 구분한다.

### Out of Scope — 콘솔과 라이브러리

- 콘솔 읽기와 쓰기, `SongTimelineLibrary` 저장은 금지다(SPEC-LDBARMAP-002 REQ-LDBARENTRY-011을 그대로 따른다).
- BPM 확정 흐름(`song_audio_analyse`)의 메시지 계약은 바꾸지 않는다.

### Out of Scope — 분석기와 박자표

- 분석기 알고리즘, 박자표(4/4 전용), 저장 스키마의 분자·분모 규칙은 바꾸지 않는다.

## §9. 참조

- `.moai/reports/t649/measure.md` — 길이 측정 원문 출력과 관찰·추정 구분(§1~§9).
- `.moai/reports/t649/scope.md` — 같은 카드의 범위 검토 문서. 이 SPEC의 근거로는 인용하지 않았다(열어 읽지 않았다, §6 Gap 9).
- `.moai/specs/SPEC-LDBARMAP-002/spec.md` — 선행 SPEC(REQ-LDBARENTRY-001~016).
- `WT-barmap-entry-ui:.moai/specs/SPEC-LDBARMAP-003/spec.md` — 화면 쪽 정렬 대상(REQ-LDBARUI-006, 007, E3). 아직 머지되지 않았다.
- `.claude/rules/moai/workflow/spec-workflow.md` § SPEC Complexity Tier — Tier 판정 기준.
