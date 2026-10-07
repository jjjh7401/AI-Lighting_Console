# t520 판정서 — SPEC-LDRHYTHM-001 M2 묶음 1 준비 (LOVE ATTACK 0~25마디 손 시연 명령 파일)

- 카드: t520 · 브랜치 `WT-m2-batch1` · 기준 `origin/main` `53a2bd9b`(t516 #561 머지) · 작성 2026-10-07
- 범위: 대본 0~25마디 행 → t516에서 확인된 수단으로 명령 파일 → 가짜 콘솔 → 실기 전부-거절 → AC-012 리허설 → **승인 요청까지**.
- 🔴 실기 쓰기 0. 이 카드에서 콘솔에 보낸 것은 읽기(`run0`)와 전부-거절 1회(승인 요청 5묶음, 모두 거절)뿐이다. `server/` 수정 0, 음원 커밋 0.

## 요약

| 항목 | 결과 | 근거 |
|---|---|---|
| 빈 번호 | 시퀀스 250·251·252, 타임코드 22 모두 비어 있음 | `run0_readonly.txt`(`path segment not found`) |
| 스피드 마스터 15 | `NORMEDVALUE 69` — t516 v1 뒤 값 그대로 | `run0_readonly.txt` |
| 다중 디머 기구 | Spiider 521 서브픽스처 **3개**, Aura XB 301·311 서브픽스처 1개(201은 t516에서 1개) | `run0_readonly.txt` |
| 쓰기 승인 파일 | `approval_m2a_batch1.txt` 579줄, sha256 `ef67a55c9eb17c7ef7d39c7f66fcfca0ef9f1964d3c6f963ce4c60698380f042` | §6 |
| 재생 승인 파일 | `approval_m2a_play.txt` 4줄, sha256 `b7a022403aff28f3f00ffb7f1cac5761765f270c1b39d4f694b219070bf1e22b` | §6 |
| 가짜 콘솔 | 쓰기 5묶음 끝까지, 트랙 NO 1→250·NO 2→251, 이벤트 7·15 · 재생 2묶음 끝까지 | `rehearse/`, `play_rehearse/` |
| 실기 전부-거절(쓰기 판) | preflight `responder_ok` · 승인 요청 5, 승인 0 · 감사 로그 `rejected` 5행, `executed`는 읽기만 · 요청 문면 = 리허설 `True` | `live_denyall/` |
| AC-012 리허설 | 쓰기 579줄 **PASS** · 재생 4줄 **PASS** · 양성 대조(승인 파일 100번째 줄 삭제) **FAIL** | `rehearse_approval_vs_sent.txt`, `play_rehearse_approval_vs_sent.txt`, `control_line_removed_result.txt` |
| BACK 201~212 | 대본대로 넣었다. **무대 화면에서 안 보이는 문제는 미해결(t519)** — 역광 펄스가 이 묶음 박자 층의 큰 몫이라 감독이 보는 그림이 비어 보일 수 있다 | t516 §4-14 |

> **v2(2026-10-07)가 이 판을 대신한다 — §11.** 감독 결정으로 BACK 위치(Pan 180 · Tilt 80)를 장면 시퀀스 모든 큐에 넣었다. 실행에 쓰는 파일은 `approval_m2a_batch1_v2.txt`(586줄, sha256 `7438fc88…`)와 `live_denyall_v2`다. 아래 §1~§10은 v1 기록이고, 차이는 §11에 적었다.

## 1. 쓴 수단 — t516 요약표에서 확인된 것만

| 대본 종류 | 콘솔 수단 | 근거 |
|---|---|---|
| 킥/스네어 펄스 · 체이스 한 칸 | 2단계 디머 페이저 → `At Phase 0` → `At Measure <박>` → `At SpeedMaster 15` | t516 v3 L2(SpeedMaster 결속) · v4 B3/B4(Measure 4·1) |
| 움직임 효과 | 절대값 2단계 페이저, **단계마다 Pan·Tilt를 같이** 넣는다 | t516 v5 E1(246) — 기울인 기준 위 Pan 흔들림 확인 · v4 A2/A3 Tilt 움직임 |
| 색/위치 한 단계 · 강조 | 타임코드 이벤트 `Go+`가 장면 시퀀스의 다음 큐를 연다 | t506 v3 · t516 v1 ④(트랙 둘) |
| 선택 + 값 | `Fixture 목록 ; Attribute …` 한 줄 | t516 §4-4 `line_shapes.txt` |
| 다중 디머 | 서브픽스처까지 적는다: `201 + 201.1`, `521 + 521.1 + 521.2 + 521.3` | 이 카드 `run0` · t516 v5 F1(301·301.1 켜짐) |
| 큐 이름 | 점 없이(`Sweep Half`) | t516 §4-1(`Measure 0.5` → `Measure 05`) |
| 이름 | `'LOVE ATTACK - RHYTHM M2a SCENE'` · `'… RHYTHM'` · `'… TC'` — `Set … Property 'Name'` | 감독 규칙, t513 §7-2 |

## 2. 설계

**시퀀스 두 개, 타임코드 하나에 트랙 둘.** 트랙 1 = 장면 250(7큐), 트랙 2 = 리듬 251(15큐). 트랙 둘은 t516 v1에서 기계로 PASS했다. 강조(BLIND)는 장면 시퀀스에 넣었다. 트랙을 셋 이상으로 늘리는 것은 안 잰 일이라 피했다.

**속성마다 주인을 하나로 정했다.** 같은 속성을 두 시퀀스가 함께 잡을 때 어느 쪽이 이기는지는 안 잰 것이기 때문이다(t516 v1 ⑤는 불이 안 켜져 판정 못 함).

| 시퀀스 | 맡는 속성 |
|---|---|
| 장면 250 | WASH 디머·색 · FOH 디머 · BACK·SIDE·무빙 **색** · 무빙 **디머** · BLIND 디머 |
| 리듬 251 | BACK **디머** · SIDE **디머** · 무빙 **Pan/Tilt** |

**리듬 큐는 매번 맡은 속성 전부를 두 단계로 다시 적는다.** 앞 큐의 페이저 단계 값이 트래킹으로 남아 움직임이 멈추지 않는 일을 막으려는 것이다. 멈춘 상태도 "두 단계 값이 같은 페이저"로 적는다(예: BACK 30/30). 이 방식이 트래킹을 실제로 끊는지는 안 잰 것이다(§5).

**타임코드 시각 = 음악 시각 + 3초(LEAD).** 시작 장면과 첫 히트를 타임코드 0초에 두지 않으려고 앞에 3초를 비웠다. 길이 62초, `AutoStop 0`(t516 v1과 같다).

**스피드 마스터는 다시 쓰지 않는다.** 마스터 15는 t516이 둔 112.35(표시 112)를 그대로 쓴다. 실행 직전에 `NORMEDVALUE`가 69가 아니면 아무것도 보내지 않고 멈춘다. 전역 마스터 값을 다시 쓰는 줄은 "새 번호만" 규칙 밖이다.

## 3. 대본 행 → 명령 (0~25마디)

음악 시각은 `reports/loveattack-music-map-20261006.md` 마디표의 다운비트 시각이다. 표의 원천은 `row_map.py` → `row_map.txt`다.

### 장면 시퀀스 250 (타임코드 트랙 1)

| 대본 행 | 큐 | 음악 → TC | 페이드 | 명령 내용 |
|---|---|---|---|---|
| 0:00.0 시작 장면 | 1 `Intro A` | 0.00 → 3.00 | 0 | WASH 0 + 라벤더(미리 색만) · FOH 0 · BACK 차가운 화이트 · SIDE 라벤더 · 무빙 디머 60 + 차가운 화이트 · BLIND 0 |
| 0:14.4 벌스 1 장면 | 2 `Verse One` | 14.36 → 17.36 | 4.27(2마디 번짐) | WASH 40 · FOH 60 · BACK 라벤더 |
| 0:29.4 프리코러스 덜어냄 | 3 `Pre One` | 29.35 → 32.35 | 0.53 | WASH 25 |
| 0:36.9 17마디 3박 비움 | 4 `Pre Gap` | 36.86 → 39.86 | 0 | WASH 10 |
| 0:37.9 **강조** BLIND 60 + 0:37.9 WASH 핑크 70 | 5 `Chorus One Hit` | 37.90 → 40.90 | 0 | BLIND 60 · WASH 70 + 핑크 |
| 0:37.9 강조 — 1박 뒤 끔 | 6 `Blind Off` | 38.43 → 41.43 | 0.27(반 박) | BLIND 0 |
| 0:46.5 핑크 → 피치 | 7 `Peach Bleed` | 46.51 → 49.51 | 2.14(1마디) | WASH 피치 |

### 리듬 시퀀스 251 (타임코드 트랙 2)

| 대본 행 | 큐 | 음악 → TC | BACK 디머(단계1/2, Measure) | SIDE-L / SIDE-R | 무빙 U / D (Pan, Tilt, Phase, Measure) |
|---|---|---|---|---|---|
| 0:00.0 BACK 30 실루엣 · 무빙 바닥 쪽 | 1 `Intro Back` | 0.00 → 3.00 | 30/30 | 0 / 0 | Pan 0 · Tilt 15 고정 |
| 0:00.0 시작 히트 | 2 `Start Hit` | 0.96 → 3.96 | 100/100 | 0 / 0 | 그대로 |
| (시작 히트 끝) | 3 `Intro Hold` | 1.50 → 4.50 | 30/30 | 0 / 0 | 그대로 |
| 0:05.8 3~6마디 4박 펄스 | 4 `Kick Four` | 5.78 → 8.78 | 30/60, M4 | 0 / 0 | 그대로 |
| 0:10.1 5마디 무빙 한 칸 올림 | 5 `Movers Mid` | 10.07 → 13.07 | 30/60, M4 | 0 / 0 | Tilt 45 고정 |
| 0:14.4 7~10마디 1·2·4박 펄스 60 | 6 `Verse Pulse` | 14.36 → 17.36 | 30/60, M1 | 0 / 0 | Tilt 45 고정 |
| 0:16.5 8~13마디 틸트 웨이브 8박 | 7 `Tilt Wave` | 16.50 → 19.50 | 30/60, M1 | 0 / 0 | Tilt 33/57(45±12), Phase 0 Thru 360, **M8** |
| 0:22.9 11~13마디 SIDE 2·4박 번갈아 · 펄스 멈춤 | 8 `Side Chase` | 22.93 → 25.93 | 30/30 | 0/100 · 100/0, M4 | 틸트 웨이브 계속 |
| 0:29.4 14마디 덜어냄 + 가속 스윕 4박 | 9 `Sweep Four` | 29.35 → 32.35 | 30/30 | 0 / 0 | Pan -12/12, Tilt 45, Phase 0, M4 |
| 15마디 스윕 2박 | 10 `Sweep Two` | 31.51 → 34.51 | 30/30 | 0 / 0 | M2 |
| 16마디 스윕 1박 | 11 `Sweep One` | 33.65 → 36.65 | 30/30 | 0 / 0 | M1 |
| 17마디 1·2박 스윕 반 박 | 12 `Sweep Half` | 35.79 → 38.79 | 30/30 | 0 / 0 | **M0.5** |
| 0:36.9 17마디 3박 — 모두 멈춤, 무빙 위쪽 한 점 | 13 `Pre Gap` | 36.86 → 39.86 | 30/30 | 0 / 0 | Pan 0 · Tilt 60 고정 |
| 0:37.9 18~25마디 BACK 펄스 100 · MOVER-U 위로 | 14 `Chorus Pulse` | 37.90 → 40.90 | 30/100, M1 | 0 / 0 | U Tilt 75 고정 · D Tilt 60 고정 |
| 0:40.1 19~25마디 MOVER-U 팬 웨이브 2박 | 15 `Pan Wave` | 40.08 → 43.08 | 30/100, M1 | 0 / 0 | U Pan -12/12, Tilt 75, Phase 0 Thru 360, M2 · D 그대로 |

- 끝: 재생 판이 음악 57.08초(26마디 1박 + 2초) 뒤에 `Off Timecode 22`·`Off Sequence 250`·`Off Sequence 251`을 보낸다. 26마디부터의 대본 행(펄스 대상 MOVER-U로 옮김 등)은 이 묶음 밖이다.
- 이벤트 간격은 가장 가까운 곳도 0.53초(시작 히트 0.96 → 1.50, BLIND 37.90 → 38.43)다. 1박 아래로 붙은 이벤트는 없다.
- 리듬 큐 하나의 실제 줄 모양은 `row_map.txt` 끝(큐 7 예시)에 있다.

## 4. 대본과 다른 점 — 확인된 수단으로 옮기며 생긴 차이

| 대본 | 이 명령 파일 | 까닭 |
|---|---|---|
| 1·2·4박 펄스(3박은 쉼, 7~10·18~25마디) | **매 박** 펄스(M1) — 3박도 친다 | 3박만 빼려면 4단계 페이저가 필요하다. 4단계 디머 페이저는 안 잰 것이다(t515 §3) |
| 3~6마디 "4박에 한 번, 반 박 안에 내림" | 4박 한 바퀴에 2박 켜짐(M4, 2단계) | 2단계 페이저는 한 바퀴를 반씩 나눈다. 켜짐 폭을 줄이는 `At Width`는 FXGEN에서만 확인했고 t516에서는 안 썼다 |
| 펄스가 박 첫머리에 맞음 | 박과 어긋날 수 있음 | 큐 Go 순간 페이저가 어느 단계부터 도는지(박 정렬)는 안 잰 것이다 |
| 시작 히트 0:00.0 | 0.96초(앞박) | 마디표의 첫 박이 0.96초다. 대본 표의 0:00.0은 "앞박" 행이다 |
| 바닥 쪽 "좁은" 고정 빔 | Tilt 15만 — 줌 없음 | 줌 값 줄은 이 수단 목록에 없다 |
| 움직임 크기 Pan ±12 · Tilt ±12 | 그대로 옮김 | 대본의 자리표시 값이다. t516 v5 E1은 ±30에서 흔들림이 보였다. ±12가 작아 안 보이면 한 줄만 바꾸면 된다 |
| 위치(바닥 쪽·중간·위쪽 한 점·위로 연 자리) | Tilt 15 · 45 · 60 · 75 | 자리표시다. Tilt 단위(퍼센트·각도)는 안 잰 것이다(t516 §4-8) |
| 색 이름 | RGB 자리표시(라벤더 72/60/100 등) | 감독 지시 2026-09-28 — 색 미세 조정은 전체를 마친 뒤 |
| ODD/EVEN | 쓰지 않음 | 0~25마디 행에는 ODD/EVEN 체이스가 없다. 11~13마디 SIDE-L/SIDE-R 번갈이는 두 목록의 단계 값을 엇갈려(0/100 · 100/0) 냈다 |

## 5. 안 잰 것 — 이 묶음에서 처음 쓰는 조합

t516에서 하나씩은 확인됐지만, 이렇게 묶어 쓰는 것은 처음이다. 실기에서 어긋나면 감독 눈으로 드러난다.

1. **한 큐 안에 선택 여러 개 + `Step 2`.** 리듬 큐마다 선택 다섯 개(BACK·SIDE-L·SIDE-R·MOVER-U·MOVER-D)에 단계 1 값을 넣고, `Step 2` 뒤 다시 다섯 개를 선택해 단계 2 값과 타이밍을 넣는다. t516은 큐마다 선택이 하나였다. `Step 2` 뒤 선택을 바꿔도 단계 2에 머무는지는 안 잰 것이다.
2. **`At Measure 8`과 `At Measure 0.5`.** 확인된 값은 4·1(v4)과 2(무변화)다. 8은 틸트 웨이브, 0.5는 17마디 반 박 스윕이다. 무빙이 0.27초 왕복을 따라가는지도 안 잰 것이다.
3. **절대값 단계 + `Phase 0 Thru 360`.** 위상 펼침은 v4 A2(상대값 한 단계)에서 확인했고, v5 E1(절대값 단계)은 `Phase 0`이었다.
4. **트래킹 끊기.** 멈춘 상태를 "두 단계 값이 같은 페이저"로 다시 적어 앞 큐의 페이저를 덮는다. 이것이 실제로 움직임을 멈추는지는 안 잰 것이다.
5. **Spiider 서브픽스처 선택.** `521 + 521.1 + 521.2 + 521.3`으로 디머·색·Pan·Tilt를 모두 준다. Spiider 디머가 켜지는지는 안 잰 것이다(t516 v2 227에서 16대 중 8대만 켜짐 — 어느 8대인지 안 갈림).
6. **소수 이벤트 시각**(예: 3.96·40.9초). t506·t516은 정수 초였다. 트랙당 이벤트 15개도 처음이다(지금까지 3개).
7. **BACK 201~212 무점등**(t519 미해결). 대본대로 넣었다.
8. **다시 재생.** `Off` 뒤 두 번째 `Go Timecode 22`가 시퀀스를 큐 1부터 다시 여는지는 안 잰 것이다. 첫 재생은 새로 만든 시퀀스라 해당 없다.

## 6. 승인 요청

### 승인 파일

| 파일 | 줄 | sha256 | 내용 |
|---|---|---|---|
| `.moai/reports/t520/approval_m2a_batch1.txt` | 579 | `ef67a55c9eb17c7ef7d39c7f66fcfca0ef9f1964d3c6f963ce4c60698380f042` | 쓰기 — 장면 250(32줄) · 리듬 251(513줄) · TC22 만들기(6) · 서브트랙(2) · 이벤트(26) |
| `.moai/reports/t520/approval_m2a_play.txt` | 4 | `b7a022403aff28f3f00ffb7f1cac5761765f270c1b39d4f694b219070bf1e22b` | 재생 — `Go Timecode 22` / `Off Timecode 22` · `Off Sequence 250` · `Off Sequence 251` |

- 두 파일 모두 주석·빈 줄·큰따옴표 0줄. `Save`·`Delete`·`Remove`·`Copy`·`Move`·`Edit`·`Master` 줄 0.
- 게이트 사유(리허설 `steps.jsonl` 집계): `Store Sequence` 22 · `Store Timecode` 4 · `Assign Sequence` 2가 금지 목록에 걸린다. 묶음 전체를 위험(`kind=t520_m2a`)으로 선언해서, 사유가 없는 줄도 승인 없이는 나가지 않는다.
- 재생 파일은 실기 전부-거절을 아직 돌릴 수 없다. 사전 판독이 250·251·TC22의 이름을 요구하는데 아직 없기 때문이다. 문면은 리허설에서 땄다(t516 되돌리기 파일과 같은 처지). 쓰기 실행 뒤에 재생 전부-거절을 먼저 돌려 문면을 확인할 수 있다.

### 실행 (리드의 「실행」 뒤에만)

```
# 1) 쓰기 — 콘솔 쓰기 579줄(걸리는 시간은 안 잰 것 · 큐를 만드는 동안 프로그래머 값이 잠깐 무대에 나온다)
uv run python .moai/reports/t520/m2a_batch1.py .moai/reports/t520/live_write --approve .moai/reports/t520/live_denyall
uv run python .moai/reports/t512/approval_vs_sent.py .moai/reports/t520/approval_m2a_batch1.txt .moai/reports/t520/live_write/audit

# 2) 재생 — 타임코드 3초 + 음악 57.08초 = 약 60초, 음원 포함
uv run python .moai/reports/t520/m2a_play.py .moai/reports/t520/play_denyall
uv run python .moai/reports/t520/m2a_play.py .moai/reports/t520/play_live --approve .moai/reports/t520/play_denyall --audio "/Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3"
uv run python .moai/reports/t512/approval_vs_sent.py .moai/reports/t520/approval_m2a_play.txt .moai/reports/t520/play_live/audit
```

- 쓰기 실행기는 시작할 때 250·251·TC22가 비었는지, 마스터 15가 69인지 다시 읽는다. 하나라도 다르면 아무것도 보내지 않는다.
- `tc_a` 뒤 트랙을 되읽어 NO로 서브트랙·이벤트 주소를 만든다. NO가 1·2가 아니면 문면이 승인과 달라져 게이트가 거절하고 멈춘다. 이벤트 수가 7·15가 아니면 판정에 적는다.
- 쓰고 남는 것: 시퀀스 250·251, 타임코드 22. 지우지 않는다. 쇼 저장은 보내지 않는다(감독이 정한다).

## 7. 음원 재생 동기

- 타임코드 0초에서 3초 뒤가 음악 0초다.
- **권장 — 스크립트가 음원을 튼다(`--audio`).** 재생 판이 `Go Timecode 22`를 보낸 뒤 3초가 되면 이 Mac에서 `afplay`로 mp3를 튼다. 틀기 직전과 직후에 타임코드 `CURSOR`를 읽어 `result.json`의 `audio`에 남긴다. 그래서 실제 어긋남을 사후에 볼 수 있다. 소리는 이 Mac의 출력 장치로 나온다. `afplay`가 소리를 내기까지의 지연은 안 잰 것이다.
- **대안 — 감독이 손으로 맞춘다.** `--audio` 없이 재생 판을 돌리고, 콘솔 타임코드 창의 시각이 3.0초를 지날 때 감독이 음원을 튼다. 사람 손 지연(대략 0.2초 안팎, 안 잰 것)이 더해진다.
- 어느 쪽이든 결과가 어긋나 보이면 LEAD를 바꾸지 말고, 측정된 어긋남을 기록한 뒤 다음 판에서 음원 시작 시각만 옮긴다.

## 8. 감독이 볼 것

| 순간(음악) | 볼 것 |
|---|---|
| 0~6마디 | 무빙이 아래쪽을 비춤 → 0.96초에 역광 한 번(BACK, 안 보일 수 있음) → 5마디에 무빙이 중간 높이로 올라감 |
| 7마디 14.4초 | WASH 라벤더가 2마디에 걸쳐 번지고 얼굴 빛(FOH)이 켜짐 |
| 8~13마디 | 무빙이 위아래로 천천히 출렁이고, 위상이 펼쳐져 줄지어 따라감(틸트 웨이브 8박) |
| 11~13마디 | SIDE-L·SIDE-R가 2박마다 번갈아 켜짐 |
| 14~17마디 | 무빙이 다 같이 좌우로 왕복하며 마디마다 두 배 빨라짐 |
| 17마디 3박 36.9초 | 모두 멈추고 WASH 10%, 무빙이 위쪽 한 점에 모임 |
| 18마디 37.9초 | BLIND가 한 박 켜졌다 꺼짐 + WASH 핑크 · MOVER-U 위로 |
| 19~25마디 | MOVER-U가 좌우로 흔들리며 줄지어 따라감(팬 웨이브 2박) · 22마디에 WASH가 피치로 번짐 |

합격/불합격이 아니라 **어울림/아님**을 본다. 위 §5의 1~5번이 어긋나면 특정 구간만 움직임이 안 보이거나 멈추지 않는 모습으로 드러난다.

## 9. 증거

| 파일 | 무엇 |
|---|---|
| `steps_run0.txt` · `run0_readonly.txt` | 실기 읽기(쓰기 0) — 빈 번호, 마스터 15, 서브픽스처, 기종 DMX 채널, 시퀀스·타임코드 목록 |
| `m2a_batch1.py` · `m2a_play.py` | 쓰기·재생 실행기(t516 v1·v5 틀) |
| `rehearse/` · `play_rehearse/` | 가짜 콘솔 리허설(감사 로그 · steps) |
| `live_denyall/` · `live_denyall.stdout.txt` | 실기 전부-거절 |
| `rehearse_approval_vs_sent.txt` · `play_rehearse_approval_vs_sent.txt` | AC-012 리허설 PASS |
| `control_line_removed.txt` · `control_line_removed_result.txt` | 양성 대조 FAIL |
| `row_map.py` · `row_map.txt` | §3 표의 원천 |

## 10. 잔여 위험

- 가짜 콘솔은 번호·트랙 NO·이벤트 수만 흉내 낸다. 페이저·트래킹·재생은 증거가 아니다.
- 리듬 큐마다 34줄이라 쓰기 파일이 579줄로 길다. 줄 하나가 콘솔에서 실패하면 그 큐 내용이 모자란 채 저장될 수 있다. 실행 판정은 송신 결과(`not-ok` 수)를 함께 본다.
- 스피드 마스터 15를 누가 바꿔 두었으면 실행기가 멈춘다(의도된 동작). 마스터 BPM이 112인지 112.35인지는 여전히 가릴 수 없다(t516 §4-1).
- BACK이 안 보이면 0~13마디의 박자 층은 SIDE 체이스(11~13마디)와 무빙 움직임만 남는다.

## 11. v2 — BACK을 객석 쪽으로 기울임 (감독 결정 2026-10-07, 리드 경유)

- 리드 판독 뒤 실행은 보류됐다. 감독 관찰은 「BACK은 켜지지만 빔이 수직 아래라 역광 방향이 아니다」였다.
- t519 시험(Seq 260~262, `Pan 180 ; Tilt 30/45/60`, 객석 = −Y)을 보고 감독이 정했다(원문): 「80도 정도는 되어야겠어」.
- 리드 지시: BACK 201~212 기준 위치를 Pan 180 · Tilt 80으로 해서 장면 시퀀스(250) 모든 큐에 넣는다. 줄 꼴은 t519 `approval_back_aim.txt` 그대로, Fixture 목록 한 줄이다. 리듬 251의 BACK은 디머만 맡는다.

**바뀐 것** — 장면 큐 7개마다 `Store` 바로 앞에 한 줄을 더했다:

```
Fixture 201 + 202 + 203 + 204 + 205 + 206 + 207 + 208 + 209 + 210 + 211 + 212 ; Attribute 'Pan' At 180 ; Attribute 'Tilt' At 80
```

- 위치는 본체(201~212)에만 준다. t519 줄 꼴도 위치는 `Fixture 201`에, 서브픽스처 `201.1`에는 디머만 줬다.
- v1 대비 `diff`: 더한 줄 7(모두 위 줄과 같음), 지운 줄 0. 장면 묶음 32 → 39줄, 리듬·타임코드 묶음은 그대로다.
- 이로써 BACK 위치의 주인은 장면 250이다(§2 표에 "BACK 위치"가 더해진다). 리듬 251은 BACK 위치를 건드리지 않는다.
- Tilt 80이 t519에서 시험한 값(30·45·60)보다 크다. 80에서 빔이 어디로 가는지는 실행 뒤 감독 눈으로 본다.

| 단계 | 결과 |
|---|---|
| 가짜 콘솔(`rehearse_v2`) | 5묶음 끝까지 · 트랙 NO 1→250, NO 2→251 · 이벤트 7·15 |
| 실기 전부-거절(`live_denyall_v2`) | preflight `responder_ok` · 사전 판독 통과(250·251·TC22 빔, 마스터 15 = 69) · 요청 5, 승인 0 · 감사 로그 `rejected` 5, `executed`는 `props_query` 1행뿐 · 요청 문면 = 리허설 `True` |
| AC-012 리허설 | `rehearse_v2_approval_vs_sent.txt` — 586줄, sha256 같음, 송신 안 됨 0 · 승인 안 됨 0 → **PASS** |
| 양성 대조 | 100번째 줄을 뺀 사본 → **FAIL**(`control_v2_line_removed_result.txt`) |

**승인 파일(v2)**

| 파일 | 줄 | sha256 |
|---|---|---|
| `.moai/reports/t520/approval_m2a_batch1_v2.txt` | 586 | `7438fc88400af70c4633700d2b10ffceee925b50dd3982ba39edf4100bb00414` |
| `.moai/reports/t520/approval_m2a_play.txt`(변화 없음) | 4 | `b7a022403aff28f3f00ffb7f1cac5761765f270c1b39d4f694b219070bf1e22b` |

- 주석·빈 줄·큰따옴표 0줄, `Save`·`Delete`·`Remove`·`Copy`·`Move`·`Edit`·`Master` 줄 0.

**실행(리드 「실행」 뒤에만)** — §6의 1)을 다음으로 바꾼다. 2) 재생은 그대로다:

