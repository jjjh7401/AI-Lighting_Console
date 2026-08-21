# PR #72 코드 리뷰 결함 — 매퍼 폭 산정 2건 (t9 후속)

> 발견: 2026-08-21 `/code-review 72` (독립 리뷰) · **재현: 리드 세션이 직접 실행**
> 대상: `server/lxseq/mapper.py` 단일 파일 · 콘솔 접촉 불필요 (전부 오프라인 재현됨)
> 이 문서가 배차 payload 의 정본이다. 아래 「관측한 출력」은 리드가 명령을 돌려 눈으로 본 것이며,
> 리뷰어의 주장을 옮겨 적은 것이 아니다.

> **라벨 주의 (2026-08-22 정정)**: 이 문서의 두 결함은 **RV1 · RV2** 다 (RV = review-originated).
> 처음엔 `D3`·`D4` 로 적었으나, 이 SPEC 에서 `D1~D7` 은 이미 **plan-audit 1회차 결함**
> (`progress.md` §Plan-phase log v0.2.0 표)이고 run-phase 의 `D1`(판독 절단)·`D2`(FixtureType 핸들)
> 와도 겹쳐, 한 글자가 세 가지를 가리키고 있었다. 리드가 만든 충돌이며 여기서 끊는다.
> **대응**: 배차 초기 메시지와 run 세션 회신의 `D3` → **RV1**, `D4` → **RV2**.
> 커밋 `3318baa`·`3561b3e` 의 메시지에는 옛 라벨이 남아 있다 — 커밋 메시지는 고치지 않는다.

## 왜 감사 2회가 놓쳤나 (범위 진술 — 원인 분석 아님)

sync 감사 2회는 「거부 부류 · 점유 가드 · 커버리지 · 봉쇄 구역」을 봤다.
두 결함은 **매퍼가 세운 계획값과 콘솔이 실제로 놓을 자리가 어긋나는 축**에 있고,
그 축은 두 감사 어느 쪽의 검사 목록에도 없었다. M4 실기 86대는 **한 타입 한 모드**여서
이 갈래를 지나가지 않았다 — 즉 「아직 만나지 않은 입력」이지 이미 벌어진 사고가 아니다.

---

## RV1 (HIGH) — 한 타입이 두 모드로 섞이면 주소가 밀린다

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

## RV2 (HIGH) — `mode_overrides` 가 실측 폭 대신 CSV 폭을 쓴다

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

- [ ] RV1 재현 입력이 **런 2개 이상**으로 갈리고, `fid_map` 의 모든 주소가 CSV 원본과 일치한다.
- [ ] RV2 재현 입력에서 `channels_per_fixture` 가 **25** 가 되고, `fid_map[2]` 는 **`1.40`**
      — 즉 **CSV 가 지정한 자리를 지킨다.**
      _개정 2026-08-22 (B안). 원문은 `1.26`(실측 폭으로 당겨 놓고 정직하게 보고) 이었다._
      _리드가 쓴 원문이 틀렸다: 「계획서와 콘솔이 같은 말을 해야 한다」만 보고_
      _「그 말이 **물리 리그와도** 같아야 한다」를 빠뜨렸다. 픽스처의 DMX 시작 주소는_
      _장비 자체에 설정돼 있으므로 `1.26` 은 정직하게 보고된 **틀린 자리**이고,_
      _콘솔은 거기 없는 장비에게 말을 걸게 된다. run 세션이 잡았다._
      _결정적 근거는 결정론이다 — A안에서는 앞 행의 탈락 여부로 뒤 행 주소가 바뀌어_
      _같은 CSV·같은 콘솔이 두 결과를 낸다. 미리보기 승인과 apply 사이에 계약이 없어진다._
