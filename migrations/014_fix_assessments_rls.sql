-- Enable RLS on assessments table if not already enabled
ALTER TABLE public.assessments ENABLE ROW LEVEL SECURITY;

-- Drop existing policies to avoid conflicts
DROP POLICY IF EXISTS "Admins have full access to assessments" ON public.assessments;

-- Create a policy to allow admins full access to all assessments
CREATE POLICY "Admins have full access to assessments"
ON public.assessments
FOR ALL
USING (
    EXISTS (
        SELECT 1 FROM auth.users
        WHERE auth.uid() = id 
        AND raw_user_meta_data->>'role' = 'admin'
    )
    OR 
    EXISTS (
        SELECT 1 FROM public.users
        WHERE auth.uid() = id 
        AND is_admin = true
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1 FROM auth.users
        WHERE auth.uid() = id 
        AND raw_user_meta_data->>'role' = 'admin'
    )
    OR 
    EXISTS (
        SELECT 1 FROM public.users
        WHERE auth.uid() = id 
        AND is_admin = true
    )
);

-- Ensure the select policy allows admins to view all assessments
CREATE OR REPLACE POLICY "Users can view their own assessments"
ON public.assessments
FOR SELECT
USING (
    auth.uid() = user_id
    OR 
    EXISTS (
        SELECT 1 FROM auth.users
        WHERE auth.uid() = id 
        AND raw_user_meta_data->>'role' = 'admin'
    )
    OR
    EXISTS (
        SELECT 1 FROM public.users
        WHERE auth.uid() = id 
        AND is_admin = true
    )
);

-- Create a function to check if current user is admin
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS boolean AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 
        FROM auth.users
        WHERE auth.uid() = id 
        AND raw_user_meta_data->>'role' = 'admin'
    ) OR EXISTS (
        SELECT 1 
        FROM public.users
        WHERE auth.uid() = id 
        AND is_admin = true
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
