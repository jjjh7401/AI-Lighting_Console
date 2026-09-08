# t337 국면 4a — 안전 자동수정 40건, 유예 62쌍 → 30쌍 · 그리고 출구가 막혀 있다는 발견

측정 트리: `.claude/worktrees/t337d` · 기준 커밋 `20fc345`(국면 3 머지 후) · 일자 2026-09-08

## 1. 주장

- 안전 자동수정 40건 적용: I001 16 · UP009 11 · E401 9 · F401 4 · SIM300 1 → **전부 0**.
- 전수 위반 **179 → 136**. 유예 쌍 **62 → 30**. `_PAIR_CEILING` 30 으로 하향.
- 산출물 13개 동일 · 검사기 3개(`validate`·`validate_ma3`·`validate_rig`) 실행 출력 바이트 동일.
- 🔴 **카드의 종료 조건은 이 계열 작업만으로는 도달할 수 없다.** 근거는 §4.

## 2. 증거

### 2.1 위험 자리 하나를 특정해서 쐈다

I001(임포트 정렬)은 이 파일들에서 위험할 수 있었다 — 11개 파일 전부가
`sys.path.insert(0, ...)` **뒤에** 로컬 모듈을 임포트하는 구조라, 정렬이 그 임포트를
`sys.path.insert` 위로 올리면 `ModuleNotFoundError` 가 난다.

적용 후 실제 배치를 읽어 확인했다 (`make_rig.py`):

```python
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from rig_data import (
```

정렬이 `sys.path.insert` 를 넘지 않았다 — isort 는 연속된 임포트 블록 안에서만
정렬하고, 그 문장이 블록을 끊는다. 「안전할 것이다」가 아니라 배치를 읽어서 확인한
것이고, 5개 스크립트 전부 exit 0 이다.

### 2.2 검사기 3개를 따로 쟀다

`validate.py`·`validate_ma3.py`·`validate_rig.py` 는 산출물을 만들지 않으므로 산출물
대조로는 아무것도 안 잡힌다. 변경 전 판(`git stash` 로 되돌린 상태)에서 세 개의 실행
출력을 받아두고, 변경 후 출력과 `diff` 했다 — 셋 다 바이트 동일.

### 2.3 유예 목록 검산

전수 출력에서 뽑은 30쌍이 `pyproject.toml` 목록과 일치. `ruff check .` → All checks
passed! · `ruff format --check` → 11 files already formatted · 전체 스위트 12,090 passed.

## 3. 남은 것 (136건 / 30쌍)

| 규칙 | 건수 | 성격 |
|---|---|---|
| UP031 | 62 | `%d` 등 폭·정밀도 붙은 숫자 변환. 정수 절단 보존 판단이 자리마다 필요 |
| E501 | 36 | 포맷으로 안 녹는 긴 줄. 줄 끊기는 사람 판단 |
| E402 | 17 | **10건은 구조적으로 제거 불가** (§4) · 7건은 올릴 수 있다 |
| B007 | 9 | 안 쓰는 루프 변수 |
| E741 | 6 | 모호한 변수명(`l` 등) |
| B905 | 5 | `zip(strict=)` 미지정 |
| SIM115 | 1 | `open()` 을 컨텍스트 매니저 없이 |

## 4. 🔴 발견 — 카드의 출구 조건이 지금 구조로는 도달 불가

카드의 종료 조건은 「per-file-ignores 목록이 비면 그 절을 통째로 지운다」다.
E402 17건을 두 갈래로 갈라 세어 보니(`.moai/state/verify/t337d/e402_survey.py`):

**(가) `sys.path` 의존 — 못 올린다: 10건**

```
make_exec.py:15      from exec_data import CUE_EX, EX_HEADERS, EXEC_NOTES, PATCH, PRESETS
make_ma3.py:19,20,30 from exec_data / rig_data / seq_data import ...
make_timeline.py:13  from seq_data import ...
make_xlsx.py:15      from seq_data import ...
validate.py:15,189   from seq_data / exec_data import ...
validate_ma3.py:15,16 from rig_data / seq_data import ...
```

이 10건은 바로 앞의 `sys.path.insert(0, 파일 위치)` 가 없으면 해석되지 않는다.
임포트를 위로 올리면 `ModuleNotFoundError` 다. **즉 이건 부채가 아니라 지금 임포트
기제가 요구하는 결과**이고, E402 유예 6쌍(`make_exec`·`make_ma3`·`make_timeline`·
`make_xlsx`·`validate`·`validate_ma3`)은 이 기제가 남아 있는 한 지울 수 없다.

**(나) 올려도 되는 것: 7건** — `openpyxl` 계열 6건과 `make_ma3.py:175` 의
`from collections import OrderedDict`. 다만 이 7건을 올려도 위 6쌍은 각 파일에
(가) 가 최소 1건씩 남아 **유예 쌍은 하나도 안 줄어든다.**

### 그래서 무엇이 필요한가

목록을 비우려면 임포트 기제를 바꿔야 한다 — 이 폴더를 패키지로 만들거나(`__init__.py`
+ 상대 임포트), 실행 진입점을 바꿔 `sys.path` 조작을 없애는 쪽이다. 그건 파이프라인의
실행 방식을 바꾸는 설계 변경이고, **이 카드(린트 유예 축소)의 범위가 아니다.**

이 사실은 카드 본문에 없었다. 카드는 「목록이 비면 절을 지운다」를 도달 가능한 것으로
전제했는데, 실측하면 6쌍이 구조적으로 남는다. **감독 판단이 필요한 자리다** — 별도
카드로 임포트 기제를 다룰지, 아니면 E402 6쌍을 「구조적 유예」로 명시 표기해 카드의
종료 조건을 고칠지.

## 5. 미검증 (Gaps)

- 위 (나) 7건은 이번에 **옮기지 않았다.** 쌍이 안 줄어 이득이 없고, 임포트 이동은
  카드가 「가장 위험하다」고 지목한 축이라 이득 없는 위험을 지지 않았다.
- 산출물 커버리지는 여전히 기본 입력 한 벌이다(국면 1~3 과 동일한 한계).
- `F401`(안 쓰는 임포트) 4건을 자동 제거했는데, 임포트에 부작용이 있는 경우 제거가
  동작을 바꾼다. 그런 부작용이 없다는 것은 **파이프라인 5개와 검사기 3개가 전부 정상
  종료하고 출력이 동일했다는 사실로만** 지탱된다 — 정적으로 증명하지 않았다.

## 6. 잔여 위험

- 유예가 30쌍으로 줄면서 이 파일들이 받는 실제 검사 범위가 넓어졌다. 앞으로 이
  폴더를 만지는 변경은 이전보다 자주 린트에 걸릴 것이고, 그건 의도된 효과다.
- E402 6쌍을 「언젠가 지울 부채」로 계속 읽으면 후속 카드가 도달 불가한 목표를 향해
  반복 착수한다. §4 를 안 남기면 그 낭비가 조용히 반복된다.
