"""반영 한 번 안의 장비 판독 재사용 — 같은 반영 안에서 같은 장비를 두 번 묻지 않는다.

「⇪ 반영」은 리그 판독(``read_design_rig``)과 무대 소속 판독(``read_beat_grid_stage``)을
차례로 부른다. 둘 다 장비마다 FID·위치·타입 같은 속성을 따로 묻는다. 이 포트는 장비
하나당 질의 한 번으로 그 속성들을 받아 두고, 뒤따르는 같은 장비 읽기는 받아 둔 값으로 답한다.

읽기 전용이다. 받아 두지 않은 이름, 장비가 아닌 경로, 실패한 장비는 원래 포트로 넘긴다.
답의 모양(``ok``·``value``·``reads``·``n``)은 원래 포트와 같다.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from server.design.rig_read_cache import KIND_FIXTURE, KIND_SINGLE, RigReadCache

#: 장비 하나당 질의 한 번에 받는 속성 — 리그 판독(화이트리스트·FID)과 무대 판독(좌표·sf).
FIXTURE_SNAPSHOT_PROPERTIES: tuple[str, ...] = (
    "FID",
    "Patch",
    "FixtureType",
    "Mode",
    "Name",
    "posx",
    "posy",
    "posz",
    "SUBFIXTUREINDEX",
)


class FixtureSnapshotPort:
    """같은 반영 안에서 장비 판독을 한 번만 묻는 읽기 전용 포트 래퍼."""

    def __init__(
        self,
        inner: Any,
        *,
        fixture_root: str,
        names: Sequence[str] = FIXTURE_SNAPSHOT_PROPERTIES,
        cache: RigReadCache | None = None,
    ) -> None:
        self._inner = inner
        self._root = fixture_root.rstrip("/")
        self._names = tuple(names)
        #: 장비 경로 -> (대문자 이름 -> 원문 판독 항목). 한 반영 안에서만 산다.
        self._by_path: dict[str, dict[str, dict[str, Any]]] = {}
        #: 묶음 판독이 실패한 장비 경로 — 같은 반영 안에서 다시 묻지 않는다.
        self._unavailable: set[str] = set()
        #: 주면 반영 사이에도 장비 판독을 재사용한다(짧은 수명 — ``rig_read_cache``).
        self._cache = cache

    # -- 읽기 세 가지 (포트 프로토콜 그대로) -----------------------------------
    def query_state(self, path: str, *, offset: int = 0) -> dict:
        if offset:
            return self._inner.query_state(path, offset=offset)
        return self._inner.query_state(path)

    def query_property(self, path: str, property_name: str) -> dict:
        if self._is_fixture(path):
            items = self._load(path)
            item = None if items is None else items.get(property_name.upper())
            if item is not None:
                return _single_reply(item)
            return self._remembered(
                (path, property_name.upper()),
                lambda: self._inner.query_property(path, property_name),
            )
        return self._inner.query_property(path, property_name)

    def query_properties(
        self, path: str, property_names: Sequence[str], *, offset: int | None = None
    ) -> dict:
        names = tuple(property_names)
        if offset is None and self._is_fixture(path):
            items = self._load(path)
            if items is not None and all(name.upper() in items for name in names):
                return {
                    "ok": True,
                    "path": path,
                    "reads": [_relabel(items[name.upper()], name) for name in names],
                    "truncated": False,
                }
        if offset is None:
            if self._is_fixture(path):
                key = (path, tuple(name.upper() for name in names))
                return self._remembered(key, lambda: self._inner.query_properties(path, names))
            return self._inner.query_properties(path, names)
        return self._inner.query_properties(path, names, offset=offset)

    # -- 내부 ---------------------------------------------------------------------
    def _is_fixture(self, path: str) -> bool:
        prefix = self._root + "/"
        return path.startswith(prefix) and path[len(prefix) :].isdigit()

    def _remembered(self, key: tuple[Any, ...], read: Callable[[], dict]) -> dict:
        """묶음에서 못 받은 장비 읽기의 답을 세션 캐시에 둔다 — **성공 답만**."""
        if self._cache is None:
            return read()
        hit = self._cache.get(KIND_SINGLE, key)
        if hit is not None:
            return hit
        reply = read()
        if isinstance(reply, Mapping) and reply.get("ok"):
            self._cache.put(KIND_SINGLE, key, reply)
        return reply

    def _load(self, path: str) -> dict[str, dict[str, Any]] | None:
        """장비 하나의 속성을 한 질의로 받아 둔다. 실패하면 ``None`` — 호출자는 원래 포트로 간다."""
        if path in self._by_path:
            return self._by_path[path]
        if path in self._unavailable:
            return None
        cache_key = (path, self._names)
        if self._cache is not None:
            cached = self._cache.get(KIND_FIXTURE, cache_key)
            if cached is not None:
                self._by_path[path] = cached
                return cached
        try:
            payload = self._inner.query_properties(path, self._names)
        except Exception:  # noqa: BLE001 — 실패는 원래 읽기 경로가 그대로 판정한다
            self._unavailable.add(path)
            return None
        if not isinstance(payload, Mapping) or not payload.get("ok"):
            self._unavailable.add(path)
            return None
        reads = payload.get("reads")
        if not isinstance(reads, list):
            self._unavailable.add(path)
            return None
        items: dict[str, dict[str, Any]] = {}
        for item in reads:
            if not isinstance(item, Mapping) or not isinstance(item.get("n"), str):
                continue
            # 읽기 쪽 규율과 같다(prechk.query._bulk_chunk): 값이 줄었거나 없는 성공 항목은
            # 받아 두지 않는다 — 그 이름은 단건 읽기로 다시 받는다. 처음 항목을 쓴다.
            if item.get("ok") and (item.get("truncated") or item.get("v") is None):
                continue
            items.setdefault(str(item["n"]).upper(), dict(item))
        self._by_path[path] = items
        if self._cache is not None:
            self._cache.put(KIND_FIXTURE, cache_key, items)
        return items


def _single_reply(item: Mapping[str, Any]) -> dict:
    """단건 판독 답의 모양 — 받아 둔 성공 항목은 문자열 값을, 실패 항목은 ``ok: False`` 를 준다."""
    if item.get("ok"):
        return {"ok": True, "value": str(item.get("v"))}
    return {"ok": False}


def _relabel(item: Mapping[str, Any], name: str) -> dict:
    """묶음 답의 항목을 호출자가 부른 이름으로 바꿔 돌려준다(읽는 쪽이 이름으로 찾는다)."""
    return {**item, "n": name}
