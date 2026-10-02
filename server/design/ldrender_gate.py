"""송신 직전 연출 판독 게이트 — `.moai/reports/t499/readout.py` 의 핵심 판정 로직을
제품 코드로 승격한 것 (SPEC-LDRENDER-001 M1, REQ-LDRENDER-013).

## 이 모듈이 하는 것과 하지 않는 것

readout.py 는 **보고서 전용 CLI 스크립트**다 — 곡 디렉터리의 JSON/텍스트 파일을
읽어 판독하고 표준출력에 찍는다. 이 모듈은 그 판독 로직 중 "무엇을 세는가"만
분리해 **임포트 가능한 순수 함수**로 만든다 — 파일 입출력은 하지 않는다(호출자가
이미 파싱한 값을 넘긴다).

readout.py 는 `.moai/reports/` 아래의 히스토리 기록이고(이 SPEC 의 §5 제약 —
과거 실행의 재현성이 그 파일의 가치다), 이 모듈이 아래에서 고치는 집계 규칙
(LIT-only) 때문에 readout.py 를 이 모듈 호출로 바꾸면 그 파일이 낸 과거 출력
(`readout_8songs.txt`, `summary.json` 등)이 바뀐다 — 그래서 readout.py 는
건드리지 않는다(M1 progress.md 참조).

## readout.py 와의 차이 — LIT-only 집계 (감독 결정 2)

readout.py 의 `rig_view`/`violations`(`stage_rig_layers`, `§6.2`)는 **디머
값과 무관하게** 그룹의 상태가 비어 있지 않으면(즉 그 그룹에 속한 기구가 이 큐
이전에 한 번이라도 값을 받았으면) 버킷에 넣는다 — 디머=0(꺼짐)인 그룹도
"층"으로 셌다. 감독 결정 2(spec.md HISTORY 2026-10-01 2차 개정)는 이것을
무효로 했다: **디머>0(LIT)인 역할만 "서로 다른 값을 받는 층"으로 센다.**
AC-LDRENDER-001·AC-LDRENDER-012·AC-LDRENDER-013 전부 이 규칙을 공유한다 —
게이트가 다른 셈법을 쓰면 게이트 PASS 와 AC-001 의 실제 판정이 어긋난다.

## readout.py 와의 또 다른 차이 — 버킷 단위 단순화 (의도된 단순화, §Gaps 참조)

readout.py 의 `distinct_layers = len({tuple(v) for v in view.values() if v})`
는 "그룹 하나가 내부적으로 서로 다른 상태 여럿을 가질 수 있다"는 경우까지
다룬다(`tuple(v)` 가 그 그룹의 **상태 목록 전체**를 한 단위로 다룬다). 이
모듈의 :func:`layer_diversity` 는 그 경우를 다루지 않고 — 상태 하나하나를
독립적으로 버킷에 넣는다(한 그룹 내부가 갈라져도 그 갈라진 상태들이 각각
다른 그룹의 상태와 우연히 같으면 합쳐질 수 있다). 지금까지 측정된 입력
(Rain 송신 목록, t499 8곡)에서는 그룹 내부가 늘 균일해(각 그룹의 상태 목록
길이가 1) 두 셈법이 일치한다 — 코드 판독으로 확인했을 뿐 그룹 내부가 갈라진
입력으로 실측하지는 않았다(§Gaps, M1 progress.md).
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "BLACKOUT_KIND",
    "MIB_PREMOVE_KIND",
    "GateResult",
    "SectionCue",
    "color_count",
    "effect_group_in_value_lines",
    "effect_line_count",
    "evaluate",
    "gate_cues_from_commands",
    "is_exempt_cue",
    "kind_for_composed_cue",
    "layer_diversity",
    "role_group_map",
]

#: AC-LDRENDER-001 이 "구간 큐 전부" 요구에서 명시 예외하는 두 큐 종류
#: (spec.md AC-001 본문, acceptance.md 경계 사례). 둘 다 정의상 정상 점등
#: 상태가 아니다.
BLACKOUT_KIND = "blackout"
MIB_PREMOVE_KIND = "mib_premove"
_EXEMPT_KINDS = frozenset({BLACKOUT_KIND, MIB_PREMOVE_KIND})

#: readout.py 의 포지션 프리셋 풀 번호 — `At Preset 2.<slot>` 류는 포지션
#: 프리셋이지 효과(페이저) recall 이 아니다(readout.py `phaser_or_other_preset_lines`
#: 의 바로 그 제외 규칙 — `At Preset 2\.` 을 뺀다). 새 규칙을 발명하지 않고
#: 그대로 재사용한다.
_POSITION_PRESET_POOL = "2"
_PRESET_LINE = re.compile(r"At Preset (\d+)\.(\d+)")

#: `rig.RIG_LAYER_ROLES`(`effect`) 가 쓰는 콘솔 그룹 이름들 — readout.py 의
#: `GROUP_NAMES`(14/15/16 = BLIND/STROBE/HAZE)와 동치. REQ-007/M5 가 이
#: 그룹들을 비액센트 큐의 공유 `fids` 에서 빼는 작업을 할 때 쓸 선행 유틸이다
#: (M1 은 이 함수를 만들기만 한다 — 아직 아무 데도 배선하지 않는다).
_DEFAULT_EFFECT_GROUP_NAMES: tuple[str, ...] = ("BLIND", "STROBE", "HAZE")


@dataclass(frozen=True)
class SectionCue:
    """한 구간 큐의 판독 입력 — readout.py 의 `read_song()`이 만드는 per-cue
    row 중 이 게이트가 쓰는 부분집합.

    ``role_view``는 readout.py의 ``rig_view(state)``와 같은 모양이다 — 역할
    (리그 그룹) 이름 -> 그 역할에 속한 기구들의 서로 다른 상태(dict, JSON 가능)
    목록. 각 상태 dict는 최소 ``"dim"``(디머 퍼센트, 없으면 미점등으로 간주)을
    담아야 LIT 판정이 의미가 있다.
    """

    cue_no: str
    name: str = ""
    kind: str | None = None
    role_view: Mapping[str, Sequence[Mapping[str, Any]]] = field(default_factory=dict)
    sent_rgb: tuple[tuple[float, float, float], ...] = ()
    group_lines: tuple[str, ...] = ()


def is_exempt_cue(cue: SectionCue) -> bool:
    """AC-001 의 블랙아웃/MIB 사전이동 예외 — 이 큐는 "구간 큐 전부" 판정에서 뺀다."""
    return cue.kind in _EXEMPT_KINDS


def layer_diversity(role_view: Mapping[str, Sequence[Mapping[str, Any]]]) -> int:
    """한 큐의 LIT-only 서로 다른 값 버킷 수 (감독 결정 2, AC-001/AC-012 집계).

    `role_view`의 각 역할(그룹)에 실린 상태들 중 디머>0(LIT)인 것만 모아, 그
    상태(JSON 직렬화)가 서로 다른 개수를 센다. 디머가 0 이하이거나
    `"dim"` 키 자체가 없는(한 번도 디머 값을 받지 못한) 상태는 꺼짐으로 보고
    버킷에서 뺀다 — "과반"·"평균"이 아니라 **있으면 센다**(큐 단위 전수 판정).
    """
    lit_values: set[str] = set()
    for states in role_view.values():
        for state in states:
            dim = state.get("dim")
            if dim is None:
                continue
            try:
                if float(dim) <= 0:
                    continue
            except (TypeError, ValueError):
                continue
            lit_values.add(json.dumps(state, sort_keys=True))
    return len(lit_values)


def effect_line_count(sent_lines: Sequence[str]) -> int:
    """송신 명령 목록 중 효과(페이저) recall 줄의 수.

    readout.py 의 `phaser_or_other_preset_lines` 와 같은 규칙을 재사용한다 —
    `At Preset <pool>.<slot>` 류 줄 중 포지션 프리셋 풀(`2`)은 뺀다(새 규칙을
    발명하지 않는다).
    """
    count = 0
    for line in sent_lines:
        match = _PRESET_LINE.search(line)
        if match and match.group(1) != _POSITION_PRESET_POOL:
            count += 1
    return count


def color_count(
    cues: Sequence[SectionCue],
    *,
    exclude_rgb: tuple[float, float, float] | None = None,
) -> int:
    """곡 전체 고유 송신 RGB 수 — 예외 큐(블랙아웃/MIB)는 제외.

    ``exclude_rgb``(M7, REQ-LDRENDER-004 §6.3 집계 플래그·M4 §Gaps 2 해소) —
    주어지면 그 RGB(통상 `key` 역할의 표준 팔레트 웜화이트)는 "곡 전체 고유
    색" 집계에서 뺀다. spec.md §3.2 [HARD]가 명시한 읽음(웜화이트는 §6.3
    "최대 2개" 집계 밖, 중립 기준광)을 그대로 따른다 — 기본값 ``None``은
    제외하지 않아 기존 호출부(`evaluate()`의 과거 동작 포함)와 바이트
    동일하다."""
    rgbs = {
        rgb
        for cue in cues
        if not is_exempt_cue(cue)
        for rgb in cue.sent_rgb
        if exclude_rgb is None or rgb != exclude_rgb
    }
    return len(rgbs)


def color_change_count(cues: Sequence[SectionCue]) -> int:
    """연속한 구간 큐 사이에 송신 색이 바뀌는 지점의 수 — 예외 큐는 건너뛴다."""
    changes = 0
    previous: tuple[tuple[float, float, float], ...] | None = None
    for cue in cues:
        if is_exempt_cue(cue):
            continue
        if previous is not None and cue.sent_rgb and set(cue.sent_rgb) != set(previous):
            changes += 1
        if cue.sent_rgb:
            previous = cue.sent_rgb
    return changes


def effect_group_in_value_lines(
    group_lines: Sequence[str],
    *,
    effect_group_names: Sequence[str] = _DEFAULT_EFFECT_GROUP_NAMES,
) -> tuple[str, ...]:
    """비액센트 큐의 값 줄 중 effect 역할 그룹(BLIND/STROBE/HAZE)을 겨냥한 줄.

    REQ-LDRENDER-007/M5 의 선행 유틸 — 이 함수는 **플래그만** 한다(값 줄에서
    실제로 effect 그룹을 빼는 것은 M5 의 몫, `reviewed_song_commands` 배선).
    M1 은 이 함수를 아직 아무 판정에도 쓰지 않는다 — `evaluate()`의 `violations`
    에 영향 없음(§Gaps, M1 progress.md 가 명시).
    """
    return tuple(line for line in group_lines if any(name in line for name in effect_group_names))


#: M7(REQ-LDRENDER-014) 배선 전용 정규식 — `reviewed_song_commands`가 실제로
#: 내는 송신 줄 문법(`song_cue_render.py` `position_cue_bundle`/
#: `_group_color_apply_command`/`_color_apply_command`)의 **부분집합**만
#: 겨냥한다. fid 멤버십은 몰라도 된다(RG5) — `Fixture <fids list>` 줄은
#: 선택 집합을 식별할 필요 없이 "공유 베이스라인 값"으로만 읽고, `Group <n>`
#: 줄은 ``role_group_map()``(아래)이 층 매핑에서 뽑은 역할로 옮긴다.
_STORE_CUE_LINE = re.compile(r"^Store Sequence \d+ Cue ([\d.]+) '([^']*)'")
_FIXTURE_VALUE_LINE = re.compile(r"^Fixture (?:\d+(?: \+ \d+)*) ;(.*)$")
_GROUP_VALUE_LINE = re.compile(r"^Group (\d+) ;(.*)$")
_VALUE_ATTR = re.compile(r"Attribute '(\w+)' At ([\d.]+)")
_RGB_ATTR_KEYS = ("ColorRGB_R", "ColorRGB_G", "ColorRGB_B")


def role_group_map(layer_mapping: Sequence[Mapping[str, object]]) -> dict[int, str]:
    """``layer_mapping`` → 그룹 번호 → 역할 (production 이 실제로 겨냥하는
    그룹만, `song_cue_render._role_group_numbers`/`_effect_group_numbers`와
    같은 동점 규율).

    단일값 역할(`key`/`back`/`side`/`wash`/`mover`)은 마지막으로 일치한
    항목이 이긴다(여러 콘솔 그룹이 한 역할에 매칭될 수 있어도 송신기는
    그중 하나만 주소로 쓴다). `effect`는 반대로 **서로 다른 그룹 번호를
    전부** 보존한다(BLIND/STROBE/HAZE가 각자 독립 주소이기 때문,
    `_effect_group_numbers`와 동형) — 그래서 단일 딕셔너리 컴프리헨션
    (마지막 항목이 이기는 축)을 공유하면서도 `effect`는 여러 키(그룹 번호)가
    전부 그 값으로 모인다(각 그룹 번호가 서로 다른 키이므로 자연히 보존됨).
    """
    mapping: dict[int, str] = {}
    for entry in layer_mapping:
        role = entry.get("role")
        group_no = entry.get("group_no")
        if not isinstance(role, str) or not isinstance(group_no, int) or isinstance(group_no, bool):
            continue
        mapping[group_no] = role
    return mapping


def kind_for_composed_cue(cue: object) -> str:
    """조립기 큐(``ComposedCue``) → 게이트 ``kind`` 어휘.

    ``ComposedCue.kind`` 자체는 블랙아웃을 모른다(``cue.dimmer.blackout``
    플래그로만 구분, acceptance.md AC-001 본문) — 이 함수가 그 변환을 한다.
    ``mib_premove``는 그대로 옮기고, 그 외(``section``/``climax_return``)는
    블랙아웃 플래그가 서면 :data:`BLACKOUT_KIND`로, 아니면 ``"section"``으로
    접는다(``climax_return``도 AC-001 "구간 큐 전부" 요구에서 예외가 아니다
    — spec.md §3.1 §Gaps, M3 후속에서 해소됨)."""
    if cue.kind == MIB_PREMOVE_KIND:
        return MIB_PREMOVE_KIND
    if getattr(getattr(cue, "dimmer", None), "blackout", False):
        return BLACKOUT_KIND
    return "section"


def gate_cues_from_commands(
    commands: Sequence[str],
    bundle_cues: Sequence[object] = (),
    *,
    layer_mapping: Sequence[Mapping[str, object]] = (),
) -> tuple[SectionCue, ...]:
    """송신 직전(또는 직후) 명령 목록 → :class:`SectionCue` 목록 (M7,
    REQ-LDRENDER-013/014 배선).

    ``reviewed_song_commands``가 실제로 조립한 문자열을 **그대로** 판독한다
    — 큐별 디머/색 값을 다시 계산하지 않는다(렌더 함수들의 역할-배정 로직을
    여기서 재구현하면 그 로직과 조용히 어긋날 위험이 있다, moai-memory 교훈
    "코드 판독은 실측이 아니다"와 같은 이유로 **송신된 문자열 자체**를
    1차 증거로 삼는다). ``.moai/reports/t501/measure_ac001_8songs.py``
    `_gate_cues_from_commands`(이 SPEC 의 측정 스크립트, readout.py
    `parse_sent`/`apply` 재사용)와 **같은 상태-추적 규율**이지만, 이 함수는
    fid 멤버십(`fid_names.json`, INFERRED)이 전혀 없어도 동작한다 — production
    이 실제로 쓰는 ``Group <n>`` 그룹-주소 문법(RG5)만 읽기 때문이다.

    상태는 역할(그룹 주소가 가리키는 역할, ``role_group_map()``) 단위로
    추적한다 — ``Fixture <...>`` 줄(공유 베이스라인, 전체 기구 묶음)은 이미
    알려진 모든 역할에 같은 값을 적용하고(콘솔 트래킹 가정과 같은 last-wins
    방향), ``Group <n>`` 줄은 그 역할 하나만 덮어쓴다. ``Store Sequence N
    Cue X '<name>'`` 줄에서 그 시점까지의 역할별 상태를 그 큐의
    :class:`SectionCue`로 접는다 — readout.py의 "큐 경계 = Store 줄, 그 앞
    값 줄을 순서대로 적용" 규율과 동형이다.

    ``bundle_cues``(조립기 번들, ``bundle.cues``)는 큐 번호로 교차조회해
    ``kind``(section/climax_return→"section"/blackout/mib_premove)만
    얻는다 — 없으면(``bundle_cues=()``) 모든 큐를 ``"section"``으로 본다
    (보수적 기본값 — 예외 큐를 놓치면 과도하게 엄격해질 뿐 조용히 느슨해지지
    않는다)."""
    group_roles = role_group_map(layer_mapping)
    all_known_roles = set(group_roles.values())
    cues_by_number: dict[str, object] = {}
    for cue in bundle_cues:
        number = getattr(cue, "cue_number", None)
        if number is not None:
            cues_by_number[f"{number:g}"] = cue

    state: dict[str, dict[str, object]] = {}
    gate_cues: list[SectionCue] = []
    for line in commands:
        store = _STORE_CUE_LINE.match(line)
        if store is not None:
            cue_no, name = store.group(1), store.group(2)
            composed = cues_by_number.get(cue_no)
            kind = kind_for_composed_cue(composed) if composed is not None else "section"
            sent_rgb = tuple(
                sorted({tuple(v["rgb"]) for v in state.values() if "rgb" in v})  # type: ignore[arg-type]
            )
            role_view = {role: (dict(values),) for role, values in state.items()}
            gate_cues.append(
                SectionCue(
                    cue_no=cue_no,
                    name=name,
                    kind=kind,
                    role_view=role_view,
                    sent_rgb=sent_rgb,
                )
            )
            continue
        fixture_match = _FIXTURE_VALUE_LINE.match(line)
        group_match = None if fixture_match is not None else _GROUP_VALUE_LINE.match(line)
        if fixture_match is None and group_match is None:
            continue
        body = fixture_match.group(1) if fixture_match is not None else group_match.group(2)
        attrs = dict(_VALUE_ATTR.findall(body))
        rgb = tuple(float(attrs[key]) for key in _RGB_ATTR_KEYS) if "ColorRGB_R" in attrs else None
        if fixture_match is not None:
            target_roles = all_known_roles | set(state)
            for role in target_roles:
                role_state = state.setdefault(role, {})
                if "Dimmer" in attrs:
                    role_state["dim"] = float(attrs["Dimmer"])
                if rgb is not None:
                    role_state["rgb"] = rgb
        else:
            role = group_roles.get(int(group_match.group(1)))
            if role is None:
                continue
            role_state = state.setdefault(role, {})
            if "Dimmer" in attrs:
                role_state["dim"] = float(attrs["Dimmer"])
            if rgb is not None:
                role_state["rgb"] = rgb
    return tuple(gate_cues)


@dataclass(frozen=True)
class GateResult:
    """REQ-013 게이트의 판정 결과 — 색 수 · 큐별 LIT 층 수 · 효과 줄 수 + 위반 목록."""

    color_count: int
    color_change_count: int
    cue_lit_layers: tuple[tuple[str, int], ...]
    min_cue_lit_layers: int | None
    effect_lines_sent: int
    fx_requested: int
    fx_hinted: int
    palette_mode: str
    violations: tuple[str, ...]

    @property
    def warns(self) -> bool:
        """REQ-014 — 경고가 발동하는가 (비차단 — 송신을 막지 않는다)."""
        return bool(self.violations)


def evaluate(
    cues: Sequence[SectionCue],
    *,
    sent_lines: Sequence[str] = (),
    fx_requested: int = 0,
    fx_hinted: int = 0,
    palette_mode: str = "modulate",
    warm_white_rgb: tuple[float, float, float] | None = None,
    effect_role_mapped: bool = True,
) -> GateResult:
    """REQ-013/REQ-014 게이트 본체 — AC-001 과 바이트 동일한 LIT-only·큐-단위
    집계로 색 수·층 수·효과 줄 수를 판정한다.

    ``palette_mode`` 가 ``"modulate"``(기본)가 아니면 색 수 경고는 n/a 로
    처리된다(REQ-015/AC-014 — 비기본 모드를 결함으로 오판하지 않는다).

    ``warm_white_rgb``(M7, REQ-LDRENDER-004 §6.3 집계 플래그·M4 §Gaps 2 해소)
    — 주어지면 `color_count()`가 그 RGB(통상 `key` 역할의 표준 팔레트
    웜화이트)를 "곡 전체 고유 색" 집계에서 뺀다(spec.md §3.2 [HARD] 의
    읽음 — 웜화이트는 §6.3 "최대 2개" 집계 밖, 중립 기준광). 기본값
    ``None``은 과거 동작과 바이트 동일(제외 없음).

    ``effect_role_mapped``(M7, M5 블로커 보고 조건 ① — 효과 역할 그룹이
    층 매핑에 아예 해석되지 않으면 `_effect_dimmer_zero_lines`가 구조적으로
    아무 줄도 못 낸다, 조용한 R3 비적용) — ``False``면 효과 요청 여부와
    무관하게 별도 경고를 낸다. 기본값 ``True``는 과거 호출부와 바이트
    동일(경고 없음).

    경고는 송신을 **차단하지 않는다**(REQ-014, SPEC-LDDESIGN-001 REQ-052 의
    비차단 경고 선례) — 이 함수는 판정만 내고, 그 판정으로 무엇을 할지는
    호출자(M7 의 배선)의 몫이다.
    """
    eval_cues = [cue for cue in cues if not is_exempt_cue(cue)]
    cue_lit_layers = tuple((cue.cue_no, layer_diversity(cue.role_view)) for cue in eval_cues)
    lit_counts = [n for _, n in cue_lit_layers]
    min_lit = min(lit_counts) if lit_counts else None

    violations: list[str] = []

    song_colors = color_count(cues, exclude_rgb=warm_white_rgb)
    if palette_mode == "modulate" and not (2 <= song_colors <= 3):
        violations.append(f"색 수 {song_colors}개(기준 2~3)")

    under_lit = [cue_no for cue_no, n in cue_lit_layers if n < 3]
    if under_lit:
        violations.append(f"LIT 층 3 미만인 구간 큐 {len(under_lit)}개: {', '.join(under_lit)}")

    effect_lines_sent = effect_line_count(sent_lines)
    if (fx_requested > 0 or fx_hinted > 0) and effect_lines_sent == 0:
        violations.append(
            f"효과 요청 {fx_requested}건 · 페이저 제안 {fx_hinted}큐 → 송신 효과 줄 0"
        )
    if not effect_role_mapped:
        violations.append("효과 역할 그룹(BLIND/STROBE/HAZE) 미매핑 — 효과 기구 분리(R3) 비적용")

    return GateResult(
        color_count=song_colors,
        color_change_count=color_change_count(cues),
        cue_lit_layers=cue_lit_layers,
        min_cue_lit_layers=min_lit,
        effect_lines_sent=effect_lines_sent,
        fx_requested=fx_requested,
        fx_hinted=fx_hinted,
        palette_mode=palette_mode,
        violations=tuple(violations),
    )
