import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
# 优先使用 SERVICE_ROLE_KEY 进行非匿名访问
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Missing Supabase credentials (SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY/SUPABASE_KEY)")
    exit(1)

supabase: Client = create_client(url, key)

res = supabase.table("book_sections").select("id").limit(1).execute()
if res.data:
    print(f"Valid section ID: {res.data[0]['id']}")
else:
    print("No sections found")
