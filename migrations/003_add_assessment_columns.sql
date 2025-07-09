-- This migration adds new columns to the assessment_results table
-- The table itself should be created by migration 002_create_assessment_results.sql

-- Add assessment summary columns to users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS last_assessment TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS resilience_score FLOAT,
ADD COLUMN IF NOT EXISTS depression_score FLOAT,
ADD COLUMN IF NOT EXISTS anxiety_score FLOAT,
ADD COLUMN IF NOT EXISTS stress_score FLOAT;
