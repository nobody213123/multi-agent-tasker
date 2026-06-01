"""
=================================================================
  Web 搜索应用 — CS 饰品实时行情查询
  功能：搜索饰品名称 → 显示实时价格、涨跌幅、多平台比价、K线图
  技术：Flask + Playwright（持久化浏览器）
=================================================================
"""
import re
import sys
import json
import threading
from datetime import datetime, timedelta

from flask import Flask, render_template, jsonify, request

from config import DASHSCOPE_API_KEY

# ============================================================
#  Playwright 持久化浏览器管理器
# ============================================================
_browser = None
_context = None
_page = None
_playwright = None
_lock = threading.Lock()


def _ensure_browser():
    """确保 Playwright 浏览器已启动并登录 csqaq.com"""
    global _browser, _context, _page, _playwright
    if _page is not None:
        return _page
    try:
        from playwright.sync_api import sync_playwright, TimeoutError
    except ImportError:
        print("❌ 请安装 playwright: pip install playwright && playwright install chromium")
        sys.exit(1)

    _playwright = sync_playwright().start()
    _browser = _playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox"],
    )
    _context = _browser.new_context(locale="zh-CN")
    _page = _context.new_page()
    _page.goto("https://csqaq.com", wait_until="networkidle", timeout=30000)
    _page.wait_for_timeout(2000)
    print("✅ Playwright 浏览器已就绪")
    return _page


def _close_browser():
    """关闭浏览器"""
    global _browser, _context, _page, _playwright
    try:
        if _browser:
            _browser.close()
    except:
        pass
    try:
        if _playwright:
            _playwright.stop()
    except:
        pass
    _browser = _context = _page = _playwright = None


# ============================================================
#  搜索 + 获取价格
# ============================================================

def search_items(keyword: str) -> list:
    """
    搜索饰品，返回匹配结果列表
    每个结果: {id, name}
    """
    page = _ensure_browser()
    results = []

    try:
        # 激活搜索框
        page.keyboard.press("/")
        page.wait_for_timeout(300)
        page.keyboard.type(keyword)
        page.wait_for_timeout(1000)

        # 从页面提取搜索建议
        suggest_items = page.evaluate(f'''
            () => {{
                const items = [];
                const els = document.querySelectorAll('[class*="suggest"] li, [class*="Suggestion"] li, li[class*="item"]');
                els.forEach(el => {{
                    const text = el.innerText.trim();
                    if (text) items.push(text);
                }});
                return items;
            }}
        ''')

        # 如果页面建议拿不到，直接用 text 搜
        if not suggest_items:
            text = page.inner_text("body")
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            suggest_items = [l for l in lines if keyword in l][:10]

        # 通过 API 获取具体 ID
        for name in suggest_items[:10]:
            # 搜索商品拿 ID
            items = page.evaluate(f'''
                fetch("https://csqaq.com/proxies/api/v1/search/suggest?text={keyword}")
                    .then(r => r.json())
                    .then(d => d.data || [])
                    .catch(() => [])
            ''')
            if items:
                for item in items:
                    results.append({"id": item["id"], "name": item["value"]})
                break

        # 关闭搜索
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)

    except Exception as e:
        print(f"  搜索异常: {e}")

    return results


