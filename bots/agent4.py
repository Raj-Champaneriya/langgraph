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
from langgraph.graph import StateGraph, END  # START is implicitly used


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
    print(
        # Corrected typo from previous version
        f"TOOL EXECUTING: multiply(x={x}, y={y})")
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
        clean_query = query.strip().upper()  # Normalize query
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
    system_prompt_content = """You are a precise assistant that uses tools for calculations and order searches. Your responses MUST strictly follow ALL rules.

**Rule 0: Core Directives**
* **A. Strict Rule Adherence:** You MUST follow all numbered rules and sub-bullets precisely. Deviations are failures.
* **B. One Action Per Turn:** If a user's request implies multiple actions, CHOOSE ONLY ONE to perform for your current turn. Address the most direct or first-mentioned valid action. DO NOT output multiple 'Action:' blocks in one response.
* **C. Conversational Only When No Tool is Needed:** For simple greetings or acknowledgments, respond politely and conversationally. DO NOT invoke any tools unless a clear task requiring a tool is stated.
* **D. Clarity Before Action:** Only decide to use a tool if the user's request is specific, clear, and explicitly requires that tool with ALL necessary inputs already provided by the user (unless Rule 1.C dictates asking for an ID).

**Rule 1: Using `search_orders` Tool**
* **A. Input Requirement:** This tool needs a specific, non-empty order ID string for the 'query' parameter.
* **B. Condition for Use:** Use this tool if the user provides a string that appears to be a specific order ID (e.g., "ORD12345", "XYZ987", "FAKEORDER101"). Attempt to use the provided ID.
* **C. Action if Order ID is Missing or Clearly Vague:**
    * If the user asks about an order (e.g., 'Where's my package?', 'check my shipment') but provides NO string that could be an order ID, OR if their query is explicitly vague (e.g., 'my recent order', 'any active order'),
    * Then your **IMMEDIATE and ONLY response MUST be to ask the user to provide the specific order ID.** Example: "To help you with your order, could you please provide the specific order ID?"
    * **DO NOT GUESS or use generic placeholders if a plausible ID isn't given by the user.**

**Rule 2: Using Math Tools (`add`, `subtract`, `multiply`)**
* Use these tools only when the user requests a calculation and provides the necessary numbers.

**Rule 3: Tool Invocation Format (VERY STRICT)**
* If you decide to call a tool (per Rules 1.B or 2), your response for that turn MUST contain *ONLY* one 'Action:' line and one 'Action Input:' line.
* **ABSOLUTELY NO OTHER TEXT, explanations, or remarks are allowed in this specific tool-calling message.**
* Example (math):
    Action: add
    Action Input: {"x": 5, "y": 3}
* Example (order search with a user-provided ID):
    Action: search_orders
    Action Input: {"query": "USER_PROVIDED_ID_STRING"}

**Rule 4: Responding After a `ToolMessage` (CRITICAL FLOW CONTROL)**
* **A. Check for `ToolMessage`:** If the latest message in the history is a `ToolMessage` (this is the output from a tool you just called):
* **B. Your SOLE TASK is to Present Result:** Your *only* job in your current response is to communicate the content of that `ToolMessage` to the user.
    * Math Tools: Clearly state the numerical result (e.g., "The result of 5 plus 3 is 62.").
    * `search_orders` Tool:
        * If details were found: Present them EXACTLY as provided in the `ToolMessage`.
        * If the `ToolMessage` says 'Order ID ... not found' or 'No order ID provided': Relay this exact information to the user (e.g., "The tool reported: Order ID 'XYZ123' not found. Please verify the order ID and try again.").
* **C. ABSOLUTELY NO NEW ACTIONS:** Your response presenting the tool's result (as per 4.B) MUST NOT contain any "Action:" or "Action Input:" lines. You must simply provide the information and STOP. Do not ask follow-up questions or try to initiate new actions in this specific response. Wait for the user's next input.
* **D. INTEGRITY GUARDRAIL:** Do not invent, infer, or hallucinate ANY information not explicitly in the `ToolMessage`. If a tool was not called for a query (e.g., a second part of a multi-action request that wasn't processed), DO NOT invent a result for it. If the `ToolMessage` is from `search_orders` and says "not found", DO NOT then make unrelated statements (e.g., about division). Stick to the tool's direct output.

**Rule 5: Handling Unavailable Capabilities**
* Your ONLY available tools are: `add`, `subtract`, `multiply`, `search_orders`.
* If the user asks for an operation for which you do not have a tool (e.g., division, square root, currency conversion, weather, date, general questions):
    * Your **ONLY response MUST be to inform the user politely that you cannot perform that action.**
    * **ABSOLUTELY DO NOT attempt to call a non-existent tool** (e.g., do not generate `Action: divide`).
    * Example: "I'm sorry, I cannot perform division as I don't have a division tool."
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
                print(
                    f"Decision: Action '{tool_name}' found for a known tool. Continue to tools.")
                return "continue_to_tools"
            else:
                print(
                    f"Decision: Action '{tool_name}' found, but tool is NOT in known tools list {[t.name for t in tools]}. LLM should have handled this based on prompt. Ending here to prevent error.")
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
    input_match = re.search(
        r"Action Input:.*?({.*?})", content, re.DOTALL | re.IGNORECASE)

    if not (action_match and input_match):
        print("Error: Tool call structure not found, though should_continue passed. This is unexpected.")
        return {"messages": [ToolMessage(content="Error: Malformed tool call structure.", tool_call_id="error_internal_parsing")]}

    tool_name = action_match.group(1).strip()
    tool_input_str = input_match.group(1).strip()
    print(
        f"Attempting to run tool: '{tool_name}' with input string: '{tool_input_str}'")

    try:
        tool_input_json = json.loads(tool_input_str)
        selected_tool = next((t for t in tools if t.name == tool_name), None)

        if selected_tool:
            result = selected_tool.invoke(tool_input_json)
            print(f"TOOL '{selected_tool.name}' EXECUTED. Result: {result}")
            return {"messages": [ToolMessage(content=str(result), name=selected_tool.name, tool_call_id=selected_tool.name)]}
        else:
            print(
                f"Error: Tool '{tool_name}' not found in the available tools list (should_continue might have missed this).")
            return {"messages": [ToolMessage(content=f"Error: Tool '{tool_name}' not found.", name=tool_name, tool_call_id=tool_name)]}

    except json.JSONDecodeError as e:
        print(
            f"Error: Invalid JSON in tool input for '{tool_name}': {tool_input_str}. Error: {e}")
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
    # Initialize final_response_content to a default value
    final_response_content = "No AI response generated or an issue occurred."

    for output_step in app.stream(inputs, stream_mode="values"):
        final_state = output_step

    print("\n--- FINAL RESULT OF GRAPH EXECUTION ---")
    if final_state and final_state['messages']:
        last_message_in_state = final_state['messages'][-1]
        if isinstance(last_message_in_state, AIMessage):
            final_response_content = last_message_in_state.content
            print(f"Final AI Response: {final_response_content}")
        else:
            final_response_content = (
                f"Ended on a non-AIMessage. Last message type: "
                f"{type(last_message_in_state).__name__}, "
                f"Content: {getattr(last_message_in_state, 'content', 'N/A')}"
            )
            print(final_response_content)
    else:
        final_response_content = "No final state or messages found."
        print(final_response_content)
    print(f"{'='*20} END OF CONVERSATION {'='*20}")
    return final_response_content  # <--- ENSURE THIS RETURNS THE CONTENT


def run_test_suite(test_prompts_list: list):
    """
    Runs all test prompts sequentially and prints a summary of results.
    """
    results = []
    print(f"\n\n{'#'*20} STARTING TEST SUITE {'#'*20}")
    print(f"Found {len(test_prompts_list)} test cases.")

    for i, prompt in enumerate(test_prompts_list):
        print(f"\n--- Test Case {i+1}/{len(test_prompts_list)} ---")
        response = run_conversation(prompt)
        results.append({
            "id": i + 1,
            "prompt": prompt,
            "response": response
        })
        # Optional: Add a small delay or a prompt to continue
        # import time
        # time.sleep(0.5) # 0.5-second delay
        # if i < len(test_prompts_list) - 1:
        #     input("Press Enter to run next test case...")

    print(f"\n\n{'#'*20} TEST SUITE SUMMARY {'#'*20}")
    if not results:
        print("No test results to display.")
        return

    for result in results:
        print(f"\n--- Result for Test Case {result['id']} ---")
        print(f"User Prompt: {result['prompt']}")
        print(f"Agent's Final Response: {result['response']}")
        print("-" * 50)

    print(f"\n{'#'*20} END OF TEST SUITE SUMMARY {'#'*20}")


# Your list of test prompts
test_prompts = [
    # --- Math Tool Tests (add, subtract, multiply) ---
    "What is 27 plus 35?",
    "Calculate 250 minus 75.",
    "18 times 4, please.",
    "The sum of 123 and 456.",
    "What is 50 multiplied by 0?",
    "If I have 10 apples and eat 3, how many are left? Use a tool.",
    "Multiply 15 by -2.",

    # --- search_orders Tool Tests (Focus on Guardrails) ---
    # Successful searches
    "Can you find order ORD12345?",
    "I need details for order XYZ987.",
    "Check status for TEST001.",

    # Order Not Found
    "Look up order ID FAKEORDER101.",
    "What's the status of order UNKNOWN99?",

    # User Doesn't Provide Order ID (Agent should ask)
    "Where is my package?",
    "Can you check my recent shipment details?",
    "I want to know about my purchase.",

    # Vague Query + Fake ID (Testing hallucination guardrail)
    "I think my order was MYORDERID000, what's its status?",

    # Attempt to get LLM to bypass asking for ID / Invent ID
    "You should know my most recent order, can you find it for me?",
    "Just search for any active order under my name.",

    # Empty/Invalid Query for Search Tool
    "Search for order: ",

    # --- Unavailable Tools / Operations Not Supported ---
    "What is 300 divided by 15?",
    "Calculate the square root of 144.",
    "What's the current temperature in New York?",
    "Tell me today's date.",

    # --- Conversational Flow & Robustness ---
    "Hello!",
    "Thank you for the information.",
    "That's great, thanks.",
    "I have two numbers, 55 and 11. Figure out what I want.",
    "I'm planning a party and need to budget. What is 125 times 8?",
    "After that long meeting, I need you to find order ORD12345 for me.",
    "Can you add 10 and 5, and also search for order XYZ987?",
]

run_test_suite(test_prompts)
