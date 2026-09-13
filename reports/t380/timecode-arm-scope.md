# t380 — 타임코드 무장 (Timecode arm) 범위 정리

카드 지시: "Scope only. Write up what the operator handoff would look like end to
end, what is already built, and what is missing — but build no new firing path
and do not weaken the existing no-`verified` verdict discipline."

이 문서는 새 발화 경로를 만들지 않는다. 이미 있는 코드를 읽고 end-to-end 흐름과
빈 자리를 적는다.

## 이미 구축된 것

1. **준비(슬롯 배정)** — `prepare_songcue` 툴(`server/orchestrator/tools.py`)이
   `timecode_slot_verdict` 로 슬롯 점유를 먼저 재고(비었을 때만),
   `Store Timecode <n>` · `Set Timecode <n> Property 'Name' …` ·
   `Assign Sequence <s> At Timecode <n>` 세 줄을 **콘솔에 직접 쓴다**(승인 번들
   경유, `run_commands`). 이 세 문형은 SONGCUE-001 M0 에서 실측 GO 다.

2. **운영자 인계 문자열** — `server/orchestrator/songcue_timecode.py`
   `operator_handoff_commands(timecode_number)` 가 `Record Timecode <n>` 한 줄을
   만든다. 이 문자열은 **`prepare_songcue` 응답 페이로드**
   (`payload["timing"]["operator_handoff"]["commands"]`)에 실려 채팅 화면에
   뜨지만, **앱은 절대 이 문자열을 발화하지 않는다** — REQ-MUSICSYNC-020 /
   AC-MUSICSYNC-022 가 못박은 경계다(`server/tests/test_songcue_tool.py` 및
   MUSICSYNC-001 acceptance.md 로 잠김).

3. **되읽기 검증기** — 같은 모듈의 `verify_songcue_timecode()` 가
   `query_state` **4회 이하**로 풀 존재·이름 일치·`TrackGroup` 구성 세 축(+
   M3-a 가 연 경우에 한해 이벤트 내용 넷째 축)을 재고, `render_timecode_verification_report()`
   가 5절(주장/증거/기준 귀속/미검증/잔여 위험) 산출물을 만든다. 판정 어휘는
   `unverified` · `SongCueTimingSkip` · `inconclusive` 셋뿐이고 **`verified` 는
   없다** — 재생 명령의 효과가 증명된 적이 없기 때문이다(모듈 독스트링).

## 끝에서 끝까지 흐르면 이런 모양이다

```
1) 운영자가 채팅으로 곡 큐를 만든다
     → prepare_songcue 가 큐/타임코드 슬롯/시퀀스 배정을 콘솔에 쓴다
2) 앱 응답에 "Record Timecode <n>" 한 줄이 인계분으로 뜬다 (앱은 안 쏜다)
3) 운영자가 그 명령을 콘솔에서 직접 실행 — 콘솔이 녹화 무장 상태가 된다
4) 운영자가 LTC 소스(또는 Timecode 에디터)에 맞춰 큐 GO 이벤트를 직접 배치한다
     — 이 절차 자체가 정본 운영 절차이며 앱이 대신하지 않는다(design.md §3)
5) 운영자가 녹화를 마쳤다고 앱에 알린다  ← ★ 이 트리거가 없다(아래 "빠진 것")
6) 앱이 verify_songcue_timecode() 로 되읽어 5절 판정을 낸다
     — 판정은 unverified/SongCueTimingSkip/inconclusive 중 하나, 'verified' 없음
```

## 빠진 것 (만들지 않았다 — 범위 밖으로 남긴다)

- **5번 트리거가 세션 어휘에 없다.** `verify_songcue_timecode` 를 실제로 부르는
  자리는 `server/tools/musicsync_m3b_verify.py`(독립 CLI 도구, 실기 검증용
  스크립트)와 테스트뿐이다 — `session.py` 어디에도 "녹화 끝났어" 같은 문장을
  받아 이 검증기를 호출하는 라우팅이 없다(`grep -rn "verify_songcue_timecode"
  server/web/session.py` 0건). 즉 운영자가 앱 채팅으로 "녹화 확인해줘"라고
  말해도 지금은 아무 일도 안 일어난다.
- **재생 명령 문법 자체가 미확정이다.** `Go Timecode 999` 는 `Illegal object`
  로 기각됐고(`.moai/state/verify/songcue-m0/steps.jsonl:73`), 그 이후 유효한
  재생 명령 후보가 measured-GO 로 승격된 기록이 없다(MUSICSYNC-001
  spec.md:50 "재생 명령 문법 ❌ 미확정"). 이 문서는 그 문형을 지어내지 않는다
  — `server/design/override_look.py` 의 `Stop IFX/PFX` 선례와 같은 규율이다.
- **타임코드 검증에 대한 채팅 응답 렌더링**이 없다 — `render_timecode_verification_report`
  는 마크다운 문자열을 만들 뿐이고, 이것을 `QuestionRequest` 나 세션 응답에
  실어 운영자 화면에 보여주는 배선이 없다.

## 이번 카드에서 하지 않은 것 (지시대로)

- 재생 명령을 발화하는 새 문형을 만들지 않았다.
- `verified` 판정 어휘를 추가하지 않았다 — 세 판정(unverified/SongCueTimingSkip/inconclusive)
  그대로 둔다.
- 5번 트리거(세션 어휘 라우팅)를 만들지 않았다 — 별도 카드로 남긴다.
