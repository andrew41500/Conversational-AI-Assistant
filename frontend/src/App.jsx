import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const renderContent = (content) => {
  if (!content) return null;
  // Split by the custom markdown-like tag we send from backend
  const parts = content.split(/(\[CHART:.*?\])/);
  return parts.map((part, i) => {
    if (part.startsWith('[CHART:') && part.endsWith(']')) {
      // Extract the data string
      const src = part.slice(7, -1);
      return <img key={i} src={src} alt="Generated Chart" className="generated-chart" />;
    }
    return <span key={i} style={{ whiteSpace: 'pre-wrap' }}>{part}</span>;
  });
};

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Multi-session state
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load all sessions on mount
  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/sessions`);
        if (res.ok) {
          const data = await res.json();
          setSessions(data.sessions);
          if (data.sessions.length > 0) {
            setActiveSessionId(data.sessions[0].id);
          } else {
            handleNewChat();
          }
        }
      } catch (err) {
        console.error("Failed to load sessions:", err);
        handleNewChat();
      }
    };
    fetchSessions();
  }, []);

  // Fetch history when activeSessionId changes
  useEffect(() => {
    if (!activeSessionId) return;

    const fetchHistory = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/history?session_id=${activeSessionId}`);
        if (res.ok) {
          const data = await res.json();
          setMessages(data.messages);
        }
      } catch (err) {
        console.error("Failed to load chat history:", err);
      }
    };
    fetchHistory();
  }, [activeSessionId]);

  const handleNewChat = () => {
    // Generate simple UUID or timestamp-based ID for simplicity
    const newSessionId = `session_${Date.now()}`;
    setActiveSessionId(newSessionId);
    setMessages([]);
  };

  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation(); // Don't trigger the click that selects the session
    if (!window.confirm("Are you sure you want to delete this chat?")) return;

    try {
      const res = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        setSessions(prev => prev.filter(s => s.id !== sessionId));
        if (activeSessionId === sessionId) {
          const remaining = sessions.filter(s => s.id !== sessionId);
          if (remaining.length > 0) {
            setActiveSessionId(remaining[0].id);
          } else {
            handleNewChat();
          }
        }
      }
    } catch (err) {
      console.error("Failed to delete session:", err);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading || !activeSessionId) return;

    const userMessage = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    const aiMessage = { role: 'ai', content: '' };
    setMessages((prev) => [...prev, aiMessage]);

    // If this is the first message in the session, fetch sessions again slightly later 
    // to dynamically load the "Title" of this new session in the Sidebar using the first msg text
    if (messages.length === 0) {
      setTimeout(async () => {
        try {
          const res = await fetch(`${API_BASE_URL}/api/sessions`);
          if (res.ok) {
            const data = await res.json();
            setSessions(data.sessions);
          }
        } catch (err) { }
      }, 1500);
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: userMessage.content,
          session_id: activeSessionId
        })
      });

      if (!response.body) throw new Error("No response body.");

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const textChunk = decoder.decode(value, { stream: true });

        setMessages((prev) => {
          const newMessages = [...prev];
          const lastIndex = newMessages.length - 1;
          newMessages[lastIndex] = {
            ...newMessages[lastIndex],
            content: newMessages[lastIndex].content + textChunk
          };
          return newMessages;
        });
      }
    } catch (err) {
      console.error("Error during streaming:", err);
      setMessages((prev) => {
        const newMessages = [...prev];
        const lastIndex = newMessages.length - 1;
        newMessages[lastIndex].content += "\n[Error: Failed to connect to backend stream]";
        return newMessages;
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar for Multi-Session */}
      <nav className="sidebar">
        <div className="sidebar-header">
          <h2>CONVERSATIONAL AI ASSISTANT</h2>
          <button className="new-chat-btn" onClick={handleNewChat}>
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 4V20M4 12H20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            New Chat
          </button>
        </div>

        <div className="session-list">
          {sessions.length === 0 && <div className="no-sessions">No previous chats</div>}
          {sessions.map(session => (
            <div
              key={session.id}
              className={`session-item ${activeSessionId === session.id ? 'active' : ''}`}
              onClick={() => setActiveSessionId(session.id)}
            >
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="session-icon">
                <path d="M21 15C21 15.5304 20.7893 16.0391 20.4142 16.4142C20.0391 16.7893 19.5304 17 19 17H7L3 21V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H19C19.5304 3 20.0391 3.21071 20.4142 3.58579C20.7893 3.96086 21 4.46957 21 5V15Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span className="session-title">{session.title}</span>
              <button
                className="delete-session-btn"
                onClick={(e) => handleDeleteSession(e, session.id)}
                title="Remove chat"
              >
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      </nav>

      {/* Main Chat Interface */}
      <div className="chat-container">
        <header className="chat-header">
          <div className="title">
            <h1>{sessions.find(s => s.id === activeSessionId)?.title || "New Chat"}</h1>
            
          </div>
        </header>

        <main className="chat-window">
          {messages.length === 0 ? (
            <div className="empty-state">
              <div className="welcome">Start a new conversation!</div>
            </div>
          ) : (
            messages.map((msg, index) => (
              <div key={index} className={`message-wrapper ${msg.role}`}>
                <div className="message-bubble">
                  {renderContent(msg.content)}
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </main>

        <div className="chat-input-wrapper">
          <form className="chat-input-area" onSubmit={handleSubmit}>
            <textarea
              placeholder="Ask me anything..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              autoFocus
              rows={1}
            />
            <button type="submit" disabled={!input.trim() || isLoading}>
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M2.01 21L23 12L2.01 3L2 10L17 12L2 14L2.01 21Z" fill="currentColor" />
              </svg>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default App;
