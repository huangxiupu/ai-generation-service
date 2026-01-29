import logging
import os
import sys
from datetime import datetime

# 确保 logs 目录存在
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def setup_logger(name: str, log_file: str, level=logging.INFO):
    """设置日志记录器"""
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 文件处理器
    file_handler = logging.FileHandler(os.path.join(LOG_DIR, log_file), encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # 避免日志向上传递到 root logger 导致重复打印
    logger.propagate = False
    
    return logger

# 创建专用于 LLM 输入输出的日志记录器
llm_logger = setup_logger('llm', 'llm.log')
# 创建通用的应用日志记录器
app_logger = setup_logger('app', 'app.log')
