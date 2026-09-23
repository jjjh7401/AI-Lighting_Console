# G6/G5 수정 후 최종 13x8 게이트 행렬 — 카드 t439

생성 명령(실행 트리: `.claude/worktrees/agent-ad70efd1e62c4316f`, HEAD 3a186fec 위에서 본 카드 커밋 적용 후):

```
uv run python3 -c "
import json
from server.concept.gates import evaluate_song, GATE_NAMES

data = json.loads(open('server/tests/fixtures/pilot_baseline.json', encoding='utf-8').read())
songs = [s for s in data if 'error' not in s]

def fmt(v):
    if v is True: return 'PASS'
    if v is False: return 'FAIL'
    return 'n/a'

pass_c=na_c=fail_c=0
for song in songs:
    result = evaluate_song(song)
    for gate in GATE_NAMES:
        v = result[gate].passed
        if v is True: pass_c+=1
        elif v is None: na_c+=1
        else: fail_c+=1
print('PASS',pass_c,'NA',na_c,'FAIL',fail_c)
"
```

## 요약

- 구 기준선(프로토타입 `final_integrated.py` 직접 실행) — PASS 98 · n/a 6 · FAIL 0.
- 구 기준선은 과대 — G6 8곡 PASS 전부가 프로토타입 자신의 `bridge_viol` 공식이 REQ-029의 **예외** 조건을 위반 조건으로 뒤집어 셈해 생긴 거짓 PASS다. 정정 기준선 = 98 − 8 = **90**.
- 이 카드(t439)에서 실측한 값 — **PASS 89 · n/a 6 · FAIL 9** (합계 104 = 8곡 × 13게이트).
- 정정 기준선(90)과 실측(89)의 차이는 1 — scott-buckley-neon.mp3의 G5가 density.py Intro 복원(본 카드 수정) 후에도 남는 **실제 위반**이기 때문이다(아래 "G5" 절 참고). 배차서 지시("다른 값을 건드려 PASS를 만들지 마라")에 따라 이 FAIL은 그대로 두었다.
- FAIL 9건 전부의 원인은 규명됐고, 전부 **실제 위반**이다(날조 없음) — G6 8건(팔레트 색 배타성 설계), G5 1건(neon의 Intro·Bridge 그룹 구성 동일).

## 최종 8×13 행렬 (본 카드 수정 후 실측)

| 곡 | G1 | G2 | G3 | G4 | G5 | G6 | G7 | G8 | G9 | G10 | G11 | G12 | G13 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Club Diver.mp3 | PASS | PASS | PASS | PASS | PASS | **FAIL** | PASS | PASS | PASS | n/a | PASS | PASS | PASS |
| Cut and Run.mp3 | PASS | PASS | PASS | PASS | PASS | **FAIL** | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| Ice cream.mp3 | PASS | PASS | PASS | n/a | PASS | **FAIL** | PASS | PASS | PASS | n/a | PASS | PASS | PASS |
| Morning.mp3 | PASS | PASS | PASS | PASS | PASS | **FAIL** | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| Rain.mp3 | PASS | PASS | PASS | PASS | PASS | **FAIL** | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| Too Cool.mp3 | PASS | PASS | PASS | PASS | PASS | **FAIL** | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| scott-buckley-neon.mp3 | PASS | PASS | PASS | PASS | **FAIL** | **FAIL** | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| 걸그룹DinoDino_C_max최고품질.wav | PASS | n/a | n/a | n/a | PASS | **FAIL** | PASS | PASS | PASS | PASS | PASS | PASS | PASS |

집계: PASS 89 · n/a 6 · FAIL 9 · 합계 104.

## G6 — "공유 보조색" 조사 결과와 실측 위반 (감독 결정 1)

