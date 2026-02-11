import os
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv
from src.utils.logger import app_logger as logger

# 加载环境变量
load_dotenv()

class SupabaseManager:
    """
    Supabase 客户端管理器，实现单例模式并处理连接初始化。
    """
    _instance: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Client:
        if cls._instance is None:
            url: str = os.environ.get("SUPABASE_URL")
            # 优先使用 SERVICE_ROLE_KEY 进行非匿名访问
            # SERVICE_ROLE_KEY 具有绕过 RLS 的权限，适用于后端服务
            service_role_key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            anon_key: str = os.environ.get("SUPABASE_KEY")
            
            key = service_role_key or anon_key

            if not url:
                error_msg = "Missing SUPABASE_URL environment variable."
                logger.error(error_msg)
                raise ValueError(error_msg)

            if not key:
                error_msg = "Missing Supabase credentials. Please set SUPABASE_SERVICE_ROLE_KEY (recommended) or SUPABASE_KEY."
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            if not service_role_key:
                logger.warning("Using Anon Key for database access. This may be restricted by RLS policies. It is strongly recommended to use SUPABASE_SERVICE_ROLE_KEY for backend services.")
            else:
                logger.info("Initializing Supabase client with Service Role Key.")

            try:
                cls._instance = create_client(url, key)
                logger.info("Supabase client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                raise

        return cls._instance

def get_db_client() -> Client:
    """
    获取数据库客户端实例（单例）。
    如果环境变量配置错误，可能会抛出 ValueError。
    """
    return SupabaseManager.get_client()

# 为了兼容旧代码，尝试初始化一个全局实例
# 注意：如果配置缺失，这里可能会打印错误日志，但不会导致 import 失败（除非被直接调用）
# 建议新代码直接调用 get_db_client()
supabase: Optional[Client] = None
try:
    # 只有在明确需要时才初始化，或者在这里懒加载？
    # 为了保持向后兼容性（如果是直接 import supabase），我们尝试获取
    # 但为了避免在没有配置的环境（如测试环境）中 import 报错，我们要捕获异常
    if os.environ.get("SUPABASE_URL") and (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")):
        supabase = get_db_client()
except Exception as e:
    logger.warning(f"Could not initialize global supabase client on module import: {e}")
