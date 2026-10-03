# 리듬 표현 조사 보고서 (카드 t502, 2026-10-03)

대상: SPEC-LDRENDER-001 실기 판정 미달(AC-016, 1~2점/5점) 뒤의 후속 조사.
기준 트리: `origin/main` `5220ca4e`. t501 실기 산출물은 미병합 브랜치 `origin/WT-ldrender-run`(`c7b231cd`)에서 읽었다.
성격: 읽기 전용 조사. 코드 수정 0건, 콘솔 쓰기 0건. 증거 원본은 `.moai/reports/t502/`에 있다.

표기 규칙: **[잰 값]** 은 이번에 명령을 돌려 출력을 본 것, **[문서]** 는 MA Lighting 공식 도움말에서 직접 확인한 것, **[추정]** 은 재지 않은 판단이다.

---

## 한눈에 보기

1. **룩이 오래 머무는 것보다 큰 문제는 한 룩 안에 박자가 없다는 점이다.** 감독이 본 Rain(시퀀스 212)에는 페이저가 하나도 실리지 않았다. 구간 안에서 움직이는 것이 아예 없다 [잰 값]. Club Diver(213)는 14큐 중 9큐가 같은 색 파형(Wave CM)을 부르고, 속도 줄을 하나도 보내지 않는다. 무빙 라이트는 큐가 바뀔 때만 위치 프리셋(2.21~2.30, 8종)으로 옮겨 가고, 큐 안에서 움직이는 줄(Pan/Tilt 페이저)은 두 시퀀스 모두 0줄이다 [잰 값].
2. **곡 분석은 BPM 숫자 하나만 넘긴다.** 비트 시각은 계산한 뒤 버리고, 온셋은 계산하지만 저장하지 않는다. 다운비트와 킥 검출은 없다 [잰 값].
3. **콘솔은 BPM 동기를 기본 기능으로 갖고 있다.** 스피드 마스터(BPM 단위, 0~225, 16개)를 페이저에 걸 수 있고, `Master 3.1 At BPM 75` 한 줄로 속도를 바꾼다 [문서].
4. **우리 규칙과 감독 요구는 정면으로 부딪치지 않는다.** §9와 REQ-036은 "룩을 얼마나 자주 바꾸나"를 정한 규칙이고, 감독이 지적한 것은 "한 룩 안의 움직임이 박자를 따르나"다. 이 축은 지금 규칙에 빈칸으로 남아 있다.
5. **권고 방향(감독 확정 전):** 룩 전환 밀도(§9)는 그대로 둔다. 그 위에 (가) 페이저 속도를 곡 BPM에 묶고, (나) 마디·프레이즈 경계의 강조를 원샷 레인으로 얹는다. 큐를 마디마다 잘게 쪼개는 방식은 권하지 않는다.

---

## 0. 출발점 — 감독이 본 것의 실측

감독 판정(2026-10-03, 리드 경유): 「작동은 한다. 그러나 Verse 하나가 20~30초 이상 단조로운 동작·연출 하나다. 리듬·비트에 따라 빠르고 다채롭게 움직여야 음악 표현이 된다.」

### 0.1 큐 유지 시간 [잰 값]

t501이 쓰기 직후 콘솔에서 되읽은 큐 속성(이름·트리거 종류·트리거 시각)으로 "다음 큐까지 몇 초 머무는가"를 계산했다.

- 명령: `python3 .moai/reports/t502/evidence/hold_durations.py`(exit 0)
- 입력: `.moai/reports/t502/evidence/t501_postwrite_cue_props.txt`(= `origin/WT-ldrender-run:.moai/reports/t501/ac016/postwrite_cue_props.txt`)
- 출력 전문: `.moai/reports/t502/evidence/hold_durations.txt`

| 시퀀스 | 곡 | 큐 수 | 트리거 | 유지 시간 최대 | 중앙값 | 20초 이상 | Verse 유지 시간 |
|---|---|---|---|---|---|---|---|
| 212 | Rain | 13 | 전부 Time | 28.5초 | 16.6초 | 4개 | 12.6 · 15.9 · **26.8** · 12.6초 |
| 213 | Club Diver | 14 | 전부 Time | 17.1초 | 10.3초 | 0개 | 10.9초 |

