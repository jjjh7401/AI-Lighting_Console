### t120 — ALIVE
claim: 49 F405 (star-import leakage) violations exist in src/Lighting_Designer/90_빌드파이프라인/, suppressed via per-file-ignores.
ran: python3 -m ruff check "src/Lighting_Designer/90_빌드파이프라인/" --isolated --select F405,F403 --statistics
saw: 49 F405 undefined-local-with-import-star-usage; 4 F403 undefined-local-with-import-star; Found 53 errors.
so: --isolated (bypassing pyproject.toml per-file-ignores) reproduces exactly the claimed 49 F405 count, so the underlying violations are still unfixed and still suppressed — premise holds.

### t122 — ALIVE
claim: server/safety/grammar.py:98 uses ord(ch) < 32 to reject control characters, which lets DEL (0x7F), C1 controls (0x80-0x9F), and U+2028 (0x2028) pass through unrejected.
ran: grep -n "ord(ch)" server/safety/grammar.py; sed -n '90,110p' server/safety/grammar.py
saw: line 98: "if ord(ch) < 32:" — DEL is ord 127, C1 range is ord 128-159, U+2028 is ord 8232; none satisfy < 32.
so: the predicate's numeric threshold arithmetically excludes DEL/C1/U+2028 from rejection, so this narrower-than-intended character class still passes the grammar layer — premise confirmed true by direct read of the source line, no console interaction needed.
### t121 — DEAD
claim: residual suppressed-lint debt on the 4 per-file-ignored files totals 76 (E501 35, E402 17, other {B007,B905,E741,SIM115} 24 combined).
ran: per-file `python3 -m ruff check "src/Lighting_Designer/90_빌드파이프라인/<file>.py" --isolated --line-length 100 --select E501,E402,B007,B905,E741,SIM115 --statistics` for make_rig.py, make_timeline.py, make_xlsx.py, validate.py (the 4 files actually named in pyproject.toml per-file-ignores).
saw: make_rig.py: E501 16, B007 1 (17); make_timeline.py: E501 14, E402 1 (15); make_xlsx.py: E501 13, E402 5, B905 3 (21); validate.py: E501 8, E402 3, B007 1 (12). Sums: E501=51, E402=9, B007=2, B905=3, E741=0, SIM115=0, total=65.
so: today's per-file totals (E501 51, E402 9, other 5, total 65) do not match the card's claimed breakdown (E501 35, E402 17, other 24, total 76) on any single code, so the specific "76" baseline is measurably stale — real debt exists but at different numbers than claimed. (Note: a naive directory-wide `--isolated` scan without narrowing to just these 4 files returns E501=234/E402=19/B007=9/E741=6/B905=5/SIM115=1 because it also picks up files outside the per-file-ignores list entirely — that wider number is NOT comparable to the card's claim and was discarded in favor of the per-file scoped measurement above.)

### t123 — ALIVE
claim: five copies of a quote-validation routine exist (position_preset_store_commands, position_cue_store_commands, _validated_label, _phaser_sequence_commands, preset_apply_command); reachability must be measured before calling it a defect.
ran: grep -n 'def <fn>' across server; sed -n windows on each definition; grep -rn '<fn>(' server | grep -v 'def <fn>' for each of the 5 names.
saw: all 5 functions exist at pointing.py:357/401, position_fx.py:116, session.py:3656, store.py:80. Each carries the same duplicated shape `if not text or "'" in text or '"' in text: raise ...`. Non-test callers: position_preset_store_commands <- session.py:5201; position_cue_store_commands <- session.py:7412; _validated_label <- position_fx.py:209; _phaser_sequence_commands <- session.py:5880; preset_apply_command <- orchestrator/tools.py:1967.
so: all five copies are reachable from a live non-test call site, so the duplication is not dead code — premise (5 copies, all reachable) holds.
