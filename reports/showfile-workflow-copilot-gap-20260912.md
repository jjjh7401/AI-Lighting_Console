# 쇼파일 end-to-end 프로세스를 코파일럿에 적용하기 — 기존 기능 대조와 개선 제안

- 대상 문서: `docs/research/ma3-effects/20-mblightarts-end-to-end-showfile-process.md` (884줄)
- 대조 기준: main `0c0237b`, 2026-09-12
- 방법: 읽기 전용 재고조사 5갈래 + 오케스트레이터 직접 검증(grep·파일 판독)

## 한 줄 결론

영상 12단계 중 **8단계는 이미 구현돼 있다.** 진짜 공백은 3곳이고, 그중 가장 큰 공백(픽셀 장비)은 **우리 실기 리그에 해당 장비가 없어** 지금 만들 이유가 없다. 당장 값이 나오는 것은 새 기능이 아니라 **이미 있는 도구를 영상의 순서로 꿰는 런북 하나**다.

## 1. 규모 실측 — 무엇을 상대로 대조했나

| 항목 | 값 | 출처 |
|---|---|---|
| 생산 코드 | 약 10만 줄 / 25개 패키지 | `wc -l server/*/*.py` |
| 최대 단일 파일 | `server/orchestrator/tools.py` 12,532줄 | 직접 판독 |
| 코파일럿 도구 | 38개 | `build_toolset()` 전수 열거 |
| SPEC | 55개 (완료 25 · 진행 9 · 초안 16 · 기타 5) | `.moai/specs/` 전수 |
| 곡→큐 경로(`server/looks/`) | 5,250줄 — 전체의 5% | 같은 명령 |

곡→큐 경로는 저장소의 일부다. 영상이 다루는 **쇼 셋업** 영역은 `vwx`(1만 줄) · `lxseq`(5.4천) · `spatial`(4.5천) · `prechk`(4천) · `safety`(3.3천)에 이미 들어 있다.

## 2. 영상 12단계 × 현 구현 대조

| # | 영상 단계 | 현 구현 | 상태 |
|---|---|---|---|
| 1 | Stage 분석 | `vwx/reader.py`·`mvr.py`·`columns.py`·`address.py`·`rig.py:450 build_designed_rig`, 도구 `precheck_vectorworks_diff` | 있음 |
| 2 | Patch | `patch_fixtures`(주소 재확인→FID 배정→되읽기 검증), `vwx/patchplan.py:670`+`luagen.py:77`(사람 실행), `lxseq/mapper.py:572` | 있음 |
| 3 | Hybrid group | `classify_arrangement_topology`·`create_arrangement_groups`, `groupgen/write.py`(점유 슬롯 정적 차단) | 있음 |
| 4 | Pixel tube group | — | **없음** |
| 5 | Tilt pixel bar / 픽셀 마스터 그룹 | — | **없음** |
| 6 | Position preset | `spatial/pointing.py` `aim_pan_tilt`·`fan_pan_tilt`·`fan_chain`·`position_preset_store_commands`, `spatial/presets.py`, PRESETGUARD-001 덮어쓰기 가드 | 있음 |
| 7 | Gobo / Focus | Focus 축은 Zoom 한정. Gobo 는 룩 스키마에서 제외(`looks/schema.py:56`), 흔적은 `lxseq/preset_parser.py` 뿐 | 부분 |
| 8 | Beam preset (strobe·prism·iris·zoom) | Iris·Zoom 만 범위 내. Prism·Shutter·Frost·Focus 는 **콘솔이 거절한 실측 결과**로 영구 제외(`looks/schema.py:16-19`) | 부분 |
| 9 | Color preset | `presets/store.py`, `lxseq/preset_mapper.py`, COLORPRESET-001(초안) | 있음 |
| 10 | Regen all | 매크로 **저작·실행** 기능 없음. `prechk/macro.py` 는 응답확인 전용 | **없음** |
| 11 | Layout cleanup / Feature Grid | 콘솔 Layout 객체·Feature Grid 경로 0건 | **없음** |
| 12 | Override / MIB | MIB 는 `spatial/mib.py` 에 완성(CUETIME-001, 실기 측정 완료). Override 슬롯·Stop IFX/PFX 는 0건 | 부분 |

## 3. 진짜 공백 — grep 0건으로 확인한 것

| 공백 | 검증 명령 | 결과 |
|---|---|---|
| 픽셀 마스터 그룹 · 서브픽스처 · simrik | `grep -ril "subfixture\|sub_fixture\|pixel.master\|simrik" server` | 0건(테스트 제외) |
| Feature Grid · Generate Layouts | `grep -ril "featuregrid\|feature grid\|feature_grid" server ui docs/proposals` | 0건 |
| 매크로 저작 | `prechk/macro.py` 판독 | 응답확인 매크로만 |
| Override 룩 · Stop IFX/PFX | `grep -ril "stop ifx\|override look\|solo spot" server` | 0건 |

