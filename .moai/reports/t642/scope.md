# t642 범위 보고 — 재연결 뒤 끄기·미리보기 번호 소실

## 1. 주장

콘솔을 재연결(새 WebSocket)하면 박자 격자의 「끄기」(`beat_grid_preview_off`)와 「미리보기」(`beat_grid_preview`)가 반영 번호를 잃고 거절된다. 이 주장은 이번 실행에서 재현되었다.

- 원인 후보: `ChatSession._beat_grid_applied`는 연결(세션)마다 `None`으로 새로 만들어지고, 저장소(`SongTimelineStore`)에서 복원되지 않는다.
- 재연결하면 앱이 새 `ChatSession`을 만들기 때문에(`server/web/app.py` 396행), 콘솔에는 반영한 시퀀스가 남아 있어도 새 세션은 「아직 콘솔에 반영된 적이 없다」고 답한다.
- 재연결을 살아남는 것은 두 세션이 함께 쥔 `SongTimelineStore`뿐이다. t635가 곡별 스냅샷을 저장소로 옮긴 것과 같은 모양이다.
- 이 보고는 단위 층에서 재현한 결과다. 수정은 시작하지 않았다.

코드 위치(이번 실행에서 Read와 grep으로 확인한 줄 번호, `server/web/session.py`):

| 위치 | 줄 | 내용 |
|---|---|---|
| 상태 초기화 | 4160 | `self._beat_grid_applied: _BeatGridAppliedState \| None = None` |
| 쓰기 | 10762 | `beat_grid_apply`가 `_BeatGridAppliedState(sequence_numbers, cue_numbers)`를 기록 |
| 읽기 | 10841 | `_beat_grid_preview_commands`가 `applied is None`이면 `None`을 돌려준다 |
| 읽기 | 10897 | `beat_grid_preview`가 거절 사유를 고를 때 다시 읽는다 |
| 세션 생성 | `server/web/app.py` 396 | `session = ChatSession(`  |

## 2. 증거

실행한 명령과 종료 코드:

```
unset MOAI_KANBAN MOAI_KANBAN_ID MOAI_KANBAN_LABEL MOAI_KANBAN_LEAD_ADDR MOAI_KANBAN_SETTINGS_INJECTED && uv run pytest -q -rs server/tests/test_beat_grid_reconnect_t642.py; echo "exit=$?"
```

종료 코드: `exit=1` (pytest가 시험 실패로 종료)

pytest 출력 전문(그대로):

```
Using CPython 3.11.15
Creating virtual environment at: .venv
   Building ma3-copilot-server @ file:///Users/studiox/Documents/Claude/Code/AI-Lighting_Console/.claude/worktrees/agent-addce6e350c6fc41f
      Built ma3-copilot-server @ file:///Users/studiox/Documents/Claude/Code/AI-Lighting_Console/.claude/worktrees/agent-addce6e350c6fc41f
Installed 97 packages in 162ms
FF.                                                                      [100%]
=================================== FAILURES ===================================
_ TestOffAndPreviewAfterReconnect.test_off_after_reconnect_still_turns_off_applied_sequences _

self = <server.tests.test_beat_grid_reconnect_t642.TestOffAndPreviewAfterReconnect object at 0x10b4a1710>
tmp_path = PosixPath('/private/var/folders/3n/gsq1nhd14hng_6kbpdw2jdxw0000gn/T/pytest-of-studiox/pytest-2849/test_off_after_reconnect_still0')

    def test_off_after_reconnect_still_turns_off_applied_sequences(self, tmp_path):
        store, _session_a = _applied_session_a(tmp_path)
    
        # 재연결 — 같은 저장소 위의 새 ChatSession, 새 FakeConsole. 콘솔 쪽에는 반영한
        # 시퀀스가 그대로 남아 있다고 보는 것이 이 시험의 전제다.
        session_b, console_b, _approval_b, _audit_b = _new_session(tmp_path, store=store)
        event = session_b.beat_grid_preview_off()
    
        # 결함: 새 세션은 번호를 잃어 「아직 반영된 적이 없다」며 거절한다. ok 플래그와
        # 실제로 나간 명령 둘 다 단언한다 — 거절하면서 명령도 0줄이어야 정직하므로,
        # 고쳐진 뒤에는 ok=True 이고 Off Sequence 가 콘솔로 나가야 한다.
>       assert event["ok"] is True, f"재연결 뒤 끄기가 거절됨: {event.get('reason')}"
E       AssertionError: 재연결 뒤 끄기가 거절됨: 아직 콘솔에 반영된 적이 없어 끌 시퀀스가 없습니다.
E       assert False is True

server/tests/test_beat_grid_reconnect_t642.py:52: AssertionError
_ TestOffAndPreviewAfterReconnect.test_preview_after_reconnect_still_goes_to_applied_cues _

self = <server.tests.test_beat_grid_reconnect_t642.TestOffAndPreviewAfterReconnect object at 0x10b4a3190>
tmp_path = PosixPath('/private/var/folders/3n/gsq1nhd14hng_6kbpdw2jdxw0000gn/T/pytest-of-studiox/pytest-2849/test_preview_after_reconnect_s0')

    def test_preview_after_reconnect_still_goes_to_applied_cues(self, tmp_path):
        store, _session_a = _applied_session_a(tmp_path)
    
        session_b, console_b, _approval_b, _audit_b = _new_session(tmp_path, store=store)
        # 1마디는 반영한 곡의 BACK 트랙 큐가 실제로 담당하는 마디다(``_timeline`` 의 cues).
        event = session_b.beat_grid_preview(1)
    
        # 결함: 새 세션은 큐 번호를 잃어 미리보기를 거절한다. 고쳐진 뒤에는 ok=True 이고
        # 반영한 큐로 Goto Cue 가 콘솔로 나가야 한다.
>       assert event["ok"] is True, f"재연결 뒤 미리보기가 거절됨: {event.get('reason')}"
E       AssertionError: 재연결 뒤 미리보기가 거절됨: 아직 콘솔에 반영된 적이 없어 미리볼 시퀀스가 없습니다.
E       assert False is True

server/tests/test_beat_grid_reconnect_t642.py:66: AssertionError
2 failed, 1 passed in 1.27s
exit=1
```

