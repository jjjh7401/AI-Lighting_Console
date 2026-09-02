# t226 — WT-degenerate-guard 를 origin/main 위에 얹고 두 변경을 합친다

베이스: `origin/main 45a8307` · 브랜치: `WT-degenerate-guard` (PR #271 제자리 갱신)
환경: 자체 워크트리 · 자체 venv(`uv sync --group dev`) · `PYTHONDONTWRITEBYTECODE=1`
콘솔: onPC LIVE, 응답기 1.6.2, `--listen-port 9005`, **쓰기 0**

## 1. 무엇이 충돌했나

`git merge origin/main` 이 낸 충돌은 **한 파일뿐**이다.

| 파일 | 결과 |
|---|---|
| `server/lxseq/position_derive.py` | 자동 병합 (충돌 0) — 다만 **의미 검산 필요**, 아래 §2 |
| `server/tests/test_lxseq_position_derive.py` | 충돌 3 헝크 |
| `server/spatial/pointing.py` | t222 만 건드림 — 충돌 없음 |
| `server/orchestrator/tools.py` · `spatial/presets.py` · `tools/lxseq_coords_write.py` | main 만 건드림 — 충돌 없음 |

검사 파일 충돌 3 헝크는 **전부 순증**이라 합집합으로 풀었다:

1. 임포트 — HEAD `_cause_of` · `_skip_for_unaimable` / main `console_label_head`
2. 임포트 — HEAD `rig_is_degenerate` / main `preset_id_from_console_head`
3. 파일 끝 클래스 블록 — HEAD `TestDegenerateRig`(10) + `TestUnaimableReasonSplit`(5)
   / main `TestConsoleDropsTheDotInLabels`(4). 세 클래스 모두 살렸다.

한쪽을 통째로 택한 헝크는 **없다**.

## 2. 자동 병합이 옳았는가 — 교차점 한 줄

두 변경이 실제로 만나는 곳은 `derive_position_presets` 의 라벨 조립 한 줄이다.
t222 는 그 위(퇴화 가드·세 갈래 사유)를, t224 는 그 줄 자체와 인자를 고쳤다.
병합 결과:

    label=f"{console_label_head(row.preset_id)} {rule.stage_meaning} · {suffix}"

즉 t224 의 한 자리 변환 + 호출자 지정 꼬리가, t222 의 가드를 통과한 행에도
그대로 걸린다. 보존된 것을 하나씩 확인했다:

- t222 술어 `rig_is_degenerate` 와 코퍼스 8종 근거 독스트링 — 그대로
- 세 갈래 사유 `unaimable` / `target_coincides` / `unaimable_mixed` — 그대로
- 135° 상한이 다른 기종에서 온 **가정**이라는 고지 — 그대로
- t224 의 `console_label_head` / `preset_id_from_console_head` 한 자리 변환 — 그대로
- t224 의 `label_suffix` 인자와 빈 꼬리 거절 — 그대로

## 3. 두 방향 검증 — 같은 86 대 FID

| 방향 | 좌표 | 산출 | 거절 | 증거 |
|---|---|---|---|---|
| 퇴화 | 정본 CSV 의 86 대, 전부 `(0,0,0)` | **0** | `degenerate_rig` 6 행 | `evidence/degenerate_direction.json` |
| 라이브 | 콘솔이 답한 86 대 실좌표 | **6** | 없음 (`skipped: []`) | `evidence/live_preview.json` |

명령줄(라이브):

    uv run python server/tools/lxseq_pos_e2e.py \
      --pos-csv ... --patch-csv ... --group-csv ... \
      --action preview --limit 0 --listen-port 9005

`--action preview` 이고 `--approve` 가 없으므로 콘솔에 아무것도 안 닿는다 —
산출물의 `approval_requests` 가 `[]` 다. 되읽은 풀(`DataPool/PresetPools/2`)은
`child_count 6` · 이름 6 건이 t224 가 남긴 「합성좌표」 라벨 그대로였고, 이번 회차는
그것을 **건드리지 않았다.**

라이브 산출 라벨의 첫 어절은 전부 점 없는 콘솔 형태다 — `POS01 …` ~ `POS06 …`.
즉 가드를 통과한 6 행이 t224 의 왕복 형태를 그대로 지고 나간다.

퇴화 방향의 사유 문면:

    좌표 86대를 읽었지만 수평 폭이 없다 (x span 0.000m · y span 0.000m <= 0.05m)
    — 목표점이 한 점으로 접혀 산출값이 무의미하다. 리그 좌표를 콘솔에 넣어야 풀린다

## 4. 회귀 — 이 트리에서 직접 쟀다

| 트리 | 결과 |
|---|---|
| `origin/main 45a8307` (detached, 같은 venv) | **10779 passed, 12 skipped** |
| 병합 커밋 `3ae0f7c` | **10793 passed, 12 skipped** (+14 = t222 가 더한 수) |
| 최종 (t226 합성 검사 3 건 추가) | **10796 passed, 12 skipped** (+3) |

t224 의 34 건은 이미 baseline 안에 있다 — 그래서 병합 델타가 34 가 아니라 14 다.
배차서의 숫자를 옮기지 않고 세 값을 전부 이 트리에서 새로 쟀다.

## 5. 뮤테이션

세 회차 전부 `assert mutated != original` 로 「적용 안 됨」 갈래를 배제했다.
상세: `evidence/mutation.txt`

| # | 자극 | 죽은 검사 |
|---|---|---|
| M1 | `rig_is_degenerate` -> `return False` | `TestDegenerateRig` 6 건 |
| M2 | 라벨을 `row.preset_id` 로 되돌림 | 라벨 3 건 (두 파일) |
| M3 | 빈 꼬리 검사를 퇴화 가드 뒤로 이동 | t226 합성 검사 1 건, **나머지 68 건 통과** |

M3 이 대조 두 팔을 한 번에 준다 — 새 검사가 잡고(팔 1), 기존 상태는 못 잡는다(팔 2).
즉 「빈 꼬리 -> 퇴화 가드」 순서는 t226 이전에 아무도 안 지키고 있었다.

## 6. 코드 밖으로 고친 것

모듈 독스트링의 「병목은 여전히 좌표 데이터다」는 t222 시점 서술이고 t224 뒤에는
거짓이다. 규약 §5 에 따라 **처방·현재상태 서술이라 고쳤다** — 숫자를 지우지 않고
「가드가 붙던 시점」으로 시점을 박은 뒤, 좌표가 들어온 뒤의 두 방향 표를 붙였다.

## 7. 안 잰 것

- **빔 착지**. 산출물은 `unverified: ["field_record"]` 를 그대로 달고 나온다 —
  기하 계산값이지 현장에서 빔이 어디 떨어지는지 본 값이 아니다. 이 회차는 콘솔에
  쓰지 않았으므로 실제 무빙헤드가 움직이는 것도 못 봤다.
- **135° 조준 상한**. t222 가 「다른 기종에서 온 가정」이라 고지했고, 이 회차도
  이 쇼 기종의 가동범위를 재지 않았다. 고지만 보존했다.
- **큐 조인 끝단**. POS 슬롯이 풀린 뒤 큐 18 개가 실제로 나가는지는 이 카드
  범위 밖이고, 콘솔 쓰기가 필요해 안 쟀다.
- **중간 폭 리그**. 두 방향은 폭 0 과 실좌표 두 끝만 쟀다. 임계 근처(0.05m 부근)는
  단위 검사(`test_the_threshold_is_borrowed_not_restated`)로만 덮여 있고 실기로는
  안 쟀다.
- **다른 소비자**. `derive_position_presets` 호출자는 `lxseq_pos_e2e.py` 하나뿐임을
  `grep -rn "derive_position_presets" server --include="*.py"` 로 확인했지만,
  대화 경로(`session.py`)가 같은 풀에 쓰는 갈래는 이 카드에서 안 봤다
  (`docs/capability-index.md` 의 「두 경로가 같은 풀에 쓴다 — 미측정」).
