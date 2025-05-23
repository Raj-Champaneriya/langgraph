# parallel nodes with join node
import asyncio
import time
from typing import TypedDict, Annotated, List
import operator  # Required for operator.add
from langgraph.graph import StateGraph, END

# --- 1. Define the State ---
# The state is a dictionary that will be passed between nodes.


class MyState(TypedDict):
    initial_data: str
    # Use None as initial to show it's populated
    parallel_output_1: Annotated[str, None]
    parallel_output_2: Annotated[str, None]
    final_summary: Annotated[str, None]
    # MODIFIED: Use Annotated with operator.add for the log.
    # This tells LangGraph to use list concatenation (operator.add)
    # to merge concurrent updates to the 'log' field.
    log: Annotated[List[str], operator.add]

# --- 2. Define the Nodes ---
# Nodes are functions or callables that operate on the state.


async def start_node(state: MyState) -> MyState:
    print("--- Executing Start Node ---")
    await asyncio.sleep(0.5)  # Simulate some initial work
    # MODIFIED: Return only this node's contribution to the log
    return {
        "initial_data": "Hello from Start Node!",
        "log": ["Start Node executed"]
    }


async def parallel_task_1(state: MyState) -> MyState:
    print(
        f"--- Executing Parallel Task 1 (input: {state['initial_data']}) ---")
    await asyncio.sleep(2)  # Simulate longer work
    output = f"Task 1 processed: {state['initial_data'].upper()}"
    print("--- Parallel Task 1 Finished ---")
    # MODIFIED: Return only this node's contribution to the log
    return {
        "parallel_output_1": output,
        "log": ["Parallel Task 1 finished"]
    }


async def parallel_task_2(state: MyState) -> MyState:
    print(
        f"--- Executing Parallel Task 2 (input: {state['initial_data']}) ---")
    await asyncio.sleep(1)  # Simulate shorter work
    # Reverse the string
    output = f"Task 2 processed: {state['initial_data'][::-1]}"
    print("--- Parallel Task 2 Finished ---")
    # MODIFIED: Return only this node's contribution to the log
    return {
        "parallel_output_2": output,
        "log": ["Parallel Task 2 finished"]
    }


async def join_node(state: MyState) -> MyState:
    print("--- Executing Join Node ---")
    # You can inspect the accumulated log here
    print(f"Current log in join_node: {state['log']}")
    await asyncio.sleep(0.5)
    summary = (
        f"Join Node Summary:\n"
        f"  Output 1: {state.get('parallel_output_1', 'Not available')}\n"
        f"  Output 2: {state.get('parallel_output_2', 'Not available')}"
    )
    print("--- Join Node Finished ---")
    # MODIFIED: Return only this node's contribution to the log
    return {
        "final_summary": summary,
        "log": ["Join Node finished"]
    }

# --- 3. Define the Graph ---
workflow = StateGraph(MyState)

# Add nodes to the graph
workflow.add_node("start", start_node)
workflow.add_node("task1", parallel_task_1)
workflow.add_node("task2", parallel_task_2)
workflow.add_node("join", join_node)

# --- 4. Define the Edges ---
workflow.set_entry_point("start")
workflow.add_edge("start", "task1")
workflow.add_edge("start", "task2")
workflow.add_edge("task1", "join")
workflow.add_edge("task2", "join")
workflow.add_edge("join", END)

# --- 5. Compile and Run the Graph ---
app = workflow.compile()


async def main():
    print("Starting graph execution...\n")
    start_time = time.time()

    # Initial input for the graph
    # The 'log' will start with this list, and subsequent log entries
    # from nodes will be concatenated to it.
    # If you want the log to start empty from the graph's perspective,
    # you can pass inputs={} and the first node writing to 'log'
    # will effectively start it (e.g., operator.add([], ["First entry"])).
    inputs = {"log": ["Initial log"]}

    final_state = await app.ainvoke(inputs)
    end_time = time.time()

    print("\n--- Graph Execution Finished ---")
    print(f"Total time: {end_time - start_time:.2f} seconds")
    print("\nFinal State:")
    for key, value in final_state.items():
        if key == "log":
            print(f"  {key}:")
            for entry in value:  # type: ignore
                print(f"    - {entry}")
        else:
            print(f"  {key}: {value}")

    task_1_finish_index = -1
    task_2_finish_index = -1
    # Ensure log_entries is treated as a list, even if it's None initially or from bad state
    log_entries: List[str] = final_state.get("log", []) if final_state else []

    # Check if parallel tasks' logs are present and their relative order
    # Note: The exact order of "Parallel Task 1 finished" and "Parallel Task 2 finished"
    # in the final log list depends on the resolution order of concurrent writes by LangGraph's
    # reducer, but both should be present if they ran.
    task_1_msg = "Parallel Task 1 finished"
    task_2_msg = "Parallel Task 2 finished"

    try:
        task_1_finish_index = log_entries.index(task_1_msg)
    except ValueError:
        task_1_finish_index = -1  # Not found

    try:
        task_2_finish_index = log_entries.index(task_2_msg)
    except ValueError:
        task_2_finish_index = -1  # Not found

    if task_1_finish_index != -1 and task_2_finish_index != -1:
        print("\nNote: Both parallel tasks contributed to the log.")
        # Task 2 has a shorter sleep, so its log entry might appear before Task 1's
        # if the reducer preserves some order or if it finishes processing first.
        if task_2_finish_index < task_1_finish_index:
            print(
                "  Task 2's log entry appears before Task 1's in the final combined log.")
        elif task_1_finish_index < task_2_finish_index:
            print(
                "  Task 1's log entry appears before Task 2's in the final combined log.")
        else:
            print(
                "  Tasks' log entries have the same index (should not happen for distinct messages).")
    elif task_1_finish_index != -1:
        print(f"\nNote: Only {task_1_msg} found in log.")
    elif task_2_finish_index != -1:
        print(f"\nNote: Only {task_2_msg} found in log.")
    else:
        print("\nError: Neither parallel task's finishing message was found in the log.")


if __name__ == "__main__":
    asyncio.run(main())


# async def join_node(state: MyState) -> MyState:
#     print("--- Executing Join Node ---")
#     # No asyncio.sleep needed here to wait for task1 and task2

#     # Example: Make an API call using results from parallel tasks
#     # This is "truly awaiting" an operation with an unfixed wait time.
#     api_result = await some_http_client.post(
#         "https://api.example.com/summarize_and_report",
#         data={
#             "info1": state.get('parallel_output_1'),
#             "info2": state.get('parallel_output_2')
#         }
#     )

#     summary = f"Join Node Summary based on API: {api_result}"
#     print("--- Join Node Finished ---")
#     return {
#         "final_summary": summary,
#         "log": ["Join Node finished after API call"]
#     }