```
uv run python .moai/reports/t520/m2a_batch1.py .moai/reports/t520/live_write --approve .moai/reports/t520/live_denyall_v2
uv run python .moai/reports/t512/approval_vs_sent.py .moai/reports/t520/approval_m2a_batch1_v2.txt .moai/reports/t520/live_write/audit
```

- v1 파일(`approval_m2a_batch1.txt`, `live_denyall/`)은 기록으로 남긴다. v1 전부-거절 폴더로는 실행할 수 없다. 문면이 달라 게이트가 거절한다.

## 12. 실기 쓰기 1회 실패 → 프로브 A → B 판(253·254·TC23)

### 12-1. 쓰기 1회(`live_write`, 리드 「실행」 2026-10-07) — 장면 묶음에서 멈춤

- 장면 묶음(39줄)은 승인됐고 모두 나갔다. 그중 4줄이 콘솔 회신 `Illegal object`, 35줄은 OK였다. 실행기는 「묶음 안 모든 줄 OK」일 때만 다음 묶음으로 가게 짜여 있어서, 리듬 251·TC22 묶음은 승인 요청도 하지 않았다. ②③(재생·음원)은 하지 않았다.
- 실패 4줄은 모두 **서브픽스처 번호(점)가 `+` 목록 안에 든 줄**이다: 큐1 BACK 색(24개), 큐1 SIDE 색(24개), 큐1 무빙 디머 60 + 색(40개), 큐2 BACK 라벤더.
- 되읽기(`after_write_readonly.txt`): Seq 250 이름·큐 7개 있음, 251·TC22 없음. AC-012 FAIL(송신 39, 승인 안 됨 547, not-ok 4).
- 🔴 **내 설계 잘못.** t516에서 확인된 점 번호 꼴은 `Fixture 201.1 ;`처럼 혼자 쓴 것뿐이었다. 그걸 `+` 목록으로 넓혀 썼고, §5 "처음 쓰는 조합"에도 적지 않았다. 확인된 꼴을 일반화한 것을 확인된 것처럼 다뤘다.
- 250은 무빙 디머 60이 빠진 채로 남았을 것이다(추정 — 실패 줄이 통째로 안 들어갔다고 본다). 잔여로 두고 덮어쓰지 않는다.

