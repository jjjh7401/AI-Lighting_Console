# SPEC-LDRHYTHM-001 — 구현 계획

## §A 맥락

- **입력**: `reports/music-lighting-benchmark-20261003.md`(벤치마크+콘솔 조사, 팩토리 리드) · `reports/rhythm-expression-research-20261003.md`(t502, 코드 판독+빈칸 표) · `.moai/reports/t502/verdict.md` · `.moai/reports/t501/sync.md`(SPEC-LDRENDER-001 AC-LDRENDER-016 FAIL 1~2점) · `docs/proposals/song-structure-lighting-standard.md` · 감독 결정 4건(2026-10-03, 리드 경유) · `reports/loveattack-song-research-20261006.md`(LOVE ATTACK 곡 조사 — 발매정보·음악적 특징·뜻과 콘셉트 §3·시각 콘셉트 §4·연출 단서 §6, 2026-10-06 리드 조사, sha256 확인) — §3·§4 는 M1 "이유" 칸의 추가 인용 대상(아래 M1 참조). §6 은 리드의 참고 메모일 뿐 기계 검사 인용 대상이 아니며, §6 단서 5(비트 드롭→강조 층 후보)는 감독 결정 3(큰 히트에만)의 범위 안이다 — 강조 층 규칙(REQ-006/AC-006)을 넓히지 않는다 · 감독 결정(2026-10-06, 리드 경유 — 첫 곡을 Club Diver 에서 LOVE ATTACK 으로 교체).
- **전제 SPEC**: SPEC-LDRENDER-001(status: implemented — M1~M7 구현 완료, AC-016 사람 판정만 미달), SPEC-LDDESIGN-001(completed), SPEC-COPILOT-FXGEN-001/FXLIB-001(completed — `At SpeedMaster` 결속·BPM 단위 확정 실측의 출처).
- **범위**: M1~M3 는 `docs/proposals/song-structure-lighting-standard.md`(§2.1·§2.3·"## 10." 인용만, 교정은 M3 범위) 와 이 SPEC 자신의 문서 산출물(대본 파일)만 다룬다. **`server/` 아래 코드는 이 SPEC 의 M1~M3 커밋에서 전혀 수정하지 않는다**(REQ-002). M4+(§E 하단)는 범위 후보 기록일 뿐 착수 대상이 아니다.
- **진입 조건**: 이 plan-phase 종료 후 Implementation Kickoff Approval(감독 착수 승인) — 카드 지시("plan 만 — run 은 감독 착수 승인 뒤")가 이 SPEC 의 run-phase 진입 자체를 그 승인에 묶는다. run-phase 진입 후에도 REQ-002 의 내부 게이트(M1~M3 각각의 감독 승인)가 별도로 적용된다.

## §B 알려진 위험 (manager-develop 착수 전 필독)

