import json
import sys
from datetime import datetime

from config import DASHSCOPE_API_KEY, LLM_MODEL, LLM_TEMPERATURE
from models.analysis import CollectedData, AnalysisResult, Recommendation


RECOMMEND_SYSTEM_PROMPT = """你是一个资深 CS:GO/CS2 饰品投资分析师。

请根据以下实时市场数据，推荐 3-5 个值得重点关注的饰品，并给出详细策略和理由。

推荐维度（选择有明确信号的）：
1. 【抄底机会】大幅下跌但基本面好的饰品（跌幅 > 5%，存世量适中）
2. 【追涨热门】热度飙升、成交量放大的饰品
3. 【平台套利】BUFF 和悠悠有品/Steam 价差大的饰品
4. 【低存世量】存世量少、有稀缺性溢价潜力的饰品
5. 【大盘联动】跟随大盘趋势的顺势机会

每个推荐必须包含：
- 饰品名称
- 推荐策略（买入/观望/套利）
- 推荐理由（结合具体数据）
- 风险提示
- 目标价位区间

要求：
- 用中文回答
- 紧扣数据，不要凭空想象
- 风险提示要诚实
- 如果数据不足以支撑推荐，明确说明

请用以下 JSON 格式返回：
[
  {{
    "name": "饰品名称",
    "strategy": "买入/观望/套利",
    "reason": "详细理由（包含具体数据）",
    "risk": "风险提示",
    "target_price": "目标价位区间",
    "signal_strength": "强/中/弱"
  }}
]

当前市场数据："""


class RecommendAgent:
    """推荐 Agent：调用 LLM 生成投资策略

    职责:
      1. 接收 CollectedData + AnalysisResult
      2. 拼接分析文本
      3. 调用 LLM 生成推荐
      4. 解析 JSON 返回结构化 Recommendation

    增量价值:
      - LLM 的语义理解能力 + 定量数据结合
      - 可独立 Mock 测试（注入 Mock LLM 响应）
      - 可更换不同 LLM 模型而无需改动其他 Agent
    """

    def __init__(self, llm=None):
        self._llm = llm or self._get_llm()

    def _get_llm(self):
        if not DASHSCOPE_API_KEY:
            return None
        try:
            from langchain_community.chat_models import ChatTongyi
            return ChatTongyi(
                model=LLM_MODEL,
                api_key=DASHSCOPE_API_KEY,
                temperature=LLM_TEMPERATURE,
            )
        except ImportError:
            return None

    def recommend(self, data: CollectedData, analysis: AnalysisResult) -> list[Recommendation]:
        if self._llm is None:
            return [Recommendation(
                name="LLM 不可用",
                strategy="—",
                reason="请配置 DASHSCOPE_API_KEY",
                risk="—",
                target_price="—",
                signal_strength="—",
            )]

        analysis_text = self._build_analysis_text(data, analysis)

        try:
            from langchain.schema import HumanMessage, SystemMessage

            messages = [
                SystemMessage(content="你是 CS:GO/CS2 饰品投资分析师，基于数据给出专业推荐。"),
                HumanMessage(content=RECOMMEND_SYSTEM_PROMPT + "\n\n" + analysis_text),
            ]

            response = self._llm.invoke(messages)
            content = response.content.strip()

            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            raw = json.loads(content)
            now = datetime.now().isoformat()
            recs = []
            for r in raw if isinstance(raw, list) else []:
                recs.append(Recommendation(
                    name=r.get("name", "未知"),
                    strategy=r.get("strategy", "观望"),
                    reason=r.get("reason", ""),
                    risk=r.get("risk", ""),
                    target_price=r.get("target_price", ""),
                    signal_strength=r.get("signal_strength", "弱"),
                    created_at=now,
                    price_at_recommend=self._get_current_price(r.get("name", "")),
                ))
            return recs

        except Exception as e:
            return [Recommendation(
                name="推荐异常",
                strategy="—",
                reason=str(e),
                risk="—",
                target_price="—",
                signal_strength="—",
            )]

    def _build_analysis_text(self, data: CollectedData, analysis: AnalysisResult) -> str:
        lines = []
        market = data.market

        lines.append(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"\n【大盘概况】")
        lines.append(f"当前在线: {market.online.current:,} 人")
        lines.append(f"本月峰值: {market.online.month_peak:,} 人")
        lines.append(f"市场热度: {market.greedy.label}")
        lines.append(f"今日涨跌: 涨{market.rate.day_up} / 跌{market.rate.day_down}")

        if market.indices:
            lines.append(f"\n【品类指数】")
            for idx in market.indices[:10]:
                lines.append(f"  {idx.name}: {idx.value:.2f} ({idx.change_pct:+.2f}%)")

        if data.ranks:
            for api_key, items in data.ranks.items():
                if items:
                    lines.append(f"\n【{api_key} Top3】")
                    for i, item in enumerate(items[:3], 1):
                        lines.append(f"  {i}. {item.name}  ¥{item.buff_sell_price:.0f}  涨跌{item.buff_price_chg:+.2f}%")

        lines.append(f"\n【趋势信号】")
        lines.append(analysis.summary)

        return "\n".join(lines)

    def _get_current_price(self, name: str) -> float:
        try:
            from providers.csqaq_provider import CsqaqSearchProvider
            provider = CsqaqSearchProvider()
            results = provider.search(name)
            if results:
                detail = provider.get_detail(results[0].id)
                provider.close()
                return detail.buff_sell_price
            provider.close()
        except Exception:
            pass
        return 0.0
