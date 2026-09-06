---
id: SPEC-COPILOT-D1GRANT-001
title: "cyc 없는 리그의 조용한 칸 — 룩 라이브러리 확장을 승인된 통로로 연다"
version: "0.1.0"
status: draft
created: 2026-09-06
updated: 2026-09-06
author: manager-spec (plan session, card t282 후속)
priority: P1
phase: "v1.8.2 target"
module: "server/looks/library/edm.yaml, server/looks/library/rock.yaml, server/tests/test_overlap_preserve.py, server/tests/test_songcue_rig_aware_look.py, server/tests/test_songcue_d1_cycless.py, server/tests/test_busking_genre.py, server/tests/test_looks_matching.py, server/looks/busking.py"
lifecycle: spec-anchored
tags: "looks-library, dynamics-1, cyc-less-rig, preserve-gate, granted-append, declaration-layer, pinned-test-flip, design-artifact, zero-console-write"
tier: M
related_specs: [SPEC-COPILOT-PRECHK-001, SPEC-COPILOT-OVERLAP-001, SPEC-COPILOT-SONGCUE-001, SPEC-COPILOT-BUSKWIZ-001, SPEC-COPILOT-LOOKLIB-001]
---

# SPEC-COPILOT-D1GRANT-001 — cyc 없는 리그의 조용한 칸

