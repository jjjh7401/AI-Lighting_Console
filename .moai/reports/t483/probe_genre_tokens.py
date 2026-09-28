from server.design.color_names import resolve_color_name
from server.design.interview import _palette_value_tokens
from server.design.profile import (
    CONCEPT_SEED_TABLE,
    GENRE_DEFAULT_TABLE,
    GLOBAL_DEFAULT_COLOR_TENDENCY,
    UNIFIED_MOOD_TABLE,
)

rows = [("genre", e.genre, e.color_tendency) for e in GENRE_DEFAULT_TABLE]
rows += [("concept", s.concept, s.color_tendency) for s in CONCEPT_SEED_TABLE]
rows += [("mood", m.label, m.color_tendency) for m in UNIFIED_MOOD_TABLE]
rows += [("global", "-", GLOBAL_DEFAULT_COLOR_TENDENCY)]
for kind, name, ct in rows:
    toks = _palette_value_tokens(ct)
    res = [(t, resolve_color_name(t) is not None) for t in toks]
    print(kind, name, "|", ct, "|", res)
