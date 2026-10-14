✂──── 여기부터 복사 ────✂

ultrathink. SPEC-LDBARMAP-004 plan 진입.
applied lessons: lesson-check-the-baseline-before-reading-the-gauge, feedback-search-the-code-before-believing-a-card, lesson-a-code-reading-inference-is-not-a-measurement, lesson-calibrate-the-instrument-against-ground-truth-first, lesson-a-number-needs-its-provenance-class, feedback-verify-over-throughput-and-hand-off-before-clear

전제 검증:
1) 워크트리 .claude/worktrees/WT-barmap-song-match, 브랜치 WT-barmap-song-match. HEAD 는 cdd473d6 이상이다. git status --short 가 비어 있다 (재개 기록 resume.md 는 커밋돼 있다)
2) 감독 결정 「C + B 길이만」 을 이 파일의 「감독 결정」 절에서 다시 읽었다
3) origin/main 이 이 브랜치보다 앞서 있으면 merge origin/main 으로 가져온다. rebase 하지 않는다 (이미 푸시된 브랜치다)
4) SPEC id 는 main 만이 아니라 모든 원격 브랜치에서 비었는지 확인한 뒤 정한다. SPEC-LDBARMAP-003 은 t648 브랜치(WT-barmap-entry-ui)에 있다. SPEC-LDBARMAP-004 는 main 에 없다

실행: 이 파일의 「측정」 절을 먼저 한다. 측정은 plan 전에 끝내고, 결과는 .moai/reports/t649/measure.md 에 적는다. 그다음 「다음 할 일」 1번부터 시작한다. plan 작성은 manager-spec 에 위임한다.

머지 후: plan-audit PASS 를 받으면 착수 승인을 리드에게 요청한다. 승인 전에는 run 단계에 들어가지 않는다.

✂──── 여기까지 복사 ────✂

---

## 감독 결정 (2026-10-14, 리드 AskUserQuestion 결과)

- 결정: 「C + B 길이만」
- C 의 화면 표시(파일명)는 t648(lane-1)이 맡는다. t649 는 서버 쪽만 한다.
  - 파일명과 sha256 을 지도 밖 키에 남긴다.
  - 저장 응답 문구에 파일명과 타임라인 제목을 함께 싣는다.
- B 는 길이만 본다. BPM 대조는 뺀다. REQ-LDBARENTRY-011 은 그대로 둔다.
  - 타임라인에 길이 정보가 없으면 「확인할 수 없음」으로 통과시키고, 그 사실을 문구에 적는다.
- 허용 오차는 숫자를 고르기 전에 실제 곡으로 잰다(편집판 길이 차이 포함). 근거가 없으면 숫자를 정하지 말고 리드에게 보고한다.
- 다음 흐름: SPEC(LDBARMAP-004 정도) plan → plan-audit → 착수 승인을 리드에게 요청.
- 47% 라서 plan 도중 50% 를 넘을 수 있다. 넘기 전에 이 파일을 쓰고 멈춘다.

## 현재 상태 (이 파일을 쓴 시점에 확인한 것)

- 워크트리: `.claude/worktrees/WT-barmap-song-match`, 브랜치 `WT-barmap-song-match`.
- 커밋 `cdd473d6`: docs(t649) 범위 보고, `.moai/reports/t649/scope.md`. 원격 브랜치와 같다(ls-remote 일치, 차이 0 0).
- origin/main 은 `b8ac5719` 이후 2커밋 앞서 있다(`git rev-list --count --left-right origin/main...HEAD` → `2 1`). 이 브랜치에만 있는 커밋은 `cdd473d6` 하나다.
- 재개 기록(이 파일)은 리드 요청으로 커밋·푸시했다.
- 코드 변경은 없다.
- 범위 보고 요약은 리드에게 보냈다(받은 편지함에 들어간 것까지 확인). 이번 감독 결정의 수신 확인은 이 파일을 쓴 뒤 보낸다.

## 코드 근거 (scope.md 에서 옮김, 기준 b8ac5719; 쓰기 전에 줄을 다시 연다)

- `analyse_bar_map`: `server/web/session.py:9478`. 곡 열쇠 기억 `9535`, 음원 디코드 `9538`, 곡 열쇠 재확인 `9557-9558`. 주석: 처리 순서 `9483-9485`, BPM 확정 상태 금지 `9495-9496` (REQ-LDBARENTRY-011).
- 곡 열쇠 `(song_title, sequence_number)`: `session.py:10362`.
- 음원 업로드와 sha256: `session.py:13748`, `13773-13774`.
- 연결 기록 쓰기: `session.py:13787-13789` (`SongAudioLinkStore.link`). 조회: `server/web/song_audio_store.py:95` (`resolve`). sha256 으로 거꾸로 찾는 메서드는 없다.
- 지도 최상위 키는 여섯 개로 고정: `server/audio/bar_map_store.py:54-56`. 다른 키는 거절 `:175`. 지도 안에 식별 정보를 넣지 않는다.
- 길이: `server/audio/bar_map.py:214-218` (`_decode_mono_audio` 가 계산). `BeatGridResult` `:105` 에는 길이가 없다. `detect_beat_grid` `:221`.
- 타임라인 `bpm` 은 `_song_bpm` 과 같은 객체: `session.py:4300-4301`. 그래서 BPM 을 읽으면 확정 상태를 읽는다.
- 디자인 경로는 `total_duration_ms` 를 채우지 않는다고 `session.py:1505` 주석이 적는다. `sugar_timeline.py:475` 는 생산 코드인지 열어 보지 않았다.
- t648 명세(브랜치 `WT-barmap-entry-ui`, `.moai/specs/SPEC-LDBARMAP-003/spec.md`): REQ-LDBARUI-006 (78행, 저장 성공 문구에 파일명), REQ-LDBARUI-013 (85행), 위치 설명 (102행), E3 문장 (167행).
- 메인 화면의 파일명 표시: `ui/src/App.tsx:1031-1033`.

