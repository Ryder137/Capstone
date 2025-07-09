-- Add missing columns to user_plants table
DO $$
BEGIN
    -- Add water_count if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name = 'user_plants' AND column_name = 'water_count') THEN
        ALTER TABLE user_plants
        ADD COLUMN water_count INT NOT NULL DEFAULT 50;
    END IF;

    -- Add is_wilting if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name = 'user_plants' AND column_name = 'is_wilting') THEN
        ALTER TABLE user_plants
        ADD COLUMN is_wilting BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;

    -- Add last_watered if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name = 'user_plants' AND column_name = 'last_watered') THEN
        ALTER TABLE user_plants
        ADD COLUMN last_watered TIMESTAMP WITH TIME ZONE;
    END IF;

    -- Add last_sunlight if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name = 'user_plants' AND column_name = 'last_sunlight') THEN
        ALTER TABLE user_plants
        ADD COLUMN last_sunlight TIMESTAMP WITH TIME ZONE;
    END IF;

    -- Add last_fertilized if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name = 'user_plants' AND column_name = 'last_fertilized') THEN
        ALTER TABLE user_plants
        ADD COLUMN last_fertilized TIMESTAMP WITH TIME ZONE;
    END IF;

    -- Add plant_type if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name = 'user_plants' AND column_name = 'plant_type') THEN
        ALTER TABLE user_plants
        ADD COLUMN plant_type VARCHAR(50) NOT NULL DEFAULT 'sunflower';
    END IF;

    -- Add growth_stage if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name = 'user_plants' AND column_name = 'growth_stage') THEN
        ALTER TABLE user_plants
        ADD COLUMN growth_stage INT NOT NULL DEFAULT 1;
    END IF;

    -- Add created_at if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name = 'user_plants' AND column_name = 'created_at') THEN
        ALTER TABLE user_plants
        ADD COLUMN created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW();
    END IF;

    -- Add updated_at if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name = 'user_plants' AND column_name = 'updated_at') THEN
        ALTER TABLE user_plants
        ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW();
    END IF;

    -- Create trigger to update updated_at on row update
    CREATE OR REPLACE FUNCTION update_modified_column() 
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW; 
    END;
    $$ language 'plpgsql';

    DROP TRIGGER IF EXISTS update_user_plants_modtime ON user_plants;
    CREATE TRIGGER update_user_plants_modtime
    BEFORE UPDATE ON user_plants
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();

    RAISE NOTICE 'Successfully added missing columns to user_plants table';
EXCEPTION WHEN OTHERS THEN
    RAISE EXCEPTION 'Error adding columns to user_plants: %', SQLERRM;
END $$;
