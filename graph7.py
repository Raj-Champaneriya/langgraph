# objective :
# Implement looping logic to route the flow of data back to the nodes
# Create a single conditional edge to handle decision-making and control graph flow
# Aim is to learn Looping logic

from typing import TypedDict, Dict, List, Any
from langgraph.graph import StateGraph, START, END
import random


class AgentState(TypedDict):
    name: str
    counter: int
    guesses: List[int]
    number: int
    hint: str
    upper_bound: int
    lower_bound: int


def setup_node(state: AgentState) -> AgentState:
    """Node that setup agent."""
    state['guesses'] = []
    state['upper_bound'] = 20
    state['lower_bound'] = 1
    state['number'] = random.randint(
        state["lower_bound"], state["upper_bound"])
    state['counter'] = 0
    print(f"Hello {state['name']}! I have selected a number.")
    return state


def adjust_bounds_node(state: AgentState) -> AgentState:
    """Node that adjusts the bounds based on the last guess."""
    hint: str = state['hint']
    last_guess: int = state['guesses'][-1] if len(state['guesses']) > 0 else 0
    if hint == "Higher":
        state['lower_bound'] = last_guess + 1
    elif hint == "Lower":
        state['upper_bound'] = last_guess - 1
    print(
        f"\nAdjusted bounds: {state["lower_bound"]} - {state["upper_bound"]}",)
    return state


def guess_node(state: AgentState) -> AgentState:
    """Node that guess a random number."""
    state['guesses'].append(random.randint(
        state["lower_bound"], state["upper_bound"]))
    state['counter'] += 1
    # Get last guess
    last_guess = state['guesses'][-1]
    print(f"\nGuessed number: {last_guess}")
    return state


def hint_node(state: AgentState) -> AgentState:
    """Node that provides a hint based on the guess."""
    last_guess = state['guesses'][-1]
    if last_guess < state['number']:
        state['hint'] = "Higher"
    elif last_guess > state['number']:
        state['hint'] = "Lower"
    else:
        state['hint'] = "Correct"
    print(f"\nHint: {state['hint']}")
    return state


def should_continue_node(state: AgentState) -> Any:
    """Node that decides what to do next."""
    hint: str = state['hint']
    attempts: int = state['counter']

    if hint != "Correct" and attempts < 7:
        return "loop"
    else:
        return "exit"


def farewell_node(state: AgentState) -> AgentState:
    """Node that bids farewell to the user."""
    if state['hint'] == "Correct":
        print(
            f"\nCongratulations {state['name']}! Bot guessed the number {state['number']} in {state['counter']} attempts.")
    else:
        print(
            f"\nSorry {state['name']}! Bot couldn't guess the number {state['number']} in {state['counter']} attempts.")
    return state

# Setup -> adjust_bounds -> guess -> hint -> farewell


graph = StateGraph(AgentState)
graph.add_node("setup_node", setup_node)
graph.add_node("adjust_bounds_node", adjust_bounds_node)
graph.add_node("guess_node", guess_node)
graph.add_node("hint_node", hint_node)
graph.add_node("farewell_node", farewell_node)

graph.set_entry_point("setup_node")
graph.add_edge("setup_node", "adjust_bounds_node")
graph.add_edge("adjust_bounds_node", "guess_node")
graph.add_edge("guess_node", "hint_node")
graph.add_conditional_edges("hint_node", should_continue_node, {
    "loop": "adjust_bounds_node",
    "exit": "farewell_node"
})
graph.set_finish_point("farewell_node")

app = graph.compile()
if __name__ == "__main__":
    name = input("Please enter your name: ")
    state = AgentState(name=name, guesses=[], hint="",
                       upper_bound=0, lower_bound=0, counter=0, number=0)
    print(f"Hey {state['name']}! Let's start:")
    answer = app.invoke(state)
