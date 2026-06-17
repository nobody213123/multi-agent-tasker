from datetime import datetime

from models.analysis import CollectedData
from models.item import Item
from tools.providers.interfaces import IndexProvider, RankProvider, SearchProvider, DetailProvider


class CollectorAgent:
    def __init__(
        self,
        index_provider: IndexProvider,
        rank_provider: RankProvider,
        search_provider: SearchProvider | None = None,
        detail_provider: DetailProvider | None = None,
    ):
        self._index = index_provider
        self._rank = rank_provider
        self._search = search_provider
        self._detail = detail_provider

    def collect_all(self) -> CollectedData:
        market = self._index.fetch_indices()
        ranks = self._rank.fetch_ranks()

        return CollectedData(
            market=market,
            ranks=ranks,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def fetch_details(self, names: list[str]) -> dict[str, Item]:
        if not self._search or not self._detail:
            return {}

        result: dict[str, Item] = {}
        for name in names:
            try:
                results = self._search.search(name)
                if results:
                    detail = self._detail.get_detail(results[0].id)
                    result[name] = detail
            except Exception:
                pass
        return result
