# 세션 인계 2 — 2026-08-07 후속 (머지 · P0-5 · 측정 도구)

> **이 문서 하나로 재개할 수 있게 썼다.** 읽는 순서: §0 → §2 → §3.
> 선행 문서 `2026-08-07-session-handoff.md`는 **그 시점의 판단 기록으로 원문 보존**돼 있다.
> 뒤집힌 문장은 §1에 소급 정정으로 열거했다 — 선행 문서를 고쳐 쓰지 않았다.

---

## §0. 지금 상태

| # | PR | 브랜치 | base | 상태 |
|---|---|---|---|---|
| — | **#29** | `jjjh7401/spec-feasibility` | `main` | ✅ **머지됨** (스펙 정정 29건) |
| — | **#30** | `jjjh7401/fix-preserve-gate-prechk` | `main` | ✅ **머지됨** (#29가 깬 main 복구 — §1-③) |
| ① | **#31** | `jjjh7401/paperwork-p0-rebased` | `main` | 🟡 **리뷰 대기.** P0 4건. 리베이스 + 회귀 재측정 완료 |
| ② | **#32** | `jjjh7401/magic-sheet` | **#31** | 🟡 **리뷰 대기.** P0-5 + 측정 도구·절차서. #31 머지 후 base를 `main`으로 |

`origin/main` = `a96e4d4`. 작업 워크트리는 여전히 4개이며 배치는 선행 문서 §0과 같다.
**단 `spec-feasibility` 워크트리의 체크아웃 브랜치는 `jjjh7401/magic-sheet`로 바뀌었다** —
메인 리포가 미커밋 83건이라 리베이스를 그쪽에서 못 돌렸고, 남의 변경을 stash하지 않기 위해
우리 워크트리에서 새 브랜치로 진행했다. **`jjjh7401/paperwork-p0`(옛 브랜치)는 스테일이며
메인 리포에 체크아웃된 채 방치돼 있다** — #31 머지 후 삭제 대상.

메인 리포의 미커밋 83건은 **그대로다. 건드리지 않았다.** `git add -A` 금지 규율 유지.

### 검증 수치 (전부 리베이스 **후** 실측)

```
uv run pytest server/tests -q   → 5,358 passed / 7 skipped / 0 failed
cd ui && npm test               → 382 passed (16 files)
npx tsc --noEmit                → clean
```

선행 문서의 `4,300 green`은 스테일 기반 수치였다 — 폐기됐다.

⚠️ **`ui/`에 `node_modules`가 없으면 `npm test`가 `vitest: command not found`로 죽는다.**
새 워크트리에서는 `cd ui && npm ci` 먼저.

---

## §1. 선행 문서에서 뒤집힌 것 — 소급 정정 7건

전부 이번 세션의 실측이다. 선행 문서 원문은 보존돼 있으니 대조해서 읽어라.

### ① §3 결정 지점 (2) — `introspect-001`과의 충돌은 **없다**

선행 문서는 `spec/introspect-001`이 *"툴 개수 계약을 델타 기준으로 재정의 중"*이라
`== 23` 하드코딩과 충돌한다고 경고했다. **실측: 그 브랜치는 `server/tests/test_tools.py`를
건드리지 않는다.** 문제의 커밋 `c7780f5`는 `.moai/specs/**/*.md` 전용 문서 커밋이고,
그 본문이 명시한다 — *"절대 개수의 고정은 `test_tools.py`가 `main` 기준으로 수행한다."*
즉 우리의 절대값 단정은 충돌이 아니라 **그 문서가 지정한 역할**이다.

### ② §3 결정 지점 (1) — (a) 맨 끝 append 채택

`build_handover_pack`은 `TOOL_NAMES` 맨 끝. 자동 병합은 페이퍼워크 인접 위치(b)에
놓았으나 저장소 선례와 병합된 주석 순서에 맞춰 끝으로 옮겼다. **툴 22 → 23 → 24**
(24번째는 P0-5의 `build_magic_sheet`, 역시 맨 끝).

### ③ ⚠️ §3이 놓친 것 — **충돌은 2파일이었지만 깨진 게이트는 4곳이었다**

리베이스 자체의 충돌은 예고대로 정확히 2파일이었다. 그런데 **머지 후에 4건이 레드로
떨어졌고, 그중 하나는 `main` 자체의 결함이었다.**

