# 새 방향 인계 — 만들어 둔 것을 다시 만들지 않기 위한 지도

> 기준: `origin/main f2e4d59` · 2026-09-14 · 이 문서의 숫자는 **이 세션에서 직접 잰 것**과
> **읽기 전용 조사로 확인한 것**만 담는다. 안 잰 것은 §9 에 따로 적었다.
>
> **이 문서를 읽는 목적은 하나다** — 새 방향에서 일할 때 *이미 있는 것을 다시 만들지 않는 것*.
> 무엇을 고칠지보다 **무엇을 건드리지 말지**가 먼저다.

---

## 0. 한 문단

한국어 조명 지시를 grandMA3 콘솔 명령으로 옮겨 OSC 로 실행하는 코파일럿이다. 콘솔 접촉·안전
게이트·리그 판독·큐 저장·런북 UI·데스크톱 배포까지 **이미 작동한다**. 막힌 곳은 단 하나,
**조명 연출 기획**의 품질이다. 새 방향은 그 한 층만 갈아끼우고 나머지는 전부 재사용한다.

## 1. 왜 방향을 바꾸나 — 2026-09-14 감독 판단

감독 지시 원문: *"코파일럿 앱이 조명연출 기획을 하는데 한계가 있다는걸 인정하고 새로운 방향을
잡을수 있도록 같이 논의해보"*, 그리고 *"언제까지 이렇게 하나하나 테스트하고 수정하고 할거야?
근본적인 문제가 있는거 아니야?"*

근거가 된 실측(이 세션, `Club Diver.mp3` 141초를 앱 경로로 끝까지 태운 타임라인):

| 잰 것 | 값 | 정본이 말하는 값 |
|---|---|---|
| 앱이 만든 구간 수 | **39개** | §9 "구간 수(중앙값 10)에 맞춘 10 부근" |
| 구간 하나의 길이 | 중앙값 **3.4초 = 2마디** | §9 "프레이즈 단위 4~8마디마다" |
| 그중 chorus 로 판정된 것 | **25개** | §7.1 사다리는 **chorus 1·2·3** 세 회차 전제 |
| 주 장비 색 | 39구간 전부 `블루` 한 색 | — |
| 효과 (t405 고치기 전) | 4종, 그중 26구간이 동일 | — |

### 뿌리 — 구간을 세는 층

`server/audio/analyze.py` 의 `analyze()` 는 **음량이 계단처럼 뛰는 지점**을 찾는다. 유일한
개수 제한은 `_MIN_SEGMENT_SECONDS = 3.0`(:44) 하나다. 클럽 트랙은 드럼 필·필터 스윕마다
음량이 뛰므로 141 ÷ 3.4 ≈ 39 가 나온다. **음악의 구성이 아니라 음량의 굴곡을 센 것이다.**

그 위에서 `_infer_confirmed_role`(`server/web/session.py`)은 **세기만** 본다 — "D레벨이
최댓값이면 chorus". 39개 중 25개가 최댓값에 걸린다. 진짜 후렴 판정은 세기가 아니라
**반복**(같은 대목이 또 나오는가)으로 해야 하는데, 그 정보를 아예 만들지 않는다.

### 그래서 왜 카드가 끝없이 나왔나

역할이 25개로 뭉치면 그 역할을 읽는 **모든 축**이 같이 뭉친다. 축이 다섯이라(색·효과·질감·
밝기·위치) 같은 병을 다섯 번 고치게 된다. 실제로 그렇게 갔다:

| 카드 | 축 | 증상 | 처방 |
|---|---|---|---|
| t402 · t406 | 색 | 후렴 25회가 같은 색 | 회차 사다리 |
| t403 | 액센트 | 141초 곡에 액센트가 1개 | 회차 사다리 |
| t405 | 효과 | 26구간이 같은 효과 | 회차 사다리 |
| (다음) | 질감 · 밝기 · 위치 | 같은 모양이 남아 있다 | — |

**교훈**: 축마다 사다리를 다는 것은 증상 치료다. 구간 층을 고치면 이 카드군이 한 번에 사라진다.

---

## 2. 새 방향은 이미 문서로 있다 — SPEC-LDPLUGIN-001 / SPEC-LDEMBED-001

**🔴 가장 중요한 사실: 새 방향의 설계 문서가 이미 작성돼 있다.** 2026-09-13~14 작성,
합계 약 145KB. 다시 쓰지 마라.

