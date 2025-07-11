-- Drop existing tables if they exist (for clean migration)
DROP TABLE IF EXISTS public.assessments CASCADE;
DROP TABLE IF EXISTS public.game_sessions CASCADE;
DROP TABLE IF EXISTS public.journal_entries CASCADE;
DROP TABLE IF EXISTS public.admin_activities CASCADE;

-- Drop existing functions
DROP FUNCTION IF EXISTS public.execute_sql(TEXT) CASCADE;

-- Create assessments table
CREATE TABLE IF NOT EXISTS public.assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Assessment details
    assessment_type TEXT NOT NULL,
    score FLOAT NOT NULL,
    max_score FLOAT NOT NULL,
    completed BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Additional metadata
    metadata JSONB,
    
    -- Indexes
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Create game_sessions table if not exists
CREATE TABLE IF NOT EXISTS public.game_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Game session details
    game_type TEXT NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    duration_seconds INTEGER NOT NULL DEFAULT 0,
    level INTEGER,
    metadata JSONB,
    
    -- Indexes
    CONSTRAINT fk_user_game_session FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Create journal_entries table if not exists
CREATE TABLE IF NOT EXISTS public.journal_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Journal entry details
    title TEXT,
    content TEXT NOT NULL,
    mood TEXT,
    tags TEXT[],
    is_private BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB,
    
    -- Indexes
    CONSTRAINT fk_user_journal FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Add RLS policies for journal_entries
ALTER TABLE public.journal_entries ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DO $$
BEGIN
    -- Drop policies with different naming patterns
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'journal_entries' AND policyname = 'Users can view own journal entries') THEN
        DROP POLICY "Users can view own journal entries" ON public.journal_entries;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'journal_entries' AND policyname = 'Users can insert own journal entries') THEN
        DROP POLICY "Users can insert own journal entries" ON public.journal_entries;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'journal_entries' AND policyname = 'Users can update own journal entries') THEN
        DROP POLICY "Users can update own journal entries" ON public.journal_entries;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'journal_entries' AND policyname = 'Users can delete own journal entries') THEN
        DROP POLICY "Users can delete own journal entries" ON public.journal_entries;
    END IF;
    
    -- Also drop any policies with the new naming pattern that might exist
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'journal_entries' AND policyname = 'Users can view their own journal entries') THEN
        DROP POLICY "Users can view their own journal entries" ON public.journal_entries;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'journal_entries' AND policyname = 'Users can create their own journal entries') THEN
        DROP POLICY "Users can create their own journal entries" ON public.journal_entries;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'journal_entries' AND policyname = 'Users can update their own journal entries') THEN
        DROP POLICY "Users can update their own journal entries" ON public.journal_entries;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'journal_entries' AND policyname = 'Users can delete their own journal entries') THEN
        DROP POLICY "Users can delete their own journal entries" ON public.journal_entries;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'journal_entries' AND policyname = 'Admins have full access to journal entries') THEN
        DROP POLICY "Admins have full access to journal entries" ON public.journal_entries;
    END IF;
END $$;

-- Users can view their own journal entries
CREATE POLICY "Users can view their own journal entries"
ON public.journal_entries
FOR SELECT
USING (auth.uid() = user_id);

-- Users can insert their own journal entries
CREATE POLICY "Users can create their own journal entries"
ON public.journal_entries
FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Users can update their own journal entries
CREATE POLICY "Users can update their own journal entries"
ON public.journal_entries
FOR UPDATE
USING (auth.uid() = user_id);

-- Users can delete their own journal entries
CREATE POLICY "Users can delete their own journal entries"
ON public.journal_entries
FOR DELETE
USING (auth.uid() = user_id);

-- Admins can do anything with journal entries
CREATE POLICY "Admins have full access to journal entries"
ON public.journal_entries
FOR ALL
USING (EXISTS (
    SELECT 1 FROM auth.users 
    WHERE id = auth.uid() AND raw_user_meta_data->>'is_admin' = 'true'
));

