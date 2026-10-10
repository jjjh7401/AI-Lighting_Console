# SPEC-LDBARMAP-001 — 리서치 (plan-phase 코드베이스 실측)

성격: 이 plan-phase가 직접 실행한 명령과 그 출력. 추론이 아니라 실측만 기록한다 — `lesson-a-code-reading-inference-is-not-a-measurement.md`(이 저장소 메모리)가 적은 "코드 판독은 실측이 아니다"를 따른다.

## 1. 다운비트 생산자 — 0건 재확인

```
$ grep -n "downbeat" -r server | wc -l
0
```

`server/` 트리 전체에 "downbeat" 문자열이 등장하는 곳이 없다. `SPEC-LDRHYTHM-001` §1이 2026-10-03(t502)·2026-10-05(이 plan-phase의 선행 SPEC들)에 각각 재확인한 것과 같은 결과다 — 2026-10-10 이 plan-phase 시점에도 공백이 그대로다.

## 2. `server/audio/analyze.py` — 비트 시각의 흐름

```
$ grep -n "beat_times\|beat_track\|_tempo_from_beats\|onsets_ms\|class AnalysisResult" server/audio/analyze.py | head -60
207:class AnalysisResult:
213:    onsets_ms: tuple[int, ...]
352:        beat_times = librosa.beat.beat_track(
361:    bpm, confidence = _tempo_from_beats(numpy, beat_times)
375:        onsets_ms=tuple(int(round(t * 1000.0)) for t in onset_times),
381:def _tempo_from_beats(numpy, beat_times) -> tuple[float | None, float]:
```

`Read` 도구로 206~424행을 직접 읽어 확인한 사실:

- `AnalysisResult`(`:207-215`)의 필드는 정확히 `bpm, bpm_confidence, boundaries_ms, onsets_ms, rms_curve, d_candidates` 여섯 개다. 박 시각(`beat_times`)이나 다운비트를 담을 필드가 없다.
- `analyze()`(`:294-378`) 본문에서 `beat_times`는 `librosa.beat.beat_track(...)`(`:352-354`)로 계산된 뒤 `_tempo_from_beats(numpy, beat_times)`(`:361`) 호출 **한 곳**에만 전달되고, 그 뒤 다시 참조되지 않는다 — `return AnalysisResult(...)`(`:371-378`)에 `beat_times`가 포함되지 않는다.
- `_tempo_from_beats`(`:381-399`)는 박 간격의 **중앙값**으로 BPM을 내고(독스트링: "`beat_track`이 돌려주는 템포 추정치 대신 박 간격의 중앙값을 쓴다"), 흔들림(표준편차/중앙값)을 `confidence`로 환산한다. 반환값은 `(bpm, confidence)` 튜플뿐 — 박 시각 자체는 돌려주지 않는다.
- `onsets_ms`(`:213`, 채워지는 곳 `:375`)는 `AnalysisResult`의 필드로 **존재한다** — `librosa.onset.onset_detect(...)`(`:355-357`)의 결과가 밀리초로 변환되어 담긴다.

**결론**: 비트 시각은 계산되지만 버려진다(BPM 계산의 중간값일 뿐). 온셋은 반환값에는 있지만, 아래 §3에서 보듯 캐시에는 저장되지 않는다.

## 3. 캐시 저장 키 — onsets_ms도 저장되지 않는다

```
$ cat .moai/reports/t475/run3/analysis.json | head -5
{
 "sha256": "c3b78bbb739f816879a33d508404c137643e01bb77af27b26e6a8514fe085b70",
 "bpm": 76.01351351351367,
 "bpm_source": "measured",
 "sections": [
$ cat .moai/reports/t475/run3/analysis.json | python3 -c "import json,sys; print(list(json.load(sys.stdin).keys()))"
['sha256', 'bpm', 'bpm_source', 'sections']
```

캐시 JSON의 최상위 키는 정확히 네 개 — `sha256`, `bpm`, `bpm_source`, `sections`. `onsets_ms`도, 박 시각도, 다운비트도 저장되지 않는다. `SPEC-LDRHYTHM-001` §1이 인용한 같은 사실(`.moai/reports/t499/runs/Club Diver/analysis.json` 대상)을 이 SPEC은 다른 파일(`t475/run3`)로 재확인했다 — 저장 형태가 바뀌지 않았음을 확인.

## 4. `_HOP_LENGTH`/`_FRAME_LENGTH` — 허용오차 산출 근거

```
$ grep -n "_HOP_LENGTH\s*=\|_FRAME_LENGTH\s*=" server/audio/analyze.py
34:_HOP_LENGTH = 512
35:_FRAME_LENGTH = 2048
```

프레임 해상도는 `512 * 1000 / sample_rate` ms — 44.1kHz면 약 11.6ms, 48kHz면 약 10.7ms. acceptance.md의 다운비트 허용오차(±60ms)는 이 프레임 해상도보다 넉넉하고(약 5~6배), 1박(0.534초)보다는 훨씬 촘촘하다 — 두 극단 사이의 보수적인 값으로 채택했다.

