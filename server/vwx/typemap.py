from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Protocol

from server.vwx.rig import _norm_type, fuzzy_type_equal
from server.vwx.verdicts import (
    DESIGNED_FOOTPRINT_MATCHES_NO_MODE,
    DMX_MODE_NOT_IN_LIBRARY,
    FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED,
    FIXTURE_TYPE_LIBRARY_TRUNCATED,
    FIXTURE_TYPE_LIBRARY_UNREADABLE,
    FIXTURE_TYPE_NAME_UNUSABLE,
    FIXTURE_TYPE_NOT_IN_LIBRARY,
    FOOTPRINT_MATCH_DESCOPE,
    TYPE_FOOTPRINT_UNMATCHABLE,
    TYPE_LIBRARY_ABSENT,
    TYPE_LIBRARY_INCOMPLETE,
    TYPE_NAME_UNUSABLE,
    TYPE_NEEDS_CONFIRMATION,
    TYPE_RESOLVED,
    skipped_check_label,
    target_exclusion_label,
    type_resolution_status_label,
    validate_autopatch,
)

FIXTURE_TYPE_LIBRARY_ROOT = "Patch/FixtureTypes"
DMX_MODES_SEGMENT = "DMXModes"
DMX_CHANNELS_SEGMENT = "DMXChannels"
MODE_NAME_PROPERTY = "Name"

ASSUMPTION_72_GO = "go"
ASSUMPTION_72_NEGATIVE = "negative"
ASSUMPTION_72_INCONCLUSIVE = "inconclusive"
ASSUMPTION_72_VALUES = frozenset(
    {
        ASSUMPTION_72_GO,
        ASSUMPTION_72_NEGATIVE,
        ASSUMPTION_72_INCONCLUSIVE,
    }
)

ALIAS_CONFIRMATION_SOURCE = "type_alias"
FOOTPRINT_UNVERIFIED_COLUMN = "footprint_unverified"

#: [round21 R20-B] 목록 칸 → **그 목록의 완전성을 말하는 칸**. 이름을 상수로 두는 이유는
#: `FOOTPRINT_UNVERIFIED_COLUMN`과 같다: 짝의 전수를 소스에서 기계적으로 셀 수 있어야
#: 새 목록 칸이 완전성 칸 없이 들어오는 것을 게이트가 잡는다. round19가
#: `mode_options`(index·name·channel_count)를 더하면서 **그 자리를 만들지 않은 것**이
#: R20-B의 기제였다 — 절단된 부분 목록이 "고를 것 전부"로 제시되고, 목록이 비지 않으니
#: 호출자의 절단 가드도 지나가 고지가 0건이었다.
#:
#: `mode_candidates`와 `mode_options`가 **같은 완전성 칸**을 가리키는 것은 둘이 같은
#: 원소를 이름만 다르게 실은 것이기 때문이다(`row()` 참조). 칸을 둘로 나누면 같은
#: 목록에 두 완전성 진술이 생겨 서로 갈릴 수 있다.
TYPE_CANDIDATES_COMPLETENESS_COLUMN = "type_candidates_completeness"
MODE_OPTIONS_COMPLETENESS_COLUMN = "mode_options_completeness"
LIST_COMPLETENESS_COLUMNS = MappingProxyType(
    {
        "type_candidates": TYPE_CANDIDATES_COMPLETENESS_COLUMN,
        "mode_candidates": MODE_OPTIONS_COMPLETENESS_COLUMN,
        "mode_options": MODE_OPTIONS_COMPLETENESS_COLUMN,
    }
)

FOOTPRINT_DESCOPE_REASON = (
    "점유폭 일치 확인을 수행하지 않는다 — 모드의 DMXFootprint 프로퍼티는 responder 표면에서 "
    "table 포인터로만 돌아와 직렬화되지 않고, DMXChannels 자식 수는 점유폭이 아니다"
    "(M0 실측: 자식 수 14 vs 실제 주소 stride 16). 모드 선택은 사용자 확인 단독이며 "
    "'점유폭 미검증' 열이 그 축소를 건별로 표시한다. 근본 해결(responder의 DMXFootprint "
    "직렬화)은 console/lua 변경이라 본 SPEC의 PRESERVE이며 범위 밖이다."
)
#: [round21 R20-A ⓐ·ⓒ] "절단되어"만 적으면 계수만 어긋난 스냅샷에서 일어나지 않은 원인을
#: 단정한다. 관측 축이 아는 사실은 **선언 총계 중 일부를 못 봤다**는 것 하나이고, 부재를
#: 단정하지 않는 이유도 그것이다. 표적 스윕까지 실패한 이름만 부재를 말할 자격이 있다.
LIBRARY_TRUNCATED_REASON = (
    "FixtureType 열거에 미관측분이 남아 라이브러리 전수를 보지 못했다 — 대응 항목이 후보에 "
    "없음을 단정하지 않는다."
)
LIBRARY_UNREADABLE_REASON = (
    "FixtureType 열거를 읽지 못했다 — 대응 항목이 후보에 없음을 단정하지 않는다."
)
#: [round21 R20-D] 열거 응답의 **행 일부를 쓰지 못했다**. 절단(목록이 잘려 뒤가 안 옴)도
#: 판독 실패(응답을 못 받음)도 아니다 — 세 축은 조치가 다르므로 사유도 따로 적는다.
#: 어느 쪽 문장을 빌려 써도 payload가 관측 사실을 거짓으로 말한다(그 대조는 `verdicts`의
#: `FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED` 주석에 있다).
#:
#: [round23 R22-D] 문장이 **원인과 유보로만** 끝나 조작자가 할 일이 없었다. 배제 라벨과
#: 같은 조치를 문장에도 적는다 — 그 둘이 다른 말을 하면 조작자는 어느 쪽을 따를지 모른다.
#: 형제 두 축(절단·판독 실패)은 조치가 **재시도 계열**이라 사유 문장이 유보로 끝나도
#: 라벨의 조치와 충돌하지 않지만, 이 축은 재조회가 무의미하므로 문장 자체가 말해야 한다.
LIBRARY_ROWS_DISCARDED_REASON = (
    "FixtureType·DMXMode 열거 행 일부에 슬롯 번호가 없어 쓰지 못했다 — "
    "대응 항목이 후보에 없음을 단정하지 않는다. "
    "같은 범위를 재조회해도 같은 행이 오므로 도면 타입명을 콘솔 표기와 맞추거나 "
    "그 GDTF를 다시 임포트해 슬롯을 재확립해야 한다."
)
#: [round17 · 공허 일치 차단] 정규화 후 영숫자가 남지 않는 이름은 라이브러리 대조 기준이
#: 되지 못한다 — `_comparable_key` 참조. 그 이름으로 "일치"를 주장하면 라이브러리 전 항목이
#: 후보가 되고, 항목이 하나뿐인 라이브러리에서는 그것이 유일 후보가 되어 확정까지 간다.
#:
#: [round18 R18-E] round17은 이 갈래를 `needs_confirmation`으로 넘겼다 — **그것이 결함이었다.**
#: 이 갈래는 `type_candidates`가 **0건**이다. 확인할 후보를 하나도 제시하지 않은 상태를
#: "사용자 확인 대기"라 적으면 `hard_stops`가 비고 `confirmation_required`가 참이 되어,
#: 조작자는 화면에 없는 것을 고르려 기다린다. 그래서 하드 스톱으로 낸다.
#:
#: **탈출구는 실측으로 구분된다**(`_alias_for`의 `if not key: continue`):
#:   · 이름이 `None`·`''`(falsy)면 별칭 **키 자체가 없어** 어떤 입력으로도 해결 불가 —
#:     진짜 막다른 길이다. 고칠 곳은 도면뿐이다.
#:   · 이름이 `'---'`·`'   '`처럼 truthy면 그 이름을 키로 한 별칭에 **실재 콘솔 이름**을
#:     저장해 두면 `alias_type`이 대조 기준이 되어 `resolved`까지 간다(실측). 그래서 이
#:     하드 스톱은 그 탈출구를 막지 않는다 — 별칭이 있으면 이 갈래에 오지 않는다.
#: 두 경우 모두 사유는 **도면 이름을 고쳐라**를 말한다: 공허한 이름은 별칭을 걸어도
#: 도면 쪽 식별이 사람에게 읽히지 않는다.
VACUOUS_TYPE_KEY_REASON = (
    "타입 이름에 영숫자가 하나도 없어 라이브러리 대조 기준이 되지 못한다 — 공허한 일치로 "
    "후보를 세지 않으므로 제시할 후보가 0건이다. 확인할 것이 없는 상태는 확인 대기가 아니라 "
    "하드 스톱이다 — 도면의 타입 이름을 고쳐야 한다. 이름이 아예 비어 있으면 별칭 등록조차 "
    "키가 없어 불가능하다. 조회에 쓰려던 이름은 구조화 칸에 그대로 남긴다."
)

#: [round19 major#5] 판정 사유는 **모듈 상수**여야 한다 — 갈래마다 사유가 리터럴로 박히면
#: "확인 대기를 말하는 갈래 전수"를 소스에서 기계적으로 셀 수 없고, 그 전수가 없으면
#: 새 갈래가 게이트를 조용히 빠져나간다(R18-E가 그 형태였다). `_resolve_one`의 모든
#: `TypeResolution(...)`은 `reason=<이 구역의 상수>`만 쓴다 — 구조 게이트가 강제한다.
TYPE_ABSENT_REASON = (
    "콘솔 라이브러리에 도면 타입에 대응하는 FixtureType이 없다. "
    "콘솔에서 GDTF 라이브러리 임포트를 먼저 수행해야 이 항목을 "
    "패치할 수 있다 — 유사한 이름으로 대체 배정하지 않는다."
)
MODE_ABSENT_REASON = (
    "콘솔에서 확인된 FixtureType에, 도면이 요구한 DMXMode에 대응하는 모드가 없다. "
    "해당 모드를 담은 GDTF 라이브러리 임포트가 선행되어야 한다 — "
    "유사한 이름의 다른 모드로 대체 배정하지 않는다."
)
ALIAS_RESOLVED_REASON = (
    "저장된 별칭으로 타입·모드를 확정했다 — 첫 확정은 사람이 했고 그 재사용을 표에 남긴다."
)
CANDIDATES_PRESENTED_REASON = "라이브러리 후보를 제시했다 — 사용자 확인 없이 확정하지 않는다."

#: [round19 major#5] 점유폭 불일치 — **고를 수 있는 모드가 라이브러리에 있다.**
#: 이전 판은 이 갈래 하나로 세 상태를 뭉갰고, `mode_candidates`에는 별칭으로 좁혀진
#: **실패한 그 모드 하나**만 실려 있었다. "모드를 다시 확인하라"고 말하면서 고를 것을
#: 보여주지 않은 것이다. 이제 라이브러리의 전 모드를 채널 수와 함께 싣는다.
FOOTPRINT_MISMATCH_CHOOSABLE_REASON = (
    "콘솔 DMXChannels 자식 수가 도면 DMX Footprint와 다르다 — 승인 전에 모드를 다시 "
    "확인해야 한다. 도면 점유폭과 채널 수가 맞는 모드가 이 FixtureType에 있으니 "
    "제시된 모드 목록에서 고르면 된다. 셀 수가 다른 모드를 고르면 주소 계획 전체가 어긋난다."
)
#: [round19 major#5] 점유폭 불일치 — **어느 모드도 맞지 않는다(전 모드 실측).**
#: 모드 선택으로는 벗어날 수 없으므로 확인 대기가 아니라 하드 스톱이고, 사유는
#: 실제 조치를 가리킨다: 고칠 것은 콘솔 라이브러리가 아니라 **도면의 점유폭 값**이다.
FOOTPRINT_UNMATCHABLE_REASON = (
    "콘솔 DMXChannels 자식 수가 도면 DMX Footprint와 다르고, 이 FixtureType의 "
    "어느 모드도 도면 점유폭과 채널 수가 맞지 않는다 — 모드 열거를 전부 읽었고 절단도 "
    "없었다. 모드를 다시 고르는 것으로는 벗어날 수 없다: 고칠 것은 도면의 DMX Footprint "
    "값이다. 라이브러리가 실제로 제공하는 모드와 그 채널 수는 제시된 모드 목록에 그대로 있다."
)
#: [round19 major#5] 점유폭 불일치 — **맞는 모드의 부재를 단정할 수 없다.**
#: 이 상태를 하드 스톱으로 적으면 찾아보지도 않은 것을 부재로 단정하는 것이 된다
#: (`fixture_type_not_in_library`를 공허 이름 갈래에 쓰지 않는 것과 같은 규율).
#:
#: [round21 R20-D] 문장이 **절단·판독 실패 둘만** 열거하고 있었다. `_absence_assertable`의
#: 전제는 셋이므로(미관측 · **폐기** · 채널 수 미판독) 폐기로 여기 온 갈래에서 이 문장은
#: 거짓이 된다 — R20-D가 고발한 것이 정확히 "사유가 관측 사실을 거짓으로 말한다"였다.
#: 어느 축이 발화했는지는 `skipped_checks`의 kind가 특정한다.
FOOTPRINT_MISMATCH_UNVERIFIED_REASON = (
    "콘솔 DMXChannels 자식 수가 도면 DMX Footprint와 다르다 — 승인 전에 모드를 다시 "
    "확인해야 한다. 맞는 모드가 있는지는 단정하지 않는다: 이 FixtureType의 모드 목록을 "
    "전수로 보지 못했다(열거에 미관측분이 남았거나, 슬롯 번호가 없어 쓰지 못한 행이 "
    "있거나, 채널 수를 읽지 못한 모드가 있다). 관측된 모드와 채널 수는 제시된 모드 "
    "목록에 그대로 있다."
)

