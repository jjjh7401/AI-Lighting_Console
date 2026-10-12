# t491 1단계 판정서 — 곡 사이 룩 재사용 실측

- 카드: t491 (1단계, 측정만, 구현 없음)
- 트리: `.claude/worktrees/t491`, 브랜치 `WT-look-reuse-census`, 기준 `f0b0071d` (= origin/main, 2026-10-12 측정)
- 콘솔 접촉: 0건. in-process 가짜 콘솔만 썼다(t501 하네스 계열).
- 시험 쇼 값(색 이름·프리셋 이름)의 의미는 해석하지 않는다. 같은지 다른지만 센다.

## 1. 결론

**지금 조립기에는 곡 사이 기억이 없다. 그래서 감독이 곡마다 같은 인터뷰 답을 주면 이웃한 두 곡은 언제나 같은 룩으로 열린다.**

- 인터뷰 답이 같을 때: 이웃 쌍 **7/7** 이 같은 첫 큐 룩으로 열렸다. 다음 곡의 구간 큐 99개 중 **67개(68%)** 가 앞 곡에서 이미 쓴 룩이다.
- 컨셉 답만 곡마다 바꾸면: 이웃 쌍 **0/7**, 재사용 큐 **0/99**.
- 한 세션에서 연달아 돌린 결과와 곡마다 새 세션에서 돌린 결과는 8곡 모두 큐 단위로 **바이트 동일**했다(두 답 세트 모두 8/8). 앞 곡이 뒤 곡의 선택을 바꾸는 장치가 없다는 실측이다. t486 §3 의 「장치가 없다」를 코드 판독이 아니라 실행 결과로 확인했다.

룩을 정하는 것은 곡이 아니라 **인터뷰 답(컨셉)** 이다. 컨셉을 돌린 실행에서 첫 큐가 같았던 쌍은 전체 28쌍 중 7쌍이고, 7쌍 모두 같은 컨셉끼리의 쌍이다(어긋남 0건, `examples.stdout.txt`).

## 2. 측정 방법

| 항목 | 내용 |
|---|---|
| 경로 | `ChatSession.run_instruction` → `_song_compose` → `_build_unified_song_plan` → `compose_song_cue_bundle`. 대화 길 끝까지 실제 코드로 돌렸다 |
| 곡 | `.moai/reports/t499/runs/*/analysis.json` 8곡(DSP 실측 BPM·구간을 재생, `Rain_first` 는 Rain 중복이라 뺐다). 순서는 이름순 |
| 하네스 | t501 `measure_ac001_8songs.rehearse` 의 부품 + `measure_m7_8songs` 의 읽기 전용 실기 증거 패치(능력 판독·페이저 풀). 두 파일은 고치지 않았다 |
| 룩(큐 하나) | `(position.stored, color.palette)` — 위치 프리셋 + 색 조합. 보조로 효과(`fx.permitted`)까지 넣은 정의도 셌다 |
| 세는 큐 | 구간 큐(`kind == "section"`)만. MIB 사전이동·절정 복귀는 파생 큐라 뺐다 |
| 실행 4가지 | 답 세트 2개(`fixed` = t501 답 그대로 8곡 동일 / `rotated` = 컨셉 답만 카드가 내민 선택지 k%3 번째로 돌림) × 세션 2개(`same_session` = 한 세션에서 연달아 / `fresh` = 곡마다 새 세션) |
| 시퀀스 번호 | 같은 세션의 곡끼리 번호가 부딪치지 않게 곡마다 `시퀀스 211+k`, `타임코드 11+k` 로 비웠다(번호 충돌은 이 측정의 질문이 아니다) |

## 3. 숫자

이웃 쌍 = 이름순으로 붙은 7쌍. 전체 쌍 = 8곡에서 나올 수 있는 28쌍(공연 순서가 바뀌어도 성립하는 값).

