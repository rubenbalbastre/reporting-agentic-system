import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function TeachAgentModal({
  open,
  teachMode,
  skills,
  skillsLoading,
  activeSkillId,
  newSkillName,
  createSkillLoading,
  skillConversations,
  activeSkillConversationId,
  skillMessages,
  skillMarkdown,
  teachInput,
  teachLoading,
  publishLoading,
  teachStatus,
  onClose,
  onSetTeachMode,
  onSelectSkill,
  onNewSkillName,
  onCreateSkill,
  onConversationChange,
  onCreateSkillConversation,
  onTeachInput,
  onSendSkillMessage,
  onPublishSkill,
}) {
  if (!open) return null;
  const [skillsSidebarHidden, setSkillsSidebarHidden] = useState(false);
  const isExploreMode = teachMode === "explore";
  const isSkillEditingView = isExploreMode && !!activeSkillId;
  const showExploreSidebar = isSkillEditingView && !skillsSidebarHidden;

  useEffect(() => {
    if (!isSkillEditingView) {
      setSkillsSidebarHidden(false);
    }
  }, [isSkillEditingView]);

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
          <button onClick={onCreateSkillConversation}>New Skill Conversation</button>
        </div>
        <div className="teach-chat-box">
          {skillMessages.map((msg) => (
            <div key={msg.id} className={`message ${msg.role}`}>
              <strong>{msg.role}:</strong> <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content || ""}</ReactMarkdown>
            </div>
          ))}
        </div>
        <textarea
          value={teachInput}
          onChange={(e) => onTeachInput(e.target.value)}
          placeholder="Describe or refine this skill..."
          rows={4}
        />
        <div className="teach-actions">
          <button className="btn-send-skill" onClick={onSendSkillMessage} disabled={teachLoading || !activeSkillConversationId}>
            {teachLoading ? "Sending..." : "Send"}
          </button>
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
          <h2>Teach the Agent</h2>
          <div className="teach-header-actions">
            {isSkillEditingView && (
              <button onClick={() => setSkillsSidebarHidden((v) => !v)}>
                {skillsSidebarHidden ? "Show Skills" : "Hide Skills"}
              </button>
            )}
            <button onClick={onClose}>Close</button>
          </div>
        </div>
        <div className="panel-content teach-modal-content">
          {!isSkillEditingView && (
            <div className="teach-mode-grid">
              <button
                className={`teach-mode-btn teach-mode-explore ${teachMode === "explore" ? "active" : ""}`}
                onClick={() => onSetTeachMode("explore")}
              >
                Explore Existing Skills
              </button>
              <button
                className={`teach-mode-btn teach-mode-create ${teachMode === "create" ? "active" : ""}`}
                onClick={() => onSetTeachMode("create")}
              >
                Create New Skill
              </button>
            </div>
          )}

          {isExploreMode && !isSkillEditingView && (
            <div className="skills-box">
              <h3>Existing Skills</h3>
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
                      <div className="skills-item-desc">
                        {skill.description || "No description yet (publish to generate)"}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {teachMode === "create" && (
            <div className="teach-create-row">
              <input
                value={newSkillName}
                onChange={(e) => onNewSkillName(e.target.value)}
                placeholder="New skill name..."
              />
              <button className="btn-create-skill" onClick={onCreateSkill} disabled={createSkillLoading}>
                {createSkillLoading ? "Creating..." : "Create Skill"}
              </button>
            </div>
          )}

          {isSkillEditingView && (
            <div className={`teach-explore-layout ${showExploreSidebar ? "" : "sidebar-hidden"}`}>
              {showExploreSidebar && (
                <div className="skills-box skills-sidebar">
                  <h3>Existing Skills</h3>
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
              <div className="teach-explore-main">{skillWorkspace}</div>
            </div>
          )}

          {!isSkillEditingView && skillWorkspace}

          {teachStatus && <div className={`teach-status ${teachStatus.type}`}>{teachStatus.text}</div>}
        </div>
      </section>
    </div>
  );
}