감독 결정 1의 지시("공유 보조색도 공통색으로 친다")를 실제로 적용하려면, `server/concept/gates.py`의 `_concept_cues` 어댑터가 각 큐의 실제 emit 색 집합(주색+보조색)을 `check_adjacent_bridge`(REQ-029, 이미 색 **집합** 교집합으로 구현돼 있어 — 여러 색이 있으면 자동으로 작동)에 넘겨야 한다. 이를 위해 "그 구간의 보조색이 어디서 나오는가"를 다음 지점에서 조사했다:

| 조사 지점 | file:line | 발견 |
|---|---|---|
| `CueState.color` | `server/concept/cue_model.py:231` | 단일 `str \| None` 필드 — 여러 그룹이 동시에 다른 색을 켤 자리가 모델에 없다 |
| `_color_ops` / `color_for` 콜백 | `server/concept/density.py` (`_color_ops`), `server/concept/gates.py:187-212` (`_make_color_for`) | 색 동작을 `{"op":"replace","color":<한 값>}` 하나만 낸다 — 섹션당 색 문자열 하나 |
| `ConceptCue.colors` 설계 의도 | `server/concept/color_strip.py:57` | 튜플로 설계돼 있어 다색을 담을 **자리**는 있다 |
| `compute_color_strip`의 보조색 읽기 | `server/concept/color_strip.py:87-88` | `colors[1]`을 보조색으로 읽지만, 이 함수를 호출하는 production 코드가 파이프라인에 없다 — REQ-026 Color Strip 산출 자체가 아직 배선되지 않았다 |
| `Palette.secondary` | `server/concept/worksheet.py:49-52` | 곡 전체 전역 상수(`gates.py`의 `SECONDARY_COLOR`) — "그 큐가 emit하는 두 번째 색"이 아니라 Verse/Bridge의 **유일한** 색으로 이미 쓰이고 있다 |

**결론: 이 파이프라인은 큐 하나에 주색+보조색을 동시에 담는 자리를 어디에도 만들지 않는다.** `Palette.secondary`를 `check_adjacent_bridge`에 억지로 밀어 넣는 것은 실제로 emit되지 않는 색을 지어내 PASS를 만드는 것과 같아, 배차서가 명시적으로 금지한 방향이다. 따라서 **`_concept_cues`는 수정하지 않았다** — 이미 실제로 emit되는 색(`row.color`, 단일값)만 담고 있고, 이것이 올바른 동작이다. 이 조사 전체는 `server/concept/gates.py`의 `_concept_cues` 독스트링에도 기록했다(향후 재조사 방지).

### G6 FAIL 8곡의 실제 위반 근거 (곡별)

원인은 8곡 모두 동일한 팔레트 설계 — 절/브릿지(COOL=파랑)와 후렴(WARM=노랑)이 색을 완전히 배타적으로 쓰면서, 인접한 두 구간이 KEY·BACK·SIDE-L·SIDE-R 그룹을 그대로 공유한다(그룹이 겹치므로 REQ-029의 "암전 전환 예외"가 적용되지 않는다). 실측 위반 건수(`check_adjacent_bridge` 반환):

| 곡 | 브리지 위반 건수 | 대표 위반 전환 |
|---|---|---|
| Club Diver.mp3 | 6 | Intro#1→Chorus#1, Chorus#1→Bridge#1, Bridge#1→Chorus#2 |
| Cut and Run.mp3 | 12 | Intro#1→Chorus#1, Chorus#3→Verse#1, Verse#1→Chorus#4 |
| Ice cream.mp3 | 3 | Bridge#1→Chorus#1, Chorus#1→Bridge#2, Bridge#2→Chorus#2 |
| Morning.mp3 | 3 | Verse#1→Chorus#1, Chorus#7→Verse#2, Verse#3→Final Chorus#1 |
| Rain.mp3 | 5 | Verse#2→Chorus#1, Chorus#2→Verse#3, Verse#3→Chorus#3 |
| Too Cool.mp3 | 7 | Intro#1→Chorus#1, Chorus#6→Verse#1, Verse#3→Chorus#7 |
| scott-buckley-neon.mp3 | 6 | Verse#4→Chorus#1, Chorus#2→Verse#5, Verse#6→Chorus#3 |
| 걸그룹DinoDino_C_max최고품질.wav | 2 | Verse#1→Chorus#1, Chorus#1→Bridge#1 |

