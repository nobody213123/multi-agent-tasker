from models.item import Item, ChartData
from models.market import MarketIndex, MarketOverview, OnlineStats
from models.analysis import Recommendation, BacktestReport


class TestItemModel:
    def test_create_item(self):
        item = Item(id="123", name="蝴蝶刀（★）")
        assert item.id == "123"
        assert item.name == "蝴蝶刀（★）"
        assert item.buff_sell_price == 0.0

    def test_item_with_prices(self):
        item = Item(
            id="456",
            name="AK-47",
            buff_sell_price=1000.0,
            buff_buy_price=950.0,
            sell_price_rate_1=2.5,
        )
        assert item.buff_sell_price == 1000.0
        assert item.sell_price_rate_1 == 2.5


class TestChartData:
    def test_is_empty_with_few_points(self):
        chart = ChartData(timestamps=[1], prices=[100])
        assert chart.is_empty is True

    def test_is_not_empty_with_enough_points(self):
        chart = ChartData(timestamps=[1, 2], prices=[100, 102])
        assert chart.is_empty is False


class TestMarketOverview:
    def test_create_overview(self):
        overview = MarketOverview(
            indices=[
                MarketIndex(id=1, name="饰品指数", value=1500.0, change_pct=-1.5),
            ],
            online=OnlineStats(current=1000000, month_peak=2000000),
        )
        assert len(overview.indices) == 1
        assert overview.indices[0].name == "饰品指数"
        assert overview.online.current == 1000000


class TestRecommendation:
    def test_create_recommendation(self):
        rec = Recommendation(
            name="Test Item",
            strategy="买入",
            reason="上涨趋势",
            risk="波动",
            target_price="¥1000",
            signal_strength="强",
        )
        assert rec.strategy == "买入"
        assert rec.signal_strength == "强"


class TestBacktestReport:
    def test_summary_format(self):
        report = BacktestReport(
            total=100,
            hit=72,
            accuracy=0.72,
            period_days=7,
        )
        summary = report.summary
        assert "7 天" in summary
        assert "72" in summary
        assert "72.0%" in summary or "72%" in summary

    def test_zero_accuracy(self):
        report = BacktestReport(total=0, hit=0, accuracy=0.0, period_days=7)
        summary = report.summary
        assert "0" in summary
