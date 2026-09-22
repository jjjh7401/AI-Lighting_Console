# SPEC-LDDESIGN-001 설계 개요

[요구사항](spec.md) · [계획](plan.md) · [인수 기준](acceptance.md) ·
[조사](research.md)

Tier L의 plan-phase 산출물(SSOT: `spec-workflow.md` § SPEC Complexity
Tier). **Conditional Design Route는 적용된다**(2026-09-22 감독 결정 —
plan.md M7 "Conditional Design Route 적용 여부" 절 참조. 기존 결정
"미적용"은 뒤집혔다). 이 문서는 M2(큐 모델 v2 타입)와 M7(UI 구성)의
설계 골격을 plan-phase에서 미리 굳혀, run-phase 재작업 위험이 가장 큰
두 마일스톤(plan.md §B 리뷰 우선순위 1·2위)을 착수 전에 구체화한다.

## 1. 큐 모델 v2 타입 개요 (M2)

```python
@dataclass(frozen=True)
class CueV2:
    # 기존 3밴드 속성값(server/looks/schema.py)은 변경하지 않는다 —
    # 아래 7필드가 그 위에 얹힌다(REQ-017).
    layer: frozenset[Layer]          # REQ-018, 1개 이상
    operation: Operation             # REQ-019, 9종 중 하나
    tracking: TrackingMode           # REQ-053, 4종 중 하나
    timing: Timing                   # REQ-024
    evidence: EvidenceGrade          # REQ-022, 4등급
    headroom: Headroom               # REQ-050, 4축
    mib: MibVerdict | None           # REQ-062, 포지션 변화가 있을 때만

Layer = Literal["visibility", "environment", "architecture", "motion", "punctuation"]
Operation = Literal["retain", "add", "remove", "reduce", "replace",
                     "isolate", "expand", "restore", "release"]
TrackingMode = Literal["block", "track", "cue_only", "release"]
EvidenceGrade = Literal["verified", "practitioner_pattern", "designed_rule", "director"]

@dataclass(frozen=True)
class Timing:
    kind: Literal["snap", "short", "long"]   # REQ-058
    seconds: float
    attr_split: bool | tuple[str, ...]       # REQ-060
    stagger: str | None                      # REQ-059

@dataclass(frozen=True)
class Headroom:
    unused_groups: int
    reserved_colors: tuple[str, ...]
    reserved_effects: tuple[str, ...]
    remaining_scale_levels: int

@dataclass(frozen=True)
class MibVerdict:
    status: Literal["dark", "mark", "live"]  # REQ-062
    window_seconds: float
    mark_insert_at: float | None             # REQ-063, live_move 대안
```

`restore`(REQ-020)는 참조 구간의 디머·색·모션을 복원하고 포지션은
제외한다 — `resolver.py`의 `apply()`가 `ref` 파라미터로 기준 상태를
받는다(§ M2 `final_integrated.py` `apply()`를 저장소 타입으로 재작성,
plan.md M2). `reduce`(REQ-021)는 직전 트래킹 값이 아니라 구간 기준
상태(`bases[ref]`)를 참조한다 — 겹쳐 곱해지지 않는다.

## 2. UI 구성 개요 (M7) — 완료(수령), 2026-09-22

> **전제 정정.** 아래 절(구판)은 M7을 "기존 메인 화면에 덧붙이는
> 확장"으로 서술했다. **틀렸다.** 감독이 돌려준 `src/DESIGN.md`가 이
> 전제를 바로잡았다: **M7은 코파일럿 메인 화면(프리셋 풀 브라우저·
> 콘솔 연결 UI·워크시트 입력)이 아니라, 그 위에 얹히는 별도의
> "런북 모드"(Runbook Mode) 페이지다.** 메인 화면은 M7 범위 밖이며
> 이미 구현돼 있다(`ui/src/components/PresetPoolPopup.tsx`·
> `PoolTile.tsx`·`PoolSection.tsx` 등). 런북 모드는 프리셋 풀 팝업을
> **메인 화면 컴포넌트를 그대로 마운트해 재사용**한다 — 팝업을
> 재구현하지 않는다.
>
> **UI 정본은 이제 `src/DESIGN.md`다.** 이 절은 그 문서의 요약이자
> REQ 대조표 역할만 한다 — 상세 사양은 `src/DESIGN.md`를, 수령
> 산출물의 구조화 인덱스는 `design/received-design.md`를, 확정
> 토큰은 `design/tokens-final.md`를, 구현 시 놓치기 쉬운 세부는
> `design/implementation-notes.md`를 보라.

