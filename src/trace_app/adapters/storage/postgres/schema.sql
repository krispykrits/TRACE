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

CREATE TABLE IF NOT EXISTS trace_workflow_runs (
    investigation_id TEXT PRIMARY KEY REFERENCES trace_jobs(investigation_id),
    attempt_id BIGINT NOT NULL REFERENCES trace_job_attempts(attempt_id),
    phase TEXT NOT NULL,
    outcome TEXT,
    failure_code TEXT
);

CREATE TABLE IF NOT EXISTS trace_snapshots (
    investigation_id TEXT PRIMARY KEY REFERENCES trace_jobs(investigation_id),
    schema_version TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    body TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trace_workflow_artifacts (
    artifact_id TEXT PRIMARY KEY,
    ordinal BIGINT GENERATED ALWAYS AS IDENTITY UNIQUE,
    investigation_id TEXT NOT NULL REFERENCES trace_jobs(investigation_id),
    attempt_id BIGINT NOT NULL REFERENCES trace_job_attempts(attempt_id),
    role TEXT NOT NULL,
    version TEXT NOT NULL,
    sensitivity TEXT NOT NULL,
    metadata TEXT NOT NULL,
    body TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trace_principal_grants (
    tenant_id UUID NOT NULL,
    object_id UUID NOT NULL,
    access_scope TEXT NOT NULL,
    environment TEXT NOT NULL,
    services TEXT[] NOT NULL,
    actions TEXT[] NOT NULL,
    PRIMARY KEY (tenant_id, object_id)
);

CREATE TABLE IF NOT EXISTS trace_execution_runs (
    investigation_id TEXT PRIMARY KEY REFERENCES trace_jobs(investigation_id),
    policy TEXT NOT NULL,
    state TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trace_execution_calls (
    call_id TEXT PRIMARY KEY,
    investigation_id TEXT NOT NULL REFERENCES trace_jobs(investigation_id),
    metadata TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trace_model_budget (
    id INTEGER PRIMARY KEY CHECK (id=1),
    limit_nusd BIGINT NOT NULL CHECK (limit_nusd > 0 AND limit_nusd <= 20000000000),
    pricing TEXT NOT NULL,
    input_rate BIGINT NOT NULL,
    output_rate BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS trace_model_months (
    month TEXT PRIMARY KEY,
    initial_nusd BIGINT NOT NULL CHECK (initial_nusd >= 0)
);

CREATE TABLE IF NOT EXISTS trace_model_attempts (
    request_id TEXT PRIMARY KEY,
    scope_id TEXT NOT NULL,
    month TEXT NOT NULL REFERENCES trace_model_months(month),
    allowance_nusd BIGINT NOT NULL CHECK (allowance_nusd >= 0),
    charged_nusd BIGINT NOT NULL CHECK (charged_nusd >= 0),
    outcome TEXT NOT NULL,
    metadata TEXT NOT NULL,
    dispatched BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS trace_model_redactions (
    request_id TEXT NOT NULL REFERENCES trace_model_attempts(request_id),
    provenance TEXT NOT NULL
);