-- Create indexes for journal_entries
CREATE INDEX IF NOT EXISTS idx_journal_entries_user_id ON public.journal_entries(user_id);
CREATE INDEX IF NOT EXISTS idx_journal_entries_created_at ON public.journal_entries(created_at);
CREATE INDEX IF NOT EXISTS idx_journal_entries_mood ON public.journal_entries(mood);

-- Grant necessary permissions on journal_entries
GRANT SELECT, INSERT, UPDATE, DELETE ON public.journal_entries TO authenticated;

-- Create admin_activities table
CREATE TABLE IF NOT EXISTS public.admin_activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    activity_type TEXT NOT NULL,
    description TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Indexes
    CONSTRAINT fk_admin FOREIGN KEY (admin_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Create a function to safely execute SQL (replacement for missing execute_sql)
CREATE OR REPLACE FUNCTION public.execute_sql(query TEXT) 
RETURNS JSONB 
LANGUAGE plpgsql 
SECURITY DEFINER
AS $$
DECLARE
    result JSONB;
    query_result RECORD;
    column_name TEXT;
    column_value TEXT;
    json_result JSONB := '{}'::JSONB;
BEGIN
    -- First try to execute as a query
    BEGIN
        EXECUTE query INTO query_result;
        
        -- Convert the result to JSON
        IF FOUND THEN
            -- Get the first column value if it's a single column
            FOR column_name, column_value IN 
                SELECT a.attname, query_result::TEXT 
                FROM pg_attribute a 
                WHERE a.attrelid = (SELECT typrelid FROM pg_type WHERE typname = 'record') 
                AND a.attnum > 0 
                LIMIT 1
            LOOP
                json_result := jsonb_build_object(column_name, column_value);
            END LOOP;
            RETURN json_result;
        ELSE
            RETURN jsonb_build_object('message', 'No data found');
        END IF;
    EXCEPTION WHEN OTHERS THEN
        -- If it's not a SELECT query, try to execute it as a command
        BEGIN
            EXECUTE query;
            RETURN jsonb_build_object('message', 'Command executed successfully');
        EXCEPTION WHEN OTHERS THEN
            RETURN jsonb_build_object(
                'error', SQLERRM,
                'state', SQLSTATE,
                'context', 'Failed to execute query: ' || query
            );
        END;
    END;
END;
$$;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_assessments_user_id ON public.assessments(user_id);
CREATE INDEX IF NOT EXISTS idx_assessments_created_at ON public.assessments(created_at);

-- Add RLS policies for assessments
ALTER TABLE public.assessments ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DO $$
BEGIN
    -- Drop policies if they exist
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'assessments' AND policyname = 'Users can view their own assessments') THEN
        DROP POLICY "Users can view their own assessments" ON public.assessments;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'assessments' AND policyname = 'Users can create their own assessments') THEN
        DROP POLICY "Users can create their own assessments" ON public.assessments;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'assessments' AND policyname = 'Users can update their own assessments') THEN
        DROP POLICY "Users can update their own assessments" ON public.assessments;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'assessments' AND policyname = 'Users can delete their own assessments') THEN
        DROP POLICY "Users can delete their own assessments" ON public.assessments;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'assessments' AND policyname = 'Admins have full access to assessments') THEN
        DROP POLICY "Admins have full access to assessments" ON public.assessments;
    END IF;
END $$;

-- Users can view their own assessments
CREATE POLICY "Users can view their own assessments"
ON public.assessments
FOR SELECT
USING (auth.uid() = user_id);

-- Users can insert their own assessments
CREATE POLICY "Users can create their own assessments"
ON public.assessments
FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Users can update their own assessments
CREATE POLICY "Users can update their own assessments"
ON public.assessments
FOR UPDATE
USING (auth.uid() = user_id);

-- Users can delete their own assessments
CREATE POLICY "Users can delete their own assessments"
ON public.assessments
FOR DELETE
USING (auth.uid() = user_id);

-- Admins can do anything with assessments
CREATE POLICY "Admins have full access to assessments"
ON public.assessments
FOR ALL
USING (EXISTS (
    SELECT 1 FROM auth.users 
    WHERE id = auth.uid() AND raw_user_meta_data->>'is_admin' = 'true'
));

