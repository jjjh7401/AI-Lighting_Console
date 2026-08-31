# t200 — primary 체크아웃이 연구 브랜치에 주차돼 있다

측정: 2026-08-31 · 워크트리 `.claude/worktrees/t200` (`WT-primary-branch-drift`) · 베이스 `f957fff`

---

## 0. 요약 — 다섯 줄

1. **카드 전제 3건 전부 재확인.** primary HEAD 는 여전히 `research/ma3-effects-phaser`(`ae8d494`)이고, `.moai/docs/lane-protocol.md` 는 거기서 안 보인다.
2. **규모: 같은 이름·다른 내용 131건.** 시끄럽게 드러나는 부재가 423건, research 에만 있는 것이 22건. 합 576.
3. 🔴 **그런데 131 은 위험 집합이 아니다.** primary 의 **미추적 잔여물**이 브랜치 diff 로는 「없음(D)」인 파일을 **디스크에서는 읽히게** 만든다. 위험 집합은 브랜치 diff 가 아니라 **primary 작업 트리**가 정한다.
4. **실물 사례를 하나 잡았다.** 인용 6건이 가리키는 `src/Lighting_Designer/02_RIG팩` 은 primary 에서 **8개 중 2개만** 답하고, 그 둘 중 하나(`.xlsx`)는 **내용이 다르다.** 아무 신호도 없다.
5. **되돌리기는 여전히 막혀 있다 — 차단 24건.** 8일 전 t3 측정과 같은 수다. 그동안 브랜치는 한 칸도 안 움직였고 main 만 154 커밋 더 갔다.

---

## 1. 전제 재측정 (착수 시점)

| 카드가 주장한 것 | 내가 잰 명령 | 결과 |
|---|---|---|
| primary 가 연구 브랜치에 있다 | `cat <primary>/.git/HEAD` | `ref: refs/heads/research/ma3-effects-phaser` ✓ |
| lane-protocol.md 가 primary 에 없다 | `ls <primary>/.moai/docs/` | `agent-lint.md` · `generic-patterns-guide.md` 둘뿐 ✓ |
| 워크트리에는 있다 | 이 워크트리에서 읽음 | 있음 ✓ (386행) |

**추가로 나온 것 — 로컬 `main` 브랜치도 낡았다.**

```
git rev-parse main research/ma3-effects-phaser origin/main
  main    453846a      <- 로컬
  research ae8d494
  origin/main f957fff

git rev-list --count --left-right origin/main...main                     -> 171  0
git rev-list --count --left-right origin/main...research/ma3-effects-phaser -> 203  4
```

로컬 `main` 이 171 뒤처져 있으므로, **어느 우주에 대고 재는지**를 먼저 정해야 한다(규약 §4.0). 이 보고서의 모든 대조 기준은 **`origin/main` = `f957fff`** 다. 로컬 `main` 을 기준으로 잰 값은 이 보고서에 없다.

**격차는 벌어지고 있다.** t3 문서(2026-08-23)가 같은 술어로 `49 4` 를 쟀다. 오늘 `203 4` 다 — 브랜치 쪽 4는 그대로이고 main 만 154 커밋 더 갔다. 8일간 아무 처분도 없었다.

---

## 2. 규모 — 카드 물음 (1)

```
git diff --name-status origin/main research/ma3-effects-phaser > <file>
cut -f1 <file> | sort | uniq -c
```

| 상태 | 건수 | 절대경로로 읽으면 |
|---|---|---|
| **M — 같은 이름, 다른 내용** | **131** | 🔴 **조용히 낡은 내용**을 답한다 |
| D — origin/main 에만 있음 | 423 | `No such file` 로 시끄럽게 드러난다 |
| A — research 에만 있음 | 22 | main 에 없던 파일이 답한다 |
| 합 | 576 | |

**M 131건이 어디에 몰려 있나** (최상위 디렉터리별):

```
server 86 · ui 12 · .moai 9 · .claude 9 · docs 3 · console 3
단일 파일 8: README.md · CLAUDE.md · CHANGELOG.md · pyproject.toml · package.json
            .gitignore · .github/workflows/label-sync.yml · config/provider.toml
```

🔴 **`CLAUDE.md` 이 M 집합에 있다** — always-loaded 하네스 파일이다. `.claude/rules/moai/` 아래 7개도 마찬가지이고 그중 `kanban-dispatch.md` 와 `agent-common-protocol.md` 가 들어 있다. 이 파일들을 primary 절대경로로 읽으면 **다른 판의 규칙**을 읽는다.

---

## 3. 🔴 그런데 131 은 위험 집합이 아니다

**존재는 도달의 증거가 아니다**(계보 `lesson-existence-is-not-reachability`). 그 렌즈로 셋을 따로 쟀다.

| 명제 | 이 카드에서 | 값 |
|---|---|---|
| **생산** — 내용이 실제로 다른가 | 브랜치 diff | M 131건 |
| **노출** — 저장소가 primary 절대경로로 그 자리를 지목하는가 | `git grep` | 아래 |
| **호출** — 그 인용이 실제로 읽히는 파일로 푸는가 | 디스크 대조 | 아래 |

