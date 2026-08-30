# 미측정 4축 실측 — CUE 정합 · 실기 그룹 · 프리셋 풀 · BM 속성표

> 2026-08-30. 기준 `origin/main` `576e73f`. 트리 `.claude/worktrees/cue-ex-parity`.
> 선행: 같은 폴더 `column-census.md` §5 가 이 축들을 **미측정**으로 남겼다.
> 콘솔 **판독만** — 쓰기 0. 코드 변경 0행.

---

## 0. 결론 먼저

| # | 축 | 판정 |
|---|---|---|
| ① | CUE 시트 ↔ cue-ex 정합 | **18/18 일치** — 어긋남 0. 단 술어를 4단계까지 정밀화해야 나온다 |
| ② | `group_mapper` 13개 이름의 실기 해결 | **12/13 해결** · 이름·슬롯 완전 일치 · `LED-W` 만 부재 |
| ③ | 콘솔 프리셋 풀의 현재 이름 | 🔴 **Color 0건 · Position 0건 · Beam 0건 · Dimmer 7건** |
| ④ | `BM` 산문을 옮길 픽스처 속성표 | **있다** — `server/looks/schema.py`. 다만 4속성 중 `Zoom` 하나만 통과 |

**그리고 아무도 묻지 않은 것 둘이 나왔다** — 실기 응답기가 **1.6.2** 이고(§1),
`xlsx` 안에 `CUE-EX` 시트가 따로 있는데 `.csv` 와 **셀 차이 0건**이다(§2.3).

---

## 1. 🔴 측정 조건이 기록과 다르다 — 응답기는 1.6.2다

    responder_roundtrip --listen-port 9005 --skip-exec
      -> live version=1.6.2  plugin=CopilotResponder   result: PASS

저장소 기록과 어긋난다. `.moai/reports/t96/reimport-recheck-20260830.md` 는 같은 날
같은 PID(38706) 에서 **1.6.1** 을 쟀고, 메모리도 「실기 1.6.1 · main 은 1.6.2」로 적혀 있다.
PID 가 같으므로 프로세스 교체가 아니라 **플러그인 재적재**로 보이지만, 누가 언제
다시 올렸는지는 **안 쟀다**(§5).

이 한 줄이 두 가지를 바꾼다:

- `introspect_probe --all-pages` 가 이제 안전하다. 「낡은 응답기에 `--all-pages` 는
  무한 루프」라는 경고는 1.6.1 조건의 것이다
- 카드 `t131` 의 전제(「실기가 1.6.1 이라 페이징이 없다」)는 **만료됐다**.
  다만 t131 의 본체 주장(프로덕션 호출부에 페이징 루프가 없다)은 이 판독이
  건드리지 않았다 — 소스 축은 그대로다

계기 검증: 음성 대조군을 먼저 쐈다.

    introspect_probe --path 'DataPool/ZZZNoSuchPoolXYZ' --listen-port 9005
      -> introspect failed: path segment not found: 'ZZZNoSuchPoolXYZ'

거절이 나왔으므로 이 뒤의 `ok` 들은 「계기가 아무거나 통과시킨 것」이 아니다.

---

## 2. ① CUE 시트 정합 — 18/18, 그런데 술어가 셋 틀렸다

`column-census.md` §5 가 「`Dim` 값과 CUE 시트 `Intensity` 가 어긋나는지 **모른다**」로
남긴 축이다. 이제 잰다.

### 2.1 술어를 네 단계로 정밀화했다

한 번에 답이 안 나온다. 거친 술어는 **없는 어긋남을 만든다.**

| 술어 | 정의 | 일치 | 어긋남 | 비교불가 |
|---|---|---|---|---|
| P1 | 큐 안 표기된 `Dim` 의 최댓값 | 14 | 2 | 2 |
| P2 | + 빈칸을 그룹별 트래킹으로 해소 | 16 | 1 | 1 |
| P3 | + 무대 전체 상태를 큐 사이로 이월 | 17 | 1 | 0 |
| P4 | + `ALL` 그룹이 전체를 덮는다 | **18** | **0** | 0 |

