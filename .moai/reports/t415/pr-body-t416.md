## 무엇 (card t416)
디코더가 **예외 없이** 중간에서 멈춘 곡을, 앱이 부분 오디오로 분석해 완전한 결과처럼 답하던 결함을 막는다.

- 원인 실측: `Let's Dance.mp3` 헤더 140.55초 · `soundfile.read` 90.98초 · libmpg123 `dequantization failed` (91초 지점). BytesIO 든 경로든 동일
- 처방: `soundfile.info().frames` 와 디코드 샘플 수를 대조, 98% 미만이면 두 길이를 적은 한국어 사유로 `AnalysisFailure`

## 검증
- 재현 테스트 RED 확인 후 GREEN (합성 mp3 의 데이터 바이트를 덮어 같은 모양을 만든다 — 실제 곡 미커밋)
- 대조군: 깨끗한 합성 mp3 는 계속 분석된다
- 실제 곡 9곡(`src/sample music/`, 커밋 안 함): Let's Dance 거절 · 7곡 정상 · LoveMe 기존 형식 오류 그대로(t413)
- 전체 스위트 → 12846 passed, 35 skipped (`test_director_*` 5파일 제외 — `jsonschema`/`rfc8785` 미선언, 기존 상태)
- `ruff check` 통과

## 미검증 · 잔여 위험
- 98% 문턱은 표본 9곡에서 오거절 0 이었을 뿐, VBR/패딩이 큰 파일에서 오거절이 없다는 보장은 아니다
- 거절만 한다 — 잘린 곡을 끝까지 읽는 복구는 하지 않았다
- 카드는 「10곡」이라 적었으나 실측 폴더에는 9개 파일이다
- CI 는 계정 결제 문제로 시작되지 않는다(#442 와 같음)

🗿 MoAI
