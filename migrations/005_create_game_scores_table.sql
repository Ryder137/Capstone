-- Create game_scores table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.game_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    game_type TEXT NOT NULL,
    score INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE public.game_scores ENABLE ROW LEVEL SECURITY;

-- Create policies for game_scores
CREATE POLICY "Users can view their own game scores"
    ON public.game_scores
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own game scores"
    ON public.game_scores
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Create index for better performance
CREATE INDEX IF NOT EXISTS idx_game_scores_user_id ON public.game_scores(user_id);
CREATE INDEX IF NOT EXISTS idx_game_scores_game_type ON public.game_scores(game_type);

-- Create a function to get the leaderboard
CREATE OR REPLACE FUNCTION public.get_leaderboard(
    p_game_type TEXT,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    user_id UUID,
    name TEXT,
    score BIGINT,
    rank BIGINT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    WITH ranked_scores AS (
        SELECT 
            u.id as user_id,
            u.name,
            SUM(gs.score) as total_score,
            RANK() OVER (ORDER BY SUM(gs.score) DESC) as rank
        FROM public.game_scores gs
        JOIN public.users u ON gs.user_id = u.id
        WHERE gs.game_type = p_game_type
        GROUP BY u.id, u.name
        ORDER BY total_score DESC
        LIMIT p_limit
    )
    SELECT 
        rs.user_id,
        rs.name,
        rs.total_score as score,
        rs.rank
    FROM ranked_scores rs
    ORDER BY rs.rank;
END;
$$;

-- Grant execute permissions to authenticated users
GRANT EXECUTE ON FUNCTION public.get_leaderboard(TEXT, INTEGER) TO authenticated;
