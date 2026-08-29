# fx.csv · cue-ex.csv 어댑터 설계 조사 (t127)

> 2026-08-30. 기준 `origin/main` `5d31690`. 리드 배차분.
> **조사와 설계까지다 — 코드 0행, 콘솔 접촉 0.**
>
> 선행: `.moai/reports/t126/doc-tool-map.md` 가 이 둘을 매핑표의 빈칸으로 지목했다.

---

## 0. 결론 먼저

**새 층은 0개다. 어댑터 둘이고, 둘의 모양이 서로 다르다.**

| | `cue-ex.csv` | `fx.csv` |
|---|---|---|
| 모양 | importer — `import_lxseq_presets` 와 같은 계열 | importer**이되 절반 이상이 거절**되는 형태 |
| 전량 | 89행 / 18큐 / 13그룹 | 8행 |
| 실을 수 있는 몫 | 미측정 (§4.3) | **8행 중 5행** — 나머지 셋은 어휘가 없다 |
| 선행 | `fx.csv` (FX 열이 FX.01~FX.08 을 참조한다) | 없음 |

**핵심 판정: 이 둘의 부재는 「도구를 덜 만들었다」가 아니라 SPEC 넷이 의도적으로
그은 선의 반대편에 있다.** FXLIB·SCENE 은 **어휘에서 생성**하는 계층이고, 두 CSV 는
**구체 인스턴스 값**을 나른다. 그래서 `compile_scene` 이나 `prepare_songcue` 를
확장하는 처방은 틀렸다 — 그 확장은 두 SPEC 이 명시로 금지한 「엔트리 발명」이 된다.

옳은 처방은 LXSEQ-001·002·003 이 이미 세 번 반복한 형태다: **생성기 도구를 건드리지
않고, 시트를 읽어 명령을 만드는 importer 를 나란히 놓는다.**

---

## 1. 읽은 SPEC 넷이 이미 정한 것 (착수 1번, `spec:` 규율)

| SPEC | 상태 | 이 조사에 거는 제약 |
|---|---|---|
| `FXGEN-001` | completed | `compose_fx` 도 **라이브러리 엔트리와 동일한 `Fx` 스키마 검증**을 통과해야 한다. 우회 경로는 없다 (REQ-FXGEN-007) |
| `FXLIB-001` | completed | FX 어휘는 폐쇄 집합이다. **효과는 기계로 확인 불가**이며 리포트에 무조건 명시한다 |
| `SCENE-001` | completed | 씬은 **새 어휘를 만들지 않는다.** `look_id`/`fx_id` 는 **실존 엔트리로만** 해석하고 미등재 id 는 명시 에러 (REQ-SCENE-002) |
| `SONGCUE-001` | completed | `prepare_songcue` 는 곡 구조에서 **생성**한다. 도구 정의가 리그 번호·리그 구간을 넘기지 말라고 못박는다 |

이 넷이 공통으로 세운 규율 하나가 이번 설계의 전부를 결정한다.

> **리터럴 발명은 금지된다.** 자연어가 미측정 문법을 요구하면 **거부와 사유 보고가
> 정답이지 근사 조립이 아니다.** (REQ-FXGEN-008)

그러므로 어댑터의 성공 기준은 **「전부 실었다」가 아니라 「실은 것과 거절한 것을
사유와 함께 갈라 보고했다」**이다. 이 형태는 이미 출하돼 있다 —
`import_lxseq_presets` 의 `held` + 닫힌 사유 클래스가 그것이다.

---

## 2. `fx.csv` — 거리 측정 (8행 전량)

시트 열: `ID, Name, Attribute, WaveSteps, BaseRate, Width, Phase, Note`

스키마(`server/fx/schema.py`)가 받는 어휘:

    KNOWN_ATTRIBUTES = Dimmer · ColorRGB_R · ColorRGB_G · ColorRGB_B · Pan · Tilt
    PATTERN_KINDS    = sweep · wave · circle · diagonal · pulse · chase
    MIN_STEPS = 2 · PHASE -360..360 · PERCENT 0..100 · WIDTH 0..100
    SPEED_MASTER 1..16 · CURVE -100..100

