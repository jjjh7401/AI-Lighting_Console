from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from typing import NamedTuple

from server.design.cue_density import plan_cue_density, rotate_palette
from server.design.cue_fade import CUE_FADE_KEYWORD, store_with_fade
from server.design.energy import beats_to_seconds
from server.fx.instantiate import is_programmer_state
from server.looks.busking import VALUE_LINE_COLLISION, looks_for_genre
from server.looks.instantiate import _values_line
from server.looks.movement import (
    BAND_ORDER,
    MOVEMENT_STILL,
    MovementError,
    MovementPlan,
    band_for_dynamics,
    plan_movement,
)
from server.looks.resolver import GroupCandidate, RoleResolution, UnmappedRole, resolve_roles
from server.looks.schema import DYNAMICS_MAX, DYNAMICS_MIN, AttributeValue, Look, LookLibrary
from server.looks.section_fade import SectionFade, fade_for_label
from server.looks.section_intent import SectionIntent, intent_for_label, sorted_candidates
from server.looks.section_vocab import (
    ROW_CHORUS,
    SECTION_TERMS,
    matched_section_terms,
    resolve_section_dynamics,
)

_MILLISECONDS_PER_SECOND = Decimal("1000")
_SECONDS_PER_MINUTE = Decimal("60")
_MILLISECONDS_PER_MINUTE = 60_000
_MMSS_PATTERN = re.compile(r"^(?P<minutes>\d+):(?P<seconds>\d{2})(?P<fraction>\.\d{1,3})?$")
_SECONDS_PATTERN = re.compile(r"^\d+(?:\.\d+)?$")
_NAME_KEYS = ("name", "section", "label")
_START_KEYS = ("start", "start_time", "time")
EXPLICIT_DYNAMICS_REQUIRED = "explicit_dynamics_required"
UNMAPPED_LOOK = "unmapped_look"
SEQUENCE_UNAVAILABLE = "sequence_unavailable"
SEQUENCE_TRUNCATED = "sequence_truncated"
SEQUENCE_NUMBER_UNAVAILABLE = "sequence_number_unavailable"
EMPTY_SECTIONS = "empty_sections"
ROLE_UNMAPPED = "role_unmapped"
#: 이 구간이 앞 곡들이 이미 쓴 룩을 **다시** 골랐다는 표시 — 그 세기에 남은 룩이
#: 하나도 없었다는 뜻이다(정본 §7: 곡 사이 재사용은 결함). 큐는 그래도 나간다:
#: 재사용으로 내려앉는 것은 받아들이되, **조용히** 내려앉지는 않는다.
LOOK_POOL_EXHAUSTED = "look_pool_exhausted"
#: 이 큐가 선언된 움직임을 못 낸 이유. 셋 다 「조용히 버렸다」의 반대말이다 — 버리는
#: 것이 카드 t357 이 없애려는 결함이므로, 못 낸 것은 이름과 함께 밖으로 나간다.
MOVEMENT_BAND_STILL = "movement_band_still"
MOVEMENT_TURN_BOUNDARY = "movement_turn_boundary"
MOVEMENT_LINE_COLLISION = "movement_line_collision"
#: 드롭 앞 큐에서 밝기를 못 뺀 네 갈래(정본 §8 [HARD], 카드 t363). 넷 다 「조용히
#: 안 했다」의 반대말이다 — 안 한 것은 이름과 함께 밖으로 나간다.
#:
#: * :data:`DARKNESS_NO_PRECEDING_CUE` — 드롭이 곡의 **첫 구간**이다. 뺄 앞 큐가 없다.
#: * :data:`DARKNESS_SIX_ROW_ABSENT` — 앞 구간의 라벨에 §6 행이 없어 **얼마나 어두워야
#:   하는지**를 정본이 주지 않았다. 행을 지어내지 않는다(``section_intent`` 의 규율).
#: * :data:`DARKNESS_SAME_SIX_ROW` — 앞 큐가 드롭과 **같은 §6 행**(chorus · drop)이다.
#:   정본이 그 행 전체를 80~100% 에 두므로 여기서 뺄 수 있는 것은 「어둠」이 아니라
#:   절정 안쪽의 작은 요철이고, §8 이 말하는 눈의 리셋은 그것으로 일어나지 않는다.
#: * :data:`DARKNESS_ALREADY_DARK` — 앞 큐가 이미 그 행의 바닥 이하다. 정본이 요구한
#:   밸리가 **이미 있다** — 더 빼는 것은 정본에 없는 일이다.
#: * :data:`DARKNESS_NO_DIMMER` — 앞 큐의 룩에 ``Dimmer`` 가 없다. 없는 축에 값을
#:   만들어 보내지 않는다(``escalate_attributes`` 와 같은 규율).
DARKNESS_NO_PRECEDING_CUE = "pre_drop_darkness_no_preceding_cue"
DARKNESS_SIX_ROW_ABSENT = "pre_drop_darkness_six_row_absent"
DARKNESS_SAME_SIX_ROW = "pre_drop_darkness_same_six_row"
DARKNESS_ALREADY_DARK = "pre_drop_darkness_already_dark"
DARKNESS_NO_DIMMER = "pre_drop_darkness_no_dimmer"
#: 감광이 실렸는데 그 큐가 **저장되지 않은** 경우. 감광은 값 라인을 바꾸므로 저장/건너뜀
#: 판정에 참여한다 — 어두워진 큐가 앞 큐와 값이 같아 건너뛰어질 수 있고, 그러면 §8 이
#: 요구한 밸리는 무대에 없다. 적용 기록을 조용히 남겨 두면 있는 것처럼 읽힌다.
DARKNESS_CUE_NOT_STORED = "pre_drop_darkness_cue_not_stored"
_DESTINATION = "ChangeDestination Root"
_CLEAR = "ClearAll"
_IMPLICIT_SYSTEM_CUE_COUNT = 2
TIMECODE_DESCOPE = "timecode_descope"
AUTO_ADVANCE_DESCOPE = "auto_advance_descope"
TRIGGER_TYPE_TIME = "Time"

#: 변형 표시로 고정한 표기 하나 — SALAMI 프라임(U+2032). 정본 §3 이 표기 셋(프라임 ·
#: RWC 의 A·B · Harmonix 숫자 접미사) 중 하나를 골라 고정하라고 지시한다. ASCII
#: 어포스트로피는 일부러 제외한다: MA3 명령줄의 인용 문자라서 라벨 어휘로 쓰면 큐 이름
#: 조립과 충돌한다.
VARIANT_PRIME = "′"

#: 아껴두기 사다리의 칸 이름, 회차마다 하나씩만 더하는 순서 그대로(정본 §7.1).
#:
#: **고쳐 적음(카드 t378)** — 이 자리는 원래 "블라인더·스트로브는 역할 어휘에 이름이
#: 없다(카드 t356, 감독 결정 선행)" 를 이유로 마지막 두 칸을 뺐다. 그 이유는 만료됐다 —
#: 카드 t356 이 2026-09-12 에 감독 승인으로 :mod:`server.looks.roles` 를 열어
#: `블라인더`·`스트로브` 가 이름을 얻었고, 실기 리그도 `BLIND`·`STROBE` 그룹을 낸다
#: (`test_looks_resolver.py::TestLxseqRigCoverage` 의
#: `test_the_ladder_rungs_the_standard_needs_are_callable` 가 이미 실측한다). 그래서
#: :data:`LADDER_BLINDER_OR_FLASH` 를 더한다 — chorus 3 이 더하는 칸(§7.1 표).
#:
#: `Pan`/`Tilt` 무빙 포지션 전환은 **아직도** 이 사다리의 칸이 아니다 — 다만 이유가
#: 바뀌었다. v1 은 이제 movement 를 낸다(카드 t357, :class:`MovementPlan`), 그런데 그
#: 통로는 **구간마다 하나**를 고르는 별도 층(:func:`_movement_carrier`)이지 반복
#: 회차마다 쌓는 사다리가 아니다. 두 층을 하나로 합치면 "밝기만 누적한다"(§6.1 [HARD])
#: 는 이 사다리의 규율과 "그 구간에서 저장되는 큐 하나만 움직인다"는 :func:`_movement_carrier`
#: 의 규율이 서로 다른 축인데도 한 필드를 다투게 된다.
#:
#: **색 스냅은 SPEC-LDCLIMAX-001(2026-09-20 감독 결정) 이후 이 사다리의 정규 칸이다**
#: (:data:`LADDER_COLOR_SNAP`). 고치기 전에는 "색 스냅도 뺀다 — 정본 §7 이 「코러스
#: 1의 색은 되돌아와야 한다」고 못박으므로 지배색을 갈아치우는 것은 상승이 아니라
#: 위반이다"였다 — 그 판단은 "색 스냅"을 §7.1 아껴두기 사다리의 에스컬레이션 칸
#: (회차마다 지배색을 새로 갈아치우는 것)으로 읽었을 때의 결론이다. SPEC-LDCLIMAX-001
#: 은 다른 정의를 쓴다: §7 이 이미 돌아오라고 요구하는 색(코러스 1이 쓴 색)을 즉시
#: 전환(페이드 0)으로 내는 것 — 새 색을 만들지 않으므로 §7 을 어기지 않는다. 이
#: 칸도 블라인더처럼 이 룩 자신의 값 라인은 바꾸지 않는다(:func:`_rung_applied`)
#: — 색은 이미 룩 자신이 들고 있는 값 그대로이고, 이 칸이 더하는 것은 페이드를
#: 0 으로 강제하는 것뿐이다(REQ-LDCLIMAX-003).
#:
#: 스트로브(앙코르·피날레 칸)는 이 목록에 **없다** — :data:`LADDER_STROBE_HIT` 로 따로
#: 두는 이유는 :func:`_climb_rungs` 독스트링에 적는다.
LADDER_DIMMER_HIT = "dimmer_hit"
LADDER_ZOOM_PINCH = "zoom_pinch"
LADDER_IRIS_PINCH = "iris_pinch"
#: chorus 3 이 더하는 칸(정본 §7.1 표 「블라인더 또는 백색 플래시」). 이 룩 자신의 값을
#: 안 바꾸는 유일한 칸이다 — 블라인더는 다른 그룹(:data:`server.looks.roles`의
#: `블라인더`)이라 :func:`_rung_applied` 가 이 칸에서 ``values`` 를 그대로 돌려주고,
#: 실제 명령은 :func:`_accent_fixture_commands` 가 사다리와 별도로 만든다. 그래도
#: :data:`LADDER_RUNGS`·``ladder`` 보고에는 실린다 — 「이 큐가 블라인더를 켰다」는 사실은
#: 보고할 것이지 값 라인 계산 안에 숨길 것이 아니다.
LADDER_BLINDER_OR_FLASH = "blinder_or_flash"
#: 색 스냅(SPEC-LDCLIMAX-001 REQ-LDCLIMAX-001) — 찍는 액센트 사다리의 마지막 후보.
#: 기존 네 칸(줌→블라인더→아이리스[→스트로브])보다 우선하지 않고, 대체도 병행도
#: 아닌 같은 회전의 한 후보다(2026-09-20 감독 결정, `plan.md §NC`). 스트로브와
#: 반대 극성이다 — ``disable_color_snap=True`` 로 명시적으로 끄지 않는 한 항상
#: 회전 후보다(REQ-LDCLIMAX-012 는 첫 실기 콘솔 검증 세션까지의 임시 킬스위치).
LADDER_COLOR_SNAP = "color_snap"
LADDER_RUNGS: tuple[str, ...] = (
    LADDER_DIMMER_HIT,
    LADDER_ZOOM_PINCH,
    LADDER_IRIS_PINCH,
    LADDER_BLINDER_OR_FLASH,
    LADDER_COLOR_SNAP,
)

#: 앙코르·피날레 칸(정본 §7.1 표 마지막 줄) — 처음으로 스트로브를 푼다.
#: :data:`LADDER_RUNGS` 에 안 넣는 이유는 §7.1 자신이 적은 조건 때문이다: "클라이맥스
#: 브레이크다운이나 세트 피날레까지 보류" 하고 "처음 두 곡에 최고의 트릭을 다 노출하지
#: 않는" 것. 이 파일은 **한 곡**만 본다 — 몇 번째 곡인지, 이 공연의 세트가 어디까지
#: 왔는지는 이 함수의 입력에 없다(``build_songcue_bundle`` 은 ``selections`` 와 리그
#: 정보만 받는다). 그 신호를 지어내는 대신 :func:`_distinct_values_line` 이 받는
#: ``allow_strobe`` 인자로 **호출자가 밝힌 자리**에서만 사다리 후보에 넣는다 — 곡이
#: 몇 번째인지 세는 일은 여전히 안 하고, 세션이 알려주지 않으면 이 칸은 그냥 없는
#: 칸처럼 동작한다(스트로브 없이도 사다리는 밝기·블라인더로 계속 오른다).
LADDER_STROBE_HIT = "strobe_hit"

#: 드롭 구조 회수(카드 t366)가 **물러선** 큐에 붙이는 표시 — 위 세 칸과는 별개다.
#: :data:`LADDER_RUNGS` 에는 넣지 않는다: 이것은 오르는 사다리의 칸이 아니라, 드롭이
#: 천장에서 충돌해 마지막 수단으로 버려지려 할 때 **드롭이 아닌** 상대 큐를 한 칸
#: 물려 자리를 비키는 표시다. 물러서는 폭·방향은 :data:`_HIT_STEP` 그대로, 바닥은
#: :data:`DARKNESS_FLOOR` 다(정본 §8 안전 바닥 — 감광이 못 내려가는 자리를 이 물러섬도
#: 넘지 않는다).
LADDER_DIMMER_YIELD = "dimmer_yield"

_DIMMER = "Dimmer"
_ZOOM = "Zoom"
_IRIS = "Iris"
#: 한 칸이 움직이는 폭과 그 방향의 한계. 밝기는 천장을 향해 오르고(정본 §6: 코러스·드롭은
#: 80~100%), 줌·아이리스는 좁아지는 쪽으로 내려간다(§6 「점점 좁힘」).
_HIT_STEP = 5
_PINCH_STEP = -5
_DIMMER_CEILING = 100
_BEAM_FLOOR = 1
#: **찍는 액센트** — 정본 §6.1 의 일곱 중 오늘의 어휘가 실제로 발화하는 셋(카드 t378 이전엔
#: 둘). 한 큐에 **하나**만 실린다(감독 결정 2026-09-12: 밝기만 누적하고 나머지는 큐당
#: 하나). 회차가 깊어지면 쌓지 않고 **갈아탄다** — 그래서 여기는 순서 있는 목록이고,
#: 깊이가 그 안을 돈다. 스트로브는 이 튜플에 **없다** — ``allow_strobe`` 가 참인 자리에서만
#: :func:`_marking_accents` 가 네 번째 자리로 더한다(:data:`LADDER_STROBE_HIT` 독스트링).
#:
#: **순서는 취향이 아니라 사다리의 충돌 구조가 강제한다.** 깊이 2(3회차)는 깊이 1
#: (2회차)과 밝기 히트 개수가 **똑같다**(``_climb_rungs`` 의 ``hits = depth - 1``이
#: 1과 2에서 둘 다 1) — 그래서 깊이 2가 값 라인에서 유일해지려면 **액센트 자신이
#: 값을 바꿔야** 한다. 블라인더는 이 룩 자신의 값을 안 바꾸는 칸이라(``_rung_applied``)
#: 첫 자리에 두면 깊이 2가 깊이 1과 완전히 같은 값이 되어 매번 충돌하고, 사다리는
#: 조용히 깊이 3으로 건너뛴다 — chorus 3 은 블라인더를 한 번도 못 켜 본다(실측:
#: 이 조정 전에는 3회차 셋짜리 곡에서 블라인더가 전혀 안 나갔다). 깊이 3부터는 밝기
#: 히트 개수가 2·3·4… 로 **그 자체가 유일**하므로, 값을 안 바꾸는 칸을 놓아도
#: 충돌하지 않는다. 그래서 값을 바꾸는 줌이 첫 자리(깊이 2, 정본 §7.1 표의 chorus 3
#: 자리를 그대로 지킨다 — 고치기 전 회귀 없음), 블라인더는 둘째 자리(깊이 3, 4회차)
#: 다. **정본 §7.1 표가 "chorus 3 = 블라인더"라고 적은 자리를 이 사다리는 그대로
#: 못 지킨다** — 충돌-회피 구조가 먼저이기 때문이다. 대신 지키는 것은 §7.1 이 요구
#: 하는 **성질**(회차가 깊어질수록 다른 요소를 더한다, 액센트는 큐당 하나, 밝기만
#: 누적)이다. 곡마다 반복 횟수가 다르므로 "정확히 3회차"라는 표의 문구를 이 계층이
#: 보장할 수 없다는 것은 미검증 잔여 위험으로 남긴다(카드 t378 보고 참조).
_MARKING_ACCENTS: tuple[str, ...] = (
    LADDER_ZOOM_PINCH,
    LADDER_BLINDER_OR_FLASH,
    LADDER_IRIS_PINCH,
)

#: 찍는 액센트 칸 이름 -> 그 칸이 겨냥하는 **룩 자신의** 속성. 줌·아이리스만 여기
#: 있다 — 블라인더·스트로브는 이 룩의 값을 안 바꾸는 다른 그룹이라(:data:`_ACCENT_FIXTURE_ROLE`)
#: 효과 판정이 축이 아니라 리그의 그룹 보유로 갈린다(:func:`_accent_is_effective`).
_MARKING_ACCENT_AXIS: dict[str, str] = dict(
    ((LADDER_ZOOM_PINCH, _ZOOM), (LADDER_IRIS_PINCH, _IRIS))
)

#: 유보 사유(SPEC-LDACCENT-001) — 그 회차·그 룩+리그+라벨 조합에서 유효한 찍는
#: 액센트 후보가 하나도 남지 않았다. 어느 축이 없었는지·어느 그룹이 없었는지는
#: :func:`_no_effective_candidate_detail` 이 ``detail`` 에 적는다.
ACCENT_NO_EFFECTIVE_CANDIDATE = "accent_no_effective_candidate"


def _look_has_attribute(look: Look, attribute: str) -> bool:
    """룩 자신의 값 라인에 그 속성이 실려 있는지 — 없으면 이 칸은 이 룩에서 무영향이다."""
    return any(value.name == attribute for value in look.attributes)


#: 색 스냅이 비교·강제하는 채널 — 리그 색 스키마의 확정 세 채널(`server/looks/
#: schema.py` ``CONFIRMED_ATTRIBUTES``)과 같은 순서. 이 모듈 안에서 따로 적는 이유는
#: ``Dimmer`` 를 뺀 색 채널만 필요하기 때문이다(REQ-LDCLIMAX-002/004, D3).
_COLOR_ATTRIBUTES: tuple[str, ...] = ("ColorRGB_R", "ColorRGB_G", "ColorRGB_B")


def _look_color(look: Look) -> tuple[AttributeValue, ...]:
    """이 룩이 싣는 ColorRGB_* 값, 정본 채널 순서 그대로 — 없는 채널은 빠진다.

    색 채널이 하나도 없으면 빈 튜플이다 — 색 스냅은 그 갈래에서 무영향으로
    판정된다(``_color_snap_is_effective``), 없는 축에 값을 만들어 보내지 않는
    :func:`_look_has_attribute` 와 같은 규율이다.
    """
    return tuple(value for value in look.attributes if value.name in _COLOR_ATTRIBUTES)


def _color_snap_is_effective(
    look: Look,
    *,
    section: SongCueSection,
    previous_color: tuple[AttributeValue, ...] | None,
    label_palette: frozenset[tuple[AttributeValue, ...]],
) -> bool:
    """색 스냅의 셋째 판정 축(REQ-LDCLIMAX-002/004, SPEC-LDCLIMAX-001 D3) — 축
    보유(줌·아이리스)도 그룹 보유(블라인더·스트로브)도 아닌 **색 비교**다.

    ``previous_color`` 는 직전에 저장된 큐의 색(REQ-004 — 다르지 않으면 "스냅"이
    관측되지 않는다), ``label_palette`` 는 이 라벨의 1회차가 이미 쓴 색 집합
    (REQ-002 — §7 색 복귀 규율이 적용되는 반복 회차에서만, 그 집합 밖의 색은
    대상이 될 수 없다). 두 값 모두 호출자가 이미 곡 전체를 훑어 계산해 넘긴다
    (``_previous_stored_color``/``_label_return_palette``) — 이 함수 자신은
    곡 상태를 전역도 가변 기본값도 없이 명시 인자로만 받는다.
    """
    current = _look_color(look)
    if not current:
        return False
    if section.instance >= 2 and label_palette and current not in label_palette:
        return False
    return current != previous_color


def _accent_is_effective(
    rung: str,
    *,
    look: Look,
    resolution: RoleResolution,
    section: SongCueSection,
    previous_color: tuple[AttributeValue, ...] | None,
    label_palette: frozenset[tuple[AttributeValue, ...]],
) -> bool:
    """이 칸이 이 룩+이 리그+이 라벨에서 실제로 관측 가능한 효과를 내는지
    (REQ-LDACCENT-001~003, REQ-LDCLIMAX-002/004).

    줌·아이리스는 **룩 자신의 값 라인**을 바꾸는지(축 보유)로 판정한다. 블라인더·
    스트로브는 **별도 무대 명령**이 실제로 나가는지로 판정한다 — 리그가 대응 그룹을
    갖는 것과, 이 큐가 속한 섹션의 라벨이 §6 행을 갖는 것 **둘 다**를 요구한다
    (:func:`_accent_fixture_commands` 가 실제로 명령을 내는 조건 그대로). 색 스냅은
    셋째 갈래(:func:`_color_snap_is_effective`)다 — 축도 그룹도 아닌 색 비교다.
    """
    axis = _MARKING_ACCENT_AXIS.get(rung)
    if axis is not None:
        return _look_has_attribute(look, axis)
    role = _ACCENT_FIXTURE_ROLE.get(rung)
    if role is not None:
        return bool(resolution.groups_for(role)) and intent_for_label(section.label) is not None
    if rung == LADDER_COLOR_SNAP:
        return _color_snap_is_effective(
            look, section=section, previous_color=previous_color, label_palette=label_palette
        )
    raise SongCueBundleError(f"unknown ladder rung: {rung!r}")


