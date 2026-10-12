# 카드 t618 — 큐 한 개 삭제 문법: 'Delete Cue N Sequence S' 가 'Not allowed'

- 배차: 리드 [96d544], 카드 t618 (Class B: run → sync).
- 작업 트리: `.claude/worktrees/t618` · 브랜치 `WT-delete-cue-syntax`
- 기준: `origin/main` `996cce28` 와 분기 차이 `0 0` (작업 시작 시 확인).
- 콘솔: 송신 없음 (배차 지시). 판별 줄은 리드가 실기로 잰다.
- 판정: **수정 보류, 제안만.** 문법 근거는 찾았지만, 그 문법이 배치 안에서 실제로 큐를 지우는지는 콘솔에서 본 적이 없다. 잘못 지우면 되돌릴 수 없는 쓰기라서 `beat_grid_send.py` 는 건드리지 않았다.

표기: **[잰 것]** 이 세션이 파일·감사 로그에서 직접 읽은 값. **[매뉴얼]** 설치된 벤더 문서(읽기 전용)에서 읽은 값. **[추정]** 읽은 값에서 끌어낸 해석.

## 3.1 주장 (Claim)

1. 앱이 내는 `Delete Cue <n> Sequence <s>` 는 실기에서 거절된다 (`Not allowed`). [잰 것]
2. 거절은 한 번이었고, 큐는 지워지지 않았다. [잰 것]
3. 매뉴얼은 큐 삭제를 "선택된 시퀀스에서" 하는 명령으로 적고, 시퀀스 인자를 받는 삭제 꼴을 보이지 않는다. [매뉴얼]
4. 벤더 시스템 테스트는 같은 설치본에서 `select <시퀀스>` 뒤 `delete cue <n> /NC` 를 쓴다. [매뉴얼]
5. 이 저장소의 실기 로그에서 `Delete Cue` 가 성공(`ok`)한 줄은 0건이다. [잰 것]
6. 따라서 올바른 문법을 확정하지 못했다. 수정 후보는 있으나 실기로 확인되지 않았다.

## 3.2 증거 (Evidence)

### 실기 — 거절된 줄

`.moai/reports/t608/v4/run-S4.jsonl` index 50 (14:53:20.948 UTC):

```
{"index": 50, "line": "Delete Cue 2 Sequence 700", "sent_at": "2026-10-12T14:53:20.948+00:00", "responded_at": "2026-10-12T14:53:21.015+00:00", "status": "failed", "detail": "Not allowed"}
```

같은 파일 `end`: `"sent": 50, "stopped_at": 50, "status": "stopped"`. 이 실행에서 `Store Sequence 700 Cue 5 CueFade 2 /CueOnly /Overwrite` 까지 49줄이 전부 `ok` 였다.

`.moai/reports/t608/v4/readback-after-S4.txt` 1행 (거절 직후):

```
== DataPool/Sequences/700 "OffCue" "CueZero" "Cue 1" "Cue 2" "Cue 3" "Cue 4" "Cue 5" "LDBEAT FOH"
```

큐 2가 그대로 남아 있다. [잰 것]

### 매뉴얼 — 설치본 grandMA3 2.4.2 (읽기 전용)

`/Users/studiox/MALightingTechnology/gma3_2.4.2/shared/language/HTML/keyword_delete.html`

- 150행: `To delete cue 2 in the selected sequence, type:` — 선택된 시퀀스 안의 큐 2 삭제. [매뉴얼]
- 160행 예시: `Delete Cue 2` — 시퀀스 인자 없음. [매뉴얼]
- 127행: `/NoConfirmation` 플래그. 앱이 쓰는 `/NoConfirm` 은 이 플래그의 줄임으로 보이며, 앱의 `Delete Sequence`·`Delete Preset`·`Delete Timecode … /NoConfirm` 은 실기에서 전부 `ok` 였다. [잰 것 + 매뉴얼]

`keyword_sequence.html` 157행 `To select sequence 5 in the sequence pool, type:` 과 `notes_cues.html` 160행 `Select Sequence 1` — 시퀀스 선택 문법. [매뉴얼]

### 벤더 시스템 테스트 — 같은 설치본

`/Users/studiox/MALightingTechnology/gma3_2.4.2/shared/resource/lib_plugins/systemtests/db/system_test_cuepart_delete.lua`

- 18–19행: `C('select '..Sequence:ToAddr());` 다음 `C('delete cue 1 /NC')` — 선택 후 큐 삭제. [매뉴얼]
- 52행: `C('Delete Cue 1 Part 1 /MoveValues /NC')` — 선택 상태에서 파트 삭제. [매뉴얼]
- `ToAddr` 의 실제 문자열 형식은 API 스텁(`gma3_api_meta.lua:324`, 본문 없음)에서 확인할 수 없다. [추정 여지]

