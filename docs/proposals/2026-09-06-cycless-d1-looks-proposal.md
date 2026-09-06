# cyc 없는 리그의 D1 — edm·rock 에 묶이는 조용한 룩 하나씩 (카드 t282)

상태: **제안 — 게이트에 막혀 실행 안 됨.** 라이브러리 파일은 이 브랜치에서 한 바이트도
안 바뀌었다. 아래 두 룩은 승인이 나면 그대로 넣을 수 있는 형태로 적어 둔 것이다.

## 1. 왜 필요한가 — 잰 것

t277 이 실기 grandMA3 에서 잰 결함: 감독이 4개 구간을 확정했는데 큐는 3개만 저장됐다.
가장 조용한 구간(`Intro`, dynamics 1)이 조용히 버려졌다. t278 이 원인을 확정했다 —
EDM 의 유일한 D1 룩 `edm-ambient-hold` 는 역할이 `배경` 하나뿐이고, 실기 리그의 18개
그룹에는 cyc 계열이 없다. 묶일 그룹이 없으니 도구가 올바르게 건너뛴 것이다.

t278 은 선택기를 고쳐 「이 리그에서 실제로 묶이는 룩」을 고르게 했지만, 고를 것이 없는
칸 둘은 그대로 남겼고 `TestWhatThisFixCannotReach` 에 못박았다: **edm 과 rock 은 각각
D1 룩이 정확히 하나이고, 그 룩의 역할은 `배경` 뿐이다.**

실기 리그에서 실제로 묶이는 역할을 이 브랜치에서 다시 쟀다
(`resolve_roles`, 18그룹 실기 목록):

| 역할 | 묶임 | 그룹 |
|---|---|---|
| 백라이트 | O | BACK |
| 프론트 | O | FOH |
| 사이드 | O | SIDE-L / SIDE-R / SIDE-ALL |
| 스페셜 | O | KEY |
| 탑 | X | `no_match` |
| 배경 | X | `no_match` |

ballad 가 멀쩡한 이유도 여기 있다 — D1 룩이 둘이고 그중 `ballad-moonlight` 이
`배경`+`백라이트` 를 함께 갖는다. 역할 하나만 묶여도 저장되므로 cyc 없이도 인트로가 산다.

## 2. 제안하는 룩 둘

두 룩 모두 **기존 D1 룩 뒤에** 놓는다. `_select_bindable` 이 요청 다이내믹스 안에서
「묶이는 **첫** 룩」을 고르므로, 이 순서가 cyc 있는 리그의 기존 동작을 그대로 지킨다:
cyc 가 있으면 앞선 `배경` 룩이 먼저 묶여 그대로 뽑히고, cyc 가 없을 때만 뒤의 새 룩이
차례를 받는다.

### 2.1 EDM — `edm-haze-shafts` (헤이즈 샤프트)

```yaml
  - look_id: "edm-haze-shafts"
    display_name: "헤이즈 샤프트"
    genre: "edm"
    dynamics: 1
    # cyc 없는 리그의 D1. 씻을 배경막이 없으면 공기를 쓴다 — 뒤에서 오는
    # 낮고 차가운 빛이 헤이즈에 걸려 무대를 벽이 아니라 부피로 만든다.
    roles: ["백라이트"]
    aliases: ["헤이즈 샤프트", "haze shafts", "빈 플로어"]
    mood_keywords: ["차가운", "어두운", "공기", "대기", "haze", "hold"]
    attributes:
      Dimmer: 18
      ColorRGB_R: 0
      ColorRGB_G: 40
      ColorRGB_B: 78
```

