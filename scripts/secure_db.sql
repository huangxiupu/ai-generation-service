-- Enable Row Level Security (RLS) for all tables
-- This ensures that by default, no role can access data unless a specific policy grants permission.
-- The service_role key (used by the backend) bypasses RLS by default.

-- 1. Revoke default privileges from public role
-- This prevents the 'anon' and 'authenticated' roles from accessing tables by default.
REVOKE ALL ON SCHEMA public FROM public;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM public;

-- Grant usage on schema to anon and authenticated (so they can potentially access if policies allow)
GRANT USAGE ON SCHEMA public TO anon, authenticated;

-- 2. Enable RLS on all tables
ALTER TABLE books ENABLE ROW LEVEL SECURITY;
ALTER TABLE book_units ENABLE ROW LEVEL SECURITY;
ALTER TABLE book_sections ENABLE ROW LEVEL SECURITY;
ALTER TABLE reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE exercise_types ENABLE ROW LEVEL SECURITY;
ALTER TABLE section_exercise_recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE generated_exercises ENABLE ROW LEVEL SECURITY;
ALTER TABLE section_preprocessing ENABLE ROW LEVEL SECURITY;

-- 3. (Optional) Create policies
-- Since this is a backend service using service_role key, we strictly deny access to anon/authenticated by default.
-- No policies are added here, which implies a "Deny All" policy for anon/authenticated roles.

-- If you need to allow anon read access to specific tables (e.g. exercise_types), uncomment below:
-- CREATE POLICY "Allow public read access" ON exercise_types FOR SELECT TO anon USING (true);