| 실행 | 쌍 | 첫 큐 룩 같음 | 다음 곡 큐 중 앞 곡 룩 재사용 | 룩을 하나라도 공유한 쌍 | 룩 집합 완전 동일 |
|---|---|---|---|---|---|
| fixed · 이웃 | 7 | **7** | **67/99 (68%)** | 7 | 0 |
| fixed · 이웃 (효과 포함) | 7 | 7 | 19/99 (19%) | 7 | 0 |
| fixed · 전체 쌍 | 28 | 28 | 253/405 (62%) | 28 | 0 |
| rotated · 이웃 | 7 | 0 | 0/99 | 0 | 0 |
| rotated · 전체 쌍 | 28 | 7 | 52/405 (13%) | 7 | 0 |

`same_session` 과 `fresh` 는 네 줄 모두 숫자가 같다(위 표는 `same_session` 값). 원자료는 `look_reuse.json`.

**효과를 넣으면 재사용이 68% → 19% 로 내려가는 이유:** 같은 위치·색인 큐끼리 효과 허용 목록이 다르다는 것까지만 숫자로 보인다. 왜 다른지는 재지 않았다(§5).

## 4. 예시 (fixed, 같은 세션)

곡마다 첫 큐 룩 — 8곡 전부 `('Ring In', ('블루', 'cyan'))` 로 같다.

| 곡 | 구간 큐 | 서로 다른 룩 |
|---|---|---|
| Club Diver | 13 | 11 |
| Cut and Run | 17 | 14 |
| Ice cream | 7 | 7 |
| Morning | 13 | 11 |
| Rain | 12 | 10 |
| Too Cool | 23 | 14 |
| scott-buckley-neon | 17 | 14 |
| 걸그룹DinoDino_C_max최고품질 | 10 | 9 |

8곡 전체를 합쳐 서로 다른 룩은 **23개** 뿐이다.

이웃 쌍별 재사용:

| 앞 곡 → 다음 곡 | 다음 곡 큐 중 재사용 | 공유한 서로 다른 룩 |
|---|---|---|
| Club Diver → Cut and Run | 13/17 | 10 |
| Cut and Run → Ice cream | 4/7 | 4 |
| Ice cream → Morning | 6/13 | 5 |
| Morning → Rain | 11/12 | 9 |
| Rain → Too Cool | 15/23 | 9 |
| Too Cool → scott-buckley-neon | 11/17 | 9 |
| scott-buckley-neon → 걸그룹DinoDino | 7/10 | 6 |

Club Diver → Cut and Run 처음 6큐: Intro `Ring In/블루+cyan`, Chorus 1 `Ring In/블루+warm white`, Chorus 2 `Home/블루+warm white`, Chorus 3 `Home/블루+warm white`, Chorus 4 `Vocal DSC/블루+warm white` 는 앞 곡에 있던 룩이다. 새 룩은 Verse 1 `Vocal DSC/블루+cyan` 하나다.

컨셉을 돌린 실행(rotated)의 첫 큐: 우주 → `Ring In/블루+cyan`, 네온 → `Cross/마젠타+cyan`, 빈티지 → `Wall/웜화이트+cyan`. 같은 컨셉을 받은 곡끼리는 첫 큐가 같다.

## 5. 안 잰 것

- **실제 음원 DSP 경로는 안 돌렸다.** t499 가 커밋한 analysis.json(DSP 실측 BPM·구간)을 재생했다. 구간 경계·D 레벨이 DSP 를 다시 돌렸을 때와 같다는 전제는 t501 M3 머리말의 판단을 따랐을 뿐, 이 카드에서 다시 재지 않았다.
- **실제 감독의 답이 곡마다 같은지는 모른다.** `fixed` 는 「모든 곡에 같은 답」, `rotated` 는 「컨셉만 기계적으로 돌림」이다. 둘 다 사람의 실제 운용이 아니다. 실제 쇼에서 감독이 곡마다 컨셉을 바꾸는 비율은 재지 않았다.
- **답 세트는 컨셉(Q1)과 그 이름이 박힌 두 답만 돌렸다.** 팔레트 운용(Q2B)·클라이맥스 위치·전환 방식 같은 다른 답은 고정했다.
- **효과 차이의 원인은 안 쟀다**(§3).
- **룩 정의는 위치 + 색 두 축이다.** 디머 값·페이드·액센트는 룩에 넣지 않았다. 넣으면 재사용 비율은 내려갈 수 있다.
- 곡 8개는 저장소에 있는 전부(t499)이지 표본 설계가 아니다.

