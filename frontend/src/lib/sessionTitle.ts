export type ChatLike = {
  session_id?: string;
  name?: string | null;
};

const PLACEHOLDER = new Set([
  "untitled chat",
  "untitled",
  "untilled chat",
  "untilled",
  "new chat",
  "new session",
]);

export function sessionDisplayTitle(chat: ChatLike): string {
  const n = (chat.name ?? "").trim();
  if (PLACEHOLDER.has(n.toLowerCase())) {
    return "Untitled chat";
  }
  if (n) {
    return n;
  }
  const sid = chat.session_id ?? "";
  if (sid.length > 10) {
    return `Session ${sid.slice(0, 8)}…`;
  }
  return sid || "Untitled";
}
