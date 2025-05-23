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


tools = [add, subtract]
model_name = "llama3.2:3b-instruct-fp16"
try:
    # Using temperature=0.0 for more deterministic tool use and responses
    # tools=tools in constructor is mostly a hint for some models; actual tool use here relies on string parsing
    model = OllamaLLM(model=model_name, temperature=0.0)
    model.invoke("test connection") # A quick check to see if the model is accessible
    print(f"Successfully connected to Ollama with model {model_name}")
except Exception as e:
    print(f"Error initializing OllamaLLM with {model_name}: {e}")
    print("Please ensure Ollama is running and the model 'llama3.2:3b-instruct-fp16' is downloaded (e.g., via 'ollama pull llama3.2:3b-instruct-fp16').")
    print("Exiting due to model initialization failure.")
    exit()


def model_call(state: AgentState) -> Any:
    """This node will invoke the LLM to decide the next action or respond."""
    print("\n--- AGENT (LLM) TURN ---")
    system_prompt_content = """You are a helpful assistant that MUST use tools to solve math problems.

IMPORTANT RULES:
1. For ANY math calculation, even simple ones, you MUST use the appropriate tool (add, subtract).
2. DO NOT calculate answers yourself - always use tools for calculations.
3. When calling a tool, use EXACTLY this format:
   Action: tool_name
   Action Input: {"param1": value1, "param2": value2}
   For example:
   Action: add
   Action Input: {"x": 5, "y": 3}

4. Interpreting Tool Results:
   When you receive a `ToolMessage` after calling a tool:
   - If the `ToolMessage` contains a numerical result (e.g., "12", "579"), this is the successful outcome of the calculation.
   - You MUST present this result clearly to the user. For example, if the user asked "What is 34 minus 22?" and you called `subtract` and received a `ToolMessage` with content "12", your response should be something like: "34 minus 22 is 12."
   - After presenting the result of a successful calculation, STOP and wait for the user's next request. DO NOT issue another 'Action' for the same calculation.

5. Handling Errors or Unavailable Tools:
   - If you try to call a tool and it returns an error message in the `ToolMessage`, inform the user about the error.
   - If the user asks for an operation for which you do not have a tool (e.g., multiplication, division), you MUST inform the user that you cannot perform that specific action because the required tool is not available. Your available tools are only: add, subtract.
   - Do not make up results if a tool fails or is unavailable.
"""
    system_prompt = SystemMessage(content=system_prompt_content)

    current_messages = [system_prompt]
    for msg in state["messages"]:
        if isinstance(msg, tuple): # Handling the initial input format
            if msg[0] == "user":
                current_messages.append(HumanMessage(content=msg[1]))
            # Other tuple types not expected here after first message
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
        # Should not happen if graph is flowing correctly (agent -> should_continue)
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
                return "end" # LLM hallucinated a tool
        else: # "Action:" was present but malformed
            print("Decision: 'Action:' found but could not parse tool name. Ending.")
            return "end"
    else:
        print("Decision: No 'Action:' found in AI response. Ending.")
        return "end"


def run_tool_node(state: AgentState):
    """Parse and execute the tool call from the LLM's response."""
    print("\n--- TOOL EXECUTION NODE ---")
    # Assumes last message is AIMessage with tool call, validated by should_continue
    last_ai_message = state["messages"][-1]
    content = last_ai_message.content

    action_match = re.search(r"Action: (\w+)", content, re.IGNORECASE)
    input_match = re.search(r"Action Input:.*?({.*?})", content, re.DOTALL | re.IGNORECASE)

    # These should always be found if should_continue routed here, but good to be safe
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
            return {"messages": [ToolMessage(content=str(result), name=selected_tool.name, tool_call_id=selected_tool.name)]} # Added name parameter
        else:
            # This case should ideally be caught by should_continue's check against known tools
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
workflow.add_edge("tools", "agent") # After tools, go back to agent to process result
app = workflow.compile()

# Revised function to manage and print conversation stream
def run_conversation(input_text):
    print(f"\n\n{'='*20} NEW CONVERSATION {'='*20}")
    print(f"User: {input_text}")
    # Initial state for the graph
    inputs = {"messages": [("user", input_text)]}

    # Use app.stream() to get intermediate steps and final output
    # The prints within the nodes will show the flow
    final_state = None
    for output_step in app.stream(inputs, stream_mode="values"):
        # The nodes themselves (model_call, run_tool_node) already print their actions.
        # We can inspect intermediate `output_step` if needed for more detailed debugging.
        # For example, to see the last message added at each stream event:
        # last_msg = output_step['messages'][-1]
        # print(f"DEBUG STREAM: Last message type: {type(last_msg).__name__}, Content: {getattr(last_msg, 'content', 'N/A')}")
        final_state = output_step # Keep track of the last state

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
run_conversation("Subtract 34 from 22. Wait, I mean 34 minus 22.")
run_conversation("What is 123 + 456?")
run_conversation("Can you multiply 4 by 9?")
run_conversation("Hello there!")