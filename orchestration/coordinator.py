from datetime import datetime
from threading import Lock

from config import DASHSCOPE_API_KEY
from models.analysis import CycleResult
from observability.logger import get_logger

from orchestration.agents.collector import CollectorAgent
from orchestration.agents.analyzer import AnalyzerAgent

from tools.llm import QwenLLMProvider
from tools.providers.interfaces import IndexProvider, RankProvider
from tools.providers.csqaq import CsqaqIndexProvider, CsqaqRankProvider
from memory.recommendation_store import RecommendationStore
from memory.backtest_engine import BacktestEngine

log = get_logger(__name__)

THRESHOLD_CHANGE = 5.0


class Coordinator:
    def __init__(
        self,
        index_provider: IndexProvider | None = None,
        rank_provider: RankProvider | None = None,
    ):
        has_llm = bool(DASHSCOPE_API_KEY)

        self._index_provider = index_provider or CsqaqIndexProvider()
        self._rank_provider = rank_provider or CsqaqRankProvider()

        self._store = RecommendationStore()
        self._backtest = BacktestEngine(self._store)

        self.collector = CollectorAgent(
            self._index_provider,
            self._rank_provider,
        )
        self.analyzer = AnalyzerAgent()

        self._cycle = 0
        self._lock = Lock()

    @property
    def cycle(self) -> int:
        with self._lock:
            return self._cycle

    def run_cycle(self) -> CycleResult:
        with self._lock:
            self._cycle += 1
            cycle = self._cycle

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result = CycleResult(cycle=cycle, timestamp=now)

        try:
            collected = self.collector.collect_all()
            result.collected = collected
            log.info("采集完成: %d 个品类", len(collected.market.indices))
        except Exception as e:
            log.error("采集失败: %s", e)
            result.error = f"采集失败: {e}"
            return result

        try:
            analysis = self.analyzer.analyze(collected)
            result.analysis = analysis
            log.info("趋势分析完成: %s", analysis.summary)
        except Exception as e:
            log.error("趋势分析失败: %s", e)
            result.error = f"趋势分析失败: {e}"
            return result

        try:
            recs = self.analyzer.generate_recommendations(
                collected,
                analysis,
                fetch_extra=self.collector.fetch_details,
            )
            result.recommendations = recs
            self._store.save(recs)
            log.info("推荐完成: %d 条", len(recs))
        except Exception as e:
            log.error("推荐失败: %s", e)
            result.error = f"推荐失败: {e}"

        try:
            alerts = self._check_alerts(collected, analysis)
            result.alerts = alerts
            if alerts:
                log.info("告警: %d 条", len(alerts))
        except Exception as e:
            log.warning("告警检测异常: %s", e)

        return result

    def run_backtest(self, days: int = 7, prices: dict[str, float] | None = None) -> object:
        return self._backtest.run(days=days, prices=prices)

    def _check_alerts(self, data, analysis) -> list[str]:
        alerts = []
        for signal in analysis.signals:
            if abs(signal.change_pct) >= THRESHOLD_CHANGE:
                direction = "暴涨" if signal.change_pct > 0 else "暴跌"
                alerts.append(
                    f"🔔 {signal.name} {direction}: {signal.change_pct:+.2f}%"
                )
        market = data.market
        if market.greedy.level == "low" and market.greedy.label == "恐慌":
            alerts.append("⚠️ 市场恐慌情绪，建议谨慎操作")
        return alerts