### 저장소 — 앱 코드와 선례

- `server/design/beat_grid_send.py:505–520`: `Delete Cue {number} Sequence {sequence_number}` 를 만든다. 같은 자리에 `@MX:WARN` 과 `@MX:REASON` 이 "가설 문법, 다음 실기 접속에서 먼저 확인, 거절되면 이 자리만 고친다" 라고 적혀 있다. 이 가설이 여기서 거절된 것이다.
- 이 저장소에서 `Select Sequence` 나 `'select '` 를 내는 코드는 없다 (`server/` grep 0건). [잰 것]
- 실기 jsonl 에서 `Delete Cue` 가 나온 줄은 위의 거절 한 줄뿐이다 (`.moai/reports` 전체 `*.jsonl` 검색). [잰 것]
- `.moai/reports/t572/run-verdict.md`, `t612/progress.md` 의 3.4 Gaps 5번, `t616/progress.md` 24행은 모두 "실기 선례 없음" 이라고 적었고, 이번 실측이 그 상태를 확인했다. [잰 것]

### 같은 뒤쪽 시퀀스 인자 — 통과 선례

`Sequence` 를 뒤에 붙인 꼴 가운데 실기 `ok` 가 확인된 것:

- `Goto Cue 1 Sequence 701`, `Goto Cue 2 Sequence 700` 등 — `v3/run-S3.jsonl` index 1–4 `ok` [잰 것]
- `Set Cue 1 Sequence 701 Property 'TrigType' 'Time'` — `v3/run-S1b.jsonl` index 11 `ok` [잰 것]

즉 뒤쪽 `Sequence S` 인자는 `Goto`·`Set` 에서는 받아들여진다. `Delete` 에서만 거절됐다. 원인이 "뒤쪽 인자 불가" 인지, "이 시퀀스 700 의 상태" 인지, 다른 것인지는 아직 가르지 못했다. [추정]

### "Not allowed" 의 다른 출처

`.moai/reports/t552/probe_cause.txt` 의 `Not allowed for existing files` 는 오디오 파일 프로브의 문구다. 콘솔 응답이 아니므로 이 카드의 선례가 아니다. [잰 것]

## 3.3 기준선 귀속 (Baseline-attribution)

- 명령: `grep -rl "Delete Cue" "<주 체크아웃>/.moai/reports" --include='*.jsonl'` → `t608/v4/run-S4.jsonl` 1건.
- 명령: `grep -rh "Delete Cue" "<주 체크아웃>/.moai/reports" --include='*.jsonl'` → 위 거절 줄 1행 (`Not allowed`).
- 명령: `sed 's/<[^>]*>//g' keyword_delete.html | grep -n -i "noconfirm\|/NC\|selected sequence"` → 127·150행.
- 명령: `grep -rn "Select Sequence\|select sequence" …/gma3_2.4.2/shared/language/HTML` → `keyword_sequence.html:157`, `notes_cues.html:150·160`, `programmer-parts.html:247`.
- 웹 검색 (WebSearch, standard): 결과 URL 목록에 `help2.malighting.com/grandMA3/2.4/HTML/keyword_delete.html` 이 있었다. **열어 보지 않았다.** 검색 요약은 "시퀀스 이름을 Delete Cue 구문에 넣는 방법은 결과에 없다, 대상 시퀀스를 미리 선택하라" 라고 했다. 이 요약은 매뉴얼 본문과 같은 방향이지만, 이 문서의 근거는 설치본 매뉴얼이다.

## 3.4 미검증 (Gaps)

1. **콘솔에서 `Select Sequence S` 후 `Delete Cue N` 이 해당 큐만 지우는지** 본 적이 없다. 이 문서의 가장 큰 공백이다.
2. **`Delete Cue N Sequence S` 가 "Not allowed" 인 원인.** 문법 인자 문제인지, 시퀀스 700 의 상태(타임코드 70 에 배정된 시퀀스, 큐 참조 등) 문제인지 가르지 못했다. [추정]
3. **`/NC` 와 `/NoConfirm` 의 차이.** 벤더 테스트는 `/NC` 를 쓰고 앱은 `/NoConfirm` 을 썼다. 큐 삭제에서 둘 다 받는지 실측이 없다.
4. **웹 매뉴얼 2.4 페이지 본문.** 검색 결과 URL 만 확인했고 열지 않았다 (WebFetch 미사용).
5. **`ToAddr()` 의 실제 주소 문자열.** 벤더 테스트의 `select` 인자 형식을 이 세션에서 확인하지 못했다.
6. **`Store Sequence 700 Cue 5 CueFade 2 /CueOnly /Overwrite` 등 같은 실행의 나머지 49줄 효과.** 이번 카드 범위 밖이다.

