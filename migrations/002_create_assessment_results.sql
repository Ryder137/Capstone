-- Create assessment_results table
CREATE TABLE IF NOT EXISTS public.assessment_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Assessment metadata
    assessment_type TEXT NOT NULL DEFAULT 'mental_health',
    total_score FLOAT NOT NULL,
    overall_level TEXT NOT NULL,
    
    -- Category scores
    category_scores JSONB,
    category_levels JSONB,
    recommendations JSONB,
    
    -- Additional metadata
    metadata JSONB,
    
    -- Indexes
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Add RLS policies for assessment_results
ALTER TABLE public.assessment_results ENABLE ROW LEVEL SECURITY;

-- Users can view their own assessment results
CREATE POLICY "Users can view their own assessment results"
ON public.assessment_results
FOR SELECT
USING (auth.uid() = user_id);

-- Users can insert their own assessment results
CREATE POLICY "Users can create their own assessment results"
ON public.assessment_results
FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Users can update their own assessment results
CREATE POLICY "Users can update their own assessment results"
ON public.assessment_results
FOR UPDATE
USING (auth.uid() = user_id);

-- Users can delete their own assessment results
CREATE POLICY "Users can delete their own assessment results"
ON public.assessment_results
FOR DELETE
USING (auth.uid() = user_id);

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create a trigger to update the updated_at column
CREATE TRIGGER update_assessment_results_updated_at
BEFORE UPDATE ON public.assessment_results
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Create an index on user_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_assessment_results_user_id ON public.assessment_results(user_id);

-- Create an index on created_at for sorting
CREATE INDEX IF NOT EXISTS idx_assessment_results_created_at ON public.assessment_results(created_at);
