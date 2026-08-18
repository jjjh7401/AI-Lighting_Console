# 13. ASSUMPTION 3건 기계 검증 프로브 — introspect로 재공략 (T16)

응답기 1.6.1(props·introspect, `12-introspect-v161-redeploy-probe.md`가 실기 배포·재검증
완료)의 신동사로 문서 08/11번이 남긴 GAP 3건(A1 멀티스텝 실증, A2 recall+큐 보존, A3
Rectangle 파형)을 재공략했다. `verification-claim-integrity` 원칙에 따라 관측된 그대로만
적고, 좁혀지지 않은 GAP은 여전히 GAP으로 남긴다.

- 실기: onPC 2.4.2, `console_port=8000`/`receive_port=9005`
- 도구: `server.tools.introspect_probe`(props/introspect), `server.tools.responder_roundtrip`
  (exec 단발 전송, 매 호출 ping+state+exec)
- 임시 오브젝트: `Preset 4.98`, `Sequence 998` — **프로브 종료 후 둘 다 삭제 확인**(§4)
- 기존 70종·곡 데이터·상시 프리셋(4.21/4.31/4.33/4.37)에는 어떤 쓰기도 하지 않았다(조회만)

---

## A1. 저장 프리셋의 멀티스텝 실증 — **부분 실증**

`introspect DataPool/PresetPools/4/31`(Breathe Warm, 2스텝)로 전체 138개 필드 중
`property_accessors`가 노출하는 27개 고정 스키마를 확인했다:

```
ACTIVE APPEARANCE COUNT DEPENDENCYEXPORT FADERENABLED GUID HASANYMATRICKSDATA HIDDEN
IGNORENETWORK INDEX INITIALMATRICKS INITIALNAME LOCK MEMORYFOOTPRINT NAME NO NOTE
OWNED PREVIEWCOPY SCRIBBLE SHUFFLEMODE STRUCTURELOCKED SYSTEMLOCKED TAGS USEREXPANDED X Y
```

이 27개 필드 목록은 **4.21(정적)·4.31(2스텝)·4.33(Rect 근사)·4.37(3스텝) 전부 동일** —
클래스별 고정 스키마이지 콘텐츠 의존이 아니다. 이 중 스텝 수 후보로 보였던 `COUNT`와
`HASANYMATRICKSDATA`를 4종 모두 조회:

| Preset | NAME | COUNT | HASANYMATRICKSDATA | MEMORYFOOTPRINT |
|---|---|---|---|---|
| 4.21 (정적) | `Warm White#2` | `0` | `false` | `2104` |
| 4.31 (2스텝, Breathe Warm) | `Breathe Warm` | `0` | `false` | `2160` |
| 4.37 (3스텝, Rainbow) | `Rainbow` | `0` | `false` | `2164` |
| 4.33 (Chase RB) | `Chase RB` | `0` | `false` | `2176` |

**`COUNT`는 스텝 수가 아니다** — 정적/2스텝/3스텝 전부 `0`으로 동일. Preset 오브젝트
자체는 자식(child)이 없다는 뜻으로 보이며(08번 문서의 `childCount:0`과 일치), 스텝은
Preset의 자식 트리가 아니라 내부(비노출) 구조에 있다. `HASANYMATRICKSDATA`도 전부
`false` — 이 필드는 MA3의 별개 이펙트 엔진(Matricks, 픽셀 매트릭스 이펙트)용 플래그로
보이며 컬러 페이저와는 무관하다(추정, 확정 아님).

`STEPCOUNT`/`NUMSTEPS`/`PHASERSTEPCOUNT`/`MULTISTEP`/`PRESETTYPE`/`STEPS` 6개 후보명을
전부 시도했으나 **전부 `property not readable`로 거부** — 08번 문서 §6.4가 확인한
`StepCount`/`Steps` 거부에 새 후보 4종을 더해도 결과는 동일하다. `TYPE`은 읽히지만 값이
`"Preset"`(클래스명)뿐 — 스텝 정보 없음.

