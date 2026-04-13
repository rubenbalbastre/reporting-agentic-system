const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function parseJson(res) {
  const text = await res.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch (_err) {
    data = { detail: text || "Unexpected backend response" };
  }
  return { ok: res.ok, status: res.status, data };
}

async function get(path) {
  const res = await fetch(`${API_BASE}${path}`);
  return parseJson(res);
}

async function post(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  return parseJson(res);
}

export const api = {
  API_BASE,
  get,
  post,
};
