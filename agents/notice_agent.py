"""
=================================================================
  消息提醒 Agent
  职责：根据研判结果生成面向用户的播报消息
        - 数据异动 → 醒目告警风格
        - 无变化   → 正常播报风格
  输入：研判结果 + 当前数据
  输出：格式化通知消息（字符串）
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


# 提醒 Agent 的系统提示词
NOTICE_SYSTEM_PROMPT = """你是一个专业的消息通知专家。

你的任务是根据研判结果生成面向用户的播报消息。

规则：
1. 如果 has_changed 为 true 或 is_abnormal 为 true：
   - 使用告警风格，消息要醒目
   - 必须包含具体的数据变化情况
   - 在消息开头添加 ⚠️ 或 🔔 等提示符号

2. 如果 has_changed 为 false 且 is_abnormal 为 false：
   - 使用正常的播报风格
   - 简洁报告当前数据状态

3. 消息要求：
   - 使用中文
   - 清晰、简洁、信息完整
   - 包含具体数值
   - 不要使用 markdown 格式
   - 限制在 200 字以内

直接输出消息内容，不要添加额外说明。"""


class NoticeAgent:
    """提醒 Agent：生成播报/告警消息"""

    def run(self, judgment: dict, current_data: dict) -> str:
        """
        执行消息生成任务

        参数:
            judgment:     研判结果字典
            current_data: 当前数据字典

        返回:
            格式化后的播报消息字符串
        """
        print(f"\n{'='*50}")
        print(f"  📢【提醒 Agent】正在生成播报消息...")
        print(f"{'='*50}")

        has_changed = judgment.get("has_changed", False)
        is_abnormal = judgment.get("is_abnormal", False)
        is_error = "error" in current_data

        # 如果有错误，直接输出简短的错误消息
        if is_error:
            msg = f"[状态] 当前数据获取异常: {current_data.get('error', '未知错误')}"
            print(f"  📄 {msg}")
            return msg

        # 如果无变化且无异常，可以不用 LLM，直接生成简洁消息
        if not has_changed and not is_abnormal and not is_error:
            msg = self._build_normal_message(current_data)
            print(f"  📄 {msg}")
            return msg

        # 有异动，用 LLM 生成醒目的告警消息
        llm = _get_llm()
        try:
            from langchain.schema import HumanMessage, SystemMessage

            judgment_str = json.dumps(judgment, ensure_ascii=False, indent=2)
            data_str = json.dumps(current_data, ensure_ascii=False, indent=2)

            messages = [
                SystemMessage(content=NOTICE_SYSTEM_PROMPT),
                HumanMessage(
                    content=(
                        f"研判结果：\n{judgment_str}\n\n"
                        f"当前数据：\n{data_str}"
                    )
                ),
            ]

            response = llm.invoke(messages)
            msg = response.content.strip()

            # 清理可能的 markdown 代码块或引号包裹
            if msg.startswith('"') and msg.endswith('"'):
                msg = msg[1:-1]
            if msg.startswith("```") and msg.endswith("```"):
                lines = msg.split("\n")
                msg = "\n".join(lines[1:-1])

            print(f"  📄 {msg}")
            return msg

        except Exception as e:
            print(f"  ⚠️  消息生成异常，使用默认格式: {e}")
            msg = self._build_fallback_message(judgment, current_data)
            print(f"  📄 {msg}")
            return msg

    # ----------------------------------------------------------
    #  辅助方法：无变化时的普通播报
    # ----------------------------------------------------------
    def _build_normal_message(self, data: dict) -> str:
        """生成普通播报消息"""
        parts = ["📊 当前数据播报"]
        for key, value in data.items():
            if key != "error":
                parts.append(f"{key}: {value}")
        return " | ".join(parts)

    # ----------------------------------------------------------
    #  辅助方法：LLM 异常时的降级消息
    # ----------------------------------------------------------
    def _build_fallback_message(self, judgment: dict, data: dict) -> str:
        """生成降级版的告警消息"""
        lines = ["🔔⚠️ 数据异动告警 ⚠️🔔"]
        trend = judgment.get("trend", "未知")
        analysis = judgment.get("analysis", "")
        lines.append(f"趋势: {trend}")
        if analysis:
            lines.append(f"说明: {analysis}")
        lines.append("当前数据:")
        for key, value in data.items():
            if key != "error":
                lines.append(f"  {key}: {value}")
        return "\n".join(lines)
