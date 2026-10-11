"""박자 격자 편집 연산 — 편집 세 길(직접 고르기·문장·AI 제안)의 단일
수렴점 (SPEC-LDBEAT-001 M3, 카드 t551, REQ-LDBEAT-007~009·015).

이 모듈은 ``cue_sheet_edit.py``와 같은 모양이다(t281) — **콘솔에 아무것도
쓰지 않는다.** 입력은 ``BeatGridView``(``server.design.beat_grid``)의
사전이고, 출력은 그 사전의 **새 사본**이다. 명령 문자열도 ``ToolCall``도
승인 카드도 여기 없다 — 그래서 이 경로로는 원리적으로 콘솔에 닿을 수
없다.

거절은 조용하지 않다. 못 고치는 요청은 :class:`BeatGridEditError`로
**사유 문자열과 함께** 튀어나온다(`cue_sheet_edit.CueSheetEditError`와
같은 관행 — 거짓 사유가 참 사유를 가리지 않게, 단일 원인만 지목한다).
**부분 적용은 없다** — 검증을 전부 끝낸 뒤에만 쓴다.

편집 가능한 칸은 ``BeatGridCue``가 이미 가진 구조화 필드뿐이다
(REQ-LDBEAT-006(i)(vi)(vii)) — 없는 칸은 지어내지 않고 거절한다
(REQ-LDBEAT-007/008, `EDITABLE_FIELD_LABELS`와 같은 화이트리스트 패턴).

그룹/역할 스코프(REQ-LDBEAT-009)는 `cue_sheet_edit._GROUP_SCOPE`/
`_resolve_group_scope`와 같은 모양으로 재사용한다 — 모르는 트랙/역할
이름은 지어내지 않고 거절하고, 매핑된 트랙에만 diff가 생긴다.

프리셋 풀 번호대(REQ-LDBEAT-015(a)(b))는 **이 모듈의 코드 상수가 아니라**
`server/design/beat_grid_data/preset_pools.yaml`에서 읽는다 — 실제 쇼
파일과 아직 대조하지 않았으므로(§B 위험 11) 번호대 값 자체는 그 데이터
파일에만 있고, 바꿀 때 이 코드를 고치지 않는다.
"""

from __future__ import annotations

import copy
import re
import unicodedata
from collections.abc import Mapping, Sequence
from pathlib import Path

import yaml

from server.design.beat_grid import (
    BeatGridCue,
    check_app_movement_axis_conflict,
    check_evidence_approval,
    normalize_beat_grid_cue,
)
from server.design.beat_grid_unverified import unverified_movement_terms
from server.design.cue_sheet_edit import MIB_MODES, TRACKING_VALUES
from server.spatial.position_fx import POSITION_FX_EFFECTS

__all__ = [
    "movement_vocabulary",
    "AXES_VALUES",
    "EDITABLE_CUE_FIELD_LABELS",
    "PERIOD_UNITS",
    "BeatGridEditError",
    "apply_beat_grid_edit",
    "apply_beat_grid_edit_range",
    "load_preset_pool_policy",
    "resolve_track_scope",
    "validate_preset_pool_assignment",
]


class BeatGridEditError(ValueError):
    """편집을 못 했다. 메시지는 감독에게 그대로 보여도 되는 한국어 사유다
    (`cue_sheet_edit.CueSheetEditError`와 같은 계약)."""


#: 고칠 수 있는 칸과 화면 이름 — 이 표에 없는 키는 「없는 칸」으로 거절한다
#: (REQ-LDBEAT-007/008, `cue_sheet_edit.EDITABLE_FIELD_LABELS`와 같은
#: 화이트리스트 패턴). ``new_preset_label``은 `BeatGridCue`의 저장 필드가
#: 아니다 — 요청 메타데이터로만 검증·보고되고 칸에 영속되지 않는다(실제
#: 콘솔 프리셋 생성·이름 붙이기는 M4 에미터의 몫이다).
EDITABLE_CUE_FIELD_LABELS: dict[str, str] = {
    "brightness": "밝기",
    "position_preset_no": "포지션 번호",
    "color_preset_no": "색 프리셋",
    "effect_preset_no": "효과 프리셋",
    "effect_kind": "효과 종류",
    "entry": "들어올 때",
    "app_movement": "앱 무빙",
    "evidence": "근거 등급",
    "new_preset_label": "신규 프리셋 이름",
}

#: REQ-LDBEAT-006(vi-3) — `app_movement.axes`가 고를 수 있는 닫힌 집합.
AXES_VALUES: frozenset[str] = frozenset({"Pan", "Tilt"})

#: REQ-LDBEAT-006(vi-4) — 음악 단위만 허용한다(초 단위는 shall not).
PERIOD_UNITS: frozenset[str] = frozenset({"beat", "bar"})

_EVIDENCE_GRADES: tuple[str, ...] = ("measured", "measured_other_group", "name_only")