### 12-2. 원인 가르기

- 실기 기록 전수(`list_shapes.py`: t513 run6/8, t516 v1~v5, t519 aim, 이번): `+` 목록 성공은 1·6·8·12·16·20개, 모두 점 없음. 실패는 24·40개, 모두 점 포함. 기록만으로는 "점"과 "길이"가 겹쳐 못 가른다.
- **프로브 A**(`line_probe.py`, Seq 252, 승인 파일 22줄 sha256 `630f8a0f…`, 리드 「실행」 1회):

| 큐 | 줄 | 콘솔 회신 |
|---|---|---|
| 1 `Main Only` | `Fixture 301 + 302 ; Attribute 'Dimmer' At 100` | OK |
| 2 `Sub In List` | `Fixture 301.1 + 302.1 ; Attribute 'Dimmer' At 100` | **Illegal object** |
| 3 `Long List 24` | `Fixture 401 + … + 430 + 111 + 112 + 113 + 114 ; Dimmer 50`(점 없이 24개) | OK |

- t512 대조 PASS(22줄, not-ok 1 = 큐2 줄). 큐 순서는 트래킹 오염을 피하려고 "본체만"을 큐1에 뒀다(리드 승인).
- 큐1 다시 보기(`replay_252.py`, 2줄 sha256 `3c2f10f7…`, 이름 사전 판독 일치, 전부-거절 뒤 리드 사전 허락으로 1회, t512 PASS). 감독 관찰(원문): **「안켜졌어」**.
- **판정(잰 것)**: ① 원인은 목록 안의 점 번호다. 길이(24개)는 원인이 아니다. ② Aura XB는 본체 선택만으로 서브픽스처 디머가 열리지 않는다(301·302 Dimmer 100 무점등). → B = `split_each`(리드 확정).

