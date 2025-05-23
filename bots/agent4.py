# react Agent with strict tool usage
# This code implements a stateful agent that uses tools for arithmetic and factual queries.
# It tracks iterations and ensures strict adherence to tool usage format.
# The agent uses a language model to generate responses and validate tool calls.
# It also includes a workflow for managing the agent's state and tool execution.
# Improved search order function to simulate a database lookup or API call.
# Add gaurdrails to ensure the agent does not invent or infer order details.

import re
import json
from typing import Annotated, Sequence, Any, TypedDict
from langchain_core.messages import BaseMessage, ToolMessage, SystemMessage, AIMessage, HumanMessage
from langchain_ollama.llms import OllamaLLM
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END # START is implicitly used

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


@tool
def add(x: int, y: int) -> int:
    """This is an addition function that adds two numbers together."""
    print(f"TOOL EXECUTING: add(x={x}, y={y})")
    return x + y


@tool
def subtract(x: int, y: int) -> int:
    """This is an subtraction function that subtracts two numbers from each other."""
    print(f"TOOL EXECUTING: subtract(x={x}, y={y})")
    return x - y

@tool
def multiply(x: int, y: int) -> int:
    """This is an multiplication function that multiplies two numbers from each other."""
    print(f"TOOL EXECUTING: multiply(x={x}, y={y})") # Corrected typo from previous version
    return x * y

@tool
def search_orders(query: str) -> str:
    """
    Searches for order details by a specific order identification (e.g., order ID).
    Only use this tool if the user provides a specific order ID or number to search for.
    The query parameter MUST be the order ID.
    """
    print(f"TOOL EXECUTING: search_orders(query='{query}')")
    # Simulate a database lookup
    mock_db = {
        "ORD12345": "Order details for 'ORD12345': Status: Shipped, Items: 1x SuperWidget, Delivery Est: Tomorrow. (Source: OMS)",
        "XYZ987": "Order details for 'XYZ987': Status: Processing, Items: 1x HyperGadget. (Source: OMS)",
        "TEST001": "Order details for 'TEST001': Status: Delivered, Items: 1x Sample Product. (Source: OMS)",
    }
    if query and query.strip():
        clean_query = query.strip().upper() # Normalize query
        if clean_query in mock_db:
            return mock_db[clean_query]
        else:
            return f"Order ID '{query}' not found. Please verify the order ID and try again. (Source: OMS)"
    else:
        return "No order ID provided for search. Please provide a specific order ID. (Source: OMS)"


tools = [add, subtract, multiply, search_orders]
model_name = "llama3.2:3b-instruct-fp16"
try:
    model = OllamaLLM(model=model_name, temperature=0.0)
    model.invoke("test connection")
    print(f"Successfully connected to Ollama with model {model_name}")
except Exception as e:
    print(f"Error initializing OllamaLLM with {model_name}: {e}")
    print("Please ensure Ollama is running and the model 'llama3.2:3b-instruct-fp16' is downloaded (e.g., via 'ollama pull llama3.2:3b-instruct-fp16').")
    print("Exiting due to model initialization failure.")
    exit()


def model_call(state: AgentState) -> Any:
    """This node will invoke the LLM to decide the next action or respond."""
    print("\n--- AGENT (LLM) TURN ---")
    system_prompt_content = """You are a helpful assistant that uses tools to perform calculations and search for order information.

IMPORTANT RULES:
1.  Tool Usage:
    * For math calculations, you MUST use the appropriate tool (add, subtract, multiply).
    * For searching order details, you MUST use the `search_orders` tool. This tool requires a specific order ID or number as the 'query'.
    * If the user asks generally about orders without providing an ID (e.g., 'where's my latest order?'), you MUST ask them to provide the specific order ID before attempting to use the `search_orders` tool. Do not try to guess the order ID.

2.  Tool Invocation Format:
    When calling a tool, use EXACTLY this format:
    Action: tool_name
    Action Input: {"param_name": "value"}

    For example (math):
    Action: add
    Action Input: {"x": 5, "y": 3}

    For example (order search):
    Action: search_orders
    Action Input: {"query": "ORD12345"}

3.  Interpreting Tool Results & Responding:
    When you receive a `ToolMessage` after calling a tool:
    * Calculation Tools (add, subtract, multiply): If the `ToolMessage` contains a numerical result (e.g., "12", "579"), this is the successful outcome. Present this result clearly (e.g., "5 plus 3 is 8.").
    * `search_orders` Tool:
        * If the `ToolMessage` contains specific order details (e.g., "Order details for 'ORD12345': Status: Shipped..."), this is a successful search. Present these details EXACTLY as provided by the tool.
        * If the `ToolMessage` indicates the order ID was 'not found' (e.g., "Order ID 'ABCDE' not found..."), inform the user that the specific order ID was not found and suggest they check the ID.
        * If the `ToolMessage` indicates 'No order ID provided', inform the user that you need a specific order ID to perform the search.
        * **CRUCIAL SEARCH GUARDRAIL: For `search_orders`, you MUST NOT add, infer, or invent ANY order details (like status, items, delivery dates, or existence of an order) that are not explicitly stated in the `ToolMessage`. If the tool provides limited information, present only that limited information. If the tool says 'not found', do not suggest the order might exist elsewhere or try to find it in other ways.**
    * After presenting the result of a successful tool use (calculation or search) or informing about a 'not found' status from search, STOP and wait for the user's next request. DO NOT issue another 'Action' for the same completed task.

4.  Handling Errors or Unavailable Tools:
    * If a tool call results in a `ToolMessage` containing an error message (distinct from a 'not found' message from `search_orders`), inform the user about the error.
    * If the user asks for an operation for which you do not have a tool (e.g., division, weather lookup), you MUST inform the user that you cannot perform that specific action because the required tool is not available.
    * Your available tools are: add, subtract, multiply, search_orders.
    * Do not make up results if a tool fails or is unavailable.
"""
    system_prompt = SystemMessage(content=system_prompt_content)

    current_messages = [system_prompt]
    for msg in state["messages"]:
        if isinstance(msg, tuple):
            if msg[0] == "user":
                current_messages.append(HumanMessage(content=msg[1]))
        else:
            current_messages.append(msg)

    response_stream = model.stream(current_messages)
    response_content = ""
    print("AI: ", end="", flush=True)
    for token in response_stream:
        print(token, end="", flush=True)
        response_content += token
    print()

    return {"messages": [AIMessage(content=response_content)]}


