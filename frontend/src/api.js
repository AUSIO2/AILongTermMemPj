const BASE = "/api";

async function request(method, path, body) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body !== undefined) opts.body = JSON.stringify(body);

  const res = await fetch(`${BASE}${path}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? res.statusText);
  }
  return res.json();
}

export const fetchStrategies = () => request("GET", "/strategies");

export const createSession = (strategy) =>
  request("POST", "/sessions", { strategy });

export const sendMessage = (sessionId, message) =>
  request("POST", `/sessions/${sessionId}/chat`, { message });

export const getHistory = (sessionId) =>
  request("GET", `/sessions/${sessionId}/history`);

export const deleteSession = (sessionId) =>
  request("DELETE", `/sessions/${sessionId}`);