유보색 검사(REQ-027)는 8곡 전부 pass — 위반 0건. G6 FAIL은 전적으로 브리지 검사(REQ-029) 때문이다.

고치려면 M3(팔레트 설계 — 절/후렴이 색을 공유하도록) 또는 M4(density.py 구간별 색 배정)의 새 결정이 필요하다 — M6(이 파일)은 기존 모듈을 조립만 하므로 이 카드에서 고치지 않는다.

## G5 — density.py Intro 분기 복원과 잔존 FAIL (감독 결정 2)

### 복원 내용

`server/concept/density.py`의 Intro 분기를 프로토타입(`.moai/state/verify/f12e5c95-t429/final_integrated.py` 61~62행)대로 복원했다:

```python
if d=='Intro':
    add(ts,d,occ,None,[{'op':'replace','color':COOL},
        {'op':'expand','roles':['BACK'],'dimmer':25,'pos':'back',
        'motion':0}],'구간',R,'Track',('long',2.0),None,src,
        '보조색 고립',base_name='Intro')
    if bars>=4: add(round(en[i]-4*BAR,1),d,occ,'보컬 시작',
        [{'op':'add','roles':['BACK','SIDE-L','SIDE-R'],'dimmer':35}],
        '프레이즈',R,'Track',('short',1.0),None,'rule','보컬 4마디 전 예고')
```

카드 t437의 축소 포팅은 KEY 10%(사실은 별도 안전 큐의 값과 우연히 같은 값) 하나만 남기고 BACK 25% 확장과 "보컬 시작" 예고 프레이즈를 뺐다. 이번 복원으로 density.py의 Intro 섹션 큐는 KEY 10% + BACK 25%(2그룹) 상태가 되고, 곡 길이가 4마디 이상이면 "보컬 시작" 프레이즈(BACK/SIDE-L/SIDE-R → 35%)가 추가된다. `tracking`은 프로토타입의 `'Track'`을 그대로 옮기지 않고 `cue_only`로 뒀다 — REQ-056(`server/concept/tracking.py`)이 phrase 층 기본값을 `cue_only`로 못박은 이유가 이 파일의 다른 phrase 큐(빌드업·눈 리셋) 전부에 이미 적용돼 있어, 이 새 phrase만 다른 규칙을 쓸 근거가 없다.

### TDD 근거

RED(수정 전) — `.moai/reports/t439/red_g5_before_fix.txt`: 새 시험 3건이 예상대로 실패(`TestIntroPrototypePort` 중 2건 + 1건, 나머지 1건은 애초에 통과하는 가드 시험).

GREEN(수정 후) — `server/tests/test_concept_density.py::TestIntroPrototypePort` 4건 전부 통과(density.py Intro 분기의 절대값 확인 3건 + "4마디 미만이면 삽입 안 함" 가드 1건).

### scott-buckley-neon.mp3의 G5는 여전히 FAIL — 실제 위반

복원 후 Intro는 KEY+BACK 2그룹·최대 25%, Bridge는 KEY+BACK 2그룹·최대 30% — **밝기는 이제 올바르게 감소한다**(25<30, 이전엔 10<30이었지만 그룹 수가 1<2로 오히려 "늘어" 보이는 결함이 있었다). 하지만 `headroom.bridge_reduced`(REQ-047)는 밝기와 그룹 수 **둘 다** 엄격히 감소해야 pass인데, 이 곡은 Intro와 Bridge가 똑같이 KEY+BACK 2그룹을 쓰므로 `2 < 2`가 거짓이라 여전히 fail한다.

```
G5 헤드룸 경고 0 False - G5: Bridge 에서 밝기·그룹 수가 줄지 않음(구간 단위 비교)
```

