# LX-SEQ 문서 대비 앱 반영도 — 적용 구분표

측정 2026-08-31 · 대상 `src/Lighting_Designer/` + 스펙 v2.1 · 작업지침 · 문서인덱스
판정 기준: 문서가 정의한 개념이 **콘솔에 실제로 닿는가**

## 오늘 도달 지점

| 층 | 결과 | 증거 |
|---|---|---|
| 1 패치 | 86/86 | `already_patched 86` |
| 2 그룹 | 18 | `group_slots_resolved 18` |
| 3 프리셋 | Color 7 · FX 2 | 풀4 1→7 · 풀21 0→2 |
| 4 큐 | 18/18 | `Sequences 1→2` · Q010~Q180 되읽기 |
| LED-W 유출 | 0건 | `no_command_emitted true` |

## A. 바로 적용

- **A1 기본 프리셋 일괄 입구** — 감독 지시. 지금은 시트마다 따로 발사. 앱에 `import_lxseq_presets`·`lxseq_presets_e2e.py`·`compose_fx`·`lxseq_fx_e2e.py`·`_PRESET_POOL_FAMILY`·`PRESET_ID_PREFIXES` 이미 있음. 빠진 건 입구 하나. 감독 결정: 되는 것부터 전부(DIM·COL·FX), BM·POS 는 사유와 함께 보고만.
- **A2 POS 를 RIG 팩에서 읽기** — 감독이 `preset-pos.csv` 에 Pan/Tilt 값 열 추가. 현재 `preset-pos` 는 시트 종류로 미등록(`PRESET_ID_PREFIXES` 에 dim·col·bm 셋뿐). 열리면 held 30→18.
- **A3 큐 라벨 정본 형식** — 지금 `"Q010"`, 정본 `"Q010 INTRO 화사"`. 곡 파일 `CUE` 시트를 읽으면 닫힘.
- **A4 TC_METHOD 경고** — 스펙이 `DERIVED` 를 「실행 확정본으로 취급하지 않는다」로 규정. 앱은 모르고 씀. `HEAD` 한 줄. 안전 조항.

## B. 다음 단계 (측정 먼저)

- **B1 개별 타이밍 I/P/C/B** — 스펙 §8-3 「콘솔급 큐의 본질」. 지금 `CueFade` 근사 하나. 조명감독 파이프라인도 `make_ma3.py:170` 에서 `[MANUAL]`. 질문: MA3 가 그룹별 Fade·Delay 를 명령줄로 받는가. 받으면 자동화, 안 받으면 원리적 한계 확정 후 「사람이 넣을 표」 방향. 어느 쪽이든 이김.
- **B2 안전 규칙 fail-closed** — 스펙 §13-4 HARD 인데 `grep inhibit` 0 · `grep MIB` 0. 문서인덱스 「BLIND 각도 — 객석 직사 금지선」 미확정. 최소안: STROBE·BLIND 큐 발사 시 Inhibit 배치 확인, 없으면 거절.
- **B3 검증 15항목** — 현재 4/15. 앱이 시트를 읽으면 1·3·5·6·8 은 기계가 도는 게 맞음. `--validate` 모드.
- **B4 BM 5건 속성 어휘** — 전량 보류(`attribute_probe_rejected` 3 · `family_out_of_scope` 3). 값이 아니라 어휘 문제. `server/looks/schema.py` 정본.
- **B5 Layer 3 분기 기록** — 문서는 데이터→`ma3.txt`→사람. 앱은 데이터→OSC 직접. 같은 목적지 다른 길인데 미기록. 문서인덱스는 `r2` 기준, 실물은 `r3`.

## C. 반영하면 안 되는 것

- **C1 POS 자동 계산** — 스펙 §8-1 「Pan/Tilt 절대값은 시트에 쓰지 않는다」. 감독이 RIG 팩에 넣는 것(A2)과 앱이 지어내는 것은 다름.
- **C2 FX.04(Hue)·FX.06(Shutter) 강행** — `KNOWN_ATTRIBUTES` 밖, `loader.py:119` 거절. FX.04 없이도 18큐 섬.
- **C3 예약 행 미리 생성** — `registry.py:359` + `test_registry_has_no_row_reserved_for_a_later_spec`. 오늘 실제로 걸림.
- **C4 검사 무력화로 통과** — C3 우회하면 다음 진짜 예약 행을 아무도 못 잡음.
- **C5 큰따옴표 복귀** — `ma3.txt` 는 사람이 붙여넣는 스크립트. 전송 경로는 `'` 만(`protocol.py:127`). 오늘 이것으로 발화 1회 실패.

## 오늘 막았던 벽 셋 — 전부 저장소에 답이 있었음

| 벽 | 답이 있던 곳 |
|---|---|
| 계획 0건 | RIG 팩 `fx.csv` (아무도 안 씀) |
| 발화 실패 | `ma3.txt:232` `Store Sequence` |
| 명령 거절 | `protocol.py:127` 주석 |

## 안 잰 것

- 개별 타이밍이 명령으로 가능한지 (B1 이 그 측정)
- BM 속성 어휘의 정확한 경계
- `ma3.txt` 와 우리 빌더가 이미 갈라졌는지
- CI 결제 정지 — PR 5건 + `WT-cue-integrate` 미머지
