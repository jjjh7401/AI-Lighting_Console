# AddOnDesk Positions 기반 포지션 프리셋 생성 리서치

> 수집일: 2026-09-11  
> 출처: Facebook 공유 영상 2건, AddOnDesk `Positions` 제품 페이지, 공개 `Manual-Positions.pdf`  
> 범위: 유료 플러그인 내부 구현을 복제하지 않고, 공개 설명과 매뉴얼에서 확인 가능한 워크플로우를 AI Lighting Copilot의 포지션 프리셋 생성 모델로 재구성한다.  
> 한계: 플러그인 자체는 유료 상품이며, 실제 Lua/MA3 내부 구현과 계산식은 확인하지 않았다. 아래 내용은 공개 문구·매뉴얼 기반의 기능 요구사항/연동 모델이다.

## 1. 확인한 공개 정보

| 출처 | 확인 내용 |
|---|---|
| Facebook video `share/v/1CRiFKg2y4` → watch `v=924912120631427` | `Position Preset Plugin`은 기준 포지션을 보정한 뒤 complete position grid를 자동 생성한다. Pan/Tilt 값이 픽스처 간 matching되며 수동 프로그래밍 시간을 줄인다고 설명한다. |
| Facebook reel `share/r/1EeoFX8wCT` → reel `2247227516038212` | Add On Desk 릴스. "수준화된/보정된 참조 포지션에서 최대 180개의 매칭 포지션 프리셋 생성"이라는 설명이 보인다. |
| AddOnDesk product page | 가격 `79,00 € excl. Tax`, grandMA3 카테고리, 태그 `Workflow`, `Productivity`, `Presets`, `Setup`, `Position`. Version `25.12.65`. |
| AddOnDesk product page | 핵심 기능: 몇 개의 calibrated reference positions만으로 최대 180개의 perfectly matching position presets 생성. |
| 공개 manual PDF | 17페이지. Quick Guide, Calibration, Create Positions, Programmer Mode, Preset Mode, Merge/Duplicate, Troubleshooting, Known Limitations가 포함된다. |

## 2. 기능 핵심 요약

Positions 플러그인의 공개 설명을 요약하면 다음 구조다.

1. **기준 포지션 보정(Calibration)**: 픽토그램이 지시하는 기준 위치로 조명을 실제 무대에서 맞추고 `Apply Position`으로 저장한다.
2. **보정값 재사용**: 같은 fixture type에 대해 한 번 보정하면 이후 자동 포지션 생성에 사용한다.
3. **포지션 조합 생성**: 6개의 Tilt position과 30개의 Pan position을 조합해 최대 180개 포지션을 만든다.
4. **두 가지 생성 모드**:
   - Programmer Mode: 현재 Programmer에 선택된 일부 픽스처 대상으로 빠르게 계산하고 결과를 Programmer에 올린다.
   - Preset Mode: Group Pool에서 선택한 전체 그룹 대상으로 Position Preset Pool에 직접 저장한다.
5. **Merge/Duplicate 선택**: 같은 Tilt/Pan 조합을 다른 그룹/fixture type에 다시 만들 때 기존 프리셋에 병합할지, 새 프리셋 세트를 만들지 선택한다.
6. **제한**: 같은 물리 방향의 픽스처끼리만 함께 처리할 수 있다. X/Y/Z 축으로 서로 회전된 픽스처는 한 번에 처리하지 않는다.
7. **오차 보정**: 기계적 공차나 설치 오차는 grandMA3의 Store Offset workflow로 보정하는 것을 권장한다.

## 3. 공개 매뉴얼 기반 워크플로우

### 3.1 Calibration

매뉴얼 기준 절차:

