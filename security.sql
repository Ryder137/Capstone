-- Additional Security Measures

-- Enable pg_stat_statements for query monitoring
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Enable pgcrypto for additional encryption capabilities
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Create a function to validate email format
CREATE OR REPLACE FUNCTION validate_email(email text)
RETURNS boolean AS $$
BEGIN
    RETURN email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$';
END;
$$ LANGUAGE plpgsql;

-- Create a function to validate password strength
CREATE OR REPLACE FUNCTION validate_password(password text)
RETURNS boolean AS $$
BEGIN
    RETURN LENGTH(password) >= 8 
        AND password ~* '[A-Z]' 
        AND password ~* '[a-z]' 
        AND password ~* '[0-9]';
END;
$$ LANGUAGE plpgsql;

-- Add constraints to users table
ALTER TABLE users 
ADD CONSTRAINT valid_email CHECK (validate_email(email)),
ADD CONSTRAINT valid_password CHECK (validate_password(password_hash));

-- Add audit logs for sensitive operations
CREATE TABLE audit_logs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    table_name VARCHAR NOT NULL,
    operation VARCHAR NOT NULL,
    user_id UUID,
    old_data JSONB,
    new_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create function for logging
CREATE OR REPLACE FUNCTION log_audit()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_logs (table_name, operation, user_id, old_data, new_data)
    VALUES (
        TG_TABLE_NAME,
        TG_OP,
        NEW.user_id,
        CASE WHEN TG_OP = 'UPDATE' THEN to_jsonb(OLD) ELSE NULL END,
        CASE WHEN TG_OP = 'UPDATE' THEN to_jsonb(NEW) ELSE to_jsonb(NEW) END
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for audit logging
CREATE TRIGGER audit_users
AFTER INSERT OR UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION log_audit();

CREATE TRIGGER audit_appointments
AFTER INSERT OR UPDATE ON appointments
FOR EACH ROW
EXECUTE FUNCTION log_audit();

-- Create indexes for better performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_journal_entries_user ON journal_entries(user_id);
CREATE INDEX idx_chat_history_user ON chat_history(user_id);
CREATE INDEX idx_game_scores_user ON game_scores(user_id);
CREATE INDEX idx_breathing_sessions_user ON breathing_sessions(user_id);
CREATE INDEX idx_appointments_user ON appointments(user_id);
CREATE INDEX idx_appointments_doctor ON appointments(doctor_id);
CREATE INDEX idx_doctors_name ON doctors(name);
CREATE INDEX idx_doctors_specialty ON doctors(specialty);
