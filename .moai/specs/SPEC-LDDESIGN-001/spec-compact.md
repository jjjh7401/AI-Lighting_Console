# SPEC-LDDESIGN-001 — 압축 요약

**무엇을**: 감독 워크시트(YAML) → 컨셉 계층(`server/concept/`, 신설,
순수 데이터) → 큐 모델 v2(동작형: retain/add/remove/reduce/replace/
isolate/expand/restore/release) → 기존 하류(lint/energy/cue_fade/OSC)
그대로. 11편의 조사·검증 보고서(2026-09-21) + 설계 문서
`src/Lighting_Director/AI_Lighting_Copilot_Research_Integration.md` +
정본 `docs/proposals/song-structure-lighting-standard.md`를 압축.

**왜**: 감독 지적 — "보고서만으론 무대가 안 바뀐다." 오늘 프로토타입
(`final_integrated.py`)이 8곡·게이트 13개(104칸)로 **PASS 98/n·a 6/
FAIL 0**을 실행값으로 증명. 후렴 정체성 유지율 0.302(현 경로) →
0.877~1.0(프로토타입, v3 최종치 8곡 전부 1.0).

**선행 조건(M0)**: t429 회귀 수정(`WT-chorus-collision` `4d4cc94f`)
`origin/main` 머지 + SPEC-LDRETURN-001 완료 확인(현재 `draft`), `bpm=
density_bpm` 실배선(t428), 두 큐 생성 경로 단일화(`web/session.py` /
`orchestrator/tools.py:3230`).

**핵심 요구사항 그룹(REQ-LDDESIGN-001~085)**:
1. **선행조건**(001~004) — M0.
2. **닫힌 어휘**(005~010) — 구간 9 · 트리거 10토큰(문서 8항목) · 원샷 7.
   판정기 5종 재매핑 + "감독 확인" 표시. `[G1]`
3. **워크시트 YAML**(011~016) — `palette`(4칸)·`concept`·`sections`·
   `notes`, 어휘 밖 값은 조립 거부.
4. **큐 모델 v2**(017~025) — layer·operation·tracking·timing·evidence·
   headroom·mib 7필드. `restore`는 색 포함, `reduce`는 구간 기준 참조.
5. **컨셉·컬러 규칙**(026~035) — 팔레트 4칸(주/보조/클라이맥스/유보),
   유보색·언더페인팅(후렴≥3)·브리지 3규칙, `_arc_palette` 회전 폐기.
   `[G6][G7]`
6. **3층 밀도**(036~041) — 구간+프레이즈=시퀀스 큐(10~45) + 원샷 별도 레인. 빌드업·눈 리셋 자동 삽입. `[G8][G13]`
7. **§4 회차**(042~049) — 정체성+축 확장 6종, 모션 분배, 후렴4회 이후 프레이즈1, Bridge remove+KEY·BACK. `[G2][G3][G4][G5]`
8. **헤드룸**(050~052) — 4축 + 경고 4조건(구간 단위). `[G5]`
9. **트래킹**(053~057) — Block/Track/Cue Only/Release. `[G9]`
10. **타이밍**(058~061) — Snap/Short/Long/순차, `cue_fade.py` 재사용. `[G11]`
11. **MIB**(062~067) — 어두운 창 판정(잠정값)·Mark 자동·무버 소등·live_move 경고. `[G12]`
12. **안전 큐·설명·근거**(068~072) — Q0.5 Block · 끝 Release · 자동 설명 · evidence 4등급.
13. **하류 브리지·게이트 고정**(073~077) — lint/energy/cue_fade 재사용, 13게이트를 `server/tests/`로 고정.
14. **UI**(078~085) — 컨셉 패널(접힘+4칸) · 인과 불릿+6칸 표 · 타임라인 색=Color Strip · CUE SHEET +2열 · PLAN CUE +3줄+Q### · 상태줄 GATE · 스크롤 연동.

**비목표**: 방송·다중 콘솔, 콘솔 프로브 필요 문법(Block/Release/축별
딜레이/Mark 실제 명령, 스트로브 정책, MIB 초 실측), 객석광/Gobo/Prism/
LED, 판정기 정확도, 학습 루프.

**잠정값**(plan.md §F, M8 프로브로 확정, 3건): MIB 이동 1.5s+정착
0.5s · 콘솔 문법 3종(Block/Release·축별 딜레이·Mark, 그때까지 주석/
메타로만 출력) · `allow_strobe` 기본값 `false`(감독이 켜야 생성).

**검증**: 8곡 자동 게이트(콘솔 불필요) + 실기 Rain 1곡 검증(필수,
AC-021) + 콘솔 프로브 3종(관측치 기록이 완료 기준, AC-022~024).

**Tier 예외**: REQ 85·AC 33은 Tier L 상한(25/25)의 3.4배·1.3배 —
감독 지시("전부를 스펙 문서로")에 따른 명시적 예외(spec.md §2.4).
M0~M8이 sub-SPEC 역할, run-phase에서 마일스톤별 카드 발행.

**Tier**: L. 산출물(SSOT 5종): spec/plan/acceptance/design/research.md.
`spec-compact.md`는 추가 요약. `progress.md`는 run-phase 착수 시.
