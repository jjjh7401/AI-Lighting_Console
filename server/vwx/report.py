"""대조 결과 -> 구조화 페이로드 + 한국어 표현 (REQ-VWX-023~025). 문서 근거 · 실물 미검증.

판독 실패·데이터 블록 미탐·미수행 판정·부정 전제를 전부 구조화된 페이로드
부류로 담는다 — 예외 산문으로 흘리지 않는다(REQ-VWX-023). 사용자 대면
문자열은 한국어다.

라벨 표는 ``server/prechk/report.py``의 **패턴**을 계승한다(``design.md``
§2.2 — "라벨 표를 코드 표현 계층에 두고 공개 접근자로 알 수 없는 코드를 그대로
통과시키지 않는다") — 닫힌 어휘 + 라벨 표 + 공개 접근자 3요소를 그대로
따르지만, **레지스트리 자체는 공유하지 않는다**: prechk의
``CLOSED_VOCABULARIES``/``VOCABULARY_LABELS``에 새 최상위 키(``diff_kind``)를
추가하면 그 레지스트리의 정확한-집합을 단언하는 기존 테스트
(``server/tests/test_prechk_verdicts.py`` ``TestVocabularies``,
``server/tests/test_prechk_report.py``)가 깨진다 — 실측 확인됨. PRESERVE는
"기존 스위트를 깨지 않는다"가 상위 불변식이므로, VWX는 자신의 신규 어휘를
**독립된 레지스트리**로 소유하고 prechk의 8개 파일은 진짜 0-diff로 남긴다.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol

from server.vwx.diff import (
    DIFF_KIND,
    FID_CID_UNREACHABLE,
    FOOTPRINT_OVERLAP_DESCOPE,
    SKIPPED_CHECK_KIND_VWX,
    WORKSHEET_BLOCK_UNDETECTED,
    DiffResult,
)


class _ShapedReadFailure(Protocol):
    """판독 단계 3종(reader/columns/address)이 공유하는 (row, kind, detail) 형태.

    세 모듈이 각자의 판독 실패 dataclass를 갖지만(reader.ReadFailure,
    columns.ColumnReadFailure, address.AddressReadFailure), 필드 형태가
    동일하다 — 이 프로토콜로 duck-typing해 하나의 리포트 필드로 합친다.
    """

    row: int | None
    kind: str
    detail: str


#: 닫힌 판정 어휘 — vwx 자체 레지스트리. server/prechk/verdicts.py의
#: CLOSED_VOCABULARIES 패턴을 계승하되 그 레지스트리 자체는 건드리지 않는다
#: (docstring 참조).
VWX_CLOSED_VOCABULARIES = MappingProxyType(
    {
        "diff_kind": DIFF_KIND,
        "skipped_check_kind": SKIPPED_CHECK_KIND_VWX,
    }
)


class UnknownVwxVerdict(ValueError):
    """VWX 닫힌 어휘 밖의 값이 판정 표면에 도달했다."""


def validate_vwx(vocabulary: str, value: str) -> str:
    """``value``가 ``vocabulary``에 속하면 그대로 반환하고, 아니면 예외를 던진다."""
    try:
        allowed = VWX_CLOSED_VOCABULARIES[vocabulary]
    except KeyError:
        raise UnknownVwxVerdict(
            f"no such vwx vocabulary {vocabulary!r} (known: {sorted(VWX_CLOSED_VOCABULARIES)})"
        ) from None
    if value not in allowed:
        raise UnknownVwxVerdict(f"{value!r} is not a {vocabulary} (allowed: {sorted(allowed)})")
    return value


_DIFF_KIND_LABELS = {
    "missing_in_console": "콘솔 미확인 — 도면에는 있으나 콘솔 실측에 대응 항목이 없다",
    "address_collision": "주소 충돌 — 콘솔 실측 기준 중복(precheck_patch 판정 재사용)",
    "quantity_mismatch": "수량 불일치 — 타입별 도면 수량과 콘솔 관측 수량이 다르다",
}

_SKIPPED_CHECK_KIND_LABELS = {
    FID_CID_UNREACHABLE: "FID/CID 아이덴티티 대조 미수행 — 슬롯==FID 쇼파일에서 원리적으로 불가",
    FOOTPRINT_OVERLAP_DESCOPE: "구간 겹침 확장 판정 미수행 — DMX Footprint 폭 출처 미주입",
    WORKSHEET_BLOCK_UNDETECTED: "워크시트 데이터 블록 미탐 — 헤더 후보를 구조적으로 찾지 못함",
}

#: 라벨 표 레지스트리 — 어휘와 키 집합이 정확히 일치함을 아래서 즉시 검증한다
#: (server/prechk/report.py의 동일 패턴 계승, AC-VWX-023 ①).
_VWX_VOCABULARY_LABELS = MappingProxyType(
    {
        "diff_kind": MappingProxyType(_DIFF_KIND_LABELS),
        "skipped_check_kind": MappingProxyType(_SKIPPED_CHECK_KIND_LABELS),
    }
)

if set(_VWX_VOCABULARY_LABELS) != set(VWX_CLOSED_VOCABULARIES):
    raise UnknownVwxVerdict(
        "vwx label tables and closed vocabularies disagree: "
        f"tables {sorted(_VWX_VOCABULARY_LABELS)} vs vocabularies {sorted(VWX_CLOSED_VOCABULARIES)}"
    )
for _vwx_vocabulary, _vwx_codes in VWX_CLOSED_VOCABULARIES.items():
    if set(_VWX_VOCABULARY_LABELS[_vwx_vocabulary]) != set(_vwx_codes):
        raise UnknownVwxVerdict(f"vwx label table for {_vwx_vocabulary} mismatches its vocabulary")


def vwx_label(vocabulary: str, code: str) -> str:
    """VWX 닫힌 어휘 코드의 한국어 라벨 — 공개 접근자를 통해서만 얻는다.

    :func:`validate_vwx`가 먼저 실행되므로 미등록 어휘·코드 둘 다 조회 전에
    실패한다 — 원문 코드를 라벨인 척 그대로 돌려주지 않는다(REQ-VWX-024).
    """
    validate_vwx(vocabulary, code)
    return _VWX_VOCABULARY_LABELS[vocabulary][code]


def diff_kind_label(code: str) -> str:
    return vwx_label("diff_kind", code)


def skipped_check_kind_label(code: str) -> str:
    return vwx_label("skipped_check_kind", code)


@dataclass(frozen=True)
class VwxReport:
    """``precheck_vectorworks_diff`` 툴의 전체 사용자 대면 페이로드.

    ``design.md`` §5.1이 정한 최상위 키를 그대로 따른다 — ``designed_rig``·
    ``console_rig``(재계산 없이 참조만)·``diffs``·``skipped_checks``·
    ``read_failures``·``summary_ko``.
    """

    diff: DiffResult
    read_failures: tuple[_ShapedReadFailure, ...] = ()

    def _diffs(self) -> dict[str, list[dict]]:
        return {
            "missing_in_console": [
                {
                    "unit_number": entry.unit_number,
                    "instrument_type": entry.instrument_type,
                    "universe": entry.universe,
                    "address": entry.address,
                    "detail": entry.detail,
                }
                for entry in self.diff.missing_in_console
            ],
            "address_collision": [
                {
                    "universe": entry.universe,
                    "address": entry.address,
                    "detail": entry.detail,
                    "members": list(entry.members),
                }
                for entry in self.diff.address_collisions
            ],
            "quantity_mismatch": [
                {
                    "instrument_type": entry.instrument_type,
                    "designed_count": entry.designed_count,
                    "console_count": entry.console_count,
                }
                for entry in self.diff.quantity_mismatches
            ],
        }

    def _vw_patch_conflicts(self) -> list[dict]:
        return [
            {
                "kind": entry.kind,
                "universe": entry.universe,
                "address": entry.address,
                "detail": entry.detail,
            }
            for entry in self.diff.designed_rig.vw_patch_conflicts
        ]

    def _skipped_checks(self) -> list[dict]:
        return [{"kind": entry.kind, "reason": entry.reason} for entry in self.diff.skipped_checks]

    def _read_failures(self) -> list[dict]:
        return [
            {"row": failure.row, "kind": failure.kind, "detail": failure.detail}
            for failure in self.read_failures
        ]

    def _join_key_conflicts(self) -> list[dict]:
        return [
            {"key": entry.key, "detail": entry.detail, "rows": list(entry.rows)}
            for entry in self.diff.designed_rig.join_key_conflicts
        ]

    def summary_ko(self) -> str:
        diffs = self._diffs()
        parts = [f"도면 픽스처 {len(self.diff.designed_rig.fixtures)}개"]
        any_diff = False
        for diff_kind, entries in diffs.items():
            if entries:
                any_diff = True
                parts.append(f"{diff_kind_label(diff_kind)} {len(entries)}건")
        if not any_diff:
            parts.append("차이 없음")
        if self.diff.skipped_checks:
            names = " · ".join(
                skipped_check_kind_label(entry.kind) for entry in self.diff.skipped_checks
            )
            parts.append(f"미수행 판정: {names}")
        if self.read_failures:
            parts.append(f"판독 실패 {len(self.read_failures)}건")
        return ". ".join(parts) + "."

    def to_dict(self) -> dict:
        designed = self.diff.designed_rig
        return {
            "designed_rig": {
                "fixture_count": len(designed.fixtures),
                "device_type_column_present": designed.device_type_column_present,
                "join_key_conflicts": self._join_key_conflicts(),
                "vw_patch_conflicts": self._vw_patch_conflicts(),
            },
            "console_rig": {
                # 재계산 없이 read_inventory/build_patch_sheet의 산출을 그대로
                # 참조한다(REQ-VWX-022) — Inventory.to_dict()가 그 산출이다.
                "inventory": self.diff.console_inventory.to_dict(),
            },
            "diffs": self._diffs(),
            "skipped_checks": self._skipped_checks(),
            "read_failures": self._read_failures(),
            "summary_ko": self.summary_ko(),
        }


def build_vwx_report(
    diff: DiffResult, *, read_failures: tuple[_ShapedReadFailure, ...] = ()
) -> VwxReport:
    """대조 결과 -> :class:`VwxReport`(REQ-VWX-023)."""
    return VwxReport(diff=diff, read_failures=read_failures)
