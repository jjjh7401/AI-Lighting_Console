# t554 판정 — 런북 UI 시안을 SPEC-LDBEAT-001 에 그대로 반영 (plan 전용)

- 브랜치 `WT-ldbeat-ui-design`, 기준 origin/main `bee51823` (`git rev-list --count --left-right origin/main...HEAD` → 착수 시 `0 0`)
- 커밋: `f22727f7`(시안 정본 복사) · `7cae7040`(시안 반영, Tier L) · `0684b447`(감사 1차 대응) · `6b636036`(감사 2차 대응) — 전부 `(카드 t554)`
- 코드 변경 0줄: `git diff --stat bee51823 HEAD -- . ':!.moai'` → 출력 없음. 콘솔 접촉 0건.
- 날짜: 2026-10-11

## ① 시안 정본 — 바이트 동일 복사

`.moai/specs/SPEC-LDBEAT-001/design/` 에 네 파일을 `cp -p` 로 복사했다. sha256 은 `sha256.txt` 에 원본과 사본을 함께 적었고, 마지막 커밋 뒤에도 같다(`shasum -a 256 -c .moai/reports/t554/sha256.txt` → OK 8건).

| 파일 | sha256 앞 16자(리드 지정값과 일치) |
|---|---|
| ldbeat-runbook-ui-proposal-20261008.html | f74c7066511a2c26 |
| ldbeat-runbook-ui-proposal-20261008.md | 39032b4d5e313a56 |
| ldbeat-runbook-mockup-20261008.html | dcd7a8062a458db1 |
| ldbeat-runbook-mockup-20261008.md | cb8ddb1e991afcfd |

## ② 시안 항목 → REQ/AC 대응표

전수 대응표는 `.moai/specs/SPEC-LDBEAT-001/design.md` §3 에 있다. 시안 23개 절이 모두 들어 있고 시안 원문을 줄 번호와 함께 인용한다. 입력 초안은 `coverage-draft.md` 다.