def movement_vocabulary(probe_results: Mapping[object, object]) -> dict[str, object]:
    """카드 t584 — 편집 칸 「움직임」 고르기 목록이 쓸 닫힌 어휘. 화면은 모양·축·
    주기 단위 이름을 이것에서만 받는다(UI 상수 0, REQ-LDBEAT-006(vi-2)~(vi-4)).

    ``unverified``·``phase_spread_unverified``는 M1 표만으로 본 값이다
    (`unverified_movement_terms`, 그룹 없이) — 고르기 전 목록의 「⚠」다. 고른
    뒤 칸의 배지는 그룹·축까지 보는 ``unverified_cells``가 정한다(실측 기록이
    그 그룹을 열었으면 배지가 없을 수 있다)."""
    return {
        "shapes": [
            {
                "name": shape,
                "unverified": bool(unverified_movement_terms({"shape": shape}, probe_results)),  # type: ignore[arg-type]
            }
            for shape in POSITION_FX_EFFECTS
        ],
        "axes": sorted(AXES_VALUES),
        "period_units": sorted(PERIOD_UNITS),
        "phase_spread_unverified": bool(
            unverified_movement_terms({"phase_spread": True}, probe_results)  # type: ignore[arg-type]
        ),
    }


_BRIGHTNESS_MODES: tuple[str, ...] = ("value", "dimmer_preset", "dimmer_effect")
_EFFECT_KINDS: tuple[str, ...] = ("position", "color", "dimmer", "mixed")

_VALUE_PERCENT_MIN, _VALUE_PERCENT_MAX = 0, 100

#: 효과 종류(`effect_kind`) → `preset_pools.yaml`의 풀 키(들). 디머는
#: 두 서브 밴드로 나뉘어 있어 여러 키를 가진다(REQ-LDBEAT-015(b)).
_KIND_TO_POOL_KEYS: dict[str, tuple[str, ...]] = {
    "position": ("position_effect",),
    "color": ("color_effect",),
    "dimmer": ("dimmer_effect_a", "dimmer_effect_b"),
    "mixed": ("mixed_all",),
}

_PRESET_POOLS_PATH: Path = Path(__file__).resolve().parent / "beat_grid_data" / "preset_pools.yaml"


# -- 프리셋 풀 번호대 정책(REQ-LDBEAT-015(a)(b)) — 데이터 파일에서 읽는다 ----


def load_preset_pool_policy(path: Path | None = None) -> dict[str, object]:
    """``preset_pools.yaml``을 읽어 ``{"confirmed": bool, "pools": {...}}``를
    돌려준다. 파일이 없거나 못 읽으면(권한·I/O·파싱 오류) **정직하게**
    ``{"confirmed": False, "pools": {}}``로 떨어진다 — 지어낸 밴드는
    0건이다(`beat_grid_probes.read_m1_probe_results`와 같은 실패-경로
    관행)."""
    target = path if path is not None else _PRESET_POOLS_PATH
    try:
        with target.open("r", encoding="utf-8") as handle:
            document = yaml.safe_load(handle)
    except OSError:
        return {"confirmed": False, "pools": {}}
    if not isinstance(document, Mapping):
        return {"confirmed": False, "pools": {}}
    pools = document.get("pools")
    return {
        "confirmed": bool(document.get("confirmed", False)),
        "pools": dict(pools) if isinstance(pools, Mapping) else {},
    }


