"""
=================================================================
  智能选品推荐引擎
  功能：分析多维度市场数据，用 LLM 生成选品策略和理由
=================================================================
"""
import json
import sys
from datetime import datetime

from config import DASHSCOPE_API_KEY, LLM_MODEL, LLM_TEMPERATURE


def _get_llm():
    """初始化大模型"""
    if not DASHSCOPE_API_KEY:
        return None
    try:
        from langchain_community.chat_models import ChatTongyi
        return ChatTongyi(
            model=LLM_MODEL,
            api_key=DASHSCOPE_API_KEY,
            temperature=0.3,
        )
    except ImportError:
        return None


# ── 数据采集 ──────────────────────────────────────────────────

def _fetch_rank_data() -> dict:
    """通过 Playwright 获取多个榜单数据"""
    from playwright.sync_api import sync_playwright

    all_data = {}
    tab_map = {
        "price":    "价格榜",
        "hot":      "热门榜",
        "supply":   "存世量榜",
        "turnover": "成交榜",
        "diff":     "平台差价榜",
    }

    def on_resp(resp):
        if "get_rank_list" in resp.url:
            try:
                j = resp.json()
                if j.get("code") == 200:
                    key = j.get("msg", "unknown")
                    all_data[key] = j["data"].get("data", [])
            except Exception:
                pass

    try:
        pw = sync_playwright().start()
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page()
        page.on("response", on_resp)

        page.goto("https://csqaq.com/rank", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        for key, tab_name in tab_map.items():
            try:
                page.click(f'text="{tab_name}"')
                page.wait_for_timeout(1500)
            except Exception:
                pass

        browser.close()
        pw.stop()

    except Exception as e:
        print(f"  ⚠️  榜单数据获取异常: {e}")

    return all_data


def _fetch_indices() -> dict:
    """获取大盘指数"""
    from tools.index_api import fetch_indices
    return fetch_indices()


# ── 数据分析 ──────────────────────────────────────────────────

def _analyze_data(rank_data: dict, indices: dict) -> str:
    """将多维度数据整理为分析文本，供 LLM 推理"""

    lines = []
    lines.append(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # 大盘概况
    online = indices.get("online", {})
    greedy = indices.get("greedy", {})
    rate = indices.get("rate", {})
    lines.append(f"\n【大盘概况】")
    lines.append(f"当前在线: {online.get('current', 0):,}人")
    lines.append(f"本月峰值: {online.get('month_peak', 0):,}人")
    lines.append(f"市场热度: {greedy.get('label', '未知')}")
    lines.append(f"今日涨跌商品: 涨{rate.get('day_up', 0)} / 跌{rate.get('day_down', 0)}")

    # 品类指数
    idx_list = indices.get("indices", [])
    if idx_list:
        lines.append(f"\n【品类指数】")
        for idx in idx_list[:10]:
            lines.append(f"  {idx['name']}: {idx['value']:.2f} ({idx['change_pct']:+.2f}%)")

    # 各榜单 Top 5
    rank_names = {
        "sell_price_rate_1": "价格涨幅榜",
        "buff_sell_num": "数量榜",
        "rank_num": "热门榜",
        "statistic": "存世量榜",
        "sell_buy_diff_buff": "平台差价榜",
        "turnover_number": "成交榜",
    }

    for api_key, label in rank_names.items():
        items = rank_data.get(api_key, [])[:5]
        if items:
            lines.append(f"\n【{label} Top5】")
            for i, item in enumerate(items, 1):
                name = item.get("name", "")
                price = item.get("buff_sell_price", 0)
                chg = item.get("buff_price_chg", 0)
                stat = item.get("statistic", 0)
                lines.append(f"  {i}. {name}  ¥{price}  涨跌{chg:+.2f}%  存世{stat}")

    return "\n".join(lines)


# ── LLM 推荐 ──────────────────────────────────────────────────

RECOMMEND_PROMPT = """你是一个资深 CS:GO/CS2 饰品投资分析师。

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
  {
    "name": "饰品名称",
    "strategy": "买入/观望/套利",
    "reason": "详细理由（包含具体数据）",
    "risk": "风险提示",
    "target_price": "目标价位区间",
    "signal_strength": "强/中/弱"
  }
]

当前市场数据："""


def _generate_recommendations(analysis_text: str) -> list:
    """调用 LLM 生成推荐"""
    llm = _get_llm()
    if llm is None:
        return [{"name": "LLM 不可用", "strategy": "—",
                 "reason": "请检查 DASHSCOPE_API_KEY 配置",
                 "risk": "—", "target_price": "—", "signal_strength": "—"}]

    try:
        from langchain.schema import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content="你是 CS:GO/CS2 饰品投资分析师，基于数据给出专业推荐。"),
            HumanMessage(content=RECOMMEND_PROMPT + "\n\n" + analysis_text),
        ]

        response = llm.invoke(messages)
        content = response.content.strip()

        # 清理 markdown 代码块
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        result = json.loads(content)
        if isinstance(result, list):
            return result

    except json.JSONDecodeError:
        # LLM 返回非 JSON，直接返回文本
        return [{"name": "AI 分析", "strategy": "—",
                 "reason": content[:500] if 'content' in dir() else "解析失败",
                 "risk": "—", "target_price": "—", "signal_strength": "—"}]
    except Exception as e:
        return [{"name": "LLM 调用异常", "strategy": "—",
                 "reason": str(e), "risk": "—", "target_price": "—",
                 "signal_strength": "—"}]

    return []


# ── 主入口 ──────────────────────────────────────────────────

def get_recommendations() -> dict:
    """
    执行完整推荐流程

    返回:
        {
            "analysis": str,           # 原始分析文本
            "recommendations": list,   # 推荐列表
            "timestamp": str,          # 生成时间
        }
    """
    print("  📡 采集市场数据...")
    rank_data = _fetch_rank_data()
    indices = _fetch_indices()

    print("  📊 分析数据中...")
    analysis = _analyze_data(rank_data, indices)

    print("  🤖 AI 生成推荐策略...")
    recommendations = _generate_recommendations(analysis)

    return {
        "analysis": analysis,
        "recommendations": recommendations,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
