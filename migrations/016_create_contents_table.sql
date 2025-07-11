-- Create contents table for storing dynamic content
CREATE TABLE IF NOT EXISTS public.contents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Content details
    title TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    content_type TEXT NOT NULL,  -- e.g., 'page', 'post', 'faq', 'announcement'
    content TEXT NOT NULL,
    excerpt TEXT,
    status TEXT NOT NULL DEFAULT 'draft',  -- 'draft', 'published', 'archived'
    published_at TIMESTAMPTZ,
    
    -- SEO and metadata
    meta_title TEXT,
    meta_description TEXT,
    meta_keywords TEXT[],
    
    -- Relationships
    author_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    
    -- Indexes
    CONSTRAINT unique_slug UNIQUE (slug)
);

-- Enable Row Level Security
ALTER TABLE public.contents ENABLE ROW LEVEL SECURITY;

-- Create indexes for faster lookups
CREATE INDEX idx_contents_slug ON public.contents(slug);
CREATE INDEX idx_contents_content_type ON public.contents(content_type);
CREATE INDEX idx_contents_status ON public.contents(status);
CREATE INDEX idx_contents_published_at ON public.contents(published_at);

-- RLS Policies
-- Allow public read access to published content
CREATE POLICY "Public content is viewable by everyone"
ON public.contents
FOR SELECT
USING (status = 'published');

-- Allow authenticated users to view all content
CREATE POLICY "Authenticated users can view all content"
ON public.contents
FOR SELECT
TO authenticated
USING (true);

-- Allow authors to manage their own content
CREATE POLICY "Users can manage their own content"
ON public.contents
FOR ALL
TO authenticated
USING (auth.uid() = author_id)
WITH CHECK (auth.uid() = author_id);

-- Allow admins to manage all content
CREATE POLICY "Admins have full access to all content"
ON public.contents
FOR ALL
TO authenticated
USING (EXISTS (
    SELECT 1 FROM auth.users
    WHERE id = auth.uid() AND raw_user_meta_data->>'is_admin' = 'true'
));

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create a trigger to update the updated_at column
CREATE TRIGGER update_contents_updated_at
BEFORE UPDATE ON public.contents
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Add comments for better documentation
COMMENT ON TABLE public.contents IS 'Stores dynamic content such as pages, posts, and announcements';
COMMENT ON COLUMN public.contents.content_type IS 'Type of content (e.g., page, post, faq, announcement)';
COMMENT ON COLUMN public.contents.status IS 'Publication status (draft, published, archived)';

-- Insert some default content if the table is empty
INSERT INTO public.contents (
    title, 
    slug, 
    content_type, 
    content, 
    excerpt, 
    status, 
    published_at, 
    author_id
) VALUES (
    'Welcome to UniCare',
    'welcome',
    'page',
    '<h1>Welcome to UniCare</h1><p>Your mental wellbeing companion at the University of the Philippines Cebu.</p>',
    'Welcome to our platform',
    'published',
    NOW(),
    (SELECT id FROM auth.users WHERE email = 'admin@example.com' LIMIT 1)
) ON CONFLICT (slug) DO NOTHING;