TYPE_TABLE_COLUMNS = (
    "candidate_id",
    "designed_type",
    "console_type",
    "console_mode",
    "status",
    "confirmation_source",
    "designed_footprint",
    "console_channel_count",
    FOOTPRINT_UNVERIFIED_COLUMN,
    # [round21 R20-B] 목록 완전성은 **표에 등재된 칸**이다. `row()`에만 있고 표에 없으면
    # 조작자 화면 렌더러가 그 칸을 그리지 않아, payload에는 있는데 사람은 못 보는
    # 상태가 된다 — 그것도 침묵이다.
    TYPE_CANDIDATES_COMPLETENESS_COLUMN,
    MODE_OPTIONS_COMPLETENESS_COLUMN,
)
TYPE_TABLE_COLUMN_LABELS = MappingProxyType(
    {
        "candidate_id": "후보 식별자",
        "designed_type": "도면 타입",
        "console_type": "콘솔 FixtureType",
        "console_mode": "콘솔 DMXMode",
        "status": "판정",
        "confirmation_source": "확인 출처",
        "designed_footprint": "도면 점유폭",
        "console_channel_count": "콘솔 DMXChannels 자식 수",
        FOOTPRINT_UNVERIFIED_COLUMN: "점유폭 미검증",
        TYPE_CANDIDATES_COMPLETENESS_COLUMN: "타입 후보 목록 완전성",
        MODE_OPTIONS_COMPLETENESS_COLUMN: "모드 목록 완전성",
    }
)


class LibraryPort(Protocol):
    def query_state(self, path: str) -> Mapping[str, object]: ...

    def query_property(self, path: str, property_name: str) -> Mapping[str, object]: ...


@dataclass(frozen=True)
class LibraryMode:
    index: int
    name: str
    channel_count: int | None = None


@dataclass(frozen=True)
class LibraryType:
    index: int
    name: str
    modes: tuple[LibraryMode, ...] = ()
    modes_available: bool = True
    modes_truncated: bool = False
    #: [round21 R20-A ⓐ] DMXModes 스냅샷이 **선언한** 총계(`node.childCount`). 절단된
    #: payload에도 이 값은 참값으로 들어 있다(형제 리더 `server/prechk/inventory.py`
    #: 독스트링 2번 · `console/lua/copilot_responder.lua:607` — 예산 루프는 항목 목록만
    #: 깎고 총계는 깎지 않는다). 읽지 못했으면 `None` — "0을 선언했다"와 다르다.
    mode_child_count: int | None = None
    #: **열거**가 근거인 모드 수. 스윕이 찾은 것을 여기 섞지 않는다(`patchplan`의
    #: `enumerated_count`와 같은 규율 — 섞으면 "열거했다"는 문장이 스윕 결과를 말한다).
    modes_enumerated_count: int = 0
    #: payload가 **실어 온** 행 수. 절단 축의 분모다 — 폐기 축(`i` 없는 행)은
    #: 여기 세어지고 `modes_enumerated_count`에서만 빠지므로 둘이 상보가 된다.
    #: `patchplan`에 대응 이름이 없어 새로 짓는다: 그쪽은 이 값을 지역 변수로만 쓰고
    #: 노출하지 않는데, 여기서는 두 축의 분리를 payload가 증명해야 한다.
    returned_mode_row_count: int = 0
    #: [round21 R20-A ⓑ] 이 타입은 **표적 스윕**이 회수했다 — 열거가 아니다.
    #: 회수 사실은 detail이지 완전성 근거가 아니다(`recover_requested_types` 독스트링).
    recovered: bool = False
    #: [round21 R20-D] **폐기** 행 수 — 슬롯 번호(`i`)가 없거나 중복이라 쓰지 못한 행.
    #: 이름은 형제 `patchplan.ExistingFidRead.to_dict()`의 `unusable_row_count`를 그대로
    #: 쓴다. 구판은 이 행을 `continue`로 버리면서 **세지 않았고**, 그래서 "슬롯이
    #: 확립되지 않았다"가 "라이브러리에 없다"로 바뀌어 나갔다(round20 R20-D).
    unusable_mode_row_count: int = 0
    #: 매핑이 아니라 슬롯 번호조차 물어볼 수 없던 행 수 — `unparsable_row_count` 형제.
    unparsable_mode_row_count: int = 0

    @property
    def observed_mode_count(self) -> int:
        return len(self.modes)

    @property
    def modes_unseen(self) -> int | None:
        """선언 총계 중 **끝내 보지 못한** 모드 수. 총계를 모르면 `None`.

        [round23 R22-B] 열거가 총계를 넘었으면 이 수도 `None`이다 — 루트 축
        (`FixtureTypeLibrary.unseen`)과 **같은 규율**이다. 두 축이 갈리면 같은 콘솔의
        루트와 모드가 서로 다른 정직함을 갖는다.
        """
        if self.mode_child_count is None or self.modes_over_enumerated:
            return None
        return max(self.mode_child_count - len(self.modes), 0)

    @property
    def modes_enumeration_short(self) -> bool:
        """열거가 **선언보다 짧았다** — 계수 대조다(`truncated` 플래그가 아니다)."""
        if self.mode_child_count is None:
            return False
        return self.mode_child_count > self.returned_mode_row_count

    #: [round23 R22-B] 루트 축 `FixtureTypeLibrary.over_enumerated`의 **형제**다. 두 축의
    #: 계수 대조는 같은 산식이어야 한다 — 한쪽만 양방향으로 고치면 선언 4모드에 5행이
    #: 온 스냅샷이 여전히 `complete=True`로 나가고, 다음 라운드가 나머지 절반을 잡는다.
    #: 이 SPEC이 반복해서 만든 형태가 정확히 그 "형제 절반만 고침"이다.
    @property
    def modes_over_enumerated(self) -> bool:
        """모드 열거가 **선언 총계를 넘었다** — 이 스냅샷은 자기모순이다."""
        if self.mode_child_count is None:
            return False
        return (
            self.modes_enumerated_count > self.mode_child_count
            or len(self.modes) > self.mode_child_count
        )

    @property
    def modes_incomplete(self) -> bool:
        """모드 목록을 전수로 보지 못했다 — **플래그와 계수 대조의 논리합**.

        둘을 병존시키는 이유는 실측이다: 예산 절단은 플래그를 세우고 목록을 깎지만,
        플래그 없이 계수만 어긋난 스냅샷도 산출 가능하고(행이 조용히 빠진 경우) 그때
        플래그 단독 판정은 부분 목록을 전수라고 부른다. 어느 한쪽만 참이어도 불완전이다.
        """
        # [round21 R20-D] 폐기 축을 **논리합에 더한다**. union은 "이 목록을 완전하다고
        # 말할 수 있는가" 하나의 질문이고, 축별 계수는 payload에서 따로 유지된다 —
        # 그래야 조작자가 조치(표적 스윕 · 재시도 · responder 확인)를 고를 수 있다.
        # [round23 R22-B] 계수 대조를 양방향으로 — 루트 축과 같은 갈래 구성이다.
        return (
            self.modes_truncated
            or self.modes_enumeration_short
            or self.modes_over_enumerated
            or self.mode_rows_discarded > 0
        )

    @property
    def mode_rows_discarded(self) -> int:
        """**폐기 축** 합계 — 절단(`modes_unseen`)·판독 실패와 한 칸에 뭉개지 않는다."""
        return self.unusable_mode_row_count + self.unparsable_mode_row_count


#: [round23 R22-F] 회수 스윕의 **비용 근거가 유효한 범위**를 나타내는 왕복 수.
#:
#: `recover_requested_types` 독스트링은 전수 스윕을 **비용을 재서 기각**했다: 200종
#: 라이브러리(U=176 · m=20)에서 전수는 negative ``176 × 22 = 3,872`` 왕복이고, 실측
#: 단가 66.25 ms/왕복이면 약 4분이라 세션이 멈춘다. 이 상수는 **그 기각선 그 자체**다 —
#: 새로 지어낸 수가 아니라 이미 기각 근거로 쓰인 수를 이름 붙여 꺼낸 것이다.
#:
#: 채택된 표적 스윕의 비용은 ``U + k·(1 + c·m)``이라 전수보다 **차수가 낮을 뿐 유계가
#: 아니다**: `child_count`는 콘솔이 선언한 총계이고 `_optional_int`만 통과하므로, U가
#: 커지면 채택 설계도 같은 기각선을 넘는다. 그때 "전수는 비싸서 안 한다"는 문장은
#: **이 설계에 대해서도 참**이 되므로, 근거가 유효 범위를 벗어났다는 사실을 payload가
#: 말해야 한다(`FixtureTypeLibrary.recovery_cost_basis_exceeded`).
#:
#: **상한이 아니다 — 스윕을 거부하지 않는다.** 거부하면 느리지만 옳은 답이 임의의
#: 수치 때문에 `fixture_type_not_in_library` 배제로 바뀌어, 이 스윕이 없애려던 바로 그
#: 거짓 부재가 돌아온다. 그리고 `child_count`에 상한을 둘 **근거가 없다**: 하드 캡은
#: 반환 행 수(`max_children=24`)에 걸린 것이지 선언 총계에 걸린 것이 아니고, 형제
#: PRESERVE `server/prechk/inventory.py`의 회수 스윕도 `1..child_count`를 상한 없이
#: 훑는다. 근거 없는 상한을 짓지 않는 판단은 round18이 FID 상한에서 이미 내렸다.
RECOVERY_COST_EVIDENCE_ROUNDTRIPS = 3_872