### 2.1 이 화면이 landing 하는 곳

런북 모드는 **신규 페이지가 아니라 기존 `ui/src/components/
RunbookMode.tsx`(263줄, 실측 2026-09-22 `scratchpad/wt-main`)를
확장하는 작업**이다. 이 컴포넌트는 이미 다음을 배선해 두고 있다:

- `cueMonitor` / `isExecutorRunning` / `onExecute` / `onRefresh` —
  실행기 단위 원샷 실행 view(비전문가용 단순 리스트, T-E 특별 계약).
- `timeline` / `timelineStale` / `timelineIsExample` /
  `onShowTimelineExample` — `SongTimeline.tsx` 연동.
- `librarySlot` — 타임라인 라이브러리 패널 슬롯.
- **t281·t291로 이미 배선된 큐시트 초안 편집** — `onSelectCue` /
  `onUndoDraft` / `onRedoDraft` / `onSaveDraft` / `onApplyDraft`
  ("콘솔에 반영", 승인 카드를 거쳐 콘솔에 닿는다). `CueSheetTimeline.tsx`
  (714줄)를 마운트해 쓴다 — 자체 14열 헤더(`SHEET_COLUMNS`,
  `Q# / Section / TC In / TC Out / Dur / Mood / Color(주/보조) /
  Intensity / Fixture Group / Movement / Effect / Trans / Fade /
  Note`)를 이미 갖고 있다. **이 14열은 spec.md REQ-082가 가정한
  "기존 12열"과 다르다** — 상세 대조는 §2.3.

M7은 이 기존 배선 위에 (a) `ConceptPanel.tsx`(신규 컴포넌트), (b)
`CueSheetTimeline.tsx`의 열 재구성(Trigger·근거 등급 등 추가, 일부
기존 열 정리), (c) PLAN CUE 카드의 그룹 편집기화, (d) 콘솔 반영 값
패널(신규), (e) 상태줄 GATE 표시를 얹는 작업이다.

### 2.2 5블록 구조 + 컨셉 패널 (변경 없음)

순서 고정(REQ-078). 컨셉 패널만 블록 1과 2 **사이**에 신규 삽입.

```
1. 오늘의 곡 · 큐 순서        (기존, 헤더만 유지)
 ─ 컨셉 패널                 (신규 ConceptPanel)
2. 타임라인 + 에너지선 + Q줄   (기존 SongTimeline 수정)
3. CUE SHEET 14열            (CueSheetTimeline 재구성 — §2.3)
4. PLAN CUE 카드              (그룹 기반 편집기로 전면 재구성 — §2.4)
5. 상태줄 + GATE              (기존 StatusBanner 수정)
```

전체 폭 1600px 고정 캔버스, 바깥 여백 28px, 블록 간 14px, 블록 배경
`--panel #1e2128` + 테두리 `#2b303a` + radius 10px(`src/DESIGN.md` §1).

### 2.3 CUE SHEET — 14열 확정(감독 결정 2026-09-22), 기존 9열 유지 + 신규 5열 추가 + 기존 5열 제거

**감독 결정(2026-09-22): CUE SHEET는 정확히 14열이다.** 기존 5열
(`TC Out`·`Dur`·`Mood`·`Trans`·`Note`)은 전부 제거하고, 신규 5열을
그 자리에 더한다. 과도(interim) 19열 상태 언어와 "결정 전까지 아무
열도 드롭하지 않는다"는 이 절의 구판 조항은 이 결정으로 대체됐다
— spec.md REQ-LDDESIGN-082(2026-09-22 재확정판)가 이 확정을 담는다.

`src/DESIGN.md` §4.4가 확정한 14열(디자인 의도 목표):
`Q# / 구간 / 회차 / Trigger / 시각 / 색 / 밝기 / 기구 그룹 / 움직임 /
효과 / Fade / MIB / Track 예외 / 근거 등급`.

실측한 기존(`CueSheetTimeline.tsx:225` `SHEET_COLUMNS`) 14열과 개념 단위로
대조하면 — 자세한 표는 `design/spec-gap.md` §2:

- **겹치는 개념, 유지** (9개): Q# · Section↔구간 · TC In≈시각 · Color↔색 ·
  Intensity↔밝기 · Fixture Group↔기구 그룹 · Movement↔움직임 ·
  Effect↔효과 · Fade.
- **신규 추가** (5개): 회차(occurrence) · Trigger · MIB · Track 예외 ·
  근거 등급.
- **제거 확정** (5개, 감독 결정 2026-09-22): TC Out · **Dur** · Mood ·
  Trans · Note.

9(유지) + 5(신규) = 14. 9 + 5(제거) = 14(기존 실측 열 수)이기도 하다 —
"Dur"를 누락해 4개로 적었던 이전 버전은 산수 오류였고, 이미 정정됐다.
spec.md REQ-LDDESIGN-082는 이 사실을 정확히 반영한다: **SHALL은 신규
5열을 추가하는 것과 기존 9열(위 "겹치는 개념")을 유지하는 것과 기존
5열을 제거하는 것 셋 모두에 걸린다 — "14"는 그 세 SHALL의 산술적
귀결이지, 별도의 "고정 개수" 제약이 아니다.** "기존 12열에 2열만
추가"라는 최초 전제는 틀렸고, 실측(9+5=14, 기존도 14열)으로 정정됐다.

**REQ-LDDESIGN-096 — 제거되는 `Trans` 값의 존속.** 제거되는 5열 중
`Trans`(SNAP/XFADE/FADE) 값은 열이 화면에서 사라지는 것이지 데이터
모델에서 사라지는 것이 아니다 — `server/design/cue_sheet_edit.py`의
`TRANS_VALUES`(38-51행)와 `EDITABLE_FIELD_LABELS["trans"]`는 이 SPEC이
바꾸지 않는다. 화면에 보이지 않게 된 이 값을 수정 요청 경로(§2.4 생성기
또는 대화창)로 여전히 바꿀 수 있게 둘지는 M7 착수 시(Implementation
Kickoff Approval 또는 design D-step 브리프) 확인해야 하며, 확인 없이
조용히 접근 불가능하게 만드는 것은 SHALL NOT이다.

### 2.4 PLAN CUE 카드 — 읽기 전용에서 편집기로

`src/DESIGN.md` §4.5가 확정한 형태는 spec.md REQ-083(하단 3줄 +
Q### 배지)보다 크다: 좌(그룹 다중 선택 편집기) / 우 452px(콘솔 반영
값 패널) 2단 구성. 상세는 `design/received-design.md` #4,
`design/spec-gap.md` §3.

**감독 결정(2026-09-22) — 항목별 제거 + 자유 입력 한 줄 채택.**
변경 스택(§4.5 항목 7)의 각 diff 줄은 개별 제거 수단(`✕`)을 갖는다
(REQ-LDDESIGN-100) — 전체 「선택 취소」와는 별개 핸들러다. 변경
스택은 선택으로 만들어지지 않는 요구를 같은 요청에 실어 보내는 자유
입력 한 줄을 갖는다(REQ-LDDESIGN-101) — 생성된 요청 문장 끝에
덧붙어 함께 전송되며, 생성기가 해석하지 않고 그대로 실어 보낸다
(REQ-092 경로 그대로).

### 2.5 프리셋 풀 팝업 — 메인 화면 컴포넌트 마운트, 재구현 금지

`src/DESIGN.md` §0이 확정: 포지션/컬러/딤머/이펙트/페이저 선택
팝업은 메인 화면의 프리셋 풀 브라우저 컴포넌트
(`PresetPoolPopup.tsx` 224줄 + `PoolTile.tsx` 76줄 + `PoolSection.tsx`,
실측 2026-09-22)를 **그대로 마운트**한다. `src/DESIGN.md`의 팝업
마크업은 그 컴포넌트 외형을 재현한 자리표시자일 뿐 — 별도 구현
대상이 아니다.

## 2.6 Claude Design 핸드오프 — 완료

**Conditional Design Route 적용 여부: 적용됨(2026-09-22 감독 결정으로
plan.md M7의 기존 "미적용" 판단을 뒤집음).** D1~D3(디자인 시스템
확인 · 브리프 전달 · Claude Design 작업)와 D4(수령)는 완료됐다.
발신 브리프 5개 파일은 `design/handoff-out/`에 보존돼 있다(발신
시점 기록 — 최신 정본 아님, 각 파일 상단에 표시).

