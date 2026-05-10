import { useCallback, useEffect, useRef, useState } from "react";
import "./App.css";
import { MarkdownBody } from "./components/MarkdownBody";
import {
  checkApiHealth,
  deleteChat,
  ensureSession,
  fetchChat,
  listChats,
  normalizeMessages,
  renameChat,
  streamChat,
  type ChatMessage,
  type ChatSummary,
} from "./lib/api";
import { sessionDisplayTitle } from "./lib/sessionTitle";
import { persistTheme, resolveInitialTheme, type Theme } from "./theme";

import avatarAi from "./assets/chat_avatar_ai.png";
import avatarUser from "./assets/chat_avatar_user.png";

const STORAGE_API = "intellectual_api_base";
const STORAGE_SESSION = "intellectual_session";

function defaultApiBase(): string {
  const env = import.meta.env.VITE_API_URL?.trim();
  return env ? env.replace(/\/$/, "") : "";
}

function formatTs(value: string | undefined): string {
  if (!value) return "";
  try {
    const dt = new Date(value);
    if (Number.isNaN(dt.getTime())) return value.slice(0, 16);
    return dt.toLocaleString(undefined, {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

export default function App() {
  const [apiBase, setApiBase] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_API) ?? defaultApiBase();
    } catch {
      return defaultApiBase();
    }
  });
  const [connected, setConnected] = useState<boolean | null>(null);
  const [sessionId, setSessionId] = useState(() => {
    try {
      return sessionStorage.getItem(STORAGE_SESSION) || crypto.randomUUID();
    } catch {
      return crypto.randomUUID();
    }
  });
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionLabel, setSessionLabel] = useState("New session");
  const [chats, setChats] = useState<ChatSummary[]>([]);
  const [listError, setListError] = useState<string | null>(null);
  const [sessionSearch, setSessionSearch] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [menuOpenSid, setMenuOpenSid] = useState<string | null>(null);
  const [renameFor, setRenameFor] = useState<{ sid: string; title: string } | null>(null);
  const [renameInput, setRenameInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const [theme, setTheme] = useState<Theme>(() => resolveInitialTheme());

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    persistTheme(theme);
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      meta.setAttribute("content", theme === "dark" ? "#121316" : "#f7f7f8");
    }
  }, [theme]);

  useEffect(() => {
    if (!menuOpenSid) return;
    const close = () => setMenuOpenSid(null);
    const t = window.setTimeout(() => document.addEventListener("click", close), 0);
    return () => {
      clearTimeout(t);
      document.removeEventListener("click", close);
    };
  }, [menuOpenSid]);

  const persistApiBase = useCallback((value: string) => {
    setApiBase(value);
    try {
      localStorage.setItem(STORAGE_API, value);
    } catch {
      /* ignore */
    }
  }, []);

  const persistSession = useCallback((sid: string) => {
    setSessionId(sid);
    try {
      sessionStorage.setItem(STORAGE_SESSION, sid);
    } catch {
      /* ignore */
    }
  }, []);

  const refreshChats = useCallback(async () => {
    try {
      const rows = await listChats(apiBase);
      setChats(rows);
      setListError(null);
    } catch (e) {
      setListError(e instanceof Error ? e.message : "Could not load conversations.");
    }
  }, [apiBase]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const ok = await checkApiHealth(apiBase);
      if (!cancelled) setConnected(ok);
    })();
    return () => {
      cancelled = true;
    };
  }, [apiBase]);

  useEffect(() => {
    refreshChats();
  }, [refreshChats]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const doc = await fetchChat(apiBase, sessionId);
        if (cancelled) return;
        setMessages(normalizeMessages(doc.messages));
        setSessionLabel(sessionDisplayTitle(doc));
      } catch {
        if (!cancelled) {
          setMessages([]);
          setSessionLabel("New session");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sessionId, apiBase]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleNewChat = async () => {
    const id = crypto.randomUUID();
    persistSession(id);
    setMessages([]);
    setSessionLabel("New session");
    setDrawerOpen(false);
    try {
      await ensureSession(apiBase, id);
      await refreshChats();
    } catch {
      /* optional */
    }
  };

  const openRename = (sid: string, title: string) => {
    setRenameFor({ sid, title });
    setRenameInput(title);
    setMenuOpenSid(null);
  };

  const submitRename = async () => {
    if (!renameFor) return;
    const name = renameInput.trim();
    if (!name) return;
    try {
      await renameChat(apiBase, renameFor.sid, name);
      if (renameFor.sid === sessionId) {
        setSessionLabel(name);
      }
      setRenameFor(null);
      await refreshChats();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Rename failed.");
    }
  };

  const handleDelete = async (sid: string) => {
    setMenuOpenSid(null);
    if (!window.confirm("Delete this conversation permanently?")) return;
    try {
      await deleteChat(apiBase, sid);
      if (sid === sessionId) {
        const id = crypto.randomUUID();
        persistSession(id);
        setMessages([]);
        setSessionLabel("New session");
        try {
          await ensureSession(apiBase, id);
        } catch {
          /* optional */
        }
        await refreshChats();
      } else {
        await refreshChats();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed.");
    }
  };

  const handleSend = async (raw: string) => {
    const text = raw.trim();
    if (!text || sending) return;
    setSending(true);
    setError(null);

    setMessages((m) => [...m, { role: "user", content: text }]);
    setMessages((m) => [...m, { role: "assistant", content: "" }]);

    try {
      await ensureSession(apiBase, sessionId);
      await streamChat(apiBase, sessionId, text, (acc) => {
        setMessages((prev) => {
          const next = [...prev];
          const last = next.length - 1;
          if (last >= 0 && next[last].role === "assistant") {
            next[last] = { role: "assistant", content: acc };
          }
          return next;
        });
      });

      try {
        const doc = await fetchChat(apiBase, sessionId);
        setSessionLabel(sessionDisplayTitle(doc));
      } catch {
        setSessionLabel((prev) => (prev === "New session" ? "Untitled chat" : prev));
      }
      await refreshChats();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Request failed.";
      setError(msg);
      setMessages((prev) => {
        const next = [...prev];
        if (next.length && next[next.length - 1].role === "assistant") {
          next.pop();
        }
        return next;
      });
    } finally {
      setSending(false);
    }
  };

  const q = sessionSearch.trim().toLowerCase();
  const filtered = chats
    .filter((c) => {
      if (!q) return true;
      const sid = (c.session_id ?? "").toLowerCase();
      const title = sessionDisplayTitle(c).toLowerCase();
      return title.includes(q) || sid.includes(q);
    })
    .slice(0, 25);

  return (
    <div className="shell">
      <div
        className={`sidebar-overlay ${drawerOpen ? "visible" : ""}`}
        aria-hidden={!drawerOpen}
        onClick={() => setDrawerOpen(false)}
      />

      <aside className={`sidebar ${drawerOpen ? "drawer-open" : ""}`}>
        <div className="sidebar-head">
          <div className="sidebar-brand-block">
            <img src="/logo.png" alt="Intellectual AI" className="sidebar-logo" width={220} height={80} />
          </div>
          <details className="conn-panel">
            <summary>Connection</summary>
            <div className="conn-field">
              <label htmlFor="api-base">API base URL</label>
              <input
                id="api-base"
                value={apiBase}
                onChange={(e) => persistApiBase(e.target.value)}
                placeholder="Empty = same-origin / proxy"
                autoComplete="off"
              />
            </div>
            <div className="status-row">
              <span className={`dot ${connected ? "ok" : "bad"}`} />
              {connected === null ? "Checking…" : connected ? "Connected" : "Unavailable"}
            </div>
          </details>

          <button type="button" className="btn-primary" onClick={() => void handleNewChat()}>
            + New chat
          </button>
        </div>

        <div className="sidebar-section-title">Conversations</div>
        <div className="search-wrap">
          <input
            type="search"
            placeholder="Search sessions…"
            value={sessionSearch}
            onChange={(e) => setSessionSearch(e.target.value)}
            aria-label="Search sessions"
          />
        </div>

        <div className="session-scroll">
          {listError && <p className="caption-muted">{listError}</p>}
          {!listError && filtered.length === 0 && q && (
            <p className="caption-muted">No sessions match your search.</p>
          )}
          {filtered.map((c) => {
            const sid = c.session_id ?? "";
            const title = sessionDisplayTitle(c);
            const ts = formatTs(c.created_at);
            const active = sid === sessionId;
            return (
              <div key={sid || title} className="session-row">
                <button
                  type="button"
                  className={`session-title-btn ${active ? "active" : ""}`}
                  title={ts || undefined}
                  onClick={() => {
                    persistSession(sid);
                    setDrawerOpen(false);
                  }}
                >
                  {title}
                </button>
                <div className="session-menu-wrap">
                  <button
                    type="button"
                    className="session-menu-btn"
                    aria-label="Conversation actions"
                    onClick={(e) => {
                      e.stopPropagation();
                      setMenuOpenSid((prev) => (prev === sid ? null : sid));
                    }}
                  >
                    ⋮
                  </button>
                  {menuOpenSid === sid && (
                    <div
                      className="session-menu-pop"
                      role="menu"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button type="button" onClick={() => openRename(sid, title)}>
                        Rename
                      </button>
                      <button type="button" className="danger" onClick={() => void handleDelete(sid)}>
                        Delete
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        <div className="sidebar-foot">
          Active session
          <strong>{sessionLabel}</strong>
          <span style={{ wordBreak: "break-all", display: "block", marginTop: "0.35rem" }}>
            {sessionId.slice(0, 13)}…
          </span>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <button
            type="button"
            className="menu-toggle"
            aria-label="Open sidebar"
            onClick={() => setDrawerOpen(true)}
          >
            ☰
          </button>
          <img
            src="/logo.png"
            alt=""
            className="topbar-logo-mark"
            width={120}
            height={40}
            decoding="async"
          />
          <div className="topbar-text">
            <p className="topbar-kicker">Intellectual AI</p>
            <h1 className="topbar-title">{sessionLabel}</h1>
          </div>

          <ThemeControl theme={theme} onThemeChange={setTheme} />
        </header>

        <div className="chat-scroll">
          {messages.length === 0 && (
            <div className="empty-hero">
              <h2>Jeffry the Genius</h2>
              <p>
                Type below to chat. Replies stream from{" "}
                <code>/api/v1/chat/stream</code>. Sessions are saved when MongoDB is configured.
              </p>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={`${i}-${m.role}`} className={`msg-row ${m.role}`}>
              {m.role === "assistant" && (
                <div className="avatar ai">
                  <img src={avatarAi} alt="" width={44} height={44} decoding="async" />
                </div>
              )}
              <div className={`bubble ${m.role} md`}>
                <MarkdownBody
                  content={m.content}
                  placeholder={m.role === "assistant" ? "Thinking…" : undefined}
                />
              </div>
              {m.role === "user" && (
                <div className="avatar user">
                  <img src={avatarUser} alt="" width={44} height={44} decoding="async" />
                </div>
              )}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        <div className="composer-wrap">
          {error && (
            <div className="error-banner" role="alert">
              {error}
            </div>
          )}
          <Composer onSend={(t) => void handleSend(t)} sending={sending} />
        </div>
      </main>

      {renameFor && (
        <div
          className="modal-backdrop"
          role="presentation"
          onClick={(e) => {
            if (e.target === e.currentTarget) setRenameFor(null);
          }}
        >
          <div className="modal" role="dialog" aria-labelledby="rename-title">
            <h3 id="rename-title">Rename session</h3>
            <label htmlFor="rename-input">Session name</label>
            <input
              id="rename-input"
              value={renameInput}
              onChange={(e) => setRenameInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void submitRename();
              }}
              autoFocus
            />
            <div className="modal-actions">
              <button type="button" onClick={() => setRenameFor(null)}>
                Cancel
              </button>
              <button type="button" className="save" onClick={() => void submitRename()}>
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SunIcon() {
  return (
    <svg className="theme-trigger-icon" width="22" height="22" viewBox="0 0 24 24" aria-hidden>
      <circle cx="12" cy="12" r="4" fill="currentColor" />
      <g stroke="currentColor" strokeWidth="2" strokeLinecap="round" fill="none">
        <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
      </g>
    </svg>
  );
}

function ThemeControl({
  theme,
  onThemeChange,
}: {
  theme: Theme;
  onThemeChange: (t: Theme) => void;
}) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const close = () => setOpen(false);
    const t = window.setTimeout(() => document.addEventListener("click", close), 0);
    return () => {
      clearTimeout(t);
      document.removeEventListener("click", close);
    };
  }, [open]);

  return (
    <div className="theme-dropdown-wrap">
      <button
        type="button"
        className="theme-trigger"
        aria-label="Appearance"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={(e) => {
          e.stopPropagation();
          setOpen((v) => !v);
        }}
      >
        <SunIcon />
      </button>
      {open && (
        <div
          className="theme-dropdown"
          role="menu"
          aria-label="Theme"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            type="button"
            role="menuitemradio"
            aria-checked={theme === "light"}
            className={`theme-dropdown-item ${theme === "light" ? "is-active" : ""}`}
            onClick={() => {
              onThemeChange("light");
              setOpen(false);
            }}
          >
            Light
          </button>
          <button
            type="button"
            role="menuitemradio"
            aria-checked={theme === "dark"}
            className={`theme-dropdown-item ${theme === "dark" ? "is-active" : ""}`}
            onClick={() => {
              onThemeChange("dark");
              setOpen(false);
            }}
          >
            Dark
          </button>
        </div>
      )}
    </div>
  );
}

function Composer({ onSend, sending }: { onSend: (text: string) => void; sending: boolean }) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const submit = () => {
    if (!value.trim() || sending) return;
    onSend(value);
    setValue("");
    queueMicrotask(() => textareaRef.current?.focus());
  };

  return (
    <div className="composer">
      <textarea
        ref={textareaRef}
        rows={1}
        placeholder="Message…"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
      />
      <button type="button" className="send-btn" disabled={sending || !value.trim()} aria-label="Send" onClick={submit}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
          <path
            d="M4 12L20 4 13 20l-3-7-7-3z"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinejoin="round"
          />
        </svg>
      </button>
    </div>
  );
}
