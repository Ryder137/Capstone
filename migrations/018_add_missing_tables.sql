-- Create game_sessions table
CREATE TABLE IF NOT EXISTS public.game_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    game_type TEXT NOT NULL,
    score INTEGER,
    duration_seconds INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create assessment_responses table
CREATE TABLE IF NOT EXISTS public.assessment_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    assessment_type TEXT NOT NULL,
    score INTEGER,
    responses JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create admin_activities table
CREATE TABLE IF NOT EXISTS public.admin_activities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    details TEXT,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS on all tables
ALTER TABLE public.game_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assessment_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.admin_activities ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for game_sessions
CREATE POLICY "Users can view their own game sessions" 
    ON public.game_sessions 
    FOR SELECT 
    USING (auth.uid() = user_id);

-- Create RLS policies for assessment_responses
CREATE POLICY "Users can view their own assessment responses" 
    ON public.assessment_responses 
    FOR SELECT 
    USING (auth.uid() = user_id);

-- Create RLS policies for admin_activities
CREATE POLICY "Admins can view all activities" 
    ON public.admin_activities 
    FOR SELECT 
    USING (EXISTS (
        SELECT 1 FROM auth.users 
        WHERE id = auth.uid() AND raw_user_meta_data->>'role' = 'admin'
    ));

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_game_sessions_user_id ON public.game_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_assessment_responses_user_id ON public.assessment_responses(user_id);
CREATE INDEX IF NOT EXISTS idx_admin_activities_user_id ON public.admin_activities(user_id);
CREATE INDEX IF NOT EXISTS idx_admin_activities_created_at ON public.admin_activities(created_at);
