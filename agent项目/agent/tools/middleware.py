from typing import Callable
from langchain.agents.middleware import AgentState, ModelRequest, before_model, dynamic_prompt, wrap_tool_call
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from utils.logger import logger
from langgraph.runtime import Runtime
from utils.prompt_loader import load_system_prompts, load_report_prompts

@wrap_tool_call
def monitor_tool(
    #请求的数据封装
    request:ToolCallRequest,
    #执行的函数本身
    handler:Callable[[ToolCallRequest],ToolMessage|Command],
)->ToolMessage|Command:
    logger.info(f"[tool monitor]执行工具:{request.tool_call['name']}")
    logger.info(f"[tool monitor]传入参数:{request.tool_call['args']}")

    if request.tool_call['name'] == "get_user_id":
        user_id = request.runtime.context.get("user_id", "unknown")
        return ToolMessage(content=str(user_id), tool_call_id=request.tool_call['id'])

    try:
        result=handler(request)
        logger.info(f"[tool monitor]工具执行结果{request.tool_call['name']}调用成功")

        if request.tool_call['name']=="fill_context_for_report":
            request.runtime.context['report']=True

        return result
    except Exception as e:
        logger.error(f"工具{request.tool_call['name']}调用失败,原因: {str(e)}")
        raise e


@before_model
def log_before_model(
    state: AgentState,
    runtime: Runtime,
):
    logger.info(f"[log_before_model]:即将调用模型,带有{len(state['messages'])}条消息")
    last_msg = state["messages"][-1]
    # content 可能为 None（如 ToolMessage），safe_str 做空值保护
    content = getattr(last_msg, "content", None)
    content_str = str(content) if content is not None else ""
    preview = content_str[:80].strip()
    logger.debug(f"[log_before_model] {type(last_msg)}: {preview}")
    return None


@dynamic_prompt  # 每一次在生成提示词之前,调用此函数
def report_prompt_switch(request:ModelRequest):#动态切换提示词
    is_report=request.runtime.context.get("report",False)
    if is_report:   #是报告生成场景,返回报告生成提示词内容
        return load_report_prompts()
    return load_system_prompts()
