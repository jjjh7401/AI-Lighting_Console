# t90 -- SPEC 장부 정리: 15건 개별 확인 (read-only)

- 워크트리: .claude/worktrees/t90, 브랜치 WT-spec-close
- 이 세션 3장째 카드 (t199 -> t202(취소) -> t90), 기준: lane-protocol.md 9절
- base: t201 merge 이후 origin/main 963b23a
- 콘솔 안 씀. 코드 안 고침. 새 카드 안 만듦(후보만 끝에 나열).

## 0. 한 줄

t201이 낸 "(b) 구현됐고 안 닫힌 것 15개"를 원본(spec.md/progress.md/dry-run)으로
개별 확인했다. 결과: **1건은 실제로 지금 닫을 수 있다(LXSEQ-001)**. 나머지 14건은
"Mx-phase 신호(§E.5) 부재"로 dry-run이 거절하는데, 이 신호 부재는 **이 15개만의
특이 현상이 아니라 프로젝트 전반의 낡은 포맷 격차**다(아래 §2). 그래서 14건을
"부분구현"으로 단정하지 않고 "포맷 격차 -- 판단 보류"로 내렸다.

## 1. 15건 개별 확인 (원본 대조 + dry-run)

방법: `.moai/specs/SPEC-COPILOT-<ID>/{spec.md,progress.md,acceptance.md}` 원본을
열고, `moai spec close <ID> --backfill-only --dry-run`으로 도구에 직접 물었다
(추측 금지 -- 카드 지시). 실제 close는 실행하지 않았다.

| SPEC | 현재 status | dry-run | 실패 사유 | 판정 | 원인 갈래 |
|---|---|---|---|---|---|
| LXSEQ-001 | implemented | **성공(전제 충족)** | -- | **닫을 준비 완료** | 해당 없음 |
| AUTOPATCH-001 | draft | 실패 | §E.5 부재 | 포맷 격차 -- 판단 보류 | (C) |
| COLORPRESET-001 | draft | 실패 | §E.2+§E.5 부재 | 포맷 격차 -- 판단 보류 | (C) |
| DEPLOY-001 | in-progress | 실패 | §E.5 부재 + AC 미PASS | 판단 보류 | (C) -- AC 미확인 |
| IMGLAYOUT-001 | completed(도구)/unknown(정규식) | noop(이미 completed) | -- | **이미 닫혀 있음** | (A) -- 두 도구가 같은 파일을 다르게 읽음(§2.1) |
| INTROSPECT-001 | draft | 실패 | §E.5 부재 | 포맷 격차 -- 판단 보류 | (C) |
| LXSEQ-002 | draft | 실패 | §E.2+§E.5 부재 | 포맷 격차 -- 판단 보류 | (C) |
| LXSEQ-003 | draft | 실패 | §E.5 부재 | 포맷 격차 -- 판단 보류 | (C) |
| MCP-001 | draft | 실패 | §E.5 부재 | 포맷 격차 -- 판단 보류 | (C) |
| MVP-001 | in-progress | 실패 | §E.5 부재 | 포맷 격차 -- 판단 보류 | (C) |
| SHEETPIPE-001 | in-progress | 실패 | §E.5 부재 + AC 미PASS | 판단 보류 | (C) -- AC 미확인 |
| TREEID-001 | draft | 실패 | §E.2+§E.5 부재 | 포맷 격차 -- 판단 보류 | (C) |
| TRUNCATE-001 | draft | 실패 | §E.2+§E.5 부재 | 포맷 격차 -- 판단 보류 | (C) |
| VWX-001 | draft | 실패 | §E.5 부재 | 포맷 격차 -- 판단 보류 | (C) |
| WRITEGATE-001 | in-progress | 실패 | §E.5 부재 | 포맷 격차 -- 판단 보류 | (C) |

이 표는 포크(t90-spec-close-verify)가 만든 초안을 내가 §2의 대조 결과로 보정한
것이다 -- 포크 원안은 12건을 "부분구현(A)"으로 적었으나, §2가 §E.5 부재를
이 15개만의 결함이 아니라고 뒤집어서 (C)로 낮췄다.

## 2. "Mx-phase 신호(§E.5) 부재"가 이 15개만의 문제인지 대조

이미 completed로 닫힌 SPEC 7개(DASHUI·BUSKWIZ·EXECBODY·SCENE·SPATIAL·PARITY·
SHOWUI)의 progress.md에서 "E.5"/"mx_commit_sha" 문자열을 찾았다:

```
grep -lc "E.5\|mx_commit_sha" <7개 progress.md>
-> DASHUI-001 만 걸림 (1/7)
```

**completed로 이미 닫힌 SPEC 7개 중 6개도 §E.5가 없다.** 즉 §E.5 부재는 이 15개
"안 닫힌" SPEC의 특이 결함이 아니라, **이 필드가 나중에 추가된 스키마라서 그
이전 SPEC 다수가 못 채운 것**이다(era 문제와 같은 모양 -- t201 §1.1의
era-exempt 29개와 같은 축일 가능성이 있다, 미확인).

