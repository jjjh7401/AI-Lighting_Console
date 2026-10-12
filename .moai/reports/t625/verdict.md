# t625 판정 — 배차 전제 불일치, 보류

- 카드: t625 · SPEC-COPILOT-SONGSTD-001 을 superseded 로 닫기
- 워크트리: `.claude/worktrees/t625` · 브랜치 `WT-songstd-superseded` · HEAD `ba984a6b` (= origin/main, 0 0)
- 상태: 파일 변경 없음. 커밋·푸시·PR 없음. 이 파일만 untracked.
- 판정: 배차 전제가 저장소 실측과 맞지 않아 보류. 리드·감독 결정 필요.

## 1. 전제 대 실측

| 전제 | 실측 | 판정 |
|---|---|---|
| `song-structure-lighting-standard.md` 가 SONGSTD-001 을 대체했다 | 이 파일은 SONGSTD·옛 파일명을 한 번도 언급하지 않는다. `git grep -c -E "SONGSTD\|song-lighting-design-standard" -- docs/proposals/song-structure-lighting-standard.md` 출력 없음 (0건). 헤더: 「곡 구조 기반 조명 연출 기준 (v1)」, 작성 2026-09-11 | 근거 없음 |
| 옛 파일명 `song-lighting-design-standard.md` 는 옛 이름이다 | 살아 있는 별개 정본. 헤더: 「곡 단위 조명연출 표준 초안 (Song Lighting Design Standard, v0.5)」, 「SPEC-COPILOT-SONGSTD-001의 1단계 산출물」. 코드 독스트링이 §2c·§3 을 인용 (`server/design/rig.py:179`, `server/design/energy.py:2`) | 틀림 |
| 옛 파일명 참조는 「활성 문서 5개」 | 28 파일 (§2). 활성 17, 기록 11 | 틀림 |
| SONGSTD-001 은 구현 PR·progress 가 없다 (감사표) | `8ecefecc feat(songstd): implement M1 music, rig, energy and lint engine` 가 origin/main 에 있다. `SONGSTD-001` 마커가 `server/design/` 7개 파일에 있다 | 틀림 |
| spec.md 의 「상태」·HISTORY 를 정정한다 | spec.md 에 상태 필드도 HISTORY 절도 없다 (1~4행: 브랜치·근거 문서·선행) | 구조 신설이 필요 |
| 「superseded」로 닫는다 | 스키마상 `* → superseded` 는 새 SPEC 을 쓰는 manager-spec 이 `feat(SPEC-{NEW-ID}): supersedes SPEC-{OLD-ID}` 로만 전환한다 (`.claude/rules/moai/development/spec-frontmatter-schema.md` § Status Transition Ownership Matrix). 문서는 SPEC 이 아니다 | 전환 경로 없음 |

## 2. 옛 파일명 참조 전수 분류

명령: `git -C <wt> grep -l "song-lighting-design-standard" -- .` → 28 파일.

| 분류 | 파일 | 처리 |
|---|---|---|
| 날짜 기록 (11) | `.moai/reports/` 7 (t142·t484·t500·t501 의 M2·M3·M6·sync), `docs/handoff/` 2, `reports/app-fresh-eyes-review-20260903.md` 1, `CHANGELOG.md` 1 | 고치지 않는다. 만료 고지만 |
| 여전히 옳음 (15) | `.moai/specs/SPEC-LDRENDER-001/` 7 (spec·plan·acceptance·research·progress·audit-plan-002·audit-plan-003 — REQ-002 가 이 정본 §2c 를 편집하도록 되어 있음), `.moai/specs/SPEC-COPILOT-SONGSTD-001/research.md` 1, `server/design/` 6, `server/tests/test_capability_verdict.py` 1 | 바꾸면 틀린 인용이 된다. 손대지 않는다 |
| 버전 표기만 낡음 (2) | `.moai/specs/SPEC-COPILOT-SONGSTD-001/spec.md:4` 「표준 v0.2」, `docs/capability-index.md:122` 「(v0.4)」. 정본은 v0.5 | 이것만 좁게 정정 가능 (감독 확인 후) |
| 경로가 틀림 (0) | — | — |

