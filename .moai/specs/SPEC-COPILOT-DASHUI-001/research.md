# SPEC-COPILOT-DASHUI-001 — 리서치 (research)

status: draft (v0.1.0, 2026-07-24). 본 브랜치(`claude/nice-satoshi-f58b50`) 코드베이스 실측 기반. file:line 앵커는 작성 시점 기준.

## §1. 목적

분할 대시보드 UI가 (a) 서버가 실제로 서빙할 수 있는 데이터 위에, (b) 기존 안전 계약을 무변경 계승하며, (c) 이미 동결된 프로토콜 계약의 additive 확장만으로 성립하는지 확인한다.

## §2. 기존 기반 인벤토리 (본 브랜치 실재)

| 자산 | 위치 | 상태 |
|---|---|---|
| 라이브 검증 rig 경로 10종 | `DEFAULT_RIG_CONTEXT_PATHS` tools.py:65-76 | 2026-07-22 onPC 2.4.2 실측. `Patch/Fixtures`·`DataPool/Presets`는 **죽은 경로**(tools.py:25-30) — 픽스처는 `Patch/Stages/1/Fixtures`, 프리셋은 `DataPool/PresetPools/<no>` 드릴다운 |
| 드릴다운 + 캡 | `DEFAULT_RIG_DRILLDOWN` tools.py:81, `RIG_DRILLDOWN_QUERY_CAP=16` tools.py:88, `PANEL_DRILLDOWN_QUERY_CAP=16` panel.py:77 | 질의당 UDP 왕복(게이트+감사 경유) — 무제한 워크 금지 근거 |
| 실패 사유 2종 | `REASON_UNRESOLVED`/`REASON_UNREACHABLE` tools.py:104-105 | public — 패널이 같은 결론을 내리도록 공유(주석 명시) |
| 발화 카탈로그 닫힌 집합 | `PANEL_CATALOG_SECTIONS` @MX:ANCHOR panel.py:118-132 | sequences + pages(→executors). fixtures 구조적 부재(슬롯≠FID) |
| 핀 스토어/카탈로그/membership | panel.py (PinStore/PanelStore/PanelCatalog) | 원자적 JSON 영속, replace 의미론(panel.py:135-143), credential 거부 |
| 게이트 경유 발화 | `PanelRuntime.fire` panel.py:631-636, `playback_command` @MX:ANCHOR panel.py:553-566 | 유일 진입·닫힌 동사쌍(`Go+`/`Off`)·단일 양의 정수 — 광역 타깃 구성 불가 |
| `/ws` 패널 라우팅 + 패널 전용 세션 키 | app.py:252-267, lazy `panel_store()` app.py:167-176 | SHOWUI M3 — 채팅 clearance와 격리 |
| 프로토콜 v1 패널 확장 | messages.py:23-61 (`PANEL_TARGET_KINDS=("executor","sequence")`), protocol.ts:62-176 | 양측 allowlist·reducer 등재 완료, `panelItemId`/`buildPanelExecute` 등 빌더 존재 |
| UI 현재 상태 | App.tsx — 채팅 단일 컬럼, `.app` max-width 860px(styles.css:24-28) | 대시보드 컴포넌트 부재(§3) |
| 디자인 토큰 | styles.css:1-11 `:root` | SHOWUI design.md가 canonical base로 지정 |

## §3. 브랜치 상태 발견 (중요)

- SHOWUI-001 커밋 계보: **M1(88a0b34)·M2(5395a10)·M3(0576553)은 본 브랜치(HEAD)의 조상** — 서버/프로토콜 절반은 여기 실재하고 앱에 배선돼 있다.
- **M4(857e9ed, ShowPanel UI)·M5(09e2c4f)·M6/sync(55942f7 등)는 본 브랜치 조상이 아니다** — `git merge-base --is-ancestor` 실측: 88a0b34 YES / 857e9ed NO / 09e2c4f NO / 55942f7 NO. 해당 커밋들은 `feat/app-deploy-file-import` 브랜치에 있다.
- 결과: 본 브랜치의 UI는 채팅 단일 컬럼이 맞고(`ui/src/components/`에 ShowPanel/PanelTile 부재), 본 SPEC의 UI는 신규 작성이다. **위험**: 훗날 두 브랜치 병합 시 UI 충돌 — 완화는 구별되는 컴포넌트 명명(plan.md §F D7) + reconciliation 명시적 범위 제외(spec.md §D).

## §4. 데이터 소싱 가능성 (풀별)

