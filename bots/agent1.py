# Objective
# Define state structure with a list of HumanMessage objects
# Initialize a llama3.2:3b-instruct-fp16 model using LangChain's ollama wrapper
# Sending and handling different types of messages
# Building and compiling the graph of the agent
# Goal is to learn how to integrate LLM in Graphs

from typing import TypedDict, List
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama.llms import OllamaLLM

class AgentState(TypedDict):
    messages: List[HumanMessage]

llm = OllamaLLM(model="llama3.2:3b-instruct-fp16", temperature=0.1)
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("human", "{input}"),
])

def process(state: AgentState) -> AgentState:
    # Process the state and return a response
    response = llm.invoke(prompt.format(input=state["messages"][-1].content))
    print(f"LLM response: {response}")
    return state

graph = StateGraph(AgentState)
graph.add_node("process", process)
graph.add_edge(START, "process")
graph.add_edge("process", END)
agent = graph.compile()

user_input = input("Enter your message: ")
while user_input.lower() != "exit":
    agent.invoke({"messages": [HumanMessage(content=user_input)]})
    user_input = input("Enter your message: ")