1. 플러그인 시작.
2. 새 fixture type을 추가했거나 처음 사용하는 fixture type이면 먼저 보정해야 한다.
3. 포지션을 만들 fixture를 선택한다.
4. 플러그인이 픽토그램으로 기준 위치를 순서대로 안내한다.
5. 무대에서 선택된 픽스처를 해당 기준 위치로 Pan/Tilt 조준한다.
6. Programmer 또는 position attribute에 값이 들어 있는지 확인한다.
7. `Apply Position`을 눌러 현재 기준 위치를 저장한다.
8. 모든 calibration point가 저장될 때까지 반복한다.

확인/수정 절차:

- Calibration section 왼쪽의 expandable panel에서 모든 calibration positions를 볼 수 있다.
- 아래쪽 arrow button으로 특정 calibration position으로 이동해 확인하거나 수정할 수 있다.
- Navigation arrow로 각 calibration position을 순서대로 검토하고 필요하면 다시 `Apply`한다.
- 기본 mode는 `Merge`이며, `Overwrite`로 바꾸면 기존 calibration value가 새 값으로 대체되어 이전 보정 데이터가 손실될 수 있다.

Copilot 해석:

- Calibration은 자동 명령 생성보다 **operator-in-the-loop** 단계다.
- AI는 "어디를 봐야 하는지"와 "어떤 기준 포지션을 저장해야 하는지"를 안내하고, 저장 결과를 구조화해야 한다.
- 보정값이 틀리면 이후 생성되는 모든 포지션이 틀리므로, 자동 생성 전에 calibration verification 단계가 필수다.

### 3.2 Programmer Mode

매뉴얼 기준:

1. 현재 Programmer에 사용할 fixture를 선택한다.
2. 원하는 Tilt position을 선택한다.
3. 현재 선택된 fixture에 적용할 Pan position icon을 선택한다.
4. 계산된 position이 Programmer에 올라간다.
5. 사용자는 이를 Position Preset으로 저장하거나 Sequence에 직접 저장할 수 있다.

용도:

- 전체 그룹이 아니라 일부 픽스처만 빠르게 위치를 만들 때.
- 라이브 프로그래밍, 부분 선택, 빠른 수정.
- 자동 저장보다 디자이너가 결과를 보고 저장할 때.

Copilot 해석:

- `destination="programmer"`인 임시 계산 모드다.
- Copilot은 결과를 바로 저장하지 않고, 사용자에게 "현재 Programmer에 올렸으니 Position Preset 또는 Cue로 저장할 수 있다"라고 보고해야 한다.
- 안전하다. 기존 pool을 덮어쓰지 않기 때문이다.

### 3.3 Preset Mode

매뉴얼 기준:

1. 하나 이상의 Tilt position을 선택한다.
2. 생성할 Pan position을 선택한다.
3. Group Pool에서 적용할 group을 선택한다.
4. Position Preset Pool의 시작 위치를 정한다.
   - 자동으로 다음 빈 preset slot을 선택할 수 있다.
   - 사용자가 특정 preset slot을 직접 고를 수도 있다.
5. `Apply`를 누르면 선택된 Tilt × Pan 조합이 자동으로 Position Preset으로 생성된다.

예:

- Tilt 3개 × Pan 5개 = 15개 position preset.
- Tilt 6개 × Pan 30개 = 최대 180개 position preset.

Copilot 해석:

- `destination="preset_pool"`인 대량 생성 모드다.
- 시작 preset slot, 생성 개수, 충돌 여부, 기존 preset 처리 정책이 반드시 필요하다.
- 자동 빈 슬롯 탐색이 가능하더라도, 이 저장소의 원칙상 실제 콘솔에서 pool 상태를 읽고 충돌 가드를 둔 뒤 실행해야 한다.

### 3.4 Merge / Duplicate

매뉴얼 기준:

- `Merge`: 같은 Tilt/Pan 조합을 다른 fixture group 또는 fixture type에 다시 생성할 때 기존 position preset에 새 fixture 값을 병합한다.
- `Duplicate`: 같은 조합이 이미 있어도 새 position preset set을 별도로 만든다.

Copilot 해석:

