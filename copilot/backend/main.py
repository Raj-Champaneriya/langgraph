import re
import json
from typing import Annotated, Sequence, Any, TypedDict

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from langchain_core.messages import BaseMessage, ToolMessage, SystemMessage, AIMessage, HumanMessage, AIMessageChunk
from langchain_core.runnables import RunnableConfig # Added
from langchain_ollama.llms import OllamaLLM
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END

# --- Agent State Definition ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

# --- Tool Definitions ---
@tool
async def add(x: int, y: int) -> int:
    """This is an addition function that adds two numbers together."""
    # print(f"TOOL EXECUTING: add(x={x}, y={y})") # Replaced by stream events
    return x + y

@tool
async def subtract(x: int, y: int) -> int:
    """This is an subtraction function that subtracts two numbers from each other."""
    # print(f"TOOL EXECUTING: subtract(x={x}, y={y})") # Replaced by stream events
    return x - y

@tool
async def multiply(x: int, y: int) -> int:
    """This is an multiplication function that multiplies two numbers from each other."""
    # print(f"TOOL EXECUTING: multiply(x={x}, y={y})") # Replaced by stream events
    return x * y

@tool
async def search_orders(query: str) -> str:
    """
    Searches for order details by a specific order identification (e.g., order ID).
    Only use this tool if the user provides a specific order ID or number to search for.
    The query parameter MUST be the order ID.
    """
    # print(f"TOOL EXECUTING: search_orders(query='{query}')") # Replaced by stream events
    mock_db = {
        "ORD12345": "Order details for 'ORD12345': Status: Shipped, Items: 1x SuperWidget, Delivery Est: Tomorrow. (Source: OMS)",
        "XYZ987": "Order details for 'XYZ987': Status: Processing, Items: 1x HyperGadget. (Source: OMS)",
        "TEST001": "Order details for 'TEST001': Status: Delivered, Items: 1x Sample Product. (Source: OMS)",
    }
    if query and query.strip():
        clean_query = query.strip().upper()
        if clean_query in mock_db:
            return mock_db[clean_query]
        else:
            return f"Order ID '{query}' not found. Please verify the order ID and try again. (Source: OMS)"
    else:
        return "No order ID provided for search. Please provide a specific order ID. (Source: OMS)"

tools_list = [add, subtract, multiply, search_orders]

# --- Model Initialization ---
model_name = "llama3.2:3b-instruct-fp16" # doer model
# model_name = "granite3.2:8b" # judge model (as per your objective, but not used in current graph)
ollama_model = None

try:
    ollama_model = OllamaLLM(model=model_name, temperature=0.0)
    ollama_model.invoke("test connection to ensure Ollama is running") # Test connection
    print(f"Successfully connected to Ollama with model {model_name}")
except Exception as e:
    print(f"Error initializing OllamaLLM with {model_name}: {e}")
    print("Please ensure Ollama is running and the model is downloaded (e.g., via 'ollama pull llama3.2:3b-instruct-fp16').")
    print("Exiting due to model initialization failure.")
    exit()

# --- LangGraph Node Definitions ---
SYSTEM_PROMPT_CONTENT = """
You are a precise assistant. You MUST use tools for calculations and order searches when appropriate. Follow ALL rules strictly.

**1. Tool Use Format (MANDATORY):**
   - To use a tool, your *entire response* for that turn MUST be ONLY:
     `Action: [tool_name]`
     `Action Input: {"parameter_name": "value", ...}`
   - Examples:
     - Math (`add`, `subtract`, `multiply`): `Action Input: {"x": number1, "y": number2}`
     - Order Search (`search_orders`): `Action Input: {"query": "ORDER_ID_STRING"}`

**2. After Tool Result (CRITICAL `ToolMessage` Handling - OVERRIDES OTHER RULES):**
   - **If the last message is a `ToolMessage` (a tool has just run):**
     a. **Your ONLY Response: State Tool Output Directly.**
        - Math (`add`, `subtract`, `multiply`): "The result is: [content directly from ToolMessage]."
        - `search_orders` (any outcome: success, 'not found', 'no ID'): Relay the exact content from the `ToolMessage`.
        - Tool Execution Error: "The tool reported an error: [content directly from ToolMessage]."
     b. **THEN STOP. NO NEW ACTIONS.** Your response MUST NOT contain `Action:` or `Action Input:`. Your turn is immediately over. Await new user input.

**3. Using `search_orders` Tool:**
   - Use this tool ONLY if the user provides a specific string that appears to be an order ID (e.g., "ORD12345", "XYZ987"). Use this exact string as the `query` value.
   - **If no specific order ID is given by the user, or their query about an order is vague** (e.g., "Where's my package?", "my recent order"):
     Your ONLY response MUST be to ask for the ID: "To help you with your order, could you please provide the specific order ID?" Do NOT guess IDs or use `search_orders` without a user-provided ID.

**4. Using Math Tools (`add`, `subtract`, `multiply`):**
   - Use ONLY for specific calculation requests where the user provides ALL necessary numbers. The JSON input MUST use `x` and `y` as parameter names.

**5. General Conduct & Unsupported Actions:**
   - **One Task First:** If a user's request contains multiple distinct tasks, address only the first clear and actionable one in your immediate response.
   - **No Tool For Chat:** For simple greetings, acknowledgments, or general questions where no specific tool is needed or applicable, respond politely without invoking any tools.
   - **Unavailable Tools/Operations:** If the user asks for an operation for which you do not have a tool (this includes division, square root, or any capabilities beyond `add`, `subtract`, `multiply`, `search_orders`):
     Your ONLY response MUST be: "I'm sorry, I cannot perform that action as I don't have the required tool." Do NOT attempt to call a non-existent tool or guess.
   - **Clarity is Key:** Only use a tool if the request is specific, clear, and all necessary inputs are directly user-provided (unless Rule 3 explicitly directs you to ask for a missing order ID).
"""

