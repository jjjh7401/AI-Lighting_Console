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
    CONSOLE_FOOTPRINT_WIDTH_INJECTION_DEFERRED,
    DIFF_KIND,
    FID_CID_UNREACHABLE,
    FOOTPRINT_OVERLAP_DESCOPE,
    MULTI_SYSTEM_MAPPING_ABSENT,
    SKIPPED_CHECK_KIND_VWX,
    WORKSHEET_BLOCK_UNDETECTED,
    DiffResult,
)
from server.vwx.reader import READ_FAILURE_NOT_PATCH_SOURCE

#: 특정 판독 실패 kind — "찾아봤는데 없다"가 아니라 "패치 출처로 성립하지
#: 않는다"는 더 구체적인 사유 문구를 낼 수 있는 두 경우(REQ-VWX-003 대응)만
#: 특별 취급한다. **이 목록이 미수행 판정의 트리거는 아니다** — 아래
#: :meth:`VwxReport.comparison_performed`가 실제 트리거(불변식)이고, 이
#: 목록은 그 불변식이 참일 때 "왜"를 더 구체적으로 말하기 위한 사유 우선순위
#: 표일 뿐이다(v0.1.3 — kind 열거로 트리거를 정의하던 방식이 join_key_conflicts
#: 경로에서 샌 것을 계기로 재설계했다, `progress.md` §E.2 참조).
_STRUCTURAL_REJECTION_KINDS = frozenset({READ_FAILURE_NOT_PATCH_SOURCE, WORKSHEET_BLOCK_UNDETECTED})

