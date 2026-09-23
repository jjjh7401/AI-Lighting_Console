"""컨셉 v2 → 콘솔 명령 컴파일 — SPEC-LDDESIGN-001 M6 (REQ-LDDESIGN-073·074,
카드 t439).

기존 하류를 그대로 재사용한다(REQ-073, 재구현 금지) — 이 모듈이 새로
하는 일은 :mod:`server.concept.gates` 의 :class:`~server.concept.gates.
SongBuild`(:class:`~server.concept.gates.TableRow` 시퀀스)를 그 하류
함수들이 기대하는 입력 형태로 바꾸는 얇은 어댑터뿐이다.

순수 데이터 모듈이다 — OSC 송신·콘솔 접근·네트워크를 하지 않는다(다른
``server/concept/*`` 모듈과 같은 원칙, ``gates.py`` 독스트링).

## 재사용 대응표

- **린트**: :func:`server.design.lint.lint_sheet`
  (:class:`~server.design.lint.LintSheet`, :class:`~server.design.
  profile.MusicProfile`, :class:`~server.design.rig.RigProfile`) — 표를
  :class:`~server.design.lint.LintSection`/:class:`~server.design.lint.
  LintCue` 로 바꿔 그대로 호출한다(``_lint_sheet_from_table``).
- **에너지/헤드룸 예산**: :func:`server.design.energy.axis_budget`
  (``d_level, profile, rig``) — 컨셉 모델에는 D 레벨 필드가 없다(다른
  설계 축, REQ-017 3밴드 확장과 무관). 이 모듈은 각 큐의 ``top`` 밝기(%)를
  energy.py 자신의 §3 표(``dimmer_pct`` 밴드)로 역매핑해 d_level 을 낸다
  (``_d_level_from_brightness`` — designed_rule, 이 SPEC 문면에 명시적
  대응표가 없다). 컨셉 v2가 D 레벨을 직접 내지 않는 한 이 역매핑이 두
  파이프라인을 잇는 유일한 다리다.
- **페이드**: :func:`server.concept.timing.emit_fade` — M5가 이미
  :func:`server.design.cue_fade.store_with_fade` 를 감싸 둔 것을 그대로
  쓴다(새 페이드 문법을 만들지 않는다, REQ-061/073).

## 콘솔 프로필(MusicProfile/RigProfile) — 라이브 콘솔 없이 짓는다

이 컴파일은 ``pilot_baseline.json`` 오프라인 곡 데이터를 다룬다(§4 B군 —
실기 콘솔 프로브는 이 SPEC 범위 밖). 실 리그 패치는
``server.web.session._try_rig_capabilities()`` 가 콘솔을 실제로 읽어야
채워지는데, 그러면 이 계층이 순수 함수가 아니게 된다. 대신
:func:`server.design.rig.build_rig_profile` 를 빈 패치(``patch=[]``,
``groups={}``, ``coords=[]``)로 불러 짓는 **퇴화 프로필**(단일 레이어,
능력 있는 기구 0개)을 쓴다:

- L6/L7 은 ``rig.layer_rules_active()`` 가 거짓이라 자동으로 꺼지고
  :class:`~server.design.lint.DisabledRuleNote` 로 그 사실이 명시된다
  (거짓 PASS 가 아니다 — RG1 원칙 그대로, ``lint.py`` 독스트링).
- ``fx_axes`` 는 능력 있는 기구가 0개이므로 예산이 0으로 잡힌다.

REQ-073 이 요구하는 것은 "실제로 호출하는지"(추적 가능성)이지 "실 리그
값으로 호출하는지"가 아니다 — D 레벨·BPM 만으로도 ``axis_budget`` 은
이미 실제 판독값(디머·페이드·채도 밴드)을 낸다. 실 리그 배선은 M6 의
배선 범위(§3.13) 밖이며, 이 한계는 이 모듈이 감추지 않고 독스트링에
명시한다.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from server.concept.gates import SongBuild, TableRow
from server.concept.timing import emit_fade
from server.design.energy import AxisBudget, axis_budget
from server.design.lint import LintCue, LintReport, LintSection, LintSheet, lint_sheet
from server.design.profile import MusicProfile
from server.design.rig import RigProfile, build_rig_profile

__all__ = [
    "CueEnergyReport",
    "CompileResult",
    "compile_song",
]

# gates.py 의 같은 이름 상수(``_EFFECT_GROUPS``)와 값이 같아야 한다 — 그
# 이름은 gates.py 의 비공개 모듈 상수라 여기서 다시 import 하지 않고
# 값만 복제했다(REQ-007 원샷 어휘가 아니라 큐 안전장치 그룹 이름이므로
# 두 값이 어긋나면 즉시 이 파일의 시험이 잡는다 — vocab.py 가 닫힌
# 어휘를 고정하는 것과 같은 이유로 이 튜플도 열리지 않는다).
_EFFECT_GROUPS: frozenset[str] = frozenset({"BLIND", "STROBE"})

#: energy.py §3 표(``_D_LEVEL_ROWS``)의 ``dimmer_pct`` 밴드 상한을 그대로
#: 옮긴 것 — (상한, 그 밴드의 D 레벨). 밴드가 서로 겹치는 값을 공유하므로
#: (예: D1 20~40 / D2 40~60) 상한을 포함하는 쪽으로 귀속시켜야 경계값
#: (40, 60, 80, 100)이 정확히 한 레벨에만 떨어진다.
_D_LEVEL_BRIGHTNESS_BANDS: tuple[tuple[float, int], ...] = (
    (40.0, 1),
    (60.0, 2),
    (80.0, 3),
    (100.0, 4),
)
#: 위 밴드 표를 다 지나면(100% 초과) 떨어지는 자리표시자 — 호출자
#: (``TableRow.top``)가 항상 0~100 정수라 이 갈래는 정상 입력으로는
#: 닿지 않는다(방어적 상한).
_D_LEVEL_MAX = 5

_DEFAULT_SEQUENCE_NO = 1


def _d_level_from_brightness(top_pct: float) -> int:
    """§ 모듈 독스트링 "에너지/헤드룸 예산" 절 — 밝기(%)를 energy.py 의
    D 레벨 밴드로 역매핑한다.

    **알려진 한계 — D5 는 이 역매핑으로 나오지 않는다.** energy.py §3
    표에서 D4 의 밴드는 80~100%, D5 의 밴드는 정확히 100~100%다 — 밝기
    스칼라 하나만으로는 100%가 "D4 의 상한"인지 "D5 그 자체"인지 구분할
    수 없다(둘이 겹치는 유일한 값). 이 함수는 보수적으로 100%를 D4 에
    귀속한다 — D5는 §3 표 자신이 "headroom_reserved=False"(여유를 전혀
    안 남기는 최댓값 tier)로 구분해 둔 특수 등급이라, 밝기값만으로
    자동 승급시키는 쪽이 오히려 과대 판정이다. 밴드 밖(음수·100 초과)은
    이 함수가 만들지 않는다 — 호출자(``TableRow.top``)는 항상 0~100
    정수다.
    """
    for threshold, level in _D_LEVEL_BRIGHTNESS_BANDS:
        if top_pct <= threshold:
            return level
    return _D_LEVEL_MAX


def _lint_sheet_from_table(table: Sequence[TableRow]) -> LintSheet:
    """표 한 줄(구간/프레이즈/안전 큐)을 :class:`LintSheet` 로 바꾼다.

    구간(``kind=="section"``) 큐마다 새 :class:`LintSection` 을 열고,
    프레이즈·안전 큐는 직전에 연 구간에 속한다(``song_cue_composer.py``
    의 ``_lint_report`` 와 같은 1-구간-당-N-큐 패턴). 표의 첫 행은 항상
    시작 안전 큐(``gates.build_song`` — ``full_rows`` 의 첫 원소)이므로
    첫 반복에서 무조건 구간 하나를 새로 연다.
    """
    sections: list[LintSection] = []
    section_index_by_row: list[int] = []
    current_index = -1
    for row in table:
        if row.kind == "section" or current_index == -1:
            current_index += 1
            sections.append(
                LintSection(index=current_index, name=f"{row.section} {row.occurrence}")
            )
        section_index_by_row.append(current_index)

    cues = tuple(
        LintCue(
            cue_no=float(row.q),
            section_index=section_index_by_row[i],
            d_level=_d_level_from_brightness(float(row.top)),
            fade_seconds=row.timing.seconds,
            # 컨셉 모델은 키/백 층을 나누지 않는다(단일 ``top`` 밝기) —
            # key 칸에만 실제 값을 싣고 back 은 「이 층 자체가 없다」는
            # 뜻으로 None 을 유지한다(LintCue 독스트링 — 0으로 지어내지
            # 않는다).
            key_dimmer_pct=float(row.top) if row.top else None,
            palette_colors=(row.color,) if row.color else (),
            is_accent=row.kind == "phrase",
            is_blackout=row.n_on == 0,
            is_audience_or_blinder=bool(frozenset(row.on) & _EFFECT_GROUPS),
        )
        for i, row in enumerate(table)
    )
    return LintSheet(sections=tuple(sections), cues=cues)


@dataclass(frozen=True)
class CueEnergyReport:
    """큐 하나의 에너지 예산 판독값 — REQ-073 "에너지/헤드룸 예산은
    energy.py 의 D1~D5" 재사용이 실제로 호출됐다는 증거이자 그 결과."""

    q: int
    d_level: int
    budget: AxisBudget


