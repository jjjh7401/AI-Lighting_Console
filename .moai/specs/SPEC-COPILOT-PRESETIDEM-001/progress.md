---
id: SPEC-COPILOT-PRESETIDEM-001
kind: progress
updated: 2026-08-25
---

# 진행 기록 — SPEC-COPILOT-PRESETIDEM-001 (카드 t87)

## §E 실행 증거

### E.1 착수 게이트 (구현 전)

축 (a) 는 「콘솔이 CSV Name 을 바이트 그대로 저장한다」에 걸려 있었고,
그것이 어긋나면 held 가 6이 아니라 0이 되어 카드가 막으려던 복제가 그대로
일어난다. 그래서 **구현 착수의 게이트**로 다뤘다.

- 명령: `python -m server.tools.lxseq_presets_e2e --preset-csv <정본 dim> --action preview --limit 0 --listen-port 9005`
- 날조 대조군 `Patch/FixtureTypesZZZNotAThing/9999` → `ok=false`
- `DataPool/PresetPools/1` → 6건, `truncated=false`
- 6/6 `byte_equal`
- 증거: `.moai/reports/t87/gate-name-roundtrip.md` · `name-roundtrip.json` (커밋 a93f51c)
- 리드가 원격에서 독립 재집계했다

**배차서 이탈 1건 (리드 승인)**: 배차서는 `--probe-only` 를 지정했으나 그 갈래는
프리셋 풀을 안 읽는다(`lxseq_presets_e2e.py:186-187` — 기준선만 읽고 멈춘다).
풀 이름이 나오는 유일한 읽기 전용 경로가 `--action preview` 라 그것을 썼다.
preview 는 명령을 만들기 전에 반환하므로(`tools.py:4863`) 콘솔 쓰기 0.

### E.2 결함 재현 (읽기 전용)

풀에 6건이 점유된 상태에서 매퍼가 슬롯 **7, 8, 9, 10, 11, 12** 를 계획하고
`held` 는 비어 있었다. 카드의 주장이 실기로 재현됐다.

### E.3 구현

- `server/lxseq/preset_mapper.py` +122 −11. 삭제된 줄은 전부 의도한 것
  (독스트링 제목 · 인라인 사유의 상수화 · `storable`→`to_plan` 치환 · 최종 반환 확장)
- `server/orchestrator/tools.py` — 페이로드 `already_present` + guidance 갱신
- 신규 검사 25건 (매퍼 20 · 툴 5). 전부 대조군을 동반한다

### E.4 검증 (관측한 것)

| 항목 | 명령 | 관측 |
|---|---|---|
| 린트 | `ruff check server/` | All checks passed |
| 포맷 | `ruff format` | 1 file reformatted |
| 프리셋 4파일 | `pytest server/tests/test_lxseq_preset_*.py` | 65 passed |
| 로컬 전량 | `pytest server/tests -q` | **10,319 passed · 12 skipped** (157.72s) |
| 뮤테이션 | 아래 E.5 | **4/4 KILLED** |

기존 검사 비회귀: 기존 픽스처(`_pool`)는 점유 항목에 `name` 을 안 싣기 때문에
이 변경이 그 판정을 안 바꾼다. 예측했고, 실측으로 확인했다(68 → 그대로 통과).

### E.5 뮤테이션 — 4/4 KILLED

M1 갈래 통째 제거 · M3 CSV 내 중복만 무력화 · M4 미판독 한계 표기 제거 ·
M5 비교 키를 `preset_id` 로 교체. 상세는 `.moai/reports/t87/mutation.md`.

M5 가 리드가 카드 본문에서 경고한 실수와 같다 — 콘솔에 가는 것은 `record.name`
이지 `preset_id` 가 아니어서, 키를 바꾸면 6건 전부 안 맞고 가드가 통째로
무력해지는데 코드는 여전히 그럴듯해 보인다. 검사가 그것을 잡는다.

## §F 판단 기록 — 한 번 뒤집은 것

이름을 못 읽은 점유 슬롯을 처음에는 **거절**로 설계했다. 이 파일의 fail-closed
선례(`_occupied_slots` 는 번호 하나 못 읽으면 전부 거절)를 따르는 것이 일관돼
보였기 때문이다.

뒤집은 이유는 **결과의 무게가 다르다**는 것이다. 번호를 틀리면 점유 슬롯을
**덮어써** 복구가 불가능하고, 이름을 모르면 생기는 것은 **중복**이다. 저장소가
이미 그 차이를 문법으로 갖고 있다 — `refusal` 과 `unverified`(REQ-LXSEQ3-014).
거절로 갔다면 한 번도 관측한 적 없는 상태를 근거로 잘 도는 임포트를 통째로
막았을 것이다.

편의 때문에 완화한 것이 아닌지 스스로 검산했다: 거절 설계는 기존 픽스처 8건을
빨갛게 만들었을 텐데, 그것은 **설계가 틀렸다는 신호가 아니라 픽스처가 합성이라는
신호**다. 판단 근거는 픽스처가 아니라 위의 무게 비대칭이다.

## §G 범위 확장 1건 (리드 보고 완료)

CSV **안**의 이름 중복도 막았다. 파서는 `duplicate_id` 만 보고 이름은 안 본다
(`preset_parser.py:285` 직독) — 안 막으면 이 가드가 **첫 실행에서** 복제한다.
술어가 같고 2줄이라 포함했다. 근거는 「두면 알려진 결함이 남는다」 하나다.

## §H 미검증 (그대로 안고 간다)

- **값 일치는 여전히 안 읽힌다.** 이 변경은 *이름*만 답한다. 이름이 같고 값이
  다른 프리셋은 보류되어 **안 고쳐진 채 남는다.**
  「이미 있음」은 「맞게 있음」이 아니다.
- **이름 길이 상한 미측정.** 잰 6개는 전부 짧다.
- **col / bm 계열 이름 왕복 미측정** — 저장 가능 0건이라 콘솔에 이름이 없다.
- **실기 재확인 안 했다.** 구현 후 콘솔에 다시 쏴서 계획이 0건인지는 **안 쟀다** —
  그것은 쓰기 승인 영역이고 이 카드 범위 밖이다. 순수 함수 검증까지가 여기다.
- **범위 밖 인접 결함 1건 (기록만)**: 이름에 따옴표가 있으면 `store.py:32` 가
  매퍼가 계획을 낸 **뒤에** 예외를 던진다. 안 건드렸다.
