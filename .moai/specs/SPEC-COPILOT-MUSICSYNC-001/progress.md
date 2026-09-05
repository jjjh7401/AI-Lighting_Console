# SPEC-COPILOT-MUSICSYNC-001 — 진행 기록

> 단계별 증거를 적는 자리. plan 단계는 §E.1 만 채우고 §E.2~§E.4 는 각 단계의 소유자가 채운다.

## §E.1 Plan-phase Audit-Ready Signal

- SPEC 작성 완료 2026-09-03 — `spec.md` · `plan.md` · `acceptance.md` · `design.md` (Tier L) + 선행 작성된 `research.md`(오케스트레이터 작성, 기준 `origin/main adae0ac`, 읽기 전용·콘솔 접촉 0).
- SPEC ID 정규식 검사(Bash 실행): `ID="SPEC-COPILOT-MUSICSYNC-001"; [[ "$ID" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]] && echo PASS || echo FAIL` → `PASS`.
- 코드 좌표 실측 확인(2026-09-03, 기준 `adae0ac`): `tools.py:5385` `cue_sheet_xlsx_base64` 취득 · `:5404` `iter_rows(min_row=5)` · `:5405-5412` 열 인덱스 판독 · `:5417-5426` 홑따옴표 fail-closed · `:5427` `cue_meta[q]` 기록 · `:5984-5987` `Store Cue` 조립 · `:6015` `group_approval.request_approval` · `:340` `DEFAULT_RIG_CONTEXT_PATHS` · `:2820-2824` timecodes 미검증 경로 주석 · `cue_parser.py:43-61` 17열 · `cue_mapper.py:333-370` `CueRowPlan` · `:373-378` `CueBucket` · `songcue.py:490-498` 타임코드 3줄 · `:501-512` `TrigType`/`TrigTime` · `:515-519` `_format_seconds` · `app.py:505-513` 분기 누락 사고 주석 · `profile.py:75` `DEFAULT_BPM = 120.0` · `:301` `effective_bpm` · `:307` `bpm_is_default` · `song_plan.py:143` `minimum=0` · `question.py:69-109` `QuestionRequest`(`commands`:85, `multi`:92) · `messages.py:24-26` 업로드 상한 상수 · `:227-262` layout_image 검증 선례 · `session.py:10004-10091` `upload_vectorworks_export` · `registry.py:364-366` `CUE_ROW`(`:366` `RequiredForbidden`) · `blacklist.yaml:81-84` 코퍼스 재측정 절차 · `:172` `Store Preset` 2토큰 선례 · `ui/src/App.tsx:830` accept 에 오디오 없음 · `:549-557` 클라이언트 검증 · `server/audio/` **부재** · `uv.lock` 에 librosa·numpy·soundfile 항목 0건.
- research.md 대비 정정·추가 3건: (a) `cue_sheet_xlsx_base64` 블록 시작이 `:5379` 가 아니라 **`:5385`**(6줄 이내 드리프트) (b) **`TimestampedSection.start_ms` 는 `minimum=0`**(`song_plan.py:143`) — PRE-ROLL 음수 TC 와 직접 충돌하며 research.md 에 없던 사실, REQ-MUSICSYNC-006 이 분리로 해소 (c) `server/safety/` 전체에 `Timecode` 문자열 **0건**(17개 항목 전수, 잘림 없이 재측정) — research.md §3.5 의 분류표는 객체별 등재가 아니라 **동사 규칙의 귀결**이며, `Record Timecode` 가 `safe` 인 것은 누락이 아니라 설계상 결과다.

### v0.1.1 자체 정정 (plan-audit 이전, 2026-09-03)

