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

### M3-a — 콘솔 타임코드 프로브 (2026-09-05, 실기 2회차)

**주장.** 세 프로브와 대조군 둘을 격리 슬롯 999(시퀀스 9 `T215 SCRATCH DELETABLE`)에서 예산 안에 실행했다. ① `TrackGroup` 아래가 **열렸다** · ② 재생 후보 4종은 **효과 미관측(미증명)** · ③ `rig_paths["timecodes"]` = `DataPool/Timecodes` 로 M0 와 일치. 설계서 §5 기준 **갈래 B**(재생 문법 미증명).

**증거.** `docs/research/ma3-effects/14-musicsync-m3a-timecode-probe-run2.md`(+ 정정 절) · 단계 로그 `docs/research/ma3-effects/evidence/musicsync-m3a-run2-steps.jsonl`(19행). 쓰기 8/8 — `Store Timecode 999` · `Set … 'Name' 'MSYNCPROBE'` · `Assign Sequence 9 At Timecode 999` · `Go`/`Go+`/`Pause`/`Toggle Timecode 999` · `Off Timecode 999`; 열거 밖 0 · 비격리 대상 0. 조회 11/12(프로브별 숫자는 노트) · 프로브 5/5. ①: `DataPool/Timecodes/999/TrackGroup 1` → `childCount 2`, 자식 `MarkerTrack "Marker"` · `Track "<T215 SCRATCH DELETABLE>"`, `truncated:false`. ⑤: 생성 전 `path segment not found: '999' (in DataPool/Timecodes/999)`. ④: 슬롯 이름 `MSYNCPROBE` 일치, 풀 childCount 1→2.

**기준 귀속.** main `793abb4` + 이 브랜치 `WT-timecode-probe`, 응답기 1.6.4, 2026-09-05T10:20Z. 오케스트레이터가 원자료로 되읽어 대조.

**미검증.** B4 잔여 — 재생 후보 넷은 `ok:true` 였으나 오브젝트 상태 스냅숏이 준비 직후와 동일해 효과를 이 채널로는 못 잰다(재생 상태 필드 부재). 프로브 1판이 낸 「효과=True」 넷은 응답 `id` 를 비교에 넣은 **오판**이며 같은 브랜치에서 정정·회귀검사(`test_a_readback_that_differs_only_by_request_id_is_no_effect`). B5 는 닫혔다(열렸다). B6 는 닫혔다(일치). B8: 실측 조회 11.

**잔여 위험.** (1) **빈 타임코드 풀에서는 앱이 타임코드를 못 쓴다** — `_timecode_slot_verdict` 의 `childCount 0 → unknown` 은 응답기가 빈 풀과 실패 열거를 같은 페이로드로 답하기 때문이며(1회차 무결론, `…-timecode-probe.md`), 이 쇼에서 2회차가 가능했던 것은 감독이 `Timecode 1` 을 손으로 만든 뒤다. M3-b 도 같은 조건. 결정 필요(응답기 1.6.5 실패 표식 / 판정 완화 / 운영 절차). (2) 잔여물 `Timecode 1`·`999` 는 삭제 예산 밖 — 운영자가 정리. (3) 후보 효과 판정은 다른 채널(`query_properties` 재생 속성 등)이 필요하며 예산 밖.
### M2 — 오디오 업로드 · 분석 · 확인 카드 (2026-09-05, TDD)

기준 트리: 워크트리 `.claude/worktrees/agent-aaf883931452e422d`, 브랜치
`worktree-agent-aaf883931452e422d`, base `793abb4`. 콘솔 접촉 **쓰기 0건 · 조회 0건** —
분석 층은 콘솔을 이름조차 부르지 않으며 그 사실이 AST 스캔으로 기계 고정돼 있다.

**변경 집합** (plan.md §E M2 표 그대로. 표 밖 파일은 `server/tests/test_prechk_tool.py`
한 건 — 웹 표면 동결 등기에 새 메시지 타입을 손으로 올린 것이며, 그 파일 자신의
규약이 「정당한 추가도 손으로 올려야 통과한다」이다.)

