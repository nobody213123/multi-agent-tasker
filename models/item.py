from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Item:
    id: str
    name: str
    market_hash_name: str = ""
    type_name: str = ""
    buff_sell_price: float = 0.0
    buff_buy_price: float = 0.0
    buff_sell_num: int = 0
    buff_buy_num: int = 0
    yyyp_sell_price: float = 0.0
    yyyp_buy_price: float = 0.0
    yyyp_sell_num: int = 0
    yyyp_lease_price: float = 0.0
    yyyp_long_lease_price: float = 0.0
    steam_sell_price: float = 0.0
    steam_buy_price: float = 0.0
    sell_price_rate_1: float = 0.0
    sell_price_rate_7: float = 0.0
    sell_price_rate_15: float = 0.0
    sell_price_rate_30: float = 0.0
    statistic: int = 0


@dataclass
class ChartData:
    timestamps: list[int] = field(default_factory=list)
    prices: list[float] = field(default_factory=list)
    volumes: list[int] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return len(self.prices) < 2


@dataclass
class SearchResult:
    id: str
    value: str
