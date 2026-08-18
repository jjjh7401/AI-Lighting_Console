# SPEC-COPILOT-BLOCKED16-001 — 수용 기준 (acceptance)

## HISTORY

| 버전 | 일자 | 변경 |
|---|---|---|
| 0.1.0 | 2026-08-18 | 최초 작성. REQ 1:1 대응. §G에 뮤테이션 검증 원자료. |
| 0.2.0 | 2026-08-18 | lead 지적(선언 수 불일치) 반영. **AC-012 신설**(REQ-B16-008 — 선언 수 무결성). AC 총계를 아래 리터럴 1곳으로 단일화하고 HISTORY에서 총계 표기를 제거. |
| 0.7.0 | 2026-08-18 | **규약 7 신설** — BSD awk 다바이트 등호 버그 자체 발견. 전 awk 호출에 `LC_ALL=C` 강제. |
| 0.6.0 | 2026-08-18 | plan-audit 3회차(FAIL 0.67, 상한) 반영. **G-1~G-5를 산문에서 검사로 이전** — AC-001 집합 대조(R3-7) · AC-004 `미정` 리터럴(R3-6) · AC-006 양성 대조군 정체+점 제거(R3-8) · AC-007 술어②·3패턴 개별(R3-3/R3-4) · AC-011 가이드 포함(R3-5) · AC-013 추적본 제외. |
| 0.5.0 | 2026-08-18 | lead 신규 P0(AC-013 stray 축이 gitignore 아래에서 상시 통과) 반영. stray 축을 `find` 기반 **중첩 `.moai`** 검사로 교체 + 생산자 통제 실험 기록. |
| 0.4.0 | 2026-08-18 | plan-audit 2회차(FAIL 0.65) 반영. **N-4** AC-008 하위검사 자기인증 제거(종료 앵커·전용 리터럴 2종·현행 마크업 계수) · **N-3** 산문 총계 제거 · **N-8** `cited` 매치 계수 · **N-7/N-9** AC-013에 미추적·외부 URL 축 추가 · AC-007 제목 3건. |
| 0.3.0 | 2026-08-18 | plan-audit 1회차(FAIL 0.62) 반영. **AC-008 재작성**(자기인증 제거 — 대상을 참조 부록으로) · **AC-013 신설**(REQ-B16-009 변경 파일 범위) · AC-004 `NF` 가드 · AC-006 게이트 하드코딩 · AC-007 좌표 해소 · AC-011 존재 단언 · AC-002 로케일. §G.10~13 신설, §G.9에 M4(관측자 lead) 추가. |

<!-- AC-COUNT: 13 -->

**[HARD] AC 총계의 유일 출처는 바로 위 `AC-COUNT` 리터럴이다.** HISTORY 행은 총계가 아니라
**증분**(어느 AC가 늘었는가)만 적는다. 초판은 HISTORY에 `AC-001~010`이라는 총계를 적었고
실제는 11건이어서 어긋났다 — 총계를 두 곳에 적으면 반드시 어긋난다. 검사를 하나 더 다는 것이
아니라 **중복 출처를 없애는 것**이 교정이다(REQ-B16-008 R).

## §0. 표기 규약 [HARD] — LDGUIDE-001 승계

**규약 1 — grep 명령은 반드시 코드블록에 둔다.** 표 셀에 넣으면 파이프를 `\|`로
이스케이프하게 되고, `grep -E`는 `\|`를 선택이 아니라 문자 그대로의 파이프로 읽어 어떤
입력에도 0을 반환한다(LDGUIDE 1회차 D1).

**규약 2 — 모든 명령에 기대값을 붙인다.**

**규약 3 — 빈 입력 가드를 넣는다.** 대상 행이 0개일 때 "위반 0"이 나오는 형태는
fail-open이다. 모든 집합 검사는 **모집단 크기를 먼저 확인**한 뒤 위반을 센다.

**규약 4 — 부인목록 금지, 전량 대조(set difference)를 쓴다.**

**규약 5 — 명령은 작성 시점에 뮤테이션으로 검증한다.** 실패해야 하는 입력을 만들어
실제로 실패하는지 확인한 뒤에만 AC에 싣는다. 기록은 §G.

**규약 6 — 식별자 대조는 단어 경계 또는 집합 연산으로 한다.**

**규약 7 — `awk`는 반드시 `LC_ALL=C`로 호출한다 [HARD].** 이 플랫폼의 BSD awk
(`awk version 20200816`)는 기본 로케일에서 **다바이트 문자열 등호 비교가 전부 참**이다:

```bash
printf '③\n' | awk '{print ($0=="미정")}'            # → 1   (거짓이어야 한다)
printf '③\n' | LC_ALL=C awk '{print ($0=="미정")}'   # → 0   (정상)
```

정규식 매치(`~`)는 두 로케일 모두 정상이나, 등호(`==`)와 배열 키를 쓰는 순간 무너진다.
`LC_ALL=C`는 등호를 바이트 정확 비교로 되돌리고 정규식도 그대로 동작한다(4로케일 × 2입력
실측, §G.8 승계). **한 곳이라도 빠지면 그 검사는 모든 한글 값을 같다고 답한다** —
반응은 하는데 판별력이 0인 형태이며, `AC-007` 1차형과 같은 계열이다.

공통 변수:

```bash
D=.moai/specs/SPEC-COPILOT-BLOCKED16-001/disposition.md
P=.moai/specs/SPEC-COPILOT-BLOCKED16-001/probe.md
T=server/orchestrator/tools.py
G=docs/user-guide.html
```

## §A. 수용 기준

### AC-001 (REQ-B16-001) — 처분표 16행 전량

```bash
rows=$(grep -cE '^\| D-[0-9]+ \|' "$D")
[ "$rows" -eq 16 ] || { echo "FAIL rows=$rows (기대 16)"; exit 1; }
# 행 수만 세면 D-1이 15행 + D-2 1행인 표가 통과한다(감사 3회차 R3-7). 집합으로 본다.
ids=$(grep -oE '^\| D-[0-9]+ ' "$D" | grep -oE '[0-9]+' | sort -n)
[ "$(printf '%s\n' "$ids" | sort -nu | tr '\n' ' ')" = "$(seq 1 16 | tr '\n' ' ')" ] \
  || { echo "FAIL D-n 집합이 1..16과 다르다"; exit 1; }
[ "$(printf '%s\n' "$ids" | wc -l)" -eq "$(printf '%s\n' "$ids" | sort -u | wc -l)" ] \
  || { echo "FAIL D-n 중복"; exit 1; }
echo "PASS rows=$rows · id 집합 1..16 · 중복 0"
```

