# 음악에 어울리는 조명 배치 — 벤치마킹과 콘솔 기능 조사

- 작성: 2026-10-03, 팩토리 리드
- 계기: 감독 판정(2026-10-03). 「문제 인식은 있지만 어떻게 해야 할지가 없다. 박자에 맞춰 많이 쪼개는 것은 의미가 없다. 쪼갠 자리에 어떤 연출과 효과를 놓아 어떻게 이을지, 그리고 그것이 음악과 어울리는지가 먼저 정해져야 한다.」
- 범위: 웹 조사(제품·현장 관행·연구)와 grandMA3 공식 매뉴얼 확인. 코드 수정 0, 콘솔 접촉 0.
- 표기: **[확인]** 은 원문 쪽을 직접 열어 읽은 것, **[요약만]** 은 검색 요약으로만 본 것, **[저장소]** 는 이 저장소의 기록, **[판단]** 은 리드의 추론이다.

---

## 한눈에 보기

1. **감독이 원하는 방식은 업계에서 실제로 쓰는 방식이다.** 음악에 맞춰 조명을 자동으로 만드는 도구들(rekordbox 조명 모드, SoundSwitch)은 박자 단위로 큐를 쪼개지 않는다. 먼저 곡을 구간 종류(인트로·벌스·코러스·브릿지·빌드업·드롭·아웃트로)로 나누고, **구간 종류마다 어떤 연출을 놓을지 정한 표**를 쓴다. 곡마다 그 표를 손으로 고칠 수 있다.
2. **박자는 큐를 쪼개는 데가 아니라 '움직임의 속도'에 쓴다.** 현장 디자이너들은 구간 안의 움직임(체이스·페이저) 속도를 곡 빠르기에 묶고, 강한 박(드롭 진입, 히트)에만 따로 강조를 얹는다.
3. **장면을 잇는 규칙도 있다.** 인접한 두 장면 사이에는 한두 가지 속성만 바꾼다. 큰 순간 직전에는 일부러 덜어낸다. 가장 큰 연출은 마지막 드롭이나 마지막 코러스에 아껴 둔다. 극적인 장면은 서서히 넘기고, 히트는 끊어서 넘긴다.
4. **"음악과 어울린다"를 숫자 하나로 재는 성공 사례는 찾지 못했다.** 연구도 결국 사람이 판정한다. 대신 판정을 세 갈래로 나누는 틀은 빌려 쓸 수 있다. 순간별로 맞는지, 넘어가는 방식이 맞는지, 곡 전체의 흐름이 맞는지다.
5. **콘솔은 감독이 알고 있는 기능을 다 갖고 있다.** 오디오 입력으로 비트를 인식하고, 효과 속도를 곡 빠르기에 묶고, 타임코드에 이벤트를 원하는 만큼 놓을 수 있다. 다만 소리 인식으로 큐를 넘기는 방식은 재현이 안 된다. 그래서 앱이 미리 시각을 계산해 타임코드에 넣는 방식을 권한다.

---

## 1. 다른 도구는 "무엇을 어디에 놓을지"를 어떻게 정하나

| 도구 | 음악에서 읽는 것 | 연출을 놓는 단위 | 어떤 연출을 고르는 방법 | 근거 |
|---|---|---|---|---|
| rekordbox 조명 모드 (AlphaTheta) | 구간 분석: Intro·Up·Down·Chorus·Bridge·Verse·Outro | 구간 | **구간 종류 → 장면** 대응표(Macro Mapping)를 사용자가 정한다. 곡마다 장면을 손으로 다듬는 편집기(Macro Editor)가 있다 | [요약만] 지원 페이지 직접 열기는 403 |
| SoundSwitch (Engine DJ) | 구간 자동 분할 + 드롭·브레이크다운·빌드업 검출 | 구간 | 미리 만든 박자 동기 패턴(Autoloop) 32~128개를 구간 종류에 자동 배정. 배정 규칙은 공개되지 않음 | [확인] rekkerd.org 기사 |
| MaestroDMX | 인트로·빌드·드롭·전환·조용한 구간을 실시간 추적 | 실시간 상태 | 에너지 단계(Still→Beam→Ambient→Chill→Energetic→Dance→Party)와 색 묶음을 바꿔 가며 반응. 조용하거나 말하는 구간에서는 조명을 낮춘다 | [확인] 제품 페이지·패턴 문서(내부 알고리즘은 비공개) |
| Lightkey | 탭 템포 | 사람이 짠 큐 | 박자 동기 효과 엔진. 구간 자동 인식은 확인되지 않음 | [요약만] |
| Avolites Titan · ChamSys MagicQ 사운드 투 라이트 | 주파수 대역 7개의 음량 | 박·음량 | 소리 크기로 큐를 넘기거나 효과 크기·속도를 바꾼다. **곡 구조를 모른다** | [확인] 두 회사 매뉴얼 |

