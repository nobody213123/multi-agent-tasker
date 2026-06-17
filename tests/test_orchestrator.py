from orchestration.coordinator import Coordinator
from tools.providers.mock import MockIndexProvider, MockRankProvider


class TestCoordinator:
    def test_init(self):
        coord = Coordinator(
            index_provider=MockIndexProvider(),
            rank_provider=MockRankProvider(),
        )
        assert coord.cycle == 0
        assert coord.collector is not None
        assert coord.analyzer is not None

    def test_run_cycle_returns_result(self):
        coord = Coordinator(
            index_provider=MockIndexProvider(),
            rank_provider=MockRankProvider(),
        )
        result = coord.run_cycle()
        assert result.cycle == 1
        assert result.collected is not None
        assert result.analysis is not None
        assert result.timestamp != ""

    def test_cycle_counter(self):
        coord = Coordinator(
            index_provider=MockIndexProvider(),
            rank_provider=MockRankProvider(),
        )
        for i in range(5):
            result = coord.run_cycle()
            assert result.cycle == i + 1

    def test_result_has_alerts(self):
        coord = Coordinator(
            index_provider=MockIndexProvider(),
            rank_provider=MockRankProvider(),
        )
        result = coord.run_cycle()
        assert isinstance(result.alerts, list)

    def test_no_error_on_success(self):
        coord = Coordinator(
            index_provider=MockIndexProvider(),
            rank_provider=MockRankProvider(),
        )
        result = coord.run_cycle()
        assert result.error == ""
