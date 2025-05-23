// src/ChatComponent.js
import { useEffect, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid"; // For unique keys

// SVG Icon for Send Button
const SendIcon = () => (
  <svg
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <line x1="22" y1="2" x2="11" y2="13"></line>
    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
  </svg>
);

// SVG Icon for Tool Activity
const ToolIcon = () => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    style={{ marginRight: '8px', verticalAlign: 'middle' }}
  >
    <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path>
    <line x1="12" y1="12" x2="12" y2="12" strokeDasharray="0.1 2" strokeLinecap="butt"></line> {/* Dotted center for visual effect */}
  </svg>
);


function ChatComponent() {
  const [userInput, setUserInput] = useState("");
  const [messages, setMessages] = useState([]); // { id: string, type: 'user' | 'ai' | 'tool_activity', content: any, timestamp: Date }
  const [isStreaming, setIsStreaming] = useState(false);
  const currentAiMessageRef = useRef("");
  const chatViewRef = useRef(null); // Ref for the chat view div

  const scrollToBottom = () => {
    if (chatViewRef.current) {
      chatViewRef.current.scrollTop = chatViewRef.current.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Inject global styles & animations
  useEffect(() => {
    const styleSheet = document.createElement("style");
    styleSheet.type = "text/css";
    styleSheet.innerText = `
      @keyframes fadeInSlideUp {
        from {
          opacity: 0;
          transform: translateY(10px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }
      .message-enter {
        animation: fadeInSlideUp 0.3s ease-out forwards;
      }

      @keyframes pulse {
        0% { opacity: 0.5; }
        50% { opacity: 1; }
        100% { opacity: 0.5; }
      }
      .ai-streaming-placeholder span {
        animation: pulse 1.5s infinite ease-in-out;
      }
      .ai-streaming-placeholder span:nth-child(1) { animation-delay: 0s; }
      .ai-streaming-placeholder span:nth-child(2) { animation-delay: 0.2s; }
      .ai-streaming-placeholder span:nth-child(3) { animation-delay: 0.4s; }

      @keyframes thinkingDots {
        0%, 20% { content: '.'; }
        40%, 60% { content: '..'; }
        80%, 100% { content: '...'; }
      }
      .thinking-dots::after {
        content: '.';
        animation: thinkingDots 1.5s infinite;
        display: inline-block;
        width: 1.5em; /* Adjust width to prevent layout shift */
        text-align: left;
      }

      /* Custom Scrollbar */
      .custom-scrollbar::-webkit-scrollbar {
        width: 8px;
      }
      .custom-scrollbar::-webkit-scrollbar-track {
        background: #2d2d2d;
        border-radius: 10px;
      }
      .custom-scrollbar::-webkit-scrollbar-thumb {
        background: #555;
        border-radius: 10px;
      }
      .custom-scrollbar::-webkit-scrollbar-thumb:hover {
        background: #666;
      }
    `;
    document.head.appendChild(styleSheet);
    return () => {
      document.head.removeChild(styleSheet);
    };
  }, []);

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!userInput.trim() || isStreaming) return;

    setIsStreaming(true);
    const newUserMessage = {
      id: uuidv4(),
      type: "user",
      content: userInput,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, newUserMessage]);
    setUserInput("");
    currentAiMessageRef.current = "";

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
        const errorData = await response.json();
        console.error("API Error:", errorData);
        setMessages((prev) => [
          ...prev,
          {
            id: uuidv4(),
            type: "ai",
            content: `Error: ${errorData.detail || "Failed to get response"}`,
            timestamp: new Date(),
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

      const aiMessageId = uuidv4();
      setMessages((prev) => [
        ...prev,
        { id: aiMessageId, type: "ai", content: "...", timestamp: new Date() },
      ]);

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === aiMessageId && msg.content === "..." && !currentAiMessageRef.current.trim()
                ? { ...msg, content: "Agent finished." } // Or remove placeholder
                : msg.id === aiMessageId && currentAiMessageRef.current.trim()
                ? { ...msg, content: currentAiMessageRef.current }
                : msg
            )
          );
          break;
        }

        const eventLines = value.split("\n\n");
        eventLines.forEach((line) => {
          if (line.startsWith("data: ")) {
            const jsonString = line.substring(6);
            try {
              const eventData = JSON.parse(jsonString);

              if (eventData.type === "llm_chunk") {
                currentAiMessageRef.current += eventData.content;
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === aiMessageId
                      ? { ...msg, content: currentAiMessageRef.current || "..." } // Keep placeholder if current content is empty
                      : msg
                  )
                );
              } else if (eventData.type === "tool_start") {
                 // Finalize previous AI message if it was just a placeholder
                if (currentAiMessageRef.current === "") {
                    setMessages(prev => prev.map(msg => msg.id === aiMessageId && msg.content === "..." ? {...msg, content: "Thinking..."} : msg));
                }
                currentAiMessageRef.current = ""; // Reset for next potential LLM chunk after tool

                setMessages((prev) => [
                  ...prev,
                  {
                    id: uuidv4(),
                    type: "tool_activity",
                    content: `Tool Starting: ${eventData.name
                      } with input ${JSON.stringify(eventData.input)}`,
                    timestamp: new Date(),
                  },
                ]);
              } else if (eventData.type === "tool_end") {
                setMessages((prev) => [
                  ...prev,
                  {
                    id: uuidv4(),
                    type: "tool_activity",
                    content: `Tool Finished: ${eventData.name
                      } - Output: ${JSON.stringify(eventData.output)}`,
                    timestamp: new Date(),
                  },
                ]);
                // After tool ends, a new AI placeholder might be needed if LLM is expected to speak again.
                // This logic depends on your agent. For now, we just add the tool_end event.
                // If an LLM response follows, it will create its own message or update the existing one.
              } else if (eventData.type === "stream_end") {
                console.log("Stream ended by server event.");
              } else if (eventData.type === "error") {
                console.error("Stream Error Event:", eventData.detail);
                setMessages((prev) => [
                  ...prev,
                  {
                    id: uuidv4(),
                    type: "ai",
                    content: `Stream Error: ${eventData.detail}`,
                    timestamp: new Date(),
                  },
                ]);
              }
            } catch (e) {
              console.error("Failed to parse JSON from stream data:", jsonString, e);
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
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsStreaming(false);
      currentAiMessageRef.current = "";
    }
  };

  // Styles
  const styles = {
    chatContainer: {
      display: "flex",
      flexDirection: "column",
      height: "100vh",
      fontFamily:
        '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol"',
      backgroundColor: "#1e1e1e", // Dark background for the whole page
      color: "#e0e0e0",
    },
    chatBox: {
      display: "flex",
      flexDirection: "column",
      height: "calc(100vh - 40px)", // Adjust if header/footer height changes
      maxWidth: "800px",
      margin: "20px auto",
      backgroundColor: "#2d2d2d", // Slightly lighter dark for chat area
      borderRadius: "12px",
      boxShadow: "0 10px 25px rgba(0, 0, 0, 0.3)",
      overflow: "hidden",
    },
    header: {
      padding: "15px 20px",
      backgroundColor: "#333333",
      borderBottom: "1px solid #444444",
      textAlign: "center",
      fontSize: "1.2em",
      fontWeight: "600",
      color: "#ffffff",
    },
    chatView: {
      flexGrow: 1,
      overflowY: "auto",
      padding: "20px",
      display: "flex",
      flexDirection: "column",
      gap: "15px",
    },
    message: {
      display: "flex",
      alignItems: "flex-end", // Align avatar with bottom of message bubble
      maxWidth: "75%",
      padding: "10px 15px",
      borderRadius: "18px",
      lineHeight: "1.5",
      wordBreak: "break-word",
      position: "relative", // For animation
    },
    userMessage: {
      backgroundColor: "#007bff",
      // background: "linear-gradient(135deg, #007bff 0%, #0056b3 100%)",
      color: "#ffffff",
      marginLeft: "auto",
      borderBottomRightRadius: "5px",
    },
    aiMessage: {
      backgroundColor: "#424242",
      color: "#e0e0e0",
      marginRight: "auto",
      borderBottomLeftRadius: "5px",
    },
    toolActivityMessage: {
      fontSize: "0.85em",
      color: "#b0b0b0", // Lighter grey for tool activity
      // backgroundColor: "#3a3a3a",
      padding: "8px 12px",
      borderRadius: "10px",
      margin: "5px auto", // Centered or adjust as needed
      maxWidth: "90%",
      textAlign: "left",
      display: 'flex',
      alignItems: 'center',
    },
    avatar: {
      width: "32px",
      height: "32px",
      borderRadius: "50%",
      backgroundColor: "#555",
      color: "#fff",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontSize: "0.9em",
      fontWeight: "bold",
      flexShrink: 0,
    },
    userAvatar: {
      marginRight: "10px",
      backgroundColor: "#0056b3",
    },
    aiAvatar: {
      marginLeft: "10px",
      backgroundColor: "#666", // Slightly different for AI
    },
    messageContent: {
      whiteSpace: "pre-wrap",
    },
    messageMeta: {
      fontSize: "0.75em",
      color: "rgba(255, 255, 255, 0.5)", // For user messages
      marginTop: "5px",
      textAlign: "right",
    },
    aiMessageMeta: {
      fontSize: "0.75em",
      color: "rgba(224, 224, 224, 0.5)", // For AI messages
      marginTop: "5px",
      textAlign: "left",
    },
    form: {
      display: "flex",
      padding: "15px 20px",
      borderTop: "1px solid #444444",
      backgroundColor: "#333333",
    },
    input: {
      flexGrow: 1,
      padding: "12px 15px",
      marginRight: "10px",
      borderRadius: "25px",
      border: "1px solid #555",
      backgroundColor: "#252525",
      color: "#e0e0e0",
      fontSize: "1em",
      outline: "none",
      transition: "border-color 0.2s, box-shadow 0.2s",
    },
    inputFocus: { // Would apply this on focus via JS if not using :focus selector
      borderColor: "#007bff",
      boxShadow: "0 0 0 2px rgba(0, 123, 255, 0.25)",
    },
    button: {
      padding: "0 18px", // Adjusted padding for icon button
      borderRadius: "25px",
      border: "none",
      backgroundColor: "#007bff",
      color: "white",
      cursor: "pointer",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontSize: "1em",
      fontWeight: "500",
      transition: "background-color 0.2s, opacity 0.2s",
    },
    buttonHover: { // Would apply this on hover
      backgroundColor: "#0056b3",
    },
    buttonDisabled: {
      backgroundColor: "#555",
      opacity: 0.7,
      cursor: "not-allowed",
    },
    thinkingIndicator: {
      fontStyle: "italic",
      color: "#aaa",
      padding: "10px 20px",
      textAlign: "center",
    },
    aiStreamingPlaceholder: {
      display: "inline-block",
    },
  };

  return (
    <div style={styles.chatContainer}>
      <div style={styles.chatBox}>
        <div style={styles.header}>LangGraph Agent Chat</div>
        <div id="chat-view" ref={chatViewRef} style={styles.chatView} className="custom-scrollbar">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className="message-enter" // For entry animation
              style={{
                ...styles.message,
                ...(msg.type === "user"
                  ? styles.userMessage
                  : msg.type === "ai"
                  ? styles.aiMessage
                  : {}), // Tool activity has its own top-level style
                flexDirection: msg.type === "user" ? "row-reverse" : "row",
              }}
            >
              {msg.type !== "tool_activity" && (
                <div
                  style={{
                    ...styles.avatar,
                    ...(msg.type === "user"
                      ? styles.userAvatar
                      : styles.aiAvatar),
                     margin: msg.type === "user" ? "0 0 0 10px" : "0 10px 0 0",
                  }}
                >
                  {msg.type === "user" ? "U" : "A"}
                </div>
              )}

              {msg.type === "tool_activity" ? (
                 <div style={styles.toolActivityMessage}>
                    <ToolIcon />
                    <div style={styles.messageContent}>
                        {msg.content}
                    </div>
                </div>
              ) : (
                <div
                  style={{
                    padding: msg.type === 'user' ? '10px 15px' : '10px 15px', // Bubble specific padding
                    borderRadius: '18px',
                    backgroundColor: msg.type === 'user' ? (styles.userMessage.backgroundColor) : (styles.aiMessage.backgroundColor),
                    color: msg.type === 'user' ? (styles.userMessage.color) : (styles.aiMessage.color),
                    borderBottomRightRadius: msg.type === 'user' ? '5px' : '18px',
                    borderBottomLeftRadius: msg.type === 'ai' ? '5px' : '18px',
                  }}
                >
                  <div style={styles.messageContent}>
                    {msg.type === "ai" && msg.content === "..." ? (
                       <span style={styles.aiStreamingPlaceholder}>
                        <span>.</span><span>.</span><span>.</span>
                      </span>
                    ) : typeof msg.content === "object" ? (
                      JSON.stringify(msg.content)
                    ) : (
                      msg.content
                    )}
                  </div>
                  {/* Optional: Timestamp */}
                  {/* <div style={msg.type === 'user' ? styles.messageMeta : styles.aiMessageMeta}>
                                    {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </div> */}
                </div>
              )}
            </div>
          ))}
          {isStreaming && messages[messages.length - 1]?.type !== "ai" &&
            (!messages.find(m => m.type === "ai" && m.content === "...")) && ( // Show thinking only if no AI placeholder
            <div style={styles.thinkingIndicator} className="thinking-dots">
              Agent is thinking
            </div>
          )}
        </div>
        <form
          onSubmit={handleSubmit}
          style={styles.form}
        >
          <input
            type="text"
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            placeholder="Ask the agent..."
            disabled={isStreaming}
            style={styles.input}
            onFocus={(e) => e.target.style.borderColor = styles.inputFocus.borderColor} // Simplified focus
            onBlur={(e) => e.target.style.borderColor = styles.input.borderColor}      // Simplified blur
          />
          <button
            type="submit"
            disabled={isStreaming}
            style={{
              ...styles.button,
              ...(isStreaming ? styles.buttonDisabled : {}),
            }}
            onMouseOver={(e) => { if (!isStreaming) e.currentTarget.style.backgroundColor = styles.buttonHover.backgroundColor; }}
            onMouseOut={(e) => { if (!isStreaming) e.currentTarget.style.backgroundColor = styles.button.backgroundColor; }}
          >
            {isStreaming ? (
              "..." // Simple sending indicator
            ) : (
              <SendIcon />
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

export default ChatComponent;