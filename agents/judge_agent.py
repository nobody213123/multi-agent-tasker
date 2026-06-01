"""
=================================================================
  异动研判 Agent
  职责：对比当前解析数据和缓存历史数据，
        判断数据是否发生变化（上涨/下跌/持平/异常波动）
  输入：当前数据（dict） + 历史数据（dict）
  输出：研判结果（dict）
=================================================================
"""
import json
import sys

from config import DASHSCOPE_API_KEY, LLM_MODEL, LLM_TEMPERATURE


def _get_llm():
    """初始化阿里云百炼大模型"""
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


# 研判 Agent 的系统提示词
JUDGE_SYSTEM_PROMPT = """你是一个数据异动研判专家。

你的任务是对比当前数据与历史缓存数据，分析数据变化情况。

你需要判断：
1. 数据是否发生了变化
2. 如果变化了，是上涨还是下跌？变化幅度大约多少？
3. 是否存在异常波动（超出正常范围的大幅变化）
4. 总体趋势分析

请严格按以下 JSON 格式返回结果：
{
  "has_changed": true/false,
  "changes": ["具体变化1", "具体变化2"],
  "trend": "上涨/下跌/持平/未知",
  "change_percent": "变化的估算百分比（如 +5.2%）或 '未知'",
  "is_abnormal": true/false,
  "analysis": "简要说明具体变化情况"
}

只返回 JSON，不要包含其他文字。"""


class JudgeAgent:
    """研判 Agent：对比数据，判断异动"""

    def run(self, current_data: dict, cached_data: dict) -> dict:
        """
        执行研判任务

        参数:
            current_data: 当前轮次解析出的数据
            cached_data:  上一轮缓存的历史数据

        返回:
            研判结果字典
        """
        print(f"\n{'='*50}")
        print(f"  ⚖️ 【研判 Agent】正在对比分析数据...")
        print(f"{'='*50}")

        # 如果没有缓存数据（首次运行），无法对比
        if not cached_data:
            print("  ℹ️  无历史数据可对比，跳过研判")
            return {
                "has_changed": False,
                "changes": [],
                "trend": "首次运行，无历史数据",
                "change_percent": "未知",
                "is_abnormal": False,
                "analysis": "这是首次抓取，已保存当前数据作为基准，下次将进行对比分析。",
            }

        # 如果当前数据为空或有错误
        if not current_data or "error" in current_data:
            print("  ⚠️  当前数据异常，无法研判")
            return {
                "has_changed": False,
                "changes": [],
                "trend": "未知",
                "change_percent": "未知",
                "is_abnormal": False,
                "analysis": f"当前数据异常: {current_data.get('error', '数据为空')}",
            }

        llm = _get_llm()
        try:
            from langchain.schema import HumanMessage, SystemMessage

            current_str = json.dumps(current_data, ensure_ascii=False, indent=2)
            cached_str = json.dumps(cached_data, ensure_ascii=False, indent=2)

            messages = [
                SystemMessage(content=JUDGE_SYSTEM_PROMPT),
                HumanMessage(
                    content=(
                        f"当前数据（最新抓取）：\n{current_str}\n\n"
                        f"历史数据（上一轮缓存）：\n{cached_str}"
                    )
                ),
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

            judgment = json.loads(content)
            print(f"  ✅ 研判完成")
            print(f"     是否有变化: {'✅ 是' if judgment.get('has_changed') else '❌ 否'}")
            print(f"     趋势: {judgment.get('trend', '未知')}")
            print(f"     异常: {'⚠️ 是' if judgment.get('is_abnormal') else '✅ 否'}")
            if judgment.get("analysis"):
                print(f"     分析: {judgment['analysis']}")
            return judgment

        except json.JSONDecodeError as e:
            print(f"  ⚠️  研判结果 JSON 解析失败: {e}")
            return {
                "has_changed": False,
                "trend": "研判失败",
                "is_abnormal": False,
                "analysis": f"研判结果解析异常: {e}",
            }
        except Exception as e:
            print(f"  ❌ 研判过程异常: {e}")
            return {
                "has_changed": False,
                "trend": "研判失败",
                "is_abnormal": False,
                "analysis": f"研判异常: {e}",
            }
