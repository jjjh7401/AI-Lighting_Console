# t160 — 구멍은 언어가 아니라 인용 형태였다. 한국어 어휘가 낸 승인은 0

- 카드: t160 · 감사 카드 · 기준 `ab18083` · 브랜치 `WT-korean-grant-vocab`
- **콘솔 접촉 0 · 코드 변경 0 · SPEC 파일 0.** 판정과 전수표까지다.

## 0. 결론 — 카드의 전제가 틀렸고, 진짜 구멍은 더 컸다

카드는 「한국어로 적힌 승인을 `grant` 술어가 못 본다」였다. 재보니:

| | 결과 |
|---|---|
| 한국어 어휘가 **추가로 낸 승인** | **0건** |
| 그런데 t158 이 놓친 승인 | **있었다** — `TRUNCATE-001` |
| 놓친 진짜 이유 | 🔴 **한국어가 아니라 「REQ 가 아닌 SPEC-ID 인용」** |
| 승인을 지는 기록 없는 SPEC | t158 「1개」 → **2개**(FXGEN-001 · TRUNCATE-001) |

**술어가 좁아서 놓친 것은 맞다. 그런데 좁았던 축이 언어가 아니었다.**

## 1. 어휘를 짓지 않고 코퍼스에서 긁었다

### 1.1 첫 발견 — 「승인」도 두 뜻이다

살아 있는 코드의 「승인」을 전부 뽑아 읽으니 대부분이 **런타임 승인 통로**였다:

    승인 통로 asked [] · 콘솔 executed []
    "승인 전 계획은 콘솔 무접촉으로 계속 수정할 수 있습니다 — "
    _Decision(command=c, status="held", reasons=("승인 필요",))
    승인 브리지와 같은 모양이다(``bind``/``unbind``/``resolve``)

**사용자에게 묻는 그 승인**이지 「이 방어를 풀어 준 승인」이 아니다.
t158 이 겪은 「예외가 두 뜻」과 **같은 함정이 「승인」에도 있다.**

### 1.2 후자 어휘를 따로 긁었다

    감독 결정 · 감독 승인 · 사용자 승인 · user-approved · 완화 · 승인된 예외

실제 문면을 열어 보니:

| 자리 | 문면 | 승인인가 |
|---|---|---|
| `tools.py:1712` | 「감독 결정(2026-08-26): dim 은 전 픽스처」 | **아니다** — 설계 결정 |
| `test_autopatch_verify.py:3223` | 「그 자동 이동이 없으므로 같은 사고가 안 난다. 감독 결정(2026-08-22)」 | **아니다** — 왜 이렇게 동작하는가 |
| `test_vwx_addressfit.py:344` | 「512 를 넘는 채널은 유니버스에 없다. 감독 결정으로 유지한다(t15)」 | **아니다** — 유지 결정 |
| `lxseq_groups_e2e.py:225` | 「전제가 하나라도 미충족이면 발사하지 않는다. 감독 승인 조건이다」 | **아니다** — 발사 전제 |
| `session.py` ×3 · `SongTimeline.tsx` | 사용자 대면 문구·UI 라벨 | **아니다** |
| 「완화」 6자리 | 「이 단언을 완화하지 마라」·「인젝션 완화」 | **아니다** — 반대 방향이거나 보안 용어 |

**한국어 어휘가 낸 승인: 0건.** 문면을 열지 않고 개수만 셌으면 「6~8건 추가」로 적었을 것이다.

## 2. 🔴 그런데 t158 은 실제로 놓쳤다 — 다른 축에서

넓힌 술어(`granted|user-approved|감독 승인|감독 결정|승인된 예외`)로 다시 훑으니
**t158 이 안 본 파일**이 나왔다:

    server/tests/test_songcue_bundle.py:141  SPEC-COPILOT-GROUPGEN-001 M3/M4 — granted exception
    server/tests/test_songcue_bundle.py:153  SPEC-COPILOT-TRUNCATE-001 (2026-08-05, user-approved)
                                             — granted exception
    server/tests/test_songcue_bundle.py:175  2026-08-07 granted exception — 타임코드 SLOT OCCUPANCY

**`:153` 이 `TRUNCATE-001` 을 인용한다** — t158 이 「기록 없음」으로 표에 올렸으면서
「인용은 출처 주석일 뿐」으로 분류한 바로 그 SPEC이다.

**왜 못 봤나**: t158 의 우주가 `REQ-<도메인>-<번호>` 였다. 이 승인은 **SPEC-ID 를 인용**하므로
술어가 REQ 를 요구하는 순간 후보에 안 든다. 언어와 무관하다 — 이 줄은 **영어**다.

### 2.1 승인 선언 전량 (15자리)

| 파일 | 선언 수 | SPEC 을 인용하는 것 |
|---|---|---|
| `test_overlap_preserve.py` | 11 | SPATIAL-001 · FXGEN-001 · DEPLOY-001 · INTROSPECT-001 · WRITEGATE-001 |
| `test_songcue_bundle.py` | 3 | GROUPGEN-001 · **TRUNCATE-001** |
| `test_fx_boundary.py` | 1 | FXGEN-001 |

