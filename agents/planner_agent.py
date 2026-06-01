"""
=================================================================
  总控规划 Agent
  职责：整体流程调度、按顺序分发任务给各 Agent、
        汇总结果、驱动缓存更新
  流程：爬取 → 解析 → 研判 → 提醒 → 更新缓存
=================================================================
"""
import json
import sys
from datetime import datetime

from config import DASHSCOPE_API_KEY, LLM_MODEL, LLM_TEMPERATURE, MONITOR_URL
from cache.data_cache import save_cache, load_cache
from agents.crawler_agent import CrawlerAgent
from agents.parser_agent import ParserAgent
from agents.judge_agent import JudgeAgent
from agents.notice_agent import NoticeAgent


def _get_llm():
    """初始化阿里云百炼大模型（用于生成计划评述）"""
    if not DASHSCOPE_API_KEY:
        print("  ❌ 错误: 未设置 DASHSCOPE_API_KEY 环境变量")
        sys.exit(1)
    try:
        from langchain_community.chat_models import ChatTongyi
        return ChatTongyi(
            model=LLM_MODEL,
            api_key=DASHSCOPE_API_KEY,
            temperature=LLM_TEMPERATURE,
        )
    except ImportError as e:
        print(f"  ❌ 缺少依赖: {e}")
        print("  💡 请运行: pip install langchain langchain-community dashscope")
        sys.exit(1)


PLANNER_SYSTEM_PROMPT = """你是一个多 Agent 系统的总控规划专家。

当前监控目标是 {url}。

你的工作流程是：
1️⃣ 爬取 Agent — 请求目标网页，获取 HTML
2️⃣ 解析 Agent — 从 HTML 提取结构化数据
3️⃣ 研判 Agent — 对比当前数据和历史缓存，判断异动
4️⃣ 提醒 Agent — 根据研判结果生成播报/告警消息
5️⃣ 更新缓存 — 将本轮数据写入本地缓存

请根据系统返回的各步骤结果，生成一段简洁的本轮执行摘要。
摘要应包括各步骤的关键结果。
使用中文，控制在 100 字以内。"""


class PlannerAgent:
    """规划 Agent：总控调度，串联全流程"""

    def __init__(self):
        """初始化所有子 Agent"""
        self.crawler = CrawlerAgent()
        self.parser = ParserAgent()
        self.judge = JudgeAgent()
        self.notice = NoticeAgent()

    # ----------------------------------------------------------
    #  主执行流程
    # ----------------------------------------------------------
    def run(self) -> dict:
        """
        执行一轮完整的监控流程

        返回:
            本轮的状态字典（包含所有中间结果）
        """
        run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'='*60}")
        print(f"  🚀【规划 Agent】开始执行监控任务")
        print(f"  🕐 时间: {run_time}")
        print(f"  🎯 目标: {MONITOR_URL}")
        print(f"{'='*60}")

        # -------------------------------------------------------
        #  Step 1: 爬取
        # -------------------------------------------------------
        print(f"\n  📋 步骤 1/4: 分发爬取任务 → CrawlerAgent")
        html = self.crawler.run(MONITOR_URL)
        if not html:
            print("  ❌ 流程终止：爬取失败")
            return {"error": "爬取失败", "run_time": run_time}

        # -------------------------------------------------------
        #  Step 2: 解析
        # -------------------------------------------------------
        print(f"\n  📋 步骤 2/4: 分发解析任务 → ParserAgent")
        parsed_data = self.parser.run(html)
        if "error" in parsed_data:
            print("  ⚠️  解析出现异常，尝试继续后续流程")

        # -------------------------------------------------------
        #  Step 3: 研判
        # -------------------------------------------------------
        print(f"\n  📋 步骤 3/4: 分发研判任务 → JudgeAgent")
        cached_data = load_cache()
        judgment = self.judge.run(parsed_data, cached_data)

        # -------------------------------------------------------
        #  Step 4: 提醒
        # -------------------------------------------------------
        print(f"\n  📋 步骤 4/4: 分发提醒任务 → NoticeAgent")
        notice_message = self.notice.run(judgment, parsed_data)

        # -------------------------------------------------------
        #  更新缓存：将本轮数据保存
        # -------------------------------------------------------
        print(f"\n  💾 正在更新缓存...")
        save_cache(parsed_data)

        # -------------------------------------------------------
        #  汇总结果
        # -------------------------------------------------------
        state = {
            "run_time": run_time,
            "url": MONITOR_URL,
            "raw_html_length": len(html),
            "parsed_data": parsed_data,
            "cached_data": cached_data,
            "judgment": judgment,
            "notice_message": notice_message,
            "error": None,
        }

        # 用 LLM 生成执行摘要
        self._generate_summary(state)

        return state

    # ----------------------------------------------------------
    #  生成执行摘要
    # ----------------------------------------------------------
    def _generate_summary(self, state: dict) -> None:
        """调用大模型生成本轮执行摘要"""
        try:
            llm = _get_llm()
            from langchain.schema import HumanMessage, SystemMessage

            summary_prompt = (
                f"本轮执行结果：\n"
                f"- 爬取状态: {'✅ 成功' if state['raw_html_length'] > 0 else '❌ 失败'}\n"
                f"- 解析数据: {json.dumps(state['parsed_data'], ensure_ascii=False)}\n"
                f"- 研判结果: 变化={'是' if state['judgment'].get('has_changed') else '否'}, "
                f"趋势={state['judgment'].get('trend', '未知')}\n"
                f"- 提醒消息: {state['notice_message']}\n"
            )

            messages = [
                SystemMessage(
                    content=PLANNER_SYSTEM_PROMPT.format(url=MONITOR_URL)
                ),
                HumanMessage(content=summary_prompt),
            ]

            response = llm.invoke(messages)
            summary = response.content.strip()
            print(f"\n  📝 执行摘要:\n  {summary}")

        except Exception as e:
            print(f"\n  ⚠️  生成摘要失败: {e}")

        print(f"\n{'='*60}")
        print(f"  ✅ 本轮监控流程执行完毕")
        print(f"{'='*60}")
