-- Migration: Add review workflow and upload tracking fields
-- Date: 2024-12-02
-- Description: Adds columns to ai_processing_results for review workflow and upload tracking,
--              plus creates batch_processing_runs and upload_history tables

-- Add review workflow columns to ai_processing_results
ALTER TABLE ai_processing_results ADD COLUMN review_status TEXT DEFAULT 'pending';
ALTER TABLE ai_processing_results ADD COLUMN reviewed_at TIMESTAMP;
ALTER TABLE ai_processing_results ADD COLUMN reviewed_by TEXT;
ALTER TABLE ai_processing_results ADD COLUMN review_notes TEXT;

-- Add upload tracking columns to ai_processing_results
ALTER TABLE ai_processing_results ADD COLUMN upload_status TEXT DEFAULT 'pending';
ALTER TABLE ai_processing_results ADD COLUMN uploaded_at TIMESTAMP;
ALTER TABLE ai_processing_results ADD COLUMN upload_error TEXT;
ALTER TABLE ai_processing_results ADD COLUMN upload_attempts INTEGER DEFAULT 0;

-- Add batch metadata columns to ai_processing_results
ALTER TABLE ai_processing_results ADD COLUMN batch_id TEXT;
ALTER TABLE ai_processing_results ADD COLUMN batch_timestamp TIMESTAMP;

-- Create batch_processing_runs table
CREATE TABLE IF NOT EXISTS batch_processing_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_id TEXT UNIQUE NOT NULL,
  start_date TEXT NOT NULL,
  end_date TEXT NOT NULL,
  total_notes INTEGER DEFAULT 0,
  processed_notes INTEGER DEFAULT 0,
  success_count INTEGER DEFAULT 0,
  needs_review_count INTEGER DEFAULT 0,
  failed_count INTEGER DEFAULT 0,
  duplicate_count INTEGER DEFAULT 0,
  skipped_count INTEGER DEFAULT 0,
  total_tokens_used INTEGER DEFAULT 0,
  processing_duration_ms INTEGER,
  status TEXT DEFAULT 'running',
  error_message TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  completed_at TIMESTAMP
);

-- Create upload_history table
CREATE TABLE IF NOT EXISTS upload_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  processing_result_id INTEGER NOT NULL,
  batch_id TEXT,
  patient_name TEXT NOT NULL,
  visit_date TEXT,
  upload_status TEXT NOT NULL,
  error_message TEXT,
  attempt_number INTEGER DEFAULT 1,
  osmind_note_found BOOLEAN DEFAULT 0,
  note_was_signed BOOLEAN DEFAULT 0,
  content_appended BOOLEAN DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (processing_result_id) REFERENCES ai_processing_results(id) ON DELETE CASCADE
);

-- Create index on review_status for faster queries
CREATE INDEX IF NOT EXISTS idx_ai_processing_results_review_status
ON ai_processing_results(review_status);

-- Create index on upload_status for faster queries
CREATE INDEX IF NOT EXISTS idx_ai_processing_results_upload_status
ON ai_processing_results(upload_status);

-- Create index on batch_id for faster queries
CREATE INDEX IF NOT EXISTS idx_ai_processing_results_batch_id
ON ai_processing_results(batch_id);

-- Create index on batch_id in upload_history
CREATE INDEX IF NOT EXISTS idx_upload_history_batch_id
ON upload_history(batch_id);

-- Create index on processing_result_id in upload_history
CREATE INDEX IF NOT EXISTS idx_upload_history_processing_result_id
ON upload_history(processing_result_id);
