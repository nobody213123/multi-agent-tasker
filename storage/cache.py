import json
import os

from config import CACHE_FILE_PATH


class CacheStorage:
    """快速缓存：存储上一轮数据，用于 Agent 对比"""

    def __init__(self, path: str | None = None):
        self._path = path or CACHE_FILE_PATH

    def save(self, data: dict) -> None:
        cache_dir = os.path.dirname(self._path)
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load(self) -> dict:
        if not os.path.exists(self._path):
            return {}
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
