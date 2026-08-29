# 조명감독 제공 문서 → 도구 매핑표 (t126)

> 2026-08-30. 기준 `origin/main` `03455b9`. **읽기 전용 조사다 — 콘솔 접촉 0, 코드 변경 0.**
>
> 정본 `.moai/reports/resume/2026-08-26-weekly-limit-handoff.md` §11.4 가 요구한 산출물이다.
> 그 절이 적은 전제 — 「리드가 지금 모르는 것: 감독이 제공한 문서가 무엇무엇인지 전수」 —
> 를 실측으로 닫는다.

---

## 0. 이 표가 답하는 것과 답하지 않는 것

정본 §11.3 이 남은 일의 형태를 이렇게 못박았다.

    아니다   「기능을 만든다」
    맞다     「감독이 준 문서·정보를 → 이미 있는 도구가 받을 수 있는 형태로 옮긴다」

그러므로 물음은 **어느 문서가 어느 도구에 닿는가**이고, 값이 있는 곳은 두 군데다 —
**이미 닿는 자리**(옮기기만 하면 되는 곳)와 **안 닿는 자리**(그 형태가 아직 없는 곳).
아래 §3 의 빈칸이 이 문서의 본체다.

**답하지 않는 것**: 각 도구가 콘솔에서 실제로 무엇을 남기는지. 이번 회차는 콘솔이
꺼져 있어(§6) 실기 0건이고, 도달 여부는 **코드 계약 판독**까지다.

---

## 1. 감독 제공 문서 — 전수 31개 (실측)

    git -c core.quotePath=false ls-tree -r --name-only origin/main -- src/Lighting_Designer

7개 폴더, 31개 파일. 정본 §11.4 는 「RIG 팩 CSV 4종은 확인했으나 다른 산출물이 있는지
미확인」이라고 적었는데, **실제로는 6개 폴더가 더 있다.**

| 폴더 | 파일 | 성격 |
|---|---|---|
| `01_스펙/` | `LX-SEQ-SPEC-v2.1.md` · `프로젝트-작업지침-CLAUDE.md` | 규격 정본 |
| `02_RIG팩/` | `.patch.csv` `.group.csv` `.preset-dim/col/bm/pos.csv` `.fx.csv` `.xlsx` | 쇼 단위 기본설정 |
| `03_곡파일_Sugar/` | `.cue-ex.csv` `.timeline.html` `.xlsx` | 곡 1개분 큐 |
| `04_grandMA3/` | `.ma3.txt` `.macros.xml` `.ma3-runbook.md` | 콘솔 산출물 (감독 쪽 생성분) |
| `05_문서인덱스/` | `lxseq-doc-index.html` | 문서 관계 맵 |
| `90_빌드파이프라인/` | 데이터 3 · 생성기 5 · 검증기 3 (Python) | 재생성 도구 |
| `99_플러그인/` | `lighting-designer-v0.1.1.plugin` | 감독 쪽 플러그인 |

`00_README.md` 가 문서 체계를 스스로 밝힌다 — **스펙 → RIG 팩 → 곡 파일 → 콘솔 산출물**,
아래 레이어를 고치면 위가 자동 재생성된다.

### 1.1 규격이 정의한 시트 6종

`01_스펙/LX-SEQ-SPEC-v2.1.md` §1:

| 레이어 | 시트 | 역할 |
|---|---|---|
| 연출 | `HEAD` | 곡·공연 메타, **장비 그룹 정의**, 색 팔레트 |
| 연출 | `CUE` | 큐 시퀀스 본문 — 사람이 읽는 정본 |
| 연출 | `NOTE` | 미확정 항목·변경 이력 |
| 실행 | `PATCH` | FID·기종·모드·Universe/Address·그룹 매핑 |
| 실행 | `PRESET` | 프리셋 정의 (POS/COL/BM/FX) |
| 실행 | `CUE-EX` | 큐 × 그룹별 파라미터·타이밍 — **기계가 읽는 정본** |

---

## 2. 도구 — 37종 (실측)

    server/orchestrator/tools.py:244  TOOL_NAMES

**정정**: 정본 §11.1 은 이 자리를 `tools.py:244` 로 적었으나 `server/tools.py` 는
`origin/main` 에 **존재하지 않는다**(양성 대조군으로 확인 — 그 경로에 대고 행수를
세면 무출력이다). 행 번호는 맞고 경로가 틀렸다. 실제는 `server/orchestrator/tools.py`.

