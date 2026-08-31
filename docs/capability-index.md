# 조명 연출 능력 색인 (Capability Index)

> 2026-08-31 전수 조사 · **SPEC 은 만들 때의 문서, 이 색인은 쓸 때의 문서다.**
> 하루에 이미 있는 기능을 세 번 다시 찾은 뒤에 만들었다.
> 갱신 규칙: 기능이 추가되면 여기도 같이 고친다.

## 왜 이 문서가 있나

2026-08-31 하루에 같은 낭비가 세 번 났다:

| 잊은 것 | 어디 있었나 |
|---|---|
| RIG 팩 `fx.csv` (FX.01~08 정의) | `src/Lighting_Designer/02_RIG팩/` — 아무도 안 씀 |
| 기본 프리셋 6축 × 10종 | `server/web/session.py` — 「없다」고 오판 |
| 배치 기반 시퀀스 | `server/spatial/` 15모듈 |
| 곡 조명연출 표준 · L1~L14 | `docs/proposals/song-lighting-design-standard.md` |

원인 셋: ① 경로가 둘(시트·대화)인데 서로 모름 ② 능력이 SPEC 46개에 흩어짐
③ 대화 트리거가 정규식이라 「무슨 말이 통하는지」 목록이 없음

## 규모

```
SPEC          46개    .moai/specs/
등재 도구      38개    server/orchestrator/tools.py
연출 모듈      60+     server/{spatial,design,looks,scene,fx,lxseq,prechk,preshow}/
문서          58편    docs/  1.2MB  ← 자산의 본체
룰북           7장    server/rulebook/assets/v2.4.2/  45KB · 약 23K 토큰
```

## 능력 7계층

1. **리그 이해** — 패치·인벤토리·공간·Vectorworks·도면이미지
2. **그룹·토폴로지** — 배치가 그룹이 된다 (`spatial/` 15모듈)
3. **프리셋 자산** — 6축 × 10종, 대화로 부름
4. **이펙트·페이저** — 라이브러리 + `compose_fx` 작성
5. **룩·씬** — 장르별 조합 단위
6. **큐·시퀀스** — 곡 구조로 배치 + 연출 표준
7. **안전 게이트** — 모든 쓰기가 지남

## ① 리그 이해

| 기능 | 도구/모듈 |
|---|---|
| 패치 임포트 | `import_lxseq_patch` |
| 패치 사전점검 | `precheck_patch` · `prechk/` 8모듈 |
| 인벤토리 판독 | `prechk/inventory.py` |
| 픽스처 타입·주소 해석 | `resolve_fixture_type` · `resolve_patch_address` |
| Vectorworks | `vectorworks_autopatch` · `precheck_vectorworks_diff` · `apply_vectorworks_patch` |
| 도면 이미지 | `analyse_layout_image` |
| 공간 기억 | `get_spatial_context` · `orchestrator/spatial_memory.py` |
| MVR 템플릿 | `docs/templates/patch_from_mvr.{csv,xlsx}` |

## ② 그룹·토폴로지 — 배치 기반 시퀀스

핵심 문장: **「한정어가 정렬이 되고, 정렬이 순서가 된다」** (`spatial/choreography.py`)

| 모듈 | 역할 |
|---|---|
| `spatial/topology.py` | 좌표에서 배치 구조 순수 검출 · `classify_arrangement_topology` |
| `spatial/rows.py` | y축 간격 클러스터링으로 열 검출 |
| `spatial/sorting.py` | 정렬 4종 (REQ-SPATIAL-009) |
| `spatial/naming.py` | 토폴로지 버킷 → 폐쇄 어휘 그룹명 |
| `spatial/vocabulary.py` | 한국어 배치 어휘 → 결정적 배치 |
| `spatial/pointing.py` | 무빙헤드를 3D 좌표로 조준 |
| `spatial/mib.py` | Move In Black — 어두울 때 미리 조준 |
| `spatial/position_moods.py` | 연출 의도 → 기본 포지션 추천 |
| `spatial/position_cuesheet.py` | 절별 무드 → 프리셋 참조 큐 |
| `spatial/position_fx.py` | 저장된 FX 포지션 프리셋을 **소비하는** 시퀀스 |
| `arrange_fixtures` · `create_arrangement_groups` | 등재 도구 |

## ③ 프리셋 자산 — 6축 × 10종