기대: `PASS rows=16 · id 집합 1..16 · 중복 0`. **행 수 · 집합 · 중복은 서로 다른 것을 막는다**
— 셋 중 하나만 두면 나머지 둘이 통과한다(규약 4).

### AC-002 (REQ-B16-001) — 처분 열 값 집합 ⊆ {①,②,③}, 공란 0

처분은 5번째 파이프 필드다(`| D-n | 단계 | 항목 | 처분 | …`).

```bash
rows=$(grep -cE '^\| D-[0-9]+ \|' "$D")
[ "$rows" -eq 16 ] || { echo "FAIL 모집단 $rows != 16 — 집합 검사를 신뢰할 수 없다"; exit 1; }
bad=$(grep -E '^\| D-[0-9]+ \|' "$D" \
  | LC_ALL=C awk -F'|' '{v=$5; gsub(/[[:space:]]/,"",v); if (v !~ /^(①|②|③)$/) print $2" -> ["v"]"}')
[ -z "$bad" ] && echo "PASS 처분 열 전량 적법" || { echo "FAIL:"; echo "$bad"; exit 1; }
```

기대: `PASS 처분 열 전량 적법`. 모집단 가드가 먼저 걸리므로 표가 비면 통과가 아니라 실패다.

### AC-003 (REQ-B16-001) — 측정 종류 열 값 집합 ⊆ {읽기, 쓰기, 무관}

측정 종류는 6번째 파이프 필드다.

```bash
rows=$(grep -cE '^\| D-[0-9]+ \|' "$D")
[ "$rows" -eq 16 ] || { echo "FAIL 모집단 $rows != 16"; exit 1; }
bad=$(grep -E '^\| D-[0-9]+ \|' "$D" \
  | LC_ALL=C awk -F'|' '{v=$6; gsub(/[[:space:]]/,"",v); if (v !~ /^(읽기|쓰기|무관)$/) print $2" -> ["v"]"}')
[ -z "$bad" ] && echo "PASS 측정 종류 전량 적법" || { echo "FAIL:"; echo "$bad"; exit 1; }
```

### AC-004 (REQ-B16-001) — 7필드 공란 0

```bash
rows=$(grep -cE '^\| D-[0-9]+ \|' "$D")
[ "$rows" -eq 16 ] || { echo "FAIL 모집단 $rows != 16"; exit 1; }
blank=$(grep -E '^\| D-[0-9]+ \|' "$D" \
  | LC_ALL=C awk -F'|' 'NF != 10 {print $2" 필드 수 "NF-2" (기대 8) — 셀 안 파이프로 열이 밀렸다"; next}
              {for(i=2;i<=9;i++){v=$i; gsub(/[[:space:]]/,"",v); if(v=="" || v=="미정" || v=="TBD" || v=="?"){print $2" 필드"i" 미정/공란: ["v"]"}}}')
[ -z "$blank" ] && echo "PASS 공란 0" || { echo "FAIL:"; echo "$blank"; exit 1; }
```

`—`(em dash)는 "해당 없음"의 **정해진** 값이므로 적법이다. `미정`·`TBD`·`?`는 **정하지 않은**
값이므로 실패다 — REQ-B16-001 R이 "미정은 값이 아니다"라고 이름으로 금지한 것이다.

빈 문자열만 보던 v0.5.0은 배정 근거와 근거 귀속이 전 행 `미정`인 16행 표를 통과시켰다
(감사 3회차 R3-6이 픽스처로 실증). **M0가 미측정으로 끝나면 그 두 칸을 `미정`으로 메우고
싶은 압력이 정확히 거기서 생긴다** — REQ가 내다보고 금지한 자리를 AC가 안 보고 있었다.

### AC-005 (REQ-B16-002) — 프로브 판정 열 값 집합 ⊆ {GO, NEGATIVE, 미측정}

```bash
prows=$(grep -cE '^\| P-[0-9]+ \|' "$P")
[ "$prows" -ge 9 ] || { echo "FAIL 프로브 행 $prows < 9 (게이트 3종 × 최소 3역할)"; exit 1; }
bad=$(grep -E '^\| P-[0-9]+ \|' "$P" \
  | LC_ALL=C awk -F'|' '{v=$9; gsub(/[[:space:]]/,"",v); if (v !~ /^(GO|NEGATIVE|미측정)$/) print $2" -> ["v"]"}')
[ -z "$bad" ] && echo "PASS 판정 열 전량 적법" || { echo "FAIL:"; echo "$bad"; exit 1; }
```

**`판독 불가`는 적법값이 아니다** — 이 AC의 존재 이유가 그것이다(REQ-B16-002 R).

### AC-006 (REQ-B16-003) — 대조군 2종 쌍 누락 0

각 게이트(6번째 필드가 아니라 3번째 필드 `게이트`)마다 세 역할이 모두 있어야 한다.

```bash
prows=$(grep -cE '^\| P-[0-9]+ \|' "$P")
[ "$prows" -ge 9 ] || { echo "FAIL 프로브 행 $prows < 9"; exit 1; }
missing=$(grep -E '^\| P-[0-9]+ \|' "$P" | LC_ALL=C awk -F'|' '
  {g=$3; r=$6; gsub(/[[:space:]]/,"",g); gsub(/[[:space:]]/,"",r); seen[substr(g,1,1)" "r]=1}
  END{split("A B C", wg, " "); split("본프로브 음성대조 양성대조", want, " ");
      for(i in wg) for(k in want) if(!((wg[i]" "want[k]) in seen)) print wg[i]": "want[k]" 없음"}')
[ -z "$missing" ] && echo "PASS 대조군 쌍 전량 존재" || { echo "FAIL:"; echo "$missing"; exit 1; }

# 역할이 있는 것과 그 역할이 제대로 된 것은 다르다 — 게이트 A 양성 대조는 기지 GO 기준점이어야 한다
pa=$(grep -E '^\| P-[0-9]+ \|' "$P" | LC_ALL=C awk -F'|' '{g=$3;r=$6;gsub(/[[:space:]]/,"",g);gsub(/[[:space:]]/,"",r);
     if(substr(g,1,1)=="A" && r=="양성대조") print $4" "$5}')
printf '%s' "$pa" | grep -q 'Pos 228' \
  || { echo "FAIL 게이트A 양성대조가 기지 기준점(Pos 228)이 아니다"; exit 1; }
printf '%s' "$pa" | grep -q 'Pos 2\.28' \
  && { echo "FAIL 점 포함 이름 — MA3가 삼킨다(SKILL.md:163-165)"; exit 1; }
echo "PASS 게이트A 양성대조 = 기지 기준점, 점 제거됨"
```