**읽을 점 [판단]:** 맨 아래 줄의 사운드 투 라이트가 감독이 "의미 없다"고 한 방식이다. 박자에는 반응하지만 무엇을 왜 놓는지가 없다. 위의 두 도구는 반대로 **구간 종류별 연출표**를 중심에 두고, 박자는 패턴 안의 움직임 속도에만 쓴다. 우리 앱의 다음 단계가 닮아야 할 쪽은 이쪽이다.

---

## 2. 현장 연출 원칙 — 무엇을 놓고 어떻게 잇나

### 2.1 구간별로 놓는 것 [확인: vellolight.com, shehds.com]

| 구간 | 놓는 것 |
|---|---|
| 벌스 | 느린 움직임, 절제된 효과, 가수 얼굴이 보이게 |
| 프리코러스 | 밝기·폭·움직임을 조금씩 더해 기대를 쌓는다 |
| 코러스 | 장면을 연다. 역광을 강하게, 효과를 넓게, 체이스를 빠르게 |
| 브릿지 | 색을 확 바꿔 곡의 꺾임을 표시한다(밝기만 바꾸지 않는다) |
| 브레이크다운 | 움직임을 줄이고 대비를 키운다. 다음 상승을 위한 숨 고르기 |
| 드롭 · 마지막 코러스 | 아껴 둔 가장 큰 연출을 쓴다 |
| 아웃트로 | 안정된 상태로 돌아온다 |

### 2.2 구간 안의 움직임 [확인]

- 체이스의 단계 수·파형·속도는 곡 빠르기에 묶고, 구간의 에너지에 따라 키운다. 박마다 따로 쏘지 않는다.
- 빠르기 환산: 한 박 = 60 ÷ BPM 초. 체이스 한 단계를 한 박, 반 박, 한 마디 같은 단위로 맞춘다.

### 2.3 장면을 잇는 규칙 — 감독이 말한 "연결"

1. **한 번에 한두 속성만 바꾼다.** 색이면 색, 위치면 위치. 셋을 한꺼번에 바꾸면 음악을 따르는 변화가 아니라 무작위로 보인다. [확인: shehds]
2. **극적인 장면은 크로스페이드로, 히트는 끊어서 넘긴다.** [확인: vellolight]
3. **큰 순간 직전에 덜어낸다.** "잠깐 멈춤, 고정된 빔, 줄인 색이 다음 히트를 더 세게 만든다. 공연 내내 최대 출력으로 움직이면 대비가 사라진다." [확인: shehds]
4. **가장 큰 연출을 아낀다.** 코러스마다 최대 연출을 쓰지 않고 드롭·마지막 코러스에 남겨 둔다. 그래야 곡 전체가 올라가는 흐름이 보인다. [확인: vellolight]
5. **구간이 바뀌어도 일부 속성은 유지한다.** 그래야 관객이 잡음이 아니라 '변화'로 읽는다. [확인: vellolight]
6. **조용한 구간·보컬 구간에서는 낮춘다.** MaestroDMX도 같은 원칙을 쓴다. [확인]
7. **색은 한 곡에 3~5개로 제한한다.** [확인: xmlitelighting]

### 2.4 음악 성질과 조명 성질의 짝 [요약만]

감각 간 대응 연구(Spence 2011)는 다음 짝이 사람에게 자연스럽게 느껴진다고 정리한다. 원문은 로그인 벽 때문에 직접 읽지 못했다.

- 소리 크기 ↔ 밝기
- 음높이 ↔ 높이(빔 위치)와 색의 밝기
- 빠르기 ↔ 움직임 속도

---

## 3. "음악과 어울린다"는 어떻게 판정하나