## 측정 (리드 보고 2026-10-14, plan 전에 새 세션에서 수행)

리드가 `find` 로 확인한 자료다(저장소 밖 worktrees 는 제외). 이 세션은 컨텍스트 52%에서 멈춰서 측정하지 않았다.

- 곡 10개: Cut and Run, Rain, Ice cream, Let's Dance, Morning, Too Cool, LoveMe, 걸그룹DinoDino_C_max최고품질.wav, scott-buckley-neon, Club Diver. 걸그룹 파일만 `.wav`, 나머지는 `.mp3`.
- 위치 (확인한 것): 이 워크트리에는 `src/sample music/` 이 없고 git 에도 추적되지 않는다. 리드 보고로는 주 체크아웃(`/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/src/sample music/`)에 있다. 읽기만 하고 옮기거나 쓰지 않는다.
- `LOVE ATTACK.mp3`: 리드 보고로는 `.moai/reports/t505/` 아래다. 이 워크트리의 `t505` 목록(추적 파일)에는 없다. `evidence/` 안이거나 주 체크아웃에 있을 수 있다. 측정 전에 `ls` 로 위치를 확인한다.
- 편집판 쌍은 저장소에 없다. 쌍을 지어내지 않는다. 편집판 측정 칸은 「편집판 측정 불가」로 공백 처리한다.
- 주의: `LoveMe.mp3` 는 디코더마다 길이가 다르다 (카드 t413). 길이 기준을 잡기 전에 이 차이부터 확인한다.
- 잴 것: 곡마다 (1) 디코더가 낸 길이, (2) 그 곡 타임라인의 길이 또는 마지막 구간 시작과의 차이. 타임라인이 없는 곡은 「없음」으로 적는다. 디코더는 앱이 쓰는 `server/audio/bar_map.py` 의 `_decode_mono_audio` 를 기본으로 하고, 설치된 다른 디코더가 있으면 함께 잰다.
- 타임라인 위치는 아직 모른다. 곡 이름으로 `git grep` 해서 결과 수를 먼저 센다.
- 기록: 결과는 `.moai/reports/t649/measure.md` 에 쓴다. 명령과 출력을 그대로 남기고, 숫자마다 디코더 이름과 버전, 파일 경로, 커밋을 같은 줄에 적는다.
- 허용 오차: 편집판 자료가 없어서 근거 있는 숫자를 정하지 못할 가능성이 크다. 근거가 없으면 숫자를 정하지 말고 리드에게 보고한다 (감독 결정).

## 다음 할 일 (순서)

1. 「전제 검증」 네 가지를 한다.
2. origin/main 이 앞서 있으면 `merge origin/main` 으로 가져온다. rebase 하지 않는다.
3. SPEC id 를 정한다. 004 가 모든 원격 브랜치에서 비었는지 확인하고, 비었으면 쓴다. 다르면 리드에게 묻는다.
4. plan 을 manager-spec 에 위임한다. 범위는 서버만이다.
   - 음원 식별 키: 지도 밖 키에 파일명과 sha256 을 저장한다. `validate_bar_map` 과 지도 최상위 키는 건드리지 않는다.
   - 응답 문구: 저장 성공 응답에 파일명과 타임라인 제목을 함께 싣는다. 형식은 t648 REQ-LDBARUI-006 과 맞춘다.
   - 길이 검사: 디코드 길이를 결과에 싣고, 타임라인에 길이가 있으면 비교한다. 없으면 「확인할 수 없음」으로 통과시키고 문구에 적는다.
   - BPM 대조는 넣지 않는다.
   - Tier 는 파일 수로 정한다 (spec-workflow.md: S 는 2파일, M 은 3파일, L 은 5파일).
5. 허용 오차를 정한다. 실제 곡과 편집판 쌍의 길이 차이를 잰다. 측정 자료가 저장소에 없으면 리드에게 목록을 요청한다. 근거가 없으면 숫자를 정하지 말고 리드에게 보고한다.
6. t648 과 응답 계약을 맞춘다. 파일명을 응답의 어느 자리에 싣는지 t648 명세와 대조한다.
7. plan-audit 을 요청하고 PASS 를 확인한다.
8. 리드에게 착수 승인을 요청한다 (SendMessage). 승인 전에는 run 단계로 가지 않는다.

## 금지와 주의

- 금지: `moai session list`, `moai todo`, 맨 `git stash`, `git add -A`, 콘솔 쓰기.
- `git add` 는 경로를 명시한다. 커밋과 푸시 전에 HEAD 와 브랜치를 다시 읽는다.
- 워크트리 밖을 가리키는 git 명령(변수로 `-C` 를 지정하는 형태)은 도구가 막는다. 명령은 워크트리 안에서 평범한 형태로 실행한다.
- 줄 번호는 움직인다. 쓰기 전에 다시 연다.
- 탐색 에이전트의 보고는 근거가 아니다. 줄을 직접 열어 확인한다.
- 재지 않은 숫자는 쓰지 않는다. 숫자마다 출처를 같은 줄에 적는다.

## 메모

- 메모리 색인: `project_ldbarmap_004_plan_t649_handoff.md` (MEMORY.md 첫 줄 아래).
- 이 파일은 재개 기록이다. 리드 요청으로 커밋·푸시했다.
