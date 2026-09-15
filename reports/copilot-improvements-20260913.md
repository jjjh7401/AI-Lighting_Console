# 코파일럿 앱 개선 보고 — 2026-09-13

기준 커밋: `2752706` → `7bd5d25` · PR 4건(#430 #431 #432 #433) 머지 · 카드 9장 종료

## 1. 감독 지적과 대응

| 감독 지적 | 대응 | 결과 |
|---|---|---|
| 컬러·이펙트·전환이 큐리스트 전체 동일 | t393 뿌리 수정 + t386 | 색 1→5종, 효과 1→5종, 질감 1→5종 |
| 분석 리포트가 없다 | t387 | 큐시트 위 접힘 요약 6줄 |
| 큐시트가 전체가 안 보인다 | t388 | 상시 스크롤바 + 가장자리 페이드 |
| 런북 우측이 비어 있다 | t389 | **미해결** — 안전한 매핑 부재로 표시 안 함 |

리드 자체 발견 3건: t390(현재 큐 강조 불가), t391(구간 이름 S1~S16 중복), t392(소수 15자리 노출).

## 2. 뿌리 원인 (t393)

`_section_role` 이 `name` 과 `mood` 만 읽는데, 오디오 확정 구간은 `name=f"S{n}"` · `mood=""` 로 생성된다(둘 다 의도된 설계 — plan.md §C D5, DSP 는 감정 미측정). 결과 16/16 전부 `other`.

`other` 는 `_ARC_PALETTE`/`_ARC_FX`/`_ARC_TEXTURE`/`_ARC_D_LEVEL` 네 표에 없어 `.get()` 이 `None` → 각 함수가 기본값 반환 → 세 축 동시 우회.

처방: t383(D레벨) 선례대로 `PositionSheetSection.role` 전용 필드 추가, `_section_role` 이 명시값 우선, `_infer_confirmed_role(index, d_levels)` 로 D레벨에서 역할 추정.

양성 대조군: `Intro/Verse 1/Chorus 1/Bridge 1/Chorus 2` 입력 시 `intro/verse/chorus/bridge/finale` 정상 반환 — 판정기 자체는 무결.

## 3. 실제 음원 end-to-end 실증

입력: `src/걸그룹DinoDino_C_max최고품질.wav` (31MB). 저장소 최초 실행.

분석 출력: BPM 126.05 (신뢰도 0.974) · 구간 16 · 1마디 1.904s · 온셋 806 · D레벨 `[2,4,4,5,5,2,2,5,4,5,4,5,1,4,2,5]`

| 축 | 개선 전 | 개선 후 |
|---|---|---|
| 역할 | 1 (전부 `other`) | 5 |
| 팔레트 | 1 | 5 |
| 이펙트 | 1 | 5 |
| 질감 | 1 | 5 |
| 이름 고유수 | 16/16 (분할 후 16/17) | 16/16 (분할 후 17/17) |

구간표(실측):

| # | 시각 | 이름 | D | 색 | 효과 |
|---|---|---|---|---|---|
| 1 | 0.0s | Intro | D2 | deep blue+블루 | (없음) |
| 2 | 6.9s | Verse 1 | D4 | 블루+cyan | slow pan |
| 3 | 20.3s | Verse 2 | D4 | 블루+cyan | slow pan |
| 4 | 26.6s | Chorus 1 | D5 | warm white+magenta+블루 | dimmer chase+pan sweep |
| 5 | 46.6s | Chorus 2 | D5 | warm white+magenta+블루 | dimmer chase+pan sweep |
| 6 | 69.0s | Verse 3 | D2 | 블루+cyan | slow pan |
| 7 | 72.8s | Verse 4 | D2 | 블루+cyan | slow pan |
| 8 | 76.9s | Chorus 3 | D5 | warm white+magenta+블루 | dimmer chase+pan sweep |
| 9 | 115.2s | Bridge 1 | D4 | cold blue+블루 | slow tilt |
| 10 | 120.1s | Chorus 4 | D5 | warm white+magenta+블루 | dimmer chase+pan sweep |
| 11 | 125.4s | Bridge 2 | D4 | cold blue+블루 | slow tilt |
| 12 | 130.1s | Chorus 5 | D5 | warm white+magenta+블루 | dimmer chase+pan sweep |
| 13 | 149.2s | Bridge 3 | D1 | cold blue+블루 | slow tilt |
| 14 | 154.7s | Verse 5 | D4 | 블루+cyan | slow pan |
| 15 | 159.3s | Bridge 4 | D2 | cold blue+블루 | slow tilt |
| 16 | 162.4s | Finale | D5 | warm white+gold+블루 | dimmer chase+accent sweep |

## 4. 페이드 (t386)

fade 는 D레벨 기반으로 이미 16배 갈려 있었다(1마디 1.904s 기준): D1 3.808s(8박) · D2 1.904s(4박) · D4 0.714s(1.5박) · D5 0.238s(반 박). 정본 §5.1 [HARD] "코러스 큐는 두 박 늦으면 안 된다"를 D5 가 이미 충족.

감독이 `FADE` 한 단어만 본 원인 둘: (a) `trans = "SNAP" if fade==0 else "FADE"` 가 16배 차이를 한 단어로 축약, (b) `Fade` 열이 화면에서 잘림(t388 이 해결).

t386 변경: `SectionDecision.role` 추가, `finale` 큐는 D1 행 fade 사용. 실측 finale 4.0s vs chorus 0.25s.

`trans` 는 여전히 1종(`FADE`) — fade==0 큐가 없기 때문. SNAP 조건 신설은 범위 밖.

## 5. 레이어 판독 (t385)

`layer_mapping` 추론은 이미 구현·발화 중이었음. 구멍은 `effect` 별칭 `{effect,fx,aerial,beam}` 이 이 리그 그룹명과 정확 일치 0건.

`strobe`/`haze` 추가. 리그 18개 중 역할 판독 5개: `key←KEY`, `back←BACK`, `audience←FOH`, `effect←STROBE,HAZE`.

미판독 13개: SIDE-L/R/ALL, MOVER-U/D/ALL, WASH-U/D/ALL, BLIND, ALL, ODD, EVEN.

## 6. 검증

| 항목 | 기준 | 결과 |
|---|---|---|
| pytest | 12682 | **12713 passed, 33 skipped** (신규 +29, 회귀 0) |
| vitest | 558 | **570 passed** (신규 +12, 회귀 0) |
| tsc | — | 0 에러 |
| ruff check / format | — | 통과 |
| CI | — | **판정 불가** — GitHub Actions 과금 차단으로 전 run 이 2초 내 미시작 실패. main 최근 5커밋 전부 동일 |

## 7. 감독 조치 필요

1. **브라우저 새로고침** — 화면 3건(스크롤 신호·현재 큐 강조·소수점)은 즉시 반영됨. 빌드·재시작 완료(앱 PID 55287, `/healthz` ok).
2. **곡 재설계 필요** — 저장된 타임라인은 구 구조라 여전히 `S1~S16` 표시. 색·이름·효과 개선은 곡을 다시 설계해야 발화.
3. **육안 확인 2건** — 스크롤바 가시성, 분석 요약 접힘 블록 렌더링. 브라우저 부재로 미검증.

## 8. 미해결 / 후속 카드

| 카드 | 내용 | 근거 |
|---|---|---|
| t389 | 런북 우측 빈 칸 | 타임라인 Seq 110 `console_stored:false`, 실행기는 다른 시퀀스. 큐 번호 체계 2종(`no` 1~16 / `cue_no` 0~14) |
| t395 | `FOH` 가 `audience` 로 판독 | 정본 §6.2·t377 은 같은 그룹을 프론트 필로 사용. MOVER/WASH 전체 미판독 |
| t396 | 역할 추정기가 절대 밝기 미고려 | 실제 곡에서 D2 연속 구간(69.0s·72.8s)이 verse 판정, D4 구간이 bridge 판정. t371·t375 와 동일 계열 |
| t382 | 양보가 상승 사다리 덮어씀 | 기존 카드 |
| t394 | t386 전제 정정 기록 | — |

## 9. 리드 자체 오류 기록

t384 최초 가설(구간 mood 의 색 단어가 `_section_palette_choice` 조기 return 으로 색표 우회) — **반증됨**. 확정 구간 mood 는 빈 문자열이라 해당 경로 미발화. 코드에서 발견한 분기가 실제로 발화하는지 미측정한 채 원인으로 단정.

t388 1차 수정(`overflow: auto` → `overflow-x/y: auto`) — **무효**. CSS 동등. 리드가 검출해 재작업 지시.
