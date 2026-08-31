# t215 — grandMA3 명령줄이 속성그룹(I/P/C/B)별 Fade·Delay 를 받는가

**판정: YES.** 다만 그 속성은 큐가 아니라 큐 **파트**의 것이고, 한 파트는
속성그룹당 값을 하나만 갖는다. 그래서 「그룹마다 다른 값」은 파트를 갈라야 담긴다.

- 일시: 2026-09-01
- 계기: `server/tools/responder_roundtrip.py` · `server/tools/introspect_probe.py`
- 콘솔: grandMA3 onPC · 응답기 `CopilotResponder` **1.6.2** · `--listen-port 9005`
- 실험 대상: **스크래치 `Sequence 9`** (없던 번호임을 먼저 확인 후 생성)
- 무접촉 확인: `Sequences/2` 'Sugar' childCount 21 · `Sequences/3` 'Sugar r3' childCount 21 —
  실험 전후 동일

---

## 1. 계기 검증 — 대조군 먼저

| # | 보낸 것 | 콘솔 응답 | 읽는 법 |
|---|---|---|---|
| C1 | `Frobnicate Sequence 9` | `responder error: Illegal object` | 없는 **동사**는 거절된다 |
| C2 | `Group 1 At Full Zorble 3` | `ok` | 🔴 없는 **꼬리 키워드**는 `ok` 를 받는다 |
| C3 | `Set Cue 1 Sequence 9 Property 'Preset1Frobnicate' 7` | `responder error: Illegal property` | 없는 **속성명**은 거절된다 |

**C2 가 이 회차의 핵심 계기 결함이다.** 꼬리 키워드 축에서는 `ok` 가 아무것도
증명하지 않는다. 그래서 아래 모든 판정은 `ok` 가 아니라 **되읽기**로 내렸다.

C2 는 더 나쁜 형태로도 재현됐다:

| 보낸 것 | 응답 | 실제 효과 |
|---|---|---|
| `Store Cue 2 'T215 ALT' Sequence 9 Preset1Fade 3 /Merge /NoConfirm` | `ok` | Sequence 9 childCount **3 → 3** (아무것도 안 생김) |
| `Store Cue 2 'T215 ALT' Sequence 9 /Merge /NoConfirm` (대조군) | `ok` | childCount **3 → 4** |

두 명령의 차이는 꼬리 `Preset1Fade 3` 하나뿐이다. 즉 그 꼬리가 **Store 전체를
조용히 죽였고**, 응답은 둘 다 `ok` 였다. 프로그래머가 비어 있어서가 아니라는 것은
대조군이 증명한다.

## 2. 되읽기 채널

`Cue` 객체에는 타이밍 속성이 없다(`CueFade` → `property not readable`).
타이밍은 **`Part` 자식**에 있다. `introspect` 로 열거한 Part 속성 중 관련분:

    INDIVIDUALTIMING · INDIVFADE · INDIVDELAY · INDIVDURATION
    PRESET1FADE / PRESET1DELAY … PRESET16FADE / PRESET16DELAY

기본값은 문자열 `"CueTiming"`(= 큐 타이밍을 따름)이고, 값이 박히면 숫자로 바뀐다.
이 두 상태가 바이트로 갈리므로 되읽기가 판별력을 갖는다.

프리셋 타입 번호는 추측하지 않고 콘솔에서 읽었다 — `DataPool/PresetPools/N` 의 `name`:

| N | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| name | Dimmer | Position | Gobo | Color | Beam | Focus |

시트 축 대응: **I → Preset1Fade · Id → Preset1Delay · P → Preset2Fade ·
C → Preset4Fade · B → Preset5Fade**.

## 3. 시도한 명령 형태 — 전문

| # | 명령 (verbatim) | 응답 | 되읽기 | 판정 |
|---|---|---|---|---|
| F1 | `Set Cue 1 Sequence 9 Property 'Preset1Fade' 3` | `ok` | `PRESET1FADE` "CueTiming" → **3.0** | ✅ 채택 |
| F1 | `Set Cue 1 Sequence 9 Property 'Preset1Delay' 0.5` | `ok` | `PRESET1DELAY` → **0.5** | ✅ |
| F1 | `Set Cue 1 Sequence 9 Property 'Preset2Fade' 4` | `ok` | `PRESET2FADE` → **4.0** | ✅ |
| F1 | `Set Cue 1 Sequence 9 Property 'Preset4Fade' 1.5` | `ok` | `PRESET4FADE` → **1.5** | ✅ |
| F1 | `Set Cue 1 Sequence 9 Property 'Preset5Fade' 0` | `ok` | `PRESET5FADE` → **0.0** | ✅ (스냅 표현 가능) |
| F1' | `Set Cue 2 Sequence 9 Property 'Preset5Delay' 2.5` | `ok` | `PRESET5DELAY` → **2.5** | ✅ 다른 큐에서 재현 |
| F1'' | `Set Cue 5 Part 1 Sequence 9 Property 'Preset1Fade' 6` | `ok` | Part 1 → **6.0** / Part 0 → "CueTiming" | ✅ 파트 지정 가능 |
| F2 | `Store Cue 2 'T215 ALT' Sequence 9 Preset1Fade 3 /Merge /NoConfirm` | `ok` | 큐 자체가 안 생김 | ❌ 거절(무효과) |
| F3 | `Assign Cue 2 Sequence 9 /Preset1Fade=3` | `ok` | `PRESET1FADE` "CueTiming" 그대로 | ❌ 무효과 |
| F4 | `Store Cue 5 Part 1 'T215 PART' Sequence 9 /Merge /NoConfirm` | `ok` | 큐 childCount **1 → 2** (Part 0 + 'T215 PART') | ✅ 파트 생성 |
| F5 | `Group 1 At 50 Fade 3` → `Store Cue 3 …` | `ok` | `INDIVFADE` **0.0 → 3.0** | ✅ 다만 §5 참조 |

