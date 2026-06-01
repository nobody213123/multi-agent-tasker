"""
=================================================================
  网页请求工具模块
  功能：使用 Playwright 无头浏览器加载目标页面，
        等待 JavaScript 渲染完成后获取页面可见文本，
        统一处理超时、连接失败等异常
=================================================================
"""
from config import RENDER_TIMEOUT


def fetch_page(url: str) -> str:
    """
    使用无头浏览器加载目标网页，返回页面渲染后的可见文本

    返回可见文本而非原始 HTML 的原因：
      - SPA 网站的原始 HTML 大量是 <script>/<style> 标签
      - 可见文本干净、简洁，LLM 解析效率更高

    参数:
        url: 目标网址

    返回:
        网页渲染后的可见文本；若请求失败则返回空字符串
    """
    print(f"  🌐 正在启动浏览器加载: {url}")

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    except ImportError:
        print("  ❌ 缺少 playwright 依赖")
        print("  💡 请运行: pip install playwright && playwright install chromium")
        return ""

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )

            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="zh-CN",
            )

            page = context.new_page()

            # 导航并等待网络空闲（所有 XHR/fetch 完成）
            page.goto(url, timeout=RENDER_TIMEOUT * 1000, wait_until="networkidle")

            # 额外等待动态渲染完成
            page.wait_for_timeout(3000)

            # 获取页面可见文本（不含 HTML 标签）
            text = page.inner_text("body")
            browser.close()

            # 清理：合并多余空行
            lines = [line.strip() for line in text.split("\n")]
            text = "\n".join(line for line in lines if line)

            print(f"  ✅ 页面加载完成，获取到 {len(text)} 个字符的可见文本")
            return text

    except PlaywrightTimeout:
        print(f"  ❌ 页面渲染超时（{RENDER_TIMEOUT} 秒）")
    except Exception as e:
        print(f"  ❌ 浏览器加载异常: {e}")

    return ""
