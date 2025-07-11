-- Function to count total users
CREATE OR REPLACE FUNCTION public.count_users()
RETURNS TABLE(count bigint)
LANGUAGE sql
AS $$
  SELECT COUNT(*) as count FROM auth.users WHERE email_confirmed_at IS NOT NULL;
$$;

-- Function to identify users needing attention
CREATE OR REPLACE FUNCTION public.get_users_needing_attention(min_entries integer DEFAULT 0)
RETURNS TABLE(
  id uuid,
  reasons text[]
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  WITH user_entries AS (
    SELECT 
      user_id,
      COUNT(*) as entry_count,
      MAX(created_at) as last_entry_date,
      COUNT(CASE WHEN sentiment_score < 0 THEN 1 END) as negative_entries,
      COUNT(CASE WHEN sentiment_score < -0.5 THEN 1 END) as very_negative_entries,
      COUNT(CASE WHEN created_at > (NOW() - INTERVAL '7 days') THEN 1 END) as recent_entries
    FROM journal_entries
    GROUP BY user_id
    HAVING COUNT(*) >= min_entries
  )
  SELECT 
    ue.user_id as id,
    array_remove(ARRAY[
      CASE WHEN ue.very_negative_entries > 0 THEN 'very_negative_entries'::text END,
      CASE WHEN ue.negative_entries > 3 THEN 'multiple_negative_entries'::text,
      CASE WHEN ue.recent_entries = 0 AND ue.entry_count > 0 THEN 'no_recent_entries'::text END
    ]) as reasons
  FROM user_entries ue
  WHERE 
    ue.very_negative_entries > 0 
    OR ue.negative_entries > 3
    OR (ue.recent_entries = 0 AND ue.entry_count > 0);
END;
$$;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION public.count_users() TO service_role;
GRANT EXECUTE ON FUNCTION public.get_users_needing_attention(integer) TO service_role;