def _no_effective_candidate_detail(
    *,
    allow_strobe: bool,
    disable_color_snap: bool,
    look: Look,
    resolution: RoleResolution,
    section: SongCueSection,
    previous_color: tuple[AttributeValue, ...] | None,
    label_palette: frozenset[tuple[AttributeValue, ...]],
) -> str:
    """유보 기록의 ``detail`` (REQ-LDACCENT-005) — 후보 집합이 애초에 비었으면
    후보 전량의 무영향 사유를, 후보는 있었지만 전부 이미 나간 값과 겹쳐 탐색이
    소진됐으면 그 사실을 적는다. 두 갈래는 같은 유보 사유
    (:data:`ACCENT_NO_EFFECTIVE_CANDIDATE`)를 공유하고 여기서만 구분된다.
    """
    accents = _marking_accents(
        allow_strobe=allow_strobe,
        disable_color_snap=disable_color_snap,
        look=look,
        resolution=resolution,
        section=section,
        previous_color=previous_color,
        label_palette=label_palette,
    )
    if accents:
        return (
            f"effective candidates ({', '.join(accents)}) all collided with an "
            "already-emitted value line"
        )
    parts: list[str] = []
    for rung in (
        LADDER_ZOOM_PINCH,
        LADDER_BLINDER_OR_FLASH,
        LADDER_IRIS_PINCH,
        LADDER_STROBE_HIT,
        LADDER_COLOR_SNAP,
    ):
        if rung == LADDER_STROBE_HIT and not allow_strobe:
            continue
        if rung == LADDER_COLOR_SNAP and disable_color_snap:
            continue
        if rung == LADDER_COLOR_SNAP:
            parts.append(f"{rung}: no observable color change")
            continue
        axis = _MARKING_ACCENT_AXIS.get(rung)
        if axis is not None:
            parts.append(f"{rung}: no {axis} axis in look")
            continue
        role = _ACCENT_FIXTURE_ROLE[rung]
        if not resolution.groups_for(role):
            parts.append(f"{rung}: no {role} fixture group in rig")
        else:
            parts.append(f"{rung}: no six-row intent for label {section.label!r}")
    return "; ".join(parts)


# @MX:NOTE: [AUTO] 회전 후보는 회전 전에 걸러진다 — 무영향 칸(줌/아이리스 축
#   부재, 블라인더/스트로브 그룹 부재, §6 행 미매치, 색 무변화)은 이 함수를 거치는
#   모든 호출자(`_climb_rungs`·`_ensure_marking_accent`·`_max_climb`·
#   `_exhausted_rungs`·`_no_effective_candidate_detail`·`_finalize_marking_accents`)
#   에서 후보로 아예 보이지 않는다(SPEC-LDACCENT-001 §2, SPEC-LDCLIMAX-001 REQ-004).
def _marking_accents(
    *,
    allow_strobe: bool,
    disable_color_snap: bool,
    look: Look,
    resolution: RoleResolution,
    section: SongCueSection,
    previous_color: tuple[AttributeValue, ...] | None,
    label_palette: frozenset[tuple[AttributeValue, ...]],
) -> tuple[str, ...]:
    """이 사다리가 회전할 찍는 액센트 **후보** — 이 룩+이 리그+이 라벨에서 실제로
    관측 가능한 효과를 내는 칸으로만 미리 거른다(SPEC-LDACCENT-001 REQ-001~003,
    SPEC-LDCLIMAX-001 REQ-LDCLIMAX-001).

    ``allow_strobe`` 가 거짓이면 :data:`_MARKING_ACCENTS` 순서 그대로 필터만 거친다
    (고치기 전과 바이트 동일 — 필터가 아무것도 안 거르는 룩+리그+라벨 조합에서는).
    참이면 :data:`LADDER_STROBE_HIT` 를 네 번째 후보로 더해 같은 필터를 통과시킨다.
    ``disable_color_snap`` 이 거짓(기본값)이면 :data:`LADDER_COLOR_SNAP` 을 **맨 끝**
    후보로 무조건 더한다(REQ-LDCLIMAX-001) — 참이면 더하지 않는다(REQ-LDCLIMAX-012,
    첫 실기 콘솔 검증 세션까지의 임시 안전판). 무영향 칸(룩이 그 축을 안 실었거나,
    리그에 그 그룹이 없거나, 이 큐의 섹션 라벨에 §6 행이 없거나, 색이 §7 집합 밖
    이거나 직전 큐와 같은 칸)은 후보에서 아예 빠진다 — **회전 전, 회차별 값 결정
    전에** 적용한다(§2), 사후에 걸러내지 않는다.
    """
    candidates = _MARKING_ACCENTS if not allow_strobe else (*_MARKING_ACCENTS, LADDER_STROBE_HIT)
    if not disable_color_snap:
        candidates = (*candidates, LADDER_COLOR_SNAP)
    return tuple(
        rung
        for rung in candidates
        if _accent_is_effective(
            rung,
            look=look,
            resolution=resolution,
            section=section,
            previous_color=previous_color,
            label_palette=label_palette,
        )
    )


def _exhausted_rungs(
    *,
    allow_strobe: bool,
    disable_color_snap: bool,
    look: Look,
    resolution: RoleResolution,
    section: SongCueSection,
    previous_color: tuple[AttributeValue, ...] | None,
    label_palette: frozenset[tuple[AttributeValue, ...]],
) -> tuple[str, ...]:
    """건너뜀 사유 문면에 실을 칸 이름 전량 — 이 자리에서 실제로 후보였던 것만.

    ``LADDER_DIMMER_HIT`` 는 늘 후보이므로 무조건 더한다. 찍는 액센트는
    :func:`_marking_accents` 가 거른 유효 집합만 싣는다 — 무영향 칸까지 "실제로
    시도했다"는 거짓 주장을 사유 문면에 남기지 않기 위해서다(SPEC-LDACCENT-001).
    """
    return (
        LADDER_DIMMER_HIT,
        *_marking_accents(
            allow_strobe=allow_strobe,
            disable_color_snap=disable_color_snap,
            look=look,
            resolution=resolution,
            section=section,
            previous_color=previous_color,
            label_palette=label_palette,
        ),
    )


def _max_climb(
    *,
    allow_strobe: bool,
    disable_color_snap: bool,
    look: Look,
    resolution: RoleResolution,
    section: SongCueSection,
    previous_color: tuple[AttributeValue, ...] | None,
    label_palette: frozenset[tuple[AttributeValue, ...]],
) -> int:
    """오를 수 있는 깊이의 상한 — 밝기의 머리 공간(천장까지의 걸음 수)에 액센트
    갈아타기를 더한 것. 정본 §6 의 「마지막 드롭은 전 리그 최대」와 같은 방향이고,
    천장에서는 값이 더 안 움직이므로 유한하다: 그 지점에서 비로소 큐를 못 세운다
    (마지막 수단의 건너뜀). 액센트 개수가 ``allow_strobe``·``disable_color_snap``
    **그리고** 이 룩+리그+라벨에서 실제로 유효한 후보 수로 갈리므로 상한도 그만큼
    갈린다 — 무영향 칸을 분모에 넣은 채 상한을 계산하면 실제로는 못 오를 깊이까지
    "시도해볼 가치가 있다"고 잘못 보고한다(SPEC-LDACCENT-001).
    """
    return _DIMMER_CEILING // _HIT_STEP + len(
        _marking_accents(
            allow_strobe=allow_strobe,
            disable_color_snap=disable_color_snap,
            look=look,
            resolution=resolution,
            section=section,
            previous_color=previous_color,
            label_palette=label_palette,
        )
    )


#: **안전 바닥** — 감광 규칙이 내려갈 수 있는 가장 낮은 ``Dimmer`` 값(정본 §8 안전 한계).
#:
#: 이 값은 **정본 §6 표가 적은 가장 낮은 밝기**다: intro 행 20~40% 와 breakdown · bridge
#: 행 20~35% 의 아래끝이 둘 다 20 이고, 표 어디에도 그보다 낮은 숫자는 없다. 지어낸
#: 숫자가 아니라 인용이라는 것이 요점이다 — 이 저장소에는 **객석 형상도 광도 모형도
#: 없으므로**(실측: ``grep -rn "eye_height|눈높이|house_depth" server`` 0건,
#: ``server/looks/movement.py`` 머리에 기록) 「비상구 표지에 몇 lux 가 닿는다」는 주장은
#: 만들 수 없다. 만들 수 있는 것은 **우리가 얼마나 어둡게 만드는가의 상한**뿐이다.
#:
#: 이 바닥이 지키는 것과 안 지키는 것은 :func:`darkness_target` 독스트링에 적는다.
DARKNESS_FLOOR = 20

#: **프론트 필** — 위치 역할 하나(정본 §6.2 [HARD], 카드 t377). 감독 실기 관측
#: (2026-09-12): "무빙만하고 조명이 켜지지않은 장비도 있어" — verse 큐가 역할
#: ``배경``·``탑``·``무버``만 실어 프론트·백라이트·스페셜이 전부 침묵하고, 무빙헤드는
#: 돌아가는데 연주자는 어둡다. 정본 원문: "프론트 필은 밝은 워시가 아니라 **부드러운
#: 보정광으로 항상 유지**한다 — 없으면 연주자가 안 보이고 영상이 어둡게 나온다."
#:
#: "항상"은 **선택된 룩과 무관하다**는 뜻으로 읽는다 — 그래서 이 상수들은 룩 선택
#: 위에 얹는 층 하나로 쓰인다(:func:`_front_fill`). 개별 룩을 고쳐서 프론트를
#: 끼워 넣지 않는 이유는 그 룩이 열 개면 규칙도 열 곳에 흩어지기 때문이다.
FRONT_FILL_ROLE = "프론트"

#: 채우는 밝기 — :data:`DARKNESS_FLOOR` 를 그대로 쓴다. 새 숫자를 짓지 않는다.
#:
#: (가) §6.2 자신이 이 광원을 "밝은 워시의 반대"로 규정한다 — §6 표가 적은 가장
#: 어두운 값이 정확히 그 뜻에 맞는 인용이다. (나) §8 의 감광 바닥과 **같은 상수**를
#: 쓰면, 드롭 앞 감광 큐(:func:`_pre_drop_darkened`)에서 이 층이 §8 이 요구한 어둠을
#: 절대 넘어서지 않는다 — 두 숫자가 달랐다면 프론트 필이 감광보다 밝게 나가 카드
#: t363 의 불변식("어둠은 어둠으로 읽혀야 한다")을 깰 수 있었다.
FRONT_FILL_DIMMER = DARKNESS_FLOOR

#: 색 — "인트로 온기"(`server/looks/library/ballad.yaml` ``ballad-intro-warm``)가
#: 이미 같은 역할(프론트+스페셜)에 쓰는 부드러운 웜톤 그대로다. 새 색을 짓지 않고
#: 이 저장소에 이미 있는 "부드러운·따뜻한" 색을 재사용한다 — §6.2 가 요구하는
#: "부드러운 보정광"의 근거가 라이브러리 자산 하나로 이미 있다.
FRONT_FILL_COLOR: tuple[AttributeValue, ...] = (
    AttributeValue("ColorRGB_R", 100),
    AttributeValue("ColorRGB_G", 75),
    AttributeValue("ColorRGB_B", 52),
)

#: 사다리의 찍는 액센트가 켜는 기구 종류 역할 — chorus 3 은 블라인더, 앙코르는
#: 스트로브(정본 §7.1 표, 카드 t378). 값은 §6 행의 **아래끝**을 쓴다 — "마지막
#: 드롭 | 전 리그 + 백색 플래시 | 최대 | 여기서 풀어라"가 정본에서 유일하게
#: 최대치를 허가한 자리이고, 그 자리는 곡 전체가 다 쓴 뒤의 "마지막 드롭" 하나다.
#: 이 사다리는 그 자리가 아니라 반복되는 코러스/드롭 안이므로, 같은 §6 행의
#: **최소 보장값**(chorus·drop 행 80~100% 의 아래끝 80)을 쓴다 — 최대가 아니라
#: 최소를 고르는 것이 "자동으로 관객 전체를 최대 밝기로 쏘지 않는다"는 안전
#: 방향(연구 문서 19의 `audience_blind_or_strobe` 안전 노트: 낮은 값·수동 확인·
#: 안전 문구 필요)과 맞는다. 행이 없으면(:func:`intent_for_label` 이 ``None``)
#: 켜지 않는다 — 숫자를 지어내지 않는 것은 :data:`DARKNESS_FLOOR` 와 같은 규율이다.
#: ``dict()`` 는 취향이 아니다 — 이 모듈은 매핑 리터럴을 **한 개도** 두지 않는 규율이
#: 있다(``test_songcue_sections`` 가 AST 로 잰다).
_ACCENT_FIXTURE_ROLE: dict[str, str] = dict(
    ((LADDER_BLINDER_OR_FLASH, "블라인더"), (LADDER_STROBE_HIT, "스트로브"))
)


@dataclass(frozen=True)
class SongCueSection:
    name: str
    start_ms: int
    index: int
    dynamics: tuple[int, ...] | None
    requires_explicit_dynamics: bool
    label: str = ""
    instance: int = 1
    variant: str = ""
    """구간 하나를 적는 세 필드(정본 §3) — 라벨 + 회차 + 변형 표시.

    ``label`` 은 이름에서 변형 표시를 뗀 것, ``instance`` 는 **그 라벨의** 등장 순번(1부터),
    ``variant`` 는 변형이면 :data:`VARIANT_PRIME` 이고 아니면 빈 문자열이다. 조명 판정은
    ``label`` 로 의도를 정하고 ``instance`` 로 강도를 정한다.

    회차는 표준 데이터셋이 주지 않는다 — Harmonix 912곡 주석에서 1·2·3번째 후렴이 전부
    문자열 ``chorus`` 다. 그래서 후처리 카운터로 만들며, 그 카운터는
    :func:`_numbered_by_label` **하나**다.

    기본값이 「이름 없는 라벨 · 1회차 · 변형 없음」인 이유는 파서를 거치지 않고 손으로
    만드는 호출자(``server/web/session.py`` 의 타이밍 경로) 때문이다 — 그쪽은 회차를 쓰지
    않으므로 선언으로 1회차다.
    """


@dataclass(frozen=True)
class SongCueLookSelection:
    section: SongCueSection
    requested_dynamics: tuple[int, ...]
    look: Look | None = None
    reason: str | None = None
    dynamics_matches: tuple[Look, ...] = ()
    """요청한 다이내믹스에 맞는 룩 **전량**, 버스킹 순서 그대로.

    ``look`` 은 그 선두 — 리그를 모르는 자리에서 고를 수 있는 유일한 답이다.
    리그에 실제로 묶이는 룩을 이 중에서 고르는 것은 역할 해석을 가진
    ``_section_bundle`` 의 일이다. 기본값이 빈 튜플이므로, 이 필드 없이 만들어진
    선택(기존 호출자·테스트)은 예전과 똑같이 ``look`` 하나로 동작한다.
    """

    reuse_reason: str | None = None
    """앞 곡의 룩으로 내려앉았으면 :data:`LOOK_POOL_EXHAUSTED`, 아니면 ``None`` (카드 t358).

    ``reason`` 과 갈라 두는 이유는 둘이 반대말이기 때문이다 — ``reason`` 은 **룩이 없다**,
    이 필드는 **룩은 있는데 새것이 아니다**. 합치면 큐가 나가는 갈래와 안 나가는 갈래가
    한 문자열에 섞이고, 보고에서 둘을 다시 가를 방법이 없어진다.
    """


@dataclass(frozen=True)
class SongCueSkippedSection:
    section: SongCueSection
    cue_number: int
    reason: str
    detail: str = ""
    collides_with_section_index: int | None = None
    collides_with_cue_number: int | None = None


@dataclass(frozen=True)
class SongCuePreDropDarkness:
    """드롭 앞 큐 하나에서 실제로 뺀 밝기 (정본 §8 [HARD], 카드 t363).

    ``before`` 와 ``after`` 는 그 큐의 ``Dimmer`` 값이고, ``row`` 는 ``after`` 를 정한
    §6 행의 이름이다. 셋을 함께 드는 이유는 하나다 — 「감광했다」는 주장은 두 숫자와
    그 숫자를 정한 문면 없이는 확인할 수 없다.

    ``drop_cue_number`` 는 이 감광이 **누구를 위한 것인지**다. 없으면 보고에서 어느
    드롭이 커졌는지 되짚을 수 없다.
    """

    section: SongCueSection
    cue_number: int
    drop_cue_number: int
    row: str
    before: float
    after: float


@dataclass(frozen=True)
class SongCueWithheldDarkness:
    """드롭 앞에서 밝기를 **못 뺀** 자리 하나와 그 이유 (정본 §8).

    ``cue_number`` 가 ``None`` 인 갈래가 하나 있다 — 드롭이 곡의 첫 구간이라 앞 큐가
    아예 없는 경우(:data:`DARKNESS_NO_PRECEDING_CUE`). 그때도 기록은 남는다: 「앞 큐가
    없어서 안 했다」와 「해야 하는데 안 했다」는 다른 사실이고, 둘 다 안 적으면 같은
    침묵이 된다.
    """

    section: SongCueSection
    cue_number: int | None
    drop_cue_number: int
    reason: str
    detail: str = ""


@dataclass(frozen=True)
class SongCueFrontFill:
    """프론트 필로 이 큐가 **더한** 그룹과 값 (정본 §6.2 [HARD], 카드 t377).

    셋을 함께 드는 이유는 :class:`SongCuePreDropDarkness` 와 같다 — 「채웠다」는 주장은
    무엇을·얼마로 채웠는지 없이는 확인할 수 없다.
    """

    section: SongCueSection
    cue_number: int
    groups: tuple[int, ...]
    dimmer: float


@dataclass(frozen=True)
class SongCueAccentFixture:
    """사다리의 찍는 액센트가 켠 블라인더·스트로브 그룹 (정본 §7.1 표, 카드 t378).

    ``rung`` 은 :data:`LADDER_BLINDER_OR_FLASH` 또는 :data:`LADDER_STROBE_HIT` 둘 중
    하나다 — §6.1 [HARD]가 큐당 액센트 하나로 못박으므로 이 필드도 하나만 든다.
    """

    section: SongCueSection
    cue_number: int
    rung: str
    groups: tuple[int, ...]
    dimmer: float


@dataclass(frozen=True)
class SongCueSectionBundle:
    section: SongCueSection
    cue_number: int
    cue_name: str
    selection: SongCueLookSelection
    commands: tuple[str, ...] = ()
    skipped: tuple[SongCueSkippedSection, ...] = ()
    unmapped: tuple[UnmappedRole, ...] = ()
    bound: Mapping[str, tuple[GroupCandidate, ...]] | None = None
    ladder: tuple[str, ...] = ()
    """이 큐가 기준 룩에 더한 사다리 칸들 — 안 올랐으면 빈 튜플(정본 §7.1).

    밖으로 내는 이유는 보고 하나다: 값이 같아 사라졌던 큐가 이제 저장되므로, 무엇을 더해서
    달라졌는지가 안 보이면 감독은 「같은 룩이 두 번 나갔다」와 구별할 수 없다.
    """

    movement: MovementPlan | None = None
    """이 큐가 실제로 낸 움직임 — 안 냈으면 ``None`` (정본 §6.4, 카드 t357).

    한 번들에서 이 필드가 채워지는 큐는 **하나**다. 왜 하나뿐인지는
    :func:`_movement_carrier` 에 적어 둔다.
    """

    fade: SectionFade | None = None
    """이 큐의 ``CueFade`` — 정본이 이 라벨에 페이드를 안 줬으면 ``None`` (카드 t363).

    ``None`` 이면 ``Store`` 줄에 아무것도 안 붙고, 그 명령은 고치기 전과 바이트 동일하다.
    """

    darkness: SongCuePreDropDarkness | None = None
    """이 큐가 드롭 앞에서 실제로 뺀 밝기 — 안 뺐으면 ``None`` (정본 §8 [HARD]).

    못 뺀 경우는 여기가 아니라 :attr:`SongCueBundle.withheld_darkness` 로 나간다 —
    ``movement`` 와 ``withheld_movement`` 가 갈라져 있는 것과 같은 형상이다.
    """

    darkness_withheld: SongCueWithheldDarkness | None = None
    """이 큐에서 감광을 못 한 이유 — 조립 도중에만 알 수 있는 셋 중 하나.

    번들 수준의 :attr:`SongCueBundle.withheld_darkness` 가 이것을 걷어 간다. 여기에
    한 번 놓는 이유는 :func:`_section_bundle` 이 큐 하나만 보기 때문이고, 곡 전체를
    보는 판정(감광했는데 그 큐가 안 저장됨)은 걷어 가는 쪽에서 붙는다.
    """

    front_fill: SongCueFrontFill | None = None
    """이 큐가 프론트 필로 **더한** 그룹·값 — 채울 것이 없었으면 ``None`` (정본 §6.2
    [HARD], 카드 t377).

    룩이 이미 프론트를 실었으면(:func:`_front_fill` 이 채울 것이 없다고 판단) ``None``
    이다 — 그때는 값 라인 자체에 프론트가 이미 있으므로 이 필드가 비어 있는 것 자체가
    "채울 필요가 없었다"는 보고다.
    """

    accent_fixture: SongCueAccentFixture | None = None
    """이 큐가 사다리의 찍는 액센트로 켠 블라인더·스트로브 그룹 — 안 켰으면 ``None``
    (정본 §7.1 표, 카드 t378).

    ``ladder`` 가 :data:`LADDER_BLINDER_OR_FLASH`/:data:`LADDER_STROBE_HIT` 를 실어도
    이 필드가 ``None`` 일 수 있다 — 리그에 그 그룹이 없으면(:func:`_accent_fixture_commands`)
    칸은 회전했지만 무대에는 아무것도 안 나갔다는 뜻이고, 그 구분이 이 필드의 존재
    이유다.
    """

    accent_withheld: SongCueWithheldAccent | None = None
    """이 큐에서 찍는 액센트를 못 채운 이유 — 조립 도중에만 알 수 있는 셋 중 하나
    (SPEC-LDACCENT-001).

    번들 수준의 :attr:`SongCueBundle.withheld_accents` 가 이것을 걷어 간다 —
    :attr:`darkness_withheld` 와 :attr:`SongCueBundle.withheld_darkness` 가 갈라져
    있는 것과 같은 형상이다.
    """


@dataclass(frozen=True)
class SongCueWithheldMovement:
    """움직임을 선언했는데 못 낸 큐 하나와 그 이유.

    버리지 않고 내보내는 이유가 이 카드의 요점이다 — 고치기 전에는 룩의 movement 가
    **조용히** 사라졌고, 조용한 것이 결함이었다. 여기에 실리면 보고에서 읽힌다.
    """

    section: SongCueSection
    cue_number: int
    band: str
    reason: str
    detail: str = ""


