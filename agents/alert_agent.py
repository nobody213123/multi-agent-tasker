from models.analysis import CollectedData, AnalysisResult


class AlertAgent:
    """告警 Agent：检测异常信号，生成通知消息

    职责:
      1. 检测品类指数异常波动（涨跌幅超阈值）
      2. 检测市场热度突变
      3. 返回可读的告警消息列表

    增量价值:
      - 无需 LLM，轻量快速
      - 从被动展示变为主动通知
      - 和 RecommendAgent 互补：一个推策略，一个推风险
    """

    THRESHOLD_CHANGE = 5.0  # 涨跌幅超 5% 触发告警
    THRESHOLD_TURNOVER = 0.5  # 换手率（待实现）

    def check(self, data: CollectedData, analysis: AnalysisResult) -> list[str]:
        alerts = []

        for signal in analysis.signals:
            if abs(signal.change_pct) >= self.THRESHOLD_CHANGE:
                direction = "暴涨" if signal.change_pct > 0 else "暴跌"
                alerts.append(
                    f"🔔 {signal.name} {direction}: {signal.change_pct:+.2f}%"
                )

        market = data.market
        if market.greedy.level == "low" and market.greedy.label == "恐慌":
            alerts.append("⚠️ 市场恐慌情绪，建议谨慎操作")

        return alerts
