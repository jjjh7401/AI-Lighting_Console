# SPEC-LDCLIMAX-001 구현 계획

## §NC. 감독 결정 기록 (2026-09-20 해소)

과거의 미해결 질문 마커("액센트 회전 기본값 — 색 스냅이 일곱 수단 중
언제·어느 순위로 자동 선택되는가")는 감독 확인으로 해소됐다. 카드 t425
본문의 질문("감독 확인 필요: 어느 수단을 기본으로 쓸지")에 대한 답:

1. **어느 곡/세트 위치에서 켜는가** — 조건부가 아니다. color_snap 은
   `disable_color_snap=True` 로 명시적으로 끄지 않는 한 **항상** 회전
   후보다. 전 곡 공통이고 장르·세트 위치별 분기는 두지 않는다.
2. **`_MARKING_ACCENTS` 기존 칸 사이에서의 우선순위** — **맨 뒤**(줌→
   블라인더→아이리스[→스트로브] 뒤, 기존 네 칸보다 우선하지 않는다).
   design.md §1.1 의 "맨 뒤" 잠정안이 그대로 확정됐다 — 다만 근거는
   "엔지니어링 최소 침습"이 아니라 **감독이 직접 정한 연출 우선순위**다.
3. **대체하는지 병행하는지** — 대체도 병행도 아니다. 같은 회전 안의 한
   후보다(큐당 찍는 액센트 하나 규율, REQ-005 는 그대로 유지). 별도
   발생 조건이나 병렬 트랙을 두지 않는다.

**바뀐 것 — `allow_color_snap`(기본값 거짓의 항상-꺼짐 스위치) 모델은
폐기한다.** 이 모델은 "색 스냅은 기본적으로 꺼진 특수 기능"을 전제했는데,
감독 결정은 그 전제 자체를 뒤집는다 — color_snap 은 zoom_pinch/
blinder_or_flash/iris_pinch/strobe_hit 와 **같은 자격**의 정규 칸이다.
대신 `disable_color_snap: bool = False`(기본값 = 끄지 않음, 즉 활성)를
남긴다 — 이것은 자동 회전을 켜는 스위치가 아니라, 첫 실기 콘솔 검증
세션까지의 **임시 킬스위치**다(REQ-012, spec.md §2/§3.3). 스코프 결정
(색 스냅 + 절정 지속시간 상한 둘 다 이 SPEC 하나에 유지, 분리하지 않음)
도 감독이 재확인했다 — 변경 없음.

**연쇄 효과 — 이 결정이 바꾸는 것들**:

- REQ-001(spec.md §3.1)이 `Where allow_color_snap=True` 게이트에서
  무조건 포함(`Ubiquitous`)으로 바뀐다.
- 새 REQ-012(spec.md §3.3)가 `disable_color_snap` 안전판을 정의한다.
- `songcue.py:109-110` 의 색 스냅 배제 독스트링은 **실제로 개정**한다
  (§F M2) — 프로즈로만 "다른 정의를 쓴다"고 적고 원문을 그대로 두면
  코드 주석과 동작이 모순된다.
- **기존 골든 시험의 바이트 동일성 재검토** — `allow_color_snap` 기본값이
  꺼져 있어서 안전했던 이전 판과 달리, color_snap 이 이제 무조건
  후보라 골든 픽스처가 실제로 바이트 동일한지는 **그 픽스처의 색
  구성에 달렸다**. `origin/main`(`2258048b`, SPEC-LDACCENT-001 PR #472
  병합 직후) 실측:
  - `TestHeadroomCaseIsUntouched.test_seven_choruses_with_ample_headroom_
    are_byte_identical_before_and_after`(`test_songcue_accent_ladder_
    t382.py:265`) — 이 픽스처의 룩(`_single_axis_look`)은 매 회차 동일한
    `ColorRGB_R/G/B=(72,100,0)`을 쓴다(파일 60-70행 근방, 색이 인자화돼
    있지 않다). 직전 저장 큐와 색이 항상 같으므로 REQ-004(무영향 배제)가
    color_snap 을 매 회차 걸러낸다 — **바이트 동일 유지**(REQ-004 가 지켜
    주는 것이지, 스위치가 꺼져서가 아니다).
  - `test_songcue_accent_fixture.py`(`_look` 헬퍼, 41-53행 근방)와
    `test_songcue_ladder.py` 의 `_look`/실기 라이브러리 픽스처들도 같은
    사유로 회차 간 색이 고정이다 — `map_sections_to_looks` 자신의 §7
    "되돌아오는 룩" 우선순위(763-803행 근방, `first_of_label`)가 반복
    라벨에 같은 룩(같은 색)을 재사용하도록 이미 편향돼 있어, 두 계층
    (룩 선택 + 액센트 회전) 모두 색 변화가 없는 방향으로 겹친다. 위
    세 파일이 인용하는 골든/회귀 시험은 이 근거로 바이트 동일 유지를
    기대한다 — 실제 확인은 M4 에서 재실행으로 한다(추측이 아니라
    실행 결과로 닫는다).
  - **바이트 동일하지 **않을** 것 — `test_every_ladder_rung_is_classified`
    (`test_songcue_ladder.py:470`, 클래스 `TestOneMarkingAccentPerCue`)**.
    이 시험은 픽스처 실행이 아니라 순수 상수 단언이다:
    `assert set(LADDER_RUNGS) == {LADDER_DIMMER_HIT, *self._MARKING}`
    (`_MARKING = (zoom_pinch, iris_pinch, blinder_or_flash)`). color_snap
    이 strobe 와 반대 극성(기본 활성)이라 `LADDER_RUNGS`(zoom/iris/
    blinder 처럼 "기본으로 도는 칸"의 집합, strobe 는 제외)에 포함하는
    것이 일관적이다(§B7) — 포함하면 이 시험은 **의도적으로 RED**가
    되고, `_MARKING` 튜플에 `LADDER_COLOR_SNAP` 을 더하는 갱신이
    필요하다. 이 시험 자신의 독스트링("새 칸이 생기면 여기가 먼저
    빨개진다")이 정확히 이 상황을 잡도록 설계됐다 — 갱신 누락이 아니라
    **설계대로 작동하는 조기 경보**다.

## §A. 컨텍스트

- **대상 파일**: `server/looks/songcue.py`(핵심 로직). 보조: `server/tests/
  test_songcue_ladder.py`, `server/tests/test_songcue_accent_ladder_t382.py`
  (회귀 확인), `server/tests/test_songcue_accent_fixture.py`(회귀 확인),
  `server/design/energy.py`(읽기 전용 — `beats_to_seconds` 재사용).
- **⚠️ 착수 전 필수 동기화**: 이 SPEC 을 작성한 시점의 로컬 checkout(`HEAD
  469e41b2`)은 `origin/main`(`2258048b`)보다 **14커밋 뒤져 있다** — 그중
  SPEC-LDACCENT-001(PR #472)이 이 SPEC 이 인용하는 `_marking_accents`/
  `_MARKING_ACCENTS`/`_accent_is_effective`/`SongCueWithheldAccent` 를
  직접 만들었다. run-phase 착수 전에 로컬 트리를 `origin/main` 과
  동기화해야 한다(`git fetch origin main && git rev-list --count
  --left-right origin/main...HEAD` → `0 N` 확인, `agent-common-protocol.md`
  § Pre-Spawn Sync Check 절차 그대로).
- **선행 완료 작업**: SPEC-LDACCENT-001 이 찍는 액센트 사다리의 무영향-칸
  필터링과 유보 보고 패턴을 이미 만들었다 — 이 SPEC 은 그 위에 새 칸
  (`color_snap`)과 새 후처리 패스(절정 지속시간 상한)를 얹는다.
- **두 파이프라인 경계**: `research.md §2` 가 확인한 대로, 이 SPEC 은
  경로 B(`server/looks/songcue.py`)만 건드린다. 경로 A(`AccentDecision`,
  `server/web/session.py`)는 무대 명령을 만들지 않으므로 이 SPEC 의
  REQ 대상이 아니다 — 착수 시 이 경계를 벗어나는 유혹(예: "김에 session.py
  도 고치자")을 거절한다(스코프 규율, Multi-File Decomposition 과 별개로
  파일 경계 자체를 지킨다).

## §B. 알려진 이슈

- **B1 — 큐 번호 정수 제약**: `SongCueSectionBundle.cue_number: int` 는
  정수 고정이다(경로 A 의 `ComposedCue.cue_number: float` 와 다르다).
  복귀 큐를 끼우면 후속 큐 전량의 번호를 1씩 밀어야 한다 — 소수점 큐
  번호를 새로 도입하지 않는다(design.md §1.2). `_cue_names` 가 이 재번호
  뒤에도 이름을 정확히 다시 매기는지 M3 에서 실측 확인이 필요하다(오늘
  코드에서 이름 재부여 시점·조건을 이 조사 단계에서 완전히 추적하지
  못했다 — run-phase 첫 조사 항목).
- **B2 — 페이드 필드명 미확정**: 경로 B(`SongCueSectionBundle` 계열)의
  개별 필드 목록에서 "이 큐의 페이드 시간"에 해당하는 정확한 필드명을
  이 조사에서 확정하지 못했다(경로 A 는 `ComposedCue.fade_seconds` 로
  명확하지만, 경로 B 는 `commands`(콘솔 명령 문자열 튜플) 안에 페이드가
  인코딩돼 있을 가능성이 있다 — `_stepped`/`_rung_applied` 가 만드는
  명령 문자열의 정확한 문법을 M2 착수 시 먼저 읽어야 한다). REQ-003
  (색 스냅 페이드=0 강제)의 구현 위치가 이 확인에 달려 있다.
- **B3 — `_marking_accents` 의 직접 호출자 네 곳**(SPEC-LDACCENT-001 §B1
  이 이미 정정한 목록 그대로 재확인): `_max_climb`·`_finalize_marking_
  accents`·`_climb_rungs`·`_ensure_marking_accent`. `disable_color_snap`
  을 `allow_strobe` 와 나란히 추가하면 이 네 곳 전부에 새 인자를 배선해야
  한다 — 하나라도 빠뜨리면 그 호출 경로에서만 색 스냅이 조용히 안 나오는
  결함이 된다(SPEC-LDACCENT-001 이 이미 겪은 실패 형태).
- **B4 — 복귀 큐의 "기준 값" 재사용**: design.md §2.1 6번 — 복귀 큐는
  새 룩을 계산하지 않고 절정 큐 자신이 이미 들고 있던 사다리-오르기-전
  값을 재방출한다고 설계했다. `_rung_applied` 가 그 "오르기 전" 값을
  어디까지 보존하는지(스텝 함수가 원본을 변형 없이 돌려주는지, 별도
  복사가 필요한지)는 M3 구현 시 확인해야 한다.
- **B5 — `_accent_is_effective` 의 판정 축은 오늘 딱 둘뿐이다**: 축-보유
  (`_MARKING_ACCENT_AXIS.get(rung)`, 줌·아이리스)와 그룹-보유
  (`_ACCENT_FIXTURE_ROLE.get(rung)`, 블라인더·스트로브) — 이 둘 다
  `None` 이면 `SongCueBundleError(f"unknown ladder rung: {rung!r}")`
  를 던지는 닫힌 if/elif 구조다(`songcue.py:204-221`). color_snap 은
  어느 쪽도 아니다 — **색 비교**(직전 저장 큐의 색과 다른가, §7 집합
  안인가)라는 **셋째 판정 축**이 필요하다(REQ-002/004). M2 는 이
  dispatch 자체를 확장해야 한다 — 기존 두 축에 억지로 끼워 맞추면
  안 된다.
- **B6 — `songcue.py:109-110` 배제 독스트링은 실제로 고친다**: 프로즈
  (spec.md/design.md)로 "다른 정의를 쓴다"고 적는 것만으로는 코드
  주석과 동작이 모순된 채로 남는다. M2 는 이 두 줄("색 스냅도 뺀다 —
  정본 §7 이 「코러스 1의 색은 되돌아와야 한다」고 못박으므로 지배색을
  갈아치우는 것은 상승이 아니라 위반이다")을 이 SPEC 의 정의(즉시
  전환된 §7 색은 위반이 아니다)로 교체하고 SPEC-LDCLIMAX-001 을
  인용한다.
- **B7 — `LADDER_RUNGS` 포함 여부와 `test_every_ladder_rung_is_classified`
  갱신**: `LADDER_RUNGS`(`songcue.py:124-129`)는 오늘 "기본으로 도는
  칸"(밝기·줌·아이리스·블라인더)만 담고, 호출자-플래그로 꺼진 채
  시작하는 `strobe_hit` 는 뺀다. color_snap 은 strobe 와 반대 극성
  (기본 활성, 명시적으로 꺼야 빠진다)이므로 `LADDER_RUNGS` 에 포함하는
  것이 이 상수의 기존 구분 기준과 일관적이다 — M2 에서 포함하고,
  `test_every_ladder_rung_is_classified`(`test_songcue_ladder.py:470`)
  의 `_MARKING` 튜플에 `LADDER_COLOR_SNAP` 을 더한다(§NC 연쇄 효과
  참고 — 이 시험은 갱신 누락을 스스로 RED 로 잡도록 설계됐다).

## §C. 사전 점검

```bash
# 1. 로컬 트리가 origin/main 과 동기화됐는지 확인 (착수 필수)
git fetch origin main
git rev-list --count --left-right origin/main...HEAD   # "0 N" 이어야 진행 가능

# 2. 대상 함수·상수가 실제로 그 자리에 있는지 확인
grep -n "^LADDER_\|^_MARKING_ACCENTS\|^def _marking_accents\|^def _accent_is_effective\|^class SongCueBundle\|^class SongCueSectionBundle" server/looks/songcue.py

# 3. beats_to_seconds 재사용 대상 확인
grep -n "^def beats_to_seconds" server/design/energy.py

# 4. 페이드 필드명 확정 (§B2) — SongCueSectionBundle 필드 목록 전량 확인
grep -n "class SongCueSectionBundle" -A 60 server/looks/songcue.py | grep -i "fade\|dimmer"
```

## §D. 제약 (위반 금지)

- REQ-LDCLIMAX-005 / 감독 결정 2026-09-12 — 큐당 찍는 액센트 정확히
  하나, 밝기만 누적. 색 스냅도 예외가 아니다.
- `disable_color_snap` 기본값은 반드시 `False`(= 끄지 않음, REQ-001
  대로 항상 활성) — `allow_color_snap`(기본값 거짓)이 아니다. 이 스위치는
  자동 회전을 켜는 스위치가 아니라 §NC 가 정한 임시 킬스위치다(REQ-012).
- 기존 골든 시험의 바이트 동일성은 **스위치가 아니라 REQ-004(무영향
  배제)가 지킨다** — 그 픽스처들이 회차 간 색 변화가 없기 때문이다
  (§NC 연쇄 효과가 실측을 인용한다). 색이 실제로 바뀌는 곡에서는 이
  SPEC 이후 color_snap 이 새 후보로 참여해 액센트 분포가 달라질 수
  있다 — 이것은 결함이 아니라 REQ-001 이 요구하는 의도된 동작이다.
- `_MARKING_ACCENTS` 상수 튜플 자체(줌→블라인더→아이리스 순서)는
  바꾸지 않는다 — `color_snap` 은 `_marking_accents` **함수**가 후보
  끝에 무조건 덧붙일 뿐(strobe 를 붙이는 것과 같은 기법), 기존 세 칸의
  순서·판정 로직을 재배열하거나 상수 자체를 4-튜플로 늘리지 않는다.
- 절정 지속시간 상한은 `zoom_pinch`/`iris_pinch`/`color_snap` 에는
  적용하지 않는다(§2 범위 결정) — 적용 대상을 `blinder_or_flash`/
  `strobe_hit` 밖으로 넓히지 않는다.
- `server/looks/songcue.py` 밖의 파일(경로 A 포함, 라이브러리 룩 YAML,
  `resolver.py`, `section_intent.py`)은 읽기만 하고 수정하지 않는다 —
  `songcue.py:109-110` 독스트링 개정은 이 파일 **안**이라 예외가 아니다.
- `{}` 매핑 리터럴을 새로 추가하지 않는다(`dict()` 함수 호출은 허용 —
  이 모듈의 기존 규율, SPEC-LDACCENT-001 §B5).
- 콘솔로 명령을 실제로 보내는 코드 경로(`server/safety/`, `server/bridge/`)
  는 건드리지 않는다 — 이 SPEC 은 순수 계산 계층이다.

## §E. 자기검증

- REQ-001~012 각각에 대해 판정 명령과 관측 출력을 PASS/FAIL 표로
  제출한다(`verification-claim-integrity.md` §3 5-section 형식).
- `uv run pytest -q` 전체 스위트 통과 수를 착수 전 기준선과 나란히
  제출한다(기준선은 `origin/main` 동기화 직후 첫 실행 — §A 동기화 이후).
- `ruff check server/looks/songcue.py server/tests/test_songcue_ladder.py`
  / `ruff format --check` 둘 다 clean.
- §NC 마커가 해소됐는지 착수 직전 `grep -n '\[NEEDS CLARIFICATION' plan.md
  spec.md` 로 확인 — 0건이어야 Implementation Kickoff Approval 통과.

## §F. 마일스톤 (결정 되돌리기 쉬운 순서 — 데이터 모델을 먼저)

### M1 — 데이터 모델 (가장 되돌리기 비싼 결정)

- `LADDER_COLOR_SNAP = "color_snap"` 상수(`songcue.py`, 기존
  `LADDER_*` 상수 옆).
- `SongCueClimaxReturn`(신규 frozen dataclass, design.md §1.2) — 필드:
  `source_section`, `source_cue_number: int`, `rung: str`,
  `cap_beats: float`, `inserted_cue_number: int`, `inserted_start_ms: int`.
- `SongCueBundle` 에 `climax_returns: tuple[SongCueClimaxReturn, ...] = ()`
  필드 추가(`withheld_movement`/`withheld_darkness`/`withheld_accents` 와
  같은 자리).
- §B2(페이드 필드명)를 이 마일스톤에서 확정한다 — 이후 모든 마일스톤이
  이 확정에 의존한다.

### M2 — 색 스냅 효과-판정 + 무조건 편입 배선 (새 타입 인터페이스, §NC 로 이미 해소)

- `_accent_is_effective`(`songcue.py:204`) 에 `color_snap` 을 위한 **셋째
  dispatch 분기**(색 비교, §B5) 추가 — 축-보유·그룹-보유 두 분기에
  끼워 맞추지 않는다. §7 색 집합 밖 색 금지(REQ-002)와 직전 큐와 색이
  같으면 무영향(REQ-004)을 만족하는지 판정하는 순수 함수.
- `_color_snap_applied`(신규, design.md §3) — 룩+복귀 색 → (룩, 강제
  페이드 0.0) 쌍.
- `_marking_accents`(`songcue.py:260`) 시그니처에 `disable_color_snap:
  bool = False` 추가 — **거짓(기본값)이면** 후보 끝(strobe 후보 뒤,
  있으면)에 `LADDER_COLOR_SNAP` 을 무조건 덧붙이고, 참이면 덧붙이지
  않는다(REQ-001/REQ-012). `_MARKING_ACCENTS` 상수 자체는 3-튜플 그대로
  둔다(§D).
- §B3 이 나열한 네 직접 호출자(`_max_climb`·`_finalize_marking_accents`·
  `_climb_rungs`·`_ensure_marking_accent`) 전부에 새 인자(`disable_color_snap`)
  배선 — 하나라도 빠뜨리면 그 경로에서만 색 스냅이 조용히 안 나오는
  결함이 된다(SPEC-LDACCENT-001 이 이미 겪은 실패 형태, §B3).
- **`songcue.py:109-110` 배제 독스트링 개정**(§B6) — "색 스냅도 뺀다..."
  두 줄을 이 SPEC 의 정의(§7 이 요구하는 되돌아오는 색을 즉시 전환하는
  것은 §7 위반이 아니다)로 교체하고 SPEC-LDCLIMAX-001 을 인용한다.
- **`LADDER_RUNGS` 에 `LADDER_COLOR_SNAP` 추가**(§B7) —
  `test_every_ladder_rung_is_classified`(`test_songcue_ladder.py:470`)
  의 `_MARKING` 튜플도 같은 커밋에서 갱신한다(이 시험이 새 칸 누락을
  스스로 잡도록 설계돼 있으므로, 갱신을 빠뜨리면 이 시험이 RED 로
  드러낸다).
- §NC 가 이미 해소됐으므로 별도 "자동 회전 배선" 마일스톤을 두지
  않는다 — 무조건 편입이 이 마일스톤의 산출물이다.

### M3 — 절정 지속시간 상한 후처리 패스

- `_apply_climax_duration_cap`(신규, design.md §2) — `build_songcue_bundle`
  반환 직전 호출. `bpm`/`meter` 는 이 함수를 호출하는 상위 계층(오늘
  `build_songcue_bundle` 시그니처에 없다 — 호출자가 이미 갖고 있는 `bpm`
  을 이 SPEC 이 새로 관통시켜야 한다. 이 관통 배선 자체가 §B1 급의
  다중 호출자 위험은 아니다 — `build_songcue_bundle` 은 이미 단일
  진입점(@MX:ANCHOR 주석, songcue.py 861행 근방)이므로 이 한 곳만
  고치면 된다)에서 전달받는다.
- 큐 재번호 매기기(§B1) — 복귀 큐 삽입 뒤 후속 큐 전량의 `cue_number`
  를 1씩 밀고, `_cue_names` 재호출 여부를 §B1 확인 결과에 따라 배선한다.
- REQ-006~009 각각의 픽스처(BPM 있음/없음, 다음 큐가 상한 안/밖) 작성.

### M4 — 시험 정합 + 회귀

- SPEC-LDACCENT-001 골든 대조군(`TestHeadroomCaseIsUntouched`,
  `test_songcue_accent_ladder_t382.py`) 과 `test_songcue_accent_fixture.py`
  · `test_songcue_ladder.py` 를 재실행해, `disable_color_snap` 인자를
  아예 넘기지 않고도(기본값 활성) 바이트 동일성이 유지되는지 확인한다
  — §NC 연쇄 효과가 실측한 대로, 이 픽스처들은 회차 간 색이 고정이라
  REQ-004(무영향 배제)가 color_snap 을 매 회차 거른다(REQ-011).
- `test_every_ladder_rung_is_classified`(`test_songcue_ladder.py:470`)
  갱신 확인 — `LADDER_COLOR_SNAP` 을 뺀 채로 두면 이 시험이 RED (§B7).
- 신규 대조군 — §7 색 집합 안 색 조합(양성), §7 색 집합 밖 색을 강제로
  넣어 REQ-002 가 거르는지(음성) 두 벌 — 둘 다 `disable_color_snap` 을
  넘기지 않는다(기본값 활성 상태에서 회전 후보로 실제로 뽑히는지 잰다).
- 신규 대조군 — `disable_color_snap=True` 로 명시적으로 끈 조합에서
  `color_snap` 이 후보에서 완전히 빠지는지(REQ-012).
- 신규 대조군 — `blinder_or_flash` 선택 + 다음 큐가 상한보다 늦게 오는
  긴 섹션(복귀 큐 삽입 확인), 다음 큐가 상한 안에 이미 오는 짧은 섹션
  (복귀 큐 생략 확인) 두 벌.
- `uv run pytest -q` 전체 스위트, `ruff check`/`ruff format --check`
  대상 파일 전량.

### M5 — 문서·MX 태그

- `@MX:ANCHOR`/`@MX:REASON` 주석을 M2/M3 가 바꾼 함수에 이 저장소
  관행대로 추가(예: `_apply_climax_duration_cap` 이 새로 얻는 "완성된
  번들 위 후처리" 성질).

## §G. 안티패턴 (하지 않을 것)

- **색 스냅을 `_MARKING_ACCENTS` 상수 튜플 자체에 직접 추가하기** — §D
  제약이 금지한다. `_marking_accents` 함수가 후보 끝에 덧붙이는 것과
  상수 자체를 4-튜플로 늘리는 것은 다르다 — 후자는 strobe 가 쓰는
  기존 기법(호출자-불투명 플래그로 함수가 붙인다)과 어긋난다.
- **`disable_color_snap` 을 영구 설계로 취급하기** — 이 스위치는 첫
  실기 콘솔 검증 세션까지의 임시 킬스위치다(§NC, REQ-012). 그 세션이
  통과하면(또는 발견된 결함이 후속 수정으로 닫히면) 후속 커밋에서
  제거한다 — `allow_strobe` 처럼 영구히 남는 스위치로 방치하지 않는다.
- **절정 지속시간 상한을 사다리·분할 계층 안에 끼워 넣기** — research.md
  §4 가 이미 기각한 방향(SPEC-LDACCENT-001 의 다중 호출자 취약점 반복).
  후처리 패스(M3)를 우회하지 않는다.
- **복귀 큐를 조용히 끼우고 보고 필드를 생략하기** — REQ-010 위반이자
  이 파일 전체의 "유보/삽입은 눈에 보이게 남긴다" 관행(SongCueWithheld*)
  을 깨는 것이다.

## §H. 교차 참조

- SPEC-LDACCENT-001(`server/looks/songcue.py`, 찍는 액센트 사다리 —
  이 SPEC 이 확장하는 기반)
- SPEC-COPILOT-SONGCUE-001(이 모듈의 원 SPEC)
- `docs/proposals/song-structure-lighting-standard.md` §6/§6.1/§7/§7.1
- `research.md`(이 SPEC 의 조사 근거 전량), `design.md`(기술 설계 상세)
