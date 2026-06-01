"""
=================================================================
  Flask Web 服务器
  功能：提供浏览器网页界面，展示大盘指数 + 饰品搜索
=================================================================
"""
import sys
import os
from pathlib import Path

# 将项目根目录加入 sys.path，确保能 import 其他模块
ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from flask import Flask, render_template, jsonify, request
from tools.index_api import fetch_indices
from tools.item_api import ItemAPI

app = Flask(__name__)

# 全局搜索 API 实例（复用浏览器会话）
_item_api = None


def get_item_api():
    """获取或初始化搜索 API（懒加载）"""
    global _item_api
    if _item_api is None:
        _item_api = ItemAPI()
    return _item_api


# ── 页面路由 ──────────────────────────────────────────────────

@app.route("/")
def index():
    """主页"""
    return render_template("index.html")


# ── API 路由 ──────────────────────────────────────────────────

@app.route("/api/indices")
def api_indices():
    """获取全品类大盘指数"""
    try:
        data = fetch_indices()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/search")
def api_search():
    """搜索饰品"""
    keyword = request.args.get("q", "").strip()
    if not keyword:
        return jsonify({"results": []})

    try:
        api = get_item_api()
        results = api.search(keyword)
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 排行榜数据 ──────────────────────────────────────────────

# 8 个榜单的排序 key 映射
RANK_TYPES = {
    "price":       "价格_价格上升(百分比)_近1天",
    "quantity":    "在售数量_升序",
    "lease":       "租赁_短租租金",
    "hot":         "热门关注_降序",
    "diff":        "价格_售价减求购价(金额)_升序(BUFF)",
    "supply":      "存世量_存世量_升序",
    "turnover":    "成交量_Steam日成交量",
    "cashout":     "挂刀套现_Steam求购挂刀",
}


@app.route("/api/rank")
def api_rank():
    """获取排行榜数据（通过 Playwright 浏览器会话）"""
    rank_type = request.args.get("type", "price")
    sort_key = RANK_TYPES.get(rank_type, RANK_TYPES["price"])

    body = {
        "page_index": 1,
        "page_size": 30,
        "search": "",
        "filter": {
            "价格最低价": 50,
            "在售最少": 50,
            "求购最少": 20,
            "类别": ["★", "普通"],
            "排序": [sort_key],
        },
        "show_recently_price": True,
    }

    try:
        from playwright.sync_api import sync_playwright

        captured = {}

        def on_resp(resp):
            if "get_rank_list" in resp.url:
                try:
                    j = resp.json()
                    if j.get("code") == 200:
                        captured["data"] = j["data"]
                except Exception:
                    pass

        pw = sync_playwright().start()
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page()
        page.on("response", on_resp)

        # 导航到 rank 页触发默认数据加载
        page.goto("https://csqaq.com/rank", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        # 点击对应 tab 触发请求
        tab_map = {
            "price": "价格榜", "quantity": "数量榜", "lease": "租赁榜",
            "hot": "热门榜", "diff": "平台差价榜", "supply": "存世量榜",
            "turnover": "成交榜", "cashout": "挂刀套现",
        }
        tab_name = tab_map.get(rank_type, "价格榜")
        try:
            page.click(f'text="{tab_name}"')
            page.wait_for_timeout(2000)
        except Exception:
            pass

        browser.close()
        pw.stop()

        if "data" in captured:
            return jsonify(captured["data"])
        return jsonify({"error": "未能获取排行榜数据"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/item/<item_id>")
def api_item_detail(item_id):
    """获取饰品详情"""
    try:
        api = get_item_api()
        data = api.get_detail_and_chart(item_id)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/recommend")
def api_recommend():
    """AI 智能选品推荐"""
    try:
        from tools.recommend import get_recommendations
        data = get_recommendations()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.teardown_appcontext
def shutdown_session(exception=None):
    """应用关闭时关闭浏览器"""
    global _item_api
    if _item_api is not None:
        _item_api.close()
        _item_api = None


def run_server(host="0.0.0.0", port=8080):
    """启动 Web 服务器"""
    print(f"\n  🌐 正在启动 Web 界面...")
    print(f"  📡 访问地址: http://localhost:{port}")
    print(f"  💡 按 Ctrl+C 停止服务器\n")
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    run_server()
