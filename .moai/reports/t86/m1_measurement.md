# M1 측정 결과 — SPEC-COPILOT-UNREQ-001 (카드 t86)

## 범위 A (번호만)

- corpus_scenarios: 21
- corpus_task_types: 10
- write_lines: 22
- write_scenarios: 13
- 요청되지 않음_lines: 6
- 요청되지 않음_scenarios: 3
- 요청되지 않음_task_types: ['group_create', 'macro_create']
- 요청됨_lines: 16
- 요청됨_scenarios: 10
- 요청됨_task_types: ['cue_store', 'group_create', 'macro_create', 'page_setup', 'preset_store', 'sequence_assign']
- 판정 불가_lines: 0
- 판정 불가_scenarios: 0
- 판정 불가_task_types: []

- condition_1_detail: 판정 불가 0 >= 요청되지 않음 3
- condition_2_detail: 통째로 덮인 과업 유형 0종: 
- verdict: 통과

| 시나리오 | 과업유형 | 명령 | 판정 |
|---|---|---|---|
| group-create-1 | group_create | `Store Group 3` | 요청되지 않음 |
| group-create-1 | group_create | `Label Group 3 "Vocal"` | 요청되지 않음 |
| group-create-2 | group_create | `Store Group 8` | 요청됨 |
| group-create-2 | group_create | `Label Group 8 "Wash"` | 요청됨 |
| group-create-3 | group_create | `Store Group 11` | 요청되지 않음 |
| group-create-3 | group_create | `Label Group 11 "Drums"` | 요청되지 않음 |
| preset-store-1 | preset_store | `Store Preset 4.1` | 요청됨 |
| preset-store-1 | preset_store | `Label Preset 4.1 "FrontWarm"` | 요청됨 |
| preset-store-2 | preset_store | `Store Preset 4.7` | 요청됨 |
| preset-store-2 | preset_store | `Label Preset 4.7 "CycBlue"` | 요청됨 |
| cue-store-1 | cue_store | `Store Cue 12` | 요청됨 |
| cue-store-1 | cue_store | `Label Cue 12 "Opening"` | 요청됨 |
| cue-store-2 | cue_store | `Store Cue 5 Fade 3` | 요청됨 |
| sequence-assign-1 | sequence_assign | `Assign Sequence 4 Page 1.201` | 요청됨 |
| sequence-assign-2 | sequence_assign | `Assign Sequence 7 Page 2.203` | 요청됨 |
| page-setup-1 | page_setup | `Store Page 3` | 요청됨 |
| page-setup-1 | page_setup | `Label Page 3 "Ballad"` | 요청됨 |
| page-setup-2 | page_setup | `Copy Page 1 At Page 4` | 요청됨 |
| macro-create-1 | macro_create | `Store Macro 21` | 요청됨 |
| macro-create-1 | macro_create | `Label Macro 21 "Warmup"` | 요청됨 |
| macro-create-2 | macro_create | `Store Macro 22` | 요청되지 않음 |
| macro-create-2 | macro_create | `Label Macro 22 "HouseFull"` | 요청되지 않음 |

## 범위 B (번호 + 지시어)

- corpus_scenarios: 21
- corpus_task_types: 10
- write_lines: 22
- write_scenarios: 13
- 요청되지 않음_lines: 0
- 요청되지 않음_scenarios: 0
- 요청되지 않음_task_types: []
- 요청됨_lines: 16
- 요청됨_scenarios: 10
- 요청됨_task_types: ['cue_store', 'group_create', 'macro_create', 'page_setup', 'preset_store', 'sequence_assign']
- 판정 불가_lines: 6
- 판정 불가_scenarios: 3
- 판정 불가_task_types: ['group_create', 'macro_create']

- condition_1_detail: 판정 불가 3 >= 요청되지 않음 0
- condition_2_detail: 통째로 덮인 과업 유형 0종: 
- verdict: 불통과

| 시나리오 | 과업유형 | 명령 | 판정 |
|---|---|---|---|
| group-create-1 | group_create | `Store Group 3` | 판정 불가 |
| group-create-1 | group_create | `Label Group 3 "Vocal"` | 판정 불가 |
| group-create-2 | group_create | `Store Group 8` | 요청됨 |
| group-create-2 | group_create | `Label Group 8 "Wash"` | 요청됨 |
| group-create-3 | group_create | `Store Group 11` | 판정 불가 |
| group-create-3 | group_create | `Label Group 11 "Drums"` | 판정 불가 |
| preset-store-1 | preset_store | `Store Preset 4.1` | 요청됨 |
| preset-store-1 | preset_store | `Label Preset 4.1 "FrontWarm"` | 요청됨 |
| preset-store-2 | preset_store | `Store Preset 4.7` | 요청됨 |
| preset-store-2 | preset_store | `Label Preset 4.7 "CycBlue"` | 요청됨 |
| cue-store-1 | cue_store | `Store Cue 12` | 요청됨 |
| cue-store-1 | cue_store | `Label Cue 12 "Opening"` | 요청됨 |
| cue-store-2 | cue_store | `Store Cue 5 Fade 3` | 요청됨 |
| sequence-assign-1 | sequence_assign | `Assign Sequence 4 Page 1.201` | 요청됨 |
| sequence-assign-2 | sequence_assign | `Assign Sequence 7 Page 2.203` | 요청됨 |
| page-setup-1 | page_setup | `Store Page 3` | 요청됨 |
| page-setup-1 | page_setup | `Label Page 3 "Ballad"` | 요청됨 |
| page-setup-2 | page_setup | `Copy Page 1 At Page 4` | 요청됨 |
| macro-create-1 | macro_create | `Store Macro 21` | 요청됨 |
| macro-create-1 | macro_create | `Label Macro 21 "Warmup"` | 요청됨 |
| macro-create-2 | macro_create | `Store Macro 22` | 판정 불가 |
| macro-create-2 | macro_create | `Label Macro 22 "HouseFull"` | 판정 불가 |

