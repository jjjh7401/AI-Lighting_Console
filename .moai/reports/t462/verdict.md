# t462 판정서 — 업로드 길의 드롭 전 어둠·절정 길이 상한을 대화 길 조립기로 옮김

- 카드: t462 · SPEC-LDDESIGN-001 REQ-003 · 근거 판정서 `.moai/reports/t448/verdict.md`
- 브랜치: `WT-composer-port`, 기준 `origin/main` fa237e32
- 콘솔 쓰기: 0 (명령은 생성만 하고 보내지 않았다)
- 판정: **PASS** — 좁힌 범위(아래 §1) 기준 완료 조건 ①~⑤ 전부 충족

## 0. 감독용 요약

대화 길(채팅·웹에서 문답으로 확정하는 길)로 만든 곡에 두 가지가 새로 걸린다.

1. **드롭 앞 어둠** — 후렴 바로 앞 큐의 밝기를 기준표의 그 구간 바닥까지 내린다. 예: 절 90% → 25%.
2. **절정 블라인더 + 2박 복귀** — 대화 길이 원래 붙이던 「절정 강조」 이름표가 이제 실제 블라인더 명령으로
   나가고, 2박(BPM 120 기준 1초) 뒤 복귀 큐가 블라인더를 끈다.

기준값(어둠 바닥 20·행별 바닥, 블라인더 2박·스트로브 4박, 블라인더 밝기 = 행 아래끝)은 업로드 길 파일
`server/looks/songcue.py` 한 곳에만 있고, 대화 길은 그것을 불러다 쓴다. 업로드 길의 명령은 한 글자도
바뀌지 않았다.

## 1. 범위 변경 — 카드 원문과 달라진 점과 근거

카드 원문은 「절정 상한·후렴 강조 사다리·드롭 전 어둠」 셋을 옮기라고 했다. 착수 직후 실제 대화 길 코드로
곡 하나를 만들어 재 보니(`probe_a.py` → `probe_a.before.txt`) 전제 일부가 틀렸다.

| 기능 | 재 본 결과 | 처리 |
|---|---|---|
| 드롭 전 어둠 | 없음. 후렴 앞 Verse 2·4·5 가 밝기 90 그대로 | 옮김 |
| 후렴 밝기 사다리 | 옮겨도 효과 0. Chorus 1·2·3 이 전부 밝기 100(D5 예산 상단)이라 +5 가 천장에 막힌다 | 옮기지 않음 (n/a) |
| 강조 사다리(줌·블라인더·아이리스 회전) | 대화 길에 **이미 자기 사다리가 있다** — `session.py` `_occurrence_accent_label`(t402·t403·t405): 가운데 후렴 「moving position hit」, 절정 「climax accent」, 피날레 「white flash」 + 회차별 색·효과 회전. t448 판정서는 조립기 파일만 세서 이걸 못 봤다 | 옮기지 않음 (n/a) — 두 사다리를 겹치면 한 큐에 액센트 둘(§6.1 위반) 위험 |
| 절정 길이 상한 | 대화 길은 블라인더·스트로브를 콘솔에 한 번도 안 내서 자를 대상이 없었다 | 대화 길의 기존 절정 이름표를 블라인더로 실제 발사한 뒤 상한을 건다 |

리드가 2026-09-27 이 좁힌 범위를 결정했다. 완료 조건 ③은 「어둠 줄이 나오고, 액센트가 블라인더 줄로
나가며, 2박 뒤 복귀한다」로 읽는다.

## 2. 무엇을 바꿨나

| 파일 | 변경 |
|---|---|
| `server/looks/songcue.py` | 2박/4박 상한을 `climax_cap_beats(rung)` 함수로 꺼냈다. 값은 그대로이고 B 도 이 함수를 쓴다 |
| `server/design/song_plan.py` | 곡 계획에 `blinder_group_no`(기본 `None`) 한 칸 |
| `server/design/song_cue_composer.py` | 조립 순서에 세 단계를 끼웠다: 드롭 앞 어둠 → 블라인더 액센트 → 절정 복귀 큐 → (기존) MIB. 큐 종류에 `climax_return`, 큐에 `accent_fixture`·`pre_drop_from`, 번들에 `arc_notes`·`timed_cues` |
| `server/web/session.py` | `_blinder_group_no`(콘솔 그룹 이름 BLIND/BLINDER 정확 일치만), 블라인더 켜는 줄과 다음 큐에서 끄는 줄, 복귀 큐를 타이밍·readback 기대값에 포함, 못 한 사유를 최종 회신에 노출 |
| `server/tests/test_song_cue_arc_t462.py` | 새 시험 20개 — 기대값을 B 함수로 계산해 값이 두 곳에 생기면 깨진다 |
| `server/tests/test_song_cue_composer.py` | 기존 시험 한 곳의 기대값 갱신: Verse→Chorus 모양이라 Verse 밝기 90→25, back 72→20 (의도한 변화) |

