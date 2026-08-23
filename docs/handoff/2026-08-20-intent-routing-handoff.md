# 2026-08-20 세션 핸드오프 — 배치 인식 이펙트 · 의도 프레임 라우팅

주제 하나로 이어진 세션이다: **"이펙트가 내가 생각한 것과 다르다"** 에서 출발해
원인을 좌표 실측으로 잡고, 페이저의 한계를 큐 시퀀스로 우회하고, 마지막에
**왜 코파일럿이 요청을 잘못 이해했는지**를 구조 문제로 규명해 고쳤다.

## 0. 지금 상태 (다음 세션 시작점)

| 항목 | 값 |
|---|---|
| HEAD | `main` (워킹트리 clean, 미추적 `server/llm/ollama_adapter.py`는 이 세션 산물 아님) |
| 열린 PR | **#67** INTENT-001 · **#68** PRESERVE 원복 · **#69** 헝크핀 재실측 — 셋 다 MERGEABLE·상호 독립 |
| 서버 | `copilot-web` 데몬 pid 19177, `http://127.0.0.1:8765`, health online |
| 콘솔 | grandMA3 onPC 2.4.2, 80대 리그(4겹 동심원 r=3·5·7·9m, 전원 z=6m) |
| 테스트 | `server/tests` 9,577 passed · #68·#69 머지 시 전체 그린 |

세션 중 만든 이펙트 12건은 **콘솔에 보존**했고 테스트 잔여물 8건은 삭제했다(§5).

## 1. 리그의 실제 기하 — 이 세션의 모든 것이 여기서 갈렸다

`get_spatial_context` 실측:

```
중심 (0.00, 0.00) · 전원 z = 6.0 m (수평 원)
링1  r=3 m  FID  1~20   0°,18°,36° … 342°   (Robin Esprite)
링2  r=5 m  FID 21~40   동일 각도 격자       (Robin LEDBeam 350)
링3  r=7 m  FID 41~60                        (Sharpy Plus)
링4  r=9 m  FID 61~80                        (Mac Aura XB)
```

**FID 순서와 무대 좌우는 무관하다.** FID 1은 x=+3.0(우측), FID 49~53은 x=−9.0(좌측).
좌→우 진행은 X좌표로 밴딩해야 하고(8밴드 × 10대), 회전은 azimuth 인덱스를
`mod 20`으로 돌려야 한다. 이 세션의 첫 시도가 FID 순서를 좌우로 가정해 틀렸고,
사용자가 "4겹 원형 디자인을 고려하면…"으로 정정해 줬다.

## 2. 만든 이펙트 (콘솔에 보존)

### 좌표 축 — 좌→우

| 시퀀스 | 이름 | 구조 |
|---|---|---|
| 600 | `Dye White2Blue L2R` | 9큐 누적 — 밴드 1..k Blue, 나머지 Cool White. 파랑이 차오르고 남는다 |
| 610 | `Blue Wave L2R` | 8큐 통과 — 크레스트(Blue) + 꼬리(Cyan) 이동, 지나가면 흰색 복귀 |

### 각도 축 — 회전

| 시퀀스 | 이름 | 구조 |
|---|---|---|
| 700 | `Rotate Wedge B/W` | 10큐 · 웨지 3스텝(54°) + 꼬리 2스텝 · 36°/큐 · 4겹 동시 |
| 710 | `Spiral Rotate B/W` | 링별 위상차 0/−36/−72/−108° → 나선 |
| 720 | `Counter Rotate B/W` | 링1·3 시계 / 링2·4 반시계 |

### 큐 체이스 어휘 예제

| 시퀀스 | 검증한 것 |
|---|---|
| 510 `RG Rotate Chase` | 8큐 `/CueOnly` Follow |
| 520 `Random Dim Chase` | 시드 1234 재현 가능 랜덤 |
| 530 `Soft Crossfade Wave` | 큐별 `CueFade 1.5` |
| 540 `Uneven Rhythm` | **큐별 개별 속도** 1.0/0.2/0.6/0.2 — 페이저 단일 속도원 한계 돌파 |
| 550 `BPM Chase` | `TrigType 'BPM'` |
| 560 `Sound Chase` | `TrigType 'Sound'` |
| 570 `Multi Attr Look Chase` | 컬러+팬/틸트+줌+디머 동시 순환 |

