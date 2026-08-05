"""주소 처리 — 4형식 정규화, 미패치 sentinel, 멀티시스템 차단 (REQ-VWX-008~011).
문서 근거 · 실물 미검증.

Vectorworks는 한 픽스처의 주소를 ``Universe/Address``(조합) · ``Universe``(정수)
· ``DMX Address``(1..512) · ``Absolute Address``(``(u-1)*512+a``) 네 형식으로
동시에 노출할 수 있다(``research.md`` §4). 우선순위는 ``Universe``+``DMX
Address`` 쌍 > ``Universe/Address`` 조합값 > ``Absolute Address`` 역산(전제
검증 성공 시에만)이다 — 추측하지 않는다(REQ-VWX-009).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from server.prechk.patch import AddressParse
from server.prechk.patch import normalize_address as console_normalize_address

PATCHED = "patched"
UNPATCHED_DESIGNED = "unpatched_designed"
MULTI_SYSTEM_AMBIGUOUS = "multi_system_ambiguous"

ADDRESS_CLASSIFICATION = frozenset({PATCHED, UNPATCHED_DESIGNED, MULTI_SYSTEM_AMBIGUOUS})

READ_FAILURE_ABS_UNVERIFIED = "absolute_address_premise_unverified"
READ_FAILURE_MULTI_SYSTEM = "multi_system_ambiguous_universe"
READ_FAILURE_ADDRESS_UNPARSEABLE = "address_unparseable"
READ_FAILURE_NO_ADDRESS_DATA = "no_address_data"
#: 3중 표현 교차검증(M0 실물 샘플 반영) — Universe+DMX Address 쌍이 최우선
#: 신뢰 소스이므로 해석 자체는 그대로 진행하되(REQ-VWX-009 우선순위 불변),
#: 동시에 존재하는 Absolute Address가 (u-1)*512+a와 다르면 Universes pane이
#: 기본 연속 512블록이 아니라는 뜻이다(Start#/End# 편집 또는 유니버스 삭제로
#: 구멍) — 경고로만 남기고 Absolute Address로 유니버스를 역산하지 않는다.
READ_FAILURE_ADDRESS_TRIPLE_MISMATCH = "address_triple_mismatch"

_KIND_RESOLVED = "resolved"
_KIND_BLOCKED = "blocked"
_KIND_READ_FAILURE = "read_failure"

_UNIVERSE_ADDRESS_SPLIT = re.compile(r"[/:\-.]")

#: 콘솔의 유니버스당 채널 슬롯 수. Absolute Address 역산(REQ-VWX-009)에서만 쓴다.
_UNIVERSE_WIDTH = 512


@dataclass(frozen=True)
class AddressOutcome:
    """한 레코드의 주소 해석 산출 — 성공/차단/판독실패 셋 중 하나.

    ``kind`` != ``"resolved"``일 때는 예외가 아니라 이 구조 자체가 실패
    신호다(``normalize_address``의 ``AddressParse.error``와 동형 — 둘 다
    예외 없이 실패를 나타내는 구조다, AC-VWX-012 ②).
    """

    kind: str
    universe: int | None = None
    address: int | None = None
    classification: str | None = None
    reason_code: str | None = None
    detail: str = ""
    #: 해석은 성공했지만 별도로 보고해야 할 경고(3중 표현 불일치 등). 성공/실패와
    #: 독립적인 축이다 — ``kind``가 ``resolved``여도 이 값이 채워질 수 있다.
    warning_kind: str | None = None
    warning_detail: str = ""


def _blank(value: str | None) -> bool:
    return value is None or not value.strip()


def _to_int(value: str | None) -> int | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def split_universe_address(raw: str) -> tuple[int | None, int | None]:
    """``Universe/Address`` 계열 조합값을 (universe, address)로 나눈다.

    구분자는 ``/``·``.``·``-``·``:`` 중 가변(``research.md`` §4).
    """
    parts = [part for part in _UNIVERSE_ADDRESS_SPLIT.split(raw.strip()) if part]
    if len(parts) != 2:
        return None, None
    return _to_int(parts[0]), _to_int(parts[1])


def classify_and_resolve(
    fields: dict[str, str],
    *,
    system_letters: frozenset[str] = frozenset(),
    contiguous_512_confirmed: bool = False,
) -> AddressOutcome:
    """컬럼 해석된 레코드 하나의 정규화 주소 + 분류(REQ-VWX-008~010).

    ``system_letters``는 파일 전체에서 관측된 System(A-Z) 문자 집합이다 —
    v0.1.6부터 이 값이 2개 이상이어도 설계 측 주소 해석 자체는 더 이상
    차단하지 않는다(결함 1, P0 — 실물 샘플 3종 재현). 주소 아이덴티티를
    ``(system, universe, address)``로 확장해 System별로 스코프를 나누면
    Universe 재사용은 더 이상 모호하지 않다 — 콘솔에는 System 개념이 없어
    콘솔 대조(``diff.py``)만 별도로 미수행 처리한다(REQ-VWX-010 재해석).
    ``contiguous_512_confirmed``는 그 파일의 Universes 창이 연속 기본
    512블록이라는 전제가 외부에서 검증됐는지 여부다 — 기본값 False로,
    검증되지 않은 한 ``Absolute Address`` 역산을 절대 수행하지 않는다
    (추측 금지, REQ-VWX-009).
    """
    universe_raw = fields.get("universe")
    dmx_raw = fields.get("address")
    combined_raw = fields.get("universe_address")
    absolute_raw = fields.get("absolute_address")

    # 미패치 sentinel — DMX Address 값 자체가 0이거나 공란이면 "설계됨·미배정"
    # 이다(REQ-VWX-008). Universe가 함께 있으면 그 값을 보존한다.
    if dmx_raw is not None and not _blank(dmx_raw) and _to_int(dmx_raw) == 0:
        return AddressOutcome(
            kind=_KIND_RESOLVED,
            classification=UNPATCHED_DESIGNED,
            universe=_to_int(universe_raw),
            address=0,
            detail="설계됨 · 미배정(DMX Address=0)",
        )
    universe_present = universe_raw is not None and not _blank(universe_raw)
    if dmx_raw is not None and _blank(dmx_raw) and universe_present:
        return AddressOutcome(
            kind=_KIND_RESOLVED,
            classification=UNPATCHED_DESIGNED,
            universe=_to_int(universe_raw),
            address=0,
            detail="설계됨 · 미배정(DMX Address 공란)",
        )

    # 최우선 — Universe + DMX Address 쌍(추측 불필요, 가장 신뢰).
    if (
        universe_raw is not None
        and dmx_raw is not None
        and not _blank(universe_raw)
        and not _blank(dmx_raw)
    ):
        universe, address = _to_int(universe_raw), _to_int(dmx_raw)
        if universe is None or address is None:
            return AddressOutcome(
                kind=_KIND_READ_FAILURE,
                reason_code=READ_FAILURE_ADDRESS_UNPARSEABLE,
                detail=f"Universe/DMX Address 쌍 파싱 불가('{universe_raw}'/'{dmx_raw}')",
            )
        warning_kind, warning_detail = None, ""
        if absolute_raw is not None and not _blank(absolute_raw):
            absolute_value = _to_int(absolute_raw)
            if absolute_value is not None:
                expected = (universe - 1) * _UNIVERSE_WIDTH + address
                if absolute_value != expected:
                    warning_kind = READ_FAILURE_ADDRESS_TRIPLE_MISMATCH
                    warning_detail = (
                        f"Absolute Address({absolute_value})가 (u-1)*512+a 기댓값({expected})과 "
                        f"불일치 — Universes pane이 기본 연속 512블록이 아닐 수 있다(Start#/End# "
                        "편집 또는 유니버스 삭제). Universe+DMX Address 조합을 그대로 신뢰하고 "
                        "Absolute Address로 유니버스를 역산하지 않는다."
                    )
        return AddressOutcome(
            kind=_KIND_RESOLVED,
            classification=PATCHED,
            universe=universe,
            address=address,
            warning_kind=warning_kind,
            warning_detail=warning_detail,
        )

    # 차선 — Universe/Address 조합값(역산이 필요 없다).
    if combined_raw is not None and not _blank(combined_raw):
        universe, address = split_universe_address(combined_raw)
        if universe is None or address is None:
            return AddressOutcome(
                kind=_KIND_READ_FAILURE,
                reason_code=READ_FAILURE_ADDRESS_UNPARSEABLE,
                detail=f"Universe/Address 조합값 파싱 불가('{combined_raw}')",
            )
        if address == 0:
            return AddressOutcome(
                kind=_KIND_RESOLVED,
                classification=UNPATCHED_DESIGNED,
                universe=universe,
                address=0,
                detail="설계됨 · 미배정(조합값 주소=0)",
            )
        return AddressOutcome(
            kind=_KIND_RESOLVED, classification=PATCHED, universe=universe, address=address
        )

    # 최후 — Absolute Address 역산. 전제(연속 512블록) 검증 성공 시에만.
    if absolute_raw is not None and not _blank(absolute_raw):
        value = _to_int(absolute_raw)
        if value is None:
            return AddressOutcome(
                kind=_KIND_READ_FAILURE,
                reason_code=READ_FAILURE_ADDRESS_UNPARSEABLE,
                detail=f"Absolute Address 파싱 불가('{absolute_raw}')",
            )
        if value == 0:
            return AddressOutcome(
                kind=_KIND_RESOLVED,
                classification=UNPATCHED_DESIGNED,
                universe=None,
                address=0,
                detail="설계됨 · 미배정(Absolute Address=0)",
            )
        if not contiguous_512_confirmed:
            return AddressOutcome(
                kind=_KIND_READ_FAILURE,
                reason_code=READ_FAILURE_ABS_UNVERIFIED,
                detail=(
                    "Absolute Address 단일값 — 연속 기본 512블록 전제가 검증되지 "
                    "않아 역산을 보류한다(추측 금지, REQ-VWX-009)"
                ),
            )
        universe = ((value - 1) // _UNIVERSE_WIDTH) + 1
        address = ((value - 1) % _UNIVERSE_WIDTH) + 1
        return AddressOutcome(
            kind=_KIND_RESOLVED, classification=PATCHED, universe=universe, address=address
        )

    return AddressOutcome(
        kind=_KIND_READ_FAILURE,
        reason_code=READ_FAILURE_NO_ADDRESS_DATA,
        detail="해석 가능한 주소 표현이 없다",
    )


@dataclass(frozen=True)
class ResolvedRecord:
    """주소까지 해석된 레코드 — ``rig.py``(M4)가 소비하는 입력 형태."""

    fields: dict[str, str]
    extra: dict[str, str]
    row_index: int
    universe: int | None
    address: int | None
    classification: str


@dataclass(frozen=True)
class AddressReadFailure:
    row: int | None
    kind: str
    detail: str


def _observed_system_letters(fields_list: list[dict[str, str]]) -> frozenset[str]:
    letters: set[str] = set()
    for fields in fields_list:
        system = fields.get("system")
        if system and system.strip():
            letters.add(system.strip().upper()[:1])
    return frozenset(letters)


def resolve_all(
    records: list,
    *,
    contiguous_512_confirmed: bool = False,
) -> tuple[list[ResolvedRecord], list[AddressReadFailure]]:
    """레코드 목록 전체를 주소 해석한다. ``records``는 ``columns.ColumnRecord``.

    ``system_letters``는 파일 전체에서 계산된다 — 레코드 하나만으로는
    멀티시스템 여부를 알 수 없기 때문이다.
    """
    system_letters = _observed_system_letters([record.fields for record in records])
    resolved: list[ResolvedRecord] = []
    failures: list[AddressReadFailure] = []
    for record in records:
        outcome = classify_and_resolve(
            record.fields,
            system_letters=system_letters,
            contiguous_512_confirmed=contiguous_512_confirmed,
        )
        if outcome.kind == _KIND_RESOLVED:
            resolved.append(
                ResolvedRecord(
                    fields=record.fields,
                    extra=record.extra,
                    row_index=record.row_index,
                    universe=outcome.universe,
                    address=outcome.address,
                    classification=outcome.classification or PATCHED,
                )
            )
            if outcome.warning_kind is not None:
                # 해석은 성공했으나 3중 표현 불일치 등 별도 경고가 있다 — 레코드는
                # resolved에 그대로 남고, 경고만 구조화된 형태로 추가 보고된다.
                failures.append(
                    AddressReadFailure(
                        row=record.row_index,
                        kind=outcome.warning_kind,
                        detail=outcome.warning_detail,
                    )
                )
        else:
            failures.append(
                AddressReadFailure(
                    row=record.row_index,
                    kind=outcome.reason_code or "unknown",
                    detail=outcome.detail,
                )
            )
    return resolved, failures


def to_console_form(universe: int, address: int) -> AddressParse:
    """(universe, address) 정수를 콘솔 표기로 되돌려 ``normalize_address``와
    같은 표현 규약을 검증한다(REQ-VWX-011, AC-VWX-012)."""
    return console_normalize_address(f"{universe}.{address}")
