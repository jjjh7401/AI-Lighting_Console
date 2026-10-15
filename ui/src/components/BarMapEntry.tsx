// 마디 지도 진입 컨트롤 `BarMapEntry` (SPEC-LDBARMAP-003, 카드 t648).
//
// props 만 받는 표시 컴포넌트다. 소켓도, 리듀서 호출도, DOM 접근도 없다. 상태는 호출부가
// `barMapEntryState.ts` 의 리듀서로 들고 이 컴포넌트에는 값을 내려 준다. 사람이 한 일(오프셋
// 고르기, 분석, 취소)은 콜백으로 올려 보낼 뿐이고, 프레임을 만들어 보내는 일은 소켓 훅의
// 몫이다. 그래서 이 파일에는 프레임 이름도 박자표 숫자도 없다(REQ-LDBARUI-011, 012).
//
// 문구는 spec.md 「문구 고정표」의 글자 그대로다. 사실 문구는 `barMapEntryState.ts` 가 만든
// 것을 가져다 쓰고, 선택지 개수는 `protocol.ts` 의 상수에서 만든다.
//
// 배치(REQ-LDBARUI-013)
// - 컨트롤 묶음(`composer-bar-map`)에는 드롭다운과 버튼만 둔다.
// - 사실 문구, 「분석 중」, 안내 줄은 묶음 밖의 별도 요소라 각자 자기 줄에 선다.
// - 래퍼 없이 형제 요소를 돌려준다. 호출부가 곡 첨부 상태 블록 안에 놓으면 묶음은 기존
//   「분석」 버튼 곁에 서고, 나머지 줄은 그 아래로 내려간다.
// - 버튼 모양은 기존 「분석」 버튼의 클래스를 그대로 쓴다. 새 CSS 는 `.composer-bar-map`
//   규칙 하나뿐이다(plan.md 바뀌는 파일 표).
import { BAR_MAP_BEATS_PER_BAR } from "../protocol";
import { BAR_MAP_NOTICE_OFF_METER, isOffMeter } from "./barMapEntryState";

export interface BarMapEntryProps {
  /** 사람이 고른 첫 박 오프셋. 고르기 전에는 `null` 이고 기본값이 없다(REQ-LDBARUI-002). */
  offset: number | null;
  /** 요청을 보내고 결과를 기다리는 중인가. 참이면 드롭다운과 분석 버튼을 막고 「분석 중」과 「취소」를 보인다. */
  waiting: boolean;
  /** 채팅 응답이 진행 중인가. 참이면 분석 버튼만 막는다. 입력창과 드롭다운은 막지 않는다. */
  responding: boolean;
  /** 곡 타임라인의 박자표 문자열. 없으면 `null`. 분석기의 박자표와 다르면 사실 문구를 보이되 선택지는 바꾸지 않는다(REQ-LDBARUI-003). */
  timelineMeter: string | null | undefined;
  /** 컨트롤 곁에 보일 안내 줄(결과, 거절 사유, 오류, 취소 안내). 없으면 `null`. */
  notice: string | null;
  /** 드롭다운에서 고른 값. 「선택」(빈 값)으로 되돌리면 `null`. */
  onOffsetChange: (offset: number | null) => void;
  /** 「마디 지도 분석」 버튼을 눌렀다. 연결 확인과 전송은 호출부가 한다. */
  onAnalyse: () => void;
  /** 「취소」 버튼을 눌렀다. 화면의 대기만 끄고 서버의 분석은 멈추지 않는다. */
  onCancel: () => void;
}

/** 드롭다운 선택지: 0 부터 한 마디 박 수 - 1 까지. 곡 박자표로 계산하지 않는다(REQ-LDBARUI-003). */
const OFFSET_CHOICES: readonly number[] = Array.from(
  { length: BAR_MAP_BEATS_PER_BAR },
  (_, beat) => beat,
);

export function BarMapEntry({
  offset,
  waiting,
  responding,
  timelineMeter,
  notice,
  onOffsetChange,
  onAnalyse,
  onCancel,
}: BarMapEntryProps) {
  return (
    <>
      <div className="composer-bar-map">
        <label>
          첫 박 오프셋{" "}
          <select
            value={offset === null ? "" : String(offset)}
            disabled={waiting}
            onChange={(event) => {
              const chosen = event.target.value;
              // 빈 값은 「선택」으로 되돌린 것이다. Number("") 는 0 이라, 걸러 내지 않으면
              // 아무것도 고르지 않은 상태가 오프셋 0 으로 읽힌다.
              onOffsetChange(chosen === "" ? null : Number(chosen));
            }}
          >
            <option value="">선택</option>
            {OFFSET_CHOICES.map((beat) => (
              <option key={beat} value={String(beat)}>
                {beat}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="composer-song-analyse"
          disabled={offset === null || waiting || responding}
          onClick={onAnalyse}
        >
          마디 지도 분석
        </button>
        {waiting && (
          <button type="button" className="composer-song-analyse" onClick={onCancel}>
            취소
          </button>
        )}
      </div>
      {isOffMeter(timelineMeter) && (
        <div className="composer-bar-map-fact">{BAR_MAP_NOTICE_OFF_METER}</div>
      )}
      {waiting && <div className="composer-bar-map-status">분석 중</div>}
      {notice ? <div className="composer-bar-map-notice">{notice}</div> : null}
    </>
  );
}
