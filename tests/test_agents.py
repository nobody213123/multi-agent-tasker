import pytest

from orchestration.agents.collector import CollectorAgent
from orchestration.agents.analyzer import AnalyzerAgent
from memory.backtest_engine import BacktestEngine
from memory.recommendation_store import RecommendationStore
from models.analysis import BacktestReport, BreakdownItem, Recommendation, CycleResult


class MockStore:
    def load_recent(self, days=7):
        return []


class MockRichStore:
    def load_recent(self, days=7):
        return [
            {"name": "A", "strategy": "买入", "price_at_recommend": 100, "created_at": "2024-01-01"},
            {"name": "B", "strategy": "买入", "price_at_recommend": 200, "created_at": "2024-01-01"},
            {"name": "C", "strategy": "买入", "price_at_recommend": 300, "created_at": "2024-01-01"},
            {"name": "D", "strategy": "买入", "price_at_recommend": 400, "created_at": "2024-01-01"},
            {"name": "E", "strategy": "买入", "price_at_recommend": 500, "created_at": "2024-01-01"},
        ]


class TestCollectorAgent:
    def test_collect_returns_data(self, mock_index_provider, mock_rank_provider):
        agent = CollectorAgent(mock_index_provider, mock_rank_provider)
        data = agent.collect_all()
        assert data.market is not None
        assert len(data.market.indices) > 0
        assert data.timestamp != ""

    def test_collect_includes_ranks(self, mock_index_provider, mock_rank_provider):
        agent = CollectorAgent(mock_index_provider, mock_rank_provider)
        data = agent.collect_all()
        assert len(data.ranks) > 0


class TestAnalyzerAgent:
    def test_analyze_returns_signals(self, sample_collected_data):
        agent = AnalyzerAgent()
        result = agent.analyze(sample_collected_data)
        assert len(result.signals) > 0
        assert result.summary != ""

    def test_analyze_detects_direction(self, sample_collected_data):
        agent = AnalyzerAgent()
        result = agent.analyze(sample_collected_data)
        for signal in result.signals:
            assert signal.direction in ("up", "down", "flat")

    def test_analyze_timestamp(self, sample_collected_data):
        agent = AnalyzerAgent()
        result = agent.analyze(sample_collected_data)
        assert result.timestamp != ""


class TestBacktestEngine:
    def test_run_with_no_prices(self):
        engine = BacktestEngine(MockStore())
        report = engine.run(days=7)
        assert report is not None
        assert report.total == 0

    def test_run_with_mock_prices(self):
        prices = {"A": 150, "B": 190, "C": 350, "D": 380, "E": 550}
        engine = BacktestEngine(MockRichStore())
        report = engine.run(days=7, prices=prices)
        assert report.total == 5
        assert report.hit > 0
        assert "买入" in report.breakdown
