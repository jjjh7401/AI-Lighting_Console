# 카드 t549 — SPEC-LDBEAT-001 M4(콘솔 송신 경로) run-verdict

cycle_type=tdd. Tier M. 기준 `af00ffb2`(origin/main). 콘솔 접촉 0건, 콘솔 쓰기 0건.

## 환경 불일치 고지(중요)

배차서는 작업 위치를 `.claude/worktrees/t549`(브랜치 `WT-ldbeat-console-send`)로
지정했으나, 이 세션은 실제로 `.claude/worktrees/agent-a96dd8e7370c1ff59`(자동
생성된 범용 에이전트 워크트리, 브랜치 `worktree-agent-a96dd8e7370c1ff59`)에
격리돼 있었다. 도구 수준 가드가 `.claude/worktrees/t549`로의 `cd`/`git -C`
리다이렉트를 거부했다(교차 워크트리 격리). `WT-ldbeat-console-send` 브랜치는
이미 다른(잠긴) 워크트리 `.claude/worktrees/t549`에 체크아웃돼 있어 이
세션에서 같은 이름으로 재사용할 수도 없었다. 두 워크트리 모두 HEAD는
`af00ffb2`로 동일했다(검증됨). 결과: 모든 작업은 `agent-a96dd8e7370c1ff59`
워크트리/브랜치에서 이뤄졌다 — 오케스트레이터는 머지 시 **이 워크트리를**
가져가야 한다(`.claude/worktrees/t549`가 아니다). 카드 ID(t549)는 커밋
메시지에 전부 포함돼 있다.

## 산출물

| 파일 | 역할 |
|---|---|
| `server/design/approval_vs_sent.py` | `.moai/reports/t512/approval_vs_sent.py` 로직의 앱 경로 승격(REQ-LDBEAT-011) |
| `server/design/beat_grid_emit.py` | 박자 격자 전용 새 에미터 + M1 의존 게이트(REQ-LDBEAT-001/003/013) |
| `server/design/send_approval.py` | 승인 단위 — 쓰기 배치당 1개, 미리보기 세션당 1회(REQ-LDBEAT-012, AC-LDBEAT-002(b)/015) |
| `server/tests/test_approval_vs_sent_t549.py` | 10개 시험 |
| `server/tests/test_send_approval_t549.py` | 7개 시험 |
| `server/tests/test_beat_grid_emit_t549.py` | 27개 시험 |
| `.moai/reports/t549/gen_sample.py` | LOVE ATTACK 샘플 배치 생성 스크립트(증거용) |
| `.moai/reports/t549/sample-approval-batch.txt` | 그 스크립트의 산출물(58줄) |

## E8 — RED 검증 (구현 전 실패 확인, 구현마다 개별 캡처)

```
$ uv run --quiet pytest server/tests/test_approval_vs_sent_t549.py -q
ModuleNotFoundError: No module named 'server.design.approval_vs_sent'
1 error in 0.07s

$ uv run --quiet pytest server/tests/test_send_approval_t549.py -q
ModuleNotFoundError: No module named 'server.design.send_approval'
1 error in 0.07s

$ uv run --quiet pytest server/tests/test_beat_grid_emit_t549.py -q
ModuleNotFoundError: No module named 'server.design.beat_grid_emit'
1 error in 0.09s
```

세 모듈 모두 테스트를 먼저 작성해 RED(ImportError, 모듈 부재)를 확인한
뒤에만 구현했다 — 구현이 테스트보다 먼저 존재한 적이 없다(TDD
Test-First Anti-Cheat 불변식 i/ii 준수).

## GREEN 검증 (구현 후)

```
$ uv run --quiet pytest server/tests/test_approval_vs_sent_t549.py server/tests/test_send_approval_t549.py server/tests/test_beat_grid_emit_t549.py server/tests/test_app_movement_t548.py server/tests/test_beat_grid_t548.py server/tests/test_beat_grid_t537.py server/tests/test_beat_grid_t532.py server/tests/test_beat_grid_probes_t537.py server/tests/test_position_fx.py server/tests/test_position_fx_dedupe_t542.py -q
........................................................................ [ 32%]
........................................................................ [ 64%]
........................................................................ [ 96%]
.........                                                                [100%]
225 passed in 1.54s
```

