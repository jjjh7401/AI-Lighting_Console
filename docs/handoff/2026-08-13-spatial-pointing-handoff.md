# 세션 핸드오프 — 2026-08-13/14 (3D 공간 포인팅·포지션 프리셋·무드 제안)

브랜치 **`feature/spatial-pointing`** (origin 푸시 완료, main 미병합). 대상은
grandMA3 Copilot (`server/` + onPC 2.4.2 라이브 콘솔, `NewShow_2026.08.08`).
이 세션의 전 기능은 라이브 콘솔에서 실측·검증됐다.

## 1. 핵심 성과 — Pan/Tilt ↔ 3D 공간 실측 모델

한 픽스처에 알려진 값을 명령하고 3D 창 빔 착지점을 스크린샷으로 판독해 확정:

- `Attribute 'Pan'/'Tilt' At <n>` = **물리 도(°)** (룰북 31의 "percent" 표기는
  오류 — 그 파일은 바이트 핀이라 수정 불가, 정정은 32_spatial_design.md에 있음)
- Pan0/Tilt0 = 수직 아래(−Z), +Tilt → +Y(업스테이지), +Pan → 위에서 반시계
  (+Y→−X at 90), 패치 `Rotz`는 Pan 프레임을 같은 방향으로 회전(빼서 보정)
- 역산: `v=T−F`, `tilt=acos(−vz/|v|)`, `pan=atan2(−vx,vy)−rotz`
- 검증: 40대 전 빔 (0,0,0) 수렴 사진. `Rotx/Roty`는 **미계측** — 0 아닌 리그는
  재계측 필요

## 2. 만들어진 것 (커밋 순)

1. `b63447c` — `server/spatial/pointing.py` (aim_pan_tilt/pointing_commands) +
   세션 직접 핸들러 `_point_fixtures_at_target`("중앙/(x,y,z) 바라보게") +
   스킬 `.claude/skills/ma3-spatial-pointing` + `tools/pointing_probe.py`
2. `b034444` — 프리셋 전략 제안서
   `docs/proposals/pan-tilt-position-preset-strategy.md` (FOCUS/LOOK 이원 체계,
   웹 리서치 출처 포함)
3. `4945916` — LOOK 계열: `fan_pan_tilt`(out/in/cross), `radial_pan_tilt`
   (ring in/out), `position_preset_store_commands`(Store/Label Preset 2.n),
   핸들러 `_look_pan_tilt`("부채살/교차/안쪽·바깥쪽 바라보게/프리셋 N로 저장")
4. `f97eeed` — 기본 포지션 10종 `basic_position_presets` (1번 항상 'Home',
   Wall/Audience/Center/Vocal DSC/Fan Out/Fan In/Cross/Ring Out/Ring In —
   전부 리그 좌표에서 유도) + `_basic_position_presets` 핸들러(시작 번호
   질문 카드 1장, "N번부터"면 생략, 무응답이면 거부). 라이브: 437/437,
   Preset 2.21~2.30 실재 + `At Preset 2.28` 리콜 재현
5. `b1ee98b` — `fan_chain`(지배축 정렬) + `tools/placement_verify.py`
   (재배치→룩→원좌표 비트단위 복원). 라이브: 일자 Fan Out / 반원 Ring Out /
   삼각형 Center 적응 확인
6. `7c07853` — 2축 부채살 `tilt_spread`(Align<> 틸트 V; "팬 45도 틸트 20도
   부채살", "팬틸트 모두/입체" 기본 ±15)
7. `2ba9ac3` — 무드→포지션 제안 `server/spatial/position_moods.py`
   (키워드 무겹침 계약, 득점 최다 승) + `_position_mood_suggestion`
   (제안 카드 → 선택만 적용, 거절이면 무전송) + 룰북 32에 의도→포지션 표
8. `3632eb2` — 큐 페이저 함정 문서화 (아래 §4)

라우팅 순서(`run_instruction`): elevation → basic_presets → look → point →
**mood** → repeating columns → … → 모델.

## 3. 콘솔에 남은 산출물 (쇼파일 상태)

- **Position 프리셋 2.21~2.30**: Home/Wall/Audience/Center/Vocal DSC/Fan Out/
  Fan In/Cross/Ring Out/Ring In (링 리그 기준 값)
- **Sequence 100 · Cue 1 'Rock Fast RGB Chase' · Executor 103**: Preset 2.28
  참조 포지션 + R→G→B 3스텝 체이스(Phase 0→360, Speed 128). 자립성 검증
  완료(빈 프로그래머에서 `Go+ Sequence 100` 재생). 현재 Off + ClearAll 상태
- 리그 좌표는 원본 링 레이아웃으로 비트 단위 복원됨

## 4. 이 세션이 계측한 함정 (스킬에 기록됨)

1. **명령 텍스트 중복 제거**: 같은 지시 안에서 동일 텍스트 줄은
   `skipped_already_executed` — 픽스처당 `Fixture <fid> ; …` 한 줄 체이닝 필수
   (실측 84/160 스킵)
2. **큐 페이저 평탄화**: 페이저 큐에 포지션만 든 프로그래머를
   `Store Cue /merge`하면 페이저가 죽는다(정지 무지개). 포지션 리콜+페이저를
   한 프로그래머 상태로 `/Overwrite`. 검증은 3D 두 프레임 픽셀 diff
3. **익스큐터 배정**: 검증 문법은 `Assign Sequence n At Executor m`;
   `At Page 1.4`는 Cannot Create Object. 페이지 컨테이너 슬롯 ≠ 익스큐터 번호
4. **프리셋 이름 중복**: MA3가 대소문자 무시하고 `#2` 접미사 자동 부여
5. **포트 9005 경합**: onPC(app_gma3)가 UDP 9005를 들고 있어 서버 시작이
   1회 실패할 수 있음 — 재시도로 해소됨. probe류(`tools/console_probe.py`,
   `pointing_probe.py`, `placement_verify.py`)는 서버 중지 후 사용

## 5. 검증·재현

```bash
uv run pytest server/tests/test_spatial_pointing.py server/tests/test_position_moods.py \
  server/tests/test_web_session.py server/tests/test_rulebook.py -q   # green
# 라이브: grandma3-web-stable 단일 서버(포트 8765) + WS. 예:
#  "모든 장비를 선택해서 불을 켜고 무대 바닥 중앙(0,0,0)…바라볼 수 있도록"
#  "기본 포지션 10개를 프리셋에 저장해줘" → 시작 번호 카드
#  "잔잔한 발라드 느낌으로 포지션 잡아줘" → 추천 카드
```

기존 실패 3건(test_prechk_tool 웹표면 가드 / test_songcue_bundle diff 가드 /
test_tools 레지스트리 중복)은 이 작업 이전부터 HEAD에 존재 — 별도 처리 필요.

## 6. 남은 확장 여지 (미착수)

- 직선 착지 부채살(바닥 등간격 점 FOCUS 역산 — pan 등간격 곡률 해소)
- 배치 자동 인식(classify_arrangement_topology)으로 배치별 10종 구성 차등
- Vocal −2m/1.6m, Ring reach 4m 등 상수의 무대 크기 비례화
- 무드 제안을 prepare_songcue와 결합한 곡 구간별 포지션 큐 시퀀스
- `Rotx`/`Roty` ≠ 0 리그의 조준 모델 계측
