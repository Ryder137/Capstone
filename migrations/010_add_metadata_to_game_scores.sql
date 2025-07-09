-- Add metadata column to game_scores table
ALTER TABLE public.game_scores
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::JSONB;

-- Update existing records to have an empty JSON object as default metadata
UPDATE public.game_scores SET metadata = '{}'::JSONB WHERE metadata IS NULL;

-- Update the save_game_score function to ensure it handles metadata correctly
CREATE OR REPLACE FUNCTION public.save_game_score(
    p_user_id UUID,
    p_game_type TEXT,
    p_score INTEGER,
    p_metadata JSONB DEFAULT '{}'::JSONB,
    p_source TEXT DEFAULT 'game',
    p_level INTEGER DEFAULT 1
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_result JSONB;
BEGIN
    -- Insert the new score with metadata, source, and level
    INSERT INTO public.game_scores (user_id, game_type, score, metadata, source, level)
    VALUES (p_user_id, p_game_type, p_score, p_metadata, p_source, p_level)
    RETURNING jsonb_build_object(
        'id', id,
        'user_id', user_id,
        'game_type', game_type,
        'score', score,
        'metadata', metadata,
        'source', source,
        'level', level,
        'created_at', created_at
    ) INTO v_result;
    
    RETURN jsonb_build_object('success', true, 'data', v_result);
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object('success', false, 'message', SQLERRM);
END;
$$;
