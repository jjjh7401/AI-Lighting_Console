# M3-a 프로브 노트 — 슬롯 999 / 시퀀스 9

SPEC-COPILOT-MUSICSYNC-001 · REQ-019·021·023·025 · AC-020·021·022

## 실행 일자

- 2026-09-05T10:20:24+00:00
- 판정: **완결** (`complete`)

## 슬롯 판정

- `_timecode_slot_verdict` 재구현 판정: **free**

## 조회 수

- 합계 11 / 상한 12
- 프로브 5건(① ② ③ ④ ⑤) / 상한 5 — 조회 수와 단위가 다르다
- `slot_verdict`: 1
- `pool_baseline`: 1
- `control_negative`: 1
- `post_prep_readback`: 1
- `probe1_trackgroup`: 1
- `probe2_candidates`: 4
- `probe3_rig_path`: 1
- `post_release_readback`: 1

## 쓰기 명령 전문

- `Store Timecode 999`
- `Set Timecode 999 Property 'Name' 'MSYNCPROBE'`
- `Assign Sequence 9 At Timecode 999`
- `Go Timecode 999`
- `Go+ Timecode 999`
- `Pause Timecode 999`
- `Toggle Timecode 999`
- `Off Timecode 999`
- 합계 8 / 상한 8

## ① TrackGroup 판독

- 경로: `DataPool/Timecodes/999/TrackGroup 1`
- 자식 2개 · childCount 2
- truncated: False · 멈춤: complete

## ② 재생 명령 후보 (가설 집합 — 실측 아님)

- `Go Timecode 999` — ok=True · **효과=True** · 응답: OK
- `Go+ Timecode 999` — ok=True · **효과=True** · 응답: OK
- `Pause Timecode 999` — ok=True · **효과=True** · 응답: OK
- `Toggle Timecode 999` — ok=True · **효과=True** · 응답: OK

## ③ rig_paths["timecodes"] 실값

- 코드 실값: `DataPool/Timecodes`
- M0 문자열: `DataPool/Timecodes` · 일치: True
- `DEFAULT_RIG_CONTEXT_PATHS` 등재 여부: False
- 그 경로가 답하는가: True

## ④ ⑤ 대조군 원문

- ④ 풀 응답: True · 사유: None
- ④ 준비 뒤 슬롯 이름: MSYNCPROBE · 일치: True
- ⑤ 생성 전 슬롯 응답: False · 원문: path segment not found: '999' (in DataPool/Timecodes/999)

## 미검증

- (없음) — 위 다섯이 모두 관측됐다

## 잔여물

- 타임코드 슬롯 999('MSYNCPROBE') 가 콘솔에 남는다 — 해제만 했고 삭제하지 않았다. 삭제 동사는 spec.md §A.4 M3-a 예산 밖이므로 이 프로브가 쏘지 않는다. 정리는 운영자 몫이다

## 2회차 정정 (오케스트레이터, 2026-09-05) — ② 의 「효과=True」 넷은 오판이다

위 본문의 ② 표는 프로브 1판이 낸 것이고, **넷 다 틀렸다.** 되읽기 다섯 장(준비 직후 + 후보 4종 뒤)을
`id` 필드만 빼고 대조하면 **바이트 단위로 전부 같다**(`evidence/musicsync-m3a-run2-steps.jsonl` seq 7·10·12·14·16).
응답기가 되읽기마다 새 요청 번호(`gate-12`·`gate-15`·`gate-17`·`gate-20`)를 매기는데 비교 함수가 그 필드를
안 걸러 「변화」로 세었다. 같은 커밋에서 `_canonical` 이 `id` 를 빼도록 고쳤고 회귀 검사를 붙였다.

정정된 판정:

| 항목 | 판정 | 근거 |
|---|---|---|
| ① `TrackGroup 1` 아래 판독 | **열렸다** | 자식 2 · `childCount` 2 · `truncated:false` — `MarkerTrack "Marker"`, `Track "<T215 SCRATCH DELETABLE>"`. 자식이 테이블 값이 아니라 오브젝트라 READBACK-001 R1 의존은 생기지 않는다 |
| ② 재생 후보 4종 (`Go`·`Go+`·`Pause`·`Toggle`) | **효과 미관측 — 전부 미증명** | 넷 다 `ok:true` 를 답했지만 오브젝트 상태 스냅숏은 준비 직후와 동일. 이 채널은 재생 상태(running/position)를 노출하지 않으므로 「효과 없음」이 아니라 **「이 채널로는 잴 수 없음」**이다. REQ-023 대로 어느 후보도 운영자 인계 목록에 올리지 않는다 → 설계서 §5 **갈래 B** |
| ③ `rig_paths["timecodes"]` 실값 | **일치** | 코드 값 `DataPool/Timecodes` = M0 문자열, 조회 응답함(childCount 2). `DEFAULT_RIG_CONTEXT_PATHS` 표에 없는 것은 결함이 아니라 설계다(`tools.py:363-372` 주석 — 모델이 타임코드를 훑지 않게 표 밖에 둔다) |
| ④ 양성 대조군 | 통과 | 풀 응답(childCount 1→2) · 슬롯 999 이름 `MSYNCPROBE` 일치 |
| ⑤ 음성 대조군 | 통과 | 생성 전 `DataPool/Timecodes/999` → `path segment not found: '999' (in DataPool/Timecodes/999)` |

예산: 쓰기 8/8(열거와 정확히 일치 · 열거 밖 0 · 비격리 대상 0) · 조회 11/12 · 프로브 5/5.

전제 조건: 이 회차는 **감독이 콘솔에 `Timecode 1` 을 손으로 만든 뒤**에야 가능했다(1회차 무결론의 원인 — 빈 풀은
unknown). 앱 스스로는 빈 쇼에 타임코드를 못 만든다 — 별도 결정 대상.

잔여물: `Timecode 1`(감독 생성) · `Timecode 999 "MSYNCPROBE"`(프로브, `Off` 로 해제만). 삭제는 운영자 몫.

미검증(B4 잔여): 재생 명령의 **효과**는 다른 채널(예: 타임코드 오브젝트의 재생 속성 `query_properties`, 또는
LTC/시계 되읽기)로만 잴 수 있으며 이 회차 예산 밖이다.
