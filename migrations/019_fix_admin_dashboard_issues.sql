-- Create the missing count_users function
CREATE OR REPLACE FUNCTION public.count_users()
RETURNS integer
LANGUAGE sql
AS $$
  SELECT COUNT(*)::integer FROM auth.users;
$$;

-- Add raw_user_meta_data column to users table if it doesn't exist
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                 WHERE table_schema = 'public' 
                 AND table_name = 'users' 
                 AND column_name = 'raw_user_meta_data') THEN
    ALTER TABLE public.users ADD COLUMN raw_user_meta_data jsonb DEFAULT '{}'::jsonb;
  END IF;
END
$$;

-- Create the assessment_responses table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.assessment_responses (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
    assessment_id uuid NOT NULL,
    responses jsonb NOT NULL,
    score integer,
    completed_at timestamptz DEFAULT now(),
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Create the admin_activities table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.admin_activities (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id uuid REFERENCES auth.users(id) ON DELETE SET NULL,
    action text NOT NULL,
    details text,
    ip_address inet,
    user_agent text,
    created_at timestamptz DEFAULT now()
);

-- Grant necessary permissions
GRANT EXECUTE ON FUNCTION public.count_users() TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.assessment_responses TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.admin_activities TO service_role;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_assessment_responses_user_id ON public.assessment_responses(user_id);
CREATE INDEX IF NOT EXISTS idx_admin_activities_created_at ON public.admin_activities(created_at);