**`MEMORYFOOTPRINT`가 유일하게 콘텐츠에 반응하는 숫자 필드다.** 정적(2104) < 2스텝
(2160) < 3스텝(2164)로 방향은 맞지만, Chase RB(2176, 스텝 수 미확인)가 3스텝보다 커서
스텝 수와 단조 대응한다고 단정할 수 없다(이름 문자열 길이 등 다른 요인이 섞여 있을 수
있음 — 검증 안 함). **결론: 스텝 존재 자체는 `MEMORYFOOTPRINT`의 값 증가로 간접
시사되지만(정적 대비 2/3스텝이 항상 더 큼), 스텝 "개수"를 이 필드 하나로 역산할 수는
없다 — 이것으로 "실증됨"이라 부르지 않는다.** 08번 문서 §4 GAP1("스텝 개수를 기계로
셀 방법")은 introspect 경로로도 **여전히 미해결**이다.

---

## A2. recall 적재 + 큐 보존 — **여전히 불가(구조적 한계 재확인) + 새 반증 신호 1건**

### A2.1 Programmer/Selection 경로 — 11번 문서와 동일하게 거부 재확인

1.6.1에서도 재시도했으나 결과는 11번 문서 §1.1과 완전히 동일하다:

```
introspect Programmer        → "path segment not found: 'Programmer'"
introspect ProgrammerPart    → "path segment not found: 'ProgrammerPart'"
introspect Selection         → "path segment not found: 'Selection'"
introspect SelectedFixtures  → "path segment not found: 'SelectedFixtures'"
```

`props`/`introspect` 신동사도 결국 같은 `resolve_path`를 타므로 새 경로가 열리지 않았다
— 예상대로였고 새로운 GAP도 아니다(구조적 한계, `console/lua/copilot_responder.lua`의
`ROOT_ALIASES`에 Programmer/Selection 별칭이 없다는 12번 문서 인용을 재확인).

### A2.2 recall → 재저장 → introspect 대조 — **새로운 반증 신호(부분적 판독 성공)**

```
ClearAll
Group 11
At Preset 4.31                          # Breathe Warm(2스텝) 리콜
Store Preset 4.98
introspect DataPool/PresetPools/4/98 --names COUNT,HASANYMATRICKSDATA,NAME,MEMORYFOOTPRINT
```

결과:

| | 4.31 원본(2스텝) | 4.98 recall 후 재저장 |
|---|---|---|
| NAME | `Breathe Warm` | `Preset 98` (**기본 이름 — 11번 문서 §1.2와 일치**) |
| MEMORYFOOTPRINT | `2160` | **`1741`** |

11번 문서 §1.2는 "자동 이름이 중립 신호(확정도 반증도 아님)"라고 정직하게 남겼는데,
이번에 새로 얻은 `MEMORYFOOTPRINT` 값은 그 중립성을 깬다: `1741`은 A1에서 관측한
**정적 프리셋(2104)보다도 작다.** recall된 프로그래머 상태를 그대로 재저장했다면
최소한 정적 프리셋 수준의 콘텐츠(컬러 값 1세트)는 담겨야 하는데, 그보다도 작은
바이트 수로 저장됐다는 것은 **recall이 프로그래머에 완전한 콘텐츠를 싣지 못했거나,
재저장 경로가 그 콘텐츠를 담지 못했다는 쪽에 무게를 두는 정량적 신호**다. 다만
`MEMORYFOOTPRINT`가 정확히 무엇을 재는지(직렬화 바이트 수인지, 내부 구조체 크기인지)는
확인하지 않았으므로 이것도 **확정이 아니라 방향성 있는 정황 증거**로만 기록한다 —
"recall이 페이저를 통째로 싣는가"는 여전히 판독 불가로 남기되, 11번 문서 대비 GAP이
"완전 중립"에서 "약한 부정 방향 정황"으로 좁혀졌다.

### A2.3 큐 저장 — Part 트리, 여전히 판독 불가

```
Store Sequence 998 Cue 1 'A2Test' CueFade 2
introspect DataPool/Sequences/998            → COUNT=3 (OffCue/CueZero/A2Test, 11번 문서와 동일 패턴)
props DataPool/Sequences/998/3 :: COUNT,MEMORYFOOTPRINT,NAME,CUENO
  → COUNT=1, MEMORYFOOTPRINT=3088, NAME='A2Test', CUENO=not readable
introspect DataPool/Sequences/998/3/1 (그 Part)
  → 27개 필드, 4.31 Preset과 **완전히 동일한 필드 집합**(diff 0)
  → COUNT=0, MEMORYFOOTPRINT=2544, NAME='A2Test'
```

Cue의 `COUNT=1`은 Part 1개를 정확히 반영(정량적으로 맞음 — 08/11번 문서보다 진전).
그러나 Part 자체는 `property_accessors`가 **Preset과 동일한 27개 범용 스키마**만
돌려준다 — Preset 참조 여부를 가르는 필드(예: `SourcePreset`류)는 introspect의
필드 목록 어디에도 존재하지 않는다. `total: 195`(Part 전체 필드 수)이지만
`property_accessors` 소스는 항상 앞쪽 27개만 노출하는 것으로 보인다(11번 문서 §4의
"Part 트리를 한 단계 더 내려가도 판독 불가"가 introspect 경로로도 그대로 재현).
**결론: "큐가 프리셋 참조인지 평탄화인지"는 여전히 판독 불가.** `MEMORYFOOTPRINT`
(Part=2544)가 4.31 Preset(2160)보다 크다는 점은 확인했으나, 이 차이가 "참조 handle
1개를 추가로 들고 있어서"인지 "Part 오브젝트 자체의 기본 오버헤드"인지 구분할 근거가
없다 — 억측하지 않는다.

### A2.4 정리 — 원복 확인

```
Delete Preset 4.98    → ok:true
Delete Sequence 998   → ok:true (첫 시도는 포트 재바인드 충돌로 실패, 재시도로 성공)
introspect DataPool/PresetPools/4/98  → "path segment not found: '98'"  (삭제 확인)
introspect DataPool/Sequences/998     → "path segment not found: '998'" (삭제 확인)
```

두 임시 오브젝트 모두 삭제 후 재조회로 부재 확인 완료. 기존 70종·곡 데이터는 조회
전용 명령(`introspect`/`props`)만 실행해 무접촉.

---

## A3. Rectangle 파형 저장 실증 — **여전히 불가**

4.33(Chase RB, Rect 근사)과 4.31(Sine)의 `introspect` 전체 필드 목록을 diff했다 —
**차이 0개**, 두 클래스 다 동일한 27개 범용 스키마만 노출한다(4.31/4.33 필드 집합
완전 일치). 08번 문서 §3/§6.1이 실측한 페이저 레이어 커맨드(`Transition`/`Accel`/
`Decel`/`Phase`/`Speed`/`Form`/`Waveform` 이름 후보 7종)를 두 프리셋 모두에 `props`로
직접 질의:

```
TRANSITION → property not readable   (4.31, 4.33 동일)
ACCEL      → property not readable   (4.31, 4.33 동일)
DECEL      → property not readable   (4.31, 4.33 동일)
PHASE      → property not readable   (4.31, 4.33 동일)
SPEED      → property not readable   (4.31, 4.33 동일)
FORM       → property not readable   (4.31, 4.33 동일)
WAVEFORM   → property not readable   (4.31, 4.33 동일)
```

**7종 후보 전부, 두 프리셋에서 완전히 동일하게 거부됐다** — 값 차이는커녕 판독 가능
여부 자체가 구별되지 않는다. `MEMORYFOOTPRINT`는 4.31=2160, 4.33=2176로 16바이트
차이가 있으나, 이름 문자열 길이("Breathe Warm" 12자 vs "Chase RB" 8자)가 반대 방향인데도
4.33이 더 크다는 점 외에는 파형 차이를 시사할 근거가 없다 — A1에서 이미 확인했듯
`MEMORYFOOTPRINT`는 스텝 개수조차 단조 대응하지 않았으므로, 이 16바이트 차이를
"Transition 0이 저장됐다"는 근거로 쓰지 않는다. **결론: introspect/props 경로로는
Rectangle 파형이 저장됐는지 전혀 판독할 수 없다 — 08번 문서 §3/§6.1의 GAP(공식
Accel/Decel 수치 미확정 + 저장 반영 여부 미검증)이 그대로 유지된다.** 이 GAP을 닫으려면
여전히 라이브 시각 관찰(픽셀 재생 관찰)이 필요하며, 이 저장소는 OSC/Lua 전용이라
그 채널이 없다(기존 문서들과 동일한 구조적 한계).

---

## 정리 — GAP 좁혀짐 정도 요약

| ASSUMPTION | 이전 판정(08/11번 문서) | 이번 판정(introspect 재공략) |
|---|---|---|
| A1. 멀티스텝 실증 | 판독 불가(`childCount:0`, `StepCount`/`Steps` 거부) | **부분 실증** — `COUNT`는 무관함을 새로 확인(0 고정), `MEMORYFOOTPRINT`가 스텝 존재를 방향성 있게 시사하나 개수 역산 불가; 6개 후보 프로퍼티명 신규 시도 전부 거부 |
| A2. recall+큐 보존 | 완전 중립(자동 이름만, 확정도 반증도 아님) | **부분 실증(약한 부정 방향)** — `MEMORYFOOTPRINT`(1741)가 정적 프리셋(2104)보다도 작아 "완전히 실렸다"는 가설에 불리한 정량 신호 신규 확보; Programmer/Selection/Part 트리는 여전히 판독 불가 |
| A3. Rectangle 파형 | 미검증(공식 수치 없음, 시각 확인 필요) | **여전히 불가** — 후보 7개 레이어 필드명 전부, 두 프리셋에서 완전히 동일하게 거부됨(구별 신호 0) |

세 항목 모두 "완전 실증"에는 이르지 못했다 — introspect의 `property_accessors` 소스는
클래스별 고정된 범용 스키마(27개)만 노출하고, 08/11번 문서가 이미 막혔던 스텝·페이저
레이어·Programmer 내부 구조는 여전히 이 경로의 시야 밖이다. 유일한 새 신호는
`MEMORYFOOTPRINT`(숫자, 콘텐츠 크기에 방향성 있게 반응)이며, A1/A2에 정황 증거로
쓸 수 있으나 개수·존재를 확정하는 데는 부족하다. 세 GAP 모두 완전히 닫으려면 여전히
라이브 시각 관찰이 필요하다는 결론은 08/11번 문서와 동일하게 유지된다.
