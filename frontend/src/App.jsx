import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";

const VIEW = {
  ORIGINAL: "original",
  REPORT: "report",
  CHAT: "chat",
};
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function App() {
  const [reports, setReports] = useState([]);
  const [activeReportId, setActiveReportId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [markdown, setMarkdown] = useState("# Loading...");

  const [sidebarVisible, setSidebarVisible] = useState(true);
  const [viewMode, setViewMode] = useState(VIEW.ORIGINAL);

  useEffect(() => {
    fetch("/content.md")
      .then((res) => res.text())
      .then(setMarkdown)
      .catch(() => setMarkdown("# Failed to load markdown"));
  }, []);

  useEffect(() => {
    loadReports();
  }, []);

  useEffect(() => {
    if (activeReportId) {
      loadMessages(activeReportId);
    }
  }, [activeReportId]);

  async function loadReports() {
    const res = await fetch(`${API_BASE}/reports`);
    const data = await res.json();
    setReports(data);
    if (!activeReportId && data.length) setActiveReportId(data[0].id);
  }

  async function loadMessages(reportId) {
    const res = await fetch(`${API_BASE}/reports/${reportId}/messages`);
    const data = await res.json();
    setMessages(data);
    return data;
  }

  async function createReport() {
    const title = `Report ${reports.length + 1}`;
    const res = await fetch(`${API_BASE}/reports`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    const created = await res.json();
    await loadReports();
    setActiveReportId(created.id);
    setMessages([]);
  }

  async function sendMessage() {
    if (!activeReportId || !input.trim()) return;

    const reportId = activeReportId;
    const content = input.trim();
    setInput("");

    const optimisticUser = {
      id: `tmp-u-${Date.now()}`,
      role: "user",
      content,
    };
    setMessages((prev) => [...prev, optimisticUser]);

    const res = await fetch(`${API_BASE}/reports/${reportId}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });

    const data = await res.json();
    await loadMessages(reportId);

    if (!res.ok) {
      alert(data.detail || "Failed to send message");
      return;
    }
  }

  const showReportPanel = useMemo(() => {
    if (viewMode === VIEW.REPORT) return true;
    if (viewMode === VIEW.CHAT) return false;
    return true;
  }, [viewMode]);

  const showChatPanel = useMemo(() => {
    if (viewMode === VIEW.CHAT) return true;
    if (viewMode === VIEW.REPORT) return false;
    return true;
  }, [viewMode]);

  function setOriginalView() {
    setViewMode(VIEW.ORIGINAL);
  }

  function setExpandReportView() {
    setViewMode(VIEW.REPORT);
  }

  function setExpandChatView() {
    setViewMode(VIEW.CHAT);
  }

  const layoutClassName = useMemo(() => {
    const withSidebar = sidebarVisible ? "with-sidebar" : "no-sidebar";
    if (showReportPanel && showChatPanel) return `layout ${withSidebar} two-panels`;
    if (showReportPanel) return `layout ${withSidebar} report-only`;
    if (showChatPanel) return `layout ${withSidebar} chat-only`;
    return `layout ${withSidebar} empty`;
  }, [sidebarVisible, showReportPanel, showChatPanel]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-left">
          <button
            className="icon-btn"
            title="Toggle Reports"
            onClick={() => setSidebarVisible((v) => !v)}
          >
            📚
          </button>
          <h1 className="app-title">IntelligentReport</h1>
        </div>
        <div className="view-controls">
          <button onClick={setOriginalView}>Original View</button>
          <button onClick={setExpandReportView}>Expand Report</button>
          <button onClick={setExpandChatView}>Expand Chat</button>
        </div>
      </header>

      <div className={layoutClassName}>
        {sidebarVisible && (
          <aside className="sidebar">
            <div className="sidebar-head">
              <h2>Reports</h2>
              <button onClick={createReport}>New Report</button>
            </div>
            <ul>
              {reports.map((r) => (
                <li key={r.id}>
                  <button
                    className={r.id === activeReportId ? "active" : ""}
                    onClick={() => setActiveReportId(r.id)}
                  >
                    {r.title}
                  </button>
                </li>
              ))}
            </ul>
          </aside>
        )}

        {showReportPanel && (
          <section className="panel report-panel">
            <div className="panel-head">
              <h2>Report Preview</h2>
            </div>
            <div className="panel-content markdown-content">
              <ReactMarkdown>{markdown}</ReactMarkdown>
            </div>
          </section>
        )}

        {showChatPanel && (
          <section className="panel chat-panel">
            <div className="panel-head">
              <h2>Chat</h2>
            </div>
            <div className="chat-input">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask to refine the report..."
                onKeyDown={(e) => {
                  if (e.key === "Enter") sendMessage();
                }}
              />
              <button onClick={sendMessage}>Send</button>
            </div>
            <div className="panel-content chat-messages">
              {messages.map((msg) => (
                <div key={msg.id} className={`message ${msg.role}`}>
                  <strong>{msg.role}:</strong>{" "}
                  {msg.status === "pending" ? (
                    "Thinking..."
                  ) : (
                    <ReactMarkdown>{msg.content || ""}</ReactMarkdown>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
