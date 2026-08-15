# SPEC-COPILOT-SONGSTD-001 — 구현 계획

## 모듈 배치

```
server/design/                # 신설 — 표준 엔진 (콘솔 무접촉, 순수)
  profile.py                  # MusicProfile, 통합 무드 사전 (R1)
  rig.py                      # RigProfile — 인벤토리/층/기하/스케일 (R1b)
  energy.py                   # D→축 예산 함수, 박↔초 환산, 장르 오버레이 (R2)
  lint.py                     # L1~L14 (R3)
  interview.py                # 연출 인터뷰 5문항 — 제안 유도·오버라이드 (R1c)
server/audio/                 # 신설 — M4 (librosa 지연 import)
  analyze.py                  # BPM/온셋/RMS→D후보/경계 (DSP)
server/spatial/position_cuesheet.py   # M2 — energy.py 소비로 확장
server/web/session.py         # 어휘 확장 (BPM·장르 파싱, M4 업로드 어휘)
```

- 기존 `position_moods.py`는 통합 사전(profile.py)의 포지션 열로 흡수하되
  하위호환 유지 (기존 핸들러·테스트 무파손). 키워드 무겹침 계약은 통합
  사전 전체로 확장.
- 콘솔 문법 신규 도입 없음 — M1~M3은 CUETIME-001 검증 문법 위에서만.

## M1 — 표준 엔진 코어 (순수 함수)

1. `profile.py`: `MusicProfile(bpm, meter, genre, key_mode, concept,
   palette)`, `resolve_section(mood_text, profile) -> (D, color_tendency,
   position_candidates)` + 우선순위 M2. 컨셉 시드 표(우주/네온/빈티지 등
   초기 6종).
2. `rig.py`: `RigProfile` + `build_rig_profile(patch, groups, coords,
   declared_layers=None)` — RG5 층 결정 순서(선언>그룹 이름 휴리스틱>
   단일층 축퇴), RG6 예산 비례. 린트·예산 함수는 RigProfile을 인자로
   받아 규칙을 조건화 (RG1 비활성 노트 포함).
3. `energy.py`: `axis_budget(D, profile, rig) -> AxisBudget(dimmer_pct,
   fade_beats, position_width, saturation, fx_axes, fx_speed_mult)` +
   `beats_to_seconds`. §3 표를 코드 상수로, §7 장르 오버레이.
4. `lint.py`: `lint_sheet(sheet, profile, rig) -> tuple[LintFinding, ...]`.
5. 유닛: 사전/리그/예산/린트 각각. Seq 114 실측 결함(전 큐 100%)을 L2
   위반 고정 케이스로, 단일층 리그의 L6/L7 비활성 케이스 포함.

## M2 — 포지션+디머 표준 시트 (라이브 검증)

1. `position_cuesheet.build_position_cue_sheet`에 `profile` 인자 추가:
   디머 = D예산(층은 아직 키층 단일 — 백층은 M3 컬러와 함께), 페이드 =
   `beats_to_seconds(fade_beats)`, G2 비대칭.
2. 세션 어휘: "…, BPM 128, 메탈:" 파싱. 린트 결과를 응답 텍스트에 병기.
3. 라이브: 동일 메탈 12구간 → 새 시퀀스(예: 115). Seq 114 대비 —
   구간별 3D 밝기 합 계단 확인, D2 페이드(1마디) vs D5(스냅) 프레임 수
   차이 측정. 완료 후 114 삭제 여부는 운영자 판단.

## M3 — 컬러 통합 (라이브 검증)

1. 팔레트 자료형 + C1~C5 검증. 컨셉/장르 시드 → 카드 확인 흐름.
2. 큐 번들 = 프리셋 리콜 + `Attribute 'ColorRGB_*' At v` 라인(한 줄 체이닝,
   dedupe 유일성) + [검증된 페이저: 밀도 예산 내] → Store CueFade →
   ClearAll. `/Merge` 금지 — 페이저는 항상 같은 프로그래머 상태에서 생성.
3. 라이브: 페이저 큐 두 프레임 diff(구동), 프레임 색 히스토그램으로
   팔레트 준수 확인.

## M4 — 오디오 분석 파이프라인

1. 의존성: `librosa`, `numpy`, `soundfile`을 프로젝트에 추가하되
   `server/audio/analyze.py`에서 **지연 import** — 서버 기동 경로와 기존
   테스트에 무영향 (feasibility에서 격리 venv로 확인한 버전 고정).
2. 업로드: Vectorworks 패턴(8MiB, base64) 복제 — `song_audio_upload`
   메시지 + 세션 어휘 "이 곡 분석해서 조명 만들어줘".
3. 흐름: DSP 측정 → [옵션] LLM 무드·장르 제안(오디오 전송은 후속 —
   1차는 측정 결과 텍스트 기반 제안) → 질문 카드(구간표+D+장르) →
   R4/R5 시트.
4. 회귀: feasibility의 합성 트랙 생성기를 테스트 픽스처로 이식 —
   BPM ≤3%, 경계 ±1s, D 일치 어서션.
5. 라이브: 실제 곡 1개 업로드 → 카드 → 시트 → 콘솔 재생 3D 확인.

## 검증 사이클 (각 M 공통 — CUETIME-001 관례)

구현 → 스코프 pytest + ruff → 서버 재시작 → 앱 UI 라이브(운영자 플로우로
재생 — Go 횟수 함정 재발 방지) → 3D 프레임 정량(Otsu·밝기 합·히스토그램)
→ 함정 스킬 기록 → 커밋·푸시.

## 리스크

- 무드 사전 확장 시 키워드 겹침 → 테스트가 전체 무겹침을 고정.
- M3 페이저+컬러 동시 저장의 dedupe(값 라인 유일성) — 선택 접두 필수.
- librosa 설치 무게(numpy 체인) — 지연 import + CI 시간 관찰, 필요시
  분석기를 별도 프로세스로 격리하는 후퇴선.
- LLM 오디오 전송(M4 옵션)은 어댑터 확장 필요 — 1차 범위에서 제외 가능.