| 게이트 | 원인 | 처분 |
|---|---|---|
| `test_overlap_preserve.py::test_the_predecessor_spec_documents_are_untouched` | **PR #29가 main을 깼다.** `_OVERLAP_BASE..HEAD` 형태라 이후 누가 그 디렉터리를 건드리든 영원히 실패한다 | **PR #30으로 별도 수정·머지.** 게이트를 약화시키지 않고 이 파일의 선례대로 **명명된 grant**를 얹었다 — 예외 경로 1개 + 지워진 10행을 행 키 열거 **와** sha256 두 겹으로 고정 |
| `test_truncate_disclosure.py::test_the_closed_tool_set_is_still_twenty_two` | **`test_tools.py` 옆의 두 번째 절대 툴 개수.** §3이 못 찾았다 | 델타 단정으로 교체 — 이 게이트의 실제 주제(TRUNCATE는 확인용 툴을 추가하지 않았다)를 단정한다. 절대값 소유자는 `test_tools.py` 하나 |
| `test_overlap_preserve.py::test_ruff_check_passes_on_them` | 우리 파일의 I001 | `ruff --fix` |
| (형식) | `ruff format` | 적용 |

**교훈**: 리베이스 충돌 목록은 "게이트가 깨지는 곳"의 부분집합일 뿐이다. 두 절대
리터럴이 이번 세션에만 두 번 깨졌다(18→22, 22→23) — 세 번째가 온다.

### ④ §3 미결 2 — TRUNCATE 어휘 통일: **하지 않는다** (사유 코드에 기록)

같은 사실이 아니다. TRUNCATE의 키 이동(`fixtures` → `partial_fixtures`)은 **JSON을
읽는 기계**가 부분 판독을 모르고 지나칠 수 없게 하는 장치다. 인수인계 인덱스는
**사람**이 읽고, 사람에겐 놓칠 키가 없다 — HTML에서 같은 규율의 형태는 **배치**(첫 화면)다.
매체를 넘어 살아남는 것은 REQ-TRUNCATE-004의 *"부족분은 산술로, 형용사로 말하지 않는다"*이며
그건 그대로 가져왔다. 사유는 `server/paperwork/bundle.py::_incompleteness_lines`
docstring에 있다 — 지우지 않았으니 다시 제안되지 않는다.

> ⚠️ P0-5가 이 판단의 전제 하나를 바꿨다. `build_magic_sheet`는 **실제로**
> `read_spatial_fixtures`를 호출하고 두 형상 분기를 소비한다. 즉 *"페이퍼워크는
> `partial_fixtures`를 만지지 않는다"*는 이제 거짓이며, docstring도 그렇게 정정했다.
> 결론(어휘 비통일)은 바뀌지 않았지만 **근거가 바뀌었다.**

### ⑤ §7-4 VWX 충돌 — **없다**

선행 문서는 VWX plan이 `server/paperwork/render.py`에 `render_patch_diff()`를 얹을
자리로 지목했으니 매직시트와 충돌 조율이 필요하다고 적었다. **실측:
`git diff origin/main...feature/SPEC-COPILOT-VWX-001 -- server/paperwork/` → 변경 0건.**
VWX는 자기 `server/vwx/report.py`(503줄)를 따로 만들었다. 조율 불필요.

### ⑥ §2 4️⃣ M2 — 후보는 2건이 아니라 **1건**이다

등재된 둘 중 **I-15는 이미 출하됐다** — 보수적 점유폭 상계가 곧
`SPEC-COPILOT-OVERLAP-001`(`spec.md:5` `status: completed`)이고, 애초에 라이브 측정이
필요한 후보도 아니었다(기존 실측만으로 성립하는 산술). 남은 것은 **I-14 하나**.

### ⑦ §2 4️⃣ M2 — **"비파괴 읽기"가 아니다**

I-14는 `deploy`로 콘솔에 프로브 플러그인을 **올린다**. `console/lua/**` PRESERVE는
안 깨지지만 쇼파일은 변한다. M1과 묶어 "30분 비파괴"로 돌리면 안 된다. 상세는
`docs/runbooks/2026-08-07-live-measurement-m1-m2.md` §3.

---

## §2. 다음 할 일 — 이 순서로

### 1️⃣ #31 → #32 순서로 리뷰·머지

#32의 base가 #31이다. #31이 머지되면 #32의 base를 `main`으로 바꾼다.
머지 후 스테일 브랜치 `jjjh7401/paperwork-p0` 삭제 + 메인 워크트리를 `main`으로.

### 2️⃣ 라이브 측정 M1 — **집행 준비 완료** (콘솔만 있으면 30분 미만)

절차서: `docs/runbooks/2026-08-07-live-measurement-m1-m2.md`.
발화 수단도 만들었다 — `responder_roundtrip.py`에 `--prop-path`/`--prop-name`.

```bash
uv run python -m server.tools.responder_roundtrip --expect-version 1.5.0 --skip-exec
uv run python -m server.tools.responder_roundtrip --skip-exec \
    --prop-path "DataPool/Sequences/1/Cue 1" --prop-name CueFade
```

**날조 대조군을 반드시 함께 발화하라.** 절차서 §1-3에 이유가 있다.

### 3️⃣ 쇼파일 복원 발신부 — **자체 SPEC 필요. 착수하지 않았다**

