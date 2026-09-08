### t264 — ALIVE
claim: SPEC 정합 드리프트 5건(completed 인데 progress.md 없음 2 · draft 인데 라이브 E2E 통과 2 · spec.md 없음 1) 미해결
ran: ls .moai/specs/SPEC-*/spec.md 2>/dev/null | wc -l; grep -l "status: completed" .moai/specs/*/spec.md 2>/dev/null; test -f .moai/specs/SPEC-*RESTORE-001*/spec.md
saw: FXGEN-001·IMGLAYOUT-001 completed 상태에서 대응 progress.md 부재 확인, RESTORE-001 디렉터리에 spec.md 없음(경로 부재), COLORPRESET-001·INTROSPECT-001 은 draft 상태 유지 확인 — moai spec audit 재실행 없이 드리프트 0 을 주장할 근거 없음
so: 5건 불일치가 여전히 존재하고 audit 정합화가 아직 실행되지 않았다.

### t265 — ALIVE
claim: SPEC-COPILOT-LXSEQ-003 AC 전수가 아무도 판정하지 않은 상태로 남아 있다
ran: sed -n '1,10p' .moai/specs/SPEC-COPILOT-LXSEQ-003/spec.md; grep -n "^status" .moai/specs/SPEC-COPILOT-LXSEQ-003/spec.md
saw: spec.md:5 status: in-progress — implemented 로 전이되지 않음, .moai/docs/lxseq-status.md 는 AC 판정 미완료를 명시
so: status 가 여전히 in-progress 이므로 카드의 전제(미판정 상태)가 그대로 유지된다.

### t266 — ALIVE
claim: 백로그 121장 triage 필요 — 열린 카드 ≤40 이 완료 조건
ran: moai todo 2>&1 | tail -5
saw: dropped=191, picked=17, queued=72 → open(picked+queued)=89
so: 열린 카드 89 > 목표 40 이므로 triage 작업은 아직 완료되지 않았다(이 세션 자체가 그 triage 작업의 일부이므로 별도 판정 없이 카운트만 보고).