@dataclass(frozen=True)
class SongCueWithheldAccent:
    """찍는 액센트를 낼 자리인데 유효한 후보가 하나도 없어 못 채운 큐 하나와 그 이유
    (SPEC-LDACCENT-001).

    회전이 후보를 고르기 전에 무영향 칸(룩이 그 축을 안 실었거나, 리그에 그 그룹이
    없거나, 이 큐가 속한 섹션 라벨에 §6 행이 없는 칸)을 미리 거르고 나면, 이 회차가
    회전할 후보가 하나도 남지 않을 수 있다. 그때 셀 이름을 지어내는 대신 여기에
    「냈어야 했는데 못 냈다」를 남긴다 — :class:`SongCueWithheldMovement`·
    :class:`SongCueWithheldDarkness` 와 같은 보고 패턴이다.
    """

    section: SongCueSection
    cue_number: int
    reason: str
    detail: str = ""


@dataclass(frozen=True)
class SongCueClimaxReturn:
    """절정 지속시간 상한이 끼워 넣은 복귀 큐 — 어느 절정 큐 뒤에, 몇 박 뒤에,
    무슨 이유로 삽입됐는지(SPEC-LDCLIMAX-001 REQ-LDCLIMAX-010).

    :class:`SongCueWithheldMovement`/:class:`SongCueWithheldDarkness`/
    :class:`SongCueWithheldAccent` 와 같은 "조립 중에만 아는 부가 사실을 명시적으로
    보고한다" 패턴을 따르되, 이것은 유보가 아니라 **삽입** 보고라 별도 클래스로
    둔다.
    """

    source_section: SongCueSection
    source_cue_number: int
    rung: str
    """:data:`LADDER_BLINDER_OR_FLASH` 또는 :data:`LADDER_STROBE_HIT` — 이 상한이
    적용되는 두 칸(design.md §2 대조표)."""
    cap_beats: float
    """2.0(백색 플래시) 또는 4.0(최강 효과) — 정본 §6 상한 값의 상한 끝."""
    inserted_cue_number: int
    inserted_start_ms: int


@dataclass(frozen=True)
class SongCueBundle:
    song_title: str
    sequence_number: int
    sequence_name: str
    commands: tuple[str, ...]
    sections: tuple[SongCueSectionBundle, ...]
    is_error: bool = False
    reason: str | None = None
    withheld_movement: tuple[SongCueWithheldMovement, ...] = ()
    withheld_darkness: tuple[SongCueWithheldDarkness, ...] = ()
    withheld_accents: tuple[SongCueWithheldAccent, ...] = ()
    climax_returns: tuple[SongCueClimaxReturn, ...] = ()
    """절정 지속시간 상한이 끼워 넣은 복귀 큐 전량 — 안 끼웠으면 빈 튜플
    (SPEC-LDCLIMAX-001 REQ-LDCLIMAX-010). ``withheld_movement``/``withheld_darkness``/
    ``withheld_accents`` 와 같은 자리, 같은 "조용히 넘어가지 않는다" 보고 규율이다.
    """

    @property
    def movement_sections(self) -> tuple[SongCueSectionBundle, ...]:
        return tuple(section for section in self.sections if section.movement is not None)

    @property
    def darkened_sections(self) -> tuple[SongCueSectionBundle, ...]:
        return tuple(section for section in self.sections if section.darkness is not None)

    @property
    def front_filled_sections(self) -> tuple[SongCueSectionBundle, ...]:
        """프론트 필이 실제로 그룹을 더한 큐들 (카드 t377)."""
        return tuple(section for section in self.sections if section.front_fill is not None)

    @property
    def accent_fixture_sections(self) -> tuple[SongCueSectionBundle, ...]:
        """블라인더·스트로브가 실제로 켜진 큐들 (카드 t378)."""
        return tuple(section for section in self.sections if section.accent_fixture is not None)

    @property
    def skipped(self) -> tuple[SongCueSkippedSection, ...]:
        return tuple(skipped for section in self.sections for skipped in section.skipped)

    @property
    def stored_sections(self) -> tuple[SongCueSectionBundle, ...]:
        return tuple(section for section in self.sections if section.commands)


@dataclass(frozen=True)
class SongCueTimingAxes:
    timecode_go: bool = True
    auto_advance_go: bool = True
    timecode_skip_reason: str = (
        "ASSUMPTION-20 is GO in M4; DESCOPE branch retained for future rerun"
    )
    auto_advance_skip_reason: str = (
        "ASSUMPTION-22 is GO in M4; DESCOPE branch retained for future rerun"
    )


@dataclass(frozen=True)
class SongCueTimingSkip:
    axis: str
    reason: str


@dataclass(frozen=True)
class SongCueTimingPlan:
    commands: tuple[str, ...]
    timecode_commands: tuple[str, ...] = ()
    auto_advance_commands: tuple[str, ...] = ()
    skipped_axes: tuple[SongCueTimingSkip, ...] = ()


class SectionTimeError(ValueError):
    def __init__(
        self,
        *,
        index: int,
        reason: str,
        previous_start_ms: int | None,
        start_ms: int,
        sections: Sequence[SongCueSection],
    ) -> None:
        self.index = index
        self.reason = reason
        self.previous_start_ms = previous_start_ms
        self.start_ms = start_ms
        self.sections = tuple(sections)
        super().__init__(
            f"section index {index} {reason}: start_ms={start_ms}, "
            f"previous_start_ms={previous_start_ms}"
        )


class SequenceNumberError(ValueError):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class SongCueBundleError(ValueError):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class _RawSection(NamedTuple):
    name: str
    start: object


def normalise_start_ms(raw: object) -> int:
    if isinstance(raw, str):
        value = raw.strip()
        match = _MMSS_PATTERN.fullmatch(value)
        if match is not None:
            minutes = int(match.group("minutes"))
            seconds = Decimal(match.group("seconds") + (match.group("fraction") or ""))
            if seconds >= _SECONDS_PER_MINUTE:
                raise ValueError(f"section seconds out of range: {raw!r}")
            return (minutes * _MILLISECONDS_PER_MINUTE) + _seconds_to_milliseconds(seconds)
        if _SECONDS_PATTERN.fullmatch(value):
            return _seconds_to_milliseconds(_decimal_from(value, raw))
        raise ValueError(f"unsupported section time format: {raw!r}")

    if isinstance(raw, bool):
        raise ValueError(f"unsupported section time format: {raw!r}")
    if isinstance(raw, int | float | Decimal):
        return _seconds_to_milliseconds(_decimal_from(str(raw), raw))

    raise ValueError(f"unsupported section time format: {raw!r}")


def parse_sections(
    raw_sections: Iterable[Mapping[str, object] | Sequence[object]],
) -> tuple[SongCueSection, ...]:
    sections = _numbered_by_label(
        tuple(_parse_section(raw, index) for index, raw in enumerate(raw_sections))
    )
    previous: SongCueSection | None = None
    for section in sections:
        if previous is not None:
            if section.start_ms < previous.start_ms:
                raise SectionTimeError(
                    index=section.index,
                    reason="starts_before_previous",
                    previous_start_ms=previous.start_ms,
                    start_ms=section.start_ms,
                    sections=sections,
                )
            if section.start_ms == previous.start_ms:
                raise SectionTimeError(
                    index=section.index,
                    reason="duplicates_previous_start",
                    previous_start_ms=previous.start_ms,
                    start_ms=section.start_ms,
                    sections=sections,
                )
        previous = section
    return sections


def map_sections_to_looks(
    sections: Iterable[SongCueSection],
    library: LookLibrary,
    genre: str,
    explicit_dynamics: Mapping[int, int] | None = None,
    *,
    used_look_ids: Iterable[str] = (),
) -> tuple[SongCueLookSelection, ...]:
    """구간마다 룩 하나. ``used_look_ids`` 는 **앞 곡들이 이미 쓴** 룩 id (카드 t358).

    정본 §7 후반 — 곡 사이에서 룩·고보·이펙트를 재사용하지 않는다. 그 기억은 이 함수가
    들지 않고(세션이 든다: :class:`server.looks.song_history.SongLookMemory`) **인자로
    들어온다**. 여기서 들면 한 곡을 만드는 동안 기억이 자라 후렴 2회차가 1회차를 피하게
    되고, 그것은 정본이 미덕이라 부른 축을 깨는 것이다.

    기본값이 빈 것이므로 기억 없이 부른 호출은 고치기 전과 **바이트 동일**하다 —
    피할 것이 없으면 아래 재배열이 항등이다.
    """
    ordered_looks = looks_for_genre(library, genre)
    # frozenset — 구간마다 다시 훑지 않고, 곡 하나를 만드는 동안 **안 움직인다**.
    already_used = frozenset(used_look_ids)
    # 순차로 도는 것이 카드 t360 이다. 「앞 큐와 가장 대비되는 룩」은 앞 구간이 무엇을
    # 골랐는지 알아야 정해지므로, 구간을 서로 **독립으로** 볼 수 없다. 앞 큐는 **룩을
    # 고른** 마지막 구간이다 — 룩이 안 붙은 구간(세기 미해석·미매핑)은 무대에 그림을
    # 안 냈으므로 다음 구간이 대비할 대상이 아니다.
    selections: list[SongCueLookSelection] = []
    previous: Look | None = None
    # 라벨마다 **1회차가 고른 룩**. 정본 §7 [HARD]: 코러스 1의 색은 이후 코러스에서
    # 되돌아와야 한다. 회차 사이의 변화는 룩 교체가 아니라 사다리가 만든다(§7.1).
    first_of_label: dict[str, Look] = dict()
    for section in sections:
        selection = _map_section_to_look(
            section=section,
            ordered_looks=ordered_looks,
            explicit_dynamics=_explicit_dynamics_for(section, explicit_dynamics),
            already_used=already_used,
            previous=previous,
            returning=first_of_label.get(section.label),
        )
        selections.append(selection)
        if selection.look is not None:
            previous = selection.look
            first_of_label.setdefault(section.label, selection.look)
    return tuple(selections)


#: 업로드 경로에서 쪼갠 큐를 서로 다르게 만드는 것의 이름 — 팔레트의 색이 아니라
#: **같은 다이내믹스 안에서 쓸 수 있는 룩**이다. 사유 문면에만 쓰인다.
SONGCUE_VARIANT_LABEL = "쓸 수 있는 룩"


def split_selections_for_density(
    selections: Sequence[SongCueLookSelection],
    *,
    bpm: float | None,
    meter: object = "4/4",
    song_end_ms: int | None = None,
) -> tuple[tuple[SongCueLookSelection, ...], tuple[str, ...]]:
    """구간 선택 목록을 마디 경계에서 쪼갠 **큐** 선택 목록으로 넓힌다 (카드 t306).

    감독 인터뷰 경로(``_build_unified_song_plan``)가 이미 하는 것과 **같은 규칙**
    이다 — 마디 산술은 :func:`server.design.cue_density.plan_cue_density` 하나가
    갖고, 이어지는 큐의 회전은 :func:`~server.design.cue_density.rotate_palette`
    하나가 갖는다. 규칙을 두 벌 두면 갈라지고, 갈라진 순간 감독이 보는 두 경로가
    다시 서로 다른 설계를 낸다.

    두 경로의 **차이**는 「무엇을 돌리느냐」 하나다. 인터뷰 경로는 팔레트의 색을
    돌리고, 이 경로는 같은 다이내믹스에 맞는 룩 목록(``dynamics_matches``)을
    돌린다. 강도를 유지하고 그림만 바꾸는 정본의 축(Q060 "강도 유지, 색만 교체")
    은 그대로다 — 다이내믹스가 같으면 D 레벨이 같기 때문이다.

    회전은 ``look`` 뿐 아니라 ``dynamics_matches`` **순서**까지 돌린다. 저장 직전
    :func:`_select_bindable` 이 이 목록의 앞에서부터 「리그에 묶이는 첫 룩」을
    고르므로, 순서를 돌려야 이어지는 큐가 앞 큐와 다른 자리에서 탐색을 시작한다.

    쓸 수 있는 룩이 하나뿐인 구간은 돌려도 같은 룩이라 **쪼개지 않는다**
    — 그 사유는 돌려주는 ``notes`` 로 밖에 나간다. BPM 이 없으면 한 건도 쪼개지
    않으며 입력이 그대로 나온다(콘솔에 가는 명령은 바이트 동일).

    :param song_end_ms: 곡 끝. 주면 **마지막 구간도** 쪼갠다. 인터뷰 경로는 이
        값을 가진 적이 없어 마지막 구간을 늘 통째로 두지만, 확정 분석 기록은
        구간마다 ``end_ms`` 를 들고 있어 이 경로에서는 알 수 있다.
    """
    ordered = tuple(selections)
    if not ordered:
        return (), ()
    plan = plan_cue_density(
        [selection.section.start_ms for selection in ordered],
        bpm=bpm,
        meter=meter,
        palette_sizes=[len(selection.dynamics_matches) for selection in ordered],
        song_end_ms=song_end_ms,
        variant_label=SONGCUE_VARIANT_LABEL,
    )
    expanded: list[SongCueLookSelection] = []
    for split in plan.splits:
        source = ordered[split.source_index]
        section = replace(source.section, start_ms=split.start_ms)
        rotated = rotate_palette(source.dynamics_matches, split.unit_index)
        look = rotated[0] if rotated else source.look
        expanded.append(replace(source, section=section, look=look, dynamics_matches=rotated))
    return tuple(expanded), plan.notes


# @MX:ANCHOR: [AUTO] 곡→큐 번들의 유일한 조립 지점. 두 번 도는 것이 설계다 —
#   1회차로 「어느 큐가 실제로 저장되는가」를 알아내고, 그 답으로 움직임을 실을 큐 하나를
#   고른 뒤 2회차에서 최종 번들을 만든다.
# @MX:REASON: 움직임을 실을 큐는 **저장되는** 큐여야 한다(룩 미해석·역할 미매칭·값 충돌로
#   건너뛴 구간에 페이저를 실으면 아무 데도 안 간다). 그런데 그 세 갈래는 조립 도중에야
#   갈린다. 1회차는 순수하고(`emitted` 를 새로 만든다) 움직임 줄은 값 라인 판정에 참여하지
#   않으므로, 2회차의 저장/건너뜀 결정은 1회차와 같다 — 그 동일성은
#   `test_songcue_movement` 가 실측한다.
def build_songcue_bundle(
    song_title: str,
    selections: Iterable[SongCueLookSelection],
    *,
    sequences_section: Mapping[str, object],
    groups_section: Mapping[str, object],
    role_aliases: Mapping[str, str] | None = None,
    allow_strobe: bool = False,
    disable_color_snap: bool = False,
    bpm: float | None = None,
) -> SongCueBundle:
    """``allow_strobe``: 이 곡이 세트에서 스트로브를 풀어도 되는 자리인지 — 기본값 거짓
    (카드 t378, :data:`LADDER_STROBE_HIT` 독스트링). 이 함수는 몇 번째 곡인지, 클라이맥스
    브레이크다운인지 **모른다** — ``selections`` 와 리그 정보만 받는다. 그 판단은
    호출자(세션/오케스트레이터 층, 곡 사이 재사용 기억을 이미 든 :mod:`server.looks.song_history`
    와 같은 자리)의 몫이고, 이 인자는 그 판단이 내려온 **결과**를 받는 자리다. 거짓이면
    스트로브 칸은 사다리 후보에도 안 들어가 이전 동작과 바이트 동일하다.

    ``disable_color_snap``: SPEC-LDCLIMAX-001 REQ-LDCLIMAX-012 — 첫 실기 콘솔 검증
    세션까지의 임시 킬스위치. 기본값 거짓(즉 색 스냅은 REQ-001 대로 무조건 회전
    후보다) — 참이면 :data:`LADDER_COLOR_SNAP` 이 후보에서 완전히 빠진다.

    ``bpm``: 절정 지속시간 상한(REQ-LDCLIMAX-006~009) 계산에 쓰는 곡 BPM.
    ``None``(기본값, 미선언)이면 상한 메커니즘은 아무 것도 하지 않는다 — 이 SPEC
    이전과 바이트 동일하다(REQ-LDCLIMAX-009, "안 재고는 안 쓴다").
    """
    ordered = tuple(selections)
    if not ordered:
        raise SongCueBundleError(EMPTY_SECTIONS)

    sequence_number = select_sequence_number(sequences_section)
    sequence_name = _ascii_label(song_title, fallback=f"Song {sequence_number}")
    # ``role_aliases``: 쇼 단위 그룹명 → 역할 표 (t356). 없으면 힌트 매칭만 돈다.
    resolution = resolve_roles(groups_section, aliases=role_aliases)
    cue_names = _cue_names(tuple(selection.section for selection in ordered))
    # 감광은 값 라인을 바꾸므로 **1회차보다 먼저** 정해져야 한다 — 어느 큐가 저장되는지가
    # 어두워진 값으로 갈리기 때문이다. 이 계산은 선택 목록의 **자리**만 보므로 순수하다.
    darken, structural_withheld = _pre_drop_positions(ordered)

    dry = _assembled(
        song_title,
        ordered,
        cue_names,
        sequence_number=sequence_number,
        sequence_name=sequence_name,
        resolution=resolution,
        movements=dict(),
        darken=darken,
        allow_strobe=allow_strobe,
        disable_color_snap=disable_color_snap,
    )
    movements, withheld = _movement_carrier(dry)
    bundle = (
        dry
        if not movements
        else _assembled(
            song_title,
            ordered,
            cue_names,
            sequence_number=sequence_number,
            sequence_name=sequence_name,
            resolution=resolution,
            movements=movements,
            darken=darken,
            allow_strobe=allow_strobe,
            disable_color_snap=disable_color_snap,
        )
    )
    bundle = replace(
        bundle,
        withheld_movement=withheld,
        withheld_darkness=structural_withheld + _darkness_withheld(bundle, darken),
        withheld_accents=_collect_withheld_accents(bundle.sections),
    )
    _guard_bundle_collision(bundle)
    # 절정 지속시간 상한(REQ-LDCLIMAX-006~011, design.md §2) — 사다리·프론트필·
    # 움직임·감광이 전부 확정된 뒤에만 "이 큐가 실제로 blinder_or_flash/strobe_hit
    # 를 실었는가"를 알 수 있으므로, 조립 도중이 아니라 조립이 끝난 **후처리 패스**로
    # 한 번 더 훑는다(design.md §2 — 여러 호출자에 컨텍스트를 빠짐없이 배선해야
    # 하는 SPEC-LDACCENT-001 §B1 취약점을 반복하지 않는다).
    return _apply_climax_duration_cap(bundle, bpm=bpm)


def _collect_withheld_accents(
    sections: Sequence[SongCueSectionBundle],
) -> tuple[SongCueWithheldAccent, ...]:
    """섹션 번들 전량에서 :attr:`SongCueSectionBundle.accent_withheld` 를 걷는다
    (SPEC-LDACCENT-001) — 기존 ``withheld_movement``/``withheld_darkness`` 집계와
    같은 패턴. 조립 도중에만 알 수 있는 값이므로 여기서 한 번에 걷는다.
    """
    return tuple(
        section.accent_withheld for section in sections if section.accent_withheld is not None
    )


def _assembled(
    song_title: str,
    ordered: Sequence[SongCueLookSelection],
    cue_names: Sequence[str],
    *,
    sequence_number: int,
    sequence_name: str,
    resolution: RoleResolution,
    movements: Mapping[int, MovementPlan],
    darken: Mapping[int, int] | None = None,
    allow_strobe: bool = False,
    disable_color_snap: bool = False,
) -> SongCueBundle:
    darken = darken if darken is not None else dict()
    section_bundles: list[SongCueSectionBundle] = []
    emitted: dict[str, tuple[int, int, str]] = dict()
    for cue_number, (selection, cue_name) in enumerate(
        zip(ordered, cue_names, strict=True), start=1
    ):
        section_bundle = _section_bundle(
            selection=selection,
            cue_number=cue_number,
            cue_name=cue_name,
            sequence_number=sequence_number,
            resolution=resolution,
            emitted=emitted,
            section_bundles=section_bundles,
            movement=movements.get(cue_number),
            drop_cue_number=darken.get(cue_number),
            allow_strobe=allow_strobe,
            disable_color_snap=disable_color_snap,
        )
        section_bundles.append(section_bundle)

    section_bundles = _rescue_value_line_collisions(
        section_bundles,
        emitted,
        sequence_number=sequence_number,
        resolution=resolution,
        movements=movements,
        darken=darken,
        allow_strobe=allow_strobe,
        disable_color_snap=disable_color_snap,
    )

    stored_commands, labelled_bundles = _flatten_commands(
        section_bundles, sequence_number, sequence_name
    )
    return SongCueBundle(
        song_title=song_title,
        sequence_number=sequence_number,
        sequence_name=sequence_name,
        commands=stored_commands,
        sections=labelled_bundles,
    )


#: ``_flatten_commands`` 가 스플라이스하는 줄의 고정 접두어 — 두 번째 훑기가 이미
#: 붙은 라벨을 다시 붙이지 않도록 감지하는 데 쓴다(``_apply_climax_duration_cap``).
_LABEL_SEQUENCE_PREFIX = "Label Sequence "


def _delabelled(bundle: SongCueSectionBundle) -> SongCueSectionBundle:
    """``_flatten_commands`` 가 붙인 ``Label Sequence`` 줄을 뗀다 — 재훑기 전
    원래 형태로 되돌려, 재훑기가 정확히 한 번만 다시 붙이게 한다."""
    commands = tuple(
        command for command in bundle.commands if not command.startswith(_LABEL_SEQUENCE_PREFIX)
    )
    if commands == bundle.commands:
        return bundle
    return replace(bundle, commands=commands)


def _flatten_commands(
    section_bundles: Sequence[SongCueSectionBundle],
    sequence_number: int,
    sequence_name: str,
) -> tuple[tuple[str, ...], tuple[SongCueSectionBundle, ...]]:
    """번들을 순서대로 이어붙인 플랫 명령 목록과, 라벨이 실린 번들들.

    조립 루프에서 뗀 이유는 하나다 — 값 라인 충돌 회수(:func:`_rescue_value_line_collisions`,
    카드 t366·t368)가 완결된 번들 목록 하나를 사후에 고칠 수 있어야 하고, 그러려면 「번들을
    쌓는 일」과 「번들을 플랫 명령으로 편다」가 같은 루프에 묶여 있으면 안 된다. 편성
    규칙 자체는 고치기 전과 같다 — 저장하는 첫 큐 뒤에 ``Label Sequence`` 를 한 번만
    끼운다.
    """
    commands: list[str] = [_DESTINATION]
    labelled: list[SongCueSectionBundle] = []
    sequence_labelled = False
    for bundle in section_bundles:
        if bundle.commands:
            commands.extend(bundle.commands)
            if not sequence_labelled:
                store_index = _first_store_index(commands, sequence_number, bundle.cue_number)
                commands.insert(
                    store_index + 1, f"Label Sequence {sequence_number} '{sequence_name}'"
                )
                bundle = replace(bundle, commands=tuple(commands[-len(bundle.commands) - 1 :]))
                sequence_labelled = True
        labelled.append(bundle)

    stored_commands = tuple(commands) if len(commands) > 1 else ()
    return stored_commands, tuple(labelled)