| 파일 | 델타 | 내용 |
|---|---|---|
| `server/audio/analyze.py` | NEW | bytes → 여섯 축 순수 함수. librosa 는 함수 안 import |
| `server/audio/__init__.py` | NEW | 콘솔 무접촉 경계를 문장으로 선언 |
| `server/tests/fixtures/audio/__init__.py` | NEW | 합성 트랙 생성기 — 표준 라이브러리만 |
| `server/tests/test_audio_boundary.py` | NEW | 형제 4종과 같은 AST 스캔 형태 |
| `server/web/messages.py` | MODIFY | `song_audio_upload` 검증 · `SongAudioRejectedError` |
| `server/web/app.py` | MODIFY | 디스패치 분기 + `song_audio_rejected` 종류 |
| `server/web/session.py` | MODIFY | `SongAudioUpload` 보관 · `analyse_song_audio` |
| `server/web/question.py` | MODIFY | 확인 카드 빌더 — `QuestionRequest` 스키마 무변경 |
| `server/design/profile.py` | MODIFY | `parse_sheet_bpm` · `resolve_bpm` · `BpmResolution` |
| `ui/src/{App.tsx,protocol.ts,useCopilotSocket.ts}` | MODIFY | accept·검증·프레임 |
| `pyproject.toml` · `packaging/GrandMA3-Copilot.spec` | MODIFY | librosa + PyInstaller 훅 |
| `src-tauri/capabilities/default.json` | EXISTING | **무변경**(diff 0줄, 아래 기계 검사) |

**AC 판정표** (전 항목 `.venv/bin/python -m pytest -q -p no:cacheprovider <경로>`)

| AC | 판정 | 검증 노드 | 관측 |
|---|---|---|---|
| AC-MUSICSYNC-010 | PASS | `test_audio_boundary.py` + 형제 4종 동시 실행 | `97 passed in 2.26s`. `server/audio/**` 위반 0건 · 뮤테이션 대조군 4종(주입된 `gate.screen` · `query_state` · bridge import · tools import)이 전부 잡힘 · 독스트링/주석 오탐 0건 |
| AC-MUSICSYNC-011 | PASS | `test_audio_analyze.py` | `23 passed in 1.86s`. bpm **129.199**(정답 128, ±3% = 124.16~131.84 안) · 경계 **(0, 15952, 32020, 36014)** ms(정답 0/16000/32000/36000, ±1000ms 안, 정답 밖 경계 0건) · D 등급 **[1,3,5,2]** 정답 일치 · 온셋 85건 · 실패 4종(빈 바이트열·잘린 RIFF·텍스트·PNG) 전부 `AnalysisFailure` + 사유 문자열 · 데워진 뒤 호출에서 파일 열기 0건 · 소켓 0건 |
| AC-MUSICSYNC-012 | PASS | `find server/tests/fixtures -type f \( -name '*.wav' -o -name '*.flac' -o -name '*.mp3' -o -name '*.m4a' \) \| wc -l` | `0`. 픽스처는 생성 스크립트로만 존재한다 |
| AC-MUSICSYNC-013 | PASS | `test_web_song_audio.py::TestTheUploadTravelsTheWholeWireNotJustTheSessionMethod` | 정상 `33 passed`. **뮤테이션 실측**: `app.py` 디스패치 분기를 제거하면 같은 클래스 7건 중 **5건이 실패**(`5 failed, 2 passed in 50.58s`, 증거 `.moai/state/verify/musicsync-m2/ac013-mutation.log`). 통과한 2건은 거절 경로라 분기 이전에 갈린다 |
| AC-MUSICSYNC-014 | PASS | `test_web_song_audio.py::TestTheEightMebibyteCapIsMeasuredOnDecodedBytes` · `::TestTheFrameIsValidatedBeforeAnythingIsStored` | `33 passed`. 상한 초과 사유에 한국어 + `8 MiB` + `8388608` 동시 포함 · 상한 **정확히** 8 MiB 는 통과(경계 대조군) · 거절 시 `session.song_audio is None` · `git diff --name-only 793abb4..HEAD -- src-tauri` → **0줄** |
| AC-MUSICSYNC-015 | PASS | `test_song_confirm_card.py` | `30 passed in 0.18s`. `multi=True` · 옵션 수 == 구간 수(1·2·4 셋 다) · DSP 제안 `selected=True`(끈 구간은 `False` — 대조군) · `QuestionRequest` 필드 집합 6개 불변 · 빌더 소스에 `provider`/`complete(`/`ask_user`/`ToolCall`/`llm` **0건** · `ask_user` 툴 스키마에 `selected`/`multi`/`commands` **부재**(툴 자체는 존재 — 대조군) |
| AC-MUSICSYNC-016 | PASS-WITH-DEBT | `test_song_bpm_priority.py::TestAConfirmedTempoTurnsOffTheDefaultMarker` · `::TestLintL11RunsOnceTheTempoIsReal` · `::TestTheDefaultTempoDisclosureFollowsTheMarker` | `34 passed in 0.04s`. 확정 128 → `bpm_is_default False` · `effective_bpm 128.0` · L11 이 `disabled_rules` 에서 빠짐(기본값일 때는 들어 있음 — 대조군) · 미확정이면 오늘과 동일(`120.0` · `True`). **DEBT**: 「BPM 미지정, 120 기본값」 문구 절은 **생산 지점**에서만 판정했다 — 아래 미검증 절 참조 |
| AC-MUSICSYNC-017 | PASS | `bash packaging/build.sh` × 2 + `du -sk` | 아래 번들 크기 절 |
| AC-MUSICSYNC-018 | PASS | `test_song_bpm_priority.py::TestFxRateIsComparedNeverAdopted` · `test_web_song_audio.py::TestTheSheetTempoDisagreementIsReportedThroughTheSession` | `34 passed` · `33 passed`. 시트 `120 (고정)` vs 측정 `128` → 채택 `128`(`source=measured`), 고지에 `128`·`120`·`어긋` 동시 포함 · 일치하면 어긋남 0건(대조군) · `FX-Rate` 역산 `100.0` 은 **측정도 시트도 없는 자리에서도** `source` 가 되지 않고 `default` 가 이김 · 역산의 비-일의성(「사이클당 박수」)이 보고 문자열에 명시 |

