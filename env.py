"""
=================================================================
  环境变量加载模块
  职责：优先从 .env 文件加载环境变量
  必须在 import config 之前导入

  用法：
    import env  # 自动加载 .env
    from config import DASHSCOPE_API_KEY  # 此时已获取 .env 中的值

  测试时无需导入此模块，直接设置 os.environ 即可
=================================================================
"""
import os
from pathlib import Path

_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path, override=False)
    except ImportError:
        pass