def _renumbered(
    bundle: SongCueSectionBundle, new_cue_number: int, sequence_number: int
) -> SongCueSectionBundle:
    """이 번들의 ``cue_number`` 를 새 번호로 옮긴다 — 저장된 큐라면 ``Store`` 줄에
    박힌 리터럴 번호도 함께 고친다(design.md §1.2 — 복귀 큐 삽입은 뒤따르는 모든
    큐의 번호를 1씩 민다).

    ``collides_with_cue_number`` 처럼 **다른** 번들을 가리키는 교차 참조는 고치지
    않는다 — 그 필드는 스킵 사유의 정보성 기록일 뿐 이 SPEC 의 판정 범위(REQ-006~
    011) 밖이다(design.md §2.2 미검증 잔여 위험과 같은 결의 문제).
    """
    if bundle.cue_number == new_cue_number:
        return bundle
    commands = bundle.commands
    if commands:
        old_marker = f"Store Sequence {sequence_number} Cue {bundle.cue_number} "
        new_marker = f"Store Sequence {sequence_number} Cue {new_cue_number} "
        commands = tuple(
            command.replace(old_marker, new_marker, 1)
            if command.startswith(old_marker)
            else command
            for command in commands
        )
    skipped = tuple(
        replace(skip, cue_number=new_cue_number) if skip.cue_number == bundle.cue_number else skip
        for skip in bundle.skipped
    )
    return replace(bundle, cue_number=new_cue_number, commands=commands, skipped=skipped)


def _climax_return_bundle(
    climax: SongCueSectionBundle, *, sequence_number: int, cue_number: int, cap_ms: int
) -> SongCueSectionBundle:
    """절정 큐 뒤에 끼우는 복귀 큐 — "사다리를 오르지 않았을 때의 기준 값"
    (design.md §2.1 6번)을 그대로 재방출하고 페이드는 강제하지 않는다(즉시 복귀).

    ``climax.selection.look`` 은 사다리 에스컬레이션 **전** 값이다 —
    :func:`escalate_attributes` 는 새 튜플만 만들 뿐 ``look`` 자체를 고치지
    않으므로, 밝기 히트를 포함해 이 절정 큐가 오른 만큼은 전혀 반영돼 있지
    않다(REQ-LDCLIMAX-007 이 요구하는 "기준 값"이 정확히 이것이다).

    같은 그룹 선택 줄(``climax.commands[1]``)을 그대로 재사용한다 — 이 큐가
    끄는 것은 절정 칸(블라인더·스트로브)뿐이고, 룩 자신이 켠 그룹은 바뀌지
    않는다.
    """
    look = climax.selection.look
    if look is None:
        raise SongCueBundleError(
            "climax cue has no resolved look; cannot build a duration-cap return cue"
        )
    values = _values_line(look.attributes)
    cue_name = f"{climax.cue_name} Return"
    return_section = replace(climax.section, name=cue_name, start_ms=cap_ms)
    commands = (
        _CLEAR,
        climax.commands[1],
        values,
        store_with_fade(f"Store Sequence {sequence_number} Cue {cue_number} '{cue_name}'", None),
        _CLEAR,
    )
    return SongCueSectionBundle(
        section=return_section,
        cue_number=cue_number,
        cue_name=cue_name,
        selection=climax.selection,
        commands=commands,
    )


# @MX:ANCHOR: [AUTO] 절정 지속시간 상한 — blinder_or_flash/strobe_hit 를 실은 큐마다
#   상한 박수 뒤에 통제된 룩으로 복귀하는 큐를 끼운다(정본 §6, SPEC-LDCLIMAX-001
#   REQ-LDCLIMAX-006~011).
# @MX:REASON: 사다리·프론트필·움직임·감광이 전부 확정된 **완성된 번들** 위에서만
#   "이 큐가 실제로 절정 칸을 실었는가"를 알 수 있다(design.md §2) — 조립 도중에
#   같은 판단을 하려면 SPEC-LDACCENT-001 §B1 이 이미 겪은 "여러 호출자에 컨텍스트를
#   빠짐없이 배선해야 하는" 취약점을 반복한다. 그래서 이 함수는 완성된
#   :class:`SongCueBundle` 을 받아 훑고, 필요할 때만 큐를 더한다 — 기존 큐의 값
#   결정 경로는 건드리지 않는다(REQ-LDCLIMAX-011).
def _apply_climax_duration_cap(bundle: SongCueBundle, *, bpm: float | None) -> SongCueBundle:
    """완성된 번들을 훑어 blinder_or_flash/strobe_hit 를 실은 큐마다 상한을
    계산하고, 다음 큐가 상한보다 늦게 오면 그 사이에 복귀 큐를 끼운다.

    ``bpm`` 이 ``None`` 이면 아무것도 하지 않는다(REQ-LDCLIMAX-009,
    ``cue_density.py`` 의 "안 재고는 안 쓴다" 규율과 같은 방향) — 입력 그대로
    반환한다(바이트 동일).
    """
    if bpm is None:
        return bundle

    sections = list(bundle.sections)
    returns: list[SongCueClimaxReturn] = []
    shift = 0
    for original in [section for section in bundle.sections if section.commands]:
        rung = original.accent_fixture.rung if original.accent_fixture is not None else None
        if rung not in (LADDER_BLINDER_OR_FLASH, LADDER_STROBE_HIT):
            continue
        cap_beats = 2.0 if rung == LADDER_BLINDER_OR_FLASH else 4.0
        cap_ms = original.section.start_ms + round(beats_to_seconds(cap_beats, bpm) * 1000)
        climax_index = original.cue_number - 1 + shift
        climax = sections[climax_index]
        next_stored = next((s for s in sections[climax_index + 1 :] if s.commands), None)
        if next_stored is not None and cap_ms >= next_stored.section.start_ms:
            # REQ-LDCLIMAX-008 — 자연 전환이 이미 상한을 지킨다. 삽입하지 않는다.
            continue
        new_cue_number = climax.cue_number + 1
        return_bundle = _climax_return_bundle(
            climax,
            sequence_number=bundle.sequence_number,
            cue_number=new_cue_number,
            cap_ms=cap_ms,
        )
        sections.insert(climax_index + 1, return_bundle)
        for later_index in range(climax_index + 2, len(sections)):
            sections[later_index] = _renumbered(
                sections[later_index], sections[later_index].cue_number + 1, bundle.sequence_number
            )
        shift += 1
        returns.append(
            SongCueClimaxReturn(
                source_section=climax.section,
                source_cue_number=climax.cue_number,
                rung=rung,
                cap_beats=cap_beats,
                inserted_cue_number=new_cue_number,
                inserted_start_ms=cap_ms,
            )
        )

    if not returns:
        return bundle
    # ``sections`` 는 ``bundle.sections`` 에서 왔고, 그 안의 첫 저장 큐는 이미
    # ``_flatten_commands`` 가 한 번 스플라이스한 ``Label Sequence`` 줄을 갖고
    # 있다(`_assembled`) — 그대로 다시 훑으면 라벨 줄이 두 번 붙는다. 다시
    # 훑기 전에 떼서, 재훑기가 정확히 한 번만 다시 붙이게 한다.
    for index, section in enumerate(sections):
        if section.commands and any(c.startswith(_LABEL_SEQUENCE_PREFIX) for c in section.commands):
            sections[index] = _delabelled(section)
            break
    commands, labelled = _flatten_commands(sections, bundle.sequence_number, bundle.sequence_name)
    return replace(bundle, commands=commands, sections=labelled, climax_returns=tuple(returns))


# @MX:ANCHOR: [AUTO] 드롭은 값 충돌로 버려지지 않는다 — 물러서는 쪽은 드롭이 아닌
#   상대다(정본 §6 「마지막 드롭은 전 리그 최대」, 카드 t366). 카드 t368 에서 3회차
#   이상의 반복 라벨(후렴 등)에도 같은 회수를 열었다 — 아래 REASON 후반부.
# @MX:REASON: 사다리(§7.1)는 **나중 큐가 오른다**. 드롭이 이미 천장(``_DIMMER_CEILING``)
#   에 있고 빔 축(줌·아이리스)도 없거나 이미 다 쓰였으면 오를 데가 없어 마지막 수단으로
#   버려졌다 — 실측(2026-09-12, main `13595be`) 8구간 EDM 입력에서 드롭 한 장이
#   사라졌다(`edm-drop-crimson`, Dimmer 100·Zoom 10, Iris 축 없음). 드롭의 값은 정본이
#   요구하는 리그 최대 그대로가 맞으므로, 대신 **충돌한 상대**(``collides_with_cue_number``
#   가 가리키는, 값 라인의 원래 임자)를 한 칸 물려 자리를 비킨다. 되돌리기 쉬운 유혹은
#   「드롭도 그냥 한 칸 더 오르게 하자」인데, 이 룩처럼 오를 축이 전혀 없는 경우 그
#   유혹은 이 결함 그대로다. 상대가 드롭 자신이면(같은 §6 행의 다른 드롭) 물리지
#   않는다 — 정본이 「전 리그 최대」를 요구하는 것은 드롭이지, 드롭과 충돌한 또 다른
#   드롭이 아니다.
#
#   **카드 t368 — 같은 결함이 드롭 아닌 반복 라벨의 3회차 이상에서도 실측됐다.**
#   빔 축이 하나뿐인 룩(``edm-drop-crimson``, 줌만)은 오를 수 있는 값이 「기준값·
#   줌 좁힌 값」 둘뿐이고, 축이 둘인 룩(``worship-glory-climax``, 줌+아이리스)도
#   「기준값·줌·아이리스」 셋뿐이다 — 1회차가 기준값을, 2회차(또는 2·3회차)가 그
#   나머지를 다 쓰면 그 다음 회차부터는 사다리를 아무리 더 올라도 이미 쓴 값으로만
#   되돌아온다(``_climb_rungs`` 의 액센트는 갈아탈 뿐 누적하지 않으므로). 그 결과
#   3회차 이상의 후렴이 통째로 버려졌다 — 정본 §7 「곡 안 반복은 미덕」의 정반대다.
#
#   회수 조건을 **드롭이거나 3회차 이상**(``section.instance >= 3``)으로 잡은 것은
#   임의가 아니다: 1회차는 언제나 기준값으로 성공하고, 2회차는 사다리의 첫 액센트로
#   성공하는 것이 **정상 경로**다 — 이 두 회차가 그래도 충돌해 버려지는 것은 이
#   룩에 액센트 축이 하나도 없다는 뜻이고(``test_songcue_ladder.py`` 의
#   ``TestTheLastResortSkipStillFires`` · ``test_songcue_bundle.py`` 의
#   ``test_value_line_collision_skips_later_section_without_pulling_next_cue`` ·
#   ``test_songcue_report.py`` 의 ``_mixed_bundle`` 이 바로 그 도합 아홉 개 대조군),
#   그 경계선까지 회수 대상으로 넓히면 이 셋이 전부 깨진다. 3회차부터 회수하는 것은
#   「액센트를 다 썼는데도 반복이 남았다」는 경우만 잡고, 「애초에 액센트가 없다」는
#   경우는 그대로 마지막 수단의 건너뜀으로 남긴다.
#
#   되돌리기 쉬운 유혹 하나 더— 밝기를 물러서는 폭을 회차 깊이에 비례해 키우는 것
#   (줌을 -5 대신 -10, -15 로). 그러면 새 값이 계속 나오지만, 감독 결정(2026-09-12,
#   ``_MARKING_ACCENTS``)이 「밝기만 누적하고 나머지는 큐당 하나」라고 못박았다 —
#   찍는 액센트의 폭 자체를 회차마다 키우는 것은 그 결정을 어기는 것과 같은 축이다.
#   그래서 여기서 새로 여는 것은 폭을 넓히는 것이 아니라, **이미 있는 밝기-물러섬
#   축**(``LADDER_DIMMER_YIELD``, 정본 §8 안전 바닥까지)을 상대에게 반복해 적용하는
#   것뿐이다 — 그 축은 이미 살아 있었다(드롭을 위해).
def _rescue_value_line_collisions(
    section_bundles: Sequence[SongCueSectionBundle],
    emitted: dict[str, tuple[int, int, str]],
    *,
    sequence_number: int,
    resolution: RoleResolution,
    movements: Mapping[int, MovementPlan],
    darken: Mapping[int, int],
    allow_strobe: bool = False,
    disable_color_snap: bool = False,
) -> tuple[SongCueSectionBundle, ...]:
    """드롭, 또는 3회차 이상의 반복 라벨이 사다리 소진으로 버려지려는 것을 되살린다.

    한 번의 훑기로 안 끝날 수 있다 — 회차가 셋 이상 겹치면(카드 t368 실측: 후렴
    4회) 앞선 회수가 만든 새 점유가 **뒤 회차의 진짜 상대**를 바꾼다(기준값을
    쥔 큐가 바뀐다). 그래서 매 시도 직전에 ``_section_bundle`` 로 다시 지어
    ``collides_with_cue_number`` 를 그 순간의 ``emitted`` 기준으로 다시 읽고,
    바뀐 것이 없을 때까지 훑기를 반복한다(``LADDER_DIMMER_YIELD`` 가 바닥까지
    유한하므로 반드시 멈춘다 — 상한은 방어적으로만 둔다).
    """
    bundles = list(section_bundles)

    def _rebuild(bundle: SongCueSectionBundle) -> SongCueSectionBundle:
        # ``bundles`` 는 이 클로저가 참조하는 시점의 **현재** 상태다(재구성 순서와
        # 무관하게 항상 "cue_number 앞의 지금 상태") — SPEC-LDCLIMAX-001 D3,
        # ``_section_bundle`` 독스트링과 같은 근거.
        return _section_bundle(
            selection=bundle.selection,
            cue_number=bundle.cue_number,
            cue_name=bundle.cue_name,
            sequence_number=sequence_number,
            resolution=resolution,
            emitted=emitted,
            section_bundles=bundles,
            movement=movements.get(bundle.cue_number),
            drop_cue_number=darken.get(bundle.cue_number),
            allow_strobe=allow_strobe,
            disable_color_snap=disable_color_snap,
        )

    for _round in range(len(bundles) + 1):
        changed = False
        for index, bundle in enumerate(bundles):
            if not bundle.skipped or bundle.skipped[0].reason != VALUE_LINE_COLLISION:
                continue
            if not (_is_literal_drop(bundle.section) or bundle.section.instance >= 3):
                continue
            # emitted 가 이전 회수로 바뀌었을 수 있다 — 갱신 없이 옛 skip 을 그대로
            # 믿으면 이미 자리를 옮긴 상대를 다시 겨눈다(카드 t368 실측).
            bundle = _rebuild(bundle)
            bundles[index] = bundle
            if not bundle.skipped:
                changed = True
                continue
            skip = bundle.skipped[0]
            if skip.reason != VALUE_LINE_COLLISION:
                continue
            rival_cue_number = skip.collides_with_cue_number
            if rival_cue_number is None:
                continue
            rival_index = rival_cue_number - 1
            if rival_index < 0 or rival_index >= len(bundles):
                continue
            rival = bundles[rival_index]
            if rival.section.index == bundle.section.index:
                # 한 구간을 마디로 쪼갠 큐끼리의 충돌 — 사다리의 일이 아니다, 접어 둔다.
                continue
            if _is_literal_drop(rival.section):
                continue
            yielded = _yield_bundle(rival, emitted)
            if yielded is None:
                continue
            bundles[rival_index] = yielded
            bundles[index] = _rebuild(bundle)
            changed = True
        if not changed:
            break
    _reorder_yields_by_repetition(bundles)
    _finalize_marking_accents(
        bundles,
        emitted,
        resolution,
        allow_strobe=allow_strobe,
        disable_color_snap=disable_color_snap,
    )
    return tuple(bundles)


# @MX:NOTE: [AUTO] 카드 t369 — 회수가 두 겹으로 겹치면 **회차 순서**가 뒤집힐 수 있다.
#   (여기도 ANCHOR 상한을 이미 넘겨 있어 NOTE 로 남긴다.)
# @MX:REASON: 위 회수 루프는 매 단계를 독립으로 푼다 — 상대를 물릴 때마다
#   :func:`_yield_bundle` 이 **그 룩의 기준값에서 처음부터** 걸리지 않는 첫 자리를
#   찾는다. 겹침이 한 겹이면(카드 t366·t368) 그것으로 충분하다. 실측(2026-09-13,
#   ``edm-drop-crimson``, 빔 축 하나뿐인 후렴 4회): 1회차가 물러서서 3회차에게
#   기준값을 내주고(``Dimmer`` 100→95), 그 직후 4회차가 **다시** 그 기준값을 원해
#   3회차를 물린다 — 그런데 3회차를 문 :func:`_yield_bundle` 은 1회차가 이미 95를
#   쥔 줄 모르고 기준값에서부터 다시 내려가 90에 닿는다. 그 결과 1회차(95)보다
#   **늦은** 3회차(90)가 더 어둡다 — 정본 §7.1 ``_ladder_start`` 의 「낮은 칸으로는
#   내려가지 않는다」를 어긴다.
#
#   고치는 자리를 회수 루프 안이 아니라 **끝에 한 번 더** 둔 이유: 루프 한 단계는
#   그 순간의 ``rival`` 하나만 보고, 이 결함은 **두 단계 사이의 관계**라 한 단계
#   안에서는 안 보인다. 그래서 모든 회수가 끝난 뒤, 같은 라벨·같은 룩(``look_id``)
#   반복끼리만 묶어 이미 낸 값들을 회차 순서로 다시 나눠 준다 — **새 값을 짓지
#   않는다**, 이미 계산된 값 집합을 회차에 맞춰 재배정할 뿐이다(그래서 아홉 개
#   대조군의 값 라인 집합·개수는 그대로다). 이미 단조증가라면(대부분의 입력) 아무
#   것도 안 바꾼다 — 그 갈래가 고치기 전과 바이트 동일하다는 것을 이 파일의 다른
#   회귀 검사들이 지킨다.
def _reorder_yields_by_repetition(bundles: list[SongCueSectionBundle]) -> None:
    """저장된 큐들을 제자리에서 고쳐, 같은 룩의 반복 회차가 밝기 역순이 되지 않게 한다.

    라벨과 룩 정체(``look_id``)가 같은 저장된 큐만 한 묶음으로 본다 — 라벨이 다르면
    (드롭 대 후렴) 회차 개념 자체가 다르고, 룩이 다르면 값의 서로 다름이 반복이 아닌
    선택의 차이다. 묶음 안에서 회차(``instance``) 순서로 늘어놓은 ``Dimmer`` 값이
    이미 단조증가면 손대지 않는다.
    """
    seen_labels: list[str] = []
    for bundle in bundles:
        if bundle.commands and bundle.section.label not in seen_labels:
            seen_labels.append(bundle.section.label)

    for label in seen_labels:
        seen_looks: list[str] = []
        for bundle in bundles:
            if not bundle.commands or bundle.section.label != label:
                continue
            look = bundle.selection.look
            if look is not None and look.look_id not in seen_looks:
                seen_looks.append(look.look_id)

        for look_id in seen_looks:
            group = [
                index
                for index, bundle in enumerate(bundles)
                if bundle.commands
                and bundle.section.label == label
                and bundle.selection.look is not None
                and bundle.selection.look.look_id == look_id
            ]
            if len(group) < 2:
                continue
            ordered = sorted(group, key=lambda index: bundles[index].section.instance)
            dimmers = [_dimmer_from_values_line(bundles[index].commands[2]) for index in ordered]
            if any(value is None for value in dimmers):
                continue
            if all(before <= after for before, after in zip(dimmers, dimmers[1:], strict=False)):
                continue
            payloads = sorted(
                (
                    (
                        dimmers[position],
                        bundles[ordered[position]].commands,
                        bundles[ordered[position]].ladder,
                    )
                    for position in range(len(ordered))
                ),
                key=lambda payload: payload[0],
            )
            for position, index in enumerate(ordered):
                _new_dimmer, new_commands, new_ladder = payloads[position]
                current = bundles[index]
                if current.commands[2] == new_commands[2]:
                    continue
                replaced_commands = (
                    current.commands[0],
                    current.commands[1],
                    new_commands[2],
                    *current.commands[3:],
                )
                bundles[index] = replace(current, commands=replaced_commands, ladder=new_ladder)


_VALUE_TOKEN_RE = re.compile(r"Attribute '([^']+)' At (-?\d+(?:\.\d+)?)")


def _parse_values_line(values: str) -> tuple[AttributeValue, ...]:
    """``_values_line`` 이 낸 문자열을 :class:`AttributeValue` 로 되돌린다.

    회수·재배열이 다 끝난 뒤에는 문자열만 남으므로(:func:`_dimmer_from_values_line`
    독스트링과 같은 사정), 재배열 뒤에 액센트를 마저 얹으려면(:func:`_finalize_marking_accents`)
    다시 구조화된 값이 필요하다. 파싱하는 형식은 :func:`_values_line`
    (`server.looks.instantiate`) 이 내는 고정 형식 하나뿐이다.
    """
    return tuple(AttributeValue(name, float(raw)) for name, raw in _VALUE_TOKEN_RE.findall(values))


_CUE_FADE_SUFFIX_RE = re.compile(rf" {re.escape(CUE_FADE_KEYWORD)} -?\d+(?:\.\d+)?$")


def _forced_zero_fade_store(store_line: str) -> str:
    """이 ``Store`` 줄의 페이드를 정확히 0으로 다시 강제한다(REQ-LDCLIMAX-003).

    이미 붙은 ``CueFade <값>`` 접미사가 있으면 떼고 다시 0을 붙인다 — 붙은 값이
    무엇이었든(라벨이 정한 값이든, 아예 없었든) 결과는 늘 ``CueFade 0`` 하나다.
    """
    base = _CUE_FADE_SUFFIX_RE.sub("", store_line)
    return store_with_fade(base, 0.0)


#: 찍는 액센트 판정에서 "이 칸이 액센트인가"를 물을 때 쓰는 전체 집합 —
#: :func:`_marking_accents` 의 ``allow_strobe`` 로 갈리는 회전 후보 목록과 다르다.
#: 1회차에서 걷어 낼 때는(:func:`_strip_marking_accent_from_base_occurrence`)
#: ``allow_strobe`` 가 그때 거짓이라고 해서 스트로브를 못 걷어 내면 안 되므로
#: 이 자리는 언제나 넷 다 본다.
_ALL_MARKING_RUNGS: tuple[str, ...] = (*_MARKING_ACCENTS, LADDER_STROBE_HIT)


