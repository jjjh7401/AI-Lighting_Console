# t573 run verdict — 박자 격자 송신 디머 속성을 그룹별로

- 카드: t573 · SPEC-LDBEAT-001 REQ-011~013(송신)
- 브랜치: `WT-dimmer-per-group` · 기준 `origin/main` 63de8d95
- 실기 콘솔 쓰기: 0건 (FakeConsole + 판독 대역만)

## 무엇이 바뀌었나

| 파일 | 변경 |
|---|---|
| `server/design/beat_grid_send.py` | `resolve_group_dimmer_attributes(rig, group_names, group_members)` 신설 — `(속성 표, 사유 표)` |
| `server/design/beat_grid_emit.py` | `dimmer_attribute_reasons` 선택 인자 — 못 고른 트랙의 밝기 값 칸이 구체 사유로 막힌다(없으면 기존 일반 사유) |
| `server/web/session.py` | 송신 경로가 `_beat_grid_group_members` 로 소속을 읽어(`read_beat_grid_stage` 재사용, 전수 그룹만) 새 함수를 부른다 |
| `server/tests/test_beat_grid_dimmer_per_group_t573.py` | 13건 |

그룹 하나를 고르는 규칙:

1. 소속을 안다(전수) → 소속 장비 **전부**의 능력이 전수이고 디머 튜플이 하나로 같으면 그 튜플.
2. 소속 장비 중 능력 미판독·부분 판독이 있으면 → 그 트랙만 사유(fid 목록)로 막는다.
3. 한 그룹에 디머 튜플이 다른 장비가 섞여 있으면 → 그 트랙만 막는다(합집합은 실기로 잰 적이 없어 내지 않는다).
4. 소속을 모른다(경로 없음·판독 실패·`complete: False`) → 기존 「리그 전 기종 같음」 규칙으로 되돌아간다. 그것도 안 되면 사유로 막는다.

기종 이름·속성 이름 상수: 0건 — `grep -n -i -e spiider -e "'Dimmer" -e '"Dimmer' server/design/beat_grid_send.py server/design/beat_grid_emit.py` → 기존 `"dimmer_preset"` 모드 이름 1줄뿐(속성 상수 아님). 속성은 `dimmer_attribute_names(capability.attributes)` 로만 걸러 온다.

## 증거 (이 트리, 63de8d95 + 이 변경)

```
$ uv run pytest -q -p no:cacheprovider server/tests/test_beat_grid_dimmer_per_group_t573.py
13 passed in 0.32s

$ uv run pytest -q -p no:cacheprovider <t573 + t563 send/web + t572 reapply + t549 emit + t576 entry
  + t578 console play + stage + t553 + t548 + write_dispatch_census>
181 passed, 1 skipped, 1 warning in 5.66s

$ make ci-local      # fmt + lint + test-fast
exit=0
```

송신 경로 시험(`TestSendPathPicksPerGroup`)이 실제 FakeConsole 에 나간 줄로 확인한 것:
`Group 4 ; Attribute 'Dimmer' At 60` + `Group 4 ; Attribute 'Dimmer2' At 60` (두 디머 그룹),
`Group 5 ; Attribute 'Dimmer' At 60` 만 (한 디머 그룹), `Group 6` 줄 0건 + 사유 「섞여」(섞인 그룹).

## 안 잰 것

- 실기 콘솔 0회. `member_fids`(무대 판독의 FID)와 `RigCapabilities.fixtures` 키(FID)가 같은 번호 공간이라는 것은 **코드 판독**이다(둘 다 FID 프로퍼티 기원) — 실기로 대조하지 않았다.
- 섞인 그룹에 디머 속성 합집합을 보냈을 때 콘솔이 없는 속성을 무시하는지는 재지 않았다 — 그래서 막는 쪽을 택했다.
- 송신마다 무대 판독(좌표 포함)을 한 번 더 한다 — 읽기 왕복이 늘지만 쓰기는 0이다. 부하는 재지 않았다.
- 전체 pytest(153s)는 돌리지 않았다 — CI 몫.
