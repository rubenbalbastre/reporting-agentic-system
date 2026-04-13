import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

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
  const [markdown, setMarkdown] = useState("# Select or create a report");

  const [sidebarVisible, setSidebarVisible] = useState(true);
  const [viewMode, setViewMode] = useState(VIEW.ORIGINAL);
  const [teachModalOpen, setTeachModalOpen] = useState(false);
  const [teachInput, setTeachInput] = useState("");
  const [teachStatus, setTeachStatus] = useState(null);
  const [teachLoading, setTeachLoading] = useState(false);
  const [skills, setSkills] = useState([]);
  const [skillsLoading, setSkillsLoading] = useState(false);
  const [showSkills, setShowSkills] = useState(false);

  useEffect(() => {
    loadReports();
  }, []);

  useEffect(() => {
    if (activeReportId) {
      loadMessages(activeReportId);
      loadReportMarkdown(activeReportId);
    } else {
      setMarkdown("# Select or create a report");
    }
  }, [activeReportId]);

  useEffect(() => {
    if (!teachModalOpen) {
      setShowSkills(false);
      return;
    }
    if (showSkills) loadSkills();
  }, [teachModalOpen, showSkills]);

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

  async function loadReportMarkdown(reportId) {
    const res = await fetch(`${API_BASE}/reports/${reportId}/markdown`);
    const data = await res.json();
    if (!res.ok) {
      setMarkdown("# Failed to load report preview");
      return;
    }
    setMarkdown(data.content || "");
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
    await loadReportMarkdown(created.id);
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
    await loadReportMarkdown(reportId);

    if (!res.ok) {
      alert(data.detail || "Failed to send message");
      return;
    }
  }

  async function submitTeachAgent() {
    const content = teachInput.trim();
    if (!content || teachLoading) return;

    setTeachLoading(true);
    setTeachStatus(null);
    try {
      const res = await fetch(`${API_BASE}/agent/teach`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      });
      const data = await res.json();
      if (!res.ok) {
        setTeachStatus({
          type: "error",
          text: data.detail || "Failed to create skill",
        });
        return;
      }

      setTeachStatus({
        type: "success",
        text: `Saved as ${data.skill_filename}`,
      });
      setTeachInput("");
      if (showSkills) await loadSkills();
    } catch (_err) {
      setTeachStatus({
        type: "error",
        text: "Network error while creating skill",
      });
    } finally {
      setTeachLoading(false);
    }
  }

  async function loadSkills() {
    setSkillsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/agent/skills`);
      const data = await res.json();
      if (!res.ok) {
        setSkills([]);
        return;
      }
      setSkills(Array.isArray(data) ? data : []);
    } catch (_err) {
      setSkills([]);
    } finally {
      setSkillsLoading(false);
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

  const activeReportTitle = useMemo(() => {
    if (!activeReportId) return null;
    const active = reports.find((r) => r.id === activeReportId);
    return active?.title || null;
  }, [reports, activeReportId]);

  function resolveMarkdownAssetUrl(src) {
    if (!src) return "";
    if (src.startsWith("/reports/")) return `${API_BASE}${src}`;
    return src;
  }

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
          <h1 className="app-title">
            <span className="app-title-brand">Intelligent Report</span>
            {activeReportTitle ? (
              <span className="app-title-report"> {activeReportTitle}</span>
            ) : null}
          </h1>
        </div>
        <div className="view-controls">
          <button className="teach-btn" onClick={() => setTeachModalOpen(true)}>
            Teach the Agent
          </button>
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
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  img: ({ src, alt }) => (
                    <img src={resolveMarkdownAssetUrl(src)} alt={alt || ""} />
                  ),
                }}
              >
                {markdown}
              </ReactMarkdown>
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
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.content || ""}
                    </ReactMarkdown>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}
      </div>

      {teachModalOpen && (
        <div
          className="modal-backdrop"
          onClick={() => setTeachModalOpen(false)}
          role="presentation"
        >
          <section
            className="teach-modal"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="Teach the Agent"
          >
            <div className="panel-head">
              <h2>Teach the Agent</h2>
              <button onClick={() => setTeachModalOpen(false)}>Close</button>
            </div>
            <div className="panel-content teach-modal-content">
              <div className="teach-actions teach-actions-left">
                <button onClick={() => setShowSkills((v) => !v)}>
                  {showSkills ? "Hide learnt skills" : "Show learnt skills"}
                </button>
              </div>
              {showSkills && (
                <div className="skills-box">
                  <h3>Existing Skills</h3>
                  {skillsLoading ? (
                    <div className="skills-empty">Loading skills...</div>
                  ) : skills.length === 0 ? (
                    <div className="skills-empty">No skills found yet.</div>
                  ) : (
                    <ul className="skills-list">
                      {skills.map((skill) => (
                        <li key={skill.skill_id} className="skills-item">
                          <div className="skills-item-name">{skill.name}</div>
                          <div className="skills-item-desc">
                            {skill.description || "No description"}
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
              <div className="message user">
                <strong>You:</strong> Describe a new behavior you want the main agent
                to follow.
              </div>
              <textarea
                value={teachInput}
                onChange={(e) => setTeachInput(e.target.value)}
                placeholder="Example: Always include a short executive summary with 3 bullet points."
                rows={7}
              />
              <div className="teach-actions">
                <button onClick={submitTeachAgent} disabled={teachLoading}>
                  {teachLoading ? "Saving..." : "Save as Skill"}
                </button>
              </div>
              {teachStatus && (
                <div className={`teach-status ${teachStatus.type}`}>
                  {teachStatus.text}
                </div>
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
