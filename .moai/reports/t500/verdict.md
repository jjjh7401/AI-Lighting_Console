# t500 판정서 — SPEC-LDRENDER-001 plan (송신 층 연출 복원)

## 판정: plan 감사 2회 FAIL, 점수 하락으로 정지(0.74 → 0.68). 감독 결정 없이는 3차를 돌리지 않는다

- 카드: t500 · 브랜치 `WT-ldrender-plan` · 워크트리 `.claude/worktrees/t500`
- base: 착수 시점 `origin/main` = `b8f44480`(t499 PR #546 머지 뒤 · `git log --oneline -1 origin/main`)
- SPEC: `.moai/specs/SPEC-LDRENDER-001/` — spec·plan·acceptance·research·progress + 연구 입력 사본 + 감사 보고 2편
- REQ 16 · AC 16(Tier M 상한 안). R-항목별: R1 3/3 · R2 3/2 · R3 2/2 · R4 4/4 · R7 4/3 · 공통(회귀·감독 실기 판정) AC 2
- 콘솔 접촉 0 · `server/` 변경 0

## 1. 감사 경과

| 회차 | 점수 | 판정 | 보고서 |
|---|---|---|---|
| 1 | 0.74 | FAIL — critical 1(t497 판단 누락) · major 4(색 배정 근거 없음 · 액센트 밖 점등 AC 좁음 · `RIG_LAYER_ROLES` 닫힌 어휘 충돌 · M1 읽기 전용 미명시) | `audit-plan-001.md` |
| 2 | 0.68 | FAIL · **STOP**(점수 하락 → 무조건 재반복 금지) — 1차 지적 D1~D7 전부 닫힘. 새로 critical 1 · major 1 | `audit-plan-002.md` |

## 2. 남은 결함 (2차, 둘 다 리드가 먼저 짚고 감사가 확인)

- **D11 (major) 완료 조건 약화** — AC-001 이 「구간 큐 중 과반」으로 적혀 있다. 카드 원문은 「구간 큐 다른 값 층 ≥3」(큐 단위)이고, t499 §6.2 판정도 「≤2 인 큐가 하나라도 있으면 위반」이다. 감독 확정 기준을 말없이 낮춘 것이다.
- **D12 (critical) 층 수 맞추기** — R1 을 기존 닫힌 역할 key·back·effect 로만 채우는데, effect 층은 R3 에 따라 비액센트 큐에서 **꺼진 상태(0)**다. back 값(key×0.8)은 0점 Rain 에도 있었다(t499: 최대 2 버킷). 그래서 AC-001 은 KEY·FOH·SIDE·WASH·MOVER 가 지금처럼 같은 값을 받는 채로, **무대가 0점 Rain 과 같아 보여도 통과할 수 있다.**

뿌리는 하나다: **켜진 층 3개를 큐마다 만들려면 SIDE·WASH·MOVER 에 역할이 있어야 하는데**, 역할 어휘가 `server/design/rig.py:44` `RIG_LAYER_ROLES = ("key","back","effect","audience")` 로 닫혀 있고 근거가 정본 `docs/proposals/song-lighting-design-standard.md` §2c 다(그 밖 역할은 `rig.py:305-308` 이 `RigProfileError`). 즉 카드 완료 조건을 정직하게 지키는 것 자체가 **정본 어휘를 바꾸는 감독 결정**을 요구한다.

## 3. 감독 결정이 필요한 것 (SPEC §5 + 이번 정지)

1. **R1 역할 어휘 (결정 2, 이번 정지의 원인)** — (a) 정본 §2c·`RIG_LAYER_ROLES` 에 side/wash/mover 추가 · (b) 기존 역할로 흡수(MOVER→effect, SIDE·WASH→back — 이 경우 켜진 층은 여전히 2) · (c) 역할은 닫아 두고 송신기만 그룹 번호로 따로 주소 · 또는 (d) 범위 축소: R1 을 1차(key/back/effect)·2차(SIDE/WASH/MOVER)로 쪼개고 「켜진 층 ≥3」은 2차 완료 조건으로 미룬다
2. **층 수 세는 법** — 꺼진(0) 층을 층으로 세지 않는다로 고정할지(감사 권고). 고정하면 1번 결정 없이는 AC-001 이 통과 불가
3. **R2 층→색 배정 (결정 3)** — 권장안: 주색은 back, key 는 중립·웜 화이트(정본 §4b C3)
4. **R4 풀에 없는 페이저 (결정 1)** — (a) 기존 FXGEN `compose_fx`/`instantiate_fx` 로 미리 생성(콘솔 쓰기 → 승인 항목) · (b) 큐별 고지만 눈에 띄게(효과는 0줄로 남음)

## 4. 판단한 카드

t497(승인 밖 ClearAll) OUT — 승인 게이트 충실도 결함이지 연출 복원이 아니고, R7 게이트는 이걸 잡지 않는다. 카드는 큐에 남긴다 · t491 OUT(곡 간 다양성 축) · t492 OUT(UI 패널, 2026-09-28 감독 분리) · t494·t495·t496 OUT(송신 층과 무관한 도구·주석·UI 시험)

## 5. 재사용으로 확인한 것 (새로 짓지 않는다)

- 페이저 recall 송신 `_phaser_cue_value_lines`(`song_cue_render.py:508`) · BACK 층 송신 `_back_layer_value_lines`(`:621`) 는 **이미 있다** — R4·R1 은 일반화·호출 전제 닫기
- 효과 생성은 FXGEN·FXLIB(completed) · 곡별 색 스위치는 COLORMODE `palette_mode`(넓히고 새로 만들지 않는다)

## 6. 안 잰 것

- 이 회차는 문서만 썼다 — 판독기·코드 실행 없음. SPEC 이 인용한 파일:줄은 감사가 8곳 이상 대조(1차, 전부 일치)했고 리드가 `rig.py:44·85-95·298-310`, LX-SEQ §11.2 규칙 6, 테스트 119행을 직접 열었다
- `fx.permitted = 0` 원인은 여전히 추정(코드 판독으로 「역할 주소록과 능력 선언 두 축이 섞임」까지 좁힘). M1 이 읽기 전용 실측으로 닫는다
- 3차 감사는 돌리지 않았다(점수 하락 정지 규약)