- **역할 선택**: `백라이트`. EDM 헤더 규칙("관객은 부스를 본다 — 오퍼레이터를 평평하게
  비추지 않는다")이 `프론트` 를 배제하고, `탑` 은 실기 리그에서 안 묶인다. 남는 것 중
  뒤에서 오는 빛만이 배경막 없이 깊이를 만든다.
- **무대에서 보이는 것**: 플로어는 비어 있고 헤이즈만 깔려 있다. 뒤쪽 바에서 낮은
  심해빛이 관객 쪽으로 나오면서 공기 중에 흐릿한 기둥으로 선다. 사람은 실루엣도 안
  되고, 무대가 "아직 시작 안 했지만 켜져는 있다"로 읽힌다.
- **D2 와 안 겹치는가**: 다음 칸은 `edm-groove-cyan`(Dimmer 55, 청록, 사이드+백라이트).
  밝기가 3배로 뛰고 옆에서 빛이 새로 들어오며 색이 심청 → 청록으로 올라간다. 리프트가
  분명하다. `edm-intro-bed`(보라, 배경+탑)와도 색·역할이 겹치지 않는다.

### 2.2 rock — `rock-wing-embers` (윙 엠버)

```yaml
  - look_id: "rock-wing-embers"
    display_name: "윙 엠버"
    genre: "rock"
    dynamics: 1
    # cyc 없는 리그의 D1. `rock-empty-stage` 의 탁한 붉은빛을 배경막 대신
    # 윙에서 낸다 — 무대 폭만 겨우 읽히는, 곡 사이의 그 상태.
    roles: ["사이드"]
    aliases: ["윙 엠버", "wing embers", "곡 사이"]
    mood_keywords: ["어두운", "붉은", "정적", "무대 전환", "embers", "dim"]
    attributes:
      Dimmer: 22
      ColorRGB_R: 65
      ColorRGB_G: 10
      ColorRGB_B: 22
```

- **역할 선택**: `사이드`. rock 의 정체성이 "얼굴은 어둡고 형태만 있다"이므로
  (`프론트` 는 코러스에서야 온다는 헤더 규칙) D1 에 `프론트`·`스페셜` 을 쓰면 장르를
  깬다. `백라이트` 는 바로 다음 칸 `rock-verse-side` 가 이미 쓴다 — D1 에서 미리
  써 버리면 벌스 진입이 밋밋해진다. 윙만 남는다.
- **무대에서 보이는 것**: 앰프와 드럼 라이저의 옆면에만 탁한 붉은 기가 걸린다. 장비의
  윤곽과 무대 폭이 겨우 읽히고, 사람이 서 있어도 실루엣의 가장자리만 보인다. 다음 곡을
  기다리는 무대다.
- **D2 와 안 겹치는가**: `rock-verse-side` 는 차가운 청색이고 `백라이트` 가 더해진다 —
  색온도가 뒤집히고 빛의 방향이 하나 늘어난다. `rock-verse-amber-grit` 과는 둘 다
  따뜻한 계열이지만 채도·밝기가 다르고(100/45/8 @52 대 65/10/22 @22) 저쪽은 `탑` 을
  함께 쓴다.

## 3. 막힌 자리 — 최소 변경과 그것을 막는 단언

`server/looks/library/` 는 `server/tests/test_overlap_preserve.py` 의 PRESERVE
초크포인트 아래에 있고, 2026-08-02 「파란」 미러 예외만 승인돼 있다. 그 예외는
**바뀐 파일 집합 자체를 못박는다**:

```python
    def test_exactly_the_three_granted_files_changed(self):
        rows = _numstat(_PRECHK_BASE, _LOOKS_LIBRARY_DIR)
        assert set(rows) == set(_LOOKS_GRANTED_LINE_PAIRS)
```

`_LOOKS_GRANTED_LINE_PAIRS` 는 `ballad.yaml`·`edm.yaml`·`worship.yaml` 셋뿐이다.
따라서 이 디렉터리에서 **추가도 통과하지 못한다** — 새 파일이든 기존 파일에 붙인
줄이든 `_numstat` 의 키 집합을 바꾸기 때문이다. t292 가 잰 "추가는 통과한다"는
블랙리스트 항목 쪽 관측이고, 이 클래스에는 적용되지 않는다.

실측(이 브랜치, 후보 룩 하나를 `rock.yaml` 에 붙여 커밋한 뒤 그 파일만 실행):

```
FAILED server/tests/test_overlap_preserve.py::TestLooksLibraryGrantedExtension::test_exactly_the_three_granted_files_changed
E       AssertionError: assert {'server/look...worship.yaml'} == {'server/look...worship.yaml'}
E         Extra items in the left set:
E         'server/looks/library/rock.yaml'
1 failed, 53 passed in 1.26s
```

`edm.yaml` 에 붙이는 경우도 같은 클래스의 다음 단언
(`test_every_change_is_a_granted_line_pair_and_every_pair_is_present`)이
막는다 — 승인된 줄 쌍과 정확히 일치해야 하기 때문이다.

### 게이트를 여는 방법 — 처방은 게이트가 아니다

`test_overlap_preserve.py` 의 독스트링이 이미 정한 순서를 그대로 따른다:
**먼저 가는 곳은 선언 층**이다. 즉 이 룩 추가를 승인 기록으로 올리고, 그 승인에 근거해
`TestLooksLibraryGrantedExtension` 에 추가 전용 예외를 다는 것 —
`_RULEBOOK_GRANTED_ADDITIONS` 가 이미 쓰는 모양(이름으로 못박고 삭제 0줄 요구)이 선례다.
단, 원래 선언(SPEC-COPILOT-PRECHK-001 §A.5)을 낸 SPEC 은 닫혀 있고, 독스트링이
"닫힌 SPEC 의 선언을 사후에 고치는 경우는 이 선례가 덮지 않는다 — 그 판단은 이 게이트
밖이다"라고 명시한다. **감독 결정 1건이 필요하다.**

이 브랜치는 그 결정을 대신하지 않았다. 게이트를 약화시키지 않았고, 닫힌 SPEC 의
승인 목록을 고치지 않았고, 스스로 예외를 발급하지 않았다.

## 4. 게이트가 열리면 무엇이 바뀌는가

`server/tests/test_songcue_rig_aware_look.py` 의 `TestWhatThisFixCannotReach` 는
지금 이렇게 단언한다(이 브랜치에서 **안 바꿨다**):

```python
assert [look.roles for look in d1] == [("배경",)]          # edm, rock
assert _stored_cues(library, genre, "ambient", _REAL_RIG) == []   # edm, rock
```

그리고 행렬은 `{"ballad": "OOOOO", "edm": "XOOOO", "rock": "XOOOO", "worship": "OOOOO"}`.

룩이 들어가면 세 단언 모두 뒤집힌다 — D1 역할 목록이 둘이 되고, `ambient` 밴드가 큐를
받고, 행렬의 두 X 가 O 가 된다. 이 클래스의 독스트링이 이미 그 순간을 예고해 뒀다:
"라이브러리가 나중에 묶이는 D1 룩을 얻으면 이 테스트가 실패하며, 그것이 이 기록을
갱신하라는 신호다." 갱신된 문면은 `server/tests/test_songcue_d1_cycless.py` 에
미리 적어 뒀고, 룩이 없는 동안은 스스로 건너뛴다.

## 5. 안 잰 것

- 실기 콘솔에서 이 두 룩을 발사해 보지 않았다. 색·밝기는 라이브러리 안의 이웃 값에서
  역산한 설계값이지 실측값이 아니다.
- cyc 있는 리그의 무회귀 성질은 `_select_bindable` 의 「첫 묶이는 룩」 규칙을 읽고
  세운 예측이다. 룩이 없으므로 실행으로 확인하지 못했다.
- 다른 소비자(preview 분류기, busking 경로)가 D1 룩 개수를 세는지 확인하지 않았다.