`역할` 열 리터럴은 공백 제거 후 `본프로브` · `음성대조` · `양성대조`로 정규화된다
(원문 표기는 `본 프로브` · `음성 대조` · `양성 대조`). 게이트는 **첫 글자**로 정규화해
라벨 흔들림(`A` vs `A. 페이드`)을 흡수한다.

**게이트 집합을 하드코딩하는 이유 [HARD]** — 초판은 `gates[g]=1`로 **데이터에서 유도**했고,
그러면 **관측되지 않은 게이트는 요구되지 않는다.** 감사 P1-1이 게이트 A만 9행이고 B·C는
아예 없는 원장을 만들어 통과시켰다 — 게이트 두 개를 한 번도 쏘지 않은 원장이 PASS였다.
역할 축은 `split()`로 하드코딩해 놓고 게이트 축만 유도한 것이 규약 4(부인목록 금지,
전량 대조) 위반이다. 두 축 모두 하드코딩한다.

### AC-007 (REQ-B16-004) — 승계 인용 3건이 해석되고, 좌표가 실재한다

인용을 요약으로 대체하면 귀속이 아니다(REQ-B16-004 R). 인용된 경로:행번호가 지금도
그 내용을 담고 있는지 직접 확인한다.

```bash
a=$(grep -c "게이트 A — 멤버십은 읽을 수 없다" .moai/specs/SPEC-COPILOT-GROUPGEN-001/progress.md)
b=$(grep -c "ASSUMPTION-27" server/prechk/footprint.py)
[ "$a" -ge 1 ] && [ "$b" -ge 1 ] && echo "PASS 승계 앵커 해석됨 (a=$a b=$b)" \
  || { echo "FAIL 승계 앵커 소실 a=$a b=$b"; exit 1; }
# 승계 3건 각각을 개별로 요구한다 — 합계 3은 한 소스를 3번 적어도 충족된다(감사 3회차 R3-4)
for pat in 'GROUPGEN-001/progress\.md:[0-9]+' 'footprint\.py:[0-9]+' 'CUETIME-001/progress\.md:[0-9]+'; do
  c=$(grep -coE "$pat" "$D")
  [ "$c" -ge 1 ] || { echo "FAIL 승계 귀속 누락: $pat"; exit 1; }
done

# 술어 ② — 좌표의 내용이 주장을 담는가. 좌표 해소만으로는 빈 줄 인용도 통과한다(감사 3회차 R3-3)
check_token(){ f=$1; n=$2; tok=$3
  sed -n "${n}p" "$f" | grep -q "$tok" \
    || { echo "FAIL 술어② 실패: $f:$n 이 '$tok' 을 담지 않는다"; return 1; }; }
check_token .moai/specs/SPEC-COPILOT-GROUPGEN-001/progress.md 232 '멤버십은 읽을 수 없다' || exit 1
check_token .moai/specs/SPEC-COPILOT-CUETIME-001/progress.md   16 'CueInFade'            || exit 1
check_token .claude/skills/ma3-spatial-pointing/SKILL.md      163 '삼킨다'                || exit 1

# 좌표 해소 — path:N 을 뽑아 그 행이 실제로 존재하는지 확인한다.
# `[0-9]+` 만으로는 99999 같은 날조 행번호가 통과한다(감사 P1-2).
badcoord=$(grep -oE '[A-Za-z0-9_./-]+\.(md|py):[0-9]+' "$D" | sort -u | while read -r pair; do
  f=${pair%:*}; n=${pair##*:}
  [ -f "$f" ] || { echo "$pair 파일 없음"; continue; }
  LC_ALL=C awk -v n="$n" 'NR==n{f=1} END{exit !f}' "$f" || echo "$pair 행 없음"
done)
[ -z "$badcoord" ] && echo "PASS 인용 좌표 전량 해소 (cited=$cited)" \
  || { echo "FAIL 좌표 미해소:"; echo "$badcoord"; exit 1; }
```

### AC-008 (REQ-B16-005) — 조준이 참조 부록에 비도구 기능으로 노출되고, 도구 표는 33행을 유지

```bash
G=docs/user-guide.html
# 부록 구간에 종료 앵커를 준다 — 없으면 EOF까지 뻗어 푸터가 검사에 잡힌다(감사 N-4)
apx=$(LC_ALL=C awk '/id="appendix-tools"/{f=1} f&&/<footer/{f=0} f' "$G")
[ -n "$apx" ] || { echo "FAIL appendix-tools 구간 추출 실패"; exit 1; }
# (1) M2가 신설하는 전용 리터럴 2종 — 기존 마크업으로는 충족될 수 없다
sec=$(printf '%s' "$apx" | grep -cE 'class="non-tool"')
[ "$sec" -ge 1 ] || { echo "FAIL 비도구 기능 절 없음 (class=\"non-tool\" 0건)"; exit 1; }
cond=$(printf '%s' "$apx" | grep -cE 'class="fire-condition"')
[ "$cond" -ge 1 ] || { echo "FAIL 발화 조건 블록 없음 (class=\"fire-condition\" 0건)"; exit 1; }
# (2) 발화 조건의 내용 — 대상과 목표가 둘 다 언급돼야 한다
fc=$(printf '%s' "$apx" | grep -A3 'class="fire-condition"')
printf '%s' "$fc" | grep -qE '대상' || { echo "FAIL 발화 조건에 '대상' 없음"; exit 1; }
printf '%s' "$fc" | grep -qE '좌표|중앙' || { echo "FAIL 발화 조건에 목표(좌표/중앙) 없음"; exit 1; }
# (3) 도구 표는 현행 마크업 그대로 33행 — 재작성을 요구하지 않는다
rows=$(printf '%s' "$apx" | grep -cE '^ *<tr><td class="c">[^<]*</td><td><code>')
[ "$rows" -eq 33 ] || { echo "FAIL 도구 표 행 수 $rows != 33"; exit 1; }
n34=$(grep -cE '34(가지|종|개)' "$G")
[ "$n34" -eq 0 ] || { echo "FAIL 34 오기 $n34건"; exit 1; }
echo "PASS 비도구 절 $sec · 발화 조건 $cond · 도구 표 ${rows}행"
```

