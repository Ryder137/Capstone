-- Create user_plants table
CREATE TABLE IF NOT EXISTS public.user_plants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    plant_type TEXT NOT NULL DEFAULT 'sunflower',
    growth_stage INTEGER NOT NULL DEFAULT 0 CHECK (growth_stage >= 0 AND growth_stage <= 100),
    last_watered TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE public.user_plants ENABLE ROW LEVEL SECURITY;

-- Create policies for user_plants
CREATE POLICY "Users can view their own plants"
    ON public.user_plants
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own plants"
    ON public.user_plants
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own plants"
    ON public.user_plants
    FOR UPDATE
    USING (auth.uid() = user_id);

-- Create a function to update the updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create a trigger to update the updated_at column
CREATE TRIGGER update_user_plants_updated_at
BEFORE UPDATE ON public.user_plants
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Add a column to track points used for plants in the users table
ALTER TABLE public.users
ADD COLUMN IF NOT EXISTS plant_points INTEGER DEFAULT 0;

-- Update the users table RLS policy to allow updating plant_points
CREATE POLICY "Users can update their own plant points"
    ON public.users
    FOR UPDATE
    USING (auth.uid() = id);
