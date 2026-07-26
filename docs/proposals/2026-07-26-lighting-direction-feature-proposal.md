# 무대 조명 연출·오퍼레이션 기능 제안 보고서

> 작성일: 2026-07-26 · 상태: 제안(proposal) · 작성 경위: 웹 조사(검색 8회 + 핵심 소스 2건 본문 검증) 기반 심층 분석
>
> 배경: 현재 앱은 grandMA3 콘솔 조작을 돕는 코파일럿(문법 계층)은 완성했으나, 조명 디자이너(연출)와
> 오퍼레이터 관점에서 무대 조명을 **연출**하는 데 도움이 되는 기능(연출 계층)이 비어 있다.
> 본 문서는 실무 워크플로우 조사 결과와 격차 분석, 우선순위별 기능 제안을 담는다.

## 1. 조사 범위와 핵심 발견

6개 각도(디자이너 워크플로우 / 오퍼레이터·버스킹 / AI 연구 / grandMA3 실무 / previz·페이퍼워크 /
소규모 현장)로 웹 조사를 수행하고, 핵심 소스 2건(arXiv 논문, MA3 타임코드 실무 가이드)은 본문을
직접 확인했다.

### ① 조명 디자이너(연출)의 실제 작업 흐름

연출 작업은 콘솔 앞에 앉기 훨씬 전에 시작된다: 대본/음악 분석 → 콘셉트·무드보드 → **큐 시놉시스**
(어느 장면에서 무엇이 변하는지 초안) → 라이트 플롯 + 페이퍼워크 → 테크 리허설에서 큐 확정.
디자이너의 4대 문서는 **플롯(어디 걸었나) / 포커스 차트(어디 비추나) / 훅업 차트(어느 채널인가) /
큐시트(언제 얼마나 밝나)**이고, 큐잉 속도를 좌우하는 것은 이를 한 장에 압축한 **매직시트**(치트시트)다.

### ② 오퍼레이터의 두 가지 운영 모드

- **큐 재생형**(연극·교회): 미리 짠 큐를 순서대로 "Go". 볼런티어 현장의 최대 장벽은 기술이 아니라
  **"망칠까 봐" 하는 두려움**이며, 훈련의 목표는 "예측 가능한 컨트롤 + 확신"이다.
- **버스킹형**(콘서트·클럽): 사전 시퀀스 없이 준비된 팔레트·이펙트·익스큐터를 실시간 트리거.
  버스킹의 성패는 **사전 준비물의 품질**(프리셋 팔레트, 익스큐터 페이지 레이아웃 — "곡당 1페이지"
  또는 "공연당 1페이지" 전략)이 결정한다.

### ③ 시간이 가장 많이 새는 곳

실무 가이드와 포럼에서 반복된 병목:

- (a) 테크 리허설은 항상 시간 부족 — 프로는 **테크 전에 큐를 미리 만들어 가서 현장에선 수정만**
  하는 방식을 선호.
- (b) 타임코드 쇼 준비 — 곡 구조(Intro/Verse/Chorus…) 단위로 곡당 시퀀스 1개, 프레임 나징(미세 조정),
  **큐 작성 전 프리셋 구축**이 대표적 시간 소모처.
- (c) previz 소프트웨어(Capture/Depence/Vision)가 성장한 이유 자체가 "현장 도착 전에 큐를 짜두는"
  수요 때문.

### ④ AI 자동화 연구가 그은 경계선

arXiv 논문(Skip-BART)은 음악→조명을 **생성 과제**로 풀어 인간 조명 엔지니어와 통계적으로 구분 불가
(p=0.72) 수준에 도달했다. 단, **프레임 단위 색/강도 동기화는 자동화 가능하지만, 공연 전체를 관통하는
미학적 일관성과 감정 해석은 인간 몫**이라는 한계를 명시한다. 상용 제품 MaestroDMX는 "박스 속 조명
디자이너"로 실시간 오디오 반응 자율 운영을 판다 — 즉 **콘솔을 대체**하는 방향이다. 반면 본 앱은
"AI가 프로그래머, 사람이 연출 확정"이라는 정반대 포지션으로, 자동화 경계선 연구 결과와 정확히
정합한다. 이 차별점은 지킬 가치가 있다.

