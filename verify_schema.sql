-- Verify Database Schema
-- Run this in Supabase SQL Editor to check if all required tables and functions exist

-- Function to check if a table exists
CREATE OR REPLACE FUNCTION table_exists(schema_name text, table_name text) 
RETURNS boolean AS $$
DECLARE
    result boolean;
BEGIN
    SELECT EXISTS (
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_schema = schema_name 
        AND table_name = table_name
    ) INTO result;
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Function to check if a function exists
CREATE OR REPLACE FUNCTION function_exists(function_name text) 
RETURNS boolean AS $$
DECLARE
    result boolean;
BEGIN
    SELECT EXISTS (
        SELECT 1 
        FROM pg_proc 
        JOIN pg_namespace ON pg_proc.pronamespace = pg_namespace.oid 
        WHERE pg_namespace.nspname = 'public' 
        AND proname = function_name
    ) INTO result;
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Function to check if RLS is enabled for a table
CREATE OR REPLACE FUNCTION rls_enabled(table_name text) 
RETURNS boolean AS $$
DECLARE
    result boolean;
BEGIN
    SELECT relrowsecurity 
    FROM pg_class 
    JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace 
    WHERE nspname = 'public' 
    AND relname = table_name
    INTO result;
    
    RETURN COALESCE(result, false);
END;
$$ LANGUAGE plpgsql;

-- Check required tables and their RLS status
SELECT 
    'Table Check' as check_type,
    table_name,
    table_exists('public', table_name) as exists,
    CASE 
        WHEN table_exists('public', table_name) THEN rls_enabled(table_name)
        ELSE NULL 
    END as rls_enabled
FROM (
    VALUES 
        ('users'),
        ('assessments'),
        ('journal_entries'),
        ('game_sessions'),
        ('admin_activities')
) AS t(table_name)
UNION ALL
-- Check required functions
SELECT 
    'Function Check' as check_type,
    function_name as table_name,
    function_exists(function_name) as exists,
    NULL as rls_enabled
FROM (
    VALUES 
        ('execute_sql')
) AS f(function_name)
ORDER BY check_type, table_name;

-- Clean up temporary functions
DROP FUNCTION IF EXISTS table_exists(text, text);
DROP FUNCTION IF EXISTS function_exists(text);
DROP FUNCTION IF EXISTS rls_enabled(text);
