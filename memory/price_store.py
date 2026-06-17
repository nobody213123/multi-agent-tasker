import json
from datetime import datetime
from pathlib import Path

PRICE_DIR = Path(__file__).resolve().parent.parent / "cache"
PRICE_FILE = PRICE_DIR / "price_snapshots.json"


class PriceStore:
    def save_snapshot(self, snapshots: list[dict]) -> None:
        PRICE_DIR.mkdir(parents=True, exist_ok=True)
        existing = self._load()
        existing.append({
            "timestamp": datetime.now().isoformat(),
            "snapshots": snapshots,
        })
        existing = existing[-365:]
        self._write(existing)

    def _load(self) -> list:
        if not PRICE_FILE.exists():
            return []
        try:
            return json.loads(PRICE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _write(self, data: list) -> None:
        PRICE_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