기대: `PASS 비도구 절 1 · 발화 조건 1 · 도구 표 33행`.

**M2가 신설해야 하는 리터럴 2종**: `class="non-tool"` · `class="fire-condition"`.
리터럴이 규정돼야 AC가 셀 수 있다(규약 2).

#### v0.4.0에서 고친 것 — 자기인증이 하위검사로 숨어 있었다

v0.3.0은 표제 증상(무변경 HEAD 통과)은 없앴으나 하위검사 셋에 결함이 남아 있었다.
감사 2회차 N-4가 셋 다 재현했다:

| 결함 | v0.3.0 형태 | 무변경 HEAD에서 | 교정 |
|---|---|---|---|
| 종료 앵커 부재 | `LC_ALL=C awk '/id="appendix-tools"/{f=1} f'` | 구간이 **EOF까지** 뻗어 문서 **푸터**가 검사에 잡힘 | `f&&/<footer/{f=0}` 추가 |
| 조준 검사 | `grep -cE '조준\|겨냥' >= 1` | **기존 도구 표 행**(`get_spatial_context` 설명)이 충족 → **이미 통과** | 전용 리터럴 `class="non-tool"`로 교체 |
| 발화 조건 검사 | `grep -cE '대상\|좌표' >= 1` | 같은 행 + **푸터**(`대상 앱: grandMA3 onPC…`)가 충족 → **이미 통과** | `class="fire-condition"` 블록 안에서 `대상` **AND** `좌표\|중앙` |

**즉 M2가 발화 조건을 한 글자도 쓰지 않아도 두 하위검사가 통과했다.** 자기인증이
사라진 게 아니라 한 층 아래로 내려가 있었다.

**그리고 행 수 검사가 승인되지 않은 재작성을 요구했다.** v0.3.0은 `^<tr data-tool=` 33건을
요구했는데 현행 행은 `    <tr><td class="c">1</td>…`(4칸 들여쓰기, `data-tool` 없음)이다.
그대로면 M2가 33행 전부에 속성을 붙이고 **동시에 들여쓰기를 0칸으로 옮겨야** 한다 —
REQ-B16-005 R이 요구한 것은 행 수 **"유지"**인데 검사 방식이 그것을 **재작성**으로 뒤집었다.
정규식 안에 숨은 서식 요구였다. 현행 리터럴을 세도록 바꿔 **마크업 변경 0**으로 만들었다.

### AC-009 (REQ-B16-005) — 유령 식별자 0 유지 (LDGUIDE AC-LDG-019 승계)

```bash
grep -oE '^            name="[a-z_]+",$' "$T" | sed 's/.*name="//;s/",//' | sort > /tmp/b16-tools.txt
tn=$(wc -l < /tmp/b16-tools.txt | tr -d " "); [ "$tn" -ge 30 ] || { echo "FAIL 도구 명단 $tn건 — 추출 실패"; exit 1; }
grep -oE '\b[a-z]+_[a-z_]+\b' "$G" | sort -u > /tmp/b16-used.txt
printf 'contents_unavailable\ndrilldown_capped\n' | sort > /tmp/b16-allow.txt
ghost=$(comm -23 /tmp/b16-used.txt /tmp/b16-tools.txt | comm -23 - /tmp/b16-allow.txt)
[ -z "$ghost" ] && echo "PASS 유령 0" || { echo "FAIL 유령:"; echo "$ghost"; exit 1; }
```

도구 명단 비공허성 가드(`tn >= 30`)가 없으면 추출 정규식이 깨졌을 때 차집합이 **가이드의
모든 토큰**을 유령으로 뱉거나, 반대로 명단이 비어 통과할 수 있다.

### AC-010 (REQ-B16-006) — 서술 정정 3건이 원문·정정 쌍으로 존재

```bash
pairs=$(grep -cE '^\| 정정-[0-9]+ \|' "$D")
[ "$pairs" -eq 3 ] && echo "PASS 정정 3건" || { echo "FAIL 정정 $pairs건 (기대 3)"; exit 1; }
```

### AC-011 (REQ-B16-007) — 시간 예측 0건

```bash
for f in "$D" "$P" docs/user-guide.html; do
  [ -f "$f" ] || { echo "FAIL 검사 대상 $f 부재 — 대상이 없으면 위반도 없다(규약 3)"; exit 1; }
  hits=$(grep -nE '[0-9]+[[:space:]]*~[[:space:]]*[0-9]+[[:space:]]*(주|개월)|[0-9]+[[:space:]]*(주|개월|일)[[:space:]]*(내|이내|안에|소요|예상|걸림)' "$f")
  [ -z "$hits" ] || { echo "FAIL 시간 예측 in $f:"; echo "$hits"; exit 1; }
done
echo "PASS 시간 예측 0"
```

**v0.6.0 정정 — 가이드를 범위에 넣었다.** v0.5.0은 가이드 쪽 시간 예측을 LDGUIDE
`AC-LDG-007`에 위임한다고 적었다. **그 위임 전제가 술어 ③에서 무너진다** — LDGUIDE-001은
`status: completed`이고, 이 SPEC의 M2가 가이드를 **새로 고친다.** 완결된 SPEC의 AC는 이후
변경을 지키지 않는다(감사 3회차 R3-5). 현행 가이드가 이미 0이므로 위양성은 없다.

**검사 범위가 spec/plan을 제외하는 이유 [HARD]** — `spec.md`·`acceptance.md`는 금지형을
**명시하기 위해** 그 형태를 인용해야 한다(REQ-B16-007 R의 `즉시(1~2주)`, §G.8 참양성
픽스처). 이 두 파일을 범위에 넣으면 금지 규정 자체가 위반으로 걸린다 — 실제로 초안에서
그렇게 걸렸고, 그래서 범위를 좁혔다. `plan.md`는 현재 깨끗하지만 같은 이유로 제외한다:
계획 문서도 금지형을 인용할 자유가 있어야 한다. **산출물(`$D`·`$P`·가이드)은 제외하지 않는다.**

**남는 구멍**: `spec.md`·`plan.md`는 여전히 이 AC의 시야 밖이다. 금지형을 인용해야 하는
문서이므로 의도된 제외이며, 그 대가로 두 문서의 진짜 시간 예측은 사람 리뷰가 유일한 방어다.

