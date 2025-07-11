-- Migration to rename assessments table to personality_tests

-- Rename the table
ALTER TABLE IF EXISTS public.assessments RENAME TO personality_tests;

-- Rename the sequence if it exists
ALTER SEQUENCE IF EXISTS public.assessments_id_seq RENAME TO personality_tests_id_seq;

-- Update any foreign key constraints
-- Note: You'll need to replace 'constraint_name' with the actual constraint name
-- You can find the constraint name with: \d+ assessments
-- ALTER TABLE public.other_table RENAME CONSTRAINT constraint_name TO new_constraint_name;

-- Update any indexes
ALTER INDEX IF EXISTS public.assessments_pkey RENAME TO personality_tests_pkey;
ALTER INDEX IF EXISTS public.idx_assessments_user_id RENAME TO idx_personality_tests_user_id;

-- Update any views, functions, or triggers that reference the table
-- Example:
-- CREATE OR REPLACE VIEW public.view_name AS SELECT * FROM public.personality_tests;

-- Update RLS policies if they exist
-- DROP POLICY IF EXISTS policy_name ON public.assessments;
-- CREATE POLICY policy_name ON public.personality_tests ...

-- Update any triggers
-- DROP TRIGGER IF EXISTS trigger_name ON public.assessments;
-- CREATE TRIGGER trigger_name ... ON public.personality_tests ...

-- Update any functions that reference the table
-- CREATE OR REPLACE FUNCTION public.function_name() ...
--   ...
--   SELECT * FROM public.personality_tests ...
--   ...
-- $$ LANGUAGE sql;

-- Add a comment to document the change
COMMENT ON TABLE public.personality_tests IS 'Stores user personality test results (previously named assessments)';

-- Update any default privileges
-- GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.personality_tests TO role_name;

-- Drop and recreate any views that depend on this table
-- DROP VIEW IF EXISTS public.dependent_view;
-- CREATE VIEW public.dependent_view AS ...

-- Update any materialized views
-- REFRESH MATERIALIZED VIEW public.materialized_view_name;