**번들 크기 실측 (AC-MUSICSYNC-017)** — 같은 기계 · 같은 명령 · 같은 워크트리

```
$ bash packaging/build.sh   # 변경 전 (librosa 없음)
build.sh: done -> dist/GrandMA3 Copilot.app
$ du -sk "dist/GrandMA3 Copilot.app"
65564	dist/GrandMA3 Copilot.app

$ bash packaging/build.sh   # 변경 후 (librosa + PyInstaller 훅)
build.sh: done -> dist/GrandMA3 Copilot.app
$ du -sk "dist/GrandMA3 Copilot.app"
274240	dist/GrandMA3 Copilot.app
```

델타 **208676 KiB = 203.8 MiB = 213.7 MB**. 판정선 **300MB 미만** →
**폴백은 선택되지 않았다.** 다만 폴백 스위치 자체는 구현·검증돼 있다
(`analysis_available()` + `test_audio_fallback.py` **11 passed**: 진짜
`ImportError` 아래에서 확인 카드가 서고, 수동 입력 BPM 128 이
`bpm_is_default=False` 까지 닿으며, 아무도 안 적으면 기본값 고지가 그대로 산다).

수집 실측: 번들에 `librosa`·`llvmlite`·`numba`·`numpy`·`scipy`·`sklearn`·`soxr`
트리와 `_soundfile_data/libsndfile_arm64.dylib` 가 들어갔고 수집 오류 0건.
동결 바이너리 부팅 확인 — `--self-check` → `self-check OK: macOS keyring backend
+ roundtrip verified`.

**RED 증거** (GREEN 이전에 관측한 그대로)

```
server/tests/test_audio_analyze.py:19: in <module>
    from server.audio.analyze import AnalysisFailure, AnalysisResult, analysis_available, analyze
E   ModuleNotFoundError: No module named 'server.audio'
```

```
    from server.web.messages import (
E   ImportError: cannot import name 'MAX_SONG_AUDIO_BYTES' from 'server.web.messages'
```

```
E   ImportError: cannot import name 'SongSectionProposal' from 'server.web.question'
E   ImportError: cannot import name 'BPM_SOURCE_DEFAULT' from 'server.design.profile'
2 errors in 0.09s
```

**전량 검사**

