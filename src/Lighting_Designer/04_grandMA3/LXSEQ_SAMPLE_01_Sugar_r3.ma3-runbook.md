# MA3 콘솔 작업 런북 — Maroon 5 / Sugar (r3)

- 대상 콘솔: grandMA3 (버전 확인필요 — `[VERIFY]`) · 출력: sACN U1–U5 (+U6 예비)
- 입력 파일: `LXSEQ_SAMPLE_01_Sugar_r3.ma3.txt`(명령 정본) · `LXSEQ_SAMPLE_01_Sugar_r3.macros.xml`(매크로 풀) · `LXSEQ_RIG_01_ShowBase_r3.patch.csv`(패치 정본)
- 근거 문서: `LXSEQ_SAMPLE_01_Sugar_r3.xlsx` (CUE-EX가 기계 정본) · `LXSEQ_RIG_01_ShowBase_r3.xlsx` (RIG 정본)
- **TC_METHOD: DERIVED — 모든 TC는 마디연산(1마디=2.000s) 도출값. 리허설 LTC 대조 전까지 실행 확정본 아님.**
- 권장 경로: **onPC에서 선빌드 → 쇼파일 이동**. 새 쇼파일에서 시작한다(`/Overwrite` 충돌 방지).

## 반입 준비 (매크로 임포트)

1. `macros.xml`의 `DataVersion="2.2.0.0"`을 콘솔 소프트웨어 버전에 맞게 수정 `[VERIFY]`
2. 파일을 `gma3_library/datapools/macros/`에 복사 (USB: `<drive>/grandMA3/gma3_library/datapools/macros/`)
3. Macro Pool 빈 슬롯에서 Import → `LXSEQ 1.~7.` 매크로 7개 확인
4. 프리셋 풀 매핑 확인 `[VERIFY]`: DIM→Pool 1, POS→Pool 2, COL→Pool 4, BM→Pool 21(All), FX→Pool 22(All)

## 8단계 작업 순서

### 1단계 — 패치 (수동)
- Patch 메뉴에서 `patch.csv` 대조 입력. GDTF: S4 LED S3 Lustr X8(Direct 12ch) · MAC Aura XB(Extended 25ch) · RUSH PAR 2 RGBW Z(9ch) · MegaPointe(Mode 1 39ch) · Spiider(Mode 1 49ch) · CUEPIX Blinder WW2(4ch) · Atomic 3000 LED(Extended 14ch) · Unique 2.1(2ch)
- 유니버스 사용량: U1 252 · U2 312 · U3 392 · U4 450 · U5 330 (전부 512 이내, U6 예비)
- FID 블록: 101 KEY · 111 FOH · 201 BACK · 301/311 SIDE · 401/421 WASH · 501/521 MOVER · 601 BLIND · 611 STROBE · 621 HAZE

### 2단계 — 그룹 (매크로 §1)
- `LXSEQ 1.` 실행 → Group 1~18 생성 (ALL·기본 12·SIDE/WASH/MOVER-ALL·ODD/EVEN)
- ODD/EVEN은 MOVER-ALL FID 명시 리스트 기준 — 생성 후 셀렉션 확인

### 3단계 — 딤머·컬러·빔 프리셋 (매크로 §2·§3·§5)
- DIM.FULL~OUT 6종, COL.01~08 8종 (COL.02/03 CCT는 `[MANUAL]` — 기종 CTO/화이트 채널로 수동 설정 후 저장)
- BM.01~05는 Zoom/Gobo/Prism/Frost 어트리뷰트를 기종 GDTF 기준으로 수동 입력 후 Store `[MANUAL]`

### 4단계 — 포지션 프리셋 현장 레코드 (매크로 §4 + 수동)
- POS.01~08: ma3.txt의 레코드 가이드대로 그룹 선택 → 조준 → `Store Preset 2.n /Merge`
- POS.05(팬아웃 종점)는 **객석 직사 금지선** 준수 — 리허설 책임자 입회

### 5단계 — Phaser 빌드 (매크로 §6 + 수동)
- SpeedMaster 1 = 120 BPM 설정 `[VERIFY]` → FX.01~08을 Programmer에서 스텝 빌드 후 Store
- 전 Phaser는 SpeedMaster 1 종속 (Rate: @1/8=240 · @1beat=120 · @1bar=30 · @2bar=15 · @4bar=7.5)
- FX.06 SHUTTER-STROBE는 Rate 상한 15 BPM(@2bar) — 광과민 고지 확인 전 사용 금지

### 6단계 — 시퀀스·큐 (매크로 §7)
- Sequence 1 "SUGAR" · Cue 10~180 (Q# 숫자부 = Cue 번호) · SNAP 5큐는 CueFade 0.0
- LED-W 행은 콘솔 큐가 아님 — `[영상팀 콜]` LW-02~06 상호 확정
- 개별 타이밍: 각 Store Cue 뒤 `[MANUAL]` 주석의 그룹별 I/P/C/B Fade·Delay를 Cue 에디터에서 입력
- FX `OFF` 행은 Stomp 후 저장 `[MANUAL]`

### 7단계 — 타임코드 (ma3.txt §8)
- LTC IN → TC Slot 1 → Timecode 에디터에 Cue 10~170 GO 이벤트 배치 (ma3.txt §8 시각표)
- **Q180(암전)은 TC 트리거 아님 — 곡 종료 확인 후 수동 GO**
- TC 유실 폴백: Exec 101에서 오퍼레이터 수동 GO 대기 상시
- DERIVED 경고: 리허설 LTC 대조 후 이벤트 시각 확정 → 곡 파일 r4(VERIFIED)로 승격

### 8단계 — 안전·백업
- Exec 레이아웃: 101 Main GO · 102 SpeedMaster · 103 HAZE · 104 STROBE Inhibit · 105 BLIND Inhibit · 106 DBO · 107 워크라이트
- STROBE·BLIND Inhibit 페이더 상시 배치 확인, MIB ON(무빙), GM 100%
- 쇼파일 USB + 네트워크 이중 백업 (리허설 전후 필수)

## 리허설 승격 경로

1. 리허설 LTC 대조 → 섹션 경계 실측 → CUE/CUE-EX TC 수정 → `TC_METHOD: VERIFIED`로 r4 발행
2. POS 레코드 완료 → PRESET 시트 `MA3 Pool` 열 기입 → RIG r4
3. BLIND 각도·광과민 고지·영상 큐(LW-02~06) 확정 → NOTE 미해결 항목 해소
