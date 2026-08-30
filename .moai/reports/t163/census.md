# t163 — 섹션 실패 사유 소실: 소비자 전수

- 카드: t163 (전수 + 판정, 코드 변경 0)
- 트리: `.claude/worktrees/t163` · 브랜치 `WT-refusal-reason-loss`
- 기준: `origin/main` **4b9d1d1** (착수 시점 재측정. 배차서의 `9ddad77` 은 한 커밋 뒤였다 — #211 이 그 사이 머지)
- 콘솔: 안 씀(실기 0건)

## 🔴 먼저 — 계기부터 틀렸다

카드의 「소비자 **9자리**」는 **내가 t152 보고서에 쓴 값이고, 틀렸다. 실측 10자리다.**

```
grep -rn "collect_rig_sections(" --include="*.py" . | grep -v tests | grep -v "def "
  -> server/orchestrator/tools.py   8자리 (2125·2220·2338·2559·4734·5685·6298·7736)
  -> server/paperwork/data.py       2자리 (180·327)
  합 10
```

리드가 내 값을 그대로 카드에 실었다. **요약이 그것이 요약한 대상의 증거가 아니다** —
이번엔 내가 그 요약의 저자였다.

## 🔴 그리고 카드의 전제가 반증됐다

카드는 「사유가 소비자에서 소실된다 — 9자리 중 몇이 같은 형태인지」로 물었다.
**같은 형태는 1자리뿐이다. 8자리가 사유를 살려 보낸다.**

t152 의 「사유가 사용자에게 안 간다」를 10자리로 일반화했으면 **8번 틀렸을 것이다.**
리드가 카드에 박은 경고(§4.1, 한 자리 관측으로 일반화 금지)가 맞았다.

## 1. 전수표 — 10자리

| # | 자리 | 도구/함수 | 사유 처리 | 기제 |
|---|---|---|---|---|
| 1 | `tools.py:2125` | `get_rig_context` | 🟢 **보존** | `summary` 를 통째로 JSON 직렬화 — 실패 단면의 `reason`·`path`·`error` 가 그대로 나간다 |
| 2 | `tools.py:2220` | `instantiate_look` | 🟢 **보존** | `"reason" in entry` 로 걸러 `f"{n}: {e['reason']}"` 로 **섹션 이름과 함께** 문면에 박고 `rig_unavailable` 도 싣는다 |
| 3 | `tools.py:2338` | busking palette | 🟢 **보존** | 위와 동일 관용구 |
| 4 | `tools.py:2559` | songcue bundle | 🟢 **보존** | 위와 동일 관용구 |
| 5 | `tools.py:4734` | `import_lxseq_groups` | 🔴 **접힘** | `map_groups` 가 `section_refusal` 의 (코드, 사유)를 `console_read_incomplete=True` 불리언으로 접는다 (t152 실측) |
| 6 | `tools.py:5685` | fx 바인딩 | 🟢 **보존** | 위와 동일 관용구 + `rig_unavailable=` |
| 7 | `tools.py:6298` | scene 바인딩 | 🟢 **보존** | 위와 동일 관용구 + `rig_unavailable=` |
| 8 | `tools.py:7736` | `create_arrangement_groups` | 🟡 **축마다 다르다** | `groups` 축은 하류 `_guard_pool_readable` 이 사유를 문면에 싣는다(보존). **`fixtures` 축은 검사가 없다** — 아래 3절 |
| 9 | `paperwork/data.py:180` | 풀 목록 | 🟢 **보존** | `unavailable_reason` + `unavailable_detail` 필드로 승격 |
| 10 | `paperwork/data.py:327` | 그룹 이름 목록 | 🟢 **보존** | `(names, reason)` 튜플로 반환 |

**집계: 보존 8 · 접힘 1 · 축마다 다름 1.**

배제 기준(숫자만 적으면 검산이 안 되므로): `server/tests/` 아래 호출(9자리)은 소비자가
아니라 검사라 뺐다. `tools.py:982`(정의)와 `:6479`(주석 언급)도 호출이 아니라 뺐다.

## 2. 카드 물음 (2) — 설계인가 각자 접은 것인가

**설계가 아니다. 한 자리가 형제와 갈렸다.**

근거 셋:

1. **8자리가 같은 관용구를 공유한다** — `unavailable = {name: entry for ... if "reason" in entry}`
   그리고 `f"{n}: {e['reason']}"`. 이건 우연히 겹친 형태가 아니라 복사된 규약이다.
2. **`section.py` 독스트링이 설계 의도를 직접 말한다**:
   > 사유를 가르는 것은 **사람이 무엇을 고쳐야 하는지가 다르기 때문**이다 —
   > 판독 실패는 연결을, 절단은 페이징을 본다.
   즉 사유를 접는 것은 이 모듈이 존재하는 이유를 되돌린다.
3. **형제 경로가 살려 보낸다.** 같은 LXSEQ 임포트 계열인 `import_lxseq_presets`
   (`tools.py:4902-4970`)는 `preset_mapper.py:284` 에서
   `if section_reason := section_refusal(pool_section):` 로 **튜플을 받아**
   `refusal` / `refusal_detail` 로 페이로드에 싣는다(`tools.py:4970-4971`).
   `group_mapper.py:362` 만 `section_refusal(...) is not None` 으로 **버린다.**

`preset_mapper.section_refusal` 은 「어휘만 번역한다」는 독스트링을 달고 공유 술어를
부른다. 두 매퍼가 같은 술어를 쓰는데 **한쪽만 결과를 버린다.**

## 3. 🔴 전수가 새로 낸 것 — :7736 의 fixtures 축

카드에 없던 발견이고, 이 카드에서 제일 값나간다.

`create_arrangement_groups` 는 `groups`·`fixtures` 두 단면을 받아 `groups` 는 하류
가드가 지키지만 **`fixtures` 실패는 아무도 안 본다.** 결과를 실행으로 쟀다.

### 3.1 groups 축 — 보존 (실행 확인)

```
A) groups 경로 미응답, fixtures 정상
   -> is_error: true · 발화 0줄
   -> {"error": "GROUP_POOL_UNAVAILABLE: the group pool could not be read
                 (path_not_resolved), so no empty slot can be measured"}
```

`collect_rig_sections` 의 사유 문자열이 **문면에 그대로** 살아 나온다.

### 3.2 fixtures 축 — 사유가 없어질 뿐 아니라 **거짓 긍정이 나간다**

```
E1) fixtures 경로 미응답, groups 정상, topology_partial 그룹 + 열거
   -> 발화 5줄 (ClearAll · Fixture 2 + 3 · Store Group 1 · Label · ClearAll)
   -> fixture_list_truncated        = false
   -> fixture_list_truncated_reason = ""

D1) 대조군: fixtures 정상(절단됨)
   -> fixture_list_truncated        = true
   -> fixture_list_truncated_reason = "the re-queried fixture container listing was truncated ..."
```

픽스처 컨테이너가 **한 글자도 안 답했는데** 페이로드가 「절단 아님」을 **적극적으로
주장한다.** 미판독이 「깨끗하게 다 읽었다」와 바이트 동일로 나간다.

### 3.3 🔴 그리고 그 손실이 @MX:ANCHOR 안전장치를 끈다

`:7742` 의 `@MX:ANCHOR` 부분판독 쓰기 거절(SPEC-COPILOT-TRUNCATE-001
REQ-TRUNCATE-008 / AC-TRUNCATE-008, mutation-required)은 열거 개수를 **부족분**
(`childCount - 열거된 수`)과 대조한다. 미판독 단면에선 `total` 이 `None` 이라
그 대조가 통째로 건너뛰어진다.

**같은 인자, 정반대 결과 (부족분 4, 열거 길이 1):**

| 픽스처 단면 | 인자 | 결과 |
|---|---|---|
| 정상 (declared 8 / listed 4) | `acknowledged_unread_fids=[5]` | **거절 · 발화 0줄** — "names 1 fixture id(s), but the fixture container reports 4 unse…" |
| **미판독** (경로 미응답) | `acknowledged_unread_fids=[5]` | **통과 · 발화 5줄** |

대조군 양팔: 정상 단면에서 길이 4 열거(`[5,6,7,8]`)는 양쪽 다 통과했다 —
즉 위 거절은 「이 가짜가 늘 거절한다」가 아니라 **크기 검사가 실제로 살아 있다**는 것이고,
미판독일 때만 죽는다.

`:7770` 주석은 `total is None` 을 「응답기가 childCount 를 안 줬을 때」로 설명한다.
**미판독 단면도 같은 자리로 흘러든다** — 그 두 상태가 코드에서 안 갈린다.

### 3.4 등급

**관측된 현장 사고가 아니다.** 가짜 콘솔에서 실행으로 관측한 결함이다.
다만 프로덕션 도달성은 판독으로 확인된다 — 프로덕션 포트는 실패·타임아웃에 예외를
던지고(`server/safety/console.py:670` 독스트링), `collect_rig_sections` 가 그것을 잡아
실패 단면으로 바꾼다. 즉 **한 경로의 타임아웃**이면 이 상태에 든다.
쓰기 경로이고 영향받는 것이 mutation-required 로 표시된 안전장치다.

## 4. 카드 물음 (3) — 구별 안 되는 것이 실제로 진단을 막는가

**자리마다 다르다.**

- **8자리(보존)**: 안 막는다. 섹션 이름과 사유가 문면에 있어 사람이 무엇을 볼지 안다.
- **:4734(접힘)**: 막는다. `path_not_resolved`(이 쇼파일에 이 경로가 틀렸다 → 설정을 본다)와
  `console_unreachable`(콘솔이 안 산다 → 연결을 본다)이 **둘 다 `console_read_incomplete: true,
  console_read_reason: null`** 로 나간다. `section.py` 독스트링이 「사람이 무엇을 고쳐야
  하는지가 다르다」고 명시한 바로 그 구분이 여기서 사라진다.
- **:7736 fixtures 축(거짓 긍정)**: 막는 정도가 아니라 **틀린 답을 준다.** 사람이
  「절단 아님」을 읽고 판독이 완전했다고 믿는다.

## 5. Gaps — 안 잰 것

- **실기 0건.** 전부 가짜 콘솔이다.
- **`section_refusal` 축은 프로덕션 소비자가 2자리뿐**(`group_mapper:362`,
  `preset_mapper:284`)이라 전수가 짧다. 그 둘 말고 **`collect_rig_sections` 사유를
  직접 읽는 자리**를 10자리로 셌다 — 두 축이 다른 것을 센다는 것을 표에 갈라 적었다.
- **:7736 의 fixtures 손실이 실제 쇼에서 얼마나 자주 나는지 안 쟀다.** 한 경로만
  타임아웃 나는 빈도는 이 저장소에 데이터가 없다.
- **거짓 긍정(`truncated: false`)이 하류에서 무엇을 하는지 안 쫓았다.**
  페이로드를 읽는 모델·UI 가 그 값을 어떻게 쓰는지 미측.
- **:2125 의 「통째로 직렬화」가 사유를 **읽기 좋게** 주는지는 안 봤다** — 나간다는
  것만 확인했고 사람이 그걸 찾을 수 있는지는 별개 축이다.

## 6. 판정

1. **카드의 「9자리」는 10자리다.** 내 t152 보고서의 오류가 카드로 옮겨졌다.
2. **「사유 소실」은 계열이 아니라 단일 결함이다.** 10 중 8이 보존. 설계가 아니라
   `group_mapper` 하나가 형제 `preset_mapper` 와 갈렸다.
3. **전수가 더 나쁜 것을 냈다.** `:7736` 의 fixtures 축은 사유를 잃는 데 그치지 않고
   **거짓 긍정을 내보내며 @MX:ANCHOR 안전장치의 크기 검사를 끈다.**
4. **수리는 안 했다** — 카드가 코드 변경 0 이고, 3.3 은 결정이 안전장치에 닿는다.

---

## 7. 검사와 뮤테이션 (2차 커밋에서 추가)

산출: `server/tests/test_section_refusal_reason_survives.py` (9검사 4절)

| 절 | 무엇을 잡는가 | 성격 |
|---|---|---|
| 1 | 보존 자리가 계속 사유를 낸다 (`get_rig_context` 표본) | 계약 |
| 2 | 쓰기 경로의 groups 축이 사유를 문면에 싣는다 (하류 가드 기제) | 계약 |
| 3 | 🔴 미판독 fixtures 가 「절단 아님」으로 나간다 | **실측 기록** |
| 4 | 🔴 그 손실이 @MX:ANCHOR 크기 검사를 끈다 | **실측 기록** |

3절·4절의 실패 메시지에 **「빨개지면 수리된 것이니 t163 수리 카드를 닫아라」**를 박았다
(리드 지시). 수리 카드가 열리면 이 검사가 그 카드의 완료 신호다.

### 7.1 뮤테이션 4회 — 그리고 M4 가 낸 교훈

| # | 심은 것 | 신규 검사 | 기존 스위트 |
|---|---|---|---|
| M1 | 실패 단면의 `reason` 을 `None` 으로 덮음 | 1·2절 빨강 | — |
| M2 | `_guard_pool_readable` 문면에서 사유 보간 제거 | 2절 빨강 | — |
| M3 | 미판독 fixtures 를 거절하게 고침(**수리 형태**) | 3·4절 빨강 | 🟢 **10513 전량 초록** |
| M4 | `total is None` 일 때 부족분을 `0` 으로 굳힘 | 4절 빨강 | 🔴 **1 빨강** |

🔴 **M4 가 이 카드에서 가장 값나가는 기록이다.** 처음에 나는 M4 로 「기존이 못 잡는가」를
재려 했고, 기존 검사
`test_truncate_disclosure.py::TestPartialGroupsCannotBeWrittenUnacknowledged::
test_an_unknown_total_still_requires_the_enumeration` 이 같이 빨개졌다.

**계기가 두 축을 동시에 건드렸기 때문이다.** 「응답기가 childCount 를 안 줬다」와
「단면을 아예 못 읽었다」가 코드에서 **같은 갈래**(`total is None`)로 흐른다. M4 는 그
갈래를 통째로 바꿨으므로 두 축 다 움직였고, 그러면 「기존이 미판독 축을 잡는가」를
답할 수 없다.

축을 갈라 M3(미판독 단면만 거절)로 다시 쟀다. 그때 결과가 **양쪽으로** 갈렸다:

- **unknown-total 축은 기존 검사가 지킨다** (M4 가 그것을 증명했다)
- **미판독 축은 아무도 안 지킨다** (M3 아래 10513 전량 초록)

**인접한 두 상태 중 하나만 지켜지고 있었고, 그 둘이 코드에서 안 갈리기 때문에
겉보기로는 지켜지는 것처럼 보였다.** 이것이 §3.3 결함의 뿌리이자, 그 결함이
지금까지 안 보인 이유다.

### 7.2 회귀

- 머지 전 스위트: 10504 passed, 12 skipped (신규 파일 제외 · M3 아래 10513 은
  t152 의 8검사가 이미 main 에 있기 때문)
- 신규 9검사 추가 후: 아래 8절 참조

## 8. Gaps 보강 — 검사 축에서 안 잰 것

- **1절은 표본 하나다.** 보존 8자리 중 `get_rig_context` 만 실행으로 걸었다.
  나머지 7자리는 **판독으로만** 보존을 확인했고 검사로 고정하지 않았다 —
  일곱 자리에 같은 관용구를 복사하면 검사 7개가 서로를 못 가르므로,
  전수표(1절 표)가 그 역할을 하고 이 파일은 대표 하나만 든다는 선택이다.
  **그 선택 때문에 나머지 7자리는 조용히 접힐 수 있다.**
- **`paperwork/data.py` 두 자리는 검사 0.** 판독만 했다.
- **3절·4절은 가짜 콘솔이다.** 실기에서 한 경로만 타임아웃 나는 형태를 안 만들어 봤다.
