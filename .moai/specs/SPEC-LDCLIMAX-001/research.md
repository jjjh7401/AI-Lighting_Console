# SPEC-LDCLIMAX-001 조사 기록

카드 t425 착수 전 조사(2026-09-20). 기준: `origin/main` `2258048b`(fetch 완료,
`git rev-list --count --left-right origin/main...HEAD` = `14 0` — 로컬
`469e41b2` 는 origin 보다 14커밋 뒤졌다). 이 파일이 인용하는 모든 줄 번호는
`git show origin/main:<path>` 로 받은 내용 기준이다.

## 1. 정본 §6/§6.1 원문 (재확인, 카드 요약 아님)

`docs/proposals/song-structure-lighting-standard.md` 를 origin/main 에서
전량 재확인했다(카드가 쓴 요약이 아니라 원문).

- §6 표의 「절정의 지속 시간에 상한이 있다」 문단(508행 파일의 200행):
  **"최강 효과는 1~4박, 백색 플래시는 1~2박. 그 뒤 통제된 룩으로 복귀한다.
  규칙은 '최강 효과로 그 순간을 찍고 곧 돌아온다'."**
- §6.1(203-217행): 코러스 순간을 찍는 수단 일곱 — 밝기 히트 · 무빙 버스트 ·
  **색 스냅** · 백색 플래시 · 드롭 직전 짧은 블랙아웃 · 짧은 스트로브 ·
  빔·포지션 히트. [HARD] 한 큐에 하나만(밝기는 예외 — 밝기만 누적, 감독
  결정 2026-09-12). 뒤 회차는 앞 회차의 액센트 위에 얹지 않고 **갈아탄다**.
- §7(245-257행): [HARD] 곡 **안**에서는 반복이 미덕 — "코러스 1에 쓴 색과
  발리후는 이후 코러스에서 되돌아와야 한다." 곡 **사이**에서는 반복이 결함.
- §7.1(259-279행): 아껴두기 사다리 — chorus 1(기준) → chorus 2(+무빙 포지션
  전환) → chorus 3(+블라인더 또는 백색 플래시) → 앙코르(+스트로브 최초
  해제). [HARD] "여기까지 그대로"가 누적하는 것은 밝기뿐 — 표의 "더하는
  요소"는 액센트이면 앞 회차 액센트를 끄고 갈아탄다.

## 2. `AccentDecision` — 두 개의 병렬 파이프라인 (핵심 발견)

이 저장소에는 액센트를 다루는 **서로 독립된 두 파이프라인**이 있다. 카드가
전제한 "AccentDecision.hits 가 안 채워진다" 관찰은 사실이지만, 실제로 무대에
값을 내는 경로는 AccentDecision 을 아예 쓰지 않는 별도 경로다.

### 경로 A — 감독 인터뷰 (session.py → song_plan.py → song_cue_composer.py)

- `server/design/song_plan.py:286-303` `AccentDecision(accents: tuple[str,
  ...] = (), source: str = "standard", hits: tuple[Mapping[str, object],
  ...] = ())`.
- `hits` 필드는 **생산자가 전무하다**(`git grep -n "\.hits"` — 시험 파일의
  스키마 시험 두 건(`test_song_plan.py:106,112`)만 이 필드를 직접 넣어 보고,
  운영 코드(`server/design/*.py`, `server/web/session.py`) 어디도 `hits=`
  키워드로 생성하지 않는다). 카드의 관찰이 정확하다.
- `accents` 필드는 생산된다 — `server/web/session.py:713-737`
  `_accent_decision`/`_occurrence_accent_label` 이 문자열 라벨만 만든다:
  `"climax accent {color}"`, `"climax accent"`, `"white flash"`,
  `"moving position hit"`. 코러스·피날레의 **가운데 회차**(무빙 포지션)와
  **마지막 회차**(백색 플래시)에만 붙는다(`_occurrence_accent_label`,
  692-710행 — SPEC 은 아니고 카드 t403 의 일반화 구현).