세부 규칙:

- **어둠**: 드롭(§6 chorus · drop 행) 바로 앞 큐만. 앞 큐도 같은 행(후렴 뒤 후렴)이거나, 이미 어둡거나,
  블랙아웃이거나, 이름이 §6 표에 없으면 건드리지 않는다. back 층은 조립기의 key→back 비율 0.8 을 지킨다.
  이 큐는 D 레벨 예산(린트 L2) 아래로 **일부러** 내려가므로 린트의 의도적 위반 선언(`tags={"L2"}`)을 단다.
- **블라인더**: 대화 길 액센트가 「white flash」 또는 「climax accent…」인 큐만. 그룹이 없으면
  (`blinder_group_absent`), 구간 이름이 §6 행에 없으면(`blinder_six_row_absent`, 예: Finale) 켜지 않고
  사유를 남긴다. 밝기 숫자를 지어내지 않는다.
- **복귀 큐**: BPM 이 있고 자동 진행(TrigTime·Timecode)일 때만. 수동 GO 는 박을 잴 시계가 없고, 복귀 큐를
  끼우면 감독이 GO 를 한 번 더 눌러야 블라인더가 꺼지므로 끼우지 않는다. 다음 큐가 상한 안에 오면
  끼우지 않는다(B 와 같은 규칙). 큐 번호는 앞뒤 큐의 가운데(예: 10.5)다.
- **끄는 줄**: 콘솔은 값을 다음 큐로 이어 가므로(트래킹) 켠 블라인더는 누가 끄기 전까지 켜진 채로 남는다.
  그래서 블라인더 큐 바로 다음 큐(복귀 큐든 다음 구간이든)가 같은 그룹을 0 으로 내린다.

## 3. 완료 조건 판정

### ① 절정 상한·기준값 바이트 동일 — PASS

- 명령: `git diff server/looks/songcue.py`
- 관측: 바뀐 줄은 `cap_beats = 2.0 if rung == LADDER_BLINDER_OR_FLASH else 4.0` →
  `cap_beats = climax_cap_beats(rung)` 하나와, 같은 식을 담은 새 함수뿐이다. `DARKNESS_FLOOR`·`_HIT_STEP`·§6
  행 표는 손대지 않았다.
- 보강: `uv run pytest server/tests/test_songcue_climax_001.py server/tests/test_songcue_t429_repeat_chorus_collision.py -q` → `21 passed`

### ② 업로드 길 콘솔 명령 바이트 동일 — PASS

- 명령: `uv run python .moai/reports/t462/dump_b.py` 을 변경 전후로 돌려 `dump_b.before.txt`·`dump_b.after.txt`, 이어서 `cmp` 로 비교
- 관측: `BYTE-IDENTICAL`, 양쪽 `TOTAL sha256=022bf9926dd0c49be7e91ebcf6068223a787bbbbcecad03bdd08f98c83cde738`
- 범위: 실제 입구 `build_songcue_bundle` + 실제 룩 라이브러리, 2곡(Ice cream·Rain) × 4장르 × BPM 있음/없음 = 16조합

### ③ 대화 길 곡에 실제로 걸림 — PASS

- 명령: `uv run python .moai/reports/t462/probe_a_console.py` → `probe_a_console.after.txt`
  (probe_a 와 같은 11구간·BPM 120 곡을 실제 빌더와 실제 명령 생성기로 만든다. 블라인더 그룹은 가짜 주소록 한 줄 `BLIND`=14)
- 관측(발췌):

```
    3 section       Verse 2          D4 key=25.0 pre_drop_from=90.0
    6 section       Verse 4          D4 key=25.0 pre_drop_from=90.0
    9 section       Verse 5          D4 key=25.0 pre_drop_from=90.0
   10 section       Chorus 3         D5 key=100.0 blinder={'rung': 'blinder_or_flash', 'group_no': 14, 'dimmer_pct': 80.0} start=144000
 10.5 climax_return Chorus 3 Return  D5 key=100.0 start=145000
blinder_six_row_absent: Q11 'Finale' 절정 액센트 — 구간 이름이 §6 표의 한 행에 맞지 않아 …
Fixture 1 + 2 + 3 + 4 ; Attribute 'Dimmer' At 25          (3회)
Group 14 ; Attribute 'Dimmer' At 80
Store Sequence 120 Cue 10 'Chorus 3' CueFade 0.25
Group 14 ; Attribute 'Dimmer' At 0
Store Sequence 120 Cue 10.5 'Chorus 3 Return' CueFade 0
Set Cue 10.5 Sequence 120 Property 'TrigTime' 145
```