## 3.5 잔여 위험 (Residual-risk)

- **엉뚱한 시퀀스의 큐가 지워질 위험.** `Select` 가 실패해도 응답이 `OK` 로 올 수 있다면, 뒤따르는 `Delete Cue N` 은 그때 선택된 다른 시퀀스의 큐 N 을 지운다. 이것이 제안을 "제안만" 으로 둔 이유다. 판별 시험에서 700–703 을 함께 읽어 이 상황을 잡아야 한다.
- 되돌릴 수 없다. 콘솔 내용은 앱이 되돌리지 못한다 (`beat_grid_send.py` 독스트링, t572 리드 결정).
- 수정이 승인 번들 내용을 바꾸므로, 고치면 승인 목록을 다시 만들고 sha 를 갱신해야 한다 (t612·t614 와 같은 처지).

## 4. 제안: 판별용 최소 줄 (리드가 실기로 잴 것, 콘솔 송신은 리드)

**반드시 scratch 시퀀스 `790` 에서 잰다.** 700–703 은 LDBEAT 쇼의 실제 시퀀스다. 790 은 어느 타임코드에도 배정되지 않은 빈 번호다 (t615 가 같은 번호를 썼고 정리했다).

준비 (선례가 있는 꼴만 쓴다):

| 순서 | 줄 | 선례 |
|---|---|---|
| S0 | `Store Sequence 790` | t615 p1 `ok`, 자동 Cue 1 생성 확인 |
| S1 | `Store Sequence 790 Cue 2` | t615 p3 `ok` |
| S2 | `Store Sequence 790 Cue 3` | 같은 꼴 |
| S3 | `Store Sequence 790 Cue 4` | 같은 꼴 |
| S4 | `ClearAll` | 여러 번 `ok` |

시험 (한 번에 한 줄씩, 줄마다 읽기):

| 순서 | 줄 | 기대와 해석 |
|---|---|---|
| C1 (대조군) | `Delete Cue 4 Sequence 790` | 앱의 v4 꼴을 790 에 그대로. **거절되면** 거절이 시퀀스 700 의 상태 탓이 아니라 이 꼴 자체라는 뜻이다. **성공하면** v4 거절은 700 의 상태 탓이었다. |
| K1 (후보) | `Select Sequence 790` | 매뉴얼 150행·벤더 테스트 18행 꼴. |
| K2 (후보) | `Delete Cue 3 /NoConfirm` | 기대: `ok`, 읽기에 790 의 Cue 3 이 없고 Cue 1·2 가 남음. Cue 4 는 C1 이 거절됐다면 남아 있고, C1 이 성공했다면 이미 없다. |
| K3 (후보, 변형) | `Delete Cue 3 /NC` | K2 와 같은 자리에 플래그만 바꾼 꼴. `/NC` 가 받는지 본다. |

**매 줄 뒤 읽기:** `DataPool/Sequences/790` 과 함께 **`DataPool/Sequences/700`·`701`·`702`·`703` 도 읽어**, K2 가 다른 시퀀스의 큐를 건드리지 않았는지 확인한다. 이것이 잘못된 대상 삭제를 잡는 장치다.

정리: `Delete Sequence 790 /NoConfirm`, `ClearAll`, 읽기로 790 이 `path segment not found` 인지 확인.

판단 기준:
- K2 `ok` 이고 790 의 Cue 3 만 사라지고 700–703 이 그대로 → 후보 꼴 채택 가능. 그때 `beat_grid_send.py:515` 를 "Select Sequence S" 한 줄 + "Delete Cue N" 으로 바꾸고, 재현 시험을 먼저 쓴다 (승인 목록 재생성 포함).
- K2 가 `Not allowed` → `Select` 후에도 거절. 시퀀스 상태 가설이나 다른 꼴을 다음 시험으로.
- K2 `ok` 인데 700–703 중 하나라도 바뀜 → **즉시 중단.** 선택 동작이 대상을 어긋나게 한 것이다. 콘솔 상태를 따로 기록하고 리드에게 보고.

## 5. 이 카드의 변경

- 코드 변경: **없음.** `beat_grid_send.py` 는 그대로다.
- 추가 파일: `.moai/reports/t618/progress.md` (이 파일).
- 콘솔 송신: 없음.
- 테스트: 문서 카드라 실행하지 않았다.

## 6. PR · CI · 머지

- PR·CI·머지 기록은 PR 페이지와 완료 보고에 있다. 이 문서에는 자기 CI 결과를 적지 않는다 (기록 커밋이 head 를 밀어서 적힌 결과가 곧 낡는다).
