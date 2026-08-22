# t11 프로브 — D2 오프라인 재현 측정

- 카드: t11 (프로브 단계만)
- 트리: `.claude/worktrees/t11` · 브랜치 `WT-console-fidelity` · HEAD `b2e22b0`
- 범위: 오프라인 전용 · 콘솔 무접촉 · 제품 코드 수정 0건
- 측정자: run 레인 (session 71f784af)

---

## 판정 한 줄

**재현됨.** D2 는 오프라인에서 재현된다 — 단, **출하된 `FakeConsole` 그대로는 재현되지 않고**, `truncate_at` 과 같은 모양의 변형(프로퍼티 판독 한 곳)을 더해야 재현된다. 리드가 가른 두 갈래 중 **「작은 카드」** 쪽이다.

---

## 1. 재현 명령 원문

`.venv/bin/python -c` 로 실행. 스크립트 파일은 남기지 않았고, 실행 후 트리는 clean 이다.

```python
import sys
from collections import Counter
sys.path.insert(0, '.')
from server.tests.test_lxseq_tool import TYPES_ROOT, FakeConsole, FakeDeploy, FakeExec, _call, _toolset

class HandleTypeConsole(FakeConsole):
    """D2 모사: 픽스처의 FixtureType 프로퍼티가 이름이 아니라 'FixtureType <슬롯>' 을 돌려준다.
    바꾸는 것은 픽스처 프로퍼티 판독 한 곳뿐 — FixtureTypes 트리 열거는 이름을 그대로 준다
    (실기에서도 그쪽은 이름이 나온다)."""
    def query_property(self, path, property_name):
        answer = super().query_property(path, property_name)
        if property_name != 'FixtureType' or not answer.get('ok'):
            return answer
        if path.startswith(TYPES_ROOT + '/'):
            return answer
        slot = self._slots.get(str(answer['value']))
        if slot is None:
            return answer
        return {'ok': True, 'value': 'FixtureType ' + str(slot)}

def second_preview(cls):
    console = cls()
    deploy, runner = FakeDeploy(console), FakeExec(console)
    reg = _toolset(console, exec_port=runner, deploy=deploy)
    first, _ = _call(reg, action='apply')
    second, _ = _call(reg, action='preview')
    return Counter(row['kind'] for row in second['plan']['skipped']), second['plan']['skipped']
```

A = `second_preview(FakeConsole)` (대조군) · B = `second_preview(HandleTypeConsole)` (D2 모사).

## 2. 관측 출력 원문

```
====================================================================
A. CONTROL - untouched FakeConsole
====================================================================
  apply: created runs=12, fixtures on console=86
  2nd preview: runs=0 skipped=86
  skip kinds = Counter({'already_patched': 86})

====================================================================
B. D2 SIM - FixtureType read returns a handle
====================================================================
  apply: created runs=12, fixtures on console=86
  2nd preview: runs=0 skipped=86
  skip kinds = Counter({'fid_occupied': 86})

====================================================================
C. NON-VACUITY - does B actually return a handle?
====================================================================
  csv/console type name    = 'ETC S4 LED S3 Lustr X8'
  control FixtureType read = {'ok': True, 'value': 'ETC S4 LED S3 Lustr X8'}
  sim     FixtureType read = {'ok': True, 'value': 'FixtureType 1'}
  sim     Name  read       = {'ok': True, 'value': 'N'}
  sim     FID   read       = {'ok': True, 'value': '7'}

====================================================================
VERDICT
====================================================================
  A control = {'already_patched': 86}
  B d2-sim  = {'fid_occupied': 86}
  matches auditor fid_occupied=86 ?         -> True
  discriminates from control (non-vacuous)? -> True
  B first skipped row = {'fid': 101, 'address': '1.1', 'kind': 'fid_occupied',
    'detail': 'FID 101는 콘솔에 이미 있다',
    'occupant': {'address': '1.1', 'name': 'KEY 101', 'fixture_type': 'FixtureType 1'},
    'occupied_fid': 101}
```

## 3. 「재현됨」의 정확한 뜻 — 한 대목을 갈라 둔다

세 가지를 따로 적는다. 뭉치면 카드 크기를 잘못 잡는다.

| 명제 | 관측 |
|---|---|
| 출하된 `FakeConsole` 이 D2 를 낸다 | **거짓.** 대조군 A = `Counter({'already_patched': 86})` |
| 프로퍼티 판독 한 곳을 핸들로 바꾼 변형이 D2 를 낸다 | **참.** B = `Counter({'fid_occupied': 86})` — 감사관 보고 수치와 완전 일치 |
| 그 변형이 실제로 갈림을 만든다(비공허) | **참.** A ≠ B, 그리고 C 에서 판독값이 `'FixtureType 1'` 로 실제로 바뀜을 직접 확인 |

따라서 **손대지 않은 가짜 콘솔로는 `fid_occupied` 가 나올 수 없다.** 감사관도 나처럼 변형을 더했거나, 아니면 라이브 관측(t9 M4)을 오프라인 재현으로 적었거나 둘 중 하나다. 어느 쪽인지 나는 모른다 — 감사관의 재현 명령 원문을 보지 못했다.