```
.moai/specs/SPEC-LDPLUGIN-001/   (tier L, status draft)
  spec.md        13.8KB  REQ-LDPLUGIN-001..032
  contract.md    52.7KB  wire shape·tool·HTTP·state·hash 의 단일 원본
  design.md      15.9KB  skill 4종 · command 7종 · MCP tool 7종 · 지식 seed · 마이그레이션
  plan.md        11.1KB  구현 순서 · 파일 소유권 · 출시
  acceptance.md  17.6KB  요구사항별 증거 · go/no-go
  research.md     9.8KB  🔴 현재 코드 근거와 한계 — 재사용 지도가 여기 있다
  schemas/ examples/

.moai/specs/SPEC-LDEMBED-001/    (tier M, status draft, depends_on LDPLUGIN)
  spec.md · plan.md · acceptance.md · research.md
```

### 그 방향이 무엇인가 (한 문단)

**앱이 예술 판단을 하려는 시도를 접는다.** 외부 `lighting-director` 플러그인(Claude Code
호스트)이 음악 근거 확인 → 전곡 의도 → 큐 설계를 맡고, 코파일럿은 **context 제공 · 검증 ·
사람 승인 · 콘솔 programming · 피드백**을 맡는다. 첫 릴리스는 플러그인 단독이 아니라
`host → draft → review → approved apply → feedback` 왕복 전체다.

핵심 결정 몇 가지(전문은 `spec.md` §2):
- 외부 `LightingPlan` 이 **정본(canonical)**. 기존 `UnifiedSongLightingPlan`/`SectionDecision`
  은 내부 재사용 지점이지 무손실 wire 별칭이 아니다.
- 코파일럿만 OSC/ConsoleLink 를 소유한다. adapter 는 stdio → 인증 HTTP 만 쓴다.
- **명시적 선택을 고정 예술 정책으로 덮어쓰지 않는다** — finale 상승·후렴 변주·기본 BPM 같은
  것. 안전 hard constraint 만 유지하고 연출 조언은 advisory 로만.

### 그 SPEC 이 이미 지목한, 오늘 내가 독립적으로 재확인한 결함

`research.md` §2 가 적어둔 합성 probe 관측: *"D `[3,3,3,3,3]` → intro,chorus,chorus,chorus,
finale — D-level 기반 role 생산이 음악 근거와 다른 문제임을 드러내는 합성 관측"*.

**오늘 실제 곡으로 같은 결론에 독립적으로 도달했다**(§1). 두 경로가 같은 뿌리를 가리킨다.

### 🔴 이 SPEC 파일들은 아직 git 에 안 올라가 있다

`git status` 에서 `??` 로 뜬다. **이 인계 커밋에 같이 올린다** — 안 올리면 다음 세션이 못 찾는다.

---

## 3. 이미 있는 것 — 절대 다시 만들지 마라

### 3.1 콘솔 접촉 · 안전 (완성, 손대지 마라)

| 무엇 | 어디 | 상태 |
|---|---|---|
| OSC 송수신 — 서버 전체의 **유일한** 송신 표면 | `server/bridge/osc.py` (`OscBridge`:142, `send_command`:195) | 작동. 주소 `/copilot/cmd`·`/copilot/feedback`·`/copilot/state`, 기본 송신 127.0.0.1:8000 / 수신 127.0.0.1:9000 |
| 그 유일성을 강제하는 아키텍처 테스트 | AC-MVP-019 (import 경계) | 작동 |
| OSC 브리지의 **유일한** 프로덕션 호출자 | `server/safety/console.py` | 작동 |
| 3단 안전 게이트 | `server/safety/gate.py` (`SafetyGate`:177, `screen()`:358) | 작동. health → 문법 → 위험분류 → live-lock → 사람 승인 → lock 재확인 → 백업 → clearance |
| 문법 가드 (따옴표 균형 · MA2 문법 거절) | `server/safety/grammar.py` | 작동 |
| 위험 분류 + 닫힌 blacklist | `server/safety/classify.py`, `blacklist.yaml` | 작동 (v3) |
| expand-or-hold (확인 불가 참조는 보류) | `server/safety/expand.py` | 작동 |
| LiveLock · 승인 카드 | `server/safety/lock.py`, `approval.py` | 작동. 기본값 **deny-all** |
| 위험 명령 전 백업 | `server/safety/backup.py` (`SaveShow`) | 작동. 🔴 **restore 송신 경로는 없다** |
| 콘솔 도달성 프로브 (오프라인 vs 응답기 저하 구분) | `server/web/console_probe.py` | 작동. 진단 전용, 송신 0 |

