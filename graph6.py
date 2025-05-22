# objective :
# Implement looping logic to route the flow of data back to the nodes
# Create a single conditional edge to handle decision-making and control graph flow
# Aim is to learn Looping logic

from typing import TypedDict, Dict, List, Any
from langgraph.graph import StateGraph, START, END
import random

class AgentState(TypedDict):
    name: str
    number: List[int]
    counter: int
    result: str
    
def greeting_node(state: AgentState) -> AgentState:
    """Node that greets the user."""
    state['number'] = []
    state['counter'] = 0
    return state

def random_node(state: AgentState) -> AgentState:
    """Node that generates a random number."""
    state['number'].append(random.randint(1, 10))
    state['counter'] += 1
    state['result'] = f"{state['result']}\nGenerated number: {state['number'][-1]}"
    return state

def should_continue_node(state: AgentState) -> Any:
    """Node that decides what to do next."""
    if state['counter'] < 5:
        return "loop"
    else:
        return "exit"

# greetings -> random -> random -> random -> random -> random -> random -> END

graph = StateGraph(AgentState)
graph.add_node("greeting_node", greeting_node)
graph.add_node("random_node", random_node)

graph.set_entry_point("greeting_node")
graph.add_edge("greeting_node", "random_node")
graph.add_conditional_edges("random_node", should_continue_node, {
    "loop": "random_node",
    "exit": END
})

app = graph.compile()
if __name__ == "__main__":
    name = input("Please enter your name: ")
    state = AgentState(name=name, number=[], counter=0, result="")
    answer = app.invoke(state)
    print(f"Hey {state['name']}! Following are generated numbers:")
    print(answer['result'])
