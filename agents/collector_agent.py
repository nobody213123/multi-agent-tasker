from datetime import datetime

from models.analysis import CollectedData
from models.market import MarketOverview
from providers.interfaces import IndexProvider, RankProvider


class CollectorAgent:
    """采集 Agent：屏蔽多数据源差异，统一输出 CollectedData

    职责:
      1. 调用 IndexProvider 获取大盘指数
      2. 调用 RankProvider 获取多维度榜单
      3. 合并为 CollectedData 供下游 Agent 使用

    增量价值:
      - 下游 Agent 只需依赖 CollectorAgent，无需关心数据源细节
      - 更换数据源只需更换 Provider，CollectorAgent 本身不变
    """

    def __init__(self, index_provider: IndexProvider, rank_provider: RankProvider):
        self._index = index_provider
        self._rank = rank_provider

    def collect(self) -> CollectedData:
        """执行一轮数据采集"""
        market = self._index.fetch_indices()
        ranks = self._rank.fetch_ranks()

        return CollectedData(
            market=market,
            ranks=ranks,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
