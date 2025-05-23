# Objectives
# Learn how to create Tools in LangGraph
# How to create ReAct Graph
# Work with different types of Messages such as ToolMessages
# Test out robustness of our graph
# Aim is to create a robust React agent

import re
import json
from typing import Annotated, Sequence, Any, TypedDict
from langchain_core.messages import BaseMessage, ToolMessage, SystemMessage, AIMessage, HumanMessage
from langchain_ollama.llms import OllamaLLM
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


@tool
def add(x: int, y: int) -> int:
    """This is an addition function that adds two numbers together."""
    print(f"TOOL CALL : Adding {x} and {y}")
    return x + y


tools = [add]
model = OllamaLLM(model="llama3.2:3b-instruct-fp16",
                  temperature=0.1, tools=tools)


def model_call(state: AgentState) -> Any:
    """This node will solve the request you input"""

    system_prompt = SystemMessage(
        content="""You are a helpful assistant that MUST use tools to solve math problems.

IMPORTANT: For ANY math calculation, even simple ones, you MUST use the appropriate tool.
DO NOT calculate answers yourself - always use tools for calculations.

When using a tool, use EXACTLY this format:
Action: tool_name
Action Input: {"param1": value1, "param2": value2}

For example, to add two numbers:
Action: add
Action Input: {"x": 5, "y": 3}
"""
    )

    # Create a list with system prompt first, then add all messages from state
    messages = [system_prompt] + list(state["messages"])

    # Check if the last message is a user message asking for a calculation
    last_message = messages[-1]
    if isinstance(last_message, HumanMessage) and any(op in last_message.content for op in ['+', 'add', 'sum', 'plus']):
        # Modify the message to explicitly ask for tool use
        messages.append(HumanMessage(content="Please use the add tool to solve this calculation."))

    # Stream response token-by-token
    response_stream = model.stream(messages)
    response = ""
    print()
    print(" - " * 20)
    print("AI: ", end="", flush=True)
    for token in response_stream:
        print(token, end="", flush=True)
        response += token
    print()  # Reset color after response

    return {"messages": [AIMessage(content=response)]}


def should_continue(state: AgentState) -> str:
    """This node will check if the conversation should continue"""
    messages = state["messages"]
    last_message = messages[-1]

    # Check for tool call patterns in the content
    if hasattr(last_message, "content"):
        content = last_message.content
        if isinstance(content, str):
            # Look for the Action: pattern
            if "Action:" in content and "Action Input:" in content:
                return "continue"

    return "end"


def run_tool(state: AgentState):
    """Parse and execute the tool call from the LLM's response"""
    messages = state["messages"]
    last_message = messages[-1]
    content = last_message.content

    # Extract tool name and input
    action_match = re.search(r"Action: (\w+)", content)
    input_match = re.search(r"Action Input: ({.*})", content)

    if action_match and input_match:
        tool_name = action_match.group(1)
        try:
            tool_input = json.loads(input_match.group(1))

            # Find and execute the tool
            for tool in tools:
                if tool.name == tool_name:
                    # Use the invoke method instead of calling the tool directly
                    result = tool.invoke(tool_input)
                    print(f"TOOL CALL : Adding {tool_input.get('x')} and {tool_input.get('y')}")
                    return {"messages": [ToolMessage(content=str(result), tool_call_id=tool.name)]}
        except json.JSONDecodeError:
            return {"messages": [ToolMessage(content="Error: Invalid JSON in tool input", tool_call_id="error")]}

    # If we get here, either there was no tool call or it was invalid
    # Let's extract numbers from the query and try to use the add tool anyway
    numbers = re.findall(r'\d+', content)
    if len(numbers) >= 2:
        x, y = int(numbers[0]), int(numbers[1])
        result = add.invoke({"x": x, "y": y})
        print(f"TOOL CALL : Adding {x} and {y}")
        return {"messages": [ToolMessage(content=str(result), tool_call_id="add")]}

    return {"messages": [ToolMessage(content="No valid tool call found", tool_call_id="error")]}


def print_stream(stream):
    print(f"User: ", end="", flush=True)
    for token in stream:
        # Convert token to string if it's not already
        if hasattr(token, "get"):
            # If token is a dict-like object, extract the relevant part
            if "messages" in token:
                token_text = str(token["messages"][-1].content)
            else:
                token_text = str(token)
        else:
            token_text = str(token)

        print(token_text, end="", flush=True)
    print()  # Reset color after response


# Create the graph
graph = StateGraph(AgentState)
graph.add_node("our_agent", model_call)
graph.add_node("tools", run_tool)  # Use our custom tool runner instead of ToolNode

graph.set_entry_point("our_agent")
graph.add_conditional_edges("our_agent", should_continue, {
    "continue": "tools",
    "end": END
})
graph.add_edge("tools", "our_agent")
graph.add_edge("our_agent", END)

agent = graph.compile()

# Initialize conversation history with a system message
inputs = {"messages": [("user", "Add 34 + 22.")]}
print_stream(agent.stream(inputs, stream_mode="values"))

# Test with another example
print("\n--- New Conversation ---\n")
inputs = {"messages": [("user", "What is 123 + 456?")]}
print_stream(agent.stream(inputs, stream_mode="values"))