"""
=================================================================
  饰品数据查询 API 封装模块
  功能：通过 csqaq.com 的前端 API 查询饰品信息、
        商品详情、价格走势图数据
=================================================================
"""
import json
import time


class ItemAPI:
    """饰品数据查询工具（封装 csqaq.com 前端 API）"""

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._responses = {}

    # ----------------------------------------------------------
    #  浏览器会话管理
    # ----------------------------------------------------------
    def _ensure_session(self):
        """确保浏览器会话已建立"""
        if self._page is not None:
            return

        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()

        self._browser = self._playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        self._context = self._browser.new_context(locale="zh-CN")
        self._page = self._context.new_page()

        # 访问首页建立会话
        self._page.goto("https://csqaq.com", wait_until="networkidle", timeout=30000)
        self._page.wait_for_timeout(2000)

    def _clear_responses(self):
        """清空已收集的响应"""
        self._responses = {}

    def _response_collector(self, url_pattern):
        """返回一个 response 处理器，收集匹配的响应"""
        def _collector(resp):
            if url_pattern in resp.url:
                try:
                    j = resp.json()
                    self._responses[resp.url] = j
                except Exception:
                    pass
        return _collector

    def close(self):
        """关闭浏览器会话"""
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None

    # ----------------------------------------------------------
    #  搜索饰品
    # ----------------------------------------------------------
    def search(self, keyword: str) -> list:
        """
        搜索饰品，返回匹配的商品列表

        参数:
            keyword: 搜索关键词（如 "蝴蝶刀"、"AK-47"）

        返回:
            [{"id": "6796", "value": "蝴蝶刀（★）"}, ...]
        """
        self._ensure_session()

        self._clear_responses()
        handler = self._response_collector("search/suggest")
        self._page.on("response", handler)

        # 通过键盘操作触发搜索
        self._page.keyboard.press("/")
        self._page.wait_for_timeout(300)

        # 清空输入框（全选后删除）
        self._page.keyboard.press("Control+A")
        self._page.keyboard.press("Delete")
        self._page.keyboard.type(keyword)
        self._page.wait_for_timeout(1500)

        # 提取搜索结果
        results = []
        for url, data in self._responses.items():
            if data.get("code") == 200:
                results = data.get("data", [])

        # 清理
        self._page.remove_listener("response", handler)
        self._page.keyboard.press("Escape")
        self._page.wait_for_timeout(200)

        return results

    # ----------------------------------------------------------
    #  获取商品详情 + 图表数据
    # ----------------------------------------------------------
    def get_detail_and_chart(self, item_id: str, period: str = "30") -> dict:
        """
        获取商品详情和价格走势数据

        参数:
            item_id: 商品 ID（从 search 方法获取）
            period:  时间范围 "7" / "15" / "30" / "90" / "180" / "365"

        返回:
            {
                "detail": { ...商品详情... },
                "chart": {
                    "timestamps": [...],
                    "prices": [...],
                    "volumes": [...]
                }
            }
            若失败则返回 {"error": "说明"}
        """
        self._ensure_session()
        self._clear_responses()

        goods_url = f"https://csqaq.com/goods/{item_id}"
        detail_key = "info/good"
        chart_key = "info/chart"

        detail_data = None
        chart_data = None

        def _collector(resp):
            nonlocal detail_data, chart_data
            try:
                j = resp.json()
                if detail_key in resp.url and j.get("code") == 200:
                    detail_data = j["data"]["goods_info"]
                if chart_key in resp.url and j.get("code") == 200:
                    chart_data = j["data"]
            except Exception:
                pass

        self._page.on("response", _collector)

        try:
            self._page.goto(goods_url, wait_until="networkidle", timeout=30000)
            self._page.wait_for_timeout(2000)
        except Exception as e:
            self._page.remove_listener("response", _collector)
            return {"error": f"加载商品页失败: {e}"}

        self._page.remove_listener("response", _collector)

        result = {}

        if detail_data:
            result["detail"] = detail_data
        else:
            result["error"] = "未能获取商品详情"

        if chart_data:
            ts = chart_data.get("timestamp", [])
            prices = chart_data.get("main_data", [])
            volumes = chart_data.get("num_data", [])

            # 过滤有效数据点
            valid = [(t, p, v) for t, p, v in zip(ts, prices, volumes) if p > 0]
            if valid:
                result["chart"] = {
                    "timestamps": [v[0] for v in valid],
                    "prices": [v[1] for v in valid],
                    "volumes": [v[2] for v in valid],
                }
            else:
                result["chart"] = {"timestamps": [], "prices": [], "volumes": []}
        else:
            result["chart"] = {"timestamps": [], "prices": [], "volumes": []}

        return result