### 12-3. B 판 — 생성기와 결과

- 생성기 `m2a_batch1.py`에 `--target b --sub-mode split_each`를 더했다. 기본값(`--target v2`)은 v2 승인 파일과 바이트 단위로 같다(`plan_stats.py` → `equals … True`, sha256 `7438fc88`).
- `split_each`: 본체 목록 한 줄 + 점 번호마다 한 줄(`Fixture 201.1 ;` — t516에서 18회 OK인 꼴). 리듬 페이저의 타이밍 줄(Phase·Measure·SpeedMaster)은 그 선택에만 붙으므로 점 번호 줄마다 다시 적는다.
- **위치(Pan/Tilt)만 담은 줄은 본체에만** 준다. Aura XB의 서브픽스처 채널(`Aura_*`)에는 Pan/Tilt가 없다(`v4_reads1.txt` DMX 채널 목록 — Pan/Tilt는 `Main Module` 쪽에만). t519가 `Fixture 201 ; Pan/Tilt`로 BACK을 실제로 돌렸다. Spiider는 같은 구조로 보고 같은 규칙을 썼다 — Spiider 위치가 본체에 있는지는 안 잰 것이다.
- 번호·이름: Seq 253 `'LOVE ATTACK - RHYTHM M2a B SCENE'` · Seq 254 `'… M2a B RHYTHM'` · TC 23 `'… M2a B TC'`. BACK Pan 180·Tilt 80은 장면 큐 7개 모두에 그대로 있다.
- **줄 수 586 → 2,446.** 까닭: Aura XB(BACK 12·SIDE 12)와 Spiider(8 × 3)의 서브픽스처 48개가 한 줄씩 따로 나가고, 리듬 큐 15개마다 BACK·SIDE 서브픽스처 24개 각각에 값 줄 + 타이밍 3줄이 두 단계로 붙는다(장면 39 → 99, 리듬 513 → 2,313).

