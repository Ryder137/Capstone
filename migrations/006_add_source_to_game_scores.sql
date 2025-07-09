-- Add source column to game_scores table
ALTER TABLE public.game_scores
ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'game';

-- Update existing records to have a default source
UPDATE public.game_scores SET source = 'game' WHERE source IS NULL;

-- Create an index on the source column for better query performance
CREATE INDEX IF NOT EXISTS idx_game_scores_source ON public.game_scores(source);

-- Update the save_game_score function to include the source parameter
CREATE OR REPLACE FUNCTION public.save_game_score(
    p_user_id UUID,
    p_game_type TEXT,
    p_score INTEGER,
    p_metadata JSONB DEFAULT '{}'::JSONB,
    p_source TEXT DEFAULT 'game'
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_result JSONB;
BEGIN
    -- Insert the new score with source
    INSERT INTO public.game_scores (user_id, game_type, score, metadata, source)
    VALUES (p_user_id, p_game_type, p_score, p_metadata, p_source)
    RETURNING jsonb_build_object(
        'id', id,
        'user_id', user_id,
        'game_type', game_type,
        'score', score,
        'source', source,
        'created_at', created_at
    ) INTO v_result;
    
    RETURN v_result;
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object('error', SQLERRM);
END;
$$;

-- Update the get_leaderboard function to filter by source if needed
CREATE OR REPLACE FUNCTION public.get_leaderboard(
    p_game_type TEXT,
    p_limit INTEGER DEFAULT 10,
    p_source TEXT DEFAULT NULL
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
    WITH filtered_scores AS (
        SELECT 
            gs.user_id,
            gs.score,
            gs.game_type,
            gs.source
        FROM public.game_scores gs
        WHERE gs.game_type = p_game_type
        AND (p_source IS NULL OR gs.source = p_source)
    ),
    ranked_scores AS (
        SELECT 
            u.id as user_id,
            u.name,
            SUM(fs.score) as total_score,
            RANK() OVER (ORDER BY SUM(fs.score) DESC) as rank
        FROM filtered_scores fs
        JOIN public.users u ON fs.user_id = u.id
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
GRANT EXECUTE ON FUNCTION public.save_game_score(UUID, TEXT, INTEGER, JSONB, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_leaderboard(TEXT, INTEGER, TEXT) TO authenticated;
