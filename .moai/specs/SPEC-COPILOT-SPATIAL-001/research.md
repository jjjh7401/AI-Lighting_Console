# SPEC-COPILOT-SPATIAL-001 — 조사 기록 (research)

status: draft (v0.1.0, 2026-08-03) · Tier L

**조사 범위**: base `origin/main` = `3176900` 트리 직접 판독 + 코디네이터 인수 웹 조사(MA help/포럼/선례 오픈소스). 본 세션에서 라이브 콘솔 접근은 없었다 — **모든 콘솔 사실은 인수 조사이거나 선행 SPEC의 실측 기록**이며, 본 세션이 새로 측정한 것은 없다. 특히 **웹 인수 조사는 타 버전(2.x 계열) 실증이고, 설치된 onPC 2.4.2에서의 프로퍼티 이름 대소문자·동작은 전건 미검증**이다(M0의 존재 이유).

**인용 규율**: 줄번호는 이 세션 기준이며 마일스톤 착수 직전 재실측한다. 근거 등급: `[코드]` · `[문서]` · `[측정]`(이 세션의 저장소 계측) · `[실측 전재]`(선행 SPEC 라이브 기록) · `[인수-웹]`(코디네이터 검증 웹 조사) · `[미확정]`.

---

## §1. 인수된 웹 조사 — 콘솔의 공간 데이터 표면 `[인수-웹]`

본 SPEC의 설계 전제다. 출처는 말미 Sources에 전건 나열한다.

### §1.1 Layout pool (2D)

- `DataPool().Layouts` 아래 레이아웃 → 요소(element). 요소는 할당 오브젝트(픽스처/그룹/매크로) + `PositionX`/`PositionY`(+크기/회전)를 가진다.
- **요소는 요소 번호·이름으로만 주소 가능하다 — 픽스처 id로 직접 주소할 수 없다**(포럼 68138). 픽스처→(x,y) 맵은 Lua에서 `layout:Children()` 반복으로만 구축된다.
- 커맨드라인 기록 실증: `Set Layout 1.2 "PositionX" 500` (포럼 3991 — moderator 확인).
- 프로그래매틱 레이아웃 생성 선례: gabe927/gma3-subfixture-layout (오픈소스 플러그인 — 동작 실증).
- **GUI가 표시하는 레이아웃을 바꾸는 Lua API는 없다**(포럼 68421). 화면 전환은 사용자 손에 남는다 → spec.md §D 제외.

### §1.2 패치 3D 무대 좌표 (정본 후보)

- `Root().ShowData.LivePatch.Stages:Children()[s]:Children()[g]:Children()[f]`의 `.posx`/`.posy`/`.posz`/`.rotx`/`.roty`/`.rotz` — Lua에서 **판독·기록 모두** 실증(포럼: `.posz = 5.0` 설정으로 픽스처가 3D에서 이동).
- 실세계 미터 단위, 3D 뷰어가 직접 반영. 모든 패치된 픽스처가 가진다 — Layout pool과 달리 존재가 보장된다 → **정본 출처**(spec.md §A.3).
- 선례: leonreucher/grandma3-patch2pdf — 패치 데이터 판독 오픈소스 실증.
- **경고**: 위 프로퍼티 이름의 정확한 대소문자는 설치본에서 미검증. MA3의 콘솔 `ok`는 미지 이름에 관대할 수 있다(§7-1) — M0 날조 대조군 의무.

### §1.3 공간 이펙트의 MA3 원리 — 방향은 선택 순서다

- 웨이브 방향을 정하는 것은 **선택 순서/선택 그리드**이지 좌표가 아니다. 페이저 `Phase 0…360`은 그리드 X축을 따라 퍼진다. MAtricks(`XWidth`/`YWidth`, Wings, Blocks)가 분포를 재성형한다.
- `Grid store`로 커스텀 그리드를 그룹에 영속화할 수 있다는 조사가 있으나 — **룰북 근거 0건(§4)·라이브 실측 0건** → ASSUMPTION-59, v1 주경로 아님.
- **"레이아웃 좌표 순서로 그리드를 만든다"는 내장 기능은 없다** — 좌표 판독→정렬→그 순서 선택이 본 앱의 부가가치 자리다.

---

## §2. rig context 현황 — 좌표 축이 0이다 `[코드]`