전 이펙트 합계 **콘솔 명령 276건 전건 `executed_ok`, skipped 0**.

## 3. 실측으로 확정한 문법·한계

| 항목 | 실측 |
|---|---|
| `Fixture <list> At Preset 4.8` | 유효 — 큐가 색 **참조**를 들고 있어 프리셋 수정이 전파된다 |
| `Set Cue <c> Sequence <s> Property 'TrigType' 'Follow'` | 유효 (룰북 31_choreography_patterns.md:106-117 확인) |
| `TrigType 'BPM'` + `TrigTime` | **`TrigTime`은 Illegal property.** 자가수정 4회(`Trigtime`·`TriggerTime`·`Trig`·`Trig Time`) 전부 Illegal. BPM 속도 속성은 **미규명** — 룰북 공백 |
| `Delete Sequence <n>` (배정된 시퀀스) | 콘솔 확인 팝업 → `User Canceled Command`. **`/nc` 옵션으로 해소** |
| `Copy Sequence <a> At <b>` (대상 점유) | 실패 → 앱이 복구 카드(`/overwrite` · 삭제 후 복사) 제시 |
| MAtricks 5축 | `PhaseFromX`·`PhaseToX`·`X`·`XWings`·`XShuffle` 전부 `compose_fx`로 실기 통과 |
| Phase 0=360 함정 | `PhaseToX 360`이 그대로 나감 — 첫·마지막 장비 동일값(문서 §2.2 재현) |

## 4. 고친 것 — SPEC-COPILOT-INTENT-001 (PR #67)

### 진단

`session.py`에 정규식 라우터 **109개 · 핸들러 29개**가 첫-매치-우선 `if/elif`
체인으로 늘어서 있다. 매치가 곧 행선지이므로:

| 실측 발화 | 잡아간 곳 | 결과 |
|---|---|---|
| `"원형 회전 R/G 컬러 페이저"` | `_POSITION_FX_VOCABULARY` circle | 팬/틸트 서클 생성 · 컬러 무시 |
| `"컬러만, 포지션이 아니라"` (2차) | 같은 정규식 | **명시적 부정 무시** · 재진입 |
| `"지금 이 큐 디머 30%"` | 결정적 경로 미스 → LLM 폴백 | 승인 없이 엉뚱한 `Sequence 1 Cue 1 /Merge` |

### 처방 (구현·머지 대기)

- **M1 하드 베토** — `포지션/무빙/빔/팬/틸트` + `아니·말고·제외·건드리지` → 좌표 판독 **앞**에서 후보 탈락, `None`으로 기존 폴백에 위임. `아니면`은 전방탐색 제외.
- **M2 축 카드 1장** — 컬러·디머가 주체이고 포지션 축 단어가 없으면 축을 카드로 확정. 속성축·무답이면 `None`(fail-closed).
- **M3 해석 고지** — `_axis_interpretation_note`가 `좌표 확인 80대 · X -9.0~9.0 · FID 순서가 아니라 콘솔 패치 좌표로` 를 회신에 싣는다.

증거: RED 6 failed → GREEN 8 passed · 회귀 406 passed · 라이브 수용 2/2
(재현 문장이 서클 흔적 0건으로 컬러 경로 이동, 스윕 회신에 해석 줄 등장).

### 이연 — 다음 세션의 1순위

- **M4** `server/effects/` 기하 생성기 6종(`wipe`/`wave`/`rotate`/`radial`/`scatter`/`pulse`) + 큐 프리뷰 편집. **§2의 5개 이펙트가 참조 구현이다** — 파이썬으로 집합을 계산해 넘긴 것들은 전건 성공했고(276/276), LLM 자유 조립은 아래 §6 ①을 유발했다.
- **M4 부수** 형제 핸들러(`_fx_position_presets`·`_phaser_recall`·`_basic_position_presets`) 베토 확장 (Q1 실측 선행).
- **M5** 사용자별 해석 기본값 세션 메모리.

정규식 109개 일괄 리팩터는 **의도적으로 제외**했다 — 첫-매치 순서에 얹힌 기존
계약(REQ-PRESETGUARD-015 등)을 동시에 흔든다.

