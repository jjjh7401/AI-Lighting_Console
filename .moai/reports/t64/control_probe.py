"""③ 날조 대조군 — 기준 커밋을 못 찾는 상태를 일부러 만들어 검사가 실제로 빨개지는지 본다.

파일을 건드리지 않는다. 모듈을 경로로 적재한 뒤 _RUN_PHASE_BASE 만 바꿔치고
두 테스트 함수를 직접 호출한다. 판정은 "무엇을 던지는가"로 한다 —
AssertionError = 빨간불(원했던 것), Skipped = 침묵(고치려던 병), 무예외 = 공허한 검사.
"""

import importlib.util
import pathlib
import sys

MOD = pathlib.Path("server/tests/test_songcue_bundle.py").resolve()
FAKE = "0000000000000000000000000000000000000001"
TESTS = (
    "test_preserve_look_files_are_unchanged_from_run_phase_base",
    "test_tools_hunks_are_only_songcue_registration_and_not_dedupe_or_state",
)


def load():
    spec = importlib.util.spec_from_file_location("probe_songcue_bundle", MOD)
    module = importlib.util.module_from_spec(spec)
    sys.modules["probe_songcue_bundle"] = module
    spec.loader.exec_module(module)
    return module


def verdict(module, name):
    try:
        getattr(module, name)()
    except AssertionError as error:
        return "RED(AssertionError)", str(error).splitlines()[0]
    except BaseException as error:  # Skipped 도 여기로 온다 — 잡아서 데이터로 쓴다
        return "OTHER(" + type(error).__name__ + ")", str(error).splitlines()[0]
    return "NO-RAISE", ""


module = load()

print("=== 대조군의 대조군: 진짜 기준 커밋 (하네스가 초록도 낼 수 있는가) ===")
for name in TESTS:
    print("  ", name, "->", verdict(module, name))

print("=== 날조 기준 커밋 (검사가 실제로 빨개지는가) ===")
module._RUN_PHASE_BASE = FAKE
for name in TESTS:
    state, first_line = verdict(module, name)
    print("  ", name, "->", state)
    print("      ", first_line)