- [ ] **반대 방향(더 넓은 override)** 테스트 신설: CSV 39ch @`1.1`·`1.40`,
      콘솔 실측 모드가 `50ch` 하나 → override. 런이 둘로 갈려 각자 CSV 주소를 지키면
      `1.1+50 = 1.51` 이라 **두 런이 계획 안에서 서로 겹친다.**
      계획 내부 겹침이 탐지되는지 확인한다 — 조용히 통과하면 그것이 RV2 ③ 의 나머지 절반이다
      (점유 검사가 콘솔 기존 점유만 보고 자기 계획 안의 겹침은 안 보는 것).
      이미 닫혀 있으면 그 관측 원문을 §E.2 에 남긴다 — 「확인했고 닫혀 있었다」도 증거다.
- [ ] 점유 가드 테스트의 **공허성 반증**: 점유를 **아예 걸지 않고** 돌렸을 때 그 테스트가
      실패하는지 확인한다. 통과하면 아직 공허하다. 원문을 §E.2 에 남긴다.
      _(run 세션 자진 신고 — 첫 판이 `'1.26' not in planned` 로 공허하게 통과했고,_
      _참인 이유가 FID1 탈락이었다. 리드가 판정 때 특히 의심할 자리다.)_
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

## 잔여 위험 — 고치지 말고 기록만 (`t11` 후보)

override 가 **좁은** 모드일 때 콘솔의 발자국(예: 25)이 물리 장비의 실제 폭(39)보다 좁다.
그러면 콘솔의 겹침 탐지가 **물리 현실보다 느슨해진다** — 콘솔은 안 겹친다고 하는데 실제
리그에서는 겹칠 수 있다. 이번 범위 밖이고 override 를 쓰는 사람이 감수하는 것이지만,
§E.2 잔여위험에 한 줄 남긴다.

---

# 리드 독립 검증 판정 — PASS (2026-08-22, HEAD `f07ac98`)

**판정: PASS.** 아래는 전부 리드 세션이 **직접 명령을 돌려 관측한 출력**이다.
run 세션의 §E.2 기록을 옮겨 적은 것이 아니며, 두 측정은 독립이다.

## 뮤테이션 재현 3건 — 전부 RED (양방향 확인)

기준 체크섬 `94ece98768e440fff20a0171c4f2e51c49457a1fbbae8008b5febbeb1e5a6bce`
(`shasum -a 256 server/lxseq/mapper.py`). 매회 복구 직후 `shasum -a 256 -c` **OK** +
`git status --short` **빈 출력** — 통과를 복구의 증거로 쓰지 않았다.

| # | 되돌린 것 | 관측한 출력 |
|---|---|---|
| 1 | `mapper.py:479` 점유 검사를 `record.channels`(CSV 폭)로 | `FAILED … ::test_occupancy_uses_the_measured_width_not_the_csv_width` · `1 failed, 43 passed` |
| 2 | `mapper.py:539` 런 경계에서 `_effective_width` 제거 | `FAILED … ::test_tree_unread_mixed_widths_still_keep_their_csv_addresses` · `1 failed, 43 passed` |
| 3 | 계획 내 겹침 조건을 `if False:` 로 | `FAILED … ::test_plan_overlap_created_by_a_wider_measured_mode_is_rejected` · `1 failed, 43 passed` |

**1번과 2번이 요점이다** — run 세션의 최초 뮤테이션에서 이 둘이 *통과*했던(= 공허했던)
자리이고, 신설된 갈래가 실제로 판별력을 가졌음을 리드가 독립적으로 확인했다.

> 앵커 주의: run 세션이 준 앵커 `_effective_width(record, mode),` 는 **1건이 아니라 2건**이다
> (`:479` 점유 검사 · `:539` 런 경계). 뒤 문맥으로 갈라야 한다. 리드가 행 번호로 확정했다.

## 원 재현 입력 2종 — CSV 주소를 지킨다

리드가 결함 발견 시 쓴 입력 그대로 재실행 (`repro1.py` · `repro2.py`).

