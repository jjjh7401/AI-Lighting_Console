# t512 판정서 — AC-LDRHYTHM-012 측정 도구(승인본 대 송신본 비교기)

- 카드: t512 · SPEC-LDRHYTHM-001 · 레인 lane-3 · 브랜치 `WT-approval-diff` (기준 `cea25c04`)
- 범위: `.moai/reports/t512/` 만. `server/` 수정 0 · 콘솔 접촉 0 (기존 실기 산출물만 읽었다)
- 판정: **도구 준비 완료 — 카드 ①~⑤ 전부 충족.** 양성 대조 4/4 FAIL, 실데이터 4/4 PASS

## 0. 결과 한눈에

| 항목 | 입력 | 기대 | 결과 | 증거 |
|---|---|---|---|---|
| ⑤ 실데이터 음성 대조 | t506 v3 승인 파일 · `live_write_v3/audit` | PASS | **PASS** (10줄, sha 동일, 0·0) | `real_t506_v3.txt` |
| ④-1 승인 파일에 `Delete Sequence 14` 끼움 | `controls/c1_approval_injected.txt` | FAIL | **FAIL** — 승인 안 됨 1 | `control_c1_approval_injected.txt` |
| ④-2 송신 기록에서 한 줄 뺌 | `controls/c2_audit_line_removed/` | FAIL | **FAIL** — 승인 안 됨 1 (`Go Timecode 14`) | `control_c2_audit_line_removed.txt` |
| 추가: 송신 기록에 승인 밖 한 줄 끼움 | `controls/c3_audit_line_added/` (SaveShow, kind=backup) | FAIL | **FAIL** — 송신 안 됨 1 | `control_c3_audit_line_added.txt` |
| 추가: 송신 두 줄 순서만 바꿈 | `controls/c4_audit_swapped/` | FAIL | **FAIL** — sha 다름, 양방향 각 1 | `control_c4_audit_swapped.txt` |
| 추가 실데이터 | t498 run6 Rain 211 (119줄) | PASS | **PASS** | `real_t498_run6.txt` |
| 추가 실데이터 | t501 Rain 212 (237줄) | PASS | **PASS** | `real_t501_rain212.txt` |
| 추가 실데이터 | t501 Club Diver 213 (266줄) | PASS | **PASS** | `real_t501_clubdiver213.txt` |

모든 판정은 종료 코드로도 갈린다: PASS = 0, FAIL = 1 (마지막 실행: real 4건 0, control 4건 1).

추가 대조 두 개를 붙인 이유: 카드의 ④ 두 개는 둘 다 「승인됐는데 안 나감」 한 방향만 건드린다. c3 이 반대 방향(「승인에 없는데 나감」)을, c4 가 「줄 집합은 같고 순서만 다름」을 잡는지 보였다.

## 1. 송신 기록 원천 — 실측으로 정함 (카드 ①)

**결론: 앱 안전 게이트의 감사 로그 `audit-YYYYMMDD.jsonl` 중 `event == "executed"` 이고 kind 가 읽기 질의가 아닌 행.** 실제 나간 줄을 나간 순서대로, 한 줄에 한 행으로 담는다.

근거 (코드 읽기 + 기존 실기 산출물 실측):

- 코드: `server/safety/gate.py:926-943` — 게이트가 `self._console.execute(command)` 를 부른 **직후** `self._audit.log_executed(command, kind="command", ok=…, outcome=…)` 를 남긴다. 결과가 실패·미확인이어도 남긴다. `server/safety/audit.py:89-92`(@MX:ANCHOR)·`:268-279`(`log_executed`) 는 이 기록이 콘솔 송신과 1:1 이라는 불변식을 적어 두었다. SaveShow 백업(`gate.py:340-343`, kind=backup)과 플러그인 배포 하위 송신(`gate.py:872`, `deploy_of`)도 같은 함수로 남는다.
- 실측 (`survey_sources.py` 출력 `survey_sources.txt`, 이 카드에서 실행):

| 실행 | 감사 로그 행 종류 | 송신 행 수 | 대조 |
|---|---|---|---|
| t498 run6 Rain 211 실기 쓰기 | executed/command 119 · executed/props_query 478 · approved 1 | 119 | 승인 파일 119줄과 순서까지 동일 (t498 `run6_sent_vs_approved.txt` 와 일치) |
| t501 Rain 212 실기 쓰기 | executed/command 237 · props_query 478 · approved 1 | 237 | 승인 파일 237줄과 동일 |
| t506 v3 타임코드 실기 | executed/command 10 · props_query 68 · approved 4 | 10 | 승인 파일 10줄과 동일 |

- 두 번째 독립 기록과 대조: t506 v3 는 프로브 스크립트가 따로 남긴 `live_write_v3/steps.jsonl` 의 `kind=exec, fired=true` 10행이 있다. 감사 로그에서 재구성한 10줄과 **순서까지 같다** (`real_t506_v3_steps_crosscheck.txt`: `10` / `True`).

후보에서 뺀 것과 이유:
- `probe-*.jsonl`: 읽기 질의 전용(state_query·heartbeat) — 콘솔 상태를 바꾸지 않고, 하루 상한을 넘으면 버려진다(`audit.py` 머리말).
- 앱 경로의 `events.json`(`send_event`): UI 로 보내는 이벤트 흐름이라 송신 1:1 이라는 보장이 코드에 없다. 읽지 않았다.
- 응답기(콘솔 플러그인) 쪽 기록: 이 저장소 산출물에는 없다 — §4 미검증.

## 2. 도구 — `approval_vs_sent.py`

```
uv run python .moai/reports/t512/approval_vs_sent.py <승인 파일> <감사 로그 폴더|audit-*.jsonl> \
    [--out <재구성 파일>] [--since <ISO>] [--until <ISO>]
```

