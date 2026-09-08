# -*- coding: utf-8 -*-
"""LXSEQ RIG 팩 — 쇼 단위 콘솔 기본설정 샘플 (LX-SEQ v2.1, 타깃 grandMA3)
장비 리스트 · 패치 · 그룹 · 프리셋(DIM/COL/POS/BM) · FX 라이브러리 · 콘솔 설정
※ 기종·풋프린트·주소는 전부 표준 가정값 — 실제 플롯 확정 시 교체 (RIG-HEAD에 명시)
"""

RIG_ID = "LXSEQ_RIG_01"
RIG_REV = "r3"

RIG_HEAD = [
    ("RIG_ID", RIG_ID),
    ("SHOW_NAME", "확인필요 (샘플: 단독 공연 1세트)"),
    ("VENUE", "확인필요 (중형 공연장 가정 · 무대 폭 12m × 깊이 8m)"),
    ("CONSOLE", "grandMA3 (기종·소프트웨어 버전 확인필요)"),
    ("OUTPUT", "sACN · Universe 1–5 (+U6 예비) · Priority 100"),
    ("SPEC_VER", "LX-SEQ v2.1"),
    ("REV", RIG_REV),
    (
        "DATA_STATUS",
        "PROPOSED — 실제 공연 표준 기종으로 제안. 풋프린트는 제조사 DMX 차트 실측값. 보유/대여 리스트 확정 필요.",
    ),
    ("SONG_FILES", "LXSEQ_SAMPLE_01_Sugar (r3) — 이 RIG의 그룹·프리셋 체계를 참조"),
]

# 장비 인벤토리: Group | 기종(실제) | Mode | ch(제조사 실측) | 수량 | 리깅 위치 | 회로/전원 | 용도 | Sugar 사용
FIXTURES = [
    (
        "KEY",
        "ETC S4 LED S3 Lustr X8",
        "Direct 12ch",
        12,
        6,
        "FOH 브리지",
        "L1",
        "인물 페이스 · 보컬 중심",
        "사용",
    ),
    (
        "FOH",
        "ETC S4 LED S3 Lustr X8",
        "Direct 12ch",
        12,
        8,
        "FOH 트러스",
        "L1",
        "전면 워시 · 전체 페이스",
        "미사용",
    ),
    (
        "BACK",
        "Martin MAC Aura XB",
        "Extended 25ch",
        25,
        12,
        "업스테이지 트러스",
        "L2",
        "백라이트 · 실루엣 · Aura FX",
        "사용",
    ),
    (
        "SIDE-L",
        "Martin MAC Aura XB",
        "Extended 25ch",
        25,
        6,
        "하수 붐 (3단×2)",
        "L3",
        "사이드 컬러 · 폭 확장",
        "사용",
    ),
    (
        "SIDE-R",
        "Martin MAC Aura XB",
        "Extended 25ch",
        25,
        6,
        "상수 붐 (3단×2)",
        "L3",
        "사이드 컬러 · 폭 확장",
        "사용",
    ),
    (
        "WASH-U",
        "Martin RUSH PAR 2 RGBW Z",
        "9ch",
        9,
        10,
        "업스테이지 플로어",
        "L4",
        "업 워시 · 바닥 컬러",
        "사용",
    ),
    (
        "WASH-D",
        "Martin RUSH PAR 2 RGBW Z",
        "9ch",
        9,
        10,
        "다운스테이지 플로어",
        "L4",
        "다운 워시",
        "사용",
    ),
    (
        "MOVER-U",
        "Robe MegaPointe",
        "Mode 1 39ch",
        39,
        8,
        "업 트러스",
        "L5",
        "에어빔 · 고보 · 프리즘 주력",
        "사용",
    ),
    (
        "MOVER-D",
        "Robe Spiider",
        "Mode 1 49ch",
        49,
        8,
        "다운 트러스",
        "L5",
        "무빙 워시빔 · 플라워 FX",
        "사용",
    ),
    (
        "BLIND",
        "Elation CUEPIX Blinder WW2",
        "4ch",
        4,
        6,
        "다운 트러스 전면",
        "L6",
        "2-cell 블라인더 (각도 리허설 확정)",
        "사용",
    ),
    (
        "STROBE",
        "Martin Atomic 3000 LED",
        "Extended 14ch",
        14,
        4,
        "업 트러스",
        "L6",
        "스트로브 + Aura 백라이트 (광과민 고지)",
        "사용",
    ),
    (
        "HAZE",
        "Look Unique 2.1",
        "2ch",
        2,
        2,
        "무대 양측 플로어",
        "L7",
        "펌프/팬 분리 제어 · 빔 가시화",
        "사용",
    ),
    (
        "FOLLOW-1",
        "Robert Juliat 1.2kW",
        "수동",
        0,
        1,
        "FOH 부스",
        "L8",
        "팔로우 (수동 운용 · DMX 없음)",
        "미사용",
    ),
]

