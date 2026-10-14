# t637 — 실곡 데이터로 런북 UI 재캡처 보고

- 카드: t637 · 브랜치: WT-runbook-recapture · 기준: origin/main ce846ab6
- 표기: [잼] 이번 작업에서 직접 측정 (명령 명시) · [옮김] 리드 보고서(lead-1013-status, lead-1014-runbook)에서 옮김 · [추정] 판단

## 1. 결론

1. 전제 재측정: 프리셋·확정 그룹·구간 색이 모두 채워진 실곡 타임라인이 저장소 증거에 있다. 중단 조건에 해당하지 않아 캡처를 진행했다.
2. 캡처 범위: 런북 미리보기 진입점(ui/runbook-preview.html)은 「오늘의 곡·큐 순서」 화면(RunbookMode)만 그린다. 시안의 본체인 박자 격자 프레임(상단 바·곡 전체 지도·3단 폴더·우측 편집 칸·한눈에·무대·하단 명령)은 이 진입점에 없다.
3. 그래서 시안 대비 요소별 판정(같음 / 데이터 부족 / 구조 문제)은 한 건도 확정하지 못했다. 보류 사유는 「경로 부재」 또는 「세션 의존」이다. 「구조 문제」로 판정할 근거는 이번 측정에 없다.
4. 멈춘 곳: 박자 격자 프레임을 실곡으로 보려면 전체 앱과 세션 상태가 필요하다. 로컬 사용자 데이터 디렉터리에 곡 저장본이 있을 수 있으나, 전체 앱을 띄우면 운영자의 콘솔 설정을 읽으므로 설정 격리를 먼저 설계해야 한다. 리드 결정을 요청한다 (§6).

## 2. 전제 재측정

### 2.1 주장
origin/main 에 프리셋·확정 그룹·구간 색이 모두 채워진 실곡 타임라인이 있다.

### 2.2 근거

(a) 곡 큐 묶음 21개, 곡 8종 — 프리셋과 구간 색 [잼]
명령: git ls-files | grep -E 'bundle_cues\.json$' | python3 -I .moai/reports/t637/scan_bundles.py.txt
결과: 큐 8–24개 · 프리셋 이름 6–8종 (큐 7–23개에 position.stored 채움) · 구간 팔레트 2–3종.

(b) 확정 그룹(layer_mapping) — 추적 JSON 1,035개 중 비어 있지 않은 항목 87건 [잼]
명령: git ls-files -- '*.json' | grep '^\.moai/reports/' | python3 -I .moai/reports/t637/scan_layer_mapping.py.txt
결과: 파싱 1,035 · 해석 실패 1 · 비어 있지 않은 layer_mapping 87건. 예: t474/rehearsal_0719c95d/events.json 의 항목 6개 (KEY 1 · FOH 2 · BACK 3 · BLIND 13 · STROBE 14 · HAZE 15).

