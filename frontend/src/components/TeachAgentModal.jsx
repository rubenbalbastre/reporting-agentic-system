import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, Eye, EyeOff, FileText, Folder, Pencil, Plus, Sparkles, SquarePen, Trash2 } from "lucide-react";
import ConfirmModal from "./ConfirmModal";
import PromptModal from "./PromptModal";
import { formatMessageTime } from "../utils/datetime";

const TITLE_KEY = "reportingagent:skill-conversation-titles";
const SKILL_TITLE_KEY = "reportingagent:skill-display-titles";

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

function buildTree(paths) {
  const root = { name: "", path: "", type: "dir", children: new Map() };
  for (const raw of paths) {
    const normalized = String(raw || "").replace(/\/+$/, "");
    if (!normalized) continue;
    const parts = normalized.split("/").filter(Boolean);
    let node = root;
    let acc = "";
    for (let i = 0; i < parts.length; i += 1) {
      const part = parts[i];
      acc = acc ? `${acc}/${part}` : part;
      const isLeaf = i === parts.length - 1;
      const isDir = !isLeaf ? true : String(raw).endsWith("/");
      if (!node.children.has(part)) {
        node.children.set(part, {
          name: part,
          path: acc,
          type: isDir ? "dir" : "file",
          children: new Map(),
        });
      }
      node = node.children.get(part);
      if (isDir) node.type = "dir";
    }
  }
  return root;
}

