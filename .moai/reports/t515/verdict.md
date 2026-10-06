# t515 판정서 — M2 준비: 대본 이벤트 종류별 콘솔 구현 방식

- 카드: t515 · SPEC-LDRHYTHM-001 · 워크트리 `.claude/worktrees/t515` · 브랜치 `WT-m2-mechanism` (기준 `d182e598`)
- 범위: 문서·저장소 판독만. `server/` 수정 0 · 콘솔 접촉 0(읽기 포함) · 가짜 콘솔 실행 0
- 산출: `reports/ldrhythm-m2-mechanism-20261006.md`(본문) · 이 판정서 · `count_kinds.py` + `evidence/count_kinds.txt`
- 판정: **카드 ①~⑤ 답함.** 단, 카드 전제 하나를 정정한다(§2).

## 1. 카드 항목별 답

| 항목 | 답 | 본문 |
|---|---|---|
| ① 종류별 방법 후보 | 네 후보(타임코드 이벤트 Go · 스피드 마스터 페이저 · 큐 안 페이저 모양 · 층별 시퀀스)를 다섯 종류에 배정했다. 반복 동작(펄스·체이스·움직임)은 페이저, 블록 경계와 장면·강조는 타임코드 이벤트 | §2 · §3 |
| ② 실기 검증 상태 | 후보마다 [실기]/[문서]/[미측정]을 근거 파일:줄과 함께 적었다 | §2 표 · 승인 파일 예시 아래 표 |
| ③ 반 박 0.267초 | 페이저여야 한다. 타임코드 이벤트의 관측 구간 폭(0.15~0.27초, t506 §9)이 동작 길이와 같다. 이벤트는 1박 이상 떨어진 블록 경계에만 둔다 | §3 "빠른 동작은" |
| ④ 객체 수 | 시퀀스 4 · 큐 약 77~87 · 타임코드 1(트랙 4) · 이벤트 약 77~87 · 스피드 마스터 1 · 프리셋 11~24 · 실행기 0~4 [추정]. 박마다 이벤트를 두면 이벤트만 약 500 이상 | §4 |
| ⑤ 첫 묶음 + 승인 파일 모양 | 묶음 0(0~6마디, 미측정 다섯 가지 확인) → 묶음 1(0~25마디, 16행, 큐 약 22). 승인 파일 예시는 이름 줄(`'LOVE ATTACK - M2a'`) 포함, 작은따옴표·주석 없는 맨 줄 규칙 | §5 |

## 2. 카드 전제 정정

카드 문면: "스피드 마스터에 묶은 페이저(At SpeedMaster 실기 확인, Master 3.n At BPM 112.35)".

- 실기로 확인된 것은 **묶는 줄** `Attribute '<a>' At SpeedMaster <n>`뿐이다 — `.moai/specs/SPEC-COPILOT-FXGEN-001/spec.md:43`(V3, onPC 2.4.2, 사람 관측).
- **BPM 설정 줄** `Master 3.n At BPM <값>`은 [문서]만 있다 — `.moai/reports/t502/verdict.md:28`(BPM Keyword 페이지). 저장소 송신 기록 0건: `grep -rnI -E "Master 3|At BPM" server | grep -v /tests/` → 0줄. 저장소 전체 grep 에서는 문서·SPEC·보고서·CHANGELOG 에만 나온다. `.moai/reports/t508/verdict.md:41`·`t504/verdict.md:33`도 "미측정"으로 적었다.
- 112.35는 t509가 잰 곡 BPM이지 콘솔에 넣어 본 값이 아니다. 소수 BPM을 마스터가 받는지는 [미측정].

## 3. 측정·판독 기록

