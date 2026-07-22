# SPEC-COPILOT-SHOWUI-001 — 디자인 명세 (design)

status: draft (v0.2.1, 2026-07-22 — plan-audit iteration 1 fold-in F1/F4, iteration 2 fix-forward 버전 정렬 반영). 시드: `design-direction.md`(2026-07-22, DP1 승인). 본 문서는 시드의 방향을 구현 가능한 디자인 계약으로 확정한다. `.moai/design/system.md`는 부재 — 본 문서 §3과 `ui/src/styles.css` `:root` 토큰이 canonical base다.

## §1. Intent

- **사용자**: 어두운 FOH에서 라이브 쇼를 진행하는 조명 오퍼레이터. 콘솔 어휘(sequence/executor/cue/look)로 사고하고, 시간 압박 아래에서 조작한다. 오발화는 관객 전체에게 보이며 되돌릴 수 없다.
- **과업**: AI 생성 연출과 콘솔 기존 시퀀스를 **한 번의 시선과 한 번의 누름**으로 실행/정지. 부차: 채팅 연출을 "패널에 추가"로 고정해 안정된 반복 컨트롤로 만들기.
- **감각 목표**: 웹 대시보드가 아니라 **콘솔 익스큐터 윙의 연장**. 정지 상태에서는 조용하고, *live*인 곳만 빛난다. 모든 컨트롤은 누르기 전에 세 질문에 답한다 — *무엇을 하는가? 지금 실행 중인가? 어떻게 멈추는가?* 목표 감각: **"버튼을 믿고 누를 수 있다."**

## §2. 어휘 → UI 번역 (요약)

| 콘솔 개념 | UI 번역 |
|---|---|
| Executor | 타일 = 익스큐터형: 고정 그리드 위치, 큰 press 타깃, 라벨+번호. **위치 안정성 > 정렬 영리함** — 쇼 중 reflow 금지, 신규는 append |
| Cue/Sequence | 콘솔 동사 노출(`Go+`, `Off`) — 범용 "재생/정지" 은유 금지. 실행 중 시퀀스는 현재 큐 번호 표기 |
| Look | one-shot recall 타일: press = apply. 시각적으로 평평/정적(모션 어포던스 없음)으로 이펙트와 구분 |
| Phaser(이펙트) | 실행 중에만 미세 모션 큐(레일 스윕). **항상 보이는 stop 어포던스 필수** — 페이저는 스스로 멈추지 않는다 |
| MAtricks | 톱레벨 컨트롤 아님 — 타일 배지/파라미터 칩("Odd/Even", "Wings 2") |
| Off/Release | 정지(타일별 Off)는 1급 single-press 액션; 전역 All Off는 고정 코너의 **파괴적 발화-클래스**(arm→fire — 정지 클래스 아님, §5/§6). 둘 다 항상 노출, 메뉴에 묻는 것 금지 |
| Appearance color | 타일 좌측 emissive 컬러칩 — 텍스트보다 먼저 색으로 인지 (실제 무대색 유래) |

(전체 표와 근거는 design-direction.md §2. 페이더 행은 DP1-①로 v1 제외 — spec.md §D.)

## §3. 컬러 월드 (토큰 규칙)

기존 토큰(`--bg #14161a`, `--panel #1e2128`, `--accent #4f8cff`, `--ok #3fb950`, `--warn #d29922`, `--bad #f85149`)을 **확장하되 교체하지 않는다.**

