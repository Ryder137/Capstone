-- Create a function to get available points from game wins only
CREATE OR REPLACE FUNCTION public.get_available_points(
    p_user_id UUID
)
RETURNS TABLE (
    total BIGINT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT COALESCE(SUM(gs.score), 0)::BIGINT as total
    FROM public.game_scores gs
    WHERE gs.user_id = p_user_id
    AND gs.source = 'game'
    GROUP BY gs.user_id;
    
    -- If no rows returned (no game scores yet), return 0
    IF NOT FOUND THEN
        RETURN QUERY SELECT 0::BIGINT as total;
    END IF;
END;
$$;

-- Grant execute permissions to authenticated users
GRANT EXECUTE ON FUNCTION public.get_available_points(UUID) TO authenticated;