async def model_call_node(state: AgentState, config: RunnableConfig) -> Any:
    # print("\n--- AGENT (LLM) TURN ---") # Replaced by stream events
    system_prompt = SystemMessage(content=SYSTEM_PROMPT_CONTENT)
    messages_for_llm = [system_prompt] + list(state["messages"])

    # The ollama_model.astream() will be picked up by astream_events
    # This node's primary job is to prepare input and return the AIMessage for state update
    response_content = ""
    async for chunk in ollama_model.astream(messages_for_llm, config=config):
        response_content += chunk
    
    return {"messages": [AIMessage(content=response_content)]}

def should_continue_node(state: AgentState) -> str:
    # print("\n--- DECISION: SHOULD CONTINUE? ---") # Replaced by stream events
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage):
        # print("Decision: Last message is not an AIMessage. Ending.")
        return "end_conversation" # Use a more descriptive name for clarity

    content = last_message.content
    if "Action:" in content and "Action Input:" in content:
        action_match = re.search(r"Action: (\w+)", content)
        if action_match:
            tool_name = action_match.group(1).strip()
            if any(t.name == tool_name for t in tools_list):
                # print(f"Decision: Action '{tool_name}' found for a known tool. Continue to tools.")
                return "continue_to_tools"
            else:
                # print(f"Decision: Action '{tool_name}' found, but tool is NOT in known tools list. LLM should have handled. Ending.")
                return "end_conversation" # LLM made a mistake, end to prevent errors
        else:
            # print("Decision: 'Action:' found but could not parse tool name. Ending.")
            return "end_conversation"
    else:
        # print("Decision: No 'Action:' found in AI response. Ending.")
        return "end_conversation"

async def run_tool_node(state: AgentState, config: RunnableConfig) -> Any:
    # print("\n--- TOOL EXECUTION NODE ---") # Replaced by stream events
    last_ai_message = state["messages"][-1]
    content = last_ai_message.content

    action_match = re.search(r"Action: (\w+)", content, re.IGNORECASE)
    input_match = re.search(r"Action Input:.*?({.*?})", content, re.DOTALL | re.IGNORECASE)

    if not (action_match and input_match):
        # This case should ideally be caught by should_continue_node or LLM's adherence to prompt
        error_msg = "Error: Malformed tool call structure from LLM."
        # print(error_msg)
        return {"messages": [ToolMessage(content=error_msg, tool_call_id="error_internal_parsing", name="error_handler")]}

    tool_name = action_match.group(1).strip()
    tool_input_str = input_match.group(1).strip()
    # print(f"Attempting to run tool: '{tool_name}' with input string: '{tool_input_str}'")

    try:
        tool_input_json = json.loads(tool_input_str)
        selected_tool = next((t for t in tools_list if t.name == tool_name), None)

        if selected_tool:
            # The selected_tool.ainvoke will be picked up by astream_events
            result = await selected_tool.ainvoke(tool_input_json, config=config)
            # print(f"TOOL '{selected_tool.name}' EXECUTED. Result: {result}")
            return {"messages": [ToolMessage(content=str(result), name=selected_tool.name, tool_call_id=selected_tool.name)]}
        else:
            error_msg = f"Error: Tool '{tool_name}' not found by tool node (should_continue might have missed this)."
            # print(error_msg)
            return {"messages": [ToolMessage(content=error_msg, name=tool_name, tool_call_id=tool_name)]}

    except json.JSONDecodeError as e:
        error_msg = f"Error: Invalid JSON in tool input for '{tool_name}': {tool_input_str}. Error: {e}"
        # print(error_msg)
        return {"messages": [ToolMessage(content=error_msg, name=tool_name, tool_call_id=tool_name)]}
    except Exception as e:
        error_msg = f"Error during execution of tool '{tool_name}': {str(e)}"
        # print(error_msg)
        return {"messages": [ToolMessage(content=error_msg, name=tool_name, tool_call_id=tool_name)]}

