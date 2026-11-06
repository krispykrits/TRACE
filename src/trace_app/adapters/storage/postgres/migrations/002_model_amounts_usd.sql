-- Apply after all workers support both the old and new amount columns.
BEGIN;
DROP VIEW IF EXISTS trace_model_accounting;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid='trace_model_attempts'::regclass
               AND attname='charged_nusd' AND NOT attisdropped)
       AND NOT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid='trace_model_attempts'::regclass
                       AND attname='budgeted_nusd' AND NOT attisdropped) THEN
        ALTER TABLE trace_model_attempts RENAME COLUMN charged_nusd TO budgeted_nusd;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid='trace_model_attempts'::regclass
               AND attname='budgeted_nusd' AND NOT attisdropped) THEN
        ALTER TABLE trace_model_attempts RENAME COLUMN budgeted_nusd TO budgeted_usd;
        ALTER TABLE trace_model_attempts ALTER COLUMN budgeted_usd TYPE NUMERIC(29,9)
            USING budgeted_usd::numeric / 1000000000;
        ALTER TABLE trace_model_attempts RENAME COLUMN allowance_nusd TO allowance_usd;
        ALTER TABLE trace_model_attempts ALTER COLUMN allowance_usd TYPE NUMERIC(29,9)
            USING allowance_usd::numeric / 1000000000;
    END IF;
END $$;
CREATE VIEW trace_model_accounting AS
SELECT request_id, scope_id, month, outcome, budgeted_usd,
       CASE WHEN metadata::jsonb ->> 'estimated_cost_usd' IS NULL
                  AND metadata::jsonb ->> 'estimated_cost_nusd' IS NULL THEN budgeted_usd
            ELSE GREATEST(budgeted_usd - COALESCE((metadata::jsonb ->> 'estimated_cost_usd')::numeric,
                         (metadata::jsonb ->> 'estimated_cost_nusd')::numeric / 1000000000), 0)
       END AS reserved_usd,
       COALESCE((metadata::jsonb ->> 'estimated_cost_usd')::numeric,
                (metadata::jsonb ->> 'estimated_cost_nusd')::numeric / 1000000000) AS estimated_cost_usd,
       NULL::numeric AS actual_billed_usd,
       (metadata::jsonb ->> 'worker_started')::boolean AS worker_started,
       (metadata::jsonb ->> 'request_sent')::boolean AS request_sent
FROM trace_model_attempts;
COMMIT;
