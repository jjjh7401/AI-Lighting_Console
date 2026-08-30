# t155 — 한 행이 시트 전체를 세운다. 설계이고, 문면에 그 축이 없었다

- 카드: t155 · SPEC-COPILOT-LXSEQ-003 · 기준 `ac761f1` · 브랜치 `WT-within-sheet-mixed`
- **콘솔 접촉 0 · 프로덕션 코드 변경 0.** 순수 함수 + 인메모리 포트로만 쟀다.

## 0. 답 세 줄

1. **한 행이 나머지를 죽인다** — 실측. planned 6행 중 하나만 번역 불가로 만들었더니 **발화 총계 0**.
2. **결함이 아니라 설계다** — `REQ-LXSEQ3-008`·acceptance 축 ②의 「부분 계획 금지」의 적용 단계 판.
3. 🔴 **그런데 그 문면이 이 축을 안 덮는다** — REQ 는 **매퍼**와 **풀·슬롯 어긋남**만 묶는다.

## 1. 실측 — 주석을 증거로 쓰지 않았다

카드가 「주석의 『같은 술어를 쓴다』를 증거로 쓰지 마라」고 했다. 값을 실제로 만들어
소비 루프를 돌렸다.

### 1.1 섞인 계획을 만들어 관찰

`_lxseq_preset_apply_command` 를 패치해 **DIM.LOW 한 행만** `None` 을 내게 하고
정본 dim 시트를 `action="apply"` 로 dispatch:

    대조군(패치 없음)         planned 6 · 적용 줄 6 · refusal null
    한 행만 번역 불가로 패치   planned 6 · **발화 총계 0** · refusal apply_untranslatable
                             untranslatable = [dict(preset_id="DIM.LOW", kind="preset-dim")]

**여섯 행이 계획에 올랐는데 한 행 때문에 여섯 다 안 나갔다.** 「그 행만 빠진다」가 아니다.

재현:

```python
real = tools_module._lxseq_preset_apply_command
def one_row_untranslatable(placement):
    return None if placement.preset_id == "DIM.LOW" else real(placement)
# tools_module._lxseq_preset_apply_command 를 위 함수로 바꾸고 dim 시트를 apply 로 dispatch
```

### 1.2 오늘 자연히 도달하는가 — 퍼즈로 쟀다

「판정 통과 · 판독 실패」인 값이 실제로 있는지 찾았다. 체계 코퍼스 + 난수 퍼즈:

| 종류 | 판정 | 판독 | 값 수 | 판정 통과 | **어긋남** |
|---|---|---|---|---|---|
| dim | `classify_storability` | `dim_level_percent` | 20,106 | 79 | **0** |
| col | `classify_storability` | `col_rgb_percents` | 22,849 | 1,365 | **0** |
| 합 | | | 42,955 | **1,444** | **0** |

🔴 **0을 그냥 안 믿었다 — 날조 대조군을 먼저 쐈다.** `col_rgb_percents` 를 특정 값에서만
`None` 을 내게 패치하니 퍼저가 「판정 True · 판독 False」를 **검출했다**. 그러니 위 0은
「없다」이지 「안 보인다」가 아니다. 패치 복원도 확인했다.

bm 은 5행 전부 보류라 `planned` 에 안 오른다(t153 실측). 그러므로 **오늘 자연히 섞인
계획은 만들어지지 않는다** — 이 축은 미래를 위한 가드다.

## 2. 설계인가 결함인가 — 설계다

같은 태도가 이 SPEC 에 **명시돼 있다**:

    spec.md:291   REQ-LXSEQ3-008  the 매퍼 shall not 부분 계획을 낸다 — 0건을 내고 대조표를 보고한다
    acceptance.md:13  축 ②  「부분 계획이 최악이다. 반쯤 맞는 프리셋이 쇼파일에 남고,
                              다음 단계(큐)가 그것을 참조한다」
    plan.md:107   「부분 계획 금지. 어긋나면 0건」

