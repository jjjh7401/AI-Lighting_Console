# t182 — 1단계 측정: 계산되는가, 닿는가

기준: `WT-groups-refusal-path` @ `0fc0439` (origin/main 과 0/0)
측정일: 2026-08-31 · 실기 콘솔 0회 (전부 가짜)
프로브: `.moai/reports/t182/probes/` 3개. 워크트리 루트에서 —
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.moai/reports/t182/probes uv run python .moai/reports/t182/probes/<name>.py`

카드가 첫 걸음을 판정이 아니라 측정으로 박았다. 재기 전에 어느 쪽 처방도 쓰지 않았다.

---

## 1. 이 가짜가 무엇을 정하나 (t181 에서 걸린 자리라 먼저 적는다)

기존 `_Console` 은 죽은 경로에서 `LookupError` 를 던진다. 실물 포트는
`StateQueryError` 다(`server/safety/console.py:89`, `raise` 8자리). t181 에서 이
차이가 처방을 통째로 바꿀 뻔했다.

그래서 **두 종류를 다 쐈다.** 결과가 갈리지 않았다 — `collect_rig_sections:1012` 가
`except Exception` 이라 종류를 안 가린다. 읽은 것과 도는 것이 같음을 확인한 것이고,
**내 가짜의 선택이 이 카드의 결과를 편향시키지 않았다**는 대조군이다.

## 2. 카드의 두 갈래 — 답은 「(가) 그리고 그 뒤에 죽는다」

`collect_rig_sections` 를 스파이로 감싸 반환값을 잡았다:

| 팔 | 죽은 경로 | 종류 | **계산된 분류** | 도구 |
|---|---|---|---|---|
| A | 없음 | — | groups·fixtures 둘 다 읽힘 | RETURNED |
| B | fixtures | `LookupError` | fixtures=`path_not_resolved` | RAISED |
| C | fixtures | `StateQueryError` | fixtures=`path_not_resolved` | RAISED |
| D | 둘 다 | `LookupError` | 둘 다 **`console_unreachable`** | RAISED |
| E | 둘 다 | `StateQueryError` | 둘 다 **`console_unreachable`** | RAISED |

RAISED 는 전부 `patchplan.py:1461` — `read_existing_fids` 안이다(t181 이 자리 B 로
남긴 그 자리).

**계산은 된다.** 카드가 「계산되는데 안 나가는 것인지, 계산 자체가 없는 것인지」를
갈랐는데 답은 **전자**이고, 계산 **직후 다음 줄**에서 도구가 죽어 페이로드가
만들어지지 않는다.

## 3. 🔴 2단계 결론을 철회했다 — 내 스텁이 답을 만들고 있었다

죽음만 고치면 닿는지 보려고 `read_existing_fids` 를 `root_unreadable=True` 로
흉내 냈다. 그랬더니 `console_unreachable` 이 페이로드 어디에도 안 나왔고
「채널이 안 흐른다」로 읽었다. **틀렸다.**

`root_unreadable=True` 는 **FID 축**의 상태다. 그 축이 `console_read_reason` 을
먼저 채워 **섹션 축을 가린다.** 축을 갈라 다시 쟀다:

| 스텁 | 팔 | `refusal` | `refusal_detail` | 페이로드에 `console_unreachable` |
|---|---|---|---|---|
| S1 FID 축 시끄러움 | C | `null` | `null` | **없음** |
| S1 FID 축 시끄러움 | E | `null` | `null` | **없음** |
| S2 FID 축 조용함 | C | `null` | `null` | 없음 |
| S2 FID 축 조용함 | E | `section_unread` | `단면을 못 읽었다: console_unreachable` | **있음** |

**S2-E 가 채널이 흐른다는 증거다.** t167 이 연 `refusal` / `refusal_detail` 통로는
실제로 사용자에게 닿는다 — 죽음만 치우면.

⚠️ **S2 첫 판은 무효였다.** 지어낸 `fids=(1,2,3)` 이 패치 시트와 안 맞아 하류가
`SpatialAnalysisError` 로 터졌다. 살아있을 때와 같은 FID 를 완전 판독으로 돌려주는
스텁으로 바꿔서 다시 쟀다. 못 쓴 팔을 조용히 버리지 않고 적는다.

## 4. 그래서 남은 결함은 카드가 적은 것과 다르다

카드는 「매퍼는 두 분류를 가르는데 사용자는 하나만 본다」로 세웠다. 재보니 매퍼 층
채널은 **흐른다**(S2-E). 실제로 남은 것은 둘이고 **둘 다 카드에 없다**:

**(ㄱ) 죽음이 채널을 막는다.** 현재는 `read_existing_fids` 가 먼저 죽어 어떤
분류도 안 나간다. t181 자리 B 그대로다.

**(ㄴ) 🔴 FID 축이 섹션 축을 가린다.** S1-E 를 보라 — 섹션 축이
`console_unreachable` 을 **계산했는데** `refusal` 이 `null` 이고 그 말이 페이로드에
없다. 그리고 **S1 이 현실적인 조합이다**: 픽스처 경로 하나가 죽으면 섹션 판독과
FID 판독이 **같은 경로를 읽으므로 둘 다 실패한다.** 즉 (ㄱ)을 고쳐도 현실 경로에서는
여전히 분류가 안 보인다.

t167 이 「두 축이 한 채널로 합쳐졌다」를 막으려고 검사를 뒀는데, 그 검사가 지키는
것은 **FID 축 채널에 섹션 사유가 들어가지 않는 것**이다. 반대 방향 —
**FID 축이 시끄러우면 섹션 사유가 사라지는 것** — 은 아무도 안 지키고 있다.

## 5. 안 잰 것

- **실기 콘솔 0회.** 전부 가짜다.
- **(ㄴ)의 기전을 안 쟀다.** `map_groups` 안에서 FID 축이 어디서 이기는지 안 따라갔다.
  「가려진다」는 관측이고 「왜」는 아직 가설도 없다.
- **S1-C 와 S2-C 가 왜 둘 다 조용한지** 안 쟀다. 픽스처 단면이 `path_not_resolved` 로
  계산됐는데 어느 스텁에서도 안 나온다 — 이 도구가 `sections["groups"]` 만 읽는다는
  t152 기록과 맞지만 확인은 안 했다.
- **처방 없음.** 이 회차는 측정만이다. (ㄴ)이 조이는 방향인지도 아직 모른다.

---

# 4단계 — (ㄱ) 만으로 사용자가 보는 것이 바뀌는가 (리드 물음)

리드가 (ㄱ) 착수 전에 하나를 재라고 했다: **S1(현실 조합)에서 FID 축이
「콘솔이 안 답했다」를 채우는가(a), 거기도 비어 있는가(b).**
(a) 면 (ㄱ) 만으로 실질 개선이고, (b) 면 (ㄱ) 의 값이 t186 에 종속된다.

## 스텁을 안 쓰고 쟀다 — 2단계에서 스텁이 답을 만들었기 때문

`patchplan.py:1461-1466` 을 읽으니 실패 반환이 코드에 그대로 있다:

    state = fid_property_port.query_state(FID_FIXTURE_ROOT)
    if state.get("ok") is not True:
        return ExistingFidRead(attempted=True, root_unreadable=True)

**3단계 S1 스텁과 바이트 동일하다** — 내가 지어낸 값이 아니라 이 함수 자신의 실패
반환이었다. 그래도 추론으로 두지 않고, 포트가 **예외 대신 `ok=False`** 를 주게 해서
**진짜 `read_existing_fids`** 를 그 갈래로 태웠다.

| 팔 | `console_read_reason` | `console_read_incomplete` | `refusal` |
|---|---|---|---|
| 대조군 살아있음 | `null` | `false` | `null` |
| FID 루트 `ok=False` (스텁 없음) | **`콘솔의 픽스처 루트 상태를 읽지 못했다`** | `true` | `null` |

## 답: (a)

**FID 축이 콘솔을 가리키는 말을 채운다.** 그러므로 (ㄱ) 만 고쳐도 사용자가 받는 것이
바뀐다:

    지금        서버 내부 문제가 발생했습니다. … 진단 로그를 확인해 주세요.   (kind=unexpected)
    (ㄱ) 이후   콘솔의 픽스처 루트 상태를 읽지 못했다                          (console_read_incomplete=true)

감독이 서버를 뒤지러 가는 대신 콘솔을 본다. **실질 개선이고 t186 에 종속되지 않는다.**

## 두 경로가 같은 답에 닿았다

3단계 S1 은 **예외 + 스텁**, 4단계는 **`ok=False` + 진짜 함수**다. 자극도 경로도
다른데 문자열이 같다. 한 계기의 답이 아니라는 뜻이고, 2단계에서 한 계기만 믿었다가
틀린 것에 대한 교정이다.

## 이 회차가 안 정한 것

- ⚠️ **이 자극은 섹션 축도 바꾼다.** `collect_rig_sections:1012` 는 예외만 잡으므로
  `ok=False` 는 그 갈래를 안 탄다. 그래서 이 회차가 정한 것은 **FID 축 문면 하나**다.
  섹션 축 거동은 여기서 읽지 않았다 — **자극이 두 축을 건드리는 것을 알고 쐈고**,
  2단계에서는 모르고 쐈다. 그 차이가 이 회차와 2단계의 차이다.
- **(ㄱ) 의 실제 수리 형태를 안 정했다.** 예외를 잡아 같은 `root_unreadable=True` 로
  보내는 것이 자연스럽지만(형제 실패 형태가 이미 그렇게 돌아간다), 그건 설계 선택이고
  이 측정이 강제하지 않는다.
- `refusal` 은 두 팔 다 `null` 이다 — (ㄴ)과 정합적이지만 이 회차가 (ㄴ)을 잰 것은 아니다.