# FID 시작 번호 (기존 곡 파일과 일치)
FID_BASE = {
    "KEY": 101,
    "FOH": 111,
    "BACK": 201,
    "SIDE-L": 301,
    "SIDE-R": 311,
    "WASH-U": 401,
    "WASH-D": 421,
    "MOVER-U": 501,
    "MOVER-D": 521,
    "BLIND": 601,
    "STROBE": 611,
    "HAZE": 621,
    "FOLLOW-1": 631,
}

# 유니버스 배치 계획 (그룹 순서대로 1번지부터 연속 패치, 512ch 초과 금지)
UNIVERSE_PLAN = [
    (1, ["KEY", "FOH", "BLIND", "STROBE", "HAZE"], "프로파일 · 이펙트 · 분위기"),
    (2, ["MOVER-U"], "MegaPointe 전용 (39ch×8=312)"),
    (3, ["MOVER-D"], "Spiider 전용 (49ch×8=392)"),
    (4, ["BACK", "SIDE-L"], "Aura XB (25ch×18)"),
    (5, ["SIDE-R", "WASH-U", "WASH-D"], "Aura XB 잔여 + RUSH PAR"),
]

# MA3 그룹 풀: Group# | 이름 | 구성 | 용도
GROUPS = [
    (1, "ALL", "전 픽스처 (FOLLOW 제외)", "글로벌 · 블랙아웃"),
    (2, "KEY", "KEY 6대", "인물광"),
    (3, "FOH", "FOH 8대", "전면 워시"),
    (4, "BACK", "BACK 12대", "실루엣"),
    (5, "SIDE-L", "SIDE-L 6대", "하수 사이드"),
    (6, "SIDE-R", "SIDE-R 6대", "상수 사이드"),
    (7, "SIDE-ALL", "SIDE-L + SIDE-R", "사이드 일괄"),
    (8, "WASH-U", "WASH-U 10대", "업 워시"),
    (9, "WASH-D", "WASH-D 10대", "다운 워시"),
    (10, "WASH-ALL", "WASH-U + WASH-D", "워시 일괄"),
    (11, "MOVER-U", "MOVER-U 8대", "에어빔"),
    (12, "MOVER-D", "MOVER-D 8대", "무빙 워시"),
    (13, "MOVER-ALL", "MOVER-U + MOVER-D", "무빙 일괄"),
    (14, "BLIND", "BLIND 6대", "블라인더"),
    (15, "STROBE", "STROBE 4대", "스트로브"),
    (16, "HAZE", "HAZE 2대", "헤이저"),
    (17, "ODD", "MOVER-ALL 홀수 FID", "체이스 A조"),
    (18, "EVEN", "MOVER-ALL 짝수 FID", "체이스 B조"),
]

# 딤머 프리셋: ID | 이름 | 레벨 | 용도
PRESET_DIM = [
    ("DIM.FULL", "풀", "100%", "정점 · 테스트"),
    ("DIM.SHOW", "쇼 하이", "85%", "일반 최고 운용 레벨 (풀 대비 여유 확보)"),
    ("DIM.MID", "미드", "60%", "벌스 · 중간 구간"),
    ("DIM.LOW", "로우", "30%", "브리지 · 절제 구간"),
    ("DIM.GLOW", "잔광", "15%", "곡 간 인계 · 대기"),
    ("DIM.OUT", "아웃", "0%", "소등"),
]

# 컬러 프리셋 (연출 팔레트 P.xx와 1:1 + 공용 확장)
PRESET_COL = [
    ("COL.01", "골드 앰버 (=P1)", "R255 G180 B60 / ~2400K", "쇼 기본 온도"),
    ("COL.02", "웜 화이트 (=P2)", "~3200K", "인물 기본"),
    ("COL.03", "뉴트럴 화이트 (=P3)", "~5600K", "작업등 · 리허설"),
    ("COL.04", "핫 핑크 (=P4)", "R255 G60 B158", "후렴 주색"),
    ("COL.05", "딥 퍼플 (=P5)", "R90 G43 B200", "절제 · 브리지"),
    ("COL.06", "터쿼이즈 (=P6)", "R46 G216 B216", "각성 · 프리코러스"),
    ("COL.07", "선셋 오렌지 (=P7)", "R255 G106 B40", "확산 보조"),
    ("COL.08", "딥 블루", "R30 G60 B255", "예비 (타 곡 대비)"),
]

