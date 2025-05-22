# Objectives
# Implement conditional logic to route the flow of data to different nodes
# Use START and END nodes to manage entry and exit points explicitly.
# Design multiple nodes to perform different operations (addition, subtraction)
# Create a router node to handle decision making and control graph flow
# Main goal is to use "add_conditional_edges()"

from typing import TypedDict, Any
from langgraph.graph import StateGraph, START, END


class AgentState(TypedDict):
    number1: int
    number2: int
    operation1: str
    result1: int
    number3: int
    number4: int
    operation2: str
    result2: int


def router_1(state: AgentState) -> Any:
    """Start node that routes to the next node."""
    state['result1'] = 0
    if state['operation1'] == 'add':
        return "addition_operation_1"
    else:
        return "subtraction_operation_1"


def router_2(state: AgentState) -> Any:
    """Start node that routes to the next node."""
    state['result2'] = 0
    if state['operation2'] == 'add':
        return "addition_operation_2"
    else:
        return "subtraction_operation_2"


def adder_1(state: AgentState) -> AgentState:
    """Node that adds two numbers."""
    state['result1'] = state['number1'] + state['number2']
    return state


def subtractor_1(state: AgentState) -> AgentState:
    """Node that subtracts two numbers."""
    state['result1'] = state['number1'] - state['number2']
    return state


def adder_2(state: AgentState) -> AgentState:
    """Node that adds two numbers."""
    state['result2'] = state['number3'] + state['number4']
    return state


def subtractor_2(state: AgentState) -> AgentState:
    """Node that subtracts two numbers."""
    state['result2'] = state['number3'] - state['number4']
    return state


def end_node(state: AgentState) -> AgentState:
    """End node that finalizes the state."""
    return state


graph = StateGraph(AgentState)

graph.add_node("router1", lambda state: state)
graph.add_node("add_node_1", adder_1)
graph.add_node("subtract_node_1", subtractor_1)

graph.add_node("router2", lambda state: state)
graph.add_node("add_node_2", adder_2)
graph.add_node("subtract_node_2", subtractor_2)

graph.add_edge(START, "router1")  # Connect the start node to the router
graph.add_conditional_edges("router1", router_1, {
    "addition_operation_1": "add_node_1",
    "subtraction_operation_1": "subtract_node_1"
})

graph.add_edge("add_node_1", "router2")  # Add the addition node to the graph
# Add the addition node to the graph
graph.add_edge("subtract_node_1", "router2")
graph.add_conditional_edges("router2", router_2, {
    "addition_operation_2": "add_node_2",
    "subtraction_operation_2": "subtract_node_2"
})

graph.add_edge("add_node_2", END)  # Connect the addition node to the end node
# Connect the subtraction node to the end node
graph.add_edge("subtract_node_2", END)

app = graph.compile()
print("Graph compiled successfully!")
print("Invoking the graph with initial state...")
answer = app.invoke({"number1": 10, "number2": 5, "operation1": "add",
                     "number3": 20, "number4": 5, "operation2": "subtract"})
print(answer['result1'])  # Output: {'result': 15}
print(answer['result2'])  # Output: {'result': 15}
