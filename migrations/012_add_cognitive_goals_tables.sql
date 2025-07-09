-- Create cognitive reframing challenges table
CREATE TABLE IF NOT EXISTS cognitive_reframing_challenges (
    id SERIAL PRIMARY KEY,
    negative_thought TEXT NOT NULL,
    category VARCHAR(50),
    difficulty_level INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create user goal categories
CREATE TABLE IF NOT EXISTS goal_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description TEXT,
    icon VARCHAR(50)
);

-- Create user goals table
CREATE TABLE IF NOT EXISTS user_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    category_id INTEGER REFERENCES goal_categories(id),
    target_value NUMERIC,
    current_value NUMERIC DEFAULT 0,
    target_date TIMESTAMP WITH TIME ZONE,
    frequency VARCHAR(20), -- daily, weekly, monthly, once
    xp_reward INTEGER DEFAULT 10,
    is_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Create badges table
CREATE TABLE IF NOT EXISTS badges (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(50) NOT NULL,
    xp_required INTEGER DEFAULT 0,
    criteria_type VARCHAR(50), -- 'xp_level', 'goal_count', 'streak', etc.
    criteria_value INTEGER
);

-- Create user achievements table
CREATE TABLE IF NOT EXISTS user_achievements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    badge_id INTEGER REFERENCES badges(id),
    xp_earned INTEGER DEFAULT 0,
    current_level INTEGER DEFAULT 1,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_activity_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Create user badge awards
CREATE TABLE IF NOT EXISTS user_badges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    badge_id INTEGER NOT NULL REFERENCES badges(id),
    earned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, badge_id)
);

-- Create user reframing responses
CREATE TABLE IF NOT EXISTS user_reframing_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    challenge_id INTEGER REFERENCES cognitive_reframing_challenges(id),
    original_thought TEXT,
    reframed_thought TEXT NOT NULL,
    is_helpful BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert some default goal categories
INSERT INTO goal_categories (name, description, icon) VALUES
('Health', 'Physical and mental health goals', 'heart-pulse'),
('Productivity', 'Work and productivity goals', 'briefcase'),
('Learning', 'Educational and skill development goals', 'graduation-cap'),
('Social', 'Relationship and social goals', 'users'),
('Personal', 'Personal development goals', 'user'),
('Hobbies', 'Hobby and interest goals', 'paint-brush');

-- Insert some default badges
INSERT INTO badges (name, description, icon, xp_required, criteria_type, criteria_value) VALUES
('First Steps', 'Complete your first goal', 'trophy', 0, 'goal_count', 1),
('Goal Getter', 'Complete 5 goals', 'trophy', 50, 'goal_count', 5),
('Goal Master', 'Complete 25 goals', 'trophy', 250, 'goal_count', 25),
('Early Bird', 'Complete a goal before 9 AM', 'sun', 30, 'streak', 3),
('Consistency', '7-day streak', 'flame', 100, 'streak', 7),
('Dedication', '30-day streak', 'award', 500, 'streak', 30);

-- Insert some cognitive reframing challenges
INSERT INTO cognitive_reframing_challenges (negative_thought, category, difficulty_level) VALUES
('I always mess things up.', 'self_esteem', 1),
('Nothing ever goes my way.', 'pessimism', 1),
('I''m not good enough for this job.', 'self_doubt', 2),
('Everyone is judging me.', 'social_anxiety', 2),
('I''ll never get better at this.', 'frustration', 1),
('I should be doing more with my life.', 'self_expectation', 3),
('No one understands me.', 'loneliness', 2),
('I''m going to fail this test.', 'anxiety', 1),
('I''m not as successful as I should be.', 'comparison', 3),
('I can''t handle this stress.', 'overwhelm', 2);

-- Create function to update timestamps
CREATE OR REPLACE FUNCTION update_modified_column() 
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW; 
END;
$$ language 'plpgsql';

-- Create triggers for all tables that need updated_at
CREATE TRIGGER update_cognitive_reframing_challenges_modtime
BEFORE UPDATE ON cognitive_reframing_challenges
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_user_goals_modtime
BEFORE UPDATE ON user_goals
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_user_achievements_modtime
BEFORE UPDATE ON user_achievements
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

-- Enable RLS on new tables
ALTER TABLE cognitive_reframing_challenges ENABLE ROW LEVEL SECURITY;
ALTER TABLE goal_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE badges ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_achievements ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_badges ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_reframing_responses ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for cognitive_reframing_challenges
CREATE POLICY "Enable read access for all users" 
ON cognitive_reframing_challenges 
FOR SELECT 
TO authenticated, anon
USING (true);

-- Create RLS policies for user_goals
CREATE POLICY "Users can manage their own goals" 
ON user_goals 
FOR ALL 
TO authenticated
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- Create RLS policies for user_achievements
CREATE POLICY "Users can view their own achievements" 
ON user_achievements 
FOR SELECT 
TO authenticated
USING (auth.uid() = user_id);

-- Create RLS policies for user_badges
CREATE POLICY "Users can view their own badges" 
ON user_badges 
FOR SELECT 
TO authenticated
USING (auth.uid() = user_id);

-- Create RLS policies for user_reframing_responses
CREATE POLICY "Users can manage their own responses" 
ON user_reframing_responses 
FOR ALL 
TO authenticated
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);
