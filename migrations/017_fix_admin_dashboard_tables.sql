-- =============================================
-- Create admin_activities table if not exists
-- =============================================
CREATE TABLE IF NOT EXISTS public.admin_activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    activity_type TEXT NOT NULL,
    description TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enable RLS on admin_activities
ALTER TABLE public.admin_activities ENABLE ROW LEVEL SECURITY;

-- Create indexes for admin_activities
CREATE INDEX IF NOT EXISTS idx_admin_activities_admin_id ON public.admin_activities(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_activities_activity_type ON public.admin_activities(activity_type);

-- Create policies for admin_activities
CREATE POLICY "Admins can view all activities"
ON public.admin_activities
FOR SELECT
USING (EXISTS (
    SELECT 1 FROM auth.users 
    WHERE id = auth.uid() AND raw_user_meta_data->>'is_admin' = 'true'
));

CREATE POLICY "Admins can insert activities"
ON public.admin_activities
FOR INSERT
WITH CHECK (EXISTS (
    SELECT 1 FROM auth.users 
    WHERE id = auth.uid() AND raw_user_meta_data->>'is_admin' = 'true'
));

-- =============================================
-- Create game_sessions table if not exists
-- =============================================
CREATE TABLE IF NOT EXISTS public.game_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    game_type TEXT NOT NULL,
    score INTEGER,
    duration_seconds INTEGER,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enable RLS on game_sessions
ALTER TABLE public.game_sessions ENABLE ROW LEVEL SECURITY;

-- Create indexes for game_sessions
CREATE INDEX IF NOT EXISTS idx_game_sessions_user_id ON public.game_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_game_sessions_game_type ON public.game_sessions(game_type);

-- Create policies for game_sessions
CREATE POLICY "Users can view their own game sessions"
ON public.game_sessions
FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own game sessions"
ON public.game_sessions
FOR INSERT
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Admins have full access to game sessions"
ON public.game_sessions
FOR ALL
USING (EXISTS (
    SELECT 1 FROM auth.users 
    WHERE id = auth.uid() AND raw_user_meta_data->>'is_admin' = 'true'
));

-- =============================================
-- Create assessment_responses table if not exists
-- =============================================
CREATE TABLE IF NOT EXISTS public.assessment_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    assessment_id UUID NOT NULL REFERENCES public.assessments(id) ON DELETE CASCADE,
    question_id TEXT NOT NULL,
    response TEXT,
    score INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Indexes
    CONSTRAINT fk_assessment_response_user FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE,
    CONSTRAINT fk_assessment FOREIGN KEY (assessment_id) REFERENCES public.assessments(id) ON DELETE CASCADE
);

-- Create indexes for assessment_responses
CREATE INDEX IF NOT EXISTS idx_assessment_responses_user_id ON public.assessment_responses(user_id);
CREATE INDEX IF NOT EXISTS idx_assessment_responses_assessment_id ON public.assessment_responses(assessment_id);

-- Enable RLS on assessment_responses
ALTER TABLE public.assessment_responses ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DO $$
BEGIN
    -- Drop policies if they exist
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'assessment_responses' AND policyname = 'Users can view their own assessment responses') THEN
        DROP POLICY "Users can view their own assessment responses" ON public.assessment_responses;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'assessment_responses' AND policyname = 'Users can create their own assessment responses') THEN
        DROP POLICY "Users can create their own assessment responses" ON public.assessment_responses;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'assessment_responses' AND policyname = 'Users can update their own assessment responses') THEN
        DROP POLICY "Users can update their own assessment responses" ON public.assessment_responses;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'assessment_responses' AND policyname = 'Users can delete their own assessment responses') THEN
        DROP POLICY "Users can delete their own assessment responses" ON public.assessment_responses;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'assessment_responses' AND policyname = 'Admins have full access to assessment responses') THEN
        DROP POLICY "Admins have full access to assessment responses" ON public.assessment_responses;
    END IF;