## 5. 타임라인 저장소 세 메커니즘 (열린 결정 0의 옵션 A 근거)

```
$ grep -n "class SongTimelineStore\|class TimelineDraftHistory\|_draft_history.record" server/web/session.py | head -10
3486:class SongTimelineStore:
8505:        self._draft_history.record(timeline)
$ grep -rn "class TimelineDraftHistory" server/web/
server/web/timeline_draft.py:29:class TimelineDraftHistory:
$ grep -n "class SongTimelineLibrary" server/web/timeline_library.py
48:class SongTimelineLibrary:
```

`SPEC-LDBEAT-001` spec.md REQ-LDBEAT-006이 인용한 줄 번호 중 `SongTimelineStore`(`session.py:3486`)와 `SongTimelineLibrary`(`timeline_library.py:48`)는 이 plan-phase 재확인으로 그대로 일치한다. `TimelineDraftHistory` 클래스 정의는 `server/web/timeline_draft.py:29`에 있고(LDBEAT spec.md가 인용한 "`server/web/timeline_draft.py`, `session.py:3831` `self._draft_history`" 서술과 부합 — 클래스 정의와 인스턴스 속성이 각각 다른 파일/줄에 있음), 레코드 호출은 `session.py:8505`에서 재확인했다.

## 6. SPEC-LDARRANGE-001 부재 확인

```
$ ls .moai/specs/ | grep -i ARRANGE
(출력 없음, exit 1)
```

`SPEC-LDARRANGE-001`은 아직 `.moai/specs/`에 존재하지 않는다 — `reports/ldbeat-feasibility-roadmap-20261010.md` §SPEC 진행안이 "순서 3, 없음"으로 적은 것과 일치.

## 7. SPEC ID 유일성 확인

```
$ ls .moai/specs/
(69개 디렉터리 나열 — SPEC-LDBARMAP-001 없음)
```

기존 69개 SPEC 중 `SPEC-LDBARMAP-001`과 겹치는 ID는 없다.

## 8. 정답지(지도 보고서) 요약

`reports/loveattack-music-map-20261006.md`를 전문 읽었다. 핵심 수치(이 문서 §한눈에보기·§3·부록 A에서 직접 인용):

- BPM 112.35(확신 0.967), 절반 격자 정합 0.34 vs 112.35 격자 0.65(우연 수준 0.20) — 절반 BPM이 틀렸음을 보이는 근거.
- 다운비트 위상 1 채택 — 화성 변화·저역 도약·후렴 히트 세 근거가 일치(§3 표).
- 빌드업: 14~17마디·42~45마디(각 4마디 연속 상승). 큰 히트(후렴 진입): 18·46마디(저역 4.4배). 킥 멈춤: 33·61·82마디(저역 0.23~0.25배). 드롭 후보(평론 대조, [추정] 등급): 63~66마디.
- 앱 분석 경로(기존 `analyze()`)와의 비교(§4): 구간 개수는 맞지만 경계가 실제 마디보다 0.41~0.82초(약 한 박) 앞서고, 빌드업/브릿지를 "Verse"로 뭉뚱그린다 — 이 SPEC이 메우는 공백이 지도 보고서 자체에서도 재확인된다.

## 9. SPEC-LDRHYTHM-001 REQ-LDRHYTHM-012(a) — 받는 후보 원문

spec.md §3.6에서 인용: 「(a) 비트·다운비트·킥 검출 — 지금은 BPM 숫자 하나만 렌더러에 닿는다(§1 인용, `analyze.py` 비트 시각 미저장·다운비트 생산자 0건, 이 plan-phase 재확인)」— 이 문장이 이 SPEC(LDBARMAP-001)이 실제로 설계·검증하는 작업이다. REQ-LDRHYTHM-012는 비요구사항 참고 각주로 "이 plan-phase 자신은 네 항목 중 무엇을 실제로 구현할지 확정하지 않는다"고 명시했으므로, 이 SPEC을 새로 만드는 것이 그 비확정 상태를 해소하는 올바른 절차다.

## 10. SPEC-LDBEAT-001 REQ-LDBEAT-006 — 저장 인터페이스 선례 원문

spec.md에서 인용: 「격자 데이터를 기존 `timeline` 사전의 새 키(예: `beat_grid`)로 심으면 (b)의 되돌리기가 코드 추가 없이 격자 편집도 덮는다(전체-사전 스냅샷 방식 때문) — 이 임베드 방식을 M2의 권고 기본 설계로 삼되, 독립 저장소가 필요한지는 M2에서 director와 함께 확정한다.」 이 SPEC의 열린 결정 0 옵션 A는 이 선례를 그대로 인용한다.

## 11. REQ-LDBARMAP-006 재설계 — 고정 격자의 두 결함 + 부호검정 설계 근거(카드 t547, 2026-10-10)

이 plan-phase가 직접 실행한 세 탐사 스크립트(`.moai/reports/t547/probe_songs.py`·`probe_sign.py`·`probe_synth.py`)의 출력을 그대로 인용한다 — 추론이 아니라 실측이다(`lesson-a-code-reading-inference-is-not-a-measurement.md`).

