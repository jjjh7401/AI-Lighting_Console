# t524 판정서 — SPEC 상태 장부 정리(범위 축소판)

- 카드: t524 · 브랜치 `WT-spec-status` · 기준 `origin/main` `606e516e` · 2026-10-07
- 성격: 문서만. 코드 0 · 콘솔 0
- **범위 축소(리드 정정, 감독 「모든 걸 반영하지 말고 필요한 것만」)**: ⑤LDPLUGIN · ⑥LDRENDER 두 개만 반영. ①②③④⑦ 은 이미 작업 트리에서 고쳤던 것을 `git restore` 로 전부 되돌렸다 — 이 PR 의 diff 는 두 파일뿐이다.

## 1. 반영한 것

| SPEC | 전 | 후 | 근거(이번에 다시 잰 것) |
|---|---|---|---|
| SPEC-LDRENDER-001 | implemented | **completed** | 감독 결정 2026-10-07(리드 경유 — 레인이 직접 들은 것은 아니다). SPEC-LDRHYTHM-001 spec.md 가 `AC-LDRENDER-016` 을 3곳 인용하고 REQ-LDRHYTHM-011 이 그것을 이어받는다. HISTORY 표에 한 줄 추가 |
| SPEC-LDPLUGIN-001 | in-progress | **superseded** | `sed -n 24p SPEC-LDRECV-001/spec.md` → 「`SPEC-LDPLUGIN-001` 을 쪼갠 여섯 자식 중 세 번째」 · `sed -n 25p SPEC-LDSTORE-001/spec.md` → 「쪼갠 여섯 자식 중 의존 뿌리」. HISTORY 절이 없어 새로 만들고 한 줄 |

두 파일 모두 `updated: 2026-10-07`. 본문은 HISTORY 한 줄 말고 손대지 않았다.

## 2. LDPLUGIN 의 한계 — 여섯 자식을 다 이름 댈 수 없다

- `grep -l "LDPLUGIN-001" .moai/specs/*/spec.md` → 자신 말고 LDEMBED·LDCOMPILE·LDRECV·LDSTORE·LDWIRE 다섯.
- LDWIRE spec.md:25 는 스스로 「원래 여섯 자식에 속하지 않는다」고 적었다. LDSEND 는 형제로 불리지만 LDPLUGIN 을 분할 부모로 인용하지 않는다.
- 분할 목록 원본 `reports/ldplugin-001/split-proposal.md` 은 저장소·git 역사 어디에도 없다(`git log --all -- '**/split-proposal.md'` → 빈 출력).
- 그래도 반영한 이유: 「분할됐다」는 사실은 두 자식 SPEC 이 명시하고, superseded 는 자식 목록 완비를 전제로 하지 않는다. manager-docs 는 이 이유로 건너뛰었고, 레인이 판단해 반영했다 — 리드가 다르게 보면 되돌리면 된다.

## 3. 빼기 전에 잰 것(기록만 — 반영 안 함)

리드 정정 전에 잰 결과. 나중 카드가 쓸 수 있게 남긴다.

- 카드 근거와 **다른 것 둘**: ⑦LDSTORE 의 제안 SHA `32b81eb9` 는 main 역사에 없다(`origin/feat/ldstore-m3-knowledge-seed` 에만 있음). main 에서 completed 를 실어 온 커밋은 PR #462 를 합친 `f12d590e`. · TRUNCATE 도 TREEID 처럼 progress.md 가 없다(카드에는 TREEID 만 적힘).
- 나머지 ①②③④ 과 LDGUIDE SHA(`3bfe660` 은 없는 객체, `15590e36` 은 main 에 있음)는 카드 근거와 맞았다.

## 4. 안 잰 것 · 남은 위험

- 감독 결정(LDRENDER completed)은 리드가 전한 말이다. 레인은 그 결정 원문을 보지 못했다.
- 이 변경은 plan-auditor 를 거치지 않았다(카드 절차에 없음).
- manager-spec 서브에이전트는 네트워크 오류(ENOTFOUND)로 보고를 다 하기 전에 끊겼다. 남은 두 파일의 diff 는 레인이 직접 읽어 확인했다(§1).
