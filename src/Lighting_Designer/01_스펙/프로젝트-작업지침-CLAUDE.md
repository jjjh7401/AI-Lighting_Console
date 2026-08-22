# 음악 조명연출 시퀀스 포맷 — Cowork 작업 지침

> moai-cowork | 생성일 2026-08-20
> 활용 플러그인: moai-office, moai-content, moai-media, moai-core, moai-writer
> 주요 산출물: 조명 큐시트(XLSX), HTML 타임라인 뷰, 연출안(PPTX/PDF), 포맷 명세서(MD)

---

## 1. 프로젝트 개요

**목적**: 무대에서 연주되는 **1곡 단위 음악**에 대한 **조명연출 시퀀스 표준 포맷**을 정립한다. 곡이 바뀌어도 동일한 규칙으로 큐시트를 작성·전달·실행할 수 있는 재현 가능한 포맷이 최종 목표다.

**1차 사용자**: 공연 무대 **조명 콘솔 오퍼레이터** (GrandMA / Hog 계열 실행 환경 가정)
**2차 사용자**: 연출가·조명감독(협의용 연출안), 무대감독(진행 큐 대조)

**타임라인 기준 축**: **곡 구조(Section) + 타임코드(TC)** 병기
- 1차 축: `Intro / Verse / Pre-Chorus / Chorus / Bridge / Break / Outro` 등 곡 구조
- 2차 축: 각 큐의 `mm:ss.f` (프레임 필요 시 SMPTE `hh:mm:ss:ff`)
- 보조: BPM·마디는 비트 싱크 이펙트에만 선택 기입

**톤·형식 제약**
- 큐시트는 **현장 인쇄 대응** — A4/A3 가로, 흑백 인쇄에도 판독 가능해야 함(색은 색상명 텍스트 병기)
- 용어는 **조명 실무 원어 유지** (wash, key, back, haze, strobe, chase, sweep, blinder, snap, fade)
- 한 큐 = 한 행. 서술형 문장 금지, 실행 가능한 지시로 작성

## 2. 행동 원칙 (HARD)

1. **사전 확인 후 실행**: 곡·러닝타임·BPM·곡 구조·장비 리스트가 없으면 먼저 묻는다.
2. **스킬 체인 보고 후 실행**: 멀티스텝 작업은 체인을 먼저 보고하고 AskUserQuestion으로 승인받는다.
3. **텍스트 산출물은 AI 슬롭 검수로 종료**: `ai-slop-reviewer` → `korean-humanize` 순으로 마감한다.
4. **기본 artifacts보다 moai 스킬 우선**: 아래 §3 표의 스킬이 있으면 기본 도구로 직접 생성하지 않는다.
5. **추측한 타임코드 금지**: 실제 음원·타임코드를 확인하지 못한 구간은 `TC: 확인필요`로 남기고 결과물 끝 「확인 필요 항목」에 모아 명시한다. 그럴듯한 초 단위를 지어내지 않는다.
6. **포맷 v1 준수**: 모든 큐시트는 `docs/LX-SEQ-SPEC-v2.1.md`의 필드·값 규칙을 따른다. 필드를 임의로 추가·삭제하지 않고, 필요하면 스펙을 먼저 개정한다.

## 3. 문서 생성 우선순위 (HARD)

| 산출물 | 사용 스킬 |
|---|---|
| XLSX / 큐시트 | `moai-office:xlsx-creator` |
| PPTX / 연출안 | `moai-office:pptx-designer` |
| PDF / 배포본 | `moai-office:pdf-writer` |
| HTML / 타임라인 뷰·스펙 | `moai-content:html-report` |
| HTML / 발표 슬라이드 | `moai-content:html-slide` |
| 차트·시각화 규칙 | `dataviz` (색·축·범례 표준) |
| 무드보드 이미지 | `moai-media:higgsfield-image` |
| AI 티 제거 | `moai-core:ai-slop-reviewer` |
| 한국어 정밀 윤문 | `moai-writer:korean-humanize` |

## 4. AI 슬롭 후처리 (HARD)

**텍스트 산출물의 마지막 단계**에 `ai-slop-reviewer` → `korean-humanize`를 호출한다.
출력은 **진단 요약 → 수정 텍스트 → 주요 변경사항** 3블록.

- 대상: 포맷 명세서, 연출안 설명, 콘셉트 서술, 작성 가이드, 공유 메일
- **제외**: 큐시트 표 데이터, 타임코드, DMX 값, 채널 번호, JSON/CSV — 숫자·코드는 손대지 않는다

## 5. 프로젝트 워크플로우 (스킬 체인)

### ① 포맷 명세서 정의·개정
- 요청 예시: "큐시트 필드에 팔로우스팟 열 추가해줘", "포맷 v1.1로 개정"
- 체인: `[스펙 설계]` → `moai-content:html-report` → `moai-core:ai-slop-reviewer` → `moai-writer:korean-humanize`
- 입력: 추가·변경할 필드, 사유 / 출력: `docs/LX-SEQ-SPEC-vN.md` + 개정 이력

### ② 1곡 조명 큐시트 (마스터 산출물)
- 요청 예시: "이 곡 조명 큐시트 만들어줘", "3분 40초 발라드 시퀀스 짜줘"
- 체인: `[곡 구조 분해]` → `[무드·컬러 팔레트 설계]` → `[CUE 작성]` → `[CUE-EX 실행 레이어 전개]` → `moai-office:xlsx-creator` → `[포맷 준수 검증 15항목]`
- 입력: 음원/곡명·러닝타임·BPM·곡 구조·장비 리스트·무드 키워드
- 출력: `.xlsx` 6시트 (HEAD/CUE/NOTE + PATCH/PRESET/CUE-EX) + `.cue-ex.csv` (MA3 임포터용)
- **제외 조건**: ai-slop-reviewer 생략 (표·수치 데이터) · 실행 레이어 불요 시 연출 3시트만 (v1.1 호환)