1. **M1~M3 는 "코드 없음"이 아니라 "이 SPEC 의 M1~M3 가 코드 없음"이다.** run-phase 가 착수되더라도 REQ-002 의 게이트는 M3 감독 승인 전까지 `server/` 변경을 금지한다 — "run-phase 진입 승인"과 "M1~M3 내부 게이트 통과"는 서로 다른 승인이다. 둘을 혼동해 M1 착수 승인만으로 M4 코드를 쓰기 시작하면 REQ-002 위반이다.
2. **"§10.3"은 존재하지 않는 조항 번호다.** spec.md §5 플래그 1 참조 — 감독 결정 원문의 "표준 §10.3 유지"는 실제로 `docs/proposals/song-structure-lighting-standard.md`의 "## 10. 아마추어로 읽히는 것" 목록 4번(326~327행)을 가리킨다. M1 대본이 이 조항을 인용할 때는 정확한 위치("§10 금지목록 4번")로 적어야 한다 — 감독에게 "§10.3"이라고 보고하면 존재하지 않는 조항을 인용하는 꼴이 된다.
3. **"박자 층"이 §9/REQ-036 을 재해석하는 것으로 오인되기 쉽다.** §9(큐 밀도, 4~8마디 발사)와 REQ-036(마디 수 기계적 분할 금지)은 **룩 전환 빈도** 축이고, 박자 층은 **룩 유지 중 움직임** 축이다 — 서로 다른 수치 체계다(REQ-LDRHYTHM-008). M1 대본을 쓸 때 "박자 층 이벤트 수"를 §9 의 "큐 수"로 혼동해 세지 않는다.
4. **박자 층의 "타임코드 이벤트"는 지금 콘솔 계약이 지원하지 않는다.** `server/director/emit.py:51` `PLAYBACK_MODES = ("manual_go", "trig_time")` — timecode 모드는 재생 경계에서 거부된다. M1(대본, 코드 0)과 M2(손 시연)는 이 제약 **아래에서** 진행한다 — M2 의 손 시연은 사람이 콘솔 GUI 에서 직접 타임코드/큐를 조작하는 것이지, 앱이 timecode 모드로 재생하는 것이 아니다. 이 제약을 M4+ 가 풀지 여부는 §3.6 후보 (b)의 몫이다.
5. **G9(스피드 마스터 BPM 설정을 곡 재생 중 싣는 방법)는 M4+ 선행 조건이지 M1~M3 의 몫이 아니다.** M2 손 시연에서 효과 속도를 보여줄 때는 감독이 지켜보는 자리에서 사람이 직접 `Master 3.1 At BPM <값>`을 쳐서 보여주는 것으로 충분하다 — 그 명령을 **곡 재생 중 자동으로** 싣는 방법은 아직 미확인이며 M4+ 가 확인할 과제다.
6. **LOVE ATTACK 원곡 오디오는 저장소 밖에 있다(의도적 미커밋).** 경로 `/Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3`(4,733,524바이트, sha256 `9ab52dfb8ac5bd8a0dc09d393b33e28ad650c07262371460994300c98581c9fa`, 2026-10-06 `ls -l`+`shasum -a 256`로 이 plan-phase 에서 직접 재실측) — 기존 8곡(Club Diver 등)이 있는 `src/sample music/`(주 체크아웃)에는 없고 앞으로도 커밋하지 않는다. M1 의 BPM·구간 분석은 이 저장소 밖 경로를 직접 참조한다 — 다른 머신에서 재현되지 않을 수 있음을 M1·M2 스크립트/산출물 어디서나 명시한다.
7. **"기존 앱 연출"(AC-LDRHYTHM-010 비교 대상)이 LOVE ATTACK 에 대해 아직 생성되지 않았다.** M3 완료 후 실기 판정 전에, LOVE ATTACK 을 현재 렌더러(SPEC-LDRENDER-001 완료 상태)로 돌린 출력을 먼저 생성해야 AC-LDRHYTHM-010 의 "기존 앱 연출과 나란히 비교"를 진행할 수 있다 — 이 생성 작업 자체는 이 SPEC 의 M1~M3 범위(코드 0) 밖이다.

## §C 사전 점검 (M1 착수 직전)

```bash
git branch --show-current
git rev-parse HEAD
# 표준 문서 §10 목록·§9 수치 베이스라인 확인(M3 교정 전 원문 보존용)
sed -n '299,333p' docs/proposals/song-structure-lighting-standard.md
# LOVE ATTACK 원곡 오디오 존재 확인(저장소 밖, 의도적 미커밋 — §B 위험 6)
ls -l "/Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3"
shasum -a 256 "/Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3"
# 분석 캐시 존재 확인(대본의 BPM 근거) — 아직 없을 수 있음, 없으면 오디오로 analyze 재실행
ls .moai/reports/t499/runs/"LOVE ATTACK"/ 2>/dev/null || echo "분석 캐시 없음 — analyze 실행 필요"
# M1~M3 게이트 동안 server/ 무변경을 사후 검증할 기준선
git log -1 --oneline -- server/
```

## §D 제약 (위반 금지)