- **열려 있던 결정 3건이 모두 확정됐다** — `plan.md §C` 가 이제 결정 기록표다(채택 · 기각 · 기각 사유 · 파급 파일 · 결정일). 확정 내용: ① 번들 상한 = `packaging/build.sh` 산출물 대비 **델타 300MB**, 초과 시 개발 모드 전용 분석 + 수동 BPM 입력 폴백 ② `Record Timecode` 는 **앱이 발화하지 않고** `QuestionRequest.commands[]` 로 운영자에게 인계, `blacklist.yaml` 등재는 후속 카드 `blacklist-record-timecode` 로 분리 ③ BPM 정본은 **측정(사람 확정) > 시트 `HEAD.BPM` > 기본값 120**, 어긋남은 항상 보고, `FX-Rate` 는 대조 전용. 결정 대기 항목은 **0건**이다.
- **요구 번호**: `REQ-MUSICSYNC-001`~`025` 연속(공백 0). 조회 예산 요구 `REQ-MUSICSYNC-025` 신설로 24→25.
- **인수 기준**: 25개 전부에 `↔ REQ-…` 명시, `acceptance.md §H` 에 REQ→AC 역방향 전수표 신설. 미대응 REQ 0건. 머리말에 「AC 번호는 REQ 번호를 함의하지 않는다」를 못박음.
- **범위 밖**: `### Out of Scope —` H3 기존 8개 전부를 산문에서 `-` 불릿으로 전환하고, `Record Timecode` 블랙리스트 등재 제외를 아홉째 항목으로 신설(§D). 측정: H3 9개, 각 항목 불릿 3개(최솟값 3).
- **앵커 정정 11건**(`adae0ac` 되읽기): `songcue.py` 490-499→**490-498** · 501-513→**501-512** · 515-520→**515-519** / `tools.py` 5985-5988→**5984-5987** · 2823-2827→**2820-2824** / `session.py` 10004-10093→**10004-10091** / `messages.py` 24-25→**24-26** · 227-244→**227-262** / `App.tsx` 549-578→**549-557** / `cue_mapper.py` 334-371→**333-370** / `Go Timecode 999` 의 `Illegal object` 출처를 `SONGCUE-001/progress.md:326`(그 줄은 ASSUMPTION-20 판정 행이며 이 문자열을 담지 않는다)에서 실측 원본 **`.moai/state/verify/songcue-m0/steps.jsonl:73`** 으로 교체. 아울러 `SONGCUE-001/progress.md:83-94, 130-147` 을 「코퍼스 재측정 절차」의 근거로 인용하던 문장을 폐기했다 — 그 파일에 `코퍼스` 문자열은 **0건**이고, 실제 절차는 `server/safety/blacklist.yaml:81-84` + `server/tests/test_measurement_corpus.py` 에 있다.
- **주어 정정**: 프로세스·산출물 주어 5건을 컴포넌트 주어로 바꿨다 — `the 분석 경로`→`the 분석 파이프라인`(REQ-009) · `the 시험 자산`→`the 픽스처 생성 스크립트`(REQ-011) · `the 확인 카드`→`the 서버 코드`(REQ-015) · `the 패키징 측정`→`When M2 완료를 보고하면, the 완료 보고`(REQ-018) · `the 산출물`→`the 검증 산출물`(REQ-022).
- **구현 방식 이관 3건**: `row[2]`·`row[3]` 인덱스(REQ-001) · `server/audio/analyze.py` 경로(REQ-008) · 「librosa 를 함수 안에서 import」(REQ-010) 를 `spec.md` 에서 빼고 `plan.md §E` M1·M2 표로 옮겼다. 요구는 관측 가능한 것만 말한다.
- 미검증: 재생 명령 문법(M3-a ②) · `TrackGroup` 아래 트랙·이벤트 판독(M3-a ①) · `rig_paths["timecodes"]` 실값(M3-a ③) · librosa 체인 실제 번들 증가분(「+150~300MB」는 추정이고 300MB 는 판정선일 뿐 측정값이 아니다) · M3-a 여섯 조회가 프로브 5건 예산 안에 드는지(`plan.md` B8, 착수 시 계상). ※ 마지막 항목은 v0.1.2 에서 단위를 갈랐다 — 아래 참조.

### v0.1.2 plan-audit 대응 (review-1 PASS 0.857, blocking 6건 해소, 2026-09-03)

감사 보고서 `.moai/reports/plan-audit/SPEC-COPILOT-MUSICSYNC-001-review-1.md` 의 D1~D7(blocking) + D8·D9(optional)를 닫았다. **REQ 25 · AC 25 는 불변** — Tier L 예산을 정확히 소진한 상태라 신설 없이 기존 본문만 개정했다.

