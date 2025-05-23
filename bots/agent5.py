# Tool Call is working only in agent 3
# drafter agent to help human save basic draft when user is satisfied with the result

import re
import json
from typing import Annotated, Sequence, Any, TypedDict
from langchain_core.messages import BaseMessage, ToolMessage, SystemMessage, AIMessage, HumanMessage
from langchain_ollama.llms import OllamaLLM
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    iteration: int = 0  # Track iterations




@tool
def add(x: int, y: int) -> int:
    """This is an addition function that adds two numbers together."""
    print(f"TOOL CALL: Adding {x} and {y}")
    return x + y


@tool
def search(query: str) -> str:
    """This is a search function that searches a knowledge base."""
    print(f"TOOL CALL: Searching {query}")
    return f"Summary for {query}: Quantum computing uses quantum-mechanical phenomena to perform computation. (Source: KB)"


@tool
def subtract(a: int, b: int):
    """This is subtraction function that subtracts two numbers together."""
    print(f"TOOL CALL: subtracting {a} and {b}")
    return a - b


@tool
def multiply(a: int, b: int):
    """This is a multiplication function that multiplies two numbers together."""
    print(f"TOOL CALL: multiply {a} and {b}")
    return a * b


tools = [add, search, subtract, multiply]
model = OllamaLLM(model="llama3.2:3b-instruct-fp16", temperature=0.1, tools=tools)


def model_call(state: AgentState) -> Any:
    """Generate response with strict tool guidance"""
    state["iteration"] += 1

    system_prompt = SystemMessage(content="""You MUST use tools for:
- Math (even simple)
- Factual queries

STRICT FORMAT:
Action: tool_name
Action Input: {"param": value}

After tool result, FINAL ANSWER must start with "Answer:"
Example:
Action: add
Action Input: {"x": 5, "y": 3}
Tool Result: 8
Answer: The sum is 8""")

    messages = [system_prompt] + list(state["messages"])

    response = []
    print("\nAssistant: ", end="", flush=True)
    for chunk in model.stream(messages):
        print(chunk, end="", flush=True)
        response.append(chunk)

    return {"messages": [AIMessage(content="".join(response))], "iteration": state["iteration"]}


def should_continue(state: AgentState) -> str:
    """Check for valid tool call or final answer"""
    last_msg = state["messages"][-1].content
    iteration = state["iteration"]

    # Stop conditions
    if iteration >= 3 or "Answer:" in last_msg:
        return "end"

    # Strict tool call detection
    if re.search(r"^Action:\s*(add|search)\s*[\r\n]+Action Input:\s*{.*}", last_msg, re.IGNORECASE | re.MULTILINE):
        return "continue"

    return "end"  # Default to ending


def run_tool(state: AgentState):
    """Execute tools with strict validation"""
    last_msg = state["messages"][-1].content

    # Match exact tool pattern
    match = re.search(
        r"Action:\s*(?P<tool>add|search)\s*[\r\n]+Action Input:\s*(?P<input>{.*?})\s*",
        last_msg,
        re.IGNORECASE | re.DOTALL
    )

    if match:
        tool_name = match.group("tool").lower()
        try:
            tool_input = json.loads(match.group("input"))
            for t in tools:
                if t.name == tool_name:
                    result = t.invoke(tool_input)
                    return {
                        "messages": [ToolMessage(content=str(result), tool_call_id=t.name)],
                        "iteration": state["iteration"]
                    }
        except Exception as e:
            return {
                "messages": [ToolMessage(content=f"Error: {str(e)}", tool_call_id="error")],
                "iteration": state["iteration"]
            }

    # Fallback for numbers in query
    numbers = [int(n) for n in re.findall(r"\d+", last_msg)][:2]
    if len(numbers) == 2:
        result = add.invoke({"x": numbers[0], "y": numbers[1]})
        return {
            "messages": [ToolMessage(content=str(result), tool_call_id="add")],
            "iteration": state["iteration"]
        }

    return {
        "messages": [ToolMessage(content="Invalid tool format", tool_call_id="error")],
        "iteration": state["iteration"]
    }


# Build workflow with iteration tracking
workflow = StateGraph(AgentState)
workflow.add_node("agent", model_call)
workflow.add_node("tools", run_tool)
workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {"continue": "tools", "end": END}
)
workflow.add_edge("tools", "agent")

agent = workflow.compile()

# Test cases
print("==== Math Test ====")
response = agent.invoke({
    "messages": [HumanMessage(content="Calculate 17 plus 90 then subtract 4 and provide final answer.")],
    "iteration": 0
})

print ("\n")
print ("\n")
print ("\n")
print ("\n==== Start ====")
print ("\n")

print("\nFinal Answer:", response["messages"][-1].content)
print ("\n==== End ====")
print ("\n")

# print("\n==== Search Test ====")
# response = agent.invoke({
#     "messages": [HumanMessage(content="Explain quantum computing")],
#     "iteration": 0
# })
# print("\nFinal Answer:", response["messages"][-1].content)
