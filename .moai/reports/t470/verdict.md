# t470 판정서 — 생성기에 트래킹·MIB·페이저·포지션 위젯 (t466 후속 UI)

2026-09-27 · lane-3 · 브랜치 `WT-generator-widgets` · 계획 `plan.md` · 문장 출처 `.moai/reports/t466/verdict.md` §1

## 판정: PASS

t460 에서 파서가 몰라 뺐던 네 조작이 생성기에 붙었다. 산출물은 여전히 문장뿐이고, 서버 코드는 바꾸지 않았다(시험 파일 하나 제외).

## 무엇이 생겼나 (diff 기준)

| 조작 | 화면 | 보내는 문장 | 이전값 |
|------|------|-------------|--------|
| 트래킹 | 4택 버튼 Track·Block·Cue Only·Release | `큐 3 트래킹 Block으로 바꿔줘` | `section.tracking`, 없으면 `Track` |
| MIB | 4택 버튼 없음·dark·mark·live | `큐 3 MIB dark로 설정` | `section.mib_mode`(조립기의 참/거짓 `mib` 와 다른 칸), 없으면 `없음` |
| 페이저 | `바꾸기` 두 개 — 풀 1(딤머 페이저)·풀 4(컬러 페이저) | `큐 3 페이저 Breathe Soft로 바꿔줘` | `section.phaser` |
| 포지션 | 풀 2 팝업 선택 | `큐 3 포지션 2.11 Sweep L로 바꿔줘` | `section.position` |

- 포지션 행은 t460 에서 임시로 `무브먼트 <이름>` 문장을 냈다. 서버에 진짜 포지션 칸이 생겼으므로 `포지션 2.<번호> <이름>` 문장으로 바꿨다.
- 네 칸 모두 큐 전체 값이라 그룹을 싣지 않는다.
- `protocol.ts` `SongTimelineSection` 에 `tracking?`·`mib_mode?`·`phaser?`·`position_preset_no?`(추가만).

## 리뷰에서 고친 것 (`e591e894`)

MIB live 경고(REQ-093 (5))가 `movement` 변경에만 붙게 돼 있었다. 포지션 행이 `position` 문장을 내면서 이 경고가 화면에서 사라질 상태였다(구현 에이전트가 스스로 보고한 공백). 조건을 `movement || position` 으로 넓히고 시험을 더했다. 수정을 되돌리면 그 시험만 FAIL 하는 것을 확인했다.

## 검증

| 무엇 | 명령 | 결과 |
|------|------|------|
| 빌드 | `npm --prefix ui run build` | exit 0 (`build.txt`) |
| UI 시험 전량 | `npm --prefix ui test` | `30 files, 704 passed` (`vitest_full.txt`) |
| 어휘 잠금 + 파서 회귀 | `pytest test_plan_cue_generator_vocabulary_t460.py test_cue_sheet_edit_vocab_t466.py test_cue_sheet_edit.py test_cue_sheet_edit_group_scope_t461.py` | `132 passed` (`pytest_vocab.txt`) |
| 어휘 잠금 뮤테이션 | fixture 의 `Block` → `Blok` | pytest FAIL(`{'tracking': 'Blok'} != {'tracking': 'Block'}`), 복구 후 PASS — 구현 에이전트 관측 |
| main 합류 | `origin/main` bdd8902b(#514) 합류 뒤 위 세 개 재실행 | 위 값 |

어휘 잠금은 이제 9문장이다(t460 5 + t470 4). 같은 fixture 를 vitest(생성기 출력 대조)와 pytest(`parse_cue_sheet_edit_request` → 기대 `changes`)가 함께 읽는다.

## 안 잰 것 (Gaps)

1. 실제 브라우저에서 위젯을 눌러 보지 않았다(빌드·vitest 만).
2. 콘솔 반영: t466 이 네 칸의 콘솔 명령을 만들지 않았다 — 초안에만 남는다. 콘솔 전송은 이 카드 범위 밖이다.
3. 페이저 이름에 `.` 이 들어가면 서버 문장 정규식(`[^,.\n]+?`)이 끝을 자를 수 있다. 실제 풀 이름에서 확인하지 않았다.
4. 순차 전송 `useEffect` 타이밍 자동 시험 부재는 t460 과 같다.
