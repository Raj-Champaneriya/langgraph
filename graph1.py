# Objectives:
# Understand & Define AgentState structure
# Create simple node functions to process and update state
# Set up a basic LangGraph structure
# Compile and invoke a LangGraph graph
# Understand how data flows through a single-node in LangGraph

# Start Point -> Node -> End Point

from typing import Dict, TypedDict
# framework that helps you design and manage the flow of tasks in your application using a graph structure
from langgraph.graph import StateGraph
from IPython.display import Image, display

# AgentState is shared data structure that keeps track of information as your application runs


class AgentState(TypedDict):  # Our State schema
    message: str


def greeting_node(state: AgentState) -> AgentState:
    # docString is important
    """Simple node that adds a greeting message to the state."""

    state['message'] = f"Hello {state["message"]}, how is your day?"
    return state


graph = StateGraph(AgentState)
graph.add_node("greeter", greeting_node)  # Add the greeting node to the graph
graph.set_entry_point("greeter")  # Set the start node
graph.set_finish_point("greeter")  # Set the end node
app = graph.compile()  # Compile the graph into an executable application

# Run the application with an initial state
initial_state = AgentState(message="John")
#result = app.run(initial_state)
#print(result)  # Output: {'message': 'Hello John, how is your day?'} 
png_data = app.get_graph().draw_mermaid_png()
with open("graph1.png", "wb") as f:
    f.write(png_data)
print("Graph saved as graph.png")