- `server/orchestrator/tools.py:150-161` `DEFAULT_RIG_CONTEXT_PATHS` — **10경로**(fixture_types / fixtures / groups / sequences / preset_pools / macros / plugins / pages / matricks / worlds). 위치 데이터 경로 없음. 주석이 규율을 명시한다: *"Every path here was read back from a live onPC 2.4.2 … Guessed paths are how 'Patch/Fixtures' and 'DataPool/Presets' shipped dead"* — 경로 발명 금지 + **stage slot 1 전제**(ASSUMPTION 주석).
- `tools.py:404-430` `rig_object` — 픽스처 스냅샷은 `{no, name}`(슬롯 미확립 시 `{name}`만). **좌표·클래스 축 없음.** docstring이 슬롯≠FID 규율을 소유한다: *"a number the responder READ, never one this code counted"*.
- `tools.py:494` `collect_rig_sections` + `:173` `RIG_DRILLDOWN_QUERY_CAP = 16` + `:455-491` 드릴다운 — 캡 도달 시 `drilldown_capped` 신호. **왕복 예산이 콘솔 질의 설계의 기존 규율**이다 — 30대 xyz를 prop 루프로 읽으면 90왕복으로 이 규율과 정면 충돌 → plan.md §F D-1의 결정 재료.

## §3. 응답기 확장 지점 `[코드]`

- `console/lua/copilot_responder.lua:876` `M.handle_request` — `ping`/`state`/`prop`/`exec`/`deploy` 5분기, 정확 문자열 일치. 신규 동사는 가산 추가 자리(INTROSPECT-001 research §3.1과 동일 판독).
- `:643` `build_prop_result` — **기존 판독의 문**. 경로 해석이 범용(root alias: DataPool/Root/ShowData/Patch)이므로, **LivePatch 경로의 단건 판독은 Lua 무변경으로 시도 가능**하다 — M0의 READ 프로브가 기존 `prop`부터 시도하는 근거.
- `PROTOCOL.md` §2(:55-70) — 동사 표. 신규 동사 채택 시 이 표 + §4 kind 절 + Revision note가 EXTEND 대상.
- 회신 예산 `CONFIG.max_payload = 1900` — 초과는 `cmd_keyword` **조용한 드롭**(pcall 성공 보고). `server/tests/test_lua_responder_payload_budget.py`가 산술 고정 선례.
- **버전 충돌 주의**: SPEC-COPILOT-INTROSPECT-001(draft)이 `M.VERSION` 1.6.0을 예약했다 — plan.md §F D-5.

## §4. 룰북 현황 — 실좌표 개념 전건 0 `[코드]`+`[측정]`

- `server/rulebook/assets/v2.4.2/` 5개 파일: `00_grammar` / `10_object_model` / `20_korean_terms` / `30_plugin_patterns` / `31_choreography_patterns`.
- `31_choreography_patterns.md`가 페이저(`:69` `Attribute 'Pan' At Phase 0 Thru 360` — *"fan the phase across the selection => a wave"*)와 MAtricks(`:82-94`, `Store MAtricks 1` 포함)를 **(validated)** 표시로 커버한다. 그러나 **`posx`/`PositionX`/`Layout`/`Grid` grep 전건 0** — 실좌표·배치 개념이 룰북에 전무하다 `[측정]`.
- `server/rulebook/assembly.py:62-63` — **정렬 파일명 순서** 조립. `32_spatial_design.md`는 31 뒤에 자연 배치된다.
- `server/tests/test_rulebook.py:1-33` — 접두 byte-stable(5회 조립 바이트 동일) + per-show 값 부재 패턴(REQ-MVP-007/008). 신설 파일도 같은 계약을 상속한다.
- **validated 규율**: 31의 커맨드는 라이브 검증 후 룰북에 실렸다(저장소 관례 — 39/39 라이브 OK 후 룰북 반영). 32도 같은 규율 — 미검증 문법을 싣지 않는다(REQ-SPATIAL-016).

## §5. look/fx 통합 지점 `[코드]`

- `server/looks/roles.py:1-16` — **포지션 롤 6종 폐쇄 어휘**(백라이트/프론트 등, 한국어 주명칭 + 별칭 + 매핑 힌트). 공간 조건은 이 롤 매칭의 **이웃 축**이다 — 롤은 "무엇(기능적 위치)"을, spatial은 "어디(좌표)"를 답한다. v1은 롤 어휘를 수정하지 않는다(PRESERVE).
- `server/fx/instantiate.py:476` — 선택 발화 선례: `[_DESTINATION, _CLEAR, f"Group {group}"]` — bare 번호형 그룹 선택. 공간 정렬 선택은 이 자리의 **fid 사슬 등가물**이다(가산 선택 문법은 M0 판정 대상).
- 매칭 규율 선례: `server/looks/matching.py` · `server/fx/matching.py` — 한국어 조사 처리·폴백 3종·동점 None·결정론(REQ-SPATIAL-015가 미러).

## §6. executor layout ≠ spatial — 어휘 충돌 지점 `[코드]`

- `server/looks/layout.py:1-22` — *"Executor layout planner — sequence -> executor -> label wiring"*. 순수 모듈, 시퀀스→익스큐터 배치.
- `server/orchestrator/layout_occupancy.py:1-15` — 그 계획의 라이브 점유 조회 래퍼.
- **둘 다 픽스처 공간 배치와 무관하다.** 최근 머지(상류 어휘 확장 ①·⑦·② 배치)에 포함된 모듈이므로 이름 충돌 시 혼동 위험이 실재한다 → 본 SPEC은 `spatial` 접두 통일 + 두 모듈 PRESERVE(spec.md §A.2, §D).

