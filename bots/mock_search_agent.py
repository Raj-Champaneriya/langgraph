import os
from typing import List, Dict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel, Field

# 1. Define the Tools
class SearchInput(BaseModel):
    query: str = Field(description="The search query to use")

class SearchTool(BaseTool):
    name: str = "search"
    description: str = "useful for answering questions about current events"
    args_schema: type[BaseModel] = SearchInput

    def _run(self, query: str) -> str:
        print(f"\n\033[32m[TOOL CALLING]\033[0m Searching for: '{query}'")
        mock_results = {
            "What is the capital of France?": "The capital of France is Paris.",
            "Bengaluru weather": "The weather in Bengaluru is currently sunny with a temperature of 30 degrees Celsius.",
            "What is the latest news on AI?": "Recent news highlights advancements in generative AI models and their applications across various industries.",
        }
        return mock_results.get(query, "No relevant search results found.")

    async def _arun(self, query: str) -> str:
        raise NotImplementedError("async not implemented yet")

tools = [SearchTool()]

# 2. Initialize the Chat Model
ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
model = ChatOllama(model="llama3.2:3b-instruct-fp16", base_url=ollama_base_url)

# 3. Define the State for LangGraph
class AgentState(BaseModel):
    messages: List[BaseMessage]
    available_tools: List[BaseTool]
    intermediate_steps: List[tuple] = Field(default_factory=list)

# 4. Create the Agent (Runnable)
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant. You can use tools to answer questions."),
    MessagesPlaceholder(variable_name="messages"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

llm_with_tools = prompt | model.bind_tools(tools)

def format_agent_scratchpad(intermediate_steps: List[tuple]) -> List[BaseMessage]:
    scratchpad_messages = []
    for action_message, observation_message in intermediate_steps:
        scratchpad_messages.append(action_message)
        if isinstance(observation_message, ToolMessage) and hasattr(observation_message, "tool_call_id"):
            scratchpad_messages.append(observation_message)
        else:
            print("Warning: ToolMessage without tool_call_id detected")
            if hasattr(action_message, "tool_calls") and action_message.tool_calls:
                tool_call_id = action_message.tool_calls[0].get('id', 'unknown_id')
                scratchpad_messages.append(ToolMessage(
                    content=str(observation_message.content),
                    tool_call_id=tool_call_id
                ))
            else:
                print("Error: Cannot add ToolMessage without tool_call_id")
    return scratchpad_messages

agent = RunnablePassthrough.assign(
    agent_scratchpad=lambda x: format_agent_scratchpad(x["intermediate_steps"])
) | llm_with_tools

# 5. Define LangGraph workflow nodes
def agent_node(state: AgentState) -> Dict[str, List[BaseMessage]]:
    result = agent.invoke(state.model_dump())
    return {"messages": [result]}

def should_continue(state: AgentState) -> str:
    last_message = state.messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "execute_tools_node"
    else:
        return "end"

def execute_tools_node(state: AgentState) -> Dict[str, List[BaseMessage]]:
    last_message = state.messages[-1]
    tool_outputs = []
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            found_tool = next((tool for tool in state.available_tools if tool.name == tool_call['name']), None)
            if found_tool:
                output = found_tool._run(**tool_call['args'])
                tool_outputs.append(ToolMessage(
                    content=output,
                    tool_call_id=tool_call['id']
                ))
            else:
                tool_outputs.append(ToolMessage(
                    content=f"Tool '{tool_call['name']}' not found.",
                    tool_call_id=tool_call['id']
                ))
    else:
        print("Warning: execute_tools_node called without tool_calls.")
    return {"messages": tool_outputs}

# 6. Build the LangGraph workflow
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("execute_tools_node", execute_tools_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {
    "execute_tools_node": "execute_tools_node",
    "end": END
})
workflow.add_edge("execute_tools_node", "agent")
chain = workflow.compile()

# 7. Run the LangGraph workflow
if __name__ == "__main__":
    question = "What is the weather in Bengaluru?"
    print(f"\n\033[1mUser:\033[0m {question}")

    result = chain.invoke({
        "messages": [HumanMessage(content=question)],
        "available_tools": tools
    })

    print("\n\033[1mFinal Answer:\033[0m")
    for output_message in result["messages"]:
        if isinstance(output_message, AIMessage) and not hasattr(output_message, 'tool_calls'):
            print(output_message.content)