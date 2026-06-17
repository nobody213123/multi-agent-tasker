import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from models.analysis import Recommendation, BacktestItem, BreakdownItem, BacktestReport

HISTORY_DIR = Path(__file__).resolve().parent.parent / "cache"
HISTORY_FILE = HISTORY_DIR / "recommend_history.json"
PRICE_SNAPSHOT_FILE = HISTORY_DIR / "price_snapshots.json"


class HistoryStorage:
    """历史记录：存储推荐记录 + 价格快照，支持回测"""

    def save_recommendations(self, recs: list[Recommendation]) -> None:
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        existing = self._load_json(HISTORY_FILE)
        now = datetime.now().isoformat()
        entries = []
        for r in recs:
            entries.append({
                "name": r.name,
                "strategy": r.strategy,
                "reason": r.reason,
                "risk": r.risk,
                "target_price": r.target_price,
                "signal_strength": r.signal_strength,
                "price_at_recommend": r.price_at_recommend,
                "created_at": now,
            })
        existing.extend(entries)
        self._write_json(HISTORY_FILE, existing)

    def load_recent_recommendations(self, days: int = 7) -> list[dict]:
        existing = self._load_json(HISTORY_FILE)
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        return [r for r in existing if r.get("created_at", "") >= cutoff]

    def save_price_snapshot(self, snapshots: list[dict]) -> None:
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        existing = self._load_json(PRICE_SNAPSHOT_FILE)
        existing.append({
            "timestamp": datetime.now().isoformat(),
            "snapshots": snapshots,
        })
        existing = existing[-365:]  # 最多保留一年
        self._write_json(PRICE_SNAPSHOT_FILE, existing)

    def run_backtest(self, days: int = 7) -> BacktestReport:
        recs = self.load_recent_recommendations(days)
        if not recs:
            return BacktestReport(period_days=days)

        prices = self._get_latest_prices()
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

    def _get_latest_prices(self) -> dict[str, float]:
        """获取当前饰品价格映射（name -> price）"""
        try:
            from tools.item_api import ItemAPI
            api = ItemAPI()
            recs = self.load_recent_recommendations(1)
            prices = {}
            for r in recs:
                results = api.search(r["name"])
                if results:
                    data = api.get_detail_and_chart(results[0]["id"])
                    detail = data.get("detail", {})
                    prices[r["name"]] = detail.get("buff_sell_price", 0)
            api.close()
            return prices
        except Exception:
            return {}

    def _load_json(self, path: Path) -> list:
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _write_json(self, path: Path, data: list) -> None:
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
