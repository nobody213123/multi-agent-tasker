from observability.logger import get_logger
from tools.providers.interfaces import IndexProvider, RankProvider, SearchProvider, DetailProvider
from models.market import (
    MarketOverview, MarketIndex, OnlineStats, GreedyStatus, RateStats,
)
from models.item import Item, ChartData, SearchResult
from models.analysis import RankItem

log = get_logger(__name__)


class CsqaqIndexProvider(IndexProvider):
    """包装 tools/index_api.py，返回 typed 数据"""

    def fetch_indices(self) -> MarketOverview:
        from tools.index_api import fetch_indices

        raw = fetch_indices()
        indices = [
            MarketIndex(
                id=i["id"],
                name=i["name"],
                value=i["value"],
                change=i["change"],
                change_pct=i["change_pct"],
                high=i.get("high", 0),
                low=i.get("low", 0),
            )
            for i in raw.get("indices", [])
        ]
        on = raw.get("online", {})
        gr = raw.get("greedy", {})
        rt = raw.get("rate", {})

        return MarketOverview(
            indices=indices,
            online=OnlineStats(
                current=on.get("current", 0),
                today_peak=on.get("today_peak", 0),
                month_peak=on.get("month_peak", 0),
                month_player=on.get("month_player", 0),
                rate=on.get("rate", 0),
            ),
            greedy=GreedyStatus(
                level=gr.get("level", "unknown"),
                label=gr.get("label", "未知"),
            ),
            rate=RateStats(
                day_up=rt.get("day_up", 0),
                day_down=rt.get("day_down", 0),
                day_flat=rt.get("day_flat", 0),
                week_up=rt.get("week_up", 0),
                week_down=rt.get("week_down", 0),
                week_flat=rt.get("week_flat", 0),
            ),
        )


class CsqaqRankProvider(RankProvider):
    """包装 tools/recommend.py 的榜单采集逻辑"""

    def fetch_ranks(self) -> dict[str, list[RankItem]]:
        from playwright.sync_api import sync_playwright, TimeoutError

        all_data = {}
        tab_map = {
            "price":    "价格榜",
            "hot":      "热门榜",
            "supply":   "存世量榜",
            "turnover": "成交榜",
            "diff":     "平台差价榜",
        }

        def on_resp(resp):
            if "get_rank_list" in resp.url:
                try:
                    j = resp.json()
                    if j.get("code") == 200:
                        key = j.get("msg", "unknown")
                        all_data[key] = j["data"].get("data", [])
                except ValueError:
                    log.warning("榜单 API 返回非 JSON 响应: %s", resp.url)

        try:
            pw = sync_playwright().start()
            browser = pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            page = browser.new_page()
            page.on("response", on_resp)
            page.goto("https://csqaq.com/rank", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)
            for tab_name in tab_map.values():
                try:
                    page.click(f'text="{tab_name}"')
                    page.wait_for_timeout(1500)
                except TimeoutError:
                    log.warning("点击榜单 %s 超时，跳过", tab_name)
            browser.close()
            pw.stop()
            log.info("排行榜数据采集完成，共 %d 个榜单", len(all_data))
        except TimeoutError:
            log.error("排行榜页面加载超时")
        except Exception as e:
            log.error("排行榜采集异常: %s", e)

        return {
            k: [RankItem.from_dict(item) for item in items]
            for k, items in all_data.items()
        }


class CsqaqSearchProvider(SearchProvider, DetailProvider):
    """包装 tools/item_api.py，返回 typed 数据"""

    def __init__(self):
        self._api: ItemAPI | None = None

    def _ensure_api(self):
        if self._api is None:
            from tools.item_api import ItemAPI
            self._api = ItemAPI()

    def search(self, keyword: str) -> list[SearchResult]:
        self._ensure_api()
        raw = self._api.search(keyword)
        return [
            SearchResult(id=r["id"], value=r["value"])
            for r in raw
        ]

    def get_detail(self, item_id: str) -> Item:
        self._ensure_api()
        raw = self._api.get_detail_and_chart(item_id)
        detail = raw.get("detail", {})
        return Item(
            id=item_id,
            name=detail.get("name", ""),
            market_hash_name=detail.get("market_hash_name", ""),
            type_name=detail.get("type_localized_name", ""),
            buff_sell_price=detail.get("buff_sell_price", 0) or 0,
            buff_buy_price=detail.get("buff_buy_price", 0) or 0,
            buff_sell_num=detail.get("buff_sell_num", 0) or 0,
            buff_buy_num=detail.get("buff_buy_num", 0) or 0,
            yyyp_sell_price=detail.get("yyyp_sell_price", 0) or 0,
            yyyp_buy_price=detail.get("yyyp_buy_price", 0) or 0,
            yyyp_sell_num=detail.get("yyyp_sell_num", 0) or 0,
            yyyp_lease_price=detail.get("yyyp_lease_price", 0) or 0,
            yyyp_long_lease_price=detail.get("yyyp_long_lease_price", 0) or 0,
            steam_sell_price=detail.get("steam_sell_price", 0) or 0,
            steam_buy_price=detail.get("steam_buy_price", 0) or 0,
            sell_price_rate_1=detail.get("sell_price_rate_1", 0) or 0,
            sell_price_rate_7=detail.get("sell_price_rate_7", 0) or 0,
            sell_price_rate_15=detail.get("sell_price_rate_15", 0) or 0,
            sell_price_rate_30=detail.get("sell_price_rate_30", 0) or 0,
            statistic=detail.get("statistic", 0) or 0,
        )

    def get_chart(self, item_id: str) -> ChartData:
        self._ensure_api()
        raw = self._api.get_detail_and_chart(item_id)
        chart = raw.get("chart", {})
        return ChartData(
            timestamps=chart.get("timestamps", []),
            prices=chart.get("prices", []),
            volumes=chart.get("volumes", []),
        )

    def close(self):
        if self._api:
            self._api.close()
            self._api = None
