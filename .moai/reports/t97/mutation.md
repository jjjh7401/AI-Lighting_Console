# t97 — 이름에 따옴표가 있으면 매퍼가 계획을 낸 뒤에 터진다

트리 `.claude/worktrees/t97` · 브랜치 `WT-quote-preflight` · 기준 `origin/main 45a631f`
측정일 2026-08-25 · 인터프리터 `uv run`(저장소 `.venv`, CPython 3.11.15)

## A. 착수 1번 — 예외가 배치 전체를 죽이나, 항목만 건너뛰나

카드 본문이 "부분 실행이면 콘솔이 절반만 찬 상태로 남는다" 를 걱정하며 이것부터
재라고 했다. **재봤고, 부분 실행이 아니다.**

수정 **전** 트리에서 `import_lxseq_presets` 를 CSV 2행(`쓰지`, `쇼'하이`)으로 호출:

| action | 관측된 출력 |
|---|---|
| `preview` | `planned` 에 둘 다 — `쇼'하이` 가 "보낼 수 있다"로 실림 · `held: []` |
| `apply` | `SpatialPointingError: preset label "쇼'하이" is empty or carries a quote` — 예외가 `registry.dispatch` **밖으로** 튐 |
| 승인 통로 | `asked: []` — 한 번도 안 물음 |
| 콘솔 발화 | `executed: []` — **0줄** |

이유는 `server/orchestrator/tools.py:4886-4888` 이 명령을 **전부 조립한 뒤에**
승인·발사로 가기 때문이다. k 번째에서 터지면 아직 아무것도 안 나갔다.

**카드가 못 봤던 것 하나**: 예외가 `ToolResult` 로 변환되지 않고 `dispatch` 밖으로
그대로 튄다. 사용자는 계획·보류·확인한계가 담긴 리포트째로 잃는다.

## B. 고친 것

1. `server/presets/store.py` — 술어 `preset_label_refusal(label) -> str | None` 를
   `__all__` 로 노출하고, `preset_store_commands` 자신도 그 술어를 부르게 했다.
   매퍼에 사본을 두지 않은 이유는 이 파일이 스스로 못박은 규율("문형을 아는 유일한
   자리 — 새 자리에 같은 문형을 적지 마라") 때문이다. 사본이 생기면 판정기와
   발사기가 갈라져, 한쪽만 바뀐 날에 계획이 통과시킨 이름에서 빌더가 터진다.
2. `server/lxseq/preset_mapper.py` — `NAME_UNSENDABLE` 보류 클래스 신설.
   거르는 자리는 **배정 전**이다(`name_taken` 과 같은 자리·같은 이유): 배정 후에
   거르면 쓰지도 않을 슬롯을 예약해 없는 부족분이 생긴다. 거절 판정보다도 앞이라
   풀을 못 읽어 0건이 된 회신에도 이 보류가 실린다 — 시트를 고칠 근거는 콘솔
   상태와 무관하기 때문이다.

`already_present` 가 아니라 `held` 에 넣었다. REQ-IDEM-003 이 둘을 섞지 말라는
근거는 "파서 판정 집계가 콘솔 상태에 따라 달라진다" 인데, 따옴표 판정은 콘솔
상태를 전혀 안 보므로 그 성질이 깨지지 않는다.

## C. 뮤테이션 — 4/4 KILLED

명령 `uv run pytest -q server/tests/test_lxseq_preset_quote_names.py`
복원은 백업 + `shasum -a 256` 대조(‎`git checkout` 은 미커밋분을 날린다).
각 회차에서 치환 대상이 정확히 1개임을 확인했다 — 0개면 "적용 안 됨"이지
"살아남음"이 아니다.

| 축 | 죽인 것 | 판정 | 빨개진 검사 |
|---|---|---|---|
| M1 | 매퍼 필터 갈래 통째 제거 | KILLED | 6 |
| M2 | 술어에서 겹따옴표 팔 제거 | KILLED | 2 |
| M3 | 보류를 안 싣고 조용히 버림 | KILLED | 5 (세 바구니 합 포함) |
| M4 | 빈 라벨 갈래 제거 | KILLED | 4 (기존 `test_presets_store` 3건 포함) |

M4 는 이 카드가 안 건드린 기존 검사도 함께 빨갛게 만든다 — 술어를 한 자리로 모은
결과 기존 보증이 새 술어에 걸렸다는 뜻이다.

## D. 전량

```
uv run pytest -q            → 10333 passed, 12 skipped (164.99s)
uv run ruff check <3파일>   → All checks passed!
uv run ruff format --check  → 3 files already formatted
```

## E. 안 잰 것 (Gaps)

- **실기 미검증.** 콘솔에 실제로 쏴서 따옴표 이름이 held 로 떨어지는지는 안 쟀다.
  쓰기 승인 영역이라 범위 밖에 뒀다. t96 과 같은 성격의 잔여다.
- **첫 빨강이 약했다.** 재현 테스트의 최초 실패는 `ImportError`(수집 실패)였고
  행위 단언이 빨간 것을 본 것은 뮤테이션 회차에서다. 판정력의 근거는 C 표다.
- **콘솔 파서의 겹따옴표 취급 미확인.** 겹따옴표도 막은 것은 빌더가 이미 막고
  있어서지, 콘솔이 겹따옴표를 구분자로 본다는 실측이 있어서가 아니다.
- **다른 이름 위험 문자 미조사.** 세미콜론·개행 등 다른 문자가 문법을 깨는지는
  안 봤다. 술어가 한 자리에 모였으니 넓힐 자리는 `preset_label_refusal` 하나다.

## F. 잔여 위험 (Residual)

- `preset_store_commands` 는 `pool_no`·`preset_no` 로도 던진다. 이 경로는 이번에
  안 막았다 — 매퍼가 슬롯을 콘솔 응답에서 받으므로 지금은 양수가 보장되지만,
  보장이 깨지면 같은 형태(계획 낸 뒤 예외)로 다시 난다.
- 예외가 `ToolResult` 로 안 바뀌고 `dispatch` 밖으로 튀는 성질은 그대로다.
  이번 수정으로 라벨 축은 막혔지만 성질 자체는 남아 있다 — 별도 카드감이다.