- 이 `accents` 라벨의 **유일한 소비처**를 전수 확인했다(`git grep -n
  "\.accents\b" -- '*.py'`, 시험 제외): `song_cue_composer.py:619`
  (`ComposedCue.accents=decision.accent.accents`, 그대로 통과) 와
  `session.py:2546`(`"accents": list(decision.accent.accents)` — 리뷰
  화면(`apply_cue_sheet_section`) 용 JSON 필드). **명령을 만드는 코드 어디도
  이 필드를 읽지 않는다** — 카드의 "문자열 라벨일 뿐, fade/dimmer/fx 값을
  전혀 안 바꾼다" 주장은 이 경로에서 정확히 확인된다.
- `fade_override: float | None`(`song_plan.py:318`, 초 단위)는 실재하고
  `song_cue_composer.py:592-596` 가 `fade_seconds` 로 그대로 흘려보낸다 —
  단 오늘 이 필드를 채우는 유일한 생산자는 **감독이 명시적으로 준
  `fade_overrides: Mapping[int, float]`**(`session.py:1930,2105,3897,8793,
  9074`) 뿐이다. 액센트 종류에 따라 자동으로 0 을 넣는 경로는 없다.

### 경로 B — 확정 분석(업로드) → 찍는 액센트 사다리 (`server/looks/songcue.py`)

- `server/looks/songcue.py` 의 `build_songcue_bundle`(875행)은 `AccentDecision`
  을 **전혀 참조하지 않는다** — 입력은 `SongCueLookSelection`(룩+섹션)과
  리그 정보뿐이다.
