-- Create RPC function to save game scores
CREATE OR REPLACE FUNCTION public.save_game_score(
    p_user_id UUID,
    p_game_type TEXT,
    p_score INTEGER,
    p_metadata JSONB DEFAULT '{}'::JSONB
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result JSONB;
BEGIN
    -- Insert the score
    INSERT INTO public.game_scores (user_id, game_type, score, metadata)
    VALUES (p_user_id, p_game_type, p_score, p_metadata)
    RETURNING to_jsonb(public.game_scores.*) INTO result;
    
    RETURN jsonb_build_object(
        'status', 'success',
        'data', result
    );
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'status', 'error',
        'message', SQLERRM
    );
END;
$$;

-- Create RPC function to get user's total points
CREATE OR REPLACE FUNCTION public.get_user_total_points(
    p_user_id UUID
)
RETURNS TABLE (total_points BIGINT)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT COALESCE(SUM(score), 0)::BIGINT as total_points
    FROM public.game_scores
    WHERE user_id = p_user_id;
END;
$$;

-- Grant execute permissions to authenticated users
GRANT EXECUTE ON FUNCTION public.save_game_score(UUID, TEXT, INTEGER, JSONB) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_user_total_points(UUID) TO authenticated;
