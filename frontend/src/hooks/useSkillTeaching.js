import { useEffect, useState } from "react";
import { api } from "../api";

export function useSkillTeaching() {
  const [teachModalOpen, setTeachModalOpen] = useState(false);
  const [teachInput, setTeachInput] = useState("");
  const [teachStatus, setTeachStatus] = useState(null);
  const [teachLoading, setTeachLoading] = useState(false);
  const [teachExpanded, setTeachExpanded] = useState(false);
  const [teachMode, setTeachMode] = useState(null);

  const [skills, setSkills] = useState([]);
  const [skillsLoading, setSkillsLoading] = useState(false);
  const [createSkillLoading, setCreateSkillLoading] = useState(false);
  const [publishLoading, setPublishLoading] = useState(false);

  const [activeSkillId, setActiveSkillId] = useState(null);
  const [newSkillName, setNewSkillName] = useState("");
  const [skillConversations, setSkillConversations] = useState([]);
  const [activeSkillConversationId, setActiveSkillConversationId] = useState(null);
  const [skillMessages, setSkillMessages] = useState([]);

  useEffect(() => {
    if (!teachModalOpen) {
      setTeachMode(null);
      setTeachExpanded(false);
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
      return;
    }
    loadSkillConversations(activeSkillId);
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
    const name = newSkillName.trim() || `New Skill ${skills.length + 1}`;
    setCreateSkillLoading(true);
    setTeachStatus(null);
    try {
      const { ok, data } = await api.post("/skills", { name });
      if (!ok) {
        setTeachStatus({ type: "error", text: data.detail || "Failed to create skill" });
        return;
      }
      setTeachStatus({ type: "success", text: `Created skill ${data.name}` });
      setNewSkillName("");
      setTeachMode("explore");
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
    } catch (_err) {
      setTeachStatus({ type: "error", text: "Network error while publishing skill" });
    } finally {
      setPublishLoading(false);
    }
  }

  async function legacyQuickSave() {
    const content = teachInput.trim();
    if (!content || teachLoading) return;
    setTeachLoading(true);
    setTeachStatus(null);
    try {
      const { ok, data } = await api.post("/agent/teach", { content });
      if (!ok) {
        setTeachStatus({ type: "error", text: data.detail || "Failed to create skill" });
        return;
      }
      setTeachStatus({ type: "success", text: `Saved as ${data.skill_filename}` });
      setTeachInput("");
      await loadSkills();
    } catch (_err) {
      setTeachStatus({ type: "error", text: "Network error while creating skill" });
    } finally {
      setTeachLoading(false);
    }
  }

  return {
    teachModalOpen,
    setTeachModalOpen,
    teachInput,
    setTeachInput,
    teachStatus,
    teachLoading,
    teachExpanded,
    setTeachExpanded,
    teachMode,
    setTeachMode,
    skills,
    skillsLoading,
    createSkillLoading,
    publishLoading,
    activeSkillId,
    setActiveSkillId,
    newSkillName,
    setNewSkillName,
    skillConversations,
    activeSkillConversationId,
    setActiveSkillConversationId,
    skillMessages,
    createSkill,
    createSkillConversation,
    sendSkillMessage,
    publishSkill,
    legacyQuickSave,
  };
}
