import json
from datetime import datetime, timedelta
from pathlib import Path

from models.analysis import Recommendation

HISTORY_DIR = Path(__file__).resolve().parent.parent / "cache"
HISTORY_FILE = HISTORY_DIR / "recommend_history.json"


class RecommendationStore:
    def save(self, recs: list[Recommendation]) -> None:
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        existing = self._load()
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
        self._write(existing)

    def load_recent(self, days: int = 7) -> list[dict]:
        existing = self._load()
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        return [r for r in existing if r.get("created_at", "") >= cutoff]

    def _load(self) -> list:
        if not HISTORY_FILE.exists():
            return []
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _write(self, data: list) -> None:
        HISTORY_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