def _accent_insertion_index(bundle: SongCueSectionBundle) -> int:
    """액센트 명령 두 줄을 끼워 넣을(또는 걷어 낼) 자리.

    :func:`_section_bundle` 의 조립 순서(값 라인 → 프론트 필 → 액센트 → 움직임 →
    Store)와 같다 — 프론트 필이 있으면 그 두 줄(``Group`` + 값) 뒤, 없으면 값 라인
    바로 뒤.
    """
    return 3 + (2 if bundle.front_fill is not None else 0)


# @MX:ANCHOR: [AUTO] 1회차(section.instance < 2)는 절대 찍는 액센트를 받지 않는다
#   (카드 t382 후속 결함 D1).
# @MX:REASON: 실측(오케스트레이터 재측정, af494681): 7·4회차 곡 모두 1회차가
#   ``blinder_or_flash`` 를 실었다. 원인은 :func:`_reorder_yields_by_repetition`
#   가 (값 라인, 사다리) 묶음을 밝기 오름차순으로 회차 사이에서 통째로 바꿔치기
#   하기 때문이다 — 1회차 자신은 이 코드 어디서도 액센트를 받지 않지만
#   (:func:`_ensure_marking_accent` 의 ``instance < 2`` 단락), 재배열이 액센트를
#   실은 **다른** 회차의 묶음을 1회차 자리로 옮겨 붙이면 그 액센트가 딸려 온다.
#   그래서 재배열이 다 끝난 뒤 1회차 자리만 다시 훑어 액센트를 걷어 낸다 — 값
#   라인은 ``look.attributes``(기준값) + 이미 확정된 ``Dimmer`` 값만으로 다시
#   지어 줌·아이리스 좁힘의 흔적을 지운다. 무대 명령(``commands[3:]``)은 여기서
#   건드리지 않는다 — 재배열이 애초에 그쪽은 안 옮기므로(``_reorder_yields_by_repetition``
#   독스트링) 이 번들 몫으로 지울 것이 없고, 사다리를 명령에 맞추는 일은
#   :func:`_reconcile_accent_fixture` 가 모든 번들에 대해 한 번에 한다.
def _strip_marking_accent_from_base_occurrence(
    bundle: SongCueSectionBundle,
    emitted: dict[str, tuple[int, int, str]],
) -> SongCueSectionBundle:
    """1회차 번들에 재배열이 얹은 찍는 액센트가 있으면 값·사다리에서 걷어 낸다."""
    look = bundle.selection.look
    if look is None or not bundle.commands:
        return bundle
    inherited = next((rung for rung in bundle.ladder if rung in _ALL_MARKING_RUNGS), None)
    if inherited is None:
        return bundle
    old_values = bundle.commands[2]
    current_dimmer = _dimmer_from_values_line(old_values)
    clean_attributes = tuple(
        AttributeValue(
            attribute.name,
            current_dimmer
            if attribute.name == _DIMMER and current_dimmer is not None
            else attribute.value,
        )
        for attribute in look.attributes
    )
    clean_values = _values_line(clean_attributes)
    new_ladder = tuple(rung for rung in bundle.ladder if rung != inherited)
    if clean_values == old_values:
        return replace(bundle, ladder=new_ladder)
    emitted.pop(old_values, None)
    emitted[clean_values] = (bundle.section.index, bundle.cue_number, look.look_id)
    new_commands = (bundle.commands[0], bundle.commands[1], clean_values, *bundle.commands[3:])
    return replace(bundle, commands=new_commands, ladder=new_ladder)


# @MX:ANCHOR: [AUTO] 무대 액센트 명령을 방금 확정된 사다리에 맞춘다(카드 t382
#   후속 결함 D2).
# @MX:REASON: 실측(오케스트레이터 재측정, af494681): 리그에 블라인더 그룹이 있어도
#   ``blinder_or_flash`` 를 실은 회차의 명령에 그 그룹 명령이 없었다. 원인은
#   :func:`_reorder_yields_by_repetition` 가 (값 라인, 사다리)만 다른 회차 것으로
#   바꿔치기하고 ``commands[3:]``(프론트 필·액센트·움직임·Store)는 이 번들
#   **자신**이 원래 낸 것을 그대로 두기 때문이다(그 함수 독스트링) — 그래서 재배열
#   뒤에는 사다리가 가리키는 액센트와 실제 무대 명령이 서로 다른 회차 것일 수
#   있다. ``bundle.accent_fixture`` 필드는 재배열이 안 건드리므로 "commands[3:]에
#   지금 액센트 명령이 실제로 있는가"를 정확히 말해 준다 — 있으면 걷어 내고
#   (``emitted`` 도 같이 지운다), 방금 확정된 사다리가 블라인더·스트로브를
#   가리키면 :func:`_accent_fixture_commands` 로 다시 만들어 붙인다. 리그에 그
#   그룹이 없으면(:func:`_accent_fixture_commands` 가 빈 명령을 돌려줌) 사다리는
#   그 칸을 실어도 무대에는 여전히 아무것도 안 나간다 — 그 갈래는 고치기 전부터
#   있던 모양이고(``SongCueSectionBundle.accent_fixture`` 독스트링), 이 카드의
#   범위 밖이다(별도 follow-up 카드 후보 — verdict.md 참고).
def _reconcile_accent_fixture(
    bundle: SongCueSectionBundle,
    resolution: RoleResolution,
    emitted: dict[str, tuple[int, int, str]],
) -> SongCueSectionBundle:
    """이 번들의 무대 액센트 명령을 지금 사다리가 가리키는 칸과 다시 맞춘다."""
    commands = bundle.commands
    accent_fixture = bundle.accent_fixture
    if accent_fixture is not None:
        insert_at = _accent_insertion_index(bundle)
        stale = commands[insert_at : insert_at + 2]
        if len(stale) == 2:
            emitted.pop(stale[1], None)
            commands = commands[:insert_at] + commands[insert_at + 2 :]
        accent_fixture = None

    rung = next((r for r in bundle.ladder if r in _ACCENT_FIXTURE_ROLE), None)
    if rung is not None:
        accent_commands, accent_rung, accent_groups, accent_dimmer = _accent_fixture_commands(
            (rung,),
            section=bundle.section,
            cue_number=bundle.cue_number,
            resolution=resolution,
            emitted=emitted,
        )
        if accent_commands:
            insert_at = _accent_insertion_index(bundle)
            commands = commands[:insert_at] + accent_commands + commands[insert_at:]
            accent_fixture = SongCueAccentFixture(
                section=bundle.section,
                cue_number=bundle.cue_number,
                rung=accent_rung,
                groups=tuple(group.number for group in accent_groups),
                dimmer=accent_dimmer,
            )

    if commands == bundle.commands and accent_fixture == bundle.accent_fixture:
        return bundle
    return replace(bundle, commands=commands, accent_fixture=accent_fixture)


# @MX:ANCHOR: [AUTO] 재배열(:func:`_reorder_yields_by_repetition`) 뒤에도 반복
#   회차(instance >= 2)는 찍는 액센트를 하나 잃지 않는다(카드 t382).
# @MX:REASON: 재배열은 값 라인·사다리 묶음을 통째로 옮긴다 — 그 묶음이 원래 어느
#   회차를 위해 만들어졌는지는 안 본다(정본 §7.1 이 요구하는 것은 "밝기가 회차
#   순으로 오른다"이지 "액센트가 원래 회차 그대로 남는다"가 아니다, `_reorder_yields_by_repetition`
#   독스트링). 실측(카드 t382): 액센트 없이 성공한 낮은 회차의 묶음이 재배열로 높은
#   회차 자리에 옮겨 가면, 그 자리는 :func:`_section_bundle` 에서 이미 액센트를
#   받았더라도 최종 결과에서는 잃는다. 이 마지막 훑기가 최종 위치를 기준으로 다시
#   확인한다.
#
#   세 단계로 나눈다 — (1) 1회차가 재배열로 물려받은 액센트를 걷어 낸다
#   (:func:`_strip_marking_accent_from_base_occurrence`, D1), (2) 그 결과 액센트를
#   잃었을 수 있는 instance >= 2 자리를 그 회차 **자신의** 회전으로 다시 채운다
#   (``force`` 는 이 자리가 양보를 거쳤는지로 정한다 — 양보는 사다리 축이
#   아니므로 "마땅한 깊이" 개념이 없다, :func:`_ensure_marking_accent` 독스트링),
#   (3) 모든 저장된 번들의 무대 명령을 지금 사다리에 맞춘다
#   (:func:`_reconcile_accent_fixture`, D2). 순서가 중요하다 — (3)은 (1)·(2)가
#   확정한 사다리를 읽으므로 반드시 마지막이다.
def _finalize_marking_accents(
    bundles: list[SongCueSectionBundle],
    emitted: dict[str, tuple[int, int, str]],
    resolution: RoleResolution,
    *,
    allow_strobe: bool = False,
    disable_color_snap: bool = False,
) -> None:
    """재배열이 끝난 뒤 액센트를 1회차에서 걷어 내고, 빠진 자리를 채우고, 무대
    명령을 사다리에 맞춘다."""
    for index, bundle in enumerate(bundles):
        if not bundle.commands or bundle.section.instance >= 2:
            continue
        bundles[index] = _strip_marking_accent_from_base_occurrence(bundle, emitted)

    for index, bundle in enumerate(bundles):
        if not bundle.commands or bundle.section.instance < 2:
            continue
        look = bundle.selection.look
        if look is None:
            continue
        # SPEC-LDCLIMAX-001 D3 — 이 시점의 ``bundles`` (재배열까지 끝난 최종 순서)
        # 에서 다시 읽는다. ``_section_bundle`` 이 처음 이 큐를 지을 때 계산한 값은
        # 재배열이 순서를 바꿨을 수 있어 이제는 낡았을 수 있다.
        previous_color = _previous_stored_color(bundles, before_cue_number=bundle.cue_number)
        label_palette = _label_return_palette(
            bundles, label=bundle.section.label, before_cue_number=bundle.cue_number
        )
        accents = _marking_accents(
            allow_strobe=allow_strobe,
            disable_color_snap=disable_color_snap,
            look=look,
            resolution=resolution,
            section=bundle.section,
            previous_color=previous_color,
            label_palette=label_palette,
        )
        if any(rung in accents for rung in bundle.ladder):
            continue
        values = bundle.commands[2]
        escalated = _parse_values_line(values)
        force = LADDER_DIMMER_YIELD in bundle.ladder
        final_values, final_rungs, withheld = _ensure_marking_accent(
            escalated,
            bundle.section,
            bundle.ladder,
            values,
            emitted,
            look=look,
            resolution=resolution,
            allow_strobe=allow_strobe,
            disable_color_snap=disable_color_snap,
            force=force,
            previous_color=previous_color,
            label_palette=label_palette,
        )
        if withheld:
            # SPEC-LDACCENT-001 REQ-005/006 — 유효한 찍는 액센트 후보가 하나도 없으면
            # 셀 이름을 지어내지 않고, 어느 섹션·어느 큐에서·어떤 이유로 못 채웠는지
            # 눈에 보이는 유보 기록을 남긴다(빈 칸으로 조용히 넘어가지 않는다).
            bundles[index] = replace(
                bundle,
                accent_withheld=SongCueWithheldAccent(
                    section=bundle.section,
                    cue_number=bundle.cue_number,
                    reason=ACCENT_NO_EFFECTIVE_CANDIDATE,
                    detail=_no_effective_candidate_detail(
                        allow_strobe=allow_strobe,
                        disable_color_snap=disable_color_snap,
                        look=look,
                        resolution=resolution,
                        section=bundle.section,
                        previous_color=previous_color,
                        label_palette=label_palette,
                    ),
                ),
            )
            continue
        added_rungs = final_rungs[len(bundle.ladder) :]
        if not added_rungs:
            continue
        if final_values != values:
            emitted.pop(values, None)
            emitted[final_values] = (bundle.section.index, bundle.cue_number, look.look_id)
        new_commands = (bundle.commands[0], bundle.commands[1], final_values, *bundle.commands[3:])
        new_ladder = bundle.ladder + added_rungs
        new_fade = bundle.fade
        if LADDER_COLOR_SNAP in added_rungs:
            # REQ-LDCLIMAX-003 — 이 마무리 패스에서 색 스냅이 새로 채워진 경우에도
            # 페이드는 정확히 0 이어야 한다. ``_section_bundle`` 의 강제는 이 큐를
            # 처음 지을 때(그때는 아직 색 스냅이 없었다) 이미 지나갔으므로, 여기서
            # Store 줄의 페이드를 다시 강제한다.
            store_index = len(new_commands) - 2
            new_commands = (
                *new_commands[:store_index],
                _forced_zero_fade_store(new_commands[store_index]),
                *new_commands[store_index + 1 :],
            )
            new_fade = SectionFade(
                line=LADDER_COLOR_SNAP,
                seconds=0.0,
                source="REQ-LDCLIMAX-003 — 마무리 패스 색 스냅도 페이드를 0으로 강제한다",
            )
        bundles[index] = replace(bundle, commands=new_commands, ladder=new_ladder, fade=new_fade)

    for index, bundle in enumerate(bundles):
        if not bundle.commands:
            continue
        bundles[index] = _reconcile_accent_fixture(bundle, resolution, emitted)


def _dimmer_from_values_line(values: str) -> float | None:
    """값 라인 문자열에서 ``Dimmer`` 수치만 뽑는다 — 없으면 ``None``.

    사다리·회수는 값을 :class:`AttributeValue` 로 들고 있다가 문자열로 편다
    (:func:`_values_line`); 회수가 끝난 뒤에는 문자열만 남으므로, 여기서는 그 문자열을
    다시 읽는다. 정규식은 :func:`_values_line` 이 내는 고정 형식(`Attribute 'Dimmer'
    At <값>`)에 맞춘 것 하나뿐이다.
    """
    match = re.search(rf"Attribute '{re.escape(_DIMMER)}' At (-?\d+(?:\.\d+)?)", values)
    if match is None:
        return None
    return float(match.group(1))


def _is_literal_drop(section: SongCueSection) -> bool:
    """이 구간이 §2.2 EDM 축의 ``drop`` 어휘 그 자체와 걸리는가.

    코러스와 드롭은 같은 §6 행(:data:`ROW_CHORUS`)을 쓰지만, 「전 리그 최대」는 정본이
    ``drop`` 라벨에만 적은 말이다 — 행으로 물으면(:func:`_is_drop_row`) 코러스까지
    걸려, 코러스끼리의 충돌(반복 회차)도 회수 대상이 되어 버린다.
    """
    return "drop" in matched_section_terms(section.label)


def _yield_bundle(
    rival: SongCueSectionBundle,
    emitted: dict[str, tuple[int, int, str]],
) -> SongCueSectionBundle | None:
    """드롭에 자리를 비켜주려고 ``rival`` 의 밝기를 한 칸씩 내린다.

    새로 겹치지 않는 값을 찾으면 그 값을 실은 번들을 돌려주고 ``emitted`` 를 그 자리에
    맞춰 고친다. :data:`DARKNESS_FLOOR` 에 닿도록(또는 애초에 ``Dimmer`` 축이 없어서)
    못 찾으면 ``None`` — 그때는 원래 스킵이 그대로 선다.

    카드 t382 — 양보로 자리를 얻은 반복 회차(instance >= 2)에 찍는 액센트를 붙이는
    일은 여기서 하지 않는다. 이 함수가 결정한 액센트는 :func:`_reorder_yields_by_repetition`
    가 값 라인·사다리만 다른 회차 것으로 바꿔치기할 때(그 함수 독스트링 — 무대
    명령은 안 옮긴다) 액센트와 실제 명령이 서로 다른 회차 것으로 어긋날 수 있다
    (카드 t382 후속 결함 D1·D2). 그래서 액센트는 회수·재배열이 전부 끝나 밝기가
    최종 확정된 뒤 :func:`_finalize_marking_accents` 한 자리에서만 결정한다 — 이
    함수는 밝기(``Dimmer``)만 다룬다.
    """
    look = rival.selection.look
    if look is None or not rival.commands:
        return None
    attributes = look.attributes
    while True:
        stepped = _stepped(attributes, _DIMMER, -_HIT_STEP, DARKNESS_FLOOR)
        candidate = _values_line(stepped)
        if candidate == _values_line(attributes):
            return None
        attributes = stepped
        if candidate not in emitted:
            old_values = rival.commands[2]
            new_commands = (
                rival.commands[0],
                rival.commands[1],
                candidate,
                *rival.commands[3:],
            )
            emitted.pop(old_values, None)
            emitted[candidate] = (rival.section.index, rival.cue_number, look.look_id)
            return replace(
                rival,
                commands=new_commands,
                ladder=rival.ladder + (LADDER_DIMMER_YIELD,),
            )


# @MX:ANCHOR: [AUTO] 한 번들이 페이저를 **하나만** 낸다는 규칙이 여기서 집행된다.
# @MX:REASON: `run_commands` 의 중복 제거는 명령 지시 하나 전체를 범위로 하고, 면제 집합은
#   `Clear`·`ClearAll`·`Fixture <n>`·`Group <n>` 뿐이다(`server/fx/instantiate.py` 의
#   `_PROGRAMMER_STATE_COMMANDS`). 페이저를 만드는 데 반드시 필요한 `Step 2` 는 내용이 없는
#   줄이라 큐마다 다르게 만들 방법이 **없다** — 두 번째 큐의 `Step 2` 는 접히고, 그 큐는
#   스텝 하나만 가진 「페이저 아닌 것」을 저장한다. 저장된 페이저 큐는 빈 큐와 구별되지
#   않으므로 그 실패는 무대에서만 보인다. 그래서 대역이 가장 센 큐 하나가 페이저를 갖고,
#   나머지는 :data:`MOVEMENT_TURN_BOUNDARY` 로 보고된다. 이 경계를 넓히려면 명령 지시를
#   큐마다 쪼개거나(`server/orchestrator/tools.py` 의 `create_arrangement_groups` 가 쓰는
#   신선한 `ExecutionContext` 패턴) 면제 집합에 `Step <k>` 를 넣어야 하고, 둘 다 fx SPEC
#   쪽 결정이므로 이 카드에서 하지 않는다.
def _movement_carrier(
    bundle: SongCueBundle,
) -> tuple[dict[int, MovementPlan], tuple[SongCueWithheldMovement, ...]]:
    """움직임을 실을 큐 **하나**와, 못 실은 큐들의 사유.

    고르는 기준은 대역이다 — 가장 센 대역, 같으면 **리터럴 드롭**(:func:`_is_literal_drop`)
    이 우선, 그래도 같으면 이른 큐. 정본 §6.4 가 「빠름 = 드롭 전용」이라 했고 §12 항목
    1의 목적이 「드롭을 드롭으로 만드는 것」이므로, 하나만 실을 수 있다면 그 하나는
    드롭이다 — 코러스는 §2.2 어휘가 드롭과 다이내믹스 행을 공유해(``chorus`` ·
    ``drop`` 모두 4~5, `section_vocab.py` `ROW_CHORUS`) 같은 룩을 받을 수 있고, 그러면
    대역이 묶인다(카드 t367 실측: 코러스 두 회차와 드롭이 전부 ``edm-drop-crimson`` 을
    받아 셋 다 ``fast``). 대역이 묶였을 때 **이른 큐**만 보면 코러스가 드롭보다 먼저
    와 이겨 버린다 — 리터럴 드롭 우선을 대역 다음, 이른 큐보다 앞서는 tie-break으로
    끼워 넣는다.
    """
    candidates: list[tuple[int, int, bool, MovementPlan]] = []
    withheld: list[SongCueWithheldMovement] = []
    for section in bundle.stored_sections:
        look = section.selection.look
        if look is None or not look.movement:
            continue
        band = band_for_dynamics(look.dynamics)
        if band == MOVEMENT_STILL:
            withheld.append(
                SongCueWithheldMovement(
                    section=section.section,
                    cue_number=section.cue_number,
                    band=band,
                    reason=MOVEMENT_BAND_STILL,
                    detail=f"look {look.look_id} sits at dynamics {look.dynamics}",
                )
            )
            continue
        try:
            plan = plan_movement(look, band=band)
        except MovementError as error:
            withheld.append(
                SongCueWithheldMovement(
                    section=section.section,
                    cue_number=section.cue_number,
                    band=band,
                    reason=error.reason,
                    detail=str(error),
                )
            )
            continue
        if plan is not None:
            candidates.append(
                (
                    BAND_ORDER.index(band),
                    section.cue_number,
                    _is_literal_drop(section.section),
                    plan,
                )
            )

    if not candidates:
        return dict(), tuple(withheld)
    carrier = max(candidates, key=lambda entry: (entry[0], entry[2], -entry[1]))
    movements: dict[int, MovementPlan] = dict()
    movements[carrier[1]] = carrier[3]
    for _rank, cue_number, _is_drop, plan in candidates:
        if cue_number == carrier[1]:
            continue
        section = next(s for s in bundle.sections if s.cue_number == cue_number)
        withheld.append(
            SongCueWithheldMovement(
                section=section.section,
                cue_number=cue_number,
                band=plan.band,
                reason=MOVEMENT_TURN_BOUNDARY,
                detail=(
                    f"cue {carrier[1]} carries this bundle's one phaser (band "
                    f"{carrier[3].band}); a second `Step 2` line in the same instruction "
                    "turn is folded by the run_commands dedupe and the cue would store a "
                    "one-step non-phaser"
                ),
            )
        )
    return movements, tuple(withheld)