| 단계 | 결과 |
|---|---|
| 가짜 콘솔(`rehearse_b`, `play_rehearse_b`) | 쓰기 5묶음 끝까지, 트랙 NO 1→253·NO 2→254, 이벤트 7·15 · 재생 2묶음 끝까지 |
| 실기 전부-거절(`live_denyall_b`) | preflight `responder_ok` · 사전 판독 통과(253·254·TC23 빔, 마스터 15 = 69) · 요청 5, 승인 0 · `rejected` 5, 명령 송신 0 · 문면 = 리허설 `True` |
| AC-012 리허설 | 쓰기 2,446줄 **PASS** · 재생 4줄 **PASS** · 양성 대조(500번째 줄 삭제) **FAIL** |
| 정적 검사 | 대상 번호는 Seq 253·254·TC 23뿐 · 점 번호가 든 `+` 목록 줄 0 · 큰따옴표 0 · Save/Delete/Remove/Copy/Move/Edit/Master 0 |

**승인 파일(B)**

| 파일 | 줄 | sha256 |
|---|---|---|
| `.moai/reports/t520/approval_m2a_batch1_b.txt` | 2446 | `42b693ade789052e52b55d5095699bb4bfc65e2b843fa27a245270f4d8a2f5b4` |
| `.moai/reports/t520/approval_m2a_play_b.txt` | 4 | `2cb3d5dcfa0392bf58dad8f3d218c408bf9b2b9cbfb5833f20d8cfb88960c60d` |

