# 상류 어휘 확장 제안 — 표제 문장이 매칭되게 하라

> 작성일: 2026-08-02 · 상태: **이행 완료(2026-08-02, 하단 §6)** · 작성 경위: SPEC-COPILOT-SCENE-001 M8 종단 라이브가 발견하고
> 사용자가 **안 D(기록만 하고 넘긴다)** 로 확정하며 후속 SPEC의 명시 대상으로 넘긴 결함의 이행 문서.
>
> 원 기록: `SPEC-COPILOT-SCENE-001/progress.md` §E.2 M8 절 ⑦(실측 표) · §E.4 "어휘 결정" 절(안 A~D 판정 표).
> 아래 "사전 실측"은 본 제안서 작성 시점(`origin/main` = `4598c36`)에 다시 잰 것이다.

## 1. 문제 — 문서가 자기 예시를 실행하지 못한다

SCENE SPEC의 표제 문장 **"파란 백라이트가 천천히 웨이브하는 씬 만들어줘"** — spec.md §A·acceptance.md
시나리오 1·plan.md §B M8이 그대로 쓰는 문장 — 이 `find_scene`에서 **양 축 `no_match`** 로 떨어진다.
체인 자체는 정상이다: 어휘가 있는 문장(`달빛 웨이브`)에서는 두 축이 정확히 붙는다.

M8 실측 표 (SCENE progress.md §E.2 ⑦ 전재):

| 질의 | fx | looks | scene |
|---|---|---|---|
| `웨이브` | `wave-soft-rise` | — | fx_only |
| **`웨이브하는`** | **None** | — | fallback |
| **`파란`** | — | **None** | fallback |
| `달빛 웨이브` | `wave-soft-rise` | `ballad-moonlight` | **both_matched** |

원인 두 가지, 둘 다 상류 어휘다:

1. **`하는`(하다-용언 관형형)이 어미 목록에 없다.** 접미 정규식이 목록에 없는 어미를 벗기지 못해
   `웨이브하는`이 별칭 `웨이브`에 닿지 않는다.
2. **`파란`이 룩 별칭에 없다.** 라이브러리는 `푸른`만 안다.

SCENE은 이것을 고칠 수 없었다 — 두 상류(`server/fx/**` · `server/looks/**`)가 SCENE의 PRESERVE였고,
씬 계층 단독 수정(안 A)은 `find_fx`와 `find_scene`이 **같은 문장에 다르게 답하는 행동 분기**를 만든다.

## 2. 사전 실측 (2026-08-02, `4598c36`) — 다음 세션이 재조사하지 않아도 되는 것

> **※ 2026-08-07** — **이행 전 스냅샷이다.** 이 절의 `파일:줄` 좌표는 이행 커밋 이후 이동했을 수 있다 — 앵커(심볼명)로 찾고 줄번호는 재실측할 것.

### 편집 지점

| 지점 | 실측 | 의미 |
|---|---|---|
| `server/fx/matching.py:163` `_ENDINGS` | 7개: `주세요·줄래·줄까·다오·보자·줘·봐` — **`하는` 없음** | fx 축 어미 확장 지점 |
| `server/scene/matching.py:97` `_ENDINGS` | **fx와 완전 동일한 7개 사본** | ⚠️ 같이 고치지 않으면 두 표면이 갈라진다 — 아래 §3 결정 ① |
| `server/looks/matching.py` | `_ENDINGS` **자체가 없다**(`_PARTICLES`만, :144) | `파란`은 어미 문제가 아니라 **별칭 부재** — looks 쪽은 어미 축 무관 |
| `server/looks/library/**` `파란` | **0건** (`푸른`은 worship.yaml:89-90 `푸른 벌스` · ballad.yaml:44 `푸른 밤` · edm.yaml:74) | 별칭/무드 키워드 추가 지점 |

### 제약 실측

- **`_ENDINGS`를 닫힌 집합으로 고정하는 테스트는 0건이다** (`grep -rn "_ENDINGS" server/tests/` → 0).
  확장이 형상 고정과 싸우지 않는다. 뒤집어 말하면 **fx↔scene 사본 동치를 지키는 가드도 없다** —
  이번 확장이 그 가드를 세울 기회다.
- fx·looks·scene의 `_PARTICLES`/`_ENDINGS` 중복은 **확립된 선례**다(SCENE 병렬 웨이브 M3 정정 기록:
  "각자 자기 본을 가진 확립된 선례 — 사본이라고 다 같은 사본이 아니다"). 단 `PATTERN_ALIASES`처럼
  **공개 상수는 읽기 import**가 규율이었다. 어미 목록을 어느 쪽으로 볼지가 plan-phase 결정이다.
