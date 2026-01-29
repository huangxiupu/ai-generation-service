import logging
import os
import sys
import json
from datetime import datetime

# 确保 logs 目录存在
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def setup_logger(name: str, log_file: str, level=logging.INFO, format_str: str = None):
    """设置日志记录器"""
    if format_str is None:
        format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    formatter = logging.Formatter(format_str)
    
    # 文件处理器
    file_path = os.path.join(LOG_DIR, log_file)
    file_handler = logging.FileHandler(file_path, encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 清除旧的 handler
    if logger.hasHandlers():
        logger.handlers.clear()
        
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # 避免日志向上传递到 root logger 导致重复打印
    logger.propagate = False
    
    return logger

def format_llm_request(model: str, messages: list) -> str:
    """将 LLM 请求格式化为 Markdown"""
    parts = ["\n" + "### 🤖 LLM REQUEST START " + "="*20]
    parts.append(f"- **Model**: `{model}`")
    parts.append("- **Messages**:")
    
    for msg in messages:
        role = msg.get('role', 'unknown').upper()
        content = msg.get('content', '')
        # 处理可能的 dict 内容（如多模态）
        if isinstance(content, list):
            content_str = json.dumps(content, ensure_ascii=False, indent=2)
        else:
            content_str = content
            
        parts.append(f"  - **{role}**:")
        # 为内容添加缩进以保持 Markdown 结构，或者使用引用块
        indented_content = "\n".join([f"    > {line}" for line in content_str.splitlines()])
        parts.append(indented_content)
    
    return "\n".join(parts)

def format_llm_response(content: str) -> str:
    """将 LLM 响应格式化为 Markdown"""
    parts = ["- **ASSISTANT (RESPONSE)**:"]
    # 尝试判断是否为 JSON，如果是则加上 json 语法高亮
    trimmed_content = content.strip()
    if trimmed_content.startswith(('{', '[')):
        try:
            # 尝试美化 JSON
            parsed = json.loads(trimmed_content)
            formatted_json = json.dumps(parsed, ensure_ascii=False, indent=2)
            parts.append(f"```json\n{formatted_json}\n```")
        except:
            parts.append(f"```json\n{trimmed_content}\n```")
    else:
        parts.append(content)
    parts.append("### 🤖 LLM REQUEST END " + "="*20 + "\n")
    return "\n".join(parts)

# 创建专用于 LLM 输入输出的日志记录器
# LLM 日志使用更简单的格式，方便阅读 Markdown
llm_logger = setup_logger('llm', 'llm.log', format_str='%(asctime)s [%(levelname)s] %(message)s')
# 创建通用的应用日志记录器
app_logger = setup_logger('app', 'app.log')
