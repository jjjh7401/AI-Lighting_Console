---
id: SPEC-COPILOT-BLOCKED16-001
title: "코파일럿 막히는 지점 16건 — 처분 결정 및 최저비용 개선"
version: "0.7.0"
status: draft
created: 2026-08-18
updated: 2026-08-18
author: orchestrator (kanban plan session, plan-tjxy3n)
priority: P1
phase: "Phase 3 — 백로그 처분"
module: ".moai/specs/SPEC-COPILOT-BLOCKED16-001/disposition.md (신규 처분표), .moai/specs/SPEC-COPILOT-BLOCKED16-001/probe.md (신규 M0 프로브 원장), docs/user-guide.html (단계 3 조준 노출), server/** 무접촉(plan §C.1 PRESERVE)"
lifecycle: spec-anchored
tier: M
related_specs: [SPEC-COPILOT-LDGUIDE-001, SPEC-COPILOT-GROUPGEN-001, SPEC-COPILOT-PRECHK-001, SPEC-COPILOT-OVERLAP-001, SPEC-COPILOT-CUETIME-001, SPEC-COPILOT-AUTOPATCH-001, SPEC-COPILOT-TRUNCATE-001]
tags: "backlog-disposition, non-destructive-probe, measurement-branching, scope-contract, capability-discoverability"
---

# SPEC-COPILOT-BLOCKED16-001 — 막히는 지점 16건 처분

> **이 SPEC은 16건을 구현하는 SPEC이 아니다.** 16건 각각을 ①이번에 구현 · ②측정 선행 ·
> ③명시적 비범위(계약 고정) 셋 중 하나로 배정하고, 배정 근거를 실측에 귀속시킨다.
> **1차 산출물은 처분표(`disposition.md`)다.**
>
> 입력: `.moai/specs/SPEC-COPILOT-LDGUIDE-001/backlog-candidates.md`(16행 원장) +
> 같은 SPEC의 `evidence.md`(E-1~E-33 근거 원장).

## §0. 이 SPEC이 증거로 인정하지 않는 것

LDGUIDE `evidence.md` §0을 승계하고 한 항을 더한다.

- `ok:true` 응답 — 실행 성공 신호는 능력 증명이 아니다.
- 도구 설명문(`description=`) — LLM 지시문이지 동작 증명이 아니다.
- **코드 안의 능력 주장 문자열** — 상수·주석·docstring이 "읽을 수 있다"고 적어 두었다는
  사실은 읽을 수 있다는 증거가 아니다. §A.4가 실제로 이 형태의 대비를 담고 있다.
- **대조군 없는 프로브** — 실패해야 정상인 날조 입력을 함께 쏘지 않은 프로브는
  판정으로 쓰지 않는다(SCENE-001 `/CueOnlyy` 선례: 오타 플래그가 `ok`+저장까지 됐다).

인정하는 것: **재실행 가능한 명령 + 그 명령이 실제로 낸 출력.**

## §A. 사실 — 실측

측정 기준: 워크트리 `/Users/studiox/orca/workspaces/AI-Lighting_Console/blocked16`,
브랜치 `jjjh7401/blocked16`, HEAD `15590e3`, 2026-08-18.

### §A.1 카드 전제 정정 — 넷 중 둘은 이미 측정돼 있다

카드는 "채널폭 · 페이드 시간 · 큐 내용 · 그룹 멤버십 — 이 넷의 성립 여부가 M0에서
갈린다"고 지시했다. 실측 결과 **넷 중 둘은 다른 SPEC이 이미 측정을 끝냈고**, 그 결과가
저장소 안에 귀속돼 있다. 카드 자신이 "기존 실측은 다시 재지 말고 승계할 것"이라 지시했으므로,
이 정정은 범위 재협상이 아니라 그 지시의 이행이다.

| 값 | 상태 | 소유 SPEC | 근거 |
|---|---|---|---|
| 그룹 멤버십 | **측정 완료 — NEGATIVE** | GROUPGEN-001 게이트 A | 정답 기지 표본 반증(§A.2) |
| 채널폭 | **부분 승계 — 현행 읽기 표면 한정 미성립.** 미측정 경로 2건 잔존 | PRECHK-001 `ASSUMPTION-27`(주장 범위 정정본) | §A.3 |
| 페이드 시간 | **측정 완료 — 부분 GO.** Cue 레벨 반증 · Part 레벨 판독 확정 | **CUETIME-001 M1**(2026-08-14 완료) | `.moai/specs/SPEC-COPILOT-CUETIME-001/progress.md:16` · §A.4 |
| 큐 내용 | **미측정** | 없음 | §A.5 |

