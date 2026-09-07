# t299 Phase 1 실측 산출물 — SPEC-COPILOT-CLASSIFYGAP-001

`Store Group` · `Store Timecode` 두 항목만 넣는 Phase 1 회차의 증거다. 전부
**이 트리의 인터프리터**(`uv run`, Python 3.11.15, `server` 패키지는 이 워크트리)로
냈고, base 는 `origin/main` `59ac394` 다.

`reports/classifygap-t299/`(plan 단계, 트리 `e0a2263`)와 **다른 회차**다. plan 단계는
계측 플러그인으로 `server/safety/` 를 안 고치고 쟀고, 이 회차는 `blacklist.yaml` 을
**실제로 고쳐서** 쟀다 — 그래서 플러그인 인공물 2건이 섞이지 않는다.

## 파일

| 파일 | 무엇을 잰 것인가 |
|---|---|
| `00_baseline_59ac394.txt` | 확대 전 전체 스위트. `12002 passed · 19 skipped · 0 failed`, exit 0 |
| `01_probe_before.txt` | 확대 전 분류기 프로브. 두 명령 전부 `matched_entry=None / risky=False` — 구멍이 이 트리에서도 열려 있었다 |
| `02_probe_after.txt` | 확대 직후 같은 프로브. 두 명령 전부 `risky=True`, 음성 대조군 9문장 전부 `risky=False` |
| `03_cost_p1_combined.txt` | **Phase 1 실제 동시 투입 비용**. `14 failed · 11996 passed · 19 skipped` (전체 12029). 개별값 6+13 의 합이 아니다 |
| `04_suite_after_updates.txt` | 갱신 대상 테스트를 고친 뒤. `12011 passed · 0 failed` |
| `05_seal_defence_after.txt` | `SEAL_DEFENCE` 귀속 재측정. **seal-only 7 → 7, 움직인 자리 0건** |
| `06_mutation_revert_timecode.txt` | 뮤테이션 — `Store Timecode` 한 줄만 되돌림. `3 failed · 12004 passed` (전체 12026) |
| `07_ruff.txt` | `uv run ruff check server/` → `All checks passed!` |
| `08_probe_final.txt` | 뮤테이션 복원 뒤 프로브 재실행. `02` 와 같은 답 |
| `09_suite_final.txt` | 최종 전체 스위트. `12011 passed · 19 skipped · 0 failed`, exit 0 |
| `probe_p1.py` | 위 프로브의 소스. 배치된 `blacklist.yaml` 을 그대로 읽으므로 확대 전/후 어느 쪽에서도 돌아간다 |
| `probe_seal_defence.py` | `SEAL_DEFENCE` 귀속 프로브. 검사가 안 알려 주는 「왜 안 움직였나」까지 찍는다 |

## 표가 스스로 검산되게

`03` 과 `06` 의 `FAILED` 줄 수가 위 표의 숫자와 일치한다. 전체 수도 함께 적었다 —
분모가 움직이기 때문이다(항목 하나가 `test_writegate.py` 에서 테스트 4개를 만든다:
12021 → 12029 → 12030).

## 이 회차가 재지 않은 것

- **실기 검증 0건.** 콘솔은 오프라인이고 포트 8000 에 접촉하지 않았다.
- **항목별 개별 비용.** 동시 투입만 쟀다. `06` 의 3건은 「Timecode 를 빼면 무엇이
  빨개지나」이고, 갱신된 테스트를 상대로 잰 값이라 「Store Group 단독 확대 비용」이
  아니다.
- **`SEAL_DEFENCE` 가 Phase 2 에서 얼마나 줄어드는가.** `05` 의 자리별 명령
  목록에서 5자리가 `Store Sequence` 를 실어 나른다는 것까지는 실측했지만, 그 5가
  실제로 redundant 로 바뀌는지는 Phase 2 룰셋으로 재야 한다.
