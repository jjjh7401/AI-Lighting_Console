## 카드 t364 — 쇼파일을 바꾸는 명령이 승인 없이 안전장치를 통과했다

`Set Layout 1.1 'PositionX' 5.0` 은 쇼파일 상태를 바꾸는 좌표 쓰기인데 `safe` 로 분류돼 승인 카드 없이 콘솔에 닿을 수 있었다. 같은 종류인 `Set Fixture 11 Posx '5.0'` 은 룰셋 v2 부터 닫혀 있었으니, 열려 있던 것은 축 하나다.

**재현 (main `c0aa6ec`, 오프라인, `validate` → `classify_command` 순수 호출, 룰셋 v8)**

```
Set Layout 1.1 'PositionX' 5.0     category=safe         risky=False   ← 승인 없이 통과
Set Fixture 11 Posx '5.0'          category=blacklisted  risky=True
Set Fixture 11 Rotx '90.0'         category=blacklisted  risky=True
```

**고친 뒤 (룰셋 v9)** — `reports/writegate-t364/05_probe_after.txt`

```
Set Layout 1.1 'PositionX' 5.0     category=blacklisted  risky=True   entry='Set Layout'
Set Layout 1.1 'PositionY' 5.0     category=blacklisted  risky=True   entry='Set Layout'
Set Lay 1.1 'PositionX' 5.0        category=blacklisted  risky=True   entry='Set Layout'
Set Fixture 11 Posx '5.0'          category=blacklisted  risky=True   entry='Set Fixture'   ← 귀속 불변
Edit Layout 1.1 'PositionX' 5.0    category=safe         risky=False  entry=None
Store Layout 3                     category=safe         risky=False  entry=None
```

## 고친 자리와 그 이유

`classify.py` 가 아니라 `server/safety/blacklist.yaml` 이다 (v8 → v9, 오브젝트 항목 `"Set Layout"`). 픽스처 축을 닫은 것도 코드가 아니라 룰셋 자산의 항목 하나(`"Set Fixture"`, v1 → v2)였고 `classify.py` 에는 명령별 규칙이 하나도 없다 — 축을 미러링한다는 것은 **그 기제를 미러링한다**는 뜻이다.

폐집합 개정 절차(REQ-MVP-013/026, "closed set changed only by version revision")는 v2 가 세우고 v3~v8 이 여섯 번 이어 쓴 것을 그대로 따랐다: **버전 범프 + REVISION HISTORY 항목 + `_would_be_held` over `load_corpus()` 비용 실측 + 항목 순서 실측**. 버전 핀 세 개(`test_safety_ruleset.py` 의 `EXPECTED_BLACKLIST` · 개수 16→17 · `version == 9`)가 설계대로 빨개졌고, 그 마찰이 헤더에 근거를 적게 만드는 장치다.

## 덮는 범위 / 안 덮는 범위

**덮는다** — 동사 `Set` + 따옴표 없는 인자 하나가 키워드 `Layout` 에 맞는 모든 줄. 오브젝트 기준이라 **프로퍼티 차원 전체**가 닫힌다: `'PositionY'`, 따옴표 없는 형태, 축약 `Set Lay …`, 좌표가 아닌 `Set Layout 1.1 Name …`(과다매칭은 설계된 방향 — 여전히 쇼파일 쓰기다). 리터럴 `'PositionX'` 하나만 잡는 규칙이었다면 `'PositionY'` 가 열린 채 남았을 것이고, 프로퍼티 이름 열거는 `blacklist.yaml` 헤더가 금지하는 open-ended list 다.

**안 덮는다** (측정했고, 의도된 경계) — 다른 동사(`Edit|Assign|Copy|Store Layout`), 복수형 `Layouts`(`Layout` 의 접두가 아니다), 오브젝트 키워드가 없는 `Set 'PositionX' 5.0`. `Set` 이 유일한 패치 쓰기 동사라는 것이 작업 가설이며, 뒤집히면 또 한 번의 리비전이 고칠 일이다.

## 실측

- **비용**: 코퍼스 21 시나리오 / 35 줄에서 **새로 보류되는 줄 0건 · 시나리오 0건**(`02_corpus_delta.txt`). v3(`LoadShow`/`NewShow`)와 같은 모양 — 이 저장소에 MA3 `Layout` 명령줄이 애초에 하나도 없다. 대표 과제 유형 누적은 v8 그대로 4/10.
- **순서**: 동사 `Set` 이 `Set Fixture` 와 겹치므로 v7 과 같은 조건이다. 목록 맨 앞으로 뒤집어 재면 귀속이 움직이는 줄이 **2건**뿐이고(`Set Fixture 11 Layout 3` · `Set Layout 1.1 Fixture 11` — 두 오브젝트 키워드를 한 줄에 담은 교차 형태), 판정은 어느 순서에서도 `blacklisted` 다(`03_entry_order.txt`). 그래서 **끝**에 두고, 그 배치 자체를 검사가 지킨다.

## 대조군 양팔

- **양성**: 재현한 줄이 `blacklisted` 로 뒤집혔고, `DenyAllApprovalPort` 아래 `SafetyGate.screen` 에서 **콘솔 송신 0건**이며 실행 포트 직접 호출도 거부된다. 매크로 본문·배포 Lua `Cmd()`·따옴표 프로퍼티 밀반입까지 간접 경로 셋 전부 막힌다.
- **음성/날조**: 고치기 전 관측은 테스트 docstring 에 그대로 남기고 단정은 **새 동작**에 건다. 안전한 줄(`Group 4`)은 게이트를 통과해 콘솔에 닿고, `Store`·MAtricks·`Set Macro`·DEPLOY 픽스처 분류는 전부 불변으로 단정한다. 비공허성 두 팔(`_would_be_held` 가 True/False 둘 다 답한다)도 검사로 고정.
- **콘솔에 아무것도 안 보냈다.** 분류기는 순수 함수이므로 직접 쟀다.

## 규율

- 코퍼스 불변식 **문면 무수정** — `server/measurement/corpus.yaml` 에 대한 diff 가 빈 출력(byte-diff 0).
- SPEC `spec.md` §D 의 「범위 밖 — Layout 요소 좌표 기록」을 만료 고지와 함께 **닫힘**으로 갱신. §E 의 정직성 기준 행도 「둘 → 하나」로 정정.
- **남은 미봉 경로 하나**: 배포 플러그인의 MA3 Lua API 직접 대입(`deploy/scan.py` 는 `Cmd()` 문자열 리터럴만 추출). 이 카드 범위 밖이고 §D 에 그대로 남는다 — 폐집합 항목으로 닫을 수 있는 종류가 아니다.

## 게이트 증거

로컬만이다. **CI 는 초록이라고 주장하지 않는다** — 이 저장소의 GitHub Actions 는 결제 문제로 잡을 시작조차 못 한다(2~4초 만에 0 스텝으로 종료, `recent account payments have failed or your spending limit needs to be increased`). 코드 실패가 아니다.

- `make ci-local` → exit 0 (`06_ci_local.txt`)
- `uv run pytest -q` → **12501 passed, 35 skipped** (`07_full_suite.txt`)
- 기준 트리: `origin/main` 과 divergence `0 0` — 머지할 것이 없어 HEAD 가 곧 `origin/main`(`c0aa6ec`) 위다.
- **미검증**: 깨끗한 환경에서의 실행. 위 둘은 개발 기계에서 잰 것이다.

🗿 MoAI