감독이 말한 "20~30초"는 Rain(212)과 맞는다. Verse 3 26.8초, Chorus 5 27.8초, Chorus 6 Return 28.5초.

### 0.2 한 룩 안에서 움직이는 것 [잰 값]

- **Rain(212): 페이저 송신 0건.** t501 진행 기록 표(`origin/WT-ldrender-run:.moai/specs/SPEC-LDRENDER-001/progress.md` 2004~2014행)에서 Rain 행은 `fx 요청/힌트/송신 = 0/11/0`이다. 설계 층이 Rain에 효과 예산을 주지 않았다. 그래서 212에서는 큐가 바뀌기 전까지 조명이 정지 화면으로 머문다.
- **Club Diver(213): 페이저 송신 11건.** 다만 페이저를 고르는 방식이 구간 이름 하나다. `server/design/song_cue_render.py:494-504`를 보면 Chorus는 `Wave CM`, Verse는 `Breathe Warm`, Bridge는 `Breathe Cool`, 피크는 `Drop Slam`, 피날레는 `Finale Slam`이다. 같은 이름의 구간에는 같은 움직임이 반복된다.
- **속도 줄은 어느 곡에도 없다.** 페이저 프리셋을 만드는 `server/web/session.py`의 빌더(`_color_phaser_form_commands` 등)는 `At Accel`·`At Decel`·`At Transition`·`At Phase`만 보낸다. `At Speed` 줄은 없다(아래 §2.1).

실제로 콘솔에 보낸 명령 목록(t501 승인 요청 원문 사본)을 세어 확인했다 [잰 값].

| 시퀀스 | 명령 줄 | 페이저 프리셋 호출 | 속도(`speed`) 줄 | 위치 프리셋 호출(큐 경계 이동) | Pan/Tilt 페이저 줄 | `Attribute` 줄에 쓰인 속성 |
|---|---|---|---|---|---|---|
| 213 Club Diver | 266 | 11 (`4.9` Wave CM ×9, `4.11` Breathe Warm ×1, `21.8` Finale Slam ×1) | 0 | 13 (2.21~2.30 중 8종) | 0 | Dimmer, ColorRGB_R/G/B/W |
| 212 Rain | 237 | 0 | 0 | 12 (같은 8종) | 0 | Dimmer, ColorRGB_R/G/B/W |

- 명령: `grep -ci "speed"`, `grep -oE "At Preset (4|21)\.[0-9]+" | sort | uniq -c`, `grep -oE "At Preset 2\.[0-9]+" | sort | uniq -c`, `grep -oE "Attribute '[^']+'" | sort | uniq -c` — 대상 파일 `.moai/reports/t502/evidence/t501_{clubdiver_213,rain_212}_approval_request.txt`
- 양성 대조: 같은 파일에서 `At Preset 4.9`는 9건 걸렸다. grep이 정상이고, 속도 줄 0은 실제 부재다.

정리하면, 감독의 지적은 큐 밀도 문제이기 전에 **룩 안이 정지해 있거나(Rain: 페이저 0, 위치는 큐 경계에서만 이동) 박자와 무관한 색 파형 하나가 반복된다(Club Diver: 14큐 중 9큐가 같은 Wave CM, 큐 안의 위치 움직임 0)**는 문제다.

---

## ① 곡 분석이 비트·다운비트·킥 위치를 이미 내는가

**답: BPM 숫자 하나만 렌더러에 닿는다.** 비트 시각은 계산한 뒤 버리고, 다운비트와 킥은 만들지 않는다.

| 항목 | 생산 | 저장(`analysis.json`) | 렌더러 소비 | 근거 |
|---|---|---|---|---|
| BPM(곡 전체 1개) | O | O | O | `server/audio/analyze.py:381` `_tempo_from_beats` → `song_cue_render.py:1328` `bpm=profile.bpm` |
| 비트 시각 | 계산만 | X | X | `analyze.py:352-354` `librosa.beat.beat_track` 결과를 BPM 계산에만 쓰고 `AnalysisResult`(207~215행)에 필드가 없다 |
| 온셋 시각 | O(`onsets_ms`) | X | X | `analyze.py:213` 필드는 있지만 저장된 캐시에는 없다 |
| 다운비트(마디 1박) | X | X | X | `grep -rln "downbeat" server` → 0건 |
| 킥(타악 온셋) | X | X | X | `onset_detect`는 타악 구분이 없는 일반 온셋 검출이다. 분석 라이브러리는 librosa 하나다 |

