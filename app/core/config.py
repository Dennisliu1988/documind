# 读取 .env，全局配置# app/core/config.py
import os

from dotenv import load_dotenv

# 加载 .env
load_dotenv()

# 开启国内镜像下载模型
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

class Settings:
    # 大模型配置 (这里默认用 DeepSeek，如果用通义，改这里)
    LLM_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL: str = "deepseek-chat"
    
    # Embedding 配置 (使用通义千问)
    EMBEDDING_API_KEY: str = os.getenv("QWEN_API_KEY", "")
    EMBEDDING_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    EMBEDDING_MODEL: str = "text-embedding-v2"
    
    # 向量数据库路径
    CHROMA_DB_DIR: str = "./chroma_db"
    
    # Rerank 模型名称
    RERANK_MODEL: str = "BAAI/bge-reranker-base"

# 实例化全局配置对象
settings = Settings()