대조군 PASS 줄: 출력 `FF.`의 세 번째 글자 `.`이다. 시험 파일의 정의 순서는 재연결 끄기, 재연결 미리보기, 대조군(같은 세션 끄기)이고, 실패 구간은 앞의 두 시험만 이름을 들었다. 따라서 통과한 하나가 `test_off_in_same_session_after_apply_control`이다. 이름별 PASS 줄은 `-v`로 따로 뽑지 않았다(지시된 실행 형태가 한 가지뿐이었기 때문이다). `-rs`는 건너뜀만 보여 주며, 이번 실행에는 건너뜀이 없었다.

## 3. 기준선 귀속

모두 이번 실행에서 이 작업 트리에 대해 잰 값이다.

| 명령 | 관측 |
|---|---|
| `git branch --show-current` | `worktree-agent-addce6e350c6fc41f` |
| `git rev-parse --short HEAD` (시험 파일 작성 전) | `31c11421` |
| `git status --short` (시험 파일 작성 전) | 출력 없음(깨끗함) |
| `git rev-list --count --left-right origin/main...HEAD` | `0	0` |
| `git status --short` (시험 파일 작성 뒤, 커밋 전) | `?? server/tests/test_beat_grid_reconnect_t642.py` |

참고: 배차 지시문은 브랜치를 `WT-beat-grid-reconnect`라고 적었으나, 실제 이 세션의 브랜치는 위 표의 `worktree-agent-addce6e350c6fc41f`였다. HEAD(`31c11421`)와 `origin/main`과의 거리(`0 0`)는 지시문과 일치한다. 브랜치 이름이 다른 이유는 확인하지 않았다.

## 4. 재현 시험 경로

시험 파일: `server/tests/test_beat_grid_reconnect_t642.py` (커밋 `f452c54f`)

| 시험 | 이번 실행 | 결함을 증명하는 관측값 |
|---|---|---|
| `TestOffAndPreviewAfterReconnect::test_off_after_reconnect_still_turns_off_applied_sequences` | FAIL | 새 세션의 `beat_grid_preview_off()`가 `ok=False`, 사유 「아직 콘솔에 반영된 적이 없어 끌 시퀀스가 없습니다.」 |
| `TestOffAndPreviewAfterReconnect::test_preview_after_reconnect_still_goes_to_applied_cues` | FAIL | 새 세션의 `beat_grid_preview(1)`이 `ok=False`, 사유 「아직 콘솔에 반영된 적이 없어 미리볼 시퀀스가 없습니다.」 |
| `TestSameSessionControl::test_off_in_same_session_after_apply_control` | PASS | 같은 세션에서 반영 직후 `beat_grid_preview_off()`가 `ok=True`이고 `Off Sequence` 명령이 `FakeConsole.executed`에 있다 |

