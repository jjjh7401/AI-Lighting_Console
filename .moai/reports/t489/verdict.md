# t489 판정서 — 컨셉 구간 재매핑 오분류(Pre-Chorus·Post-Chorus·Outro)

- 카드: t489 (Class B — 원인 미확정 결함, plan 생략)
- 브랜치: `WT-section-remap` (배차서대로)
- 워크트리: `.claude/worktrees/t489`
- base: 착수 시점 `origin/main` (`git rev-list --left-right --count origin/main...HEAD` → `0 0`)
- venv: 이 트리 자체 `uv sync --group dev` (종료코드 0)

## 판정: PASS

## 1. 원인 (재현 명령 + 출력)

`server/concept/gates.py` `remap_baseline_sections` 의 분기:

```
elif name == "Finale":           section = "Outro"
elif name in ("Intro", "Verse", "Chorus", "Bridge"):  section = name
else:                            section = "Rap/Solo/Dance Break"
```

- 이 함수는 프로토타입 `doc_sections()` 를 옮긴 것이고, 프로토타입의 입력은 **판정기 역할 5종**(intro·verse·chorus·bridge·finale, `vocab.py` `CLASSIFIER_ROLES`)뿐이었다. 그래서 `Pre-Chorus`·`Post-Chorus`·`Outro` 라는 이름이 들어올 일이 없었다 — **의도된 배제가 아니라 상정 밖 입력**이다.
- 9종 어휘(`vocab.py` `SECTIONS`, REQ-005)에는 셋 다 이미 있다. `density.py` 의 else 분기 주석도 「Pre-Chorus(판정기가 직접 낸 경우)」를 상정한다.
- 직접 지시 경로는 자유 라벨을 그대로 `baseline_name` 으로 넘긴다(`session_bridge.py:135` `decision.section.label`). `session_bridge.py` 독스트링 「알려진 격차」가 이미 이 폴백을 적어 두었다.

재현(RED): `uv run pytest server/tests/test_concept_section_remap_t489.py -q` → `4 failed, 3 passed` (`red_before.txt`). 실패 넷 모두 기대 이름 자리에 `Rap/Solo/Dance Break` 가 나왔다.

원인 검증: 그 값을 내는 코드는 위 `else` 한 줄뿐이다 — 증상이 아니라 원인이다.

## 2. 8곡 전체 오분류 수

`pilot_baseline.json` 10곡 중 유효 8곡, 111구간:

```
heads {'Intro': 8, 'Chorus': 55, 'Bridge': 9, 'Verse': 31, 'Finale': 8}
fallback {}
```

**0/111.** 8곡은 판정기 이름만 쓰므로 이 결함을 원리적으로 못 잡는다. 오분류는 자유 라벨 경로에서만 난다 — t486 실경로 곡은 **3/10**(Pre-Chorus 1·2, Outro). 그래서 8곡 게이트 기준선은 이 수정으로 움직이지 않는다(새 시험 `test_pilot_fixture_has_no_fallback` 이 0 을 잠근다).

## 3. 수정

`name in (...)` 튜플에 `Pre-Chorus`·`Post-Chorus`·`Outro` 를 더했다(1줄) + 독스트링에 t489 근거. `Finale → Outro`, 미지 라벨 → 폴백, 마지막 후렴 승급은 그대로다(시험 3개가 잠금).

- GREEN: `7 passed` (`green_after.txt`)
- 뮤테이션: 튜플에서 `Post-Chorus` 만 빼면 `1 failed, 6 passed` (`mutation_post_chorus.txt`) — 시험이 이름 하나 단위로 문다.

## 4. 기존 시험 4개가 움직였다 — 버그를 잠그고 있었다

관련 32파일(`server.concept` / `concept_report` 를 import 하는 전부): 고친 직후 `4 failed, 594 passed`. 같은 넷을 고치기 전 코드로 돌리면 `17 passed`(`related_before.txt`) — 내 변경이 움직인 것이다.

원인은 t455 곡(…Chorus 3 → Outro)의 행 차이 하나다(`rows_before.txt` ↔ `rows_after.txt`, `row_diff.py`):

```
< 19 150.0 section Rap/Solo/Dance Break 1 None
< 20 166.0 safety Outro 0 None
< rows: 20
---
> 19 148.0 phrase Final Chorus 1 드롭 직전의 정적
> 20 150.0 section Outro 1 None
> 21 166.0 safety Outro 0 None
> rows: 21
```

### 리드 조건 — REQ-038 문면과 판단

`spec.md:213`:

> REQ-LDDESIGN-038 | **When** 마지막 후렴(Final Chorus)과 Outro 사이의 간격이 3마디 이상이면, 컴파일러는 **SHALL** Outro 진입 직전 1마디 지점에 눈 리셋 프레이즈 큐(밝기를 대폭 낮춤, 트리거 "드롭 직전의 정적")를 삽입한다.

`acceptance.md` AC-032: 「Outro 진입 조건을 만족하는 곡은 눈 리셋 큐가 정확히 1개 있다(REQ-038, 조건 미충족 곡은 n/a)」.

