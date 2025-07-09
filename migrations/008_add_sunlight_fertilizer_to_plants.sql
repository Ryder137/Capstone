-- Add sunlight and fertilizer columns to user_plants
ALTER TABLE user_plants
ADD COLUMN sunlight_level INT NOT NULL DEFAULT 50,
ADD COLUMN last_sunlight TIMESTAMP WITH TIME ZONE,
ADD COLUMN fertilizer_level INT NOT NULL DEFAULT 50,
ADD COLUMN last_fertilizer TIMESTAMP WITH TIME ZONE;

-- Create a function to update plant growth based on all factors
CREATE OR REPLACE FUNCTION update_plant_growth(
    p_user_id UUID,
    p_plant_id UUID,
    p_water_points INT DEFAULT 0,
    p_sunlight_points INT DEFAULT 0,
    p_fertilizer_points INT DEFAULT 0
) RETURNS JSONB AS $$
DECLARE
    v_plant RECORD;
    v_new_growth FLOAT;
    v_water_contribution FLOAT;
    v_sunlight_contribution FLOAT;
    v_fertilizer_contribution FLOAT;
    v_total_points INT;
    v_result JSONB;
BEGIN
    -- Get current plant state
    SELECT * INTO v_plant
    FROM user_plants
    WHERE user_id = p_user_id AND id = p_plant_id
    FOR UPDATE;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object('status', 'error', 'message', 'Plant not found');
    END IF;
    
    -- Calculate contributions from each factor (weighted)
    v_water_contribution := LEAST(100, v_plant.water_count * 5) * 0.4; -- 40% weight
    v_sunlight_contribution := LEAST(100, v_plant.sunlight_level) * 0.35; -- 35% weight
    v_fertilizer_contribution := LEAST(100, v_plant.fertilizer_level) * 0.25; -- 25% weight
    
    -- Calculate new growth (0-100 scale)
    v_new_growth := LEAST(100, 
        (v_water_contribution + v_sunlight_contribution + v_fertilizer_contribution) / 3
    );
    
    -- Update plant growth
    UPDATE user_plants
    SET 
        growth_stage = LEAST(3, FLOOR(v_new_growth / 33.34) + 1),
        last_updated = NOW(),
        water_count = GREATEST(0, LEAST(100, v_plant.water_count + p_water_points)),
        sunlight_level = GREATEST(0, LEAST(100, v_plant.sunlight_level + p_sunlight_points)),
        fertilizer_level = GREATEST(0, LEAST(100, v_plant.fertilizer_level + p_fertilizer_points)),
        last_watered = CASE WHEN p_water_points > 0 THEN NOW() ELSE v_plant.last_watered END,
        last_sunlight = CASE WHEN p_sunlight_points > 0 THEN NOW() ELSE v_plant.last_sunlight END,
        last_fertilizer = CASE WHEN p_fertilizer_points > 0 THEN NOW() ELSE v_plant.last_fertilizer END
    WHERE user_id = p_user_id AND id = p_plant_id
    RETURNING * INTO v_plant;
    
    -- Calculate decay for next time (slight decay over time)
    PERFORM pg_notify('plant_updated', jsonb_build_object(
        'user_id', p_user_id,
        'plant_id', p_plant_id,
        'growth_stage', v_plant.growth_stage,
        'water_level', v_plant.water_count,
        'sunlight_level', v_plant.sunlight_level,
        'fertilizer_level', v_plant.fertilizer_level
    )::text);
    
    RETURN jsonb_build_object(
        'status', 'success',
        'plant', jsonb_build_object(
            'growth_stage', v_plant.growth_stage,
            'water_count', v_plant.water_count,
            'sunlight_level', v_plant.sunlight_level,
            'fertilizer_level', v_plant.fertilizer_level,
            'last_watered', v_plant.last_watered,
            'last_sunlight', v_plant.last_sunlight,
            'last_fertilizer', v_plant.last_fertilizer,
            'is_wilting', v_plant.water_count < 20 OR v_plant.sunlight_level < 20
        )
    );
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object('status', 'error', 'message', SQLERRM);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION update_plant_growth(UUID, UUID, INT, INT, INT) TO authenticated;
