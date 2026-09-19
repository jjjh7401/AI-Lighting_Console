-- SPEC-LDRECV-001 M4 — durable execution journal · idempotency · destination 예약
-- (계약 §9.7 · §10 · REQ-LDPLUGIN-023).
--
-- 이 마이그레이션은 `001_initial.sql` 을 재정의하지 않는다 — 뒤에 이어붙이는 EXTEND
-- 다. `001_initial.sql` 자신의 주석(1-8행)이 이미 이 분리를 예견했다: "approval 과
-- execution journal 은 형제 SPEC-LDRECV-001 의 것이므로 여기서 만들지 않는다."
--
-- `idempotency_keys`(001, `plan_revisions` 에 FK)는 plan **제출** 전용이다. 이 파일의
-- `idempotency_records` 는 execution(apply) 경로의 범용 멱등 저장소이며 plan revision
-- 에 묶이지 않는다 — 별개 테이블인 이유다.

PRAGMA foreign_keys = ON;

-- 하나의 apply 시도. 계약 §10 의 PlanState 실행 부분(`applying`)에 대응하는 durable
-- 기록이며, `state` 는 이 SPEC 이 정의하는 journal state 다: planned → sending
-- (디스크 commit) → sent/acknowledged/failed/unknown.
--
-- `approval_id` 는 승인 소비의 durable 증거다 — 계약 §10: "승인은 첫 execution
-- allocation 시 소비된다."
CREATE TABLE IF NOT EXISTS executions (
    execution_id TEXT    NOT NULL PRIMARY KEY,
    project_id   TEXT    NOT NULL,
    principal_id TEXT    NOT NULL,
    approval_id  TEXT    NOT NULL,
    operation    TEXT    NOT NULL,
    state        TEXT    NOT NULL,
    created_at   TEXT    NOT NULL,
    updated_at   TEXT    NOT NULL
) STRICT;

CREATE INDEX IF NOT EXISTS executions_by_approval
    ON executions (approval_id);

-- bundle journal — execution 하나가 여러 bundle 을 순서대로 보낸다. 계약 §10:
-- "journal에는 bundle planned→sending(디스크 commit)→sent/acknowledged/failed/unknown과
-- 시간·오류·evidence를 남긴다."
CREATE TABLE IF NOT EXISTS execution_bundles (
    execution_id TEXT    NOT NULL,
    bundle_index INTEGER NOT NULL,
    bundle_id    TEXT    NOT NULL,
    state        TEXT    NOT NULL,
    updated_at   TEXT    NOT NULL,
    error        TEXT,

    PRIMARY KEY (execution_id, bundle_index),
    FOREIGN KEY (execution_id) REFERENCES executions (execution_id)
) STRICT;

-- 멱등 key (계약 §9.7) — execution(apply) 경로 전용. `result_body` 는 최초 응답 전체를
-- JSON 문자열로 보관한다 — 계약 §10: "최초 저장한 status와 body를 그대로 replay한다."
-- `plan_revisions` 에 대한 FK 가 없다 — plan 제출과 달리 이 경로의 result 는 특정
-- revision 행이 아니라 execution 하나에 대응한다.
CREATE TABLE IF NOT EXISTS idempotency_records (
    project_id          TEXT    NOT NULL,
    principal_id        TEXT    NOT NULL,
    operation           TEXT    NOT NULL,
    idempotency_key     TEXT    NOT NULL,

    request_fingerprint TEXT    NOT NULL,

    result_execution_id TEXT    NOT NULL,
    result_status       INTEGER NOT NULL,
    result_body         TEXT    NOT NULL,

    created_at          TEXT    NOT NULL,

    PRIMARY KEY (project_id, principal_id, operation, idempotency_key),
    FOREIGN KEY (result_execution_id) REFERENCES executions (execution_id)
) STRICT;

-- destination 점유 — design.md §3 채택안 B. `context.py`(형제 SPEC 소유, 불변
-- ContextSnapshot)와 분리된 LDRECV 자신의 가변 상태다. create-only(LD-TARGET-001):
-- 이미 `reserved` 인 slot 위에 다른 execution 이 조용히 재선택하지 못한다.
CREATE TABLE IF NOT EXISTS destination_reservations (
    project_id               TEXT NOT NULL,
    show_id                  TEXT NOT NULL,
    sequence_id              TEXT NOT NULL,
    reserved_by_execution_id TEXT NOT NULL,
    reserved_at              TEXT NOT NULL,
    status                   TEXT NOT NULL,

    PRIMARY KEY (project_id, show_id, sequence_id)
) STRICT;
