# Objectives
# Learn how to create Tools in LangGraph
# How to create ReAct Graph
# Work with different types of Messages such as ToolMessages
# Test out robustness of our graph
# Aim is to create a robust React agent

# provides additional context without affecting the type itself
from typing import Annotated
# To automatically handle the state updates for sequences such as by adding new messages to a chat history
from typing import Sequence, Any, TypedDict
# The foundational class for all message types in LangGraph
from langchain_core.messages import BaseMessage
# Passes data back to LLM after it calls a tool such as the content
from langchain_core.messages import ToolMessage
# Message for providing instructions to the LLM
from langchain_core.messages import SystemMessage
from langchain_ollama.llms import OllamaLLM
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

# reducer function
# Rules that controls how updates from nodes are combined with the existing state
# Tells us how to merge new data into the current state
# Without a reducer, updates would have replaced the existing value entirely!

# state = {"messages": ["Hi"]}  # Initial state
# update = {"messages": ["Nice to meet you"]}  # Update state
# # without a reducer state would be replaced
# new_state = {"messages": ["Nice to meet you"]}

# state = {"messages": ["Hi"]}  # Initial state
# update = {"messages": ["Nice to meet you"]}  # Update state
# # with a reducer state would be updated
# new_state = {"messages": ["Hi", "Nice to meet you"]}
# # The reducer function is used to combine the new state with the existing state


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
        content="You are a helpful assistant. You can use tools to perform calculations."
    )

    # Create a list with system prompt first, then add all messages from state
    messages = [system_prompt] + list(state["messages"])

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

    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    """This node will check if the conversation should continue"""

    messages = state["messages"]
    last_message = messages[-1]

    # Check if the message is an AI message and has tool_calls attribute
    if hasattr(last_message, "content"):
        # For LangChain's AIMessage format
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"
        # For string content that might contain tool calls
        elif isinstance(last_message.content, str) and "action" in last_message.content.lower():
            return "continue"

    return "end"


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


graph = StateGraph(AgentState)
graph.add_node("our_agent", model_call)

tool_node = ToolNode(tools=tools)
graph.add_node("tools", tool_node)

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
