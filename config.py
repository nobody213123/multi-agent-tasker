"""
=================================================================
  全局配置文件（纯常量定义，无副作用）
  所有值从 os.environ 读取，不自动加载 .env
  调用方（main.py / web/app.py）需在 import 前先执行 load_env()
=================================================================
"""
import os
from pathlib import Path

# ============================================================
#  阿里云百炼（DashScope）大模型配置
# ============================================================
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen-turbo")
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.0"))

# ============================================================
#  监控目标配置
# ============================================================
MONITOR_URL = os.environ.get("MONITOR_URL", "https://csqaq.com")

# ============================================================
#  轮询时间间隔（单位：秒）
# ============================================================
POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "300"))

# ============================================================
#  HTTP 请求头伪装
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

REQUEST_TIMEOUT = 30
RENDER_TIMEOUT = 30

# ============================================================
#  缓存文件路径
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE_PATH = os.path.join(BASE_DIR, "cache", "data_cache.json")
