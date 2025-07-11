-- Create game_sessions table
CREATE TABLE IF NOT EXISTS public.game_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    game_type TEXT NOT NULL,
    score INTEGER,
    duration_seconds INTEGER,
    completed_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.game_sessions ENABLE ROW LEVEL SECURITY;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_game_sessions_user_id ON public.game_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_game_sessions_completed_at ON public.game_sessions(completed_at);

-- Add sample data
INSERT INTO public.game_sessions (user_id, game_type, score, duration_seconds, completed_at)
SELECT 
    id as user_id,
    CASE 
        WHEN random() < 0.5 THEN 'memory' 
        ELSE 'puzzle' 
    END as game_type,
    (random() * 1000)::INT as score,
    (random() * 300 + 60)::INT as duration_seconds,
    NOW() - (random() * INTERVAL '30 days')
FROM auth.users
CROSS JOIN generate_series(1, 5);

-- Add sample data for assessments
-- First check if the table exists and get its structure
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'assessments') THEN
        -- Get column information
        IF EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'assessments' 
            AND column_name = 'completed_at'
        ) THEN
            -- If completed_at exists
            INSERT INTO public.assessments (user_id, assessment_type, score, completed_at, created_at, updated_at)
            SELECT 
                id as user_id,
                'phq-9' as assessment_type,
                (random() * 20)::INT as score,
                NOW() - (random() * INTERVAL '30 days'),
                NOW() - (random() * INTERVAL '30 days'),
                NOW() - (random() * INTERVAL '30 days')
            FROM auth.users
            CROSS JOIN generate_series(1, 3);
        ELSE
            -- If completed_at doesn't exist, check if max_score is required
            IF EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'assessments' 
                AND column_name = 'max_score'
                AND is_nullable = 'NO'
            ) THEN
                -- With max_score (required)
                INSERT INTO public.assessments (user_id, assessment_type, score, max_score, created_at, updated_at)
                SELECT 
                    id as user_id,
                    'phq-9' as assessment_type,
                    (random() * 20)::INT as score,
                    27 as max_score,  -- Standard PHQ-9 max score
                    NOW() - (random() * INTERVAL '30 days'),
                    NOW() - (random() * INTERVAL '30 days')
                FROM auth.users
                CROSS JOIN generate_series(1, 3);
            ELSE
                -- Without max_score
                INSERT INTO public.assessments (user_id, assessment_type, score, created_at, updated_at)
                SELECT 
                    id as user_id,
                    'phq-9' as assessment_type,
                    (random() * 20)::INT as score,
                    NOW() - (random() * INTERVAL '30 days'),
                    NOW() - (random() * INTERVAL '30 days')
                FROM auth.users
                CROSS JOIN generate_series(1, 3);
            END IF;
        END IF;
    ELSE
        RAISE NOTICE 'assessments table does not exist, skipping data insertion';
    END IF;
END $$;