P1 이 만든 어긋남 2건(Q030·Q100)과 비교불가 2건(Q060·Q140)은 **전부 거짓이었다.**
규격 §11.1 3행이 「빈칸 = 트래킹」이라고 이미 말했는데 P1 이 그걸 안 읽은 것이다.

각 단계가 지운 거짓 신호:

    P1 -> P2   Q060 빈칸 3행 = Q050 의 90 을 물려받는다.  CUE 90    일치
               Q140 빈칸 4행 = Q130 의 100 을 물려받는다. CUE 100   일치
               Q100 표기 70 이지만 앞 두 행이 트래킹 95.  CUE 95    일치
    P2 -> P3   Q030 은 SIDE 둘만 적혀 있다(40,40). CUE 는
               `Fixture Group = KEY+BACK+SIDE-L+SIDE-R` 이고
               `Intensity = KEY 70 / SIDE 40` 이다. KEY·BACK 은 Q020
               (70·35)에서 이월된다 -> 무대 상태는 KEY 70 · SIDE 40   일치
    P3 -> P4   Q180 은 `ALL` 한 행 `Dim 0` 뿐인데 상태엔 BACK 20 ·
               HAZE 20 이 남는다. `group.csv` 1행이 `ALL = 전 픽스처
               (FOLLOW 제외) · 글로벌 블랙아웃` 이므로 ALL 0 이 덮는다  일치

> **이 표가 결론보다 중요하다.** 「Dim 과 Intensity 가 어긋난다」는 보고를
> P1 로 냈다면 존재하지 않는 결함 2건을 올렸을 것이다. 규격이 선언한 의미론
> (트래킹 · `ALL`)을 술어에 넣기 전까지 그 수는 시트가 아니라 **내 술어**를 잰 값이다.

### 2.2 Q# 축은 완전 대응

    CUE 시트 Q#     18개
    cue-ex Q#       18개
    CUE 에만 있는 것  0
    cue-ex 에만       0

### 2.3 아무도 안 물은 것 — `.xlsx` 안에 `CUE-EX` 시트가 따로 있다

`LXSEQ_SAMPLE_01_Sugar_r3.xlsx` 는 6장짜리다: `HEAD` `CUE` `NOTE` `PATCH` `PRESET` `CUE-EX`.
즉 `.cue-ex.csv` 와 같은 내용이 통합문서 안에도 산다. 둘이 갈라졌으면 어댑터가
어느 쪽을 읽느냐가 결과를 바꾼다 — 그래서 전수로 댔다.

    xlsx CUE-EX  89행   csv  89행
    17열 x 89행 = 1513셀 대조 -> 셀 차이 **0건**

지금은 갈라져 있지 않다. 다만 이건 **오늘 이 파일 쌍의 관측**이지 불변식이 아니다.
두 자리가 손으로 유지되는 한 갈라질 수 있고, 그때 조용히 갈라진다.

### 2.4 측정 함정 둘 — 다음 사람이 같은 데서 넘어진다

- `<sheet name="...">` 로 시트 이름을 긁으면 **0개가 나온다.** 이 파일은
  `<sheet xmlns:r="..." name="...">` 순서라 `name` 앞에 속성이 하나 더 있다.
  0 을 「시트가 없다」로 읽으면 그 자리에서 조사가 끝난다
- 이 통합문서엔 `sharedStrings.xml` 이 **없다**(전부 `inlineStr`). 게다가 한글이
  `&#51312;` 같은 수치 참조로 인코딩돼 있어 **언이스케이프를 안 하면 한글이 안 잡힌다**

---

## 3. ② 실기 그룹 — 12/13 해결, 슬롯까지 일치

