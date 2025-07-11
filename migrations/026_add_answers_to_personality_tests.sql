-- First, drop the table if it exists to ensure a clean slate
DROP TABLE IF EXISTS public.personality_tests CASCADE;

-- Then create the table with all required columns
CREATE TABLE public.personality_tests (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    resilience_score FLOAT,
    depression_score FLOAT,
    anxiety_score FLOAT,
    stress_score FLOAT,
    overall_score FLOAT,
    level TEXT,
    recommendation TEXT,
    answers JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add comment to the table
COMMENT ON TABLE public.personality_tests IS 'Stores personality test results for users';

-- Create an index on user_id for better query performance
CREATE INDEX IF NOT EXISTS idx_personality_tests_user_id ON public.personality_tests(user_id);

-- Update RLS policies to include the new columns
DO $$
BEGIN
  -- Drop existing policies first to avoid conflicts
  IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'personality_tests') THEN
    EXECUTE (SELECT string_agg('DROP POLICY IF EXISTS "' || policyname || '" ON public.personality_tests;', ' ')
             FROM pg_policies WHERE tablename = 'personality_tests');
  END IF;

  -- Recreate policies with updated column list
  EXECUTE '
    -- Allow users to view their own test results
    CREATE POLICY "Users can view their own test results"
    ON public.personality_tests
    FOR SELECT
    USING (auth.uid() = user_id);

    -- Allow users to insert their own test results
    CREATE POLICY "Users can insert their own test results"
    ON public.personality_tests
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

    -- Allow service role full access (for admin functions)
    CREATE POLICY "Service role has full access to test results"
    ON public.personality_tests
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

    -- Allow authenticated users to view all test results (for admin dashboard)
    CREATE POLICY "Allow authenticated users to view all test results"
    ON public.personality_tests
    FOR SELECT
    TO authenticated
    USING (true);
  ';
END;
$$ LANGUAGE plpgsql;