구성: 한 `SongTimelineStore`를 공유하는 두 `ChatSession`. 세션 A에서 실제 `beat_grid_apply()`를 성공시킨 뒤(`ok=True`를 단언), 새 세션 B에서 끄기·미리보기를 부른다. 필드를 직접 쓰지 않고 실제 반영 경로로만 번호를 만든다. 실패 사유가 거절 문구(`ok` 플래그)에서 나왔으므로 ImportError나 픽스처 오류가 아니라 결함 자체 때문이다. 대조군이 통과하므로 하네스는 끄기 경로에 닿는다.

## 5. 수정 범위

수정이 건드릴 가능성이 큰 파일:

- `server/web/session.py`
  - 상태 초기화(4160행), `beat_grid_apply`의 쓰기(10762행), `_beat_grid_preview_commands`(10841행)와 `beat_grid_preview`(10897행)의 읽기.
  - 상태를 저장소 쪽으로 옮긴다면 같은 파일의 `SongTimelineStore`(3672행)도 대상이다. t635가 곡별 스냅샷을 저장소로 옮긴 방식과 같다. 이미 `beat_grid_allocation` / `set_beat_grid_allocation`(3746, 3749행)이 곡 열쇠별 할당 기록을 쥐고 있다.
- `server/tests/test_write_dispatch_census.py`: 디스패치 지점이 옮겨 가면 갱신이 필요하다. 현재 `_beat_grid_dispatch_preview`(179행 근처)가 항목으로 올라 있다.

콘솔 쓰기 질문에 대한 답은 예(YES)다. 끄기는 `Off Sequence N`을, 미리보기는 `Goto Cue c Sequence n`을 보내고, 둘 다 `_beat_grid_dispatch_preview`를 거친다(코드를 읽어 확인했다). 다만 이번 RED 시험에는 살아 있는 가짜 콘솔이 필요하지 않다. 인메모리 `FakeConsole`로 명령 문자열만 단언한다.

수정 단계에서 정해야 할 결정 지점(여기서는 고르지 않는다):

- (가) 상태가 사는 곳: 세션인지 저장소인지.
- (나) 「가장 최근 반영(곡을 가리지 않음)」으로 둘지, 곡별 열쇠로 나눌지.
- (다) 영속 할당 기록과의 관계: 할당 기록은 판정이 통과했을 때만, 그리고 소유했거나 새로 만든 트랙에 대해서만 쓰인다. 반면 `_beat_grid_applied`는 판정 통과 여부와 무관하게 쓰이고 모든 반영 트랙의 번호를 담는다. 둘의 범위가 다르다.
- (라) 메모리에만 두는 스냅샷으로 갈지, 파일로 남는 할당 기록을 쓸지.

(나)~(라)의 서술은 코드를 읽어서 얻은 것이다. 이번 실행에서 동작으로 확인한 것은 아니다.

## 6. 미검증 (Gaps)

이번 실행에서 관측하지 않은 것:

- 실제 WebSocket 재연결 경로. 이 시험은 단위 층이며 `app.py`의 재연결 처리 자체는 돌려 보지 않았다. 새 `ChatSession` 생성 지점이 396행이라는 것은 grep으로만 확인했다.
- 살아 있는 콘솔. 콘솔이 재연결 뒤에도 반영한 시퀀스를 그대로 쥐고 있다는 전제는 시험이 가정한 것이지 실측이 아니다.
- 전체 시험 묶음. 이 파일 하나만 돌렸다.
- 연결마다 새로 생기는 다른 필드: `_beat_grid_pool_slots`, `_beat_grid_empty_marks`, `_beat_grid_suggestions`, `_preview_approval`. 줄 번호만 grep으로 봤고, 재연결 뒤 동작은 재지 않았다.
- 수정 시도. 시도하지 않았다.

## 7. 잔여 위험

