import { useState, useEffect, useRef, useCallback } from "react";
import {
  fetchStrategies,
  createSession,
  sendMessage,
  deleteSession,
  getHistory,
} from "./api";
import "./App.css";

function Message({ role, content }) {
  const isUser = role === "user";
  return (
    <div className={`message-row ${isUser ? "user" : "assistant"}`}>
      <div className="avatar">{isUser ? "你" : "AI"}</div>
      <div className="bubble">
        {content.split("\n").map((line, i) => (
          <span key={i}>
            {line}
            {i < content.split("\n").length - 1 && <br />}
          </span>
        ))}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="message-row assistant">
      <div className="avatar">AI</div>
      <div className="bubble typing">
        <span />
        <span />
        <span />
      </div>
    </div>
  );
}

let sessionCounter = 1;

export default function App() {
  const [strategies, setStrategies] = useState([]);
  const [selectedStrategy, setSelectedStrategy] = useState("");
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  /** 按会话 id 保存消息，切换/新建会话时互不覆盖 */
  const [messagesBySession, setMessagesBySession] = useState({});
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    fetchStrategies()
      .then((list) => {
        const merged = Array.from(new Set(["NoMem", ...list]));
        setStrategies(merged);
        if (merged.length > 0) setSelectedStrategy(merged[0]);
      })
      .catch(() => setError("无法连接后端，请先启动 uvicorn api.app:app --reload"));
  }, []);

  const messages =
    activeSessionId && messagesBySession[activeSessionId] != null
      ? messagesBySession[activeSessionId]
      : [];

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleNewSession = useCallback(async () => {
    if (!selectedStrategy) return;
    setError("");
    try {
      const { session_id } = await createSession(selectedStrategy);
      const label = `${selectedStrategy} #${sessionCounter++}`;
      setSessions((prev) => [...prev, { id: session_id, label, strategy: selectedStrategy }]);
      setMessagesBySession((prev) => ({ ...prev, [session_id]: [] }));
      setActiveSessionId(session_id);
      inputRef.current?.focus();
    } catch (e) {
      setError(e.message);
    }
  }, [selectedStrategy]);

  const handleSelectSession = useCallback(
    async (id) => {
      const session = sessions.find((s) => s.id === id);
      if (!session) return;
      setActiveSessionId(id);
      setError("");
      try {
        const hist = await getHistory(id);
        setMessagesBySession((prev) => {
          if (prev[id] !== undefined && prev[id].length > 0) return prev;
          return { ...prev, [id]: hist };
        });
      } catch {
        setMessagesBySession((prev) => {
          if (prev[id] !== undefined) return prev;
          return { ...prev, [id]: [] };
        });
      }
    },
    [sessions]
  );

  const handleDeleteSession = useCallback(
    async (id, e) => {
      e.stopPropagation();
      try {
        await deleteSession(id);
      } catch {}
      setSessions((prev) => prev.filter((s) => s.id !== id));
      setMessagesBySession((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      if (activeSessionId === id) {
        setActiveSessionId(null);
      }
    },
    [activeSessionId]
  );

  const handleSend = useCallback(async () => {
    const text = input.trim();
    const sid = activeSessionId;
    if (!text || !sid || loading) return;
    setInput("");
    setError("");
    setMessagesBySession((prev) => ({
      ...prev,
      [sid]: [...(prev[sid] ?? []), { role: "user", content: text }],
    }));
    setLoading(true);
    try {
      const { reply } = await sendMessage(sid, text);
      setMessagesBySession((prev) => ({
        ...prev,
        [sid]: [...(prev[sid] ?? []), { role: "assistant", content: reply }],
      }));
    } catch (e) {
      setError(e.message);
      setMessagesBySession((prev) => ({
        ...prev,
        [sid]: [
          ...(prev[sid] ?? []),
          { role: "assistant", content: `[错误] ${e.message}` },
        ],
      }));
    } finally {
      setLoading(false);
    }
  }, [input, activeSessionId, loading]);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  const activeSession = sessions.find((s) => s.id === activeSessionId);

  return (
    <div className="layout">
      {/* 左侧边栏 */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <span className="logo">AI 记忆对话</span>
        </div>

        <div className="strategy-section">
          <label className="section-label">记忆策略</label>
          <select
            className="strategy-select"
            value={selectedStrategy}
            onChange={(e) => setSelectedStrategy(e.target.value)}
          >
            {strategies.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <button className="new-session-btn" onClick={handleNewSession} disabled={!selectedStrategy}>
            + 新建对话
          </button>
        </div>

        <div className="session-list">
          <label className="section-label">历史对话</label>
          {sessions.length === 0 && (
            <p className="empty-hint">暂无对话，点击新建</p>
          )}
          {sessions.map((s) => (
            <div
              key={s.id}
              className={`session-item ${s.id === activeSessionId ? "active" : ""}`}
              onClick={() => handleSelectSession(s.id)}
            >
              <span className="session-label">{s.label}</span>
              <button
                className="delete-btn"
                onClick={(e) => handleDeleteSession(s.id, e)}
                title="删除"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </aside>

      {/* 右侧聊天区 */}
      <main className="chat-area">
        {!activeSession ? (
          <div className="welcome">
            <div className="welcome-icon">🧠</div>
            <h2>选择记忆策略，开始对话</h2>
            <p>在左侧选择一种记忆策略，点击「新建对话」即可开始</p>
          </div>
        ) : (
          <>
            <div className="chat-header">
              <span className="chat-title">{activeSession.label}</span>
              <span className="chat-strategy-badge">{activeSession.strategy}</span>
            </div>

            <div className="messages-area">
              {messages.length === 0 && (
                <div className="empty-messages">发送第一条消息，开始对话吧</div>
              )}
              {messages.map((m, i) => (
                <Message key={i} role={m.role} content={m.content} />
              ))}
              {loading && <TypingIndicator />}
              <div ref={messagesEndRef} />
            </div>

            {error && <div className="error-bar">{error}</div>}

            <div className="input-area">
              <textarea
                ref={inputRef}
                className="input-box"
                placeholder="输入消息，按 Enter 发送，Shift+Enter 换行"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={loading}
                rows={1}
              />
              <button
                className="send-btn"
                onClick={handleSend}
                disabled={!input.trim() || loading}
              >
                {loading ? "…" : "发送"}
              </button>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
