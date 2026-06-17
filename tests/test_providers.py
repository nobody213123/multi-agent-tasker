from tools.providers.mock import MockIndexProvider, MockRankProvider, MockSearchProvider
from models.analysis import RankItem


class TestMockIndexProvider:
    def test_fetch_indices_returns_overview(self, mock_index_provider):
        overview = mock_index_provider.fetch_indices()
        assert len(overview.indices) == 3
        assert overview.indices[0].name == "饰品指数"
        assert overview.online.current > 0
        assert overview.greedy.label != ""

    def test_indices_have_values(self, mock_index_provider):
        overview = mock_index_provider.fetch_indices()
        for idx in overview.indices:
            assert idx.value != 0


class TestMockRankProvider:
    def test_fetch_ranks_returns_rank_items(self, mock_rank_provider):
        ranks = mock_rank_provider.fetch_ranks()
        assert isinstance(ranks, dict)
        for items in ranks.values():
            for item in items:
                assert isinstance(item, RankItem)
        assert "sell_price_rate_1" in ranks

    def test_rank_items_have_required_fields(self, mock_rank_provider):
        ranks = mock_rank_provider.fetch_ranks()
        for items in ranks.values():
            for item in items:
                assert isinstance(item.name, str) and len(item.name) > 0
                assert item.buff_sell_price > 0


class TestMockSearchProvider:
    def test_search_returns_results(self, mock_search_provider):
        results = mock_search_provider.search("蝴蝶刀")
        assert len(results) == 2
        assert results[0].id == "1"
        assert "蝴蝶刀" in results[0].value

    def test_get_detail_returns_item(self, mock_search_provider):
        item = mock_search_provider.get_detail("1")
        assert item.id == "1"
        assert item.buff_sell_price > 0

    def test_get_chart_returns_data(self, mock_search_provider):
        chart = mock_search_provider.get_chart("1")
        assert not chart.is_empty
        assert len(chart.prices) == 10
        assert len(chart.timestamps) == 10
