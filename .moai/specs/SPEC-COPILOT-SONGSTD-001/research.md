# SPEC-COPILOT-SONGSTD-001 — 리서치 기록 (2026-08-14)

곡/타임라인 단위 조명연출 표준의 근거 수집. 병렬 리서치 4방향(웹 3 + 리포 1)
+ 오케스트레이터 직접 검색 2회. 상세 원문은 각 에이전트 트랜스크립트
(`history://TimelineLDResearch` 등) — 본 문서는 표준 초안이 인용하는 사실의
압축본이다. 표준 초안: `docs/proposals/song-lighting-design-standard.md`.

## A. 타임라인 설계 방법론 (TimelineLDResearch + 직접 검색)

- LD의 표준 절차: 곡을 3회 청취 — ①감상 ②명시적 큐 포인트(악센트·벌스/
  코러스 경계·템포 변화) 추출 ③곡의 "색"(감정) 결정. 결과물은 통상
  **4~5개 기본 룩**(오프닝/벌스/코러스/솔로/엔딩). [ProSoundWeb, GearHeads]
- 큐는 음악적 랜드마크(intro/verse/chorus/bridge/solo/breakdown/end)마다
  최소 1개. "구간마다 큐가 있으면 대체로 올바른 방향." [MLP Lighting]
- 긴장-해소 모델: 벌스=긴장 축적, 프리코러스=입가심(변화 예고),
  코러스=해소. [MLP Lighting]
- **헤드룸 보존**: 무빙이 상시 돌고 색이 수 초마다 바뀌면 클라이맥스에서
  갈 곳이 없다. [Starshine]
- 다운비트 정렬: 큐·범프는 마디의 1박(다운비트)에. 곡 끝의 "버튼"(박수
  유도 범프)은 0.5~2카운트 급점등 후 유지→서서히 다운. [MLP, ControlBooth,
  Lin-Manuel Miranda]
- 페이드 관례: 스냅(0s)=곡 내 급격한 히트/드롭 한정, 크로스페이드
  1.5~2s=구간 전환 기본, 3~5s=빌드·감정 전환. [SHEHDS, Uking]
- 실행 모드 3종: 풀 타임코드(고정 셋리스트·정밀), 풀 버스킹(즉흥),
  **하이브리드가 현대 표준**(빅히트·드롭·씬체인지=타임코드, 스트로브·컬러
  범프·오디언스 스윕=수동). 전곡 타임코드 고정은 기계적 쇼 위험.
  [Spotlight Report, TicketFairy, Uking]
- 큐 번호 규약(연극): 장면당 번호 대역을 띄워 리허설 삽입 여지 확보
  (100/200/…, 또는 10/20/… + 11,12 삽입). [Theatrecrafts]

## B. 이펙트(페이저) 운용 관례 (EffectsResearch)

- 축별 용도: Pan/Tilt 스위프=기악·빌드업(벌스에선 무빙 절제), 서클(pan+tilt
  saw, phase 오프셋)=미드템포 최면 구간, 디머 체이스/펄스=리듬 강조, 컬러
  체이스=질감, 고보/프리즘/줌/포커스=특정 순간의 어트리뷰트 큐(상시 아님).
  [SHEHDS, OnStageLighting, SoundSwitch]
- **속도 배수 관례**: 빠른 축(컬러·디머)=1박/스텝, 느린 축(포지션)=8박 주기
  — 축별 속도를 배수 관계로 겹친다. [Uking]
- BPM 동기: 콘솔 speed를 곡 BPM에 동기(탭템포/MIDI/타임코드). 같은 BPM도
  장르가 스냅(테크노) vs 페이드(하우스)를 결정. [freudundlight, LQE]
- 절제: "완벽한 한 아이디어 > 싸우는 다섯 아이디어", "움직일 수 있다고 매번
  움직이지 않는다", 동시 사용 픽스처를 줄이면 피크가 커진다. [Oasis,
  ChurchProduction, Vectorworks]
- 스트로브 안전: 발작 위험 10–25Hz 대역, UK HSE 권고 ≤4Hz, 연속 시퀀스
  ≤30초, 입구 경고문. 스트로브는 구두점. [Epilepsy Society, litelees]
- grandMA3 phaser: Speed 단위 BPM/Hz/s, Phase 0…360(픽스처별 오프셋),
  recipe = 선택+프리셋+MAtricks+fade/delay+Speed/Phase, 값 2개 지정 시
  범위 스프레드. [MA help 2.0/2.4]

## C. 컬러·인텐시티 설계 (ColorIntensityResearch)