# @MX:NOTE: [AUTO] 드롭 앞에서 밝기를 빼는 자리를 **고르는** 유일한 판정(정본 §8 [HARD]).
#   (ANCHOR 가 아니라 NOTE 인 이유는 파일 상한이다 — `.moai/config/sections/mx.yaml` 의
#   `anchor_per_file: 3` 을 이 파일이 이미 넷으로 넘겨 있었고, 더 얹지 않는다.)
#   고르는 기준이 두 가지로 갈릴 수 있고, 갈래를 잘못 잡으면 규칙이 조용히
#   무력해진다. (가) 「드롭 구간의 **첫** 큐 앞」 — 여기서 고른 것. (나) 「드롭 대역 큐
#   앞이면 언제나」 — 밀도 경로가 한 구간을 여러 큐로 쪼개면(`split_selections_for_density`)
#   드롭 안쪽 큐마다 앞 큐를 어둡게 만들어, 정본이 「짧게」라고 못박은 드롭 한복판에
#   밸리가 생긴다. 그래서 앞 큐의 **구간 색인이 다를 때만** 방아쇠다.
def _pre_drop_positions(
    ordered: Sequence[SongCueLookSelection],
) -> tuple[dict[int, int], tuple[SongCueWithheldDarkness, ...]]:
    """감광할 큐 번호 → 그 감광이 키우는 드롭의 큐 번호, 그리고 구조적으로 못 하는 자리.

    「드롭 대역」은 정본 §6 표의 **chorus · drop 행**이다. 그 행이 후렴과 드롭을 한 줄에
    묶은 것은 정본의 선택이고(``section_vocab.ROW_CHORUS``), §8 의 메커니즘 —
    「플래시 앞에 무슨 일이 있었는지가 만든다」 — 도 절정 일반에 대한 말이다. 어휘로
    후렴과 드롭을 가를 방법이 없으므로(같은 행·같은 대역), 가르는 척하지 않는다.
    """
    darken: dict[int, int] = dict()
    withheld: list[SongCueWithheldDarkness] = []
    for position, selection in enumerate(ordered):
        if not _is_drop_row(selection.section):
            continue
        drop_cue_number = position + 1
        if position == 0:
            withheld.append(
                SongCueWithheldDarkness(
                    section=selection.section,
                    cue_number=None,
                    drop_cue_number=drop_cue_number,
                    reason=DARKNESS_NO_PRECEDING_CUE,
                    detail=(
                        "the drop is this song's first cue; there is no preceding cue to "
                        "take brightness out of"
                    ),
                )
            )
            continue
        previous = ordered[position - 1]
        if previous.section.index == selection.section.index:
            # 같은 구간을 마디로 쪼갠 뒷큐다 — 드롭의 첫 큐가 아니므로 방아쇠가 아니다.
            continue
        darken[position] = drop_cue_number
    return darken, tuple(withheld)


def _is_drop_row(section: SongCueSection) -> bool:
    intent = intent_for_label(section.label)
    return intent is not None and intent.row == ROW_CHORUS


# @MX:NOTE: [AUTO] §8 안전 한계의 **유일한** 집행 지점 — 감광이 내려갈 수 있는 바닥.
#   (여기도 ANCHOR 가 아니라 NOTE 다 — 위와 같은 파일 상한 사유.)
#   이 함수가 지키는 것과 **못 지키는 것**을 갈라 두지 않으면 다음 사람이 이
#   바닥을 광도 보장으로 읽는다. 지키는 것: 이 규칙이 내보내는 ``Dimmer`` 는 절대
#   :data:`DARKNESS_FLOOR` 아래로 안 간다 — 블랙아웃(§8 이 허용한 세 형태 중 하나)을
#   **일부러 안 만든다**는 뜻이기도 하다. 못 지키는 것: 비상구 표지에 실제로 닿는 빛의
#   양. 객석 형상도 광도 모형도 저장소에 없고(실측 0건), 없는 모형을 지어내면 그 숫자가
#   안전 주장으로 인용된다. 그리고 이 바닥은 **우리가 내리는 값**만 막는다 — 라이브러리가
#   스스로 20 아래로 저작한 룩은 이 규칙이 올리지 않는다(올리는 것은 감광이 아니다).
def darkness_target(intent: SectionIntent) -> int:
    """이 §6 행에서 감광이 내려갈 목표값 — 행의 바닥, 단 안전 바닥 위로 잘린다.

    목표를 「행의 바닥」으로 잡는 것은 숫자를 안 지어내기 위해서다. 정본은 §8 에
    **얼마나** 빼라는 수를 안 줬고, 그 구간에 대해 정본이 실제로 적은 가장 어두운 값은
    §6 표 그 행의 아래끝이다.
    """
    return max(intent.brightness[0], DARKNESS_FLOOR)


def _pre_drop_darkened(
    look: Look,
    *,
    section: SongCueSection,
    cue_number: int,
    drop_cue_number: int | None,
) -> tuple[Look, SongCuePreDropDarkness | None, SongCueWithheldDarkness | None]:
    """드롭 앞 큐의 밝기를 뺀 룩, 그 기록, 또는 못 뺀 이유 (정본 §8 [HARD]).

    **형태를 고른 근거.** §8 은 세 형태를 허용한다 — 더 어두운 큐 · 짧은 블랙아웃 ·
    줄인 워시. 고른 것은 **줄인 워시**(앞 큐의 ``Dimmer`` 를 그 구간의 §6 바닥까지
    내린다)이고, 나머지 둘을 안 고른 이유가 각각 있다:

    * **짧은 블랙아웃**: §8 자신이 같은 절에서 비상구·통로·안전 표지의 가독을 요구한다.
      전 리그를 0 으로 보내는 큐를 자동으로 만들 근거가 이 계층에는 없다 — 객석 형상이
      없어 「그래도 표지는 읽힌다」를 **잴 수 없기** 때문이다.
    * **큐를 새로 끼워 넣기**: 끼운 큐에는 시작 시각이 필요하고, 자동 진행 경로가 그
      값으로 ``TrigTime`` 을 쓴다(:func:`_auto_advance_commands`). 정본이 드롭 앞 긴장에
      준 단위는 초가 아니라 **마디**(§6 「드롭 직전 마지막 마디」)이고, 마디 산술은
      ``cue_density`` 에 있으며 조립 단계는 BPM 을 받지 않는다. 초를 골라 끼우는 것은
      정본에 없는 숫자를 만드는 일이다.

    **같은 §6 행이면 안 한다**(:data:`DARKNESS_SAME_SIX_ROW`). 후렴 뒤의 후렴처럼 앞 큐가
    드롭과 같은 행이면, 정본이 그 행 전체를 80~100% 로 두므로 여기서 빼는 것은 절정 안쪽의
    요철이지 §8 이 말하는 어둠이 아니다. 이 갈래를 안 두면 부작용이 실측된다 — 반복 후렴의
    앞 회차들이 전부 행 바닥으로 눌려 §7.1 사다리의 상승(카드 t355)이 평평해진다.

    룩의 ``look_id`` 는 안 바꾼다 — 보고와 곡 사이 기억이 부르는 이름은 라이브러리의 그
    룩 그대로여야 한다. 바뀌는 것은 이 큐에 실리는 값 하나다.
    """
    if drop_cue_number is None:
        return look, None, None
    intent = intent_for_label(section.label)
    if intent is None:
        return (
            look,
            None,
            SongCueWithheldDarkness(
                section=section,
                cue_number=cue_number,
                drop_cue_number=drop_cue_number,
                reason=DARKNESS_SIX_ROW_ABSENT,
                detail=(
                    f"section label {section.label!r} matches no single §6 row, so the "
                    "standard gives no floor to take this cue down to"
                ),
            ),
        )
    if intent.row == ROW_CHORUS:
        return (
            look,
            None,
            SongCueWithheldDarkness(
                section=section,
                cue_number=cue_number,
                drop_cue_number=drop_cue_number,
                reason=DARKNESS_SAME_SIX_ROW,
                detail=(
                    f"this cue sits on the same §6 row {ROW_CHORUS!r} as the drop; the "
                    "standard keeps that whole row at 80~100%, so nothing taken out here "
                    "is the darkness §8 asks for"
                ),
            ),
        )
    before = _attribute_value(look, _DIMMER)
    if before is None:
        return (
            look,
            None,
            SongCueWithheldDarkness(
                section=section,
                cue_number=cue_number,
                drop_cue_number=drop_cue_number,
                reason=DARKNESS_NO_DIMMER,
                detail=f"look {look.look_id} carries no {_DIMMER} value",
            ),
        )
    target = darkness_target(intent)
    if before <= target:
        return (
            look,
            None,
            SongCueWithheldDarkness(
                section=section,
                cue_number=cue_number,
                drop_cue_number=drop_cue_number,
                reason=DARKNESS_ALREADY_DARK,
                detail=(
                    f"look {look.look_id} already sits at {before:g} which is at or below "
                    f"the §6 {intent.row!r} floor {target}"
                ),
            ),
        )
    darkened = replace(look, attributes=_at_value(look.attributes, _DIMMER, target))
    applied = SongCuePreDropDarkness(
        section=section,
        cue_number=cue_number,
        drop_cue_number=drop_cue_number,
        row=intent.row,
        before=before,
        after=target,
    )
    return darkened, applied, None


def _darkness_withheld(
    bundle: SongCueBundle, darken: Mapping[int, int]
) -> tuple[SongCueWithheldDarkness, ...]:
    """감광을 노린 큐 중 **무대에 안 닿은** 것들의 사유.

    저장되지 않은 큐의 감광은 없는 것과 같다 — 적용 기록만 남겨 두면 밸리가 있는 것처럼
    읽힌다. 그래서 저장 여부를 **번들이 완성된 뒤** 다시 보고, 안 저장됐으면 적용을
    사유로 바꾼다.
    """
    withheld: list[SongCueWithheldDarkness] = []
    for section in bundle.sections:
        drop_cue_number = darken.get(section.cue_number)
        if drop_cue_number is None:
            continue
        if section.commands:
            if section.darkness_withheld is not None:
                withheld.append(section.darkness_withheld)
            continue
        detail = "; ".join(
            part
            for part in (
                *(skipped.reason for skipped in section.skipped),
                section.darkness_withheld.reason if section.darkness_withheld else "",
            )
            if part
        )
        withheld.append(
            SongCueWithheldDarkness(
                section=section.section,
                cue_number=section.cue_number,
                drop_cue_number=drop_cue_number,
                reason=DARKNESS_CUE_NOT_STORED,
                detail=detail or "cue stored nothing",
            )
        )
    return tuple(withheld)


def _attribute_value(look: Look, attribute: str) -> float | None:
    for value in look.attributes:
        if value.name == attribute:
            return value.value
    return None


def _at_value(
    values: Sequence[AttributeValue], attribute: str, target: float
) -> tuple[AttributeValue, ...]:
    """한 속성만 목표값으로 바꾼 값들 — 그 속성이 없으면 그대로.

    없는 축을 만들어 넣지 않는 것은 :func:`escalate_attributes` 와 같은 규율이다.
    """
    return tuple(
        AttributeValue(attribute, target) if value.name == attribute else value for value in values
    )


def _guard_bundle_collision(bundle: SongCueBundle) -> None:
    """면제 대상이 아닌 줄이 번들 안에서 두 번 나오면 거절한다.

    이 그물이 잡는 것은 위 :func:`_movement_carrier` 의 규칙이 깨진 경우다. 움직임이 없는
    번들에서는 값 라인이 `emitted` 로, Store 라인이 큐 번호로 이미 유일하므로 이 함수는
    아무것도 바꾸지 않는다 — 무회귀 성질.
    """
    seen: set[str] = set()
    for command in bundle.commands:
        if is_programmer_state(command):
            continue
        if command in seen:
            raise SongCueBundleError(
                f"{MOVEMENT_LINE_COLLISION}: {command!r} appears twice in one bundle; the "
                "run_commands dedupe drops the second occurrence and the affected Store "
                "runs against an incomplete programmer — silently, because a stored "
                "phaser cue is indistinguishable from an empty one"
            )
        seen.add(command)


def render_songcue_report(bundle: SongCueBundle) -> str:
    parts = [bundle.song_title, bundle.sequence_name]
    parts.extend(section.section.name for section in bundle.sections)
    parts.extend(skipped.detail for skipped in bundle.skipped)
    return "\n".join(part for part in parts if part)


def select_sequence_number(sequences_section: Mapping[str, object]) -> int:
    unavailable = sequences_section.get("reason")
    if isinstance(unavailable, str) or sequences_section.get("ok") is False:
        raise SequenceNumberError(SEQUENCE_UNAVAILABLE)
    if sequences_section.get("truncated"):
        raise SequenceNumberError(SEQUENCE_TRUNCATED)
    occupied = _sequence_numbers(sequences_section)
    candidate = 1
    while candidate in occupied:
        candidate += 1
    return candidate


def observed_user_cue_count(sequence_payload: Mapping[str, object]) -> int:
    if sequence_payload.get("truncated"):
        raise SequenceNumberError(SEQUENCE_TRUNCATED)
    node = sequence_payload.get("node")
    child_count = node.get("childCount") if isinstance(node, Mapping) else None
    if not isinstance(child_count, int):
        raise SequenceNumberError(SEQUENCE_UNAVAILABLE)
    return max(0, child_count - _IMPLICIT_SYSTEM_CUE_COUNT)


def build_songcue_timing(
    bundle: SongCueBundle,
    *,
    timecode_number: int,
    axes: SongCueTimingAxes | None = None,
) -> SongCueTimingPlan:
    if isinstance(timecode_number, bool) or timecode_number < 1:
        raise ValueError(f"timecode_number must be positive: {timecode_number!r}")
    selected_axes = axes or SongCueTimingAxes()
    timecode_commands: tuple[str, ...] = ()
    auto_advance_commands: tuple[str, ...] = ()
    skipped: list[SongCueTimingSkip] = []
    if selected_axes.timecode_go:
        timecode_commands = _timecode_commands(bundle, timecode_number)
    else:
        skipped.append(
            SongCueTimingSkip(axis=TIMECODE_DESCOPE, reason=selected_axes.timecode_skip_reason)
        )
    if selected_axes.auto_advance_go:
        auto_advance_commands = _auto_advance_commands(bundle)
    else:
        skipped.append(
            SongCueTimingSkip(
                axis=AUTO_ADVANCE_DESCOPE, reason=selected_axes.auto_advance_skip_reason
            )
        )
    return SongCueTimingPlan(
        commands=timecode_commands + auto_advance_commands,
        timecode_commands=timecode_commands,
        auto_advance_commands=auto_advance_commands,
        skipped_axes=tuple(skipped),
    )


def plan_prepare_songcue_timing(
    bundle: SongCueBundle,
    request: Mapping[str, object],
    *,
    axes: SongCueTimingAxes | None = None,
) -> SongCueTimingPlan:
    return build_songcue_timing(
        bundle,
        timecode_number=_prepare_songcue_timecode_number(request),
        axes=axes,
    )


def _parse_section(raw: Mapping[str, object] | Sequence[object], index: int) -> SongCueSection:
    section = _raw_section(raw)
    name = section.name.strip()
    if not name:
        raise ValueError(f"section index {index} has an empty name")
    dynamics = _section_dynamics(name)
    label, variant = _label_and_variant(name)
    return SongCueSection(
        name=name,
        start_ms=normalise_start_ms(section.start),
        index=index,
        dynamics=dynamics,
        requires_explicit_dynamics=dynamics is None,
        label=label,
        variant=variant,
    )


def _label_and_variant(name: str) -> tuple[str, str]:
    """이름을 라벨과 변형 표시로 가른다(정본 §3).

    변형은 라벨을 **바꾸지 않는다** — 마지막 후렴이 편곡이 달라도 후렴이므로, 프라임이
    붙은 이름은 같은 라벨의 다음 회차로 센다. 프라임만 남는 이름은 라벨이 없으므로
    변형으로 읽지 않는다.
    """
    stripped = name.rstrip(VARIANT_PRIME).strip()
    if stripped and stripped != name:
        return stripped, VARIANT_PRIME
    return name, ""


def _numbered_by_label(sections: Sequence[SongCueSection]) -> tuple[SongCueSection, ...]:
    """라벨마다 등장 순번을 붙인다 — 표준 데이터셋이 주지 않는 필드(정본 §3).

    저장소의 회차 카운터는 이 함수 **하나**다. 큐 이름의 중복 해소(:func:`_cue_names`)도
    같은 값을 읽는다 — 두 벌을 두면 이름이 가리키는 회차와 사다리가 오르는 회차가 갈리고,
    갈린 순간 감독이 화면에서 읽는 「후렴 2」와 콘솔에 실제로 나간 세기가 다른 것이 된다.
    """
    seen: dict[str, int] = dict()
    numbered: list[SongCueSection] = []
    for section in sections:
        seen[section.label] = seen.get(section.label, 0) + 1
        numbered.append(replace(section, instance=seen[section.label]))
    return tuple(numbered)


def _map_section_to_look(
    *,
    section: SongCueSection,
    ordered_looks: Sequence[Look],
    explicit_dynamics: int | None,
    already_used: frozenset[str] = frozenset(),
    previous: Look | None = None,
    returning: Look | None = None,
) -> SongCueLookSelection:
    if explicit_dynamics is not None:
        requested_dynamics = (_validated_dynamics(explicit_dynamics, section.index),)
    elif section.dynamics is None:
        return SongCueLookSelection(
            section=section, requested_dynamics=(), reason=EXPLICIT_DYNAMICS_REQUIRED
        )
    else:
        requested_dynamics = section.dynamics

    matches = tuple(look for look in ordered_looks if look.dynamics in requested_dynamics)
    if not matches:
        return SongCueLookSelection(
            section=section, requested_dynamics=requested_dynamics, reason=UNMAPPED_LOOK
        )
    ranked, reuse_reason = _ranked_against_history(
        matches,
        already_used,
        previous=previous,
        intent=intent_for_label(section.label),
        returning=returning,
    )
    return SongCueLookSelection(
        section=section,
        requested_dynamics=requested_dynamics,
        look=ranked[0],
        dynamics_matches=ranked,
        reuse_reason=reuse_reason,
    )


def _ranked_against_history(
    matches: Sequence[Look],
    already_used: frozenset[str],
    *,
    previous: Look | None = None,
    intent: SectionIntent | None = None,
    returning: Look | None = None,
) -> tuple[tuple[Look, ...], str | None]:
    """후보를 줄 세운다 — 곡 사이 신선도(t358) 바깥, 구간 의도와 대비(t360) 안.

    **두 카드가 겹쳐 사는 자리이므로 순서에 계약이 있다.**

    1. 앞 곡이 안 쓴 룩이 앞, 쓴 룩이 뒤(카드 t358, 정본 §7 후반: 곡 사이 재사용은 결함).
       이것이 **가장 바깥**이다 — 곡 안에서 아무리 대비가 커도 앞 곡을 되쓰는 것보다
       먼저 오지 않는다.
    2. 각 묶음 **안에서** 정본 §6 의 구간 의도 → 앞 큐와의 대비 → 기존 전순서
       (``section_intent.ordering_key``). 카드 t360 이 여기를 채웠다.

    쓴 룩을 목록에서 **빼지 않는** 것은 t358 이 정한 형상 그대로다. 뒤에 남겨 두면 두
    성질이 함께 산다: 새 룩이 있으면 그것이 선두라 곡 B 가 곡 A 의 룩으로 열리지 않고,
    새 룩이 리그에 하나도 안 묶이면 :func:`_select_bindable` 이 뒤쪽의 쓴 룩을 찾아내
    큐가 사라지지 않는다. 빼 버리면 두 번째 성질이 「큐 없음」으로 바뀌는데, 재사용보다
    나쁘다.

    **고치기 전과 바이트 동일한 갈래**가 남아 있다: §6 행이 없는 라벨 + 앞 큐 없음이면
    ``ordering_key`` 가 ``(dynamics, look_id)`` 로 퇴화하고, 그 순서는
    ``busking.looks_for_genre`` 가 준 것과 같다.

    한계 하나를 적어 둔다: 밀도 경로(:func:`split_selections_for_density`)는 이 목록을
    **회전**시키므로, 한 구간이 여러 큐로 쪼개지면 여기서 정한 선두가 그대로 나가지
    않는다. 저장 직전 :func:`_select_bindable` 이 목록 앞에서부터 리그에 묶이는 첫 룩을
    다시 고르는 것도 같은 성질이다. 그 갈래는 여기서 막지 않고 **저장된 결과를 재서**
    보고한다(``prepare_songcue`` 의 ``cross_song_looks.reused_look_ids``) — 의도가 아니라
    실제로 나간 것을 재는 쪽이 참이다.
    """
    fresh = tuple(look for look in matches if look.look_id not in already_used)
    if not fresh:
        ranked = sorted_candidates(matches, previous=previous, intent=intent, returning=returning)
        return ranked, LOOK_POOL_EXHAUSTED
    stale = tuple(look for look in matches if look.look_id in already_used)
    ranked = sorted_candidates(
        fresh, previous=previous, intent=intent, returning=returning
    ) + sorted_candidates(stale, previous=previous, intent=intent, returning=returning)
    return ranked, None


# @MX:NOTE: [AUTO] 이 리그에서 룩이 「묶인다」는 것의 **유일한 정의**. 선택
#   (`_select_bindable`)과 저장(`_section_bundle`)이 같은 술어를 봐야 한다 —
#   둘이 갈리면 선택기가 고른 룩을 번들이 건너뛰고, 그 상태는 고치기 전보다 나쁘다.
#   역할 **하나만** 묶여도 참이라는 것이 이 규칙의 핵심이고, ballad 가 cyc 없는
#   리그에서도 멀쩡했던 이유다(첫 D1 룩이 배경+백라이트를 함께 갖고 있었다).
def _bound_groups(look: Look, resolution: RoleResolution) -> dict[str, tuple[GroupCandidate, ...]]:
    """이 룩의 역할 중 이 리그의 그룹에 묶인 것들.

    ``dict()`` 는 취향이 아니다 — 이 모듈은 매핑 리터럴을 **한 개도** 두지 않는
    규율이 있고(``test_songcue_sections`` 가 AST 로 잰다), 그래야 다이내믹스
    어휘가 ``matching`` 바깥에서 다시 정의될 자리가 생기지 않는다.
    """
    bound: dict[str, tuple[GroupCandidate, ...]] = dict()
    for role in look.roles:
        candidates = resolution.groups_for(role)
        if candidates:
            bound[role] = candidates
    return bound


def _select_bindable(look: Look, matches: Sequence[Look], resolution: RoleResolution) -> Look:
    """요청한 다이내믹스 안에서 이 리그에 실제로 묶이는 **첫** 룩.

    하나도 안 묶이면 ``look`` — 오늘의 선택 — 을 그대로 돌려준다. 그래야 큐를 못
    세우는 구간의 ``role_unmapped`` 보고가 지금과 같은 룩·같은 사유로 남는다.

    cyc 를 갖춘 리그에서는 첫 룩이 이미 묶이므로 이 함수가 그 룩을 돌려주고,
    저장되는 것은 고치기 전과 같다(무회귀 성질 —
    ``test_songcue_rig_aware_look.TestCycRigIsUnchanged`` 가 실측한다).
    """
    for candidate in matches:
        if _bound_groups(candidate, resolution):
            return candidate
    return look