-- RLS for admin_activities
ALTER TABLE public.admin_activities ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DO $$
BEGIN
    -- Drop policies if they exist
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'admin_activities' AND policyname = 'Admins can view all activities') THEN
        DROP POLICY "Admins can view all activities" ON public.admin_activities;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'admin_activities' AND policyname = 'Admins can create activities') THEN
        DROP POLICY "Admins can create activities" ON public.admin_activities;
    END IF;
END $$;

-- Admins can view all activities
CREATE POLICY "Admins can view all activities"
ON public.admin_activities
FOR SELECT
USING (EXISTS (
    SELECT 1 FROM auth.users 
    WHERE id = auth.uid() AND raw_user_meta_data->>'is_admin' = 'true'
));

-- Admins can insert activities
CREATE POLICY "Admins can create activities"
ON public.admin_activities
FOR INSERT
WITH CHECK (EXISTS (
    SELECT 1 FROM auth.users 
    WHERE id = auth.uid() AND raw_user_meta_data->>'is_admin' = 'true'
));

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_assessments_user_id ON public.assessments(user_id);
CREATE INDEX IF NOT EXISTS idx_assessments_created_at ON public.assessments(created_at);
CREATE INDEX IF NOT EXISTS idx_admin_activities_admin_id ON public.admin_activities(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_activities_created_at ON public.admin_activities(created_at);

-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON public.assessments TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.game_sessions TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.journal_entries TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.admin_activities TO authenticated;

GRANT EXECUTE ON FUNCTION public.execute_sql TO authenticated;

-- RLS for game_sessions
ALTER TABLE public.game_sessions ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DO $$
BEGIN
    -- Drop policies if they exist
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'game_sessions' AND policyname = 'Users can view their own game sessions') THEN
        DROP POLICY "Users can view their own game sessions" ON public.game_sessions;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'game_sessions' AND policyname = 'Users can create their own game sessions') THEN
        DROP POLICY "Users can create their own game sessions" ON public.game_sessions;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'game_sessions' AND policyname = 'Users can update their own game sessions') THEN
        DROP POLICY "Users can update their own game sessions" ON public.game_sessions;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'game_sessions' AND policyname = 'Users can delete their own game sessions') THEN
        DROP POLICY "Users can delete their own game sessions" ON public.game_sessions;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'game_sessions' AND policyname = 'Admins have full access to game sessions') THEN
        DROP POLICY "Admins have full access to game sessions" ON public.game_sessions;
    END IF;
END $$;

-- Users can view their own game sessions
CREATE POLICY "Users can view their own game sessions"
ON public.game_sessions
FOR SELECT
USING (auth.uid() = user_id);

-- Users can insert their own game sessions
CREATE POLICY "Users can create their own game sessions"
ON public.game_sessions
FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Users can update their own game sessions
CREATE POLICY "Users can update their own game sessions"
ON public.game_sessions
FOR UPDATE
USING (auth.uid() = user_id);

-- Users can delete their own game sessions
CREATE POLICY "Users can delete their own game sessions"
ON public.game_sessions
FOR DELETE
USING (auth.uid() = user_id);

-- Admins can do anything with game sessions
CREATE POLICY "Admins have full access to game sessions"
ON public.game_sessions
FOR ALL
USING (EXISTS (
    SELECT 1 FROM auth.users 
    WHERE id = auth.uid() AND raw_user_meta_data->>'is_admin' = 'true'
));

-- Create indexes for game_sessions
CREATE INDEX IF NOT EXISTS idx_game_sessions_user_id ON public.game_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_game_sessions_created_at ON public.game_sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_game_sessions_game_type ON public.game_sessions(game_type);

-- Grant necessary permissions on game_sessions
GRANT SELECT, INSERT, UPDATE, DELETE ON public.game_sessions TO authenticated;

-- RLS for journal_entries
ALTER TABLE public.journal_entries ENABLE ROW LEVEL SECURITY;

-- Users can view their own journal entries
CREATE POLICY "Users can view their own journal entries"
ON public.journal_entries
FOR SELECT
USING (auth.uid() = user_id);