- **D1·D2 (major) — M3-a 쓰기 예산이 정의되지 않은 말에 걸려 있었다**(원문 어휘는 감사 보고서 D1 이 인용한다; 이 SPEC 디렉터리에서는 잔존 검사를 위해 다시 쓰지 않는다). 이제 열거다: 슬롯 준비 3줄(`Store Timecode <n>` · `Set Timecode <n> Property 'Name' '<ascii>'` · `Assign Sequence <s> At Timecode <n>`) + 재생 후보 **4건 이하** + 해제 1줄(`Off Timecode <n>`) = **8건 이하**, 전부 격리 슬롯 하나를 향하고 기존 승인 게이트를 지나며 쇼 시퀀스에는 0건. 슬롯은 `_timecode_slot_verdict`(`server/orchestrator/tools.py:2792`)의 3분 판정에서 **free** 를 받은 번호만 쓰고 **occupied·unknown 이면 쓰기 0건 · 무결론**이다. 같은 열거를 여섯 자리에 전파했다 — `spec.md §A.4`·REQ-019·REQ-025 · `acceptance.md` AC-021·AC-030 · `plan.md §D`·M3-a 절 · `design.md §5`. 감사가 지적한 「`plan.md:42` 가 M3-a 를 통째로 읽기 전용이라 적었다」도 정정했다(읽기 전용인 것은 **조회**다).
- **D3 (major) — REQ-014 괄호의 축소 추정치는 인용한 코드가 반증한다.** `server/web/messages.py:218` 이 8 MiB 를 **디코드된 원본 바이트**에 걸고, `:26` 의 base64 문자열 길이 상한(≈10.7 MiB, `:208` 검사)은 거기서 **파생**된다 — 실효 원본 상한은 **8 MiB**. REQ-014 의 괄호 주석을 삭제하고 `design.md:77` 을 고쳤으며 `research.md` R6 에 만료 고지를 남겼다. 자체 재측정: `grep -rn 'max_size\|max_message' server/web/*.py` → **0건(rc=1)** — 그 축소치를 뒷받침할 WebSocket 프레임 상한 근거도 없다.
- **D6 (major) — 음수 `TrigTime` 의 콘솔 수용 여부가 미측정인데 미검증 목록에 없었다.** `plan.md §B` 에 **B9** 를 올렸다. 자체 재측정에서 감사 인용의 행 번호를 정정한다 — `SPEC-COPILOT-SONGCUE-001/progress.md` 의 `'TrigTime' 4` 는 **`:377`**(감사는 `:375`), `'TrigType' 'Zzz'` 는 **`:375`**(감사는 `:373`)다. 같은 파일 `:677` 감사 로그의 `'TrigTime' 40` 도 양수라, **양수만 실측됐다**는 결론 자체는 그대로 선다. AC-006 에 거절 시 강등 절을 덧붙이고(새 AC 신설이 아니라 절 추가 — 예산 보존), AC-031 미검증 열거에 B9 를 넣고, `design.md §6` 에 위험 W11 을 추가했다.
- **D4 (minor)** — GEARS 다섯 이름 밖 표식 2건(REQ-012·017)을 `[Event-driven]` 으로. 문장 본문 무변경.
- **D5 (minor)** — 「취지」 판정 3건을 리터럴 판정으로. AC-007 은 `리허설 LTC 대조 전까지 실행 확정본이 아님` 리터럴 `in` 검사 3회, AC-008 은 `시간 정보 없음`·`manual_go` 두 리터럴 `in` 검사 2회, AC-024 는 **부재 증명을 존재 판정으로 뒤집었다** — 5절 표제 다섯의 `grep -c` ≥1 + 미검증 절의 `unverified`/`SongCueTimingSkip` 리터럴 + 판정 필드가 `verified` 가 아님. REQ-007 문면도 리터럴을 요구하도록 맞췄다.
- **D7 (minor) — §A.4 M3-a 조회 칸에 조회 수가 아니라 프로브 수가 들어 있었다.** 이제 **`query_state` 12회 이하**이고 12항목 내역이 같은 칸에 있다 — 슬롯 판정 1 · 준비 전 베이스라인 1 · 준비 후 되읽기 1 · `TrackGroup 1` 판독 1 · 재생 후보 효과 되읽기 4 · `rig_paths` 실값 1 · 양성 대조군 1 · 음성 대조군 1 · 해제 뒤 되읽기 1. 프로브 5건은 **별도 축**으로 남는다. `plan.md` B8 이 스스로 드러냈던 단위 혼선(「여섯 조회가 프로브 5건 안에」)을 같이 정정했고, 이로써 S11 의 「쓰기·조회 양쪽에서 예산 안에」가 양쪽 모두 수치 상한을 갖는다.
- **D8·D9 (optional)** — REQ-015 의 필드 수준 지정(`multi=True`·구간당 옵션·`selected=True`)을 `plan.md §E` M2 표의 `question.py` 행으로 이관하고 그 행을 정본으로 표기. `plan.md:61` 에 `research.md §1.3` 헤더 실측 인용을 붙였다(`CUE` 탭 4행 헤더 순서 ↔ 오늘 코드의 `row[0]`·`row[1]`·`row[5]`·`row[12]`).
- **새로 잰 것**: `server/web/messages.py:24-26, 205-218`(8 MiB 가 디코드분에 걸린다) · `server/orchestrator/tools.py:2792-2850`(`_timecode_slot_verdict` 3분 판정 — free/occupied/unknown, 내부에서 `query_state` 1회) · `SONGCUE-001/progress.md:375, 377, 677`(양수 실측 전수) · `grep -rn 'max_size\|max_message' server/web/*.py` → 0건.
- **여전히 미검증**: B4 · B5 · B6 · B7 · B8(새 단위 12회 기준으로 재계상) · **B9(음수 `TrigTime`)**. 12회라는 조회 상한 자체도 **설계상 계상치**이지 실측이 아니다 — M3-a 착수 시 실제 호출 수를 세어 노트에 적는다.

