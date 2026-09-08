# 리드 직접 측정분 (2026-09-08, main 5a8c24e)

## ruff 부채 계열 — 유예 목록이 손대지 않은 채 그대로다
측정: `uv run ruff check .` → All checks passed! 인데, 그것은 **유예된 통과**다.
`pyproject.toml [tool.ruff.lint.per-file-ignores]` 에 11개 파일 × 규칙 = **85쌍**
(선언된 @MX:CEILING 값 85와 정확히 일치 — 하나도 줄지 않았다).
`[tool.ruff.format] exclude` 는 12개 파일.
규칙별 유예 파일 수: E501 11 · UP009 11 · UP031 9 · E401 8 · I001 8 · E402 6 ·
E701 6 · E702 5 · F401 4 · B007 4 · F403 4 · F405 4 · B905 2 · SIM300 1 · E741 1 · SIM115 1

- t63  SUPERSEDED-CANDIDATE — "570건이 ci-local 범위 밖" 중 「범위 밖」은 해소됨
       (t115 가 조용한 무검사를 밝은 유예로 바꿨다). 남은 실체는 85쌍이고 그것은
       t118~t121 이 소유한다. → t115 + t118~t121 에 흡수.
- t118 ALIVE — format exclude 12개 파일 그대로.
- t119 ALIVE — UP031 이 9개 파일에서 유예 중.
- t120 ALIVE — F405 가 4개 파일에서 유예 중.
- t121 ALIVE — E501(11) · E402(6) · B007(4) · B905(2) · E741(1) · SIM115(1) 전부 유예 중.
- t115 의 @MX:UPGRADE 가 "목록이 비면 이 절과 format exclude 를 통째로 지운다"
  라고 적혀 있다 → t118~t121 이 그 출구 조건의 이행 카드다. 넷 다 살아 있다.

## SPEC 장부 — 카드보다 나쁘다
측정: SPEC 54개 전수, spec.md frontmatter + acceptance.md/progress.md 존재 여부.

- status 필드가 아예 없는 SPEC **3개**: CUETIME-001 · RESTORE-001 · SONGSTD-001
  (RESTORE-001 은 **spec.md 자체가 없다** — 빈 SPEC 디렉터리)
- completed 인데 acceptance/progress 결손 **3개**: FXGEN-001 · IMGLAYOUT-001 · SPATIALMEM-001
- acceptance.md 없음 **6개**: COLORPRESET-001 · FXGEN-001 · IMGLAYOUT-001 ·
  PRESETGUARD-002 · RESTORE-001 · SPATIALMEM-001

- t264 ALIVE — 카드는 "completed 인데 progress.md 없음 **2**(FXGEN-001·IMGLAYOUT-001)"
       이라 적었으나 지금은 **3**이다(SPATIALMEM-001 추가). 카드 숫자가 낡았고,
       낡은 방향이 「더 나빠진」 쪽이다.
- t136 ALIVE — COLORPRESET-001 은 status `draft`, acceptance.md 없음. 카드 그대로.
- t143 SUPERSEDED-CANDIDATE — 대상과 완료 조건이 t136 과 같다(COLORPRESET-001
       acceptance.md 작성 + status 전이). 둘 중 하나로 합쳐야 한다.
- t117 부분 DEAD — "LXSEQ-002·003 을 draft 에서 in-progress 로" 중 **LXSEQ-003 은
       이미 in-progress** 다. 남은 것은 LXSEQ-002 하나뿐 → 카드 범위를 좁혀야 한다.
- t265 ALIVE — LXSEQ-003 은 `in-progress` 이고 완료 조건인 `implemented` 가 아니다.

## 어느 카드도 안 덮고 있는 것 (신규)
- SPEC 3개에 status 필드가 없다 → 어느 상태 감사도 이 셋을 세지 못한다.
- SPEC-COPILOT-RESTORE-001 은 디렉터리만 있고 spec.md 가 없다.
- `.moai/reports/` 118개 중 13개는 큐에 카드가 없다(t54 t57 t80 t86 t87 t93 t95
  t97 t98 t103 + 접미사 2 + 잘못 들어온 .png 1). 옛 `moai todo done` 이 카드를
  파괴한 흔적으로 보인다.
