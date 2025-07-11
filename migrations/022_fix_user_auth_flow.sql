-- Migration to fix user authentication flow and ensure users table consistency

-- Create a function to sync auth.users with public.users
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if user already exists in public.users
    IF NOT EXISTS (SELECT 1 FROM public.users WHERE id = NEW.id) THEN
        -- Insert the new user into public.users
        INSERT INTO public.users (
            id,
            email,
            full_name,
            is_admin,
            is_active,
            created_at,
            updated_at
        )
        VALUES (
            NEW.id,
            NEW.email,
            COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1)),
            COALESCE((NEW.raw_user_meta_data->>'is_admin')::boolean, false),
            true,
            NEW.created_at,
            NEW.updated_at
        )
        ON CONFLICT (id) DO NOTHING;
        
        -- Log the user creation
        INSERT INTO public.admin_activities (
            user_id,
            user_email,
            action,
            details
        )
        VALUES (
            NEW.id,
            NEW.email,
            'user_created',
            'User account created via auth trigger'
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create the trigger if it doesn't exist
DO $$
BEGIN
    -- Drop the trigger if it exists to avoid duplicates
    DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
    
    -- Create the trigger
    CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();
    
    RAISE NOTICE 'Created trigger for syncing auth.users to public.users';
EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'Error creating auth.users trigger: %', SQLERRM;
END;
$$;

-- Create a function to update public.users when auth.users is updated
CREATE OR REPLACE FUNCTION public.handle_updated_user()
RETURNS TRIGGER AS $$
BEGIN
    -- Update the corresponding user in public.users
    UPDATE public.users
    SET 
        email = NEW.email,
        updated_at = NOW()
    WHERE id = NEW.id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create the update trigger if it doesn't exist
DO $$
BEGIN
    -- Drop the trigger if it exists to avoid duplicates
    DROP TRIGGER IF EXISTS on_auth_user_updated ON auth.users;
    
    -- Create the trigger
    CREATE TRIGGER on_auth_user_updated
    AFTER UPDATE ON auth.users
    FOR EACH ROW
    WHEN (OLD.email IS DISTINCT FROM NEW.email)
    EXECUTE FUNCTION public.handle_updated_user();
    
    RAISE NOTICE 'Created update trigger for auth.users';
EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'Error creating auth.users update trigger: %', SQLERRM;
END;
$$;

-- Ensure the users table has all required columns
DO $$
BEGIN
    -- Add missing columns to users table if they don't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_schema = 'public' 
                  AND table_name = 'users' 
                  AND column_name = 'is_active') THEN
        ALTER TABLE public.users ADD COLUMN is_active boolean DEFAULT true;
        RAISE NOTICE 'Added is_active column to users table';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_schema = 'public' 
                  AND table_name = 'users' 
                  AND column_name = 'last_login') THEN
        ALTER TABLE public.users ADD COLUMN last_login timestamp with time zone;
        RAISE NOTICE 'Added last_login column to users table';
    END IF;
    
    -- Set default values for existing users
    UPDATE public.users 
    SET is_active = COALESCE(is_active, true)
    WHERE is_active IS NULL;
    
    -- Ensure all auth users have a corresponding users table entry
    INSERT INTO public.users (
        id,
        email,
        full_name,
        is_admin,
        is_active,
        created_at,
        updated_at
    )
    SELECT 
        id,
        email,
        COALESCE(raw_user_meta_data->>'full_name', split_part(email, '@', 1)),
        COALESCE((raw_user_meta_data->>'is_admin')::boolean, false),
        true,
        created_at,
        updated_at
    FROM auth.users
    WHERE id NOT IN (SELECT id FROM public.users)
    ON CONFLICT (id) DO UPDATE SET
        email = EXCLUDED.email,
        updated_at = NOW();
    
    RAISE NOTICE 'Ensured all auth users have corresponding public.users entries';
    
EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'Error ensuring users table consistency: %', SQLERRM;
END;
$$;
