# SPEC-COPILOT-CLASSIFYGAP-001 — 구현 계획

> 되돌리기 어려운 결정을 앞에 둔다. 아래 §A~§C 가 사람이 먼저 읽어야 하는
> 판단이고, §F 의 마일스톤은 그 판단이 정해진 뒤의 기계적 순서다.

---

## §A 가장 먼저 정해야 하는 것 — 열려 있는 판단 셋

### A-1 판별 술어를 어디에 두는가 [NEEDS CLARIFICATION: 술어 소유]

두 안이 있고, 둘 다 REQ-CG-001 을 만족시킬 수 있다.

**안 1 — `blacklist.yaml` 에 항목 네 개를 넣는다.**

```yaml
- "Store Sequence"
- "Store Cue"
- "Store Group"
- "Store Timecode"
```

- 값: 폐집합 규율을 그대로 잇는다. 버전 상승·근거 기록·핀 테스트가 이미 있고,
  `_match_blacklist` 하나만 지나므로 판정 경로가 늘지 않는다.
- 대가: **비용이 크다.** 실측 71건(고유 54). 특히 `Store Cue` 단독이 62건으로
  가장 비싸다.
- 축소 변형: 네 개 대신 `Store Sequence` + `Store Timecode` 만 넣으면
  실측 비용이 크게 내려간다(각 33·6, 겹침 고려 시 합 미측정). 다만 `Store Cue 1`
  과 `Store Group 3` 이 열린 채 남으므로 REQ-CG-001 을 **부분만** 만족한다.
  받침을 놓는 SPEC 이 받침에 구멍을 남기는 셈이라, 채택하려면 남는 구멍을
  후속 카드로 명시해야 한다.

**안 2 — `write_reason.showfile_write_risk` 를 분류 층이 재사용한다.**

- 값: 두 층이 같은 답을 말한다. 봉합이 「쓰기」라 부르는 것과 분류가 「쓰기」라
  부르는 것이 정의상 일치하고, 새 쓰기 어휘가 생겼을 때 갱신 자리가 하나다.
- 대가: **방향이 반대다.** `write_reason` 은 번들 단위 **문면 생성기**(정규식
  12개, 한국어 문장 조립)이고 분류 층은 명령 단위 **폐집합 판정기**다.
  `blacklist.yaml` 헤더가 지키는 성질 — 폐집합, 리비전마다 버전 상승과 비준
  SPEC 기록, `test_safety_ruleset.py` 의 3중 핀 — 은 정규식 모듈로 표현되지
  않는다. 또한 `write_reason.py` 는 의도적으로 `server/safety/` **밖에** 있다
  (모듈 docstring: 「이 모듈은 심사하지 않는다」). 분류 층이 그것을 import 하면
  그 경계가 뒤집히고, `test_overlap_preserve.py` 의 파일 집합 핀과도 부딪친다.

**권고: 안 1.** 근거는 경계다 — 안 2 는 「심사하지 않는 모듈」을 심사 경로에
넣어 t317 이 세운 규율(가드를 약화시키지 말고 우회하라)을 거꾸로 돌린다.
다만 이것은 권고이고, 비용 71건이 감독 판단을 요구할 만큼 크다.

### A-2 비용 71건을 받아들이는가 [NEEDS CLARIFICATION: 비용 수락]

이것이 이 SPEC 의 중심 결정이다. 71건 중 몇 건이 **제품 동작 변경**이고 몇 건이
**픽스처 변경**인지가 답을 정한다. §B 의 분류가 그 재료이고,
`acceptance.md` §D.2 가 전수표를 든다.

핵심 위험을 한 문장으로: **감독이 룩 하나 만들 때마다 승인 카드가 뜨면, 감독은
카드를 안 읽게 되고 그게 진짜 쓰기를 통과시킨다.** 이 SPEC 이 막으려는 사고를
이 SPEC 이 만들 수 있다.

### A-3 큐시트 반영의 두 번째 카드 [NEEDS CLARIFICATION: 큐시트 이중 카드]