-- Users can insert their own journal entries
CREATE POLICY "Users can create their own journal entries"
ON public.journal_entries
FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Users can update their own journal entries
CREATE POLICY "Users can update their own journal entries"
ON public.journal_entries
FOR UPDATE
USING (auth.uid() = user_id);

-- Users can delete their own journal entries
CREATE POLICY "Users can delete their own journal entries"
ON public.journal_entries
FOR DELETE
USING (auth.uid() = user_id);

-- Admins can do anything with journal entries
CREATE POLICY "Admins have full access to journal entries"
ON public.journal_entries
FOR ALL
USING (EXISTS (
    SELECT 1 FROM auth.users 
    WHERE id = auth.uid() AND raw_user_meta_data->>'is_admin' = 'true'
));

-- Create indexes for journal_entries
CREATE INDEX IF NOT EXISTS idx_journal_entries_user_id ON public.journal_entries(user_id);
CREATE INDEX IF NOT EXISTS idx_journal_entries_created_at ON public.journal_entries(created_at);

-- Grant necessary permissions on journal_entries
GRANT SELECT, INSERT, UPDATE, DELETE ON public.journal_entries TO authenticated;

-- =============================================
-- TEST DATA FOR ADMIN PANEL
-- =============================================

-- Only insert test data if we're in development mode
DO $$
BEGIN
    -- Check if we should insert test data (only in development)
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'postgres') THEN
        -- Create a test admin user if it doesn't exist
        INSERT INTO auth.users (
            id, email, encrypted_password, email_confirmed_at, 
            created_at, updated_at, last_sign_in_at, raw_app_meta_data, 
            raw_user_meta_data, is_super_admin, confirmation_token, 
            email_change, email_change_token_new, recovery_token
        ) VALUES (
            '00000000-0000-0000-0000-000000000001', 
            'admin@example.com', 
            crypt('admin123', gen_salt('bf')), 
            now(), 
            now(), 
            now(), 
            now(), 
            '{"provider":"email","providers":["email"]}'::jsonb, 
            '{"is_admin": true, "full_name": "Test Admin"}'::jsonb, 
            FALSE, 
            '', 
            '', 
            '', 
            ''
        ) ON CONFLICT (id) DO NOTHING;
        
        -- Add test assessments
        INSERT INTO public.assessments (
            user_id, assessment_type, score, max_score, completed, metadata
        ) VALUES 
        ('00000000-0000-0000-0000-000000000001', 'depression', 8, 27, TRUE, '{"notes": "Test assessment"}'),
        ('00000000-0000-0000-0000-000000000001', 'anxiety', 12, 27, TRUE, '{"notes": "Follow-up required"}');
        
        -- Add test journal entries
        INSERT INTO public.journal_entries (
            user_id, title, content, mood, tags, is_private, metadata
        ) VALUES 
        ('00000000-0000-0000-0000-000000000001', 'First Entry', 'This is a test journal entry.', 'happy', ARRAY['test', 'sample'], FALSE, '{"location": "home"}'),
        ('00000000-0000-0000-0000-000000000001', 'Second Entry', 'Another test entry.', 'neutral', ARRAY['test'], TRUE, '{"location": "work"}');
        
        -- Add test game sessions
        INSERT INTO public.game_sessions (
            user_id, game_type, score, duration_seconds, level, metadata
        ) VALUES 
        ('00000000-0000-0000-0000-000000000001', 'memory', 1000, 120, 3, '{"difficulty": "medium"}'),
        ('00000000-0000-0000-0000-000000000001', 'puzzle', 850, 180, 5, '{"difficulty": "hard"}');
        
        -- Add test admin activities
        INSERT INTO public.admin_activities (
            admin_id, activity_type, description, metadata
        ) VALUES 
        ('00000000-0000-0000-0000-000000000001', 'login', 'Admin logged in', '{"ip": "192.168.1.1"}'),
        ('00000000-0000-0000-0000-000000000001', 'user_edit', 'Updated user profile', '{"user_id": "00000000-0000-0000-0000-000000000002"}');
        
        RAISE NOTICE 'Test data inserted successfully';
    END IF;
END $$;
