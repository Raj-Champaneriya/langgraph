# Objective:
# Define a more complex AgentState.
# Create a processing node that performs operations on list data.
# Setup a LangGraph that processes and outputs computed results.
# Invoke the graph with structured inputs and retrieve outputs.
# Main Goal - Handle multiple inputs

from typing import Dict, TypedDict, List
from langgraph.graph import StateGraph


class AgentState(TypedDict):
    values: List[int]
    name: str
    result: str
    operation: str


def process_values_node(state: AgentState) -> AgentState:
    """This function handles multiple inputs and processes them."""
    if state['operation'] == 'sum':
        state['result'] = f"Hello {state['name']}, the sum of your values is {sum(state['values'])}."
    elif state['operation'] == 'average':
        state['result'] = f"Hello {state['name']}, the average of your values is {sum(state['values']) / len(state['values'])}."
    elif state['operation'] == 'max':
        state['result'] = f"Hello {state['name']}, the maximum of your values is {max(state['values'])}."
    elif state['operation'] == 'min':
        state['result'] = f"Hello {state['name']}, the minimum of your values is {min(state['values'])}."
    else:
        state['result'] = f"Hello {state['name']}, I don't know how to process your values."
    return state


graph = StateGraph(AgentState)
# Add the processing node to the graph
graph.add_node("processor", process_values_node)
graph.set_entry_point("processor")  # Set the start node
graph.set_finish_point("processor")  # Set the end node
app = graph.compile()  # Compile the graph into an executable application
print("Graph compiled successfully!")
png_data = app.get_graph().draw_mermaid_png()
with open("graph2.png", "wb") as f:
    f.write(png_data)
print("Graph saved as graph2.png")
print("Invoking the graph with initial state...")
answer = app.invoke({"values": [1, 2, 3, 4, 5], "name": "Alice", "operation": "max"})
# Output: {'result': 'Hello Alice, the sum of your values is 6.'}
print(answer['result'])