신규 44개(10+7+27) + 기존 관련 181개 전부 PASS, 회귀 0건.

## Lint/format

```
$ uv run --quiet ruff check server/design/approval_vs_sent.py server/design/send_approval.py server/design/beat_grid_emit.py server/tests/test_approval_vs_sent_t549.py server/tests/test_send_approval_t549.py server/tests/test_beat_grid_emit_t549.py
All checks passed!

$ uv run --quiet ruff format --check <같은 파일들>
6 files already formatted
```

## AC-LDBEAT-012 — PRESERVE diff 0줄 확인

```
$ git diff af00ffb2 -- server/director/emit.py ui/src/components/CueSheetTimeline.tsx server/looks/songcue.py
(출력 없음, 0줄)
```

songcue.py의 기존 함수 본문(`_timecode_commands`/`_ascii_label`)은 전혀
수정하지 않았다 — `_ascii_label`/`_format_seconds`를 import해 재사용만
했다. `_timecode_commands` 자체는 재사용하지 않았다(아래 §Gaps 참조).

## E1 — AC 매트릭스

| AC | 검증 | 결과 |
|---|---|---|
| AC-LDBEAT-006(server-side 부분) | `.moai/reports/t512/approval_vs_sent.py`를 앱 경로로 포팅, 새 비교 로직 미발명. `test_approval_vs_sent_t549.py` 10개(c1~c4 합성 음성 대조 FAIL, 일치 승인+감사 PASS, READ_KINDS/SUMMARY_KINDS 제외, import 전수 조사) | PASS |
| AC-LDBEAT-012 | `git diff af00ffb2 -- server/director/emit.py ui/src/components/CueSheetTimeline.tsx server/looks/songcue.py` → 0줄 | PASS |
| AC-LDBEAT-002(b) | `PreviewApprovalSession` — `approve()` 1회 뒤 `authorize_preview()` 반복 호출 전부 `True`(세션-1회 승인). 쓰기 승인 개념 자체가 이 클래스에 없음을 `hasattr` 로 확인 | PASS(순수 상태 객체 단위 — 서버 세션 배선은 범위 밖, 아래 §Gaps) |
| AC-LDBEAT-015 | `build_write_approval_batch` — N=3칸 배치에도 아티팩트 1개, 커맨드 줄 수 == 칸 전체 합, sha256 = 전체 텍스트의 sha256 | PASS |
| AC-LDBEAT-001(서버측 부분) | `blocked_m1_items_for_cue` + `emit_beat_grid_write_bundle` — M1 미확인 항목에 의존하는 칸은 거절(reason에 "미확인 항목 N개(목록)"), PASS면 통과. LOVE ATTACK 실데이터 통합 시험으로 블록 목록을 아래 §블록 목록에 전수 확인 | PASS |

## 게이트가 막은 LOVE ATTACK 칸 전체 목록 (실측, `gen_sample.py` 실행 결과)

`probe_results`는 실제 `progress.md`를 `read_m1_probe_results_from_path`로
읽은 **살아있는** 값이다(①⑧만 PASS, 나머지는 미확인/부분/움직임 없음) —
손으로 옮긴 표가 아니다.

**효과 프리셋 의존(④ 미확인) — 8칸 전부 거절**:

| 트랙 | 마디 |
|---|---|
| BACK | 3, 7, 18, 22 |
| SIDE-ALL | 11, 14 |
| MOVER-U | 14 |
| MOVER-D | 14 |

**앱 무빙(`app_movement`) 의존(⑤⑦⑨ 미확인) — 4칸 전부 거절**:

| 트랙 | 마디 |
|---|---|
| MOVER-U | 11, 18 |
| MOVER-D | 7, 22 |

**거절되지 않고 내용이 있는 칸(6칸)**:

| 트랙 | 마디 | 내용 |
|---|---|---|
| FOH | 7 | 디머 프리셋 1.1 리콜 |
| WASH-ALL | 7, 14 | 밝기 값(40%, 25%) |
| MOVER-D | 18 | 위치 프리셋 2.1 리콜(정적, app_movement 없음) |
| BLIND | 17, 18 | 디머 프리셋 1.6 리콜 · 밝기 값(100%) |

**추가 발견 — 8트랙을 타임코드 하나에 몰면 전부 거절된다**: LOVE ATTACK은
콘솔 그룹 트랙 8개(FOH·WASH-ALL·BACK·SIDE-ALL·MOVER-U·MOVER-D·BLIND·
STROBE)다. M1 ①이 구조로 확인한 실제 최대는 6개(`progress.md` "TC 30 에
시퀀스 트랙 6개(228→233)")다 — ①이 PASS라 해도 이 수를 넘는 묶음은
측정 범위 밖이라고 판단해, 이 모듈은 독자적으로 `MEASURED_MAX_TIMECODE_
TRACKS = 6`을 두어 8트랙을 한 타임코드에 몰면 **트랙 레벨에서 전부**
거절한다(배차서의 매핑을 "느슨하게 풀지 않는" 방향 — 오히려 더 엄격하게
좁혔다, `test_all_eight_love_attack_tracks_on_one_timecode_exceeds_
measured_max` 로 확인). 샘플 배치는 타임코드를 둘(30/31)로 나눠 이 상한을
피했다.

## 판단 콜 — feature→M1 항목 매핑(배차서가 준 것을 그대로 썼지만, 다음은 이 레인의 판단)

1. **⑩⑪은 이 게이트에서 뺐다.** 배차서는 "dimmer phase spread → ⑩"을
   들었지만, `server/design/beat_grid_probes.py`의 `DEFAULT_PROBE_IDS`는
   1~9만 추적하고 그 모듈 독스트링이 "⑩⑪은 … 이 SPEC의 게이트 대상이
   아니다"라고 명시한다 — REQ-LDBEAT-001 조문 자체도 "9개"라고 적는다.
   이 모듈은 현재 "디머 위상 펼침"이라는 별도 기능을 내지 않으므로(밝기는
   `brightness_value_commands`의 값 지정뿐, 위상 펼침은 `app_movement`
   쪽에만 있고 그건 ⑨에 이미 걸려 있다) 이 판단이 결과를 바꾸지 않았다.
2. **효과 프리셋 **리콜**(정적 번호 호출)을 ④에 건 것은 보수적 해석이다.**
   M1 ③이 "`At Preset` 접두 없는 형태는 콘솔이 받는다"를 이미 구조로
   확인했으므로, 단순 리콜 자체는 ③을 통과한 것으로 볼 여지가 있다.
   그러나 배차서가 명시한 매핑("effect preset recall → ④")을 그대로
   따랐다 — ④("효과 프리셋이 스피드마스터·Measure를 지니는지")가
   미확인인 한, 효과 프리셋을 통한 **박자 동기화**가 의도대로 되는지는
   증명되지 않았다고 보수적으로 읽었다. 이 해석을 완화하면(리콜만으로
   충분하다고 보면) BACK/SIDE-ALL/MOVER-U/MOVER-D의 효과 8칸이 전부
   허용으로 바뀐다 — 감독/리드가 재검토할 지점이다.
3. **정적 위치·색 프리셋 리콜, 디머 프리셋/값 지정은 M1에 걸지 않았다.**
   ③은 프리셋 **수정** 전파에 대한 항목이지 리콜 자체가 아니다고 읽었다.

## 안 잰 것(Gaps)

- **이 에미터가 낸 명령은 콘솔에 한 줄도 보내지 않았다** — 전부 순수
  함수 호출과 파일 I/O(progress.md 읽기)뿐이다.
- **`_timecode_commands`(songcue.py) 함수 자체는 재사용하지 못했다** —
  그 함수는 `SongCueBundle`(섹션-큐 곡 전용 데이터클래스)에 결합돼
  있어 박자 격자의 트랙·칸 모양과 맞지 않는다. 대신 그 함수가 내는
  **문자열 모양**(`Store Timecode N`/`Set Timecode N Property 'Name' …`/
  `Assign Sequence S At Timecode N`)을 소스 재확인(`grep -n
  "^def _timecode_commands"`)으로 검증한 뒤 손으로 재현했다 — `_ascii_
  label`/`_format_seconds`는 직접 import해 그대로 재사용했다(songcue.py
  diff 0줄 유지).
- **"Store Cue" 뒤 "ClearAll" 삽입은 이 레인의 설계 판단**(배차서가
  명시하지 않음) — 다음 칸을 쌓기 전에 프로그래머 상태를 비워야
  겹침(이전 칸 속성이 다음 칸에 새는 것)을 막을 수 있다고 판단했다.
  t538이 `ClearAll`을 실기에서 쓴 전례(`progress.md:153`)를 인용한다.
  이 삽입이 실제 콘솔에서 올바른지는 **실기로 재지 않았다**.
- **다섯 개 PRESERVE 파일**(`server/director/emit.py`,
  `ui/src/components/CueSheetTimeline.tsx`, `server/looks/songcue.py`,
  `server/design/cue_sheet_edit.py`, `console/lua/**`) diff 0줄은 확인
  했으나, **이 에미터가 생성한 명령을 실제로 UI/서버 엔드포인트에 연결
  하는 배선은 이 카드 범위 밖**이다(카드 본문 Deliverables 5 — "Wire
  nothing to the real console", 명시적 제외). 그래서 "AI 제안 → 「적용」
  → 이 에미터 → 콘솔"의 전체 경로는 여전히 미배선이다.
- **`PreviewApprovalSession`의 서버 세션 배선**(실제 HTTP 세션에 이
  객체를 어디에 두는지)은 설계하지 않았다 — 순수 상태 객체만 만들었다.
  REQ-LDBEAT-012(b)의 "세션 시작 1회 승인"을 실제 웹 세션에 연결하는
  일은 M4의 나머지 몫(UI/서버 엔드포인트 배선)으로 남는다.
- **승인=송신 비교(REQ-LDBEAT-011) 통합**: `approval_vs_sent.py`는
  승격됐지만, 이 M4 에미터가 실제로 송신한 뒤 그 비교를 **호출**하는
  배선은 만들지 않았다(비교 로직 자체만 포팅 — 호출 지점은 카드 범위
  밖인 "AI 제안→적용→전송" 전체 배선과 함께 남는다).
- **8트랙을 전부 담으려면 타임코드를 둘 이상 쓰거나 M1 ①을 6개 초과로
  재확인해야 한다** — 이 레인은 어느 쪽도 결정하지 않았다(감독/리드
  판단 사항, 위 §추가 발견 참조).
- **ruff/pytest는 이 레인이 영향을 줄 수 있는 파일로만 좁혔다** — 전체
  스위트(`uv run pytest server/`)는 돌리지 않았다(카드 §D 제약 — lane-
  local 검증만).
- **커밋 전 `git fetch`로 origin 분기 여부는 재확인하지 않았다** — 이
  세션이 격리된 워크트리에서 일했고, 오케스트레이터가 머지 전 재확인할
  것으로 본다.

## 아직 커밋하지 않은 상태

이 레인은 HEAD `af00ffb2`에서 신규 파일만 추가했다(PRESERVE diff 0줄,
`git status --short`로 확인된 미추적 파일 6개 + 이 리포트 디렉터리). 커밋은
이 verdict 작성 직후 진행한다 — 실제 SHA는 작업 응답 본문에 기록한다.