## §E.2 Run-phase Evidence

### M1 — 시트 시간열 수용 (2026-09-05, TDD)

기준 트리: 워크트리 `.claude/worktrees/agent-a6d3d048bacc1915a`, 브랜치
`worktree-agent-a6d3d048bacc1915a`, base `3df3c06`(= `origin/main`). 콘솔 접촉 **0건** —
실기 발화 없음(테스트는 전부 가짜 포트).

**변경 집합** (plan.md §E M1 표 그대로, 그 밖의 파일 0건)

| 파일 | 델타 | 내용 |
|---|---|---|
| `server/lxseq/cue_time.py` | NEW | `mm:ss.f` 순수 파서(5갈래) + 타임라인 얕은 투사 + 세 리터럴 상수 |
| `server/lxseq/cue_mapper.py` | MODIFY | `CueTimingViolation` + `cue_timing_violations()` — `CueHold` 와 **별도 타입** |
| `server/orchestrator/tools.py` | MODIFY | `TC In`/`TC Out`/`HEAD` 판독 · `TrigType`/`TrigTime` 두 줄을 기존 승인 번들에 · `cue_timing`·`timing_apply` 페이로드 |
| `server/tests/test_lxseq_cue_time.py` | NEW | 파서·투사 단위 33건 |
| `server/tests/test_lxseq_cue_tool.py` | MODIFY | AC-001~008 도구 층 22건 |
| `server/tests/test_lxseq_cue_mapper.py` | MODIFY | 단조성 위반 어휘 5건 |
| `server/tests/test_lxseq_cue_harness.py` | MODIFY | 정본 곡파일 전량 회귀 3건 |

`server/lxseq/cue_parser.py` · `server/sheets/registry.py` · `server/design/song_plan.py` 는
**무변경**이며, 그 사실을 `git diff --name-only 3df3c06 -- <두 파일>` 이 비어 있음으로
기계 검사한다(`TestCsvOnlySaysItsHonestLimit::test_the_two_preserve_files_have_no_diff_against_the_base`,
PASSED — skip 아님).

**AC 판정표** (전 항목 `.venv/bin/python -m pytest -q -p no:cacheprovider <node-id>`)