## 3. 재측정한 t623·t624 전제 (독립 카드)

- t623 WRITEGATE-001: `spec.md:5` `status: in-progress`. `progress.md:5·13` 「M2(라이브) 미실행 · `SKIP: CONDITION_NOT_MET`」. 전제 일치.
- t624 CUETIME-001: `spec.md:7` 「- 상태: T1 진행 중」 낡은 헤더 존재, 일치. 다만 frontmatter 블록은 `status` 가 빈 값이 아니라 블록 자체가 없다 (`^---` 0건).

## 4. 결정이 필요한 것 (감독)

1. 원안 집행: 하지 않는다. 활성 참조 17곳 중 코드 독스트링 6곳과 LDRENDER REQ-002 가 정본을 잘못 가리키게 된다.
2. 좁은 정정: 버전 표기 2곳 (v0.2·v0.4 → v0.5). 실측 근거가 있다. 종결이 아니다.
3. SONGSTD-001 종결 방식: superseded 면 superseding SPEC 이 필요하다 (manager-spec 소유). completed 면 sync 전에 구현 범위 (M1~M4 중 어디까지인지) 를 먼저 재야 한다. 이번 판정에서는 재지 않았다.
4. 정본 이전: 감독 의도가 정본을 structure 문서로 옮기는 것이라면, 코드 독스트링·LDRENDER REQ-002·capability-index 가 함께 바뀌는 SPEC 작업이다. 카드 한 장으로 할 일이 아니다.

## 5. 안 잰 것 (Gaps)

- v0.5 정본에 §2c·§3·§4b 절 번호가 아직 있는지 재측정하지 않았다. 인용은 「여전히 옳음」으로 잠정 분류했다.
- SONGSTD-001 구현이 M1~M4 중 어디까지인지 재측정하지 않았다. M1 커밋만 확인했다.
- 감독 결정 (2026-10-12) 의 원 근거 대화는 확인할 수 없다. 감사표의 「판단 불가」 문구와 결정문만 있다.

## 6. 잔여 위험

- 감사표의 SONGSTD 행이 틀렸다. 같은 감사의 다른 행 전제도 착수 전 재측정이 필요하다. t623·t624 는 재측정 결과 일치했다.

## 7. 결정 결과 (2026-10-13)

- 감독 결정 (리드 전달): SONGSTD-001 「대체됨으로 닫기」를 철회한다. SONGSTD 상태는 건드리지 않는다.
- 이 PR 이 한 일: 옛 정본 표기를 v0.5 로 맞췄다. 리드 지시는 2곳(v0.2·v0.4)이었고, grep 으로 확인하니 3곳이었다. 같은 SPEC 안에서 4행은 v0.5 인데 13행이 v0.2 로 남으면 어긋나므로 13행도 함께 고쳤다.
  - `.moai/specs/SPEC-COPILOT-SONGSTD-001/spec.md` 4행: `(표준 v0.2)` → `(표준 v0.5)`
  - `.moai/specs/SPEC-COPILOT-SONGSTD-001/spec.md` 13행: `표준 v0.2가 그 기준이고` → `표준 v0.5가 그 기준이고`
  - `docs/capability-index.md` 122행: `(v0.4)` → `(v0.5)`
- 정본 헤더 확인: `docs/proposals/song-lighting-design-standard.md:1` 은 `v0.5` 다 (기준 `origin/main` `0ab9c756`).
- 남은 긴장: `.moai/docs/lane-protocol.md` §5 는 「날짜·베이스·버전이 박힌 측정 기록은 숫자를 고치지 말고 만료 고지를 붙여라」라고 한다. 근거 행(4행·13행)은 연구 시점의 기록이라 이 규칙에 걸린다. 감독이 숫자 교체를 택했으므로 따랐다. 만료 고지 방식이 필요하면 후속 한 커밋으로 처리할 수 있다.
- §1~§6 의 분석과 판정은 그대로 둔다. 「superseded 종결」과 「옛 파일명 5곳 정정」은 이 PR 에서 하지 않는다.
