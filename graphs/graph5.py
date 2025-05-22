# objective :
# Implement looping logic to route the flow of data back to the nodes
# Create a single conditional edge to handle decision-making and control graph flow
# Aim is to learn Looping logic

from typing import TypedDict, Any
from langgraph.graph import StateGraph, START, END


class AgentState(TypedDict):
    name: str
    result: str


def greeting_node(state: AgentState) -> AgentState:
    """Node that greets the user."""

    # print("Welcome to the interactive agent!")
    state['result'] = f"Hello! How can I assist you today?"
    return state


def ask_name_node(state: AgentState) -> AgentState:
    """Node that asks for the user's name."""

    # print("Let's get to know each other!")
    state['result'] = f"{state['result']} \nNice to meet you, {state['name']}!"
    return state


def farewell_node(state: AgentState) -> AgentState:
    """Node that bids farewell to the user."""
    state['result'] = f"{state['result']} \nGoodbye, {state['name']}! Have a great day!"
    return state


graph = StateGraph(AgentState)
graph.add_node("greeting_node", greeting_node)
graph.add_node("ask_name_node", ask_name_node)
graph.add_node("farewell_node", farewell_node)

graph.set_entry_point("greeting_node")
graph.add_edge("greeting_node", "ask_name_node")
graph.add_edge("ask_name_node", "farewell_node")
graph.set_finish_point("farewell_node")

app = graph.compile()

if __name__ == "__main__":
    name = input("Please enter your name: ")
    state = AgentState(name=name, result="")
    answer = app.invoke(state)

    # Loop back to the greeting node
    while True:

        print(answer['result'])
        if input("Do you want to exit? (yes/no) ").lower() == "yes":
            break

        print("Let's continue!")
        name = input("Please enter your name: ")
        state = AgentState(name=name, result="")
        answer = app.invoke(state)