`column-census.md` §5 가 「13개 이름이 지금 콘솔에서 실제로 해결되는지 **미측정**」으로
남긴 축이다.

    t95_state_dump --path 'DataPool/Groups' --listen-port 9005
      node: childCount 18 · class Groups     truncated: **False**
      1 ALL      2 KEY       3 FOH       4 BACK      5 SIDE-L   6 SIDE-R
      7 SIDE-ALL 8 WASH-U    9 WASH-D   10 WASH-ALL 11 MOVER-U 12 MOVER-D
     13 MOVER-ALL 14 BLIND  15 STROBE   16 HAZE     17 ODD     18 EVEN

`truncated: False` 이므로 이건 **전수**다 — 「18개가 돌아왔다」가 아니라 「18개가 전부다」.

| | 값 |
|---|---|
| 콘솔 그룹 | 18 |
| `group.csv` 행 | 18 |
| 이름 일치 | **18 / 18** |
| 슬롯(`GroupNo`) 일치 | **18 / 18** |
| cue-ex 가 쓰는 이름 | 13 |
| 그중 실기에서 해결 | **12** |
| 미해결 | 1 — `LED-W` |

`REQ-LXSEQ2-009`(「측정 슬롯이 시트 `GroupNo` 와 어긋나면 0배치 + 대조표」)가 요구하는
대조에서 **어긋남 0건**이다. 그리고 `LED-W` 가 콘솔에도 없다는 것은
`column-census.md` §4.1 의 판정(「조명 그룹이 아니라 영상팀 큐」)을 **실기가 한 번 더
확인**해 준 것이다 — 시트·패치·콘솔 세 자리 전부에서 부재다.

---

## 4. 🔴 ③ 콘솔 프리셋 풀 — 이름 축이 열려도 실릴 자리가 없다

`column-census.md` §2.4 가 「섞이는 자리는 하류다 — 콘솔 풀에 무엇이 어떤 이름으로
들어 있느냐가 정한다」고 남긴 축이다. 쟀더니 **혼합이 아니라 부재**였다.

    t95_state_dump --path 'DataPool/PresetPools' -> childCount 14 · truncated False
      1 Dimmer  2 Position  3 Gobo  4 Color  5 Beam  6 Focus
      7 Control 8 Shapers   9 Video    21~25 All 1~5

| 풀 | childCount | truncated | 내용 |
|---|---|---|---|
| `Dimmer` (1) | **7** | False | 풀 · 쇼 하이 OLD · 미드 · 로우 · 잔광 · 아웃 · 쇼 하이 |
| `Position` (2) | **0** | False | 비었다 |
| `Color` (4) | **1** | False | 슬롯 32 `Preset 32` (기본 이름) |
| `Beam` (5) | **0** | False | 비었다 |

네 풀 전부 `truncated: False` — 절단이 아니라 **실제로 그만큼뿐**이다.

### 4.1 `COL` 48건은 지금 실릴 슬롯이 하나도 없다

`Color` 풀에 `COL.xx` 이름이 **0개**다. 유일한 1건은 슬롯 32 의 `Preset 32` 로,
이름이 기본값이라 `COL` 어느 것과도 대응하지 않는다.

> 이것이 카드 `t133`·`t134` 의 전제를 바꾼다. 두 카드는 「`COL.02`·`COL.03` 이
> 켈빈 전용이라 막힌다」(t133)와 「시트 0-255 를 콘솔 0-100 으로 옮기는 규칙」(t134)을
> 묻는데, **그 물음들은 나머지 44건이 이미 통한다는 것을 전제한다.** 지금 콘솔에서는
> 44건도 안 통한다 — 갈 슬롯 자체가 없기 때문이다.
>
> 즉 켈빈 4건은 **막힌 것 중 특수한 4건**이지 「4건만 막힌 상황」이 아니다.

그리고 t105·t132 가 기록한 「콘솔 컬러 풀 20건은 전부 우리 앱이 쓴 것」도
지금 상태와 다르다 — 그 20건이 **없다**.