이 구분이 카드 크기를 가른다는 리드의 판단은 맞았고, 답은 **작은 카드** 쪽이다: 오프라인이 원리적으로 못 보는 자리가 아니라, 가짜 콘솔에 갈래가 하나 빠져 있을 뿐이다. `truncate_at`(D1 에서 같은 이유로 추가된 변형)과 정확히 같은 모양이다.

## 4. 역방향 모호성 — 새로 재지 않았다, 기록된 것을 그대로 옮긴다

콘솔에 접속하지 않았으므로 **이번 프로브는 슬롯 12를 읽지 않았다.** 아래는 t9 M4 의 라이브 관측 기록(`progress.md`)이며, 내가 재현한 것이 아니다.

```
Patch/FixtureTypes  childCount 15 · listed 15 · truncated false
  슬롯  4  Robin Spiider   <-- 중복
  슬롯 12  Robin Spiider   <-- 중복
```

- 슬롯 12가 무엇이 다른지(모드 집합 · GDTF 판본) — **안 읽힌다.** t9 도 못 읽었고 이번에도 읽지 않았다. 추정하지 않는다.
- 실제로 잡힌 것은 **슬롯 4** (`FixtureType 4`, MOVER-D 8대 FID 521~528, 실측).

### 다만 — 이 모호성이 D2 수정을 막는지는 방향에 달려 있다

`_occupancy_skip`(`server/lxseq/mapper.py:325`)이 비교하는 것은

```python
(first.fixture_type or "") == console_type      # console_type 은 이름
```

즉 필요한 것은 **핸들 → 이름**(정방향)이지 이름 → 슬롯(역방향)이 아니다.

| 방향 | 모호한가 | 근거 |
|---|---|---|
| 슬롯 → 이름 (정방향) | **모호하지 않다** | 슬롯 4 → `Robin Spiider`, 슬롯 12 → `Robin Spiider`. 둘 다 같은 이름이라 중복이 답을 가르지 않는다. t9 기록도 「슬롯→이름은 모호하지 않다」 |
| 이름 → 슬롯 (역방향) | **모호하다** | `Robin Spiider` 가 4/12 둘 다 |

그리고 정방향에 필요한 슬롯↔이름 대응은 **툴이 이미 수행하는 판독 안에 들어 있다.** 측정:

```
FixtureTypes tree read the tool already performs:
  truncated = False   childCount = 8
    {'i': 1, 'name': 'ETC S4 LED S3 Lustr X8', 'class': 'FixtureType'}
    {'i': 4, 'name': 'Look Unique 2.1', 'class': 'FixtureType'}
    ...
  slot key present on every child? -> True
  name key present on every child? -> True
```

라이브 기록에서도 이 트리는 `truncated false · listed 15/15` 로 **온전히 읽혔다.**

> 주의: 「정방향이면 충분하다」는 위 코드 한 줄을 읽은 결과이지, 고쳐서 초록을 본 관측이 아니다. 수정은 하지 않았다.

## 5. 재현하지 않은 것 (명시)

- **콘솔 라이브 재현 0건.** onPC 에 접속하지 않았다. 슬롯 12 재판독, 86대 상태 재조회, 실기 `FixtureType` 판독 — 전부 하지 않았다.
- **감사관의 재현 절차 미확인.** 감사관이 어떤 명령으로 `Counter({'fid_occupied': 86})` 를 얻었는지 원문을 보지 못했다. 내 B 와 수치가 같다는 것만 관측했다.
- **전체 스위트 미실행.** 이 프로브는 테스트를 고치지도 돌리지도 않았다(기준선 9681 대비 대조 없음).
- **D2 수정 시도 0건.** 정방향 해석을 실제로 매퍼에 넣어보지 않았다 — 그것이 초록을 내는지는 **미측정**이다.
- **t9 라이브 기록 재검증 0건.** §4 의 슬롯 표와 `truncated false` 는 `progress.md` 인용이며 내 관측이 아니다.
- **다른 가짜↔실물 괴리 미조사.** t11 카드 본체(전수조사)는 손대지 않았다.

## 6. 잔여 위험

- 내 `HandleTypeConsole` 은 실기 핸들 형식을 `'FixtureType <슬롯>'` 으로 **가정**했다. 이 형식은 t9 라이브 관측(`"fixture_type": "FixtureType 10"`)과 일치하지만, 다른 클래스·다른 경로에서 형식이 다를 가능성은 재지 않았다.
- 오프라인 슬롯 번호(1~8)와 실기 슬롯 번호(4·8·9·10·11·13·14·15)는 다르다. 가짜는 CSV 8종만 갖고, 실기 라이브러리는 15종이다. 재현이 성립하는 것은 **갈래**이지 번호가 아니다.
- 슬롯 12의 정체가 끝내 안 읽히면, 정방향 수정 자체는 서지만 「같은 이름 두 슬롯 중 어느 쪽으로 새로 패치할 것인가」는 여전히 열려 있다 — D2 수정과 별개의 결정이다.

---

## 다음 배차에 필요한 재료 (판단 아님)

1. D2 수정을 **정방향(핸들→이름)** 으로 한정하면 `Robin Spiider` 중복은 막지 않는다 — 카드에서 이 둘을 분리할 수 있다.
2. 가짜 콘솔에 핸들 변형을 더하는 것은 `truncate_at` 선례가 있다.
3. 슬롯 12 판독은 콘솔 접속이 필요하므로 이 카드에 넣으려면 실기 확인 슬롯이 따로 있어야 한다.
