# t225 — 콘솔 프리셋 풀 전수 판독 (읽기 전용)

**응답기 1.6.2 · `--listen-port 9005` · 콘솔 쓰기 0.**
전부 같은 도구 한 종으로 한 번에 한 경로씩 쐈다:

    uv run python -m server.tools.t95_state_dump --path "<경로>" --listen-port 9005

`t95_state_dump` 는 요약이 아니라 **회신 원문**을 찍는다. 아래 표의 수는 그
원문의 `node.childCount` 와 `children` 배열에서 읽은 것이고, 모든 회신이
`ok: true` · `truncated: false` 였다.

## 판독 순서와 결과

| # | 경로 | ok | childCount | truncated |
|---|---|---|---|---|
| 1 | `DataPool/PresetPools` | true | 14 | false |
| 2 | `DataPool/PresetPools/4` (Color) | true | 7 | false |
| 3 | `DataPool/PresetPools/5` (Beam) | true | **0** | false |
| 4 | `DataPool/PresetPools/21` (All 1) | true | 2 | false |
| 5 | `DataPool/PresetPools/2` (Position) | true | 6 | false |
| 6 | `DataPool/PresetPools/1` (Dimmer) | true | 7 | false |
| 7 | `DataPool/Groups` | true | 18 | false |

### 3번의 0 은 「안 보인다」가 아니라 「없다」다 — 대조군

`childCount 0` 은 거짓 0 일 수 있다(코퍼스 기록). 그래서 **형제 풀**로 대조했다:
같은 도구 · 같은 명령 형태 · 같은 응답기로 2·4·5·6번이 각각 7·2·6·7 을 답했고
1번이 풀 14개를 답했다. 판독기가 눈먼 상태였다면 그 다섯도 0 이었을 것이다.
즉 3번의 0 은 **계기의 침묵이 아니라 풀의 상태**다.

## 풀별 내용

### Color (pool 4) — 6종 + 미명명 1

| 슬롯 | 이름 | 시트 ID |
|---|---|---|
| 1 | 골드 앰버 (=P1) | COL.01 |
| 2 | 핫 핑크 (=P4) | COL.04 |
| 3 | 딥 퍼플 (=P5) | COL.05 |
| 4 | 터쿼이즈 (=P6) | COL.06 |
| 5 | 선셋 오렌지 (=P7) | COL.07 |
| 6 | 딥 블루 | COL.08 |
| 32 | Preset 32 | (해당 없음) |

**COL.02 「웜 화이트 (=P2)」와 COL.03 「뉴트럴 화이트 (=P3)」가 없다.**
정본 시트 8행 중 이 둘만 값이 색온도 단독(`~3200K` · `~5600K`)이다.

### Beam (pool 5) — 비었다

childCount 0. 정본 BM 시트 5행 중 콘솔에 올라간 것은 0건이다.

### All 1 (pool 21, FX 목적지) — 2종

| 슬롯 | 이름 | 시트 ID |
|---|---|---|
| 1 | DIM-PULSE | FX.02 |
| 2 | PT-CIRCLE | FX.08 |

정본 FX 시트 8행 중 2건. 나머지 6건이 없다.

### Position (pool 2) — 6종, 전부 해결

`POS01`~`POS06` + 「· 합성좌표」. 라벨 첫 어절로 ID 조인이 선다(t220·t224).
콘솔이 라벨에서 `.` 을 지우므로 첫 어절이 `POS01` 로 돌아온다 — t224 실측.

### Dimmer (pool 1) — 7슬롯, 이름 6종이 시트와 맞는다

풀 · 쇼 하이 OLD · 미드 · 로우 · 잔광 · 아웃 · 쇼 하이.
`DIM.SHOW` 는 슬롯 **7**(「쇼 하이」)에 걸린다 — 슬롯 2 는 「쇼 하이 OLD」라
이름이 달라 조인 대상이 아니다.

## 산술 검산 — `preset_slots_resolved = 20`

DIM 6 + POS 6 + COL 6 + BM 0 + FX 2 = **20**.
t224 가 콘솔 왕복으로 얻은 값과 **바이트 일치**한다. 서로 다른 두 경로
(툴 응답 vs 풀 전수 판독)가 같은 수를 냈으므로, 이 슬롯표는 재현된 값이다.

## 🔴 판독 도중 응답기가 조용해졌다

7번까지, 그리고 `lxseq_fx_e2e --action preview` 한 번까지는 전부 정상 회신이었다
(그 preview 의 `baseline.channel_trustworthy` 가 `true`, 날조 경로 대조군
`ok=false`, `Patch/Stages/1/Fixtures` · `DataPool/Groups` 둘 다 `ok=true`).
그 **직후** 같은 `DataPool/PresetPools/21` 조회가 5초 무회신으로 죽었고,
이후 세 번(경로 둘 + `responder_roundtrip --diagnose`) 전부 무회신이었다.

침묵 직전에 돈 것이 `Patch/Stages/1/Fixtures` 를 밟는 하네스라는 점에서
배차서가 경고한 상관과 **같은 형태**다. 다만 이것은 **상관이고 대조군이 없다** —
Fixtures 만 단독으로 쏘는 대조를 돌리려면 응답기가 살아 있어야 하는데, 그게
지금 없는 것이다. 「원인」으로 승격하지 않는다.

⚠️ onPC 를 재시작하지 않았다(배차서 [HARD], 미저장 작업과 오늘의 좌표가 그 안에 있다).

## 부수 발견 — `--timeout-seconds` 가 안 먹는다

`t95_state_dump --timeout-seconds 10` 을 줘도 실패 문면은 `within 5.0s` 였다.
플래그는 선언돼 있는데(기본 6.0) 실제 대기는 5.0 이다 — 플래그가 상태 포트까지
안 내려간다. 이 회차에서 고치지 않는다(콘솔이 죽어 검증할 수 없다). 카드감.
