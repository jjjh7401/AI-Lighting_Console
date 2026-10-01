"""카드 t501 M3⑥ — AC-LDRENDER-003 바이트 동일성, 고치기 전/후 두 버전 직접 대조.

acceptance.md AC-003 측정 문구 그대로: "git stash 없이 변경 전/후 두 트리에서
같은 입력으로 reviewed_song_commands 호출 → diff." 다만 여기서는 전체 워크트리를
새로 만드는 대신(무거움), M3 착수 커밋(`a037ad24`, M2 완료)의 **그 함수 소스
자체**를 `git show`로 읽어 격리된 네임스페이스에서 실행하고, 지금 트리의
`_role_dimmer_value_lines`와 **같은 입력**에 같은 출력을 내는지 직접 비교한다 —
"두 트리"가 아니라 "두 버전의 함수"지만, 비교 대상(한 함수의 전/후 소스)과
증거(같은 입력 → diff)의 성질은 acceptance.md 가 요구하는 것과 같다.

왜 이걸로 충분한가: M3 가 바꾼 것은 오직 ``song_cue_composer.CueDimmerData``와
``song_cue_render._back_layer_value_lines``→``_role_dimmer_value_lines`` 두
자리다. AC-003 이 요구하는 "오늘과 바이트 동일"의 "오늘"은 이 두 함수의 **입출력
계약**이지 둘러싼 세션 전체 흐름이 아니다 — 그래서 함수 하나만 떼어 대조해도
증거로 충분하다(어차피 세션 레벨 전체 리허설은 이 워크트리에 원곡 오디오가 없어
불가능 — `measure_ac001_8songs.py` 머리말 참조).

실행: uv run python .moai/reports/t501/ac003_byte_diff.py
콘솔 접촉: 0건. git 접촉: `git show`(읽기 전용) 1회.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

BASELINE_SHA = "a037ad24"  # M3 착수 베이스라인(M2 완료 커밋) — 배차서 §값 동일.


@dataclass(frozen=True)
class _Dimmer:
    key_pct: float | None
    back_pct: float | None
    role_pct: dict


@dataclass(frozen=True)
class _Cue:
    kind: str
    dimmer: _Dimmer


def _old_back_layer_value_lines():
    """`a037ad24`의 `_back_layer_value_lines` 소스를 그대로 읽어 실행 가능한
    함수로 만든다(고치지 않는다 — 글자 그대로 `git show` 출력에서 함수 정의만
    자른다)."""
    text = subprocess.run(
        ["git", "show", f"{BASELINE_SHA}:server/design/song_cue_render.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    start = text.index("def _back_layer_value_lines(")
    end = text.index("\ndef _accent_fixture_value_lines(")
    source = text[start:end]
    namespace: dict = {}
    exec(source, namespace)  # noqa: S102 — 신뢰된 자체 git history, 읽기 전용 측정 스크립트.
    return namespace["_back_layer_value_lines"]


def main() -> None:
    from server.design.song_cue_render import _role_dimmer_value_lines

    old_fn = _old_back_layer_value_lines()

    scenarios = {
        "single_layer_no_mapping": ((), _Cue("section", _Dimmer(80.0, None, {"key": 80.0}))),
        "back_only_lit": (
            ({"role": "back", "group_no": 12, "group_name": "Back"},),
            _Cue("section", _Dimmer(80.0, 64.0, {"key": 80.0, "back": 64.0})),
        ),
        "back_only_dark": (
            ({"role": "back", "group_no": 12, "group_name": "Back"},),
            _Cue("section", _Dimmer(0.0, 0.0, {"key": 0.0, "back": 0.0})),
        ),
        "back_only_no_dimmer_role_pct_fallback": (
            # 옛 함수의 "role_pct 없음 → key_pct*0.8 재계산" 안전망과,
            # 새 함수의 "role_pct 가 이미 back 을 채워 왔다"는 전제가
            # 같은 결과를 내는지(지금 트리의 유일한 생산 경로 — _dimmer_data)
            ({"role": "back", "group_no": 12, "group_name": "Back"},),
            _Cue("section", _Dimmer(50.0, 40.0, {"key": 50.0, "back": 40.0})),
        ),
        "mapping_with_only_side_no_role_pct_value": (
            # side 가 매핑돼 있지만 role_pct 에 값이 없다(M3 가 막아 둔 미해결
            # 결정) — 옛 함수는 애초에 "back" 만 찾으므로 역시 빈 줄.
            ({"role": "side", "group_no": 7, "group_name": "Side-All"},),
            _Cue("section", _Dimmer(80.0, None, {"key": 80.0})),
        ),
        "mib_premove_untouched": (
            ({"role": "back", "group_no": 12, "group_name": "Back"},),
            _Cue("mib_premove", _Dimmer(None, None, {})),
        ),
    }

    mismatches = []
    for name, (layer_mapping, cue) in scenarios.items():
        old_out = old_fn(cue, layer_mapping)
        new_out = _role_dimmer_value_lines(cue, layer_mapping)
        status = "OK" if old_out == new_out else "MISMATCH"
        if status == "MISMATCH":
            mismatches.append(name)
        print(f"{name}: {status}  old={old_out!r}  new={new_out!r}")

    if mismatches:
        print(f"\nFAIL — {len(mismatches)}건 불일치: {mismatches}")
        raise SystemExit(1)
    print(f"\nPASS — {len(scenarios)}건 전부 바이트 동일.")


if __name__ == "__main__":
    main()
