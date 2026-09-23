# t455 · t456 판정서 — 런북 화면용 서버 데이터

- 카드: t455(행 단위 컨셉 표 + 짝짓기), t456(구간 색 HEX) — 클래스 C, SPEC-LDDESIGN-001 M7
- 브랜치: `WT-runbook-payload` · 기준 `origin/main` `36da2f92`
- 콘솔 쓰기: 0건 (순수 계산 경로와 가짜 포트만 사용)
- 원칙: 기존 payload 키는 그대로 두고 추가만 했다(lane-1 t454가 지금 키로 화면을 짓는 중). 원천이 없는 값은 `null`로 둔다.

## 1. 착수 전 실측 — 짝짓기 재료

명령: `.venv/bin/python .moai/reports/t455/measure_rows.py` → `measure_rows.out.txt` (t454와 같은 8구간 곡, 120 BPM)

- 컨셉 행 20 = safety 2 + section 8 + phrase 10. section 행 8개는 화면 구간 8개와 수와 순서가 같다.
- phrase 중 `Pre-Chorus` 3행(q5·9·14)은 화면에 없는 이름이다. 시각상으로는 앞 구간(Verse 1·Verse 2·Bridge) 안에 있다.
- 재매핑이 `Outro`를 `Rap/Solo/Dance Break`로 바꾼다. `Finale`만 Outro로 처리하는 기존 동작이며, 범위 밖이라 기록만 한다.
- 원샷 3개는 ts가 해당 section 행의 ts와 같다(density가 `occ.start`로 만든다).
- 근거 등급: 큐마다 등급을 매기는 생산자가 0곳이다. `CueV2(` 호출이 0곳이고, `EVIDENCE_FOR_*` 상수도 쓰는 곳이 0곳이다.

## 2. 짝 규칙 (리드 승인 2026-09-23)

1. k번째 `kind=section` 행 ↔ 화면 구간 k(순서 기준).
2. phrase 행(Pre-Chorus 포함)은 바로 앞 section 행과 같은 화면 구간에 붙는다.
3. safety 행은 `null`이다(곡 구간 바깥).
4. 원샷은 ts가 같은 section 행에 `one_shot: {shot, target}`으로 붙는다.
5. section 행 수와 화면 구간 수가 다르면 짝을 짓지 않는다. 모든 행이 `screen_position: null`이 되고 `row_pairing: {available: false, reason}`으로 알린다. 추측하지 않는다.

**시각 기준을 버린 이유:** 다리(`session_bridge._mmss_from_ms`)가 ms를 초 단위로 버림한다. 그래서 15.5초에 시작하는 구간의 행은 ts 15가 되고, 앞 구간에 잘못 붙는다.

**이름+회차 기준을 버린 이유:** `Pre-Chorus`는 화면 구간 이름이 아니고, 재매핑이 이름을 바꾼다(`Outro` → `Rap/Solo/Dance Break`).

근거 등급은 리드 결정 A에 따라 전 행 `null`이다. 생산자 배선은 카드 t457로 분리됐다.

## 3. 변경

| 파일 | 내용 |
|---|---|
| `server/design/color_names.py` | `color_hex(name)` 추가. `resolve_color_name` 결과(0-100)를 0-255로 반올림해 `#RRGGBB`로 낸다. 못 찾으면 `None`. |
| `server/web/session.py` | 구간 행에 `palette_primary_hex`·`palette_secondary_hex` 추가. 키는 항상 있고, 해석하지 못하면 값이 `None`이다. |
| `server/concept/session_bridge.py` | `_concept_rows` 추가. `concept_report`에 `rows`·`row_pairing` 추가. 모듈 독스트링의 t452 격차 항목을 해소됨으로 고치고(리드 허가), 짝 규칙을 적었다. |
| `server/tests/test_runbook_payload_t455_t456.py` | 신규 13건 |

행 필드: `q · ts · kind · section · occurrence · trigger · tracking · mib(dark/mark/live/null) · one_shot · evidence · screen_position`. 흰색은 `color_names.py`가 일부러 배선하지 않았으므로 `None`이다. 경계를 그대로 유지했고, UI 쪽 색 표 복제는 없다.

## 4. 검증

| 주장 | 명령 | 관측 |
|---|---|---|
| RED | `pytest server/tests/test_runbook_payload_t455_t456.py` (구현 전) | `ImportError: cannot import name '_concept_rows'` (`pytest_red.txt`) |
| GREEN | 같은 명령 | `13 passed` (`pytest_green.txt`) |
| 영향 범위 | `xargs pytest < scoped_files.txt` (78개 파일: 컨셉·후렴색·곡·songcue·큐시트·웹 세션·overlap 가드·관련 grep) | `1819 passed, 2 skipped` (`pytest_scoped.txt`) |
| 변이 1 | 수 불일치일 때도 짝을 짓게 바꾸고 재실행 → 원복 | `1 failed, 12 passed` |
| 변이 2 | 원샷을 phrase 행에도 붙이고 위치를 한 칸 밀어 재실행 → 원복 | `1 failed, 12 passed` |
| 실제 payload | `.venv/bin/python .moai/reports/t455/measure_payload_after.py` | `measure_payload_after.out.txt` — Blue `#0D33FF` · Amber `#FF8C0D` · Warm White `#FFBF66` · 흰색/gold/핑크 `None`. `row_pairing {available: True}`, 20행 |
| 린트 | `ruff check` / `ruff format --check` (변경 파일 + 증거 스크립트) | 통과 (`ruff_check.txt`) |

## 5. 안 잰 것 (Gaps)

- **UI는 건드리지 않았다.** `ui/src/protocol.ts` 타입에 새 필드를 추가하지 않았다. lane-1이 t454에서 같은 파일을 고치는 중이라 충돌을 피했다. 화면 반영은 lane-1 몫이다.
- **MIB `live`는 실제 출력에서 한 번도 안 나왔다.** 이 픽스처에서는 `dark`·`mark`·`null`만 관측됐다. `live`는 해석기 어휘상 가능한 값일 뿐이다.
- **짝이 안 맞는 경우는 함수를 직접 불러 시험했다.** `screen_count=7`을 억지로 넣었다. 실제 곡에서 수가 어긋나는 경로는 찾지 못했다(두 어댑터 모두 구간 목록을 1:1로 넘긴다).
- **tools.py 경로(`prepare_songcue`)의 `rows`는 따로 시험하지 않았다.** 같은 공통 실행기를 타므로 키는 생기지만, 그 경로에는 화면 구간 목록이 없다.
- 전체 시험 묶음은 로컬에서 돌리지 않았다. CI에 맡긴다.

## 6. 잔여 위험

- `Outro` → `Rap/Solo/Dance Break` 재매핑은 행의 `section` 값에 그대로 보인다. 화면이 이 값을 구간 이름으로 쓰면 감독에게 틀린 이름이 보인다. 화면은 `screen_position`으로 화면 구간의 `label`을 읽어야 한다.
- 원샷 짝은 ts가 정확히 같을 때만 붙는다. density가 원샷 ts를 section 시작과 다르게 만들도록 바뀌면 조용히 `null`이 된다.
