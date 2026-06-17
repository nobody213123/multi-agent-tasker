from providers.interfaces import IndexProvider, RankProvider, SearchProvider, DetailProvider
from models.market import MarketOverview, MarketIndex, OnlineStats, GreedyStatus, RateStats
from models.item import Item, ChartData, SearchResult
from models.analysis import RankItem


class MockIndexProvider(IndexProvider):
    def fetch_indices(self) -> MarketOverview:
        return MarketOverview(
            indices=[
                MarketIndex(id=1, name="饰品指数", value=1570.33, change=-36.65, change_pct=-2.28),
                MarketIndex(id=2, name="租赁指数", value=570.64, change=-4.87, change_pct=-0.85),
                MarketIndex(id=3, name="匕首指数", value=511.94, change=1.10, change_pct=0.22),
            ],
            online=OnlineStats(current=1491883, month_peak=1492812, month_player=31361348),
            greedy=GreedyStatus(level="high", label="活跃"),
            rate=RateStats(day_up=5137, day_down=11153),
        )


class MockRankProvider(RankProvider):
    def fetch_ranks(self) -> dict[str, list[RankItem]]:
        return {
            "sell_price_rate_1": [
                RankItem(name="Mock 涨幅1", buff_sell_price=800, buff_price_chg=12.5, statistic=5000),
                RankItem(name="Mock 涨幅2", buff_sell_price=1200, buff_price_chg=8.3, statistic=3000),
            ],
            "buff_sell_num": [
                RankItem(name="Mock 数量1", buff_sell_price=100, buff_price_chg=2.1, statistic=100000),
            ],
        }


class MockSearchProvider(SearchProvider, DetailProvider):
    def search(self, keyword: str) -> list[SearchResult]:
        return [
            SearchResult(id="1", value=f"{keyword}（Mock）"),
            SearchResult(id="2", value=f"{keyword} | Mock Pattern"),
        ]

    def get_detail(self, item_id: str) -> Item:
        return Item(
            id=item_id,
            name=f"Mock Item {item_id}",
            buff_sell_price=1000.0,
            buff_buy_price=950.0,
            sell_price_rate_1=2.5,
            sell_price_rate_7=-1.2,
            buff_sell_num=500,
            buff_buy_num=100,
        )

    def get_chart(self, item_id: str) -> ChartData:
        return ChartData(
            timestamps=[1700000000000 + i * 86400000 for i in range(10)],
            prices=[float(1000 + i * 10) for i in range(10)],
            volumes=[100 + i * 5 for i in range(10)],
        )
