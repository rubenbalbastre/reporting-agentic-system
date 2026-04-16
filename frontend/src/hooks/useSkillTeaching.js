import { useEffect, useReducer } from "react";
import { api } from "../api";
import { isPublishedSkill } from "../utils/skills";

const initialState = {
  teachModalOpen: false,
  teachInitialPanel: "draft",
  teachInput: "",
  teachStatus: null,
  loading: {
    teach: false,
    skills: false,
    create: false,
    del: false,
    publish: false,
    openDraft: false,
  },
  skills: [],
  activeSkillId: null,
  skillConversations: [],
  activeSkillConversationId: null,
  skillMessages: [],
  skillMarkdown: "",
  skillFiles: [],
};

function reducer(state, action) {
  switch (action.type) {
    case "set_teach_modal_open":
      return { ...state, teachModalOpen: action.value };
    case "set_teach_initial_panel":
      return { ...state, teachInitialPanel: action.value };
    case "set_teach_input":
      return { ...state, teachInput: action.value };
    case "set_teach_status":
      return { ...state, teachStatus: action.value };
    case "set_loading":
      return { ...state, loading: { ...state.loading, [action.key]: action.value } };
    case "reset_active_skill_state":
      return {
        ...state,
        activeSkillId: null,
        activeSkillConversationId: null,
        skillMessages: [],
        skillMarkdown: "",
        skillFiles: [],
      };
    case "set_skills":
      return { ...state, skills: action.value };
    case "set_active_skill_id":
      return { ...state, activeSkillId: action.value };
    case "clear_for_no_active_skill":
      return {
        ...state,
        skillConversations: [],
        activeSkillConversationId: null,
        skillMarkdown: "",
        skillFiles: [],
      };
    case "set_skill_conversations":
      return { ...state, skillConversations: action.value };
    case "set_active_skill_conversation_id":
      return { ...state, activeSkillConversationId: action.value };
    case "set_skill_messages":
      return { ...state, skillMessages: action.value };
    case "set_skill_markdown":
      return { ...state, skillMarkdown: action.value };
    case "set_skill_files":
      return { ...state, skillFiles: action.value };
    default:
      return state;
  }
}

