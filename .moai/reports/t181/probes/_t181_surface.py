"""사용자가 실제로 읽는 문자열을 잰다.

session.py:9906 이 except Exception 으로 잡아 _report_error -> classify_exception
-> error_event 로 옮긴다. 그 끝의 message 가 사용자 문면이다.

팔 셋:
  A) 죽은 경로가 던지는 그 예외  -> 측정값
  B) 형태가 다른 예외들          -> 같은 문면이면 「일반 오류로 접힌다」
  C) 비공허성 - 분류기가 실제로 갈리는 경우가 있는가
     C 가 없으면 A 의 결과가 「접혔다」인지 「이 분류기는 상수다」인지 안 갈린다.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")

from server.llm.errors import ProviderError
from server.web.session import classify_exception

CASES = [
    (
        "A  dead console path  (측정값)",
        LookupError("console did not answer: Patch/Stages/1/Fixtures"),
    ),
    ("B1 unknown object path", LookupError("unknown object path: DataPool/Nope")),
    ("B2 plain ValueError", ValueError("boom")),
    ("B3 TimeoutError", TimeoutError("console timed out")),
    ("C1 ValueError No API key  (비공허성)", ValueError("No API key configured")),
    (
        "C2 ProviderError rate_limit (비공허성)",
        ProviderError(
            kind="rate_limit", provider="anthropic", retryable=True, raw_detail="slow down"
        ),
    ),
]

for label, exc in CASES:
    try:
        kind, message = classify_exception(exc)
    except BaseException as err:
        print(f"{label}\n    <case unusable: {type(err).__name__}: {err}>\n")
        continue
    print(f"{label}")
    print(f"    kind    = {kind!r}")
    print(f"    message = {message!r}")
    print()
