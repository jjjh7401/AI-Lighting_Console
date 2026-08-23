# SPEC 감사 보고서 (2회차) — SPEC-COPILOT-BLOCKED16-001

회차: 2/3
감사 대상: `spec.md` v0.4.0 · `plan.md` v0.3.0 · `acceptance.md` v0.3.0 · `progress.md`
기준 트리: `/Users/studiox/orca/workspaces/AI-Lighting_Console/blocked16`, HEAD `15590e3`, 2026-08-18
범위: 델타 한정. 1회차 CLEAN 항목은 승계했고 재감사하지 않았다.

**M1 컨텍스트 격리 적용** — 작성자의 추론 맥락은 무시했다. 판정은 네 산출물 파일과
내가 직접 돌린 명령의 출력에만 근거한다.

---

## 1. 판정

| 항목 | 값 |
|---|---|
| **판정** | **FAIL** |
| **점수** | **0.65 / 1.00** (1회차 0.62 → 회귀 아님, STOP 신호 없음) |
| **run 진입** | **차단**. M0·M1은 P0-1r로 차단, M2는 AC-008 결함으로 차단 |
| 결함 | **P0 1건 · P1 6건 · P2 4건** |
| 3회차 | 가능(상한 미도달) |

### 왜 점수가 오르지 않았는가

교정의 **기계 층은 대부분 닫혔다.** 내가 직접 픽스처를 만들어 재현한 결과
AC-002·004·006·007·011과 AC-008의 자기인증 제거는 **전부 판별력을 보였다**(§2).
이것은 실적이며 그렇게 적는다.

점수가 오르지 않은 이유는 **내용 층**이다. 1회차 P0-1의 실패 경로 —
*"소유 SPEC의 계획서를 읽고 실측 기록을 열지 않았다"* — 가 한 번만 밟힌 것이
아니었다. 이번 회차에서 **같은 경로를 두 번 더 밟은 것을 재현했다.**

- **게이트 A**(P0-1이 다시 쓴 바로 그 게이트)의 주소 형식이 실측된 형식과 다르다. →§4
- **채널폭 승계**가 인용하는 근거 문단이, 같은 파일의 다음 줄에서 뒤집힌다. →§4

두 건 모두 인용은 **정확히 해소된다.** 그래서 게이트 D도 AC-007도 잡지 못한다.
이것이 §5의 게이트 D 판정으로 이어진다.

---

## 2. 교정별 판정표 — 내가 돌린 명령과 관측

모든 픽스처는 세션 스크래치패드에 만들었고 대상 4파일은 읽기만 했다.

| 1회차 결함 | 판정 | 내가 돌린 것 | 관측 |
|---|---|---|---|
| **P2-1** AC-004 파이프 밀림 | **닫힘** | 16행 정상 / D-2 셀에 `\|` 주입(NF=11) / D-3 근거칸 공백, 세 형태에 AC-004 본문 실행 | 정상 `PASS 공란 0` exit=0 · 밀림 `FAIL: D-2 필드 수 9 (기대 8)` exit=1 · 공란 `FAIL: D-3 필드7 공란` exit=1 |
| **P1-1** AC-006 게이트 누락 | **닫힘** | 3게이트×3역할=9행 / 게이트 A만 9행 / 긴 라벨(`A. 페이드 Part 경로 주소화`) / 행수 9 유지+역할만 파괴 | 정상 `PASS` · A만 `FAIL: B 3건 + C 3건 없음` · 긴 라벨 `PASS`(`substr(g,1,1)` 정상 흡수) · 역할 파괴 `FAIL: A: 음성대조 없음` |
| **P1-2** AC-007 행번호 미검증 | **닫힘** | 실좌표 3행 / `progress.md:99999` / `progress.md:0` / `server/nope/ghost.py:5` | 정상 **`PASS 인용 좌표 전량 해소 (cited=3)` exit=0** · 99999 `FAIL … 행 없음` · 0 `FAIL … 행 없음` · 없는 파일 `server/nope/ghost.py:5 파일 없음`. **fail-closed가 아니라 진짜 판별한다** — 정상 입력이 exit 0으로 통과함을 확인했다 |
| **P0-2** AC-008 자기인증 | **부분 — 표제 증상은 닫혔고 자기인증이 하위검사로 이동했다** | 무변경 HEAD에서 AC-008 전 단계 실행 | 앵커 추출 성공(61행) · `class="non-tool"` **0** → 첫 내용 검사에서 실패. **내용 부재로 떨어지며 앵커 부재가 아니다** ✓. 그러나 §3 N-4 참조 |
| **P2-2** AC-011 대상 부재 | **닫힘** | 부재 / 위반 있음 / 깨끗, 세 형태 | 부재 `FAIL 검사 대상 … 부재` · 위반 `FAIL 시간 예측 … 측정 후 (2~4주)` · 깨끗 `PASS 시간 예측 0` |
| **P2-6** AC-002 로케일 | **닫힘** | `LC_ALL` 미설정 / `C` / `C.UTF-8` / `ko_KR.UTF-8` 네 로케일 × 정상·`④` 두 입력 | 8회 전부 기대대로. 교대형 `/^(①\|②\|③)$/`가 `LC_ALL=C`에서도 판별한다 |
| **P1-4** M3 경계 검사 AC 부재 | **부분 — 절반만 닫혔다** | `grep -n "외부 URL" acceptance.md spec.md plan.md` | `acceptance.md` **0건**. 1회차 지적은 *"경계 검사(허용 경로)**와 외부 URL 0**"* 두 건이었고 AC-013은 앞의 한 건만 덮는다. §3 N-9 |
| **P2-8** `AC-019` 치환 손상 | **닫힘** | `grep -oE '(^\|[^-])AC-019'` 4파일 · LDGUIDE 원본 대조 | 잔존 bare `AC-019`는 `progress.md:250`(결함을 *설명하는* 문장, 정당) 1곳뿐. `spec/plan/acceptance` 0건. LDGUIDE 원본 `AC-LDG-019`=1 · bare `AC-019`=0. 이중 접두(`AC-LDG-LDG` 등) 0건 |
| **AC-007 1차형 판별력 0** (자진 신고 a) | **닫힘** | 위 P1-2 3방향 재현 | `awk NR==n` 단일 명령이 정상 입력을 exit 0으로 통과시킨다. 판별력 회복 확인 |
| **P0-1** 페이드 미측정 오배정 | **부분 — 처분은 옳아졌고 게이트 설계가 여전히 틀렸다** | §4 승계 재대조 | 처분(측정 완료·부분 GO)은 CUETIME 기록과 **일치**. 그러나 게이트 A의 주소 형식이 실측형과 다르다 → **P0-1r**(§3) |
| **P0-3** 채널폭 ③→② | **부분 — 처분값은 유지되나 배정 근거가 반증된다** | §4 승계 재대조 | ②는 옳다(I-14 잔존). 그러나 *"I-15가 다음 후보"*는 **거짓** → **N-1**(§3) |
| **P2-3/P2-4/P2-5/P2-7** 서식·대응표·수 불일치·frontmatter | **닫힘** | `plan.md` 정정 행 서식·D-1~D-16 대응표 육안 · frontmatter 12필드 계수 · AC-012 실행 | 서식·대응표 실재. frontmatter 12/12. AC-012 기계 검사 `PASS 선언=13 정의=13 분모=13`. **단 산문이 어긋난다** → N-3 |
| **P1-3** 멤버십 잔여 한계 | **닫힘** | `grep -n "응답기 1.7.0 확장은 증거상 사망했다"` GROUPGEN progress.md | `:402` 해소. `plan.md` M0-4에 인용 실재 |

