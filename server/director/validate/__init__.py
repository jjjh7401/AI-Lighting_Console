"""Director 계획 검증층 — 판정하고 낮춘다 (SPEC-LDCOMPILE-001).

저장하지 않고(`SPEC-LDSTORE-001`) 실행하지 않는다(`SPEC-LDRECV-001`). 이 층이 내는 것은
`ValidationReport` 와 frozen artifact 뿐이다.

핵심 주장 하나 — **보존할 수 없으면 지원한다고 말하지 않는다.** parser 가 받아들이는 것과
emitter 가 실제로 콘솔에 남기는 것은 다르고, 그 차이를 조용히 메우는 것(clamp·quantize·
대체 preset·필드 제거)이 이 층이 막아야 하는 실패다.

[HARD] OSC 를 만지지 않는다. `server/bridge/osc.py` 가 서버 전체의 유일한 송신 표면이며
frozen artifact 는 **bytes** 이고 발화가 아니다.
"""

from __future__ import annotations
