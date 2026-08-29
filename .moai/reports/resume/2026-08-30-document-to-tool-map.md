# 조명감독 문서 → 도구 매핑표 — 2026-08-30

> 재개 문서 §11.4 가 요구한 산출물. 기준 `origin/main` `5c1326f`.
> **이 표가 남은 작업의 실체다** — 기능을 만드는 것이 아니라 문서를 이미 있는
> 도구가 받을 형태로 옮기는 일이다.

## 1. 조명감독이 제공하는 문서 — 전수 (실측)

`src/Lighting_Designer/` 트리, 빌드 파이프라인 제외:

| 폴더 | 파일 | 무엇 |
|---|---|---|
| `00_README.md` | 1 | 개요 |
| `01_스펙/` | `LX-SEQ-SPEC-v2.1.md` · `프로젝트-작업지침-CLAUDE.md` | 규약 |
| `02_RIG팩/` | `patch` · `group` · `fx` · `preset-dim` · `preset-col` · `preset-bm` · `preset-pos` (+`.xlsx`) | **리그 정의 7종** |
| `03_곡파일_Sugar/` | `cue-ex.csv` · `timeline.html` (+`.xlsx`) | **곡별 큐시트** |
| `04_grandMA3/` | `ma3-runbook.md` · `ma3.txt` · `macros.xml` | 콘솔 인계물 |
| `05_문서인덱스/` | `lxseq-doc-index.html` | 색인 |
| `99_플러그인/` | `lighting-designer-v0.1.1.plugin` | 감독 플러그인 |

🔴 **리드가 종일 본 것은 `02_RIG팩/` 의 preset 3종뿐이었다.** `03_곡파일` 과
`04_grandMA3` 는 **한 번도 안 열었다.** 그런데 큐·시퀀스 축의 재료가 거기 있다.

## 2. 매핑표 — 문서가 어느 도구로 가는가

| 문서 | 내용 (실측) | 받을 도구 | 상태 |
|---|---|---|---|
| `patch.csv` | 픽스처 패치 | `import_lxseq_patch` → `patch_fixtures` | ✅ 경로 있음 (LXSEQ-001 implemented) |
| `group.csv` | **18행** — `ALL`·`KEY`·`FOH`·`BACK`·`SIDE-L`… + Members + Purpose | `import_lxseq_groups` → `create_arrangement_groups` | 🟡 코드 있음, M4 미성립 |
| `preset-dim.csv` | 6행, 퍼센트 | `import_lxseq_presets` | ✅ **값까지 실기 증명**(t114) |
| `preset-col.csv` | 8행, RGB 6 + 켈빈 2 | 〃 | ⏸️ 감독이 hold |
| `preset-bm.csv` | 5행, **값이 산문** | 〃 | ⏸️ 파서 없음 |
| `preset-pos.csv` | 8행, 값 열 없음 | — | 의도적 제외 (REQ-LXSEQ3-002) |
| **`fx.csv`** | **7행** — `DIM-CHASE`·`DIM-PULSE`·`COL-RAINBOW`·`TILT-SWEEP`·`SHUTTER-STROBE`… + Attribute/WaveSteps/BaseRate/Width/Phase | **`find_fx` · `instantiate_fx` · `compose_fx`** | ❓ **경로 미확인** |
| **`cue-ex.csv`** | **89행 / 큐 18개** — `Q#`·`Group`·`Dim`·`COL`·`POS`·`BM`·`FX`·`FX-Rate`·`FX-Phase`·`I-Fade`·`C-Fade`·`Snap`·`Note` | **`prepare_songcue` · `compile_scene` · `build_cue_sheet`** | ❓ **경로 미확인** |
| `timeline.html` | 곡 구조 시각화 | (참고용) | — |
| `ma3-runbook.md` | 콘솔 작업 순서 | (사람이 읽는 것) | — |
| `macros.xml` | MA3 매크로 | (콘솔 직접 임포트) | — |

## 3. 🔴 가장 큰 발견 — 두 문서가 도구에 안 이어져 있을 수 있다

`fx.csv` 와 `cue-ex.csv` 는 **완전한 형태의 재료**인데, 이것을 받는 임포트 경로가
있는지 **미확인**이다. `import_lxseq_*` 는 patch·groups·presets 셋뿐이다.

    확인해야 할 것
      1) sheets/registry.py 에 fx · cue 행이 있는가
      2) prepare_songcue 가 이 CSV 형식을 받는가, 아니면 다른 입력을 받는가
      3) compile_scene 의 입력 형태는 무엇인가

**있으면 배선만 하면 되고, 없으면 그것이 진짜 남은 작업이다.**
어느 쪽이든 **먼저 재고 나서** 판단한다 — 없다고 단정하고 만들기 시작하면
오늘까지 여덟 번 반복한 그 실수다.