def validate_preset_pool_assignment(
    kind: str, number: str | None, policy: Mapping[str, object]
) -> str | None:
    """``number``가 ``kind``(REQ-LDBEAT-006(i-3) ``effect_kind``와 같은
    집합)의 효과 풀 번호대 안에 있는지 검사한다. 번호가 `None`이면
    (아직 미정) 검사 대상이 아니다 — `None`.

    번호대는 이 함수가 아니라 호출자가 넘긴 ``policy``(``preset_pools.yaml``
    에서 읽은 것)가 쥔다 — 이 모듈은 숫자를 전혀 하드코딩하지 않는다.
    번호대가 그 ``kind``에 아직 선언돼 있지 않으면 **거절**한다(fail-closed
    — 손해가 큰 쪽으로 기운다, "fail-closed 는 손해에 비례한다")."""
    if number is None:
        return None
    pool_keys = _KIND_TO_POOL_KEYS.get(kind)
    if not pool_keys:
        return f"효과 종류 '{kind}'에는 선언된 풀이 없습니다 — REQ-LDBEAT-015(b)."
    pools = policy.get("pools") if isinstance(policy, Mapping) else None
    pools = pools if isinstance(pools, Mapping) else {}
    candidates = [pools[key] for key in pool_keys if key in pools]
    try:
        value = float(number)
    except (TypeError, ValueError):
        return f"프리셋 번호 '{number}'를 읽을 수 없습니다 — REQ-LDBEAT-015(b)."
    if not candidates:
        return (
            f"'{kind}' 효과 풀 번호대가 아직 확정되지 않았습니다(REQ-LDBEAT-015(b)) — "
            "쇼 파일 대조 후 preset_pools.yaml 을 고쳐 주세요."
        )
    for band in candidates:
        if not isinstance(band, Mapping):
            continue
        try:
            start = float(band["start"])
            end = float(band["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if start <= value <= end:
            return None
    ranges = " 또는 ".join(
        f"{band['start']}~{band['end']}" for band in candidates if isinstance(band, Mapping)
    )
    return f"프리셋 번호 {number}는 '{kind}' 효과 풀 번호대({ranges}) 밖입니다 — REQ-LDBEAT-015(b)."


# -- 그룹/역할 스코프(REQ-LDBEAT-009) -----------------------------------------


def _group_key(name: str) -> str:
    return name.strip().casefold()


def resolve_track_scope(tracks: Sequence[Mapping[str, object]], target: str) -> list[int]:
    """``target``이 가리키는 트랙의 인덱스 목록 — `cue_sheet_edit.
    _resolve_group_scope`와 같은 모양으로, 그룹 이름 **정확 일치**를
    먼저 보고(대소문자 무시), 없으면 **층 역할**(이미 트랙에 계산돼
    저장된 ``layer_role``, `server.design.rig.resolve_layer_role`의
    결과 — 여기서 다시 계산하지 않는다) 일치로 넓힌다. 하나도
    매칭되지 않으면 빈 리스트(호출자가 거절한다) — 지어내지 않는다."""
    folded = _group_key(target)
    exact = [
        index
        for index, track in enumerate(tracks)
        if _group_key(str(track.get("group_name") or "")) == folded
    ]
    if exact:
        return exact
    return [
        index
        for index, track in enumerate(tracks)
        if _group_key(str(track.get("layer_role") or "")) == folded
    ]


# -- 칸 필드 검증(부분 적용 금지 — 쓰기 전에 전부 검증) -----------------------


def _validate_brightness(value: object) -> None:
    if not isinstance(value, Mapping):
        raise BeatGridEditError("밝기 값은 {mode, value_percent, preset_no} 모양이어야 합니다.")
    mode = value.get("mode")
    if mode is not None and mode not in _BRIGHTNESS_MODES:
        raise BeatGridEditError(
            f"밝기 모드는 {', '.join(_BRIGHTNESS_MODES)} 중 하나여야 합니다(받은 값: {mode!r})."
        )
    filled = [key for key in ("value_percent", "preset_no") if value.get(key) is not None]
    if len(filled) > 1:
        raise BeatGridEditError(
            "밝기는 값/디머 프리셋/디머 효과 프리셋 중 정확히 하나만 쓸 수 있습니다 "
            "— REQ-LDBEAT-015(c)."
        )
    percent = value.get("value_percent")
    if percent is not None:
        if not isinstance(percent, (int, float)) or isinstance(percent, bool):
            raise BeatGridEditError(f"밝기 값(%)은 숫자여야 합니다 (받은 값: {percent!r}).")
        if not (_VALUE_PERCENT_MIN <= percent <= _VALUE_PERCENT_MAX):
            raise BeatGridEditError(
                f"밝기 값(%)은 {_VALUE_PERCENT_MIN}~{_VALUE_PERCENT_MAX} 사이여야 합니다 "
                f"(요청값: {percent})."
            )


def _validate_app_movement(value: object) -> None:
    """닫힌 어휘·축·주기·위상 값 검증. 「⚠ 실기 미확인」 경고는 여기서 내지
    않는다 — 그 판정은 트랙(그룹)과 M1 표를 알아야 해서 `apply_beat_grid_edit`
    의 병합 루프가 `unverified_movement_terms`로 낸다(카드 t579)."""
    if value is None:
        return
    if not isinstance(value, Mapping):
        raise BeatGridEditError(
            "app_movement 값은 {shape, axes, period_unit, period_value, phase_spread} "
            "모양이어야 합니다."
        )
    shape = value.get("shape")
    if shape is not None and shape not in POSITION_FX_EFFECTS:
        raise BeatGridEditError(
            f"app_movement.shape '{shape}'는 닫힌 어휘 "
            f"{', '.join(POSITION_FX_EFFECTS)} 안에 없습니다 — REQ-LDBEAT-006(vi-2)."
        )
    axes = value.get("axes") or ()
    for axis in axes:
        if axis not in AXES_VALUES:
            raise BeatGridEditError(
                f"app_movement.axes 값 '{axis}'는 {', '.join(sorted(AXES_VALUES))} 중 "
                "하나여야 합니다 — REQ-LDBEAT-006(vi-3)."
            )
    period_unit = value.get("period_unit")
    if period_unit is not None and period_unit not in PERIOD_UNITS:
        raise BeatGridEditError(
            f"app_movement.period_unit '{period_unit}'는 음악 단위"
            f"({', '.join(sorted(PERIOD_UNITS))})만 허용됩니다 — 초 단위는 shall not "
            "(REQ-LDBEAT-006(vi-4))."
        )
    period_value = value.get("period_value")
    if period_value is not None:
        if not isinstance(period_value, int) or isinstance(period_value, bool):
            raise BeatGridEditError(
                f"app_movement.period_value는 정수여야 합니다 (받은 값: {period_value!r})."
            )
        if period_value <= 0:
            raise BeatGridEditError(
                f"app_movement.period_value는 양수여야 합니다 (받은 값: {period_value})."
            )
    phase_spread = value.get("phase_spread")
    if phase_spread is not None and not isinstance(phase_spread, bool):
        raise BeatGridEditError(
            f"app_movement.phase_spread는 참/거짓/미정이어야 합니다 (받은 값: {phase_spread!r})."
        )


def _validate_evidence(value: object) -> None:
    if value is None:
        return
    if not isinstance(value, Mapping):
        raise BeatGridEditError("evidence 값은 {grade, approval} 모양이어야 합니다.")
    grade = value.get("grade")
    if grade is not None and grade not in _EVIDENCE_GRADES:
        raise BeatGridEditError(
            f"evidence.grade '{grade}'는 {', '.join(_EVIDENCE_GRADES)} 중 하나여야 합니다 "
            "— REQ-LDBEAT-006(vii-2)."
        )
    approval = value.get("approval")
    if approval is not None and not isinstance(approval, Mapping):
        raise BeatGridEditError(
            "evidence.approval은 {by, date, source} 모양이거나 미정이어야 합니다."
        )


def beats_per_bar_from_timeline(timeline: object) -> int | None:
    """REQ-LDBEAT-006(i-4f) — 곡의 마디당 박 수를 곡 데이터에서만 읽는다.

    ``timeline["time_signature"]``(``"3/4"`` 같은 문자열, ``song_plan``) 을 먼저,
    없으면 ``timeline["bar_map"]["time_signature"]``(``[분자, 분모]``,
    ``beat_grid_send`` 와 같은 출처)를 본다. 못 읽으면 ``None`` — 4를 지어내지
    않는다(카드 t574)."""
    if not isinstance(timeline, Mapping):
        return None
    signature = timeline.get("time_signature")
    if isinstance(signature, str):
        match = re.fullmatch(r"\s*(\d+)\s*/\s*\d+\s*", signature)
        if match and int(match.group(1)) > 0:
            return int(match.group(1))
    bar_map = timeline.get("bar_map")
    pair = bar_map.get("time_signature") if isinstance(bar_map, Mapping) else None
    if isinstance(pair, Sequence) and not isinstance(pair, (str, bytes)) and len(pair) == 2:
        beats = pair[0]
        if isinstance(beats, int) and not isinstance(beats, bool) and beats > 0:
            return beats
    return None


def _validate_beat_count(value: object, label: str) -> None:
    """박 수 필드 하나 — 미정 또는 0 이상의 정수(음악 단위, 초 아님)."""
    if value is None:
        return
    if not isinstance(value, int) or isinstance(value, bool):
        raise BeatGridEditError(f"{label}(박 수)는 정수여야 합니다 (받은 값: {value!r}).")
    if value < 0:
        raise BeatGridEditError(f"{label}(박 수)는 0 이상이어야 합니다 (받은 값: {value}).")


def _validate_entry(value: object, beats_per_bar: int | None = None) -> None:
    if not isinstance(value, Mapping):
        raise BeatGridEditError("entry 값은 {fade_bars, mib_mode} 모양이어야 합니다.")
    fade_bars = value.get("fade_bars")
    if fade_bars is not None:
        if not isinstance(fade_bars, int) or isinstance(fade_bars, bool):
            raise BeatGridEditError(
                f"들어올 때(마디 수)는 정수여야 합니다 (받은 값: {fade_bars!r})."
            )
        if fade_bars < 0:
            raise BeatGridEditError(
                f"들어올 때(마디 수)는 0 이상이어야 합니다 (받은 값: {fade_bars})."
            )
    mib_mode = value.get("mib_mode")
    if mib_mode is not None and mib_mode not in MIB_MODES:
        raise BeatGridEditError(
            f"MIB 모드 '{mib_mode}'는 {', '.join(MIB_MODES)} 중 하나여야 합니다."
        )
    # 카드 t574 — SPEC-LDBEAT-001 0.5.0 REQ-LDBEAT-006(i-4a)~(i-4e).
    _validate_beat_count(value.get("fade_beats"), "들어올 때")
    if fade_bars is not None and value.get("fade_beats") is not None:
        raise BeatGridEditError(
            "들어올 때는 마디(fade_bars)와 박(fade_beats) 중 하나로만 정합니다 "
            "— REQ-LDBEAT-006(i-4a)."
        )
    _validate_beat_count(value.get("delay_beats"), "딜레이")
    _validate_beat_count(value.get("position_late_beats"), "위치만 따로")
    trigger_beat = value.get("trigger_beat")
    if trigger_beat is not None:
        if not isinstance(trigger_beat, int) or isinstance(trigger_beat, bool):
            raise BeatGridEditError(f"트리거 박은 정수여야 합니다 (받은 값: {trigger_beat!r}).")
        if beats_per_bar is None:
            raise BeatGridEditError(
                "트리거 박을 정하려면 곡 박자표(마디당 박 수)가 필요합니다 — "
                "박자표를 몰라 범위를 확인할 수 없어 저장하지 않습니다(REQ-LDBEAT-006(i-4f))."
            )
        if not 1 <= trigger_beat <= beats_per_bar:
            raise BeatGridEditError(
                f"트리거 박은 1~{beats_per_bar} 사이여야 합니다(이 곡 박자표 기준, "
                f"받은 값: {trigger_beat}) — REQ-LDBEAT-006(i-4b)."
            )
    tracking = value.get("tracking")
    if tracking is not None and tracking not in TRACKING_VALUES:
        raise BeatGridEditError(
            f"트래킹 값은 {', '.join(TRACKING_VALUES)} 중 하나여야 합니다 "
            f"(받은 값: {tracking!r}) — REQ-LDBEAT-006(i-4e)."
        )


def _validate_effect_kind(value: object) -> None:
    if value is not None and value not in _EFFECT_KINDS:
        raise BeatGridEditError(
            f"effect_kind '{value}'는 {', '.join(_EFFECT_KINDS)} 중 하나여야 합니다 "
            "— REQ-LDBEAT-006(i-3)."
        )


_ASCII_LABEL_PATTERN = re.compile(r"[^0-9A-Za-z _.-]")


def _assert_ascii_preset_label(label: object) -> None:
    """REQ-LDBEAT-015(d) — 콘솔에 들어가는 신규 프리셋 이름은 영문·숫자만
    이다. ``_ascii_label``(``server.looks.songcue``)이 콘솔 송신 직전에
    **정규화(치환)**하는 것과 달리, 이 자리는 아직 송신 전인 **편집 요청
    검증** 단계라 치환하지 않고 **거절**한다 — 한글이 섞인 이름을 조용히
    영문으로 지어내면 감독이 의도한 이름과 달라진다."""
    if not isinstance(label, str) or not label.strip():
        raise BeatGridEditError("신규 프리셋 이름이 비어 있습니다 — 무엇으로 할지 적어 주세요.")
    normalised = unicodedata.normalize("NFKD", label)
    ascii_only = normalised.encode("ascii", "ignore").decode("ascii")
    if _ASCII_LABEL_PATTERN.sub("", ascii_only) != _ASCII_LABEL_PATTERN.sub("", label):
        raise BeatGridEditError(
            f"신규 프리셋 이름 '{label}'에 한글/비-ASCII 문자가 있습니다 — "
            "콘솔 이름은 영문·숫자만 허용됩니다(REQ-LDBEAT-015(d))."
        )
    if not re.fullmatch(r"[0-9A-Za-z _.-]+", label):
        raise BeatGridEditError(
            f"신규 프리셋 이름 '{label}'에 영문·숫자·공백·` _.-` 밖의 문자가 있습니다 "
            "— REQ-LDBEAT-015(d)."
        )


# -- 메인 진입점 ---------------------------------------------------------------


def _find_cue(track: Mapping[str, object], bar: int) -> BeatGridCue | None:
    for cue in track.get("cues") or []:
        if isinstance(cue, Mapping) and cue.get("bar") == bar:
            return cue  # type: ignore[return-value]
    return None


# @MX:ANCHOR: [AUTO] 편집 세 길(직접 고르기·문장·AI 제안 「적용」)이 전부
# 이 함수 하나로 수렴한다 — 기대 fan_in >= 3(REQ-LDBEAT-007/008).
# @MX:REASON: 세 입력 경로가 각자 콘솔 페이로드를 지어내지 못하게 막는
# 유일한 진입점이라, 이 함수를 우회하는 새 경로가 추가되면 REQ-LDBEAT-008
# (화이트리스트·값 범위·단일-원인 거절의 단일 진실 지점)이 깨진다.
def apply_beat_grid_edit(
    grid: Mapping[str, object],
    *,
    bar: int,
    target: str,
    changes: Mapping[str, object],
    beats_per_bar: int | None = None,
) -> tuple[dict[str, object], list[str]]:
    """``grid``(``BeatGridView``)의 사본에 ``changes``를 적용하고
    (새 그리드, 변경 보고)를 돌려준다. 원본은 건드리지 않는다.

    세 입력 경로(직접 고르기·문장·AI 제안의 「적용」) 모두 이 함수
    하나로 수렴한다(REQ-LDBEAT-007/008) — UI는 이 함수를 호출하는 것
    말고 콘솔 페이로드를 직접 구성하지 않는다.

    ``target``은 콘솔 그룹 트랙 이름(정확 일치, 대소문자 무시) 또는 층
    역할 이름(``server.design.rig.RIG_LAYER_ROLES``) 중 하나다 —
    `resolve_track_scope`가 매칭되는 트랙 인덱스를 돌려주고, 하나도
    없으면 거절한다(REQ-LDBEAT-009, `cue_sheet_edit._resolve_group_scope`
    와 같은 모양). 매칭된 **모든** 트랙의 ``bar`` 칸에 같은 ``changes``가
    적용되고, 매칭되지 않은 트랙은 바이트까지 그대로 보존된다
    (AC-LDBEAT-014(b)). 그 바에 칸이 아직 없으면 새로 만든다(AI 제안·
    직접 고르기가 새 칸을 여는 경우).

    **부분 적용 금지**: 모든 검증이 끝난 뒤에만 쓴다 — 사유를 던지기
    전에는 아무것도 바뀌지 않는다."""
    if not changes:
        raise BeatGridEditError(
            "무엇을 고칠지 못 읽었습니다. 예: 'MOVER-U 11마디 포지션 2.1로', '이 칸 밝기 70%로'."
        )
    unknown = [key for key in changes if key not in EDITABLE_CUE_FIELD_LABELS]
    if unknown:
        editable = ", ".join(EDITABLE_CUE_FIELD_LABELS.values())
        raise BeatGridEditError(
            f"'{unknown[0]}'은(는) 박자 격자가 가진 항목이 아닙니다. 수정 가능한 항목: {editable}."
        )

    tracks = list(grid.get("tracks") or [])
    scope = resolve_track_scope(tracks, target)
    if not scope:
        known = ", ".join(str(track.get("group_name") or "") for track in tracks)
        role_values = {str(t.get("layer_role") or "") for t in tracks if t.get("layer_role")}
        roles = ", ".join(sorted(role_values))
        raise BeatGridEditError(
            f"트랙/역할 '{target}'을 찾을 수 없습니다 — 이 곡의 트랙: {known} "
            f"(역할: {roles}). 이름을 지어내지 않습니다."
        )

    # --- 검증을 전부 끝낸 뒤에 쓴다 (부분 적용 금지) -------------------------
    report: list[str] = []
    warnings: list[str] = []

    if "brightness" in changes:
        _validate_brightness(changes["brightness"])
    if "entry" in changes:
        # 카드 t574 — 트리거 박 범위는 그 곡 박자표(호출자가 곡 데이터에서 읽어 넘김).
        _validate_entry(changes["entry"], beats_per_bar)
    if "effect_kind" in changes:
        _validate_effect_kind(changes["effect_kind"])
    if "evidence" in changes:
        _validate_evidence(changes["evidence"])
    if "app_movement" in changes:
        _validate_app_movement(changes["app_movement"])

    new_preset_label = changes.get("new_preset_label")
    if "new_preset_label" in changes:
        _assert_ascii_preset_label(new_preset_label)

    # 효과 프리셋 풀 번호대(REQ-LDBEAT-015(a)(b)) — effect_kind가 changes에
    # 있으면 그걸 쓰고, 없으면 이 스코프의 기존 칸 값을 본다(단일 칸 기준 —
    # 스코프가 여러 트랙이면 각 트랙의 기존 값을 따로 본다, 아래 루프에서).
    policy = load_preset_pool_policy()

    # 축 충돌(REQ-LDBEAT-006(vi-7))·근거 승인(REQ-LDBEAT-015(f)(g))은
    # **병합된 칸** 기준으로 검사해야 한다 — 기존 칸 값과 이번 변경을
    # 합친 뒤에 본다. 스코프의 트랙마다 기존 칸이 다를 수 있으므로 먼저
    # 병합 결과를 전부 만들어 검증하고(쓰기 전), 전부 통과해야 그다음에
    # 쓴다.
    merged_cues: dict[int, BeatGridCue] = {}
    for index in scope:
        track = tracks[index]
        existing = _find_cue(track, bar)
        base = dict(existing) if existing is not None else {"bar": bar}
        merged_raw = {**base, **{k: v for k, v in changes.items() if k != "new_preset_label"}}
        merged = normalize_beat_grid_cue(merged_raw)
        # 새 프리셋 번호의 승인(REQ-LDBEAT-015(f)(g))은 이번 changes 에 함께 온
        # evidence.approval 만 인정한다 — 칸에 이미 있던 승인(예: t555 밝기
        # 100% 승인)이 새 번호를 통과시키면 안 된다(감독 선택 2026-10-11,
        # 합친 CI run 38112994889 빨강의 원인). 카드 t577(REQ-LDBEAT-015(h-5))
        # 이후로도 이 "저장된 승인 재사용 금지" 자체는 그대로 유지한다 —
        # 바뀌는 것은 거절이 발화하는 시점뿐이다(h-6).
        fresh_approval_cue = merged if "evidence" in changes else {**merged, "evidence": None}

        # 카드 t577(REQ-LDBEAT-015(h-1)) — 새 프리셋 번호를 완전한
        # evidence.approval 없이 넣어도 **거절하지 않는다**. 그 칸·필드는
        # 초안에 그대로 받아들여지고 "승인 대기" 상태로 남는다 — 관찰
        # 가능한 상태는 새 필드가 아니라 `check_evidence_approval`(완전성
        # 판정)과 non-null 프리셋 번호의 교차로 파생된다. 승인은 이제
        # 편집 시점이 아니라 「⇪ 콘솔에 반영」 승인 카드에서만 일어난다
        # (`server/web/session.py` `beat_grid_apply`, h-2~h-4).
        pending_fields: list[str] = []

        effect_kind = merged.get("effect_kind")
        effect_number = merged.get("effect_preset_no")
        if effect_number is not None and "effect_preset_no" in changes:
            pool_reason = validate_preset_pool_assignment(effect_kind, effect_number, policy)
            if pool_reason is not None:
                # 카드 t551 계속(코디네이터 지시 2026-10-11, 조건 3) — REQ-
                # LDBEAT-015(b)의 shall 절은 "종류별 풀에 나눠 담긴다"는 저장
                # 분리 원칙만 구속하고, 정확한 번호대 자체는 spec.md REQ-
                # LDBEAT-015 증거 칸이 "M2/M3 재확인 대상"이라고 명시한
                # PROVISIONAL 값이다(§5 항목 4). `policy["confirmed"]`가
                # 그 재확인 여부를 쥔다 — 확정 전에는 거절이 아니라 경고다
                # (REQ-LDBEAT-010의 "실기 미확인 모양" 경고-아닌-거절과
                # 같은 관행). 확정 후에는 그대로 거절한다(회귀 없음).
                if policy.get("confirmed"):
                    raise BeatGridEditError(pool_reason)
                warnings.append(f"⚠ 번호대 미확인 — {pool_reason}")
            if check_evidence_approval(fresh_approval_cue) is not None:
                pending_fields.append(EDITABLE_CUE_FIELD_LABELS["effect_preset_no"])

        brightness = merged.get("brightness") or {}
        if (
            brightness.get("mode") == "dimmer_effect"
            and brightness.get("preset_no") is not None
            and "brightness" in changes
        ):
            pool_reason = validate_preset_pool_assignment(
                "dimmer", brightness.get("preset_no"), policy
            )
            if pool_reason is not None:
                # 위 effect_preset_no 분기와 같은 confirmed-게이트(조건 3).
                if policy.get("confirmed"):
                    raise BeatGridEditError(pool_reason)
                warnings.append(f"⚠ 번호대 미확인 — {pool_reason}")
            if check_evidence_approval(fresh_approval_cue) is not None:
                pending_fields.append("디머 효과 프리셋")

        # 카드 t577(REQ-LDBEAT-015(h-1)) — position_preset_no·color_preset_no
        # 도 그 네 필드에 포함되지만(h-1 본문), 이전까지 이 승인 완전성
        # 판정 경로에 아예 없었다(plan M10 1단계가 메우라고 지목한 틈) —
        # 여기서 같은 모양으로 메운다. 둘 다 풀 번호대 자체가 없으므로
        # `validate_preset_pool_assignment` 호출은 없다(위치/색 프리셋은
        # 그 검사의 대상이 아니다).
        if (
            merged.get("position_preset_no") is not None
            and "position_preset_no" in changes
            and check_evidence_approval(fresh_approval_cue) is not None
        ):
            pending_fields.append(EDITABLE_CUE_FIELD_LABELS["position_preset_no"])

        if (
            merged.get("color_preset_no") is not None
            and "color_preset_no" in changes
            and check_evidence_approval(fresh_approval_cue) is not None
        ):
            pending_fields.append(EDITABLE_CUE_FIELD_LABELS["color_preset_no"])

        if pending_fields:
            group_name = track.get("group_name")
            warnings.append(
                f"⚠ 승인 대기 — {group_name} {bar}마디 {', '.join(pending_fields)}: "
                "「⇪ 콘솔에 반영」 승인 카드에서 승인해야 콘솔로 나갑니다"
            )
            # REQ-LDBEAT-015(h-5) — 이 칸에 저장될 `evidence`는 `fresh_
            # approval_cue`가 본 값(이번 changes 가 "evidence" 를 안 실었으면
            # None)과 같아야 한다. 안 그러면 base 의 **낡은** 승인이 그대로
            # 남아, 나중에 `check_evidence_approval(merged)`을 그 칸에 다시
            # 돌리면 "승인됨"으로 거짓 통과한다(이번 CI가 실측으로 잡은
            # 결함 — 승인 재사용 금지는 판정 단계뿐 아니라 **저장**에도
            # 적용돼야 한다).
            merged = {**merged, "evidence": fresh_approval_cue.get("evidence")}

        conflict_reason = check_app_movement_axis_conflict(merged)
        if conflict_reason is not None:
            raise BeatGridEditError(conflict_reason)

        if "app_movement" in changes:
            # REQ-LDBEAT-010 — 미확인 어휘는 거절이 아니라 **경고**다(명시적 선택은
            # 막지 않는다). 확인 여부는 M1 표(``grid["probe_results"]``)와 실측
            # 무빙 기록에서만 읽는다 — 코드 상수 목록 없음(카드 t579).
            group_no = track.get("group_no") if track.get("group_no_confirmed") else None
            terms = unverified_movement_terms(
                merged.get("app_movement"),
                grid.get("probe_results") or {},  # type: ignore[arg-type]
                group_no=group_no if isinstance(group_no, int) else None,
            )
            if terms:
                warnings.append(
                    f"⚠ 실기 미확인 — {track.get('group_name')} {bar}마디 "
                    f"{'·'.join(terms)}: M1 프로브로 아직 확인되지 않았습니다 "
                    "(REQ-LDBEAT-010). 곡의 기본값으로는 쓰지 않고, 송신은 M1 게이트를 거칩니다."
                )

        merged_cues[index] = merged

    # --- 여기부터 쓰기. 위를 전부 통과했으므로 중간에 튀지 않는다. ---------
    updated = copy.deepcopy(dict(grid))
    updated_tracks = list(updated["tracks"])
    for index, merged in merged_cues.items():
        track = dict(updated_tracks[index])
        cues = [dict(cue) for cue in track.get("cues") or []]
        replaced = False
        for position, cue in enumerate(cues):
            if cue.get("bar") == bar:
                cues[position] = merged
                replaced = True
                break
        if not replaced:
            cues.append(merged)
            cues.sort(key=lambda c: c["bar"])
        track["cues"] = cues
        updated_tracks[index] = track
        changed_fields = ", ".join(
            EDITABLE_CUE_FIELD_LABELS[key] for key in changes if key != "new_preset_label"
        )
        report.append(f"{track['group_name']} {bar}마디 {changed_fields} 수정")
    updated["tracks"] = updated_tracks

    if new_preset_label is not None:
        report.append(f"신규 프리셋 이름 제안: {new_preset_label} (콘솔 생성은 별도 송신 경로)")

    report.extend(warnings)
    return updated, report


def apply_beat_grid_edit_range(
    grid: Mapping[str, object],
    *,
    bar_start: int,
    bar_end: int,
    target: str,
    changes: Mapping[str, object],
    beats_per_bar: int | None = None,
) -> tuple[dict[str, object], list[str]]:
    """``apply_beat_grid_edit``의 마디 **범위** 판이다 — 문장 경로(②)가
    받는 mockup 명령창의 실제 모양("22~25마디 MOVER-D ...")을 그대로
    따른다(``reports/ldbeat-runbook-ui-proposal-20261008.html`` `#bRule`).

    ``[bar_start, bar_end]``(양끝 포함) 구간에서 ``target``에 매칭되는
    트랙의 **이미 있는 칸에만** 적용한다 — mockup의 ``bRule`` 핸들러와
    같은 선택: 새 칸을 새로 만들지 않는다(``segs=SEG[...].filter(...)``,
    없으면 거절). 직접 고르기(path ①)와 달리 "그 바에 칸이 없으면 새로
    만든다"는 `apply_beat_grid_edit` 자신의 계약이 아니라 이 범위 함수가
    의도적으로 좁힌 것이다 — 문장 범위 편집에서 새 칸을 지어내지 않는다.

    **부분 적용 금지**는 전체 범위에 걸린다 — 범위 안 칸 중 하나라도
    검증에 실패하면 전부 되돌린다(어느 칸도 바뀌지 않는다)."""
    tracks = list(grid.get("tracks") or [])
    scope = resolve_track_scope(tracks, target)
    if not scope:
        known = ", ".join(str(track.get("group_name") or "") for track in tracks)
        raise BeatGridEditError(
            f"트랙/역할 '{target}'을 찾을 수 없습니다 — 이 곡의 트랙: {known}. "
            "이름을 지어내지 않습니다."
        )
    bars_in_range: set[int] = set()
    for index in scope:
        for cue in tracks[index].get("cues") or []:
            cue_bar = cue.get("bar")
            if isinstance(cue_bar, int) and bar_start <= cue_bar <= bar_end:
                bars_in_range.add(cue_bar)
    if not bars_in_range:
        raise BeatGridEditError(
            f"{bar_start}~{bar_end}마디에 '{target}'의 칸이 없습니다 — 문장 범위 편집은 "
            "이미 있는 칸만 고칩니다(새 칸을 지어내지 않습니다)."
        )
    current = grid
    report: list[str] = []
    for bar in sorted(bars_in_range):
        current, bar_report = apply_beat_grid_edit(
            current, bar=bar, target=target, changes=changes, beats_per_bar=beats_per_bar
        )
        report.extend(bar_report)
    return dict(current), report
