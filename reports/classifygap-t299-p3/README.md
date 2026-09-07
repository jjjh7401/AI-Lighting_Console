# t299 Phase 3 실측 산출물 — SPEC-COPILOT-CLASSIFYGAP-001

`Store Cue` **한 항목**을 폐집합에 넣은(v6 → v7) **마지막** 회차의 증거다. 전부
**이 트리의 인터프리터**(`uv run`, Python 3.11.15, `server` 패키지도 이 워크트리)로
냈고, base 는 `origin/main` `e158e44`(Phase 2 = PR #370 머지분)다.

`reports/classifygap-t299/`(plan 단계, 트리 `e0a2263`) ·
`reports/classifygap-t299-p1/`(Phase 1, base `59ac394`) ·
`reports/classifygap-t299-p2/`(Phase 2, base `ca34ebe`)와도 **다른 회차**다.
plan 단계는 계측 플러그인으로 쟀고, 이 회차는 Phase 1·2 와 같이 `blacklist.yaml` 을
**실제로 고쳐서** 쟀다 — 그래서 플러그인 인공물이 안 섞인다.

## 이 회차의 결론

이 SPEC 이 닫으려던 네 명령이 **다 닫혔다**. 전체 스위트
`12017 passed · 31 skipped · 0 failed`, exit 0.

한 단계로 끝났다 — Phase 2 처럼 「확대가 드러낸 결함」을 따로 닫을 일이 없었다.
큐시트 반영 한 동작의 카드 수는 확대 전후 모두 **1장**이고, `SEAL_DEFENCE` 귀속도
움직이지 않았다.

`server/safety/*.py` 코드는 **한 줄도 안 고쳤다**(`git diff --stat -- 'server/safety/*.py'`
출력 없음). 고친 곳은 `blacklist.yaml`(데이터) · `corpus.yaml`(헤더 고지) · 갱신된
핀 테스트 11개다.

## 실측 요약

| 항목 | 값 |
|---|---|
| 기준선 (확대 전) | `12012 passed · 31 skipped · 0 failed`, exit 0 (전체 12043) |
| 이 항목 투입 비용 | `33 failed · 11983 passed · 31 skipped` (전체 12047) |
| plan 단계 예측 | **62** (트리 `e0a2263`, 계측 플러그인, 전체 12021) — **옮겨 쓰지 않았다** |
| 최종 (갱신 후) | `12017 passed · 31 skipped · 0 failed`, exit 0 (전체 12048) |
| 뮤테이션 (한 줄 되돌림) | `6 failed · 12007 passed · 31 skipped` (전체 12044) |
| 큐시트 카드 수 | 확대 전 **1장** → 확대 후 **1장** (변화 없음) |
| `SEAL_DEFENCE` | 자리 11, seal-only **2 / 11** — 확대 전과 **같다** |
| 종류 2(확대가 틀렸다는 신호) | **0건** |
| 실기 콘솔 접촉 | **0건** |

### 왜 62 가 아니라 33 인가

옮겨 쓰지 않고 이 트리에서 다시 쟀다. 차이는 전제가 셋 달라진 결과다.

1. 분모가 v5·v6 으로 두 번 움직였다(12021 → 12043).
2. Phase 1·2 가 「안전한 예」 리터럴 여럿을 이미 비-`Store` 명령으로 옮겼다 —
   plan 단계에 있던 충돌 상당수가 그때 사라졌다.
3. 계측 플러그인 인공물(plan 단계 2건)이 이 회차에는 원리적으로 안 섞인다.

### 전체 수가 12047 → 12048 인 이유 (표가 스스로 검산되게)

항목 하나가 `test_writegate.py` 에서 테스트를 4개 만든다(12043 + 4 = 12047).
그 뒤 이 회차가 검사를 **셋 더하고 둘 뺐다** → 순 +1 = 12048.

- 더한 셋: `test_the_option_axis_literal_is_still_outside_the_closed_set` ·
  `test_the_entry_order_preserves_the_sequence_attribution` ·
  `test_direct_blacklist_commands_are_blacklisted[Store Cue 1]`(파라미터 1개)
- 뺀 둘: `test_writegate.py::…test_the_form_stays_non_risky[Store Cue 12-…]` ·
  `test_showfile_replacement_gate.py::…test_classification_did_not_move[Store Cue 12]`
  (둘 다 `UNCHANGED_SAFE`/`UNCHANGED` 에서 그 줄을 뺐으므로 파라미터가 사라진다)

## 33건의 분류 (일괄 갱신 금지 — REQ-CG-009)

| 종류 | 건수 | 처리 |
|---|---|---|
| 1 — 갱신 대상 | **33** | 개별 근거를 주석/docstring 에 적고 갱신 |
| 2 — 확대가 틀렸다는 신호 | **0** | — |
| 3 — 계측 인공물 | **0** | 계측 플러그인을 안 썼으므로 원리적으로 0 |
| `[NEEDS CLARIFICATION]` | **0** | 감독 판단이 필요한 자리가 없었다 |

파일별 33건: `safety_gate` 14 · `safety_classify` 6 · `writegate` 2 ·
`safety_ruleset` 2 · `safety_expand` 2 · `deploy_scan` 2 · `writegate_merge_gap` 1 ·
`showfile_replacement_gate` 1 · `safety_e2e_audit` 1 · `safety_corpus` 1 ·
`safety_bootstrap` 1.

**33건 전부가 같은 모양이었다**: `Store Cue <n>` 을 「안전한 예 / 깨끗한 본문 /
benign 본문」 리터럴로 쓰던 배관 검사, 또는 폐집합·버전·코퍼스 장부 핀. 쇼파일을
안 고치는 흐름이 승인을 요구하게 된 자리는 하나도 없다.

### 위험 신호 파일이 이 회차에 **없다**

plan 단계 §D.2 가 종류 2 후보로 든 파일들(`test_web_cue_sheet_apply` ·
`test_seeded_song_apply` · `test_fx_boundary`)과 `test_writegate_session_sites` 는
33건에 **한 건도** 없다. 측정 명령·출력:
`grep -cE 'web_cue_sheet_apply|seeded_song_apply|fx_boundary|writegate_session_sites' 03_cost_p3.txt` → `0`.

이유는 두 가지다. 그 자리들이 실어 나르는 쇼파일 쓰기는 `Store Sequence <N> Cue <M>`
이고 v6 이 이미 잡았으므로 이 확대가 새로 건드릴 것이 없다. 그리고 Phase 2 가
큐시트 반영의 중복 질문자를 제거해 그 자리가 이미 봉합이 됐다.

### 리터럴을 옮긴 방향 — Phase 1 의 교훈을 지켰다

「안전한 예」 리터럴은 **프로그래머 값**(`Fixture <n> At 50` 등)으로 옮겼다. 폐집합은
쇼파일 **쓰기** 오브젝트만 담으므로 어떤 리비전도 그쪽을 다시 잡지 않는다. Phase 1 은
하나를 당시 남은 구멍(`Store Sequence`)으로 옮겼다가 한 리비전 만에 다시 잃었다.

**예외 하나, 근거를 적어 남긴다.** `test_safety_classify.py` 의 옵션 축 검사 셋은
재는 축이 「`Store` 를 위험하게 만드는 것은 동사가 아니라 `/overwrite` **옵션**」
이어서 `Store` 가 아닌 명령으로는 축 자체가 사라진다. 그래서 폐집합 밖의 `Store`
오브젝트(`Store Page 3`)를 쓰고, 그 전제를 `_OPTION_AXIS_OBJECT` 한 곳에서 읽게 한
뒤 `test_the_option_axis_literal_is_still_outside_the_closed_set` 으로 따로 지킨다 —
후속 카드가 `Store Page` 를 넣는 날, 실패 메시지가 「축이 깨졌다」가 아니라
「리터럴의 전제가 깨졌으니 이렇게 옮겨라」를 직접 말한다.

### 빨개지지 않았지만 갱신한 것 하나 (조용히 공허해지는 자리)

`test_safety_classify::test_option_abbreviation_still_matches` 는 33건에 **없다** —
초록이었다. 그러나 옛 형태(`Store Cue 5 /o` 의 `category == "blacklisted"`)는 v7
이후 **옵션을 아예 못 읽어도** 오브젝트가 걸려서 초록이 된다. 재려던 축이 다른 축에
가려지는 모양이라, 리터럴을 옮기고 `matched_entry == "Store /overwrite"` 를 단언하도록
바꿨다. 비용 33건에는 안 들어가지만 갱신하지 않으면 방어가 조용히 사라지는 자리다.

## 배차서 전제 하나를 실측으로 정정했다

배차서는 「your widening adds a second matching entry to the same bundle. It must
stay 1」이라고 적었다. 카드 수가 1장으로 유지된다는 결론은 맞지만, **기전이 다르다** —
그리고 그 차이가 리비전의 배치 결정을 좌우한다.

`08_entry_order.txt` 가 합성 룰셋 셋으로 잰 것:

| 룰셋 | `Store Sequence 210 Cue 10 /Merge` 의 `matched_entry` |
|---|---|
| ① 배치된 순서 (`Store Sequence` 앞) | `'Store Sequence'` |
| ② `Store Cue` **만** 든 룰셋 | `'Store Cue'` — 항목이 그 줄에 **닿는다** |
| ③ `Store Cue` 를 앞으로 뒤집은 순서 | `'Store Cue'` — 귀속이 **바뀐다** |

즉 항목 수준에서는 두 번째 일치가 성립하지만, `classify.py::_match_blacklist` 가
**첫** 일치에서 즉시 돌아오므로 두 번째 사유는 카드에 실리지 않는다. 그래서
「사유가 둘 병기된다」가 아니라 「귀속이 v6 그대로 보존된다」가 이 배치의 성질이다.
항목을 목록 **끝**에 둔 것이 그 보존의 조건이고, 그 조건을 주석이 아니라
`test_the_entry_order_preserves_the_sequence_attribution` 이 지킨다.

## 뮤테이션 모양이 Phase 1·2 와 **다르다**

한 줄만 되돌리면 6건이 빨개진다. Phase 1·2 는 「분류를 관측하는 단언이 **하나**뿐」
이었지만 이 회차는 **셋**이다 — 같은 문장으로 보고하면 틀린다.

| # | 빨개지는 검사 | 무엇을 관측하나 |
|---|---|---|
| 1 | `test_safety_classify::test_direct_blacklist_commands_are_blacklisted[Store Cue 1]` | **분류** (표준 핀) |
| 2 | `test_deploy_scan::test_quoted_object_name_never_matches` | **분류** (이 회차가 넣은 비공허성 짝) |
| 3 | `test_writegate_merge_gap::test_the_entry_order_preserves_the_sequence_attribution` | **분류** (이 회차가 넣은 비공허성 짝) |
| 4 | `test_safety_ruleset::test_blacklist_is_exactly_the_shipped_closed_set` | 장부 (멤버십·개수) |
| 5 | `test_writegate::test_the_measurement_corpus_cannot_collide_with_this_entry` | 장부 (코퍼스 충돌 목록) |
| 6 | `test_writegate_merge_gap::test_the_blacklist_now_carries_every_store_object_this_spec_scoped` | 장부 (Store 계열 목록) |

분류 관측이 셋이 된 것은 이 회차가 비공허성 짝을 둘 더 넣었기 때문이고 의도한
결과다 — 핀 하나에만 의존하면 그 핀이 지워질 때 방어가 통째로 조용해진다.

버전 핀(`version == 7`)은 이 뮤테이션에서 **안** 빨개진다(항목만 되돌리고 버전은
그대로 뒀으므로). 그래서 위 6건은 전부 항목 자체에 귀속된다.

## `SEAL_DEFENCE` — 손으로 안 고쳤고, 고칠 것이 없었다

`07_seal_defence_p3.txt` 가 자리별로 재고, 그 출력이 배치된
`test_writegate_session_sites.py::SEAL_DEFENCE` 와 **줄 단위로 일치**한다. 그래서 그
파일의 diff 는 **없다**(`git diff --stat -- server/tests/test_writegate_session_sites.py`
출력 없음).

| | Phase 2 뒤 | Phase 3 뒤 |
|---|---|---|
| 자리 수 | 11 | 11 |
| seal-only | 2 | **2** |

**AC-CG-005 는 Phase 2 에서 이미 PASS 다**(7 → 2). 이 회차는 그 수를 더 줄이지
못하고 유지한다. 남은 두 자리가 실어 나르는 것이
`Assign Sequence`(`_offer_fx_executor_assignment`) 와
`Copy Sequence`+`Assign Sequence`(`_setlist_mode`) 뿐이고, SPEC §F 가 그 둘을
범위 밖에 뒀기 때문이다. **파생 추정이 아니라 자리별 실측이다** — 카드 **t325** 가
그 둘을 받는다.

## 파일

| 파일 | 무엇을 잰 것인가 |
|---|---|
| `00_baseline_e158e44.txt` | 확대 전 전체 스위트. `12012 passed · 31 skipped · 0 failed`, exit 0 (전체 12043) |
| `01_probe_before.txt` | 확대 전 분류기 프로브. 여섯 명령 — `Store Cue 1` 은 `matched_entry=None`, AC-CG-001 은 **3/4** |
| `02_cuesheet_cards_before.txt` | 확대 **전** 큐시트 반영 카드 수. **1장**(항목 5), 감사 로그 `[('approved','draft_apply')]` |
| `03_cost_p3.txt` | **Phase 3 실제 확대 비용**. `33 failed · 11983 passed · 31 skipped` (전체 12047) |
| `04_probe_after.txt` | 확대 직후 프로브. 네 `Store` 형태 전부 `risky=True`(AC-CG-001 **4/4**), `Fixture 1 At 50`·`Group 4` 는 그대로 `None` |
| `05_risk_signals_detail.txt` | 판정이 필요했던 후보들의 실패 문면 전문(배관·확장·코퍼스·부트스트랩·감사·deploy) |
| `06_cuesheet_cards_after.txt` | 확대 **후** 카드 수. **1장** — 항목 5, 귀속은 `'Store Sequence'` 그대로 |
| `07_seal_defence_p3.txt` | `SEAL_DEFENCE` 귀속 재측정. 자리 11, seal-only **2 / 11**(변화 없음) |
| `08_entry_order.txt` | 항목 **순서**가 귀속을 바꾸는가 — 합성 룰셋 셋으로 잰 값. 위 「배차서 전제 정정」의 근거 |
| `09_mutation_revert_cue.txt` | 항목 뮤테이션 — `Store Cue` 한 줄만 되돌림. `6 failed · 12007 passed` (전체 12044) |
| `10_suite_final.txt` | 최종 전체 스위트. `12017 passed · 31 skipped · 0 failed`, exit 0 (전체 12048) |
| `11_probe_final.txt` | 최종 분류기 프로브 + 음성 대조군. 잘못 판정 0건, 흐름 단위 카드 **0장** |
| `12_cuesheet_cards_final.txt` | 갱신 후 큐시트 카드 수 재확인. **1장**, `kind='draft_apply'` 보존 |
| `13_cuesheet_reject.txt` | 그 한 장을 **거절**했을 때. 콘솔 **0건**, 감사 로그 `[('rejected','draft_apply')]` |

### 프로브 소스

| 파일 | 무엇을 하는가 |
|---|---|
| `probe_p3.py` | `01`·`04`·`11`. 배치된 `blacklist.yaml` 을 그대로 읽으므로 확대 전/후 어느 쪽에서도 돌아간다 |
| `probe_entry_order.py` | `08`. 배치본은 안 건드리고 **합성 룰셋**으로 순서 축만 잰다 |
| `probe_cuesheet_cards.py` | `02`·`06`·`12`. 카드가 몇 장 뜨든 전부 승인하면서 장수를 센다 — 「장수」와 「승인 누락」을 분리해서 잰다 |
| `probe_cuesheet_reject.py` | `13`. 같은 하네스, 폴러만 전부 거절로 바꿨다 |
| `probe_seal_defence_p3.py` | `07`. 비교 없이 **측정만** 하고, 표에 붙여 쓸 형태로 출력한다 |
| `_retarget_gate_literals.py` | `test_safety_gate.py` 의 운반용 리터럴을 **빨개진 검사 함수 본문 안에서만** 치환한 일회용 스크립트. 무엇을 바꿨는지 출력으로 남기려고 파일로 뒀다(`대상 검사 14개, 치환된 줄 34개`) |

## 표가 스스로 검산되게

`03` · `09` · `10` 의 `FAILED` 줄 수가 위 표의 숫자와 일치한다. 전체 수도 함께
적었다 — **분모가 움직인다**(위 「12047 → 12048」 절이 그 산수를 적는다).

## 이 회차가 재지 않은 것

- **실기 검증 0건.** 콘솔은 오프라인이고 포트 8000 에 접촉하지 않았다
  (측정: `git diff -- server/ | grep -c 8000` → 0).
- **`Store Page`·`Store Macro`·`Assign`·`Copy` 의 확대 비용.** §F 범위 밖이라
  안 쟀다. `Store Page` 는 이제 옵션 축 리터럴로도 쓰이므로, 그 오브젝트를 넣는
  후속 카드는 `_OPTION_AXIS_OBJECT` 이동을 함께 계획해야 한다.
- **`SEAL_DEFENCE` 두 자리를 0 으로 만드는 경로.** 이 SPEC 으로는 불가하다는 것만
  실측했고, `Assign`/`Copy` 를 넣었을 때의 비용은 안 쟀다(카드 t325).
- **UI 렌더.** 카드가 화면에 몇 개로 그려지는지는 서버 이벤트(`approval_request`)
  수로만 쟀다. `ui/` 는 안 건드렸고 안 쟀다.
- **명시 선언과 레지스트리 자동 선언을 동시에 없앤 뮤테이션.** Phase 2 가 범위 밖에
  둔 그대로 남는다.
- **`test_safety_classify::TestExecutorRenameInvariance` 의 parametrize 공허성.**
  두 파라미터의 본문이 바이트 동일해서 before/after 를 구분하지 못한다는 것은
  **관측했고 문면으로 남겼지만 고치지 않았다** — 이 SPEC 의 범위가 아니다.
