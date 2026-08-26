# t112 — 전달 래퍼가 대상 인자명을 무시한다: 오류 문면이 거짓말을 한다

- 카드: t112 (감사 C5 · t53 계열)
- 브랜치: `WT-honest-refusal` · 기준 `origin/main` **1cf831c**
- 범위: **정직한 거절**까지. 업로드 능력은 안 연다. t53 의 두-시트 운반 모양은 안 정한다.
- 실기: **0건** (콘솔은 sync 레인이 쓰는 중)

## 1. 주장

첨부 경로로 GROUP 시트를 올린 사용자가 받던 거절 사유가 **거짓**이었다.
「'group_content_base64'가 없다 — GROUP 시트 파일에서 읽은 바이트를 base64로 넘겨라」.
파일은 줬다. 없던 것은 파일이 아니라 **그 바이트가 실린 인자의 이름**이었다.

고친 뒤에는 참인 사유가 나온다 — 「'patch_content_base64'가 없다 — 그룹의 멤버 FID 는
패치 시트의 Group 라벨에서만 온다」. 이 경로는 **여전히 거절한다.** 고쳐진 것은 문면뿐이고,
카드가 말한 그대로 그게 값이다.

## 2. 증거

### 2.1 결함 재현 (수정 전)

    .venv/bin/python -m pytest server/tests/test_sheet_pipe_content_arg.py -q
    -> 11 failed, 2 passed in 0.88s

관측된 문면 (테스트 실패 출력 그대로):

    'group_content_base64'가 없다 — GROUP 시트 **파일**에서 읽은 바이트를 base64로
    넘겨라. 사용자가 채팅에 붙여넣은 본문으로 만들지 마라.

### 2.2 기전 — 잰 세 자리

| 자리 | 파일:행 (수정 전) | 관측 |
|---|---|---|
| 래퍼가 싣는 이름 | `server/orchestrator/tools.py:5173` | `forwarded["file_content_base64"] = content` — 리터럴 |
| 대상이 읽는 이름 | `server/orchestrator/tools.py:4633` | `call.arguments.get("group_content_base64")` |
| 스키마 required | `server/orchestrator/tools.py:10107` | `group_content_base64` · `patch_content_base64` |

같은 파일의 `@MX:WARN`(5108)이 대상 **툴 이름**에 대해 이미 「리터럴 금지」를 못박아 뒀다.
그 규율이 **인자 이름**에는 안 걸려 있었다 — 같은 결함 계열의 안 덮인 절반이다.

### 2.3 수정 (3자리)

| 파일 | 무엇 |
|---|---|
| `server/sheets/registry.py` | `SheetKindRow.content_arg` 추가 · 기본값은 예전 이름 `file_content_base64` |
| `server/sheets/registry.py` | `GROUP_ROW.content_arg = "group_content_base64"` |
| `server/orchestrator/tools.py` | `forwarded[row.content_arg] = content` + `@MX:WARN` 을 인자명까지 확장 |

### 2.4 검사 (수정 후)

    .venv/bin/python -m pytest server/tests/test_sheet_pipe_content_arg.py -q
    -> 13 passed in 0.21s

    .venv/bin/python -m pytest -q
    -> 10430 passed, 12 skipped, 1 warning in 157.66s

    make lint
    -> 종료코드 0 (출력 없음)

    ruff format --check (수정 3파일)
    -> 3 files already formatted

## 3. 뮤테이션 — 6/6 KILLED

복원은 백업 + sha256 대조다(`git checkout` 안 쓴다 — 미커밋분이 날아간다).
매 회 **치환이 실제로 적용됐는지** 먼저 단언해 「생존」과 「적용 안 됨」을 안 헷갈렸다.

| # | 뮤테이션 | 판정 |
|---|---|---|
| 1 | 래퍼를 `forwarded["file_content_base64"]` 로 되돌린다 | KILLED |
| 2 | `GROUP_ROW.content_arg` 를 옛 이름으로 되돌린다 | KILLED |
| 3 | 거절 문면에서 FID 매핑원 문장을 지운다 | KILLED |
| 4 | `SheetKindRow` 기본값을 `group_content_base64` 로 뒤집는다 | KILLED |
| 5 | 래퍼가 옛 이름으로도 **함께** 싣는다 | KILLED |
| 6 | `GROUP_ROW.content_arg` 를 빈 문자열로 비운다 | KILLED |

두 축이 따로 죽는다는 것이 요점이다 — 1·5 는 **전달 인자명**, 3 은 **거절 문면**.
4·6 은 경계(기본값·퇴화값)이고, 2 는 카드가 지목한 바로 그 자리다.

## 4. 계열 — 점-수정이 아니다

`TestRowContentArgMatchesTargetSchema` 는 레지스트리의 **tool 종 행 전수**를 돌며
「행이 지목한 인자명이 대상 스키마의 required 에 들어 있는가」를 묻는다. 오늘 도는 행은 5개
(patch · group · preset-dim · preset-col · preset-bm)이고, 5개 미만이면 계수 단언이 빨개진다.
나중에 인자명이 갈리는 행이 또 생기면 그 행이 이 검사를 지날 때 걸린다.

대조군도 함께 둔다 — group 을 뺀 4행은 여전히 `file_content_base64` 여야 한다.
전부 새 이름으로 바꿔 놓고 초록을 받는 길을 막는다.

## 5. 미검증 (gap)

- **실기 0건.** 실제 앱에서 파일을 첨부해 이 문면이 화면에 뜨는 것은 안 봤다. 잰 것은
  래퍼→대상 배선과 그 결과 문면까지다.
- **`registry.py` GROUP_ROW 주석의 전제가 이제야 참이 됐다.** 주석은 「첨부 경로로 부르면
  그룹 시트만 도착하고 FID 매핑원이 없어 툴이 명시적으로 거절한다」고 적어 뒀는데, 오늘까지
  코드는 그보다 앞에서 「파일이 없다」로 거절했다. 주석 문면은 안 고쳤다 — 이제 맞아서다.
- **`vectorworks` 행은 이 검사 밖이다.** `session_method` 종이라 래퍼가 `no_target_tool` 로
  거절한다. 그 거절이 옳은지는 이 카드가 안 물었다.
- **`import_uploaded_sheet` 의 `@MX:DEBT`(action 생략 호출)는 그대로다.** t53 소관이다.

## 6. 잔여 위험

- 이 수정은 **업로드 경로를 안 연다.** 그룹 시트만으로는 여전히 못 만든다. 「고쳤다」를
  「이제 첨부로 그룹이 만들어진다」로 읽으면 틀린다.
- `content_arg` 는 문자열이라 대상 스키마와의 정합은 **검사가** 지킨다. 검사를 지우면
  다음 행에서 같은 비대칭이 조용히 돌아온다.
