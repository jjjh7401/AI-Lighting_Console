# t154 — 카드 전제가 반증됐다. SPEC 은 맞았고, 내가 t141 에 넣은 오류를 걷었다

🔴 **이 카드 본문의 전제는 반증됐다.** 큐의 t154 카드는 「SPEC §A.4-2b 가 폭발 반경을
과소평가했다」고 적혀 있으나 **그 전제가 틀렸다.** SPEC 문면은 정확하다 — 고치지 마라.
문면만 읽고 SPEC 을 고치러 오지 마라. 실제 처방은 §3 이다.

- 카드: t154 · SPEC-COPILOT-LXSEQ-003 · 기준 `04f9238` · 브랜치 `WT-blast-radius-text`
- **콘솔 접촉 0 · 코드 로직 변경 0.** 주석·문서·검사 메시지만 고쳤다.

## 1. 무엇이 반증됐나

카드 전제: 「소비 루프가 종류를 안 가리니 bm 한 행이 열리면 dim·col 까지 죽는다 —
프리셋 임포트 **전체**가 0건이다」. 그 전제를 만든 것은 t141 레인(나)이다.

루프가 종류를 안 가리는 것은 **맞다**:

    server/orchestrator/tools.py:5002   for placement in result.planned:

나는 **그 위를 안 읽었다** — 무엇이 `planned` 에 들어오는가:

    server/lxseq/preset_parser.py:380   kind = resolve_sheet_kind(header)
    server/lxseq/preset_parser.py:434   PresetParseResult(sheet_kind=kind, records=..., ...)
    server/orchestrator/tools.py:4883   parsed = parse_preset_csv(text)   <- 프로덕션 유일 호출지
    server/orchestrator/tools.py:4872   sheet_bytes = base64.b64decode(raw, ...)  <- 시트 한 장
    server/orchestrator/tools.py:4888   _PRESET_POOL_FAMILY[parsed.sheet_kind]    <- 종류 하나로 풀 선택

**한 번의 임포트 = 한 시트 = 한 종류.** `result.planned` 는 구조적으로 단일 종류다.
BM.04 가 열려 죽는 것은 **그 bm 임포트**이고 dim·col 은 다른 호출이라 안 죽는다.

**원래 SPEC 문면(「열면 bm 임포트가 통째로 0건」)이 정확하다.**

### 1.1 실행으로 묶인 부분과 안 묶인 부분

- **묶였다**: `server/tests/test_lxseq_preset_parser.py::TestExactColumnSets::
  test_each_sheet_resolves_to_its_own_kind` 가 시트마다 `sheet_kind` 가 자기 종류로
  풀리는 것을 이미 단언한다. 중복해서 짓지 않고 인용한다.
- **안 묶였다**: 「프로덕션 호출지가 하나」는 **아키텍처 사실**이라 검사가 없다.
  배치 임포트 툴이 생기면 이 반증이 다시 뒤집힌다. 리드가 독립으로
  `git grep "import_lxseq_presets" -- server/orchestrator/*.py server/web/*.py` 로
  배치 툴 부재를 확인했다.

⚠️ `server/tests/test_lxseq_preset_mapper.py:42` 는 `out.extend(parse_preset_csv(text).records)`
로 **여러 시트를 한 목록에 합쳐** 매퍼에 넘긴다. 즉 **매퍼는 혼합을 다룰 수 있지만
프로덕션 경로가 혼합을 만들지 않는다.** 그 검사를 「혼합이 가능하다」의 근거로 인용하면
안 된다 — **도구의 능력과 실제 경로는 다른 명제다.**

## 2. 내가 어디서 틀렸나 — 리드의 실수와 같은 형태다

| | 읽은 곳 | 안 읽은 곳 | 방향 |
|---|---|---|---|
| 리드(t142 배차서) | 적용 표(`tools.py:1710`) | 소비 루프 | 반경을 **좁혔다** |
| 나(t141) | 소비 루프(`:5002`) | **생산 지점** | 반경을 **넓혔다** |

둘 다 「한 자리를 읽고 그 자리에서 일반화」다. 내 쪽이 더 나쁘다 — 좁히는 오류는
더 조심하는 방향이지만, **넓히는 오류는 없는 위험을 만들고 그것이 카드가 되어
정본 수정 직전까지 갔다.**

그리고 나는 t141 보고서에 「**코드가 스스로 말한다**(거절 문면에 「한 줄도」가 적혀
있다)」를 근거로 썼다. 그 문장은 참이지만 **내 결론의 넓이를 보증하지 않았다** —
「그 계획의 한 줄도」이지 「모든 계획의 한 줄도」가 아니다. **인용문이 세 보인다고
그 문장이 내 결론의 범위까지 덮지는 않는다.**

