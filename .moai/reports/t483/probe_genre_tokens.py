from server.design.interview import _palette_value_tokens
from server.design.profile import GENRE_DEFAULT_TABLE, CONCEPT_SEED_TABLE, UNIFIED_MOOD_TABLE, GLOBAL_DEFAULT_COLOR_TENDENCY
from server.design.color_names import resolve_color_name
rows=[("genre",e.genre,e.color_tendency) for e in GENRE_DEFAULT_TABLE]
rows+=[("concept",s.concept,s.color_tendency) for s in CONCEPT_SEED_TABLE]
rows+=[("mood",m.label,m.color_tendency) for m in UNIFIED_MOOD_TABLE]
rows+=[("global","-",GLOBAL_DEFAULT_COLOR_TENDENCY)]
for kind,name,ct in rows:
    toks=_palette_value_tokens(ct)
    res=[(t, resolve_color_name(t) is not None) for t in toks]
    print(kind,name,"|",ct,"|",res)
