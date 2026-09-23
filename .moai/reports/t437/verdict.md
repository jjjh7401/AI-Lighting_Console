# t437 판정 — SPEC-LDDESIGN-001 M4 3층 밀도·회차 규칙·헤드룸 (REQ-036~052)

- 레인: lane-1 · 워크트리 `.claude/worktrees/t437` · 브랜치 `WT-concept-density`
- 기준: `origin/main@a54db70e`(M3 PR #483 포함) 위 커밋 4개
- 판정: **PASS(범위 한정)** — 단 🔴 G4 정의 1건은 SPEC 판단이 필요해서 잔여 위험으로 넘긴다

## 산출물

| 파일 | 내용 |
|---|---|
| `server/concept/density.py` | 3층 컴파일러(구간·프레이즈·원샷 레인 분리), 빌드업·눈 리셋 삽입, 4회차 이후 프레이즈 상한, Bridge remove, G13 |
| `server/concept/escalation.py` | 모션 분배, 6축 회차 비교(색 제외), G2·G3·G4, 6회 이상 정상 판정 |
| `server/concept/headroom.py` | 구간 큐별 4축 헤드룸, G5 경고 4조건(경고만 내고 막지 않음) |
| 시험 3파일 | 신규 91건(density 42 · escalation 29 · headroom 20) |

기존 파일과 `__init__.py`는 건드리지 않았다. 색은 호출부 콜백 `color_for`로만 받는다.

## 레인이 직접 잰 것

1. 에이전트가 보고한 커밋 SHA 3개를 되읽었다. 기준은 `06e3d125`의 후손이고, 변경은 새 파일 6개와 progress.md뿐이다. 이 3개를 main 위로 cherry-pick했고 충돌은 0이다.
2. `uv run pytest server/tests/test_concept_*.py -q` → `270 passed`(`pytest_concept.txt`). 신규 시험은 `--collect-only` 기준 91건이다.
3. ruff check 통과, ruff format 14 files already formatted.
4. 변이 시험 3종. 각각 쏜 뒤 원래대로 되돌렸다.

| 심은 결함 | 결과 |
|---|---|
| Chorus 1 경고 조건 OR → AND (REQ-051) | 2 failed |
| Bridge를 직전 브릿지 아닌 구간 대신 바로 앞 큐와 비교 (REQ-047) | 2 failed |
| 4회차 이후 프레이즈 큐 상한 제거 (REQ-045) | 4 failed |

## 🔴 잔여 위험 — G4 「직전 구간」 정의

- **SPEC 원문(REQ-048):** 「직전 구간에 남은 모션 단계가 1 이상」이다.
- **구현:** 원형 `final_integrated.py`의 `table[index(final)-1]`을 그대로 옮겨, Final Chorus 바로 앞 **큐 행**을 본다.
- **문제:** 그 행이 절(Verse)이나 빌드업이면 `restore(Verse 1)`가 모션을 0으로 되돌린다. 그러면 「남은 모션」이 부풀어 검사가 통과한다. 실측 예는 Rain의 남은 모션 3이다.
- **결과:** 회차 4에서 이미 최대 모션을 쓴 곡도 G4를 통과할 수 있다. REQ-044가 막으려던 경우가 바로 이것이다.
- **판단 요청:** 비교 대상을 「직전 후렴 회차」로 바꿀지는 SPEC 판단이다. M6 8곡 게이트 고정 전에 정해야 한다.

## 레인 사이 조율

- 빌드업·눈 리셋·후렴 뒷마디 프레이즈 큐는 `tracking: cue_only`로 뒀다. 원형은 빌드업이 Track이었다.
- 에이전트는 REQ-056 문면을 근거로 들었다. 트래킹 확정은 M5(t438) 소관이라 서로 맞춰야 한다.

## 안 잰 것

- `session.py`/`tools.py` 배선은 M6 몫이다.
- 전체 시험은 CI에 맡겼다.
- 실기 콘솔은 0회다.
- 4/4 박자를 가정했다.
- 그룹 목록은 원형의 11그룹이고 실제 리그가 아니다.
- 원샷 레인은 콘솔 방출이 없다.
