import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

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
  const isSkillEditingView = !!activeSkillId;
  const showExploreSidebar = !skillsSidebarHidden;
  const activeSkill = skills.find((skill) => skill.id === activeSkillId) || null;

  function handleCreateSkillClick() {
    setSkillsSidebarHidden(true);
    onCreateSkill();
  }

  const skillWorkspace = activeSkillId ? (
    <div className="skill-workspace">
      <div className="skill-markdown-panel">
        <div className="panel-head">
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
        <div className="teach-actions teach-actions-left">
          <select
            value={activeSkillConversationId || ""}
            onChange={(e) => onConversationChange(Number(e.target.value))}
            disabled={skillConversations.length === 0}
          >
            {skillConversations.length === 0 ? (
              <option value="">No conversations</option>
            ) : (
              skillConversations.map((c) => (
                <option key={c.id} value={c.id}>
                  Skill Conversation #{c.id}
                </option>
              ))
            )}
          </select>
          <button
            className="icon-action-btn"
            onClick={onCreateSkillConversation}
            title="New skill conversation"
            aria-label="New skill conversation"
          >
            <span role="img" aria-hidden="true">✏️</span>
          </button>
        </div>
        <div className="teach-chat-box">
          {skillMessages.map((msg) => (
            <div key={msg.id} className={`message ${msg.role}`}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content || ""}</ReactMarkdown>
            </div>
          ))}
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
          <button className="btn-send-skill" onClick={onSendSkillMessage} disabled={teachLoading || !activeSkillConversationId}>
            {teachLoading ? "Sending..." : "Send"}
          </button>
        </div>
        <div className="teach-actions">
          <button
            className="btn-publish-skill"
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
          <h2>
            Teach the Agent
            {isSkillEditingView && activeSkill ? (
              <>
                : <span className="teach-title-skill">Skill {activeSkill.name}</span>
              </>
            ) : null}
          </h2>
          <div className="teach-header-actions">
            <button onClick={() => setSkillsSidebarHidden((v) => !v)}>
              {skillsSidebarHidden ? "Show Skills" : "Hide Skills"}
            </button>
            <button onClick={onClose}>Close</button>
          </div>
        </div>

        <div className="panel-content teach-modal-content">
          <div className={`teach-explore-layout ${showExploreSidebar ? "" : "sidebar-hidden"}`}>
            {showExploreSidebar && (
              <div className="skills-box skills-sidebar">
                <div className="sidebar-head">
                  <h3>Existing Skills</h3>
                  <div className="sidebar-actions">
                    <button
                      className="icon-action-btn"
                      onClick={handleCreateSkillClick}
                      disabled={createSkillLoading}
                      title={createSkillLoading ? "Creating skill..." : "Create new skill"}
                      aria-label={createSkillLoading ? "Creating skill" : "Create new skill"}
                    >
                      {createSkillLoading ? "…" : "+"}
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
                      {deleteSkillLoading ? "…" : "🗑"}
                    </button>
                  </div>
                </div>
                {skillsLoading ? (
                  <div className="skills-empty">Loading skills...</div>
                ) : skills.length === 0 ? (
                  <div className="skills-empty">No skills found yet.</div>
                ) : (
                  <ul className="skills-list">
                    {skills.map((skill) => (
                      <li
                        key={skill.id}
                        className={`skills-item ${activeSkillId === skill.id ? "active" : ""}`}
                        onClick={() => onSelectSkill(skill.id)}
                      >
                        <div className="skills-item-name">{skill.name}</div>
                        <div className="skills-item-desc">{skill.description || "No description yet (publish to generate)"}</div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
            <div className="teach-explore-main">
              {isSkillEditingView ? skillWorkspace : <div className="skills-empty skill-empty-state">Select a skill or create a new one.</div>}
            </div>
          </div>

          {teachStatus && <div className={`teach-status ${teachStatus.type}`}>{teachStatus.text}</div>}
        </div>
      </section>
    </div>
  );
}