| 무엇 | 명령 | 관측 |
|---|---|---|
| 기준 트리 | `git merge-base --is-ancestor d182e598 HEAD` | `HEAD_OK`, HEAD `d182e598` |
| 대본 판 | `git log origin/WT-loveattack-m1 -4` | `5e064752` t514 수정본이 `6de980be` t511 초안 위에 있음 → `5e064752`를 읽었다 |
| 종류별 행 수 | `git show origin/WT-loveattack-m1:…/m1-love-attack-script.md > tmp` 후 `python3 .moai/reports/t515/count_kinds.py < tmp` (exit 0) | `rows 61 {색/위치 21, 펄스 20, 움직임 효과 8, 체이스 8, 강조 4}` · 0~25마디 16 `{색/위치 6, 펄스 5, 움직임 3, 체이스 1, 강조 1}` (`evidence/count_kinds.txt`). 첫 실행에서 분류 안 된 8행을 찍어 보고 "움직임 효과" 종류를 추가했다 — 이후 미분류 0 |
| 이벤트 수 | 대본 §4 표(옮긴 값) | 펄스 173 · 체이스 120 · 색/위치 23 · 움직임 8곳 · 강조 4 — t514 `count_script.py` 출력, 이 카드에서 다시 재지 않음 |
| 가짜 콘솔 능력 | `grep -n -i -E "timecode\|speedmaster\|master\|bpm" server/tests/fake_console.py` | `Timecodes` 빈 풀 2줄뿐 — 타임코드 이벤트·스피드 마스터 동작 없음 |
| 앱 타임코드 이름 실기값 | `grep -n -i "name" .moai/reports/t502/evidence/t501_rain_212_approval_request.txt` | `210:Set Timecode 12 Property 'Name' 'Sequence 212 Timecode'` |
| `Label Sequence` 송신 이력 | `grep -rlI "Label Sequence" .moai/reports/t498 .moai/reports/t501 .moai/reports/t502 .moai/reports/t506` | 0건. 양성 대조 `grep -rlI "Assign Sequence" .moai/reports/t498 .moai/reports/t502` → 2파일 |
| position_fx 속도 줄 | `grep -n "At Speed" server/spatial/position_fx.py` | `:160-177` 고정 `At Speed` — SpeedMaster 아님 |
| 재생 계약 | `sed -n 45,56p server/director/emit.py` | `PLAYBACK_MODES = ("manual_go", "trig_time")` |

## 4. 안 잰 것 (Gaps)

- 콘솔을 읽지 않았다. 본문의 [실기]는 전부 이전 카드 기록(t506 · FXGEN V1~V7 · 룰북 validated · t498/t501 송신)을 옮긴 것이다.
- 객체 수·명령 줄 수는 행 수에서 계산한 추정이다. 명령 파일을 만들어 세지 않았다.
- 가짜 콘솔 리허설은 하지 않았다(가짜 콘솔에 타임코드·마스터 모형이 없어 의미가 작다 — 본문 §5 끝).
- [미측정] 12건: 박 정렬 · 4스텝 밝기 페이저 · 같은 속성 두 시퀀스 겹침 · 한 타임코드 트랙 여러 개 · SpeedMaster+Measure 동시 · ½박 Pan/Tilt · 소수 BPM · `Master 3.n At BPM` 송신 · `Label Sequence` 송신 · 한글 이름 · 이벤트 수 상한 · 스피드 마스터 1번 사용 여부. 앞 다섯은 묶음 0 확인 항목으로 넣었다.
- 본문의 한국어 다듬기(humanize 스킬) 패스는 돌리지 않았다.

## 5. 잔여 위험

- 대본이 감독 검토 중이다(PR #557 OPEN, `5e064752`). 종류가 바뀌거나 늘면 §3 표가 바뀐다. 행이 바뀌면 §1·§4 숫자만 바뀐다.
- 묶음 0의 "박 정렬"이 실패하면 페이저 중심 설계가 흔들린다. 그때 대안은 박 단위 이벤트지만, 정밀도 구간이 반 박과 같아 펄스 모양이 무너질 수 있다 — 측정 방법(이벤트 간격을 좁혀 빠지는 수 세기, t506 §9 끝)을 먼저 바꿔야 판단할 수 있다.
- 승인 파일 예시의 `<…>` 번호는 송신 직전 풀 재판독으로 채운다. 예시 그대로는 승인 대상이 아니다.