근거도 같다 — t108 C1: 적용 줄 없이 저장 줄만 나가면 그 순간의 프로그래머 상태가 그
이름으로 영속하고, 슬롯 점유만 되읽히므로 **아무도 틀린 것을 못 본다.**

## 3. 🔴 그러나 문면이 이 축을 안 덮는다 (카드가 요구한 산출물)

| | REQ-LXSEQ3-008 | 실측한 축 |
|---|---|---|
| 주어 | **매퍼** | 툴 층의 **소비 루프** |
| 조건 | 풀·슬롯 측정 불완전 / 시트 기대 어긋남 | **값을 명령으로 못 옮김** |
| 단계 | 계획 | **적용** |

**세 칸이 다 다르다.** 즉 이 성질은 지금 **런타임 거절 문면**(`refusal_detail` 의
「…한 줄도 보내지 않았다」)과 **코드 주석**에만 있고, 요구사항·수용기준에는 없다.

처분: `preset-unify-design.md` **§6.2** 를 신설해 축과 실측을 적었고, REQ 가 이것을
덮지 않는다는 사실도 같이 적었다. **요구사항 승격은 SPEC 본문 소유자 판단**이라
안 했다 — gap 으로 남긴다.

## 4. 낸 것

| 자리 | 무엇 |
|---|---|
| `server/tests/test_lxseq_preset_value_path.py` | `TestOneUntranslatableRowStopsTheWholeSheet` — 섞인 계획 검사 + 대조군 |
| `.moai/specs/SPEC-COPILOT-LXSEQ-003/preset-unify-design.md` §6.2 | 축 · 실측 · REQ 미포함 사실 |

기존 검사(`test_nothing_fires_when_the_attribute_table_has_no_entry`)는 표를 **통째로**
비워 **전부** 번역 불가인 계획만 잰다 — 「한 행만 불가일 때 나머지는」이 안 갈렸다.
그 자리를 열었다.

## 5. 검증

    전체 스위트  10504 passed, 12 skipped, exit 0
                (기준 ac761f1 는 10502 — 추가한 검사 2개와 정확히 일치)
    ruff check server/  -> All checks passed!

### 5.1 뮤테이션 2/2 KILLED

| # | 뒤집은 것 | 결과 |
|---|---|---|
| M1 | `tools.py` 의 `if untranslatable:` → `if False:` (fail-closed 를 끔) | **KILLED** — 새 검사 + 기존 형제 검사 둘 다 빨강 |
| M2 | `LXSEQ_PRESET_APPLY_ATTRIBUTE` 를 빈 dict 로 (대조군이 공허한지) | **KILLED** — 대조군 검사가 빨강 |

M2 가 중요하다: 대조군이 「이 시트는 원래 안 나간다」와 구분되지 않으면 본 검사가
무엇을 지키는지 안 읽힌다. 복원은 체크섬 대조(`bee85d72…3733`), `git status` 빈 출력.

## 6. 안 잰 것

1. **`preset-pos` 축** — 헤더에 값 열이 없어 파서가 종류로 안 받는다. 그 경로에서
   섞임이 가능한지는 안 봤다.
2. **col 의 `_RGB_TRIPLE` 이 못 잡는 표기** — 퍼즈 알파벳을 `0-9 R G B 공백 . / % ~ - + , K`
   로 한정했다. 그 밖 문자(전각 숫자, 유니코드 공백 등)로 판정만 통과하는 값이 있는지는
   안 쟀다. 대조군이 검출력을 보였으니 코퍼스를 넓히면 답이 나온다.
3. **번역 불가가 값이 아니라 종류에서 오는 경우의 자연 발생** — bm 이 planned 에 오르는
   날(t149 이후)이 그것이고, 그때는 시트 전체가 bm 이라 「나머지」가 없다. 종류를
   가로지르는 전파는 t154 가 이미 부정했다(한 임포트 = 한 시트 = 한 종류).
4. **요구사항 승격 여부** — SPEC 본문 소유권 밖이라 안 건드렸다.