| AC | 판정 | 검증 노드 | 관측 |
|---|---|---|---|
| AC-MUSICSYNC-001 | PASS | `test_lxseq_cue_tool.py::TestSheetTimeLandsOnTheCue::test_preview_carries_the_two_timing_lines_side_by_side` · `::test_the_trigtime_value_follows_format_seconds_semantics` | `PASSED` ×2. preview 페이로드의 `cue_timing.cues[].commands` 가 `["Set Cue 10 Sequence 2 Property 'TrigType' 'Time'", "Set Cue 10 Sequence 2 Property 'TrigTime' 0"]` |
| AC-MUSICSYNC-002 | PASS | `::TestOneApprovalBundleAndNoExtraQueries::test_the_three_lines_ride_one_approval_bundle` · `::test_preview_writes_nothing_to_the_console` · `::test_the_query_state_count_does_not_grow_when_times_are_read` | `PASSED` ×3. 승인 요청 **1건**에 `Store Cue`+두 줄 동거 · preview `exec_port.sent == []` · `query_state` 호출 수 시트 준 쪽 == 안 준 쪽 |
| AC-MUSICSYNC-003 | PASS | `::TestUndeterminedNeverFires::test_needs_check_blank_and_malformed_are_three_distinct_reasons` | `PASSED`. 사유 3종 `needs_check`/`blank`/`malformed` 가 **서로 다른 값** · 세 큐의 `commands == []` · 성한 Q040 은 그대로 나감 |
| AC-MUSICSYNC-004 | PASS | `::TestNoInventedZero::test_an_undetermined_cue_carries_no_number_and_emits_no_trigtime` · `::test_a_genuine_zero_is_the_only_cue_that_may_say_trigtime_zero` | `PASSED` ×2. 미확정 큐의 `tc_in.ms is None` · 페이로드 전문에 `TrigTime 0` **부재** · 진짜 `00:00.0` 큐에서만 `'TrigTime' 0` |
| AC-MUSICSYNC-005 | PASS | `::TestMonotonicityViolationsAreASeparateList::test_a_backwards_tc_in_is_listed_and_the_order_is_untouched` · `::test_a_tc_out_past_the_next_tc_in_is_a_separate_item` · `::test_the_violation_is_not_mixed_into_the_cue_hold_vocabulary` | `PASSED` ×3. 별도 목록 `cue_timing.monotonicity_violations` · 시트 순서 보존 · `cues_held`/`held` 에 위반 어휘 0건 |
| AC-MUSICSYNC-006 | PASS | `::TestPreRollIsCarriedButNotProjected::test_a_negative_tc_in_is_emitted_and_excluded_from_the_timeline` · `::test_a_console_rejection_demotes_only_that_cue_and_writes_no_rollback` · `test_lxseq_cue_time.py::TestTimelineProjection::test_the_projection_raises_no_song_plan_error_on_a_negative_cue` | `PASSED` ×3. `'TrigTime' -30` 발화 · `timeline.excluded_preroll == ["Q005"]` · `SongPlanError` 미발생 · 거절 시 계수 판정 `applied ∪ rejected == attempted`, `applied ∩ rejected == ∅`, `rollback_commands == []` |
| AC-MUSICSYNC-007 | PASS | `::TestDerivedWarningPropagates::test_the_result_payload_carries_the_literal` · `::test_the_timeline_projection_carries_the_literal` · `::test_the_cue_label_family_carries_the_literal` | `PASSED` ×3(리터럴 `in` 검사 3회). 부정 대조군 `::test_a_non_derived_method_gets_no_warning` 도 `PASSED` — 경고가 늘 켜져 있는 계기가 아님 |
| AC-MUSICSYNC-008 | PASS | `::TestCsvOnlySaysItsHonestLimit::test_no_timing_lines_and_both_literals_in_the_reason` · `::test_the_seventeen_column_exact_set_is_untouched` · `::test_the_two_preserve_files_have_no_diff_against_the_base` | `PASSED` ×3. `'TrigTime'` 0건 · 사유에 `시간 정보 없음`·`manual_go` 둘 다 · 17열 정확 집합과 `CUE_ROW.predicate.required_columns` 무변경 · 두 PRESERVE 파일 diff 공집합 |

**정본 실물 회귀** — 합성 시트만으로는 실제 열 자리가 증명되지 않아 정본 곡파일
두 장(`LXSEQ_SAMPLE_01_Sugar_r3.cue-ex.csv` 89행 + 같은 이름 `.xlsx`)을 그대로
통과시켰다: 18 큐 전부 시각 판독, 미확정 **0건**, 단조성 위반 **0건**, 타임라인
18구간, PRE-ROLL 제외 0건, `HEAD.TC_METHOD` 가 `DERIVED…` 라 경고 리터럴 점화
(`test_lxseq_cue_harness.py::test_the_canonical_song_file_yields_a_time_for_every_cue`,
`::test_the_canonical_song_file_declares_itself_derived`, `::test_the_canonical_csv_alone_still_reads_and_says_its_limit` — 3건 `PASSED`).