각 축에 **저장 + 재생성** 트리거가 쌍으로 있다. 「다시 잡아줘」는 이미 저장된 자리를
**제자리에** 다시 쓴다 — 큐가 프리셋 번호를 참조하니 새 자리면 재생성이 성립 안 함.

| 축 | 부르는 말 | 10종 |
|---|---|---|
| BASIC 포지션 | 기본/베이직 + 포지션 | Home · Wall · Audience · Center · Vocal DSC · Fan Out · Fan In · Cross · Ring Out · Ring In |
| BASIC 컬러 | 기본 + 컬러/색 | Warm White · Cool White · Red · Amber · Yellow · Green · Cyan · Blue · Magenta · Lavender |
| BASIC 딤머 | 기본 + 디머/밝기 | Dim 10~90 · Full |
| 컬러 페이저 | 멀티컬러/컬러 이펙트/컬러 페이저 | Breathe Warm · Breathe Cool · Chase RB · Chase CM · Wave CM · Wave WA · Rainbow · Pulse RY · Duo GL · Slam RW |
| 디머 페이저 | 디머 이펙트/디머 페이저 | Breathe Soft · Breathe Deep · Pulse Hard · Pulse Half · Wave Soft · Wave Full · Ripple · Flash Accent · Alt Half · Slam Run |
| 콤보 페이저 | 콤보/복합/컬러디머/드롭 프리셋 | Club Duo · Finale Slam 등 (All 1 풀) |
| FX 포지션 | 이펙트 + 포지션 | sweep · flyout · circle · ballyhoo · wave (5종) |

정본 SPEC: `COLORPRESET-001` · `PRESETGUARD-001/002` · `PRESETIDEM-001`
동형 안전장치: 점유 검사 → 덮어쓰기 카드 → 룩별 독립 번들 → 페이지드 되읽기 산술 → 라벨 가족 재생성

🔴 **축 충돌 판정** (`session.py:1826`) — 「포지션 빼고 컬러 스윕」처럼 배제 문장이
배제하려는 낱말을 쓰면 낱말 판정이 뒤집힌다. 3라운드 실측 끝에 어휘 판정을 버리고
**카드 한 장으로 축 확정**. 근거: 누출은 되돌리기 어려운 콘솔 쓰기, 과잉은 질문 한 장.

## ④ 이펙트·페이저

| 기능 | 도구 |
|---|---|
| FX 검색 | `find_fx` · `fx/library/` (dimmer 5 · color 3 · movement 11) |
| FX 적용 | `instantiate_fx` — 🔴 기본은 시퀀스 생성, **`destination=preset`** 필요 |
| **FX 작성** | `compose_fx` — 라이브러리에 없는 페이저를 인자로 만든다 |
| 연구 14편 | `docs/research/ma3-effects/` — phaser·recipe·MATricks 에디터 |

⚠️ Recipe·MATricks 에디터 연구가 있는데 우리는 Phaser 만 쓴다.

## ⑤ 룩·씬

`find_looks` · `instantiate_look` · `find_scene` · `compile_scene`(룩+FX=씬) ·
`prepare_busking` · `plan_executor_layout`
룩 라이브러리: ballad 7 · edm 9 · rock 8 · worship 8

## ⑥ 큐·시퀀스 — 🔴 연출 표준이 여기 있다

**정본**: `docs/proposals/song-lighting-design-standard.md` (v0.4)
> 「효과의 나열」이 아니라 **조명감독이 타임라인 위에서 내리는 판단**을 기계 검사 가능한 규칙으로.

**철학 4조**: ①조명은 곡의 구두점 ②긴장-해소 모델 ③헤드룸 보존 ④하나의 완벽한 아이디어

**11절**: 타임라인 문법 · 음악 프로파일 · 리그 프로파일 · 조명감독 의도 계층 ·
에너지 모델 D1~D5 · 축별 규칙 5종 · 대비·변화율 · 전환 타이밍 · 장르 프로파일 ·
입력 계약 · 콘솔 능력 경계

**린트 L1~L14 — `server/design/lint.py` 에 전부 구현됨**, `lint_sheet()` 로 호출,
`song_cue_composer` 를 통해 실제 소비된다.