### 3.2 리그 · 공간 (완성)

| 무엇 | 어디 |
|---|---|
| Pan/Tilt 역산 조준 (실측 유래 공식, onPC 2.4.2 · 40대 수렴 실측 2026-08-13) | `server/spatial/pointing.py` `aim_pan_tilt` |
| 물리적 도달 불가 거절 | `PointingTiltLimitError`, `POINTING_TILT_LIMIT_DEGREES` |
| Move-In-Black (소수점 큐 번호 이용) | `server/spatial/mib.py` `apply_mib` |
| 설치 방향·분할 사전 점검 (읽기 전용 조언) | `server/spatial/preflight.py` |
| 포지션 프리셋 풀 + 덮어쓰기 보호 | `server/spatial/presets.py`, SPEC-COPILOT-PRESETGUARD-001 |
| 좌표 판독 | `get_spatial_context` (session.py ~:5391-5450) |

🔴 **못 읽는 것 셋** (코드가 스스로 적어둔 한계 — 다시 시도해서 시간 쓰지 마라):
1. **Group 멤버십을 못 읽는다** (`session.py:1333-1334` "the drilldown wall").
2. **Rotx/Roty 는 한 번도 실측된 적 없다** (`pointing.py:18-20`). Rotz 만 쟀다. 0 이 아닌
   회전이 확인된 장비는 조준 대상에서 **뺀다**(`rotation_skipped`).
3. **값을 못 읽는다** — 슬롯 점유와 이름까지다. 이름이 맞다고 색이 맞는 것이 아니다.
   그리고 **`0` 은 부재의 증거가 아니다**(내용 있는 Group 이 `COUNT 0` 을 답한 사례).

### 3.3 라이브러리 (데이터, 완성)

| 무엇 | 어디 | 개수 |
|---|---|---|
| FX 라이브러리 | `server/fx/library/{color,dimmer,movement}.yaml` | **22개** (color 3 · dimmer 5 · movement 14) |
| 룩 라이브러리 | `server/looks/library/{ballad,edm,rock,worship}.yaml` | **34개** (rock 9 · edm 10 · ballad 7 · worship 8) |
| FX 매칭 (한국어 별칭 · 패턴 축) | `server/fx/matching.py` `match_fx` | 닫힌 패턴 6종 |
| 룩 매칭 (장르 · 세기 · 무드) | `server/looks/matching.py` | — |

두 매처 모두 **없으면 지어내지 않는다** — 실패하면 `fallback_reason` 을 돌려준다. 이 규율은 유지.

### 3.4 앱 표면 (완성)

| 무엇 | 어디 |
|---|---|
| 실행 | `python -m server.web` → `server/web/serve.py:main`, 기본 `127.0.0.1:8765` |
| 웹소켓 | `/ws` 하나 (`server/web/app.py:343`), 서브프로토콜 `copilot.v1` |
| 🔴 Origin 필수 | `server/web/handshake.py:143-145`. 없으면 무조건 1008 거부 |
| 메시지 타입 | 클라→서버 9종 · 서버→클라 22종 (`server/web/messages.py`) |
| React UI 컴포넌트 | `ui/src/components/` — **38 파일**. `RunbookMode` `CueSheetTimeline` `SongTimeline` `ApprovalCard` `ReviewCard` `QuestionCard` `CueMonitor` `DashBoard` `PresetPoolPopup` `TimelineLibrary` 등 (대부분 `.test.tsx` 동반) |
| 타임라인 저장/불러오기 REST | `server/web/timeline_api.py` — `GET/POST /api/timelines`, `POST .../load`, `DELETE` |
| 데스크톱 빌드 | `src-tauri/`, `dist/GrandMA3 Copilot.app`, `GrandMA3-Copilot-0.4.0.dmg` |

### 3.5 곡 → 큐 파이프라인 (작동하되 이 층이 새 방향의 교체 대상)

```
곡 업로드 → analyze() → 확인 카드(BPM) → 인터뷰 8문항 → _build_unified_song_plan
  → SectionDecision × N → song_cue_composer → _song_timeline_payload → 런북 UI
  → cue_sheet_apply → 안전 게이트 → 콘솔
```