- **연구 사례 [확인, 일부]:** Skip-BART(arXiv 2506.01482, 2026)는 록·메탈 라이브 공연 35개의 조명을 학습해 음악에서 색과 밝기를 만든다. 평가는 두 가지를 같이 한다. 실제 디자이너가 만든 조명과 프레임마다 비교하는 숫자 평가와, 사람이 "분위기와 에너지 흐름이 음악과 맞는가"를 보는 판정이다. 결과는 "사람 조명 엔지니어와 비슷한 수준"이라고 보고했다. 판정 인원·점수 척도는 PDF에서 읽지 못했다.
- **후속 연구 [요약만]:** SeqLight는 먼저 공간 전체의 색 분포를 정하고, 그다음 기구별로 나눈다. "무슨 분위기인가"와 "어느 기구가 맡나"를 분리하는 구조다.
- **숫자만으로 잰 성공 사례: 없음.** 숫자 평가는 "사람이 한 것을 따라 했나"까지만 답한다. "좋은가"는 결국 사람이 본다.

**우리 판정에 빌려 쓸 틀 [판단]:**

1. **순간별 판정:** 구간마다 2.1 표의 처리와 맞는지 본다. 앱이 미리 자가 점검할 수 있다.
2. **연결 판정:** 인접한 두 장면이 2.3의 규칙을 지키는지 본다. 바꾼 속성 수, 큰 순간 전의 덜어냄, 최대 연출의 위치를 센다. 앱이 미리 셀 수 있다.
3. **곡 전체 판정:** 감독이 실기에서 본다. 기계로 대체하지 않는다.

1과 2는 감독 판정 전에 걸러 내는 체(최소 조건)일 뿐이고, 합격 여부는 3이 정한다.

---

## 4. grandMA3 콘솔 — 가능한 것과 아직 모르는 것

| 기능 | 가능 여부 | 문법·근거 |
|---|---|---|
| 오디오 입력 | 가능 | 뒷면 XLR 3핀 Audio Remote In, 신호 50mV 이상 [확인: Connect Audio In] |
| 소리로 큐 넘기기 | 가능 | 큐 트리거 Sound(주파수 대역 22개 중 선택) [확인: Sequence Sheet] |
| 비트로 큐 넘기기 | 가능 | 큐 트리거 BPM, "사운드 입력의 비트로 큐를 넘긴다" [확인: Sequence Sheet] |
| 자동 BPM 마스터 | 가능 | 스피드 마스터 16번이 오디오에서 BPM을 잡는다 [확인: Speed Masters] |
| 스피드 마스터를 곡 빠르기로 설정 | 가능 | `Master 3.1 At BPM 75` [확인: BPM Keyword] |
| 효과를 스피드 마스터에 묶기 | 가능, **실기 확인됨** | `Attribute "Pan" At SpeedMaster 1` [확인: SpeedMaster Keyword] · 2026-08-15 실기 확인 [저장소: FXGEN spec §A.1 V3, t502 보고서] |
| `At Speed <값>`의 단위 | BPM, **실기 확인됨** | [저장소: FXLIB spec.md:64 ASSUMPTION-38, t502 보고서] |
| 타임코드 쇼 만들기 | 가능, **실기 확인됨** | `Store Timecode 999` · `Assign Sequence 9 At Timecode 999` 실기 송신 성공 [저장소: docs/research/ma3-effects/14-musicsync-m3a-timecode-probe-run2.md:29] |
| 타임코드 재생 | 문법은 있음, **효과는 실기 미확인** | 같은 문서의 「2회차 정정」: Go·Pause 등이 콘솔 상태를 바꿨다는 판정은 오판이었고, 재생 효과는 관측되지 않았다 [저장소:75] |
| 타임코드 이벤트로 특정 큐 실행 | 가능 | 이벤트에 동작(Token)을 걸어 큐를 실행한다 [확인: Timecode Events] |
| 콘솔 내부 시계로 재생 | 가능 | 외부 SMPTE·MIDI·Art-Net 또는 내부 시계 [확인: Timecode] |
| 시퀀스당 큐 수 | 사실상 제한 없음 | "거의 무제한의 시퀀스와 시퀀스당 많은 큐" [요약만] |

### 판단 — 큐 100개 넘게 박자에 놓을 수 있나

**가능하다. 방식은 하나를 권한다 [판단].**

