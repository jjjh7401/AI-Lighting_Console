# t605 run 판정 — t593 「반영당 효과 1개」 우회 걷기

판정: **PASS** (콘솔 쓰기 0)
브랜치 `WT-fx-per-apply-limit` · 기준 origin/main `faeef1db` · 구현 커밋 `a082e617`

## 왜 걷을 수 있나
- t601(#641) 이후 `run_commands` 는 **앞선 호출**에서 실행된 줄만 건너뛴다(`server/orchestrator/tools.py` 실행 고리).
- 반영(`beat_grid_apply`)은 반영 한 번에 `_dispatch_declared` 를 **한 번** 부른다. `_dispatch_declared` 는 부를 때마다 새 `ExecutionContext(risk=…, approval_owned_by_caller=True)` 를 만든다(`server/web/session.py` 약 11983행, 내가 직접 읽어 확인). 그래서 `executed_ok` 가 비어 있고, 반영 묶음 안의 반복 줄은 전부 나간다. 구현 에이전트가 메서드 본문 전체를 읽어 「한 반영 = 한 디스패치」라고 보고했고, 나는 컨텍스트를 새로 만드는 줄을 다시 확인했다.

## 걷은 것
1. `beat_grid_effect_presets.effect_preset_outcomes` 의 겹침 검사와 `EFFECT_BATCH_COLLISION` 상수. 이제 번호마다 따로 판정한다. `EFFECT_CREATE_ON_APPLY` 문구에서 「반영당 하나」를 뺐다(BPM 조건은 그대로).
2. `session.py` 의 「효과 만들기 줄이 큐 줄과 겹치면 반영 중단」 가드. **재판정 결과 제거**: 위 이유로 한 반영 안에서는 겹친 줄도 빠지지 않는다. 좁혀서 남길 경우가 없다.
3. 주석 정리: `beat_grid.py`, `beat_grid_color_presets.py` 의 상호 참조.
4. 시험(`test_effect_preset_create_t593.py`): 「하나만」을 잠그던 3건을 새 동작을 잠그는 시험으로 바꿨다. 재현 시험 2건(효과 둘을 한 반영에 → 두 `Store Preset 22.n` 과 `ChangeDestination Root`·`Step 2` 를 포함한 모든 줄이 콘솔에 도착 / 큐 줄과 겹쳐도 반영이 멈추지 않고 모든 줄 도착). 구현 에이전트 보고로는 고치기 전 코드에서 RED였다(사유: `EFFECT_BATCH_COLLISION` 보류, `status["ok"] is False`).

## 증거 (이 트리 `a082e617`, origin/main 대비 0 뒤)
- `uv run pytest -q -p no:cacheprovider -o addopts=""` 대상: t593 · t601 · t595 · t603 · t594 · t598 · t600 · t592 · t607 · t589 → `263 passed in 2.44s`
- `ruff check`(5 파일) → `All checks passed!` · `ruff format --check` → `5 files already formatted`
- 뮤테이션: `effect_preset_outcomes` 가 첫 번호만 만들고 나머지를 보류하게 되돌리면(옛 「반영당 하나」) → `3 failed, 37 passed`. 되돌린 뒤 `git status` 깨끗함.
- 공용 stash 에 남은 항목 없음(`git stash list` 빈 결과). 구현 에이전트가 RED 확인에 stash 를 썼다고 보고해서 확인했다.

## 안 건드린 것
- 쓰는 쪽 겹침 가드(`fx/instantiate.py _guard_collision`·`collided_lines`, `groupgen`, `looks/busking.py`, `scene/compile.py`)와 보호 구역 `server/orchestrator/tools.py`. t601 판정서가 「해롭지 않아 그대로 둔다 — 걷을지 리드 판단」으로 남긴 것들이다.

## 안 잰 것
- 실기 0회. 효과 둘을 한 반영 묶음에 섞는 꼴의 콘솔 동작은 실기 카드(t602 ⑨ / 그 후속)의 항목이다.
- 모델 대화 한 차례 안에서 효과 도구를 두 번 부르는 호출 간 겹침은 그대로 건너뛴다(REQ-MVP-033). 이 카드 범위 밖이다.