# @MX:ANCHOR: [AUTO] 프론트 필·찍는 액센트 그룹은 다른 그룹이라 이 룩 자신의 값
#   라인에 안 실린다 — `run_commands` 의 전곡 단위 중복 제거를 피하려면 이 층도
#   자기만의 값으로 유일해야 한다 (카드 t377·t378).
# @MX:REASON: `_guard_bundle_collision` 이 지키는 사실 그대로다 — 한 곡의 명령 전체가
#   **하나의** `run_commands` 호출로 나가고, 그 콘솔 쪽 중복 제거는 `Clear`·
#   `ClearAll`·`Group <n>`/`Fixture <n>` 만 면제한다(`server/fx/instantiate.py`
#   `_PROGRAMMER_STATE_COMMANDS`). 프론트 필 값을 매 큐 **같은 문자열**로 내면
#   2번째부터는 콘솔이 조용히 버린다 — 이 카드가 고치려는 결함(연주자가 안 보임)이
#   그대로 남는 것과 같다. 그래서 이 두 층도 기준 룩과 같은 ``emitted`` 사전을
#   읽고 써서, 겹치면 밝기를 한 걸음씩 올려 유일한 문자열을 찾는다.
def _unique_floor_climb(
    floor: int,
    ceiling: int,
    other_attributes: tuple[AttributeValue, ...],
    emitted: Mapping[str, tuple[int, int, str]],
) -> tuple[int, str] | None:
    """``Dimmer`` 를 ``floor`` 부터 ``ceiling`` 까지 올려 ``emitted`` 와 안 겹치는
    값 라인을 찾는다. 못 찾으면 ``None`` — 그 구간에서는 채우지 않는다(마지막
    수단의 건너뜀, 사다리와 같은 규율).
    """
    for dimmer in range(floor, ceiling + 1):
        candidate = _values_line((AttributeValue(_DIMMER, dimmer), *other_attributes))
        if candidate not in emitted:
            return dimmer, candidate
    return None


#: 프론트 필이 올라갈 수 있는 위쪽 끝 — 정본 §6 표 intro 행(20~40%)의 위쪽 끝이다.
#: 그 위로는 §6 표에서 "밝은 워시"가 시작되는 구간(빌드 40~55% 부터)과 겹쳐, §6.2
#: 가 금지한 "밝은 워시"가 된다. 프론트 필은 이 상한을 넘지 않는다 — 넘어야만
#: 유일해지는 자리라면 채우지 않는다(:data:`_unique_floor_climb` 의 마지막 수단).
_FRONT_FILL_CEILING = 40


def _front_fill(
    bound: Mapping[str, tuple[GroupCandidate, ...]],
    resolution: RoleResolution,
    emitted: dict[str, tuple[int, int, str]],
    *,
    section: SongCueSection,
    cue_number: int,
) -> tuple[tuple[str, ...], tuple[GroupCandidate, ...], float | None]:
    """프론트 필 명령 두 줄(그룹 선택 + 값)과 그 그룹들 — 채울 것이 없으면 ``((), ())``.

    세 갈래에서 빈 것을 돌려준다. 이미 프론트가 묶여 있으면(``bound`` 에 이미
    :data:`FRONT_FILL_ROLE`) 룩이 스스로 프론트를 실은 것이므로 그 값을 존중하고
    아무것도 더하지 않는다 — 라이브러리가 스스로 지은 값을 이 층이 덮어 쓰지 않는
    것은 :func:`darkness_target` 이 라이브러리가 스스로 20 아래로 저작한 룩을 안
    올리는 것과 같은 규율이다. 리그에 프론트로 묶일 그룹이 아예 없으면
    (``resolution.groups_for`` 가 빈 튜플) 채울 대상이 없다. :data:`FRONT_FILL_DIMMER`
    부터 :data:`_FRONT_FILL_CEILING` 까지 다 겹치면(``emitted`` 가 이미 그 구간을
    전부 쥐고 있으면) 채우지 않는다 — 값을 지어내는 대신 못 채웠다고 인정한다.
    """
    if FRONT_FILL_ROLE in bound:
        return (), (), None
    groups = resolution.groups_for(FRONT_FILL_ROLE)
    if not groups:
        return (), (), None
    found = _unique_floor_climb(FRONT_FILL_DIMMER, _FRONT_FILL_CEILING, FRONT_FILL_COLOR, emitted)
    if found is None:
        return (), (), None
    dimmer, candidate = found
    emitted[candidate] = (section.index, cue_number, "front-fill")
    return (_selection_line(groups), candidate), groups, dimmer


# @MX:ANCHOR: [AUTO] 사다리의 찍는 액센트가 블라인더·스트로브 그룹을 켠다 (정본 §7.1
#   표, 카드 t378).
# @MX:REASON: 이 룩 자신의 값(:func:`escalate_attributes`)은 블라인더·스트로브
#   칸에서 안 바뀐다 — 다른 그룹이기 때문이다. 그래서 사다리가 고른 칸
#   (``rungs``)을 여기서 다시 읽어 실제 명령을 만든다. 리그에 그 그룹이 없거나
#   (:func:`_accent_fixture_commands` 가 빈 튜플을 돌려줌) §6 행을 못 찾으면
#   (:func:`intent_for_label` 이 ``None``) 칸은 회전했지만 무대에는 아무것도 안
#   나간다 — 없는 축에 값을 만들어 보내지 않는 것이 이 계층의 규율이다.
def _accent_fixture_commands(
    rungs: Sequence[str],
    *,
    section: SongCueSection,
    cue_number: int,
    resolution: RoleResolution,
    emitted: dict[str, tuple[int, int, str]],
) -> tuple[tuple[str, ...], str | None, tuple[GroupCandidate, ...], float | None]:
    """찍는 액센트가 블라인더·스트로브를 골랐으면 그 명령 두 줄과 칸·그룹·값, 아니면 빈 값들.

    :class:`SongCueAccentFixture` 는 호출자(:func:`_section_bundle`)가 이 네 값으로
    조립한다.

    ``rungs`` 에 :data:`LADDER_BLINDER_OR_FLASH`/:data:`LADDER_STROBE_HIT` 가 최대
    하나만 있다고 전제한다(§6.1 [HARD] "한 큐에 찍는 액센트 하나" —
    :func:`_climb_rungs` 가 이미 지킨다).

    밝기는 §6 행의 **아래끝**에서 시작해 **위끝까지만** 오른다(:data:`_ACCENT_FIXTURE_ROLE`
    독스트링 — 최대치는 "마지막 드롭" 하나의 자리다). 그 구간이 이미 다 겹치면 이번
    큐는 채우지 않는다.
    """
    rung = next((r for r in rungs if r in _ACCENT_FIXTURE_ROLE), None)
    if rung is None:
        return (), None, (), None
    role = _ACCENT_FIXTURE_ROLE[rung]
    groups = resolution.groups_for(role)
    if not groups:
        return (), None, (), None
    intent = intent_for_label(section.label)
    if intent is None:
        return (), None, (), None
    floor, ceiling = intent.brightness
    found = _unique_floor_climb(floor, ceiling, (), emitted)
    if found is None:
        return (), None, (), None
    dimmer, candidate = found
    emitted[candidate] = (section.index, cue_number, f"accent-{rung}")
    commands = (_selection_line(groups), candidate)
    return commands, rung, groups, dimmer


# SPEC-LDCLIMAX-001 D3 — 색 스냅 판정 상태를 곡 전체에서 어떻게 배선하는가.
#
# 후보였던 셋: (1) `_section_bundle` 이 갱신하는 가변 딕셔너리(``emitted`` 와 같은
# 자리) — 그런데 이 값은 **순서 의존**이다: `_rescue_value_line_collisions` 가 앞선
# 큐를 나중에 다시 짓는(rebuild) 순간, "누적해 온 previous_color"는 그 rebuild
# 시점의 곡 상태를 반영하지 못한다(그 시점 이전 cue_number 기준이 아니라 "지금까지
# 처리한 순서" 기준이 되어 버린다). (2) 함수 기본값(`= None`) — 안 쓴다: 요청이
# 명시적으로 금지했고, 무엇보다 "곡 전체 상태"는 태생적으로 가변인데 함수 기본값은
# 한 번만 평가되므로 두 번째 곡을 조립할 때 첫 곡의 상태가 새어 든다(고전적인 가변
# 기본값 결함, `_look_color` 근방 규율과 같은 방향). (3, 채택) **순수 함수로,
# 이미 조립된 번들 목록에서 매번 다시 읽는다.** ``_assembled`` 의 진행 중 목록도
# ``_rescue_value_line_collisions`` 가 재조립 중인 목록도 모두 "지금 이 cue_number
# 앞에 무엇이 실제로 저장돼 있는가"를 그대로 담고 있으므로, 어느 재조립 순서에서
# 호출해도 같은 답을 낸다(멱등) — 전역도 가변 기본값도 아닌, 호출자가 매번 넘기는
# 명시 인자 하나(``section_bundles``)로 충분하다.
def _previous_stored_color(
    section_bundles: Sequence[SongCueSectionBundle], *, before_cue_number: int
) -> tuple[AttributeValue, ...] | None:
    """``before_cue_number`` 보다 앞이고 실제로 저장된(``commands`` 가 있는) 큐 중
    가장 최근의 색 — REQ-LDCLIMAX-004 판정 입력. 없으면 ``None``(첫 저장 큐 또는
    앞선 큐 전부 색 채널이 없음).
    """
    for bundle in reversed(section_bundles):
        if bundle.cue_number >= before_cue_number or not bundle.commands:
            continue
        look = bundle.selection.look
        if look is None:
            continue
        color = _look_color(look)
        if color:
            return color
    return None


def _label_return_palette(
    section_bundles: Sequence[SongCueSectionBundle], *, label: str, before_cue_number: int
) -> frozenset[tuple[AttributeValue, ...]]:
    """이 라벨의 1회차가 ``before_cue_number`` 앞에서 실제로 저장한 색 집합 —
    REQ-LDCLIMAX-002 판정 입력(§7 색 복귀 규율). 1회차가 아직 저장되지 않았으면
    빈 집합이고, 빈 집합은 "제한 없음"으로 읽힌다(:func:`_color_snap_is_effective`).
    """
    colors: set[tuple[AttributeValue, ...]] = set()
    for bundle in section_bundles:
        if bundle.cue_number >= before_cue_number or not bundle.commands:
            continue
        if bundle.section.label != label or bundle.section.instance != 1:
            continue
        look = bundle.selection.look
        if look is None:
            continue
        color = _look_color(look)
        if color:
            colors.add(color)
    return frozenset(colors)


def _section_bundle(
    *,
    selection: SongCueLookSelection,
    cue_number: int,
    cue_name: str,
    sequence_number: int,
    resolution: RoleResolution,
    emitted: dict[str, tuple[int, int, str]],
    section_bundles: Sequence[SongCueSectionBundle],
    movement: MovementPlan | None = None,
    drop_cue_number: int | None = None,
    allow_strobe: bool = False,
    disable_color_snap: bool = False,
) -> SongCueSectionBundle:
    # SPEC-LDCLIMAX-001 D3 — 색 스냅 판정이 필요로 하는, 곡 전체를 훑어야만 아는
    # 상태 둘(직전 저장 큐의 색·이 라벨 1회차가 쓴 색 집합)을 여기서 한 번만
    # 계산해 아래 호출자 전량에 명시 인자로 흘려보낸다. ``section_bundles`` 는
    # 이 큐 앞에 이미 조립된 번들들이다 — `_assembled` 의 진행 중 목록이거나
    # `_rescue_value_line_collisions` 가 재조립 중인 목록이거나, 어느 쪽이든
    # "이 cue_number 이전"의 최신 상태를 읽는다(전역도 가변 기본값도 아니다).
    previous_color = _previous_stored_color(section_bundles, before_cue_number=cue_number)
    label_palette = _label_return_palette(
        section_bundles, label=selection.section.label, before_cue_number=cue_number
    )
    if selection.look is None:
        skipped = SongCueSkippedSection(
            section=selection.section,
            cue_number=cue_number,
            reason=selection.reason or UNMAPPED_LOOK,
            detail=selection.reason or UNMAPPED_LOOK,
        )
        return SongCueSectionBundle(
            section=selection.section,
            cue_number=cue_number,
            cue_name=cue_name,
            selection=selection,
            skipped=(skipped,),
        )

    look = _select_bindable(selection.look, selection.dynamics_matches, resolution)
    if look is not selection.look:
        # 보고에 실리는 선택과 번들이 실제로 세운 룩이 어긋나지 않게 한다.
        selection = replace(selection, look=look)
    bound = _bound_groups(look, resolution)
    unmapped: list[UnmappedRole] = []
    for role in look.roles:
        if role in bound:
            continue
        entry = resolution.unmapped_for(role)
        if entry is not None:
            unmapped.append(entry)
    groups = _selected_groups(bound)
    if not groups:
        skipped = SongCueSkippedSection(
            section=selection.section,
            cue_number=cue_number,
            reason=ROLE_UNMAPPED,
            detail="; ".join(entry.reason for entry in unmapped),
        )
        return SongCueSectionBundle(
            section=selection.section,
            cue_number=cue_number,
            cue_name=cue_name,
            selection=selection,
            skipped=(skipped,),
            unmapped=tuple(unmapped),
            bound=bound,
        )

    # 감광은 **값 라인을 만들기 전에** 온다(정본 §8). 사다리(§7.1)는 충돌이 방아쇠인
    # 해소 장치라 어두워진 값에서 다시 오르기 시작한다 — 그래서 감광한 큐가 앞 큐와
    # 값이 겹치면 밝기가 칸당 한 걸음(`_HIT_STEP`)씩 되올라갈 수 있고, 그 사실은
    # `darkness` 의 두 숫자와 실제 값 라인을 나란히 보면 읽힌다.
    look, darkness, darkness_withheld = _pre_drop_darkened(
        look,
        section=selection.section,
        cue_number=cue_number,
        drop_cue_number=drop_cue_number,
    )
    values, rungs = _distinct_values_line(
        look,
        selection.section,
        emitted,
        resolution=resolution,
        allow_strobe=allow_strobe,
        disable_color_snap=disable_color_snap,
        previous_color=previous_color,
        label_palette=label_palette,
    )
    if values is not None:
        # 카드 t382 — 이 회차가 양보로 받은 자리든 기준값 자리든, 반복 회차(instance
        # >= 2)는 찍는 액센트를 하나 받는다(정본 §7.1). `_distinct_values_line` 이
        # 충돌 없이 곧바로 기준값(``rungs=()``)이나 얕은 깊이로 끝났다고 해서 액센트를
        # 건너뛰지 않는다 — 자세한 이유는 :func:`_ensure_marking_accent` 독스트링.
        # 유보 여부는 여기서 버린다(SPEC-LDACCENT-001) — 재배열 뒤 `_finalize_marking_accents`
        # 가 최종 사다리를 기준으로 다시 판정하고 기록하는 것이 권위 있는 자리다.
        values, rungs, _withheld = _ensure_marking_accent(
            escalate_attributes(look.attributes, rungs),
            selection.section,
            rungs,
            values,
            emitted,
            look=look,
            resolution=resolution,
            allow_strobe=allow_strobe,
            disable_color_snap=disable_color_snap,
            previous_color=previous_color,
            label_palette=label_palette,
        )
    if values is None:
        previous_section, previous_cue, previous_look = emitted[_values_line(look.attributes)]
        skipped = SongCueSkippedSection(
            section=selection.section,
            cue_number=cue_number,
            reason=VALUE_LINE_COLLISION,
            detail=(
                f"value line matches section {previous_section} "
                f"cue {previous_cue} look {previous_look}; "
                "ladder exhausted ("
                + ", ".join(
                    _exhausted_rungs(
                        allow_strobe=allow_strobe,
                        disable_color_snap=disable_color_snap,
                        look=look,
                        resolution=resolution,
                        section=selection.section,
                        previous_color=previous_color,
                        label_palette=label_palette,
                    )
                )
                + ")"
            ),
            collides_with_section_index=previous_section,
            collides_with_cue_number=previous_cue,
        )
        return SongCueSectionBundle(
            section=selection.section,
            cue_number=cue_number,
            cue_name=cue_name,
            selection=selection,
            skipped=(skipped,),
            bound=bound,
            darkness_withheld=darkness_withheld,
        )
    emitted[values] = (selection.section.index, cue_number, look.look_id)
    # 프론트 필 — 정본 §6.2 [HARD], 카드 t377. 이 룩이 프론트를 안 실었어도 이 층이
    # 채운다("항상 유지"는 선택된 룩과 무관하다는 뜻). 값 라인 **뒤**, 움직임/액센트
    # 그룹 **앞**에 둔다 — 기준 룩이 먼저, 그 다음이 "항상 있는" 보정광, 마지막이 이
    # 큐에서만 튀는 액센트라는 층 순서다.
    front_fill_commands, front_fill_groups, front_fill_dimmer = _front_fill(
        bound, resolution, emitted, section=selection.section, cue_number=cue_number
    )
    front_fill = (
        SongCueFrontFill(
            section=selection.section,
            cue_number=cue_number,
            groups=tuple(group.number for group in front_fill_groups),
            dimmer=front_fill_dimmer,
        )
        if front_fill_groups
        else None
    )
    # 찍는 액센트 그룹 — 블라인더·스트로브(카드 t378). 사다리 칸 계산
    # (:func:`_distinct_values_line`)은 이 룩 자신의 값만 보므로 다른 그룹의 명령은
    # 여기서 따로 만든다. 회차가 그 칸을 안 골랐거나(``rungs`` 에 없음) 리그에 그 그룹이
    # 없으면 아무것도 안 낸다 — 없는 축에 값을 만들어 보내지 않는 것은
    # :func:`escalate_attributes` 와 같은 규율이다.
    accent_commands, accent_rung, accent_groups, accent_dimmer = _accent_fixture_commands(
        rungs,
        section=selection.section,
        cue_number=cue_number,
        resolution=resolution,
        emitted=emitted,
    )
    accent_fixture = (
        SongCueAccentFixture(
            section=selection.section,
            cue_number=cue_number,
            rung=accent_rung,
            groups=tuple(group.number for group in accent_groups),
            dimmer=accent_dimmer,
        )
        if accent_rung is not None
        else None
    )
    # 움직임 줄은 **값 라인 뒤**에 온다: 기준 룩이 먼저 프로그래머에 실리고, 페이저는 그
    # 위에 더하는 액센트다(정본 §6.1 「한 큐에 하나만」과 같은 방향). 이 순서가 이 카드의
    # 유일한 미실측 가정이다 — 정적 Dimmer·색과 2스텝 Pan 을 한 캡처에 섞었을 때 정적
    # 값이 살아 있는지는 콘솔에서 확인해야 알 수 있고, 저장된 페이저 큐는 빈 큐와 구별되지
    # 않으므로 사후 판독으로는 못 가른다(`server/fx/instantiate.py` 머리의 @MX:WARN).
    # 페이드는 ``Store`` 줄에 붙는다 — 문면을 만드는 것은 이 파일이 아니라
    # ``server.design.cue_fade.store_with_fade`` 하나다(카드 t363). ``Property 'Fade'``
    # 는 금지이고(`docs/handoff/2026-08-15-timeline-workflow-handoff.md:19`), 그 규율이
    # 두 소비자에 흩어지지 않게 하려고 조립을 한 자리로 모았다.
    #
    # 색 스냅이 확정됐으면(REQ-LDCLIMAX-003) 라벨이 정하는 페이드 대신 정확히 0 을
    # 강제한다 — "즉시 전환"은 크로스페이드가 아니라 하드 스냅이다. 값은 이미
    # ``look`` 자신의 것과 같으므로(REQ-LDCLIMAX-002 가 이미 §7 집합 안임을 확인했다)
    # 색·Dimmer·Zoom·Iris 등 다른 속성 값은 색 스냅이 없었을 때와 동일하게 남는다.
    if LADDER_COLOR_SNAP in rungs:
        fade = SectionFade(
            line=LADDER_COLOR_SNAP,
            seconds=0.0,
            source="REQ-LDCLIMAX-003 — 색 스냅은 페이드를 0 으로 강제한다(즉시 전환)",
        )
    else:
        fade = fade_for_label(selection.section.label)
    commands = (
        _CLEAR,
        _selection_line(groups),
        values,
        *front_fill_commands,
        *accent_commands,
        *(movement.commands if movement is not None else ()),
        store_with_fade(
            f"Store Sequence {sequence_number} Cue {cue_number} '{cue_name}'",
            fade.seconds if fade is not None else None,
        ),
        _CLEAR,
    )
    return SongCueSectionBundle(
        section=selection.section,
        cue_number=cue_number,
        cue_name=cue_name,
        selection=selection,
        commands=commands,
        bound=bound,
        ladder=rungs,
        movement=movement,
        fade=fade,
        darkness=darkness,
        darkness_withheld=darkness_withheld,
        front_fill=front_fill,
        accent_fixture=accent_fixture,
    )


# @MX:ANCHOR: [AUTO] 값이 같은 구간을 **버리지 않는다** — 곡 안의 반복은 규범이고,
#   되돌아와야 하는 룩을 지우는 것이 결함이었다(정본 §7 · §12 항목 3).
# @MX:REASON: 고치기 전에는 값 라인이 앞 큐와 같으면 그 구간을 통째로 건너뛰었고, 실측
#   5구간 EDM 입력이 큐 3장이 됐다(후렴이 드롭과 값이 같아 둘이 사라졌다). 되돌리기 쉬운
#   유혹이 둘 있다 — (가) 충돌하면 다시 버리기, (나) 회차와 무관하게 늘 한 칸 올리기.
#   (가)는 이 카드가 없애려는 결함 그대로이고, (나)는 충돌이 없는 입력의 콘솔 명령까지
#   바꿔서 무회귀 성질을 깨뜨린다. 사다리는 **충돌이 방아쇠**이고 **칸은 회차가 정한다**.
def _distinct_values_line(
    look: Look,
    section: SongCueSection,
    emitted: Mapping[str, tuple[int, int, str]],
    *,
    resolution: RoleResolution,
    allow_strobe: bool = False,
    disable_color_snap: bool = False,
    previous_color: tuple[AttributeValue, ...] | None,
    label_palette: frozenset[tuple[AttributeValue, ...]],
) -> tuple[str | None, tuple[str, ...]]:
    """앞선 큐와 겹치지 않는 값 라인과 그때 더한 사다리 칸들. 못 만들면 ``(None, ())``.

    기준 룩이 이미 유일하면 그대로 돌려준다 — 충돌이 없는 입력이 내는 명령은 고치기 전과
    **바이트 동일**하다. 겹치면 사다리를 오르는데, 시작 칸은 회차가 정하고(정본 §3: 세기는
    회차가 정한다) 거기서도 겹치면 한 칸씩 더 올린다. 마지막 칸까지 값이 안 달라지면 —
    이미 천장에 있거나 리그가 그 축을 안 갖고 있으면 — 그때만 큐를 못 세운다.

    **한 구간 안에서 쪼갠 큐끼리 겹치는 것은 사다리의 일이 아니다.** 정본 §7 의 상승은
    구간의 **반복 회차** 사이에서 일어난다. 마디 경계로 쪼갠 큐들은 같은 구간의 같은 회차
    이므로, 여기서 밝기를 올리면 구간 하나가 도중에 세어진다 — 밀도 경로의 축(강도는
    유지하고 그림만 교체)을 정면으로 어기는 것이다. 그래서 같은 구간끼리의 충돌은 예전처럼
    건너뛴다.

    ``allow_strobe`` 는 호출자가 밝힌 세트 위치 신호다(:data:`LADDER_STROBE_HIT` 독스트링)
    — 이 함수 자신은 몇 번째 곡인지 모른다.
    """
    base = _values_line(look.attributes)
    previous = emitted.get(base)
    if previous is None:
        return base, ()
    if previous[0] == section.index:
        return None, ()
    max_climb = _max_climb(
        allow_strobe=allow_strobe,
        disable_color_snap=disable_color_snap,
        look=look,
        resolution=resolution,
        section=section,
        previous_color=previous_color,
        label_palette=label_palette,
    )
    for depth in range(_ladder_start(section), max_climb + 1):
        rungs = _climb_rungs(
            depth,
            allow_strobe=allow_strobe,
            disable_color_snap=disable_color_snap,
            look=look,
            resolution=resolution,
            section=section,
            previous_color=previous_color,
            label_palette=label_palette,
        )
        candidate = _values_line(escalate_attributes(look.attributes, rungs))
        if candidate not in emitted:
            return candidate, rungs
    return None, ()