**알려진 위양성 계열 (LDGUIDE §G 기각 기록 승계)**: `10분 간격 백업` · `90일 보관` 형태는
기간 명사이지 예측이 아니다. 위 정규식은 범위형(`N~M주`)과 예측 어미형(`N주 내/소요/예상`)만
잡고 순수 기간 명사는 잡지 않는다. 광역형(`[0-9]+(주|개월)` 단독)은 이 위양성 때문에
LDGUIDE에서 기각됐으며 여기서 다시 제안하지 않는다.

### AC-012 (REQ-B16-008) — 선언한 AC 수 == 실제 정의 수 == 커버리지 분모

```bash
A=.moai/specs/SPEC-COPILOT-BLOCKED16-001/acceptance.md
defined=$(grep -cE '^### AC-[0-9]{3}' "$A")
[ "$defined" -ge 1 ] || { echo "FAIL AC 정의 0건 — 추출 정규식이 깨졌다"; exit 1; }
declared=$(grep -oE '<!-- AC-COUNT: [0-9]+ -->' "$A" | grep -oE '[0-9]+')
[ -n "$declared" ] || { echo "FAIL AC-COUNT 리터럴 부재"; exit 1; }
denom=$(grep -oE '커버리지 \*\*[0-9]+/[0-9]+\*\*' "$A" | grep -oE '/[0-9]+' | tr -d '/')
[ -n "$denom" ] || { echo "FAIL 커버리지 분모 부재"; exit 1; }
[ "$defined" -eq "$declared" ] && [ "$defined" -eq "$denom" ] \
  && echo "PASS 선언=$declared 정의=$defined 분모=$denom" \
  || { echo "FAIL 선언=$declared 정의=$defined 분모=$denom"; exit 1; }
```

기대: 세 값이 **일치**. (수를 여기 적지 않는다 — 적는 순간 `AC-COUNT` 리터럴 말고
총계의 두 번째 출처가 되고, 그것이 REQ-B16-008이 금지한 형태다. v0.3.0은 여기에 `12`를
박아 두고 실제가 `13`이 됐다 — 감사 2회차 N-3.)

**세 가드가 각각 다른 것을 막는다** — `defined >= 1`은 추출 정규식 파손 시의 fail-open을,
`-n declared`는 리터럴 삭제 시의 통과를, `-n denom`은 커버리지 절 삭제 시의 통과를 막는다.
셋 중 하나라도 빠지면 "대상이 없어서 어긋남도 없다"가 통과가 된다.

**이 AC가 스스로 만드는 위험**: 검사를 고치면 항상 통과하는 새 검사가 생긴다는 것이 이
저장소의 기록된 교훈이다. 그래서 이 AC 자신을 §G.9에서 3방향으로 뮤테이션했다 —
리터럴만 틀리기 / 분모만 틀리기 / 리터럴 삭제. 세 방향 모두 잡히지 않으면 이 AC는
자기가 막겠다던 결함을 그대로 통과시킨다.

### AC-013 (REQ-B16-009) — 변경 파일 허용 2경로 + git 가시 오염 0 + **중첩 `.moai` 0** + 외부 URL 0

```bash
BASE=$(git merge-base HEAD origin/main)
[ -n "$BASE" ] || { echo "FAIL merge-base 미해소 — 기준점 없이 세면 무의미"; exit 1; }
files=$(git diff --name-only "$BASE"...HEAD)
[ -n "$files" ] && echo "변경 파일 $(printf '%s\n' "$files" | wc -l | tr -d ' ')건" \
  || { echo "FAIL 변경 0건 — 비교 기준이 잘못됐다"; exit 1; }
outside=$(printf '%s\n' "$files" \
  | grep -vE '^\.moai/specs/SPEC-COPILOT-BLOCKED16-001/|^docs/user-guide\.html$')
[ -z "$outside" ] && echo "PASS 허용 2경로뿐" || { echo "FAIL 범위 밖:"; echo "$outside"; exit 1; }

# 미추적 축 — git status는 이것을 보지 못한다(아래 [HARD] 참조)
stray=$(git status --porcelain | LC_ALL=C awk '{print $2}' \
  | grep -vE '^\.moai/specs/SPEC-COPILOT-BLOCKED16-001/|^docs/user-guide\.html$|\.jsonl$')
[ -z "$stray" ] && echo "PASS git 가시 오염 0" || { echo "FAIL git 가시 범위 밖:"; echo "$stray"; exit 1; }

# git에 눈먼 축 — 파일시스템을 직접 본다. git 계열은 어떤 형태로도 이 자리를 못 본다.
# 추적본은 저장소의 일부이지 오염이 아니다 — 추적 파일이 0건인 중첩 .moai만 stray다
nested=""
for d in $(find . -type d -name '.moai' -not -path './.git/*' -not -path './.moai'); do
  [ -z "$(git ls-files "$d")" ] && nested="$nested $d"
done
[ -z "$nested" ] && echo "PASS 중첩 .moai stray 0" || { echo "FAIL stray:"; echo "$nested"; exit 1; }

# 외부 URL 0 (M3-5) — LDGUIDE가 아니라 이 SPEC이 자기 diff에 대해 센다
urls=$(grep -coE 'https?://' docs/user-guide.html)
[ "$urls" -eq 0 ] && echo "PASS 외부 URL 0" || { echo "FAIL 외부 URL ${urls}건"; exit 1; }
```

기대: `PASS 허용 2경로뿐`.

#### [HARD] git 계열은 이 오염을 구조적으로 볼 수 없다

v0.4.0의 미추적 축은 `git status --porcelain`이었다. **stray가 실제로 떨어지는 자리에서는
영원히 통과한다** — 그 자리를 `.gitignore`가 명시적으로 무시하기 때문이다:

```bash
git check-ignore -v .moai/specs/SPEC-COPILOT-BLOCKED16-001/.moai/state/config-cache.json
#  → .gitignore:248:.moai/specs/*/.moai/	.moai/specs/…/.moai/state/config-cache.json
git status --porcelain -uall | grep -c 'BLOCKED16-001/.moai'
#  → 0        (-uall 로도 안 보인다)
```

**통과가 부재의 증거가 아니라 관측 표면 밖이라는 뜻이었다.**

