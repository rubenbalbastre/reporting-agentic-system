import { useEffect, useState } from "react";
import { api } from "../api";

export function useSkillTeaching(toast) {
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

  function resetActiveSkillState() {
    setActiveSkillId(null);
    setActiveSkillConversationId(null);
    setSkillMessages([]);
    setSkillMarkdown("");
  }

  function setErrorStatus(defaultMessage, detail) {
    const text = detail || defaultMessage;
    setTeachStatus({ type: "error", text });
    toast?.error(text);
  }

  async function withLoading(setLoading, task) {
    setLoading(true);
    try {
      await task();
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!teachModalOpen) {
      resetActiveSkillState();
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
    setTeachStatus(null);
    await withLoading(setCreateSkillLoading, async () => {
      try {
        const { ok, data } = await api.post("/skills", { name });
        if (!ok) {
          setErrorStatus("Failed to create skill", data.detail);
          return;
        }
        setTeachStatus({ type: "success", text: `Created skill ${data.name}` });
        toast?.success(`Created skill ${data.name}`);
        await loadSkills();
        setActiveSkillId(data.id);
        const convs = await loadSkillConversations(data.id);
        if (!convs.length) {
          const newConv = await api.post(`/skills/${data.id}/conversations`);
          if (newConv.ok && newConv.data?.id) {
            setActiveSkillConversationId(newConv.data.id);
          }
        } else {
          setActiveSkillConversationId(convs[0].id);
        }
      } catch (_err) {
        setErrorStatus(
          "Could not reach backend. Check backend is running on :8000 and DB schema is up to date (make db-init).",
        );
      }
    });
  }

  async function deleteSkill() {
    if (!activeSkillId || deleteSkillLoading) return;
    setTeachStatus(null);
    await withLoading(setDeleteSkillLoading, async () => {
      try {
        const { ok, data } = await api.del(`/skills/${activeSkillId}`);
        if (!ok) {
          setErrorStatus("Failed to delete skill", data.detail);
          return;
        }
        setTeachStatus({ type: "success", text: "Skill deleted" });
        toast?.success("Skill deleted");
        resetActiveSkillState();
        await loadSkills();
      } catch (_err) {
        setErrorStatus("Network error while deleting skill");
      }
    });
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
      setErrorStatus("Failed to create skill conversation", data.detail);
      return;
    }
    await loadSkillConversations(activeSkillId);
    setActiveSkillConversationId(data.id);
    toast?.success("Skill conversation created");
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
    setTeachStatus(null);
    setTeachInput("");
    setSkillMessages((prev) => [
      ...prev,
      { id: `tmp-su-${Date.now()}`, role: "user", content, created_at: new Date().toISOString() },
      { id: `tmp-sa-${Date.now()}`, role: "assistant", content: "", status: "pending", created_at: new Date().toISOString() },
    ]);
    await withLoading(setTeachLoading, async () => {
      try {
        const { ok, data } = await api.post(`/skill-conversations/${activeSkillConversationId}/messages`, { content });
        if (!ok) {
          setErrorStatus("Failed to send skill message", data.detail);
          return;
        }
        await loadSkillMessages(activeSkillConversationId);
      } catch (_err) {
        setErrorStatus("Network error while sending skill message");
      }
    });
  }

  async function publishSkill() {
    if (!activeSkillId || !activeSkillConversationId || publishLoading) return;
    setTeachStatus(null);
    await withLoading(setPublishLoading, async () => {
      try {
        const { ok, data } = await api.post(`/skills/${activeSkillId}/publish`, {
          skill_conversation_id: activeSkillConversationId,
        });
        if (!ok) {
          setErrorStatus("Failed to publish skill", data.detail);
          return;
        }
        setTeachStatus({ type: "success", text: `Published ${data.name}` });
        toast?.success(`Published ${data.name}`);
        await loadSkills();
        await loadSkillMarkdown(activeSkillId);
      } catch (_err) {
        setErrorStatus("Network error while publishing skill");
      }
    });
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