| # | 검사 |
|---|---|
| L1 | 구간당 큐 ≥1 |
| L2 | D 단조성 — D↑인데 키층 디머↓ |
| L3 | 헤드룸 — D5 이전 전축 최대 동시 사용 |
| L4 | 포지션 폭이 D 상승 경계에서 축소 |
| L5 | 팔레트 크기 > 5 또는 곡 중 이탈 |
| L6 | 키층 소등 + 보컬 구간 |
| L7 | 백층 > 키층 (실루엣 태그 없이) |
| L8 | 블랙아웃 > 3회 |
| L9 | 스냅(0s)이 히트/드롭/버튼 외 |
| L10 | 동시 이펙트 축 > D레벨 예산 |
| L11 | 이펙트 Speed가 BPM 배수 격자 밖 (±10%) |
| L12 | 인접 큐 변화 축 > 2 |
| L13 | 동일 3중 조합 연속 |
| L14 | 블라인더 예산 초과(>2회) 또는 D5 외 사용 |

**린트는 차단이 아니라 보고다** — 연출은 규칙을 의도적으로 깰 수 있고 그 결정은 운영자가 카드에서 내린다.

`design/` 9모듈: `energy`(D1-D5 축 예산) · `profile`(곡 정체성) · `rig`(리그 조건) ·
`interview`(5문항) · `lint`(L1-L14) · `song_cue_composer` · `song_plan` · `position_sheet`

LX-SEQ 시트 경로: `import_lxseq_cues` · `lxseq/cue_parser.py` · `cue_mapper.py`
큐 되읽기: `web/cue_monitor.py` `_cue_items` (번호·이름까지, 내용은 안 옴)

## ⑦ 안전 게이트

①문법(`grammar.py`) → ②위험분류(`classify.py`) → ③사람 승인(`approval.py`)
`Store Preset`·`Store Cue` 는 위험 분류라 승인 없이 무조건 차단.
백업 · 라이브 잠금 · 감사로그(JSONL 90일) · `preshow_check`(OSC·시퀀스·프리셋 무결성 + 알려진 함정 3건)
인계 문서: `build_handover_pack` — 패치시트+큐시트+프리셋목록+매직시트

## 🔴 두 경로가 같은 풀에 쓴다 — 미측정

```
시트 경로   RIG 팩 CSV      → import_lxseq_presets → 콘솔
대화 경로   「기본 컬러 잡아줘」 → session.py BASIC   → 콘솔
```
표준 10색을 올린 뒤 시트 COL 7건을 올리면 어떻게 되는지 **아무도 안 쟀다.**
덮어쓰기·번호 충돌 가능성. 공존하는 이상 언젠가 터진다.

## 룰북 — 능력을 앱에 알려주는 자리

```
server/rulebook/assets/v2.4.2/  7장 45KB (약 23K 토큰)
00_grammar · 10_object_model · 20_korean_terms · 30_plugin_patterns
31_choreography_patterns · 32_spatial_design · 33_effect_editors
```
`assembly.py` 가 `.md` 를 **정렬 순서로 자동 조립** → `serve.py:301` → 세션·오케스트레이터.
**파일을 넣기만 하면 시스템 프롬프트에 들어간다. 코드 변경 0.**

⚠️ 프롬프트 캐시 계약(`cache_control: ephemeral`) — 파일 추가 시 **일회성 무효화**.
자주 바뀌는 내용(진행 상황·미머지 PR)은 넣지 말 것.

## 아직 안 본 것 (다음 우선순위)

1. **`docs/curriculum/` 17편 532KB** — 제일 큰 덩어리, 조명감독 지식 체계 가능성
2. `docs/handoff/` 7편 — `COLOR_PHASER_SEQUENCE` 가 참조하는 `2026-08-16-session-handoff.md`
3. Recipe·MATricks 에디터 연구가 `compose_fx` 에 반영됐는지
4. L1~L14 와 LX-SEQ 스펙 검증 15항목의 정확한 겹침
5. 등재 도구 38개 중 **한 번도 안 불러본 것**의 수
6. 두 경로의 풀 충돌 (위)

## 오늘 배운 것 — 반복하지 말 것

- **직접 import 만 보고 「안 불린다」고 넓히지 마라.** `lint`·`energy` 를 그렇게 오판했다가 `song_cue_composer` 경유를 발견해 정정했다.
- **코드만 보고 「없다」고 하지 마라.** 자산의 본체는 `docs/` 였다.
- 「없다」 전에 훑을 자리: 0 메모리 → 1 입력 포맷 정본 → 2 기존 SPEC → 3 등재 도구 → 4 코드 → **5 docs/**