## 2. 격차 분석 — 현재 앱 vs 연출·운영 워크플로우

현재 앱(`.moai/project/product.md` 기준)은 자연어→커맨드, Lua 플러그인, 패치, 이펙트/큐 생성까지 —
즉 **"문법 계층"은 완성**했으나, 그 위의 **"연출 계층"이 통째로 비어** 있다:

| 워크플로우 단계 | 실무자가 하는 일 | 현재 앱 | 격차 |
|---|---|---|---|
| 연출 준비 | 음악 분석, 룩 구상, 큐 시놉시스 | ❌ 없음 | 🔴 큼 |
| 프로그래밍 | 커맨드/큐/프리셋 작성 | ✅ 핵심 역량 | — |
| 타임코드 쇼 빌드 | 곡 구조 마커, 시퀀스 배치, 나징 | ❌ 없음 | 🔴 큼 |
| 버스킹 준비 | 팔레트·익스큐터 페이지 설계 | ⚠️ 개별 명령으로만 가능 | 🟡 중간 |
| 문서화 | 매직시트·큐시트·인수인계 | ❌ 없음 | 🟡 중간 |
| 쇼 당일 운영 | 프리쇼 체크, 큐 진행, 이상 대응 | ⚠️ 상태 조회만 있음 | 🟡 중간 |

## 3. 기능 제안 (우선순위순)

### 🥇 P1 — 연출 계층의 뼈대 (기존 자산으로 즉시 착수 가능)

#### P1-1. 송 구조 기반 큐리스트 초안 생성기 — 로드맵 Phase 3의 구체화

음원 파일을 분석(구간 분할·BPM·에너지 곡선)해 Intro/Verse/Chorus 구조를 뽑고, 섹션별 룩을 매핑해
**"곡당 시퀀스 1개 + 타임코드 트랙 + 섹션 마커"**라는 실무 표준 구조 그대로 MA3에 생성한다.
실무자들이 손으로 하던 "DAW 마커 → MA3 미러링" 작업을 통째로 대체하며, 이미 검증된 OSC/Lua 배포
파이프라인 위에서 동작한다. Skip-BART 연구가 이 방향의 실현 가능성을 입증했고, 초안→사람 검토라는
앱의 안전 철학과도 맞는다.

#### P1-2. 버스킹 준비 마법사

리그 컨텍스트(이미 구현됨)를 읽어 "이 리그로 버스킹 준비해줘" 한 마디에 **컬러/포지션/빔 프리셋
팔레트 + 장르별 익스큐터 페이지 레이아웃**을 일괄 생성한다. 버스킹 실무의 성패가 사전 준비물 품질에
달려 있고, "큐 작성 전 프리셋 구축"이 최대 시간 소모처라는 조사 결과에 직격으로 대응한다.

#### P1-3. 연출 어휘 계층(룩 라이브러리) — Phase 2 목표의 실체화

"웅장한 금색 코러스" 같은 추상 지시를 **앵글·컬러·강도·무브먼트 조합의 '룩'**으로 변환하는 디자인
지식 레이어. 장르별(록/발라드/워십/EDM) 룩 템플릿을 내장하고 사용자 리그에 맞게 인스턴스화한다.
P1-1·P1-2가 모두 이 어휘 위에서 돌아가므로 공통 기반이 된다.

### 🥈 P2 — 차별화 기능

#### P2-4. 자동 페이퍼워크 생성

쇼파일을 읽어 매직시트·큐시트·훅업 차트를 자동 생성(HTML/PDF). 디자이너 4대 문서를 손으로 만드는
관행 대비 명확한 시간 절약이고, 앱의 기대효과인 "인수인계 용이"와 직결된다. 쇼파일 파서가 이미 있어
구현 부담이 낮다.

#### P2-5. 볼런티어 런북 모드

큐리스트를 읽어 **"다음 Go를 누르면 무슨 일이 일어나는지"를 한국어 진행 대본**으로 만들어주는 모드.
"망칠까 봐" 두려움이 최대 장벽이라는 조사 결과에 대응하며, 앱의 핵심 타깃(전문 오퍼레이터가 없는
소규모 현장)과 정확히 겹친다.