이름 충돌 주의: `server/looks/layout.py` 가 있지만 이것은 **익스큐터 배치**(시퀀스를 몇 페이지 몇 칸에 앉힐지) 플래너이고, 영상의 콘솔 Layout View 와 다른 물건이다. 이 혼동은 `SPATIAL-001` §A.2/A.3 가 이미 명문으로 갈라놨다 — 「layout」은 MA Layout pool 만 가리키고, executor layout 은 BUSKWIZ 소유의 다른 축이다.

### 3.1 「없음」의 종류가 셋이라는 것 (SPEC 재고조사 후 정정)

grep 0건은 셋을 구별하지 못한다. SPEC 을 읽고 나서야 갈렸다.

| 공백 | 실제 성격 |
|---|---|
| 픽셀 · 서브픽스처 | **의도적 배제.** `SPATIAL-001/spec.md:195-197` 이 "멀티셀 픽스처의 셀 단위 좌표·레이아웃 일체" 를 Out of Scope 로 못박고 **"v1 의 공간 단위는 픽스처 1대"** 라고 선언했다. 선례 플러그인(`gabe927/gma3-subfixture-layout`)까지 적어놨다 |
| 콘솔 Layout pool | **이미 부분 범위 안.** `ASSUMPTION-55`(판독 — children 반복으로 PositionX/Y) · `ASSUMPTION-56`(기록 — `Set Layout <l>.<e> "PositionX" <v>`, 포럼 확인 수준) 로 들어와 있고 DEFERRED 상태다. 「조사 선행」이 아니라 **조사가 절반 돼 있다** |
| Feature Grid | **논의된 적 자체가 없음.** 코드·SPEC·research 어디에도 0건. 배제도 아니고 공백도 아닌, 미논의 |

### 3.2 🔴 곁가지로 나온 열린 구멍 하나

`WRITEGATE-001` §D 가 「Layout 요소 좌표 기록」을 Out of Scope 로 두면서, 그 명령 형태가 **오늘도 안전 게이트에서 `safe` 로 분류되는 닫히지 않은 경로**라고 명시 기록해뒀다. 즉 지금 누군가 그 문형을 보내면 승인 없이 통과한다. Layout 축이 DEFERRED 라 함께 이연됐을 뿐, 구멍은 열려 있다. 영상 11단계를 건드리기 전에 **이것부터 닫는 게 순서다.**

## 4. 가장 중요한 발견 — 픽셀 공백은 지금 메울 이유가 없다

영상 작업량의 큰 몫이 픽셀 장비(Astera Titan 튜브, GP X4 틸트 바)인데, **우리 실기 리그에 그 장비가 없다.**

기록된 리그(`LXSEQ-001/research.md:28`)는 12그룹 86대이고 장비 타입 8종은 전부 비픽셀이다 — ETC S4 LED, Elation CUEPIX Blinder WW2, Martin Atomic 3000 LED, Look Unique 2.1(헤이저), Robe MegaPointe, Robe Spiider, Martin MAC Aura XB, Martin RUSH PAR 2.

`astera`·`GP X4`·`titan tube` 를 저장소 전역에서 찾으면 VWX **테스트 픽스처 파일**에만 나온다(`server/tests/fixtures/vwx/`). 즉 도면 파서가 그런 이름을 읽을 수는 있으나 우리 쇼의 장비는 아니다.

→ 영상 4·5·7.1·7.2 절(픽셀 그룹·픽셀 마스터·dim default)은 **장비를 실제로 들이기 전까지 착수 대상이 아니다.** 이 영역에 코드를 쓰면 검증할 장비가 없어 실기 0회로 남는다.

## 5. 영상과 기존 SPEC 이 충돌하는 지점

