"""``CueFade`` — 이 저장소가 **실측한 유일한 페이드 형태**를 조립하는 한 자리.

이 파일은 새 문법이 아니다. ``cue_sheet_apply.plan_console_apply`` 안에 인라인으로
있던 세 줄(``store += f" CueFade {…:g}"`` 과 그 위의 주석)을 **들어 올린** 것이고,
소비자가 둘이 되는 순간 그렇게 했다 — 곡→큐 경로(``server/looks/songcue.py``)가
같은 문법을 쓰기 때문이다. 베끼면 두 벌이 되고, 두 벌은 조용히 갈라진다.

**문법의 근거**(옮겨 온 원문 그대로):

* ``Store … Cue <n> '<이름>' CueFade <초>`` 는 T11 프로브 §2/§4 에서 실제로 성공한
  형태다(``server/web/session.py`` ``_preset_recall_store_commands`` 독스트링).
* ``Property 'Fade'`` 는 **금지**다 —
  ``docs/handoff/2026-08-15-timeline-workflow-handoff.md:19``.
* ``/Merge`` 와 함께 쓰는 순서의 실행 로그는
  ``.moai/specs/SPEC-COPILOT-INTENT-001/progress.md:66`` 에 있다.

**왜 ``server/design/`` 인가.** 들어 올린 원본이 여기 있고(``cue_sheet_apply``),
``server/looks/songcue.py`` 는 이미 ``server.design.cue_density`` 를 들여온다 —
looks → design 방향은 기존 배선 그대로다. 반대로 두면 새 의존 방향이 생긴다.

**옮기지 않은 호출자 둘을 적어 둔다**(안 한 것을 못 한 것처럼 적지 않기 위해서다):
``server/spatial/pointing.py`` 와 ``server/spatial/position_fx.py`` 도 같은 문법을
자기 자리에서 조립한다. 그 둘은 자기 SPEC 의 검증 문면을 함께 들고 있어 이 카드의
범위가 아니다 — 셋째 소비자가 생기는 날 같이 옮기는 것이 맞다.
"""

from __future__ import annotations

__all__ = ["CUE_FADE_KEYWORD", "CueFadeError", "store_with_fade"]

CUE_FADE_KEYWORD = "CueFade"


class CueFadeError(ValueError):
    """조립할 수 없는 페이드 값. 숫자가 아니거나 음수다."""


def store_with_fade(store: str, fade_seconds: float | None) -> str:
    """``Store …`` 줄에 페이드를 붙인다. ``None`` 이면 **받은 줄 그대로** 돌려준다.

    ``None`` 갈래가 항등인 것이 이 함수의 무회귀 성질이다 — 페이드가 안 붙는 입력이
    내는 명령은 이 파일이 생기기 전과 바이트 동일하다.

    ``:g`` 포맷은 원본에서 온 것이고 뜻이 있다: ``2.0`` 이 ``2`` 로, ``0.2`` 가
    ``0.2`` 로 나간다. 실측된 문면(``CueFade 2``)과 같은 모양이 되는 쪽이다.
    """
    if fade_seconds is None:
        return store
    if isinstance(fade_seconds, bool) or not isinstance(fade_seconds, int | float):
        raise CueFadeError(f"cue fade must be a number: {fade_seconds!r}")
    if fade_seconds < 0:
        raise CueFadeError(f"cue fade must be non-negative: {fade_seconds!r}")
    return f"{store} {CUE_FADE_KEYWORD} {fade_seconds:g}"