def _ladder_start(section: SongCueSection) -> int:
    """회차가 정하는 첫 칸 — 2회차는 한 칸, 3회차는 두 칸(정본 §7.1 표).

    1회차가 겹치는 것은 같은 라벨의 반복이 아니라 **다른 라벨과 값이 같은** 경우다(실측:
    후렴 1이 드롭과 같았다). 그때도 한 칸은 올린다 — 안 올리면 그 큐가 사라지고, 사라지는
    것을 없애는 것이 이 카드다. 낮은 칸으로는 내려가지 않는다: 뒤 회차가 앞 회차보다
    약해지면 상승이 아니다.
    """
    return max(1, section.instance - 1)


# @MX:ANCHOR: [AUTO] 한 큐에 **찍는 액센트는 하나** — 밝기만 누적한다(정본 §6.1 [HARD],
#   감독 결정 2026-09-12).
# @MX:REASON: 고치기 전에는 칸 목록의 앞자락을 그대로 잘라 썼기 때문에(`_LADDER_CLIMB[:n]`)
#   깊이가 3에 닿으면 줌 좁힘과 아이리스 좁힘이 **함께** 나갔다 — 실측(2026-09-12,
#   `051e98b`)에서 후렴 4회차 한 큐가 `Zoom At 13` 과 `Iris At 55` 를 같이 실었고 둘 다
#   실제로 값을 바꿨다. §6.1 은 「셋을 한꺼번에 쓰면 아무것도 안 찍힌다」고 못박는다.
#   되돌리기 쉬운 유혹은 「누적이 §7.1 의 문면이니 앞자락을 자르자」이다. 정본의 두 절이
#   부딪혔고 감독이 갈래를 정했다 — **누적하는 축은 밝기 하나**이고, 찍는 액센트는
#   갈아탄다. 밝기를 액센트와 같은 규율로 묶으면 t355 의 성질(반복 회차가 사라지지 않는다)
#   이 깨진다: 축이 하나도 남지 않는 회차가 생겨 큐가 다시 버려진다.
def _climb_rungs(
    depth: int,
    *,
    allow_strobe: bool = False,
    disable_color_snap: bool = False,
    look: Look,
    resolution: RoleResolution,
    section: SongCueSection,
    previous_color: tuple[AttributeValue, ...] | None,
    label_palette: frozenset[tuple[AttributeValue, ...]],
) -> tuple[str, ...]:
    """깊이 하나가 내는 칸들 — 밝기 히트 여러 개 + 찍는 액센트 **최대 하나**.

    깊이 1은 밝기뿐이고(2회차), 깊이 2부터 액센트가 하나 붙는다. 더 깊어지면 밝기 히트가
    한 개씩 쌓이는 동안 액센트는 :func:`_marking_accents` 안에서 **갈아탄다** — 누적이
    아니라 교체다. 그래서 어느 깊이에서든 돌려주는 칸 중 찍는 액센트는 최대 하나다.

    밝기가 천장에 닿으면 그 뒤의 밝기 히트는 값을 안 바꾼다(:func:`_stepped` 가 자른다).
    그때는 액센트 교체만 값 라인을 가르고, 그것도 다 떨어지면 큐를 못 세운다.

    ``accents`` 는 이 룩+이 리그+이 라벨에서 이미 **효과가 있는 것만** 거른 후보다
    (SPEC-LDACCENT-001). 그 집합이 비어 있으면(무영향 칸뿐이면) 붙일 액센트가 없다 —
    무영향 칸 이름을 지어내지 않고 밝기 히트만 돌려준다; 그 회차가 액센트를 정말
    필요로 했는지는 :func:`_ensure_marking_accent` 가 값이 정해진 뒤에 다시 본다.
    """
    accents = _marking_accents(
        allow_strobe=allow_strobe,
        disable_color_snap=disable_color_snap,
        look=look,
        resolution=resolution,
        section=section,
        previous_color=previous_color,
        label_palette=label_palette,
    )
    if depth <= 1:
        return (LADDER_DIMMER_HIT,)
    hits = (LADDER_DIMMER_HIT,) * (depth - 1)
    if not accents:
        return hits
    return hits + (accents[(depth - 2) % len(accents)],)


def escalate_attributes(
    attributes: Sequence[AttributeValue], rungs: Sequence[str]
) -> tuple[AttributeValue, ...]:
    """기준 룩에 사다리 칸을 순서대로 더한 값들(정본 §7.1 아껴두기 사다리).

    받은 칸을 순서대로 다 더한다 — 무엇을 더할지 고르는 것은 여기가 아니라
    :func:`_climb_rungs` 의 일이다. 「한 큐에 찍는 액센트 하나」(§6.1)는 그쪽에서 지켜지고,
    이 함수는 **주어진 대로** 더하므로 손으로 액센트 둘을 넘기면 둘 다 나간다 — 그 성질이
    검사에서 대조군(누적 복원)을 만들 수 있게 한다.

    리그가 그 축을 안 갖거나 이미 한계에 닿은 칸은 **아무것도 바꾸지 않는다** — 없는 축에
    값을 만들어 보내지 않는 것이 이 계층의 규율이다(``Zoom``·``Iris`` 는 M0 프로브가 받은
    어휘이고, 룩이 안 실었으면 이 리그에서 그 칸은 없는 칸이다).
    """
    escalated = tuple(attributes)
    for rung in rungs:
        escalated = _rung_applied(escalated, rung)
    return escalated


# @MX:ANCHOR: [AUTO] 반복 회차(instance >= 2)는 값 라인이 어떻게 정해졌든 찍는
#   액센트를 하나 받는다 — 충돌-회피 사다리가 자리를 대신 정해 줬다는 이유로
#   건너뛰지 않는다(카드 t382, 정본 §7.1).
# @MX:REASON: 실측(카드 t382 보고): 값 라인 충돌-회피 구조가 먼저이므로(``_MARKING_ACCENTS``
#   독스트링), 반복이 깊어져 값 겹침이 사다리를 완전히 소진시키면
#   (:func:`_rescue_value_line_collisions`) 양보로 자리를 얻은 회차나 양보가 비워
#   준 기준값 자리를 그대로 물려받은 회차는
#   ``_distinct_values_line`` 이 애초에 액센트를 시도하기도 전에(``rungs=()``) 값을
#   확정해 버린다 — 후렴 일곱 중 여섯이 액센트 없이 밝기만 오르내리는 결과가 그것이다.
#   `_distinct_values_line` 자신이 액센트를 고집하게 만들면 그 함수의 규율("충돌이
#   방아쇠, 칸은 회차가 정한다")이 깨진다 — 충돌 없는 입력의 명령까지 바뀐다. 그래서
#   이 함수는 값 라인이 **이미 정해진 뒤**, 성공한 자리에서만 액센트가 빠졌는지 검사해
#   하나를 더 얹는다.
def _climb_depth_reached(rungs: tuple[str, ...]) -> int:
    """``rungs`` 가 :func:`_climb_rungs` 의 어느 깊이에서 나왔는지 — 액센트 없는 두 모양만.

    호출자가 이미 액센트 유무를 걸렀으므로, 여기 남는 것은 :func:`_climb_rungs` 가
    액센트 없이 낼 수 있는 두 모양뿐이다: 기준값 그대로(``()``, 깊이 0)와 밝기 히트
    하나(``(dimmer_hit,)``, 깊이 1). 그 밖의 모양이 들어오면 이미 액센트가 있다는
    뜻이므로 호출자 쪽 조건이 먼저 걸러낸다.
    """
    return 1 if rungs == (LADDER_DIMMER_HIT,) else 0


def _ensure_marking_accent(
    escalated: Sequence[AttributeValue],
    section: SongCueSection,
    rungs: tuple[str, ...],
    values: str,
    emitted: Mapping[str, tuple[int, int, str]],
    *,
    look: Look,
    resolution: RoleResolution,
    allow_strobe: bool = False,
    disable_color_snap: bool = False,
    force: bool = False,
    previous_color: tuple[AttributeValue, ...] | None,
    label_palette: frozenset[tuple[AttributeValue, ...]],
) -> tuple[str, tuple[str, ...], bool]:
    """이 회차에 찍는 액센트가 아직 없으면 하나 골라 붙인다 — 값이 이미 정해진 뒤에도.

    1회차(``section.instance < 2``)는 그대로 둔다 — 기준 회차는 아무것도 더하지 않는다는
    성질이 이 카드의 범위 밖이다. ``rungs`` 가 이미 :func:`_marking_accents` 의 칸을
    하나 갖고 있으면(정상적으로 사다리를 오른 경우) 그대로 둔다 — §6.1 「하나만」을
    두 번 채우지 않는다.

    ``force`` 가 거짓이면(기본값, 직접 사다리를 오른 성공 경로) **이 회차가 마땅히
    닿았어야 할 깊이**(:func:`_ladder_start`, 곧 ``instance - 1``)에 실제로 닿아
    있으면 그대로 둔다 — 2회차가 깊이 1(밝기 히트 하나, 액센트 없음)에서 곧바로
    성공하는 것은 이 카드가 고치는 결함이 아니라 정본 §7.1 자신의 설계다("2회차는
    밝기만"). 실제로 닿은 깊이가 마땅한 깊이보다 **얕으면**(기준값을 그대로 물려받은
    ``()`` 나, 3회차 이상인데 1에서 멈춘 경우) 사다리가 이 회차를 위해 오른 것이
    아니라 충돌-회피가 자리를 대신 정해 준 것이므로 그때는 강제한다.

    ``force`` 가 참이면(양보 경로, :func:`_yield_bundle`) 깊이를 안 따진다 — 양보는
    사다리 축 자체가 아니므로 "마땅한 깊이" 개념이 없고, 자리를 얻은 이상 액센트를
    받는다(카드 t382 결정).

    ``escalated`` 는 ``rungs`` 까지 이미 반영된 현재 값 상태다(:func:`escalate_attributes`
    가 만든 것, 또는 양보 축처럼 그 함수가 모르는 칸으로 만들어진 값도 무방하다 —
    여기서는 그 위에 액센트 하나만 얹는다). 회차가 고르는 첫 자리는 :func:`_marking_accents`
    가 이 룩+이 리그+이 라벨에서 거른 유효 후보 안에서 ``(instance - 2) % len`` 이고
    (:func:`_climb_rungs` 와 같은 회전), 그 자리가 이미 나간 값과 겹치면 회전판을 한
    칸씩 밀어 겹치지 않는 자리를 찾는다 — 블라인더·스트로브는 이 룩 자신의 값을 안
    바꾸므로(:func:`_rung_applied`) 항상 겹치지 않아 회전은 유한한 안에서 반드시 멈춘다.

    셋째 반환값은 **유보 여부**(SPEC-LDACCENT-001, REQ-LDACCENT-005) — 이 회차가
    액센트를 마땅히 받아야 하는데(이미 있지도 않고, 마땅한 깊이에도 안 닿았는데)
    REQ-004 의 탐색(이 룩+이 리그+이 라벨에서 유효한 후보 전량을 회전 순서대로
    시도)을 다 거쳐도 유효한 후보가 하나도 남지 않으면 참이다 — 후보 집합이
    애초에 비어 있었든(무영향 칸뿐), 있었지만 전부 이미 나간 값과 겹쳤든 같은
    사유다. 그때 ``values``·``rungs`` 는 입력 그대로 돌려준다 — 셀 이름을
    지어내지 않는다.
    """
    if section.instance < 2:
        return values, rungs, False
    accents = _marking_accents(
        allow_strobe=allow_strobe,
        disable_color_snap=disable_color_snap,
        look=look,
        resolution=resolution,
        section=section,
        previous_color=previous_color,
        label_palette=label_palette,
    )
    if any(rung in accents for rung in rungs):
        return values, rungs, False
    if not force and _climb_depth_reached(rungs) >= _ladder_start(section):
        return values, rungs, False
    if not accents:
        return values, rungs, True
    start = (section.instance - 2) % len(accents)
    for offset in range(len(accents)):
        accent = accents[(start + offset) % len(accents)]
        candidate = _values_line(_rung_applied(escalated, accent))
        if candidate == values or candidate not in emitted:
            return candidate, rungs + (accent,), False
    return values, rungs, True


def _rung_applied(values: Sequence[AttributeValue], rung: str) -> tuple[AttributeValue, ...]:
    if rung == LADDER_DIMMER_HIT:
        return _stepped(values, _DIMMER, _HIT_STEP, _DIMMER_CEILING)
    if rung == LADDER_ZOOM_PINCH:
        return _stepped(values, _ZOOM, _PINCH_STEP, _BEAM_FLOOR)
    if rung == LADDER_IRIS_PINCH:
        return _stepped(values, _IRIS, _PINCH_STEP, _BEAM_FLOOR)
    if rung == LADDER_COLOR_SNAP:
        # 색은 이미 바뀌지 않는다 — 색 스냅이 내는 색은 이 룩 자신이 이미 들고
        # 있는 §7 복귀 색이고(REQ-LDCLIMAX-002, 호출자가 효과 판정으로 이미
        # 확인했다), "에스컬레이션"은 값 라인이 아니라 페이드(REQ-LDCLIMAX-003)
        # 쪽에서 일어난다 — 그 강제는 ``_section_bundle`` 이 ``rungs`` 를 보고
        # 별도로 한다(design.md 의 sketch 는 이 자리에서 ``(look, float)`` 쌍을
        # 돌려주는 헬퍼를 그렸지만, 그 반환형은 이 함수의 계약(``tuple[AttributeValue,
        # ...]`` 만)과 맞지 않는다 — 시그니처 불일치를 그대로 옮기지 않고 여기서는
        # 항등, 페이드는 별도 지점에서 강제하는 쪽으로 갈랐다).
        return tuple(values)
    if rung in (LADDER_BLINDER_OR_FLASH, LADDER_STROBE_HIT):
        # 이 룩 자신의 값은 안 바뀐다 — 블라인더·스트로브는 다른 그룹이다
        # (:data:`LADDER_BLINDER_OR_FLASH` 독스트링). 실제 명령은
        # :func:`_accent_fixture_commands` 가 ``rungs`` 를 따로 읽어 만든다.
        return tuple(values)
    raise SongCueBundleError(f"unknown ladder rung: {rung!r}")


def _stepped(
    values: Sequence[AttributeValue], attribute: str, step: int, limit: int
) -> tuple[AttributeValue, ...]:
    """한 속성만 한 칸 움직인 값들 — 그 속성이 없거나 한계에 닿아 있으면 그대로."""
    stepped: list[AttributeValue] = []
    for value in values:
        if value.name != attribute:
            stepped.append(value)
            continue
        target = value.value + step
        bounded = min(target, limit) if step > 0 else max(target, limit)
        stepped.append(AttributeValue(attribute, bounded))
    return tuple(stepped)


def _timecode_commands(bundle: SongCueBundle, timecode_number: int) -> tuple[str, ...]:
    timecode_name = _ascii_label(
        f"{bundle.sequence_name} Timecode", fallback=f"Timecode {timecode_number}"
    )
    return (
        f"Store Timecode {timecode_number}",
        f"Set Timecode {timecode_number} Property 'Name' '{timecode_name}'",
        f"Assign Sequence {bundle.sequence_number} At Timecode {timecode_number}",
    )


def _auto_advance_commands(bundle: SongCueBundle) -> tuple[str, ...]:
    commands: list[str] = []
    for section in bundle.stored_sections:
        commands.append(
            f"Set Cue {section.cue_number} Sequence {bundle.sequence_number} "
            f"Property 'TrigType' '{TRIGGER_TYPE_TIME}'"
        )
        commands.append(
            f"Set Cue {section.cue_number} Sequence {bundle.sequence_number} "
            f"Property 'TrigTime' {_format_seconds(section.section.start_ms)}"
        )
    return tuple(commands)


def _format_seconds(start_ms: int) -> str:
    seconds = Decimal(start_ms) / _MILLISECONDS_PER_SECOND
    if seconds == seconds.to_integral_value():
        return str(int(seconds))
    return format(seconds.normalize(), "f")


def _selected_groups(bound: Mapping[str, tuple[GroupCandidate, ...]]) -> tuple[GroupCandidate, ...]:
    selected = sorted(
        {group.number: group for groups in bound.values() for group in groups}.items()
    )
    return tuple(group for _number, group in selected)


def _selection_line(groups: Sequence[GroupCandidate]) -> str:
    return "Group " + " + ".join(str(group.number) for group in groups)


def _first_store_index(commands: Sequence[str], sequence_number: int, cue_number: int) -> int:
    prefix = f"Store Sequence {sequence_number} Cue {cue_number} "
    for index, command in enumerate(commands):
        if command.startswith(prefix):
            return index
    raise SongCueBundleError(SEQUENCE_UNAVAILABLE)


def _sequence_numbers(sequences_section: Mapping[str, object]) -> set[int]:
    listed = sequences_section.get("objects")
    if not isinstance(listed, list):
        listed = sequences_section.get("children")
    if not isinstance(listed, list):
        raise SequenceNumberError(SEQUENCE_UNAVAILABLE)
    occupied: set[int] = set()
    for entry in listed:
        if not isinstance(entry, Mapping):
            raise SequenceNumberError(SEQUENCE_NUMBER_UNAVAILABLE)
        number = entry.get("no", entry.get("i"))
        if not isinstance(number, int):
            raise SequenceNumberError(SEQUENCE_NUMBER_UNAVAILABLE)
        occupied.add(number)
    return occupied


def _cue_names(sections: Sequence[SongCueSection]) -> tuple[str, ...]:
    """중복 라벨을 회차로 가른 큐 이름.

    순번은 여기서 다시 세지 않고 :attr:`SongCueSection.instance` 를 읽는다 —
    카운터는 :func:`_numbered_by_label` 하나다. 파서를 거치지 않은 구간은 라벨이 비어 있어
    이름으로 센다(그쪽은 선언으로 1회차다).
    """
    totals: dict[str, int] = dict()
    for section in sections:
        key = section.label or section.name
        totals[key] = totals.get(key, 0) + 1
    names: list[str] = []
    for section in sections:
        fallback = f"Section {section.index + 1}"
        base = _ascii_label(section.name, fallback=fallback)
        if totals[section.label or section.name] > 1:
            base = f"{base} {section.instance}"
        names.append(base)
    return tuple(names)


def _ascii_label(value: str, *, fallback: str) -> str:
    normalised = unicodedata.normalize("NFKD", value)
    ascii_text = normalised.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^0-9A-Za-z _.-]+", " ", ascii_text.replace("'", " "))
    label = " ".join(cleaned.split())
    return label or fallback


def _explicit_dynamics_for(
    section: SongCueSection, explicit_dynamics: Mapping[int, int] | None
) -> int | None:
    if explicit_dynamics is None:
        return None
    return explicit_dynamics.get(section.index)


def _validated_dynamics(value: int, index: int) -> int:
    if isinstance(value, bool) or value < DYNAMICS_MIN or value > DYNAMICS_MAX:
        raise ValueError(
            f"section index {index} explicit dynamics must be "
            f"between {DYNAMICS_MIN} and {DYNAMICS_MAX}: {value!r}"
        )
    return value


def _raw_section(raw: Mapping[str, object] | Sequence[object]) -> _RawSection:
    if isinstance(raw, Mapping):
        return _RawSection(
            name=str(_first_present(raw, _NAME_KEYS)), start=_first_present(raw, _START_KEYS)
        )
    if isinstance(raw, str):
        raise ValueError("section entries must provide both name and start time")
    if len(raw) != 2:
        raise ValueError("section entries must provide exactly two values")
    name, start = raw
    return _RawSection(name=str(name), start=start)


def _prepare_songcue_timecode_number(request: Mapping[str, object]) -> int:
    timecode_number = request.get("timecode_number")
    if (
        isinstance(timecode_number, bool)
        or not isinstance(timecode_number, int)
        or timecode_number < 1
    ):
        raise ValueError("'timecode_number' must be a positive integer")
    return timecode_number


def _first_present(values: Mapping[str, object], keys: Sequence[str]) -> object:
    for key in keys:
        if key in values:
            return values[key]
    raise ValueError(f"section entry is missing one of {keys!r}")


def _section_dynamics(name: str) -> tuple[int, ...] | None:
    """구간 이름 → 세기 대역. 판정은 ``section_vocab`` 하나가 갖는다 (카드 t362).

    한때 이 자리가 ``matching.resolve_dynamics`` 를 불렀다. 그 함수는 **운영자 질의**의
    판정이라 걸린 말의 대역을 전부 합집합하는데, 구간 라벨에서는 그것이 틀린 답이다 —
    ``Post-Chorus`` 가 ``post-chorus`` ∪ ``chorus`` = (3,4,5) 로 읽혀 후렴 대역의 룩이
    후주에 붙는다(실측: 고치기 전 ``Pre-Chorus`` 와 ``Post-Chorus`` 가 둘 다 (4,5) 였다).
    """
    if not SECTION_TERMS:
        raise RuntimeError("section vocabulary is empty")
    return resolve_section_dynamics(name)


def _decimal_from(value: str, raw: object) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"unsupported section time format: {raw!r}") from exc


def _seconds_to_milliseconds(seconds: Decimal) -> int:
    if seconds < 0:
        raise ValueError(f"section time must be non-negative: {seconds}")
    milliseconds = seconds * _MILLISECONDS_PER_SECOND
    if milliseconds != milliseconds.to_integral_value():
        raise ValueError(f"section time must resolve to a whole millisecond: {seconds}")
    return int(milliseconds)
