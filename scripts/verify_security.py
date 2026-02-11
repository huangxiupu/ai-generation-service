import os
import sys
# 添加项目根目录到 sys.path，以便可以导入 src
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from supabase import create_client
from src.utils.logger import app_logger as logger

# 加载环境变量
load_dotenv()

def verify_security():
    """
    验证 Supabase 的安全配置。
    1. 检查 Anon Key 是否被限制（RLS 生效）。
    2. 检查 Service Role Key 是否拥有访问权限。
    """
    url = os.environ.get("SUPABASE_URL")
    anon_key = os.environ.get("SUPABASE_KEY")
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not anon_key or not service_role_key:
        logger.error("Missing credentials in .env file for verification. Ensure SUPABASE_URL, SUPABASE_KEY, and SUPABASE_SERVICE_ROLE_KEY are set.")
        print("Error: Missing credentials. Please check logs/app.log or set environment variables.")
        return

    logger.info("Starting security verification...")
    print("Starting security verification...")

    # 1. 验证 Anon Key 访问 (预期：受限)
    logger.info("--- Testing Anon Key Access (Should be restricted) ---")
    print("\n--- Testing Anon Key Access (Should be restricted) ---")
    try:
        anon_client = create_client(url, anon_key)
        
        # 尝试读取 exercise_types
        # 如果 RLS 开启且无策略，应该返回空列表
        try:
            res = anon_client.table("exercise_types").select("*").limit(1).execute()
            if not res.data:
                 msg = "✅ Anon Key read access restricted (no data returned)."
                 logger.info(msg)
                 print(msg)
            else:
                 msg = f"⚠️ Anon Key retrieved data: {res.data}. Check if RLS is enabled and policies are configured correctly."
                 logger.warning(msg)
                 print(msg)
        except Exception as e:
            msg = f"✅ Anon Key read attempt failed/restricted: {e}"
            logger.info(msg)
            print(msg)
        
        # 尝试写入 (预期：失败)
        try:
            # 尝试插入一个假数据
            anon_client.table("exercise_types").insert({
                "code": "security_test", 
                "name": "Security Test",
                "structure_schema": {}
            }).execute()
            msg = "❌ Anon Key was able to INSERT data! Security failure."
            logger.error(msg)
            print(msg)
        except Exception as e:
            # postgrest.exceptions.APIError: {'code': '42501', 'details': None, 'hint': None, 'message': 'new row violates row-level security policy for table "exercise_types"'}
            if "42501" in str(e) or "row-level security" in str(e):
                 msg = "✅ Anon Key write attempt blocked by RLS as expected."
                 logger.info(msg)
                 print(msg)
            else:
                 msg = f"✅ Anon Key write attempt failed: {e}"
                 logger.info(msg)
                 print(msg)

    except Exception as e:
        logger.info(f"✅ Anon Key access failed/restricted: {e}")
        print(f"✅ Anon Key access failed/restricted: {e}")

    # 2. 验证 Service Role Key 访问 (预期：成功)
    logger.info("--- Testing Service Role Key Access (Should succeed) ---")
    print("\n--- Testing Service Role Key Access (Should succeed) ---")
    try:
        sr_client = create_client(url, service_role_key)
        
        # 尝试读取
        res = sr_client.table("exercise_types").select("count", count="exact").execute()
        msg = f"✅ Service Role Key read access successful. Total rows: {res.count}"
        logger.info(msg)
        print(msg)
        
    except Exception as e:
        msg = f"❌ Service Role Key access failed: {e}"
        logger.error(msg)
        print(msg)

if __name__ == "__main__":
    verify_security()
