"""t513 — 실행 봉쇄(2b) 양성 대조: 같은 패치를 단 ConsoleLink 에 명령을 넣으면 송신 0 · failed 인가.

대조군(패치 없음)은 같은 명령이 송신 함수에 도달함을 보인다 — 계기가 송신을 셀 수 있다는 증거.
콘솔 접촉 0: 송신 함수는 목록에 적기만 한다.
실행: uv run python .moai/reports/t513/control_exec_block.py
"""

from server.safety.console import ConsoleLink, ExecOutcome, LinkTimeouts

for patched in (False, True):
    wire: list[str] = []
    link = ConsoleLink(timeouts=LinkTimeouts(exec_confirm_seconds=0.2))
    link.bind_send(wire.append)
    if patched:
        blocked: list[str] = []

        def _blocked_execute(command, _blocked=blocked, **_kw):
            _blocked.append(command)
            return ExecOutcome(status="failed", detail="t513 deny-all: not sent to console")

        link._execute = _blocked_execute
    try:
        outcome = link.execute("ClearAll")
    except Exception as error:  # noqa: BLE001
        outcome = f"raised {type(error).__name__}: {error}"
    print(f"patched={patched} wire_sends={len(wire)} outcome={outcome}")
