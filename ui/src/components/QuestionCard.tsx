import { useState } from "react";

import type { PendingQuestion } from "../protocol";

function copyCommand(command: string) {
  if (typeof navigator === "undefined" || navigator.clipboard === undefined) return;
  void navigator.clipboard.writeText(command);
}

/**
 * 다중 선택 답 하나로 이어 붙인다 — 서버가 읽는 형식은 `", "`(콤마 + 공백) 결합이다.
 *
 * 순서는 **`options`에 실린 순서**다. 클릭 순서로 이으면 사용자가 「컬러」를 먼저
 * 누른 것만으로 서버의 계열 처리 순서가 바뀌는데, 그 순서는 카드를 만든 쪽이 정한
 * 것이라 UI가 흔들 자리가 아니다.
 */
export function joinChosenLabels(
  options: readonly { label: string }[],
  chosen: readonly string[],
): string {
  return options
    .map((option) => option.label)
    .filter((label) => chosen.includes(label))
    .join(", ");
}

/**
 * 체크박스 하나가 켜지거나 꺼진 뒤의 선택 목록.
 *
 * 같은 라벨을 두 번 담지 않는다 — 담기면 답에 같은 계열이 두 번 실려 서버가 그것을
 * 두 번 실행한다(프리셋 저장은 경고 없이 덮어쓴다).
 */
export function toggleChosenLabel(
  chosen: readonly string[],
  label: string,
  checked: boolean,
): string[] {
  if (!checked) return chosen.filter((each) => each !== label);
  return chosen.includes(label) ? [...chosen] : [...chosen, label];
}
/**
 * 모델이 되묻는 질문 카드 — 추측 대신 물으라는 통로.
 *
 * 실측 사례: 콘솔 라이브러리에 없는 픽스처 타입을 요청받자 모델이 `Import` 문법과
 * GDTF 파일명을 다섯 번 추측하고 플러그인까지 배포·실행했으나 장비는 하나도
 * 생기지 않았다(59.6초 소모). 그 자리에 이 카드가 선다.
 *
 * **선택지가 있어도 자유 입력을 닫지 않는다.** 사용자의 실제 사정이 선택지에 없는
 * 경우가 실물에서 흔하다 — 콘솔에 다른 이름으로 들어와 있다든지, 지금은 콘솔을
 * 만질 수 없다든지.
 *
 * `question.multi`가 참이면 같은 선택지를 **체크박스 + 「확인」**으로 렌더한다.
 * 한 문장이 여러 계열을 지정하는 경우(«포지션, 컬러, 딤머 프리셋을 설정해줘»)에
 * 단일 선택 카드는 그중 하나만 받고 나머지를 조용히 버리기 때문이다. 답은 고른
 * 라벨을 `", "`로 이은 한 문자열이고, 순서는 **클릭 순서가 아니라 카드에 실린
 * 순서**다 — 서버가 계열을 그 순서로 실행하므로 클릭 순서가 실행 순서를 흔들면
 * 안 된다.
 */
export function QuestionCard({
  question,
  onAnswer,
}: {
  question: PendingQuestion;
  onAnswer: (requestId: string, answer: string) => void;
}) {
  const [typed, setTyped] = useState("");
  // 서버가 `selected`로 표시한 항목은 체크된 채 뜬다 — 문장이 이미 지목한
  // 계열이 그것이다. 카드는 `key={request_id}`로 물음마다 새로 마운트되므로
  // 초기값 한 번이면 충분하다(이전 물음의 선택이 새 카드로 새지 않는다).
  const [chosen, setChosen] = useState<string[]>(() =>
    question.options.filter((option) => option.selected).map((option) => option.label),
  );

  return (
    <section className="card question-card" aria-label="질문">
      <h3 className="question-prompt">{question.prompt}</h3>
      {question.why && <p className="question-why">{question.why}</p>}

      {question.steps.length > 0 && (
        <ol className="question-steps">
          {question.steps.map((step, index) => (
            <li key={index}>{step}</li>
          ))}
        </ol>
      )}
      {question.commands.length > 0 && (
        <div className="question-commands">
          {question.commands.map((command) => (
            <div key={command} className="question-command-row">
              <code className="command-text">{command}</code>
              <button
                type="button"
                className="command-copy"
                onClick={() => copyCommand(command)}
                aria-label="명령 복사"
              >
                복사
              </button>
            </div>
          ))}
          <p className="question-command-hint">
            앱이 이 명령을 <strong>대신 실행</strong>합니다 — 위 버튼으로 답만 주시면 됩니다.
            자동 실행이 또 실패할 때만 이 명령을 복사해 콘솔 명령줄에 붙여넣으세요.
          </p>
        </div>
      )}

      {question.options.length > 0 &&
        (question.multi ? (
          <div className="question-options question-options-multi">
            {question.options.map((option) => (
              <label key={option.label} className="question-option-check">
                <input
                  type="checkbox"
                  checked={chosen.includes(option.label)}
                  onChange={(event) => {
                    // 갱신 함수 밖에서 읽는다 — React가 갱신을 미루면 이벤트 대상은
                    // 이미 다른 상태일 수 있다.
                    const isChecked = event.target.checked;
                    setChosen((previous) =>
                      toggleChosenLabel(previous, option.label, isChecked),
                    );
                  }}
                />
                <span className="question-option-label">{option.label}</span>
                {option.description && (
                  <span className="question-option-desc">{option.description}</span>
                )}
              </label>
            ))}
            <button
              type="button"
              className="question-option-confirm"
              disabled={chosen.length === 0}
              onClick={() => {
                const answer = joinChosenLabels(question.options, chosen);
                if (!answer) return;
                setChosen([]);
                onAnswer(question.request_id, answer);
              }}
            >
              확인
            </button>
          </div>
        ) : (
          <div className="question-options">
            {question.options.map((option) => (
              <button
                key={option.label}
                type="button"
                className="question-option"
                onClick={() => onAnswer(question.request_id, option.label)}
              >
                <span className="question-option-label">{option.label}</span>
                {option.description && (
                  <span className="question-option-desc">{option.description}</span>
                )}
              </button>
            ))}
          </div>
        ))}

      <form
        className="question-freeform"
        onSubmit={(event) => {
          event.preventDefault();
          const answer = typed.trim();
          if (!answer) return;
          setTyped("");
          onAnswer(question.request_id, answer);
        }}
      >
        <input
          type="text"
          value={typed}
          onChange={(event) => setTyped(event.target.value)}
          placeholder="감독 요청을 직접 입력"
          aria-label="감독 요청 직접 입력"
        />
        <button type="submit" disabled={!typed.trim()}>
          감독 요청 반영
        </button>
      </form>
    </section>
  );
}
