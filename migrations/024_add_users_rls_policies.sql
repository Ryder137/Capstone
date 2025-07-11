-- Enable RLS on users table if not already enabled
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Drop all existing policies to avoid conflicts
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'users') THEN
    EXECUTE (SELECT string_agg('DROP POLICY IF EXISTS "' || policyname || '" ON public.users;', ' ')
             FROM pg_policies WHERE tablename = 'users');
  END IF;
END $$;

-- Allow users to view their own profile
CREATE POLICY "Users can view their own profile"
ON public.users
FOR SELECT
USING (auth.uid() = id);

-- Allow users to update their own profile
CREATE POLICY "Users can update their own profile"
ON public.users
FOR UPDATE
USING (auth.uid() = id)
WITH CHECK (auth.uid() = id);

-- Allow service role to access all users (for admin functions)
-- This uses the service role key which bypasses RLS by default
CREATE POLICY "Service role has full access"
ON public.users
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Allow authenticated users to view all users (needed for admin functions)
CREATE POLICY "Allow authenticated users to view all users"
ON public.users
FOR SELECT
TO authenticated
USING (true);

-- Allow authenticated users to insert their own profile (for registration)
-- This assumes your registration flow creates a user record after auth signup
CREATE POLICY "Users can insert their own profile"
ON public.users
FOR INSERT
WITH CHECK (auth.uid() = id);

-- Optional: Allow public access for auth-related operations if needed
-- This is useful for registration flows where the user doesn't exist yet
CREATE POLICY "Public access for registration"
ON public.users
FOR INSERT
TO anon
WITH CHECK (true);

-- Create a function to handle user creation on signup
-- This ensures a user record is created when someone signs up via Supabase Auth
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.users (id, email, created_at, updated_at)
  VALUES (
    NEW.id, 
    NEW.email, 
    NEW.created_at, 
    NEW.updated_at
  )
  ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email,
    updated_at = EXCLUDED.updated_at;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Drop the trigger if it exists
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Create a trigger that fires when a new user signs up
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE ON public.users TO authenticated;

-- Add a comment to document the RLS setup
COMMENT ON TABLE public.users IS 'User profiles with RLS policies for self-service access and admin management';

-- Ensure the function is secure
REVOKE ALL ON FUNCTION public.handle_new_user() FROM PUBLIC;
