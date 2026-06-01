"""
=================================================================
  数据爬取 Agent
  职责：调用网页请求工具，获取目标页面的 HTML 原始内容
  输入：目标 URL
  输出：原始 HTML 字符串
=================================================================
"""
from tools.web_request import fetch_page


class CrawlerAgent:
    """爬取 Agent：负责获取网页源码"""

    def run(self, url: str) -> str:
        """
        执行爬取任务

        参数:
            url: 目标网址

        返回:
            网页 HTML 字符串（失败时返回空字符串）
        """
        print(f"\n{'='*50}")
        print(f"  🔍【爬取 Agent】开始抓取: {url}")
        print(f"{'='*50}")

        html = fetch_page(url)

        if html:
            print(f"  ✅ 抓取完成，获取到 {len(html)} 个字符")
        else:
            print(f"  ❌ 抓取失败，页面内容为空")

        return html