🔴 **인터뷰는 8문항이고, 두 곳에 나뉘어 있다** (이 세션 실측 — 실제로 태워서 셌다):

| # | 문항 | 어디 |
|---|---|---|
| 1 | 타이밍 방식 (타임코드/수동) | `server/web/session.py:8011` |
| 2 | Timecode 번호 | `server/web/session.py:8038` |
| 3 | Q1 컨셉 "공연 전체가 어떤 느낌이면" | `server/design/interview.py:502` |
| 4 | Q2 팔레트 "어떤 색이 잘 어울릴까요" | `server/design/interview.py:570` |
| 5 | Q3 클라이맥스 | `server/design/interview.py:615` |
| 6 | Q4 공간 서사 | `server/design/interview.py:822` |
| 7 | Q5 질감 (컷/페이드) | `server/design/interview.py:877` |
| 8 | 레이어 매핑 확인 (그룹 이름에서 역할 추정) | `server/web/session.py:8658` |

> ⚠️ `interview.py` 만 세면 **5문항**으로 보인다(`STEP_ORDER`). 코드 주석도 "다섯 개의 닫힌
> 질문"이라 적혀 있다. 하지만 감독이 실제로 답하는 것은 8개다. **계기가 무엇을 세는지 먼저 물어라.**

> ⚠️ `server/design/sugar_timeline.py` 는 **Maroon5 Sugar 전용 고정 데모 데이터**다
> (파일 주석: "서버가 계산한 값이 아니라 옮겨 적은 값"). 살아 있는 타임라인 생산자는
> **`server/web/session.py:2349 _song_timeline_payload`** 다. 헷갈리지 마라.

**실제 타임라인 구간 키** (이 세션 실측, 29개):
`index label start_ms cue_number plan_status d_level palette position texture fx fade_seconds
accents mib trig_time_seconds d_source palette_source position_source position_candidates
texture_source role end_ms duration_ms bar_start bar_count palette_primary palette_secondary
intensity fixture_groups movement trans`

### 3.6 큐시트 — 콘솔에 나가는 칸과 안 나가는 칸

`server/design/cue_sheet_apply.py`:

- **나가는 것** (`CONSOLE_APPLIABLE_FIELDS`:103-109): `intensity` `d_level` `palette_primary`
  `palette_secondary` `fade_seconds`
- **안 나가는 것과 그 사유** (`UNSOURCED_FIELD_REASONS`:113-131) — 🔴 **사유가 칸마다 다르다.
  "지원 안 함"이 아니라 각각 다른 경계다. 새로 조사하지 마라, 코드에 적혀 있다**:
  - `mood` — 콘솔 값이 아니라 룩을 고르는 말
  - `movement` — Pan/Tilt 명령 형태가 저장소에 없음(룩 라이브러리는 움직임을 안 담기로 한 설계)
  - `effect` — 페이저 스텝 축을 요구하고 콘솔에서 기계로 안 되읽힘 (FXLIB-001 M0 실측)
  - `trans` — SNAP/XFADE/FADE 를 페이드 초로 환산할 근거 없음
  - `note` — 콘솔에 값이 없는 칸

**편집 표면은 이미 있다** — `server/design/cue_sheet_edit.py`: 자연어 큐 편집 요청 파싱
(`parse_cue_sheet_edit_request`:190), 적용(`apply_cue_sheet_edit`:392), 변경 전/후를 사람이 읽는
문장으로 보고. 편집 가능 필드: `mood` `palette_primary` `palette_secondary` `intensity`
`movement` `effect`(+`note` `trans`).

---

## 3.7 연출 기획 층 지도 — 새 방향이 손댈 바로 그 층

### 모듈 (server/design/, 20개 파일 9,296줄)

