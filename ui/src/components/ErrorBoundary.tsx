// 앱 최상단 오류 경계. 렌더 중 잡히지 않은 오류가 나면 React 는 #root 트리를
// 통째로 내려서 화면이 검게 빈다. 여기서 받아 「이 부분을 그리지 못했어요」만
// 보여 준다.
//
// React 경계가 잡지 못하는 것: 이벤트 핸들러 안과 비동기 코드의 오류.
import { Component, type ErrorInfo, type ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("화면 일부를 그리지 못했습니다", error, info.componentStack);
  }

  // 상태만 비운다. 같은 데이터면 다시 던지고 안내가 다시 뜬다.
  private reset = (): void => {
    this.setState({ error: null });
  };

  render(): ReactNode {
    const { error } = this.state;
    if (error === null) return this.props.children;
    return (
      <section className="error-boundary-fallback" role="alert">
        <h2>이 부분을 그리지 못했어요</h2>
        <p>화면 데이터에 빠진 값이 있거나 예상하지 못한 값이 들어왔을 수 있어요.</p>
        <button type="button" onClick={this.reset}>
          다시 그리기
        </button>
        <details>
          <summary>오류 내용</summary>
          <pre>{error.message}</pre>
        </details>
      </section>
    );
  }
}
