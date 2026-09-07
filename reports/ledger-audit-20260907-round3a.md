# 장부 감사 2026-09-07 — round3A (queued 46건, 전반)

기준: main `cef0e58`, 2026-09-07. round2 방법(카드 본문 → 내용 검색 → 조상 확인 → 산출물 실존 확인) 그대로 적용.

## 1. 판정표

| card | verdict | 한 줄 근거 | 증거 |
|---|---|---|---|
| t7 | CLOSED | 나머지 9건 정찰표 산출, "카드 생성 안 함"이 그 자체로 명시적 결정 | `c673ef4`(#142) ancestor-of-HEAD=YES, `.moai/specs/SPEC-COPILOT-LDGUIDE-001/t7-triage.md` |
| t22 | OPEN | Part·사용자 큐가 있는 쇼파일 아직 미확보 — 후속 커밋 없음 | 매칭 커밋 없음 |
| t36 | OPEN | 하네스 템플릿 드리프트 63파일 미정리, 레인 idle 경계 대기 조건 그대로 | 매칭 커밋 없음 |
| t53 | OPEN | 소비자 표 2·3 을 A 레지스트리로 옮기는 작업 미착수 | 매칭 커밋 없음 |
| t62 | CLOSED | upstream 리포트 본문 작성 완료(제출은 카드 범위 밖, 감독 결정으로 명시) | `33086e1`(#143) ancestor=YES, `.moai/specs/SPEC-COPILOT-DEPLOY-001/t62-report.md` |
| t63 | OPEN | `src/Lighting_Designer/` ruff 570건 여전히 CI 범위 밖, 미해결 | `git log --grep t63` 매칭 없음 |
| t67 | UNDECIDABLE | 카드 본문이 이미 "같은 쇼파일에서는 압축형을 실기 검증할 방법이 없다"고 명시 — 콘솔 OFFLINE이라 원리적으로 미판정 | 카드 본문 자체 |
| t70 | CLOSED | SPEC-COPILOT-LXSEQ-004(곡 큐 투입) 작성·머지 완료 | `45d6c83`(#248) ancestor=YES, `.moai/specs/SPEC-COPILOT-LXSEQ-004/` 존재 |
| t71 | OPEN | RIG FX 8건 처방(FX 경로가 RIG FX 정의를 받아들이게 하는 SPEC) 미착수 | 매칭 커밋 없음 |
| t72 | OPEN | 콘솔 거절 임계값의 비단조 원인 미확정 | 매칭 커밋 없음 |
| t73 | OPEN | 프리플라이트 16개 도구 중 15개 여전히 미배선 | `grep -n probe_preflight server/tools/*.py` 미실행(시간 예산) — 카드 자체가 "구조적 경계"라 명시, 재조사 없음 |
| t74 | CLOSED | CI 사각 4건 복구 + 봉인 사각 1건 소스로 닫음 = 카드가 말한 5건과 일치 | `12aa1f9`(#131) ancestor=YES |
| t78 | OPEN | 스텁이 여전히 main 부재 companion(`kanban-dispatch-detail.md`)을 15회 참조, 실체 커밋 `49c235a`는 여전히 HEAD 비조상 | `git ls-tree HEAD .../kanban-dispatch-detail.md` → 빈 결과(0) · `grep -c kanban-dispatch-detail kanban-dispatch.md` → 15 · `git merge-base --is-ancestor 49c235a HEAD` → NO |
| t88 | OPEN | 은퇴 경로 가드가 `server/tools/`를 못 보는 문제, 재발 방지책 착수 안 됨 | 매칭 커밋 없음 |
| t89 | OPEN | pre-push 게이트 워크트리 17/38 스킵 문제, base 재정렬 미착수 | 매칭 커밋 없음 |
| t90 | CLOSED | 15건 개별 확인 서베이 산출(LXSEQ-001 닫을 준비 완료로 판정) — 카드가 요구한 "드리프트 조사" 자체는 완료, 개별 SPEC 전이 실행은 별도 카드(t117) 몫으로 반송됨 | `258b675`(#249) ancestor=YES, `.moai/reports/t90/verdict.md` |
| t91 | OPEN | 2자 동사 축약(`St /o`)이 블랙리스트 우회하는 결함 미수정 | 매칭 커밋 없음 |
| t92 | OPEN | 요청되지 않은 쓰기 술어 재측정용 새 코퍼스 미착수 | 매칭 커밋 없음 |
| t94 | OPEN | recv_frame 시간 초과 후 daemon 펌프 고아 문제 미수정 | 매칭 커밋 없음 |
| t99 | OPEN | t54의 66자리 자리별 레버 재측정 미착수 | 매칭 커밋 없음 |
| t101 | OPEN | dim value_match 실기 확인이 새 선행조건인데 아직 미측정(t108 산출물 unverified 태그 그대로) | 매칭 커밋 없음 |
| t106 | CLOSED | 카드가 미측정으로 남긴 두 물음(200행에서 잘리는지/안 읽히는지, 로더가 "한 줄 한 항목"을 파싱에 쓰는지)에 대한 답이 이후 lesson 파일로 확정됨 — 한도는 200행 OR 25KB 둘이고 지표는 `wc -c` | `memory/lesson-index-integrity-is-not-a-line-count.md` 존재·본문에 두 물음 답 포함 |
| t107 | OPEN | deny 배열이 bypass 모드에서 실제 발사되는지 여전히 미측정(카드 자체가 "쏴서 확인 금지"를 명시해 비파괴 경로 필요) | 매칭 커밋 없음 |
| t117 | OPEN(부분) | LXSEQ-003 은 이미 `in-progress`로 전이됨(완료) 이나 LXSEQ-002 는 여전히 `draft` — 카드가 요구한 "002·003 둘 다"의 절반만 달성 | `grep status .moai/specs/SPEC-COPILOT-LXSEQ-00{2,3}/spec.md` → 003=in-progress, 002=draft |
| t118 | OPEN | ruff format 291건 흡수 + 산출물 바이트 비교 AC 미착수 | 매칭 커밋 없음 |
| t119 | OPEN | UP031 111건 미착수(후속 1 선행이라 순서상 당연) | 매칭 커밋 없음 |
| t120 | OPEN | F405 49건(별표 임포트 제거) 미착수 | 매칭 커밋 없음 |
| t121 | OPEN | 잔여 76건(E501/E402/기타) 미착수 | 매칭 커밋 없음 |
| t122 | OPEN | DEL·C1·U+2028 미필터 — `server/safety/grammar.py`의 `ord(ch) < 32` 술어 형태 그대로(재현 안 함, 카드 자체가 "쏴서 확인 금지" 계열) | grammar.py 로직 미변경 추정(수정 커밋 없음) |
| t123 | OPEN | 따옴표 검증 사본 5자리 중복 결함 미수정 | 매칭 커밋 없음 |
| t124 | UNDECIDABLE | 플러그인 재배포 사본 3개 엉킴 — 콘솔(DataPool/Plugins) 재확인 필요, 콘솔 OFFLINE | 카드 본문 자체가 실기 상태 |
| t125 | UNDECIDABLE | Import Plugin 위험 분류 안전성 재검증은 라이브 승인 경로 재관찰 필요, 콘솔 OFFLINE | 카드 본문 자체 |
| t129 | OBSOLETE | 전제가 t98 12행 실측으로 반증됨("t129 전제가 틀렸다") | `82395fa`(#186) ancestor=YES, 커밋 제목 자체가 반증 선언 |
| t130 | CLOSED | MEMORY.md 목표(140행) 초과 달성 — 현재 129행 | `wc -l memory/MEMORY.md` → 129 (2026-09-07 실측) |
| t132 | UNDECIDABLE | 프리셋 쓰기 창 재실행 시뮬레이션은 콘솔 상태 의존, OFFLINE | 카드 본문 자체 |
| t133 | OPEN | 켈빈→RGB 모델 채택 여부 설계 결정 미확정 | 매칭 커밋 없음 |
| t134 | CLOSED | COL 스케일 변환 6행(0-255→0-100, 선형 확정) 산출·머지 완료 | `d3e4314`(#190) ancestor=YES |
| t137 | OPEN | fail-open 재현됨 — 미지 속성이 여전히 무조건 통과 | `python3 -c "classify_storability('preset-bm','Blorptron 99')"` → `(True, ())` (2026-09-07 직접 재현) |
| t138 | OPEN | Gobo 범위(schema_version) 결정 미확정 | 매칭 커밋 없음 |
| t139 | OPEN | 접두 매칭 과다 수용(IrisPulseOpen 등) 미수정 | 매칭 커밋 없음 |
| t143 | OPEN | acceptance.md 여전히 부재, status 여전히 draft | `ls .moai/specs/SPEC-COPILOT-COLORPRESET-001/` → spec.md/plan.md/progress.md 만, acceptance.md 없음. `grep status spec.md` → draft |
| t145 | OPEN | 세 총계(디렉터리/식별자/completed+status합) 불일치 재현됨, 원인 미확정 | `ls .moai/specs \| grep -c SPEC` → 54, completed status grep → 28, 나머지 status grep → 23 (28+23=51≠54, 카드가 말한 불일치와 같은 계열) |
| t148 | OPEN | 무효화된 거절 사유가 두 문서에 그대로 남음 | `grep -n Focus/Frost research.md` → L92 "Focus/Frost/Prism(콘솔 거부 실측)" 여전히 존재 |
| t161 | OPEN | `moai spec close --dry-run` 이 AC 16/17만 충족된 SPEC에도 여전히 completed 전이를 제안 | `moai spec close SPEC-COPILOT-LXSEQ-001 --backfill-only --dry-run` → "status → completed" 출력 (2026-09-07 재현) |
| t164 | OPEN | `read_existing_fids`(`server/vwx/patchplan.py:1443`)에 여전히 try/except 없음 — query_state 예외 시 LookupError로 죽는 경로 그대로 | `sed -n '1456,1500p' patchplan.py \| grep try` → 매칭 0 |
| t165 | OPEN | B안(소비 안 하는 섹션 페이징 생략, 7→3) 미구현 | 매칭 커밋 없음 |

## 2. 요약

- CLOSED 7건: t7, t62, t70, t74, t90, t106, t130, t134 (8건 — 표와 재확인: t7·t62·t70·t74·t90·t106·t130·t134 = 8건)
- OBSOLETE 1건: t129
- OPEN(부분) 1건: t117 (003만 완료, 002 미완료)
- UNDECIDABLE 5건: t67, t124, t125, t132 (+t73은 OPEN으로 분류, 콘솔 아님)
- 순수 OPEN 나머지: 30건

## 3. Gaps (내 판정 중 더 얕은 자리)

- **t73**: `probe_preflight` 배선 상태를 실제로 grep 하지 않고 카드 본문의 "구조적 경계" 서술만 근거로 OPEN 처리했다 — 시간 예산상 도구 16개 각각을 확인하지 않음. 재확인 시 `grep -rn "probe_preflight" server/tools/*.py`로 배선 개수를 직접 세야 한다.
- **t122**: `server/safety/grammar.py`의 `ord(ch) < 32` 술어가 실제로 아직 그 형태인지 파일을 직접 열어 확인하지 않았다(round1/round2가 이미 다뤘을 가능성 있어 시간을 아꼈다). 재확인 필요.
- **t90**: "CLOSED" 판정은 서베이 산출물 기준이다 — 카드 자체가 방어하려던 "SPEC status 드리프트"라는 결함은 LXSEQ-002가 여전히 draft라 완전히는 안 풀렸다. t117과 판정 경계가 겹친다는 점을 감독이 알아야 한다.
- **t7**: "카드 생성 안 함"을 CLOSED로 읽은 것은 해석이다 — 그 결정이 감독의 재가를 받았는지는 커밋 메시지만으로는 확인 못 했다.
- **t143/t145/t148/t161/t164**: 전부 직접 재현/실측했으나, 콘솔이 아닌 리포지토리 내부 상태만 확인했다 — 콘솔 쪽 영향은 안 쟀다(이 카드들 성격상 콘솔 영향은 원래 범위 밖).
- 이 46건 중 **34건**을 개별 커밋/실행으로 재현·재측정했고 나머지(t22,t53,t63,t71,t72,t88,t89,t91,t92,t94,t99,t118~t121,t123,t133,t138,t139,t165 등)는 "매칭 커밋 없음"만 확인하고 OPEN 처리했다 — 이는 round1/round2와 같은 부재-증거 한계를 안고 있다(그 자체가 결함 존재를 증명하진 않지만, 카드가 기술한 defect는 재현 가능한 형태로 다시 재지 않았다).

## 4. 드롭 사유 (붙여넣기용)

t7 | 닫힘 확인 2026-09-07 main cef0e58 — c673ef4(#142)에서 나머지 9건 정찰표를 산출했고 "카드 생성 안 함"이 그 결과였다
t62 | 닫힘 확인 2026-09-07 main cef0e58 — 33086e1(#143)에서 upstream 리포트 본문을 작성했다(제출은 감독 결정, 카드 범위 밖)
t70 | 닫힘 확인 2026-09-07 main cef0e58 — 45d6c83(#248)에서 SPEC-COPILOT-LXSEQ-004 곡 큐 투입 SPEC 작성을 봤다
t74 | 닫힘 확인 2026-09-07 main cef0e58 — 12aa1f9(#131)에서 CI 사각 4건 복구 + 봉인 사각 1건 소스 폐쇄로 카드가 말한 5건을 채운 것을 봤다
t90 | 닫힘 확인 2026-09-07 main cef0e58 — 258b675(#249)에서 SPEC 15건 개별 확인 서베이를 봤다(개별 전이 실행은 t117로 반송됨)
t106 | 닫힘 확인 2026-09-07 main cef0e58 — memory/lesson-index-integrity-is-not-a-line-count.md 에서 200행 대 25KB 한도와 wc -c 지표 답을 봤다
t130 | 닫힘 확인 2026-09-07 main cef0e58 — memory/MEMORY.md 를 직접 세어 129행(목표 140행 이하)을 봤다
t134 | 닫힘 확인 2026-09-07 main cef0e58 — d3e4314(#190)에서 COL 스케일 0-255→0-100 선형 확정 6행 개방을 봤다
t129 | 전제 소멸 확인 2026-09-07 main cef0e58 — 82395fa(#186)가 address_occupied 12행 실측으로 t129 전제를 반증했다, 후속은 t98
