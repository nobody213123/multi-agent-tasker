from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class MarketIndex:
    id: int
    name: str
    value: float
    change: float = 0.0
    change_pct: float = 0.0
    high: float = 0.0
    low: float = 0.0


@dataclass
class OnlineStats:
    current: int = 0
    today_peak: int = 0
    month_peak: int = 0
    month_player: int = 0
    rate: float = 0.0


@dataclass
class GreedyStatus:
    level: str = "unknown"
    label: str = "未知"


@dataclass
class RateStats:
    day_up: int = 0
    day_down: int = 0
    day_flat: int = 0
    week_up: int = 0
    week_down: int = 0
    week_flat: int = 0


@dataclass
class MarketOverview:
    indices: list[MarketIndex] = field(default_factory=list)
    online: OnlineStats = field(default_factory=OnlineStats)
    greedy: GreedyStatus = field(default_factory=GreedyStatus)
    rate: RateStats = field(default_factory=RateStats)
