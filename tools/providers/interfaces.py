from __future__ import annotations
from abc import ABC, abstractmethod

from models.market import MarketOverview
from models.item import Item, ChartData, SearchResult
from models.analysis import CollectedData, RankItem


class IndexProvider(ABC):
    @abstractmethod
    def fetch_indices(self) -> MarketOverview: ...


class RankProvider(ABC):
    @abstractmethod
    def fetch_ranks(self) -> dict[str, list[RankItem]]: ...


class SearchProvider(ABC):
    @abstractmethod
    def search(self, keyword: str) -> list[SearchResult]: ...


class DetailProvider(ABC):
    @abstractmethod
    def get_detail(self, item_id: str) -> Item: ...

    @abstractmethod
    def get_chart(self, item_id: str) -> ChartData: ...
