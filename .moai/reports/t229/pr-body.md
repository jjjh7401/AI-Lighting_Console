## 무엇을 했나

`classify_storability` 의 bm 분기에 **범위 축** 보류 하나를 이었다. 기존 두 축을
둘 다 통과하는 값이 있었다 — BM.01 의 `Zoom 45°` 는 Zoom 을 쏠 수 있고(어휘 축
통과) 조각도 읽히는데(구조 축 통과), 실측한 Robin MegaPointe(FixtureType 11
Mode 1)의 줌은 **1.8~42.0도**라 그 기종이 45도를 못 낸다.

`server/prechk/capability_read.py` 의 **첫 비테스트 소비자**다. 그 판독기는 t343
이 넣었고 이 PR 전까지 호출자가 0건이었다.

## 설계 결정 넷

1. **주입이지 조회가 아니다.** `capabilities` 키워드 인자로 받기만 한다. 파서는
   콘솔을 읽지 않고, 인자를 주지 않으면 이 축을 전혀 평가하지 않는다.
2. **도 표기만 대조한다.** 퍼센트·맨숫자는 안 본다 — 역방향 축에서 콘솔 `At`
   매핑이 어느 끝을 DMX 0 으로 두는지 이 저장소는 아직 안 쟀다(t235). 재지 않은
   방향으로 옮기면 뒤집힌 값이 조용히 범위 안에 들어온다.
3. **정규화(0~1) 축은 도 값과 대조하지 않는다.** `Frost1`(0.0~1.0)과 도 값은
   단위가 다르다. 틀린 사유로 막는 것이 안 막는 것보다 나쁘다.
4. **미판독은 결함이 아니다.** `AxisRange.measurable` 이 거짓이면 걸지 않는다.

포함 검사는 **정렬**해서 한다. 정렬 없이 `from <= v <= to` 로 쓰면 역방향 축의
모든 값이 범위 밖이 된다. 축 자신은 방향을 그대로 보존한다.

값을 자르지 않는다. 범위 밖이면 값·구간·채널을 사유 문면에 실어 보류한다.

## 검증

| 항목 | 명령 | 결과 |
|---|---|---|
| 전체 시험 | `uv run pytest server/tests/ -q` | `12221 passed, 35 skipped` (변경 전 `12178 passed, 35 skipped` — 신규 43, 회귀 0) |
| 린트 | `uv run ruff check server/ src/ .moai/` | `All checks passed!` |
| 포맷 | `uv run ruff format --check` (두 파일) | `2 files already formatted` |
| 유예 목록 | `pyproject.toml` 무변경 (`--stat` 빈 출력) | 신규 유예 쌍 0 |
| 바이트 동일 | `diff` `bm-classify-{before,after}.txt` | 종료 코드 0 |
| 뮤테이션 | `low = min(…)` -> `low = axis.physical_from` (`preset_parser.py:792`) | 5 failed / 38 passed, 복원 후 43 passed |

인터프리터 귀속: `server/` 안에서 `uv run python -c "import server; print(server.__file__)"`
가 이 워크트리를 답했다(`…/agent-a4b49f2152678091f/server/__init__.py`).

## 안 잰 것

- **콘솔 접촉 0.** 실기·onPC 어느 쪽도 이 PR 에서 안 붙였다. 축 고정값은
  `test_capability_read.py` 와 같은 2026-09-10 실측 표본을 손으로 옮긴 것이다.
- **`read_mode_capabilities` 와의 실제 결선은 안 했다.** `parse_preset_csv` 는
  `capabilities` 를 안 나른다 — 주입 지점을 만드는 것은 이 카드 범위 밖이다.
  지금 프로덕션 경로는 전부 `capabilities=None` 이라 이 축이 **아직 안 돈다**.
- **기종·모드 이름을 사유에 못 적는다.** `ModeCapabilities` 가 타입/모드 슬롯을
  싣지 않아 provenance 는 축의 채널 이름뿐이다.
- **퍼센트 축의 방향**(t235) 은 그대로 미측정이다.
- Zoom 외의 각도 축(빔 앵글, 아이리스 등)은 실측 표본이 없어 안 쐈다.

## 감독 결정 대기 (이 PR 에서 손대지 않았다)

BM.01 의 `Zoom 45°` 가 MegaPointe 범위 1.8~42.0 **밖**이다. 시트 값을 그대로 두고
보류로 드러내는 쪽을 택했으므로, **어느 각도를 쓸지**는 열린 결정이다. 시트는
한 글자도 안 고쳤다.

🗿 MoAI