> **이 SPEC 이 닫는 구멍**: 실기 리그에서 **곡의 가장 조용한 구간이 큐를 하나도 못 받는다.**
>
> 감독이 4개 구간을 확정했는데 저장된 큐는 3개였다(카드 t277, 실기 grandMA3 실측). 사라진 것은 인트로다. EDM 의 유일한 dynamics-1 룩 `edm-ambient-hold` 는 역할이 `배경` 하나뿐이고, 실기 리그의 18개 그룹에는 cyc/호리 계열이 **없다**. 묶일 그룹이 없으니 번들이 올바르게 건너뛰었고, 그 침묵은 오류 메시지 없이 지나갔다.
>
> **선택 로직으로는 못 닫는다.** 카드 t278 이 선택기를 「이 리그에서 실제로 묶이는 룩」을 고르도록 고쳤고 worship 을 살렸다. 그러나 edm 과 rock 은 **고를 것이 없다** — 두 장르의 D1 룩은 각각 하나뿐이고 그 역할은 `배경` 뿐이다. t278 은 이 잔여를 `server/tests/test_songcue_rig_aware_look.py::TestWhatThisFixCannotReach` 에 정직하게 못박았다. 남은 것은 **라이브러리 내용**이지 로직이 아니다.
>
> **그리고 그 내용을 넣는 통로가 막혀 있다.** 카드 t282 가 넣으려다 PRESERVE 초크포인트에 **정당하게** 막혔고, 게이트를 약화시키지 않고 멈췄다(PR #344, 브랜치 `WT-d1-looks`). 이 SPEC 이 여는 것은 그 통로 하나다 — **두 파일에 각각 한 룩**, 그 이상은 아니다.

> **콘솔 쓰기 0.** 이 SPEC 이 콘솔에 발화하는 명령은 없다(REQ-D1GRANT-020). 실기 검증은 이 SPEC 의 산출물이 아니다(§4).

## HISTORY

| 날짜 | 버전 | 변경 | 근거 |
|---|---|---|---|
| 2026-09-06 | 0.1.0 | 최초 작성 (카드 t282 후속, Tier M) | t277 실기 실측 · t278 잔여 핀 · t282 게이트 실측(PR #344) |

---

## §1 왜 (WHY)

### 1.1 관측된 손해

카드 t277, 실기 grandMA3: 감독이 확정한 4개 구간 중 **3개만** 콘솔에 저장됐다. 버려진 것은 가장 조용한 구간이고, 앱은 그것을 실패로 보고하지 않았다. 운영자가 세어 보기 전에는 알 수 없다.

### 1.2 왜 로직으로 못 닫는가

카드 t278 이 원인을 확정했다: `_map_section_to_look` 이 요청 다이내믹스에 맞는 **첫** 룩을 리그와 무관하게 집었다. t278 은 `_select_bindable`(`server/looks/songcue.py:427`)을 넣어 「요청 다이내믹스 안에서 이 리그에 실제로 묶이는 첫 룩」을 고르게 했고, 이미 묶이는 D1 룩을 갖고 있던 worship 은 그 한 줄로 살아났다.

edm·rock 은 살아나지 않았다. 이 트리(`a1e75e5`)에서 다시 쟀다:

```
--- D1 census ---
ballad [('ballad-moonlight', ('배경', '백라이트')), ('ballad-single-key', ('스페셜',))]
edm [('edm-ambient-hold', ('배경',))]
rock [('rock-empty-stage', ('배경',))]
worship [('worship-prayer-wash', ('배경', '탑')), ('worship-scripture-key', ('프론트', '스페셜'))]
```

그리고 실기 18그룹의 역할 결속(같은 회차, `resolve_roles`):

```
mapped: ['백라이트', '사이드', '스페셜', '프론트']
unmapped: {'탑': 'no_match', '배경': 'no_match'}
```

edm·rock 의 D1 후보 집합은 크기 1 이고 그 유일한 원소가 안 묶이는 역할만 갖는다. **선택기가 못 고르는 것이 아니라 고를 것이 없다.** ballad 가 멀쩡했던 것도 선호 때문이 아니라 `ballad-moonlight` 이 `배경`+`백라이트` 를 함께 갖고 있어서다 — 역할 하나만 묶여도 저장되기 때문이다.

### 1.3 왜 게이트가 막았고, 왜 그것이 옳았는가

`server/looks/library/` 는 `server/tests/test_overlap_preserve.py` 의 `_PRESERVE_PATHS`(`:96-107`, 열 항목 중 일곱 번째) 아래에 있고, 그 디렉터리에는 2026-08-02 「파란」 미러 예외 하나만 승인돼 있다(`_LOOKS_GRANTED_LINE_PAIRS`, `:311-338`). 그 예외는 줄 텍스트만이 아니라 **바뀐 파일 집합 자체**를 못박는다(`:1078-1080`):

```python
    def test_exactly_the_three_granted_files_changed(self):
        rows = _numstat(_PRECHK_BASE, _LOOKS_LIBRARY_DIR)
        assert set(rows) == set(_LOOKS_GRANTED_LINE_PAIRS)
```

키가 `ballad.yaml`·`edm.yaml`·`worship.yaml` 셋뿐이므로 **추가조차 통과하지 못한다.** t282 가 후보 룩 하나를 `rock.yaml` 에 붙여 실측한 판정:

```
E       AssertionError: assert {'server/look...worship.yaml'} == {'server/look...worship.yaml'}
E         Extra items in the left set:
E         'server/looks/library/rock.yaml'
1 failed, 53 passed in 1.26s
```

이것은 결함이 아니라 게이트가 설계대로 동작한 것이다. 룩 라이브러리는 **실기 콘솔에 도달하는 연출 자산**이고, 아무도 다시 확인하지 않는 경로로 조용히 늘어나면 안 된다.

### 1.4 왜 새 SPEC 이어야 하는가 — 그리고 닫힌 SPEC 문제는 실재하지 않는다

`test_overlap_preserve.py` 의 모듈 독스트링(`:52-61`)은 처방 순서를 정한다: 게이트에 예외를 다는 것은 마지막 수단이고 **먼저 가는 곳은 선언 층**이다. 원래 선언은 `SPEC-COPILOT-PRECHK-001/plan.md:89` §A.5 첫 행 — 「PRECHK는 룩 계층 소비자가 아니다. 변경 0건」. 그리고 독스트링은 이렇게 경고한다: **「닫힌 SPEC 의 선언을 사후에 고치는 경우는 이 선례가 덮지 않는다.」**

t282 는 그 문장에서 멈췄다. 그 신중함은 옳았지만, 한 걸음 더 재면 막다른 길이 아니다. 이 게이트에는 이미 **네 건의 승인된 예외**가 살아 있고, **넷 다 PRECHK 가 아닌 다른 SPEC 이 발급했으며, 넷 다 PRECHK 의 §A.5 를 고치지 않았다**(`test_overlap_preserve.py` 실측):

| 승인 | 발급 SPEC | 대상 | 상수 |
|---|---|---|---|
| 2026-08-02 | 상류 어휘 확장 제안서 (§6, 사용자 승인) | `server/looks/library/` 「파란」 미러 | `_LOOKS_GRANTED_LINE_PAIRS` (`:311`) |
| 2026-08-03 | `SPEC-COPILOT-SPATIAL-001` M3 | 룰북 자산 1건 추가 | `_RULEBOOK_GRANTED_ADDITIONS` (`:130`) |
| 2026-08-15 | `SPEC-COPILOT-FXGEN-001` REQ-FXGEN-017 (b) | 룰북 자산 1건 **append-only** | `_RULEBOOK_GRANTED_APPEND` (`:144`) |
| 2026-08-12~2026-09-04 | `SPEC-COPILOT-DEPLOY-001` 외 (재핀 다수) | `console/lua/**` 개정 | `_CONSOLE_LUA_GRANTED_REVISION_DIGESTS` (`:298`) |

`_RULEBOOK_DIR` 과 `console/lua/` 역시 PRECHK §A.5 가 「변경 0건」으로 선언한 항목이다(`plan.md:89` 표의 3·4행). 즉 **PRECHK 의 선언을 고치지 않고 새 SPEC 이 자기 이름으로 예외를 발급하는 것**은 이 파일에서 네 번 반복된 정규 경로다.

그 이유는 독스트링 자신이 설명한다(`:42-50`): §A.5 의 문장은 **「PRECHK 는 이 파일들을 안 건드렸다」는 역사적 사실**이지 「아무도 못 건드린다」는 집행 경계가 아니다. 역사적 사실은 고쳐서는 안 되고, **고칠 필요도 없다** — 이 SPEC 이 룩 파일을 건드려도 「PRECHK 가 안 건드렸다」는 여전히 참이다.

따라서 이 SPEC 이 하는 일은 **닫힌 선언의 개정이 아니라 새 선언의 발급**이다. 필요한 감독 결정은 「PRECHK 를 고쳐도 되는가」가 아니라 **「이 두 룩을 라이브러리에 넣어도 되는가」** 하나이며, 그 결정의 기록 자리가 이 문서다.

---

## §2 무엇을 (WHAT)

`server/looks/library/edm.yaml` 과 `rock.yaml` 에 각각 **dynamics 1 룩 하나씩**을 파일 끝에 덧붙이고, 그 추가를 `test_overlap_preserve.py` 에 **이 SPEC 이름으로 날짜가 붙은 append-only 예외**로 등록한다. 예외는 파일 둘·룩 둘로 닫혀 있고, 그 밖의 어떤 변경도 여전히 게이트에서 실패한다.

동시에, 이 추가로 뒤집히는 **핀 세 종**(잔여 기록·개수 단언·산문 인용)을 같은 커밋에서 **의도적으로** 갱신한다. 조용히 뒤집히는 핀은 구멍보다 나쁘다.

---

## §3 요구사항 (GEARS)

### 3.1 라이브러리 내용

- **REQ-D1GRANT-001** [Ubiquitous] — the `server/looks/library/edm.yaml` **shall** dynamics 1 룩 `edm-haze-shafts` 를 **정확히 하나** 얻는다. `roles` 는 `["백라이트"]`, `display_name` 은 `"헤이즈 샤프트"`, 색·밝기는 `Dimmer 18` · `ColorRGB_R 0` · `ColorRGB_G 40` · `ColorRGB_B 78`. 역할 선택 근거: EDM 헤더 규칙(`edm.yaml:22-25`, 「관객은 부스를 본다」)이 `프론트` 를 배제하고, `탑` 은 실기 리그에서 안 묶인다(§1.2 실측) — 배경막 없이 깊이를 만드는 것은 뒤에서 오는 빛뿐이다.
- **REQ-D1GRANT-002** [Ubiquitous] — the `server/looks/library/rock.yaml` **shall** dynamics 1 룩 `rock-wing-embers` 를 **정확히 하나** 얻는다. `roles` 는 `["사이드"]`, `display_name` 은 `"윙 엠버"`, 색·밝기는 `Dimmer 22` · `ColorRGB_R 65` · `ColorRGB_G 10` · `ColorRGB_B 22`. 역할 선택 근거: rock 헤더 규칙(`rock.yaml:8-12`, 「얼굴은 어둡고 형태만 있다 — `프론트` 는 코러스에서 온다」)이 `프론트`·`스페셜` 을 배제하고, `백라이트` 는 바로 다음 칸 `rock-verse-side`(D2)가 이미 쓴다 — D1 에서 미리 쓰면 벌스 진입의 대비가 사라진다.
- **REQ-D1GRANT-003** [Ubiquitous] — the 두 새 `look_id` **shall** 자기 장르의 기존 D1 `look_id` 보다 **사전순 뒤**에 온다. 이것이 cyc 있는 리그의 무회귀를 지키는 **유일한** 기제다: `looks_for_genre`(`server/looks/busking.py:81-97`)는 `(dynamics, look_id)` 로 정렬하며 **파일 안의 위치를 보지 않는다.** 이 트리에서 실측: `sorted(["edm-ambient-hold","edm-haze-shafts"])` → `['edm-ambient-hold', 'edm-haze-shafts']`, `sorted(["rock-empty-stage","rock-wing-embers"])` → `['rock-empty-stage', 'rock-wing-embers']`. 이 성질은 주석이 아니라 **검사로** 고정한다.
- **REQ-D1GRANT-004** [Unwanted] — the 이 SPEC **shall not** 기존 룩의 어떤 필드도 바꾼다. 네 자산 파일의 삭제 줄은 2026-08-02 승인된 「파란」 쌍의 옛 줄 넷 **외에 0건**이어야 한다.
- **REQ-D1GRANT-005** [Ubiquitous] — the 두 추가 블록 **shall** 각 파일의 **옛 EOF 뒤**에 붙는다(edm.yaml 156행, rock.yaml 141행 — 기준 커밋 `95687a0e` 에서 실측). 기능적 이유가 아니라(REQ-003 이 순서를 정한다) 게이트 이유다: 순수 삽입 훅 하나는 위쪽 줄을 한 줄도 밀지 않으므로 승인된 「파란」 쌍의 훅 위치가 그대로 유지되고, 추가된 줄의 diff 순서가 결정론적이 된다.

### 3.2 선언 층과 게이트

- **REQ-D1GRANT-006** [Ubiquitous] — the `SPEC-COPILOT-PRECHK-001/plan.md` **shall** 바이트 동일하게 유지된다. 이 SPEC 은 닫힌 SPEC 의 선언을 개정하지 않고 §1.4 의 네 선례와 같은 방식으로 **자기 이름의 예외를 발급**한다.
- **REQ-D1GRANT-007** [Ubiquitous] — the `server/tests/test_overlap_preserve.py` **shall** 새 모듈 수준 상수 `_LOOKS_GRANTED_D1_APPENDS` 를 `_LOOKS_GRANTED_LINE_PAIRS`(`:338`) 바로 뒤에 얻는다. 형태는 「경로 → 덧붙인 줄의 정확한 텍스트 튜플」이며, 바로 위에 승인 주석이 `2026-09-06 granted addition — SPEC-COPILOT-D1GRANT-001` 로 시작해 이 SPEC ID 를 명시한다(`:109`·`:135`·`:303` 의 기존 승인 주석과 같은 모양).
- **REQ-D1GRANT-008** [Ubiquitous] — the `TestLooksLibraryGrantedExtension` 의 파일 집합 단언(`:1078-1080`) **shall** 두 승인의 **합집합**을 요구한다 — `set(rows) == set(_LOOKS_GRANTED_LINE_PAIRS) | set(_LOOKS_GRANTED_D1_APPENDS)`. `edm.yaml` 은 두 집합 **모두**에 속하고, `rock.yaml` 은 새 집합에만, `ballad.yaml`·`worship.yaml` 은 옛 집합에만 속한다.
- **REQ-D1GRANT-009** [Ubiquitous] — the 줄 텍스트 단언(`:1082-1086`) **shall** 추가분을 **느슨하게 흡수하지 않는다.** 파일별로 삭제 줄은 승인된 쌍의 옛 줄과 **정확히** 같아야 하고, 추가 줄은 `[쌍의 새 줄…] + [덧붙인 블록…]` 과 **정확히** 같아야 한다. 이 순서는 REQ-005 가 보장한다(`edm.yaml` 의 「파란」 훅은 옛 74행, 삽입 훅은 옛 156행 — 실측).
- **REQ-D1GRANT-010** [Ubiquitous] — the 게이트 **shall** 각 승인 파일의 추가가 **옛 EOF 위의 순수 삽입 훅 하나**임을 단언한다 — `old_count == 0` 이고 `old_start == len(기준 커밋 본문의 줄 수)`. 형태는 `TestChoreographyObservedEffectGrantedAppend::test_the_addition_is_one_appended_hunk_at_the_old_eof`(`:993-1000`)를 그대로 따른다.
- **REQ-D1GRANT-011** [Ubiquitous] — the 게이트 **shall** 덧붙인 블록마다 `- look_id:` 가 **정확히 한 번** 나타남을 단언한다. 이것이 「파일당 룩 하나」라는 승인의 폭을 기계로 고정하는 자리다.
- **REQ-D1GRANT-012** [Unwanted] — the 이 SPEC **shall not** 게이트를 넓힌다. 반영 후에도 다음 셋은 **여전히 실패해야** 하며, 그 실패를 심은 변경으로 실측한 뒤 되돌린다: ① `server/looks/library/` 의 세 번째 파일 변경, ② 승인 파일에 룩 하나 더 덧붙이기, ③ 승인 파일에서 줄 하나 삭제.
- **REQ-D1GRANT-013** [Unwanted] — the 이 SPEC **shall not** `_PRESERVE_PATHS`(`:96`), `_preserve_diff_command`(`:671`), `_PRECHK_BASE`(`:77`) 를 바꾼다. 승인은 **좁히는 방향으로만** 더해진다.

### 3.3 뒤집히는 핀

- **REQ-D1GRANT-014** [Ubiquitous] — the `server/tests/test_songcue_rig_aware_look.py::TestWhatThisFixCannotReach`(`:237`) **shall** 삭제가 아니라 **교체**된다. 새 클래스의 독스트링은 **전/후를 함께** 적는다 — 전: edm·rock 의 D1 룩이 하나이고 역할이 `("배경",)` 뿐이며 `ambient` 밴드가 실기 리그에서 큐를 못 받았다. 후: 두 장르가 묶이는 D1 룩을 얻었고 `ambient` 가 큐를 받는다. 새 단언은 **네 장르 전부** 실기 리그에서 D1 큐를 받는다는 것이며, 그 근거로 각 장르에 역할이 `{탑, 배경}` 의 부분집합이 **아닌** D1 룩이 하나 이상 있음을 함께 단언한다.
- **REQ-D1GRANT-015** [Ubiquitous] — the `test_the_matrix_is_recorded_for_the_report`(`:263`) **shall** 실기 리그 행렬을 네 장르 모두 `"OOOOO"` 로 갱신하고, **같은 자리에 음성 대조 행렬**을 둔다 — `_UNBINDABLE_RIG` 로 잰 네 장르 전부 `"XXXXX"`. 전량 O 인 행렬만으로는 「쟀는데 통과」와 「계측기가 공허」가 밖에서 구별되지 않는다.
- **REQ-D1GRANT-016** [Ubiquitous] — the `server/tests/test_songcue_d1_cycless.py` **shall** 최종 상태에서 skip 게이트를 **하나도** 갖지 않는다: `_require_proposed` 헬퍼와 `TestTheSkipIsNotAPermanentPass` 클래스가 사라지고, 남은 세 클래스가 무조건 실행된다. 이 파일은 PR #344 (브랜치 `WT-d1-looks`) 에서 부재 트립와이어로 태어났으며, 룩이 들어오는 순간 그 트립와이어가 자기 목적을 다한다.

### 3.4 개수를 세는 소비자

- **REQ-D1GRANT-017** [Ubiquitous] — the `server/tests/test_busking_genre.py` **shall** `_EXPECTED_COUNTS`(`:30`)를 `edm` 9→10, `rock` 8→9 로 갱신한다. `test_edm_nine_looks_survive`(`:45`)는 이름과 리터럴을 함께 갱신하되 **비공허 근거는 유지한다** — 그 검사의 요지는 「9」가 아니라 `len(edm) > MAX_TOOL_MATCHES`(=8), 즉 절단 경로를 안 탔다는 증명이다.
- **REQ-D1GRANT-018** [Ubiquitous] — the `server/tests/test_looks_matching.py::test_a_long_result_is_truncated_and_says_it_was`(`:673-677`) **shall** `report["total"]` 기대값을 9→10 으로 갱신하고, 같은 함수 안의 `min(9, MAX_TOOL_MATCHES)` 와 `MAX_TOOL_MATCHES < 9` 리터럴도 함께 옮긴다.
- **REQ-D1GRANT-019** [Ubiquitous] — the 산문 인용 **shall** 실측에 맞춰진다 — `server/looks/library/edm.yaml:7` 의 「Nine looks」, `server/looks/busking.py:13` 의 「EDM은 9룩이므로 … **정확히 1건이 조용히 사라진다** — 8룩이 돌아오고」. 후자는 숫자만 바꾸면 틀린다: 10룩이면 사라지는 것은 2건이다.
- **REQ-D1GRANT-020** [Ubiquitous] — the run 단계 **shall** 룩 **개수**에 의존하는 자리를 전수로 재고 그 명령과 결과를 progress 에 남긴다. §3.4 의 세 건은 plan 단계에서 실측한 것이며 **전수라는 주장이 아니다**. `server/preshow/checks.py:111` 은 개수를 동적으로 세어 보고만 하므로 핀이 아니다(같은 회차 실측).

### 3.5 예산

- **REQ-D1GRANT-021** [Unwanted] — the 이 SPEC **shall not** 콘솔에 어떤 명령도 발화한다. 검증은 전량 오프라인이며, `127.0.0.1:8000` 대상 실행 0건이다.

---

## §4 범위 제외 (Exclusions)

이 절은 **만들지 않을 것**을 적는다. 아래 항목은 out of scope 이며, 이 SPEC 의 어떤 마일스톤도 이들을 건드리지 않는다.

### Out of Scope — 선택 로직과 번들 경로

- `_select_bindable`·`_bound_groups`·`_section_bundle`(`server/looks/songcue.py`)은 카드 t278 이 이미 고쳤고 이 SPEC 은 **한 줄도** 바꾸지 않는다. 이 SPEC 이 더하는 것은 그 선택기가 고를 **재료**다.
- `resolve_roles`·`server/looks/resolver.py` 의 역할 사전, `ROLE_NAMES` 어휘는 손대지 않는다. `탑`·`배경` 이 실기 리그에서 안 묶이는 것은 이 SPEC 이 **우회할** 사실이지 고칠 대상이 아니다.

### Out of Scope — 다른 장르·다른 칸의 확장

- ballad·worship 은 이미 묶이는 D1 룩을 갖고 있다(§1.2 실측). 이 SPEC 은 그 두 장르의 라이브러리를 건드리지 않는다.
- dynamics 2~5 의 어떤 칸에도 룩을 더하지 않는다. 관측된 손해는 D1 하나뿐이다.
- 세 번째 룩(같은 장르의 두 번째 추가)은 승인 밖이다. 특히 `edm` 은 이 추가로 10룩이 되어 `test_looks_library.py` 의 `MAX_LOOKS_PER_GENRE = 10`(`:50`) 상한에 **정확히 닿는다** — 그 상수를 올리는 것은 별도 결정이다.

### Out of Scope — 게이트의 구조 변경

- `_PRESERVE_PATHS` 목록, 기준 커밋 `_PRECHK_BASE`, `_preserve_diff_command()` 의 스왑 규칙은 바꾸지 않는다(REQ-013).
- 나머지 세 승인(`_RULEBOOK_GRANTED_ADDITIONS`·`_RULEBOOK_GRANTED_APPEND`·`_CONSOLE_LUA_GRANTED_REVISION_DIGESTS`)과 `server/safety/**`·`server/orchestrator/tools.py` 의 보호 구간은 읽기만 한다.
- `test_songcue_bundle.py` 의 선례 게이트(다른 기준 커밋에 묶여 있다)는 건드리지 않는다.

### Out of Scope — 실기 발사와 색 값의 실측 보정

- 두 룩을 실기 콘솔에서 발사해 색·밝기를 눈으로 확인하는 회차는 이 SPEC 의 산출물이 **아니다**. 값은 라이브러리 안 이웃 룩에서 역산한 **설계값**이며(§5), 실기 확인은 sync 단계에서 별도 카드로 올린다.
- 무빙 속성(Pan/Tilt), 빔 계열 속성, 효과 계열은 이 두 룩에 넣지 않는다 — v1 라이브러리의 무브먼트 0건 규율과 `FORBIDDEN_ATTRIBUTE_TOKENS`(`test_looks_library.py:75`) 스캔을 그대로 지킨다.

---

## §5 제약 (Constraints)

- **값은 설계 판단이지 측정이 아니다.** 두 룩의 색·밝기는 같은 파일 안 이웃 룩(`edm-groove-cyan` D2 · `rock-verse-side` D2 · `rock-empty-stage` D1)에서 **역산한** 값이다. 실기 콘솔에서 발사한 적이 없고, 이 SPEC 이 닫혀도 그 상태는 변하지 않는다. 이것은 코드 결함 위험이 아니라 **연출 품질 위험**이며, 감독의 눈이 최종 심판이다.
- **D2 와의 대비가 룩의 존재 이유다.** `edm-haze-shafts`(Dimmer 18, 심청) → `edm-groove-cyan`(Dimmer 55, 청록, 사이드+백라이트): 밝기 3배, 빛의 방향 추가, 색상 상승. `rock-wing-embers`(Dimmer 22, 탁한 붉은) → `rock-verse-side`(Dimmer 48, 차가운 청, 사이드+백라이트): 색온도 반전, 방향 추가. 이 대비가 무너지면 룩을 더한 의미가 없다.
- **무회귀의 축은 파일 위치가 아니라 `look_id` 사전순이다**(REQ-003). 제안서(PR #344 §2)는 「파일에서 뒤에 놓는다」로 설명했으나 `looks_for_genre` 는 파일 순서를 보지 않는다. 오늘 결과가 맞는 것은 두 새 id 가 우연히 뒤로 정렬되기 때문이며, **이름을 바꾸면 조용히 깨진다.** 그래서 검사로 고정한다.
- **핀은 의도적으로만 뒤집는다.** `TestWhatThisFixCannotReach`·`_EXPECTED_COUNTS`·`report["total"]`·산문 인용 넷은 전부 이 추가로 반드시 실패한다. 실패를 보고 숫자만 고치는 것은 이 SPEC 이 금지하는 형태이며, 각 자리에 **왜 바뀌었는지**를 남긴다(REQ-014·017·019).
- **게이트는 좁히는 방향으로만 자란다.** 승인은 더하되 `_PRESERVE_PATHS` 와 기준 커밋은 불변이고, 반영 후에도 심은 변경 셋이 실패해야 한다(REQ-012).
- **콘솔 예산 0.** REQ-021.

---

## §6 성공 기준

- `acceptance.md` 의 AC-D1GRANT-001..014 전부 통과.
- `server/tests` 전량 초록, 새 회귀 0건.
- 실기 리그 행렬 네 장르 `"OOOOO"`, 음성 대조 행렬 네 장르 `"XXXXX"`.
- 심은 변경 세 종에서 게이트가 여전히 실패(출력 인용 후 되돌림).
- `SPEC-COPILOT-PRECHK-001/plan.md` 바이트 불변.
- 콘솔 쓰기 명령 발화 0건.
