"""프리셋 저장 명령 빌더 — 층 중립 리프.

**왜 여기 있는가.** 이 빌더는 원래 `server/web/session.py` 에 있었고, 그
독스트링이 「spatial 은 무접촉이라 일반형은 세션 계층에 산다」고 적어 뒀다 —
의도된 배치였지 사고가 아니었다. 그러나 그 자리에서는 **툴 층이 닿을 수 없다**:
`session.py` 가 `orchestrator/tools.py` 를 임포트하므로 역방향이 순환이다.

`SPEC-COPILOT-LXSEQ-003` 이 시트에서 온 프리셋을 툴 경유로 저장하려 했을 때
그 벽에 부딪혔다. 선택은 둘이었다 — 툴 층이 문형을 **한 번 더** 적거나, 빌더를
**양쪽이 닿는 자리**로 옮기거나. 사본을 늘리면 문형이 바뀔 때 **어느 자리가 안
고쳐졌는지 아무도 모른다**(이 저장소가 프로브 포트에서 이미 치른 값이다).
그래서 옮겼다.

`server/spatial/pointing.py` 의 포지션 전용 빌더는 그대로 둔다 — 풀 2에 고정된
다른 계약이고, 이 일반형의 `pool_no=2` 출력과 문자 단위로 같다(그 등가성을
검사가 잰다).
"""

from server.presets.store import preset_store_commands

__all__ = ["preset_store_commands"]
