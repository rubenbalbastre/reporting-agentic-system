import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, Pencil } from "lucide-react";

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
  const showEmptyState = !activeReportId || messages.length === 0;

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
              conversations.map((c) => (
                <option key={c.id} value={c.id}>
                  Conversation #{c.id}
                </option>
              ))
            )}
          </select>
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
            <p>{!activeReportId ? "Select a report to start chatting." : "Start your first conversation for this report."}</p>
            <button className="btn-secondary" onClick={onCreateConversation} disabled={!activeReportId}>
              New Conversation
            </button>
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className={`message ${msg.role}`}>
              {msg.status === "pending" ? (
                "Thinking..."
              ) : (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content || ""}</ReactMarkdown>
              )}
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
          disabled={!activeReportId}
        />
        <button className="btn-send-report btn-primary" onClick={onSendMessage} disabled={!activeReportId}>Send</button>
      </div>
    </section>
  );
}