### 2.1 행별 판정

| 행 | Attribute | 스키마 | 판정 |
|---|---|---|---|
| FX.01 DIM-CHASE | Dimmer | ✅ | 🟢 매핑 가능 |
| FX.02 DIM-PULSE | Dimmer | ✅ | 🟢 매핑 가능 |
| FX.03 DIM-BREATHE | Dimmer | ✅ | 🟢 매핑 가능 |
| FX.04 COL-RAINBOW | **Hue** | ❌ 부재 | ❌ 어휘 없음 — 스키마는 `ColorRGB_*` 3채널이지 Hue 축이 아니다 |
| FX.05 TILT-SWEEP | Tilt | ✅ | 🟢 매핑 가능 |
| FX.06 SHUTTER-STROBE | **Shutter** | ❌ 부재 | ❌ 어휘 없음 — **라이브 프로브가 이미 거절한 속성**이다 |
| FX.07 DIM-TWINKLE | Dimmer | ✅ | 🟡 속성은 되나 패턴이 `Random` — `PATTERN_KINDS` 에 없다 |
| FX.08 PT-CIRCLE | **Pan+Tilt** | 분해 필요 | 🟡 한 행이 두 속성 — 스키마는 Pan·Tilt 를 따로 든다 |

**5/8 이 속성 축에서 통과한다.** FX.04·FX.06 은 어휘 부재로 원리적 불가이고,
FX.07·FX.08 은 결정이 필요한 자리다.

### 2.2 값 문법이 산문이다 — 진짜 비용은 여기다

속성보다 값 쪽이 멀다. 시트의 값은 사람이 읽는 서술이다.

    WaveSteps   "2-step 100/0" · "Sine 100↔60" · "Ramp 0→360°" · "Sine ±25°"
                "Strobe" · "Random 100↔30" · "Circle Ø소"
    BaseRate    "240 (@1/8)" · "120 (@1beat)" · "30 (@1bar)" · "15 (@2bar)"
    Width       "50%" · "—"
    Phase       "0..360" · "0" · "random"

세 자리가 결정을 요구한다.

- **`BaseRate` 는 값이 둘이다** — 숫자(240)와 음표 단위(@1/8). 스키마의
  `speed` · `speed_master` · `measure` 중 어디로 가는지 자명하지 않다.
  `measure` 는 비트 수인데 `@1/8` 은 음표 분할이라 같은 축이 아니다
- **`Phase` 의 `0..360` 은 한 값이 아니라 픽스처 간 확산 범위다.** 스키마의
  `PHASE` 는 단일 값 축이다. 확산은 다른 축(위상 확산)이고 그 대응이 미측정이다
- **`Phase` 의 `random`** 과 **`WaveSteps` 의 `Random`** 은 스키마에 표현이 없다

**REQ-FXGEN-008 이 이 자리들을 결정한다 — 근사 조립이 아니라 거절이 정답이다.**
그러므로 fx 어댑터의 v1 은 **5행을 계획하고 3행을 사유와 함께 보류하는 것**이
목표이지, 8행을 다 싣는 것이 목표가 아니다.

---

## 3. `cue-ex.csv` — 거리 측정 (89행 전량)

시트 열: `Q#, Group, Dim, COL, POS, BM, FX, FX-Rate, FX-Phase, FX-Width,
I-Fade, I-Delay, P-Fade, C-Fade, B-Fade, Snap, Note`

규격 §1 이 이 시트를 **「기계가 읽는 정본」**이라고 못박는다. 실제로 값 문법이
`fx.csv` 와 전혀 다르다 — 산문이 아니라 참조와 수치다.

