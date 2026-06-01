"""
=================================================================
  大盘指数数据模块
  功能：通过 csqaq.com 的 current_data API 获取所有品类指数、
        当前在线人数、市场热度等
=================================================================
"""
from datetime import datetime

API_URL = "https://csqaq.com/proxies/api/v1/current_data"


def fetch_indices() -> dict:
    """
    从 csqaq.com 获取全品类大盘指数 + 市场热度 + 在线数据

    返回:
        {
            "indices": [ {品类指数列表} ],
            "online": { "current": 当前在线, "today_peak": 今日峰值,
                        "month_peak": 本月峰值, "month_player": 本月活跃 },
            "greedy": { "level": "high/low", "label": "活跃/恐慌" },
            "rate": { 涨跌商品统计 },
        }
        网络异常时返回 {"indices": [], "online": {}, "greedy": {}}
    """
    import requests

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://csqaq.com/",
    }

    try:
        resp = requests.get(API_URL, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 200:
            print(f"  ⚠️  API 返回异常: {data.get('msg', '未知')}")
            return {"indices": [], "online": {}, "greedy": {}}

        d = data.get("data", {})

        # 品类指数
        raw_list = d.get("sub_index_data", [])
        indices = []
        for item in raw_list:
            indices.append({
                "id": item["id"],
                "name": item["name"],
                "value": item["market_index"],
                "change": item["chg_num"],
                "change_pct": item["chg_rate"],
                "high": item.get("high"),
                "low": item.get("low"),
                "updated_at": item.get("updated_at", ""),
            })

        # 在线数据
        on = d.get("online_number", {})
        online = {
            "current": on.get("current_number", 0),
            "today_peak": on.get("today_peak", 0),
            "month_peak": on.get("month_peak", 0),
            "month_player": on.get("month_player", 0),
            "rate": on.get("rate", 0),
        }

        # 贪婪指数（市场热度）
        g = d.get("greedy_status", {})
        greedy = {
            "level": g.get("level", "unknown"),
            "label": g.get("label", "未知"),
        }

        # 涨跌商品统计
        rt = d.get("rate_data", {})
        rate = {
            "day_up": rt.get("count_positive_1", 0),
            "day_down": rt.get("count_negative_1", 0),
            "day_flat": rt.get("count_zero_1", 0),
            "week_up": rt.get("count_positive_7", 0),
            "week_down": rt.get("count_negative_7", 0),
            "week_flat": rt.get("count_zero_7", 0),
        }

        return {
            "indices": indices,
            "online": online,
            "greedy": greedy,
            "rate": rate,
        }

    except requests.exceptions.Timeout:
        print("  ❌ 指数 API 请求超时")
    except requests.exceptions.ConnectionError:
        print("  ❌ 网络连接失败")
    except Exception as e:
        print(f"  ❌ 指数获取异常: {e}")

    return {"indices": [], "online": {}, "greedy": {}, "rate": {}}


def format_indices_table(data: dict, prev_cache: dict = None) -> str:
    """
    将指数 + 热度数据渲染为终端表格

    参数:
        data:       fetch_indices() 返回的完整字典
        prev_cache: 上轮缓存 { "品类名": {"value": ..., ...} }

    返回:
        格式化文本
    """
    indices = data.get("indices", [])
    online = data.get("online", {})
    greedy = data.get("greedy", {})
    rate = data.get("rate", {})

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not indices:
        return "  (暂无数据)"

    lines = []
    w = 60  # 表格宽度

    # ── 在线人数 & 热度顶栏 ──
    lines.append("")
    lines.append("╔" + "═" * w + "╗")

    cur = online.get("current", 0)
    peak = online.get("month_peak", 0)
    mp = online.get("month_player", 0)
    greedy_label = greedy.get("label", "")
    greedy_level = greedy.get("level", "")

    heat_icon = "🔥" if greedy_level == "high" else "❄️" if greedy_level == "low" else "⚡"

    # 用 padded_left / padded_right 来平分空间
    left = f"👥 在线 {cur:>10,}"
    right = f"{heat_icon} {greedy_label}"
    padding = w - len(left) - len(right) - 2  # -2 for 边空格
    lines.append(f"║ {left}{' ' * padding}{right} ║")

    up = rate.get("day_up", 0)
    down = rate.get("day_down", 0)
    left2 = f"🏔 本月峰值 {peak:>10,}  |  月活跃 {mp:>10,}"
    right2 = f"📈 {up:>4}  📉 {down:>4}"
    padding2 = w - len(left2) - len(right2) - 2
    lines.append(f"║ {left2}{' ' * padding2}{right2} ║")

    lines.append("╠" + "═" * w + "╣")

    # ── 大盘指数表头 ──
    lines.append(f"║  📊 全品类大盘指数          {now}  ║")
    lines.append("╠════════════════════════════════════════════════════════════╣")
    lines.append(f"║  {'品类':<10} {'指数':>10} {'涨跌额':>10} {'涨跌幅':>8}    ║")
    lines.append("║────────────────────────────────────────────────────────────║")

    for idx in indices:
        name = idx["name"]
        value = idx["value"]
        change = idx["change"]
        change_pct = idx["change_pct"]

        arrow = "▲" if change_pct > 0 else "▼" if change_pct < 0 else "─"

        cache_mark = ""
        if prev_cache and name in prev_cache:
            prev = prev_cache[name]
            diff = value - prev["value"]
            if diff > 0.01:
                cache_mark = " 🔺"
            elif diff < -0.01:
                cache_mark = " 🔻"
            else:
                cache_mark = "  ·"

        lines.append(
            f"║  {name:<10} {value:>10.2f} {change:>+10.2f} {change_pct:>+7.2f}% {arrow}{cache_mark}  ║"
        )

    lines.append("╚" + "═" * w + "╝")

    return "\n".join(lines)
