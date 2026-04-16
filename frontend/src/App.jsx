import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { BookOpen, Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import ReportChatPanel from "./components/ReportChatPanel";
import TeachAgentModal from "./components/TeachAgentModal";
import ConfirmModal from "./components/ConfirmModal";
import ToastStack from "./components/ToastStack";
import { api } from "./api";
import { useReportChat, VIEW } from "./hooks/useReportChat";
import { useSkillTeaching } from "./hooks/useSkillTeaching";
import { useToast } from "./hooks/useToast";

export default function App() {
  const { toasts, toast } = useToast();
  const [reportDeleteOpen, setReportDeleteOpen] = useState(false);
  const report = useReportChat(toast);
  const skill = useSkillTeaching(toast);

  function resolveMarkdownAssetUrl(src) {
    if (!src) return "";
    if (src.startsWith("/reports/")) {
      return `${api.API_BASE}${src}`;
    }

    if (report.activeReportId) {
      const rel = src.replace(/^\.\//, "").replace(/^\/+/, "");
      if (rel.startsWith("figures/")) {
        return `${api.API_BASE}/reports/${report.activeReportId}/files/${rel}`;
      }
    }

    return src;
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-main">
          <div className="topbar-left">
            <button className="icon-btn btn-ghost" title="Toggle Reports" onClick={() => report.setSidebarVisible((v) => !v)}>
              <BookOpen size={18} strokeWidth={2} aria-hidden="true" />
            </button>
            <h1 className="app-title">
              <span className="app-title-brand">Intelligent Report</span>
              {report.activeReportTitle ? <span className="app-title-report"> {report.activeReportTitle}</span> : null}
            </h1>
          </div>
          <div className="segmented-control" role="group" aria-label="View mode">
            <button
              className={report.viewMode === VIEW.ORIGINAL ? "segment active" : "segment"}
              aria-pressed={report.viewMode === VIEW.ORIGINAL}
              onClick={() => report.setViewMode(VIEW.ORIGINAL)}
            >
              Original
            </button>
            <button
              className={report.viewMode === VIEW.REPORT ? "segment active" : "segment"}
              aria-pressed={report.viewMode === VIEW.REPORT}
              onClick={() => report.setViewMode(VIEW.REPORT)}
            >
              Report
            </button>
            <button
              className={report.viewMode === VIEW.CHAT ? "segment active" : "segment"}
              aria-pressed={report.viewMode === VIEW.CHAT}
              onClick={() => report.setViewMode(VIEW.CHAT)}
            >
              Chat
            </button>
          </div>
        </div>
        <div className="topbar-utilities">
          <button className="teach-btn btn-primary" onClick={() => skill.setTeachModalOpen(true)}>
            Teach the Agent
          </button>
        </div>
      </header>

      <div className={`${report.layoutClassName} ${report.sidebarVisible ? "" : "sidebar-collapsed"}`}>
        <aside className="sidebar">
          <div className="sidebar-head">
            <h2>Reports</h2>
            <div className="sidebar-actions">
              <button
                className="icon-action-btn btn-ghost"
                onClick={report.createReport}
                title="New report"
                aria-label="New report"
              >
                <Plus size={16} strokeWidth={2} aria-hidden="true" />
              </button>
              <button
                className="icon-action-btn btn-ghost"
                onClick={report.renameReport}
                disabled={!report.activeReportId}
                title="Rename report"
                aria-label="Rename report"
              >
                <Pencil size={16} strokeWidth={2} aria-hidden="true" />
              </button>
              <button
                className="btn-delete-report icon-danger-btn"
                onClick={() => setReportDeleteOpen(true)}
                disabled={!report.activeReportId || report.deleteReportLoading}
                title={report.deleteReportLoading ? "Deleting report..." : "Delete report"}
                aria-label={report.deleteReportLoading ? "Deleting report" : "Delete report"}
              >
                {report.deleteReportLoading ? "…" : <Trash2 size={16} strokeWidth={2} aria-hidden="true" />}
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

        {report.showReportPanel && (
          <section className="panel report-panel">
            <div className="panel-head sticky-head">
              <h2>Report Preview</h2>
              <button
                className="btn-secondary"
                onClick={report.exportReportPdf}
                disabled={!report.activeReportId}
                title="Export report as PDF"
                aria-label="Export report as PDF"
              >
                Export PDF
              </button>
            </div>
            <div className="panel-content markdown-content">
              <div className="prose-container">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    img: ({ src, alt }) => <img src={resolveMarkdownAssetUrl(src)} alt={alt || ""} />,
                  }}
                >
                  {report.markdown}
                </ReactMarkdown>
              </div>
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


      <ConfirmModal
        open={reportDeleteOpen}
        title="Delete Report"
        message="Delete this report and all its conversations?"
        confirmLabel="Delete Report"
        loading={report.deleteReportLoading}
        onCancel={() => setReportDeleteOpen(false)}
        onConfirm={async () => {
          await report.deleteReport();
          setReportDeleteOpen(false);
        }}
      />

      <ToastStack toasts={toasts} onDismiss={toast.remove} />
    </div>
  );
}