🔴 잡아낸 순서가 중요하다: **문서 편집 4자리를 다 만든 뒤 실행 확인을 붙이려다 잡았다.**
그 순서가 아니었으면 정본에 오류가 들어갔다. **「코드 변경 0이니 검증할 게 없다」가 함정**이다.

## 3. 처방 — 전수 분류 (매치 수가 처방 수가 아니다)

`git grep` 으로 「프리셋 임포트 전체」·「bm 만이 아니」·「종류를 안 가린」·
「프리셋 임포트가 통째로」·「dim·col」 5계열을 훑었다.

### 3.1 고침 — 현재상태 서술 (코드 2자리)

| 자리 | 무엇 |
|---|---|
| `server/lxseq/preset_parser.py` `_PROBE_REJECTED` 주석 | 「프리셋 임포트 전체가 0건 — bm 만이 아니다」 → 「그 bm 임포트가 통째로 0건」 + 반증 경위와 좌표 |
| `server/tests/test_lxseq_preset_beam_vocabulary.py` `TestTheStaleHoldTripwire` 독스트링 · 실패 메시지 | 동일 정정 |

🔴 **트립와이어 로직은 안 건드렸다.** 동작은 안 틀렸고 크기 주장만 틀렸다. 손대면
t141 의 3/3 뮤테이션이 무효가 된다.

### 3.2 반증 고지만 — 그 시점 기록 (2자리, 원문 불변)

| 자리 | 삽입/삭제 |
|---|---|
| `.moai/reports/t141/design.md` §2 | **+15 / −0** |
| `.moai/reports/t141/verdict.md` §4 | **+15 / −0** |

**고치지 않고 고지만 붙인 이유**: 내가 그렇게 주장했다는 **사실 자체가 감사 기록**이다.
원문을 지우면 「소비 루프만 읽고 생산 지점을 안 읽는」 형태가 기록에서 사라진다.
t140 이 세운 기준(기록은 고치지 않고 고지한다)의 직접 적용이다.

### 3.3 여전히 옳음 — 손대지 않음

| 자리 | 왜 |
|---|---|
| `spec.md` §A.4-2b · `preset-unify-design.md` §5 | **원래 문면이 맞다.** 카드가 고치라던 자리다 |
| `.moai/reports/t135/beam-vocabulary.md` · `t146/spec-body-correction.md` | 원문 정확 |
| `.moai/reports/t140/doc-expiry.md` · `t142/verdict.md` | 크기 주장이 없다 |
| `.moai/specs/…/progress.md:613-614` | 「**임포트가** 통째로 거절된다」 — `bm` 을 안 붙였고 그대로 참이다 |

### 3.4 못 고침

**PR #201 본문**에 틀린 주장이 있다. 머지됐고 본문은 수정하지 않는다 — 기록으로 남긴다.
그 PR 을 근거로 인용하는 사람이 있으면 이 보고서와 §3.2 의 고지가 그 자리를 막는다.

## 4. 검증

    ruff check server/                                   -> All checks passed!
    ruff format --check (편집 2파일)                      -> 2 files already formatted
    pytest test_lxseq_preset_beam_vocabulary.py
           test_lxseq_preset_parser.py                    -> 41 passed
    전체 스위트                                            -> §4.1

기록 2건이 **삭제 0**인 것이 원문 불변의 기계적 증거다.

## 5. 안 잰 것

1. **한 시트 안에서 번역 가능/불가가 섞이는 경우** — col 은 판정과 판독이 같은 술어를
   쓴다고 주석이 말하지만 **실행으로 안 쟀다.** 섞인다면 「단일 종류 안에서도 한 행이
   나머지를 죽이는가」가 남는 물음이고, 그건 이 카드가 안 연다.
2. **배치 임포트 툴의 부재** — 검사가 아니라 grep 으로 확인했다. 생기면 반증이 뒤집힌다.
3. **종류 간 전파를 실행으로 부정하지 않았다** — 기존 검사
   (`test_lxseq_preset_value_path.py`)는 표를 비워 **한 종류** 계획만 재므로 전파를
   긍정도 부정도 하지 않는다.
4. **계기 함정 하나**: `grep -rn "bm 임포트" --include='*.md' .` 이 1건을 냈는데 같은
   시점 `git grep` 과 파일 직접 지목은 5건을 냈다. 1건을 믿었으면 4자리를 놓쳤다.
   **두 계기가 다른 답을 내면 셋째를 쏴라.**