#### P2-6. 프리쇼 체크 자동화

픽스처 응답 확인 매크로 생성 + 결과 리포트(주소 불일치·무응답 픽스처 탐지). 기존 OSC 상태 조회
능력의 자연스러운 확장이다.

### 🥉 P3 — 장기 (Phase 4 이후)

- **P3-7. 레퍼런스 이미지 → 룩 변환**: 무드보드/공연 사진에서 팔레트·무드를 추출해 룩 제안.
- **P3-8. 라이브 다음 큐 제안·이상 감지**: 라이브 잠금 모드에서 read-only 제안 카드(로드맵 Phase 4
  그대로 — MaestroDMX식 자율 운영은 계속 비목표로 유지 권장).
- **P3-9. previz 연계**: MVR 내보내기로 Capture/Depence 검증 루프 연결.

## 4. 결론

조사 결과가 가리키는 방향은 하나다: **실무의 최대 병목은 "콘솔 문법"이 아니라 "현장 도착 전 준비"**
(큐 초안, 프리셋 팔레트, 타임코드 구조, 문서)이고, 현재 앱은 그 준비 작업을 실행할 손(문법 계층)은
완성했지만 무엇을 준비할지 아는 머리(연출 계층)가 없다. P1 세 기능(룩 어휘 → 큐리스트 생성 → 버스킹
마법사)이 그 머리를 만들어주며, 셋 다 기존 로드맵(Phase 2·3)과 어긋남 없이 이미 검증된 파이프라인
위에 얹을 수 있다.

## Sources

- [Automatic Stage Lighting Control: Rule-Driven or Generative? (arXiv)](https://arxiv.org/html/2506.01482) · [Stage Light is Sequence² (arXiv)](https://arxiv.org/pdf/2605.03660)
- [How I Turn a Cue List into a Tour-Ready Light Show (grandMA3 타임코드 실무)](https://www.starshinelights.com/blogs/news/grandma3-timecode-guide) · [MA Lighting 포럼 — 타임코드 쇼 베스트 프랙티스](https://forum.malighting.com/forum/thread/68160-best-practice-for-timecode-show/) · [콘서트 조명 방법론 스레드](https://forum.malighting.com/forum/thread/61888-concert-lighting-methodology/)
- [The Design Process (LibreTexts)](https://human.libretexts.org/Bookshelves/Theater_and_Film/Book:_Theatrical_Worlds_(Mitchell)/06:_Lighting_Design/6.05:_The_Design_Process) · [Theatrecrafts — 조명 페이퍼워크](https://theatrecrafts.com/pages/home/topics/lighting/lighting-design-paperwork/) · [Magic Sheets: Revisited (Mike Wood LD)](https://www.mikewoodld.com/2024/11/11/magic-sheets-revisited-2/)
- [Essential Busking — Executors (On Stage Lighting)](https://www.onstagelighting.co.uk/lighting-equipment/stage-lighting-control/busking-page-executors/) · [Timecode vs Busking (Ticket Fairy)](https://www.ticketfairy.com/blog/lighting-for-bpm-festivals-timecode-vs-busking)
- [MaestroDMX](https://maestrodmx.com/) · [MaestroDMX 리뷰 (Digital DJ Tips)](https://www.digitaldjtips.com/maestrodmx-is-an-ai-powered-lighting-designer-in-a-box/)
- [Capture & Depence previz 활용기](https://www.visualspectrum.studio/blog-posts/how-we-use-capture-depence-for-previsualisation-in-touring-shows) · [Vectorworks Vision](https://www.vectorworks.net/en-US/vision)
- [교회 볼런티어 조명 훈련 (Church Production)](https://www.churchproduction.com/magazine/how-to-train-church-lighting-volunteers-without-overwhelming/) · [Cueing vs Busking (Church Production)](https://www.churchproduction.com/education/lighting-cueing-vs-busking/) · [LightKey 오퍼레이터 훈련 (Churchfront)](https://churchfront.com/2026/05/12/lightkey-operator-training-the-simple-way-to-run-church-lighting-without-panic/)