## §7. 안전 계층 — WRITE가 소비할 것 `[코드]`

- `server/safety/backup.py:1-26` — showfile 백업 3규칙(세션 시작 / 주기 / **위험 커맨드 직전** ③), 실패 시 `BackupError`로 실행 차단(fail-safe). **restore SEND 경로는 의도적 부재(T-B2 scope cut)** — 스냅샷을 콘솔로 되돌리는 길이 없다. ⇒ WRITE의 복원은 showfile 복원이 아니라 **원좌표 재기록 번들**이어야 한다(REQ-SPATIAL-020의 형상 근거).
- `server/safety/blacklist.yaml` — `Store /overwrite` 등 봉쇄. `Delete`도 블랙리스트(선행 SPEC 확립) — 단 **좌표 기록의 revert는 재기록이므로 Delete가 필요 없다**(M0 정리 부채 없음의 근거).
- 게이트 단일 관문: `run_commands` → `gate.screen()` — 커맨드라인 기록 채널(D-2 (a))이 채택되면 기존 스크리닝·감사·승인이 그대로 적용된다. Lua 대입 채널(D-2 (b))은 이 관문 밖의 **신규 쓰기 표면**이라 비용이 크다.
- 경계 집행: `server/tests/test_architecture.py`(전역 import 스캔 — 신규 패키지 자동 포섭) · `test_looks_boundary.py`(AST 스캔 선례).

## §8. 선행 실측 상속 `[실측 전재]`

| 사실 | 원출처 | 본 SPEC에의 함의 |
|---|---|---|
| 존재하지 않는 `/CueOnlyy`가 `ok`+저장 — `ok`·재조회 비변별 | SCENE-001 M0 (`progress.md §E.2`) | 프로퍼티 이름 축에도 같은 관대함이 있을 수 있다 — **날조 대조군 의무**(REQ-SPATIAL-026 (c)) |
| 프로브 A/B 표적 공유로 대조군이 표적 점유 | SCENE-001 M0 승계 결함 | **프로브별 표적 분리**(REQ-SPATIAL-026 (d)) |
| 실행기 실번호 = i+100, 무오류 오발 | SHOWUI-001 실측 | 슬롯≠FID — 좌표 맵 식별자 규율(REQ-SPATIAL-007) + ASSUMPTION-57 |
| 회신 1900 초과 조용한 드롭 (스윕 2000 전달 / 2100 드롭) | 응답기 CONFIG 주석 (2026-07-24 실측) | 벌크 회신 산술 고정 테스트(ASSUMPTION-60) |
| 번들 줄당 ~66ms | BUSKWIZ 실측 전재 | 선택 사슬 30줄 ≈ 2s — 발화 예산 산술(design.md §7) |
| `Cmd()` OK ≠ 효과 | FXLIB M0 | 기록 검증은 재조회로(REQ-SPATIAL-021) |

## §9. 후속 SPEC 후보 (본 SPEC이 생성하지 않는다)

1. **회전축 연출** — rot* 기록·활용. M0가 회전 판독까지 확인한 경우에만 성립.
2. **Gridstore 영속화** — M6 측정이 GO인 경우에만. 매 발화 선택 순서의 성능이 문제가 될 때 재검토.
3. **서브픽스처 공간 축** — 멀티셀 웨이브. gabe927 선례 참조.
4. **공간 조건 룩 롤 확장** — roles.py의 기능적 롤에 좌표 조건을 결합하는 축(예: "y가 가장 뒤인 행 = 백라이트 후보"). v1은 두 축을 분리 유지한다.

---

## Sources (코디네이터 인수 웹 조사 원출처)

- https://help.malighting.com/grandMA3/2.2/HTML/lua_objectfree_selectedlayout.html — SelectedLayout Lua 오브젝트
- https://help.malighting.com/grandMA3/2.3/HTML/layouts.html — Layout pool 공식 문서
- https://forum.malighting.com/forum/thread/3991-how-do-i-set-layout-element-properties-with-a-command/ — `Set Layout 1.2 "PositionX" 500` (moderator 확인)
- https://forum.malighting.com/forum/thread/68138-set-property-layout-but-direct-to-fixture-number-instead-of-layout-object-number/ — 요소는 요소 번호로만 주소 가능
- https://forum.malighting.com/forum/thread/68421-change-selected-layout-via-lua/ — GUI 레이아웃 전환 API 부재
- https://github.com/leonreucher/grandma3-patch2pdf — 패치 데이터 판독 선례
- https://github.com/gabe927/gma3-subfixture-layout — 프로그래매틱 레이아웃 생성 선례
