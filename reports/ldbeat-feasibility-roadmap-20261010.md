# 런북 박자 배치 — 되는 것·안 되는 것·SPEC 진행안 (md 요약판)

- 2026-10-10 · 리드 · 사람용 본문 `reports/ldbeat-feasibility-roadmap-20261010.html`
- 감독 요청 2026-10-10: 「되는 것과 안 되는 것, 그리고 앞으로 해야 할 것을 스펙을 만들어서 진행할 수 있도록 정리」
- 기준: origin/main `88ecfb9d` (PR #569 머지 직후)

## 결론
- 화면(런북 UI 시안)은 전부 만들 수 있다. 막는 기술 장벽 없음.
- 화면을 채울 내용 중 「곡을 마디 단위로 분석」「역할×마디 배치를 앱이 스스로 짜기」는 지금 앱에 없다 → 새 SPEC 둘.
- 콘솔로 보내는 쪽은 절반 확인. 남은 확인은 SPEC-LDBEAT-001 M1 프로브로.
- 진행 순서: ① LDBEAT(손으로 짠 LOVE ATTACK 배치를 첫 데이터로 화면+송신 완성) → ② 마디 분석 SPEC → ③ 자동 배치 SPEC.

## 되는 것 (잰 것)
| 항목 | 근거 |
|---|---|
| 장비 86대 위치·회전 읽기(10.3초, 일괄 props) | t525 `.moai/reports/t525/verdict.md` r1 |
| 장비 이름 → 역할 추정 + 감독 확인 | `server/design/rig.py` RIG_LAYER_ROLES |
| 시퀀스·큐 콘솔 쓰기, 타임코드에 시퀀스 1개 붙이기 | `server/looks/songcue.py:634-641` |
| 타임코드 트랙 2개 실기 | t516 verdict |
| Goto Cue 1 Sequence N · Off Sequence | t520 verdict §16-2 |
| 페이저 + 스피드마스터 15(112.35 BPM) + Measure | t516·t519 |
| 효과 프리셋 저장 `Store Preset p.n /Universal` | t513 |
| 승인=송신 바이트 대조 | `.moai/reports/t512/approval_vs_sent.py` (리포트 스크립트 — 앱 경로 승격 필요) |
| 콘솔 이름 영문화(한글 제거) | `songcue.py:683` `_ascii_label` |
| 곡 BPM·구간(벌스·후렴) | `server/audio/analyze.py` |
| 화면 동작(타임라인·편집창·재생·음악 동기) | 시안 `reports/ldbeat-runbook-ui-proposal-20261008.html` 에서 동작 |

## 일부만 되는 것
| 항목 | 지금 | 막힌 이유 / 고칠 것 |
|---|---|---|
| 그룹 소속 | 그룹당 앞 2대 | 응답기 `max_prop_value=240`(`console/lua/copilot_responder.lua:43`) — 긴 값 나눠 읽기 추가 |
| 무대 앞뒤(객석 방향) | 이름으로 추정 | 콘솔에서 읽는 방법 미확인 |
| 앱 재생 경계 | manual_go·trig_time 만 | `server/director/emit.py:51` 이 타임코드 모드 거부 → 박자 전용 새 에미터(기존은 그대로) |

## 없는 것 (새로 만들어야 함)
1. 마디 단위 곡 분석 — `analyze.py` 비트 시각은 BPM 계산에만 쓰고 저장 안 함, 다운비트 생산자 0 (LDRHYTHM REQ-012 재확인)
2. 역할×마디 배치 자동 생성 — 지금 LOVE ATTACK 배치는 리드 손작업(`reports/effect-arrangement-rules-20261007.md` §4)
3. 역할별 시퀀스 여러 개 + 타임코드 트랙 여러 개 에미터 — songcue 는 시퀀스 1개를 타임코드 1개에
4. 역할×마디 데이터 저장 칸 — 저장소 3종(SongTimelineStore·TimelineDraftHistory·SongTimelineLibrary) 모두 없음
5. 마디·역할 문장 편집 — `cue_sheet_edit.py` 는 큐 단위만
6. AI 제안(색 프리셋 생성·격자 제안 → 「적용」) — 효과(find_fx·compose_fx)·위치(pointing.py)만 있음
7. 프리셋 참조 큐 생성 흐름(앱이 프리셋 만들고 큐가 번호로 참조)

## 콘솔에서 아직 안 잰 것 (LDBEAT M1 프로브)
타임코드 트랙 3개 이상(6개 필요) · Goto 2번 이후 큐·여러 시퀀스 동시 · 프리셋 고치면 참조 큐가 따라가는지 · 효과 프리셋이 스피드마스터 15/Measure 를 지니는지 · 위치 프리셋 위 상대값 움직임 · 타임코드 중간부터 재생 · 큐 하나 그룹 하나 + Step 2 · 같은 그룹 두 시퀀스 분담 · circle·발리후

## SPEC 진행안
| 순서 | SPEC | 상태 | 하는 일 | 끝나면 감독이 보는 것 |
|---|---|---|---|---|
| 1 | SPEC-LDBEAT-001 (개정) | draft(plan 머지 #568) | M1 콘솔 프로브+응답기 긴 값 읽기 → M2 격자 화면·저장 → M3 마디·역할 편집 → M4 박자 에미터(승인=송신) → M5·M6 | LOVE ATTACK 0~25마디를 런북에서 보고·고치고·콘솔로 보내기 |
| 2 | SPEC-LDBARMAP-001 (새) | 없음 | 비트·다운비트·마디 경계·마디별 변화(킥·드롭·빌드) 검출, 저장 | 새 곡을 넣으면 마디 지도가 나옴(LOVE ATTACK 손 분석과 대조) |
| 3 | SPEC-LDARRANGE-001 (새) | 없음 | 확정 배치 규칙 + 마디 지도 + 무대 패치로 역할×마디 초안 생성, AI 제안 카드 | 새 곡의 배치 초안이 런북에 자동으로 뜸 |

LDBEAT 개정에 넣을 것: 프리셋 방식(색·위치·효과 풀, 밝기 값/디머 프리셋) · 편집 세 길(고르기·문장·AI 제안→「적용」) · 영문 콘솔 이름 · UI 결정(타임라인 접기, 전환 버튼, 우측 편집창, 2D 무대, 재생·±10초) · 무대는 콘솔 패치에서 그림(t525) · 응답기 긴 값 나눠 읽기 · REQ-013 의 songcue.py 언급.

## 감독 결정 필요
1. 진행 순서(LDBEAT 먼저, 손 데이터로) 동의
2. 박자 전용 새 에미터(기존 emit.py 유지) — 권고: 새로
3. 앱이 만든 이 곡 프리셋·시퀀스 덮어쓰기 허용 — 권고: 앱이 만든 번호대만
4. AI 제안은 항상 「적용」을 거침 — 권고: 예
5. 미리보기(Goto·Off) 승인은 시작할 때 한 번 — 권고: 예

## 바로 다음
1. 결정 1~5 확인 → 2. 레인에 LDBEAT 개정 카드(plan 만) → 3. plan-audit → 4. 착수 승인 → M1 프로브(콘솔 쓰기는 「실행」 뒤)
