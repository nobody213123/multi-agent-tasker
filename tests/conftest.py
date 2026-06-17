import pytest

from models.market import MarketOverview, MarketIndex, OnlineStats, GreedyStatus, RateStats
from models.analysis import CollectedData, AnalysisResult, TrendSignal, Recommendation, BreakdownItem, RankItem
from tools.providers.mock import MockIndexProvider, MockRankProvider, MockSearchProvider


@pytest.fixture
def mock_index_provider():
    return MockIndexProvider()


@pytest.fixture
def mock_rank_provider():
    return MockRankProvider()


@pytest.fixture
def mock_search_provider():
    return MockSearchProvider()


@pytest.fixture
def sample_market_overview():
    return MarketOverview(
        indices=[
            MarketIndex(id=1, name="饰品指数", value=1570.33, change=-36.65, change_pct=-2.28),
            MarketIndex(id=2, name="租赁指数", value=570.64, change=-4.87, change_pct=-0.85),
        ],
        online=OnlineStats(current=1000000, month_peak=1500000, month_player=30000000),
        greedy=GreedyStatus(level="high", label="活跃"),
        rate=RateStats(day_up=5000, day_down=10000),
    )


@pytest.fixture
def sample_collected_data(sample_market_overview):
    return CollectedData(
        market=sample_market_overview,
        ranks={"price": [RankItem(name="Test Item", buff_sell_price=1000)]},
        timestamp="2024-01-01 12:00:00",
    )


@pytest.fixture
def sample_recommendations():
    return [
        Recommendation(
            name="蝴蝶刀（★）",
            strategy="买入",
            reason="近7日放量上涨",
            risk="短期波动风险",
            target_price="¥8000-9000",
            signal_strength="强",
            price_at_recommend=7500.0,
        ),
        Recommendation(
            name="AK-47 红线",
            strategy="观望",
            reason="价格高位横盘",
            risk="回调风险",
            target_price="¥400-450",
            signal_strength="中",
            price_at_recommend=420.0,
        ),
    ]
