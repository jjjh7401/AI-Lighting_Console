"""타이밍 필드 기본값 배정 — SPEC-LDDESIGN-001 M5 (REQ-LDDESIGN-058~061).

트리거·구간 종류에 따라 :class:`~server.concept.cue_model.Timing` 기본값
(REQ-058)을 배정한다. 축별 딜레이 콘솔 명령 방출은 이 SPEC 범위 밖이다
(REQ-060 — 데이터 필드만 채운다. `server/director/emit.py:60`
``AXIS_TIMING_OBSERVED`` 관측 0건). 페이드 초는 새 문법을 만들지 않고
기존 :func:`server.design.cue_fade.store_with_fade` 를 그대로 재사용한다
(REQ-061).

**판단 근거 — 이 파일이 내린 결정(spec.md REQ-058 문언은 10종 트리거
어휘와의 1:1 대응을 직접 명시하지 않는다, progress.md 에 편차로 기록)**:

- "드롭·히트·백색 플래시류"는 10종 트리거 중 가장 가까운
  "드롭 직전의 정적"에 대응한다고 본다 — snap.
- "프레이즈 전환(악기 추가 등)"은 문면이 직접 예시로 든 "악기 추가"를
  포함해, 같은 프레이즈 전환 계열인 "악기 제거"·"보컬 시작"·
  "보컬 종료"·"빌드업 시작"까지 묶는다 — short.
- 감독 전용 4종(코드·조성 변화·핵심 가사·안무 대형 변화·중심 멤버·
  솔로 변경)은 "발라드성 공간 확장" 계열의 느린 분위기 전환으로 보아
  long 을 기본값으로 삼는다.
- 트리거가 없거나(대다수 구간 큐) 위 세 분류 밖이면 AC-LDDESIGN-011
  ("모든 시퀀스 큐가 timing 을 가진다")을 지키기 위해 short 를 안전
  기본값으로 쓴다 — Outro 구간은 예외로 long(:func:`outro_timing`).
"""

from __future__ import annotations

from server.concept.cue_model import Timing
from server.design.cue_fade import store_with_fade

__all__ = [
    "SNAP_SECONDS",
    "SHORT_SECONDS",
    "LONG_SECONDS",
    "CHORUS_ENTRY_STAGGER",
    "CHORUS_ENTRY_ATTR_SPLIT",
    "default_timing",
    "chorus_entry_timing",
    "outro_timing",
    "emit_fade",
]

SNAP_SECONDS = 0.2  # REQ-058 snap: 0~0.3초
SHORT_SECONDS = 1.5  # REQ-058 short: 1~2초
LONG_SECONDS = 3.0  # REQ-058 long: 2~4초

_SNAP_TRIGGERS: frozenset[str] = frozenset({"드롭 직전의 정적"})
_SHORT_TRIGGERS: frozenset[str] = frozenset(
    {"악기 추가", "악기 제거", "보컬 시작", "보컬 종료", "빌드업 시작"}
)
_LONG_TRIGGERS: frozenset[str] = frozenset(
    {"코드·조성 변화", "핵심 가사", "안무 대형 변화", "중심 멤버·솔로 변경"}
)

# REQ-059 — 후렴 진입 큐 기본 순차 딜레이(중앙→외곽).
CHORUS_ENTRY_STAGGER = "0→0.4s 중앙→외곽"
# REQ-060 — 후렴 진입 큐에서 최소 색·밝기를 분리해 기록한다.
CHORUS_ENTRY_ATTR_SPLIT: tuple[str, ...] = ("color", "dimmer")


def default_timing(*, trigger: str | None = None, section: str | None = None) -> Timing:
    """REQ-058 — 트리거(있으면 우선) 또는 구간 종류에 따른 기본 Timing."""
    if trigger in _SNAP_TRIGGERS:
        return Timing(kind="snap", seconds=SNAP_SECONDS, attr_split=False, stagger=None)
    if trigger in _SHORT_TRIGGERS:
        return Timing(kind="short", seconds=SHORT_SECONDS, attr_split=False, stagger=None)
    if trigger in _LONG_TRIGGERS:
        return Timing(kind="long", seconds=LONG_SECONDS, attr_split=False, stagger=None)
    if section == "Outro":
        return outro_timing()
    return Timing(kind="short", seconds=SHORT_SECONDS, attr_split=False, stagger=None)


def chorus_entry_timing(*, stagger: str = CHORUS_ENTRY_STAGGER) -> Timing:
    """REQ-059/060 — 후렴 진입 큐: snap + stagger + 색/밝기 분리."""
    return Timing(
        kind="snap", seconds=SNAP_SECONDS, attr_split=CHORUS_ENTRY_ATTR_SPLIT, stagger=stagger
    )


def outro_timing() -> Timing:
    """REQ-058 — 발라드성 공간 확장·아웃트로는 long."""
    return Timing(kind="long", seconds=LONG_SECONDS, attr_split=False, stagger=None)


def emit_fade(store: str, timing: Timing) -> str:
    """REQ-061 — 페이드 초 방출은 기존 ``store_with_fade`` 를 그대로
    재사용한다(새 페이드 문법을 만들지 않는다, ``Property 'Fade'`` 형태는
    계속 금지다)."""
    return store_with_fade(store, timing.seconds)
