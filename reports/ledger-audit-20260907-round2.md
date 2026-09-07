# 장부 감사 2026-09-07 라운드 2 — picked 25건

측정 트리: main `cef0e58` (2026-09-07). 콘솔/실기 데스크는 오프라인 — 실기 확인이 필요한 판정은 UNDECIDABLE로 표기.

## 방법 요약

각 카드 본문에 적힌 커밋/PR 인용을 `git log --oneline --all`로 찾고, `git merge-base --is-ancestor <sha> HEAD`로 main 도달 여부를 실측했다. 25건 전부 커밋 메시지 제목이 카드 번호·주제와 정확히 일치했다(우연한 번호 일치가 아님을 커밋 subject 문면으로 확인). 카드가 "조사/판정 산출"을 약속한 경우(survey/audit) 산출물(verdict.md 등) 존재까지 확인했고, "고침"을 약속한 경우(fix/feat) 코드 diff가 실제로 merge됐는지 확인했다.

## 25행 표

| card | verdict | 한 줄 근거 | 증거(경로·명령·PR) |
|---|---|---|---|
| t96 | CLOSED | 응답기 버전·페이징 재측정 3연작이 전부 병합됐다(꼬리까지) | `git log --oneline` 0783368(#170)·03455b9(#172)·b3dd094(#183), 전부 `merge-base --is-ancestor <sha> HEAD` true |
| t100 | UNDECIDABLE | 카드 자신이 "카드 안 닫힘"이라 명시 — onPC 콘솔 미기동으로 발사 자체가 정지됨 | 커밋 `d0e7118`은 브랜치 `WT-universal-composite`에 존재하나 **main의 조상이 아님**(`merge-base --is-ancestor d0e7118 HEAD` false, PR 없음). 재개조건은 콘솔 가동 — 지금 데스크 오프라인이라 판정 불가 |
| t105 | CLOSED | "값은 있고 프로퍼티가 안 준다"를 138개 전수로 확정, survey PR 병합 | `a4f313b`(#185), ancestor 확인 |
| t116 | OPEN | A분류 17장 목표수준 재검토 카드 자체가 착수 흔적이 없다 | `git log --grep=t116` 0건, `.moai/reports/t116/` 부재, `find`로 확인. 이 라운드 감사가 사실상 t116이 요구한 일(전수 재확인)의 후속판이다 |
| t126 | CLOSED | 감독 문서→도구 매핑표 산출, survey PR 병합 | `5d31690`(#179), ancestor 확인, 산출물 `.moai/reports/t126/doc-tool-map.md` |
| t131 | CLOSED | 프리셋 풀 페이징 루프 구현, 실기 86/86 문구 포함 fix PR 병합 | `7d35a73`(#195), ancestor 확인 |
| t135 | CLOSED | 서베이(#191)+수정(#193) 두 커밋 모두 병합, 철자 불일치 3/3 확인 후 회귀 방지까지 완료 | `fa24d1b`(#191)·`5498415`(#193), 둘 다 ancestor |
| t136 | CLOSED(잔여 있음) | 장부 판정(M1~M3 정상·acceptance 부재는 결함) survey PR 병합 — 다만 **acceptance.md 생성 자체는 아직 안 됐다** | `d4c9d33`(#192) ancestor. `.moai/specs/SPEC-COPILOT-COLORPRESET-001/` 직접 `ls` → spec.md/plan.md/progress.md만 존재, acceptance.md 여전히 부재, `spec.md` frontmatter `status: draft` 그대로(2026-09-07 실측). 카드가 약속한 것은 "판정"이지 "닫기" 자체가 아니었다고 읽을 수 있으나 제목이 "장부 마감"이라 애매함 — 후속 카드(t159가 이 SPEC과 무관함을 확인)로도 실제 acceptance.md 신설은 안 잡힌다. 성공 판정은 survey 산출물 기준, 실제 SPEC 클로징은 감독 판단 필요 |
| t140 | CLOSED | 만료 문서 두 자리 갱신, docs PR 병합 | `c40401e`(#194) ancestor |
| t141 | CLOSED | 어휘 튜플 연결(트립와이어) 구현, feat PR 병합. 단 t154가 이 카드의 과장을 나중에 정정함 | `04f9238`(#201) ancestor. 정정: `748b9bf`(#202, t154) "내가 t141 에 넣은 과장을 걷는다" — t141 자체 작업은 병합됐고 문제는 해석 과장이었지 구현 결함 아님 |
| t142 | CLOSED | Focus/Frost 철자 오분류 확인·문서화, docs PR 병합 | `08edf8b`(#196) ancestor. 실제 정본 잠금 해제는 t149가 별도로 처리 |
| t144 | CLOSED | tier 계약 미충족 SPEC 전수 감사(카드가 안 2건 대비 실제 10건), audit PR 병합 | `aa2c63b`(#206) ancestor |
| t146 | CLOSED | spec.md 본문 두 자리(Prism/Frost 사유 분리) 갱신, docs PR 병합 | `af7125d`(#200) ancestor |
| t147 | CLOSED | 메모리 색인 바이트 상한 진단·정정, docs PR 병합 | `41aed8c`(#197) ancestor |
| t149 | CLOSED | PRESERVE 게이트 두 곳의 예외 기구 정리, audit PR 병합 | `d58f370`(#210) ancestor |
| t150 | CLOSED | fx 경로 프리셋 풀 페이징 적용, 뮤테이션 3/3, fix PR 병합 | `f47c5f5`(#198) ancestor |
| t151 | CLOSED | collect_rig_sections 페이징 적용, 뮤테이션 3/3, fix PR 병합 | `493d5a4`(#199) ancestor |
| t152 | CLOSED | 요청 섹션 집합 고정(10,505개 대상 회귀 방지), test PR 병합 | `9ddad77`(#212) ancestor |
| t153 | CLOSED | 보류 개수 표기 규약(클래스수 vs 배타행수) 확정, docs PR 병합 | `ac761f1`(#203) ancestor |
| t154 | CLOSED | t141의 과장 반증·정정, fix PR 병합("SPEC이 맞았다") | `748b9bf`(#202) ancestor |
| t155 | CLOSED | 시트 단위 번역가능/불가 축 설계 반영, feat PR 병합 | `5df9101`(#204) ancestor |
| t156 | CLOSED | 모델 지시에 클래스 합 성질 명시(페이로드 불변), feat PR 병합 | `a80a3dc`(#205) ancestor |
| t158 | CLOSED | PRESERVE 안전장치 인용 전수, "무게있는 자리 1건" 확정, audit PR 병합 | `3adb20a`(#207) ancestor |
| t159 | CLOSED | `moai spec audit` MUST-FIX 유일건(SyncStatusDrift) 조사, t144와 교집합 0 확정, audit PR 병합 | `ab18083`(#208) ancestor |
| t160 | CLOSED | 한국어 승인 문구 전수 재검색(어휘 아니라 인용형태가 원인), audit PR 병합 | `38e09b9`(#209) ancestor |

## 드롭 사유 (붙여넣기용, `]` 미포함)

```
t96 | 닫힘 확인 2026-09-07 main cef0e58 — survey 3연작 0783368·03455b9·b3dd094 전부 merge-base ancestor 확인, 재측정 결론은 1.6.1 그대로
t105 | 닫힘 확인 2026-09-07 main cef0e58 — PR #185(a4f313b) 138개 전수 판정 병합 확인
t126 | 닫힘 확인 2026-09-07 main cef0e58 — PR #179(5d31690) 매핑표 산출물 .moai/reports/t126/doc-tool-map.md 존재 확인
t131 | 닫힘 확인 2026-09-07 main cef0e58 — PR #195(7d35a73) 페이징 루프 구현 병합 확인
t135 | 닫힘 확인 2026-09-07 main cef0e58 — PR #191·#193(fa24d1b·5498415) 서베이+수정 둘 다 병합 확인
t136 | 닫힘 확인 2026-09-07 main cef0e58 — PR #192(d4c9d33) 장부 판정 산출 병합 확인. 잔여 acceptance.md 신설은 감독 판단 대상으로 별도 카드 필요
t140 | 닫힘 확인 2026-09-07 main cef0e58 — PR #194(c40401e) 문서 두 자리 갱신 병합 확인
t141 | 닫힘 확인 2026-09-07 main cef0e58 — PR #201(04f9238) 트립와이어 구현 병합 확인, 해석 과장은 t154가 정정
t142 | 닫힘 확인 2026-09-07 main cef0e58 — PR #196(08edf8b) 철자오분류 문서화 병합 확인, 정본 잠금 해제는 t149가 이어받음
t144 | 닫힘 확인 2026-09-07 main cef0e58 — PR #206(aa2c63b) tier 계약 전수 감사 병합 확인
t146 | 닫힘 확인 2026-09-07 main cef0e58 — PR #200(af7125d) spec.md 본문 갱신 병합 확인
t147 | 닫힘 확인 2026-09-07 main cef0e58 — PR #197(41aed8c) 색인 바이트 진단 병합 확인
t149 | 닫힘 확인 2026-09-07 main cef0e58 — PR #210(d58f370) PRESERVE 예외기구 정리 병합 확인
t150 | 닫힘 확인 2026-09-07 main cef0e58 — PR #198(f47c5f5) fx 경로 페이징 병합 확인, 뮤테이션 3/3
t151 | 닫힘 확인 2026-09-07 main cef0e58 — PR #199(493d5a4) collect_rig_sections 페이징 병합 확인, 뮤테이션 3/3
t152 | 닫힘 확인 2026-09-07 main cef0e58 — PR #212(9ddad77) 요청 섹션 집합 고정 병합 확인
t153 | 닫힘 확인 2026-09-07 main cef0e58 — PR #203(ac761f1) 보류 개수 표기 규약 병합 확인
t154 | 닫힘 확인 2026-09-07 main cef0e58 — PR #202(748b9bf) t141 과장 정정 병합 확인
t155 | 닫힘 확인 2026-09-07 main cef0e58 — PR #204(5df9101) 시트 단위 번역가능 축 반영 병합 확인
t156 | 닫힘 확인 2026-09-07 main cef0e58 — PR #205(a80a3dc) 모델 지시 갱신 병합 확인
t158 | 닫힘 확인 2026-09-07 main cef0e58 — PR #207(3adb20a) PRESERVE 인용 전수 병합 확인
t159 | 닫힘 확인 2026-09-07 main cef0e58 — PR #208(ab18083) spec audit MUST-FIX 조사 병합 확인
t160 | 닫힘 확인 2026-09-07 main cef0e58 — PR #209(38e09b9) 승인 문구 전수 재검색 병합 확인
```

t100·t116은 CLOSED 사유 없음 — 드롭 대상 아님(t100은 콘솔 재개 대기, t116은 미착수).

## Gaps(안 잰 것)

- 25건 중 23건을 커밋 subject·PR 번호·ancestor 여부까지만 확인했다. **각 커밋의 실제 diff 내용을 전부 읽지는 않았다** — 라운드 1의 "요약 재릴레이 금지" 원칙에서, 커밋 subject를 카드 판정 근거로 쓰는 것은 subject 자체가 이 저장소 관행상 "무엇을 쟀는지"를 정확히 요약하는 형태(예: "뮤테이션 3/3", "실기 86/86")를 취하고 있어 이번엔 subject를 신뢰 가능한 1차 신호로 다뤘다. 다만 t113 후속인 t116이 바로 "머지=완료가 아닐 수 있다"를 경고한 카드였다는 점에서, 이 판정도 **목표 수준 재검토는 아니다** — 커밋이 실제로 카드가 요구한 산출물을 만들었는지 diff까지 읽는 3차 라운드가 필요할 수 있다.
- t136의 "장부 마감" 판정이 가장 약하다: survey는 병합됐지만 실제 acceptance.md 생성·status 전이는 안 됐다. CLOSED로 적었으나 이건 "조사 완료"이지 "SPEC 장부 실제로 닫힘"은 아니다. 감독이 원했던 의미가 후자라면 이 행은 OPEN으로 재분류해야 한다.
- t141의 "닫힘"도 이중적이다 — t141 자체 구현은 병합됐지만 그 카드가 주장한 결함 해석이 나중(t154)에 과장으로 판명됐다. 구현물 자체는 남아있고 유효하므로 CLOSED로 유지했지만, 카드 텍스트 그대로를 "옳았다"로 읽으면 안 된다.
- t100 판정은 UNDECIDABLE이 맞다고 본다: 코드/테스트는 커밋됐지만 카드가 정의한 완료 조건(실기 프로브)이 明示적으로 "안 됨"이며 원인은 콘솔 미가동, 지금도 오프라인이라 해소 불가.
- t116은 OPEN으로 판정했으나, 이 라운드 감사 자체(25건 중 23건 CLOSED)가 사실상 t116이 요구한 작업의 일부를 대체 수행한 셈이다 — 그러나 t116이 지정한 대상(A분류 17장: t4 t41 t47 t48 t55 t56 t58 t60 t61 t64 t65 t66 t68 t82 t83 t85 t104)은 이번 스코프 밖이라 여전히 미착수다.
- 콘솔/실기 필요한 판정은 t100 하나뿐이었다(나머지 24건은 코드/문서 검토로 판정 가능했다).
