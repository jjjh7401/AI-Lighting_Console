import { useState } from "react";

import type { PendingQuestion } from "../protocol";

function copyCommand(command: string) {
  if (typeof navigator === "undefined" || navigator.clipboard === undefined) return;
  void navigator.clipboard.writeText(command);
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
 */
export function QuestionCard({
  question,
  onAnswer,
}: {
  question: PendingQuestion;
  onAnswer: (requestId: string, answer: string) => void;
}) {
  const [typed, setTyped] = useState("");

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
            위 명령을 복사해 <strong>콘솔 명령줄에 직접</strong> 붙여넣고 실행하세요 — 앱이
            대신 실행하면 동작하지 않습니다.
          </p>
        </div>
      )}

      {question.options.length > 0 && (
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
      )}

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
