"""t322 (b) — 게이트에 닿은 **모든 번들**을 세어, 선언 없이 지나간 쇼파일 쓰기를 찾는다.

카드 t321 은 자리마다 구동기 하나씩만 몰았다. 「다른 갈래가 다른 번들을
내보내는가」는 그래서 안 재진 채로 남았다. 손으로 갈래를 열거하면 열거한
만큼만 답이 나오는데, 그 「만큼」이 얼마인지도 모른다.

그래서 손으로 세지 않고 **계기를 붙인다**: `SafetyGate.screen` 을 감싸
테스트 전량이 도는 동안 게이트에 닿은 번들을 전부 기록한다. 그러면 스위트가
여는 갈래만큼이 자동으로 표본이 된다 — 그 표본의 크기가 곧 이 측정의 한계고,
한계가 숫자로 나온다.

찾는 것은 하나: **쇼파일을 고치는 줄을 실었는데 선언(`risk`)이 없는 번들.**
그런 번들이 있으면 그 자리는 「봉합됐다」고 적힌 채 어떤 갈래에서는 카드
없이 콘솔에 닿는다 — 봉인 안 된 자리보다 나쁘다.

사용:
    uv run pytest server/tests -q -p server.tests.t322_dispatch_census
    (결과: .moai/state/verify/t322/dispatch_census.json)
"""

from __future__ import annotations

import inspect
import json
import os
import re
from pathlib import Path

from server.safety.gate import SafetyGate

#: 테스트 t321 이 쓰는 것과 같은 계열 — 쇼파일 오브젝트를 만들거나 덮는 줄.
_SHOWFILE_PREFIXES = ("Store ", "Assign Sequence ", "Copy Sequence ", "Set Fixture ")

#: `write_reason` 의 정규식이 못 보는 쇼파일 변경 후보. 별도로 세어 둔다 —
#: 「선언에 안 실린다」와 「쇼파일을 안 고친다」는 다른 말이기 때문이다.
_UNCLASSIFIED_WRITE = re.compile(r"\bSet Cue \S+ Sequence \d+ Property\b")

_OUT = Path(os.environ.get("T322_CENSUS_OUT", ".moai/state/verify/t322/dispatch_census.json"))

_records: list[dict] = []
_original = SafetyGate.screen


def _provenance() -> dict:
    """이 번들이 **어디서** 게이트에 닿았는지 — 세션 쓰기 자리인가, 게이트 단위 검사인가.

    이 구분이 없으면 게이트 자체를 시험하는 검사(`gate.screen(["Store Cue 1"])`)가
    「선언 없는 쇼파일 쓰기」로 잡혀 실제 결함을 덮는다. 세는 대상은
    **세션이 낸 번들**뿐이다.
    """
    frames = inspect.stack()
    files = [f.filename for f in frames]
    functions = [f.function for f in frames]
    return {
        "from_session": any(f.endswith("server/web/session.py") for f in files),
        "via_dispatch_declared": "_dispatch_declared" in functions,
        # 세션 안에서 이 번들을 만든 함수들 — 「세션이 스택에 있다」로는
        # 어느 자리인지 못 가른다. 자리 이름을 그대로 적는다.
        "session_frames": [
            fr.function for fr in frames if fr.filename.endswith("server/web/session.py")
        ],
        "test_frame": next(
            (
                f"{Path(fr.filename).name}:{fr.function}"
                for fr in frames
                if "/server/tests/" in fr.filename
                and not fr.filename.endswith("t322_dispatch_census.py")
            ),
            "?",
        ),
    }


def _instrumented(self, commands, *, risk=None):
    commands = list(commands)
    showfile = [c for c in commands if c.startswith(_SHOWFILE_PREFIXES)]
    unclassified = [c for c in commands if _UNCLASSIFIED_WRITE.search(c)]
    _records.append(
        {
            "commands": commands,
            "declared": risk is not None,
            "kind": risk.kind if risk is not None else None,
            "showfile_writes": showfile,
            "unclassified_writes": unclassified,
            **_provenance(),
        }
    )
    return _original(self, commands, risk=risk)


def pytest_configure(config):  # noqa: ARG001
    SafetyGate.screen = _instrumented


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    SafetyGate.screen = _original
    # 같은 번들이 여러 테스트에서 반복되므로, 고유 (명령들, 선언여부) 로 접는다.
    seen: dict[tuple, dict] = {}
    for record in _records:
        key = (tuple(record["commands"]), record["declared"], record["from_session"])
        entry = seen.setdefault(key, {**record, "occurrences": 0})
        entry["occurrences"] += 1
    unique = list(seen.values())
    session_bundles = [r for r in unique if r["from_session"]]
    violations = [r for r in session_bundles if r["showfile_writes"] and not r["declared"]]
    unclassified_only = [
        r for r in session_bundles if r["unclassified_writes"] and not r["showfile_writes"]
    ]
    payload = {
        "total_screen_calls": len(_records),
        "unique_bundles": len(unique),
        "unique_session_bundles": len(session_bundles),
        "session_declared": sum(1 for r in session_bundles if r["declared"]),
        "session_undeclared": sum(1 for r in session_bundles if not r["declared"]),
        "session_bundles_with_showfile_write": sum(
            1 for r in session_bundles if r["showfile_writes"]
        ),
        "VIOLATIONS_showfile_write_without_declaration": violations,
        "unclassified_write_without_any_classified_write": unclassified_only,
        "kinds_seen": sorted({r["kind"] for r in session_bundles if r["kind"]}),
        "session_bundles_detail": session_bundles,
        "non_session_bundle_count": len(unique) - len(session_bundles),
    }
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
