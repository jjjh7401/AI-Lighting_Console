# 콘솔 실측 상태 + 막는 것 둘 — 2026-08-30

> 리드 세션 인계. **콘솔 쓰기 0** — 읽기와 preview 만.
> 기준 `origin/main` `5d31690`. onPC pid **38706**.

## 1. 채널 신뢰성 — 대조군 둘 다 통과 (이걸 먼저 세웠다)

    판독 채널  실재 경로 ok / 날조 경로 "path segment not found"     trustworthy
    쓰기 채널  ZZZNOTACOMMAND -> "Illegal object" (executed_ok 아님)  trustworthy

포트 점유는 응답을 뜻하지 않으므로 매번 이걸 먼저 쏜다.

## 2. 지금 콘솔은 grandMA3 **기본 쇼파일**이다 — 우리 리그가 아니다

이름을 읽어 확정했다(개수만 보고 판단하면 틀린다 — 리드가 한 번 틀렸다):

| 항목 | 값 | 정체 |
|---|---|---|
| 그룹 5 | `All Fixtures` · … · `Mac Aura XB` | **장비 종류별 기본 그룹** |
| 딤 프리셋 20 | `Dim 10` … `Slam Run` | **MA3 기본 프리셋** |
| 포지션 프리셋 20 | `Home` … | **MA3 기본 프리셋** |
| 시퀀스 1 | `Default`, 큐 2개 | 빈 쇼 |
| 픽스처 80 | (17개만 회신 — 절단) | — |
| 플러그인 5 | 슬롯1 `CopilotResponder` + 패치 플러그인 4 | **사본 얽힘 없음** |

RIG 팩 이름(`ALL`·`KEY`·`FOH`·`BACK`·`SIDE-L`)도 우리 프리셋 이름(`풀`·`쇼 하이`)도
**하나도 없다.** 지난주 t114 가 만든 슬롯 7 `쇼 하이`(85%)도 사라졌다.

**이건 오히려 좋은 조건이다** — 덮어쓸 감독 작업이 없으므로 리그를 처음부터 잡을 수 있다.

## 3. 막는 것 ① — 픽스처 타입이 콘솔 라이브러리에 없다

`lxseq_e2e --action preview` 실측:

    런 1개 · 계획 1대 · 건너뛴 행 **85건**
    skipped[*].kind = "type_unresolved"
    "콘솔 라이브러리에 없다 — 콘솔에서 타입 추가 후 재실행하라"

**점유가 아니다.** 타입이 없어서다.

| 콘솔에 있는 8종 | RIG 팩이 요구하는데 없는 것 |
|---|---|
| Robin Esprite · Robin Forte HP · Robin LEDBeam 350 · Robin Spiider · Xtylos · Sharpy Plus · Robin MMX Spot · Mac Aura XB | **ETC S4 LED S3 Lustr X8** · **Elation CUEPIX Blinder WW2** · **Martin Atomic 3000 LED** · **Look Unique 2.1** · **Robe MegaPointe** · Martin… |

🔴 **자동화 경로가 없다.** 픽스처 타입 라이브러리 추가는 콘솔 GUI 전용
(`Patch → Import Fixture Type`)이다. **감독 작업이다.**

## 4. 막는 것 ② — 응답기가 1.6.1 을 물고 있다

    디스크 (~/MALightingTechnology/.../copilot_responder.lua)  VERSION 1.6.2  osc_slot 2
    콘솔 (ping 회신)                                            **1.6.1**

t104 가 겪은 그 자리다 — **풀 캐싱**. `Import Plugin` 이 `executed_ok "OK"` 를 내도
콘솔은 옛 버전을 계속 답한다. **판정 기준은 콘솔이 답하는 version 이지 명령 결과가 아니다.**

결과: 프리셋 풀이 `childCount 20` 인데 19개만 회신(절단) → 임포트 하네스가
`pool_truncated` 로 **fail-closed**. 1.6.2 의 페이징이 이걸 푼다(t104 가 138개 열거 확인).

🔴 **자기 자신을 지울 수 없는 구조**라 별칭 스왑이 필요하다(README §2.2).
GUI 재임포트가 훨씬 싸다: `Plugins 풀 → 슬롯 1 → Import/Export → Import`.
**감독 작업이다.**

## 5. 그래서 순서가 정해진다

    감독 GUI ①  픽스처 타입 8종 추가        -> 패치 85행이 풀린다
    감독 GUI ②  응답기 재임포트 (1.6.2)     -> 절단이 풀려 프리셋이 들어간다
    그다음      patch -> group -> preset    (임포트 경로 전부 있음)
    병렬 가능   fx·cue 어댑터 설계          (콘솔 무관 — 코드 작업)

`cue-ex.csv` 가 `COL.01`·`POS.03`·`FX.02` 를 참조하므로 **프리셋이 먼저 있어야
큐가 그것을 가리킬 수 있다.** 순서 의존이 문서에 박혀 있다.

## 6. 매핑표는 레인 판이 정본이다

리드와 레인이 **서로 모른 채 같은 조사**를 했고 **같은 결론**(`fx.csv`·`cue-ex.csv`
둘이 빈칸)에 도달했다 — 독립 재현이라 신뢰도가 올라간다.

**정본: `.moai/reports/t126/doc-tool-map.md`** (PR #179, main `5d31690`).
7폴더 31파일 전수 + `preset-pos` 부재가 결함이 아니라는 판정(REQ-LXSEQ3-002)까지 있다.
리드 판(PR #178)은 중복이라 닫았다.

## 7. 안 잰 것

- **픽스처 타입 추가 후 패치가 실제로 되는지** — 타입이 없어 preview 까지만
- 응답기 재임포트 후 페이징이 이 쇼파일에서도 되는지
- 그룹 임포트 preview (패치가 선행이라 아직 의미 없음)
- **fx·cue 어댑터의 설계** — 입구가 없다는 것까지만 쟀고 어떻게 만들지는 미착수