### 4.2 `Dimmer` 풀은 7건인데 csv 는 6행이다

    preset-dim.csv  6행:  풀 · 쇼 하이 · 미드 · 로우 · 잔광 · 아웃
    콘솔 Dimmer 풀 7건:  1 풀 · 2 쇼 하이 OLD · 3 미드 · 4 로우 ·
                          5 잔광 · 6 아웃 · 7 쇼 하이

슬롯 1~6 은 csv 순서 그대로이고, **슬롯 2 만 이름 끝에 ` OLD` 가 붙어 있으며
같은 이름의 새 항목이 슬롯 7 에 있다.**

관측은 여기까지다. 「재실행이 덮지 않고 다음 빈 슬롯에 붙었다」는 **그럴듯한 읽기이지
관측이 아니다** — 나는 임포트를 돌린 적이 없고 누가 언제 돌렸는지도 안 쟀다.
확인한 것 하나: ` OLD` 접미사를 붙이는 코드는 `server/` 안에 **없다**
(`grep -rn 'OLD' server --include='*.py'` 에 해당 생산자 0건). 그러니 그 이름은
콘솔이 붙였거나 사람이 붙인 것이고, **우리 코드가 아니다.**

> 카드 `t132` 가 물은 「재실행하면 슬롯 배정이 어떻게 되나」의 답에 가까운 관측이지만,
> 재실행을 관측한 것이 아니므로 그 카드를 이것으로 닫으면 안 된다.

### 4.3 `POS` 는 두 겹으로 막혀 있다

`column-census.md` §3.1 이 「`preset-pos.csv` 에 값 열이 아예 없다」고 쟀다.
여기에 하나가 더해진다 — **`Position` 풀도 비어 있다**(childCount 0).
즉 값이 시트에 없고, 콘솔에도 그 자리가 아직 없다.

---

## 5. ④ `BM` 속성표 — 있다. 그리고 그 표가 4속성 중 3을 막는다

`column-census.md` §3.3 이 「`Zoom`·`Gobo`·`Prism`·`Frost` 를 기종별 속성으로 옮기려면
픽스처 속성표가 필요하고, 이 판독은 그 표의 **존재를 확인하지 않았다**」고 남겼다.

**표는 있다** — `server/looks/schema.py`. 두 개의 표가 나눠 든다.

    PROBE_GATED_ATTRIBUTES = ("Zoom", "Iris")            # :50
    IN_SCOPE_POOL_FAMILIES = ("Dimmer","Color","Beam","Focus")   # :58
    ATTRIBUTE_POOL_FAMILY:                                # :62
        Dimmer -> Dimmer · ColorRGB_R/G/B -> Color
        Iris   -> Beam   · Zoom           -> Focus

`BM` 이 요구하는 네 속성을 이 표에 대면:

| `BM` 속성 | 표의 답 | 막는 자리 | 사유 클래스 |
|---|---|---|---|
| `Zoom` | `Focus` 계열 · 프로브 통과 | 안 막힌다 | — |
| `Gobo` | 매핑에 없음 | `IN_SCOPE_POOL_FAMILIES` 에 `Gobo` 부재 | **선언으로 제외** |
| `Prism` | 매핑에 없음 | `PROBE_GATED_ATTRIBUTES` 에 부재 | **프로브 거절** |
| `Frost` | 매핑에 없음 | 같음 | **프로브 거절** |

파일 머리말이 사유를 직접 적는다(:15-17): 「M0 라이브 프로브가 `Zoom` 과 `Iris` 로
해소했다. `Focus`/`Frost`/`Prism1`/`Shutter` 는 **콘솔이 거절해서 애초에 안 들어왔다**」.
그리고 :56-57 이 「`Position`/`All`/`Gobo`/`Control`/`Shapers`/`Video` 는 범위 밖
(spec.md §D)」이라고 못 박는다.

