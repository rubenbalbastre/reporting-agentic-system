import { useEffect, useMemo, useState } from "react";
import { api } from "../api";

export const VIEW = {
  ORIGINAL: "original",
  REPORT: "report",
  CHAT: "chat",
};

export function useReportChat() {
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

  useEffect(() => {
    loadReports();
  }, []);

  useEffect(() => {
    if (!activeReportId) {
      setMarkdown("# Select or create a report");
      setConversations([]);
      setActiveConversationId(null);
      setMessages([]);
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
      return;
    }
    setMarkdown(data.content || "");
  }

  async function createReport() {
    const title = `Report ${reports.length + 1}`;
    const { ok, data } = await api.post("/reports", { title });
    if (!ok) return;
    await loadReports();
    setActiveReportId(data.id);
    const convs = await loadConversations(data.id);
    if (convs.length) setActiveConversationId(convs[0].id);
    await loadReportMarkdown(data.id);
  }

  async function createConversation() {
    if (!activeReportId) return;
    const { ok, data } = await api.post(`/reports/${activeReportId}/conversations`);
    if (!ok) {
      alert(data.detail || "Failed to create conversation");
      return;
    }
    await loadConversations(activeReportId);
    setActiveConversationId(data.id);
  }

  async function deleteReport() {
    if (!activeReportId || deleteReportLoading) return;
    setDeleteReportLoading(true);
    try {
      const deletingId = activeReportId;
      const { ok } = await api.del(`/reports/${deletingId}`);
      if (!ok) {
        alert("Failed to delete report");
        return;
      }
      const { ok: okReports, data } = await api.get("/reports");
      const list = okReports && Array.isArray(data) ? data : [];
      setReports(list);
      if (!list.length) {
        setActiveReportId(null);
        setConversations([]);
        setActiveConversationId(null);
        setMessages([]);
        setMarkdown("# Select or create a report");
        return;
      }
      const next = list.find((r) => r.id !== deletingId) || list[0];
      setActiveReportId(next.id);
    } finally {
      setDeleteReportLoading(false);
    }
  }

  function exportReportPdf() {
    if (!activeReportId) return;
    window.open(`${api.API_BASE}/reports/${activeReportId}/pdf`, "_blank", "noopener,noreferrer");
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
      { id: tempUserId, role: "user", content },
      { id: tempAssistantId, role: "assistant", content: "", status: "pending" },
    ]);

    const { ok, data } = await api.post(`/conversations/${conversationId}/messages`, { content });
    await loadMessages(conversationId);
    await loadReportMarkdown(activeReportId);
    if (!ok) alert(data.detail || "Failed to send message");
  }

  const showReportPanel = useMemo(() => viewMode !== VIEW.CHAT, [viewMode]);
  const showChatPanel = useMemo(() => viewMode !== VIEW.REPORT, [viewMode]);

  const layoutClassName = useMemo(() => {
    const withSidebar = sidebarVisible ? "with-sidebar" : "no-sidebar";
    if (showReportPanel && showChatPanel) return `layout ${withSidebar} two-panels`;
    if (showReportPanel) return `layout ${withSidebar} report-only`;
    if (showChatPanel) return `layout ${withSidebar} chat-only`;
    return `layout ${withSidebar} empty`;
  }, [sidebarVisible, showReportPanel, showChatPanel]);

  const activeReportTitle = useMemo(() => {
    const active = reports.find((r) => r.id === activeReportId);
    return active?.title || null;
  }, [reports, activeReportId]);

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
