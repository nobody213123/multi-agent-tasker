import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import env  # noqa: F401

import time

from flask import Flask, jsonify, request, render_template

from tools.providers.csqaq import CsqaqIndexProvider, CsqaqRankProvider, CsqaqSearchProvider
from orchestration.coordinator import Coordinator

TEMPLATE_DIR = ROOT_DIR / "web" / "templates"
app = Flask(__name__, template_folder=str(TEMPLATE_DIR))

_search_provider = None
_rank_provider = None
_index_provider = None
_coordinator = None
_last_recommend_result = None
_last_recommend_time = 0
_last_rank_result = None
_last_rank_time = 0


def get_search_provider():
    global _search_provider
    if _search_provider is None:
        _search_provider = CsqaqSearchProvider()
    return _search_provider


def get_rank_provider():
    global _rank_provider
    if _rank_provider is None:
        _rank_provider = CsqaqRankProvider()
    return _rank_provider


def get_index_provider():
    global _index_provider
    if _index_provider is None:
        _index_provider = CsqaqIndexProvider()
    return _index_provider


def get_coordinator():
    global _coordinator
    if _coordinator is None:
        _coordinator = Coordinator(
            index_provider=get_index_provider(),
            rank_provider=get_rank_provider(),
        )
    return _coordinator


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/indices")
def api_indices():
    try:
        overview = get_index_provider().fetch_indices()
        return jsonify({
            "indices": [
                {"id": i.id, "name": i.name, "value": i.value,
                 "change": i.change, "change_pct": i.change_pct}
                for i in overview.indices
            ],
            "online": {
                "current": overview.online.current,
                "today_peak": overview.online.today_peak,
                "month_peak": overview.online.month_peak,
                "month_player": overview.online.month_player,
            },
            "greedy": {"level": overview.greedy.level, "label": overview.greedy.label},
            "rate": {
                "day_up": overview.rate.day_up,
                "day_down": overview.rate.day_down,
                "week_up": overview.rate.week_up,
                "week_down": overview.rate.week_down,
            },
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/search")
def api_search():
    keyword = request.args.get("q", "").strip()
    if not keyword:
        return jsonify({"results": []})
    try:
        provider = get_search_provider()
        results = provider.search(keyword)
        return jsonify({"results": [{"id": r.id, "value": r.value} for r in results]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/item/<item_id>")
def api_item_detail(item_id):
    try:
        provider = get_search_provider()
        detail = provider.get_detail(item_id)
        chart = provider.get_chart(item_id)
        return jsonify({
            "detail": {
                "name": detail.name,
                "market_hash_name": detail.market_hash_name,
                "type_localized_name": detail.type_name,
                "buff_sell_price": detail.buff_sell_price,
                "buff_buy_price": detail.buff_buy_price,
                "buff_sell_num": detail.buff_sell_num,
                "buff_buy_num": detail.buff_buy_num,
                "yyyp_sell_price": detail.yyyp_sell_price,
                "yyyp_buy_price": detail.yyyp_buy_price,
                "yyyp_sell_num": detail.yyyp_sell_num,
                "steam_sell_price": detail.steam_sell_price,
                "steam_buy_price": detail.steam_buy_price,
                "sell_price_rate_1": detail.sell_price_rate_1,
                "sell_price_rate_7": detail.sell_price_rate_7,
                "sell_price_rate_15": detail.sell_price_rate_15,
                "sell_price_rate_30": detail.sell_price_rate_30,
                "statistic": detail.statistic,
            },
            "chart": {
                "timestamps": chart.timestamps,
                "prices": chart.prices,
                "volumes": chart.volumes,
            },
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/rank")
def api_rank():
    global _last_rank_result, _last_rank_time
    try:
        rank_type = request.args.get("type", "price")
        type_map = {
            "price": "sell_price_rate_1",
            "hot": "rank_num",
            "supply": "statistic",
            "turnover": "turnover_number",
            "diff": "sell_buy_diff_buff",
            "quantity": "rank_num",
            "cashout": "sell_buy_diff_buff",
        }
        now = time.time()
        if _last_rank_result and (now - _last_rank_time) < CACHE_TTL:
            data = _last_rank_result
        else:
            data = get_rank_provider().fetch_ranks()
            _last_rank_result = data
            _last_rank_time = now
        key = type_map.get(rank_type, "sell_price_rate_1")
        items = [item.__dict__ for item in data.get(key, [])]
        return jsonify({"data": items})
    except Exception as e:
        return jsonify({"data": [], "error": str(e)}), 500


CACHE_TTL = 300

@app.route("/api/recommend")
def api_recommend():
    global _last_recommend_result, _last_recommend_time
    try:
        now = time.time()
        if _last_recommend_result and (now - _last_recommend_time) < CACHE_TTL:
            result = _last_recommend_result
        else:
            coord = get_coordinator()
            result = coord.run_cycle()
            _last_recommend_result = result
            _last_recommend_time = now
        return jsonify({
            "recommendations": [
                {
                    "name": r.name,
                    "strategy": r.strategy,
                    "reason": r.reason,
                    "risk": r.risk,
                    "target_price": r.target_price,
                    "signal_strength": r.signal_strength,
                }
                for r in result.recommendations
            ],
            "analysis": result.analysis.summary if result.analysis else "",
            "alerts": result.alerts,
            "cycle": result.cycle,
            "timestamp": result.timestamp,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/lease-recommend")
def api_lease_recommend():
    global _last_recommend_result, _last_recommend_time
    try:
        now = time.time()
        if _last_recommend_result and (now - _last_recommend_time) < CACHE_TTL:
            result = _last_recommend_result
        else:
            coord = get_coordinator()
            result = coord.run_cycle()
            _last_recommend_result = result
            _last_recommend_time = now
        return jsonify({
            "recommendations": [
                {
                    "name": r.name,
                    "cost": f"¥{r.price_at_recommend:,.2f}" if r.price_at_recommend else "—",
                    "daily_lease": f"¥{(r.price_at_recommend * 0.003):,.2f}" if r.price_at_recommend else "—",
                    "risk_level": r.risk,
                    "monthly_roi": "—",
                    "reason": r.reason,
                    "advice": r.strategy,
                    "risk": r.risk,
                }
                for r in result.recommendations
            ],
            "analysis": result.analysis.summary if result.analysis else "",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/backtest")
def api_backtest():
    try:
        coord = get_coordinator()
        report = coord.run_backtest(days=7)
        return jsonify({
            "total": report.total,
            "hit": report.hit,
            "accuracy": report.accuracy,
            "breakdown": {
                k: {"total": v.total, "hit": v.hit, "accuracy": v.accuracy}
                for k, v in report.breakdown.items()
            },
            "summary": report.summary,
            "period_days": report.period_days,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/cycle")
def api_coordinator_status():
    coord = get_coordinator()
    return jsonify({
        "cycle": coord.cycle,
        "has_recommender": True,
    })


@app.teardown_appcontext
def shutdown_session(exception=None):
    global _search_provider
    if _search_provider is not None:
        _search_provider.close()
        _search_provider = None


def run_server(host="0.0.0.0", port=8080):
    print(f"\n  🌐 正在启动 Web 界面...")
    print(f"  📡 访问地址: http://localhost:{port}")
    print(f"  💡 按 Ctrl+C 停止服务器\n")
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    run_server()