| 파일 | 줄 | 소유 범위 |
|---|---|---|
| `profile.py` | 649 | 🔴 **우선순위 체인의 정본 구현** — 무드어 → (D레벨·컬러경향·포지션후보) 통합 사전, `resolve_section()`:562 |
| `interview.py` | 1165 | 감독 인터뷰 5문항 (나머지 3문항은 session.py) |
| `energy.py` | 303 | D1~D5 → 축별 예산 (`axis_budget`) |
| `cue_density.py` | 272 | 마디 격자 큐 분할 (`plan_cue_density`) |
| `cue_fade.py` | 53 | CueFade 문법 조립 (판정 아님) |
| `lint.py` | 725 | L1~L14 린트 + RG1 게이팅 |
| `color_names.py` | 137 | 색 이름 → RGB(0-100), 한/영 동치표 |
| `song_cue_composer.py` | 893 | 축 결정들 → 실제 큐 커맨드 합성 |
| `song_plan.py` | 1105 | 곡 전체 구간→큐 계획 자료구조 |
| `sugar_timeline.py` | 495 | ⚠️ Maroon5 Sugar 전용 **고정 데모** (살아 있는 경로 아님) |
| `position_sheet.py` | 160 | 축값 → 포지션 큐시트 |
| `override_look.py` | 344 | Global Preset override 번들 계획기 |
| `rig.py` | 412 | RigProfile — 레이어 규칙이 조건화되는 4축 |
| `rig_capability_read.py` | 194 | 콘솔 → 리그 능력 판독 배선 |
| `rig_preflight.py` | 341 | 쇼 전 읽기 전용 리그 점검 |
| `capability_join.py` | 299 | fid 단위 능력 조인 |
| `capability_verdict.py` | 487 | 능력 판독 → 계획 단계 거절 판정 |
| `cue_sheet_edit.py` | 526 | 큐시트 초안 편집 (콘솔에 안 씀) |
| `cue_sheet_apply.py` | 690 | 편집본 → 콘솔 커맨드 계획 |

### 우선순위 체인 — 이게 설계의 뼈대다

`server/design/profile.py:562 resolve_section()` 이 세 축의 정본 순서를 못박는다:

```
감독 답변(director_intent) > 구간 무드어(UNIFIED_MOOD_TABLE) > 컨셉(CONCEPT_SEED_TABLE)
  > 장르(GENRE_DEFAULT_TABLE) > 전역 기본값
```

- 세 축(D레벨·컬러경향·포지션후보)이 **각각 독립으로** 이 체인을 돈다 (`profile.py:573-582`).
  하나의 티어가 세 축을 한꺼번에 정하지 않는다.
- D레벨 체인만 컨셉·장르 단이 없다 — 표준 §2b 가 그렇게 정의했다 (`profile.py:608-613`).
- 그 위에 `session.py` 의 `_section_*_decision` 이 **구간 role 아크**를 한 겹 더 얹는다.
  그 층의 순서는 `session.py:722-723`: `구간 자연어 > 감독 구간 선택 > Q4 > 장르 > fallback`.

### 축별 결정 함수

| 축 | 함수 | 표 |
|---|---|---|
| D-level | `profile.py:608-613` | `_ARC_D_LEVEL`(session.py:729)은 role 아크용 별도 |
| 팔레트 | `session.py:1714 _section_palette_choice()` | `_ARC_PALETTE`(:795) + `rotate_palette` 회전 + `_ACCENT_WEIGHT_LADDER`(:1035) |
| 포지션 | `profile.py:625-643` + `session.py:610 _section_director_override()` | `_DIRECT_POSITION_INTENTS`(:904) |
| 텍스처 | `session.py:954 _section_texture_decision()` | `_ARC_TEXTURE`(:730) |
| FX | `session.py:972 _section_fx_decision()` | `_ARC_FX`(:737) + `_ARC_FX_LADDER`(:764) |
| 액센트 | `session.py:691 _accent_decision()` | `_occurrence_accent_label()`(:670) |
| 페이드 | **결정 함수 없음** — `cue_fade.py` 는 조립기일 뿐, 숫자는 상위가 정한다 |
| 움직임 | **별도 축 없음** — `_ARC_FX_LADDER` 안에 이동계 이름이 섞여 FX 경로에 합류 |

### `_ARC_*` 표 다섯 — 전부 role 5종 키

`_ARC_D_LEVEL` `_ARC_TEXTURE` `_ARC_FX` `_ARC_FX_LADDER` `_ARC_PALETTE` (전문은 session.py:729-800).

🔴 **`_ARC_FX_LADDER` 만 「회차별 튜플의 튜플」 구조다**(카드 t405, 2026-09-14). 나머지 넷은
role 당 값 한 벌이고, 회차 변주는 `rotate_palette`·`_arc_accent_weight` 같은 **별도 회전 함수**가
바깥에서 더한다. **구조가 통일돼 있지 않다** — 새 방향에서 이 층을 다시 설계할 때의 출발점.

### Role 분류기 둘 — 신호가 다르다