→ 넷 중 **셋이 이미 측정됐다.** M0의 비파괴 읽기 프로브는 **큐 내용 · 팬/틸트 현재값** 2건과,
페이드의 **잔여 한 갈래**(임의 큐에서 Part 경로가 어떻게 주소화되는가 — §A.4)에 배정한다.

> **초판 정정 [HARD]**: v0.1.0은 페이드를 `미측정 · 소유 SPEC 없음`으로 배정했다. 틀렸다.
> CUETIME-001의 `spec.md`(검증 *계획*)만 읽고 `progress.md`(실측 *기록*)를 열지 않았기 때문이다.
> **REQ-B16-002의 거울상 위반** — 이 SPEC이 금지한 "미측정을 부재로 읽기"의 반대 방향,
> 즉 **측정된 것을 미측정으로 읽기**를 스스로 저질렀다. 독립 감사 1회차 P0-1로 적발됐다.
> 교훈: 소유 SPEC을 승계할 때 **계획 문서가 아니라 진행 기록을 먼저 연다.**

### §A.2 그룹 멤버십 — 정답을 아는 표본에서 반증됐다

```bash
grep -n "게이트 A — 멤버십은 읽을 수 없다" .moai/specs/SPEC-COPILOT-GROUPGEN-001/progress.md
grep -n "grandMA3 does not expose group membership" server/groupgen/write.py
```

관측:

```
.moai/specs/SPEC-COPILOT-GROUPGEN-001/progress.md:232:### §E.2.2 게이트 A — 멤버십은 읽을 수 없다 (**증명됨, 추론 아님**)
server/groupgen/write.py:410:            "grandMA3 does not expose group membership on any readable "
```

GROUPGEN M0가 확인한 것: 후보 속성 `Object`/`Fixtures`/`Content`/`Members` 전부 `ok:false`,
`Count`는 클래스 메서드 핸들(다른 그룹에서 동일 주소), `Selection`은 접근마다 새로 조립되는
불투명 테이블. **멤버를 정확히 아는 Group 14에서도 판독 채널이 없었다** — 남의 그룹을 읽어
낸 추론이 아니라 정답 기지 표본에서의 반증이다. `props COUNT`는 실사용 그룹 4/4에서 `0`이고,
같은 배치의 날조 대조군은 `ok:false`이므로 그 `0`은 오류가 아니라 실제 판독값이다.

**이 SPEC이 승계하되 닫지 않는 잔여**: Group 속성 101개 중 73개는 `introspect` 페이로드
절단(`max_payload = 1900`)으로 관측되지 않았다. 그 안에 멤버 열거 필드가 있을 가능성은
배제되지 않았다. 처분은 이 잔여를 **계약 문면에 명시**하는 형태로 고정한다 —
"판독 불가"가 아니라 "관측 가능한 표면에서 판독 불가, 미관측 표면 73필드 잔존"이 정직한 문장이다.

### §A.3 채널폭 — "전량 반증"은 소유 SPEC이 스스로 철회한 문면이다

```bash
sed -n '1,6p' server/prechk/footprint.py
grep -n "def upper_bound\|def walk_mode_widths" server/prechk/footprint.py
sed -n '644,652p' .moai/specs/SPEC-COPILOT-PRECHK-001/progress.md
```

관측(발췌):

```
server/prechk/footprint.py:3: The pre-check cannot join a patched fixture to its own DMX footprint: the fixture
server/prechk/footprint.py:4: node reports its type and mode as DISPLAY STRINGS, and every candidate route from
server/prechk/footprint.py:5: those strings to a path index was refuted (SPEC-COPILOT-PRECHK-001,
server/prechk/footprint.py:6: ``ASSUMPTION-27``). So the range-overlap axis shipped disabled.
server/prechk/footprint.py:8: This module takes the weaker proposition that survives the refutation. Let ``W``
server/prechk/footprint.py:9: be the largest footprint among the modes that can be ENUMERATED.
   ↑ 6행은 OVERLAP 이전의 역사 서술이고, 8행부터가 현재 동작이다. 발췌를 6행에서 끊으면
     "지금도 비활성"으로 읽힌다 — 감사 2회차 N-1이 정확히 그 경로였다.
server/prechk/footprint.py:130:def upper_bound(outcome: WalkOutcome) -> int | None:
server/prechk/footprint.py:217:def walk_mode_widths(
```