**계**: 완전히 닫힘 9건 · 부분 4건 · 미개봉 0건.

---

## 3. 새 결함

### P0-1r — 게이트 A가 실측되지 않은 주소 형식을 쓰고, 양성 대조군이 발화할 수 없다

**심각도**: critical · **분류**: blocking
**위치**: `plan.md:77`(게이트 A 핸들 축) · `plan.md:100`(M0-3 양성 대조군) · `spec.md:188-190`(§A.4.2)

CUETIME progress.md **21행**이 명시한다:

```
$ sed -n '21p' .moai/specs/SPEC-COPILOT-CUETIME-001/progress.md
- 신규 실측 함정 2건 스킬 §3b 기록: 큐 이름 점(.) 제거, CueInFade
```

즉 기록 자신이 *"readback 경로는 스킬에 적었다"*고 가리킨다. 그 자리에 형식이 있다:

```
$ sed -n '166,170p' .claude/skills/ma3-spatial-pointing/SKILL.md
- **CueFade readback**: Cue 오브젝트의 `CueFade`/`Fade` prop은
  `property not readable`. 실제 값은 **큐 Part**에 `CueInFade`로 산다 —
  `prop:DataPool/Sequences/<n>/<cueName>/<partName>|CueInFade` (part
  이름은 큐 이름과 동일; 실측 5.0 readback).
$ sed -n '160,163p' .claude/skills/ma3-spatial-pointing/SKILL.md
  - **큐 이름의 점(.)은 MA3가 삼킨다**: `'Pos 2.28'`로 저장하면 실제 큐
    이름은 `Pos 228`이 된다. 이름으로 오브젝트를 다시 찾을 때(prop/state
    경로) 점 없는 이름을 써야 한다.
```

실측된 형식은 **이름 기반** `DataPool/Sequences/<n>/<cueName>/<partName>` 이고
part 이름은 큐 이름과 같으며 점은 제거된다. `plan.md:77`의 게이트 A는:

```
① DataPool/Sequences/<S>/Cue <C> 의 children   ② DataPool/Sequences/<S>/Cue <C>/Part <P>
③ CUETIME이 만든 Seq 101 Cue 1 (기지 GO 기준점)
```

①②는 **번호 기반** `Cue <C>` / `Part <P>`이며 이 형식은 어디에서도 실측되지 않았다.
`plan.md:91`은 한술 더 떠 *"`state`로 실재하는 시퀀스·큐·픽스처를 먼저 열거해 **실물
번호**를 얻고"*라 지시한다 — 실측 기록은 번호가 아니라 **이름**이 열쇠라고 적었다.

`grep -rn "cueName\|partName\|스킬 §3b\|ma3-spatial-pointing" .moai/specs/SPEC-COPILOT-BLOCKED16-001/` → **0건**.
SPEC은 이 형식을 한 번도 열지 않았다.

**왜 P0인가.** 이것은 분기를 틀리게 하는 결함이 아니라 **게이트를 발화 불능으로 만드는**
결함이다. ③은 *양성 대조군*이다(`plan.md:100` — `A: Seq 101 Cue 1의 Part CueInFade`).
번호형으로 주소화하면 기지 GO 기준점이 `ok:false`를 답하고, `plan.md:100`의 자기 규정이
발동한다 — *"**`ok:false` 일색을 판정으로 쓸 수 없다** — 프로브 장치 자체가 죽었을
가능성을 배제하지 못한다."* 게이트 A 배치 전체가 무효가 되고, 6-a는 프로브를 돌리고도
`미측정`으로 남는다. **틀린 판정보다 나쁘다 — 판정이 없는데 있었다고 믿게 된다.**

그리고 §A.4.2의 *"임의 큐에서 Part 경로가 **어떻게 주소화되는가**는 미측정"*은 과장이다.
형식은 기록돼 있다. 미측정인 것은 **그 형식이 SPEC이 만들지 않은 큐·다중 Part 큐로
일반화되는가**뿐이다. 잔여를 실제보다 넓게 적으면 게이트 목적이 흐려진다.

**교정형**
1. `plan.md:77` 게이트 A 축을 `① DataPool/Sequences/<n>` children(`state`)으로 실물
   **큐 이름** 획득 → `② <n>/<cueName>` children으로 part 이름 획득 →
   `③ <n>/<cueName>/<partName>` + `CueInFade`로 재정의.
2. `plan.md:100` 양성 대조군 A를 실측형 `DataPool/Sequences/101/Pos 228/Pos 228` +
   `CueInFade`(기대 `5.0`)로 고정. 점 제거 함정을 [HARD]로 병기.
3. `spec.md` §A.4.2의 잔여를 *"형식은 실측됨(스킬 §3b). 미측정은 타 SPEC이 만든 큐와
   다중 Part 큐로의 일반화"*로 좁히고, 근거를
   `.claude/skills/ma3-spatial-pointing/SKILL.md:167-169`로 귀속.

