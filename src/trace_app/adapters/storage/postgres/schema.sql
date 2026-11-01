CREATE TABLE IF NOT EXISTS trace_jobs (
    investigation_id TEXT PRIMARY KEY,
    submitted_tenant UUID NOT NULL,
    submitted_object UUID NOT NULL,
    access_scope TEXT NOT NULL,
    submission_key TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    service TEXT NOT NULL,
    environment TEXT NOT NULL,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    expires_at TEXT,
    max_attempts INTEGER NOT NULL CHECK (max_attempts = 1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled', 'expired')),
    assessment_status TEXT NOT NULL DEFAULT 'pending',
    review_status TEXT NOT NULL DEFAULT 'pending',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    active_attempt_id BIGINT,
    lease_until TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    failure_code TEXT,
    UNIQUE (access_scope, submission_key)
);

CREATE TABLE IF NOT EXISTS trace_job_attempts (
    attempt_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    investigation_id TEXT NOT NULL REFERENCES trace_jobs(investigation_id),
    started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    lease_until TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    outcome TEXT NOT NULL CHECK (outcome IN ('running', 'completed', 'failed', 'cancelled', 'interrupted'))
);

CREATE INDEX IF NOT EXISTS trace_jobs_queue_idx ON trace_jobs(status, created_at, investigation_id);

CREATE TABLE IF NOT EXISTS trace_principal_grants (
    tenant_id UUID NOT NULL,
    object_id UUID NOT NULL,
    access_scope TEXT NOT NULL,
    environment TEXT NOT NULL,
    services TEXT[] NOT NULL,
    actions TEXT[] NOT NULL,
    PRIMARY KEY (tenant_id, object_id)
);