- **권하지 않는 방식 — 콘솔의 소리 인식으로 큐 넘기기.** 공식 문서에 정확도·지연 보장이 없다. 사용자 포럼에는 "느리다, 안 잡힌다"는 글이 있다([요약만]). 무엇보다 공연마다 결과가 달라서, 감독이 보고 고친 연출이 그대로 재생된다는 보장이 없다.
- **권하는 방식 — 앱이 시각을 미리 계산해 타임코드 이벤트로 넣기.** 매번 같은 연출이 나오고, 감독이 이벤트를 한 줄씩 고칠 수 있다. 타임코드 생성과 시퀀스 연결은 이미 실기에서 성공했다. 재생 효과는 아직 확인하지 못했다.
- **효과 속도는 스피드 마스터로 묶는다.** 곡이 시작할 때 마스터 하나를 곡 빠르기로 맞추고, 페이저는 그 마스터를 따르게 한다. 묶는 문법은 실기로 확인됐다.

---

## 5. 지금 우리 앱과의 차이 (t502 실측, PR #548)

- 곡 분석은 빠르기 숫자 하나만 넘긴다. 비트 시각은 계산한 뒤 버리고, 다운비트와 킥은 만들지 않는다.
- 실기로 검증된 무빙 페이저 경로(`server/spatial/position_fx.py`, 곡 빠르기를 받는 `At Speed`)가 이미 있다. 하지만 곡 큐를 만드는 쪽은 이 경로를 부르지 않는다.
- 감독이 본 Rain(212)은 한 장면 안에서 움직이는 것이 0이었다. Club Diver(213)는 14장면 중 9장면이 같은 색 흐름 하나였다.
- 우리 표준(§9)에는 구간마다 무엇을 놓을지는 있지만, **장면을 잇는 규칙(2.3)과 구간 안 움직임 속도의 규칙이 없다.**

---

## 6. 제안 — 코드보다 「연출 대본」을 먼저

감독이 짚은 순서대로라면 다음 일은 코드를 쓰는 것이 아니라 **한 곡의 연출 대본을 먼저 확정하는 것**이다 [판단].

- **대본의 모양:** 곡의 시간 순서대로 「음악 순간 → 놓는 연출 → 앞 장면과 잇는 방식 → 이유」를 적는다.
  - 예: 「1:02 코러스 진입 히트 → 블라인더 한 번, 무빙 전부 위로 열기 → 프리코러스 마지막 2박을 어둡게 비워 둔 뒤 끊어서 넘김 → 2.3 규칙 3, 4」
- **절차:**
  1. 리드가 2장의 원칙과 1장의 구간표 방식으로 한 곡(예: Club Diver)의 대본 초안을 쓴다.
  2. 감독이 대본만 보고 고친다(콘솔 없이).
  3. 고친 대본을 콘솔에 손으로 올려 감독이 본다.
  4. 감독이 "어울린다"고 하면, 그 대본을 만든 규칙을 표준과 SPEC으로 옮긴다.
  5. 그다음에 앱이 같은 대본을 만들게 한다.
- **이 순서의 이유:** 지금까지는 규칙을 먼저 코드로 만들고 실기에서 판정받았다. 그래서 두 번 연속 "작동은 하지만 음악이 아니다"로 끝났다. 대본을 먼저 확정하면 "무엇이 어울리는가"를 코드 이전에 감독의 눈으로 정할 수 있다.

### 감독이 정할 것

1. 위 순서(대본 먼저 → 손으로 올려 보기 → 규칙화 → 코드)로 갈지.
2. 첫 곡으로 무엇을 쓸지. Club Diver는 빠르고 구간이 분명하다. Rain은 느린 곡이라 "절제"를 보기에 좋다.
3. 박자 표현에 스트로브·블라인더 번쩍임을 넣을지. 표준 §10.3은 "스트로브는 강조이지 박자 계수기가 아니다"라고 정해 두었다.
4. 효과 속도의 기준을 앱이 분석한 빠르기(재현 가능)로 할지, 콘솔 오디오 입력(현장 적응, 재현 불가)으로 할지.

---

## 7. 확인하지 못한 것

