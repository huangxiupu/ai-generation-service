import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("警告：在环境变量中未找到 SUPABASE_URL 或 SUPABASE_KEY。")
    supabase: Client = None
else:
    supabase: Client = create_client(url, key)

def get_db_client() -> Client:
    """
    获取数据库客户端实例。
    """
    return supabase