- 룩 자산 편집 시 **LOOKLIB 자산 테스트**(32룩 코어4 강제 등)와 **SCENE의 32룩 전수 스윕**이
  살아 있다 — 별칭·무드 키워드 추가는 값 라인을 건드리지 않으므로 충돌하지 않아야 정상이나,
  `test_looks_library.py`에 별칭 중복 금지·개수류 단언이 있는지 착수 시 확인할 것.
- **룰북은 무관하다** — 이 확장은 `server/rulebook/assets/**`를 건드릴 이유가 없고, 건드리면
  byte-diff 0 게이트가 죽는다.

### 왜 라이브 세션이 필요 없는가

매칭은 **순수 정적 계층**이다(콘솔 무접촉 — SCENE REQ-SCENE-007 계열). 인수는 전부 pytest로 선다.
라이브 세션 0회 SPEC의 선례는 OVERLAP이다.

## 3. plan-phase가 정해야 할 결정 (미리 좁혀 둔 것)

| # | 결정 | 선택지 | 사전 관찰 |
|---|---|---|---|
| ① | fx↔scene 어미 사본 처리 | (a) 둘 다 편집 + **동치 가드 테스트 신설** / (b) scene이 fx를 읽기 import | (b)는 M3 정정(`PATTERN_ALIASES`)과 같은 방향이지만, `_ENDINGS`는 `_SUFFIX` 정규식 조립에 들어가는 **비공개 상수**라 선례상 (a)가 관례에 가깝다. 어느 쪽이든 **"오늘 같음"이 아니라 "같음이 강제됨"** 을 산출물로 남겨야 한다 |
| ② | `하는` 하나인가, 용언 관형형 부류인가 | `하는`만 / `하는·시키는·거리는` 등 부류 | M8 실측은 `하는` 1건만 갈랐다. **측정 없이 부류를 넓히지 말 것** — SCENE 교리("채움값 발명 금지")의 어미판 |
| ③ | `파란`을 어디에 넣나 | 별칭(`aliases`) / 무드 키워드(`mood_keywords`) / 둘 다 | `푸른`은 두 곳 모두에 있다(worship.yaml:89-90). 대상 룩 선정도 결정 대상 — `파란`이 `푸른 벌스`·`푸른 밤` 중 무엇에 붙어야 하는지는 **연출 판단**이라 사용자 확인이 필요할 수 있다 |
| ④ | SPEC 형식 | FXLIB/LOOKLIB **amendment**(`completed → in-progress`, `amendment_of:`) / 신규 SPEC | 두 완료 SPEC의 자산·코드를 고치므로 frontmatter 규율(§ Status Transition)상 amendment 경로가 정석. 신규 SPEC이면 두 SPEC에 걸친 소유권 서술이 필요하다 |

## 4. 인수 기준 스케치

1. **표제 문장이 붙는다**: `find_scene("파란 백라이트가 천천히 웨이브하는 씬 만들어줘")` →
   두 축 매칭(`no_match` 아님). 씬 조합 자산이 없으면 `no_scene_composes_axes`가 **정직한 답**이다 —
   그 사유까지 없애려면 ~~조합 씬 자산 추가가 별도 항목이 된다~~ → **조건 미성립으로 소멸(2026-08-07).** §6 실측이 실제 씬(`ballad-moonlight-rise`)에 착지했으므로 `no_scene_composes_axes`는 발동하지 않았고 별도 항목도 열리지 않았다.
2. **두 표면이 같은 답을 낸다**: 같은 문장에 대해 `find_fx`와 `find_scene`의 fx 축 판정이 일치.
   (SCENE이 안 A를 기각한 이유가 이 속성이다 — 이제 이것을 **테스트로** 세운다.)
3. **기존 어휘 무회귀**: fx 12·룩 32·씬 5의 기존 질의 코퍼스(SCENE `test_scene_matching.py`의
   57질의 순회 포함) 전건 무변화.
4. **어미 목록 동치 강제**(결정 ①의 산출): fx↔scene이 갈라지면 죽는 가드.
5. 뮤테이션: `하는` 항목 제거 시 표제 문장 테스트가 죽는다 / `파란` 별칭 제거 시 동일.

## 5. ~~착수 절차 (다음 세션)~~ — **취소 (§6 결정 ④로 대체)**

> **※ 2026-08-07** — 이 절은 *"`/moai plan`으로 SPEC 개설"* 을 지시하지만 **§6 결정 ④가 경량 진행(SPEC 미개설)으로
> 그것을 취소했고 그 경로로 실제 이행됐다.** 살아 있는 지시문으로 남으면 다음 세션이 **이미 닫힌 SPEC을 연다.**
> 아래 내용은 작성 시점 계획의 기록으로만 보존한다.