@dataclass(frozen=True)
class FixtureTypeLibrary:
    types: tuple[LibraryType, ...] = ()
    available: bool = True
    truncated: bool = False
    #: [round21 R20-A ⓐ] 루트 스냅샷이 **선언한** 타입 총계(`node.childCount`).
    #: 이름은 `patchplan.ExistingFidRead.child_count`·`prechk.Inventory.child_count`와
    #: 같은 것을 쓴다 — 같은 개념을 두 층이 다르게 부르면 그 자체가 형제 불일치다.
    child_count: int | None = None
    #: **열거**가 근거인 타입 수(스윕 이전에 못박는다).
    enumerated_count: int = 0
    #: payload가 실어 온 행 수 — 절단 축의 분모. `LibraryType.returned_mode_row_count` 참조.
    returned_row_count: int = 0
    #: 표적 스윕이 회수한 타입 수. `patchplan`의 같은 이름과 같은 뜻이고, **완전성 근거가
    #: 아니다** — 스윕은 관측을 늘릴 뿐 판정을 승격하지 않는다.
    recovered_count: int = 0
    #: 스윕 상한(= `child_count`). 스윕하지 않았으면 `None` — "0까지 훑었다"와 다르다.
    recovery_boundary: int | None = None
    #: 스윕 프로브가 **결말을 내지 못한** 건수(응답은 `ok=true`인데 이름을 얻지 못했다).
    #: `ok=false`는 여기 세지 않는다: 유계 프로브 범위 안의 빈 인덱스는 희소 풀의
    #: **정보**이지 결함이 아니다(`prechk.inventory._probe_slot` 독스트링).
    probe_failures: int = 0
    #: [round21 R20-D] 폐기 축 — `LibraryType.unusable_mode_row_count` 형제이고
    #: `patchplan.ExistingFidRead`의 같은 이름과 같은 뜻이다. 절단과 **다른 축**이다:
    #: 목록이 잘린 것이 아니라 온 행을 못 쓴 것이라, 같은 범위를 다시 읽어도 같다.
    unusable_row_count: int = 0
    unparsable_row_count: int = 0
    #: [round23 R22-F] 스윕이 실제로 던진 **이름 프로브 왕복 수**. 파생값으로 다시 세지
    #: 않고 기록한다 — `recovery_boundary - enumerated_count`로 되계산하면 루프에 가드가
    #: 하나 붙는 순간 payload가 조용히 거짓말을 한다.
    recovery_probe_count: int = 0

    @property
    def observed_type_count(self) -> int:
        return len(self.types)

    @property
    def unseen(self) -> int | None:
        """선언 총계 중 **끝내 보지 못한** 타입 수. 총계를 모르면 `None`.

        `patchplan._existing_fids_from_console`과 같은 산식이다: 회수분을 포함한
        **관측 전체**를 총계에서 뺀다. 그래서 스윕이 하나를 찾으면 이 수는 하나 줄지만,
        `enumeration_short`는 그대로 참으로 남아 완전성 판정은 올라가지 않는다.

        [round23 R22-B] 열거가 **총계를 넘었으면** 이 수는 `None`이다. `max(..., 0)`은
        음의 차이를 0으로 지우는데, 그 0은 "못 본 것이 없다"라는 **긍정 주장**으로 읽힌다
        — 자기모순 스냅샷에서 그 주장을 할 근거는 없다. 총계를 못 읽은 것과 총계를 믿을
        수 없는 것은 조작자에게 같은 상태다: **모른다**. 형제
        `patchplan.ExistingFidRead`는 그 자리에 `over_enumerated` boolean을 따로 실어
        `unseen=0`이 무해하게 읽히는 것을 막는다 — 여기서는 그 boolean도 싣고 이 수도
        비운다(같은 dict가 두 말을 하지 않게).
        """
        if self.child_count is None or self.over_enumerated:
            return None
        return max(self.child_count - len(self.types), 0)

    @property
    def enumeration_short(self) -> bool:
        """열거가 **선언보다 짧았다** — 계수 대조. 스윕은 이 값을 내리지 못한다."""
        if self.child_count is None:
            return False
        return self.child_count > self.returned_row_count

    #: [round23 R22-B] 계수 대조의 **반대 방향**. round21은 형제
    #: `patchplan.ExistingFidRead`에서 여덟 칸을 이름까지 그대로 가져오면서 이 축만
    #: 빠뜨렸고, 그 클래스의 주석은 *"관측이 총계와 어느 방향으로든 어긋나면 완전하다고
    #: 말할 수 없다"*고 적는다. 한 방향만 보면 **선언 2에 3행**이 온 스냅샷과 **음의
    #: 선언 총계**가 `enumeration_short=False` · `unseen=max(...,0)=0`을 지나
    #: `complete=True`라는 **긍정 주장**으로 나가고, 그 위에서 부재까지 단정된다.
    @property
    def over_enumerated(self) -> bool:
        """열거가 **선언 총계를 넘었다** — 이 스냅샷은 자기모순이다.

        형제(`patchplan._existing_fids_from_console`)와 **같은 분모**로 잰다: 쓸 수
        있었던 슬롯 수다. 실어 온 행 수(`returned_row_count`)로 재면 중복·무효 행이
        섞인 정상 스냅샷을 자기모순이라 부른다 — 그 행들은 이미 폐기 축이 세고 있고,
        상보식(`returned == enumerated + unusable + unparsable`)이 그것을 보장한다.

        관측 수(`len(types)`)도 함께 보는 이유는 표적 스윕이다: 회수분은
        `enumerated_count`에 섞이지 않으므로 그쪽 계수만으로는 넘침을 놓친다.

        음의 선언 총계는 관측이 0건이어도 이 비교에 걸린다 — 슬롯 수는 음수가 못 된다.
        """
        if self.child_count is None:
            return False
        return self.enumerated_count > self.child_count or len(self.types) > self.child_count

    #: [round23 R22-B] **두 표면이 같은 근거를 보게 한다.** `recover_requested_types`의
    #: 스윕 도메인 가드가 이 식을 인라인으로 들고 있었다 — 같은 판정을 두 자리가 따로
    #: 적으면 한쪽만 고쳐지고 그 갈림이 다음 라운드의 결함이 된다. 가드는 이제 이
    #: 프로퍼티를 부르고, payload도 같은 값을 싣는다.
    @property
    def index_domain_violated(self) -> bool:
        """열거된 슬롯 번호가 선언 경계 `1..child_count` 밖이다.

        **이것은 완전성 축이 아니다** — `enumeration_incomplete`에 넣지 않는다. 콘솔의
        슬롯 풀은 희소할 수 있어서(`prechk.inventory._probe_slot` 독스트링) 총계 1에
        3번 슬롯 하나가 오는 스냅샷은 정상이고, 그 목록은 실제로 전수다. 형제
        `patchplan.ExistingFidRead`도 인덱스 도메인을 `complete`에 넣지 않고 스윕
        전제로만 쓴다 — 여기서 넣으면 두 리더가 같은 콘솔을 다르게 읽는다.

        스윕이 이 조건에서 훑기를 거부하는 이유는 다르다: 스윕은 `1..child_count`를
        **위치로** 훑으므로 열거 인덱스가 그 범위 밖이면 도메인 자체가 어긋난 것이다.

        그래도 두 표면은 어긋나지 않는다. 이 가드가 **판정을 좌우하는 자리**까지
        오려면 앞선 가드(`enumerated_count >= child_count`)를 통과해야 하고, 그때는
        열거가 선언보다 짧거나 폐기 행이 있다는 뜻이라 완전성 진술이 이미 `True`가
        아니다. 그 일치를 round23 절이 대조군으로 고정한다.
        """
        if self.child_count is None:
            return False
        return not all(1 <= entry.index <= self.child_count for entry in self.types)

    @property
    def enumeration_incomplete(self) -> bool:
        """라이브러리를 전수로 보지 못했다 — **플래그와 계수 대조의 논리합**.

        `LibraryType.modes_incomplete`와 같은 이유로 둘을 병존시킨다. 이전 판은
        `truncated` 플래그 단독으로 판정했고, 그것이 PRESERVE
        `server/prechk/inventory.py` 독스트링 2번이 금지한 바로 그 형태다.
        """
        # [round21 R20-D] 폐기 축을 논리합에 더한다 — `LibraryType.modes_incomplete` 참조.
        # [round23 R22-B] 계수 대조를 **양방향**으로 본다. 초과 열거는 "못 본 것이 있다"가
        # 아니라 "이 스냅샷을 믿을 수 없다"이지만, 이 칸이 답하는 질문은 하나다 —
        # **이 목록을 전수라고 말할 수 있는가**. 말할 수 없다.
        return (
            self.truncated
            or self.enumeration_short
            or self.over_enumerated
            or self.rows_discarded > 0
        )

    @property
    def rows_discarded(self) -> int:
        """루트 열거의 **폐기 축** 합계. 모드 행 폐기는 각 `LibraryType`이 들고 있다."""
        return self.unusable_row_count + self.unparsable_row_count

    @property
    def recovery_cost_basis_exceeded(self) -> bool | None:
        """이 스윕이 **자기 설계 근거의 유효 범위를 벗어났는가**. 안 훑었으면 `None`.

        `recover_requested_types`는 전수 스윕을 ``3,872`` 왕복(≈4분)이라는 실측 비용으로
        기각했다. 채택된 표적 스윕은 차수가 낮을 뿐 **유계가 아니다** — `child_count`가
        크면 이름 프로브만으로 같은 왕복 수에 도달하고, 그 순간 기각 문장은 이 설계에도
        그대로 적용된다. 그것을 조작자에게 말하지 않으면 payload는 "비용을 재서 골랐다"는
        근거를 **범위 밖에서도 유효한 것처럼** 들고 있는 셈이다.

        이 칸은 **거부가 아니라 고지**다: 참이어도 회수분은 그대로 실려 나간다.
        """
        if self.recovery_boundary is None:
            return None
        return self.recovery_probe_count >= RECOVERY_COST_EVIDENCE_ROUNDTRIPS

    def to_dict(self) -> dict[str, object]:
        return {
            "path": FIXTURE_TYPE_LIBRARY_ROOT,
            "available": self.available,
            "truncated": self.truncated,
            # [round21 R20-A ⓐ] `type_count`·`mode_count`의 뜻은 **바꾸지 않았다**
            # (= 본 수). 소비자를 조용히 깨뜨리는 대신 **칸을 늘렸다** — 선언 총계와
            # 미관측 수가 옆에 서야 "본 수 = 총계"라는 오독이 성립하지 않는다.
            "type_count": len(self.types),
            "child_count": self.child_count,
            "enumerated_count": self.enumerated_count,
            "returned_row_count": self.returned_row_count,
            "unseen_count": self.unseen,
            "recovered_count": self.recovered_count,
            "recovery_boundary": self.recovery_boundary,
            "probe_failure_count": self.probe_failures,
            # [round23 R22-F] 비용 근거의 **유효 범위**를 payload가 직접 말한다. 왕복
            # 수를 싣지 않으면 고지가 참인 이유를 조작자가 확인할 수 없다.
            "recovery_probe_count": self.recovery_probe_count,
            "recovery_cost_basis_exceeded": self.recovery_cost_basis_exceeded,
            "enumeration_short": self.enumeration_short,
            "enumeration_incomplete": self.enumeration_incomplete,
            # [round23 R22-B] 반대 방향 축 둘. `enumeration_short`만 실으면 조작자는
            # 계수 대조가 **한 방향만** 본다는 사실을 payload에서 읽을 수 없고,
            # `enumeration_incomplete`만 실으면 어느 축이 발화했는지 알 수 없다.
            "over_enumerated": self.over_enumerated,
            "index_domain_violated": self.index_domain_violated,
            # [round21 R20-D] 절단(`unseen_count`)과 **다른 축**이다. 한 칸으로 합치지
            # 않는다 — 조치가 다르면 어휘도 달라야 한다.
            "unusable_row_count": self.unusable_row_count,
            "unparsable_row_count": self.unparsable_row_count,
            "rows_discarded_count": self.rows_discarded,
            "types": [
                {
                    "index": entry.index,
                    "name": entry.name,
                    "mode_count": len(entry.modes),
                    "modes_available": entry.modes_available,
                    "modes_truncated": entry.modes_truncated,
                    "mode_child_count": entry.mode_child_count,
                    "modes_enumerated_count": entry.modes_enumerated_count,
                    "returned_mode_row_count": entry.returned_mode_row_count,
                    "mode_unseen_count": entry.modes_unseen,
                    "modes_enumeration_short": entry.modes_enumeration_short,
                    # [round23 R22-B] 루트 축과 같은 반대 방향 칸 — 형제 절반만 싣지 않는다.
                    "modes_over_enumerated": entry.modes_over_enumerated,
                    "modes_incomplete": entry.modes_incomplete,
                    "recovered": entry.recovered,
                    "unusable_mode_row_count": entry.unusable_mode_row_count,
                    "unparsable_mode_row_count": entry.unparsable_mode_row_count,
                    "mode_rows_discarded_count": entry.mode_rows_discarded,
                }
                for entry in self.types
            ],
        }


@dataclass(frozen=True)
class ListCompleteness:
    """제시된 목록 **하나**가 선언된 전부인지 말하는 자리.

    [round21 R20-B] round19는 `mode_options`(index·name·channel_count)를 더하면서
    **그 목록의 완전성을 말할 자리를 만들지 않았다.** 그래서 절단된 부분 목록이
    "고를 것 전부"로 제시되고, 목록이 비지 않으니 호출자의 절단 가드도 지나가
    `incompleteness_kind`가 서지 않았고 `skipped_checks`가 **0건**이었다. round19 자신의
    기준(*"고를 수 있는 것을 보여주는 것이 확인 대기의 전제"*)이 그 새 필드에서 깨졌다.

    `complete`는 **삼치**다. 이치로 두면 "근거 없음"이 "완전"으로 읽힌다 — 이 SPEC이
    반복해서 뭉갠 것이 정확히 *"모른다"*와 *"없다"*의 구별이다:
      · `True`  — 선언 총계와 대조해 전수를 봤다. **긍정 주장**이다.
      · `False` — 못 본 것이 있다(축은 `incompleteness_kind`가 말한다).
      · `None`  — 완전성을 말할 **근거 자체가 없다**(선언 총계를 못 읽었거나 열거를
                  거치지 않은 해상 결과). 표시 없음과 완전은 다르다.

    **계수는 여기서 세지 않는다.** `FixtureTypeLibrary`·`LibraryType`이 이미
    `child_count`·`enumerated_count`·`unseen`을 들고 있고(round21 R20-A), 같은 개념을 두
    자리에서 세면 그 자체가 다음 라운드의 형제 불일치다. 이 칸은 그것을 **옮긴다**.

    `presented_count`를 `observed_count`와 따로 두는 이유: 목록은 요청 이름으로 **좁혀질**
    수 있어서(`_mode_candidates`·`_type_candidates`) 행에 실린 수가 관측 수보다 작을 수
    있고, 그 차이는 절단이 아니다. `declared − observed`만이 미관측이다.
    """

    complete: bool | None
    incompleteness_kind: str | None = None
    declared_count: int | None = None
    observed_count: int | None = None
    presented_count: int = 0
    unseen_count: int | None = None

    def presenting(self, count: int) -> ListCompleteness:
        """이 진술을 **이 행이 실은 원소 수**와 함께 쓴다 — 진술 자체는 행마다 같다."""
        return replace(self, presented_count=count)

    def to_dict(self) -> dict[str, object]:
        return {
            "complete": self.complete,
            "incompleteness_kind": self.incompleteness_kind,
            # 축 라벨은 `skipped_checks` 고지와 **같은 어휘·같은 라벨**에서 온다 —
            # 목록 옆 표시와 고지가 다른 말을 쓰면 조작자가 둘을 묶지 못한다.
            "label": (
                None
                if self.incompleteness_kind is None
                else skipped_check_label(self.incompleteness_kind)
            ),
            "declared_count": self.declared_count,
            "observed_count": self.observed_count,
            "presented_count": self.presented_count,
            "unseen_count": self.unseen_count,
        }


def _library_list_completeness(library: FixtureTypeLibrary) -> ListCompleteness:
    """`type_candidates`가 실린 목록의 완전성 — **라이브러리 열거**가 근거다.

    축 판정은 `_library_axis` 하나에서만 난다(고지와 같은 자리). `complete=True`는
    축이 비었다는 것만으로 내지 않는다: 선언 총계(`child_count`)를 못 읽었으면 대조할
    기준이 없으므로 `None`이다 — 플래그 단독으로 전수를 주장하지 않는다는 규율
    (PRESERVE `server/prechk/inventory.py` 독스트링 2번)이 완전성 **주장** 쪽에도 걸린다.
    """
    axis = _library_axis(library)
    return ListCompleteness(
        complete=False if axis is not None else (None if library.child_count is None else True),
        incompleteness_kind=axis,
        declared_count=library.child_count,
        observed_count=len(library.types),
        unseen_count=library.unseen,
    )