- 수정이 디스패치 센서스(`test_write_dispatch_census.py`)를 바꿀 수 있다.
- `test_beat_grid_send_t563.py`, t572, t578 계열의 기존 시험이 이 필드의 수명(연결 단위)에 기대고 있을 수 있다. 이번 실행에서는 돌리지 않았다.
- 미리보기 승인(`_preview_approval`)은 재연결 뒤 다시 묻는 것이 설계상 맞다. 수정이 승인 상태까지 옮기지 않도록 주의해야 하고, 이 시험은 승인을 기본 각본(모두 승인)으로 통과시키므로 그 동작을 지켜 주지 않는다.
- 두 번째 곡을 반영한 뒤 재연결하는 경우처럼 「가장 최근 반영」과 곡별 열쇠가 갈리는 경우는 이 시험이 다루지 않는다.

## 8. 카드 브랜치에서 재확인과 기준선 보완

섹션 2와 3의 실행은 서브에이전트가 자체로 만든 워크트리(`worktree-agent-addce6e350c6fc41f`)에서 이뤄졌다. 두 커밋(`f452c54f` 시험, `081ce38a` 보고)은 카드 브랜치 `WT-beat-grid-reconnect`에 `git merge --ff-only`로 옮겼다. 커밋 SHA는 그대로다.

옮긴 뒤 카드 워크트리에서 같은 시험을 한 번 더 돌렸다.

명령(한 번 실행, 환경 격리 형태):

```
unset MOAI_KANBAN MOAI_KANBAN_ID MOAI_KANBAN_LABEL MOAI_KANBAN_LEAD_ADDR MOAI_KANBAN_SETTINGS_INJECTED && uv run pytest -v -rs server/tests/test_beat_grid_reconnect_t642.py; echo "exit=$?"
```

관측(원문 발췌, 트레이스백의 위치 줄은 생략):

```
server/tests/test_beat_grid_reconnect_t642.py::TestOffAndPreviewAfterReconnect::test_off_after_reconnect_still_turns_off_applied_sequences FAILED [ 33%]
server/tests/test_beat_grid_reconnect_t642.py::TestOffAndPreviewAfterReconnect::test_preview_after_reconnect_still_goes_to_applied_cues FAILED [ 66%]
server/tests/test_beat_grid_reconnect_t642.py::TestSameSessionControl::test_off_in_same_session_after_apply_control PASSED [100%]
E       AssertionError: 재연결 뒤 끄기가 거절됨: 아직 콘솔에 반영된 적이 없어 끌 시퀀스가 없습니다.
E       assert False is True
E       AssertionError: 재연결 뒤 미리보기가 거절됨: 아직 콘솔에 반영된 적이 없어 미리볼 시퀀스가 없습니다.
E       assert False is True
========================= 2 failed, 1 passed in 1.59s =========================
exit=1
```

판독: 두 재연결 시험은 `ok` 단언에서 실패했고, 사유는 결함 메시지다. 대조군은 통과했다. 섹션 2의 서브에이전트 실행과 결과가 같다.

확인한 줄 번호(읽기와 grep으로 확인했다. 실행으로 확인한 것은 아니다):

- `server/web/app.py` 396행: `ChatSession(` 생성 (grep).
- `server/web/session.py` 3672행 `SongTimelineStore`, 3746행과 3749행 할당 기록 메서드 (grep).
- `server/web/session.py` 10762행의 `_beat_grid_applied` 쓰기는 10772행 `if verdict.passed:` 앞에 있다 (읽기). 따라서 판정과 무관하게 쓰인다.
- 할당 기록 쓰기(10812행)는 10772행 `if verdict.passed:` 블록 안에 있다. 10778~10811행 사이에 이 블록을 닫는 줄은 없다 (읽기).
- `server/web/session.py` 10792~10795행의 주석: 할당 기록은 원래 소유한 트랙과 이번에 실제로 만든 트랙만 적는다. 그렇지 않으면 다음 반영이 「기록한 시퀀스가 콘솔에 없다」로 거절된다 (읽기).
- `server/tests/test_write_dispatch_census.py` 179행: `_beat_grid_dispatch_preview` 항목 (grep).

기준선 보완:

- 통합 전 카드 브랜치: `WT-beat-grid-reconnect` @ `31c11421`, `git status --short` 비어 있음, `git rev-list --count --left-right origin/main...HEAD` = `0 0`.
- 통합 뒤: `WT-beat-grid-reconnect` @ `081ce38a`.

서브에이전트 자체 워크트리(`worktree-agent-addce6e350c6fc41f`)는 아직 남아 있다. 정리(폐기)는 리드의 통합과 원격 병합이 끝난 뒤에 한다.

상태: RED 확인, 수정 미착수, 「실행」 대기.
