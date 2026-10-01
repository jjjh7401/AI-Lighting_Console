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
    "is_exempt_cue",
    "layer_diversity",
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


def color_count(cues: Sequence[SectionCue]) -> int:
    """곡 전체 고유 송신 RGB 수 — 예외 큐(블랙아웃/MIB)는 제외."""
    rgbs = {rgb for cue in cues if not is_exempt_cue(cue) for rgb in cue.sent_rgb}
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
) -> GateResult:
    """REQ-013/REQ-014 게이트 본체 — AC-001 과 바이트 동일한 LIT-only·큐-단위
    집계로 색 수·층 수·효과 줄 수를 판정한다.

    ``palette_mode`` 가 ``"modulate"``(기본)가 아니면 색 수 경고는 n/a 로
    처리된다(REQ-015/AC-014 — 비기본 모드를 결함으로 오판하지 않는다).

    경고는 송신을 **차단하지 않는다**(REQ-014, SPEC-LDDESIGN-001 REQ-052 의
    비차단 경고 선례) — 이 함수는 판정만 내고, 그 판정으로 무엇을 할지는
    호출자(M7 의 배선)의 몫이다.
    """
    eval_cues = [cue for cue in cues if not is_exempt_cue(cue)]
    cue_lit_layers = tuple((cue.cue_no, layer_diversity(cue.role_view)) for cue in eval_cues)
    lit_counts = [n for _, n in cue_lit_layers]
    min_lit = min(lit_counts) if lit_counts else None

    violations: list[str] = []

    song_colors = color_count(cues)
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