export function useSkillTeaching(toast) {
  const [state, dispatch] = useReducer(reducer, initialState);

  const setTeachModalOpen = (value) => dispatch({ type: "set_teach_modal_open", value });
  const setTeachInitialPanel = (value) => dispatch({ type: "set_teach_initial_panel", value });
  const setTeachInput = (value) => dispatch({ type: "set_teach_input", value });
  const setActiveSkillId = (value) => dispatch({ type: "set_active_skill_id", value });
  const setActiveSkillConversationId = (value) => dispatch({ type: "set_active_skill_conversation_id", value });

  function setErrorStatus(defaultMessage, detail) {
    const text = detail || defaultMessage;
    dispatch({ type: "set_teach_status", value: { type: "error", text } });
    toast?.error(text);
  }

  async function withLoading(key, task) {
    dispatch({ type: "set_loading", key, value: true });
    try {
      await task();
    } finally {
      dispatch({ type: "set_loading", key, value: false });
    }
  }

  useEffect(() => {
    if (!state.teachModalOpen) {
      dispatch({ type: "reset_active_skill_state" });
      return;
    }
    loadSkills();
  }, [state.teachModalOpen]);

  useEffect(() => {
    if (!state.activeSkillId) {
      dispatch({ type: "clear_for_no_active_skill" });
      return;
    }
    loadSkillConversations(state.activeSkillId);
    loadSkillMarkdown(state.activeSkillId);
    loadSkillFiles(state.activeSkillId);
  }, [state.activeSkillId]);

  useEffect(() => {
    if (!state.activeSkillConversationId) {
      dispatch({ type: "set_skill_messages", value: [] });
      return;
    }
    loadSkillMessages(state.activeSkillConversationId);
  }, [state.activeSkillConversationId]);

  useEffect(() => {
    if (!state.teachStatus) return;
    const timer = setTimeout(() => dispatch({ type: "set_teach_status", value: null }), 3500);
    return () => clearTimeout(timer);
  }, [state.teachStatus]);

  async function loadSkills() {
    dispatch({ type: "set_loading", key: "skills", value: true });
    try {
      const { ok, data } = await api.get("/skills");
      dispatch({ type: "set_skills", value: ok && Array.isArray(data) ? data : [] });
    } finally {
      dispatch({ type: "set_loading", key: "skills", value: false });
    }
  }

  async function createSkill() {
    if (state.loading.create) return;
    const name = `New Skill ${state.skills.length + 1}`;
    dispatch({ type: "set_teach_status", value: null });
    await withLoading("create", async () => {
      try {
        const { ok, data } = await api.post("/skills", { name });
        if (!ok) {
          setErrorStatus("Failed to create skill", data.detail);
          return;
        }
        dispatch({ type: "set_teach_status", value: { type: "success", text: `Created skill ${data.name}` } });
        toast?.success(`Created skill ${data.name}`);
        await loadSkills();
        dispatch({ type: "set_active_skill_id", value: data.id });
        const convs = await loadSkillConversations(data.id);
        if (!convs.length) {
          const newConv = await api.post(`/skills/${data.id}/conversations`);
          if (newConv.ok && newConv.data?.id) {
            dispatch({ type: "set_active_skill_conversation_id", value: newConv.data.id });
          }
        } else {
          dispatch({ type: "set_active_skill_conversation_id", value: convs[0].id });
        }
      } catch (_err) {
        setErrorStatus(
          "Could not reach backend. Check backend is running on :8000 and DB schema is up to date (make db-init).",
        );
      }
    });
  }

  async function deleteSkill() {
    if (!state.activeSkillId || state.loading.del) return;
    dispatch({ type: "set_teach_status", value: null });
    await withLoading("del", async () => {
      try {
        const { ok, data } = await api.del(`/skills/${state.activeSkillId}`);
        if (!ok) {
          setErrorStatus("Failed to delete skill", data.detail);
          return;
        }
        dispatch({ type: "set_teach_status", value: { type: "success", text: "Skill deleted" } });
        toast?.success("Skill deleted");
        dispatch({ type: "reset_active_skill_state" });
        await loadSkills();
      } catch (_err) {
        setErrorStatus("Network error while deleting skill");
      }
    });
  }

  async function loadSkillConversations(skillId) {
    const { ok, data } = await api.get(`/skills/${skillId}/conversations`);
    const list = ok && Array.isArray(data) ? data : [];
    dispatch({ type: "set_skill_conversations", value: list });
    if (list.length && !list.some((c) => c.id === state.activeSkillConversationId)) {
      dispatch({ type: "set_active_skill_conversation_id", value: list[0].id });
    }
    return list;
  }

  async function createSkillConversation() {
    if (!state.activeSkillId) return;
    const { ok, data } = await api.post(`/skills/${state.activeSkillId}/conversations`);
    if (!ok) {
      setErrorStatus("Failed to create skill conversation", data.detail);
      return;
    }
    await loadSkillConversations(state.activeSkillId);
    dispatch({ type: "set_active_skill_conversation_id", value: data.id });
    toast?.success("Skill conversation created");
  }

  async function loadSkillMessages(skillConversationId) {
    const { ok, data } = await api.get(`/skill-conversations/${skillConversationId}/messages`);
    dispatch({ type: "set_skill_messages", value: ok && Array.isArray(data) ? data : [] });
  }

  async function loadSkillMarkdown(skillId) {
    const { ok, data } = await api.get(`/skills/${skillId}/markdown`);
    if (!ok) {
      dispatch({ type: "set_skill_markdown", value: "# Skill markdown not published yet" });
      return;
    }
    dispatch({ type: "set_skill_markdown", value: data.content || "" });
  }

  async function loadSkillFiles(skillId) {
    const { ok, data } = await api.get(`/skills/${skillId}/files`);
    if (!ok) {
      dispatch({ type: "set_skill_files", value: [] });
      return;
    }
    dispatch({ type: "set_skill_files", value: Array.isArray(data.files) ? data.files : [] });
  }

  async function sendSkillMessage() {
    if (!state.activeSkillConversationId || !state.teachInput.trim() || state.loading.teach) return;
    const content = state.teachInput.trim();
    dispatch({ type: "set_teach_status", value: null });
    dispatch({ type: "set_teach_input", value: "" });
    dispatch({
      type: "set_skill_messages",
      value: [
        ...state.skillMessages,
        { id: `tmp-su-${Date.now()}`, role: "user", content, created_at: new Date().toISOString() },
        { id: `tmp-sa-${Date.now()}`, role: "assistant", content: "", status: "pending", created_at: new Date().toISOString() },
      ],
    });

    await withLoading("teach", async () => {
      try {
        const { ok, data } = await api.post(`/skill-conversations/${state.activeSkillConversationId}/messages`, { content });
        if (!ok) {
          setErrorStatus("Failed to send skill message", data.detail);
          return;
        }
        await loadSkillMessages(state.activeSkillConversationId);
      } catch (_err) {
        setErrorStatus("Network error while sending skill message");
      }
    });
  }

  async function publishSkill() {
    if (!state.activeSkillId || !state.activeSkillConversationId || state.loading.publish) return;
    dispatch({ type: "set_teach_status", value: null });
    await withLoading("publish", async () => {
      try {
        const { ok, data } = await api.post(`/skills/${state.activeSkillId}/publish`, {
          skill_conversation_id: state.activeSkillConversationId,
        });
        if (!ok) {
          setErrorStatus("Failed to publish skill", data.detail);
          return;
        }
        dispatch({ type: "set_teach_status", value: { type: "success", text: `Published ${data.name}` } });
        toast?.success(`Published ${data.name}`);
        await loadSkills();
        await loadSkillMarkdown(state.activeSkillId);
      } catch (_err) {
        setErrorStatus("Network error while publishing skill");
      }
    });
  }

  async function openSkillInDraft() {
    if (!state.activeSkillId || state.loading.openDraft) return;
    dispatch({ type: "set_teach_status", value: null });
    await withLoading("openDraft", async () => {
      try {
        const { ok, data } = await api.post(`/skills/${state.activeSkillId}/open-draft`);
        if (!ok) {
          setErrorStatus("Failed to open draft", data.detail);
          return;
        }
        dispatch({ type: "set_teach_status", value: { type: "success", text: `Opened draft ${data.name}` } });
        toast?.success(`Opened draft ${data.name}`);
        dispatch({ type: "set_teach_initial_panel", value: "draft" });
        await loadSkills();
        dispatch({ type: "set_active_skill_id", value: data.id });
        const convs = await loadSkillConversations(data.id);
        if (convs.length) {
          dispatch({ type: "set_active_skill_conversation_id", value: convs[0].id });
        }
        await loadSkillMarkdown(data.id);
      } catch (_err) {
        setErrorStatus("Network error while opening draft");
      }
    });
  }

  const activeSkill = state.skills.find((s) => s.id === state.activeSkillId) || null;
  const activeSkillIsPublished = isPublishedSkill(activeSkill);

  return {
    teachModalOpen: state.teachModalOpen,
    setTeachModalOpen,
    teachInitialPanel: state.teachInitialPanel,
    setTeachInitialPanel,
    teachInput: state.teachInput,
    setTeachInput,
    teachStatus: state.teachStatus,
    teachLoading: state.loading.teach,
    skills: state.skills,
    skillsLoading: state.loading.skills,
    createSkillLoading: state.loading.create,
    deleteSkillLoading: state.loading.del,
    publishLoading: state.loading.publish,
    openDraftLoading: state.loading.openDraft,
    activeSkillId: state.activeSkillId,
    setActiveSkillId,
    skillConversations: state.skillConversations,
    activeSkillConversationId: state.activeSkillConversationId,
    setActiveSkillConversationId,
    skillMessages: state.skillMessages,
    skillMarkdown: state.skillMarkdown,
    skillFiles: state.skillFiles,
    createSkill,
    deleteSkill,
    createSkillConversation,
    sendSkillMessage,
    publishSkill,
    openSkillInDraft,
    activeSkillIsPublished,
    isPublishedSkill,
  };
}
