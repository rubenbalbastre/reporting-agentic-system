import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, Pencil, SquarePen } from "lucide-react";
import { formatMessageTime } from "../utils/datetime";

const TITLE_KEY = "reportingagent:conversation-titles";

function loadStoredTitles() {
  try {
    return JSON.parse(localStorage.getItem(TITLE_KEY) || "{}");
  } catch (_err) {
    return {};
  }
}

function saveStoredTitles(map) {
  localStorage.setItem(TITLE_KEY, JSON.stringify(map));
}

export default function ReportChatPanel({
  activeReportId,
  activeConversationId,
  conversations,
  input,
  messages,
  onInputChange,
  onSendMessage,
  onConversationChange,
  onCreateConversation,
}) {
  const hasActiveConversation = Boolean(activeConversationId);
  const showEmptyState = !activeReportId || messages.length === 0;
  const [conversationTitles, setConversationTitles] = useState(() => loadStoredTitles());

  const conversationOptions = useMemo(() => {
    return conversations.map((c, idx) => {
      const fallback = c.title || `Conversation ${idx + 1}`;
      const name = conversationTitles[c.id] || fallback;
      return { ...c, displayName: name };
    });
  }, [conversations, conversationTitles]);

  function renameConversation() {
    if (!activeConversationId) return;
    const current = conversationOptions.find((c) => c.id === activeConversationId)?.displayName || "Conversation";
    const next = window.prompt("Rename conversation", current);
    if (next === null) return;
    const value = next.trim();
    if (!value) return;
    const updated = { ...conversationTitles, [activeConversationId]: value };
    setConversationTitles(updated);
    saveStoredTitles(updated);
  }

  return (
    <section className="panel chat-panel">
      <div className="panel-head">
        <h2>Chat</h2>
        <div className="conversation-controls">
          <select
            value={activeConversationId || ""}
            onChange={(e) => onConversationChange(Number(e.target.value))}
            disabled={!activeReportId || conversations.length === 0}
          >
            {conversations.length === 0 ? (
              <option value="">No conversations</option>
            ) : (
              conversationOptions.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.displayName}
                </option>
              ))
            )}
          </select>
          <button
            className="icon-action-btn btn-ghost"
            onClick={renameConversation}
            disabled={!activeConversationId}
            title="Rename conversation"
            aria-label="Rename conversation"
          >
            <SquarePen size={16} strokeWidth={2} aria-hidden="true" />
          </button>
          <button
            className="icon-action-btn btn-ghost"
            onClick={onCreateConversation}
            disabled={!activeReportId}
            title="New conversation"
            aria-label="New conversation"
          >
            <Pencil size={16} strokeWidth={2} aria-hidden="true" />
          </button>
        </div>
      </div>
      <div className="panel-content chat-messages">
        {showEmptyState ? (
          <div className="empty-state">
            <Bot size={18} strokeWidth={2} aria-hidden="true" />
            <p>
              {!activeReportId
                ? "Select or create a report first."
                : "Ask the agent to improve the report. Try: refine sections, add analyses, or request new charts."}
            </p>
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className={`message-wrap ${msg.role}`}>
              <div className={`message ${msg.role}`}>
                {msg.status === "pending" ? (
                  "Thinking..."
                ) : (
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content || ""}</ReactMarkdown>
                )}
              </div>
              <div className="message-meta" title={msg.created_at || ""}>{formatMessageTime(msg.created_at)}</div>
            </div>
          ))
        )}
      </div>
      <div className="chat-input">
        <input
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          placeholder="Ask to refine the report..."
          onKeyDown={(e) => {
            if (e.key === "Enter") onSendMessage();
          }}
          disabled={!hasActiveConversation}
        />
        <button className="btn-send-report btn-primary" onClick={onSendMessage} disabled={!hasActiveConversation}>Send</button>
      </div>
    </section>
  );
}
