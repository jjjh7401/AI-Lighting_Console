# SPEC-COPILOT-BLOCKED16-001 — M0 비파괴 라이브 읽기 프로브 원장 (probe)

측정 기준: 워크트리 `/Users/studiox/orca/workspaces/AI-Lighting_Console/blocked16`,
브랜치 `jjjh7401/blocked16`, base `15590e3`, 2026-08-18. 측정 주체 run-tjxy3n.

`exec` · `deploy` 동사 사용 0건. 쇼파일 쓰기 0건. 오브젝트 생성 0건(`plan.md` §C.3).

## §1. 콘솔 접속 상태 — 실측

M0 착수 시점에 grandMA3 onPC는 **미접속**이다. 명령과 출력으로 귀속한다.

> **2026-08-23 상태 변경** — 이 §1 은 2026-08-18 M0 시점의 실측 기록이며 그대로 둔다.
> 그 뒤 콘솔이 기동돼 게이트 B·C 를 실측했다. 현재 조건은 §2 「측정 조건」 표를 볼 것.

```bash
ps aux | grep -i "gma3\|grandma\|onpc" | grep -v grep    # 출력 없음 == 미접속
lsof -nP -iUDP | grep -E ":8000|:9005"
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

관측:

```
(ps: 출력 없음)
python3.1 12689 studiox    4u  IPv4 0x19bdefca43329d74      0t0  UDP 127.0.0.1:9005
(lsof TCP:8000: 출력 없음 — 앱 서버도 미기동)
```

UDP 9005를 잡고 있는 것은 콘솔이 아니라 로컬 파이썬 프로세스이며, 앱 서버의 TCP 8000은
열려 있지 않다. 프로브 매체(`responder_roundtrip`)는 앱 서버를 경유하므로 **발화 자체가
불가능**하다.

→ 게이트 A · B · C의 판정은 전부 **`미측정`**이다. **`판독 불가`가 아니다**(REQ-B16-002).
게이트 D는 콘솔 무관이므로 이 상태와 독립적으로 판정된다.

## §2. 프로브 원장

| id | 게이트 | 핸들 | 속성 | 역할 | 명령 | 관측 출력 | 판정 |
|---|---|---|---|---|---|---|---|
| P-1 | A. 페이드 Part 주소화 | `DataPool/Sequences/<n>/<cueName>/<partName>` | `CueInFade` | 본 프로브 | `--prop-path DataPool/Sequences/1/CueZero --prop-name CueInFade` (Part 부재로 큐 노드에 대체 발사) | `ok=False` — `property not readable: CueInFade`. **다만 원장이 물은 Part 노드가 아니다** | **측정 불가** — 재료 부재 |
| P-2 | A. 페이드 Part 주소화 | 위와 동일(큐 노드 대체) | `CueInFadeee` (날조) | 음성 대조 | `--prop-name CueInFadeee` | `ok=False` — `property not readable: CueInFadeee`. 채널에 판별력 있음 | 대조 성립 |
| P-3 | A. 페이드 Part 주소화 | `DataPool/Sequences/101/Pos 228/Pos 228` | `CueInFade` | 양성 대조 | 기지 GO 기준점 | **발사 못 함 — 이 쇼파일에 그 경로가 없다.** 시퀀스는 1개(`Default`), 자식은 `OffCue`·`CueZero` 뿐 | **측정 불가** |
| P-4 | B. 큐 내용 | `DataPool/Sequences/1/CueZero` (큐 노드축) | `Content` · `Values` · `Parts` · `TrigType` · `Name` | 본 프로브 | `--prop-path DataPool/Sequences/1/CueZero` | `Content`·`Values`·`Parts`·`TrigType` **4종 전부** `ok=False` (`property not readable`) · `Name` → `ok=True value='CueZero'` | **NEGATIVE (귀속)** — 단서는 아래 |
| P-5 | B. 큐 내용 | 위와 동일 | `Contentt` (날조) | 음성 대조 | `--prop-name Contentt` | `ok=False` — `property not readable: Contentt` | 대조 성립 |
| P-6 | B. 큐 내용 | `DataPool/Sequences/1` (시퀀스 핸들) | `CurrentCue` | 양성 대조 | 위와 동일 | **`ok=False` — `property not readable: CurrentCue`.** 원장의 "기지 GO" 가 지금은 거짓이다. 같은 핸들에서 `Name` → `ok=True 'Default'`, 날조 `Namee` → 거절이므로 **장치는 살아 있고 이 거절은 귀속된다**. 같은 핸들 `CueNo` → `ok=True ''` (빈 문자열) | **정정 — 아래 참조** |
| P-7 | C. 팬/틸트 현재값 | `Patch/Stages/1/Fixtures/1` | `pan` · `tilt` · `Pan` · `Tilt` | 본 프로브 | `--prop-path Patch/Stages/1/Fixtures/1` | **4종 전부** `ok=False` — `property not readable: <name>` | **NEGATIVE (귀속)** |
| P-8 | C. 팬/틸트 현재값 | 위와 동일 | `pann` (날조) | 음성 대조 | `--prop-name pann` | `ok=False` — `property not readable: pann` | 대조 성립 |
| P-9 | C. 팬/틸트 현재값 | 위와 동일(동일 슬롯) | `posx` | 양성 대조 | `--prop-name posx` | **`ok=True value='0.0'`** — 같은 핸들에서 장치 생존 확인 | GO |
| P-10 | D. 승계 확인 3건 | 문서 좌표(콘솔 무관) | 승계 앵커 3건 | 본 프로브 | `grep -n` 3건 — §3 표 참조 | 3건 전부 해소. GROUPGEN `progress.md:232` · footprint.py:6(+본문 8-12) · CUETIME `progress.md:16` | GO |
| P-11 | D. 승계 확인 3건 | 문서 좌표(콘솔 무관) | 날조 앵커 3건 | 음성 대조 | `grep -c "게이트 A — 멤버십은 읽을 수 있다"` · `grep -c "ASSUMPTION-99"` · `grep -c "CueOutFadeee"` | `0` · `0` · `0` — 전부 0. 검사에 판별력이 있다 | GO |
| P-12 | D. 승계 확인 3건 | 문서 좌표(콘솔 무관) | 실재 앵커 3건 | 양성 대조 | `grep -c "게이트 A — 멤버십은 읽을 수 없다"` · `grep -c "ASSUMPTION-27"` · `grep -c "CueInFade"` | `1` · `1` · `2` — 전부 1 이상. 검사 장치 생존 확인 | GO |

### 측정 조건 (2026-08-23) — 판정은 이 조건 안에서만 참이다

| 항목 | 값 |
|---|---|
| 응답기 | v1.6.1 · `CopilotResponder` |
| 전송 | `osc.udp://127.0.0.1:8000` · 회신 9005 |
| 발사 | 전부 `--skip-exec` (읽기 전용). **콘솔에 쓰지 않았다** |
| 쇼파일 — 픽스처 | `Patch/Stages/1/Fixtures` childCount 86 (카드 t9 가 넣은 것) |
| 쇼파일 — 시퀀스 | `DataPool/Sequences` childCount **1**(`Default`), 자식은 `OffCue`·`CueZero` 뿐 — **사용자 큐 없음** |
| 시퀀스 상태 | **정지** (같은 핸들 `CueNo` 가 빈 문자열) |
| 그룹 | `DataPool/Groups` childCount 0 |