개수는 37로 정본과 일치한다. 이 표에서 중요한 것은 **importer 계열이 넷뿐**이라는 것이다:

    import_lxseq_patch · import_lxseq_groups · import_lxseq_presets · import_uploaded_sheet

`import_lxseq_cues` 같은 **큐 importer 는 없다.**

---

## 3. 매핑표 — 문서 한 장이 어느 도구에 닿는가

닿음 = 그 파일 종류를 받는 도구가 등재돼 있다. 근거는 전부 코드 인용이다.

| 감독 문서 | 받는 도구 | 첨부 경로 | 판정 |
|---|---|---|---|
| `.patch.csv` | `import_lxseq_patch` → `patch_fixtures` | `kind="patch"` (registry.py:283) | 🟢 닿음 |
| `.group.csv` | `import_lxseq_groups` → `create_arrangement_groups` | `kind="group"` (registry.py:317) | 🟢 닿음 |
| `.preset-dim.csv` | `import_lxseq_presets` | `kind="preset-dim"` (registry.py:339) | 🟢 닿음 |
| `.preset-col.csv` | `import_lxseq_presets` | `kind="preset-col"` (registry.py:346) | 🟡 닿되 값 보류 |
| `.preset-bm.csv` | `import_lxseq_presets` | `kind="preset-bm"` (registry.py:353) | 🟡 닿되 값 보류 |
| `.preset-pos.csv` | **없음** | 미등재 | ⬜ 설계상 제외 |
| `.fx.csv` | **없음** | 미등재 | ❌ 빈칸 |
| `.cue-ex.csv` | **없음** | 미등재 | ❌ **빈칸 — 4단계의 실체** |
| `.xlsx` (RIG·곡) | 미확인 | 미측정 | ⬜ 안 쟀다 |
| `.ma3.txt` · `.macros.xml` | 해당 없음 | — | 감독 쪽 산출물, 입력이 아니다 |
| `01_스펙` · `05_문서인덱스` | 해당 없음 | — | 사람이 읽는 규격 |
| `90_빌드파이프라인` | 해당 없음 | — | 감독 쪽 재생성 도구 |
| `99_플러그인` | 해당 없음 | — | 감독 쪽 플러그인 |

첨부 registry 가 인식하는 종류는 여섯이다 — `patch` · `vectorworks` · `group` ·
`preset-dim` · `preset-col` · `preset-bm`. 그 목록에 `preset-pos` · `fx` · `cue-ex`
가 **없다**는 것이 위 표의 빈칸을 만든다.

### 3.1 `preset-col` · `preset-bm` 의 🟡 — 닿지만 값이 안 실린다

`import_lxseq_presets` 는 세 시트를 다 읽되 **넣을 수 있는 것만 계획하고 나머지를
`held` 에 사유 클래스와 함께 싣는다**(도구 설명 원문). 보류 사유는 닫힌 클래스로
코드에 박혀 있다 — `server/lxseq/preset_parser.py`:

    HOLD_SCALE_UNCONVERTED   col — 255 대 100. 풀 수 있으나 해석이다
    HOLD_NO_RGB_VALUE        col — 색온도만. 켈빈 모델이 저장소에 없다
    HOLD_PROBE_REJECTED      bm  — 라이브 프로브가 거절했다

같은 파일이 dim 을 이렇게 적는다 — 「세 시트 중 **해석이 0인 유일한 자리**」.
그래서 실기에서 dim 만 값이 실렸다는 기존 관측(t108)은 우연이 아니라 **이 구조의 귀결**이다.

### 3.2 `preset-pos` 의 ⬜ — 결함이 아니라 설계된 제외

`server/lxseq/preset_parser.py` 머리말이 직접 적는다:

> 세 종류의 열 집합이 서로 다르고, 넷째(`preset-pos`)까지 넣어도 쌍마다 구별된다.
> `preset-pos` 의 서명도 분기도 두지 않는다(REQ-LXSEQ3-002). 그 시트는 값 열이 없다.

