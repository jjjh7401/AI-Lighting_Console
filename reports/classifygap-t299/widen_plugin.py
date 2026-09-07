"""t299 측정 전용 pytest 플러그인 — server/safety/ 를 건드리지 않고 블랙리스트를 넓힌다.

`load_ruleset(path=DEFAULT_RULESET_PATH)` 의 기본 인자는 def 시점에 묶이므로
모듈 속성만 바꿔서는 안 먹는다. `__defaults__` 를 직접 갈아끼운다.

사용:
  MOAI_T299_RULESET=<widened.yaml> python -m pytest -p widen_plugin ...
"""

from __future__ import annotations

import os
from pathlib import Path

from server.safety import ruleset as _rs

_override = os.environ.get("MOAI_T299_RULESET")
if _override:
    p = Path(_override).resolve()
    if not p.is_file():
        raise SystemExit(f"t299: ruleset override not found: {p}")
    _rs.DEFAULT_RULESET_PATH = p
    _rs.load_ruleset.__defaults__ = (p,)
