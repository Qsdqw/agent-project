from uuid import uuid4

from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessageChunk, HumanMessage, AIMessage

from model.factory import get_chat_model
from utils.prompt_loader import load_system_prompts
from agent.tools.middleware import monitor_tool, log_before_model, report_prompt_switch
from agent.tools.agent_tools import (
    rag_summarize, get_weather, get_user_location, get_user_id,
    get_current_month, fetch_external_data, fill_context_for_report,
)


class ReactAgent:
    def __init__(self):
        self.memory = MemorySaver()
        self.agent = create_agent(
            model=get_chat_model(),
            system_prompt=load_system_prompts(),
            tools=[rag_summarize, get_weather, get_user_location, get_user_id,
                   get_current_month, fetch_external_data, fill_context_for_report],
            middleware=[monitor_tool, log_before_model, report_prompt_switch],
            checkpointer=self.memory
        )

    def restore_from_messages(self, messages: list[dict], thread_id: str):
        langchain_messages = []
        for m in messages:
            if m["role"] == "user":
                langchain_messages.append(HumanMessage(content=m["content"]))
            elif m["role"] == "assistant":
                langchain_messages.append(AIMessage(content=m["content"]))

        config = {"configurable": {"thread_id": thread_id}}
        self.agent.update_state(config, {"messages": langchain_messages})

    def execute_stream(self, query: str, thread_id: str = None, user_id: int = None):
        if thread_id is None:
            thread_id = str(uuid4())

        input_dict = {
            "messages": [
                {"role": "user", "content": query},
            ]
        }
        config = {"configurable": {"thread_id": thread_id}}

        for chunk in self.agent.stream(
            input_dict,
            stream_mode="messages",
            config=config,
            context={"report": False, "user_id": user_id}
        ):
            msg, meta = chunk
            if isinstance(msg, AIMessageChunk) and msg.content and not msg.tool_calls:
                yield msg.content


if __name__ == "__main__":
    agent = ReactAgent()
    tid = str(uuid4())
    for token in agent.execute_stream("扫地机器人在我所在的地区气温下如何保养", thread_id=tid):
        print(token, end="", flush=True)