| 풀 | 경로 | 깊이 | 비고 |
|---|---|---|---|
| Sequences | `DataPool/Sequences` | 1 | 기존 발화 카탈로그 소스 그대로 |
| Executors | `DataPool/Pages` 드릴다운 | 2 | 자식 `no`는 페이지 내 슬롯 — **발화 번호가 아님**(§5) |
| Groups | `DataPool/Groups` | 1 | `no`가 곧 주소(Group `<no>`) — 참조 어휘로 최적 |
| Presets | `DataPool/PresetPools` + `<no>` 드릴다운 | 2 | 풀 타입(≈8-10종) → 내용물. "풀 존재"와 "내용물 저장됨"은 다른 답(tools.py:38-44) |
| Macros | `DataPool/Macros` | 1 | 실행 형태는 §6 |
| Plugins | `DataPool/Plugins` | 1 | read-only 목록 |
| Fixtures | `Patch/Stages/1/Fixtures` | 1 | stage 슬롯 1 가정(단일-showfile 실측, tools.py:57-64) — 카운트 요약이면 함정 노출면 최소 |
| MAtricks/Worlds | 검증됨 | 1 | v1 제외(IA 판단 — design.md §2) |

드릴다운 예산: 프리셋 풀 타입만으로 ~8-10 질의 + 페이지 드릴다운 → 단일 16캡 공유는 상시 캡아웃 위험. **섹션별 유계 예산 분리 권고**(M2).

## §5. 익스큐터 주소 해석 (EXECBODY-001 소비)

- 실측 교훈: 페이지 1의 자식 인덱스 `i`에 대해 콘솔 발화 실번호는 `i+100`(전 슬롯 균일 실측) — 그리고 `Go+ Executor 101`(자식 인덱스 그대로)은 **오류 없이 엉뚱한 대상을 발화**할 수 있는 무오류 오발 함정. SHOWUI M6이 이 이유로 익스큐터 타일을 v1 축소했었다.
- EXECBODY-001이 해소: 응답기 `resolve_path`가 ObjectList() 경유로 Executor 콘솔 주소를 해석(M6, 커밋 6c08fd4), 게이트는 할당-시퀀스 아이덴티티로 본문을 스크리닝해 양성 본문 익스큐터의 single-press를 승인 0·`SaveShow` 0으로 통과(AC-EXECBODY-010 라이브 PASS, 커밋 40e79b7).
- 잔존 규율: 오프셋 하드코딩 금지(AC-EXECBODY-016) — 해석된 번호가 없으면 발화 타일을 제공하지 않는 것이 유일하게 정직한 동작(REQ-DASHUI-011).

## §6. 매크로 실행 형태 (룰북 검증)

- 룰북 `00_grammar.md:60`: `Macro` 키워드 = "Run a macro by id/name", 예 `Macro 3`. `10_object_model.md:26`: Macro = 저장된 커맨드 라인 목록.
- 즉 v1 실행 형태는 **베어 참조 `Macro <no>`**(별도 동사 없음). `playback_command` 빌더의 닫힌 집합에 additive 케이스로 추가하되 "단일 양의 정수 + 닫힌 형태" 속성은 유지.
- 게이트 관점: `Macro <no>`는 invoking 참조 — 기존 fail-closed 확장 기계(재귀 상한·순환 탐지·블랙리스트 본문·본문 부재 보류)가 그대로 적용된다(EXECBODY AC-008이 이 기계의 무변경 상속을 이미 검증). 블랙리스트 본문 매크로 press는 승인 카드로 표면화 — 이것이 의도된 정직한 UX다.
- 라이브 편차 리스크: 실행 형태·게이트 분류의 실측 편차 시 매크로 press만 read-only 강등(plan.md §E R2 — EXECBODY 정직 DESCOPE 선례).

## §7. 리스크 요약

1. **브랜치 분기 UI 충돌**(§3) — 명명 회피 + 범위 제외.
2. **드릴다운 예산 캡아웃**(§4) — 섹션별 예산 + 정직 표기.
3. **익스큐터 해석 실패 showfile**(§5) — 미제공 + 표기, 추정 금지.
4. **매크로 라이브 편차**(§6) — 정직 축소 경로.
5. **stage 슬롯 1 가정**(tools.py:57-64) — 픽스처 요약이 `path_not_resolved`로 정직 실패(기존 의미론), 대시보드는 그 사유를 그대로 렌더.
6. **정보→발화 승격 회귀** — 정보 형상에 target_kind 구조적 부재 + membership 음성 테스트.

## §8. 권고 (Recommendations — 구속력 있음)

1. 정보 카탈로그는 신규 `dash_catalog` additive 이벤트로 분리 — `panel_catalog`/`PANEL_CATALOG_SECTIONS`의 "발화 가능 닫힌 집합" 의미 보존.
2. 매크로는 `PANEL_TARGET_KINDS` additive 확장 + 빌더 닫힌-집합 확장으로 기존 발화 경로에 편승 — 신규 실행 경로 0.
3. 드릴다운은 섹션별 유계 예산.
4. 익스큐터 발화 타일은 해석된 콘솔 번호 전제.
5. 픽스처는 카운트 요약(목록·FID 비제시).
6. 새로고침은 접속 시 + 수동만(폴링 금지), 갱신은 전체 교체.
7. 컴포넌트 명명은 DashBoard/PoolSection/PoolTile(타 브랜치 충돌 회피).