function sortNodes(nodes) {
  return [...nodes].sort((a, b) => {
    if (a.type !== b.type) return a.type === "dir" ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
}

function FileTree({ node, depth = 0 }) {
  const children = sortNodes(node.children.values());
  if (!children.length) return null;
  return (
    <ul className="skill-tree-level" data-depth={depth}>
      {children.map((child) => {
        const isSkillMd = child.type === "file" && child.name.toLowerCase() === "skill.md";
        return (
          <li key={child.path} className={`skill-tree-item ${isSkillMd ? "skill-md" : ""}`}>
            <div className="skill-tree-row" style={{ paddingLeft: `${depth * 14}px` }}>
              {child.type === "dir" ? (
                <Folder size={14} strokeWidth={2} aria-hidden="true" />
              ) : (
                <FileText size={14} strokeWidth={2} aria-hidden="true" />
              )}
              <span>{child.name}</span>
            </div>
            {child.type === "dir" ? <FileTree node={child} depth={depth + 1} /> : null}
          </li>
        );
      })}
    </ul>
  );
}

export default function TeachAgentModal({
  open,
  mode = "draft",
  skills,
  skillsLoading,
  activeSkillId,
  createSkillLoading,
  deleteSkillLoading,
  skillConversations,
  activeSkillConversationId,
  skillMessages,
  skillMarkdown,
  skillFiles,
  teachInput,
  teachLoading,
  publishLoading,
  openDraftLoading,
  activeSkillIsPublished,
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
  onOpenSkillInDraft,
}) {
  if (!open) return null;

  const [skillsSidebarHidden, setSkillsSidebarHidden] = useState(false);
  const [skillDeleteOpen, setSkillDeleteOpen] = useState(false);
  const [renameConversationOpen, setRenameConversationOpen] = useState(false);
  const [editSkillTitleOpen, setEditSkillTitleOpen] = useState(false);
  const [skillTitles, setSkillTitles] = useState(() => loadStoredSkillTitles());
  const [conversationTitles, setConversationTitles] = useState(() => loadStoredTitles());
  const isSkillEditingView = !!activeSkillId;
  const showExploreSidebar = !skillsSidebarHidden;
  const activeSkill = skills.find((skill) => skill.id === activeSkillId) || null;
  const activeSkillTitle = activeSkill ? (skillTitles[activeSkill.id] || "") : "";
  const safeSkillMessages = Array.isArray(skillMessages) ? skillMessages : [];
  const safeSkillFiles = Array.isArray(skillFiles) ? skillFiles : [];
  const skillFilesTree = useMemo(() => buildTree(safeSkillFiles), [safeSkillFiles]);

  const isPublished = (skill) => {
    const path = (skill?.skill_md_path || "").toLowerCase();
    return path.includes("/skills/") && !path.includes("/skills_drafts/");
  };

  const draftSkills = useMemo(() => skills.filter((s) => !isPublished(s)), [skills]);
  const publishedSkills = useMemo(() => skills.filter((s) => isPublished(s)), [skills]);
  const skillsPanel = mode === "published" ? "published" : "draft";
  const visibleSkills = skillsPanel === "published" ? publishedSkills : draftSkills;

  function handleSelectSkill(skillId) {
    onSelectSkill(skillId);
  }

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
    setRenameConversationOpen(true);
  }

  function confirmRenameSkillConversation(value) {
    if (!activeSkillConversationId) return;
    const updated = { ...conversationTitles, [activeSkillConversationId]: value };
    setConversationTitles(updated);
    saveStoredTitles(updated);
    setRenameConversationOpen(false);
  }

  function editSkillTitle() {
    if (!activeSkillId) return;
    setEditSkillTitleOpen(true);
  }

  function confirmEditSkillTitle(value) {
    if (!activeSkillId) return;
    const custom = { ...skillTitles };
    if (!value) {
      delete custom[activeSkillId];
    } else {
      custom[activeSkillId] = value;
    }
    setSkillTitles(custom);
    saveStoredSkillTitles(custom);
    setEditSkillTitleOpen(false);
  }

  const skillWorkspace = activeSkillId ? (
    <div className={`skill-workspace ${activeSkillIsPublished ? "published-only" : ""}`}>
      <section className="panel skill-markdown-panel">
        <div className="panel-head sticky-head">
          <h3>Skill Preview</h3>
          {activeSkillIsPublished ? (
            <button className="btn-secondary skill-preview-action" onClick={onOpenSkillInDraft} disabled={openDraftLoading}>
              {openDraftLoading ? "Opening..." : "Open in Draft"}
            </button>
          ) : null}
        </div>
        <div className="panel-content markdown-content">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{skillMarkdown || "# Skill markdown not published yet"}</ReactMarkdown>
        </div>
      </section>

      {activeSkillIsPublished ? (
        <section className="panel skill-files-panel">
          <div className="panel-head sticky-head">
            <h3>Skill Folder</h3>
          </div>
          <div className="panel-content skill-files-content">
            {safeSkillFiles.length === 0 ? (
              <div className="skills-empty">No files found.</div>
            ) : (
              <FileTree node={skillFilesTree} />
            )}
          </div>
        </section>
      ) : null}

      {!activeSkillIsPublished ? (
      <section className="panel skill-chat-section">
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
        <div className="panel-content teach-chat-box">
          {safeSkillMessages.length === 0 ? (
            <div className="empty-state compact">
              <Bot size={18} strokeWidth={2} aria-hidden="true" />
              <p>Describe the skill goal and constraints. Then iterate with examples, edge cases, and expected outputs.</p>
            </div>
          ) : (
            safeSkillMessages.map((msg, idx) => (
              <div key={msg?.id ?? `skill-msg-${idx}`} className={`message-wrap ${msg?.role || "assistant"}`}>
                <div className={`message ${msg?.role || "assistant"}`}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {typeof msg?.content === "string" ? msg.content : (msg?.status === "pending" ? "Thinking..." : "")}
                  </ReactMarkdown>
                </div>
                <div className="message-meta" title={msg?.created_at || ""}>{formatMessageTime(msg?.created_at)}</div>
              </div>
            ))
          )}
        </div>
        <div className="chat-input">
          <input
            value={teachInput}
            onChange={(e) => onTeachInput(e.target.value)}
            placeholder={activeSkillIsPublished ? "Open in Draft to modify this published skill" : "Describe or refine this skill..."}
            disabled={activeSkillIsPublished}
            onKeyDown={(e) => {
              if (e.key === "Enter") onSendSkillMessage();
            }}
          />
          <button className="btn-send-skill btn-primary" onClick={onSendSkillMessage} disabled={teachLoading || !activeSkillConversationId || activeSkillIsPublished}>
            {teachLoading ? "Sending..." : "Send"}
          </button>
        </div>
        <div className="teach-actions">
          <button
            className="btn-publish-skill btn-secondary"
            onClick={onPublishSkill}
            disabled={publishLoading || !activeSkillConversationId || activeSkillIsPublished}
            title="Name and description are generated when publishing the skill."
          >
            {publishLoading ? "Publishing..." : "Publish"}
          </button>
        </div>
      </section>
      ) : null}
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
              {skillsPanel === "published" ? "Skill Library" : "Teach the Agent"}
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
            <aside className="sidebar skills-sidebar">
                <div className="sidebar-head sticky-head">
                  <h3>Skills</h3>
                  <div className="sidebar-actions">
                    <button
                      className="icon-action-btn btn-ghost"
                      onClick={handleCreateSkillClick}
                      disabled={createSkillLoading || skillsPanel === "published"}
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
                      onClick={() => setSkillDeleteOpen(true)}
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
                ) : visibleSkills.length === 0 ? (
                  <div className="empty-state compact">
                    <Sparkles size={18} strokeWidth={2} aria-hidden="true" />
                    <p>
                      {skillsPanel === "draft"
                        ? "No draft skills yet. Create one to start teaching the agent."
                        : "No skills published yet."}
                    </p>
                  </div>
                ) : (
                  <ul className="skills-list">
                    {visibleSkills.map((skill) => (
                      <li
                        key={skill.id}
                        className={`skills-item ${activeSkillId === skill.id ? "active" : ""}`}
                        onClick={() => handleSelectSkill(skill.id)}
                      >
                        <div className="skills-item-name">{skillTitles[skill.id] || "Untitled Skill"}</div>
                        <div className="skills-item-desc">Name: {skill.name}</div>
                      </li>
                    ))}
                  </ul>
                )}
            </aside>
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

      <ConfirmModal
        open={skillDeleteOpen}
        title="Delete Skill"
        message="Delete this skill and all its skill conversations?"
        confirmLabel="Delete Skill"
        loading={deleteSkillLoading}
        onCancel={() => setSkillDeleteOpen(false)}
        onConfirm={async () => {
          await onDeleteSkill();
          setSkillDeleteOpen(false);
        }}
      />

      <PromptModal
        open={renameConversationOpen}
        title="Rename Skill Conversation"
        label="Conversation name"
        initialValue={
          skillConversationOptions.find((c) => c.id === activeSkillConversationId)?.displayName || "Skill Conversation"
        }
        confirmLabel="Save"
        onCancel={() => setRenameConversationOpen(false)}
        onConfirm={confirmRenameSkillConversation}
      />

      <PromptModal
        open={editSkillTitleOpen}
        title="Edit Skill Title"
        label="Skill title"
        initialValue={activeSkillTitle || ""}
        confirmLabel="Save"
        onCancel={() => setEditSkillTitleOpen(false)}
        onConfirm={confirmEditSkillTitle}
      />
    </div>
  );
}
