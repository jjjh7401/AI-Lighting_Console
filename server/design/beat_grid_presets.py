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

from server.design.beat_grid_edit import _KIND_TO_POOL_KEYS, validate_preset_pool_assignment
from server.design.console_slots import StateQuery, paged_pool_children, resolve_named_pool_no
from server.design.preset_names import match_preset_name_across_pools

__all__ = [
    "EFFECT_SEARCH_POOL_NAMES",
    "POOL_NAME_BY_FIELD",
    "app_preset_description",
    "app_preset_label",
    "build_preset_drawer",
    "effect_kind_to_pool_name",
    "first_free_base_color_number",
    "first_free_base_position_number",
    "first_free_preset_number",
    "pool_name_to_effect_kind",
    "read_effect_pools_by_number",
    "read_named_pool",
    "record_app_preset_description",
    "record_app_preset_label",
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

#: 카드 t589 — 위 표의 역방향(``effect_kind`` → 콘솔 풀 이름). "+ 새
#: 프리셋" 다이얼로그가 빈 번호를 고르기 전에 콘솔 점유를 확인할 풀
#: 하나를 찾는 자리 — 드로워가 이미 읽는 그 이름 그대로 재사용한다(새
#: 풀 이름을 지어내지 않는다).
_EFFECT_KIND_TO_POOL_NAME: dict[str, str] = {
    kind: name for name, kind in _POOL_NAME_TO_EFFECT_KIND.items()
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


def effect_kind_to_pool_name(kind: str) -> str | None:
    """카드 t589 — `pool_name_to_effect_kind`의 역방향. 모르는 종류는
    `None`(지어내지 않는다)."""
    return _EFFECT_KIND_TO_POOL_NAME.get(kind)


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


def read_effect_pools_by_number(
    query: StateQuery,
    pool_root: str,
    kind: str,
    *,
    policy: Mapping[str, object],
    probe_prefix: str,
) -> dict[int, dict[int, str | None]]:
    """카드 t607(REQ-LDBEAT-015(h)/(b) 계속) — 「＋ 새 프리셋 만들기」 다이얼로그가
    `first_free_preset_number`에 넘길 콘솔 점유를, 풀 **이름**이 아니라
    ``policy``(=`preset_pools.yaml`)가 ``kind``에 선언한 번호대의 풀 **번호**로
    직접 읽는다.

    **근본 원인**: `effect_kind_to_pool_name`(풀 이름 사전)과 `preset_pools.yaml`
    (번호대 사전)은 서로 다른 자리에서 따로 관리돼, 실측으로 어긋남이 발견됐다
    (카드 t604 — 혼합 효과는 이름으로 풀 21("All 1")을 가리키지만 번호대는 풀
    22(``mixed_all: 22.0~22.99``)다). 이름으로 읽은 점유를 번호대가 다른 풀의
    점유로 쓰면 — 즉 21번 풀의 점유로 22.x 번호가 비었는지를 판정하면 — 틀린
    번호를 배정한다. 리드 결정(카드 t607): 풀 이름 규칙을 전혀 쓰지 않는다 —
    이름은 쇼마다 바뀔 수 있어 믿을 자리가 아니다.

    디머처럼 한 ``kind``가 여러 번호대 키를 가져도(``_KIND_TO_POOL_KEYS``) 같은
    풀 번호를 가리키면 그 풀은 한 번만 읽는다. 못 읽은 풀(이름 해석이 아니라
    ``paged_pool_children`` 판독 실패)은 돌려주는 지도에 아예 담지 않는다 —
    `first_free_preset_number`가 "그 풀 번호가 지도에 없으면 미확인으로 다룬다"
    (오늘까지의 "배정+경고" 동작을 그대로 유지한다)."""
    pool_keys = _KIND_TO_POOL_KEYS.get(kind)
    if not pool_keys:
        return {}
    pools = policy.get("pools") if isinstance(policy, Mapping) else None
    pools = pools if isinstance(pools, Mapping) else {}
    pool_numbers: list[int] = []
    for key in pool_keys:
        band = pools.get(key)
        bounds = _parse_band_bounds(band) if isinstance(band, Mapping) else None
        if bounds is None:
            continue
        pool_no = bounds[0]
        if pool_no not in pool_numbers:
            pool_numbers.append(pool_no)
    result: dict[int, dict[int, str | None]] = {}
    for pool_no in pool_numbers:
        children = paged_pool_children(
            query, f"{pool_root}/{pool_no}", probe_id=f"{probe_prefix}-pool{pool_no}-slots"
        )
        if children is not None:
            result[pool_no] = children
    return result


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


def app_preset_description(grid: Mapping[str, object], preset_no: str) -> str | None:
    """카드 t569 — 앱이 만든 프리셋의 설명(곡별 ``grid["preset_descriptions"]``
    ``{"pool.slot": 설명}``). 없거나 빈 글자면 ``None``(지어내지 않는다)."""
    descriptions = grid.get("preset_descriptions")
    if not isinstance(descriptions, Mapping):
        return None
    value = descriptions.get(preset_no)
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def record_app_preset_description(
    grid: Mapping[str, object], preset_no: str, description: str
) -> dict[str, object]:
    """카드 t569 — 앱이 프리셋을 만들 때 그 설명을 곡별 격자에 남기는 단일
    저장 자리. ``grid``의 사본을 돌려준다(원본은 그대로). 빈 설명은 거절한다
    — 비어 있으면 저장하지 않는 것이 "설명 없음"이다.

    한국어 설명은 화면에만 남는다(REQ-LDBEAT-015(c)) — 콘솔 이름은
    ``new_preset_label``(영문·숫자) 자리이고 이 설명과 다르다."""
    if not isinstance(description, str) or not description.strip():
        raise ValueError("프리셋 설명이 비어 있습니다.")
    updated = dict(grid)
    existing = grid.get("preset_descriptions")
    descriptions = dict(existing) if isinstance(existing, Mapping) else {}
    descriptions[preset_no] = description.strip()
    updated["preset_descriptions"] = descriptions
    return updated


def app_preset_label(grid: Mapping[str, object], preset_no: str) -> str | None:
    """카드 t589 — 앱이 만든 프리셋의 콘솔 이름(영문·숫자, 곡별 ``grid
    ["preset_labels"]`` ``{"pool.slot": 이름}``). ``app_preset_description``
    과 같은 저장 모양·같은 "지어내지 않는다" 규칙 — 없거나 빈 글자면
    ``None``."""
    labels = grid.get("preset_labels")
    if not isinstance(labels, Mapping):
        return None
    value = labels.get(preset_no)
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def record_app_preset_label(
    grid: Mapping[str, object], preset_no: str, label: str
) -> dict[str, object]:
    """카드 t589 — `record_app_preset_description`과 짝인 저장 자리. 콘솔
    이름(영문·숫자, REQ-LDBEAT-015(d))을 곡별 격자에 남긴다. ``grid``의
    사본을 돌려준다(원본은 그대로). 빈 이름은 거절한다 — 비어 있으면
    저장하지 않는 것이 "이름 없음"이다."""
    if not isinstance(label, str) or not label.strip():
        raise ValueError("프리셋 이름이 비어 있습니다.")
    updated = dict(grid)
    existing = grid.get("preset_labels")
    labels = dict(existing) if isinstance(existing, Mapping) else {}
    labels[preset_no] = label.strip()
    updated["preset_labels"] = labels
    return updated


def _referenced_preset_numbers(grid: Mapping[str, object]) -> set[str]:
    """``grid`` 전수가 쓰는 프리셋 번호 집합 — `_usage_for_slot`과 같은
    네 자리(위치·색·효과·디머 프리셋/디머 효과)를 보되, 번호 하나를
    묻는 게 아니라 전부를 모은다(새 프리셋이 고를 수 없는 "이미 쓰는
    번호" 전체)."""
    referenced: set[str] = set()
    for track in grid.get("tracks") or []:
        if not isinstance(track, Mapping):
            continue
        for cue in track.get("cues") or []:
            if not isinstance(cue, Mapping):
                continue
            brightness = cue.get("brightness")
            if isinstance(brightness, Mapping) and brightness.get("mode") in (
                "dimmer_preset",
                "dimmer_effect",
            ):
                value = brightness.get("preset_no")
                if value is not None:
                    referenced.add(str(value))
            for field in _PRESET_NUMBER_FIELDS:
                value = cue.get(field)
                if value is not None:
                    referenced.add(str(value))
    return referenced


def _parse_band_bounds(band: Mapping[str, object]) -> tuple[int, int, int] | None:
    """``{"start": "2.61", "end": "2.68"}`` 모양 → ``(풀 번호, 시작 슬롯,
    끝 슬롯)``. 둘 다 "pool.slot" 꼴이고 같은 풀 번호를 가리켜야 한다 —
    못 읽거나 풀 번호가 다르면 ``None``(지어내지 않는다)."""
    try:
        pool_start, slot_start = str(band["start"]).split(".", 1)
        pool_end, slot_end = str(band["end"]).split(".", 1)
        pool = int(pool_start)
        if int(pool_end) != pool:
            return None
        return pool, int(slot_start), int(slot_end)
    except (KeyError, TypeError, ValueError):
        return None


def first_free_preset_number(
    kind: str,
    *,
    policy: Mapping[str, object],
    grid: Mapping[str, object],
    console_children: Mapping[int, Mapping[int, object] | None] | None,
) -> tuple[str | None, str | None, str | None]:
    """카드 t589(REQ-LDBEAT-015(h)) — "+ 새 프리셋 만들기" 다이얼로그가 쓰는
    번호 배정. ``kind``(``effect_kind``)가 `preset_pools.yaml`에서 쓰는
    효과 풀 번호대(들, 디머는 서브 밴드 a→b 순서) 안에서, 격자가 이미
    참조하지 않고(``_referenced_preset_numbers``) **콘솔에서도 비어
    있는** 첫 슬롯을 돌려준다. 코드 상수로 번호대를 짜지 않는다 — 전부
    ``policy``(`load_preset_pool_policy`가 읽은 그 데이터)에서만 읽는다.

    ``console_children``은 **풀 번호**로 가른 지도다 — ``{풀 번호: {슬롯:
    이름}}``(카드 t607). 후보 ``pool.slot``의 점유는 반드시 그 ``pool``
    번호 키로만 본다 — **다른 풀의 자리를 그 후보가 비었는지 판단에 쓰지
    않는다**. 어느 종류의 콘솔 풀 **이름**과 그 종류의 번호대가 가리키는
    풀 **번호**가 어긋날 수 있다는 것이 실측으로 드러났다(카드 t604 —
    혼합 효과는 이름으로 풀 21("All 1")을, 번호대는 풀 22를 가리킨다).
    그래서 이 함수는 풀 이름을 전혀 모른다 — 호출자가 `read_effect_pools_
    by_number`로 번호째 읽어 넘긴다.

    어느 후보의 풀 번호가 이 지도에 없으면(그 풀을 못 읽었거나 시도하지
    않았다) 오늘까지의 동작을 그대로 유지한다 — 거절하지 않고 배정하되
    경고를 돌려준다(격자 참조만 보고 고른 상태를 감독에게 알릴 뿐).
    ``console_children`` 자체가 ``None``이면(풀을 아예 하나도 못 읽었다)
    모든 후보가 이 경로를 탄다.

    반환: ``(번호 또는 None, 거절 사유 또는 None, 경고 또는 None)``.
    번호대가 그 종류에 아예 없거나(base 풀) 번호대가 전부 찼으면 번호는
    ``None``이고 거절 사유가 채워진다."""
    no_band_reason = (
        f"효과 종류 '{kind}'에는 선언된 풀이 없습니다 — preset_pools.yaml 에 이 종류의 "
        "번호대가 없어 빈 번호를 정할 수 없습니다 — 번호대를 지어내지 않습니다."
    )
    pool_keys = _KIND_TO_POOL_KEYS.get(kind)
    if not pool_keys:
        return None, no_band_reason, None
    pools = policy.get("pools") if isinstance(policy, Mapping) else None
    pools = pools if isinstance(pools, Mapping) else {}
    referenced = _referenced_preset_numbers(grid)
    found_band = False
    for key in pool_keys:
        band = pools.get(key)
        bounds = _parse_band_bounds(band) if isinstance(band, Mapping) else None
        if bounds is None:
            continue
        found_band = True
        pool_no, slot_start, slot_end = bounds
        # 이 후보의 풀 번호로만 점유를 본다 — 다른 풀의 children 을
        # 빌려 쓰지 않는다(카드 t607). 지도에 그 풀 번호가 없으면(못
        # 읽음·시도 안 함 둘 다 `.get()` 으로 같은 None) "미확인"이다.
        pool_children = console_children.get(pool_no) if console_children is not None else None
        for slot in range(slot_start, slot_end + 1):
            candidate = f"{pool_no}.{slot}"
            if candidate in referenced:
                continue
            # 키가 있으면 콘솔에 그 번호가 있다 — 이름 없는 프리셋은 값이
            # None 이라 `.get()` 으로는 빈칸과 구분이 안 된다(`paged_pool_children`).
            if pool_children is not None and slot in pool_children:
                continue
            warning = (
                None
                if pool_children is not None
                else "⚠ 콘솔 빈칸 미확인 — 풀을 읽지 못해 격자 참조만 보고 골랐습니다"
            )
            return candidate, None, warning
    if not found_band:
        return None, no_band_reason, None
    return (
        None,
        f"'{kind}' 효과 풀 번호대가 모두 찼습니다(preset_pools.yaml) — 번호대를 넓히지 않고는 "
        "새 프리셋을 더 만들 수 없습니다.",
        None,
    )


def _first_free_base_pool_number(
    *,
    policy: Mapping[str, object],
    grid: Mapping[str, object],
    console_children: tuple[int, Mapping[int, object]] | None,
    pool_label: str,
) -> tuple[str | None, str | None]:
    """``first_free_base_position_number``(t599)·``first_free_base_color_
    number``(t594)가 공유하는 몸체 — 거절 문구의 풀 이름만 ``pool_label``로
    가른다(두 함수의 docstring·반환이 그 호출자별 규칙을 말한다)."""
    if console_children is None:
        return None, (
            f"콘솔에서 {pool_label} 풀을 읽지 못해 빈 슬롯을 알 수 없습니다 — "
            "번호대 보호가 없는 기본 풀이라 추측해 배정하지 않습니다."
        )
    pool_no, children = console_children

    pools = policy.get("pools") if isinstance(policy, Mapping) else None
    pools = pools if isinstance(pools, Mapping) else {}
    skip_bands: list[tuple[int, int]] = []
    for band in pools.values():
        bounds = _parse_band_bounds(band) if isinstance(band, Mapping) else None
        if bounds is None:
            continue
        band_pool, slot_start, slot_end = bounds
        if band_pool == pool_no:
            skip_bands.append((slot_start, slot_end))

    def _in_skip_band(slot: int) -> bool:
        return any(start <= slot <= end for start, end in skip_bands)

    base_occupied = [slot for slot in children if not _in_skip_band(slot)]
    start = max(base_occupied) + 1 if base_occupied else 1

    referenced = _referenced_preset_numbers(grid)
    slot = start
    while True:
        if not _in_skip_band(slot):
            candidate = f"{pool_no}.{slot}"
            if slot not in children and candidate not in referenced:
                return candidate, None
        slot += 1


def first_free_base_position_number(
    *,
    policy: Mapping[str, object],
    grid: Mapping[str, object],
    console_children: tuple[int, Mapping[int, object]] | None,
) -> tuple[str | None, str | None]:
    """카드 t599(REQ-LDBEAT-015(i-3)) — "+ 새 프리셋 만들기" **위치** 필드가
    쓰는 base 위치 번호 배정. base 위치 풀(2.41~)은 효과 번호대가 없는
    풀이라(REQ-LDBEAT-015(b)) `preset_pools.yaml`에서 번호대를 읽지
    않는다 — 대신 그 풀의 **효과** 번호대(``policy["pools"]`` 중 풀 번호가
    같은 밴드, 예: ``position_effect`` 2.61~2.68)만 건너뛰어 겹치지 않게
    하고, 나머지는 콘솔이 실제로 쥔 첫 빈 슬롯이다 — 리그 상수를 짓지
    않는다(번호대도 풀 번호도 코드에 없다).

    ``console_children``은 `read_named_pool(query, pool_root, "Position",
    ...)`가 돌려준 그 쌍 ``(풀 번호, {슬롯: 이름|None})`` 그대로다 — 이
    함수 자신은 콘솔을 읽지 않는다(순수). 그 풀을 콘솔에서 못 읽었으면
    (``None``) 거절한다 — `first_free_preset_number`(효과 풀)와 달리
    "경고만 내고 배정"으로 떨어지지 않는다: base 풀은 번호대 보호가 없어
    틀리게 고르면 기존 쇼 프리셋을 되찾을 길이 없다(손해가 비대칭이다).

    반환: ``(번호 또는 None, 거절 사유 또는 None)``."""
    return _first_free_base_pool_number(
        policy=policy, grid=grid, console_children=console_children, pool_label="Position"
    )


def first_free_base_color_number(
    *,
    policy: Mapping[str, object],
    grid: Mapping[str, object],
    console_children: tuple[int, Mapping[int, object]] | None,
) -> tuple[str | None, str | None]:
    """카드 t594(REQ-LDBEAT-015(i-5)) — "+ 새 프리셋 만들기" **색** 필드가
    쓰는 base 색 번호 배정. `first_free_base_position_number`(t599)와
    같은 몸체·같은 규칙(``_first_free_base_pool_number``) — base 색 풀
    (4.21~)도 효과 번호대가 없는 풀이라 ``preset_pools.yaml``에서 번호대를
    읽지 않고, 대신 그 풀의 **효과** 번호대(``color_effect`` 4.41~4.99)만
    건너뛴다. 나머지는 콘솔이 실제로 쥔 첫 빈 슬롯이다.

    ``console_children``은 `read_named_pool(query, pool_root, "Color",
    ...)`가 돌려준 그 쌍 그대로다(이 함수 자신은 콘솔을 읽지 않는다).
    그 풀을 콘솔에서 못 읽었으면 거절한다 — base 풀은 번호대 보호가 없어
    틀리게 고르면 기존 쇼 프리셋을 되찾을 길이 없다(위치와 같은 비대칭).

    반환: ``(번호 또는 None, 거절 사유 또는 None)``."""
    return _first_free_base_pool_number(
        policy=policy, grid=grid, console_children=console_children, pool_label="Color"
    )


def build_preset_drawer(
    grid: Mapping[str, object],
    *,
    pools: Mapping[str, tuple[int, Mapping[int, str | None]] | None],
    policy: Mapping[str, object],
) -> list[dict[str, object]]:
    """mockup `drawDrawer()`의 세 섹션(디머 1·위치 2·색 4)을 그 모양 그대로
    조립한다 — 판독되지 않은 풀은 빈 목록으로(지어낸 항목 0건),
    사용처(``used_by``)는 ``grid``를 전수 스캔해 실제 참조만 센다(mockup의
    `usage()`와 같은 계산, 데모 ``P`` 객체가 아니라 이 호출의 ``grid``가
    출처다). ``policy``(`beat_grid_edit.load_preset_pool_policy`가 돌려주는
    모양)의 ``confirmed``는 그대로 모든 섹션에 싣는다 — `False`면 UI가
    "번호대 미확인"을 보여야 한다(REQ-LDBEAT-015(b) 번호대 확정 여부,
    카드 t551 지시 2항).

    카드 t551 계속(코디네이터 지시 2026-10-11, 조건 1 — "lead 가 옵션 A를
    골랐다": mockup 자신이 같은 풀 안에서 번호대로 기본/효과 프리셋을
    가른다는 근거). 각 항목에 ``is_effect_band``를 더한다 — 그 항목의
    번호가 ``policy``(=`preset_pools.yaml`, 코드 상수 0건)가 선언한 그
    풀의 **효과** 번호대 안에 있는지를, 새 판정 규칙을 짜지 않고
    `beat_grid_edit.validate_preset_pool_assignment`(이미 `apply_beat_
    grid_edit`가 쓰는 그 함수)를 그대로 재사용해 판정한다 — 거절 사유가
    `None`이면 그 효과 풀 번호대 안에 있다는 뜻이다. 번호대가 아직 선언돼
    있지 않거나(``pools``가 비었거나) 그 풀 종류를 모르면 "효과"로
    지어내지 않고 `False`(= 기본 쪽에 남긴다)로 떨어진다.

    카드 t568(REQ-LDBEAT-023(c)) — 각 항목에 ``description``을 명시적
    `None`으로 더한다. `paged_pool_children`이 돌려받는 콘솔 응답은
    슬롯 번호·이름뿐이라(PROTOCOL §4.2) 프리셋의 "설명 텍스트"를 읽는
    경로가 이 저장소에 없다(새 콘솔 프로브 없이 조사 완료) — 그래서 그
    필드를 지어내지 않고 자리만 명시적으로 비워 둔다(생략과는 다르다 —
    "비었다"는 사실 자체가 확인된 정보다)."""
    confirmed = bool(policy.get("confirmed"))
    sections: list[dict[str, object]] = []
    for pool_name, title in _DRAWER_SECTIONS:
        entry = pools.get(pool_name)
        kind = pool_name_to_effect_kind(pool_name)
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
            description = app_preset_description(grid, preset_no)
            used_by = _usage_for_slot(grid, preset_no)
            is_effect_band = (
                kind is not None
                and validate_preset_pool_assignment(kind, preset_no, policy) is None
            )
            entries.append(
                {
                    "preset_no": preset_no,
                    "name": name,
                    "usage_count": len(used_by),
                    "used_by": used_by,
                    "is_effect_band": is_effect_band,
                    # 카드 t569(REQ-LDBEAT-023(c), 리드 결정 B) — 칩 툴팁의
                    # "설명 텍스트"는 앱이 그 프리셋을 만들 때 저장한 설명
                    # (``grid["preset_descriptions"]``)이다. 없으면 콘솔에서
                    # 읽은 쇼 프리셋이라 설명은 비우고 출처만 "show" — 칩
                    # 위 글자가 이미 콘솔 이름이므로 툴팁에 다시 쓰지 않는다.
                    # 콘솔 NOTE 는 읽지 않는다(t569 실측: 칩 서랍 34칸 모두
                    # 빈 값, `.moai/reports/t569/run-verdict.md`).
                    "description": description,
                    "description_source": "app" if description else "show",
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
