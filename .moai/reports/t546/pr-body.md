## 무엇을 고쳤나 (카드 t546, 판정 근거 t536 `verdict.md`)

`analyze()` 가 내는 BPM 이 hop 512 격자(44.1kHz 에서 11.6ms 칸) 값으로만 나왔다. 박 간격의 **중앙값**을 썼기 때문이다. 그래서 참 112 BPM 이 112.347 로 나왔다. 이 값은 감독 확인 카드에 그대로 뜨고, 받으면 그대로 확정된다. 그 BPM 으로 큐를 8마디씩 쪼개면 8마디째에 54~117ms 밀렸다.

이제 `analyze()` 는 `_tempo_from_beat_regression` 을 쓴다.

- 박에 번호를 매겨 박 시각에 직선을 맞추고, 그 기울기로 BPM 을 낸다.
- 잔차 표준편차가 박 길이의 **10%** 를 넘으면 회귀를 버리고 지금의 중앙값을 낸다. 반 박 자리에 박이 하나 끼어 그 뒤 번호가 밀린 경우다.
- 확신(`bpm_confidence`)의 계산과 의미는 그대로다.

## 🔴 (1) 두 경로의 BPM 이 이제 다를 수 있다

- `analyze()`(확인 카드로 가는 생산 경로)는 회귀값을 쓴다. 예: LOVE ATTACK **112.002**.
- `bar_map.detect_beat_grid` 는 `_tempo_from_beats`(중앙값)를 **그대로** 쓴다. 예: LOVE ATTACK **112.347**.

이유: `detect_beat_grid` 뒤의 절반/두 배 검사(REQ-LDBARMAP-006)에 정확한 BPM 을 주면 3곡이 두 배로 뒤집힌다(LOVE ATTACK 112→224, Let's Dance 120→240, LoveMe 100→200). 옛 BPM 에서는 곡 전체에 깐 고정 격자가 약 한 박 밀려 정합도가 우연 수준(0.27~0.33)이었다. 그래서 이 검사는 10곡 모두에서 한 번도 발동하지 않았다. 재보정은 카드 **t547** 로 뺐다. `detect_beat_grid` 를 부르는 생산 코드는 0곳이다(`tools/barmap` 과 시험만 부른다).

`TestTwoPathsSplit` 시험이 이 갈림을 고정한다. `_tempo_from_beats` 는 112.347 을 그대로 내고, `analyze()` 는 클릭 트랙에서 112.0 을 낸다.

## 🔴 (2) CI 에서 skip 되는 로컬 전용 실곡 시험 — 로컬 실행 결과

`server/tests/test_audio_bar_map.py::test_detect_beat_grid_real_love_attack_matches_fixture_and_ac016` 은 원곡 mp3 가 있을 때만 돈다. CI 에는 원곡이 없어 skip 된다.

- A 적용 전(회귀를 `_tempo_from_beats` 에 바로 넣었을 때): **FAILED** — `Obtained: 224.0038… Expected: 112.35 ± 0.56`
- A 적용 뒤(이 PR): **1 passed** (`.moai/reports/t546/local_real_song.txt`)

## 🔴 (3) 컷 0.10 의 근거는 합성 박 목록이다

`.moai/reports/t546/cut_basis.py`·`cut_basis.txt` 로 쟀다. 실제 곡은 쓰지 않았다.

- 깨끗한 박: hop 512 양자화 + 사람 연주 흔들림 σ 0~15ms, 60~200 BPM 에서 잔차는 박의 **최대 5.0%** 였다.
- 번호 밀림: 반 박 자리에 박 하나를 넣고, 위치를 곡의 5~95% 로, 템포를 76·112·160 으로 바꿔 쟀다. 잔차는 **최소 20.1%** 였다.
- 0.10 은 두 값의 기하 중간이다. t536 의 실제 10곡은 대조로만 썼다.
- 한계: 템포가 곡 중간에 바뀌는 곡은 재지 않았다. 그런 곡은 잔차가 커져 중앙값으로 돌아가는 쪽으로만 틀린다.

## 증거

| 항목 | 명령 | 결과 |
|---|---|---|
| 재현(고치기 전 함수) | `uv run pytest server/tests/test_audio_tempo_t546.py`(첫 판, 회귀를 `_tempo_from_beats` 로 시험) | `6 failed, 5 passed` — 112→112.347, 128.5→129.199, 160→161.499 (`red.txt`) |
| 고치기 전/뒤 `analyze()` | `uv run python .moai/reports/t546/red_analyze.py` | 클릭 112/120/128.5/160 → before 112.347/120.185/129.199/161.499, after 111.997/119.997/128.500/160.010 (`red_analyze.txt`) |
| 10곡 전후 | `uv run python .moai/reports/t546/d_compare.py` | 대조군 D(온셋 접기, 박 추적기 안 씀)와의 차가 6곡에서 줄었다(최대 1.500→0.004). 4곡은 폴백으로 같고, 나빠진 곡은 0이다. bar_map 의 채택값은 10곡 모두 전과 같다 (`d_compare.txt`) |
| 관련 시험 | `uv run pytest server/tests/ tools/barmap -k "audio or bar_map or barmap or tempo or bpm or song or analy"` | `1309 passed, 2 skipped`(skip 2개는 무관한 기존 DESCOPE 갈래) (`green.txt`) |
| 린트 | `ruff check`·`ruff format` | 통과 |

## 112.347 을 박은 7파일 — 줄마다 읽은 결과, 고칠 것 0

- `tools/barmap/ground_truth.py:21` `TARGET_BPM = 112.35` — 지도 보고서·acceptance 의 문서 상수다(정답지 격자). 생산 함수의 출력이 아니다.
- `server/tests/test_audio_bar_map_store.py:40,79,138` · `test_session_bar_map_store.py:49` — `build_bar_map_payload(bpm=112.35)` 에 넣는 **입력 자료**다.
- `server/tests/test_audio_bar_map.py:170` — 부록 A 간격을 만드는 입력 자료다.
- `test_audio_bar_map.py:327` · `fixtures/love_attack_beat_grid.json` — `detect_beat_grid` 가 낸 값의 기록이다. bar_map 은 중앙값 그대로라 맞는 기록이다.
- `test_audio_bar_map.py:390` — 로컬 실곡 시험이다. 위 (2) 에서 통과했다.
- `tools/barmap/candidates.py:73,252` — `_tempo_from_beats` 를 읽기만 한다. 중앙값 그대로라 동작이 같다.

## 이 리그·곡에만 맞는 것

없다. 콘솔 0, 장비 무관. 10곡 대조는 대조일 뿐 상수를 고르는 데 쓰지 않았다.

## 안 잰 것

- 사람이 잰 BPM 과의 대조. D 는 클릭 4개에서만 참값으로 검증했다.
- 10곡 밖의 곡과 템포가 바뀌는 곡.
- 확인 카드에 실제로 뜨는 문구를 화면에서 보지는 않았다(`{bpm:g}` → 112.002 처럼 소수가 뜬다).

🗿 MoAI