### ③ HTML 타임라인 뷰
- 요청 예시: "큐시트 타임라인으로 보여줘", "연출가 확인용 시각화"
- 체인: `[큐시트 파싱]` → `moai-content:html-report` + `dataviz` → `[자체완결 검증]`
- 입력: ②의 xlsx / 출력: 단일 HTML (인라인 CSS·SVG, 가로 타임라인, 색 블록, 인쇄 대응)
- **제외 조건**: ai-slop-reviewer 생략

### ④ 연출안 PPT/PDF
- 요청 예시: "연출가 협의용 연출안 만들어줘", "무드보드 포함 PDF로"
- 체인: `[콘셉트 정리]` → (선택) `moai-media:higgsfield-image` → `moai-office:pptx-designer` → `moai-office:pdf-writer` → `moai-core:ai-slop-reviewer`
- 입력: ②③ 산출물 + 콘셉트 키워드 / 출력: `.pptx` + `.pdf`

### ⑤ 큐시트 검증·리뷰
- 요청 예시: "이 큐시트 포맷 맞는지 봐줘", "전환 너무 잦은지 점검"
- 체인: `[스펙 대조]` → `[전환 밀도·색 연속성 진단]` → `[수정 제안]`
- 출력: PASS/FAIL 항목별 진단표 + 수정안. 파일을 임의로 덮어쓰지 않는다.

## 5.4 활용 코디네이터 에이전트

| 코디네이터 | 담당 | 호출 트리거 |
|---|---|---|
| `moai-office:office-doc-qa` | 오피스 문서 생성+AI 티 검수 | "연출안 PPT 만들고 검수까지" |
| `moai-core:core-text-qa-coordinator` | 텍스트 최종 QA(슬롭→윤문→맞춤법) | "공유 전 마지막 검수" |
| `moai-media:media-production-pipeline` | 무드보드·레퍼런스 이미지 제작 | "무드보드 이미지 뽑아줘" |

## 5.5 프로젝트 에이전트

- `lighting-sequence-coordinator` — 곡 분해 → 팔레트 → 큐시트 → 타임라인 → 연출안 전 과정 오케스트레이션

⚠️ `./.claude/agents/`의 에이전트는 **새 세션(또는 `/reload-plugins`)에서 활성화**됩니다.

## 6. 큐시트 필드 규격 (요약)

정본은 `docs/LX-SEQ-SPEC-v2.1.md`. 요약 열 순서:

`Q# | Section | TC In | TC Out | Dur | Mood | Color(주/보조) | Intensity | Fixture Group | Movement | Effect | Transition | Fade | Note`

- `Q#`: `Q010`, `Q020` … 10 단위 증분 (중간 삽입 여지)
- `TC In/Out`: `mm:ss.f`, 곡 시작 = `00:00.0` · `TC_METHOD`(VERIFIED/DERIVED) 필수
- `Intensity`: 0–100 (%) · `Transition`: `SNAP`|`FADE`|`XFADE`|`BUMP` · `Fade`: 초 소수 1자리

**실행 레이어 (v2.0, 타깃 grandMA3)**: `PATCH`(패치) + `PRESET`(POS/COL/BM/FX 프리셋 — Position은 절대값 대신 현장 레코드 참조) + `CUE-EX`(큐×그룹 long format, 빈칸=트래킹, I/P/C/B 개별 페이드, Phaser Rate는 BPM 동기 공식 `SongBPM÷사이클박수`). CUE-EX는 CSV 병행 출력 — MA3 SequenceImporter 등 임포트 경로용.

## 7. 실행 플로우

1. **[Interview]** 빠진 맥락 수집 (곡·러닝타임·BPM·구조·장비·무드) — 최대 3질문
2. **[Summary]** 곡 구조 분해표를 먼저 제시해 확인
3. **[Plan+Confirm]** 체인 + 완료 기준 제시 → AskUserQuestion 승인
4. **[Execute]** 체인 순차 실행 → 단계별 요약 → 검수 → 「확인 필요 항목」 명시 → SendUserFile로 전달

**스킵 조건**: 단순 조회, 이미 상세 지시, "빠르게" 명시, 직전 작업의 후속 요청

## 8. 커넥터 / API 키

- 현재 필수 API 키 없음
- 무드보드 이미지 생성 시 **Higgsfield MCP** 사용 (세션 연결 필요)
- 필요 시 `.moai/credentials.env`에 프로젝트 격리 저장

## 9. 딥씽킹

`--deepthink` / `ultrathink` 포함 시 단계별 심층 분석.
자동 트리거: 포맷 스펙 개정, 3개+ 산출물 동시 작업, 곡 전체 연출 콘셉트 결정.

## 10. 프로젝트 맥락

- 사용자는 방송·무대 제작 현장 실무자다. 조명 용어를 풀어 설명하지 말고 실무 어휘로 바로 쓴다.
- 이 프로젝트의 성공 기준은 "예쁜 문서"가 아니라 **다른 사람이 그 큐시트만 보고 동일하게 실행할 수 있는가**다.
- 1곡 샘플은 포맷 검증용이다. 샘플을 만들 때마다 포맷의 빈틈을 기록하고 스펙 개정 후보로 남긴다.

---

**작업을 요청하면 위 체인이 자동으로 트리거됩니다. 자연스럽게 대화하세요.**