이는 배차서가 명시적으로 허용한 결과다("If G5 still FAILs for neon after the restore, report it — do not tweak other values"). density.py를 더 손대 이 곡만 group count를 줄이는 것은 "다른 값을 건드려 PASS를 만드는" 방향이므로 하지 않았다.

## 집계 정합성

- 구 기준선(프로토타입, 과대): PASS 98 / n/a 6 / FAIL 0
- 정정 기준선(G6 거짓 PASS 8건만 뺀 값): PASS 90 / n/a 6 / FAIL 8
- 이 카드의 실측(G6 8건 + G5 1건 실제 위반): **PASS 89 / n/a 6 / FAIL 9**

정정 기준선(90)과 실측(89)의 차이 1은 scott-buckley-neon의 G5 — density.py 복원으로도 못 고치는 이 곡 고유의 조명 설계(Intro·Bridge가 같은 그룹 조합을 쓴다) 때문이며, 위에서 실측으로 확인했다.

## 검증

```
uv run pytest server/tests -k "concept or density or gates" -q
```
→ `.moai/reports/t439/pytest_g5g6.txt` — 465 passed, 11 skipped, 13676 deselected, exit 0.

```
uv run ruff check server/concept/gates.py server/concept/density.py server/tests/test_concept_gates.py server/tests/test_concept_density.py
```
→ All checks passed.

### 안 잰 것(Gaps)

`server/tests -q`(전체 스코프, 필터 없음)를 한 번 돌려보니 `TestTouchedFilesPassLint::test_ruff_format_reports_no_change` 1건이 FAIL한다 — `git diff --name-only <_OVERLAP_BASE>..HEAD`가 잡는 "이 SPEC이 손댄 전체 .py 목록" 5개(`server/concept/gates.py`, `server/tests/test_concept_gates.py`, `server/tests/test_concept_density.py`, `server/tests/test_chorus_color_identity_t439.py`, `server/tests/test_chorus_color_two_paths_t439.py`) 중 `ruff format --check`에 걸리는 항목이 있다는 게이트다. 직접 조사(uncommitted 변경을 임시 stash해 재확인)한 결과:

- `server/tests/test_chorus_color_identity_t439.py`·`test_chorus_color_two_paths_t439.py`는 이 카드가 전혀 건드리지 않은 파일이고, 이미 커밋(903f1b75)된 상태에서부터 `ruff format --check`에 걸린다 — 이 카드 이전부터 있던 문제.
- `server/concept/gates.py`도 stash 후(이 카드의 수정 없이) 이미 `ruff format --check`에 걸린다 — 걸리는 지점(`_mmss` 독스트링의 `""`, `g12_mib_no_live_moves`/`g13_cue_density`의 줄바꿈)은 전부 이 카드가 손대지 않은 기존 코드다. 이 카드가 추가한 `_concept_cues` 독스트링 블록은 `ruff format --check`를 통과한다.
- `server/tests/test_concept_gates.py`도 stash 후 이미 걸린다 — 걸리는 지점(`TestFabricatedControlProbe`의 `g4_final_new_axis_and_headroom(...).passed is True` 줄바꿈)은 이 카드가 손대지 않은 기존 시험이다. 이 카드가 고친 독스트링·주석 블록은 포맷을 깨지 않는다.
- `server/tests/test_concept_density.py`는 이 카드가 새로 추가한 `TestIntroPrototypePort`에서 처음엔 2곳이 `ruff format --check`에 걸렸다 — 둘 다 고쳤고(`intro_section = next(...)` 한 줄로, `row["ops"] == [...]` 한 줄로), 지금은 파일 전체가 통과한다.

결론: 이 게이트의 FAIL은 **이 카드 이전부터 있던 상태**이고, 이 카드가 새로 만든 코드는 전부 `ruff format --check`를 통과한다. 두 미관련 파일과 gates.py/test_concept_gates.py의 기존 코드까지 재포맷하는 건 이 카드의 선언 범위(G6/G5) 밖이라(Scope Discipline) 손대지 않았다 — 별도 카드가 필요하다.

🗿 MoAI