`_cue_sheet_draft_apply`(`server/web/session.py:9049·9999`)는
`approval_owned_by_caller=True` 로 **자기 승인 채널**을 갖는다. 그 자리의 번들에
`Store Cue` 가 들어 있으면, 확대 뒤 분류 층이 새로 보류를 만든다. §D-2 가 확인한
「카드 한 장」 합성은 **봉합이 붙은 번들**에 대한 성질이고, 이 자리는 봉합을
일부러 붙이지 않은 자리다 — 그래서 여기서만 감독이 카드를 두 번 볼 수 있다.

`test_web_cue_sheet_apply.py` 4건이 정확히 이 자리이고, 그중
`test_an_accepted_batch_is_asked_once_not_once_per_command` 는 이름 그대로
「한 번만 묻는다」를 지키는 핀이다. **이 4건은 갱신 대상이 아니라 신호일 가능성이
가장 높다.**

---

## §B 깨지는 테스트의 분류 원칙

일괄 갱신 금지(REQ-CG-009). 판정 질문은 하나다: **이 테스트는 확대가 옳다는
전제에서 갱신되어야 하는가, 아니면 확대가 틀렸다고 말하고 있는가?**

| 종류 | 판정 기준 | 처리 |
|---|---|---|
| 1 — 갱신 대상 | 오늘의 눈감음을 고정한 핀 / 폐집합 핀 / 재측정 전제로 설계된 귀속표 | 근거를 적고 갱신 |
| 2 — 확대가 틀렸다는 신호 | 쇼파일을 **안 고치는** 흐름이 승인을 요구하게 됨 | 갱신 금지. 술어를 좁히거나 그 자리에 봉합을 쓴다 |
| 3 — 계측 인공물 | 측정 하네스가 만든 것 | 무시(실제 리비전에서는 안 난다) |

3번은 대조군이 지목했다: 원본을 바이트 동일 복사해 다른 경로에서 돌리면
1건만 깨진다(`test_default_path_is_the_ssot_yaml_under_server_safety`).
두 번째 인공물은 `test_every_shipped_revision_is_documented_in_the_file` —
내 스크래치 파일의 리비전 주석이 `REVISION HISTORY` 블록 안에 없고 비준 SPEC
이름도 없어서 깨진다. 제대로 쓴 리비전은 이 검사를 통과한다.

전수 분류표는 `acceptance.md` §D.2.

---

## §C 비용 재측정 절차 (재현 가능, `server/safety/` 무수정)

이 SPEC 은 `server/safety/` 를 고치지 않고 확대 비용을 쟀다. run 단계도 같은
절차로 재측정한다(분모가 움직이므로).

1. 스크래치 룰셋을 만든다. 원본 문면을 보존한 채 `version` 을 올리고
   `blacklist` 끝에 후보 항목을 텍스트로 덧붙인다(주석을 지우면 리비전 문서화
   검사가 인공물로 깨진다).
2. pytest 플러그인으로 `load_ruleset` 의 **기본 인자**를 갈아끼운다. 모듈 속성만
   바꿔서는 안 먹는다 — 기본값은 `def` 시점에 묶인다:

   ```python
   _rs.DEFAULT_RULESET_PATH = p
   _rs.load_ruleset.__defaults__ = (p,)
   ```

3. `MOAI_T299_RULESET=<yaml> PYTHONPATH=<plugindir> uv run pytest -q server/tests -p widen_plugin`
4. **대조군을 먼저 쏜다** — 원본 바이트 동일 복사본으로 같은 명령을 돌려
   인공물 수를 확정한다. 대조군 없이 얻은 실패 수는 증거가 아니다.
5. 인용할 때 실패 수와 전체 수를 함께 적는다(REQ-CG-010).

인터프리터는 **이 트리의 것**을 쓴다(`uv run`). 형제 워크트리의 인터프리터를
빌리면 다른 트리의 코드를 조용히 import 할 수 있다.

측정 산출물: `reports/classifygap-t299/` — 스크래치 룰셋(`bl_*.yaml`), 플러그인
(`widen_plugin.py`), 회차별 결과(요약 + `FAILED` 목록. 트레이스백은 어디서도
인용하지 않았으므로 남기지 않았다). 각 결과 파일의 `FAILED` 줄 수가 표의 숫자와
일치하므로 표가 스스로 검산된다.

---

## §D 제약

