# Objectives
# Use different message types - HumanMessage and AIMessage
# Maintain a full conversation history using both message types
# Use a different LLM model - "llama3.2:3b-instruct-fp16"
# Create a sophisticated conversation flow
# The goal is to create a form of memory for our agent (In-Memory)

import os
from typing import TypedDict, List, Union
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langchain_ollama.llms import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage

# Define ANSI color codes
COLORS = {
    "RESET": "\033[0m",
    "RED": "\033[31m",
    "GREEN": "\033[32m",
    "YELLOW": "\033[33m",
    "BLUE": "\033[34m",
    "MAGENTA": "\033[35m",
    "CYAN": "\033[36m",
    "WHITE": "\033[37m"
}


class AgentState(TypedDict):
    messages: List[Union[HumanMessage, AIMessage]]


llm = OllamaLLM(model="llama3.2:3b-instruct-fp16", temperature=0.1)


def process(state: AgentState) -> AgentState:
    """This node will solve the request you input"""
    response = llm.invoke(state["messages"])
    print(f"LLM response: {COLORS['GREEN']}{response}{COLORS['RESET']}")
    state["messages"].append(AIMessage(content=response))
    print(f"Conversation history: {COLORS['BLUE']}{state['messages']}{COLORS['RESET']}")
    return state


graph = StateGraph(AgentState)
graph.add_node("process", process)
graph.add_edge(START, "process")
graph.add_edge("process", END)
agent = graph.compile()

conversation_history: List[Union[HumanMessage, AIMessage]] = []

# Initialize the conversation with a system message
system_message = SystemMessage(content="You are a helpful assistant.")
agent.invoke({"messages": [system_message]})
user_input = input(f"{COLORS['YELLOW']}Enter your message: {COLORS['RESET']}")
while user_input.lower() != "exit":
    conversation_history.append(HumanMessage(content=user_input))

    # Append the user input as a HumanMessage
    result = agent.invoke({"messages": conversation_history})
    conversation_history = result["messages"]
    user_input = input("Enter your message: ")

with open("conversation_history.txt", "w") as f:
    for message in conversation_history:
        speaker = "User" if isinstance(message, HumanMessage) else "AI"
        f.write(f"{speaker}:{message.content}\n")

print("Conversation history saved to conversation_history.txt file.")
