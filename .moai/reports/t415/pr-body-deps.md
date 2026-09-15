## 무엇
`cde2744`(SPEC-LDSTORE-001)가 `server/director` 와 `test_director_*` 5파일을 main 에 넣었지만, 그 코드가 import 하는 `jsonschema[format-nongpl]>=4.23` · `rfc8785>=0.1.4` 선언은 커밋되지 않았다. main 기준 CI 가 수집 단계에서 `ModuleNotFoundError` 5건으로 멈춘다 — PR #442·#443 CI 로그에서 실측.

- `pyproject.toml` 에 두 줄(+설명 주석) · `uv lock` 갱신
- 선언 문구는 main 체크아웃에 미커밋으로 남아 있던 수정과 **같은 내용** — 그 세션이 나중에 커밋해도 충돌이 적게 맞췄다

## 검증
- `uv lock --check` → Resolved 100 packages
- `pytest test_director_*` 5파일 → 129 passed
- 전체 스위트는 이 PR 의 CI 로 확인

## 순서
이 PR 이 먼저 머지돼야 #442·#443 의 CI 가 초록이 될 수 있다.

🗿 MoAI