## 6. 감독에게 물을 근거

- 같은 답을 주면 연속 두 곡이 같은 룩으로 열린다(7/7). 다음 곡 큐의 2/3 가 앞 곡 룩이다.
- 컨셉을 바꾸면 겹치지 않는다(0/7). 지금은 **감독의 답이 곡 사이 다양성을 만드는 유일한 손잡이**다.
- 그래서 물을 것: 「같은 답을 준 연속 곡도 조립기가 스스로 다른 룩으로 열어야 하는가, 아니면 컨셉을 바꾸는 것으로 충분한가」.

## 7. 산출물

| 파일 | 내용 |
|---|---|
| `measure_look_reuse.py` | 측정 스크립트(4가지 실행) |
| `measure_look_reuse.stdout.txt` | 실행 출력, exit 0 |
| `look_reuse.json` | 곡별 큐·룩 원자료와 쌍별 통계 |
| `examples.py` · `examples.stdout.txt` | 예시 추출과 「첫 큐 같음 ⇔ 같은 컨셉」 검산(어긋남 0) |
| `probe_one.py` · `probe_rotated.py` | 하네스 동작 확인용 탐침. `probe_rotated.py` 가 첫 실행의 결함을 잡았다(아래) |

**첫 실행의 결함.** 처음 돌렸을 때 rotated 에서 네온·빈티지 곡이 구간 큐 0개로 나왔다. 다섯째 답 「우주 컨셉 우선 배치」가 컨셉을 바꿔도 그대로 남아 카드가 거절한 것이다. 컨셉 이름이 박힌 답을 바꿔 끼우게 고쳤고, 앞으로 큐 0개 곡이 나오면 결과를 쓰지 않고 멈추게 했다. 위 숫자는 고친 뒤 실행이다.

> §1~§7 은 구현 **전** 측정이다. 그 원자료는 `look_reuse_before.json`(커밋 `600d445d` 의 `look_reuse.json` 을 그대로 꺼낸 것)이고, 지금 `look_reuse.json` 은 구현 **후** 측정이다.

---

# 2단계 — 구현 (감독 결정 2026-10-12)

감독 결정: 「같은 답을 준 연속 곡도 앱이 스스로 앞 곡과 다른 룩으로 연다」.

## 8. 결론

**같은 답 8곡을 한 세션에서 돌리면 이웃 쌍 첫 큐 같음이 7/7 → 0/7, 다음 곡 큐 중 앞 곡 룩 재사용이 67/99(68%) → 13/99(13%) 로 내려갔다.** 효과는 실제로 도는 대화 길에서 나왔다. 측정 스크립트는 1단계와 같은 것(`measure_look_reuse.py`, 한 글자도 안 고침)이고 `run_instruction` 을 부른다.

곡마다 새 세션을 만든 대조군(`fresh`)은 구현 전과 숫자가 같다(7/7, 67/99). 효과가 세션 기억에서만 나온다는 뜻이다. 기억 범위는 한 쇼(세션) 안이다.

## 9. 측정 전후 (같은 스크립트, 같은 8곡)

