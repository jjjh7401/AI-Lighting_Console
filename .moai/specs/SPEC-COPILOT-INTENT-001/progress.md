---
id: SPEC-COPILOT-INTENT-001
document: progress
version: "0.1.0"
updated: 2026-08-19
status: in-progress
---

# §0 현재 상태

- **status**: in-progress (M1~M3 완료 · M4·M5 이연)
- **AC**: 8/8 자동 PASS · 2/2 라이브 PASS
- **회귀**: `server/tests` 9583 passed · 6 skipped · 3 failed(전부 선행 결함, §F.1)
- **변경 파일**: `server/web/session.py` · `server/tests/test_web_session.py` (2개)

# §E.1 사전 실측 (재현 케이스)

2026-08-19 라이브 세션에서 관측된 오라우팅 4건 — spec.md §0 표. 이 SPEC은 그중 **①②(어휘 하이재킹·부정 무시)** 와 **④(기하 해석 미고지)** 를 대상으로 한다. ③(`"지금 이 큐"` + 디머 폴백)은 범위 밖(§3).

# §E.2 run-phase 증거

## RED

```
$ .venv/bin/python -m pytest -q server/tests/test_web_session.py -k IntentFrame
6 failed, 2 passed, 398 deselected in 1.98s
```
실패 문면 발췌 — 베토 미구현으로 좌표 판독이 발생:
```
Left contains one more item: ToolCall(id='position-fx-read', name='get_spatial_context', arguments={})
AssertionError: assert 0 == 1   # 축 카드 0장
AssertionError: assert '좌표 해석' in '좌우 스윕 포지션 이펙트를 시퀀스 201에 …'
```

## GREEN

```
$ .venv/bin/python -m pytest -q server/tests/test_web_session.py -k IntentFrame
8 passed, 398 deselected in 1.08s

$ .venv/bin/python -m pytest -q server/tests/test_web_session.py
406 passed in 2.09s
```

## 라이브 수용 (앱 재시작 후, pid 69483)

**AC-INTENT-007 — 부정 하드 베토**

입력: `"컬러 페이저만 만들어줘, 포지션은 건드리지 말고. 원형으로 도는 색 시퀀스로."`

```
서클 빌더 흔적(Preset 2.x · 'Pan' · 'Tilt'): 없음
실행된 명령: ChangeDestination Root / ClearAll / Group 1 /
             Attribute 'ColorRGB_R' At 100 / … / Store Preset 22.2 'Rainbow Wave' /Universal
```
동일 계열 문장이 2026-08-19에는 두 번 연속 팬/틸트 서클 빌더로 갔다(`Store Sequence 201 Cue 1 'Circle'`). 이제 컬러 경로로 간다.

**AC-INTENT-008 — 해석 문장**

입력: `"좌우 스윕 포지션 이펙트 시퀀스 800 만들어줘, FX 프리셋 41번부터"`

```
좌표 해석: 좌표 확인 80대 · X -9.0~9.0 · Y -9.0~9.0 m
           — FID 순서가 아니라 콘솔 패치 좌표로 배치를 판단했습니다.
Store Sequence 800 Cue 1 'Sweep L' CueFade 2      executed_ok
Store Sequence 800 Cue 2 'Sweep R' CueFade 2 /Merge  executed_ok
```

# §F.1 선행 결함 등재 (이 SPEC이 고치지 않음)

| # | 결함 | 근거 | 처분 |
|---|---|---|---|
| 1 | `preview.py`가 PRESERVE 핀 형태(4행 컴프리헨션)에서 ruff 형태(1행)로 드리프트한 채 HEAD에 있다. 커밋 `6d0b58c`가 한 번 원복했으나 재발했다. | `git diff 95687a0..HEAD -- server/web/preview.py` = `1 insertion(+), 5 deletions(-)` | **별도 PR로 해소** — SPEC-COPILOT-INTENT-001 범위 밖이므로 분리 커밋 |
| 2 | `tools.py` 헝크핀 드리프트 (`test_tools_hunks_are_only_songcue_registration…`) | 본 SPEC은 `tools.py` 미변경. clean HEAD(stash 상태)에서 동일 재현 | 등재만 |
| 3 | `TestSidecarSelfReap::…without_a_pipe` 타이밍 플레이크 | 단독 재실행 시 PASS | 등재만 |
| 4 | 형제 핸들러(`_fx_position_presets`·`_phaser_recall`·`_basic_position_presets`)에 동일 베토 부재 | 코드 실측 — 베토는 `_position_fx_sequence`에만 삽입 | **M4** |
| 5 | `"지금 이 큐" + 디머/페이드/FX`가 승인 필수 경로를 우회 (`_timeline_edit_target_position`이 포지션만 파싱) | 2026-08-19 실측 — 승인 없이 `Store Sequence 1 Cue 1 /Merge` | 별도 SPEC 대상 |

# §G 다음 세션 진입점

1. **M4** — `server/effects/` 기하 생성기 6종(`wipe`/`wave`/`rotate`/`radial`/`scatter`/`pulse`) + 큐 프리뷰. 이번 세션에서 파이썬으로 수동 생성한 5개 이펙트(`Sequence 600·610·700·710·720`, 총 276 명령 전건 `executed_ok`·skipped 0)가 그 생성기의 참조 구현이다.
2. **M4 부수** — §F.1 #4 형제 핸들러 베토 확장 (Q1 실측 선행).
3. **해소됨** — §F.1 #1은 별도 PR(`fix(preserve)`)에서 핀 형태 복원 + 포매터 전용 제외로 처리했다. 초판의 "PRESERVE ↔ ruff 상호 배타" 판정은 **오측이었다**: ruff 게이트는 `_touched()` = `git diff BASE..HEAD -- *.py` 로 대상을 뽑으므로, 핀 형태를 **커밋**하면 `preview.py`는 touched 집합에서 빠져 포매터 검사 자체를 받지 않는다. 오측의 원인은 워킹트리에만 복원한 상태에서 게이트를 돌린 것 — HEAD는 여전히 드리프트 형태였으므로 touched에 남아 있었다. 두 base(`95687a0`·`85a4b23`)의 `preview.py`는 바이트 동일함을 실측 확인했다.
