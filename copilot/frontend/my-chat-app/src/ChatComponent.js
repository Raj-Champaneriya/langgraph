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
    style={{ marginRight: "8px", verticalAlign: "middle", flexShrink: 0 }}
  >
    <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path>
  </svg>
);

function ChatComponent() {
  const [userInput, setUserInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const currentAiMessageRef = useRef("");
  const chatViewRef = useRef(null);
  const requestStartTimeRef = useRef(null); // To store start time of user request

  const scrollToBottom = () => {
    if (chatViewRef.current) {
      chatViewRef.current.scrollTop = chatViewRef.current.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const styleSheet = document.createElement("style");
    styleSheet.type = "text/css";
    styleSheet.innerText = `
      @keyframes fadeInSlideUp {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
      }
      .message-entry { /* Changed class name slightly for clarity */
        animation: fadeInSlideUp 0.3s ease-out forwards;
      }

      @keyframes pulse {
        0% { opacity: 0.5; } 50% { opacity: 1; } 100% { opacity: 0.5; }
      }
      .ai-streaming-placeholder span { animation: pulse 1.5s infinite ease-in-out; }
      .ai-streaming-placeholder span:nth-child(1) { animation-delay: 0s; }
      .ai-streaming-placeholder span:nth-child(2) { animation-delay: 0.2s; }
      .ai-streaming-placeholder span:nth-child(3) { animation-delay: 0.4s; }

      @keyframes thinkingDots {
        0%, 20% { content: '.'; } 40%, 60% { content: '..'; } 80%, 100% { content: '...'; }
      }
      .thinking-dots::after {
        content: '.'; animation: thinkingDots 1.5s infinite; display: inline-block; width: 1.5em; text-align: left;
      }

      .custom-scrollbar::-webkit-scrollbar { width: 8px; }
      .custom-scrollbar::-webkit-scrollbar-track { background: #2d2d2d; border-radius: 10px; }
      .custom-scrollbar::-webkit-scrollbar-thumb { background: #555; border-radius: 10px; }
      .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #666; }
    `;
    document.head.appendChild(styleSheet);
    return () => {
      document.head.removeChild(styleSheet);
    };
  }, []);

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!userInput.trim() || isStreaming) return;

    requestStartTimeRef.current = Date.now(); // Store start time

    setIsStreaming(true);
    const newUserMessage = {
      id: uuidv4(),
      type: "user",
      content: userInput,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, newUserMessage]);
    const currentInput = userInput; // Store for the API call
    setUserInput("");
    currentAiMessageRef.current = "";

    const aiMessageId = uuidv4();
    setMessages((prev) => [
      ...prev,
      { id: aiMessageId, type: "ai", content: "...", timestamp: new Date() },
    ]);

    try {
      const response = await fetch("http://localhost:8000/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify({ text: currentInput }),
      });

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ detail: "Failed to parse error JSON." }));
        console.error("API Error:", errorData);
        const errorContent = `Error: ${
          errorData.detail || "Failed to get response"
        }`;
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === aiMessageId
              ? {
                  ...msg,
                  content: errorContent,
                  responseTime:
                    (Date.now() - requestStartTimeRef.current) / 1000,
                }
              : msg
          )
        );
        setIsStreaming(false);
        return;
      }

      if (!response.body) {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === aiMessageId
              ? {
                  ...msg,
                  content: "Empty response from server.",
                  responseTime:
                    (Date.now() - requestStartTimeRef.current) / 1000,
                }
              : msg
          )
        );
        setIsStreaming(false);
        return;
      }

      const reader = response.body
        .pipeThrough(new TextDecoderStream())
        .getReader();

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          const responseEndTime = Date.now();
          const durationMs =
            responseEndTime - (requestStartTimeRef.current || responseEndTime);

          setMessages((prev) =>
            prev.map((msg) => {
              if (msg.id === aiMessageId) {
                let finalContent = currentAiMessageRef.current.trim();
                if (!finalContent && msg.content === "...") {
                  finalContent = "Agent finished processing.";
                } else if (!finalContent) {
                  finalContent = msg.content; // Keep existing if it was updated by non-llm event
                }
                return {
                  ...msg,
                  content: finalContent,
                  responseTime: durationMs / 1000,
                };
              }
              return msg;
            })
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
                      ? {
                          ...msg,
                          content: currentAiMessageRef.current || "...",
                        }
                      : msg
                  )
                );
              } else if (
                eventData.type === "tool_start" ||
                eventData.type === "tool_end"
              ) {
                // Finalize previous AI message content if it was just a placeholder "..." before tool activity
                if (
                  currentAiMessageRef.current === "" &&
                  eventData.type === "tool_start"
                ) {
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === aiMessageId && msg.content === "..."
                        ? { ...msg, content: "Processing with tools..." }
                        : msg
                    )
                  );
                }
                // Reset for potential new LLM chunks after this tool cycle for the same aiMessageId
                if (eventData.type === "tool_end")
                  currentAiMessageRef.current = "";

                const toolContent =
                  eventData.type === "tool_start"
                    ? `Tool Starting: ${
                        eventData.name
                      } with input ${JSON.stringify(eventData.input)}`
                    : `Tool Finished: ${
                        eventData.name
                      } - Output: ${JSON.stringify(eventData.output)}`;
                setMessages((prev) => [
                  ...prev,
                  {
                    id: uuidv4(),
                    type: "tool_activity",
                    content: toolContent,
                    timestamp: new Date(),
                  },
                ]);
              } else if (eventData.type === "stream_end") {
                console.log("Stream ended by server event.");
              } else if (eventData.type === "error") {
                console.error("Stream Error Event:", eventData.detail);
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === aiMessageId
                      ? {
                          ...msg,
                          content: `Stream Error: ${eventData.detail}`,
                          responseTime:
                            (Date.now() - requestStartTimeRef.current) / 1000,
                        }
                      : msg
                  )
                );
                // Potentially break or handle reader closure
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
      const errorContent = "Error: Could not connect or stream failed.";
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === aiMessageId
            ? {
                ...msg,
                content: errorContent,
                responseTime:
                  (Date.now() - (requestStartTimeRef.current || Date.now())) /
                  1000,
              }
            : msg
        )
      );
    } finally {
      setIsStreaming(false);
      currentAiMessageRef.current = "";
      requestStartTimeRef.current = null;
    }
  };

  const styles = {
    chatContainer: {
      display: "flex",
      flexDirection: "column",
      alignItems: "center", // Center chatBox horizontally
      justifyContent: "flex-start",
      minHeight: "100vh",
      fontFamily:
        '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol"',
      backgroundColor: "#1e1e1e",
      color: "#e0e0e0",
      padding: "20px 0", // Vertical padding for the container
      boxSizing: "border-box",
    },
    chatBox: {
      display: "flex",
      flexDirection: "column",
      width: "100%", // Take full width of allocated centered space
      maxWidth: "800px", // Max width of the chat interface
      backgroundColor: "#2d2d2d",
      borderRadius: "12px",
      boxShadow: "0 10px 25px rgba(0, 0, 0, 0.3)",
      overflow: "hidden",
      flexGrow: 1, // Allows chatBox to take available vertical space if chatContainer is taller
      maxHeight: "calc(100vh - 40px)", // Ensure it doesn't overflow viewport due to padding
      boxSizing: "border-box",
    },
    header: {
      /* ... unchanged ... */ padding: "15px 20px",
      backgroundColor: "#333333",
      borderBottom: "1px solid #444444",
      textAlign: "center",
      fontSize: "1.2em",
      fontWeight: "600",
      color: "#ffffff",
    },
    chatView: {
      /* ... unchanged ... */ flexGrow: 1,
      overflowY: "auto",
      padding: "20px",
      display: "flex",
      flexDirection: "column",
      gap: "0px", // Gap handled by messageEntry margin
      width: "100%",
      boxSizing: "border-box",
    },
    messageEntry: {
      // Wrapper for avatar, bubble, and meta like response time
      marginBottom: "15px",
    },
    messageBubbleWrapper: {
      // New wrapper for avatar and bubble flex layout
      display: "flex",
      alignItems: "flex-end", // Align avatar with bottom of message bubble
    },
    message: {
      // Bubble styling
      padding: "10px 15px",
      borderRadius: "18px",
      lineHeight: "1.5",
      wordBreak: "break-word",
      maxWidth: "75%",
      position: "relative",
    },
    userMessage: {
      /* ... unchanged ... */ backgroundColor: "#007bff",
      color: "#ffffff",
      borderBottomRightRadius: "5px",
      marginLeft: "auto", // Added for alignment within flex wrapper
    },
    aiMessage: {
      /* ... unchanged ... */ backgroundColor: "#424242",
      color: "#e0e0e0",
      borderBottomLeftRadius: "5px",
      marginRight: "auto", // Added for alignment
    },
    toolActivityMessage: {
      /* ... unchanged ... */ fontSize: "0.85em",
      color: "#b0b0b0",
      padding: "8px 12px",
      borderRadius: "10px",
      margin: "10px auto 10px",
      maxWidth: "90%",
      textAlign: "left",
      display: "flex",
      alignItems: "center",
      backgroundColor: "rgba(70, 70, 70, 0.5)", // Subtle background
    },
    avatar: {
      /* ... unchanged ... */ width: "32px",
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
    userAvatar: { marginRight: "10px", backgroundColor: "#0056b3" },
    aiAvatar: {
      marginLeft: "0px",
      marginRight: "10px",
      backgroundColor: "#666",
    }, // AI avatar on left, then margin
    messageContent: { whiteSpace: "pre-wrap" },
    responseTimeText: {
      fontSize: "0.75em",
      color: "#9e9e9e",
      marginTop: "5px",
      paddingLeft: `calc(32px + 10px)`, // Avatar width (32px) + AI avatar's right margin (10px)
      textAlign: "left",
    },
    form: {
      /* ... unchanged ... */ display: "flex",
      padding: "15px 20px",
      borderTop: "1px solid #444444",
      backgroundColor: "#333333",
      width: "100%",
      boxSizing: "border-box",
    },
    input: {
      /* ... unchanged ... */ flexGrow: 1,
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
    inputFocus: {
      borderColor: "#007bff",
      boxShadow: "0 0 0 2px rgba(0, 123, 255, 0.25)",
    },
    button: {
      /* ... unchanged ... */ padding: "0 18px",
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
    buttonHover: { backgroundColor: "#0056b3" },
    buttonDisabled: {
      backgroundColor: "#555",
      opacity: 0.7,
      cursor: "not-allowed",
    },
    thinkingIndicator: {
      /* ... unchanged ... */ fontStyle: "italic",
      color: "#aaa",
      padding: "10px 20px",
      textAlign: "center",
    },
    aiStreamingPlaceholder: { display: "inline-block" },
  };

  return (
    <div style={styles.chatContainer}>
      <div style={styles.chatBox}>
        <div style={styles.header}>LangGraph Agent Chat</div>
        <div
          id="chat-view"
          ref={chatViewRef}
          style={styles.chatView}
          className="custom-scrollbar"
        >
          {messages.map((msg) => (
            <div
              key={msg.id}
              className="message-entry"
              style={styles.messageEntry}
            >
              {msg.type === "tool_activity" ? (
                <div style={styles.toolActivityMessage}>
                  <ToolIcon />
                  <div style={styles.messageContent}>{msg.content}</div>
                </div>
              ) : (
                <>
                  <div
                    style={{
                      ...styles.messageBubbleWrapper,
                      flexDirection:
                        msg.type === "user" ? "row-reverse" : "row",
                    }}
                  >
                    <div
                      style={{
                        ...styles.avatar,
                        ...(msg.type === "user"
                          ? styles.userAvatar
                          : styles.aiAvatar),
                      }}
                    >
                      {msg.type === "user" ? "You" : "A"}
                    </div>
                    <div
                      style={{
                        ...styles.message,
                        ...(msg.type === "user"
                          ? styles.userMessage
                          : styles.aiMessage),
                      }}
                    >
                      <div style={styles.messageContent}>
                        {msg.type === "ai" && msg.content === "..." ? (
                          <span style={styles.aiStreamingPlaceholder}>
                            <span>.</span>
                            <span>.</span>
                            <span>.</span>
                          </span>
                        ) : typeof msg.content === "object" ? (
                          JSON.stringify(msg.content)
                        ) : (
                          msg.content
                        )}
                      </div>
                    </div>
                  </div>
                  {msg.type === "ai" && msg.responseTime !== undefined && (
                    <div style={styles.responseTimeText}>
                      Agent: {msg.responseTime.toFixed(1)}s
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
          {isStreaming &&
            messages[messages.length - 1]?.type !== "ai" &&
            !messages.find((m) => m.type === "ai" && m.content === "...") && (
              <div style={styles.thinkingIndicator} className="thinking-dots">
                Agent is thinking
              </div>
            )}
        </div>
        <form onSubmit={handleSubmit} style={styles.form}>
          <input
            type="text"
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            placeholder="Ask the agent..."
            disabled={isStreaming}
            style={styles.input}
            onFocus={(e) =>
              (e.target.style.borderColor = styles.inputFocus.borderColor)
            }
            onBlur={(e) =>
              (e.target.style.borderColor = styles.input.borderColor)
            }
          />
          <button
            type="submit"
            disabled={isStreaming}
            style={{
              ...styles.button,
              ...(isStreaming ? styles.buttonDisabled : {}),
            }}
            onMouseOver={(e) => {
              if (!isStreaming)
                e.currentTarget.style.backgroundColor =
                  styles.buttonHover.backgroundColor;
            }}
            onMouseOut={(e) => {
              if (!isStreaming)
                e.currentTarget.style.backgroundColor =
                  styles.button.backgroundColor;
            }}
          >
            {isStreaming ? "..." : <SendIcon />}
          </button>
        </form>
      </div>
    </div>
  );
}

export default ChatComponent;