**backlog 3열 서술이 부정확하다.** 모드별 채널폭은 픽스처 타입 트리에서 **이미 열거된다**
(`walk_mode_widths` → `DMXChannels` childCount). 막히는 것은 **패치된 픽스처를 자기 모드의
footprint에 잇는 조인**이다.

#### §A.3.1 그러나 "조인 후보 전량 반증"을 그대로 승계해서는 안 된다 [HARD]

소유 SPEC이 자기 감사에서 이 주장의 범위를 **철회**했다:

```
.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:644:
### `ASSUMPTION-27` 주장 범위 정정 (P2-5)
접두 행과 출하 코드가 "후보 12건 전건 부정"을 **무한정**으로 적었다. 정확한 주장은 이렇다 —
**변경하지 않은 응답기 읽기 표면(state·prop) 위에서, 실제 발화한 프로퍼티명 집합에 한정해 0건.**
응답기는 프로퍼티명을 열거할 수 없으므로 **어떤 프로퍼티 프로브 집합도 부재 증명이 될 수 없다.**
```

같은 절이 표에 없던 **미측정 후보 2건**을 열거한다:

| 후보 | 내용 | 성질 |
|---|---|---|
| **I-14** | `deploy` + `exec`로 콘솔측 프로브를 올려 `handle:Get("FixtureType")`의 실제 반환 타입 판독 | **미측정.** 이 SPEC §C.3이 `exec`/`deploy`를 금지하므로 M0 밖 |
| **I-15** | 열거 가능한 모드 집합에 대한 **보수적 점유폭 상계** — 폭 ∈ {29, 31}, 실측 최소 주소 간격 42. 42 > 31이므로 조인 없이 겹침 0건이 증명된다 | **출하 완료.** `SPEC-COPILOT-OVERLAP-001`(`status: completed`)로 측정·구현·출하됨 — `.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:914` · 코드 `server/prechk/patch.py:72` `BOUND_PROVES_CLEAR` |

I-15가 배제됐던 이유도 기술이 아니라 구조다 — `server/prechk/patch.py`의 `FootprintPolicy`가
`enabled` 이진 게이트라 **"경계 있는 폭" 형상을 표현할 수 없다.**

#### §A.3.2 따라서 처분은 ③이 아니다

