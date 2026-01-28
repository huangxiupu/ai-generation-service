import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Missing Supabase credentials")
    exit(1)

supabase: Client = create_client(url, key)

res = supabase.table("book_sections").select("id").limit(1).execute()
if res.data:
    print(f"Valid section ID: {res.data[0]['id']}")
else:
    print("No sections found")