- 이 경로가 SPEC-LDACCENT-001(방금 병합, PR #472, `origin/main 2258048b`)이
  고친 "찍는 액센트 사다리"다: `_MARKING_ACCENTS = (LADDER_ZOOM_PINCH,
  LADDER_BLINDER_OR_FLASH, LADDER_IRIS_PINCH)`(songcue.py:180-184),
  `LADDER_STROBE_HIT`(140행)는 `allow_strobe` 인자로 호출자가 켠 자리에서만
  네 번째 후보로 더해진다. 이 사다리는 **실제로 값을 바꾼다** —
  `_rung_applied`/`_stepped`(2447/2462행 근방)가 룩 자신의 `Zoom`/`Iris`
  속성값을 스텝하고, `_accent_fixture_commands`(2197행)가 블라인더·스트로브
  그룹에 별도 무대 명령을 낸다.
- **색 스냅은 이미 명시적으로 배제됐다**(songcue.py:109-110, 사다리 상수
  정의 바로 위 독스트링): *"색 스냅도 뺀다 — 정본 §7 이 「코러스 1의 색은
  되돌아와야 한다」고 못박으므로 지배색을 갈아치우는 것은 상승이 아니라
  위반이다."* 이 코드베이스 자신의 판단은, "색 스냅"을 §7.1 아껴두기
  사다리의 **에스컬레이션 칸**(회차마다 지배색을 새로 갈아치우는 것)으로
  읽었을 때의 결론이다 — 절정 한 순간에 이미 정해진(§7 이 요구하는
  '돌아오는') 색을 **즉시 전환**(페이드 0)으로 내는 것과는 다른 조작이다.
  이 구분이 §5 의 결정 근거다.

**결론**: 실제 무대 값을 바꾸는 것은 경로 B 뿐이다. 이 SPEC 은 경로 B(
`server/looks/songcue.py`, SPEC-LDACCENT-001 이 고친 그 파일)를 대상으로
한다 — §6 의 설계 근거(코러스별 색·조명)가 실제로 실리는 유일한 자리이기
때문이고, 경로 A(`AccentDecision`/`session.py`)는 오늘 표시 전용이라 이
SPEC 의 요구사항을 걸 대상이 아니다. 경로 A 를 같은 수준으로 끌어올리는
일은 별도 SPEC 의 범위다(§4 비목표).

## 3. 기존 인프라 — 이미 있는 것 (다시 짓지 않는다)

- **박자→초 변환**: `server/design/energy.py:221-233` `beats_to_seconds(beats:
  float, bpm: float) -> float` — `beats * (60.0 / bpm)`. 페이드-인 표
  (104-170행)가 이미 이 축으로 박 수를 초로 바꾼다. 이 SPEC 의 절정 지속시간
  상한(1~4박/1~2박)도 같은 함수로 변환한다 — 새 변환식을 짓지 않는다.
- **BPM 접근**: `server/design/profile.py:281,308` `MusicProfile.effective_bpm`
  (없으면 기본값으로 대체하는 **관대한** 버전). 그러나
  `cue_density.py:57`의 선행 규율(§4 참고) — "안 잰 템포로 계산한 마디는
  틀린 자리에 큐를 놓는다"는 이유로 `effective_bpm` 대신 **선언된 `bpm`
  자체**(`None` 허용)를 쓴다. 이 SPEC 도 같은 규율을 따른다(REQ-LDCLIMAX-009).
- **마디 경계 분할 선례**: `server/design/cue_density.py`(272행,
  `plan_cue_density`, 163행)가 이미 한 구간을 마디 경계에서 여러 큐로
  쪼갠다(`BAR_UNIT_BARS = 8`, 89행) — "구간 하나에 큐 하나"라는 오늘의 가정을
  이미 깬 선례다. 그러나 이 분할은 **회차·액센트 선택보다 먼저**
  일어난다(session.py:1896 `_split_sections_for_density` 호출은
  `_build_unified_song_plan` 의 회차 루프보다 앞선다) — 즉 "이 조각이
  실제로 최강 효과 액센트를 받을지"를 분할 시점에는 아직 모른다. 절정
  지속시간 상한을 이 분할 축으로 넣으려면 회차·액센트 선택을 분할 이전으로
  당겨야 하는데, 그러면 SPEC-LDACCENT-001 이 이미 겪은 "네 호출자 전부에
  컨텍스트를 빠짐없이 배선해야 한다"는 취약점을 분할 계층에서 또 만든다
  (§4 결정 근거).
- **큐 번호 타입 제약**: `server/looks/songcue.py` 의 `SongCueSectionBundle.
  cue_number: int`(504행 근방), `SongCueWithheldAccent.cue_number: int`
  (603행) — **정수 고정**이다(경로 A 의 `ComposedCue.cue_number: float`
  와 다르다, `song_cue_composer.py:601`). 복귀 큐를 끼워 넣으면 이 정수
  체계를 어떻게 유지할지가 §4 의 설계 결정 대상이다.

## 4. 결정 근거 — 이 SPEC 이 고른 기술적 방향 (기계적 근거 + 감독 결정 반영)

이 절은 원래 **엔지니어링 판단**(창작·비즈니스 판단과는 다른 층위)으로
작성했다 — 자동 회전 참여 여부 한 항목만 2026-09-20 감독 결정으로
덮어써졌다(§5). 다른 항목은 그대로 코드 근거만으로 유효하다.

- **색 스냅의 "실제 색 변경"은 §7 이 이미 돌아오라고 요구하는 색을 즉시
  전환(페이드 0)으로 내는 것으로 정의한다** — songcue.py:109-110 이 배제한
  "지배색을 새로 갈아치우는" 해석은 채택하지 않는다. 이유: 후자는 §7 [HARD]
  와 직접 충돌하고, 이미 이 코드베이스 자신이 그 충돌을 이유로 명시
  거부했다. 전자는 §7 과 충돌하지 않으면서 카드의 "진짜 fade=0 즉시 색
  전환"이라는 관찰 가능한 요구를 그대로 만족한다. **이 SPEC 은 이 결정에
  따라 songcue.py:109-110 의 배제 문면 자체도 개정한다**(plan.md M2,
  §B6) — 이 절의 판단이 코드 주석과 모순된 채로 남지 않는다.
- **자동 회전(사다리) 참여 여부 — 감독 결정(2026-09-20)으로 덮어써짐**:
  이 절의 원래 초안은 `allow_strobe` 와 같은 호출자-불투명 플래그로
  분리하고(`allow_color_snap: bool = False`, 기본값 거짓 — 오늘과 바이트
  동일), 참으로 켜는 시점·기준은 감독이 아직 정하지 않은 결정으로
  남겨 뒀다. **감독이 2026-09-20 에 직접 정했다** — color_snap 은 조건부
  스위치가 아니라 zoom_pinch/blinder_or_flash/iris_pinch/strobe_hit 와
  같은 자격의 정규 칸이고, 이 넷보다 우선하지 않으며, 대체도 병행도
  아닌 같은 회전의 한 후보다(§5). `disable_color_snap: bool = False`
  (기본값 = 끄지 않음, 즉 활성)만 첫 실기 콘솔 검증 세션까지의 임시
  안전판으로 남는다 — `allow_strobe` 의 패턴을 극성만 뒤집어 재사용한다.
- **절정 지속시간 상한은 사다리·분할 계층이 아니라 조립 결과(이미 완성된
  `SongCueBundle`) 위에 얹는 후처리 패스로 구현한다** — 마디-분할 선례
  (§3)를 분할 시점에서 재사용하려면 회차·액센트 확정을 분할보다 앞당겨야
  해서 SPEC-LDACCENT-001 이 겪은 다중 호출자 배선 취약점을 반복한다. 완성된
  번들 위에서 "이 큐가 `blinder_or_flash`/`strobe_hit` 를 실었는가"를
  보고 필요할 때만 복귀 큐를 추가하는 편이 파급 범위가 좁고 테스트
  경계가 명확하다(§4 상세는 design.md).
- **상한 대상은 `blinder_or_flash`(§6 "백색 플래시" 행, 2박)와
  `strobe_hit`(§6 "최강 효과" 일반 행, 4박)로 좁힌다** — 이 둘만이 룩
  자신의 값이 아니라 **별도 고정장비 그룹**을 켜는 칸(songcue.py:117-122,
  186-191)이라, §6 이 말하는 "통제된 룩에서 벗어난 극단 상태"에 해당한다.
  `zoom_pinch`/`iris_pinch`/`color_snap`은 이 룩 자신의 D-레벨 예산 안에서
  움직이는 값이라 §6 표의 밝기 상한이 이미 그 범위를 규율한다 — 별도
  지속시간 상한을 또 얹는 것은 이 SPEC 의 범위를 넘는 재설계다(§4 비목표).

## 5. 감독 결정 기록 (2026-09-20 해소)

카드 t425 본문이 명시한 미해결 질문("감독 확인 필요: 어느 수단을 기본으로
쓸지")은 감독 확인으로 해소됐다. 답: color_snap 은 `disable_color_snap=True`
로 명시적으로 끄지 않는 한 항상 회전 후보이고(전 곡 공통, 조건부 아님),
기존 `_MARKING_ACCENTS` 사다리(줌→블라인더→아이리스[→스트로브]) **뒤,
맨 끝**에 위치하며(이 넷보다 우선하지 않는다), 그 사다리를 대체하지도
병행하지도 않는다 — 같은 회전 안의 한 후보다. §4 가 이미 기계적 근거로
제안했던 "맨 끝" 배치가 감독의 연출 판단으로 그대로 확정됐다 — 다만
그 배치를 지지하는 스위치 모델(`allow_color_snap`, 기본값 거짓의 항상
꺼짐)은 감독 결정으로 폐기되고, 반대 극성의 임시 안전판
(`disable_color_snap`, 기본값 거짓 = 끄지 않음)으로 대체됐다. 상세는
plan.md §NC(해소 기록)와 spec.md §2/§5 가 담당한다.
