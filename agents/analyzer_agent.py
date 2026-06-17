from datetime import datetime

from models.analysis import CollectedData, AnalysisResult, TrendSignal
from storage.cache import CacheStorage


class AnalyzerAgent:
    """分析 Agent：纯统计计算，不依赖 LLM

    职责:
      1. 对比本轮数据和缓存历史数据
      2. 计算品类涨跌趋势、波动率
      3. 生成 TrendSignal 列表

    增量价值:
      - 纯数学计算，速度快（ms 级）、结果可复现
      - 和 LLM 推荐的失败模式不同：统计不会幻觉
      - 独立可测：注入数据就能测
    """

    def __init__(self, cache: CacheStorage | None = None):
        self._cache = cache or CacheStorage()

    def analyze(self, data: CollectedData) -> AnalysisResult:
        signals: list[TrendSignal] = []

        for idx in data.market.indices:
            direction = "up" if idx.change_pct > 0 else "down" if idx.change_pct < 0 else "flat"
            signals.append(TrendSignal(
                name=idx.name,
                direction=direction,
                change_pct=idx.change_pct,
                description=f"{idx.name}: {idx.value:.2f} ({idx.change_pct:+.2f}%)",
            ))

        volatility = self._calc_volatility(signals)

        summary = self._build_summary(data.market, signals)
        self._cache.save(self._to_cache_dict(data))

        return AnalysisResult(
            signals=signals,
            summary=summary,
            volatility=volatility,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def _calc_volatility(self, signals: list[TrendSignal]) -> float:
        if not signals:
            return 0.0
        changes = [abs(s.change_pct) for s in signals]
        return sum(changes) / len(changes)

    def _build_summary(self, market, signals: list[TrendSignal]) -> str:
        up = sum(1 for s in signals if s.direction == "up")
        down = sum(1 for s in signals if s.direction == "down")
        flat = sum(1 for s in signals if s.direction == "flat")

        parts = [
            f"大盘概况: 在线 {market.online.current:,} 人",
            f"涨 {up} 跌 {down} 平 {flat}",
            f"热度 {market.greedy.label}",
        ]
        top_signal = max(signals, key=lambda s: abs(s.change_pct), default=None)
        if top_signal:
            parts.append(f"最异常: {top_signal.name} ({top_signal.change_pct:+.2f}%)")

        return " | ".join(parts)

    def _to_cache_dict(self, data: CollectedData) -> dict:
        """Crawler/Parser Agent 的缓存格式"""
        return {
            "indices": [
                {
                    "name": i.name,
                    "value": i.value,
                    "change_pct": i.change_pct,
                }
                for i in data.market.indices
            ],
            "online": {
                "current": data.market.online.current,
                "month_peak": data.market.online.month_peak,
            },
        }