**판단: 맞는다.**
- 자리: REQ-038 이 지정한 자리가 바로 Final Chorus → Outro 경계다. 간격 = 150 − 125 = 25초 = 12.5마디(120 BPM, 1마디 2초) ≥ 3. 삽입 시각 = 150 − 1마디 = 148.0 ✓
- 동작: 큐의 op 는 `reduce factor 0.3`(`density.py`) — 「밝기를 대폭 낮춤」 ✓
- 트리거 이름 「드롭 직전의 정적」은 스펙이 이 자리에 붙인 어휘다 — 코드가 지어낸 것이 아니다.
- AC-032 기준으로는 고치기 **전이 위반**이었다(조건을 만족하는 곡에 눈 리셋 0개 — Outro 가 폴백 이름이라 조건 검사에 안 걸렸다). 고친 뒤 정확히 1개.

그래서 21 로 잠갔다. 리드가 짚은 「Outro 는 드롭이 아니다」는 **스펙의 트리거 어휘 선택**에 대한 지적이고, 구현이 스펙과 어긋나는 것은 아니다 — 관찰로만 남긴다(카드로 세울지는 리드 판단).

### 고친 기대값

| 파일 | 바꾼 것 |
|---|---|
| `test_runbook_payload_t455_t456.py` | 행 수 20 → 21(두 곳), q 범위 1..21, safety 는 q21, 새 단언: q20 = (Outro, 화면 7), q19 = (드롭 직전의 정적, 화면 6) |
| `test_concept_reserve_t461.py` | `unused_groups` 에 눈 리셋 행 `1` 과 Outro 행 `9` 가 들어감(이전 Rap 폴백 retain 은 `1`) — 실측 `reserve_after.txt` |

재실행: 관련 32파일 `598 passed` (`related_after.txt`).

## 5. 실경로 곡(t486 프로브) — 전후

`brightness_probe.py`(t486 원본 복사)를 이 트리에서 돌렸다(`brightness_probe_after.txt`):

| 구간 | 고치기 전 컨셉 구간 | 후 | 설명 최대 % 전 → 후 |
|---|---|---|---|
| Pre-Chorus 1 | Rap/Solo/Dance Break | Pre-Chorus | 45 → 45 |
| Pre-Chorus 2 | Rap/Solo/Dance Break | Pre-Chorus | 38 → 38 |
| Outro | Rap/Solo/Dance Break | Outro | 100 → 20 |

10구간 전부 제 칸이다. Pre-Chorus 의 설명 값이 안 바뀐 것은 정상이다 — `density.py` 가 Pre-Chorus·Post-Chorus·Rap 을 같은 else 분기(retain)로 다룬다. Outro 는 Outro 규칙(KEY·BACK 20)을 타서 100 → 20 이 됐다.

`sheet == description: 1/10` 은 그대로다 — 시트 값과 설명 값이 갈리는 건 t486(lane-1) 이 다루는 축이고 이 카드 범위 밖이다.

## 6. 부수 관찰 — Pre-Chorus D4 → KEY 40 이 Verse D3 → 70 보다 낮은 원인

`prechorus_key_probe.py` → `prechorus_key_probe.txt`:

```
label | D | KEY | pre_drop_from | KEY without pre-drop darkness
Verse 1 | 3 | 70.0 | None | 70.0
Pre-Chorus 1 | 4 | 40.0 | 90.0 | 90.0
Bridge | 2 | 20.0 | 50.0 | 50.0
```

D4 예산만으로는 Pre-Chorus 가 **90**(Verse 70 보다 높다). `song_cue_composer._apply_pre_drop_darkness`(정본 §8 「드롭 앞 어둠」, 카드 t462)가 후렴(chorus·drop 행) **바로 앞** 큐를 그 행의 `darkness_target` 으로 내린다 — pre-chorus·build 행은 40. Bridge 도 같은 규칙으로 50 → 20. 대조군(그 함수만 끔)에서 90 으로 돌아온다. **의도된 규칙이지 결함이 아니다** — 카드 지시대로 원인만 기록한다.

## 7. 안 잰 것

- 전체 스위트는 로컬에서 안 돌렸다 — 관련 32파일만(lane-local 규약). 전체는 CI 가 PR 헤드에서.
- UI(`npm test`) 안 돌림 — 서버만 바꿨다. UI 시험은 서버를 부르지 않고 **저장된 사본** `ui/src/components/runbookServerPayload.json`(t458 이 뜬 서버 실출력)을 읽는다. 그래서 CI 는 초록으로 남지만, 🔴 **그 사본이 이 버그의 출력을 담고 있다**: `grep -c "Rap/Solo/Dance Break"` → `1`(옛 Outro 행), 행 수 20(`runbookM7Third.test.tsx:35` 가 잠금). 사본을 읽는 곳은 3곳 — `runbookPreview.tsx`(미리보기 화면), `runbookMibWarning.test.tsx`, `runbookM7Third.test.tsx`. 다시 뜨는 것은 UI 범위이고 lane-1·2 가 컨셉 패널 쪽을 고치는 중이라 이 PR 에 넣지 않았다 → **별도 카드 제안**(사본 재생성 + 20→21).
- `Post-Chorus` 는 단위 시험으로만 확인했다 — 실경로 곡에 Post-Chorus 라벨이 든 사례로는 안 쟀다.
- 라벨 대소문자·오타(`pre-chorus`, `PreChorus`)는 여전히 폴백이다 — `split(" ")[0]` 정확 일치라서. 이 카드는 9종 어휘와 같은 표기만 고쳤다.
- t486(lane-1)·t485(lane-2) 와 파일 겹침: 내가 고친 건 `gates.py` 와 시험 3파일이다. t486 이 `test_runbook_payload_t455_t456.py` 를 건드리면 머지 때 충돌 가능.