그리고 `.gitignore:248`(`.moai/specs/*/.moai/`)과 `:250`(`server/**/.moai/`)은
**누군가 이 문제를 전에 겪고 gitignore로 "고친" 흔적**이다. 이 저장소의 기록된 교훈
(검사를 고치면 항상 통과하는 새 검사가 생긴다 — 3라운드 중 두 번째 기전이 **gitignore**였다)의
세 번째 재발이다.

**248행을 지우는 방향은 택하지 않는다** — 다른 SPEC들의 기대를 깨고, "안 보이게 만든 규칙을
지워서 보이게 한다"는 교정은 이 SPEC 범위 밖이다. **보는 쪽을 바꿨다**: `find`는 gitignore를
읽지 않으므로 이 자리를 본다.

#### 생산자 — 측정으로 특정함 (추측 아님)

통제 실험. stray 3건을 전부 제거해 기준선을 만든 뒤:

| 실험 | 명령 | 결과 |
|---|---|---|
| 1 | 평범한 Bash 호출(훅 발화), cwd=루트 | 재생성 **0** |
| 2 | `(cd .moai/specs && moai todo list)` | `.moai/specs/.moai/` **생성** |
| 3 | `(cd .moai/specs/SPEC-COPILOT-BLOCKED16-001 && moai session current)` | `.moai/specs/SPEC-COPILOT-BLOCKED16-001/.moai/` **생성** |
| 4 | 실험 2를 재실행(파일 이미 존재) | mtime **불변** — 이미 있으면 다시 쓰지 않는다 |

**생산자 = 프로젝트 루트가 아닌 cwd에서 호출된 `moai` CLI.** 상태 캐시를 cwd 상대 경로에 쓴다.

실험 4가 lead의 관측(`(cd .moai/specs && moai todo list)`로 재현 시도했으나 파일이 갱신되지
않았다)과 정합한다 — **생성은 되지만 이미 있으면 갱신하지 않아** 기존 파일만 보면 안 보인다.

이것이 `plan.md` §C.2의 명시 경로 스테이징 [HARD]가 필요한 이유이기도 하다. `.gitignore`가
가려 주는 동안은 커밋에 실리지 않지만, 가림막이 바뀌면 그때부터 실린다.

**고정 SHA를 쓰지 않는다** — LDGUIDE `§D.13`이 rebase 후 기준점이 무관한 이력 296파일을
삼켜 **상시 실패**(fail-closed)한 선례가 있다. `merge-base`를 매번 계산한다.

**두 가드가 각각 다른 것을 막는다**: `-n "$BASE"`는 기준점 미해소 시의 무의미한 통과를,
`-n "$files"`는 비교 기준이 잘못돼 diff가 비었을 때의 fail-open을 막는다.
후자가 없으면 `outside`도 비고 `PASS`가 나온다 — **아무것도 안 바꿔서 통과**하는 형태다.

**LDGUIDE `AC-LDG-013`에 위임할 수 없는 이유**: 그쪽 허용 경로는
`.moai/specs/SPEC-COPILOT-LDGUIDE-001/`이라 이 SPEC의 diff에 돌리면 **오히려 실패**한다.

## §B. REQ ↔ AC 대응

| REQ | AC | 미대응 |
|---|---|---|
| REQ-B16-001 | AC-001 · AC-002 · AC-003 · AC-004 | 없음 |
| REQ-B16-002 | AC-005 | 없음 |
| REQ-B16-003 | AC-006 | **부분** — `exec` 미사용은 기계 검증 불가(§C.1) |
| REQ-B16-004 | AC-007 | 없음 |
| REQ-B16-005 | AC-008 · AC-009 | 없음 |
| REQ-B16-006 | AC-010 | 없음 |
| REQ-B16-007 | AC-011 | **부분** — 위양성 계열 잔존(§A AC-011 각주) |
| REQ-B16-008 | AC-012 | 없음 |
| REQ-B16-009 | AC-013 | 없음 |

## §C. 기계 검증이 닿지 않는 곳 — 명시

### §C.1 `exec` 미사용은 사후 기계 검증이 불가하다

REQ-B16-003의 "읽기 동사만 쓴다"는 **프로브 실행 시점의 행위**이며, 산출물에서 사후로
증명되지 않는다. `probe.md`에 `exec`이 없다는 것은 쓰지 않았다는 증거가 아니라 적지
않았다는 사실일 뿐이다.

대체 통제(약함, 명시):
- `probe.md`의 모든 명령 열이 `responder_roundtrip ... --skip-exec` 형태인지 육안 확인.
- 프로브 전후 쇼파일 객체 수 대조는 **하지 않는다** — 그 대조 자체가 콘솔 질의이며,
  미접속 상태에서는 수행 불가하고, 접속 상태에서도 "바뀌지 않았다"를 증명하려면
  전수 열거가 필요해 예산을 넘는다.

이 한계를 닫지 않고 남긴다.

### §C.2 미측정 분기의 AC는 내용을 검사하지 않는다

AC-005는 판정 열의 **값 집합**만 본다. `미측정` 행이 GO·NEGATIVE 두 분기를 실제로
설계했는지는 산문 검사이며 기계로 세지 않는다. 처분표 리뷰에서 사람이 본다.

### §C.3 프로브 최소 행 수 9의 근거와 한계

게이트 3종 × 역할 3종 = 9가 하한이다. 후보 속성이 여럿이므로 실제 행은 더 많다.
이 하한은 **역할 누락**을 잡고 **속성 후보 누락**은 잡지 못한다 — 후보 목록의 충분성은
plan §B M0-2의 표가 소유하며 AC가 세지 않는다.

## §D. 뮤테이션 검증 커버리지

| AC | 뮤테이션 수행 | 결과 |
|---|---|---|
| AC-001 | O | §G.1 |
| AC-002 | O | §G.2 |
| AC-003 | O | §G.3 |
| AC-004 | O | §G.4 — **1회 헛돌았고 재시도해 잡았다** |
| AC-005 | O | §G.5 |
| AC-006 | O | §G.6 — **죽은 코드 1행 발견·제거, 행수 유지형 재시도** |
| AC-009 | O | §G.7 |
| AC-011 | O | §G.8 — 양방향(참양성 6/6 · 위양성 0/5) |
| AC-012 | O | §G.9 — 3방향(리터럴 오기 · 분모 오기 · 리터럴 삭제) |
| AC-007 | O | §G.11 — 3방향(정상 · 날조 행번호 · 없는 파일) |
| AC-008 | O | §G.10 — **개정 전 HEAD에서 실패 확인**(자기인증 제거 실증) |
| AC-010 | O | §G.12 |
| AC-013 | O | §G.13 |