@dataclass(frozen=True)
class CompileResult:
    """곡 하나(:class:`SongBuild`)를 콘솔 명령으로 컴파일한 결과 —
    REQ-073/074 가 검증 대상으로 삼는 산출물."""

    song: str
    commands: tuple[str, ...]
    lint_report: LintReport
    energy_reports: tuple[CueEnergyReport, ...]
    profile: MusicProfile
    rig: RigProfile


def compile_song(build: SongBuild, *, sequence_no: int = _DEFAULT_SEQUENCE_NO) -> CompileResult:
    """REQ-073 — ``SongBuild`` 를 기존 하류(린트·에너지·페이드)로
    통과시켜 콘솔 명령 문자열을 낸다. OSC 송신은 하지 않는다 — 문자열만
    반환한다(다른 ``server/concept/*`` 모듈과 같은 원칙).

    ``sequence_no`` 는 이 컴파일이 저장할 콘솔 시퀀스 번호다 — 실행기
    번호 배정 자체는 이 SPEC 의 M6 배선 범위 밖이라(§4 B군과 별개로,
    REQ-083 의 "Page children 의 i+100" 규칙은 UI/M7 이 결정한다)
    호출자가 넘기지 않으면 자리표시자 1을 쓴다.
    """
    profile = MusicProfile(bpm=build.bpm)
    rig = build_rig_profile(patch=[], groups={}, coords=[])

    sheet = _lint_sheet_from_table(build.table)
    lint_report = lint_sheet(sheet, profile, rig)

    energy_reports: list[CueEnergyReport] = []
    for row in build.table:
        level = _d_level_from_brightness(float(row.top))
        energy_reports.append(
            CueEnergyReport(q=row.q, d_level=level, budget=axis_budget(level, profile, rig))
        )

    commands = tuple(
        emit_fade(
            f"Store Sequence {sequence_no} Cue {row.q} '{row.section} {row.occurrence}'",
            row.timing,
        )
        for row in build.table
    )

    return CompileResult(
        song=build.song,
        commands=commands,
        lint_report=lint_report,
        energy_reports=tuple(energy_reports),
        profile=profile,
        rig=rig,
    )
