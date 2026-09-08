### t145 — ALIVE

claim: `moai spec audit` 총계 셋(디렉터리/findings distinct-id/total_specs/grandfathered+modern_era_clean)이 서로 안 맞는다. 2026-08-30 실측(디렉터리45=findings45, total_specs44, 합43)과 같은 구조의 불일치가 현재 커밋에도 존재하는지.

ran:
```
moai spec audit --json > /tmp/triage/audit02c.json
find .moai/specs -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort > /tmp/triage/dirs.txt; wc -l /tmp/triage/dirs.txt
python3 -c "import json; d=json.load(open('/tmp/triage/audit02c.json')); print(len(d['drift_findings']), len(set(f['spec_id'] for f in d['drift_findings'])), d['total_specs'], d['grandfathered'], d['modern_era_clean'])"
comm -23 /tmp/triage/dirs.txt /tmp/triage/findingids.txt; comm -13 /tmp/triage/dirs.txt /tmp/triage/findingids.txt
```

saw: 디렉터리 개수 = 54. `drift_findings` 배열의 distinct `spec_id` = 54 (comm 양방향 0 — 완전 일치). `total_specs` = 53 (디렉터리보다 1 적음). `grandfathered`(35) + `modern_era_clean`(17) = 52 (디렉터리보다 2 적음, total_specs보다 1 적음). JSON 필드명은 카드가 가정한 `findings`가 아니라 `drift_findings`였다(그리고 개별 항목의 `era` 필드는 이진 grandfathered/modern 이 아니라 `V2.x`/`V3R2-R4`/`V3R5`/`V3R6`/빈문자열 다섯 값이며, 9개 SPEC은 findings 안에서 era 값이 여러 개 섞여 있다 — grandfathered/modern_era_clean 분류가 이 JSON의 findings 배열만으로는 역산되지 않는다).

so: 카드가 2026-08-30에 관측한 "세 계수가 서로 다르다"는 구조적 불일치는 2026-09-08 현재도 그대로 존재한다(수치는 45/44/43 → 54/53/52로 성장했을 뿐, 디렉터리와 findings-distinct-id가 일치하고 total_specs·grandfathered+modern_era_clean 은 각각 적다는 패턴은 동일). 카드의 세 가지 물음(총계 44/53이 빼는 1건이 무엇인지, 미분류 2건이 무엇인지, 어느 값을 인용해야 하는지)은 이 JSON 산출물만으로는 답이 안 나온다 — grandfathered/modern_era_clean 판정 로직이 findings 배열 밖(moai 바이너리 내부)에 있다.

gap: UNMEASURED — 어느 SPEC이 total_specs 53에서 빠졌는지, 어느 2건이 grandfathered/modern_era_clean 어느 쪽에도 안 들어갔는지는 `moai` CLI 소스(Go, 이 저장소 밖) 없이는 못 잰다. 필요한 다음 명령: moai 소스 저장소에서 grandfathered/modern_era_clean 판정 함수를 읽거나, `moai spec audit --json` 에 SPEC별 분류 필드를 얹는 verbose 옵션이 있는지 `moai spec audit --help` 로 확인.