| 영상이 요구 | 우리 SPEC 의 결정 | 처분 |
|---|---|---|
| 3.1 「기존 패치 전부 삭제 후 재패치」 | AUTOPATCH-001: **생성만**, 기존 픽스처 수정·삭제·재주소는 명시 제외 | SPEC 이 옳다. 삭제는 되돌릴 수 없고 백업 복원 경로도 별도 미구현 |
| 4.x 그룹 저장 후 멤버십 검증 | GROUPGEN-001: 멤버십 재조회는 **원리적 불가**(MA3 미노출). 복원 조건까지 기재 | 영상 절차를 그대로 옮기면 그 벽에 부딪힌다. 대안은 계획·승인 시점 검증 |
| 6.2 Auto pos 의 「override all positions」 | PRESETGUARD-001: Position 프리셋 덮어쓰기 가드 | 가드 유지. 덮어쓰기는 감독 승인 1건으로 올려야 함 |
| 6.3·6.4 Gobo·Prism 프리셋 | `looks/schema.py`: Gobo 는 SPEC D절 제외, Prism·Shutter 는 **콘솔 거절 실측** | 프리즘류는 재시도해도 같은 결과. 고보는 별도 SPEC 판단 필요 |
| 6.2 포지션 프리셋 일괄 생성 | LXSEQ-003 이 `preset-pos` 8종(POS.01~08)을 **제외** — "현장 레코드 필요"이고 시트에 값 열 자체가 없음 | 포지션 값은 시트가 아니라 현장에서 나온다. 영상의 Auto pos 와 같은 결론 |
| 11 레이아웃에 프리셋 얹기 | BUSKWIZ-001 M0 실측: 「프리셋을 익스큐터에 직접 얹는 문법」이 저장소 전체 **0건** → DESCOPE 확정. 우회로(시퀀스 만들어 배정)는 §D 가 금지 | 영상 11단계 일부는 문법이 없어서 못 한다. 장비나 의지 문제가 아니다 |

## 6. 제안 — 어디에 무엇을 덧대나

### P1. 쇼 셋업 런북 (신규 코드 0)
영상 12단계를 기존 38개 도구의 호출 순서로 적은 런북을 만든다. 1·2·3·6·9·12단계는 도구가 이미 있고, 없는 단계는 「감독이 콘솔에서 직접」으로 표시한다. 비용이 가장 싸고 즉시 값이 난다.
- 대는 곳: `docs/proposals/` + `server/orchestrator/` 라우팅
- 선행: 없음

### P2. 매크로 저작·실행 (작고 효과 큼)
`regen all`·`auto pos`·`dim default` 가 전부 콘솔 매크로 실행이다. 지금은 실행 수단이 없어 이 세 단계가 통째로 수동이다.
- 대는 곳: `presets/store.py` 옆에 매크로 명령 빌더, `safety/classify.py` 에 매크로 실행 위험 분류
- 주의: 매크로는 내용이 콘솔 안에 있어 우리가 못 읽는다. `safety/expand.py` 의 「확장 불가는 보류」 원칙에 그대로 걸린다 — 승인 문구에 「내용 미확인」을 명시해야 한다

### P3. Override 섹션 (중간)
솔로 스팟·하이라이트는 실기에서 자주 쓰는데 0건이다. MIB 는 이미 있으니 절반은 깔려 있다.
- 대는 곳: `spatial/mib.py` 옆, `looks/` 의 룩 선택과 연결
- 선행: Stop IFX/PFX 명령 문법 확인(실기 1회)

### P4. Layout 축 — 구멍 먼저, 기능은 그다음
순서가 바뀌었다. §3.2 의 열린 게이트 경로(`Set Layout … "PositionX"` 가 `safe` 로 통과)를 닫는 것이 먼저다. 그건 기능 추가가 아니라 **이미 열려 있는 승인 우회를 막는 일**이라 영상과 무관하게 값이 있다. 그다음에 `ASSUMPTION-55/56` 을 실기로 판정하면 Layout 축이 열린다.
- 대는 곳: `safety/classify.py` 의 분류 규칙
- Feature Grid 는 여기에 얹히는 그다음 층이고, 지금은 논의된 적도 없는 미개척지다

### P5. 픽셀 지원 (보류 — 근거 둘)
1. 우리 리그에 그 장비가 없다(§4).
2. `SPATIAL-001` 이 **v1 공간 단위를 「픽스처 1대」로 명시 배제**했다. 재론 조건도 안 걸어놨다.
즉 「아직 안 만든 것」이 아니라 「안 만들기로 정한 것」이다. 뒤집으려면 장비 도입 + SPEC 재론 둘 다 필요하다.

## 7. 안 잰 것

- `interview.py`(1,165줄)·`song_plan.py`(1,087줄)·`song_cue_composer.py`(872줄) 내부 로직은 헤더만 확인
- 영상은 자막 기반이라 pool 번호·클릭 위치가 프레임 단위 실측이 아니다(문서 자체가 명시)
- Override·Feature Grid 의 「없음」은 grep 0건이지 콘솔이 그 기능을 안 준다는 뜻이 아니다
- **리그 기록이 하나가 아니다.** §4 의 86대는 `LXSEQ-001` 의 패치 CSV 기준이고, `GROUPGEN-001` 은 별도의 이종 리그 39대(Robe MMX Spot 19 + LEDBeam 350 20)를 쓴다. 픽셀 부재 판정은 전자 기준이며, 후자에도 픽셀 장비는 없다
- 이 영상 문서(`20-…`)를 포함해 `docs/research/ma3-effects/17~20` 은 코드·SPEC 인용 **0건** — 아직 아무 데서도 소비되지 않은 신규 리서치다. 이 리포트가 20번의 첫 소비다
