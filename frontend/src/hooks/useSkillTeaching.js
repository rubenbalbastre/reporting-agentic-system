import { useEffect, useState } from "react";
import { api } from "../api";

export function useSkillTeaching() {
  const [teachModalOpen, setTeachModalOpen] = useState(false);
  const [teachInput, setTeachInput] = useState("");
  const [teachStatus, setTeachStatus] = useState(null);
  const [teachLoading, setTeachLoading] = useState(false);

  const [skills, setSkills] = useState([]);
  const [skillsLoading, setSkillsLoading] = useState(false);
  const [createSkillLoading, setCreateSkillLoading] = useState(false);
  const [deleteSkillLoading, setDeleteSkillLoading] = useState(false);
  const [publishLoading, setPublishLoading] = useState(false);

  const [activeSkillId, setActiveSkillId] = useState(null);
  const [skillConversations, setSkillConversations] = useState([]);
  const [activeSkillConversationId, setActiveSkillConversationId] = useState(null);
  const [skillMessages, setSkillMessages] = useState([]);
  const [skillMarkdown, setSkillMarkdown] = useState("");

  useEffect(() => {
    if (!teachModalOpen) {
      setActiveSkillId(null);
      setActiveSkillConversationId(null);
      setSkillMessages([]);
      return;
    }
    loadSkills();
  }, [teachModalOpen]);

  useEffect(() => {
    if (!activeSkillId) {
      setSkillConversations([]);
      setActiveSkillConversationId(null);
      setSkillMarkdown("");
      return;
    }
    loadSkillConversations(activeSkillId);
    loadSkillMarkdown(activeSkillId);
  }, [activeSkillId]);

  useEffect(() => {
    if (!activeSkillConversationId) {
      setSkillMessages([]);
      return;
    }
    loadSkillMessages(activeSkillConversationId);
  }, [activeSkillConversationId]);

  async function loadSkills() {
    setSkillsLoading(true);
    try {
      const { ok, data } = await api.get("/skills");
      setSkills(ok && Array.isArray(data) ? data : []);
    } finally {
      setSkillsLoading(false);
    }
  }

  async function createSkill() {
    if (createSkillLoading) return;
    const name = `New Skill ${skills.length + 1}`;
    setCreateSkillLoading(true);
    setTeachStatus(null);
    try {
      const { ok, data } = await api.post("/skills", { name });
      if (!ok) {
        setTeachStatus({ type: "error", text: data.detail || "Failed to create skill" });
        return;
      }
      setTeachStatus({ type: "success", text: `Created skill ${data.name}` });
      await loadSkills();
      setActiveSkillId(data.id);
      const convs = await loadSkillConversations(data.id);
      if (convs.length) setActiveSkillConversationId(convs[0].id);
    } catch (_err) {
      setTeachStatus({
        type: "error",
        text: "Could not reach backend. Check backend is running on :8000 and DB schema is up to date (make db-init).",
      });
    } finally {
      setCreateSkillLoading(false);
    }
  }

  async function deleteSkill() {
    if (!activeSkillId || deleteSkillLoading) return;
    setDeleteSkillLoading(true);
    setTeachStatus(null);
    try {
      const { ok, data } = await api.del(`/skills/${activeSkillId}`);
      if (!ok) {
        setTeachStatus({ type: "error", text: data.detail || "Failed to delete skill" });
        return;
      }
      setTeachStatus({ type: "success", text: "Skill deleted" });
      setActiveSkillId(null);
      setActiveSkillConversationId(null);
      setSkillMessages([]);
      setSkillMarkdown("");
      await loadSkills();
    } catch (_err) {
      setTeachStatus({ type: "error", text: "Network error while deleting skill" });
    } finally {
      setDeleteSkillLoading(false);
    }
  }

  async function loadSkillConversations(skillId) {
    const { ok, data } = await api.get(`/skills/${skillId}/conversations`);
    const list = ok && Array.isArray(data) ? data : [];
    setSkillConversations(list);
    if (list.length && !list.some((c) => c.id === activeSkillConversationId)) {
      setActiveSkillConversationId(list[0].id);
    }
    return list;
  }

  async function createSkillConversation() {
    if (!activeSkillId) return;
    const { ok, data } = await api.post(`/skills/${activeSkillId}/conversations`);
    if (!ok) {
      setTeachStatus({ type: "error", text: data.detail || "Failed to create skill conversation" });
      return;
    }
    await loadSkillConversations(activeSkillId);
    setActiveSkillConversationId(data.id);
  }

  async function loadSkillMessages(skillConversationId) {
    const { ok, data } = await api.get(`/skill-conversations/${skillConversationId}/messages`);
    setSkillMessages(ok && Array.isArray(data) ? data : []);
  }

  async function loadSkillMarkdown(skillId) {
    const { ok, data } = await api.get(`/skills/${skillId}/markdown`);
    if (!ok) {
      setSkillMarkdown("# Skill markdown not published yet");
      return;
    }
    setSkillMarkdown(data.content || "");
  }

  async function sendSkillMessage() {
    if (!activeSkillConversationId || !teachInput.trim() || teachLoading) return;
    const content = teachInput.trim();
    setTeachLoading(true);
    setTeachStatus(null);
    setTeachInput("");
    try {
      const { ok, data } = await api.post(`/skill-conversations/${activeSkillConversationId}/messages`, { content });
      if (!ok) {
        setTeachStatus({ type: "error", text: data.detail || "Failed to send skill message" });
        return;
      }
      await loadSkillMessages(activeSkillConversationId);
    } catch (_err) {
      setTeachStatus({ type: "error", text: "Network error while sending skill message" });
    } finally {
      setTeachLoading(false);
    }
  }

  async function publishSkill() {
    if (!activeSkillId || !activeSkillConversationId || publishLoading) return;
    setPublishLoading(true);
    setTeachStatus(null);
    try {
      const { ok, data } = await api.post(`/skills/${activeSkillId}/publish`, {
        skill_conversation_id: activeSkillConversationId,
      });
      if (!ok) {
        setTeachStatus({ type: "error", text: data.detail || "Failed to publish skill" });
        return;
      }
      setTeachStatus({ type: "success", text: `Published ${data.name}` });
      await loadSkills();
      await loadSkillMarkdown(activeSkillId);
    } catch (_err) {
      setTeachStatus({ type: "error", text: "Network error while publishing skill" });
    } finally {
      setPublishLoading(false);
    }
  }

  return {
    teachModalOpen,
    setTeachModalOpen,
    teachInput,
    setTeachInput,
    teachStatus,
    teachLoading,
    skills,
    skillsLoading,
    createSkillLoading,
    deleteSkillLoading,
    publishLoading,
    activeSkillId,
    setActiveSkillId,
    skillConversations,
    activeSkillConversationId,
    setActiveSkillConversationId,
    skillMessages,
    skillMarkdown,
    createSkill,
    deleteSkill,
    createSkillConversation,
    sendSkillMessage,
    publishSkill,
  };
}
