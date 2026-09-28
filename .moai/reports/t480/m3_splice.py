# ruff: noqa: E501 — 표지 문자열은 tools.py 원문 그대로여야 한다(줄바꿈 불가).
"""t480 M3 — tools.py 의 prepare_songcue 꼬리를 조립기 길로 바꿔 끼운다(정확한 표지로만).

1. `timecode_number` 검사 바로 뒤에 선택 인자 `preset_start` 검사를 넣는다(D2).
2. 룩 라이브러리 적재(`if looks is None:`)부터 핸들러 끝까지를 `m3_handler_tail.py.txt` 로 바꾼다.
3. 모듈 수준 도우미 `_state_port_query` 를 `_confirmed_density_bpm` 앞에 넣는다.

실행(저장소 루트): `uv run python .moai/reports/t480/m3_splice.py`
"""

from pathlib import Path

TOOLS = Path("server/orchestrator/tools.py")
TAIL = Path(".moai/reports/t480/m3_handler_tail.py.txt").read_text()
src = TOOLS.read_text()

handler_at = src.index(
    "    def prepare_songcue(call: ToolCall, context: ExecutionContext) -> ToolExecution:"
)
end_at = src.index("    # -- precheck_patch", handler_at)
start_at = src.index("        if looks is None:\n", handler_at)
assert start_at < end_at
src = src[:start_at] + TAIL + src[end_at:]

anchor = (
    "            return _error_result(call, \"'timecode_number' must be a positive integer\")\n"
)
assert src.count(anchor) == 1
preset_block = anchor + (
    "        # 카드 t480 D2 — 포지션 프리셋 시작 번호(선택). 주면 대화 길처럼 기본 10라벨을\n"
    "        # 그 범위에서 라벨로 찾고, 안 주면 포지션 축을 끈다(번호를 지어내지 않는다).\n"
    '        preset_start = call.arguments.get("preset_start")\n'
    "        if preset_start is not None and (\n"
    "            isinstance(preset_start, bool) or not isinstance(preset_start, int) or preset_start < 1\n"
    "        ):\n"
    "            return _error_result(call, \"'preset_start' must be a positive integer\")\n"
)
src = src.replace(anchor, preset_block, 1)

helper_anchor = "def _confirmed_density_bpm("
assert src.count(helper_anchor) == 1
helper = '''def _state_port_query(state_port: StateQueryPort):
    """상태 포트를 ``server.design.console_slots`` 판독기의 콘솔 질의 함수로 감싼다
    (카드 t480). 세션이 ``query_state`` 도구로 하는 것과 같은 인자·같은 응답이고,
    실패(예외)는 ``None`` — 판독기가 그것을 「못 읽었다」로 다룬다."""

    def query(probe_id: str, arguments: Mapping[str, object]) -> object | None:
        del probe_id  # 도구 호출 id 는 세션 감사용이다 — 포트 직접 조회에는 없다.
        path = str(arguments["path"])
        offset = arguments.get("offset")
        try:
            if offset:
                return state_port.query_state(path, offset=offset)  # type: ignore[call-arg]
            return state_port.query_state(path)
        except Exception:  # noqa: BLE001 — 포트마다 예외 형태가 달라 폭넓게 「못 읽음」
            return None

    return query


'''
src = src.replace(helper_anchor, helper + helper_anchor, 1)
TOOLS.write_text(src)
print("spliced")