> 카드 `t135` 가 「두 사유는 성격이 다르니 한 처방으로 묶지 마라」고 한 것이 맞다.
> **선언 제외**(`Gobo`)는 우리가 스스로 그은 선이라 SPEC 을 고치면 열린다.
> **프로브 거절**(`Prism`·`Frost`)은 콘솔이 답한 것이라 SPEC 을 고쳐도 안 열린다.

### 5.1 그런데 그 프로브 판정은 낡았을 수 있다

`PROBE_GATED_ATTRIBUTES` 의 주석은 근거를 `progress.md §E.2 measurement 1` 로 단다.
그 측정이 **언제·어느 응답기·어느 쇼파일에서** 났는지 이 판독은 확인하지 않았다.
§1 에서 응답기가 1.6.2 로 바뀐 것이 드러난 만큼, 「옛 판정이 낡았을 수 있다」는
`t135` 의 의심은 근거가 있다. 다만 **재측정은 이 회차에서 안 했다**(§6).

그리고 `Beam` 풀이 지금 비어 있으므로(§4), `Prism`·`Frost` 가 열리더라도
실릴 자리는 별도로 만들어야 한다.

---

## 6. 안 잰 것 — 검증된 것으로 물려받지 마라

- **콘솔 쓰기 0.** 판독만 했다. 프리셋 임포트를 돌린 적 없다
- **응답기가 언제·누구에 의해 1.6.2 가 됐는지.** PID 가 같다는 것만 안다.
  재적재라는 것은 **추론**이다
- **` OLD` 접미사를 누가 붙였는지.** 우리 코드가 아니라는 것까지만 쟀다
- **M0 프로브 판정의 측정 조건.** `Prism`·`Frost` 거절이 어느 조건의 것인지 미확인.
  1.6.2 에서의 재측정도 **안 했다**
- **`Focus`·`Gobo`·`Control`·`Shapers`·`Video`·`All 1~5` 풀의 내용.** 안 읽었다
- **`Patch/Stages/1/Fixtures` 는 절단됐다** — childCount 86 인데 19개만 회신
  (`truncated: True`). 86개 라벨 전수는 안 읽었다. 즉 `build_label_fid_table` 이
  86 FID 를 전부 잇는지는 **여전히 미측정**이다. §3 이 답한 것은 그룹 **이름과 슬롯**이지
  멤버십이 아니다
- **`Snap` 결정**(`column-census.md` §4.2)은 이 회차가 건드리지 않았다. 그대로 열려 있다
- **다른 곡파일.** `Sugar_r3` 한 장이다. 대조군 없음

---

## 7. 측정 조건

    origin/main   576e73f
    트리          .claude/worktrees/cue-ex-parity (WT-cue-ex-parity, origin/main 에서 신규)
    콘솔          grandMA3 onPC · app_gma3 pid 38706 · UDP 8000 송신 / 9005 수신
    응답기        live 1.6.2 (CopilotResponder) — 저장소 기록 1.6.1 과 불일치, §1
    쇼 상태       Fixtures 86 · Groups 18 · Dimmer 프리셋 7 · Color 1 · Position 0 · Beam 0
    시트          src/Lighting_Designer/03_곡파일_Sugar/ 의 .cue-ex.csv · .xlsx
    코드          server/looks/schema.py · server/lxseq/group_mapper.py (판독만)
    콘솔 쓰기      0
    코드 변경      0행
    분석 스크립트   `.claude/worktrees/cue-ex-columns/.moai/reports/cue-ex-columns/`
                  의 parity.py · parity2.py · parity3.py · parity4.py (커밋 제외)

⚠️ 쇼 상태는 오늘 하루에만 여러 번 바뀌었다(t105 가 같은 함정을 기록했다).
위 다섯 수는 **이 판독 시점의 값**이고, 다음 세션은 재측정하고 시작해야 한다.