**RV1** (`Aura` 12/25/12ch — CSV `1.1`·`1.13`·`1.38`)
```
런 1.1  count 1 mode 'Basic 12ch'    width 12
런 1.13 count 1 mode 'Extended 25ch' width 25
런 1.38 count 1 mode 'Basic 12ch'    width 12
fid_map: {1: '1.1', 2: '1.13', 3: '1.38'}   skipped: []
```
수정 전에는 런 1개(폭 12)에 `fid_map[3] = '1.25'` 였다. **행마다 제 모드를 갖고 CSV 자리를 지킨다.**

**RV2** (`MegaPointe` 39ch @`1.1`·`1.40`, override `Mode 2 25ch`)
```
런 1.1  count 1 width 25
런 1.40 count 1 width 25
fid_map: {1: '1.1', 2: '1.40'}
```
`channels_per_fixture` 가 **39 → 25**(자기모순 해소), `fid_map[2]` 가 **`1.40`** — 개정 기준 충족.

## 수용기준 대조

| 기준 | 관측 | 판정 |
|---|---|---|
| RV1 런 2개 이상 · `fid_map` 이 CSV 주소와 일치 | 런 3개 · 전부 일치 | PASS |
| RV2 `channels_per_fixture == 25` · `fid_map[2] == '1.40'` | 25 · `'1.40'` | PASS |
| 넓은 override 계획 내 겹침 탐지 | 뮤테이션 3 이 RED — 테스트 실재·판별력 있음 | PASS |
| 점유 가드 공허성 반증 | 뮤테이션 1 이 RED | PASS |
| 뮤테이션 양방향 + 복구 증명 | 3/3 RED · 체크섬 3/3 OK | PASS |
| 전체 스위트 기준선 대비 +9 | `9691 passed, 8 skipped, 1 warning in 140.73s` · exit 0 (9682 → **+9**) | PASS |
| 봉쇄 구역 0-diff | `git diff --stat 4d30134~1..HEAD -- console/lua server/safety server/prechk server/vwx server/paperwork server/rulebook/assets` → **빈 출력** | PASS |
| 파일 범위 | `mapper.py` · `test_lxseq_mapper.py` · `progress.md` **3개뿐** | PASS |

## 리드가 관측하지 **않은** 것 (Gaps)

- **실기 확인 0건.** 폭이 섞인 CSV 를 실제 grandMA3 에 apply 한 사람은 아무도 없다.
  두 결함 다 오프라인 재현·오프라인 검증이다. run 세션도 §E.2 에 같은 취지로 명시했다.
- **`ruff` 를 리드가 재실행하지 않았다.** run 세션 보고(`All checks passed!` ·
  `4 files already formatted`)를 읽었을 뿐이다.
- **`_reject_plan_overlaps` 의 O(n²) 비용**을 큰 리그에서 재지 않았다.
- **run 세션의 뮤테이션 6회 중 4·5번**(연속성·겹침 계열 나머지)은 재현하지 않았다.
  1·2·3번(내가 지정한 3건)만 독립 확인했다.
- **리뷰 지적 #3**(`awaited_human` 미전파) · **#5**(완전성 술어 재구현) — 여전히 미재현 가설.
  **#4**(중복 행 이중 거부로 `rows_total` 과대 보고)는 리드가 재현했으나 이번 범위 밖이다.

## 잔여 위험

- 좁은 override 는 콘솔 발자국이 물리 장비 폭보다 좁아, 콘솔의 겹침 판정이 물리 현실보다
  느슨하다. **의도된 선택**이며 이를 고정하는 테스트 본문에 그 취지가 적혀 있다 — 나중에
  결함으로 오해해 "고치는" 사고를 막기 위함이다. `t11` 후보.
- 가짜↔실물 괴리 계열(`D1` 절단 · `D2` 핸들 · 이번 폭 산정)이 **세 번째**다.
  오프라인 스위트가 원리적으로 볼 수 없는 자리가 더 있다고 보는 편이 안전하다 → `t11`.