저장된 캐시 실측 [잰 값]:

```
=== .moai/reports/t499/runs/Club Diver/analysis.json
keys: ['sha256', 'bpm', 'bpm_source', 'sections']
bpm 139.67483108108198 bpm_source measured
=== .moai/reports/t499/runs/Morning/analysis.json
keys: ['sha256', 'bpm', 'bpm_source', 'sections']
bpm 117.45383522727278 bpm_source measured
```

음수 대조 확인: `grep -rln "onset" server`는 생산자(`analyze.py`)와 테스트 3개에서만 걸렸다. 같은 grep 방식으로 `grep -c "bpm" server/audio/analyze.py` → 15건이 나오므로 grep 자체는 정상 동작한다.

**필요한 작업:** (a) 비트 시각과 온셋을 결과·캐시·렌더 경로까지 흘려보내는 배관. 계산은 이미 하고 있다. (b) 다운비트와 킥 검출은 새로 만들어야 한다.

**주의 [추정]:** Rain의 측정 BPM은 76.01이다. 템포 검출에서 흔한 "절반/두 배" 오검출 후보일 수 있다(152 BPM일 가능성). 페이저 속도를 BPM에 묶으면 이 오차가 그대로 화면에 나온다. 이번에는 재지 않았다.

---

## ② 페이저 속도를 곡 BPM에 맞출 수 있는가

**답: 콘솔과 우리 라이브러리 모두 가능하다. 곡 송신 경로만 연결이 안 돼 있다.**

### 2.1 코드 [잰 값]

- **곡 송신 경로는 속도를 보내지 않는다.** `server/web/session.py`의 페이저 빌더는 `At Accel/Decel/Transition/Phase`만 만든다. 카탈로그(`server/design/phaser_catalog.py:21`, `("Wave CM", ("Cyan","Magenta"), "sine", "0 Thru 360")`)에도 속도 필드가 없다.
- **"Wave CM Speed 30 고정"이라는 전제는 코드 근거가 없다.** 이 배차의 전제였지만, `grep -rn "Speed 30\|CM Speed\|At Speed" server`(`server/fx/`·테스트 제외)에서 곡 송신 경로에 걸리는 줄은 0건이다. `Speed 30`은 옛 미리보기 증거(`.moai/reports/t225/evidence/fx_preview_all8.json`)와 다른 SPEC 진행 기록에만 나온다. 콘솔에 저장된 Wave CM 프리셋(4.9)의 실제 속도 값은 **재지 않았다**(빈칸 G1).
- **FX 라이브러리는 속도를 다룬다.** `server/fx/schema.py:132-199`에 `speed`(고정 BPM)와 `speed_master`(1~16, 라이브 마스터 연결)가 있고, 둘은 함께 쓸 수 없다. `server/fx/instantiate.py:561-576`은 `Attribute '<a>' At Speed <v>` 또는 `Attribute '<a>' At SpeedMaster <n>`를 보낸다. 라이브러리 예시로는 `server/fx/library/dimmer.yaml`의 `pulse-beat`(speed 60)과 `pulse-master-sync`(speed_master 1)가 있다.
- **그 라이브러리는 곡 렌더러에 연결돼 있지 않다.** `grep -rnE "^\s*(from server\.fx|import server\.fx)" server`(`server/fx/`·테스트 제외)에서 import하는 파일은 6개다: `orchestrator/tools.py`, `scene/compile.py`, `scene/report.py`, `scene/matching.py`, `looks/movement.py`, `tools/lxseq_fx_e2e.py`. 곡 렌더러 `song_cue_render.py`에는 import가 없고 주석(332행) 한 줄만 있다. 서브에이전트는 "아무 데서도 안 쓴다"고 보고했지만 이 grep으로 바로잡았다. 간접 경로는 하나 있다. 곡 렌더러가 쓰는 `server/looks/songcue.py:10`이 `server/looks/movement.py`의 `MovementPlan`을 가져오고, `movement.py:41`은 `server.fx.instantiate.phaser_lines`를 쓴다. 하지만 t501 실기 송신 명령에는 속도 줄도 Pan/Tilt 페이저 줄도 0건이었다(§0.2 표, 위치는 프리셋 호출로만 바뀐다). 그래서 이 경로는 지금 곡 송신에서 아무 줄도 만들지 않는다고 판단한다 [잰 값: 송신 결과 / 추정: 원인 — 코드 분기는 추적하지 않았다].
- **BPM은 송신 지점까지 와 있다.** `song_cue_render.py:1328`에서 `bpm=profile.bpm`으로 이미 전달된다. 페이저 빌더에 넘기는 연결만 없다.

