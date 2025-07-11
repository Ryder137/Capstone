-- Check if RLS is enabled on users table
SELECT 
    tablename, 
    rowsecurity AS "RLS Enabled"
FROM 
    pg_tables 
WHERE 
    schemaname = 'public' 
    AND tablename = 'users';

-- Check existing RLS policies on users table
SELECT 
    schemaname,
    tablename,
    policyname,
    roles,
    cmd,
    qual,
    with_check
FROM 
    pg_policies
WHERE 
    tablename = 'users';

-- Check table structure
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM 
    information_schema.columns 
WHERE 
    table_schema = 'public' 
    AND table_name = 'users'
ORDER BY 
    ordinal_position;