- 송신으로 세는 행: `event == "executed"` 이고 kind 가 `props_query/state_query/property_query/introspect_query/heartbeat`(읽기) 도 `deploy`(요약 행) 도 아닌 것. **모르는 kind 는 송신으로 센다** — 새 송신 종류가 생기면 빠지는 대신 「송신 안 됨」으로 걸린다.
- 승인 파일 정규형: 빈 줄과 `#` 주석 줄을 뺀 명령 줄 + 줄 끝 `\n`. 송신 재구성 파일도 같은 형식. **조건 (1) sha256 은 이 정규형끼리 비교한다.** 원본 sha256 과 「원본 == 정규형」도 함께 찍는다.
- 조건 (2)(3): `difflib.SequenceMatcher` 로 순서를 맞춘 뒤 남는 줄을 방향별로 찍는다. 이름은 AC 문면을 따랐다 — `송신 안 됨` = 승인 파일에 없는데 송신 기록에 있음(`SENT_NOT_APPROVED`), `승인 안 됨` = 승인 파일에 있는데 송신 기록에 없음(`APPROVED_NOT_SENT`). 이름만 보면 거꾸로 읽히기 쉬워서 영문 표식을 같은 줄에 붙였다.
- 송신 결과가 ok 가 아닌 행은 `WARN sends not ok` 로 따로 센다. **판정에는 안 넣었다**(AC 세 조건 밖). 실데이터 4건 모두 0.
- 실데이터 PASS 의 sha 를 도구 밖에서 다시 쟀다 (`real_t506_v3_shasum.txt`):

```
a68fadcacace1b79c994d2fc2ff3224be3a102feaba60f668f1cbfac6cf260a2  t512/rebuilt/t506_v3_approval_canonical.txt
a68fadcacace1b79c994d2fc2ff3224be3a102feaba60f668f1cbfac6cf260a2  t512/rebuilt/t506_v3_sent.txt
```

(정규형은 `grep -v '^#' | grep -v '^$'` 로 따로 만들었다. 원본 `commands_for_approval_v3.txt` 은 `# 묶음 n` 주석이 있어 원본 sha `cebe9242…` 는 다르다 — 정규형 비교인 이유.)

## 3. M2 에서 쓸 때 (리드·M2 레인에게)

1. **승인 파일은 주석·빈 줄 없는 맨 명령 줄로 만든다.** 그러면 「원본 == 정규형」이 True 가 되어 AC 문면의 `shasum -a 256 <승인 파일> <재구성 파일>` 이 원본 파일 그대로 같아진다. 주석이 꼭 필요하면 정규형 비교라는 사실을 판정서에 적는다.
2. **송신 실행마다 새 감사 폴더를 쓴다**(t498·t501·t506 실행 스크립트처럼 `audit_dir=OUT / "audit"`). 앱 기본 폴더 `server/audit_logs/` 는 하루치에 여러 실행이 섞이므로, 그걸 쓸 땐 `--since/--until` 로 창을 잘라야 한다.
3. 묶음 단위 승인이면 묶음마다 승인 파일 하나 · 실행 하나로 돌리거나, 묶음 승인 파일들을 순서대로 이어 붙인 파일 하나와 그 실행의 감사 로그 전체를 비교한다.
4. 백업이 실제로 나가면(SaveShow, kind=backup) 승인 파일에 없으므로 FAIL 이 난다(c3 이 그 모양). t498 이후 실행 스크립트는 백업을 「기록만」으로 바꿔 끼워 실제로 안 보냈다 — M2 도 그렇게 하거나, 백업 줄을 승인 파일에 넣어야 한다.

## 4. 미검증 (안 잰 것)

- **응답기 쪽 수신 기록과의 대조는 안 했다.** 감사 로그는 앱이 「보냈다」고 남긴 기록이지 콘솔이 받은 기록이 아니다. 응답기 audit 이 이 저장소 산출물에 없다.
- 앱이 송신 직후·기록 직전에 죽는 경우(송신됐는데 행이 없음)는 재현하지 않았다.
- `--since/--until` 창 자르기는 실데이터에서 써 보지 않았다(4건 모두 실행 전용 폴더라 필요 없었다).
- 배포 하위 송신(`deploy_of`) 행이 실제로 섞인 로그로는 돌리지 않았다 — 코드 읽기로만 송신으로 센다.
- t498·t501 의 `approval_request_1.txt` 는 앱이 낸 승인 요청 사본이다. 사람이 승인한 파일과 같은지는 t498 판정서(A4)를 믿었다.

## 5. 잔여 위험

- 비교는 바이트 단위 정확 일치다. 앱이 송신 직전에 줄을 바꾸는 단계(기구 목록 재작성 등)가 생기면 FAIL 이 난다 — 의도한 동작이지만, 그때는 승인 파일을 「바뀐 뒤」 내용으로 다시 승인받아야 한다(AC 문면 그대로).
- kind 목록(`READ_KINDS`)은 지금 `gate.py` 기준이다. 새 읽기 질의 kind 가 생기면 송신으로 잘못 세어 FAIL 이 난다(잡는 쪽으로 틀린다).

## 6. 파일

- 도구: `approval_vs_sent.py` · 대조 생성: `make_controls.py` · 원천 판독: `survey_sources.py`
- 실데이터 출력: `real_t506_v3.txt` · `real_t506_v3_shasum.txt` · `real_t506_v3_steps_crosscheck.txt` · `real_t498_run6.txt` · `real_t501_rain212.txt` · `real_t501_clubdiver213.txt`
- 양성 대조: `controls/` (입력) · `control_c1~c4_*.txt` (출력)
- 재구성 파일: `rebuilt/t506_v3_sent.txt` · `rebuilt/t506_v3_approval_canonical.txt`
