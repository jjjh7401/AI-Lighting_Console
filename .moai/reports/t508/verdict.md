# t508 판정서 — SPEC-LDRHYTHM-001 첫 곡 변경 + M2 착수 전 AC

- 카드: t508 · 브랜치: `WT-rhythm-song` · 기준: `origin/main` `e7eaf690`, 작업 중 `15345084`(t510) 를 병합
- 범위: plan 문서만. `git diff --stat 15345084 HEAD -- server/` → 빈 출력. 콘솔 접촉 0
- 커밋: `5ca2b101`(첫 곡 교체 + AC-012 + 조사 문서 반입) · `46ec621e`(origin/main 병합) · `1ad5fc50`(비교 기준을 t510 기준선으로) · 이 판정서 커밋(progress.md 기록 정리 포함)

## 1. 카드 지시별 판정

| 지시 | 상태 | 근거 |
|---|---|---|
| 첫 곡 Club Diver → LOVE ATTACK (REQ-004·AC-004·감독 결정 2) | 충족 | 살아 있는 REQ/AC/plan 줄은 전부 LOVE ATTACK. 남은 "Club Diver" 는 10-03 원문 인용·HISTORY·정정 메모·범위 밖 선언·참고 자료 언급뿐(감사 4차가 하나씩 분류) |
| 원래 결정 원문은 지우지 말고 정정 메모 | 충족 | spec.md 10-03 인용 블록 그대로(감사 4차가 origin/main 본과 대조). 10-06 결정 원문은 정정 메모 + HISTORY |
| 합격 = LOVE ATTACK 실기 감독 ≥3점 + 기존 앱 연출과 나란히 비교 | 충족 | AC-010. 비교 대상 = t510 기준선(`reports/loveattack-baseline-20261006.md`) |
| M2 착수 전 AC 추가(승인본=송신본) | 충족, 측정 도구는 준비물 | AC-012 — sha256 동일 · 승인 안 된 송신 줄 0 · 송신 안 된 승인 줄 0 · 양성 대조(`Delete Sequence 14` 주입 → FAIL). REQ-001 에 트레이스 |
| M1 경로 `m1-love-attack-script.md` | 충족 | plan.md M1 · AC-003 · AC-006 측정 줄 |
| Club Diver 대본(PR #553)은 참고 자료로만 | 충족 | plan.md 참고 자료 메모 1곳 |

## 2. 잰 것

| 명령 | 출력 |
|---|---|
| `ls -l` · `shasum -a 256` `/Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3` | 4,733,524 바이트 · `9ab52dfb8ac5bd8a0dc09d393b33e28ad650c07262371460994300c98581c9fa` (리드 값과 같음, 저장소 밖 보관) |
| `shasum -a 256` 조사 문서 원본·사본 | 둘 다 `9f136b05abc35d566bdc617f42e47415f92c814fb38e1cc3ede4bc1282871a9b` (원본은 주 체크아웃에 그대로) |
| `grep -n "UNEXPLAINED\|MISSING" .moai/reports/t498/classify_diff.py` | 49·55행 `UNEXPLAINED rehearsal-only` / `real-only` 뿐 — **MISSING 출력 없음**, 리허설↔실기 비교 도구 |
| `moai spec lint spec.md` | No findings (manager-spec 실행 보고, 감사 4차 재확인) |

## 3. plan 감사

- t508 정정 감사(1회): **PASS 0.96** (Tier M 통과선 0.80). 보고서 `.moai/reports/plan-audit/SPEC-LDRHYTHM-001-review-4.md` (gitignore 대상 — 레인 트리에만 있음)
- 지적 1건(minor, 막지 않음): progress.md §E.1 의 「iteration 1 아직 미실행」이 낡음 → 이 커밋에서 감사 이력으로 고침. 같은 단락의 「기존 앱 연출 미생성」도 t510 기준선 반영으로 고침

## 4. 카드 문면과 다르게 처리한 것

- **AC-012 측정**: 카드는 「classify UNEXPLAINED 0 · MISSING 0」. 그러나 지금 `classify_diff.py` 는 MISSING 을 출력하지 않고 승인본↔송신본을 비교하지도 않는다. 그래서 AC-012 는 세 조건을 직접 적고, 승인본↔송신본 비교 스크립트(또는 classify_diff.py 를 고쳐 두 UNEXPLAINED 방향을 「승인 안 됨」「송신 안 됨」으로 읽는 판)를 **M2 전 준비물**로 적었다. 리드 확인 받음.
- **비교 기준**: 작업 중 main 에 t510(LOVE ATTACK 기존 앱 연출 기준선)이 들어와 「기존 앱 연출 미생성」이 낡은 문장이 됐다. main 을 병합하고 AC-010·REQ-011·plan 을 t510 기준선으로 고쳤다.

## 5. 재지 않은 것

- t510 기준선은 **가짜 콘솔에서만** 만들어졌다. 실기 재생은 M2 에서 감독 승인 송신(AC-012 규칙)으로 한다 — 실기에서 같은 190줄이 나가는지는 모른다(가짜 콘솔은 풀을 응답하지 않아 페이저 송신 0줄).
- LOVE ATTACK 의 BPM·구간 지도(t509)는 이 카드에서 읽지 않았다. M1 시각 작업은 그 산출물에 기댄다.
- 곡 중간 `Master 3.n At BPM` 송신 방법 — 미측정.
- 타임코드 이벤트: **실기 큐 진행은 잰 사실이다** — t506(PR #552, 머지 `e7eaf690`, `.moai/reports/t506/verdict.md` §9)이 실기에서 Go+ 이벤트 3개로 Seq 9 큐 1→2→3 을 약 1·2·3초에 넘겼고(전환 구간마다 이벤트 시각 포함), 이벤트를 명령줄로 만들 수 있음(Lua 불필요 — 작은따옴표 · `cd Timecode 14.1.1.1.1` · 트랙 NO 주소)도 쟀다. **남은 미측정은 정밀도(약 0.15초 표본 간격이 한계)와 이벤트 수 상한**이다. 앱 재생 계약은 여전히 timecode 모드를 거부한다(`server/director/emit.py:51`) — 앱 쪽 배선은 M4+ 후보. (처음 판정서에는 「미측정」으로 적었다가 리드 판독으로 고침)

## 6. 판정

plan 정정 완료. 감사 PASS 0.96. 콘솔 0 · 코드 0. 머지는 리드, run(M1)은 감독 착수 승인 뒤.
