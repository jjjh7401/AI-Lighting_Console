"""장비·기종 판독을 미리 채운다 — 서버를 띄울 때와 곡을 열 때(리드 결정, 2026-10-19).

첫 「⇪」이 기종 채널을 콘솔에서 처음부터 걷지 않도록 판독을 백그라운드에서 한 번 돈다.
판독이 전수가 아니면 캐시에 적지 않으므로 다음 반영이 다시 묻는다. 예열은 덤이다.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from server.design.fixture_snapshot import FixtureSnapshotPort, RememberingFixturePort
from server.design.rig_capability_read import read_design_rig
from server.design.rig_read_cache import RigReadCache, follow_patch_epoch
from server.orchestrator.tools import DEFAULT_RIG_CONTEXT_PATHS

_LOG = logging.getLogger(__name__)


def warm_device_layers(
    gate: Any, *, rig_paths: Mapping[str, str] | None, cache: RigReadCache
) -> bool:
    """장비·기종 판독을 한 번 돌려 캐시를 채운다. 전수로 읽혔을 때만 ``True``.

    이미 도는 예열이 있으면 기다리지 않고 ``False`` 를 돌려준다. 콘솔 오류는 삼키고 로그만 남긴다.
    예열 잠금은 캐시마다 둔다 — 서버에는 캐시가 하나라 한 번에 하나만 돈다.
    """
    paths = dict(rig_paths or DEFAULT_RIG_CONTEXT_PATHS)
    fixtures = paths.get("fixtures")
    if not fixtures or not cache.warm_lock.acquire(blocking=False):
        return False
    try:
        follow_patch_epoch(cache, gate.patch_write_epoch)
        snapshot = FixtureSnapshotPort(gate.state_port, fixture_root=str(fixtures), cache=cache)
        types_root = str(paths.get("fixture_types", DEFAULT_RIG_CONTEXT_PATHS["fixture_types"]))
        remembered = RememberingFixturePort(
            gate.state_port, fixture_root=str(fixtures), cache=cache
        )
        with cache.reading():
            rig_read = read_design_rig(snapshot, fixture_types_root=types_root, cache=cache)
            # 반영 경로의 기종 판독은 장비별 기억을 쓴다 — 그 기억도 미리 채워 둔다.
            read_design_rig(remembered, fixture_types_root=types_root, cache=cache)
        return bool(rig_read.whole)
    except Exception:  # noqa: BLE001 — 예열은 덤이다. 실패가 서버 시작·곡 열기를 막지 않는다.
        _LOG.warning("장비 판독 예열이 실패했다 — 첫 반영이 다시 읽는다", exc_info=True)
        return False
    finally:
        cache.warm_lock.release()


#: 예열 재시도 간격(초). 서버를 막 띄우면 콘솔이 아직 응답하지 않을 수 있어 한 번에 포기하지 않는다.
WARM_RETRY_DELAYS_SECONDS = (0.0, 5.0, 15.0, 30.0, 60.0)


def warm_until_whole(
    gate: Any,
    *,
    rig_paths: Mapping[str, str] | None,
    cache: RigReadCache,
    delays: Sequence[float] = WARM_RETRY_DELAYS_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> bool:
    """예열을 전수로 끝낼 때까지 간격을 두고 다시 시도한다. 끝내 못 하면 ``False``.

    콘솔이 아직 응답하지 않은 시도는 캐시에 아무것도 적지 않으므로 다음 시도가 안전하다.
    """
    for attempt, delay in enumerate(delays, start=1):
        if delay:
            sleep(delay)
        if warm_device_layers(gate, rig_paths=rig_paths, cache=cache):
            _LOG.info("장비 판독 예열 완료 — %d번째 시도", attempt)
            return True
        _LOG.warning("장비 판독 예열 %d번째 시도가 전수로 끝나지 않았다", attempt)
    _LOG.warning("장비 판독 예열이 %d번 뒤에도 끝나지 않았다 — 첫 반영이 다시 읽는다", len(delays))
    return False
