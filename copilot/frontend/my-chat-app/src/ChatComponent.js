// src/ChatComponent.js
import { useEffect, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid"; // For unique keys

function ChatComponent() {
  const [userInput, setUserInput] = useState("");
  const [messages, setMessages] = useState([]); // { id: string, type: 'user' | 'ai' | 'tool_activity', content: any }
  const [isStreaming, setIsStreaming] = useState(false);
  const currentAiMessageRef = useRef(""); // To accumulate AI chunks

  const scrollToBottom = () => {
    const chatView = document.getElementById("chat-view");
    if (chatView) {
      chatView.scrollTop = chatView.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!userInput.trim() || isStreaming) return;

    setIsStreaming(true);
    const newUserMessage = { id: uuidv4(), type: "user", content: userInput };
    setMessages((prev) => [...prev, newUserMessage]);
    setUserInput("");
    currentAiMessageRef.current = ""; // Reset current AI message accumulator

    try {
      const response = await fetch("http://localhost:8000/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify({ text: userInput }),
      });

      if (!response.ok) {
        const errorData = await response.json(); // Or .text() if not JSON
        console.error("API Error:", errorData);
        setMessages((prev) => [
          ...prev,
          {
            id: uuidv4(),
            type: "ai",
            content: `Error: ${errorData.detail || "Failed to get response"}`,
          },
        ]);
        setIsStreaming(false);
        return;
      }

      if (!response.body) {
        setIsStreaming(false);
        return;
      }

      const reader = response.body
        .pipeThrough(new TextDecoderStream())
        .getReader();

      // Add a placeholder for the AI message that will be populated
      const aiMessageId = uuidv4();
      setMessages((prev) => [
        ...prev,
        { id: aiMessageId, type: "ai", content: "..." },
      ]);

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          // Final update for the current AI message, if any residual content
          if (currentAiMessageRef.current.trim()) {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessageId
                  ? { ...msg, content: currentAiMessageRef.current }
                  : msg
              )
            );
          } else if (
            // If no LLM chunks came for this AI message, it might be an empty response or just tool use
            messages.find(
              (msg) => msg.id === aiMessageId && msg.content === "..."
            )
          ) {
            // Remove placeholder if no content was streamed for it.
            // Or replace with a specific message like "Agent processing complete."
            // This depends on how you want to handle turns that only result in tool use then end.
            setMessages((prev) =>
              prev.map(
                (msg) =>
                  msg.id === aiMessageId
                    ? { ...msg, content: "Agent finished." }
                    : msg // Or remove
              )
            );
          }
          break;
        }

        // Process Server-Sent Events (each value chunk can have multiple events)
        const eventLines = value.split("\n\n");
        eventLines.forEach((line) => {
          if (line.startsWith("data: ")) {
            const jsonString = line.substring(6); // Remove 'data: '
            try {
              const eventData = JSON.parse(jsonString);

              if (eventData.type === "llm_chunk") {
                currentAiMessageRef.current += eventData.content;
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === aiMessageId
                      ? { ...msg, content: currentAiMessageRef.current }
                      : msg
                  )
                );
              } else if (eventData.type === "tool_start") {
                setMessages((prev) => [
                  ...prev,
                  {
                    id: uuidv4(),
                    type: "tool_activity",
                    content: `Tool Starting: ${
                      eventData.name
                    } with input ${JSON.stringify(eventData.input)}`,
                  },
                ]);
              } else if (eventData.type === "tool_end") {
                setMessages((prev) => [
                  ...prev,
                  {
                    id: uuidv4(),
                    type: "tool_activity",
                    content: `Tool Finished: ${
                      eventData.name
                    } - Output: ${JSON.stringify(eventData.output)}`,
                  },
                ]);
              } else if (eventData.type === "stream_end") {
                console.log("Stream ended by server event.");
                // The main 'done' condition of the reader loop will handle finalization.
              } else if (eventData.type === "error") {
                console.error("Stream Error Event:", eventData.detail);
                setMessages((prev) => [
                  ...prev,
                  {
                    id: uuidv4(),
                    type: "ai", // Show error as an AI message
                    content: `Stream Error: ${eventData.detail}`,
                  },
                ]);
                // Potentially stop processing further events if it's a fatal stream error
              }
            } catch (e) {
              console.error(
                "Failed to parse JSON from stream data:",
                jsonString,
                e
              );
            }
          }
        });
      }
    } catch (error) {
      console.error("Fetch API or streaming failed:", error);
      setMessages((prev) => [
        ...prev,
        {
          id: uuidv4(),
          type: "ai",
          content: `Error: Could not connect to the server or stream failed.`,
        },
      ]);
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        fontFamily: "Arial, sans-serif",
        maxWidth: "700px",
        margin: "0 auto",
        border: "1px solid #ccc",
      }}
    >
      <h2>LangGraph Agent Chat (Streaming)</h2>
      <div
        id="chat-view"
        style={{
          flexGrow: 1,
          overflowY: "auto",
          padding: "10px",
          borderBottom: "1px solid #ccc",
        }}
      >
        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              marginBottom: "10px",
              padding: "8px",
              borderRadius: "5px",
              maxWidth: "80%",
              wordBreak: "break-word",
              backgroundColor:
                msg.type === "user"
                  ? "#e0f7fa"
                  : msg.type === "ai"
                  ? "#f1f1f1"
                  : "#fffacd",
              marginLeft: msg.type === "user" ? "auto" : "0",
              marginRight: msg.type === "user" ? "0" : "auto",
            }}
          >
            <strong>
              {msg.type === "user"
                ? "You"
                : msg.type === "ai"
                ? "Agent"
                : "System"}
              :
            </strong>
            <div style={{ whiteSpace: "pre-wrap" }}>
              {typeof msg.content === "object"
                ? JSON.stringify(msg.content)
                : msg.content}
            </div>
          </div>
        ))}
        {isStreaming && messages[messages.length - 1]?.type !== "ai" && (
          <div style={{ fontStyle: "italic" }}>Agent thinking...</div>
        )}
      </div>
      <form
        onSubmit={handleSubmit}
        style={{
          display: "flex",
          padding: "10px",
          borderTop: "1px solid #ccc",
        }}
      >
        <input
          type="text"
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          placeholder="Ask the agent..."
          disabled={isStreaming}
          style={{
            flexGrow: 1,
            padding: "10px",
            marginRight: "10px",
            borderRadius: "5px",
            border: "1px solid #ddd",
          }}
        />
        <button
          type="submit"
          disabled={isStreaming}
          style={{
            padding: "10px 15px",
            borderRadius: "5px",
            border: "none",
            backgroundColor: "#007bff",
            color: "white",
            cursor: "pointer",
          }}
        >
          {isStreaming ? "Sending..." : "Send"}
        </button>
      </form>
    </div>
  );
}

export default ChatComponent;