스냅샷 보관·조회·감사연결은 완료, 되돌려 올리는 발신부만 비어 있다. 자리는
`server/safety/gate.py`의 `@MX:NOTE`(`make_showfile_backup_action` 옆)에 예약돼 있고
사유는 `server/safety/backup.py:24-28`에 있다 — *"needs its own SPEC + live
calibration first"*. WRITEGATE-001이 선행의 절반을 이미 치렀다.

⚠️ **이건 M2/I-14의 선행이기도 하다.** 복원 경로가 없는 상태에서 쇼파일에 쓰는
측정을 돌리면 복구가 수작업뿐이다. 순서를 이렇게 두는 편이 낫다: **M1 → 복원 발신부
→ M2**.

### 4️⃣ 비텍스트 입력 개통 (선행 문서 §4 W8)

열면 제안서 P1-1 전반부(음원 분석)와 P3-7(이미지→룩)이 동시에 살아난다.
MA3 벽이 아니라 우리 앱 미개통 인프라다.

---

## §3. 이번 세션이 실제로 밟은 함정

1. **⚠️ 머지 전 CI가 없다.** `gh pr merge`가 그냥 머지된다 — PR #29가 그렇게
   들어가서 main을 레드로 만들었다. **머지 전에 `uv run pytest server/tests -q`를
   직접 돌려라.** 이 저장소는 체크 0건이고, PRESERVE 상시 게이트가 CI 대신이다.
2. **⚠️ `BASE..HEAD` 형태의 PRESERVE 단정은 시한폭탄이다.** 그 디렉터리를 건드리는
   **모든 후속 작업**이 깨진다. 고칠 때 게이트를 약화시키지 말고 이 파일의 선례대로
   명명된 grant를 얹어라(`test_overlap_preserve.py`의 2026-08-02 · 08-03 · 08-07 세 건).
3. **⚠️ 절대 개수 리터럴은 두 곳에 있었다.** `grep -rn "== 22" server/tests`로는
   부족하다 — 다음에 툴을 추가하는 사람은 `TOOL_NAMES`를 참조하는 **모든** 단정을
   먼저 찾아라.
4. **⚠️ 새 워크트리의 `ui/`에 `node_modules`가 없다.** `npm ci` 먼저.
5. **⚠️ 메인 리포가 더러우면 거기서 리베이스할 수 없다.** 남의 미커밋 83건을
   stash하지 말고, 우리 소유의 깨끗한 워크트리에서 새 브랜치로 리베이스하라.
   (같은 브랜치를 두 워크트리에 체크아웃할 수 없으므로 브랜치명이 바뀐다.)

---

## §4. 이번 세션 산출물

| 커밋 | 브랜치 | 내용 |
|---|---|---|
| `095cb36` | 머지됨(#30) | PRESERVE 게이트 grant — main 복구 |
| `311e966` | #31 | P0 4건 (리베이스 적응 포함) |
| `65e1fa0` | #32 | P0-5 매직시트 축약형 |
| `86b0491` | #32 | `prop` 측정 스텝 + 라이브 측정 절차서 |
| (이 문서) | #32 | 세션 인계 2 |

신규 파일:

| 경로 | 내용 |
|---|---|
| `server/tests/test_paperwork_magic_sheet.py` | 18건 — 세 읽히는 축 · 멤버십 미추론(양방향) · TRUNCATE 두 형상 · 섹션 단위 열화 · 툴 등록 |
| `docs/runbooks/2026-08-07-live-measurement-m1-m2.md` | 라이브 측정 절차서. 좌표 6건 실측 대조 완료 |
| `docs/handoff/2026-08-07-session-handoff-2.md` | 이 문서 |

---

## §5. 검증 0건 영역 — 명시

관측하지 않은 것을 보고하지 않는다. 이번 세션이 **확인하지 않은** 것:

1. **라이브 측정 M1·M2 자체** — 콘솔이 없었다. 도구와 절차서까지가 도달 범위였다.
   `prop` 스텝은 **모의 Lua 응답기**를 상대로 검증됐다(실제 onPC 아님).
2. **두 HTML 리포트의 내부 서술** — 존재와 브랜치 배치만 확인. 본문 미검증.
3. **`spec-vwx-001`·`e2e-live` 워크트리의 현재 작업 내용** — 읽기만 했고 건드리지 않았다.
   두 세션에 이번 main 변경(#29·#30)을 **통지하지 않았다** — 그쪽이 리베이스할 때
   PRESERVE grant를 만나게 된다.
4. **P0-5 매직시트의 실제 콘솔 렌더** — 모의 포트로 HTML을 생성해 육안 확인했다
   (부분 판독 케이스 포함). 실제 리그의 좌표로는 미검증.
5. **선행 문서 §5의 확정 결정 8건** — 이번 세션은 그중 5·6·8만 접했다.
