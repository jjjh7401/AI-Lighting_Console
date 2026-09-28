"""카드 t484 2단계 — 색 이름이 0개이던 Q2 후보 9개에 감독 결정(2026-09-28)을
적용한다. 1단계 조사: `.moai/reports/t484/verdict.md`.

감독 결정:
1. 표준 문구 보강 — Ring In +블루 · Cross +앰버 · Wall +블루/시안
2. 색 어휘에 흰색 별칭 — 웜화이트→Warm White · 쿨화이트→Cool White.
   빈티지·Home = 웜화이트, Center = 쿨화이트
3. 팝·Fan Out 은 '색 미정' 표시
4. 기본 색 조합은 감독이 Warm/Cool 을 고른다 — 지금처럼 미해소(맨 '화이트'도 미해소 유지)

곡 큐 경로(업로드 입구 ``prepare_songcue`` — t480 이후 대화 길과 같은 조립기)를
실제로 돌려 저장 큐마다 색 줄이 서는지 본다 — 1단계 실측(옛 경로)은 9개 모두
5/5 구간 감독 색 미적용이었다. 계기와 대조군은 t483 시험의 것을 그대로 쓴다.
"""

from __future__ import annotations

import pytest

from server.design.color_names import COLOR_PALETTE_SEQUENCE, resolve_color_name
from server.design.interview import _palette_value_tokens, _q2_color_candidates
from server.design.profile import (
    CONCEPT_SEED_TABLE,
    GENRE_DEFAULT_TABLE,
    GLOBAL_DEFAULT_COLOR_TENDENCY,
    UNIFIED_MOOD_TABLE,
    MusicProfile,
)
from server.tests.test_q2_modifier_token_primary_t483 import _upload_color_counts

_RGB = dict(COLOR_PALETTE_SEQUENCE)


def _tendency(name: str) -> str:
    for seed in CONCEPT_SEED_TABLE:
        if seed.concept == name:
            return seed.color_tendency
    for genre in GENRE_DEFAULT_TABLE:
        if genre.genre == name:
            return genre.color_tendency
    for entry in UNIFIED_MOOD_TABLE:
        if entry.label == name:
            return entry.color_tendency
    raise KeyError(name)


#: 감독 결정 1·2 — 후보 → 주색이 돼야 할 표준 10색 이름.
_DECIDED_PRIMARY = {
    "Ring In": "Blue",
    "Cross": "Amber",
    "Wall": "Blue",
    "빈티지": "Warm White",
    "Home": "Warm White",
    "Center": "Cool White",
}


def test_white_aliases_resolve() -> None:
    assert resolve_color_name("웜화이트") == _RGB["Warm White"]
    assert resolve_color_name("쿨화이트") == _RGB["Cool White"]


def test_bare_white_stays_unresolved() -> None:
    """감독 결정 4 · t409 — 맨 '화이트'/'흰색' 은 여전히 미해소."""
    assert resolve_color_name("화이트") is None
    assert resolve_color_name("흰색") is None


@pytest.mark.parametrize("name", sorted(_DECIDED_PRIMARY))
def test_decided_candidate_primary_is_the_decided_color(name: str) -> None:
    tokens = _palette_value_tokens(_tendency(name))
    assert resolve_color_name(tokens[0]) == _RGB[_DECIDED_PRIMARY[name]], (name, tokens)


@pytest.mark.parametrize("name", sorted(_DECIDED_PRIMARY))
def test_decided_candidate_reaches_every_songcue_cue(name: str) -> None:
    stores, colors, failures = _upload_color_counts(_tendency(name))
    assert stores > 0
    assert colors == stores, (name, colors, stores)
    assert not failures, failures


def _candidate(profile: MusicProfile, value: str) -> tuple[str, str, str]:
    for candidate in _q2_color_candidates(profile):
        if candidate[2] == value:
            return candidate
    raise AssertionError(value)


@pytest.mark.parametrize(
    ("profile", "value"),
    [
        (MusicProfile(genre="팝"), _tendency("팝")),
        (MusicProfile(), _tendency("Fan Out")),
        (MusicProfile(), GLOBAL_DEFAULT_COLOR_TENDENCY),
    ],
    ids=["pop", "fan-out", "global-default"],
)
def test_colorless_candidate_is_marked_undecided(profile: MusicProfile, value: str) -> None:
    label, description, _value = _candidate(profile, value)
    assert "색 미정" in label
    assert "색 미정" in description


def test_candidate_with_a_color_is_not_marked() -> None:
    label, description, _value = _candidate(MusicProfile(genre="록"), _tendency("록"))
    assert "색 미정" not in label
    assert "색 미정" not in description


def test_every_q2_candidate_is_either_colored_or_marked() -> None:
    """전수 — 풀리는 색 이름이 없는데 표시도 없는 후보가 하나도 남지 않는다."""
    profile = MusicProfile(concept="빈티지", genre="팝")
    seen = [c for c in _q2_color_candidates(profile)]
    seen += [c for c in _q2_color_candidates(MusicProfile(concept="우주", genre="edm"))]
    for label, _description, value in seen:
        colored = any(resolve_color_name(t) is not None for t in _palette_value_tokens(value))
        assert colored or "색 미정" in label, (label, value)
