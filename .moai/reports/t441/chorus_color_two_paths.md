# t441 — 구간별 주색 결정, 두 조립 경로 대조 (SPEC-LDDESIGN-001 REQ-003)

명령: `uv run pytest server/tests/test_chorus_color_two_paths_t441.py -q`

카드 t439(`chorus_color_two_paths_t439.md`)는 두 경로가 서로 다른 색 표현 공간(이름 팔레트 vs 룩 라이브러리 RGB)을 쓴다는 것을 실측했다. 이 카드는 그 간극을 메운다 — 경로 B(`prepare_songcue`)가 세션의 Q2(팔레트)·Q2B(색 운용) 답을 `interview_records` 로 받아, 경로 A와 **같은 함수**(`section_palette._section_palette_choice`)로 정한 주색을 이미 고른 룩의 ColorRGB 위에 덮는다.

곡: Intro 1 + 후렴류 3회(라벨 Chorus/Verse/Drop/Chorus — Drop 은 §6 「chorus · drop」 행이라 Chorus 와 같은 **역할**). 팔레트 답: `블루` (표준 팔레트 8번 Blue, RGB (5, 20, 100)).

## color_usage = modulate

| 구간 | 역할 | 경로 A 주색 | 경로 B ColorRGB | 일치 |
|---|---|---|---|---|
| A:Intro/B:Intro | intro | 블루 | (5, 20, 100) | PASS |
| A:Chorus/B:Chorus | chorus | 블루 | (5, 20, 100) | PASS |
| A:Verse/B:Verse | verse | 블루 | (5, 20, 100) | PASS |
| A:Chorus/B:Drop | chorus | 블루 | (5, 20, 100) | PASS |
| A:Chorus/B:Chorus | chorus | 블루 | (5, 20, 100) | PASS |

## color_usage = per_chorus

| 구간 | 역할 | 경로 A 주색 | 경로 B ColorRGB | 일치 |
|---|---|---|---|---|
| A:Intro/B:Intro | intro | 블루 | (5, 20, 100) | PASS |
| A:Chorus/B:Chorus | chorus | 블루 | (5, 20, 100) | PASS |
| A:Verse/B:Verse | verse | 블루 | (5, 20, 100) | PASS |
| A:Chorus/B:Drop | chorus | 블루 | (5, 20, 100) | PASS |
| A:Chorus/B:Chorus | chorus | 블루 | (5, 20, 100) | PASS |

## 대조군

- 기록 없음(`records=None`) / Q2 미답 → 경로 B 선택 변경 없음 (`TestRecordsAbsentIsByteIdenticalToToday` — PASS), 후렴 룩은 여전히 `edm-drop-crimson` (100,0,15).
- 날조 대조군(`resolve_color_name` 무력화) → 경로 B 는 crimson 그대로, 경로 A 는 여전히 블루 — 교차 확인이 실제로 이 코드에 의존함을 보인다 (`TestFabricatedControl` — PASS).

## 안 잰 것

- 보조색(`colors[1]`) 은 경로 B 로 옮기지 않는다 — 경로 A 의 콘솔 명령 생성기(`_song_color_value_lines`)도 주색 한 줄만 내므로 대칭이다. 회차 사다리(모듈레이트 회전·per_chorus 액센트)는 전부 이 축에 살아서 이 표에는 드러나지 않는다 — "메인 컬러 중심" 불변식(카드 t409)이 주색을 역할·회차·색 운용과 무관하게 고정하기 때문이다.
- 실기 콘솔 0회 — 가짜 실행 포트(`_RecordingPort`)·가짜 상태 포트 (`_SongCueStatePort`) 위에서만 돈다(이 SPEC 의 다른 회차들과 같은 관행).
