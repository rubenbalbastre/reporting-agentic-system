import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import ReportChatPanel from "./components/ReportChatPanel";
import TeachAgentModal from "./components/TeachAgentModal";
import { api } from "./api";
import { useReportChat, VIEW } from "./hooks/useReportChat";
import { useSkillTeaching } from "./hooks/useSkillTeaching";

export default function App() {
  const report = useReportChat();
  const skill = useSkillTeaching();

  function resolveMarkdownAssetUrl(src) {
    if (!src) return "";
    if (src.startsWith("/reports/")) return `${api.API_BASE}${src}`;
    return src;
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-left">
          <button className="icon-btn" title="Toggle Reports" onClick={() => report.setSidebarVisible((v) => !v)}>
            📚
          </button>
          <h1 className="app-title">
            <span className="app-title-brand">Intelligent Report</span>
            {report.activeReportTitle ? <span className="app-title-report"> {report.activeReportTitle}</span> : null}
          </h1>
        </div>
        <div className="view-controls">
          <button className="teach-btn" onClick={() => skill.setTeachModalOpen(true)}>
            Teach the Agent
          </button>
          <button onClick={() => report.setViewMode(VIEW.ORIGINAL)}>Original View</button>
          <button onClick={() => report.setViewMode(VIEW.REPORT)}>Expand Report</button>
          <button onClick={() => report.setViewMode(VIEW.CHAT)}>Expand Chat</button>
        </div>
      </header>

      <div className={report.layoutClassName}>
        {report.sidebarVisible && (
          <aside className="sidebar">
            <div className="sidebar-head">
              <h2>Reports</h2>
              <div className="sidebar-actions">
                <button
                  className="icon-action-btn"
                  onClick={report.createReport}
                  title="New report"
                  aria-label="New report"
                >
                  +
                </button>
                <button
                  className="btn-delete-report icon-danger-btn"
                  onClick={() => {
                    if (!report.activeReportId) return;
                    const confirmed = window.confirm("Delete this report and all its conversations?");
                    if (confirmed) report.deleteReport();
                  }}
                  disabled={!report.activeReportId || report.deleteReportLoading}
                  title={report.deleteReportLoading ? "Deleting report..." : "Delete report"}
                  aria-label={report.deleteReportLoading ? "Deleting report" : "Delete report"}
                >
                  {report.deleteReportLoading ? "…" : "🗑"}
                </button>
              </div>
            </div>
            <ul>
              {report.reports.map((r) => (
                <li key={r.id}>
                  <button
                    className={r.id === report.activeReportId ? "active" : ""}
                    onClick={() => report.setActiveReportId(r.id)}
                  >
                    {r.title}
                  </button>
                </li>
              ))}
            </ul>
          </aside>
        )}

        {report.showReportPanel && (
          <section className="panel report-panel">
            <div className="panel-head">
              <h2>Report Preview</h2>
            </div>
            <div className="panel-content markdown-content">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  img: ({ src, alt }) => <img src={resolveMarkdownAssetUrl(src)} alt={alt || ""} />,
                }}
              >
                {report.markdown}
              </ReactMarkdown>
            </div>
          </section>
        )}

        {report.showChatPanel && (
          <ReportChatPanel
            activeReportId={report.activeReportId}
            activeConversationId={report.activeConversationId}
            conversations={report.conversations}
            input={report.input}
            messages={report.messages}
            onInputChange={report.setInput}
            onSendMessage={report.sendMessage}
            onConversationChange={report.setActiveConversationId}
            onCreateConversation={report.createConversation}
          />
        )}
      </div>

      <TeachAgentModal
        open={skill.teachModalOpen}
        skills={skill.skills}
        skillsLoading={skill.skillsLoading}
        activeSkillId={skill.activeSkillId}
        createSkillLoading={skill.createSkillLoading}
        deleteSkillLoading={skill.deleteSkillLoading}
        skillConversations={skill.skillConversations}
        activeSkillConversationId={skill.activeSkillConversationId}
        skillMessages={skill.skillMessages}
        skillMarkdown={skill.skillMarkdown}
        teachInput={skill.teachInput}
        teachLoading={skill.teachLoading}
        publishLoading={skill.publishLoading}
        teachStatus={skill.teachStatus}
        onClose={() => skill.setTeachModalOpen(false)}
        onSelectSkill={skill.setActiveSkillId}
        onCreateSkill={skill.createSkill}
        onDeleteSkill={skill.deleteSkill}
        onConversationChange={skill.setActiveSkillConversationId}
        onCreateSkillConversation={skill.createSkillConversation}
        onTeachInput={skill.setTeachInput}
        onSendSkillMessage={skill.sendSkillMessage}
        onPublishSkill={skill.publishSkill}
      />
    </div>
  );
}
