# Objective:
# Create multiple nodes that sequentially process data & update different parts of state
# Connect Nodes together in a graph
# Invoke the graph and see how the state is transformed step-by-step
# Main Objective - Handle multiple nodes
from typing import TypedDict
from langgraph.graph import StateGraph


class AgentState(TypedDict):
    name: str
    age: str
    skills: list[str]
    final: str


def first_node(state: AgentState) -> AgentState:
    """This is the first node of our sequence."""
    state['final'] = f"Hello {state['name']},"
    return state


def second_node(state: AgentState) -> AgentState:
    """This is the second node of our sequence."""
    state['final'] += f" you are {state['age']} years old."
    return state


def third_node(state: AgentState) -> AgentState:
    """This is the third node of our sequence."""
    state['final'] += f" Have a great day and use {", ".join(state['skills'])} to your advantage!"
    return state


graph = StateGraph(AgentState)
# Add the nodes to the graph
graph.add_node("first", first_node)
graph.add_node("second", second_node)
graph.add_node("third", third_node)
graph.set_entry_point("first")  # Set the start node
graph.add_edge("first", "second")  # Connect the first and second nodes
graph.add_edge("second", "third")  # Connect the second and third nodes
graph.set_finish_point("third")  # Set the end node

app = graph.compile()  # Compile the graph into an executable application
print("Graph compiled successfully!")

print("Invoking the graph with initial state...")
answer = app.invoke({"name": "Alice", "age": "30",
                    "skills": ["Python", "Java", "Machine Learning"]})
# Output: {'final': 'Hello Alice, you are 30 years old. Have a great day!'}
print(answer['final'])
