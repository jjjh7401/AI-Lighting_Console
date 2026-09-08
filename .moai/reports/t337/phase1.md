# t337 국면 1 — ruff format 적용, 유예 85쌍 → 70쌍

측정 트리: `.claude/worktrees/t337` · 기준 커밋 `3a84cce` · 일자 2026-09-08

## 1. 주장

- 11개 파이프라인 파일에 `ruff format` 을 적용했고 **산출물 13개가 안 바뀌었다**.
- `[tool.ruff.lint.per-file-ignores]` 의 (파일, 규칙) 쌍이 **85 → 70**.
- `[tool.ruff.format].exclude` 에서 파이프라인 11줄을 지웠다(PRESERVE 핀 `server/web/preview.py` 는 유지).
- `_PAIR_CEILING` 을 85 → 70 으로 같이 낮췄다.

## 2. 증거

### 2.1 전수 위반 — 카드가 미검증으로 남긴 자리

카드는 4개 파일 부분표본만 갖고 있었다. 11개 전수를 유예 무시로 처음 쟀다.

```
$ uv run ruff check "src/Lighting_Designer/90_빌드파이프라인/" --no-cache \
    --config 'lint.per-file-ignores={}' --statistics
```

| 규칙 | 국면 1 전 | 국면 1 후 |
|---|---|---|
| E501 | 234 | 35 |
| UP031 | 110 | 110 |
| E702 | 55 | **0** |
| F405 | 49 | 49 |
| E701 | 27 | **0** |
| E402 | 19 | 19 |
| I001 | 17 | 16 |
| UP009 | 11 | 11 |
| B007 | 9 | 9 |
| E401 | 9 | 9 |
| E741 | 6 | 6 |
| B905 | 5 | 5 |
| F401 | 4 | 4 |
| F403 | 4 | 4 |
| SIM115 | 1 | 1 |
| SIM300 | 1 | 1 |
| **합** | **561** | **279** |

포맷이 녹인 것은 E701(27) · E702(55) 전량과 E501 199건, I001 1건. 나머지 규칙은 손대지 않았다.

### 2.2 산출물 대조 (핵심 AC)

`.moai/state/verify/t337/run.sh` 가 생산 스크립트 5개를 지정 디렉터리로 돌린다.
실행 순서 정정: `make_exec.py` 는 `make_xlsx.py` 산출 `.xlsx` 를 입력으로 먹으므로
뒤에 온다(첫 시도에서 exit=1 로 드러났다).

최종 대조 — `.moai/state/verify/t337/final-cmp.txt`, 13/13 SAME, DIFF 0건.

## 3. 계기 무결성 — 양팔 검증

이 카드의 AC 는 「바이트 비교」인데, **13개 중 2개는 원리적으로 바이트 비교가 불가능**하다.

- 아무것도 안 바꾸고 두 번 돌리면 `.xlsx` 2개가 다르다(대조군 실측).
- 차이는 zip 멤버 `docProps/core.xml` — 생성 시각. 실제로 다른 멤버는 `docProps/core.xml` 하나뿐임을 압축 해제 후 `diff -rq` 로 확인.
- 그래서 `cmp.sh` 는 비-xlsx 11개는 바이트 비교, xlsx 2개는 `core.xml` 만 제외한 멤버 내용 비교를 한다.

계기가 **다른 것을 잡아내는지**도 쐈다(구멍 쪽 팔):

| 뮤테이션 | 계기 응답 |
|---|---|
| 변경 없이 재실행 | 13/13 SAME (거짓양성 0) |
| `patch.csv` 에 1바이트 추가 | DIFF(바이트) 검출 |
| xlsx 안 `sheet1.xml` 에 주석 삽입 | DIFF(내용) 검출 |

즉 이 SAME 은 「못 재서 조용한」 SAME 이 아니다.

## 4. 게이트 검사 변경 — 전제가 뒤집혔다

`test_the_format_exclusion_matches_the_same_files` 가 「린트 유예 집합 == 포맷 제외
집합」을 못박고 있었고, 국면 1 이 그 대칭을 깼다(포맷은 끝, 린트 유예 70쌍 잔존).
검사를 방향을 뒤집어 다시 썼다:

- `test_no_pipeline_file_is_format_excluded` — 파이프라인 파일이 포맷 제외로 **되돌아오면** 빨개진다.
- `test_the_pipeline_is_formatted` — 위 검사가 공허해지지 않게 하는 짝. 제외만 지우고 포맷을 안 하면 위는 통과하는데 파일은 안 포맷된 상태다. `ruff format --check` 로 실물을 잰다.

두 검사 모두 뮤테이션으로 확인:

| 뮤테이션 | 결과 |
|---|---|
| `rig_data.py` 에 `x   =  1` 추가 | `test_the_pipeline_is_formatted` FAIL |
| `rig_data.py` 를 포맷 제외로 되돌림 | `test_no_pipeline_file_is_format_excluded` FAIL |

## 5. 미검증 (Gaps)

- **국면 2~4 는 손대지 않았다.** UP031 110 · F405 49 · E402 19 · I001 16 · UP009 11 · B007 9 · E401 9 · E741 6 · B905 5 · F401 4 · F403 4 · SIM115 1 · SIM300 1 = 279건이 그대로 남아 있고, 유예 70쌍이 그것을 덮고 있다.
- **산출물 커버리지의 한계.** 대조한 것은 이 저장소가 기본 입력으로 생산하는 13개다. 다른 입력(다른 쇼·다른 곡)으로 갈릴 경로는 안 쟀다. 「이 입력에 대해 안 바뀌었다」가 잰 것의 전부다.
- **`packaging/rust_scan.py` · `packaging/verify_packaged_e2e.py` 2개가 포맷 미적용**이다. 이건 이 변경 전부터 그랬음을 `git show HEAD:` 로 확인했고(별건), 이 카드 범위 밖이다.

## 6. 잔여 위험

- E501 잔여 35건은 포맷으로 안 녹는 긴 줄이라 국면 4 에서 줄을 끊어야 하고, 그건 포맷 변경이 아니라 사람 판단이다.
- 유예 목록을 실측으로 다시 쓸 때 규칙 하나를 실수로 빠뜨리면 `ruff check .` 가 즉시 빨개지므로 그 방향은 조용히 틀릴 수 없다. 반대로 **필요 없는 규칙을 남기는** 실수는 조용하다 — 70쌍이 전부 실제 위반에 대응한다는 것은 `--config 'lint.per-file-ignores={}'` 전수 출력에서 파일별로 뽑은 값이라는 점으로만 지탱된다.
