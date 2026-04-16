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

async function request(method, path, body) {
  const init = { method };
  if (body !== undefined) {
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(body);
  }
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
  });
  return parseJson(res);
}

async function get(path) {
  return request("GET", path);
}

async function post(path, body) {
  return request("POST", path, body);
}

async function del(path) {
  return request("DELETE", path);
}

export const api = {
  API_BASE,
  get,
  post,
  del,
};