| 토큰 | 값 방향 | 역할 / 규칙 |
|---|---|---|
| Console black | base `#14161a` 유지, 패널 웰은 더 깊게(`#101216`) | 패널 배경은 채팅 표면보다 *낮은* 하드웨어 웰 |
| **Live amber** | `#ffb02e` 계열 (`--warn`보다 뜨겁게) | **유일한 "RUNNING" 색.** 활성 재생 상태 전용(타일 보더/레일/배지). 장식 사용 절대 금지 |
| Go green | `--ok #3fb950` 재사용 | 발화 순간의 momentary 피드백만 — 잔류 금지 |
| Stop red | `--bad #f85149` 재사용 | Off/All-Off·파괴적 정지 전용. 패널 내 오류 텍스트에 사용 금지(의미 희석 방지) |
| Appearance chips | 고채도 무대색(cyan `#00c8ff`, magenta `#ff3fa4`, warm white `#ffd9a0`, UV `#7a5cff` 등) emissive 칩 + 미광 | 정지 상태에서 채도가 허용되는 유일한 자리 — 색 = 정보 |
| Dimmed rest | 텍스트 `--muted #9aa0a6`, 크롬 `#2b2f36` 1px | 정지 시 패널은 거의 모노크롬 — 암순응 보호 |

**대비 규칙**: 어두운 FOH에서 팔 길이 거리 가독 — 패널 내 라벨 최소 15px, 상태는 색 단독 전달 금지(`RUN`/`OFF` 텍스트 배지 병행). `color-scheme: dark` 고정 (REQ-SHOWUI-018/020).

## §4. 시그니처 — Live Rail 타일 해부구조

모든 패널 타일(look/effect/sequence)이 공유하는 단일 해부구조 (REQ-SHOWUI-018):

1. **어피어런스 컬러칩** — 좌측 엣지, 전체 높이, emissive. 타일 정체성.
2. **이름 + 타입 배지** — 콘솔 이름 그대로 + `LOOK`/`FX`/`SEQ` 배지(+ MAtricks 칩).
3. **하단 레일(bottom rail)** — 타일의 상태 목소리:
   - 정지: 어두움(`#2b2f36`).
   - 실행 중(이펙트): live-amber **스윕 애니메이션** (속도는 이펙트 rate를 느슨히 따름).
   - 실행 중(정적 룩 유지): live-amber **솔리드**.
   - arm 진행: **press-진행 인디케이터**로 겸용 (arm→fire 2-step의 시각 채널).

한 요소가 정체성·상태·안전을 동시에 나르며, 앱의 다른 어디에도 나타나지 않는 패널 고유 시그니처다.

## §5. 상호작용 명세 (arm→fire / 정지 / 차단)

- **발화(fire)**: 일반 타일은 **single-press**. `createDecisionGuard` 재사용으로 연타 1회 수렴(REQ-SHOWUI-011). 발화 순간 Go green momentary 플래시 → 실행 확인 시 live-amber 상태로 전이.
- **정지(stop) — 타일별 Off 클래스**: **항상 single-press, zero-step, 항상 노출.** 정지 클래스는 **타일별 `Off`만**을 뜻한다 — 정지에 arm 단계·모달·메뉴 진입 금지, 그리고 1-in-flight busy 가드에서 면제(진행 중 execute가 있어도 즉시 처리) (REQ-SHOWUI-012). **전역 All Off는 정지 클래스가 아니다** — 파괴적 발화(fire)-클래스 액션으로 arm→fire 2-step의 지배를 받는다 (§6, REQ-SHOWUI-024/025/026). 두 클래스는 서로소다.
- **arm→fire (파괴적 발화-클래스 한정)**: All Off·블랙아웃급 룩만 2-step — 1차 press = arm(레일이 진행 표시, 짧은 타임아웃 후 자동 disarm), 2차 press = fire. **확인 모달 절대 금지** (REQ-SHOWUI-019 모달 금지 + REQ-SHOWUI-024 arm→fire, design-direction §5.1).
- **busy**: 실행 1건 진행 중 추가 발화는 타일 잠금 + busy 시각 상태 — 토스트 아님, 상태는 타일 위에 지속 표기.
- **차단 상태**: `live_lock` → 전체 타일 제안 전용(비활성 + 제안 어포던스); `health ≠ online`/`executions_blocked` → 패널 레벨 차단 배너 + 타일 비활성 (REQ-SHOWUI-009/010). 색 규칙: 차단 표시는 live-amber를 쓰지 않는다(RUNNING 전용 보존).
- **연결 종료**: running 표시 즉시 소거(fail-closed, REQ-SHOWUI-015) — "아마 아직 돌고 있음" 추정 렌더 금지.