#: 결함 2(P1, v0.1.7) — 스코프 한정 리드 임계값. 후보 행의 이 비율 이상이
#: 판독 실패로 탈락하면 ``summary_ko``는 "도면 픽스처 N개"보다 탈락 사실을
#: 먼저 말한다. 30%는 "이 대조 결과가 원본 리그를 대표한다고 보기 어려운"
#: 손실 규모의 보수적 하한이다 — 오탈자 한 줄 수준의 잡음(수 % 이내)과 실물
#: 02 사례(16행 중 15행, 93.75%)처럼 리그 대부분이 무너진 경우를 확실히
#: 가르는 값으로 골랐다. 임계 미만이어도(0건 초과) 스코프 한정 문구 자체는
#: 여전히 붙는다 — 다만 문장 맨 앞이 아니라 뒤에 붙는다.
_LARGE_DROP_LEAD_THRESHOLD = 0.3


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
    CONSOLE_FOOTPRINT_WIDTH_INJECTION_DEFERRED: (
        "콘솔 측 구간 겹침 폭 주입 미수행 — 설계 측은 수행했으나 콘솔 SLOT 키 주입은 2차 작업"
    ),
    MULTI_SYSTEM_MAPPING_ABSENT: (
        "콘솔 대조 미수행 — System→콘솔 유니버스 매핑이 없다(설계 측 산출은 정상 수행됨)"
    ),
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
    #: 결함 2(P1) — 판독은 됐으나 의도적으로 배제된 행(집계행·비-DMX 액세서리).
    #: ``read_failures``와 절대 섞지 않는다("판독 실패"와 "판독됐으나 제외"는
    #: 다른 사건이다).
    excluded_rows: tuple = ()

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

    def _excluded_rows(self) -> list[dict]:
        return [
            {"row": entry.row, "kind": entry.kind, "detail": entry.detail}
            for entry in self.excluded_rows
        ]

    def _join_key_conflicts(self) -> list[dict]:
        return [
            {"key": entry.key, "detail": entry.detail, "rows": list(entry.rows)}
            for entry in self.diff.designed_rig.join_key_conflicts
        ]

    def _design_overlaps(self) -> list[dict]:
        return [
            {"universe": entry.universe, "detail": entry.detail, "members": list(entry.members)}
            for entry in self.diff.designed_rig.design_overlaps
        ]

    def _fixtures(self) -> list[dict]:
        """픽스처마다 주소 근거(``address_basis``)를 개별 표기한다(v0.1.7, 결함 1 P0
        요건 b) — 리그 전체 등급(``designed_rig.address_basis``)과 별개로, 어느
        픽스처가 역산 근거를 썼는지 숨기지 않는다."""
        return [
            {
                "unit_number": fixture.unit_number,
                "instrument_type": fixture.instrument_type,
                "system": fixture.system,
                "universe": fixture.universe,
                "address": fixture.address,
                "classification": fixture.classification,
                "address_basis": fixture.address_basis,
            }
            for fixture in self.diff.designed_rig.fixtures
        ]

    def comparison_performed(self) -> bool:
        """대조를 실제로 수행했는가 — **불변식**: 설계상 리그 픽스처가 0대이면 False.

        v0.1.3 재설계 — 이전 버전은 ``read_failures``의 특정 kind(``not_
        patch_source``/``worksheet_block_undetected``) 목록에 매칭될 때만
        미수행으로 판정했다. 트리거를 kind로 나열하는 방식은 그 목록에 없는
        새 경로(예: ``join_key_conflicts``로 전 행이 탈락해 ``read_failures``는
        비어 있지만 ``fixture_count``는 0인 경우)에서 반드시 샌다 — 실제로
        샜다(코디네이터 재현). 트리거를 열거하는 대신 **결과로 판정**한다:
        비교할 설계 픽스처가 한 대도 없으면, 트리거가 무엇이든(판독 실패·
        조인키 충돌·전 행 액세서리 필터링·빈 파일·그 밖의 무엇이든) 대조는
        성립하지 않는다.

        v0.1.6 추가 — 설계 픽스처가 1대 이상이어도, System이 2개 이상
        관측되면(``observed_systems``) 콘솔 대조(``diffs``)는 여전히
        미수행이다(결함 1, P0). 이 경우와 "픽스처 0대"는 서로 다른 원인이며
        :meth:`_diffs_payload`/:meth:`summary_ko`가 사유 문구를 절대
        뭉뚱그리지 않는다 — 전자는 :meth:`_multi_system_reason`, 후자는
        :meth:`_no_fixtures_reason`만 쓴다.
        """
        return (
            len(self.diff.designed_rig.fixtures) > 0
            and len(self.diff.designed_rig.observed_systems) <= 1
        )

    def _multi_system_reason(self) -> str:
        """멀티시스템으로 콘솔 대조만 미수행인 사유 — 일반 판독 실패와 구별되는 문구다."""
        observed = " ".join(sorted(self.diff.designed_rig.observed_systems))
        return (
            f"System {observed} 관측 — System→콘솔 유니버스 매핑이 없어 콘솔 대조를 "
            "수행하지 않았다. 매핑이 주어지면 수행 가능하다."
        )

    def _diffs_not_performed_reason(self) -> str:
        """``diffs.reason``에 실릴 사유 — 픽스처 0대(:meth:`_no_fixtures_reason`)와
        멀티시스템(:meth:`_multi_system_reason`)을 원인별로 분리해 돌려준다."""
        if not self.diff.designed_rig.fixtures:
            return self._no_fixtures_reason()
        return self._multi_system_reason()

    def _no_fixtures_reason(self) -> str:
        """설계 픽스처가 0대인 **실제 원인**을 우선순위대로 지목한다.

        ``diffs.reason``에 실리는 값이다 — 결함 2 1차 교정 때부터 이 필드는
        판독 실패의 **원문 사유**를 그대로 실었다(회귀 테스트가 정확한
        문구를 검사한다). 이 값은 바뀌지 않는다; :meth:`summary_ko`가 문장
        형태로 감쌀 때만 접두어를 붙인다.

        여러 원인이 동시에 있을 수 있으므로(예: 판독 실패도 있고 조인키
        충돌도 있는 경우) 가장 구체적인 단서부터 우선한다: ① 판독이 애초에
        패치 출처로 성립하지 않은 두 종류 → ② 그 밖의 판독 실패 → ③ 조인키
        충돌(오늘 새로 드러난 경로) → ④ 그 무엇도 해당하지 않는 구조화되지
        않은 잔여 사례(방어적 폴백 — 이 분기가 실제로 도달하면 새 원인이
        발견됐다는 신호다).
        """
        structural = next(
            (
                failure
                for failure in self.read_failures
                if failure.kind in _STRUCTURAL_REJECTION_KINDS
            ),
            None,
        )
        if structural is not None:
            return structural.detail
        if self.read_failures:
            return f"판독 실패 {len(self.read_failures)}건으로 설계상 리그를 세우지 못했다"
        join_conflicts = self.diff.designed_rig.join_key_conflicts
        if join_conflicts:
            details = " · ".join(entry.detail for entry in join_conflicts[:3])
            more = f" 외 {len(join_conflicts) - 3}건" if len(join_conflicts) > 3 else ""
            count = len(join_conflicts)
            return f"조인 키 충돌 {count}건으로 설계상 리그를 세우지 못했다 — {details}{more}"
        return "설계상 리그에 유효한 픽스처가 0대다 — 구조화된 원인이 식별되지 않았다"

    def _no_fixtures_summary_lead(self) -> str:
        """``summary_ko``의 첫 문장 — 원인 종류에 맞는 서술로 감싼다.

        구조적 거부(``not_patch_source``/``worksheet_block_undetected``)는
        "패치 출처로 성립하지 않는다 — {사유}" 형태를, 그 밖의 원인은
        :meth:`_no_fixtures_reason`이 이미 완결된 문장이므로 그대로 쓴다.
        """
        structural = next(
            (
                failure
                for failure in self.read_failures
                if failure.kind in _STRUCTURAL_REJECTION_KINDS
            ),
            None,
        )
        if structural is not None:
            return f"패치 출처로 성립하지 않는다 — {structural.detail}"
        return self._no_fixtures_reason()

    def _excluded_breakdown_ko(self) -> str:
        """제외행 사유별 건수 — ``제외 4건(집계행 3 · 비DMX 액세서리 1)`` 형태(결함 2, P1)."""
        counts: dict[str, int] = {}
        for entry in self.excluded_rows:
            counts[entry.kind] = counts.get(entry.kind, 0) + 1
        labels = {
            "aggregate_row": "집계행",
            "non_dmx_accessory": "비DMX 액세서리",
        }
        breakdown = " · ".join(
            f"{labels.get(kind, kind)} {count}" for kind, count in counts.items()
        )
        return f"제외 {len(self.excluded_rows)}건({breakdown})"

    def _drop_ratio(self) -> float:
        rig = self.diff.designed_rig
        if rig.candidate_row_count <= 0:
            return 0.0
        return rig.dropped_row_count / rig.candidate_row_count

    def _append_read_failure_and_excluded_parts(self, parts: list[str]) -> None:
        """``판독 실패``/``제외`` 두 사건을 절대 뭉뚱그리지 않고 각각 명시한다(결함 2, P1).

        제외행이 있으면 판독 실패가 0건이어도 "판독 실패 0건 · 제외 M건(...)"을
        명시한다 — "이 파일은 판독 실패가 없는 깨끗한 파일"이라는 오해를 막는다.
        제외행이 없으면 기존과 동일하게 판독 실패가 있을 때만 표기한다.
        """
        if self.excluded_rows:
            parts.append(f"판독 실패 {len(self.read_failures)}건 · {self._excluded_breakdown_ko()}")
        elif self.read_failures:
            parts.append(f"판독 실패 {len(self.read_failures)}건")

    def summary_ko(self) -> str:
        if not self.comparison_performed():
            # 사유로 문장을 시작한다 — "차이 없음"이라는 표현은 여기서 절대
            # 등장하지 않는다(비협상). 미수행 판정·판독 실패 건수는 여전히
            # 뒤에 덧붙여 정보를 잃지 않는다.
            if self.diff.designed_rig.fixtures:
                # 멀티시스템 — 설계 측 산출은 정상이므로 픽스처 수를 먼저 밝힌다.
                parts = [
                    f"도면 픽스처 {len(self.diff.designed_rig.fixtures)}개",
                    self._multi_system_reason(),
                    "콘솔 대조를 수행하지 않았다",
                ]
                if self.diff.designed_rig.address_basis_note:
                    parts.append(self.diff.designed_rig.address_basis_note)
            else:
                parts = [self._no_fixtures_summary_lead(), "대조를 수행하지 않았다"]
            if self.diff.skipped_checks:
                names = " · ".join(
                    skipped_check_kind_label(entry.kind) for entry in self.diff.skipped_checks
                )
                parts.append(f"미수행 판정: {names}")
            self._append_read_failure_and_excluded_parts(parts)
            if self.diff.designed_rig.scope_qualified:
                parts.append(self.diff.designed_rig.scope_note)
            return ". ".join(parts) + "."

        diffs = self._diffs()
        rig = self.diff.designed_rig
        parts: list[str] = []
        lead_with_drop = rig.scope_qualified and self._drop_ratio() >= _LARGE_DROP_LEAD_THRESHOLD
        if lead_with_drop:
            # 결함 2(P1) — 큰 탈락 비율에서는 "도면 픽스처 N개"보다 탈락 사실이
            # 먼저 나와야 한다: 원본 대비 얼마나 못 읽었는지가 그 뒤에 나오는
            # 수량/충돌 판정보다 더 중요한 정보다.
            parts.append(rig.scope_note)
        parts.append(f"도면 픽스처 {len(rig.fixtures)}개")
        if rig.address_basis_note:
            # 결함 1(P0) 요건 c — 리그 등급이 역산이면 전제 문구를 숨기지 않는다.
            parts.append(rig.address_basis_note)
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
        self._append_read_failure_and_excluded_parts(parts)
        if rig.scope_qualified and not lead_with_drop:
            # 임계 미만이지만 여전히 0건은 아니다 — 정보를 숨기지 않는다,
            # 다만 문장 맨 앞을 차지할 정도는 아니므로 꼬리에 붙인다.
            parts.append(rig.scope_note)
        return ". ".join(parts) + "."

    def _diffs_payload(self) -> dict:
        """대조가 성립하지 않으면 빈 배열 3종 대신 ``performed: False``를 낸다.

        빈 배열(``missing_in_console: []`` 등)은 "찾아봤는데 없다"로 읽힌다
        — 대조 자체가 성립하지 않은 경우(:meth:`comparison_performed`가
        False) 이 세 키를 아예 생략하고 ``performed``/``reason``만 실어
        구조적으로 미수행임을 드러낸다. 정상 대조에서는 기존 3키 +
        ``performed: True``를 그대로 낸다 — 기존 호출자·테스트가 참조하는
        형태를 보존.
        """
        if not self.comparison_performed():
            return {"performed": False, "reason": self._diffs_not_performed_reason()}
        return {"performed": True, **self._diffs()}

    def to_dict(self) -> dict:
        designed = self.diff.designed_rig
        return {
            "designed_rig": {
                "fixture_count": len(designed.fixtures),
                "device_type_column_present": designed.device_type_column_present,
                "join_key_conflicts": self._join_key_conflicts(),
                "vw_patch_conflicts": self._vw_patch_conflicts(),
                "design_overlaps": self._design_overlaps(),
                "footprint_data_present": designed.footprint_data_present,
                "observed_systems": sorted(designed.observed_systems),
                "address_basis": designed.address_basis,
                "address_basis_note": designed.address_basis_note,
                "scope_qualified": designed.scope_qualified,
                "scope_note": designed.scope_note,
                "candidate_row_count": designed.candidate_row_count,
                "dropped_row_count": designed.dropped_row_count,
                "fixtures": self._fixtures(),
            },
            "console_rig": {
                # 재계산 없이 read_inventory/build_patch_sheet의 산출을 그대로
                # 참조한다(REQ-VWX-022) — Inventory.to_dict()가 그 산출이다.
                "inventory": self.diff.console_inventory.to_dict(),
            },
            "diffs": self._diffs_payload(),
            "skipped_checks": self._skipped_checks(),
            "read_failures": self._read_failures(),
            "excluded_rows": self._excluded_rows(),
            "summary_ko": self.summary_ko(),
        }


def build_vwx_report(
    diff: DiffResult,
    *,
    read_failures: tuple[_ShapedReadFailure, ...] = (),
    excluded_rows: tuple = (),
) -> VwxReport:
    """대조 결과 -> :class:`VwxReport`(REQ-VWX-023)."""
    return VwxReport(diff=diff, read_failures=read_failures, excluded_rows=excluded_rows)