| 실행 | 지표 | 구현 전 | 구현 후 |
|---|---|---|---|
| fixed · 한 세션 · 이웃 7쌍 | 첫 큐 룩 같음 | 7/7 | **0/7** |
| fixed · 한 세션 · 이웃 7쌍 | 다음 곡 큐 중 앞 곡 룩 재사용 | 67/99 (68%) | **13/99 (13%)** |
| fixed · 한 세션 · 이웃 7쌍 | 룩을 하나라도 공유한 쌍 | 7 | 3 |
| fixed · 한 세션 · 이웃 7쌍 (효과 포함) | 재사용 | 19/99 | 5/99 |
| fixed · 한 세션 · 전체 28쌍 | 첫 큐 룩 같음 | 28 | 5 |
| fixed · 한 세션 · 전체 28쌍 | 재사용 | 253/405 (62%) | 104/405 (26%) |
| fixed · 한 세션 | 8곡 전체 서로 다른 룩 | 23 | 38 |
| fixed · 새 세션(대조) · 이웃 7쌍 | 첫 큐 같음 / 재사용 | 7/7 · 67/99 | 7/7 · 67/99 (변화 없음) |
| rotated · 한 세션 · 전체 28쌍 | 첫 큐 같음 | 7 | **0** |
| rotated · 한 세션 · 전체 28쌍 | 재사용 | 52/405 | 12/405 |
| rotated · 한 세션 | 8곡 전체 서로 다른 룩 | — | 81 |

원자료: 전 `look_reuse_before.json`, 후 `look_reuse.json` · `measure_look_reuse.stdout.txt`(exit 0) · `after_openings.stdout.txt`(exit 0).

곡별 첫 큐(fixed, 한 세션, 전 → 후): Club Diver `Ring In/블루+cyan` → 그대로 · Cut and Run → `Home/cyan+블루` · Ice cream → `Vocal DSC/블루+cyan` · Morning → `Fan Out/블루+cyan` · Rain → `Ring In/블루+cyan` · Too Cool → `Home/cyan+블루` · scott-buckley-neon → `Vocal DSC/블루+cyan` · 걸그룹DinoDino → `Ring In/블루+cyan`.

**전체 28쌍에 남은 첫 큐 같음 5쌍은 「바닥남」 규칙이 만든 것이다.** 같은 답에서 나올 수 있는 첫 큐 후보는 넷(Ring In·Home·Vocal DSC·Fan Out)뿐이라, 다섯째 곡(Rain)부터는 가장 오래전에 쓴 룩으로 돌아간다. 이웃 쌍에는 하나도 없다. 남은 이웃 재사용 13개는 Morning → Rain 6, scott-buckley-neon → 걸그룹 5, Ice cream → Morning 2 다(`after_openings.stdout.txt`).

## 10. 무엇을 바꿨나

| 자리 | 바꾼 것 |
|---|---|
| `server/design/song_look_memory.py` (새 파일) | `song_looks`(조립 결과 → 구간 큐 룩), `choose_look_offset`(고르기). 순수 함수 |
| `server/design/song_cue_render.py` `_build_unified_song_plan` | `look_offset`(기본 0) 인자. Q4 위치 목록을 돌려 분배하고, 후보가 여럿인 위치는 `candidates[k % n]`, 팔레트 색 순서를 `rotate_palette` 로 돌린다. 구간이 직접 적은 색(`section_text`)은 안 건드린다. 0 이면 오늘과 같다 |
| `server/web/session.py` `_song_compose` | 오프셋 0, 1, 2 … 로 조립해 보고, 곡 룩이 앞서 본 후보와 같아지면(회전이 한 바퀴) 멈춘 뒤 고른다. 상수 없음 — 후보 수는 감독 답의 목록 길이가 정한다 |
| `session.py` 곡 저장 성공 지점 | 콘솔 저장이 끝난 곡의 룩만 `_song_look_history` 에 넣는다. 승인 안 된 계획·거절된 저장은 안 넣는다 |
| `session.py` `_song_plan_edit` | 「앞 곡 룩 허용」(이 곡만 끔) · 「앞 곡과 다른 룩」(다시 켬) |
| `session.py` `_song_finalize` | 오프셋을 돌렸으면 검토 글에 한 줄 — 몇 칸 돌렸는지, 끄는 문구 |
| `docs/proposals/song-structure-lighting-standard.md` §12 | 항목 2 만료 고지 아래 갱신 고지 |