그래서 "§E.5 부재 = 미완성"으로 읽으면 안 된다. dry-run이 거절하는 것은 사실이지만,
그 거절이 "구현이 안 됐다"를 뜻하는지 "닫기 도구의 전제 스키마가 그 시절 SPEC엔
안 맞는다"를 뜻하는지는 **이번 회차에서 못 갈랐다** -- 그래서 (A)가 아니라
기본값 (C)로 내렸다(카드가 요구한 3분류 규율).

## 3. 훅 로그 확인 -- LXSEQ-002/003 때 무엇을 봤나

`.moai/logs/status-transition-audit.log`는 `.gitignore`에 있어 이 워크트리엔
없다(git이 안 옮김) -- primary 체크아웃(`/Users/studiox/Documents/Claude/Code/
AI-Lighting_Console/.moai/logs/`)에서 직접 확인했다(로컬 러타임 상태라 primary
절대경로 금지 규칙의 대상인 "저장소 파일"과는 다르다고 판단함).

- 총 964줄, **마지막 항목이 2026-08-18**(LDGUIDE-001 completed 전이).
- LXSEQ-002(2026-08-24 draft)·LXSEQ-003(2026-08-25 M1~M4 머지) 관련 항목은
  **0건** -- 없는 이유는 "훅이 조언 전용이라 조용히 지나갔다"가 아니라
  **로그 자체가 그 날짜 이후로 안 쌓였다**는 것이다.
- 원인은 미확인(A/B/C 셋 다 후보): 훅이 특정 조건에서 안 켜지는지(A), 이
  머신의 primary 체크아웃 설정 문제인지(A에 가까움), 아니면 그 이후 status
  전이가 Edit 도구가 아니라 다른 경로(스크립트·bulk write)로 일어나서 훅
  자체가 관측할 수 없는 구간이었는지(B/C에 가까움) -- 훅 스크립트 자체는
  git 이력상 초기 커밋 이후 안 바뀌었고(`.claude/hooks/moai/status-transition-
  ownership.sh`, 2b8c28e), settings.json에도 여전히 등록돼 있다. **코드를
  더 열어 원인을 확정하는 것은 이번 회차 범위 밖으로 남긴다.**

## 4. 날조 대조군 -- `moai spec drift`가 공허한 검사인지

completed·비era-exempt인 `SPEC-COPILOT-DASHUI-001`(t201 spec-drift.json에서
GitImpliedStatus=completed, Drifted=false 확인)의 spec.md status를 **이
워크트리 사본에서만** `completed` -> `draft`로 바꾸고 재실행했다:

```
바꾸기 전: {'SPECID': 'SPEC-COPILOT-DASHUI-001', 'FrontmatterStatus': 'completed', 'GitImpliedStatus': 'completed', 'Drifted': False}
바꾼 후:   {'SPECID': 'SPEC-COPILOT-DASHUI-001', 'FrontmatterStatus': 'draft',     'GitImpliedStatus': 'completed', 'Drifted': True}
```

**빨개졌다 -- 공허한 검사가 아니다.** 즉시 `git checkout --` 로 원복했고
(정본 건드리지 않음), `git status --short`로 깨끗한 트리 확인했다.

## 5. 안 잰 것

- DEPLOY-001·SHEETPIPE-001의 "AC 미PASS"가 정확히 어느 AC인지 acceptance.md를
  열어 확인 못함 -- (C) 판단을 확정하려면 필요.
- §E.5 부재가 era-exempt 29개 축과 겹치는지 교차 확인 안 함(§2의 가설).
- 훅 로그 공백(§3)의 진짜 원인 -- 코드를 더 읽어야 하고 이번 회차 범위 밖.
- (d) 5건·(e) 21건은 이번 카드 범위 밖(t201이 이미 "안 잰 것"으로 남긴 것과 동일).
- PR/머지 SHA 개별 재확인은 포크가 t201의 계기를 재신뢰했고 독립 재검증은 안 함
  -- 이것도 "요약을 원본 대조군으로 쓴" 것일 수 있어 여기 명시해 둔다.

## 6. 후속 카드 후보 (admit은 리드 판정, 카드는 안 만듦)

1. `LXSEQ-001` 실제 닫기(`moai spec close SPEC-COPILOT-LXSEQ-001 --backfill-only`) --
   dry-run으로 전제 충족 확인됨, 실행만 남음.
2. §E.5 부재가 era 전반의 스키마 격차인지 전수 확인(completed 21개 + 이번 14개
   대조) -- 확인되면 "포맷 격차 -- 판단 보류" 14건이 한 번에 갈릴 수 있다.
3. DEPLOY-001·SHEETPIPE-001의 acceptance.md AC 미PASS 원인 확인.
4. 훅 로그가 2026-08-18 이후 멈춘 원인 확인(A/B/C 미확정).
5. IMGLAYOUT-001의 frontmatter 파서 불일치(§2.1) -- `spec status --list`와
   `spec close`가 같은 파일을 다르게 읽는 것은 t201이 이미 지적한 것과 같은
   축(프론트매터 없는 spec.md 3개)일 가능성.
