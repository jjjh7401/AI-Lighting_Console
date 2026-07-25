import {
  type ExecutionPreview,
  type ExecutionPreviewCommand,
  type PreviewRiskLevel,
} from "../protocol";

const RISK_LABELS: Record<PreviewRiskLevel, string> = {
  info: "정보",
  caution: "주의",
  danger: "위험",
};

const ACTION_LABELS: Record<string, string> = {
  store_overwrite: "덮어쓰기",
  store: "저장",
  delete: "삭제",
  blackout: "블랙아웃",
  off: "오프",
  run: "실행",
  modify: "수정",
  unknown: "명령",
};

export function previewCommandMeta(command: ExecutionPreviewCommand): string {
  const action = ACTION_LABELS[command.action] ?? command.action;
  const target =
    command.target === null ? command.target_kind : `${command.target_kind} ${command.target}`;
  return `${target} · ${action}`;
}

export function ExecutionPreviewCard({ preview }: { preview: ExecutionPreview }) {
  return (
    <section className={`execution-preview-card preview-risk-${preview.risk_level}`}>
      <div className="preview-header">
        <div className="preview-title">실행 전 미리보기</div>
        <span className="preview-risk">{RISK_LABELS[preview.risk_level]}</span>
      </div>
      <div className="preview-summary">{preview.summary}</div>
      <div className="preview-command-list">
        {preview.commands.map((command, index) => (
          <div className="preview-command-row" key={`${preview.preview_id}-${index}`}>
            <code className="preview-command-text">{command.command}</code>
            <span className="preview-command-label">{command.label}</span>
            <span className="preview-command-meta">{previewCommandMeta(command)}</span>
          </div>
        ))}
      </div>
      {preview.warnings.length > 0 && (
        <div className="preview-warning-list">
          {preview.warnings.map((warning, index) => (
            <div
              className={`preview-warning preview-warning-${warning.severity}`}
              key={`${warning.command}-${warning.label}-${index}`}
            >
              <span className="preview-warning-label">{warning.label}</span>
              <span className="preview-warning-detail">{warning.detail}</span>
            </div>
          ))}
        </div>
      )}
      <div className="preview-scope">명령 문자열 기반 preview입니다. 실제 Cue diff/tracking 영향은 포함하지 않습니다.</div>
    </section>
  );
}
