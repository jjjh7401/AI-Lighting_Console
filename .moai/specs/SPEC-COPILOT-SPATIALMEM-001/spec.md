---
id: SPEC-COPILOT-SPATIALMEM-001
title: "리그 기하 기억 · 표본 재검증 · 신선도 고지 (Spatial Memory)"
version: "0.1.0"
status: completed
created: 2026-08-20
updated: 2026-08-20
author: manager-spec
priority: P1
phase: "Phase 3 응답 지연 — 반복 판독 제거"
module: "server/orchestrator/spatial_memory.py (신설), server/orchestrator/tools.py (get_spatial_context · arrange_fixtures), server/web/session.py · app.py (배선), server/tests/test_spatial_memory.py (신설)"
lifecycle: spec-anchored
tags: "latency, spatial-read, remembered-geometry, sample-revalidation, freshness-disclosure, invalidation, partial-read-never-cached"
tier: M
related_specs: [SPEC-COPILOT-SPATIAL-001, SPEC-COPILOT-TRUNCATE-001, SPEC-COPILOT-PRECHK-001, SPEC-COPILOT-PRESETGUARD-001]
---

# SPEC-COPILOT-SPATIALMEM-001 — 리그 기하 기억

> **이 SPEC이 닫는 구멍**: 좌표는 연출 작업 중 변하지 않는데 **매 요청마다 전량 다시 읽는다.**
> 실측(2026-08-20, onPC 2.4.2, 80대 리그): `get_spatial_context` 한 번이
> 픽스처당 1왕복 × 80 = **9.58초**. 같은 요청을 연속 두 번 실행해도
> **9.58초로 동일** — 캐시가 존재하지 않는다.
>
> **왜 지금인가**: 좌표 기반 요청(웨이브·높이·배치·공간 이펙트)은 이 앱의 핵심
> 차별점이고, 그 턴의 **46%가 이 재판독**이다. 프로그래밍 세션에서 좌표 기반
> 요청을 10회 하면 **96초를 동일한 값을 다시 읽는 데** 쓴다.
>
> **무엇을 하지 않는가**: 기억을 관측으로 위장하지 않는다. 이 저장소의 규율은
> *"성공은 관측에서만 나온다"*(`tools.py:3724`)이고, 좌표 축 하나를 못 읽으면
> 값을 지어내지 않고 `rotation_unread`에 이름으로 올린다(`tools.py:979~981`).
> 기억한 좌표를 **방금 읽은 것처럼** 제시하면 같은 원칙을 정면으로 위반한다.

## A. 배경

### A.1 무엇이 이미 작동하는가 (건드리지 않는다)

| 절 | 상태 | 근거 |
|---|---|---|
| 좌표 판독 | ✅ 건강 | `read_spatial_fixtures()`(`tools.py:1118`) — 열거 + 픽스처당 속성 읽기 |
| 벌크 읽기 | ✅ 건강 | `bulk_capable()`(`prechk/query.py:63`) — 픽스처당 4왕복을 1왕복으로 |
| 부분 판독 분기 | ✅ 건강 | 완전하면 `fixtures`, 불완전하면 `partial_fixtures` + `missing` (REQ-TRUNCATE-001/002) |
| 분석 보류 | ✅ 건강 | 부분 판독에는 `analysis_withheld` — 부분 리그에 확신 있는 배치를 내지 않는다 |
| 쓰기 후 되읽기 | ✅ 건강 | `arrange_fixtures`가 수치 비교로 검증(`tools.py:6012~6050`) |
| TTL 캐시 선례 | ✅ 건강 | `ExecutorNoCache`(`web/app.py:121`, TTL 60초), `SnapshotCache` + `cached: true` 배지 |
| **좌표 기억** | ❌ **오늘 없음** | 연속 두 번 실행 시 왕복 80회를 그대로 재지불 |

즉 이 SPEC은 *"판독이 틀렸다"* 를 고치는 것이 **아니다.** 판독은 정확하다.
**정확한 판독을 불필요하게 반복한다**를 고친다.

### A.2 측정 (2026-08-20, 실기 onPC 2.4.2 · 80대 리그)

턴 내부 분해 — 웹소켓 진행 이벤트 도착 시각:

```
+ 0.00s  모델: 요청 파악
+ 2.63s  도구: 무대 좌표 읽기 시작
+12.21s  도구 완료          ← 콘솔 9.58s (턴의 46%)
+18.53s  chat_response      ← 모델 6.32s
```

감사 로그(`server/audit_logs/audit-20260820.jsonl`) 실측:

| 항목 | 값 |
|---|---|
| 좌표 왕복 | 80건 (`Patch/Stages/1/Fixtures/N fid,posx,posy,posz`) |
| 건당 지연 | 67 ms |
| 같은 턴의 배경 `cue_monitor` 폴링 | 126건 |
| 2회 연속 실행 시간 | 9.58초 / 9.58초 (완전 동일 — 캐시 없음) |

### A.3 이 데이터는 시간이 아니라 사건으로 낡는다

좌표는 60초가 지나서 틀려지지 않는다. **누군가 바꿔야** 틀려진다. 변경 주체는 둘뿐이다.

1. **앱 자신** — `arrange_fixtures`. 이 경로는 이미 되읽기로 검증하므로, 검증된 값을
   그대로 기억에 반영할 수 있다. 관측된 값이므로 기억이 아니라 관측이다.
2. **콘솔 앞의 사람** — 직접 리패치·좌표 이동. **앱은 이것을 볼 수 없다.**

②가 이 SPEC의 유일한 실질 위험이며, 순수 TTL로는 다룰 수 없다. TTL은 "얼마나
오래됐나"만 알고 "바뀌었나"는 모른다.

## B. 요구사항