```
$ .venv/bin/python -m pytest -q -p no:cacheprovider server/tests
11204 passed, 9 skipped, 1 warning in 151.73s (0:02:31)

$ .venv/bin/ruff check server ui
All checks passed!
$ .venv/bin/ruff format --check server
495 files already formatted

$ npx tsc --noEmit   (ui/)
(출력 없음, exit 0)
$ npm --prefix ui run test
Test Files  21 passed (21) · Tests  506 passed (506)

$ git diff --name-only 793abb4..HEAD -- src-tauri server/lxseq server/orchestrator server/safety server/looks
(출력 없음 — 0줄)
$ git diff --name-only 793abb4..HEAD -- .moai/specs | wc -l
0
```

```
$ .venv/bin/python -m pytest -q --cov=server.audio --cov=server.web.question --cov=server.design.profile server/tests
server/audio/__init__.py       1      0   100%
server/audio/analyze.py      134     12    91%
server/design/profile.py     220      9    96%
server/web/question.py       120      2    98%
```

**설계 판단 기록 — plan.md M2 표와 다른 자리 하나**

확인 카드 빌더를 `server/web/question.py` **안**에 두었다. 표는 그 행을
「`question.py` 소비 측」이라 적었는데, 소비 측 후보 둘(`tools.py`·`session.py`)
중 `tools.py` 는 이번 회차의 PRESERVE 목록이고 `session.py` 는 카드를 **세우는**
자리가 아니라 **부르는** 자리다. 스키마(`QuestionRequest` 데이터클래스)는 한 글자도
바뀌지 않았고 그 사실을 필드 집합 시험이 고정한다 — 즉 「스키마 무변경」과
「빌더 추가」가 같은 파일에서 양립한다. `session.py` 는 그 빌더를 부르는
`analyse_song_audio` 를 갖는다.

**미검증(재지 못한 것 — 「비었음」이 아니다)**

- **동결 앱 안에서 librosa import 와 `analyze` 호출이 실제로 도는지 안 쟀다.**
  잰 것은 (a) 정적 수집(트리와 dylib 가 번들에 있다) (b) 동결 바이너리 부팅
  (`--self-check`)까지다. `--self-check` 는 키링만 보고, 동결 앱에 임의 코드를
  넣을 진입점이 없다. 이 공백은 실기 확인 몫이다.
- **AC-MUSICSYNC-016 의 「BPM 미지정, 120 기본값」 문구 절은 생산 지점에서만
  판정했다.** 저장소 전수에서 이 문구를 만드는 자리는 `interview.py`
  `_tempo_band_texture` 하나뿐이고, 그 사유 문자열은 `_build_q5` 의 중복 제거
  루프(`for label, _desc, texture`)에서 **버려진다** — 실측: `Q5_TEXTURE` 카드를
  직렬화하면 기본값 프로필에서도 이 문구가 **미포함**이다. 즉 오늘 이 문구는
  사용자 출력에 애초에 닿지 않는다. 소비 지점의 그 공백은 이 SPEC 의 범위가
  아니라 고치지 않았고, 판정은 생산 지점(문구가 붙고/사라진다)에서 했다.
- **시트 `HEAD.BPM` 과 분석의 실제 접합은 안 배선했다.** `analyse_song_audio` 는
  `sheet_bpm` 을 인자로 받고 그 경로를 시험이 지나지만, M1 임포터가 읽은 값을
  이 메서드로 넘기는 호출자는 `server/orchestrator/tools.py` 에 있어야 하고 그
  파일은 이번 회차의 PRESERVE 목록이다. AC-MUSICSYNC-018 은 `resolve_bpm` 과
  세션 층에서 판정했다.
- **실제 곡으로는 분석기를 안 재봤다.** 판정은 전부 합성 트랙이다(설계된 한계,
  design.md §6 W10). 구간 분절기는 **에너지 기반**이라 세기가 그대로인 음색·화성
  전환은 못 잡는다 — 합성 픽스처는 세기 계단으로 경계를 만들므로 이 한계가
  픽스처에서는 드러나지 않는다.
- **`analyze` 의 「파일 시스템 접촉 0건」은 데워진 뒤의 호출만 잰 값이다.**
  librosa/numba 의 **최초 import** 는 캐시 파일을 열며, 그것은 분석 행위가 아니라
  적재 행위라 판정에서 제외했다. 이 제외를 시험 독스트링에도 적어 두었다.
- 실기 콘솔 왕복 0건 — 이번 회차의 모든 관측은 오프라인이다.

## §E.3 Run-phase Audit-Ready Signal