- **PRESERVE**: `server/**`(M1~M3 전체 — REQ-002, byte-diff 0) · `docs/proposals/song-structure-lighting-standard.md`(M1·M2 동안 읽기만, 교정은 M3 의 명시된 범위로만 한정) · `.moai/specs/SPEC-LDRENDER-001/**`(이 SPEC 이 M1~M3 중 수정하지 않음).
- M1 대본 산출물은 **코드 블록이 아니라 표/산문**이어야 한다 — 코드 스니펫으로 "연출 의도"를 적지 않는다(코드 0 원칙, REQ-003).
- M2 손 시연의 콘솔 쓰기는 **구간(또는 묶음) 단위 커맨드 파일 1개를 통째로 1회** 감독 승인받는다(REQ-001, 리드 PR #550 판독 반영) — t498(`real_console.py`/`classify_diff.py`)·t501 AC-016(`.moai/reports/t501/ac016/real_song.py`/`classify_diff.py`)이 쓴 흐름과 같다: 가짜 콘솔로 리허설 → 감독이 그 파일을 승인 → **승인받은 파일과 실제로 보낸 파일이 바이트 동일**한지 확인(classify/diff) → 송신. 승인 단위는 **파일**이지 **줄**이 아니다 — 그러나 승인 없이 쓰기가 나가는 일, 또는 승인받은 파일과 다른 내용이 나가는 일은 여전히 금지한다(SPEC-LDRENDER-001 §D 의 단일 관문 선례와 같은 신중함).
- M3 가 교정하는 표준 문서 범위는 M1 대본이 실제로 인용한 조항(§2.1·§2.3·"§10 금지목록 4번"의 정확한 번호 표기)으로 한정한다 — 다른 절을 손대지 않는다.
- §10.3 오표기를 M1~M3 어느 산출물에도 그대로 옮기지 않는다 — §B 위험 2 참조, 반드시 "§10 금지목록 4번"으로 정정해 인용한다.
- **M1 산출물 경로는 `.moai/specs/SPEC-LDRHYTHM-001/m1-love-attack-script.md` 하나로 고정한다**(plan-auditor iter1 D1 반영, 2026-10-06 곡 교체로 경로명도 `m1-club-diver-script.md`→`m1-love-attack-script.md`로 교정) — AC-LDRHYTHM-006 의 오표기 검사와 "§10 금지목록 4번" 인용 검사가 이 경로만을 스캔하므로, 다른 파일명으로 산출물을 쓰면 그 AC 가 아무것도 검사하지 못한 채 통과하는 거짓 PASS 가 된다.
- **M2 의 첫 콘솔 송신 전에 AC-LDRHYTHM-012(승인본=송신본 sha256 동일 + 설명 안 되는 줄 0건)의 측정 도구가 준비돼 있어야 한다** — 지금은 준비돼 있지 않다(`.moai/reports/t498/classify_diff.py`는 "리허설 대 실기" 비교 도구이고, "승인 대 송신" 비교 도구가 아니다). 그 전까지는 M2 의 콘솔 쓰기 커맨드를 발화하지 않는다.

## §E 마일스톤 (결정 번복 비용 순 — 감독 판단이 가장 크게 바뀔 수 있는 대본 작업이 먼저, 규칙화·문서 교정은 뒤로)

### M1 — LOVE ATTACK 연출 대본 (REQ-LDRHYTHM-003, 005, 006, 007)

가장 되돌리기 비싼 축 — 감독이 대본 자체를 통째로 고칠 수 있다(코드가 없으므로 되돌리기 비용은 "다시 쓰기"뿐이지만, 이 단계의 **판단**이 뒤의 M2·M3·M4+ 전부를 좌우한다).

- **선행 조건**: LOVE ATTACK 원곡 오디오(§B 위험 6 — 저장소 밖 `/Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3`)의 BPM·구간 분석이 먼저 돼 있어야 시각(타임스탬프) 칸을 채울 수 있다.
- LOVE ATTACK 한 곡 전체를 시간순으로, 다음 **6칸 표**로 적는다(plan-audit iter2 D-NEW-1 — "큰 히트에만"이라는 배치 조건을 기계로 셀 수 있게 하기 위한 고정 형식): **시각**(타임스탬프) · **층**(닫힌 어휘, 정확히 `박자` 또는 `강조` 둘 중 하나만) · **모멘트유형**(닫힌 어휘, `코러스진입`/`드롭`/`마지막코러스`/`기타` 중 하나만) · **연출** · **잇는 방식**(벤치마크 §2.3 규칙 번호 인용) · **이유**(벤치마크 §2.1 또는 §2.3, 또는 `reports/loveattack-song-research-20261006.md` §3〈뜻과 콘셉트〉·§4〈시각 콘셉트〉 인용 — §6〈연출 단서〉는 리드의 참고 메모일 뿐 이 칸의 인용 대상이 아니다).
- **참고(비채택, 재사용 금지)**: 브랜치 `origin/WT-rhythm-m1`(PR #553, 미머지)에 Club Diver 대상으로 작성된 같은 형식의 대본 초안(`m1-club-diver-script.md`, t507 카드)이 있다 — 6칸 표 형식·강조 배치 방법의 작성 참고로만 보고, 내용(시각·이벤트·곡 특성)은 Club Diver 전용이라 LOVE ATTACK 에 그대로 옮기지 않는다.
- **닫힌 어휘 규칙**: 층=강조인 모든 행은 모멘트유형이 `코러스진입`/`드롭`/`마지막코러스` 세 값 중 하나여야 한다 — `기타`를 포함한 그 밖의 값이 하나라도 있으면 AC-LDRHYTHM-006 위반이다(REQ-006). 모멘트유형은 자유 서술이 아니라 이 네 값 중 하나로만 쓴다 — 그 외 음악적 순간(벌스·브릿지·브레이크다운 등)은 전부 `기타`로 통일하고, 구체 서술은 "연출"·"이유" 칸에 적는다.
- **라벨의 진실성은 기계 검사의 몫이 아니다** — 모멘트유형 값이 닫힌 어휘 중 하나인지는 AC-LDRHYTHM-006 이 기계로 세지만, 그 라벨이 실제로 맞는지(이 순간이 정말 "큰 히트"인지)는 M1 감독 검토가 사람 눈으로 확인한다(REQ-LDRHYTHM-011 — 기계 점검은 사전 체일 뿐).
- 박자 층 항목에는 "킥/스네어 펄스", "체이스 한 칸", "색/위치 한 단계" 중 어느 것인지 명시한다(REQ-005).
- 강조 층 항목(스트로브·블라인더)은 큰 히트에만 배치하고, 그 근거로 "§10 금지목록 4번"(정확한 표기, §B 위험 2)을 "이유" 칸에 인용한다(REQ-006).
- 코드 diff 0줄, 콘솔 커맨드 0건임을 커밋 메시지·progress.md 에 명시한다.
- 산출물: `.moai/specs/SPEC-LDRHYTHM-001/m1-love-attack-script.md`(이 경로가 M1 의 유일한 공식 산출물 파일이다 — AC-LDRHYTHM-006 의 측정 스코프가 이 경로 하나로 고정된다, §D 제약 참조).

### M2 — 대본 손 시연 (REQ-LDRHYTHM-004)

M1 대본이 감독 검토를 통과한 뒤에만 착수한다. 되돌리기 비용은 M1 보다 낮다(대본은 고정, 시연 방식만 조정) — 그러나 콘솔 쓰기가 처음 발생하는 단계이므로 승인 절차가 엄격하다.

- **M2 착수(콘솔 첫 송신) 전 게이트**: AC-LDRHYTHM-012(승인본=송신본 sha256 동일 + 설명 안 되는 줄 0건)의 측정 도구(승인-대-송신 비교 스크립트)가 준비돼 있어야 한다 — 지금은 준비돼 있지 않다(§D 제약 참조). 준비 전에는 첫 `Store`/`Go` 커맨드를 발화하지 않는다.
- 대본을 구간(또는 묶음) 단위 커맨드 파일로 묶어 가짜 콘솔에 리허설한다(t498 `real_console.py`·t501 AC-016 `real_song.py`와 같은 리허설 흐름). 그 파일 하나를 통째로 감독에게 보여주고 승인받은 뒤에만 `Store`/`Go` 등 쓰기 커맨드를 발화한다 — 승인은 파일 단위 1회이며, 승인받은 파일과 실제로 보낸 파일이 바이트 동일한지 확인한다(AC-LDRHYTHM-012, 위 게이트 참조).
- 시연 로그는 **묶음(배치) 단위**로 기록한다(어느 파일을 언제 승인·송신했는지). 그 묶음이 실기에서 재생된 뒤, 감독이 결과를 보고 대본의 각 줄에 「어울림/아님」을 표시한다 — 승인은 파일 단위(사전)지만, M3 가 쓰는 **줄 단위 증거**는 이 사후 표시에서 나온다.
- 효과 속도(박자 층)는 사람이 직접 `Master 3.n At BPM <LOVE ATTACK 분석 BPM>` 을 쳐서 보여준다(§B 위험 5 — 자동화는 M4+ 의 몫).

### M3 — 규칙화: 표준 문서 + SPEC 갱신 (REQ-LDRHYTHM-001, 008)

M2 에서 감독이 "어울린다"고 확인한 대본 줄들의 **공통 규칙**을 문서로 승격한다. 되돌리기 비용이 가장 낮다 — 이미 감독이 승인한 내용을 옮겨 적는 작업이다.

- `docs/proposals/song-structure-lighting-standard.md` 교정 범위는 M1 이 인용한 조항의 정정(§10.3 → "§10 금지목록 4번" 같은 정확한 표기)과, M2 가 확인한 새 규칙(박자 층/강조 층 구분이 §2.1·§2.3 과 어떻게 결합하는지)의 추가로 한정한다. §9/REQ-036 수치는 건드리지 않는다(REQ-008, §D 제약).
- SPEC-LDRHYTHM-001 자신의 HISTORY 에 M3 완료와 그 규칙의 요지를 기록한다(새 REQ ID 추가 없이, 기존 REQ 의 완료 상태만 갱신 — Tier M 상한을 넘기지 않는다).
- M4+ 범위 후보(§3.6)를 M3 종료 시점의 실제 필요에 맞춰 재확인 — 대본·시연에서 쓰이지 않은 후보는 M4+ 에서 제외하거나 재설계 대상으로 플래그한다.

### M4+ — 앱 구현 (범위 후보만 기록, 이 SPEC 의 착수 대상 아님)

§3.6(REQ-LDRHYTHM-012)의 네 후보(비트/다운비트/킥 검출, 타임코드 이벤트 송신, position_fx/plan_movement 연결, 장면 연결 규칙 승격)는 M3 종료 후 별도 승인(또는 별도 SPEC)으로 다룬다. 이 plan.md 는 그 구현 순서·방법을 정하지 않는다 — M3 가 실제로 확인한 필요만 다음 단계의 입력이 된다.

## §F 안티패턴

- **M1 대본을 코드 스니펫으로 쓰지 마라** — 대본은 사람이 읽는 표/산문이다. 코드가 섞이면 "코드 0"의 의미가 흐려진다.
- **"§10.3"을 그대로 복사해 인용하지 마라** — §B 위험 2. 정확한 위치("## 10." 목록 4번)로 고쳐 쓴다.
- **M2 손 시연에서 승인 없이 파일을 보내지 마라, 또는 승인받은 파일과 다른 내용을 보내지 마라** — 승인 단위는 구간(또는 묶음) 커맨드 파일 1개이지만, 그 승인 자체를 생략하거나 승인 후 파일을 고쳐서 보내면 감독 결정 1의 핵심(코드를 먼저 쓰고 나중에 평가받는 옛 순서로 되돌아가는 것)이 깨진다 — 바이트 동일성 확인(classify/diff, t498·t501 AC-016 선례)이 이 안티패턴을 막는 기계적 장치다.
- **§9/REQ-036 수치를 "박자 층이 생겼으니"라는 이유로 올리지 마라** — 두 축은 다르다(REQ-008).
- **M3 에서 M4+ 후보를 전부 확정 REQ 로 승격하지 마라** — M2 가 실제로 확인한 것만 다음 단계 입력이다. 확인되지 않은 후보를 발명으로 메우지 않는다.
- **M2 를 AC-LDRHYTHM-012 측정 도구 없이 시작하지 마라** — 지금 있는 `classify_diff.py`는 "승인 대 송신" 비교 도구가 아니다(§D 제약). 없는 도구를 있다고 가정하고 송신하지 않는다.
- **"이유" 칸에 `reports/loveattack-song-research-20261006.md` §6(연출 단서)을 직접 인용하지 마라** — §6 은 리드가 §1~§5 를 읽고 미리 걸러 낸 참고 메모이지 인용 대상 원문이 아니다. 인용 대상은 §3·§4 뿐이다(§A 입력 참조).

## §G 교차 참조

- `reports/music-lighting-benchmark-20261003.md` §2.1(구간별로 놓는 것)·§2.3(장면을 잇는 규칙)·§6(제안 — 대본 먼저).
- `reports/rhythm-expression-research-20261003.md` §①~⑤(현재 구현과의 차이, 선택지 비교, 측정 가능한 합격 기준 초안 — 감독 확정 대기였던 R1~R6 중 일부는 이 SPEC 의 REQ-011/012 에 반영).
- `docs/proposals/song-structure-lighting-standard.md` §9(큐 밀도)·"## 10."(금지 목록, 4번 항목).
- `.moai/specs/SPEC-LDRENDER-001/spec.md`·`sync.md`(AC-LDRENDER-016 FAIL 1~2점 — 이 SPEC 의 R6 합격 기준이 같은 척도를 재사용하는 이유).
- `.moai/specs/SPEC-COPILOT-FXGEN-001/spec.md` V3(`At SpeedMaster` 실기 확인) · `.moai/specs/SPEC-COPILOT-FXLIB-001/spec.md` ASSUMPTION-38(Speed 단위 BPM 확정) — REQ-LDRHYTHM-009 의 실기 근거.
- `reports/loveattack-song-research-20261006.md` §3(뜻과 콘셉트)·§4(시각 콘셉트) — M1 "이유" 칸의 추가 인용 대상. §6(연출 단서)은 인용 대상이 아니다(§A 입력·§F 안티패턴).
- `.moai/reports/t507/verdict.md` §5(브랜치 `origin/WT-rhythm-m1`) — AC-LDRHYTHM-012 제안 원문. `.moai/reports/t498/classify_diff.py` — "리허설 대 실기" 비교 도구(§D 제약, AC-012 가 요구하는 "승인 대 송신" 비교 도구가 아님).
- 브랜치 `origin/WT-rhythm-m1`(PR #553, 미머지) `m1-club-diver-script.md`(t507) — M1 6칸 표 형식·강조 배치의 작성 참고(비채택, §E M1 참조).