### 11.1 고정 격자의 결함 1 — BPM 오차에 취약

```
$ cat .moai/reports/t547/probe_songs.txt   # LOVE ATTACK 행만 인용
LOVE ATTACK.mp3         112.347  112.002 |   112.347  0.29/ 0.29/ 0.31 |   224.004  0.61/ 0.42/ 0.82 |   0.52     0.87
```

같은 곡(LOVE ATTACK)을 중앙값 BPM(112.347)과 t546 회귀 BPM(112.002)으로 각각 고정 격자를 깔아 비교하면 grid-lock 비율(raw 열)이 0.29→0.61로 두 배 이상 달라진다 — BPM 추정 오차 0.3%가 곡 전체에 걸쳐 격자를 약 1박 어긋나게 만들기 때문이다. 옛 중앙값 BPM에서는 이 검사(`_check_bpm_half_double`)가 10곡 전부에서 한 번도 발동하지 못했다 — 사실상 맹목이었다.

### 11.2 고정 격자의 결함 2 — 밀도 편향(거짓 두 배)

같은 표(adopt@med vs adopt@reg 열): 회귀 BPM(정확)으로 바꾸자 더 촘촘한 두 배 격자가 구조적으로 더 높은 비율을 내(8분음표 하이햇이 걸림) 10곡 중 3곡이 거짓 두 배로 뒤집힌다 — LOVE ATTACK 112.347→224.004(정답 112.35), Let's Dance 119.681→240.061, LoveMe 99.384→199.988. "온셋이 더 많이 걸린다"는 템포가 두 배라는 증거가 아니다.

### 11.3 부호검정 설계 — 추정 비트 격자 자체를 기준틀로

```
$ cat .moai/reports/t547/probe_sign.txt   # 머리줄 + LOVE ATTACK·Ice cream 행
song                      n  w_mid     p_mid |  w_odd     p_two
LOVE ATTACK.mp3         326   0.16  2.34e-38 |   0.58  5.98e-02
Ice cream.mp3           122   0.36  9.37e-04 |   0.59  2.00e-01
```

`probe_sign.py`는 고정 격자 대신 추정 박 i와 i+1 사이의 중간점(mid_i)·박 자신(on_i)의 온셋 강도를 짝지어 단측 부호검정(H1: 박이 중간점보다 강하다, α=0.01)을 적용한다. 실제 10곡 전부 p_mid<0.01(최대 9.37e-04, Ice cream n=122)로 keep — 거짓 두 배 3건(LOVE ATTACK·Let's Dance·LoveMe)이 사라진다.

### 11.4 합성 대조군 — adopt_double·keep·ambiguous 세 갈래 재현

```
$ cat .moai/reports/t547/probe_synth.txt   # 5개 케이스만 인용
case                            tracked  w_mid     p_mid |  w_odd     p_two
112 박+8분 하이햇 0.3                 112.00   0.24  8.98e-12 |   0.41  1.46e-01
112 박+8분 하이햇 0.7                 112.00   0.46  1.95e-01 |   0.48  7.41e-01
224 같은 세기(참 224)                 112.00   0.54  8.45e-01 |   0.39  5.98e-02
240 같은 세기(참 240)                 120.00   0.62  9.99e-01 |   0.53  5.94e-01
56 박+8분 0.3(참 56)                112.00   0.00  4.28e-50 |   0.15  4.11e-11
```

`probe_synth.py`는 `probe_sign.py`와 같은 검정을 알려진 정답 템포의 합성 클릭 트랙에 적용해 설계의 세 판정 경로를 전부 재현한다 — 참 224/240(112/120으로 추정) 균등 세기 클릭은 w_mid≥0.54·p_mid≥0.845로 adopt_double, 112+8분 하이햇(세기 0.3)은 p_mid=8.98e-12로 keep, 112+8분 하이햇(세기 0.7, 강함)은 w_mid=0.46·p_mid=0.195(≥α이지만 w_mid<0.5)로 ambiguous.

### 11.5 절반 후보의 홀짝 혼동(설계가 자동 채택하지 않는 이유)

§11.3·§11.4의 `p_two` 열: 짝수/홀수 추정 박 사이의 홀짝 부호검정은 실제 10곡 중 6곡(`probe_sign.txt` 전체 10행, 이 문서에는 2행만 인용)에서 α=0.01 유의하고, 합성 대조군의 참 절반 케이스(56 BPM+8분, 112로 추정: p_two=4.11e-11)와 정상 112 킥/스네어+8분(p_two=1.83e-04, `probe_synth.txt` 전체 8행 중 1행)도 둘 다 유의하다 — 이 검정은 "트래커가 두 배로 잡음"과 "정상곡의 킥/스네어 악센트"를 가르지 못한다. 그래서 REQ-LDBARMAP-006은 절반을 이 판정으로 자동 채택하지 않고, 사람 확인 카드(별도, 범위 밖)로 넘긴다.