- `Merge`는 기존 프리셋을 수정한다. 이미 Cue가 참조 중인 preset이면 공연 전체 룩에 영향을 줄 수 있다.
- `Duplicate`는 pool을 더 많이 쓰지만 기존 cue/preset 참조를 건드리지 않는다.
- 기본 추천:
  - 쇼 초반/프리셋 라이브러리 구축: `Merge`.
  - 리허설 중 안전한 실험/기존 큐 보존: `Duplicate`.
  - 이미 공연에 쓰인 preset: 자동 `Merge` 금지, 사용자 확인 필요.

### 3.5 Middle Mode

제품 페이지 Tips에 따르면:

- fixture group의 fixture 수가 홀수일 때 Settings gear에서 `Middle Mode`를 켤 수 있다.
- 홀수 fixture count의 계산을 최적화해 더 대칭적인 position layout을 만든다.

Copilot 해석:

- 그룹 fixture count가 홀수이면 `middle_mode=true` 후보를 제안한다.
- center fixture가 존재하는 배열은 좌우 mirrored pan 계산이 달라질 수 있으므로, odd/even fixture count를 position generation request에 포함한다.

## 4. 제한사항과 안전 가드

| 항목 | 공개 매뉴얼 내용 | Copilot 정책 |
|---|---|---|
| 같은 물리 방향 | 같은 physical orientation을 가진 fixture만 자동 생성 가능 | orientation group을 먼저 나눈다. truss별/fixture type별 분리 생성 |
| 회전된 설치 | X/Y/Z 축으로 서로 회전된 fixture, upside down, 90도 회전, 다른 pan/tilt orientation은 함께 처리 불가 | 한 그룹에 섞여 있으면 자동 생성 금지. 사용자가 그룹을 나누게 안내 |
| 설치 공차 | 작은 mechanical tolerance나 installation inaccuracy는 개별 조정 필요 | Store Offset workflow를 안내. 생성 프리셋 자체를 무작정 수정하지 않음 |
| 잘못된 calibration | incorrect calibration data는 모든 generated positions에 영향을 줌 | 생성 전 calibration review 필수. 대표 포지션 검증 후 대량 생성 |
| Overwrite | 기존 calibration value를 새 값으로 대체해 손실 가능 | 기본 `Merge`; `Overwrite`는 명시 확인 필요 |
| Preset Merge | 기존 position preset에 새 fixture 값을 병합 | 이미 사용 중인 preset이면 안전 확인 필요 |

## 5. Copilot 연동 모델

### 5.1 처리 파이프라인

| 단계 | 입력 | Copilot 내부 산출물 | grandMA3 연결 |
|---|---|---|---|
| 1. 요청 해석 | "무빙 포지션 프리셋 자동으로 잡아줘" | `PositionPresetRequest` | 아직 콘솔 명령 없음 |
| 2. 대상 분리 | fixture type, truss, orientation | `OrientationGroup[]` | Group / Fixture selection |
| 3. Calibration 확인 | reference positions 존재 여부 | `CalibrationProfile` | Position Preset 또는 plugin/cue data |
| 4. 생성 계획 | tilt set, pan set, mode | `PositionGridPlan` | Programmer 또는 Preset Pool |
| 5. 저장 정책 | merge/duplicate/overwrite | `StorePolicy` | Preset Pool 충돌 가드 |
| 6. 실행 | command bundle / operator step | `ExecutionPlan` | OSC `run_commands`, manual operator step |
| 7. 검증 | 샘플 포지션 관측 | `PositionReport` | 대표 preset call + 시각 확인 |

### 5.2 공통 요청 스키마

```json
{
  "intent": "create_position_presets",
  "target": {
    "group_label": "MOVER-U",
    "fixture_type": "moving_profile",
    "orientation_group": "upstage_truss_same_orientation"
  },
  "calibration": {
    "profile_id": "MOVER-U-default",
    "required": true,
    "status": "verified"
  },
  "grid": {
    "tilt_positions": ["near", "mid", "far"],
    "pan_positions": ["SL", "CSL", "C", "CSR", "SR"],
    "middle_mode": false
  },
  "mode": "preset",
  "store": {
    "destination": "position_preset_pool",
    "start_slot": "next_free",
    "policy": "duplicate"
  },
  "safety": {
    "same_orientation_only": true,
    "allow_overwrite": false,
    "requires_store_offset_review": true
  }
}
```

