"""카드 t406 — t402 팔레트 회전이 실제로는 A-B-A-B 두 상태뿐이고, 회전이
언어만 다른 같은 색(한국어 원색 "블루" vs 영어 아크 색 "blue")을 겹쳐
찍는 결함을 고친다.

재현 1 (AB-AB): `_arc_palette` 를 코러스 역할로 회차 1~6 에 걸쳐 부르면
occurrence 1·3·5 가 서로 바이트 동일하고 2·4·6 도 서로 바이트 동일했다
(회전 주기 2). 코러스가 6회를 넘게 반복돼도 상태는 둘뿐이었다.

재현 2 (언어 중복): verse 아크는 ("blue", "cyan") 인데 감독 원색이
"블루"(한국어)면, 회전이 짝수 회차에서 arc[-1]="blue" 를 골라
("블루", "blue") 를 낸다 — 같은 색이 언어만 바뀌어 두 번 찍힌다.

핫픽스(코디네이터 지시, 같은 카드) — 채도/무게는 색 문자열과 분리된
`_arc_accent_weight` 채널로만 나른다. `cue_sheet_apply.py` 의
`_palette_rgb` 는 색 문자열의 첫 토큰을 범례 id 로 읽으므로("P4 핫핑크"
→ "P4"), 무게를 색 문자열에 접두어로 붙이면 그 조회가 항상 실패해
콘솔로 색이 아예 안 나간다(코디네이터 실측). 그래서 상태의 다양성은
이제 `_arc_palette`(색) 와 `_arc_accent_weight`(무게) 두 채널을 함께
봐야 한다 — 색만 보면 여전히 회전 주기 2 다(의도된 설계).
"""

from __future__ import annotations

from server.web.session import _arc_accent_weight, _arc_palette


class TestArcPaletteBreaksTheTwoStateCycle:
    def test_chorus_state_does_not_collapse_to_two_across_six_occurrences(self):
        """상태 = (색, 무게) 쌍. 색만으로는 회전 주기 2가 의도된 설계이지만
        (콘솔 범례 조회를 지키기 위해 — 카드 t406 핫픽스), 무게를 더한
        전체 상태는 6회차에 2종을 넘어야 한다."""
        base = ("블루",)
        seen = {
            (_arc_palette(base, "chorus", occurrence=n), _arc_accent_weight("chorus", n))
            for n in range(1, 7)
        }
        assert len(seen) > 2, f"6회차인데 상태가 {len(seen)}종뿐이다 — A-B-A-B 재발 (t406)"

    def test_accent_weight_is_never_baked_into_the_colour_string(self):
        """카드 t406 핫픽스 — 무게 수식어("짙은"/"연한"/"쿨톤"/"웜톤")가 색
        문자열의 접두어로 섞이면 `cue_sheet_apply.py` 의 범례 조회(첫 토큰
        기준)가 항상 실패한다. "warm white"·"warm special" 같은 원래부터
        있던 두 단어짜리 색 이름은 무게 수식어가 아니므로 걸리지 않는다 —
        여기서 보는 건 "무게 사다리 단어가 색 앞에 붙었는가"뿐이다."""
        base = ("블루",)
        for occurrence in range(1, 9):
            for role in ("intro", "verse", "chorus", "bridge", "finale"):
                colors = _arc_palette(base, role, occurrence=occurrence)
                for color in colors:
                    for weight_word in ("짙은", "연한", "쿨톤", "웜톤"):
                        assert not color.startswith(f"{weight_word} "), (
                            f"{role} 회차 {occurrence}: {color!r} 에 무게 수식어가 "
                            "섞였다 (t406 핫픽스)"
                        )

    def test_verse_never_duplicates_the_directors_colour_under_another_language(self):
        base = ("블루",)
        for occurrence in range(1, 9):
            colors = _arc_palette(base, "verse", occurrence=occurrence)
            assert "blue" not in colors, (
                f"회차 {occurrence}: {colors} — '블루' 와 'blue' 가 같은 색인데 둘 다 찍혔다 (t406)"
            )

    def test_main_colour_is_always_present_verbatim(self):
        base = ("블루",)
        for occurrence in range(1, 9):
            for role in ("intro", "verse", "chorus", "bridge", "finale"):
                colors = _arc_palette(base, role, occurrence=occurrence)
                assert "블루" in colors, f"{role} 회차 {occurrence} 에서 메인 컬러가 사라졌다"

    def test_occurrence_one_stays_byte_identical_to_pre_t406_where_no_collision_existed(self):
        """회귀 없음 — 언어 충돌이 없던 조합은 t402 시절과 바이트 동일해야 한다."""
        base = ("블루",)
        assert _arc_palette(base, "chorus", occurrence=1) == ("warm white", "magenta", "블루")
        assert _arc_palette(base, "verse", occurrence=1) == ("블루", "cyan")

    def test_intro_occurrence_one_also_had_the_language_collision_and_is_now_fixed(self):
        """intro 아크의 첫 색("deep blue")이 "블루" 와 이미 같은 색이었다 —
        intro 는 회차가 항상 1(싱글턴)이라 이 결함은 회전을 기다릴 필요도
        없이 감독이 파랑 계열을 메인으로 고를 때마다 매번 났다."""
        base = ("블루",)
        colors = _arc_palette(base, "intro", occurrence=1)
        assert colors == ("warm special", "블루")
        assert "blue" not in colors


class TestArcAccentWeightChannel:
    """카드 t406 핫픽스 — 무게는 `PaletteDecision.weight` 로만 흐르는
    별도 채널이다."""

    def test_first_occurrence_carries_no_weight(self):
        assert _arc_accent_weight("chorus", 1) is None

    def test_later_occurrences_carry_a_weight_label(self):
        """사다리는 5칸 주기이고 그중 하나("")는 무게 없음 — 그래서 회차
        범위를 넓게 잡아 "다양성"만 확인한다(모든 회차가 None 아님을
        요구하진 않는다: 5·10·15... 회차는 사다리가 원래 무게 없음으로
        되돌아가는 자리다)."""
        labels = {_arc_accent_weight("chorus", n) for n in range(2, 7)}
        assert len(labels) > 1
        assert any(label is not None for label in labels)

    def test_role_without_an_arc_carries_no_weight(self):
        assert _arc_accent_weight("other", 5) is None
