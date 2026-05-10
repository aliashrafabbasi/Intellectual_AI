import type { ChatLike } from "./sessionTitle";

export type ChatMessage = { role: "user" | "assistant"; content: string };

export type ChatSummary = ChatLike & {
  created_at?: string;
};

export type ChatDocument = ChatLike & {
  messages?: Array<{ role: string; content: string }>;
  created_at?: string;
};

function join(base: string, path: string): string {
  const b = base.replace(/\/$/, "");
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${b}${p}`;
}

/** Empty base uses same-origin `/api` (Vite dev proxy) or production reverse-proxy. */
export function apiUrl(base: string, path: string): string {
  if (!base) {
    return path.startsWith("/") ? path : `/${path}`;
  }
  return join(base, path);
}

export async function checkApiHealth(base: string): Promise<boolean> {
  try {
    const r = await fetch(apiUrl(base, "/docs"), { method: "GET", signal: AbortSignal.timeout(4000) });
    return r.ok;
  } catch {
    return false;
  }
}

export async function listChats(base: string): Promise<ChatSummary[]> {
  const r = await fetch(apiUrl(base, "/api/v1/chats"), { signal: AbortSignal.timeout(60000) });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || `Failed to list chats (${r.status})`);
  }
  const data = (await r.json()) as unknown;
  return Array.isArray(data) ? (data as ChatSummary[]) : [];
}

export async function fetchChat(base: string, sessionId: string): Promise<ChatDocument> {
  const r = await fetch(apiUrl(base, `/api/v1/chat/${encodeURIComponent(sessionId)}`), {
    signal: AbortSignal.timeout(60000),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || `Failed to load chat (${r.status})`);
  }
  return (await r.json()) as ChatDocument;
}

export async function ensureSession(base: string, sessionId: string): Promise<void> {
  const r = await fetch(apiUrl(base, `/api/v1/chat/${encodeURIComponent(sessionId)}/ensure`), {
    method: "POST",
    signal: AbortSignal.timeout(30000),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || `ensure failed (${r.status})`);
  }
}

export async function deleteChat(base: string, sessionId: string): Promise<void> {
  const r = await fetch(apiUrl(base, `/api/v1/chat/${encodeURIComponent(sessionId)}`), {
    method: "DELETE",
    signal: AbortSignal.timeout(30000),
  });
  if (r.status === 404) {
    throw new Error("Session not found on server.");
  }
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || `Delete failed (${r.status})`);
  }
}

export async function renameChat(base: string, sessionId: string, name: string): Promise<void> {
  const r = await fetch(apiUrl(base, `/api/v1/chat/${encodeURIComponent(sessionId)}`), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
    signal: AbortSignal.timeout(30000),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || `Rename failed (${r.status})`);
  }
}

export function normalizeMessages(raw: ChatDocument["messages"]): ChatMessage[] {
  if (!raw || !Array.isArray(raw)) return [];
  const out: ChatMessage[] = [];
  for (const m of raw) {
    if (m && typeof m === "object" && "role" in m && "content" in m) {
      const role = m.role === "assistant" ? "assistant" : "user";
      out.push({ role, content: String(m.content ?? "") });
    }
  }
  return out;
}

export async function streamChat(
  base: string,
  sessionId: string,
  message: string,
  onDelta: (accumulated: string) => void,
): Promise<string> {
  const r = await fetch(apiUrl(base, "/api/v1/chat/stream"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  if (!r.ok) {
    const t = await r.text();
    let detail = t;
    try {
      const j = JSON.parse(t) as { detail?: string };
      if (j.detail) detail = j.detail;
    } catch {
      /* keep text */
    }
    throw new Error(detail || `Stream failed (${r.status})`);
  }
  const reader = r.body?.getReader();
  if (!reader) {
    throw new Error("No response body");
  }
  const decoder = new TextDecoder();
  let acc = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    acc += decoder.decode(value, { stream: true });
    onDelta(acc);
  }
  acc += decoder.decode();
  onDelta(acc);
  return acc;
}