- 고치기 전 같은 곡(`probe_a.before.txt`): Verse 2·4·5 밝기 90, 블라인더 줄 0, 복귀 큐 0.

### ④ 8곡 게이트 기준선 75/29/0 유지 — PASS

- 명령: `uv run pytest server/tests/test_concept_gates.py -q` → `22 passed`
  (이 파일이 `(pass, n/a, fail) == (75, 29, 0)` 을 단언한다, 424행)
- 참고: 게이트는 `server/concept` 파이프라인으로 돌고 이번 변경은 그 경로를 타지 않는다.

### ⑤ MIB 동작 불변 — PASS

- 명령: `uv run pytest server/tests/test_mib.py server/tests/test_concept_mib.py server/tests/test_director_validate_mib.py -q` → `64 passed`,
  조립기 MIB 시험 `-k mib` → `1 passed`
- 근거: 새 단계는 MIB 앞에서 돈다. 어둠 바닥은 20 이상이라 MIB 의 「앞 큐가 0 인가」 판정을 바꾸지 않고,
  복귀 큐는 불이 켜진 큐라 뒤 큐의 MIB 를 발화시키지 않는다.

### 회귀 — 영향받는 시험 전체

- 명령: 이 네 모듈(+`server.concept`·`server.spatial.mib`)을 import 하는 시험 105파일
  (`affected_tests.txt`)을 `uv run pytest @.moai/reports/t462/affected_tests.txt -q`
- 관측: `2633 passed, 24 skipped` (`affected_run.txt`). 린트 `ruff check`·`ruff format --check` 통과.

## 4. 안 잰 것

- **전체 시험 스위트**는 로컬에서 끝까지 돌리지 않았다(시작했으나 규모 때문에 중단). 영향받는 105파일만
  돌렸다 — 전체는 CI 가 PR head 에서 돈다.
- **실기 콘솔**에 보내지 않았다. `Group 14 ; Attribute 'Dimmer' At 80`, 소수 큐 번호 `Cue 10.5` 의 저장·
  TrigTime 이 실기에서 받아들여지는지는 잰 적이 없다. 소수 큐 번호는 MIB 가 이미 `1.5` 꼴로 쓰고 있어
  문법상 새롭지 않지만, **소수 큐에 TrigTime 을 거는 것**은 이 저장소에서 처음이다.
- **블라인더 그룹 찾기**는 가짜 주소록으로만 쐈다. 실기 리그 그룹 이름 `BLIND` 는 t379 실측 기록(rig.py
  주석)에 근거한다.
- 업로드 길 덤프(②)에서는 절정 복귀 큐가 한 번도 생기지 않았다(16조합 모두 `returns=[]`). 상한 함수를
  꺼낸 변경의 바이트 동일성은 B 의 절정 시험(21 passed)이 받친다.

## 5. 남은 위험

- **어둠이 구간 전체에 걸린다.** 앞 큐가 마디로 쪼개지지 않은 긴 절이면 그 절 전체가 25% 로 간다(B 도 같은
  「줄인 워시」 형태다). 대화 길은 BPM 이 있으면 구간을 마디로 쪼개므로 보통은 마지막 조각만 어두워지지만,
  BPM 이 없는 곡에서는 절 전체가 어두워진다.
- **블라인더 기구가 전체 기구 목록에 들어 있으면**, 복귀 큐의 끄는 줄 때문에 그 기구가 다른 큐보다 어두워진다
  (그룹 멤버십은 콘솔에서 못 읽는다, RG5).
- **L14(블라인더 곡당 2회·D5 전용)** 는 보고만 하고 막지 않는다. 대화 길 이름표 규칙상 절정 1 + 마지막 후렴 1 이 보통의 최대라 넘지 않을 것으로 보지만, 재 본 것은 아니다.
- 대화 길 회신 문구에 「절정 연출 미반영: …」 한 줄이 새로 붙을 수 있다(블라인더 그룹이 없는 리그에서는
  매 곡).

## 6. 증거 파일

`.moai/reports/t462/` — `probe_a.py`·`probe_a.before.txt`(고치기 전), `probe_a_console.py`·
`probe_a_console.after.txt`(고친 뒤 콘솔 명령), `dump_b.py`·`dump_b.before.txt`·`dump_b.after.txt`(②),
`affected_tests.txt`·`affected_run.txt`(회귀).
