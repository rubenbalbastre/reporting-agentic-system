import { useEffect, useState } from "react";
import { api } from "../api";

export const VIEW = {
  ORIGINAL: "original",
  REPORT: "report",
  CHAT: "chat",
};

export function useReportChat(toast) {
  const [reports, setReports] = useState([]);
  const [activeReportId, setActiveReportId] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [markdown, setMarkdown] = useState("# Select or create a report");
  const [sidebarVisible, setSidebarVisible] = useState(true);
  const [viewMode, setViewMode] = useState(VIEW.ORIGINAL);
  const [deleteReportLoading, setDeleteReportLoading] = useState(false);

  function resetReportSelection() {
    setActiveReportId(null);
    setConversations([]);
    setActiveConversationId(null);
    setMessages([]);
    setMarkdown("# Select or create a report");
  }

  useEffect(() => {
    loadReports();
  }, []);

  useEffect(() => {
    if (!activeReportId) {
      resetReportSelection();
      return;
    }
    loadConversations(activeReportId);
    loadReportMarkdown(activeReportId);
  }, [activeReportId]);

  useEffect(() => {
    if (!activeConversationId) {
      setMessages([]);
      return;
    }
    loadMessages(activeConversationId);
  }, [activeConversationId]);

  async function loadReports() {
    const { ok, data } = await api.get("/reports");
    const list = ok && Array.isArray(data) ? data : [];
    setReports(list);
    if (!activeReportId && list.length) setActiveReportId(list[0].id);
    return list;
  }

  async function loadConversations(reportId) {
    const { ok, data } = await api.get(`/reports/${reportId}/conversations`);
    const list = ok && Array.isArray(data) ? data : [];
    setConversations(list);
    if (!list.length) {
      setActiveConversationId(null);
      return list;
    }
    if (!list.some((c) => c.id === activeConversationId)) {
      setActiveConversationId(list[0].id);
    }
    return list;
  }

  async function loadMessages(conversationId) {
    const { ok, data } = await api.get(`/conversations/${conversationId}/messages`);
    setMessages(ok && Array.isArray(data) ? data : []);
  }

  async function loadReportMarkdown(reportId) {
    const { ok, data } = await api.get(`/reports/${reportId}/markdown`);
    if (!ok) {
      setMarkdown("# Failed to load report preview");
      toast?.error("Failed to load report preview");
      return;
    }
    setMarkdown(data.content || "");
  }

  async function createReport() {
    const title = `Report ${reports.length + 1}`;
    const { ok, data } = await api.post("/reports", { title });
    if (!ok) {
      toast?.error("Failed to create report");
      return;
    }
    await loadReports();
    setActiveReportId(data.id);
    const convs = await loadConversations(data.id);
    if (!convs.length) {
      const newConv = await api.post(`/reports/${data.id}/conversations`);
      if (newConv.ok && newConv.data?.id) {
        setActiveConversationId(newConv.data.id);
      }
    } else {
      setActiveConversationId(convs[0].id);
    }
    await loadReportMarkdown(data.id);
    toast?.success("Report created");
  }

  async function createConversation() {
    if (!activeReportId) return;
    const { ok, data } = await api.post(`/reports/${activeReportId}/conversations`);
    if (!ok) {
      toast?.error(data.detail || "Failed to create conversation");
      return;
    }
    await loadConversations(activeReportId);
    setActiveConversationId(data.id);
    toast?.success("Conversation created");
  }

  async function renameReport(nextTitle) {
    if (!activeReportId) return;
    const active = reports.find((r) => r.id === activeReportId);
    const currentTitle = active?.title || "";
    const title = String(nextTitle || "").trim();
    if (!title || title === currentTitle) return;

    const { ok, data } = await api.post(`/reports/${activeReportId}/title`, { title });
    if (!ok) {
      toast?.error(data.detail || "Failed to rename report");
      return;
    }

    setReports((prev) => prev.map((r) => (r.id === activeReportId ? { ...r, title: data.title } : r)));
    toast?.success("Report renamed");
  }

  async function deleteReport() {
    if (!activeReportId || deleteReportLoading) return;
    setDeleteReportLoading(true);
    try {
      const deletingId = activeReportId;
      const { ok } = await api.del(`/reports/${deletingId}`);
      if (!ok) {
        toast?.error("Failed to delete report");
        return;
      }
      const list = await loadReports();
      if (!list.length) {
        resetReportSelection();
        toast?.success("Report deleted");
        return;
      }
      const next = list.find((r) => r.id !== deletingId) || list[0];
      setActiveReportId(next.id);
      toast?.success("Report deleted");
    } finally {
      setDeleteReportLoading(false);
    }
  }

  function exportReportPdf() {
    if (!activeReportId) return;
    window.open(`${api.API_BASE}/reports/${activeReportId}/pdf`, "_blank", "noopener,noreferrer");
    toast?.info("Export started");
  }

  async function sendMessage() {
    if (!activeConversationId || !input.trim()) return;
    const content = input.trim();
    const conversationId = activeConversationId;
    const tempUserId = `tmp-u-${Date.now()}`;
    const tempAssistantId = `tmp-a-${Date.now()}`;
    setInput("");
    setMessages((prev) => [
      ...prev,
      { id: tempUserId, role: "user", content, created_at: new Date().toISOString() },
      { id: tempAssistantId, role: "assistant", content: "", status: "pending", created_at: new Date().toISOString() },
    ]);

    const { ok, data } = await api.post(`/conversations/${conversationId}/messages`, { content });
    await loadMessages(conversationId);
    await loadReportMarkdown(activeReportId);
    if (!ok) toast?.error(data.detail || "Failed to send message");
  }

  const showReportPanel = viewMode !== VIEW.CHAT;
  const showChatPanel = viewMode !== VIEW.REPORT;

  const layoutClassName = (() => {
    if (showReportPanel && showChatPanel) return "layout two-panels";
    if (showReportPanel) return "layout report-only";
    if (showChatPanel) return "layout chat-only";
    return "layout empty";
  })();

  const activeReportTitle = (() => {
    const active = reports.find((r) => r.id === activeReportId);
    return active?.title || null;
  })();

  return {
    reports,
    activeReportId,
    setActiveReportId,
    conversations,
    activeConversationId,
    setActiveConversationId,
    messages,
    input,
    setInput,
    markdown,
    sidebarVisible,
    setSidebarVisible,
    viewMode,
    setViewMode,
    createReport,
    renameReport,
    deleteReport,
    deleteReportLoading,
    exportReportPdf,
    createConversation,
    sendMessage,
    layoutClassName,
    activeReportTitle,
    showReportPanel,
    showChatPanel,
  };
}