**RED 증거**(GREEN 이전에 관측)

```
server/tests/test_lxseq_cue_time.py:16: in <module>
    from server.lxseq.cue_time import (
E   ModuleNotFoundError: No module named 'server.lxseq.cue_time'
```

```
>       from server.lxseq.cue_mapper import cue_timing_violations
E       ImportError: cannot import name 'cue_timing_violations' from 'server.lxseq.cue_mapper'
5 failed, 64 deselected in 0.06s
```

```
>       return next(c for c in payload["cue_timing"]["cues"] if c["cue_no"] == cue_no)
E       KeyError: 'cue_timing'
17 failed, 23 passed in 0.44s
```

**전량 검사**

```
$ .venv/bin/python -m pytest -q -p no:cacheprovider server/tests
11055 passed, 12 skipped, 1 warning in 147.63s (0:02:27)
```

```
$ .venv/bin/ruff check <touched 7 files>
All checks passed!
$ .venv/bin/ruff format --check <touched 7 files>
7 files already formatted
```

```
$ .venv/bin/python -m pytest -q --cov=server.lxseq.cue_time --cov=server.lxseq.cue_mapper ...
server/lxseq/cue_mapper.py     339      9    97%
server/lxseq/cue_time.py        75      0   100%
```

**설계 판단 기록 — plan.md M1 표와 다른 자리 하나**

`cue_mapper.py` 의 `[MODIFY]` 를 `CueRowPlan`·`CueBucket` **필드 추가**가 아니라
`CueTimingViolation` **신설**로 이행했다. 시각은 xlsx 에서 오고 `map_cues` 는 그
바이트를 보지 않으므로, 두 데이터클래스에 필드를 더하면 **아무도 채우지 않는
칸**이 남는다 — 「검사 자신이 공허할 수 있다」와 같은 형태의 결함이다. 대신
`CueHold` 바로 옆에 별도 타입을 두어 REQ-MUSICSYNC-005 의 「섞지 않는다」가
정의 자리에서 보이게 했다. 파일 집합은 M1 표 그대로다.

**미검증(재지 못한 것 — 「비었음」이 아니다)**

- **B9 — 음수 `TrigTime` 인자를 콘솔이 받아들이는지는 여전히 미측정이다.** 이번에
  잰 것은 콘솔의 답이 아니라 **거절을 받았을 때의 우리 거동**이다(가짜 실행 포트로
  그 큐의 `'TrigTime' -30` 만 실패시켜 관측). 실기 확인은 M3 리허설 몫이다.
- 실기 콘솔 왕복 0건 — 이번 회차의 모든 관측은 오프라인이다.
- `HEAD.BPM` 문자열(`120 (고정)`)은 **읽기만** 했다. 파싱·우선순위 채택은 M2 몫이며
  `server/design/profile.py` 는 무변경이다.
- `_format_seconds` 를 사설 이름 그대로 임포트했다 — 중복 구현을 만들지 않으려는
  선택이고, `songcue.py` 는 M1 파일 집합 밖이라 공개화하지 않았다.

## §E.3 Run-phase Audit-Ready Signal

```yaml
run_complete_at: 2026-09-05
run_commit_sha: pending-backfill-m1
run_status: audit-ready
milestone: M1
ac_pass_count: 8
ac_fail_count: 0
ac_scope: AC-MUSICSYNC-001..008 (M1 전량)
preserve_list_post_run_count: 3   # cue_parser.py · registry.py · song_plan.py — 전부 무변경
console_writes_emitted: 0
new_warnings_or_lints_introduced: 0
full_suite: "11055 passed, 12 skipped"
coverage_new_module: "server/lxseq/cue_time.py 100%"
unverified: [B9]
m1_to_mN_commit_strategy: "M1 단일 커밋 — M2·M3 는 이 SPEC 의 후속 회차"
```

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_

## Plan Audit-Ready Signal

- plan_complete_at: 2026-09-04T00:02:42Z
- plan_status: audit-ready
- plan_audit: PASS 0.923 (iteration 2, .moai/reports/plan-audit/SPEC-COPILOT-MUSICSYNC-001-review-2.md) · review-2 D1 은 0.1.3 에서 문장 교체로 해소
