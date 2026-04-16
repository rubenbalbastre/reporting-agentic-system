import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, Eye, EyeOff, Pencil, Plus, Sparkles, SquarePen, Trash2 } from "lucide-react";

const TITLE_KEY = "reportingagent:skill-conversation-titles";
const SKILL_TITLE_KEY = "reportingagent:skill-display-titles";

function formatTime(dateText) {
  if (!dateText) return "";
  const d = new Date(dateText);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

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

function loadStoredSkillTitles() {
  try {
    return JSON.parse(localStorage.getItem(SKILL_TITLE_KEY) || "{}");
  } catch (_err) {
    return {};
  }
}

function saveStoredSkillTitles(map) {
  localStorage.setItem(SKILL_TITLE_KEY, JSON.stringify(map));
}

export default function TeachAgentModal({
  open,
  skills,
  skillsLoading,
  activeSkillId,
  createSkillLoading,
  deleteSkillLoading,
  skillConversations,
  activeSkillConversationId,
  skillMessages,
  skillMarkdown,
  teachInput,
  teachLoading,
  publishLoading,
  teachStatus,
  onClose,
  onSelectSkill,
  onCreateSkill,
  onDeleteSkill,
  onConversationChange,
  onCreateSkillConversation,
  onTeachInput,
  onSendSkillMessage,
  onPublishSkill,
}) {
  if (!open) return null;

  const [skillsSidebarHidden, setSkillsSidebarHidden] = useState(false);
  const [skillTitles, setSkillTitles] = useState(() => loadStoredSkillTitles());
  const [conversationTitles, setConversationTitles] = useState(() => loadStoredTitles());
  const isSkillEditingView = !!activeSkillId;
  const showExploreSidebar = !skillsSidebarHidden;
  const activeSkill = skills.find((skill) => skill.id === activeSkillId) || null;
  const activeSkillTitle = activeSkill ? (skillTitles[activeSkill.id] || "") : "";

  const skillConversationOptions = useMemo(() => {
    return skillConversations.map((c, idx) => {
      const fallback = c.title || `Skill Conversation ${idx + 1}`;
      return { ...c, displayName: conversationTitles[c.id] || fallback };
    });
  }, [skillConversations, conversationTitles]);

  function handleCreateSkillClick() {
    setSkillsSidebarHidden(true);
    onCreateSkill();
  }

  function renameSkillConversation() {
    if (!activeSkillConversationId) return;
    const current =
      skillConversationOptions.find((c) => c.id === activeSkillConversationId)?.displayName || "Skill Conversation";
    const next = window.prompt("Rename skill conversation", current);
    if (next === null) return;
    const value = next.trim();
    if (!value) return;
    const updated = { ...conversationTitles, [activeSkillConversationId]: value };
    setConversationTitles(updated);
    saveStoredTitles(updated);
  }

  function editSkillTitle() {
    if (!activeSkillId) return;
    const current = activeSkillTitle || "";
    const next = window.prompt("Skill title", current);
    if (next === null) return;
    const value = next.trim();
    const custom = { ...skillTitles };
    if (!value) {
      delete custom[activeSkillId];
    } else {
      custom[activeSkillId] = value;
    }
    setSkillTitles(custom);
    saveStoredSkillTitles(custom);
  }

  const skillWorkspace = activeSkillId ? (
    <div className="skill-workspace">
      <div className="skill-markdown-panel">
        <div className="panel-head sticky-head">
          <h3>Skill Preview</h3>
        </div>
        <div className="panel-content markdown-content">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{skillMarkdown || "# Skill markdown not published yet"}</ReactMarkdown>
        </div>
      </div>

      <div className="skill-chat-section">
        <div className="teach-editor-info" title="Name and description are generated when publishing the skill.">
          Name and description are generated when publishing.
        </div>
        <div className="panel-head sticky-head">
          <h3>Working Chat</h3>
          <div className="teach-actions teach-actions-left">
            <select
              value={activeSkillConversationId || ""}
              onChange={(e) => onConversationChange(Number(e.target.value))}
              disabled={skillConversations.length === 0}
            >
              {skillConversations.length === 0 ? (
                <option value="">No conversations</option>
              ) : (
                skillConversationOptions.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.displayName}
                  </option>
                ))
              )}
            </select>
            <button
              className="icon-action-btn btn-ghost"
              onClick={renameSkillConversation}
              disabled={!activeSkillConversationId}
              title="Rename skill conversation"
              aria-label="Rename skill conversation"
            >
              <SquarePen size={16} strokeWidth={2} aria-hidden="true" />
            </button>
            <button
              className="icon-action-btn btn-ghost"
              onClick={onCreateSkillConversation}
              title="New skill conversation"
              aria-label="New skill conversation"
            >
              <Pencil size={16} strokeWidth={2} aria-hidden="true" />
            </button>
          </div>
        </div>
        <div className="teach-chat-box">
          {skillMessages.length === 0 ? (
            <div className="empty-state compact">
              <Bot size={18} strokeWidth={2} aria-hidden="true" />
              <p>Describe the skill goal and constraints. Then iterate with examples, edge cases, and expected outputs.</p>
            </div>
          ) : (
            skillMessages.map((msg) => (
              <div key={msg.id} className={`message-wrap ${msg.role}`}>
                <div className={`message ${msg.role}`}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content || (msg.status === "pending" ? "Thinking..." : "")}</ReactMarkdown>
                </div>
                <div className="message-meta">{formatTime(msg.created_at)}</div>
              </div>
            ))
          )}
        </div>
        <div className="chat-input">
          <input
            value={teachInput}
            onChange={(e) => onTeachInput(e.target.value)}
            placeholder="Describe or refine this skill..."
            onKeyDown={(e) => {
              if (e.key === "Enter") onSendSkillMessage();
            }}
          />
          <button className="btn-send-skill btn-primary" onClick={onSendSkillMessage} disabled={teachLoading || !activeSkillConversationId}>
            {teachLoading ? "Sending..." : "Send"}
          </button>
        </div>
        <div className="teach-actions">
          <button
            className="btn-publish-skill btn-secondary"
            onClick={onPublishSkill}
            disabled={publishLoading || !activeSkillConversationId}
          >
            {publishLoading ? "Publishing..." : "Publish Skill"}
          </button>
        </div>
      </div>
    </div>
  ) : null;

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <section
        className="teach-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Teach the Agent"
      >
        <div className="panel-head">
          <div className="teach-head-left">
            <button
              className="icon-action-btn skill-toggle-btn btn-ghost"
              onClick={() => setSkillsSidebarHidden((v) => !v)}
              title={skillsSidebarHidden ? "Show skills panel" : "Hide skills panel"}
              aria-label={skillsSidebarHidden ? "Show skills panel" : "Hide skills panel"}
            >
              {skillsSidebarHidden ? (
                <Eye size={16} strokeWidth={2} aria-hidden="true" />
              ) : (
                <EyeOff size={16} strokeWidth={2} aria-hidden="true" />
              )}
            </button>
            <h2>
              Teach the Agent
              {isSkillEditingView && activeSkill ? (
                <>
                  : <span className="teach-title-skill">{activeSkillTitle || "Untitled Skill"}</span>
                </>
              ) : null}
            </h2>
          </div>
          <div className="teach-header-actions">
            <button className="btn-ghost" onClick={onClose}>Close</button>
          </div>
        </div>

        <div className="panel-content teach-modal-content">
          <div className={`teach-explore-layout ${showExploreSidebar ? "" : "sidebar-hidden"}`}>
            <div className="skills-box skills-sidebar">
                <div className="sidebar-head sticky-head">
                  <h3>Skills</h3>
                  <div className="sidebar-actions">
                    <button
                      className="icon-action-btn btn-ghost"
                      onClick={handleCreateSkillClick}
                      disabled={createSkillLoading}
                      title={createSkillLoading ? "Creating skill..." : "Create new skill"}
                      aria-label={createSkillLoading ? "Creating skill" : "Create new skill"}
                    >
                      {createSkillLoading ? "…" : <Plus size={16} strokeWidth={2} aria-hidden="true" />}
                    </button>
                    <button
                      className="icon-action-btn btn-ghost"
                      onClick={editSkillTitle}
                      disabled={!isSkillEditingView}
                      title="Edit skill title"
                      aria-label="Edit skill title"
                    >
                      <SquarePen size={16} strokeWidth={2} aria-hidden="true" />
                    </button>
                    <button
                      className="btn-delete-skill icon-danger-btn"
                      onClick={() => {
                        if (!isSkillEditingView) return;
                        const confirmed = window.confirm("Delete this skill and all its skill conversations?");
                        if (confirmed) onDeleteSkill();
                      }}
                      disabled={!isSkillEditingView || deleteSkillLoading}
                      title={deleteSkillLoading ? "Deleting skill..." : "Delete skill"}
                      aria-label={deleteSkillLoading ? "Deleting skill" : "Delete skill"}
                    >
                      {deleteSkillLoading ? "…" : <Trash2 size={16} strokeWidth={2} aria-hidden="true" />}
                    </button>
                  </div>
                </div>
                {skillsLoading ? (
                  <div className="skills-empty">Loading skills...</div>
                ) : skills.length === 0 ? (
                  <div className="empty-state compact">
                    <Sparkles size={18} strokeWidth={2} aria-hidden="true" />
                    <p>No skills yet. Create one to start teaching the agent.</p>
                  </div>
                ) : (
                  <ul className="skills-list">
                    {skills.map((skill) => (
                      <li
                        key={skill.id}
                        className={`skills-item ${activeSkillId === skill.id ? "active" : ""}`}
                        onClick={() => onSelectSkill(skill.id)}
                      >
                        <div className="skills-item-name">{skillTitles[skill.id] || "Untitled Skill"}</div>
                        <div className="skills-item-desc">Name: {skill.name}</div>
                      </li>
                    ))}
                  </ul>
                )}
            </div>
            <div className="teach-explore-main">
              {isSkillEditingView ? (
                skillWorkspace
              ) : (
                <div className="empty-state skill-empty-state">
                  <Bot size={18} strokeWidth={2} aria-hidden="true" />
                  <p>Select a skill or create a new one to begin.</p>
                </div>
              )}
            </div>
          </div>

          {teachStatus && <div className={`teach-status ${teachStatus.type}`}>{teachStatus.text}</div>}
        </div>
      </section>
    </div>
  );
}