**실행(리드 「실행」 뒤에만)**

```
uv run python .moai/reports/t520/m2a_batch1.py .moai/reports/t520/live_write_b --approve .moai/reports/t520/live_denyall_b --target b --sub-mode split_each
uv run python .moai/reports/t512/approval_vs_sent.py .moai/reports/t520/approval_m2a_batch1_b.txt .moai/reports/t520/live_write_b/audit
uv run python .moai/reports/t520/m2a_play.py .moai/reports/t520/play_denyall_b --target b
uv run python .moai/reports/t520/m2a_play.py .moai/reports/t520/play_live_b --approve .moai/reports/t520/play_denyall_b --target b --audio "/Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3"
uv run python .moai/reports/t512/approval_vs_sent.py .moai/reports/t520/approval_m2a_play_b.txt .moai/reports/t520/play_live_b/audit
```

**아직 안 잰 것(B)**

- 점 번호 한 줄 + 바로 뒤 타이밍 줄(`Fixture 201.1 ; Dimmer …` → `Attribute 'Dimmer' At Phase 0` …)이 페이저를 그 서브픽스처에 거는지. t516의 점 번호 줄은 정적 값만 줬다.
- Spiider 서브픽스처 디머가 켜지는지, Spiider 위치가 본체에 있는지.
- 쓰기 2,446줄이 한 번에 나갈 때 응답기·콘솔이 끝까지 받는지(지금까지 실기 최대 124줄).
- §5의 나머지(한 큐에 선택 여러 개 + `Step 2`, Measure 8·0.5, 트래킹 끊기, 소수 이벤트 시각)는 그대로 미측정이다.
- 잔여 객체: Seq 250(색·무빙 디머 일부 빠짐), Seq 252(프로브 A). 지울지는 감독이 정한다.

