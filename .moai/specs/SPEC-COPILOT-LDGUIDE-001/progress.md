# SPEC-COPILOT-LDGUIDE-001 — 진행 기록 (progress)

## 현재 상태

| 항목 | 값 |
|---|---|
| 단계 | **plan** |
| status | `draft` (v0.1.0) |
| 워크트리 | `.claude/worktrees/ldguide` |
| 브랜치 | `worktree-ldguide` |
| 기준 커밋 | `2092a42` (`main` 최신 — "Merge pull request #43") |
| 칸반 카드 | t1 (Class C), lead = `lead-tjueej` |
| plan-audit | **미실행** — 아래 §4 참조 |

## §1. plan 단계에서 한 일

1. **격리** — 공유 체크아웃이 다른 브랜치(`research/ma3-effects-phaser`)에 미커밋 수정
   다수를 안고 있어 손대지 않고, 워크트리 `ldguide`를 만들어 진입.
2. **능력 실측** — 앱의 도구 표면과 룰북을 코드에서 직접 확인.
3. **사용자 확인 3건** — AskUserQuestion 1라운드로 미확정 입력 해소.
4. **SPEC 3종 작성** — `spec.md` · `plan.md` · `acceptance.md`.

## §2. 증거 (명령 + 관측 출력)

측정 시각 2026-08-17, 위치 `.claude/worktrees/ldguide`, HEAD `2092a42`.

| # | 주장 | 명령 | 관측 출력 |
|---|---|---|---|
| E1 | 워크트리가 `main` 최신에서 깨끗하게 분기 | `git rev-parse --short HEAD` · `git status --short` | `2092a42` · (출력 없음 = clean) |
| E2 | 앱에 등록된 도구는 33종 | `grep -cE '^            name="[a-z_]+",$' server/orchestrator/tools.py` | `33` |
| E3 | 기존 가이드가 존재하며 감독 워크플로우 축으로 쓰여 있음 | `wc -c docs/user-guide.html` · `grep -oE '<h2[^>]*>[^<]+</h2>'` | `55212` · 12개 절(워크플로우 1~5 포함) |
| E4 | 기존 가이드 최종 변경 | `git log -1 --format='%ci' -- docs/user-guide.html` | `2026-08-13 14:41:24 +0900` (커밋 `2e20dda`) |
| E5 | 가이드가 도구 수를 22로 주장 | `grep -oE '22가지' docs/user-guide.html` | `22가지` 1건 (절 제목 "22가지 AI 도구 전체 목록") |
| E6 | 도구 식별자 17종만 가이드에 등장 | 33종 이름 alternation grep → `sort -u` | 17줄 (부재 16종은 spec.md §A.2에 열거) |
| E7 | 16건 부재가 곧 능력 누락은 **아님** (반례 관측) | `grep -c -iE 'vectorworks\|도면\|MVR'` 외 3건 | `8` / `배치·위상 15` / `매직 2` / `익스큐터 6` |
| E8 | 가이드는 외부 의존 0 (자체완결) | `grep -coE 'https?://...'` · `grep -cE '<script\|<link'` | `0` · `0` |
| E9 | 목차 앵커 12개 | `grep -oE 'href="#s[0-9]+"' \| wc -l` | `12` |
| E10 | 룰북 7종 존재 | `wc -l server/rulebook/assets/v2.4.2/*.md` | 7파일 799줄 |
| E11 | `.moai/project/product.md` 존재 (skill Step 2.5 충족) | `ls .moai/project/` | `product.md` 포함 |

### §2.1 미검증 — 명시

다음은 **확인하지 않았다.** run 단계 M0의 과제다:

- 식별자 부재 16종 각각이 산문으로 덮였는지(`covered-in-prose` / `stale` / `absent`).
  E6·E7은 서로 반대 방향을 가리키며, 개수 차이만으로는 판정할 수 없다.
- 단계 3(포커싱)·단계 7(리허설·수정)에 대응 기능이 실제로 있는지.
  `server/spatial/pointing.py` 파일 존재는 확인했으나 **도구로 노출됐는지는 미확인**.
- 안전 경고 4건의 근거 원문 재확인. 현재는 도구 설명문과 기존 기록에 의존한 상태이며,
  설명문은 동작 증명이 아니다.
- 기존 가이드의 나머지 수치 주장(`12 이펙트` · `4종` 등)의 진위.

## §3. 사용자 확인 기록 (2026-08-17, AskUserQuestion 1라운드)

| 질문 | 사용자 선택 |
|---|---|
| 가이드의 단계 축 | **시간순 현장 흐름 9단계** — 도면 수령 / 패치 / 셋업·포커싱 / 그룹·프리셋 / 룩·이펙트 / 큐리스트 / 리허설·수정 / 본공연 운용 / 철수·인계 |
| 기존 `docs/user-guide.html` 처리 | **같은 파일 전면 개정** (신규 분리 아님, 폐기 후 재작성 아님) |
| 독자 | **감독 본인 + 같이 일하는 오퍼레이터·크루** (2계층) |

이 3건이 spec.md의 REQ-LDG-001 · 003 · 010의 근거다.

## §4. 카드 전제 정정 — lead에게 보고할 사항

카드 t1은 *"…감독의 언어로 설명한 문서가 없습니다"* 를 배경으로 적었다. **이 전제는
사실과 다르다.** `docs/user-guide.html`이 이미 존재하고(E3·E4), 이미 워크플로우 축으로
쓰여 있으며, "추가 기능 제안 로드맵" 절까지 갖고 있다.

따라서 카드의 실제 작업은 **신규 집필이 아니라 개정**이며, 진짜 결함은 "문서 부재"가
아니라 **"문서가 앱보다 뒤처짐"**(E2 vs E5: 33 vs 22)과 **"구성 축이 감독의 시간축과
어긋남"**이다. SPEC은 이 정정된 전제 위에 세웠다.

## §5. 산출물

```
.moai/specs/SPEC-COPILOT-LDGUIDE-001/
  spec.md        — 결함 3건(A.1~A.3) · REQ-LDG-001~015 · Out of Scope · 열린 질문 4건
  plan.md        — M0~M5 · M0 게이트 A~D(분기 서술 포함) · PRESERVE · Mode 5 권고
  acceptance.md  — AC-LDG-001~017 (REQ 1:1) · 엣지 6건 · 품질 게이트
  progress.md    — 이 파일
```

아직 만들지 않은 것(run 단계 산출물): `evidence.md` · `backlog-candidates.md`.

## §6. 다음 단계

1. **plan-audit** — 미실행. 독립 감사(plan-auditor)를 돌릴지 사용자 확인 대기 중.
   이 세션은 "사용자가 요청하지 않은 에이전트 호출 금지" 제약 아래 있어, 감사 에이전트를
   임의로 띄우지 않았다.
2. 감사 통과 후 lead에게 완료 통보 → run 열로 이관.

## 이력

| 일자 | 내용 |
|---|---|
| 2026-08-17 | plan 단계 착수. 워크트리 격리 · 능력 실측 11건 · 사용자 확인 3건 · SPEC 3종 작성. plan-audit 미실행. |
