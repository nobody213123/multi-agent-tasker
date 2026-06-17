from datetime import datetime
from threading import Lock

from config import DASHSCOPE_API_KEY
from logger import get_logger
from models.analysis import CycleResult

from agents.collector_agent import CollectorAgent
from agents.analyzer_agent import AnalyzerAgent
from agents.recommend_agent import RecommendAgent
from agents.backtest_agent import BacktestAgent
from agents.alert_agent import AlertAgent

from providers.interfaces import IndexProvider, RankProvider
from providers.csqaq_provider import CsqaqIndexProvider, CsqaqRankProvider
from storage.history import HistoryStorage

log = get_logger(__name__)


class Orchestrator:
    """总控调度器 —— 整个系统的"大脑"

    工作流程（每轮）:
      1. CollectorAgent 采集数据（大盘 + 榜单）
      2. AnalyzerAgent 统计分析（趋势、波动率）
      3. RecommendAgent 每 N 轮调用 LLM 生成推荐
      4. BacktestAgent 每日跑一次回测
      5. AlertAgent 检测异常并生成告警

    设计原则:
      - 各 Agent 通过数据类传递消息，不直接耦合
      - 每个 Agent 可独立 Mock
      - RecommendAgent/BacktestAgent 按周期执行，不每轮都跑
    """

    RECOMMEND_INTERVAL = 5
    BACKTEST_INTERVAL = 20

    def __init__(
        self,
        index_provider: IndexProvider | None = None,
        rank_provider: RankProvider | None = None,
    ):
        has_llm = bool(DASHSCOPE_API_KEY)

        self._index_provider = index_provider or CsqaqIndexProvider()
        self._rank_provider = rank_provider or CsqaqRankProvider()

        self._history = HistoryStorage()

        self.collector = CollectorAgent(self._index_provider, self._rank_provider)
        self.analyzer = AnalyzerAgent()
        self.recommender = RecommendAgent() if has_llm else None
        self.backtester = BacktestAgent(self._history)
        self.alerter = AlertAgent()

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
            collected = self.collector.collect()
            result.collected = collected
            log.info("采集完成: %d 个品类", len(collected.market.indices))
        except Exception as e:
            log.error("采集失败: %s", e)
            result.error = f"采集失败: {e}"
            return result

        try:
            analysis = self.analyzer.analyze(collected)
            result.analysis = analysis
            log.info("分析完成: %s", analysis.summary)
        except Exception as e:
            log.error("分析失败: %s", e)
            result.error = f"分析失败: {e}"
            return result

        if self.recommender and cycle % self.RECOMMEND_INTERVAL == 0:
            try:
                recs = self.recommender.recommend(collected, analysis)
                result.recommendations = recs
                self._history.save_recommendations(recs)
                log.info("推荐完成: %d 条推荐", len(recs))
            except Exception as e:
                log.error("推荐失败: %s", e)
                result.error = f"推荐失败: {e}"

        if cycle % self.BACKTEST_INTERVAL == 0:
            try:
                report = self.backtester.run(days=7)
                result.backtest = report
                log.info("回测完成: %s", report.summary)
            except Exception as e:
                log.error("回测失败: %s", e)
                result.error = f"回测失败: {e}"

        try:
            alerts = self.alerter.check(collected, analysis)
            result.alerts = alerts
            if alerts:
                log.info("告警: %d 条", len(alerts))
        except Exception as e:
            log.warning("告警检测异常: %s", e)

        return result