---

### N-1 (P1) — 채널폭 승계가 **완료된 작업을 미측정으로** 적는다

**심각도**: major · **분류**: blocking
**위치**: `spec.md:133`(I-15 행) · `spec.md:145`(*"I-15가 다음 후보"*) · `spec.md:104-107`(인용 발췌)

`spec.md:133`은 I-15를 *"**미측정이나 라이브 불필요.** 소유 SPEC이 '후속 SPEC이 가장 먼저
볼 후보'로 명시"*로 적고, `spec.md:145`가 *"미측정 경로 I-14 · I-15 잔존, **I-15가 다음
후보.**"*로 못 박는다. 소유 SPEC 기록은 정반대다:

```
$ sed -n '914p' .moai/specs/SPEC-COPILOT-PRECHK-001/progress.md
| **1** | ~~구간 겹침 재개 (후보 I-15)~~ — **출하 완료, `SPEC-COPILOT-OVERLAP-001`(2026-08-07 정정)** | …
$ grep -n '^status:' .moai/specs/SPEC-COPILOT-OVERLAP-001/spec.md
5:status: completed
$ grep -n 'I-15' .moai/specs/SPEC-COPILOT-OVERLAP-001/progress.md | head -1
151:본 SPEC의 출처는 **PRECHK의 독립 run-audit가 열거한 후보 I-15**…
```

I-15는 측정됐고 구현됐고 출하됐다(라이브 관측: 상계 31 · 열거 완전 `True` ·
`progress.md:357`). 코드에도 살아 있다:

```
$ grep -rn "bound_proves_clear" server/prechk/verdicts.py server/prechk/patch.py
verdicts.py:49:    {"exact_widths", "bound_proves_clear", "bound_inconclusive", "not_performed"}
patch.py:72:BOUND_PROVES_CLEAR = validate("overlap_basis", "bound_proves_clear")
```

**기전 — 인용이 뒤집히는 지점 직전에서 잘렸다.** `spec.md:104-107`은
`footprint.py` 3~6행을 발췌하고 6행 *"So the range-overlap axis shipped **disabled**."*
에서 멈춘다. 같은 독스트링 8행이 반전한다:

```
$ sed -n '8,14p' server/prechk/footprint.py
This module takes the weaker proposition that survives the refutation. Let ``W``
be the largest footprint among the modes that can be ENUMERATED. …
```

즉 6행은 **OVERLAP 이전의 역사 서술**이고 8행부터가 현재 동작이다. 4행 창이 정확히
그 경계에서 닫혔다.

**처분에 미치는 영향**: D-2의 처분값 **②는 유지된다**(I-14가 진짜로 미측정이므로).
무너지는 것은 **배정 근거**다. 이 문면이 `disposition.md`로 옮겨지면 다음 세션은
**이미 출하된 SPEC을 다시 열도록** 지시받는다.