- `server/safety/` 는 이 SPEC 의 **수정 대상**이다(안 1 채택 시 `blacklist.yaml`).
  plan 단계에서는 읽기만 했다.
- `console/lua/`, `server/looks/library/` 는 수정 금지.
- 포트 8000 접촉 금지.
- 문서·주석은 한국어(`documentation: ko`, `code_comments: ko`).
- 커밋 메시지는 t299 를 명시하고 `🗿 MoAI` 로 끝낸다.

---

## §E 자체 검증

- 확대 후 §B 프로브 재실행 → 네 명령 전부 `risky=True`.
- REQ-CG-006 의 아홉 문장 프로브 → 전부 `risky=False`.
- `SEAL_DEFENCE` 재측정 → seal-only 수 감소.
- 봉합 + 확대 동시 투입 게이트 프로브 → 승인 요청 1건.
- 전체 스위트 → 0 failed(갱신 완료 후), 전체 수 병기.

---

## §F 마일스톤 (우선순위 순, 시간 예측 없음)

### M1 — 판단 확정 (Priority High)

§A 의 세 [NEEDS CLARIFICATION] 를 감독 승인으로 닫는다. 술어 소유(A-1),
비용 수락 범위(A-2), 큐시트 이중 카드 처리(A-3). **이것이 닫히기 전에 코드를
고치지 않는다** — 술어가 바뀌면 아래 전부가 다시 돌아야 한다.

### M2 — 분류 전수표 확정 (Priority High)

54개 고유 함수를 1/2/3 종으로 판정한다. 2번이 하나라도 나오면 M1 로 돌아간다 —
2번은 술어가 틀렸다는 뜻이므로 갱신으로 넘어가면 안 된다.

### M3 — 폐집합 리비전 (Priority High)

`blacklist.yaml` v4 → v5. 항목 추가 + `REVISION HISTORY` 에 비준 SPEC 이름,
항목별 실측 비용, 전체 수를 기록. 헤더의 기존 규율을 그대로 따른다.

### M4 — 오늘의 눈감음 핀 뒤집기 (Priority Medium)

`test_writegate_merge_gap.py` 3건. 이 파일의 docstring 은 「고치는 파일이 아니라
못을 박는 파일」이라고 적혀 있고 BULKGATE 종결 기록이 「단언은 바이트 그대로」라고
못 박았다 — **이 SPEC 이 그 못을 뽑는 SPEC 이므로**, 뽑는 근거를 같은 docstring 에
이어 적는다. 조용히 뒤집으면 다음 사람이 사고로 읽는다.

### M5 — 귀속표·폐집합 핀 재측정 (Priority Medium)

`SEAL_DEFENCE` 와 `test_safety_ruleset.py` / `test_writegate.py` 의 핀들.
`UNCHANGED_SAFE` 에서 줄을 빼려면 그 줄마다 개별 근거를 적는다(그 튜플의 주석이
「한 줄 빼는 것이 나머지를 풀지 않는다」고 경고한다).

### M6 — 남는 구멍 등재 (Priority Low)

`Store Page` · `Store Macro` · `Assign Sequence` · `Copy Sequence` 와, 축소
변형을 채택했다면 그때 남는 명령을 후속 카드로 등재한다. 「분류했다」와
「안전하다」를 구별해 적는다.

---

## §G 안티패턴

- 71건을 일괄 갱신하고 초록을 성과로 보고하기. 2번 종류를 갱신하면 확대가 틀렸다는
  유일한 신호를 지운다.
- t292 의 「8건」을 그대로 인용하기. 분모가 움직였다.
- 봉합을 떼서 귀속표를 redundant 로 만들기(REQ-CG-008).
- 대조군 없이 실패 수를 보고하기.
- 시스템 `python3` 로 프로브를 돌리기. 이 저장소는 3.11 이 필요하고, 형제 트리의
  인터프리터는 다른 트리의 코드를 import 할 수 있다.

---

## §H 교차 참조

- `spec.md` §C — 항목별 실측 비용표
- `acceptance.md` §D.2 — 54개 전수 분류표
- `reports/classifygap-t299/` — 측정 산출물(추적됨)
- `server/safety/blacklist.yaml` 헤더 — 폐집합 리비전 절차의 정본