**고르기 규칙**(`choose_look_offset`): ① 첫 큐 룩이 이 세션에서 한 번도 안 쓰인 후보 → ② 다 쓰였으면 첫 큐 룩을 가장 오래전에 쓴 후보(멈추지 않음) → ③ 앞 곡 룩을 덜 다시 쓰는 후보 → ④ 작은 오프셋(0 = 감독 답 그대로). 「썼다」는 그 곡의 어느 큐에서든 나온 룩이다.

## 11. 시험

`server/tests/test_song_look_memory_t491.py` — 12개 통과. 대화 길 시험 5개는 기존 하네스(`TestSongDesignInterviewSession`)로 `run_instruction` 을 끝까지(리뷰 승인 → 저장) 돈다.

- 같은 세션 둘째 곡의 첫 큐가 첫 곡과 다르다
- 새 세션의 같은 곡은 첫 곡과 같다(기억 범위 = 세션)
- 「앞 곡 룩 허용」이면 둘째 곡이 첫 곡과 같다(오프셋 0)
- 검토 글에 끄는 문구가 나온다
- 승인 안 된 곡은 기억에 안 들어간다
- 고르기 규칙 6개, 오프셋 0 ⇔ 끈 경로 동일 1개

**돌연변이 확인**(시험이 결함을 잡는지):

| 돌연변이 | 결과 |
|---|---|
| `_song_compose` 가 항상 오프셋 0 (배선 끊김 — t486 이 지운 죽은 배선과 같은 꼴) | 2개 실패(둘째 곡 다름 · 검토 글) |
| 저장 성공 뒤 기억 기록 줄 제거 | 4개 실패 |

둘 다 되돌렸다(`grep -c MUTANT` → 0).

**기존 시험:** `pytest server/tests -k "song or chorus or palette or composer or web_session or songcue or timeline or arc or accent or ldrender or upload or concept or beat_grid or preset"` → 3597 passed, 8 skipped. `make ci-local`(fmt · lint · test-fast) → exit 0. 전체 묶음은 CI 가 잰다.

## 12. 안 잰 것 (2단계)

- **무대에서 어떻게 보이는지는 안 쟀다.** 콘솔 0. 바뀌는 것은 감독이 고른 위치 목록의 순서와 팔레트 색 순서(주색↔보조색)다. 주색이 바뀐 곡이 감독 눈에 「다른 룩」으로 읽히는지는 사람이 봐야 안다.
- **팔레트 회전은 역할별 색 배정을 바꾼다.** `back`·`mover` 가 받는 지배색과 `side`·`wash` 가 받는 보조색이 맞바뀐다(SPEC-LDRENDER-001 M4 규칙 그대로, 순서만 바뀐 입력). 의도와 맞는지 감독 확인이 필요할 수 있다.
- **다시 조립할 때마다 후보 수만큼 조립한다.** 8곡 측정에서 체감 지연은 없었지만 시간은 재지 않았다.
- **세션이 끝나면 기억도 사라진다.** 서버 재시작이나 새 브라우저 세션은 새 쇼로 친다(지시 ③ 그대로).
- **업로드 길(`prepare_songcue`)에는 효과가 없다.** 같은 조립 함수를 부르는 운영 호출처는 둘이다 — `server/web/session.py` `_song_compose`(대화 길, 이번에 배선)와 `server/design/upload_song_plan.py:197`(`server/orchestrator/tools.py:3065` `prepare_songcue` 도구가 부름). 업로드 길은 `look_offset` 을 안 넘기므로 기본값 0 — 오늘과 같고, 곡 사이 회피도 없다. 지시가 대화 길 끝을 지목해서 넓히지 않았다. 감독이 실제 쇼에서 어느 길로 곡을 올리는지는 재지 않았다.
- 실제 DSP 경로·실제 감독 답의 다양성은 1단계와 같이 안 쟀다(§5).
