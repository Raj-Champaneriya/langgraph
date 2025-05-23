# Objectives
# Use different message types - HumanMessage and AIMessage
# Maintain a full conversation history using both message types
# Use a different LLM model - "llama3.2:3b-instruct-fp16"
# Create a sophisticated conversation flow
# The goal is to create a form of memory for our agent (In-Memory) & Streaming interaction

import os
import sys
import time
from typing import TypedDict, List, Union
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langchain_ollama.llms import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate

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
    messages: List[Union[HumanMessage, AIMessage, SystemMessage]]


llm = OllamaLLM(model="llama3.2:3b-instruct-fp16", temperature=0.1, streaming=True)


def process(state: AgentState) -> AgentState:
    """This node will solve the request you input"""
    
    print(f"{COLORS['YELLOW']}Generating response...{COLORS['RESET']}")

    # Stream response token-by-token
    response_stream = llm.stream(state["messages"])
    response = ""
    print(f"{COLORS['GREEN']}AI: ", end="", flush=True)
    for token in response_stream:
        print(token, end="", flush=True)
        response += token
    print(COLORS['RESET'])  # Reset color after response
    
    state["messages"].append(AIMessage(content=response))
    
    print("--" * 50)
    print(" " * 50)
    print(f"{COLORS['CYAN']}Conversation history: {COLORS['RESET']}")
    for msg in state["messages"]:
        if isinstance(msg, HumanMessage):
            print(f"{COLORS['GREEN']}User: {msg.content}{COLORS['RESET']}")
        elif isinstance(msg, AIMessage):
            print(f"{COLORS['MAGENTA']}AI: {msg.content}{COLORS['RESET']}")
        elif isinstance(msg, SystemMessage):
            print(f"{COLORS['BLUE']}System: {msg.content}{COLORS['RESET']}")
    
    return state


graph = StateGraph(AgentState)
graph.add_node("process", process)
graph.add_edge(START, "process")
graph.add_edge("process", END)
agent = graph.compile()

# Initialize conversation history with a system message
conversation_history: List[Union[HumanMessage, AIMessage, SystemMessage]] = [
    SystemMessage(content="You are a helpful assistant.")
]

# Interactive loop
try:
    while True:
        user_input = input(f"\n{COLORS['YELLOW']}Enter your message (type 'exit' to quit): {COLORS['RESET']}")
        if user_input.lower() == "exit":
            break

        conversation_history.append(HumanMessage(content=user_input))

        # Invoke the agent with current conversation history
        result = agent.invoke({"messages": conversation_history})
        conversation_history = result["messages"]

except KeyboardInterrupt:
    print("\nExiting conversation...")

# Save conversation history to file
with open("conversation_history.txt", "w") as f:
    for message in conversation_history:
        speaker = "User" if isinstance(message, HumanMessage) else "AI" if isinstance(message, AIMessage) else "System"
        f.write(f"{speaker}: {message.content}\n")

print(f"{COLORS['GREEN']}Conversation history saved to conversation_history.txt{COLORS['RESET']}")