**안 쏴 본 경로를 두고 "불가"를 영구 계약으로 굳히는 것은 REQ-B16-002를 이 SPEC이 스스로
위반하는 형태다.** 초판 §A.3은 정확히 그렇게 적었고("확정 판정은 조인 반증으로 불가하며
상계 판정이 최종 형태다"를 계약으로 고정), 독립 감사 1회차 P0-3으로 적발됐다.

정확한 문면: **"현행 응답기 읽기 표면 + 실제 발화한 프로퍼티명 집합에 한정해 미성립.
미측정 경로는 I-14(라이브 필요) 1건. I-15는 OVERLAP-001로 출하 완료."**

> **v0.5.0 정정 [HARD]** — v0.3.0은 I-15를 "미측정이나 라이브 불필요, 다음 후보"로 적었다.
> **거짓이다.** I-15는 이미 측정·구현·출하됐다(`PRECHK-001/progress.md:914` →
> `~~구간 겹침 재개 (후보 I-15)~~ — 출하 완료, SPEC-COPILOT-OVERLAP-001`).
>
> **기전**: §A.3 인용 발췌가 `footprint.py` 3~6행에서 닫혔는데, **8행부터 문단이 반전한다.**
> 6행 `So the range-overlap axis shipped disabled.`는 OVERLAP 이전의 **역사 서술**이고,
> 8행 `This module takes the weaker proposition that survives the refutation.`부터가
> 현재 동작이다. 4행 창이 정확히 그 경계에서 닫혔다.
>
> 이 문면이 처분표로 옮겨졌으면 다음 세션은 **이미 출하된 SPEC을 다시 열도록** 지시받는다.
> 처분값 ②는 유지된다(I-14가 진짜로 미측정이므로). 무너진 것은 배정 근거다. 감사 2회차 N-1.

→ 2단계 채널폭 항목의 처분은 **②(측정 선행)**이며, ③이 아니다. OVERLAP-001의 상계 축
(겹침의 **부재**만 증명하고 존재는 증명하지 못하는 비대칭)은 현재 출하 형태이지 최종 형태가 아니다.

### §A.4 페이드 시간 — 이미 라이브로 측정됐고, 정답은 다른 핸들에 있다

```bash
sed -n '3p;14,18p' .moai/specs/SPEC-COPILOT-CUETIME-001/progress.md
grep -n "PROPERTY_UNOBSERVED_NOTE" server/looks/songcue_report.py
```

관측:

```
.moai/specs/SPEC-COPILOT-CUETIME-001/progress.md:3:  ## M1 (T1) — 완료 2026-08-14
.moai/specs/SPEC-COPILOT-CUETIME-001/progress.md:16:  - readback: Part `CueInFade` = **5.0** (Cue의 CueFade prop은 not
.moai/specs/SPEC-COPILOT-CUETIME-001/progress.md:17:    readable — Part 레벨이 정답).
server/looks/songcue_report.py:15:PROPERTY_UNOBSERVED_NOTE = (...)
```

CUETIME-001 M1은 **2026-08-14에 완료**됐고 라이브 onPC에서 두 가지를 동시에 확정했다:

1. **Cue 노드의 `CueFade` prop은 읽히지 않는다** — NEGATIVE.
2. **Part 레벨 `CueInFade`는 `5.0`으로 읽힌다** — GO. 3D 픽셀 diff(정지 구간 5px)로 5초
   페이드 프로파일과도 정합했다.

`songcue_report.py`의 `PROPERTY_UNOBSERVED_NOTE` 상수("responder prop이 읽을 수 있다")는
**방향은 맞고 핸들이 틀렸다** — Cue가 아니라 Part다. backlog의 "판독 경로가 확인되지 않아
비워 둔 상태다"는 **틀렸다.**

#### §A.4.1 이 SPEC이 §A.5의 교훈을 자기 게이트에 적용하지 않았다

§A.5는 교훈 `no-readable-current-cue-property`(한 핸들 소진을 "읽을 수 없다"로 일반화했고
정답은 핸들을 바꾸는 것이었다)를 인용하면서 **게이트 B에만** 다축 설계를 적용했다. 게이트 A는
`DataPool/Sequences/<S>/Cue <C>` 단일 핸들에 후보 4종을 쏘는 형태로 남겼다 — 즉 **CUETIME이
이미 확인한 그 NEGATIVE를 재생산하도록** 설계돼 있었고, 그 결과로 "큐시트 페이드 열은
비운다"를 영구 계약으로 고정하게 돼 있었다. **읽히는 값을 두고 비운다고 굳히는 형태다.**

#### §A.4.2 그래서 무엇이 남는가

승계로 닫히는 것: **페이드 값은 읽힌다(Part 레벨).** 6단계 처분은 ③(비움 계약)이 아니다.

**주소 형식도 실측돼 있다** — `CUETIME-001/progress.md:21`이 "readback 경로는 스킬 §3b"를
가리키고, 그 자리에 형식이 있다:

```
.claude/skills/ma3-spatial-pointing/SKILL.md:167-169:
  prop:DataPool/Sequences/<n>/<cueName>/<partName>|CueInFade
  (part 이름은 큐 이름과 동일; 실측 5.0 readback)
.claude/skills/ma3-spatial-pointing/SKILL.md:163-165:
  큐 이름의 점(.)은 MA3가 삼킨다 — 'Pos 2.28'로 저장하면 실제 이름은 'Pos 228'
```

승계로 닫히지 **않는** 것: CUETIME이 확인한 것은 **자기가 만든 Seq 101 Cue 1 한 건**이다.
미측정인 것은 이 형식이 **타 SPEC이 만든 큐**와 **다중 Part 큐**로 일반화되는가뿐이다.

> **v0.5.0 정정 [HARD]** — v0.3.0은 잔여를 "임의 큐에서 Part 경로가 **어떻게 주소화되는가**는
> 미측정"으로 적었다. **과장이다.** 형식은 기록돼 있었고, 나는 `progress.md:16-17`은 읽고
> **21행이 가리킨 곳을 열지 않았다.** 그 결과 게이트 A가 번호 형식(`Cue <C>/Part <P>`)을
> 썼고, 그 형식은 저장소 어디에도 실측 기록이 없다. 양성 대조군을 미실측 형식으로 쏘면
> 기지 GO 기준점이 `ok:false`를 답해 **게이트 A 배치 전체가 무효**가 된다.
> 잔여를 실제보다 넓게 적으면 게이트 목적이 흐려진다. 감사 2회차 P0-1r.

### §A.5 큐 내용 — 핸들은 이미 열려 있고 속성명이 미측정이다

```bash
grep -n "SEQUENCE_PATH_TEMPLATE\|CURRENT_CUE_PROPERTY_CANDIDATES" server/web/cue_monitor.py
grep -n "def read_properties" server/prechk/query.py
```

관측:

```
server/web/cue_monitor.py:49:SEQUENCE_PATH_TEMPLATE = "DataPool/Sequences/{sequence_no}"
server/web/cue_monitor.py:62:CURRENT_CUE_PROPERTY_CANDIDATES: tuple[str, ...] = ("CurrentCue",)
server/prechk/query.py:38:def read_properties(
```

현재 큐는 **시퀀스 핸들의 `CurrentCue`로 라이브 확정**돼 있다(정지 `'Sequence 80.1'` →
`Go+` 2회 후 `'Sequence 80.2'`). 큐 children은 `drill_into`로 열려 이름까지 나온다.
미측정인 것은 **큐 노드 자체의 내부 값**(`DataPool/Sequences/<n>/Cue <c>`에서 무엇이 답하는가)이다.

저장소 교훈 `no-readable-current-cue-property`가 기록한 오판 유형을 여기서 반복하지 않는다:
한 핸들에서 후보가 소진된 것을 "읽을 수 없다"로 일반화했던 사례이며, 정답은 핸들을 바꾸는
것이었다. → M0의 큐 내용 프로브는 **핸들 축(시퀀스 / 큐 노드 / 큐 children)을 먼저 나눈다.**

### §A.6 조준 — 이미 동작하고, 막히는 것은 발견 가능성뿐이다

LDGUIDE `evidence.md` §6 게이트 A가 **GO**로 판정했다. `server/web/session.py:107`이
`server/spatial/pointing.py`를 직접 임포트하고, 같은 파일 `_POINT_AT_TARGET` 정규식이
`바라보|비추|향하|조준|겨냥|point|aim`을 인식한다. 등록 도구 33종에 없을 뿐이다.

→ **만드는 일이 아니라 드러내는 일이다.** 측정 의존이 없으므로 M0과 병렬 진행이 가능하며,
16건 중 유일하게 이 SPEC의 run에서 완결 가능한 항목이다.

### §A.7 서술 정정 3건 — 처분표가 원본 서술을 그대로 옮기면 안 되는 자리

| # | backlog 원문 | 정정 |
|---|---|---|
| 정정-1 | 2단계 "장비 채널폭을 직접 읽지 못해" | 모드별 폭은 열거된다. 막히는 것은 픽스처↔모드 **조인**이며, 그 조인조차 "전량 반증"이 아니라 **현행 읽기 표면 한정 미성립**이다. 미측정 경로 2건 잔존(§A.3) |
| 정정-2 | 6단계 "페이드 값 판독 경로가 확인되지 않아" | **확인됐다.** Cue 레벨 `CueFade`는 반증, **Part 레벨 `CueInFade`는 `5.0`으로 판독 확정**(CUETIME-001 M1, 2026-08-14 라이브). 남은 것은 임의 큐에서의 Part 경로 주소화뿐(§A.4) |
| 정정-3 | 8단계 "콘솔이 되돌아오는 신호를 주지 않아 원리적으로 불가하다" | 콘솔 **상태**는 `exec` 결과 + `prop` readback으로 확인된다. 불가한 것은 **DMX 출력이 실물 장비에 도달했는가**이며, 이는 콘솔 밖의 사실이다 |

정정-3은 등급 문제이기도 하다. "원리적 불가"를 좁히면 계약 문면이 정확해지고, 넓게 두면
확인 가능한 것까지 포기한 것으로 읽힌다.

## §B. 요구사항 (GEARS)

### REQ-B16-001 — 처분표 전량 배정

- **G**: 16건 전부가 세 값 중 하나를 갖는다.
- **E**: 처분표가 작성될 때,
- **A**: 각 행은 `단계 · 항목 · 처분(①/②/③) · 배정 근거 · 근거 귀속(E-N 또는 명령+출력) ·
  측정 종류(읽기/쓰기/무관) · 소유 SPEC(있으면)` 7필드를 갖는다.
- **R**: 공란 금지. 미정은 값이 아니다 — 정할 수 없는 행은 ②로 배정하고 무엇을 재야 하는지 적는다.
- **S**: 행 수 == 16, 처분 열의 값 집합 ⊆ {①,②,③}, 공란 0.

### REQ-B16-002 — 미측정을 부재로 읽지 않는다

- **G**: 콘솔 미접속이 "판독 불가" 결론으로 굳지 않는다.
- **E**: M0 실행 시 onPC가 붙어 있지 않으면,
- **A**: 해당 프로브 행을 **`미측정`**으로 기록하고, 처분을 측정 결과에 분기시켜 설계한다
  (GO 분기 / NEGATIVE 분기 둘 다 유효한 출력으로 명시).
- **R**: `미측정`과 `NEGATIVE`는 다른 값이며 서로 대체되지 않는다. 프로브 원장에서
  `미측정` 행은 `판독 불가`로 요약되지 않는다.
- **S**: 프로브 원장의 판정 열 값 집합 ⊆ {GO, NEGATIVE, 미측정}.

**run 착수 게이트 연결 [HARD]**: 이 REQ는 *미측정을 부재로 읽는 것*을 금지한다. 그 거울상
(*측정된 것을 미측정으로 읽기*)과 그 변종 둘이 감사 1·2회차에서 세 번 적발됐으므로,
인용에서 유래한 전제는 M0에서 3술어로 재확인한 뒤에만 처분에 쓴다 — `plan.md` §B.9.

### REQ-B16-003 — 프로브는 비파괴 읽기이며 대조군을 동반한다

- **G**: M0가 쇼파일 상태를 바꾸지 않는다.
- **E**: 프로브를 쏠 때,
- **A**: `prop`/`state` 읽기 동사만 쓰고, 각 프로브마다 **실패해야 정상인 날조 입력**을
  같은 배치에서 함께 쏜다.
- **R**: `exec` 동사 사용 금지. 날조 대조군이 `ok:true`를 내면 그 배치의 판정 전체를 폐기한다.
- **S**: 프로브 원장의 모든 판정 행이 대조군 행과 쌍을 이룬다(대조군 없는 판정 0건).

### REQ-B16-004 — 승계 실측 재측정 금지

- **G**: 이미 측정된 것을 다시 재지 않는다.
- **E**: 그룹 멤버십·채널폭·**페이드** 처분을 정할 때,
- **A**: 소유 SPEC의 측정 결과를 인용하고 그 잔여 한계를 계약 문면에 옮긴다.
- **R**: 승계 인용은 **문서 경로 + 행 번호**로 귀속한다. 요약 재진술만으로는 귀속이 아니다.
  **좌표가 해소되는 것과 주장이 아직 유효한 것은 다르다** — 인용 3건 전부 정확히 해소되면서
  승계 주장이 반증된 사례가 실제로 있었다(감사 2회차 N-1).
- **S**: 승계 **3건** 각각이 소유 SPEC 경로:행번호를 갖고, 그 행이 주장의 핵심 토큰을 담으며, 소유 SPEC에 후속 반전이 없다.

### REQ-B16-005 — 조준을 **기능 대조표 쪽에** 노출한다

- **G**: 감독이 기능 목록에서 조준의 존재를 알 수 있다.
- **E**: 감독이 참조 부록(`id="appendix-tools"`)의 기능 대조표를 볼 때,
- **A**: 조준이 **비도구 기능** 별도 절로 나타나며, 발화 조건(대상 + 목표가 둘 다 필요)을 함께 싣는다.
- **R**: 등록 도구 33종 표의 **행으로 넣지 않는다** — 넣으면 `33` 주장이 34로 어긋난다.
  표 옆에 별도 절을 신설하고, 표의 행 수는 33을 유지한다.
- **S**: AC-008.

#### 초판 정정 [HARD] — 간극은 단계 3에 없었다

v0.1.0의 REQ-B16-005는 **E와 S를 둘 다 단계 3 구간에 걸었다.** 독립 감사 1회차 P0-2가
무변경 HEAD에서 AC-008을 그대로 돌려 **세 하위 검사 전부 통과**함을 보였다:

```bash
G=docs/user-guide.html
s3=$(awk '/id="stage-3"/{f=1} f&&/id="stage-4"/{f=0} f' "$G")
printf '%s' "$s3" | grep -cE '조준|겨냥'   # 3
grep -cE '33(가지|종|개)' "$G"              # 2
grep -cE '34(가지|종|개)' "$G"              # 0
```

즉 **아무것도 고치지 않은 상태에서 통과하는 자기인증 AC**였다. 현행 단계 3은 이미 조준을
충실히 서술하며, 가이드 자신이 그 구간에서 간극의 위치를 명시한다:

```
단계 3 구간 19행: <p>조준 기능은 <b>기능 대조표에 나타나지 않습니다.</b> 문장으로는
                  도달하지만 목록에는 없어,
```

**backlog 3단계 첫 항목이 지목한 간극은 "기능 대조표에 나타나지 않는다"이고, 그 자리는
`id="appendix-tools"`다.** 초판은 간극이 없는 자리를 고치라 요구하고 간극이 있는 자리는
R로 묶어 놓았다 — "run에서 완결 가능한 유일한 항목"이 관측 가능한 산출을 내지 않는 형태다.

#### 발화 조건을 함께 싣는 이유

```bash
sed -n '3546,3555p' server/web/session.py
```

`_POINT_AT_TARGET` 정규식을 통과해도 **중앙어 또는 좌표 3쌍**이 없으면 `return None`이다.
"조준이 됩니다"만 적으면 감독이 "조준해"라고만 말하고 아무 일도 일어나지 않는다.
노출 문면은 **무엇을 함께 말해야 하는지**를 담아야 쓸 수 있는 문서가 된다.

### REQ-B16-006 — 서술 정정 3건 반영

- **G**: 처분표가 원본의 부정확한 서술을 승계하지 않는다.
- **E**: §A.7의 3건에 해당하는 행을 쓸 때,
- **A**: 정정된 서술을 쓰고, 원문과 정정을 나란히 남긴다.
- **R**: 원문을 지우지 않는다 — 무엇이 바뀌었는지 감독이 볼 수 있어야 한다.
- **S**: 처분표에 정정 3건이 원문·정정 쌍으로 존재한다.

### REQ-B16-007 — 시간 예측 금지

- **G**: 처분표가 일정을 담지 않는다.
- **E**: 우선순위를 표기할 때,
- **A**: 순서(먼저/다음)와 등급(P0~P3)만 쓴다.
- **R**: `N주` · `N개월` · `즉시(1~2주)` 형태 금지. LDGUIDE가 로드맵 절을 drop한 사유와 같다.
- **S**: 산출물에서 시간 예측 정규식 매치 0건.

### REQ-B16-008 — 이 SPEC의 문서가 선언한 수와 실제를 어긋내지 않는다

- **G**: 산출 문서가 자기 자신에 대해 틀린 수를 말하지 않는다.
- **E**: 문서가 자기 구성요소의 개수를 언급할 때,
- **A**: 개수의 출처는 **하나**여야 한다 — 기계 판독 리터럴 1곳. 다른 곳은 그 리터럴을
  참조하거나, 총계가 아니라 **증분**(무엇이 늘었는가)을 적는다.
- **R**: 총계를 두 곳 이상에 적지 않는다. 검사를 하나 더 다는 것으로 해결하지 않는다 —
  중복 출처가 남아 있으면 검사가 통과해도 다음 판본에서 다시 어긋난다.
- **S**: AC-012.

**이 REQ가 생긴 경위**: 초판 `acceptance.md` HISTORY가 `AC-001~010`이라 적었으나 실제
정의는 11건이었다(lead 지적, 2026-08-18). LDGUIDE-001이 교정한 결함 유형(등록 33종을
22종으로 표기)을 **그 SPEC의 규율을 승계한 문서가 자기 HISTORY에서 재생산한 것**이다.
승계한 규율이 남의 문서에는 걸리고 자기 문서에는 안 걸린 자리다.

### REQ-B16-009 — 쓰기 범위가 기계로 봉쇄된다

- **G**: 이 SPEC의 변경이 허용 2경로를 벗어나지 않는다.
- **E**: run 종료 시점에 변경 파일 목록을 낼 때,
- **A**: `.moai/specs/SPEC-COPILOT-BLOCKED16-001/**` + `docs/user-guide.html` 두 경로만 나타난다.
- **R**: `plan.md` §C.1 PRESERVE 목록은 문서 선언이며 그 자체로는 검사가 아니다.
  기계 검사가 없으면 `server/**` 무접촉 주장은 미관측 주장이다.
- **S**: AC-013.

**이 REQ가 생긴 경위**: 독립 감사 1회차 P1-4 — `plan.md` M3이 회귀 항목 5개를 나열하는데
경계 검사(허용 경로)와 외부 URL 0에 대응 AC가 없었다. LDGUIDE의 `AC-LDG-013`에 위임할
수도 없다 — 그쪽 허용 경로는 LDGUIDE 디렉터리라 이 SPEC의 diff에 돌리면 오히려 실패한다.

## §C. 비목표

- **16건의 구현.** 이 SPEC은 처분을 정하며, ①로 배정된 항목 외에는 구현하지 않는다.
- **쓰기 프로브.** 복원 경로(4-b · 7-b)의 성립 여부는 쓰기 측정을 요구하며 M0 밖이다.
- **응답기 확장.** 신규 동사(`M.VERSION` 1.7.0 계열)는 이 SPEC에서 열지 않는다.
- **`introspect` 페이지네이션.** 그룹 속성 73필드 미관측 잔여를 뚫는 작업은 TRUNCATE-001
  계열의 몫이며, 여기서는 잔여로 기록만 한다.
- **감독 도메인 결정의 대행.** 1단계 판정 기준·5단계 사용자 정의 범위는 제품 결정이며
  이 SPEC이 스스로 정하지 않는다. blocker로 lead에 올렸고 **2026-08-18 확정 회신을 받았다**(§D).
  확정된 것은 다음 SPEC의 방향이며, 그 구현은 여전히 이 SPEC의 비목표다.

## §D. 열린 질문 — lead 확정분 반영 (v0.2.0)

초판(v0.1.0)은 Q1·Q2·Q4를 감독 결정 대기로 두었다. **2026-08-18 lead가 감독 위임을 받아
셋 다 확정했다.** 처분은 셋 다 ③(이번 SPEC 비범위)로 변하지 않았고, 확정된 것은 **다음 SPEC의
방향**이다 — 즉 이 결정들은 처분표의 `배정 근거` 열을 채우지, 처분 열을 바꾸지 않는다.

| # | 질문 | 상태 | 확정 내용 | 처분 |
|---|---|---|---|---|
| Q1 | 1단계 어긋남 판정을 유형 분류로 갈 것인가 | **확정** | 감독 판정 보조표. 유형 분류 채택 안 함 | ③ |
| Q2 | 5단계 사용자 정의를 파일 편집인가 화면 학습인가 | **확정** | 파일 편집 경로 우선. 화면 학습은 이번에 열지 않음 | ③ |
| Q3 | 8단계 다중 콘솔을 범위에 넣을 것인가 | **결정 불필요** | 하드웨어 자원(콘솔 2대) 전제가 없어 측정 대상 자체가 존재하지 않는다. 감독 위임 대상이 아니다 | ③ |
| Q4 | 6단계 오디오 구간 분할에 외부 의존을 추가할 것인가 | **확정** | 추가하지 않음. 명시적 비범위로 고정 | ③ |

각 결정의 근거 전문과 다음 SPEC 후보 3건은 `progress.md` §H에 있다.
Q3이 감독 위임 대상이 아닌 이유는 `progress.md` §H.1에 있다.

**[HARD] §D 번호 규약**: 이 표의 질문 번호는 `progress.md` §H에 **전량** 나타난다.
결정이 불필요한 항목도 그 사실을 값으로 적는다 — 번호만 빠지면 다음 세션이 누락으로 읽는다.
초판에서 Q3이 실제로 그렇게 빠졌고 lead가 지적해 닫았다.
