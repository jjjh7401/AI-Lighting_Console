# 00. 종합 정리 & 계획 — grandMA3 이펙트(Phaser) 생성 역량 강화

> 오케스트레이션 리서치(태스크 A~D, 2026-08-14, 브랜치 `research/ma3-effects-phaser`)의
> 코디네이터 종합본. 상세 근거는 01~04 문서 참조.

## 1. 핵심 결론

1. **MA3 이펙트 = Phaser.** 2개 이상의 Step(절대/상대 값)을 Speed/Phase/Width/Measure/
   Accel·Decel(=Attack/Decay 대응)/Transition 레이어로 순환·보간하는 엔진. Phase를 선택
   전체에 0→360으로 스프레드하면 웨이브가 되고, Pan/Tilt에 90° 위상차를 주면 서클이 된다.
   (01, 02 문서)
2. **명령줄만으로 페이저 생성 가능** — 그리고 이 저장소는 그 문법을 onPC 2.4.2에서 이미
   라이브 검증했다(`server/rulebook/assets/v2.4.2/31_choreography_patterns.md`).
   패턴: `ChangeDestination Root → ClearAll → Group N → 값 → Step 2 → 값 → At Phase … →
   At Speed … → Store Sequence N Cue 1 → ClearAll`. (04 §1)
3. **이 저장소는 이미 페이저 파이프라인을 구현·검증 완료** (SPEC-FXLIB-001):
   - 스키마: `server/fx/schema.py` (`MIN_STEPS=2` 강제)
   - 라이브러리: `server/fx/library/{dimmer,color,movement}.yaml`
   - 빌더: `server/fx/instantiate.py` (`build_fx_bundle`, phase 분배, 충돌 가드, 시퀀스 번호 실측)
   - LLM 도구: `server/orchestrator/tools.py`의 `find_fx` / `instantiate_fx`
     (단일 실행 경로 `run_commands`로 재진입 — 안전 게이트/감사 로그 상속)
4. **함정 3종** (04 §1.3): ① 스텝 1개면 페이저 미생성(모든 라인 `ok:true`인데 무대 정지),
   ② `Attribute … At Step k` 형은 무효, ③ 저장된 페이저는 기계적 read-back 불가 →
   성공 판정은 명령 verdict + 사람/시각 관측에 의존.

## 2. 리서치가 드러낸 갭 (현 구현 대비)

| # | 갭 | 근거 | 가치 |
|---|---|---|---|
| G1 | **효과 레퍼토리 부족** — 라이브러리에 movement 4종(sweep/wave/circle/diagonal)+dimmer/color 일부만. 리서치는 figure-8, ballyhoo, fly-out(waterfall), rainbow(ColorRGB 3스텝), HSB Hue 웨이브, 스트로브, 아이리스 펄스, 줌 브리딩, 고보 스핀 등 검증 가능한 레시피 다수 확보 | 02 §2, 03 §1–3 | 높음 — 사용자 체감 직결 |
| G2 | **Accel/Decel 커브 미방출** (`GATED_AXIS_NOT_EMITTED`) — 사인형 vs 각진 형태를 못 가름. 공식 레시피(사인 디머 = Accel −100/Decel −100)가 존재하므로 재검증 대상 | 01 §5.5, 03 §4, 04 §3.4 | 높음 — 룩 품질 |
| G3 | **`At Relative` 스텝 값 미검증** (`ASSUMPTION-40`) — 상대 페이저(중심 프리셋 + 오프셋 서클) 불가 | 02 §②, 04 §3.4 | 중 — 포지션 이펙트 자유도 |
| G4 | **SpeedMaster 미지원** — 고정 BPM만. `At SpeedMaster N`으로 여러 페이저 속도 동기/실시간 템포 제어 가능 | 01 §5.7, 04 §1.2 | 중 |
| G5 | **MAtricks Grid 서브선택 미지원** — 5축 phase/wings/shuffle만. `Grid x/y` 셀렉션 없음 | 04 §3.4 | 낮음–중 |
| G6 | **Measure / Width 레이어 미방출** — 스텝 타이밍 비율 제어 불가 | 01 §5.3–5.4 | 중 |

## 3. 실행 계획 (제안)

### Phase 1 — 라이브 검증 (onPC 2.4.2, `tools/console_probe.py` 계열 활용)
콘솔 실측 없이는 어떤 축도 방출하지 않는 것이 이 저장소의 원칙. 검증 항목:
- V1: `At Accel -100` / `At Decel -100` (M0에서 `ok:true`+무효과 관측 → 스텝 컨텍스트에서 재시도)
- V2: `At Relative <n>` 스텝 값 (베이스 프리셋 위 상대 오프셋)
- V3: `Attribute '<a>' At SpeedMaster N` + SpeedMaster BPM 변경 반영
- V4: `At Width <pct>` / Measure 레이어
- V5: 3스텝 페이저 (rainbow ColorRGB 3스텝 레시피)
- 검증 결과는 `31_choreography_patterns.md` 규약대로 rulebook 자산에 추가.

### Phase 2 — 스키마/빌더 확장 (`server/fx/`)
- `schema.py`: `accel`/`decel`(스텝 단위), `relative` 스텝 값, `speed_master`, `width`,
  `measure` 필드 추가 — V1~V4 통과 항목만 게이트 해제.
- `instantiate.py`: 해당 라인 방출 + 기존 충돌 가드/시퀀스 실측 유지. 3+스텝 지원 확인.

### Phase 3 — 라이브러리 확충 (`server/fx/library/*.yaml`)
리서치 레시피를 스키마로 번역해 추가 (검증된 축만 사용):
- movement: figure-8, ballyhoo, fly-out, pan sweep(전용), circle-relative(V2 통과 시)
- dimmer: sine breathing(V1 통과 시), pulse(width 좁게), strobe(사각파)
- color: rainbow 3-step, 2-color chase, HSB hue wave(픽스처 HSB 지원 실측 필요)
- beam: iris pulse, zoom breathing, gobo spin(프로파일 의존 → 리그 실측 가드)
- 무드→BPM 시드는 기존 choreography 표 재사용.

### Phase 4 — 도구/UX
- `find_fx` 매칭 사전에 신규 패턴 동의어(한국어 포함: 서클, 발리후, 무지개, 브리딩 등) 추가.
- `instantiate_fx` 성공 후 사용자 관측 요청 메시지 표준화 (함정 ③ 대응).

### Phase 5 — 검증/마감
- `server/fx` 단위 테스트(번들 골든 비교) 확장, 라이브 스모크(M-시리즈 관례) 1회,
  CHANGELOG 갱신.

## 4. 리스크
- Accel/Decel·Relative는 과거 실측에서 무효과/미검증 — Phase 1 결과에 따라 G2/G3 범위 축소 가능.
- 고보/프리즘은 픽스처 프로파일 의존성이 커서 라이브러리 항목에 리그-검증 가드 필수 (03 §3.1).
- 페이저 read-back 불가는 콘솔 제약이라 해소 불가 — 관측 기반 확인 UX로 우회.

## 5. 산출물 목록
- `01-phaser-fundamentals.md` — 페이저 엔진·파라미터 총론 (18개 출처)
- `02-pantilt-effects.md` — 포지션 이펙트 7종 레시피 + 커맨드라인 문법
- `03-color-dimmer-beam-effects.md` — 디머/컬러/빔 레시피 + Accel·Decel/Measure/MAtricks
- `04-programmatic-phasers.md` — 명령줄 쿠크북 + Lua API + 저장소 통합 분석
