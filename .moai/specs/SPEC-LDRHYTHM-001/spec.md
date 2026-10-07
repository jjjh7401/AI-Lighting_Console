---
id: SPEC-LDRHYTHM-001
title: "리듬 연출 — 대본 우선 설계(LOVE ATTACK)"
version: "0.2.0"
status: in-progress
created: 2026-10-05
updated: 2026-10-07
author: jaihyun
priority: P1
phase: "Lighting Copilot v1.2 target"
module: "docs/proposals/song-structure-lighting-standard.md(M3 버전 올림 대상), server/design/song_cue_render.py, server/spatial/position_fx.py, server/looks/movement.py, server/audio/analyze.py (M4+ 앱 구현 후보 — M1~M3 은 대본·시연·규칙화뿐, 코드 변경 0)"
lifecycle: spec-anchored
tags: "rhythm, beat-layer, accent-layer, director-script, bpm-speedmaster, process-gate, love-attack"
tier: M
related_specs: [SPEC-LDRENDER-001, SPEC-LDDESIGN-001, SPEC-COPILOT-FXGEN-001, SPEC-COPILOT-FXLIB-001]
---

# SPEC-LDRHYTHM-001 — 리듬 연출: 대본 우선 설계(LOVE ATTACK)

## HISTORY

| 일자 | 내용 |
|---|---|
| 2026-10-05 | 최초 작성(카드 t504). 입력: `reports/music-lighting-benchmark-20261003.md`(벤치마크+콘솔 조사) · `reports/rhythm-expression-research-20261003.md`(t502, 코드 판독+빈칸 표) · `.moai/reports/t502/verdict.md` · `.moai/reports/t501/sync.md`(AC-LDRENDER-016 FAIL 1~2점) · `docs/proposals/song-structure-lighting-standard.md`. 감독 결정 4건(2026-10-03, 리드 경유)을 전면 반영. Tier M(아래 §0 근거). **plan만 — 코드 변경 0, 콘솔 접촉 0.** |
| 2026-10-05 | **plan-audit iteration 1 FAIL(0.75, 통과선 0.80) 대응.** D1(critical) — AC-LDRHYTHM-006(`acceptance.md`)의 측정 커맨드가 SPEC 디렉터리 전체 `*.md`를 스캔해, 감독 결정 원문 인용(`spec.md:32`)과 이 AC 자신의 서술(`acceptance.md`) 때문에 M1 품질과 무관하게 항상 "§10.3" 매치가 남아 영원히 FAIL 하는 결정 불능 criterion 이었다 — 측정 스코프를 M1 실제 산출물 파일 하나(`m1-club-diver-script.md`, `plan.md` M1 §E 가 그 경로를 고정)로 좁히고, "§10 금지목록 4번"을 정확히 인용했는지(양성)와 "§10.3" 오표기가 없는지(음성) 둘 다 보는 양성+음성 복합 검사로 바꿨다. D2(minor, 선택) — REQ-LDRHYTHM-012 한 문장 안에서 shall-주체가 "다음 항목"→"이 plan-phase"로 바뀌던 것을 비요구사항 참고 각주로 분리해 GEARS 단일 주체 골격을 정리했다. REQ/AC 총량(12/11)·ID 추가삭제 없음 — 문면 교정만. |
| 2026-10-05 | **plan-audit iteration 2 PASS(0.92) + D-NEW-1(major) 대응.** iter1 D1 해소 과정에서 AC-LDRHYTHM-006 의 측정이 "§10 금지목록 4번" 인용/"§10.3" 오표기 문자열 그렙 2건뿐이라, Then 절의 핵심 조건("강조 층은 큰 히트에만 배치")을 실제로 검사하지 않는 구멍이 남아 있었다(인용만 1회 정확히 하고 나머지 배치가 느슨해도 기계적으로 PASS). `plan.md` M1 산출물에 **닫힌 어휘 2열**("층": 박자\|강조, "모멘트유형": 코러스진입\|드롭\|마지막코러스\|기타)을 가진 6칸 표 형식을 신설해 배치 조건을 기계로 셀 수 있게 하고, `acceptance.md` AC-LDRHYTHM-006 을 자매 AC(003~005)와 같은 "오프라인 검사" 패턴으로 재작성 — 층=강조인 행 전수를 모멘트유형 열과 대조해 닫힌 집합 밖(기타 포함)이면 위반으로 집계(위반 수=0 이어야 PASS), 기존 양성/음성 그렙 2건은 유지. "그 항목들은 전부"의 지시 대상을 "층 열 값이 강조인 행 전체"로 명시해 지시어 모호성도 해소. 모멘트유형 라벨의 진실성(그 순간이 실제 큰 히트인지)은 기계 검사가 아니라 M1 감독 검토의 몫임을 양쪽 문서에 명시(REQ-LDRHYTHM-011 과 일치). REQ/AC 총량(12/11)·ID 추가삭제 없음 — M1 표 형식 신설 + AC-006 측정 재작성뿐. |
| 2026-10-05 | **plan-audit iteration 3 FAIL(0.80, blocking) + D-NEW-2(major, 회귀) 대응.** iter2 가 `plan.md` M1 의 표 형식을 6칸(시각/층/모멘트유형/연출/잇는 방식/이유)으로 바꿨는데, REQ-LDRHYTHM-003(`spec.md`)과 AC-LDRHYTHM-003(`acceptance.md`)은 여전히 옛 4칸("음악 순간/놓는 연출/잇는 방식/이유")을 서술해, M1 이 plan.md 대로 6칸 표를 쓰면 AC-003 의 글자 그대로 조건을 만족하는 칸 이름이 하나도 없는 모순이 생겼다 — D-NEW-1 해소가 낳은 전형적 회귀. REQ-003·AC-003 둘 다 plan.md 의 6칸 이름·닫힌 어휘(층: 박자\|강조, 모멘트유형: 코러스진입\|드롭\|마지막코러스\|기타)와 동일하게 교정하면서, "곡의 어느 순간인지→무엇을 두는지→앞 장면과 어떻게 잇는지→왜 그런지"라는 원래 4단계 의도는 유지했다. 감독 결정 원문(`spec.md:34`, verbatim)은 손대지 않았다 — `grep -n "음악 순간\|놓는 연출\|네 칸\|앞 장면과 잇는 방식" spec.md plan.md acceptance.md progress.md` 로 전수 재확인한 결과 그 verbatim 인용 1건만 남고 나머지 모든 참조가 교정됐다. REQ/AC 총량(12/11)·ID 변경 없음. |
| 2026-10-05 | **리드 PR #550 판독 — M2 승인 단위를 묶음 파일 1회 승인으로.** 구간 안 박자 층 이벤트 하나하나를 감독이 개별로 승인해야 한다는 옛 서술은 운영상 불가능하다는 지적 — 박자 층은 곡당 수백 개 이벤트라, 그 서술대로면 감독이 수백 번 승인해야 한다. t498(`real_console.py`/`classify_diff.py`)·t501 AC-016(`.moai/reports/t501/ac016/real_song.py`/`classify_diff.py`)이 쓴 흐름으로 교체했다: 구간(또는 묶음) 단위 커맨드 파일 → 가짜 콘솔 리허설 → 감독이 그 바이트 동일 파일을 **1회** 승인 → 송신. 시연 로그는 묶음 단위로 남기고, 실기 재생 후 감독이 대본의 각 줄에 「어울림/아님」을 표시해 M3 가 쓰는 줄 단위 증거를 남긴다. `spec.md:62`(REQ-001)·`spec.md:128`·`plan.md:36,59,60,79` 를 교정했고, `(REQ-003)`/`(REQ-004)`로 잘못 인용됐던 두 곳(`spec.md:128`, `plan.md:36`)을 승인 절차를 실제로 정의하는 REQ-001 인용으로 바로잡았다. 감독 결정 원문("쓰기는 감독 승인")은 손대지 않았다 — 배치 승인도 감독 승인이다. 네 산출물 전수 재확인 결과 이 교정 전 표현의 잔존 0건. REQ/AC 총량(12/11)·ID 변경 없음. |
| 2026-10-06 | **감독 결정 교정(카드 t508) — 첫 곡을 Club Diver 에서 LOVE ATTACK 으로 교체 + M2 착수 전 AC-012 신설.** 감독 결정(2026-10-06, 리드 경유): 「테스트 음악은 완성도·리듬·비트가 떨어진다. 실제 K-pop 리센느 'LOVE Attack' 으로 다시 진행, 기존 조명연출과 비교」 — 이 결정은 위 "감독 결정 (원문, 2026-10-03)"의 (2)항("첫 곡 Club Diver")을 **대체**한다(원문은 지우지 않고 그대로 남긴다 — 아래 "감독 결정" 절의 교정 메모 참조). REQ-LDRHYTHM-004(첫 곡 범위)·AC-LDRHYTHM-004(곡 범위 검사)·REQ-LDRHYTHM-011/AC-LDRHYTHM-010(합격 기준)을 LOVE ATTACK 기준으로 교정하고, AC-LDRHYTHM-010 에 "같은 곡의 기존 앱 연출과 나란히 비교"(기존 쪽에는 통과 기준이 없고 비교 결과만 기록) 절차를 추가했다. M1 공식 산출물 경로를 `m1-club-diver-script.md`→`m1-love-attack-script.md`로 바꿨다(plan.md M1·acceptance.md AC-003/AC-006 동일 교정). M2 착수(콘솔 첫 송신) 전 게이트로 **AC-LDRHYTHM-012**(승인본=송신본 sha256 동일 + 설명 안 되는 줄 0건)를 신설했다(제안 원문 `.moai/reports/t507/verdict.md` §5, 브랜치 `origin/WT-rhythm-m1`) — 그 제안이 인용한 `classify_diff.py`(`.moai/reports/t498/classify_diff.py`, 이 plan-phase 에서 본문 재확인)는 지금 "승인 대 송신" 비교 도구가 아니라 "리허설 대 실기" 비교 도구이고(`UNEXPLAINED rehearsal-only:`/`UNEXPLAINED real-only:` 두 줄만 찍고 `MISSING` 출력은 없다), 이 사실을 AC-012 측정 란에 명시해 M2 시작 전 준비할 선행 조건(승인-대-송신 비교 스크립트는 아직 없음)으로 적었다. **LOVE ATTACK 원곡 오디오 위치를 §5 플래그로 측정 기록**: `/Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3`(4,733,524바이트, sha256 `9ab52dfb8ac5bd8a0dc09d393b33e28ad650c07262371460994300c98581c9fa`, 2026-10-06 `ls -l`+`shasum -a 256`로 이 plan-phase 에서 직접 재실측) — 저장소 안(`src/sample music/` 등)에는 **의도적으로** 두지 않는다(커밋 안 함). "기존 앱 연출"(AC-010 비교 대상)이 LOVE ATTACK 에 대해 아직 생성되지 않았다는 선행 조건은 §5 플래그로 남긴다. Club Diver 대본 초안(PR #553, 브랜치 `origin/WT-rhythm-m1`, 미머지)은 형식(6칸 표·강조 배치) 참고 자료로만 plan.md M1 에 인용했다 — 내용(시각·이벤트)은 Club Diver 전용이라 재사용하지 않는다. REQ 총량 **12개 불변**, AC 총량 **11→12개**(AC-012 신설, REQ-LDRHYTHM-001 에 트레이스) — Tier M 상한(각 16개) 안에 든다. `status`는 draft 로 불변(run-phase 착수 전 — Status Transition Ownership Matrix 의 상태 전이가 아니라 plan-phase 내부 교정, `spec-frontmatter-schema.md` § Non-transition frontmatter corrections 절 참조). **같은 날 리드 보강**: `reports/loveattack-song-research-20261006.md`(LOVE ATTACK 곡 조사 — 발매정보·음악적 특징·뜻과 콘셉트 §3·시각 콘셉트 §4·연출 단서 §6, 2026-10-06 리드 조사, sha256 `9f136b05abc35d566bdc617f42e47415f92c814fb38e1cc3ede4bc1282871a9b` 확인, 주 체크아웃 원본과 바이트 동일)을 M1 입력 목록(plan.md §A)에 추가하고, REQ-LDRHYTHM-003·AC-LDRHYTHM-003·plan.md M1 의 "이유" 칸 인용 규칙을 벤치마크 §2.1/§2.3 단독에서 그 문서 §3(뜻과 콘셉트)·§4(시각 콘셉트)도 인용할 수 있게 넓혔다 — 그 문서 §6(연출 단서)은 리드의 참고 메모일 뿐 인용 대상이 아니며, §6 단서 5("비트 드롭→강조 층 후보, 큰 히트에만")는 감독 결정 3의 범위 안이어서 강조 층 규칙(REQ-006/AC-006, "강조는 큰 히트에만")을 넓히지 않는다는 점을 plan.md §A 에 명시했다. |
| 2026-10-06 | **t510 기존 앱 연출 기준선 반영 — 전제 갱신(같은 날 후속 카드).** AC-LDRHYTHM-010/REQ-LDRHYTHM-011/plan.md §B 가 "기존 앱 연출(비교 대상)이 아직 생성되지 않았다"고 적었던 것이 낡았다 — 카드 t510(브랜치 `WT-loveattack-base`, origin/main 머지 커밋 `15345084`)이 `reports/loveattack-baseline-20261006.md`(+`.html`)와 `.moai/reports/t510/verdict.md`로 그 기준선을 **가짜 콘솔까지는** 생성했다 — LOVE ATTACK 을 현재 렌더러(송신 층 포함, SPEC-LDRENDER-001 완료 상태)로 돌려 11큐·FakeConsole 송신 190줄·큐별 유지/색/층/페이저 표를 냈다(페이저는 가짜 콘솔이 풀에 응답하지 않아 제안 9큐가 송신 0줄 — t510 §7 "안 잰 것", 실기에서는 다를 수 있음). **실제 콘솔에는 아직 재생되지 않았다** — 비교에 쓰려면 이 기준선을 실기 콘솔에 올리는 송신이 필요하고, 그 송신은 M2 와 같은 감독 승인 절차(AC-LDRHYTHM-012 의 "승인=송신" 규칙, sha256 동일+설명 안 되는 줄 0건)를 그대로 따른다 — 이 송신 자체는 이 SPEC 의 M1~M3 범위(코드 0) 밖이다. REQ-LDRHYTHM-011·AC-LDRHYTHM-010·spec.md §5 플래그 5·plan.md §B 위험 7 의 문면을 "아직 생성되지 않았다"에서 이 상태(가짜 콘솔 생성됨, 실기 미재생)로 교정했다. t510 기준선 두 경로를 plan.md §A 입력 목록에 추가했다(M1 대본이 "지금 앱이 무엇을 하는지"와 대비할 자료 — "이유" 칸 인용 대상은 아니다). 다른 것은 손대지 않았다. REQ/AC 총량(12/12)·ID 변경 없음. |
| 2026-10-06 | **타임코드 이벤트 실기 진행을 t506 측정으로 갱신(리드 검토, 낡은 전제 1건).** REQ-LDRHYTHM-012 (b)가 "재생 효과 자체는 실기 미확인(t502 §3.1)"이라고 적었던 것이 낡았다 — t506(`.moai/reports/t506/verdict.md` §9, PR #552 머지 `e7eaf690`)이 2026-10-05 실기 콘솔에서 측정했다: Timecode 14 에 만든 `Go+` 이벤트 3개가 Seq 9 큐를 1→2→3 으로 약 1/2/3초에 진행시켰고(전환 구간이 매번 이벤트 시각을 포함, 약 0.15초 샘플링), 이벤트는 Lua 없이 명령줄로도 만들 수 있다(작은따옴표만·`cd Timecode 14.1.1.1.1`·트랙 주소는 `NO`/`CmdSubTrack`). (b)를 이 사실로 교정하면서, **앱의** 재생 계약은 지금도 timecode 모드를 거부한다는 것(`emit.py:51`)은 그대로 남겼다 — 이 M4+ 후보는 이제 "콘솔에서 이미 동작이 확인된 메커니즘에 앱을 배선하는 것"이고, 남은 미확인은 정밀도(약 0.15초 샘플 간격에 묶임)와 이벤트 수 상한뿐이다. **grep 결과**: spec.md:42(카드 본문 요약, 2026-10-05 작성 당시 t504 원문 그대로 — 리드 지시로 손대지 않음)·spec.md:53(§1 배경, 앱 계약이 지금도 timecode 를 안 쓴다는 서술 — 바뀌지 않았으므로 그대로)·plan.md §B 위험 4(같은 앱 계약 서술, 그대로)에도 "미확인"/"거부" 표현이 남아 있으나, 셋 다 이 교정 대상이 아니다(§B 위험 4·spec.md:53 은 여전히 참인 앱 계약 서술, spec.md:42 는 리드가 보존을 지시한 카드 요약). 다른 곳은 손대지 않았다. REQ/AC 총량(12/12)·ID 변경 없음. |
| 2026-10-06 | **M1 감독 통과 + REQ-LDRHYTHM-005 네 범주 교정 + M2 준비 반영(카드 t517, 같은 날 후속).** 감독이 M1 LOVE ATTACK 대본(`.moai/specs/SPEC-LDRHYTHM-001/m1-love-attack-script.md`, PR #557 머지 `6d2e87f6`)을 검토하고 원문 「통과로 진행」으로 승인했다(2026-10-06, 리드 경유 전달, 카드 t517 본문). REQ-LDRHYTHM-005 를 t514 판정서(`.moai/reports/t514/verdict.md`) §4 의 정정안대로 교정했다 — 감독 검토 지적(t514, 「Position(pan&tilt)는 조명연출 효과로 사용하지 않아?」)에 따라 대본이 이미 추가한 박자 층 네 번째 종류 "움직임 효과"를 REQ 문면에도 반영한다(원래 문면은 §3.3 REQ-LDRHYTHM-005 뒤 블록쿼트에 그대로 보존). `acceptance.md` AC-LDRHYTHM-005 도 "세 범주"→"네 범주"로 동일 교정했다(원래 문면 보존). `plan.md` M1 §E 의 박자 층 종류 나열도 같이 교정했다. M2 준비 조사(t515, `.moai/reports/t515/verdict.md`·`reports/ldrhythm-m2-mechanism-20261006.md`)의 결론 — 반복 동작(펄스·체이스·움직임)은 스피드 마스터 결속 페이저로, 장면 경계·강조는 타임코드 이벤트로, 반 박(0.267초)은 타임코드 이벤트로 낼 수 없음 — 과 M2 첫 묶음 순서(묶음 0: 0~6마디로 다섯 가지 미측정 항목 확인, 카드 t516 진행 중·보고서 미작성 → 묶음 1: 0~25마디)를 `plan.md` M2 §E 에 반영했다. 감독 작명 규칙(시퀀스·타임코드 이름 `'<곡명> - <버전>'`, 승인 파일에 이름 설정 줄 포함)을 `plan.md` §D 제약에 추가했다. `progress.md` 의 M1 미결 항목(AC-005 세 범주 문면)을 이 교정으로 해소됐다고 기록했다. REQ/AC 총량(12/12) · ID 추가삭제 없음 — 기존 REQ/AC 문면 교정 + plan.md M2 보강뿐. `status` 는 `in-progress` 로 불변(§ Non-transition frontmatter corrections — status 전이 아닌 본문 교정). |
| 2026-10-07 | **REQ-LDRHYTHM-012 GEARS shall 복원(카드 t518).** t517 정정 감사(`.moai/reports/t517/plan-audit.md` D1)가 REQ-012 행에 GEARS 키워드 `shall` 이 0건임을 발견했다 — 2026-10-05 iteration 1 D2(비요구사항 참고 각주 분리, 위 HISTORY 참조)에서 주체를 "다음 항목"으로 정리하며 그 과정에 `shall` 자체가 사라진 것으로 보인다. 첫 절("다음 항목은 M4+ 단계의 범위 후보로만 기록된다")에만 `shall` 하나를 복원했다(REQ-LDRHYTHM-011 의 주체-shall 배치와 동일한 자리) — (a)~(d) 항목·참고 각주·근거 칸은 전부 그대로다. REQ/AC 총량(12/12)·ID 변경 없음 — GEARS 문면 교정뿐. |

## §0. Tier 선택 근거

**Tier M.** 이 SPEC 자신의 M1~M3 산출물(대본·시연 로그·규칙화된 문서 교정)은 코드를 만들지 않아 Tier S 범위이지만, M4+ 로 넘어가는 순간 건드릴 파일이 4개 모듈(`song_cue_render.py`/`position_fx.py`/`movement.py`/`analyze.py`) 이상으로 퍼지고 REQ/AC 수가 Tier S 상한(각 8개)을 넘는다 — 그러나 M4+ 자체는 이 SPEC 이 지금 구현하는 범위가 아니라 **후보**(§3.6)로만 기록하므로 L 급 산출물(design.md·research.md)은 과하다. REQ 12개·AC 12개로 Tier M 상한(각 16개) 안에 든다.

## 감독 결정 (원문, 2026-10-03, 리드 경유)

> 리듬 연출 SPEC plan(SPEC-LDRHYTHM-001) — 감독 결정 2026-10-03 4건: (1) 순서 = 대본 먼저: M1 Club Diver 연출 대본(시간순 음악 순간→놓는 연출→앞 장면과 잇는 방식→이유, 코드 0) 감독 검토 → M2 대본을 손으로 콘솔 시연(쓰기는 감독 승인) → M3 감독이 어울린다 한 대본의 규칙을 표준·SPEC 으로 → M4 이후 앱 구현. M1~M3 통과 전 앱 코드 금지 (2) 첫 곡 Club Diver (3) 두 층: 박자 층 = 킥·스네어·마디마다 디머 펄스·체이스 한 칸·색/위치 한 단계를 타임코드 이벤트로(곡당 수백 개 허용), 강조 층 = 스트로브·블라인더는 큰 히트에만(표준 §10.3 유지) (4) 효과 속도 = 앱 분석 BPM 으로 스피드 마스터(At SpeedMaster 실기 확인됨), 콘솔 오디오 입력 안 씀.

> **정정(원문은 그대로 둔다) — 감독 결정, 2026-10-06, 리드 경유**: 「테스트 음악은 완성도·리듬·비트가 떨어진다. 실제 K-pop 리센느 'LOVE Attack' 으로 다시 진행, 기존 조명연출과 비교」. 이 결정은 위 (2)항("첫 곡 Club Diver")을 **대체**한다 — (1)·(3)·(4)항은 그대로 유효하며, 대상 곡만 Club Diver 에서 LOVE ATTACK 으로 바뀐다. "기존 조명연출과 비교"는 §3.6/AC-LDRHYTHM-010 에서 "같은 곡(LOVE ATTACK)의 기존 앱 연출과 나란히 비교"로 구체화했다(아래 REQ-LDRHYTHM-011 참조).

카드 본문이 추가로 적은 **앱 구현 범위 후보**(결정 4건과는 구분 — 후보일 뿐 결정 아님, §3.6 에서 다룬다): 「비트·다운비트·킥 검출(지금 BPM 만 넘김), 타임코드 이벤트 송신(재생 효과 실기 미확인), position_fx 무빙 경로 재사용, 장면 연결 규칙(한두 속성만·큰 순간 전 덜어냄·최대 연출 아끼기)」. 합격 기준은 카드 본문대로 「LOVE ATTACK 실기 감독 3점 이상, 기계 점검(순간별·연결)은 사전 체일 뿐」이다(2026-10-06 정정 반영 — 2026-10-05 작성 당시 t504 카드 원문은 Club Diver 기준이었다).

## 1. 배경 — 작동은 하는데 음악이 아니다, 두 번째 반복

t498(Rain 실기 파일럿, 0/5점)과 t501(SPEC-LDRENDER-001 송신 층 복원 뒤 재실기, AC-LDRENDER-016 **1~2/5점**, 통과선 3점)이 같은 모양의 판정을 두 번 냈다 — 기계 동작(큐 전환·되읽기·기존 쇼 보존)은 PASS, 감독 육안 판정은 FAIL. t501 sync 보고(`.moai/reports/t501/sync.md`)의 감독 판정 원문: 「작동은 한다. 그러나 Verse 하나가 20~30초 이상 단조로운 동작·연출 하나 — 리듬·비트에 따라 빠르고 다채롭게 움직여야 음악 표현이 된다.」

t502 조사(`reports/rhythm-expression-research-20261003.md`, 이하 "리듬 보고서")가 코드 판독으로 확정한 것 [잰 값]:
- Rain(시퀀스 212): 페이저 송신 **0건** — 큐 안에서 움직이는 것이 아예 없다(§0.2).
- Club Diver(시퀀스 213): 14큐 중 9큐가 같은 색 파형(Wave CM) 반복, 속도(`speed`) 줄 **0건**, 큐 안 Pan/Tilt 페이저 **0건**(§0.2 표) — `grep -ci speed` 등으로 실측, 위치는 큐 경계의 프리셋 호출로만 바뀐다.
- 곡 분석은 BPM 숫자 하나만 렌더러에 닿는다 — 비트 시각은 계산한 뒤 버리고(`server/audio/analyze.py:352-354` `librosa.beat.beat_track` 결과가 BPM 계산에만 쓰이고 `AnalysisResult`(`:207-215`)에 필드가 없음), 다운비트 생산자는 `grep -rln "downbeat" server` **0건**(이 plan-phase 에서 재확인 — `.claude/worktrees/t504`에서도 0건). 온셋(`onsets_ms`)은 `AnalysisResult`(`analyze.py:213`, `:375`)에 필드는 있으나 캐시(`analysis.json`) 저장 키는 `sha256, bpm, bpm_source, sections` 뿐으로 온셋이 저장되지 않는다(캐시 실측, `.moai/reports/t499/runs/Club Diver/analysis.json`).
- 실기 검증된 BPM 속도 무빙 페이저(`server/spatial/position_fx.py:145-177` `_relative_phaser_lines`, `speed_bpm` 인자)와 짜여 있지만 쓰이지 않는 `plan_movement`(`server/looks/movement.py:192`, 호출처는 테스트뿐 — `grep -rln "plan_movement" server` → `movement.py`, `tests/test_looks_library.py`, `tests/test_songcue_movement.py`)가 **이미 저장소에 있는데 곡 렌더러에 연결돼 있지 않다**. 곡 렌더러의 큐 묶음 생성 호출(`server/design/song_cue_render.py:1437` `SongCueSectionBundle(...)`, 이 plan-phase 에서 재확인 — 리듬 보고서가 인용한 `:1102`와 줄 번호가 다르나 동일 호출부)은 `movement` 인자를 넘기지 않는다 — 필드 기본값이 `None`이라(`server/looks/songcue.py:206-211`) 무빙 줄이 생기지 않는다. `songcue.py:210` 주석이 가리키는 `_movement_carrier` 함수는 코드에 없다(`grep -rn "_movement_carrier" server` → 주석 3곳뿐, 함수 정의 없음).
- 타임코드 재생 모드는 계약에 아직 없다 — `server/director/emit.py:51` `PLAYBACK_MODES = ("manual_go", "trig_time")`(이 plan-phase 에서 재확인), 데이터 모델(`server/design/song_plan.py:61` `TimingMode`)에는 `"timecode"` 리터럴이 있지만 재생 경계에서 쓰이지 않는다.

이 반복(두 번째 "작동은 하지만 음악이 아니다")에 대해 감독이 2026-10-03 내린 결론은 **순서를 바꾸라**는 것이다 — 규칙을 먼저 코드로 만들고 실기에서 판정받는 지금까지의 순서를 뒤집어, **대본(사람이 읽는 연출 각본)을 먼저 확정하고, 감독이 그 대본에 동의한 뒤에야 규칙화하고 코드를 쓴다**. 위 "감독 결정 (원문)" 절 (1)이 이 순서를 정의한다.

## 2. 이 SPEC 의 성격 — 대본·시연·규칙화 3단계, 앱 구현은 다음 SPEC 의 일(M4+)

이 SPEC 의 M1~M3 은 **문서와 콘솔 시연**만 다룬다 — `server/` 아래 어떤 파일도 이 SPEC 의 M1~M3 커밋에서 수정되지 않는다(REQ-002). M4(앱 구현)는 이 SPEC 의 plan-phase 가 "후보 범위"로만 적어 두고(§3.6), 착수 여부·방법은 M3 가 끝난 뒤 별도 run-phase 승인(필요하면 별도 SPEC 분리)을 받는다. 이 분리 자체가 감독 결정 1의 핵심이다 — 코드를 먼저 쓰고 실기로 검증받는 순서를 뒤집어, **감독의 눈이 코드보다 먼저 "무엇이 어울리는가"를 정한다.**

## 3. 요구사항 (GEARS)

### 3.1 R1 — 대본 우선 게이트 (REQ-LDRHYTHM-001~003)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDRHYTHM-001 | **The** 리듬 연출 작업 **shall** 다음 순서를 따른다: M1(LOVE ATTACK 연출 대본, 코드 0) → 감독 검토 → M2(대본을 손으로 콘솔 시연, 쓰기는 **구간/묶음 단위 커맨드 파일 1개를 통째로 1회** 감독 승인 — t498(`real_console.py`/`classify_diff.py`)·t501 AC-016(`.moai/reports/t501/ac016/real_song.py`/`classify_diff.py`)이 쓴 리허설→승인→바이트동일 송신 흐름과 같다, 리드 판독(2026-10-05) 반영) → M3(감독이 "어울린다"고 한 대본의 규칙을 표준 문서·SPEC 으로 옮김) → M4 이후(앱 구현, 별도 승인). 이 순서를 건너뛰거나 뒤섞지 않는다. | 감독 결정 1(원문 위), 리듬 보고서 §6 제안("코드보다 「연출 대본」을 먼저"); 승인 단위 교정: 리드 PR #550 판독 — t498/t501 AC-016 선례 |
| REQ-LDRHYTHM-002 | [HARD] **While** M1·M2·M3 중 하나라도 감독 승인을 받지 못한 상태인 동안, **어떤** 주체도 `server/` 아래 M4 후보 범위(§3.6)의 앱 코드를 작성하거나 수정하지 **shall not**. 이 게이트는 이 SPEC 자신의 run-phase 착수 시점(이 plan-phase 종료 직후)부터 즉시 적용된다 — "plan 만, run 은 감독 착수 승인 뒤"라는 카드 지시와 별개의, M1~M3 **내부** 순서 게이트다. | 감독 결정 1("M1~M3 통과 전 앱 코드 금지") |
| REQ-LDRHYTHM-003 | **When** M1 이 착수되면, 산출물 **shall** LOVE ATTACK 한 곡의 시간순 표(열: 시각 / 층 / 모멘트유형 / 연출 / 잇는 방식 / 이유 — `plan.md` M1 의 6칸 정의와 동일한 칸 이름·닫힌 어휘, plan-audit iter3 D-NEW-2 반영)이고, 코드 diff 0줄·콘솔 쓰기 커맨드 0건이다 — 리듬 보고서 §6 의 대본 예시("1:02 코러스 진입 히트 → 블라인더 한 번, 무빙 전부 위로 열기 → 프리코러스 마지막 2박을 어둡게 비워 둔 뒤 끊어서 넘김 → 2.3 규칙 3·4")와 같은 형식을 따른다. 곡의 어느 순간인지(시각)→그 순간에 무엇을 두는지(층·모멘트유형·연출)→앞 장면과 어떻게 잇는지(잇는 방식)→왜 그렇게 하는지(이유), 네 질문에 답하는 원래 구조의 의도는 그대로 유지된다. "잇는 방식" 칸은 벤치마크 보고서 §2.3(장면을 잇는 규칙 1~7)의 조항 번호를 인용하고, "이유" 칸은 §2.1(구간별로 놓는 것) 또는 §2.3 의 조항 번호를, 또는 `reports/loveattack-song-research-20261006.md`(LOVE ATTACK 곡 조사, 2026-10-06) §3(뜻과 콘셉트) 또는 §4(시각 콘셉트)를 인용한다 — 그 문서의 §6(연출 단서)은 리드의 참고 메모일 뿐 이 칸의 인용 대상이 아니다. 새 규칙을 이유 없이 발명하지 않는다. | 감독 결정 1, `reports/music-lighting-benchmark-20261003.md` §2.1·§2.3·§6, `reports/loveattack-song-research-20261006.md` §3·§4; `plan.md` M1(§E) 6칸 표 정의 |

### 3.2 R2 — 첫 곡 범위 (REQ-LDRHYTHM-004)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDRHYTHM-004 | **The** M1~M3 의 대본·시연·규칙화 작업 범위 **shall** LOVE ATTACK 한 곡으로 한정된다. 기존 8곡 데이터셋(Club Diver 포함, t499 판독 대상)과 Rain 은 전부 이 SPEC 의 범위 밖이다(§4 Out of Scope) — 원래 테스트 음악(Club Diver, 벤치마크 보고서 §6 「감독이 정할 것」 2항의 빠른 템포·분명한 구간 기준으로 선택됐던 곡)은 완성도·리듬·비트가 떨어진다는 감독 판단에 따라 실제 K-pop 곡 LOVE ATTACK 으로 교체됐다(감독 결정 2026-10-06, 위 "감독 결정" 절의 정정 참조 — 원래 감독 결정 2(2026-10-03)를 대체). 원곡 오디오는 저장소 밖에 있다(§5 플래그 4). | 감독 결정 2026-10-06(정정) — 원래 벤치마크 보고서 §6 기준(빠른 템포·분명한 구간)은 폐기, 음악 완성도 기준으로 교체 |

### 3.3 R3 — 두 층 모델: 박자 층과 강조 층 (REQ-LDRHYTHM-005~007)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDRHYTHM-005 | **The** 대본(M1)·시연(M2)·규칙화(M3) **shall** 연출을 두 층으로 나눠 기술한다. **박자 층**: 킥·스네어·마디마다 디머 펄스 1개, 체이스 한 칸 전진, 색/위치 한 단계, **움직임 효과**(무빙 Pan/Tilt 페이저 — 지금 위치를 중심으로 스피드 마스터 박 주기에 맞춰 계속 움직임) 중 하나를 타임코드 이벤트로 기록하며, 곡당 수백 개까지 허용한다(마디·박 단위 분할이지만 콘솔 큐 자체를 쪼개는 것이 아니다 — 타임코드 이벤트가 독립 레인이다, §3.4 와 구분). [범주 확장 정정 2026-10-06(t517) — 아래 블록쿼트 참조] | 감독 결정 3, 리듬 보고서 §③ 권고(원샷 레인/타임코드로 강조를 얹는 안); 네 번째 종류 추가는 `.moai/reports/t514/verdict.md` §4 |
| REQ-LDRHYTHM-006 | **The** 대본·시연·규칙화 **shall** **강조 층**(스트로브·블라인더)을 큰 히트(코러스 진입·드롭·마지막 코러스 등)에만 배치한다 — 매 박마다 번쩍이지 않는다. [문서 인용 정정 — 아래 §6 "안 잰 것/정정" 참조] 감독 결정 원문이 "표준 §10.3"으로 지칭한 조항은 표준 문서(`docs/proposals/song-structure-lighting-standard.md`)에 `§10.3`이라는 하위 번호가 없고, 실제로는 **"## 10. 아마추어로 읽히는 것" 목록의 4번 항목**(326~327행, "스트로브는 액센트여야 한다, BPM 카운터가 아니다", 권장 상한 약 4Hz)이다 — 이 REQ 는 그 조항(이하 "§10 금지목록 4번"으로 정확히 지칭)을 그대로 유지한다. | 감독 결정 3, `docs/proposals/song-structure-lighting-standard.md:326-327`(직접 대조 확인, 이 plan-phase 에서 재확인) |
| REQ-LDRHYTHM-007 | **While** 박자 층과 강조 층이 같은 큐·같은 타임코드 구간에 공존하는 동안, 대본은 **shall** 두 층을 시각적으로 구분해 적는다(예: 박자 층은 표의 "연출" 칸에 약어로, 강조 층은 별도 "강조" 칸 또는 굵게) — M3 가 규칙화할 때 두 층의 구분이 유지돼야 규칙 문서에서도 "매 박 번쩍임"과 "박자 동기 무빙"이 혼동되지 않는다. | 리듬 보고서 §④ 표("박자 표현에 스트로브·디머 번쩍임을 넣을지"는 감독이 정할 것 3항으로 남아 있었으나, 감독 결정 3이 "강조 층 = 스트로브·블라인더는 큰 히트에만"으로 **이미 답했다** — 이 REQ 는 그 답을 두 층 분리 표기로 구현한다) |

> **범주 확장 정정(원문은 그대로 둔다) — 2026-10-06, 카드 t517**: 감독이 M1 LOVE ATTACK 대본을 검토하며 「Position(pan&tilt)는 조명연출 효과로 사용하지 않아?」라고 지적했다(t514, 2026-10-06). 대본(`m1-love-attack-script.md`)은 이미 이 지적을 반영해 네 번째 박자 층 종류 "움직임 효과"를 추가했고, REQ-LDRHYTHM-005 는 그 대본과 일치하도록 교정됐다 — `acceptance.md` AC-LDRHYTHM-005·`plan.md` M1 §E 도 동일하게 교정했다(세 곳 모두 "원래 문면" 보존). **REQ-LDRHYTHM-005 원래 문면(2026-10-05)**: 「**The** 대본(M1)·시연(M2)·규칙화(M3) **shall** 연출을 두 층으로 나눠 기술한다. **박자 층**: 킥·스네어·마디마다 디머 펄스 1개, 체이스(또는 페이저) 한 칸 전진, 색/위치 한 단계 중 하나를 타임코드 이벤트로 기록하며, 곡당 수백 개까지 허용한다(마디·박 단위 분할이지만 콘솔 큐 자체를 쪼개는 것이 아니다 — 타임코드 이벤트가 독립 레인이다, §3.4 와 구분).」 근거: `.moai/reports/t514/verdict.md` §4(정정안 제안, SPEC 수정은 리드 판단으로 유보됐던 것을 이 교정으로 확정). REQ-LDRHYTHM-007 의 "박자 동기 무빙"은 이미 움직임을 박자 층으로 보고 있어 이 교정과 충돌하지 않는다(t514 §4 "추가 검토 거리").

### 3.4 R4 — 두 층과 기존 큐 밀도 규칙의 비충돌 (REQ-LDRHYTHM-008)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDRHYTHM-008 | **The** 박자 층·강조 층 도입 **shall** `docs/proposals/song-structure-lighting-standard.md` §9(큐 밀도, "발사 지점은 프레이즈 단위 4~8마디마다")와 `SPEC-LDDESIGN-001` REQ-036("마디 수로 기계적 분할을 밀도 결정 수단으로 쓰지 않는다")을 바꾸지 않는다 — 두 축은 서로 다르다: §9/REQ-036 은 **룩 전환 간격**(콘솔 큐 자체가 바뀌는 빈도)을 규율하고, 이 SPEC 의 박자 층은 **한 룩이 유지되는 동안의 움직임**(타임코드 이벤트·스피드 마스터 동기 페이저)을 규율한다. 대본·규칙화 산출물은 이 두 축이 같은 수치(예: 큐 수)를 놓고 경쟁하지 않음을 명시한다. | 리듬 보고서 §④ 표(1행: "겉보기 충돌 — 룩 전환 축과 룩 안 움직임 축은 다르다"), §3.1 큐 밀도 비교표(마디 단위 분할 시 112~448개 큐가 되어 REQ-036 위반이라는 판단 — 이 REQ 는 그 방식을 채택하지 않음을 재확인) |

### 3.5 R5 — 효과 속도 출처 (REQ-LDRHYTHM-009~010)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDRHYTHM-009 | **The** 박자 층의 효과(체이스·페이저) 속도 **shall** 앱이 분석한 곡 BPM 에서 나온 **스피드 마스터**에 결속한다(`Master 3.n At BPM <분석 BPM>` + `Attribute '<a>' At SpeedMaster <n>`) — 페이저마다 고정 `At Speed <리터럴>` 을 박는 방식(선택지 A, 리듬 보고서 §2.3)은 쓰지 않는다. `At SpeedMaster <n>` 결속 자체는 **실기 확인됨**(`.moai/specs/SPEC-COPILOT-FXGEN-001/spec.md:43` V3, 2026-08-15 onPC 2.4.2 오퍼레이터 GUI 관측 — "마스터 BPM 변경이 페이저에 실시간 반영"). **미확인으로 남는 것**: 곡 재생 중 `Master 3.n At BPM <값>` 을 큐 커맨드·매크로로 싣는 구체 방법(리듬 보고서 G9, 아래 §6) — M4+ 가 착수되면 이 확인이 선행 조건이다. | 감독 결정 4, FXGEN spec.md:43, FXLIB spec.md:64(ASSUMPTION-38 GO, Speed 단위 = BPM) |
| REQ-LDRHYTHM-010 | **The** 박자 층 **shall not** grandMA3 스피드 마스터 16번(콘솔 오디오 입력에서 자동으로 BPM 을 잡는 마스터, help.malighting.com Speed Masters 문서 "Speed master 16 is a BPM master... controlled by incoming audio")을 속도 출처로 쓴다 — 결과가 공연마다 달라 재현·감독 사전 확인이 불가능하기 때문이다(벤치마크 보고서 §4 판단). | 감독 결정 4("콘솔 오디오 입력 안 씀"), 벤치마크 보고서 §4 "판단 — 큐 100개 넘게 박자에 놓을 수 있나" |

### 3.6 R6 — 합격 기준과 M4+ 범위 후보 (REQ-LDRHYTHM-011~012)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDRHYTHM-011 | [HARD] **The** 이 SPEC 의 합격 기준 **shall** LOVE ATTACK 을 실기 콘솔에 올린 **감독 육안 판정 ≥3/5점**(AC-LDRENDER-016 과 같은 척도)이**고**, 그 판정은 **같은 곡(LOVE ATTACK)의 기존 앱 연출과 나란히** 이루어져야 한다(같은 콘솔에서 기존 앱 연출을 먼저 재생해 감독이 점수를 매기고, 이어서 M1~M3 데모를 재생해 감독이 점수를 매긴다 — 기존 쪽에는 통과 기준이 없고 비교 결과만 기록한다). "기존 앱 연출"은 **t510 기준선**(`reports/loveattack-baseline-20261006.md`, `.moai/reports/t510/verdict.md`)으로 생성돼 있다 — 단 가짜 콘솔에만 나갔고(11큐·190줄), **실제 콘솔에는 아직 재생되지 않았다**. 비교를 위해 그 기준선을 실기 콘솔에 올리는 일은 M2 의 감독 승인 송신(AC-LDRHYTHM-012 의 승인=송신 규칙과 동일)으로 처리한다(§5 플래그 5). 오프라인 기계 점검(순간별 판정 — 구간마다 벤치마크 §2.1 처리와 일치하는지, 연결 판정 — §2.3 규칙 준수 여부, 리듬 보고서 §⑤ R1~R4 류 지표)은 **사전 체(pre-filter)일 뿐**이다 — 기계 점검 전부 PASS 가 이 SPEC 의 완료를 의미하지 **않는다**. t501(AC-LDRENDER-016, 기계 판정 8곡 전부 PASS 인데 실기 1~2점 FAIL)이 바로 이 구분이 왜 필요한지의 증거다. | 카드 완료 조건(원래 "Club Diver 실기 감독 3점 이상, 기계 점검은 사전 체일 뿐")을 감독 결정 2026-10-06(정정 — 대상 곡 LOVE ATTACK + 기존 앱 연출과 나란히 비교)으로 교정, `.moai/reports/t501/sync.md`(AC-016 FAIL 1~2점), 리듬 보고서 §3("곡 전체 판정: 감독이 실기에서 본다. 기계로 대체하지 않는다") |
| REQ-LDRHYTHM-012 | **The** 다음 항목은 M4+(앱 구현) 단계의 **범위 후보**로만 **shall** 기록된다 — M3(규칙화)가 LOVE ATTACK 대본·시연에서 실제로 필요하다고 확인한 항목만 M4+ 가 채택한다: (a) 비트·다운비트·킥 검출 — 지금은 BPM 숫자 하나만 렌더러에 닿는다(§1 인용, `analyze.py` 비트 시각 미저장·다운비트 생산자 0건, 이 plan-phase 재확인), (b) 타임코드 이벤트 송신 — 문법은 있으나(`song_plan.py:61` `TimingMode`) **앱의** 재생 경계에서는 지금도 거부된다(`emit.py:51`). **콘솔 자체**에서는 실기로 진행이 확인됐다(`.moai/reports/t506/verdict.md` §9, 2026-10-05 실기 측정, PR #552 머지 `e7eaf690`) — Timecode 14 에 만든 `Go+` 이벤트 3개가 Seq 9 큐를 1→2→3 으로 약 1/2/3초에 진행시켰고(전환 구간이 매번 이벤트 시각을 포함, 약 0.15초 샘플링), 그 이벤트는 Lua 없이 명령줄로도 만들 수 있다(작은따옴표만·`cd Timecode 14.1.1.1.1`·트랙 주소는 `NO`/`CmdSubTrack`). 이 M4+ 후보는 이제 "콘솔에서 이미 동작이 확인된 메커니즘에 앱을 배선하는 것"이고, 남은 미확인은 정밀도(약 0.15초 샘플 간격에 묶임)와 이벤트 수 상한이다, (c) `position_fx`/`plan_movement` 무빙 경로를 곡 렌더러에 연결 — 실기 검증된 코드가 이미 있으나 연결이 안 돼 있다(§1 인용), (d) 장면 연결 규칙(한두 속성만 변경·큰 순간 전 덜어냄·최대 연출 아끼기, 벤치마크 §2.3)을 송신기 레벨 검사로 승격. *(참고 — 비요구사항 설명, plan-audit iter1 D2 분리: 이 plan-phase 자신은 네 항목 중 무엇을 실제로 구현할지 확정하지 않는다. 지금 쓰는 것은 "카드가 제시한 후보"이며 "이미 확정된 작업"이 아니다 — 각 항목이 실제로 M4+ 의 REQ 가 될지는 M3 종료 후 재확인한다.)* | 카드 본문("앱 구현 범위 후보"), 리듬 보고서 §1/§2.1/§3.1/빈칸 표(G1·G4·G5·G6·G8·G9) |

## 4. 제외 범위 (Out of Scope)

### Out of Scope — M4+ 앱 구현 자체

REQ-002 가 명시하듯, M1~M3 통과 전에는 어떤 앱 코드도 이 SPEC 의 작업이 아니다. §3.6 의 후보 목록은 "무엇을 적을지"의 기록일 뿐, 이 plan-phase 가 그 구현을 승인하지 않는다.

- `server/audio/analyze.py`(다운비트·킥 검출 추가), `server/design/song_cue_render.py`(움직임 배선), `server/spatial/position_fx.py`/`server/looks/movement.py`(곡 렌더러 연결), `server/director/emit.py`(타임코드 재생 모드 개방) — 전부 M4+ 로 이월.

### Out of Scope — LOVE ATTACK 이외의 곡

Rain·Club Diver 를 포함한 기존 8곡(t499 판독 대상) 전체의 대본·시연·규칙화는 이 SPEC 의 범위 밖이다(REQ-004) — Club Diver 는 원래 M1~M3 대상이었으나 감독 결정(2026-10-06)으로 LOVE ATTACK 으로 교체됐다. Rain 의 "페이저 0건" 결함(§1 인용)은 후속 SPEC/카드의 몫이다.

- Rain 및 기존 8곡(Club Diver 포함)의 연출 대본 작성, 해당 곡들의 콘솔 시연.

### Out of Scope — §9 큐 밀도·REQ-036 재협상

REQ-008 이 명시하듯 이 SPEC 은 룩 전환 빈도(§9) 수치를 올리거나 REQ-036 의 "마디 수 기계적 분할 금지"를 재해석하지 않는다. 박자 층은 그 축과 다른 축이다.

- `docs/proposals/song-structure-lighting-standard.md` §9 수치 변경, `SPEC-LDDESIGN-001` REQ-036 재작성.

### Out of Scope — SPEC-LDRENDER-001 이월 항목(R5/R6)

구간 역할별 디머 대역 재산정(R5)과 후렴 상승 사다리·드롭 앞 암전(R6)은 SPEC-LDRENDER-001 §4 가 이미 후속 SPEC 으로 분리해 둔 항목이다. 이 SPEC 은 그 분리를 재론하지 않는다.

- `_dimmer_data`/`_D_LEVEL_ROWS` 로직 변경, 연속 후렴 상승 사다리·눈 리셋 암전 큐 로직.

### Out of Scope — 콘솔 쓰기(이 plan-phase 자신)

이 문서를 작성하는 plan-phase 자신은 콘솔에 어떤 커맨드도 보내지 않는다. M2(손 시연)의 콘솔 쓰기는 이 SPEC 의 run-phase 이후, 구간/묶음 단위 커맨드 파일 1개를 통째로 1회 감독 승인받는 별도 활동이다(REQ-001).

- 이 plan-phase 세션의 콘솔 접촉(조회·쓰기 모두 포함).

## 5. 열린 결정 — 전부 해소(0건), 잔여 플래그만 기록

2026-10-03 감독 결정 4건으로 열린 결정은 없다. 다만 아래는 "결정은 났으나 구현 전 재확인이 필요한" 잔여 플래그다(발명하지 않고 명시만 함):

1. **§10.3 인용 불일치**(REQ-006 각주) — 감독 결정 원문이 가리킨 "표준 §10.3"은 실제로 "## 10." 목록의 4번 항목이다. 조항의 **의미**(스트로브는 액센트, BPM 카운터 아님)는 그대로 유지되므로 재결정 사항이 아니지만, M3 가 표준 문서를 교정할 때 이 호칭을 정확한 위치로 고쳐야 한다.
2. **G9 — `Master 3.n At BPM` 을 곡 재생 중 싣는 방법 미확인**(REQ-009) — M4+ 가 스피드 마스터 경로를 실제로 구현하기 전에 공식 문서(큐 Command 열) 또는 실기로 확인이 필요하다.
3. **G5 — Rain 분석 BPM(76.01)의 절반/두 배 오검출 가능성**(§1 인용, 리듬 보고서 §①) — Club Diver 자체의 BPM(139.67, `measured` 소스)은 이번 조사에서 의심 후보로 지목되지 않았으나, M4+ 가 다른 곡으로 확장될 때 참값 대조가 필요하다.
4. **LOVE ATTACK 원곡 오디오 위치(저장소 밖, 의도적 미커밋)** — 감독 결정(2026-10-06) 이후 실측: `/Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3`(4,733,524바이트, sha256 `9ab52dfb8ac5bd8a0dc09d393b33e28ad650c07262371460994300c98581c9fa`, 2026-10-06 `ls -l`+`shasum -a 256`로 이 plan-phase 에서 직접 재실측)에 있다. 기존 8곡(Club Diver 등)이 있는 `src/sample music/`(주 체크아웃) 안에는 **의도적으로** 두지 않는다 — M1 의 BPM·구간 분석 스크립트는 이 저장소 밖 경로를 직접 참조해야 하고, 그 경로가 다른 머신에서 재현되지 않을 수 있음을 M1·M2 산출물에 명시한다.
5. **"기존 앱 연출"(AC-LDRHYTHM-010 비교 대상)은 t510 기준선으로 가짜 콘솔까지는 생성됐으나, 실제 콘솔에는 아직 재생되지 않았다.** `reports/loveattack-baseline-20261006.md`(+`.html`)와 `.moai/reports/t510/verdict.md`(카드 t510, 2026-10-06)가 LOVE ATTACK 을 현재 렌더러(SPEC-LDRENDER-001 완료 상태)로 돌린 결과다 — 11큐, 가짜 콘솔(FakeConsole) 송신 190줄, 큐별 유지·색·층·페이저 표가 있다. 가짜 콘솔은 페이저 풀에 답하지 않아 페이저 제안 9큐가 송신 0줄로 나왔다는 한계가 명시돼 있다(실기에서는 0이 아닐 수 있음). 이 기준선을 실제 콘솔에 올려 AC-LDRHYTHM-010 의 비교에 쓰려면, M2 와 같은 감독 승인 송신(AC-LDRHYTHM-012 의 승인=송신 규칙)이 선행 조건이다 — 이 송신 작업 자체는 이 SPEC 의 M1~M3 범위(코드 0) 밖이며, AC-LDRHYTHM-010 의 Given 절 선행 조건으로만 명시한다.
