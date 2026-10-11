"""박자 격자 편집의 프리셋 카탈로그 판독 — 기존 콘솔 READ 재사용 (SPEC-
LDBEAT-001 M3, 카드 t551 후속, 리드 지시 2026-10-11).

**근본 원인 정정**: 이 카드의 M3 1차 구현은 "프리셋 카탈로그(이름↔번호)를
읽는 경로가 이 앱에 없다"고 적었다 — 틀렸다. `server.design.console_slots`
(``paged_pool_children``/``resolve_named_pool_no``, 카드 t480)와
`server.design.preset_names`(``match_preset_name``/``match_preset_name_
across_pools``, 카드 t477)가 이미 그 경로다. 이 모듈은 **새 판독 규율을
만들지 않는다** — 그 둘을 그대로 재사용해 박자 격자가 쓰는 세 항목(위치·
색·밝기)과 "효과"(네 풀 모두 검색)에 맞춰 얇게 감싼다.

이 모듈 자신은 콘솔에 아무것도 쓰지 않는다(읽기만, `StateQuery` 주입) —
"콘솔 쓰기 0" 규칙과 충돌하지 않는다. 생산 경로는 `ChatSession`의 기존
`_resolve_named_pool_no`/`_paged_pool_children`(둘 다 이미 존재)를 그대로
주입하고, 시험은 가짜 `query`만 주입한다(`test_preset_label_lookup_t232.py`
의 `_FakeRegistry`/`_PoolHost`와 같은 관행) — 콘솔 접촉은 이 카드 범위에서
0건이다."""

from __future__ import annotations

from collections.abc import Mapping

from server.design.console_slots import StateQuery, paged_pool_children, resolve_named_pool_no
from server.design.preset_names import match_preset_name_across_pools

__all__ = [
    "EFFECT_SEARCH_POOL_NAMES",
    "POOL_NAME_BY_FIELD",
    "build_preset_drawer",
    "pool_name_to_effect_kind",
    "read_named_pool",
    "resolve_effect_preset_name",
    "resolve_preset_name",
]

#: REQ-LDBEAT-015(b) — 위치·색·밝기가 사는 콘솔 풀 이름. 기존 세션 관행과
#: 같은 이름(`ChatSession._resolve_color_pool_no`="Color",
#: `_resolve_named_pool_no("Dimmer", ...)` 재확인) — 번호는 하드코딩하지
#: 않고 매번 이름으로 해석한다.
POOL_NAME_BY_FIELD: dict[str, str] = {
    "위치": "Position",
    "색": "Color",
    "밝기": "Dimmer",
}

#: "효과"는 항목별 풀이 없다 — REQ-LDBEAT-015(b)의 네 효과 풀(위치·색·
#: 디머·이 곡 전용 혼합 All) 전부를 검색해, 어느 풀에서 찾았는지로
#: `effect_kind`를 되짚는다(기존 세션 관행 `_resolve_named_pool_no("All 1", ...)`
#: 재사용 — 새 풀 이름을 지어내지 않는다).
EFFECT_SEARCH_POOL_NAMES: tuple[str, ...] = ("Position", "Color", "Dimmer", "All 1")

_POOL_NAME_TO_EFFECT_KIND: dict[str, str] = {
    "Position": "position",
    "Color": "color",
    "Dimmer": "dimmer",
    "All 1": "mixed",
}

#: 드로워 섹션 제목 — mockup `drawDrawer()`의 세 ``<h6>`` 제목 그대로
#: (`ldbeat-runbook-ui-proposal-20261008.html` "---------- drawer ----------").
_DRAWER_SECTIONS: tuple[tuple[str, str], ...] = (
    ("Dimmer", "디머 풀 1 — 밝기·밝기 효과"),
    ("Position", "위치 풀 2 — 위치·움직임(상대값)"),
    ("Color", "색 풀 4"),
)

#: 큐 칸의 번호 필드 중 프리셋 "pool.slot" 문자열을 담을 수 있는 자리.
#: `brightness.preset_no`는 `mode`가 `dimmer_preset`/`dimmer_effect`일 때만
#: 의미가 있다(REQ-LDBEAT-015(c), beat_grid_edit._validate_brightness 참조).
_PRESET_NUMBER_FIELDS: tuple[str, ...] = (
    "position_preset_no",
    "color_preset_no",
    "effect_preset_no",
)


def pool_name_to_effect_kind(pool_name: str) -> str | None:
    """콘솔 풀 **이름** → `effect_kind`(REQ-LDBEAT-006(i-3)). 모르는 이름은
    `None`(지어내지 않는다) — `EFFECT_SEARCH_POOL_NAMES` 네 개만 안다."""
    return _POOL_NAME_TO_EFFECT_KIND.get(pool_name)


def read_named_pool(
    query: StateQuery, pool_root: str, pool_name: str, *, probe_prefix: str
) -> tuple[int, dict[int, str | None]] | None:
    """``pool_name`` 풀을 이름으로 찾아 완전 판독 — ``(풀 번호, {슬롯: 이름})``.
    풀을 못 찾거나(이름 부재) 판독이 실패하면(절단·I/O) ``None``. 새 규율
    없음 — `resolve_named_pool_no` + `paged_pool_children` 그대로."""
    slug = pool_name.lower().replace(" ", "")
    pool_no = resolve_named_pool_no(
        query, pool_root, pool_name, probe_id=f"{probe_prefix}-{slug}-pool"
    )
    if pool_no is None:
        return None
    children = paged_pool_children(
        query, f"{pool_root}/{pool_no}", probe_id=f"{probe_prefix}-{slug}-slots"
    )
    if children is None:
        return None
    return pool_no, children


