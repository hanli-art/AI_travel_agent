# monitor_hook.py
from agents import RunHooks, RunContextWrapper, Agent
from typing import Any

class MonitorHooks(RunHooks):
    """
    自定义监控钩子，用于在控制台打印 Agent 和 Tool 的执行过程
    """

    async def on_agent_start(self, context: RunContextWrapper[Any], agent: Agent) -> None:
        """智能体开始工作时触发"""
        print(f"\n[监控] 🚀 智能体 '{agent.name}' 开始处理任务...")
    async def on_tool_start(self, context: RunContextWrapper[Any], agent: Agent, tool: Any) -> None:
        """工具开始执行时触发"""
        print(f"[监控] 🔧 智能体 '{agent.name}' 准备调用工具: 【{tool.name}】")
        # 注意：具体参数通常在工具函数内部打印更容易获取，这里打印工具名即可

    async def on_tool_end(self, context: RunContextWrapper[Any], agent: Agent, tool: Any, result: str) -> None:
        """工具执行完毕时触发"""
        print(f"[监控] ✅ 工具 【{tool.name}】 执行完毕！")
        print(f"[监控] 📤 工具返回数据: {result}")

    async def on_agent_end(self, context: RunContextWrapper[Any], agent: Agent, output: Any) -> None:
        """智能体完成任务时触发"""
        print(f"[监控] 🏁 智能体 '{agent.name}' 任务完成。\n")