## 13. split_each 보류 → 그룹 선택 프로브 G (감독 의견 2026-10-07)

- 감독(원문, 리드 경유): 「여러대의 장비를 작동하려면 그룹을 만들어서 사용하면 되잖아」. 앱 Seq 219도 `Group N ; Attribute …` 꼴을 쓴다(t516 `line_shapes.txt`: 219에 110줄).
- B 판(§12-3, 2,446줄)은 만들어 두었으나 실행 보류다.

### 13-1. 프로브 G — 기존 그룹 5(SIDE-L)로 서브픽스처 디머가 열리나

- `group_probe.py`(프로브 A 실행기 재사용): 새 Seq 255 큐 1 `Group 5 ; Attribute 'Dimmer' At 100` → 5초 여유 → `Goto Cue 1 Sequence 255` 15초 → `Off Sequence 255`. 이름 `'GROUP PROBE - GROUP 5 SIDE-L'`.
- 그룹 구성원(서브픽스처 포함 여부)은 응답기로 읽을 수 없다(그룹 `COUNT` 늘 0, t516 §4-3). 그래서 감독 눈으로 가른다. 볼 곳은 무대 왼쪽 가장자리 X −7m · 무대 뒤쪽 Y +3m 기둥(301 높이 1.2m, 302 2.6m …).