조건을 적는 이유는 P-6 이다. 원장은 `CurrentCue` 를 "기지 GO" 로 적었는데 이번엔 거절됐다.
원 측정이 틀린 것이 아니라 **조건이 빠져 있었다** — 그때는 시퀀스가 돌고 있었을 것이다.
상태를 안 적은 라이브 판정은 다음 세션에서 뒤집힌다.

### 처분 — 닫힌 것과 못 닫은 것을 섞지 않는다

**게이트 C (팬/틸트 현재값) — 닫힘 · NEGATIVE 귀속**

본 프로브 4종(`pan` `tilt` `Pan` `Tilt`) 전부 거절, 음성 대조 `pann` 거절, **양성 대조 `posx` 가
`ok=True value=0.0`**. 같은 핸들에서 장치가 살아 있으므로 거절은 "장치가 죽어서"가 아니라
"그 프로퍼티라서"다. **팬/틸트 현재값은 이 프로퍼티 채널로 읽을 수 없다** 가 귀속된 판정이다.

**게이트 B (큐 내용) — 닫힘 · NEGATIVE 귀속, 단서 필수**

본 4종 거절, 음성 `Contentt` 거절, 양성 `Name → CueZero` ok. 장치 생존이 확인돼 귀속된다.

⚠️ **단서**: 이 쇼파일엔 사용자 큐가 없다(위 조건표). **내용이 빈 기본 큐(`CueZero`)에서의
거절이므로, 내용 있는 실제 큐에서도 같은지는 이 측정이 답하지 않는다.** 그 확인은 큐가 든
쇼파일이 필요하다.