**교정형**: `spec.md:133` I-15 행을 `출하 완료 — SPEC-COPILOT-OVERLAP-001(completed)`로,
`:145`를 *"미측정 경로는 I-14 1건. I-15는 OVERLAP-001로 출하 완료
(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:914`)"*로. `:104-107` 발췌를 8행까지
연장하거나, 6행이 역사 서술임을 병기.

---

### N-2 (P1) — REQ-B16-004가 승계 2건에 멈춰 있다

**심각도**: major · **분류**: blocking
**위치**: `spec.md:269`(E) · `spec.md:271`(S) · `plan.md:23` · `plan.md:207` · `acceptance.md:131`(제목)

```
$ grep -n "승계 2건\|승계 3건\|승계 인용 2건" spec.md plan.md acceptance.md
acceptance.md:131:### AC-007 (REQ-B16-004) — 승계 인용 2건이 실제로 해석된다
acceptance.md:142:… "FAIL 처분표 귀속 부족 cited=$cited (기대 >=3, 승계 3건)" …
spec.md:271:- **S**: 승계 2건 각각이 소유 SPEC 경로:행번호를 갖는다.
plan.md:23:2. **승계 2건을 재측정하지 않는 결정**(§spec A.1) …
plan.md:207:2. 승계 2건의 잔여 한계 문면 — 그룹 속성 73필드 미관측 · 상계의 비대칭 …
```

`spec.md` §A.1은 승계를 **3건**으로 다시 썼고 `plan.md` HISTORY는 *"승계 3건화"*를
적었으며 게이트 D는 *"승계 확인 3건"*이고 AC-007은 `cited >= 3`을 강제한다. 그런데
**REQ 본문은 2건에 남았다** — E는 *"그룹 멤버십·채널폭 처분을 정할 때"*로 페이드를
호명조차 하지 않는다.

**해로운 이유 두 가지.**
1. REQ의 S와 그 REQ의 AC가 **서로 다른 수를 요구한다.** S를 충족한 산출물이 AC-007에서
   떨어진다. REQ가 무엇을 요구하는지 두 문서가 불일치한다.
2. `plan.md:207` M1 필수 항목 2가 *"승계 **2건**의 잔여 한계 문면"*이므로, 처분표는
   페이드의 잔여 한계 — **바로 게이트 A가 존재하는 이유** — 를 싣지 않아도 된다.

**교정형**: `spec.md:269` E에 페이드 추가, `:271` S를 `승계 3건`으로.
`plan.md:23`·`:207`, `acceptance.md:131` 제목을 3건으로.

---

### N-3 (P1) — REQ-B16-008을 정의한 문서가 자기 수를 두 번째로 틀렸다

**심각도**: major · **분류**: blocking
**위치**: `acceptance.md:248` · `:343-345` · `:347` · §G.9 표

기계 검사는 통과한다:

```
$ A=.moai/specs/SPEC-COPILOT-BLOCKED16-001/acceptance.md
$ defined=$(grep -cE '^### AC-[0-9]{3}' "$A"); declared=$(grep -oE '<!-- AC-COUNT: [0-9]+ -->' "$A" | grep -oE '[0-9]+')
$ denom=$(grep -oE '커버리지 \*\*[0-9]+/[0-9]+\*\*' "$A" | grep -oE '/[0-9]+' | tr -d '/')
$ echo "$declared $defined $denom"
13 13 13        → PASS 선언=13 정의=13 분모=13
```

산문은 세 곳에서 어긋난다:

```
$ grep -n "기대: \`PASS 선언=\|이 분모 \`\|커버리지 \*\*\|미검증 3건" "$A"
248:기대: `PASS 선언=12 정의=12 분모=12`.
343:커버리지 **13/13**. …
344:4/19였던 선례가 있다. 미검증 3건은 산출물(`disposition.md` 정정 행 · 개정된 가이드)이
347:이 분모 `12`는 AC-012가 `AC-COUNT` 리터럴·실제 정의 수와 함께 기계 대조한다 …
$ grep -c "선언=12" "$A"
4
```

- `:248` 기대 문자열이 `12`. 실제는 `13`.
- `:347`이 *"이 분모 `12`"*라 단정. 실제는 `13`.
- `:343`의 `13/13`과 `:344`의 *"미검증 3건"*은 **같은 문단 안에서 서로를 부정한다.**
  13/13이면 미검증은 0이다. 둘 중 하나는 이 SPEC 자신의 뮤테이션 커버리지에 대한
  미관측 주장이다.
- §G.9 원장의 *"현 판본"* 행이 `PASS 선언=12 정의=12 분모=12`를 관측으로 적는다 —
  현 판본을 서술하지 않는다.

**이것이 REQ-B16-008이 금지한 바로 그 형태다.** REQ의 R은 *"총계를 두 곳 이상에 적지
않는다"*이고, `AC-COUNT`·커버리지 분모는 단일화했으나 **기대 문자열·산문·원장이 총계의
세 번째·네 번째·다섯 번째 출처로 남았다.** REQ 자신의 경위 문단이 *"승계한 규율이 남의
문서에는 걸리고 자기 문서에는 안 걸린 자리"*라 적었는데, 같은 자리에서 다시 걸렸다.
그리고 AC-012는 이 산문을 보지 않으므로 **검사가 있어도 잡히지 않는다.**

**교정형**: `:248`을 `기대: 세 값이 일치(현행 13)`처럼 **수를 쓰지 않는 문면**으로.
`:347`에서 `12`를 제거. `:344`의 *"미검증 3건"*을 커버리지 실태에 맞춰 정정하거나
`13/13`을 정정 — 둘 중 어느 쪽이 참인지 결정해야 한다. §G.9의 *"현 판본"* 행은
관측 시점(`v0.2.0`)을 명기.

---

### N-4 (P1) — AC-008: 자기인증이 하위검사로 이동했고, 승인되지 않은 33행 마크업 재작성을 요구한다

**심각도**: major · **분류**: blocking
**위치**: `acceptance.md` AC-008 블록 · `spec.md:273-280`(REQ-B16-005) · `plan.md:211-225`(M2)

**(a) 하위검사 2건이 무변경 HEAD에서 이미 통과한다.**

```
$ G=docs/user-guide.html; apx=$(awk '/id="appendix-tools"/{f=1} f' "$G")
$ printf '%s' "$apx" | grep -nE '조준|겨냥'
20:    <tr><td class="c">3</td><td><code>get_spatial_context</code></td><td>장비 3D 좌표 판독 (조준 계산의 기반)</td></tr>
$ printf '%s' "$apx" | grep -nE '대상|좌표'
20:    <tr>…get_spatial_context…</tr>
57:  대상 앱: grandMA3 onPC 코파일럿 &middot; 구성: 감독 워크플로우 9단계
```

`조준 >= 1`은 **기존 도구 표 행**이 충족하고, `대상|좌표 >= 1`은 같은 행과 **푸터**가
충족한다. REQ-B16-005 A가 가장 중히 여기는 *"발화 조건(대상 + 목표가 둘 다 필요)을
함께 싣는다"*의 대리 검사가 **문서 푸터로 통과한다.** M2가 발화 조건을 한 글자도 쓰지
않아도 두 하위검사는 통과한다. 지금 AC-008을 떨어뜨리는 것은 오직 새 리터럴 2종뿐이다.

푸터가 잡히는 이유는 `awk '/id="appendix-tools"/{f=1} f'`에 **종료 앵커가 없어** 부록
구간이 EOF까지 뻗기 때문이다.

**(b) `^<tr data-tool=` 이 33행 재작성을 요구한다.**

```
$ printf '%s' "$apx" | grep -c 'data-tool'
0
$ printf '%s' "$apx" | grep -cE '^ *<tr><td class="c">[^<]*</td><td><code>'
33
```

현행 행은 `    <tr><td class="c">1</td><td><code>…` 이다 — **4칸 들여쓰기** + `data-tool`
속성 없음. AC-008은 `^<tr data-tool=`을 **33개** 요구하므로 M2는 33행 전부에 속성을
붙이고 **동시에 들여쓰기를 0칸으로 옮겨야** 한다. 어느 REQ도 이를 승인하지 않았고
(REQ-B16-005 A는 *"별도 절 신설"*뿐, R은 *"행 수 33을 **유지**한다"*), `plan.md` M2의
작업 목록에도 없다. *"유지"*를 요구한 조항이 검사 방식 때문에 **재작성**으로 뒤집혔다.

들여쓰기를 유지한 채 속성만 붙이면 `^` 앵커가 0을 세고 AC-008이 실패한다 —
정규식 안에 숨은 서식 요구다.

**교정형**
1. 부록 추출에 종료 앵커를 준다: `awk '/id="appendix-tools"/{f=1} f&&/<footer/{f=0} f'`.
2. 행 수 검사를 **현행 리터럴**로: `grep -cE '^ *<tr><td class="c">[^<]*</td><td><code>'`
   (지금 33을 센다 — 마크업 변경 0).
3. 발화 조건 검사를 새 절 안으로 한정하고 판별력 있는 리터럴로 교체 —
   예: 비도구 절 구간에서 `대상`과 `좌표|중앙` **둘 다** ≥1, 또는 M2가 신설할
   전용 리터럴(`class="fire-condition"` 등)을 규정.

---

### N-5 (P1) — 게이트 C의 NEGATIVE가 ③으로 가는 것은 이 SPEC이 인용한 규칙과 모순이다

**심각도**: major · **분류**: blocking
**위치**: `plan.md:45`(게이트 C 분기 행)

`plan.md:45`: *"`posx` 양성 대조는 되는데 pan/tilt만 `ok:false` → **3-b ③**"*.

`spec.md:125`가 소유 SPEC에서 인용해 온 규칙은 이렇다:

```
$ sed -n '644,648p' .moai/specs/SPEC-COPILOT-PRECHK-001/progress.md | tail -2
… 응답기는 프로퍼티명을 열거할 수 없으므로(console/lua/copilot_responder.lua:204-217)
**어떤 프로퍼티 프로브 집합도 부재 증명이 될 수 없다.**
```

게이트 C의 NEGATIVE는 한 핸들 위에서 **이름 4개**(`pan·tilt·Pan·Tilt`)를 소진한
결과다. 그것으로 ③(영구 비범위 계약)을 굳히는 것은 인용해 온 규칙이 금지하는 형태이며,
`spec.md:140-142`가 채널폭에 대해 *"안 쏴 본 경로를 두고 '불가'를 영구 계약으로 굳히는
것은 REQ-B16-002를 이 SPEC이 스스로 위반하는 형태"*라며 ③→②로 고친 바로 그 추론이다.
**같은 SPEC이 §A.3.2에서 고친 것을 게이트 C에서 되풀이한다.**

lead가 우려한 비대칭이 여기 있다 — 틀린 ②는 다음 세션이 되짚지만, 틀린 ③은 *"읽을 수
없다"*로 굳고 아무도 반증하지 않는다.

**교정형**: 게이트 C NEGATIVE를 **②**로 하고 문면을 *"현행 읽기 표면 + 발화한 이름 4개에
한정해 미성립. 잔여: (i) 포지션 프리셋 저장값 표면 (ii) 응답기 확장"*으로 범위화.

---

### N-6 (P1) — 게이트 D는 "승계 확인"이 아니라 "인용 해소 확인"이다

**심각도**: major · **분류**: blocking
**위치**: `plan.md:46`(게이트 D 행) · `acceptance.md` AC-007

게이트 D의 GO 조건은 *"소유 SPEC 인용이 **경로:행번호로 해석됨**"*이고 AC-007도 행의
**존재**만 확인한다. 내용은 보지 않는다:

```
$ awk -v n=645 'NR==n{f=1} END{exit !f}' .moai/specs/SPEC-COPILOT-PRECHK-001/progress.md && echo "645 통과"
645 통과
$ sed -n '645p' .moai/specs/SPEC-COPILOT-PRECHK-001/progress.md
(빈 줄)
```

**빈 줄을 가리키는 인용도 게이트 D를 통과한다.**

그리고 N-1이 증명이다 — 채널폭 승계의 인용은 **전부 정확히 해소되는데**
(`footprint.py:3-6` 실재 · `PRECHK progress.md:644` 실재) 승계된 주장은 같은 파일
914행에서 반증된다. 게이트 D는 P0-1의 결함 계열을 **구조적으로 탐지할 수 없다.**
P0-1에 대응해 만든 게이트가 P0-1을 잡지 못한다.

덧붙여 가장 하중이 큰 승계(페이드)의 소유 SPEC은 **frontmatter가 없어 `status:`가
비어 있다**:

```
$ grep -c '^status:' .moai/specs/SPEC-COPILOT-CUETIME-001/spec.md
0
```

게이트 D는 *"이 승계가 나중에 뒤집혔는가"*를 물을 수단이 없다.

**교정형**: 게이트 D에 술어 두 개를 더한다.
(1) **내용 대조** — 인용 행이 주장의 핵심 토큰을 담는지(`awk NR==n` + `grep -q`).
(2) **후속 반전 탐색** — 소유 `progress.md` 전체에서
`grep -nE '출하 완료|SUPERSEDED|~~|철회'` + 소유 SPEC `status:` 확인.
(2)만 있었어도 N-1은 잡혔다.

---

### N-7 (P2) — AC-013이 미커밋·미추적 변경을 보지 못한다

**심각도**: minor · **분류**: optional
**위치**: `acceptance.md` AC-013

```
$ git status --porcelain
 M .moai/harness/usage-log.jsonl
 M .moai/lessons-inbox.jsonl
?? .moai/specs/.moai/
?? .moai/specs/SPEC-COPILOT-BLOCKED16-001/
$ find .moai/specs/.moai -type f
.moai/specs/.moai/state/config-cache.json
```

허용 2경로 밖 변경이 **지금 작업 트리에 3건** 있고, `git diff BASE...HEAD` 기반인
AC-013은 하나도 보지 못한다. `.moai/specs/.moai/state/config-cache.json`은 이 SPEC의
plan 세션이 만든 잘못된 상대 경로 산물로 보인다. 저장소 교훈
`gate-blind-to-untracked-files`가 이 함정을 이미 기록하고 있다.

부수 위험: `plan.md` §C.2는 `git add -A`를 금지하지 않는다. run이 `git add .moai/specs/`를
쓰면 `.moai/specs/.moai/`가 함께 쓸려 들어간다.

**교정형**: AC-013에 `git status --porcelain` 또는
`git ls-files --others --exclude-standard` 축을 더한다. `plan.md` §C.2에 명시 경로 스테이징
[HARD]를 추가.

### N-8 (P2) — AC-007의 `cited` 가드가 매치가 아니라 **행**을 센다

**심각도**: minor · **분류**: optional
한 행에 승계 인용 3건을 모두 적은 처분표는 `cited=1`로 실패한다(내가 첫 픽스처에서
실제로 밟았다). fail-closed 방향이라 위험하지 않으나, 서식 제약이 검사에 숨어 있다.
**교정형**: `grep -oE … | wc -l` 로 매치를 세거나, 세 패턴 각각의 존재를 개별 확인.

### N-9 (P2) — 1회차 P1-4의 "외부 URL 0" 절반이 미개봉

**심각도**: minor · **분류**: optional
`plan.md:233` M3-5는 *"외부 URL 0"*을 회귀 항목으로 두는데 `acceptance.md`에 `외부 URL`
0건이다. `spec.md:358`이 그 지적을 인용하면서도 AC-013은 허용 경로 절반만 덮었다.
M2가 `docs/user-guide.html`에 외부 참조를 넣어도 잡히지 않는다.
**교정형**: AC에 `grep -cE 'https?://' docs/user-guide.html` == 0 추가, 또는
LDGUIDE AC 소유임을 AC-011처럼 명시적으로 위임 선언.

### N-10 (P2) — 게이트 C가 도달 가능한 후보 표면 하나를 열거하지 않는다

**심각도**: minor · **분류**: optional
`DEFAULT_RIG_CONTEXT_PATHS`의 `preset_pools`("DataPool/PresetPools")는 **라이브 교정된**
읽기 표면이고 드릴다운으로 개별 프리셋 내용에 닿는다(`server/orchestrator/tools.py:268-273`).
CUETIME은 Preset 2.28을 저장했고 픽스처 시트가 `"2.28 Cro…"`로 표시함을 관측했다.
*"현재값"*과 *"저장값"*은 다른 질문이지만 3-b(포커스 차트)에는 저장값으로 충분할 수 있다.
게이트 C는 이 표면을 후보로도 적지 않는다.
**교정형**: 게이트 C 잔여에 프리셋 표면을 명기(핸들 축으로 승격할지는 run 판단).

---

## 4. 승계 3건 재대조 — 소유 SPEC의 `progress.md` 기준

**통과도 값으로 적는다.** 아래는 전부 내가 이번 회차에 직접 연 것이다.

| # | 승계 | 명령 | 관측 행 | 그 행이 세우는 것 | 배정된 처분을 지지하는가 |
|---|---|---|---|---|---|
| 1 | 그룹 멤버십<br>GROUPGEN-001 | `grep -n "게이트 A — 멤버십은 읽을 수 없다" …/GROUPGEN-001/progress.md` | **232** | 정답 기지 표본 Group 14에서도 후보 4종 `ok:false`, `childCount 0`. 추론 아닌 반증 | **지지 ✓** |
| 1a | 〃 잔여 한계 | `grep -n "정직한 천장" …` | **391** | 속성 101개 중 **73개 미관측**(`max_payload=1900`), 멤버 열거 필드 가능성 배제 못 함 | **지지 ✓** — `spec.md` §A.2가 이 문면을 정확히 옮겼다 |
| 1b | 〃 우회 경로 | `grep -n "응답기 1.7.0 확장은 증거상 사망했다" …` | **402** | 신규 동사가 직렬화할 대상이 없음. 단 소유 SPEC은 *"원리적으로 불가"*까지 적었고 BLOCKED16은 더 보수적으로 적었다(문제 아님) | **지지 ✓** |
| 2 | 채널폭<br>PRECHK-001 | `sed -n '644,653p' …/PRECHK-001/progress.md` | **644-653** | `ASSUMPTION-27` 범위 철회 + 미측정 후보 I-14·I-15 | **부분** — 철회 문면과 I-14는 지지. **I-15는 반증됨** |
| 2a | 〃 반증 지점 | `sed -n '914p' …/PRECHK-001/progress.md` | **914** | `~~구간 겹침 재개 (후보 I-15)~~ — **출하 완료, SPEC-COPILOT-OVERLAP-001**` | **불일치 ✗** → N-1 |
| 2b | 〃 교차 확인 | `grep -n '^status:' …/OVERLAP-001/spec.md` · `grep -rn "bound_proves_clear" server/prechk/` | `spec.md:5 completed` · `verdicts.py:49` `patch.py:72` | 상계 축이 실측·구현·출하됨 | **불일치 ✗** |
| 2c | 〃 인용 발췌 | `sed -n '1,14p' server/prechk/footprint.py` | **3-6 vs 8-14** | 6행 *"shipped disabled"*는 역사, 8행부터가 현재 동작. 발췌가 6행에서 끊겼다 | **불일치 ✗** |
| 3 | 페이드<br>CUETIME-001 | `grep -n "CueInFade" …/CUETIME-001/progress.md` | **16, 21** | 16행: Part `CueInFade` = **5.0**, Cue의 `CueFade`는 not readable | **지지 ✓** — 처분(측정 완료·부분 GO)은 옳다 |
| 3a | 〃 한계 | `sed -n '3,20p' …` | **3, 12-13** | M1 완료 2026-08-14. 산출물은 **Sequence 101 Cue 1 'Pos 228'** — 자기가 만든 큐 1건 | **지지 ✓** — *"한 건뿐"* 주장 정확 |
| 3b | 〃 **기록이 가리킨 곳** | `sed -n '21p' …` → `sed -n '166,170p' .claude/skills/ma3-spatial-pointing/SKILL.md` | **21 → SKILL.md:167-169** | 21행이 *"readback 경로는 스킬 §3b"*를 가리키고, 그 자리에 실측 형식 `DataPool/Sequences/<n>/<cueName>/<partName>` 이 있다 | **불일치 ✗** — 게이트 설계가 이 형식을 안 쓴다 → **P0-1r** |

**결론.** 세 건 중 **1건(그룹 멤버십)만 온전히 지지**된다. 채널폭은 처분값(②)은
살아남되 배정 근거가 반증되고, 페이드는 처분값은 옳되 그 처분이 남긴 게이트가 실측
형식을 쓰지 않는다.

**lead의 조건 2가 옳았다.** P0-1의 실패 경로는 한 번이 아니라 **세 번** 밟혔다 —
계획서만 읽기(1회차) → 기록의 뒷부분을 안 읽기(N-1) → **기록이 가리킨 곳을 안 열기**(P0-1r).
세 번째가 가장 교묘하다. 기록을 열었고, 인용도 정확하고, 게이트 D도 통과한다.

---

## 5. 게이트 C · 게이트 D 판정

### 게이트 C — 단일 축 자체는 **증거상 방어된다.** 결함은 다른 데 있다

lead의 자진 신고는 *"단일 핸들 축이 P0-1의 거울상 아닌가"*였다. **아니다.** 근거:

1. **피벗할 하위 층이 없다.** 페이드는 Cue → **Part**로 핸들을 바꿀 수 있었다.
   픽스처 노드는 자식이 없다:
   ```
   $ sed -n '296p' .moai/specs/SPEC-COPILOT-PRECHK-001/progress.md   # 발췌
   … 픽스처 노드 childCount는 0이다 …
   ```
   Cue↔Part와 **같은 형상이 아니다.**
2. **핸들은 살아 있다.** 같은 슬롯에서 `posx/posy/posz`가 읽힌다
   (`server/orchestrator/tools.py:1319` + `:5562` `read_properties`) — 양성 대조군 설계는 옳다.
3. **Pan/Tilt는 저장소 전역에서 커맨드 표면뿐이다.**
   `grep -rn "'Pan'\|\"Pan\"" server/ console/` → `server/spatial/pointing.py`(`Attribute 'Pan' At <n>`,
   물리 도) · `server/fx/schema.py:55 MOVEMENT_ATTRIBUTES` · `server/fx/instantiate.py`.
   **읽기 경로 0건.** 라이브 현재값은 프로그래머/출력 층에 있고 오브젝트 트리가 싣지 않는다.

→ 두 번째 핸들이 실재한다는 증거가 없으므로 **"단일 축"은 여기서 결함이 아니다.**
그렇게 적는 것이 정직한 문장이다.

**그러나 게이트 C에는 두 결함이 있다**: NEGATIVE→③이 SPEC 자신이 인용한 규칙과
모순되고(**N-5, P1**), 도달 가능한 프리셋 표면을 후보로도 적지 않는다(**N-10, P2**).

### 게이트 D — **결함 있음.** 이름과 동작이 다르다

**N-6** 전문 참조. 요약: 게이트 D는 인용이 *해소되는가*만 묻고 인용된 기록이
*주장을 지지하는가*는 묻지 않는다. 빈 줄을 가리키는 인용도 통과하고(재현함),
N-1이 실증한다 — 인용 3건 전부 정확히 해소되는데 승계 주장은 반증된다.
**P0-1에 대응해 만든 게이트가 P0-1의 결함 계열을 구조적으로 못 잡는다.**

---

## 6. 확인했고 깨끗한 것

명령을 직접 돌려 재현한 것만 적는다.

- **AC-004 `NF != 10` 가드** — 밀린 행 검출, 정상 행 통과, 공란 검출 3방향 판별.
- **AC-006 하드코딩 게이트 집합** — B/C 누락 6건 검출, 긴 라벨(`A. 페이드 Part 경로
  주소화`) 정상 통과, 행수 9 유지 + 역할 파괴 검출. `substr(g,1,1)` 정규화 정상 작동.
- **AC-007 좌표 해소** — **정상 입력 exit 0**(판별력 있음), 날조 행번호·행 0·없는 파일
  전부 검출. 1차형의 판별력 0 문제는 해소됐다.
- **AC-011 존재 단언** — 부재/위반/깨끗 3방향 판별.
- **AC-002 로케일 교대형** — 4개 로케일 × 2입력 = 8회 전부 기대대로.
- **AC-008 자기인증 표제 증상** — 무변경 HEAD에서 실패하며, **내용 부재**로 떨어진다
  (앵커는 61행 정상 추출). 우연한 실패가 아니다.
- **AC-009** — 현행 트리 `tn=33`, `PASS 유령 0` 실행 확인.
- **AC-012 기계 검사** — `PASS 선언=13 정의=13 분모=13`(검사 자체는 정상. 산문이 문제).
- **AC-013 두 가드** — 현 트리에서 `FAIL 변경 0건`(의도한 fail-closed), 범위 필터가
  `server/web/session.py`만 뽑아내는 것 확인.
- **`AC-019` 치환 손상** — 4파일 단어 경계 대조. 잔존 1건은 결함을 설명하는 문장으로 정당.
  이중 접두 손상 0건.
- **인용 좌표 전량** — `CUETIME progress.md:3/16/17` · `songcue_report.py:15` ·
  `groupgen/write.py:410` · `footprint.py:3-6/130/217` · `PRECHK progress.md:644` ·
  `cue_monitor.py:49/62` · `prechk/query.py:38` · `session.py:107` · `session.py:3546-3555`
  — **전부 정확**. 1회차 P1-2가 고친 두 좌표도 유효.
- **REQ-B16-005 발화 조건 주장** — `session.py:218-225` `_POINT_AT_TARGET` /
  `_POINT_TARGET_TRIPLE` / `_POINT_TARGET_CENTRE` 확인. 정규식 통과 후 좌표 3쌍도
  중앙어도 없으면 `return None`. **주장 정확.**
- **§A.7 정정-1·정정-2** — `walk_mode_widths`(`footprint.py:217`) 실재로 모드별 폭 열거
  성립. 정정-2는 §4 승계 3으로 확정.
- **§D 번호 규약** — Q1~Q4 전부 `progress.md`에 실재, §H.1(`:171`)이 Q3 해명.
- **REQ 번호** — REQ-B16-001~009 순차, 결번·중복 0.
- **frontmatter** — 12필드 전량.
- **D7 교차 SPEC** — 참조 8건 중 retired/superseded/archived **0건**(BLOCKING 없음).
  다만 CUETIME-001은 frontmatter 자체가 없어 `status:` 판독 불가 → N-6 근거.
- **D8** — `syscall` 0건. 자동 PASS.
- **MP-7** — `[NEEDS CLARIFICATION` 0건.
- **Out of Scope** — `spec.md:361` §C 비목표, 구체 항목 5건.

---

## 7. 확인하지 못한 것

1. **라이브 프로브 전량.** 지시대로 콘솔 미접촉, `responder_roundtrip.py` 미실행.
   게이트 A·B·C의 실제 판정은 M0의 몫이다. **P0-1r은 라이브 없이 판정했다** —
   근거가 라이브 관측이 아니라 *"SPEC이 쓴 형식 ≠ 저장소에 실측 기록된 형식"*이라는
   문서 대조이기 때문이다.
2. **`Cue <C>` / `Part <P>` 번호형이 실제로 실패하는가.** 실패를 관측하지 않았다.
   내가 세운 것은 *"이름형만 실측됐고 번호형은 어디에도 실측 기록이 없다"*이며,
   양성 대조군을 미실측 형식으로 잡는 것은 그 자체로 결함이다. 번호형도 통하면
   P0-1r의 피해는 줄지만 **결함은 남는다** — 기지 GO 기준점은 기지형으로 쏘아야 한다.
3. **`미검증 3건`(N-3)이 어느 3건인가.** §D 표는 13건 전부 `O`이므로 문장이
   어느 판본의 잔재인지 특정하지 못했다. 둘 중 무엇이 참인지는 작성자만 안다.
4. **`.moai/specs/.moai/state/config-cache.json`의 생성 주체.** 이 SPEC의 plan 세션으로
   추정하나 확증하지 못했다 — **SUSPECTED**. 시도한 것: `git log`(미추적이라 이력 없음),
   파일 내용 확인. 어느 쪽이든 허용 경로 밖이고 AC-013이 못 본다는 사실은 불변.
5. **GEARS 형식 적합성(MP-2).** 이 저장소는 G/E/A/R/S 분해형을 전 SPEC에 일관 적용하며
   1회차가 이를 결함으로 올리지 않았다. 델타 범위 밖으로 두고 **1회차 판정을 승계**했다.
   재감사하지 않았다.
6. **프리셋 표면(N-10)이 실제로 pan/tilt 값을 답하는가.** 경로가 라이브 교정됐다는
   사실만 확인했고 내용 판독은 라이브가 필요하다. 그래서 P2로 두고 *"후보로 적어라"*까지만 요구한다.

---

## 8. 필수 통과 기준 (M5)

| # | 기준 | 판정 | 근거 |
|---|---|---|---|
| MP-1 | REQ 번호 일관 | **PASS** | `grep -oE '^### REQ-B16-[0-9]{3}'` → 001~009 순차, 결번·중복 0 |
| MP-2 | GEARS 형식 | **승계(1회차)** | 델타 범위 밖. §7-5 |
| MP-3 | frontmatter | **PASS** | 12필드 전량 |
| MP-4 | 언어 중립성 | **N/A** | 단일 프로젝트 범위 SPEC, 다언어 도구 미포함 |
| MP-5 | D7 BLOCKING | **PASS** | 참조 8건, retired/superseded/archived 0 |
| MP-6 | D8 BLOCKING | **PASS** | `syscall` 0건 |
| MP-7 | 미해소 clarification | **PASS** | `[NEEDS CLARIFICATION` 0건 |

**필수 기준 실패는 없다.** FAIL 판정은 루브릭 점수와 blocking 결함 7건에서 나온다.

## 9. 루브릭 점수

| 차원 | 점수 | 대역 | 근거 |
|---|---|---|---|
| Clarity | 0.75 | 0.75 | 대체로 명확. REQ-B16-004(2 vs 3) · AC-007 제목 · AC-012 기대 문자열에서 해석 갈림 |
| Completeness | 0.75 | 0.75 | 절 전량 존재, Out of Scope 구체. 외부 URL 축(N-9) 미대응 |
| Testability | 0.60 | 0.50~0.75 | 기계 층은 실측으로 강해졌으나 AC-008 하위검사 2건 무력 · AC-013 미추적 사각 · AC-007 내용 무관심 · AC-012가 통과하면서 산문이 틀림 |
| Traceability | 0.50 | 0.50 | 인용은 전부 해소되나 승계 3건 중 2건이 반증되거나 절반만 전파됨. 게이트 D가 이를 구조적으로 못 잡음 |

**총점 (0.75+0.75+0.60+0.50)/4 = 0.65**

회귀 없음(0.62 → 0.65). STOP 신호 없음. 3회차 가용.

---

## 10. 권고 — manager-spec 조치 순서

blocking 7건. 되돌리기 어려운 순서로 적는다.

1. **P0-1r** — `plan.md:77` 게이트 A 축을 이름 기반 실측형으로 재정의하고,
   `plan.md:100` 양성 대조군 A를 `DataPool/Sequences/101/Pos 228/Pos 228` +
   `CueInFade`(기대 `5.0`)로 고정. `spec.md` §A.4.2의 잔여를
   *"형식은 실측됨(`.claude/skills/ma3-spatial-pointing/SKILL.md:167-169`),
   미측정은 타 SPEC 생성 큐·다중 Part 큐로의 일반화"*로 좁힌다.
   **이것을 고치지 않으면 M0 게이트 A는 돌려도 판정을 내지 못한다.**
2. **N-6** — 게이트 D에 내용 대조 + 후속 반전 탐색 두 술어를 더한다.
   `grep -nE '출하 완료|SUPERSEDED|~~|철회'` + 소유 SPEC `status:`.
   **1을 고치기 전에 이것부터 넣으면 3·4를 자동으로 잡는다.**
3. **N-1** — `spec.md:133` I-15 행을 `출하 완료 — OVERLAP-001(completed)`로,
   `:145`를 *"미측정 경로는 I-14 1건"*으로. `:104-107` 발췌를 8행까지 연장.
4. **N-2** — REQ-B16-004 E·S를 승계 3건으로. `plan.md:23`·`:207`,
   `acceptance.md:131` 제목 동반 정정.
5. **N-5** — 게이트 C NEGATIVE를 ②로 하고 범위화 문면 적용.
6. **N-4** — 부록 추출에 종료 앵커, 행 수 검사를 현행 리터럴로, 발화 조건 검사를
   판별력 있는 리터럴로. **마크업 33행 재작성 요구를 제거한다.**
7. **N-3** — `acceptance.md:248`·`:347`에서 수를 제거, `:343-345`의
   `13/13` ↔ `미검증 3건` 모순 해소, §G.9 *"현 판본"* 행에 관측 시점 명기.

P2 4건(N-7~N-10)은 lead 재량. **N-9는 값이 싸다** — grep 한 줄이다.

### 3회차 범위 제안

위 7건의 델타에 한정하고, 특히 **게이트 D 교정(2번)이 들어간 뒤 승계 3건을 그 새 게이트로
다시 통과시켜 보는 것**을 3회차의 핵심 항목으로 둘 것을 권한다. 새 게이트가 N-1을 잡지
못하면 교정이 헛돈 것이다.

### 마지막으로 — 이 SPEC이 잘하고 있는 것

교정 15건 중 9건을 **완전히** 닫았고, 그 기계 층은 내가 직접 픽스처를 만들어 재현했다.
§G 뮤테이션 원장은 자기 검사가 헛도는 경우(§G.4 1차 · §G.6 1차 · §G.11 1차형)를 숨기지
않고 적었으며, 이번 회차에서 그 세 기록이 전부 사실임을 확인했다. **자기 실패를 원장에
적는 규율은 이 저장소에서 드물게 잘 지켜지고 있다.** 남은 결함이 전부 *내용* 층 —
남의 기록을 어디까지 읽는가 — 에 몰려 있는 것도 그 규율의 결과다. 기계는 이미 정직하다.
