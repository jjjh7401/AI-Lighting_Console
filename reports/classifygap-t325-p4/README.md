# t325 — 분류 층이 `Assign Sequence`·`Copy Sequence` 를 보게 한다 (blacklist v7→v8)

SPEC-COPILOT-CLASSIFYGAP-001 의 Phase 4. Phase 1~3(v4→v7, PR #369·#370·#371)이
여섯 `Store` 오브젝트를 닫은 뒤에도 `SEAL_DEFENCE` 의 seal-only 두 자리가 남아
있었다. 그 둘이 실어 나르는 것이 `Assign Sequence <n> At Executor <m>` 와
`Copy Sequence <src> At <dst>` 뿐이고 동사가 `Store` 가 아니라서 앞선 세 리비전
어디에도 안 닿았다. 이 회차가 그 두 오브젝트를 닫는다.

## 무엇을 쟀나

| 항목 | 명령 | 관측 |
|---|---|---|
| 기준선 | `uv run python -m pytest server/tests -q` @ f28fbdf | `00_baseline_f28fbdf.txt` |
| 확대 후 전체 | 같은 명령, 이 트리 | **12032 passed · 35 skipped · 0 failed** (2026-09-07) |
| 뮤테이션 | 두 항목만 되돌리고 전체 | **9 failed · 12015 passed · 35 skipped** — `07_mutation_both.txt` |
| 봉합 층 대조 | `09_seal_layer_vs_classify.txt` | 봉합은 「쓰기다」, 분류는 `None` 이었다 |
| 봉합 분류 전/후 | `03_…_before.txt` / `10_…_after.txt` | 두 자리 `seal-only` → `redundant` |

뮤테이션에서 죽는 9건에 `test_writegate_session_sites.py` 의 두 자리
(`_offer_fx_executor_assignment` · `_setlist_mode`)가 **직접** 들어 있다 —
파생 추정이 아니라 그 자리 자체가 관측한다.

총계가 12067 → 12059 로 8 줄어든 것은 「항목 하나 = 테스트 4개」의 정확한 두 배다
(`blacklist.yaml` REVISION HISTORY 의 분모 경고).

## 확대의 근거

이 저장소는 이미 두 줄을 쇼파일 쓰기로 비준하고 있었다 —
`server/orchestrator/write_reason.py` 의 `_ASSIGN_EXECUTOR`(:54)·
`_COPY_SEQUENCE`(:55)가 같은 줄을 읽어 감독에게 사유로 설명한다(:122·:126).
봉합 층과 분류 층의 답이 갈려 있었고, 이 리비전이 그 마지막 쌍을 없앤다.
(경로 실측 2026-09-07 — 이 저장소에 `server/safety/write_reason.py` 는 **없다**.)

## 안 잰 것

- **실기 검증 0건.** 콘솔 오프라인, 포트 8000 미접촉.
- **UI 렌더 미측정.** 서버 `approval_request` 이벤트 수로만 셌다.
- **`Store Page`·`Store Macro` 확대 비용.** SPEC §F 범위 밖 그대로.
- **중복 레인.** 같은 카드를 `WT-classify-widen-p4` 도 동시에 작업했고 그 트리는
  뮤테이션(`Assign Sequence` 제거)이 걸린 채 방치돼 있다. 이 PR 은 p4b 계열이고
  p4 트리는 손대지 않았다 — 처분은 감독 몫.
