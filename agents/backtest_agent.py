from models.analysis import BacktestReport
from storage.history import HistoryStorage


class BacktestAgent:
    """回测 Agent：评估历史推荐准确率

    职责:
      1. 读取指定天数前的推荐记录
      2. 获取当前价格并对比
      3. 按策略（买入/观望/套利）分类统计准确率
      4. 生成 BacktestReport

    增量价值:
      - 是项目唯一能证明"AI 推荐有用"的组件
      - 没有回测，推荐就是"你说啥是啥"
      - 回测数据可驱动 Prompt 优化（哪个策略不准就改进哪个）
    """

    def __init__(self, history: HistoryStorage | None = None):
        self._history = history or HistoryStorage()

    def run(self, days: int = 7) -> BacktestReport:
        return self._history.run_backtest(days=days)
