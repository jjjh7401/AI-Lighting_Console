-- SPEC-LDSTORE-001 M1 — Director 저장소 최초 스키마 (계약 §9.7 · §10).
--
-- 계약 §10: "SQLite(stdlib sqlite3)를 revision/CAS/idempotency/approval/execution
-- journal 의 transaction 원본으로 사용한다."
--
-- 이 마이그레이션은 M1 범위인 **plan revision + idempotency** 만 만든다. approval 과
-- execution journal 은 형제 SPEC-LDRECV-001 의 것이므로 여기서 만들지 않는다 — 미리
-- 만들면 그 SPEC 이 실제 요구를 확인하기 전에 형태가 굳는다.

PRAGMA foreign_keys = ON;

-- 불변 plan revision. 한 (project, plan, revision) 은 한 번만 쓰이고 절대 갱신되지 않는다.
-- UPDATE 를 쓰지 않는 것이 불변성의 구현이다 — 애플리케이션 규율이 아니라 접근 패턴이다.
CREATE TABLE IF NOT EXISTS plan_revisions (
    project_id     TEXT    NOT NULL,
    plan_id        TEXT    NOT NULL,
    revision       INTEGER NOT NULL,

    -- 제출된 LightingPlan 의 **원문 JSON**. 서버가 재직렬화한 값이 아니라 제출 그대로다
    -- (계약 §3: "plan 은 제출 그대로이며 base_revision 을 서버 revision 으로
    -- 덮어쓰지 않는다"). 되읽을 때 이 bytes 를 그대로 파싱해 돌려준다.
    plan_json      BLOB    NOT NULL,

    -- sha256(UTF-8(JCS(plan))) — 계약 §9.2.
    plan_digest    TEXT    NOT NULL,

    -- 제출자가 선언한 base_revision. plan_json 안에도 있지만 CAS 질의에서 쓰려고 꺼내 둔다.
    base_revision  INTEGER NOT NULL,

    -- 계약 §10 의 PlanState. M1 이 도달하는 것은 submitted 와 needs_revision 뿐이다 —
    -- ready_for_review 는 실제 검증기(SPEC-LDCOMPILE-001)가 끼워질 때 처음 나온다.
    state          TEXT    NOT NULL,

    created_at     TEXT    NOT NULL,

    -- CAS 의 실체. 같은 revision 을 두 번 쓰려는 두 번째 시도가 여기서 막힌다.
    PRIMARY KEY (project_id, plan_id, revision)
) STRICT;

CREATE INDEX IF NOT EXISTS plan_revisions_head
    ON plan_revisions (project_id, plan_id, revision DESC);

-- 멱등 key (계약 §9.7).
--
-- unique 는 (project_id, principal_id, operation, idempotency_key) 다 — key 만으로는
-- 안 된다. 다른 principal 이 같은 key 를 골랐을 때 남의 결과를 replay 받으면 안 된다.
--
-- request_fingerprint 는 sha256(JCS({operation, project_id, principal_id, request})) 이고
-- request 는 body 에서 idempotency_key 만 제거한 객체다. 같은 key + 같은 fingerprint 는
-- 최초 결과 replay, 같은 key + 다른 fingerprint 는 IDEMPOTENCY_CONFLICT 다.
CREATE TABLE IF NOT EXISTS idempotency_keys (
    project_id          TEXT    NOT NULL,
    principal_id        TEXT    NOT NULL,
    operation           TEXT    NOT NULL,
    idempotency_key     TEXT    NOT NULL,

    request_fingerprint TEXT    NOT NULL,

    -- replay 할 대상. 계약 §10: "최초 저장한 status 와 body 를 그대로 replay 한다."
    result_plan_id      TEXT    NOT NULL,
    result_revision     INTEGER NOT NULL,
    result_status       INTEGER NOT NULL,

    created_at          TEXT    NOT NULL,

    PRIMARY KEY (project_id, principal_id, operation, idempotency_key),
    FOREIGN KEY (project_id, result_plan_id, result_revision)
        REFERENCES plan_revisions (project_id, plan_id, revision)
) STRICT;
