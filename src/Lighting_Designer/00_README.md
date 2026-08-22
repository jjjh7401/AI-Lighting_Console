# Lighting_Designer — LX-SEQ 프로젝트 아카이브

grandMA3 조명연출 시퀀스 포맷(LX-SEQ) 프로젝트의 전체 산출물. 2026-08-21 기준 최신 리비전.

## 폴더 구성

| 폴더 | 내용 |
|---|---|
| `01_스펙/` | LX-SEQ 포맷 명세서 v2.1 (모든 문서의 규격 정본) + 프로젝트 작업지침 |
| `02_RIG팩/` | 쇼 단위 콘솔 기본설정 r3 — 장비 86대·패치(U1–U5)·그룹 18·프리셋 35·FX 8·콘솔 설정 |
| `03_곡파일_Sugar/` | Maroon 5 "Sugar" r3 — 큐시트 6시트 XLSX·CUE-EX CSV·타임라인 HTML |
| `04_grandMA3/` | 콘솔 반영 — 명령 스크립트 452줄·매크로 XML·프로그래밍 런북 |
| `05_문서인덱스/` | 전 문서 관계 맵 (브라우저로 열기) |
| `90_빌드파이프라인/` | 데이터 3 + 생성기 5 + 검증기 3 (Python) — 데이터만 고치면 전 산출물 재생성 |
| `99_플러그인/` | lighting-designer 플러그인 v0.1.1 설치 파일 |

## 문서 체계 (정본은 항상 아래쪽)

스펙 → RIG 팩 → 곡 파일 → 콘솔 산출물. 아래 레이어를 고치면 위가 자동 재생성된다.

## 상태

- 검증 28/28 PASS (곡 15 · RIG 8 · MA3 5)
- `TC_METHOD: DERIVED` — 리허설 LTC 대조 후 VERIFIED 승격 필요
- 장비 `PROPOSED` — 보유/대여 리스트 확정 필요
- 미확정: POS 현장 레코드 8건 · BLIND 각도 · 영상팀 큐(LW-02~06) · 콘솔 버전([VERIFY] 3건)

## 재생성 방법

`90_빌드파이프라인/`에서 `seq_data.py`(곡)·`exec_data.py`(실행)·`rig_data.py`(장비)만 수정 후:
`make_xlsx → make_exec → make_timeline → make_rig → make_ma3 → validate 3종` 순서로 실행.
또는 Cowork에서 lighting-designer 플러그인에게 요청.