-- Add sample data for breathing_sessions
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'breathing_sessions') THEN
        -- Check if duration_seconds column exists
        IF EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'breathing_sessions' 
            AND column_name = 'duration_seconds'
        ) THEN
            -- With duration_seconds
            IF EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'breathing_sessions' 
                AND column_name = 'completed_at'
            ) THEN
                -- With completed_at and duration_seconds
                INSERT INTO public.breathing_sessions (user_id, duration_seconds, pattern, completed_at, created_at, updated_at)
                SELECT 
                    id as user_id,
                    (random() * 300 + 60)::INT as duration_seconds,
                    '4-7-8' as pattern,
                    NOW() - (random() * INTERVAL '30 days'),
                    NOW() - (random() * INTERVAL '30 days'),
                    NOW() - (random() * INTERVAL '30 days')
                FROM auth.users
                CROSS JOIN generate_series(1, 4);
            ELSE
                -- With duration_seconds but no completed_at
                INSERT INTO public.breathing_sessions (user_id, duration_seconds, pattern, created_at, updated_at)
                SELECT 
                    id as user_id,
                    (random() * 300 + 60)::INT as duration_seconds,
                    '4-7-8' as pattern,
                    NOW() - (random() * INTERVAL '30 days'),
                    NOW() - (random() * INTERVAL '30 days')
                FROM auth.users
                CROSS JOIN generate_series(1, 4);
            END IF;
        ELSE
            -- Without duration_seconds
            IF EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'breathing_sessions' 
                AND column_name = 'duration'
            ) THEN
                -- With duration (instead of duration_seconds)
                IF EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = 'breathing_sessions' 
                    AND column_name = 'completed_at'
                ) THEN
                    -- With duration and completed_at
                    INSERT INTO public.breathing_sessions (user_id, duration, pattern, completed_at, created_at, updated_at)
                    SELECT 
                        id as user_id,
                        (random() * 300 + 60)::INT as duration,
                        '4-7-8' as pattern,
                        NOW() - (random() * INTERVAL '30 days'),
                        NOW() - (random() * INTERVAL '30 days'),
                        NOW() - (random() * INTERVAL '30 days')
                    FROM auth.users
                    CROSS JOIN generate_series(1, 4);
                ELSE
                    -- With duration but no completed_at
                    INSERT INTO public.breathing_sessions (user_id, duration, pattern, created_at, updated_at)
                    SELECT 
                        id as user_id,
                        (random() * 300 + 60)::INT as duration,
                        '4-7-8' as pattern,
                        NOW() - (random() * INTERVAL '30 days'),
                        NOW() - (random() * INTERVAL '30 days')
                    FROM auth.users
                    CROSS JOIN generate_series(1, 4);
                END IF;
            ELSE
                -- Minimal insertion with just required fields
                INSERT INTO public.breathing_sessions (user_id, pattern, created_at, updated_at)
                SELECT 
                    id as user_id,
                    '4-7-8' as pattern,
                    NOW() - (random() * INTERVAL '30 days'),
                    NOW() - (random() * INTERVAL '30 days')
                FROM auth.users
                CROSS JOIN generate_series(1, 4);
            END IF;
        END IF;
    ELSE
        RAISE NOTICE 'breathing_sessions table does not exist, skipping data insertion';
    END IF;
END $$;

-- Add sample admin activities
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'admin_activities') THEN
        -- Check if user_email column exists
        IF EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'admin_activities' 
            AND column_name = 'user_email'
        ) THEN
            -- With user_email column
            WITH actions AS (
                SELECT 
                    id as user_id,
                    email as user_email,
                    CASE 
                        WHEN random() < 0.3 THEN 'login' 
                        WHEN random() < 0.6 THEN 'update' 
                        ELSE 'create' 
                    END as action_type,
                    NOW() - (random() * INTERVAL '7 days') as created_time
                FROM auth.users
                CROSS JOIN generate_series(1, 3)  -- 3 activities per user
            )
            INSERT INTO public.admin_activities (
                user_id, 
                user_email,
                action, 
                details, 
                created_at, 
                updated_at
            )
            SELECT 
                user_id,
                user_email,
                action_type,
                CASE 
                    WHEN action_type = 'login' THEN 'User logged in to admin dashboard'
                    WHEN action_type = 'update' THEN 'User updated settings'
                    ELSE 'User created new content'
                END as details,
                created_time,
                created_time + (random() * INTERVAL '1 hour')
            FROM actions;
        ELSE
            -- Without user_email column
            WITH actions AS (
                SELECT 
                    id as user_id,
                    CASE 
                        WHEN random() < 0.3 THEN 'login' 
                        WHEN random() < 0.6 THEN 'update' 
                        ELSE 'create' 
                    END as action_type,
                    NOW() - (random() * INTERVAL '7 days') as created_time
                FROM auth.users
                CROSS JOIN generate_series(1, 3)  -- 3 activities per user
            )
            INSERT INTO public.admin_activities (
                user_id, 
                action, 
                details, 
                created_at, 
                updated_at
            )
            SELECT 
                user_id,
                action_type,
                CASE 
                    WHEN action_type = 'login' THEN 'User logged in to admin dashboard'
                    WHEN action_type = 'update' THEN 'User updated settings'
                    ELSE 'User created new content'
                END as details,
                created_time,
                created_time + (random() * INTERVAL '1 hour')
            FROM actions;
        END IF;
    ELSE
        RAISE NOTICE 'admin_activities table does not exist, skipping data insertion';
    END IF;
END $$;