**이 칸을 「빈칸」으로 읽고 채우러 가면 안 된다.** 완료된 SPEC 이 이유를 들어 뺀
자리다. 포지션은 시트에서 값을 옮기는 일이 아니라 콘솔에서 조준해 레코드하는 일이다.

### 3.3 `.fx.csv` 와 `.cue-ex.csv` 의 ❌ — 진짜 빈칸 둘

RIG 팩과 곡파일에서 **이 둘만** 받는 자리가 없다.

FX 쪽은 도구가 있으나 성격이 다르다 — `find_fx` · `instantiate_fx` · `compose_fx` 는
**어휘에서 생성**하지 시트를 읽지 않는다.

큐 쪽도 같다. `prepare_songcue` 는 `run_commands` 까지 가지만 **importer 가 아니라
generator** 이고, 도구 정의가 리그 번호·리그 구간을 넘기지 말라고 못박는다
(t68 조사분, 카드 t70 본문에 기록됨).

---

## 4. 정본 §4-1 「4단계가 무엇인가」 — 답

정본은 이 물음의 답이 **카드 t69 에 있다**고 적었다. **그 전제는 거짓이다** —
큐에 t69 가 없다. t65·t66·t67·t68·t70·t71·t72 는 있고 **t69 만 부재**다.
`moai todo done` 이 카드를 파괴한다는 기존 관측과 부합한다.

t69 없이도 답은 세 갈래 증거가 한 점으로 모인다.

| 증거 | 내용 |
|---|---|
| 카드 t70 본문 | 「SPEC-COPILOT-LXSEQ-004 작성: **곡 큐 투입** … **t69(프리셋 19)가 선행**」 |
| SPEC 번호 | `.moai/specs/` 에 LXSEQ-001·002·003 만 존재. **004 는 아직 없다** |
| 규격 §1 | 실행 레이어 3시트 = PATCH · PRESET · **CUE-EX**. 앞 둘은 이미 닿는다 |

    1단계  패치     patch.csv     → import_lxseq_patch      LXSEQ-001  implemented
    2단계  그룹     group.csv     → import_lxseq_groups     LXSEQ-002  코드 머지
    3단계  프리셋   preset-*.csv  → import_lxseq_presets    LXSEQ-003  본체 증명됨
    4단계  곡 큐    cue-ex.csv    → (없음)                  LXSEQ-004  미작성

**판정: 4단계는 「곡 큐 투입 — `cue-ex.csv` 를 읽어 콘솔 큐로 넣는 importer」다.**

**증거 등급**: 이것은 추론이다. 네 단계를 1:1 로 적어 놓은 표를 어디서도 읽지
못했고, 위 세 증거의 수렴으로 도출했다. 감독 확인을 받기 전까지 확정으로 쓰지 말 것.

---

## 5. 안 잰 것

- **`.xlsx` 경로.** RIG 팩과 곡파일 둘 다 xlsx 본체가 있으나 첨부 registry 가 이를
  어떻게 분류하는지 안 쟀다. CSV 는 xlsx 에서 뽑은 파생물이므로, xlsx 를 직접 받는
  길이 있으면 매핑이 한 칸씩 당겨질 수 있다
- **`04_grandMA3/*.ma3.txt` 452줄.** 감독 산출물이지 입력이 아니라고 판정했으나,
  `run_commands` 로 그대로 흘릴 수 있는지는 안 쟀다. 만약 된다면 4단계의 **다른 답**이다
- **`99_플러그인/lighting-designer-v0.1.1.plugin`** 의 내용. 이 앱과 겹치는지 미측정
- **도달 가능성 전부.** 이 표는 「등재돼 있는가」를 답하지 「실제로 콘솔에 남는가」는
  안 답한다. 콘솔이 꺼져 있었다(§6)
- **`preset_parser.py` 의 범위 밖 목록에 `Position` 이 든 것**과 §3.2 의 `preset-pos`
  제외가 같은 결정인지 다른 결정인지 안 쟀다

---

## 6. 측정 조건

    origin/main       03455b9
    트리              .claude/worktrees/t126  (WT-doc-tool-map, origin/main 기준 신규)
    콘솔              app_gma3 미기동 — 프로세스 조회 무출력
    콘솔 쓰기         0건
    코드 변경         0행

콘솔이 꺼져 있으므로 이 회차의 모든 판정은 **코드 판독**이며 실기 귀속이 없다.