# 포지션 프리셋: ID | 무대 의미 | 대상 그룹 | 레코드 가이드
PRESET_POS = [
    ("POS.01", "보컬 센터 페이스", "KEY", "센터 마이크 위치 · 얼굴 높이 · 그림자 최소 각"),
    ("POS.02", "무대 전체 커버", "MOVER-D", "밴드 라인 포함 균일 커버 · 겹침 30%"),
    ("POS.03", "밴드 라인 백", "BACK", "연주자 5인 실루엣 각 · 객석 눈부심 금지"),
    ("POS.04", "틸트업 스타트 (무대 안쪽)", "MOVER-U", "빔 무대 바닥 안쪽 · 상승 시작점"),
    (
        "POS.05",
        "팬아웃 종점 (객석 상단)",
        "MOVER-ALL",
        "객석 상단 45° · 직사 금지선 위 · 좌우 부채꼴",
    ),
    ("POS.06", "센터 집중 (브리지)", "KEY+BACK", "보컬 1인 포커스 · 주변 어둠 유지"),
    ("POS.07", "크로스 빔", "MOVER-U", "좌우 교차 에어빔 · 예비 (타 곡 대비)"),
    ("POS.08", "플로어 스캔", "MOVER-D", "바닥 훑기 시작점 · 예비"),
]

# 빔 프리셋
PRESET_BM = [
    ("BM.01", "와이드 워시", "MOVER-ALL", "Zoom 45° · Gobo OPEN · Prism OFF"),
    ("BM.02", "미드 빔", "MOVER-ALL", "Zoom 20° · Gobo OPEN"),
    ("BM.03", "좁은 빔 + 프리즘", "MOVER-U", "Zoom 8° · Prism 3-facet ON"),
    ("BM.04", "소프트 프로스트", "KEY", "Frost 30%"),
    ("BM.05", "고보 브레이크업", "MOVER-U", "Gobo 슬롯2(브레이크업) · Zoom 25° · 예비"),
]

# FX(Phaser) 라이브러리: ID | 이름 | 어트리뷰트 | 파형·스텝 | 기본 Rate(BPM) | 기본 Width | 기본 Phase | 비고
FX_LIB = [
    (
        "FX.01",
        "DIM-CHASE",
        "Dimmer",
        "2-step 100/0",
        "240 (@1/8)",
        "50%",
        "0..360",
        "런 체이스 · ODD/EVEN 분리 가능",
    ),
    ("FX.02", "DIM-PULSE", "Dimmer", "Sine 100↔60", "120 (@1beat)", "—", "0..360", "얕은 맥동"),
    ("FX.03", "DIM-BREATHE", "Dimmer", "Sine 100↔40", "30 (@1bar)", "—", "0..360", "느린 호흡"),
    ("FX.04", "COL-RAINBOW", "Hue", "Ramp 0→360°", "15 (@2bar)", "—", "0..360", "색상 순환"),
    ("FX.05", "TILT-SWEEP", "Tilt", "Sine ±25°", "30 (@1bar)", "—", "0..360", "수평 스윕"),
    (
        "FX.06",
        "SHUTTER-STROBE",
        "Shutter",
        "Strobe",
        "15 (@2bar)",
        "—",
        "0",
        "광과민 고지 필수 · Rate 상한 15",
    ),
    ("FX.07", "DIM-TWINKLE", "Dimmer", "Random 100↔30", "30 (@1bar)", "—", "random", "반짝임"),
    ("FX.08", "PT-CIRCLE", "Pan+Tilt", "Circle Ø소", "30 (@1bar)", "—", "0..360", "원형 무브"),
]

