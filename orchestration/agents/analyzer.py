import json
import re
from datetime import datetime

from models.analysis import CollectedData, AnalysisResult, TrendSignal, Recommendation
from memory.cache_store import CacheStore
from tools.llm import LLMProvider, MockLLMProvider, QwenLLMProvider
from observability.logger import get_logger

log = get_logger(__name__)
from config import DASHSCOPE_API_KEY, LLM_MODEL, LLM_TEMPERATURE


FIRST_PASS_PROMPT = """你是一个资深 CS:GO/CS2 饰品投资分析师。

重要市场规则：Buff 平台采用 T+7 结算机制。饰品卖出后，资金需要 7 天才能到账（可提现或用于购买）。这意味着：
- 任何短线交易（7 天内快进快出）的资金会被锁定，无法快速周转
- 推荐买入策略时，需确保预期持有期超过 7 天，且价格趋势在 7 天以上维度看涨
- 套利策略必须考虑 7 天锁仓期的价格波动风险
- "观望"是 T+7 市场下的中性策略，适合高波动饰品

当前市场数据如下。请分析哪些饰品值得深入关注。

在分析的最后，列出你需要额外数据的饰品名称（如果需要的话），格式如下：
DATA_NEEDS: 饰品A, 饰品B, 饰品C

如果你不需要额外数据，则输出：DATA_NEEDS: 无

当前市场数据："""

SECOND_PASS_PROMPT = """基于首次分析的结果和以下补充数据，给出最终推荐。

重要市场规则提醒：Buff 平台采用 T+7 结算机制，卖出后资金需 7 天到账。
- 策略为"买入"时，必须确保预期持有期 > 7 天，且 7 天以上趋势看涨
- "套利"策略必须评估 7 天锁仓期内价格反向波动的风险
- 对短期内（< 7 天）涨幅过大的饰品，T+7 结算意味着高位接盘后无法快速止损，风险需标注为"高"

请用 JSON 格式返回推荐列表：
[
  {{
    "name": "饰品名称",
    "strategy": "买入/观望/套利",
    "reason": "详细理由（包含具体数据，必须提及 T+7 对该推荐的影响分析）",
    "risk": "风险提示（必须包含 T+7 锁仓风险说明）",
    "target_price": "目标价位区间",
    "signal_strength": "强/中/弱"
  }}
]

首次分析结论：
{first_analysis}

补充数据：
{extra_data}"""


class AnalyzerAgent:
    def __init__(self, llm: LLMProvider | None = None, cache: CacheStore | None = None):
        self._llm = llm or self._build_llm()
        self._cache = cache or CacheStore()

    def _build_llm(self) -> LLMProvider:
        if not DASHSCOPE_API_KEY:
            return MockLLMProvider(response='[]')
        try:
            return QwenLLMProvider(
                model=LLM_MODEL,
                api_key=DASHSCOPE_API_KEY,
                temperature=LLM_TEMPERATURE,
            )
        except ImportError:
            return MockLLMProvider(response='[]')

    def analyze(
        self,
        data: CollectedData,
        fetch_extra=None,
    ) -> AnalysisResult:
        signals = self._compute_signals(data)
        volatility = self._calc_volatility(signals)
        summary = self._build_summary(data.market, signals)

        self._cache.save(self._to_cache_dict(data))

        analysis = AnalysisResult(
            signals=signals,
            summary=summary,
            volatility=volatility,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        return analysis

    def generate_recommendations(
        self,
        data: CollectedData,
        analysis: AnalysisResult,
        fetch_extra=None,
    ) -> list[Recommendation]:
        context = self._build_context(data, analysis)

        first_response = self._llm.generate(FIRST_PASS_PROMPT + "\n\n" + context)

        needs = self._parse_data_needs(first_response)

        if needs and fetch_extra:
            extra_items = fetch_extra(needs)
            extra_text = self._format_extra(extra_items)
        else:
            extra_text = "无额外数据"

        second_prompt = SECOND_PASS_PROMPT.format(
            first_analysis=first_response,
            extra_data=extra_text,
        )

        second_response = self._llm.generate(second_prompt)

        log.info("LLM 推荐原始响应 (前200字): %s", second_response[:200])
        return self._parse_recommendations(second_response)

    def _compute_signals(self, data: CollectedData) -> list[TrendSignal]:
        signals: list[TrendSignal] = []
        for idx in data.market.indices:
            direction = "up" if idx.change_pct > 0 else "down" if idx.change_pct < 0 else "flat"
            signals.append(TrendSignal(
                name=idx.name,
                direction=direction,
                change_pct=idx.change_pct,
                description=f"{idx.name}: {idx.value:.2f} ({idx.change_pct:+.2f}%)",
            ))
        return signals

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

    def _build_context(self, data: CollectedData, analysis: AnalysisResult) -> str:
        lines = []
        market = data.market

        lines.append(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"\n【大盘概况】")
        lines.append(f"当前在线: {market.online.current:,} 人")
        lines.append(f"本月峰值: {market.online.month_peak:,} 人")
        lines.append(f"市场热度: {market.greedy.label}")
        lines.append(f"今日涨跌: 涨{market.rate.day_up} / 跌{market.rate.day_down}")
        lines.append(f"结算规则: Buff T+7 到账，卖出后资金锁定 7 天")

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

    def _parse_data_needs(self, response: str) -> list[str]:
        match = re.search(r"DATA_NEEDS:\s*(.+)", response)
        if not match:
            return []
        raw = match.group(1).strip()
        if raw == "无" or raw == "无":
            return []
        return [name.strip() for name in raw.split(",") if name.strip()]

    def _format_extra(self, items: dict[str, object]) -> str:
        if not items:
            return "无"
        lines = []
        for name, item in items.items():
            price = getattr(item, "buff_sell_price", "N/A")
            lines.append(f"- {name}: 当前售价 ¥{price}")
        return "\n".join(lines)

    def _parse_recommendations(self, response: str) -> list[Recommendation]:
        raw = self._extract_json(response)
        if raw is None or not isinstance(raw, list):
            return []

        now = datetime.now().isoformat()
        recs = []
        for r in raw:
            recs.append(Recommendation(
                name=r.get("name", "未知"),
                strategy=r.get("strategy", "观望"),
                reason=r.get("reason", ""),
                risk=r.get("risk", ""),
                target_price=r.get("target_price", ""),
                signal_strength=r.get("signal_strength", "弱"),
                created_at=now,
                price_at_recommend=0.0,
            ))
        return recs

    def _extract_json(self, text: str):
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        brace_match = re.search(r"\[.*?\]", text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group())
            except (json.JSONDecodeError, ValueError):
                pass

        code_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        if code_match:
            try:
                return json.loads(code_match.group(1).strip())
            except (json.JSONDecodeError, ValueError):
                pass

        return None

    def _to_cache_dict(self, data: CollectedData) -> dict:
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
