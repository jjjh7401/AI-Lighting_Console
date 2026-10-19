"""장비·기종 판독을 미리 채운다 — 서버를 띄울 때와 곡을 열 때(리드 결정, 2026-10-19).

첫 「⇪」이 기종 채널을 콘솔에서 처음부터 걷지 않도록 판독을 백그라운드에서 한 번 돈다.
판독이 전수가 아니면 캐시에 적지 않으므로 다음 반영이 다시 묻는다. 예열은 덤이다.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Mapping
from typing import Any

from server.design.fixture_snapshot import FixtureSnapshotPort
from server.design.rig_capability_read import read_design_rig
from server.design.rig_read_cache import RigReadCache, follow_patch_epoch
from server.orchestrator.tools import DEFAULT_RIG_CONTEXT_PATHS

_LOG = logging.getLogger(__name__)

#: 예열은 한 번에 하나만 돈다 — 서버 시작과 곡 열기가 겹쳐도 콘솔 읽기가 두 줄로 서지 않는다.
_WARM_LOCK = threading.Lock()


def warm_device_layers(
    gate: Any, *, rig_paths: Mapping[str, str] | None, cache: RigReadCache
) -> bool:
    """장비·기종 판독을 한 번 돌려 캐시를 채운다. 전수로 읽혔을 때만 ``True``.

    이미 도는 예열이 있으면 기다리지 않고 ``False`` 를 돌려준다. 콘솔 오류는 삼키고 로그만 남긴다.
    """
    paths = dict(rig_paths or DEFAULT_RIG_CONTEXT_PATHS)
    fixtures = paths.get("fixtures")
    if not fixtures or not _WARM_LOCK.acquire(blocking=False):
        return False
    try:
        follow_patch_epoch(cache, gate.patch_write_epoch)
        snapshot = FixtureSnapshotPort(gate.state_port, fixture_root=str(fixtures), cache=cache)
        types_root = str(paths.get("fixture_types", DEFAULT_RIG_CONTEXT_PATHS["fixture_types"]))
        with cache.reading():
            rig_read = read_design_rig(snapshot, fixture_types_root=types_root, cache=cache)
        return bool(rig_read.whole)
    except Exception:  # noqa: BLE001 — 예열은 덤이다. 실패가 서버 시작·곡 열기를 막지 않는다.
        _LOG.warning("장비 판독 예열이 실패했다 — 첫 반영이 다시 읽는다", exc_info=True)
        return False
    finally:
        _WARM_LOCK.release()
