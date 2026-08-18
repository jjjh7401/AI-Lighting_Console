# SPEC-COPILOT-BLOCKED16-001 — M0 비파괴 라이브 읽기 프로브 원장 (probe)

측정 기준: 워크트리 `/Users/studiox/orca/workspaces/AI-Lighting_Console/blocked16`,
브랜치 `jjjh7401/blocked16`, base `15590e3`, 2026-08-18. 측정 주체 run-tjxy3n.

`exec` · `deploy` 동사 사용 0건. 쇼파일 쓰기 0건. 오브젝트 생성 0건(`plan.md` §C.3).

## §1. 콘솔 접속 상태 — 실측

M0 착수 시점에 grandMA3 onPC는 **미접속**이다. 명령과 출력으로 귀속한다.

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
| P-1 | A. 페이드 Part 주소화 | `DataPool/Sequences/<n>/<cueName>/<partName>` (실물 이름은 M0 착수 시 `state` 열거로 획득) | `CueInFade` | 본 프로브 | `uv run python -m server.tools.responder_roundtrip --skip-exec --host 127.0.0.1 --port 8000 --listen-port 9005 --prop-path ... --prop-name CueInFade --wait 5` | 미발화 — 콘솔·앱 서버 미기동(§1) | 미측정 |
| P-2 | A. 페이드 Part 주소화 | `DataPool/Sequences/<n>/<cueName>/<partName>` | `CueInFadeee` (날조) | 음성 대조 | 위와 동일, `--prop-name CueInFadeee` | 미발화 — 콘솔·앱 서버 미기동(§1) | 미측정 |
| P-3 | A. 페이드 Part 주소화 | `DataPool/Sequences/101/Pos 228/Pos 228` (CUETIME 기지 기준점. 점 없는 이름) | `CueInFade` | 양성 대조 | 위와 동일, 기지 GO 기준점 | 미발화 — 콘솔·앱 서버 미기동(§1) | 미측정 |
| P-4 | B. 큐 내용 | `DataPool/Sequences/<S>/<cueName>` (큐 노드축) | `Content` · `Values` · `Parts` · `TrigType` · `Name` | 본 프로브 | 위와 동일, 핸들 3축(시퀀스 · 큐 노드 · 큐 children) 순회 | 미발화 — 콘솔·앱 서버 미기동(§1) | 미측정 |
| P-5 | B. 큐 내용 | `DataPool/Sequences/<S>/<cueName>` | `Contentt` (날조) | 음성 대조 | 위와 동일 | 미발화 — 콘솔·앱 서버 미기동(§1) | 미측정 |
| P-6 | B. 큐 내용 | `DataPool/Sequences/<S>` (시퀀스 핸들) | `CurrentCue` | 양성 대조 | 위와 동일. 기지 GO — `cue_monitor.py:62` 라이브 확정본 | 미발화 — 콘솔·앱 서버 미기동(§1) | 미측정 |
| P-7 | C. 팬/틸트 현재값 | `Patch/Stages/1/Fixtures/<slot>` | `pan` · `tilt` · `Pan` · `Tilt` | 본 프로브 | 위와 동일 | 미발화 — 콘솔·앱 서버 미기동(§1) | 미측정 |
| P-8 | C. 팬/틸트 현재값 | `Patch/Stages/1/Fixtures/<slot>` | `pann` (날조) | 음성 대조 | 위와 동일 | 미발화 — 콘솔·앱 서버 미기동(§1) | 미측정 |
| P-9 | C. 팬/틸트 현재값 | `Patch/Stages/1/Fixtures/<slot>` (동일 슬롯) | `posx` | 양성 대조 | 위와 동일. 기지 GO — SPATIAL-001 실측 경로 | 미발화 — 콘솔·앱 서버 미기동(§1) | 미측정 |
| P-10 | D. 승계 확인 3건 | 문서 좌표(콘솔 무관) | 승계 앵커 3건 | 본 프로브 | `grep -n` 3건 — §3 표 참조 | 3건 전부 해소. GROUPGEN `progress.md:232` · footprint.py:6(+본문 8-12) · CUETIME `progress.md:16` | GO |
| P-11 | D. 승계 확인 3건 | 문서 좌표(콘솔 무관) | 날조 앵커 3건 | 음성 대조 | `grep -c "게이트 A — 멤버십은 읽을 수 있다"` · `grep -c "ASSUMPTION-99"` · `grep -c "CueOutFadeee"` | `0` · `0` · `0` — 전부 0. 검사에 판별력이 있다 | GO |
| P-12 | D. 승계 확인 3건 | 문서 좌표(콘솔 무관) | 실재 앵커 3건 | 양성 대조 | `grep -c "게이트 A — 멤버십은 읽을 수 없다"` · `grep -c "ASSUMPTION-27"` · `grep -c "CueInFade"` | `1` · `1` · `2` — 전부 1 이상. 검사 장치 생존 확인 | GO |

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

게이트 A · B · C가 `미측정`이므로 해당 처분 행(D-2 · D-5 · D-10 · D-12 · D-16)은
**측정 결과에 분기시켜** 설계된다(REQ-B16-002). 분기 문면은 `disposition.md`에 있다.

## 이력

| 일자 | 내용 |
|---|---|
| 2026-08-18 | M0 최초 작성. 콘솔 미접속 실측 → 게이트 A·B·C `미측정`, 게이트 D `GO`(3술어 재확인 + 대조군 2종). 좌표 정정 1건(session.py 3546-3555 → 3547-3557). 측정 주체 run-tjxy3n, base `15590e3`. |