def _mode_list_completeness(console_type: LibraryType | None) -> ListCompleteness:
    """`mode_candidates`·`mode_options`가 실린 목록의 완전성 — 그 타입의 **모드 열거**가 근거다.

    `console_type`이 `None`이면 열거를 거치지 않았다 — 목록도 비어 있다(그 상관관계는
    게이트가 잰다). 그 상태를 `complete=False`로 적으면 "못 본 모드가 있다"는 거짓
    진술이 되고, `True`로 적으면 근거 없는 전수 주장이 된다. 그래서 `None`이다.
    """
    if console_type is None:
        return ListCompleteness(complete=None)
    axis = _mode_axis(console_type)
    return ListCompleteness(
        complete=(
            False if axis is not None else (None if console_type.mode_child_count is None else True)
        ),
        incompleteness_kind=axis,
        declared_count=console_type.mode_child_count,
        observed_count=len(console_type.modes),
        unseen_count=console_type.modes_unseen,
    )


def _confirmable_from(listing: ListCompleteness) -> bool:
    """이 목록에서 **`len(...) == 1`을 확정의 근거로 삼아도 되는가.**

    [round23 R22-E] round21은 `row()`가 완전성 진술을 **필수**로 받게 만들었지만 그
    값을 읽는 처분을 만들지 않았다 — 처방의 절반이었다. 그래서 한 행이 `resolved`와
    `complete:false`를 동시에 말했고, `declared 4 / observed 1 / unseen 3` 옆에서
    `hard_stops=[]`가 나갔다. `len(...) == 1`이 *"이 이름에 맞는 것은 이것뿐"*을 뜻하려면
    그 목록이 전수여야 한다 — 아니면 두 번째 일치가 미관측 구간에 있어도 유일 후보로
    읽힌다(`fuzzy_type_equal`도 모드 대조도 **포함관계**라 흔하다: `Mode 1` ⊂ `Mode 10`).

    술어가 삼치를 **`is True`로** 받는 것이 요점이다. `complete`는 삼치이고
    (`ListCompleteness` 독스트링), `None`은 "완전성을 말할 근거 자체가 없다"이지
    "완전하다"가 아니다. `is not False`로 쓰면 근거 없음이 완전으로 읽히는데, 그것이
    이 SPEC이 반복해 뭉갠 *"모른다"*와 *"없다"*의 혼동이다.

    `bool(listing.complete)`는 이 삼치 위에서 **행동이 같다**(`bool(None)`이 거짓이다)
    — round23 뮤테이션 실측에서 등가로 확인됐다. 그래도 `is True`로 적는 이유는
    `complete`가 언젠가 삼치를 넘어설 때 truthiness가 조용히 갈리기 때문이다: 이 자리는
    "참인가"가 아니라 **"전수라고 주장했는가"**를 묻는다.
    """
    return listing.complete is True


def _confirmable_lists(library: FixtureTypeLibrary, presented_type: LibraryType | None) -> bool:
    """확정에 쓰인 **두 목록이 모두 전수인가** — 타입 축과 모드 축은 같은 규칙이다.

    [round23 R22-E] 한 축만 닫으면 나머지가 남는다: R22-C 실증에서 타입 축이,
    R22-E 실증에서 모드 축이 각각 `resolved`와 `complete:false`를 공존시켰다.

    근거는 **행에 실리는 그 진술 그대로**다 — `row()`의 두 완전성 칸은
    `_library_list_completeness`(계획 자리에서 한 번)와 `mode_options_completeness`
    (= `_mode_list_completeness(presented_type)`)에서 오고, 여기서도 같은 함수를 같은
    인자로 부른다. 두 자리가 다른 식을 쓰면 표시와 처분이 갈릴 수 있고, 그 갈림이
    바로 이번 라운드가 고발당한 형태다.
    """
    return _confirmable_from(_library_list_completeness(library)) and _confirmable_from(
        _mode_list_completeness(presented_type)
    )


@dataclass(frozen=True)
class TypeRequest:
    candidate_id: str
    instrument_type: str
    gdtf_fixture: str | None = None
    mode: str | None = None
    footprint: int | None = None
    cell_count: int | None = None

    @property
    def designed_type(self) -> str:
        return self.gdtf_fixture or self.instrument_type


