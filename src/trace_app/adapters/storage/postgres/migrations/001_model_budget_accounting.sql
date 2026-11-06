-- Run after deploying a version that supports both column names.
-- Existing amounts remain counted against the same budget.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid='trace_model_attempts'::regclass
               AND attname='charged_nusd' AND NOT attisdropped)
       AND EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid='trace_model_attempts'::regclass
                   AND attname='budgeted_nusd' AND NOT attisdropped) THEN
        RAISE EXCEPTION 'Both model budget columns exist; reconcile before migrating';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid='trace_model_attempts'::regclass
               AND attname='charged_nusd' AND NOT attisdropped)
       AND NOT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid='trace_model_attempts'::regclass
                       AND attname='budgeted_nusd' AND NOT attisdropped) THEN
        ALTER TABLE trace_model_attempts RENAME COLUMN charged_nusd TO budgeted_nusd;
    END IF;
END $$;

CREATE OR REPLACE VIEW trace_model_accounting AS
SELECT request_id, scope_id, month, outcome,
       budgeted_nusd,
       CASE WHEN metadata::jsonb ->> 'estimated_cost_nusd' IS NULL THEN budgeted_nusd
            ELSE GREATEST(budgeted_nusd - (metadata::jsonb ->> 'estimated_cost_nusd')::bigint, 0)
       END AS reserved_nusd,
       (metadata::jsonb ->> 'estimated_cost_nusd')::bigint AS estimated_cost_nusd,
       NULL::bigint AS actual_billed_nusd,
       (metadata::jsonb ->> 'worker_started')::boolean AS worker_started,
       (metadata::jsonb ->> 'request_sent')::boolean AS request_sent
FROM trace_model_attempts;