```yaml
run_complete_at: 2026-09-05
run_commit_sha: pending-backfill-m2
run_status: audit-ready
milestone: M1 + M3-a + M2
milestone_evidence_note: "§E.2 는 M1·M3-a·M2 세 절을 담는다(오케스트레이터가 통합 시 합류). 아래 계수는 M2 회차 것"
ac_pass_count: 8            # M2: AC-MUSICSYNC-010..018 중 9개 판정, 8 PASS
ac_pass_with_debt_count: 1  # AC-MUSICSYNC-016 (문구 절은 생산 지점 판정)
ac_fail_count: 0
ac_scope: AC-MUSICSYNC-010..018 (M2 전량)
preserve_list_post_run_count: 5   # src-tauri · server/lxseq · server/orchestrator · server/safety · server/looks — 전부 diff 0줄
console_writes_emitted: 0
console_queries_emitted: 0
new_warnings_or_lints_introduced: 0
full_suite: "11204 passed, 9 skipped"
ui_typecheck: "npx tsc --noEmit exit 0"
ui_tests: "21 files / 506 tests passed"
coverage_new_module: "server/audio/analyze.py 91% · server/design/profile.py 96% · server/web/question.py 98%"
bundle_size_before_kib: 65564
bundle_size_after_kib: 274240
bundle_delta_mb: 213.7
bundle_cap_mb: 300
bundle_fallback_selected: false
unverified:
  - 동결 앱 안에서의 librosa import / analyze 호출
  - AC-016 문구 절의 소비 지점(_build_q5 가 사유 문자열을 버린다)
  - 시트 HEAD.BPM → analyse_song_audio 접합(호출자가 PRESERVE 파일에 있다)
  - 실제 곡 파일로의 분석기 검증
  - B9(음수 TrigTime 콘솔 수용) — M1 에서 넘어온 채 그대로
  - B4(재생 명령 효과) — M3-a 갈래 B, 이 채널로는 미관측
m1_to_mN_commit_strategy: "M2 는 논리 단위 5커밋(분석 코어 → 업로드 경로 → 카드/BPM → UI → 패키징)"
```

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_

## Plan Audit-Ready Signal

- plan_complete_at: 2026-09-04T00:02:42Z
- plan_status: audit-ready
- plan_audit: PASS 0.923 (iteration 2, .moai/reports/plan-audit/SPEC-COPILOT-MUSICSYNC-001-review-2.md) · review-2 D1 은 0.1.3 에서 문장 교체로 해소

## Run Phase 1 — Plan Audit Gate (2026-09-05)

- audit_verdict: PASS
- audit_score: 0.973 (iteration 3/3, delta re-check on v0.1.3; trend 0.857 → 0.923 → 0.973)
- audit_report: .moai/reports/plan-audit/SPEC-COPILOT-MUSICSYNC-001-review-3.md
- audit_at: 2026-09-05T05:17:07Z
- auditor_version: plan-auditor (opus, read-only, console contact 0)
- audit_cache_hit: false (v0.1.3 edit changed the artifact hash after review-2)
- post-audit fixes (orchestrator-direct, no REQ/AC change): spec.md HISTORY 0.1.3 row moved into the table; frontmatter `updated` → 2026-09-04
- anchor drift re-measured on main 3df3c06: tools.py anchors +73 lines (5385→5458 · 5404→5477 · 5405-5412→5478-5485 · 5417-5426→5490-5499 · 5427→5500 · 5984-5987→6057-6060); other 12 anchors unchanged

## §F Phase 4 Mode Selection (2026-09-05, M1)

- Input: tier L · M1 scope 7 files (1 new + 2 modify + 4 tests) · domains 1 (Python server) · language mix Python only · concurrency benefit LOW (coding-heavy, sequential TDD)
- direct: not selected (semantic change, multi-file) · serial: **selected** · fanout: not selected (single domain, coding-heavy) · sweep: not selected (not a mechanical transform)
- Decision: serial (manager-develop, cycle_type=tdd), Mode 5 envelope "Standard"
- Justification: M1 is one domain and every file depends on the parser's result-kind set, so per-file parallelism would race on the same contract. Anthropic's coding-task parallelism caveat applies. Implementation Kickoff Approval obtained 2026-09-05 (operator chose M1-first, autonomous progression).
- Worktree: .claude/worktrees/musicsync-m1 · branch WT-sheet-time-import · base origin/main 3df3c06