def _resolve_preset_name_with_pool(
    query: StateQuery,
    pool_root: str,
    field: str,
    name: str,
    *,
    probe_prefix: str,
):
    pool_names = (
        EFFECT_SEARCH_POOL_NAMES if field == "효과" else (POOL_NAME_BY_FIELD.get(field, field),)
    )
    pools: dict[int | str, dict[int, str | None] | None] = {}
    pool_no_to_name: dict[int, str] = {}
    for pool_name in pool_names:
        result = read_named_pool(query, pool_root, pool_name, probe_prefix=probe_prefix)
        if result is None:
            # 풀 이름 해석 실패·판독 실패 둘 다 이 자리를 "못 읽음"으로
            # 남긴다 — pool_no를 모르면 음수 플레이스홀더를 못 쓰므로,
            # 풀 이름 자체를 키로 둬 unread 쪽에 모은다.
            pools[pool_name] = None
            continue
        pool_no, children = result
        pools[pool_no] = children
        pool_no_to_name[pool_no] = pool_name
    match = match_preset_name_across_pools(pools, name)
    matched_pool_name = pool_no_to_name.get(match.pool_no) if match.pool_no is not None else None
    return match, matched_pool_name


def resolve_preset_name(
    query: StateQuery,
    pool_root: str,
    field: str,
    name: str,
    *,
    probe_prefix: str,
):
    """``field``("위치"|"색"|"밝기"|"효과")가 쓰는 풀(들)에서 ``name``의
    슬롯 하나 — `server.design.preset_names.PresetPoolMatch`(``pool_no``·
    ``slot``이 있으면 찾음, 없으면 ``kind``가 사유: ``"absent"``·
    ``"ambiguous"``·``"pool_unread"``). 풀 이름 자체를 콘솔에서 못 찾아도
    (이름 목록 부재) ``pool_unread``로 묶인다 — "그 풀이 없다"와 "그
    이름이 없다"를 같은 "모름"으로 다루되, 어느 경우든 추측하지 않는다."""
    match, _pool_name = _resolve_preset_name_with_pool(
        query, pool_root, field, name, probe_prefix=probe_prefix
    )
    return match


def resolve_effect_preset_name(
    query: StateQuery, pool_root: str, name: str, *, probe_prefix: str
) -> tuple[object, str | None]:
    """ "효과" 항목 전용 — ``(match, matched_pool_name)``. ``effect_kind``
    (REQ-LDBEAT-006(i-3))는 번호만으로는 역추적할 수 없다 — 어느 풀
    이름에서 매칭됐는지가 필요해서, 그 이름을 함께 돌려준다(호출자가
    `pool_name_to_effect_kind`로 바꾼다)."""
    return _resolve_preset_name_with_pool(query, pool_root, "효과", name, probe_prefix=probe_prefix)


def _usage_for_slot(grid: Mapping[str, object], preset_no: str) -> list[dict[str, object]]:
    used_by: list[dict[str, object]] = []
    for track in grid.get("tracks") or []:
        if not isinstance(track, Mapping):
            continue
        group_name = track.get("group_name")
        for cue in track.get("cues") or []:
            if not isinstance(cue, Mapping):
                continue
            referenced = set()
            brightness = cue.get("brightness")
            if isinstance(brightness, Mapping) and brightness.get("mode") in (
                "dimmer_preset",
                "dimmer_effect",
            ):
                value = brightness.get("preset_no")
                if value is not None:
                    referenced.add(value)
            for field in _PRESET_NUMBER_FIELDS:
                value = cue.get(field)
                if value is not None:
                    referenced.add(value)
            if preset_no in referenced:
                used_by.append({"group_name": group_name, "bar": cue.get("bar")})
    return used_by


def build_preset_drawer(
    grid: Mapping[str, object],
    *,
    pools: Mapping[str, tuple[int, Mapping[int, str | None]] | None],
    confirmed: bool,
) -> list[dict[str, object]]:
    """mockup `drawDrawer()`의 세 섹션(디머 1·위치 2·색 4)을 그 모양 그대로
    조립한다 — 판독되지 않은 풀은 빈 목록으로(지어낸 항목 0건),
    사용처(``used_by``)는 ``grid``를 전수 스캔해 실제 참조만 센다(mockup의
    `usage()`와 같은 계산, 데모 ``P`` 객체가 아니라 이 호출의 ``grid``가
    출처다). ``confirmed``는 `preset_pools.yaml`의 값 그대로 모든 섹션에
    싣는다 — `False`면 UI가 "번호대 미확인"을 보여야 한다(REQ-LDBEAT-015(b)
    번호대 확정 여부, 이 카드 지시 2항)."""
    sections: list[dict[str, object]] = []
    for pool_name, title in _DRAWER_SECTIONS:
        entry = pools.get(pool_name)
        if entry is None:
            sections.append(
                {
                    "pool_name": pool_name,
                    "title": title,
                    "pool_no": None,
                    "entries": [],
                    "unread": True,
                    "bands_confirmed": confirmed,
                }
            )
            continue
        pool_no, children = entry
        entries: list[dict[str, object]] = []
        for slot in sorted(children):
            name = children[slot]
            if name is None:
                continue
            preset_no = f"{pool_no}.{slot}"
            used_by = _usage_for_slot(grid, preset_no)
            entries.append(
                {
                    "preset_no": preset_no,
                    "name": name,
                    "usage_count": len(used_by),
                    "used_by": used_by,
                }
            )
        sections.append(
            {
                "pool_name": pool_name,
                "title": title,
                "pool_no": pool_no,
                "entries": entries,
                "unread": False,
                "bands_confirmed": confirmed,
            }
        )
    return sections