def get_price(item_id: int) -> dict:
    """
    获取指定商品的完整价格数据
    """
    page = _ensure_browser()
    result = {"id": item_id, "name": "", "prices": {}, "changes": {}}

    try:
        page.goto(f"https://csqaq.com/goods/{item_id}",
                   wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)

        text = page.inner_text("body")

        # --------------------------------------------------
        #  解析名称
        # --------------------------------------------------
        name_match = re.search(r'^(.+?)\n', text)
        if name_match:
            result["name"] = name_match.group(1).strip()

        # --------------------------------------------------
        #  解析涨跌幅
        # --------------------------------------------------
        # 今日: ￥50（0.62%）
        patterns = {
            "今日": r'今日\s*[￥¥]\s*[\d.]+[（(]([+-]?[\d.]+)%[）)]',
            "本周": r'本周\s*[￥¥]\s*[\d.]+[（(]([+-]?[\d.]+)%[）)]',
            "本月": r'本月\s*[￥¥]\s*[\d.]+[（(]([+-]?[\d.]+)%[）)]',
        }
        for key, pat in patterns.items():
            m = re.search(pat, text)
            if m:
                result["changes"][key] = float(m.group(1))

        # --------------------------------------------------
        #  解析各平台价格
        # --------------------------------------------------
        # BUFF / 悠悠有品 / Steam / C5GAME / IGXE ...
        platform_pattern = re.compile(
            r'(BUFF|悠悠有品|Steam|C5GAME|IGXE|ECOSteam)\s*'
            r'在售价[:：]\s*([\d.]+)[￥¥]?\s*'
            r'求购价[:：]\s*([\d.]+)[￥¥]?'
        )
        for m in platform_pattern.finditer(text):
            platform = m.group(1)
            result["prices"][platform] = {
                "sell": float(m.group(2)),
                "buy": float(m.group(3)),
            }

        # 解析在售/求购数
        stock_pattern = re.compile(
            r'(BUFF|悠悠有品|Steam|C5GAME|IGXE|ECOSteam)\s*'
            r'.*?在售数[:：]\s*(\d+)'
        )
        for m in stock_pattern.finditer(text):
            platform = m.group(1)
            if platform in result["prices"]:
                result["prices"][platform]["sell_num"] = int(m.group(2))

        # 获取在售价（从 BUFF 取）
        if "BUFF" in result["prices"]:
            result["current_price"] = result["prices"]["BUFF"]["sell"]

        # --------------------------------------------------
        #  获取 30 天图表数据
        # --------------------------------------------------
        try:
            chart_resp = page.evaluate(f'''
                fetch("https://csqaq.com/proxies/api/v1/info/chart?id={item_id}&type=daily")
                    .then(r => r.json())
                    .then(d => {{
                        if (d.code === 200) {{
                            return {{timestamps: d.data.timestamp, prices: d.data.close}};
                        }}
                        return null;
                    }})
                    .catch(() => null)
            ''')
            if chart_resp and chart_resp.get("timestamps"):
                result["chart"] = chart_resp
        except Exception:
            pass

    except Exception as e:
        print(f"  获取价格异常 (id={item_id}): {e}")

    return result


# ============================================================
#  Flask Web 应用
# ============================================================
app = Flask(__name__)


@app.route("/")
def index():
    """首页"""
    return render_template("index.html")


@app.route("/api/search")
def api_search():
    """搜索 API: /api/search?q=蝴蝶刀"""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"code": 400, "msg": "请输入搜索关键词"})

    with _lock:
        items = search_items(q)

    if not items:
        return jsonify({"code": 404, "msg": f"未找到与「{q}」相关的商品"})

    # 取第一个结果的 ID 获取价格
    first_id = int(items[0]["id"])
    with _lock:
        price_data = get_price(first_id)

    return jsonify({
        "code": 200,
        "suggestions": items[:10],
        "detail": price_data,
    })


@app.route("/api/price/<int:item_id>")
def api_price(item_id):
    """根据商品 ID 获取价格"""
    with _lock:
        data = get_price(item_id)
    return jsonify({"code": 200, "data": data})


@app.teardown_appcontext
def shutdown(_=None):
    pass


def main():
    """启动 Web 应用"""
    print("🚀 正在启动 CS 饰品行情查询服务...")
    _ensure_browser()

    print("✅ 服务已就绪，请访问:")
    print("   http://127.0.0.1:5000")
    print("   ⚠️  首次搜索需要约 5-10 秒（Playwright 渲染页面）")
    print("   输入 Ctrl+C 停止服务")

    try:
        app.run(debug=False, host="127.0.0.1", port=5000)
    finally:
        _close_browser()


if __name__ == "__main__":
    main()