커버리지 **13/13**. 이 수를 부풀리지 않는다 — LDGUIDE가 "전량 검증"이라 적었다가 실제
4/19였던 선례가 있다. **미검증은 0건이다** — v0.2.0까지 남아 있던 3건(AC-007·008·010)은
v0.3.0에서 전부 뮤테이션했다(§G.10~12).

> **v0.4.0 정정** — v0.3.0은 분자·분모를 `13/13`으로 고치면서 바로 다음 문장의
> "미검증 3건"을 그대로 두었다. **같은 문단이 스스로를 부정했다**(13/13이면 미검증은 0이다).
> AC-012는 산문을 보지 않으므로 기계 검사가 통과하는 채로 남았다 — 감사 2회차 N-3.

이 분모는 AC-012가 `AC-COUNT` 리터럴·실제 정의 수와 함께 기계 대조한다 — 세 곳이
어긋나면 실패한다. **여기에도 수를 다시 쓰지 않는다**(N-3).

## §G. 뮤테이션 원자료

실패해야 정상인 입력을 만들어 실제로 실패하는지 확인한 기록이다.
관측자: plan 열 세션 `plan-tjxy3n`, 2026-08-18. 픽스처는 세션 스크래치패드에 생성했다.

### §G.1 AC-001 — 행 수

| 입력 | 관측 |
|---|---|
| 16행 픽스처 | `PASS rows=16` |
| 1행 삭제(15행) | `FAIL rows=15 (기대 16)` |

### §G.2 AC-002 — 처분 열 집합

| 입력 | 관측 |
|---|---|
| 전량 `③` | `PASS 처분 열 전량 적법` |
| 1행을 `④`로 | `FAIL: D-2 -> [④]` |
| **빈 표** | `FAIL 모집단 0 != 16` — 모집단 가드가 fail-open을 막는다 |

빈 표 검증이 이 AC의 핵심이다. 가드가 없으면 표가 비었을 때 "위반 0"이 되어 통과한다.

### §G.3 AC-003 — 측정 종류 열 집합

| 입력 | 관측 |
|---|---|
| 전량 `무관` | `PASS 측정 종류 적법` |
| 1행을 `읽음`으로(적법값 `읽기`가 아님) | `FAIL: D-2 -> [읽음]` |

### §G.4 AC-004 — 공란

| 입력 | 관측 |
|---|---|
| 공란 없음 | `PASS 공란 0` |
| **1차 뮤테이션**(존재하지 않는 문자열 치환) | `PASS 공란 0` — **뮤테이션이 헛돌았다** |
| 2차 뮤테이션(실제 행의 근거 칸 비움, diff로 적용 확인) | `FAIL: D-2 필드7 공란` |

1차의 통과는 명령이 옳다는 증거가 아니라 **뮤테이션이 아무것도 바꾸지 않았다**는 증거였다.
`diff`로 적용 여부를 먼저 확인한 뒤에야 결과를 판정으로 썼다. 이 절차를 남긴다 —
뮤테이션 자체도 헛돌 수 있다.

### §G.5 AC-005 — 프로브 판정 열 집합

| 입력 | 관측 |
|---|---|
| 전량 `미측정` | `PASS 판정 열 적법` |
| 1행을 `판독 불가`로 | `FAIL: P-2 -> [판독불가]` |

REQ-B16-002가 금지한 바로 그 값이 실제로 걸린다.

### §G.6 AC-006 — 대조군 쌍

| 입력 | 관측 |
|---|---|
| 게이트 3종 × 역할 3종 = 9행 | `PASS 대조군 쌍 전량 존재` |
| **1차 뮤테이션**(양성 대조 행 삭제, 8행) | `FAIL 프로브 행 8 < 9` — **검사 대상이 아니라 행수 가드가 잡았다** |
| 2차 뮤테이션(행 수 9 유지, 역할만 `본 프로브`로 바꿔치기) | `FAIL: A: 양성대조 없음` |

1차는 통과했지만 **역할 대조 로직이 작동한다는 증거가 아니었다**. 행 수를 고정한 채
역할만 무너뜨려야 그 로직이 시험된다.

초안의 awk에는 `for(r in want) ;` 한 행이 있었다 — `want` 배열이 정의된 적 없어 0회
순회하는 죽은 코드였고, 검사는 그 뒤 하드코딩된 세 줄로만 동작하고 있었다. 검증 과정에서
발견해 `split()` 기반으로 교체했다.

### §G.7 AC-009 — 유령 식별자 (실물 저장소 대상)

| 입력 | 관측 |
|---|---|
| 현재 `docs/user-guide.html` | `도구 명단 tn=33` · `PASS 유령 0` |
| 사용 토큰 목록에 `fake_ghost_tool` 주입 | `PASS 뮤테이션 검출: fake_ghost_tool` |
| 도구 추출 정규식 파손(`[A-Z]+` 대문자형) | `PASS 비공허성 가드 발동 (tb=0)` |

세 번째 행이 규약 3의 실증이다. 가드가 없으면 추출이 깨졌을 때 명단이 비고, 차집합이
가이드의 모든 토큰을 유령으로 뱉거나 반대로 조용히 통과한다.

### §G.8 AC-011 — 시간 예측 (양방향)

참양성 픽스처 6종 — `즉시 (1~2주)` · `측정 후 (2~4주)` · `중기 (1~2개월)` · `3주 내 완료` ·
`2개월 소요` · `5일 이내`:

```
검출 6/6
```

위양성 픽스처 5종 — `10분 간격 백업` · `90일 보관 정책` · `버전 2주차 회고 문서` ·
`Cue 3 페이드 2초` · `33가지 도구`:

```
검출 0
```

**LDGUIDE 기각형 대조**: 광역형 `[0-9]+[[:space:]]*(주|개월)`를 같은 위양성 픽스처에
돌리면 `1`건이 걸린다(`버전 2주차 회고 문서`). 기각 사유가 지금도 유효함을 확인했으므로
이 형태를 다시 제안하지 않는다.

### §G.9 AC-012 — 선언 수 무결성 (3방향)

이 AC는 **자기가 막겠다던 결함을 자기가 통과시킬 수 있는** 종류다. 이 저장소에는
"검사를 고치면 항상 통과하는 새 검사가 생긴다"는 기록된 교훈이 있으므로 3방향으로 쟀다.
각 뮤테이션은 `diff -q`로 실제 적용 여부를 먼저 확인했다(§G.4 절차 승계).

