"""콘솔 프리셋 풀에서 라벨로 슬롯을 찾는 판독기 — 대화 길·업로드 길 공용.

카드 t480(SPEC-LDDESIGN-001 REQ-003) — 원래 ``ChatSession`` 메서드였던 풀 판독
(``_paged_pool_children``·``_resolve_named_pool_no``)과 라벨 → 슬롯 해석
(포지션 t232·페이저 T12·흰색 t453)을 이 모듈로 옮겼다. 업로드 길
(``server/orchestrator/tools.py``)은 층 경계 때문에 ``server.web`` 을 import 할 수
없어서, 조립기 큐의 라벨을 콘솔 슬롯으로 바꾸려면 이 판독기가 세션 밖에 있어야 했다.

판독 규율은 한 글자도 바꾸지 않았다. 콘솔을 묻는 방법만 호출자가 넘긴다 —
``query(probe_id, arguments)`` 는 ``query_state`` 도구와 같은 인자
(``{"path": ..., "offset": ...}``)를 받아 해석된 응답(dict)을, 실패하면 ``None`` 을
돌려준다. 세션은 도구 레지스트리로, 업로드 길은 상태 포트로 이 함수를 만든다.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping

from server.design.phaser_catalog import _PHASER_LABEL_POOL_NAME
from server.design.preset_names import NAME_ABSENT, NAME_AMBIGUOUS, match_preset_name
from server.design.song_cue_render import _WHITE_PRESET_LABELS
from server.spatial.pointing import SpatialPointingError

#: ``query(probe_id, arguments) -> payload | None``.
StateQuery = Callable[[str, Mapping[str, object]], object | None]
#: ``resolve_named_pool_no(target_name, *, probe_id) -> int | None``.
PoolNoResolver = Callable[..., int | None]
#: ``paged_pool_children(path, *, probe_id) -> {slot: name} | None``.
PoolReader = Callable[..., dict[int, str | None] | None]


def paged_pool_children(
    query: StateQuery, path: str, *, probe_id: str
) -> dict[int, str | None] | None:
    """``path`` 컨테이너의 자식 번호→이름 완전 판독 — 페이징 공용 몸통.

    The responder caps ``children`` at 24 per reply (PROTOCOL §4.2), so
    containers past 24 children need PAGING: follow-up queries carry
    ``offset`` (the accumulated child count) and a paging-aware responder
    echoes it back. Live-measured 2026-08-16: a 31-preset pool made the
    store read-back report 10 freshly stored presets as "미확인 0/10"
    because slots 41~50 fell outside the first window — paged reads
    recover exactly that case.

    Names ride along because span-family selection needs them: the
    regeneration card offered a BASIC span for an FX regeneration request
    (live 2026-08-16) and the first option got picked — the name of a
    span's first slot is what tells the families apart.

    Truncation WITHOUT progress is still "cannot be read", not a smaller
    container: a legacy responder ignores ``offset`` (no echo, always the
    first window), so a paged reply missing the matching echo — or adding
    zero new children, or erroring, or blowing the page cap — aborts to
    None. Unknown ≠ empty — partial reads join the unreadable path, which
    every caller already renders honestly.
    """
    slots: dict[int, str | None] = {}
    seen = 0
    for page in range(10):  # 상한 10페이지(240슬롯) — 실제 컨테이너 크기의 여유 상계
        arguments: dict[str, object] = {"path": path}
        if page:
            # 후속 창은 누적 자식 수부터. 첫 요청은 기존 무페이징 판독과
            # 인자까지 동일하다(하위호환 — 구버전 응답기도 첫 창은 준다).
            arguments["offset"] = seen
        payload = query(f"{probe_id}-p{page}" if page else probe_id, arguments)
        children = payload.get("children") if isinstance(payload, dict) else None
        if not isinstance(children, list):
            return None
        if page:
            # 무진전 방어 — 구버전 응답기는 offset을 무시하고 항상 첫 창을
            # 돌려준다(에코 부재). 에코 불일치·신규 자식 0개도 같은 갈래:
            # 반복해도 전진이 없으므로 즉시 부분 판독(None)으로 내려간다.
            echo = payload.get("offset")
            if isinstance(echo, bool) or echo != seen:
                return None
            if not children:
                return None
        for child in children:
            if isinstance(child, dict):
                try:
                    # 실기 responder는 슬롯 번호를 "i"로 보낸다 (PROTOCOL §4.2,
                    # rig_object와 동일 규칙); "no"는 정규화된 페이로드용.
                    number = int(child.get("i", child.get("no")))
                except (TypeError, ValueError):
                    continue
                name = child.get("name")
                slots[number] = name if isinstance(name, str) else None
        seen += len(children)
        # 절단 판정은 두 경로 — 응답기 truncated 플래그 또는 childCount 산술.
        # 한쪽만 삭제돼도 나머지가 잡는다 (TRUNCATE-001과 같은 이중 방어).
        node = payload.get("node")
        child_count = node.get("childCount") if isinstance(node, dict) else None
        more = bool(payload.get("truncated")) or (
            isinstance(child_count, int) and child_count > seen
        )
        if not more:
            return slots  # 누적 == 총계(또는 총계 미달 주장 없음) — 완전 판독
        if not children:
            # 빈 창이 "더 있다"고 주장 — offset이 전진할 수 없는 모순.
            return None
    return None  # 페이지 상한 초과 — 부분 판독은 더 작은 컨테이너가 아니다


def resolve_named_pool_no(
    query: StateQuery, pool_root: str, target_name: str, *, probe_id: str
) -> int | None:
    """이름이 정확히 ``target_name``인 프리셋 풀의 번호 — 공용 몸통.

    `instantiate.py:220`의 함정을 세션 계층에 적용한 것이다(REQ-COLORPRESET-
    002): *"Preset 4.1 = Color"는 룰북 예시 프로즈이지 이 쇼파일의 계약이
    아니다* — 풀 이름은 운영자가 바꿀 수 있으므로 번호를 하드코딩하면
    손으로 만든 프리셋을 덮는다. ``DataPool/PresetPools`` 자식에서 이름
    일치 풀을 찾고, 실패·부재·절단은 전부 ``None``(거부)이다. 풀 목록은
    십수 개 규모라 페이징 없이 한 창을 읽고, 절단 주장(플래그 또는
    childCount 산술)이 있으면 추측하지 않는다.
    """
    payload = query(probe_id, {"path": pool_root})
    children = payload.get("children") if isinstance(payload, dict) else None
    if not isinstance(children, list):
        return None
    node = payload.get("node")
    child_count = node.get("childCount") if isinstance(node, dict) else None
    if bool(payload.get("truncated")) or (
        isinstance(child_count, int) and child_count > len(children)
    ):
        # 절단된 목록에 대상 풀이 없다 ≠ 풀이 없다 — 모름은 거부다.
        return None
    for child in children:
        if not isinstance(child, dict) or child.get("name") != target_name:
            continue
        try:
            return int(child.get("i", child.get("no")))
        except (TypeError, ValueError):
            return None
    return None


def white_preset_slots(
    resolve_pool_no: PoolNoResolver, read_pool: PoolReader, pool_root: str
) -> dict[str, tuple[int, int] | str]:
    """카드 t453 — 흰색 이름 → 콘솔 컬러 프리셋 ``(풀, 슬롯)`` 또는 못 찾은 사유.

    풀을 한 번 완전 판독하고, 이름 매칭은 공용 규칙
    ``server.design.preset_names.match_preset_name``(t477)의 **정확한 이름**
    규칙만 쓴다(``#n`` 접미 무시). 라벨 전체를 알므로 첫 낱말 규칙은 켜지
    않는다 — 「웜」만으로 찾는 것은 짐작이다. 슬롯이 하나면 쓰고, 없거나
    여럿이면 사유를 남긴다. 컬러 풀 번호는 이름 "Color"로 해석한다
    (하드코딩 금지, ``phaser_slot_by_label``과 같은 리졸버).
    """
    pool_no = resolve_pool_no("Color", probe_id="song-white-preset-pool")
    if pool_no is None:
        reason = "Color 프리셋 풀을 찾지 못해 흰색 프리셋 라벨을 확인할 수 없습니다"
        return dict.fromkeys(_WHITE_PRESET_LABELS, reason)
    children = read_pool(f"{pool_root}/{pool_no}", probe_id="song-white-preset-slots")
    if children is None:
        reason = (
            f"Color 프리셋 풀(Preset {pool_no}.x)을 읽지 못해 흰색 프리셋 라벨을 확인할 수 없습니다"
        )
        return dict.fromkeys(_WHITE_PRESET_LABELS, reason)
    resolved: dict[str, tuple[int, int] | str] = {}
    for white, label in _WHITE_PRESET_LABELS.items():
        match = match_preset_name(children, label)
        if match.slot is not None:
            resolved[white] = (pool_no, match.slot)
        elif match.kind == NAME_AMBIGUOUS:
            resolved[white] = (
                f"'{label}' 라벨이 Color 프리셋 여러 슬롯 {list(match.candidates)}에 있어 "
                "특정할 수 없습니다"
            )
        else:
            resolved[white] = f"'{label}' 라벨의 Color 프리셋을 콘솔에서 찾지 못했습니다"
    return resolved


def phaser_slot_by_label(
    resolve_pool_no: PoolNoResolver, read_pool: PoolReader, pool_root: str, label: str
) -> tuple[int, int] | None:
    """카탈로그 페이저 라벨 → 실기 ``(pool_no, slot)``, 못 찾으면 None(거부).

    슬롯 번호는 코드 상수가 아니다 — 저장 시점에 실제로 어느 칸에 앉았는지
    는 운영자의 저장 순서가 정하므로, 라벨을 키로 실기를 페이지드로 완전
    열거해 찾는다(T11 프로브 §5, ``paged_pool_children`` 실측 입증). 어느
    풀을 열지는 ``_PHASER_LABEL_POOL_NAME``(카탈로그 3계열이 서로소이므로
    고정 매핑이 안전)으로 정하고, 그 풀의 실기 번호는 ``resolve_named_
    pool_no``로 해석한다(하드코딩 금지). 중복명 접미('#2')는
    ``presets_api._base_name``과 같은 규율로 관용한다. 풀 해석 실패·페이징
    판독 실패·라벨 부재는 모두 None(추측 금지) — 판독 실패와 부재를 구별한
    고지는 호출자 책임이다.
    """
    pool_name = _PHASER_LABEL_POOL_NAME.get(label)
    if pool_name is None:
        return None
    probe_slug = pool_name.lower().replace(" ", "")
    pool_no = resolve_pool_no(pool_name, probe_id=f"phaser-recall-pool-{probe_slug}")
    if pool_no is None:
        return None
    children = read_pool(f"{pool_root}/{pool_no}", probe_id=f"phaser-recall-slots-{probe_slug}")
    if children is None:
        return None
    for slot, name in children.items():
        base = name.split("#", 1)[0] if isinstance(name, str) else None
        if base == label:
            return pool_no, slot
    return None


def resolve_position_preset_labels(
    pool: Mapping[int, str | None] | None,
    labels: Iterable[str],
    *,
    start: int,
    span: int,
    pool_no: int,
) -> dict[str, int]:
    """룩 라벨 집합 -> Position 프리셋 슬롯(t232) — 판독한 풀 하나로 해석한다.

    `start + BASIC_POSITION_SEQUENCE.index(label)`로 번호를 짓던 옛
    경로는 그 자리가 실제로 그 라벨인지 확인하지 않았다 — 연속 10칸이
    다른 프리셋(예: 시트 프리셋)으로 채워져 있으면 조용히 엉뚱한 프리셋을
    불렀다(카드 t232 판독). 풀을 완전 판독한 결과(``pool``)에서 라벨을
    직접 찾는다.

    라벨은 베이스이름 매칭으로 찾는다(``#n`` 중복 접미 제거). 같은
    베이스이름이 여러 슬롯에 있으면 운영자가 고른 구간
    ``[start, start+span-1]`` 안의 슬롯을 우선한다 — 구간 안에 정확히
    하나가 있으면 그것을 쓴다. 구간 안에 하나도 없는데 구간 밖에 둘
    이상이면 모호 — 거부한다(추측 금지). 어디서든 후보가 딱 하나뿐이면
    그것을 쓴다. 풀을 읽지 못했으면(``pool is None``) 그 자체로 거부한다 —
    라벨 부재와는 다른 사유를 남긴다.
    """
    if pool is None:
        raise SpatialPointingError(
            f"Position 프리셋 풀(Preset {pool_no}.x)을 읽지 못해 라벨을 확인할 수 없습니다"
        )
    # 매칭 규칙은 공용 순수 함수 하나에 있다(t477 — 초안 이름 판독·t453 과 같은 몸통).
    resolved: dict[str, int] = {}
    for label in labels:
        if label in resolved:
            continue
        match = match_preset_name(pool, label, span=(start, start + span - 1))
        if match.slot is not None:
            resolved[label] = match.slot
            continue
        if match.kind == NAME_ABSENT:
            raise SpatialPointingError(
                f"'{label}' 라벨의 Position 프리셋을 콘솔에서 찾지 못했습니다"
            )
        raise SpatialPointingError(
            f"'{label}' 라벨이 Position 프리셋 여러 슬롯 {list(match.candidates)}에 있어 "
            "특정할 수 없습니다"
        )
    return resolved
