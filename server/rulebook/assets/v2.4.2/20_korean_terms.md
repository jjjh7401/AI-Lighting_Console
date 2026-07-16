# 한국어 조명 용어 사전 (Korean Field-Lighting Term Dictionary Axis)

Korean stage-lighting field vocabulary mapped to grandMA3 object/keyword
vocabulary classes. When a Korean instruction uses a field term from this table,
resolve it to the mapped MA3 vocabulary before generating commands. Where the
mapping is showfile-dependent (marked "showfile"), first look up the actual
group/preset names via `get_rig_context` instead of assuming ids.

| 한국어 용어 | MA3 어휘 (vocabulary class) | 비고 |
|---|---|---|
| 샤막 | Cyc/backdrop wash fixtures — `Group` named like 'Cyc'/'샤막' + related Color/Dimmer `Preset` | sharkstooth scrim wash; showfile |
| 워시 | Wash-class fixtures — Wash FixtureType, `Group` named like 'Wash'/'워시', wash Color/Position `Preset` | showfile |
| 무빙, 무빙라이트 | Moving-head fixtures (Spot/Wash/Beam FixtureTypes) selected via `Group` or `Fixture` ranges | showfile |
| 스팟 | Spot/Profile-class moving heads — Spot FixtureType, `Group` named like 'Spot' | showfile |
| 빔 | Beam-class fixtures — Beam FixtureType, `Group` named like 'Beam' | showfile |
| 핀조명, 폴로스팟 | Followspot/pinspot fixtures — dedicated `Group`, Dimmer/Position `Preset` | showfile |
| 고보 | `Gobo` attribute family — Gobo wheel values, Gobo `Preset` pool | attribute |
| 딤머, 밝기 | `Dimmer` attribute — intensity via `At <0-100>`, `Full`, `Out`, Dimmer `Preset` pool | attribute |
| 색온도 | CTC (color temperature) — Color attribute family, Color `Preset` pool | attribute |
| 색, 컬러 | Color attribute family — color mix/wheel values, Color `Preset` pool | attribute |
| 큐 | `Cue` object inside a `Sequence` (`Cue 5 Sequence 2`) | object |
| 시퀀스 | `Sequence` object | object |
| 그룹 | `Group` object (stored fixture selection) | object |
| 프리셋 | `Preset` object (pool.slot addressing, e.g. `Preset 4.1`) | object |
| 매크로 | `Macro` object (stored command list) | object |
| 페이더 | Executor fader — `Page <page>.<executor>` with `At <level>` | object |
| 페이지 | `Page` object (executor layout page) | object |
| 페이드 | `Fade` timing keyword (`Store Cue 5 Fade 3`) | keyword |
| 객석등 | House-light fixtures — `Group` named like 'House'/'객석' | showfile |
| 암전 | Blackout — intensity to 0 on the relevant selection (`At 0` / dedicated cue); NEVER map to `Off Everything` without explicit human approval | safety |

Rule: this dictionary is part of the FIXED prompt prefix — it never contains
per-show or per-turn values. Showfile-dependent rows name a vocabulary CLASS;
the concrete object ids come from `get_rig_context` at run time.