## 4. cue-ex.csv 의 구조 — 시퀀스·큐 축의 재료

    Q010  BACK    Dim 55  COL.01  POS.03         I-Fade 0.0  Snap Y
    Q010  WASH-U  Dim 55  COL.01                 I-Fade 0.0  Snap Y
    Q010  HAZE    Dim 40                         [MANUAL] 30초 전 선투입
    Q020  KEY     Dim 70  COL.02  POS.01         I-Fade 1.5  "보컬 페이스 확보"
    Q030  SIDE-L  Dim 40  COL.06         FX.02   Rate 15  Phase 0..360  "@2bar 얕게"

한 큐가 **여러 행**(그룹별)으로 펼쳐지고, 각 행이 **프리셋 ID 를 참조**한다
(`COL.01` · `POS.03` · `BM.02` · `FX.02`). 즉 **프리셋이 먼저 콘솔에 있어야
큐가 그것을 가리킬 수 있다** — 순서 의존이 문서 구조에 박혀 있다.

    patch → group → preset → fx → cue     ← 이 순서가 문서에서 읽힌다

## 5. 다음 세션의 첫 작업

    1. sheets/registry.py 를 읽어 fx · cue 행 유무를 잰다   ← 코드 읽기, 콘솔 무관
    2. prepare_songcue · compile_scene 의 입력 형태를 읽는다
    3. 그 결과로 §3 의 갈래가 정해진다 — 배선이냐 신규냐
    4. onPC 가 켜지면 실기

**onPC 는 지금 꺼져 있다**(2026-08-30 실측 — 프로세스 0, UDP 9005 점유 0).
1~3 은 콘솔 없이 할 수 있다.

---

## 6. §3 을 쟀다 (2026-08-30, 콘솔 무관 — 코드 읽기)

### 6.1 시트 레지스트리에 fx · cue 행이 **없다**

`server/sheets/registry.py` 의 등록 종류 **6개** (실측):

    patch · vectorworks · group · preset-dim · preset-col · preset-bm

**`fx` 없음. `cue` 없음.** 즉 `fx.csv` 와 `cue-ex.csv` 는 업로드 판별기가
`unknown_sheet_kind` 로 거절한다 — 임포트 입구 자체가 없다.

### 6.2 `prepare_songcue` 는 CSV 를 안 받는다

`tools.py:2397` 의 인자:

    song_title        문자열
    genre             운영자 자신의 단어
    timecode_number   양의 정수
    sections          곡 구조 배열 (비어 있으면 거절)
    explicit_dynamics …

**곡 구조를 대화로 받는 도구**이지 큐시트 CSV 를 읽는 도구가 아니다.
`cue-ex.csv` 의 89행(큐 18개 × 그룹별 행)을 이 인자에 넣을 자리가 없다.

### 6.3 그래서 갈래가 정해졌다 — **신규다, 배선이 아니다**

    fx.csv     → 받을 입구 없음. 레지스트리 행 + 파서 + 매퍼가 필요하다
    cue-ex.csv → 받을 입구 없음. 같다

**다만 「기능이 없다」가 아니다.** FX 를 만드는 도구(`instantiate_fx`·`compose_fx`)와
큐를 만드는 도구(`compile_scene`·`build_cue_sheet`)는 **이미 있고 실전 테스트를
거쳤다.** 없는 것은 **CSV → 그 도구들** 사이의 어댑터다.

이것이 LXSEQ-001·002·003 이 patch·group·preset 에 대해 한 일과 **정확히 같은 형태**다:

    LXSEQ-001  patch.csv  → patch_fixtures              (다리 놓기, 엔진 신설 0)
    LXSEQ-002  group.csv  → create_arrangement_groups   (같음)
    LXSEQ-003  preset.csv → run_commands                (같음)
    ???        fx.csv     → instantiate_fx              ← 없다
    ???        cue-ex.csv → compile_scene               ← 없다

### 6.4 다음 세션의 결정 — 감독께 물을 것

**cue-ex.csv 가 4단계인가?** 재개 문서 §1 이 「4단계 중 3단계」라 적고 4단계 정의를
미확인으로 남겼는데, 문서 구조가 답을 시사한다:

    patch → group → preset → **fx → cue**
    1단계   2단계   3단계     ???

`cue-ex.csv` 는 곡별 산출물이고(`03_곡파일_Sugar/`), 나머지 셋은 리그 산출물이다
(`02_RIG팩/`). **리그를 다 잡은 뒤 곡을 얹는 순서**가 문서 구조 자체에 있다.

⚠️ 이건 **문서 배치에서 읽은 추론**이지 t69 를 확인한 것이 아니다. 감독 확인 필요.