### B.1 기억 (REQ-SPATIALMEM-001~004)

- **REQ-SPATIALMEM-001** — 완전 판독 결과를 `(fixtures_path, include_rotation)` 키로 기억한다.
- **REQ-SPATIALMEM-002** — **부분 판독은 기억하지 않는다.** `partial_fixtures` 형태의 응답은
  저장 대상이 아니다. 불완전한 리그를 완전한 것으로 굳히면 `analysis_withheld`가 지키는
  불변식이 무너진다.
- **REQ-SPATIALMEM-003** — 기억은 프로세스 전역이다. 탭 N개가 같은 콘솔을 보므로
  세션마다 따로 읽을 이유가 없다(`SnapshotCache`와 같은 근거).
- **REQ-SPATIALMEM-004** — 기억 저장소가 배선되지 않으면(`None`) 동작은 **오늘과 완전히 동일**하다.
  기존 테스트가 왕복 횟수를 정확히 세고 있으므로, 기본값은 비활성이다.

### B.2 표본 재검증 (REQ-SPATIALMEM-005~008)

- **REQ-SPATIALMEM-005** — 기억을 쓰기 전에 **값싼 프로브**로 확인한다.
  ① 컨테이너 1회 조회로 `childCount` 비교(추가·삭제 감지)
  ② 기억된 슬롯 중 표본 K개(기본 3, 처음·중간·끝)의 좌표 재확인
  총 왕복 **4회 내외**.
- **REQ-SPATIALMEM-006** — 프로브가 하나라도 어긋나면 **전량 재판독**한다. 최악의 경우
  비용이 오늘과 같으므로 손해가 없다.
- **REQ-SPATIALMEM-007** — 프로브 자체가 실패하면(포트 예외 등) 기억을 쓰지 않고 전량 재판독한다.
  판정 불가는 적중이 아니다.
- **REQ-SPATIALMEM-008** — 표본은 **좌표까지** 비교한다. 개수만 보면 "80대 그대로,
  위치만 이동"을 놓친다.

### B.3 신선도 고지 (REQ-SPATIALMEM-009~010)

- **REQ-SPATIALMEM-009** — 기억에서 답한 응답에는 `freshness` 블록이 **반드시** 붙는다:
  읽은 시각, 경과 시간, 재검증에 쓴 왕복 수와 표본 슬롯. 모델이 사용자에게 전달할 수 있도록
  한국어 문장을 포함한다.
- **REQ-SPATIALMEM-010** — 콘솔에서 직접 읽은 응답도 `freshness.source = "console"`을 갖는다.
  출처가 있는 응답과 없는 응답이 섞이면 모델이 구분을 배우지 못한다.

### B.4 무효화 (REQ-SPATIALMEM-011~013)

- **REQ-SPATIALMEM-011** — `arrange_fixtures`가 **검증 성공**하면(`verified: true`) 되읽은
  좌표로 해당 픽스처만 갱신한다. 되읽기 값은 관측이므로 기억의 신뢰도를 낮추지 않는다.
- **REQ-SPATIALMEM-012** — `arrange_fixtures`가 검증 실패·부분 실패하면 **전체 무효화**한다.
  무엇이 어디로 갔는지 모르는 상태를 기억으로 남기지 않는다.
- **REQ-SPATIALMEM-013** — 사용자가 강제 갱신을 요청하면(`force_refresh: true`) 기억을 버리고
  전량 재판독한다. 대시보드 수동 새로고침과 같은 조작 핸들이다.

## C. Out of Scope

1. 다중 객체 일괄 읽기(`props` 프로토콜 확장) — responder Lua 변경·콘솔 배포·라이브 검증이 필요하다. 별도 SPEC.
2. 배경 `cue_monitor` 폴링 억제 — 같은 지연 계열이나 원인과 경로가 다르다. 별도 작업.
3. 응답 텍스트 스트리밍 — 모델 구간 개선이며 이 SPEC과 독립.
4. 기억의 디스크 영속화 — 프로세스 재기동 시 첫 판독은 콘솔에서 한다.
5. 회전축(`rotx/roty/rotz`) 전용 최적화 — 키에 포함될 뿐 별도 취급하지 않는다.

## D. 가정

- **ASSUMPTION-86** — 패치 좌표는 `arrange_fixtures` 또는 콘솔 직접 조작으로만 바뀐다.
  쇼 실행 중 자동으로 변하지 않는다.
- **ASSUMPTION-87** — 표본 3개 + 개수 비교가 실무상의 콘솔 직접 변경을 잡아낸다.
  전수 검증이 아니므로 **확률적 보증**이며, 이 한계는 `freshness` 문면에 명시한다.
- **ASSUMPTION-88** — `childCount`는 컨테이너 조회 1회로 얻을 수 있다(`read_spatial_fixtures`가
  이미 그렇게 쓴다, `tools.py:1141~1144`).

## E. 변경 이력

| 버전 | 날짜 | 내용 |
|---|---|---|
| 0.1.0 | 2026-08-20 | 최초 작성. REQ 13 · ASSUMPTION 86-88 · Out of Scope 5항. Tier M. 실측 근거: 80왕복/9.58초/67ms. |
| 0.1.1 | 2026-08-20 | 구현·병합 완료(`ff664a3`, PR #66). 실기 검증(onPC 2.4.2, 80대): 도구 구간 9.58초 → **0.25초**, 턴 22.66초 → 10.83초. 적중 시 왕복 **4회**(표본 슬롯 1/41/80). `arrange_fixtures` 검증 이동 후 기억이 `z=5.0`을 반영한 채 적중(REQ-011), 원값 복원 완료. 뮤테이션: 프로브 무력화 6건 RED, 부분 판독 캐시 허용 2건 RED. server 9,578 passed / 6 skipped. status → completed. |