SPEC 을 인용하는 선언 **7건 / 7개 SPEC**. 나머지 8건은 프로토콜·PR 번호·카드·제안서·
문서 교정 패스를 근거로 들어 SPEC 을 안 인용한다.

**그중 기록(progress.md)이 없는 SPEC: 2개** — `FXGEN-001`(전무) · `TRUNCATE-001`(plan·acceptance 는 있고 progress 없음).

### 2.2 그 승인의 집행도 기계적이다 — 다만 **종류가 다르다** (열어서 확인)

t158 은 「집행이 기계적이라 기록 복원 불필요」로 닫았다. 그 결론이 새로 찾은
`TRUNCATE-001` 건에도 서는지 읽었다(`test_songcue_bundle.py:153-173`):

    THIS GRANT IS NOT ADDITIVE-ONLY, and that is the difference from the two above:
      git diff --unified=0 38a6e7e2..HEAD -- server/orchestrator/tools.py
        | grep -cE '^-[^-]'                                          ->  203
    So the "ZERO pre-existing lines modified" evidence the GROUPGEN note leans on
    is NOT available here and must not be implied.

**주석이 자기 증거의 한계를 스스로 적었다.** 그리고 대신 무엇이 검증됐는지도 적는다:

    both protected ranges are present VERBATIM in HEAD --
      old 234..238  `_PROGRAMMER_STATE_COMMANDS`
      old 524..569  the in-bundle dedupe loop
    Protected-range overlap re-verified mechanically: ZERO across all 43 hunks.

**집행은 기계적이다** — 다만 FXGEN 축(경로 이름 + 헤딩 문자열 + 삭제 0)보다 **보증이
좁다**: 203줄이 수정된 채로, **두 블록이 바이트 동일**하다는 것만 보증한다.
그리고 후속에게 「위치가 아니라 **내용**으로 다시 확인하라」고 지시까지 남겼다.

**판정: t158 §3 의 결론은 이 건에도 선다.** 기록 복원은 필요 없다. 다만 보증의
**종류**가 달라서, 「승인은 다 같은 강도로 고정돼 있다」로 뭉뚱그리면 안 된다.

## 3. 대조군 — 두 팔로 쐈다

카드가 「결과 수를 믿기 전에 대조군을 먼저 쏴라」고 했다. **한 팔로는 부족하다** —
넓힌 술어가 잡는다는 것과 좁은 술어가 놓친다는 것은 다른 명제다.

날조 대조군(한국어 승인 + SPEC-ID 인용) 한 줄을 `server/lxseq/preset_parser.py` 맨 위에 심었다:

    #: 2026-08-30 승인된 예외 — SPEC-COPILOT-ZZPROBE-001, 감독 승인. 날조 대조군.

| 팔 | 술어 | 결과 |
|---|---|---|
| ① 검출력 | 넓힌 술어 | **잡았다** — `preset_parser.py:1` |
| ② 구멍 | t158 의 좁은 술어(`REQ-` + `grant`) | **못 잡았다** (빈 출력) |

**①만 쐈으면 「넓힘이 필요했다」가 증명 안 된다.** ②가 그것을 증명한다.
복원 확인: `git status --porcelain` 0줄.

## 4. t158 의 내 문장을 정정했다

t158 §2 가 「**넷 전부 FXGEN-001 이다.** 나머지 넷의 인용은 출처 주석이다」로 닫았다.
**틀렸다** — `TRUNCATE-001` 도 승인을 진다. 원문은 안 고치고 정정 고지를 붙였다.

## 5. 등급 — 조사 범위의 공백이지 사고가 아니다

「승인이 누락됐다」가 **아니다.** 승인은 전부 문서화돼 있고 날짜와 근거를 달고 있다.
빠진 것은 **내가 그 승인들을 안 셌다**는 것뿐이다. 그리고 t158 §3 의 결론
(집행이 기계적이라 기록 복원 불필요)은 **TRUNCATE 건에도 성립하는지 안 쟀다**(§6-1).

## 6. 안 잰 것

1. **(§2.2 로 옮겼다 — 열어서 확인했다.)** 남은 것은 그 승인이 **다른 종류의 보증**을
   준다는 점이고, 그 차이가 다른 승인에도 있는지는 전수 안 했다.
2. **승인 선언을 세는 술어도 여전히 좁을 수 있다** — `granted`·`user-approved`·한국어 5어휘로
   좁혔다. 다른 표기(예: 「예외로 둔다」·「이 자리만 뺀다」)로 적힌 승인은 여전히 안 보인다.
   대조군이 검출력을 보였으니 어휘를 더 넣으면 잴 수 있다.
3. **`.claude/` 규칙·스킬 문서** — 살아 있는 코드만 훑었다(t158 과 같은 경계).
4. **SPEC 을 안 인용하는 8건** — 프로토콜·PR·카드를 근거로 드는 승인들이 그 근거를
   실제로 갖고 있는지는 안 봤다. 「죽은 인용」 축의 SPEC 밖 판이다.