```bash
# 1. 상태 확인 (SCENE §0 킥오프 킷의 4종 그대로)
git log --oneline -3          # 4598c36 … 85611a1 … e4bc78e   ← 작성 시점 베이스 기록. 이행 커밋은 그 뒤에 났고 main은 계속 전진했다 — 이 SHA로 현재 상태를 확인하지 말 것
# 2. 이 제안서와 SCENE progress.md §0 · §E.4 를 읽는다
# 3. /moai plan 으로 SPEC 개설 — §3의 결정 4건을 plan-phase 질문으로 올린다
```

**착수 전 금지 사항 승계**: `feat/spec-copilot-scene-001` 브랜치 삭제 금지(SCENE 증거 사슬) ·
새 SPEC의 PRESERVE BASE는 **자기 착수 시점 SHA**(SCENE 게이트 명령 복사 금지 — PRECHK §E.9 함정) ·
SCENE §0 교훈 21~25 승계(특히 22 "문이 둘이면 그물도 둘", 23 "가드 전수 스윕은 싸고 값지다").

## 6. 이행 기록 (2026-08-02 — 경량 진행, Orca 오케스트레이션)

사용자 확정: SPEC 미개설 **경량 진행**(결정 ④), 나머지 결정은 아래와 같이 닫혔다.

| # | 결정 | 확정 |
|---|---|---|
| ① | fx↔scene 어미 사본 | **(a) 둘 다 편집 + 동치 가드 신설** — `server/tests/test_matching_endings_parity.py`가 원소·순서 동일을 강제 |
| ② | 어미 범위 | **`하는` 1건만** (측정된 것만) |
| ③ | `파란` 위치 | **`푸른`이 있는 모든 슬롯에 미러** — worship.yaml(aliases+mood) · ballad.yaml(aliases+mood) · edm.yaml(mood) · **scene core.yaml:27(mood)** |
| ④ | SPEC 형식 | 경량 진행 — 코드+테스트+본 기록 |

수행 형태: 쓰기 집합 교집합 ∅ 검증 후 Orca orchestration 2-병렬(Run `run_3549d1b7ee86`). 슬라이스 B(룩 별칭)는
워커가 완주(`worker_done`, 431 green). 슬라이스 A(어미 축) 워커는 Claude CLI 로그인 만료로 착수 실패 —
**코디네이터가 인라인 구현**(오케스트레이션 밖 실행임을 명기, task는 failed로 정산).

이음매 발견(SCENE 교훈 17 재현): 상류 두 곳만으로는 표제 문장의 look 축이 열리지 않는다 —
`match_scene`의 look 축 어휘는 **씬 자산의 자기 항목**에서 나오므로(`server/scene/matching.py` `_terms_for`),
`server/scene/library/core.yaml`의 `푸른`(ballad-moonlight-rise mood)에도 미러가 필요했다. 워커 B는 scene/** 금지였고
이 지점은 코디네이터가 통합 검증에서 잡아 반영했다.

인수 실측 (§4 대비):

1. 표제 문장 `find_scene` → **both_matched · ballad-moonlight-rise** (look=ballad-moonlight · fx=wave-soft-rise). ✅
2. 두 표면 동일 답: `웨이브하는`에 `match_fx`·`match_scene` fx 축 모두 wave-soft-rise — 테스트로 고정. ✅
3. 무회귀: pytest **3938 passed / 5 skipped** (직전 정본 3927+11 신규 — parity 8 + blue alias 3). ✅
4. 동치 가드: `TestEndingListParity` — fx↔scene 갈라지면 죽는다. ✅
5. 뮤테이션 실측: `하는` 제거 → 5 failed / `파란`(ballad) 제거 → 6 failed — 둘 다 킬 확인 후 원복. ✅

`푸른`↔`파란` 쌍둥이 문장 동일 답도 테스트로 고정(`test_the_blue_twin_words_answer_identically`).
룰북(`server/rulebook/assets/**`) 무접촉.

커밋 후에만 보이는 게이트(SCENE 교훈 18 재현): OVERLAP의 상시 PRESERVE 게이트
(`test_overlap_preserve.py`)가 `server/looks/library/`를 PRECHK BASE 기준으로 잠그고 있어 커밋 직후
1건 FAIL — 약화 대신 **정밀 허가**로 갱신했다(`TestLooksLibraryGrantedExtension`: 3파일·라인쌍
정확 텍스트만 통과, 그 외는 여전히 FAIL). 최종: pytest **3941 passed / 5 skipped**.
커밋: `761f01e`(확장 본체) · `c052d9f`(게이트 정밀 허가).