# --- Graph Definition ---
workflow = StateGraph(AgentState)
workflow.add_node("agent", model_call_node)
workflow.add_node("tools_executor", run_tool_node) # Renamed for clarity

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue_node,
    {
        "continue_to_tools": "tools_executor",
        "end_conversation": END
    }
)
workflow.add_edge("tools_executor", "agent")
graph_app = workflow.compile()


# --- FastAPI Application ---
app_fastapi = FastAPI(title="LangGraph Streaming Agent API")

# CORS Middleware
app_fastapi.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows all origins for development
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods
    allow_headers=["*"], # Allows all headers
)

class UserInput(BaseModel):
    text: str
    # session_id: str | None = None # Optional: for multi-turn conversations beyond single request-response

@app_fastapi.post("/chat/stream")
async def chat_stream_endpoint(user_input: UserInput):
    if not ollama_model:
        raise HTTPException(status_code=500, detail="Ollama model not initialized.")

    # Initial state for the graph
    # The `add_messages` annotation on AgentState will handle combining this with history if state was persisted.
    # For a simple request-response stream, we start fresh or load from a session_id if implemented.
    inputs = {"messages": [HumanMessage(content=user_input.text)]}

    async def event_generator():
        try:
            # astream_events provides structured events for LLMs, tools, etc.
            # We are interested in:
            # - "on_llm_stream": Chunks from the LLM.
            # - "on_tool_start": When a tool is about to be called.
            # - "on_tool_end": When a tool has finished and its output.
            # We can also get "on_chat_model_stream" for AIMessageChunk
            async for event in graph_app.astream_events(inputs, version="v1", include_types=["llm", "chat_model", "tool"]):
                kind = event["event"]
                data_to_send = {}

                if kind == "on_chat_model_stream":
                    chunk_content = event["data"]["chunk"].content
                    if chunk_content: # Ensure content is not empty
                        data_to_send = {"type": "llm_chunk", "content": chunk_content}
                elif kind == "on_llm_stream": # Fallback for non-chat models or different chunk types
                    chunk_content = event["data"]["chunk"]
                    if isinstance(chunk_content, str) and chunk_content:
                         data_to_send = {"type": "llm_chunk", "content": chunk_content}
                    # elif hasattr(chunk_content, 'content') and chunk_content.content: # For AIMessageChunk if not caught by on_chat_model_stream
                    #    data_to_send = {"type": "llm_chunk", "content": chunk_content.content}
                elif kind == "on_tool_start":
                    data_to_send = {
                        "type": "tool_start",
                        "name": event["name"], # Tool name
                        "input": event["data"].get("input")
                    }
                elif kind == "on_tool_end":
                    output = event["data"].get("output")
                    # Ensure output is serializable
                    if not isinstance(output, (dict, list, str, int, float, bool, type(None))):
                        output = str(output)
                    data_to_send = {
                        "type": "tool_end",
                        "name": event["name"], # Tool name
                        "output": output
                    }
                
                if data_to_send:
                    yield f"data: {json.dumps(data_to_send)}\n\n"
            
            # Signal the end of the stream explicitly
            yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"

        except Exception as e:
            print(f"Error during stream generation: {e}") # Log server-side
            error_payload = {"type": "error", "detail": "An error occurred while processing your request."}
            # For more detailed client-side error, you might send str(e) but be careful with sensitive info
            if isinstance(e, HTTPException):
                error_payload = {"type": "error", "detail": e.detail, "status_code": e.status_code}
            
            yield f"data: {json.dumps(error_payload)}\n\n"


    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    # Note: The test_prompts and run_test_suite are for local command-line testing.
    # They are not directly used by the FastAPI service but can be run separately if needed.
    # For running the FastAPI server:
    uvicorn.run(app_fastapi, host="0.0.0.0", port=8000)