@dataclass(frozen=True)
class TypeHardStop:
    candidate_id: str
    code: str
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "code": validate_autopatch("target_exclusion_reason", self.code),
            "label": target_exclusion_label(self.code),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class TypeResolution:
    request: TypeRequest
    status: str
    reason: str
    console_type: LibraryType | None = None
    console_mode: LibraryMode | None = None
    type_candidates: tuple[LibraryType, ...] = ()
    mode_candidates: tuple[LibraryMode, ...] = ()
    confirmation_source: str | None = None
    alias_key: str | None = None
    footprint_check: Mapping[str, object] = field(default_factory=dict)
    hard_stop_code: str | None = None
    incompleteness_kind: str | None = None
    #: [round17 S17-02] 사유 **문장**에 콘솔 판독 원문을 보간하지 않기 위한 구조화 칸(§0 2b④).
    #: `console_type`은 **확정된** 타입만 담으므로(별칭 없이 후보 1건이면 `None`), 사람에게
    #: 제시된 이름을 담을 자리가 없었다. 그 자리가 없으면 문장이 그 역할을 떠맡는다 —
    #: 그렇게 들어간 `'CD 5'`가 `payload["types"]`에서 CD 게이트 밖으로 새어 나갔다.
    presented_type: LibraryType | None = None
    #: 라이브러리 조회에 실제로 쓴 이름(별칭이 있으면 별칭 값, 없으면 도면 값).
    searched_type_key: str | None = None
    searched_mode_key: str | None = None

    @property
    def hard_stop(self) -> TypeHardStop | None:
        if self.hard_stop_code is None:
            return None
        return TypeHardStop(
            candidate_id=self.request.candidate_id,
            code=self.hard_stop_code,
            reason=self.reason,
        )

    @property
    def mode_options_completeness(self) -> ListCompleteness:
        """`mode_candidates`·`mode_options`가 **선언된 모드 전부인가**.

        [round21 R20-B] **저장하지 않고 파생한다.** 갈래마다 세팅하게 만들면 새 갈래가
        조용히 빠뜨리고, 그것이 R20-B의 기제 그 자체였다 — 절단이 참인데
        `incompleteness_kind`를 세우지 않은 갈래가 고지 0건을 냈다. 파생의 근거는
        `presented_type`이고, 그 건전성은 `_mode_candidates`가 지는 부분집합 불변식
        (`mode_candidates ⊆ presented_type.modes`)이 뒷받침한다.
        """
        return _mode_list_completeness(self.presented_type)

    def row(self, *, type_candidates_completeness: ListCompleteness) -> dict[str, object]:
        """조작자 화면 한 행. **완전성 진술 없이는 조립되지 않는다.**

        [round21 R20-B] 인자를 **필수 키워드**로 둔 것이 이번 반영의 처방이다. round19가
        `mode_options`를 더하면서 그 목록의 완전성을 말할 자리를 안 만든 것이 R20-B의
        원인이었으므로, 같은 실수를 **구조로** 막는다: 목록을 실으면서 완전성을 빼는
        조립은 `TypeError`가 된다. 라이브러리 축은 행마다 같으므로 계산 자리도
        `TypeResolutionPlan.to_dict()` 한 곳이다(행마다 만들면 갈래가 늘 때 빠뜨린다).
        모드 축은 이 해상 결과 자신의 `presented_type`에서 파생한다.
        """
        channel_count = self.footprint_check.get("console_channel_count")
        return {
            "candidate_id": self.request.candidate_id,
            "designed_type": self.request.designed_type,
            "instrument_type": self.request.instrument_type,
            "gdtf_fixture": self.request.gdtf_fixture,
            "designed_mode": self.request.mode,
            "cell_count": self.request.cell_count,
            "status": validate_autopatch("type_resolution_status", self.status),
            "status_label": type_resolution_status_label(self.status),
            "console_type": self.console_type.name if self.console_type is not None else None,
            "console_type_index": (
                self.console_type.index if self.console_type is not None else None
            ),
            "console_mode": self.console_mode.name if self.console_mode is not None else None,
            "console_mode_index": (
                self.console_mode.index if self.console_mode is not None else None
            ),
            # [round17 S17-02] 사람에게 **제시된** 콘솔 이름 — 확정 여부와 무관하다.
            # 사유 문장은 이 칸을 대신 말하지 않는다(§0 2b④ · 2c①).
            "presented_console_type": (
                self.presented_type.name if self.presented_type is not None else None
            ),
            "presented_console_type_index": (
                self.presented_type.index if self.presented_type is not None else None
            ),
            "searched_type_key": self.searched_type_key,
            "searched_mode_key": self.searched_mode_key,
            "type_candidates": [entry.name for entry in self.type_candidates],
            "mode_candidates": [entry.name for entry in self.mode_candidates],
            # [round19 major#5] 이름만 적으면 조작자는 **무엇을 고를지** 판단할 근거가 없다.
            # 점유폭 불일치에서 실제로 필요한 것은 각 모드의 채널 수다 — 이름 목록과 같은
            # 원소를 채널 수까지 붙여 싣는다(모든 갈래에 자동 적용된다).
            "mode_options": [
                {"index": entry.index, "name": entry.name, "channel_count": entry.channel_count}
                for entry in self.mode_candidates
            ],
            # [round21 R20-B] 목록 옆에 **그 목록이 선언된 전부인가**를 함께 싣는다.
            # 표시가 없으면 완전하다는 뜻이 되게 하려면 칸이 **항상** 있어야 한다 —
            # 절단일 때만 붙이는 칸은 그 자체가 침묵의 자리다.
            TYPE_CANDIDATES_COMPLETENESS_COLUMN: type_candidates_completeness.presenting(
                len(self.type_candidates)
            ).to_dict(),
            MODE_OPTIONS_COMPLETENESS_COLUMN: self.mode_options_completeness.presenting(
                len(self.mode_candidates)
            ).to_dict(),
            "confirmation_source": self.confirmation_source,
            "confirmation_required": self.status == TYPE_NEEDS_CONFIRMATION,
            "designed_footprint": self.request.footprint,
            "console_channel_count": channel_count,
            FOOTPRINT_UNVERIFIED_COLUMN: self.footprint_check.get("match") is not True,
            "footprint_check": dict(self.footprint_check),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class TypeResolutionPlan:
    assumption_72: str
    library: FixtureTypeLibrary
    resolutions: tuple[TypeResolution, ...]

    @property
    def footprint_match_performed(self) -> bool:
        return self.assumption_72 == ASSUMPTION_72_GO

    def to_dict(self) -> dict[str, object]:
        # [round21 R20-B] 라이브러리 축 완전성은 **한 자리에서** 만든다. `row()`가 그것을
        # 필수 키워드로 받으므로 이 자리를 빠뜨리면 조립 자체가 실패한다 — 목록을 내면서
        # 완전성을 말하지 않는 상태가 구조적으로 불가능하다.
        type_axis = _library_list_completeness(self.library)
        rows = [
            resolution.row(type_candidates_completeness=type_axis)
            for resolution in self.resolutions
        ]
        return {
            "ok": True,
            "assumption_72": self.assumption_72,
            "library": self.library.to_dict(),
            "type_table": {
                "columns": list(TYPE_TABLE_COLUMNS),
                "column_labels": dict(TYPE_TABLE_COLUMN_LABELS),
                "rows": rows,
            },
            "hard_stops": [
                resolution.hard_stop.to_dict()
                for resolution in self.resolutions
                if resolution.hard_stop is not None
            ],
            "skipped_checks": self._skipped_checks(),
            "footprint_mismatches": self._footprint_mismatches(),
            "alias_reuse": self._alias_reuse(),
            FOOTPRINT_UNVERIFIED_COLUMN: not self.footprint_match_performed,
        }

    def _skipped_checks(self) -> list[dict[str, object]]:
        checks: list[dict[str, object]] = []
        if not self.footprint_match_performed:
            checks.append(
                _skipped_check(
                    FOOTPRINT_MATCH_DESCOPE,
                    FOOTPRINT_DESCOPE_REASON,
                    assumption_72=self.assumption_72,
                )
            )
        for kind, reason, extra in (
            (FIXTURE_TYPE_LIBRARY_UNREADABLE, LIBRARY_UNREADABLE_REASON, {}),
            (FIXTURE_TYPE_LIBRARY_TRUNCATED, LIBRARY_TRUNCATED_REASON, {}),
            # [round21 R20-D] 폐기 축은 절단·판독실패와 **동시에 참일 수 있다** — 셋을
            # 한 칸으로 뭉개면 조작자가 조치를 고를 수 없다. 고지에 계수를 함께 실어
            # 규모까지 말한다("행을 못 썼다"만 적으면 몇 개인지 모른다).
            (
                FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED,
                LIBRARY_ROWS_DISCARDED_REASON,
                {
                    "discarded_row_count": _library_rows_discarded(self.library),
                    "unusable_row_count": self.library.unusable_row_count,
                    "unparsable_row_count": self.library.unparsable_row_count,
                    "unusable_mode_row_count": sum(
                        entry.unusable_mode_row_count for entry in self.library.types
                    ),
                    "unparsable_mode_row_count": sum(
                        entry.unparsable_mode_row_count for entry in self.library.types
                    ),
                },
            ),
        ):
            # [round21 R20-B] **관측 축**을 함께 본다. 이전 판은 처분 축
            # (`incompleteness_kind`)만 봤고, 절단된 목록이 비지 않은 갈래는 그 칸을
            # 세우지 않으므로 고지가 0건이었다 — 조작자는 부분 목록을 전부로 봤다.
            #
            # **처분 축을 넓혀 고치지 않은 이유**: `apply._unresolved_type_verdict`가 그
            # 칸을 배제 코드로 그대로 옮긴다. 확인 대기 갈래에 세우면 배제 코드가
            # `type_confirmation_pending`에서 절단 코드로 바뀌어, round19 불변식
            # (`confirmation_required`가 참이면 배제 코드는 pending) 이 깨진다. 고치려다
            # 옆을 깨는 것이 이 SPEC의 반복 실패라, 관측과 처분을 **다른 축으로 둔다**:
            #   · 처분 = 이 후보를 어떻게 할 것인가(배제 코드).
            #   · 관측 = 제시한 목록이 전부인가(마커 · 고지).
            # [round21 R20-D] 세 번째 근거: **동시에 참인 축 전부**. 위 두 근거는 축을
            # 하나만 고른다(`_library_axis`는 처분용이라 첫 축에서 멈춘다). 절단과 폐기가
            # 함께 참인 스냅샷에서 그러면 하나만 고지되고, 조작자는 남은 조치를 모른다.
            if (
                kind in _library_observed_axes(self.library)
                or kind in self._observed_incompleteness_kinds()
                or any(resolution.incompleteness_kind == kind for resolution in self.resolutions)
            ):
                checks.append(_skipped_check(kind, reason, **extra))
        return checks

    def _observed_incompleteness_kinds(self) -> frozenset[str]:
        """행에 실린 완전성 진술이 **불완전이라 말한** 축 전부.

        고지가 마커와 **같은 근거**에서 나야 한다 — 두 자리에서 따로 판정하면 마커가
        불완전이라 말하면서 고지가 비는 조합이 다시 가능해진다. `complete is None`
        (근거 없음)은 여기 세지 않는다: 미관측을 단정하는 것이 아니라 모른다는 뜻이고,
        그 상태에서 "열거를 못 봤다"고 고지하면 없는 사실을 말하는 것이 된다.
        """
        statements = [
            _library_list_completeness(self.library),
            *(resolution.mode_options_completeness for resolution in self.resolutions),
        ]
        return frozenset(
            statement.incompleteness_kind
            for statement in statements
            if statement.complete is False and statement.incompleteness_kind is not None
        )

    def _footprint_mismatches(self) -> list[dict[str, object]]:
        return [
            {
                "candidate_id": resolution.request.candidate_id,
                "console_type": resolution.footprint_check.get("console_type"),
                "console_mode": resolution.footprint_check.get("console_mode"),
                "designed_footprint": resolution.request.footprint,
                "console_channel_count": resolution.footprint_check.get("console_channel_count"),
                "reason": resolution.footprint_check.get("reason"),
            }
            for resolution in self.resolutions
            if resolution.footprint_check.get("match") is False
        ]

    def _alias_reuse(self) -> list[dict[str, object]]:
        return [
            {
                "candidate_id": resolution.request.candidate_id,
                "alias_key": resolution.alias_key,
                "console_type": resolution.console_type.name,
                "console_mode": (
                    resolution.console_mode.name if resolution.console_mode is not None else None
                ),
            }
            for resolution in self.resolutions
            if resolution.confirmation_source == ALIAS_CONFIRMATION_SOURCE
            and resolution.console_type is not None
        ]


def read_fixture_type_library(
    port: LibraryPort, *, read_channel_counts: bool = False
) -> FixtureTypeLibrary:
    """FixtureType 열거를 읽고 **몇 개를 못 봤는지 함께 센다**.

    [round21 R20-A ⓐ] 이전 판은 절단을 `state["truncated"]` 플래그 하나로 받았다.
    PRESERVE `server/prechk/inventory.py` 독스트링 2번이 금지한 형태이고, 같은 파일의
    `_read_channel_count`가 30줄 거리에서 이미 `node.childCount`를 정상적으로 읽고
    있었다 — 규율이 한 모듈 안에서 갈려 있었다. 이제 총계를 읽어 **계수 대조**로
    판정하고 플래그는 병존시킨다(`FixtureTypeLibrary.enumeration_incomplete`).

    **추가 질의는 0회다.** `childCount`는 절단된 payload에도 이미 들어 있다.
    """
    state = port.query_state(FIXTURE_TYPE_LIBRARY_ROOT)
    if state.get("ok") is not True:
        return FixtureTypeLibrary(available=False)
    node = state.get("node")
    child_count = _optional_int(node.get("childCount")) if isinstance(node, Mapping) else None
    rows = _mapping_rows(state.get("children"))
    # [round21 R20-D] payload가 **실어 온 행 전부**. 매핑이 아닌 행은 슬롯 번호조차
    # 물어볼 수 없다 — `patchplan._existing_fids_from_console`의 `unparsable_rows`와
    # 같은 산식이고, 구판은 그 행을 `_mapping_rows`가 조용히 삼키게 두었다.
    raw_rows = _row_sequence(state.get("children"))
    unparsable_rows = len(raw_rows) - len(rows)
    unusable_rows = 0
    seen_slots: set[int] = set()
    types: list[LibraryType] = []
    for child in rows:
        index = _optional_int(child.get("i"))
        listed = _optional_string(child.get("name"))
        # [round21 R20-D] **버린 것을 센다.** 구판은 계수 없이 버려 "슬롯이 확립되지
        # 않았다"를 "라이브러리에 없다"로 바꿔 냈다. 중복 `i`도 형제와 같이 폐기로
        # 센다(`patchplan`의 `child_index in read_slots` 갈래) — 같은 인덱스를 두 번
        # 읽으면 같은 콘솔 경로가 서로 다른 이름으로 두 번 실린다.
        if index is None or not listed or index in seen_slots:
            unusable_rows += 1
            continue
        seen_slots.add(index)
        types.append(_read_type(port, index, listed, read_channel_counts=read_channel_counts))
    return FixtureTypeLibrary(
        types=tuple(types),
        available=True,
        truncated=state.get("truncated") is True,
        child_count=child_count,
        enumerated_count=len(types),
        # 절단 축의 분모는 **실어 온 행 전부**다. 폐기 행을 빼면 폐기가 절단으로 새어
        # `returned == enumerated + unusable + unparsable` 상보가 깨진다.
        returned_row_count=len(raw_rows),
        unusable_row_count=unusable_rows,
        unparsable_row_count=unparsable_rows,
    )


def recover_requested_types(
    port: LibraryPort,
    library: FixtureTypeLibrary,
    wanted: Sequence[str],
    *,
    read_channel_counts: bool = False,
) -> FixtureTypeLibrary:
    """열거에 없는 **요청된 타입 이름만** 유계 스윕으로 찾고, 일치를 **전수로** 모은다.

    규율은 PRESERVE `server/prechk/inventory.py`의 회수 스윕에서 그대로 가져왔고,
    `patchplan._existing_fids_from_console`이 round19에 같은 방식으로 인용했다:

    * **스윕 전제**(`slots_established`): 열거된 항목이 **하나라도** 있어야 한다.
      responder의 슬롯 해석기는 `any_slot_known`이 거짓일 때 `children[wanted]`를 —
      즉 **위치**를 — 돌려준다. 열거가 빈 상태에서 스윕하면 위치를 슬롯으로 오인한다.
    * **경계**: `1..child_count` 유계. 총계를 모르면 스윕하지 않는다.
    * **인덱스 도메인**: 열거된 인덱스가 경계 밖이면 스윕 도메인이 어긋난 것이므로
      스윕하지 않는다.
    * **판정은 스윕으로 승격되지 않는다.** 이 함수는 `types`·`recovered_count`·
      `probe_failures`·`recovery_probe_count`만 늘린다. `truncated`·`child_count`·
      `enumerated_count`·`returned_row_count`는 손대지 않으므로 `enumeration_short`와
      `enumeration_incomplete`는 **정의상 변하지 않는다**. 회수해 놓고 "전수를 봤다"고
      적는 것이 R18-A식 거짓 보고다.
    * 프로브 실패는 `probe_failures`라는 **진단 계수**로 남고 관측이 되지 않는다.
      `ok=false`는 실패가 아니다 — 유계 범위 안의 빈 인덱스는 희소 풀의 정보다.

    **[round23 R22-C] 조기 종료는 없다 — 모호성 규율은 열거 경로와 하나다.**
    구판은 첫 퍼지 일치에서 `break` 했다. `fuzzy_type_equal`은 **포함관계** 매칭이라
    요청 이름을 부분 포함하는 다른 제품이 더 낮은 슬롯에 있으면 스윕은 그것을 회수하고
    **정답 슬롯은 프로브조차 하지 않았다** — 스윕이 없을 때 fail-closed로 배제되던
    입력이 **잘못된 타입 확정**으로 바뀌었다. 그래서 이름 프로브는 전 미열거 슬롯에
    한 번씩 돌고, 일치가 둘 이상이면 **둘 다 회수해** 후보로 싣는다. 확정 여부는
    열거 경로와 **같은 자리**(`len(type_candidates) == 1`)가 판단한다.

    **왜 전수 스윕이 아닌가 — 비용을 재서 버렸다.**
    미관측 인덱스 수를 ``U = child_count - enumerated_count``, 일치한 타입 수를 ``k``
    (보통 1), 한 타입의 모드 수를 ``m``이라 하자.

    `_read_type` 한 번의 비용은 ``1 + c·m`` 이다: DMXModes 상태 1회 + 모드당 이름
    프로퍼티 1회 + (점유폭 GO 분기에서만) 모드당 DMXChannels 상태 1회. 즉 기본
    분기(`negative`)는 ``c=1``, GO 분기는 ``c=2``.

    * 표적 스윕(채택): ``U + k·(1 + c·m)`` 회. 이름 확인은 인덱스당 `query_state`
      **1회**뿐이고 `_read_type`은 **일치한 타입에만** 딸려온다. 200종 라이브러리
      (열거 24, U=176, k=1, m=20)에서 negative ``176 + 21 = 197`` · GO
      ``176 + 41 = 217`` 회 — 형제 FID 스윕과 **같은 차수**다(그쪽 실측: 39슬롯에서
      40왕복·2.65s = 왕복당 66.25ms → 약 13~15초).
    * 전수 스윕(채택하지 않음): ``U·(1 + 1 + c·m)`` 회. 같은 조건에서 negative
      ``176 × 22 = 3,872`` · GO ``176 × 42 = 7,392`` 회 — 왕복당 66.25ms면 4분~8분이고
      세션이 멈춘다. GDTF 모드 5~20 대역에서 1,232~7,392회다.

    즉 전수 스윕의 부재는 **결함이 아니라 비용 판정의 결과**다. 표적 스윕까지 실패한
    이름만 부재를 말할 자격이 있고, 그 밖에는 미관측을 미관측이라 적는다.

    **[round23 R22-F] 그 비용 근거의 유효 범위.** 위 기각은 ``3,872`` 왕복(≈4분)에서
    내려졌는데, 채택 설계의 비용도 ``U``에 **선형**이고 `child_count`는 콘솔이 선언한
    정수라 이 함수가 묶지 않는다. 즉 ``U``가 ``3,872 − k(1 + c·m)``(위 예시 값으로
    약 3,850)을 넘으면 **"전수는 비싸서 안 한다"는 문장이 이 설계에도 그대로 참**이
    된다 — 근거가 자기 유효 범위를 벗어난다.

    그때 **스윕을 거부하지는 않는다**. 거부하면 느리지만 옳은 답이 임의의 수치 때문에
    `fixture_type_not_in_library` 배제로 바뀌어, 이 스윕이 없애려던 거짓 부재가
    돌아온다. 그리고 `child_count`에 상한을 둘 **근거가 없다**(하드 캡은 반환 행 수에
    걸린 것이지 선언 총계에 걸린 것이 아니고, 형제 PRESERVE 스윕도 상한 없이 훑는다) —
    근거 없는 상한을 짓지 않는 판단은 round18이 FID 상한에서 이미 내렸다. 대신
    **왕복 수와 범위 이탈 사실을 payload에 싣는다**: `recovery_probe_count` ·
    `FixtureTypeLibrary.recovery_cost_basis_exceeded` · `RECOVERY_COST_EVIDENCE_ROUNDTRIPS`.
    진행 보고와 중단 수단은 포트 계약 밖이라 여기서 만들 수 없고, 만들 수 없는 것을
    만든 척하는 대신 **비용이 얼마였는지 말한다**.
    """
    if not library.available or not wanted:
        return library
    child_count = library.child_count
    if child_count is None:
        return library
    # 스윕 전제 — 열거가 비면 인덱스가 위치로 강등된다(위 독스트링).
    if not library.types:
        return library
    # 절단 판정은 **계수 대조**로 한다. 플래그가 아니다.
    if library.enumerated_count >= child_count:
        return library
    # [round23 R22-B] 이 가드의 식은 **완전성 진술과 같은 자리**에서 온다. 구판은 여기에
    # 인라인 표현식이었고, 같은 스냅샷을 스윕은 거부하는데 목록 완전성은 `complete=True`로
    # 말했다 — 두 표면이 같은 근거를 다르게 신뢰했다.
    if library.index_domain_violated:
        return library
    pending = [
        key
        for key in dict.fromkeys(wanted)
        if not any(fuzzy_type_equal(key, entry.name) for entry in library.types)
    ]
    if not pending:
        return library

    observed = {entry.index for entry in library.types}
    # [round23 R22-C] **조기 종료가 없다.** 구판은 첫 퍼지 일치에서 `break` 하고
    # `pending`을 줄였다. 포함관계 매칭이라 요청 이름을 부분 포함하는 다른 제품이 더
    # 낮은 슬롯에 있으면 그것으로 확정되고 정답 슬롯은 프로브도 되지 않았다.
    # `pending`을 줄이지 않는 것이 그 규율의 코드 형태다 — 줄이면 뒤 슬롯의 같은 이름이
    # 안 걸려 조기 종료가 다른 형태로 되살아난다.
    matched: list[tuple[int, str]] = []
    probe_failures = 0
    probe_count = 0
    for index in range(1, child_count + 1):
        if index in observed:
            continue
        probe_count += 1
        try:
            probe = port.query_state(f"{FIXTURE_TYPE_LIBRARY_ROOT}/{index}")
        except Exception:
            # 전송 결함 — 응답을 못 받은 것이지 인덱스가 빈 것이 아니다.
            probe_failures += 1
            continue
        if probe.get("ok") is not True:
            continue
        probe_node = probe.get("node")
        name = _optional_string(probe_node.get("name")) if isinstance(probe_node, Mapping) else None
        if not name:
            probe_failures += 1
            continue
        # [round17 모호성 규율] 이 이름에 맞는 요청 키를 **하나 고르지 않는다** — 어느
        # 키가 걸렸는지는 회수 여부를 바꾸지 않으므로 존재만 묻는다. 구판 주석은 이
        # **요청 키 쪽** 모호성만 다뤘고, 같은 표현식 안 형제인 **콘솔 이름 쪽** 모호성
        # (한 요청 키에 여러 콘솔 이름이 걸림)은 다루지 않았다 — 그것이 R22-C다.
        if any(fuzzy_type_equal(key, name) for key in pending):
            matched.append((index, name))
    # `_read_type`(DMXModes + 모드당 프로퍼티)은 **일치한 슬롯에만** 건다 — 표적 스윕과
    # 전수 스윕을 가르는 지점이고, 독스트링 비용 표의 `k` 계수 그 자체다.
    recovered = tuple(
        replace(
            _read_type(port, index, name, read_channel_counts=read_channel_counts),
            recovered=True,
        )
        for index, name in matched
    )
    # [round23 R22-A] **손으로 필드를 열거하지 않는다.** 구판은 11칸 중 9칸만 옮겨
    # `unusable_row_count`·`unparsable_row_count`를 기본값 0으로 리셋했고, 상보식
    # `returned == enumerated + unusable + unparsable`이 깨지면서 폐기 축이 통째로
    # 사라져 `library_incomplete`가 `library_absent`로 하강했다 — round21이 R20-D로
    # 닫은 거짓 부재("콘솔에서 GDTF 라이브러리 임포트를 먼저")가 그대로 되살아났다.
    # 열거식 재구성은 **결함 생성기**다: 칸이 늘 때마다 옮기기를 잊을 자리가 하나씩
    # 는다. 인자를 두 개 더 적는 것이 아니라 `replace`로 그 실수를 **표현 불가능**하게
    # 만드는 것이 처방이다(같은 파일 `ListCompleteness.presenting`이 이미 그 형태다).
    return replace(
        library,
        types=tuple(sorted((*library.types, *recovered), key=lambda entry: entry.index)),
        recovered_count=library.recovered_count + len(recovered),
        recovery_boundary=child_count,
        probe_failures=library.probe_failures + probe_failures,
        recovery_probe_count=library.recovery_probe_count + probe_count,
    )


def resolve_fixture_types(
    requests: Sequence[TypeRequest],
    *,
    library_port: LibraryPort,
    assumption_72: str = ASSUMPTION_72_NEGATIVE,
    type_aliases: Mapping[str, object] | None = None,
) -> TypeResolutionPlan:
    branch = _assumption_72_or_default(assumption_72)
    footprint_enabled = branch == ASSUMPTION_72_GO
    library = read_fixture_type_library(library_port, read_channel_counts=footprint_enabled)
    aliases = dict(type_aliases or {})
    # [round21 R20-A ⓑ] 열거가 짧았고 요청된 이름이 그 안에 없으면 **그 이름만** 찾는다.
    # 별칭이 대조 기준을 바꾸므로 별칭 해석 뒤에 부른다 — `_type_search_keys`가 곧
    # `_type_candidates`가 쓸 키와 같은 키를 낸다(스윕이 다른 기준으로 찾으면 회수해
    # 놓고도 후보로 잡히지 않는다).
    wanted: list[str] = []
    for request in requests:
        _key, alias_type, _alias_mode = _alias_for(request, aliases)
        wanted.extend(_type_search_keys(request, alias_type))
    library = recover_requested_types(
        library_port, library, wanted, read_channel_counts=footprint_enabled
    )
    resolutions = tuple(
        _resolve_one(request, library, aliases, footprint_enabled=footprint_enabled)
        for request in requests
    )
    return TypeResolutionPlan(assumption_72=branch, library=library, resolutions=resolutions)


def _resolve_one(
    request: TypeRequest,
    library: FixtureTypeLibrary,
    aliases: Mapping[str, object],
    *,
    footprint_enabled: bool,
) -> TypeResolution:
    alias_key, alias_type, alias_mode = _alias_for(request, aliases)
    # [round17 S17-02] 조회에 실제로 쓴 이름을 **문장이 아니라 칸으로** 들고 다닌다.
    # 별칭 값은 사람이 콘솔에서 확인해 저장한 **콘솔 쪽 이름**이라 도면 값과 같은 등급이
    # 아니다 — 사유 문장에 보간되면 `payload["types"]`가 CD 게이트 밖으로 원문을 흘린다.
    searched_type_key = alias_type or request.designed_type
    searched_mode_key = alias_mode or request.mode
    if not _type_search_keys(request, alias_type):
        # [round17 · 공허 일치 차단] 대조 기준이 될 이름이 없다. "라이브러리에 없다"고
        # 적으면 **찾아보지도 않은 것을 부재로 단정**하는 것이다 — 그래서 코드도 사유도
        # `fixture_type_not_in_library`가 아니다.
        # [round18 R18-E] 그러나 `needs_confirmation`도 아니다: 이 갈래는 `type_candidates`가
        # **0건**이라 제시된 후보가 없다. 확인할 것이 없는 상태를 "확인 대기"로 적으면
        # `hard_stops`가 비고 `confirmation_required`가 참이 되어, 조작자는 화면에 없는 것을
        # 고르려 기다린다. 하드 스톱으로 낸다 — 고칠 곳은 도면이다.
        # (별칭 탈출구는 남아 있다: 이름이 truthy면 그 이름을 키로 한 별칭에 실재 콘솔 이름을
        #  저장해 두면 `alias_type`이 기준이 되어 이 갈래에 오지 않는다. 이름이 `None`·`''`면
        #  `_alias_for`의 `if not key: continue`에 걸려 그 탈출구조차 없다 — 실측 확인.)
        return TypeResolution(
            request=request,
            status=TYPE_NAME_UNUSABLE,
            reason=VACUOUS_TYPE_KEY_REASON,
            hard_stop_code=FIXTURE_TYPE_NAME_UNUSABLE,
            searched_type_key=searched_type_key,
            searched_mode_key=searched_mode_key,
            footprint_check=_footprint_check(
                None, None, request, footprint_enabled=footprint_enabled
            ),
        )
    type_candidates = _type_candidates(request, library, alias_type)
    if not type_candidates:
        incomplete = _library_incompleteness(library, None)
        if incomplete is not None:
            return TypeResolution(
                request=request,
                status=TYPE_LIBRARY_INCOMPLETE,
                reason=_incompleteness_reason(incomplete),
                incompleteness_kind=incomplete,
                searched_type_key=searched_type_key,
                searched_mode_key=searched_mode_key,
                footprint_check=_footprint_check(
                    None, None, request, footprint_enabled=footprint_enabled
                ),
            )
        return TypeResolution(
            request=request,
            status=TYPE_LIBRARY_ABSENT,
            reason=TYPE_ABSENT_REASON,
            searched_type_key=searched_type_key,
            searched_mode_key=searched_mode_key,
            hard_stop_code=FIXTURE_TYPE_NOT_IN_LIBRARY,
            footprint_check=_footprint_check(
                None, None, request, footprint_enabled=footprint_enabled
            ),
        )

    sole_candidate = type_candidates[0] if len(type_candidates) == 1 else None
    confirmed_type = sole_candidate if alias_type else None
    presented_type = confirmed_type or sole_candidate

    if presented_type is not None and not presented_type.modes_available:
        return TypeResolution(
            request=request,
            status=TYPE_LIBRARY_INCOMPLETE,
            reason=LIBRARY_UNREADABLE_REASON,
            console_type=confirmed_type,
            type_candidates=type_candidates,
            confirmation_source=ALIAS_CONFIRMATION_SOURCE if confirmed_type else None,
            alias_key=alias_key if confirmed_type else None,
            presented_type=presented_type,
            searched_type_key=searched_type_key,
            searched_mode_key=searched_mode_key,
            incompleteness_kind=FIXTURE_TYPE_LIBRARY_UNREADABLE,
            footprint_check=_footprint_check(
                confirmed_type, None, request, footprint_enabled=footprint_enabled
            ),
        )

    mode_candidates = _mode_candidates(request, presented_type, alias_mode)
    if presented_type is not None and not mode_candidates:
        incomplete = _library_incompleteness(library, presented_type)
        if incomplete is not None:
            return TypeResolution(
                request=request,
                status=TYPE_LIBRARY_INCOMPLETE,
                reason=_incompleteness_reason(incomplete),
                console_type=confirmed_type,
                type_candidates=type_candidates,
                confirmation_source=ALIAS_CONFIRMATION_SOURCE if confirmed_type else None,
                alias_key=alias_key if confirmed_type else None,
                presented_type=presented_type,
                searched_type_key=searched_type_key,
                searched_mode_key=searched_mode_key,
                incompleteness_kind=incomplete,
                footprint_check=_footprint_check(
                    confirmed_type, None, request, footprint_enabled=footprint_enabled
                ),
            )
        return TypeResolution(
            request=request,
            status=TYPE_LIBRARY_ABSENT,
            reason=MODE_ABSENT_REASON,
            console_type=confirmed_type,
            presented_type=presented_type,
            searched_type_key=searched_type_key,
            searched_mode_key=searched_mode_key,
            type_candidates=type_candidates,
            confirmation_source=ALIAS_CONFIRMATION_SOURCE if confirmed_type else None,
            alias_key=alias_key if confirmed_type else None,
            hard_stop_code=DMX_MODE_NOT_IN_LIBRARY,
            footprint_check=_footprint_check(
                confirmed_type, None, request, footprint_enabled=footprint_enabled
            ),
        )

    confirmed_mode = mode_candidates[0] if alias_mode and len(mode_candidates) == 1 else None
    resolved = confirmed_type is not None and confirmed_mode is not None
    footprint_check = _footprint_check(
        confirmed_type if resolved else None,
        confirmed_mode if resolved else None,
        request,
        footprint_enabled=footprint_enabled,
    )
    if resolved and footprint_check.get("match") is False:
        # [round19 major#5] 이 갈래는 **막다른 길이었다.** 도달 조건이 "별칭에 모드가
        # 지정돼 있다"이고 `_mode_candidates`가 그 `alias_mode`로 후보를 걸러내므로,
        # `mode_candidates`에는 **점유폭이 안 맞은 바로 그 모드 하나**만 실려 있었다.
        # 그런데 문장은 "모드를 다시 확인해야 한다"고 말했다 — 조작자 화면에는 고를 것이
        # 없거나(모드가 하나뿐 · 전부 불일치), 맞는 모드가 실제로 있어도 payload가 그것을
        # 보여주지 않았다. 실제 조치가 "도면 DMX Footprint를 고쳐라"인 경우에도 문장은
        # 모드 확인을 가리켜 **거짓 안내**였다.
        #
        # 그래서 여기서는 **라이브러리의 전 모드를 채널 수와 함께** 후보로 싣는다 —
        # 고를 수 있는 것을 보여주는 것이 "확인 대기"의 전제다. 그리고 맞는 모드가 하나도
        # 없으면 모드 선택으로 못 벗어나므로 **하드 스톱**이고, 사유는 실제 조치를 가리킨다.
        #
        # `assumption_72`가 `go`가 아니면 대조 자체가 수행되지 않아 `match`는 `None`이다 —
        # 이 갈래에 오지 않는다. 미수행을 불일치와 같은 문장으로 다루지 않는다.
        #
        # `resolved`이므로 `confirmed_type`은 `None`이 아니고 `presented_type`과 같다 —
        # 그래도 단언을 심지 않고 좁힌다(런타임 단언은 실패 경로를 예외로 바꾼다).
        library_modes = confirmed_type.modes if confirmed_type is not None else ()
        matching = tuple(mode for mode in library_modes if mode.channel_count == request.footprint)
        # 맞는 모드의 **부재를 단정할 수 있는가** — 전제는 `_absence_assertable` 한 자리에
        # 모여 있다. 구판은 이 표현식이 인라인이었고, 전제 하나(`modes_available`)는 80줄
        # 위 조기 반환에 있었으며 또 하나(**폐기된 행이 없음**)는 어디에도 없었다
        # (round20 R20-D). 20줄·80줄 거리로 흩어진 전제는 다음 라운드에 또 하나가 빠진다.
        #
        # [round23 R22-E 형제 표면] **타입 정체가 확실해야** 이 부재를 말할 수 있다.
        # `_absence_assertable`이 재는 것은 *이 타입의* 모드 목록이 전수인가이고, 하드
        # 스톱이 주장하는 것은 *맞는 모드가 없다*이므로 그 사이에 전제가 하나 더 있다:
        # **이 타입이 맞는 타입인가.** 루트 열거가 부분이면 요청 이름을 부분 포함하는
        # 다른 제품이 미관측 구간에 있을 수 있고, 그때 "도면 점유폭을 고쳐라"는 거짓
        # 안내다. 확정을 막는 것과 같은 근거(행에 실리는 완전성 진술)를 본다 —
        # 막지 않으면 `resolved`는 아니지만 **확정 등급의 부재 단정**이 나간다.
        absence_assertable = _absence_assertable(confirmed_type) and _confirmable_from(
            _library_list_completeness(library)
        )
        footprint_branch: dict[str, object] = {
            "request": request,
            "console_type": confirmed_type,
            "console_mode": confirmed_mode,
            "type_candidates": type_candidates,
            # 별칭으로 좁혀진 한 건이 아니라 **라이브러리 전 모드**를 싣는다.
            "mode_candidates": library_modes,
            "confirmation_source": ALIAS_CONFIRMATION_SOURCE,
            "alias_key": alias_key,
            "presented_type": presented_type,
            "searched_type_key": searched_type_key,
            "searched_mode_key": searched_mode_key,
            "footprint_check": footprint_check,
        }
        if matching:
            return TypeResolution(
                status=TYPE_NEEDS_CONFIRMATION,
                reason=FOOTPRINT_MISMATCH_CHOOSABLE_REASON,
                **footprint_branch,  # type: ignore[arg-type]
            )
        if absence_assertable:
            return TypeResolution(
                status=TYPE_FOOTPRINT_UNMATCHABLE,
                reason=FOOTPRINT_UNMATCHABLE_REASON,
                hard_stop_code=DESIGNED_FOOTPRINT_MATCHES_NO_MODE,
                **footprint_branch,  # type: ignore[arg-type]
            )
        # 맞는 모드가 목록에 없지만 **부재를 단정할 수 없다** — 이 상태는 확인 대기가
        # 아니다: 제시된 모드 중 어느 것을 골라도 점유폭이 안 맞으므로 조작자가 payload로
        # 수행할 수 있는 선택이 없다. "후보 제시 — 사용자 확인 대기"라 적으면 R18-E와
        # 같은 거짓이 된다. 관측 불완전으로 낸다(`skipped_checks`에 그 사유가 함께 나간다).
        # 확정 타입도 비운다: 관측이 불완전한 상태에서 콘솔 타입을 확정으로 내보내지 않는다.
        return TypeResolution(
            request=request,
            status=TYPE_LIBRARY_INCOMPLETE,
            reason=FOOTPRINT_MISMATCH_UNVERIFIED_REASON,
            incompleteness_kind=(
                _library_incompleteness(library, confirmed_type) or FIXTURE_TYPE_LIBRARY_UNREADABLE
            ),
            type_candidates=type_candidates,
            mode_candidates=library_modes,
            presented_type=presented_type,
            searched_type_key=searched_type_key,
            searched_mode_key=searched_mode_key,
            footprint_check=footprint_check,
        )
    if resolved and not _confirmable_lists(library, presented_type):
        # [round23 R22-E] **완전성 마커를 읽는 처분이 여기 있다.** round21은 `row()`가
        # 완전성 진술을 필수로 받게 만들었지만 그 값을 소비하는 자리를 만들지 않았고,
        # 그래서 한 행이 `resolved`와 `complete:false`를 동시에 말했다 — 선언 4모드 중
        # 1행(`Mode 10`)만 도착한 스냅샷에서 도면이 요구한 `Mode 1`이 포함관계 퍼지로
        # 그 하나에 붙어 확정까지 갔다(점유폭이 달라 주소 배치까지 어긋난다).
        #
        # **왜 확인 대기가 아닌가.** 제시된 목록이 부분이면 조작자가 골라야 할 것이
        # 화면에 없을 수 있다 — 그 상태를 "확인 대기"로 적는 것이 R18-E의 거짓이다.
        # 이 갈래의 처분은 형제 넷과 **같은** `library_incomplete`이고 축도 같은
        # `_library_incompleteness` 하나에서 나온다. 새 상태도 새 코드도 만들지 않는다:
        # `incompleteness_kind`는 `apply._unresolved_type_verdict`를 거쳐 배제 코드가
        # 되므로, 여기에 어휘를 더하는 것은 처분 축을 넓히는 일이다(round19 major#4).
        #
        # 축을 못 고르는 경우(`child_count`를 못 읽어 완전성이 `None`)의 대체는 바로 위
        # 점유폭 미검증 갈래와 **같은 식**이다 — 두 자리가 갈리면 같은 스냅샷이 자리마다
        # 다른 축을 말한다.
        #
        # 확정 칸(`console_type`·`console_mode`)은 비운다. 관측이 불완전한 상태에서
        # 확정을 내보내지 않는다 — 위 갈래와 같은 규율이다.
        blocking = _library_incompleteness(library, presented_type) or (
            FIXTURE_TYPE_LIBRARY_UNREADABLE
        )
        return TypeResolution(
            request=request,
            status=TYPE_LIBRARY_INCOMPLETE,
            reason=_incompleteness_reason(blocking),
            incompleteness_kind=blocking,
            type_candidates=type_candidates,
            mode_candidates=mode_candidates,
            presented_type=presented_type,
            searched_type_key=searched_type_key,
            searched_mode_key=searched_mode_key,
            footprint_check=footprint_check,
        )
    return TypeResolution(
        request=request,
        status=TYPE_RESOLVED if resolved else TYPE_NEEDS_CONFIRMATION,
        reason=ALIAS_RESOLVED_REASON if resolved else CANDIDATES_PRESENTED_REASON,
        console_type=confirmed_type,
        console_mode=confirmed_mode,
        type_candidates=type_candidates,
        mode_candidates=mode_candidates,
        confirmation_source=ALIAS_CONFIRMATION_SOURCE if resolved else None,
        alias_key=alias_key if resolved else None,
        presented_type=presented_type,
        searched_type_key=searched_type_key,
        searched_mode_key=searched_mode_key,
        footprint_check=footprint_check,
    )


def _comparable_key(value: object) -> str | None:
    """대조 기준이 되는 이름만 통과시킨다 — **정규화 후 영숫자가 남아야** 한다.

    [round17 · 공허 일치 차단] `rig.fuzzy_type_equal`은 `rig._norm_type`으로 비영숫자를
    전부 제거한 뒤 포함관계를 본다. 그래서 `'---'`·`'--'`처럼 영숫자가 없는 이름은 정규화
    결과가 빈 문자열이 되고, 빈 문자열은 **모든** 이름에 포함되므로 그 이름은 라이브러리
    전 항목과 "일치"한다. 라이브러리 항목이 하나뿐이면 그것이 **유일 후보**가 되어 별칭과
    함께 `resolved`까지 가고, 도면이 이름조차 준 적 없는 FixtureType이 전달 Lua의
    `Patch().FixtureTypes[...]`에 박힌다(실증됨).

    막는 층은 여기다 — `rig.py`는 1단계 공개 계약(AC-AUTOPATCH-025)이라 바꾸지 않는다.
    판정 술어를 재구현하지도 않는다: 같은 `_norm_type`을 호출해 **공허함만** 본다.
    """
    if not isinstance(value, str) or not value:
        return None
    return value if _norm_type(value) else None


def is_vacuous_type_name(value: object) -> bool:
    """`_comparable_key`의 **공개 술어** — 이 이름은 타입 대조 기준이 되지 못한다.

    [round18 R18-J] 같은 판정을 `patchplan`이 필요로 한다: 1단계 `diff.compare`가
    `fuzzy_type_equal`로 조인하므로 공허한 도면 타입 이름은 콘솔 전 항목과 "일치"하고
    그 픽스처는 `missing_in_console`·`quantity_mismatch` 양쪽에서 사라진다. 2단계는
    그 소멸을 **고칠** 수 없지만(1단계 소관) **고지**해야 한다. 술어를 재구현하지 않고
    이 하나를 쓴다 — 두 층의 공허 판정이 갈리면 고지가 대상과 어긋난다.
    """
    return _comparable_key(value) is None


def _alias_for(
    request: TypeRequest, aliases: Mapping[str, object]
) -> tuple[str | None, str | None, str | None]:
    for key in (request.gdtf_fixture, request.instrument_type):
        if not key:
            continue
        entry = aliases.get(key)
        if isinstance(entry, Mapping):
            # 공허한 별칭 값은 **저장된 확인**이 아니다 — 없는 것으로 취급해 확정 경로를 막는다.
            return key, _comparable_key(entry.get("type")), _comparable_key(entry.get("mode"))
        if isinstance(entry, str) and entry:
            return key, _comparable_key(entry), None
    return None, None, None


def _type_search_keys(request: TypeRequest, alias_type: str | None) -> tuple[str, ...]:
    """라이브러리 대조에 쓸 이름 — 공허한 이름은 기준이 되지 못하므로 제외한다."""
    raw: tuple[object, ...] = (
        (alias_type,) if alias_type else (request.instrument_type, request.gdtf_fixture)
    )
    keys = (_comparable_key(value) for value in raw)
    return tuple(key for key in keys if key is not None)


def _type_candidates(
    request: TypeRequest, library: FixtureTypeLibrary, alias_type: str | None
) -> tuple[LibraryType, ...]:
    keys = _type_search_keys(request, alias_type)
    return tuple(
        entry for entry in library.types if any(fuzzy_type_equal(key, entry.name) for key in keys)
    )


def _mode_candidates(
    request: TypeRequest, console_type: LibraryType | None, alias_mode: str | None
) -> tuple[LibraryMode, ...]:
    """제시할 모드 후보 — **반드시 `console_type.modes`의 부분집합**이다.

    [round21 R20-B] 이전 판의 주석은 요청 모드가 없을 때 *"전 모드를 후보로 제시한다"*고
    적었다. **그 문장이 결함이었다**: `console_type.modes`는 절단될 수 있는 열거 결과이고,
    그것을 "전 모드"라 부르면 부분 목록이 전부로 제시된다. 목록이 비지 않으니 호출자의
    절단 가드(`if presented_type is not None and not mode_candidates`)도 지나가고,
    `incompleteness_kind`가 서지 않아 고지가 **0건**이었다.

    이 함수는 목록을 **좁히기만** 한다. 그 목록이 선언된 전부인지는
    `TypeResolution.mode_options_completeness`가 `presented_type`에서 파생해 말한다.
    완전성을 여기서 함께 돌려주지 않는 이유는, 갈래마다 그것을 실어 나르게 만들면 새
    갈래가 조용히 빠뜨리기 때문이다 — R20-B의 기제 그 자체다. 대신 이 함수는 그 파생의
    전제인 **부분집합 불변식**을 진다: 여기서 `console_type` 밖의 모드를 만들어 넣으면
    완전성 진술이 그 원소를 덮지 못한다.
    """
    if console_type is None:
        return ()
    # 공허한 모드 이름은 "모드 미지정"과 같다 — 관측된 모드를 후보로 제시하고 확정은 하지
    # 않는다. **"관측된"이 "전"이 아니다** — 그 차이를 말하는 것이 완전성 칸이다.
    wanted = _comparable_key(alias_mode) or _comparable_key(request.mode)
    if not wanted:
        return console_type.modes
    return tuple(entry for entry in console_type.modes if fuzzy_type_equal(wanted, entry.name))


def _footprint_check(
    console_type: LibraryType | None,
    console_mode: LibraryMode | None,
    request: TypeRequest,
    *,
    footprint_enabled: bool,
) -> Mapping[str, object]:
    check: dict[str, object] = {
        "assumption_72": ASSUMPTION_72_GO if footprint_enabled else ASSUMPTION_72_NEGATIVE,
        "performed": False,
        "match": None,
        "presented_before_approval": False,
        "console_type": console_type.name if console_type is not None else None,
        "console_mode": console_mode.name if console_mode is not None else None,
        "designed_footprint": request.footprint,
        "console_channel_count": console_mode.channel_count if console_mode is not None else None,
        "source_path": (
            _channel_path(console_type, console_mode)
            if console_type is not None and console_mode is not None
            else None
        ),
        "reason": FOOTPRINT_DESCOPE_REASON,
    }
    if not footprint_enabled:
        return MappingProxyType(check)
    if console_mode is None:
        check["reason"] = "타입·모드가 확정되지 않아 점유폭을 대조하지 않았다."
        return MappingProxyType(check)
    if console_mode.channel_count is None:
        check["reason"] = (
            "콘솔에서 DMXChannels 자식 수를 읽지 못해 점유폭을 대조하지 않았다 — "
            "일치로 간주하지 않는다."
        )
        return MappingProxyType(check)
    if request.footprint is None:
        check["reason"] = "도면에 DMX Footprint 값이 없어 대조할 기준이 없다."
        return MappingProxyType(check)
    matched = console_mode.channel_count == request.footprint
    check["performed"] = True
    check["match"] = matched
    check["presented_before_approval"] = not matched
    check["reason"] = (
        "도면 DMX Footprint와 콘솔 DMXChannels 자식 수가 일치한다."
        if matched
        else "도면 DMX Footprint와 콘솔 DMXChannels 자식 수가 다르다 — 승인 전에 제시한다."
    )
    return MappingProxyType(check)


def _channel_path(console_type: LibraryType, console_mode: LibraryMode) -> str:
    return (
        f"{FIXTURE_TYPE_LIBRARY_ROOT}/{console_type.index}/{DMX_MODES_SEGMENT}/"
        f"{console_mode.index}/{DMX_CHANNELS_SEGMENT}"
    )


def _library_axis(library: FixtureTypeLibrary) -> str | None:
    """**라이브러리 목록**을 전수라고 말할 수 없게 만든 축. 말할 수 있으면 `None`.

    [round21 R20-B] `_library_incompleteness`에서 뽑아 올렸다. 이유는 축 이름이 두
    자리에서 갈리지 않게 하는 것이다: 이 축 이름은 `skipped_checks` 고지에도 실리고
    `ListCompleteness.incompleteness_kind`(= 목록 옆에 붙는 완전성 진술)에도 실리는데,
    판정이 두 곳에 있으면 같은 스냅샷을 한쪽은 절단, 한쪽은 폐기라 부를 수 있다.

    **순서가 규율이다**: 좁은 축을 먼저 본다. union 프로퍼티
    (`enumeration_incomplete` = 플래그 ∪ 계수 대조 ∪ 폐기)가 좁은 축을 흡수하므로,
    union을 먼저 보면 폐기 전용 축에 **영영 도달하지 못한다**(= 도달 불가가 된 분류,
    R18-C·R18-E와 같은 계열). 새 축을 더할 때도 union보다 **앞에** 둔다.
    """
    if not library.available:
        return FIXTURE_TYPE_LIBRARY_UNREADABLE
    # [round21 R20-D] **폐기를 union보다 먼저 본다.** `enumeration_incomplete`가 폐기까지
    # 논리합으로 삼키므로, 뒤에 두면 폐기 전용 축에 영영 도달하지 못한다 — 그러면 조작자는
    # 효과 없는 재판독을 반복한다(같은 범위를 다시 읽어도 같은 행이 온다).
    if library.rows_discarded:
        return FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED
    # [round21 R20-A ⓐ] 플래그 단독이 아니라 **플래그 ∪ 계수 대조**로 판정한다 —
    # `truncated=false`인데 `childCount != 반환 행 수`인 스냅샷을 구판은 전수로 읽었다.
    if library.enumeration_incomplete:
        return FIXTURE_TYPE_LIBRARY_TRUNCATED
    return None


def _mode_axis(console_type: LibraryType) -> str | None:
    """**한 타입의 모드 목록**을 전수라고 말할 수 없게 만든 축. `_library_axis`의 형제.

    순서 규율은 `_library_axis`와 같다 — 좁은 축을 union보다 앞에 둔다.
    """
    if not console_type.modes_available:
        return FIXTURE_TYPE_LIBRARY_UNREADABLE
    # [round21 R20-D] 루트와 같은 순서 규율 — 폐기가 union보다 앞이다.
    if console_type.mode_rows_discarded:
        return FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED
    if console_type.modes_incomplete:
        return FIXTURE_TYPE_LIBRARY_TRUNCATED
    return None


def _library_incompleteness(
    library: FixtureTypeLibrary, console_type: LibraryType | None
) -> str | None:
    """두 축의 합 — 라이브러리 축이 먼저다(타입을 못 고른 이유가 상위에 있으면 그것이 답).

    [round21 R20-B] 이름·서명은 그대로 두고 본문만 두 축 함수로 위임한다. 호출자
    (`_resolve_one` 넷)가 이 이름으로 처분을 정하고 있어, 이름을 바꾸면 그 넷의 갈래
    전수 게이트가 함께 움직인다 — 이번 반영의 축소 대상이 아니다.
    """
    axis = _library_axis(library)
    if axis is not None or console_type is None:
        return axis
    return _mode_axis(console_type)


def _incompleteness_reason(kind: str) -> str:
    if kind == FIXTURE_TYPE_LIBRARY_UNREADABLE:
        return LIBRARY_UNREADABLE_REASON
    if kind == FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED:
        return LIBRARY_ROWS_DISCARDED_REASON
    return LIBRARY_TRUNCATED_REASON


def _library_rows_discarded(library: FixtureTypeLibrary) -> int:
    """라이브러리 전체의 **폐기 축** 합계 — 루트 행과 모드 행을 함께 센다."""
    return library.rows_discarded + sum(entry.mode_rows_discarded for entry in library.types)


def _library_observed_axes(library: FixtureTypeLibrary) -> frozenset[str]:
    """이 스냅샷에서 **동시에 참인** 관측 축 전부. `_library_axis`의 집합판이다.

    [round21 R20-D] 처분(`incompleteness_kind`)은 칸이 하나라 축을 하나만 고르지만,
    고지는 다르다: 절단·폐기·판독실패는 **조치가 서로 다르므로**(표적 스윕 · responder
    확인 · 재시도) 함께 참이면 함께 나가야 한다. 하나로 뭉개면 조작자는 남은 조치를
    모른 채 한 가지만 시도하고, 그것이 효과가 없으면 원인을 잘못 짚는다.

    절단 축은 union 프로퍼티(`enumeration_incomplete`)가 **아니라** 그 두 갈래
    (`truncated` · `enumeration_short`)를 본다. union은 폐기까지 논리합으로 삼키므로,
    union을 쓰면 폐기만 있는 스냅샷에서 "열거에 미관측분이 남았다"는 **없는 사실**을
    고지하게 된다 — 축을 가르려고 만든 자리에서 축을 다시 뭉개는 셈이다.
    """
    axes: set[str] = set()
    if not library.available:
        axes.add(FIXTURE_TYPE_LIBRARY_UNREADABLE)
    if library.rows_discarded:
        axes.add(FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED)
    if library.truncated or library.enumeration_short:
        axes.add(FIXTURE_TYPE_LIBRARY_TRUNCATED)
    for entry in library.types:
        if not entry.modes_available:
            axes.add(FIXTURE_TYPE_LIBRARY_UNREADABLE)
        if entry.mode_rows_discarded:
            axes.add(FIXTURE_TYPE_LIBRARY_ROWS_DISCARDED)
        if entry.modes_truncated or entry.modes_enumeration_short:
            axes.add(FIXTURE_TYPE_LIBRARY_TRUNCATED)
    return frozenset(axes)


def _absence_assertable(console_type: LibraryType | None) -> bool:
    """이 타입의 모드 목록을 **전수로 실측했다**고 말할 수 있는가.

    [round20 R20-D] 이 술어의 전제는 구판에서 흩어져 있었다: 하나는 `_resolve_one`의
    인라인 표현식에, 하나는 80줄 위 조기 반환에, 하나(**폐기된 행이 없음**)는 어디에도
    없었다. 그래서 `i` 없는 행이 섞인 스냅샷에서 "모드 열거를 전부 읽었고 절단도
    없었다"는 **거짓 사유**와 함께 하드 스톱이 나갔다. 전제를 한 자리에 모으고 등기부를
    붙인다 — `server/tests/test_autopatch_types.py`의 round21 절이 이 함수의 AST에서
    전제를 뽑아 등기부와 전단사를 단정한다.

    목록 완전성 갈래는 `modes_incomplete`(플래그 ∪ 계수 대조 ∪ 폐기)와 **같은 셋**이다.
    union을 부르지 않고 갈래를 펼치는 이유는 등기부다: 갈래마다 지워 보는 뮤테이션이
    성립해야 하고, `modes_incomplete`에 갈래가 늘면 등기 전수와 어긋나 그 자리에서 먼저
    실패한다. 두 층이 조용히 갈라지는 길을 막는다.
    """
    if console_type is None:
        return False
    return (
        console_type.modes_available
        and not console_type.modes_truncated
        and not console_type.modes_enumeration_short
        # [round23 R22-B] 반대 방향도 전제다. 관측이 총계를 **넘은** 스냅샷에서
        # "전 모드를 실측했다"고 말하면 그것도 근거 없는 긍정 주장이다 —
        # `modes_incomplete` union에 갈래가 늘었으므로 등기 전단사가 여기를 강제한다.
        and not console_type.modes_over_enumerated
        # `== 0`이 아니라 `not`이다 — 이 저장소의 구조 게이트가 이름 토큰이 실린 항등
        # 비교를 전부 막는다(`equality_confirmation_locations`). 의미는 같다.
        and not console_type.mode_rows_discarded
        and all(mode.channel_count is not None for mode in console_type.modes)
    )


def _row_sequence(value: object) -> tuple[object, ...]:
    """행 **전부**(매핑이 아닌 것 포함) — `_mapping_rows`의 분모다.

    [round21 R20-D] `_mapping_rows`는 매핑이 아닌 행을 계수 없이 버린다. 그 행도 payload가
    실어 온 행이므로 "몇 개가 왔는가"의 분모에는 들어가야 한다. 빼면 폐기가 절단 축으로
    새어 조작자가 responder 문제에 표적 스윕을 돌린다. 형제 `patchplan._row_sequence`와
    같은 함수이고 **이름까지 같게** 둔다.
    """
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(value)


def _skipped_check(kind: str, reason: str, **extra: object) -> dict[str, object]:
    check: dict[str, object] = {
        "kind": validate_autopatch("skipped_check_kind", kind),
        "label": skipped_check_label(kind),
        "reason": reason,
    }
    check.update(extra)
    return check


def _read_type(
    port: LibraryPort, index: int, listed: str, *, read_channel_counts: bool
) -> LibraryType:
    modes_path = f"{FIXTURE_TYPE_LIBRARY_ROOT}/{index}/{DMX_MODES_SEGMENT}"
    state = port.query_state(modes_path)
    if state.get("ok") is not True:
        return LibraryType(index=index, name=listed, modes_available=False)
    # [round21 R20-A ⓐ] 모드 열거도 같은 계수 대조를 받는다 — 추가 질의 0회.
    node = state.get("node")
    mode_child_count = _optional_int(node.get("childCount")) if isinstance(node, Mapping) else None
    rows = _mapping_rows(state.get("children"))
    # [round21 R20-D] 모드 열거도 루트와 **같은 폐기 계수 규율**을 받는다 — 한 모듈 안에서
    # 규율이 갈리는 것이 R20-A·R20-D를 함께 낳은 기제다.
    raw_rows = _row_sequence(state.get("children"))
    unparsable_mode_rows = len(raw_rows) - len(rows)
    unusable_mode_rows = 0
    seen_mode_slots: set[int] = set()
    modes: list[LibraryMode] = []
    for child in rows:
        mode_index = _optional_int(child.get("i"))
        if mode_index is None or mode_index in seen_mode_slots:
            unusable_mode_rows += 1
            continue
        seen_mode_slots.add(mode_index)
        mode_path = f"{modes_path}/{mode_index}"
        mode_name = _read_mode_name(port, mode_path) or _optional_string(child.get("name")) or ""
        channel_count = _read_channel_count(port, mode_path) if read_channel_counts else None
        modes.append(LibraryMode(index=mode_index, name=mode_name, channel_count=channel_count))
    return LibraryType(
        index=index,
        name=listed,
        modes=tuple(modes),
        modes_truncated=state.get("truncated") is True,
        mode_child_count=mode_child_count,
        modes_enumerated_count=len(modes),
        returned_mode_row_count=len(raw_rows),
        unusable_mode_row_count=unusable_mode_rows,
        unparsable_mode_row_count=unparsable_mode_rows,
    )


def _read_mode_name(port: LibraryPort, mode_path: str) -> str | None:
    response = port.query_property(mode_path, MODE_NAME_PROPERTY)
    if response.get("ok") is not True:
        return None
    return _optional_string(response.get("value"))


def _read_channel_count(port: LibraryPort, mode_path: str) -> int | None:
    state = port.query_state(f"{mode_path}/{DMX_CHANNELS_SEGMENT}")
    if state.get("ok") is not True:
        return None
    node = state.get("node")
    if not isinstance(node, Mapping):
        return None
    return _optional_int(node.get("childCount"))


def _assumption_72_or_default(value: str | None) -> str:
    if value is None:
        return ASSUMPTION_72_NEGATIVE
    if value not in ASSUMPTION_72_VALUES:
        raise ValueError(
            f"assumption_72 must be one of {sorted(ASSUMPTION_72_VALUES)}, got {value!r}"
        )
    return value


def _mapping_rows(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(row for row in value if isinstance(row, Mapping))


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