### 3.1 노출 — 저장소가 primary 절대경로를 쓰는 자리

```
git grep -cI -- (primary 절대경로)     -> 43개 파일
git grep -hIo -- /Users/studiox(경로문자)*  -> 163건, 고유 40종
```

43개 파일 중 대부분은 `.moai/reports/` 와 `.moai/specs/` 의 **그 시점 기록**이다(규약 §5 — 정정 대상이 아니라 고지 대상). 접두사가 워크트리 하위경로까지 같이 잡으므로 갈랐다: 163건 중 **40건이 `.claude/worktrees/` 하위**다.

**저장소 파일을 primary 루트로 푸는 인용은 셋뿐이다:**

| 인용 | 건수 |
|---|---|
| `<primary>/src/Lighting_Designer/02_RIG팩` | 6 |
| `<primary>/src/vectorworks_export_sample_with_data.csv` | 2 |
| `<primary>` 맨 루트 (산문 언급) | 10 |

즉 **생산 131건 중 노출된 것은 두 자리뿐**이다. 131 을 「위험 자리 수」로 읽으면 65배 부풀린다.

### 3.2 호출 — 실물 사례 하나를 잡았다

두 자리를 디스크에서 직접 대조했다.

**(a) `src/vectorworks_export_sample_with_data.csv` — 안전**

```
shasum -a 256 <primary>/src/vectorworks_export_sample_with_data.csv  814c5021…
shasum -a 256 src/vectorworks_export_sample_with_data.csv             814c5021…   동일
```

**(b) `src/Lighting_Designer/02_RIG팩` — 🔴 위험이 실물로 있다**

브랜치 diff 로는 이 디렉터리의 8개 파일이 **전부 `D`**(research 에 없음)다. 「없으면 시끄럽게 드러나니 안전하다」로 읽힐 자리다. **아니다** — 그 파일들은 primary 에 **미추적으로 디스크에 남아 있다**(Aug 21). 그래서 절대경로 읽기가 **성공한다.**

```
shasum -a 256 <primary>/src/Lighting_Designer/02_RIG팩/*   -> 2개 파일만
shasum -a 256 src/Lighting_Designer/02_RIG팩/*             -> 8개 파일
```

| 파일 | primary (미추적) | origin/main | 판정 |
|---|---|---|---|
| `…r3.patch.csv` | `77a34d4b…` | `77a34d4b…` | 동일 — 안전 |
| **`…r3.xlsx`** | `a750f30c…` | `1c645919…` | 🔴 **조용히 다르다** |
| `.fx.csv` `.group.csv` `.preset-bm/col/dim/pos.csv` | 없음 | 있음 | 시끄럽게 드러남 |

**그러므로 위험 집합은 브랜치 diff 가 아니라 primary 작업 트리가 정한다.** 미추적 잔여물이 `D` 를 조용한 `M` 으로 바꾼다. 이 자리는 **디렉터리 인용**(6건)이라 더 나쁘다 — 목록을 읽는 쪽은 8개 중 2개를 받고도 그것이 전부인 줄 안다.

⚠️ 이 대조는 **두 자리**에서만 했다. 노출된 자리가 둘뿐이라 전수이긴 하지만, 「미추적 잔여물이 D 를 조용하게 만든다」는 기전이 저장소 전역에 몇 군데나 있는지는 **안 쟀다**(§7).

---

## 4. 되돌릴 수 있나 — 카드 물음 (3)

🔴 **재기만 했다. 브랜치는 안 건드렸다.** `checkout` · `switch` · `reset` 을 한 번도 안 썼다.

```
find <primary>/src/Lighting_Designer -type f | wc -l                      26
git -c core.quotePath=false ls-tree -r --name-only origin/main -- 같은 경로  30
comm -12 (디스크) (main)   -> 24     <- git switch main 을 막는 파일
comm -23                   ->  2     <- 디스크에만
comm -13                   ->  6     <- main 에만
```

**차단 24건.** t3 문서(2026-08-23)가 잰 24와 **같은 수**다. 8일간 안 줄었다.

판정 재료 넷:

1. **막혀 있다.** 미추적 24개가 덮일 자리에 있어 평범한 `switch` 는 거부된다.
2. **브랜치 고유분은 거의 없다.** t3 실측 인용 — 미머지 커밋 4개, 브랜치 고유 1,063줄인데 main 이 7,416줄 앞선다. 브랜치에만 있는 테스트 2개는 **옛 계약**이라 main 에서 19개가 빨개진다.
3. **트리에 프로세스가 붙어 있었다** (t3 실측: `codex` · `mcp-serve` · Chrome). 이 카드에서 **재측정 안 했다.**
4. **`main-checkout-branch-guard.md` 가 primary 의 브랜치 상태 변경을 [HARD] 로 금지**한다. 그러므로 이건 고칠 대상이 아니라 **살아야 하는 조건**일 수 있다 — 카드가 그 판정을 먼저 하라고 한 이유다.

