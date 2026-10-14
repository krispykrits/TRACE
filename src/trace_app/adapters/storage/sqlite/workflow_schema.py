"""SQLite-only schema extension, separate to avoid adapter composition cycles."""

WORKFLOW_SCHEMA = (
    """CREATE TABLE workflow_runs (
        investigation_id TEXT PRIMARY KEY REFERENCES investigations(investigation_id) ON DELETE CASCADE,
        attempt_id INTEGER NOT NULL REFERENCES attempts(attempt_id) ON DELETE CASCADE,
        phase TEXT NOT NULL, outcome TEXT, failure_code TEXT
    )""",
    """CREATE TABLE workflow_artifacts (
        artifact_id TEXT PRIMARY KEY,
        investigation_id TEXT NOT NULL REFERENCES investigations(investigation_id) ON DELETE CASCADE,
        attempt_id INTEGER NOT NULL REFERENCES attempts(attempt_id) ON DELETE CASCADE,
        role TEXT NOT NULL, version TEXT NOT NULL, sensitivity TEXT NOT NULL,
        metadata TEXT NOT NULL, body TEXT NOT NULL
    )""",
)
