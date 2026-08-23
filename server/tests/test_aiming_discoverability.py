"""t6 — 조준 발화 조건 문서가 코드보다 덜 적으면 조용히 어긋난다.

조준은 등재된 툴이 아니라 ``server/web/session.py`` 의 정규식이 문장에서 바로
잡아내는 기능이다. 그래서 감독이 그 기능에 닿는 유일한 길은 **어떻게 말해야
발화되는지를 아는 것**이고, 그것을 알려 주는 곳은 사용 가이드의 발화 조건 절뿐이다.

이 어긋남은 실패 신호가 없다. 가이드가 트리거를 덜 적어도 코드는 멀쩡히 돌고,
테스트도 초록이고, 아무도 되묻지 않는다. 덜 적힌 만큼 감독이 못 쓸 뿐이다 —
실제로 `point` · `aim` · `center` · `centre` 가 동작하는데 가이드는 한국어만
적고 있었다(카드 t6 실측).

한글 트리거는 활용형이라(바라보/바라볼/비춰/비출) 문서의 사전형과 글자 단위로
대조할 수 없다. ASCII 트리거는 활용이 없으므로 기계 대조가 성립한다 — 그래서
이 가드는 **영문 트리거만** 본다. 좁지만 확실한 축이다.
"""

from __future__ import annotations

import re
from pathlib import Path

from server.web.session import _POINT_AT_TARGET, _POINT_TARGET_CENTRE

PROJECT_ROOT = Path(__file__).resolve().parents[2]
USER_GUIDE = PROJECT_ROOT / "docs" / "user-guide.html"
FIRE_CONDITION = re.compile(r"<div class=.fire-condition.>(?P<body>.*?)</div>", re.DOTALL)


def _ascii_tokens(pattern: re.Pattern[str]) -> set[str]:
    """정규식 대안 목록에서 ASCII 토큰만 뽑는다 (활용 없는 것들)."""
    raw = pattern.pattern
    return set(re.findall(r"[a-zA-Z]{2,}", raw))


def _fire_condition_text() -> str:
    match = FIRE_CONDITION.search(USER_GUIDE.read_text(encoding="utf-8"))
    assert match is not None, "사용 가이드에 발화 조건 절이 없다"
    return match.group("body")


class TestAimingTriggersAreDocumented:
    """코드가 받는 영문 트리거는 전부 가이드에 적혀 있어야 한다."""

    def test_the_fire_condition_block_exists(self) -> None:
        assert _fire_condition_text().strip(), "발화 조건 절이 비어 있다"

    def test_every_ascii_verb_is_documented(self) -> None:
        body = _fire_condition_text()
        missing = sorted(t for t in _ascii_tokens(_POINT_AT_TARGET) if t not in body)
        assert not missing, (
            f"코드는 받는데 가이드에 없는 조준 동사: {missing} — "
            "감독이 그 표현을 쓸 수 있다는 걸 알 방법이 없다"
        )

    def test_every_ascii_centre_word_is_documented(self) -> None:
        body = _fire_condition_text()
        missing = sorted(t for t in _ascii_tokens(_POINT_TARGET_CENTRE) if t not in body)
        assert not missing, f"코드는 받는데 가이드에 없는 조준점 표현: {missing}"


class TestTheGuardCanActuallyFail:
    """가드가 실패할 수 있는지 — 실패할 수 없는 가드는 가드가 아니다."""

    def test_a_token_absent_from_the_body_is_reported_missing(self) -> None:
        body = "조준 동사: point, aim"
        missing = [t for t in ("point", "aim", "센터없음zzz") if t not in body]
        assert missing == ["센터없음zzz"], "누락 검출 로직이 반대로 동작한다"

    def test_the_extractor_finds_the_english_tokens(self) -> None:
        tokens = _ascii_tokens(_POINT_AT_TARGET)
        assert "point" in tokens and "aim" in tokens, (
            f"추출기가 영문 토큰을 못 찾는다: {sorted(tokens)}"
        )