- 팔레트: **3~5색 제한**(많으면 회색화). 베이스+액센트, 보색(긴장·펀치) vs
  유사색(통일). 3레이어: 베이스(중립 화이트, 가시성)/미들(무드 워시)/톱
  (액센트). [XMLite, Epic, Betopper]
- 프런트는 웜/중립 화이트로 피부톤 보존, 채도 색은 백/배경 레이어로.
  흔한 실패 = 배경 화려한데 보컬 얼굴 어두움. [Epic, Starshine]
- **백라이트 = 키의 30~50%** 시작 가이드라인. 키 표준 45/45. [SHEHDS]
- 색 의미론: 레드=강렬(피크·과용 시 불안), 블루=차분·감성(발라드 표준,
  연구 근거), 웜/쿨 대비=록의 다이내믹스 시각화. 벌스 쿨→코러스 웜 관례.
  [SHEHDS ×3, illustrate]
- CCT: 텅스텐 3200K, 에너지 구간 5600~7000K, 감성 구간 3000~4000K.
  full CTO ≈ 5600→3200K. 혼용 편차 관객 ±500K/카메라 ±300K.
  [OnStageLighting, vellolight]
- 페이드 디폴트(연극): 2~5s 전환, 디자이너 기본값 3.1s/5.1s 관례,
  스냅~1분 혼용. [ControlBooth]

## D. 장르 프로파일 (Timeline + Color 리서치 종합)

- 메탈: 서브장르 팔레트(블랙=콜드 블루/화이트, 스래시=레드/웜, 파워=비비드),
  더블킥×스트로브 동기, 대비>편안함. [TicketFairy metal]
- 록: 레드·화이트 시그니처, 같은 곡 내 웜/쿨 대비, 드럼 히트·보컬 진입
  정밀 타이밍, 블랙아웃 후 급점등. [SHEHDS rock]
- EDM: 속도·기하학 중심, 드롭=스트로브 폭발, 단색 볼드 워시. [djclublight]
- 발라드: 소프트 화이트 프런트+쿨블루/퍼플 백, 무빙 최소, 긴 페이드,
  마지막 벌스 타이트 스팟+페이드투블랙. [SHEHDS, Northern]

## E. 현 콘솔(Copilot) 능력 경계 (ConsoleCapabilityScout — 파일:라인 근거)

- 정적 값 축(밴드1): Dimmer, ColorRGB_R/G/B만 무조건 허용
  (schema.py:39-45). Zoom/Iris는 프로브 통과(밴드3). Pan/Tilt 정적 값은
  룩 로더가 거부하지만 **spatial 계층이 별도 보유**(Position 프리셋
  2.21~2.30 + 큐 시트, 이번 CUETIME-001).
- 페이저: Step/Phase(0 Thru 360)/Speed(BPM) 문법 검증. 라이브러리:
  dimmer 2종(pulse-beat/breath), color 2종(warm-cool/club-rgb Speed 128),
  movement 8종(sweep/wave/circle/diagonal — ASSUMPTION-40, 직접 실측 아님).
  MAtricks 5축.
- 다이내믹스 1~5는 **룩 선택 인덱스일 뿐** 값을 스케일하지 않음
  (busking.py:96-115) — 표준의 핵심 개선 지점.
- 시간축: TrigType Time/Follow + TrigTime, Timecode 저장·배정 검증
  (songcue.py:481-498, mib.py).
- **못 내는 축**: Gobo(풀 스코프 밖), 스트로브/셔터(danger 정책 배제),
  Focus/Frost/Prism(콘솔 거부 실측), At Relative/Accel/Decel(게이트),
  SpeedMaster(그렙 0건). 이펙트는 기계 판독 불가(Phase/Speed 읽기 불가).

## 종합 판단 (표준 초안의 뼈대)

1. 리서치는 일관되게 "**구간 다이내믹스가 모든 축을 함께 결정**"을 지지 —
   현 시스템의 빈 곳(다이내믹스가 룩 인덱스에 불과)과 정확히 대응.
2. 기계 검사 가능한 규칙이 다수 추출됨: 팔레트 3~5색, 백=키 30~50%,
   스냅 0s는 히트 한정, 페이드 2~5s 기본, 최고점 예산(블라인더=마지막
   코러스·엔딩), 헤드룸 단조성, 축 속도 배수, 인접 큐 변화율.
3. 표준은 콘솔 능력 경계(E)를 2계층으로 다뤄야 함: 지금 집행 가능한 규칙
   (디머/RGB/포지션/페이저/타이밍) vs 장래 규칙(고보/스트로브/줌 확장).