**격리 대조**: F1 을 다섯 번 쏜 뒤 손대지 않은 이웃 속성
(`PRESET2DELAY` · `PRESET4DELAY` · `PRESET3FADE`)은 전부 `"CueTiming"` 그대로였다.
쓰기는 지정한 자리에만 닿는다.

## 4. 채택한 형태

    Set Cue <번호> [Part <n> ]Sequence <시퀀스> Property 'Preset<타입>Fade' <초>
    Set Cue <번호> [Part <n> ]Sequence <시퀀스> Property 'Preset<타입>Delay' <초>

파트가 필요한 경우:

    Store Cue <번호> Part <n> "<라벨>" Sequence <시퀀스> /Merge /NoConfirm

## 5. 재지 못한 것 (gap)

- **한 파트 안에서 그룹마다 다른 개별 타이밍**. F5 의 프로그래머 `Fade` 키워드는
  분명히 큐에 실린다(대조군: 키워드 없이 저장한 큐는 `INDIVFADE` 0.0). 그러나
  두 그룹에 서로 다른 값(7.25 / 1.5)을 주고 저장하니 `INDIVFADE` 가 **7.25 하나만**
  답했다 — 이 채널은 그룹별 값을 직렬화하지 않는다. 「둘 다 실렸다」도 「하나만
  실렸다」도 증명되지 않았으므로 **파이프라인은 이 경로를 쓰지 않는다.**
  파트 분해는 되읽기로 증명된 경로다.
- **BM 축의 타입 번호.** 시트의 BM 프리셋은 풀 21(All-type)에 산다. 타이밍 색인은
  풀이 아니라 **속성 타입**을 따르므로, BM 프리셋이 Zoom 같은 Focus 속성을 담고
  있으면 그 부분은 `Preset5Fade`(Beam)가 아니라 `Preset6Fade`(Focus)에 걸린다.
  BM 프리셋의 실제 속성 구성은 안 쟀다.
- **FX 축(풀 22)의 타이밍**은 시트에 열이 없어 다루지 않았다.
- **생성된 스크립트를 콘솔에서 실행해 보지 않았다.** 명령 *형태*만 스크래치
  Sequence 9 에서 쟀고, 그때 쓴 것은 `Group 1·2·3` 이지 시트의 이름 그룹이 아니다.
  Sequence 1 에 실제로 쏘는 것은 감독 승인 사항이라 이 카드에서 하지 않았다.
- **파트가 한 Go 에서 각자 타이밍으로 함께 발사되는지**는 MA3 문서상 동작이고
  여기서 재지 않았다.
- 값 표기는 `0`, `0.5`, `1.5`, `2.5`, `3`, `4`, `6`, `7.25` 만 왕복했다. 더 긴
  소수·음수·`CueTiming` 문자열 되돌리기는 안 쟀다.

## 6. 콘솔에 남긴 것

- `Sequence 9`, 라벨 **`T215 SCRATCH DELETABLE`**, 큐 5개. 지워도 되는 습작이다.
  삭제는 하지 않았다 — 되돌릴 수 없는 콘솔 쓰기라 확인과 사고가 같은 행위가 된다.
- 프로그래머는 `ClearAll` 로 비웠다.
- `Sequences/1·2·3` 에는 아무 명령도 보내지 않았다.

## 7. 이 판정으로 바뀐 코드

- `make_ma3.py` — `[MANUAL] 개별 타이밍` 주석이 실제 명령이 됐다. 값이 충돌하지
  않는 그룹끼리 한 파트로 묶고, 충돌하면 파트를 가른다. 시트 18큐 중 파트가
  갈리는 것은 **Q040 · Q110 · Q160** 셋(파트 4개 추가).
- `validate_ma3.py` M3 — 파트 저장을 큐 개수에서 빼고, 대신 고아 파트를 잡는다.
- `server/tests/test_ma3_cue_part_timing.py` — 11개 검사.
  뮤테이션 **5/5 사망**(파트 충돌 판정 무력화 · Preset1Delay 축 제거 · Part 토큰
  삭제 · 타이밍 없는 그룹 합류 · 파트 저장 구문에서 Part 제거).

⚠️ 2 팔 대조의 두 번째 팔(「기존 검사로는 못 잡는가」)은 여기서 **퇴화한다** —
`test_pipeline_out_paths.py` 가 커밋된 산출물과 바이트 동일성을 보므로 생성기를
어떻게 바꾸든 빨개진다. 즉 기존 검사는 「달라졌다」를 말하고 **무엇이 틀렸는지는
말하지 않는다.** 새 검사가 하는 일이 그것이다.
