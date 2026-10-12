"""저장 실패 시험이 실제로 저장을 시도했고 무엇이 기록을 막았는지 본다(탐침)."""

from server.tests.test_upload_look_memory_t609 import _Memory, _registry, _song, _StoreFailingPort

port = _StoreFailingPort()
memory = _Memory()
execution, payload = _song(_registry(memory, port=port))
print("store attempted:", [c for c in port.executed if c.startswith("Store Sequence")][:2])
print("failures:", len(port.failures))
print("result.is_error:", execution.result.is_error)
print("gate_status:", payload.get("gate_status"))
print("outcome statuses:", sorted({o.status for o in execution.command_outcomes}))
print("memory:", len(memory.history))