## §6. All Off UX — bounded enumeration (DP1-② 확정)

- **위치**: 고정 코너(패널 우하단), 항상 노출, Stop red 계열, arm→fire 2-step.
- **동작**: 패널이 **추적 중인 running executor들만** 개별 `Off Executor N`으로 정지하는 bounded 번들. 광역 `Thru`/`*`/`Everything` 커맨드 금지 (REQ-SHOWUI-025 bounded 구성 + REQ-SHOWUI-026 광역 금지 — 위험 분류기의 개방형 타깃 승인 보류를 쇼 중에 유발하지 않기 위한 의도된 설계).
- **정직한 라벨링**: 라벨은 범위를 정직하게 전달한다 — 예: **"ALL OFF (패널)"** + 보조 문구 "패널이 추적하는 재생만 정지". 패널 밖 콘솔측 재생이 유지된다는 **한계를 UI에 명시**한다 (spec.md §A 한계 서술의 UI 대응).
- **엣지**: running 추적 항목 0건이면 no-op(비활성 렌더 허용).

## §7. 피해야 할 기본값 (금지 목록)

1. 발화 확인 모달(`window.confirm` 류) — 금지. 안전은 arm→fire 레일 + 상태 표시가 담당.
2. hover 전용 컨트롤/툴팁 단독 정보 — 금지 (터치·장갑·급한 손).
3. 상태 변화 토스트 — 금지. 상태는 타일 위에 지속 표기 (콘솔 응답 오류는 기존 채팅 스트림 사용 가능).
4. 리스트 reflow/자동 정렬 — 금지. 그리드 위치 고정, 신규 append (REQ-SHOWUI-017; reorder는 v1 범위 밖 — DP1-③).
5. 미디어 플레이어 은유(▶ ⏸ ⏹ 단독) — 금지. 콘솔 동사 라벨(`Go+`/`Off`) 우선, 아이콘은 보조 (REQ-SHOWUI-020).
6. 라이트/자동 테마 — 금지. 다크 고정.

## §8. 레이아웃

- **2컬럼**: 채팅(주) + 패널(부), 패널은 접기 가능 — chat-first 경험 보존 (REQ-SHOWUI-017). 기존 `.app` 860px 캡은 확장/해제 필요(styles.css:24 — 수평 프리미티브 부재, 실제 CSS 변경).
- **접기 패턴 모델**: `SettingsPanel` 토글 선례(App.tsx:18,60) — 단 패널은 오버레이가 아니라 사이드 영역(콘솔 윙 감각).
- **그리드**: 타일 고정 위치, append-only. 터치 친화 press 타깃 크기.

## §9. 트레이서빌리티

| 디자인 요소 | 요구 앵커 |
|---|---|
| Live Rail 해부구조 | REQ-SHOWUI-018 |
| live-amber 배타 규칙 / RUN·OFF 배지 / 15px | REQ-SHOWUI-018 |
| 모달 금지 | REQ-SHOWUI-019 |
| arm→fire (파괴적 발화-클래스) | REQ-SHOWUI-024 |
| 정지 클래스(타일별 Off) single-press + busy 가드 면제 | REQ-SHOWUI-012 |
| All Off bounded UX + 한계 표기 | REQ-SHOWUI-025/026, spec.md §A |
| 콘솔 동사 / 다크 고정 | REQ-SHOWUI-020 |
| 2컬럼·접기·그리드 안정 | REQ-SHOWUI-017 |
| 차단/제안/busy 상태 렌더 | REQ-SHOWUI-009/010/011 |
| fail-closed running 소거 | REQ-SHOWUI-015/016 |
