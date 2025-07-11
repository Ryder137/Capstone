-- Create assessment_responses table
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

-- Create game_sessions table
CREATE TABLE IF NOT EXISTS public.game_sessions (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
    game_type text NOT NULL,
    duration_seconds integer NOT NULL,
    score integer,
    completed_at timestamptz DEFAULT now(),
    created_at timestamptz DEFAULT now()
);

-- Create admin_activities table
CREATE TABLE IF NOT EXISTS public.admin_activities (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id uuid REFERENCES auth.users(id) ON DELETE SET NULL,
    action text NOT NULL,
    details text,
    ip_address inet,
    user_agent text,
    created_at timestamptz DEFAULT now()
);

-- Create content table
CREATE TABLE IF NOT EXISTS public.content (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    title text NOT NULL,
    slug text UNIQUE NOT NULL,
    content_type text NOT NULL,
    content_text text,
    content_html text,
    is_published boolean DEFAULT false,
    published_at timestamptz,
    created_by uuid REFERENCES auth.users(id) ON DELETE SET NULL,
    updated_by uuid REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Create RPC function to count users
CREATE OR REPLACE FUNCTION public.count_users()
RETURNS bigint
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT COUNT(*) FROM auth.users;
$$;

-- Set up RLS policies
ALTER TABLE public.assessment_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.game_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.admin_activities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.content ENABLE ROW LEVEL SECURITY;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_assessment_responses_user_id ON public.assessment_responses(user_id);
CREATE INDEX IF NOT EXISTS idx_game_sessions_user_id ON public.game_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_admin_activities_user_id ON public.admin_activities(user_id);
CREATE INDEX IF NOT EXISTS idx_content_published ON public.content(is_published, published_at);

-- Insert initial admin activity
INSERT INTO public.admin_activities (admin_id, activity_type, description, created_at)
SELECT id, 'system', 'Initial admin activity', now()
FROM auth.users
WHERE id = (SELECT id FROM auth.users WHERE raw_user_meta_data->>'role' = 'admin' LIMIT 1)
LIMIT 1;
