"""
=================================================================
  本地数据缓存模块
  功能：保存上一轮抓取的解析结果至 JSON 文件，
        用于新旧数据对比（涨跌判断、异动识别）
=================================================================
"""
import json
import os

from config import CACHE_FILE_PATH


def save_cache(data: dict) -> None:
    """
    将解析后的数据写入本地缓存文件

    参数:
        data: 需要缓存的数据字典（如 {"price": 100, "change": "+2.5%"}）
    """
    cache_dir = os.path.dirname(CACHE_FILE_PATH)
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    try:
        with open(CACHE_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  📦 缓存已更新 → {CACHE_FILE_PATH}")
    except Exception as e:
        print(f"  ⚠️  缓存写入失败: {e}")


def load_cache() -> dict:
    """
    从本地缓存文件读取上一轮的历史数据

    返回:
        缓存的数据字典；若文件不存在或损坏则返回空字典
    """
    if not os.path.exists(CACHE_FILE_PATH):
        print("  📭 暂无历史缓存数据，这是首次运行")
        return {}

    try:
        with open(CACHE_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"  📖 已读取历史缓存数据")
        return data
    except (json.JSONDecodeError, Exception) as e:
        print(f"  ⚠️  缓存文件损坏，将重置缓存: {e}")
        return {}
