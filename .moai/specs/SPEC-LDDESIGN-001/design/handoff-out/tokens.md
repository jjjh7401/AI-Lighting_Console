> **사전 핸드오프 기록(발신 시점, 2026-09-22 이전) — 현재 정본 아님.** 이 문서는 Claude Design에 보낸 발신 브리프다. 디자인이 돌아온 뒤 `src/DESIGN.md`가 UI 정본이 됐고, 이 문서의 전제(M7 = 메인 화면 확장) 중 일부는 틀렸다(M7은 별도 런북 모드 페이지). 참고용 역사 기록으로 보존한다 — 최신 설계는 `../design.md`와 `../received-design.md`를 보라.

# M7 다크 테마 토큰 — 실측·신규 구분

측정 위치: `scratchpad/wt-main/ui/src/styles.css`(2026-09-22 실측, 3,734행).
표기 `측정-기존`은 이미 앱에 있는 값 그대로 쓰는 토큰, `신규-설계필요`는
M7이 처음 필요로 하는 값 — Claude Design이 §브리프 §6 팔레트 규율(비유
금지, 색만으로 상태 구분 금지)을 지켜 골라야 하는 토큰이다.

## 측정-기존 (그대로 쓴다 — 재정의·변형 금지)

| 토큰 | 값 | 출처(파일:행) |
|---|---|---|
| `--bg` | `#14161a` | `styles.css:3` |
| `--panel` | `#1e2128` | `styles.css:4` |
| `--text` | `#e8eaed` | `styles.css:5` |
| `--muted` | `#9aa0a6` | `styles.css:6` |
| `--accent` | `#4f8cff` | `styles.css:7` |
| `--ok` | `#3fb950` | `styles.css:8` |
| `--warn` | `#d29922` | `styles.css:9` |
| `--bad` | `#f85149` | `styles.css:10` |
| `--live-amber` | `#ffb02e` | `styles.css:17`(실행 중 풀 타일 전용, 다른 용도 재사용 금지 — 주석 명시) |
| `--track`(runbook) | `#7d8ea6` | `styles.css:1559` |
| `--timeline-line` | `#344256` | `styles.css:1720` |
| `--energy`(D1~D3) | `#5c7fa8` | `styles.css:1861` |
| `--energy`(D4) | `#d67d4d` | `styles.css:1869` |
| `--energy`(D5) | `#f04f5d` | `styles.css:1870` |
| `--cst-row-h` | `28px` | `styles.css:3682` |
| `--cst-head-h` | `30px` | `styles.css:3683` |
| `--pool-accent`(그룹) | `#2f6db4` | `styles.css:1220` |
| `--pool-accent`(프리셋풀) | `#1d8a80` | `styles.css:1224` |
| `--pool-accent`(매크로) | `#b03535` | `styles.css:1228` |
| `--pool-accent`(플러그인) | `#a53a9b` | `styles.css:1232` |
| `--pool-accent`(실행기) | `#a08428` | `styles.css:1236` |

## 신규-설계필요 (M7이 새로 정의해야 함)

Claude Design이 값을 제안하는 항목. §브리프 팔레트 규율: 기존 토큰과
색상환에서 충돌하지 않게(특히 `--ok`/`--warn`/`--bad`와 헷갈리지 않게),
그리고 모든 상태는 아이콘/모양과 함께 쓰인다는 전제로 고른다.

| 항목 | 용도 | 형태 요구 (REQ-근거) |
|---|---|---|
| 컨셉 패널 서피스 색 | `ConceptPanel.tsx` 배경/테두리 | `--panel`과 구별되되 과하게 튀지 않아야 함(패널이 접혀 있을 때 5블록 사이에서 존재감은 있되 시선을 뺏지 않음) — REQ-079 |
| 컨셉 패널 강조선/포인트 색 | 패널 헤더의 "이 곡의 연출" 라벨, 펼침 화살표 | 클릭 가능함을 암시하는 색 + 커서 포인터 병행 — REQ-079 |
| 근거 등급(evidence) 배지 4종 | `verified` / `practitioner_pattern` / `designed_rule` / `director` | 색 4종 + **각기 다른 라벨 텍스트**(REQ-071: "이 곡에서 검증했다는 뜻이 아님"을 UI가 명시해야 하므로 색만으로 절대 구분 불가) |
| GATE 통과/경고 표시 | 상태줄 GATE 요약 + 펼침 상세표 | PASS(`--ok`+체크 아이콘) / WARN(`--warn`+느낌표) / FAIL(`--bad`+X) / N/A(중립색+"해당없음" 텍스트) 4상태 — REQ-084 |
| `Q###` 배지 | 타임라인 Q줄 · CUE SHEET 첫 열 · PLAN CUE 카드 | 세 위치에서 동일 폰트(고정폭 권장, 기존 CUE SHEET가 `ui-monospace`류를 씀)·동일 색으로 "같은 값"임을 시각적으로 확인 가능해야 함 — REQ-083, AC-019 |
| 원샷 점(dot) 색 | 타임라인 dot row, 원샷 종류별 | 7종 원샷 어휘(REQ-007) 중 실제 발생하는 종류만 구분 — White hit/Blinder hit/Dimmer bump/짧은 Strobe 등, 색 + 호버 시 텍스트 라벨 |
| Mark 지점 마커 | 타임라인 dot row 위 Mark 라벨 | 원샷 점과 형태로 구별(점 vs 다른 모양), MIB `mark` 판정에서만 등장 — REQ-081, REQ-062 |
| Track 예외 값 강조 | CUE SHEET `Track 예외` 열 | 기본값(`Track`, 빈 칸)과 예외값(`Block`/`Cue Only`/`Release`) 시각 구분 — REQ-082 |

## 개수 요약

- 측정-기존: 18개 토큰(색 15 + 크기 2 + 계열 1).
- 신규-설계필요: 8개 항목(그 중 다색 배지 3개는 각각 4종 값을 가짐 —
  근거 등급 4 + GATE 4 = 총 개별 색상 값으로는 최소 8+2+4+4 = 대략
  18개 색상 결정이 더 필요하다).

감독 확인 필요: 원샷 7종(REQ-007) 전부에 각각 다른 점 색을 줄지, 아니면
"타격성"(Kick/Snare/Cymbal accent, White hit, Blinder hit)과 "전환성"
(Dimmer bump, Color bump, Position snap, 짧은 Strobe)으로 2계열만 나눌지는
이 문서에서 결정하지 않는다 — Claude Design 산출물을 보고 감독이 정한다.