**게이트 A (페이드 Part 주소화) — 열린 채 · 측정 불가**

NEGATIVE 가 **아니다**. 이 쇼파일에 Part 가 없어 원장이 물은 대상 자체가 부재한다.
P-3 의 양성 기준점 `DataPool/Sequences/101/Pos 228/Pos 228` 도 없다. 큐 노드에 대체
발사한 `CueInFade` 거절은 Part 주소화에 대한 답이 아니다.
**닫으려면 Part 가 있는 쇼파일이 필요하다.**

**P-6 (`CurrentCue`) — 원장 표기 정정**

원장의 "기지 GO" 는 **지금 조건에서 거짓**이다. 거절은 귀속된다(양성 `Name → Default` ok,
날조 `Namee` 거절). 화해 가설은 **상태 의존** — 원 측정은 시퀀스 구동 중이었을 것이다.
확인하려면 시퀀스를 기동해야 하고 그것은 **쓰기**라 이 카드에서 하지 않았다.
`docs/runbooks/fake-real-parity-method.md` §5 **W-1** 로 이연했다.

**게이트 D의 대조군이 게이트 A~C와 다른 이유**: A~C의 대조군은 프로브 장치(응답기 왕복)의
생존을 확인하지만, D의 매체는 `grep`이다. 그래서 D의 음성 대조는 **날조 앵커가 0을 답하는가**
(판별력)를, 양성 대조는 **실재 앵커가 1 이상을 답하는가**(장치 생존)를 본다. 둘 다 통과했으므로
D의 `GO`는 귀속된 판정이다.

## §3. 게이트 D — 인용 유래 전제 3술어 재확인 (`plan.md` §B.9)

| 승계 | ① 좌표 해소 | ② 좌표의 내용이 주장을 담는가 | ③ 소유 SPEC 후속 반전 | 판정 |
|---|---|---|---|---|
| 그룹 멤버십 (GROUPGEN-001) | `progress.md:232` 해소 | `### §E.2.2 게이트 A — 멤버십은 읽을 수 없다 (**증명됨, 추론 아님**)` — 핵심 토큰 담김 | **반전 없음**(`spec.md:5` `status: completed`, 반전 마커 스캔에서 게이트 A 관련 철회 0건) | 승계 유효 |
| 채널폭 (PRECHK-001) | `footprint.py:6` · `progress.md:644` 해소 | `ASSUMPTION-27` 담김. **단 `footprint.py:6`은 역사 서술이고 현재 동작은 8-12행** — 발췌를 6행에서 끊으면 "지금도 비활성"으로 읽힌다 | **반전 없음**(`spec.md:5` `status: completed`). 단 소유 SPEC이 P2-5로 **주장 범위를 스스로 좁혔고**, 이 SPEC은 좁혀진 문면을 승계한다. I-15는 OVERLAP-001(`status: completed`, `patch.py:72` `BOUND_PROVES_CLEAR`)로 출하 완료 | 승계 유효(정정본 한정) |
| 페이드 (CUETIME-001) | `progress.md:16` 해소 | `- readback: Part \`CueInFade\` = **5.0** (Cue의 CueFade prop은 not readable — Part 레벨이 정답)` — 핵심 토큰 담김 | **`판독 불가`** — `spec.md`에 frontmatter가 없어 `status:`를 기계로 읽을 수 없다(`grep -n '^status:'` 출력 없음). 대체 근거: `progress.md:3` `## M1 (T1) — 완료 2026-08-14` + 반전 마커 계수 `0` | 승계 유효(대체 근거) |

**`판독 불가`는 통과가 아니다.** 세 승계 중 CUETIME만 기계 판독 경로가 없으며, 하필 감사
1회차 P0-1이 났던 그 승계다. 값 그대로 적고 대체 근거를 명령·출력으로 남긴다
(`plan.md` §B.9 술어 ③ 3값 규율).

### §3.1 run이 새로 확인한 좌표 정정 1건 [HARD]

`spec.md` §B REQ-B16-005 「발화 조건을 함께 싣는 이유」가 `server/web/session.py:3546-3555`를
인용하며 "`_POINT_AT_TARGET` 정규식을 통과해도 중앙어 또는 좌표 3쌍이 없으면 `return None`"이라
적었다. **술어 ②로 재확인한 결과 그 창이 주장의 핵심 토큰 앞에서 닫힌다.**

