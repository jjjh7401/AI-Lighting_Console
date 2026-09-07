# t299 Phase 2 실측 산출물 — SPEC-COPILOT-CLASSIFYGAP-001

`Store Sequence` **한 항목**을 폐집합에 넣고(v5 → v6), 그 확대가 드러낸 **중복 카드
결함**까지 닫은 회차의 증거다. 전부 **이 트리의 인터프리터**(`uv run`,
Python 3.11.15, `server` 패키지는 이 워크트리)로 냈고, base 는 `origin/main`
`ca34ebe`(Phase 1 = PR #369 머지분)다.

`reports/classifygap-t299/`(plan 단계, 트리 `e0a2263`)와도,
`reports/classifygap-t299-p1/`(Phase 1, base `59ac394`)와도 **다른 회차**다.
plan 단계는 계측 플러그인으로 쟀고, 이 회차는 Phase 1 과 같이 `blacklist.yaml` 을
**실제로 고쳐서** 쟀다 — 그래서 플러그인 인공물이 안 섞인다.

## 이 회차의 결론

분류 층 확대는 옳았고, 확대가 드러낸 결함 하나를 같이 닫았다. 전체 스위트
`12012 passed · 31 skipped · 0 failed`, exit 0.

두 단계로 읽으면 된다.

1. **확대** (`01`~`10`). `Store Sequence` 를 넣었다. 실측 비용 32건 / 전체 12034.
   대조군 전부 깨끗, `Store Cue`(Phase 3) 미접촉. 그런데 큐시트 반영 한 동작에
   승인 카드가 **두 장** 뜨는 것이 실측됐다(`06`) — 그 자리가 t292 때부터 자기
   승인 채널로 수락을 따로 받고 있었기 때문이다.
2. **결함 수정** (`11`~`17`). 그 임시 채널을 걷어내고 `BatchRisk` 선언으로 바꿔
   **게이트가 유일한 질문자**가 되게 했다. 카드 1장, 사유 둘 병기, 감사 로그
   `kind` 보존, 거절 시 콘솔 0건. 위험 신호 7건은 **갱신 없이** 초록이 됐다.

`server/safety/*.py` 코드는 **한 줄도 안 고쳤다**. 고친 곳은 `blacklist.yaml`(데이터),
`session.py`(중복 질문자 제거 — 순 **-28줄**), 그리고 갱신된 핀 테스트들이다.

## 파일

### 1단계 — 확대

| 파일 | 무엇을 잰 것인가 |
|---|---|
| `00_baseline_ca34ebe.txt` | 확대 전 전체 스위트. `12011 passed · 19 skipped · 0 failed`, exit 0 (전체 12030) |
| `01_probe_before.txt` | 확대 전 분류기 프로브. 지정된 다섯 명령 — `Store Sequence …` 는 `matched_entry=None` |
| `02_cuesheet_cards_before.txt` | 확대 **전** 큐시트 반영 카드 수. **1장**(항목 5), 감사 로그 `[('approved','draft_apply')]` |
| `03_cost_p2.txt` | **Phase 2 실제 확대 비용**. `32 failed · 11983 passed · 19 skipped` (전체 12034) |
| `04_probe_after.txt` | 확대 직후 프로브. `Store Sequence …` → `risky=True`, `Store Cue 1` 은 그대로 `None`, 음성 대조군 9문장 전부 `risky=False` |
| `05_risk_signals_detail.txt` | 위험 신호 8건의 실패 문면 전문. `카드 2장 — 묶음당 1장이어야 한다 / assert 2 == 1` 이 여기 있다 |
| `06_cuesheet_cards_after.txt` | 확대 **후** 카드 수. **2장** — `request_id` 가 다르고(`approval-1`·`approval-2`), 둘째 장이 첫 장에서 이미 승인한 그 명령을 다시 묻는다 |
| `07_seal_defence_after.txt` | 수정 **전** `SEAL_DEFENCE` 재측정. seal-only **7 → 2**, 다섯 자리 이동(열 자리 기준) |
| `08_fx_bundle_probe.txt` | FX 번들 17줄 중 걸리는 줄은 `Store Sequence 90 Cue 1 'M6'` **하나**. 같은 번들에 `showfile_write_risk` 를 물으면 「쇼파일 쓰기」라고 답한다 — 두 층이 같은 답을 한다는 근거 |
| `09_mutation_revert_sequence.txt` | 항목 뮤테이션 — `Store Sequence` 한 줄만 되돌림. `2 failed · 12010 passed` (전체 12031). 둘 중 **분류를 관측하는 것은 하나뿐** |
| `10_suite_remaining_red.txt` | FX 핀만 갱신한 중간 상태. `31 failed` — 24 갱신 대상 + 7 결함 |

### 2단계 — 중복 카드 수정

| 파일 | 무엇을 잰 것인가 |
|---|---|
| `11_cuesheet_cards_after_fix.txt` | 수정 후 카드 수. **1장**(항목 5). `Store Sequence` 줄에 선언 사유와 분류 사유가 **둘 다** 실린다. 감사 로그 `[('approved','draft_apply')]` — `kind` 보존 |
| `12_cuesheet_reject.txt` | 그 한 장을 **거절**했을 때. 콘솔 **0건**, 답장 「승인받지 못해 … 콘솔에는 아무것도 쓰지 않았습니다」, 감사 로그 `[('rejected','draft_apply')]` |
| `13_seal_defence_after_fix.txt` | `SEAL_DEFENCE` **재측정**. 자리 **10 → 11**(반영 자리가 봉합이 됐다), seal-only **2 / 11**. 표에 넣은 값은 이 파일 끝의 출력을 그대로 옮긴 것 |
| `14_suite_final.txt` | 최종 전체 스위트. `12012 passed · 31 skipped · 0 failed`, exit 0 (전체 12043) |
| `15_probe_final.txt` | 최종 분류기 프로브 + 음성 대조군. 잘못 판정 0건, 흐름 단위 카드 **0장** |
| `16_mutation_seal_none.txt` | 봉합 뮤테이션 — 반영 자리의 `risk` 를 `None` 으로. `2 failed · 12010 passed · 31 skipped` (전체 12043) |
| `17_mutation_card_shape.txt` | 위 뮤테이션에서 **카드가 어떻게 되는가**. 아래 「뮤테이션이 약한 이유」 참조 |

### 프로브 소스

| 파일 | 무엇을 하는가 |
|---|---|
| `probe_p2.py` | `01`·`04`·`15`. 배치된 `blacklist.yaml` 을 그대로 읽으므로 확대 전/후 어느 쪽에서도 돌아간다 |
| `probe_cuesheet_cards.py` | `02`·`06`·`11`·`17`. 카드가 몇 장 뜨든 **전부 승인**하면서 장수를 센다 — 스위트 폴러가 첫 장만 승인하는 것과 달리, 「장수」와 「승인 누락」을 분리해서 잰다 |
| `probe_cuesheet_reject.py` | `12`. 같은 하네스, 폴러만 **전부 거절**로 바꿨다 |
| `probe_seal_defence_p2.py` | `13`. Phase 1 판은 표에 없는 자리에서 `KeyError` 로 멈춘다(자리가 하나 늘었으므로). 이 판은 비교 없이 **측정만** 하고, 표에 붙여 쓸 형태로 출력한다 |

`07` 은 Phase 1 의 `probe_seal_defence.py` 를 그대로 재사용했다(수정 전 시점).

## 표가 스스로 검산되게

`03` · `09` · `10` · `14` · `16` 의 `FAILED` 줄 수가 위 표의 숫자와 일치한다.
전체 수도 함께 적었다 — **분모가 움직인다**: 항목 하나가 `test_writegate.py` 에서
테스트를 4개 만들고(12030 → 12034), 이 회차가 넣은 검사들이 다시 더한다
(최종 12043). `skipped` 도 19 → 31 로 움직였다: seal-only 가 7 → 2 로 줄면서
skip 조건이 걸리는 자리가 늘었다(두 검사 × 자리 수).

## 32건의 분류 (일괄 갱신 금지 — REQ-CG-009)

| 종류 | 건수 | 처리 |
|---|---|---|
| 1 — 갱신 대상 | 25 | 개별 근거를 적고 갱신. `writegate_session_sites` 15 · `writegate_merge_gap` 5 · `safety_ruleset` 2 · `bulkgate_declaration` 2 · `fx_boundary` 1 |
| 중복 카드 결함 | 7 | **갱신하지 않았다.** 원인을 고쳤고 7건이 그대로 초록이 됐다(`git diff --stat` 로 두 파일 무수정 확인) |
| 2 — 확대가 틀렸다는 신호 | 0 | — |
| 3 — 계측 인공물 | 0 | 계측 플러그인을 안 썼으므로 원리적으로 0 |

## 왜 7건이 「확대가 틀렸다」가 아니었나

7건 전부 **한 자리**였다: 큐시트 초안 반영(`session.py::_cue_sheet_draft_apply`).
실패 기전은 「쇼파일을 안 고치는 흐름이 승인을 요구하게 됨」이 아니라 **중복**이었다.

- 이 자리는 확대 전에도 이미 카드를 띄웠다(`02`: 1장). 반영은 쇼파일 쓰기이고
  카드가 뜨는 것이 옳다.
- 확대 후 2장이 됐다(`06`). 첫 장은 `_accept_draft_apply_batch` 가 자기 채널로
  받는 수락, 둘째 장은 분류 층이 만든 것. `approval_owned_by_caller` 는 *봉합*
  카드만 막고 분류 카드는 막지 않는다(`gate.py` `approval_findings`).
- 스위트의 폴러는 첫 장만 승인하고 돌아가므로(두 파일 모두
  `_run_with_auto_approval`) 둘째 장이 타임아웃 거절되고 `console.executed == []`
  가 된다 — 일곱 검사가 빨개지는 기전이 전부 이것 하나였다.

**고친 방향은 억제가 아니라 제거다.** `approval_owned_by_caller` 가 분류 카드까지
막게 하면 호출자가 최후 방어층의 눈을 감길 권한을 갖는다(fail-closed 의 반대).
대신 두 번째 질문자를 없앴다 — `_accept_draft_apply_batch` 를 지우고 `BatchRisk`
선언을 실어 게이트가 유일한 질문자가 되게 했다. 사유는 손으로 적지 않고
`write_reason.showfile_write_risk` 가 **나갈 명령에서** 읽는다(t323 규율, 열 자리
봉합과 같은 함수).

## 뮤테이션이 약한 이유 (`16` · `17`) — 실측으로 확인한 것

반영 자리의 `risk` 를 `None` 으로 되돌리면 **2건**만 빨개지고, 둘 다 `kind`
관측이다(`test_the_acceptance_is_written_to_the_audit_log` ·
`test_the_audit_names_this_site[_cue_sheet_draft_apply]`).

카드가 사라지지 않는다. `17` 이 그 이유를 찍는다: 카드는 여전히 **1장 · 항목 5 ·
사유 둘**이고, 감사 로그의 `kind` 만 `draft_apply` → **`model_run_commands`** 로
바뀐다. `tools.py::dispatch_run_commands` 가 `risk is None` 이고
`approval_owned_by_caller` 도 아니면 **선언을 스스로 만든다**(t323 모델 통로
받침, 같은 `showfile_write_risk`).

즉 이 자리의 방어는 셋이다: 명시 선언 → 레지스트리 자동 선언 → 분류 층. 명시
선언의 고유 기여는 이제 **카드가 아니라 `kind` 귀속**이고, 그것을 2건이 관측한다.
「분류를 관측하는 단언이 하나뿐」이라는 Phase 1·2 의 성질과는 **다른 모양**이다 —
같은 문장으로 보고하면 틀린다.

## 이 회차가 재지 않은 것

- **실기 검증 0건.** 콘솔은 오프라인이고 포트 8000 에 접촉하지 않았다.
- **명시 선언과 레지스트리 자동 선언을 **동시에** 없앤 경우.** 그때 카드가
  분류 층만으로 1항목이 되는지, 그것을 관측하는 검사가 있는지는 안 쟀다.
  위 「방어 셋」 중 둘을 동시에 빼는 뮤테이션은 이 회차 범위 밖이다.
- **`Store Cue`(Phase 3) 확대 비용.** 안 쟀다.
- **FX 흐름 단위 카드 수.** `08` 은 번들 분류만, `13` 은 자리별 귀속만 잰다.
  FX 흐름이 카드 한 장인지는 `test_fx_boundary.py` 의 레지스트리 검사가
  통과한다는 **간접** 증거뿐이다.
- **`session.py:9999`(`_song_finalize` 경로)의 카드 수.** 그 자리도
  `approval_owned_by_caller=True` 를 쓰는데, 큐시트 자리만 셌다. 그 자리는 명시
  선언(`risk=`)을 이미 함께 싣고 있어 같은 결함 모양이 아니지만, **카드를 센
  것은 아니다.**
- **UI 렌더.** 카드가 화면에 몇 개로 그려지는지는 서버 이벤트(`approval_request`)
  수로만 쟀다. `ui/` 는 안 건드렸고 안 쟀다.
