"""카드 t484 조사 — 색 이름이 0개인 Q2 후보를 전수로 뜨고, 곡 큐 경로에서
구간마다 주색이 풀리는지 실행으로 잰다. 코드는 바꾸지 않는다(읽기 전용).

실행: uv run python .moai/reports/t484/probe_colorless_q2.py
"""

from __future__ import annotations

from server.design.color_names import resolve_color_name
from server.design.interview import _palette_value_tokens
from server.design.profile import (
    CONCEPT_SEED_TABLE,
    GENRE_DEFAULT_TABLE,
    GLOBAL_DEFAULT_COLOR_TENDENCY,
    UNIFIED_MOOD_TABLE,
)
from server.tests.test_chorus_color_two_paths_t441 import _path_b_selections, _records


def _rows() -> list[tuple[str, str, str]]:
    rows = [("장르", e.genre, e.color_tendency) for e in GENRE_DEFAULT_TABLE]
    rows += [("컨셉", s.concept, s.color_tendency) for s in CONCEPT_SEED_TABLE]
    rows += [("무드", m.label, m.color_tendency) for m in UNIFIED_MOOD_TABLE]
    rows += [("기본", "기본 색 조합", GLOBAL_DEFAULT_COLOR_TENDENCY)]
    return rows


def main() -> None:
    print("== Q2 후보 전수 (토큰 → RGB 해소) ==")
    colorless = []
    for kind, name, text in _rows():
        tokens = _palette_value_tokens(text)
        resolved = [t for t in tokens if resolve_color_name(t) is not None]
        mark = "색 0개" if not resolved else f"주색 {tokens[0]}"
        print(f"{kind}\t{name}\t{text!r}\t{tokens}\t{mark}")
        if not resolved:
            colorless.append((kind, name, text))
    print(f"\n색 이름 0개 후보: {len(colorless)}개")

    print("\n== 곡 큐 경로 실행 (5구간 픽스처, t441) — 주색 실패 사유 수 ==")
    for kind, name, text in colorless:
        _selections, notes = _path_b_selections(records=_records(palette=text))
        first = notes[0] if notes else "-"
        print(f"{kind}\t{name}\t실패 {len(notes)}\t{first}")
    _selections, notes = _path_b_selections(records=_records(palette="블루"))
    print(f"대조군\t'블루'\t실패 {len(notes)}")

    print("\n== 제안에 쓸 색 이름의 현재 해소 여부 ==")
    for word in (
        "앰버",
        "블루",
        "시안",
        "레드",
        "마젠타",
        "퍼플",
        "웜화이트",
        "쿨화이트",
        "Warm White",
        "Cool White",
        "화이트",
    ):
        print(f"{word!r}\tresolve={resolve_color_name(word)}\ttokens={_palette_value_tokens(word)}")


if __name__ == "__main__":
    main()