| 입력 | 적용 확인 | 관측 |
|---|---|---|
| 관측 당시 판본(v0.2.0) | — | `PASS 선언=12 정의=12 분모=12` |
| 리터럴만 오기(`AC-COUNT: 11`) | 적용됨 | `FAIL 선언=11 정의=12 분모=12` |
| 커버리지 분모만 오기(`9/11`) | 적용됨 | `FAIL 선언=12 정의=12 분모=11` |
| 리터럴 행 삭제 | 적용됨 | `FAIL AC-COUNT 리터럴 부재` |

세 번째가 fail-open 방어의 실증이다. `-n "$declared"` 가드가 없으면 리터럴이 사라졌을 때
`declared`가 빈 문자열이 되고, `[ 12 -eq "" ]`는 수치 비교가 아니라 문자열 비교로 떨어져
**어긋남이 없는 것처럼 통과**한다(§0 규약 3).

**M4 — AC를 늘리고 선언을 안 고치는 방향** (관측자: **`lead-tjxy3n`**, 2026-08-18)

| 입력 | 적용 확인 | 관측 |
|---|---|---|
| 사본에 `### AC-013` 한 줄 추가 | 적용됨(정의 수 12 → 13) | 원본 `PASS 선언=12 정의=12 분모=12` exit=0 / 뮤테이션 `FAIL 선언=12 정의=13 분모=12` exit=1 |

**이 방향이 앞의 셋보다 중요하다.** 앞의 셋은 전부 **선언 쪽을 틀리게 하는** 방향인데,
이번 결함이 실제로 밟은 경로는 반대쪽 — **AC를 늘리고 선언을 안 고치는 것**이다. 내가 잰
세 방향에는 그 경로가 없었고, lead가 쳐서 잡히는 것을 확인했다. **뮤테이션 방향을 고를 때
"실제로 고장난 적 있는 경로"를 먼저 친다** — 이것이 이 항목이 남기는 규율이다.

**이 AC가 여전히 막지 못하는 것**: `AC-COUNT` 리터럴과 커버리지 분모와 실제 정의 수를
**동시에 같은 틀린 값으로** 바꾸면 통과한다. 세 곳이 함께 틀릴 확률은 낮지만 0이 아니며,
특히 일괄 치환으로 개수를 바꿀 때 그렇다. 이 구멍은 닫지 않고 남긴다 — 닫으려면 네 번째
출처가 필요하고, 그것이 곧 이 REQ가 금지한 중복 출처다.

### §G.10 AC-008 — 개정 전 HEAD에서 실패하는가 (자기인증 제거 실증)

감사 P0-2는 **초판 AC-008이 무변경 HEAD에서 통과**함을 보였다. 재작성본이 같은 함정에
빠지지 않았는지가 이 항목의 유일한 질문이다.

```bash
G=docs/user-guide.html
apx=$(LC_ALL=C awk '/id="appendix-tools"/{f=1} f' "$G")
printf '%s' "$apx" | grep -cE 'class="non-tool"'   # 0
printf '%s' "$apx" | grep -cE '^<tr data-tool='     # 0
```

| 대상 | 관측 | 판정 |
|---|---|---|
| 초판 AC-008 · 무변경 HEAD | 조준 3 · 33 주장 2 · 34 오기 0 → **전 항목 통과** | 자기인증 |
| 재작성 AC-008 · 무변경 HEAD | `class="non-tool"` **0건** → `FAIL 부록에 비도구 기능 절 없음` | **정상**(M2가 만들어야 통과) |

`id="appendix-tools"` 앵커 자체는 실재하므로 구간 추출은 성공하고, 실패는 **내용 부재**로
떨어진다 — 앵커 부재로 인한 우연한 실패가 아니다.

### §G.11 AC-007 — 인용 좌표 해소 (3방향)

초판 AC-007은 `path:[0-9]+` 존재만 셌다. 감사 P1-2가 행번호를 `99999`로 망가뜨린 픽스처가
`PASS`함을 보였다 — **행 번호 귀속을 요구하는 AC가 행 번호를 검증하지 않았다.**

| 입력 | 관측 |
|---|---|
| 정상 좌표 3건 | `PASS 좌표 전량 해소` |
| `progress.md:99999` 주입 | `FAIL: ...progress.md:99999 행 없음` |
| 없는 파일 경로 주입 | `FAIL: server/nope/ghost.py:5 파일 없음` |

**작성 중 이 검사 자체가 한 번 깨졌다.** 첫 형태는 `while IFS=: read -r f n` + `wc -l`을
썼는데 함수 안 중첩 명령 치환에서 `wc`·`tr`이 실행되지 않아 **정상 픽스처까지 FAIL**했다.
fail-closed 방향이라 위험하지는 않았으나 판별력이 0인 검사였다 — 정상과 이상을 구분하지
못하면 검사가 아니다. `LC_ALL=C awk -v n=... 'NR==n{f=1} END{exit !f}'` 단일 명령으로 바꿔 3방향을
다시 쟀다. **새로 쓴 명령도 헛돈다**(규약 5)의 실례를 하나 더 남긴다.

### §G.12 AC-010 — 정정 행 수

| 입력 | 관측 |
|---|---|
| 정정 3행 | `PASS 정정 3건` |
| 정정 2행 | `FAIL 정정 2건 (기대 3)` |

### §G.13 AC-013 — 변경 파일 범위 (현행 트리 실행)

```bash
BASE=$(git merge-base HEAD origin/main)   # 15590e3630ffced112eb7b17e8d2c353fcd1fc97
git diff --name-only "$BASE"...HEAD        # (출력 없음)
```

현 시점 HEAD는 `merge-base`와 같고 SPEC 파일은 아직 미커밋이라 diff가 **0건**이다.
`-n "$files"` 가드가 `FAIL 변경 0건 — 비교 기준이 잘못됐다`로 떨어진다 — **의도한 fail-closed**다.
이 가드가 없으면 `outside`도 비어 `PASS 허용 2경로뿐`이 나온다: **아무것도 안 바꿔서
통과**하는 형태이며, AC-008이 초판에서 빠졌던 함정과 같은 종류다.

run 종료 시점에는 SPEC 파일이 커밋돼 diff가 채워지므로 이 AC가 실질 판정을 낸다.
