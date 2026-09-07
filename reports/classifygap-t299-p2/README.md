# t299 Phase 2 실측 산출물 — SPEC-COPILOT-CLASSIFYGAP-001

`Store Sequence` **한 항목만** 넣는 Phase 2 회차의 증거다. 전부 **이 트리의
인터프리터**(`uv run`, Python 3.11.15, `server` 패키지는 이 워크트리)로 냈고,
base 는 `origin/main` `ca34ebe`(Phase 1 = PR #369 머지분)다.

`reports/classifygap-t299/`(plan 단계, 트리 `e0a2263`)와도,
`reports/classifygap-t299-p1/`(Phase 1, base `59ac394`)와도 **다른 회차**다.
plan 단계는 계측 플러그인으로 쟀고, 이 회차는 Phase 1 과 같이
`blacklist.yaml` 을 **실제로 고쳐서** 쟀다 — 그래서 플러그인 인공물이 안 섞인다.

## 이 회차의 결론 한 줄

분류 층 확대 자체는 옳다(대조군 전부 깨끗, Phase 3 대상 미접촉). 그러나
**큐시트 반영 자리에서 감독이 카드를 두 장 본다** — 그것 때문에 이 회차는
초록에 도달하지 못했고, 남은 판단은 감독의 것이다. `06` 이 그 실측이다.

## 파일

| 파일 | 무엇을 잰 것인가 |
|---|---|
| `00_baseline_ca34ebe.txt` | 확대 전 전체 스위트. `12011 passed · 19 skipped · 0 failed`, exit 0 (전체 12030) |
| `01_probe_before.txt` | 확대 전 분류기 프로브. 배차서가 지정한 다섯 명령 전부 — `Store Sequence …` 는 `matched_entry=None` |
| `02_cuesheet_cards_before.txt` | 확대 **전** 큐시트 반영 카드 수. **1장**(항목 5개), 감사 로그 `[('approved','draft_apply')]` |
| `03_cost_p2.txt` | **Phase 2 실제 확대 비용**. `32 failed · 11983 passed · 19 skipped` (전체 12034). plan 단계의 33(다른 트리)이 아니다 |
| `04_probe_after.txt` | 확대 직후 같은 프로브. `Store Sequence …` → `risky=True`, `Store Cue 1` 은 그대로 `None`, 음성 대조군 9문장 전부 `risky=False` |
| `05_risk_signals_detail.txt` | 위험 신호 8건의 실패 문면 전문. `카드 2장 — 묶음당 1장이어야 한다 / assert 2 == 1` 이 여기 있다 |
| `06_cuesheet_cards_after.txt` | 확대 **후** 큐시트 반영 카드 수. **2장** — `request_id` 가 서로 다르고(`approval-1`·`approval-2`), 둘째 장이 첫 장에서 이미 승인한 그 명령을 다시 묻는다. 감사 로그도 두 항목 |
| `07_seal_defence_after.txt` | `SEAL_DEFENCE` 귀속 재측정. **seal-only 7 → 2**, 다섯 자리가 움직였다(자리별 명령까지 찍혀 있다) |
| `08_fx_bundle_probe.txt` | FX 번들 17줄 중 걸리는 줄은 `Store Sequence 90 Cue 1 'M6'` **하나**. 같은 번들에 `showfile_write_risk` 를 물으면 「쇼파일 쓰기」라고 답한다 — 두 층이 같은 답을 말한다는 근거 |
| `09_mutation_revert_sequence.txt` | 뮤테이션 — `Store Sequence` 한 줄만 되돌림. `2 failed · 12010 passed · 19 skipped` (전체 12031). 둘 중 **분류를 관측하는 것은 하나뿐** |
| `10_suite_remaining_red.txt` | FX 핀 갱신 뒤 남은 빨강. 남은 것이 무엇인지 이 파일이 답한다 |
| `probe_p2.py` | `01`·`04` 의 소스. 배치된 `blacklist.yaml` 을 그대로 읽으므로 확대 전/후 어느 쪽에서도 돌아간다 |
| `probe_cuesheet_cards.py` | `02`·`06` 의 소스. 카드가 몇 장 뜨든 **전부** 승인하면서 장수를 센다 — 스위트 폴러가 첫 장만 승인하는 것과 달리, 「장수」와 「승인 누락」을 분리해서 잰다 |

`07` 은 Phase 1 의 `probe_seal_defence.py` 를 그대로 재사용했다(같은 질문, 같은 도구).

## 표가 스스로 검산되게

`03` · `09` · `10` 의 `FAILED` 줄 수가 위 표의 숫자와 일치한다. 전체 수도 함께
적었다 — **분모가 움직인다**: 항목 하나가 `test_writegate.py` 에서 테스트를 4개
만들고(12030 → 12034), 이 회차가 넣은 분류 핀 1건이 다시 +1 이다.

## 32건의 분류 (일괄 갱신 금지 — REQ-CG-009)

| 종류 | 건수 | 파일 |
|---|---|---|
| 1 — 갱신 대상 | 25 | `writegate_session_sites` 15 · `writegate_merge_gap` 5 · `safety_ruleset` 2 · `bulkgate_declaration` 2 · `fx_boundary` 1 |
| **중복 카드 결함 (감독 판단 대기)** | **7** | `web_cue_sheet_apply` 4 · `seeded_song_apply` 3 |
| 2 — 확대가 틀렸다는 신호 | 0 | — |
| 3 — 계측 인공물 | 0 | 계측 플러그인을 안 썼으므로 원리적으로 0 |

이 회차가 실제로 갱신한 것은 `fx_boundary` 1건뿐이다(근거는 그 파일의
docstring 과 `08`). 나머지 24건은 손대지 않았다 — plan.md §M1 이 「§A 판단이
닫히기 전에 코드를 고치지 않는다」고 못 박았고, §A-3 이 바로 아래 결함이다.

## 왜 7건이 「확대가 틀렸다」가 아닌가

7건 전부 **한 자리**다: 큐시트 초안 반영(`session.py:9041`). 실패 기전은
「쇼파일을 안 고치는 흐름이 승인을 요구하게 됨」이 아니라 **중복**이다.

- 이 자리는 확대 전에도 이미 카드를 띄웠다(`02`: 1장). 반영은 쇼파일 쓰기이고
  카드가 뜨는 것이 옳다.
- 확대 후 카드가 2장이 된다(`06`). 첫 장은
  `session.py::_accept_draft_apply_batch` 가 자기 채널로 받는 수락이고, 둘째
  장은 분류 층이 만든다. `ExecutionContext.approval_owned_by_caller` 는 *봉합*
  카드만 막고 분류 카드는 막지 않는다(`gate.py:399·415`).
- 스위트의 폴러는 첫 장만 승인하고 돌아간다(두 파일 모두 `_run_with_auto_approval`).
  그래서 둘째 장이 타임아웃으로 거절되고 `console.executed == []` 가 된다 —
  일곱 검사가 빨개지는 기전이 전부 이것 하나다.

중복 카드는 감독이 카드를 안 읽게 만드는 바로 그 사고다. 절충이 아니라 결함이고,
고치는 자리(`session.py` 또는 `server/safety/gate.py`)는 이 SPEC 의 선언 범위
밖이다.

## 이 회차가 재지 않은 것

- **실기 검증 0건.** 콘솔은 오프라인이고 포트 8000 에 접촉하지 않았다.
- **전체 스위트 초록.** 위 결함 때문에 도달하지 못했다. `10` 이 남은 빨강이다.
- **남은 24건의 갱신 후 비용.** 갱신을 안 했으므로 「갱신 뒤 전체 초록」 값이 없다.
- **`Store Cue`(Phase 3) 확대 비용.** 이 회차에서 재지 않았다.
- **FX 회차의 카드 수를 흐름 단위로 센 값.** `08` 은 번들의 분류만 재고,
  `07` 은 자리별 귀속만 잰다. FX 흐름이 카드 한 장인지 두 장인지는
  `test_fx_boundary.py` 의 레지스트리 검사들이 통과한다는 간접 증거뿐이다.
- **다른 `approval_owned_by_caller` 자리(`session.py:9999`)의 카드 수.**
  큐시트 자리만 셌다.
