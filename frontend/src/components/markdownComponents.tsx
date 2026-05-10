import React, { useCallback, useMemo, useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vs, vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import type { Components } from "react-markdown";

function nodeToPlainText(node: React.ReactNode): string {
  if (node == null || typeof node === "boolean") return "";
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(nodeToPlainText).join("");
  if (React.isValidElement(node)) {
    return nodeToPlainText(node.props.children as React.ReactNode);
  }
  return "";
}

/** Map markdown fence language → Prism grammar id (VS Code–style highlighting). */
function toPrismLanguage(label: string): string {
  const k = label.toLowerCase().trim();
  const map: Record<string, string> = {
    js: "javascript",
    javascript: "javascript",
    jsx: "jsx",
    mjs: "javascript",
    cjs: "javascript",
    ts: "typescript",
    tsx: "tsx",
    py: "python",
    python: "python",
    rb: "ruby",
    rs: "rust",
    go: "go",
    golang: "go",
    sh: "bash",
    bash: "bash",
    shell: "bash",
    zsh: "bash",
    ps1: "powershell",
    yml: "yaml",
    yaml: "yaml",
    md: "markdown",
    json: "json",
    jsonc: "json",
    html: "markup",
    xml: "markup",
    svg: "markup",
    vue: "markup",
    css: "css",
    scss: "scss",
    sass: "sass",
    less: "less",
    sql: "sql",
    swift: "swift",
    kt: "kotlin",
    kts: "kotlin",
    java: "java",
    cpp: "cpp",
    cxx: "cpp",
    cc: "cpp",
    hpp: "cpp",
    h: "cpp",
    c: "c",
    cs: "csharp",
    fs: "fsharp",
    php: "php",
    dart: "dart",
    lua: "lua",
    r: "r",
    scala: "scala",
    dockerfile: "docker",
    graphql: "graphql",
    gql: "graphql",
    toml: "toml",
    ini: "ini",
    env: "properties",
    proto: "protobuf",
    diff: "diff",
    txt: "markdown",
    text: "markdown",
    plaintext: "markdown",
    log: "markdown",
  };
  return map[k] ?? k;
}

function CodeBlockSunIcon() {
  return (
    <svg className="md-code-theme-icon" width="18" height="18" viewBox="0 0 24 24" aria-hidden>
      <circle cx="12" cy="12" r="4" fill="currentColor" />
      <g stroke="currentColor" strokeWidth="2" strokeLinecap="round" fill="none">
        <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
      </g>
    </svg>
  );
}

function PreWithToolbar({ children }: React.HTMLAttributes<HTMLPreElement>) {
  const rawText = nodeToPlainText(children);

  let langLabel = "text";
  try {
    const child = React.Children.only(children) as React.ReactElement<{ className?: string }>;
    const cls = child.props.className ?? "";
    const langMatch = /language-([\w+-]+)/.exec(cls);
    if (langMatch) langLabel = langMatch[1];
  } catch {
    /* not a single code child */
  }

  const [copied, setCopied] = useState(false);
  const [panelLight, setPanelLight] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(rawText);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }, [rawText]);

  const prismLang = useMemo(() => toPrismLanguage(langLabel), [langLabel]);
  const highlightStyle = panelLight ? vs : vscDarkPlus;
  const codeForHighlight = rawText.replace(/\n$/, "");

  return (
    <div className={`md-code-panel ${panelLight ? "md-code-panel--light" : "md-code-panel--dark"}`}>
      <div className="md-code-toolbar">
        <span className="md-code-lang">{langLabel}</span>
        <div className="md-code-toolbar-end">
          <button
            type="button"
            className="md-code-theme-btn"
            aria-label={panelLight ? "Use dark style for this code block" : "Use light style for this code block"}
            aria-pressed={panelLight}
            title="Toggle light / dark code style"
            onClick={() => setPanelLight((v) => !v)}
          >
            <CodeBlockSunIcon />
          </button>
          <button type="button" className="md-code-copy-btn" onClick={() => void handleCopy()}>
            {copied ? "Copied!" : "Copy code"}
          </button>
        </div>
      </div>
      <div className="md-code-pre md-code-pre--syntax">
        <SyntaxHighlighter
          PreTag="div"
          language={prismLang}
          style={highlightStyle}
          showLineNumbers={false}
          wrapLongLines={false}
          customStyle={{
            margin: 0,
            padding: "0.85rem 1rem 1rem",
            borderRadius: 0,
            fontSize: "0.8125rem",
            lineHeight: 1.55,
            background: "transparent",
          }}
          codeTagProps={{
            style: {
              fontFamily:
                'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "JetBrains Mono", monospace',
              fontSize: "inherit",
            },
          }}
        >
          {codeForHighlight}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}

function CodeElement({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLElement> & { node?: unknown }) {
  const isFence = typeof className === "string" && className.includes("language-");
  const rest = { ...props } as Record<string, unknown>;
  delete rest.node;

  if (isFence) {
    return (
      <code className={className} {...(rest as React.HTMLAttributes<HTMLElement>)}>
        {children}
      </code>
    );
  }
  const inlineClass = ["md-inline-code", className].filter(Boolean).join(" ");
  return (
    <code className={inlineClass} {...(rest as React.HTMLAttributes<HTMLElement>)}>
      {children}
    </code>
  );
}

function openInNewTab(href: string | undefined): boolean {
  if (!href || href.startsWith("#")) return false;
  try {
    const u = new URL(href, window.location.origin);
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}

function MarkdownLink({
  href,
  children,
  ...props
}: React.AnchorHTMLAttributes<HTMLAnchorElement> & { node?: unknown }) {
  const rest = { ...props } as Record<string, unknown>;
  delete rest.node;
  const external = openInNewTab(typeof href === "string" ? href : undefined);
  return (
    <a
      href={href}
      {...(rest as React.AnchorHTMLAttributes<HTMLAnchorElement>)}
      {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
    >
      {children}
    </a>
  );
}

export const markdownComponents: Partial<Components> = {
  pre: PreWithToolbar,
  code: CodeElement,
  a: MarkdownLink,
};
