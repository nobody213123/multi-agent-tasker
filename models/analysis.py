from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime

from models.market import MarketOverview


@dataclass
class CollectedData:
    market: MarketOverview
    ranks: dict[str, list[RankItem]] = field(default_factory=dict)
    timestamp: str = ""


@dataclass
class TrendSignal:
    name: str
    direction: str  # up / down / flat
    change_pct: float
    description: str = ""


@dataclass
class AnalysisResult:
    signals: list[TrendSignal] = field(default_factory=list)
    summary: str = ""
    volatility: float = 0.0
    timestamp: str = ""


@dataclass
class Recommendation:
    name: str
    strategy: str
    reason: str
    risk: str
    target_price: str
    signal_strength: str
    created_at: str = ""
    price_at_recommend: float = 0.0


@dataclass
class BacktestItem:
    recommendation: Recommendation
    price_now: float
    change_pct: float
    is_hit: bool


@dataclass
class RankItem:
    name: str = ""
    buff_sell_price: float = 0.0
    buff_buy_price: float = 0.0
    buff_price_chg: float = 0.0
    buff_sell_num: int = 0
    buff_buy_num: int = 0
    statistic: int = 0
    id: str = ""
    exterior_localized_name: str = ""
    rarity_localized_name: str = ""

    @staticmethod
    def from_dict(d: dict) -> RankItem:
        return RankItem(
            name=str(d.get("name", "")),
            buff_sell_price=float(d.get("buff_sell_price", 0) or 0),
            buff_buy_price=float(d.get("buff_buy_price", 0) or 0),
            buff_price_chg=float(d.get("buff_price_chg", 0) or 0),
            buff_sell_num=int(d.get("buff_sell_num", 0) or 0),
            buff_buy_num=int(d.get("buff_buy_num", 0) or 0),
            statistic=int(d.get("statistic", 0) or 0),
            id=str(d.get("id", "") or ""),
            exterior_localized_name=str(d.get("exterior_localized_name", "") or ""),
            rarity_localized_name=str(d.get("rarity_localized_name", "") or ""),
        )


@dataclass
class BreakdownItem:
    total: int = 0
    hit: int = 0
    accuracy: float = 0.0


@dataclass
class BacktestReport:
    total: int = 0
    hit: int = 0
    accuracy: float = 0.0
    breakdown: dict[str, BreakdownItem] = field(default_factory=dict)
    items: list[BacktestItem] = field(default_factory=list)
    period_days: int = 7
    timestamp: str = ""

    @property
    def summary(self) -> str:
        return (
            f"回测周期 {self.period_days} 天 | "
            f"共 {self.total} 条推荐 | "
            f"命中 {self.hit} 条 | "
            f"准确率 {self.accuracy:.1%}"
        )


@dataclass
class CycleResult:
    collected: CollectedData | None = None
    analysis: AnalysisResult | None = None
    recommendations: list[Recommendation] = field(default_factory=list)
    backtest: BacktestReport | None = None
    alerts: list[str] = field(default_factory=list)
    cycle: int = 0
    timestamp: str = ""
    error: str = ""
