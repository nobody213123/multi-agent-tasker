"""
==========================================================
  全局配置文件
  存放 API 密钥、监控网址、轮询间隔、请求头等全局参数
==========================================================
"""
import os
from pathlib import Path

# ----------------------------------------------------------
#  从 .env 文件加载环境变量（若存在）
#  优先级：.env 文件 → 系统环境变量
# ----------------------------------------------------------
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path, override=False)
        print(f"  ✅ 已加载环境变量: {_env_path}")
    except ImportError:
        print("  ⚠️  检测到 .env 文件但 python-dotenv 未安装")
        print("  💡 安装: pip install python-dotenv")
        print("  💡 或将 .env 中的变量通过 export 设置到系统环境")

# ============================================================
#  阿里云百炼（DashScope）大模型配置
# ============================================================
# API 密钥优先从 .env 读取，回退到系统环境变量
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")

# 大模型名称（可选值：qwen-turbo、qwen-plus、qwen-max）
# 可通过 .env 中 LLM_MODEL 覆盖
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen-turbo")

# 模型温度参数（0~1，值越小输出越确定）
LLM_TEMPERATURE = 0.0

# ============================================================
#  监控目标配置
# ============================================================
# 可通过 .env 中 MONITOR_URL 覆盖
MONITOR_URL = os.environ.get("MONITOR_URL", "https://csqaq.com")

# ============================================================
#  轮询时间间隔（单位：秒）
# ============================================================
# 可通过 .env 中 POLL_INTERVAL_SECONDS 覆盖
POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "300"))

# ============================================================
#  HTTP 请求头伪装（模拟正常浏览器访问）
# ============================================================
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
}

# ============================================================
#  请求超时设置
# ============================================================
REQUEST_TIMEOUT = 30  # 秒

# ============================================================
#  Playwright 浏览器渲染超时
# ============================================================
RENDER_TIMEOUT = 30  # 秒，等待 JS 渲染完成的最大时间

# ============================================================
#  缓存文件路径
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE_PATH = os.path.join(BASE_DIR, "cache", "data_cache.json")
