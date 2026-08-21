# PR #72 코드 리뷰 결함 — 매퍼 폭 산정 2건 (t9 후속)

> 발견: 2026-08-21 `/code-review 72` (독립 리뷰) · **재현: 리드 세션이 직접 실행**
> 대상: `server/lxseq/mapper.py` 단일 파일 · 콘솔 접촉 불필요 (전부 오프라인 재현됨)
> 이 문서가 배차 payload 의 정본이다. 아래 「관측한 출력」은 리드가 명령을 돌려 눈으로 본 것이며,
> 리뷰어의 주장을 옮겨 적은 것이 아니다.

## 왜 감사 2회가 놓쳤나 (범위 진술 — 원인 분석 아님)

sync 감사 2회는 「거부 부류 · 점유 가드 · 커버리지 · 봉쇄 구역」을 봤다.
두 결함은 **매퍼가 세운 계획값과 콘솔이 실제로 놓을 자리가 어긋나는 축**에 있고,
그 축은 두 감사 어느 쪽의 검사 목록에도 없었다. M4 실기 86대는 **한 타입 한 모드**여서
이 갈래를 지나가지 않았다 — 즉 「아직 만나지 않은 입력」이지 이미 벌어진 사고가 아니다.

---

## D3 (HIGH) — 한 타입이 두 모드로 섞이면 주소가 밀린다

**위치**: `server/lxseq/mapper.py:384` (`if csv_type not in mode_resolutions:`) + `:463` (`boundary_key`)

**기전**: 모드 확정이 **타입당 1회**만 일어나고 그 결과를 같은 타입의 모든 행에 재사용한다.
`_resolve_mode` 는 **첫 행**의 `channels` / `mode_label` 로만 불린다. 런을 가르는 `boundary_key`
에도 `record.channels` 가 빠져 있어, 폭이 다른 행이 한 런으로 뭉치고 폭은 런 머리 값이 된다.

**재현 (리드가 실행 · 관측한 출력)**

입력 CSV 3행 — `Aura` 타입, 12ch @1.1 / **25ch** @1.13 / 12ch @1.38

```
생성된 런 수: 1
  런: {'address': '1.1', 'count': 3, 'fids': [1, 2, 3],
       'console_mode': 'Basic 12ch', 'channels_per_fixture': 12}
fid_map: {1: '1.1', 2: '1.13', 3: '1.25'}
skipped: []
```

**틀린 것 2가지**
1. FID 3 이 `1.25` 에 놓인다 — CSV 는 `1.38` 을 요구했다.
2. FID 2 는 CSV 가 25채널로 선언했는데 12채널 모드로 패치된다.

**조용하다** — `skipped` 가 비어 있어 경고가 한 줄도 없다.

---

## D4 (HIGH) — `mode_overrides` 가 실측 폭 대신 CSV 폭을 쓴다

**위치**: `server/lxseq/mapper.py:179` (override 분기의 `ModeResolution(channels=channels, ...)`)

**기전**: override 분기는 `channels=channels` — 즉 **CSV 의 `Ch`** 를 그대로 넣는다.
매칭된 실측 모드의 폭(`mode_read.modes` 중 이름이 일치하는 `ModeChoice.width`)은 버려진다.
`mode_overrides` 는 `mode_unresolved` 의 **문서상 해법**이고, `mode_unresolved` 는 애초에
「CSV 폭과 같은 실측 모드가 없다」일 때 뜬다 — 즉 override 경로는 **폭이 다른 것이 정상**이다.

**재현 (리드가 실행 · 관측한 출력)**

입력 CSV 2행 — `MegaPointe` 39ch @1.1 / 39ch @1.40 · 콘솔 실측 모드는 `Mode 2 25ch` 하나뿐
· `mode_overrides={"MegaPointe": "Mode 2 25ch"}`

```
런: {'address': '1.1', 'count': 2,
     'console_mode': 'Mode 2 25ch', 'channels_per_fixture': 39}
fid_map: {1: '1.1', 2: '1.40'}
```

**틀린 것 3가지**
1. **자기모순** — `console_mode` 는 25채널인데 `channels_per_fixture` 는 39다.
2. 콘솔은 stride 25 로 놓으므로 FID 2 의 실제 자리는 `1.26` 이다. 미리보기는 `1.40` 이라고 한다.
3. `_occupancy_skip` 의 점유 사전검사도 CSV 폭으로 돈다 —
   **실제로 쓰이는 주소는 점유 검사를 한 번도 거치지 않는다.**

> 이 앱엔 되돌리기가 없다. 「승인한 것 ≠ 콘솔이 받은 것」이 정확히 이 모양이다.

---

## 고칠 방향 (제안 — 구현자가 더 나은 안을 내면 그걸로)

1. `mode_resolutions` 의 키를 `csv_type` 단독에서 **`(csv_type, record.channels, record.mode_label)`**
   로 넓힌다. 한 타입이 두 폭으로 오면 해석도 둘이어야 한다.
2. override 분기에서 `channels` 를 **매칭된 `ModeChoice.width`** 로 바꾼다.
   (`names` 는 현재 문자열 리스트라 폭을 잃는다 — `mode_read.modes` 를 직접 순회해야 한다.)
3. `boundary_key` 에 폭을 넣어 폭이 다른 행이 한 런으로 뭉치지 않게 한다.

## 이 수정이 닫혔다고 말하려면 (수용 기준)

- [ ] D3 재현 입력이 **런 2개 이상**으로 갈리고, `fid_map` 의 모든 주소가 CSV 원본과 일치한다.
- [ ] D4 재현 입력에서 `channels_per_fixture` 가 **25** 가 되고, `fid_map[2]` 가 `1.26` 이 된다.
      (`1.40` 이 아니라 — 계획서가 콘솔의 실제 배치와 같은 말을 해야 한다.)
- [ ] 두 갈래 각각에 **회귀 테스트 신설**, 그리고 **뮤테이션 양방향 검증**:
      고친 자리를 되돌리면 새 테스트가 RED, 되돌리기 전엔 통과. 원문을 §E.2 에 남긴다.
- [ ] 전체 스위트 재측정 — 기준선 **9682 passed, 8 skipped** 대비 증가분이 신규 테스트 수와 일치.
- [ ] `git diff --quiet -- console/lua server/safety server/prechk server/vwx` exit 0 (봉쇄 구역 무변경).

## 범위 밖 — 손대지 말 것

- **D2**(FixtureType 이 이름 대신 핸들) → 카드 `t11`. 이번 커밋의 대상이 아니다.
- 리뷰 지적 **#3**(`awaited_human` 미전파 · `tools.py:4473`) · **#5**(완전성 술어 재구현 · `mapper.py:141`)
  → **리드가 재현하지 않았다.** 가설 상태이며 이번 배차에 포함하지 않는다.
- 리뷰 지적 **#4**(중복 행이 2회 거부돼 `rows_total` 이 2행 파일을 4로 보고) → 리드가 재현은 했으나
  콘솔 영향이 없고 보고 숫자만 틀린다. 여력이 남으면 같이, 아니면 `t11`.
- **콘솔 접촉 금지.** 두 결함 모두 오프라인에서 재현됐고 오프라인에서 검증된다.
