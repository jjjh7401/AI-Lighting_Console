"""Human review gate types (M7 — REQ-MVP-019/027, AC-MVP-010 ②③).

The review is a DISTINCT request type from the M4 command approval, carried
over the same channel pattern (M5 ApprovalChannel): the reviewer sees the
plugin name, a bounded source preview, the compile verdict, and the full
destructive-scan report — then approves or rejects the deployment.

Fail-safe: the DEFAULT port denies everything. Without a wired review channel
no plugin can ever deploy (REQ-MVP-019 deny-by-default, REQ-MVP-014 spirit).
The human review gate is the AUTHORITATIVE control; the scan it displays is a
best-effort assist signal (REQ-MVP-027 residual-risk framing).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from server.deploy.scan import ScanReport

# Bounded preview so one review request stays a sane WebSocket frame; the full
# source length is always reported alongside.
PREVIEW_MAX_CHARS = 4000


@dataclass(frozen=True)
class ReviewRequest:
    """Everything the human reviewer must see for one deployment."""

    plugin_name: str
    source_preview: str
    source_length: int
    source_truncated: bool
    compile_ok: bool
    scan: ScanReport


def build_review_request(
    plugin_name: str, lua_source: str, *, compile_ok: bool, scan: ScanReport
) -> ReviewRequest:
    """Compose one review request with a bounded source preview."""
    truncated = len(lua_source) > PREVIEW_MAX_CHARS
    return ReviewRequest(
        plugin_name=plugin_name,
        source_preview=lua_source[:PREVIEW_MAX_CHARS],
        source_length=len(lua_source),
        source_truncated=truncated,
        compile_ok=compile_ok,
        scan=scan,
    )


class ReviewPort(Protocol):
    """Blocking human review channel (M5 ApprovalChannel wires the UI)."""

    def request_review(self, request: ReviewRequest) -> bool:
        """Return True only when the human approved the deployment."""
        ...


class DenyAllReviewPort:
    """Fail-safe default: no review channel -> nothing ever deploys."""

    def request_review(self, request: ReviewRequest) -> bool:
        return False