| 단계 | 결과 |
|---|---|
| 가짜 콘솔(`groupG_rehearse`) | 3묶음 끝까지 |
| 실기 전부-거절(`groupG_denyall`) | 사전 판독 Seq 255 빔 · 요청 3, 승인 0 · `rejected` 3, 명령 송신 0 · 문면 = 리허설 `True` |
| AC-012 리허설 | 8줄 PASS |
| 승인 파일 | `approval_group_probe.txt` 8줄, sha256 `a48099b85e96cb936eb2a277a92830fa0d02a7ab9385ea3c893fec42ebf03bfd` |

- 실행(리드 「실행」 뒤에만): `uv run python .moai/reports/t520/group_probe.py .moai/reports/t520/groupG_live --approve .moai/reports/t520/groupG_denyall` → `approval_vs_sent.py approval_group_probe.txt groupG_live/audit`

### 13-2. 초안 — 그룹 5로 안 켜질 때, 서브픽스처까지 담은 새 그룹 (쓰지 않음, 문서 근거만)

**문서 근거**

- [Select Fixtures](https://help.malighting.com/grandMA3/2.2/HTML/operate_select_fixtures.html): 「To select fixture 301 and all its sub-fixtures, type: Fixture 301.」 · 「To select the main fixtures and all sub-fixtures of fixtures 301 thru 303, type: Fixture 301 Thru 303.」 · 따로 친 선택은 누적된다(「Fixture 1 Thru 5」 뒤 「Fixture 9 + 10」이 선택에 더해진다).
- [Groups](https://help.malighting.com/grandMA3/2.2/HTML/qsg_group.html): 지금 선택에서 `Store Group 1`로 그룹을 만든다. 이 페이지는 서브픽스처 포함·덮어쓰기 옵션을 적지 않는다.
- 저장소 룰북 `server/rulebook/assets/v2.4.2/00_grammar.md:66`: `Fixture 101 Thru 110` → `Store Group 7` → `Label Group 7 'Vocals'`.

**초안 줄 꼴(번호 `<G>`는 실행 직전 빈 그룹 번호를 읽어 정한다 — 그룹 1~18 사용 중)**

```
ChangeDestination Root
ClearAll
Fixture 301 Thru 306.
Store Group <G>
Set Group <G> Property 'Name' 'SIDE-L ALL DIMMERS'
ClearAll
```

- 같은 꼴로 BACK `Fixture 201 Thru 212.`, SIDE-R `Fixture 311 Thru 316.`, MOVER-D `Fixture 521 Thru 528.`을 만든다.
- 뒤 점(`301.`) 선택은 **우리 콘솔에서 안 잰 것**이다. 프로브 A에서 거절된 것은 `+` 목록 안의 점 번호(`301.1 + 302.1`)였고, 뒤 점 꼴은 다른 문법이다.
- 뒤 점 선택이 받아들여지면 그룹을 만들지 않고 `Fixture 301 Thru 306. ; Attribute 'Dimmer' At 100`처럼 바로 써도 된다. 새 그룹은 감독이 콘솔에서 손으로 다시 쓰기 편하다는 이점이 있다.
- `Set Group … Property 'Name'`은 시퀀스·타임코드에서만 실기로 확인한 꼴이다. 그룹에서는 안 잰 것이다(대안: 룰북의 `Label Group <G> '…'`).
- 서브픽스처만 담은 그룹의 `Group N ; Attribute 'Pan'` 같은 줄이 위치 채널 없는 서브픽스처에서 오류를 내는지도 안 잰 것이다.

Sources:
- [Select Fixtures — grandMA3 2.2](https://help.malighting.com/grandMA3/2.2/HTML/operate_select_fixtures.html)
- [Groups — grandMA3 2.2](https://help.malighting.com/grandMA3/2.2/HTML/qsg_group.html)