| 분류기 | 어디 | 보는 신호 |
|---|---|---|
| `_section_role` | `session.py:923-944` | 명시 `section.role` > 이름+무드 문자열 정규식 |
| `_infer_confirmed_role` | `session.py:804-826` | 🔴 **서수(첫/끝) + D레벨 상대값만**. 무드 단어를 절대 안 본다 |

오디오 확정 구간은 이름·무드가 비어서 **항상 두 번째가 돈다**. 그래서 §1 의 "39개 중 25개가
chorus" 가 나온다. `level >= max(d_levels) → chorus` 한 줄이 그 원인이다.

### 큐 분할 상수 (`cue_density.py`)

```python
BAR_UNIT_BARS = 8                 # 8마디당 큐 1장
MIN_UNITS_TO_SPLIT = 2            # 16마디부터 둘로 갈림
MIN_PALETTE_COLORS_TO_SPLIT = 2   # 색 하나면 큐 하나 (회전이 항등이므로)
DEFAULT_VARIANT_LABEL = "색"
```

BPM 또는 박자표가 `None` 이면 분할 0건(추측 금지). 큐 수는 팔레트 변주 수를 넘지 않는다.

🔴 **오늘 실측으로 드러난 것**: 이 상수들은 **거의 작동하지 않는다**. analyzer 가 이미 2마디
구간을 39개 주므로 8마디 분할이 걸릴 구간이 거의 없다(실측: 39개 중 35개가 `bar_count=2`,
분할 접미사 `(n/m)` 붙은 이름 0개). §12 5번의 진단("8마디 고정 분할이 문제")은 **자리가 틀렸다**.

### 린트 L1~L14 (`lint.py`)

L1 구간당 큐≥1 · L2 D 단조성 · L3 헤드룸 · L4 포지션폭 축소 · L5 팔레트 이탈 ·
**L6 키층 소등(조건부)** · **L7 백층>키층(조건부)** · L8 블랙아웃 예산 · L9 스냅 위치 ·
L10 이펙트 축 예산 · **L11 BPM 그리드(조건부)** · L12 인접 큐 변화 축 수 · L13 3중 조합 연속 ·
L14 객석/블라인더 예산

- L6·L7 은 `rig.layer_rules_active()`(RG1) 가 True 일 때만 돈다
- L11 은 BPM 이 실측/선언값일 때만 (`profile.bpm_is_default` False)
- 🔴 **미실행 규칙은 조용히 빠지지 않고 `DisabledRuleNote(rule_id, reason)` 로 보고된다** — 이 규율 유지
- 큐 `tags` 에 rule_id 를 넣으면 개별 억제 가능

### 🔴 예술 판정 생산자가 **둘**이다

이것이 새 방향에서 가장 먼저 정리할 구조다. `SPEC-LDPLUGIN-001/research.md` 도 같은 것을
지목한다("동일 Director 외에 두 번째 예술 policy producer가 남지 않도록 후속에서 제거·호출부 치환").

| 생산자 | 어디 | 무엇으로 정하나 |
|---|---|---|
| ① 룩 라이브러리 경로 | `server/looks/songcue.py` (`map_sections_to_looks`) | 라벨·장르 → 룩 34종 매칭, 후렴 반복 accent/밝기 정책 |
| ② 아크 표 경로 | `server/web/session.py` `_ARC_*` + `server/design/` | role 5종 → 축별 표 조회 |

둘 다 살아 있고 `session.py` 가 양쪽을 임포트한다(`session.py:119-124`). 새 방향은 이 둘을
**하나로** 만들거나 둘 다 외부 Director 로 대체한다.

### 테스트

`server.design` 을 참조하는 테스트 **41 파일**, `session.py` 의 아크/role 결정 함수를 직접
참조하는 테스트 **10 파일**. 이 층을 갈아끼우면 이 51개가 판정 기준이 된다.

---

## 3.8 정본 §12 「고칠 것 7개」의 현재 상태 — 🔴 문서가 낡았다

`song-structure-lighting-standard.md` §12 는 2026-09-11(`e443552`) 기준이다. 오늘(`f2e4d59`)
실측으로 **최소 한 항목이 이미 닫혔고, 한 항목은 진단 자체가 틀렸다**:

| # | §12 가 적은 것 | 오늘 실측 |
|---|---|---|
| 1 | "`server.fx` 임포트 0건 — 움직임이 콘솔에 안 나간다" | 🟢 **닫힘**. `server/looks/movement.py` 가 `from server.fx.instantiate import phaser_lines`(:41) 로 잇는다. 그 파일 주석이 스스로 "고치기 전에 실측한 것(2026-09-11)" 이라 적었다 |
| 5 | "8마디 고정 분할이 문제" | 🔴 **자리가 틀렸다**. 상수는 그대로지만 analyzer 가 이미 2마디 구간을 준다 — 분할이 걸릴 자리가 없다. 진짜 자리는 `analyze.py:44 _MIN_SEGMENT_SECONDS = 3.0` |
| 2·3·4·6·7 | — | 이 세션에서 재확인하지 않았다(§9) |

**교훈**: 날짜 붙은 진단은 노화한다. §12 를 읽을 때는 근거 커밋(`e443552`)과 현재 HEAD 사이를
먼저 대조하라.

---

## 4. 규모 — 다시 만들면 얼마를 잃나

| | 값 | 출처 |
|---|---|---|
| `server/` 파이썬 파일 | **591** | `find server -name "*.py" \| wc -l` |
| `server/web/session.py` | **12,313 줄** | `wc -l` |
| 테스트 파일 | **350** | `ls server/tests \| wc -l` |
| 테스트 통과 | **12,794 passed · 31 skipped** | 이 세션 `uv run pytest` |
| 머지된 PR | **67** | `git log --merges \| wc -l` |
| SPEC | **56건** (completed 28 · draft 14 · in-progress 9 · implemented 2) | `.moai/specs/` |
| UI 컴포넌트 파일 | **38** | `ls ui/src/components` |
| 서버 패키지 | 25개 | `ls server/` |

---

## 5. 안 되는 것 — 다시 시도해서 시간 쓰지 마라

1. **Group 멤버십 판독** — 드릴다운 벽 (`session.py:1333-1334`)
2. **프리셋 **값** 판독** — 슬롯 점유·이름까지. 값은 안 온다
3. **`COUNT 0` 을 부재의 증거로 쓰기** — 내용 있는 Group 이 0 을 답한다
4. **Rotx/Roty 실측값** — 한 번도 잰 적 없다. 0 가정
5. **이펙트 되읽기** — 페이저는 기계로 안 되읽힌다 (FXLIB-001 M0)
6. **restore 송신** — 백업은 되는데 되돌리는 경로가 없다
7. **큰따옴표 송신** — 콘솔이 아예 안 받는다. 홑따옴표만 (`pointing.py:363`)
8. **CI** — 🔴 저장소 전체가 과금 차단으로 죽어 있다. **로컬 `uv run pytest` 가 유일한 판정 근거**
9. **8 MiB 넘는 음원 업로드** — 거절이 아니라 연결이 끊긴다 (카드 t397). 감독 곡 31.5MB 가 여기 걸림

---

## 6. 열린 카드 57장을 새 방향 기준으로 가른다

`moai todo` 실측: queued 49 · picked 8 = **57장** (dropped 299).

### (가) 새 방향에서 살아 있다 — 연출 기획 축 (13장)

`t382` 충돌 회피가 상승 사다리를 덮어씀 · `t394` 전환 표시 · `t395` FOH 가 객석으로 판독 ·
`t396` 역할 추정기가 절대 밝기를 안 봄 · `t401` 팔레트 기조 vs 후렴 질러도 됨(감독 결정 완료) ·
`t404` 색 운용 방식 인터뷰 문항 · `t411` 기존 효과 이름 5개가 라이브러리에 안 걸림 ·
`t347` 능력 어휘 매핑표 · `t352` MOVER-ALL 줌 상한 · `t374` override_look 을 도구로 등록 ·
`t138` Gobo 범위 · `t229` 물리 단위 판독 경로 · `t232` 프리셋 참조 안정성

🔴 **`t396` 과 `t395` 는 §1 의 뿌리와 같은 층이다** — 새 방향에서 우선순위가 올라간다.

### (나) 앱·도구 유지보수 (6장)
`t397`(음원 8MiB 절단 — 감독이 실제로 겪음) · `t22` · `t72` · `t244` · `t263` · `t376`

### (다) 하네스·장부·메타 (38장) — 🔴 새 방향에서 **버릴 후보**

`t18 t36 t47 t53 t56 t59 t60 t65 t67 t78 t81 t88 t91 t92 t94 t99 t100 t101 t122 t139 t148
t161 t164 t191 t195 t265 t266 t268 t293 t298 t337 t338 t339 t340 t341 t342 t354`

