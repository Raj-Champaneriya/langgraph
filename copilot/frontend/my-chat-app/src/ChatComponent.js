// src/ChatComponent.js
import { useEffect, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid"; // For unique keys

// --- SVG Icons ---
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

// Icon for Suggested Prompt Tiles (generic idea icon)
const PromptTileIcon = () => (
  <svg
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="currentColor"
    style={{ color: "#88a0b8", flexShrink: 0 }}
  >
    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v2h-2zm0 4h2v6h-2z" />
  </svg>
);

// --- Suggested Prompts Data ---
const suggestedPromptsData = [
  {
    id: "archer_summary",
    title: "Archer Summary",
    prompt: "Give me the list of items from Archer in table format",
  },
  {
    id: "aramark_escalated_summary",
    title: "Aramark Escalated Summary",
    prompt:
      "Give me the list of all items from Aramark which has isEscalated is true in table format",
  },
  {
    id: "last_week_summary",
    title: "Last Week Summary",
    prompt: "Give me the list of all items created last week",
  },
  {
    id: "aramark_summary",
    title: "Aramark Summary",
    prompt: "Give me the list of items from Aramark in table format",
  },
];

function ChatComponent() {
  const [userInput, setUserInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const currentAiMessageRef = useRef("");
  const chatViewRef = useRef(null);
  const requestStartTimeRef = useRef(null);

  const scrollToBottom = () => {
    if (chatViewRef.current)
      chatViewRef.current.scrollTop = chatViewRef.current.scrollHeight;
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const styleSheet = document.createElement("style");
    styleSheet.type = "text/css";
    styleSheet.innerText = `
      @keyframes fadeInSlideUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
      .message-entry { animation: fadeInSlideUp 0.3s ease-out forwards; }
      @keyframes pulse { 0% { opacity: 0.5; } 50% { opacity: 1; } 100% { opacity: 0.5; } }
      .ai-streaming-placeholder span { animation: pulse 1.5s infinite ease-in-out; }
      .ai-streaming-placeholder span:nth-child(1) { animation-delay: 0s; }
      .ai-streaming-placeholder span:nth-child(2) { animation-delay: 0.2s; }
      .ai-streaming-placeholder span:nth-child(3) { animation-delay: 0.4s; }
      @keyframes thinkingDots { 0%, 20% { content: '.'; } 40%, 60% { content: '..'; } 80%, 100% { content: '...'; } }
      .thinking-dots::after { content: '.'; animation: thinkingDots 1.5s infinite; display: inline-block; width: 1.5em; text-align: left; }
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

  const handleSubmit = async (e, textOverride = null) => {
    if (e) e.preventDefault();
    const textToSubmit = textOverride !== null ? textOverride : userInput;

    if (!textToSubmit.trim() || isStreaming) return;

    requestStartTimeRef.current = Date.now();
    setIsStreaming(true);

    const newUserMessage = {
      id: uuidv4(),
      type: "user",
      content: textToSubmit,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, newUserMessage]);

    // If a suggested prompt was used, userInput state was set for feedback,
    // now clear it. If user typed, clear it as well.
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
        body: JSON.stringify({ text: textToSubmit }), // Use textToSubmit
      });

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ detail: "Failed to parse error JSON." }));
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
                if (!finalContent && msg.content === "...")
                  finalContent = "Agent finished processing.";
                else if (!finalContent) finalContent = msg.content;
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
              } else if (eventData.type === "stream_end")
                console.log("Stream ended by server event.");
              else if (eventData.type === "error") {
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
              }
            } catch (e) {
              console.error("Failed to parse JSON:", jsonString, e);
            }
          }
        });
      }
    } catch (error) {
      console.error("Fetch/stream failed:", error);
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

  const handleSuggestedPromptClick = async (promptText) => {
    if (isStreaming) return;
    setUserInput(promptText); // Update UI briefly for visual feedback
    await handleSubmit(null, promptText); // Pass prompt directly to submit logic
  };

  // --- Styles ---
  const styles = {
    chatContainer: {
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "flex-start",
      minHeight: "100vh",
      fontFamily:
        '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
      backgroundColor: "#1e1e1e",
      color: "#e0e0e0",
      padding: "20px 0",
      boxSizing: "border-box",
    },
    chatBox: {
      display: "flex",
      flexDirection: "column",
      width: "100%",
      maxWidth: "800px",
      backgroundColor: "#2d2d2d",
      borderRadius: "12px",
      boxShadow: "0 10px 25px rgba(0,0,0,0.3)",
      overflow: "hidden",
      flexGrow: 1,
      maxHeight: "calc(100vh - 40px)",
      boxSizing: "border-box",
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
      gap: "0px",
      width: "100%",
      boxSizing: "border-box",
    },
    messageEntry: { marginBottom: "15px" },
    messageBubbleWrapper: { display: "flex", alignItems: "flex-end" },
    message: {
      padding: "10px 15px",
      borderRadius: "18px",
      lineHeight: "1.5",
      wordBreak: "break-word",
      maxWidth: "75%",
      position: "relative",
    },
    userMessage: {
      backgroundColor: "#007bff",
      color: "#ffffff",
      borderBottomRightRadius: "5px",
      marginLeft: "auto",
    },
    aiMessage: {
      backgroundColor: "#424242",
      color: "#e0e0e0",
      borderBottomLeftRadius: "5px",
      marginRight: "auto",
    },
    toolActivityMessage: {
      fontSize: "0.85em",
      color: "#b0b0b0",
      padding: "8px 12px",
      borderRadius: "10px",
      margin: "10px auto 10px",
      maxWidth: "90%",
      textAlign: "left",
      display: "flex",
      alignItems: "center",
      backgroundColor: "rgba(70,70,70,0.5)",
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
    userAvatar: { marginRight: "10px", backgroundColor: "#0056b3" },
    aiAvatar: { marginRight: "10px", backgroundColor: "#666" },
    messageContent: { whiteSpace: "pre-wrap" },
    responseTimeText: {
      fontSize: "0.75em",
      color: "#9e9e9e",
      marginTop: "5px",
      paddingLeft: `calc(32px + 10px)`,
      textAlign: "left",
    },
    // Suggested Prompts Styles
    suggestedPromptsContainer: {
      display: "grid",
      gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", // Responsive columns
      gap: "12px",
      padding: "15px 20px 10px 20px",
      borderBottom: "1px solid #444444", // Separator from input form
      backgroundColor: "#2d2d2d", // Consistent with chatBox background
    },
    promptTile: {
      display: "flex",
      alignItems: "flex-start", // Align icon and text block
      backgroundColor: "#383838", // Slightly different from chatBox bg
      padding: "12px 15px",
      borderRadius: "8px",
      cursor: "pointer",
      transition:
        "background-color 0.2s ease-in-out, transform 0.1s ease-in-out",
      border: "1px solid #4a4a4a",
    },
    promptTileHover: {
      // Apply this on hover via JS if needed, or use :hover in injected CSS
      backgroundColor: "#454545",
      transform: "translateY(-2px)",
    },
    promptTileIconContainer: {
      // Wrapper for the icon if more styling is needed for it
      marginRight: "12px",
      marginTop: "2px", // Align icon better with title
    },
    promptTileTextContainer: {
      display: "flex",
      flexDirection: "column",
      textAlign: "left",
    },
    promptTileTitle: {
      fontSize: "0.95em",
      fontWeight: "600",
      color: "#e0e0e0",
      marginBottom: "4px",
    },
    promptTileText: {
      fontSize: "0.85em",
      color: "#b0b0b0",
      lineHeight: "1.4",
    },
    // Form and Input Styles
    form: {
      display: "flex",
      padding: "15px 20px",
      borderTop: "1px solid #444444",
      backgroundColor: "#333333",
      width: "100%",
      boxSizing: "border-box",
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
    inputFocus: {
      borderColor: "#007bff",
      boxShadow: "0 0 0 2px rgba(0,123,255,0.25)",
    },
    button: {
      padding: "0 18px",
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
      fontStyle: "italic",
      color: "#aaa",
      padding: "10px 20px",
      textAlign: "center",
      backgroundColor: "#2d2d2d",
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
              {/* ... message rendering logic (unchanged) ... */}
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
        </div>

        {/* --- Suggested Prompts Section --- */}
        {!isStreaming && (
          <div style={styles.suggestedPromptsContainer}>
            {suggestedPromptsData.map((p) => (
              <div
                key={p.id}
                style={styles.promptTile}
                onClick={() => handleSuggestedPromptClick(p.prompt)}
                role="button"
                tabIndex={0}
                onKeyPress={(e) => {
                  if (e.key === "Enter" || e.key === " ")
                    handleSuggestedPromptClick(p.prompt);
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor =
                    styles.promptTileHover.backgroundColor;
                  e.currentTarget.style.transform =
                    styles.promptTileHover.transform;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor =
                    styles.promptTile.backgroundColor;
                  e.currentTarget.style.transform = "none";
                }}
                onFocus={(e) => {
                  e.currentTarget.style.backgroundColor =
                    styles.promptTileHover.backgroundColor;
                }}
                onBlur={(e) => {
                  e.currentTarget.style.backgroundColor =
                    styles.promptTile.backgroundColor;
                }}
              >
                <div style={styles.promptTileIconContainer}>
                  <PromptTileIcon />
                </div>
                <div style={styles.promptTileTextContainer}>
                  <div style={styles.promptTileTitle}>{p.title}</div>
                  <div style={styles.promptTileText}>{p.prompt}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {isStreaming &&
          !messages.some(
            (m) => m.id === currentAiMessageRef.current && m.content === "..."
          ) && // Check if current AI message still placeholder
          (!messages.length ||
            messages[messages.length - 1]?.type !== "ai" ||
            messages[messages.length - 1]?.content === "...") && ( // More robust check for thinking
            <div style={styles.thinkingIndicator} className="thinking-dots">
              Agent is thinking
            </div>
          )}

        <form onSubmit={handleSubmit} style={styles.form}>
          <input
            type="text"
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            placeholder="Message Copilot..."
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
            <SendIcon />
          </button>
        </form>
      </div>
    </div>
  );
}

export default ChatComponent;