## 5. 게이트 두 건 처분 — 반대 방향으로 갈랐다

| | PRESERVE 바이트핀 (PR #68) | 헝크 트립와이어 (PR #69) |
|---|---|---|
| 계약 | "한 바이트도 안 바뀌었다" | "무엇이 바뀌었는지 세어 보라" |
| 드리프트 원인 | 전역 `ruff format`이 4행 컴프리헨션을 1행으로 접음 (2회 재발) | PR #66 SPATIALMEM-001이 tools.py 변경 후 핀 미갱신 |
| 처분 | **원복** + `[tool.ruff.format] exclude` (lint는 유지) | **재실측** 66→65 + 원인 SPEC 명명 |
| 근거 | 갱신은 곧 계약 파기 | 파일 주석: `It is a TRIPWIRE, not a constant` |

**정정 기록**: 세션 중간에 "PRESERVE와 ruff가 상호 배타"라고 판정했으나 **오측**이었다.
ruff 게이트는 `_touched()` = `git diff BASE..HEAD -- *.py`로 대상을 뽑으므로, 핀
형태를 **커밋**하면 `preview.py`는 touched 집합에서 빠져 포매터 검사를 받지 않는다.
워킹트리에만 복원한 상태로 게이트를 돌려 양쪽이 동시에 붉게 보였던 것이다.
두 base(`95687a0`·`85a4b23`)의 `preview.py`가 바이트 동일함도 실측 확인했다.

## 6. 등재 — 고치지 않은 결함

① **번들 내 중복 명령 억제가 큐 체이스를 망가뜨린다.** MVP M6c-6의
"in-bundle duplicate re-execution" 방지가, 큐마다 정당하게 반복되어야 하는 값
라인을 삼킨다. 실측: 4큐 체이스에서 블랙아웃 3줄 스킵 → 트래킹으로 값 전진;
8큐에서 26줄 스킵 → **큐 5~8이 빈 프로그래머로 저장**. 회피는 라인을 유니크하게
구성하거나 큐당 번들 분리(둘 다 실증). 근본 수정은 `Store` 경계마다 dedupe
캐시 리셋.

② **`"지금 이 큐"` + 디머/페이드/FX가 승인 필수 경로를 우회한다.**
`_timeline_edit_target_position`이 포지션만 파싱해 나머지는 LLM 폴백으로 흐르고,
그 폴백이 stale한 Executor→Sequence 바인딩으로 승인 없이 병합했다. 별도 SPEC 대상.

③ **`Store Preset 22.2`가 21.25에 착지.** 명령은 `executed_ok`인데 판독은 다른
슬롯. 직전 `22.1`은 정상 착지. `Cmd()` 성공 보고 계열 함정으로 보이나 **추측하지
않고 관측만 등재** — `tools/console_probe.py`로 두 오브젝트 직접 판독 필요.

④ **BPM 트리거의 속도 속성 미규명** (§3).

⑤ **`Sequence 1 Cue 1`에 Dimmer 30%가 병합됨** (②의 결과). 병합 전 원래 값을
읽어두지 않아 **추측 복원을 하지 않았다.** 원 값을 아는 사람이 되돌려야 한다.

## 7. 콘솔 정리 내역

삭제(순수 테스트 잔여물): Sequence **2 · 201 · 400 · 410 · 420 · 430 · 500 · 800**.
`500 BW L2R Chase`는 FID 순서 오해 버전이라 함께 제거했다.

보존(검증된 산출물): Sequence **510~570 · 600 · 610 · 700 · 710 · 720** + Executor
107~118, Preset 전량(21.13~21.25 · 22.1~22.2 포함).

판독 검증: 삭제 잔존 0 · 보존 12/12 확인.

## 8. 다음 세션 진입점

1. **PR #67·#68·#69 머지** — 상호 독립, 순서 무관. #68·#69가 들어가면 `server/tests` 전체 그린.
2. **INTENT-001 M4** — 기하 생성기 + 큐 프리뷰. §2가 참조 구현, §6 ①이 이 작업이 해소하는 결함.
3. **§6 ③ 프로브** — `Store Preset` 착지 불일치 규명.
4. **§6 ⑤ 결정** — `Sequence 1 Cue 1` 디머 원복 여부·원 값.