기억해 둔 감독 지시가 이 판단의 근거다 — *"장치는 제품이 아니다"* (2026-09-11: 열린 47장 중
45장이 측정 카드였고, 그날 머지 여섯이 전부 "안 된다고 말하는 장치"였다).
**카드를 고를 때 「감독이 눈으로 볼 게 늘어나나」를 먼저 물어라.**

---

## 7. 정본 문서 — 이미 쓰여 있다

| 문서 | 내용 |
|---|---|
| `docs/proposals/song-structure-lighting-standard.md` | 곡 구조 기반 연출 기준 v1. 14장, **[HARD] 19개**. §7.1 아껴두기 사다리, §9 큐 밀도, §12 **현재 구현과의 차이 7개(우선순위 포함)** |
| `docs/proposals/song-lighting-design-standard.md` | 곡 단위 조명연출 표준 v0.4. D1~D5 에너지 모델, 축별 규칙, 린트 L1~L14, 콘솔 능력 경계 |
| `reports/copilot-architecture-20260908.md` | 전체 구조 실측 보고서 (명령 경로 · 안전 게이트 3단 · 패키지 층 · LX-SEQ 4단계) |
| `docs/user-guide.html` | 감독 워크플로우 축 사용 가이드 (55KB, SPEC-LDGUIDE-001 로 개정 완료) |

🔴 **§12 의 7개 차이 중 5번(8마디 고정 분할)이 아직 열려 있다** — 그런데 오늘 실측으로
**진짜 원인은 마디 분할이 아니라 analyzer 가 39구간을 주는 것**임이 드러났다.
`BAR_UNIT_BARS = 8` 은 그대로인데 구간이 이미 2마디다. §12 5번의 진단을 새로 써야 한다.

---

## 8. 다음 세션이 할 일 — 순서

1. **이 인계 문서와 두 LD SPEC 을 먼저 읽어라.** `SPEC-LDPLUGIN-001/research.md` 가 재사용 지도다.
2. **Implementation Kickoff Approval 을 감독에게 받아라.** 두 SPEC 모두 *"문서 작성만 요청되었고
   Implementation Kickoff Approval 은 아직 없다"* 고 스스로 못박고 있다. 승인 없이 구현 시작 금지.
3. **구현 전에 감독 결정 두 건이 필요하다** (§2 의 SPEC 이 다루지 않는 축):
   - 외부 플러그인 방향(LDPLUGIN)으로 먼저 갈지, 구간 층 수리(§1)를 앱 안에서 먼저 할지
   - 열린 카드 (다) 38장을 버릴지
4. **무엇을 하든 §3 을 다시 만들지 마라.** 콘솔·안전·리그·라이브러리·UI·데스크톱 배포는 끝났다.

---

## 9. 안 잰 것

- `server/orchestrator/` 내부 (도구 34종의 책임 분담) — 목록만 확인, 본문 미독
- `ui/src/` 컴포넌트 내부 구조 — 파일 목록만 셌다
- SPEC 56건 각각의 인수기준 통과 여부 — 산출물 존재와 frontmatter status 만 쟀다
- `SPEC-LDPLUGIN-001/contract.md` 52.7KB 전문 — §1~§3 과 research 만 읽었다
- 실기 콘솔 도달 — 이 세션 콘솔 쓰기 **0회**. §3.1 의 "작동"은 코드·테스트 근거이고 오늘 실기로 재현한 것이 아니다
- `server/looks/` 내부(`songcue.py` `roles.py` `matching.py` `busking.py` `song_history.py`)
  — §3.7 의 「생산자 둘」 중 ① 쪽은 임포트 경계만 쟀고 본문은 안 읽었다
- `lint.py` L1~L14 각 검사의 세부 비교식 — rule_id 목록과 게이팅 조건만 쟀다
- `interview.py`(1165줄) `song_plan.py`(1105줄) `song_cue_composer.py`(893줄) 본문 — docstring 수준만
- 테스트 41개/10개는 **파일명 grep 매치 수**다. 각 테스트가 무엇을 지키는지(커버리지 질)는 안 쟀다
- 정본 §12 의 2·3·4·6·7 항목이 여전히 유효한지 — 1번과 5번만 오늘 대조했다
- 정본 [HARD] 19개 각각을 코드가 지키는지 — §12 가 적어둔 7개만 안다