| 항목 | 이유 |
|---|---|
| rekordbox 조명 모드의 세부 동작 | 지원 페이지가 403. 검색 요약으로만 봤다 |
| SoundSwitch의 구간→패턴 배정 규칙 | 비공개 |
| Skip-BART 판정의 인원·척도 | PDF에서 읽지 못했다 |
| 감각 대응 연구 원문 | 로그인 벽 |
| 타임코드 이벤트·트랙 수 상한, 시간 정밀도 | 공식 문서에서 찾지 못했다 |
| 효과 속도 절반·두 배 배수 문법 | 공식 문서에서 찾지 못했다 |
| 시퀀스 단위로 스피드 마스터를 묶는 공식 문법 | 포럼 글 제목만 봤다 |
| 콘솔 오디오 비트 인식의 정확도 | 실기 시험이 필요하다 |
| 타임코드 재생이 실제로 큐를 넘기는지 | 실기 미확인 |
| 팝·EDM 공연의 곡당 일반적인 큐 수 | 포럼 글 하나(「시퀀스당 100개 넘는 큐는 흔하다」)뿐 |

---

## 출처

- [What is LIGHTING mode? — AlphaTheta Help Center](https://support.alphatheta.com/en-US/articles/8297993958425) [요약만]
- [How can I use rekordbox Lighting mode? — AlphaTheta Help Center](https://support.alphatheta.com/en-US/articles/4410034117401?product=4406500792217) [요약만]
- [SoundSwitch automated phrase detection — rekkerd.org](https://rekkerd.org/soundswitch-flips-the-script-with-new-advanced-lighting-automation-and-automated-phrase-detection/)
- [SoundSwitch 2.9 — Hummingbird Media](https://news.hummingbirdmedia.com/lighting-control-software-soundswitch-announces-version-29-with-auto-bpm-detection-and-enhanced-autoloop-features)
- [MaestroDMX — kpodj.com](https://kpodj.com/maestro-dmx-m-246)
- [Patterns Overview — MaestroDMX](https://maestrodmx.freshdesk.com/support/solutions/articles/153000070516-patterns-overview)
- [Lightkey](https://lightkeyapp.com/en) [요약만]
- [External triggering — Avolites Titan Manual](https://manual.avolites.com/docs/17.0/running-the-show/midi-dmx-or-audio-triggering/)
- [Audio — ChamSys MagicQ Documentation](https://secure.chamsys.co.uk/docs/magicq/manual/audio.html)
- [Concert lighting methodology — MA Lighting Forum](https://forum.malighting.com/forum/thread/61888-concert-lighting-methodology/) [요약만]
- [Programming Chases and Cues for Live Shows — VELLO Light](https://www.vellolight.com/article/programming-chases-cues-live-shows/)
- [How to Sync Stage Lights With Music — SHEHDS](https://shehds.com/blogs/news/how-to-sync-stage-lights-with-music)
- [Stage Lighting Color Theory & Emotion — XM Lite](https://www.xmlitelighting.com/stage-lighting-color-theory-rules-emotions-and-real-world-applications/)
- [Automatic Stage Lighting Control: Rule-Driven Process or Generative Task? (Skip-BART)](https://arxiv.org/pdf/2506.01482)
- [Stage Light is Sequence² (SeqLight)](https://pith.science/paper/2605.03660) [요약만]
- [Crossmodal correspondences: A tutorial review](https://link.springer.com/article/10.3758/s13414-010-0073-7) [요약만]
- [grandMA3 — Speed Masters](https://help.malighting.com/grandMA3/2.4/HTML/masters_speed.html)
- [grandMA3 — BPM Keyword](https://help.malighting.com/grandMA3/2.0/HTML/keyword_bpm.html)
- [grandMA3 — SpeedMaster Keyword](https://help.malighting.com/grandMA3/2.0/HTML/keyword_speedmaster.html)
- [grandMA3 — Sequence Sheet](https://help.malighting.com/grandMA3/2.2/HTML/cue_sequence_sheet.html)
- [grandMA3 — Timecode](https://help.malighting.com/grandMA3/2.1/HTML/timecode.html)
- [grandMA3 — Create a Timecode Show](https://help.malighting.com/grandMA3/2.3/HTML/timecode_create.html)
- [grandMA3 — Timecode Events](https://help.malighting.com/grandMA3/2.3/HTML/timecode_events.html)
- [grandMA3 — Connect Audio In](https://help.malighting.com/grandMA3/2.3/HTML/fs_connect_audio_in.html)