def should_continue(state: AgentState) -> str:
    """This node will check if the conversation should continue to tools or end."""
    print("\n--- DECISION: SHOULD CONTINUE? ---")
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage):
        print("Decision: Last message is not an AIMessage. Ending.")
        return "end"

    content = last_message.content
    if "Action:" in content and "Action Input:" in content:
        action_match = re.search(r"Action: (\w+)", content)
        if action_match:
            tool_name = action_match.group(1).strip()
            if any(t.name == tool_name for t in tools):
                print(f"Decision: Action '{tool_name}' found for a known tool. Continue to tools.")
                return "continue_to_tools"
            else:
                print(f"Decision: Action '{tool_name}' found, but tool is NOT in known tools list { [t.name for t in tools] }. LLM should have handled this based on prompt. Ending here to prevent error.")
                return "end"
        else:
            print("Decision: 'Action:' found but could not parse tool name. Ending.")
            return "end"
    else:
        print("Decision: No 'Action:' found in AI response. Ending.")
        return "end"


def run_tool_node(state: AgentState):
    """Parse and execute the tool call from the LLM's response."""
    print("\n--- TOOL EXECUTION NODE ---")
    last_ai_message = state["messages"][-1]
    content = last_ai_message.content

    action_match = re.search(r"Action: (\w+)", content, re.IGNORECASE)
    input_match = re.search(r"Action Input:.*?({.*?})", content, re.DOTALL | re.IGNORECASE)

    if not (action_match and input_match):
        print("Error: Tool call structure not found, though should_continue passed. This is unexpected.")
        return {"messages": [ToolMessage(content="Error: Malformed tool call structure.", tool_call_id="error_internal_parsing")]}

    tool_name = action_match.group(1).strip()
    tool_input_str = input_match.group(1).strip()
    print(f"Attempting to run tool: '{tool_name}' with input string: '{tool_input_str}'")

    try:
        tool_input_json = json.loads(tool_input_str)
        selected_tool = next((t for t in tools if t.name == tool_name), None)

        if selected_tool:
            result = selected_tool.invoke(tool_input_json)
            print(f"TOOL '{selected_tool.name}' EXECUTED. Result: {result}")
            return {"messages": [ToolMessage(content=str(result), name=selected_tool.name, tool_call_id=selected_tool.name)]}
        else:
            print(f"Error: Tool '{tool_name}' not found in the available tools list (should_continue might have missed this).")
            return {"messages": [ToolMessage(content=f"Error: Tool '{tool_name}' not found.", name=tool_name, tool_call_id=tool_name)]}

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in tool input for '{tool_name}': {tool_input_str}. Error: {e}")
        return {"messages": [ToolMessage(content=f"Error: Invalid JSON in tool input: {tool_input_str}", name=tool_name, tool_call_id=tool_name)]}
    except Exception as e:
        print(f"Error executing tool '{tool_name}': {e}")
        return {"messages": [ToolMessage(content=f"Error during execution of tool '{tool_name}': {str(e)}", name=tool_name, tool_call_id=tool_name)]}

# Create the graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", model_call)
workflow.add_node("tools", run_tool_node)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue_to_tools": "tools",
        "end": END
    }
)
workflow.add_edge("tools", "agent")
app = workflow.compile()

def run_conversation(input_text):
    print(f"\n\n{'='*20} NEW CONVERSATION {'='*20}")
    print(f"User: {input_text}")
    inputs = {"messages": [("user", input_text)]}
    final_state = None
    for output_step in app.stream(inputs, stream_mode="values"):
        final_state = output_step

    print("\n--- FINAL RESULT OF GRAPH EXECUTION ---")
    if final_state and final_state['messages']:
        last_message_in_state = final_state['messages'][-1]
        if isinstance(last_message_in_state, AIMessage):
            print(f"Final AI Response: {last_message_in_state.content}")
        else:
            print(f"Ended on a non-AIMessage. Last message type: {type(last_message_in_state).__name__}, Content: {getattr(last_message_in_state, 'content', 'N/A')}")
    else:
        print("No final state or messages found.")
    print(f"{'='*20} END OF CONVERSATION {'='*20}")


# --- Test Cases ---
run_conversation("Subtract 95 from 150. Wait, I mean 150 minus 95.")
run_conversation("What is 36 plus 45?")
run_conversation("Can you multiply 9 by 2?")
run_conversation("Hello there!")
# Test cases for search functionality
run_conversation("Please find my order ORD12345.") # Expected: Found
run_conversation("What about order XYZ987?")     # Expected: Found
run_conversation("Search for order FAKEID000.") # Expected: Not Found
run_conversation("Where is my order?")          # Expected: AI asks for order ID
run_conversation("Can you check the status of order TEST001") # Expected: Found
run_conversation("Tell me about order ") # Expected: AI asks for order ID or tool returns 'No order ID provided' message