```bash
awk 'NR>=3544 && NR<=3558 {printf "%d:%s\n", NR, $0}' server/web/session.py
```

관측(발췌):

```
3546:        """                                    ← 인용 시작점이 docstring 종료 따옴표
3547:        if _POINT_AT_TARGET.search(text) is None:
3548:            return None                        ← 이것은 "동사 부재" 경로다
3554:        elif _POINT_TARGET_CENTRE.search(text) is not None:
3555:            target = PointingTarget(0.0, 0.0, 0.0)
3556:        else:
3557:            return None  # aiming verb without a target — let the model ask
```

주장이 말한 **"대상 부재 시 `return None`"은 3557행**이고, 인용 창은 3555에서 닫혔다.
창 안의 3548행 `return None`은 **동사 부재** 경로여서, 좌표는 해소되고 주장도 참인데
**그 좌표가 주장의 근거를 담고 있지 않다.** 감사 3회차 R3-1과 같은 계열이며, 이 SPEC에서
**네 번째** 재발이다.

→ **정확한 좌표는 `server/web/session.py:3547-3557`이다.** M2 산출물과 처분표는 정정본을
쓴다. 정규식 정의는 `server/web/session.py:218-224`(`_POINT_AT_TARGET` · `_POINT_TARGET_CENTRE`
· `_POINT_TARGET_TRIPLE`).

## §4. 질의 예산

게이트당 발화 0건(콘솔 미접속). 예산 소진 없음. 예산 초과로 중단된 게이트 0건.

## §5. 미측정이 남긴 것 — GO/NEGATIVE 양분기는 처분표가 진다

게이트 A · B · C가 `미측정`이므로 해당 처분 행(D-5 · D-10 · D-12 · D-16)은
**측정 결과에 분기시켜** 설계된다(REQ-B16-002). 분기 문면은 `disposition.md`에 있다.

**2026-08-23 갱신** — 콘솔이 켜져 게이트 B·C 를 실측했다(§2 처분).

| 게이트 | 이전 | 지금 |
|---|---|---|
| A. 페이드 Part | 미측정 | **여전히 못 닫음 — 측정 불가**(쇼파일에 Part 부재) |
| B. 큐 내용 | 미측정 | **NEGATIVE** (단서: 빈 기본 큐 기준) |
| C. 팬/틸트 | 미측정 | **NEGATIVE** (양성 대조 `posx` ok 로 귀속) |

따라서 B·C 에 걸린 처분 행은 이제 분기가 아니라 확정 갈래를 탄다. A 에 걸린 행은
분기 설계를 그대로 유지한다 — **재료가 없어 못 잰 것이지 NEGATIVE 가 아니다.**

## 이력

| 일자 | 내용 |
|---|---|
| 2026-08-18 | M0 최초 작성. 콘솔 미접속 실측 → 게이트 A·B·C `미측정`, 게이트 D `GO`(3술어 재확인 + 대조군 2종). 좌표 정정 1건(session.py 3546-3555 → 3547-3557). 측정 주체 run-tjxy3n, base `15590e3`. |
| 2026-08-18 | sync 감사 F-2 교정. §5의 게이트 의존 행 열거에서 **D-2 제거** — D-2는 게이트 A~C가 아니라 I-14(범위 밖)에 걸려 있다(`disposition.md` §3). 교정 후 4행이 §3 분기 표·이력의 「`미측정` 4행」과 일치. 측정 주체 sync-tjxy3n, 대상 `7c2abf2`. |
| 2026-08-23 | 콘솔 기동 창에서 P-1~P-9 재발화(읽기 전용, `--skip-exec`). 게이트 C **NEGATIVE 귀속**(양성 대조 `posx` ok=True 0.0) · 게이트 B **NEGATIVE 귀속, 단서**(쇼파일에 사용자 큐 없음 — 빈 기본 큐 기준) · 게이트 A **측정 불가**(Part 부재, P-3 기준점 부재) · **P-6 원장 표기 정정** — `CurrentCue` 의 "기지 GO" 가 지금 조건에서 거짓이며 상태 의존 가설은 쓰기가 필요해 런북 §5 W-1 로 이연. 측정 조건표 신설. 측정 주체 카드 t12, 응답기 v1.6.1. |
