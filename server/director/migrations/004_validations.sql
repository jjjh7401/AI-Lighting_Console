-- SPEC-LDWIRE-001 M2 -- ValidationReport persistence (design.md section-nab
-- alternative A: DirectorStore extension, not a separate store module).
--
-- This migration is an EXTEND, not a redefinition of 001/002/003 -- it adds
-- one new table so validation_id can be resolved back to the ValidationReport
-- captured at PUT-plan submission time. store.py's own comment (line 38)
-- already predicted this gap: "validation_id / approval_id / execution_id
-- are omitted because that relationship does not exist yet."

PRAGMA foreign_keys = ON;

-- One row per issued validation_id. Immutable once written -- a validation_id
-- is a deterministic hash of (plan_digest, revision, context_digest), so a
-- retried submission with identical inputs recomputes the SAME id and this
-- insert is a no-op (ON CONFLICT DO NOTHING at the call site), never a
-- silent overwrite of a prior report.
CREATE TABLE IF NOT EXISTS validations (
    validation_id    TEXT    NOT NULL PRIMARY KEY,
    project_id       TEXT    NOT NULL,
    plan_id          TEXT    NOT NULL,
    plan_digest      TEXT    NOT NULL,
    context_digest   TEXT    NOT NULL,
    compiled_digest  TEXT    NOT NULL,
    outcome          TEXT    NOT NULL,
    diagnostics_json TEXT    NOT NULL,
    compiled_json    TEXT    NOT NULL,
    created_at       TEXT    NOT NULL,
    expires_at       TEXT    NOT NULL
) STRICT;

CREATE INDEX IF NOT EXISTS validations_by_project
    ON validations (project_id, validation_id);