### 5.3 Copilot 기능으로 나눌 작업

| 기능 | 자동화 가능성 | 이유 |
|---|---|---|
| Group/fixture type 분류 | 높음 | patch metadata와 group label에서 추론 가능 |
| orientation group 분리 | 중간 | 정확한 physical orientation은 도면/patch/사용자 확인 필요 |
| calibration 안내 | 높음 | 기준 포지션을 순서대로 제시하고 사용자가 조준 |
| calibration 값 저장 | 중간 | 콘솔 command path 검증 필요. 기존 position preset 저장은 가능하나 read-back 한계 있음 |
| Pan/Tilt grid 계산 | 낮음~중간 | MAgics 내부 계산식은 미확인. 자체 구현하려면 stage coordinate/fixture orientation 모델 필요 |
| Programmer Mode 흉내 | 중간 | 사용자 선택 fixture에 계산/호출 결과를 올리는 방식은 가능하지만 값 검증 필요 |
| Preset Mode 흉내 | 중간 | 다량 preset 생성은 가능하나 pool 충돌/merge semantics 가드 필요 |
| Store Offset 안내 | 높음 | 오차 보정 workflow를 사용자에게 안내하는 것은 가능 |

핵심 결론: Copilot v1은 유료 플러그인의 자동 계산을 그대로 복제하려 하기보다, **보정-검증-생성 계획-저장 가드**를 제공하고, 실제 Pan/Tilt 계산은 검증된 console path 또는 사용자 확인 루프를 거쳐 단계적으로 확장하는 편이 안전하다.

## 6. 콘솔 연결 방식

### 6.1 Programmer Mode에 해당하는 Copilot 흐름

```text
사용자: "MOVER-U 중 1~6번만 center-mid 포지션 잡아줘"

Copilot:
1. Fixture/Group 선택 범위를 확인한다.
2. 해당 fixture type의 calibration profile이 있는지 확인한다.
3. 없으면 calibration runbook을 제시한다.
4. 있으면 target pan/tilt 후보를 Programmer에 올리는 command bundle을 만든다.
5. 저장은 자동으로 하지 않고 "Preset으로 저장 / Cue로 저장" 선택지를 제시한다.
```

필요한 내부 객체:

- `target_selection`
- `calibration_profile`
- `requested_pan_position`
- `requested_tilt_position`
- `destination="programmer"`

### 6.2 Preset Mode에 해당하는 Copilot 흐름

```text
사용자: "업스테이지 무빙 전체에 3단 틸트, 5점 팬 포지션 프리셋 만들어줘"

Copilot:
1. 업스테이지 무빙 그룹을 찾는다.
2. 같은 orientation인지 확인한다.
3. Tilt 3개 × Pan 5개 = 15개 preset 생성 계획을 보여준다.
4. Position Preset Pool 시작 슬롯을 측정하거나 사용자에게 받는다.
5. 기존 preset 충돌을 확인한다.
6. policy가 Duplicate이면 새 슬롯에 저장한다.
7. 대표 3개 preset을 호출해 사용자 관측을 받는다.
```

필요한 내부 객체:

- `orientation_group`
- `tilt_positions[]`
- `pan_positions[]`
- `preset_count`
- `start_slot`
- `store_policy`
- `sample_verify_positions[]`

### 6.3 Calibration runbook

```text
1. 대상 fixture type 또는 group을 선택한다.
2. 기준 포지션 이름을 화면에 제시한다.
   예: Center Near, Center Mid, Center Far, Stage Left, Stage Right 등
3. 사용자가 실제 무대에서 조명을 해당 위치로 조준한다.
4. Copilot은 해당 값을 CalibrationProfile의 reference point로 저장한다.
5. 모든 reference point가 끝나면 대표 조합을 만들어 검증한다.
6. 검증 실패 시 calibration부터 다시 확인한다.
```

