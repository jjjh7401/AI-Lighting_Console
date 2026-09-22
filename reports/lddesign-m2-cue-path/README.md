# 큐 경로 실측 — 감독 확정 경로는 색을 콘솔로 보내지 않는다

측정일 2026-09-22 · 트리 `.claude/worktrees/lddesign-m1` @ `c4eed85e`
(`origin/main` = `7a5432a7`, 동기화 `0 0`) · SPEC-LDDESIGN-001 M2 첫 단계.

## 재게 된 이유

plan.md §M2 가 "큐 경로 단일화"를 M0 에서 이관하며 **착수 전 실측할 것**으로
「두 경로가 같은 입력에 같은 결과를 내는지」를 지정했다. 그 전제가 맞는지부터
확인했고, **틀렸다**.

## 호출 전수 (시험 제외)

| 함수 | 모듈 | 호출 지점 |
|---|---|---|
| `compose_song_cue_bundle` | `server/design/song_cue_composer.py` (924행) | `session.py:8800`, `session.py:10764` |
| `build_songcue_bundle` | `server/looks/songcue.py` (3594행) | `tools.py:3230` |

두 경로는 서로 만나지 않는다. `tools.py` 전체에 `UnifiedSongLightingPlan`·
`compose_song_cue_bundle` 이 **0건**이고, `session.py` 는 `build_songcue_bundle`
을 **한 번도 부르지 않는다**.

두 경로 모두 콘솔 명령을 낸다 — 생성기가 다르다:

- 길 A: `session.py:8154 _reviewed_song_commands` → `spatial/mib.py:143 position_cue_bundle`
- 길 B: `looks/songcue.py:1075 build_songcue_bundle`

## 측정 — 양쪽 팔 대조군

같은 판별 토큰(`color|colour|cyan|amber|magenta|blue|red|white`)을 두 경로에
그대로 적용했다. 길 A 입력에는 구간마다 **서로 다른 색**을 넣었다 — 색이
실린다면 세 큐 블록이 달라져야 한다.

| | 길 A (감독 확정) | 길 B (코파일럿) |
|---|---|---|
| 명령 줄 수 | 22 | 29 |
| **색 관련 줄** | **0** | **5** (`ColorRGB_R/G/B`) |
| 대상 지정 | `Fixture 1 + 2 + 3 + 4` | `Group 15` / `Group 12` / … (역할 해석) |
| 위치 | `At Preset 2.4` (위치 프리셋) | `Pan/Tilt At Relative` + `Phase` + `Speed` |
| 줌 | 없음 | `Attribute 'Zoom' At 10` |
| 타임코드 | 포함 (`Store Timecode 9` 외 7줄) | 없음 (별도 `build_songcue_timing`) |
| 검사(lint)·MIB·재질의 | 있음 | 없음 |

재현: `probe_path_a.py` · `probe_path_b.py` (워크트리 루트에서
`.venv/bin/python <경로>`), 출력은 `path_a_output.txt` · `path_b_output.txt` (이 디렉터리).

### 길 A 가 낸 세 큐 블록 (발췌)

```
Fixture 1 + 2 + 3 + 4 ; At Preset 2.4
Fixture 1 + 2 + 3 + 4 ; Attribute 'Dimmer' At 70
Store Sequence 210 Cue 101 'Intro' CueFade 1.5
ClearAll
Fixture 1 + 2 + 3 + 4 ; At Preset 2.4
Fixture 1 + 2 + 3 + 4 ; Attribute 'Dimmer' At 90
Store Sequence 210 Cue 102 'Verse' CueFade 0.75
ClearAll
```

설계층은 색을 들고 있었다 — `CueColorData(palette=('blue','cyan'))` ·
`('amber','white')` · `('magenta','red')`. 세 블록이 **밝기와 페이드만** 다르다.

### 위치 프리셋이 색을 품을 가능성 — 배제됨

`POSITION_PRESET_POOL = 2`(`spatial/pointing.py:218`, grandMA3 Position 풀).
앱이 그 풀에 쓰는 값 라인은 `Attribute 'Dimmer'/'Pan'/'Tilt'` 뿐이다
(`pointing.py:350-352`). 색 속성이 없다.

## 결론

**감독이 화면에서 확정한 큐는 색 없이 콘솔로 나간다.** 색은 코파일럿 경로로만
나가고, 그 경로에는 감독의 검사·MIB·재질의가 하나도 걸려 있지 않다.

이 SPEC 이 만드는 컨셉 계층·컬러 규칙(M3)·팔레트는 지금 배선으로는 감독 확정
경로를 통해 무대에 닿지 못한다. M2 의 "큐 경로 단일화"가 M0 에서 앞당겨진
이유가 이것이다 — 합치기 전에는 그 위에 얹는 v2 7필드가 어느 쪽에도 온전히
닿지 않는다.

plan.md 가 적은 회귀 시험(「같은 입력에 같은 결과」)은 **쓸 수 없다**. 두 함수는
받는 것도 내는 것도 달라 비교 대상이 없다. 합치기는 "둘 중 하나 고르기"가 아니라
**길 B 의 명령 생성 앞에 길 A 의 설계·검사를 세우는 일**이다 — plan.md 의
「인터뷰가 입구, 대화가 엔진」이 이 뜻이다.

## 안 잰 것

- 두 경로가 **실기 콘솔**에서 어떻게 보이는지 — 콘솔 0회.
- 감독 확정 경로에 색이 빠진 것이 **언제부터인지**(git 이력 추적 안 함).
- 길 B 의 `Group` 지정과 길 A 의 `Fixture` 지정이 같은 기구를 가리키는지.
- 길 A 에 색을 붙이는 것과 길 B 에 검사를 붙이는 것 중 어느 쪽이 싼지.