(c) 선택한 실곡 타임라인 [잼]
출처: .moai/reports/t474/rehearsal_0719c95d/events.json 의 events[3].timeline (해시는 payload-provenance.json 에 기록).
- lifecycle = approved · 구간 12 · layer_mapping 6 · 프리셋 이름 8종 (Ring In, Home, Vocal DSC, Center, Wall, Cross, Fan Out, Audience) · 구간 팔레트 hex 쌍 2종 (#0D33FF+#00E6FF, #0D33FF+#FFBF66).
- BPM 76.01: 같은 폴더 analysis.json 의 bpm_source = measured.
- 곡 제목 「Design Interview」: 인터뷰 기본값일 가능성 [추정]. 출처 미확인.

(d) 시험 데이터 대조 [잼]
ui/src/components/runbookServerPayload.json: 구간 8 · layer_mapping 0. 생성 스크립트 .moai/reports/t454/measure_payload.py 는 테스트용 계획(_plan(bpm=120.0, sections=…))을 쓴다. 리드의 「시험 데이터에 확정 그룹 없음」 판정과 일치 [옮김 → 이번에 재측정].

### 2.3 기준선
origin/main ce846ab6 의 추적 파일. 모든 명령은 이 워크트리에서 실행. 음원 파일은 저장소에 없다: git ls-files | grep -ciE '\.(mp3|wav|flac|m4a|ogg)$' → 0 [잼].

### 2.4 미측정
- 음원 원본의 해시 대조. analysis.json 의 sha256 값은 c3b78bbb739f… 로 기록만 했다.
- 곡 제목의 출처.

### 2.5 잔여 위험
- 「Design Interview」 제목과 실제 곡의 대응은 확인되지 않았다.
- 실기 콘솔 상태는 확인하지 않았다. 콘솔에 접촉하지 않았다.

## 3. 캡처

### 3.1 방법 [잼]
- 진입점: ui/runbook-preview.html (vite dev, 이 워크트리의 ui/, 빈 포트). UI 소스는 한 바이트도 고치지 않았다.
- 데이터: ui/src/components/runbookServerPayload.json 요청만 Playwright 로 가로채, §2.2(c) 실곡 타임라인으로 응답했다. 가로채기가 0회면 중단하도록 되어 있다. 두 폭 모두 1회씩 가로챘다.
- 시안: .moai/specs/SPEC-LDBEAT-001/design/ldbeat-runbook-ui-proposal-20261008.html (file URL).
- 실행: 워크트리 루트에서 uv run --with playwright python .moai/reports/t637/capture_t637.py.txt (Chrome 채널, 헤드리스). npm --prefix ui ci 선행.
- 프로세스: vite 는 자기 프로세스 그룹으로 띄우고 종료 후 포트 해제를 확인했다 (port_free_after_stop = true).
- 콘솔·웹소켓 접촉: 없음. 서버 미기동.

### 3.2 실행 로그 [잼] (run-log.json)
vite 준비 0.52초 · 가로채기 app-1450 1회 · app-1700 1회 · 페이지 오류 0 · 콘솔 오류 0 · 요청 실패 0 · 본문 글자 수 앱 4,794 / 시안 7,981 (두 폭 동일).

### 3.3 텍스트 대조 [잼] (dom-checks.json, 두 폭 값 동일)

| 문자열 | 앱(미리보기) | 시안 |
|---|---|---|
| 마디 | 12 | 52 |
| 구간 | 3 | 6 |
| 반영 대기 | 0 | 0 |
| 쓰기 잠김 | 0 | 0 |
| [미확인] | 0 | 0 |
| ▤ | 0 | 1 |
| 프리셋 | 0 | 15 |
| 빔 | 0 | 0 |
| 이름표 | 0 | 2 |
| KEY | 12 | 0 |
| FOH | 0 | 4 |
| BACK | 24 | 9 |
| BLIND | 0 | 5 |
| STROBE | 0 | 2 |
| HAZE | 0 | 0 |
| ★ | 0 | 9 |
| ⚠ | 0 | 7 |
| 페이드 | 1 | 9 |
| 딜레이 | 0 | 3 |
| 프로브 | 0 | 0 |
| AI | 0 | 6 |
| Ring In | 4 | 0 |
| 한눈에 | 0 | 4 |
| 무대 | 0 | 4 |
| Design Interview | 2 | 0 |

해석 주의: 두 페이지는 다른 화면이다. 앱에서 0 이라는 것은 「이 화면에 그 문자열이 없다」는 뜻이지 「기능이 없다」는 뜻이 아니다.

### 3.4 1450px 시각 확인 [잼] (app-1450.png)
- 화면 구성: 「오늘의 곡·큐 순서」 제목 · 곡 블록(Design Interview · 76.01 BPM · 12 cues) · TC_METHOD DERIVED 경고 · 타임라인(Intro 7마디 20.9초, Verse 1 4마디 12.6초, Verse 2 5마디 15.9초; 우측이 잘린 것으로 보임 [추정]) · 큐 시트 · 디렉터 타임라인 카드 · GATE(통과 13 · 실패 0) · 실행 런북(「확인된 곡·큐가 없습니다 — 콘솔이 아직 연결되지 않았거나 응답이 없을 수 있습니다」).
- 관찰 1: 페이드 값이 원자료 소수로 나온다. 예: 「3.1573333333333267s」 (PLAN CUE 1 카드). 실곡 데이터에서만 드러난 표시 형식 결함 후보. 시안에 대응 항목 없음.
- 관찰 2: 밝기 열에 KEY·BACK 값만 있고 FOH·BLIND·STROBE·HAZE 값은 없다 (DOM 0). 확정 그룹 6개 중 4개가 비어 보인다 → 데이터 부족 후보 [추정: 원자료의 밝기 키는 아직 열어 보지 않았다].
- 1700px: PNG 저장. 시각 대조는 하지 않았다 (텍스트 대조는 두 폭 동일).

## 4. 요소별 판정 (시안 본체 기준)

| 리드 목록 항목 [옮김] | 시안 | 앱(미리보기) | 판정 |
|---|---|---|---|
| ① 마디 표시의 구간 이름 | 상단 바 (문서 「마디」 52) | 상단 바 없음 · 큐 블록에 「마디」 12 | 보류 — 경로 부재 |
| ② 반영 대기 배지 | 「반영 대기」 문자열 0 | 0 | 보류 — 시안 문구와 대조 불가 |
| ③ 줄 이름 둘째 줄 | 박자 격자 소속 | 없음 | 보류 — 경로 부재 |
| ④ 눈금 구간 이름·경계선 | 박자 격자 소속 | 없음 | 보류 — 경로 부재 |
| ⑤ 한눈에·무대 높이 | 한눈에 4 · 무대 4 | 0 · 0 | 보류 — 경로 부재 |
| ⑥ 무대 이름표·빔 | 이름표 2 · 빔 0 | 0 · 0 | 보류 — 빔 문구가 양쪽 0 이라 측정 불가 |
| 곡 전체 지도 (★·⚠) | ★ 9 · ⚠ 7 | 0 · 0 | 보류 — 경로 부재 |
| 전환 화면 (페이드·딜레이) | 페이드 9 · 딜레이 3 | 1 · 0 | 보류 — 콘솔 연결 상태 의존 가능 |
| 프리셋 서랍 (▤) | ▤ 1 · 프리셋 15 | 0 · 0 | 보류 — 세션·콘솔 상태 의존 가능 |
| 쓰기 잠김 표지 | 0 | 0 | 보류 — 세션 상태 의존 |
| 프로브 패널 | 0 | 0 | 보류 |
| 하단 명령 입력·AI 제안 | AI 6 | 0 | 보류 |

미리보기 전용 관찰 (시안 대응 없음): 페이드 원자료 표시 (§3.4 관찰 1), 밝기 열의 그룹 누락 (관찰 2, 데이터 부족 후보 [추정]).

결론: 「같음 / 데이터 부족 / 구조 문제」 판정은 0건 확정이다. 보류 사유는 모두 「경로 부재」 또는 「세션 의존」이다.

## 5. 미측정 (Gaps)
1. 박자 격자 프레임 (시안 본체): 전체 앱 경로가 필요하다.
2. 가짜 콘솔·서버 미기동: 의뢰의 「가짜 콘솔로 띄워」를 이행하지 않았다. 콘솔 의존 요소(쓰기 잠김, 반영 대기, 딜레이 상태, 프리셋 서랍 상태)는 측정 불가.
3. 1700px 시각 대조: 텍스트 대조만 두 폭 동일 확인.
4. 음원 대조: 저장소에 음원이 없다 (추적 0). 로컬 사용자 데이터 디렉터리 「GrandMA3 Copilot」 이 있으나 이름만 확인했고 내용은 열지 않았다.
5. 컨텍스트 %: .moai/state/context-usage.json 의 session_id(3115fb23…)가 이 세션(dfdb65b9…)과 달라 값을 버렸다. 측정 불가.

## 6. 다음 카드 제안 (리드 결정)
- A (권장): 전체 앱 캡처. 서버(server/web/serve.py)와 가짜 콘솔(server/tests/fake_console.py)을 격리된 설정·데이터 디렉터리로 띄우고, 곡 저장본이나 음원을 세션에 올린 뒤 박자 격자를 캡처한다. 격리가 먼저다. 운영자 설정에 실기 콘솔 주소가 있으면 연결될 수 있다.
- B: 판정 범위를 축소한다. 시안 상단 프레임을 빼고, 미리보기 RunbookMode 와 시안 문서 중 대응되는 항목만 비교한다.

## 7. 재현 명령
- 전제: git ls-files | grep -E 'bundle_cues\.json$' | python3 -I .moai/reports/t637/scan_bundles.py.txt
- 전제: git ls-files -- '*.json' | grep '^\.moai/reports/' | python3 -I .moai/reports/t637/scan_layer_mapping.py.txt
- 캡처: uv run --with playwright python .moai/reports/t637/capture_t637.py.txt (워크트리 루트, npm --prefix ui ci 선행)
- 산출물: app-1450.png · app-1700.png · mockup-1450.png · mockup-1700.png · dom-checks.json · run-log.json · payload-provenance.json

## 8. 어긋난 절차 (정직하게 적는다)
- 워크트리를 git worktree add 로 만들었다. 레인 규약은 런처 진입을 요구한다. 세션이 이미 워크트리 안이라 EnterWorktree(name) 이 거절됐다. 커밋 전이라 잃은 것은 없다. 리드가 고아 트리로 정리해야 한다.
- 워크트리 디렉터리 이름을 카드 번호가 아니라 WT-runbook-recapture 로 두었다(배차서 값). 규약상 디렉터리는 카드 번호다.
- 가짜 콘솔을 띄우지 않았다 (§5-2).
- moai session list 는 실행하지 않았다. 주 체크아웃에 대해서는 git 명령을 쓰지 않았다.