### 3.1 실측 분포

    행        89
    큐        18 (Q# distinct)
    그룹      13 — ALL · BACK · BLIND · HAZE · KEY · LED-W · MOVER-D · MOVER-U
                   SIDE-L · SIDE-R · STROBE · WASH-D · WASH-U
    FX 열     빈칸 42 · OFF 17 · FX 참조 30

### 3.2 FX 참조 30건의 내역 — fx.csv 가 선행인 이유

| FX id | 건수 | fx.csv §2.1 판정 |
|---|---|---|
| FX.01 | 8 | 🟢 |
| FX.08 | 5 | 🟡 분해 필요 |
| FX.03 | 5 | 🟢 |
| FX.05 | 4 | 🟢 |
| FX.02 | 4 | 🟢 |
| FX.04 | 2 | ❌ 어휘 없음 |
| FX.07 | 1 | 🟡 패턴 없음 |
| FX.06 | 1 | ❌ 어휘 없음 |

**FX 참조 30건의 검산: 🟢 21건**(FX.01 8 + FX.03 5 + FX.05 4 + FX.02 4)
**· 🟡 6건**(FX.08 5 + FX.07 1) **· ❌ 3건**(FX.04 2 + FX.06 1) **= 30.**
곧장 닿는 것은 21건이고, 6건은 결정 대기, 3건은 어휘 부재로 막힌다. `cue-ex` 어댑터는 `fx.csv` 어댑터의 판정을 그대로 물려받으므로,
**fx 가 선행이고 cue-ex 가 후행이다.**

`OFF` 17건은 별도 축이다 — 「이펙트를 끈다」의 스키마 표현이 무엇인지 이 조사에서
찾지 못했다. §5 에 미측정으로 남긴다.

### 3.3 왜 `compile_scene` 도 `prepare_songcue` 도 이것을 못 받는가

둘 다 도구 정의를 읽었고, 둘 다 구조적으로 이 시트의 입구가 아니다.

- **`compile_scene`** 은 `find_scene` 이 고른 **`scene_id`** 와 그리그가 나열한
  **그룹 번호**를 받아 **시퀀스 1개 · 큐 1개**를 만든다. `cue-ex.csv` 는 18개 큐를
  나르고, 참조하는 것은 scene id 가 아니라 `COL.01` · `POS.03` 같은 **프리셋 id** 다
- **`prepare_songcue`** 는 `song_title` · `genre` · `sections` 를 받아 **곡 구조에서
  생성**한다. 도구 정의가 리그 번호·리그 구간을 넘기지 말라고 직접 금지한다

즉 두 도구는 **어휘에서 만드는 쪽**이고 이 시트는 **이미 정해진 값을 나르는 쪽**이다.
확장이 아니라 나란한 importer 가 맞는 형태이며, 그것이 LXSEQ-001·002·003 의 형태다.

### 3.4 이미 있는 재료 — 그룹 이름 해석

13개 그룹은 번호가 아니라 **이름**이다. 이름을 리그의 그룹으로 해석하는 매퍼가
저장소에 이미 있다 — `server/lxseq/group_mapper.py`. 새로 짓지 말 것.

---

## 4. 설계 — 어댑터 둘, 전부 기존 것을 잇는다

### 4.1 공통 골격 — 이미 세 번 출하된 형태를 그대로 쓴다

`import_lxseq_patch` · `import_lxseq_groups` · `import_lxseq_presets` 가 공유하는
형태이고, 넷째·다섯째도 같아야 한다.

    1. 바이트는 파일에서만 온다 (채팅 붙여넣기 base64 금지)
    2. 기본 action 은 preview — 콘솔에 아무것도 쓰지 않는다
    3. 전부 읽되 넣을 수 있는 것만 계획하고, 나머지를 held 에 사유 클래스와 함께
    4. 쓰기는 기존 단일 초크포인트(run_commands → gate)에 위임
    5. 풀·슬롯이 어긋나면 아무것도 만들지 않고 대조표를 낸다 (부분 계획 금지)
    6. 첨부 registry 에 kind 를 등재 — 그래야 첨부 버튼 경로가 열린다

6번이 t126 이 찾은 빈칸의 실체다. registry 가 받는 종류는 지금 여섯이고
`fx` · `cue-ex` 가 거기 없다.

### 4.2 새 층은 몇 개인가 — 0개

| 필요한 것 | 이미 있는가 |
|---|---|
| 시트 파싱 골격 | ✅ `server/lxseq/preset_parser.py` 계열 |
| 그룹 이름 → 번호 | ✅ `server/lxseq/group_mapper.py` |
| FX 스키마·검증 | ✅ `server/fx/schema.py` |
| 명령 조립 | ✅ FXLIB/FXGEN 의 스텝 열 규율 |
| 실행 경로 | ✅ `run_commands` 단일 초크포인트 |
| 보류 사유 클래스 | ✅ `import_lxseq_presets` 의 `held` 선례 |
| 첨부 배선 | ✅ `server/sheets/registry.py` — 행 추가뿐 |

**전부 있다.** 새로 쓰는 것은 두 파서와 두 매퍼, 그리고 registry 두 행이다.

### 4.3 착수 순서

    1단계  fx 어댑터    8행 중 5행 계획 · 3행 보류. 사유 클래스를 먼저 닫는다
    2단계  cue-ex 어댑터  fx 판정을 물려받는다. 18큐 · 13그룹 · OFF 축 결정 필요

**cue-ex 가 실제로 몇 행을 실을 수 있는지는 이 조사에서 재지 않았다.** FX 열만
분류했고, `Dim` · `COL` · `POS` · `BM` 열과 5종 페이드 열은 각각 별도 판정이 필요하다.
그 판정 없이 「89행이 닿는다」고 적으면 §2 에서 fx.csv 가 보여준 것과 같은 함정에
빠진다 — **속성이 통과한다고 값이 통과하는 것이 아니다.**

---

## 5. 안 잰 것 — 다음 세션이 검증된 것으로 물려받지 말 것

- **`cue-ex.csv` 의 `Dim` · `COL` · `POS` · `BM` 열이 실제로 닿는지.** FX 열만 분류했다.
  `COL.01` · `POS.03` 은 프리셋 id 인데, t126 이 잰 대로 `preset-pos` 는 애초에
  importer 가 없다 — POS 참조가 무엇에 해결되는지 **미측정**이다
- **5종 페이드 열**(`I-Fade` · `I-Delay` · `P-Fade` · `C-Fade` · `B-Fade`)과 `Snap` 의
  스키마 대응. 하나도 안 봤다
- **`OFF` 17건의 표현.** 이펙트를 끄는 명령 형태를 찾지 못했다
- **`BaseRate` 의 `@1/8` 음표 단위**가 `speed` · `speed_master` · `measure` 중
  어디로 가는지. 자명하지 않고, 틀리면 무음 실패다
- **`Phase` 의 `0..360` 확산 축**이 스키마의 단일 `PHASE` 와 어떻게 다른지
- **13개 그룹 이름이 지금 리그에서 해결되는지.** 매퍼의 존재만 확인했고
  **실행은 0회**다. 리드 보고에 따르면 지금 콘솔은 기본 쇼파일이라 RIG 팩 이름이
  하나도 없다 — 그렇다면 13개 전부 미해결일 수 있다 (이 세션은 콘솔을 안 만졌다)
- **실기 전량.** 이 조사는 시트 판독과 코드 판독뿐이다

---

## 6. 측정 조건

    origin/main   5d31690
    트리          .claude/worktrees/t127 (WT-fx-cue-adapter, origin/main 기준 신규)
    콘솔          이 세션은 만지지 않았다 — 쓰기 0, 판독 0
    코드 변경     0행
    읽은 SPEC     FXGEN-001 · FXLIB-001 · SCENE-001 · SONGCUE-001 (넷 다 completed)

시트 두 장은 이 워크트리의 작업 사본에서 읽었다(트리가 `5d31690` 체크아웃이므로 내용은 origin/main 과 같으나, 해시 대조는 하지 않았다). `.csv` 두 장 모두 선두에 BOM 이
있다 — 파서를 쓸 때 첫 열 이름이 조용히 깨지는 자리다.