END $$;

-- Users can view their own assessment responses
CREATE POLICY "Users can view their own assessment responses"
ON public.assessment_responses
FOR SELECT
USING (auth.uid() = user_id);

-- Users can insert their own assessment responses
CREATE POLICY "Users can create their own assessment responses"
ON public.assessment_responses
FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Users can update their own assessment responses
CREATE POLICY "Users can update their own assessment responses"
ON public.assessment_responses
FOR UPDATE
USING (auth.uid() = user_id);

-- Users can delete their own assessment responses
CREATE POLICY "Users can delete their own assessment responses"
ON public.assessment_responses
FOR DELETE
USING (auth.uid() = user_id);

-- Admins can do anything with assessment responses
CREATE POLICY "Admins have full access to assessment responses"
ON public.assessment_responses
FOR ALL
USING (EXISTS (
    SELECT 1 FROM auth.users 
    WHERE id = auth.uid() AND raw_user_meta_data->>'is_admin' = 'true'
));

-- Grant necessary permissions on assessment_responses
GRANT SELECT, INSERT, UPDATE, DELETE ON public.assessment_responses TO authenticated;

-- =============================================
-- Create views for admin dashboard
-- =============================================

-- View for admin activities with user information
CREATE OR REPLACE VIEW public.admin_activities_view AS
SELECT 
    aa.*,
    u.email as admin_email,
    COALESCE(u.raw_user_meta_data->>'full_name', u.email) as admin_name
FROM 
    public.admin_activities aa
JOIN 
    auth.users u ON aa.admin_id = u.id;

-- Grant permissions on the view
GRANT SELECT ON public.admin_activities_view TO authenticated;

-- Create a function to log admin activities
CREATE OR REPLACE FUNCTION public.log_admin_activity(
    p_admin_id UUID,
    p_activity_type TEXT,
    p_description TEXT,
    p_metadata JSONB DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_activity_id UUID;
BEGIN
    INSERT INTO public.admin_activities (
        admin_id, 
        activity_type, 
        description, 
        metadata
    ) VALUES (
        p_admin_id,
        p_activity_type,
        p_description,
        p_metadata
    )
    RETURNING id INTO v_activity_id;
    
    RETURN v_activity_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission on the function
GRANT EXECUTE ON FUNCTION public.log_admin_activity(UUID, TEXT, TEXT, JSONB) TO authenticated;

-- =============================================
-- Insert test data for development
-- =============================================
DO $$
BEGIN
    -- Only insert test data in development environment
    IF current_setting('app.env', true) = 'development' THEN
        -- Insert test admin activities
        INSERT INTO public.admin_activities (admin_id, activity_type, description, metadata)
        SELECT 
            id, 
            'login', 
            'Admin user logged in', 
            jsonb_build_object('ip', '127.0.0.1', 'user_agent', 'Test User Agent')
        FROM auth.users 
        WHERE raw_user_meta_data->>'is_admin' = 'true'
        LIMIT 1;
        
        -- Insert test game sessions
        INSERT INTO public.game_sessions (user_id, game_type, score, duration_seconds, metadata)
        SELECT 
            id, 
            'memory', 
            100, 
            300, 
            jsonb_build_object('level', 5, 'difficulty', 'medium')
        FROM auth.users 
        WHERE raw_user_meta_data->>'is_admin' = 'true'
        LIMIT 1;
        
        -- Insert test assessment responses
        INSERT INTO public.assessment_responses (user_id, assessment_id, question_id, response, score)
        SELECT 
            u.id, 
            a.id, 
            'question_1', 
            'Test response', 
            5
        FROM auth.users u
        CROSS JOIN (SELECT id FROM public.assessments LIMIT 1) a
        WHERE u.raw_user_meta_data->>'is_admin' = 'true'
        LIMIT 1;
    END IF;
END $$;
