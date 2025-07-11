-- Migration to fix breathing_sessions table schema

-- First, check if the table exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables 
                  WHERE table_schema = 'public' 
                  AND table_name = 'breathing_sessions') THEN
        
        -- Create the table if it doesn't exist
        CREATE TABLE public.breathing_sessions (
            id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
            duration_seconds integer NOT NULL DEFAULT 0,
            pattern text,
            completed_at timestamp with time zone,
            created_at timestamp with time zone DEFAULT now(),
            updated_at timestamp with time zone DEFAULT now()
        );
        
        -- Add indexes
        CREATE INDEX idx_breathing_sessions_user_id ON public.breathing_sessions(user_id);
        CREATE INDEX idx_breathing_sessions_created_at ON public.breathing_sessions(created_at);
        
        -- Add RLS policies if using Row Level Security
        ALTER TABLE public.breathing_sessions ENABLE ROW LEVEL SECURITY;
        
        RAISE NOTICE 'Created breathing_sessions table';
    ELSE
        -- Table exists, check and add missing columns
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_schema = 'public' 
                      AND table_name = 'breathing_sessions' 
                      AND column_name = 'duration_seconds') THEN
            
            -- Add duration_seconds column if it doesn't exist
            ALTER TABLE public.breathing_sessions 
            ADD COLUMN duration_seconds integer NOT NULL DEFAULT 0;
            
            -- If we have an old 'duration' column, copy its values
            IF EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_schema = 'public' 
                      AND table_name = 'breathing_sessions' 
                      AND column_name = 'duration') THEN
                UPDATE public.breathing_sessions 
                SET duration_seconds = duration;
                
                -- Optionally drop the old column after migration
                -- ALTER TABLE public.breathing_sessions DROP COLUMN duration;
            END IF;
            
            RAISE NOTICE 'Added duration_seconds column to breathing_sessions';
        END IF;
        
        -- Ensure other columns exist with proper constraints
        PERFORM public.create_missing_columns(
            'public', 
            'breathing_sessions', 
            jsonb_build_object(
                'pattern', 'text',
                'completed_at', 'timestamp with time zone',
                'created_at', 'timestamp with time zone DEFAULT now()',
                'updated_at', 'timestamp with time zone DEFAULT now()'
            )
        );
        
        -- Add any missing indexes
        IF NOT EXISTS (SELECT 1 FROM pg_indexes 
                      WHERE tablename = 'breathing_sessions' 
                      AND indexname = 'idx_breathing_sessions_user_id') THEN
            CREATE INDEX idx_breathing_sessions_user_id ON public.breathing_sessions(user_id);
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM pg_indexes 
                      WHERE tablename = 'breathing_sessions' 
                      AND indexname = 'idx_breathing_sessions_created_at') THEN
            CREATE INDEX idx_breathing_sessions_created_at ON public.breathing_sessions(created_at);
        END IF;
        
        RAISE NOTICE 'Verified breathing_sessions table structure';
    END IF;
    
EXCEPTION WHEN OTHERS THEN
    RAISE EXCEPTION 'Error fixing breathing_sessions table: %', SQLERRM;
END $$;