- 유효 17건, 대체됨·부분 대체 6건이다(#4·12·13·14·15·18). 대체된 행에는 그것을 이긴 뒤 결정의 원문 인용이 붙어 있다.
- 리드가 확정한 일반화 세 곳을 반영했다.
  - (a) ▸ 펼침과 칩 툴팁은 유지한다. 「오른쪽 칸은 … 열 때만, 평소엔 2칸」만 「편집 칸 위치」로 대체한다.
  - (b) 「곡에 연결된 로컬 음원을 열 때 자동 연결」로 일반화한다. 원문의 Mac 경로는 예시로만 인용한다.
  - (c) 「갈라지기 전 부모 그룹 줄로」로 일반화한다. 원문의 SIDE-ALL 은 예시다. 「여기서 갈라짐」 표시와 화면 오류에도 재생을 계속하는 것도 shall 절로 넣었다.

## ③ 바뀐 REQ / AC 목록 (기존 번호 변경 0)

기존 REQ-001~015·AC-001~016 본문은 바뀌지 않았다.
- `git diff bee51823 HEAD -- spec.md acceptance.md` 에서 기존 ID 가 든 삭제 줄은 1줄이다. acceptance.md §A.1 머리 문단으로, 옛 문장 전체를 그대로 두고 뒤에 덧붙였다(접두 일치 확인).
- spec.md 에서 바뀐 것은 frontmatter(`tier: M→L`, `version 0.3.3→0.4.0`, `module`)와 §0 Tier 근거뿐이다.

| 신설 REQ | 화면 영역 | 대응 AC |
|---|---|---|
| REQ-LDBEAT-016 | [HARD] 교차영역 — 시안 이탈은 감독 승인, 치수(310·440·320·1640/97%·1450px) 보존 | acceptance.md §D DoD → AC-021(b)·019(e)·022(c)·017(c)·017(a)(b) |
| REQ-LDBEAT-017 | 상단 바 | AC-LDBEAT-017 |
| REQ-LDBEAT-018 | 곡 전체 지도 | AC-LDBEAT-018 |
| REQ-LDBEAT-019 | 타임라인 줄·막대 | AC-LDBEAT-019 |
| REQ-LDBEAT-020 | 이음매·전환(시간 표기 포함) | AC-LDBEAT-020 |
| REQ-LDBEAT-021 | 편집 칸 | AC-LDBEAT-021 |
| REQ-LDBEAT-022 | 2D 무대 | AC-LDBEAT-022 |
| REQ-LDBEAT-023 | 이 마디 한눈에 | AC-LDBEAT-023 |
| REQ-LDBEAT-024 | 재생·음원 | AC-LDBEAT-024 |
| REQ-LDBEAT-025 | 명령창·AI·프리셋 서랍 | AC-LDBEAT-025 |

- Tier M→L: 감독이 시안을 그대로 지으라고 요구했다. 기존 SPEC 이 이미 REQ 15·AC 16 이라 Tier M 한도(각 16)로는 시안 항목을 담을 수 없었다. 리드가 안 A 로 결정했다.
- REQ/AC 는 25/25 로 Tier L 한도에 꽉 찼다. AC 는 화면 영역별로 묶고, 그 안에 시안 항목마다 확인 행을 두었다(리드 승인).
- ③ 어긋난 곳 바로잡기:
  - 시간 표기는 시안대로 초를 먼저, 박·마디를 괄호에 쓴다. 표시만 바꾸고 `fade_bars` 저장 단위는 그대로 둔다(REQ-020(e)).
  - 시안 안에서 결정이 바뀐 곳은 문서 순서상 뒤 결정이 이긴다고 명기했다.
- ④ HARD 절: 시안에서 벗어나려면 감독 승인이 필요하다(REQ-016).
- plan.md: M9 에 화면 구현 단계를 두었다(REQ-017~025, REQ-021 단계 포함). 기존 마일스톤 번호는 바꾸지 않았다.
- research.md: 현재 `BeatGrid.tsx`·`RunbookMode.tsx` 와 대조한 결과 54행이다. 구현 10, 부분 15, 미구현 29, 상충 0.

## ④ plan-audit 결과 (Tier L 통과선 0.85)

| 회차 | 대상 | 판정 | 점수 | 주요 지적 | 보고서 |
|---|---|---|---|---|---|
| 1 | 7cae7040 | FAIL | 0.75 | D1 GEARS 혼재(REQ-019(b)) · D2 440/1640px 검증 수단 없음 · D3 research §10 집계 오류 · D4 M9 에 REQ-021 단계 없음 · D5 줄 수 281→280 | `plan-audit.md` |
| 2 | 0684b447 | FAIL | 0.80 | D1~D5 해결. 같은 GEARS 혼재가 4곳 더(REQ-020(a)·021(b)·024(b)(c)) · AC-024 검증 행 누락 · 「spec.md §D」 오기 5곳 | `plan-audit-iter2.md` |
| 3(최종) | 6b636036 | **PASS** | **1.00** | blocking 0 · 선택 3건(D-OPT-1~3, 아래) | `plan-audit-iter3.md` |

- 감사마다 새 감사자를 썼다(앞 회차 판단에 끌리지 않게).
- 감사가 지적한 것 중 다음은 내가 직접 다시 쟀다.
  - D1: `grep -n "새 shall 절을 만들지 않는다"`
  - D3: §1~§9 행 재집계 54/10/15/29
  - D5: `wc -l` → 280
  - D-NEW-1: REQ-020 칸 인용
  - D-NEW-6: `grep -c "spec.md §D"`

### 남은 선택 사항 (blocking 아님, 손대지 않음)
- D-OPT-1: spec.md REQ-020(d) 둘째 문장의 주어에 `**The**` 굵게 표시가 빠졌다.
- D-OPT-2: REQ-021(b) 첫 While 절의 표현이 다소 동어반복이다.
- D-OPT-3: acceptance.md:45 AC-009(c) 검증 수단 칸의 「충분」. t554 이전부터 있던 문구다.

## 안 잰 것

- `shall_sweep.py`(내 검사)는 현재 판에서 0건이다. 하지만 대조로 0684b447 판에 돌려 보니 3건을 잡고 REQ-021(b) 1건을 놓쳤다. 그래서 「shall 없는 문장 0」의 근거는 3회차 감사자의 독립 재점검이고, 이 스크립트가 아니다.
- 시안 HTML 의 동작(눌러 보는 시안)을 브라우저로 다시 돌려 보지 않았다. 대응은 md 요약판과 HTML 의 절 제목을 대조한 것이다(두 파일 모두 17:51 판).
- research.md 의 file:line 인용은 2회차 감사자가 7건, 1회차 감사자가 7건을 확인했다. 나머지 행은 전수 확인하지 않았다.
- lane-3(t551)가 같은 SPEC 디렉터리의 progress.md 를 건드릴 수 있다. 이 브랜치는 progress.md 에 덧붙이기만 했지만, 머지 순서에 따라 충돌이 날 수 있다(아직 머지 시험 안 함).
- 브랜치는 아직 원격에 푸시하지 않았다. PR·CI 도 없다.