### t267 — ALIVE
claim: RIG fx.csv 의 FX.01~08 이 내장 FX 라이브러리 19종과 이름 교집합 0이며 find_fx 로 검색 안 됨
ran: grep -n "def find_fx" server/orchestrator/tools.py; ls server/fx/library/*.yaml | wc -l; grep -il "FX\." server/fx/library/*.yaml
saw: find_fx 는 server/fx/library/*.yaml(19개 항목)만 검색 대상으로 하며 RIG fx.csv 코드네임(FX.01~08)과 이름 교집합 0(과거 세션 실측, .moai/reports/t225/evidence/fx_preview_all8.json 로 뒷받침) — 재확인 결과 동일 구조 유지
so: RIG 의 8개 FX 는 여전히 find_fx 검색 대상 밖에 있다.

### t268 — DECISION
claim: Record Timecode 를 blacklist.yaml 에 2토큰으로 등재할지 결정 필요
ran: grep -n "Record Timecode\|Store Timecode" server/safety/blacklist.yaml; sed -n '30,45p' .moai/specs/SPEC-COPILOT-MUSICSYNC-001/plan.md
saw: blacklist.yaml:445 에 Store Timecode 는 있으나 Record Timecode 부재(grep exit 1) — plan.md §C 결정 (ii) 가 이미 선택되어 앱이 말하지 않고 QuestionRequest 로 라우팅하는 방식을 채택했고, (i) 등재 방식은 명시적으로 후속 카드로 유보됨(그 후속 카드가 t268 자신)
so: 결정은 이미 내려졌다(ii 채택, i 유보) — 이 카드는 유보된 (i) 옵션을 실행할지 여부를 다시 결정해야 하는 후속 항목이며, 권고는 "현행 (ii) 유지, (i) 은 실제 오사용 사례가 관측될 때 재검토"이다.

### t283 — UNMEASURED
claim: t283 실측 페이로드에서 CHORUS1 이 duration 176s·bar_count 88 로 나와 다음 구간 시작이 아니라 곡 끝(song_end_ms)까지 먹은 것으로 의심됨
ran: grep -rn "176\|88" server/tests/test_cue_density.py; grep -n "CHORUS1" server/tests/test_cue_density.py; find . -path ./node_modules -prune -o -iname "*283*" -print 2>/dev/null; sed -n '195,210p' server/design/cue_density.py
saw: test_cue_density.py 의 SUGAR_SECTIONS 정본 데이터셋에서 CHORUS1 = (56.0s, 16bar, 2cues) — 카드가 주장하는 176s/88bar 와 불일치. cue_density.py:203 에 `end = starts[index+1] if ... else song_end_ms` fallback 로직은 실재하나, 카드가 언급하는 "t283 실측 페이로드" 를 담은 파일/리포트가 저장소 어디에도 없음(find 결과 0건)
so: 의심되는 메커니즘(song_end_ms fallback)은 코드상 존재하지만 카드가 인용하는 구체적 측정값(176s/88bar)을 재현할 원본 페이로드가 없어, `python3 -c "<sugar_timeline 실제 곡으로 cue_sheet 생성 후 CHORUS1 구간 duration/bar_count 출력>"` 형태의 신규 실측 없이는 참/거짓을 정할 수 없다.

### t284 — DEAD
claim: 큐시트 항목 mood·note·total_duration_ms·tc_source·tc_origin·palette_legend·XFADE 구분·다중 fixture_groups 에 자리가 없다(생산자 없음)
ran: grep -n "^class CueSheetSectionFields" server/design/song_plan.py; grep -n "mood\|note\|fixture_groups\|trans" server/design/sugar_timeline.py | head -10; grep -n "TRANS_VALUES" server/design/cue_sheet_edit.py
saw: song_plan.py:903 `class CueSheetSectionFields`(frozen dataclass) 가 total_duration_ms/tc_source/tc_origin/palette_legend 를 실제 필드로 보유; sugar_timeline.py `_section()`(~379-451) 이 mood/note/fixture_groups(list)/trans(="XFADE") 를 딕�너리로 생성; cue_sheet_edit.py:51 `TRANS_VALUES = ("SNAP","XFADE","FADE")` 로 XFADE 를 명시적으로 구분·처리
so: 카드가 "자리 없음"이라 주장한 7개 필드 전부 실제 생산자/구분 로직이 이미 존재하므로 이 카드의 전제는 더 이상 성립하지 않는다.

### t292 — DEAD
claim: "이 시퀀스 조도 올려줘" 같은 시퀀스+올려 문장이 2점을 얻어 적용(반영)으로 오라우팅된다
ran: python3 -c "import re; DEST=re.compile(r'콘솔|데스크|초안|시퀀스\s*\d+'); print(bool(DEST.search('이 시퀀스 조도 올려줘')))"
saw: False — `_DRAFT_APPLY_DESTINATION`(session.py:1128)의 `시퀀스\s*\d+` 는 숫자가 붙은 시퀀스만 매치하며, 카드 예시 문장("이 시퀀스")에는 번호가 없어 destination 축 자체가 매치되지 않음. 번호가 붙는 변형("시퀀스 3의 큐 2 조도 올려줘")은 destination 은 매치하지만 `_DRAFT_APPLY_EDIT_OBJECT`(1140-1142, t301 태그 주석에서 이 정확한 문장을 배제 사례로 명시)가 조도 편집으로 판별해 반영 라우팅을 차단
so: 카드가 지목한 정확한 문장도, 번호가 붙은 변형도 현재 코드에서는 이미 차단되어 있어(t295/t301 후속 수정) 이 misrouting 은 더 이상 재현되지 않는다.

### t293 — ALIVE
claim: 적용 판정의 40자 길이 축이 곡 브리핑 오탐을 막는 대가로 실제 40자 넘는 지시가 라우팅에서 빠지는 빈도가 미측정
ran: grep -n "_DRAFT_APPLY_MAX_CHARS" server/web/session.py; sed -n '1155,1165p' server/web/session.py; find . -iname "*298*" 2>/dev/null; ls .moai/reports 2>/dev/null | grep -i "298\|295"
saw: session.py:1160 `_DRAFT_APPLY_MAX_CHARS = 40` 존재, 주석은 코퍼스 내 최단 실제 적용 명령이 22자임과 197자 회귀 문장 사례만 기록 — 40자 초과 실제 적용 지시의 빈도를 측정한 값이나 리포트(t298/t295 참조 대상) 는 저장소에 없음(find/ls 결과 0건)
so: 40자 경계는 실재하지만 그 경계가 실제 적용 지시를 얼마나 자주 잘라내는지는 여전히 측정되지 않았다 — 필요한 명령은 실제 사용자 발화 코퍼스에 대해 `len(text) > 40 and is_apply_intent(text)` 빈도를 세는 신규 분석이다.

### TALLY
ALIVE: t264, t265, t266, t267, t293
DEAD: t284, t292
DECISION: t268
UNMEASURED: t283
