"""
=================================================================
  终端价格走势图渲染器
  功能：将价格数据渲染为终端文本图表（Sparkline + 统计）
=================================================================
"""
from datetime import datetime


def render_price_chart(timestamps: list, prices: list, width: int = 40) -> str:
    """
    渲染价格走势迷你图

    参数:
        timestamps: Unix 毫秒时间戳列表
        prices:     对应价格列表（单位：分或元均可）
        width:      图表宽度（字符数）

    返回:
        多行文本图表
    """
    if not prices or len(prices) < 2:
        return "  (数据不足，无法绘制)"

    n = len(prices)
    if n < width:
        width = n

    # 降采样：取 width 个等距点
    indices = [int(i * (n - 1) / (width - 1)) for i in range(width)]
    sampled = [prices[i] for i in indices]
    sampled_ts = [timestamps[i] for i in indices]

    min_p = min(sampled)
    max_p = max(sampled)
    cur_p = sampled[-1]
    first_p = sampled[0]

    # 价格范围
    p_range = max_p - min_p
    if p_range == 0:
        p_range = 1

    # 构建 Sparkline
    bars = []
    for p in sampled:
        ratio = (p - min_p) / p_range
        level = min(7, int(ratio * 8))
        bars.append("▁▂▃▄▅▆▇█"[level])

    sparkline = "".join(bars)

    # 时间范围
    start_time = datetime.fromtimestamp(sampled_ts[0] / 1000).strftime("%m-%d")
    end_time = datetime.fromtimestamp(sampled_ts[-1] / 1000).strftime("%m-%d")

    change = cur_p - first_p
    change_pct = (change / first_p) * 100 if first_p != 0 else 0
    arrow = "↑" if change >= 0 else "↓"

    lines = [
        f"  📈 价格走势 ({start_time} ~ {end_time})",
        f"  ─────────────────────────────────",
        f"  {sparkline}",
        f"  ─────────────────────────────────",
        f"  ¥{min_p:,.2f} {'─' * (width-16)} ¥{max_p:,.2f}",
        f"  (最低)           →           (最高)",
        f"",
        f"  开盘: ¥{first_p:,.2f}  当前: ¥{cur_p:,.2f}",
        f"  涨跌: ¥{change:+,.2f} ({change_pct:+.2f}%) {arrow}",
    ]

    return "\n".join(lines)


def render_item_full(item_id: str, detail: dict, chart_data: dict) -> str:
    """
    渲染完整的饰品信息展示

    参数:
        item_id:  饰品 ID
        detail:   饰品详情字典
        chart_data: 图表数据字典

    返回:
        格式化终端文本
    """
    lines = []
    lines.append("")
    lines.append("=" * 56)
    lines.append(f"  🗡️  {detail['name']}")
    lines.append(f"  {detail.get('market_hash_name', '')}")
    lines.append(f"  类型: {detail.get('type_localized_name', '未知')}")
    lines.append("=" * 56)

    # 价格变化
    lines.append("")
    lines.append("  📊 近期涨跌幅")
    lines.append("  ───────────────────────────────────────")
    rate_1 = detail.get("sell_price_rate_1")
    rate_7 = detail.get("sell_price_rate_7")
    rate_15 = detail.get("sell_price_rate_15")
    rate_30 = detail.get("sell_price_rate_30")
    if rate_1 is not None:
        lines.append(f"   24h: {rate_1:+.2f}%     7天: {rate_7:+.2f}%")
    if rate_15 is not None:
        lines.append(f"   15天: {rate_15:+.2f}%    30天: {rate_30:+.2f}%")

    # 各平台价格
    lines.append("")
    lines.append("  💰 各平台价格")
    lines.append("  ┌────────────┬────────────┬────────────┐")
    lines.append("  │ 平台       │ 售价       │ 求购价     │")
    lines.append("  ├────────────┼────────────┼────────────┤")

    buff_sell = detail.get("buff_sell_price")
    buff_buy = detail.get("buff_buy_price")
    yyyp_sell = detail.get("yyyp_sell_price")
    yyyp_buy = detail.get("yyyp_buy_price")
    steam_sell = detail.get("steam_sell_price", 0)
    steam_buy = detail.get("steam_buy_price", 0)

    if buff_sell:
        lines.append(f"  │ BUFF       │ ¥{buff_sell:<8,.2f} │ ¥{buff_buy:<8,.2f} │")
    if yyyp_sell:
        lines.append(f"  │ 悠悠有品   │ ¥{yyyp_sell:<8,.2f} │ ¥{yyyp_buy:<8,.2f} │")
    if steam_sell:
        lines.append(f"  │ Steam      │ ¥{steam_sell:<8,.2f} │ ¥{steam_buy:<8,.2f} │")
    lines.append("  └────────────┴────────────┴────────────┘")

    # 流通量
    lines.append("")
    buff_sell_num = detail.get("buff_sell_num", 0)
    buff_buy_num = detail.get("buff_buy_num", 0)
    yyyp_sell_num = detail.get("yyyp_sell_num", 0)
    lines.append(f"  📦 流通量: BUFF在售 {buff_sell_num} | BUFF求购 {buff_buy_num} | 悠悠在售 {yyyp_sell_num}")

    # 价格走势图
    lines.append("")
    ts = chart_data.get("timestamps", [])
    ps = chart_data.get("prices", [])
    if ts and ps:
        lines.append(render_price_chart(ts, ps))
    else:
        lines.append("  (暂无走势数据)")

    # Steam 挂刀比例
    buff_steam_buy = detail.get("buff_steam_buy_conversion")
    steam_buff_buy = detail.get("steam_buff_buy_conversion")
    if buff_steam_buy:
        lines.append("")
        lines.append("  🔄 挂刀汇率")
        lines.append(f"    BUFF→Steam (求购): {buff_steam_buy:.0%}")
        if steam_buff_buy:
            lines.append(f"    Steam→BUFF (求购): {steam_buff_buy:.0%}")

    lines.append("")
    lines.append("=" * 56)

    return "\n".join(lines)