### 2.2 MA3 공식 문서 [문서]

| 사실 | 원문 | 출처 |
|---|---|---|
| 스피드 마스터는 BPM 단위, 0~225 | "Speed masters have values between 0 and 225 BPM." | [Speed Masters](https://help.malighting.com/grandMA3/2.4/HTML/masters_speed.html) |
| 16개 | "There are 16 different speed masters." | 같은 쪽 |
| 페이저에 걸 수 있다 | "Speed masters can be assigned to sequences, cues, cue parts, attributes, presets, generators, and phasers." | 같은 쪽 |
| 16번은 소리 입력 BPM 마스터 | "Speed master 16 is a BPM master. It is controlled by incoming audio and automatically adopts the detected beats per minute (BPM) as the master speed." | 같은 쪽 |
| 마스터 BPM 설정 문법 | `Master 3.1 At BPM 75` | [BPM Keyword](https://help.malighting.com/grandMA3/2.0/HTML/keyword_bpm.html) |
| 속도 층 BPM 지정 문법 | `At Speed BPM 5` | 같은 쪽 |

**확인하지 못한 것 [추정/미확인]:**
- 페이저를 스피드 마스터에 거는 정확한 문법. 우리 코드는 `At SpeedMaster <n>`를 쓰지만, 이번에 읽은 문서 쪽에서는 그 토큰을 찾지 못했다(빈칸 G2).
- 우리 코드의 `At Speed <v>`가 BPM으로 해석되는지. 문서 예시는 `At Speed BPM 5`처럼 단위 토큰을 붙인다. 단위 없이 보내면 콘솔의 현재 속도 표시 단위를 따를 수 있다(빈칸 G3).

### 2.3 선택지

| 선택지 | 방식 | 장점 | 비용·위험 |
|---|---|---|---|
| A. 페이저마다 고정 BPM | 렌더 시 `speed = 곡 BPM × k`를 계산해 `At Speed` 줄을 보낸다 | 이미 있는 `server/fx` 송신문 재사용. 곡마다 결정적이다 | 프리셋이 곡마다 달라진다(프리셋 풀 소비). 단위 확인(G3) 필요 |
| B. 곡 시작 시 스피드 마스터 설정 | 첫 큐에서 `Master 3.n At BPM <곡 BPM>`, 페이저는 마스터 n에 묶는다 | 프리셋 하나를 모든 곡에서 재사용한다. 현장 조작자가 페이더로 보정할 수 있다 | 연결 문법(G2) 실기 확인 필요. 마스터 번호 배정 규칙 필요 |
| C. 마스터 16(소리 입력 BPM) | 콘솔이 오디오 입력에서 박자를 잡는다 | 코드 작업이 가장 적다 | 오디오 입력 배선이 필요하고, 결과를 우리가 재거나 재현할 수 없다 |
| 배수 | 1/2·1·2배 등 | A·B 위에 얹는다 | 구간 에너지별 배수 규칙이 필요하다 |

**권고 [추정]:** B를 기본으로 한다. 곡 하나에 마스터 한 줄이면 되고, 프리셋을 곡마다 새로 만들지 않아도 된다. 다만 G2 연결 문법을 실기에서 읽기 전용으로 확인하는 일이 착수 조건이다. A는 G2가 막힐 때의 대안이다.

---

## ③ 큐를 어떻게 쪼갤 것인가

### 3.1 지금 재생 방식 [잰 값]

- `server/director/emit.py:51` `PLAYBACK_MODES = ("manual_go", "trig_time")`. 주석에 "timecode mode 와 자동 GO 는 여기 없다"고 적혀 있다. 데이터 모델(`server/design/song_plan.py:61`)에는 `"timecode"`가 있지만 송신 경계에서 거부된다.
- 실기 212·213 큐는 전부 `TRIGTYPE=Time`이다(0.1의 되읽기).
- 원샷(REQ-LDDESIGN-040)은 워크시트 모델까지만 구현돼 있다(`server/concept/worksheet.py:67-227` `OneShotRow`, G13 집계 분리 `server/concept/gates.py:698`). 콘솔용 레인·실행기·송신기는 없다. `session_bridge.py:206,239`에서는 화면 표시용 주석으로만 붙는다.

### 3.2 MA3 큐 트리거 종류 [문서]

[Sequence Sheet](https://help.malighting.com/grandMA3/2.2/HTML/cue_sequence_sheet.html) 원문:
- Time: "The cue is triggered a set time after the previous cue is triggered."
- Sound: "…using a sound as the trigger. Choosing one of 22 different frequency areas…"
- BPM: "This will trigger the cue using the beats in the sound input. This can become useful with several cues triggered by the BPM."

타임코드는 큐 트리거 종류가 아니라 별도 객체다. 내부 시계로도 돌릴 수 있다 [문서, [Timecode](https://help.malighting.com/grandMA3/2.3/HTML/timecode.html)]. 큐 수 상한은 이번에 쪽을 직접 읽어 확인하지 못했다(빈칸 G4).

### 3.3 세 가지 방식 비교

128 BPM, 3분 30초 곡 기준 계산: 1박 = 60/128 = 0.469초, 1마디(4/4) = 1.875초.

| | (1) 구간 안을 마디·박 단위 큐로 쪼갬 | (2) 원샷 레인(REQ-040) | (3) 타임코드 이벤트 |
|---|---|---|---|
| 큐 수 | 마디 단위 210/1.875 ≈ **112개**, 박 단위 ≈ **448개**. 지금은 10~45개(G13) | 시퀀스 큐 수는 그대로. 강조 수만큼 이벤트 추가 | 시퀀스 큐 수는 그대로. 트랙 이벤트 추가 |
| 우리 규칙과의 관계 | REQ-036이 금지한 "마디 수로 기계적 분할" 그 자체. G13 상한 초과 | 이미 설계된 길. 콘솔 송신만 비어 있다 | `emit.py`에서 timecode 거부 해제 필요 |
| 동기 정밀도 | 큐 시각만큼 정확. 다만 오래 쌓이면 어긋남을 고치기 어렵다 | 원샷의 `at` 시각만큼 정확 | 시계 기준으로 정확 |
| 조작자 편집성 | 가장 나쁘다. 큐 시트가 수백 줄이 된다 | 좋다. 강조만 이름 붙은 줄로 남는다 | 중간. 타임코드 창과 큐 시트를 오가야 한다 |
| 작업량 [추정] | 작다(렌더 루프만) | 중간(레인·실행기 송신기 신규) | 크다(재생 모드 신규) |

**권고 [추정]:** 층을 나눈다.
- 룩 전환(구간·프레이즈 큐): §9와 REQ-036을 그대로 지킨다.
- 구간 안 움직임: ②의 BPM 동기 페이저가 맡는다. 큐를 늘리지 않아도 "박자에 맞춰 움직인다"는 요구의 대부분을 채운다.
- 마디·프레이즈 경계 강조(히트, 드롭 진입, 필): 원샷 레인(2)으로 얹는다. 이 강조가 감독이 말한 "다채로움"을 맡는다.
- (1)은 권하지 않는다. (3)은 원샷을 시각에 정확히 맞추는 수단으로, (2) 다음 단계에서 검토한다.

---

## ④ 저장소 정본 §9 · REQ-036과 감독 요구의 충돌 정리

원문 [잰 값, 원문과 대조함]:
- `docs/proposals/song-structure-lighting-standard.md:312` — "발사 지점은 비트마다가 아니라 **프레이즈 단위 4~8마디마다**."
- 같은 파일 313행 — "템포 탭은 스네어·하이햇이 아니라 **킥드럼**에 맞춘다."
- `.moai/specs/SPEC-LDDESIGN-001/spec.md:212`(REQ-036) — 큐 밀도는 구간 층·프레이즈 층·원샷 층 세 층으로 구성하며, "분할 단위(마디 수로 기계적 분할)를 밀도 결정 수단으로 쓰지 않는다."
- 같은 파일 216행(REQ-040) — 원샷은 시퀀스 큐와 별도 레인에 기록하고 G13은 시퀀스 큐만 센다.
- 표준 §10.3(326~327행) — "스트로브는 액센트여야 한다, BPM 카운터가 아니다." 권장 상한은 약 4Hz.

| 조항 | 내용 | 감독 요구가 뜻하는 것 | 판정 | 이유 |
|---|---|---|---|---|
| §9 4~8마디 발사 | 룩 전환 간격 | 박자에 맞는 움직임 | 겉보기 충돌 | 룩 전환 축과 룩 안 움직임 축은 다르다. 다만 Rain Verse 3(26.8초, 76 BPM으로 약 8.5마디)은 §9 상한도 넘는다 |
| REQ-036 기계적 분할 금지 | 마디 수로 큐를 자르지 말 것 | 한 룩 20~30초 정지를 없앨 것 | 충돌 아님(빈칸) | 구간 안에 얼마나 움직여야 하는지는 정해진 바가 없다 |
| REQ-040 원샷 별도 집계 | 원샷은 G13 밖 | 강조를 더 자주 | 충돌 아님 | 원샷을 늘려도 밀도 게이트에 걸리지 않는다. 오히려 해법의 자리다 |
| §10.3 스트로브 | 박마다 번쩍이지 말 것 | "비트에 따라"를 박마다 번쩍임으로 읽으면 충돌 | 좁은 범위의 실제 충돌 가능성 | 감독 뜻이 움직임인지 번쩍임인지 확인이 필요하다 |
| (없음) | 움직임 속도와 BPM의 관계 | 움직임이 박자를 따를 것 | **진짜 빈칸** | 표준·LDDESIGN·LDRENDER 어디에도 없다. LDRENDER는 페이저가 송신되는지만 잰다 |

---

## ⑤ 측정 가능한 합격 기준 초안 — 「감독 확정 대기」

> 아래 숫자는 전부 **초안**이다. 감독이 확정하기 전에는 SPEC에 옮기지 않는다. 기준선은 이번에 잰 212·213 값이다.

| 번호 | 기준(초안) | 재는 법 | 기준선 [잰 값] | 초안 목표 |
|---|---|---|---|---|
| R1 | **점등 구간 큐마다 움직임이 있다** | 점등된 구간 큐 가운데 페이저가 1개 이상 실린 비율 | Rain 212: 0/13 / Club Diver 213: 11/14(같은 Wave CM이 9회) | 100%, 그리고 같은 페이저 연속 반복 상한(감독 결정) |
| R2 | **움직임이 곡 BPM에 묶인다** | 송신된 페이저 중 속도가 곡 BPM의 {¼, ½, 1, 2}배로 지정되거나 곡 BPM 마스터에 묶인 비율 | 0%(속도 줄 0건) | 90% 이상 |
| R3 | **변화 없는 시간의 상한** | 큐·원샷·타임코드 이벤트 중 어떤 것도 없는 가장 긴 구간(마디 수). 단, R2를 채운 페이저가 도는 시간은 "변화 있음"으로 칠지 감독 결정 | 212 최대 28.5초(76 BPM 기준 약 9마디) / 213 최대 17.1초(139.7 BPM 기준 약 10마디) | 8마디 이하 |
| R4 | **강조 밀도** | Chorus·Drop 구간에서 4마디당 원샷 강조 수 | 0(원샷 송신기 없음) | 4마디당 1개 이상 |
| R5 | **BPM 오검출 가드** | 분석 BPM을 사람이 잰 참값과 비교해 절반·두 배 오류가 있는 곡 수 | 안 잼(G5) | 0곡 |
| R6 | **사람 판정** | 실기에서 감독 육안 판정(AC-LDRENDER-016 형식) | 1~2점 | 3점 이상 |

R1·R2는 송신 명령만 읽으면 오프라인으로 잴 수 있다. R3·R4는 렌더 결과의 시각표로, R5는 참값 표가 있어야 잰다. R6은 기계로 대체할 수 없다.

---

## 감독이 정할 것

1. "리듬과 비트에 따라 빠르고 다채롭게"는 무엇에 가까운가: (가) 룩을 더 자주 바꾼다, (나) 한 룩 안의 움직임이 박자를 따른다, (다) 둘 다.
2. (가)가 포함된다면: §9의 "4~8마디마다 룩 전환"을 올릴 것인가, 아니면 원샷 강조로만 채울 것인가.
3. 박자 표현에 스트로브·디머 번쩍임을 포함할 것인가. 포함하면 §10.3("BPM 카운터가 아니다", 4Hz 상한)에 예외를 둬야 한다.
4. 속도 기준: 곡 분석 BPM(재현 가능)과 콘솔 소리 입력 BPM(현장 적응, 재현 불가) 중 무엇을 쓸 것인가.
5. ⑤ R1~R6의 목표 숫자와, R3에서 BPM 동기 페이저를 "변화"로 칠지 여부.
6. 범위: SPEC-LDRENDER-001을 연장할 것인가, 새 SPEC(리듬)을 열 것인가. LDRENDER-001은 이미 구간별 밝기(P6)를 후속 SPEC으로 넘긴 선례가 있다.

---

## 안 잰 것(빈칸)

| 번호 | 내용 | 이유 | 메우는 법 |
|---|---|---|---|
| G1 | 콘솔에 저장된 페이저 프리셋(4.9~4.11, 21.7~21.8)의 실제 속도 값 | 이번 카드는 읽기 전용 문서 조사로 한정했다 | 콘솔 읽기 전용 `props` 조회 |
| G2 | 페이저를 스피드 마스터에 거는 정확한 문법 | 읽은 문서 쪽에 토큰이 없었다 | 공식 문서 추가 탐색 또는 실기 읽기 전용 확인 |
| G3 | 단위 없는 `At Speed <v>`의 단위 해석 | 문서 예시는 `At Speed BPM <v>`다 | 실기 확인 |
| G4 | 시퀀스당 큐 수·실행기 수 상한 | 해당 쪽을 직접 읽지 않았다(서브에이전트는 검색 요약만 인용) | 공식 문서 쪽 직접 확인 |
| G5 | BPM 검출 정확도(절반·두 배 오류) | 참값 표가 없다. Rain 76 BPM이 의심 후보다 | 8곡 참값 대조 |
| G6 | `beat_track`의 비트 시각 품질 | 오디오를 다시 분석하지 않았다 | 곡 몇 개로 비트 시각을 뽑아 육안·청취 대조 |
| G7 | `looks/movement.py` 경로가 곡 송신에서 왜 줄을 만들지 않는지 | 송신 결과(0줄)만 쟀고 코드 분기는 추적하지 않았다 | `song_cue_render.py`에서 `MovementPlan` 사용처 추적 |
| G8 | R1 기준선 11/14의 큐 단위 대응 | 프리셋 호출 수(11)와 큐 수(14)만 셌고 큐별로 짝짓지 않았다 | 승인 요청 원문을 큐 경계로 나눠 집계 |

## 증거 목록

- `.moai/reports/t502/evidence/hold_durations.py`, `hold_durations.txt` — 0.1 유지 시간 계산
- `.moai/reports/t502/evidence/t501_postwrite_cue_props.txt` — t501 실기 되읽기 사본
- `.moai/reports/t502/evidence/t501_{clubdiver_213,rain_212}_approval_request.txt` — t501이 콘솔에 보낸 명령 원문 사본
- `.moai/reports/t502/verdict.md` — 측정 명령·출력·등급 정리
