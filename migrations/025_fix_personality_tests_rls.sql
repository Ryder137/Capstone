-- Enable RLS on personality_tests table if not already enabled
ALTER TABLE public.personality_tests ENABLE ROW LEVEL SECURITY;

-- Drop all existing policies to avoid conflicts
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'personality_tests') THEN
    EXECUTE (SELECT string_agg('DROP POLICY IF EXISTS "' || policyname || '" ON public.personality_tests;', ' ')
             FROM pg_policies WHERE tablename = 'personality_tests');
  END IF;
END $$;

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
