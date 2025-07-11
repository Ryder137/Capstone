-- Migration to fix policy naming conflicts
-- This script should be run after 013_add_missing_admin_tables.sql

-- First, drop all existing policies on tables to avoid conflicts
DO $$
DECLARE
    drop_sql TEXT;
BEGIN
    -- Drop all policies on journal_entries
    SELECT COALESCE(
        string_agg('DROP POLICY IF EXISTS "' || policyname || '" ON public.journal_entries;', E'\n'),
        'SELECT 1;' -- Default statement if no policies exist
    ) INTO drop_sql
    FROM pg_policies
    WHERE tablename = 'journal_entries';
    
    EXECUTE drop_sql;
    
    -- Drop all policies on assessments
    SELECT COALESCE(
        string_agg('DROP POLICY IF EXISTS "' || policyname || '" ON public.assessments;', E'\n'),
        'SELECT 1;' -- Default statement if no policies exist
    ) INTO drop_sql
    FROM pg_policies
    WHERE tablename = 'assessments';
    
    EXECUTE drop_sql;
    
    -- Drop all policies on game_sessions
    SELECT COALESCE(
        string_agg('DROP POLICY IF EXISTS "' || policyname || '" ON public.game_sessions;', E'\n'),
        'SELECT 1;' -- Default statement if no policies exist
    ) INTO drop_sql
    FROM pg_policies
    WHERE tablename = 'game_sessions';
    
    EXECUTE drop_sql;
    
    -- Drop all policies on admin_activities
    SELECT COALESCE(
        string_agg('DROP POLICY IF EXISTS "' || policyname || '" ON public.admin_activities;', E'\n'),
        'SELECT 1;' -- Default statement if no policies exist
    ) INTO drop_sql
    FROM pg_policies
    WHERE tablename = 'admin_activities';
    
    EXECUTE drop_sql;
END $$;

-- Now, re-create all policies with consistent naming

-- Function to safely create a policy if it doesn't exist
CREATE OR REPLACE FUNCTION safe_create_policy(
    policy_name TEXT,
    table_name TEXT,
    command TEXT,
    using_expr TEXT,
    with_check_expr TEXT DEFAULT NULL
) RETURNS VOID AS $$
DECLARE
    policy_exists BOOLEAN;
    create_sql TEXT;
BEGIN
    -- Check if policy already exists
    SELECT EXISTS (
        SELECT 1 
        FROM pg_policies 
        WHERE policyname = policy_name 
        AND tablename = table_name
    ) INTO policy_exists;
    
    -- Only create the policy if it doesn't exist
    IF NOT policy_exists THEN
        -- Build the CREATE POLICY statement
        create_sql := format(
            'CREATE POLICY "%s" ON public.%I FOR %s USING (%s)',
            policy_name,
            table_name,
            command,
            using_expr
        );
        
        -- Add WITH CHECK clause if provided
        IF with_check_expr IS NOT NULL THEN
            create_sql := create_sql || format(' WITH CHECK (%s)', with_check_expr);
        END IF;
        
        -- Execute the CREATE POLICY statement
        EXECUTE create_sql;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Journal Entries Policies
DO $$
BEGIN
    -- Only create policies if the table exists
    IF EXISTS (
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'journal_entries'
    ) THEN
        PERFORM safe_create_policy(
            'Users can view own journal entries',
            'journal_entries',
            'SELECT',
            'auth.uid() = user_id'
        );
        
        PERFORM safe_create_policy(
            'Users can insert own journal entries',
            'journal_entries',
            'INSERT',
            'true',
            'auth.uid() = user_id'
        );
        
        PERFORM safe_create_policy(
            'Users can update own journal entries',
            'journal_entries',
            'UPDATE',
            'auth.uid() = user_id',
            'auth.uid() = user_id'
        );
        
        PERFORM safe_create_policy(
            'Users can delete own journal entries',
            'journal_entries',
            'DELETE',
            'auth.uid() = user_id'
        );
        
        -- Admin policy
        PERFORM safe_create_policy(
            'Admins have full access to journal entries',
            'journal_entries',
            'ALL',
            'EXISTS (SELECT 1 FROM auth.users WHERE id = auth.uid() AND raw_user_meta_data->>''is_admin'' = ''true'')'
        );
    END IF;
END $$;

-- Assessments Policies
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'assessments'
    ) THEN
        PERFORM safe_create_policy(
            'Users can view own assessments',
            'assessments',
            'SELECT',
            'auth.uid() = user_id'
        );
        
        PERFORM safe_create_policy(
            'Users can create own assessments',
            'assessments',
            'INSERT',
            'true',
            'auth.uid() = user_id'
        );
        
        PERFORM safe_create_policy(
            'Users can update own assessments',
            'assessments',
            'UPDATE',
            'auth.uid() = user_id',
            'auth.uid() = user_id'
        );
        
        PERFORM safe_create_policy(
            'Users can delete own assessments',
            'assessments',
            'DELETE',
            'auth.uid() = user_id'
        );
        
        -- Admin policy
        PERFORM safe_create_policy(
            'Admins have full access to assessments',
            'assessments',
            'ALL',
            'EXISTS (SELECT 1 FROM auth.users WHERE id = auth.uid() AND raw_user_meta_data->>''is_admin'' = ''true'')'
        );
    END IF;
END $$;

-- Game Sessions Policies
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'game_sessions'
    ) THEN
        PERFORM safe_create_policy(
            'Users can view own game sessions',
            'game_sessions',
            'SELECT',
            'auth.uid() = user_id'
        );
        
        PERFORM safe_create_policy(
            'Users can create own game sessions',
            'game_sessions',
            'INSERT',
            'true',
            'auth.uid() = user_id'
        );
        
        PERFORM safe_create_policy(
            'Users can update own game sessions',
            'game_sessions',
            'UPDATE',
            'auth.uid() = user_id',
            'auth.uid() = user_id'
        );
        
        PERFORM safe_create_policy(
            'Users can delete own game sessions',
            'game_sessions',
            'DELETE',
            'auth.uid() = user_id'
        );
        
        -- Admin policy
        PERFORM safe_create_policy(
            'Admins have full access to game sessions',
            'game_sessions',
            'ALL',
            'EXISTS (SELECT 1 FROM auth.users WHERE id = auth.uid() AND raw_user_meta_data->>''is_admin'' = ''true'')'
        );
    END IF;
END $$;

-- Admin Activities Policies
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'admin_activities'
    ) THEN
        PERFORM safe_create_policy(
            'Admins can view all activities',
            'admin_activities',
            'SELECT',
            'EXISTS (SELECT 1 FROM auth.users WHERE id = auth.uid() AND raw_user_meta_data->>''is_admin'' = ''true'')'
        );
        
        PERFORM safe_create_policy(
            'Admins can create activities',
            'admin_activities',
            'INSERT',
            'true',
            'EXISTS (SELECT 1 FROM auth.users WHERE id = auth.uid() AND raw_user_meta_data->>''is_admin'' = ''true'')'
        );
    END IF;
END $$;

-- Enable RLS on all tables if not already enabled
ALTER TABLE public.journal_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.game_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.admin_activities ENABLE ROW LEVEL SECURITY;
