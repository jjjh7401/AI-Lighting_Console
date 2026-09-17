-- SPEC-LDRECV-001 M6 — 운영 중단·recovery (계약 §10 · REQ-LDPLUGIN-032).
--
-- recovery 흐름은 원본 execution 행을 고치지 않는다(불변) — 새 execution 을 만들고
-- 이 별도 테이블에 "어느 recovery 가 어느 원본을 잇는가"만 기록한다. 001/002 와
-- 같은 `CREATE TABLE IF NOT EXISTS` 관례를 그대로 따른다 — `ALTER TABLE` 로 기존
-- `executions` 행에 컬럼을 더하지 않는다. 이렇게 하면 원본 행이 물리적으로 한
-- 바이트도 바뀌지 않는다는 것이 스키마 수준에서 보장된다(AC-LDPLUGIN-032 항목4
-- "원본 execution 기록은 불변으로 남고" — 애초에 덮어쓸 컬럼 자체가 없다).
--
-- `IF NOT EXISTS` 이므로 `ExecutionJournal._migrate()` 가 매 연결마다 001+002+003
-- 을 순서대로 재적용해도 안전하다(002 자신의 관례와 동일 — ALTER TABLE 이었다면
-- 두 번째 오픈에서 "duplicate column" 으로 깨졌을 것이다).

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS execution_recovery_links (
    recovery_execution_id TEXT NOT NULL PRIMARY KEY,
    original_execution_id TEXT NOT NULL,
    created_at             TEXT NOT NULL,

    FOREIGN KEY (recovery_execution_id) REFERENCES executions (execution_id),
    FOREIGN KEY (original_execution_id) REFERENCES executions (execution_id)
) STRICT;

CREATE INDEX IF NOT EXISTS execution_recovery_links_by_original
    ON execution_recovery_links (original_execution_id);
