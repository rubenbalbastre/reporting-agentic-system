import express from "express";
import cors from "cors";
import OpenAI from "openai";

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

const openai = process.env.OPENAI_API_KEY
  ? new OpenAI({ apiKey: process.env.OPENAI_API_KEY })
  : null;

let nextReportId = 2;
let nextMessageId = 1;

const reports = [
  {
    id: 1,
    title: "First Report",
    created_at: new Date().toISOString(),
  },
];

const messagesByReport = new Map();

function getMessages(reportId) {
  if (!messagesByReport.has(reportId)) {
    messagesByReport.set(reportId, []);
  }
  return messagesByReport.get(reportId);
}

app.get("/api/reports", (_req, res) => {
  res.json([...reports].sort((a, b) => b.id - a.id));
});

app.post("/api/reports", (req, res) => {
  const title = String(req.body?.title || "New Report").trim();
  const report = {
    id: nextReportId++,
    title,
    created_at: new Date().toISOString(),
  };
  reports.push(report);
  messagesByReport.set(report.id, []);
  res.status(201).json(report);
});

app.get("/api/reports/:reportId/messages", (req, res) => {
  const reportId = Number(req.params.reportId);
  if (!Number.isFinite(reportId)) {
    return res.status(400).json({ error: "Invalid report id" });
  }
  return res.json(getMessages(reportId));
});

app.post("/api/reports/:reportId/messages", async (req, res) => {
  const reportId = Number(req.params.reportId);
  const userContent = String(req.body?.content || "").trim();

  if (!Number.isFinite(reportId)) {
    return res.status(400).json({ error: "Invalid report id" });
  }
  if (!userContent) {
    return res.status(400).json({ error: "Message content is required" });
  }

  const reportExists = reports.some((r) => r.id === reportId);
  if (!reportExists) {
    return res.status(404).json({ error: "Report not found" });
  }

  const reportMessages = getMessages(reportId);

  const userMessage = {
    id: nextMessageId++,
    report_id: reportId,
    role: "user",
    content: userContent,
    created_at: new Date().toISOString(),
  };
  reportMessages.push(userMessage);

  let assistantContent =
    "I stored your message in memory. Add OPENAI_API_KEY to enable AI responses.";

  if (openai) {
    try {
      const completion = await openai.responses.create({
        model: process.env.OPENAI_MODEL || "gpt-4.1-mini",
        input: [
          {
            role: "system",
            content:
              "You are a concise analytics reporting assistant helping refine report drafts.",
          },
          { role: "user", content: userContent },
        ],
      });
      assistantContent = completion.output_text?.trim() || assistantContent;
    } catch (_err) {
      assistantContent =
        "OpenAI request failed. Your message is stored, but I could not generate a response.";
    }
  }

  const assistantMessage = {
    id: nextMessageId++,
    report_id: reportId,
    role: "assistant",
    content: assistantContent,
    created_at: new Date().toISOString(),
  };
  reportMessages.push(assistantMessage);

  return res.status(201).json({ messages: [userMessage, assistantMessage] });
});

app.listen(PORT, () => {
  console.log(`Backend listening on http://localhost:${PORT}`);
});
