from datetime import datetime

from models.analysis import Recommendation, BacktestItem, BreakdownItem, BacktestReport
from memory.recommendation_store import RecommendationStore


class BacktestEngine:
    def __init__(self, store: RecommendationStore | None = None):
        self._store = store or RecommendationStore()

    def run(self, days: int = 7, prices: dict[str, float] | None = None) -> BacktestReport:
        recs = self._store.load_recent(days)
        if not recs or not prices:
            return BacktestReport(period_days=days)

        items: list[BacktestItem] = []
        breakdown: dict[str, BreakdownItem] = {}

        for r in recs:
            name = r["name"]
            strategy = r["strategy"]
            past_price = r.get("price_at_recommend", 0)
            current_price = prices.get(name, 0)

            if past_price <= 0 or current_price <= 0:
                continue

            change_pct = (current_price - past_price) / past_price
            if strategy == "买入":
                is_hit = change_pct > 0.02
            elif strategy == "套利":
                is_hit = abs(change_pct) < 0.03
            else:
                is_hit = True

            items.append(BacktestItem(
                recommendation=Recommendation(
                    name=name,
                    strategy=strategy,
                    reason=r.get("reason", ""),
                    risk=r.get("risk", ""),
                    target_price=r.get("target_price", ""),
                    signal_strength=r.get("signal_strength", ""),
                ),
                price_now=current_price,
                change_pct=change_pct,
                is_hit=is_hit,
            ))

            if strategy not in breakdown:
                breakdown[strategy] = BreakdownItem()
            breakdown[strategy].total += 1
            if is_hit:
                breakdown[strategy].hit += 1

        total = len(items)
        hit = sum(1 for i in items if i.is_hit)
        accuracy = hit / total if total > 0 else 0.0

        for b in breakdown.values():
            b.accuracy = b.hit / b.total if b.total > 0 else 0.0

        return BacktestReport(
            total=total,
            hit=hit,
            accuracy=accuracy,
            breakdown=breakdown,
            items=items,
            period_days=days,
            timestamp=datetime.now().isoformat(),
        )