D1~D5 흐름(`.claude/agents/moai/manager-design.md` 파이프라인):

1. **D1 — 디자인 시스템 확인**: 완료(발신 시점).
2. **D2 — 브리프 전달**: 완료 — `design/handoff-out/handoff-brief.md`
   외 4개 파일.
3. **D3 — Claude Design 작업**: 완료 — 산출물 `src/DESIGN.md`(206줄,
   2026-09-22 수령).
4. **D4 — 수령**: 완료. `src/DESIGN.md`를 UI 정본으로 채택. 원본
   `GrandMA3 Copilot M7.dc.html` 렌더 파일은 저장소에 없다(`src/`
   전수 확인 — 우리는 손으로 쓴 설계 문서만 보유하고, 렌더된 디자인
   시스템 파일 자체는 갖고 있지 않다. `design/spec-gap.md`에 감독
   확인 필요 항목으로 기록).
5. **D5 — 구현 반영**: **다음 단계**. `design/spec-gap.md`가 이
   구현 반영에 앞서 spec.md/plan.md/acceptance.md가 먼저 바뀌어야
   할 항목을 정리한 작업 지시서다. spec-gap.md 반영 뒤
   `manager-develop`에 Section A-E 배차(PRESERVE 목록에 `design/`
   산출물 + `src/DESIGN.md` 포함, H8) → `sync-auditor`가 구현 후
   브랜드 일관성(Consistency 차원)을 판정한다.

이 SPEC의 M7 착수(run-phase)는 D4가 끝난 뒤 시작한다 — 이제 시작
가능하다. 단, §3.14의 REQ 본문이 `src/DESIGN.md`와 어긋나는 부분은
`design/spec-gap.md`를 통해 spec.md에 먼저 반영돼야 한다(별도
에이전트가 수행).

## 3. 이 설계가 결정하지 않는 것

- 실제 콘솔 명령 방출 문법(Block/Release, 축별 딜레이, Mark) — M8
  프로브 이후(§4 B군, plan.md §F). `src/DESIGN.md` §5도 이를
  재확인한다("콘솔 실제 방출 컨트롤은 M8 이후").
- `server/concept/` 패키지 내부 모듈 분할의 최종 파일명 — plan.md §C
  M1~M6의 "파일" 목록이 제안이며, run-phase 착수 시 최종 확정한다.
- 큐 모델 v2의 직렬화 형식(JSON 스키마 버전 등) — 저장소 기존 관행
  (dataclass 직렬화 방식)을 M2 착수 시 확인 후 따른다.
- `src/DESIGN.md` §0 각주가 남긴 감독 확인 필요 항목(컨셉 패널 접힘
  상태 라벨 줄바꿈 허용 여부, 로딩 상태 폐기 여부, 원샷 점 색 계열
  분리 여부) — `design/spec-gap.md`에 감독 확인 필요 항목으로
  이관했다. 이 문서는 답을 내리지 않는다. **주의**: 이 항목은 아래
  2026-09-22 5건 판정과는 별개다 — CUE SHEET 14열·컨셉 패널
  "한눈에"+탭 3개·폰트·항목별 제거·자유 입력 한 줄 5건은 이미
  판정됐고(§2.3, §2.4, 아래), 위 3항목(줄바꿈·로딩 상태·원샷 점
  색 계열)은 여전히 미확인이다.

**2026-09-22 감독 결정 5건 — 이 문서가 반영을 마친 항목.** CUE SHEET
14열 확정(§2.3, REQ-082/096) · 컨셉 패널 "한눈에" 5단계 카드 + 탭
3개 채택(§4.2 "한눈에" 구획은 REQ-097·098로 채택, 정보 구조 확대인지
단순 세분화인지의 판단은 "확대"로 감독이 확정했다 — 더 이상 미결이
아니다) · IBM Plex 웹폰트 미채택(§2.6/`design/tokens-final.md`) ·
PLAN CUE 수정요청 생성기 항목별 제거 채택(§2.4, REQ-100) · 자유 입력
한 줄 채택(§2.4, REQ-101). 다섯 건 전부 판정 완료 — 남은 감독 확인
필요 항목은 위 3항목(줄바꿈·로딩 상태·원샷 점 색 계열)뿐이다.