**판정은 리드 몫이다.** 이 레인은 처분을 제안하지 않는다.

---

## 5. 처방 후보 — 카드 물음 (4), 판정은 리드

**후보 1 — 규약에 한 줄.** 「저장소 파일을 primary 절대경로로 읽지 마라 — primary 는 임의 브랜치일 수 있고, 미추적 잔여물이 남아 조용히 다른 내용을 답할 수 있다.」

이 카드의 실측이 그 문장을 받친다. 다만 **더 정확한 문장은 「읽지 마라」가 아니라 「읽었으면 무엇을 읽었는지 재라」**일 수 있다 — 워크트리 밖 파일을 읽어야 하는 정당한 자리가 있기 때문이다(이 카드가 그랬다: primary 의 `.git/HEAD` 를 읽어야 전제를 잰다).

**후보 2 — 인용을 상대경로나 ref 기준으로.** `git show origin/main:<경로>` 는 트리 상태와 무관하게 답한다. 이 카드에서 실제로 그렇게 쟀다(`git ls-tree`·`git diff` 전부 ref 기준).

**후보 3 — 정본 인용에는 sha256 을 같이 싣기.** 이 카드가 `.xlsx` 차이를 잡은 방법이다. 비용은 한 줄, 효과는 조용한 차이를 시끄럽게 만든다.

⚠️ 셋 다 **비용을 안 쟀다.** t198 이 처방 셋의 값을 비교하면서 「비용을 재지 않은 처방은 권고가 아니다」를 보였는데, 이 카드도 같은 상태다.

---

## 6. 측정 규율 — 내가 이 카드에서 두 번 밟았다

둘 다 규약 §4.0(0을 「없다」로 읽지 마라) 계열이다. 남겨 둔다.

**(1) 조용한 명령을 빈 결과로 읽었다.** `git grep -cI -- <primary경로> > <file>` 을 쏘고 터미널에 `(Bash completed with no output)` 이 뜨자 **매치 0건**으로 읽었다. 그건 리다이렉트라서 화면에 안 나온 것이고, **파일은 1,837바이트**였다. 43개 파일이 거기 있었다.

   판별은 한 줄이다 — `wc -c <file>`. 리다이렉트한 명령의 결과는 **화면이 아니라 파일에 물어라.**

**(2) 이름을 안 열고 부재를 판정할 뻔했다.** `ls <primary>/src/Lighting_Designer/02_RIG/` 가 `No such file` 을 답했다. 실제 이름은 **`02_RIG팩`**(한글 접미사)이다. 그대로 「primary 에 없다」로 적었으면 이 카드의 **핵심 발견이 통째로 사라졌을** 것이다 — 그 디렉터리는 있고, 내용이 다르다.

   그리고 이건 새 함정이 아니다. t3 문서가 같은 자리에서 **자기정정**을 적어 뒀다(비ASCII 경로가 `core.quotePath` 로 이스케이프돼 차단 파일을 4개로 셌다가 24개로 정정). **계보 문서가 경고한 함정을 같은 경로에서 다시 밟았다.**

---

## 7. 안 잰 것

| # | 안 잰 것 | 왜 |
|---|---|---|
| 1 | 「미추적 잔여물이 D 를 조용하게 만든다」가 저장소 전역에 몇 군데인가 | 노출된 두 자리만 대조했다. primary 미추적 전수(t3 실측 19,600개)와 main 추적 트리의 교집합을 안 쟀다 |
| 2 | primary 작업 트리의 미커밋 수정 | `git -C <primary> status` 가 워크트리 가드에 막힌다(t197 실측). 디스크 `ls`·`shasum` 으로만 우회했다 |
| 3 | 그 트리에 붙은 프로세스 | t3 가 쟀고(codex·mcp-serve·Chrome) 이 카드는 **재측정 안 했다** — 8일 지났다 |
| 4 | M 131건 중 harness 파일(`CLAUDE.md`·`.claude/rules/**`)의 실제 차이 내용 | 이름만 셌고 diff 본문은 안 열었다 |
| 5 | 처방 셋의 비용 | 정량 미측정 |
| 6 | 로컬 `main`(453846a)이 왜 171 뒤처져 있는지, 그것이 별개 위험인지 | 이 카드 밖 |

## 8. 잔여 위험

- 이 보고서의 모든 값은 **2026-08-31 시점**이다. primary 트리는 공유 자원이고 다른 세션이 붙어 있을 수 있어, **읽는 시점에 이미 다를 수 있다.**
- `.xlsx` 차이는 sha256 으로만 확인했다. **무엇이 다른지는 안 열었다**(바이너리라 비용이 든다). 「낡았다」가 아니라 「다르다」까지가 관측이다.
- 차단 24건은 **파일 이름의 교집합**이다. 그중 몇 개가 실제로 내용까지 다른지는 안 쟀다 — `switch` 거부는 이름만으로 나므로 판정에는 충분하지만, 「덮여도 손실 없음」을 말하려면 내용 대조가 더 필요하다.
