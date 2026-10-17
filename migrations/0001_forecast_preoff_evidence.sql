-- Apply explicitly with Wrangler to the intended D1 environment before enabling ingestion.
-- No existing race tables are modified.
CREATE TABLE IF NOT EXISTS forecast_preoff_evidence (
  capture_id TEXT PRIMARY KEY,
  race_id TEXT NOT NULL,
  feature_hash TEXT NOT NULL,
  receipt_hash TEXT NOT NULL,
  snapshot_json TEXT NOT NULL,
  receipt_json TEXT NOT NULL,
  captured_at_epoch INTEGER NOT NULL,
  stored_at_epoch INTEGER NOT NULL,
  post_at_epoch INTEGER NOT NULL,
  UNIQUE(race_id, feature_hash, captured_at_epoch)
);
CREATE INDEX IF NOT EXISTS idx_forecast_evidence_race_time
 ON forecast_preoff_evidence(race_id, captured_at_epoch);
CREATE TRIGGER IF NOT EXISTS prevent_forecast_evidence_update
 BEFORE UPDATE ON forecast_preoff_evidence
 BEGIN SELECT RAISE(ABORT, 'append-only evidence cannot be updated'); END;
CREATE TRIGGER IF NOT EXISTS prevent_forecast_evidence_delete
 BEFORE DELETE ON forecast_preoff_evidence
 BEGIN SELECT RAISE(ABORT, 'append-only evidence cannot be deleted'); END;
