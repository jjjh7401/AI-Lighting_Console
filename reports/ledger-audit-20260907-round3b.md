# 장부 감사 2026-09-07 — round3b (queued 후반 46장)

기준: main `cef0e58`, 2026-09-07 측정. 대상: t169~t311 구간의 `queued` 46장(배차서 목록 그대로). round3a 는 나머지 절반을 맡았으므로 겹치지 않음.

## 1. 46행 표

| card | verdict | 근거 | 증거 |
|---|---|---|---|
| t169 | OPEN | REQ 승격 여부·문안 판정이 아직 감독/리드 결정 대기 — 구현·문서 변경 없음 | 카드 본문 자체가 "판정할 것"으로 끝남, 후속 커밋 없음 |
| t170 | OPEN | 같음(번들 순서 계약 REQ 승격 미정) | 상동 |
| t171 | OPEN | 같음(name_unsendable REQ 승격 미정) | 상동 |
| t172 | OPEN | LXSEQ-003 HISTORY 표 정정 미착수 | `.moai/specs/SPEC-COPILOT-LXSEQ-003/spec.md` HISTORY 섹션 미확인(착수 흔적 없음) |
| t173 | OBSOLETE | 카드 본문이 스스로 전제 만료를 적었다(리드가 같은 세션에 만료시킴) — 색인이 이미 24,939B로 줄어 안 잘림 | 카드 본문 1행: "🔴 전제 만료 2026-08-30 (리드가 같은 세션에 만료시켰다)" |
| t175 | CLOSED (근거 약함) | `server/looks/schema.py` 현재 문면이 카드가 요구한 형태(선언 층 먼저·게이트 예외 마지막, P1-1/P1-2 병기)로 이미 되어 있음. 다만 이 파일은 git log 상 커밋 1건(`c1c1382`)뿐이라 "옛 사유 → 새 사유" 전후 diff 를 직접 못 봄 — 스쿼시 머지 관행(t262 확인) 고려 시 그 1커밋에 포함됐을 가능성 | `server/looks/schema.py:8-18` 되읽기, `git log --oneline -- server/looks/schema.py` |
| t178 | OPEN | MEMORY.md 잠금 부재 위험 자체는 구조적 — 잠금 메커니즘 도입 흔적 없음 | 카드가 위험을 기록만 함, 후속 수정 커밋 없음 |
| t180 | OPEN | primary 체크아웃 미커밋 잔재 정리는 별도 세션 사안 — 이 조사가 커밋으로 이어진 흔적 없음 | 카드 자체가 관측 기록, 조치 커밋 미확인 |
| t183 | CLOSED | `except StateQueryError` 가 이제 tools.py 여러 자리(2096·3428·3635·3834·4486·4899·5095 등)에 붙어 있음 — t183 이 찾은 미포착 문제가 t187 작업으로 닫힘 | `grep -n "except StateQueryError" server/orchestrator/tools.py`, PR #228 MERGED (`cad7918a`) |
| t185 | OPEN | `moai todo` 동사 9종 재정의·drop 관행 정착은 판정 대기 사안(t113 done 예외 재검토 등) — 규약 문서 변경 흔적 없음 | 카드 자체가 "판정할 것" 나열, 후속 없음 |
| t187 | CLOSED | 콘솔 침묵 거절 6자리에 대한 방어(`except StateQueryError`)가 PR #228(base e25930c) 로 머지되어 main 에 있음 | `gh pr view 228` state MERGED, mergeCommit `cad7918a`; `git merge-base --is-ancestor cad7918a HEAD` 는 부모 커밋 e25930c 기준 확인, tools.py 실체 존재 |
| t191 | OPEN | 색인 예산(파일명 길이) 결론은 관측 기록일 뿐, 규약화 흔적 없음 | 후속 커밋 없음 |
| t195 | OPEN | §9 검문이 captured_at 낡음을 못 잡는 구멍 — 수정 흔적 없음 | 카드 자체가 구멍 보고, context-window-management.md 등 관련 규칙 파일에 낡음-검문 보강 문구 미확인 |
| t197 | CLOSED | 카드가 요청한 "2회차 — §3.2 상호작용 절 + 6개 명령줄 + 이스케이프 달러 사례"가 PR #242 로 머지됨(제목이 정확히 "정정 — 루프도 히어독도 무죄였다 + 리드 요청 §3.2 상호작용") | `git log --oneline --grep=t197 -i` → `f957fff (#242)`, `git merge-base --is-ancestor f957fff HEAD` |
| t199 | OPEN | 카드 자신이 "⏸️ 파킹 2026-08-31, 재개는 감독 판정 후"로 명시 — 파킹된 미완 3건 미해결 | 카드 본문 1행 |
| t200 | OPEN | 같음. "🔴파킹된 미완" 2건(미추적 잔여물 전수·저장소 절대경로 자리 전수) 미해결 | 카드 본문 |
| t203 | CLOSED | 카드가 요구한 산출물(plan-audit PASS/FAIL 판정 + 근거)이 `.moai/reports/t203/verdict.md` 로 실재 — 판정은 FAIL 이지만 카드의 일(감사 수행)은 완수됨 | `.moai/reports/t203/verdict.md` 헤더: "감사 대상 eec0455 시점의 SPEC … FAIL 6건, WARN 3건" |
| t209 | CLOSED | 카드 본문은 "PR #262 열림, CI 결제 문제로 머지 대기"라 적지만 실측 결과 이미 MERGED — 낡은 기록 | `gh pr view 262` state MERGED mergeCommit `f0011ab`; `git merge-base --is-ancestor f0011ab HEAD` 확인; `server/orchestrator/tools.py:5780` 부근에 `import_lxseq_cues` 실체 존재 |
| t210 | CLOSED | 카드 본문은 "PR #263 열림"이라 적지만 실측 결과 MERGED. `docs/capability-index.md` 실재 | `gh pr view 263` state MERGED mergeCommit `d32b5b1`; `docs/capability-index.md` 파일 존재 확인 |
| t211 | CLOSED | README.md §8 근거표가 카드 목표 숫자대로 갱신됨(커밋 834+ · 테스트 251 · 규칙 71 · 스킬 34 등) | PR #264 → main `92c1896`, `docs/curriculum/README.md:170-182` 되읽기 |
| t213 | CLOSED | sessions.md 의 "음악 → 큐 자동 생성" 행이 '⬜ 미착수' → '✅ 됨' 으로 정정됨 | PR #265 → main `96828ed`, `docs/curriculum/sessions.md` §M7-1 되읽기: "음악 → 큐 자동 생성 … ✅ 됨" |
| t215 | CLOSED | 카드가 요구한 측정("MA3 명령줄이 속성그룹별 Fade/Delay 를 받는가")이 `.moai/reports/t215/verdict.md` 에 "판정: YES(파트 단위)"로 확정됨 | `.moai/reports/t215/verdict.md` §1 |
| t221 | OPEN | POS.02·03·04 조준 불가 원인(물리 vs 규칙) 분석은 나왔으나 후속 조치(좌표 계약 확정·발사)는 t223 으로 이월 — 아직 판정만 있고 구현 없음 | 카드 자체가 관측/단서 기록으로 끝남 |
| t223 | OPEN | "좌표 입력 계약" 확정이 감독 방향만 있고 계약 필드·시행 코드는 미착수 | 카드 본문이 "계약에 들어갈 것" 나열로 끝남, 후속 커밋 미확인 |
| t229 | OPEN | COL.02 켈빈 모델·BM 어휘 거절 모두 설계 판단 대기 — 코드 변경 흔적 없음(FX_LIBRARY 등 무관 코드는 확인했으나 이 카드가 요구한 켈빈/BM 파서 확장은 별개) | 카드 자체가 "설계 판단" 필요로 끝남 |
| t232 | OPEN | 프리셋 참조가 이름 참조인지 슬롯 참조인지 갈래 미확정(t230 이 "이 채널로는 못 잰다"로 확정) | 카드 자체가 미확정 갈래 기술로 끝남 |
| t244 | OPEN | 카드가 스스로 "착수 조건 — 지금은 아니다(bm 이 아직 판정기 보류 상태)"로 명시. `test_lxseq_preset_target_column.py` 는 이 카드가 아니라 t243 의 트립와이어(PR #291)이고, 카드가 요구한 "대상 열 발사 경로" 자체는 미구현 | 카드 본문 "착수 조건" 단락; `git log --oneline -- server/tests/test_lxseq_preset_target_column.py` → `fbbe414 test(t243)…` (t244 아님) |
| t245 | OPEN | "콘솔이 모르는 속성을 거절하는가" 측정 자체가 감독 승인 필요한 콘솔 쓰기 회차 — 수행 흔적(verdict.md 등) 없음 | `.moai/reports/t245/` 디렉터리 부재 |
| t249 | OBSOLETE | 카드가 요청한 "카드 126장 전수 triage"는 바로 이 라운드(round1/2/3a/3b) 자체가 수행 중인 작업으로 대체됨 — 후속 카드는 이 감사 시리즈 | 본 보고서(round3b) + round1/round2/round3a 존재 |
| t255 | CLOSED | 카드가 요구한 산출물("4단계가 무엇을 약속했고 무엇을 냈는가" 판정 + status 정정)이 `.moai/reports/t255/verdict.md` 로 실재, LXSEQ-004 status 도 draft→in-progress 로 이미 전이됨 | `.moai/reports/t255/verdict.md` 요약 3줄; `.moai/specs/SPEC-COPILOT-LXSEQ-004/spec.md:5` `status: in-progress` |
| t261 | CLOSED | COL 프리셋 콘솔 저장 완료 — 8/8 슬롯 확인(콘솔 쓰기 2건, 이미 6건 존재) | `.moai/reports/t261/verdict.md` §1 슬롯 표, `evidence/` 9종 JSON |
| t262 | CLOSED | 카드가 요구한 4항목(status 전이·progress.md 갱신·콘솔 지식 반영·다음 시작점) 산출물이 `.moai/reports/t262/verdict.md` 로 실재, LXSEQ-003/004 status 도 in-progress 로 확인 | `.moai/reports/t262/verdict.md` 요약; spec.md status 상동 |
| t263 | OPEN | 서류 4종+preshow_check 실기 검증 미수행 | `.moai/reports/t263/` 디렉터리 부재 |
| t264 | OPEN | `moai spec audit` 드리프트가 여전히 존재(FXGEN-001·IMGLAYOUT-001 progress.md 부재, RESTORE-001 spec.md 부재) — 완료 조건(드리프트 0) 미달 | `.moai/specs/SPEC-COPILOT-FXGEN-001/progress.md` 부재, `.moai/specs/SPEC-COPILOT-IMGLAYOUT-001/progress.md` 부재, `.moai/specs/SPEC-COPILOT-RESTORE-001/spec.md` 부재(`ls` 확인) |
| t265 | OPEN | LXSEQ-003 status 가 아직 `in-progress`(완료 조건은 `implemented` 전이) | `.moai/specs/SPEC-COPILOT-LXSEQ-003/spec.md:5` `status: in-progress` |
| t266 | OPEN | 완료 조건(열린 카드 ≤40) 미달 — 현재 `moai todo` 의 queued+picked 합이 109장 | `grep -c "queued\|picked" todo_full.txt` = 109(round3b 측정, 2026-09-07) |
| t267 | OPEN | FX_LIBRARY_DIR 에 color/dimmer/movement.yaml 셋뿐 — RIG fx.csv 의 FX.01~08 미등재, find_fx 검색 대상 아님 | `server/fx/loader.py:61` `DEFAULT_LIBRARY_DIR`, 실측 `ls`(color.yaml/dimmer.yaml/movement.yaml 3개뿐) |
| t268 | OPEN | blacklist.yaml 에 "Record Timecode"/"record_timecode" 문자열 부재 — 등재 결정 미착수 | `grep -i "record.timecode" server/safety/blacklist.yaml` → 0건 |
| t283 | OPEN | 큐시트 구간 길이(end_ms 도출 규칙) 재확인 미수행 — 후속 보고서 없음 | 관련 verdict 부재 |
| t284 | OPEN | 큐시트 미채움 항목(mood·total_duration_ms 등) 열기 미착수 | 상동 |
| t292 | OPEN | "시퀀스 조도 올려줘" 오라우팅 — 안전 방향(거절)이라 급하지 않지만 여전히 열림. 카드 자신이 "열림"으로 표기 | 카드 본문 |
| t293 | OPEN | 40자 초과 시 라우팅 이탈 — 실제 지시 빈도 미측정, 조치 없음 | 카드 본문 |
| t298 | OPEN | 마디 쪼개기 미작동 원인(클립 성질 vs 세그멘터 성질) 미구분 | 카드 본문 |
| t303 | OPEN | RigGeometry 에 span 정보 추가 미착수 | `server/**/*.py` 내 `_build_geometry` 관련 span 필드 추가 흔적 확인 안 함(카드 자체 요청 미이행으로 간주) |
| t310 | OPEN | layer_mapping 생산자 이원화(문서 저장 vs preflight) 불일치 — 처방 갈래 미확정, 수정 없음 | 카드 본문 "처방 갈래:"로 끝남 |
| t311 | CLOSED | AC-CG-005 가 SPEC-COPILOT-CLASSIFYGAP-001 sync 세션에서 Phase 2→4 로 최종 PASS 됨(seal-only 7→0) — 카드가 제기한 "SPEC 범위 안에서 달성 불가" 문제가 범위 확대로 해소됨 | `.moai/specs/SPEC-COPILOT-CLASSIFYGAP-001/progress.md:751,770` "AC-CG-005 를 seal-only 2 → 0 으로 마저 닫았다" / "PASS … Phase 4 … seal-only 0" |

## 2. 드롭 사유 (CLOSED/OBSOLETE 전부)

```
t175 | 닫힘 확인 2026-09-07 main cef0e58 — server/looks/schema.py 8-18행이 이미 요구된 선언층-우선 형태(단, 단일 커밋 c1c1382 뿐이라 전후 대조는 스쿼시 병합 관행에 의존)
t183 | 닫힘 확인 2026-09-07 main cef0e58 — tools.py 여러 자리(2096·3428·3635·3834·4486·4899·5095)에 except StateQueryError 확인, PR #228 로 반영됨
t187 | 닫힘 확인 2026-09-07 main cef0e58 — PR #228(cad7918a) 머지로 콘솔 침묵 거절 방어가 반영됨
t197 | 닫힘 확인 2026-09-07 main cef0e58 — PR #242(f957fff)로 2회차(§3.2 상호작용·이스케이프 달러 사례) 반영됨
t203 | 닫힘 확인 2026-09-07 main cef0e58 — .moai/reports/t203/verdict.md 에 plan-audit FAIL 판정 산출 확인, 카드가 요구한 감사 산출물은 완수됨
t209 | 닫힘 확인 2026-09-07 main cef0e58 — PR #262(f0011ab) MERGED 직접 확인, import_lxseq_cues 코드 존재
t210 | 닫힘 확인 2026-09-07 main cef0e58 — PR #263(d32b5b1) MERGED 직접 확인, docs/capability-index.md 존재
t211 | 닫힘 확인 2026-09-07 main cef0e58 — PR #264(92c1896) 반영, README.md §8 근거표 목표 숫자로 갱신 확인
t213 | 닫힘 확인 2026-09-07 main cef0e58 — PR #265(96828ed) 반영, sessions.md 해당 행 ✅ 됨으로 정정 확인
t215 | 닫힘 확인 2026-09-07 main cef0e58 — .moai/reports/t215/verdict.md 에 YES(파트 단위) 판정 산출 확인
t255 | 닫힘 확인 2026-09-07 main cef0e58 — .moai/reports/t255/verdict.md 산출 확인, LXSEQ-004 status in-progress 로 정정 완료
t261 | 닫힘 확인 2026-09-07 main cef0e58 — .moai/reports/t261/verdict.md·evidence/ 로 COL 프리셋 8/8 콘솔 저장 확인
t262 | 닫힘 확인 2026-09-07 main cef0e58 — .moai/reports/t262/verdict.md 산출 확인, LXSEQ-003·004 status in-progress 정합
t311 | 닫힘 확인 2026-09-07 main cef0e58 — progress.md 에 AC-CG-005 PASS(Phase 4, seal-only 0) 확정 확인
t173 | 전제 소멸 확인 2026-09-07 main cef0e58 — 카드 본문이 스스로 만료를 적었고 색인이 이미 재축소됨(리드 후속 관리 대상)
t249 | 전제 소멸 확인 2026-09-07 main cef0e58 — 카드가 요청한 전수 triage 를 이 감사 라운드(round1·round2·round3a·round3b)가 대체 수행함
```

## 3. Gaps — 스스로 흔들리는 판정

- **t175** — 유일하게 diff 대조 없이 CLOSED 로 낸 행. `server/looks/schema.py` 는 git 이력이 커밋 1개(`c1c1382`)뿐이라, "옛 거절 사유"가 실제로 존재했다가 고쳐진 것인지 아니면 처음부터 이 형태였는지를 diff 로 못 갈랐다. 카드 본문이 인용한 t142/t162 흐름과 텍스트 정합은 확인했지만, 이건 정황 증거다. drop 하되 이 한 줄은 감독이 원하면 재확인 가능하도록 남긴다.
- **t249** OBSOLETE 판정은 "성공적으로 대체됐다"는 뜻이 아니라 "이 형태로는 더 이상 별도 작업이 아니다"라는 뜻 — 실제 전수 triage(126장)는 아직 미완이고, round1·2·3a·3b 를 다 합쳐도 46+α 장만 처리했다. t266(완료 조건: 열린 카드 ≤40)이 OPEN 인 것과 짝이다.
- **t203** CLOSED 판정은 "카드의 일이 끝났다"는 뜻이지 "LXSEQ-004 가 통과했다"는 뜻이 아니다 — 감사 결과는 FAIL 이었다. 이 구분을 감독이 다르게 읽을 수 있어 명시해 둔다.
- **t267** 은 find_fx 가 참조하는 디렉터리(`server/fx/library/`)만 봤다 — RIG `fx.csv` 를 다른 경로로 흡수하는 코드가 있는지는 전수로 grep 하지 않았다(시간 제약). OPEN 판정 자체는 안전한 방향(과닫힘 방지)이라 낮은 위험.
- **t172·t178·t180·t191·t195·t221·t223·t229·t232·t244·t245·t283·t284·t292·t293·t298·t303·t310** 은 대부분 "카드 본문이 관측 기록으로 끝나고 후속 커밋이 안 보인다"는 부재 증거에 의존한다 — 각 카드의 인용 SHA/PR 존재 여부만 개별 확인했고, 카드가 지목한 파일의 diff 를 전부 열어보지는 못했다(46장 규모 제약). round2 방법론(§ 확인)을 따랐으나 심도는 얕다.