중요: 공개 매뉴얼은 플러그인이 픽토그램을 사용한다고 설명한다. Copilot은 HTML/UI에서 간단한 stage grid와 point label을 보여 주는 방식으로 같은 사용자 경험을 제공할 수 있다.

## 7. 자연어 매칭 사전 후보

| 사용자 표현 | 라우팅 |
|---|---|
| "포지션 프리셋 자동으로 만들어줘" | `create_position_presets` |
| "기준 포지션 보정해줘" | `calibrate_position_profile` |
| "팬 5점, 틸트 3단으로" | `grid.pan_count=5`, `grid.tilt_count=3` |
| "무빙 전체 포지션팩" | `mode="preset"`, group-based |
| "선택한 장비만 현재 프로그래머에 올려" | `mode="programmer"` |
| "다른 그룹도 같은 프리셋에 합쳐" | `store.policy="merge"` |
| "기존 거 건드리지 말고 따로 만들어" | `store.policy="duplicate"` |
| "홀수 대라 가운데 기준으로 대칭 맞춰" | `middle_mode=true` |
| "틀어진 장비 보정" | `store_offset_review` |
| "트러스별로 따로 만들어" | `orientation_group_by="truss"` |

## 8. Copilot 구현 후보

| 후보 ID | 기능 | 입력 | 출력 | 안전 조건 |
|---|---|---|---|---|
| `position-calibration-runbook` | 기준 포지션 보정 안내 | group, fixture type, reference points | CalibrationProfile draft | 사용자 조준 확인 필수 |
| `position-grid-plan` | Tilt × Pan 조합 계획 | tilt set, pan set, target group | preset count, naming plan | 같은 orientation group만 |
| `position-programmer-apply` | 선택 fixture에 포지션 후보 적용 | selection, one pan/tilt pair | Programmer values | 자동 저장 금지 |
| `position-preset-batch` | position preset 대량 생성 | group, grid, start slot | position preset set | pool 충돌 확인 |
| `position-merge-existing` | 기존 preset에 fixture group 병합 | existing preset set, new group | merged preset | 이미 사용 중이면 확인 |
| `position-duplicate-set` | 새 preset set 생성 | group, grid | duplicate preset collection | pool 공간 확인 |
| `position-store-offset-guide` | 설치 오차 보정 안내 | misaligned fixture report | Store Offset runbook | generated preset 직접 덮어쓰기 금지 |

## 9. AI Lighting Copilot에 넣을 때의 결론

1. 포지션 프리셋 자동화의 본질은 "많은 preset을 빠르게 Store"가 아니라 **기준 보정값을 신뢰할 수 있게 만드는 것**이다.
2. 사용자에게는 "몇 개 Pan/Tilt를 만들까요?"보다 먼저 "같은 방향으로 설치된 장비끼리 묶었나요?"를 물어야 한다.
3. `Programmer Mode`와 `Preset Mode`를 분리해야 한다. 전자는 안전한 미리보기, 후자는 pool write가 있는 대량 생성이다.
4. `Merge`는 편하지만 위험하다. 기존 cue가 참조 중인 preset에 영향을 줄 수 있으므로, Copilot 기본값은 `Duplicate` 또는 사용자 확인이어야 한다.
5. Store Offset은 핵심 후처리다. 포지션 생성 후 일부 장비가 미세하게 어긋나면 preset을 다시 만들기보다 offset workflow를 안내해야 한다.
6. 공개 자료만으로는 MAgics 기반 계산식을 확인할 수 없다. Copilot은 첫 단계에서 operator-guided calibration과 runbook형 자동화를 제공하고, 실제 Pan/Tilt 계산 자동화는 별도 실측이 필요하다.