# 콘솔 기본설정 (grandMA3)
CONSOLE_SETUP = [
    ("소프트웨어", "grandMA3 v2.x (버전 확인필요) · 쇼파일명 = RIG_ID 동일"),
    ("출력 프로토콜", "sACN · Universe 1–5 (+U6 예비) · Priority 100 · 백업 노드 확인필요"),
    ("트래킹", "Tracking ON (시퀀스 기본) — CUE-EX 빈칸=트래킹 규칙과 일치"),
    (
        "Speed Master",
        "SpeedMaster 1 = 120 BPM (Sugar) · 모든 Phaser는 SpeedMaster 1 종속 · 곡별로 BPM 재설정",
    ),
    (
        "타임코드",
        "LTC IN → TC Slot 1 · 메인 시퀀스 TC 트리거 · TC 유실 시 수동 GO 폴백 (오퍼레이터 대기 필수)",
    ),
    ("MIB", "Move In Black ON (무빙 계열) — 소등 상태에서 다음 큐 포지션 선이동"),
    ("Grand Master", "GM 100% 고정 운용 · 비상 DBO는 X-keys 지정"),
    ("Inhibit", "STROBE·BLIND 그룹 Inhibit 페이더 상시 배치 — 광과민·객석 민원 시 즉시 차단"),
    (
        "프리셋 풀",
        "Pool 번호는 코드가 축별로 정한다 — POS = Preset 2 (pointing.py) · DIM = Preset 1 (실사격) · 시트는 값만 나른다 · 이름은 본 문서 ID와 동일하게",
    ),
    ("백업", "쇼파일 버전업 시마다 USB + 네트워크 이중 백업 · 리허설 전후 필수"),
]

# 이그제큐터 레이아웃 (Page 1): 위치 | 할당 | 동작
EXEC_LAYOUT = [
    ("Exec 101 (Main Go)", "메인 시퀀스 (Sugar 등 셋리스트)", "TC 슬레이브 · 수동 GO 폴백"),
    ("Exec 102 (Fader)", "SpeedMaster 1", "120 BPM · 곡별 재설정"),
    ("Exec 103 (Fader)", "HAZE 출력", "수동 조정 (곡 시작 30초 전 선투입)"),
    ("Exec 104 (Fader)", "STROBE Inhibit", "내리면 스트로브 전체 차단"),
    ("Exec 105 (Fader)", "BLIND Inhibit", "내리면 블라인더 전체 차단"),
    ("Exec 106 (Key)", "DBO (Dead Blackout)", "비상 전체 암전 토글"),
    ("Exec 107 (Key)", "FOH 워크라이트", "COL.03 뉴트럴 · 전환/사고 시"),
]

RIG_NOTES = [
    (
        "리허설변경",
        "FIXTURE 전체",
        "r3: lighting-designer 플러그인 파이프라인 재생성판. 풋프린트 제조사 DMX 차트 재확인 완료 (Robe 공식 DMX 차트: MegaPointe M1=39ch·Spiider M1=49ch / Martin: Aura XB Ext=25ch·Atomic 3000 LED Ext=14ch·RUSH PAR 2=9ch).",
        "2026-08-21",
        "해결(r3)",
    ),
    (
        "리허설변경",
        "FIXTURE 전체",
        "r2: 가정 기종 → 실제 공연 표준 기종으로 교체 (S4 LED S3 Lustr X8 · MAC Aura XB · RUSH PAR 2 · MegaPointe · Spiider · CUEPIX WW2 · Atomic 3000 LED · Unique 2.1). 풋프린트는 제조사 DMX 차트 실측. 전 기종 grandMA3 픽스처 라이브러리/GDTF 존재.",
        "2026-08-20",
        "해결(r2)",
    ),
    (
        "확인필요",
        "FIXTURE 전체",
        "제안 기종이며 보유/대여 리스트와 대조 필요. 기종·모드 변경 시 풋프린트만 고치면 PATCH 자동 재계산.",
        "2026-08-20",
        "미해결",
    ),
    (
        "확인필요",
        "PATCH",
        "Universe 배치·주소는 자동 계산 초안 (U1–U5, U6 예비). 현장 노드 구성·케이블 런 확정 후 조정.",
        "2026-08-20",
        "미해결",
    ),
    (
        "확인필요",
        "POS.01~08",
        "포지션 프리셋 전부 현장 레코드 필요 — 레코드 가이드 열 기준.",
        "2026-08-20",
        "미해결",
    ),
    ("확인필요", "CONSOLE", "grandMA3 버전·sACN 노드·TC 소스 기기 미확정.", "2026-08-20", "미해결"),
    (
        "장비이슈",
        "STROBE·BLIND",
        "Inhibit 페이더 상시 배치 (Exec 104·105) — 운용 안전 규칙.",
        "2026-08-20",
        "미해결",
    ),
]
