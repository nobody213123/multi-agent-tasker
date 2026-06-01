"""
=================================================================
  程序入口模块
  功能：提供菜单选择
        1. 盯盘监控（定时轮询全品类大盘指数）
        2. 交互式搜索饰品价格
=================================================================
"""
import time
import threading
import json
from pathlib import Path

from config import POLL_INTERVAL_SECONDS, DASHSCOPE_API_KEY, CACHE_FILE_PATH

# ── 大盘指数监控 ──────────────────────────────────────────────
# 使用 requests 直调 current_data API，对比缓存，打印表格

CACHE_INDEX_FILE = Path(CACHE_FILE_PATH).parent / "index_cache.json"


def load_index_cache() -> dict:
    """读取上轮缓存的大盘指数"""
    if CACHE_INDEX_FILE.exists():
        try:
            return json.loads(CACHE_INDEX_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_index_cache(indices: list) -> None:
    """保存当前指数到缓存"""
    cache = {idx["name"]: {"value": idx["value"], "change_pct": idx["change_pct"]}
             for idx in indices}
    CACHE_INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_INDEX_FILE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def run_one_index_cycle(prev_cache: dict) -> dict:
    """执行一轮指数监控"""
    from tools.index_api import fetch_indices, format_indices_table

    print(f"\n{'─' * 60}")
    print(f"  📡 正在获取全品类大盘指数...")
    print(f"{'─' * 60}")

    data = fetch_indices()
    if not data.get("indices"):
        print("  ❌ 获取指数失败，等待下一轮重试")
        return {"indices": [], "online": {}, "greedy": {}, "rate": {}}

    table = format_indices_table(data, prev_cache)
    print(table)

    return data


def run_monitor_mode():
    """大盘指数定时轮询模式"""
    stop_event = threading.Event()

    # 后台监听 exit
    def listener():
        while not stop_event.is_set():
            try:
                cmd = input()
                if cmd.strip().lower() == "exit":
                    stop_event.set()
            except (EOFError, KeyboardInterrupt):
                stop_event.set()
                break

    threading.Thread(target=listener, daemon=True).start()

    cycle = 0
    prev_cache = load_index_cache()
    if prev_cache:
        print(f"  📦 已读取上轮缓存")

    try:
        while not stop_event.is_set():
            cycle += 1
            print(f"\n{'#' * 60}")
            print(f"  🔄 第 {cycle} 轮监控  (输入 exit 返回主菜单)")
            print(f"{'#' * 60}")

            data = run_one_index_cycle(prev_cache)
            indices = data.get("indices", [])

            if indices:
                save_index_cache(indices)
                prev_cache = {idx["name"]: {"value": idx["value"],
                                            "change_pct": idx["change_pct"]}
                              for idx in indices}

            # 等待（可中断）
            print(f"\n  ⏳ 等待 {POLL_INTERVAL_SECONDS} 秒后刷新...")
            for _ in range(POLL_INTERVAL_SECONDS):
                if stop_event.is_set():
                    break
                time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n  🛑 检测到 Ctrl+C，返回主菜单...")

    print(f"\n  👋 盯盘已停止，共执行 {cycle} 轮")


# ── 搜索模式 ──────────────────────────────────────────────────

def run_web_mode():
    """启动网页可视化界面"""
    from web.app import run_server
    run_server()


def run_search_mode():
    """交互式饰品价格查询"""
    from tools.item_api import ItemAPI
    from tools.chart_renderer import render_item_full

    api = ItemAPI()

    try:
        while True:
            print("\n" + "=" * 56)
            print("  🔍 饰品价格查询  (输入 exit 返回主菜单)")
            print("=" * 56)
            keyword = input("\n  请输入饰品名称: ").strip()

            if keyword.lower() == "exit":
                break
            if not keyword:
                continue

            print(f"  🔎 搜索 \"{keyword}\"...")
            results = api.search(keyword)

            if not results:
                print("  ❌ 未找到匹配结果")
                continue

            print(f"\n  共 {len(results)} 个结果:")
            for i, item in enumerate(results[:15], 1):
                print(f"  {i:>2}. {item['value']}")
            if len(results) > 15:
                print(f"  ... 还有 {len(results) - 15} 个")

            choice = input(f"\n  序号 (1-{min(15, len(results))}，0 重新搜索): ").strip()
            if choice == "0" or not choice:
                continue

            try:
                idx = int(choice) - 1
                if idx < 0 or idx >= min(15, len(results)):
                    print("  ❌ 序号无效")
                    continue
            except ValueError:
                print("  ❌ 请输入数字")
                continue

            sel = results[idx]
            print(f"\n  ⏳ 加载 \"{sel['value']}\"...")
            data = api.get_detail_and_chart(sel["id"])

            if "error" in data:
                print(f"  ❌ {data['error']}")
                continue

            print(render_item_full(sel["id"], data["detail"], data["chart"]))
            input("\n  ⏎ 回车继续查询...")

    finally:
        api.close()


# ── 主菜单 ────────────────────────────────────────────────────

def print_banner():
    print("""
    ╔══════════════════════════════════════════════════╗
    ║         🤖 网页数据自动盯盘多Agent系统 🤖        ║
    ║                                                   ║
    ║  大盘指数: 全品类轮询对比                        ║
    ║  饰品搜索: 实时价格 / 走势图 / 涨跌幅            ║
    ║                                                   ║
    ╚══════════════════════════════════════════════════╝
    """)


def print_menu():
    print()
    print("  ╔══════════════════════════════════╗")
    print("  ║         主菜单                   ║")
    print("  ╠══════════════════════════════════╣")
    print("  ║  1. 大盘指数盯盘                 ║")
    print("  ║     (全品类指数轮询 + 涨跌标红)  ║")
    print("  ║                                  ║")
    print("  ║  2. 搜索饰品价格                 ║")
    print("  ║     (查询实时价格/走势/涨跌幅)   ║")
    print("  ║                                  ║")
    print("  ║  3. 启动网页界面                 ║")
    print("  ║     (浏览器打开可视化看板)       ║")
    print("  ║                                  ║")
    print("  ║  exit → 退出                     ║")
    print("  ╚══════════════════════════════════╝")
    print()


def main():
    print_banner()

    if not DASHSCOPE_API_KEY:
        print("  ❌ 未检测到 DASHSCOPE_API_KEY 环境变量")
        print("  💡 请在 .env 中填写或 export 设置")
        return

    print("  ✅ API 密钥已配置\n")

    while True:
        print_menu()
        choice = input("  请选择 (1 / 2 / 3 / exit): ").strip()

        if choice == "1":
            print(f"\n  ✅ 轮询间隔: {POLL_INTERVAL_SECONDS} 秒")
            print(f"  💡 监控中输 exit 可返回主菜单\n")
            run_monitor_mode()

        elif choice == "2":
            run_search_mode()

        elif choice == "3":
            run_web_mode()

        elif choice.lower() == "exit":
            print("\n  👋 再见！")
            break

        else:
            print("  ❌ 输入 1、2、3 或 exit")


if __name__ == "__main__":
    main()
